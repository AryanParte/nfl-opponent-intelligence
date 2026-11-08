import type { EvidenceSource } from './contract';

export function SourceView({ source, titleId, versionLabel }: {
  source: EvidenceSource; titleId: string; versionLabel: string;
}) {
  return <section className="panel source" aria-labelledby={titleId}>
    <div className="section-heading"><h3 id={titleId}>Source &amp; availability</h3><span>{versionLabel}</span></div>
    <p className="source-label">{source.label}</p>
    <dl className="provenance">
      <div><dt>Snapshot acquired (UTC)</dt><dd>{source.snapshot.retrieved_at_utc}</dd></div>
      <div><dt>Upstream asset updated (UTC)</dt><dd>{source.snapshot.source.asset_updated_at_utc}</dd></div>
    </dl>
    <p className="muted">Dataset attribution: {source.snapshot.license.attribution} · {source.snapshot.license.identifier}. Displayed values are calculated cohort summaries.</p>
    <p>These are source timestamps, not a live-feed or freshness guarantee. A week cutoff does not establish that the source was available before that week.</p>
    <details><summary>Inspect source fingerprints</summary>
      <dl><dt>Decoded CSV SHA-256</dt><dd className="fingerprint">{source.sha256}</dd>
        <dt>Archive SHA-256</dt><dd className="fingerprint">{source.snapshot.archive.sha256}</dd></dl>
      <p className="muted">Fingerprints identify bytes; they do not certify completeness or analytical validity.</p>
    </details>
  </section>;
}
