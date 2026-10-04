"""Run with python -m opponent_intelligence; JSON goes to stdout."""

import argparse
import csv
import json
from pathlib import Path
import sys

from .pbp import load_csv
from .ingestion import load_snapshot
from .report import PERIODS, build_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create an auditable NFL offense or defense cohort report.")
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--csv", type=Path, help="Local uncompressed nflverse-shaped UTF-8 CSV")
    inputs.add_argument("--snapshot", type=Path, help="Verified local snapshot directory; never downloads")
    parser.add_argument("--source-label", required=True, help="Describe data origin; label synthetic fixtures explicitly")
    parser.add_argument("--team", required=True, help="Selected team abbreviation, e.g. CAR")
    parser.add_argument("--side", choices=("offense", "defense"), default="offense",
                        help="Team's role to select (default: offense); EPA stays offense-relative")
    parser.add_argument("--season", required=True, type=int)
    parser.add_argument("--before-week", required=True, type=int, help="Exclusive cutoff: target week is not included")
    parser.add_argument("--season-type", choices=("REG", "POST"), default="REG")
    parser.add_argument("--minimum-plays", type=int, default=30, help="Warning threshold, not a significance test")
    parser.add_argument("--yardline-min", type=float,
                        help="Inclusive minimum pre-play yardline_100 (offense's distance to opposing goal line)")
    parser.add_argument("--yardline-max", type=float,
                        help="Inclusive maximum pre-play yardline_100; bounds are 0..100 for either side")
    parser.add_argument("--score-min", type=int,
                        help="Inclusive minimum pre-play score_differential in whole points; omitted end is unbounded")
    parser.add_argument("--score-max", type=int,
                        help="Inclusive maximum pre-play score_differential (offense minus defense for either side)")
    parser.add_argument("--period", choices=PERIODS,
                        help="Pre-play period; OT includes every overtime period (qtr >= 5)")
    parser.add_argument("--clock-min", type=int,
                        help="Inclusive minimum seconds remaining in the selected period (requires --period)")
    parser.add_argument("--clock-max", type=int,
                        help="Inclusive maximum seconds remaining (requires --period); bounds 0..900, omitted ends 0/900")
    args = parser.parse_args(argv)
    try:
        report = build_report(
            load_snapshot(args.snapshot) if args.snapshot is not None else load_csv(args.csv),
            team=args.team, side=args.side, season=args.season,
            before_week=args.before_week, season_type=args.season_type,
            minimum_plays=args.minimum_plays, source_label=args.source_label,
            yardline_min=args.yardline_min, yardline_max=args.yardline_max,
            score_min=args.score_min, score_max=args.score_max,
            period=args.period, clock_min=args.clock_min, clock_max=args.clock_max,
        )
        payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
