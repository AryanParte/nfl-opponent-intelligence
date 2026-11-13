import type { DecisionDocument } from './decision';
import { useJsonDownload } from './useJsonDownload';

export function decisionFilename({ decision: { cohort: c } }: DecisionDocument): string {
  // Only validated basic situation values, never source labels, local choices or draft inputs.
  return `nfl-di-${c.team}-${c.season}-${c.season_type}-before-week-${c.before_week_exclusive}-down-${c.down.minimum_inclusive}-distance-${c.distance.minimum_inclusive}-${c.distance.maximum_inclusive}.decision.json`;
}

export function DecisionDownload({ document }: { document: DecisionDocument }) {
  const current = useJsonDownload(document);
  return <section className="report-download" aria-label="Decision download">
    {current?.url ? <a href={current.url} download={decisionFilename(document)} aria-describedby="decision-download-help">Download decision JSON</a>
      : current ? <p role="alert">This browser could not prepare the JSON download. The decision evidence is still available to read.</p>
      : <p>Preparing decision JSON download…</p>}
    <p id="decision-download-help" className="muted">Full returned decision evidence, including provenance, filters, warnings, contrasts and any requested comparison or uncertainty.
      {' '}Your local call choice is not included. No new request or calculation. Your browser controls saving; check its downloads.
      Editing the query removes this link. The filename identifies the basic situation; the JSON records the full context.</p>
  </section>;
}
