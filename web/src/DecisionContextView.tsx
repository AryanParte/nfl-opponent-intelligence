import type { Decision } from './decision';
import { number, scoreRange } from './report';

/** Show returned context stages in selection order; final distance survivors feed metrics. */
export function DecisionContextView({ decision }: { decision: Decision }) {
  const { field_position: field, score_differential: score, period, clock } = decision.cohort;
  const unrestrictedField = <p className="muted">Field position: unrestricted; missing positions are not excluded by field position.</p>;
  const unrestrictedScore = <p className="muted">Pre-play score: unrestricted; missing scores are not excluded by score.</p>;
  const unrestrictedTime = <p className="muted">Period and clock: unrestricted; no time-context exclusions.</p>;
  if (!field && !score && !period) return <>{unrestrictedField}{unrestrictedScore}{unrestrictedTime}</>;
  const quality = decision.data_quality;
  const rows = [
    ...(field ? [{ label: 'Field position', counts: quality.field_position_filter!, missing: 'missing_yardline_100', outside: 'outside_range' }] : []),
    ...(score ? [{ label: 'Pre-play score', counts: quality.score_differential_filter!, missing: 'missing_score_differential', outside: 'outside_range' }] : []),
    ...(period ? [{ label: 'Period', counts: quality.period_filter!, missing: 'missing_qtr', outside: 'outside_period' }] : []),
    ...(clock ? [{ label: 'Clock', counts: quality.clock_filter!, missing: 'missing_quarter_seconds_remaining', outside: 'outside_range' }] : []),
    { label: 'Down', counts: quality.down_filter!, missing: 'missing_down', outside: 'outside_range' },
    { label: 'Distance', counts: quality.distance_filter!, missing: 'missing_yards_to_go', outside: 'outside_range' },
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
    {period ? <><h4>Pre-play period &amp; clock</h4>
      <p><strong>{period.label === 'OT' ? 'OT — all periods numbered 5 or higher' : period.label}</strong>.
        {clock ? <> <strong>{clock.minimum_inclusive}–{clock.maximum_inclusive} seconds remaining at play start</strong>, inclusive.</>
          : ' Clock unrestricted: period selection alone does not exclude missing clocks.'}</p>
      <p>Q4 excludes overtime, even at the same clock value. Q4 0–120 is not a definition of the last two minutes of a game.
        OT bounds apply within each overtime period, not to cumulative overtime time. The 0–900 input limit does not certify season-specific overtime rules.</p>
    </> : unrestrictedTime}
    <p>Selected offense / season / exclusive week cutoff → {field && 'field position → '}{score && 'pre-play score → '}{period && 'period → '}{clock && 'clock → '}down → distance.
      Each stage starts with the preceding stage’s retained plays. Requested missing context is excluded, not imputed.
      Down and distance are required at ingestion, so their missing counts are zero here.</p>
    {field && score && <p>Before score = after field position. Missing score counts describe only field-position survivors;
      a play missing both fields is removed at the field stage, not counted twice.</p>}
    {period && <p>Period counts describe only survivors of earlier requested filters.
      Missing period means unknown, not overtime. {clock ? 'Clock counts describe period survivors; a play missing both period and clock is removed at period, not counted twice.'
        : 'No clock stage was requested; missing clocks can remain.'}
      {' '}Zero seconds is observed, not missing. No substitution from elapsed, half/game clocks or later outcomes.</p>}
    <p className="table-hint muted">Scroll the accounting table horizontally to read all columns.</p>
    <div className="table-scroll" role="region" tabIndex={0} aria-label="Decision filter accounting, scroll horizontally on small screens">
      <table><caption className="sr-only">Selected offense exclusions after season and exclusive week cutoff</caption>
        <thead><tr><th scope="col">Stage</th><th scope="col">Before filter</th><th scope="col">Missing value</th>
          <th scope="col">Outside filter</th><th scope="col">After filter</th></tr></thead>
        <tbody>{rows.map(({ label, counts, missing, outside }) => <tr key={label}><th scope="row">{label}</th>
          <td>{number(counts.plays_before_filter)}</td><td>{number(counts[missing])}</td>
          <td>{number(counts[outside])}</td><td>{number(counts.plays_after_filter)}</td>
        </tr>)}</tbody>
      </table>
    </div>
    <p className="muted">Counts before the final distance stage are intermediate. Candidate metrics and games use only final distance-stage survivors.
      Missing EPA is counted separately. Stage exclusions already belong to the global outside-cohort count; do not add them again.</p>
  </section>;
}
