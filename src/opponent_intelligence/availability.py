"""Offline personnel/motion field inventory, not a new analytical data contract."""

import argparse
from collections import Counter
import csv
from io import StringIO
import json
from pathlib import Path
import sys

from .ingestion import _read_snapshot, _snapshot_dataset
from .pbp import MISSING, _integer, _optional_integer


# Exact documented names only: never guess aliases or infer motion from text.
# See docs/PERSONNEL_MOTION.md for source definitions and the scope decision.
CANDIDATE_FIELDS = (
    "offense_personnel", "defense_personnel", "offense_formation",
    "offense_players", "defense_players", "offense_positions", "defense_positions",
    "is_motion", "is_play_action", "is_rpo", "is_no_huddle", "qb_location",
    "n_offense_backfield", "n_defense_box", "shotgun", "no_huddle",
    "desc", "pass_location", "run_location", "run_gap",
)
BINARY_CONTEXT_FIELDS = frozenset({"shotgun", "no_huddle"})


def _category(value: str, field: str) -> str:
    if value.upper() in MISSING:
        return "missing"
    if field not in BINARY_CONTEXT_FIELDS:
        return "observed"
    try:
        flag = _optional_integer(value, field, minimum=0, maximum=1)
    except ValueError:
        return "other"
    return "one" if flag == 1 else "zero"


def _summary(counts: Counter, rows: int, field: str) -> dict:
    missing = counts["missing"]
    observed = rows - missing
    result = {
        "status": "no_rows" if rows == 0 else "all_missing" if observed == 0 else "observed",
        "rows": rows, "non_missing": observed, "missing": missing,
    }
    if field in BINARY_CONTEXT_FIELDS:
        # "other" is non-missing but not a valid numeric 0/1. Do not turn it
        # into false or change the adapter's eligibility policy for this audit.
        result["binary_counts"] = {key: counts[key] for key in ("zero", "one", "other")}
    return result


def audit_availability(directory: Path) -> dict:
    """Inventory exact candidate names on verified raw and adapter-eligible rows.

    Counts describe the entire supplied season snapshot, not an as-of-week
    cohort. Non-missing text is not semantic validation or proof
    of charting coverage. Absent columns have null counts, never fabricated zeros.
    """
    raw, manifest = _read_snapshot(directory)
    dataset = _snapshot_dataset(raw, manifest)
    eligible_keys = {(play.game_id, play.play_id) for play in dataset.plays}
    reader = csv.DictReader(StringIO(raw.decode("utf-8-sig")), strict=True)
    columns = reader.fieldnames
    present = [field for field in CANDIDATE_FIELDS if field in columns]
    raw_counts = {field: Counter() for field in present}
    eligible_counts = {field: Counter() for field in present}
    raw_rows = eligible_rows = 0
    for row in reader:
        # The adapter already validated widths, identities, duplicate keys,
        # seasons and eligible fields on these same byte-verified CSV bytes.
        key = (row["game_id"].strip(), _integer(row["play_id"].strip(), "play_id", 0, 1_000_000))
        eligible = key in eligible_keys
        raw_rows += 1
        eligible_rows += eligible
        for field in present:
            category = _category(row[field].strip(), field)
            raw_counts[field][category] += 1
            if eligible:
                eligible_counts[field][category] += 1
    if raw_rows != dataset.input_rows or eligible_rows != len(eligible_keys):
        raise ValueError("availability counts do not reconcile with the adapter")
    return {
        "schema_version": 1,
        "audit": "personnel_motion_field_availability",
        "source": {"sha256": dataset.source_sha256, "snapshot": manifest},
        "scope": {
            "season": manifest["season"], "eligible_season_types": ["REG", "POST"],
            "week_cutoff": None, "column_count": len(columns),
            "raw_rows": raw_rows, "eligible_rows": eligible_rows,
            "excluded_rows_by_reason": dict(sorted(dataset.exclusions.items())),
            "missing_markers_case_insensitive": sorted(MISSING),
        },
        "fields": {
            field: {
                "column_present": field in present,
                "raw": _summary(raw_counts[field], raw_rows, field) if field in present else None,
                "eligible": _summary(eligible_counts[field], eligible_rows, field)
                if field in present else None,
            }
            for field in CANDIDATE_FIELDS
        },
        "limits": [
            "Only exact candidate names are inventoried; aliases and free text are not inferred.",
            "Non-missing counts are not semantic validation, charting coverage, or feature support.",
            "Shotgun, no-huddle, and play locations are not personnel or motion measurements.",
            "Raw counts include administrative and excluded plays; eligible counts use the current adapter.",
            "All weeks and REG/POST rows are audited; this is not a historically available feature set.",
            "No supplementary participation/charting dataset was downloaded, joined, or validated.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit personnel/motion field availability offline.")
    parser.add_argument("--snapshot", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        payload = json.dumps(audit_availability(args.snapshot), indent=2, sort_keys=True, allow_nan=False)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
