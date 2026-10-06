"""Exploratory whole-game percentile bootstrap, not predictive validation."""

from collections import Counter, defaultdict
from math import ceil, fsum, isclose
from random import Random
from typing import NamedTuple

from .pbp import Play


METRICS = ("dropback_rate", "success_rate", "epa_per_play")
DIFFERENCES = ("dropback_rate_pp", "success_rate_pp", "epa_per_play")
MINIMUM_GAMES = 5
FEW_GAMES = 20
MINIMUM_VALID_FRACTION = 0.95


class _GameTotals(NamedTuple):
    plays: int
    dropbacks: int
    epa_observations: int
    epa_sum: float
    positive_epa: int


def validate_bootstrap(repetitions: int | None, seed: int | None) -> int | None:
    if repetitions is None:
        if seed is not None:
            raise ValueError("bootstrap_seed requires bootstrap_repetitions")
        return None
    if type(repetitions) is not int or not 200 <= repetitions <= 10000:
        raise ValueError("bootstrap_repetitions must be an integer in 200..10000")
    if seed is None:
        return 0
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("bootstrap_seed must be an integer in 0..4294967295")
    return seed


def _game_totals(plays: list[Play]) -> dict:
    by_game = defaultdict(list)
    for play in plays:
        by_game[play.game_id].append(play)
    totals = {}
    for game, rows in sorted(by_game.items()):
        # Stable aggregation order makes the bootstrap insensitive to input row order.
        rows.sort(key=lambda p: p.play_id)
        observed = [p.epa for p in rows if p.epa is not None]
        totals[game] = _GameTotals(len(rows), sum(p.dropback for p in rows), len(observed),
                                  fsum(observed), sum(v > 0 for v in observed))
    return totals


def _weighted_metrics(totals: dict, weights: dict) -> tuple:
    rows = [(values, weights[game]) for game, values in totals.items() if weights.get(game, 0)]
    plays = sum(v.plays * w for v, w in rows)
    observed = sum(v.epa_observations * w for v, w in rows)
    # Pool play numerators/denominators, not unweighted game averages. Normalize
    # before multiplying EPA sums to avoid overflow from large multiplicities.
    return (
        sum(v.dropbacks * w for v, w in rows) / plays if plays else None,
        sum(v.positive_epa * w for v, w in rows) / observed if observed else None,
        fsum(v.epa_sum * (w / observed) for v, w in rows) if observed else None,
    )


def _percentile(ordered: list[float], probability: float) -> float:
    position = (len(ordered) - 1) * probability
    lower = int(position)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[min(lower + 1, len(ordered) - 1)] * fraction


def _summary(values: list[float], support: dict, attempted: int, unit: str) -> dict:
    minimum = min(support.values())
    interval = None
    if minimum == 0:
        status = "undefined_estimate"
    elif minimum < MINIMUM_GAMES:
        status = "insufficient_games"
    elif len(values) < ceil(MINIMUM_VALID_FRACTION * attempted):
        status = "too_few_valid_replicates"
    else:
        ordered = sorted(values)
        lower, upper = _percentile(ordered, 0.025), _percentile(ordered, 0.975)
        if isclose(lower, upper, rel_tol=1e-12, abs_tol=1e-12):
            status = "degenerate_interval"
        else:
            status = "ok"
            interval = {"lower": lower, "upper": upper}
    return {"interval": interval, "status": status, "unit": unit,
            "support_games": support, "few_games": minimum < FEW_GAMES,
            "valid_replicates": len(values), "undefined_replicates": attempted - len(values)}


def build_uncertainty(
    selected_groups: dict[tuple[int, str], list[Play]],
    baseline_groups: dict[tuple[int, str], list[Play]] | None,
    *, repetitions: int, seed: int,
) -> dict:
    """Use one joint game-multiplicity draw for every population and situation.

    Inputs have already passed the report's role, time, and context selection.
    None means comparison was not requested; an empty dict is a requested but
    empty baseline. Overall includes baseline-only buckets, even though the
    situation output contains only buckets observed for the selected team.
    """
    comparison = baseline_groups is not None
    populations = {"selected": selected_groups}
    if comparison:
        populations["baseline"] = baseline_groups
    distance_order = {"short": 0, "medium": 1, "long": 2}
    keys = [None] + sorted(selected_groups, key=lambda k: (k[0], distance_order[k[1]]))
    totals = {}
    for name, groups in populations.items():
        totals[name] = {key: _game_totals(
            [p for plays in groups.values() for p in plays] if key is None else groups.get(key, [])
        ) for key in keys}
    games = sorted({game for population in totals.values() for game in population[None]})
    samples = {key: {name: [[], [], []] for name in populations} for key in keys}
    if comparison:
        for key in keys:
            samples[key]["difference"] = [[], [], []]
    rng = Random(seed)
    attempted = repetitions if games else 0
    for _ in range(attempted):
        # If a shared game is drawn twice, both sides' plays appear twice. Drawing
        # the two populations independently would destroy this paired structure.
        weights = Counter(games[rng.randrange(len(games))] for _ in games)
        for key in keys:
            estimates = {name: _weighted_metrics(by_key[key], weights) for name, by_key in totals.items()}
            if comparison:
                estimates["difference"] = tuple(
                    None if left is None or right is None else (left - right) * scale
                    for left, right, scale in zip(estimates["selected"], estimates["baseline"], (100, 100, 1))
                )
            for name, metrics in estimates.items():
                for values, value in zip(samples[key][name], metrics):
                    if value is not None:
                        values.append(value)

    rows = {}
    for key in keys:
        rows[key] = {}
        for name, distributions in samples[key].items():
            metric_names = DIFFERENCES if name == "difference" else METRICS
            rows[key][name] = {}
            for index, (metric, values) in enumerate(zip(metric_names, distributions)):
                sides = populations if name == "difference" else [name]
                support = {side: sum((v.plays if index == 0 else v.epa_observations) > 0
                                     for v in totals[side][key].values())
                           for side in sides}
                unit = ("expected_points_per_observed_play" if index == 2
                        else "percentage_points" if name == "difference" else "proportion")
                rows[key][name][metric] = _summary(values, support, attempted, unit)
    return {
        "method": "game_cluster_percentile_v1", "nominal_level": 0.95,
        "repetitions": repetitions, "performed_repetitions": attempted, "seed": seed,
        "random_generator": "python_random.Random.randrange", "quantile_method": "linear_n_minus_1",
        "resampling_unit": "game_id", "resampling_games": len(games),
        "resampling_population": "selected_and_baseline_union" if comparison else "selected",
        "shared_game_weights": comparison,
        "minimum_support_games": MINIMUM_GAMES, "few_games_warning_below": FEW_GAMES,
        "minimum_valid_fraction": MINIMUM_VALID_FRACTION,
        "overall": rows[None],
        "situations": [{"down": key[0], "distance": key[1], **rows[key]} for key in keys[1:]],
        "warnings": [
            "Exploratory pointwise percentile intervals, not calibrated coverage, significance tests, or predictions.",
            "Whole-game resampling retains within-game dependence; repeated teams/opponents across games remain dependent.",
            "Five-game and 95%-valid gates are application safeguards, not statistical reliability guarantees; few games remain fragile.",
            "Undefined resamples are counted and excluded; any reported bounds condition on defined replicates.",
            "Constant or near-zero-width percentile intervals are withheld, not interpreted as certainty.",
            "Selection is fixed before resampling; source availability, missing-data bias, and upstream EPA model uncertainty are not estimated.",
        ],
    }
