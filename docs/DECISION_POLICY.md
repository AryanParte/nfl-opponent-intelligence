# Run/Pass comparison and abstention policy

Recorded 2026-10-21, policy `descriptive_only_v1`. This closes P1.5's
**descriptive foundation**, not decision-quality validation. The offline builder
can compare observed Run/Pass summaries but must abstain from choosing a call.
Scout, the existing source/metric/uncertainty stack and contract v1 are preserved.
No model, API, UI, new source or opponent adjustment is introduced.

## Three different questions

1. **What was observed?** Candidate frequency, observed EPA and EPA > 0 success,
   with their own denominators, games, missingness, source and selected situation.
2. **How do those summaries differ?** A deterministic descriptive subtraction,
   with explicit direction/units and no replacement for missing estimates.
3. **Which call should be chosen next?** Not answered. Observed calls were selected
   under different circumstances; neither a mean nor an exploratory interval
   estimates the outcome of an unplayed alternative here.

The first two are supported. The third requires a separately justified target,
method and evaluation. A larger sample or more resamples does not change that
capability boundary. There is no significance cutoff that enables ranking.

## Executable contract

`comparison` retains its original three fields and meanings:

```json
{
  "status": "insufficient_evidence",
  "preferred_candidate": null,
  "reason": "candidate_comparison_not_validated"
}
```

The reason refers to **preferred-call validation**, not an arithmetic bug or an
assertion that every cohort is small. The additive `policy_version` identifies
this policy. Clients must not infer a winner from signs, `available`, `ok`, a
false small-sample flag, or a missing interval. There is no override request.

`comparison.descriptive_contrast` adds:

- `population: selected_offense`, `direction: pass_minus_run`. Both candidates
  come from the **same already filtered offense cohort**. No new filtering,
  widening, reweighting, ingestion or formula implementation is involved.
- `metrics.frequency_pp`: 100 × (Pass frequency − Run frequency). The common
  denominator is all eligible Run/Pass plays, including plays with missing EPA.
  This is a difference in observed usage, **not call utility** or percent change.
- `metrics.epa_per_play`: Pass observed EPA mean − Run observed EPA mean. Each
  mean uses its own observed-EPA denominator. It is not a paired-play effect.
- `metrics.success_rate_pp`: 100 × (Pass success rate − Run success rate), using
  each call's observed EPA and success condition EPA > 0. It is not a conversion
  probability, scoring probability or win probability.

Each metric returns `value`, `unit`, `status` (`available` or `unavailable`), and
`unavailable_candidates`. The latter maps only candidates with undefined inputs
to their existing availability reason; it is `{}` for a defined difference.
Counts, count warnings and observed denominators remain in `candidates`; do not
display this summary stripped of them. Units are `percentage_points` for the
rates and `expected_points_per_observed_play` for EPA.

| Selected evidence | Frequency difference | Outcome differences / missing candidate reasons |
| --- | --- | --- |
| Empty cohort | null, `unavailable`, both `empty_cohort` | null, both `empty_cohort` |
| Nonempty parent, one candidate absent | ±100 pp, `available` | null, absent candidate `unobserved_candidate` |
| A candidate has plays but no observed EPA | defined, `available` | null, that candidate `missing_epa`; preserve the other candidate's reason if also undefined |
| Both candidates have observed EPA | defined, `available` | defined, `available`; zero and negative differences remain real values |

No additional minimum count is invented: frequency needs a nonempty parent and
outcome subtraction needs at least one observed EPA **per candidate**. These are
arithmetic requirements, not adequacy guarantees. Changing `minimum_plays` only
changes the existing candidate count warnings, never the subtraction or abstention.
Missing EPA is not imputed or removed from frequency. Missing context follows the
existing conditional exclusion ledgers. Neither a league value nor a nearby
situation fills an unavailable selected estimate.

`comparison.descriptive_contrast.uncertainty` always returns
`{"status": "not_implemented", "interval": null}`. The existing optional
`uncertainty.candidates` intervals concern **individual candidates** and
**selected-minus-matching-league** differences, not Pass-minus-Run. Do not subtract
marginal endpoints or reuse a league-difference interval for this new contrast.
Even non-overlapping individual intervals do not change the policy. A future
contrast interval needs a tested within-replicate contrast and support policy;
that alone still would not validate ranking. No extra resampling is performed.

For the existing [invented first-and-ten replay](DECISION_CONTRACT.md#reproduce-the-invented-example),
the descriptive contrast is approximately +33.3333 frequency pp, +0.6 EPA/play
and +100 success pp. Those are only differences between three invented rows.
The preferred candidate is null. League comparison there is instead Pass − its
league Pass baseline: −2.4 EPA/play. The two contrasts must never be confused.

This is additive within the offline v1 contract: existing source, candidate,
league and uncertainty fields and the three original abstention fields retain
their values. Exact-key consumers of `comparison` must allow the new documented
fields. Scout schema v2, HTTP output, briefs and downloads do not change.

## Opponent evidence: defer explicitly

`comparison.opponent_evidence` is always
`{"status": "deferred", "reason": "opponent_conditioning_not_validated"}`.
`DecisionRequest` still rejects `opponent` and `side` rather than ignoring them.
This means opponent conditioning is not an admitted decision capability, **not**
that the source lacks defense IDs. No adjustment is hidden in the league baseline.

These are distinct populations, not interchangeable estimates:

- Selected offense across its observed opponents: the current decision cohort.
- Production allowed by a defense against its observed offenses: existing Scout
  defense mode, still offense-relative EPA and EPA > 0 success allowed.
- One offense against one defense: head-to-head history, potentially very few
  games with a different opponent/time/personnel mix.
- A future matchup projection: requires a specified adjustment or outcome model,
  not averaging the offense's production with a defense's allowed production.

The pinned audit found just five CAR late-close-range plays, with Run EPA from
one game and Pass from four. Even its 387-play first-and-ten cohort spans only
17 selected games. These examples motivate caution but do not establish a universal
opponent-sample cutoff. No arbitrary extra minimum or head-to-head filter is
approved by this policy. Existing bootstrap/count gates are not such approval.

Before admitting opponent-specific evidence, record and test:

1. The intended estimand and role: descriptive defense history, head-to-head
   history or a model-based matchup value. Keep their outputs distinct.
2. Exact source, season/type/cutoff/context, opponent identity and baseline
   exclusions, shared-game accounting, missingness and candidate-specific support.
   No silent cross-season pooling, fallback or double-counting shared games.
3. Source/model release evidence and support/overlap diagnostics for both calls
   across relevant contexts/opponents. Label retrospective descriptions as such;
   any decision-time replay must establish availability at that time. Specify
   abstention before inspecting attractive outcomes. A count threshold is not
   evidence of overlap.
4. Independent raw-cohort checks for descriptive evidence; for predictive or
   action-ranking claims, forward-time held-out evaluation against a stated
   baseline, domain/era boundaries and error/calibration analysis as applicable.
   Causal claims additionally require explicit identification assumptions and
   sensitivity analysis; prediction accuracy alone does not identify action effects.

Until those gates are met, use Scout's separate defense description without
promoting it to opponent-conditioned decision evidence. Fourth-down Run/Pass
remains conditional on eligible Run/Pass plays, not go/punt/kick choice. OT remains
a historical selector, not a rules-aware decision model.

## Why abstention is justified; requirements for a future policy

The [pinned nflreadr dictionary](https://github.com/nflverse/nflreadr/blob/dca0b7f6c02f18a4d6e644b03f6d8ec8757d2265/data-raw/dictionary_pbp.csv)
defines possession/defense identity, offense-relative EPA and observed dropbacks
(including sacks/scrambles). It does not certify the coach's intended call. Our
inference is that these labels cannot alone identify interventions such as calling
a specific run concept instead of a pass concept.

Hernán's [methodological overview](https://hsph.harvard.edu/profile/miguel-hernan/)
emphasizes well-defined causal questions and assumptions when interpreting
observational comparisons. Applying that distinction here is **our policy choice**:
unmeasured personnel, defensive response and within-range context differences
remain. Filtering the same ranges does not make calls exchangeable. More data
can reduce sampling variability without removing selection bias.

The model author's [nflfastR methodology](https://opensourcefootball.com/posts/2020-09-28-nflfastr-ep-wp-and-cp-models/)
separates EP/WP state models and expected-dropback tendency and describes
leave-one-season-out evaluation. It does not establish that our observed EPA
contrast predicts the effect of changing a call. Upstream calibration is not a
validation receipt for this policy, newer artifacts or forward-time replay.
No external code, model, raw data or license rights are newly acquired here.

A future preferred-call policy must specify the target (historical description,
forecast or action effect), decision-time inputs and release evidence, permitted
claims, comparator/baseline, loss or utility and abstention criteria. Evaluate
forward-time generalization, relevant error/calibration and coverage, sparse/
out-of-domain states, model/source uncertainty, and multiplicity from exploring
many situations. A historical maximum mean, baseline-adjusted difference or
nominal interval excluding zero is not a shortcut. No "evidence favors", winner
badge, numeric confidence score or coaching recommendation is authorized now.

## Verification and next boundary

`tests/test_decision_policy.py` uses hand-calculated and exact-rational invented
examples for signs/units, unequal/missing denominators, empty/absent/missing
reasons, thresholds, league isolation, non-overlapping intervals, cutoffs/context,
OT/fourth-down selection, unsupported inputs and deterministic isolated output.
The existing raw audit's frozen receipt continues to check its original field
subset; it is not relabeled as a fingerprint of these new policy fields.

Run the synthetic contract checks with no downloads:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_decision*.py' -v
```

To independently replay the 24 new contrast values on the same eight pinned
cohorts, reuse the repository-only raw-record oracle (not production metrics):

```sh
PYTHONPATH=src python3 - <<'PY'
from decimal import localcontext
from pathlib import Path
from unittest.mock import patch
from opponent_intelligence.decision import DecisionRequest, build_decision_evidence
from validation import decision_audit as audit

directory = Path('data/raw/nflverse/pbp/2024') / audit.ARCHIVE_SHA256
with patch('socket.create_connection', side_effect=AssertionError('no network')), localcontext() as ctx:
    ctx.prec = 50
    audit.audit_snapshot(directory)  # Verifies both pinned hashes and original checks.
    raw, manifest = audit._read_snapshot(directory)
    dataset = audit._snapshot_dataset(raw, manifest)
    rows = audit.raw_eligible(raw)
    for name, options in audit.CASES:
        request = DecisionRequest(**(dict(team='CAR', season=2024, before_week=19,
            down=1, distance_min=10, distance_max=10) | options))
        team = [r for r in rows if r['posteam'] == request.team and r['season'] == request.season
                and r['season_type'] == request.season_type and r['week'] < request.before_week]
        selected, _ = audit.raw_context(team, request)
        expected = audit.differences(audit.ratios(selected, 'pass'), audit.ratios(selected, 'run'))
        comparison = build_decision_evidence(dataset, request, source_label='Retrospective audit')['comparison']
        for key, value in zip(audit.DIFFERENCES, expected):
            audit.check(comparison['descriptive_contrast']['metrics'][key]['value'],
                        None if value is None else float(value), name + '.' + key)
        assert comparison['preferred_candidate'] is None
        assert comparison['opponent_evidence']['status'] == 'deferred'
print('Eight cases / 24 contrast values match; no preferred call.')
PY
```

This additional check does not change the original frozen receipt or establish
calibration, causal effects or decision quality. Source terms and retrieval limits
remain those of [the original audit](DECISION_AUDIT.md).

P1.5 is complete **within descriptive-only scope**, with preferred calls and
opponent conditioning explicitly deferred. Next: P1.6's first bounded,
version-pinned nfl4th input/output, license, assumptions and historical-availability
audit, building on the [initial desk review](DECISION_INTELLIGENCE.md). Decide
reuse/adapt/defer with evidence before installing/converting or serving any model.
Richer sources, model integration and Decision Lab API/UI remain separate units.
