# Engineering status

As of the scheduled run on 2026-09-30, P1.2 acquisition and analytical integration
are complete for the recorded 2024 snapshot. All 60 offline tests pass on Python
3.11/3.12/3.13. The 49,492-row real artifact passes the adapter audit; its 34,902
eligible identities and four selected cohort calculations reconcile. Reports
retain source provenance. These are retrospective descriptive checks, not model
validation, external gamebook reconciliation, a web interface, or deployment.

## Canonical repository and migration

- Remote: https://github.com/AryanParte/nfl-opponent-intelligence
- Stable clone: `/Users/aryanparte/Documents/nfl-opponent-intelligence`
- Working branch: `codex/audit-real-pbp-snapshot`, started from updated `origin/main`
  at `78623c6` after observing PR #3 was merged. Continue its PR while unmerged.
- Previous acquisition review: [PR #3](https://github.com/AryanParte/nfl-opponent-intelligence/pull/3),
  merged at `78623c6`. No open PRs or review feedback remained at this run's start.
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
Network is blocked in acquisition tests, including their CLI subprocess. Sixteen
new snapshot integration tests cover verified provenance, corruption/mutation,
season matching, raw/adapter reconciliation, missingness, empty data, and CLI
errors. No real dataset is required by the test suite.

The last observed CI before this unit is the successful
[PR #3 final-head run](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/36651429362)
on `75e67f7`. Earlier pushes needed manual dispatch because no automatic run
appeared. This branch needs its own remote CI after publication; local success is
not remote evidence. No workflow code or repository settings were changed.

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

Begin P1.3 with an explicit opponent-defense cohort view: preserve offense-perspective
EPA, identify the side selected, keep exclusive week cutoffs and denominator audits,
and test reciprocal offense/defense selections. Context filters and matched league
baselines follow. Do not move to UI/predictive work yet. External schedule/gamebook
reconciliation, historical availability, backup, automatic CI triggering, and
larger-than-memory ingestion remain documented limitations, not completed claims.

The host's `/usr/bin/git` Xcode shim fails. The installed
`/Library/Developer/CommandLineTools/usr/bin/git` works. An unrelated ancestor Git
repository exists, so always verify the project root before staging anything.
