# NFL Opponent Intelligence

A reproducible foundation for weekly NFL opponent preparation: turn play-by-play
data into offense tendencies with explicit sample sizes, metric definitions,
source fingerprints, and a cutoff that excludes the week being prepared for.

**Status:** first working increment. The local CSV-to-JSON pipeline and synthetic
edge-case tests work. Real-season ingestion, a web interface, opponent adjustment,
and deployment are still on the [roadmap](ROADMAP.md). This is an independent
portfolio project, with no NFL or team affiliation.

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
values, and duplicate play identities cause an error rather than silent repair.

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
4. `tests/test_pipeline.py` checks independently calculated results, malformed
   inputs, time boundaries, and command-line behavior.

The pure analytical functions can later serve a FastAPI application. Storage and
the React interface will be added after the pipeline works on a verified real
season. There is currently no database, external API dependency, or trained model.

## Project records

- [Roadmap and next task](ROADMAP.md)
- [Current engineering status](docs/STATUS.md)
- [Daily learning log](LEARNING_LOG.md)
- [Data contract and provenance](docs/DATA_CONTRACT.md)
- [Metric definitions](docs/METRICS.md)
- [Portfolio presentation plan](docs/PORTFOLIO.md)
- [Contribution and review workflow](CONTRIBUTING.md)
- [Daily sync, commit identity, and recovery](docs/DAILY_WORKFLOW.md)

The GitHub Actions workflow is committed. Local verification and observed remote
CI results are recorded separately in the status and learning log.
