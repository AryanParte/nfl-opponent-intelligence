/** Shared wire-contract guards; these validate evidence, never produce estimates. */
export const object = (v: unknown): v is Record<string, unknown> =>
  typeof v === 'object' && v !== null && !Array.isArray(v);
export const exact = (v: Record<string, unknown>, keys: readonly string[]) =>
  Object.keys(v).length === keys.length && keys.every(k => Object.hasOwn(v, k));
export const count = (v: unknown): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0;
export const finite = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
export const rate = (v: unknown) => v === null || (finite(v) && v >= 0 && v <= 1);
export const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(item => typeof item === 'string');
export const matches = (v: unknown, expected: Record<string, unknown>) => object(v)
  && exact(v, Object.keys(expected)) && Object.entries(expected).every(([key, item]) => v[key] === item);
const hash = (v: unknown) => typeof v === 'string' && /^[0-9a-f]{64}$/.test(v);
const timestamp = (v: unknown) => {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$/.test(v)) return false;
  const parsed = Date.parse(v);
  // Date.parse normalizes impossible dates; require the original calendar time.
  return Number.isFinite(parsed) && new Date(parsed).toISOString().slice(0, 19) === v.slice(0, 19);
};
export type EvidenceSource = { label: string; sha256: string; snapshot: {
  retrieved_at_utc: string; season: number; archive: { sha256: string };
  decoded_csv: { sha256: string }; source: { sha256: string; asset_updated_at_utc: string };
  license: { attribution: string; identifier: string };
} };

/** Consistency of declared provenance, not browser verification of snapshot bytes. */
export function validSource(source: unknown, season: number): source is EvidenceSource {
  if (!object(source)) return false;
  const snapshot = source.snapshot;
  return typeof source.label === 'string' && !!source.label.trim() && hash(source.sha256)
    && object(snapshot) && timestamp(snapshot.retrieved_at_utc) && object(snapshot.archive)
    && hash(snapshot.archive.sha256) && object(snapshot.source) && snapshot.season === season
    && object(snapshot.decoded_csv) && snapshot.decoded_csv.sha256 === source.sha256
    && snapshot.source.sha256 === snapshot.archive.sha256
    && object(snapshot.license) && typeof snapshot.license.attribution === 'string'
    && typeof snapshot.license.identifier === 'string' && timestamp(snapshot.source.asset_updated_at_utc);
}
