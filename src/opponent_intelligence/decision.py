"""Offline, offense-only Run/Pass evidence. No ranking, model, API or IO."""

from copy import deepcopy
from dataclasses import dataclass

from .cohort import context_filters, filter_context, select_population
from .metrics import metric_difference, summarize_plays
from .pbp import Dataset, Play
from .uncertainty import build_candidate_uncertainty, validate_bootstrap


@dataclass(frozen=True, kw_only=True)
class DecisionRequest:
    """Exact down and inclusive distance; validated when evidence is built.

    Equal distance bounds select an exact distance. No implicit widening, opponent
    adjustment or defensive decision support. Other bounds share Scout semantics.
    """

    team: str
    season: int
    before_week: int
    down: int
    distance_min: int
    distance_max: int
    season_type: str = "REG"
    yardline_min: float | None = None
    yardline_max: float | None = None
    score_min: int | None = None
    score_max: int | None = None
    period: str | None = None
    clock_min: int | None = None
    clock_max: int | None = None
    minimum_plays: int = 30
    compare_league: bool = False
    bootstrap_repetitions: int | None = None
    bootstrap_seed: int | None = None


def _candidate_evidence(population: list[Play], minimum_plays: int) -> list[dict]:
    """Identical candidate definitions and denominators for either population."""
    candidates = []
    for name, dropback, label in (("run", False, "Run (non-dropback)"),
                                  ("pass", True, "Pass (dropback, including sacks/scrambles)")):
        plays = [play for play in population if play.dropback == dropback]
        metrics = summarize_plays(plays, minimum_plays)
        if not population:
            outcome_state = "empty_cohort"
        elif not plays:
            outcome_state = "unobserved_candidate"
        elif not metrics["epa_observations"]:
            outcome_state = "missing_epa"
        else:
            outcome_state = "available"
        candidates.append({
            "candidate": name, "label": label,
            "mapping": {"source_field": "qb_dropback", "equals": int(dropback)},
            **{key: metrics[key] for key in (
                "plays", "games", "epa_observations", "missing_epa", "epa_per_play",
                "success_rate", "small_sample", "small_epa_sample",
            )},
            "frequency": len(plays) / len(population) if population else None,
            "frequency_denominator": len(population),
            "availability": {"frequency": "available" if population else "empty_cohort",
                             "outcomes": outcome_state},
        })
    return candidates


def _context_warnings(contexts: dict, quality: dict, *, prefix: str = "") -> list[str]:
    warnings = []
    for name, context in contexts.items():
        stage = quality[name + "_filter"]
        if stage["missing_" + context["field"]]:
            warnings.append(f"{prefix}{name} filter excluded {stage['missing_' + context['field']]} of "
                            f"{stage['plays_before_filter']} surviving plays with missing "
                            f"{context['field']}; no imputation.")
    return warnings


def _candidate_comparison(candidates: list[dict]) -> dict:
    """Separate arithmetic availability from permission to rank observed calls.

    Only the already selected candidate summaries enter this policy. League
    estimates, count thresholds and bootstrap endpoints cannot unlock a winner.
    """
    by_name = {candidate["candidate"]: candidate for candidate in candidates}
    run, passed = by_name["run"], by_name["pass"]
    metrics = {}
    for name, field, scale, unit, availability in (
        ("frequency_pp", "frequency", 100, "percentage_points", "frequency"),
        ("epa_per_play", "epa_per_play", 1, "expected_points_per_observed_play", "outcomes"),
        ("success_rate_pp", "success_rate", 100, "percentage_points", "outcomes"),
    ):
        value = metric_difference(passed[field], run[field], scale=scale)
        metrics[name] = {
            "value": value, "unit": unit,
            "status": "unavailable" if value is None else "available",
            "unavailable_candidates": {
                candidate["candidate"]: candidate["availability"][availability]
                for candidate in (run, passed) if candidate[field] is None
            },
        }
    return {
        "status": "insufficient_evidence", "preferred_candidate": None,
        "reason": "candidate_comparison_not_validated",
        "policy_version": "descriptive_only_v1",
        "descriptive_contrast": {
            "population": "selected_offense", "direction": "pass_minus_run",
            "metrics": metrics,
            "uncertainty": {"status": "not_implemented", "interval": None},
        },
        "opponent_evidence": {
            "status": "deferred", "reason": "opponent_conditioning_not_validated",
        },
    }


def _league_comparison(
    evidence: dict, selected: list[Play], others: list[Play], contexts: dict, minimum_plays: int,
) -> tuple[dict, list[Play]]:
    baseline, quality = filter_context(others, contexts)
    candidates = _candidate_evidence(baseline, minimum_plays)
    selected_by_name = {candidate["candidate"]: candidate for candidate in evidence["candidates"]}
    for candidate in candidates:
        dropback = candidate["mapping"]["equals"]
        plays = [play for play in baseline if play.dropback == dropback]
        teams = sorted({play.offense for play in plays})
        candidate["coverage"] = {
            "teams": teams, "team_count": len(teams),
            "shared_games_with_selected_candidate": len(
                {play.game_id for play in plays}
                & {play.game_id for play in selected if play.dropback == dropback}
            ),
        }
        left = selected_by_name[candidate["candidate"]]
        candidate["difference"] = {
            "frequency_pp": metric_difference(left["frequency"], candidate["frequency"], scale=100),
            "epa_per_play": metric_difference(left["epa_per_play"], candidate["epa_per_play"]),
            "success_rate_pp": metric_difference(left["success_rate"], candidate["success_rate"], scale=100),
        }
    teams = sorted({play.offense for play in baseline})
    warnings = [
        "Baseline uses only available source plays; observed teams/counts do not certify full league coverage.",
        "Plays are pooled, not equally weighted team/game means; context mixes within requested ranges may differ.",
        "Descriptive differences are not opponent adjustment, causal effects, predictive validation or action ranking.",
        "Selected and baseline plays are disjoint but may share games/opponents; game counts are not independence guarantees.",
    ]
    if not baseline:
        warnings.append("No matching baseline plays; frequencies, outcomes and differences are null. No fallback.")
    if any(candidate["missing_epa"] for candidate in candidates):
        warnings.append("Missing baseline EPA affects only candidate EPA/success denominators, not call frequency.")
    warnings.extend(_context_warnings(contexts, quality, prefix="Baseline "))
    return {
        "population": {
            "scope": "available_source_only", "side": "offense", "team_field": "posteam",
            "excluded_team": evidence["cohort"]["team"], "weighting": "pooled_plays",
            "plays": len(baseline), "games": len({play.game_id for play in baseline}),
            "teams": teams, "team_count": len(teams),
            "shared_games_with_selected": len({play.game_id for play in baseline}
                                              & {play.game_id for play in selected}),
        },
        "cohort": deepcopy({key: value for key, value in evidence["cohort"].items() if key != "team"}),
        "difference_convention": "selected_minus_baseline",
        "difference_units": {"frequency_pp": "percentage_points",
                             "epa_per_play": "expected_points_per_observed_play",
                             "success_rate_pp": "percentage_points"},
        "data_quality": {
            "eligible_rows_same_season_type_before_week":
                evidence["data_quality"]["eligible_rows_same_season_type_before_week"],
            "excluded_selected_team_rows": evidence["data_quality"]["team_plays_before_context_filters"],
            "plays_before_context_filters": len(others), "plays_after_context_filters": len(baseline),
            "filter_order": list(contexts), **quality,
        },
        "candidates": candidates,
        "warnings": warnings,
    }, baseline


def build_decision_evidence(
    dataset: Dataset, request: DecisionRequest, *, source_label: str,
) -> dict:
    """Describe observed candidate outcomes, never estimate an unplayed call.

    Accept an already validated Dataset; retain its original ingestion accounting
    and provenance. The separate contract version is NOT Scout report schema v2.
    """
    if not isinstance(request, DecisionRequest):
        raise TypeError("request must be a DecisionRequest")
    for name, lower, upper in (("down", 1, 4), ("distance_min", 0, 100), ("distance_max", 0, 100)):
        value = getattr(request, name)
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError(f"{name} must be an integer in {lower}..{upper}")
    if request.distance_min > request.distance_max:
        raise ValueError("distance_min must not exceed distance_max")
    if type(request.minimum_plays) is not int or request.minimum_plays < 1:
        raise ValueError("minimum_plays must be a positive integer warning threshold")
    if type(request.compare_league) is not bool:
        raise ValueError("compare_league must be a boolean")
    bootstrap_seed = validate_bootstrap(request.bootstrap_repetitions, request.bootstrap_seed)
    if not isinstance(source_label, str) or not source_label.strip():
        raise ValueError("source_label must describe the input data")
    temporal, team_plays = select_population(
        dataset, team=request.team, season=request.season, before_week=request.before_week,
        season_type=request.season_type,
    )
    contexts = context_filters(
        dataset, yardline_min=request.yardline_min, yardline_max=request.yardline_max,
        score_min=request.score_min, score_max=request.score_max, period=request.period,
        clock_min=request.clock_min, clock_max=request.clock_max,
    )
    # Keep Scout's optional-filter order; append exact situation constraints.
    # Use the same selector, not Scout's short/medium/long presentation buckets.
    contexts["down"] = {"field": "down", "minimum_inclusive": request.down,
                        "maximum_inclusive": request.down, "missing_policy": "reject_at_ingestion"}
    contexts["distance"] = {"field": "yards_to_go", "minimum_inclusive": request.distance_min,
                            "maximum_inclusive": request.distance_max,
                            "missing_policy": "reject_at_ingestion"}
    selected, quality = filter_context(team_plays, contexts)
    candidates = _candidate_evidence(selected, request.minimum_plays)
    source = {"label": source_label, "sha256": dataset.source_sha256}
    if dataset.source_manifest is not None:
        source["snapshot"] = deepcopy(dataset.source_manifest)
    warnings = [
        "Observed run/dropback categories are not verified intended calls; sacks and scrambles are Pass.",
        "Only eligible run/pass plays are counted; not every attempted call or fourth-down option is represented.",
        "Descriptive associations are not causal effects, guaranteed future performance or coaching recommendations.",
        "Week filtering does not reconstruct historical source availability or EPA model training.",
        "Small-sample flags are count warnings, not validated reliability or ranking thresholds.",
        "Opponent adjustment and EP/WP action values are not implemented here.",
    ]
    if not selected:
        warnings.append("No matching plays; no widening or fallback. Frequencies and outcomes are null.")
    if any(candidate["missing_epa"] for candidate in candidates):
        warnings.append("Missing EPA changes only candidate EPA/success denominators, not call frequency.")
    warnings.extend(_context_warnings(contexts, quality))
    evidence = {
        "contract_version": 1,
        "evidence_kind": "descriptive_observed_calls",
        "source": source,
        "cohort": {"team": request.team, "side": "offense", "season": request.season,
                   "season_type": request.season_type, "before_week_exclusive": request.before_week,
                   **contexts},
        "metric_context": {"perspective": "offense", "interpretation": "produced",
                           "success_condition": "epa > 0", "frequency_unit": "proportion"},
        "estimation_policy": {"frequency_minimum_parent_plays": 1,
                              "outcome_minimum_epa_observations": 1,
                              "minimum_plays_warning": request.minimum_plays},
        "population": {"plays": len(selected), "games": len({play.game_id for play in selected})},
        "data_quality": {
            "input_rows": dataset.input_rows, "eligible_rows_all_teams": len(dataset.plays),
            "excluded_rows_by_reason": dict(sorted(dataset.exclusions.items())),
            "eligible_rows_outside_cohort": len(dataset.plays) - len(selected),
            "eligible_rows_same_season_type_before_week": len(temporal),
            "team_plays_before_context_filters": len(team_plays),
            "filter_order": list(contexts), **quality,
        },
        "candidates": candidates,
        "comparison": _candidate_comparison(candidates),
        "warnings": warnings,
    }
    baseline = None
    if request.compare_league:
        others = [play for play in temporal if play.offense != request.team]
        evidence["league_comparison"], baseline = _league_comparison(
            evidence, selected, others, contexts, request.minimum_plays,
        )
    if request.bootstrap_repetitions is not None:
        evidence["uncertainty"] = build_candidate_uncertainty(
            selected, baseline, repetitions=request.bootstrap_repetitions, seed=bootstrap_seed,
        )
    return evidence
