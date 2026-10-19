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
historical availability and enrichment remain separate limitations. Review this
PR before starting another unit; do not merge automatically.

**Publication:** implementation `0054dcd` is pushed with matching local/remote
SHAs and GitHub-confirmed AryanParte author/committer attribution.
[PR #13](https://github.com/AryanParte/nfl-opponent-intelligence/pull/13) is open,
unmerged and attached. Its automatic
[push workflow](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37853903611)
passed all six jobs on this exact implementation SHA. Logs confirm 196 core and
20 API tests per runtime, successful optional-dependency checks and synthetic
demos. Unlike earlier runs, no manual dispatch was needed. A separate PR-triggered
run was queued at this checkpoint; the PR description records final-head CI after
this documentation receipt. No repository trigger settings or daily automation
were changed. This observation does not establish a cause for earlier CI issues.

## 2026-10-09 — First local report viewer (scheduled run)

**Built / why:** a narrow React/TypeScript view of the existing snapshot API.
Five explicit query controls lead to overall metrics, down/distance rows, missing
EPA counts, sample warnings and source timestamps/fingerprints. Loading, empty,
failure, manual retry and timeout states are distinct. Editing controls removes
the old result and cancels the request; late responses cannot relabel an older
cohort. A loopback-only Vite proxy connects the browser to the existing API without
changing CORS, adding a database, deploying anything or downloading source data.

Started `codex/local-report-view` from fetched `origin/main` `39af171` after PR #13
merged. The checkout was clean and matched its upstream; the merge tree matched
the prior feature head. The merged-main workflow passed all six Python jobs, no
open PRs/reviews remained, and the 196 core / 20 API baseline tests passed. The
canonical clone and history are preserved; the daily automation is unchanged.

**Review:** `web/src/App.tsx`, `web/src/report.ts`, their tests, `web/vite.config.ts`,
`web/config.test.ts`, `tests_api/test_frontend_contract.py`,
`tests_api/synthetic_snapshot.py`, `.github/workflows/ci.yml` and `docs/WEB.md`.
Trace an edited query through abort/response identity checks into the rendered
cohort, then compare the synthetic browser fixture with its actual API replay.

**Sports concepts:** dropback rate uses all eligible plays, while EPA and success
use observed EPA only. Defense displays opposing offensive production without
reversing EPA or calling offensive success a defensive stop. Short distance includes
zero yards. Missing/empty rates are unavailable, not zero. Source acquisition and
asset-update dates remain visible: a week cutoff on a retrospective snapshot does
not prove pregame availability, and a count flag is not a reliability test.

**Software/statistical concepts:** consumed-contract validation, same-origin
loopback proxying, immutable source identity, optional dependency boundaries,
request cancellation and stale-response suppression. Counts partition across
situations; game counts and rates do not sum. Synthetic end-to-end contract fixtures
catch drift, but agreement between layers is not independent validation of source
data or statistical calibration. Display rounding never changes API measurements.

**What to learn:** trustworthy interfaces preserve analytical meaning, including
denominators and unavailable values. A successful HTTP status alone is insufficient:
verify the returned cohort, schema and provenance before showing measurements.
The first view deliberately does not request comparison or bootstrap calculations;
it rejects unexpected advanced blocks instead of hiding or mislabeling them.

**Three review questions:**

1. Why can six plays produce a 50% dropback rate and 60% success rate, and what
   changes in the interpretation—not the signs—when the selected role is defense?
2. How do the request sequence, abort signal and returned-cohort checks prevent
   a slow response from displaying a report under newly edited controls?
3. What do the source timestamps, hashes, synthetic contract replay and live
   browser checks establish, and what availability or reliability claims do they
   not justify?

**Verification / self-review:** 51 frontend tests, TypeScript checking and the
production bundle build pass on Node 24.19.0 after clean locked installs. All 196
core and 21 API tests pass on Python 3.11/3.12/3.13, with API warnings treated as
errors. The new API test regenerates the labeled browser fixtures exactly with
network blocked; fixed stored gzip blocks and an OS byte prevent platform-specific
fixture hashes. CI adds one frontend job while keeping the six Python jobs separate.

An isolated Chrome 154 loopback check exercised the real pinned 2024 snapshot:
no initial fetch, CAR offense (984 plays, 626 dropbacks, EPA/play -0.052 and 41.4%
success), defense and an empty cutoff. There were no page errors or external page
requests, repository-file access outside `web/` returned 403, and desktop/mobile
layouts were inspected with no page overflow at 390px. The committed screenshot
is actual desktop output; these are local integration checks, not browser CI,
load benchmarks or accessibility certification. No source bytes were changed.

The live check exposed an initially overstrict UTC timestamp decoder (`Z` only);
it now accepts the acquisition tool's fractional `+00:00` timestamps, with a
regression test. Review also fixed short-distance wording, missing versus zero EPA
test assumptions, Node/DOM test isolation and the mobile selector. It added date
validity, bucket partition, JSON media-type and safe error-lookup guards. Reviewed
the complete diff for stale/mismatched cohorts, misleading denominators, hidden
warnings, source/path exposure, dependency coupling and scope. Exact published SHA,
GitHub attribution and remote CI evidence are recorded in the PR; local checks
alone do not claim remote success.

**Remaining / next:** add an opt-in matched league comparison view using the
existing API, including actual baseline coverage, matched situation buckets,
percentage-point differences and unavailable comparisons. Broader context filters,
uncertainty, downloads, a CI browser demo and a broader accessibility review remain
unfinished P1.4 slices. Keep the calculations in the existing builder and inspect
this branch's PR/CI before continuing; do not merge automatically.

## 2026-10-10 — Opt-in matched league comparison view

**Built / why:** a comparison checkbox and local browser panel using the existing
API. Selected/baseline measurements retain observed team coverage, play/game/EPA
counts, missingness, sample flags, matching situations and all baseline warnings.
Differences show percentage-point or EPA/play units. Empty/unknown comparisons
stay distinct from unrequested calculations; edits abort work and discard stale
responses. This makes the existing comparison inspectable without a second
analytics implementation, new dependencies or a deployment.

Synced the canonical clone and started `codex/league-comparison-view` at `fcba137`
after PR #14 merged. Its tree matched `01cb6cd`, merged-main CI passed all seven
jobs, no open PRs/review findings remained, and the checkout was clean/in sync.
Baseline 196 core / 21 API / 51 frontend tests passed before implementation.

**Review files:** `web/src/ComparisonView.tsx`, `web/src/report.ts`,
`web/src/comparison.test.tsx`, `web/src/App.tsx`,
`tests_api/test_frontend_contract.py`, `docs/WEB.md` and the comparison screenshot.

**Sports/statistical concepts:** exclude the selected team in the same role, not
every game involving it. Pool plays rather than team averages; show observed
coverage rather than assume a complete league. Defense remains offensive
production allowed. Rate differences are percentage points, not percent change.
Missing EPA leaves dropback denominators intact. Baseline-only buckets contribute
to overall totals but not selected-team rows, and populations may share games.

**Software concepts / what to learn:** align buckets by identity, validate the
returned cohort and requested optional block, and keep UI cancellation separate
from server computation. Difference validation checks returned arithmetic/units
within 1e-9; rendering uses the API's estimate. Rounded cells may not subtract to
the rounded difference. Synthetic contract replay tests integration, not the
truth of real observations or predictive calibration.

**Three review questions:**

1. Why can the displayed baseline situation counts sum to less than its overall
   count, and why must an unmatched bucket never use the overall baseline rate?
2. What does a +3.4 pp dropback difference mean, and why is a positive defense
   EPA difference not automatically an improvement or an opponent-adjusted result?
3. How do comparison presence checks, bucket keys and abort/sequence handling
   prevent a valid-looking response from being attached to the wrong query?

**Verification / self-review:** 99 frontend tests, type-check/build and clean
locked installation pass on Node 24.19.0. All 196 core and 21 API tests pass on
Python 3.11/3.12/3.13, with API warnings treated as errors. Ten explicitly synthetic
endpoint fixtures replay with network blocked. New checks cover units/signs,
missing/empty populations, baseline-only and reordered buckets, malformed
coverage/ledgers/optional blocks, literal warnings and stale-toggle responses.

Isolated Chrome 154 reproduced the frozen CAR 2024 REG-before-19 comparison
exactly: 984 selected versus 32,351 baseline plays, 31 observed baseline teams,
17 shared games and 12 matched rows. Overall and expanded-row rendering, defense,
toggle-off and 390px layout passed, with no external page requests or page errors.
The screenshot is actual retrospective output. No new source data was acquired.

Full-diff review checked default-off compatibility, bucket joins, null/zero and
denominator handling, hidden warnings, temporal/coverage claims and scope. It
retained unequal baseline bucket totals, normalized displayed negative zero and
clarified unrounded differences. Test selectors were fixed to distinguish intended
rows from repeated text in collapsed details. Core/API code, dependencies, workflow
configuration and daily automation are unchanged. Exact publication, attribution
and CI receipts are recorded in the feature PR, not inferred from local checks.

**Remaining / next:** optional pre-play field-position controls with inclusive/
default bounds and explicit missing-context accounting for both populations.
Score/clock controls, uncertainty, downloads, browser CI and broader accessibility
work remain unfinished. No inference calibration, historical pregame availability
or public deployment is claimed. Review the PR before continuing; never auto-merge.

## 2026-10-11 — Optional pre-play field-position controls

**Built / why:** minimum/maximum yards-to-goal controls and a returned-filter
accounting panel over the existing snapshot API. Both populations keep inclusive
bounds, offense-relative coordinates, missing-position exclusions and the existing
metric denominator rules. Blank versus zero/full-range, source-column errors and
empty results stay distinct. Every edit invalidates previous results. This makes
the existing field-position analysis usable and auditable without another
measurement implementation, dependency, database or deployment.

Fetched the canonical clone and started `codex/field-position-view` from updated
`origin/main` at `c9b9087` after PR #15 merged. Its tree equals feature head
`a3f1e71`; merged-main CI passed all seven jobs. No open PRs/reviews remained,
the checkout matched its upstream with no local changes, and baseline 196 core /
21 API / 99 frontend tests passed before implementation. History is preserved.

**Review files:** `web/src/report.ts`, `web/src/App.tsx`,
`web/src/FieldPositionView.tsx`, `web/src/field-position.test.tsx`,
`tests_api/test_frontend_contract.py`, and `docs/WEB.md` with the new screenshot.

**Sports/statistical concepts:** field position is measured before the play,
toward the offense's opponent's goal, even in defense mode. A 0–20-yard play
cohort is not drive-level red-zone efficiency. Context missingness and EPA
missingness change different denominators. Full-range filtering can remove
unknown positions, unlike no filter. Baseline exclusion occurs before context
selection, and each population needs its own count reconciliation. These are
descriptive available-source cohorts, not adjusted or causal effects.

**Software concepts / what to learn:** model omission separately from zero;
serialize only explicit options but validate the returned effective defaults.
Compare nested cohort values rather than object references. Validate both local
stage partitions and cross-population totals before rendering. Preserve malformed
text for validation rather than allowing numeric-input sanitization to convert
it to blank. API-generated fixtures verify transport compatibility, while small
hand-checkable expectations expose unit/denominator mistakes. Source/time cutoffs
and hashes still do not prove historical information availability.

**Three review questions:**

1. Why can blank bounds and an explicit 0–100 range return different counts,
   and how is a missing position different from missing EPA or an absent column?
2. When selecting CAR defense at 0–20, whose goal line is the target, and why
   must neither the coordinates nor EPA be reversed or called drive efficiency?
3. Why must baseline `excluded_selected_team_rows` equal the selected count
   before field filtering, and which checks prevent a stale or mismatched report?

**Verification / self-review:** 184 frontend tests, clean locked install and
type-check/build pass on Node 24.19.0. All 196 core / 21 API tests pass on Python
3.11/3.12/3.13 with API warnings treated as errors; `pip check` finds no broken
requirements. Twenty-two labeled synthetic endpoint fixtures replay with network
blocked. All ten original fixtures remain unchanged. Twelve additions cover
both roles, comparison on/off, zero/default/fractional/full ranges, same-source
unfiltered output, empty pre-week counts and missing context in either population.
Tests reject bad filter identity/policy/counts, hidden filters, incorrect temporal
totals, stale edits and missing-column fallback.

Six Chrome 154 loopback queries exercised real 2024 REG-before-19 data. At 0–20,
CAR offense retains 156 / 984 plays versus 4,991 / 32,351 baseline plays; neither
has missing positions, with 828 / 27,360 outside-range exclusions. CAR defense
retains 218 / 1,131 versus 4,929 / 32,204. Lower-only, fractional/zero empty and
cleared-filter states passed; cleared overall/comparison blocks match the frozen
historical report exactly. Malformed text makes no request. Desktop/mobile
inspection found no document overflow at 390px; accounting tables scroll by
keyboard. No external page requests or page errors occurred. The screenshot is
actual retrospective output; both owned servers were stopped. This is integration
evidence, not a fresh raw-data audit, calibrated inference, load test or browser CI.

Full-diff review checked defaults, field/cohort identity, missing/zero handling,
pre-filter leave-team-out counts, double-counted exclusions, warnings, source/time
claims and unrelated scope. It added same-source unfiltered and zero-base fixtures,
kept invalid text distinct from omission, and corrected a clipped evidence image.
It clarified baseline goal-line wording and scoped the global-exclusion note to
the selected cohort so population-specific counts are not confused.
No core/API code, source bytes, dependencies, workflow settings or daily automation
changed. Exact published SHA, GitHub attribution and CI receipts belong in the
feature PR; local success alone is not proof of remote CI success.

**Remaining / next:** optional signed whole-point pre-play score controls, composed
with field position using the existing order. Show selected/baseline per-stage
missing/outside/retained counts and validate both effective cohorts. Clock controls,
uncertainty display, downloads, browser CI and broader accessibility remain open.
Keep the builder canonical, inspect PR/CI before continuing, and never auto-merge.

## 2026-10-12 — Pre-play score controls and ordered context accounting

**Built / why:** signed whole-point score controls with unbounded blank ends,
inclusive ties, offense-relative signs in either role, and a returned-score
accounting panel. Both populations now show field survivors feeding score before
final metrics. Validation rejects wrong context identities, order, disconnected
stages and final counts. Existing stale-response, safe-error and explicit-submit
behavior applies. This makes score-context analysis auditable without new formulas,
dependencies, downloads, storage or deployment.

Fetched the stable clone, verified PR #16 merged at `a83a3c2` (same tree as
`0a957cc`) and all seven merged-main CI jobs passed. The previous branch was clean
and matched upstream; no open PRs/reviews remained. Started `codex/pre-play-score-view`
from updated `origin/main`; baseline 196 core / 21 API / 184 frontend tests passed.

**Review files:** `web/src/report.ts`, `web/src/ScoreView.tsx`, `web/src/App.tsx`,
`web/src/FieldPositionView.tsx`, `web/src/score.test.tsx`,
`tests_api/test_frontend_contract.py`, and `docs/WEB.md` with the real screenshot.

**Sports/statistical concepts:** pre-play offense points minus defense points;
negative still means the opposing offense trails when viewing defense. Zero is a
known tie, not missing. Missing score and missing EPA affect different denominators.
After field selection, score missingness is conditional; a play missing both is
excluded only once. Final play/game/team coverage describes the intersection, not
an adjusted, causal, neutral-game or predictive conclusion.

**Software concepts / what to learn:** distinguish invalid text, omitted options,
nullable unbounded ends and numeric zero. Validate both nested identities and
ordered count chains; preserve schema v2's older field-only shape. API-generated
fixtures check interoperability while hand-checkable expectations detect shared
mistakes. Keep the existing builder as the measurement source, not duplicated UI
analytics. Client validation complements, never replaces, the API boundary.

**Three review questions:**

1. What does score -7 mean for CAR defense, and why would selecting post-play
   scores or replacing a missing score with zero change the cohort incorrectly?
2. Why does a play missing both position and score appear only in the field
   exclusions, and how do stage counts reconcile with final metrics and baseline exclusion?
3. How do blank, `0`, and `-` differ at the input/request/response boundaries,
   and which checks prevent stale or misidentified measurements from appearing?

**Verification / self-review:** 290 frontend tests, clean locked install and
type-check/build pass on Node 24.19.0. All 196 core / 21 API tests pass on Python
3.11/3.12/3.13; API warnings are errors and `pip check` passes. Thirty-seven labeled
synthetic API fixtures replay offline; all 22 previous fixtures are unchanged.
Fifteen additions cover both roles, standalone/combined context, open ends, ties,
input limits, missing score/EPA and empty cohorts. Mutation and interaction tests
cover wrong identity, ordering/linkage, invalid inputs, stale edits and safe errors.

Six isolated Chrome 154 real-snapshot queries passed. For CAR offense before 2024
REG week 19 with field 0–20 and score -7–0, counts are 984 → 156 → 90; the baseline
is 32,351 → 4,991 → 2,244. Defense, one-ended positive/negative ranges and ties also
passed. Clearing filters restores the frozen overall/comparison blocks exactly.
Desktop/mobile inspection, 390px document width, keyboard table scrolling, invalid
partial-sign no-fetch behavior and no external requests/page errors passed. Both
owned servers were stopped; the screenshot is actual retrospective output.

Review corrected field-only final-count/retention assumptions for chained filters,
made missing-column guidance context-neutral, scoped a duplicate-text test selector
and used tolerance for a hand-computed floating-point EPA expectation. No analytics,
API, raw data, dependency, workflow or automation changes. Local checks are not
remote CI receipts; the published PR records exact SHA, attribution and CI results.

**Remaining / next:** period/clock controls with explicit Q1–Q4/OT, period required
for seconds bounds, zero/missing distinctions and four-stage population accounting.
Uncertainty display, downloads, browser CI and broader accessibility remain open.
No source-availability, calibration, load-test or deployment claim. Inspect this
branch's PR/reviews before continuing and never auto-merge.

## 2026-10-13 — Period/clock controls and four-stage cohort accounting

**Built / why:** Q1–Q4/OT selection and optional inclusive whole-second clock
bounds over the existing API, with separate selected/baseline period and clock
ledgers. Earlier field/score counts are intermediate when time filters follow;
all final metrics retain their proper denominators. This exposes game context
without new analytics, silent cohort broadening, downloads or dependency changes.

Fetched the stable clone and verified PR #17 merged at `4872669`, with the same
tree as `4e402a1` and all seven merged-main CI jobs successful. The prior checkout
was clean and matched upstream, with no open PRs or review feedback. Started
`codex/period-clock-view` from updated `origin/main`; baseline 196 core / 21 API /
290 frontend tests passed. The 8 AM automation was not modified.

**Review files:** `web/src/report.ts`, `web/src/TimeView.tsx`, `web/src/App.tsx`,
`web/src/FieldPositionView.tsx`, `web/src/ScoreView.tsx`, `web/src/time.test.tsx`,
`tests_api/test_frontend_contract.py`, and `docs/WEB.md` with the real screenshot.

**Sports concepts:** clock means seconds remaining in the period at play start,
not elapsed or cumulative game time. Q4 excludes OT; OT includes every period
numbered 5 or higher. Period-only can retain missing clocks; an explicit full-clock
range excludes them. Zero is observed. Field → score → period → clock counts are
conditional, and a play missing multiple contexts is excluded only at its first
active missing stage. Final sample sizes and missing EPA remain distinct.

**Software/statistical concepts / what to learn:** distinguish omitted, zero,
invalid and missing values; enforce dependent query options before fetching.
Validate nested cohort identity, units/timing, ordered partitions and pre-context
leave-team-out totals. API-generated fixtures detect cross-layer drift while
hand-calculated cases test assumptions. Keep computation server-side, preserve
stale-response protection, and do not mistake tiny context samples for reliable
scouting findings or historically available predictors.

**Three review questions:**

1. Why can Q4-only and Q4 0–900 produce different samples, and why is Q4 0–120
   not interchangeable with the last two minutes of every game?
2. For a play missing both period and clock after field/score filtering, which
   ledger counts the exclusion and how do all four stages reconcile to final plays?
3. Why must baseline team exclusion use pre-context counts, and how do query
   validation, response identity checks and request cancellation protect the display?

**Verification / self-review:** 418 frontend tests, clean lockfile installation
and type-check/build pass on Node 24.19.0. All 196 core / 21 API tests pass on
Python 3.11/3.12/3.13; API warnings are errors and `pip check` passes. All 58 labeled
synthetic endpoint fixtures replay offline; the 37 previous cases are unchanged.
New tests cover every period, multiple OTs, period-only without a clock column,
zero/one-ended/full ranges, missing/empty populations, both roles, broken metadata/
stage chains, invalid inputs, clearing controls, late responses and safe API errors.

Seven isolated Chrome 155 loopback queries passed on the pinned retrospective
2024 snapshot. CAR offense, REG before week 19, field 0–20, score -7–0, Q4 0–120
gives 984 → 156 → 90 → 4 → 0 plays versus 32,351 → 4,991 → 2,244 → 426 → 139
other-offense plays; the empty selected sample stays empty. Defense, OT, period-only,
full/zero clock and clearing controls also passed. Cleared overall/comparison
blocks match the frozen report exactly. Desktop/mobile inspection, 390px document
width, keyboard table scrolling, invalid-input no-fetch behavior and zero external
page requests/errors passed. Both owned test servers were stopped.

Complete-diff review relabeled intermediate field/score survivors, generalized the
ordered validator without changing analytics, and clarified the field caption's
season/week selection so it cannot be mistaken for later period filtering. Initial
test selectors were fixed to use accessible-name prefixes and actual help text;
all verification reran. No API/core, source, dependency, CI or automation changes.
The published PR records exact SHA, attribution and CI; local checks alone are
not remote CI receipts or statistical/accessibility/load validation.

**Remaining / next:** expose the existing opt-in exploratory game-bootstrap API
controls and returned per-metric uncertainty/support states, with bounded options,
selected-only/opt-in comparison support, method/dependence caveats and no browser
recomputation.
Downloads, browser CI and broader accessibility remain open. Inspect this branch's
PR/reviews before continuing; never merge automatically.

## 2026-10-14 — Exploratory uncertainty controls and game-support tables

**Built / why:** opt-in, bounded game-bootstrap controls and returned overall/
matching-situation intervals over the existing snapshot API. Selected-only and
comparison reports show contributing games, defined/undefined draws and every
withheld/unavailable status alongside point estimates. This makes the amount of
evidence visible without replacing the builder, inferring certainty from missing
intervals or presenting exploratory bounds as calibrated confidence.

Fetched the canonical clone and verified PR #18 merged at `1b1a37e`, with the same
tree as `c47ffea` and all seven merged-main CI jobs successful. The prior checkout
was clean and matched upstream, with no open PRs or review findings. Started
`codex/uncertainty-view` from updated `origin/main`; baseline 196 core / 21 API /
418 frontend tests passed. Initial connector transport trouble was bypassed with
bounded public GitHub reads; the connector later recovered. No repository, access,
global identity or 8 AM automation settings were changed.

**Review files:** `web/src/uncertainty.ts`, `web/src/UncertaintyView.tsx`,
`web/src/report.ts`, `web/src/App.tsx`, `web/src/uncertainty.test.tsx`,
`tests_api/test_frontend_contract.py`, and `docs/WEB.md` with the real screenshot.

**Sports concepts:** game support is not a count of independent plays. Dropbacks
use games with eligible plays; EPA/success require observed EPA. Both populations
use the same cohort filters and offensive sign, including defense mode. Shared
games appear once in the comparison resampling union, and missing matching
baseline buckets never borrow overall support. Repeated teams/opponents still
create cross-game dependence that whole-game resampling does not remove.

**Software/statistical concepts / what to learn:** omitted repetitions, seed zero,
invalid text and requested-but-undefined output are different states. Gate
precedence, paired valid counts, per-metric support and subset consistency belong
in a defensive transport boundary. Differences are computed within shared draws,
not by subtracting endpoints. Percentile bounds need not contain the original
estimate; pointwise nominal 95% does not mean simultaneous or calibrated coverage.
More draws add computation, not games. A seed needs the same source/cohort/runtime
for replay, and client cancellation does not cancel server computation.

**Three review questions:**

1. Why does CAR's 17-game selected sample with 272 baseline games use a 272-game
   union, and why can enabling comparison change the selected interval?
2. How can a valid point estimate have a withheld interval, and how do zero EPA
   support, fewer than five games, too few defined draws and degeneracy differ?
3. Why must paired differences use the same draws, and which checks prevent
   wrong-query results, impossible support counts or stale responses from display?

**Verification / self-review:** 545 frontend tests, clean locked installation and
type-check/build pass on Node 24.19.0. All 196 core / 22 API tests pass on Python
3.11/3.12/3.13, with API warnings as errors and clean dependency checks. Thirteen
new synthetic fixtures replay through the actual endpoint with networking blocked;
all 58 previous fixtures are unchanged. Two explicitly labeled controlled-RNG
cases check 189/200 versus 190/200 defined draws, not real seed behavior or
calibration. Independent pooled/support counts and contract mutations cover all
statuses, both roles, empty frames, missing EPA/buckets, limits and context queries.
UI tests cover explicit retry, invalid text, unsafe warning text, clearing controls
and ignored stale responses. A bootstrap-on/off comparison proves filtered
estimates and accounting are unchanged.

Eight isolated Chrome 155 loopback queries passed on the pinned retrospective
2024 snapshot. The CAR offense comparison at 1000 draws / seed 20261006 exactly
matches frozen uncertainty, overall and comparison blocks. Selected-only, defense,
maximum seed, four-stage filtered and empty-frame cases also pass. The filtered
defense has three plays in one game: bounds are withheld with 130 defined and 70
undefined draws. The filtered offense is empty while its baseline is observed;
before-week-1 performs zero draws. Clearing controls restores frozen measurements.
Invalid text/seed-only requests never fetch. Desktop and 390px mobile layout,
keyboard table scrolling and zero external page requests/errors passed; owned
servers were stopped. These are local integration checks, not browser CI, load,
screen-reader or statistical calibration evidence.

Complete-diff review tightened full-frame, subset and paired support checks,
matched the combined-filter fixture cutoff to its no-bootstrap counterpart, and
kept displayed seeds ungrouped for copyable replay. One test's minus-sign expectation
was corrected to the existing ASCII format; relevant checks reran. No analytics,
API/core, dependencies, source bytes, CI workflow or automation changed. Consult
the published PR for exact SHA, GitHub attribution and remote CI receipts; local
tests alone do not establish remote verification.

**Remaining / next:** download the current validated schema-v2 JSON from the
viewer, preserving all provenance and optional contexts/comparison/uncertainty.
Use a safe cohort filename, no extra request, no stale/loading/error export, and
object-URL cleanup. Test a saved file through the existing offline brief renderer;
do not reimplement it in JavaScript. Broader accessibility/browser CI, calibration,
historical availability and deployment remain open. Inspect this branch's PR and
reviews before continuing; never auto-merge.

## 2026-10-15 — Downloadable report JSON with exact offline replay

**Built / why:** a native download link for the current validated schema-v2 report.
It saves the original decoded API JSON text, including all source/method fields,
filters, comparison and uncertainty, without another request or calculation.
This lets an analyst preserve the exact report they reviewed and use the existing
offline brief renderer rather than a second browser implementation.

Fetched the canonical clone and verified PR #19 merged at `bd7e39d`, with the same
tree as `ed47af0` and all seven merged-main CI jobs successful. The prior checkout
was clean and matched upstream; no open PRs or review feedback remained. Started
`codex/report-json-download` from updated `origin/main`. Baseline 196 core / 22 API /
545 frontend tests passed. No repository, global identity or 8 AM automation
settings were changed. The published PR records exact SHA, attribution and CI.

**Review files:** `web/src/report.ts`, `web/src/ReportDownload.tsx`,
`web/src/App.tsx`, `web/src/download.test.tsx`, `web/src/test-setup.ts` and
`docs/WEB.md#download-and-replay-the-current-report`. The existing Python
`src/opponent_intelligence/brief.py` and its fingerprint contract were reused,
not modified or ported.

**Sports concepts:** a downloaded empty cohort is not a failed request; missing
EPA remains null, not zero. Defense stays offense-relative. All filter ledgers,
separate denominators, paired uncertainty states, support counts and source dates
remain in the export even if the UI summarizes only a subset. Saving a 2024
retrospective report acquired in 2026 cannot establish pregame information
availability, opponent adjustment or predictive validation.

**Software/statistical concepts / what to learn:** parsing and reserializing can
change bytes and Python-decoded number representations (`1.0` versus `1`, negative
zero and integers outside JavaScript's exact range). Keep validated response text
and the parsed view together. A basic-cohort filename is not a full report identity;
filters, seed and source inside the JSON distinguish reports. A native Blob URL
needs an explicit owner/lifetime: reuse it while the link exists, revoke on report
removal, and never pair old bytes with new controls. Browser download intent is
not proof of a saved file. Exact replay tests serialization/integration, not
statistical calibration or source authenticity.

**Three review questions:**

1. Why can `JSON.stringify` change a Python report fingerprint even when the
   rendered measurements look identical, and how does retaining response text help?
2. When is the object URL created, reused and revoked, and what prevents an edited,
   stale, timed-out or failed response from exporting the wrong report?
3. Which fields distinguish two reports with the same suggested filename, and
   what does a byte-exact offline brief replay establish—and not establish?

**Verification / self-review:** 635 frontend tests, a clean locked installation
and type-check/build pass on Node 24.19.0. All 196 core / 22 API tests pass on Python
3.11/3.12/3.13, with API warnings as errors and clean dependency checks. Ninety new
frontend cases cover all 71 unchanged endpoint fixtures plus numeric/Unicode/extra
field preservation, empty/null and error states, stale edits, timeout, repeated
clicks, failed replacement and StrictMode/unmount resource cleanup.

Seven native Chrome 155 downloads across six real-snapshot queries match response
text exactly, with no additional API request: the full frozen comparison,
selected-only uncertainty, both-role four-stage filters, empty pre-week-1 and
cleared options. Every saved file renders offline with identical file/stdin output;
the frozen CAR report reproduces committed Markdown byte-for-byte. Filtered
defense has 3 / 136 selected/baseline plays, offense 0 / 139; these are existing
measurements, not new findings. Keyboard Enter at 390px, desktop/mobile visual
inspection and zero external page requests/errors passed. All 12 StrictMode URLs
were released once; both owned servers were stopped. These are local integration
checks, not browser CI, screen-reader certification or statistical validation.

Review preserved original JSON instead of changing numeric spellings, added a
failed-replacement cleanup test, and clarified non-unique basic filenames and
browser-controlled saving. Relevant checks reran. No API/core calculations,
dependencies, raw bytes, CI workflow or automation changed. Local verification
does not itself claim remote publication or successful CI; consult the PR receipt.
One full-suite attempt timed out after simultaneous roughly 53-second stalls in
seven workers, including unchanged tests. The identical 635-test suite then passed
in 11.46 seconds and the build passed; no timeout or assertion was relaxed. The
underlying execution-stall cause was not established; check independent CI too.

**Remaining / next:** a repeatable CI browser smoke flow using a clearly labeled
synthetic immutable snapshot and the actual API/viewer. Check build/edit/error/
download, saved-file brief replay and targeted keyboard/mobile behavior, block
unexpected external requests and stop owned servers. Broader accessibility review
remains open; no database is justified by the current single-snapshot flow.
Calibration, historical availability and deployment remain unverified. Inspect
this branch's PR and reviews first; do not merge automatically.

## 2026-10-15 — Scout browser CI and Decision Intelligence direction (manual run)

**Built / why:** a repeatable browser integration suite for existing Scout, over
the real FastAPI app and an explicitly synthetic immutable snapshot. Desktop and
narrow Chromium exercise both-role filtered reports, comparison/withheld intervals,
native JSON downloads and the existing offline brief renderer. This closes the
browser-CI unit without duplicating analytics or starting a premature decision UI.

The roadmap now preserves Scout and plans Play Caller / Decision Lab through
P1.5–P1.9; former operational/case-study work remains P1.10. The architecture record
defines separate PBP/charting/tracking/model layers, an initial primary-source
nfl4th/fastrmodels/participation/FTN/Big Data Bowl review, validation/licensing gates
and a no-database decision for the current access pattern. No model or enrichment
is integrated. No automation, source history or production calculations changed.

Synced the stable clone; PR #20 was merged at `b0fc74f`, tree-equivalent to
`3d53724`, with seven green merged-main CI jobs. No open PRs/reviews or unpublished
work remained. Created `codex/scout-browser-ci` from updated `origin/main`.
The published PR is the receipt for exact SHA, attribution and remote CI.

**Review files:** `web/playwright.config.ts`, `web/e2e/scout.spec.ts`,
`tests_api/browser_server.py`, `tests_api/test_browser_server.py`,
`web/config.test.ts`, `.github/workflows/ci.yml`, `docs/WEB.md`,
`docs/DECISION_INTELLIGENCE.md`, `ROADMAP.md` and `AGENTS.md`.

**Sports concepts:** CAR offense and ATL defense describe the same invented
three-play cohort, with offense-relative EPA. EPA/success use two observed values,
not all three plays. One game cannot support a displayed bootstrap interval.
Historical call frequency/outcome association is not causal call quality; a
dropback includes sacks/scrambles, not just raw pass-type rows. Source/model
release dates and decision-time inputs matter independently of week filtering.

**Software/statistical concepts / what to learn:** component tests and live-browser
integration catch different failures. Reuse the verified snapshot adapter, report
builder and renderer; mock delivery timing only to check stale-response handling.
Server/resource ownership must survive cancellation. A temporary directory around
`uvicorn.run()` alone is insufficient when the server replays SIGTERM after
shutdown; cleanup belongs in the application lifespan before that signal. Pre-owned
ports must fail closed, not be reused or killed. Mature model reuse still requires
feature/runtime parity and temporal validation; state EP/WP is not an action-value
model, and realized pass information must not leak into pre-play inputs.

**Three review questions:**

1. What does byte-identical API-to-download-to-brief replay verify, and why does
   it not establish real-world statistical calibration or causal optimality?
2. Why did the first server harness leave temporary snapshots after SIGTERM,
   and how do the lifespan and occupied-port checks prevent unsafe cleanup/reuse?
3. Why can't a current nfl4th/fastrmodels artifact or an FTN charting field simply
   be attached to a historical pre-play decision query without additional audits?

**Verification / self-review:** 196 core / 24 API tests on each of Python
3.11/3.12/3.13, API warnings as errors, clean pip checks, 636 frontend tests, clean
locked npm install and type-check/build pass. Eight browser scenarios pass on
desktop/narrow Chromium, also repeated twice (16 executions), no retries. Live
occupied-port checks preserve the existing owner and verify owned listeners and
temporary snapshots are cleaned up. All 71 existing browser-contract fixtures and
production report outputs are unchanged; no real raw data is needed for browser CI.

Initial harness failures exposed incorrect imports/keyword arguments and a select
locator mismatch; fixed them rather than changing production behavior. The cleanup
probe then caught the Uvicorn signal-replay issue above; added lifespan-order tests
and reran integration. Review also enforced separate Vitest/Playwright discovery,
type-checking of browser tests, bounded single-worker execution, outbound guards
and explicit distinction between local checks and remote CI. No full WCAG audit,
cross-browser certification, model output validation, enriched joins or benchmark
is claimed. CI failure artifacts contain synthetic data only.

**Remaining / next:** the bounded Scout accessibility review is P1.4's last
surface item. Then specify/test the first small offline P1.5 Run vs Pass contract;
do not combine it with API/UI/models. Preserve the same repository and Scout
contracts. Inspect this PR's CI/reviews before new work; do not merge or enable
auto-merge. The existing 8 AM schedule and automation configuration are unchanged.

## 2026-10-16 — Bounded Scout accessibility and error recovery

**Built / why:** completed P1.4's last bounded local-surface unit. Invalid queries
now identify and focus the relevant controls, retain their instructions and describe
the error programmatically. Required controls/formats are explicit, input borders
have stronger contrast, and browser coverage now includes state-by-state scans,
full keyboard order/correction, disclosures, table access and 320px reflow. This
makes the existing evidence easier to reach without changing football calculations.

Synced the stable clone; PR #21 was merged at `91129ea`, tree-equivalent to
`491a503`, with all eight main CI jobs green and no open PR/review feedback.
Created `codex/scout-accessibility` from updated `origin/main`, preserving history.
The published PR provides the exact SHA, attribution and remote-CI receipt.

**Review files:** `web/src/report.ts` (`QueryValidationError`), `web/src/App.tsx`
(field descriptions and validation-only focus), `web/src/styles.css`,
`web/src/report.test.ts`, `web/src/App.test.tsx`, `web/e2e/scout.spec.ts`,
`web/package-lock.json` and `docs/ACCESSIBILITY.md`.

**Sports concepts:** seconds remaining need an explicit period; a valid clock value
is not the invalid field when the period is missing. Small/empty samples, missing
EPA and withheld one-game intervals remain visible, not zero-filled or hidden.
Offense/defense meaning, matched baselines, denominators and provenance are unchanged.

**Software/statistical concepts / what to learn:** preserve typed field identity
at the validation boundary instead of guessing from error-message text. Link an
error to a control without deleting its existing help. Only a synchronous rejected
submission should move focus; a late request must not interrupt navigation.
Automatic accessibility tools miss some keyboard and non-text-contrast problems.
Zero detected violations is not a conformance claim, just as a green regression
suite is not statistical calibration. Keep synthetic testing distinct from real
observations and actual assistive-technology testing distinct from DOM assertions.

**Three review questions:**

1. Why does a missing period invalidate the period control, rather than valid
   seconds, and how are inverted minimum/maximum relationships represented?
2. Why can local validation move focus while an asynchronous API failure should
   not, and how do repeated submission and edit tests guard that distinction?
3. What can axe, keyboard regressions and 320px screenshots demonstrate—and what
   screen-reader, zoom, cross-browser and statistical claims can they not support?

**Verification / self-review:** 196 core / 24 API tests on Python 3.11/3.12/3.13,
API warnings as errors, clean pip checks, 672 frontend tests, clean locked npm
installation and type-check/build pass. Fourteen browser cases pass without retries;
14 full-page axe scans report no automatic violations. All 71 generated API fixtures
are unchanged. Owned test servers stop; ports 8000/5173 are free afterward.

The pre-fix keyboard regression failed while the initial automated scan passed.
Fixed field association/focus, and independently measured input-border contrast
from 2.20:1 to 3.72:1 against white. Complete-diff review checked all validation
branches and unchanged accepted queries, range relationships, retained help,
repeated errors, asynchronous focus, stale results and sanitized API messages.
Scan `incomplete` findings were inspected and retained: a decorative arrow and
short/clipped table cells, not a clean bill of health. Expanded desktop scans and
visual narrow screenshots support the bounded review; no actual screen reader ran.
The unmodified MPL-2.0 checker is pinned/dev-only, not a runtime or data dependency.
The first baseline frontend attempt hit worker-start/test timeouts; bounded-worker
baseline and the final default-worker run passed without relaxing test timeouts.

**Remaining / next:** P1.4 is complete within its documented local scope. Actual
assistive technology, real devices, cross-browser, zoom and high-contrast settings
remain release-readiness gaps. After PR review, begin only the small offline P1.5
Run vs Pass contract and semantics tests; no decision UI/API/model or duplicate
analytics. Do not merge or enable auto-merge. The 8 AM automation is unchanged.

## 2026-10-17 — First offline Run/Pass evidence contract (P1.5)

**Built / why it matters:** after observing PR #22 merged and all eight main CI
jobs green, started `codex/run-pass-decision-contract` from `origin/main` at
`0c3c4a3`. Added a frozen offense-only request and executable offline contract for
exact down/inclusive distance, optional pre-play context, observed Run/Pass
frequencies/outcomes, counts, missing states and provenance. Extracted the existing
cohort/metric primitives for reuse by both Scout and decision evidence. This gives
the future Decision Lab a testable foundation without duplicating analytics or
claiming the larger mean is the correct call.

**Review these files:** `src/opponent_intelligence/decision.py` (request, candidate
mapping, states, abstention), `cohort.py` (shared validation/selection/ledger),
`metrics.py` and `report.py` (one set of formulas, unchanged Scout output),
`tests/test_decision.py` (independent synthetic expectations), and
`docs/DECISION_CONTRACT.md` (replay, semantics, source audit, limits).

**Sports concepts:** sacks and scrambles are dropbacks even when raw play type is
run; the Run label means remaining eligible non-dropbacks, not verified huddle
intent. Exact 3rd-and-4 is not a whole medium-distance bucket. EPA/success retain
offense perspective. Fourth-down Run/Pass frequency is conditional on eligible
plays, not all go/punt/kick choices. RPO/aborted-play intent remains unobserved.

**Software / statistical concepts:** share a pure selector and summarizer rather
than filter and relabel a Dataset's original provenance; separate validation,
mathematical availability, count warnings and decision validity. Preserve null
versus zero, candidate-specific EPA denominators, distinct-game counts, ordered
missingness and exclusive cutoffs. No hidden cohort widening, baseline fallback,
file/network IO, new dependency or frontend formula.

**Learn from this:** manually reproduce the invented first-and-ten example (Run
1 play, Pass 2; frequencies 1/3 and 2/3; EPA 0 and 0.6) and explain why neither
frequency nor outcome difference proves a counterfactual or coaching recommendation.
Learn how to extend a validated system without breaking its existing consumers.

**Three review questions:**

1. Why is a scramble-shaped run in the Pass candidate, and what can the retained
   dropback flag not establish about intended calls, RPOs or aborted plays?
2. When is an unobserved Run frequency zero versus null, and why do missing EPA
   values affect outcome denominators without removing frequency observations?
3. Why does the contract still return no preferred call after its count warnings
   clear, and what matching, uncertainty and validation work remains before ranking?

**Verification / self-review:** 218 core / 24 API tests pass on Python
3.11/3.12/3.13, API warnings as errors, with clean dependency checks; 672 frontend
tests, type-check/build and 14 browser cases pass. The 71 committed API fixtures
are unchanged. All 22 added tests use invented situations, not purported real-team
results. Baseline 196 core / 24 API / 672 frontend tests passed before changes.
The initial browser invocation was blocked at launch by macOS sandbox IPC; the
approved rerun passed with no relaxed assertions, timeouts or retries. Owned
loopback servers stop afterward. No new dependencies or data were acquired.

Complete-diff review checked shared formulas/bounds, ingestion accounting, exact
selection, source copying, cutoff leakage, candidate partitions, null states,
role interpretation and unsupported options. Corrected the documentation's
snapshot-loader module reference. Pinned primary field definitions and existing
PBP attribution support observed categories only; no intended-call classifier or
model validation was invented. No unsafe dataset substitution or statistical
threshold masquerading as decision reliability was introduced.

**Remaining / next:** add exact-match same-role leave-team-out candidate league
baselines/differences with coverage and missing-cell semantics. Then add candidate
support/uncertainty and independently reconcile pinned real cohorts; keep ranking
withheld. P1.5 is not complete. No decision API/UI/model, storage, deployment or
enrichment in this unit. Review the PR; do not merge or enable auto-merge. The
existing 8 AM daily automation is unchanged.

## 2026-10-18 — Matched Run/Pass league baselines (P1.5)

**Built / why it matters:** after observing PR #23 merged at `5010cd7` with all
eight main CI jobs green and no open PR/review feedback, started
`codex/decision-league-baselines` from updated `origin/main`. Added opt-in
leave-offense-out Run/Pass baselines to the offline contract. Both populations use
the same exact down, inclusive distance, optional contexts and temporal window.
Pooled metrics, explicit differences, coverage and missingness give descriptive
team evidence a traceable comparison without inventing a preferred call.

**Review these files:** `src/opponent_intelligence/decision.py` (shared candidate
evidence, baseline selection/coverage/ledgers), `metrics.py` and `report.py`
(one null-aware difference formula), `tests/test_decision_league.py` (independent
synthetic calculations), and `docs/DECISION_CONTRACT.md` (replay and semantics).

**Sports concepts:** exclude the selected offense, not its opponents or whole
games; an opposing offense's plays against that franchise can remain. Sacks and
scrambles stay in Pass. Both groups use offense-relative EPA/score/field context.
A 3rd-and-4 baseline is not a medium-distance bucket; broader requested ranges can
still have unequal situation mixes. Available teams are not certified full-league
coverage, and descriptive differences are not opponent-strength adjustment.

**Software / statistical concepts:** reuse the same selector, summarizer and
difference arithmetic. Pooled EPA weights observed plays, not teams equally:
invented ATL Pass EPA `[1, -1, missing]` and NO `[3]` yield 1, not 1.5. The missing
play still contributes to frequency. Percentage-point differences are not percent
changes. Play-disjoint populations can share games; candidate game totals overlap
and do not certify independent observations. Keep full-source provenance separate
from each population's ordered, conditional exclusion ledger.

**Learn from this:** reproduce the synthetic example by hand, then trace its
denominators and nulls through the builder and tests. Explain why a zero observed
frequency is meaningful in a nonempty cohort while absent EPA is unavailable,
and why neither matched filters nor a positive difference establishes a winner.

**Three review questions:**

1. Why does pooled Pass EPA equal 1 rather than 1.5 in the example, and which
   denominator still includes the missing-EPA play?
2. Which offensive plays are excluded from the baseline, when can games overlap,
   and why must candidate game counts not be summed as independent samples?
3. When is a frequency difference defined while an outcome difference is null,
   and why do exact matching and cleared count warnings still not justify ranking?

**Verification / self-review:** 238 core / 24 API tests pass on each of Python
3.11/3.12/3.13, API warnings as errors, with clean pip checks; 672 frontend tests,
type-check/build and 14 browser cases pass. All 71 API-produced fixtures are
unchanged. Baseline 218 core / 24 API / 672 frontend tests passed before changes.
The 20 new tests use explicitly invented rows; no real-team results or validation
are claimed. Browser process IPC required approved outside-sandbox execution;
no retries, assertion changes or timeout increases. Owned test servers stop and
ports 8000/5173 are free. No dependencies or raw datasets were acquired.

Complete-diff review checked cutoff/role isolation, no bucket fallback, candidate
partitions, source accounting, conditional missingness, pooled denominators, shared
games, signed units, null propagation and unchanged Scout outputs. Added explicit
inclusive-distance and OT/clock-zero tests during review. Documented unequal
within-range mixes and retained capability abstention even above count-warning
thresholds. Primary field definitions were rechecked against the pinned dictionary;
no new source/model/license assumptions were introduced. The published PR records
the exact commit, attribution and remote-CI receipt separately from local checks.

**Remaining / next:** candidate-level per-metric game support and exploratory
paired whole-game uncertainty using existing resampling with shared-game weights.
Keep interval-withholding and ranking separate; independent pinned real-cohort
reconciliation and a justified comparison policy still remain. P1.5 is not complete;
no decision API/UI/model, enrichment, storage or deployment in this unit. Review
the PR; do not merge or enable auto-merge. The 8 AM automation is unchanged.

## 2026-10-19 — Candidate-level game support and exploratory uncertainty (P1.5)

**Built / why:** after PR #24 merged at `6246a3b` (same tree as `c06c7fa`) and all
eight main CI jobs passed, started `codex/decision-candidate-uncertainty` from
updated `origin/main`. Added optional seeded whole-game intervals and per-metric
support for Run/Pass and matching league differences. Extracted the existing
resampling loop for both Scout and decision adapters rather than building another
bootstrap. This makes sparse evidence visible without pretending to select a call.

**Review files:** `src/opponent_intelligence/uncertainty.py` (shared draws,
candidate frequency denominator, support and withholding), `decision.py` (bounded
opt-in, reused filtered baseline), `tests/test_decision_uncertainty.py` (independent
expanded-play oracle), and `docs/DECISION_CONTRACT.md` / `docs/UNCERTAINTY.md`.

**Sports concepts:** games contribute different numbers of calls; pooled metrics
are not game averages. A game with no Run still informs Run frequency. Missing EPA
does not erase a call, but cannot support its EPA/success estimate. Both calls and
opposing offenses can share game effects; repeated opponents across different games
remain dependent. Sacks/scrambles stay in Pass and defense EPA stays offense-relative.

**Software/statistical concepts / learn:** distinguish three counts: candidate
games, parent games for frequency support, and candidate observed-EPA games for
outcome support. Sample one shared game frame, retain multiplicities for both
calls/populations, and calculate differences within each draw. Never subtract
marginal interval endpoints, redraw missing denominators or equate a constant
bootstrap with certainty. Reuse the existing method/metadata and keep contracts
separate; 200–10000 draws bound this offline option, not a new API. Five-game and
95%-valid gates are safeguards, not reliability or decision thresholds.

**Three review questions:**

1. If Run occurs in only one of five matching games, why can its frequency have
   five support games while its EPA has at most one, and what if that EPA is missing?
2. Why must selected/league and Run/Pass share game draws, and why can a paired
   EPA difference be constant even when both marginal intervals vary?
3. What distinguishes undefined, insufficient-game, too-few-valid and degenerate
   intervals, and why does even an available interval not justify ranking calls?

**Verification / self-review:** 254 core / 24 API tests pass on each Python
3.11/3.12/3.13 with API warnings as errors and clean pip checks; 672 frontend tests
and type-check/build pass. The 16 new tests include all 3,125 ordered five-game
draws, separate quantiles, support asymmetry, zero/missing/empty cases, exact 95%
boundaries, no redraw/opt-out sampling, fixed cutoffs, RNG/row-order stability and
Scout defense compatibility. All 71 API-produced fixtures are unchanged; six Scout
uncertainty cases match main byte-for-byte, including key order. Baseline 238 core /
24 API tests passed before implementation. Synthetic doc replay confirms low-support
interval withholding. No raw datasets, dependencies or models were acquired.

Browser run one passed 13/14 cases but a narrow accessibility evaluation took about
94 seconds and exceeded the existing 60-second test limit. Its emitted scans had
no automatic violations; cause remains unconfirmed. Retained its synthetic trace
locally as recorded in STATUS. The unchanged full rerun passed all 14 in 15.5 seconds;
no timeouts/assertions/retry settings were loosened. Owned listeners stopped.

Complete-diff review checked denominator/null semantics, shared frames, support
precedence, paired units, temporal isolation, source accounting and unchanged
Scout serialization. Added asymmetric-support and baseline-only-draw tests and
clarified the inherited population-pairing flag; removed stale architecture
next-step text. Rechecked primary cluster-bootstrap and
paired-sampling references without copying code or claiming NFL calibration.
The published PR records actual SHA, attribution and remote CI separately.

**Remaining / next:** independently reconcile pinned retrospective candidate
points, baselines, support and seeded intervals from raw source rows. Then document
the remaining abstention/opponent-evidence policy. Keep ranking withheld; P1.5 is
not yet complete. No decision API/UI/model, enrichment, database or deployment.
Review the PR without merging or auto-merge. The 8 AM automation is unchanged.
