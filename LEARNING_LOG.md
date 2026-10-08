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

**Publication:** implementation `16f637f` is pushed with matching local/remote SHAs
and confirmed AryanParte author/committer attribution.
[PR #7](https://github.com/AryanParte/nfl-opponent-intelligence/pull/7) is open,
unmerged, and attached to the task. [Implementation CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37134408317)
passed the offline regression suite and synthetic demo on Python 3.11/3.12/3.13.
Manual dispatch was needed because no automatic run appeared. The PR description
records final-head verification after this publication-record update. No workflow
code, repository settings, or daily automation changed.

**Remaining/next task:** optional pre-play quarter/clock filtering, beginning with
source semantics and regulation/overtime boundaries. Preserve both roles, existing
filters/defaults, exclusive week cutoffs, and explicit ordered missingness. Matched
league baselines, game-level uncertainty, and the actual brief follow. Keep this
unit's PR unmerged for Aryan's review; existing source/CI/scale limitations remain.

## 2026-10-04 — Explicit pre-play periods and clock ranges

**Built:** optional `qtr` / `quarter_seconds_remaining` parsing, `--period`
Q1–Q4/OT, and inclusive `--clock-min` / `--clock-max` seconds. A clock range requires
a period; OT groups all overtime periods. Four-stage field/score/period/clock
selection reports conditional missing/outside counts without duplicate removals.
Started `codex/pre-play-clock-filters` from updated `origin/main` at `7f4bfb3`,
after confirming PR #7 merged with passing final-head CI and no outstanding review
feedback. The preceding branch was clean and matched upstream. History, canonical
clone, source bytes, and the existing 8 AM automation are preserved.

**Why it matters:** analysts can isolate comparable portions of a period without
mixing regulation and overtime, using end-of-play information, or silently dropping
unknown clocks. This completes the planned P1.3 context filters, not the whole brief.

**Review:** `src/opponent_intelligence/pbp.py` (exact nullable integers),
`report.py` (period/range validation, ordered filters and counts), `__main__.py`,
`tests/test_clock_filters.py`, the new snapshot test in `tests/test_ingestion.py`,
and the clock sections in `docs/METRICS.md` / `docs/REAL_DATA_AUDIT.md`.

**Sports concepts:** start-of-play versus end-of-play clocks; regulation period
versus OT; seconds remaining versus cumulative elapsed time; eligible zero-clock
plays; unchanged offense-relative score/EPA on either side. Q4 0..120 is not a
definition of the final two minutes of a game that may continue into overtime.

**Software/statistical concepts:** exact whole-value parsing, optional header
availability, explicit API validation, backwards-compatible optional JSON keys,
conditional missingness and ordered count partitions, independent raw/Decimal
checks, and immutable provenance. Context selection does not adjust for opponents,
remove within-game dependence, or prove historical information availability.

**What to learn:** trace the invented 13-play cohort through all four optional
filters: 13 → 10 → 9 → 5 → 3. Explain why the final three plays contain only two
EPA observations (0.8 and -0.4), so EPA/play is 0.2, success 1/2, and dropback rate
1/3. Contrast period-only selection with an explicit full 0..900 clock range when
clock values are missing.

**Three review questions:**

1. Why must a clock range name a period, and why is `game_seconds_remaining <= 120`
   not a safe substitute for Q4 selection?
2. How do a zero clock, missing clock, absent clock header, and omitted clock filter
   affect selection and denominators differently?
3. When a play lacks both period and clock, where is its removal counted, and how
   do the stage counts relate to global `eligible_rows_outside_cohort`?

**Verification/self-review:** the 112-test baseline passed. All 130 offline tests
now pass on Python 3.11/3.12/3.13 (17 clock tests and one snapshot integration test).
They exercise fractions float would round, exact boundaries, all OT periods,
overlapping missingness, absent columns even on empty inputs, retained missing EPA,
both roles, exclusive cutoffs, unchanged no-time reports, and deterministic CLI
output. Complete-diff review strengthened malformed-clock CLI coverage without
time flags, and clarified clock-max help and the docs' regulation/OT limitations.
No metric formula, eligibility rule, or original fixture changed.

The read-only spreadsheet/CSV audit informed acceptance of clock zero and kept raw
missingness separate from eligible missingness: five raw missing clocks versus
zero eligible; no missing periods. All 34,902 raw/adapter period-clock identities
and source start-time conversions match. Two eligible plays start at zero seconds.
The artifact has 174 REG OT plays in qtr 5; synthetic tests cover additional OT
periods and 900-second clocks without claiming those occur here. Independent raw
selection and Decimal EPA sums match 7,680 filtered reports and their situation
measurements; 768 no-time reports exactly match merged PR #7. Replay evidence is
documented; this is source consistency/selection verification, not gamebook or
predictive validation. No raw data or prior dated evidence was edited.

**Publication:** implementation `e85ad85` is pushed with matching local/remote SHAs
and confirmed AryanParte author/committer attribution.
[PR #8](https://github.com/AryanParte/nfl-opponent-intelligence/pull/8) is open,
unmerged, and attached to the task, with no review submissions or threads at
publication. [Implementation CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37219835829)
passed the offline regression suite and synthetic demo on Python 3.11/3.12/3.13.
The existing workflow needed manual dispatch because no automatic run appeared.
The PR description records final-head verification after this publication-record
update. No workflow code, repository settings, or daily automation changed.

**Remaining/next task:** matched league baselines for offense tendencies with an
explicit comparison population and matching season/type/week, context filters,
and down/distance. Report baseline denominators and null/small-sample behavior;
do not call descriptive differences opponent adjustment. Game-level uncertainty
and the static brief follow; UI stays deferred. Known source-availability,
automatic-CI-triggering, and in-memory scale limitations remain.

## 2026-10-05 — Matched leave-team-out league baselines

**Built / why:** `--compare-league` adds a pooled baseline of other teams in the
same role, with identical season/type/week and context filters, matching down/
distance buckets, explicit sample sizes/coverage, and selected-minus-baseline
differences. It makes tendencies interpretable against available peers without
presenting them as opponent-adjusted rankings. Started `codex/matched-league-baselines`
from updated `origin/main` at `bbf4299` after PR #8 merged with passing final CI;
the preceding branch was clean and no open PRs/reviews remained.

**Review:** `src/opponent_intelligence/report.py` (shared ordered filters,
comparison population, bucket matching, null-safe differences), `__main__.py`,
`tests/test_league_comparison.py`, the snapshot integration test, and
`docs/METRICS.md` / the baseline section of `docs/REAL_DATA_AUDIT.md`.

**Sports concepts:** compare offenses with other offenses and defenses with other
defenses while preserving offensive EPA/signs. Match down/distance and pre-play
contexts. Excluding one role does not exclude every game involving that franchise.
Both populations can share games and opponents; broad context ranges still mix
different situations and are not opponent adjustment.

**Software/statistical concepts:** one shared selection implementation prevents
filter drift; pooled numerators/denominators differ from averages of team rates.
Rate deltas are percentage points, not percent change. Null denominators propagate
to differences; an absent matching bucket never falls back to the overall rate.
Observed coverage, conditional missingness, and immutable provenance stay explicit.

**What to learn:** in the invented comparison, target dropbacks are 2/3 versus
baseline 3/5 (about +6.67 percentage points). Target EPA is 0/2 versus baseline
1/4, so the difference is -0.25, despite three versus five eligible plays. Missing
EPA is retained in dropback denominators. Baseline team rates 0/1 and 3/4 must not
be averaged to 0.375; pooling yields 0.6.

**Three review questions:**

1. In a CAR defense comparison, which plays are excluded from the baseline, and
   why can the selected cohort and baseline still share games?
2. Why does pooling baseline dropbacks/plays differ from averaging team rates, and
   why can EPA and play-call denominators differ within the same cohort?
3. What should the difference be when a matching down/distance baseline bucket is
   empty but the overall league baseline has plays, and why?

**Verification/self-review:** baseline 130 tests passed; 146 now pass on Python
3.11/3.12/3.13 (15 comparison tests plus one snapshot test). Coverage includes both
roles, all context stages and missingness, exclusive cutoffs, matching/absent
buckets, independent sample flags, empty populations, missing EPA, unmodified
non-comparison reports, deterministic CLI output, and snapshot provenance.
Complete-diff review checked role exclusion, pooled versus averaged rates, nulls
versus zero, filter order, time cutoffs, coverage, dependence, and documentation.
It found that the immutability test kept the same dataset reference; a deep copy
now makes that assertion sensitive to in-place changes. Added an explicit
after-filter team-coverage assertion and kept the socket-blocked offline guarantee
in the snapshot test, separate from the subprocess CLI determinism check.

The read-only spreadsheet/CSV audit compared 2,048 reports to independent source
selection and Decimal arithmetic, including bucket deltas and population ledgers;
2,048 non-comparison outputs exactly match merged PR #8. It confirmed variable
filtered team coverage and empty selected cohorts with nonempty baselines, so the
output exposes coverage and null differences explicitly. Replay evidence is in
the audit document. No raw data, source contract, original fixture, or existing
metric formula changed. This is selection verification, not model validation.

**Publication:** implementation `55601b0` is pushed on `codex/matched-league-baselines`;
local/remote SHAs match, and GitHub attributes both author and committer to
AryanParte. [PR #9](https://github.com/AryanParte/nfl-opponent-intelligence/pull/9)
is open, unmerged, and attached; no review submissions or threads were present.
No automatic CI run appeared, so the existing workflow was dispatched:
[implementation run](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37372593882).
All three jobs are currently queued without runners or executed steps; do not
treat this as passed or failed. The PR description will record final-head CI after
the publication-receipt update. The existing 8 AM automation is unchanged.

**Remaining / next:** check pending remote CI before new development; fix any
change-caused failures without discarding published work. Then implement
reproducible game-level uncertainty respecting shared games,
explicit support thresholds, and opt-in behavior; then the static historical brief.
Known source availability, automatic-CI-triggering, and in-memory scale limits remain.

## 2026-10-06 — Exploratory whole-game uncertainty

**Built / why:** opt-in seeded game-cluster percentile intervals for the selected
cohort, matching league baseline, and paired differences, overall and by observed
down/distance. Game support, undefined replicates, low-support/degenerate states,
and limitations prevent a large play count from masquerading as strong evidence.
Started `codex/game-cluster-uncertainty` from updated `origin/main` at `af19425`;
PR #9 was merged, the checkout was clean, and no open PRs or review feedback remained.

**Prior CI resolved:** October 5's two attempts failed before tests because hosted
runners were not assigned. The user-authorized retry on merged `main`
[passed all three jobs](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37382909725)
at `af19425`, with 146 tests and the synthetic demo per version. That supersedes
the prior entry's pending status without rewriting its dated account.

**Review:** `src/opponent_intelligence/uncertainty.py`, the opt-in integration in
`report.py` / `__main__.py`, `tests/test_uncertainty.py`, the snapshot integration
test, and `docs/UNCERTAINTY.md` / the new real-data audit section.

**Sports concepts:** plays share a game's context; a team's season provides few
games even when it has hundreds of plays. EPA remains offense-relative for defense.
Pre-play filters and temporal cutoffs precede resampling. Both sides can contain
plays from the same game, while repeated teams also create unresolved cross-game
dependence. These intervals are descriptive, not scouting or predictive validation.

**Software/statistical concepts:** aggregate sufficient per-game counts/sums,
resample entire games with replacement, share each game's multiplicity across
populations/buckets, and pool denominators rather than average game means. Local
seeded RNG and sorted identities make replay stable without global random-state
changes. Percentile bounds are pointwise and conditional on defined replicates.
Five-game, 95%-valid, and few-game warning thresholds are explicit application
policies, not guarantees of statistical coverage.

**What to learn:** in the unequal-size synthetic example, pooled EPA is 10/15,
not the unweighted mean of five game means (zero). If baseline EPA equals selected
EPA plus three within every shared game, the paired difference is always -3;
independent game draws would invent variability in that contrast. A zero-width
bootstrap interval is withheld rather than called certainty. More repetitions
reduce Monte Carlo noise but cannot add observed games.

**Three review questions:**

1. Why must both populations use the same multiplicity when a shared game is
   drawn, and why does pooling differ from averaging game averages?
2. How can a cohort have five play-supporting games but only one EPA-supporting
   game, and what happens to its intervals and undefined replicate counts?
3. Why are the five-game gate and nominal 95% bounds not a guarantee of reliable
   NFL inference, even if all software tests pass?

**Verification/self-review:** the original 146 tests passed before implementation;
161 now pass on Python 3.11/3.12/3.13. Fourteen new tests include exhaustive
enumeration of all 3,125 five-game draws and independently expanded play arithmetic
with a separate quantile routine. A twenty-third snapshot test preserves hashes
and manifests with sockets blocked. The raw read-only audit reconciled eight
1,000-replicate reports and all their buckets to Decimal/NumPy expectations, plus
eight unchanged legacy reports. It confirmed why early one/two-game cohorts need
withheld intervals and visible undefined counts. Complete-diff review checked
pairing, per-metric denominators, cutoff/filter order, empty populations, option
validation, provenance, and unsupported coverage claims. Clarified the README's
low-support example as overall intervals (missing buckets can instead be undefined),
used named per-game totals and explicit EPA units, and documented conditional
replicates, comparison-frame changes, and uncalibrated support policies. After
review, all 161 tests passed again on all three runtimes; a 1,000-draw synthetic
report had identical serialized SHA-256 across them. Both documented CLI examples
and the separate raw-record support recipe replayed successfully. `git diff --check`
passed. No remaining verified defect was found in this unit; methodological limits
remain explicit below.

**Publication:** implementation `f07b378` is pushed on
`codex/game-cluster-uncertainty` with matching local/remote SHAs and GitHub-confirmed
AryanParte author/committer attribution. [PR #10](https://github.com/AryanParte/nfl-opponent-intelligence/pull/10)
is open, unmerged, and attached; no review threads/submissions were present.
The manually dispatched existing [verification workflow](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37473511186)
passed on that exact SHA. All three job logs confirm 161 tests and the synthetic
demo passed. No automatic run appeared; that trigger issue remains separate from
the now-resolved runner allocation failure. The PR description records verification
for the later documentation-only publication head. No workflow configuration,
repository settings, or 8 AM automation changed.

**Remaining / next:** deterministic JSON-to-Markdown static historical opponent
brief with source/cohort/role traceability, denominators, baseline coverage, and
all uncertainty states preserved. Coverage calibration, cross-game dependence,
historical availability, automatic CI triggering, and larger-than-memory scale
remain explicit limitations. Do not skip to a UI or call this calibrated inference.

## 2026-10-07 — Traceable historical opponent briefs

**Built / why:** a separate offline JSON-to-Markdown command and pure rendering API.
The brief turns the existing measurements into readable cohort evidence while
keeping role, cutoff, contexts, denominator/missingness counts, baseline coverage,
every uncertainty state, method/source metadata, and warnings visible. Frozen
synthetic and retrospective CAR examples can be reviewed and replayed without
raw data. No analytical formulas, filters, bootstrap, or existing JSON defaults changed.

Started `codex/static-historical-brief` at updated `origin/main` `07ee523` after
confirming PR #10 merged. The previous checkout was clean with no unpublished
commits. No open PRs/reviews remained. PR #10's exact final-head CI was successful;
the merge tree matched it, and all 161 baseline tests passed locally. No new
merged-main CI run was present, so this does not claim one occurred.

**Review:** `src/opponent_intelligence/brief.py`, `brief_validation.py`,
`tests/test_brief.py`, `docs/BRIEFS.md`, and the two JSON/Markdown pairs under
`docs/examples/`. Start with the synthetic example before reading the real one.

**Sports concepts:** a defensive brief still reports opposing offensive EPA and
success, not sign-reversed efficiency or defensive stops. Plays and observed EPA
have distinct denominators. A baseline can share games and have missing matching
buckets; an overall league average is not a valid substitute. The CAR example's
984 plays are only 17 games, and its source was acquired in 2026, not before a
2024 matchup. Percentile intervals remain exploratory and uncalibrated.

**Software/statistical concepts:** separate measurement from presentation; validate
saved inputs and cross-field relationships before emitting any text; match buckets
by keys rather than array position; preserve null/zero and optional/empty states.
Percentages and percentage-point differences use different scaling. A content
fingerprint ties a brief to a report, while input bytes have a separate fingerprint.
Rendering escapes untrusted text without activating links, images, or HTML.

**What to learn:** the synthetic report has six eligible plays but only five
observed EPA values: dropbacks are 3/6, success is 3/5, and EPA is 0.2/5. Display
rounding must not change the underlying values. A digest proves content identity
under a stated serialization rule, not authenticity, complete coverage, historical
availability, or good statistical inference. `1.0` versus `1` can change this
application's report fingerprint even when the numeric measurement is equal.

**Three review questions:**

1. Why do the synthetic dropback and success rates use different denominators,
   and why must missing EPA or an unavailable interval never display as zero?
2. Why are comparison rows joined by down/distance keys, and what would go wrong
   if a missing bucket borrowed the overall baseline or a pp difference were scaled again?
3. What exactly does each fingerprint identify, and what cannot be concluded
   about authenticity, historical availability, or statistical reliability from it?

**Verification / self-review:** all 181 tests pass on Python 3.11/3.12/3.13,
including 20 new renderer tests. Both examples replay byte-for-byte offline; the
synthetic JSON/brief also regenerate from the original fixture. Thirty-two pinned
CAR report combinations rendered without changing their JSON and retained source
fingerprints. This checks integration, not a new raw-data/statistical audit.
A separate bundled Markdown parser rejected activation of hostile sample markup;
a network-blocked headless preview showed readable tables and no horizontal
overflow at 1280 pixels. No parser/browser dependency was added to the project.

Review fixed an example-generation fingerprint mismatch caused by intermediate
numeric normalization: saved examples now retain the pipeline's Python JSON, and
the synthetic source-to-brief replay is asserted exactly. Added checks for changed
context coordinates/timing, inconsistent ledgers, missing provenance notices,
integer success counts, and impossible empty selected buckets. The complete diff
(source, tests, docs, and generated evidence) was reviewed for units, denominator
and role errors, unsupported inference, unsafe markup, determinism, and scope.
Kept team lists compact without dropping coverage, and removed Markdown trailing
whitespace. All 181 tests passed again on all three runtimes; the full pinned-source
CLI pipeline reproduced the historical Markdown byte-for-byte. Final staged
`git diff --check` passed. No remaining verified defect was found; limitations remain
explicit rather than being presented as completed validation.

**Publication:** implementation `36aaff3` is pushed on
`codex/static-historical-brief` with matching local/remote SHAs and GitHub-confirmed
AryanParte author/committer attribution. [PR #11](https://github.com/AryanParte/nfl-opponent-intelligence/pull/11)
is open, unmerged, and attached; no review threads/submissions were present.
The existing [verification workflow](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37694342796)
passed on that exact SHA, with 181 tests and the synthetic demo successful in each
of the three job logs. It was manually dispatched after no automatic run appeared.
The PR description records verification for the later documentation-only head.
No raw data, workflow settings, or 8 AM automation changed.

**Remaining / next:** audit personnel/motion field availability and licensing,
then document feasible-versus-deferred scope before closing P1.3 or building P1.4.
The brief is a one-team historical cohort summary, not a two-team matchup model.
Ingestion checks raw-byte integrity; rendering does not reverify raw bytes or the
authenticity of arbitrary saved JSON.
Calibration, repeated-team dependence, historical availability, automatic CI
triggering, and larger-than-memory ingestion remain explicit limitations.

## 2026-10-08 — Personnel/motion availability and scope decision

**Built / why:** an offline, byte-verified field inventory and primary-source
availability/licensing review. The pinned 2024 PBP has 372 columns but lacks the
personnel and motion candidates. The audit separates absent columns, all-missing
values, empty populations, observed zeroes and unknown numeric flags. The decision
closes P1.3 within its useful PBP-only brief scope; supplementary enrichment is
deferred, not implemented or declared impossible. No existing metric, report,
source byte, license, workflow or daily automation was changed.

Started `codex/personnel-motion-audit` from fetched `origin/main` `5fd1adc` after
confirming PR #11 merged. The old checkout was clean and matched upstream; no
open PRs or review feedback remained. Its final-head CI at `955bc2d` was successful
and the merge tree identical. No new merged-main run was present. All 181 baseline
tests passed before implementation.

**Review:** `src/opponent_intelligence/availability.py`, `tests/test_availability.py`,
`docs/PERSONNEL_MOTION.md`, and `docs/evidence/pbp-2024-23370d5d10f8.availability.json`.
Read the scope/source table before interpreting the field counts.

**Sports concepts:** personnel composition, formation, tempo and motion are
different concepts. Shotgun/no-huddle flags cannot identify RB/TE packages or motion.
FTN's documented motion flag covers before or at the snap, not motion type/speed.
Recent participation delivery is post-season; today's retrospective file cannot
automatically become a feature available during that season.

**Software/statistical concepts:** distinguish schema presence from observed data
and semantic validity. Keep raw versus eligible denominators and source-specific
terms/provenance. Extra non-missing columns are not silently promoted into the
adapter contract. Inventory output is deterministic, and hashes identify the
audited bytes; they do not prove charting quality or historical availability.

**What to learn:** among 34,902 eligible plays, 24,703 have shotgun=1 and 4,398 have
no_huddle=1, with no missing/other numeric codes. These describe their own indicators,
not personnel or motion. An absent motion column has no measurable false count.
A documented public dataset and published digest still require acquisition,
byte verification, duplicate-safe joins, missingness review and release-time
evidence before it can support a defensible new metric.

**Three review questions:**

1. How do absent columns, all-missing values, empty cohorts and observed zeroes
   differ, and why must a motion-rate denominator exclude unknown/unmatched flags?
2. Why can shotgun/no-huddle or a backfield count not substitute for personnel
   composition or motion, even when their values are non-missing?
3. What must be verified before joining and publishing FTN enrichment, and why
   do post-season delivery and current-file timestamps matter for historical evaluation?

**Verification / self-review:** 195 tests pass locally on Python 3.11/3.12/3.13,
including 14 new synthetic tests. They cover raw/eligible partitions, zero/missing/
absent/empty distinctions, invalid flags, no alias/text inference, provenance,
malformed inputs, corruption, deterministic counts and blocked-network CLI replay.
The frozen evidence replays byte-for-byte with connections blocked. A separate raw
CSV/Decimal check reconciled all 20 candidates and the 49,492 raw / 34,902 eligible
denominators without using adapter eligibility. Primary definitions/loaders were
pinned to a source commit; supplementary assets were inspected as metadata only,
not downloaded or misrepresented as coverage-validated data.

Review checked the complete diff for denominator mistakes, accidental proxy
claims, mixed licensing, temporal leakage, inflated validation claims and unnecessary
scope. Clarified that the season-type policy applies to eligible rows, not a new
validation of every raw administrative row. Corrected test setup for CRLF malformed
headers and network blocking without breaking SSL imports. Removed a duplicate
documentation heading. Remote publication, exact SHA attribution and CI results
are recorded in the feature PR rather than inferred from these local checks.

**Remaining / next:** implement the first P1.4 FastAPI report endpoint using an
explicitly configured immutable local snapshot and the existing report builder.
Add synthetic request/response/error tests, bound expensive options, and keep API
dependencies optional; no arbitrary path inputs or per-request downloads. Enrichment,
legal review for particular redistributed adaptations, calibration, historical
availability, automatic CI triggering and larger-than-memory ingestion remain
separate unfinished work. Do not restart the brief or change the daily schedule.

## 2026-10-08 — Local snapshot report API (additional manual run)

**Built / why:** the first P1.4 product boundary, optional FastAPI `GET /v1/report`
over one explicitly configured, verified local snapshot. Requests reuse the pure
builder/schema v2 with bounded options and stable errors; they cannot choose files,
change labels or download data. Startup loads once, and overlapping report builders
receive 503 rather than accumulating expensive queued work. API/test dependencies
and CI are separate from the dependency-free core. This exposes existing evidence
to a future interface without introducing a second measurement implementation.

Started `codex/snapshot-report-api` from fetched `origin/main` `9f9a647` after PR #12
merged. The previous checkout was clean, matched upstream and had no unpublished
commits. No open PRs/reviews remained. Final-head CI for `62bdcc1` passed and the
merge tree matched; no new merged-main run was present. All 195 baseline tests
passed locally. This manual run does not replace or alter the 8 AM automation.

**Review:** `src/opponent_intelligence/api.py`, `api_models.py`,
`tests_api/test_api.py`, `tests/test_optional_api.py`, `pyproject.toml`,
`requirements/api-constraints.txt`, `.github/workflows/ci.yml` and `docs/API.md`.
Trace one request from query model through the unchanged builder to the response.

**Sports concepts:** offense-relative EPA and success keep their meaning in
defense mode. Six synthetic plays but only five EPA observations still mean
different rate denominators. An empty cohort returns null rates, not invented
zero performance. A 1,000-resample cap is a compute policy, not a sample-size or
calibration guarantee. Source acquisition in 2026 remains explicit even when
the request cutoff selects 2024: this is retrospective analysis, not proof of
pregame information availability.

**Software/statistical concepts:** separate trusted operator configuration from
untrusted query input; load and verify in application lifespan, not per request;
preserve null versus absent fields; validate response shape without duplicating
statistical formulas. A per-instance nonblocking lock is not distributed rate
limiting. Row/game limits after parsing are not a streaming memory cap. Optional
dependencies and constrained versions preserve the lightweight core; constraints
are not artifact-hash/build-tool locks.

**What to learn:** immutable input identity and stable transport contracts make
integration testable. A successful HTTP response does not certify statistical
reliability. Inspect source fingerprints, denominators, warnings and missingness
before discussing a result, and distinguish independent fixture expectations
from equivalence checks against the existing builder.

**Three review questions:**

1. Why does changing a cache pointer or passing a snapshot path in a query not
   change the served dataset, and what operator action is required to change it?
2. Why do empty reports keep null rates and absent opt-in blocks, and why must
   defense EPA and the observed-EPA denominator survive serialization unchanged?
3. What work do the query/resample bounds and per-instance lock limit, and what
   memory, concurrency, latency, security and inference guarantees do they not provide?

**Verification / self-review:** 196 core plus 20 API tests pass on all three Python
versions (3.11/3.12/3.13); API tests also pass with warnings treated as errors,
and optional environments pass `pip check`. Clean 3.11/3.12 installs resolved the
constrained extras. Tests block network access and cover response/core equivalence
plus independent counts, invalid inputs, startup integrity, resident-data stability,
missing context, resource bounds, real request overlap/recovery and sanitized
builder/response failures. The core CLI passes with site packages disabled.

The pinned real historical report replays exactly under sorted JSON serialization,
including numeric types, with 1,000 resamples and seed 20261006. Ten further role/
context combinations match the builder with network blocked. A real loopback
Uvicorn factory returned 200 and the expected 984 plays, then was stopped. These
are integration checks, not additional independent source or statistical audits.

Review replaced the deprecated `httpx` TestClient fallback with current `httpx2`,
added invalid/nonfinite response, default/maximum seed and period-without-clock
coverage, and retained a request-local dataset reference. Reviewed the complete
diff for dependency coupling, paths/exception exposure, source replacement,
concurrency cleanup, missing-data/role/cutoff mistakes and overclaimed limits.
Documented that nested variable method/context dictionaries remain governed by
the core contract, rather than claiming full semantic OpenAPI validation.
Remote SHA, AryanParte attribution and exact-head CI receipts are recorded in
the feature PR; local checks alone do not claim remote success.

**Remaining / next:** a narrow React/TypeScript local view consuming this endpoint,
with query controls, provenance, counts/rates, loading/error/empty/null states and
contract tests. Choose the local browser/API connection deliberately; no CORS
policy, authentication, database, deployment or UI was added here. Snapshot loading
is still memory-resident; bounds are not performance benchmarks. Calibration,
historical availability, enrichment and automatic CI triggering remain separate
limitations. Review this PR before starting another unit; do not merge automatically.
