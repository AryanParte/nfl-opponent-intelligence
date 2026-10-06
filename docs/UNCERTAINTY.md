# Exploratory game-level uncertainty

Add `--bootstrap-repetitions 1000` to an existing report command. The optional
`--bootstrap-seed 0` selects the seed (default 0). Repetitions must be an integer
in 200..10000; seeds must be integers in 0..4294967295 and require repetitions.
The Python keywords are `bootstrap_repetitions` and `bootstrap_seed`; both default
to `None`, meaning no uncertainty block. Booleans are not accepted as integers.
No extra packages, source fields, or network access are needed for reporting.

## What is estimated

This is an exploratory, pointwise **game-cluster percentile bootstrap** of the
existing pooled dropback rate, success rate, and mean observed EPA. With
`--compare-league`, it also describes the available baseline and the
selected-minus-baseline differences. It does not change the point estimates,
eligibility, missing-data denominators, or defense interpretation.

Games, not plays, are the resampling units. Plays in the same game share strategy,
opponents, personnel, and game state. Treating them as independent draws can
understate uncertainty. Whole-cluster resampling and the hazards of few clusters
are discussed by [Cameron and Miller, sections II.F and VI.C](https://faculty.econ.ucdavis.edu/faculty/cameron/research/Cameron_Miller_JHR_2015_February.pdf).
The [SciPy bootstrap documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)
describes percentile intervals and paired sampling; SciPy is **not** a runtime
dependency here. These sources motivate the method, not its calibration for NFL data.

An NFL team's single-season sample is small, and games involving repeated teams
are not independent. The procedure preserves within-game dependence and shared
games, **not** cross-game team/opponent dependence. Bounds are nominal 95%
resampling intervals, not validated 95% coverage, significance tests, opponent
adjustment, or forecasts. They do not measure upstream EPA-model uncertainty,
source revisions, selection/missingness bias, or future performance.

## Reproducible procedure

1. Apply the existing season/type/exclusive-week and requested pre-play context
   filters once. Do not use future plays, outcome-based filters, or new imputation.
2. Without comparison, use the selected cohort's distinct game IDs. With
   comparison, use the **union** of selected and baseline game IDs after filtering,
   including games in baseline-only situations. Sort IDs lexicographically.
3. For each of B repetitions, draw G games uniformly with replacement from those
   G observed games using a local `random.Random(seed).randrange(G)` generator.
   A game drawn twice receives weight two. Apply that same multiplicity to all
   its eligible plays on both sides and in every reported situation. Never draw
   selected and baseline populations independently.
4. Recompute pooled numerator/denominator ratios using per-game sufficient totals.
   Do not average game averages. EPA and success retain only observed EPA in their
   denominator; missing EPA still contributes to the dropback denominator. A
   difference is computed **within each paired replicate**, not by subtracting
   independently computed interval endpoints. Rate differences use percentage
   points; individual rates use proportions. EPA differences retain the offense's sign.
5. For each metric, count and exclude replicates with an absent required denominator.
   A difference requires both sides to be defined. Of the remaining ordered values,
   use the 2.5th and 97.5th percentiles with linear interpolation at `(n - 1) * p`.
   The support/validity rules below can withhold the resulting interval.

This resamples the observed filtered population, not an external schedule. The
number of selected games in a replicate can vary, including zero; no replacement
draw is made just to get a usable value. Turning comparison on changes the
resampling population and can change selected-side bounds and undefined counts.
The seed, options, immutable source, method version, and supported Python runtime
are needed for replay. Tests check row-order invariance and Python 3.11–3.13;
the local RNG does not modify global random state. Future Python RNG changes may
require a method-version migration.

## Support, unavailable intervals, and warnings

Support is counted separately for each population, metric, and down/distance
bucket. Dropback support means distinct games with eligible plays. EPA/success
support means distinct games with at least one observed EPA. Difference support
includes both populations; a large league cannot compensate for a tiny team sample.
Existing play-count flags remain independent of these game-level rules.

| Status | Interval behavior, in precedence order |
| --- | --- |
| `undefined_estimate` | A required side has zero contributing games; bounds are `null` |
| `insufficient_games` | A required side has fewer than five contributing games; bounds are `null` |
| `too_few_valid_replicates` | Fewer than `ceil(0.95 * performed_repetitions)` defined values; bounds are `null` |
| `degenerate_interval` | Endpoints are equal/near-equal (`math.isclose`, relative and absolute tolerance `1e-12`); bounds are `null`, not certainty |
| `ok` | Numerical interval is available under this method; this is not a reliability certificate |

Five games and 95% usable draws are **application safeguards**, not published
statistical guarantees. `few_games` separately warns below 20 contributing games
on any required side, even when an interval is returned. Twenty is a warning
heuristic, not a guarantee either. All finite-sample and cross-game limitations
still apply above these cutoffs. Any available interval with undefined draws is
conditional on the defined replicates, so valid/undefined counts must remain visible.
Increasing B reduces simulation noise; it does not create additional observed games.

## JSON contract

Opt-in adds only top-level `uncertainty` within report schema v2. Every prior field,
including warnings, source provenance, and `league_comparison`, stays unchanged.
Metadata records method version, nominal level, seed/RNG, requested/performed
repetitions, quantile convention, resampling population/game count, shared weights,
and support/validity cutoffs. An empty resampling frame performs zero repetitions.

`overall.selected` and each observed `situations[].selected` contain entries for
`dropback_rate`, `success_rate`, and `epa_per_play`. Comparison adds `baseline`
and `difference` at each level; difference rate keys end in `_pp`. An entry has:

- `interval`: `{lower, upper}` or `null`, plus an explicit `status`;
- `unit`: `proportion`, `percentage_points`, or `expected_points_per_observed_play`;
- `support_games`: a map naming each required population, plus `few_games`;
- `valid_replicates` and `undefined_replicates`, summing to performed repetitions.

Point estimates remain in the existing report fields. Only selected-team observed
situations are listed, and missing baseline buckets never borrow overall support.
Intervals are pointwise, not simultaneous intervals across all displayed findings.
Renderers must carry the status, support, and method limitations into any brief.

## Verification and remaining limits

`tests/test_uncertainty.py` independently enumerates all 3,125 ordered five-game
resamples. It expands games into plays and checks bounds using a separate quantile
implementation. Unequal game sizes distinguish pooling from averaging game means;
shared EPA effects cancel from paired differences. Other cases cover missing EPA,
zero versus missing, empty cohorts/buckets, support boundaries, degeneracy, exactly
95% versus less than 95% valid draws, context filters, temporal exclusion, defense
semantics, immutability, deterministic CLI output, and RNG isolation.

The [pinned-data check](REAL_DATA_AUDIT.md#uncertainty-extension-2026-10-06)
reconciles actual-source support and intervals against independent calculations.
These verify implementation, not statistical coverage. Coverage simulation and
alternative cross-game/small-sample methods remain future methodological work;
do not label this first method calibrated or use an interval excluding zero as
a claim of team strength or predictive quality.
