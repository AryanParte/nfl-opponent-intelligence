# Sports portfolio roadmap

The original plan is a roughly 16-week direction at 10–15 hours/week, not a promise
of delivery dates or a project-count target. Daily runs complete one coherent
unit, preserve earlier work, and adjust estimates using evidence. The present
implementation priority is Project 1. GitHub is the persistent source of truth:
https://github.com/AryanParte/nfl-opponent-intelligence. Sync the canonical clone at
`/Users/aryanparte/Documents/nfl-opponent-intelligence`, then read the status file
and latest commits before choosing work. Do not recreate the project in new sessions.

## Project 1 — NFL Opponent Intelligence Platform

### P1.1 — Measurement foundation (complete, 2026-09-28)

- [x] Isolated repository on `codex/opponent-intelligence-foundation`.
- [x] Honest README, development instructions, roadmap, and learning log.
- [x] Local nflverse-shaped CSV loader with schema, duplicate, and value checks.
- [x] Explicit offense/season/type selection and exclusive week boundary.
- [x] Dropback rate, EPA/play, success rate, and down/distance splits with counts.
- [x] Missing-data and exclusion accounting; synthetic fixture and offline tests.
- [x] CI configuration for publication; local checks performed.

### P1.2 — Reproducible real-data ingestion (complete, 2026-09-30)

- [x] Address the loader review finding (2026-09-29): reject unrecognized
      `play_type` values with regression tests, preserve documented categories,
      and separately audit missing types without changing metric denominators.
- [x] Verify the published 2024 nflverse gzip CSV asset and dataset terms using
      primary sources; record exact acquisition evidence and attribution.
- [x] Add an explicit fetch command with bounded timeout/retries and local cache.
      Record URL, retrieval timestamp, source/version identifiers and SHA-256.
      Treat an upstream revision as a new snapshot; do not silently overwrite it.
- [x] Support the actual release format and audit real schemas/missingness before
      relaxing any contract. Keep big/raw data out of Git.
- [x] Test the fetcher offline with controlled responses, corruption, retries,
      atomic publication failures, immutable revisions, and verified cache reuse.
- [x] Run the acquired real-season snapshot through the analytical adapter and
      reconcile exclusions and selected totals;
      record evidence and source limitations without calling it model validation.
- [x] Preserve the zero-network synthetic demo for contributors and CI.

The raw acquisition unit (2026-09-29) and snapshot-to-report integration/audit
(2026-09-30) are complete; see [real-data evidence](docs/REAL_DATA_AUDIT.md).
All 49,492 rows reconcile, with 34,902 eligible plays. Four selected cohorts were
cross-checked directly from source CSV using decimal EPA sums. No eligibility
rules were relaxed. This is one retrospective snapshot's adapter validation, not
external schedule/box-score reconciliation, a scale benchmark, or model validation.

### P1.3 — Useful opponent brief (complete within PBP-only scope, 2026-10-08)

- [x] Add explicit opponent-defense summaries (2026-10-01): offense-relative EPA,
      role-labeled report schema v2, denominator accounting, exclusive week cutoffs,
      reciprocal selection tests, and unchanged default offense measurements.
- [x] Add optional pre-play field-position ranges (2026-10-02): validated
      `yardline_100`, inclusive bounds, both roles, missingness/count reconciliation,
      and unchanged valid unfiltered reports. Pinned-snapshot cross-checks passed.
- [x] Add optional pre-play score ranges (2026-10-03): signed whole points,
      unbounded ends, both roles without sign reversal, ordered field/score
      missingness accounting, unchanged defaults, and pinned-snapshot checks.
- [x] Add optional pre-play period/clock filters (2026-10-04): explicit Q1–Q4/OT,
      inclusive seconds with a required period, zero/missing distinction, ordered
      four-stage accounting for both roles, and unchanged valid defaults.
- [x] Add optional matched league baselines (2026-10-05): exclude the selected
      team in the same role, pool available plays under identical filters, match
      down/distance buckets, and expose coverage, denominators, and null differences.
- [x] Add opt-in exploratory game-level uncertainty (2026-10-06): paired whole-game
      resampling, seeded percentile bounds, per-metric support/undefined counts,
      withheld low-support/degenerate intervals, and explicit cross-game limitations.
- [x] Produce a readable static historical opponent brief (2026-10-07): offline
      JSON-to-Markdown rendering, traceable role/cohort/source and denominators,
      matching baselines, every uncertainty state, and replayable synthetic and
      retrospective examples. This describes a cohort, not a two-team projection.
- [x] Audit personnel/motion availability and licensing (2026-10-08): replayable
      raw/eligible field inventory, primary-source definitions and terms, explicit
      absence/missing/zero distinctions, and a feasible-versus-deferred decision.
      No enrichment, motion/personnel metrics, or paid data acquisition is claimed.

The [scope decision](docs/PERSONNEL_MOTION.md) closes P1.3's final acceptance item.
The pinned PBP lacks these fields; supplementary participation/charting is feasible
in principle but requires separate manifests, terms, join/coverage validation and
release-time evidence. The useful historical brief stays PBP-only. Shotgun,
no-huddle, descriptions and play locations must not stand in for personnel/motion.
At P1.3 completion, 195 tests passed locally on Python 3.11/3.12/3.13;
see [current status](docs/STATUS.md) for subsequent verification.
Method calibration, cross-game dependence and historical information availability
remain unverified. PR #12 was observed merged at `9f9a647`; its final feature-head
CI passed. Inspect current PR/CI and reviews before selecting new work.

### P1.4 — Product surface (in progress)

- [x] First narrow FastAPI report endpoint (2026-10-08, additional manual run):
      `GET /v1/report` over one operator-configured immutable local snapshot,
      schema v2 and the existing builder, optional dependencies, stable errors,
      bounded queries/resampling and one active builder per application instance.
      196 core and 20 API tests pass on Python 3.11/3.12/3.13; real frozen-report
      replay, ten additional role/context reports and a loopback Uvicorn smoke
      test passed. See [API contract and limits](docs/API.md). No per-request
      paths/downloads, database, frontend or deployment were added.
- [ ] React/TypeScript interface with situational comparison, source freshness,
      downloadable reports, and visible uncertainty/missing-data states.
- [ ] Choose DuckDB/PostgreSQL only when actual access patterns justify storage;
      record the decision. Keep a small modular service before adding components.
- [ ] Accessible empty/error/loading states and an end-to-end demo.

Next coherent unit: the first narrow React/TypeScript local report view consuming
this existing API: team/season/cutoff/role controls, source provenance, counts/rates
and explicit loading/error/empty/null states, with contract tests. Keep optional
comparison/uncertainty states honest; do not rebuild analytics or add storage to
support a single configured snapshot. Plan any local browser-to-API connection
explicitly; there is no CORS or deployment policy yet. Inspect this branch's PR/CI
before starting it. No frontend work was performed in the API unit.

### P1.5 — Operational evidence and case study

- [ ] Docker, repeatable builds, and CI that verifies data and API contracts.
- [ ] Scheduled ingestion with freshness checks, retries, failure reporting, and
      immutable dataset manifests. Do not describe delayed releases as live feeds.
- [ ] Deployment appropriate to measured needs; document costs and limitations.
- [ ] Benchmark a realistic workload and preserve reproducible evidence.
- [ ] Publish architecture, method, three evidence-backed football findings,
      limitations, demo video, and portfolio case study.
- [ ] Request domain feedback through Aryan and incorporate concrete review notes.

## GitHub and portfolio presentation (alongside Project 1)

- [x] Professional project README, honest current scope, and reproducible demo.
- [x] Create the permanent GitHub repository and preserve the initial snapshot on
      main and `codex/opponent-intelligence-foundation`; clone the same history to
      the stable local path and verify GitHub attributes it to AryanParte.
- [x] Update the 8 AM Eastern automation to sync the stable clone and push verified
      work, with explicit recovery, identity, and continuation instructions.
- [x] Publish the migration documentation as
      [PR #1](https://github.com/AryanParte/nfl-opponent-intelligence/pull/1)
      against the preserved main baseline. Observed merged on 2026-09-29; daily
      work continues from updated `origin/main`, without automatic merges.
- [ ] Review descriptions, topics, demo evidence, and README gaps in Aryan's
      existing two strongest engineering projects; propose focused improvements.
- [ ] Prepare a profile README and a short engineering-focused biography using
      only verified experience. Pin completed strong work as it becomes available.
- [ ] Build the portfolio skeleton, then add real project screenshots and results.
      Do not let site polish displace the first working sports product.
- [ ] Assemble a resume, short demo, and review packet for Akhi after substantive
      work exists. No contacting others without Aryan's instruction.

## Later projects (deferred)

1. NFL tracking study: evaluate catch-window/coverage behavior on licensed Big
   Data Bowl data, establish simple baselines, split by game/time, quantify error,
   and explain failure cases. Validate feasible inputs before promising a metric.
2. NBA lineup/rotation study: begin with reliable possession/lineup reconstruction
   and descriptive uncertainty. Adjusted player effects require regularization and
   validation; lineup association alone cannot justify causal rotation advice.
3. Short Panthers fourth-down and NBA matchup case studies, then a coherent public
   portfolio and interview practice. Keep factual claims reproducible.

## Definition of done for each daily unit

Observable working behavior, meaningful passing checks, a critical complete-diff
review with fixes, updated continuation notes, a learning-log entry, and a clear
commit on the feature branch. A network or publication blocker does not justify
restarting local work or pretending a remote action succeeded.
