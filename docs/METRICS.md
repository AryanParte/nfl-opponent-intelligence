# Metric contract v1

## Cohort

An offense's eligible plays from one explicitly requested NFL season and REG or
POST season type, with `week < before_week`. `--before-week 3` selects weeks 1–2.
Default season type is REG. No automatic cross-season or playoff pooling occurs.
Week 1 can validly yield no observations. The report names the requested cohort.

Only `play_type` run/pass rows are included. Sacks are pass plays. A scramble is
classified as a dropback using `qb_dropback`, even when its play type is run.
Kneels, spikes, two-point attempts, special teams, and `no_play` rows are excluded.
This intentionally excludes nullified-penalty/no-play outcomes rather than
claiming to reconstruct every attempted play call. Penalties retained as run/pass
in the upstream data remain included. See
[nflfastR's guide](https://nflfastr.com/articles/beginners_guide.html) and
[upstream field construction](https://github.com/nflverse/nflfastR/blob/master/R/helper_add_nflscrapr_mutations.R).

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

## Independent fixture calculation

For synthetic CAR/2024/REG before week 3, six plays remain. Three are dropbacks,
three are designed runs. Observed EPA is 0.8, 0.2, -1.2, 0.4, and 0.0, which sums
to 0.2: EPA/play = 0.2 / 5 = 0.04. Three of five observed values are positive, so
success rate = 0.6. The sixth play has missing EPA but belongs in the tendency
denominator. These numbers are test expectations, not Panthers findings.

## Limits on interpretation

The report is descriptive. It does not estimate play-call intent perfectly,
adjust for defensive opponents, isolate player skill, or recommend a play.
Situational buckets still mix score, time, field position, personnel, and game
strategy. Repeated plays within a game are dependent; later uncertainty work
must respect that structure instead of assuming independent observations.

The exclusive week cutoff keeps target-week outcomes out of the cohort. It does
not guarantee a leakage-free historical prediction: current releases may revise
old observations, and the upstream EPA model may have been trained on later
data. Forecasting requires explicit information-availability dates, versioned
features and models, time-based evaluation, and a baseline. Do not repurpose this
output as proof of predictive quality without that work.
