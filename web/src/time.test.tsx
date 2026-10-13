import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { App } from './App';
import fixtures from './__fixtures__/reports.json';
import { fetchReport, parseQuery, parseReport, PERIODS, type Draft, type Query } from './report';

const fixture = fixtures.time_four_stage;
const query = fixture.query as Query;
const draft: Draft = { team: 'CAR', season: '2024', before_week: '3', side: 'offense', season_type: 'REG',
  compare_league: true, yardline_min: '', yardline_max: '', score_min: '', score_max: '', period: '', clock_min: '', clock_max: '' };
const reply = (value: unknown, status = 200) => new Response(JSON.stringify(value), {
  status, headers: { 'content-type': 'application/json' },
});
const periodInput = () => screen.getByRole('combobox', { name: 'Period' });
const bounds = () => [screen.getByRole('textbox', { name: 'Minimum seconds remaining' }),
  screen.getByRole('textbox', { name: 'Maximum seconds remaining' })];
const change = (input: HTMLElement, value: string) => fireEvent.change(input, { target: { value } });
const submit = () => userEvent.click(screen.getByRole('button', { name: 'Build report' }));
function setup(q: Query = query) {
  render(<App />);
  change(screen.getByRole('textbox', { name: 'Team code' }), q.team);
  change(screen.getByRole('spinbutton', { name: 'Before week' }), String(q.before_week));
  change(screen.getByRole('combobox', { name: 'Role' }), q.side);
  change(periodInput(), q.period ?? '');
  for (const [label, key] of [['Minimum yards to goal', 'yardline_min'], ['Maximum yards to goal', 'yardline_max'],
    ['Minimum score difference', 'score_min'], ['Maximum score difference', 'score_max'],
    ['Minimum seconds remaining', 'clock_min'], ['Maximum seconds remaining', 'clock_max']] as const) {
    change(screen.getByRole('textbox', { name: label }), q[key] === undefined ? '' : String(q[key]));
  }
  if (q.compare_league) fireEvent.click(screen.getByRole('checkbox'));
}

describe('explicit period and optional whole-second clock request', () => {
  it.each(['', ...PERIODS])('accepts period %j without adding a clock filter', period => {
    expect(parseQuery({ ...draft, period })).toEqual({ ...fixtures.time_unfiltered.query, ...(period ? { period } : {}) });
  });
  it.each(['Q5', 'q4', '4', 'OT2', ' Q4 ', 'ALL'])('rejects unsupported period %j', period => {
    expect(() => parseQuery({ ...draft, period })).toThrow('Choose Q1');
  });
  it.each([
    ['', '', {}], [' ', ' ', {}], ['', '120', { clock_max: 120 }], ['900', '', { clock_min: 900 }],
    ['0', '0', { clock_min: 0, clock_max: 0 }], [' 0 ', '900', { clock_min: 0, clock_max: 900 }],
  ])('keeps entered clock ends %j / %j, including zero', (lower, upper, expected) => {
    expect(parseQuery({ ...draft, period: 'Q4', clock_min: lower, clock_max: upper }))
      .toEqual({ ...fixtures.time_period.query, ...expected });
  });
  it.each(['-1', '+1', '1.0', '.5', '1e2', '0x10', 'NaN', 'Infinity', '901', '2:00', '120 seconds'])('rejects clock %j', value => {
    for (const key of ['clock_min', 'clock_max']) expect(() => parseQuery({ ...draft, period: 'Q4', [key]: value })).toThrow('whole seconds');
  });
  it('requires a period even for zero and rejects reversed bounds', () => {
    for (const key of ['clock_min', 'clock_max']) expect(() => parseQuery({ ...draft, [key]: '0' })).toThrow('explicit period');
    expect(() => parseQuery({ ...draft, period: 'Q4', clock_min: '121', clock_max: '120' })).toThrow('must not exceed');
  });
  it('sends only the explicit narrow query, never a path, download or implicit clock default', async () => {
    for (const name of ['time_period', 'time_offense', 'time_lower_only', 'time_zero', 'time_ot', 'time_four_stage'] as const) {
      const chosen = fixtures[name]; vi.mocked(fetch).mockResolvedValueOnce(reply(chosen.report));
      await fetchReport(chosen.query as Query, new AbortController().signal);
      const url = new URL(String(vi.mocked(fetch).mock.lastCall![0]), 'http://localhost');
      expect(url.pathname).toBe('/api/v1/report');
      expect(Object.fromEntries(url.searchParams)).toEqual(Object.fromEntries(Object.entries(chosen.query)
        .filter(([, v]) => v !== false).map(([k, v]) => [k, String(v)])));
    }
  });
});

describe('time-context identity and independently counted synthetic populations', () => {
  it('distinguishes period-only, absent clock column, full clock range, zero, null EPA and multi-period OT', () => {
    expect(fixtures.time_unfiltered.report.overall.plays).toBe(15);
    for (const name of ['time_period', 'time_period_no_clock'] as const) {
      expect(fixtures[name].report.overall.plays).toBe(8);
      expect(fixtures[name].report.cohort).not.toHaveProperty('clock');
      expect(fixtures[name].report.data_quality).not.toHaveProperty('clock_filter');
    }
    expect(fixtures.time_period.report.source.sha256).toBe(fixtures.time_full_clock.report.source.sha256);
    expect(fixtures.time_full_clock.report.overall.plays).toBe(7); // Same bytes, explicit range excludes one missing clock.
    expect(fixtures.time_zero.report.overall).toMatchObject({ plays: 1, dropbacks: 0, epa_per_play: -.4, success_rate: 0 });
    expect(fixtures.time_lower_only.report.overall).toMatchObject({ plays: 1, epa_observations: 0, missing_epa: 1, epa_per_play: null });
    expect(fixtures.time_lower_only.report.cohort.clock).toMatchObject({ minimum_inclusive: 900, maximum_inclusive: 900 });
    expect(fixtures.time_offense.report.overall).toMatchObject({ plays: 5, dropbacks: 3, epa_observations: 4, missing_epa: 1, success_rate: .75 });
    expect(fixtures.time_offense.report.overall.epa_per_play).toBeCloseTo(.35, 12);
    expect(fixtures.time_defense.report.overall).toEqual(fixtures.time_offense.report.overall); // ATL allows CAR's production: no sign flip.
    expect(fixtures.time_ot.report.cohort.period).toMatchObject({ minimum_inclusive: 5, maximum_inclusive: null });
    expect(fixtures.time_ot.report.overall).toMatchObject({ plays: 2, dropbacks: 1, success_rate: .5 }); // Periods 5 AND 6.
    expect(fixtures.time_ot.report.overall.epa_per_play).toBeCloseTo(-.1, 12);
    expect(fixtures.time_q1.report.overall).toMatchObject({ plays: 1, epa_per_play: .2 });
    expect(fixtures.time_q2.report.overall).toMatchObject({ plays: 1, epa_per_play: -.2 });
    expect(fixtures.time_q3.report.overall).toMatchObject({ plays: 1, epa_per_play: .1 });
  });
  it('reconciles all four stages without double-counting overlapping missing fields or using retained leave-team-out counts', () => {
    const r = parseReport(fixture.report, query), base = r.league_comparison!;
    expect(r.data_quality).toMatchObject({ input_rows: 23, eligible_rows_all_teams: 22, eligible_rows_outside_cohort: 19,
      filter_order: ['field_position', 'score_differential', 'period', 'clock'],
      field_position_filter: { plays_before_filter: 15, missing_yardline_100: 2, outside_range: 1, plays_after_filter: 12 },
      score_differential_filter: { plays_before_filter: 12, missing_score_differential: 1, outside_range: 0, plays_after_filter: 11 },
      period_filter: { plays_before_filter: 11, missing_qtr: 1, outside_period: 5, plays_after_filter: 5 },
      clock_filter: { plays_before_filter: 5, missing_quarter_seconds_remaining: 1, outside_range: 1, plays_after_filter: 3 } });
    expect(base.data_quality).toEqual({ eligible_rows_same_season_type_before_week: 20, excluded_selected_team_rows: 15,
      plays_before_context_filters: 5, plays_after_context_filters: 1, filter_order: ['field_position', 'score_differential', 'period', 'clock'],
      field_position_filter: { plays_before_filter: 5, missing_yardline_100: 1, outside_range: 0, plays_after_filter: 4 },
      score_differential_filter: { plays_before_filter: 4, missing_score_differential: 0, outside_range: 0, plays_after_filter: 4 },
      period_filter: { plays_before_filter: 4, missing_qtr: 1, outside_period: 1, plays_after_filter: 2 },
      clock_filter: { plays_before_filter: 2, missing_quarter_seconds_remaining: 1, outside_range: 0, plays_after_filter: 1 } });
    expect(r.overall).toMatchObject({ plays: 3, games: 1, dropbacks: 1, epa_observations: 2, missing_epa: 1, epa_per_play: .2, success_rate: .5 });
    expect(base.overall).toMatchObject({ plays: 1, epa_per_play: 3 });
    expect(base.population).toMatchObject({ team_count: 1, shared_games_with_selected: 1 });
    expect(fixtures.time_four_stage_defense.report.overall).toEqual(r.overall);
    expect(fixtures.time_period.report.data_quality.period_filter).toEqual({
      plays_before_filter: 15, missing_qtr: 2, outside_period: 5, plays_after_filter: 8 });
    expect(fixtures.time_all_missing_period.report.data_quality.clock_filter.plays_before_filter).toBe(0);
    expect(fixtures.time_all_missing_clock.report.data_quality.clock_filter.missing_quarter_seconds_remaining).toBe(8);
    for (const name of ['time_all_missing_period', 'time_all_missing_clock', 'time_empty_field', 'time_before_first_week'] as const) {
      expect(fixtures[name].report.overall).toMatchObject({ plays: 0, games: 0, dropback_rate: null, epa_per_play: null });
    }
    expect(fixtures.time_missing_baseline_clock.report.league_comparison.overall.plays).toBe(0);
  });
  it('requires exactly the submitted contexts and resolved bounds, not an implicit or hidden clock stage', () => {
    for (const changed of [{ period: undefined }, { period: 'OT' as const }, { clock_max: undefined }, { clock_max: 0 }, { clock_min: 1 }]) {
      expect(() => parseReport(fixture.report, { ...query, ...changed })).toThrow('incompatible');
    }
    for (const [name, other] of [['time_period', 'time_full_clock'], ['time_full_clock', 'time_period'], ['time_unfiltered', 'time_period']] as const) {
      expect(() => parseReport(fixtures[name].report, fixtures[other].query as Query)).toThrow('incompatible');
    }
    for (const population of ['selected', 'baseline']) {
      const r = structuredClone(fixtures.time_ot.report);
      (population === 'selected' ? r : r.league_comparison).cohort.period.maximum_inclusive = 5 as any;
      expect(() => parseReport(r, fixtures.time_ot.query as Query)).toThrow('incompatible');
    }
  });
  for (const population of ['selected', 'baseline'] as const) {
    it.each([
      ['missing period identity', (r: any) => { delete r.cohort.period; }],
      ['wrong period label', (r: any) => { r.cohort.period.label = 'OT'; }],
      ['wrong period field', (r: any) => { r.cohort.period.field = 'quarter'; }],
      ['period includes OT', (r: any) => { r.cohort.period.maximum_inclusive = null; }],
      ['imputed period', (r: any) => { r.cohort.period.missing_policy = 'zero'; }],
      ['game clock', (r: any) => { r.cohort.clock.field = 'game_seconds_remaining'; }],
      ['elapsed time', (r: any) => { r.cohort.clock.timing = 'post_play'; }],
      ['minutes', (r: any) => { r.cohort.clock.unit = 'minutes'; }],
      ['null lower clock default', (r: any) => { r.cohort.clock.minimum_inclusive = null; }],
      ['wrong clock end', (r: any) => { r.cohort.clock.maximum_inclusive = 900; }],
      ['imputed clock', (r: any) => { r.cohort.clock.missing_policy = 'zero'; }],
      ['missing order', (r: any) => { delete r.data_quality.filter_order; }],
      ['clock before period', (r: any) => { r.data_quality.filter_order = ['field_position', 'score_differential', 'clock', 'period']; }],
      ['omitted order stage', (r: any) => { r.data_quality.filter_order.pop(); }],
      ['missing period ledger', (r: any) => { delete r.data_quality.period_filter; }],
      ['missing clock ledger', (r: any) => { delete r.data_quality.clock_filter; }],
      ['wrong period outside key', (r: any) => { r.data_quality.period_filter.outside_range = r.data_quality.period_filter.outside_period; delete r.data_quality.period_filter.outside_period; }],
      ['fractional missing', (r: any) => { r.data_quality.period_filter.missing_qtr = .5; }],
      ['coerced count', (r: any) => { r.data_quality.clock_filter.plays_before_filter = '5'; }],
      ['negative count', (r: any) => { r.data_quality.clock_filter.outside_range = -1; }],
      ['unbalanced stage', (r: any) => { r.data_quality.period_filter.missing_qtr += 1; }],
      ['disconnected score/period', (r: any) => { r.data_quality.period_filter.plays_before_filter += 1; r.data_quality.period_filter.missing_qtr += 1; }],
      ['disconnected period/clock', (r: any) => { r.data_quality.clock_filter.plays_before_filter += 1; r.data_quality.clock_filter.missing_quarter_seconds_remaining += 1; }],
      ['wrong final count', (r: any) => { r.data_quality.clock_filter.plays_after_filter += 1; r.data_quality.clock_filter.missing_quarter_seconds_remaining -= 1; }],
    ])(`rejects ${population} %s`, (_name, mutate) => {
      const r = structuredClone(fixture.report); mutate(population === 'selected' ? r : r.league_comparison);
      expect(() => parseReport(r, query)).toThrow('incompatible');
    });
    it(`rejects an unrequested ${population} clock ledger on a period-only report`, () => {
      const r: any = structuredClone(fixtures.time_period.report);
      (population === 'selected' ? r : r.league_comparison).data_quality.clock_filter = fixture.report.data_quality.clock_filter;
      expect(() => parseReport(r, fixtures.time_period.query as Query)).toThrow('incompatible');
    });
  }
  it('rejects post-context leave-team-out accounting and double-counted losses', () => {
    const r = structuredClone(fixture.report); r.league_comparison.data_quality.excluded_selected_team_rows = 3;
    expect(() => parseReport(r, query)).toThrow('incompatible');
    const doubled = structuredClone(fixture.report); doubled.data_quality.eligible_rows_outside_cohort += 12;
    expect(() => parseReport(doubled, query)).toThrow('incompatible');
  });
});

describe('period/clock controls, accounting and stale-response safety', () => {
  it('starts unrestricted and blank without requesting a report', () => {
    render(<App />); expect(periodInput()).toHaveValue('');
    for (const input of bounds()) expect(input).toHaveValue('');
    expect(screen.getByText(/not elapsed time or MM:SS/)).toBeVisible(); expect(fetch).not.toHaveBeenCalled();
  });
  it.each(['time_period', 'time_period_no_clock', 'time_offense', 'time_defense', 'time_ot', 'time_zero', 'time_lower_only',
    'time_four_stage', 'time_four_stage_defense', 'time_field_period', 'time_score_period', 'time_all_missing_period',
    'time_all_missing_clock', 'time_missing_baseline_clock', 'time_empty_field', 'time_before_first_week'] as const)(
    'renders returned per-population stages, final metrics and warnings: %s', async name => {
      const chosen = fixtures[name], q = chosen.query as Query;
      vi.mocked(fetch).mockResolvedValue(reply(chosen.report)); setup(q); await submit();
      const region = within(await screen.findByRole('region', { name: 'Pre-play period & clock' }));
      const r = parseReport(chosen.report, q);
      expect(region.getByText(/Q4 excludes overtime/)).toBeVisible();
      expect(region.getByText(/A play missing both period and clock/)).toBeVisible();
      for (const [label, quality] of [['Selected cohort', r.data_quality], ['Other teams baseline', r.league_comparison?.data_quality]] as const) {
        if (!quality) { expect(region.queryByRole('row', { name: new RegExp(`^${label}`) })).not.toBeInTheDocument(); continue; }
        const p = quality.period_filter!, c = quality.clock_filter;
        expect(within(region.getByRole('row', { name: new RegExp(`^${label} / Period `) })).getAllByRole('cell').map(cell => cell.textContent))
          .toEqual([p.plays_before_filter, p.missing_qtr, p.outside_period, p.plays_after_filter].map(String));
        if (c) expect(within(region.getByRole('row', { name: new RegExp(`^${label} / Clock `) })).getAllByRole('cell').map(cell => cell.textContent))
          .toEqual([c.plays_before_filter, c.missing_quarter_seconds_remaining, c.outside_range, c.plays_after_filter].map(String));
        else expect(region.queryByRole('row', { name: new RegExp(`^${label} / Clock `) })).not.toBeInTheDocument();
      }
      if (r.cohort.clock) expect(region.getByText(/After period is intermediate; after clock is final/)).toBeVisible();
      else expect(region.getByText(/After period is final; no clock stage/)).toBeVisible();
      if (r.cohort.field_position) expect(screen.getByRole('columnheader', { name: 'After field filter' })).toBeVisible();
      if (r.cohort.score_differential) expect(screen.getByRole('columnheader', { name: 'After score filter' })).toBeVisible();
      if (q.period === 'OT') expect(region.getByText('OT — all periods numbered 5 or higher')).toBeVisible();
      if (r.league_comparison) expect(screen.queryByText(/no context filters requested/)).not.toBeInTheDocument();
      for (const warning of [...r.warnings, ...(r.league_comparison?.warnings ?? [])]) expect(screen.getByText(warning)).toBeVisible();
      if (!r.overall.plays) expect(screen.getByRole('heading', { name: 'No eligible plays match this query.' })).toBeVisible();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  it('clears clock to period-only, but never silently clears bounds when period is removed', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(reply(fixtures.time_offense.report))
      .mockResolvedValueOnce(reply({ ...fixtures.time_period.report, league_comparison: undefined }))
      .mockResolvedValueOnce(reply({ ...fixtures.time_unfiltered.report, league_comparison: undefined }));
    setup(fixtures.time_offense.query as Query); await submit(); await screen.findByRole('article');
    change(periodInput(), ''); expect(bounds()[1]).toHaveValue('120');
    expect(screen.queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
    await submit(); expect(screen.getByRole('alert')).toHaveTextContent('explicit period'); expect(fetch).toHaveBeenCalledTimes(1);
    change(periodInput(), 'Q4'); change(bounds()[1], ''); await submit();
    expect(await screen.findByText(/Clock unrestricted: period selection alone/)).toBeVisible();
    expect(String(vi.mocked(fetch).mock.lastCall![0])).not.toContain('clock_');
    change(periodInput(), ''); expect(fetch).toHaveBeenCalledTimes(2); await submit();
    expect(await screen.findByText('Period and clock: unrestricted; no time-context exclusions.')).toBeVisible();
    expect(String(vi.mocked(fetch).mock.lastCall![0])).not.toMatch(/period|clock_/);
  });
  it.each([0, 1, 2])('aborts and ignores an old response when time control %i changes', async index => {
    let finish!: (response: Response) => void;
    vi.mocked(fetch).mockImplementation(() => new Promise(resolve => { finish = resolve; })); setup(); await submit();
    const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
    change([periodInput(), ...bounds()][index], index === 0 ? 'OT' : '60'); expect(signal.aborted).toBe(true);
    await act(async () => { finish(reply(fixture.report)); });
    expect(screen.queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
  });
  it('preserves invalid clock text and reports missing context safely, without silent fallback', async () => {
    setup(); change(bounds()[1], '2:00'); await submit();
    expect(bounds()[1]).toHaveValue('2:00'); expect(screen.getByRole('alert')).toHaveTextContent('whole seconds');
    expect(fetch).not.toHaveBeenCalled(); change(bounds()[1], '120');
    vi.mocked(fetch).mockResolvedValue(reply({ error: { code: 'context_unavailable', message: '/private/source/path' } }, 422));
    await submit(); expect(await screen.findByRole('alert')).toHaveTextContent('period selection');
    expect(screen.getByRole('alert')).not.toHaveTextContent('/private/source/path');
    expect(screen.queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
  });
});
