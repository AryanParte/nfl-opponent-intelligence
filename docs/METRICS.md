# Metric contract v1

## Cohort

A selected team's eligible plays from one explicitly requested NFL season and REG
or POST season type, with `week < before_week`. `--before-week 3` selects weeks 1–2.
Default season type is REG. `--side offense` (the default) matches `posteam`;
`--side defense` matches `defteam`, pooling the offenses that faced that defense.
No automatic cross-season or playoff pooling occurs. Week 1 can validly yield no
observations. The report names the requested team and role, including empty cohorts.

Only `play_type` run/pass rows are included. Sacks are pass plays. A scramble is
classified as a dropback using `qb_dropback`, even when its play type is run.
Kneels, spikes, two-point attempts, special teams, and `no_play` rows are excluded.
This intentionally excludes nullified-penalty/no-play outcomes rather than
claiming to reconstruct every attempted play call. Penalties retained as run/pass
in the upstream data remain included. See
[nflfastR's guide](https://nflfastr.com/articles/beginners_guide.html) and
[upstream field construction](https://github.com/nflverse/nflfastR/blob/master/R/helper_add_nflscrapr_mutations.R).

Recognized missing play types are excluded and counted as `missing_play_type`;
they do not increase play-call or EPA denominators. Unknown named types invalidate
the input instead of silently becoming exclusions. See the
[input contract](DATA_CONTRACT.md#play-type-validation-and-exclusion-order) for
accepted categories, missing markers, and exclusion precedence.

## Pre-play field-position ranges

`--yardline-min` / `--yardline-max` (Python: `yardline_min` / `yardline_max`) select
an inclusive `yardline_100` range after the team, role, season/type, and exclusive
week filters. Values must be finite numbers in 0..100 with minimum <= maximum.
One omitted bound defaults to 0 or 100; both omitted means **no field filter**.
Bounds may be equal or fractional. The [input contract](DATA_CONTRACT.md#optional-field-position)
defines the source field and its validation.
Python bounds accept built-in integers/floats, not booleans or numeric strings;
the CLI parses numeric arguments before applying the same range checks.

Coordinates remain offense-relative even for a defense report: 20 means 20 yards
from the offense's opponent's goal line, while 80 means the offense's own 20.
Do not substitute `100 - yardline_100` when selecting defense. Selection uses the
pre-play position, not yards gained, touchdown flags, or an end-of-play location.
The explicit 0..20 range is a play cohort, not a drive-level red-zone efficiency
statistic or a claim of an NFL-standard metric definition.

A requested filter excludes missing positions, with a warning and counts. Without
a filter, missing positions do not remove plays. Consequently, explicitly asking
for 0..100 is **not** equivalent to omitting both flags if positions are missing.
An absent column causes an error when filtering; a present but all-missing column
can validly yield zero plays and null rates. Missing EPA among selected plays still
affects only EPA/success denominators.

Filtered reports add `cohort.field_position` with the field, effective inclusive
bounds, offense perspective, and missing policy. They also add
`data_quality.field_position_filter` with `plays_before_filter`,
`missing_yardline_100`, `outside_range`, and `plays_after_filter`. These satisfy
`before = missing + outside_range + after` within the otherwise selected cohort.
The global `eligible_rows_outside_cohort` already includes those removed by the
field filter; do not add the nested counts again. Situations, rates, games, and
sample warnings are calculated on the final selected plays.

These optional fields are additive within report schema v2 and absent when no
range is requested. Valid unfiltered reports retain their previous JSON output.
Recognizing the optional source field does intentionally reject malformed observed
values that were previously ignored. The metric formulas themselves are unchanged.

## Pre-play score ranges

`--score-min` / `--score-max` (Python: `score_min` / `score_max`) select an inclusive
range of **pre-play** `score_differential`, offense points minus defense points.
The [source contract](DATA_CONTRACT.md#optional-pre-play-score) requires whole points.
API bounds must be built-in integers, not booleans, floats, or numeric strings;
CLI bounds use integer notation. Minimum must not exceed maximum. One omitted
end is unbounded and is recorded as JSON `null`, not a fabricated maximum score.
Both omitted means no score filter. Zero is a real bound, not an omitted value.

Use maximum -1 for a trailing offense, both bounds 0 for a tie, or minimum 1 for
a leading offense. The sign is **not reversed** for defense selection: -7 means
the opposing offense trails the selected defense by seven. These are point ranges,
not inferred possession counts, win probabilities, or a definition of neutral
game situations. Never substitute post-play scores, which can select on outcomes.

Missing scores are excluded only when a score range is requested. A present but
all-missing column yields zero plays and null rates; an absent column is an error,
including in empty cohorts. No zero/tie imputation or post-play fallback occurs.
Missing EPA on retained plays still affects only EPA/success denominators.

Score-filtered reports add `cohort.score_differential` (field, inclusive bounds,
offense perspective, missing policy), `data_quality.score_differential_filter`
(`plays_before_filter`, `missing_score_differential`, `outside_range`,
`plays_after_filter`), and `data_quality.filter_order`. Order is fixed: team/role/
season/week selection, then field position if requested, then score. The order
list names only active optional filters; it appears when score or period filtering
is used, preserving the earlier unfiltered and field-only JSON shapes.

Each stage satisfies `before = missing + outside_range + after`. The score
stage's input is the field stage's output when both are active. A play missing
both fields is counted only at the field stage; score missingness here is
conditional, not the total missing scores in the base cohort. The dataset audit
provides source-wide/eligible missingness separately. These removals are already
inside global `eligible_rows_outside_cohort`; do not add them again. Final metrics,
situations, games, and sample warnings use the intersection of all requested
filters. These additive schema-v2 keys do not change the metric formulas.

## Pre-play period and clock

`--period Q1|Q2|Q3|Q4|OT` (Python: `period`) selects pre-play `qtr`.
Q1–Q4 each select one regulation period; OT groups all `qtr >= 5`. With a period
selected, optional `--clock-min` / `--clock-max` (Python: `clock_min` / `clock_max`)
select **inclusive seconds remaining in that period at play start**. Bounds must
be built-in integers in 0..900, not booleans/floats/strings; CLI bounds use integer
notation. Minimum cannot exceed maximum. One omitted end defaults to 0 or 900;
both omitted means no clock filter, not an implicit complete-clock requirement.
Clock bounds require an explicit period, even for otherwise empty data.

For example, Q4 with maximum 120 includes clocks 120 and 0, but excludes Q2 and
OT even at the same clock value. Period-only Q4 retains missing clocks. An explicit
0..900 range removes them. Unknown periods are excluded only when period selection
is requested; absent headers are errors, distinct from present/all-missing values.
No missing context is imputed from another clock. See the [source contract](DATA_CONTRACT.md#optional-pre-play-period-and-clock).

An OT clock is time left **within each overtime period**, not cumulative time;
Q4 0..120 is not a claim about the final two minutes of a game that may go to OT.
The source's `game_seconds_remaining` resets to the period clock in OT, so it is
not a safe substitute for explicit regulation/OT selection. No season-specific
overtime duration or strategy is inferred from a clock range.

Time-filtered reports add these schema-v2 keys only when requested:

| Key | Meaning |
| --- | --- |
| `cohort.period` | `field=qtr`, requested `label`, inclusive bounds (OT: 5 to `null`), missing policy `exclude` |
| `cohort.clock` | `field=quarter_seconds_remaining`, effective inclusive bounds, `unit=seconds`, `timing=pre_play`, missing policy `exclude` |
| `data_quality.period_filter` | `plays_before_filter`, `missing_qtr`, `outside_period`, `plays_after_filter` |
| `data_quality.clock_filter` | `plays_before_filter`, `missing_quarter_seconds_remaining`, `outside_range`, `plays_after_filter` |

Order is fixed regardless of CLI flag order: team/role/season/week → field position
→ score → period → clock. `filter_order` lists active optional stages when score
or period is requested, preserving previous unfiltered/field-only output. Each
stage receives only the previous stage's survivors; before = missing + outside +
after. A play missing both period and clock is removed at the period stage, not
counted twice. These counts are conditional, not source-wide missingness, and
already belong in global `eligible_rows_outside_cohort`. Final metrics/situations
use survivors, and missing EPA affects only EPA/success denominators. Neither
defense selection nor time filtering reverses EPA or score signs.

Valid reports without these options retain their previous JSON output. All metric
formulas, exclusive week cutoffs, and provenance meanings are unchanged. Optional
source fields that are present but malformed now fail validation.

## Matched league baselines

`--compare-league` (Python: `compare_league=True`, a strict boolean) adds
`league_comparison` within report schema v2. Omitted/false leaves the previous
report unchanged, including warnings. No extra source columns or network are needed.

The comparison population consists of **other teams in the same role**, from
the same supplied dataset, season, REG/POST type, and exclusive week window:

- Offense: select `posteam != team`; exclude the selected offense's plays.
- Defense: select `defteam != team`; compare offensive production allowed by
  other defenses. The selected franchise's offensive plays can still belong to
  this baseline. Exclusion is by role, not every game involving that franchise.

The role/EPA meanings follow the [nflreadr dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv)
and [nflfastR's team summaries](https://nflfastr.com/articles/beginners_guide.html),
rechecked on 2026-10-05. Leave-team-out pooling is this application's explicit
comparison policy, not a claimed upstream or NFL-standard metric.

The same validated field/score/period/clock filters run in the same order for
both populations. No missing context is imputed. Baseline metrics use the existing
formulas: dropbacks / eligible plays, mean observed EPA, and positive EPA / observed
EPA. Pool counts/sums across plays; **do not average team or game averages**.
Baseline `small_sample` and `small_epa_sample` use the requested play threshold
separately. They are not uncertainty intervals or significance tests.

| Comparison key | Contract |
| --- | --- |
| `population` | Excluded team, role/source team field, `available_source_only` scope, `pooled_plays` weighting, sorted observed teams and count **after filters**, and number of games shared with the selected cohort |
| `cohort` | The report's season/type/week, role, threshold, and effective requested contexts, without a selected `team` field |
| `overall` | Baseline measurements with play/game/EPA denominators and sample flags |
| `overall_difference` | Selected overall minus baseline overall |
| `situations` | Only the selected team's observed down/distance buckets, each with matching `baseline` metrics and `difference` |
| `data_quality` | Same-season/type/window eligible rows, selected-team rows excluded before context filtering, baseline rows before/after filters, ordered conditional filter counts |
| `warnings` | Baseline-specific coverage, interpretation, dependence, empty/missing-data notices |

Differences have keys `dropback_rate_pp` and `success_rate_pp` (100 × rate
difference in **percentage points**, not percent change), and `epa_per_play`
(difference in expected points per observed play). Positive means numerically
higher than baseline, not universally better. Defense retains the offense's sign.
`difference_convention` is `selected_minus_baseline`.

If either side lacks the relevant denominator, its difference is `null`. An empty
matching baseline bucket stays empty even if overall league data exists. Baseline-only
buckets are not invented as selected-team observations; the displayed baseline
situation counts therefore need not sum to baseline overall plays. No selected
plays means no comparison situation rows, but a baseline overall may still exist.

The population ledger satisfies `same-season/type/window rows = selected-team
rows + baseline rows before context filters`. Each active baseline filter then
satisfies `before = missing + outside + after`. The top-level data quality still
describes the selected team; its outside-cohort count already includes baseline
plays. Do not add the two ledgers as if they were disjoint source totals.

"League" is a baseline label, not a completeness certificate: a manual file may
contain one other team or none, and narrow filters may remove many teams. Overall
differences match requested ranges but do not reweight down/distance or other
within-range context mixes; use the matched bucket rows. Neither these differences
nor the baseline adjust for opponent strength or justify causal/predictive claims.
The two populations have disjoint plays but may share games and opponents. Later
uncertainty work must respect those dependencies. The exclusive cutoff does not
reconstruct historical source availability or upstream model training.

## Definitions

- **Plays:** count of the eligible cohort, regardless of EPA availability.
- **Dropbacks:** eligible plays where `qb_dropback == 1`, including sacks and
  scrambles. The complement is labeled designed runs for this completed-play
  cohort; this is an outcome-based proxy, not film-verified play-call intent.
- **Dropback rate:** dropbacks / eligible plays. Missing EPA does not change it.
- **EPA per play:** arithmetic mean of observed EPA, with an explicitly reported
  `epa_observations` denominator. EPA expresses expected points added from the
  possession team's perspective; it is imported from upstream, not fit here.
- **Success rate:** number of observed EPA values strictly greater than zero /
  EPA observations. Zero EPA is observed but not a success. This is not the
  alternative yardage-threshold definition of success rate.
- **Situations:** down 1–4 crossed with short (0–3 yards to go), medium (4–6), or
  long (7+). These transparent product buckets are not claimed as an NFL standard.
- **Small samples:** `small_sample` flags plays below the chosen threshold;
  `small_epa_sample` applies it independently to EPA observations. Default 30 is a
  warning heuristic, not a statistical significance or reliability guarantee.

Undefined rates return JSON `null`, never a misleading zero. Source row counts,
exclusions, selected games, and missingness should stay visible in later UIs.

## Defense interpretation

Changing the selected side does not change any metric formula. In a defense view,
EPA and success describe opposing offenses' production allowed; EPA is not negated
and success is not inverted. Positive EPA remains good for the offense. A zero-EPA
play is observed but unsuccessful under this definition. Neither this success rate
nor its complement is a drive-level defensive stop rate. Missing EPA is still
excluded only from EPA/success denominators, not from play-call counts.

Dropbacks and designed runs describe the offenses faced, and down/distance is the
offense's pre-play situation. These conventions follow the
[nflreadr field dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv),
checked on 2026-10-01: `posteam` is the possession team, `defteam` is the defense,
and EPA is possession-relative. A defense cohort may contain multiple opposing
offenses and their game situations; it does not isolate defensive ability.

## Report schema v2

Report JSON changed on 2026-10-01. Consumers must replace the v1 `cohort.offense`
field with `cohort.team` and inspect `cohort.side` (`offense` or `defense`). The
default CLI/API role remains offense and its measurements are unchanged, but the
JSON shape is intentionally not backward-compatible. All reports, including
manual CSV and empty reports, emit `schema_version: 2` and this additional context:

```json
{
  "metric_context": {
    "perspective": "offense",
    "interpretation": "allowed",
    "success_condition": "epa > 0"
  }
}
```

`interpretation` is `allowed` for defense and `produced` for offense. Remaining
cohort fields, metric keys, source provenance, exclusions, and null behavior are
unchanged. Renderers must use the role/context instead of silently labeling every
report an offense report. Raw snapshot manifests and audit documents keep their
own schema version 1; the unchanged metric formulas remain metric contract v1.

## Independent fixture calculation

For synthetic CAR/2024/REG before week 3, six plays remain. Three are dropbacks,
three are designed runs. Observed EPA is 0.8, 0.2, -1.2, 0.4, and 0.0, which sums
to 0.2: EPA/play = 0.2 / 5 = 0.04. Three of five observed values are positive, so
success rate = 0.6. The sixth play has missing EPA but belongs in the tendency
denominator. These numbers are test expectations, not Panthers findings.

The same CSV's ATL defense/2024/REG before week 3 contains five plays: three
dropbacks and two designed runs. Its four observed EPA values are 0.8, 0.2, -1.2,
and 0.4, giving 0.2 / 4 = 0.05 EPA/play and 3 / 4 = 75% offensive success allowed.
The fifth play has missing EPA. The defense tests also use separate synthetic typed
records to cover multiple opponents; those are not additional NFL observations.

`test_field_position.py` generates a separate synthetic CAR cohort with six plays:
positions 0, 20, 20.5, 100, missing, and 10. The 0..20 filter leaves three plays,
one dropback, and EPA 0.8, -0.4, and missing. Thus EPA/play is 0.4 / 2 = 0.2,
success is 1 / 2, and dropback rate is 1 / 3. One missing position and two known
out-of-range positions reconcile the three removals; none is a real team finding.

`test_score_filters.py` uses a separate nine-play synthetic base. A 0..20 field
range removes two unknown positions and one outside position, leaving six.
A -7..0 score range then removes one unknown score and one leading-offense play,
leaving four plays: two dropbacks and EPA 0.8, -0.4, 0, and missing. EPA/play is
0.4 / 3, success 1 / 3, and dropback rate 2 / 4. One record missing both contexts
is removed once, not twice. The original fixture remains unchanged.

`test_clock_filters.py` supplies another invented cohort: 13 base plays become
8 after Q4 selection (2 unknown periods, 3 other periods), then 5 with clock 0..120
(1 unknown clock, 2 outside). Those five have 3 dropbacks and 4 observed EPA values
0.8, -0.4, 0.3, 0.7: EPA/play 0.35 and success 3/4. Combining field 0..20, score
-7..0, Q4, and clock 0..120 gives the staged counts 13 → 10 → 9 → 5 → 3. The final
three plays have one dropback and EPA 0.8, -0.4, and missing, hence EPA/play 0.2,
success 1/2, and dropback rate 1/3. These are test expectations, not team findings.

## Limits on interpretation

The report is descriptive. It does not estimate play-call intent perfectly,
adjust for opponents on either side, isolate player skill, or recommend a play.
Even with requested field/score/period/clock filters, situational buckets still mix
personnel, opponents, and game strategy (and context values within each range).
Repeated plays within a game are dependent; later uncertainty work
must respect that structure instead of assuming independent observations.

The exclusive week cutoff keeps target-week outcomes out of the cohort. It does
not guarantee a leakage-free historical prediction: current releases may revise
old observations, and the upstream EPA model may have been trained on later
data. Forecasting requires explicit information-availability dates, versioned
features and models, time-based evaluation, and a baseline. Do not repurpose this
output as proof of predictive quality without that work.
