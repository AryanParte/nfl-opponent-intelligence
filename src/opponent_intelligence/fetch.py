"""Explicit network command for raw snapshots; the report CLI remains offline."""

import argparse
import json
from pathlib import Path
import sys

from .snapshots import ASSET_NAME, SEASON, SnapshotError, fetch_snapshot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch and verify an immutable nflverse raw snapshot.")
    parser.add_argument("--season", required=True, type=int, choices=(SEASON,))
    parser.add_argument("--cache-dir", type=Path, default=Path("data/raw/nflverse"))
    parser.add_argument("--refresh", action="store_true", help="Check upstream without replacing old snapshots")
    parser.add_argument("--timeout", type=float, default=30, help="Per socket-operation timeout in seconds")
    parser.add_argument("--attempts", type=int, default=3, help="Attempts per request, including the first")
    args = parser.parse_args(argv)
    try:
        directory = fetch_snapshot(args.cache_dir, season=args.season, refresh=args.refresh,
                                   timeout=args.timeout, attempts=args.attempts)
    except (SnapshotError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"snapshot_sha256": directory.name,
                      "archive_path": str((directory / ASSET_NAME).resolve()),
                      "manifest_path": str((directory / "manifest.json").resolve())},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
