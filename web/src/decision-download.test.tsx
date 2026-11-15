import { StrictMode, useLayoutEffect } from 'react';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { App, REQUEST_TIMEOUT_MS } from './App';
import { DecisionDownload, decisionFilename } from './DecisionDownload';
import { fetchDecisionDocument, type DecisionDocument, type DecisionQuery } from './decision';
import fixtures from './__fixtures__/decisions.json';
import reports from './__fixtures__/reports.json';

const response = (json: string) => new Response(json, { headers: { 'content-type': 'application/json; charset=utf-8' } });
const view = () => within(screen.getByRole('tabpanel', { name: 'Decision Lab' }));
const link = () => screen.queryByRole('link', { name: 'Download decision JSON' });
const input = (name: string) => (view().getByRole('form') as HTMLFormElement).elements.namedItem(name) as HTMLElement;
const edit = (name: string, value: string) => fireEvent.change(input(name), { target: { value } });
const submit = () => fireEvent.click(view().getByRole('button', { name: 'Compare Run and Pass' }));
const blobText = (blob: Blob) => new Promise<string>((resolve, reject) => {
  const reader = new FileReader(); reader.onload = () => resolve(reader.result as string);
  reader.onerror = () => reject(reader.error); reader.readAsText(blob);
});
const createdBlob = (index = 0) => vi.mocked(URL.createObjectURL).mock.calls[index][0] as Blob;
async function documentFor(name: keyof typeof fixtures = 'selected', text = JSON.stringify(fixtures[name].decision)) {
  vi.mocked(fetch).mockResolvedValueOnce(response(text));
  return fetchDecisionDocument(fixtures[name].query as DecisionQuery, new AbortController().signal);
}
function setup(name: keyof typeof fixtures = 'selected') {
  const result = render(<App />); fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  for (const [key, value] of Object.entries(fixtures[name].query)) {
    if (key === 'compare_league') { if (value) fireEvent.click(input(key)); }
    else edit(key, String(value));
  }
  return result;
}

// Existing endpoint-produced fixtures cover distinct evidence shapes without new data or formulas.
it.each(['selected', 'context', 'bootstrap_context', 'empty_plain', 'unobserved', 'missing_epa_plain', 'overtime'] as const)(
  'downloads the complete validated %s response without another request', async name => {
    const json = JSON.stringify(fixtures[name].decision);
    const doc = await documentFor(name, json); const result = render(<DecisionDownload document={doc} />);
    expect(link()).toBeVisible(); expect(link()).toHaveAttribute('href', 'blob:http://localhost/test-1');
    expect(link()).toHaveAttribute('download', decisionFilename(doc));
    expect(decisionFilename(doc)).toMatch(/^nfl-di-[A-Z]{2,3}-\d{4}-(REG|POST)-before-week-\d{1,2}-down-[1-4]-distance-\d{1,3}-\d{1,3}\.decision\.json$/);
    expect(decisionFilename(doc).length).toBeLessThan(100);
    expect(createdBlob().type).toBe('application/json;charset=utf-8');
    expect(await blobText(createdBlob())).toBe(json);
    expect(JSON.parse(await blobText(createdBlob()))).toEqual(fixtures[name].decision);
    expect(doc.decision.comparison.preferred_candidate).toBeNull();
    expect(link()).toHaveAccessibleDescription(expect.stringContaining('Your local call choice is not included'));
    expect(fetch).toHaveBeenCalledTimes(1); result.unmount();
    expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:http://localhost/test-1');
  });

it('preserves unrendered fields, numeric spelling, whitespace and Unicode rather than reserializing parsed evidence', async () => {
  const json = `${JSON.stringify(fixtures.selected.decision, null, 2).slice(0, -1)},
    "extra": {"float": 1.0, "minus_zero": -0.0, "exponent": 1e-7,
    "large_integer": 9007199254740993, "unicode": "🏈 café \\u00e9", "missing": null}}
`;
  const doc = await documentFor('selected', json); render(<DecisionDownload document={doc} />);
  expect(JSON.stringify(doc.decision)).not.toContain('9007199254740993'); // Parsing in JS loses this integer's precision.
  expect(await blobText(createdBlob())).toBe(json);
  expect(link()).toHaveAttribute('download', 'nfl-di-CAR-2024-REG-before-week-3-down-1-distance-10-10.decision.json');
});

it('uses only validated basic situation values in the filename, never a source label', async () => {
  const data = structuredClone(fixtures.unobserved.decision);
  data.source.label = '../../CON:\\private\n<img src=x onerror=alert(1)> 🏈';
  const doc = await documentFor('unobserved', JSON.stringify(data)); render(<DecisionDownload document={doc} />);
  expect(link()).toHaveAttribute('download', 'nfl-di-CAR-2024-REG-before-week-3-down-3-distance-7-7.decision.json');
  expect(document.querySelector('img')).toBeNull();
  expect(await blobText(createdBlob())).toContain(JSON.stringify(data.source.label));
});

describe('download resource ownership', () => {
  it('keeps repeat downloads live, replacing filename and content together without briefly serving the previous document', async () => {
    const first = await documentFor(), second = await documentFor('unobserved');
    const seen: (string | null)[] = [];
    function Observe({ value }: { value: DecisionDocument }) {
      useLayoutEffect(() => { seen.push(link()?.getAttribute('href') ?? null); }, [value]);
      return <DecisionDownload document={value} />;
    }
    const result = render(<Observe value={first} />);
    link()!.addEventListener('click', event => event.preventDefault()); // jsdom has no native download manager.
    await userEvent.click(link()!); await userEvent.click(link()!);
    result.rerender(<Observe value={first} />);
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1); expect(URL.revokeObjectURL).not.toHaveBeenCalled();
    result.rerender(<Observe value={second} />);
    expect(seen).toEqual([null, null]); // No prior bytes paired with the new filename, even before effects flush.
    expect(link()).toHaveAttribute('href', 'blob:http://localhost/test-2');
    expect(link()).toHaveAttribute('download', 'nfl-di-CAR-2024-REG-before-week-3-down-3-distance-7-7.decision.json');
    expect(await blobText(createdBlob(1))).toBe(second.json);
    expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:http://localhost/test-1');
    result.unmount(); expect(vi.mocked(URL.revokeObjectURL).mock.calls).toEqual([['blob:http://localhost/test-1'], ['blob:http://localhost/test-2']]);
    expect(fetch).toHaveBeenCalledTimes(2); // Only document acquisition, not clicks/renders.
  });

  it('cleans up StrictMode resources once and leaves the current link live', async () => {
    const doc = await documentFor(); const result = render(<StrictMode><DecisionDownload document={doc} /></StrictMode>);
    expect(URL.createObjectURL).toHaveBeenCalledTimes(2);
    expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:http://localhost/test-1');
    expect(link()).toHaveAttribute('href', 'blob:http://localhost/test-2');
    result.unmount(); expect(vi.mocked(URL.revokeObjectURL).mock.calls).toEqual([['blob:http://localhost/test-1'], ['blob:http://localhost/test-2']]);
  });

  it('removes a previous URL when replacement preparation fails and recovers on a new document', async () => {
    const first = await documentFor(), next = await documentFor('unobserved'), last = await documentFor();
    const result = render(<DecisionDownload document={first} />);
    vi.mocked(URL.createObjectURL).mockImplementationOnce(() => { throw new Error('/private/secret'); });
    result.rerender(<DecisionDownload document={next} />);
    expect(link()).not.toBeInTheDocument(); expect(screen.getByRole('alert')).not.toHaveTextContent('/private/secret');
    expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:http://localhost/test-1');
    result.rerender(<DecisionDownload document={last} />);
    expect(link()).toHaveAttribute('href', 'blob:http://localhost/test-2');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    result.unmount(); expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2);
  });

  it.each(['Blob', 'URL'])('retains evidence and abstention if %s preparation fails', async failure => {
    if (failure === 'URL') vi.mocked(URL.createObjectURL).mockImplementationOnce(() => { throw new Error('/private/secret'); });
    else vi.stubGlobal('Blob', class { constructor() { throw new Error('/private/secret'); } });
    vi.mocked(fetch).mockResolvedValueOnce(response(JSON.stringify(fixtures.selected.decision))); setup(); submit();
    await view().findByRole('heading', { name: 'CAR · Run vs Pass' });
    expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
    expect(await view().findByRole('alert')).toHaveTextContent('decision evidence is still available to read');
    expect(view().getByRole('alert')).not.toHaveTextContent('/private/secret');
    expect(link()).not.toBeInTheDocument(); expect(URL.revokeObjectURL).not.toHaveBeenCalled();
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});

it('preserves both mode downloads and exact decision bytes across choosing, clearing and mode switches', async () => {
  const decisionJson = JSON.stringify(fixtures.bootstrap_context.decision);
  vi.mocked(fetch).mockResolvedValueOnce(response(decisionJson)); const result = setup('bootstrap_context'); submit();
  const download = await screen.findByRole('link', { name: 'Download decision JSON' });
  fireEvent.click(view().getByRole('radio', { name: 'Run' }));
  fireEvent.click(view().getByRole('radio', { name: 'Pass' }));
  fireEvent.click(view().getByRole('button', { name: 'Clear choice' }));
  expect(link()).toBe(download); expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
  expect(await blobText(createdBlob())).toBe(decisionJson);
  fireEvent.click(screen.getByRole('tab', { name: 'Scout' }));
  expect(link()).not.toBeInTheDocument(); // Mounted but inaccessible in the hidden panel.
  expect(URL.revokeObjectURL).not.toHaveBeenCalled();
  vi.mocked(fetch).mockResolvedValueOnce(response(JSON.stringify(reports.offense.report)));
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Before week' }), { target: { value: '3' } });
  fireEvent.click(screen.getByRole('button', { name: 'Build report' }));
  const scoutDownload = await screen.findByRole('link', { name: 'Download report JSON' });
  expect(scoutDownload).toHaveAttribute('href', 'blob:http://localhost/test-2');
  fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  expect(link()).toBe(download); expect(link()).toHaveAttribute('href', 'blob:http://localhost/test-1');
  expect(URL.createObjectURL).toHaveBeenCalledTimes(2); expect(URL.revokeObjectURL).not.toHaveBeenCalled();
  const ids = [...document.querySelectorAll('[id]')].map(node => node.id); expect(new Set(ids).size).toBe(ids.length);
  edit('before_week', '2'); expect(link()).not.toBeInTheDocument();
  expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:http://localhost/test-1');
  fireEvent.click(screen.getByRole('tab', { name: 'Scout' }));
  expect(screen.getByRole('link', { name: 'Download report JSON' })).toBe(scoutDownload);
  result.unmount(); expect(vi.mocked(URL.revokeObjectURL).mock.calls).toEqual([['blob:http://localhost/test-1'], ['blob:http://localhost/test-2']]);
  expect(fetch).toHaveBeenCalledTimes(2);
});

it('removes the old link on resubmit, rejects ignored late responses after edits, and never exports request errors', async () => {
  let finish!: (response: Response) => void;
  vi.mocked(fetch).mockResolvedValueOnce(response(JSON.stringify(fixtures.selected.decision)))
    .mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }))
    .mockRejectedValueOnce(new TypeError('offline'));
  setup(); expect(link()).not.toBeInTheDocument(); submit(); await screen.findByRole('link', { name: 'Download decision JSON' });
  submit(); expect(link()).not.toBeInTheDocument();
  expect(view().getByRole('status')).toHaveTextContent('Loading decision evidence');
  expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:http://localhost/test-1');
  edit('distance_min', '9');
  await act(async () => finish(response(JSON.stringify(fixtures.selected.decision))));
  expect(link()).not.toBeInTheDocument(); expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
  submit(); await view().findByRole('alert'); expect(link()).not.toBeInTheDocument();
  expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
});

it.each(['query', 'mode', 'timeout', 'unmount'])('rejects a late response after %s invalidation without allocating a URL', async invalidation => {
  let finish!: (response: Response) => void;
  vi.mocked(fetch).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  if (invalidation === 'timeout') vi.useFakeTimers();
  const result = setup(); submit();
  const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
  if (invalidation === 'query') edit('team', 'ATL');
  if (invalidation === 'mode') fireEvent.click(screen.getByRole('tab', { name: 'Scout' }));
  if (invalidation === 'unmount') result.unmount();
  if (invalidation === 'timeout') await act(async () => { await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS); });
  expect(signal.aborted).toBe(true);
  await act(async () => finish(response(JSON.stringify(fixtures.selected.decision))));
  if (invalidation === 'mode') fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  expect(link()).not.toBeInTheDocument(); expect(URL.createObjectURL).not.toHaveBeenCalled();
});

it('clears the ready link on invalid input without a request and exports a valid empty result after correction', async () => {
  vi.mocked(fetch).mockResolvedValueOnce(response(JSON.stringify(fixtures.selected.decision)))
    .mockResolvedValueOnce(response(JSON.stringify(fixtures.empty_plain.decision)));
  setup(); submit(); await screen.findByRole('link', { name: 'Download decision JSON' });
  edit('before_week', '0'); expect(link()).not.toBeInTheDocument(); submit();
  expect(view().getByRole('alert')).toBeVisible(); expect(fetch).toHaveBeenCalledTimes(1);
  expect(URL.revokeObjectURL).toHaveBeenCalledExactlyOnceWith('blob:http://localhost/test-1');
  edit('before_week', '1'); submit(); await screen.findByRole('link', { name: 'Download decision JSON' });
  expect(view().getByRole('heading', { name: 'No eligible plays match this situation.' })).toBeVisible();
  expect(await blobText(createdBlob(1))).toBe(JSON.stringify(fixtures.empty_plain.decision));
  expect(link()).toHaveAttribute('download', 'nfl-di-CAR-2024-REG-before-week-1-down-1-distance-10-10.decision.json');
});

it.each(['malformed', 'schema', 'cohort', 'preferred_call', 'non_json', 'http_error'])('never offers a download for invalid %s evidence', async kind => {
  const data = structuredClone(fixtures.selected.decision);
  if (kind === 'schema') Object.assign(data, { contract_version: 2 });
  if (kind === 'cohort') data.cohort.team = 'ATL';
  if (kind === 'preferred_call') Object.assign(data.comparison, { preferred_candidate: 'pass' });
  const reply = kind === 'malformed' ? response('{') : kind === 'non_json' ? new Response('<html>not JSON</html>', { headers: { 'content-type': 'text/html' } })
    : kind === 'http_error' ? new Response('{"error":{"code":"report_busy"}}', { status: 503 }) : response(JSON.stringify(data));
  vi.mocked(fetch).mockResolvedValueOnce(reply); setup(); submit();
  await view().findByRole('alert'); expect(link()).not.toBeInTheDocument(); expect(URL.createObjectURL).not.toHaveBeenCalled();
});
