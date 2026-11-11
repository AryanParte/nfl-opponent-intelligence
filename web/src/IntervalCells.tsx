import { epa, number, percentage, signedDifference } from './report';
import type { IntervalSummary } from './uncertainty';

export const intervalPopulations = { selected: 'Selected', baseline: 'Baseline', difference: 'Selected − baseline' };
const statuses: Record<IntervalSummary['status'], string> = {
  ok: 'Available · exploratory', undefined_estimate: 'Undefined estimate · no contributing games',
  insufficient_games: 'Withheld · fewer than 5 contributing games',
  too_few_valid_replicates: 'Withheld · fewer than 95% defined draws',
  degenerate_interval: 'Withheld · constant / near-constant interval',
};
export const intervalValue = (value: number | null, unit: IntervalSummary['unit']) => value === null ? 'Unavailable'
  : unit === 'proportion' ? percentage(value) : unit === 'percentage_points' ? signedDifference(value, 'pp') : `${epa(value)} EPA/play`;

/** Present returned estimates and interval evidence; never calculate bounds. */
export function IntervalCells({ point, item }: { point: number | null; item: IntervalSummary }) {
  return <>
    <td>{intervalValue(point, item.unit)}</td>
    <td>{item.interval ? `${intervalValue(item.interval.lower, item.unit)} to ${intervalValue(item.interval.upper, item.unit)}`
      : item.status === 'undefined_estimate' ? 'Unavailable' : 'Withheld'}</td>
    <td>{Object.entries(item.support_games).map(([side, n]) => `${intervalPopulations[side as 'selected' | 'baseline']} ${number(n!)}`).join(' · ')}
      <small>{item.few_games ? 'Few games (<20 on a required side)' : 'No few-game flag; not a reliability guarantee'}</small></td>
    <td>{number(item.valid_replicates)} / {number(item.undefined_replicates)}</td><td>{statuses[item.status]}</td>
  </>;
}
