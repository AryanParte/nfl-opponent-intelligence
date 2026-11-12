# Decision Lab view, browser contract and client

Implemented 2026-11-05 as the first P1.9 slice. `web/src/decision.ts` consumes the
existing [Decision API](API.md#decision-request-contract), contract v1. The first
rendered Decision Lab mode followed on 2026-11-06 in the same app as Scout;
optional field-position controls and exclusion accounting followed on 2026-11-07,
then pre-play score controls on 2026-11-08 and period/clock controls on 2026-11-09.
The optional matched candidate league view followed on 2026-11-10, with bounded
candidate game-support/uncertainty controls and views on 2026-11-11, then optional
user-call selection and fixed descriptive contrasts on 2026-11-12.
No package, API, core formula or data source changed.

## First rendered slice

Select **Decision Lab** in the mode tabs, then submit an offense team code,
season/type, exclusive before-week cutoff, one exact down and inclusive whole-yard
distance bounds. Defaults are inputs, not asserted source coverage. The first
form defaults to unrestricted field position, score and period/clock, with optional
context controls. Comparison defaults off; bootstrap repetitions and seed default
blank. Each feature is opt-in and can be requested independently. It does not offer defense/opponent conditioning, a preferred call,
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

Both views use `useSnapshotRequest.ts`. A query-field edit removes old evidence and
aborts pending work. A mode switch preserves completed states but cancels pending
requests and resets their spinner to idle. Generation checks prevent an ignored
abort from publishing later. A 15-second deadline ends loading independently of
transport settlement; retry is always explicit, and server work may continue
after browser cancellation. Unmount clears timers and aborts requests. Only a
new local validation failure focuses an invalid field; API errors, completion and
returning to an existing validation error do not steal focus.

## Optional user choice and fixed descriptive contrast

**Your call (optional)** is a native Run/Pass radio group with a Clear choice button.
It starts unselected and is independent of `DecisionDraft` and the API query.
Selecting or clearing a call annotates the fixed Run-then-Pass evidence rows with
Your choice / Alternative. It never fetches, cancels an active request, changes the
response, reorders rows, recomputes a statistic or grades the choice. Evidence and
the contrast remain available without a choice. These are observed categories,
including sacks/scrambles in Pass, not verified intended coaching calls.

Any query-field edit clears both choice and evidence, including comparison and
bootstrap edits; restoring the old query value does not restore the old choice.
A same-query retry preserves the choice but hides old/failed evidence. A choice
made while loading annotates the current response only; existing generation guards
still reject late responses after query edits. Mode changes preserve the choice,
with the existing pending-request cancellation policy. Reload clears it; nothing
is sent to the server or saved to persistent browser storage.

`DecisionContrastView.tsx` formats only the validated server-provided
`comparison.descriptive_contrast`. Direction is always **Pass minus Run**, for
selected-offense frequency (pp), EPA/observed play and offensive success (pp),
regardless of the selected call. It is separate from same-call selected-minus-
league differences. Frequency uses the parent play denominator; outcomes require
observed EPA for each candidate. Missing inputs expose each candidate's returned
empty-cohort / unobserved-call / missing-EPA reason, with no league substitution.
Measured zero and negative values remain estimates; a displayed zero can also
reflect rounding. Selection bias is not removed by matching these filters.

The Pass-minus-Run interval remains explicitly **not implemented**. Candidate and
league-difference intervals cannot be substituted or subtracted to supply it.
Mandatory abstention remains visible with or without a choice, including absent
calls and empty cohorts. The [existing policy](DECISION_POLICY.md) is unchanged.
Twenty new component cases use existing actual synthetic HTTP fixtures for signs,
zeros/nulls, unchanged query/evidence, query invalidation, pending/retry behavior,
mode preservation and malformed contrast rejection. Desktop/narrow real-API tests
add native radio/clear keyboard flow, actual signed values, absence/empty reasons,
320-pixel table containment and axe scans. All 69 Decision and 71 Scout fixtures
remain unchanged; these checks verify software, not decision quality.

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
offense accounting in order: field → score → period → clock → down → distance, including only active
optional stages after season/type/exclusive week selection. Each row displays before, missing, outside and after counts from
the API through `DecisionFilterTable.tsx`, which also renders the separate baseline
ledger. Down/distance are required at ingestion, so their missing counts are zero.
Only final distance-stage survivors supply candidate metrics/games; earlier
counts are intermediate. Missing EPA is separate, and stage exclusions already
belong to the global outside-cohort count. Do not sum them into it again.
This is a play cohort, not drive-level red-zone efficiency or a complete game state.
No preferred call is added. The view must be extended with every newly exposed
context stage; it supports field position, pre-play score, period and clock.

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

## Optional pre-play period and clock

`TimeControls.tsx` is shared with Scout, preserving its labels and IDs; Decision
uses separate help IDs and independent state. Q1–Q4 select one regulation quarter;
OT selects every period numbered 5 or higher under the existing cohort contract.
Clock bounds require a period, use inclusive whole seconds remaining within that
period (0–900), and never interpret MM:SS or elapsed/half/game clocks. The source
fields remain `qtr` and `quarter_seconds_remaining`, following the
[nflverse dictionary](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv).
No new source, terms or enrichment is introduced.

Both blank clock ends omit filtering. One entered end defaults its companion to
0 or 900; an explicit 0–900 range excludes missing clocks, unlike period-only
selection. Zero is observed, not missing. Period-only selection works even when
the snapshot has no clock column; requesting an absent context column is an error.
A present but entirely missing requested column may yield an empty cohort.
Clearing the period preserves entered bounds and produces a linked validation
error until the clock bounds are cleared or an explicit period is restored.

The ledger reads the API's `outside_period` for period and `outside_range` for the
other stages, after any field/score selection. Clock receives only period survivors;
a play missing both values is removed once at period. Down/distance still follow:
even the clock-stage count is intermediate. No imputation, automatic widening or
fallback occurs. Q4 excludes OT; Q4 0–120 does not define a game's final two minutes.
OT bounds apply separately within each overtime period, not cumulatively. The
input maximum does not certify season-specific overtime rules. These are historical
cohorts, not complete game states or validated recommendations.

## Optional matched candidate league comparison

**Compare with other offenses** defaults off and uses the existing boolean request
field. Toggling clears stale evidence and aborts pending work; only submission
fetches. Its draft/help IDs are independent of Scout, and returning to a completed
Decision result preserves the comparison without another request. No uncertainty
request is implied by checking comparison.

`DecisionComparisonView.tsx` renders other offenses under the same snapshot,
season/type, exclusive cutoff, exact down, inclusive distance and all requested
context filters/missingness policies. The selected team is excluded as the offense
before situation filtering; its defensive appearances may remain. Matching is not
opponent adjustment, standardization within ranges, complete league coverage or
historical-availability certification. Baseline rates pool plays rather than
averaging team rates. The selected estimates and provenance remain unchanged.

Each fixed Run/Pass section shows selected and baseline plays/games, observed and
missing EPA, count flags and availability. Frequency uses each population's final
play denominator; outcomes use that candidate's observed EPA. Returned differences
are selected minus the **same baseline call**, not Pass minus Run. Rate differences
are percentage points, not percent change. Positive means numerically higher, not
better or significant. Values are formatted only; differences use the API's
unrounded estimates and are never recomputed from displayed rounded cells.

Parent/candidate offense codes and game/shared-game coverage remain separate.
Candidate game/team counts can overlap and must not be summed; shared games and
repeated teams can create dependence. Coverage includes plays missing EPA and does
not measure observed-EPA game support. Count flags are not reliability tests.

Empty selected/baseline populations, unobserved calls, missing EPA and observed zero
stay distinct. Baseline evidence may remain visible when the selected cohort is
empty, but differences are unavailable. An unobserved candidate in a nonempty parent
has zero frequency and unavailable outcomes. No wider cohort, zero outcome or other
fallback replaces unavailable evidence; a preferred call remains withheld.

Baseline accounting first shows eligible temporal plays, selected-offense removals
and the remaining other-offense plays. The shared table then shows active field →
score → period → clock → down → distance counts, each conditional on prior survivors.
Final distance survivors supply baseline metrics/coverage; missing EPA is separate.
These are baseline exclusions, not selected-team missingness or source-wide coverage.
Returned baseline warnings are displayed. Tables retain captions, headers and named
keyboard-focusable horizontal scroll regions.

## Optional candidate support and uncertainty

`BootstrapControls.tsx` is shared with Scout, with independent Decision draft state
and help/error IDs. Repetitions 200–1,000 opt in; an optional uint32 seed defaults to
zero. Both blank omits uncertainty. Text inputs preserve malformed partial values;
a seed without repetitions is an error, including a retained seed after clearing
repetitions. No automatic fetch, retry or silent option removal. Edits cancel stale
browser work but do not guarantee server computation has stopped.

`DecisionUncertaintyView.tsx` consumes the existing candidate block.
`IntervalCells.tsx` shares formatting, support/draw counts and status labels with
Scout without sharing their different metric mappings. Run/Pass tables display
selected, and when requested baseline and paired selected-minus-baseline evidence.
Rates are shown as percentages, rate differences as percentage points; bounds and
point estimates are returned values, never reconstructed in React.

Frequency support counts all parent-cohort games, including games without the call.
Outcome support counts games with observed EPA for that call; candidate point-table
games include missing-EPA plays and are a different count. Both calls use the same
game draws even when `shared_game_weights` is false for selected-only evidence.
With league comparison, both populations also share weights from the game-ID union.
Comparison can change selected bounds through the frame; it does not change points.
Paired differences are formed within draws, not by subtracting marginal endpoints.

The view preserves all five returned interval states: available, undefined, fewer
than five contributing games, fewer than 95% defined draws, and degenerate bounds.
The separate below-20-games flag is a warning, not a reliability guarantee. Withheld
bounds do not mean zero uncertainty; undefined estimates stay unavailable. Empty
frames perform zero draws, while a baseline-only frame can still perform draws.
More repetitions add no observed games. These are exploratory nominal 95% pointwise
bounds, not calibrated confidence, significance tests or predictions. No contrast
interval or preferred call is introduced, including when bounds exclude zero.

Method/RNG/quantile, seed, frame size, performed/requested draws and all warnings
remain visible. Replay still needs source/cohort/runtime identity. Keyboard-focusable
tables expose support and interval status on narrow screens. See the existing
[analytical contract](DECISION_CONTRACT.md#optional-candidate-uncertainty) for the
procedure and unaddressed dependence, missingness and source/model limitations.

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

`tests_api/test_decision_frontend_contract.py` freezes **69 actual HTTP responses**
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

Seventeen time fixtures add period-only/absent-clock-column, all regulation
quarters, pooled OT, zero/equal/one-sided/full/empty bounds, all-missing contexts,
combined filters and a final distance-stage empty cohort. All prior 42 Decision
fixtures and 71 Scout fixtures (58 standard and 13 uncertainty) remain unchanged.
Independent expectations reconcile all six active stages to final candidates.
Clearing-clock and clearing-time tests hold snapshot and earlier filters fixed;
mutations reject wrong clock sources/timing, bounds, missing policies and ledgers.
The browser checks 15 → 12 → 11 → 5 → 3 survivors, period-only versus explicit
full-clock missingness, OT, zero clock, recovery, mode state and keyboard scrolling.
These synthetic tests verify implementation, not statistical or football validity.

Five league fixtures add an unequal three-offense mix, its same-snapshot comparison-
off counterpart, all-baseline/all-selected missing EPA and an unobserved selected
Run. All 59 prior Decision values and 71 Scout fixtures remain unchanged. Independent
expectations distinguish pooled rates from team means, candidate/parent coverage,
shared games and signed differences. Twenty-two new component cases cover off/on/off,
empty/missing states, separate six-stage counts, OT, stale responses, mode preservation,
safe errors and invalid baseline rejection. The browser tests same-source off/on/off,
hand-counted selected/baseline evidence, empty states, keyboard toggling and narrow
comparison/accounting scrolling. These synthetic outcomes are software checks.

Five uncertainty fixtures add same-snapshot selected/league uncertainty-off counterparts,
combined contexts, maximum request/seed and selected-only empty-frame behavior.
All prior 64 Decision values and 71 Scout fixtures are unchanged. Thirty-nine new
component cases cover unchanged points across off/on/off, parent versus candidate
support, every interval state, the controlled 189/200 versus 190/200 valid-draw gate,
paired differences/units, maximum/invalid inputs, safe errors, stale responses and
independent mode state. Controlled draws stay explicitly labeled, not seed replays.
Real browser checks use the actual API for optional comparisons, sparse/empty
support, input correction, point preservation, keyboard flow and 320-pixel scrolling.

Run the normal core/API/browser checks in [WEB.md](WEB.md). To intentionally
regenerate only the Decision fixtures with optional API dependencies installed:

```sh
PYTHONPATH=src python3 -m tests_api.test_decision_frontend_contract > web/src/__fixtures__/decisions.json
```

Review regenerated evidence and rerun the API equivalence test; do not update
expected JSON simply to accept a regression. Final results are in [STATUS](STATUS.md).

## Next bounded unit

Add a Decision JSON download for the current validated `DecisionDocument.json`.
Preserve the original decoded response text, full provenance, contexts, warnings,
contrasts, baselines and uncertainty; do not reserialize or add the local choice.
Reuse the Scout object-URL lifecycle where practical, with distinct safe filenames
and help IDs. Show a ready-only link; invalidate it on query changes/errors and
revoke owned URLs on replacement/unmount, while preserving completed downloads
across mode switches and call-choice edits. Test native downloads, exact text,
failed preparation, stale responses and Scout compatibility. No new request,
statistics, data source, model, storage or deployment.
