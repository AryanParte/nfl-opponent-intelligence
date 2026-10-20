"""Offline verification oracle, NOT a second production analytics/ingestion API.

Use the existing bounded snapshot reader/adapter, then independently select raw
CSV records and expand sampled games into rows. Only the system under test calls
the decision builder; the oracle never imports its selectors/metrics/resampler.
"""

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import csv
from dataclasses import asdict
from decimal import Decimal, localcontext
from hashlib import sha256
from io import StringIO
import json
from math import ceil, isclose, isfinite
from pathlib import Path
from random import Random
from statistics import quantiles
import sys

from opponent_intelligence.decision import DecisionRequest, build_decision_evidence
from opponent_intelligence.ingestion import _read_snapshot, _snapshot_dataset


ARCHIVE_SHA256 = "23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06"
CSV_SHA256 = "6ae564c2c49378ec531303292966caee596982278b9fcdad9c9dd0a0dc16bfa7"
TOLERANCE = 1e-12
METRICS = ("frequency", "success_rate", "epa_per_play")
DIFFERENCES = ("frequency_pp", "success_rate_pp", "epa_per_play")

# Fixed before inspecting results. These are audit cases, not selected findings.
CASES = (
    ("car-empty-before-week-one", dict(before_week=1)),
    ("car-early-first-ten", dict(before_week=3)),
    ("car-full-first-ten", {}),
    ("car-midseason-third-four", dict(before_week=10, down=3, distance_min=4, distance_max=4)),
    ("car-late-close-range", dict(down=3, distance_min=1, distance_max=4, yardline_max=50,
                                score_max=0, period="Q4", clock_max=300)),
    ("car-overtime-second-down", dict(down=2, distance_min=0, distance_max=10, period="OT")),
    ("kc-postseason-third-short", dict(team="KC", season_type="POST", before_week=23,
                                     down=3, distance_min=1, distance_max=4)),
    ("car-absent-postseason", dict(season_type="POST", before_week=23)),
)


class AuditMismatch(ValueError):
    """A checked production value disagrees with its raw-record reference."""


def check(actual, expected, path="result"):
    """Compare a declared subset, exact counts/states, absolute-only float tolerance."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise AuditMismatch(f"{path}: expected mapping")
        for key, value in expected.items():
            if key not in actual:
                raise AuditMismatch(f"{path}.{key}: missing")
            check(actual[key], value, f"{path}.{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise AuditMismatch(f"{path}: list length/type differs")
        for index, (value, reference) in enumerate(zip(actual, expected)):
            check(value, reference, f"{path}[{index}]")
    elif isinstance(expected, float):
        if (type(actual) not in (int, float) or not isfinite(actual)
                or not isclose(actual, expected, rel_tol=0, abs_tol=TOLERANCE)):
            raise AuditMismatch(f"{path}: {actual!r} != {expected!r}")
    elif type(actual) is not type(expected) or actual != expected:
        raise AuditMismatch(f"{path}: {actual!r} != {expected!r}")


def raw_eligible(raw):
    """Specific to already adapter-validated input, not a permissive replacement parser."""
    rows = []
    for source in csv.DictReader(StringIO(raw.decode("utf-8-sig")), strict=True):
        source = {key: value.strip() for key, value in source.items()}
        if source["play_type"] not in {"run", "pass"} or any(
            Decimal(source[key]) != 0 for key in ("two_point_attempt", "qb_kneel", "qb_spike")
        ):
            continue
        row = {key: source[key] for key in ("game_id", "season_type", "posteam")}
        for key in ("play_id", "season", "week", "down", "ydstogo", "qb_dropback",
                    "epa", "yardline_100", "score_differential", "qtr", "quarter_seconds_remaining"):
            value = source.get(key, "")
            row[key] = None if value.upper() in {"", "NA", "NAN", "NULL"} else Decimal(value)
        rows.append(row)
    return rows


def raw_context(rows, request):
    """Direct predicates/ordered ledgers without production context helpers."""
    stages = []
    if request.yardline_min is not None or request.yardline_max is not None:
        stages.append(("field_position", "yardline_100",
                       0 if request.yardline_min is None else request.yardline_min,
                       100 if request.yardline_max is None else request.yardline_max))
    if request.score_min is not None or request.score_max is not None:
        stages.append(("score_differential", "score_differential", request.score_min, request.score_max))
    if request.period:
        lower = 5 if request.period == "OT" else int(request.period[1])
        stages.append(("period", "qtr", lower, None if request.period == "OT" else lower))
    if request.clock_min is not None or request.clock_max is not None:
        stages.append(("clock", "quarter_seconds_remaining",
                       0 if request.clock_min is None else request.clock_min,
                       900 if request.clock_max is None else request.clock_max))
    stages.extend((("down", "down", request.down, request.down),
                   ("distance", "ydstogo", request.distance_min, request.distance_max)))
    quality = {"filter_order": [stage[0] for stage in stages]}
    for name, field, lower, upper in stages:
        known = [row for row in rows if row[field] is not None]
        kept = [row for row in known
                if (lower is None or row[field] >= Decimal(str(lower)))
                and (upper is None or row[field] <= Decimal(str(upper)))]
        typed_field = "yards_to_go" if field == "ydstogo" else field
        quality[name + "_filter"] = {
            "plays_before_filter": len(rows), "missing_" + typed_field: len(rows) - len(known),
            "outside_period" if name == "period" else "outside_range": len(known) - len(kept),
            "plays_after_filter": len(kept),
        }
        rows = kept
    return rows, quality


def calls(rows, candidate):
    return [row for row in rows if row["qb_dropback"] == (candidate == "pass")]


def games(rows):
    return {row["game_id"] for row in rows}


def ratios(parent, candidate):
    subset = calls(parent, candidate)
    epa = [row["epa"] for row in subset if row["epa"] is not None]
    return (
        Decimal(len(subset)) / len(parent) if parent else None,
        Decimal(sum(value > 0 for value in epa)) / len(epa) if epa else None,
        sum(epa, Decimal(0)) / len(epa) if epa else None,
    )


def floats(values):
    return {key: None if value is None else float(value) for key, value in values.items()}


def differences(left, right):
    return tuple(None if a is None or b is None else (a - b) * scale
                 for a, b, scale in zip(left, right, (100, 100, 1)))


def point_evidence(parent, candidate, minimum):
    subset = calls(parent, candidate)
    observed = [row for row in subset if row["epa"] is not None]
    return {
        "candidate": candidate, "plays": len(subset), "games": len(games(subset)),
        "epa_observations": len(observed), "missing_epa": len(subset) - len(observed),
        "frequency_denominator": len(parent), **floats(dict(zip(METRICS, ratios(parent, candidate)))),
        "small_sample": len(subset) < minimum, "small_epa_sample": len(observed) < minimum,
        "availability": {
            "frequency": "available" if parent else "empty_cohort",
            "outcomes": ("empty_cohort" if not parent else "unobserved_candidate" if not subset
                         else "missing_epa" if not observed else "available"),
        },
    }


def interval(values, support, attempted, unit):
    """Separate quantile implementation; literal safeguards check method-version drift."""
    minimum = min(support.values())
    bounds = None
    if minimum == 0:
        status = "undefined_estimate"
    elif minimum < 5:
        status = "insufficient_games"
    elif len(values) < ceil(Decimal("0.95") * attempted):
        status = "too_few_valid_replicates"
    else:
        cuts = quantiles(values, n=40, method="inclusive")
        lower, upper = float(cuts[0]), float(cuts[-1])
        status = "degenerate_interval" if isclose(lower, upper, rel_tol=1e-12, abs_tol=1e-12) else "ok"
        if status == "ok":
            bounds = {"lower": lower, "upper": upper}
    return {
        "interval": bounds, "status": status, "unit": unit, "support_games": support,
        "few_games": minimum < 20, "valid_replicates": len(values),
        "undefined_replicates": attempted - len(values),
    }


def raw_uncertainty(populations, repetitions, seed):
    by_game = {name: defaultdict(list) for name in populations}
    for name, rows in populations.items():
        for row in rows:
            by_game[name][row["game_id"]].append(row)
    frame = sorted(set().union(*(games(rows) for rows in populations.values())))
    sides = [*populations, "difference"] if "baseline" in populations else ["selected"]
    samples = {call: {side: [[], [], []] for side in sides} for call in ("run", "pass")}
    generator = Random(seed)
    attempted = repetitions if frame else 0
    for _ in range(attempted):
        draw = [frame[generator.randrange(len(frame))] for _ in frame]
        # Deliberately expand rows, no production sufficient totals or weighting.
        expanded = {name: [row for game in draw for row in by_game[name][game]] for name in populations}
        for call in samples:
            estimates = {name: ratios(rows, call) for name, rows in expanded.items()}
            if "baseline" in populations:
                estimates["difference"] = differences(estimates["selected"], estimates["baseline"])
            for side, values in estimates.items():
                for distribution, value in zip(samples[call][side], values):
                    if value is not None:
                        distribution.append(value)
    result = []
    for call, by_side in samples.items():
        record = {"candidate": call}
        for side, distributions in by_side.items():
            names = DIFFERENCES if side == "difference" else METRICS
            record[side] = {}
            for index, (name, values) in enumerate(zip(names, distributions)):
                required = populations if side == "difference" else [side]
                support = {s: len(games(populations[s] if index == 0 else [
                    row for row in calls(populations[s], call) if row["epa"] is not None
                ])) for s in required}
                unit = ("expected_points_per_observed_play" if index == 2 else
                        "percentage_points" if side == "difference" else "proportion")
                record[side][name] = interval(values, support, attempted, unit)
        result.append(record)
    return {
        "method": "game_cluster_percentile_v1", "nominal_level": 0.95,
        "random_generator": "python_random.Random.randrange", "quantile_method": "linear_n_minus_1",
        "resampling_unit": "game_id", "repetitions": repetitions, "seed": seed,
        "performed_repetitions": attempted, "resampling_games": len(frame),
        "resampling_population": "selected_and_baseline_union" if "baseline" in populations else "selected",
        "shared_game_weights": "baseline" in populations,
        "minimum_support_games": 5, "few_games_warning_below": 20, "minimum_valid_fraction": 0.95,
        "candidates": result,
    }


def raw_reference(rows, request):
    """Expected values derived only from raw records and the declared request."""
    temporal = [row for row in rows if row["season"] == request.season
                and row["season_type"] == request.season_type and row["week"] < request.before_week]
    team = [row for row in temporal if row["posteam"] == request.team]
    selected, quality = raw_context(team, request)
    result = {
        "contract_version": 1, "evidence_kind": "descriptive_observed_calls",
        "cohort": {"team": request.team, "side": "offense", "season": request.season,
                   "season_type": request.season_type, "before_week_exclusive": request.before_week},
        "population": {"plays": len(selected), "games": len(games(selected))},
        "data_quality": {"eligible_rows_all_teams": len(rows),
                         "eligible_rows_outside_cohort": len(rows) - len(selected),
                         "eligible_rows_same_season_type_before_week": len(temporal),
                         "team_plays_before_context_filters": len(team), **quality},
        "candidates": [point_evidence(selected, c, request.minimum_plays) for c in ("run", "pass")],
        "comparison": {"status": "insufficient_evidence", "preferred_candidate": None,
                       "reason": "candidate_comparison_not_validated"},
    }
    populations = {"selected": selected}
    if request.compare_league:
        others = [row for row in temporal if row["posteam"] != request.team]
        baseline, ledger = raw_context(others, request)
        populations["baseline"] = baseline
        candidates = [point_evidence(baseline, c, request.minimum_plays) for c in ("run", "pass")]
        for evidence in candidates:
            call = evidence["candidate"]
            teams = sorted({row["posteam"] for row in calls(baseline, call)})
            evidence["coverage"] = {
                "teams": teams, "team_count": len(teams),
                "shared_games_with_selected_candidate": len(games(calls(baseline, call)) & games(calls(selected, call))),
            }
            evidence["difference"] = floats(dict(zip(DIFFERENCES, differences(
                ratios(selected, call), ratios(baseline, call),
            ))))
        teams = sorted({row["posteam"] for row in baseline})
        result["league_comparison"] = {
            "population": {"plays": len(baseline), "games": len(games(baseline)), "teams": teams,
                           "team_count": len(teams), "excluded_team": request.team,
                           "shared_games_with_selected": len(games(selected) & games(baseline))},
            "data_quality": {"eligible_rows_same_season_type_before_week": len(temporal),
                             "excluded_selected_team_rows": len(team),
                             "plays_before_context_filters": len(others),
                             "plays_after_context_filters": len(baseline), **ledger},
            "candidates": candidates,
        }
    if request.bootstrap_repetitions is not None:
        result["uncertainty"] = raw_uncertainty(
            populations, request.bootstrap_repetitions, request.bootstrap_seed or 0,
        )
    return result


def reconcile(raw, dataset, cases):
    """Fail closed before returning any receipt; usable with invented rows in CI."""
    if sha256(raw).hexdigest() != dataset.source_sha256:
        raise AuditMismatch("raw bytes differ from adapter fingerprint")
    rows = raw_eligible(raw)
    keys = {(r["game_id"], int(r["play_id"])) for r in rows}
    if len(keys) != len(rows) or keys != {(p.game_id, p.play_id) for p in dataset.plays}:
        raise AuditMismatch("raw eligible identities differ from adapter")
    expected_manifest = deepcopy(dataset.source_manifest)
    receipt = []
    # Decimal math is isolated from the caller's context; raw input precision is
    # retained well beyond float comparison tolerance without changing production.
    with localcontext() as context:
        context.prec = 50
        for identifier, request in cases:
            actual = build_decision_evidence(dataset, request, source_label="Retrospective audit input")
            expected = raw_reference(rows, request)
            check(actual, expected, identifier)
            check(actual["source"]["sha256"], dataset.source_sha256, identifier + ".source.sha256")
            if expected_manifest is not None:
                check(actual["source"]["snapshot"], expected_manifest, identifier + ".source.snapshot")
                check(dataset.source_manifest, expected_manifest, identifier + ".input_manifest")
            digest = sha256(json.dumps(expected, sort_keys=True, allow_nan=False).encode()).hexdigest()
            # Compact receipt: complete checked values are hashed, not duplicated
            # as another report. A replay recomputes and checks every declared field.
            point_keys = ("candidate", "plays", "games", "epa_observations", "missing_epa",
                          "frequency_denominator", "frequency", "epa_per_play", "success_rate")
            summary = {"id": identifier, "request": {k: v for k, v in asdict(request).items() if v is not None},
                       "reference_sha256": digest,
                       "population": expected["population"],
                       "selected": [{k: c[k] for k in point_keys} for c in expected["candidates"]]}
            if request.compare_league:
                league = expected["league_comparison"]
                summary["baseline_population"] = {k: league["population"][k] for k in (
                    "plays", "games", "team_count", "shared_games_with_selected",
                )}
                summary["baseline"] = [{k: c[k] for k in (*point_keys, "difference")}
                                       for c in league["candidates"]]
            if "uncertainty" in expected:
                uncertainty = expected["uncertainty"]
                entries = [entry for c in uncertainty["candidates"] for side, metrics in c.items()
                           if side != "candidate" for entry in metrics.values()]
                summary["uncertainty"] = {
                    "resampling_games": uncertainty["resampling_games"],
                    "checked_entries": len(entries),
                    "status_counts": dict(sorted(Counter(e["status"] for e in entries).items())),
                    "selected_epa": {c["candidate"]: c["selected"]["epa_per_play"]
                                     for c in uncertainty["candidates"]},
                }
            receipt.append(summary)
    return {"cases": receipt, "eligible_rows": len(rows)}


def audit_snapshot(directory):
    raw, manifest = _read_snapshot(directory)
    if manifest["archive"]["sha256"] != ARCHIVE_SHA256 or sha256(raw).hexdigest() != CSV_SHA256:
        raise AuditMismatch("this replay requires the pinned 2024 archive AND decoded CSV hashes")
    dataset = _snapshot_dataset(raw, manifest)
    cases = [(name, DecisionRequest(**(dict(team="CAR", season=2024, before_week=19,
                                          down=1, distance_min=10, distance_max=10,
                                          compare_league=True, bootstrap_repetitions=200,
                                          bootstrap_seed=17) | options))) for name, options in CASES]
    return {
        "audit_version": 1, "kind": "retrospective_software_reconciliation_not_model_validation",
        "source": manifest, "absolute_tolerance": TOLERANCE,
        "method": "raw_decimal_expanded_game_rows_statistics_inclusive_quantiles",
        "modifications": "Derived aggregate audit results; no raw rows redistributed or source bytes changed.",
        **reconcile(raw, dataset, cases),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--check", type=Path, help="Compare to a saved aggregate receipt without overwriting it")
    args = parser.parse_args(argv)
    try:
        receipt = audit_snapshot(args.snapshot)
        if args.check:
            # Exact receipt equality includes hashes/method/options, not just totals.
            saved = json.dumps(json.loads(args.check.read_text()), sort_keys=True, allow_nan=False)
            if saved != json.dumps(receipt, sort_keys=True, allow_nan=False):
                raise AuditMismatch("saved receipt differs from freshly reconciled evidence")
        output = json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n"
    except (OSError, ValueError) as exc:
        print(f"decision audit failed: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
