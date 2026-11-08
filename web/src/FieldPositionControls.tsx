import type { AriaAttributes } from 'react';

type Bound = 'yardline_min' | 'yardline_max';
export function FieldPositionControls({ draft, edit, fieldAccessibility, idPrefix = '', showDefenseNote = false }: {
  draft: Record<Bound, string>;
  edit: (field: Bound, value: string) => void;
  fieldAccessibility: (field: Bound, help: string) => Pick<AriaAttributes, 'aria-invalid' | 'aria-describedby'>;
  idPrefix?: string; showDefenseNote?: boolean;
}) {
  const help = `${idPrefix}field-help`, coordinates = `${idPrefix}field-coordinate-help`;
  return <fieldset className="field-controls" aria-describedby={`${help} ${coordinates}`}>
    <legend>Pre-play field position (optional)</legend>
    <p id={coordinates} className="muted">Yards to the offense’s opponent’s goal line{showDefenseNote ? ', in either role' : ''}.
      20 = opponent’s 20; 80 = own 20.{showDefenseNote && ' Defense mode does not reverse the coordinates.'}</p>
    <div className="field-inputs">
      {/* Text preserves invalid partial input instead of turning it into an omitted filter. */}
      <label>Minimum yards to goal<input name="yardline_min" type="text" inputMode="decimal" autoComplete="off"
        value={draft.yardline_min} onChange={event => edit('yardline_min', event.target.value)} {...fieldAccessibility('yardline_min', `${help} ${coordinates}`)} /></label>
      <label>Maximum yards to goal<input name="yardline_max" type="text" inputMode="decimal" autoComplete="off"
        value={draft.yardline_max} onChange={event => edit('yardline_max', event.target.value)} {...fieldAccessibility('yardline_max', `${help} ${coordinates}`)} /></label>
    </div>
    <p id={help} className="muted">Inclusive decimals 0–100; use a dot. Both blank = no field filter.
      With one bound entered, the blank end defaults to 0 or 100. Any requested range, even 0–100, excludes missing positions.</p>
  </fieldset>;
}
