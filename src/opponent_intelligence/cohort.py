"""Shared selection for Scout and offline decision evidence; no statistical formulas."""

from .pbp import Dataset, Play, _team


PERIODS = ("Q1", "Q2", "Q3", "Q4", "OT")


def select_population(
    dataset: Dataset, *, team: str, season: int, before_week: int,
    side: str = "offense", season_type: str = "REG",
) -> tuple[list[Play], list[Play]]:
    """Return the temporal population and its selected team/role subset."""
    if not isinstance(team, str):
        raise ValueError("team must be an uppercase team abbreviation")
    _team(team, "team")
    if side not in ("offense", "defense"):
        raise ValueError("side must be offense or defense")
    for name, value in (("season", season), ("before_week", before_week)):
        if type(value) is not int:
            raise ValueError(f"{name} must be an integer")
    if not 1999 <= season <= 9999 or not 1 <= before_week <= 23:
        raise ValueError("season must be 1999..9999 and before_week must be 1..23")
    if season_type not in ("REG", "POST"):
        raise ValueError("season_type must be REG or POST")
    if dataset.source_manifest is not None and season != dataset.source_manifest["season"]:
        raise ValueError("requested season differs from snapshot manifest")
    temporal = [play for play in dataset.plays if (
        play.season == season and play.season_type == season_type and play.week < before_week
    )]
    role_field = "offense" if side == "offense" else "defense"
    return temporal, [play for play in temporal if getattr(play, role_field) == team]


def context_filters(
    dataset: Dataset, *, yardline_min: float | None = None, yardline_max: float | None = None,
    score_min: int | None = None, score_max: int | None = None,
    period: str | None = None, clock_min: int | None = None, clock_max: int | None = None,
) -> dict:
    """Validate optional pre-play bounds, retaining absence versus missingness."""
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
    period_context = None
    if period is not None:
        if period not in PERIODS:
            raise ValueError("period must be Q1, Q2, Q3, Q4, or OT")
        if "qtr" not in dataset.optional_columns:
            raise ValueError("period filtering requires the qtr source column")
        period_lower = 5 if period == "OT" else int(period[1])
        period_upper = None if period == "OT" else period_lower
        period_context = {"field": "qtr", "label": period,
                          "minimum_inclusive": period_lower, "maximum_inclusive": period_upper,
                          "missing_policy": "exclude"}
    clock_context = None
    if clock_min is not None or clock_max is not None:
        if period is None:
            raise ValueError("clock filtering requires an explicit period (Q1..Q4 or OT)")
        for name, value in (("clock_min", clock_min), ("clock_max", clock_max)):
            if value is not None and (type(value) is not int or not 0 <= value <= 900):
                raise ValueError(f"{name} must be an integer number of seconds in 0..900")
        clock_lower = 0 if clock_min is None else clock_min
        clock_upper = 900 if clock_max is None else clock_max
        if clock_lower > clock_upper:
            raise ValueError("clock_min must not exceed clock_max")
        if "quarter_seconds_remaining" not in dataset.optional_columns:
            raise ValueError("clock filtering requires the quarter_seconds_remaining source column")
        clock_context = {"field": "quarter_seconds_remaining", "minimum_inclusive": clock_lower,
                         "maximum_inclusive": clock_upper, "unit": "seconds", "timing": "pre_play",
                         "missing_policy": "exclude"}
    return {name: context for name, context in (
        ("field_position", field_position), ("score_differential", score_context),
        ("period", period_context), ("clock", clock_context),
    ) if context is not None}


def filter_context(plays: list[Play], contexts: dict) -> tuple[list[Play], dict]:
    """Apply the same ordered, validated bounds to either comparison population."""
    quality = {}
    for name, context in contexts.items():
        field = context["field"]
        lower, upper = context["minimum_inclusive"], context["maximum_inclusive"]
        before = len(plays)
        known = [play for play in plays if getattr(play, field) is not None]
        selected = [play for play in known
                    if (lower is None or getattr(play, field) >= lower)
                    and (upper is None or getattr(play, field) <= upper)]
        quality[name + "_filter"] = {
            "plays_before_filter": before, "missing_" + field: before - len(known),
            "outside_period" if name == "period" else "outside_range": len(known) - len(selected),
            "plays_after_filter": len(selected),
        }
        plays = selected
    return plays, quality
