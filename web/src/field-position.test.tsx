import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { App } from './App';
import fixtures from './__fixtures__/reports.json';
import { fetchReport, parseQuery, parseReport, type Draft, type Query } from './report';

const fixture = fixtures.field_offense_comparison;
const query = fixture.query as Query;
const draft: Draft = { team: 'CAR', season: '2024', before_week: '3', side: 'offense', season_type: 'REG',
  compare_league: true, yardline_min: '', yardline_max: '', score_min: '', score_max: '' };
const reply = (value: unknown, status = 200) => new Response(JSON.stringify(value), {
  status, headers: { 'content-type': 'application/json' },
});
const bounds = () => [screen.getByRole('textbox', { name: 'Minimum yards to goal' }),
  screen.getByRole('textbox', { name: 'Maximum yards to goal' })];
const change = (input: HTMLElement, value: string) => fireEvent.change(input, { target: { value } });
const submit = () => userEvent.click(screen.getByRole('button', { name: 'Build report' }));

function setup(q: Query = query) {
  render(<App />);
  change(screen.getByRole('textbox', { name: 'Team code' }), q.team);
  change(screen.getByRole('spinbutton', { name: 'Before week' }), String(q.before_week));
  change(screen.getByRole('combobox', { name: 'Role' }), q.side);
  change(bounds()[0], q.yardline_min === undefined ? '' : String(q.yardline_min));
  change(bounds()[1], q.yardline_max === undefined ? '' : String(q.yardline_max));
  if (q.compare_league) fireEvent.click(screen.getByRole('checkbox'));
}

describe('optional field-position request', () => {
  it.each([
    ['', '', {}], [' ', ' ', {}], ['', '20', { yardline_max: 20 }],
    ['80', '', { yardline_min: 80 }], ['0', '100', { yardline_min: 0, yardline_max: 100 }],
    ['', '0', { yardline_max: 0 }], ['20.5', '20.5', { yardline_min: 20.5, yardline_max: 20.5 }],
    [' .5 ', '20.', { yardline_min: .5, yardline_max: 20 }],
  ])('parses %j / %j without substituting zero for an omitted end', (lower, upper, expected) => {
    const { yardline_min, yardline_max, ...base } = draft;
    expect(parseQuery({ ...base, yardline_min: lower, yardline_max: upper })).toEqual({
      ...fixtures.offense_comparison.query, ...expected,
    });
  });
  it.each(['-1', '101', 'Infinity', 'NaN', '1e1', '0x14', '20 yards', '20,5', '.', '1 0'])('rejects non-decimal/out-of-range bound %j', value => {
    for (const field of ['yardline_min', 'yardline_max']) expect(() => parseQuery({ ...draft, [field]: value })).toThrow('bounds must be decimals');
  });
  it('rejects reversed endpoints before sending', () => {
    expect(() => parseQuery({ ...draft, yardline_min: '21', yardline_max: '20' })).toThrow('must not exceed');
  });
  it('serializes only entered bounds, including zero, without paths, downloads or bootstrap', async () => {
    for (const name of ['field_offense', 'field_lower_only', 'field_zero', 'field_fractional', 'field_full_range'] as const) {
      const chosen = fixtures[name];
      vi.mocked(fetch).mockResolvedValueOnce(reply(chosen.report));
      await fetchReport(chosen.query as Query, new AbortController().signal);
      const url = new URL(String(vi.mocked(fetch).mock.lastCall![0]), 'http://localhost');
      const expected = Object.fromEntries(Object.entries(chosen.query).filter(([, v]) => v !== false).map(([k, v]) => [k, String(v)]));
      expect(url.pathname).toBe('/api/v1/report');
      expect(Object.fromEntries(url.searchParams)).toEqual(expected);
    }
  });
});

describe('filtered response identity and accounting', () => {
  it('matches independent synthetic inclusive endpoints, role counts and denominators', () => {
    const r = parseReport(fixture.report, query);
    // CAR: 0 / 20 / 100 / missing / 20.5 / 80. Baseline ATL: 20.
    expect(r.data_quality.field_position_filter).toEqual({ plays_before_filter: 6, missing_yardline_100: 1, outside_range: 3, plays_after_filter: 2 });
    expect(r.overall).toMatchObject({ plays: 2, games: 1, dropbacks: 1, epa_observations: 2, epa_per_play: .5, success_rate: 1 });
    expect(r.league_comparison!.data_quality).toMatchObject({ excluded_selected_team_rows: 6, plays_before_context_filters: 1,
      field_position_filter: { plays_before_filter: 1, missing_yardline_100: 0, outside_range: 0, plays_after_filter: 1 } });
    const d = parseReport(fixtures.field_defense_comparison.report, fixtures.field_defense_comparison.query as Query);
    expect(d.data_quality.field_position_filter).toEqual({ plays_before_filter: 5, missing_yardline_100: 1, outside_range: 2, plays_after_filter: 2 });
    expect(d.overall.epa_per_play).toBe(.5); // Not sign-flipped or complemented coordinates.
    expect(d.league_comparison!.data_quality.field_position_filter).toEqual({ plays_before_filter: 2, missing_yardline_100: 0, outside_range: 1, plays_after_filter: 1 });
  });
  it('distinguishes no filter, full range, zero, fractional bounds, missing EPA and missing position', () => {
    expect(fixtures.offense.report.overall.plays).toBe(6);
    expect(fixtures.field_unfiltered.report.overall).toEqual(fixtures.offense.report.overall);
    expect(fixtures.field_unfiltered.report.data_quality).not.toHaveProperty('field_position_filter');
    expect(fixtures.field_unfiltered.report.source.sha256).toBe(fixtures.field_full_range.report.source.sha256);
    expect(fixtures.field_full_range.report.overall).toMatchObject({ plays: 5, epa_observations: 4, missing_epa: 1 });
    expect(fixtures.field_full_range.report.data_quality.field_position_filter).toMatchObject({ missing_yardline_100: 1, outside_range: 0 });
    expect(fixtures.field_zero.report.overall).toMatchObject({ plays: 1, epa_per_play: .8 });
    expect(fixtures.field_fractional.report.overall).toMatchObject({ plays: 1, dropback_rate: 0, epa_per_play: null, missing_epa: 1 });
    expect(fixtures.field_lower_only.report.cohort.field_position.maximum_inclusive).toBe(100);
    expect(fixtures.field_lower_only.report.overall).toMatchObject({ plays: 2, epa_per_play: -.6 });
  });
  it('requires the exact requested filter, while leaving unfiltered reports compatible', () => {
    expect(() => parseReport(fixtures.offense_comparison.report, query)).toThrow('incompatible');
    expect(() => parseReport(fixture.report, fixtures.offense_comparison.query as Query)).toThrow('incompatible');
    expect(() => parseReport(fixture.report, { ...query, yardline_min: 1 })).toThrow('incompatible');
    // Explicit 0 and the omitted lower end identify the same effective cohort.
    expect(parseReport(fixture.report, { ...query, yardline_min: 0 })).toEqual(fixture.report);
  });
  for (const population of ['selected', 'baseline'] as const) {
    it.each([
      ['missing field identity', (r: any) => { delete r.cohort.field_position; }],
      ['wrong source field', (r: any) => { r.cohort.field_position.field = 'yards_gained'; }],
      ['wrong minimum', (r: any) => { r.cohort.field_position.minimum_inclusive = 1; }],
      ['wrong maximum', (r: any) => { r.cohort.field_position.maximum_inclusive = 21; }],
      ['reversed perspective', (r: any) => { r.cohort.field_position.perspective = 'defense'; }],
      ['changed missing policy', (r: any) => { r.cohort.field_position.missing_policy = 'include'; }],
      ['extra filter', (r: any) => { r.cohort.score_differential = {}; }],
      ['missing accounting', (r: any) => { delete r.data_quality.field_position_filter; }],
      ['fractional count', (r: any) => { r.data_quality.field_position_filter.missing_yardline_100 = .5; }],
      ['negative count', (r: any) => { r.data_quality.field_position_filter.outside_range = -1; }],
      ['coerced count', (r: any) => { r.data_quality.field_position_filter.plays_before_filter = '6'; }],
      ['unreconciled count', (r: any) => { r.data_quality.field_position_filter.plays_before_filter += 1; }],
      ['retained not final', (r: any) => { r.data_quality.field_position_filter.plays_after_filter += 1; r.data_quality.field_position_filter.plays_before_filter += 1; }],
      ['extra hidden filter accounting', (r: any) => { r.data_quality.clock_filter = {}; }],
    ])(`rejects ${population} %s`, (_name, mutate) => {
      const report = structuredClone(fixture.report);
      mutate(population === 'selected' ? report : report.league_comparison);
      expect(() => parseReport(report, query)).toThrow('incompatible');
    });
  }
  it.each([
    ['after-filter team exclusion', (r: any) => { r.league_comparison.data_quality.excluded_selected_team_rows = 2; }],
    ['unrequested order', (r: any) => { r.league_comparison.data_quality.filter_order = ['score_differential']; }],
    ['omitted order', (r: any) => { r.league_comparison.data_quality.filter_order = []; }],
    ['wrong baseline before', (r: any) => { r.league_comparison.data_quality.plays_before_context_filters += 1; }],
    ['wrong baseline after', (r: any) => { r.league_comparison.data_quality.plays_after_context_filters += 1; }],
    ['wrong temporal total', (r: any) => { r.league_comparison.data_quality.eligible_rows_same_season_type_before_week += 1; }],
    ['double-counted global exclusions', (r: any) => { r.data_quality.eligible_rows_outside_cohort += 4; }],
    ['invalid raw reconciliation', (r: any) => { r.data_quality.input_rows += 1; }],
  ])('rejects %s', (_name, mutate) => {
    const report = structuredClone(fixture.report); mutate(report);
    expect(() => parseReport(report, query)).toThrow('incompatible');
  });
});

describe('field-position controls and display', () => {
  it('starts blank, labels coordinates/defaults, and does not auto-request', () => {
    render(<App />);
    for (const input of bounds()) { expect(input).toHaveValue(''); expect(input).toHaveAttribute('inputmode', 'decimal'); }
    expect(screen.getByText(/Both blank = no field filter/)).toBeVisible();
    expect(screen.getByText(/Defense mode does not reverse the coordinates/)).toBeVisible();
    expect(fetch).not.toHaveBeenCalled();
  });
  it.each(['field_offense', 'field_offense_comparison', 'field_defense_comparison', 'field_missing_baseline', 'field_all_missing', 'field_empty', 'field_fractional', 'field_before_first_week'] as const)(
    'shows returned bounds, separate ledgers, missing/empty states and warnings: %s', async name => {
      const chosen = fixtures[name], q = chosen.query as Query;
      vi.mocked(fetch).mockResolvedValue(reply(chosen.report)); setup(q); await submit();
      const region = within(await screen.findByRole('region', { name: 'Pre-play field position' }));
      const field = chosen.report.cohort.field_position;
      expect(region.getByText(`${field.minimum_inclusive}–${field.maximum_inclusive} yards to the offense’s opponent’s goal line`)).toBeVisible();
      const counts = chosen.report.data_quality.field_position_filter;
      const row = region.getByRole('row', { name: /^Selected cohort/ });
      expect(within(row).getAllByRole('cell').map(cell => cell.textContent)).toEqual([
        counts.plays_before_filter, counts.missing_yardline_100, counts.outside_range, counts.plays_after_filter,
      ].map(String));
      if ('league_comparison' in chosen.report) {
        const base = chosen.report.league_comparison;
        const b = base.data_quality.field_position_filter;
        expect(within(region.getByRole('row', { name: /^Other teams baseline/ })).getAllByRole('cell').map(cell => cell.textContent))
          .toEqual([b.plays_before_filter, b.missing_yardline_100, b.outside_range, b.plays_after_filter].map(String));
        expect(screen.getByText(/identical inclusive field-position bounds/)).toBeVisible();
        for (const warning of base.warnings) expect(screen.getByText(warning)).toBeVisible();
      } else expect(region.queryByRole('row', { name: /^Other teams baseline/ })).not.toBeInTheDocument();
      for (const warning of chosen.report.warnings) expect(screen.getByText(warning)).toBeVisible();
      if (!chosen.report.overall.plays) expect(screen.getByRole('heading', { name: 'No eligible plays match this query.' })).toBeVisible();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  it('keeps malformed text visible and rejects it instead of treating it as a blank/unfiltered query', async () => {
    setup(); change(bounds()[1], '1e'); await submit();
    expect(bounds()[1]).toHaveValue('1e');
    expect(screen.getByRole('alert')).toHaveTextContent('bounds must be decimals');
    expect(fetch).not.toHaveBeenCalled();
  });
  it('clearing both bounds removes the old report and omits the filter on the next explicit request', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(reply(fixture.report)).mockResolvedValueOnce(reply(fixtures.offense_comparison.report));
    setup(); await submit(); await screen.findByRole('article');
    change(bounds()[1], ''); expect(screen.queryByRole('article')).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1); await submit();
    expect(await screen.findByText('Field position: unrestricted; missing positions are not excluded by field position.')).toBeVisible();
    expect(String(vi.mocked(fetch).mock.lastCall![0])).not.toContain('yardline_');
    expect(screen.queryByRole('region', { name: 'Pre-play field position' })).not.toBeInTheDocument();
  });
  it.each([0, 1])('editing bound %i aborts and suppresses a stale filtered response', async index => {
    let finish!: (response: Response) => void;
    vi.mocked(fetch).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    setup(); await submit();
    const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
    change(bounds()[index], '10'); expect(signal.aborted).toBe(true);
    await act(async () => { finish(reply(fixture.report)); });
    expect(screen.queryByRole('article')).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it('shows a missing source column as an error, never as an empty cohort or an automatic unfiltered fallback', async () => {
    vi.mocked(fetch).mockResolvedValue(reply({ error: { code: 'context_unavailable', message: '/private/source/path' } }, 422));
    setup(); await submit();
    const error = await screen.findByRole('alert');
    expect(error).toHaveTextContent('snapshot lacks the requested context column');
    expect(error).not.toHaveTextContent('/private/source/path');
    expect(screen.queryByRole('article')).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
