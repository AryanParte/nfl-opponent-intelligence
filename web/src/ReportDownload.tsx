import { useJsonDownload } from './useJsonDownload';
import type { ReportDocument } from './report';

export function reportFilename({ report: { cohort: c } }: ReportDocument): string {
  // Only the validated basic cohort, never a source label, URL, path or draft input.
  return `nfl-oi-${c.team}-${c.season}-${c.season_type}-${c.side}-before-week-${c.before_week_exclusive}.report.json`;
}

export function ReportDownload({ document }: { document: ReportDocument }) {
  const current = useJsonDownload(document);
  return <section className="report-download" aria-label="Report download">
    {current?.url ? <a href={current.url} download={reportFilename(document)} aria-describedby="download-help">Download report JSON</a>
      : current ? <p role="alert">This browser could not prepare the JSON download. The report is still available to read.</p>
      : <p>Preparing JSON download…</p>}
    <p id="download-help" className="muted">Full returned report, including provenance and any requested filters, comparison and uncertainty.
      {' '}No new request or calculation. Your browser controls saving; check its downloads. Editing the query removes this link.</p>
  </section>;
}
