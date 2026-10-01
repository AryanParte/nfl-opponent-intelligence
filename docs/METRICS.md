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

## Limits on interpretation

The report is descriptive. It does not estimate play-call intent perfectly,
adjust for opponents on either side, isolate player skill, or recommend a play.
Situational buckets still mix score, time, field position, personnel, and game
strategy. Repeated plays within a game are dependent; later uncertainty work
must respect that structure instead of assuming independent observations.

The exclusive week cutoff keeps target-week outcomes out of the cohort. It does
not guarantee a leakage-free historical prediction: current releases may revise
old observations, and the upstream EPA model may have been trained on later
data. Forecasting requires explicit information-availability dates, versioned
features and models, time-based evaluation, and a baseline. Do not repurpose this
output as proof of predictive quality without that work.
