import type { Candidate, Decision } from './decision';
import { number } from './report';
import { IntervalCells, intervalPopulations } from './IntervalCells';

type Row = NonNullable<Decision['uncertainty']>['candidates'][number];
type Baseline = NonNullable<Decision['league_comparison']>['candidates'][number];
const metrics = [
  ['frequency', 'frequency_pp', 'Call frequency'],
  ['success_rate', 'success_rate_pp', 'Offensive success (EPA > 0)'],
  ['epa_per_play', 'epa_per_play', 'EPA / observed play'],
] as const;
function CandidateIntervals({ row, selected, baseline }: { row: Row; selected: Candidate; baseline?: Baseline }) {
  const label = row.candidate === 'run' ? 'Run' : 'Pass';
  return <div className="table-scroll" role="region" tabIndex={0} aria-label={`${label} uncertainty, scroll horizontally on small screens`}>
    <table className="uncertainty-table"><caption className="sr-only">{label} point estimates, exploratory intervals and per-metric game support</caption>
      <thead><tr><th scope="col">Population / metric</th><th scope="col">Point estimate</th><th scope="col">Nominal 95% bounds</th>
        <th scope="col">Contributing games</th><th scope="col">Defined / undefined draws</th><th scope="col">Interval status</th></tr></thead>
      <tbody>{(['selected', 'baseline', 'difference'] as const).flatMap(population => {
        if (!row[population]) return [];
        return metrics.map(([metric, difference, label]) => {
          const item = population === 'difference' ? row.difference![difference] : row[population]![metric];
          const point = population === 'difference' ? baseline!.difference[difference] : (population === 'selected' ? selected : baseline!)[metric];
          return <tr key={`${population}:${metric}`}><th scope="row">{intervalPopulations[population]} / {label}</th>
            <IntervalCells point={point} item={item} /></tr>;
        });
      })}</tbody>
    </table>
  </div>;
}
export function DecisionUncertaintyView({ decision }: { decision: Decision }) {
  const u = decision.uncertainty;
  if (!u) return null;
  return <section className="panel uncertainty" aria-labelledby="decision-uncertainty-title">
    <div className="section-heading"><h3 id="decision-uncertainty-title">Candidate game support and exploratory uncertainty</h3>
      <span>Requested · not calibrated confidence</span></div>
    <p>Whole-game percentile bootstrap · nominal 95%, pointwise, not simultaneous across findings.
      These intervals are not significance tests, predictions, opponent adjustment or a preferred-call rule.</p>
    <p><strong>{number(u.performed_repetitions)} / {number(u.repetitions)} performed / requested draws</strong> · seed {u.seed}
      {' · '}{number(u.resampling_games)} games in the {u.shared_game_weights ? 'selected + baseline union; shared game weights' : 'selected-only resampling frame'}.</p>
    <p>Both calls use the same game draws, including games with no observations of a call.
      {' '}{u.shared_game_weights ? 'Selected and baseline also share those weights. Turning comparison on changes the frame and can change selected bounds without changing point estimates.'
        : 'League comparison was not requested; shared weights still apply across Run and Pass.'}
      {' '}An empty frame performs zero draws. More draws add computation, not observed games.</p>
    <p>Frequency support counts all parent-cohort games, even those without this call.
      Success/EPA support counts only games with observed EPA for this call. Neither necessarily equals the candidate games in the point-evidence table.
      A missing outcome stays unavailable; an unobserved call in a nonempty parent has zero frequency, not proof it is never called.</p>
    <p>Intervals require at least 5 contributing games on every required side and 95% defined draws; below 20 games is flagged separately.
      These are application safeguards, not reliability guarantees. Withheld bounds do not mean zero uncertainty.
      Point estimates remain visible when only the interval is withheld.</p>
    <p>Rate bounds are percentages; difference bounds are selected minus the same baseline call in percentage points (pp), or EPA/play.
      Paired differences are computed within each draw, never by subtracting marginal bounds.
      No Pass-minus-Run contrast interval is implemented. Neither interval overlap nor non-overlap selects a preferred call.
      Rounded endpoints can look equal despite a nonzero unrounded width.</p>
    <p className="table-hint muted">Scroll interval tables horizontally to read support, draw counts and status.</p>
    {u.candidates.map(row => <section key={row.candidate} aria-labelledby={`decision-${row.candidate}-uncertainty-title`}>
      <h4 id={`decision-${row.candidate}-uncertainty-title`}>{row.candidate === 'run' ? 'Run' : 'Pass'} intervals and support</h4>
      <CandidateIntervals row={row} selected={decision.candidates.find(candidate => candidate.candidate === row.candidate)!}
        baseline={decision.league_comparison?.candidates.find(candidate => candidate.candidate === row.candidate)} />
    </section>)}
    <details><summary>Decision uncertainty method and replay metadata</summary><dl>
      <dt>Method / unit</dt><dd>{u.method} / {u.resampling_unit}</dd>
      <dt>Random generator / quantile</dt><dd>{u.random_generator} / {u.quantile_method}</dd>
    </dl><p>Replay also requires the exact cohort, immutable source fingerprints and supported Python runtime.
      The browser validates returned metadata; it does not resample or certify statistical coverage.</p></details>
    <div className="comparison-warnings"><h4>Candidate uncertainty limitations</h4>
      <ul>{u.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></div>
  </section>;
}
