"""Offline FTN/PBP cardinality and encoding coverage; no serving enrichment."""

import argparse
from collections import Counter, defaultdict
import csv
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path

from opponent_intelligence.ingestion import _read_snapshot
from opponent_intelligence.pbp import DataValidationError, _load_csv_bytes
from opponent_intelligence.snapshots import MAX_DECODED_BYTES, SnapshotError
from validation import ftn_contract as contract, ftn_snapshot as snapshot


FLAGS = tuple(f for f in contract.FIELDS if f.startswith("is_"))
COUNTS = ("n_offense_backfield", "n_defense_box", "n_blitzers", "n_pass_rushers")
FIELDS = (*contract.CODE_DOMAINS, *COUNTS, *FLAGS)
ISSUES = ("absent_column", "missing_value", "unknown_code", "invalid_value")
STATES = ("unmatched", *ISSUES, "recognized_code", "integer_0_to_11",
          "literal_true", "literal_false")
STRATUM_COLUMNS = ("role", "team", "season_type", "week", "candidate", "plays",
                   "games", "matched_plays", "matched_games", "unmatched_plays", "field_issues")


def field_state(row, name):
    """Encoding only: recognized/false/zero does NOT establish applicability."""
    if row is None:
        return "unmatched"
    if name not in row:
        return "absent_column"
    value = row[name]
    if value in contract.MISSING:
        return "missing_value"
    if name in contract.CODE_DOMAINS:
        return "recognized_code" if value in contract.CODE_DOMAINS[name] else "unknown_code"
    if name in COUNTS:
        number = contract._integer(value)
        return "integer_0_to_11" if number is not None and number <= 11 else "invalid_value"
    return {"TRUE": "literal_true", "FALSE": "literal_false"}.get(value, "invalid_value")


def _context(game, season, week):
    return (contract._game(game) is not None and season == snapshot.SEASON == int(game[:4])
            and week == int(game[5:7]) and 1 <= week <= 22)


def _ftn_index(raw):
    header, rows = contract.read_csv(raw)
    required = {"nflverse_game_id", "nflverse_play_id", "ftn_game_id", "ftn_play_id",
                "season", "week"}
    if not required <= set(header):
        raise SnapshotError("FTN join requires both key domains and season/week columns")
    index, ftn_keys = {}, set()
    for row in rows:
        game = contract._game(row["nflverse_game_id"])
        play = contract._integer(row["nflverse_play_id"])
        ftn_key = tuple(contract._integer(row[name]) for name in ("ftn_game_id", "ftn_play_id"))
        if game is None or play is None or None in ftn_key:
            raise SnapshotError("FTN join refuses missing/invalid key rows")
        key = (game, play)
        if key in index or ftn_key in ftn_keys:
            raise SnapshotError("FTN join refuses duplicate keys in either domain")
        if not _context(game, contract._integer(row["season"]), contract._integer(row["week"])):
            raise SnapshotError("FTN season/week disagree with the 2024 game key")
        index[key] = row
        ftn_keys.add(ftn_key)
    return index


def _raw_pbp_keys(raw):
    # The production loader validates the same bytes FIRST. This extra audit-only
    # index includes excluded rows, so they are not mislabeled as absent from PBP.
    keys = set()
    for row in csv.DictReader(StringIO(raw.decode("utf-8-sig"))):
        game = row["game_id"].strip()
        play = contract._integer(row["play_id"].strip())
        season, week = (contract._integer(row[f].strip()) for f in ("season", "week"))
        if play is None or not _context(game, season, week):
            raise SnapshotError("PBP join requires exact integer IDs and consistent 2024 game context")
        key = (game, play)
        if key in keys:
            raise SnapshotError("PBP join refuses duplicate keys")
        keys.add(key)
    return keys


def _summary(items):
    """Each item is one left-hand PBP play, with a row or explicit non-match."""
    fields = {name: dict.fromkeys(STATES, 0) for name in FIELDS}
    games, matched_games = set(), set()
    matched = 0
    for play, row in items:
        games.add(play.game_id)
        if row is not None:
            matched += 1
            matched_games.add(play.game_id)
        for name in FIELDS:
            fields[name][field_state(row, name)] += 1
    return {"plays": len(items), "games": len(games), "matched_plays": matched,
            "matched_games": len(matched_games), "unmatched_plays": len(items) - matched,
            "fields": fields}


def compare(pbp_raw, ftn_raw):
    """Audit supplied bytes; CLI audit() additionally requires verified manifests."""
    if not pbp_raw or len(pbp_raw) > MAX_DECODED_BYTES:
        raise SnapshotError("empty or oversized PBP audit input")
    # Reuse the actual eligibility, exclusions, dropback and missing-EPA policy.
    dataset = _load_csv_bytes(pbp_raw, expected_season=snapshot.SEASON)
    pbp_keys = _raw_pbp_keys(pbp_raw)
    ftn = _ftn_index(ftn_raw)
    eligible = {(p.game_id, p.play_id) for p in dataset.plays}
    left = [(p, ftn.get((p.game_id, p.play_id))) for p in dataset.plays]
    strata = defaultdict(list)
    for play, row in left:
        candidate = "pass" if play.dropback else "run"
        for role, team in (("offense", play.offense), ("defense", play.defense)):
            strata[(role, team, play.season_type, play.week, candidate)].append((play, row))
    stratum_rows = []
    for key, items in sorted(strata.items()):
        summary = _summary(items)
        # Sparse issues are counts of FIELD states, never imputed values. Full
        # encoding partitions are retained overall and for each candidate below.
        issues = {f: {state: n for state, n in summary["fields"][f].items()
                      if state in ISSUES and n} for f in FIELDS}
        issues = {f: counts for f, counts in issues.items() if counts}
        stratum_rows.append([*key, *(summary[f] for f in STRATUM_COLUMNS[5:-1]), issues])
    excluded_ftn = ftn.keys() & (pbp_keys - eligible)
    orphan_ftn = ftn.keys() - pbp_keys
    return {
        "parsed_sha256": {"pbp_csv": sha256(pbp_raw).hexdigest(),
                          "ftn_csv": sha256(ftn_raw).hexdigest()},
        "join": {
            "cardinality": "one-to-zero-or-one FTN row per eligible PBP play",
            "pbp_raw_rows": dataset.input_rows, "ftn_raw_rows": len(ftn),
            "pbp_exclusions": dict(sorted(dataset.exclusions.items())),
            "eligible_pbp_rows": len(left), "left_join_rows": len(left),
            "raw_pbp_rows_without_ftn": len(pbp_keys - ftn.keys()),
            "ftn_rows_matching_eligible_pbp": len(ftn.keys() & eligible),
            "ftn_rows_matching_excluded_pbp": len(excluded_ftn),
            "ftn_rows_without_pbp": len(orphan_ftn),
        },
        "overall": _summary(left),
        "by_candidate": {candidate: _summary([(p, r) for p, r in left if p.dropback == dropback])
                         for candidate, dropback in (("run", False), ("pass", True))},
        "outside_eligible_pbp": {
            label: {name: dict(sorted(Counter(field_state(ftn[key], name) for key in keys).items()))
                    for name in FIELDS}
            for label, keys in (("matching_excluded_pbp", excluded_ftn), ("without_pbp", orphan_ftn))
        },
        "stratum_columns": list(STRATUM_COLUMNS), "strata": stratum_rows,
    }


def audit(pbp_directory, ftn_directory):
    pbp_raw, pbp_manifest = _read_snapshot(pbp_directory)
    if pbp_manifest["season"] != snapshot.SEASON:
        raise SnapshotError("FTN coverage audit is limited to 2024")
    ftn_manifest = snapshot.verify(ftn_directory)
    ftn_raw = snapshot.read_csv(ftn_directory)
    return {
        "schema_version": 1, "scope": "offline 2024 REG+POST FTN/PBP encoding coverage",
        "source_manifests": {"pbp": pbp_manifest, "ftn": ftn_manifest},
        **compare(pbp_raw, ftn_raw),
        "charting_accuracy_validated": False, "field_applicability_validated": False,
        "historical_row_availability_verified": False, "play_families_approved": [],
        "receipt_license": {
            "identifier": "CC-BY-SA-4.0", "url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "attribution": "FTN Data via nflverse; nflverse play-by-play data (CC BY 4.0)",
            "modifications": "Joined aggregate coverage/encoding counts; no row-level redistribution.",
        },
        "limitations": [
            "Retrospective 2024 REG+POST snapshot comparison, not a pregame feature replay.",
            "Pass means dropback including sacks/scrambles; defense groups describe opponent offense.",
            "Unmatched plays remain in every denominator; missing EPA never removes a coverage row.",
            "Field states partition eligible plays, not applicable/observed-feature denominators.",
            "Recognized codes, literal FALSE and numeric zero do not prove applicability or accuracy.",
            "Unknown codes are retained; malformed encodings are counted, never coerced or imputed.",
            "Strata contain observed groups only; omitted groups are not a complete schedule audit.",
            "Source extraction/update/retrieval times do not establish first public availability.",
            "No motion, RPO, play-action or other feature rates or enriched reports are approved.",
        ],
    }


def encode(report):
    """Keep a standard JSON receipt reviewable: one compact line per stratum."""
    summary = {key: value for key, value in report.items() if key != "strata"}
    prefix = json.dumps(summary, indent=2, allow_nan=False)[:-2]
    rows = ",\n".join("    " + json.dumps(row, separators=(",", ":"), allow_nan=False)
                      for row in report["strata"])
    return prefix + ',\n  "strata": [\n' + rows + '\n  ]\n}\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pbp-snapshot", type=Path, required=True)
    parser.add_argument("--ftn-snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="create a new aggregate receipt; never overwrite")
    args = parser.parse_args()
    try:
        encoded = encode(audit(args.pbp_snapshot, args.ftn_snapshot))
        if args.output:
            with args.output.open("x", encoding="utf-8") as handle:
                handle.write(encoded)
        else:
            print(encoded, end="")
    except (SnapshotError, DataValidationError, OSError, UnicodeError, csv.Error) as exc:
        parser.exit(1, f"FTN coverage audit failed: {exc}\n")


if __name__ == "__main__":
    main()
