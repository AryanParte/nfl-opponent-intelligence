import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { App } from './App';
import fixtures from './__fixtures__/reports.json';
import { fetchReport, parseQuery, parseReport, signedDifference, type Query } from './report';

const fixture = fixtures.offense_comparison;
const query = fixture.query as Query;
const reply = (value: unknown) => new Response(JSON.stringify(value), { headers: { 'content-type': 'application/json' } });
const toggle = () => screen.getByRole('checkbox', { name: 'Compare with other teams in the same role' });
async function load(name: keyof typeof fixtures = 'offense_comparison') {
  const chosen = fixtures[name];
  vi.mocked(fetch).mockResolvedValue(reply(chosen.report));
  render(<App />);
  fireEvent.change(screen.getByRole('textbox', { name: 'Team code' }), { target: { value: chosen.query.team } });
  fireEvent.change(screen.getByRole('spinbutton', { name: 'Before week' }), { target: { value: String(chosen.query.before_week) } });
  fireEvent.change(screen.getByRole('combobox', { name: 'Role' }), { target: { value: chosen.query.side } });
  fireEvent.change(screen.getByRole('combobox', { name: 'Season type' }), { target: { value: chosen.query.season_type } });
  await userEvent.click(toggle());
  await userEvent.click(screen.getByRole('button', { name: 'Build report' }));
  await screen.findByRole('heading', { name: 'Matched league comparison' });
  return within(screen.getByRole('region', { name: 'Matched league comparison' }));
}

describe('comparison contract', () => {
  it('uses independent percentage-point expectations, not relative percent change', () => {
    const result = parseReport(fixture.report, query).league_comparison!;
    expect(result.population.teams).toEqual(['ATL']);
    expect(result.population.shared_games_with_selected).toBe(1);
    expect(result.overall).toMatchObject({ plays: 1, games: 1, epa_observations: 1, dropback_rate: 1, success_rate: 1 });
    expect(result.overall_difference).toMatchObject({ dropback_rate_pp: -50, success_rate_pp: -40 });
    expect(result.overall_difference.epa_per_play).toBeCloseTo(-2.96);
    expect(signedDifference(-40, 'pp')).toBe('-40.0 pp');
    expect(signedDifference(25, 'pp')).toBe('+25.0 pp');
    expect(signedDifference(0, 'pp')).toBe('0.0 pp');
    expect(signedDifference(-0.00001, 'EPA/play')).toBe('0.000 EPA/play');
    expect(signedDifference(null, 'pp')).toBe('Unavailable');
  });
  it('accepts baseline-only buckets without demanding they partition displayed rows', () => {
    const chosen = fixtures.baseline_only_bucket_comparison;
    const result = parseReport(chosen.report, chosen.query as Query).league_comparison!;
    expect(result.overall.plays).toBe(1);
    expect(result.situations.reduce((n, row) => n + row.baseline.plays, 0)).toBe(0);
    expect(result.situations.some(row => row.down === 4)).toBe(false);
  });
  it('requires comparison only when requested, preserving the off contract', () => {
    expect(() => parseReport(fixtures.offense.report, query)).toThrow('incompatible report');
    expect(() => parseReport(fixture.report, { ...query, compare_league: false })).toThrow('incompatible report');
    expect(() => parseQuery({ team: 'CAR', season: '2024', before_week: '3', side: 'offense', season_type: 'REG',
      compare_league: 'true' as unknown as boolean })).toThrow();
  });
  it('sends only the explicit opt-in, never bootstrap or filesystem options', async () => {
    vi.mocked(fetch).mockResolvedValue(reply(fixture.report));
    await fetchReport(query, new AbortController().signal);
    const url = String(vi.mocked(fetch).mock.calls[0][0]);
    expect(url).toBe('/api/v1/report?team=CAR&season=2024&before_week=3&side=offense&season_type=REG&compare_league=true');
  });
  it.each([
    ['missing comparison', (r: any) => { delete r.league_comparison; }],
    ['null comparison', (r: any) => { r.league_comparison = null; }],
    ['wrong exclusion', (r: any) => { r.league_comparison.population.excluded_team = 'NO'; }],
    ['wrong role', (r: any) => { r.league_comparison.population.side = 'defense'; }],
    ['wrong role field', (r: any) => { r.league_comparison.population.team_field = 'defteam'; }],
    ['unsupported weighting', (r: any) => { r.league_comparison.population.weighting = 'team_average'; }],
    ['coverage claim', (r: any) => { r.league_comparison.population.scope = 'all_teams'; }],
    ['wrong team count', (r: any) => { r.league_comparison.population.team_count = 31; }],
    ['selected team in baseline', (r: any) => { r.league_comparison.population.teams = ['CAR']; }],
    ['duplicate team', (r: any) => { r.league_comparison.population.teams.push('ATL'); r.league_comparison.population.team_count = 2; }],
    ['impossible shared games', (r: any) => { r.league_comparison.population.shared_games_with_selected = 2; }],
    ['wrong baseline cutoff', (r: any) => { r.league_comparison.cohort.before_week_exclusive = 4; }],
    ['extra baseline filter', (r: any) => { r.league_comparison.cohort.period = {}; }],
    ['wrong ledger', (r: any) => { r.league_comparison.data_quality.plays_before_context_filters = 2; }],
    ['wrong convention', (r: any) => { r.league_comparison.difference_convention = 'baseline_minus_selected'; }],
    ['wrong situation scope', (r: any) => { r.league_comparison.situation_scope = 'all_league_buckets'; }],
    ['wrong units', (r: any) => { r.league_comparison.overall_difference.success_rate_pp = -0.4; }],
    ['wrong sign', (r: any) => { r.league_comparison.overall_difference.epa_per_play = 2.96; }],
    ['false unavailable', (r: any) => { r.league_comparison.overall_difference.epa_per_play = null; }],
    ['malformed baseline', (r: any) => { r.league_comparison.overall.missing_epa = -1; }],
    ['wrong count flag', (r: any) => { r.league_comparison.overall.small_sample = false; }],
    ['missing bucket', (r: any) => { r.league_comparison.situations.pop(); }],
    ['duplicate bucket', (r: any) => { r.league_comparison.situations[1] = r.league_comparison.situations[0]; }],
    ['extra bucket', (r: any) => { r.league_comparison.situations.push(r.league_comparison.situations[0]); }],
    ['mismatched bucket', (r: any) => { r.league_comparison.situations[0].down = 4; }],
    ['undefined replaced by zero', (r: any) => { r.league_comparison.situations[1].difference.epa_per_play = 0; }],
    ['malformed warnings', (r: any) => { r.league_comparison.warnings = [null]; }],
  ])('rejects %s before display', (_name, mutate) => {
    const report = structuredClone(fixture.report); mutate(report);
    expect(() => parseReport(report, query)).toThrow('incompatible report');
  });
});

describe('comparison interactions and interpretation', () => {
  it('starts off, does not auto-fetch, and exposes a labeled checkbox', () => {
    render(<App />);
    expect(toggle()).not.toBeChecked();
    expect(fetch).not.toHaveBeenCalled();
  });
  it('shows selected/baseline values, denominator counts, coverage, flags and every baseline warning', async () => {
    const region = await load();
    const table = within(region.getByRole('table', { name: 'Overall league comparison' }));
    expect(table.getByText('-50.0 pp')).toBeVisible();
    expect(table.getByText('-40.0 pp')).toBeVisible();
    expect(table.getByText('-2.960 EPA/play')).toBeVisible();
    expect(table.getByText('3 / 6 plays')).toBeVisible();
    expect(table.getByText('1 / 1 plays')).toBeVisible();
    expect(region.getByText(/1 observed baseline teams/)).toBeVisible();
    expect(region.getByText(/1 games shared/)).toHaveTextContent('ATL');
    expect(region.getAllByText('Baseline:', { selector: 'strong' })[0].parentElement).toHaveTextContent('1 plays / 1 games · 1 EPA observed / 0 missing · Few plays · Few EPA observations');
    for (const warning of fixture.report.league_comparison.warnings) expect(region.getByText(warning)).toBeVisible();
    expect(region.getByText(/not percent change/)).toBeVisible();
  });
  it('uses matching buckets by identity even when the API rows are reordered', async () => {
    const report = structuredClone(fixture.report);
    report.league_comparison.situations.reverse();
    await load();
    vi.mocked(fetch).mockResolvedValue(reply(report));
    await userEvent.click(screen.getByRole('button', { name: 'Build report' }));
    await screen.findByRole('table', { name: 'Overall league comparison' });
    await userEvent.click(screen.getByText('1 / long · selected 3 plays · baseline 1 plays'));
    expect(within(screen.getByRole('table', { name: '1 / long league comparison' })).getByText('-2.600 EPA/play')).toBeVisible();
    await userEvent.click(screen.getByText('2 / short · selected 1 plays · baseline 0 plays'));
    expect(within(screen.getByRole('table', { name: '2 / short league comparison' })).getAllByText('Unavailable')).toHaveLength(6);
    const bucket = screen.getByText('2 / short · selected 1 plays · baseline 0 plays').closest('details')!;
    expect(within(bucket).getByText('No matching baseline plays. No overall-baseline fallback is used.')).toBeVisible();
  });
  it('keeps defense signs and labels offensive production allowed by other defenses', async () => {
    const region = await load('defense_comparison');
    expect(region.getByText(/other defenses’ allowed offensive production/)).toHaveTextContent('excluding ATL in the same role');
    const table = within(region.getByRole('table', { name: 'Overall league comparison' }));
    expect(table.getByText('-1.450 EPA/play')).toBeVisible();
    expect(table.getByText('+25.0 pp')).toBeVisible();
    expect(table.getByText('+10.0 pp')).toBeVisible();
  });
  it.each(['empty_comparison', 'empty_baseline_comparison', 'empty_selected_comparison'] as const)('shows requested-but-empty states: %s', async name => {
    const region = await load(name);
    const table = within(region.getByRole('table', { name: 'Overall league comparison' }));
    expect(table.getAllByText('Unavailable').length).toBeGreaterThanOrEqual(6);
    expect(screen.getByText('requested; shown above')).toBeVisible();
    expect(screen.getAllByText('not requested')).toHaveLength(1); // Only uncertainty.
    if (name !== 'empty_baseline_comparison') expect(region.getByText(/No selected-team situation rows/)).toBeVisible();
  });
  it('retains the dropback comparison when baseline EPA is entirely missing', async () => {
    const region = await load('missing_epa_comparison');
    const table = within(region.getByRole('table', { name: 'Overall league comparison' }));
    expect(table.getByText('-50.0 pp')).toBeVisible();
    expect(table.getAllByText('Unavailable')).toHaveLength(4);
    expect(region.getAllByText('Baseline:', { selector: 'strong' })[0].parentElement).toHaveTextContent('0 EPA observed / 1 missing');
  });
  it('renders baseline warnings as literal text and fails closed on a missing requested block', async () => {
    await load();
    const report = structuredClone(fixture.report);
    report.league_comparison.warnings.push('<img src=x onerror=alert(1)>');
    vi.mocked(fetch).mockResolvedValueOnce(reply(report)).mockResolvedValueOnce(reply(fixtures.offense.report));
    await userEvent.click(screen.getByRole('button', { name: 'Build report' }));
    expect(await screen.findByText('<img src=x onerror=alert(1)>')).toBeVisible();
    expect(document.querySelector('img')).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Build report' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('incompatible report');
    expect(screen.queryByRole('article')).not.toBeInTheDocument();
  });
  it('removes old results when toggled off and ignores a late comparison response', async () => {
    await load();
    let finish!: (value: Response) => void;
    vi.mocked(fetch).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    await userEvent.click(screen.getByRole('button', { name: 'Build report' }));
    const signal = vi.mocked(fetch).mock.lastCall![1]!.signal!;
    await userEvent.click(toggle());
    expect(signal.aborted).toBe(true);
    await act(async () => { finish(reply(fixture.report)); });
    expect(screen.queryByRole('article')).not.toBeInTheDocument();
    vi.mocked(fetch).mockResolvedValue(reply(fixtures.offense.report));
    await userEvent.click(screen.getByRole('button', { name: 'Build report' }));
    await screen.findByRole('article');
    expect(String(vi.mocked(fetch).mock.lastCall![0])).not.toContain('compare_league');
    expect(screen.queryByRole('heading', { name: 'Matched league comparison' })).not.toBeInTheDocument();
    expect(screen.getAllByText('not requested')).toHaveLength(2);
  });
});
