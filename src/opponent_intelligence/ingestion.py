"""Bridge a verified local raw snapshot to analytical records, without networking."""

from dataclasses import replace
import gzip
from hashlib import sha256
from pathlib import Path
import zlib

from .pbp import Dataset, _load_csv_bytes
from .snapshots import ASSET_NAME, MAX_DECODED_BYTES, SnapshotError, verify_snapshot


def _read_snapshot(directory: Path) -> tuple[bytes, dict]:
    manifest = verify_snapshot(directory)
    try:
        with gzip.open(directory / ASSET_NAME, "rb") as source:
            raw = source.read(MAX_DECODED_BYTES + 1)
    except (gzip.BadGzipFile, EOFError, zlib.error) as exc:
        raise SnapshotError("invalid or truncated snapshot gzip stream") from exc
    # Recheck the bytes actually being parsed, not only the preceding verification
    # pass. A local mutation between reads must not inherit the old provenance.
    if len(raw) > MAX_DECODED_BYTES or {
        "size_bytes": len(raw), "sha256": sha256(raw).hexdigest(),
    } != manifest["decoded_csv"]:
        raise SnapshotError("decoded CSV differs from verified snapshot manifest")
    return raw, manifest


def _snapshot_dataset(raw: bytes, manifest: dict) -> Dataset:
    dataset = _load_csv_bytes(raw, expected_season=manifest["season"])
    return replace(dataset, source_manifest=manifest)


def load_snapshot(directory: Path) -> Dataset:
    """Read an explicit content-addressed directory, never fetch or follow current.json."""
    raw, manifest = _read_snapshot(directory)
    return _snapshot_dataset(raw, manifest)
