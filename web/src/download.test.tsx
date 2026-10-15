import { StrictMode } from 'react';
import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { App, REQUEST_TIMEOUT_MS } from './App';
import { ReportDownload, reportFilename } from './ReportDownload';
import { fetchReportDocument, type Query, type ReportDocument } from './report';
import reports from './__fixtures__/reports.json';
import uncertainty from './__fixtures__/uncertainty-reports.json';

const response = (json: string) => new Response(json, { headers: { 'content-type': 'application/json; charset=utf-8' } });
const query = reports.offense.query as Query;
const signal = () => new AbortController().signal;
const exportLink = () => screen.queryByRole('link', { name: 'Download report JSON' });
const blobText = (blob: Blob) => new Promise<string>((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve(reader.result as string);
  reader.onerror = () => reject(reader.error);
  reader.readAsText(blob);
});
async function documentFor(json = JSON.stringify(reports.offense.report)): Promise<ReportDocument> {
  vi.mocked(fetch).mockResolvedValueOnce(response(json));
  return fetchReportDocument(query, signal());
}
function setupApp() {
  const view = render(<App />);
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Before week' }), { target: { value: '3' } });
  return view;
}
const submit = () => userEvent.click(screen.getByRole('button', { name: 'Build report' }));

describe('lossless validated response download', () => {
  const cases = [...Object.entries(reports), ...Object.entries(uncertainty).map(([key, value]) => [`uncertainty/${key}`, value] as const)];
  it.each(cases)('retains every API field and null, without a second request: %s', async (_name, fixture) => {
    const json = JSON.stringify(fixture.report);
    vi.mocked(fetch).mockResolvedValueOnce(response(json));
    const doc = await fetchReportDocument(fixture.query as Query, signal());
    expect(doc.report).toEqual(fixture.report);
    expect(doc.json).toBe(json);
    const view = render(<ReportDownload document={doc} />);
    const link = exportLink()!;
    expect(link).toBeVisible();
    expect(link).toHaveAttribute('href', 'blob:http://localhost/test-1');
    const c = fixture.report.cohort;
    expect(link).toHaveAttribute('download', `nfl-oi-${c.team}-${c.season}-${c.season_type}-${c.side}-before-week-${c.before_week_exclusive}.report.json`);
    expect(reportFilename(doc)).toMatch(/^nfl-oi-[A-Z]{2,3}-\d{4}-(REG|POST)-(offense|defense)-before-week-\d{1,2}\.report\.json$/);
    expect(reportFilename(doc).length).toBeLessThan(90);
    const blob = vi.mocked(URL.createObjectURL).mock.calls[0][0] as Blob;
    expect(blob.type).toBe('application/json;charset=utf-8');
    expect(await blobText(blob)).toBe(json);
    expect(fetch).toHaveBeenCalledTimes(1);
    view.unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:http://localhost/test-1');
  });

  it('preserves lexical numbers, extra fields, whitespace and Unicode for Python fingerprint replay', async () => {
    const json = `${JSON.stringify(reports.offense.report, null, 2).slice(0, -1)},
      "extra": {"float": 1.0, "minus_zero": -0.0, "exponent": 1e-7,
      "large_integer": 9007199254740993, "unicode": "🏈 café \\u00e9", "zero": 0, "missing": null}}
`;
    const doc = await documentFor(json);
    expect(doc.json).toBe(json);
    expect(JSON.stringify(doc.report)).not.toContain('9007199254740993'); // JS cannot represent this integer.
    render(<ReportDownload document={doc} />);
    const blob = vi.mocked(URL.createObjectURL).mock.calls[0][0] as Blob;
    expect(await blobText(blob)).toBe(json);
    expect(JSON.parse(await blobText(blob))).toEqual(doc.report);
  });

  it('never uses arbitrary source labels or URLs in the suggested filename', async () => {
    const report = structuredClone(reports.offense.report);
    report.source.label = '../../CON:\\private\n<img src=x onerror=alert(1)> 🏈';
    const doc = await documentFor(JSON.stringify(report));
    render(<ReportDownload document={doc} />);
    expect(exportLink()).toHaveAttribute('download', 'nfl-oi-CAR-2024-REG-offense-before-week-3.report.json');
    expect(document.querySelector('img')).toBeNull();
    expect(await blobText(vi.mocked(URL.createObjectURL).mock.calls[0][0] as Blob)).toContain(JSON.stringify(report.source.label));
  });

  it.each([
    ['malformed JSON', '{'],
    ['wrong cohort', JSON.stringify(reports.defense.report)],
    ['unsupported schema', JSON.stringify({ ...reports.offense.report, schema_version: 1 })],
    ['unrequested uncertainty', JSON.stringify(uncertainty.selected.report)],
  ])('never yields an exportable document for %s', async (_name, json) => {
    vi.mocked(fetch).mockResolvedValueOnce(response(json));
    await expect(fetchReportDocument(query, signal())).rejects.toThrow();
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });
});

describe('object URL lifetime', () => {
  it('reuses a live native download link on repeated clicks and revokes only after removal', async () => {
    const doc = await documentFor();
    const view = render(<ReportDownload document={doc} />);
    const link = exportLink()!;
    // jsdom has no download manager; native saving is checked separately in Chrome.
    link.addEventListener('click', event => event.preventDefault());
    await userEvent.click(link); await userEvent.click(link);
    view.rerender(<ReportDownload document={doc} />);
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
    expect(URL.revokeObjectURL).not.toHaveBeenCalled();
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/saved successfully/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Your browser controls saving/)).toBeVisible();
    view.unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:http://localhost/test-1');
  });

  it('replaces the resource and filename together when the validated document changes', async () => {
    const first = await documentFor();
    vi.mocked(fetch).mockResolvedValueOnce(response(JSON.stringify(reports.defense.report)));
    const next = await fetchReportDocument(reports.defense.query as Query, signal());
    const view = render(<ReportDownload document={first} />);
    view.rerender(<ReportDownload document={next} />);
    expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:http://localhost/test-1');
    expect(exportLink()).toHaveAttribute('href', 'blob:http://localhost/test-2');
    expect(exportLink()).toHaveAttribute('download', reportFilename(next));
    expect(await blobText(vi.mocked(URL.createObjectURL).mock.calls[1][0] as Blob)).toBe(next.json);
    view.unmount();
    expect(vi.mocked(URL.revokeObjectURL).mock.calls).toEqual([['blob:http://localhost/test-1'], ['blob:http://localhost/test-2']]);
  });

  it('owns and cleans up each StrictMode effect resource once without leaving a revoked link', async () => {
    const doc = await documentFor();
    const view = render(<StrictMode><ReportDownload document={doc} /></StrictMode>);
    expect(URL.createObjectURL).toHaveBeenCalledTimes(2);
    expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:http://localhost/test-1');
    expect(exportLink()).toHaveAttribute('href', 'blob:http://localhost/test-2');
    view.unmount();
    expect(vi.mocked(URL.revokeObjectURL).mock.calls).toEqual([['blob:http://localhost/test-1'], ['blob:http://localhost/test-2']]);
  });

  it('removes the previous link even if preparing its replacement fails', async () => {
    const first = await documentFor();
    const next = await documentFor();
    const view = render(<ReportDownload document={first} />);
    vi.mocked(URL.createObjectURL).mockImplementationOnce(() => { throw new Error('unavailable'); });
    view.rerender(<ReportDownload document={next} />);
    expect(exportLink()).not.toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('could not prepare');
    view.unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:http://localhost/test-1');
  });

  it('keeps a valid report visible when browser download preparation fails, without leaking exception text', async () => {
    vi.mocked(URL.createObjectURL).mockImplementation(() => { throw new Error('/private/secret'); });
    vi.mocked(fetch).mockResolvedValueOnce(response(JSON.stringify(reports.offense.report)));
    const view = setupApp(); await submit();
    expect(await screen.findByRole('heading', { name: 'CAR · Offense' })).toBeVisible();
    expect(screen.getByRole('alert')).toHaveTextContent('could not prepare the JSON download');
    expect(screen.getByRole('alert')).not.toHaveTextContent('/private/secret');
    expect(exportLink()).not.toBeInTheDocument();
    view.unmount();
    expect(URL.revokeObjectURL).not.toHaveBeenCalled();
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});

describe('download follows the displayed response, never a stale draft', () => {
  it('has no link in idle/loading/stale/error states and releases the previous report on resubmit', async () => {
    let finish!: (response: Response) => void;
    vi.mocked(fetch).mockResolvedValueOnce(response(JSON.stringify(reports.offense.report)))
      .mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }))
      .mockRejectedValueOnce(new TypeError('offline'));
    setupApp();
    expect(exportLink()).not.toBeInTheDocument();
    expect(URL.createObjectURL).not.toHaveBeenCalled();
    await submit(); expect(await screen.findByRole('link', { name: 'Download report JSON' })).toBeVisible();
    await submit();
    expect(exportLink()).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Building report');
    expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:http://localhost/test-1');
    fireEvent.change(screen.getByRole('textbox', { name: 'Team code' }), { target: { value: 'ATL' } });
    await act(async () => { finish(response(JSON.stringify(reports.offense.report))); });
    expect(exportLink()).not.toBeInTheDocument();
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
    await submit();
    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the local API');
    expect(exportLink()).not.toBeInTheDocument();
  });

  it('clears and revokes the ready download immediately on a query edit', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(response(JSON.stringify(reports.offense.report)));
    setupApp(); await submit();
    await screen.findByRole('link', { name: 'Download report JSON' });
    fireEvent.change(screen.getByRole('textbox', { name: 'Bootstrap seed' }), { target: { value: '0' } });
    expect(exportLink()).not.toBeInTheDocument();
    expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:http://localhost/test-1');
    expect(fetch).toHaveBeenCalledTimes(1);
    await submit();
    expect(screen.getByRole('alert')).toHaveTextContent('seed requires repetitions');
    expect(exportLink()).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['unreadable', response('{')],
    ['mismatched', response(JSON.stringify(reports.defense.report))],
    ['non-JSON', new Response('<html>not the API</html>', { headers: { 'content-type': 'text/html' } })],
    ['HTTP failure', new Response('{"error":{"code":"report_busy"}}', { status: 503 })],
  ])('never enables a link after an %s response', async (_name, reply) => {
    vi.mocked(fetch).mockResolvedValueOnce(reply);
    setupApp(); await submit();
    await screen.findByRole('alert');
    expect(exportLink()).not.toBeInTheDocument();
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it('rejects a late response after timeout even if the transport ignores abort', async () => {
    vi.useFakeTimers();
    let finish!: (response: Response) => void;
    vi.mocked(fetch).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    setupApp(); fireEvent.submit(screen.getByRole('form', { name: 'Build a cohort report' }));
    await act(async () => { await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS); });
    await act(async () => { finish(response(JSON.stringify(reports.offense.report))); });
    expect(exportLink()).not.toBeInTheDocument();
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it('allows a validated empty cohort export with nulls and provenance intact', async () => {
    const json = JSON.stringify(reports.empty.report);
    vi.mocked(fetch).mockResolvedValueOnce(response(json));
    setupApp();
    fireEvent.change(screen.getByRole('spinbutton', { name: 'Before week' }), { target: { value: '1' } });
    await submit();
    expect(await screen.findByRole('heading', { name: 'No eligible plays match this query.' })).toBeVisible();
    expect(exportLink()).toHaveAttribute('download', 'nfl-oi-CAR-2024-REG-offense-before-week-1.report.json');
    expect(await blobText(vi.mocked(URL.createObjectURL).mock.calls[0][0] as Blob)).toBe(json);
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
