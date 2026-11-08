import type { Decision } from './decision';
import { number, scoreRange } from './report';

/** Only field and score are exposed here; down and distance always follow. */
export function DecisionContextView({ decision }: { decision: Decision }) {
  const { field_position: field, score_differential: score } = decision.cohort;
  const unrestrictedField = <p className="muted">Field position: unrestricted; missing positions are not excluded by field position.</p>;
  const unrestrictedScore = <p className="muted">Pre-play score: unrestricted; missing scores are not excluded by score.</p>;
  if (!field && !score) return <>{unrestrictedField}{unrestrictedScore}</>;
  const quality = decision.data_quality;
  const rows = [
    ...(field ? [{ label: 'Field position', counts: quality.field_position_filter!, missing: 'missing_yardline_100' }] : []),
    ...(score ? [{ label: 'Pre-play score', counts: quality.score_differential_filter!, missing: 'missing_score_differential' }] : []),
    { label: 'Down', counts: quality.down_filter!, missing: 'missing_down' },
    { label: 'Distance', counts: quality.distance_filter!, missing: 'missing_yards_to_go' },
  ];
  return <section className="panel field-position" aria-labelledby="decision-context-title">
    <div className="section-heading"><h3 id="decision-context-title">Situation filters</h3><span>Returned filters · inclusive</span></div>
    {field ? <><h4>Pre-play field position</h4>
    <p><strong>{field.minimum_inclusive}–{field.maximum_inclusive} yards to the offense’s opponent’s goal line</strong>.</p>
    <p>20 means the opponent’s 20-yard line; 80 means the offense’s own 20.
      This is a play cohort, not a drive-level red-zone efficiency statistic.</p></> : unrestrictedField}
    {score ? <><h4>Pre-play score difference</h4>
      <p><strong>{scoreRange(score)}</strong> · offense points minus defense points before the play. A blank end remains unbounded, not zero.</p>
      <p>Negative means the offense is trailing; positive means it is leading; 0 is a known tie, not a missing score.
        No post-play score substitution. This range is not a neutral-game or win-probability definition.</p>
    </> : unrestrictedScore}
    <p>Selected offense / season / exclusive week cutoff → {field && 'field position → '}{score && 'pre-play score → '}down → distance.
      Each stage starts with the preceding stage’s retained plays. Requested missing context is excluded, not imputed.
      Down and distance are required at ingestion, so their missing counts are zero here.</p>
    {field && score && <p>Before score = after field position. Missing score counts describe only field-position survivors;
      a play missing both fields is removed at the field stage, not counted twice.</p>}
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
    <p className="muted">Counts before the final distance stage are intermediate. Candidate metrics and games use only final distance-stage survivors.
      Missing EPA is counted separately. Stage exclusions already belong to the global outside-cohort count; do not add them again.</p>
  </section>;
}
