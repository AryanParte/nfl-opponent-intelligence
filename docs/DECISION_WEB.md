# Decision Lab view, browser contract and client

Implemented 2026-11-05 as the first P1.9 slice. `web/src/decision.ts` consumes the
existing [Decision API](API.md#decision-request-contract), contract v1. The first
rendered Decision Lab mode followed on 2026-11-06 in the same app as Scout;
optional field-position controls and exclusion accounting followed on 2026-11-07,
then pre-play score controls on 2026-11-08. No
package, API, core formula or data source changed.

## First rendered slice

Select **Decision Lab** in the mode tabs, then submit an offense team code,
season/type, exclusive before-week cutoff, one exact down and inclusive whole-yard
distance bounds. Defaults are inputs, not asserted source coverage. The first
form defaults to unrestricted field position and score, with optional inclusive
bounds for both. Period/clock stay unrestricted, comparison off and bootstrap
unrequested. It does not offer defense/opponent conditioning, a preferred call,
user-call grading or advanced play families.

`DecisionLab.tsx` renders the validated selected-offense population and fixed Run,
then Pass rows. Frequency uses parent eligible plays; outcomes use candidate
observed EPA. It displays games (which can overlap between candidates), observed/
missing EPA, count flags and the returned threshold. Empty parent, unobserved call,
missing EPA and measured zero remain distinct. All warnings, timestamps, source
label, attribution and hashes are visible through the shared `SourceView`.
The view explicitly withholds a preferred call even when one point estimate is
larger, and labels these categories as observed plays rather than verified intent.
No formula, model, contrast interval or fallback cohort is introduced.

`App.tsx` uses manual-activation tabs following the
[WAI-ARIA tabs pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/): named tabs
and panels, selected/tab-stop states, Left/Right wrapping, Home/End focus movement,
Enter/Space activation and an active-mode skip link. Visited views stay mounted
under `hidden` so drafts, completed evidence, expanded details and Scout's existing
download URL survive mode changes, consistent with
[React state preservation](https://react.dev/learn/preserving-and-resetting-state).
Only the active panel participates in keyboard/accessibility navigation; the
Decision form is first mounted on its initial visit. Reloading the page resets
in-memory state; no persistent browser storage was added.

Both views use `useSnapshotRequest.ts`. A control edit removes old evidence and
aborts pending work. A mode switch preserves completed states but cancels pending
requests and resets their spinner to idle. Generation checks prevent an ignored
abort from publishing later. A 15-second deadline ends loading independently of
transport settlement; retry is always explicit, and server work may continue
after browser cancellation. Unmount clears timers and aborts requests. Only a
new local validation failure focuses an invalid field; API errors, completion and
returning to an existing validation error do not steal focus.

## Optional pre-play field position

`FieldPositionControls.tsx` is shared with Scout; Decision uses distinct help IDs
and independent draft state. Inputs remain text so an invalid partial decimal
cannot become a blank, unfiltered request. Both blank means no field filter.
One entered bound defaults the other end to 0 or 100; equal and fractional bounds
are valid, and zero is observed rather than missing. Any explicit range, including
0–100, excludes missing positions. Coordinates are yards to the offense's
opponent's goal line: 20 is the opponent's 20, 80 is the offense's own 20, following
the [nflverse field definition](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv).

`DecisionContextView.tsx` renders the validated effective bounds and selected
offense accounting in order: field → score → down → distance, including only active
optional stages after season/type/exclusive week selection. Each row displays before, missing, outside and after counts from
the API. Down/distance are required at ingestion, so their missing counts are zero.
Only final distance-stage survivors supply candidate metrics/games; earlier
counts are intermediate. Missing EPA is separate, and stage exclusions already
belong to the global outside-cohort count. Do not sum them into it again.
This is a play cohort, not drive-level red-zone efficiency or a complete game state.
No preferred call is added. The view must be extended with every newly exposed
context stage; it currently supports field position and pre-play score.

## Optional pre-play score difference

`ScoreControls.tsx` and the `scoreRange` presentation helper are shared with Scout;
Decision retains separate draft state and help/error IDs. Inclusive signed whole
points range from −1000 to +1000, the API input limits rather than typical scores.
Both blank means no score filter. One blank end is unbounded (JSON null), not a
zero/default maximum. A 0–0 range selects known ties; a requested range always
excludes missing pre-play scores. Invalid signs, decimals and exponents remain
visible text and cannot silently become an unfiltered request.

Score means offense points minus defense points at play start, following the
[nflverse dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv).
Negative is trailing, positive leading. There is no post-play substitution, inferred
possession, neutral-game definition or win-probability claim. The API retains the
exclusive historical cutoff and mandatory abstention.

When both filters apply, field precedes score. Score missingness counts only field
survivors; a play missing both is excluded once at field. The same ledger then
shows down/distance, so the score-stage count is still intermediate. Missing EPA
remains separate. An absent requested score column is an error; a present column
with all missing values may return an empty cohort. Clearing score bounds preserves
field selection and requires a new explicit request, with no stale or fallback result.

## Request and response boundaries

`parseDecisionQuery` accepts a complete `DecisionDraft`: string controls (blank
for unused optional fields), plus boolean `compare_league`. It reuses Scout's
common field validation and adds required integer down 1–4, inclusive distance
0–100 and optional count-warning threshold 1–100,000 (default 30). Clock bounds
require a period. Bootstrap requests stay opt-in at 200–1,000 repetitions with an
optional uint32 seed. `DecisionQueryValidationError.fields` identifies controls;
missing companion fields identify the companion, such as period or repetitions.

`fetchDecisionDocument` independently validates the typed query at runtime and
copies it before awaiting. Only supported fields reach `/api/v1/decision`; callers
cannot supply a filesystem path, URL, defense role, opponent, model or play family.
The development proxy allows exactly the Scout and Decision routes. It still
binds to loopback and cannot serve surrounding snapshots as assets.

The client forwards an `AbortSignal`, omits credentials, disables caching and
rejects redirects. It checks HTTP success and JSON content type, maps known API
errors to fixed messages, and never displays raw server exceptions. Invalid JSON
gets a safe error. Transport/cancellation errors propagate; there is no automatic
retry, cohort widening or synthetic fallback. These choices follow the browser's
[Fetch response and cancellation semantics](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch).
The shared React request hook supplies the stale-response policy described above;
transport cancellation alone is insufficient.

`parseDecision` checks the consumed wire contract before returning the original
object. Shared source guards in `contract.ts`, context checks in `report.ts` and
interval guards in `uncertainty.ts` preserve Scout's existing behavior. Checks cover:

- Exact requested season/type/exclusive week/down/distance and optional contexts;
  ordered missingness/exclusion ledgers with no implicit widening.
- Run then Pass, the `qb_dropback` mapping and explicit labels including
  sacks/scrambles. Candidate plays partition the parent; games may overlap.
- Frequency against all parent plays, versus candidate observed-EPA denominators
  for EPA/success. Empty parent, unobserved candidate and missing EPA stay distinct;
  zero is not substituted for an unavailable outcome.
- Requested-only leave-team-out baseline and uncertainty blocks; matching cohort,
  baseline team coverage, selected-minus-baseline units and declared differences.
- Parent-game frequency support versus candidate observed-EPA game support;
  shared-game union, method/seed, valid/undefined draws and all five interval states.
  The browser does not resample or reconstruct intervals from endpoints.
- Immutable-manifest hash/timestamp/season consistency, source labels, attribution
  and warnings. This checks declared provenance, not snapshot bytes in the browser.
- `descriptive_only_v1` abstention, null preferred call and deferred opponent
  evidence, even with available means/intervals. Pass-minus-Run is descriptive;
  its contrast interval remains explicitly unimplemented.

Count identities and declared difference arithmetic are validation checks. The
client returns the server's estimates unchanged; it never fills in missing values,
generates predictions or derives a recommendation. `DecisionDocument.json` retains
the original decoded response text for a later download flow: reserialization in
JavaScript can change numeric lexemes. The typed view does not certify unconsumed
manifest metadata, source completeness, causal validity or historical availability.

## Reproducible evidence

`tests_api/test_decision_frontend_contract.py` freezes **42 actual HTTP responses**
in `web/src/__fixtures__/decisions.json`. Observations, source IDs/timestamps and
labels are explicitly synthetic; fixtures never enter the live app. Snapshot bytes
and hashes are created with the existing factory, and acquisition/socket calls are
blocked. Two labeled cases deliberately control resampling draws to hit the
95% valid-replicate boundary; they are not claimed to replay their seed.

The fixtures cover selected-only/league, REG/POST, empty selected/baseline/parent,
absent calls, missing EPA, distance ranges, combined contexts, zero clock, overtime
and all interval statuses. Frontend tests include hand-counted point expectations,
malformed/mismatched payloads, denominator/provenance/policy mutations, bounded
requests, safe HTTP errors, cancellation and query mutation during a request.
Two additional responses cover empty/missing-EPA cases without optional comparison,
matching the initial form. Component tests cover fields/focus, exact narrow queries,
all missing states, zero outcomes, safe errors, mandatory abstention, edits, ignored
aborts, deadlines, unmount and preservation of both modes. Chromium exercises the
rendered form through Vite into FastAPI on desktop/narrow profiles, checks
hand-counted synthetic outcomes, keyboard tabs/forms and 320-pixel table containment,
and scans idle/invalid/error/empty/loaded states with axe. Screenshots are inspected;
automated scans do not establish accessibility conformance or screen-reader support.
The existing 71 Scout API fixtures are unchanged.

Seven field-position fixtures add partial/default/full/fractional/zero/lower-only,
all-missing and empty cases with hand-counted stage expectations. They preserve
all 23 previous Decision fixture values. Tests reject mismatched bounds, missing
ledgers, broken counts/order and late responses; a missing context column stays
an error. Real browser tests verify the filtered synthetic sample, invalid-input
recovery, keyboard order, independent Scout state and a focusable 320-pixel
accounting table. Clearing both bounds restores an explicitly requested unrestricted
cohort; an empty response never silently widens its query.

Twelve score fixtures add inclusive/one-sided/tied/input-limit/all-missing/empty/
missing-EPA/combined cases and filter removal within the same synthetic snapshot.
All 30 prior Decision fixtures remain unchanged. Independent stage counts cover
conditional missingness and a final distance-stage empty result; mutation tests
reject wrong signs/perspective/bounds/order/chains. Real browser tests reconcile
15 → 12 → 11 plays under combined field/score selection, then verify known ties,
empty and cleared-bound recovery, mode state, keyboard order and 320-pixel scrolling.
These invented outcomes verify the software, not football performance.

Run the normal core/API/browser checks in [WEB.md](WEB.md). To intentionally
regenerate only the Decision fixtures with optional API dependencies installed:

```sh
PYTHONPATH=src python3 -m tests_api.test_decision_frontend_contract > web/src/__fixtures__/decisions.json
```

Review regenerated evidence and rerun the API equivalence test; do not update
expected JSON simply to accept a regression. Final results are in [STATUS](STATUS.md).

## Next bounded unit

Add optional period/clock controls using existing validation: Q1–Q4/OT and inclusive
seconds remaining, with clock requiring a period. Extend the ledger to active
field → score → period → clock → down → distance; test missing periods/clocks,
zero clock, OT, bounds and empty/stale states. Candidate league/interval views, user-choice
comparison and downloads follow separately. No ranking/model, new data layer,
database or deployment is implied by this view.
