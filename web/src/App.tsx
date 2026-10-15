import { useEffect, useRef, useState, type FormEvent } from 'react';
import { epa, fetchReportDocument, number, parseQuery, percentage, PERIODS, type Draft, type ReportDocument } from './report';
import { ComparisonView } from './ComparisonView';
import { FieldPositionView } from './FieldPositionView';
import { ScoreView } from './ScoreView';
import { TimeView } from './TimeView';
import { UncertaintyView } from './UncertaintyView';
import { ReportDownload } from './ReportDownload';

export const REQUEST_TIMEOUT_MS = 15_000;
type State = { kind: 'idle' | 'loading' } | { kind: 'error'; message: string }
  | { kind: 'ready'; document: ReportDocument };
const initial: Draft = { team: 'CAR', season: '2024', before_week: '19', side: 'offense', season_type: 'REG',
  compare_league: false, yardline_min: '', yardline_max: '', score_min: '', score_max: '', period: '', clock_min: '', clock_max: '', bootstrap_repetitions: '', bootstrap_seed: '' };

function ReportView({ document }: { document: ReportDocument }) {
  const { report } = document;
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
    <ReportDownload document={document} />
    <FieldPositionView report={report} />
    <ScoreView report={report} />
    <TimeView report={report} />
    {m.plays === 0 && <section className="notice empty" aria-label="Empty cohort">
      <h3>No eligible plays match this query.</h3>
      <p>Try a later cutoff with available games, another team code, season type, or context range. An absent team code is not proof that a team exists. Missing rates are unavailable, not zero performance.</p>
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
    <UncertaintyView report={report} />
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
        {' '}Uncertainty: <strong>{report.uncertainty ? 'requested; support and limitations shown above' : 'not requested'}</strong>.</p>
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
      const document = await fetchReportDocument(query, controller.signal);
      if (sequence.current === request && !controller.signal.aborted) setState({ kind: 'ready', document });
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
        <fieldset className="field-controls" aria-describedby="field-help field-coordinate-help">
          <legend>Pre-play field position (optional)</legend>
          <p id="field-coordinate-help" className="muted">Yards to the offense’s opponent’s goal line, in either role.
            20 = opponent’s 20; 80 = own 20. Defense mode does not reverse the coordinates.</p>
          <div className="field-inputs">
            {/* Keep invalid text distinguishable from blank (which means omit the filter). */}
            <label>Minimum yards to goal<input name="yardline_min" type="text" inputMode="decimal" autoComplete="off"
              value={draft.yardline_min} onChange={(e) => edit('yardline_min', e.target.value)} aria-describedby="field-help field-coordinate-help" /></label>
            <label>Maximum yards to goal<input name="yardline_max" type="text" inputMode="decimal" autoComplete="off"
              value={draft.yardline_max} onChange={(e) => edit('yardline_max', e.target.value)} aria-describedby="field-help field-coordinate-help" /></label>
          </div>
          <p id="field-help" className="muted">Inclusive decimals 0–100; use a dot. Both blank = no field filter.
            With one bound entered, the blank end defaults to 0 or 100. Any requested range, even 0–100, excludes missing positions.</p>
        </fieldset>
        <fieldset className="field-controls" aria-describedby="score-help score-perspective-help">
          <legend>Pre-play score difference (optional)</legend>
          <p id="score-perspective-help" className="muted">Offense points minus defense points before the play.
            Negative = offense trailing; positive = offense leading; 0 = tied, not missing.
            Defense mode does not reverse the sign.</p>
          <div className="field-inputs">
            {/* Text keeps partial signs invalid, not blank; the keyboard must allow minus. */}
            <label>Minimum score difference<input name="score_min" type="text" autoComplete="off"
              value={draft.score_min} onChange={(e) => edit('score_min', e.target.value)} aria-describedby="score-help score-perspective-help" /></label>
            <label>Maximum score difference<input name="score_max" type="text" autoComplete="off"
              value={draft.score_max} onChange={(e) => edit('score_max', e.target.value)} aria-describedby="score-help score-perspective-help" /></label>
          </div>
          <p id="score-help" className="muted">Inclusive signed whole points, -1000 to +1000 (API input limits, not typical game scores).
            A blank end is unbounded; both blank = no score filter. Any requested score range excludes missing pre-play scores.
            Field position is filtered first when both are requested.</p>
        </fieldset>
        <fieldset className="field-controls" aria-describedby="time-help clock-help">
          <legend>Pre-play period &amp; clock (optional)</legend>
          <div className="field-inputs">
            <label>Period<select name="period" value={draft.period} onChange={(e) => edit('period', e.target.value)} aria-describedby="time-help">
              <option value="">Unrestricted</option>
              {PERIODS.map(period => <option key={period} value={period}>{period === 'OT' ? 'OT — all overtime periods' : period}</option>)}
            </select></label>
          </div>
          <p id="time-help" className="muted">Q1–Q4 select one regulation quarter; OT selects all periods numbered 5 or higher.
            Period-only selection excludes unknown periods but does not exclude missing clocks.</p>
          <div className="field-inputs">
            <label>Minimum seconds remaining<input name="clock_min" type="text" inputMode="numeric" autoComplete="off"
              value={draft.clock_min} onChange={(e) => edit('clock_min', e.target.value)} aria-describedby="clock-help" /></label>
            <label>Maximum seconds remaining<input name="clock_max" type="text" inputMode="numeric" autoComplete="off"
              value={draft.clock_max} onChange={(e) => edit('clock_max', e.target.value)} aria-describedby="clock-help" /></label>
          </div>
          <p id="clock-help" className="muted">Inclusive whole seconds 0–900 remaining in the selected period at play start, not elapsed time or MM:SS.
            Clock bounds require an explicit period. Both blank = no clock filter; with one bound entered, the blank end defaults to 0 or 900.
            Zero is observed, not missing. Any requested clock range excludes missing clocks. Clearing the period does not clear entered bounds.</p>
        </fieldset>
        <label className="comparison-toggle"><input type="checkbox" name="compare_league" checked={draft.compare_league}
          onChange={(e) => edit('compare_league', e.target.checked)} aria-describedby="comparison-help" />
          Compare with other teams in the same role</label>
        <p id="comparison-help" className="muted">Optional pooled baseline from available source plays. Does not request uncertainty calculations.</p>
        <fieldset className="field-controls" aria-describedby="bootstrap-help">
          <legend>Exploratory game bootstrap (optional)</legend>
          <div className="field-inputs">
            <label>Bootstrap repetitions<input name="bootstrap_repetitions" type="text" inputMode="numeric" autoComplete="off"
              value={draft.bootstrap_repetitions} onChange={e => edit('bootstrap_repetitions', e.target.value)} aria-describedby="bootstrap-help" /></label>
            <label>Bootstrap seed<input name="bootstrap_seed" type="text" inputMode="numeric" autoComplete="off"
              value={draft.bootstrap_seed} onChange={e => edit('bootstrap_seed', e.target.value)} aria-describedby="bootstrap-help" /></label>
          </div>
          <p id="bootstrap-help" className="muted">Whole repetitions 200–1000 opt in; both blank means not requested. Seed 0–4294967295 requires repetitions;
            blank seed defaults to 0. Works with or without comparison. More draws add computation, not observed games or statistical reliability.
            Bounds are exploratory, not calibrated confidence. Editing clears results; aborting or timing out does not stop server computation.</p>
        </fieldset>
        <div className="form-footer"><div><p id="cutoff-help">Exclusive cutoff: only weeks strictly before this week are included.</p>
          <p id="query-help" className="muted">Use source team codes. The API's operator selects the local season snapshot, not this form.</p></div>
          <button type="submit" disabled={state.kind === 'loading'}>{state.kind === 'loading' ? 'Building…' : 'Build report'} <span aria-hidden="true">→</span></button></div>
      </form>
      <div className="request-status" role="status" aria-live="polite">{state.kind === 'loading' ? 'Building report from the configured local snapshot…'
        : state.kind === 'ready' ? `Report loaded: ${state.document.report.cohort.team}, ${state.document.report.cohort.side}, ${state.document.report.overall.plays} eligible plays.` : ''}</div>
      {state.kind === 'idle' && <section className="empty-state"><span className="eyebrow">Ready when you are</span>
        <h2>Select a cohort to inspect the evidence.</h2><p>No report has been requested for these controls. No automatic fetches or background refreshes.</p></section>}
      {state.kind === 'error' && <section className="notice error" role="alert"><h2>Report unavailable</h2><p>{state.message}</p><p>Correct the query or connection, then select Build report. No previous result is shown.</p></section>}
      {state.kind === 'ready' && <ReportView document={state.document} />}
    </main>
    <footer>Independent portfolio project · No NFL or team affiliation · Local development view, not a deployed product</footer>
  </>;
}
