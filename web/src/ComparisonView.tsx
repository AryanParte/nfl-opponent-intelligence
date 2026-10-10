import { epa, number, percentage, signedDifference, type Difference, type Metrics, type Report } from './report';

function Counts({ label, metrics: m }: { label: string; metrics: Metrics }) {
  return <p className="comparison-counts"><strong>{label}:</strong> {number(m.plays)} plays / {number(m.games)} games
    {' · '}{number(m.epa_observations)} EPA observed / {number(m.missing_epa)} missing
    {' · '}{m.small_sample ? 'Few plays' : 'No play-count flag'}
    {' · '}{m.small_epa_sample ? 'Few EPA observations' : 'No EPA-count flag'}</p>;
}

function ComparisonTable({ selected, baseline, difference, label }: {
  selected: Metrics; baseline: Metrics; difference: Difference; label: string;
}) {
  return <>
    <Counts label="Selected" metrics={selected} /><Counts label="Baseline" metrics={baseline} />
    {baseline.plays === 0 && <p className="comparison-empty">No matching baseline plays. No overall-baseline fallback is used.</p>}
    <div className="table-scroll" role="region" tabIndex={0} aria-label={`${label}, scroll horizontally on small screens`}>
      <table className="comparison-table"><caption className="sr-only">{label}</caption>
        <thead><tr><th scope="col">Metric</th><th scope="col">Selected</th><th scope="col">Baseline</th><th scope="col">Selected − baseline</th></tr></thead>
        <tbody>
          <tr><th scope="row">Dropback rate</th>
            <td>{percentage(selected.dropback_rate)}<small>{number(selected.dropbacks)} / {number(selected.plays)} plays</small></td>
            <td>{percentage(baseline.dropback_rate)}<small>{number(baseline.dropbacks)} / {number(baseline.plays)} plays</small></td>
            <td>{signedDifference(difference.dropback_rate_pp, 'pp')}</td></tr>
          <tr><th scope="row">EPA / observed play</th><td>{epa(selected.epa_per_play)}</td><td>{epa(baseline.epa_per_play)}</td>
            <td>{signedDifference(difference.epa_per_play, 'EPA/play')}</td></tr>
          <tr><th scope="row">Offensive success (EPA &gt; 0)</th>
            <td>{percentage(selected.success_rate)}<small>{number(selected.epa_observations)} observed EPA denominator</small></td>
            <td>{percentage(baseline.success_rate)}<small>{number(baseline.epa_observations)} observed EPA denominator</small></td>
            <td>{signedDifference(difference.success_rate_pp, 'pp')}</td></tr>
        </tbody>
      </table>
    </div>
  </>;
}

export function ComparisonView({ report }: { report: Report }) {
  const comparison = report.league_comparison;
  if (!comparison) return null;
  const { population, overall, overall_difference, situations, warnings } = comparison;
  // Join by identity, not array position. The decoder requires exactly matching keys.
  const selected = new Map(report.situations.map(row => [`${row.down}:${row.distance}`, row]));
  return <section className="panel comparison" aria-labelledby="comparison-title">
    <div className="section-heading"><h3 id="comparison-title">Matched league comparison</h3><span>Available source only</span></div>
    <p>Baseline: other {population.side === 'defense' ? 'defenses’ allowed offensive production' : 'offenses’ production'},
      excluding {population.excluded_team} in the same role. Same season, type and exclusive cutoff; no context filters requested.</p>
    <p><strong>{number(population.team_count)} observed baseline teams</strong>: {population.teams.join(', ') || 'none'}.
      {' '}{number(population.shared_games_with_selected)} games shared with the selected cohort.</p>
    <p>Pooled plays, not an average of team rates. Observed coverage does not certify a complete league.
      Overall situation mixes may differ; these are not opponent-adjusted scores.</p>
    <p className="muted">Differences are selected minus baseline. pp means percentage points, not percent change.
      Positive means numerically higher, not necessarily better. Defense EPA is not sign-reversed.
      Null differences are unavailable, not zero; count flags do not establish reliability.
      Differences use unrounded API estimates, so subtracting rounded cells can differ in the last digit.</p>
    <p className="table-hint muted">Scroll comparison tables horizontally to read all columns.</p>
    <h4>Overall comparison</h4>
    <ComparisonTable selected={report.overall} baseline={overall} difference={overall_difference} label="Overall league comparison" />
    <h4>Matching down &amp; distance</h4>
    <p className="muted">Only selected-team observed buckets are listed. Baseline-only buckets may contribute to overall totals,
      so baseline counts below need not sum to the overall baseline. Expand a row for counts and metrics.</p>
    {situations.length === 0 && <p>No selected-team situation rows to compare. The overall baseline may still have observations.</p>}
    {situations.map(row => <details className="comparison-bucket" key={`${row.down}:${row.distance}`}>
      <summary>{row.down} / {row.distance} · selected {number(selected.get(`${row.down}:${row.distance}`)!.plays)} plays
        {' · '}baseline {number(row.baseline.plays)} plays</summary>
      <ComparisonTable selected={selected.get(`${row.down}:${row.distance}`)!} baseline={row.baseline}
        difference={row.difference} label={`${row.down} / ${row.distance} league comparison`} />
    </details>)}
    {warnings.length > 0 && <div className="comparison-warnings"><h4>Baseline warnings</h4>
      <ul>{warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul></div>}
  </section>;
}
