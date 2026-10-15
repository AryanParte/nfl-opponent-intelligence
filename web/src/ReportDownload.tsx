import { useEffect, useState } from 'react';
import type { ReportDocument } from './report';

export function reportFilename({ report: { cohort: c } }: ReportDocument): string {
  // Only the validated basic cohort, never a source label, URL, path or draft input.
  return `nfl-oi-${c.team}-${c.season}-${c.season_type}-${c.side}-before-week-${c.before_week_exclusive}.report.json`;
}

export function ReportDownload({ document }: { document: ReportDocument }) {
  const [resource, setResource] = useState<{ document: ReportDocument; url: string | null } | null>(null);
  useEffect(() => {
    let url: string;
    try {
      // Do not stringify the parsed object, round values or project out unrendered fields.
      url = URL.createObjectURL(new Blob([document.json], { type: 'application/json;charset=utf-8' }));
    } catch {
      setResource({ document, url: null });
      return;
    }
    setResource({ document, url });
    // Reuse one URL while the link is accessible; not a premature revoke on click.
    return () => URL.revokeObjectURL(url);
  }, [document]);

  // A new document must never temporarily link to the previous document's bytes.
  const current = resource?.document === document ? resource : null;
  return <section className="report-download" aria-label="Report download">
    {current?.url ? <a href={current.url} download={reportFilename(document)} aria-describedby="download-help">Download report JSON</a>
      : current ? <p role="alert">This browser could not prepare the JSON download. The report is still available to read.</p>
      : <p>Preparing JSON download…</p>}
    <p id="download-help" className="muted">Full returned report, including provenance and any requested filters, comparison and uncertainty.
      {' '}No new request or calculation. Your browser controls saving; check its downloads. Editing the query removes this link.</p>
  </section>;
}
