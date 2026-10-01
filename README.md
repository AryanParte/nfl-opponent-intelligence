# NFL Opponent Intelligence

A reproducible foundation for weekly NFL opponent preparation: turn play-by-play
data into offense tendencies and defense-side summaries with explicit sample sizes,
metric definitions, source fingerprints, and a cutoff that excludes the week being
prepared for.

**Status:** the offline CSV/snapshot-to-JSON pipeline and immutable 2024 raw-data
acquisition work. The recorded 2024 snapshot passes the adapter audit and selected
cohort reconciliations. Reports can select a team's offense or defense while
keeping EPA offense-relative. Context filters, a web interface, adjustment, and
deployment remain on the [roadmap](ROADMAP.md). This is an independent portfolio
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
- [Portfolio presentation plan](docs/PORTFOLIO.md)
- [Contribution and review workflow](CONTRIBUTING.md)
- [Daily sync, commit identity, and recovery](docs/DAILY_WORKFLOW.md)

The GitHub Actions workflow is committed. Local verification and observed remote
CI results are recorded separately in the status and learning log.
