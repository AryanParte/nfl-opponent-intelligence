"""Shared descriptive summaries of validated eligible plays."""

from math import fsum

from .pbp import Play


def metric_difference(selected: float | None, baseline: float | None, *, scale: int = 1) -> float | None:
    """Selected minus baseline; an undefined estimate cannot become zero."""
    return None if selected is None or baseline is None else (selected - baseline) * scale


def summarize_plays(plays: list[Play], minimum_plays: int) -> dict:
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
