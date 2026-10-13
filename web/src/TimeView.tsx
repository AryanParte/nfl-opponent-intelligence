import { number, type Report } from './report';

export function TimeView({ report }: { report: Report }) {
  const { period, clock } = report.cohort;
  if (!period) return <p className="muted">Period and clock: unrestricted; no time-context exclusions.</p>;
  const populations = [['Selected cohort', report.data_quality],
    ...(report.league_comparison ? [['Other teams baseline', report.league_comparison.data_quality] as const] : [])] as const;
  const rows = populations.flatMap(([label, quality]) => {
    const p = quality.period_filter!;
    const entries = [{ label, stage: 'Period', before: p.plays_before_filter, missing: p.missing_qtr,
      outside: p.outside_period, after: p.plays_after_filter }];
    if (clock) {
      const c = quality.clock_filter!;
      entries.push({ label, stage: 'Clock', before: c.plays_before_filter, missing: c.missing_quarter_seconds_remaining,
        outside: c.outside_range, after: c.plays_after_filter });
    }
    return entries;
  });
  return <section className="panel field-position" aria-labelledby="time-title">
    <div className="section-heading"><h3 id="time-title">Pre-play period &amp; clock</h3><span>Returned filters</span></div>
    <p><strong>{period.label === 'OT' ? 'OT — all periods numbered 5 or higher' : period.label}</strong>.
      {clock ? <> <strong>{clock.minimum_inclusive}–{clock.maximum_inclusive} seconds remaining at play start</strong>, inclusive.</>
        : ' Clock unrestricted: period selection alone does not exclude missing clocks.'}</p>
    <p>Q4 excludes overtime, even at the same clock value. Q4 0–120 is not a definition of the last two minutes of a game.
      OT bounds apply within each overtime period, not to cumulative overtime time. The 0–900 input limit does not certify season-specific overtime rules.</p>
    <p>Filter order: team / role / season / exclusive week cutoff → {report.cohort.field_position && 'field position → '}
      {report.cohort.score_differential && 'pre-play score → '}period{clock && ' → clock'}.
      Each stage receives only the preceding stage’s survivors; before = missing + outside + after.</p>
    <p>Missing means unknown period or clock at that stage; outside means a different period or a clock outside the range.
      Unknown values are excluded only by their requested filter, never imputed from another clock or later outcomes.
      A play missing both period and clock is removed at period, not counted twice.</p>
    <p className="table-hint muted">Scroll the accounting table horizontally to read all columns.</p>
    <div className="table-scroll" role="region" tabIndex={0} aria-label="Period and clock accounting, scroll horizontally on small screens">
      <table><caption className="sr-only">Ordered time-context exclusions after earlier cohort filters</caption>
        <thead><tr><th scope="col">Population / stage</th><th scope="col">Before</th><th scope="col">Missing</th>
          <th scope="col">Outside</th><th scope="col">After stage</th></tr></thead>
        <tbody>{rows.map(q => <tr key={`${q.label}:${q.stage}`}><th scope="row">{q.label} / {q.stage}</th>
          <td>{number(q.before)}</td><td>{number(q.missing)}</td><td>{number(q.outside)}</td><td>{number(q.after)}</td></tr>)}</tbody>
      </table>
    </div>
    <p className="muted">{clock ? 'After period is intermediate; after clock is final.' : 'After period is final; no clock stage was requested.'}
      {' '}All metrics and game/team coverage below use final survivors. Missing EPA is counted separately.
      Stage counts are conditional, not source-wide missingness. Selected losses are already in the global outside-cohort count; do not add them again.</p>
  </section>;
}
