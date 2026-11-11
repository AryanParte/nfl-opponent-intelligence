# Scout accessibility review — 2026-10-16

This closes P1.4's **bounded local-viewer review**, not a WCAG conformance audit,
screen-reader certification or public-release claim. Scout's analytics, API,
schema v2, snapshots and downloadable evidence are unchanged. The original review
preceded Decision Lab; the bounded follow-ups below cover its rendered slices.

## Decision uncertainty follow-up — 2026-11-11

Shared text inputs preserve invalid partial values and use Decision-specific help/
error IDs. Both controls join the native tab order; invalid repetitions or an
orphaned seed focus repetitions, while an invalid seed focuses itself. Correcting
the query removes stale evidence and requires explicit submission. Mode changes
preserve independent drafts and completed results without another request.

Run/Pass interval tables have captions, row/column headers and named keyboard-
focusable scroll regions. Availability and withheld reasons are text, not color;
method metadata is a native disclosure. All 32 desktop/narrow Chromium cases pass,
including actual synthetic API evidence, sparse/empty support, input correction,
keyboard order, comparison toggling and 320-pixel containment/scrolling. The focused
narrow screenshot was inspected. New axe scans have zero violations; loaded desktop
and invalid states have no incompletes, while narrow/clipped numeric tables retain
contrast incompletes (including empty-state tables). This does not resolve every
contrast node or establish conformance. Screen-reader, real-device, zoom and cross-
browser gaps remain. No unexpected requests/errors; owned servers stopped.

## Decision league comparison follow-up — 2026-11-10

The optional checkbox is in the native tab order, works with Space and has unique
Decision help/error IDs. Toggling removes stale evidence without fetching; returning
from Scout preserves a completed result and independent mode state. Candidate
comparison and baseline-accounting tables have captions, row/column headers and
named keyboard-focusable scroll regions. Unavailable values are text, not color.

All 30 desktop/narrow Chromium cases pass, including real synthetic API off/on/off,
separate selected/baseline accounting and empty-baseline/empty-selected states.
New axe scans have no violations. Loaded desktop has no incomplete checks;
loaded narrow and 320-pixel/empty-state scans retain color-contrast incompletes
on numeric/clipped table content. Focused 320-pixel comparison and ledger screenshots
were inspected: surrounding text reflows, focus outlines remain visible and wide
columns scroll within their regions without page overflow. Those checks do not
resolve all incomplete contrast nodes or establish conformance. No unexpected
external requests/page errors occurred; owned servers stopped. Screen-reader,
real-device, zoom and cross-browser coverage remain open.

## Decision period/clock follow-up — 2026-11-09

Shared controls preserve Scout behavior and give Decision unique help/error IDs.
Keyboard order includes period and both seconds bounds. A clock without a period
focuses the missing period; malformed seconds retain their text and focus their
own error. Clearing period never silently clears entered bounds. Completed time
queries and independent Scout drafts survive mode changes.

All 28 desktop/narrow Chromium cases pass. Actual synthetic API checks cover
period-only/full-clock missingness, combined six-stage accounting, OT/zero/empty
states and filter-removal recovery. Axe reports no violations in the new scans;
narrow numeric/clipped table cells retain contrast `incomplete` results for review.
The focused 320-pixel accounting screenshot was inspected: text reflows, the
focus outline is visible and wide columns scroll within the named table region.
No unexpected external requests/page errors occurred; owned servers stopped.
These checks do not establish assistive-technology or WCAG conformance. The
existing manual, real-device, zoom and cross-browser gaps remain open.

## Decision score follow-up — 2026-11-08

Shared text controls retain partial signs for validation and permit a minus sign;
Decision-specific help IDs keep mounted Scout controls independent. Keyboard order
includes both score bounds; invalid input focuses its linked error without fetching.
The combined context section retains table headers, a caption and a named focusable
scroll region. All 26 desktop/narrow Chromium cases pass, including real API
field/score accounting, tie/empty/filter-removal recovery, preserved mode state,
axe scans and 320-pixel keyboard scrolling. The focused screenshot was inspected;
no unexpected external requests or page errors occurred. Existing assistive-technology,
zoom, real-device and cross-browser gaps remain open.

## Decision field-position follow-up — 2026-11-07

Shared field controls retain text input, decimal keyboard hints and linked error/
coordinate instructions. Decision-specific help IDs avoid collisions with mounted
Scout controls. Invalid bounds preserve input and focus the field; edits clear
stale evidence. Keyboard order now includes both optional bounds. The exclusion
table has a caption, row/column headers and a named focusable scroll region.

All 24 desktop/narrow Chromium cases pass. New real API cases include invalid,
filtered, empty and cleared-bound recovery, mode preservation, axe scans and
320-pixel horizontal keyboard scrolling without document overflow. The focused
accounting screenshot was inspected. No unexpected external browser request or
uncaught page error occurred. Existing coverage gaps below remain open.

## Decision Lab follow-up — 2026-11-06

The same app now has manually activated Scout/Decision tabs, with named panels,
selected/tab-stop states, Left/Right wrapping, Home/End, Enter/Space and a skip link
to the active query. Hidden visited views retain drafts/results without entering
the keyboard/accessibility tree. Only a new submitted validation error focuses a
field; returning to a saved error or receiving an asynchronous result does not.
The new form has field-linked instructions/errors and a persistent polite status;
the candidate table has headers, a caption and a keyboard-focusable horizontal
scroll region. A preferred call is explicitly withheld in every response.

The expanded synthetic Chromium suite passes 22 desktop/narrow cases, including
real Decision API evidence and Scout download preservation. Axe scans cover
Decision idle/invalid/error/empty/loaded states and 320-pixel reflow. Keyboard-only
navigation and screenshot inspection complement those scans. The initial scan
found a low-contrast tab hover caused by generic button CSS; the selector was
corrected and the full suite rerun. Visual review also separated table sublabels.
No unexpected external browser request or uncaught page error occurred.
These checks do not close the assistive-technology, cross-browser, zoom or real-device
gaps below and do not constitute WCAG certification.

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
