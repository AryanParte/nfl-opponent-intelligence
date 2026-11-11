import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { App } from './App';
import fixtures from './__fixtures__/decisions.json';

const reply = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } });
const view = () => within(screen.getByRole('tabpanel', { name: 'Decision Lab' }));
const input = (name: string) => (view().getByRole('form') as HTMLFormElement).elements.namedItem(name) as HTMLElement;
const edit = (name: string, value: string) => fireEvent.change(input(name), { target: { value } });
const submit = () => fireEvent.click(view().getByRole('button', { name: 'Compare Run and Pass' }));
const title = 'Candidate game support and exploratory uncertainty';
const cells = (call: string, metric: string) => within(within(view().getByRole('region', {
  name: `${call} uncertainty, scroll horizontally on small screens`,
})).getByRole('row', { name: new RegExp(`^${metric}`) })).getAllByRole('cell');
function setup(name: keyof typeof fixtures) {
  render(<App />); fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  for (const [key, value] of Object.entries(fixtures[name].query)) {
    if (key === 'compare_league') { if (value) fireEvent.click(input(key)); }
    else edit(key, String(value));
  }
}

it.each([
  ['bootstrap_selected', 'bootstrap_selected_plain'],
  ['bootstrap_comparison', 'bootstrap_comparison_plain'],
  ['bootstrap_context', 'context'],
] as const)('opts in only on submit and preserves all point evidence across off/on/off: %s', async (onName, offName) => {
  const off = fixtures[offName], on = fixtures[onName];
  const { uncertainty: _uncertainty, ...points } = on.decision; expect(points).toEqual(off.decision);
  vi.mocked(fetch).mockResolvedValueOnce(reply(off.decision)).mockResolvedValueOnce(reply(on.decision)).mockResolvedValueOnce(reply(off.decision));
  setup(offName); expect(input('bootstrap_repetitions')).toHaveValue(''); expect(input('bootstrap_seed')).toHaveValue('');
  expect(input('bootstrap_repetitions')).toHaveAccessibleDescription(expect.stringContaining('200–1000'));
  expect(fetch).not.toHaveBeenCalled(); submit(); await view().findByRole('article');
  const selected = view().getByRole('region', { name: 'Run and Pass evidence, scroll horizontally on small screens' }).textContent;
  expect(view().queryByRole('region', { name: title })).not.toBeInTheDocument();
  edit('bootstrap_repetitions', '200');
  if ('bootstrap_seed' in on.query) edit('bootstrap_seed', String(on.query.bootstrap_seed));
  expect(view().queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
  submit(); await view().findByRole('region', { name: title });
  expect(view().getByRole('region', { name: 'Run and Pass evidence, scroll horizontally on small screens' })).toHaveTextContent(selected!);
  expect(view().getByText(/Exploratory uncertainty was requested/)).toBeVisible();
  expect(view().queryByText(/Uncertainty was not requested/)).not.toBeInTheDocument();
  expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
  edit('bootstrap_repetitions', ''); edit('bootstrap_seed', ''); submit(); await view().findByRole('article');
  expect(view().queryByRole('region', { name: title })).not.toBeInTheDocument();
  expect(view().getByRole('region', { name: 'Run and Pass evidence, scroll horizontally on small screens' })).toHaveTextContent(selected!);
  for (const [index, query] of [off.query, on.query, off.query].entries()) {
    const url = new URL(String(vi.mocked(fetch).mock.calls[index][0]), 'http://localhost');
    expect(Object.fromEntries(url.searchParams)).toEqual(Object.fromEntries(Object.entries(query).map(([k, v]) => [k, String(v)])));
  }
});

it('distinguishes parent-frequency games from candidate and observed-EPA games, including default seed', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.bootstrap_selected.decision)); setup('bootstrap_selected'); submit();
  const section = await view().findByRole('region', { name: title });
  expect(section).toHaveTextContent('200 / 200 performed / requested draws · seed 0 · 5 games');
  expect(section).toHaveTextContent('selected-only resampling frame');
  expect(section).toHaveTextContent('shared weights still apply across Run and Pass');
  const frequency = cells('Run', 'Selected / Call frequency');
  expect(frequency[0]).toHaveTextContent('40.0%'); expect(frequency[1]).toHaveTextContent('0.0% to 92.3%');
  expect(frequency[2]).toHaveTextContent('Selected 5'); expect(frequency[3]).toHaveTextContent('200 / 0');
  expect(frequency[4]).toHaveTextContent('Available · exploratory');
  const epa = cells('Run', 'Selected / EPA');
  expect(epa[0]).toHaveTextContent('0.333 EPA/play'); expect(epa[1]).toHaveTextContent('Withheld');
  expect(epa[2]).toHaveTextContent('Selected 2'); expect(epa[3]).toHaveTextContent('182 / 18');
  expect(epa[4]).toHaveTextContent('fewer than 5 contributing games');
  expect(cells('Pass', 'Selected / EPA')[2]).toHaveTextContent('Selected 3');
  expect(within(section).getAllByRole('row')).toHaveLength(8); // 3 selected metrics + header, for each call.
  fireEvent.click(view().getByText('Decision uncertainty method and replay metadata'));
  expect(section).toHaveTextContent('game_cluster_percentile_v1 / game_id');
  expect(section).toHaveTextContent('python_random.Random.randrange / linear_n_minus_1');
  for (const warning of fixtures.bootstrap_selected.decision.uncertainty.warnings) expect(within(section).getByText(warning)).toBeVisible();
});

it('shows paired same-call differences with separate support and units, never marginal endpoint subtraction', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.bootstrap_comparison.decision)); setup('bootstrap_comparison'); submit();
  const section = await view().findByRole('region', { name: title });
  expect(section).toHaveTextContent('5 games in the selected + baseline union'); // not ten games
  expect(section).toHaveTextContent('No Pass-minus-Run contrast interval is implemented');
  const freq = cells('Run', 'Selected − baseline / Call frequency');
  expect(freq[0]).toHaveTextContent('-20.0 pp'); expect(freq[1]).toHaveTextContent('-100.0 pp to +86.7 pp');
  expect(freq[2]).toHaveTextContent('Baseline 5 · Selected 5');
  const epa = cells('Run', 'Selected − baseline / EPA');
  expect(epa[0]).toHaveTextContent('-3.556 EPA/play'); expect(epa[1]).toHaveTextContent('Withheld');
  expect(epa[2]).toHaveTextContent('Baseline 3 · Selected 2'); expect(epa[3]).toHaveTextContent('184 / 16');
  expect(cells('Run', 'Selected / EPA')[3]).toHaveTextContent('185 / 15');
  expect(cells('Run', 'Baseline / EPA')[3]).toHaveTextContent('199 / 1');
  expect(within(section).getAllByRole('row')).toHaveLength(20);
  expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
});

it.each([
  ['bootstrap_unobserved', 'Run', 'Selected / Call frequency', '0.0%', 'Withheld', 'constant / near-constant'],
  ['bootstrap_unobserved', 'Run', 'Selected / EPA', 'Unavailable', 'Unavailable', 'Undefined estimate'],
  ['bootstrap_partial_epa', 'Pass', 'Selected / EPA', '-2.000 EPA/play', 'Withheld', 'fewer than 5 contributing games'],
  ['bootstrap_missing_epa', 'Run', 'Selected / EPA', 'Unavailable', 'Unavailable', 'Undefined estimate'],
  ['bootstrap_sparse_draws', 'Run', 'Selected / EPA', '0.000 EPA/play', 'Withheld', 'fewer than 95% defined draws'],
  ['bootstrap_valid_boundary', 'Run', 'Selected / EPA', '0.000 EPA/play', '-2.000 EPA/play to 2.000 EPA/play', 'Available'],
  ['bootstrap_empty', 'Run', 'Selected / Call frequency', 'Unavailable', 'Unavailable', 'Undefined estimate'],
  ['bootstrap_empty_selected', 'Run', 'Selected / Call frequency', 'Unavailable', 'Unavailable', 'Undefined estimate'],
  ['bootstrap_empty_selected_only', 'Run', 'Selected / Call frequency', 'Unavailable', 'Unavailable', 'Undefined estimate'],
] as const)('keeps point and interval states distinct: %s / %s', async (name, call, metric, point, bounds, status) => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures[name].decision)); setup(name); submit();
  const section = await view().findByRole('region', { name: title });
  const row = cells(call, metric); expect(row[0]).toHaveTextContent(point); expect(row[1]).toHaveTextContent(bounds); expect(row[4]).toHaveTextContent(status);
  if (name === 'bootstrap_sparse_draws' || name === 'bootstrap_valid_boundary') {
    expect(row[3]).toHaveTextContent(name === 'bootstrap_sparse_draws' ? '189 / 11' : '190 / 10');
    expect(section).toHaveTextContent('Few games (<20 on a required side)');
    expect(view().getByText(/deliberately controlled draws test/)).toBeVisible();
  }
  if (name === 'bootstrap_partial_epa') expect(row[2]).toHaveTextContent('Selected 1');
  if (name === 'bootstrap_empty' || name === 'bootstrap_empty_selected_only') expect(section).toHaveTextContent('0 / 200 performed / requested draws');
  if (name === 'bootstrap_empty_selected') {
    expect(section).toHaveTextContent('200 / 200 performed / requested draws');
    expect(cells('Run', 'Baseline / Call frequency')[0]).toHaveTextContent('50.0%');
    expect(cells('Run', 'Selected − baseline / Call frequency')[0]).toHaveTextContent('Unavailable');
  }
  expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
});

it('displays available outcome and difference bounds without turning no few-game flag into reliability', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.bootstrap_many_games.decision)); setup('bootstrap_many_games'); submit();
  await view().findByRole('region', { name: title });
  expect(cells('Run', 'Selected / Call frequency')[2]).toHaveTextContent('Selected 20');
  expect(cells('Run', 'Selected / Call frequency')[2]).toHaveTextContent('No few-game flag; not a reliability guarantee');
  expect(cells('Run', 'Selected / EPA')[2]).toHaveTextContent('Selected 10');
  expect(cells('Run', 'Selected / EPA')[1]).toHaveTextContent('-0.175 EPA/play to 1.243 EPA/play');
  expect(cells('Run', 'Selected − baseline / EPA')[1]).toHaveTextContent('-4.231 EPA/play to -1.950 EPA/play');
  expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
});

it.each([
  ['199', '', 'bootstrap_repetitions'], ['1001', '', 'bootstrap_repetitions'], ['2e2', '', 'bootstrap_repetitions'],
  ['200.5', '', 'bootstrap_repetitions'], ['-1', '', 'bootstrap_repetitions'], ['+200', '', 'bootstrap_repetitions'],
  ['abc', '', 'bootstrap_repetitions'], ['200', '-1', 'bootstrap_seed'], ['200', '4294967296', 'bootstrap_seed'],
  ['200', '1.5', 'bootstrap_seed'], ['200', '1e2', 'bootstrap_seed'], ['', '0', 'bootstrap_repetitions'],
])('rejects invalid or orphaned bootstrap fields without fetching: %s / %s', (repetitions, seed, field) => {
  setup('selected'); edit('bootstrap_repetitions', repetitions); edit('bootstrap_seed', seed); submit();
  expect(fetch).not.toHaveBeenCalled(); expect(view().getByRole('alert')).toBeVisible();
  expect(input(field)).toHaveFocus(); expect(input(field)).toHaveAttribute('aria-invalid', 'true');
  expect(input(field)).toHaveAttribute('aria-describedby', 'decision-bootstrap-help decision-query-error');
  expect(input('bootstrap_repetitions')).toHaveValue(repetitions); expect(input('bootstrap_seed')).toHaveValue(seed);
});

it('accepts the bounded maximum and uint32 seed, then preserves mode state with unique IDs', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.bootstrap_maximum.decision)); setup('bootstrap_maximum'); submit();
  const section = await view().findByRole('region', { name: title }); expect(section).toHaveTextContent('1,000 / 1,000 performed / requested draws · seed 4294967295');
  const url = new URL(String(vi.mocked(fetch).mock.calls[0][0]), 'http://localhost');
  expect(url.searchParams.get('bootstrap_repetitions')).toBe('1000'); expect(url.searchParams.get('bootstrap_seed')).toBe('4294967295');
  fireEvent.click(screen.getByRole('tab', { name: 'Scout' }));
  const scout = within(screen.getByRole('tabpanel', { name: 'Scout' }));
  expect(scout.getByRole('textbox', { name: 'Bootstrap repetitions' })).toHaveValue('');
  fireEvent.change(scout.getByRole('textbox', { name: 'Bootstrap repetitions' }), { target: { value: '500' } });
  fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  expect(input('bootstrap_repetitions')).toHaveValue('1000'); expect(section).toBeVisible(); expect(fetch).toHaveBeenCalledTimes(1);
  const ids = Array.from(document.querySelectorAll('[id]'), n => n.id); expect(new Set(ids).size).toBe(ids.length);
});

it('clearing repetitions with a retained seed requires correction, then recovers without uncertainty', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.bootstrap_comparison_plain.decision)); setup('bootstrap_comparison');
  edit('bootstrap_repetitions', ''); submit(); expect(fetch).not.toHaveBeenCalled(); expect(input('bootstrap_repetitions')).toHaveFocus();
  edit('bootstrap_seed', ''); submit(); await view().findByRole('article'); expect(view().queryByRole('region', { name: title })).not.toBeInTheDocument();
});

it('rejects late evidence after an uncertainty edit and retains edited controls on a safe API error', async () => {
  let finish!: (response: Response) => void;
  vi.mocked(fetch).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  setup('bootstrap_selected'); submit(); const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
  edit('bootstrap_seed', '7'); expect(signal.aborted).toBe(true);
  await act(async () => finish(reply(fixtures.bootstrap_selected.decision)));
  expect(view().queryByRole('article')).not.toBeInTheDocument(); expect(view().getByRole('status')).toBeEmptyDOMElement();
  vi.mocked(fetch).mockResolvedValueOnce(reply({ error: { code: 'report_busy', message: 'PRIVATE /operator/path' } }, 503));
  submit(); await view().findByRole('alert'); expect(view().queryByRole('article')).not.toBeInTheDocument();
  expect(input('bootstrap_seed')).toHaveValue('7'); expect(screen.getByRole('tabpanel', { name: 'Decision Lab' })).not.toHaveTextContent('PRIVATE');
});

it.each(['absent', 'seed', 'frame', 'support', 'draws', 'status', 'bounds', 'units', 'contrast'])('rejects malformed uncertainty before rendering: %s', async mutation => {
  const d = structuredClone(fixtures.bootstrap_comparison.decision), u = d.uncertainty;
  if (mutation === 'absent') Reflect.deleteProperty(d, 'uncertainty');
  if (mutation === 'seed') u.seed = 8;
  if (mutation === 'frame') u.resampling_games = 10;
  if (mutation === 'support') u.candidates[0].selected.frequency.support_games.selected = 2;
  if (mutation === 'draws') u.candidates[0].selected.epa_per_play.valid_replicates = 201;
  if (mutation === 'status') u.candidates[0].selected.epa_per_play.status = 'ok';
  if (mutation === 'bounds') u.candidates[0].selected.frequency.interval.lower = -.01;
  if (mutation === 'units') u.candidates[0].difference.frequency_pp.unit = 'proportion';
  if (mutation === 'contrast') Reflect.set(d.comparison.descriptive_contrast.uncertainty, 'interval', { lower: 0, upper: 1 });
  vi.mocked(fetch).mockResolvedValue(reply(d)); setup('bootstrap_comparison'); submit(); await view().findByRole('alert');
  expect(view().queryByRole('article')).not.toBeInTheDocument();
});
