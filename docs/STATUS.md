# Engineering status

As of 2026-09-28, the CSV-to-JSON measurement foundation is implemented and its 18
offline tests pass on Python 3.11.4. The demo uses only synthetic data. No real
football findings, predictive model, web interface, or production deployment exist.

## Immediate priority

Aryan requested migration before further feature development: preserve the current
work, publish `AryanParte/nfl-opponent-intelligence`, use the stable clone at
`/Users/aryanparte/Documents/nfl-opponent-intelligence`, and update daily runs to
sync and push. The original task directory is not the intended future workspace.
No earlier commits existed before the foundation snapshot.

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

After verifying migration, reject unrecognized play types explicitly instead of
silently treating them as supported exclusions. Then continue P1.2 in ROADMAP.md:
immutable real-season ingestion with source manifests and offline fetcher tests.

The host's `/usr/bin/git` Xcode shim fails. The installed
`/Library/Developer/CommandLineTools/usr/bin/git` works. An unrelated ancestor Git
repository exists, so always verify the project root before staging anything.
