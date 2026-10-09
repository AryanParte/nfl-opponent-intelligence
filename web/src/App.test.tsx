import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { App, REQUEST_TIMEOUT_MS } from './App';
import fixtures from './__fixtures__/reports.json';

const reply = (report: unknown, status = 200) => new Response(JSON.stringify(report), {
  status, headers: { 'content-type': 'application/json' },
});
function setup() {
  render(<App />);
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Before week' }), { target: { value: '3' } });
}
async function submit() { await userEvent.click(screen.getByRole('button', { name: 'Build report' })); }

it('starts without a request and exposes labeled keyboard-usable controls', () => {
  render(<App />);
  expect(fetch).not.toHaveBeenCalled();
  expect(screen.getByRole('textbox', { name: 'Team code' })).toHaveValue('CAR');
  expect(screen.getByRole('spinbutton', { name: 'Season' })).toHaveValue(2024);
  expect(screen.getByRole('combobox', { name: 'Role' })).toHaveValue('offense');
  expect(screen.getByRole('combobox', { name: 'Season type' })).toHaveValue('REG');
  expect(screen.getByText(/No automatic fetches/)).toBeVisible();
});

it('shows independent counts, different rate denominators, provenance and all warnings', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.offense.report));
  setup(); await submit();
  expect(await screen.findByRole('heading', { name: 'CAR · Offense' })).toBeVisible();
  expect(screen.getByText('50.0%')).toBeVisible();
  expect(screen.getByText('60.0%')).toBeVisible();
  expect(screen.getByText('0.040')).toBeVisible();
  expect(screen.getByText('3 dropbacks / 6 plays')).toBeVisible();
  expect(screen.getByText('5 observed EPA · 1 missing')).toBeVisible();
  expect(screen.getByText(fixtures.offense.report.source.label)).toBeVisible();
  expect(screen.getByText(fixtures.offense.report.source.snapshot.retrieved_at_utc)).toBeVisible();
  for (const warning of fixtures.offense.report.warnings) expect(screen.getByText(warning)).toBeVisible();
  expect(screen.getAllByText('not requested')).toHaveLength(2);
  await userEvent.click(screen.getByText('Inspect source fingerprints'));
  expect(screen.getByText(fixtures.offense.report.source.sha256)).toBeVisible();
});

it('labels defense as opposing offensive production without sign reversal', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.defense.report));
  setup();
  fireEvent.change(screen.getByRole('textbox', { name: 'Team code' }), { target: { value: 'ATL' } });
  await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Role' }), 'defense');
  await submit();
  expect(await screen.findByRole('heading', { name: 'ATL · Defense' })).toBeVisible();
  expect(screen.getByText('0.050')).toBeVisible();
  expect(screen.getByText('75.0%')).toBeVisible();
  expect(screen.getByText(/these are not defensive stops/)).toBeVisible();
});

it('distinguishes empty/null results from request failure', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.empty.report));
  setup();
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Before week' }), { target: { value: '1' } });
  await submit();
  expect(await screen.findByRole('heading', { name: 'No eligible plays match this query.' })).toBeVisible();
  expect(screen.getAllByText('Unavailable')).toHaveLength(3);
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  expect(screen.getByText('No observed situation rows.')).toBeVisible();
});

it('rejects invalid query before any network call', async () => {
  setup();
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Before week' }), { target: { value: '0' } });
  await submit();
  expect(screen.getByRole('alert')).toHaveTextContent('cutoff week 1–23');
  expect(fetch).not.toHaveBeenCalled();
});

it('announces loading, prevents duplicate submits, clears results on edits and ignores stale responses', async () => {
  let finish!: (value: Response) => void;
  vi.mocked(fetch).mockImplementation(() => new Promise((resolve) => { finish = resolve; }));
  setup(); await submit();
  expect(screen.getByRole('status')).toHaveTextContent('Building report');
  expect(screen.getByRole('button', { name: 'Building…' })).toBeDisabled();
  const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
  fireEvent.change(screen.getByRole('textbox', { name: 'Team code' }), { target: { value: 'ATL' } });
  expect(signal.aborted).toBe(true);
  await act(async () => { finish(reply(fixtures.offense.report)); });
  expect(screen.queryByRole('article')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Build report' })).toBeEnabled();
});

it('does not keep a prior report under edited controls or after a failed retry', async () => {
  vi.mocked(fetch).mockResolvedValueOnce(reply(fixtures.offense.report)).mockRejectedValueOnce(new TypeError('socket failed'));
  setup(); await submit();
  await screen.findByRole('article');
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Before week' }), { target: { value: '4' } });
  expect(screen.queryByRole('article')).not.toBeInTheDocument();
  await submit();
  expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the local API');
  expect(screen.queryByRole('article')).not.toBeInTheDocument();
});

it('handles busy/retry and does not echo server exception text', async () => {
  vi.mocked(fetch).mockResolvedValueOnce(reply({ error: { code: 'report_busy', message: '/private/secret' } }, 503))
    .mockResolvedValueOnce(reply(fixtures.offense.report));
  setup(); await submit();
  const error = await screen.findByRole('alert');
  expect(error).toHaveTextContent('another report');
  expect(error).not.toHaveTextContent('/private/secret');
  await submit();
  expect(await screen.findByRole('article')).toBeVisible();
});

it('renders untrusted labels and warnings literally, never as active markup', async () => {
  const report = structuredClone(fixtures.offense.report);
  report.source.label = '<img src=x onerror=alert(1)>';
  report.warnings.push('<script>alert(1)</script>');
  vi.mocked(fetch).mockResolvedValue(reply(report));
  setup(); await submit();
  expect(await screen.findByText(report.source.label)).toBeVisible();
  expect(document.querySelector('img')).toBeNull();
  expect(document.querySelector('article script')).toBeNull();
});

it('fails closed on malformed JSON and mismatched returned cohorts', async () => {
  vi.mocked(fetch).mockResolvedValueOnce(new Response('{', { headers: { 'content-type': 'application/json' } }))
    .mockResolvedValueOnce(reply(fixtures.defense.report));
  setup(); await submit();
  expect(await screen.findByRole('alert')).toHaveTextContent('unreadable JSON');
  await submit();
  expect(await screen.findByRole('alert')).toHaveTextContent('incompatible report');
  expect(screen.queryByRole('article')).not.toBeInTheDocument();
});

it('times out and makes a manual retry available without auto-retrying', async () => {
  vi.useFakeTimers();
  vi.mocked(fetch).mockImplementation((_url, init) => new Promise((_resolve, reject) => {
    init!.signal!.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
  }));
  setup();
  fireEvent.submit(screen.getByRole('form', { name: 'Build a cohort report' }));
  await act(async () => { await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS); });
  expect(screen.getByRole('alert')).toHaveTextContent('timed out after 15 seconds');
  expect(screen.getByRole('button', { name: 'Build report' })).toBeEnabled();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('presents zero measurements as zero, not unavailable', async () => {
  const report = structuredClone(fixtures.offense.report);
  report.overall.epa_per_play = 0;
  report.overall.success_rate = 0;
  vi.mocked(fetch).mockResolvedValue(reply(report));
  setup(); await submit();
  await screen.findByRole('article');
  expect(screen.getByText('0.000')).toBeVisible();
  expect(screen.getAllByText('0.0%').length).toBeGreaterThan(0);
  const card = screen.getByRole('heading', { name: 'EPA / observed play' }).closest('section')!;
  expect(within(card).queryByText('Unavailable')).not.toBeInTheDocument();
  // A different situation still has no EPA observations; preserve its unavailable cells.
  expect(within(screen.getByRole('table')).getAllByText('Unavailable')).toHaveLength(2);
});

it('aborts an in-flight request on unmount', async () => {
  vi.mocked(fetch).mockImplementation(() => new Promise(() => {}));
  const view = render(<App />); await submit();
  const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
  view.unmount();
  expect(signal.aborted).toBe(true);
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
});
