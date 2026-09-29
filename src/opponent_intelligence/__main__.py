"""Run with python -m opponent_intelligence; JSON goes to stdout."""

import argparse
import csv
import json
from pathlib import Path
import sys

from .pbp import load_csv
from .report import build_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create an auditable NFL offense tendency report.")
    parser.add_argument("--csv", required=True, type=Path, help="Local nflverse-shaped UTF-8 CSV")
    parser.add_argument("--source-label", required=True, help="Describe data origin; label synthetic fixtures explicitly")
    parser.add_argument("--team", required=True, help="Offense abbreviation, e.g. CAR")
    parser.add_argument("--season", required=True, type=int)
    parser.add_argument("--before-week", required=True, type=int, help="Exclusive cutoff: target week is not included")
    parser.add_argument("--season-type", choices=("REG", "POST"), default="REG")
    parser.add_argument("--minimum-plays", type=int, default=30, help="Warning threshold, not a significance test")
    args = parser.parse_args(argv)
    try:
        report = build_report(
            load_csv(args.csv), team=args.team, season=args.season,
            before_week=args.before_week, season_type=args.season_type,
            minimum_plays=args.minimum_plays, source_label=args.source_label,
        )
        payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
