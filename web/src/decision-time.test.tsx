import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { App } from './App';
import fixtures from './__fixtures__/decisions.json';

const reply = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'content-type': 'application/json' } });
const view = () => within(screen.getByRole('tabpanel', { name: 'Decision Lab' }));
const form = () => view().getByRole('form') as HTMLFormElement;
function edit(name: string, value: string) { fireEvent.change(form().elements.namedItem(name) as HTMLElement, { target: { value } }); }
function setup(name: keyof typeof fixtures = 'selected') {
  render(<App />); fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  for (const [key, value] of Object.entries(fixtures[name].query)) if (key !== 'compare_league') edit(key, String(value));
}
const submit = () => fireEvent.click(view().getByRole('button', { name: 'Compare Run and Pass' }));
const params = (index = 0) => new URL(String(vi.mocked(fetch).mock.calls[index][0]), 'http://localhost').searchParams;
const counts = (region: HTMLElement) => within(region).getAllByRole('row').slice(1)
  .map(row => within(row).getAllByRole('cell').map(cell => Number(cell.textContent)));

it('defaults to unrestricted time and explains quarter, whole seconds, missingness and omitted-end defaults', () => {
  setup();
  const period = view().getByRole('combobox', { name: 'Period' });
  expect(period).toHaveValue('');
  expect(within(period).getAllByRole('option').map(option => (option as HTMLOptionElement).value)).toEqual(['', 'Q1', 'Q2', 'Q3', 'Q4', 'OT']);
  expect(period).toHaveAccessibleDescription(expect.stringContaining('does not exclude missing clocks'));
  for (const label of ['Minimum seconds remaining', 'Maximum seconds remaining']) {
    const input = view().getByRole('textbox', { name: label });
    expect(input).toHaveValue('');
    expect(input).toHaveAccessibleDescription(expect.stringContaining('not elapsed time or MM:SS'));
    expect(input).toHaveAccessibleDescription(expect.stringContaining('blank end defaults to 0 or 900'));
  }
  expect(fetch).not.toHaveBeenCalled();
});

// Independently counted invented rows: Q4 has 8 plays, one unknown clock and two above 120.
// Every row is down 1 / distance 10; the last case verifies final-distance exclusion.
it.each([
  ['time_period', [[15, 2, 5, 8], [8, 0, 0, 8], [8, 0, 0, 8]], 8],
  ['time_period_no_clock', [[15, 2, 5, 8], [8, 0, 0, 8], [8, 0, 0, 8]], 8],
  ['time_clock', [[15, 2, 5, 8], [8, 1, 2, 5], [5, 0, 0, 5], [5, 0, 0, 5]], 5],
  ['time_q1', [[15, 2, 12, 1], [1, 0, 0, 1], [1, 0, 0, 1]], 1],
  ['time_q2', [[15, 2, 12, 1], [1, 0, 0, 1], [1, 0, 0, 1], [1, 0, 0, 1]], 1],
  ['time_q3', [[15, 2, 12, 1], [1, 0, 0, 1], [1, 0, 0, 1]], 1],
  ['time_ot', [[15, 2, 11, 2], [2, 0, 0, 2], [2, 0, 0, 2], [2, 0, 0, 2]], 2],
  ['zero_clock', [[15, 2, 5, 8], [8, 1, 6, 1], [1, 0, 0, 1], [1, 0, 0, 1]], 1],
  ['time_lower_only', [[15, 2, 5, 8], [8, 1, 6, 1], [1, 0, 0, 1], [1, 0, 0, 1]], 1],
  ['time_full_clock', [[15, 2, 5, 8], [8, 1, 0, 7], [7, 0, 0, 7], [7, 0, 0, 7]], 7],
  ['time_four_stage', [[15, 2, 1, 12], [12, 1, 0, 11], [11, 1, 5, 5], [5, 1, 1, 3], [3, 0, 0, 3], [3, 0, 0, 3]], 3],
  ['time_all_missing_period', [[15, 15, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], 0],
  ['time_all_missing_clock', [[15, 2, 5, 8], [8, 8, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], 0],
  ['time_empty_clock', [[15, 2, 5, 8], [8, 1, 7, 0], [0, 0, 0, 0], [0, 0, 0, 0]], 0],
  ['time_boundary', [[15, 2, 5, 8], [8, 1, 6, 1], [1, 0, 0, 1], [1, 0, 0, 1]], 1],
  ['time_distance_empty', [[15, 2, 5, 8], [8, 1, 2, 5], [5, 0, 0, 5], [5, 0, 5, 0]], 0],
] as const)('renders time stages and final denominators without widening: %s', async (name, expected, plays) => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures[name].decision));
  setup(name); submit();
  const filters = await view().findByRole('region', { name: 'Situation filters' });
  expect(counts(filters)).toEqual(expected);
  const hasClock = 'clock' in fixtures[name].decision.cohort;
  expect(within(filters).getAllByRole('rowheader').map(row => row.textContent)).toEqual([
    ...(name === 'time_four_stage' ? ['Field position', 'Pre-play score'] : []), 'Period', ...(hasClock ? ['Clock'] : []), 'Down', 'Distance',
  ]);
  expect(within(filters).getByText(/Q4 excludes overtime/)).toBeVisible();
  expect(within(filters).getByText(/use only final distance-stage survivors/)).toBeVisible();
  expect(within(filters).getByText(/do not add them again/)).toBeVisible();
  expect(view().getByRole('status')).toHaveTextContent(`CAR, ${plays} eligible plays.`);
  expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
  expect(view().queryByText(/Period and clock: unrestricted/)).not.toBeInTheDocument();
  expect(Object.fromEntries(params())).toEqual(Object.fromEntries(Object.entries(fixtures[name].query).map(([key, value]) => [key, String(value)])));
  for (const warning of fixtures[name].decision.warnings) expect(view().getByText(warning)).toBeVisible();
  if (!plays) expect(view().getByRole('heading', { name: 'No eligible plays match this situation.' })).toBeVisible();
  if (!hasClock) expect(within(filters).getByText(/Clock unrestricted: period selection alone/)).toBeVisible();
  if (name === 'time_ot') {
    expect(within(filters).getByText('OT — all periods numbered 5 or higher')).toBeVisible();
    expect(view().getByRole('row', { name: /^Run/ })).toHaveTextContent('-0.600');
    expect(view().getByRole('row', { name: /^Pass/ })).toHaveTextContent('0.400'); // periods 5 AND 6
  }
  if (name === 'time_four_stage') {
    expect(within(filters).getByText('0–120 seconds remaining at play start')).toBeVisible();
    const run = view().getByRole('row', { name: /^Run/ });
    expect(run).toHaveTextContent('2 / 3 plays'); expect(run).toHaveTextContent('-0.400');
    expect(run).toHaveTextContent('1 observed EPA denominator'); // one of two runs has missing EPA
    expect(view().getByRole('row', { name: /^Pass/ })).toHaveTextContent('0.800'); // future EPA=99 is excluded
  }
  if (name === 'zero_clock') expect(within(filters).getByText('0–0 seconds remaining at play start')).toBeVisible();
  if (name === 'time_boundary') expect(view().getByRole('row', { name: /^Pass/ })).toHaveTextContent('0.800');
  if (name === 'time_lower_only') {
    expect(within(filters).getByText('900–900 seconds remaining at play start')).toBeVisible();
    const run = within(view().getByRole('row', { name: /^Run/ }));
    expect(run.getAllByText('Unavailable')).toHaveLength(2);
    expect(run.getByText(/EPA missing for every observed play/)).toBeVisible();
  }
});

it.each([
  ['clock_min', '-1'], ['clock_max', '+1'], ['clock_min', '1.0'], ['clock_max', '1e2'],
  ['clock_min', 'NaN'], ['clock_max', 'Infinity'], ['clock_min', '901'], ['clock_max', '2:00'],
] as const)('preserves invalid %s=%s as an accessible error without HTTP', (name, value) => {
  setup('time_period'); edit(name, value); submit();
  const input = form().elements.namedItem(name)!;
  expect(input).toHaveValue(value); expect(input).toHaveFocus();
  expect(input).toHaveAttribute('aria-invalid', 'true');
  expect(input).toHaveAccessibleDescription(expect.stringContaining('Clock bounds must be whole seconds'));
  expect(fetch).not.toHaveBeenCalled();
  edit(name, '0'); expect(input).not.toHaveAttribute('aria-invalid');
});

it.each(['clock_min', 'clock_max'])('requires a period even when %s is zero, with focus on the missing period', name => {
  setup(); edit(name, '0'); submit();
  expect(view().getByRole('combobox', { name: 'Period' })).toHaveFocus();
  expect(view().getByRole('combobox', { name: 'Period' })).toHaveAccessibleDescription(expect.stringContaining('Choose an explicit period'));
  expect(form().elements.namedItem(name)).toHaveValue('0'); expect(fetch).not.toHaveBeenCalled();
});

it('rejects reversed clock bounds, then preserves zero and canonicalizes whitespace', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.zero_clock.decision));
  setup('time_period'); edit('clock_min', '121'); edit('clock_max', '120'); submit();
  expect(form().elements.namedItem('clock_min')).toHaveFocus();
  for (const name of ['clock_min', 'clock_max']) expect(form().elements.namedItem(name)).toHaveAttribute('aria-invalid', 'true');
  expect(fetch).not.toHaveBeenCalled();
  edit('clock_min', ' 0 '); edit('clock_max', ' 0 '); submit(); await view().findByRole('article');
  expect(params().get('clock_min')).toBe('0'); expect(params().get('clock_max')).toBe('0');
});

it('removing a clock range keeps the period and restores missing clocks from the same snapshot', async () => {
  expect(fixtures.time_full_clock.decision.source).toEqual(fixtures.time_period.decision.source);
  vi.mocked(fetch).mockResolvedValueOnce(reply(fixtures.time_full_clock.decision)).mockResolvedValueOnce(reply(fixtures.time_period.decision));
  setup('time_full_clock'); submit(); await view().findByRole('article');
  expect(view().getByRole('status')).toHaveTextContent('7 eligible plays');
  edit('clock_min', ''); edit('clock_max', '');
  expect(view().queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
  submit(); await view().findByRole('article');
  expect(params(1).has('clock_min')).toBe(false); expect(params(1).has('clock_max')).toBe(false);
  expect(params(1).get('period')).toBe('Q4'); expect(view().getByRole('status')).toHaveTextContent('8 eligible plays');
  expect(view().getByText(/Clock unrestricted: period selection alone/)).toBeVisible();
  expect(view().queryByRole('rowheader', { name: 'Clock' })).not.toBeInTheDocument();
});

it('clearing period retains clock text and blocks HTTP until both bounds are cleared; earlier filters stay fixed', async () => {
  expect(fixtures.time_four_stage.decision.source).toEqual(fixtures.time_context_unrestricted.decision.source);
  vi.mocked(fetch).mockResolvedValueOnce(reply(fixtures.time_four_stage.decision)).mockResolvedValueOnce(reply(fixtures.time_context_unrestricted.decision));
  setup('time_four_stage'); submit(); await view().findByRole('article');
  edit('period', ''); expect(form().elements.namedItem('clock_max')).toHaveValue('120');
  expect(view().queryByRole('article')).not.toBeInTheDocument(); submit();
  expect(form().elements.namedItem('period')).toHaveFocus(); expect(fetch).toHaveBeenCalledTimes(1);
  edit('clock_max', ''); submit(); await view().findByRole('article');
  expect(Object.fromEntries(params(1))).toEqual(Object.fromEntries(Object.entries(fixtures.time_context_unrestricted.query).map(([key, value]) => [key, String(value)])));
  expect(view().getByRole('status')).toHaveTextContent('11 eligible plays');
  expect(view().getByText('Period and clock: unrestricted; no time-context exclusions.')).toBeVisible();
  expect(counts(view().getByRole('region', { name: 'Situation filters' }))).toEqual([[15, 2, 1, 12], [12, 1, 0, 11], [11, 0, 0, 11], [11, 0, 0, 11]]);
});

it.each([['period', 'OT'], ['clock_min', '60'], ['clock_max', '0']])('editing %s aborts and rejects a late time-filter response', async (name, value) => {
  let finish!: (response: Response) => void;
  vi.mocked(fetch).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  setup('time_four_stage'); submit(); const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
  edit(name, value); expect(signal.aborted).toBe(true);
  await act(async () => finish(reply(fixtures.time_four_stage.decision)));
  expect(view().queryByRole('article')).not.toBeInTheDocument(); expect(view().getByRole('status')).toBeEmptyDOMElement();
});

it('preserves independent time drafts, completed evidence and unique help IDs across modes', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.time_four_stage.decision));
  setup('time_four_stage'); submit(); await view().findByRole('article');
  fireEvent.click(screen.getByRole('tab', { name: 'Scout' }));
  const scoutPeriod = screen.getByRole('combobox', { name: 'Period' });
  expect(scoutPeriod).toHaveValue(''); fireEvent.change(scoutPeriod, { target: { value: 'Q2' } });
  fireEvent.change(screen.getByRole('textbox', { name: 'Maximum seconds remaining' }), { target: { value: '60' } });
  fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  expect(form().elements.namedItem('period')).toHaveValue('Q4'); expect(form().elements.namedItem('clock_max')).toHaveValue('120');
  expect(view().getByRole('status')).toHaveTextContent('3 eligible plays');
  const ids = Array.from(document.querySelectorAll('[id]'), node => node.id);
  expect(new Set(ids).size).toBe(ids.length); expect(fetch).toHaveBeenCalledTimes(1);
});

it('handles absent requested context columns as a safe error without converting them to empty or unrestricted evidence', async () => {
  vi.mocked(fetch).mockResolvedValue(reply({ error: { code: 'context_unavailable', message: '/private/operator/snapshot.csv' } }, 422));
  setup('time_clock'); submit();
  expect(await view().findByRole('alert')).toHaveTextContent('snapshot lacks a requested context column');
  expect(screen.getByRole('tabpanel', { name: 'Decision Lab' })).not.toHaveTextContent('/private/operator');
  expect(view().queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
});

it.each(['period_bounds', 'clock_bounds', 'post_play', 'clock_field', 'missing_policy', 'missing_ledger', 'missing_count', 'stage_order', 'stage_chain'])('rejects inconsistent time evidence: %s', async mutation => {
  const data = structuredClone(fixtures.time_four_stage.decision);
  if (mutation === 'period_bounds') data.cohort.period.maximum_inclusive = 5;
  if (mutation === 'clock_bounds') data.cohort.clock.minimum_inclusive = 1;
  if (mutation === 'post_play') data.cohort.clock.timing = 'post_play';
  if (mutation === 'clock_field') data.cohort.clock.field = 'game_seconds_remaining';
  if (mutation === 'missing_policy') data.cohort.period.missing_policy = 'include';
  if (mutation === 'missing_ledger') Reflect.deleteProperty(data.data_quality, 'clock_filter');
  if (mutation === 'missing_count') data.data_quality.clock_filter.missing_quarter_seconds_remaining += 1;
  if (mutation === 'stage_order') data.data_quality.filter_order.splice(2, 2, 'clock', 'period');
  if (mutation === 'stage_chain') { data.data_quality.clock_filter.plays_before_filter += 1; data.data_quality.clock_filter.outside_range += 1; }
  vi.mocked(fetch).mockResolvedValue(reply(data)); setup('time_four_stage'); submit();
  expect(await view().findByRole('alert')).toBeVisible(); expect(view().queryByRole('article')).not.toBeInTheDocument();
});
