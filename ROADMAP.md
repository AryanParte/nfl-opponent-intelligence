# Sports portfolio roadmap

The original plan is a roughly 16-week direction at 10–15 hours/week, not a promise
of delivery dates or a project-count target. Daily runs complete one coherent
unit, preserve earlier work, and adjust estimates using evidence. The present
implementation priority is Project 1. Local code and documents are authoritative;
read the status file and latest commits before choosing work.

## Project 1 — NFL Opponent Intelligence Platform

### P1.1 — Measurement foundation (complete, 2026-09-28)

- [x] Isolated repository on `codex/opponent-intelligence-foundation`.
- [x] Honest README, development instructions, roadmap, and learning log.
- [x] Local nflverse-shaped CSV loader with schema, duplicate, and value checks.
- [x] Explicit offense/season/type selection and exclusive week boundary.
- [x] Dropback rate, EPA/play, success rate, and down/distance splits with counts.
- [x] Missing-data and exclusion accounting; synthetic fixture and offline tests.
- [x] CI configuration for publication; local checks performed.

### P1.2 — Reproducible real-data ingestion (NEXT)

- [ ] Verify a completed-season nflverse CSV release and its dataset terms using
      primary sources; start with 2024 to keep the example fixed.
- [ ] Add an explicit fetch command with bounded timeout/retries and local cache.
      Record URL, retrieval timestamp, source/version identifiers and SHA-256.
      Treat an upstream revision as a new snapshot; do not silently overwrite it.
- [ ] Support the actual release format and audit real schemas/missingness before
      relaxing any contract. Keep big/raw data out of Git.
- [ ] Test the fetcher offline with controlled responses, corruption, and retries.
- [ ] Run one real-season ingestion and reconcile exclusions and selected totals;
      record evidence and source limitations without calling it model validation.
- [ ] Preserve the zero-network synthetic demo for contributors and CI.

This is the next coherent unit. Do not begin UI or predictive work before it.

### P1.3 — Useful opponent brief

- [ ] Add opponent-defense summaries and field position/score/time filters with
      consistent pre-play context and auditable cohort counts.
- [ ] Compare an offense's tendencies with league baselines in matching contexts.
- [ ] Add game-level uncertainty estimates and sample warnings; explain dependence
      among plays and the limits of small numbers of games.
- [ ] Produce a readable static historical matchup brief with traceable findings.
- [ ] Validate personnel/motion data availability and licensing separately. The
      initial play-by-play contract does not guarantee these fields exist.

### P1.4 — Product surface

- [ ] FastAPI endpoints with a stable report schema and invalid-input behavior.
- [ ] React/TypeScript interface with situational comparison, source freshness,
      downloadable reports, and visible uncertainty/missing-data states.
- [ ] Choose DuckDB/PostgreSQL only when actual access patterns justify storage;
      record the decision. Keep a small modular service before adding components.
- [ ] Accessible empty/error/loading states and an end-to-end demo.

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
- [ ] Create/connect the intended GitHub repository, then push a feature branch
      and prepare a PR where a base branch exists. Do not merge automatically.
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
