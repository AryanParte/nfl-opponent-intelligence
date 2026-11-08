import type { Decision } from './decision';
import { number } from './report';

/** This view's only optional context is field position; down and distance always follow. */
export function DecisionFieldPositionView({ decision }: { decision: Decision }) {
  const field = decision.cohort.field_position;
  if (!field) return <p className="muted">Field position: unrestricted; missing positions are not excluded by field position.</p>;
  const quality = decision.data_quality;
  const rows = [
    { label: 'Field position', counts: quality.field_position_filter!, missing: 'missing_yardline_100' },
    { label: 'Down', counts: quality.down_filter!, missing: 'missing_down' },
    { label: 'Distance', counts: quality.distance_filter!, missing: 'missing_yards_to_go' },
  ];
  return <section className="panel field-position" aria-labelledby="decision-field-position-title">
    <div className="section-heading"><h3 id="decision-field-position-title">Pre-play field position</h3><span>Returned filter · inclusive</span></div>
    <p><strong>{field.minimum_inclusive}–{field.maximum_inclusive} yards to the offense’s opponent’s goal line</strong>.</p>
    <p>20 means the opponent’s 20-yard line; 80 means the offense’s own 20.
      This is a play cohort, not a drive-level red-zone efficiency statistic.</p>
    <p>Selected offense / season / exclusive week cutoff → field position → down → distance.
      Each stage starts with the preceding stage’s retained plays. Missing positions are excluded, not imputed.
      Down and distance are required at ingestion, so their missing counts are zero here.</p>
    <p className="table-hint muted">Scroll the accounting table horizontally to read all columns.</p>
    <div className="table-scroll" role="region" tabIndex={0} aria-label="Decision filter accounting, scroll horizontally on small screens">
      <table><caption className="sr-only">Selected offense exclusions after season and exclusive week cutoff</caption>
        <thead><tr><th scope="col">Stage</th><th scope="col">Before filter</th><th scope="col">Missing value</th>
          <th scope="col">Outside range</th><th scope="col">After filter</th></tr></thead>
        <tbody>{rows.map(({ label, counts, missing }) => <tr key={label}><th scope="row">{label}</th>
          <td>{number(counts.plays_before_filter)}</td><td>{number(counts[missing])}</td>
          <td>{number(counts.outside_range)}</td><td>{number(counts.plays_after_filter)}</td>
        </tr>)}</tbody>
      </table>
    </div>
    <p className="muted">Field-position and down counts are intermediate. Candidate metrics and games use only final distance-stage survivors.
      Missing EPA is counted separately. Stage exclusions already belong to the global outside-cohort count; do not add them again.</p>
  </section>;
}
