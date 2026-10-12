import { number, type FieldPositionCounts, type Report } from './report';

export function FieldPositionView({ report }: { report: Report }) {
  const field = report.cohort.field_position;
  if (!field) return <p className="muted">Field position: unrestricted; missing positions are not excluded by field position.</p>;
  const rows: [string, FieldPositionCounts][] = [['Selected cohort', report.data_quality.field_position_filter!]];
  if (report.league_comparison) rows.push(['Other teams baseline', report.league_comparison.data_quality.field_position_filter!]);
  return <section className="panel field-position" aria-labelledby="field-position-title">
    <div className="section-heading"><h3 id="field-position-title">Pre-play field position</h3><span>Returned filter · inclusive</span></div>
    <p><strong>{field.minimum_inclusive}–{field.maximum_inclusive} yards to the offense’s opponent’s goal line</strong>.</p>
    <p>Coordinates stay offense-relative in either role: 20 means the opponent’s 20-yard line, 80 the offense’s own 20.
      The target is the defending team’s goal line on each play, including baseline plays. This is a play cohort, not a drive-level red-zone efficiency statistic.</p>
    <p>Filter order: team / role / season / exclusive week cutoff → field position.
      Missing positions are excluded, not imputed. Before = missing + outside + retained, separately for each population.</p>
    <p className="table-hint muted">Scroll the accounting table horizontally to read all columns.</p>
    <div className="table-scroll" role="region" tabIndex={0} aria-label="Field-position accounting, scroll horizontally on small screens">
      <table><caption className="sr-only">Field-position exclusions after team and time selection</caption>
        <thead><tr><th scope="col">Population</th><th scope="col">Before filter</th><th scope="col">Missing position</th>
          <th scope="col">Outside range</th><th scope="col">{report.cohort.score_differential ? 'After field filter' : 'Retained plays'}</th></tr></thead>
        <tbody>{rows.map(([label, q]) => <tr key={label}><th scope="row">{label}</th>
          <td>{number(q.plays_before_filter)}</td><td>{number(q.missing_yardline_100)}</td>
          <td>{number(q.outside_range)}</td><td>{number(q.plays_after_filter)}</td></tr>)}</tbody>
      </table>
    </div>
    <p className="muted">{report.cohort.score_differential
      ? 'After field filter is an intermediate count, passed to the score stage below. Metrics and game/team coverage use only final survivors.'
      : 'All metrics and game/team coverage below use retained plays.'} Missing EPA is counted separately.
      Selected-cohort exclusions are already in the global outside-cohort count; do not add stage losses to it again.</p>
  </section>;
}
