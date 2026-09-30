# Recorded 2024 snapshot: analytical audit

On 2026-09-30, the acquired nflverse artifact passed the existing analytical
contract without changing eligibility rules or imputing missing values. This is
an audit of one retrospective release, not predictive validation or a claim that
all upstream football annotations are correct.

## Source and replay

The [acquisition manifest](evidence/pbp-2024-23370d5d10f8.manifest.json) identifies
the original unchanged archive, its nflverse source, CC-BY-4.0 attribution,
2026-08-13 upstream update, and 2026-09-30 UTC retrieval. The
[machine-readable audit](evidence/pbp-2024-23370d5d10f8.audit.json) contains all
observed week counts, required-field missingness, types, and reconciliation.
It is a derived summary, not a replacement for the raw artifact.

- Compressed SHA-256: `23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06`
- Decoded CSV SHA-256: `6ae564c2c49378ec531303292966caee596982278b9fcdad9c9dd0a0dc16bfa7`

From the repository root, after acquiring or restoring those exact bytes:

```sh
snapshot_dir=data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06
PYTHONPATH=src python3 -m opponent_intelligence.audit --snapshot "$snapshot_dir"
PYTHONPATH=src python3 -m opponent_intelligence \
  --snapshot "$snapshot_dir" --team CAR --season 2024 --before-week 3 \
  --source-label 'nflverse 2024 retrospective snapshot; acquired 2026-09-30 UTC'
```

Both commands are offline. Neither silently acquires data nor follows `current.json`.
The report carries the raw manifest; its top-level source hash identifies decoded
CSV bytes. A new acquisition of identical data has a different retrieval receipt,
even when the byte hashes and analytical results agree. Raw data remains ignored
by Git and must be preserved separately for replay if the public release changes.

## Source-wide findings

All 49,492 rows have season 2024 and unique `(game_id, play_id)` identities. All
15 required columns are present among 372 total columns. Only documented play
types or missing markers occur. The successful audit also checks consistent game
season-type/week metadata, including excluded rows.

| Observed coverage | Regular season | Postseason |
| --- | ---: | ---: |
| Source rows | 47,274 | 2,218 |
| Unique games | 272 | 13 |
| Week range | 1–18 | 19–22 |
| Eligible plays | 33,335 | 1,567 |
| Eligible dropbacks | 20,116 | 914 |
| Observed EPA among eligible plays | 33,335 | 1,567 |
| Distinct eligible offenses | 32 | 14 |

Observed game coverage was **not** compared against an independent schedule or
official gamebooks. Game counts alone cannot establish completeness or prove
that no individual source play is omitted.

The exact row reconciliation is:

`49,492 = 34,902 eligible + 12,996 non-run/pass + 1,446 missing type + 148 conversions`.

Raw pass/run counts are 20,007 / 15,043, before the 148 conversion exclusions.
The non-run/pass bucket includes 437 type-labeled kneels and 75 type-labeled spikes.
Type exclusion occurs before flag checks; do not add those counts again. These
counts follow the project policy, not an official box-score play-total definition.

Missingness is counted before exclusions: down 8,009; possession team 2,713;
defense 2,713; play type 1,446; dropback flag 1,446; conversion flag 1,517; EPA 570.
All other required fields have zero missing markers. No eligible play has missing
required values, including EPA. No values were filled with zero. The parser still
supports missing EPA on future eligible plays without removing them from the
play-call denominator.

## Independent cohort reconciliation

The audit enumerates raw eligible identities separately from the adapter and
compares the exact sets, not only their sizes. Separately, direct CSV filtering
and `Decimal` EPA sums reproduced the following report outputs. Counts matched
exactly and floating-point rates/means agreed within absolute tolerance `1e-12`.
The source rows, not the generated report, supplied the expected values.

| Cohort (exclusive cutoff) | Games | Plays / EPA observations | Dropbacks | Positive EPA | Decimal EPA sum |
| --- | ---: | ---: | ---: | ---: | ---: |
| CAR REG before week 1 | 0 | 0 | 0 | 0 | 0 |
| CAR REG before week 3 | 2 | 101 | 68 | 27 | -49.2657959262087725 |
| CAR REG before week 19 | 17 | 984 | 626 | 407 | -51.645793381342929396 |
| KC POST before week 23 | 3 | 156 | 107 | 70 | -0.2485040105889483 |

For CAR before week 3, dropback rate is `68/101`, success rate is `27/101`, and
EPA/play is the recorded EPA sum divided by 101. These select games
`2024_01_CAR_NO` and `2024_02_LAC_CAR`; week 3 is excluded. The empty week-1 cohort
returns null rates, not zero. These are descriptive reconciliation examples, not
a scouting recommendation or proof that 101 plays are independent observations.

This minimal independent calculation reproduces any row of the table; change
`team`, `kind`, and `cutoff` together to select that cohort:

```python
import csv
from decimal import Decimal
import gzip
from pathlib import Path

root = Path("data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06")
team, kind, cutoff = "CAR", "REG", 3
with gzip.open(root / "play_by_play_2024.csv.gz", "rt", encoding="utf-8-sig", newline="") as source:
    rows = [r for r in csv.DictReader(source)
            if r["season"] == "2024" and r["posteam"] == team
            and r["season_type"] == kind and int(r["week"]) < cutoff
            and r["play_type"] in {"run", "pass"}
            and all(r[f] == "0" for f in ("two_point_attempt", "qb_kneel", "qb_spike"))]
epa = [Decimal(r["epa"]) for r in rows if r["epa"].strip().upper() not in {"", "NA", "NAN", "NULL"}]
print(len({r["game_id"] for r in rows}), len(rows), len(epa),
      sum(r["qb_dropback"] == "1" for r in rows), sum(v > 0 for v in epa), sum(epa))
```

The snippet is specific to this already-verified artifact's numeric serialization,
not a replacement for the strict adapter or its missing/invalid-input handling.

## Verification and limits

All 60 synthetic offline tests pass on Python 3.11/3.12/3.13. Sixteen integration
tests add provenance/hash agreement, bounded rereads, corruption and mutation
handling, wrong-season rejection, audit disagreement detection, empty cohorts,
missingness, and deterministic all-or-nothing CLIs. The existing synthetic fixture
and its measurement expectations remain unchanged; CI never downloads this season.

The [nflreadr dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv)
and [nflfastR field construction](https://github.com/nflverse/nflfastR/blob/master/R/helper_add_nflscrapr_mutations.R)
were rechecked on 2026-09-30 for the existing category/dropback policy. We did not
validate every extra column, independently estimate EPA, reconcile official box
scores, or reconstruct historical information availability. A season retrieved
after its games cannot certify leakage-free forecasting.

Raw missingness and analytical denominators stay separate. Analytical loading is
bounded but in-memory, not a
large-scale streaming claim. Empty or incomplete snapshots are described honestly,
not automatically certified complete. New snapshots need a fresh audit.

Next: P1.3 opponent-defense cohorts with explicit EPA perspective and time cutoffs,
then context filters and matched league baselines. UI and predictive work remain
deferred.
