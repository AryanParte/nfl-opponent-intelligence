import type { AriaAttributes } from 'react';

type Bound = 'score_min' | 'score_max';
export function ScoreControls({ draft, edit, fieldAccessibility, idPrefix = '', showDefenseNote = false }: {
  draft: Record<Bound, string>;
  edit: (field: Bound, value: string) => void;
  fieldAccessibility: (field: Bound, help: string) => Pick<AriaAttributes, 'aria-invalid' | 'aria-describedby'>;
  idPrefix?: string; showDefenseNote?: boolean;
}) {
  const help = `${idPrefix}score-help`, perspective = `${idPrefix}score-perspective-help`;
  return <fieldset className="field-controls" aria-describedby={`${help} ${perspective}`}>
    <legend>Pre-play score difference (optional)</legend>
    <p id={perspective} className="muted">Offense points minus defense points before the play.
      Negative = offense trailing; positive = offense leading; 0 = tied, not missing.
      {showDefenseNote && ' Defense mode does not reverse the sign.'}</p>
    <div className="field-inputs">
      {/* Text keeps partial signs invalid, not blank; the keyboard must allow minus. */}
      <label>Minimum score difference<input name="score_min" type="text" autoComplete="off"
        value={draft.score_min} onChange={event => edit('score_min', event.target.value)} {...fieldAccessibility('score_min', `${help} ${perspective}`)} /></label>
      <label>Maximum score difference<input name="score_max" type="text" autoComplete="off"
        value={draft.score_max} onChange={event => edit('score_max', event.target.value)} {...fieldAccessibility('score_max', `${help} ${perspective}`)} /></label>
    </div>
    <p id={help} className="muted">Inclusive signed whole points, -1000 to +1000 (API input limits, not typical game scores).
      A blank end is unbounded; both blank = no score filter. Any requested score range excludes missing pre-play scores.
      Field position is filtered first when both are requested.</p>
  </fieldset>;
}
