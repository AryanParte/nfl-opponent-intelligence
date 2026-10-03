# Learning log

## 2026-09-28 — First working measurement pipeline

**Built:** a local CSV loader, typed play records, an offense-summary CLI, source
fingerprints, explicit cohort selection, down/distance splits, and an offline
synthetic test suite. Added professional project documentation and a staged
roadmap. The workspace was empty; no prior project commits existed.

**Why it matters:** every later dashboard needs reliable definitions and data
handling. An attractive chart cannot repair a wrong denominator or a report that
includes the game it is supposed to help prepare for.

**Review:** `src/opponent_intelligence/pbp.py` for input validation;
`src/opponent_intelligence/report.py` for cohort selection and metric denominators;
`tests/test_pipeline.py` for independent expected values; `docs/METRICS.md` for
interpretation and limitations. Start with the README demo.

**Sports concepts:** sacks and scrambles count as dropbacks; kneels, spikes,
conversions and no-play rows are excluded; EPA measures value from the offense's
perspective; success here means strictly positive EPA.

**Software/statistical concepts:** data contracts, composite identities, duplicate
rejection, immutable typed records, hashing exact input bytes, explicit nulls,
separate metric denominators, regression tests, and temporal selection. A minimum
sample warning does not constitute statistical significance.

**What to learn:** manually reconcile six synthetic plays and five observed EPA
values. Explain why the report has a 50% dropback rate, 0.04 EPA/play, and 60%
success rate. Distinguish a tested descriptive calculation from a validated
prediction or a production deployment.

**Three review questions:**

1. Why does a scramble count as a dropback even when `play_type` is `run`?
2. Which denominators change when EPA is missing, and which must stay unchanged?
3. Why does excluding the target week still not prove a historical forecast is
   free of leakage from later source revisions or model training?

**Verification:** 18 offline tests passed on Python 3.11.4. The command-line demo
matched independently calculated fixture totals and repeated byte-for-byte. The
staged diff passed Git's whitespace check. No real-season or remote CI validation
has run yet.

**Review findings and remaining issues:** all source, tests, configuration and
documentation were inspected. Unknown `play_type` values currently enter the
generic exclusion bucket, which could hide an upstream schema change; tighten that
with a regression test after migration. Source labels are caller supplied, the
loader is in-memory, and actual release compatibility remains unverified.

**Next task:** at Aryan's request, first preserve and publish this work to the
permanent GitHub repository and stable clone, update daily sync/push instructions,
then finish the noted validation fix before P1.2 real-data ingestion.

## 2026-09-28 — Persistent repository migration

**Built:** the public GitHub repository, a stable clone, verified repository-local
commit identity, and durable daily sync/push/recovery instructions. Updated the
existing 8 AM Eastern task instead of creating a duplicate schedule. Preserved all
19 project files in foundation commit `ba72f50` and seeded the review baseline with
that same commit; no previous commits existed to rewrite or discard.

**Why it matters:** project progress now survives a new Codex workspace. The
remote history and roadmap carry the work, and the stable clone is recoverable.

**Review:** `AGENTS.md`, `docs/DAILY_WORKFLOW.md`, `docs/STATUS.md`, and the roadmap.
The foundation code and tests were preserved unchanged through the migration.

**Sports concepts:** no new analytical claim. The existing EPA, dropback, and
week-cutoff definitions remain unchanged and retain their synthetic-data limits.

**Software concepts:** local versus remote state, commit identity versus login,
upstream tracking, fast-forward synchronization, immutable commit hashes, and PR
review. The GitHub no-reply address links work to the verified account without
publishing a personal email address.

**What to learn:** trace one commit from the original project to GitHub and the
fresh stable clone. A successful push must be checked against the actual remote
SHA; a local commit alone is not durable remote publication.

**Three review questions:**

1. How would you recover both merged and unmerged work if the local clone vanished?
2. Why can the GitHub login succeed while a commit is still attributed incorrectly?
3. What should a daily run do when local and remote branch histories diverge?

**Verification/self-review:** original and cloned files matched, all 18 tests
passed in the stable clone, local/remote foundation SHAs matched, and GitHub
confirmed author and committer attribution to AryanParte. The working branch is
`codex/opponent-intelligence-foundation`, published in
[PR #1](https://github.com/AryanParte/nfl-opponent-intelligence/pull/1); no PR has
been merged. Reviewed the complete migration diff and sync instructions for
user-change preservation, stale-backup risks, and missing-clone recovery. The
filesystem grant separately required access to `.git` metadata. The original
checkout was moved intact into the dated task's `work/migration-backup` directory;
the former outputs directory now points to the canonical repository.

**Remaining/next task:** migration is complete. Address the recorded unknown-play-type
validation finding before P1.2 real-season ingestion. GitHub recognizes the CI
workflow as active, but its Actions API returned zero workflow runs at handoff;
remote CI remains unverified and must be checked separately from local test success.

## 2026-09-29 — Explicit play-type validation

**Built:** a closed vocabulary for nflverse play types, line-specific errors for
unknown labels, and a separate `missing_play_type` exclusion count. Added seven
regression-test methods and documented exclusion order and missingness. Synced
the permanent clone, observed PR #1 merged, and started `codex/validate-play-types`
from updated `origin/main` (`fac284b`). No project or history was recreated.

**Why it matters:** a misspelled pass label previously disappeared as an exclusion,
potentially changing play-call denominators without an error. The loader now
distinguishes an invalid category from a documented exclusion or missing value.

**Review:** `src/opponent_intelligence/pbp.py` (validation before filtering),
`tests/test_pipeline.py` (independent category expectations and failure cases),
`docs/DATA_CONTRACT.md` (accepted labels and precedence), and `docs/METRICS.md`.

**Sports concepts:** sacks remain pass plays and scrambles remain run-shaped
dropbacks. Documented special-teams, kneel/spike, and no-play types stay excluded.
The upstream dictionary permits missing types on end-of-play rows, but this
adapter does not infer why an individual value is missing. No real NFL observations
or new performance claims were introduced.

**Software/statistical concepts:** schema drift, explicit category validation,
auditable missingness, identity checks before filtering, red/green regression
tests, and all-or-nothing CLI output. Missing play type excludes a row from the
eligible cohort; missing EPA on an eligible play still preserves its play-call
denominator. These are different data-quality situations.

**What to learn:** trace how a bad label could bias a rate if silently removed.
Explain why missing-type rows are counted without imputing a category, and why
the metric totals remain unchanged for valid input. Find the exact error line in
a two-row synthetic input whose last row contains a typo.

**Three review questions:**

1. How could silently excluding a misspelled pass change the reported dropback rate?
2. Why do missing play type and missing EPA affect different denominators?
3. What exit status and stdout should the CLI produce when a valid row is followed
   by an invalid play type, and which test verifies that behavior?

**Verification/self-review:** all 18 baseline tests passed before changes. The new
targeted tests then failed against the original loader (21 failing assertions
across subtests and the CLI), demonstrating the regression. All 25 tests now pass
on Python 3.11.9, 3.12.7, and 3.13.2. Reviewed category coverage against the nflreadr
dictionary and nflfastR field construction on 2026-09-29. The self-review added a
mixed-row reconciliation test to verify both the exclusion totals and unchanged
metric denominators. Identity validation, documented missing types, strict case
handling, and no partial CLI output were checked explicitly.

**Publication/CI:** implementation commit `19b5a09` was pushed to the existing
GitHub repository with matching local/remote SHAs and confirmed AryanParte author
and committer attribution. [PR #2](https://github.com/AryanParte/nfl-opponent-intelligence/pull/2)
is open, not merged. No automatic CI appeared after the push/PR, despite enabled
repository settings. Manually dispatching the existing Verify workflow succeeded:
[run 36566444248](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/36566444248)
passed the test suite and synthetic demo on Python 3.11/3.12/3.13. No repository
settings or workflow code were changed to obtain this result.

**Remaining/next task:** verify the completed 2024 nflverse release and dataset
terms, then build the bounded, cached fetcher and immutable source manifest with
offline tests (P1.2). Real-release compatibility, temporal source availability,
and downstream predictive validity remain unverified. Recheck automatic CI
triggering on future pushes; a successful manual run does not explain its absence.

## 2026-09-29 — Additional manual run: immutable raw snapshots

**Built:** a separate 2024 raw-data fetch command with bounded socket timeouts,
retries, byte limits, published-digest checks, gzip validation, immutable snapshot
directories, and provenance manifests. Default cache reuse is verified and offline;
explicit refresh preserves earlier versions. Started `codex/immutable-pbp-snapshots`
from merged PR #2's updated main (`635ee9a`). The 8 AM automation was not changed.

**Why it matters:** a season name or download URL does not identify stable data.
Hashes, source IDs, and retrieval times make an analysis traceable to exact bytes
and keep upstream revisions from silently replacing yesterday's evidence.

**Review:** `src/opponent_intelligence/snapshots.py` (download, verification, and
publication), `src/opponent_intelligence/fetch.py` (explicit network CLI),
`tests/test_snapshots.py` (synthetic failure cases), `docs/INGESTION.md` (source
terms and limits), and its linked real acquisition manifest.

**Sports concepts:** raw data acquisition is not validation of play classifications,
season coverage, EPA, or tendency denominators. The 2024 artifact was updated in
2026; it cannot establish what was available before a particular 2024 game.

**Software/statistical concepts:** content-addressed storage, source provenance,
compressed versus decoded hashes, bounded retries, atomic publication, cache
integrity, repeatable tests, and the distinction between event time and retrieval
time. Data-license review is separate from client-library licensing.

**What to learn:** follow one artifact from release metadata through a verified
download into an immutable manifest. Explain the only mutable pointer, why stale
cache reuse is deliberate, and what checks are still needed before reporting real
football results. A hash detects a changed artifact but does not archive its bytes.

**Three review questions:**

1. Why record both compressed and decoded SHA-256 hashes, plus the upstream asset ID?
2. Which files may change during refresh, and what happens if download or pointer
   publication fails after an older valid snapshot already exists?
3. Why does downloading a completed 2024 season in 2026 not justify a leakage-free
   historical forecast or prove the season's analytical denominators are correct?

**Verification/self-review:** all 44 tests pass on Python 3.11/3.12/3.13, including
19 new acquisition tests with blocked network. Acquired the real 19,362,351-byte
gzip artifact and matched its published digest; its 99,483,794 decoded bytes also
match the separately published CSV digest. Offline reuse passed without modifying
the manifest. The committed small manifest matches the local copy; raw data is
ignored. Self-review tightened type/boundary checks, verified the archive hash
before decompression, blocked network inside CLI tests, and added tests for
concurrent identical publication and filesystem publication failure. The complete
diff review also found malformed numeric headers and deeply invalid JSON could
escape clean error handling; fixed those paths and added regression cases. No
existing measurement definitions or fixtures were changed.

**Publication:** implementation commit `f1cb37d` is pushed on
`codex/immutable-pbp-snapshots`, with matching local/remote SHAs and GitHub author
and committer attribution to `AryanParte`.
[PR #3](https://github.com/AryanParte/nfl-opponent-intelligence/pull/3) is open for
review, not merged. The existing workflow needed manual dispatch because no
automatic run appeared; [implementation CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/36651274225)
passed the suite and synthetic demo on all three Python versions. Final-head
verification after this documentation update is recorded in the PR description.

**Remaining/next task:** wire this exact snapshot into the analytical loader with
provenance; audit full-season schemas, missingness, identities and exclusions;
reconcile cohort totals before publishing real findings. CSV semantics, historical
information availability, durable external data backup, and automatic CI triggering
remain separate open issues. Keep the PR unmerged for Aryan's review.

## 2026-09-30 — Verified snapshots reach analytical reports

**Built:** offline `--snapshot` reporting with the acquisition manifest attached,
bounded gzip decoding, actual-parsed-byte hash checks, and an audit command for
coverage, required-field missingness, and raw/adapter identity reconciliation.
Started `codex/audit-real-pbp-snapshot` from merged PR #3's `78623c6`. No automation
changes or new project checkout were made.

**Why it matters:** a report can now identify its exact raw inputs, and every
eligible/excluded source row is accounted for before real findings are used.

**Review:** `ingestion.py` (verified bytes), `audit.py` (independent selection),
`report.py` (provenance), `tests/test_ingestion.py`, and `docs/REAL_DATA_AUDIT.md`.

**Sports concepts:** 2024 REG and POST remain separate; sacks/scrambles are
dropbacks; type-labeled kneels/spikes are already excluded. Source missingness
is not the same as missingness among eligible plays. No eligibility rule changed.

**Software/statistical concepts:** content identity versus file encoding, explicit
version selection, check/read races, set equality versus matching counts, decimal
cross-checks, and retrospective data versus historical information availability.

**What to learn:** trace a report's decoded hash back to its compressed snapshot
and receipt. Reconcile `49,492 = 34,902 + 12,996 + 1,446 + 148`. Use the independent
CSV recipe to reproduce CAR's pre-week-3 numerators and denominators.

**Three review questions:**

1. Why do gzip and decoded CSV have different hashes, and which does the report use?
2. How can 570 raw rows lack EPA while all 34,902 eligible plays have observed EPA?
3. Why do matching eligible counts and an exclusive week cutoff still fall short
   of proving correct identities or leakage-free forecasting?

**Verification/self-review:** 60 tests pass on Python 3.11/3.12/3.13 (16 new).
The full artifact audit passes; four cohorts match independent CSV/Decimal
calculations within `1e-12`. Tests exercise corruption, mutation between reads,
wrong seasons, conflicting metadata, same-count/wrong-identity disagreement, and
no partial CLI output. Review preserved identity-first validation precedence and
the original synthetic contract. Raw data was not edited or committed; the small
derived audit records its source and limits.

**Publication:** implementation `24f61c6` is pushed with matching local/remote SHAs
and confirmed AryanParte author/committer attribution.
[PR #4](https://github.com/AryanParte/nfl-opponent-intelligence/pull/4) is open and
unmerged. [Implementation CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/36786252031)
passed the suite and synthetic demo on all three Python versions. Manual dispatch
was needed because no automatic run appeared. The PR description records final-head
verification after this documentation update.

**Remaining/next task:** P1.2 is complete for this snapshot. Add P1.3's defense-side
cohort with explicit offense-perspective EPA and time-bound tests. Independent
schedule/gamebook matching, upstream annotation accuracy, historical availability,
external backup, automatic CI triggering, and large-scale streaming remain open
limits. Keep the new PR unmerged for Aryan's review.

## 2026-10-01 — Explicit defense-side opponent reports

**Built:** `--side defense` and the matching Python API select plays by defending
team while preserving offense-relative EPA and all metric formulas. Report schema
v2 identifies team, role, and interpretation; the default remains offense, but JSON
consumers must migrate from `cohort.offense`. Started `codex/defense-cohort-reports`
from merged PR #4's `8ed98e6`; no open review feedback remained. The stable clone,
existing history, raw snapshot, and 8 AM automation were preserved.

**Why it matters:** an analyst can now inspect what offenses did against a chosen
defense, with traceable denominators and no misleading EPA sign reversal. This is
the first P1.3 unit, not a completed matchup brief or opponent-adjusted evaluation.

**Review:** `src/opponent_intelligence/report.py` (selection and schema),
`src/opponent_intelligence/__main__.py` (explicit CLI choice),
`tests/test_defense_reports.py` (hand-calculated and reciprocal expectations),
`tests/test_ingestion.py` (snapshot provenance), and `docs/METRICS.md` (migration).

**Sports concepts:** possession-relative EPA; offensive success allowed versus
defensive stops; sacks/scrambles in dropbacks; opposing offense down/distance;
opponent mix; separate regular/postseason cohorts and exclusive week boundaries.

**Software/statistical concepts:** selection versus measurement, versioned JSON
contracts, reciprocal/mirrored tests, additive counts versus non-additive rates,
and missing-EPA denominators. Plays within games remain dependent; these summaries
do not provide uncertainty estimates, causal attribution, or predictive validation.

**What to learn:** trace `--side` from CLI to the team predicate, explain why
`_metrics` is unchanged, and reproduce the synthetic ATL defense's 0.2 / 4 EPA
and 3 / 4 success calculations. Inspect schema metadata before labeling output.

**Three review questions:**

1. Why does selecting a defense change the team predicate but not the EPA sign or
   the success condition?
2. How do zero and missing EPA affect success, EPA, and dropback denominators, and
   why is `1 - success_rate` not a drive-level defensive stop rate?
3. How must a v1 JSON consumer migrate, and why do matching offense/defense play
   totals not justify adding team rates or claiming opponent-adjusted quality?

**Verification/self-review:** 60 baseline tests passed. The 14 new defense tests
failed before implementation; all 75 tests (including one new snapshot integration
test) now pass on Python 3.11/3.12/3.13. Both README demos pass. Coverage includes
multiple opponents, empty cohorts, season/week cutoffs, source exclusions, invalid
side/no partial JSON, default offense compatibility, and positive/negative/zero/
missing EPA. Review corrected reduced typed fixtures' input-row accounting and
made report-v2 versus manifest-v1 compatibility explicit. No source fields or
eligibility rules were changed; no duplicated metric implementation was added.

With network blocked, 256 reports from the existing verified real snapshot matched
independent team counters over typed eligible plays. Each side's partitions total
0, 3,811, 33,335, and 1,567 plays for REG before weeks 1/3/19 and POST before week
23 respectively; manifests remain intact. This is a role-selection integration
check, not a new raw CSV audit, external gamebook comparison, or forecast test.

**Publication:** implementation `208fb90` is pushed with matching local/remote SHAs
and confirmed AryanParte author/committer attribution.
[PR #5](https://github.com/AryanParte/nfl-opponent-intelligence/pull/5) is open,
unmerged, and attached to the task. [Implementation CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/36877565779)
passed the offline regression suite and synthetic demo on all three Python versions.
Manual dispatch was needed because no automatic run appeared. The PR description
records final-head verification after this publication-record update. Workflow
configuration, repository settings, and the existing daily automation are unchanged.

**Remaining/next task:** add an optional pre-play field-position filter using a
reviewed `yardline_100` contract, explicit boundaries/missingness, and tests for
both roles without changing unfiltered results. Score/time filters, matched league
baselines, game-level uncertainty, and a readable brief remain unfinished. Keep
the feature PR unmerged for Aryan's review; prior source/CI limitations still apply.

## 2026-10-02 — Pre-play field-position filters

**Built:** optional `yardline_100` parsing and inclusive `--yardline-min` /
`--yardline-max` filters for both roles. Reports expose effective bounds and the
base/missing/outside/selected play counts. Audits distinguish raw and eligible
optional-field missingness. Started `codex/field-position-filters` from merged
PR #5's `de354ac`, with no outstanding PRs or reviews. No automation changes.

**Why it matters:** analysts can compare defined regions of the field without
confusing offense/defense coordinates, treating unknown positions as zero, or
hiding the plays removed from a cohort. Existing valid unfiltered output is intact.

**Review:** `src/opponent_intelligence/pbp.py` (optional-field contract),
`report.py` (range selection and accounting), `audit.py` (missingness populations),
`__main__.py` (flags), `tests/test_field_position.py`, the two new snapshot tests
in `tests/test_ingestion.py`, and the field-position section in `docs/REAL_DATA_AUDIT.md`.

**Sports concepts:** pre-play position versus post-play outcomes; 20 means 20 yards
from the offense's opponent's goal line for either role; selected plays are not
drive-level red-zone opportunities. EPA and success retain the offense perspective.

**Software/statistical concepts:** optional headers versus missing observations,
finite inclusive bounds, backward-compatible output extensions, independent raw
selection/Decimal checks, and conditional missing-data denominators. A 0..100
filter excludes unknown positions; no filter retains them. Samples still mix
score/time/opponents and contain within-game dependence.

**What to learn:** follow a source row through eligibility, team/time selection,
range selection, then measurement. Reconcile the synthetic six-play base as
`6 = 1 missing position + 2 outside range + 3 selected`, then explain why only
two selected plays supply EPA while all three supply the dropback denominator.

**Three review questions:**

1. Why must a defense's 0..20 filter use the offense's coordinates without flipping
   them, and why should it avoid end-of-play positions?
2. How do an absent column, a missing position, zero yards, and missing EPA differ
   in errors, selection, and metric denominators?
3. How do the nested field-filter counts reconcile with global exclusions without
   double-counting, and why do the raw 3,542 missing positions not reduce this
   snapshot's 34,902 eligible plays?

**Verification/self-review:** the 75-test baseline passed. New range/validation
cases failed against the prior implementation; all 93 offline tests now pass on
Python 3.11/3.12/3.13. Sixteen field tests and two snapshot tests cover absent and
all-missing fields, fractional/equal/zero/end bounds, malformed values even outside
the requested cohort, exclusions, reciprocal roles, time boundaries, provenance,
and no partial CLI output. Review removed silent extra-key dropping from the test
CSV writer and strengthened scoped-missingness and filtered sample-warning
assertions; optional-field availability survives empty input and snapshot loading.
Existing fixture bytes, eligibility rules, and formulas remain
unchanged. Schema additions and the stricter newly recognized column are documented.

The read-only spreadsheet audit kept raw bytes untouched and separated source-wide
from eligible missingness: 3,542 versus zero; eligible positions span 1..99. All
34,902 position/identity pairs reconcile. With network blocked, 576 filtered reports
match independent raw selection and Decimal calculations (EPA tolerance `1e-12`),
and 192 unfiltered reports exactly match the merged predecessor. The evidence and
replay recipe are committed in the existing audit document, not presented as model
validation, external gamebook matching, or opponent-adjusted performance.

**Publication:** implementation `b71789c` is pushed with matching local/remote SHAs
and confirmed AryanParte author/committer attribution.
[PR #6](https://github.com/AryanParte/nfl-opponent-intelligence/pull/6) is open,
unmerged, and attached to the task. [Implementation CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37020736183)
passed the offline regression suite and synthetic demo on Python 3.11/3.12/3.13.
Manual dispatch was needed because no automatic run appeared. The PR description
records final-head verification after this publication-record update. Workflow
configuration, repository settings, and the existing daily automation are unchanged.

**Remaining/next task:** optional pre-play `score_differential` filtering, keeping
the offense-relative sign for both roles and testing combined field/score ranges,
missingness, and unchanged defaults. Time filtering, matched baselines, game-level
uncertainty, and the actual brief remain unfinished. Existing snapshot availability,
automatic CI triggering, and scale limits remain; leave this PR unmerged for review.

## 2026-10-03 — Pre-play score filters and combined cohort accounting

**Built:** optional whole-point `score_differential` parsing and inclusive
`--score-min` / `--score-max` filters with unbounded omitted ends. Both roles keep
the offense-relative sign. Combined filters run field position then score, expose
the order, and count each removed play once. Started `codex/pre-play-score-filters`
from merged PR #6's `5d12321`; preceding branch/upstream matched and no outstanding
PRs or review feedback remained. The existing history and canonical clone are
preserved; the automation is unchanged.

**Why it matters:** analysts can separate trailing/tied/leading offensive plays
without selecting on post-play outcomes, confusing defense perspective, or hiding
missing-context removals. This is another P1.3 component, not a completed brief.

**Review:** `src/opponent_intelligence/pbp.py` (exact whole-point parsing),
`report.py` (validation, selection order, counts), `__main__.py` (CLI flags),
`tests/test_score_filters.py`, the new snapshot test in `tests/test_ingestion.py`,
and `docs/METRICS.md` / the score section in `docs/REAL_DATA_AUDIT.md`.

**Sports concepts:** score at the start versus end of a play; possession-relative
leads/deficits for either role; ties versus unknown scores; no inferred possession
counts or neutral-game labels; unaltered offensive EPA/success interpretation.

**Software/statistical concepts:** exact parsing rather than float rounding,
nullable unbounded ends, optional header availability, backward-compatible JSON
extensions, conditional missingness, non-overlapping removal counts, independent
raw/Decimal checks, and source provenance. Filtering is not opponent adjustment
and does not make plays within a game independent.

**What to learn:** trace the synthetic nine-play base through `9 = 2 missing
position + 1 outside position + 6`, then `6 = 1 missing score + 1 outside score + 4`.
Explain why the four retained plays have only three EPA observations and why a
play missing both fields is removed only at the first stage.

**Three review questions:**

1. For a defense report, what does `score_max=-1` select, and why would using
   `score_differential_post` change the question being measured?
2. How do an omitted bound, a bound of zero, missing score, and missing EPA differ
   in selection and denominator handling?
3. Why are score-filter missingness counts conditional on any field filter, and
   how do both stage counts reconcile with global exclusions without double-counting?

**Verification/self-review:** the 93-test baseline passed; new feature cases failed
against the predecessor. All 112 tests now pass on Python 3.11/3.12/3.13 (18 score
tests plus one snapshot test). Coverage includes fractions that float would round,
large exact integers, negative/equal/open ends, absent/all-missing columns,
overlapping missing contexts, all-missing EPA, reciprocal roles, exclusive cutoffs,
empty cohorts, unchanged no-score output, provenance, and CLI errors without JSON.
Review strengthened all-missing-EPA checks, false-versus-zero validation, and
CLI-order invariance; availability is validated even if another filter empties
the cohort. The stricter newly recognized source
column and score-only metadata are documented. Metric formulas, eligibility rules,
and original fixture bytes are unchanged.

The read-only CSV audit separated 2,713 raw missing scores from zero among 34,902
eligible plays. Every eligible score agrees with its raw identity and the source's
pre-play point difference; 1,456 eligible pre/post values differ. Independent raw
selection and Decimal arithmetic matched 2,304 filtered reports; 576 no-score
reports exactly matched merged PR #6. Replay evidence is in the audit document.
These checks validate selection/internal source consistency, not gamebooks, model
training, forecast quality, or historical availability.

**Publication:** local verification is complete; push, PR, attribution, remote-SHA,
and CI receipts will be recorded after publication. No workflow/repository settings
or daily automation changes are part of this unit.

**Remaining/next task:** optional pre-play quarter/clock filtering, beginning with
source semantics and regulation/overtime boundaries. Preserve both roles, existing
filters/defaults, exclusive week cutoffs, and explicit ordered missingness. Matched
league baselines, game-level uncertainty, and the actual brief follow. Keep this
unit's PR unmerged for Aryan's review; existing source/CI/scale limitations remain.
