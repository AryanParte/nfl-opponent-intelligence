import type { Decision } from './decision';
import { number, type Contexts } from './report';

/** Both populations have the same validated filter sequence, but different counts. */
export function DecisionFilterTable({ cohort, quality, baseline = false }: {
  cohort: Contexts;
  quality: Decision['data_quality'] | NonNullable<Decision['league_comparison']>['data_quality'];
  baseline?: boolean;
}) {
  const { field_position: field, score_differential: score, period, clock } = cohort;
  const rows = [
    ...(field ? [{ label: 'Field position', counts: quality.field_position_filter!, missing: 'missing_yardline_100', outside: 'outside_range' }] : []),
    ...(score ? [{ label: 'Pre-play score', counts: quality.score_differential_filter!, missing: 'missing_score_differential', outside: 'outside_range' }] : []),
    ...(period ? [{ label: 'Period', counts: quality.period_filter!, missing: 'missing_qtr', outside: 'outside_period' }] : []),
    ...(clock ? [{ label: 'Clock', counts: quality.clock_filter!, missing: 'missing_quarter_seconds_remaining', outside: 'outside_range' }] : []),
    { label: 'Down', counts: quality.down_filter!, missing: 'missing_down', outside: 'outside_range' },
    { label: 'Distance', counts: quality.distance_filter!, missing: 'missing_yards_to_go', outside: 'outside_range' },
  ];
  return (
    <div className="table-scroll" role="region" tabIndex={0} aria-label={`${baseline ? 'Baseline' : 'Decision'} filter accounting, scroll horizontally on small screens`}>
      <table><caption className="sr-only">{baseline ? 'Other offenses exclusions after season, exclusive week cutoff and selected-team removal' : 'Selected offense exclusions after season and exclusive week cutoff'}</caption>
        <thead><tr><th scope="col">Stage</th><th scope="col">Before filter</th><th scope="col">Missing value</th>
          <th scope="col">Outside filter</th><th scope="col">After filter</th></tr></thead>
        <tbody>{rows.map(({ label, counts, missing, outside }) => <tr key={label}><th scope="row">{label}</th>
          <td>{number(counts.plays_before_filter)}</td><td>{number(counts[missing])}</td>
          <td>{number(counts[outside])}</td><td>{number(counts.plays_after_filter)}</td>
        </tr>)}</tbody>
      </table>
    </div>
  );
}
