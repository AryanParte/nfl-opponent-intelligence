import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { App } from './App';
import { UncertaintyView, intervalValue } from './UncertaintyView';
import fixtures from './__fixtures__/uncertainty-reports.json';
import original from './__fixtures__/reports.json';
import { fetchReport, parseQuery, parseReport, type Draft, type Query } from './report';

const query = fixtures.comparison.query as Query;
const draft: Draft = { team: 'CAR', season: '2024', before_week: '19', side: 'offense', season_type: 'REG',
  compare_league: true, yardline_min: '', yardline_max: '', score_min: '', score_max: '', period: '', clock_min: '', clock_max: '',
  bootstrap_repetitions: '', bootstrap_seed: '' };
const reply = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'content-type': 'application/json' } });
const inputs = () => [screen.getByRole('textbox', { name: 'Bootstrap repetitions' }), screen.getByRole('textbox', { name: 'Bootstrap seed' })];
const change = (element: HTMLElement, value: string) => fireEvent.change(element, { target: { value } });
const submit = () => userEvent.click(screen.getByRole('button', { name: 'Build report' }));
function setup() {
  render(<App />);
  fireEvent.click(screen.getByRole('checkbox'));
  change(inputs()[0], '200'); change(inputs()[1], '7');
}

describe('opt-in bootstrap request boundary', () => {
  it.each([
    ['', '', {}], [' ', ' ', {}], ['200', '', { bootstrap_repetitions: 200 }],
    ['200', '0', { bootstrap_repetitions: 200, bootstrap_seed: 0 }],
    [' 1000 ', '4294967295', { bootstrap_repetitions: 1000, bootstrap_seed: 4294967295 }],
  ])('preserves omission, API defaults and inclusive limits: %j / %j', (repetitions, seed, expected) => {
    const { bootstrap_repetitions: _b, bootstrap_seed: _s, ...base } = query;
    expect(parseQuery({ ...draft, bootstrap_repetitions: repetitions, bootstrap_seed: seed })).toEqual({ ...base, ...expected });
  });
  it.each(['0', '199', '1001', '-200', '+200', '200.0', '2e2', '0xC8', 'NaN', 'Infinity', '200 draws'])('rejects repetitions %j', value => {
    expect(() => parseQuery({ ...draft, bootstrap_repetitions: value })).toThrow('Bootstrap repetitions');
  });
  it.each(['-1', '+1', '1.0', '1e2', '0x10', 'NaN', 'Infinity', '4294967296', '1 seed'])('rejects seed %j', value => {
    expect(() => parseQuery({ ...draft, bootstrap_repetitions: '200', bootstrap_seed: value })).toThrow('seed must');
  });
  it('requires repetitions even for a zero seed', () => {
    expect(() => parseQuery({ ...draft, bootstrap_seed: '0' })).toThrow('seed requires repetitions');
  });
  it.each(['selected', 'defense', 'context'] as const)('sends only explicit options, never paths or downloads: %s', async name => {
    const f = fixtures[name]; vi.mocked(fetch).mockResolvedValueOnce(reply(f.report));
    const controller = new AbortController(); await fetchReport(f.query as Query, controller.signal);
    const [url, options] = vi.mocked(fetch).mock.lastCall!;
    expect(Object.fromEntries(new URL(String(url), 'http://localhost').searchParams)).toEqual(Object.fromEntries(Object.entries(f.query)
      .filter(([, v]) => v !== false).map(([k, v]) => [k, String(v)])));
    expect(options).toMatchObject({ signal: controller.signal, credentials: 'omit', cache: 'no-store', redirect: 'error' });
  });
});

describe('returned uncertainty contract and independent support expectations', () => {
  it.each(Object.keys(fixtures) as (keyof typeof fixtures)[])('accepts the actual synthetic API response: %s', name => {
    const f = fixtures[name]; expect(parseReport(f.report, f.query as Query)).toEqual(f.report);
  });
  it('preserves pooled estimates, shared-game union and paired differences', () => {
    const r = parseReport(fixtures.comparison.report, query), u = r.uncertainty!;
    expect(r.overall).toMatchObject({ games: 5, plays: 15, dropbacks: 9, epa_observations: 15, success_rate: 9 / 15, epa_per_play: 10 / 15 });
    expect(u.resampling_games).toBe(5); // Not 5 selected + 5 baseline = 10.
    expect(u.overall.selected.epa_per_play.support_games).toEqual({ selected: 5 });
    expect(u.overall.difference!.epa_per_play).toMatchObject({ status: 'degenerate_interval', interval: null,
      support_games: { selected: 5, baseline: 5 }, valid_replicates: 200, undefined_replicates: 0 });
    expect(r.league_comparison!.overall_difference.epa_per_play).toBeCloseTo(-3);
    expect(fixtures.many_games.report.uncertainty.overall.selected.epa_per_play.few_games).toBe(false);
  });
  it('keeps play support, observed-EPA support, empty frames and absent baseline buckets separate', () => {
    const partial = fixtures.partial_epa.report.uncertainty.overall.selected;
    expect(partial.dropback_rate.support_games).toEqual({ selected: 5 });
    expect(partial.epa_per_play.support_games).toEqual({ selected: 1 });
    expect(partial.epa_per_play.status).toBe('insufficient_games');
    expect(fixtures.missing_epa.report.uncertainty.overall.selected.epa_per_play).toMatchObject({
      status: 'undefined_estimate', interval: null, valid_replicates: 0, undefined_replicates: 200 });
    expect(fixtures.empty.report.uncertainty).toMatchObject({ performed_repetitions: 0, resampling_games: 0 });
    expect(fixtures.empty_selected.report.uncertainty).toMatchObject({ performed_repetitions: 200, resampling_games: 5 });
    const bucket = fixtures.baseline_only_bucket.report.uncertainty.situations[0];
    expect(bucket.baseline.epa_per_play).toMatchObject({ status: 'undefined_estimate', support_games: { baseline: 0 } });
    expect(bucket.difference.epa_per_play.support_games).toEqual({ selected: 5, baseline: 0 });
  });
  it('keeps the exact 190/200 gate separate from the few-game warning (controlled synthetic draws)', () => {
    expect(fixtures.sparse_draws.report.uncertainty.overall.selected.epa_per_play).toMatchObject({
      status: 'too_few_valid_replicates', interval: null, valid_replicates: 189, undefined_replicates: 11, few_games: true });
    expect(fixtures.valid_boundary.report.uncertainty.overall.selected.epa_per_play).toMatchObject({
      status: 'ok', valid_replicates: 190, undefined_replicates: 10, few_games: true });
    expect(fixtures.sparse_draws.report.source.label).toContain('not a seed replay');
  });
  it('adds uncertainty without changing any combined-filter counts or estimates', () => {
    const r = fixtures.context.report, plain = original.time_four_stage.report;
    for (const key of ['cohort', 'overall', 'situations', 'data_quality', 'league_comparison'] as const) expect(r[key]).toEqual(plain[key]);
  });
  it.each([157, 159])('rejects impossible paired valid counts %i when one side has 200 and the other 158', valid => {
    const r = structuredClone(fixtures.small.report);
    for (const item of Object.values(r.uncertainty.overall.difference)) { item.valid_replicates = valid; item.undefined_replicates = 200 - valid; }
    expect(() => parseReport(r, fixtures.small.query as Query)).toThrow('incompatible report');
  });
  it.each([
    ['method', 'other'], ['nominal_level', .9], ['repetitions', 201], ['performed_repetitions', 199], ['seed', 0],
    ['random_generator', 'browser'], ['quantile_method', 'nearest'], ['resampling_unit', 'play_id'],
    ['resampling_games', 10], ['resampling_population', 'selected'], ['shared_game_weights', false],
    ['minimum_support_games', 4], ['few_games_warning_below', 19], ['minimum_valid_fraction', .9], ['warnings', [4]],
  ])('rejects incompatible metadata %s', (key, value) => {
    const r: any = structuredClone(fixtures.comparison.report); r.uncertainty[key] = value;
    expect(() => parseReport(r, query)).toThrow('incompatible report');
  });
  it.each([
    ['missing', (r: any) => { delete r.uncertainty; }], ['null', (r: any) => { r.uncertainty = null; }],
    ['unknown population', (r: any) => { r.uncertainty.overall.adjusted = {}; }],
    ['missing baseline', (r: any) => { delete r.uncertainty.overall.baseline; }],
    ['missing difference', (r: any) => { delete r.uncertainty.overall.difference; }],
    ['missing metric', (r: any) => { delete r.uncertainty.overall.selected.success_rate; }],
    ['extra metric', (r: any) => { r.uncertainty.overall.selected.yards = {}; }],
    ['missing bucket', (r: any) => { r.uncertainty.situations.pop(); }],
    ['extra bucket', (r: any) => { r.uncertainty.situations.push(r.uncertainty.situations[0]); }],
    ['wrong bucket', (r: any) => { r.uncertainty.situations[0].distance = 'short'; }],
    ['wrong baseline units', (r: any) => { r.uncertainty.overall.baseline.dropback_rate.unit = 'percentage_points'; }],
    ['wrong difference units', (r: any) => { r.uncertainty.overall.difference.dropback_rate_pp.unit = 'proportion'; }],
    ['wrong paired support', (r: any) => { r.uncertainty.overall.difference.epa_per_play.support_games.baseline = 4; }],
    ['numeric bounds on degenerate', (r: any) => { r.uncertainty.overall.difference.epa_per_play.interval = { lower: -3, upper: -3 }; }],
    ['wrong EPA draw support', (r: any) => { r.uncertainty.overall.selected.success_rate.support_games.selected = 4; }],
  ])('rejects broken structure/paired semantics: %s', (_name, mutate) => {
    const r = structuredClone(fixtures.comparison.report); mutate(r); expect(() => parseReport(r, query)).toThrow('incompatible report');
  });
  it.each([
    ['fractional support', (v: any) => { v.support_games.selected = 4.5; }],
    ['negative support', (v: any) => { v.support_games.selected = -1; }],
    ['excess support', (v: any) => { v.support_games.selected = 6; }],
    ['missing support', (v: any) => { v.support_games = {}; }],
    ['unexpected support side', (v: any) => { v.support_games.baseline = 5; }],
    ['wrong few flag', (v: any) => { v.few_games = false; }],
    ['missing status', (v: any) => { delete v.status; }], ['unknown status', (v: any) => { v.status = 'confident'; }],
    ['wrong precedence', (v: any) => { v.status = 'insufficient_games'; v.interval = null; }],
    ['null available bounds', (v: any) => { v.interval = null; }],
    ['nonfinite bounds', (v: any) => { v.interval.lower = -Infinity; }],
    ['reversed bounds', (v: any) => { v.interval = { lower: 2, upper: 1 }; }],
    ['equal bounds', (v: any) => { v.interval = { lower: 1, upper: 1 }; }],
    ['near-equal bounds', (v: any) => { v.interval = { lower: 1, upper: 1 + 1e-13 }; }],
    ['string bounds', (v: any) => { v.interval.upper = '2'; }],
    ['missing bound', (v: any) => { delete v.interval.lower; }],
    ['extra bound', (v: any) => { v.interval.middle = 0; }],
    ['fractional draws', (v: any) => { v.valid_replicates = 199.5; v.undefined_replicates = .5; }],
    ['incorrect total draws', (v: any) => { v.undefined_replicates = 1; }],
    ['impossible undefined draw from full frame', (v: any) => { v.valid_replicates = 199; v.undefined_replicates = 1; }],
  ])('rejects invalid interval/support: %s', (_name, mutate) => {
    const r = structuredClone(fixtures.comparison.report); mutate(r.uncertainty.overall.selected.epa_per_play);
    expect(() => parseReport(r, query)).toThrow('incompatible report');
  });
  it('validates rate/pp bounds without treating EPA as a proportion or requiring point containment', () => {
    const r: any = structuredClone(fixtures.comparison.report);
    for (const [population, key, lower, upper] of [['selected', 'dropback_rate', -.1, .5], ['baseline', 'dropback_rate', 0, 1.1],
      ['difference', 'dropback_rate_pp', -101, 0], ['difference', 'dropback_rate_pp', 0, 101]] as const) {
      const changed = structuredClone(r); changed.uncertainty.overall[population][key].interval = { lower, upper };
      expect(() => parseReport(changed, query)).toThrow('incompatible report');
    }
    r.uncertainty.overall.selected.epa_per_play.interval = { lower: -4, upper: -3 };
    expect(() => parseReport(r, query)).not.toThrow(); // Percentile intervals need not contain the point estimate.
  });
  it('rejects fabricated gates, zero support draws and situation/overall contradictions', () => {
    const sparse = structuredClone(fixtures.sparse_draws.report);
    sparse.uncertainty.overall.selected.epa_per_play.status = 'degenerate_interval';
    expect(() => parseReport(sparse, fixtures.sparse_draws.query as Query)).toThrow('incompatible report');
    const empty = structuredClone(fixtures.empty_selected.report);
    empty.uncertainty.overall.selected.epa_per_play.valid_replicates = 1;
    empty.uncertainty.overall.selected.epa_per_play.undefined_replicates = 199;
    expect(() => parseReport(empty, fixtures.empty_selected.query as Query)).toThrow('incompatible report');
    const partial: any = structuredClone(fixtures.partial_epa.report);
    for (const key of ['success_rate', 'epa_per_play']) {
      partial.uncertainty.situations[0].selected[key].valid_replicates++;
      partial.uncertainty.situations[0].selected[key].undefined_replicates--;
      // Preserve paired counts so this specifically reaches the subset guard.
      const difference = partial.uncertainty.situations[0].difference[key === 'success_rate' ? 'success_rate_pp' : key];
      difference.valid_replicates++; difference.undefined_replicates--;
    }
    expect(() => parseReport(partial, fixtures.partial_epa.query as Query)).toThrow('incompatible report');
  });
  it('joins situations by key, permits reordered rows, rejects duplicate replacement and unrequested sections', () => {
    const f = fixtures.small, r = structuredClone(f.report); r.uncertainty.situations.reverse();
    expect(() => parseReport(r, f.query as Query)).not.toThrow();
    r.uncertainty.situations[0] = r.uncertainty.situations[1];
    expect(() => parseReport(r, f.query as Query)).toThrow('incompatible report');
    const plain = { ...original.offense.report, uncertainty: fixtures.small.report.uncertainty };
    expect(() => parseReport(plain, original.offense.query as Query)).toThrow('incompatible report');
  });
});

describe('uncertainty display and request lifecycle', () => {
  it('formats rates as percents, differences as pp, and EPA without changing its offensive sign', () => {
    expect(intervalValue(.125, 'proportion')).toBe('12.5%');
    expect(intervalValue(-12.5, 'percentage_points')).toBe('-12.5 pp');
    expect(intervalValue(-1.25, 'expected_points_per_observed_play')).toBe('-1.250 EPA/play');
    expect(intervalValue(null, 'proportion')).toBe('Unavailable');
  });
  it.each(Object.keys(fixtures) as (keyof typeof fixtures)[])('renders returned values and all warnings without resampling: %s', name => {
    const f = fixtures[name], r = parseReport(f.report, f.query as Query);
    render(<UncertaintyView report={r} />);
    const region = within(screen.getByRole('region', { name: 'Exploratory game-level uncertainty' }));
    const table = within(region.getByRole('table', { name: 'Overall uncertainty' }));
    const rows = table.getAllByRole('row');
    expect(rows).toHaveLength(r.league_comparison ? 10 : 4);
    const selected = r.uncertainty!.overall.selected;
    for (const [index, key] of ['dropback_rate', 'success_rate', 'epa_per_play'].entries()) {
      const item = selected[key as keyof typeof selected];
      expect(within(rows[index + 1]).getAllByRole('cell')[0]).toHaveTextContent(intervalValue(r.overall[key as keyof typeof selected], item.unit));
      expect(within(rows[index + 1]).getAllByRole('cell')[3]).toHaveTextContent(`${item.valid_replicates.toLocaleString('en-US')} / ${item.undefined_replicates}`);
    }
    for (const warning of r.uncertainty!.warnings) expect(region.getByText(warning)).toBeVisible();
    expect(region.getByText(/These are application safeguards, not reliability guarantees/)).toBeVisible();
    expect(region.getByText(/EPA keeps its offensive sign/)).toBeVisible();
    expect(region.getByText(/No browser resampling or endpoint subtraction/)).toBeVisible();
    expect(fetch).not.toHaveBeenCalled();
  });
  it.each([
    ['missing_epa', /Undefined estimate · no contributing games/], ['partial_epa', /Withheld · fewer than 5 contributing games/],
    ['sparse_draws', /Withheld · fewer than 95% defined draws/], ['comparison', /Withheld · constant \/ near-constant interval/],
    ['many_games', /No few-game flag; not a reliability guarantee/],
  ] as const)('makes %s states explicit, never zero-width certainty', (name, message) => {
    const f = fixtures[name]; render(<UncertaintyView report={parseReport(f.report, f.query as Query)} />);
    expect(screen.getAllByText(message)[0]).toBeVisible();
  });
  it('starts blank with no automatic request, and handles invalid text without silent fallback', async () => {
    render(<App />); for (const input of inputs()) expect(input).toHaveValue('');
    expect(fetch).not.toHaveBeenCalled(); change(inputs()[0], '2e2'); await submit();
    expect(inputs()[0]).toHaveValue('2e2'); expect(screen.getByRole('alert')).toHaveTextContent('Bootstrap repetitions');
    change(inputs()[0], ''); change(inputs()[1], '0'); await submit();
    expect(screen.getByRole('alert')).toHaveTextContent('seed requires repetitions'); expect(fetch).not.toHaveBeenCalled();
  });
  it('clears both fields to a normal report; clearing just repetitions preserves seed and prevents a request', async () => {
    const plain = structuredClone(fixtures.comparison.report) as any; delete plain.uncertainty;
    vi.mocked(fetch).mockResolvedValueOnce(reply(fixtures.comparison.report)).mockResolvedValueOnce(reply(plain));
    setup(); await submit(); await screen.findByRole('heading', { name: 'Exploratory game-level uncertainty' });
    change(inputs()[0], ''); expect(inputs()[1]).toHaveValue('7'); expect(screen.queryByRole('article')).not.toBeInTheDocument();
    await submit(); expect(screen.getByRole('alert')).toHaveTextContent('seed requires repetitions'); expect(fetch).toHaveBeenCalledTimes(1);
    change(inputs()[1], ''); await submit(); await screen.findByRole('article');
    expect(screen.queryByRole('heading', { name: 'Exploratory game-level uncertainty' })).not.toBeInTheDocument();
    expect(String(vi.mocked(fetch).mock.lastCall![0])).not.toContain('bootstrap_');
  });
  it.each([0, 1])('aborts stale work when bootstrap input %i changes, without auto-running', async index => {
    let finish!: (response: Response) => void;
    vi.mocked(fetch).mockImplementation(() => new Promise(resolve => { finish = resolve; })); setup(); await submit();
    const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
    change(inputs()[index], index ? '8' : '201'); expect(signal.aborted).toBe(true);
    await act(async () => { finish(reply(fixtures.comparison.report)); });
    expect(screen.queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
  });
  it('surfaces busy safely, leaves bounded inputs intact and retries only on submit', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(reply({ error: { code: 'report_busy', message: '/private/source' } }, 503))
      .mockResolvedValueOnce(reply(fixtures.comparison.report)); setup(); await submit();
    expect(await screen.findByRole('alert')).toHaveTextContent('building another report');
    expect(screen.getByRole('alert')).not.toHaveTextContent('/private/source'); expect(fetch).toHaveBeenCalledTimes(1);
    expect(inputs()[0]).toHaveValue('200'); expect(inputs()[1]).toHaveValue('7');
    await submit(); expect(await screen.findByRole('heading', { name: 'Exploratory game-level uncertainty' })).toBeVisible();
  });
  it('escapes returned uncertainty warnings as text', () => {
    const r = parseReport(fixtures.selected.report, fixtures.selected.query as Query);
    r.uncertainty!.warnings.push('<img src=x onerror=alert(1)>'); render(<UncertaintyView report={r} />);
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeVisible(); expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });
  it('shows zero bucket support instead of substituting the valid overall baseline', async () => {
    const f = fixtures.baseline_only_bucket; render(<UncertaintyView report={parseReport(f.report, f.query as Query)} />);
    await userEvent.click(screen.getByText('1 / long · interval support'));
    const table = within(screen.getByRole('table', { name: '1 / long uncertainty' }));
    const row = within(table.getByRole('row', { name: /^Baseline \/ EPA \/ observed play / }));
    expect(row.getAllByRole('cell')[0]).toHaveTextContent('Unavailable');
    expect(row.getAllByRole('cell')[2]).toHaveTextContent('Baseline 0');
    expect(row.getAllByRole('cell')[4]).toHaveTextContent('Undefined estimate');
  });
});
