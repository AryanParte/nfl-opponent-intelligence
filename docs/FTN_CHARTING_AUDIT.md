# FTN 2024 artifact and contract audit

Reviewed/acquired 2026-10-30. This first narrow **P1.7** slice extends the
[personnel/motion review](PERSONNEL_MOTION.md). One public CSV is acquired and
verified independently of PBP. It is **not joined or served**; no play families,
rates, coaching recommendations or historical-availability claims are enabled.
Scout and the offline decision contract are unchanged.

## Source and rights boundary

Rechecked the [release metadata][release], [nflreadr loader][loader] and
[dictionary][dictionary] at commit `23f915a5be30415aeaa0c5c80cd23b2c69cda122`.
The commit and listed asset are unchanged from October 8. Unlike that metadata-only
review, this run downloaded the bytes and verified their hash.

The loader identifies this manual-charting subset as **FTN Data via nflverse**,
under **CC BY-SA 4.0**, not PBP's CC BY 4.0. Documented coverage starts in 2022;
the within-48-hour charting cadence is not a verified public-release SLA.
The [legal code][legalcode], including attribution, modification notices,
ShareAlike and database rights, was reviewed for this bounded local acquisition.
No paid/access-controlled service was accessed. This is not legal clearance for
future combined exports or a claim that all application code inherits ShareAlike;
review the intended distribution before shipping enriched downloads.

The cache retains unmodified CSV, pinned loader/dictionary and nflreadr MIT notice.
Their hashes, URLs, byte counts and attribution appear in the manifest embedded
in the [aggregate receipt][receipt]. Raw rows and source-file copies stay ignored,
not redistributed in Git. That derived receipt and the FTN-derived counts here
are made available under [CC BY-SA 4.0][license], attributed to FTN Data via
nflverse. Modification: aggregate schema/key/encoding inventory, no row-level
redistribution. No endorsement is implied. The [nflreadr software/documentation
notice][mit] remains separate from dataset terms.

## Immutable identity and timing

| Item | Verified/observed value |
| --- | --- |
| Asset | `ftn_charting_2024.csv` / ID `288253517` |
| Release | `ftn_charting` / ID `119740650` |
| CSV size | 8,254,908 bytes, uncompressed UTF-8 CSV |
| CSV SHA-256 | `6faae8118cc13ce62589210d553733128ed35e558671009b4a7a8fc5c674c2cb` |
| Asset created / updated | 2025-09-01 01:29:36 / 01:29:37 UTC |
| This acquisition | 2026-10-30 17:56:04.882310 UTC |
| Release container published | 2023-09-03 16:14:36 UTC; not the 2024 asset's publication |

Only the reviewed asset name/ID/URL/digest/size/timestamps are accepted. A changed
release needs another review, not an implicit refresh. The shared PBP transport
now accepts an explicit media type for this second GitHub metadata route; its
original default and bounded body/socket/retry behavior are preserved. The first
acquisition returned HTTP 415 with the binary Accept header. GitHub's JSON Accept
header resolved it without changing any pins.

Snapshots live at `data/raw/nflverse/ftn_charting/2024/<CSV-SHA256>/`, separately
from `pbp/2024/`. Publication stages verified files under a cooperative writer
lock. Existing invalid snapshots are preserved and rejected, never repaired.
There is no latest pointer or second production ingestion path. Offline reuse
checks the CSV, source Git blobs and manifest/notices. The auditor rehashes the
exact bytes it parses after verification. Hashes detect integrity drift, not
malicious upstream attestation; the lock is not a hostile-local-writer boundary.

`date_pulled` means **nflverse's extraction from the FTN API**, not first public
availability. Observed range: 2024-11-13 12:29:59.804047 through
2025-09-01 01:29:30.123782 UTC. Neither these values, a release container date,
asset update nor acquisition proves pregame availability or a revision history.
No leakage-safe historical feature replay is approved by this audit.

## Artifact findings

**48,031 raw rows**, **29 columns**, **285 distinct game IDs**. Headers match the
pinned dictionary exactly; no blank/`NA` tokens are present. This is not a
complete-schedule reconciliation, PBP coverage check or charting-accuracy validation.
Raw rows have not been filtered by the analytical run/dropback policy; do not
use these counts as play-call denominators or infer which specific rows are eligible.

| Key domain | Valid-format rows | Distinct composite keys | Missing/invalid rows | Duplicate groups |
| --- | ---: | ---: | ---: | ---: |
| `nflverse_game_id, nflverse_play_id` | 48,031 | 48,031 | 0 / 0 | 0 |
| `ftn_game_id, ftn_play_id` | 48,031 | 48,031 | 0 / 0 | 0 |

Only the **NFLverse** pair is a candidate join key for PBP `(game_id, play_id)`.
FTN IDs are a separate namespace, not aliases. Numeric IDs parse as bounded exact
nonnegative integers (`.0` forms normalize without floats); exponents, fractions,
negative/whitespace/overflow encodings reject. Game ID shape is checked separately.
All rows agree on 2024 and their embedded week with CSV season/week. This is
internal consistency, not referential integrity. The auditor never opens PBP.

All 15 documented logical columns contain uppercase `TRUE`/`FALSE`. This verifies
serialization, **not applicability**: false on a non-applicable play is not
automatically a negative observation. No motion/play-action/RPO rates are computed.

| Field | Documented-code rows | Outside documented codes | Separate raw check |
| --- | ---: | ---: | --- |
| `starting_hash` (`L/M/R`) | 36,430 | 11,601 | All outside values are literal `0` |
| `qb_location` (`U/S/P`) | 36,426 | 11,605 | All outside values are literal `0` |

The receipt reports unknown totals without echoing arbitrary strings. `0` is not
mapped to a formation, valid hash, missing flag or false observation. Investigate
its applicability/source-generation semantics in the next join/coverage audit.
`read_thrown=0` has a different documented meaning from 2023 onward; codes are
field/year-specific. Motion covers movement before **or** at the snap, not a
trajectory or exclusively at-snap motion. Backfield counts do not identify running
backs or personnel composition. Other numeric/text columns receive only
presence/missing-token inventories here, not range/football-semantic validation.

## Reproduce

From the canonical repository with Python 3.11–3.13, no extra dependencies:

```sh
PYTHONPATH=src python3 -m validation.ftn_snapshot --acquire

ftn_snapshot=data/raw/nflverse/ftn_charting/2024/6faae8118cc13ce62589210d553733128ed35e558671009b4a7a8fc5c674c2cb
PYTHONPATH=src python3 -m validation.ftn_snapshot --verify "$ftn_snapshot"
PYTHONPATH=src python3 -m validation.ftn_contract --snapshot "$ftn_snapshot" \
  | cmp - docs/evidence/ftn-2024-6faae8118cc1.contract.json
PYTHONPATH=src python3 -m unittest discover -s tests -p test_ftn_contract.py -v
```

First acquisition explicitly needs network; verified cache reuse is offline.
`cmp` exits zero with the original manifest. A fresh acquisition of the same bytes
has a new retrieval time: compare inventory, source identity and hashes separately
and retain that truthful manifest. Do not copy the old time to manufacture replay.
`--output` creates a new receipt exclusively, refusing to overwrite. Audit/verify
never download, follow mutable pointers or edit the cache.

The 23 new synthetic/offline tests cover metadata/media-type drift, corrupt/
oversized/incomplete bytes, manifest/notice mutations, transfer/publication errors,
locks/symlinks, offline reuse, post-verification mutation, exact IDs/duplicates,
absent/missing/false/unknown states, date/context errors, input bounds, order/BOM
invariance and no-clobber CLI output. CI checks receipt pins/count partitions, not
the real CSV. No raw data, new dependency or network is needed in tests.

A separate local raw-CSV/Decimal check reconciled dictionary order, key/game
counts, season/week, missing tokens, every logical/code partition and timestamps
without importing the auditor. Exact offline replay passes on all supported
Python versions. [STATUS](STATUS.md) and [learning log](../LEARNING_LOG.md) record
final checks and complete-diff findings.

## Admission and next unit

**Acquire/audit only.** No charting field is admitted to production typed data,
API, React or decision ranking. Next: one offline left-join/coverage audit against
verified PBP, enforcing cardinality and preserving all eligible PBP rows. Count
unmatched/unknown/invalid values separately by team/week/candidate, investigate
placeholder/applicability semantics and independently reconcile totals. Never
inner-join away missing evidence or widen cohorts to hide it. Extraction/release
timing stays distinct from game time. Participation/tracking, richer play families
and enriched exports remain deferred; synthetic model parity does not unlock them.

[release]: https://api.github.com/repos/nflverse/nflverse-data/releases/tags/ftn_charting
[loader]: https://github.com/nflverse/nflreadr/blob/23f915a5be30415aeaa0c5c80cd23b2c69cda122/R/load_ftn_charting.R
[dictionary]: https://github.com/nflverse/nflreadr/blob/23f915a5be30415aeaa0c5c80cd23b2c69cda122/data-raw/dictionary_ftn_charting.csv
[mit]: https://github.com/nflverse/nflreadr/blob/23f915a5be30415aeaa0c5c80cd23b2c69cda122/LICENSE.md
[license]: https://creativecommons.org/licenses/by-sa/4.0/
[legalcode]: https://creativecommons.org/licenses/by-sa/4.0/legalcode.en
[receipt]: evidence/ftn-2024-6faae8118cc1.contract.json
