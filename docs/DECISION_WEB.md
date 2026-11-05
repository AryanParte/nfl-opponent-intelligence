# Decision browser contract and client

Implemented 2026-11-05 as the first P1.9 slice. `web/src/decision.ts` consumes the
existing [Decision API](API.md#decision-request-contract), contract v1. It is not
a new rendered mode: Scout remains the current UI. Navigation, forms and evidence
views follow separately. No package, API, core formula or data source changed.

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
Future React code must still invalidate stale requests after edits/mode changes;
transport cancellation alone does not establish a UI state policy.

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

`tests_api/test_decision_frontend_contract.py` freezes **21 actual HTTP responses**
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
The existing Chromium suite also calls this real client through Vite into FastAPI
on desktop/narrow profiles while Scout remains idle. The existing 71 Scout API
fixtures are unchanged.

Run the normal core/API/browser checks in [WEB.md](WEB.md). To intentionally
regenerate only the Decision fixtures with optional API dependencies installed:

```sh
PYTHONPATH=src python3 -m tests_api.test_decision_frontend_contract > web/src/__fixtures__/decisions.json
```

Review regenerated evidence and rerun the API equivalence test; do not update
expected JSON simply to accept a regression. Final results are in [STATUS](STATUS.md).

## Next bounded unit

Add accessible Scout/Decision Lab navigation and a minimal Decision situation form
(team, season/type, cutoff, exact down and inclusive distance). Use this client for
a basic Run/Pass evidence table with denominators, games, missing states, warnings,
provenance and permanent abstention. Test loading/error/empty/stale response states
and preserve Scout state. Advanced context/baseline/uncertainty controls, user-choice
comparison and downloads can follow as separate units. No ranking/model, new data
layer, database or deployment is implied by this client.
