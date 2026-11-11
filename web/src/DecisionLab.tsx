import { useEffect, useRef, useState, type FormEvent } from 'react';
import { DecisionQueryValidationError, fetchDecisionDocument, parseDecisionQuery,
  type Candidate, type Decision, type DecisionDocument, type DecisionDraft } from './decision';
import { epa, number, percentage } from './report';
import { SourceView } from './SourceView';
import { useSnapshotRequest } from './useSnapshotRequest';
import { FieldPositionControls } from './FieldPositionControls';
import { DecisionContextView } from './DecisionContextView';
import { ScoreControls } from './ScoreControls';
import { TimeControls } from './TimeControls';
import { DecisionComparisonView } from './DecisionComparisonView';
import { BootstrapControls } from './BootstrapControls';
import { DecisionUncertaintyView } from './DecisionUncertaintyView';

const initial: DecisionDraft = {
  team: 'CAR', season: '2024', before_week: '19', season_type: 'REG', down: '1', distance_min: '10', distance_max: '10',
  minimum_plays: '', compare_league: false, yardline_min: '', yardline_max: '', score_min: '', score_max: '',
  period: '', clock_min: '', clock_max: '', bootstrap_repetitions: '', bootstrap_seed: '',
};
const outcomes: Record<Candidate['availability']['outcomes'], string> = {
  available: 'Observed EPA available', empty_cohort: 'Empty cohort: frequency and outcomes unavailable',
  unobserved_candidate: 'Call unobserved: frequency is zero; outcomes unavailable',
  missing_epa: 'EPA missing for every observed play of this call: outcomes unavailable',
};

function DecisionEvidence({ decision }: { decision: Decision }) {
  const { cohort, population, candidates } = decision;
  return <article aria-labelledby="decision-result-title">
    <div className="report-heading">
      <div><p className="eyebrow">Returned offensive cohort</p><h2 id="decision-result-title">{cohort.team} · Run vs Pass</h2></div>
      <p className="cohort-tag">{cohort.season} {cohort.season_type} · weeks &lt; {cohort.before_week_exclusive}</p>
    </div>
    <p className="interpretation">Down {cohort.down.minimum_inclusive} · {cohort.distance.minimum_inclusive}–{cohort.distance.maximum_inclusive} yards to go, inclusive.
      {' '}This is a historical situation, not a fully specified game state.</p>
    <DecisionContextView decision={decision} />
    <section className="notice" aria-labelledby="decision-abstention-title">
      <h3 id="decision-abstention-title">No preferred call</h3>
      <p>Insufficient evidence for a preferred call: candidate comparison has not been validated.
        Observed Run and Pass outcomes describe different plays; a higher EPA or success rate does not establish which call is optimal.</p>
      <p>Historical associations only. No causal claim, guaranteed future performance or coaching recommendation.
        Opponent-specific evidence is deferred.</p>
    </section>
    {population.plays === 0 && <section className="notice empty" aria-label="Empty decision cohort">
      <h3>No eligible plays match this situation.</h3>
      <p>No broader cohort was substituted. Check the team, season, cutoff, down, distance, field-position, score, period and clock filters. Missing rates are unavailable, not zero performance.</p>
    </section>}
    <section className="panel" aria-labelledby="decision-evidence-title">
      <div className="section-heading"><h3 id="decision-evidence-title">Observed call evidence</h3><span>Descriptive · offense only</span></div>
      <p><strong>{number(population.plays)} eligible plays / {number(population.games)} {population.games === 1 ? 'game' : 'games'}</strong> in this situation.
        Frequency uses all eligible plays. EPA and offensive success (EPA &gt; 0) use each call’s observed EPA only.</p>
      <p className="muted">Run is non-dropback; Pass includes sacks and scrambles. These are observed play categories, not verified intended play calls.
        Calls partition plays; a game can contain both calls, so candidate game counts can overlap.</p>
      <p className="table-hint muted">Scroll the table horizontally to read all columns.</p>
      <div className="table-scroll" role="region" tabIndex={0} aria-label="Run and Pass evidence, scroll horizontally on small screens">
        <table className="decision-table"><caption className="sr-only">Observed Run and Pass evidence for the selected offense</caption>
          <thead><tr><th scope="col">Observed call</th><th scope="col">Frequency</th><th scope="col">Games</th>
            <th scope="col">EPA / observed play</th><th scope="col">Offensive success</th><th scope="col">EPA n / missing</th><th scope="col">Evidence state</th></tr></thead>
          <tbody>{candidates.map(candidate => <tr key={candidate.candidate}>
            <th scope="row">{candidate.candidate === 'run' ? 'Run' : 'Pass'}<small>{candidate.label}</small></th>
            <td>{percentage(candidate.frequency)}<small>{number(candidate.plays)} / {number(candidate.frequency_denominator)} plays</small></td>
            <td>{number(candidate.games)}</td><td>{epa(candidate.epa_per_play)}</td>
            <td>{percentage(candidate.success_rate)}<small>{number(candidate.epa_observations)} observed EPA denominator</small></td>
            <td>{number(candidate.epa_observations)} / {number(candidate.missing_epa)}</td>
            <td>{outcomes[candidate.availability.outcomes]}<small>
              {candidate.small_sample ? 'Few plays' : 'No play-count flag'} · {candidate.small_epa_sample ? 'Few EPA observations' : 'No EPA-count flag'}
            </small></td>
          </tr>)}</tbody>
        </table>
      </div>
      <p className="muted">Count warning threshold: {decision.estimation_policy.minimum_plays_warning}. Absence of a flag does not establish statistical reliability.</p>
    </section>
    <DecisionComparisonView decision={decision} />
    <DecisionUncertaintyView decision={decision} />
    <SourceView source={decision.source} titleId="decision-source-title" versionLabel={`Decision contract v${decision.contract_version}`} />
    <section className="notice" aria-labelledby="decision-warnings-title">
      <h3 id="decision-warnings-title">Read before interpreting</h3>
      <p>{decision.uncertainty ? 'Exploratory uncertainty was requested. Intervals do not validate a preferred call.' : decision.league_comparison ? 'Matched league comparison was requested. Uncertainty was not requested; differences are descriptive, not significance tests.'
        : 'League comparison and uncertainty were not requested. This view displays selected-offense evidence only.'}</p>
      {decision.warnings.length > 0 && <ul>{decision.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul>}
    </section>
  </article>;
}

export function DecisionLab({ active }: { active: boolean }) {
  const [draft, setDraft] = useState(initial);
  const { state, invalidate, failValidation, load } = useSnapshotRequest<DecisionDocument, keyof DecisionDraft>(active);
  const form = useRef<HTMLFormElement>(null);
  useEffect(() => {
    // A new submitted validation error may focus a field; returning to this mode must not.
    if (active && state.kind === 'error' && state.fields?.length) {
      const field = form.current?.elements.namedItem(state.fields[0]);
      if (field instanceof HTMLElement) field.focus();
    }
  }, [state]);
  function fieldAccessibility(field: keyof DecisionDraft, help?: string) {
    const invalid = state.kind === 'error' && state.fields?.includes(field);
    return { 'aria-invalid': invalid ? true as const : undefined,
      'aria-describedby': [help, invalid && 'decision-query-error'].filter(Boolean).join(' ') || undefined };
  }
  function edit<Key extends keyof DecisionDraft>(field: Key, value: DecisionDraft[Key]) {
    invalidate();
    setDraft(previous => ({ ...previous, [field]: value }));
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    let query;
    try { query = parseDecisionQuery(draft); }
    catch (error) {
      failValidation((error as Error).message, error instanceof DecisionQueryValidationError ? error.fields : undefined);
      return;
    }
    await load(signal => fetchDecisionDocument(query, signal));
  }
  return <>
    <section className="intro"><p className="eyebrow">Decision Lab / Run vs Pass</p>
      <h1>Compare the calls.<br /><span>Understand the evidence.</span></h1>
      <p>Inspect what an offense did in a defined historical situation. Start with Run and Pass; every result shows the sample and where the evidence stops.</p>
    </section>
    <form ref={form} id="decision-query" className="panel query" noValidate onSubmit={submit} aria-labelledby="decision-query-title">
      <div className="section-heading"><h2 id="decision-query-title">Define a situation</h2><span>One configured snapshot</span></div>
      <p className="muted">Team, season/type, cutoff, down and distance are required; field position, pre-play score, period and clock are optional.
        Offense only. Defaults are query inputs, not a claim of data availability.</p>
      <div className="controls decision-controls">
        <label>Offense team code<input name="team" autoComplete="off" maxLength={3} required value={draft.team}
          onChange={event => edit('team', event.target.value.toUpperCase())} {...fieldAccessibility('team', 'decision-team-help')} /></label>
        <label>Season<input name="season" type="number" min={1999} max={9999} step={1} required value={draft.season}
          onChange={event => edit('season', event.target.value)} {...fieldAccessibility('season', 'decision-season-help')} /></label>
        <label>Before week<input name="before_week" type="number" min={1} max={23} step={1} required value={draft.before_week}
          onChange={event => edit('before_week', event.target.value)} {...fieldAccessibility('before_week', 'decision-cutoff-help')} /></label>
        <label>Season type<select name="season_type" value={draft.season_type} onChange={event => edit('season_type', event.target.value)} {...fieldAccessibility('season_type')}>
          <option value="REG">Regular season</option><option value="POST">Postseason</option></select></label>
      </div>
      <fieldset className="field-controls" aria-describedby="decision-distance-help"><legend>Down &amp; distance</legend>
        <div className="decision-situation">
          <label>Exact down<select name="down" value={draft.down} onChange={event => edit('down', event.target.value)} {...fieldAccessibility('down', 'decision-distance-help')}>
            {[1, 2, 3, 4].map(down => <option key={down} value={down}>{down}</option>)}</select></label>
          <label>Minimum yards to go<input name="distance_min" type="text" inputMode="numeric" autoComplete="off" required value={draft.distance_min}
            onChange={event => edit('distance_min', event.target.value)} {...fieldAccessibility('distance_min', 'decision-distance-help')} /></label>
          <label>Maximum yards to go<input name="distance_max" type="text" inputMode="numeric" autoComplete="off" required value={draft.distance_max}
            onChange={event => edit('distance_max', event.target.value)} {...fieldAccessibility('distance_max', 'decision-distance-help')} /></label>
        </div>
        <p id="decision-distance-help" className="muted">One exact down, 1–4. Distance is an inclusive whole-yard range, 0–100; equal bounds select one distance.
          Zero is observed, not missing. Blank bounds are invalid. No automatic widening or replacement cohort.</p>
      </fieldset>
      <FieldPositionControls draft={draft} edit={edit} fieldAccessibility={fieldAccessibility} idPrefix="decision-" />
      <ScoreControls draft={draft} edit={edit} fieldAccessibility={fieldAccessibility} idPrefix="decision-" />
      <TimeControls draft={draft} edit={edit} fieldAccessibility={fieldAccessibility} idPrefix="decision-" />
      <label className="comparison-toggle"><input type="checkbox" name="compare_league" checked={draft.compare_league}
        onChange={event => edit('compare_league', event.target.checked)} {...fieldAccessibility('compare_league', 'decision-comparison-help')} />
        Compare with other offenses</label>
      <p id="decision-comparison-help" className="muted">Optional pooled baseline excludes the selected offense and matches this situation within the available snapshot.
        Does not request uncertainty or recommend a call.</p>
      <BootstrapControls draft={draft} edit={edit} fieldAccessibility={fieldAccessibility} idPrefix="decision-" />
      <div className="form-footer"><div>
        <p id="decision-cutoff-help">Whole week 1–23. Exclusive cutoff: only weeks strictly before this week are included.</p>
        <p id="decision-season-help" className="muted">Whole season 1999–9999; it must be available in the configured snapshot.</p>
        <p id="decision-team-help" className="muted">Use a 2–3 letter team code. An empty response does not validate that a team exists.</p>
      </div><button type="submit" disabled={state.kind === 'loading'}>{state.kind === 'loading' ? 'Comparing…' : 'Compare Run and Pass'}</button></div>
    </form>
    <div className="request-status" role="status" aria-live="polite">{state.kind === 'loading' ? 'Loading decision evidence from the local snapshot…'
      : state.kind === 'ready' ? `Decision evidence loaded: ${state.document.decision.cohort.team}, ${state.document.decision.population.plays} eligible plays. No preferred call.` : ''}</div>
    {state.kind === 'idle' && <section className="empty-state"><h2>Define a situation to compare observed calls.</h2>
      <p>No evidence has been requested for these controls. No automatic fetches or background refreshes.</p></section>}
    {state.kind === 'error' && <section className="notice error" role="alert"><h2>Decision evidence unavailable</h2>
      <p id="decision-query-error">{state.message}</p><p>Correct the query or connection, then select Compare Run and Pass. No previous result is shown.</p></section>}
    {state.kind === 'ready' && <DecisionEvidence decision={state.document.decision} />}
  </>;
}
