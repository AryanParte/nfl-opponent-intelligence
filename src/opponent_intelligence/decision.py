"""Offline, offense-only Run/Pass evidence. No ranking, model, API or IO."""

from copy import deepcopy
from dataclasses import dataclass

from .cohort import context_filters, filter_context, select_population
from .metrics import summarize_plays
from .pbp import Dataset


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
    candidates = []
    for name, dropback, label in (("run", False, "Run (non-dropback)"),
                                  ("pass", True, "Pass (dropback, including sacks/scrambles)")):
        plays = [play for play in selected if play.dropback == dropback]
        metrics = summarize_plays(plays, request.minimum_plays)
        if not selected:
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
            "frequency": len(plays) / len(selected) if selected else None,
            "frequency_denominator": len(selected),
            "availability": {"frequency": "available" if selected else "empty_cohort",
                             "outcomes": outcome_state},
        })
    source = {"label": source_label, "sha256": dataset.source_sha256}
    if dataset.source_manifest is not None:
        source["snapshot"] = deepcopy(dataset.source_manifest)
    warnings = [
        "Observed run/dropback categories are not verified intended calls; sacks and scrambles are Pass.",
        "Only eligible run/pass plays are counted; not every attempted call or fourth-down option is represented.",
        "Descriptive associations are not causal effects, guaranteed future performance or coaching recommendations.",
        "Week filtering does not reconstruct historical source availability or EPA model training.",
        "Small-sample flags are count warnings, not validated reliability or ranking thresholds.",
        "League baselines, candidate uncertainty, opponent adjustment and EP/WP action values are not implemented here.",
    ]
    if not selected:
        warnings.append("No matching plays; no widening or fallback. Frequencies and outcomes are null.")
    if any(candidate["missing_epa"] for candidate in candidates):
        warnings.append("Missing EPA changes only candidate EPA/success denominators, not call frequency.")
    for name, context in contexts.items():
        stage = quality[name + "_filter"]
        if stage["missing_" + context["field"]]:
            warnings.append(f"{name} filter excluded {stage['missing_' + context['field']]} of "
                            f"{stage['plays_before_filter']} surviving plays with missing "
                            f"{context['field']}; no imputation.")
    return {
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
        "comparison": {"status": "insufficient_evidence", "preferred_candidate": None,
                       "reason": "candidate_comparison_not_validated"},
        "warnings": warnings,
    }
