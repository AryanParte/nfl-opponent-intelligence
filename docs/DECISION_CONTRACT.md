# Offline Run/Pass evidence contract v1

First P1.5 slice, 2026-10-17; optional matched candidate baselines added 2026-10-18.
Optional candidate-level game support and exploratory intervals added 2026-10-19.
Explicit descriptive contrast/abstention policy added 2026-10-21; see
[comparison and opponent-evidence policy](DECISION_POLICY.md).
This is a Python-only **descriptive evidence builder**,
not a new API, CLI, browser mode, predictive model or recommendation engine. Scout
schema v2, endpoints, briefs and UI stay unchanged. The request and JSON-compatible
result have a separate `contract_version: 1`; do not send this result to the Scout
brief renderer or treat it as a schema-v2 report.

## Reproduce the invented example

From the repository root, with Python 3.11+ and no installed dependencies/network:

```sh
PYTHONPATH=src python3 - <<'PY'
import json
from pathlib import Path
from opponent_intelligence.decision import DecisionRequest, build_decision_evidence
from opponent_intelligence.pbp import load_csv

dataset = load_csv(Path("tests/fixtures/synthetic_pbp.csv"))
request = DecisionRequest(team="CAR", season=2024, before_week=3,
                          down=1, distance_min=10, distance_max=10, compare_league=True,
                          bootstrap_repetitions=200, bootstrap_seed=0)
result = build_decision_evidence(
    dataset, request, source_label="Invented test fixture; not real NFL observations",
)
print(json.dumps(result, indent=2, allow_nan=False))
PY
```

The fixture yields three first-and-ten plays in two games: Run has one play,
frequency 1/3, EPA 0 and success 0; Pass has two plays, frequency 2/3, EPA 0.6 and
success 1. Both samples are tiny. These numbers describe **invented rows**, not
Carolina performance. `preferred_candidate` is null even though one mean is higher.
The optional baseline has one ATL Pass with EPA 3: Pass's selected-minus-baseline
EPA difference is -2.4 and frequency difference is about -33.33 percentage points.
Baseline Run frequency is 0, but its EPA/success and outcome differences are null.
One available opposing offense is not certified league coverage.
The optional uncertainty block withholds all intervals here: frequency has two
selected support games and one baseline game; Run and Pass each have only one
selected observed-EPA game. Baseline Run outcomes have zero support and are
`undefined_estimate`, not a zero-width interval. More draws cannot add games.
For real offline work, load the already acquired immutable snapshot with the
existing `ingestion.load_snapshot` function; the builder never opens paths or
downloads data. The caller retains responsibility for a truthful source label.

## Request and selection

`DecisionRequest` is frozen and keyword-only. Values are validated by
`build_decision_evidence(dataset, request, source_label=...)`. Unknown arguments
raise `TypeError`; invalid supported values raise `ValueError`. No silent coercion.

| Request | Accepted semantics |
| --- | --- |
| `team` | Uppercase 2–3-letter source abbreviation; offense only. Syntactic validation is not a team registry. Unknown but well-formed teams yield an empty cohort. |
| `season`, `season_type` | Integer 1999–9999, `REG` (default) or `POST`; no cross-season/type pooling. A snapshot manifest's season must agree. |
| `before_week` | Integer 1–23, exclusive. Target-week and later outcomes are excluded; week 1 is valid and empty. |
| `down` | Required exact integer 1–4, not a down bucket. |
| `distance_min`, `distance_max` | Both required integers 0–100, inclusive and ordered; equal bounds mean exact recorded yards to go. No short/medium/long widening. |
| `yardline_min/max`, `score_min/max`, `period`, `clock_min/max` | Same pre-play, offense-relative bounds, optional-header checks, missing-value exclusions and defaults as [Scout](METRICS.md). Clock requires a period. |
| `minimum_plays` | Positive integer count-warning threshold, default 30; not an accuracy, independence or ranking guarantee. |
| `compare_league` | Boolean, default `False`. `True` adds same-role leave-team-out candidate baselines; no new data is loaded. Integer/string lookalikes are rejected. |
| `bootstrap_repetitions` | Optional integer 200–10000; omitted means no uncertainty block or resampling. Uses the existing offline bootstrap bounds. |
| `bootstrap_seed` | Optional integer 0–4294967295, default 0 when repetitions are set. Seed alone is invalid. Booleans/strings/floats are rejected. |

Booleans, numeric strings and floats are not accepted for integer fields. Field
position alone accepts finite integers/floats in 0–100. No `side`, opponent,
play-family, filesystem-path, model or fallback option exists here.
Defense remains a Scout capability, with offensive production **allowed** rather
than sign-flipped EPA or a defensive stop rate.

Selection order: season/type/week and offense → field position → score → period →
clock → exact down → distance. Only active optional filters are included. Each
stage records `before = missing + outside + after`; missingness is conditional on
surviving prior stages. Down/distance are required at ingestion, so their missing
counts are zero for a validated Dataset. Input/exclusion totals and source hash
continue to describe the **original full dataset**, not a relabeled filtered file.

Missing optional observations stay in the cohort when their filter is omitted.
An absent requested column is an error even when the selected team has no plays;
a present but all-missing column can yield an empty cohort. No imputation, nearby
distance/team/year fallback, or borrowing Scout's grouped buckets occurs.

These are historical selectors, not a game-state/rules validator. Zero yards means
recorded zero, not an inferred inches value. Goal-to-go is not independently
identified. OT means all recorded periods >=5; clock bounds apply within each
period. There is no inference of possession, legal future actions or OT rules.
A fourth-down result is **conditional on eligible Run/Pass**, not a comparison
with going, punting or kicking. Unsupported situations do not trigger a model.

## Candidate mapping and source audit

Reviewed the [nflreadr PBP dictionary at commit
`dca0b7f`](https://github.com/nflverse/nflreadr/blob/dca0b7f6c02f18a4d6e644b03f6d8ec8757d2265/data-raw/dictionary_pbp.csv).
Its definitions distinguish `play_type` from `qb_dropback`: sacks can be pass
rows, scrambles can be run rows, and both are dropbacks. `ydstogo` references the
line to gain or goal line. The implementation therefore uses the **already validated
typed** `Play.dropback`, not raw play type, completion, yards gained or description:

- `pass`: eligible `qb_dropback == 1`, labeled **Pass (dropback, including sacks/scrambles)**.
- `run`: remaining eligible `qb_dropback == 0`, labeled **Run (non-dropback)**.

The two candidates exhaust this project's eligible plays. Existing ingestion
excludes kneels, spikes, conversions, special teams, no-play and missing-type rows;
see [eligibility](DATA_CONTRACT.md). Nullified plays are not every attempted call,
and penalties retained as run/pass remain in scope. Do not interpret frequency as
the fraction of all snaps, all fourth-down choices or all calls a coach intended.

This is an observed category audit, **not validation of huddle intent**. The typed
dataset does not retain separate sack/scramble, RPO or aborted-play flags. An
aborted play retained as eligible is classified only by its dropback flag, not
reconstructed intent. No claims about concept recognition or clean designed-call
labels follow. RPO, play action, screen, inside/outside run and finer families stay
deferred under the [richer-source gates](DECISION_INTELLIGENCE.md).

No external implementation, new data or model artifact is copied or installed.
Existing [PBP attribution/CC BY 4.0 records](INGESTION.md#source-and-attribution-review)
and snapshot manifests remain intact. These terms do not substitute for a future
participation/charting/tracking source's own audit.

## Evidence, denominators and states

`population` contains final eligible plays and distinct games. Each candidate has:

- `plays`, `games`: all candidate observations, including missing EPA. Games may
  overlap across candidates; **do not sum candidate game counts** for parent games.
- `frequency = candidate plays / frequency_denominator`, where the denominator is
  the entire final eligible cohort. Values are proportions, not percentages.
- `epa_observations`, `missing_epa`: disjoint counts that sum to candidate plays.
- `epa_per_play`: arithmetic mean over that candidate's observed EPA;
  `success_rate`: fraction of those observations with EPA > 0. Zero is observed
  but not a success. The denominator is **not all candidate plays** when EPA is missing.
- `small_sample` and `small_epa_sample`: candidate plays and observed EPA count,
  respectively, below `minimum_plays`. Neither flag assesses game independence.

The calculations reuse `metrics.summarize_plays`; common population, bounds and
ordered exclusion logic live in `cohort.py`, also used by Scout. No duplicate
ingestion, browser calculation or second outcome formula was added.

| Condition | Frequency / `availability.frequency` | Outcomes / `availability.outcomes` |
| --- | --- | --- |
| Empty parent | null / `empty_cohort` | null / `empty_cohort` |
| Nonempty parent, candidate absent | 0 / `available` | null / `unobserved_candidate` |
| Candidate observed, all EPA missing | observed proportion / `available` | null / `missing_epa` |
| At least one observed candidate EPA | observed proportion / `available` | descriptive values / `available` |

Minimum point-estimate support is one parent play for frequency and one candidate
EPA observation for outcomes, explicitly recorded in `estimation_policy`. This
means mathematically defined, **not reliable**. Even clearing the 30-count warning
does not validate a comparison. Optional game support/interval rules below reuse
Scout's safeguards, not a decision-reliability threshold.

`comparison` always returns `status: insufficient_evidence`,
`reason: candidate_comparison_not_validated`, and `preferred_candidate: null`.
This is a capability/validation abstention even in large samples, not a test of
whether the point estimates happen to differ. There is no automatic winner,
fallback baseline, confidence score, EP/WP impact or model-estimated counterfactual.

The same block now includes `policy_version: descriptive_only_v1`, an explicit
`descriptive_contrast` over the selected offense, and deferred `opponent_evidence`.
The contrast subtracts **Run from Pass** for frequency/success (percentage points)
and observed EPA/play, reusing `metric_difference`. Per-metric `value`, `unit`,
`status` and `unavailable_candidates` distinguish undefined inputs from observed
zero differences. Candidate counts/denominators and warnings remain required
context. No Run/Pass contrast interval is implemented: its `uncertainty` returns
`status: not_implemented`, `interval: null`, even when individual candidate or
selected-minus-league intervals exist. Neither optional baselines/resampling nor
warning thresholds alter this block. See [exact states, interpretation, opponent
deferral and future admission gates](DECISION_POLICY.md). This is additive within
v1; the original three abstention fields retain their values, and Scout is unchanged.

## Matched candidate league baselines

`compare_league=True` adds `league_comparison` within contract v1. Omit it for
selected-only evidence; enabling it does not alter any selected counts, values,
source metadata or ranking state. Scout's separate schema-v2 comparison is unchanged.
The shared `metrics.metric_difference` preserves its arithmetic and null behavior.

Baseline plays must be in the **same source, season, season type and exclusive week
window**, with `posteam != requested team`. Exclusion is by offensive role, not by
game or defense: an opponent's offensive plays against the selected franchise may
remain. Apply the **identical ordered** optional contexts, exact down, inclusive
distance bounds and candidate mapping. Rechecked the pinned dictionary above for
possession-team, defense-team and offense-relative field/EPA semantics; leave-team-out
pooling is our explicit descriptive policy, not an NFL-standard adjustment model.

Pool individual plays and observed EPA, **not equally weighted team/game means**.
For example, invented ATL Pass EPA `[1, -1, missing]` and NO `[3]` give baseline
EPA `(1 - 1 + 3) / 3 = 1`, not the mean of team means `(0 + 3) / 2 = 1.5`.
The missing observation remains in the Pass frequency numerator. A requested
distance/field/score/time range can have different within-range mixes between
populations; matching the same bounds does not standardize those mixes or remove
unobserved confounding. No nearest-bucket, overall-league or other-season fallback.

| Comparison key | Meaning |
| --- | --- |
| `population` | `available_source_only`, excluded offense, `posteam` role field, pooled-play weighting, final plays/games, sorted observed teams/count and games shared with selected plays. |
| `cohort` | Same effective selection as the parent except selected `team` is omitted; the excluded team is in population metadata. The parent's estimation policy applies to both populations. |
| `candidates` | Run and Pass baseline evidence with the same fields, denominators, availability reasons and count flags as selected candidates, including absent candidates. |
| Candidate `coverage` | Teams/count with at least one matching candidate play, and games shared with the **same selected candidate**. Counts include plays with missing EPA; they are not observed-EPA support or independent-game certification. |
| Candidate `difference` | Matching selected candidate minus baseline candidate: `frequency_pp`, `epa_per_play`, `success_rate_pp`. |
| `difference_units` | Frequencies/success use 100 × proportion difference (percentage points, not percent change). EPA differences are expected points per observed play. Positive means numerically higher, not universally better. |
| `data_quality` | Temporal eligible rows, selected-offense rows excluded **before** context filters, baseline before/after counts and ordered stage ledgers. |
| `warnings` | Available-source scope, unequal context mixes, dependence and interpretation limits, missing EPA/context and empty-baseline notices. |

The single parent `source` hash/manifest applies to **both** populations; no second
snapshot or relabeled subset is created. The two populations have disjoint plays,
but games/opponents can overlap. Neither parent game totals nor candidate shared-game
counts should be summed across candidates. These coverage counts do not themselves
supply an uncertainty interval or correct cross-game dependence; optional
per-metric support is defined separately below.

The baseline ledger satisfies:

```text
same-season/type/window eligible = excluded selected-offense rows + baseline before filters
each filter: before = missing + outside + after
final baseline plays = Run plays + Pass plays
```

Its stage missingness is conditional on earlier filters, not all-source missingness.
The top-level source/outside-selected-cohort ledger is unchanged and **already
includes baseline plays**; do not sum it with baseline exclusions as disjoint totals.
Coverage teams are observed after all filters, separately for each candidate.

Every difference is null if either corresponding estimate is null. A candidate
with no plays in a nonempty parent has a genuine zero observed frequency, so its
frequency difference may exist while its EPA/success differences remain null.
An empty baseline gives null frequencies/outcomes/differences even if nearby
distances have data. A nonempty baseline never fills an empty selected cohort:
baseline evidence remains visible, selected estimates/differences stay null.
All-missing EPA also leaves frequency intact but blocks outcome differences.

The top-level `comparison` **still abstains** with
`candidate_comparison_not_validated`. Matched descriptive differences, even above
count-warning thresholds, are not enough to choose between Run and Pass. No
opponent-strength adjustment, causal/predictive validation or EP/WP action model
is implemented by these descriptive extensions.

## Optional candidate uncertainty

`bootstrap_repetitions` adds only top-level `uncertainty` within contract v1.
Existing candidate values, baseline comparisons, source and no-ranking state do
not change. No repetitions means no new block or resampling cost. This is not
Scout's `uncertainty.overall/situations` shape; decision evidence uses
`uncertainty.candidates`, in Run/Pass order, with `candidate`, `selected` and,
when comparison is requested, `baseline` and `difference`.

The adapter reuses [the existing game-cluster procedure and status gates](UNCERTAINTY.md),
not a second sampler, percentile formula or confidence policy. Filter the exact
cohort once, then draw G games with replacement from its sorted G observed game IDs
(the selected/baseline union when comparison is on). Each draw gives **both calls
and both populations the same game multiplicities**. Missing-EPA plays remain in
the frame. Games with no observations for a particular call are not discarded.

For each call and population, recompute:

| Metric | Replicate denominator | `support_games` |
| --- | --- | --- |
| `frequency` | All eligible parent-cohort plays in that draw | Games with parent-cohort plays, including games with zero observations of this call |
| `epa_per_play`, `success_rate` | Observed EPA for this candidate in that draw | Games with at least one observed EPA for this candidate |

The point-evidence candidate `games` field remains all games with that candidate's
plays, including missing EPA. It is neither frequency-denominator support nor
necessarily observed-EPA support. For example, a call observed once in one of five
parent games has five frequency-support games but at most one EPA-support game.
Zero observations of a call across a nonempty parent yields zero frequency in all
defined draws and a withheld `degenerate_interval`, not certainty that it is never
called. Its outcome estimate is undefined. A draw with no parent plays has null
frequency, not zero, and is counted as undefined rather than redrawn.

Differences are **selected minus matching league candidate** within each shared
draw, not Run minus Pass, and not subtraction of marginal interval endpoints.
Difference keys are `frequency_pp`, `success_rate_pp`, `epa_per_play`; both required
populations' support is reported. One well-supported side cannot rescue the other.
Individual rate intervals use proportions; differences use percentage points.

Entries expose `interval`, `status`, `unit`, `support_games`, `few_games`, and
valid/undefined replicate counts. Status precedence is `undefined_estimate`,
`insufficient_games` (below five on either required side),
`too_few_valid_replicates` (below 95% defined draws), `degenerate_interval`, then
`ok`. Fewer than 20 support games also warns. Gates are application safeguards,
not calibration or decision reliability. Empty union frames perform zero draws;
the two candidates and their unavailable states remain visible. Metadata preserves
method `game_cluster_percentile_v1`, nominal 0.95 level, seed/RNG, linear quantiles,
frame size, requested/performed draws, shared weights and thresholds.
The inherited `shared_game_weights` flag indicates selected/baseline pairing: it
is false for selected-only evidence. Run and Pass still share the same draws in
that mode; false does not mean the calls were sampled independently.

These are exploratory pointwise intervals, not simultaneous bounds, significance
tests, predictions, or a Run-versus-Pass decision rule. Cross-game team/opponent
dependence, confounding, source/model history, missingness bias and upstream EPA
model uncertainty remain unaddressed. Comparison changes the game frame and can
change selected-side intervals. Even an `ok` interval excluding zero never unlocks
a preferred call. Existing [primary references](UNCERTAINTY.md#what-is-estimated)
motivate reuse, not NFL calibration; no external implementation was installed.

`tests/test_decision_uncertainty.py` independently expands all 3,125 ordered draws
of five invented games, checks pooled candidate statistics and paired differences
against separate quantiles, and covers every support/withholding state. The
shared game effects cancel in a candidate EPA contrast despite varying marginal
intervals. Synthetic verification does not establish real-world coverage.

## Limits and foundation boundary

Source hash and a deep-copied snapshot manifest (when supplied by the snapshot
loader) preserve provenance. Filtering before a week does not establish that a
later source revision or upstream EPA model was available at that time. Outcomes
are historical offense-relative values; selection bias and unobserved confounding
remain. No causal, out-of-sample, game-rule or coaching validation is claimed.

The [2026-10-20 pinned-snapshot reconciliation](DECISION_AUDIT.md) now independently
checks candidate points, baselines, game support and seeded intervals on eight
predeclared situations directly from raw records. It verifies implementation,
not statistical calibration, intended calls or causal decision quality.
The [2026-10-21 policy](DECISION_POLICY.md) closes the remaining P1.5 foundation
gate within descriptive-only scope. Preferred calls and opponent conditioning
remain explicitly deferred, not implicitly approved by completion of a milestone.
Next: a bounded, version-pinned nfl4th input/output, terms, assumptions and
historical-availability audit under P1.6 before any model integration. API/UI and
richer data remain separate later units.
