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

it('starts with blank score bounds and describes pre-play signs and unbounded ends', () => {
  setup();
  for (const label of ['Minimum score difference', 'Maximum score difference']) {
    const input = view().getByRole('textbox', { name: label });
    expect(input).toHaveValue('');
    expect(input).not.toHaveAttribute('inputmode', 'numeric'); // keyboard must allow minus
    expect(input).toHaveAccessibleDescription(expect.stringContaining('A blank end is unbounded'));
    expect(input).toHaveAccessibleDescription(expect.stringContaining('Offense points minus defense points before the play'));
  }
  expect(fetch).not.toHaveBeenCalled();
});

it.each([
  ['score_range', [[6, 2, 2, 2], [2, 0, 1, 1], [1, 0, 0, 1]], '-7 to 0 points', 1],
  ['score_lower_only', [[6, 2, 2, 2], [2, 0, 1, 1], [1, 0, 0, 1]], 'At least +1 points', 1],
  ['score_upper_only', [[6, 2, 3, 1], [1, 0, 0, 1], [1, 0, 0, 1]], 'At most -7 points', 1],
  ['score_tied', [[6, 2, 3, 1], [1, 0, 0, 1], [1, 0, 0, 1]], '0 to 0 points', 1],
  ['score_input_limits', [[6, 2, 0, 4], [4, 0, 2, 2], [2, 0, 0, 2]], '-1000 to +1000 points', 2],
  ['score_empty', [[6, 2, 4, 0], [0, 0, 0, 0], [0, 0, 0, 0]], '-6 to -1 points', 0],
  ['score_all_missing', [[6, 6, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], 'At most 0 points', 0],
  ['score_missing_epa', [[6, 2, 3, 1], [1, 0, 0, 1], [1, 0, 0, 1]], '0 to 0 points', 1],
  ['score_field', [[6, 1, 2, 3], [3, 1, 0, 2], [2, 0, 1, 1], [1, 0, 0, 1]], '-7 to 0 points', 1],
  ['score_zero_lower', [[6, 2, 1, 3], [3, 0, 2, 1], [1, 0, 0, 1]], 'At least 0 points', 1],
  ['score_distance_empty', [[6, 2, 2, 2], [2, 0, 1, 1], [1, 0, 1, 0]], '-7 to 0 points', 0],
] as const)('renders independent exclusions, signs and final survivor counts: %s', async (name, counts, range, plays) => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures[name].decision));
  setup(name); submit();
  const filters = within(await view().findByRole('region', { name: 'Situation filters' }));
  expect(filters.getByText(range)).toBeVisible();
  expect(filters.getByText(/A blank end remains unbounded, not zero/)).toBeVisible();
  expect(filters.getByText(/No post-play score substitution/)).toBeVisible();
  expect(filters.getAllByRole('rowheader').map(row => row.textContent)).toEqual([
    ...(name === 'score_field' ? ['Field position'] : []), 'Pre-play score', 'Down', 'Distance',
  ]);
  expect(filters.getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell').map(cell => Number(cell.textContent)))).toEqual(counts);
  expect(filters.getByText(/use only final distance-stage survivors/)).toBeVisible();
  expect(filters.getByText(/do not add them again/)).toBeVisible();
  expect(view().getByRole('status')).toHaveTextContent(`CAR, ${plays} eligible plays.`);
  expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
  for (const warning of fixtures[name].decision.warnings) expect(view().getByText(warning)).toBeVisible();
  expect(view().queryByRole('alert')).not.toBeInTheDocument();
  const sent = Object.fromEntries(new URL(String(vi.mocked(fetch).mock.calls[0][0]), 'http://localhost').searchParams);
  expect(sent).toEqual(Object.fromEntries(Object.entries(fixtures[name].query).map(([key, value]) => [key, String(value)])));
  if (name === 'score_field') expect(filters.getByText(/a play missing both fields is removed at the field stage/)).toBeVisible();
  if (!plays) expect(view().getByRole('heading', { name: 'No eligible plays match this situation.' })).toBeVisible();
  if (name === 'score_tied') expect(view().getByText('0.200')).toBeVisible();
  if (name === 'score_lower_only' || name === 'score_zero_lower') expect(view().getByText('0.000')).toBeVisible(); // future EPA=8 excluded
  if (name === 'score_missing_epa') {
    const run = within(view().getByRole('row', { name: /^Run/ }));
    expect(run.getByText('100.0%')).toBeVisible();
    expect(run.getAllByText('Unavailable')).toHaveLength(2);
    expect(run.getByText(/EPA missing for every observed play/)).toBeVisible();
  }
});

it.each([
  ['score_min', '-'], ['score_max', '+'], ['score_min', '-7.0'], ['score_max', '1e2'],
  ['score_min', '-1001'], ['score_max', '1001'], ['score_min', 'NaN'], ['score_max', 'Infinity'],
] as const)('preserves invalid %s=%s, focuses its error and makes no request', (name, value) => {
  setup(); edit(name, value); submit();
  const input = form().elements.namedItem(name)!;
  expect(input).toHaveValue(value); expect(input).toHaveFocus();
  expect(input).toHaveAttribute('aria-invalid', 'true');
  expect(input).toHaveAccessibleDescription(expect.stringContaining('Pre-play score bounds must be signed whole points'));
  expect(fetch).not.toHaveBeenCalled();
  edit(name, '0'); expect(input).not.toHaveAttribute('aria-invalid');
  expect(view().queryByRole('alert')).not.toBeInTheDocument();
});

it('rejects reversed bounds and keeps an explicit leading plus and whitespace semantically valid', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.score_lower_only.decision));
  setup(); edit('score_min', '7'); edit('score_max', '-7'); submit();
  expect(fetch).not.toHaveBeenCalled();
  expect(view().getByRole('textbox', { name: 'Minimum score difference' })).toHaveFocus();
  for (const label of ['Minimum score difference', 'Maximum score difference']) {
    expect(view().getByRole('textbox', { name: label })).toHaveAttribute('aria-invalid', 'true');
  }
  edit('score_min', ' +1 '); edit('score_max', ''); submit(); await view().findByRole('article');
  const params = new URL(String(vi.mocked(fetch).mock.calls[0][0]), 'http://localhost').searchParams;
  expect(params.get('score_min')).toBe('1'); expect(params.has('score_max')).toBe(false);
});

it('clears both score bounds while retaining the field query and replacing stale evidence', async () => {
  vi.mocked(fetch).mockResolvedValueOnce(reply(fixtures.score_field.decision)).mockResolvedValueOnce(reply(fixtures.score_field_unrestricted.decision));
  setup('score_field'); submit(); await view().findByRole('article');
  edit('score_min', ''); edit('score_max', '');
  expect(view().queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
  expect(view().getByRole('textbox', { name: 'Maximum yards to goal' })).toHaveValue('20.5');
  submit(); await view().findByRole('article');
  const params = new URL(String(vi.mocked(fetch).mock.calls[1][0]), 'http://localhost').searchParams;
  expect(params.has('score_min')).toBe(false); expect(params.has('score_max')).toBe(false);
  expect(params.get('yardline_max')).toBe('20.5');
  expect(view().getByText('Pre-play score: unrestricted; missing scores are not excluded by score.')).toBeVisible();
  const ledger = within(view().getByRole('region', { name: 'Decision filter accounting, scroll horizontally on small screens' }));
  expect(ledger.getAllByRole('rowheader').map(row => row.textContent)).toEqual(['Field position', 'Down', 'Distance']);
  expect(ledger.getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell').map(cell => Number(cell.textContent)))).toEqual([
    [6, 1, 2, 3], [3, 0, 2, 1], [1, 0, 0, 1],
  ]);
});

it.each(['score_min', 'score_max'])('editing %s cancels and rejects a late combined-context response', async name => {
  let finish!: (response: Response) => void;
  vi.mocked(fetch).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  setup('score_field'); submit();
  const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
  edit(name, '1'); expect(signal.aborted).toBe(true);
  await act(async () => finish(reply(fixtures.score_field.decision)));
  expect(view().queryByRole('article')).not.toBeInTheDocument();
  expect(view().getByRole('status')).toBeEmptyDOMElement();
});

it('preserves independent Scout and Decision score drafts, results and help IDs', async () => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures.score_field.decision));
  setup('score_field'); submit(); await view().findByRole('article');
  fireEvent.click(screen.getByRole('tab', { name: 'Scout' }));
  const scoutInput = screen.getByRole('textbox', { name: 'Minimum score difference' });
  expect(scoutInput).toHaveValue('');
  expect(scoutInput).toHaveAccessibleDescription(expect.stringContaining('Defense mode does not reverse the sign'));
  fireEvent.change(scoutInput, { target: { value: '14' } });
  fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  expect(view().getByRole('textbox', { name: 'Minimum score difference' })).toHaveValue('-7');
  expect(view().getByRole('region', { name: 'Situation filters' })).toBeVisible();
  const ids = Array.from(document.querySelectorAll('[id]'), node => node.id);
  expect(new Set(ids).size).toBe(ids.length); expect(fetch).toHaveBeenCalledTimes(1);
});

it('keeps a missing score column as a safe error instead of an empty or unfiltered result', async () => {
  vi.mocked(fetch).mockResolvedValue(reply({ error: { code: 'context_unavailable', message: '/private/operator/snapshot.csv' } }, 422));
  setup('score_range'); submit();
  expect(await view().findByRole('alert')).toHaveTextContent('snapshot lacks a requested context column');
  expect(screen.getByRole('tabpanel', { name: 'Decision Lab' })).not.toHaveTextContent('/private/operator');
  expect(view().queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
});

it.each(['bounds', 'perspective', 'missing_ledger', 'missing_count', 'stage_order', 'stage_chain', 'final_count'])('rejects inconsistent combined score evidence: %s', async mutation => {
  const data = structuredClone(fixtures.score_field.decision);
  if (mutation === 'bounds') data.cohort.score_differential.minimum_inclusive = -8;
  if (mutation === 'perspective') Object.assign(data.cohort.score_differential, { perspective: 'defense' });
  if (mutation === 'missing_ledger') Reflect.deleteProperty(data.data_quality, 'score_differential_filter');
  if (mutation === 'missing_count') data.data_quality.score_differential_filter.missing_score_differential += 1;
  if (mutation === 'stage_order') data.data_quality.filter_order.splice(0, 2, 'score_differential', 'field_position');
  if (mutation === 'stage_chain') { data.data_quality.score_differential_filter.plays_before_filter += 1; data.data_quality.score_differential_filter.outside_range += 1; }
  if (mutation === 'final_count') data.data_quality.distance_filter.plays_after_filter += 1;
  vi.mocked(fetch).mockResolvedValue(reply(data)); setup('score_field'); submit();
  expect(await view().findByRole('alert')).toBeVisible();
  expect(view().queryByRole('article')).not.toBeInTheDocument();
});
