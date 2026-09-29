# Input contract and provenance

The first adapter accepts an uncompressed UTF-8 CSV in the nflverse play-by-play
shape. A UTF-8 BOM is accepted. It has no downloader yet. Runtime parsing reads
the file into memory; streaming larger datasets is future work, not a scale claim.

The source SHA-256 is computed from exactly the bytes parsed. Source labels are
required at the command line. Labels are supplied by the caller, not certified
provenance; retrieval/version manifests are the next milestone.

## Required columns

| Fields | Interpretation and validation |
| --- | --- |
| `game_id`, `play_id` | Unique pair across every row; nonempty game ID and integral play ID. Duplicate records fail even if IDs serialize as `1` versus `1.0`. |
| `season`, `season_type`, `week` | NFL season year; REG/POST; nflverse week 1–22. January games belong to the source season, not necessarily their calendar year. |
| `posteam`, `defteam` | Distinct uppercase abbreviations of 2–3 ASCII letters. This validates shape, not the historical franchise identity. |
| `play_type` | A documented lowercase nflverse category or an explicit missing marker; unknown values fail. See the exclusion policy below. |
| `down`, `ydstogo` | Integral down 1–4 and yards to go 0–100; not imputed. |
| `qb_dropback` | Explicit 0/1 indicator; pass rows require 1. A run with 1 is treated as a scramble/dropback. |
| `qb_kneel`, `qb_spike`, `two_point_attempt` | Explicit 0/1 indicators used to exclude special situations. |
| `epa` | Finite numeric value, or blank/NA/NaN/null for missing. No zero imputation. |

Required headers must exist even if every row is excluded. Additional columns are
accepted and ignored. Duplicate headers and wrong-width rows fail. Integral
numeric strings like `1.0` are accepted. Row validation errors include CSV line
numbers, and malformed rows are never silently dropped.

Every row must have an identity. Recognized non-run/pass and missing-type rows may
have blank down, team, EPA, and other fields; those are not parsed after exclusion.
Two-point attempts are excluded before validating down, which is often missing
for conversions. Raw source exclusion counts and the number outside the requested
cohort remain in the report; an individual row has exactly one exclusion reason.

## Play-type validation and exclusion order

The [upstream dictionary](https://nflreadr.nflverse.com/articles/dictionary_pbp.html)
and [field construction](https://github.com/nflverse/nflfastR/blob/master/R/helper_add_nflscrapr_mutations.R)
were checked on 2026-09-29. This is a fixed adapter contract, not a promise to accept
new upstream categories silently. Leading/trailing whitespace is trimmed. Named
categories are case-sensitive: `PASS`, `sack`, and typos are errors, not aliases.

| Input | Loader behavior |
| --- | --- |
| `run`, `pass` | Continue with conversion/kneel/spike flags and eligible-play validation. |
| `punt`, `field_goal`, `kickoff`, `extra_point`, `qb_kneel`, `qb_spike`, `no_play` | Exclude under `non_run_pass`, preserving the existing classification. |
| Blank, `NA`, `NaN`, `null` (missing markers are case-insensitive) | Exclude under `missing_play_type`, not the non-run/pass bucket. |
| Any other value | Fail the entire load with CSV line number and offending value. The CLI exits with status 2 and emits no report. |

Identity/duplicate checks run first, including on excluded rows. Play-type checks
precede situation flags and the report's team/season/week filters; an unknown
category cannot disappear simply because that row would be outside the cohort.
The upstream dictionary permits missing types for end-of-play rows. The adapter
does not infer the cause of missingness or impute a play type from other fields.
Missing-type counts are source-wide and do not add observations to any denominator.

For a `run`/`pass` row, the flag exclusion order remains conversion, kneel, spike.
A `qb_kneel`/`qb_spike` type is already excluded by type, so its flags are not read.
Exclusion-reason keys are data-dependent; consumers should read the returned map
rather than assume a fixed list. Audit a new upstream category before extending
this contract. Real-season compatibility is still a separate validation gate.

## Fixture provenance

`tests/fixtures/synthetic_pbp.csv` was authored for this project's tests on
2026-09-28. All 14 rows are synthetic, including the game IDs and EPA values. It
contains a negative-EPA sack-shaped row, a run-shaped scramble, kneel/spike and
conversion flags, a no-play row, missing and zero EPA, another offense, a target
week, playoffs, and another season. None is a downloaded game observation.

## Source references and next validation gate

- [nflreadr play-by-play dictionary](https://nflreadr.nflverse.com/articles/dictionary_pbp.html)
- [nflfastR beginner guide](https://nflfastr.com/articles/beginners_guide.html)
- [nflfastR field construction](https://github.com/nflverse/nflfastR/blob/master/R/helper_add_nflscrapr_mutations.R)
- [nflreadr release loader](https://github.com/nflverse/nflreadr/blob/main/R/load_pbp.R)
- [nflverse data releases](https://github.com/nflverse/nflverse-data/releases)

These primary sources informed the field contract; compatibility with a complete
real-season release is not yet verified. The next run must inspect actual source
coverage and terms, preserve an immutable snapshot manifest, and explain any
required contract changes. A source package's code license does not itself grant
all rights to redistribute its underlying data.
