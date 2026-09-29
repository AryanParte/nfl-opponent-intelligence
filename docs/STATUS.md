# Engineering status

As of 2026-09-28, the CSV-to-JSON measurement foundation is implemented and its 18
offline tests pass on Python 3.11.4. The demo uses only synthetic data. No real
football findings, predictive model, web interface, or production deployment exist.

## Canonical repository and migration

- Remote: https://github.com/AryanParte/nfl-opponent-intelligence
- Stable clone: `/Users/aryanparte/Documents/nfl-opponent-intelligence`
- Working branch: `codex/opponent-intelligence-foundation`
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
dropbacks, five observed EPA values, 0.04 EPA/play, and 0.6 success rate. CI is
configured for Python 3.11/3.12/3.13 but has not run remotely yet.

## Follow-up

Reject unrecognized play types explicitly instead of silently treating them as
supported exclusions. Then continue P1.2 in ROADMAP.md:
immutable real-season ingestion with source manifests and offline fetcher tests.

The host's `/usr/bin/git` Xcode shim fails. The installed
`/Library/Developer/CommandLineTools/usr/bin/git` works. An unrelated ancestor Git
repository exists, so always verify the project root before staging anything.
