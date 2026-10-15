/** Validate only this view's consumed contract; do not recompute analytics. */
import { validUncertainty, type Uncertainty } from './uncertainty';
export const PERIODS = ['Q1', 'Q2', 'Q3', 'Q4', 'OT'] as const;
export type Query = {
  team: string; season: number; before_week: number;
  side: 'offense' | 'defense'; season_type: 'REG' | 'POST';
  compare_league: boolean;
  yardline_min?: number; yardline_max?: number;
  score_min?: number; score_max?: number;
  period?: typeof PERIODS[number]; clock_min?: number; clock_max?: number;
  bootstrap_repetitions?: number; bootstrap_seed?: number;
};
export type Draft = { [Key in Exclude<keyof Query, 'compare_league'>]: string } & { compare_league: boolean };
export type FieldPosition = { field: 'yardline_100'; minimum_inclusive: number; maximum_inclusive: number;
  perspective: 'offense'; missing_policy: 'exclude' };
export type FieldPositionCounts = { plays_before_filter: number; missing_yardline_100: number;
  outside_range: number; plays_after_filter: number };
export type ScoreContext = { field: 'score_differential'; minimum_inclusive: number | null; maximum_inclusive: number | null;
  perspective: 'offense'; missing_policy: 'exclude' };
export type ScoreCounts = { plays_before_filter: number; missing_score_differential: number;
  outside_range: number; plays_after_filter: number };
export type PeriodContext = { field: 'qtr'; label: NonNullable<Query['period']>; minimum_inclusive: number;
  maximum_inclusive: number | null; missing_policy: 'exclude' };
export type ClockContext = { field: 'quarter_seconds_remaining'; minimum_inclusive: number; maximum_inclusive: number;
  unit: 'seconds'; timing: 'pre_play'; missing_policy: 'exclude' };
type PeriodCounts = { plays_before_filter: number; missing_qtr: number; outside_period: number; plays_after_filter: number };
type ClockCounts = { plays_before_filter: number; missing_quarter_seconds_remaining: number; outside_range: number; plays_after_filter: number };
type Contexts = { field_position?: FieldPosition; score_differential?: ScoreContext; period?: PeriodContext; clock?: ClockContext };
const contextKeys = ['field_position', 'score_differential', 'period', 'clock'] as const;
const contextCount = (contexts: Contexts) => contextKeys.filter(key => contexts[key] !== undefined).length;
type SelectedQuality = { input_rows: number; eligible_rows_all_teams: number; eligible_rows_outside_cohort: number;
  excluded_rows_by_reason: Record<string, number>; field_position_filter?: FieldPositionCounts;
  score_differential_filter?: ScoreCounts; period_filter?: PeriodCounts; clock_filter?: ClockCounts; filter_order?: string[] };
export type Metrics = {
  plays: number; games: number; dropbacks: number; designed_runs: number;
  epa_observations: number; missing_epa: number;
  dropback_rate: number | null; success_rate: number | null; epa_per_play: number | null;
  small_sample: boolean; small_epa_sample: boolean;
};
export type Report = {
  schema_version: 2;
  cohort: { team: string; season: number; before_week_exclusive: number;
    side: Query['side']; season_type: Query['season_type']; minimum_plays_warning: number } & Contexts;
  data_quality: SelectedQuality;
  source: { label: string; sha256: string; snapshot: {
    retrieved_at_utc: string; archive: { sha256: string };
    source: { asset_updated_at_utc: string };
    license: { attribution: string; identifier: string };
  } };
  overall: Metrics;
  situations: (Metrics & { down: number; distance: 'short' | 'medium' | 'long' })[];
  warnings: string[];
  league_comparison?: Comparison;
  uncertainty?: Uncertainty;
};
export type Difference = { dropback_rate_pp: number | null; success_rate_pp: number | null; epa_per_play: number | null };
/** Keep the validated decoded response text: JS reserialization changes numeric lexemes. */
export type ReportDocument = { readonly report: Report; readonly json: string };
export type Comparison = {
  population: { scope: 'available_source_only'; side: Query['side']; excluded_team: string;
    team_field: 'posteam' | 'defteam'; teams: string[]; team_count: number;
    weighting: 'pooled_plays'; shared_games_with_selected: number };
  data_quality: { eligible_rows_same_season_type_before_week: number; excluded_selected_team_rows: number;
    plays_before_context_filters: number; plays_after_context_filters: number; filter_order: string[];
    field_position_filter?: FieldPositionCounts; score_differential_filter?: ScoreCounts;
    period_filter?: PeriodCounts; clock_filter?: ClockCounts };
  overall: Metrics;
  overall_difference: Difference;
  situations: { down: number; distance: Report['situations'][number]['distance']; baseline: Metrics; difference: Difference }[];
  warnings: string[];
};

export function parseQuery(draft: Draft): Query {
  const whole = (value: string, min: number, max: number) =>
    /^\d+$/.test(value) && Number(value) >= min && Number(value) <= max;
  if (!/^[A-Z]{2,3}$/.test(draft.team) || !whole(draft.season, 1999, 9999)
      || !whole(draft.before_week, 1, 23) || !['offense', 'defense'].includes(draft.side)
      || !['REG', 'POST'].includes(draft.season_type) || typeof draft.compare_league !== 'boolean') {
    throw new Error('Use a 2–3 letter uppercase team code, season 1999–9999 and cutoff week 1–23. Check the role and season type.');
  }
  const bound = (text: string): number | undefined => {
    const value = text.trim();
    if (value === '') return undefined;
    if (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(value) || !Number.isFinite(Number(value)) || Number(value) > 100) {
      throw new Error('Field-position bounds must be decimals from 0 to 100, or blank. Use a dot for decimals.');
    }
    return Number(value);
  };
  const lower = bound(draft.yardline_min), upper = bound(draft.yardline_max);
  if ((lower ?? 0) > (upper ?? 100)) throw new Error('Minimum yards to goal must not exceed maximum yards to goal.');
  const scoreBound = (text: string): number | undefined => {
    const value = text.trim();
    if (value === '') return undefined;
    if (!/^[+-]?\d+$/.test(value) || !Number.isSafeInteger(Number(value)) || Math.abs(Number(value)) > 1000) {
      throw new Error('Pre-play score bounds must be signed whole points from -1000 to +1000, or blank.');
    }
    return Number(value);
  };
  const scoreLower = scoreBound(draft.score_min), scoreUpper = scoreBound(draft.score_max);
  if (scoreLower !== undefined && scoreUpper !== undefined && scoreLower > scoreUpper) {
    throw new Error('Minimum score difference must not exceed maximum score difference.');
  }
  if (draft.period !== '' && !PERIODS.some(period => period === draft.period)) {
    throw new Error('Choose Q1, Q2, Q3, Q4 or OT, or leave the period unrestricted.');
  }
  const clockBound = (text: string): number | undefined => {
    const value = text.trim();
    if (value === '') return undefined;
    if (!whole(value, 0, 900)) throw new Error('Clock bounds must be whole seconds from 0 to 900, or blank.');
    return Number(value);
  };
  const clockLower = clockBound(draft.clock_min), clockUpper = clockBound(draft.clock_max);
  if ((clockLower !== undefined || clockUpper !== undefined) && draft.period === '') {
    throw new Error('Choose an explicit period before using clock bounds. Clear both clock bounds for unrestricted periods.');
  }
  if ((clockLower ?? 0) > (clockUpper ?? 900)) throw new Error('Minimum seconds remaining must not exceed maximum seconds remaining.');
  const repetitions = draft.bootstrap_repetitions.trim(), seed = draft.bootstrap_seed.trim();
  if ((repetitions !== '' && !whole(repetitions, 200, 1000)) || (seed !== '' && !whole(seed, 0, 4294967295))) {
    throw new Error('Bootstrap repetitions must be whole numbers from 200 to 1000; seed must be a whole number from 0 to 4294967295. Leave both blank for no uncertainty.');
  }
  if (seed !== '' && repetitions === '') throw new Error('Bootstrap seed requires repetitions. Clear both fields to omit uncertainty.');
  return { team: draft.team, season: Number(draft.season), before_week: Number(draft.before_week),
    ...(lower === undefined ? {} : { yardline_min: lower }), ...(upper === undefined ? {} : { yardline_max: upper }),
    ...(scoreLower === undefined ? {} : { score_min: scoreLower }), ...(scoreUpper === undefined ? {} : { score_max: scoreUpper }),
    ...(draft.period === '' ? {} : { period: draft.period as Query['period'] }),
    ...(clockLower === undefined ? {} : { clock_min: clockLower }), ...(clockUpper === undefined ? {} : { clock_max: clockUpper }),
    ...(repetitions === '' ? {} : { bootstrap_repetitions: Number(repetitions) }), ...(seed === '' ? {} : { bootstrap_seed: Number(seed) }),
    side: draft.side as Query['side'], season_type: draft.season_type as Query['season_type'], compare_league: draft.compare_league };
}

const object = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v);
const count = (v: unknown): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0;
const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const rate = (v: unknown) => v === null || (finite(v) && v >= 0 && v <= 1);
const hash = (v: unknown) => typeof v === 'string' && /^[0-9a-f]{64}$/.test(v);
const timestamp = (v: unknown) => {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$/.test(v)) return false;
  const parsed = Date.parse(v);
  // Date.parse can normalize impossible dates (e.g. February 30); reject those.
  return Number.isFinite(parsed) && new Date(parsed).toISOString().slice(0, 19) === v.slice(0, 19);
};

function metrics(v: unknown): v is Metrics {
  if (!object(v) || !['plays', 'games', 'dropbacks', 'designed_runs', 'epa_observations', 'missing_epa']
    .every((key) => count(v[key]))) return false;
  const m = v as unknown as Metrics;
  return m.dropbacks + m.designed_runs === m.plays && m.epa_observations + m.missing_epa === m.plays
    && m.games <= m.plays && (m.games === 0) === (m.plays === 0)
    && (m.plays === 0 ? m.dropback_rate === null : finite(m.dropback_rate))
    && (m.epa_observations === 0 ? m.success_rate === null && m.epa_per_play === null
      : finite(m.success_rate) && finite(m.epa_per_play))
    && rate(m.dropback_rate) && rate(m.success_rate)
    && m.small_sample === (m.plays < 30) && m.small_epa_sample === (m.epa_observations < 30);
}

function situation(v: unknown): boolean {
  if (!object(v)) return false;
  const { down, distance } = v;
  return metrics(v) && v.plays > 0 && count(down) && down >= 1 && down <= 4
    && typeof distance === 'string' && ['short', 'medium', 'long'].includes(distance);
}

const countKeys = ['plays', 'dropbacks', 'designed_runs', 'epa_observations', 'missing_epa'] as const;
const bucketKey = (row: { down: number; distance: string }) => `${row.down}:${row.distance}`;

function requestedField(query: Query): FieldPosition | undefined {
  if (query.yardline_min === undefined && query.yardline_max === undefined) return undefined;
  return { field: 'yardline_100', minimum_inclusive: query.yardline_min ?? 0,
    maximum_inclusive: query.yardline_max ?? 100, perspective: 'offense', missing_policy: 'exclude' };
}

function requestedScore(query: Query): ScoreContext | undefined {
  if (query.score_min === undefined && query.score_max === undefined) return undefined;
  return { field: 'score_differential', minimum_inclusive: query.score_min ?? null,
    maximum_inclusive: query.score_max ?? null, perspective: 'offense', missing_policy: 'exclude' };
}

function requestedContexts(query: Query): Contexts {
  const period = query.period;
  return { field_position: requestedField(query), score_differential: requestedScore(query),
    period: period === undefined ? undefined : { field: 'qtr', label: period,
      minimum_inclusive: period === 'OT' ? 5 : Number(period.slice(1)),
      maximum_inclusive: period === 'OT' ? null : Number(period.slice(1)), missing_policy: 'exclude' },
    clock: query.clock_min === undefined && query.clock_max === undefined ? undefined
      : { field: 'quarter_seconds_remaining', minimum_inclusive: query.clock_min ?? 0, maximum_inclusive: query.clock_max ?? 900,
        unit: 'seconds', timing: 'pre_play', missing_policy: 'exclude' } };
}

function sameContext(value: unknown, expected: Contexts[keyof Contexts]): boolean {
  return expected === undefined ? value === undefined : object(value) && Object.keys(value).length === Object.keys(expected).length
    && Object.entries(expected).every(([key, v]) => value[key] === v);
}

/** Return the pre-context count only when each active stage reconciles in order.
 * Field-only selected reports omit filter_order in schema v2; baselines always include it.
 */
function contextBefore(q: Record<string, unknown>, plays: number, contexts: Contexts, requireOrder: boolean): number | undefined {
  const stages = [
    { name: 'field_position', missing: 'missing_yardline_100', outside: 'outside_range' },
    { name: 'score_differential', missing: 'missing_score_differential', outside: 'outside_range' },
    { name: 'period', missing: 'missing_qtr', outside: 'outside_period' },
    { name: 'clock', missing: 'missing_quarter_seconds_remaining', outside: 'outside_range' },
  ] as const;
  const order = stages.filter(stage => contexts[stage.name]).map(stage => stage.name);
  if (requireOrder ? !Array.isArray(q.filter_order) || q.filter_order.length !== order.length
      || q.filter_order.some((v, i) => v !== order[i]) : 'filter_order' in q) return undefined;
  let before: number | undefined, after: number | undefined;
  for (const stage of stages) {
    const key = `${stage.name}_filter`;
    if (!contexts[stage.name]) { if (key in q) return undefined; continue; }
    const v = q[key];
    if (!object(v) || Object.keys(v).length !== 4 || !count(v.plays_before_filter) || !count(v.plays_after_filter)
        || !count(v[stage.missing]) || !count(v[stage.outside])
        || v.plays_before_filter !== (v[stage.missing] as number) + (v[stage.outside] as number) + v.plays_after_filter
        || (after !== undefined && v.plays_before_filter !== after)) return undefined;
    before ??= v.plays_before_filter;
    after = v.plays_after_filter;
  }
  return after === undefined ? plays : after === plays ? before : undefined;
}

function selectedQuality(value: unknown, plays: number, contexts: Contexts): value is SelectedQuality {
  const requireOrder = !!(contexts.score_differential || contexts.period);
  if (!object(value) || Object.keys(value).length !== 4 + contextCount(contexts) + Number(requireOrder)
      || !count(value.input_rows) || !count(value.eligible_rows_all_teams) || !count(value.eligible_rows_outside_cohort)
      || !object(value.excluded_rows_by_reason) || !Object.values(value.excluded_rows_by_reason).every(count)) return false;
  const q = value as SelectedQuality;
  const before = contextBefore(value, plays, contexts, requireOrder);
  return q.input_rows === q.eligible_rows_all_teams + Object.values(q.excluded_rows_by_reason).reduce((n, v) => n + v, 0)
    && q.eligible_rows_all_teams === q.eligible_rows_outside_cohort + plays
    && before !== undefined && before <= q.eligible_rows_all_teams;
}

function difference(value: unknown, selected: Metrics, baseline: Metrics): value is Difference {
  if (!object(value)) return false;
  return ([['dropback_rate_pp', 'dropback_rate', 100], ['success_rate_pp', 'success_rate', 100],
    ['epa_per_play', 'epa_per_play', 1]] as const).every(([key, metric, scale]) => {
    const left = selected[metric], right = baseline[metric];
    if (left === null || right === null) return value[key] === null;
    // Check the declared convention/units; render the API value, not a new estimate.
    return finite(value[key]) && Math.abs(value[key] - (left - right) * scale) <= 1e-9;
  });
}

function comparison(value: unknown, report: Report): value is Comparison {
  if (!object(value) || !object(value.population) || !object(value.cohort)
      || !object(value.data_quality) || !metrics(value.overall)
      || !difference(value.overall_difference, report.overall, value.overall)
      || value.difference_convention !== 'selected_minus_baseline'
      || value.situation_scope !== 'selected_team_observed_buckets'
      || !Array.isArray(value.warnings) || !value.warnings.every(w => typeof w === 'string')) return false;
  const { population: p, cohort: c, data_quality: q, overall } = value;
  const contexts = report.cohort;
  // Leave-team-out happens before context filtering, not on the displayed plays.
  const selectedBefore = report.data_quality.field_position_filter?.plays_before_filter
    ?? report.data_quality.score_differential_filter?.plays_before_filter
    ?? report.data_quality.period_filter?.plays_before_filter ?? report.overall.plays;
  const baselineBefore = contextBefore(q, overall.plays, contexts, true);
  if (Object.keys(c).length !== 5 + contextCount(contexts)
      || Object.entries(report.cohort).some(([key, v]) => !['team', ...contextKeys].includes(key) && c[key] !== v)
      || contextKeys.some(key => !sameContext(c[key], contexts[key]))
      || p.scope !== 'available_source_only' || p.weighting !== 'pooled_plays'
      || p.side !== report.cohort.side || p.excluded_team !== report.cohort.team
      || p.team_field !== (report.cohort.side === 'defense' ? 'defteam' : 'posteam')
      || !Array.isArray(p.teams) || !p.teams.every(t => typeof t === 'string' && /^[A-Z]{2,3}$/.test(t) && t !== report.cohort.team)
      || new Set(p.teams).size !== p.teams.length || p.team_count !== p.teams.length
      || p.teams.length > overall.plays || (p.teams.length === 0) !== (overall.plays === 0)
      || !count(p.shared_games_with_selected) || p.shared_games_with_selected > Math.min(overall.games, report.overall.games)
      || Object.keys(q).length !== 5 + contextCount(contexts)
      || !count(q.plays_before_context_filters) || !count(q.eligible_rows_same_season_type_before_week)
      || q.excluded_selected_team_rows !== selectedBefore || q.plays_after_context_filters !== overall.plays
      || q.eligible_rows_same_season_type_before_week !== q.plays_before_context_filters + selectedBefore
      || q.eligible_rows_same_season_type_before_week > report.data_quality.eligible_rows_all_teams
      || baselineBefore === undefined || baselineBefore !== q.plays_before_context_filters
      || !Array.isArray(value.situations) || value.situations.length !== report.situations.length) return false;
  const selected = new Map(report.situations.map(row => [bucketKey(row), row]));
  const seen = new Set<string>();
  const rows: Comparison['situations'] = [];
  for (const row of value.situations) {
    if (!object(row) || !count(row.down) || typeof row.distance !== 'string' || !metrics(row.baseline)) return false;
    const key = bucketKey({ down: row.down, distance: row.distance });
    const match = selected.get(key);
    if (!match || seen.has(key) || !difference(row.difference, match, row.baseline)
        || row.baseline.games > overall.games) return false;
    seen.add(key);
    rows.push(row as unknown as Comparison['situations'][number]);
  }
  // Only selected buckets appear: baseline-only buckets may contribute to overall.
  return countKeys.every(key => rows.reduce((n, row) => n + row.baseline[key], 0) <= overall[key]);
}

export function parseReport(value: unknown, query: Query): Report {
  const fail = () => { throw new Error('The API returned an incompatible report. No measurements were displayed.'); };
  if (!object(value) || value.schema_version !== 2 || !object(value.cohort)
      || !object(value.metric_context) || !object(value.source)) return fail();
  const { cohort, source, metric_context: context } = value;
  const contexts = requestedContexts(query);
  // Reject a different/filtered cohort rather than silently displaying it under this query.
  if (cohort.team !== query.team || cohort.season !== query.season || cohort.side !== query.side
      || cohort.season_type !== query.season_type || cohort.before_week_exclusive !== query.before_week
      || cohort.minimum_plays_warning !== 30 || Object.keys(cohort).length !== 6 + contextCount(contexts)
      || contextKeys.some(key => !sameContext(cohort[key], contexts[key]))
      || context.interpretation !== (query.side === 'defense' ? 'allowed' : 'produced')
      || context.perspective !== 'offense' || context.success_condition !== 'epa > 0') return fail();
  const snapshot = source.snapshot;
  if (typeof source.label !== 'string' || !source.label.trim() || !hash(source.sha256)
      || !object(snapshot) || !timestamp(snapshot.retrieved_at_utc) || !object(snapshot.archive)
      || !hash(snapshot.archive.sha256) || !object(snapshot.source) || snapshot.season !== query.season
      || !object(snapshot.decoded_csv) || snapshot.decoded_csv.sha256 !== source.sha256
      || snapshot.source.sha256 !== snapshot.archive.sha256
      || !object(snapshot.license) || typeof snapshot.license.attribution !== 'string'
      || typeof snapshot.license.identifier !== 'string'
      || !timestamp(snapshot.source.asset_updated_at_utc)) return fail();
  if (!metrics(value.overall) || !Array.isArray(value.situations)
      || !value.situations.every(situation)
      || !Array.isArray(value.warnings) || !value.warnings.every((w) => typeof w === 'string')) return fail();
  const situations = value.situations as Report['situations'];
  const overall = value.overall;
  if (!selectedQuality(value.data_quality, overall.plays, contexts)) return fail();
  const keys = situations.map((r) => `${r.down}:${r.distance}`);
  if (new Set(keys).size !== keys.length
      // Counts partition across buckets; games do not, and rates must not be summed.
      || countKeys
        .some((key) => situations.reduce((n, row) => n + row[key], 0) !== overall[key])) return fail();
  if (query.compare_league ? !comparison(value.league_comparison, value as unknown as Report)
    : 'league_comparison' in value) return fail();
  if (query.bootstrap_repetitions === undefined ? 'uncertainty' in value
    : !validUncertainty(value.uncertainty, value as unknown as Report, query)) return fail();
  return value as unknown as Report;
}

const errors: Record<string, string> = {
  invalid_query: 'The API rejected the query. Check the fields and try again.',
  season_unavailable: 'That season is not in the configured snapshot. Check the operator’s snapshot configuration.',
  context_unavailable: 'The configured snapshot lacks the requested context column. Clear the requested context bounds and period selection, or ask the operator to choose a suitable snapshot.',
  report_busy: 'The API is building another report. Wait a moment, then select Build report again.',
  snapshot_not_ready: 'The API snapshot is not ready. Ask the operator to check startup.',
};

export async function fetchReportDocument(query: Query, signal: AbortSignal): Promise<ReportDocument> {
  const params = new URLSearchParams({ team: query.team, season: String(query.season),
    before_week: String(query.before_week), side: query.side, season_type: query.season_type });
  if (query.compare_league) params.set('compare_league', 'true');
  if (query.yardline_min !== undefined) params.set('yardline_min', String(query.yardline_min));
  if (query.yardline_max !== undefined) params.set('yardline_max', String(query.yardline_max));
  if (query.score_min !== undefined) params.set('score_min', String(query.score_min));
  if (query.score_max !== undefined) params.set('score_max', String(query.score_max));
  if (query.period !== undefined) params.set('period', query.period);
  if (query.clock_min !== undefined) params.set('clock_min', String(query.clock_min));
  if (query.clock_max !== undefined) params.set('clock_max', String(query.clock_max));
  if (query.bootstrap_repetitions !== undefined) params.set('bootstrap_repetitions', String(query.bootstrap_repetitions));
  if (query.bootstrap_seed !== undefined) params.set('bootstrap_seed', String(query.bootstrap_seed));
  const response = await fetch(`/api/v1/report?${params}`, {
    signal, credentials: 'omit', cache: 'no-store', redirect: 'error',
  });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const code = object(body) && object(body.error) ? body.error.code : null;
    throw new Error(typeof code === 'string' && Object.hasOwn(errors, code) ? errors[code]
      : `Report request failed (HTTP ${response.status}). Check the local API and retry.`);
  }
  if (response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'application/json') {
    throw new Error('The local API did not return JSON. Check that the API and viewer are both running.');
  }
  const json = await response.text();
  return { report: parseReport(JSON.parse(json), query), json };
}

export async function fetchReport(query: Query, signal: AbortSignal): Promise<Report> {
  return (await fetchReportDocument(query, signal)).report;
}

export const percentage = (value: number | null) => value === null ? 'Unavailable' : `${(value * 100).toFixed(1)}%`;
export const epa = (value: number | null) => value === null ? 'Unavailable' : value.toFixed(3);
export const number = (value: number) => value.toLocaleString('en-US');
export function signedDifference(value: number | null, unit: 'pp' | 'EPA/play'): string {
  if (value === null) return 'Unavailable';
  // Normalize displayed negative zero; signs describe direction, never "better".
  const rounded = Number(value.toFixed(unit === 'pp' ? 1 : 3));
  return `${rounded > 0 ? '+' : ''}${rounded.toFixed(unit === 'pp' ? 1 : 3)} ${unit}`;
}
