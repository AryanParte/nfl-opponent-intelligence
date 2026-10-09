"""Explicitly invented snapshot factory shared by API and browser contract tests."""

import csv
import gzip
from hashlib import sha256
import io
import json

from opponent_intelligence import snapshots


def write_snapshot(root, rows, fieldnames):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    raw = stream.getvalue().encode()
    # Stored blocks make the tiny test artifact independent of deflater heuristics.
    archive = gzip.compress(raw, compresslevel=0, mtime=0)
    # Pin gzip's OS byte across Python/zlib platforms; payload and CRC are unchanged.
    archive = archive[:9] + b"\xff" + archive[10:]
    digest = sha256(archive).hexdigest()
    directory = root / digest
    directory.mkdir(exist_ok=True)
    # Fictional IDs/timestamps solely for testing the manifest contract, not real acquisition.
    manifest = {
        "schema_version": 1, "season": 2024, "retrieved_at_utc": "2026-10-08T00:00:00Z",
        "source": {
            "release_api_url": snapshots.RELEASE_API, "release_tag": "pbp", "release_id": 100,
            "asset_id": 200, "asset_name": snapshots.ASSET_NAME, "download_url": snapshots.ASSET_URL,
            "size_bytes": len(archive), "sha256": digest,
            "asset_updated_at_utc": "2025-02-10T00:00:00Z",
        },
        "archive": {"sha256": digest, "size_bytes": len(archive)},
        "decoded_csv": {"sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)},
        "license": snapshots._license_notice(),
    }
    (directory / snapshots.ASSET_NAME).write_bytes(archive)
    (directory / "manifest.json").write_text(json.dumps(manifest))
    return directory
