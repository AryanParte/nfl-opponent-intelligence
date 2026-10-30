"""Acquire/verify only the reviewed FTN 2024 artifact, outside serving ingestion.

Uses the existing bounded HTTP transport. No PBP joins, mutable latest pointer,
automatic refresh, arbitrary download URL, or production charting dependency.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha1, sha256
import json
import os
from pathlib import Path
import tempfile

from opponent_intelligence.snapshots import (
    MAX_METADATA_BYTES, SnapshotError, _download, _read_json, _utc_timestamp,
)


SEASON = 2024
ASSET_NAME = "ftn_charting_2024.csv"
ASSET_SHA256 = "6faae8118cc13ce62589210d553733128ed35e558671009b4a7a8fc5c674c2cb"
ASSET_BYTES = 8254908
RELEASE_API = "https://api.github.com/repos/nflverse/nflverse-data/releases/tags/ftn_charting"
ASSET_URL = f"https://github.com/nflverse/nflverse-data/releases/download/ftn_charting/{ASSET_NAME}"
SOURCE_COMMIT = "23f915a5be30415aeaa0c5c80cd23b2c69cda122"
SOURCE_ROOT = f"https://raw.githubusercontent.com/nflverse/nflreadr/{SOURCE_COMMIT}"
SOURCE_FILES = {
    "load_ftn_charting.R": ("R/load_ftn_charting.R", "07bf9f63c4f6028699d220d455ab364396cbee25", 2220),
    "dictionary_ftn_charting.csv": (
        "data-raw/dictionary_ftn_charting.csv", "ca2278443124d0db2644ba74e13f90a43b599907", 2551),
    "nflreadr-LICENSE.md": ("LICENSE.md", "e7c93e8e5d9b2f8f5863b58ed1bb3325e7862ee4", 1075),
}
DEFAULT_CACHE = Path("data/raw/nflverse/ftn_charting/2024")


def release_identity():
    """Metadata observed 2026-10-30; timestamps are not row availability evidence."""
    return {
        "release_api_url": RELEASE_API, "release_id": 119740650,
        "release_tag": "ftn_charting", "release_published_at_utc": "2023-09-03T16:14:36Z",
        "asset_id": 288253517, "asset_name": ASSET_NAME, "download_url": ASSET_URL,
        "asset_created_at_utc": "2025-09-01T01:29:36Z",
        "asset_updated_at_utc": "2025-09-01T01:29:37Z",
        "size_bytes": ASSET_BYTES, "sha256": ASSET_SHA256,
    }


def source_identity():
    return {
        "dataset": "FTN charting via nflverse", "season": SEASON,
        "reviewed_on": "2026-10-30", "release": release_identity(),
        "documentation_commit": SOURCE_COMMIT,
        "license": {
            "identifier": "CC-BY-SA-4.0",
            "url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "legalcode_url": "https://creativecommons.org/licenses/by-sa/4.0/legalcode.en",
            "source_url": f"{SOURCE_ROOT}/R/load_ftn_charting.R",
            "attribution": "FTN Data via nflverse",
            "modifications": "Source CSV retained byte-for-byte; no transformations.",
        },
        "documentation_license": {
            "identifier": "MIT", "attribution": "Copyright (c) 2021 nflreadr authors",
            "source_url": f"{SOURCE_ROOT}/LICENSE.md",
        },
        "historical_row_availability_verified": False,
        "joined_to_pbp": False,
    }


def _same_json(actual, expected):
    # Dict equality alone treats False == 0 and 2024 == 2024.0 as identical.
    try:
        return json.dumps(actual, sort_keys=True, allow_nan=False) == json.dumps(
            expected, sort_keys=True, allow_nan=False)
    except (ValueError, TypeError):
        return False


def _check_release(release):
    try:
        matches = [a for a in release["assets"] if a["name"] == ASSET_NAME]
        if len(matches) != 1:
            raise SnapshotError("expected one reviewed FTN CSV release asset")
        asset = matches[0]
        observed = {
            "release_api_url": RELEASE_API, "release_id": release["id"],
            "release_tag": release["tag_name"], "release_published_at_utc": release["published_at"],
            "asset_id": asset["id"], "asset_name": asset["name"],
            "download_url": asset["browser_download_url"],
            "asset_created_at_utc": asset["created_at"], "asset_updated_at_utc": asset["updated_at"],
            "size_bytes": asset["size"], "sha256": asset["digest"].removeprefix("sha256:"),
        }
        if asset["state"] != "uploaded" or asset["digest"] != f"sha256:{ASSET_SHA256}":
            raise SnapshotError("FTN release digest/state changed; review before acquiring")
        if not _same_json(observed, release_identity()):
            raise SnapshotError("FTN release metadata changed; review before acquiring")
    except (KeyError, TypeError, AttributeError) as exc:
        raise SnapshotError("invalid FTN release metadata") from exc


def _read_file(path, size):
    if path.is_symlink() or not path.is_file():
        raise SnapshotError(f"not a regular snapshot file: {path.name}")
    with path.open("rb") as handle:
        raw = handle.read(size + 1)
    if len(raw) != size:
        raise SnapshotError(f"snapshot size mismatch: {path.name}")
    return raw


def read_csv(directory):
    """Recheck the exact bytes the auditor will parse, not just an earlier read."""
    raw = _read_file(Path(directory) / ASSET_NAME, ASSET_BYTES)
    if sha256(raw).hexdigest() != ASSET_SHA256:
        raise SnapshotError("FTN CSV SHA-256 differs from the reviewed asset")
    return raw


def _files(directory):
    raw = read_csv(directory)
    records = {ASSET_NAME: {"sha256": sha256(raw).hexdigest(),
                           "size_bytes": len(raw), "url": ASSET_URL}}
    for name, (relative, blob, size) in SOURCE_FILES.items():
        raw = _read_file(directory / name, size)
        actual_blob = sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()
        if actual_blob != blob:
            raise SnapshotError(f"pinned documentation Git blob mismatch: {name}")
        records[name] = {"sha256": sha256(raw).hexdigest(), "size_bytes": len(raw),
                         "git_blob_sha1": blob, "url": f"{SOURCE_ROOT}/{relative}"}
    return records


def verify(directory):
    """Offline, fail-closed verification; never repair or replace existing files."""
    directory = Path(directory)
    if any(p.is_symlink() for p in (directory, *directory.parents)) or not directory.is_dir():
        raise SnapshotError("snapshot must be a real directory without symlink parents")
    if {p.name for p in directory.iterdir()} != {ASSET_NAME, "manifest.json", *SOURCE_FILES}:
        raise SnapshotError("unexpected or missing FTN snapshot files")
    path = directory / "manifest.json"
    if path.is_symlink() or not path.is_file():
        raise SnapshotError("manifest must be a regular file")
    manifest = _read_json(path)
    if (set(manifest) != {"schema_version", "source", "retrieved_at_utc", "files"}
            or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1
            or not _same_json(manifest["source"], source_identity())
            or not _utc_timestamp(manifest["retrieved_at_utc"])
            or not _same_json(manifest["files"], _files(directory))):
        raise SnapshotError("FTN snapshot manifest identity/fingerprints do not match")
    return manifest


def acquire(cache=DEFAULT_CACHE):
    """Reuse exact verified bytes offline or explicitly acquire the reviewed pin.

    The cooperative lock and temporary staging follow the existing artifact-cache
    pattern. Revisions need a new source review, not a silent latest-pointer update.
    """
    cache = Path(cache)
    if any(p.is_symlink() for p in (cache, *cache.parents)):
        raise SnapshotError("cache path must not traverse symlinks")
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / ASSET_SHA256
    if destination.exists() or destination.is_symlink():
        verify(destination)
        return destination
    lock = cache / ".acquire.lock"
    try:
        with lock.open("x"):
            pass
    except FileExistsError as exc:
        raise SnapshotError("acquisition lock exists; inspect the active/interrupted run") from exc
    try:
        if destination.exists() or destination.is_symlink():
            verify(destination)
            return destination
        with tempfile.TemporaryDirectory(prefix=".ftn-acquire-", dir=cache) as temporary:
            staging = Path(temporary)
            _download(RELEASE_API, staging / "release.json", MAX_METADATA_BYTES, 30, 3,
                      accept="application/vnd.github+json")
            _check_release(_read_json(staging / "release.json"))
            candidate = staging / ASSET_SHA256
            candidate.mkdir()
            _download(ASSET_URL, candidate / ASSET_NAME, ASSET_BYTES, 30, 3)
            for name, (relative, _, size) in SOURCE_FILES.items():
                _download(f"{SOURCE_ROOT}/{relative}", candidate / name, size, 30, 3)
            manifest = {"schema_version": 1, "source": source_identity(),
                        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                        "files": _files(candidate)}
            (candidate / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n",
                                                      encoding="utf-8")
            verify(candidate)
            # Cooperative writers cannot replace an existing snapshot. Even an
            # unexpected preexisting empty directory must survive untouched.
            if destination.exists() or destination.is_symlink():
                verify(destination)
            else:
                os.rename(candidate, destination)
        return destination
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--acquire", action="store_true", help="explicit reviewed network acquisition")
    action.add_argument("--verify", type=Path, help="offline verification only")
    args = parser.parse_args()
    try:
        directory = acquire() if args.acquire else args.verify
        manifest = verify(directory)
    except (SnapshotError, OSError) as exc:
        parser.exit(1, f"FTN snapshot failed: {exc}\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
