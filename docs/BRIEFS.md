# Historical opponent briefs

The brief is a deterministic presentation of this project's report schema v2,
not another analytical pipeline. It accepts a saved UTF-8 JSON file or stdin,
validates the fields it uses, and prints GitHub-flavored Markdown. No package
installation, raw dataset, network, new bootstrap draw, or current timestamp is
needed for rendering. Existing report generation and JSON defaults are unchanged.

## Run and review

```sh
PYTHONPATH=src python3 -m opponent_intelligence.brief \
  --report docs/examples/synthetic.report.json

PYTHONPATH=src python3 -m opponent_intelligence.brief \
  --report docs/examples/car-2024-reg-before-week-19.report.json
```

Use `--report -` to read stdin. Redirect stdout to a **new** file if desired; the
renderer itself does not create or overwrite files. The Python API is
`opponent_intelligence.brief.render_brief(report) -> str`. It does not mutate its
argument and returns one trailing newline. Errors return CLI status 2 with a
diagnostic on stderr and no partial Markdown on stdout.

- [Synthetic Markdown](examples/synthetic.md) / [JSON](examples/synthetic.report.json):
  invented input, not real team evidence; six selected plays, five observed EPA,
  one matching baseline play. It intentionally shows withheld intervals.
- [Retrospective CAR offense Markdown](examples/car-2024-reg-before-week-19.md) /
  [JSON](examples/car-2024-reg-before-week-19.report.json): 2024 REG, week < 19,
  no optional context filters, available-source league comparison, 1,000 whole-game
  draws, seed 20261006. It contains aggregate report output, not raw play-by-play.

The real example was generated from the same pinned artifact used in the
[real-data audit](REAL_DATA_AUDIT.md). It contains 984 CAR plays across 17 games,
626 dropbacks, and 984 observed EPA values. The source was acquired on
2026-09-30, so this is **retrospective** analysis, not proof that these inputs or
the upstream EPA model were available during 2024. Nominal intervals retain the
few-game warning. No prediction, adjusted team-strength estimate, or scouting
recommendation is generated.

## Exact replay from source

The synthetic example is produced by the pipeline command in the README with
`--compare-league --bootstrap-repetitions 200 --bootstrap-seed 0` and its exact
source label. The pinned historical example requires the recorded snapshot to
already exist; no implicit acquisition occurs:

```sh
snapshot_dir=data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06
PYTHONPATH=src python3 -m opponent_intelligence \
  --snapshot "$snapshot_dir" \
  --source-label 'nflverse 2024 retrospective snapshot; acquired 2026-09-30 UTC' \
  --team CAR --side offense --season 2024 --before-week 19 --compare-league \
  --bootstrap-repetitions 1000 --bootstrap-seed 20261006 \
  | PYTHONPATH=src python3 -m opponent_intelligence.brief --report -
```

The committed JSON retains the pipeline's Python JSON serialization. Do not
normalize numbers through another serializer when regenerating an exact example:
changing `1.0` to `1` can preserve a measurement while changing its report fingerprint.
To regenerate, keep the pipeline JSON, then render that same JSON. CI renders both
committed JSON examples byte-for-byte without raw-data access; it also regenerates
the synthetic source report and brief independently from the original CSV fixture.

The real aggregate example retains nflverse attribution, CC-BY-4.0 identification,
license/source URLs, retrieval/update timestamps, and both archive/decoded hashes.
The brief identifies its transformation as a summary of those metrics. See
[acquisition and license evidence](INGESTION.md) for source terms and limitations.

## Display and traceability contract

Brief format v1 supports report schema v2, the present context/comparison contract,
and optional `game_cluster_percentile_v1` uncertainty. Unknown report or bootstrap
versions fail rather than inheriting labels intended for a different method.

| Display | Source and rule |
| --- | --- |
| Role, season/type, exclusive cutoff, contexts | `cohort` and `metric_context`; defense never flips EPA or success |
| Overall / situational measurements | `overall`, `situations`; deterministic down then short/medium/long ordering |
| Play/game/EPA counts and warnings | Each population's own counts; missing EPA is not a zero or a removed dropback |
| Baseline and differences | `league_comparison`; join by down/distance keys, never by list position or overall fallback |
| Coverage and accounting | Full recorded population and row/filter ledgers, without adding overlapping ledgers |
| Intervals, withheld states, game support and draws | Every `uncertainty.overall` and `uncertainty.situations` entry, including baseline and difference |
| Provenance and cautions | Source metadata and all three warning lists retained as literal text |

Individual rates are formatted as percentages to one decimal; rate differences
are percentage points to one decimal. EPA and its differences use three decimals.
Only display is rounded; no underlying measurement is replaced. Rounded signed
zero is displayed without a minus sign, and a narrow rounded interval is not
certainty. Full precision remains in JSON. Undefined values say **unavailable**;
an unrequested comparison/uncertainty block is distinguished from a requested but
empty one. No ranking or outcome-based selection of favorable findings occurs.

The report fingerprint is SHA-256 of UTF-8-encoded Python
`json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)`.
Whitespace and object-key order do not affect it; array order and Python-decoded
number representations do. This is the application's serialization rule, not an
RFC canonicalization claim. It covers the entire report, including extra fields
not summarized in tables. The separate input fingerprint identifies CSV bytes.
Neither digest is an authenticity signature or a substitute for verifying a raw
snapshot with the ingestion pipeline.

## Input checks and safe text

The CLI limits input to 4 MiB, rejects duplicate JSON keys, malformed UTF-8,
non-finite values, and incomplete/unsupported consumed fields. Validation checks
roles, context coordinates and bounds, counts/null denominators, sample flags,
source/population/filter ledgers, comparison alignment/direction, and uncertainty
units/support/status/replicate relationships. A supplied snapshot must contain
the supported provenance notices and agree with the report's decoded hash/season.

This is **not** independent raw-play verification, a general-purpose JSON Schema
validator, or a proof that a supplied EPA mean/bootstrap interval is authentic.
Extra fields are fingerprinted but may not be displayed outside the metadata
sections. Arbitrary report labels remain caller assertions, even with a snapshot.

All embedded data is literal text: line breaks are collapsed, control/bidi format
characters are made visible, and ASCII punctuation is escaped. This follows
[CommonMark's backslash-escape rules](https://spec.commonmark.org/0.31.2/#backslash-escapes)
and the [GFM table syntax](https://github.github.com/gfm/#tables-extension-).
Source URLs remain visible text; embedded Markdown links, images, HTML and scripts
are not activated. No rendering dependencies are added to the project.

## Verification and next boundary

Twenty renderer tests cover independent hand-calculated synthetic values, both
roles, zero/missing/empty cases, every interval status, percentage-point units,
support visibility, reordered buckets, rejected malformed inputs, escaping,
provenance, unchanged inputs, offline file/stdin/subprocess execution, and both
exact examples. The full 181-test suite passes on Python 3.11/3.12/3.13.

The same renderer was exercised on 32 pinned CAR report combinations: both roles,
before weeks 3/19, unrestricted/Q4 clock 0..120, comparison off/on, and uncertainty
off/on (200 draws). JSON was unchanged after rendering and source fingerprints
were retained. This checks report-to-brief integration, not new statistical
coverage or an independent re-audit of the already checked metrics. A separate
bundled Markdown parser found no active markup from hostile sample labels; a
network-blocked headless preview showed no horizontal overflow at 1280 pixels.

Next, audit personnel/motion field availability and source licensing before
claiming those concepts can be measured. The brief does not contain those fields,
an opponent-specific matchup model, a UI, or deployment.
