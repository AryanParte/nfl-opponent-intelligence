# Input contract and provenance

The analytical adapter accepts an uncompressed UTF-8 CSV, or an explicit verified
2024 [raw snapshot directory](INGESTION.md) containing gzip CSV and its manifest.
A UTF-8 BOM is accepted. Analytical parsing still reads decoded CSV into memory;
snapshot expansion is capped at 256 MiB, but memory use exceeds decoded size.
Streaming larger datasets is future work, not a scale claim.

The source SHA-256 is computed from exactly the bytes parsed. Source labels are
required at the command line. Labels are supplied by the caller, not certified
provenance. Snapshot reports add `source.snapshot`, retaining the acquisition
manifest with source URLs, IDs, timestamps, attribution, and archive/decoded
fingerprints. `source.sha256` means decoded CSV bytes (including any BOM), not gzip
bytes; it matches `source.snapshot.decoded_csv.sha256`. Manual `--csv` reports keep
their original source block and do not claim verified acquisition provenance.
Both input paths now emit [report schema v2](METRICS.md#report-schema-v2), with
explicit team/side and offense-relative metric context; the manifest schema is unchanged.

`--snapshot` is mutually exclusive with `--csv`, never downloads, and never follows
`current.json`. It verifies the stored archive/manifest, then rechecks the decoded
bytes actually parsed to detect changes between reads. Every snapshot row's season,
including excluded rows, must match its manifest. The requested report season must
also match. Empty cohorts remain valid. The copied manifest describes the unchanged
raw archive; report metrics and audit summaries are derived work, not raw data.

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

Required headers must exist even if every row is excluded. Recognized optional
columns are validated as described below; other additional columns are ignored.
Duplicate headers and wrong-width rows fail. Integral
numeric strings like `1.0` are accepted. Row validation errors include CSV line
numbers, and malformed rows are never silently dropped.

Every row must have an identity. Recognized non-run/pass and missing-type rows may
have blank down, team, EPA, and other fields; those are not parsed after exclusion.
Two-point attempts are excluded before validating down, which is often missing
for conversions. Raw source exclusion counts and the number outside the requested
cohort remain in the report; an individual row has exactly one exclusion reason.

## Optional field position

`yardline_100` is recognized as of 2026-10-02. It is the offense's pre-play distance
in yards to the opposing goal line, not yards gained or an end-of-play location.
The [nflreadr dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv)
defines its possession-relative direction; nflfastR's
[starting-position example](https://nflfastr.com/articles/nflfastR.html) uses 80 for
an offense at its own 20. The parser accepts finite numbers in **0..100 inclusive**,
including fractional yards. These are explicit adapter bounds, not a claim that
every boundary occurs in the recorded data. Blank/NA/NaN/null mean missing, not zero.

The header may be absent for backward-compatible unfiltered reports. If present,
malformed or out-of-range values on eligible rows fail with CSV line context even
when the row is outside the requested team/week. Already-excluded rows do not need
valid field-position values, matching the down/EPA validation precedence.

`Play.yardline_100` defaults to `None`. `Dataset.optional_columns` records recognized
headers, including on empty inputs, so an absent field is distinct from a present
field with all values missing. Direct typed-dataset callers must populate this
metadata when supplying the field. Requested range filters require the column;
an absent column fails instead of presenting an unavailable result as an empty one.
No source data is imputed, and the original synthetic fixture is unchanged.

## Optional pre-play score

`score_differential` is recognized as of 2026-10-03. It is possession-team points
minus defensive-team points **at the start of the play**, as confirmed by the
[dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv)
and [nflfastR construction](https://github.com/nflverse/nflfastR/blob/master/R/helper_add_nflscrapr_mutations.R)
reviewed that day. Negative means the offense trails, zero means tied, and positive
means the offense leads, for both report roles. `score_differential_post` describes
the end of the play and is ignored, never a fallback for absent/missing pre-play
context. The adapter does not reconstruct scores from outcomes.

Observed values must be signed whole points in ASCII decimal notation (`-7`,
`+7`, `0`, and `-7.00` are accepted). Fractions, scientific notation, separators,
infinities, and other malformed values fail. Parsing does not pass through float,
so tiny fractions cannot round to whole points and large integers retain precision.
No football score cap is inferred from this snapshot's observed range; Python's
integer-string safety limit still applies. Blank/NA/NaN/null remain missing, not
ties. `Play.score_differential` is an integer or `None`.

Like field position, the header is optional without its filter, but a requested
score filter requires it even if other filters leave no plays. Present values are
validated on every eligible row, including rows outside the requested cohort;
already-excluded rows do not need valid score context. `Dataset.optional_columns`
retains availability even with no rows. Raw/eligible audit missingness automatically
includes this recognized column when present. Valid reports without a score filter
are unchanged; malformed values in this newly recognized field now fail instead
of being ignored. See [score filtering](METRICS.md#pre-play-score-ranges).

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
this contract. The recorded 2024 snapshot passed without relaxing this policy.

## Snapshot audit

`python -m opponent_intelligence.audit --snapshot DIRECTORY` verifies bytes and
parses through the same strict adapter, then independently enumerates raw eligible
identities and checks exact set equality and row accounting. It counts missing
markers across all required columns before exclusions, and records types and
observed games/rows per week. The audit additionally validates REG/POST and week
on every row and rejects conflicting game contexts, even on excluded rows.
These are explicit audit checks; ordinary reporting does not run the whole audit.
Audit schema v1 now also includes `input.optional_column_missing_counts` (all raw
rows) and `adapter.optional_column_missing_counts` (eligible plays). Only recognized
headers actually present appear in these maps; `{}` means absent, not zero missing
values. Required-field counts and source provenance retain their existing meanings.

Duplicate keys, malformed inputs, and audit disagreements fail the entire command
with no partial JSON. Zero duplicate keys in a successful audit means validation
passed, not that duplicates were silently removed. A header-only snapshot can
produce an empty audit; coverage is reported, not assumed complete.

## Fixture provenance

`tests/fixtures/synthetic_pbp.csv` was authored for this project's tests on
2026-09-28. All 14 rows are synthetic, including the game IDs and EPA values. It
contains a negative-EPA sack-shaped row, a run-shaped scramble, kneel/spike and
conversion flags, a no-play row, missing and zero EPA, another offense, a target
week, playoffs, and another season. None is a downloaded game observation.

## Source references and verification scope

- [nflreadr play-by-play dictionary](https://nflreadr.nflverse.com/articles/dictionary_pbp.html)
- [nflfastR beginner guide](https://nflfastr.com/articles/beginners_guide.html)
- [nflfastR field construction](https://github.com/nflverse/nflfastR/blob/master/R/helper_add_nflscrapr_mutations.R)
- [nflreadr release loader](https://github.com/nflverse/nflreadr/blob/main/R/load_pbp.R)
- [nflverse data releases](https://github.com/nflverse/nflverse-data/releases)

These primary sources informed the field contract. The 2024 release and data terms
have been reviewed, and the recorded immutable snapshot passes the analytical
adapter and cohort reconciliation (see [REAL_DATA_AUDIT.md](REAL_DATA_AUDIT.md)).
That evidence does not certify every extra field, prove externally complete game
coverage, or validate upstream EPA training. Audit new snapshots before using
their findings. A source package's code license does not itself grant all rights
to redistribute its underlying data.
