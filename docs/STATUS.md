# Engineering status

As of the scheduled run on 2026-10-01, P1.3's explicit defense-side reports are
implemented. All 75 offline tests pass on Python 3.11/3.12/3.13. `--side defense`
selects the offenses facing a team, with EPA still offense-relative. Report schema
v2 names the selected team/side and metric interpretation; existing default-offense
measurements and source provenance are unchanged. P1.2 remains complete for the
recorded 2024 snapshot. These are retrospective descriptive checks, not model
validation, opponent adjustment, a web interface, or deployment.

## Canonical repository and migration

- Remote: https://github.com/AryanParte/nfl-opponent-intelligence
- Stable clone: `/Users/aryanparte/Documents/nfl-opponent-intelligence`
- Working branch: `codex/defense-cohort-reports`, started from updated `origin/main`
  at `8ed98e6` after observing PR #4 was merged. Continue its PR while unmerged.
- Current review: [PR #5](https://github.com/AryanParte/nfl-opponent-intelligence/pull/5),
  open and unmerged. Implementation `208fb90` is pushed with matching local/remote
  SHAs and confirmed AryanParte author/committer attribution. Do not enable auto-merge.
- Previous analytical integration review:
  [PR #4](https://github.com/AryanParte/nfl-opponent-intelligence/pull/4), merged at
  `8ed98e6`. No open PRs or review feedback remained at this run's start.
- Previous acquisition review: [PR #3](https://github.com/AryanParte/nfl-opponent-intelligence/pull/3),
  merged at `78623c6`.
- Previous review: [PR #2](https://github.com/AryanParte/nfl-opponent-intelligence/pull/2),
  merged on 2026-09-29.
- Migration review: [PR #1](https://github.com/AryanParte/nfl-opponent-intelligence/pull/1),
  merged on 2026-09-29. Inspect current open PRs before selecting new work.
- Preserved foundation commit: `ba72f50700ff77f031e738f64c55217ffd5ad59c`
- Review base: `main`, initially seeded with that exact preserved snapshot.
- Author/committer: `Aryan Parte <134340600+AryanParte@users.noreply.github.com>`;
  GitHub's commit API confirms both are linked to `AryanParte`.

No earlier commits existed. All original project files were captured in the
foundation commit, pushed, and recovered by cloning GitHub into the stable path.
The initial clone matched the original files byte-for-byte excluding Git metadata
and Python caches. Local/remote branch SHAs matched, and all 18 tests passed from
the stable clone. Future work continues here; the old outputs checkout is retired.

The existing `daily-sports-portfolio-engineering` task remains active at 8 AM
America/New_York. Its prompt now requires remote sync, stable-clone recovery,
verified commit identity, one meaningful unit, tests, complete-diff self-review,
updated documents, commit, push, remote-SHA verification, and PR review.
This run did not modify, duplicate, disable, or reschedule it.

## Verification

From the project root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m opponent_intelligence \
  --csv tests/fixtures/synthetic_pbp.csv \
  --source-label 'Synthetic verification fixture; not real NFL observations' \
  --team CAR --season 2024 --before-week 3
```

Both commands passed locally. The fixture yields six cohort plays, three
dropbacks, five observed EPA values, 0.04 EPA/play, and 0.6 success rate. The 25
existing pipeline tests remain intact. Nineteen acquisition tests cover source
metadata, hashes, retries, interrupted bodies, byte limits, gzip errors, cache
corruption, revision retention, atomic publication failures, and CLI behavior.
Network is blocked in acquisition tests, including their CLI subprocess. Seventeen
snapshot integration tests cover verified provenance, corruption/mutation,
season matching, raw/adapter reconciliation, missingness, empty data, CLI errors,
and defense reports retaining manifest schema v1 inside report schema v2. Fourteen
defense tests check independent numerical expectations, multiple opponents, default
offense compatibility, situations, positive/negative/zero/missing EPA, cutoffs,
empty cohorts, reciprocal selections, count partitions, and API/CLI validation.
No real dataset is required by the test suite.

The new synthetic defense command in README.md also passes: five plays, three
dropbacks, four observed EPA values, 0.05 EPA/play, and 0.75 offensive success
allowed. Self-review corrected reduced typed test fixtures to keep input-row
accounting consistent and documented the breaking report schema change explicitly.

With the existing real snapshot verified and network blocked, 256 reports (32
teams × two sides × four season/cutoff combinations) match independent counters
over the eligible typed records. Both offense and defense partitions sum to zero
plays for REG before week 1, 3,811 for REG before week 3, 33,335 for REG before week
19, and 1,567 for POST before week 23. Every report retains the unchanged manifest.
This is an integration check of role selection, not a new independent raw-data
audit, gamebook check, defensive ranking, or forecast evaluation. Games/rates are
not additive across team partitions.

The [PR #5 implementation run](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/36877565779)
passed on `208fb90`: Python 3.11/3.12/3.13 each succeeded in the offline regression
suite and synthetic demo. No automatic run appeared after push/PR creation, so the
existing workflow was dispatched manually. Final-head verification after this
publication-record update is recorded in the PR description. No workflow code,
repository settings, or daily automation were changed.

## Raw acquisition evidence

`PYTHONPATH=src python3 -m opponent_intelligence.fetch --season 2024` downloaded
the real archive, matched GitHub's published digest, and recorded an immutable
manifest. The 19,362,351-byte compressed artifact decodes to 99,483,794 bytes;
the decoded hash also matches the separately published CSV asset. Offline reuse
with the network blocked passed and preserved the original manifest.

See [INGESTION.md](INGESTION.md) and the
[committed manifest](evidence/pbp-2024-23370d5d10f8.manifest.json) for IDs, hashes,
retrieval/update times, source terms, limits, and replay instructions. Raw data
remains ignored by Git. Acquisition supports only 2024 and validates bytes/gzip
integrity. The new offline `--snapshot` report path separately validates required
analytical fields, checks all row seasons, and includes the source manifest.

See [REAL_DATA_AUDIT.md](REAL_DATA_AUDIT.md) and its committed JSON evidence for
observed coverage, missingness, exact row reconciliation, replay commands, and
four independently cross-checked cohort totals. No contract relaxation was needed.

## Current data contract

Only the nine documented nflverse play-type labels are recognized. Unknown labels
fail with a line number and value, including on otherwise excluded rows. Missing
markers remain accepted and are counted separately under `missing_play_type`.
Identity checks still precede exclusions. Named categories remain case-sensitive;
the adapter does not silently repair typos or infer categories from other fields.
See docs/DATA_CONTRACT.md for the exact policy and source references.

## Follow-up

Continue P1.3 with an optional pre-play field-position filter (`yardline_100`):
verify the definition and missingness, define range boundaries, preserve unfiltered
results, and test both roles and missing-field accounting. Score/time filters and
matched league baselines follow. The current adapter does not yet parse these
context fields. Report JSON consumers must migrate from `cohort.offense` to
`cohort.team`/`cohort.side`; see [METRICS.md](METRICS.md#report-schema-v2).
Do not move to UI/predictive work yet. External schedule/gamebook
reconciliation, historical availability, backup, automatic CI triggering, and
larger-than-memory ingestion remain documented limitations, not completed claims.

The host's `/usr/bin/git` Xcode shim fails. The installed
`/Library/Developer/CommandLineTools/usr/bin/git` works. An unrelated ancestor Git
repository exists, so always verify the project root before staging anything.
