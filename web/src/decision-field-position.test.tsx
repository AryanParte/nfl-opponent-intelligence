import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { App } from './App';
import fixtures from './__fixtures__/decisions.json';

const response = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'content-type': 'application/json' } });
const panel = () => screen.getByRole('tabpanel', { name: 'Decision Lab' });
const view = () => within(panel());
const form = () => view().getByRole('form') as HTMLFormElement;
function edit(name: string, value: string) { fireEvent.change(form().elements.namedItem(name) as HTMLElement, { target: { value } }); }
function setup(name: keyof typeof fixtures = 'selected') {
  render(<App />);
  fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  for (const [key, value] of Object.entries(fixtures[name].query)) {
    if (key !== 'compare_league') edit(key, String(value));
  }
}
const submit = () => fireEvent.click(view().getByRole('button', { name: 'Compare Run and Pass' }));

it('keeps field bounds blank by default and explains offense coordinates and explicit full-range missingness', () => {
  setup();
  for (const name of ['Minimum yards to goal', 'Maximum yards to goal']) {
    const input = view().getByRole('textbox', { name });
    expect(input).toHaveValue('');
    expect(input).toHaveAttribute('inputmode', 'decimal');
    expect(input).toHaveAccessibleDescription(expect.stringContaining('Any requested range, even 0–100, excludes missing positions.'));
  }
  expect(view().getByText(/20 = opponent’s 20; 80 = own 20/)).toBeVisible();
  expect(fetch).not.toHaveBeenCalled();
});

it.each([
  ['field_partial', [[6, 1, 2, 3], [3, 0, 1, 2], [2, 0, 1, 1]], '0–20.5', 1],
  ['field_full', [[6, 1, 0, 5], [5, 0, 3, 2], [2, 0, 0, 2]], '0–100', 2],
  ['field_all_missing', [[6, 6, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], '0–100', 0],
  ['field_fractional', [[6, 1, 4, 1], [1, 0, 0, 1], [1, 0, 0, 1]], '20.5–20.5', 1],
  ['field_zero', [[6, 1, 4, 1], [1, 0, 0, 1], [1, 0, 0, 1]], '0–0', 1],
  ['field_lower', [[6, 1, 3, 2], [2, 0, 1, 1], [1, 0, 0, 1]], '80–100', 1],
  ['field_empty', [[6, 1, 5, 0], [0, 0, 0, 0], [0, 0, 0, 0]], '91–99', 0],
] as const)('renders independent ordered counts and effective bounds: %s', async (name, expected, bounds, finalPlays) => {
  vi.mocked(fetch).mockResolvedValue(response(fixtures[name].decision));
  setup(name); submit();
  const region = within(await view().findByRole('region', { name: 'Situation filters' }));
  expect(region.getByText(`${bounds} yards to the offense’s opponent’s goal line`)).toBeVisible();
  expect(region.getAllByRole('rowheader').map(row => row.textContent)).toEqual(['Field position', 'Down', 'Distance']);
  expect(region.getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell').map(cell => Number(cell.textContent)))).toEqual(expected);
  expect(region.getByText(/use only final distance-stage survivors/)).toBeVisible();
  expect(region.getByText(/do not add them again/)).toBeVisible();
  expect(view().getByRole('status')).toHaveTextContent(`CAR, ${finalPlays} eligible plays.`);
  expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
  for (const warning of fixtures[name].decision.warnings) expect(view().getByText(warning)).toBeVisible();
  expect(view().queryByRole('alert')).not.toBeInTheDocument();
  if (finalPlays === 0) expect(view().getByRole('heading', { name: 'No eligible plays match this situation.' })).toBeVisible();
  if (name === 'field_fractional') {
    const run = within(view().getByRole('row', { name: /^Run/ }));
    expect(run.getByText('100.0%')).toBeVisible();
    expect(run.getAllByText('Unavailable')).toHaveLength(2);
    expect(run.getByText(/EPA missing for every observed play/)).toBeVisible();
  }
  if (name === 'field_lower') expect(view().getByText('0.000')).toBeVisible(); // before-week excludes future EPA=8
  const sent = Object.fromEntries(new URL(String(vi.mocked(fetch).mock.calls[0][0]), 'http://localhost').searchParams);
  expect(sent).toEqual(Object.fromEntries(Object.entries(fixtures[name].query).map(([key, value]) => [key, String(value)])));
});

it.each([
  ['yardline_min', '-1'], ['yardline_max', '101'], ['yardline_min', '1e'], ['yardline_max', 'NaN'],
  ['yardline_min', 'Infinity'], ['yardline_max', '20,5'], ['yardline_max', '.'],
] as const)('retains invalid %s=%s, links its error and prevents a silent unfiltered request', (name, value) => {
  setup(); edit(name, value); submit();
  const field = form().elements.namedItem(name)!;
  expect(field).toHaveValue(value);
  expect(field).toHaveFocus();
  expect(field).toHaveAttribute('aria-invalid', 'true');
  expect(field).toHaveAccessibleDescription(expect.stringContaining('Field-position bounds must be decimals'));
  expect(fetch).not.toHaveBeenCalled();
  edit(name, '20.5');
  expect(field).not.toHaveAttribute('aria-invalid');
  expect(view().queryByRole('alert')).not.toBeInTheDocument();
});

it('marks both reversed bounds and focuses the minimum before requesting', () => {
  setup(); edit('yardline_min', '80'); edit('yardline_max', '20'); submit();
  expect(view().getByRole('textbox', { name: 'Minimum yards to goal' })).toHaveFocus();
  for (const label of ['Minimum yards to goal', 'Maximum yards to goal']) {
    expect(view().getByRole('textbox', { name: label })).toHaveAttribute('aria-invalid', 'true');
  }
  expect(view().getByRole('alert')).toHaveTextContent('Minimum yards to goal must not exceed maximum yards to goal.');
  expect(fetch).not.toHaveBeenCalled();
});

it('clears stale evidence and omits both blank bounds on an explicit unfiltered retry', async () => {
  vi.mocked(fetch).mockResolvedValueOnce(response(fixtures.field_full.decision)).mockResolvedValueOnce(response(fixtures.selected.decision));
  setup('field_full'); submit(); await view().findByRole('article');
  edit('yardline_min', ''); edit('yardline_max', '');
  expect(view().queryByRole('article')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
  submit(); await view().findByRole('article');
  expect(view().getByText('Field position: unrestricted; missing positions are not excluded by field position.')).toBeVisible();
  expect(view().getByRole('status')).toHaveTextContent('CAR, 3 eligible plays.');
  expect(String(vi.mocked(fetch).mock.calls[1][0])).not.toContain('yardline_');
  expect(view().queryByRole('region', { name: 'Situation filters' })).not.toBeInTheDocument();
});

it.each(['yardline_min', 'yardline_max'])('editing %s aborts and rejects a late filtered response', async name => {
  let finish!: (response: Response) => void;
  vi.mocked(fetch).mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  setup('field_full'); submit();
  const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
  edit(name, '20'); expect(signal.aborted).toBe(true);
  await act(async () => finish(response(fixtures.field_full.decision)));
  expect(view().queryByRole('article')).not.toBeInTheDocument();
  expect(view().getByRole('status')).toBeEmptyDOMElement();
});

it('preserves a field-filtered result across mode changes without colliding with Scout controls', async () => {
  vi.mocked(fetch).mockResolvedValue(response(fixtures.field_partial.decision));
  setup('field_partial'); submit(); await view().findByRole('article');
  fireEvent.click(screen.getByRole('tab', { name: 'Scout' }));
  expect(screen.getByRole('textbox', { name: 'Maximum yards to goal' })).toHaveValue('');
  fireEvent.change(screen.getByRole('textbox', { name: 'Maximum yards to goal' }), { target: { value: '80' } });
  fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  expect(view().getByRole('textbox', { name: 'Maximum yards to goal' })).toHaveValue('20.5');
  expect(view().getByRole('region', { name: 'Situation filters' })).toBeVisible();
  expect(fetch).toHaveBeenCalledTimes(1);
  const ids = Array.from(document.querySelectorAll('[id]'), node => node.id);
  expect(new Set(ids).size).toBe(ids.length);
});

it('reports an unavailable column as an error without widening or exposing server paths', async () => {
  vi.mocked(fetch).mockResolvedValue(response({ error: { code: 'context_unavailable', message: '/private/snapshot.csv' } }, 422));
  setup('field_full'); submit();
  expect(await view().findByRole('alert')).toHaveTextContent('snapshot lacks a requested context column');
  expect(panel()).not.toHaveTextContent('/private/snapshot.csv');
  expect(view().queryByRole('article')).not.toBeInTheDocument();
  expect(fetch).toHaveBeenCalledTimes(1);
});

it.each(['bounds', 'missing_ledger', 'missing_count', 'stage_order', 'final_count'])('fails closed on inconsistent field response: %s', async mutation => {
  const data = structuredClone(fixtures.field_partial.decision);
  if (mutation === 'bounds') data.cohort.field_position.maximum_inclusive = 21;
  if (mutation === 'missing_ledger') Reflect.deleteProperty(data.data_quality, 'field_position_filter');
  if (mutation === 'missing_count') data.data_quality.field_position_filter.missing_yardline_100 += 1;
  if (mutation === 'stage_order') data.data_quality.filter_order.reverse();
  if (mutation === 'final_count') data.data_quality.distance_filter.plays_after_filter += 1;
  vi.mocked(fetch).mockResolvedValue(response(data));
  setup('field_partial'); submit();
  expect(await view().findByRole('alert')).toBeVisible();
  expect(view().queryByRole('article')).not.toBeInTheDocument();
});
