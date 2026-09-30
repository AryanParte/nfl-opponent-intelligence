"""Acquire immutable, byte-verified nflverse raw snapshots (not analytical validation)."""

from datetime import datetime, timezone
import errno
import gzip
from hashlib import sha256
from http.client import IncompleteRead
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zlib


SEASON = 2024  # Expand only after reviewing another release and its terms.
ASSET_NAME = f"play_by_play_{SEASON}.csv.gz"
RELEASE_API = "https://api.github.com/repos/nflverse/nflverse-data/releases/tags/pbp"
ASSET_URL = f"https://github.com/nflverse/nflverse-data/releases/download/pbp/{ASSET_NAME}"
LICENSE_SOURCE = "https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
MAX_METADATA_BYTES = 2 * 1024 * 1024
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_DECODED_BYTES = 256 * 1024 * 1024
CHUNK_BYTES = 64 * 1024
TRANSIENT_HTTP = {408, 429, 500, 502, 503, 504}


class SnapshotError(ValueError):
    """Acquisition or cache verification failed; no successful snapshot was selected."""


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _positive_int(value: object, maximum: int) -> bool:
    return type(value) is int and 0 < value <= maximum


def _utc_timestamp(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0
    except ValueError:
        return False


def _copy_and_hash(source, destination, limit: int) -> tuple[int, str]:
    digest = sha256()
    size = 0
    while chunk := source.read(CHUNK_BYTES):
        size += len(chunk)
        if size > limit:
            raise SnapshotError(f"payload exceeds {limit} byte limit")
        digest.update(chunk)
        if destination is not None:
            destination.write(chunk)
    return size, digest.hexdigest()


def _download(url: str, target: Path, limit: int, timeout: float, attempts: int) -> None:
    """Bound individual socket operations, body size, attempts, and retry backoff."""
    request = Request(url, headers={
        "User-Agent": "nfl-opponent-intelligence/0.1",
        "Accept": "application/vnd.github+json" if url == RELEASE_API else "application/octet-stream",
    })
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise SnapshotError(f"unexpected HTTP status {response.status} for {url}")
                length = response.headers.get("Content-Length")
                expected_length = None
                if length is not None:
                    try:
                        expected_length = int(length)
                    except ValueError as exc:
                        raise SnapshotError("invalid Content-Length") from exc
                    if not length.isascii() or not length.isdecimal() or expected_length > limit:
                        raise SnapshotError("invalid or oversized Content-Length")
                with target.open("wb") as output:
                    size, _ = _copy_and_hash(response, output, limit)
                if expected_length is not None and size != expected_length:
                    raise IncompleteRead(b"", max(0, expected_length - size))
            return
        except HTTPError as exc:
            exc.close()
            if exc.code not in TRANSIENT_HTTP:
                raise SnapshotError(f"HTTP {exc.code} fetching {url}") from exc
            failure = f"HTTP {exc.code}"
        except (URLError, TimeoutError, ConnectionError, IncompleteRead) as exc:
            failure = type(exc).__name__
        if attempt + 1 < attempts:
            time.sleep(min(2 ** attempt, 4))
    raise SnapshotError(f"fetch failed after {attempts} attempts ({failure}): {url}")


def _read_json(path: Path) -> dict:
    with path.open("rb") as source:
        raw = source.read(MAX_METADATA_BYTES + 1)
    if len(raw) > MAX_METADATA_BYTES:
        raise SnapshotError("JSON metadata exceeds size limit")
    try:
        value = json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise SnapshotError(f"invalid JSON metadata: {path.name}") from exc
    if not isinstance(value, dict):
        raise SnapshotError("JSON metadata must be an object")
    return value


def _validate_source(source: dict) -> None:
    try:
        valid = (
            source["release_api_url"] == RELEASE_API
            and source["release_tag"] == "pbp"
            and _positive_int(source["release_id"], 2**63 - 1)
            and _positive_int(source["asset_id"], 2**63 - 1)
            and source["asset_name"] == ASSET_NAME
            and source["download_url"] == ASSET_URL
            and _positive_int(source["size_bytes"], MAX_ARCHIVE_BYTES)
            and _is_sha256(source["sha256"])
            and _utc_timestamp(source["asset_updated_at_utc"])
        )
    except (KeyError, TypeError):
        valid = False
    if not valid:
        raise SnapshotError("source metadata violates the 2024 nflverse asset contract")


def _select_source(release: dict) -> dict:
    try:
        if not isinstance(release["assets"], list):
            raise SnapshotError("release assets must be a list")
        matches = [asset for asset in release["assets"]
                   if isinstance(asset, dict) and asset.get("name") == ASSET_NAME]
        if len(matches) != 1:
            raise SnapshotError(f"expected exactly one {ASSET_NAME} release asset")
        asset = matches[0]
        digest = asset["digest"]
        if asset["state"] != "uploaded" or not isinstance(digest, str) or not digest.startswith("sha256:"):
            raise SnapshotError("asset must be uploaded and provide a SHA-256 digest")
        source = {
            "release_api_url": RELEASE_API, "release_id": release["id"],
            "release_tag": release["tag_name"], "asset_id": asset["id"],
            "asset_name": asset["name"], "download_url": asset["browser_download_url"],
            "size_bytes": asset["size"], "sha256": digest.removeprefix("sha256:"),
            "asset_updated_at_utc": asset["updated_at"],
        }
    except (KeyError, TypeError) as exc:
        raise SnapshotError("release is missing required asset metadata") from exc
    _validate_source(source)
    return source


def _archive_fingerprints(path: Path, *, expected_sha256: str, expected_size: int) -> tuple[dict, dict]:
    with path.open("rb") as archive:
        size, digest = _copy_and_hash(archive, None, MAX_ARCHIVE_BYTES)
    if digest != expected_sha256 or size != expected_size:
        raise SnapshotError("archive fingerprint mismatch with published asset digest/size")
    try:
        with gzip.open(path, "rb") as decoded:
            decoded_size, decoded_digest = _copy_and_hash(decoded, None, MAX_DECODED_BYTES)
    except (gzip.BadGzipFile, EOFError, zlib.error) as exc:
        raise SnapshotError("invalid or truncated gzip stream") from exc
    if not size or not decoded_size:
        raise SnapshotError("empty raw data is not a valid snapshot")
    return ({"size_bytes": size, "sha256": digest},
            {"size_bytes": decoded_size, "sha256": decoded_digest})


def verify_snapshot(directory: Path) -> dict:
    """Rehash both representations without network access; never repair in place."""
    if not _is_sha256(directory.name):
        raise SnapshotError("invalid snapshot directory name")
    for path in (directory, directory / ASSET_NAME, directory / "manifest.json"):
        if path.is_symlink():
            raise SnapshotError("snapshot paths must not be symbolic links")
    try:
        manifest = _read_json(directory / "manifest.json")
        _validate_source(manifest["source"])
        if (type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1
                or type(manifest["season"]) is not int or manifest["season"] != SEASON
                or not _utc_timestamp(manifest["retrieved_at_utc"])
                or manifest["source"]["sha256"] != directory.name):
            raise SnapshotError("invalid snapshot manifest identity")
        archive, decoded = _archive_fingerprints(
            directory / ASSET_NAME, expected_sha256=directory.name,
            expected_size=manifest["source"]["size_bytes"],
        )
        if (archive != manifest["archive"] or decoded != manifest["decoded_csv"]
                or archive["sha256"] != directory.name
                or archive["size_bytes"] != manifest["source"]["size_bytes"]):
            raise SnapshotError("cached snapshot fingerprint mismatch; preserve it for investigation")
        if manifest["license"] != _license_notice():
            raise SnapshotError("missing or invalid data attribution notice")
        return manifest
    except (KeyError, TypeError) as exc:
        raise SnapshotError("snapshot manifest is missing required fields") from exc


def _license_notice() -> dict:
    return {"identifier": "CC-BY-4.0", "url": LICENSE_URL,
            "source_url": LICENSE_SOURCE, "attribution": "nflverse play-by-play data",
            "modifications": "Archive retained byte-for-byte; no data transformations."}


def fetch_snapshot(cache_dir: Path, *, season: int = SEASON, refresh: bool = False,
                   timeout: float = 30.0, attempts: int = 3) -> Path:
    """Reuse verified local bytes, or explicitly acquire the current upstream asset.

    Snapshots are addressed by compressed SHA-256. current.json is the only mutable
    pointer; it changes only after a complete verified snapshot is published.
    """
    if type(season) is not int or season != SEASON:
        raise SnapshotError("only the reviewed 2024 season is supported")
    if type(attempts) is not int or not 1 <= attempts <= 5:
        raise SnapshotError("attempts must be an integer from 1 to 5")
    if type(timeout) not in (int, float) or not 0 < timeout <= 120 or not math.isfinite(timeout):
        raise SnapshotError("timeout must be finite, positive, and at most 120 seconds")
    root = Path(cache_dir) / "pbp" / str(season)
    root.mkdir(parents=True, exist_ok=True)
    pointer = root / "current.json"
    if pointer.is_symlink():
        raise SnapshotError("cache pointer must not be a symbolic link")
    if pointer.exists() and not refresh:
        selected = _read_json(pointer).get("snapshot_sha256")
        if not _is_sha256(selected):
            raise SnapshotError("invalid cached snapshot pointer")
        directory = root / selected
        verify_snapshot(directory)
        return directory

    # All intermediate files belong to this temporary directory. Failures leave
    # old snapshots and the old pointer untouched; no partial snapshot is visible.
    with tempfile.TemporaryDirectory(prefix=".fetch-", dir=root) as temporary:
        staging = Path(temporary)
        metadata_path = staging / "release.json"
        _download(RELEASE_API, metadata_path, MAX_METADATA_BYTES, timeout, attempts)
        source = _select_source(_read_json(metadata_path))
        candidate = staging / source["sha256"]
        candidate.mkdir()
        archive_path = candidate / ASSET_NAME
        _download(source["download_url"], archive_path, source["size_bytes"], timeout, attempts)
        archive, decoded = _archive_fingerprints(
            archive_path, expected_sha256=source["sha256"], expected_size=source["size_bytes"],
        )
        manifest = {
            "schema_version": 1, "season": season,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": source, "archive": archive, "decoded_csv": decoded,
            "license": _license_notice(),
        }
        (candidate / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        destination = root / source["sha256"]
        if destination.exists() or destination.is_symlink():
            verify_snapshot(destination)
        else:
            try:
                candidate.rename(destination)
            except OSError as exc:
                if exc.errno not in (errno.EEXIST, errno.ENOTEMPTY):
                    raise
                # Another fetch may have published these same bytes first.
                verify_snapshot(destination)
        pending_pointer = staging / "current.json"
        pending_pointer.write_text(json.dumps({"snapshot_sha256": destination.name}) + "\n")
        os.replace(pending_pointer, pointer)
        return destination
