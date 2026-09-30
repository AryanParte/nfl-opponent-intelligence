# Engineering status

As of the additional manual run on 2026-09-29, the measurement foundation,
explicit play-type validation, and immutable raw acquisition are implemented.
All 44 offline tests pass on Python 3.11/3.12/3.13. A real 2024 raw artifact has
been downloaded and byte-verified, but analytical reports still use synthetic
data. No validated real-season football findings, predictive model, web interface,
or production deployment exist.

## Canonical repository and migration

- Remote: https://github.com/AryanParte/nfl-opponent-intelligence
- Stable clone: `/Users/aryanparte/Documents/nfl-opponent-intelligence`
- Working branch: `codex/immutable-pbp-snapshots`, started from updated `origin/main`
  at `635ee9a` after observing PR #2 was merged.
- Previous review: [PR #2](https://github.com/AryanParte/nfl-opponent-intelligence/pull/2),
  merged on 2026-09-29. Continue the current branch/PR if still unmerged.
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
This additional manual run did not modify, duplicate, disable, or reschedule it.

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
existing pipeline tests remain intact. Nineteen new acquisition tests cover source
metadata, hashes, retries, interrupted bodies, byte limits, gzip errors, cache
corruption, revision retention, atomic publication failures, and CLI behavior.
Network is blocked in acquisition tests, including their CLI subprocess.

The last verified CI before this unit is the
[PR #2 final-head run](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/36566743986).
Automatic triggering did not run for that PR; manual workflow dispatch succeeded.
The new branch's CI must be checked separately after publication. No automation,
repository settings, or workflow code were changed during this manual run.

## Raw acquisition evidence

`PYTHONPATH=src python3 -m opponent_intelligence.fetch --season 2024` downloaded
the real archive, matched GitHub's published digest, and recorded an immutable
manifest. The 19,362,351-byte compressed artifact decodes to 99,483,794 bytes;
the decoded hash also matches the separately published CSV asset. Offline reuse
with the network blocked passed and preserved the original manifest.

See [INGESTION.md](INGESTION.md) and the
[committed manifest](evidence/pbp-2024-23370d5d10f8.manifest.json) for IDs, hashes,
retrieval/update times, source terms, limits, and replay instructions. Raw data
remains ignored by Git. The fetcher currently supports only 2024 and validates
bytes/gzip integrity, not analytical CSV semantics. It does not automatically
propagate provenance into the existing reporting CLI.

## Current data contract

Only the nine documented nflverse play-type labels are recognized. Unknown labels
fail with a line number and value, including on otherwise excluded rows. Missing
markers remain accepted and are counted separately under `missing_play_type`.
Identity checks still precede exclusions. Named categories remain case-sensitive;
the adapter does not silently repair typos or infer categories from other fields.
See docs/DATA_CONTRACT.md for the exact policy and source references.

## Follow-up

Continue P1.2 with the exact acquired snapshot: add gzip-aware analytical loading
or an auditable extraction adapter; audit schemas, seasons/games/weeks, duplicate
identities, missingness, categories, and exclusions; reconcile selected totals and
metric denominators. Carry the source manifest into reports. Preserve the existing
cohort policy unless actual evidence justifies a documented change, and keep the
synthetic demo network-free. Do not move to UI/predictive work yet.

The host's `/usr/bin/git` Xcode shim fails. The installed
`/Library/Developer/CommandLineTools/usr/bin/git` works. An unrelated ancestor Git
repository exists, so always verify the project root before staging anything.
