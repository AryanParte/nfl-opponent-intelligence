"""Offline raw-schema/key reconnaissance; never joins FTN to PBP or reports rates."""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import re

from opponent_intelligence.snapshots import SnapshotError
from validation import ftn_snapshot as snapshot


# Exact names in the pinned nflreadr dictionary, not inferred PBP aliases.
FIELDS = (
    "ftn_game_id", "nflverse_game_id", "season", "week", "ftn_play_id", "nflverse_play_id",
    "starting_hash", "qb_location", "n_offense_backfield", "n_defense_box", "is_no_huddle",
    "is_motion", "is_play_action", "is_screen_pass", "is_rpo", "is_trick_play",
    "is_qb_out_of_pocket", "is_interception_worthy", "is_throw_away", "read_thrown",
    "is_catchable_ball", "is_contested_ball", "is_created_reception", "is_drop", "is_qb_sneak",
    "n_blitzers", "n_pass_rushers", "is_qb_fault_sack", "date_pulled",
)
CODE_DOMAINS = {
    "starting_hash": {"L", "M", "R"}, "qb_location": {"U", "S", "P"},
    "read_thrown": {"0", "1", "2", "CHK", "DES", "SD"},  # 2024 only; 2022 differs.
}
MISSING = {"", "NA"}  # CSV blank/NA only; no truthiness, stripping or invented false.
MAX_BYTES = 16 * 1024 * 1024
MAX_ROWS = 100_000


def _integer(value):
    # Normalize documented numeric IDs exactly, without float rounding or aliases.
    if len(value) > 16 or re.fullmatch(r"[0-9]+(?:\.0+)?", value) is None:
        return None
    number = int(value.split(".")[0])
    return number if number <= 2**31 - 1 else None


def _game(value):
    if re.fullmatch(r"[0-9]{4}_[0-9]{2}_[A-Z]{2,3}_[A-Z]{2,3}", value) is None:
        return None
    return value


def _timestamp(value):
    # A source extraction timestamp, never a first-publication/available-at timestamp.
    if "T" not in value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.utcoffset() is None:
            return None
        return parsed.astimezone(timezone.utc).isoformat()
    except (ValueError, OverflowError):
        return None


def inventory(raw):
    """Audit bounded CSV bytes without interpreting flags as eligibility or truth."""
    if not raw or len(raw) > MAX_BYTES:
        raise SnapshotError("empty or oversized FTN audit input")
    try:
        reader = csv.reader(StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
        header = next(reader, [])
        if (not header or len(header) > 128 or any(not x or x != x.strip() for x in header)
                or len(header) != len(set(header))):
            raise SnapshotError("empty, duplicate or malformed CSV header")
        columns = {name: {"missing_rows": 0, "nonmissing_rows": 0} for name in header}
        flags = {name: {"true_rows": 0, "false_rows": 0, "unrecognized_rows": 0}
                 for name in FIELDS if name.startswith("is_") and name in columns}
        codes = {name: Counter() for name in CODE_DOMAINS if name in columns}
        key_specs = {
            "nflverse": (("nflverse_game_id", "nflverse_play_id"), (_game, _integer)),
            "ftn": (("ftn_game_id", "ftn_play_id"), (_integer, _integer)),
        }
        keys = {}
        counts = {}
        for name, (fields, _) in key_specs.items():
            present = all(field in columns for field in fields)
            keys[name] = {"columns": list(fields), "columns_present": present,
                          "counts": ({"missing_key_rows": 0, "invalid_key_rows": 0,
                                      "valid_key_rows": 0} if present else None)}
            counts[name] = Counter()
        dates = {"valid_rows": 0, "invalid_rows": 0, "minimum_utc": None, "maximum_utc": None}
        context_columns = all(f in columns for f in ("nflverse_game_id", "season", "week"))
        context = {"matching_rows": 0, "missing_rows": 0, "inconsistent_or_invalid_rows": 0}
        rows = 0
        for values in reader:
            rows += 1
            if rows > MAX_ROWS or len(values) != len(header):
                raise SnapshotError(f"row limit or ragged CSV at record {rows}")
            row = dict(zip(header, values))
            for name, value in row.items():
                columns[name]["missing_rows" if value in MISSING else "nonmissing_rows"] += 1
                if value in MISSING:
                    continue
                if name in flags:
                    flags[name][{"TRUE": "true_rows", "FALSE": "false_rows"}.get(
                        value, "unrecognized_rows")] += 1
                if name in codes:
                    # Emit only documented domain counts plus one unknown total;
                    # never leak arbitrary strings/row data into the aggregate receipt.
                    codes[name][value if value in CODE_DOMAINS[name] else "outside_documented_codes"] += 1
                if name == "date_pulled":
                    date = _timestamp(value)
                    dates["valid_rows" if date else "invalid_rows"] += 1
                    if date:
                        dates["minimum_utc"] = min(dates["minimum_utc"] or date, date)
                        dates["maximum_utc"] = max(dates["maximum_utc"] or date, date)
            for name, (fields, parsers) in key_specs.items():
                summary = keys[name]["counts"]
                if summary is None:
                    continue
                if any(row[field] in MISSING for field in fields):
                    summary["missing_key_rows"] += 1
                    continue
                parsed = tuple(parse(row[field]) for field, parse in zip(fields, parsers))
                if any(value is None for value in parsed):
                    summary["invalid_key_rows"] += 1
                else:
                    summary["valid_key_rows"] += 1
                    counts[name][parsed] += 1
            if context_columns:
                game, season, week = (row[f] for f in ("nflverse_game_id", "season", "week"))
                if any(v in MISSING for v in (game, season, week)):
                    context["missing_rows"] += 1
                elif (_game(game) and _integer(season) == snapshot.SEASON == int(game[:4])
                      and _integer(week) == int(game[5:7]) and 1 <= int(game[5:7]) <= 22):
                    context["matching_rows"] += 1
                else:
                    context["inconsistent_or_invalid_rows"] += 1
        for name, pairs in counts.items():
            summary = keys[name]["counts"]
            if summary is not None:
                summary.update({
                    "distinct_keys": len(pairs), "distinct_games": len({key[0] for key in pairs}),
                    "duplicate_key_groups": sum(n > 1 for n in pairs.values()),
                    "rows_in_duplicate_groups": sum(n for n in pairs.values() if n > 1),
                    "duplicate_excess_rows": sum(n - 1 for n in pairs.values()),
                })
        return {
            "raw_rows": rows, "header": header,
            "missing_documented_columns": sorted(set(FIELDS) - set(header)),
            "undocumented_columns": sorted(set(header) - set(FIELDS)),
            "columns": {name: {"column_present": name in columns,
                               "counts": columns.get(name)} for name in dict.fromkeys((*FIELDS, *header))},
            "logical_encodings": flags,
            "documented_codes": {name: {code: codes[name][code] for code in
                sorted(CODE_DOMAINS[name] | {"outside_documented_codes"})} for name in codes},
            "keys": keys, "game_season_week_consistency": context if context_columns else None,
            "source_extraction_time": dates if "date_pulled" in columns else None,
        }
    except (UnicodeError, csv.Error) as exc:
        raise SnapshotError("invalid UTF-8 or malformed FTN CSV") from exc


def audit(directory):
    manifest = snapshot.verify(directory)
    raw = snapshot.read_csv(directory)
    return {
        "schema_version": 1, "scope": "raw FTN 2024 schema and key reconnaissance only",
        "source_manifest": manifest,
        "parsed_csv_sha256": sha256(raw).hexdigest(),
        "inventory": inventory(raw),
        "join_to_pbp_performed": False, "charting_accuracy_validated": False,
        "historical_row_availability_verified": False, "play_families_approved": [],
        "receipt_license": {
            "identifier": "CC-BY-SA-4.0", "attribution": "FTN Data via nflverse",
            "url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "modifications": "Aggregate schema/key/encoding inventory; no row-level data redistributed.",
        },
        "limitations": [
            "Raw rows are not filtered by the PBP analytical eligibility policy; no rates computed.",
            "FALSE is a literal CSV value, not proof that a charted feature is applicable or observed.",
            "Nonmissing fields and valid key syntax do not establish charting accuracy or PBP coverage.",
            "Date pulled records FTN API extraction by nflverse, not first public or pregame availability.",
            "Unknown codes and duplicate/missing keys are not silently repaired or mapped to proxies.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="create a new aggregate receipt; never overwrite")
    args = parser.parse_args()
    try:
        report = audit(args.snapshot)
        encoded = json.dumps(report, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(encoded)
        else:
            print(encoded, end="")
    except (SnapshotError, OSError) as exc:
        parser.exit(1, f"FTN audit failed: {exc}\n")


if __name__ == "__main__":
    main()
