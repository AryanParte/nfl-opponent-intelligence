# NFL Opponent Intelligence

A reproducible foundation for weekly NFL opponent preparation: turn play-by-play
data into offense tendencies and defense-side summaries with explicit sample sizes,
metric definitions, source fingerprints, and a cutoff that excludes the week being
prepared for.

**Status:** the offline CSV/snapshot-to-JSON pipeline and immutable 2024 raw-data
acquisition work. The recorded 2024 snapshot passes the adapter audit and selected
cohort reconciliations. Reports can select a team's offense or defense while
keeping EPA offense-relative, with optional pre-play field-position, score, and
period/clock filters, matched league baselines, and opt-in exploratory game-level
resampling intervals. A separate offline JSON-to-Markdown command produces a
traceable historical brief. P1.3's availability audit is complete: personnel and
motion measurements remain deferred because they require separate source
integration; shotgun and no-huddle are not substitutes. A web interface,
adjustment, and deployment remain on the [roadmap](ROADMAP.md). This is an independent portfolio
project, with no NFL or team affiliation or predictive-validation claim.

[GitHub](https://github.com/AryanParte/nfl-opponent-intelligence) is the permanent
source of truth. The daily workflow continues existing branches and the roadmap,
with tests, self-review, learning notes, and pushed commits for each completed unit.

## Try it

Requires Python 3.11 or later. The current runtime and tests use only the standard
library; the following commands need no package installation or network access.
Run them from the repository root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v

PYTHONPATH=src python3 -m opponent_intelligence \
  --csv tests/fixtures/synthetic_pbp.csv \
  --source-label 'Synthetic verification fixture; not real NFL observations' \
  --team CAR --season 2024 --before-week 3
```

The fixture is entirely invented. Team abbreviations illustrate the schema; its
numbers make no statement about any real team. The command describes weeks 1–2
of the chosen season; week 3 and later, other offenses, and playoff rows are
excluded. It produces these hand-checkable totals:

| Output | Synthetic result |
| --- | ---: |
| Eligible cohort plays / games | 6 / 2 |
| Dropbacks / designed runs | 3 / 3 |
| Dropback rate | 50% |
| Observed / missing EPA | 5 / 1 |
| EPA per observed play | 0.04 |
| Success rate among observed EPA | 60% |

JSON also includes down/distance splits, all input exclusion counts, the exact
input SHA-256, and warnings. Empty rates are `null`. Invalid schema, malformed
values, unknown play types, and duplicate play identities cause an error rather
than silent repair. Recognized missing play types are excluded with a separate
audit count; see the [input contract](docs/DATA_CONTRACT.md).

### Select the defense

`--side offense` is the default. To describe the offenses facing a selected defense:

```sh
PYTHONPATH=src python3 -m opponent_intelligence \
  --csv tests/fixtures/synthetic_pbp.csv \
  --source-label 'Synthetic verification fixture; not real NFL observations' \
  --team ATL --side defense --season 2024 --before-week 3
```

This invented example contains five plays, three dropbacks, and four observed EPA
values: 0.05 EPA/play and 75% offensive success allowed. EPA is **not sign-flipped**;
success still means offensive EPA > 0, not defensive stops. Down/distance describes
the opposing offense. Denominator rules, missing-data handling, and the exclusive
week cutoff are unchanged.

Reports now use JSON schema v2: `cohort.team` and `cohort.side` replace
`cohort.offense`, with explicit `metric_context`. Existing commands still default
to offense and retain the same measurements, but JSON consumers must migrate;
see [schema and interpretation](docs/METRICS.md#report-schema-v2).

### Compare with other teams

Add `--compare-league` to include a pooled baseline excluding the selected team
in the same role. This example is entirely synthetic and still needs no network:

```sh
PYTHONPATH=src python3 -m opponent_intelligence \
  --csv tests/fixtures/synthetic_pbp.csv \
  --source-label 'Synthetic verification fixture; not real NFL observations' \
  --team CAR --season 2024 --before-week 3 --compare-league
```

The invented baseline has just one ATL offensive play with EPA 3, compared with
CAR's six plays and EPA/play 0.04: the difference is -2.96. Its tiny sample warning
is intentional; this fixture is not league coverage or evidence about either team.

Both populations use the same season/type, exclusive week cutoff, and requested
field/score/period/clock filters. Each selected down/distance bucket gets its own
matching baseline; missing matches produce null differences, not a fallback to
the league-wide rate. Rate differences are **percentage points**, and EPA
differences remain offense-relative. Defense mode compares production allowed by
other defenses, without reversing EPA or success.

The JSON exposes observed baseline teams, play/game/EPA counts, missingness,
shared games, and selected-minus-baseline differences. It pools individual plays,
not team averages; overall context mixes may still differ. No comparison is added
unless requested. See the [comparison contract](docs/METRICS.md#matched-league-baselines)
and [real-data verification](docs/REAL_DATA_AUDIT.md#league-baseline-extension-2026-10-05).

### Check game-level support and uncertainty

Add `--bootstrap-repetitions 1000 --bootstrap-seed 0` for reproducible whole-game
resampling. With comparison enabled, both populations use the same game draws:

```sh
PYTHONPATH=src python3 -m opponent_intelligence \
  --csv tests/fixtures/synthetic_pbp.csv \
  --source-label 'Synthetic verification fixture; not real NFL observations' \
  --team CAR --season 2024 --before-week 3 --compare-league \
  --bootstrap-repetitions 1000 --bootstrap-seed 0
```

The invented fixture has only two selected games and one baseline game: its
overall intervals are deliberately `null` with `insufficient_games`, while existing
point estimates remain available. More resamples cannot fix insufficient observed games.
Supported cohorts can have nominal 95% percentile intervals, but these are
exploratory—not calibrated coverage, significance tests, or predictions. Reports
show per-metric game support, undefined draws, small-game warnings, and degenerate
interval states. See the [method and JSON contract](docs/UNCERTAINTY.md), including
the limits of repeated teams/opponents across games.

### Read a historical opponent brief

Open the [synthetic brief](docs/examples/synthetic.md) or the
[retrospective CAR offense example](docs/examples/car-2024-reg-before-week-19.md).
The latter summarizes 984 eligible plays across 17 games from the pinned 2024
snapshot, acquired in 2026—not a forecast or a historically available 2024 scouting
report. Both include source fingerprints, denominators, matching baselines,
unavailable intervals, few-game warnings, and interpretation limits.

Replay the committed aggregate JSON without downloading raw data:

```sh
PYTHONPATH=src python3 -m opponent_intelligence.brief \
  --report docs/examples/car-2024-reg-before-week-19.report.json
```

Or pipe a newly generated synthetic report directly into the renderer:

```sh
PYTHONPATH=src python3 -m opponent_intelligence \
  --csv tests/fixtures/synthetic_pbp.csv \
  --source-label 'Synthetic verification fixture; not real NFL observations' \
  --team CAR --season 2024 --before-week 3 --compare-league \
  --bootstrap-repetitions 200 --bootstrap-seed 0 \
  | PYTHONPATH=src python3 -m opponent_intelligence.brief --report -
```

Markdown goes to stdout; existing JSON commands are unchanged. Invalid saved
reports fail before any brief is printed. See the [brief contract and replay
instructions](docs/BRIEFS.md), including what a fingerprint does **not** prove.

### Personnel and motion: known limits

The pinned PBP snapshot has neither personnel nor motion columns. The
[availability and licensing audit](docs/PERSONNEL_MOTION.md) records the direct
fields, unsuitable proxies, separately documented sources, and a replayable
offline inventory. It also explains why data published after a season cannot be
assumed available during that season. No personnel or motion rate is exposed by
the current reports, and no supplementary dataset has been acquired or joined.

## Acquire a reproducible raw snapshot

The optional acquisition command downloads the reviewed 2024 nflverse gzip CSV,
checks the published digest, and saves an immutable snapshot with a provenance
manifest. Its first run requires network access; subsequent runs verify the cache
offline. Explicit `--refresh` acquires changed upstream bytes without overwriting
older snapshots. Raw data stays out of Git.

```sh
PYTHONPATH=src python3 -m opponent_intelligence.fetch --season 2024
```

[Acquisition, attribution, and verification evidence](docs/INGESTION.md) explains
the cache. Use the explicit snapshot directory printed by acquisition to audit or
report offline; neither command fetches data or follows the mutable cache pointer:

```sh
snapshot_dir=data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06
PYTHONPATH=src python3 -m opponent_intelligence.audit --snapshot "$snapshot_dir"
PYTHONPATH=src python3 -m opponent_intelligence \
  --snapshot "$snapshot_dir" \
  --source-label 'nflverse 2024 retrospective snapshot; acquired 2026-09-30 UTC' \
  --team CAR --season 2024 --before-week 3
```

This pinned example requires the recorded snapshot to be present. If upstream has
changed, a fresh acquisition produces a different directory; do not relabel it as
this snapshot. [Real-data audit and limits](docs/REAL_DATA_AUDIT.md) records the
49,492-row reconciliation and independently checked cohort denominators.
Snapshot reports include the source manifest and both byte fingerprints.
`--csv` remains the uncompressed, caller-labeled path; the synthetic demo stays
independent of GitHub availability and credentials.

### Limit field position

Using that same pinned snapshot, select plays where opposing offenses faced CAR
at or within 20 yards of CAR's goal line:

```sh
PYTHONPATH=src python3 -m opponent_intelligence \
  --snapshot "$snapshot_dir" \
  --source-label 'nflverse 2024 retrospective snapshot; acquired 2026-09-30 UTC' \
  --team CAR --side defense --season 2024 --before-week 3 \
  --yardline-min 0 --yardline-max 20
```

Bounds are inclusive and use the offense's `yardline_100` coordinates for either
side. Omit one bound to use 0 or 100; omit both to leave the cohort unfiltered.
Missing positions are excluded only when filtering, with explicit counts and a
warning. Filtering requires the source column, even for an otherwise empty cohort.
The original synthetic fixture omits it intentionally; the offline field-position
tests generate separate synthetic inputs. See [definitions](docs/METRICS.md#pre-play-field-position-ranges)
and the [real-data check](docs/REAL_DATA_AUDIT.md#field-position-extension-2026-10-02).

### Limit the pre-play score

Select CAR offensive plays while trailing, within 20 yards of the opposing goal
line, using the same pinned snapshot:

```sh
PYTHONPATH=src python3 -m opponent_intelligence \
  --snapshot "$snapshot_dir" \
  --source-label 'nflverse 2024 retrospective snapshot; acquired 2026-09-30 UTC' \
  --team CAR --season 2024 --before-week 3 \
  --yardline-max 20 --score-max -1
```

`--score-min` / `--score-max` are inclusive whole-point bounds on pre-play
`score_differential` (offense minus defense). One omitted end is unbounded; omit
both for no score filter. Use `--score-min 0 --score-max 0` for ties, or
`--score-min 1` for an offense leading. For `--side defense`, the sign still refers
to the **opposing offense**, not the selected defense. Post-play scores are never
used as a substitute.

These optional filters exclude unknown context only when requested. Field position
runs first, then score, with explicit order and separate before/missing/outside/
after counts so overlaps are not counted twice. This example selects seven plays
from two games; it is a retrospective software check, not a scouting conclusion.
See [score semantics](docs/METRICS.md#pre-play-score-ranges) and
[reconciliation evidence](docs/REAL_DATA_AUDIT.md#score-extension-2026-10-03).

### Select a period and pre-play clock

Select CAR offensive plays starting with at most 120 seconds left in Q4:

```sh
PYTHONPATH=src python3 -m opponent_intelligence \
  --snapshot "$snapshot_dir" \
  --source-label 'nflverse 2024 retrospective snapshot; acquired 2026-09-30 UTC' \
  --team CAR --season 2024 --before-week 3 \
  --period Q4 --clock-max 120
```

`--period` accepts `Q1`, `Q2`, `Q3`, `Q4`, or `OT` (all overtime periods).
Clock bounds are inclusive whole seconds remaining **at the start of the play**,
not elapsed time or the end-of-play clock. An explicit period is required with
`--clock-min` / `--clock-max`; one omitted end defaults to 0 or 900. Zero is valid.
Period-only selection does not require an observed clock. With neither period nor
clock flags, previous output is unchanged.

The example excludes OT; it is not a "last two minutes of the game" definition.
An OT range applies separately within each overtime period, not to cumulative
overtime elapsed time. Field/score filters can be combined: selection order is
field position → score → period → clock, after team/season/week selection. Missing
context is excluded only by its requested filter, with separate counts/warnings.
Absent required source columns are errors, not empty results. The original fixture
has no time columns; clock tests generate explicitly synthetic inputs. See
[clock semantics](docs/METRICS.md#pre-play-period-and-clock) and
[pinned-snapshot evidence](docs/REAL_DATA_AUDIT.md#clock-extension-2026-10-04).

## The football decision

The eventual user is an analyst preparing an opponent brief: how often does an
offense drop back in comparable situations, how effective are those plays, and
how much evidence supports each observation? This first increment establishes
the measurement contract needed to answer those questions reliably.

Dropbacks include sacks and scrambles. Kneels, spikes, conversion attempts, and
non-run/pass plays are excluded. Missing EPA still contributes to the play-call
denominator. [Metric definitions and limitations](docs/METRICS.md) explain the
inclusion policy and why the current output is descriptive rather than a forecast.

## How the code fits together

1. `src/opponent_intelligence/pbp.py` validates a local CSV and records exclusions.
2. `src/opponent_intelligence/report.py` selects the historical cohort and computes
   totals and down/distance splits.
3. `src/opponent_intelligence/__main__.py` exposes the workflow as a JSON command.
4. `src/opponent_intelligence/fetch.py` and `snapshots.py` acquire and verify raw
   data separately from analytical reporting.
5. `ingestion.py` binds parsed gzip bytes to provenance; `audit.py` reconciles raw
   coverage, missingness, and eligible identities against the adapter.
6. `tests/test_pipeline.py` checks independently calculated results, malformed
   inputs, time boundaries, and command-line behavior.
   `tests/test_snapshots.py` tests acquisition and cache failure cases offline;
   `tests/test_ingestion.py` tests provenance, audit, and report integration.
   `tests/test_defense_reports.py` checks role selection, reciprocal measurements,
   denominator accounting, and unaltered EPA interpretation.
   `tests/test_field_position.py` checks optional-field validation, inclusive bounds,
   scoped missingness, legacy compatibility, and CLI failures.
   `tests/test_score_filters.py` checks signed whole-point bounds, pre/post-play
   separation, combined-filter accounting, reciprocal roles, and compatibility.
   `tests/test_clock_filters.py` checks period/clock bounds, OT separation,
   zero versus missing, four-stage accounting, and unchanged defaults.
   `tests/test_league_comparison.py` checks leave-team-out pooling, matching buckets,
   explicit difference units, independent population counts, and unavailable results.
7. `uncertainty.py` resamples shared whole games with optional support-aware intervals.
   `tests/test_uncertainty.py` checks all 3,125 resamples of a five-game synthetic
   example independently, plus missingness, support, pairing, and reproducibility.
8. `brief.py` renders saved JSON as deterministic Markdown; `brief_validation.py`
   checks the consumed schema and cross-field relationships. `tests/test_brief.py`
   covers units, support, unsafe text, invalid saved inputs, and byte-exact examples.
9. `availability.py` audits exact personnel/motion candidate columns offline,
   separating schema absence from missing observations and zero-valued indicators.
   `tests/test_availability.py` verifies counts, provenance and safe failure states.

The pure analytical functions can later serve a FastAPI application. Storage and
the React interface remain deferred until useful opponent briefs exist.
The reporting core has no database, runtime API dependency, or trained
model; only the explicit acquisition command contacts GitHub.

## Project records

- [Roadmap and next task](ROADMAP.md)
- [Current engineering status](docs/STATUS.md)
- [Daily learning log](LEARNING_LOG.md)
- [Data contract and provenance](docs/DATA_CONTRACT.md)
- [Raw snapshots, source terms, and acquisition evidence](docs/INGESTION.md)
- [Real-season audit and cohort reconciliation](docs/REAL_DATA_AUDIT.md)
- [Metric definitions](docs/METRICS.md)
- [Exploratory uncertainty method](docs/UNCERTAINTY.md)
- [Historical brief format and examples](docs/BRIEFS.md)
- [Personnel/motion availability and scope decision](docs/PERSONNEL_MOTION.md)
- [Portfolio presentation plan](docs/PORTFOLIO.md)
- [Contribution and review workflow](CONTRIBUTING.md)
- [Daily sync, commit identity, and recovery](docs/DAILY_WORKFLOW.md)

The GitHub Actions workflow is committed. Local verification and observed remote
CI results are recorded separately in the status and learning log.
