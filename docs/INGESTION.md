# Immutable raw play-by-play snapshots

The acquisition command verifies the published **2024** nflverse gzip CSV bytes.
It does not itself certify CSV semantics or season completeness. Offline reporting
now accepts an explicit snapshot directory through `--snapshot`; `--csv` still
requires uncompressed CSV. The recorded artifact's analytical checks are documented
in [REAL_DATA_AUDIT.md](REAL_DATA_AUDIT.md), separately from raw acquisition.

## Acquire and reuse

From the project root, with Python 3.11+ and no extra dependencies:

```sh
# First acquisition uses the public GitHub release API and asset download.
PYTHONPATH=src python3 -m opponent_intelligence.fetch --season 2024

# The same command rehashes cached bytes without making network requests.
PYTHONPATH=src python3 -m opponent_intelligence.fetch --season 2024

# Explicitly check/download the current upstream asset; retain older snapshots.
PYTHONPATH=src python3 -m opponent_intelligence.fetch --season 2024 --refresh
```

JSON stdout contains the archive path, manifest path, and snapshot SHA-256.
Failures exit with status 2, explain the error on stderr, and emit no success JSON.
`--cache-dir` changes the cache location. The default `data/raw/nflverse` is ignored
by Git. Never commit raw season data, and use a private, trusted local cache directory.
Only the reviewed 2024 source is enabled; other seasons fail explicitly.

```text
data/raw/nflverse/pbp/2024/
├── current.json                         # mutable selection, updated atomically
└── <compressed-SHA-256>/                 # immutable-by-policy snapshot
    ├── play_by_play_2024.csv.gz           # unchanged upstream bytes
    └── manifest.json                    # first successful acquisition provenance
```

The manifest records the release/tag and asset identifiers, canonical source URL,
asset update time, retrieval time in UTC, compressed and decoded byte counts and
SHA-256 hashes, and data attribution. Decoded bytes are hashed but not stored.
The source API must provide the expected compressed digest and size. A changing
release URL is not a version identifier; the content hashes identify the bytes.

## Cache and failure semantics

- Default reuse is offline, **not** a freshness check. Both compressed and decoded
  bytes are verified, along with the manifest identity and attribution.
- Refresh fetches the release metadata again. A different compressed digest gets
  a new directory. Identical bytes reuse the original manifest even if upstream
  asset metadata changed: retrieval time means first acquisition, not last check.
- Acquisition stages files on the same filesystem. The completed directory is
  published before `current.json` is atomically replaced. Failure before pointer
  publication leaves the previous selection unchanged. A fully published orphan
  can be verified and reused by a later fetch; partial downloads are cleaned up.
- Existing corrupt snapshots are never silently repaired or overwritten. Preserve
  them for investigation and use a separate cache directory if recovery is needed.
  Symbolic-link snapshot files/directories and pointers are rejected.
- Concurrent identical-byte publishers verify and reuse the winning directory.
  Different concurrent refreshes can finish in either order; the pointer is the
  last completed selection, not a guarantee of newest upstream update time.
  Serialize refreshes when ordering matters. Atomic visibility is not a guarantee
  against power loss or malicious local edits; this cache is not a data backup.

Each request defaults to three attempts (allowed: 1–5) and a 30-second socket
operation timeout (finite, positive, at most 120 seconds). This is not a hard
wall-clock deadline for an entire transfer. Transient network failures, interrupted
bodies, and HTTP 408/429/500/502/503/504 retry with capped 1/2/4-second backoff.
Other HTTP failures, invalid metadata, and content-integrity failures fail closed.
GitHub rate-limit HTTP 403 is reported without retries; no credentials are needed.

Streaming limits are 2 MiB for release JSON, 64 MiB for the gzip archive, and
256 MiB for decoded content. Declared lengths and streamed sizes are bounded.
The compressed digest is checked **before** decompression. Gzip CRC/truncation and
empty payload checks precede publication. Hashes prove byte agreement, not that a
file contains correct football observations or a valid analytical CSV.

## Source and attribution review

Reviewed on 2026-09-29 (America/New_York):

- [nflverse play-by-play release](https://github.com/nflverse/nflverse-data/releases/tag/pbp)
  and its [release metadata API](https://api.github.com/repos/nflverse/nflverse-data/releases/tags/pbp).
- [nflreadr's official loader](https://github.com/nflverse/nflreadr/blob/main/R/load_pbp.R)
  identifies the nflverse-data play-by-play release as the source.
- The data repository publishes [CC-BY-4.0 terms at this reviewed revision](https://github.com/nflverse/nflverse-data/blob/f0697ac22524b0c7d0e64517475f252bb6b78409/LICENSE.md).
  This is a data-license check, not an inference from a client package's code license.

Credit **nflverse play-by-play data**, link the source and
[CC-BY-4.0 license](https://creativecommons.org/licenses/by/4.0/), retain supplied
notices, and identify modifications when sharing derived work. This increment
copies the archive without transformation. Do not imply nflverse/NFL/team
endorsement or assume these terms cover logos, trademarks, tracking data, or
separately licensed participation/charting products. No blanket rights clearance
is claimed. Future datasets need their own terms review.

## Real acquisition evidence

The [committed small manifest](evidence/pbp-2024-23370d5d10f8.manifest.json) is a
byte-for-byte copy of the local acquisition manifest. It records:

| Observation | Value |
| --- | --- |
| Release / asset ID | 58152862 / 512957856 |
| Upstream asset update | 2026-08-13 12:26:27 UTC |
| Acquisition | 2026-09-30 00:19:00 UTC (2026-09-29 locally) |
| Compressed bytes | 19,362,351 |
| Decoded bytes | 99,483,794 |
| Compressed SHA-256 | `23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06` |
| Decoded SHA-256 | `6ae564c2c49378ec531303292966caee596982278b9fcdad9c9dd0a0dc16bfa7` |

The compressed hash matched the release asset digest. The decoded hash also
matched the separately listed uncompressed CSV asset (ID 512957834). Reusing the
real cache with network access blocked succeeded without rewriting its manifest.
The offline suite covers acquisition errors, publication, and cache policy
with entirely synthetic responses; live availability is not a CI prerequisite.

The public release can be revised or removed. A recorded hash detects changes but
does not preserve remote bytes: keep the downloaded artifact for exact replay.
Durable external archival storage is not implemented, and Git contains only the
small manifest, not the 19 MB archive. In particular, **a 2024 season file retrieved
or revised in 2026 is not evidence of what was available before a 2024 game**.

## Analytical validation and next stage

The 2026-09-30 unit read this exact snapshot through the gzip-aware analytical
adapter, carried its manifest into reports, audited required fields and observed
coverage, and reconciled exclusions and selected cohort denominators. See the
[audit evidence](REAL_DATA_AUDIT.md) for replay commands and remaining limits.
Repeat that audit for new snapshots. Defense-side reporting followed on 2026-10-01;
see the [current roadmap](../ROADMAP.md) for the next product unit. Neither step
establishes predictive validity or a production deployment.
