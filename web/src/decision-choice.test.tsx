import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { App } from './App';
import fixtures from './__fixtures__/decisions.json';

const reply = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json' } });
const view = () => within(screen.getByRole('tabpanel', { name: 'Decision Lab' }));
const input = (name: string) => (view().getByRole('form') as HTMLFormElement).elements.namedItem(name) as HTMLElement;
const edit = (name: string, value: string) => fireEvent.change(input(name), { target: { value } });
const select = (name: 'Run' | 'Pass') => fireEvent.click(view().getByRole('radio', { name }));
const submit = () => fireEvent.click(view().getByRole('button', { name: 'Compare Run and Pass' }));
const contrast = () => view().getByRole('region', { name: 'Run vs Pass: descriptive contrast' });
const values = () => within(contrast()).getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell')[0].textContent);
const points = () => view().getByRole('table', { name: 'Observed Run and Pass evidence for the selected offense' });
function setup(name: keyof typeof fixtures = 'selected') {
  render(<App />); fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  for (const [key, value] of Object.entries(fixtures[name].query)) {
    if (key === 'compare_league') { if (value) fireEvent.click(input(key)); }
    else edit(key, String(value));
  }
}

it('starts with no choice, supports native keyboard selection and clearing without fetching', async () => {
  setup(); const user = userEvent.setup();
  const group = view().getByRole('group', { name: 'Your call (optional)' });
  expect(group).toHaveAccessibleDescription(expect.stringContaining('Editing any query field clears your choice'));
  const run = view().getByRole('radio', { name: 'Run' }), pass = view().getByRole('radio', { name: 'Pass' });
  expect(run).not.toBeChecked(); expect(pass).not.toBeChecked();
  const clear = view().getByRole('button', { name: 'Clear choice' }); expect(clear).toBeDisabled();
  run.focus(); await user.keyboard(' '); expect(run).toBeChecked();
  await user.keyboard('{ArrowRight}'); expect(pass).toHaveFocus(); expect(pass).toBeChecked(); expect(run).not.toBeChecked();
  await user.tab(); expect(clear).toHaveFocus(); await user.keyboard('{Enter}');
  expect(clear).toBeDisabled(); expect(run).not.toBeChecked(); expect(pass).not.toBeChecked();
  expect(fetch).not.toHaveBeenCalled();
});

it('annotates stable rows without changing the query, evidence, fixed contrast, source, intervals or Scout state', async () => {
  const fixture = fixtures.bootstrap_context;
  const serialized = JSON.stringify(fixture.decision);
  vi.mocked(fetch).mockResolvedValue(reply(fixture.decision)); setup('bootstrap_context'); select('Run'); submit();
  await view().findByRole('article');
  const url = new URL(String(vi.mocked(fetch).mock.calls[0][0]), 'http://localhost');
  expect(Object.fromEntries(url.searchParams)).toEqual(Object.fromEntries(Object.entries(fixture.query).map(([key, value]) => [key, String(value)])));
  const tableBefore = within(points()).getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell').map(cell => cell.textContent));
  const contrastBefore = within(contrast()).getByRole('table').textContent;
  const league = view().getByRole('region', { name: 'Matched candidate league comparison' }).textContent;
  const uncertainty = view().getByRole('region', { name: 'Candidate game support and exploratory uncertainty' }).textContent;
  fireEvent.click(view().getByText('Inspect source fingerprints'));
  expect(view().getByText(fixture.decision.source.sha256)).toBeVisible();
  const assertChoice = (selected: 'Run' | 'Pass') => {
    const [run, pass] = within(points()).getAllByRole('rowheader');
    expect(run).toHaveTextContent(/^Run/); expect(pass).toHaveTextContent(/^Pass/);
    expect(run).toHaveTextContent(selected === 'Run' ? 'Your choice' : 'Alternative');
    expect(pass).toHaveTextContent(selected === 'Pass' ? 'Your choice' : 'Alternative');
    expect(contrast()).toHaveTextContent(`Your choice: ${selected}. Alternative: ${selected === 'Run' ? 'Pass' : 'Run'}.`);
    expect(values()).toEqual(['-33.3 pp', '+1.200 EPA/play', '+100.0 pp']);
    expect(within(contrast()).getByRole('table')).toHaveTextContent(contrastBefore!);
    expect(within(points()).getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell').map(cell => cell.textContent))).toEqual(tableBefore);
    expect(view().getByRole('region', { name: 'Matched candidate league comparison' })).toHaveTextContent(league!);
    expect(view().getByRole('region', { name: 'Candidate game support and exploratory uncertainty' })).toHaveTextContent(uncertainty!);
    expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
    expect(contrast()).toHaveTextContent('Pass-minus-Run interval: not implemented.');
    expect(fetch).toHaveBeenCalledTimes(1);
  };
  assertChoice('Run'); select('Pass'); assertChoice('Pass');
  fireEvent.click(screen.getByRole('tab', { name: 'Scout' }));
  expect(screen.getByRole('heading', { name: 'Select a cohort to inspect the evidence.' })).toBeVisible();
  fireEvent.click(screen.getByRole('tab', { name: 'Decision Lab' }));
  expect(view().getByRole('radio', { name: 'Pass' })).toBeChecked(); assertChoice('Pass');
  fireEvent.click(view().getByRole('button', { name: 'Clear choice' }));
  expect(contrast()).toHaveTextContent('No call selected. Both options remain available for inspection.');
  expect(within(points()).queryByText('Your choice')).not.toBeInTheDocument();
  expect(within(points()).queryByText('Alternative')).not.toBeInTheDocument();
  expect(within(contrast()).getByRole('table')).toHaveTextContent(contrastBefore!);
  expect(JSON.stringify(fixture.decision)).toBe(serialized);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it.each([
  ['selected', ['+33.3 pp', '+0.600 EPA/play', '+100.0 pp']],
  ['bootstrap_comparison', ['+20.0 pp', '+0.556 EPA/play', '-11.1 pp']],
  ['bootstrap_many_games', ['0.0 pp', '0.000 EPA/play', '0.0 pp']],
] as const)('renders signed, zero and rounded server differences without a choice or ranking: %s', async (name, expected) => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures[name].decision)); setup(name); submit(); await view().findByRole('article');
  expect(values()).toEqual(expected);
  expect(within(contrast()).getAllByText('Descriptive estimate')).toHaveLength(3);
  expect(contrast()).toHaveTextContent('No call selected');
  expect(contrast()).toHaveTextContent('Pass − Run');
  expect(contrast()).toHaveTextContent('a displayed zero can hide a small difference');
  expect(contrast()).toHaveTextContent('Individual-candidate and selected-minus-league intervals');
  expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
});

it.each([
  ['empty_plain', ['Unavailable', 'Unavailable', 'Unavailable'], ['Run: selected cohort is empty.', 'Pass: selected cohort is empty.']],
  ['unobserved', ['+100.0 pp', 'Unavailable', 'Unavailable'], ['Run: no observed plays of this call.']],
  ['missing_epa_plain', ['-100.0 pp', 'Unavailable', 'Unavailable'], ['Run: EPA missing for every observed play of this call.', 'Pass: no observed plays of this call.']],
] as const)('retains explicit candidate-specific null reasons with a selected call: %s', async (name, expected, reasons) => {
  vi.mocked(fetch).mockResolvedValue(reply(fixtures[name].decision)); setup(name); select('Run'); submit(); await view().findByRole('article');
  expect(values()).toEqual(expected);
  const outcome = within(contrast()).getByRole('row', { name: /^EPA \/ observed play/ });
  for (const reason of reasons) expect(outcome).toHaveTextContent(reason);
  expect(contrast()).toHaveTextContent('Your choice: Run. Alternative: Pass.');
  expect(view().getByRole('heading', { name: 'No preferred call' })).toBeVisible();
  if (name === 'empty_plain') expect(view().getByRole('region', { name: 'Empty decision cohort' })).toBeVisible();
});

it.each([['team', 'ATL'], ['distance_min', '9'], ['score_min', '0'], ['compare_league', 'true'], ['bootstrap_seed', '7']] as const)(
  'clears choice and evidence on query edit %s, even when the old value is restored', async (name, value) => {
    vi.mocked(fetch).mockImplementation(async () => reply(fixtures.selected.decision)); setup(); select('Pass'); submit(); await view().findByRole('article');
    const original = (input(name) as HTMLInputElement).value;
    if (name === 'compare_league') fireEvent.click(input(name)); else edit(name, value);
    expect(view().queryByRole('article')).not.toBeInTheDocument();
    expect(view().getByRole('radio', { name: 'Pass' })).not.toBeChecked();
    expect(view().getByRole('button', { name: 'Clear choice' })).toBeDisabled();
    if (name === 'compare_league') fireEvent.click(input(name)); else edit(name, original);
    submit(); await view().findByRole('article');
    expect(contrast()).toHaveTextContent('No call selected');
    expect(fetch).toHaveBeenCalledTimes(2);
  });

it('uses the latest choice during a pending request without cancelling it, but rejects evidence after a query edit', async () => {
  let resolve!: (response: Response) => void;
  vi.mocked(fetch).mockImplementation(() => new Promise(yes => { resolve = yes; }));
  setup(); select('Run'); submit();
  const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
  select('Pass'); expect(signal.aborted).toBe(false); expect(fetch).toHaveBeenCalledTimes(1);
  await act(async () => resolve(reply(fixtures.selected.decision)));
  expect(contrast()).toHaveTextContent('Your choice: Pass. Alternative: Run.');
  submit(); const stale = resolve;
  const nextSignal = vi.mocked(fetch).mock.calls[1][1]!.signal!;
  edit('before_week', '2'); select('Run'); expect(nextSignal.aborted).toBe(true);
  await act(async () => stale(reply(fixtures.selected.decision)));
  expect(view().queryByRole('article')).not.toBeInTheDocument();
  expect(view().getByRole('radio', { name: 'Run' })).toBeChecked();
});

it('preserves the local choice on a same-query retry without retaining failed evidence or grading it', async () => {
  vi.mocked(fetch).mockResolvedValueOnce(reply(fixtures.selected.decision))
    .mockResolvedValueOnce(reply({ error: { code: 'report_busy', message: 'busy' } }, 503))
    .mockResolvedValueOnce(reply(fixtures.selected.decision));
  setup(); select('Run'); submit(); await view().findByRole('article'); submit();
  await view().findByRole('alert'); expect(view().queryByRole('article')).not.toBeInTheDocument();
  expect(view().getByRole('radio', { name: 'Run' })).toBeChecked();
  submit(); await view().findByRole('article'); expect(contrast()).toHaveTextContent('Your choice: Run. Alternative: Pass.');
  expect(fetch).toHaveBeenCalledTimes(3);
});

it.each(['direction', 'value', 'reason', 'interval', 'preference'])('rejects invalid server %s rather than rendering a misleading contrast', async kind => {
  const data = structuredClone(fixtures.selected.decision);
  if (kind === 'direction') Object.assign(data.comparison.descriptive_contrast, { direction: 'run_minus_pass' });
  if (kind === 'value') data.comparison.descriptive_contrast.metrics.epa_per_play.value = 99;
  if (kind === 'reason') Object.assign(data.comparison.descriptive_contrast.metrics.epa_per_play, { unavailable_candidates: { run: 'missing_epa' } });
  if (kind === 'interval') Object.assign(data.comparison.descriptive_contrast.uncertainty, { status: 'ok', interval: [0, 1] });
  if (kind === 'preference') Object.assign(data.comparison, { preferred_candidate: 'pass' });
  vi.mocked(fetch).mockResolvedValue(reply(data)); setup(); select('Pass'); submit();
  await view().findByRole('alert'); expect(view().queryByRole('article')).not.toBeInTheDocument();
  expect(view().getByRole('radio', { name: 'Pass' })).toBeChecked();
});
