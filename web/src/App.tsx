import { useEffect, useRef, useState, type FormEvent } from 'react';
import { epa, fetchReport, number, parseQuery, percentage, type Draft, type Report } from './report';
import { ComparisonView } from './ComparisonView';

export const REQUEST_TIMEOUT_MS = 15_000;
type State = { kind: 'idle' | 'loading' } | { kind: 'error'; message: string }
  | { kind: 'ready'; report: Report };
const initial: Draft = { team: 'CAR', season: '2024', before_week: '19', side: 'offense', season_type: 'REG', compare_league: false };

function ReportView({ report }: { report: Report }) {
  const { overall: m, cohort, source } = report;
  const defense = cohort.side === 'defense';
  return <article aria-labelledby="report-title">
    <div className="report-heading">
      <div><p className="eyebrow">Returned cohort</p>
        <h2 id="report-title">{cohort.team} <span>· {defense ? 'Defense' : 'Offense'}</span></h2></div>
      <p className="cohort-tag">{cohort.season} {cohort.season_type} · weeks &lt; {cohort.before_week_exclusive}</p>
    </div>
    <p className="interpretation">{defense
      ? 'Production allowed to opposing offenses. EPA and success stay offense-relative; these are not defensive stops.'
      : 'Production by the selected offense. EPA and success are offense-relative.'}</p>
    {m.plays === 0 && <section className="notice empty" aria-label="Empty cohort">
      <h3>No eligible plays match this query.</h3>
      <p>Try a later cutoff with available games, another team code, or season type. An absent team code is not proof that a team exists. Missing rates are unavailable, not zero performance.</p>
    </section>}
    <div className="metric-grid">
      <section className="metric"><h3>Eligible plays</h3><strong>{number(m.plays)}</strong>
        <p>{number(m.games)} games · {number(m.designed_runs)} designed runs</p></section>
      <section className="metric"><h3>Dropback rate{defense ? ' faced' : ''}</h3><strong>{percentage(m.dropback_rate)}</strong>
        <p>{number(m.dropbacks)} dropbacks / {number(m.plays)} plays</p></section>
      <section className="metric"><h3>EPA / observed play{defense ? ' allowed' : ''}</h3><strong>{epa(m.epa_per_play)}</strong>
        <p>{number(m.epa_observations)} observed EPA · {number(m.missing_epa)} missing</p></section>
      <section className="metric"><h3>Offensive success{defense ? ' allowed' : ''}</h3><strong>{percentage(m.success_rate)}</strong>
        <p>EPA &gt; 0 / {number(m.epa_observations)} observed EPA</p></section>
    </div>
    <section className="panel" aria-labelledby="situations-title">
      <div className="section-heading"><h3 id="situations-title">Down &amp; distance</h3><span>Descriptive splits</span></div>
      <p className="muted">Short: 0–3 yards · medium: 4–6 · long: 7+. Dropbacks use all plays; EPA and success use observed EPA only.</p>
      <p className="table-hint muted">Scroll the table horizontally to read all columns.</p>
      {report.situations.length === 0 ? <p>No observed situation rows.</p>
        : <div className="table-scroll" role="region" aria-label="Down and distance table, scroll horizontally on small screens" tabIndex={0}>
          <table><caption className="sr-only">Selected cohort by offensive down and distance</caption>
            <thead><tr><th scope="col">Down / distance</th><th scope="col">Plays</th><th scope="col">Games</th>
              <th scope="col">Dropbacks</th><th scope="col">EPA / play</th><th scope="col">Success</th>
              <th scope="col">EPA n / missing</th><th scope="col">Sample flags</th></tr></thead>
            <tbody>{report.situations.map((row) => <tr key={`${row.down}-${row.distance}`}>
              <th scope="row">{row.down} / {row.distance}</th><td>{number(row.plays)}</td><td>{number(row.games)}</td>
              <td>{percentage(row.dropback_rate)}</td><td>{epa(row.epa_per_play)}</td><td>{percentage(row.success_rate)}</td>
              <td>{number(row.epa_observations)} / {number(row.missing_epa)}</td>
              <td>{[row.small_sample && 'Few plays', row.small_epa_sample && 'Few EPA observations'].filter(Boolean).join(' · ') || 'No count flag'}</td>
            </tr>)}</tbody>
          </table>
        </div>}
      <p className="muted">Count warning threshold: {cohort.minimum_plays_warning}. Absence of a flag does not establish statistical reliability.</p>
    </section>
    <ComparisonView report={report} />
    <section className="panel source" aria-labelledby="source-title">
      <div className="section-heading"><h3 id="source-title">Source &amp; availability</h3><span>Report schema v{report.schema_version}</span></div>
      <p className="source-label">{source.label}</p>
      <dl className="provenance">
        <div><dt>Snapshot acquired (UTC)</dt><dd>{source.snapshot.retrieved_at_utc}</dd></div>
        <div><dt>Upstream asset updated (UTC)</dt><dd>{source.snapshot.source.asset_updated_at_utc}</dd></div>
      </dl>
      <p className="muted">Dataset attribution: {source.snapshot.license.attribution} · {source.snapshot.license.identifier}. Displayed values are calculated cohort summaries.</p>
      <p>These are source timestamps, not a live-feed or freshness guarantee. A week cutoff does not establish that the source was available before that week.</p>
      <details><summary>Inspect source fingerprints</summary>
        <dl><dt>Decoded CSV SHA-256</dt><dd className="fingerprint">{source.sha256}</dd>
          <dt>Archive SHA-256</dt><dd className="fingerprint">{source.snapshot.archive.sha256}</dd></dl>
        <p className="muted">Fingerprints identify bytes; they do not certify completeness or analytical validity.</p>
      </details>
    </section>
    <section className="notice" aria-labelledby="warnings-title">
      <h3 id="warnings-title">Read before interpreting</h3>
      <p>League comparison: <strong>{report.league_comparison ? 'requested; shown above' : 'not requested'}</strong>.
        {' '}Uncertainty: <strong>not requested</strong>. This view does not request bootstrap calculations.</p>
      <p>Overall sample flags: {m.small_sample ? 'few plays' : 'no play-count flag'}; {m.small_epa_sample ? 'few EPA observations' : 'no EPA-count flag'}.</p>
      {report.warnings.length > 0 && <ul>{report.warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul>}
      <p>Descriptive history only—not opponent adjustment, a forecast, calibrated inference or a scouting recommendation.</p>
    </section>
  </article>;
}

export function App() {
  const [draft, setDraft] = useState<Draft>(initial);
  const [state, setState] = useState<State>({ kind: 'idle' });
  const sequence = useRef(0);
  const active = useRef<AbortController | null>(null);
  useEffect(() => () => { sequence.current += 1; active.current?.abort(); }, []);

  function edit<Key extends keyof Draft>(field: Key, value: Draft[Key]) {
    sequence.current += 1;
    active.current?.abort();
    setDraft((previous) => ({ ...previous, [field]: value }));
    setState({ kind: 'idle' }); // Never relabel a previous response with a new draft query.
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const request = ++sequence.current;
    active.current?.abort();
    let query;
    try { query = parseQuery(draft); }
    catch (error) { setState({ kind: 'error', message: (error as Error).message }); return; }
    const controller = new AbortController();
    active.current = controller;
    let timedOut = false;
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, REQUEST_TIMEOUT_MS);
    setState({ kind: 'loading' });
    try {
      const report = await fetchReport(query, controller.signal);
      if (sequence.current === request && !controller.signal.aborted) setState({ kind: 'ready', report });
    } catch (error) {
      if (sequence.current === request) setState({ kind: 'error', message: timedOut
        ? 'The request timed out after 15 seconds. Check the local API before retrying; server work may still be running.'
        : error instanceof TypeError ? 'Cannot reach the local API. Start the configured API on 127.0.0.1:8000 and retry.'
        : error instanceof SyntaxError ? 'The API returned unreadable JSON. No measurements were displayed.'
        : error instanceof Error ? error.message : 'The report could not be loaded. Please retry.' });
    } finally { clearTimeout(timer); if (sequence.current === request) active.current = null; }
  }

  return <>
    <a className="skip-link" href="#query">Skip to report query</a>
    <header className="masthead"><div className="brand"><span className="monogram" aria-hidden="true">OI</span>Opponent Intelligence</div>
      <span className="local-tag">Local snapshot · read-only</span></header>
    <main>
      <section className="intro"><p className="eyebrow">NFL / Historical report viewer</p>
        <h1>Know the sample.<br /><span>Then read the tendencies.</span></h1>
        <p>Explore a team's offense or the production its defense allowed. Every report keeps the cutoff, source and denominators in view.</p>
      </section>
      <form id="query" className="panel query" onSubmit={submit} noValidate aria-labelledby="query-title">
        <div className="section-heading"><h2 id="query-title">Build a cohort report</h2><span>One configured snapshot</span></div>
        <div className="controls">
          <label>Team code<input name="team" autoComplete="off" maxLength={3} pattern="[A-Z]{2,3}" required value={draft.team}
            onChange={(e) => edit('team', e.target.value.toUpperCase())} aria-describedby="query-help" /></label>
          <label>Season<input name="season" type="number" min={1999} max={9999} step={1} required value={draft.season}
            onChange={(e) => edit('season', e.target.value)} /></label>
          <label>Before week<input name="before_week" type="number" min={1} max={23} step={1} required value={draft.before_week}
            onChange={(e) => edit('before_week', e.target.value)} aria-describedby="cutoff-help" /></label>
          <label>Role<select name="side" value={draft.side} onChange={(e) => edit('side', e.target.value)}>
            <option value="offense">Offense</option><option value="defense">Defense</option></select></label>
          <label>Season type<select name="season_type" value={draft.season_type} onChange={(e) => edit('season_type', e.target.value)}>
            <option value="REG">Regular season</option><option value="POST">Postseason</option></select></label>
        </div>
        <label className="comparison-toggle"><input type="checkbox" name="compare_league" checked={draft.compare_league}
          onChange={(e) => edit('compare_league', e.target.checked)} aria-describedby="comparison-help" />
          Compare with other teams in the same role</label>
        <p id="comparison-help" className="muted">Optional pooled baseline from available source plays. Does not request uncertainty calculations.</p>
        <div className="form-footer"><div><p id="cutoff-help">Exclusive cutoff: only weeks strictly before this week are included.</p>
          <p id="query-help" className="muted">Use source team codes. The API's operator selects the local season snapshot, not this form.</p></div>
          <button type="submit" disabled={state.kind === 'loading'}>{state.kind === 'loading' ? 'Building…' : 'Build report'} <span aria-hidden="true">→</span></button></div>
      </form>
      <div className="request-status" role="status" aria-live="polite">{state.kind === 'loading' ? 'Building report from the configured local snapshot…'
        : state.kind === 'ready' ? `Report loaded: ${state.report.cohort.team}, ${state.report.cohort.side}, ${state.report.overall.plays} eligible plays.` : ''}</div>
      {state.kind === 'idle' && <section className="empty-state"><span className="eyebrow">Ready when you are</span>
        <h2>Select a cohort to inspect the evidence.</h2><p>No report has been requested for these controls. No automatic fetches or background refreshes.</p></section>}
      {state.kind === 'error' && <section className="notice error" role="alert"><h2>Report unavailable</h2><p>{state.message}</p><p>Correct the query or connection, then select Build report. No previous result is shown.</p></section>}
      {state.kind === 'ready' && <ReportView report={state.report} />}
    </main>
    <footer>Independent portfolio project · No NFL or team affiliation · Local development view, not a deployed product</footer>
  </>;
}
