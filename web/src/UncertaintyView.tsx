import { epa, number, percentage, signedDifference, type Difference, type Metrics, type Report } from './report';
import { intervalMetrics, type IntervalRow, type IntervalSummary } from './uncertainty';

const metricLabels = ['Dropback rate', 'Offensive success', 'EPA / observed play'];
const populations = { selected: 'Selected', baseline: 'Baseline', difference: 'Selected − baseline' };
const statuses: Record<IntervalSummary['status'], string> = {
  ok: 'Available · exploratory', undefined_estimate: 'Undefined estimate · no contributing games',
  insufficient_games: 'Withheld · fewer than 5 contributing games',
  too_few_valid_replicates: 'Withheld · fewer than 95% defined draws',
  degenerate_interval: 'Withheld · constant / near-constant interval',
};
export const intervalValue = (value: number | null, unit: IntervalSummary['unit']) => value === null ? 'Unavailable'
  : unit === 'proportion' ? percentage(value) : unit === 'percentage_points' ? signedDifference(value, 'pp') : `${epa(value)} EPA/play`;

function IntervalTable({ row, selected, baseline, difference, label }: {
  row: IntervalRow; selected: Metrics; baseline?: Metrics; difference?: Difference; label: string;
}) {
  return <div className="table-scroll" role="region" tabIndex={0} aria-label={`${label}, scroll horizontally on small screens`}>
    <table className="uncertainty-table"><caption className="sr-only">{label}</caption>
      <thead><tr><th scope="col">Population / metric</th><th scope="col">Point estimate</th><th scope="col">Nominal 95% bounds</th>
        <th scope="col">Contributing games</th><th scope="col">Defined / undefined draws</th><th scope="col">Interval status</th></tr></thead>
      <tbody>{(Object.keys(populations) as (keyof typeof populations)[]).flatMap(population => {
        const entries = row[population];
        if (!entries) return [];
        return intervalMetrics.map((metric, i) => {
          const key = population === 'difference' && i < 2 ? `${metric}_pp` : metric;
          const item = (entries as Record<string, IntervalSummary>)[key];
          const point = population === 'difference' ? difference![key as keyof Difference]
            : (population === 'selected' ? selected : baseline!)[metric];
          return <tr key={`${population}:${metric}`}><th scope="row">{populations[population]} / {metricLabels[i]}</th>
            <td>{intervalValue(point, item.unit)}</td>
            <td>{item.interval ? `${intervalValue(item.interval.lower, item.unit)} to ${intervalValue(item.interval.upper, item.unit)}`
              : item.status === 'undefined_estimate' ? 'Unavailable' : 'Withheld'}</td>
            <td>{Object.entries(item.support_games).map(([side, n]) => `${populations[side as 'selected' | 'baseline']} ${number(n!)}`).join(' · ')}
              <small>{item.few_games ? 'Few games (<20 on a required side)' : 'No few-game flag; not a reliability guarantee'}</small></td>
            <td>{number(item.valid_replicates)} / {number(item.undefined_replicates)}</td><td>{statuses[item.status]}</td></tr>;
        });
      })}</tbody>
    </table>
  </div>;
}

export function UncertaintyView({ report }: { report: Report }) {
  const u = report.uncertainty;
  if (!u) return null;
  const selected = new Map(report.situations.map(row => [`${row.down}:${row.distance}`, row]));
  const baseline = new Map(report.league_comparison?.situations.map(row => [`${row.down}:${row.distance}`, row]));
  return <section className="panel uncertainty" aria-labelledby="uncertainty-title">
    <div className="section-heading"><h3 id="uncertainty-title">Exploratory game-level uncertainty</h3><span>Requested · not calibrated confidence</span></div>
    <p>Whole-game percentile bootstrap · nominal 95%, pointwise, not simultaneous across findings.
      These bounds are not significance tests, opponent adjustment or predictions. No browser resampling or endpoint subtraction.</p>
    <p><strong>{number(u.performed_repetitions)} / {number(u.repetitions)} performed / requested draws</strong> · seed {u.seed}
      {' · '}{number(u.resampling_games)} games in the {u.shared_game_weights ? 'selected + baseline union; shared game weights' : 'selected-only resampling frame'}.</p>
    <p>{u.shared_game_weights ? 'Selected and baseline use the same game draws. Differences are formed inside each paired draw; turning comparison on changes the frame and can change selected bounds.'
      : 'Only selected-cohort games are resampled; league comparison was not requested.'}
      {' '}An empty frame performs zero draws. More draws do not add observed games.</p>
    <p>Support counts distinct games with eligible plays for dropbacks, and with observed EPA for success/EPA.
      Intervals require at least 5 games on every required side and 95% defined draws; below 20 games is flagged separately.
      These are application safeguards, not reliability guarantees. Withheld bounds are not zero uncertainty or certainty.
      Point estimates remain available when only an interval is withheld.</p>
    <p>Percent bounds are rates; pp bounds are selected-minus-baseline percentage points. EPA keeps its offensive sign in defense mode.
      Values are rounded for display; equal displayed endpoints can hide a nonzero unrounded width.</p>
    <p className="table-hint muted">Scroll interval tables horizontally to read support, draw counts and status.</p>
    <h4>Overall intervals and support</h4>
    <IntervalTable row={u.overall} selected={report.overall} baseline={report.league_comparison?.overall}
      difference={report.league_comparison?.overall_difference} label="Overall uncertainty" />
    <h4>Situation intervals and support</h4>
    <p>Only selected-team observed buckets are listed. Each uses its own support; missing baseline buckets never borrow overall support.</p>
    {u.situations.length === 0 && <p>No selected-team situation intervals.</p>}
    {u.situations.map(row => {
      const key = `${row.down}:${row.distance}`, match = baseline.get(key);
      return <details key={key}><summary>{row.down} / {row.distance} · interval support</summary>
        <IntervalTable row={row} selected={selected.get(key)!} baseline={match?.baseline} difference={match?.difference}
          label={`${row.down} / ${row.distance} uncertainty`} /></details>;
    })}
    <details><summary>Method and replay metadata</summary><dl>
      <dt>Method / unit</dt><dd>{u.method} / {u.resampling_unit}</dd>
      <dt>Random generator / quantile</dt><dd>{u.random_generator} / {u.quantile_method}</dd>
    </dl><p>Replay also needs the cohort options, immutable source fingerprints and supported Python runtime.
      The browser checks the returned contract, not the resampled distribution or statistical coverage.</p></details>
    <div className="comparison-warnings"><h4>Uncertainty limitations</h4>
      <ul>{u.warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul></div>
  </section>;
}
