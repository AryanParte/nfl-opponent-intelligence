import { afterEach, describe, expect, it, vi } from 'vitest';
import fixtures from './__fixtures__/decisions.json';
import { parseDecision, parseDecisionQuery, fetchDecisionDocument, DecisionQueryValidationError,
  type Decision, type DecisionDraft, type DecisionQuery } from './decision';

const cases = fixtures as unknown as Record<string, { query: DecisionQuery; decision: Decision }>;
const base = cases.selected.query;
const draft: DecisionDraft = { team: 'CAR', season: '2024', season_type: 'REG', before_week: '3', compare_league: false,
  yardline_min: '', yardline_max: '', score_min: '', score_max: '', period: '', clock_min: '', clock_max: '',
  bootstrap_repetitions: '', bootstrap_seed: '', down: '1', distance_min: '10', distance_max: '10', minimum_plays: '' };
const clone = <T,>(v: T): T => structuredClone(v);
afterEach(() => vi.unstubAllGlobals());

describe('Decision request contract', () => {
  it('uses the existing common query rules, inclusive exact distance and no role', () => {
    expect(parseDecisionQuery(draft)).toEqual(base);
    expect(parseDecisionQuery({ ...draft, down: '4', distance_min: '0', distance_max: '100', minimum_plays: '100000',
      yardline_min: '.5', score_max: '+0', period: 'OT', clock_min: '0', clock_max: '900',
      bootstrap_repetitions: '1000', bootstrap_seed: '4294967295' })).toMatchObject({
      down: 4, distance_min: 0, distance_max: 100, minimum_plays: 100000, yardline_min: .5, score_max: 0,
      period: 'OT', clock_min: 0, clock_max: 900, bootstrap_repetitions: 1000, bootstrap_seed: 4294967295 });
  });
  it.each([
    ['down', '0'], ['down', '5'], ['down', '1.5'], ['down', '1e0'], ['distance_min', '-1'], ['distance_max', '101'],
    ['distance_min', ''], ['distance_max', ''], ['distance_min', '11'], ['minimum_plays', '0'], ['minimum_plays', '100001'],
    ['team', 'car'], ['team', 'CÁR'], ['season', '1998'], ['before_week', '24'], ['season_type', 'ALL'],
    ['yardline_min', 'Infinity'], ['score_max', '1001'], ['period', 'Q5'], ['clock_max', '120'],
    ['bootstrap_repetitions', '199'], ['bootstrap_repetitions', '1001'], ['bootstrap_seed', '0'],
  ])('rejects invalid %s=%s with field identities', (key, value) => {
    try { parseDecisionQuery({ ...draft, [key]: value }); throw new Error('accepted'); }
    catch (error) { expect(error).toBeInstanceOf(DecisionQueryValidationError);
      const expected = key === 'clock_max' ? 'period' : key === 'bootstrap_seed' ? 'bootstrap_repetitions' : key;
      expect((error as DecisionQueryValidationError).fields).toContain(expected); }
  });
  it.each(['side', 'opponent', 'snapshot', 'path', 'model', 'play_family'])('rejects unsupported %s', key => {
    expect(() => parseDecisionQuery({ ...draft, [key]: 'unsupported' })).toThrow(DecisionQueryValidationError);
  });
  it.each([null, [], { ...draft, team: null }, { ...draft, compare_league: 'false' }, { ...draft, down: 1 }])('rejects malformed draft %#', value => {
    expect(() => parseDecisionQuery(value as unknown as DecisionDraft)).toThrow(DecisionQueryValidationError);
  });
});

describe('actual synthetic API Decision fixtures', () => {
  it.each(Object.entries(cases))('accepts %s without altering returned evidence', (_name, { decision, query }) => {
    const original = clone(decision);
    expect(parseDecision(decision, query)).toBe(decision);
    expect(decision).toEqual(original);
  });
  it('independently checks denominators and zero versus unavailable outcomes', () => {
    const d = parseDecision(cases.selected.decision, base);
    expect(d.population).toEqual({ plays: 3, games: 2 });
    expect(d.candidates[0]).toMatchObject({ plays: 1, frequency_denominator: 3, frequency: 1 / 3, epa_per_play: 0, success_rate: 0 });
    expect(d.candidates[1]).toMatchObject({ plays: 2, frequency: 2 / 3, epa_observations: 2, success_rate: 1 });
    expect(d.candidates[1].epa_per_play).toBeCloseTo(.6);
    expect(cases.missing_epa.decision.candidates[0]).toMatchObject({ frequency: 1, epa_per_play: null, success_rate: null,
      availability: { frequency: 'available', outcomes: 'missing_epa' } });
    expect(cases.unobserved.decision.candidates[0]).toMatchObject({ frequency: 0, epa_per_play: null,
      availability: { frequency: 'available', outcomes: 'unobserved_candidate' } });
    expect(cases.empty.decision.candidates[0]).toMatchObject({ frequency: null, availability: { frequency: 'empty_cohort', outcomes: 'empty_cohort' } });
  });
  it('keeps candidate frequency support at parent games and abstains with intervals', () => {
    const d = parseDecision(cases.bootstrap_comparison.decision, cases.bootstrap_comparison.query);
    expect(d.candidates[0].games).toBe(2);
    expect(d.uncertainty!.candidates[0].selected.frequency.support_games.selected).toBe(5);
    expect(d.uncertainty!.candidates[0].selected.epa_per_play.support_games.selected).toBe(2);
    for (const { decision } of Object.values(cases)) {
      expect(decision.comparison.preferred_candidate).toBeNull();
      expect(decision.comparison.reason).toBe('candidate_comparison_not_validated');
    }
    const statuses = new Set(Object.values(cases).flatMap(({ decision }) => decision.uncertainty?.candidates.flatMap(row =>
      [row.selected, row.baseline, row.difference].flatMap(pop => Object.values(pop ?? {}).map(item => item.status))) ?? []));
    expect([...statuses].sort()).toEqual(['degenerate_interval', 'insufficient_games', 'ok', 'too_few_valid_replicates', 'undefined_estimate']);
  });
  it('retains parent frequency support for an absent call and a baseline-only frame', () => {
    const absent = cases.bootstrap_unobserved;
    const d = parseDecision(absent.decision, absent.query);
    expect(d.candidates[0]).toMatchObject({ plays: 0, games: 0, frequency: 0 });
    expect(d.uncertainty!.candidates[0].selected.frequency).toMatchObject({ status: 'degenerate_interval',
      support_games: { selected: 5 }, valid_replicates: 200, interval: null });
    expect(d.uncertainty!.candidates[0].selected.epa_per_play.status).toBe('undefined_estimate');
    const empty = cases.bootstrap_empty_selected;
    const baselineOnly = parseDecision(empty.decision, empty.query);
    expect(baselineOnly.population.plays).toBe(0);
    expect(baselineOnly.uncertainty).toMatchObject({ resampling_games: 5, performed_repetitions: 200 });
  });
});

// Mutations model broken/mismatched wire responses, never fabricate live evidence.
// Path updates also exercise missing nested values without a large typed cast per case.
function setPath(target: unknown, path: string, replacement: unknown) {
  const keys = path.split('.');
  let parent = target as Record<string, unknown>;
  for (const key of keys.slice(0, -1)) parent = parent[key] as Record<string, unknown>;
  parent[keys.at(-1)!] = replacement;
}
const invalid: [string, string, unknown][] = [
  ['selected', 'contract_version', 2], ['selected', 'evidence_kind', 'prediction'],
  ['selected', 'cohort.team', 'ATL'], ['selected', 'cohort.side', 'defense'], ['selected', 'cohort.before_week_exclusive', 4],
  ['selected', 'cohort.season', 2025], ['selected', 'cohort.season_type', 'POST'], ['selected', 'cohort.down.minimum_inclusive', 2],
  ['selected', 'cohort.distance.maximum_inclusive', 11], ['selected', 'cohort.distance.missing_policy', 'impute'],
  ['selected', 'cohort.opponent', 'ATL'], ['context', 'cohort.clock.maximum_inclusive', 121],
  ['context', 'cohort.score_differential.minimum_inclusive', 0], ['context', 'cohort.field_position', null],
  ['overtime', 'cohort.period.maximum_inclusive', 5], ['selected', 'cohort.period', null],
  ['selected', 'source.sha256', 'bad'], ['selected', 'source.snapshot.decoded_csv.sha256', 'a'.repeat(64)],
  ['selected', 'source.snapshot.source.sha256', 'b'.repeat(64)], ['selected', 'source.snapshot.season', 2025],
  ['selected', 'source.snapshot.retrieved_at_utc', '2026-02-30T00:00:00Z'], ['selected', 'source.snapshot.source.asset_updated_at_utc', 'yesterday'],
  ['selected', 'source.snapshot.license', null], ['selected', 'source.label', ' '],
  ['selected', 'metric_context.interpretation', 'allowed'], ['selected', 'metric_context.success_condition', 'first_down'],
  ['selected', 'estimation_policy.minimum_plays_warning', 1], ['selected', 'population.games', 4],
  ['selected', 'candidates', []], ['selected', 'candidates.0.candidate', 'pass'], ['selected', 'candidates.1.mapping.equals', 0],
  ['selected', 'candidates.1.label', 'Pass recommendation'], ['selected', 'candidates.0.plays', -1],
  ['selected', 'candidates.0.plays', 1.5], ['selected', 'candidates.0.games', 0],
  ['selected', 'candidates.0.epa_observations', 2], ['selected', 'candidates.0.missing_epa', 1],
  ['selected', 'candidates.0.frequency_denominator', 1], ['selected', 'candidates.1.frequency', .5],
  ['selected', 'candidates.0.epa_per_play', null], ['selected', 'candidates.0.epa_per_play', Infinity],
  ['selected', 'candidates.0.success_rate', 1.1], ['selected', 'candidates.0.small_sample', false],
  ['selected', 'candidates.0.small_epa_sample', false], ['selected', 'candidates.0.availability.frequency', 'empty_cohort'],
  ['empty', 'candidates.0.frequency', 0], ['unobserved', 'candidates.0.availability.outcomes', 'missing_epa'],
  ['unobserved', 'candidates.0.frequency', -1e-10], ['missing_epa', 'candidates.0.frequency', 1 + 1e-10],
  ['missing_epa', 'candidates.0.success_rate', 0], ['missing_epa', 'candidates.0.availability.outcomes', 'available'],
  ['selected', 'comparison.preferred_candidate', 'pass'], ['selected', 'comparison.policy_version', 'winner_v1'],
  ['selected', 'comparison.reason', 'more_data_needed'], ['selected', 'comparison.status', 'available'],
  ['selected', 'comparison.opponent_evidence.status', 'available'],
  ['selected', 'comparison.descriptive_contrast.direction', 'run_minus_pass'],
  ['selected', 'comparison.descriptive_contrast.metrics.frequency_pp.value', 0],
  ['unobserved', 'comparison.descriptive_contrast.metrics.frequency_pp.value', 100 + 1e-10],
  ['selected', 'comparison.descriptive_contrast.metrics.epa_per_play.unit', 'percentage_points'],
  ['selected', 'comparison.descriptive_contrast.uncertainty.interval', { lower: 0, upper: 1 }],
  ['missing_epa', 'comparison.descriptive_contrast.metrics.epa_per_play.unavailable_candidates', {}],
  ['selected', 'data_quality.input_rows', 0], ['selected', 'data_quality.eligible_rows_outside_cohort', 0],
  ['selected', 'data_quality.excluded_rows_by_reason', { invalid: -1 }],
  ['selected', 'data_quality.team_plays_before_context_filters', 3],
  ['selected', 'data_quality.down_filter.missing_down', 1], ['selected', 'data_quality.distance_filter.plays_before_filter', 99],
  ['selected', 'data_quality.filter_order', ['distance', 'down']], ['context', 'data_quality.clock_filter.outside_range', 0],
  ['selected', 'league_comparison', null], ['league', 'league_comparison', null],
  ['league', 'league_comparison.population.excluded_team', 'ATL'], ['league', 'league_comparison.population.teams', ['CAR']],
  ['league', 'league_comparison.population.shared_games_with_selected', 99], ['league', 'league_comparison.population.weighting', 'teams'],
  ['league', 'league_comparison.cohort.distance.minimum_inclusive', 0],
  ['league', 'league_comparison.data_quality.excluded_selected_team_rows', 0],
  ['league', 'league_comparison.candidates.1.coverage.teams', ['GB']],
  ['league', 'league_comparison.candidates.0.difference.epa_per_play', 0],
  ['league', 'league_comparison.candidates.1.difference.epa_per_play', 2.4],
  ['league', 'league_comparison.difference_units.frequency_pp', 'proportion'],
  ['selected', 'uncertainty', null], ['bootstrap_selected', 'uncertainty', null],
  ['bootstrap_selected', 'uncertainty.method', 'normal'], ['bootstrap_selected', 'uncertainty.seed', 7],
  ['bootstrap_comparison', 'uncertainty.resampling_games', 10], ['bootstrap_comparison', 'uncertainty.shared_game_weights', false],
  ['bootstrap_comparison', 'uncertainty.candidates.0.selected.frequency.support_games.selected', 2],
  ['bootstrap_comparison', 'uncertainty.candidates.0.selected.epa_per_play.support_games.selected', 5],
  ['bootstrap_comparison', 'uncertainty.candidates.0.selected.epa_per_play.status', 'ok'],
  ['bootstrap_comparison', 'uncertainty.candidates.0.selected.frequency.interval.lower', -1],
  ['bootstrap_comparison', 'uncertainty.candidates.0.selected.frequency.valid_replicates', 201],
  ['bootstrap_comparison', 'uncertainty.candidates.0.difference.frequency_pp.unit', 'proportion'],
  ['bootstrap_comparison', 'uncertainty.candidates.0.difference.epa_per_play.support_games.selected', 1],
  ['bootstrap_sparse_draws', 'uncertainty.candidates.0.selected.epa_per_play.status', 'degenerate_interval'],
  ['bootstrap_empty', 'uncertainty.performed_repetitions', 200], ['bootstrap_empty', 'uncertainty.candidates.0.selected.frequency.interval', { lower: 0, upper: 1 }],
  ['selected', 'warnings', [3]], ['bootstrap_selected', 'uncertainty.warnings', null],
];
it.each(invalid)('rejects %s mutation %s=%j', (name, path, replacement) => {
  const { decision, query } = clone(cases[name]);
  setPath(decision, path, replacement);
  expect(() => parseDecision(decision, query)).toThrow('incompatible Decision evidence');
});
it.each([null, [], {}, 'bad'])('rejects malformed envelope %#', value => {
  expect(() => parseDecision(value, base)).toThrow('incompatible Decision evidence');
});

describe('Decision fetch boundary', () => {
  const response = (text: string, type = 'application/json') => new Response(text, { headers: { 'Content-Type': type } });
  it('uses only the fixed local route, forwards cancellation, and preserves original JSON text', async () => {
    const json = JSON.stringify(cases.selected.decision).replace('"contract_version":1', '"contract_version":1.000');
    const fetcher = vi.fn().mockResolvedValue(response(json)); vi.stubGlobal('fetch', fetcher);
    const signal = new AbortController().signal;
    const result = await fetchDecisionDocument(base, signal);
    expect(result.json).toBe(json);
    expect(result.decision).toEqual(cases.selected.decision);
    const [url, options] = fetcher.mock.calls[0];
    expect(new URL(url, 'http://localhost').pathname).toBe('/api/v1/decision');
    expect(Object.fromEntries(new URL(url, 'http://localhost').searchParams)).toEqual(
      Object.fromEntries(Object.entries(base).map(([k, v]) => [k, String(v)])));
    expect(options).toEqual({ signal, credentials: 'omit', cache: 'no-store', redirect: 'error' });
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('freezes the submitted query before awaiting, including explicit zero and false', async () => {
    const query = clone(cases.zero_clock.query);
    vi.stubGlobal('fetch', vi.fn().mockImplementation(async () => { query.clock_max = 900; return response(JSON.stringify(cases.zero_clock.decision)); }));
    expect((await fetchDecisionDocument(query, new AbortController().signal)).decision).toEqual(cases.zero_clock.decision);
    const url = new URL(vi.mocked(fetch).mock.calls[0][0] as string, 'http://localhost');
    expect(url.searchParams.get('clock_max')).toBe('0');
    expect(url.searchParams.get('compare_league')).toBe('false');
  });
  it.each([ { ...base, snapshot: '/tmp/data' }, { ...base, side: 'offense' }, { ...base, down: '1' },
    { ...base, compare_league: 'false' }, { ...base, bootstrap_repetitions: 1001 }, { ...base, minimum_plays: null },
    { ...base, season: NaN }, { ...base, down: 1.1 } ])('rejects runtime query %# before network', async value => {
    const fetcher = vi.fn(); vi.stubGlobal('fetch', fetcher);
    await expect(fetchDecisionDocument(value as DecisionQuery, new AbortController().signal)).rejects.toThrow(DecisionQueryValidationError);
    expect(fetcher).not.toHaveBeenCalled();
  });
  it.each(['text/html', 'application/problem+json', ''])('rejects unexpected content type %s', async type => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response('private raw HTML', type)));
    await expect(fetchDecisionDocument(base, new AbortController().signal)).rejects.toThrow('did not return JSON');
  });
  it('sanitizes invalid JSON and does not display raw response contents', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response('private raw JSON')));
    await expect(fetchDecisionDocument(base, new AbortController().signal)).rejects.toThrow(/^The API returned invalid JSON/);
  });
  it('handles a non-JSON HTTP error without exposing the body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('private server traceback', { status: 500 })));
    await expect(fetchDecisionDocument(base, new AbortController().signal)).rejects.toThrow('Decision request failed (HTTP 500)');
  });
  it.each(['invalid_query', 'duplicate_parameter', 'season_unavailable', 'context_unavailable', 'report_busy', 'snapshot_not_ready',
    'query_too_long', 'internal_error', 'constructor', '<script>'])('handles HTTP errors safely without retries: %s', async code => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code, message: 'private path /secrets' } }), { status: 503 }));
    vi.stubGlobal('fetch', fetcher);
    await expect(fetchDecisionDocument(base, new AbortController().signal)).rejects.not.toThrow(/private|secrets|script|constructor/);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it.each([new DOMException('Cancelled', 'AbortError'), new TypeError('Network failure')])('preserves transport/cancellation errors %# without fallback', async error => {
    const fetcher = vi.fn().mockRejectedValue(error); vi.stubGlobal('fetch', fetcher);
    await expect(fetchDecisionDocument(base, new AbortController().signal)).rejects.toBe(error);
    expect(fetcher).toHaveBeenCalledTimes(1);
  });
  it('rejects a valid response for a different situation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(JSON.stringify(cases.selected.decision))));
    await expect(fetchDecisionDocument({ ...base, down: 2 }, new AbortController().signal)).rejects.toThrow('incompatible Decision evidence');
  });
});
