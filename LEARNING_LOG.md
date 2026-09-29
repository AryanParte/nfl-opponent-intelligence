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
