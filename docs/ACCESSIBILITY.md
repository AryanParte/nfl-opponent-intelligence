# Scout accessibility review — 2026-10-16

This closes P1.4's **bounded local-viewer review**, not a WCAG conformance audit,
screen-reader certification or public-release claim. Scout's analytics, API,
schema v2, snapshots and downloadable evidence are unchanged. Decision Lab is
still planned. The next implementation unit is its small offline P1.5 contract.

## Findings and changes

1. **Invalid-query recovery:** a real-browser regression initially failed because
   submitting a clock without a period left focus on the clock, with no invalid
   field association. `parseQuery` now raises a typed `QueryValidationError` with
   field identities, preserving existing validation rules/messages. React marks
   those controls with `aria-invalid`, adds the error to `aria-describedby`
   **without replacing existing instructions**, and focuses the first affected
   control after a rejected submission. Relational range errors identify both
   ends; missing period/repetitions identify the missing prerequisite, not valid
   seconds/seed values. Validation still stops at the first failed rule/group;
   it does not claim to enumerate every error. Any edit clears the displayed error
   and invalid markers, as it already cleared stale results. Repeated invalid
   submission refocuses correctly; no HTTP request is made.
2. **Do not interrupt navigation:** only local submission validation moves focus.
   API/network/timeout failures retain the existing alert; asynchronous completion
   does not focus a field or mislabel valid controls. The polite status region
   stays mounted across states. DOM/live-region tests are not evidence of what a
   particular screen reader actually speaks.
3. **Visible instructions and contrast:** required controls and core input formats
   are now explicit. The input/select border changed from `#9fb2ba` (2.20:1 against
   white) to `#728892` (3.72:1). The browser test computes the sRGB contrast ratio
   from rendered styles and requires at least 3:1. This manual-review finding was
   not detected by axe. Existing 3px blue focus outlines, native controls, table
   captions, column/row headers and focusable named scroll regions are retained.

The design follows W3C guidance on [field errors and notifications](https://www.w3.org/WAI/tutorials/forms/notifications/),
[non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)
and [reflow, including two-dimensional data tables](https://www.w3.org/WAI/WCAG21/Understanding/reflow.html).
Tests are evidence for these specific behaviors, not full coverage of those standards.

## Reproduction and evidence

Use [the existing browser harness setup](WEB.md#repeatable-browser-integration-checks)
with free loopback ports 8000/5173, Python 3.13/API extras, Node 24.19.0 and pinned
Chromium. From `web/`, `npm ci`, `npm test`, `npm run build` and `npm run test:e2e`
run the component/contract, type/build and actual-browser checks. Activate the API
virtual environment before the browser command. No real NFL data or public server
is needed; the API uses an explicitly **synthetic**, immutable local snapshot.

- 672 frontend tests pass (36 new cases for field identities, error associations,
  repeated submission, cleanup and non-interrupting asynchronous errors).
- All 14 browser cases pass on Chromium 156.0.8078.4, Playwright 1.64.1: seven at
  1280×900 and seven at 390×844; the full keyboard case also switches to 320×900
  CSS pixels in each context. This is a viewport/reflow test, not actual browser
  zoom or a physical mobile-device test.
- axe-core / `@axe-core/playwright` 4.14.0 scan idle, loading, invalid query, actual
  API error, empty cohort, expanded filtered report and expanded 320px report.
  No automatic violations in these 14 scans, with no exclusions or disabled rules.
  [Playwright's guidance](https://playwright.dev/docs/accessibility-testing) explicitly
  distinguishes automatic checks from manual and user evaluation.
- Keyboard tests follow all 15 controls in DOM order, submit, correct the period
  dependency using native selection, open disclosures with Enter, reach named
  tables, scroll with ArrowRight and leave with Tab. Existing tests cover native
  keyboard JSON download and byte-identical offline brief replay. 320px query and
  table screenshots were visually inspected: controls/text reflow, focus is visible,
  wide tables scroll within the report and the document has no horizontal overflow.
- Core 196 / API 24 tests pass on Python 3.11/3.12/3.13 (API warnings as errors;
  clean dependency checks). All 71 generated API fixtures remain unchanged.

The checker is **development-only**, MPL-2.0, unmodified and pinned in
`web/package-lock.json`; npm retains its upstream license. It is not imported by
the application and adds no production dependency or football-data source.
Full axe JSON, including `incomplete`, is written to ignored `web/test-results/`
and retained with existing CI diagnostics on failure. No real/user data is captured.

## Scan incompletes are not passes

The recorded full-page scans also contain review-needed contrast results:

- the decorative `aria-hidden` arrow beside the Build report text (non-text glyph);
- short numeric cells and partially clipped cells in narrow horizontal tables.

These were inspected, not suppressed. The arrow conveys no information beyond
the labeled button. Expanded desktop tables have no unresolved cell contrast
checks; narrow tables use the same colors, with scrolling verified and screenshots
inspected. Clipped off-screen cells are intentional two-dimensional table overflow,
not hidden measurements. This does **not** prove every visual state or assistive
technology can navigate every cell. The raw incomplete entries remain available
for follow-up; a zero-violation scan must never be summarized as full compliance.

## Remaining coverage

Before a public accessibility/conformance claim, separately verify and record:

- VoiceOver/Safari and NVDA/Firefox or Chrome: label/help verbosity, repeated error
  announcements, loading/completion speech, table header associations/navigation,
  disclosures and download feedback with actual assistive technology enabled;
- Firefox/WebKit, real touch devices, 200% text resizing, 400% browser zoom, text
  spacing overrides and forced-colors/high-contrast settings;
- keyboard-only and low-vision user evaluation beyond scripted paths; review all
  remaining `incomplete` results in those environments.

None of those checks ran here. Do not infer spoken output from a DOM assertion,
mobile support from viewport emulation, or WCAG certification from axe. Preserve
these release-readiness gaps while moving to the small P1.5 foundation unit;
do not start a parallel UI, analytics stack, database or model to close this review.
