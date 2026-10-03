"""Descriptive team cohorts; all metrics retain the offense's perspective."""

from collections import defaultdict
from copy import deepcopy
from math import fsum

from .pbp import Dataset, Play, _team


def _metrics(plays: list[Play], minimum_plays: int) -> dict:
    observed_epa = [play.epa for play in plays if play.epa is not None]
    count = len(plays)
    epa_count = len(observed_epa)
    dropbacks = sum(play.dropback for play in plays)
    return {
        "plays": count,
        "games": len({play.game_id for play in plays}),
        "dropbacks": dropbacks,
        "designed_runs": count - dropbacks,
        "dropback_rate": dropbacks / count if count else None,
        "epa_observations": epa_count,
        "missing_epa": count - epa_count,
        "epa_per_play": fsum(observed_epa) / epa_count if epa_count else None,
        "success_rate": sum(value > 0 for value in observed_epa) / epa_count if epa_count else None,
        "small_sample": count < minimum_plays,
        "small_epa_sample": epa_count < minimum_plays,
    }


def build_report(
    dataset: Dataset,
    *,
    team: str,
    season: int,
    before_week: int,
    side: str = "offense",
    season_type: str = "REG",
    minimum_plays: int = 30,
    yardline_min: float | None = None,
    yardline_max: float | None = None,
    score_min: int | None = None,
    score_max: int | None = None,
    source_label: str,
) -> dict:
    """Select a team's offense or defense, season/type, and weeks < before_week.

    Selecting defense changes the team predicate, not EPA signs or denominators.
    Optional pre-play position and score bounds retain the offense's perspective.
    Filters run in fixed order: team/time, field position, then score differential.
    The week boundary prevents including target-week outcomes. It cannot ensure
    historical availability of subsequently revised upstream values.
    """
    _team(team, "team")
    if side not in ("offense", "defense"):
        raise ValueError("side must be offense or defense")
    for name, value in (("season", season), ("before_week", before_week), ("minimum_plays", minimum_plays)):
        if type(value) is not int:
            raise ValueError(f"{name} must be an integer")
    if not 1999 <= season <= 9999 or not 1 <= before_week <= 23:
        raise ValueError("season must be 1999..9999 and before_week must be 1..23")
    if season_type not in {"REG", "POST"} or minimum_plays < 1:
        raise ValueError("season_type must be REG/POST and minimum_plays must be positive")
    if not source_label.strip():
        raise ValueError("source_label must describe the input data")
    if dataset.source_manifest is not None and season != dataset.source_manifest["season"]:
        raise ValueError("requested season differs from snapshot manifest")
    field_position = None
    if yardline_min is not None or yardline_max is not None:
        for name, value in (("yardline_min", yardline_min), ("yardline_max", yardline_max)):
            if value is not None and (type(value) not in (int, float) or not 0 <= value <= 100):
                raise ValueError(f"{name} must be a finite number in 0..100")
        lower = 0.0 if yardline_min is None else float(yardline_min)
        upper = 100.0 if yardline_max is None else float(yardline_max)
        if lower > upper:
            raise ValueError("yardline_min must not exceed yardline_max")
        if "yardline_100" not in dataset.optional_columns:
            raise ValueError("field-position filtering requires the yardline_100 source column")
        field_position = {"field": "yardline_100", "minimum_inclusive": lower,
                          "maximum_inclusive": upper, "perspective": "offense",
                          "missing_policy": "exclude"}
    score_context = None
    if score_min is not None or score_max is not None:
        for name, value in (("score_min", score_min), ("score_max", score_max)):
            if value is not None and type(value) is not int:
                raise ValueError(f"{name} must be an integer number of points")
        if score_min is not None and score_max is not None and score_min > score_max:
            raise ValueError("score_min must not exceed score_max")
        if "score_differential" not in dataset.optional_columns:
            raise ValueError("score filtering requires the score_differential source column")
        score_context = {"field": "score_differential", "minimum_inclusive": score_min,
                         "maximum_inclusive": score_max, "perspective": "offense",
                         "missing_policy": "exclude"}
    selected = [play for play in dataset.plays if (
        (play.offense if side == "offense" else play.defense) == team and play.season == season
        and play.season_type == season_type and play.week < before_week
    )]
    field_quality = None
    if field_position is not None:
        before_count = len(selected)
        missing_count = sum(play.yardline_100 is None for play in selected)
        selected = [play for play in selected if play.yardline_100 is not None
                    and lower <= play.yardline_100 <= upper]
        field_quality = {"plays_before_filter": before_count,
                         "missing_yardline_100": missing_count,
                         "outside_range": before_count - missing_count - len(selected),
                         "plays_after_filter": len(selected)}
    score_quality = None
    if score_context is not None:
        # Count only plays surviving the previous filter, so overlapping missing
        # context and out-of-range values never create duplicate removals.
        before_count = len(selected)
        missing_count = sum(play.score_differential is None for play in selected)
        selected = [play for play in selected if play.score_differential is not None
                    and (score_min is None or play.score_differential >= score_min)
                    and (score_max is None or play.score_differential <= score_max)]
        score_quality = {"plays_before_filter": before_count,
                         "missing_score_differential": missing_count,
                         "outside_range": before_count - missing_count - len(selected),
                         "plays_after_filter": len(selected)}
    groups: dict[tuple[int, str], list[Play]] = defaultdict(list)
    for play in selected:
        distance = "short" if play.yards_to_go <= 3 else "medium" if play.yards_to_go <= 6 else "long"
        groups[(play.down, distance)].append(play)
    warnings = [
        "Descriptive completed-play tendencies; no opponent adjustment or causal claims.",
        "Week filtering does not reconstruct historical source availability or EPA model training.",
    ]
    if side == "defense":
        warnings.append("Defense view describes opposing offenses: EPA is not sign-flipped; "
                        "success still means offensive EPA > 0, not a defensive stop rate.")
    if not selected:
        warnings.append("No eligible plays match this cohort; rates are null, not zero.")
    if any(play.epa is None for play in selected):
        warnings.append("Missing EPA is excluded only from EPA and success-rate denominators.")
    if field_quality is not None and field_quality["missing_yardline_100"]:
        warnings.append("Missing yardline_100 excluded by field-position filter: "
                        f"{field_quality['missing_yardline_100']} of "
                        f"{field_quality['plays_before_filter']} base-cohort plays; no imputation.")
    if score_quality is not None and score_quality["missing_score_differential"]:
        warnings.append("Missing score_differential excluded by score filter: "
                        f"{score_quality['missing_score_differential']} of "
                        f"{score_quality['plays_before_filter']} plays after team/time and any "
                        "field-position filter; no imputation.")
    distance_order = {"short": 0, "medium": 1, "long": 2}
    source = {"label": source_label, "sha256": dataset.source_sha256}
    if dataset.source_manifest is not None:
        source["snapshot"] = deepcopy(dataset.source_manifest)
    report = {
        "schema_version": 2,
        "source": source,
        "cohort": {"team": team, "side": side, "season": season, "season_type": season_type,
                   "before_week_exclusive": before_week, "minimum_plays_warning": minimum_plays},
        "metric_context": {"perspective": "offense",
                           "interpretation": "allowed" if side == "defense" else "produced",
                           "success_condition": "epa > 0"},
        "data_quality": {"input_rows": dataset.input_rows,
                         "eligible_rows_all_teams": len(dataset.plays),
                         "excluded_rows_by_reason": dict(sorted(dataset.exclusions.items())),
                         "eligible_rows_outside_cohort": len(dataset.plays) - len(selected)},
        "overall": _metrics(selected, minimum_plays),
        "situations": [
            {"down": down, "distance": distance, **_metrics(plays, minimum_plays)}
            for (down, distance), plays in sorted(
                groups.items(), key=lambda item: (item[0][0], distance_order[item[0][1]])
            )
        ],
        "warnings": warnings,
    }
    if field_position is not None:
        report["cohort"]["field_position"] = field_position
        report["data_quality"]["field_position_filter"] = field_quality
    if score_context is not None:
        report["cohort"]["score_differential"] = score_context
        report["data_quality"]["score_differential_filter"] = score_quality
        report["data_quality"]["filter_order"] = (
            (["field_position"] if field_position is not None else []) + ["score_differential"]
        )
    return report
