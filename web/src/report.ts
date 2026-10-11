/** Validate only this view's consumed contract; do not recompute analytics. */
export type Query = {
  team: string; season: number; before_week: number;
  side: 'offense' | 'defense'; season_type: 'REG' | 'POST';
  compare_league: boolean;
  yardline_min?: number; yardline_max?: number;
};
export type Draft = { [Key in Exclude<keyof Query, 'compare_league'>]: string } & { compare_league: boolean };
export type FieldPosition = { field: 'yardline_100'; minimum_inclusive: number; maximum_inclusive: number;
  perspective: 'offense'; missing_policy: 'exclude' };
export type FieldPositionCounts = { plays_before_filter: number; missing_yardline_100: number;
  outside_range: number; plays_after_filter: number };
type SelectedQuality = { input_rows: number; eligible_rows_all_teams: number; eligible_rows_outside_cohort: number;
  excluded_rows_by_reason: Record<string, number>; field_position_filter?: FieldPositionCounts };
export type Metrics = {
  plays: number; games: number; dropbacks: number; designed_runs: number;
  epa_observations: number; missing_epa: number;
  dropback_rate: number | null; success_rate: number | null; epa_per_play: number | null;
  small_sample: boolean; small_epa_sample: boolean;
};
export type Report = {
  schema_version: 2;
  cohort: { team: string; season: number; before_week_exclusive: number;
    side: Query['side']; season_type: Query['season_type']; minimum_plays_warning: number;
    field_position?: FieldPosition };
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
};
export type Difference = { dropback_rate_pp: number | null; success_rate_pp: number | null; epa_per_play: number | null };
export type Comparison = {
  population: { scope: 'available_source_only'; side: Query['side']; excluded_team: string;
    team_field: 'posteam' | 'defteam'; teams: string[]; team_count: number;
    weighting: 'pooled_plays'; shared_games_with_selected: number };
  data_quality: { eligible_rows_same_season_type_before_week: number; excluded_selected_team_rows: number;
    plays_before_context_filters: number; plays_after_context_filters: number; filter_order: string[];
    field_position_filter?: FieldPositionCounts };
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
  return { team: draft.team, season: Number(draft.season), before_week: Number(draft.before_week),
    ...(lower === undefined ? {} : { yardline_min: lower }), ...(upper === undefined ? {} : { yardline_max: upper }),
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

function sameField(value: unknown, expected: FieldPosition | undefined): boolean {
  return expected === undefined ? value === undefined : object(value) && Object.keys(value).length === 5
    && Object.entries(expected).every(([key, v]) => value[key] === v);
}

function fieldCounts(value: unknown, plays: number): value is FieldPositionCounts {
  if (!object(value) || Object.keys(value).length !== 4
      || !['plays_before_filter', 'missing_yardline_100', 'outside_range', 'plays_after_filter'].every(key => count(value[key]))) return false;
  const q = value as FieldPositionCounts;
  return q.plays_after_filter === plays
    && q.plays_before_filter === q.missing_yardline_100 + q.outside_range + q.plays_after_filter;
}

function selectedQuality(value: unknown, plays: number, filtered: boolean): value is SelectedQuality {
  if (!object(value) || Object.keys(value).length !== (filtered ? 5 : 4)
      || !count(value.input_rows) || !count(value.eligible_rows_all_teams) || !count(value.eligible_rows_outside_cohort)
      || !object(value.excluded_rows_by_reason) || !Object.values(value.excluded_rows_by_reason).every(count)) return false;
  const q = value as SelectedQuality;
  return q.input_rows === q.eligible_rows_all_teams + Object.values(q.excluded_rows_by_reason).reduce((n, v) => n + v, 0)
    && q.eligible_rows_all_teams === q.eligible_rows_outside_cohort + plays
    && (filtered ? fieldCounts(q.field_position_filter, plays) && q.field_position_filter.plays_before_filter <= q.eligible_rows_all_teams
      : !('field_position_filter' in q));
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
  const field = report.cohort.field_position;
  // Leave-team-out happens before context filtering, not on the displayed plays.
  const selectedBefore = report.data_quality.field_position_filter?.plays_before_filter ?? report.overall.plays;
  if (Object.keys(c).length !== (field ? 6 : 5)
      || Object.entries(report.cohort).some(([key, v]) => key !== 'team' && key !== 'field_position' && c[key] !== v)
      || !sameField(c.field_position, field)
      || p.scope !== 'available_source_only' || p.weighting !== 'pooled_plays'
      || p.side !== report.cohort.side || p.excluded_team !== report.cohort.team
      || p.team_field !== (report.cohort.side === 'defense' ? 'defteam' : 'posteam')
      || !Array.isArray(p.teams) || !p.teams.every(t => typeof t === 'string' && /^[A-Z]{2,3}$/.test(t) && t !== report.cohort.team)
      || new Set(p.teams).size !== p.teams.length || p.team_count !== p.teams.length
      || p.teams.length > overall.plays || (p.teams.length === 0) !== (overall.plays === 0)
      || !count(p.shared_games_with_selected) || p.shared_games_with_selected > Math.min(overall.games, report.overall.games)
      || !Array.isArray(q.filter_order) || q.filter_order.length !== (field ? 1 : 0)
      || (field && q.filter_order[0] !== 'field_position') || Object.keys(q).length !== (field ? 6 : 5)
      || !count(q.plays_before_context_filters) || !count(q.eligible_rows_same_season_type_before_week)
      || q.excluded_selected_team_rows !== selectedBefore || q.plays_after_context_filters !== overall.plays
      || q.eligible_rows_same_season_type_before_week !== q.plays_before_context_filters + selectedBefore
      || q.eligible_rows_same_season_type_before_week > report.data_quality.eligible_rows_all_teams
      || (field ? !fieldCounts(q.field_position_filter, overall.plays)
          || q.field_position_filter.plays_before_filter !== q.plays_before_context_filters
        : 'field_position_filter' in q || q.plays_before_context_filters !== overall.plays)
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
  const field = requestedField(query);
  // Reject a different/filtered cohort rather than silently displaying it under this query.
  if (cohort.team !== query.team || cohort.season !== query.season || cohort.side !== query.side
      || cohort.season_type !== query.season_type || cohort.before_week_exclusive !== query.before_week
      || cohort.minimum_plays_warning !== 30 || Object.keys(cohort).length !== (field ? 7 : 6)
      || !sameField(cohort.field_position, field)
      || context.interpretation !== (query.side === 'defense' ? 'allowed' : 'produced')
      || context.perspective !== 'offense' || context.success_condition !== 'epa > 0'
      || 'uncertainty' in value) return fail();
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
  if (!selectedQuality(value.data_quality, overall.plays, field !== undefined)) return fail();
  const keys = situations.map((r) => `${r.down}:${r.distance}`);
  if (new Set(keys).size !== keys.length
      // Counts partition across buckets; games do not, and rates must not be summed.
      || countKeys
        .some((key) => situations.reduce((n, row) => n + row[key], 0) !== overall[key])) return fail();
  if (query.compare_league ? !comparison(value.league_comparison, value as unknown as Report)
    : 'league_comparison' in value) return fail();
  return value as unknown as Report;
}

const errors: Record<string, string> = {
  invalid_query: 'The API rejected the query. Check the fields and try again.',
  season_unavailable: 'That season is not in the configured snapshot. Check the operator’s snapshot configuration.',
  context_unavailable: 'The configured snapshot lacks the requested context column. Clear the field-position bounds or ask the operator to choose a suitable snapshot.',
  report_busy: 'The API is building another report. Wait a moment, then select Build report again.',
  snapshot_not_ready: 'The API snapshot is not ready. Ask the operator to check startup.',
};

export async function fetchReport(query: Query, signal: AbortSignal): Promise<Report> {
  const params = new URLSearchParams({ team: query.team, season: String(query.season),
    before_week: String(query.before_week), side: query.side, season_type: query.season_type });
  if (query.compare_league) params.set('compare_league', 'true');
  if (query.yardline_min !== undefined) params.set('yardline_min', String(query.yardline_min));
  if (query.yardline_max !== undefined) params.set('yardline_max', String(query.yardline_max));
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
  return parseReport(await response.json(), query);
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
