"""Descriptive team cohorts; all metrics retain the offense's perspective."""

from collections import defaultdict
from copy import deepcopy

from .cohort import PERIODS, context_filters, filter_context, select_population
from .metrics import summarize_plays
from .pbp import Dataset, Play
from .uncertainty import build_uncertainty, validate_bootstrap


def _group_situations(plays: list[Play]) -> dict[tuple[int, str], list[Play]]:
    groups: dict[tuple[int, str], list[Play]] = defaultdict(list)
    for play in plays:
        distance = "short" if play.yards_to_go <= 3 else "medium" if play.yards_to_go <= 6 else "long"
        groups[(play.down, distance)].append(play)
    return groups


def _differences(selected: dict, baseline: dict) -> dict:
    differences = {}
    for metric, output, scale in (("dropback_rate", "dropback_rate_pp", 100),
                                  ("success_rate", "success_rate_pp", 100),
                                  ("epa_per_play", "epa_per_play", 1)):
        left, right = selected[metric], baseline[metric]
        differences[output] = None if left is None or right is None else (left - right) * scale
    return differences


def _league_comparison(
    report: dict, selected: list[Play], others: list[Play], temporal_count: int,
    selected_base_count: int, contexts: dict, minimum_plays: int, role_field: str,
) -> dict:
    before_count = len(others)
    baseline, quality = filter_context(others, contexts)
    teams = sorted({getattr(play, role_field) for play in baseline})
    baseline_metrics = summarize_plays(baseline, minimum_plays)
    baseline_groups = _group_situations(baseline)
    situations = []
    # Only the selected team's observed buckets are compared; never fall back
    # to overall league values when a matching baseline bucket is unavailable.
    for situation in report["situations"]:
        key = (situation["down"], situation["distance"])
        metrics = summarize_plays(baseline_groups.get(key, []), minimum_plays)
        situations.append({"down": key[0], "distance": key[1], "baseline": metrics,
                           "difference": _differences(situation, metrics)})
    warnings = [
        "Baseline uses only available source plays; full league coverage is not certified.",
        "Pooled descriptive differences are not opponent adjustment or predictive validation.",
        "Overall context mixes may differ; compare matching down/distance rows, not a reweighted overall score.",
        "Plays within games are dependent; selected and baseline populations may share games and opponents.",
    ]
    if not baseline:
        warnings.append("No eligible baseline plays match; baseline rates and differences are null.")
    if any(play.epa is None for play in baseline):
        warnings.append("Missing baseline EPA affects only EPA and success-rate denominators.")
    for name, context in contexts.items():
        stage = quality[name + "_filter"]
        missing = stage["missing_" + context["field"]]
        if missing:
            warnings.append(f"Baseline {name} filter excluded {missing} of "
                            f"{stage['plays_before_filter']} surviving plays with missing "
                            f"{context['field']}; no imputation.")
    return {
        "population": {"scope": "available_source_only", "side": report["cohort"]["side"],
                       "excluded_team": report["cohort"]["team"],
                       "team_field": "posteam" if role_field == "offense" else "defteam",
                       "teams": teams, "team_count": len(teams), "weighting": "pooled_plays",
                       "shared_games_with_selected": len({p.game_id for p in selected}
                                                         & {p.game_id for p in baseline})},
        "cohort": deepcopy({key: value for key, value in report["cohort"].items() if key != "team"}),
        "difference_convention": "selected_minus_baseline",
        "situation_scope": "selected_team_observed_buckets",
        "data_quality": {"eligible_rows_same_season_type_before_week": temporal_count,
                         "excluded_selected_team_rows": selected_base_count,
                         "plays_before_context_filters": before_count,
                         "plays_after_context_filters": len(baseline),
                         "filter_order": list(contexts), **quality},
        "overall": baseline_metrics,
        "overall_difference": _differences(report["overall"], baseline_metrics),
        "situations": situations,
        "warnings": warnings,
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
    period: str | None = None,
    clock_min: int | None = None,
    clock_max: int | None = None,
    compare_league: bool = False,
    bootstrap_repetitions: int | None = None,
    bootstrap_seed: int | None = None,
    source_label: str,
) -> dict:
    """Select a team's offense or defense, season/type, and weeks < before_week.

    Selecting defense changes the team predicate, not EPA signs or denominators.
    Optional pre-play position and score bounds retain the offense's perspective.
    Filters run in fixed order: team/week, field position, score, period, clock.
    Clock bounds require a period; OT groups all overtime periods (qtr >= 5).
    The week boundary prevents including target-week outcomes. It cannot ensure
    historical availability of subsequently revised upstream values.
    """
    if type(compare_league) is not bool:
        raise ValueError("compare_league must be a boolean")
    effective_seed = validate_bootstrap(bootstrap_repetitions, bootstrap_seed)
    if type(minimum_plays) is not int:
        raise ValueError("minimum_plays must be an integer")
    if minimum_plays < 1:
        raise ValueError("minimum_plays must be positive")
    if not isinstance(source_label, str) or not source_label.strip():
        raise ValueError("source_label must describe the input data")
    temporal, selected_base = select_population(
        dataset, team=team, season=season, before_week=before_week, side=side, season_type=season_type,
    )
    contexts = context_filters(
        dataset, yardline_min=yardline_min, yardline_max=yardline_max,
        score_min=score_min, score_max=score_max, period=period, clock_min=clock_min, clock_max=clock_max,
    )
    role_field = "offense" if side == "offense" else "defense"
    selected, quality = filter_context(selected_base, contexts)
    field_position = contexts.get("field_position")
    score_context = contexts.get("score_differential")
    period_context = contexts.get("period")
    clock_context = contexts.get("clock")
    field_quality = quality.get("field_position_filter")
    score_quality = quality.get("score_differential_filter")
    period_quality = quality.get("period_filter")
    clock_quality = quality.get("clock_filter")
    groups = _group_situations(selected)
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
    if period_quality is not None and period_quality["missing_qtr"]:
        warnings.append("Missing qtr excluded by period filter: "
                        f"{period_quality['missing_qtr']} of {period_quality['plays_before_filter']} "
                        "plays after team/week and any field/score filters; no imputation.")
    if clock_quality is not None and clock_quality["missing_quarter_seconds_remaining"]:
        warnings.append("Missing quarter_seconds_remaining excluded by clock filter: "
                        f"{clock_quality['missing_quarter_seconds_remaining']} of "
                        f"{clock_quality['plays_before_filter']} plays after period selection "
                        "and any field/score filters; no imputation.")
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
        "overall": summarize_plays(selected, minimum_plays),
        "situations": [
            {"down": down, "distance": distance, **summarize_plays(plays, minimum_plays)}
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
    if period_context is not None:
        report["cohort"]["period"] = period_context
        report["data_quality"]["period_filter"] = period_quality
    if clock_context is not None:
        report["cohort"]["clock"] = clock_context
        report["data_quality"]["clock_filter"] = clock_quality
    if score_context is not None or period_context is not None:
        report["data_quality"]["filter_order"] = list(contexts)
    if compare_league:
        others = [play for play in temporal if getattr(play, role_field) != team]
        report["league_comparison"] = _league_comparison(
            report, selected, others, len(temporal), len(selected_base), contexts, minimum_plays, role_field,
        )
    if bootstrap_repetitions is not None:
        baseline_groups = None
        if compare_league:
            baseline, _ = filter_context(others, contexts)
            baseline_groups = _group_situations(baseline)
        report["uncertainty"] = build_uncertainty(
            groups, baseline_groups, repetitions=bootstrap_repetitions, seed=effective_seed,
        )
    return report
