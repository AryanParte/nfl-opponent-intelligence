/** Validate only this view's consumed contract; do not recompute analytics. */
export type Query = {
  team: string; season: number; before_week: number;
  side: 'offense' | 'defense'; season_type: 'REG' | 'POST';
};
export type Draft = { [Key in keyof Query]: string };
export type Metrics = {
  plays: number; games: number; dropbacks: number; designed_runs: number;
  epa_observations: number; missing_epa: number;
  dropback_rate: number | null; success_rate: number | null; epa_per_play: number | null;
  small_sample: boolean; small_epa_sample: boolean;
};
export type Report = {
  schema_version: 2;
  cohort: { team: string; season: number; before_week_exclusive: number;
    side: Query['side']; season_type: Query['season_type']; minimum_plays_warning: number };
  source: { label: string; sha256: string; snapshot: {
    retrieved_at_utc: string; archive: { sha256: string };
    source: { asset_updated_at_utc: string };
    license: { attribution: string; identifier: string };
  } };
  overall: Metrics;
  situations: (Metrics & { down: number; distance: 'short' | 'medium' | 'long' })[];
  warnings: string[];
};

export function parseQuery(draft: Draft): Query {
  const whole = (value: string, min: number, max: number) =>
    /^\d+$/.test(value) && Number(value) >= min && Number(value) <= max;
  if (!/^[A-Z]{2,3}$/.test(draft.team) || !whole(draft.season, 1999, 9999)
      || !whole(draft.before_week, 1, 23) || !['offense', 'defense'].includes(draft.side)
      || !['REG', 'POST'].includes(draft.season_type)) {
    throw new Error('Use a 2–3 letter uppercase team code, season 1999–9999 and cutoff week 1–23. Check the role and season type.');
  }
  return { team: draft.team, season: Number(draft.season), before_week: Number(draft.before_week),
    side: draft.side as Query['side'], season_type: draft.season_type as Query['season_type'] };
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

export function parseReport(value: unknown, query: Query): Report {
  const fail = () => { throw new Error('The API returned an incompatible report. No measurements were displayed.'); };
  if (!object(value) || value.schema_version !== 2 || !object(value.cohort)
      || !object(value.metric_context) || !object(value.source)) return fail();
  const { cohort, source, metric_context: context } = value;
  // Reject a different/filtered cohort rather than silently displaying it under this query.
  if (cohort.team !== query.team || cohort.season !== query.season || cohort.side !== query.side
      || cohort.season_type !== query.season_type || cohort.before_week_exclusive !== query.before_week
      || cohort.minimum_plays_warning !== 30 || Object.keys(cohort).length !== 6
      || context.interpretation !== (query.side === 'defense' ? 'allowed' : 'produced')
      || context.perspective !== 'offense' || context.success_condition !== 'epa > 0'
      || 'league_comparison' in value || 'uncertainty' in value) return fail();
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
  const keys = situations.map((r) => `${r.down}:${r.distance}`);
  if (new Set(keys).size !== keys.length
      // Counts partition across buckets; games do not, and rates must not be summed.
      || (['plays', 'dropbacks', 'designed_runs', 'epa_observations', 'missing_epa'] as const)
        .some((key) => situations.reduce((n, row) => n + row[key], 0) !== overall[key])) return fail();
  return value as unknown as Report;
}

const errors: Record<string, string> = {
  invalid_query: 'The API rejected the query. Check the fields and try again.',
  season_unavailable: 'That season is not in the configured snapshot. Check the operator’s snapshot configuration.',
  report_busy: 'The API is building another report. Wait a moment, then select Build report again.',
  snapshot_not_ready: 'The API snapshot is not ready. Ask the operator to check startup.',
};

export async function fetchReport(query: Query, signal: AbortSignal): Promise<Report> {
  const params = new URLSearchParams({ team: query.team, season: String(query.season),
    before_week: String(query.before_week), side: query.side, season_type: query.season_type });
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
