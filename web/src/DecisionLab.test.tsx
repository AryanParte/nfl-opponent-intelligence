import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { App, REQUEST_TIMEOUT_MS } from './App';
import fixtures from './__fixtures__/decisions.json';
import reports from './__fixtures__/reports.json';

const reply = (value: unknown, status = 200) => new Response(JSON.stringify(value), {
  status, headers: { 'content-type': 'application/json' },
});
const panel = () => screen.getByRole('tabpanel', { name: 'Decision Lab' });
const view = () => within(panel());
function edit(name: string, value: string) {
  const form = view().getByRole('form') as HTMLFormElement;
  fireEvent.change(form.elements.namedItem(name) as HTMLElement, { target: { value } });
}
function setup() {
  const rendered = render(<App />);
  fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  edit('before_week', '3');
  return rendered;
}
const submit = () => fireEvent.click(view().getByRole('button', { name: 'Compare Run and Pass' }));
async function loaded() { await view().findByRole('heading', { name: 'CAR · Run vs Pass' }); }
function rows() { return view().getAllByRole('row').slice(1).map(row => within(row)); }

it('opens an accessible second mode without fetching or offering unsupported controls', () => {
  setup();
  expect(fetch).not.toHaveBeenCalled();
  expect(screen.getByRole('tab', { name: 'Decision Lab' })).toHaveAttribute('aria-selected', 'true');
  expect(screen.getAllByRole('tabpanel')).toHaveLength(1);
  expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
  expect(view().getByRole('combobox', { name: 'Exact down' })).toHaveValue('1');
  expect(view().queryByRole('combobox', { name: 'Role' })).not.toBeInTheDocument();
  expect(view().getByText(/No automatic fetches/)).toBeVisible();
  expect(screen.getByRole('link', { name: 'Skip to decision query' })).toHaveAttribute('href', '#decision-query');
});

it('sends exactly the narrow query, then shows independent evidence, abstention and source provenance', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.selected.decision));
  setup(); submit(); await loaded();
  const [url, options] = vi.mocked(fetch).mock.calls[0];
  const parsed = new URL(String(url), 'http://localhost');
  expect(parsed.pathname).toBe('/api/v1/decision');
  expect(Object.fromEntries(parsed.searchParams)).toEqual({ team: 'CAR', season: '2024', before_week: '3', season_type: 'REG',
    down: '1', distance_min: '10', distance_max: '10', compare_league: 'false' });
  expect(options).toMatchObject({ credentials: 'omit', cache: 'no-store', redirect: 'error' });
  expect(view().getByText('3 eligible plays / 2 games')).toBeVisible();
  const [run, pass] = rows();
  expect(run.getByText('33.3%')).toBeVisible();
  expect(run.getByText('1 / 3 plays')).toBeVisible();
  expect(run.getByText('0.000')).toBeVisible(); // zero EPA and zero success are observations, not missing
  expect(run.getByText('0.0%')).toBeVisible();
  expect(pass.getByText('66.7%')).toBeVisible();
  expect(pass.getByText('0.600')).toBeVisible();
  expect(pass.getByText('100.0%')).toBeVisible();
  expect(pass.getByText('2 observed EPA denominator')).toBeVisible();
  expect(view().getAllByText('Few plays · Few EPA observations')).toHaveLength(2);
  expect(view().getByText(/candidate game counts can overlap/)).toBeVisible();
  expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
  expect(view().getByText(/not verified intended play calls/)).toBeVisible();
  expect(view().getByText(/League comparison and uncertainty were not requested/)).toBeVisible();
  expect(view().getByText(fixtures.selected.decision.source.label)).toBeVisible();
  expect(view().getByText(fixtures.selected.decision.source.snapshot.retrieved_at_utc)).toBeVisible();
  for (const warning of fixtures.selected.decision.warnings) expect(view().getByText(warning)).toBeVisible();
  fireEvent.click(view().getByText('Inspect source fingerprints'));
  expect(view().getByText(fixtures.selected.decision.source.sha256)).toBeVisible();
  expect(view().getByRole('status')).toHaveTextContent('Decision evidence loaded: CAR, 3 eligible plays. No preferred call.');
});

it.each([
  ['empty_plain', '1', '1', '10', '10', 'Empty cohort: frequency and outcomes unavailable', 'Unavailable'],
  ['unobserved', '3', '3', '7', '7', 'Call unobserved: frequency is zero; outcomes unavailable', '0.0%'],
  ['missing_epa_plain', '3', '2', '6', '6', 'EPA missing for every observed play of this call: outcomes unavailable', '100.0%'],
] as const)('keeps %s distinct from zero-valued performance', async (key, week, down, lower, upper, state, frequency) => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures[key].decision));
  setup(); edit('before_week', week); edit('down', down); edit('distance_min', lower); edit('distance_max', upper);
  submit(); await loaded();
  const [run] = rows();
  expect(run.getByText(state)).toBeVisible();
  expect(run.getAllByText('Unavailable')).toHaveLength(key === 'empty_plain' ? 3 : 2);
  expect(run.getAllByText(frequency).length).toBeGreaterThan(0);
  expect(view().queryByRole('alert')).not.toBeInTheDocument();
  if (key === 'empty_plain') expect(view().getByRole('heading', { name: 'No eligible plays match this situation.' })).toBeVisible();
});

it.each([
  ['team', '?'], ['season', '1998'], ['before_week', '0'], ['distance_min', ''], ['distance_max', ''],
  ['distance_min', '-1'], ['distance_max', '101'], ['distance_min', '4.2'], ['distance_min', '11'],
])('links and focuses invalid %s=%s without a request or hidden-panel focus', (name, value) => {
  setup(); edit(name, value); submit();
  const form = view().getByRole('form') as HTMLFormElement;
  const input = form.elements.namedItem(name)!;
  expect(input).toHaveFocus();
  expect(input).toHaveAttribute('aria-invalid', 'true');
  expect(input).toHaveAccessibleDescription(expect.stringContaining(view().getByRole('alert').querySelector('#decision-query-error')!.textContent!));
  expect(fetch).not.toHaveBeenCalled();
  view().getByRole('button', { name: 'Compare Run and Pass' }).focus();
  submit(); expect(input).toHaveFocus();
  fireEvent.click(screen.getByRole('tab', { name: 'Scout' }));
  screen.getByRole('tab', { name: 'Decision Lab' }).focus();
  fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  expect(screen.getByRole('tab', { name: 'Decision Lab' })).toHaveFocus();
  edit(name, name === 'team' ? 'CAR' : '3');
  expect(input).not.toHaveAttribute('aria-invalid');
});

it('keeps explicit zero and inclusive full distance bounds in the request without widening', () => {
  vi.mocked(fetch).mockImplementation(() => new Promise(() => {}));
  const { unmount } = setup();
  edit('distance_min', '0'); edit('distance_max', '100'); edit('down', '4'); edit('season_type', 'POST');
  submit();
  expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain('distance_min=0&distance_max=100');
  expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain('down=4');
  expect(String(vi.mocked(fetch).mock.calls[0][0])).toContain('season_type=POST');
  unmount();
});

it('clears old evidence on edits and failures, with safe API errors and explicit retry', async () => {
  vi.mocked(fetch).mockResolvedValueOnce(reply(fixtures.selected.decision))
    .mockResolvedValueOnce(reply({ error: { code: 'report_busy', message: 'SECRET /local/path' } }, 503))
    .mockResolvedValueOnce(reply(fixtures.selected.decision));
  setup(); submit(); await loaded();
  edit('team', 'ATL');
  expect(view().queryByRole('table')).not.toBeInTheDocument();
  edit('team', 'CAR'); submit();
  expect(await view().findByRole('alert')).toHaveTextContent('Another report is being built');
  expect(panel()).not.toHaveTextContent('SECRET');
  expect(view().queryByRole('table')).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(2);
  submit(); await loaded(); expect(fetch).toHaveBeenCalledTimes(3);
});

it.each(['invalid_json', 'wrong_cohort', 'preferred_call', 'network'])('shows %s failure without evidence or focus stealing', async kind => {
  const decision = structuredClone(fixtures.selected.decision);
  if (kind === 'wrong_cohort') decision.cohort.team = 'ATL';
  if (kind === 'preferred_call') Object.assign(decision.comparison, { preferred_candidate: 'pass' });
  let resolve!: (response: Response) => void, reject!: (error: Error) => void;
  vi.mocked(fetch).mockImplementation(() => new Promise((yes, no) => { resolve = yes; reject = no; }));
  setup(); submit();
  const field = view().getByRole('textbox', { name: 'Minimum yards to go' }); field.focus();
  await act(async () => {
    if (kind === 'network') reject(new TypeError('fetch failed'));
    else resolve(kind === 'invalid_json' ? new Response('{', { headers: { 'content-type': 'application/json' } }) : reply(decision));
  });
  expect(view().getByRole('alert')).toBeVisible();
  expect(view().queryByRole('table')).not.toBeInTheDocument();
  expect(field).toHaveFocus();
});

it('aborts edits, rejects an ignored late response, and keeps the persistent loading status', async () => {
  let resolve!: (response: Response) => void;
  vi.mocked(fetch).mockImplementation(() => new Promise(yes => { resolve = yes; }));
  setup(); const status = view().getByRole('status'); submit();
  expect(status).toHaveTextContent('Loading decision evidence');
  expect(view().getByRole('button', { name: 'Comparing…' })).toBeDisabled();
  const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
  edit('distance_min', '9');
  expect(signal.aborted).toBe(true);
  await act(async () => resolve(reply(fixtures.selected.decision)));
  expect(view().queryByRole('table')).not.toBeInTheDocument();
  expect(view().getByRole('status')).toBe(status);
  expect(status).toBeEmptyDOMElement();
});

it.each(['Scout', 'Decision Lab'])('cancels pending %s work on switching modes, with no stale result on return', async mode => {
  let resolve!: (response: Response) => void;
  vi.mocked(fetch).mockImplementation(() => new Promise(yes => { resolve = yes; }));
  if (mode === 'Scout') {
    render(<App />);
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Before week' }), { target: { value: '3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Build report' }));
  } else { setup(); submit(); }
  const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
  const other = screen.getByRole('tab', { name: mode === 'Scout' ? 'Decision Lab' : 'Scout' });
  await userEvent.click(other);
  expect(signal.aborted).toBe(true);
  await act(async () => resolve(reply(mode === 'Scout' ? reports.offense.report : fixtures.selected.decision)));
  expect(other).toHaveFocus();
  fireEvent.click(screen.getByRole('tab', { name: mode }));
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
  expect(screen.getByRole('status')).toBeEmptyDOMElement();
  expect(screen.getByRole('spinbutton', { name: 'Before week' })).toHaveValue(3);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it.each(['Scout', 'Decision Lab'])('finishes the %s deadline even when transport ignores abort, and cleans up on unmount', async mode => {
  vi.useFakeTimers();
  let resolve!: (response: Response) => void;
  vi.mocked(fetch).mockImplementation(() => new Promise(yes => { resolve = yes; }));
  const { unmount } = mode === 'Scout' ? render(<App />) : setup();
  if (mode === 'Scout') {
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Before week' }), { target: { value: '3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Build report' }));
  }
  else submit();
  const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
  await act(async () => { vi.advanceTimersByTime(REQUEST_TIMEOUT_MS); });
  expect(signal.aborted).toBe(true);
  expect(screen.getByRole('alert')).toHaveTextContent('timed out after 15 seconds');
  await act(async () => resolve(reply(mode === 'Scout' ? reports.offense.report : fixtures.selected.decision)));
  expect(screen.getByRole('alert')).toHaveTextContent('timed out');
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: mode === 'Scout' ? 'Build report' : 'Compare Run and Pass' }));
  const retrySignal = vi.mocked(fetch).mock.calls[1][1]!.signal!;
  unmount();
  expect(retrySignal.aborted).toBe(true);
  expect(vi.getTimerCount()).toBe(0);
});

it('preserves both completed results, details and the Scout download across mode switches', async () => {
  vi.mocked(fetch).mockResolvedValueOnce(reply(reports.offense.report)).mockResolvedValueOnce(reply(fixtures.selected.decision));
  render(<App />);
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Before week' }), { target: { value: '3' } });
  fireEvent.click(screen.getByRole('button', { name: 'Build report' }));
  const download = await screen.findByRole('link', { name: 'Download report JSON' });
  fireEvent.click(screen.getByText('Inspect source fingerprints'));
  fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  edit('before_week', '3'); submit(); await loaded();
  fireEvent.click(view().getByText('Inspect source fingerprints'));
  fireEvent.click(screen.getByRole('tab', { name: 'Scout' }));
  expect(screen.getByRole('link', { name: 'Download report JSON' })).toBe(download);
  expect(within(screen.getByRole('tabpanel', { name: 'Scout' })).getByText(reports.offense.report.source.sha256)).toBeVisible();
  expect(URL.revokeObjectURL).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  expect(view().getByRole('table')).toBeVisible();
  expect(view().getByText(fixtures.selected.decision.source.sha256)).toBeVisible();
  expect(fetch).toHaveBeenCalledTimes(2);
  const ids = Array.from(document.querySelectorAll('[id]'), node => node.id);
  expect(new Set(ids).size).toBe(ids.length);
});

it('supports manual keyboard tab activation with wrapping, Home and End without fetching', async () => {
  render(<App />); const user = userEvent.setup();
  const scout = screen.getByRole('tab', { name: 'Scout' }), decision = screen.getByRole('tab', { name: 'Decision Lab' });
  scout.focus(); await user.keyboard('{ArrowLeft}'); expect(decision).toHaveFocus();
  expect(scout).toHaveAttribute('aria-selected', 'true');
  await user.keyboard('{Enter}'); expect(decision).toHaveAttribute('aria-selected', 'true');
  await user.keyboard('{ArrowRight}'); expect(scout).toHaveFocus();
  await user.keyboard(' '); expect(scout).toHaveAttribute('aria-selected', 'true');
  await user.keyboard('{End}'); expect(decision).toHaveFocus();
  await user.keyboard('{Home}'); expect(scout).toHaveFocus();
  expect(fetch).not.toHaveBeenCalled();
});

it('renders untrusted source text and warnings as text without executing markup', async () => {
  const decision = structuredClone(fixtures.selected.decision);
  decision.source.label = '<img src=x onerror=alert(1)>';
  decision.warnings.push('<script>bad()</script>');
  vi.mocked(fetch).mockResolvedValue(reply(decision));
  setup(); submit(); await loaded();
  expect(view().getByText(decision.source.label)).toBeVisible();
  expect(view().getByText('<script>bad()</script>')).toBeVisible();
  expect(panel().querySelector('img, script')).toBeNull();
});
