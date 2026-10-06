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

At the 2026-09-30 audit, all 60 synthetic offline tests passed on Python
3.11/3.12/3.13. Sixteen integration tests add provenance/hash agreement, bounded
rereads, corruption and mutation
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

P1.3 opponent-defense cohorts followed on 2026-10-01, preserving EPA perspective
and time cutoffs. See the [current roadmap](../ROADMAP.md) for context filters and
matched league baselines. UI and predictive work remain deferred.

## Field-position extension (2026-10-02)

The same unchanged snapshot contains `yardline_100`. A direct raw-CSV check found
3,542 missing values across 49,492 source rows, but zero missing or invalid values
among 34,902 eligible plays. Eligible values span 1..99 yards, all integral; the
adapter's broader 0..100/fractional contract is exercised with synthetic tests.
Every eligible `(game_id, play_id, yardline_100)` agreed between raw CSV and the
updated adapter. Rerunning the audit now exposes raw and eligible optional-field
missingness separately; the earlier committed audit JSON remains dated evidence.

With network blocked, 576 filtered reports were checked: 32 teams × two roles ×
three season/cutoff combinations × three inclusive ranges. Direct source
selection and Decimal EPA sums matched play/game/dropback/EPA counts, EPA means
within `1e-12`, offensive success rates, range-removal counts, and retained
manifests. The 192 corresponding unfiltered reports matched merged PR #5's output
exactly. Neither the original synthetic fixture nor raw source files changed.

Summing play counts across teams gives the same total for either role:

| Season and exclusive cutoff | 0..20 yards | 80..100 yards | Exactly 20 yards |
| --- | ---: | ---: | ---: |
| REG before week 3 | 590 | 331 | 34 |
| REG before week 19 | 5,147 | 2,967 | 302 |
| POST before week 23 | 233 | 136 | 12 |

Columns overlap (exactly 20 is part of 0..20); they are not disjoint totals.
Do not sum team game counts or rates as if they were play counts. These are
software reconciliation checks, not adjusted defense rankings, external gamebook
validation, or a forecast evaluation.

After verifying the pinned snapshot with the audit command above, this independent
recipe reproduces the table directly from raw records:

```python
import csv
from decimal import Decimal
import gzip
from pathlib import Path

root = Path("data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06")
with gzip.open(root / "play_by_play_2024.csv.gz", "rt", encoding="utf-8-sig", newline="") as source:
    eligible = [r for r in csv.DictReader(source) if r["season"] == "2024"
                and r["play_type"] in {"run", "pass"}
                and all(float(r[f]) == 0 for f in ("two_point_attempt", "qb_kneel", "qb_spike"))]
assert all(r["yardline_100"].strip().upper() not in {"", "NA", "NAN", "NULL"} for r in eligible)
for kind, cutoff in (("REG", 3), ("REG", 19), ("POST", 23)):
    counts = [sum(r["season_type"] == kind and int(r["week"]) < cutoff
                  and low <= Decimal(r["yardline_100"]) <= high for r in eligible)
              for low, high in ((0, 20), (80, 100), (20, 20))]
    print(kind, cutoff, counts)
```

For an individual filtered cohort, add the same range predicate to the earlier
independent EPA recipe; use `posteam` for offense or `defteam` for defense. The
normal report CLI uses `--yardline-min` and `--yardline-max`. The recipes are
checks of this artifact, not replacements for production missing-data validation.

## Score extension (2026-10-03)

The same unchanged pinned snapshot contains `score_differential`. Across 49,492
raw rows, 2,713 scores are missing. All 34,902 eligible plays have observed whole
scores, serialized as integer strings, ranging from -46 to 46. Every eligible
identity and score matches the adapter exactly, and every eligible score equals
the source's pre-play `posteam_score - defteam_score`. There are 1,456 eligible
plays whose pre/post-play scores differ. This checks internal source consistency,
not independently reconstructed gamebook scores. The source's broader numeric
dictionary is narrowed to the explicit [whole-point contract](DATA_CONTRACT.md#optional-pre-play-score).

With snapshot loading/auditing blocked from network access, 2,304 reports matched
independent raw selections and Decimal EPA calculations: 32 teams × two roles ×
REG before 3 / REG before 19 / POST before 23 × no field range / 0..20 / 80..100 ×
scores <= -1 / exactly 0 / >= 1 / -7..7 inclusive. Exact play/game/dropback/EPA
counts, filter-stage removals, source manifests, and situation play totals agree;
means/rates agree within absolute tolerance `1e-12`. The 576 corresponding reports
without score filtering (including field-only reports) exactly match merged
PR #6's implementation at `5d12321`.

For either role, summing team play counts without a field restriction gives:

| Season and exclusive cutoff | Offense trailing | Tied | Offense leading | Score -7..7 |
| --- | ---: | ---: | ---: | ---: |
| REG before week 3 | 1,863 | 696 | 1,252 | 2,546 |
| REG before week 19 | 16,011 | 6,097 | 11,227 | 21,486 |
| POST before week 23 | 785 | 188 | 594 | 955 |

The first three columns partition the eligible cohort for this complete-score
snapshot; -7..7 overlaps them and must not be added to their sum. A defense's
trailing column still means the **opposing offense** trails. These counts are
reconciliation checks, not opponent-adjusted rankings or predictive validation.

After verifying the pinned snapshot with the audit command above, this independent
raw-record recipe reproduces the table and component check:

```python
import csv
import gzip
from pathlib import Path

root = Path("data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06")
with gzip.open(root / "play_by_play_2024.csv.gz", "rt", encoding="utf-8-sig", newline="") as source:
    rows = [r for r in csv.DictReader(source) if r["season"] == "2024"
            and r["play_type"] in {"run", "pass"}
            and all(r[f] == "0" for f in ("two_point_attempt", "qb_kneel", "qb_spike"))]
assert len(rows) == 34902
assert all(int(r["score_differential"]) == int(r["posteam_score"]) - int(r["defteam_score"]) for r in rows)
assert sum(r["score_differential"] != r["score_differential_post"] for r in rows) == 1456
for kind, cutoff in (("REG", 3), ("REG", 19), ("POST", 23)):
    scores = [int(r["score_differential"]) for r in rows
              if r["season_type"] == kind and int(r["week"]) < cutoff]
    print(kind, cutoff, [sum(s < 0 for s in scores), sum(s == 0 for s in scores),
                         sum(s > 0 for s in scores), sum(-7 <= s <= 7 for s in scores)])
```

This recipe relies on verified serialization/missingness in this artifact; it is
not a general parser. To replay the README score example using the earlier
independent EPA recipe, additionally select `posteam == "CAR"`, REG before week 3,
`0 <= yardline_100 <= 20`, and `score_differential <= -1`. The stages contain
101 → 7 → 7 plays, with two games, seven dropbacks, seven observed EPA values,
one positive EPA, and Decimal EPA sum `-5.474402579713683`. No missing-context
removals occur in this snapshot, so synthetic tests exercise those failure paths.
No raw bytes or previous dated evidence were changed. Time context, historical
availability, external gamebooks, uncertainty, and forecast evaluation remain
outside this unit's verification scope.

## Clock extension (2026-10-04)

The same unchanged artifact contains `qtr` and `quarter_seconds_remaining`.
There are zero raw missing periods and five raw missing clocks; neither field
is missing among the 34,902 eligible plays. All eligible values are integer
strings and match the adapter by `(game_id, play_id)` exactly. Every eligible
quarter clock equals `60 * minutes + seconds` from the source's start-of-play
`time` string. This is internal source consistency, not official gamebook review.

Eligible regulation clocks span 0..900, including **two eligible plays at zero**.
All 174 eligible OT plays are REG `qtr=5`, with clocks 70..600; there is no POST
OT in this artifact. For all 174, `game_seconds_remaining` equals the quarter
clock, supporting explicit period selection rather than treating that field as
a regulation-only game countdown. Multiple OT periods and the broader 0..900 OT
contract are synthetic test coverage, not observed findings from this season.

With socket creation blocked for snapshot loading/auditing, 7,680 reports match
independent raw selection and Decimal EPA calculations: 32 teams × two roles ×
REG before 3 / REG before 19 / POST before 23 × four context selections × ten
time selections. Contexts are no field/score filter, yardline <=20, score <=-1,
and yardline >=80 with score -7..7. Times are each of Q1/Q2/Q3/Q4/OT alone,
Q2/Q4/OT with clock 0..120, Q4 exactly 0, and Q4 clock 600..900.

Play/game/dropback/EPA counts, period/clock-stage removals, provenance, situation
keys, and every situation's measurements agree; rates/means use absolute tolerance
`1e-12`. The 768 corresponding reports without time options exactly match merged
PR #7's report implementation at `7f4bfb3`, including field/score-filtered output.
All 130 offline tests pass on Python 3.11/3.12/3.13; no test needs this real season.
Missing and invalid contexts are exercised synthetically, since eligible contexts
are complete in the recorded artifact. No raw files or dated evidence were changed.

For either role, summing team play counts without field/score filters gives:

| Season and exclusive cutoff | Q2 clock 0..120 | Q4 clock 0..120 | All OT | OT clock 0..120 |
| --- | ---: | ---: | ---: | ---: |
| REG before week 3 | 256 | 175 | 18 | 0 |
| REG before week 19 | 2,443 | 1,519 | 174 | 4 |
| POST before week 23 | 108 | 48 | 0 | 0 |

OT 0..120 is a subset of all OT; do not add those columns. These are counts of
eligible completed plays, not all snaps, independent observations, or forecasts.

After verifying the pinned snapshot with the audit command above, this read-only
recipe reproduces the table directly from source records:

```python
import csv
import gzip
from pathlib import Path

root = Path("data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06")
with gzip.open(root / "play_by_play_2024.csv.gz", "rt", encoding="utf-8-sig", newline="") as source:
    rows = [{k: r[k] for k in ("season_type", "week", "qtr", "quarter_seconds_remaining", "time")}
            for r in csv.DictReader(source) if r["season"] == "2024"
            and r["play_type"] in {"run", "pass"}
            and all(r[f] == "0" for f in ("two_point_attempt", "qb_kneel", "qb_spike"))]
assert len(rows) == 34902
for r in rows:
    minute, second = map(int, r["time"].split(":"))
    assert int(r["quarter_seconds_remaining"]) == 60 * minute + second
for kind, cutoff in (("REG", 3), ("REG", 19), ("POST", 23)):
    pairs = [(int(r["qtr"]), int(r["quarter_seconds_remaining"])) for r in rows
             if r["season_type"] == kind and int(r["week"]) < cutoff]
    print(kind, cutoff, [sum(q == 2 and 0 <= c <= 120 for q, c in pairs),
                         sum(q == 4 and 0 <= c <= 120 for q, c in pairs),
                         sum(q >= 5 for q, c in pairs),
                         sum(q >= 5 and 0 <= c <= 120 for q, c in pairs)])
```

This recipe uses the verified serialization and completeness of this artifact;
it is not a general-purpose loader. For the README time example, add `qtr == 4`
and `0 <= quarter_seconds_remaining <= 120` to the earlier independent EPA
recipe (CAR offense, REG before week 3). It selects four plays from one game,
one dropback, four observed EPA, zero positive EPA, and Decimal EPA sum
`-3.350863943167499`. These tiny samples are software checks, not tactical advice.
Historical availability, upstream model training, external gamebooks, matched
baselines, and game-level uncertainty remain outside this verification scope.

## League-baseline extension (2026-10-05)

The unchanged pinned snapshot was checked against independent raw-record
leave-team-out selections and Decimal EPA calculations. All **2,048** requested
comparisons agree: 32 teams × two roles × REG before 1/3/19 or POST before 23 ×
eight context selections. Contexts were unrestricted; yardline <=20; yardline >=80;
score exactly 0; score <=-1; Q4 clock 0..120; combined yardline <=20, score <=-1,
Q2 clock 0..120; and OT clock 0..900.

Overall and matching down/distance counts, rates, EPA means, and differences
reconcile (counts/categories exact; floating-point absolute tolerance `1e-12`).
Checks also cover the baseline population ledger, every active filter stage,
observed teams, shared-game counts, disjoint selected/baseline identities, empty
cohorts, and snapshot provenance. The corresponding 2,048 reports without the
option exactly match merged PR #8 at `bbf4299`, despite the shared-filter refactor.
Snapshot loading was checked with socket creation blocked. All 146 offline tests
pass on Python 3.11/3.12/3.13; synthetic tests supply the missing EPA/context cases
that this complete-context eligible snapshot does not contain.

These CAR/2024/REG-before-week-3 checks show why coverage and denominators matter:

| Selected role/context | Selected plays | Baseline plays / games | Baseline teams | Baseline dropbacks | Shared games |
| --- | ---: | ---: | ---: | ---: | ---: |
| Offense, no optional contexts | 101 | 3,710 / 32 | 31 | 2,171 | 2 |
| Offense, Q4 clock 0..120 | 4 | 171 / 29 | 27 | 112 | 0 |
| Defense, no optional contexts | 124 | 3,687 / 32 | 31 | 2,191 | 2 |
| Defense, Q4 clock 0..120 | 0 | 175 / 30 | 29 | 113 | 0 |

Every listed baseline play has observed EPA. The unrestricted offensive baseline
has 1,590 positive EPA values and Decimal sum `-76.2939792890668281486`; its
EPA/play is about -0.0205644. CAR's existing -0.4877802 minus that baseline is
about -0.4672157 expected points per observed play. These are unadjusted historical
software checks, not a team-strength estimate. The last row has real baseline
observations but **null differences**, because the selected defense cohort is empty.
Team counts are observed after filtering, not assumed to be 31. Shared games are
intersections; do not add selected and baseline game counts as distinct games.

After verifying this snapshot, the following independent source recipe reproduces
the first row and its EPA calculation. Use `role="defteam"` for defense and set
`late_q4=True` for the last two-minute Q4 clock range. The range is pre-play and
does not include overtime. Run with the existing CLI plus `--compare-league` to
compare against the report; do not use generated report metrics as expectations.

```python
import csv
from decimal import Decimal
import gzip
from pathlib import Path

root = Path("data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06")
role, late_q4 = "posteam", False
with gzip.open(root / "play_by_play_2024.csv.gz", "rt", encoding="utf-8-sig", newline="") as source:
    rows = [{k: r[k] for k in (role, "game_id", "qb_dropback", "epa")}
            for r in csv.DictReader(source) if r["season"] == "2024" and r["season_type"] == "REG"
            and int(r["week"]) < 3 and r["play_type"] in {"run", "pass"}
            and all(r[f] == "0" for f in ("two_point_attempt", "qb_kneel", "qb_spike"))
            and (not late_q4 or (int(r["qtr"]) == 4 and 0 <= int(r["quarter_seconds_remaining"]) <= 120))]
selected = [r for r in rows if r[role] == "CAR"]
baseline = [r for r in rows if r[role] != "CAR"]
assert len(selected) + len(baseline) == len(rows)
epa = [Decimal(r["epa"]) for r in baseline]
print(len(selected), len(baseline), len({r["game_id"] for r in baseline}),
      len({r[role] for r in baseline}), sum(r["qb_dropback"] == "1" for r in baseline),
      len({r["game_id"] for r in selected} & {r["game_id"] for r in baseline}),
      len(epa), sum(v > 0 for v in epa), sum(epa), sum(epa) / len(epa) if epa else None)
```

The recipe depends on this artifact's verified serialization and observed complete
EPA/context fields, not a replacement for the strict loader. No raw data, manifest,
or previous dated evidence was changed. Matching broad ranges and buckets is not
opponent adjustment, historical-information reconstruction, or game-independent
inference. Game-level uncertainty and the static brief remain unfinished.

## Uncertainty extension (2026-10-06)

The same pinned artifact was loaded with socket creation blocked. Its 34,902
eligible raw records and decoded SHA-256 remain unchanged. Eight comparisons were
checked: CAR offense/defense × REG before week 3/19 × unrestricted/Q4 clock 0..120,
each with 1,000 bootstrap repetitions and seed 20261006.

An independent read-only verifier selected raw CSV records, constructed game-level
numerators/denominators and Decimal EPA sums, and multiplied them by the joint
seeded game-multiplicity matrix. NumPy's linear quantiles provided a separate
interval implementation. Overall and every reported down/distance bucket agree:
support, statuses, and defined/undefined counts exactly; interval bounds within
`1e-12` absolute tolerance. Eight reports without uncertainty exactly match merged
PR #9 (`af19425`). NumPy was used only for this check; reporting/tests remain
standard-library-only. This is implementation verification, not coverage calibration.

| CAR role and REG cutoff | Context | Selected contributing EPA games | Defined / requested replicates | Selected EPA interval |
| --- | --- | ---: | ---: | --- |
| Offense, before week 3 | Unrestricted | 2 | 879 / 1,000 | Withheld: insufficient games |
| Offense, before week 3 | Q4 clock 0..120 | 1 | 644 / 1,000 | Withheld: insufficient games |
| Defense, before week 3 | Q4 clock 0..120 | 0 | 0 / 1,000 | Withheld: undefined estimate |
| Offense, before week 19 | Unrestricted | 17 | 1,000 / 1,000 | Approximately -0.1752253 to 0.0616823 |
| Defense, before week 19 | Unrestricted | 17 | 1,000 / 1,000 | Approximately 0.0898787 to 0.2311647 |

Both full-season rows still warn `few_games=true`. Their resampling frame contains
272 distinct games when comparison is on, not 17 + 272 independent games. EPA is
offense-relative, including the defense row. These are nominal exploratory
resampling intervals for descriptive means, not validated significance or team
strength. Early-season undefined draws arise when the union-game sample contains
no selected-team game; they are not retried or silently turned into zeros.

Replay the unrestricted offense example using the existing pinned snapshot:

```sh
snapshot_dir=data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06
PYTHONPATH=src python3 -m opponent_intelligence \
  --snapshot "$snapshot_dir" \
  --source-label 'nflverse 2024 retrospective snapshot; acquired 2026-09-30 UTC' \
  --team CAR --season 2024 --before-week 19 --compare-league \
  --bootstrap-repetitions 1000 --bootstrap-seed 20261006
```

Use `--side defense`, `--before-week 3`, and/or `--period Q4 --clock-max 120`
for the remaining cases. The following separate raw-record recipe reproduces the
early unrestricted offense's two supporting games, 32-game union, and 879 defined
versus 121 undefined draws; it does not read generated report values:

```python
import csv
import gzip
from pathlib import Path
from random import Random

root = Path("data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06")
with gzip.open(root / "play_by_play_2024.csv.gz", "rt", encoding="utf-8-sig", newline="") as source:
    rows = [(r["game_id"], r["posteam"]) for r in csv.DictReader(source)
            if r["season"] == "2024" and r["season_type"] == "REG" and int(r["week"]) < 3
            and r["play_type"] in {"run", "pass"}
            and all(r[f] == "0" for f in ("two_point_attempt", "qb_kneel", "qb_spike"))]
games = sorted({game for game, _ in rows})
selected = {game for game, team in rows if team == "CAR"}
rng, valid = Random(20261006), 0
for _ in range(1000):
    # Consume all G draws even if a selected game is encountered early.
    drawn = {games[rng.randrange(len(games))] for _ in games}
    valid += bool(selected & drawn)
print(len(selected), len(games), valid, 1000 - valid)  # 2 32 879 121
```

This recipe relies on the pinned artifact's verified complete eligible EPA fields;
it is not a replacement for loader validation or a missing-EPA support check.
Report-only generation observed 0.014–0.625 seconds for these eight requests on
this host, excluding load/verification time. That is a smoke check, not a scale
benchmark or a cross-machine performance guarantee. No raw source, manifest,
original fixture, or previous dated evidence was modified.
