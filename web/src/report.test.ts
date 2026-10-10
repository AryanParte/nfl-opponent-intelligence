import { describe, expect, it, vi } from 'vitest';
import fixtures from './__fixtures__/reports.json';
import { epa, fetchReport, parseQuery, parseReport, percentage, type Draft, type Query } from './report';

const query = fixtures.offense.query as Query;
const draft: Draft = { team: 'CAR', season: '2024', before_week: '3', side: 'offense', season_type: 'REG', compare_league: false };
const response = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'content-type': 'application/json' } });

describe('consumed report contract', () => {
  it.each(Object.keys(fixtures) as (keyof typeof fixtures)[])('accepts actual synthetic API fixture: %s', (name) => {
    const fixture = fixtures[name];
    expect(parseReport(fixture.report, fixture.query as Query)).toEqual(fixture.report);
  });
  it('preserves independent denominators, nulls and role semantics', () => {
    const report = parseReport(fixtures.offense.report, query);
    expect(report.overall).toMatchObject({ plays: 6, epa_observations: 5, missing_epa: 1, dropback_rate: .5, success_rate: .6 });
    expect(report.overall.epa_per_play).toBeCloseTo(.04);
    expect(fixtures.defense.report.overall.epa_per_play).toBeCloseTo(.05);
    expect(epa(null)).toBe('Unavailable');
    expect(epa(0)).toBe('0.000');
    expect(percentage(null)).toBe('Unavailable');
    expect(percentage(0)).toBe('0.0%');
  });
  it('accepts both UTC timestamp spellings, including fractional acquisition times', () => {
    const report = structuredClone(fixtures.offense.report);
    report.source.snapshot.retrieved_at_utc = '2026-10-08T00:00:00.168819+00:00';
    expect(parseReport(report, query).source.snapshot.retrieved_at_utc).toBe(report.source.snapshot.retrieved_at_utc);
  });
  it.each([
    ['version', (r: any) => { r.schema_version = 1; }],
    ['wrong team', (r: any) => { r.cohort.team = 'ATL'; }],
    ['wrong cutoff', (r: any) => { r.cohort.before_week_exclusive = 4; }],
    ['wrong role', (r: any) => { r.cohort.side = 'defense'; }],
    ['unexpected filters', (r: any) => { r.cohort.period = {}; }],
    ['comparison', (r: any) => { r.league_comparison = {}; }],
    ['uncertainty', (r: any) => { r.uncertainty = null; }],
    ['perspective', (r: any) => { r.metric_context.perspective = 'defense'; }],
    ['success definition', (r: any) => { r.metric_context.success_condition = 'yards > 0'; }],
    ['missing provenance', (r: any) => { delete r.source.snapshot; }],
    ['inconsistent source hash', (r: any) => { r.source.sha256 = '0'.repeat(64); }],
    ['invalid timestamp', (r: any) => { r.source.snapshot.retrieved_at_utc = 'yesterday'; }],
    ['impossible date', (r: any) => { r.source.snapshot.retrieved_at_utc = '2026-02-30T00:00:00Z'; }],
    ['missing attribution', (r: any) => { delete r.source.snapshot.license; }],
    ['nonfinite metric', (r: any) => { r.overall.epa_per_play = Infinity; }],
    ['impossible rate', (r: any) => { r.overall.success_rate = 1.1; }],
    ['wrong denominator', (r: any) => { r.overall.missing_epa = 0; }],
    ['coerced number', (r: any) => { r.overall.plays = '6'; }],
    ['wrong sample flag', (r: any) => { r.overall.small_sample = false; }],
    ['duplicate bucket', (r: any) => { r.situations.push(r.situations[0]); }],
    ['missing bucket', (r: any) => { r.situations.pop(); }],
    ['inconsistent bucket EPA counts', (r: any) => { r.situations[0].epa_observations -= 1; r.situations[0].missing_epa += 1; }],
    ['unobserved empty bucket', (r: any) => { r.situations.push({ ...fixtures.empty.report.overall, down: 4, distance: 'short' }); }],
    ['wrong warning type', (r: any) => { r.warnings = [42]; }],
  ])('rejects %s instead of displaying misidentified/invalid measurements', (_name, mutate) => {
    const report = structuredClone(fixtures.offense.report);
    mutate(report);
    expect(() => parseReport(report, query)).toThrow('incompatible report');
  });
});

describe('request boundary', () => {
  it('accepts the UI request and validates numbers before sending', () => {
    expect(parseQuery(draft)).toEqual(query);
    for (const change of [{ team: '../' }, { team: 'car' }, { season: '' }, { before_week: '0' },
      { before_week: '24' }, { before_week: '3.5' }, { side: 'both' }, { season_type: 'PRE' }]) {
      expect(() => parseQuery({ ...draft, ...change })).toThrow('Use a 2–3 letter');
    }
  });
  it('sends only the narrow same-origin query and preserves the signal', async () => {
    const fetcher = vi.mocked(fetch).mockResolvedValue(response(fixtures.offense.report));
    const controller = new AbortController();
    expect(await fetchReport(query, controller.signal)).toEqual(fixtures.offense.report);
    const [url, options] = fetcher.mock.calls[0];
    expect(url).toBe('/api/v1/report?team=CAR&season=2024&before_week=3&side=offense&season_type=REG');
    expect(options).toMatchObject({ signal: controller.signal, credentials: 'omit', cache: 'no-store', redirect: 'error' });
    expect(options).not.toHaveProperty('body');
  });
  it.each([
    [422, 'season_unavailable', 'That season is not in the configured snapshot'],
    [503, 'report_busy', 'The API is building another report'],
    [503, 'snapshot_not_ready', 'The API snapshot is not ready'],
    [500, 'unexpected', 'Report request failed (HTTP 500)'],
    [500, 'toString', 'Report request failed (HTTP 500)'],
  ])('handles HTTP %i / %s without echoing exception text', async (status, code, message) => {
    vi.mocked(fetch).mockResolvedValue(response({ error: { code, message: '/private/secrets' } }, status));
    await expect(fetchReport(query, new AbortController().signal)).rejects.toThrow(message);
  });
  it('handles an HTML proxy failure and a non-JSON successful response', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response('<h1>Proxy error</h1>', { status: 502 }));
    await expect(fetchReport(query, new AbortController().signal)).rejects.toThrow('HTTP 502');
    for (const mime of ['text/html', 'application/jsonp']) {
      vi.mocked(fetch).mockResolvedValueOnce(new Response('{}', { headers: { 'content-type': mime } }));
      await expect(fetchReport(query, new AbortController().signal)).rejects.toThrow('did not return JSON');
    }
  });
});
