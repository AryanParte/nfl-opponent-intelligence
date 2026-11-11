import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { App } from './App';
import fixtures from './__fixtures__/decisions.json';

const reply = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'content-type': 'application/json' } });
const view = () => within(screen.getByRole('tabpanel', { name: 'Decision Lab' }));
const toggle = () => fireEvent.click(view().getByRole('checkbox', { name: 'Compare with other offenses' }));
function edit(name: string, value: string) {
  fireEvent.change((view().getByRole('form') as HTMLFormElement).elements.namedItem(name) as HTMLElement, { target: { value } });
}
function setup(name: keyof typeof fixtures = 'league_multi') {
  render(<App />); fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  for (const [key, value] of Object.entries(fixtures[name].query)) {
    if (key === 'compare_league') { if (value) toggle(); }
    else edit(key, String(value));
  }
}
const submit = () => fireEvent.click(view().getByRole('button', { name: 'Compare Run and Pass' }));
const comparison = () => view().getByRole('region', { name: 'Matched candidate league comparison' });
const cells = (call: 'Run' | 'Pass', metric: string) => within(within(view().getByRole('region', {
  name: `${call} league comparison, scroll horizontally on small screens`,
})).getByRole('row', { name: new RegExp(`^${metric}`) })).getAllByRole('cell');
const accounting = (population: 'Decision' | 'Baseline') => view().getByRole('region', { name: `${population} filter accounting, scroll horizontally on small screens` });
const counts = (region: HTMLElement) => within(region).getAllByRole('row').slice(1)
  .map(row => within(row).getAllByRole('cell').map(cell => Number(cell.textContent)));

it('defaults off and only fetches after explicit submission, preserving selected evidence across off/on/off', async () => {
  const off = fixtures.league_multi_plain.decision, on = fixtures.league_multi.decision;
  expect(off.source).toEqual(on.source); expect(off.candidates).toEqual(on.candidates);
  vi.mocked(fetch).mockResolvedValueOnce(reply(off)).mockResolvedValueOnce(reply(on)).mockResolvedValueOnce(reply(off));
  setup('league_multi_plain');
  const control = view().getByRole('checkbox', { name: 'Compare with other offenses' });
  expect(control).not.toBeChecked(); expect(control).toHaveAccessibleDescription(expect.stringContaining('excludes the selected offense'));
  expect(fetch).not.toHaveBeenCalled();
  submit(); await view().findByRole('article');
  expect(view().queryByRole('region', { name: 'Matched candidate league comparison' })).not.toBeInTheDocument();
  const selected = view().getByRole('region', { name: 'Run and Pass evidence, scroll horizontally on small screens' }).textContent;
  toggle(); expect(view().queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
  submit(); await view().findByRole('region', { name: 'Matched candidate league comparison' });
  expect(view().getByRole('region', { name: 'Run and Pass evidence, scroll horizontally on small screens' })).toHaveTextContent(selected!);
  expect(view().getByText(on.source.sha256)).not.toBeVisible(); // fingerprint disclosure stays closed
  expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
  expect(view().queryByText(/League comparison and uncertainty were not requested/)).not.toBeInTheDocument();
  expect(view().getByText(/Uncertainty was not requested; differences are descriptive/)).toBeVisible();
  toggle(); expect(view().queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(2);
  submit(); await view().findByRole('article');
  expect(view().queryByRole('region', { name: 'Matched candidate league comparison' })).not.toBeInTheDocument();
  expect(view().getByRole('region', { name: 'Run and Pass evidence, scroll horizontally on small screens' })).toHaveTextContent(selected!);
  for (const [index, enabled] of [false, true, false].entries()) {
    const url = new URL(String(vi.mocked(fetch).mock.calls[index][0]), 'http://localhost');
    expect(Object.fromEntries(url.searchParams)).toEqual({ team: 'CAR', season: '2024', before_week: '3', season_type: 'REG',
      down: '1', distance_min: '10', distance_max: '10', compare_league: String(enabled) });
  }
});

it('renders independent pooled call metrics, signed differences and overlapping coverage without ranking', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.league_multi.decision)); setup(); submit();
  const section = await view().findByRole('region', { name: 'Matched candidate league comparison' });
  expect(section).toHaveTextContent('6 baseline plays / 3 games');
  expect(section).toHaveTextContent('3 observed baseline offenses: ATL, DAL, NYG');
  expect(section).toHaveTextContent('1 games shared with the selected cohort');
  expect(section).toHaveTextContent('not an average of team rates');
  expect(section).toHaveTextContent('not Pass minus Run'); expect(section).toHaveTextContent('not percent change');
  expect(section).toHaveTextContent('does not adjust for opponents');
  expect(section).toHaveTextContent('Baseline Run: 2 plays / 2 games · 2 EPA observed / 0 missing');
  expect(section).toHaveTextContent('Baseline Pass: 4 plays / 3 games · 3 EPA observed / 1 missing');
  expect(section).toHaveTextContent('Baseline Run coverage: 2 offenses (ATL, NYG); 0 games shared with selected Run plays');
  expect(section).toHaveTextContent('Baseline Pass coverage: 3 offenses (ATL, DAL, NYG); 1 games shared with selected Pass plays');
  const runFreq = cells('Run', 'Call frequency');
  expect(runFreq[0]).toHaveTextContent('33.3%'); expect(runFreq[0]).toHaveTextContent('1 / 3 plays');
  expect(runFreq[1]).toHaveTextContent('33.3%'); expect(runFreq[1]).toHaveTextContent('2 / 6 plays'); // not mean of team rates: 27.8%
  expect(runFreq[2]).toHaveTextContent('0.0 pp');
  expect(cells('Run', 'EPA').map(cell => cell.textContent)).toEqual(['0.000', '0.500', '-0.500 EPA/play']);
  const runSuccess = cells('Run', 'Offensive success');
  expect(runSuccess[0]).toHaveTextContent('0.0%'); expect(runSuccess[1]).toHaveTextContent('50.0%'); expect(runSuccess[2]).toHaveTextContent('-50.0 pp');
  const passFreq = cells('Pass', 'Call frequency');
  expect(passFreq[1]).toHaveTextContent('66.7%'); expect(passFreq[1]).toHaveTextContent('4 / 6 plays');
  expect(cells('Pass', 'EPA').map(cell => cell.textContent)).toEqual(['0.600', '1.333', '-0.733 EPA/play']);
  const passSuccess = cells('Pass', 'Offensive success');
  expect(passSuccess[1]).toHaveTextContent('66.7%'); expect(passSuccess[1]).toHaveTextContent('3 observed EPA denominator');
  expect(passSuccess[2]).toHaveTextContent('+33.3 pp');
  expect(counts(accounting('Baseline'))).toEqual([[6, 0, 0, 6], [6, 0, 0, 6]]);
  expect(section).toHaveTextContent('12 eligible plays in the same season/type before the cutoff → 6 selected-offense plays removed → 6 other-offense plays');
  for (const warning of fixtures.league_multi.decision.league_comparison.warnings) expect(within(section).getByText(warning)).toBeVisible();
  expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
});

it.each([
  ['empty', 'Unavailable', 'Unavailable', 'Unavailable'],
  ['empty_baseline', '0.0%', 'Unavailable', 'Unavailable'],
  ['empty_selected', 'Unavailable', '25.0%', 'Unavailable'],
  ['league', '33.3%', '0.0%', '+33.3 pp'],
  ['league_missing_epa', '33.3%', '33.3%', '0.0 pp'],
  ['league_selected_missing_epa', '33.3%', '33.3%', '0.0 pp'],
  ['league_unobserved_selected_run', '0.0%', '33.3%', '-33.3 pp'],
] as const)('keeps empty, absent calls, missing EPA and measured zero distinct: %s', async (name, selectedFrequency, baselineFrequency, difference) => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures[name].decision)); setup(name); submit();
  const section = await view().findByRole('region', { name: 'Matched candidate league comparison' });
  const row = cells('Run', 'Call frequency');
  expect(row[0]).toHaveTextContent(selectedFrequency); expect(row[1]).toHaveTextContent(baselineFrequency); expect(row[2]).toHaveTextContent(difference);
  expect(cells('Run', 'EPA')[2]).toHaveTextContent('Unavailable'); expect(cells('Run', 'Offensive success')[2]).toHaveTextContent('Unavailable');
  if (name === 'empty' || name === 'empty_baseline') expect(section).toHaveTextContent('No matching baseline plays. No broader baseline');
  if (name === 'empty_selected') {
    expect(section).toHaveTextContent('The selected cohort is empty'); expect(cells('Pass', 'EPA')[1]).toHaveTextContent('1.400');
    expect(cells('Pass', 'EPA')[2]).toHaveTextContent('Unavailable');
  }
  if (name === 'league') expect(section).toHaveTextContent('Call unobserved: frequency is zero; outcomes unavailable');
  if (name === 'league_missing_epa') {
    expect(section).toHaveTextContent('Baseline Run: 2 plays / 2 games · 0 EPA observed / 2 missing');
    expect(section).toHaveTextContent('EPA missing for every observed play of this call');
  }
  if (name === 'league_selected_missing_epa') {
    expect(cells('Run', 'EPA')[0]).toHaveTextContent('Unavailable'); expect(cells('Run', 'EPA')[1]).toHaveTextContent('0.500');
  }
  expect(view().queryByRole('alert')).not.toBeInTheDocument();
  expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
});

it('keeps selected and baseline six-stage counts separate under identical contexts', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.context.decision)); setup('context'); submit();
  const section = await view().findByRole('region', { name: 'Matched candidate league comparison' });
  expect(counts(accounting('Decision'))).toEqual([[15, 2, 1, 12], [12, 1, 0, 11], [11, 1, 5, 5], [5, 1, 1, 3], [3, 0, 0, 3], [3, 0, 0, 3]]);
  expect(counts(accounting('Baseline'))).toEqual([[5, 1, 0, 4], [4, 0, 0, 4], [4, 1, 1, 2], [2, 1, 0, 1], [1, 0, 0, 1], [1, 0, 0, 1]]);
  expect(within(accounting('Baseline')).getAllByRole('rowheader').map(row => row.textContent)).toEqual(['Field position', 'Pre-play score', 'Period', 'Clock', 'Down', 'Distance']);
  expect(section).toHaveTextContent('20 eligible plays in the same season/type before the cutoff → 15 selected-offense plays removed → 5 other-offense plays');
  expect(cells('Pass', 'EPA').map(cell => cell.textContent)).toEqual(['0.800', '3.000', '-2.200 EPA/play']);
  expect(cells('Run', 'Call frequency')[2]).toHaveTextContent('+66.7 pp');
  expect(section).toHaveTextContent('Final distance-stage survivors supply baseline metrics');
});

it('uses the matching OT baseline without sign reversal or a Q4 fallback', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.overtime.decision)); setup('overtime'); submit();
  await view().findByRole('region', { name: 'Matched candidate league comparison' });
  expect(cells('Pass', 'EPA').map(cell => cell.textContent)).toEqual(['0.400', '-1.000', '+1.400 EPA/play']);
  expect(cells('Pass', 'Offensive success')[2]).toHaveTextContent('+100.0 pp');
  expect(counts(accounting('Baseline'))).toEqual([[5, 2, 2, 1], [1, 0, 0, 1], [1, 0, 0, 1], [1, 0, 0, 1]]);
});

it('removes stale comparison evidence on edits and rejects a response after switching comparison off', async () => {
  let finish!: (response: Response) => void;
  vi.mocked(fetch).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  setup('context'); submit(); const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
  toggle(); expect(signal.aborted).toBe(true); expect(view().queryByRole('article')).not.toBeInTheDocument();
  await act(async () => finish(reply(fixtures.context.decision)));
  expect(view().queryByRole('article')).not.toBeInTheDocument(); expect(view().getByRole('status')).toBeEmptyDOMElement();
});

it('preserves independent comparison toggles and completed evidence across modes with unique IDs', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.context.decision)); setup('context'); submit();
  await view().findByRole('region', { name: 'Matched candidate league comparison' });
  fireEvent.click(screen.getByRole('tab', { name: 'Scout' }));
  expect(screen.getByRole('checkbox', { name: 'Compare with other teams in the same role' })).not.toBeChecked();
  fireEvent.click(screen.getByRole('checkbox', { name: 'Compare with other teams in the same role' }));
  fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  expect(view().getByRole('checkbox', { name: 'Compare with other offenses' })).toBeChecked();
  expect(comparison()).toBeVisible(); expect(fetch).toHaveBeenCalledTimes(1);
  toggle(); fireEvent.click(screen.getByRole('tab', { name: 'Scout' }));
  expect(screen.getByRole('checkbox', { name: 'Compare with other teams in the same role' })).toBeChecked();
  const ids = Array.from(document.querySelectorAll('[id]'), node => node.id); expect(new Set(ids).size).toBe(ids.length);
});

it('fails safely on an API error instead of substituting unfiltered or selected-only evidence', async () => {
  vi.mocked(fetch).mockResolvedValue(reply({ error: { code: 'report_busy', message: '/private/operator/path' } }, 503));
  setup(); submit(); await view().findByRole('alert');
  expect(view().queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('tabpanel', { name: 'Decision Lab' })).not.toHaveTextContent('/private/operator');
  expect(view().getByRole('checkbox', { name: 'Compare with other offenses' })).toBeChecked();
});

it.each(['cohort', 'missing_block', 'direction', 'unit', 'coverage', 'stage_chain', 'final_count'])('rejects invalid requested baseline before rendering: %s', async mutation => {
  const data = structuredClone(fixtures.context.decision);
  const b = data.league_comparison;
  if (mutation === 'cohort') b.cohort.clock.maximum_inclusive = 121;
  if (mutation === 'missing_block') Reflect.deleteProperty(data, 'league_comparison');
  if (mutation === 'direction') b.candidates[1].difference.epa_per_play = 2.2;
  if (mutation === 'unit') b.difference_units.frequency_pp = 'percent_change';
  if (mutation === 'coverage') b.population.teams = ['CAR'];
  if (mutation === 'stage_chain') { b.data_quality.clock_filter.plays_before_filter += 1; b.data_quality.clock_filter.outside_range += 1; }
  if (mutation === 'final_count') b.data_quality.distance_filter.plays_after_filter += 1;
  vi.mocked(fetch).mockResolvedValue(reply(data)); setup('context'); submit(); await view().findByRole('alert');
  expect(view().queryByRole('article')).not.toBeInTheDocument();
});

it('rejects an unsolicited comparison block when comparison is off', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.league_multi.decision)); setup('league_multi_plain'); submit();
  await view().findByRole('alert'); expect(view().queryByRole('article')).not.toBeInTheDocument();
});
