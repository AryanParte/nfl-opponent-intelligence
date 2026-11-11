import type { AriaAttributes } from 'react';

type Field = 'bootstrap_repetitions' | 'bootstrap_seed';
export function BootstrapControls({ draft, edit, fieldAccessibility, idPrefix = '' }: {
  draft: Record<Field, string>;
  edit: (field: Field, value: string) => void;
  fieldAccessibility: (field: Field, help: string) => Pick<AriaAttributes, 'aria-invalid' | 'aria-describedby'>;
  idPrefix?: string;
}) {
  const help = `${idPrefix}bootstrap-help`;
  return (
    <fieldset className="field-controls" aria-describedby={help}>
      <legend>Exploratory game bootstrap (optional)</legend>
      <div className="field-inputs">
        <label>Bootstrap repetitions<input name="bootstrap_repetitions" type="text" inputMode="numeric" autoComplete="off"
          value={draft.bootstrap_repetitions} onChange={e => edit('bootstrap_repetitions', e.target.value)} {...fieldAccessibility('bootstrap_repetitions', help)} /></label>
        <label>Bootstrap seed<input name="bootstrap_seed" type="text" inputMode="numeric" autoComplete="off"
          value={draft.bootstrap_seed} onChange={e => edit('bootstrap_seed', e.target.value)} {...fieldAccessibility('bootstrap_seed', help)} /></label>
      </div>
      <p id={help} className="muted">Whole repetitions 200–1000 opt in; both blank means not requested. Seed 0–4294967295 requires repetitions;
        blank seed defaults to 0. Works with or without comparison. More draws add computation, not observed games or statistical reliability.
        Bounds are exploratory, not calibrated confidence. Editing clears results; aborting or timing out does not stop server computation.</p>
    </fieldset>
  );
}
