"""Validate the v2 fields a brief consumes, without claiming to audit raw data."""

import json
from math import ceil, isclose, isfinite
import re

from .uncertainty import DIFFERENCES, METRICS, validate_bootstrap


COUNTS = ("plays", "games", "dropbacks", "designed_runs", "epa_observations", "missing_epa")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _integer(value, name: str, minimum: int = 0) -> None:
    _require(type(value) is int and value >= minimum, f"{name} must be an integer >= {minimum}")


def _text(value, name: str) -> None:
    _require(isinstance(value, str) and bool(value.strip()), f"{name} must be nonempty text")


def _object(value, name: str) -> None:
    _require(type(value) is dict, f"{name} must be an object")


def _warnings(value) -> None:
    _require(type(value) is list and all(isinstance(v, str) for v in value), "warnings must be a list of text")


def _json_value(value) -> None:
    if type(value) is dict:
        _require(all(type(k) is str for k in value), "JSON object keys must be strings")
        for child in value.values():
            _json_value(child)
    elif type(value) is list:
        for child in value:
            _json_value(child)
    else:
        _require(value is None or type(value) in (str, int, float, bool), "expected JSON values only")
        if type(value) is float:
            _require(isfinite(value), "non-finite numbers are not supported")


def _number(value, name: str) -> None:
    _require(type(value) in (int, float) and isfinite(value), f"{name} must be a finite number")


def _metrics(row: dict, threshold: int) -> None:
    _object(row, "metrics")
    for key in COUNTS:
        _integer(row[key], key)
    plays, observed = row["plays"], row["epa_observations"]
    _require(row["dropbacks"] + row["designed_runs"] == plays, "play-type counts do not reconcile")
    _require(observed + row["missing_epa"] == plays, "EPA counts do not reconcile")
    _require((plays == 0 and row["games"] == 0) or 1 <= row["games"] <= plays, "invalid game count")
    for key, denominator in (("dropback_rate", plays), ("success_rate", observed), ("epa_per_play", observed)):
        if denominator == 0:
            _require(row[key] is None, f"{key} must be null without a denominator")
        else:
            _number(row[key], key)
            if key != "epa_per_play":
                _require(0 <= row[key] <= 1, f"{key} must be in 0..1")
    if plays:
        _require(isclose(row["dropback_rate"], row["dropbacks"] / plays, rel_tol=1e-12, abs_tol=1e-12),
                 "dropback rate does not match its counts")
    if observed:
        successes = row["success_rate"] * observed
        _require(isclose(successes, round(successes), rel_tol=0, abs_tol=1e-8),
                 "success rate cannot represent an integer count of positive-EPA plays")
    for key, count in (("small_sample", plays), ("small_epa_sample", observed)):
        _require(type(row[key]) is bool and row[key] == (count < threshold), f"{key} disagrees with threshold")


def _situations(rows: list) -> dict:
    _require(type(rows) is list, "situations must be a list")
    indexed = {}
    for row in rows:
        _object(row, "situation")
        _require(type(row["down"]) is int and 1 <= row["down"] <= 4, "situation down must be 1..4")
        _require(row["distance"] in ("short", "medium", "long"), "unknown distance bucket")
        key = (row["down"], row["distance"])
        _require(key not in indexed, "duplicate down/distance bucket")
        indexed[key] = row
    return indexed


def _difference(values: dict, selected: dict, baseline: dict) -> None:
    _object(values, "difference")
    for metric, key, scale in zip(METRICS, DIFFERENCES, (100, 100, 1)):
        left, right = selected[metric], baseline[metric]
        if left is None or right is None:
            _require(values[key] is None, "difference must be null when a side is undefined")
        else:
            _number(values[key], key)
            _require(isclose(values[key], (left - right) * scale, rel_tol=1e-12, abs_tol=1e-12),
                     "difference is not selected minus matching baseline")


def _contexts(cohort: dict) -> None:
    fields = {"field_position": "yardline_100", "score_differential": "score_differential",
              "period": "qtr", "clock": "quarter_seconds_remaining"}
    for name, field in fields.items():
        if name not in cohort:
            continue
        context = cohort[name]
        _object(context, name)
        _require(context["field"] == field and context["missing_policy"] == "exclude", "unsupported context field/policy")
        lower, upper = context["minimum_inclusive"], context["maximum_inclusive"]
        if name == "period":
            label = context["label"]
            _require(label in ("Q1", "Q2", "Q3", "Q4", "OT"), "unsupported period")
            expected = 5 if label == "OT" else int(label[1])
            _require(type(lower) is int and lower == expected, "period lower bound disagrees with label")
            _require(upper is None if label == "OT" else type(upper) is int and upper == expected,
                     "period upper bound disagrees with label")
        elif name == "score_differential":
            _require(context["perspective"] == "offense", "score context must stay offense-relative")
            _require(any(v is not None for v in (lower, upper)), "score filter needs at least one bound")
            _require(all(v is None or type(v) is int for v in (lower, upper)), "score bounds must be integers or null")
        else:
            if name == "clock":
                _require("period" in cohort and context["unit"] == "seconds" and context["timing"] == "pre_play",
                         "clock must use pre-play seconds and an explicit period")
                _require(type(lower) is int and type(upper) is int, "clock bounds must be integers")
                maximum = 900
            else:
                _require(context["perspective"] == "offense", "field context must stay offense-relative")
                maximum = 100
            for value in (lower, upper):
                _number(value, name + " bound")
                _require(0 <= value <= maximum, name + " bound outside supported range")
        _require(lower is None or upper is None or lower <= upper, "context minimum exceeds maximum")


def _quality(report: dict, cohort: dict, comparison: dict | None) -> None:
    quality = report["data_quality"]
    for key in ("input_rows", "eligible_rows_all_teams", "eligible_rows_outside_cohort"):
        _integer(quality[key], key)
    exclusions = quality["excluded_rows_by_reason"]
    _object(exclusions, "excluded_rows_by_reason")
    for count in exclusions.values():
        _integer(count, "excluded rows")
    _require(quality["input_rows"] == quality["eligible_rows_all_teams"] + sum(exclusions.values()),
             "source row accounting does not reconcile")
    _require(quality["eligible_rows_all_teams"] == quality["eligible_rows_outside_cohort"] + report["overall"]["plays"],
             "selected row accounting does not reconcile")
    contexts = [key for key in ("field_position", "score_differential", "period", "clock") if key in cohort]
    populations = [(quality, report["overall"]["plays"])]
    if comparison is not None:
        baseline = comparison["data_quality"]
        for key in ("eligible_rows_same_season_type_before_week", "excluded_selected_team_rows",
                    "plays_before_context_filters", "plays_after_context_filters"):
            _integer(baseline[key], key)
        _require(baseline["eligible_rows_same_season_type_before_week"] == baseline["excluded_selected_team_rows"]
                 + baseline["plays_before_context_filters"], "baseline row accounting does not reconcile")
        _require(baseline["eligible_rows_same_season_type_before_week"] <= quality["eligible_rows_all_teams"]
                 and baseline["plays_after_context_filters"] == comparison["overall"]["plays"], "invalid baseline accounting")
        populations.append((baseline, comparison["overall"]["plays"]))
    for ledger, final_plays in populations:
        previous = None
        if "filter_order" in ledger:
            _require(ledger["filter_order"] == contexts, "filter order does not match requested contexts")
        for name in contexts:
            field = cohort[name]["field"]
            stage = ledger[name + "_filter"]
            keys = ("plays_before_filter", "missing_" + field,
                    "outside_period" if name == "period" else "outside_range", "plays_after_filter")
            for key in keys:
                _integer(stage[key], key)
            before, missing, outside, after = (stage[key] for key in keys)
            _require(before == missing + outside + after and (previous is None or before == previous),
                     "context filter accounting does not reconcile")
            previous = after
        if contexts:
            _require(previous == final_plays, "final context count does not match measurements")
    if comparison is not None:
        first = contexts[0] + "_filter" if contexts else None
        selected_before = quality[first]["plays_before_filter"] if first else report["overall"]["plays"]
        baseline_before = baseline[first]["plays_before_filter"] if first else comparison["overall"]["plays"]
        _require(selected_before == baseline["excluded_selected_team_rows"]
                 and baseline_before == baseline["plays_before_context_filters"], "population context inputs do not reconcile")


def _uncertainty_row(row: dict, populations: dict, metadata: dict) -> None:
    expected = set(populations) | ({"difference"} if "baseline" in populations else set())
    _require(set(row) - {"down", "distance"} == expected, "uncertainty populations do not match report")
    for name in expected:
        metrics = DIFFERENCES if name == "difference" else METRICS
        _require(set(row[name]) == set(metrics), "uncertainty metric keys do not match method")
        for index, key in enumerate(metrics):
            item = row[name][key]
            sides = populations if name == "difference" else {name: populations[name]}
            support = item["support_games"]
            _require(set(support) == set(sides), "uncertainty support populations do not match")
            for side, points in sides.items():
                _integer(support[side], "support_games")
                maximum = points["games"] if index == 0 else min(points["games"], points["epa_observations"])
                _require(0 <= support[side] <= maximum, "uncertainty support exceeds available games")
                if index == 0:
                    _require(support[side] == maximum, "dropback support must equal play-supporting games")
                else:
                    _require((support[side] == 0) == (points["epa_observations"] == 0), "invalid EPA support")
            unit = ("expected_points_per_observed_play" if index == 2 else
                    "percentage_points" if name == "difference" else "proportion")
            _require(item["unit"] == unit, "uncertainty unit does not match metric")
            valid, undefined = item["valid_replicates"], item["undefined_replicates"]
            _integer(valid, "valid_replicates")
            _integer(undefined, "undefined_replicates")
            _require(valid + undefined == metadata["performed_repetitions"], "replicate counts do not reconcile")
            minimum = min(support.values())
            _require(type(item["few_games"]) is bool and item["few_games"] == (minimum < 20), "incorrect few_games flag")
            required_status = ("undefined_estimate" if minimum == 0 else "insufficient_games" if minimum < 5 else
                               "too_few_valid_replicates" if valid < ceil(0.95 * metadata["performed_repetitions"]) else None)
            status, bounds = item["status"], item["interval"]
            _require(status == required_status if required_status else status in ("ok", "degenerate_interval"),
                     "uncertainty status disagrees with support/validity")
            if minimum == 0:
                _require(valid == 0, "undefined estimate cannot have valid replicates")
            if status == "ok":
                _object(bounds, "interval")
                _number(bounds["lower"], "lower interval bound")
                _number(bounds["upper"], "upper interval bound")
                _require(bounds["lower"] < bounds["upper"] and not isclose(
                    bounds["lower"], bounds["upper"], rel_tol=1e-12, abs_tol=1e-12), "invalid interval bounds")
                if index != 2:
                    lower, upper = (-100, 100) if name == "difference" else (0, 1)
                    _require(lower <= bounds["lower"] <= bounds["upper"] <= upper, "rate interval outside unit range")
            else:
                _require(bounds is None, "withheld interval must be null")


def validate_report(report: dict) -> None:
    """Reject unsupported or internally inconsistent fields before rendering any text.

    This checks the consumed contract, not source authenticity, raw play identities,
    EPA sums, or the statistical calibration of supplied bootstrap distributions.
    """
    try:
        _json_value(report)
        _object(report, "report")
        _require(type(report["schema_version"]) is int and report["schema_version"] == 2, "requires report schema_version 2")
        cohort, source = report["cohort"], report["source"]
        _object(cohort, "cohort")
        _object(source, "source")
        _text(source["label"], "source.label")
        _require(isinstance(source["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", source["sha256"]),
                 "source.sha256 must be a lowercase SHA-256 fingerprint")
        _text(cohort["team"], "cohort.team")
        _require(re.fullmatch(r"[A-Z]{2,3}", cohort["team"]), "cohort.team must be an uppercase team abbreviation")
        _require(cohort["side"] in ("offense", "defense"), "cohort.side must be offense or defense")
        for key in ("season", "before_week_exclusive", "minimum_plays_warning"):
            _integer(cohort[key], key, 1)
        _require(1999 <= cohort["season"] <= 9999 and cohort["before_week_exclusive"] <= 23, "invalid season/week window")
        _require(cohort["season_type"] in ("REG", "POST"), "season_type must be REG or POST")
        _contexts(cohort)
        context = report["metric_context"]
        _require(context["perspective"] == "offense" and context["success_condition"] == "epa > 0"
                 and context["interpretation"] == ("allowed" if cohort["side"] == "defense" else "produced"),
                 "metric_context disagrees with role or metric contract")
        _object(report["data_quality"], "data_quality")
        _warnings(report["warnings"])
        if "snapshot" in source:
            snapshot = source["snapshot"]
            _object(snapshot, "source.snapshot")
            _require(type(snapshot["schema_version"]) is int and snapshot["schema_version"] == 1,
                     "unsupported snapshot manifest version")
            _require(snapshot["season"] == cohort["season"], "snapshot season does not match cohort")
            _require(snapshot["decoded_csv"]["sha256"] == source["sha256"], "snapshot decoded hash mismatch")
            for key in ("archive", "decoded_csv"):
                _integer(snapshot[key]["size_bytes"], key + " size", 1)
                _require(isinstance(snapshot[key]["sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", snapshot[key]["sha256"]),
                         "invalid snapshot fingerprint")
            _text(snapshot["retrieved_at_utc"], "retrieved_at_utc")
            for key in ("identifier", "attribution", "url", "source_url", "modifications"):
                _text(snapshot["license"][key], "license." + key)
            for key in ("download_url", "asset_name", "asset_updated_at_utc"):
                _text(snapshot["source"][key], "snapshot.source." + key)
        threshold = cohort["minimum_plays_warning"]
        selected = _situations(report["situations"])
        for row in [report["overall"], *selected.values()]:
            _metrics(row, threshold)
        _require(all(row["plays"] > 0 for row in selected.values()), "selected situations must contain observed plays")
        for key in set(COUNTS) - {"games"}:
            _require(sum(row[key] for row in selected.values()) == report["overall"][key], "selected situation counts do not reconcile")
        baseline = None
        comparison = report.get("league_comparison")
        if "league_comparison" in report:
            _object(comparison, "league_comparison")
            _require(comparison["cohort"] == {k: v for k, v in cohort.items() if k != "team"}, "baseline cohort does not match selected cohort")
            population = comparison["population"]
            expected = {"scope": "available_source_only", "weighting": "pooled_plays", "excluded_team": cohort["team"],
                        "side": cohort["side"], "team_field": "posteam" if cohort["side"] == "offense" else "defteam"}
            _require(all(population[k] == v for k, v in expected.items()), "unsupported baseline population")
            teams = population["teams"]
            _require(type(teams) is list and all(isinstance(v, str) for v in teams), "baseline teams must be text list")
            _integer(population["team_count"], "team_count")
            _require(len(set(teams)) == len(teams) == population["team_count"] and cohort["team"] not in teams,
                     "baseline team coverage is inconsistent")
            _require((len(teams) == 0) == (comparison["overall"]["plays"] == 0)
                     and len(teams) <= comparison["overall"]["plays"], "baseline team count cannot match its plays")
            _integer(population["shared_games_with_selected"], "shared games")
            _require(population["shared_games_with_selected"] <= min(report["overall"]["games"], comparison["overall"]["games"]),
                     "shared game count exceeds available games")
            _require(comparison["difference_convention"] == "selected_minus_baseline"
                     and comparison["situation_scope"] == "selected_team_observed_buckets", "unsupported comparison convention")
            _object(comparison["data_quality"], "baseline data_quality")
            _warnings(comparison["warnings"])
            baseline = _situations(comparison["situations"])
            _require(baseline.keys() == selected.keys(), "baseline situation keys do not match selected situations")
            for key in [None, *selected]:
                left = report["overall"] if key is None else selected[key]
                right = comparison["overall"] if key is None else baseline[key]["baseline"]
                difference = comparison["overall_difference"] if key is None else baseline[key]["difference"]
                _metrics(right, threshold)
                _difference(difference, left, right)
        _quality(report, cohort, comparison)
        if "uncertainty" in report:
            uncertainty = report["uncertainty"]
            _object(uncertainty, "uncertainty")
            expected = {"method": "game_cluster_percentile_v1", "nominal_level": 0.95, "minimum_support_games": 5,
                        "few_games_warning_below": 20, "minimum_valid_fraction": 0.95, "resampling_unit": "game_id",
                        "random_generator": "python_random.Random.randrange", "quantile_method": "linear_n_minus_1",
                        "resampling_population": "selected" if comparison is None else "selected_and_baseline_union"}
            _require(all(uncertainty[k] == v for k, v in expected.items()), "unsupported uncertainty method or metadata")
            _require(type(uncertainty["shared_game_weights"]) is bool
                     and uncertainty["shared_game_weights"] == (comparison is not None), "invalid shared-game weights flag")
            _integer(uncertainty["seed"], "seed")
            validate_bootstrap(uncertainty["repetitions"], uncertainty["seed"])
            games = report["overall"]["games"]
            if comparison is not None:
                games += comparison["overall"]["games"] - comparison["population"]["shared_games_with_selected"]
            _integer(uncertainty["resampling_games"], "resampling_games")
            _integer(uncertainty["performed_repetitions"], "performed_repetitions")
            _require(uncertainty["resampling_games"] == games and uncertainty["performed_repetitions"] == (
                uncertainty["repetitions"] if games else 0), "resampling frame/count does not match cohort")
            _warnings(uncertainty["warnings"])
            intervals = _situations(uncertainty["situations"])
            _require(intervals.keys() == selected.keys(), "uncertainty situation keys do not match selected situations")
            for key in [None, *selected]:
                populations = {"selected": report["overall"] if key is None else selected[key]}
                if comparison is not None:
                    populations["baseline"] = comparison["overall"] if key is None else baseline[key]["baseline"]
                _uncertainty_row(uncertainty["overall"] if key is None else intervals[key], populations, uncertainty)
    except (KeyError, TypeError, AttributeError, OverflowError, RecursionError) as exc:
        raise ValueError(f"invalid report structure: {exc}") from exc


def canonical_report(report: dict) -> str:
    validate_report(report)
    return json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
