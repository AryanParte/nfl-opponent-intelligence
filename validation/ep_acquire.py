"""Explicit acquisition of one pinned EP container; never loads or executes it.

Repository-only experiment setup. Reuses the production bounded HTTP transport,
but does not change PBP ingestion, the installed package, or any serving path.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha1, sha256
import json
import os
from pathlib import Path
import tempfile

from opponent_intelligence.snapshots import (
    SnapshotError, _download, _read_json, _utc_timestamp,
)


COMMIT = "ca185baf7757c2992e57ce2bdf2f296c515465d8"
RELEASED_AT = "2026-02-07T13:19:40Z"
ROOT_URL = f"https://raw.githubusercontent.com/nflverse/fastrmodels/{COMMIT}"
FILES = {
    "ep_model.rda": ("data/ep_model.rda", "f1a434b6f6f67fcb2195d0aeb6cf5d7dd88c7a09", 2864452),
    "LICENSE.md": ("LICENSE.md", "74fa99449286373a0ac870d1c25b66a1dbea20ee", 16384),
    "DESCRIPTION": ("DESCRIPTION", "23816b7c488b1484e8a51bc138d18006397a09a9", 16384),
}
SNAPSHOT_NAME = FILES["ep_model.rda"][1]
DEFAULT_CACHE = Path(".cache/ep-reference/artifacts")


def _fingerprint(path, expected_blob, limit):
    if path.is_symlink() or not path.is_file():
        raise SnapshotError(f"not a regular artifact file: {path.name}")
    with path.open("rb") as source:
        raw = source.read(limit + 1)
    if not raw or len(raw) > limit:
        raise SnapshotError(f"empty or oversized artifact: {path.name}")
    blob = sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()
    if blob != expected_blob:
        raise SnapshotError(f"pinned Git blob mismatch: {path.name}")
    return {"git_blob_sha1": blob, "sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _identity():
    return {
        "repository": "nflverse/fastrmodels", "version": "2.1.0", "commit": COMMIT,
        "release_published_at_utc": RELEASED_AT,
        "license": {"identifier": "MIT", "source_url": f"{ROOT_URL}/LICENSE.md",
                    "attribution": "Copyright (c) 2021 Sebastian Carl,Ben Baldwin",
                    "scope": "Package artifact; not a license for separate training datasets."},
        "representation": "R .rda container; raw EP payload not yet extracted or executed",
        "verified_training_window": None,
    }


def verify(directory):
    """Verify every pinned byte and provenance record offline; never repair a cache."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise SnapshotError("artifact snapshot must be a real directory")
    if {p.name for p in directory.iterdir()} != set(FILES) | {"manifest.json"}:
        raise SnapshotError("unexpected or missing artifact snapshot files")
    manifest_path = directory / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise SnapshotError("manifest must be a regular file, not a symlink")
    manifest = _read_json(directory / "manifest.json")
    if (set(manifest) != {"schema_version", "source", "retrieved_at_utc", "files"}
            or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1
            or manifest["source"] != _identity()
            or not _utc_timestamp(manifest["retrieved_at_utc"])
            or not isinstance(manifest["files"], dict) or set(manifest["files"]) != set(FILES)):
        raise SnapshotError("invalid EP acquisition manifest")
    for name, (relative, blob, limit) in FILES.items():
        actual = _fingerprint(directory / name, blob, limit)
        if name == "ep_model.rda" and actual["size_bytes"] != limit:
            raise SnapshotError("EP container size differs from pinned metadata")
        if manifest["files"][name] != actual | {"url": f"{ROOT_URL}/{relative}"}:
            raise SnapshotError(f"artifact manifest fingerprint mismatch: {name}")
    return manifest


def acquire(cache=DEFAULT_CACHE):
    """Acquire only reviewed fixed URLs, publish atomically, or reuse offline.

    The Git blob ID fixes the destination before download. Its SHA-1 is computed
    with Git framing; the manifest also records a fresh SHA-256 of actual bytes.
    Changed/corrupt cache entries are errors, not refresh/replacement requests.
    """
    cache = Path(cache)
    if any(p.is_symlink() for p in (cache, *cache.parents)):
        raise SnapshotError("cache path must not traverse symlinks")
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / SNAPSHOT_NAME
    if destination.exists() or destination.is_symlink():
        verify(destination)
        return destination
    lock = cache / ".acquire.lock"
    try:
        with lock.open("x"):
            pass
    except FileExistsError as exc:
        raise SnapshotError("acquisition lock exists; inspect an active/interrupted run before retrying") from exc
    try:
        # A writer may have finished between the first check and lock acquisition.
        if destination.exists() or destination.is_symlink():
            verify(destination)
            return destination
        return _publish(cache, destination)
    finally:
        lock.unlink()


def _publish(cache, destination):
    with tempfile.TemporaryDirectory(prefix=".ep-acquire-", dir=cache) as temporary:
        staged = Path(temporary) / "snapshot"
        staged.mkdir()
        records = {}
        for name, (relative, blob, limit) in FILES.items():
            url = f"{ROOT_URL}/{relative}"
            _download(url, staged / name, limit, timeout=30, attempts=3)
            records[name] = _fingerprint(staged / name, blob, limit) | {"url": url}
        manifest = {"schema_version": 1, "source": _identity(),
                    "retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "files": records}
        (staged / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        verify(staged)
        try:
            os.rename(staged, destination)
        except OSError:
            # A concurrent writer may have published the same pinned snapshot.
            # Verify it; never overwrite, delete or "repair" someone else's files.
            if not destination.exists():
                raise
            verify(destination)
        return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--acquire", action="store_true", help="explicit networked setup")
    action.add_argument("--verify", type=Path, help="offline verification of an existing snapshot")
    args = parser.parse_args()
    try:
        directory = acquire() if args.acquire else args.verify
        manifest = verify(directory)
    except (SnapshotError, OSError) as exc:
        parser.exit(1, f"EP acquisition failed: {exc}\n")
    print(json.dumps({"status": "container_bytes_verified", "directory": str(directory),
                      "manifest_sha256": sha256((directory / "manifest.json").read_bytes()).hexdigest(),
                      "ep_container": manifest["files"]["ep_model.rda"],
                      "model_executed": False, "predictive_validation": False}, indent=2))


if __name__ == "__main__":
    main()
