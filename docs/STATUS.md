# Engineering status

As of 2026-09-29, the CSV-to-JSON measurement foundation and explicit play-type
validation are implemented. All 25 offline tests pass on Python 3.11.9, 3.12.7,
and 3.13.2. The demo uses only synthetic data. No real football findings,
predictive model, web interface, or production deployment exist.

## Canonical repository and migration

- Remote: https://github.com/AryanParte/nfl-opponent-intelligence
- Stable clone: `/Users/aryanparte/Documents/nfl-opponent-intelligence`
- Working branch: `codex/validate-play-types`, started from updated `origin/main`
  at `fac284b` after observing the migration PR was merged.
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
dropbacks, five observed EPA values, 0.04 EPA/play, and 0.6 success rate, unchanged
by this fix. The seven added test methods cover unknown labels, exclusion order,
documented non-run/pass labels, missing-type counts, identity checks, unchanged
cohort metrics, and CLI failure with no partial output. The new regression tests
failed against the original loader before implementation.

The offline suite also passed using `python3.11` and `python3.12`. CI is configured
for Python 3.11/3.12/3.13. At the start of this run GitHub's Actions API returned
zero runs, even though repository Actions are enabled and all actions are allowed.
Remote CI has not yet been verified; do not infer remote success from local tests.

## Current data contract

Only the nine documented nflverse play-type labels are recognized. Unknown labels
fail with a line number and value, including on otherwise excluded rows. Missing
markers remain accepted and are counted separately under `missing_play_type`.
Identity checks still precede exclusions. Named categories remain case-sensitive;
the adapter does not silently repair typos or infer categories from other fields.
See docs/DATA_CONTRACT.md for the exact policy and source references.

## Follow-up

Continue P1.2 in ROADMAP.md: verify the completed 2024 nflverse release and its
dataset terms, then implement immutable ingestion with source manifests and
offline fetcher tests. Audit actual schemas, missingness, categories, and exclusions
before claiming real-season compatibility. Keep the zero-network synthetic demo.

The host's `/usr/bin/git` Xcode shim fails. The installed
`/Library/Developer/CommandLineTools/usr/bin/git` works. An unrelated ancestor Git
repository exists, so always verify the project root before staging anything.
