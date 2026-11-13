import type { Call, Candidate, Decision } from './decision';
import { signedDifference } from './report';

const unavailable: Record<Exclude<Candidate['availability']['outcomes'], 'available'>, string> = {
  empty_cohort: 'selected cohort is empty',
  unobserved_candidate: 'no observed plays of this call',
  missing_epa: 'EPA missing for every observed play of this call',
};
const metrics = [
  ['frequency_pp', 'Call frequency', 'pp'],
  ['epa_per_play', 'EPA / observed play', 'EPA/play'],
  ['success_rate_pp', 'Offensive success (EPA > 0)', 'pp'],
] as const;

export function DecisionContrastView({ decision, choice }: { decision: Decision; choice: Call | null }) {
  const contrast = decision.comparison.descriptive_contrast;
  return <section className="panel comparison" aria-labelledby="decision-contrast-title">
    <div className="section-heading"><h3 id="decision-contrast-title">Run vs Pass: descriptive contrast</h3><span>Selected offense only</span></div>
    <p>{choice ? <>Your choice: <strong>{choice === 'run' ? 'Run' : 'Pass'}</strong>. Alternative: <strong>{choice === 'run' ? 'Pass' : 'Run'}</strong>.</>
      : 'No call selected. Both options remain available for inspection.'}</p>
    <p>Direction stays <strong>Pass − Run</strong> regardless of your choice. Positive means Pass is numerically higher;
      negative means Run is higher. Values are rounded, so a displayed zero can hide a small difference.
      None establishes a better call or grades your choice.</p>
    <p className="muted">Frequency uses the same eligible-play denominator for both calls, including missing EPA.
      Outcome differences use each call’s observed EPA denominator, shown above. pp means percentage points, not percent change.
      These are returned differences from unrounded estimates; subtracting rounded cells can differ.</p>
    <p className="table-hint muted">Scroll the contrast table horizontally to read all columns.</p>
    <div className="table-scroll" role="region" tabIndex={0} aria-label="Pass minus Run descriptive contrast, scroll horizontally on small screens">
      <table className="comparison-table"><caption className="sr-only">Selected offense: Pass minus Run descriptive differences</caption>
        <thead><tr><th scope="col">Metric</th><th scope="col">Pass − Run</th><th scope="col">Evidence state</th></tr></thead>
        <tbody>{metrics.map(([key, label, unit]) => {
          const metric = contrast.metrics[key];
          return <tr key={key}><th scope="row">{label}</th><td>{signedDifference(metric.value, unit)}</td>
            <td>{metric.status === 'available' ? 'Descriptive estimate' : 'Unavailable'}
              {(['run', 'pass'] as const).map(call => {
                const reason = metric.unavailable_candidates[call];
                return reason && reason !== 'available' ? <small key={call}>{call === 'run' ? 'Run' : 'Pass'}: {unavailable[reason]}.</small> : null;
              })}
            </td></tr>;
        })}</tbody>
      </table>
    </div>
    <p><strong>Pass-minus-Run interval: not implemented.</strong> Individual-candidate and selected-minus-league intervals, when requested,
      are different estimates. They do not supply an interval for this contrast.</p>
    <p>The calls occurred on different plays; matching these situation filters does not remove selection bias or unmeasured context.
      Missing differences stay unavailable, with no substitution from league evidence. No preferred call is selected.</p>
  </section>;
}
