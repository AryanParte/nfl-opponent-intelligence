import { number, type Report, type ScoreCounts } from './report';

const points = (value: number) => `${value > 0 ? '+' : ''}${value}`;

export function ScoreView({ report }: { report: Report }) {
  const score = report.cohort.score_differential;
  if (!score) return <p className="muted">Pre-play score: unrestricted; no score-based exclusions.</p>;
  const { minimum_inclusive: lower, maximum_inclusive: upper } = score;
  const range = lower === null ? `At most ${points(upper!)} points`
    : upper === null ? `At least ${points(lower)} points` : `${points(lower)} to ${points(upper)} points`;
  const rows: [string, ScoreCounts][] = [['Selected cohort', report.data_quality.score_differential_filter!]];
  if (report.league_comparison) rows.push(['Other teams baseline', report.league_comparison.data_quality.score_differential_filter!]);
  return <section className="panel field-position" aria-labelledby="score-title">
    <div className="section-heading"><h3 id="score-title">Pre-play score difference</h3><span>Returned filter · inclusive</span></div>
    <p><strong>{range}</strong> · offense points minus defense points before the play. A blank end remains unbounded, not zero.</p>
    <p>Negative means the offense is trailing; positive means it is leading; 0 is a known tie, not a missing score.
      For a selected defense, -7 means the opposing offense trails that defense by 7. Baseline plays use their own offense’s perspective too.
      No sign reversal or post-play score substitution. This range is not a neutral-game or win-probability definition.</p>
    <p>Filter order: team / role / season / exclusive week cutoff → {report.cohort.field_position && 'field position → '}pre-play score.
      Missing scores are excluded, not imputed. Before = missing + outside + retained, separately for each population.</p>
    {report.cohort.field_position && <p>Before score = after field position. Missing score counts describe only field-position survivors;
      a play missing both fields is removed at the field stage, not counted twice.</p>}
    <p className="table-hint muted">Scroll the accounting table horizontally to read all columns.</p>
    <div className="table-scroll" role="region" tabIndex={0} aria-label="Pre-play score accounting, scroll horizontally on small screens">
      <table><caption className="sr-only">Pre-play score exclusions after earlier selection stages</caption>
        <thead><tr><th scope="col">Population</th><th scope="col">Before score</th><th scope="col">Missing score</th>
          <th scope="col">Outside range</th><th scope="col">{report.cohort.period ? 'After score filter' : 'Final retained plays'}</th></tr></thead>
        <tbody>{rows.map(([label, q]) => <tr key={label}><th scope="row">{label}</th>
          <td>{number(q.plays_before_filter)}</td><td>{number(q.missing_score_differential)}</td>
          <td>{number(q.outside_range)}</td><td>{number(q.plays_after_filter)}</td></tr>)}</tbody>
      </table>
    </div>
    <p className="muted">{report.cohort.period
      ? 'After score filter is intermediate, passed to period selection below. Metrics and game/team coverage use only final survivors.'
      : 'All metrics and game/team coverage below use final retained plays.'} Missing EPA is counted separately.
      Selected-cohort stage exclusions are already in the global outside-cohort count; do not add them again.</p>
  </section>;
}
