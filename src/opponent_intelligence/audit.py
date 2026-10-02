"""Reconcile a verified snapshot's raw rows with the analytical eligibility policy."""

import argparse
from collections import Counter, defaultdict
import csv
from io import StringIO
import json
from pathlib import Path
import sys

from .ingestion import _read_snapshot, _snapshot_dataset
from .pbp import DataValidationError, MISSING, REQUIRED_COLUMNS, _integer


def audit_snapshot(directory: Path) -> dict:
    """Validate the adapter, then independently enumerate eligible raw identities.

    Coverage counts describe this artifact, not agreement with an external game
    schedule. Raw missingness covers required and recognized optional fields;
    optional-field missingness is also counted separately on eligible plays.
    """
    raw, manifest = _read_snapshot(directory)
    dataset = _snapshot_dataset(raw, manifest)
    reader = csv.DictReader(StringIO(raw.decode("utf-8-sig")), strict=True)
    columns = reader.fieldnames
    missing = Counter({column: 0 for column in REQUIRED_COLUMNS})
    optional_missing = Counter({column: 0 for column in dataset.optional_columns})
    types: Counter[str] = Counter()
    coverage_rows: Counter[tuple[str, int]] = Counter()
    coverage_games: dict[tuple[str, int], set[str]] = defaultdict(set)
    game_context: dict[str, tuple[str, int]] = {}
    raw_eligible: set[tuple[str, int]] = set()
    for row in reader:
        values = {key: value.strip() for key, value in row.items()}
        for column in REQUIRED_COLUMNS:
            missing[column] += values[column].upper() in MISSING
        for column in dataset.optional_columns:
            optional_missing[column] += values[column].upper() in MISSING
        kind = values["play_type"]
        types["<missing>" if kind.upper() in MISSING else kind] += 1
        try:
            season_type = values["season_type"]
            if season_type not in {"REG", "POST"}:
                raise DataValidationError("season_type must be REG or POST on every audited row")
            week = _integer(values["week"], "week", 1, 22)
            context = (season_type, week)
            game = values["game_id"]
            if game in game_context and game_context[game] != context:
                raise DataValidationError("game has conflicting season type or week")
            game_context[game] = context
            coverage_rows[context] += 1
            coverage_games[context].add(game)
            # Separate set-based reconciliation, not a call to the adapter's row
            # selection. Short-circuit special situations before unused flags.
            if kind in {"run", "pass"} and all(
                float(values[flag]) == 0
                for flag in ("two_point_attempt", "qb_kneel", "qb_spike")
            ):
                raw_eligible.add((game, int(float(values["play_id"]))))
        except DataValidationError as exc:
            raise DataValidationError(f"CSV line {reader.line_num}: {exc}") from exc
    parsed_keys = {(play.game_id, play.play_id) for play in dataset.plays}
    if raw_eligible != parsed_keys:
        raise DataValidationError("raw eligibility identities do not match analytical adapter")
    excluded = sum(dataset.exclusions.values())
    if dataset.input_rows != len(parsed_keys) + excluded:
        raise DataValidationError("input, eligible, and excluded rows do not reconcile")
    by_type = []
    for season_type in ("REG", "POST"):
        plays = [play for play in dataset.plays if play.season_type == season_type]
        games = {game for game, context in game_context.items() if context[0] == season_type}
        if not games:
            continue
        by_type.append({
            "season_type": season_type, "input_games": len(games),
            "eligible_games": len({play.game_id for play in plays}),
            "eligible_rows": len(plays), "dropbacks": sum(play.dropback for play in plays),
            "epa_observations": sum(play.epa is not None for play in plays),
            "offenses": sorted({play.offense for play in plays}),
        })
    return {
        "schema_version": 1,
        "source": {"sha256": dataset.source_sha256, "snapshot": manifest},
        "input": {
            "rows": dataset.input_rows, "column_count": len(columns),
            "required_column_missing_counts": dict(sorted(missing.items())),
            "optional_column_missing_counts": dict(sorted(optional_missing.items())),
            "play_type_counts": dict(sorted(types.items())),
            "coverage": [{"season_type": kind, "week": week,
                          "rows": coverage_rows[(kind, week)],
                          "games": len(coverage_games[(kind, week)])}
                         for kind, week in sorted(coverage_rows, key=lambda item: item[1])],
        },
        "adapter": {
            "eligible_rows": len(dataset.plays),
            "excluded_rows_by_reason": dict(sorted(dataset.exclusions.items())),
            "by_season_type": by_type,
            "optional_column_missing_counts": {
                column: sum(getattr(play, column) is None for play in dataset.plays)
                for column in dataset.optional_columns
            },
        },
        "reconciliation": {"raw_and_adapter_eligible_identities_match": True,
                           "accounted_rows": len(parsed_keys) + excluded,
                           "duplicate_play_keys": 0},
        "limits": [
            "Coverage is observed in this snapshot, not matched to an independent schedule.",
            "Validation covers required and recognized optional adapter fields, not every extra upstream column.",
            "Retrospective source revisions and EPA training may use later information.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit an explicit local NFL raw snapshot offline.")
    parser.add_argument("--snapshot", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        payload = json.dumps(audit_snapshot(args.snapshot), indent=2, sort_keys=True, allow_nan=False)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
