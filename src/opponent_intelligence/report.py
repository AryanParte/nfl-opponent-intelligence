"""Descriptive offense summaries with explicit cohorts and denominators."""

from collections import defaultdict
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
    season_type: str = "REG",
    minimum_plays: int = 30,
    source_label: str,
) -> dict:
    """Use only the requested offense/season/type and weeks < before_week.

    The week boundary prevents including target-week outcomes. It cannot ensure
    historical availability of subsequently revised upstream values.
    """
    _team(team, "team")
    for name, value in (("season", season), ("before_week", before_week), ("minimum_plays", minimum_plays)):
        if type(value) is not int:
            raise ValueError(f"{name} must be an integer")
    if not 1999 <= season <= 9999 or not 1 <= before_week <= 23:
        raise ValueError("season must be 1999..9999 and before_week must be 1..23")
    if season_type not in {"REG", "POST"} or minimum_plays < 1:
        raise ValueError("season_type must be REG/POST and minimum_plays must be positive")
    if not source_label.strip():
        raise ValueError("source_label must describe the input data")
    selected = [play for play in dataset.plays if (
        play.offense == team and play.season == season
        and play.season_type == season_type and play.week < before_week
    )]
    groups: dict[tuple[int, str], list[Play]] = defaultdict(list)
    for play in selected:
        distance = "short" if play.yards_to_go <= 3 else "medium" if play.yards_to_go <= 6 else "long"
        groups[(play.down, distance)].append(play)
    warnings = [
        "Descriptive completed-play tendencies; no opponent adjustment or causal claims.",
        "Week filtering does not reconstruct historical source availability or EPA model training.",
    ]
    if not selected:
        warnings.append("No eligible plays match this cohort; rates are null, not zero.")
    if any(play.epa is None for play in selected):
        warnings.append("Missing EPA is excluded only from EPA and success-rate denominators.")
    distance_order = {"short": 0, "medium": 1, "long": 2}
    return {
        "schema_version": 1,
        "source": {"label": source_label, "sha256": dataset.source_sha256},
        "cohort": {"offense": team, "season": season, "season_type": season_type,
                   "before_week_exclusive": before_week, "minimum_plays_warning": minimum_plays},
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
