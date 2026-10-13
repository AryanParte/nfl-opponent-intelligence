import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { App } from './App';
import fixtures from './__fixtures__/reports.json';
import { fetchReport, parseQuery, parseReport, type Draft, type Query } from './report';

const fixture = fixtures.score_field;
const query = fixture.query as Query;
const draft: Draft = { team: 'CAR', season: '2024', before_week: '3', side: 'offense', season_type: 'REG',
  compare_league: true, yardline_min: '', yardline_max: '', score_min: '', score_max: '', period: '', clock_min: '', clock_max: '' };
const reply = (value: unknown, status = 200) => new Response(JSON.stringify(value), {
  status, headers: { 'content-type': 'application/json' },
});
const bounds = () => [screen.getByRole('textbox', { name: 'Minimum score difference' }),
  screen.getByRole('textbox', { name: 'Maximum score difference' })];
const change = (input: HTMLElement, value: string) => fireEvent.change(input, { target: { value } });
const submit = () => userEvent.click(screen.getByRole('button', { name: 'Build report' }));

function setup(q: Query = query) {
  render(<App />);
  change(screen.getByRole('textbox', { name: 'Team code' }), q.team);
  change(screen.getByRole('spinbutton', { name: 'Before week' }), String(q.before_week));
  change(screen.getByRole('combobox', { name: 'Role' }), q.side);
  for (const [label, key] of [['Minimum yards to goal', 'yardline_min'], ['Maximum yards to goal', 'yardline_max'],
    ['Minimum score difference', 'score_min'], ['Maximum score difference', 'score_max']] as const) {
    change(screen.getByRole('textbox', { name: label }), q[key] === undefined ? '' : String(q[key]));
  }
  if (q.compare_league) fireEvent.click(screen.getByRole('checkbox'));
}

describe('optional signed whole-point request', () => {
  it.each([
    ['', '', {}], [' ', ' ', {}], ['', '0', { score_max: 0 }], ['0', '', { score_min: 0 }],
    ['-7', '0', { score_min: -7, score_max: 0 }], ['0', '0', { score_min: 0, score_max: 0 }],
    [' +7 ', '', { score_min: 7 }], ['', '-7', { score_max: -7 }],
    ['-1000', '+1000', { score_min: -1000, score_max: 1000 }],
  ])('parses %j / %j without substituting an end', (lower, upper, expected) => {
    expect(parseQuery({ ...draft, score_min: lower, score_max: upper })).toEqual({ ...fixtures.offense_comparison.query, ...expected });
  });
  it.each(['-', '+', '1.0', '.5', '-.5', '1e1', '0x10', 'NaN', 'Infinity', '1,000', '1 0', '7 points',
    '-1001', '1001', '9007199254740992'])('rejects invalid score bound %j', value => {
    for (const key of ['score_min', 'score_max']) expect(() => parseQuery({ ...draft, [key]: value })).toThrow('signed whole points');
  });
  it('rejects reversed bounds, including negative values', () => {
    expect(() => parseQuery({ ...draft, score_min: '-3', score_max: '-7' })).toThrow('must not exceed');
  });
  it('serializes only entered score/field bounds, never null, paths, downloads or bootstrap options', async () => {
    for (const name of ['score_offense', 'score_lower_only', 'score_upper_only', 'score_tied', 'score_input_limits', 'score_field'] as const) {
      const chosen = fixtures[name]; vi.mocked(fetch).mockResolvedValueOnce(reply(chosen.report));
      await fetchReport(chosen.query as Query, new AbortController().signal);
      const url = new URL(String(vi.mocked(fetch).mock.lastCall![0]), 'http://localhost');
      expect(url.pathname).toBe('/api/v1/report');
      expect(Object.fromEntries(url.searchParams)).toEqual(Object.fromEntries(Object.entries(chosen.query)
        .filter(([, v]) => v !== false).map(([k, v]) => [k, String(v)])));
    }
  });
});

describe('score identity, stages and independent synthetic expectations', () => {
  it('distinguishes a tied score, open ends, empty and missing from a numeric zero', () => {
    const unfiltered = fixtures.score_unfiltered.report;
    expect(unfiltered.overall.plays).toBe(6);
    expect(unfiltered.data_quality).not.toHaveProperty('score_differential_filter');
    expect(fixtures.score_input_limits.report.overall).toMatchObject({ plays: 4, epa_observations: 4 });
    expect(fixtures.score_input_limits.report.overall.epa_per_play).toBeCloseTo(-.05, 12);
    expect(fixtures.score_tied.report.overall).toMatchObject({ plays: 1, dropback_rate: 0, epa_per_play: .2 });
    expect(fixtures.score_upper_only.report.cohort.score_differential.minimum_inclusive).toBeNull();
    expect(fixtures.score_upper_only.report.overall).toMatchObject({ plays: 1, epa_per_play: .8 });
    expect(fixtures.score_lower_only.report.cohort.score_differential.maximum_inclusive).toBeNull();
    expect(fixtures.score_lower_only.report.overall).toMatchObject({ plays: 2, epa_per_play: -.6 });
    for (const name of ['score_empty', 'score_all_missing', 'score_before_first_week'] as const) {
      expect(fixtures[name].report.overall).toMatchObject({ plays: 0, games: 0, dropback_rate: null, epa_per_play: null });
    }
    expect(fixtures.score_missing_baseline.report.league_comparison.overall.plays).toBe(0);
    expect(fixtures.score_missing_epa.report.overall).toMatchObject({ plays: 2, epa_observations: 0, missing_epa: 2, epa_per_play: null });
  });
  it('counts overlapping missing fields once and keeps pre-context leave-team-out counts', () => {
    const r = parseReport(fixture.report, query), base = r.league_comparison!;
    // CAR: field 6 -> 3 (one missing, two outside), then score 3 -> 2 (one missing).
    // ATL: field 5 -> 3 (one missing, one outside), then score 3 -> 2 (one missing).
    expect(r.data_quality.field_position_filter).toEqual({ plays_before_filter: 6, missing_yardline_100: 1, outside_range: 2, plays_after_filter: 3 });
    expect(base.data_quality.field_position_filter).toEqual({ plays_before_filter: 5, missing_yardline_100: 1, outside_range: 1, plays_after_filter: 3 });
    for (const quality of [r.data_quality, base.data_quality]) {
      expect(quality.filter_order).toEqual(['field_position', 'score_differential']);
      expect(quality.score_differential_filter).toEqual({ plays_before_filter: 3, missing_score_differential: 1, outside_range: 0, plays_after_filter: 2 });
    }
    expect(r.overall).toMatchObject({ plays: 2, games: 1, epa_per_play: .5, success_rate: 1 });
    expect(base.overall).toMatchObject({ plays: 2, games: 1, epa_per_play: 3 });
    expect(base.data_quality).toMatchObject({ excluded_selected_team_rows: 6, eligible_rows_same_season_type_before_week: 11 });
    expect(fixtures.score_comparison.report.data_quality.score_differential_filter).toEqual({
      plays_before_filter: 6, missing_score_differential: 2, outside_range: 2, plays_after_filter: 2,
    }); // Without field position, both missing scores are visible in this stage.
    expect(fixtures.score_field_defense.report.overall).toEqual(r.overall);
    expect(fixtures.score_defense.report.overall).toEqual(r.overall); // Same CAR production allowed by ATL, no sign flip.
  });
  it('requires exact requested score and field identity, with null as unbounded (not zero or the input limit)', () => {
    for (const changed of [{ score_min: undefined }, { score_max: undefined }, { score_min: 0 }, { yardline_max: undefined }]) {
      expect(() => parseReport(fixture.report, { ...query, ...changed })).toThrow('incompatible');
    }
    expect(() => parseReport(fixtures.score_unfiltered.report, fixtures.score_comparison.query as Query)).toThrow('incompatible');
    expect(() => parseReport(fixtures.score_comparison.report, fixtures.score_unfiltered.query as Query)).toThrow('incompatible');
    for (const replacement of [0, -1000]) {
      const r = structuredClone(fixtures.score_upper_only.report);
      (r.cohort.score_differential.minimum_inclusive as number | null) = replacement;
      expect(() => parseReport(r, fixtures.score_upper_only.query as Query)).toThrow('incompatible');
    }
  });
  for (const population of ['selected', 'baseline'] as const) {
    it.each([
      ['missing score identity', (r: any) => { delete r.cohort.score_differential; }],
      ['post-play score', (r: any) => { r.cohort.score_differential.field = 'score_differential_post'; }],
      ['reversed perspective', (r: any) => { r.cohort.score_differential.perspective = 'defense'; }],
      ['imputed missing scores', (r: any) => { r.cohort.score_differential.missing_policy = 'zero'; }],
      ['wrong zero boundary', (r: any) => { r.cohort.score_differential.maximum_inclusive = null; }],
      ['hidden period filter', (r: any) => { r.cohort.period = {}; }],
      ['missing score ledger', (r: any) => { delete r.data_quality.score_differential_filter; }],
      ['missing order', (r: any) => { delete r.data_quality.filter_order; }],
      ['reversed order', (r: any) => { r.data_quality.filter_order.reverse(); }],
      ['omitted stage', (r: any) => { r.data_quality.filter_order.pop(); }],
      ['extra stage', (r: any) => { r.data_quality.filter_order.push('clock'); }],
      ['fractional missing count', (r: any) => { r.data_quality.score_differential_filter.missing_score_differential = .5; }],
      ['negative count', (r: any) => { r.data_quality.score_differential_filter.outside_range = -1; }],
      ['coerced count', (r: any) => { r.data_quality.score_differential_filter.plays_before_filter = '3'; }],
      ['stage does not reconcile', (r: any) => { r.data_quality.score_differential_filter.missing_score_differential += 1; }],
      ['disconnected stages', (r: any) => { r.data_quality.score_differential_filter.plays_before_filter += 1; r.data_quality.score_differential_filter.missing_score_differential += 1; }],
      ['final count mismatch', (r: any) => { r.data_quality.score_differential_filter.plays_after_filter += 1; r.data_quality.score_differential_filter.missing_score_differential -= 1; }],
      ['unexpected ledger', (r: any) => { r.data_quality.clock_filter = {}; }],
    ])(`rejects ${population} %s`, (_name, mutate) => {
      const r = structuredClone(fixture.report); mutate(population === 'selected' ? r : r.league_comparison);
      expect(() => parseReport(r, query)).toThrow('incompatible');
    });
  }
  it('rejects a fabricated field stage on a score-only report and loss double-counting', () => {
    for (const population of ['selected', 'baseline']) {
      const r: any = structuredClone(fixtures.score_comparison.report);
      const target = population === 'selected' ? r : r.league_comparison;
      target.data_quality.field_position_filter = fixture.report.data_quality.field_position_filter;
      expect(() => parseReport(r, fixtures.score_comparison.query as Query)).toThrow('incompatible');
    }
    const r = structuredClone(fixture.report); r.data_quality.eligible_rows_outside_cohort += 4;
    expect(() => parseReport(r, query)).toThrow('incompatible');
  });
});

describe('score controls and display', () => {
  it('starts blank with signed, pre-play, offense-relative and unbounded explanations', () => {
    render(<App />);
    for (const input of bounds()) expect(input).toHaveValue('');
    expect(screen.getByText(/A blank end is unbounded/)).toBeVisible();
    expect(screen.getByText(/0 = tied, not missing/)).toBeVisible();
    expect(fetch).not.toHaveBeenCalled();
  });
  it.each(['score_offense', 'score_comparison', 'score_defense', 'score_lower_only', 'score_upper_only', 'score_tied',
    'score_field', 'score_field_defense', 'score_empty', 'score_all_missing', 'score_missing_baseline', 'score_missing_epa', 'score_before_first_week'] as const)(
    'renders the returned score ledger, final metrics and warnings: %s', async name => {
      const chosen = fixtures[name], q = chosen.query as Query;
      vi.mocked(fetch).mockResolvedValue(reply(chosen.report)); setup(q); await submit();
      const region = within(await screen.findByRole('region', { name: 'Pre-play score difference' }));
      expect(region.getByText(/For a selected defense, -7 means/)).toBeVisible();
      expect(region.getByRole('columnheader', { name: 'Final retained plays' })).toBeVisible();
      const r = parseReport(chosen.report, q);
      for (const [label, quality] of [['Selected cohort', r.data_quality], ['Other teams baseline', r.league_comparison?.data_quality]] as const) {
        if (!quality) { expect(region.queryByRole('row', { name: new RegExp(`^${label}`) })).not.toBeInTheDocument(); continue; }
        const counts = quality.score_differential_filter!;
        expect(within(region.getByRole('row', { name: new RegExp(`^${label}`) })).getAllByRole('cell').map(cell => cell.textContent))
          .toEqual([counts.plays_before_filter, counts.missing_score_differential, counts.outside_range, counts.plays_after_filter].map(String));
      }
      if (r.cohort.field_position) {
        expect(screen.getByRole('columnheader', { name: 'After field filter' })).toBeVisible();
        expect(region.getByText(/Before score = after field position/)).toBeVisible();
      } else expect(screen.queryByRole('region', { name: 'Pre-play field position' })).not.toBeInTheDocument();
      if (r.league_comparison) {
        expect(screen.getByText(/Identical inclusive pre-play score bounds/)).toBeVisible();
        expect(screen.queryByText(/no context filters requested/)).not.toBeInTheDocument();
      }
      for (const warning of [...r.warnings, ...(r.league_comparison?.warnings ?? [])]) expect(screen.getByText(warning)).toBeVisible();
      if (!r.overall.plays) expect(screen.getByRole('heading', { name: 'No eligible plays match this query.' })).toBeVisible();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  it.each([['score_lower_only', 'At least +1 points'], ['score_upper_only', 'At most -7 points'],
    ['score_tied', '0 to 0 points'], ['score_comparison', '-7 to 0 points']] as const)('labels actual bounds: %s', async (name, label) => {
    const chosen = fixtures[name]; vi.mocked(fetch).mockResolvedValue(reply(chosen.report)); setup(chosen.query as Query); await submit();
    expect(await screen.findByText(label)).toBeVisible();
  });
  it.each(['-', '+', '1.5'])('keeps invalid text %j visible instead of silently omitting the filter', async value => {
    setup(); change(bounds()[0], value); await submit();
    expect(bounds()[0]).toHaveValue(value); expect(screen.getByRole('alert')).toHaveTextContent('signed whole points');
    expect(fetch).not.toHaveBeenCalled();
  });
  it('clearing both scores removes old results and sends an unfiltered query only on explicit submit', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(reply(fixtures.score_comparison.report)).mockResolvedValueOnce(reply(fixtures.score_unfiltered.report));
    setup(fixtures.score_comparison.query as Query); await submit(); await screen.findByRole('article');
    for (const input of bounds()) change(input, '');
    expect(screen.queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
    await submit(); expect(await screen.findByText('Pre-play score: unrestricted; no score-based exclusions.')).toBeVisible();
    expect(String(vi.mocked(fetch).mock.lastCall![0])).not.toContain('score_');
  });
  it.each([0, 1])('aborts and ignores an old response after score endpoint %i changes', async index => {
    let finish!: (response: Response) => void;
    vi.mocked(fetch).mockImplementation(() => new Promise(resolve => { finish = resolve; })); setup(); await submit();
    const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!; change(bounds()[index], '7'); expect(signal.aborted).toBe(true);
    await act(async () => { finish(reply(fixture.report)); });
    expect(screen.queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
  });
  it('shows context-unavailable errors without path leakage, empty-cohort claims or automatic fallback', async () => {
    vi.mocked(fetch).mockResolvedValue(reply({ error: { code: 'context_unavailable', message: '/private/source/path' } }, 422));
    setup(fixtures.score_comparison.query as Query); await submit();
    expect(await screen.findByRole('alert')).toHaveTextContent('Clear the requested context bounds');
    expect(screen.getByRole('alert')).not.toHaveTextContent('/private/source/path');
    expect(screen.queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
  });
});
