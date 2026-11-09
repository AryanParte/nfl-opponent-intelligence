import type { AriaAttributes } from 'react';
import { PERIODS } from './report';

type Field = 'period' | 'clock_min' | 'clock_max';
export function TimeControls({ draft, edit, fieldAccessibility, idPrefix = '' }: {
  draft: Record<Field, string>;
  edit: (field: Field, value: string) => void;
  fieldAccessibility: (field: Field, help: string) => Pick<AriaAttributes, 'aria-invalid' | 'aria-describedby'>;
  idPrefix?: string;
}) {
  const timeHelp = `${idPrefix}time-help`, clockHelp = `${idPrefix}clock-help`;
  return (
    <fieldset className="field-controls" aria-describedby={`${timeHelp} ${clockHelp}`}>
      <legend>Pre-play period &amp; clock (optional)</legend>
      <div className="field-inputs">
        <label>Period<select name="period" value={draft.period} onChange={(e) => edit('period', e.target.value)} {...fieldAccessibility('period', timeHelp)}>
          <option value="">Unrestricted</option>
          {PERIODS.map(period => <option key={period} value={period}>{period === 'OT' ? 'OT — all overtime periods' : period}</option>)}
        </select></label>
      </div>
      <p id={timeHelp} className="muted">Q1–Q4 select one regulation quarter; OT selects all periods numbered 5 or higher.
        Period-only selection excludes unknown periods but does not exclude missing clocks.</p>
      <div className="field-inputs">
        <label>Minimum seconds remaining<input name="clock_min" type="text" inputMode="numeric" autoComplete="off"
          value={draft.clock_min} onChange={(e) => edit('clock_min', e.target.value)} {...fieldAccessibility('clock_min', clockHelp)} /></label>
        <label>Maximum seconds remaining<input name="clock_max" type="text" inputMode="numeric" autoComplete="off"
          value={draft.clock_max} onChange={(e) => edit('clock_max', e.target.value)} {...fieldAccessibility('clock_max', clockHelp)} /></label>
      </div>
      <p id={clockHelp} className="muted">Inclusive whole seconds 0–900 remaining in the selected period at play start, not elapsed time or MM:SS.
        Clock bounds require an explicit period. Both blank = no clock filter; with one bound entered, the blank end defaults to 0 or 900.
        Zero is observed, not missing. Any requested clock range excludes missing clocks. Clearing the period does not clear entered bounds.</p>
    </fieldset>
  );
}
