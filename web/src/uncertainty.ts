import type { Metrics, Query, Report } from './report';

export const intervalMetrics = ['dropback_rate', 'success_rate', 'epa_per_play'] as const;
const differenceMetrics = ['dropback_rate_pp', 'success_rate_pp', 'epa_per_play'] as const;
export type IntervalSummary = {
  interval: { lower: number; upper: number } | null;
  status: 'ok' | 'undefined_estimate' | 'insufficient_games' | 'too_few_valid_replicates' | 'degenerate_interval';
  unit: 'proportion' | 'percentage_points' | 'expected_points_per_observed_play';
  support_games: { selected?: number; baseline?: number };
  few_games: boolean; valid_replicates: number; undefined_replicates: number;
};
export type IntervalRow = {
  selected: Record<typeof intervalMetrics[number], IntervalSummary>;
  baseline?: Record<typeof intervalMetrics[number], IntervalSummary>;
  difference?: Record<typeof differenceMetrics[number], IntervalSummary>;
};
export type Uncertainty = {
  method: 'game_cluster_percentile_v1'; nominal_level: 0.95;
  repetitions: number; performed_repetitions: number; seed: number;
  random_generator: 'python_random.Random.randrange'; quantile_method: 'linear_n_minus_1';
  resampling_unit: 'game_id'; resampling_games: number;
  resampling_population: 'selected' | 'selected_and_baseline_union'; shared_game_weights: boolean;
  minimum_support_games: 5; few_games_warning_below: 20; minimum_valid_fraction: 0.95;
  overall: IntervalRow; situations: (IntervalRow & { down: number; distance: string })[];
  warnings: string[];
};

const object = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const exact = (v: Record<string, unknown>, keys: readonly string[]) => Object.keys(v).length === keys.length && keys.every(k => Object.hasOwn(v, k));
const count = (v: unknown): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0;
const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const bucket = (v: { down: number; distance: string }) => `${v.down}:${v.distance}`;

function intervalRow(value: unknown, selected: Metrics, baseline: Metrics | undefined, performed: number, frameGames: number, situation = false): boolean {
  const populations = baseline ? ['selected', 'baseline', 'difference'] as const : ['selected'] as const;
  if (!object(value) || !exact(value, [...populations, ...(situation ? ['down', 'distance'] : [])])) return false;
  for (const population of populations) {
    const entries = value[population], keys = population === 'difference' ? differenceMetrics : intervalMetrics;
    if (!object(entries) || !exact(entries, keys)) return false;
    for (const [index, key] of keys.entries()) {
      const item = entries[key];
      const sides = population === 'difference' ? { selected, baseline: baseline! }
        : population === 'baseline' ? { baseline: baseline! } : { selected };
      if (!object(item) || !exact(item, ['interval', 'status', 'unit', 'support_games', 'few_games', 'valid_replicates', 'undefined_replicates'])
          || !object(item.support_games) || !exact(item.support_games, Object.keys(sides))) return false;
      const support = item.support_games;
      for (const [side, points] of Object.entries(sides)) {
        const n = support[side], maximum = index === 0 ? points.games : Math.min(points.games, points.epa_observations);
        if (!count(n) || n > maximum || (index === 0 ? n !== maximum : (n === 0) !== (points.epa_observations === 0))) return false;
      }
      const unit = index === 2 ? 'expected_points_per_observed_play' : population === 'difference' ? 'percentage_points' : 'proportion';
      const valid = item.valid_replicates, undefinedDraws = item.undefined_replicates;
      if (item.unit !== unit || !count(valid) || !count(undefinedDraws) || valid + undefinedDraws !== performed) return false;
      const minimum = Math.min(...Object.values(support) as number[]);
      if (frameGames > 0 && minimum === frameGames && valid !== performed) return false;
      const required = minimum === 0 ? 'undefined_estimate' : minimum < 5 ? 'insufficient_games'
        : valid < Math.ceil(.95 * performed) ? 'too_few_valid_replicates' : undefined;
      if (item.few_games !== (minimum < 20) || (minimum === 0 && valid !== 0)
          || (required ? item.status !== required : item.status !== 'ok' && item.status !== 'degenerate_interval')) return false;
      const bounds = item.interval;
      if (item.status === 'ok') {
        if (!object(bounds) || !exact(bounds, ['lower', 'upper']) || !finite(bounds.lower) || !finite(bounds.upper)
            || bounds.lower >= bounds.upper
            || Math.abs(bounds.upper - bounds.lower) <= Math.max(1e-12, 1e-12 * Math.max(Math.abs(bounds.lower), Math.abs(bounds.upper)))
            || (index !== 2 && (bounds.lower < (population === 'difference' ? -100 : 0) || bounds.upper > (population === 'difference' ? 100 : 1)))) return false;
      } else if (bounds !== null) return false;
    }
    // Success and EPA use the same observed-EPA denominators and games, not play support.
    const dropback = entries[keys[0]] as IntervalSummary, success = entries[keys[1]] as IntervalSummary, epa = entries[keys[2]] as IntervalSummary;
    if (success.valid_replicates !== epa.valid_replicates
        || epa.valid_replicates > dropback.valid_replicates
        || (Object.entries(epa.support_games).every(([side, n]) => dropback.support_games[side as 'selected' | 'baseline'] === n)
          && epa.valid_replicates !== dropback.valid_replicates)
        || Object.entries(success.support_games).some(([side, n]) => epa.support_games[side as 'selected' | 'baseline'] !== n)) return false;
  }
  if (baseline) {
    const row = value as unknown as IntervalRow;
    for (const [i, key] of intervalMetrics.entries()) {
      const left = row.selected[key], right = row.baseline![key], diff = row.difference![differenceMetrics[i]];
      // Paired differences require both denominators in the SAME replicate.
      if (diff.support_games.selected !== left.support_games.selected || diff.support_games.baseline !== right.support_games.baseline
          || diff.valid_replicates > Math.min(left.valid_replicates, right.valid_replicates)
          || diff.valid_replicates < Math.max(0, left.valid_replicates + right.valid_replicates - performed)) return false;
    }
  }
  return true;
}

/** Validate consumed method/support metadata, not bootstrap distributions or statistical calibration. */
export function validUncertainty(value: unknown, report: Report, query: Query): value is Uncertainty {
  if (!object(value) || !count(query.bootstrap_repetitions) || query.bootstrap_repetitions < 200 || query.bootstrap_repetitions > 1000) return false;
  const comparison = report.league_comparison;
  const games = report.overall.games + (comparison ? comparison.overall.games - comparison.population.shared_games_with_selected : 0);
  const performed = games ? query.bootstrap_repetitions : 0;
  const expected = { method: 'game_cluster_percentile_v1', nominal_level: .95,
    repetitions: query.bootstrap_repetitions, performed_repetitions: performed, seed: query.bootstrap_seed ?? 0,
    random_generator: 'python_random.Random.randrange', quantile_method: 'linear_n_minus_1', resampling_unit: 'game_id',
    resampling_games: games, resampling_population: comparison ? 'selected_and_baseline_union' : 'selected', shared_game_weights: !!comparison,
    minimum_support_games: 5, few_games_warning_below: 20, minimum_valid_fraction: .95 };
  if (!exact(value, [...Object.keys(expected), 'overall', 'situations', 'warnings'])
      || Object.entries(expected).some(([key, v]) => value[key] !== v)
      || !Array.isArray(value.warnings) || !value.warnings.every(w => typeof w === 'string')
      || !intervalRow(value.overall, report.overall, comparison?.overall, performed, games)
      || !Array.isArray(value.situations) || value.situations.length !== report.situations.length) return false;
  const selected = new Map(report.situations.map(row => [bucket(row), row]));
  const baseline = new Map(comparison?.situations.map(row => [bucket(row), row.baseline]));
  const seen = new Set<string>();
  for (const row of value.situations) {
    if (!object(row) || !count(row.down) || typeof row.distance !== 'string') return false;
    const key = bucket({ down: row.down, distance: row.distance }), points = selected.get(key);
    if (!points || seen.has(key) || !intervalRow(row, points, baseline.get(key), performed, games, true)) return false;
    // Each situation is a subset, never a source of more support/defined draws than overall.
    const overall = value.overall as IntervalRow;
    for (const population of ['selected', 'baseline', 'difference'] as const) {
      const entries = row[population] as Record<string, IntervalSummary> | undefined;
      const totals = overall[population] as Record<string, IntervalSummary> | undefined;
      if (entries && Object.entries(entries).some(([metric, item]) => item.valid_replicates > totals![metric].valid_replicates
          || Object.entries(item.support_games).some(([side, n]) => n! > totals![metric].support_games[side as 'selected' | 'baseline']!))) return false;
    }
    seen.add(key);
  }
  return true;
}
