import type { Candidate, Decision } from './decision';
import { epa, number, percentage, signedDifference } from './report';
import { DecisionFilterTable } from './DecisionFilterTable';

type Baseline = NonNullable<Decision['league_comparison']>;
const states: Record<Candidate['availability']['outcomes'], string> = {
  available: 'Observed EPA available',
  empty_cohort: 'Empty cohort: frequency and outcomes unavailable',
  unobserved_candidate: 'Call unobserved: frequency is zero; outcomes unavailable',
  missing_epa: 'EPA missing for every observed play of this call: outcomes unavailable',
};
function Counts({ candidate, label }: { candidate: Candidate; label: string }) {
  return <p className="comparison-counts"><strong>{label}:</strong> {number(candidate.plays)} plays / {number(candidate.games)} games
    {' · '}{number(candidate.epa_observations)} EPA observed / {number(candidate.missing_epa)} missing
    {' · '}{candidate.small_sample ? 'Few plays' : 'No play-count flag'}
    {' · '}{candidate.small_epa_sample ? 'Few EPA observations' : 'No EPA-count flag'}.
    {' '}{states[candidate.availability.outcomes]}.</p>;
}
function CandidateComparison({ selected, baseline }: { selected: Candidate; baseline: Baseline['candidates'][number] }) {
  const label = baseline.candidate === 'run' ? 'Run' : 'Pass';
  return <section aria-labelledby={`decision-${baseline.candidate}-comparison-title`}>
    <h4 id={`decision-${baseline.candidate}-comparison-title`}>{label} compared with other offenses</h4>
    <Counts candidate={selected} label={`Selected ${label}`} /><Counts candidate={baseline} label={`Baseline ${label}`} />
    <p className="comparison-counts">Baseline {label} coverage: {number(baseline.coverage.team_count)} offenses
      ({baseline.coverage.teams.join(', ') || 'none'}); {number(baseline.coverage.shared_games_with_selected_candidate)} games shared with selected {label} plays.</p>
    <div className="table-scroll" role="region" tabIndex={0} aria-label={`${label} league comparison, scroll horizontally on small screens`}>
      <table className="comparison-table"><caption className="sr-only">{label}: selected offense versus other offenses in the same situation</caption>
        <thead><tr><th scope="col">Metric</th><th scope="col">Selected</th><th scope="col">Baseline</th><th scope="col">Selected − baseline</th></tr></thead>
        <tbody>
          <tr><th scope="row">Call frequency</th>
            <td>{percentage(selected.frequency)}<small>{number(selected.plays)} / {number(selected.frequency_denominator)} plays</small></td>
            <td>{percentage(baseline.frequency)}<small>{number(baseline.plays)} / {number(baseline.frequency_denominator)} plays</small></td>
            <td>{signedDifference(baseline.difference.frequency_pp, 'pp')}</td></tr>
          <tr><th scope="row">EPA / observed play</th><td>{epa(selected.epa_per_play)}</td><td>{epa(baseline.epa_per_play)}</td>
            <td>{signedDifference(baseline.difference.epa_per_play, 'EPA/play')}</td></tr>
          <tr><th scope="row">Offensive success (EPA &gt; 0)</th>
            <td>{percentage(selected.success_rate)}<small>{number(selected.epa_observations)} observed EPA denominator</small></td>
            <td>{percentage(baseline.success_rate)}<small>{number(baseline.epa_observations)} observed EPA denominator</small></td>
            <td>{signedDifference(baseline.difference.success_rate_pp, 'pp')}</td></tr>
        </tbody>
      </table>
    </div>
  </section>;
}
export function DecisionComparisonView({ decision }: { decision: Decision }) {
  const comparison = decision.league_comparison;
  if (!comparison) return null;
  const { population, data_quality: quality } = comparison;
  return <section className="panel comparison" aria-labelledby="decision-comparison-title">
    <div className="section-heading"><h3 id="decision-comparison-title">Matched candidate league comparison</h3><span>Available source only</span></div>
    <p>Baseline: other offenses, excluding {population.excluded_team} as the offense. Same snapshot, season/type, exclusive week cutoff,
      exact down, inclusive distance and every requested field-position, pre-play score, period and clock filter, with identical missing-data policies.</p>
    <p><strong>{number(population.plays)} baseline plays / {number(population.games)} games</strong>.
      {' '}{number(population.team_count)} observed baseline offenses: {population.teams.join(', ') || 'none'}.
      {' '}{number(population.shared_games_with_selected)} games shared with the selected cohort.</p>
    <p>Pooled plays, not an average of team rates. Available offenses do not certify complete league coverage.
      Matching these filters does not adjust for opponents or all game context. Shared games and repeated teams can create dependence;
      candidate game/team counts can overlap and must not be summed for population coverage.
      Coverage includes plays with missing EPA; it is not observed-EPA game support.</p>
    <p className="muted">Differences are selected minus the same baseline call, not Pass minus Run.
      pp means percentage points, not percent change. Positive means numerically higher, not better or statistically significant.
      Null differences are unavailable, not zero. Returned differences use unrounded estimates, so subtracting rounded cells can differ.
      Count flags do not establish reliability; no preferred call is selected.</p>
    {population.plays === 0 && <p className="comparison-empty">No matching baseline plays. No broader baseline or replacement cohort is used.</p>}
    {decision.population.plays === 0 && <p className="comparison-empty">The selected cohort is empty. Any baseline evidence remains visible; selected-minus-baseline differences are unavailable.</p>}
    <p className="table-hint muted">Scroll comparison tables horizontally to read all columns.</p>
    {comparison.candidates.map(candidate => <CandidateComparison key={candidate.candidate} baseline={candidate}
      selected={decision.candidates.find(selected => selected.candidate === candidate.candidate)!} />)}
    <h4>Baseline exclusion accounting</h4>
    <p>{number(quality.eligible_rows_same_season_type_before_week)} eligible plays in the same season/type before the cutoff
      {' → '}{number(quality.excluded_selected_team_rows)} selected-offense plays removed
      {' → '}{number(quality.plays_before_context_filters)} other-offense plays before situation filters.</p>
    <DecisionFilterTable cohort={comparison.cohort} quality={quality} baseline />
    <p className="muted">Each row uses only the preceding stage’s survivors; before = missing + outside + after.
      Final distance-stage survivors supply baseline metrics and coverage. Missing EPA is separate; exclusions are not additional losses to sum again.
      Baseline counts describe other offenses; they are not selected-team missingness or source-wide coverage.</p>
    {comparison.warnings.length > 0 && <div className="comparison-warnings"><h4>Baseline warnings</h4>
      <ul>{comparison.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></div>}
  </section>;
}
