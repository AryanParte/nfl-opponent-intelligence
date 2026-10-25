# Sports portfolio roadmap

The original plan is a roughly 16-week direction at 10–15 hours/week, not a promise
of delivery dates or a project-count target. Daily runs complete one coherent
unit, preserve earlier work, and adjust estimates using evidence. The present
implementation priority is Project 1. GitHub is the persistent source of truth:
https://github.com/AryanParte/nfl-opponent-intelligence. Sync the canonical clone at
`/Users/aryanparte/Documents/nfl-opponent-intelligence`, then read the status file
and latest commits before choosing work. Do not recreate the project in new sessions.

## Project 1 — NFL Decision Intelligence (same repository)

Direction updated 2026-10-15: preserve the existing Opponent Intelligence product
as **Scout / Analysis**, then add a narrow **Play Caller / Decision Lab**. Reuse
the validated pipeline, metrics, baselines, uncertainty, API and React UI. No new
repository, duplicated analytics or LLM branding layer. The differentiator is
explainable football evidence, not a play-calling game or a clone of another site.
See [direction, evidence layers and initial source review](docs/DECISION_INTELLIGENCE.md).
Decision Lab's API/UI remain planned. P1.4's bounded local surface is complete;
P1.5's offline contract, matched candidate baselines and exploratory uncertainty
are implemented and independently reconciled on pinned retrospective cohorts.
Its comparison/abstention policy closes the descriptive foundation: explicit
Pass-minus-Run differences, no preferred-call label, opponent conditioning deferred.
P1.6's [nfl4th](docs/NFL4TH_AUDIT.md) and
[fastrmodels EP/WP](docs/FASTRMODELS_AUDIT.md) interface audits are complete with
runtime integration deferred. The [EP-only reference strategy/protocol](docs/EP_REFERENCE_PROTOCOL.md)
is now implemented with synthetic input/capture checks. Next is acquisition and
an isolated R reference capture, not a model endpoint or an action-ranking claim.

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

### P1.4 — Product surface (complete within local scope, 2026-10-16)

- [x] First narrow FastAPI report endpoint (2026-10-08, additional manual run):
      `GET /v1/report` over one operator-configured immutable local snapshot,
      schema v2 and the existing builder, optional dependencies, stable errors,
      bounded queries/resampling and one active builder per application instance.
      196 core and 20 API tests pass on Python 3.11/3.12/3.13; real frozen-report
      replay, ten additional role/context reports and a loopback Uvicorn smoke
      test passed. See [API contract and limits](docs/API.md). No per-request
      paths/downloads, database, frontend or deployment were added.
- [x] First narrow local React/TypeScript report view (2026-10-09): explicit
      team/season/cutoff/role/type controls, returned cohort, denominator-aware
      metrics and splits, warnings, attribution, timestamps and hashes. Loading,
      error, empty/null, retry, timeout and stale-response handling are tested.
      A loopback-only route proxy keeps API/CORS/data selection unchanged.
      51 frontend tests plus Python API-to-fixture replay, type-check/build and
      a real-snapshot browser smoke check passed; see [viewer evidence](docs/WEB.md).
- [x] Opt-in matched league comparison view (2026-10-10): observed same-role
      coverage, pooled baseline counts, signed percentage-point/EPA differences,
      matched buckets, missing/empty states and all baseline warnings. Ten
      synthetic API fixtures, 99 frontend tests and real-snapshot browser replay
      cover the consumed contract; no analytics, source or API changes.
- [x] Optional pre-play field-position controls (2026-10-11): inclusive decimal
      bounds, omitted-end defaults, offense-relative coordinates in either role,
      returned filter identity and separate selected/baseline exclusion accounting.
      Missing column errors, all-missing/empty cohorts, zero versus omission and
      stale edits are covered; 184 frontend tests, 22 API-generated fixtures and
      real-snapshot desktop/mobile browser checks pass. Core/API remain unchanged.
- [x] Optional pre-play score controls (2026-10-12): inclusive signed whole-point
      bounds, unbounded omitted ends, ties versus missing scores and unchanged
      offense-minus-defense signs in either role. Selected/baseline field-then-score
      ledgers reconcile to final metrics; conditional missingness is not counted
      twice. 290 frontend tests, 37 endpoint-generated fixtures and real-snapshot
      desktop/mobile checks pass. No new analytics, API or dependency changes.
- [x] Optional pre-play period/clock controls (2026-10-13): explicit Q1–Q4/OT,
      whole seconds with a required period, omitted-end defaults and zero/missing
      distinctions. Period-only selection can retain missing clocks. Both
      populations' field → score → period → clock ledgers reconcile to final
      metrics; 418 frontend tests, 58 endpoint-generated fixtures and real-snapshot
      desktop/mobile checks pass. Existing analytics/API/dependencies are unchanged.
- [x] Visible exploratory uncertainty/support states (2026-10-14): bounded opt-in
      game-bootstrap controls for selected-only/comparison queries, returned overall
      and matching-bucket intervals, per-metric game support and all withheld/undefined
      states. No browser resampling or endpoint subtraction. 545 frontend tests,
      71 endpoint-generated fixtures and real-snapshot desktop/mobile checks pass.
- [x] Download the current validated JSON report (2026-10-15): retain the decoded
      API text unchanged, including all provenance, contexts, comparison and
      uncertainty. Safe basic-cohort filenames, no new request/recomputation,
      ready-only links and owned object-URL cleanup. 635 frontend tests and seven
      native Chrome downloads pass; six real-snapshot reports replay offline,
      including byte-exact reproduction of the frozen historical Markdown brief.
- [x] Record the storage decision (2026-10-15 manual run): no database for one
      bounded immutable, memory-resident snapshot and portable reports. Revisit
      only with measured access patterns; see the architecture decision above.
- [x] Repeatable synthetic browser integration/CI flow (2026-10-15 manual run):
      actual FastAPI and React, desktop/narrow Chromium, both-role filtered reports,
      native JSON download/offline brief replay, invalid/error/empty/stale states,
      keyboard/scroll checks, outbound-request guards and owned-server cleanup.
      No real raw data, external data acquisition or second analytics implementation.
- [x] Bounded Scout accessibility review (2026-10-16): field-associated validation
      errors and focus recovery, explicit required/input instructions, stronger
      control borders, automated scans of six application states plus 320px reflow,
      keyboard order/disclosures/table scrolling, retained captions/header semantics
      and non-interrupting asynchronous errors. 672 frontend / 14 browser tests pass.
      [Coverage, incomplete scan findings and assistive-technology limits](docs/ACCESSIBILITY.md)
      are explicit; this is not screen-reader testing or WCAG certification.

P1.4 is merged and verified through PR #22; P1.5's contract/baselines/uncertainty
merged as PRs #23–#25, with the real-cohort audit merged as PR #26. Do not prolong
P1.4 with unrelated polish or combine foundation work with decision API/UI/models.
Inspect open PRs/CI/reviews before branching; never duplicate
unmerged work. Assistive-technology/cross-browser evaluation remains a documented
release-readiness gap, not a claim that the bounded review certified accessibility.

### P1.5 — Decision Intelligence foundation (descriptive scope complete, 2026-10-21)

- [x] First small slice (2026-10-17): a precise, offline Run vs Pass request/evidence contract
      with exact down/distance and situational cohort semantics, candidate mapping,
      denominators, sample requirements and null/unavailable/insufficient states.
      Audited dropback/scramble/sack versus non-dropback interpretation; offense-only,
      shared selection/metrics, explicit no-ranking state, no UI or model.
      [Contract and synthetic replay](docs/DECISION_CONTRACT.md); 22 new tests,
      218 core / 24 API / 672 frontend / 14 browser checks pass. Scout v2 unchanged.
- [x] Reuse shared cohort/metric primitives for candidate frequencies, EPA/play,
      success, play/game counts and matching leave-team-out league baselines.
      Baselines completed 2026-10-18: opt-in exact matching, pooled-play weights,
      explicit differences/units, candidate coverage/shared games, separate ledgers
      and null handling; 20 new synthetic tests. No broader-bucket fallback,
      opponent adjustment or preferred-call label. Scout schema v2 is unchanged.
- [x] Candidate-level per-metric game support and exploratory paired whole-game
      uncertainty (2026-10-19): shared resampling/quantiles/withholding, fixed exact
      cohorts, parent-frequency versus candidate-EPA support, null/undefined counts,
      strict bounded opt-in. Sixteen new tests including all 3,125 ordered five-game
      draws; Scout outputs/defense meaning unchanged. Ranking remains withheld.
- [x] Independently reconcile pinned retrospective candidate points, baselines,
      per-metric support and seeded intervals directly from raw rows (2026-10-20):
      eight predeclared situations, all 34,902 eligible identities, 144 interval
      entries and exact receipt replay on Python 3.11–3.13. Repository-only oracle,
      Decimal arithmetic, expanded game rows, separate quantiles and synthetic
      mutation tests; [evidence/replay](docs/DECISION_AUDIT.md). No raw redistribution,
      production changes, coverage/model validation or historical-availability claim.
- [x] Comparison/abstention and opponent-evidence policy (2026-10-21): explicit
      selected-offense Pass-minus-Run descriptive differences with units and
      candidate-specific unavailable reasons; ranking always withheld. No contrast
      interval is invented from marginal/league bounds. Opponent conditioning is
      explicitly deferred with cohort/support/temporal validation gates, not
      silently adjusted. [Policy](docs/DECISION_POLICY.md); 14 new synthetic tests.

This completes the offline **descriptive** foundation, not causal, predictive or
preferred-call validation. No winner label, opponent model or new API/UI is implied.
Inspect this unit's PR/CI before continuing; do not duplicate unmerged work.

### P1.6 — Open-source decision-model evaluation/integration gate

- [x] Extend the initial nfl4th desk review into one version-pinned
      input/output, assumptions, license/terms and historical model/data availability
      audit (2026-10-22): [findings and gate](docs/NFL4TH_AUDIT.md), source/asset
      metadata receipt and seven offline contract-drift checks. Thirteen manual
      inputs mapped; five missing and four nullable in typed Play. Reuse as
      methodological reference; defer runtime use pending context, asset terms,
      verified bytes/lineage, parity and temporal validation. No models acquired
      or executed; metadata digests are not local verification.
- [x] Bounded versioned fastrmodels EP/WP evaluation (2026-10-23):
      [findings and gate](docs/FASTRMODELS_AUDIT.md), separate artifact/consumer
      source pins, fourteen raw-input mappings, 18/11/12 ordered model features,
      terms, serialization and three artifact-metadata observations. Eight offline
      checks guard receipt/typed-contract drift, not model predictions. Reuse
      candidate artifacts/methodology; defer runtime integration pending context,
      acquisition/lineage, parity and temporal validation. No model bytes acquired,
      no R installed and no model inference or probability validation performed.
- [x] EP-only strategy/protocol (2026-10-24): select isolated pinned R first,
      then independent Python inference with the same extracted package EP bytes;
      document alternatives, terms/acquisition/runtime plan and exit criteria.
      [Protocol](docs/EP_REFERENCE_PROTOCOL.md), 25 hand-specified synthetic feature
      cases, 16 rejected states and 15 offline/mutation tests cover input encoding,
      capture identity, batch/single agreement, class order and absolute tolerances.
      No model/runtime acquired or executed; synthetic comparator probabilities
      are not golden predictions. Runtime targets are provisional, not a tested lock.
- [ ] **Next unit:** acquire/verify only the pinned package EP artifact and
      provision/lock the isolated R reference. Capture actual features/probabilities
      for the fixed corpus and reproduce offline, or record a concrete compatibility/
      terms blocker. No Python serving integration, WP, real-data enrichment or API/UI.
- [ ] Independently test golden examples, transformations, possession/time/OT
      boundaries and runtime parity using the predeclared protocol before any EP/WP
      integration. The Python candidate must be independent of the oracle. Version models,
      features, training windows and provenance; do not infer action values from
      state values alone. Unsupported integrations remain explicitly deferred.

### P1.7 — Richer football data audit

- [ ] Extend the existing participation/FTN audit, not a second ingestion stack:
      separate immutable manifests/hashes, attribution/terms and release-time evidence.
- [ ] Validate joins/cardinality against PBP and audit unmatched/unknown/invalid
      observations by team, week and candidate; no imputation of absent charting.
- [ ] Approve only directly defensible play families with adequate samples and
      reproducible semantics/tests. Defer weak proxies and unvalidated concepts.
- [ ] Scope a future Big Data Bowl tracking source/research reference only after
      checking its specific terms, coverage and identity/coordinate semantics.

### P1.8 — Decision API

- [ ] Narrow optional FastAPI endpoint reusing the tested decision layer and an
      explicitly configured immutable snapshot; no request paths or downloads.
- [ ] Return candidates, evidence, denominators, league context, warnings,
      uncertainty, source/model versions and explicit insufficient-evidence states.
- [ ] Bound computation and test request/response/errors/concurrency. No unexplained
      AI score or EP/WP claim without the model-validation gate above. A documented
      defer decision in P1.6/P1.7 must not force models/enrichment into the PBP-only API.

### P1.9 — Play Caller / Decision Lab UI

- [ ] Scout and Play Caller navigation in the existing React app; keep Scout intact.
- [ ] Situation definition, supported-call selection and comparison against
      alternatives, with clear historical versus model evidence labels.
- [ ] Explain frequency/outcomes/league context/support/provenance; honest empty,
      insufficient and abstention states, accessible request/download flows.
- [ ] No browser analytics or causal-optimality/coaching/guaranteed-performance claims.

### P1.10 — Operational evidence and case study (preserved from former P1.5)

- [ ] Docker, repeatable builds, and CI that verifies data and API contracts.
- [ ] Scheduled ingestion with freshness checks, retries, failure reporting, and
      immutable dataset manifests. Do not describe delayed releases as live feeds.
- [ ] Deployment appropriate to measured needs; document costs and limitations.
- [ ] Benchmark a realistic workload and preserve reproducible evidence.
- [ ] Publish architecture, method, three evidence-backed football findings,
      limitations, demo video, and portfolio case study.
- [ ] Request domain feedback through Aryan and incorporate concrete review notes.

### Later decision capabilities (gated, not immediate work)

More specific play families, opponent-adjusted action modeling, historical replay,
fourth-down go/punt/field-goal mode, EP/WP action grading, tracking/spatial/route/
coverage features and richer predictive ranking require validated evidence first.
Challenge/daily-scenario modes are optional later UX, not the product's foundation.
No generative AI for input/explanations/marketing; learned methods require a defined
football target, temporal splits, leakage protection, baseline comparison and
calibration/error analysis where relevant. Keep the four evidence layers separate.

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
