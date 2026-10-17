# Offline Run/Pass evidence contract v1

First P1.5 slice, 2026-10-17. This is a Python-only **descriptive evidence builder**,
not a new API, CLI, browser mode, predictive model or recommendation engine. Scout
schema v2, endpoints, briefs and UI stay unchanged. The request and JSON-compatible
result have a separate `contract_version: 1`; do not send this result to the Scout
brief renderer or treat it as a schema-v2 report.

## Reproduce the invented example

From the repository root, with Python 3.11+ and no installed dependencies/network:

```sh
PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path
from opponent_intelligence.decision import DecisionRequest, build_decision_evidence
from opponent_intelligence.pbp import load_csv

dataset = load_csv(Path("tests/fixtures/synthetic_pbp.csv"))
request = DecisionRequest(team="CAR", season=2024, before_week=3,
                          down=1, distance_min=10, distance_max=10)
result = build_decision_evidence(
    dataset, request, source_label="Invented test fixture; not real NFL observations",
)
print(json.dumps(result, indent=2, allow_nan=False))
PY
```

The fixture yields three first-and-ten plays in two games: Run has one play,
frequency 1/3, EPA 0 and success 0; Pass has two plays, frequency 2/3, EPA 0.6 and
success 1. Both samples are tiny. These numbers describe **invented rows**, not
Carolina performance. `preferred_candidate` is null even though one mean is higher.
For real offline work, load the already acquired immutable snapshot with the
existing `ingestion.load_snapshot` function; the builder never opens paths or
downloads data. The caller retains responsibility for a truthful source label.

## Request and selection

`DecisionRequest` is frozen and keyword-only. Values are validated by
`build_decision_evidence(dataset, request, source_label=...)`. Unknown arguments
raise `TypeError`; invalid supported values raise `ValueError`. No silent coercion.

| Request | Accepted semantics |
| --- | --- |
| `team` | Uppercase 2–3-letter source abbreviation; offense only. Syntactic validation is not a team registry. Unknown but well-formed teams yield an empty cohort. |
| `season`, `season_type` | Integer 1999–9999, `REG` (default) or `POST`; no cross-season/type pooling. A snapshot manifest's season must agree. |
| `before_week` | Integer 1–23, exclusive. Target-week and later outcomes are excluded; week 1 is valid and empty. |
| `down` | Required exact integer 1–4, not a down bucket. |
| `distance_min`, `distance_max` | Both required integers 0–100, inclusive and ordered; equal bounds mean exact recorded yards to go. No short/medium/long widening. |
| `yardline_min/max`, `score_min/max`, `period`, `clock_min/max` | Same pre-play, offense-relative bounds, optional-header checks, missing-value exclusions and defaults as [Scout](METRICS.md). Clock requires a period. |
| `minimum_plays` | Positive integer count-warning threshold, default 30; not an accuracy, independence or ranking guarantee. |

Booleans, numeric strings and floats are not accepted for integer fields. Field
position alone accepts finite integers/floats in 0–100. No `side`, opponent,
play-family, filesystem-path, model, interval or fallback option exists here.
Defense remains a Scout capability, with offensive production **allowed** rather
than sign-flipped EPA or a defensive stop rate.

Selection order: season/type/week and offense → field position → score → period →
clock → exact down → distance. Only active optional filters are included. Each
stage records `before = missing + outside + after`; missingness is conditional on
surviving prior stages. Down/distance are required at ingestion, so their missing
counts are zero for a validated Dataset. Input/exclusion totals and source hash
continue to describe the **original full dataset**, not a relabeled filtered file.

Missing optional observations stay in the cohort when their filter is omitted.
An absent requested column is an error even when the selected team has no plays;
a present but all-missing column can yield an empty cohort. No imputation, nearby
distance/team/year fallback, or borrowing Scout's grouped buckets occurs.

These are historical selectors, not a game-state/rules validator. Zero yards means
recorded zero, not an inferred inches value. Goal-to-go is not independently
identified. OT means all recorded periods >=5; clock bounds apply within each
period. There is no inference of possession, legal future actions or OT rules.
A fourth-down result is **conditional on eligible Run/Pass**, not a comparison
with going, punting or kicking. Unsupported situations do not trigger a model.

## Candidate mapping and source audit

Reviewed the [nflreadr PBP dictionary at commit
`dca0b7f`](https://github.com/nflverse/nflreadr/blob/dca0b7f6c02f18a4d6e644b03f6d8ec8757d2265/data-raw/dictionary_pbp.csv).
Its definitions distinguish `play_type` from `qb_dropback`: sacks can be pass
rows, scrambles can be run rows, and both are dropbacks. `ydstogo` references the
line to gain or goal line. The implementation therefore uses the **already validated
typed** `Play.dropback`, not raw play type, completion, yards gained or description:

- `pass`: eligible `qb_dropback == 1`, labeled **Pass (dropback, including sacks/scrambles)**.
- `run`: remaining eligible `qb_dropback == 0`, labeled **Run (non-dropback)**.

The two candidates exhaust this project's eligible plays. Existing ingestion
excludes kneels, spikes, conversions, special teams, no-play and missing-type rows;
see [eligibility](DATA_CONTRACT.md). Nullified plays are not every attempted call,
and penalties retained as run/pass remain in scope. Do not interpret frequency as
the fraction of all snaps, all fourth-down choices or all calls a coach intended.

This is an observed category audit, **not validation of huddle intent**. The typed
dataset does not retain separate sack/scramble, RPO or aborted-play flags. An
aborted play retained as eligible is classified only by its dropback flag, not
reconstructed intent. No claims about concept recognition or clean designed-call
labels follow. RPO, play action, screen, inside/outside run and finer families stay
deferred under the [richer-source gates](DECISION_INTELLIGENCE.md).

No external implementation, new data or model artifact is copied or installed.
Existing [PBP attribution/CC BY 4.0 records](INGESTION.md#source-and-attribution-review)
and snapshot manifests remain intact. These terms do not substitute for a future
participation/charting/tracking source's own audit.

## Evidence, denominators and states

`population` contains final eligible plays and distinct games. Each candidate has:

- `plays`, `games`: all candidate observations, including missing EPA. Games may
  overlap across candidates; **do not sum candidate game counts** for parent games.
- `frequency = candidate plays / frequency_denominator`, where the denominator is
  the entire final eligible cohort. Values are proportions, not percentages.
- `epa_observations`, `missing_epa`: disjoint counts that sum to candidate plays.
- `epa_per_play`: arithmetic mean over that candidate's observed EPA;
  `success_rate`: fraction of those observations with EPA > 0. Zero is observed
  but not a success. The denominator is **not all candidate plays** when EPA is missing.
- `small_sample` and `small_epa_sample`: candidate plays and observed EPA count,
  respectively, below `minimum_plays`. Neither flag assesses game independence.

The calculations reuse `metrics.summarize_plays`; common population, bounds and
ordered exclusion logic live in `cohort.py`, also used by Scout. No duplicate
ingestion, browser calculation or second outcome formula was added.

| Condition | Frequency / `availability.frequency` | Outcomes / `availability.outcomes` |
| --- | --- | --- |
| Empty parent | null / `empty_cohort` | null / `empty_cohort` |
| Nonempty parent, candidate absent | 0 / `available` | null / `unobserved_candidate` |
| Candidate observed, all EPA missing | observed proportion / `available` | null / `missing_epa` |
| At least one observed candidate EPA | observed proportion / `available` | descriptive values / `available` |

Minimum point-estimate support is one parent play for frequency and one candidate
EPA observation for outcomes, explicitly recorded in `estimation_policy`. This
means mathematically defined, **not reliable**. Even clearing the 30-count warning
does not validate a comparison. Candidate uncertainty/game-support rules are not
implemented in this slice; Scout's five-game resampling gate is not repurposed as
a decision-reliability threshold.

`comparison` always returns `status: insufficient_evidence`,
`reason: candidate_comparison_not_validated`, and `preferred_candidate: null`.
This is a capability/validation abstention even in large samples, not a test of
whether the point estimates happen to differ. There is no automatic winner,
fallback baseline, confidence score, EP/WP impact or model-estimated counterfactual.

## Limits and next slice

Source hash and a deep-copied snapshot manifest (when supplied by the snapshot
loader) preserve provenance. Filtering before a week does not establish that a
later source revision or upstream EPA model was available at that time. Outcomes
are historical offense-relative values; selection bias and unobserved confounding
remain. No causal, out-of-sample, game-rule or coaching validation is claimed.

Next: a separate coherent unit for **matched, same-role, leave-team-out candidate
league baselines** using the exact same down/distance/context/candidate rules and
explicit differences/nulls/coverage. Do not reuse Scout's broader presentation
buckets or unmatched overall values. Candidate-level uncertainty/support and a
justified comparison policy follow; ranking remains withheld. No API/UI/model
until those foundation contracts are tested and independently reconciled.
