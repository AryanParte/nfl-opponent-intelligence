/** Decision contract v1: accept descriptive evidence, never choose or estimate a call. */
import { object, exact, count, finite, rate, strings, matches, validSource, type EvidenceSource } from './contract';
import { parseQuery, QueryValidationError, requestedContexts, contextBefore, contextKeys, sameContext,
  type Query, type Draft, type Contexts } from './report';
import { intervalRow, validUncertaintyMetadata, type IntervalSummary, type UncertaintyMetadata } from './uncertainty';

export type DecisionQuery = Omit<Query, 'side'> & {
  down: number; distance_min: number; distance_max: number; minimum_plays?: number;
};
export type DecisionDraft = Omit<Draft, 'side'> & {
  down: string; distance_min: string; distance_max: string; minimum_plays: string;
};
export class DecisionQueryValidationError extends Error {
  constructor(message: string, readonly fields: readonly (keyof DecisionDraft)[]) {
    super(message); this.name = 'DecisionQueryValidationError';
  }
}
const commonKeys = ['team', 'season', 'before_week', 'season_type', 'compare_league', 'yardline_min', 'yardline_max',
  'score_min', 'score_max', 'period', 'clock_min', 'clock_max', 'bootstrap_repetitions', 'bootstrap_seed'] as const;
const decisionKeys = ['down', 'distance_min', 'distance_max', 'minimum_plays'] as const;
const queryKeys = [...commonKeys, ...decisionKeys];

export function parseDecisionQuery(draft: DecisionDraft): DecisionQuery {
  if (!object(draft) || !exact(draft, queryKeys)) {
    throw new DecisionQueryValidationError('Use only the supported Decision fields.', []);
  }
  const bad = queryKeys.filter(key => typeof draft[key] !== (key === 'compare_league' ? 'boolean' : 'string'));
  if (bad.length) throw new DecisionQueryValidationError('Check the Decision field types.', bad);
  let common: Query;
  try { common = parseQuery({ ...Object.fromEntries(commonKeys.map(key => [key, draft[key]])), side: 'offense' } as Draft); }
  catch (error) {
    if (error instanceof QueryValidationError) throw new DecisionQueryValidationError(error.message,
      error.fields.filter((field): field is Exclude<keyof Draft, 'side'> => field !== 'side'));
    throw error;
  }
  const integer = (key: typeof decisionKeys[number], min: number, max: number) => {
    const raw = draft[key].trim();
    if (!/^\d+$/.test(raw) || !Number.isSafeInteger(Number(raw)) || Number(raw) < min || Number(raw) > max) {
      throw new DecisionQueryValidationError(`${key} must be a whole number from ${min} to ${max}.`, [key]);
    }
    return Number(raw);
  };
  const down = integer('down', 1, 4), lower = integer('distance_min', 0, 100), upper = integer('distance_max', 0, 100);
  if (lower > upper) throw new DecisionQueryValidationError('Minimum distance must not exceed maximum distance.', ['distance_min', 'distance_max']);
  const { side: _side, ...query } = common;
  return { ...query, down, distance_min: lower, distance_max: upper,
    ...(draft.minimum_plays.trim() === '' ? {} : { minimum_plays: integer('minimum_plays', 1, 100000) }) };
}

/** Copy and validate runtime input before awaiting a response; TS types are erased. */
function checkedQuery(query: DecisionQuery): DecisionQuery {
  if (!object(query) || Object.keys(query).some(key => !queryKeys.includes(key as keyof DecisionQuery))) {
    throw new DecisionQueryValidationError('Use only the supported Decision fields.', []);
  }
  const stringKeys = ['team', 'season_type', 'period'];
  const draft: Record<string, unknown> = {};
  for (const key of queryKeys) {
    const value = query[key];
    if (value !== undefined && typeof value !== (key === 'compare_league' ? 'boolean' : stringKeys.includes(key) ? 'string' : 'number')) {
      throw new DecisionQueryValidationError('Check the Decision field types.', [key]);
    }
    draft[key] = key === 'compare_league' ? value : value === undefined ? '' : String(value);
  }
  return parseDecisionQuery(draft as DecisionDraft);
}

export type Call = 'run' | 'pass';
type OutcomeState = 'available' | 'empty_cohort' | 'unobserved_candidate' | 'missing_epa';
type Population = { plays: number; games: number };
export type Candidate = Population & {
  candidate: Call; label: string; mapping: { source_field: 'qb_dropback'; equals: 0 | 1 };
  epa_observations: number; missing_epa: number; epa_per_play: number | null; success_rate: number | null;
  small_sample: boolean; small_epa_sample: boolean; frequency: number | null; frequency_denominator: number;
  availability: { frequency: 'available' | 'empty_cohort'; outcomes: OutcomeState };
};
type Metric = 'frequency_pp' | 'epa_per_play' | 'success_rate_pp';
type Difference = Record<Metric, number | null>;
type Bounds = { field: 'down' | 'yards_to_go'; minimum_inclusive: number; maximum_inclusive: number; missing_policy: 'reject_at_ingestion' };
type Cohort = { team: string; side: 'offense'; season: number; season_type: Query['season_type']; before_week_exclusive: number;
  down: Bounds; distance: Bounds } & Contexts;
type FilterName = typeof contextKeys[number] | 'down' | 'distance';
type Ledger = { plays_before_filter: number; plays_after_filter: number } & Record<string, number>;
type Quality = { filter_order: FilterName[] } & Partial<Record<`${FilterName}_filter`, Ledger>>;
type SelectedQuality = Quality & { input_rows: number; eligible_rows_all_teams: number; excluded_rows_by_reason: Record<string, number>;
  eligible_rows_outside_cohort: number; eligible_rows_same_season_type_before_week: number; team_plays_before_context_filters: number };
type BaselineCandidate = Candidate & { coverage: { teams: string[]; team_count: number; shared_games_with_selected_candidate: number }; difference: Difference };
type LeagueComparison = {
  cohort: Omit<Cohort, 'team'>;
  population: Population & { scope: 'available_source_only'; side: 'offense'; team_field: 'posteam'; excluded_team: string;
    weighting: 'pooled_plays'; teams: string[]; team_count: number; shared_games_with_selected: number };
  difference_convention: 'selected_minus_baseline'; difference_units: Record<Metric, string>;
  data_quality: Quality & { eligible_rows_same_season_type_before_week: number; excluded_selected_team_rows: number;
    plays_before_context_filters: number; plays_after_context_filters: number };
  candidates: [BaselineCandidate, BaselineCandidate]; warnings: string[];
};
type CandidateIntervals = { candidate: Call; selected: Record<'frequency' | 'success_rate' | 'epa_per_play', IntervalSummary>;
  baseline?: Record<'frequency' | 'success_rate' | 'epa_per_play', IntervalSummary>; difference?: Record<Metric, IntervalSummary> };
export type Decision = {
  contract_version: 1; evidence_kind: 'descriptive_observed_calls'; source: EvidenceSource; cohort: Cohort;
  metric_context: { perspective: 'offense'; interpretation: 'produced'; success_condition: 'epa > 0'; frequency_unit: 'proportion' };
  estimation_policy: { frequency_minimum_parent_plays: 1; outcome_minimum_epa_observations: 1; minimum_plays_warning: number };
  population: Population; data_quality: SelectedQuality; candidates: [Candidate, Candidate]; warnings: string[];
  comparison: { status: 'insufficient_evidence'; preferred_candidate: null; reason: 'candidate_comparison_not_validated'; policy_version: 'descriptive_only_v1';
    descriptive_contrast: { population: 'selected_offense'; direction: 'pass_minus_run';
      metrics: Record<Metric, { value: number | null; unit: string; status: 'available' | 'unavailable'; unavailable_candidates: Partial<Record<Call, OutcomeState>> }>;
      uncertainty: { status: 'not_implemented'; interval: null } };
    opponent_evidence: { status: 'deferred'; reason: 'opponent_conditioning_not_validated' } };
  league_comparison?: LeagueComparison;
  uncertainty?: UncertaintyMetadata & { candidates: [CandidateIntervals, CandidateIntervals] };
};
export type DecisionDocument = { readonly decision: Decision; readonly json: string };
const calls = ['run', 'pass'] as const;
const labels = ['Run (non-dropback)', 'Pass (dropback, including sacks/scrambles)'];
const metricSpecs = [['frequency_pp', 'frequency', 100, 'percentage_points'],
  ['epa_per_play', 'epa_per_play', 1, 'expected_points_per_observed_play'],
  ['success_rate_pp', 'success_rate', 100, 'percentage_points']] as const;
const units = Object.fromEntries(metricSpecs.map(([name, , , unit]) => [name, unit]));
const close = (a: unknown, b: number) => finite(a) && Math.abs(a - b) <= 1e-9;
const population = (v: unknown): v is Population & Record<string, unknown> => object(v) && count(v.plays) && count(v.games)
  && v.games <= v.plays && (v.games === 0) === (v.plays === 0);

function candidates(value: unknown, parent: Population, minimum: number): value is [Candidate, Candidate] {
  if (!Array.isArray(value) || value.length !== 2) return false;
  for (const [i, c] of value.entries()) {
    if (!population(c) || !object(c) || c.candidate !== calls[i] || c.label !== labels[i]
        || !matches(c.mapping, { source_field: 'qb_dropback', equals: i })
        || !count(c.epa_observations) || !count(c.missing_epa) || c.epa_observations + c.missing_epa !== c.plays
        || c.games > parent.games || c.frequency_denominator !== parent.plays
        || !rate(c.frequency) || (parent.plays ? !close(c.frequency, c.plays / parent.plays) : c.frequency !== null)
        || (c.epa_observations ? !finite(c.epa_per_play) || !finite(c.success_rate) : c.epa_per_play !== null || c.success_rate !== null)
        || !rate(c.success_rate) || c.small_sample !== (c.plays < minimum) || c.small_epa_sample !== (c.epa_observations < minimum)
        || !matches(c.availability, { frequency: parent.plays ? 'available' : 'empty_cohort',
          outcomes: !parent.plays ? 'empty_cohort' : !c.plays ? 'unobserved_candidate' : !c.epa_observations ? 'missing_epa' : 'available' })) return false;
  }
  // Calls partition plays. A game may contain both calls, so game counts overlap.
  return value[0].plays + value[1].plays === parent.plays && value[0].games + value[1].games >= parent.games;
}

function qualityBefore(q: unknown, plays: number, contexts: Contexts, prefixKeys: string[]): number | undefined {
  if (!object(q)) return undefined;
  const active = contextKeys.filter(key => contexts[key]);
  const order = [...active, 'down', 'distance'];
  if (!exact(q, [...prefixKeys, 'filter_order', ...order.map(key => `${key}_filter`)])
      || !strings(q.filter_order) || q.filter_order.join(',') !== order.join(',')) return undefined;
  let after = plays;
  for (const [name, missing] of [['distance', 'missing_yards_to_go'], ['down', 'missing_down']]) {
    const v = q[`${name}_filter`];
    if (!object(v) || !exact(v, ['plays_before_filter', 'plays_after_filter', missing, 'outside_range'])
        || !count(v.plays_before_filter) || !count(v.outside_range) || v[missing] !== 0
        || v.plays_after_filter !== after || v.plays_before_filter !== after + v.outside_range) return undefined;
    after = v.plays_before_filter;
  }
  return contextBefore({ ...q, filter_order: active }, after, contexts, true);
}

function declaredDifference(value: unknown, left: Candidate, right: Candidate): boolean {
  return object(value) && exact(value, metricSpecs.map(([name]) => name)) && metricSpecs.every(([name, field, scale]) =>
    left[field] === null || right[field] === null ? value[name] === null
      : close(value[name], (left[field] - right[field]) * scale) && (scale === 1 || Math.abs(value[name] as number) <= 100));
}

function abstention(value: unknown, selected: [Candidate, Candidate]): boolean {
  if (!object(value) || !exact(value, ['status', 'preferred_candidate', 'reason', 'policy_version', 'descriptive_contrast', 'opponent_evidence'])
      || value.status !== 'insufficient_evidence' || value.preferred_candidate !== null
      || value.reason !== 'candidate_comparison_not_validated' || value.policy_version !== 'descriptive_only_v1'
      || !matches(value.opponent_evidence, { status: 'deferred', reason: 'opponent_conditioning_not_validated' })) return false;
  const c = value.descriptive_contrast;
  if (!object(c) || !exact(c, ['population', 'direction', 'metrics', 'uncertainty']) || c.population !== 'selected_offense'
      || c.direction !== 'pass_minus_run' || !matches(c.uncertainty, { status: 'not_implemented', interval: null })
      || !object(c.metrics) || !exact(c.metrics, metricSpecs.map(([name]) => name))) return false;
  const values: Record<string, unknown> = {};
  for (const [name, field, , unit] of metricSpecs) {
    const item = c.metrics[name];
    const unavailable = Object.fromEntries(selected.filter(call => call[field] === null)
      .map(call => [call.candidate, call.availability[field === 'frequency' ? 'frequency' : 'outcomes']]));
    if (!object(item) || !exact(item, ['value', 'unit', 'status', 'unavailable_candidates']) || item.unit !== unit
        || item.status !== (Object.keys(unavailable).length ? 'unavailable' : 'available')
        || !matches(item.unavailable_candidates, unavailable)) return false;
    values[name] = item.value;
  }
  return declaredDifference(values, selected[1], selected[0]);
}

function teamCoverage(v: Record<string, unknown>, plays: number, excluded: string): v is Record<string, unknown> & { teams: string[] } {
  return strings(v.teams) && v.teams.every(t => /^[A-Z]{2,3}$/.test(t) && t !== excluded)
    && new Set(v.teams).size === v.teams.length && v.team_count === v.teams.length
    && v.teams.length <= plays && (v.teams.length === 0) === (plays === 0);
}

function league(value: unknown, d: Decision, query: DecisionQuery): value is LeagueComparison {
  if (!object(value) || !population(value.population) || !object(value.population) || !object(value.cohort)
      || !candidates(value.candidates, value.population, query.minimum_plays ?? 30) || !strings(value.warnings)
      || value.difference_convention !== 'selected_minus_baseline' || !matches(value.difference_units, units)) return false;
  const p = value.population, q = value.data_quality;
  const { team: _team, ...cohort } = d.cohort;
  if (!exact(value.cohort, Object.keys(cohort)) || Object.entries(cohort).some(([k, v]) =>
    object(v) ? !matches((value.cohort as Record<string, unknown>)[k], v) : (value.cohort as Record<string, unknown>)[k] !== v)) return false;
  const before = qualityBefore(q, p.plays, d.cohort,
    ['eligible_rows_same_season_type_before_week', 'excluded_selected_team_rows', 'plays_before_context_filters', 'plays_after_context_filters']);
  if (p.scope !== 'available_source_only' || p.side !== 'offense' || p.team_field !== 'posteam'
      || p.excluded_team !== query.team || p.weighting !== 'pooled_plays' || !teamCoverage(p, p.plays, query.team)
      || !count(p.shared_games_with_selected) || p.shared_games_with_selected > Math.min(p.games, d.population.games)
      || before === undefined || !object(q) || q.plays_before_context_filters !== before || q.plays_after_context_filters !== p.plays
      || q.excluded_selected_team_rows !== d.data_quality.team_plays_before_context_filters
      || q.eligible_rows_same_season_type_before_week !== d.data_quality.eligible_rows_same_season_type_before_week
      || q.eligible_rows_same_season_type_before_week !== before + d.data_quality.team_plays_before_context_filters) return false;
  const teams = new Set<string>();
  for (const [i, c] of value.candidates.entries()) {
    const raw = c as Candidate & Record<string, unknown>, coverage = raw.coverage;
    if (!object(coverage) || !teamCoverage(coverage, c.plays, query.team)
        || !count(coverage.shared_games_with_selected_candidate)
        || coverage.shared_games_with_selected_candidate > Math.min(c.games, d.candidates[i].games, p.shared_games_with_selected)
        || !declaredDifference(raw.difference, d.candidates[i], c)) return false;
    coverage.teams.forEach(team => teams.add(team));
  }
  return teams.size === p.teams.length && p.teams.every(team => teams.has(team));
}

function uncertainty(value: unknown, d: Decision, query: DecisionQuery): boolean {
  const b = d.league_comparison;
  const games = d.population.games + (b ? b.population.games - b.population.shared_games_with_selected : 0);
  if (!validUncertaintyMetadata(value, query, games, !!b, ['candidates'])
      || !Array.isArray(value.candidates) || value.candidates.length !== 2) return false;
  for (const [i, row] of value.candidates.entries()) {
    if (!object(row) || row.candidate !== calls[i] || !intervalRow(row,
      { ...d.candidates[i], frequency_games: d.population.games },
      b ? { ...b.candidates[i], frequency_games: b.population.games } : undefined,
      value.performed_repetitions, games, ['candidate'], 'frequency')) return false;
  }
  // Both frequencies share the same parent denominator and defined draws.
  const rows = value.candidates as CandidateIntervals[];
  return (['selected', 'baseline', 'difference'] as const).every(key => {
    const left = rows[0][key], right = rows[1][key];
    if (!left || !right) return left === right;
    const metric = key === 'difference' ? 'frequency_pp' : 'frequency';
    return (left as Record<string, IntervalSummary>)[metric].valid_replicates === (right as Record<string, IntervalSummary>)[metric].valid_replicates;
  });
}

export function parseDecision(value: unknown, input: DecisionQuery): Decision {
  const query = checkedQuery(input);
  const fail = (): never => { throw new Error('The API returned incompatible Decision evidence. No measurements were displayed.'); };
  if (!object(value) || value.contract_version !== 1 || value.evidence_kind !== 'descriptive_observed_calls'
      || !validSource(value.source, query.season) || !object(value.cohort) || !population(value.population)
      || !candidates(value.candidates, value.population, query.minimum_plays ?? 30) || !strings(value.warnings)) return fail();
  const contexts = requestedContexts({ ...query, side: 'offense' });
  const c = value.cohort;
  if (!exact(c, ['team', 'side', 'season', 'season_type', 'before_week_exclusive', 'down', 'distance', ...contextKeys.filter(key => contexts[key])])
      || c.team !== query.team || c.side !== 'offense' || c.season !== query.season || c.season_type !== query.season_type
      || c.before_week_exclusive !== query.before_week || contextKeys.some(key => !sameContext(c[key], contexts[key]))
      || !matches(c.down, { field: 'down', minimum_inclusive: query.down, maximum_inclusive: query.down, missing_policy: 'reject_at_ingestion' })
      || !matches(c.distance, { field: 'yards_to_go', minimum_inclusive: query.distance_min, maximum_inclusive: query.distance_max, missing_policy: 'reject_at_ingestion' })
      || !matches(value.metric_context, { perspective: 'offense', interpretation: 'produced', success_condition: 'epa > 0', frequency_unit: 'proportion' })
      || !matches(value.estimation_policy, { frequency_minimum_parent_plays: 1, outcome_minimum_epa_observations: 1, minimum_plays_warning: query.minimum_plays ?? 30 })) return fail();
  const q = value.data_quality;
  const counts = ['input_rows', 'eligible_rows_all_teams', 'eligible_rows_outside_cohort', 'eligible_rows_same_season_type_before_week', 'team_plays_before_context_filters'];
  const before = qualityBefore(q, value.population.plays, contexts, [...counts, 'excluded_rows_by_reason']);
  if (!object(q) || before === undefined || counts.some(key => !count(q[key])) || !object(q.excluded_rows_by_reason)
      || !Object.values(q.excluded_rows_by_reason).every(count) || q.team_plays_before_context_filters !== before
      || q.input_rows !== (q.eligible_rows_all_teams as number) + (Object.values(q.excluded_rows_by_reason) as number[]).reduce((sum, n) => sum + n, 0)
      || q.eligible_rows_all_teams !== (q.eligible_rows_outside_cohort as number) + value.population.plays
      || before > (q.eligible_rows_same_season_type_before_week as number)
      || (q.eligible_rows_same_season_type_before_week as number) > (q.eligible_rows_all_teams as number)
      || !abstention(value.comparison, value.candidates)) return fail();
  const d = value as unknown as Decision;
  if (query.compare_league ? !league(value.league_comparison, d, query) : 'league_comparison' in value) return fail();
  if (query.bootstrap_repetitions !== undefined ? !uncertainty(value.uncertainty, d, query) : 'uncertainty' in value) return fail();
  return d;
}

const errorMessages: Record<string, string> = {
  invalid_query: 'The API rejected the situation. Check the Decision fields.',
  duplicate_parameter: 'The API rejected duplicate query fields.',
  season_unavailable: 'That season is not in the configured snapshot.',
  context_unavailable: 'The configured snapshot lacks a requested context column. Clear that filter or check the snapshot.',
  report_busy: 'Another report is being built. Wait a moment, then try again.',
  snapshot_not_ready: 'The API snapshot is not ready. Check startup.',
  query_too_long: 'The Decision query exceeds the API limit.',
};
export async function fetchDecisionDocument(input: DecisionQuery, signal: AbortSignal): Promise<DecisionDocument> {
  const query = checkedQuery(input);
  const params = new URLSearchParams(Object.entries(query).map(([key, value]) => [key, String(value)]));
  const response = await fetch(`/api/v1/decision?${params}`, { signal, credentials: 'omit', cache: 'no-store', redirect: 'error' });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const code = object(body) && object(body.error) ? body.error.code : null;
    throw new Error(typeof code === 'string' && Object.hasOwn(errorMessages, code) ? errorMessages[code]
      : `Decision request failed (HTTP ${response.status}). Check the local API and retry.`);
  }
  if (response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'application/json') {
    throw new Error('The local API did not return JSON. Check that the API and viewer are running.');
  }
  const json = await response.text();
  let value: unknown;
  try { value = JSON.parse(json); } catch { throw new Error('The API returned invalid JSON. No Decision evidence was displayed.'); }
  return { decision: parseDecision(value, query), json };
}
