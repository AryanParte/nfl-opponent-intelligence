# Local snapshot evidence API

The optional HTTP service exposes **GET `/v1/report`** (Scout schema v2) and
**GET `/v1/decision`** (Run/Pass contract v1, added 2026-11-04). Both reuse the
existing core builders and the same verified resident PBP snapshot. It is a
read-only local service,
not a deployment or a new statistical model. There is no database,
authentication, CORS policy, remote data selector, or HTTP ingestion command.
Only the operator chooses a snapshot, before startup. The offline CLI still
requires only Python's standard library.
The optional [local browser viewer](WEB.md) uses a loopback Vite proxy; this API
does not serve frontend assets and its CORS policy was not changed for that view.

## Install and start

Alternatively, use the [pinned API container](CONTAINER.md) with the same required
snapshot/source-label configuration. Its non-root single worker reads a read-only
mount; the image contains no data or frontend. The Python install below remains
optional and unchanged.

From the repository root, with Python 3.11–3.13:

```sh
python3 -m venv .venv/api
.venv/api/bin/python -m pip install -c requirements/api-constraints.txt '.[api]'

export NFL_OI_SNAPSHOT="$PWD/data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06"
export NFL_OI_SOURCE_LABEL='nflverse 2024 retrospective snapshot; acquired 2026-09-30 UTC'
.venv/api/bin/python -m uvicorn opponent_intelligence.api:app_from_env \
  --factory --host 127.0.0.1 --port 8000
```

Installation needs package-network access. The named snapshot must already exist;
see [explicit acquisition](INGESTION.md). The example identifies the originally
recorded bytes, not whatever upstream serves today. Use your actual immutable
directory and an accurate source label if acquisition yields a different revision.
Configuration requires an absolute directory and a nonblank label of at most 300
characters. Neither is accepted from a request. Do not point at `current.json`.

Startup verifies the manifest, archive/decoded hashes, row seasons and adapter
contract through `load_snapshot`, then keeps that parsed dataset for the lifespan
of this application. Missing/corrupt input or oversized data aborts startup; there
is no silent download or fallback. Subsequent requests do not reread files or
follow cache pointers. Changing source bytes, environment variables or pointers
does not replace the resident dataset: stop and restart with explicit configuration.
This is application-level snapshot isolation, not an OS write-protection mechanism.

Run one worker on loopback for this slice. Do not expose it publicly: query limits
are not authentication, rate limiting, transport security or a deployment review.
The service makes no network acquisition calls. `/openapi.json` documents its
transport schema; interactive `/docs` and `/redoc` pages are disabled.

## Scout request contract

```sh
curl --get 'http://127.0.0.1:8000/v1/report' \
  --data-urlencode 'team=CAR' --data-urlencode 'season=2024' \
  --data-urlencode 'before_week=19'
```

The route version (`v1`) and analytical report version (`schema_version: 2`) are
different contracts. Query names use underscores, not the CLI's hyphens. All
options apply to the single configured snapshot, never to request-selected files.

| Query parameter | Contract / default |
| --- | --- |
| `team` | Required; 2–3 uppercase ASCII letters, e.g. `CAR`. No alias normalization or team registry lookup. |
| `season` | Required integer, 1999–9999; must equal the snapshot's season. Current ingestion supports only 2024. |
| `before_week` | Required integer, 1–23; **exclusive** cutoff in the existing nflverse week numbering. |
| `side` / `season_type` | `offense` or `defense` (default `offense`); `REG` or `POST` (default `REG`). |
| `minimum_plays` | Integer 1–100,000; default 30. Warning threshold, not a filter or an uncertainty guarantee. |
| `yardline_min` / `yardline_max` | Optional finite numbers 0–100, inclusive distance to the offense's target goal line. |
| `score_min` / `score_max` | Optional whole points, inclusive, from -1,000 to 1,000; offense minus defense, including in defense mode. These are API safety bounds, not possible-score claims. |
| `period` | Optional `Q1`, `Q2`, `Q3`, `Q4`, or `OT`; the latter includes all overtime periods. |
| `clock_min` / `clock_max` | Optional whole seconds remaining 0–900 inclusive; requires `period`. Zero is observed, not missing. |
| `compare_league` | Exactly lowercase `true` or `false`; default `false`. No `1`, `True`, or implicit truthiness. |
| `bootstrap_repetitions` | Optional integer 200–1,000. Omit for no uncertainty calculation; API cap is intentionally below the CLI's 10,000. |
| `bootstrap_seed` | Optional integer 0–4,294,967,295; requires repetitions. Builder defaults to seed 0 when repetitions alone are supplied. |

Minimums must not exceed their maximums. Omitted field/score ends are unbounded;
clock ends default to 0/900 when a clock range is requested. Missing required
context columns are errors. Missing values in present columns are excluded only
by requested filters, with the existing ordered ledgers retained. See
[metric definitions](METRICS.md) and [uncertainty](UNCERTAINTY.md).

Unknown parameters (including paths, URLs, source labels and refresh flags),
duplicate parameters (including encoded duplicate names), request bodies and
non-GET methods are rejected. The raw query string is limited to 2,048 bytes,
before URL decoding. Trailing slashes are not redirected.

## Decision request contract

```sh
curl --get 'http://127.0.0.1:8000/v1/decision' \
  --data-urlencode 'team=CAR' --data-urlencode 'season=2024' \
  --data-urlencode 'before_week=19' --data-urlencode 'down=3' \
  --data-urlencode 'distance_min=4' --data-urlencode 'distance_max=4' \
  --data-urlencode 'compare_league=true'
```

Decision requests use the same required `team`, `season`, `before_week`, optional
context bounds, season type, count-warning threshold, comparison and bootstrap
options as Scout, **except `side` is not accepted**. Decision evidence is offense-only;
defense remains a Scout report. Three additional parameters are required:

| Query parameter | Contract |
| --- | --- |
| `down` | Integer 1–4; exact recorded down. |
| `distance_min` / `distance_max` | Integers 0–100, inclusive and ordered; equal bounds select exact yards to go. |

There is no inferred distance bucket, automatic cohort widening or sparse-data
fallback. Field position and score remain offense-relative; period/clock select
historical observations, not a rules-valid future game state. Fourth down still
means evidence **conditional on eligible Run/Pass plays**, not go/punt/field-goal
values. See the [decision contract](DECISION_CONTRACT.md) for candidate mapping,
ordered exclusion ledgers and denominator semantics.

This is HTTP text parsing into the core `DecisionRequest`, not a change to its
strict Python argument types. Cost bounds match Scout: at most 1,000 resamples,
seed 0 by default when repetitions are supplied, 2,048 raw query bytes, no duplicate
keys or bodies. `side` (even `offense`), opponent, candidate/play-family, charting,
model, path, URL, source-label and refresh options are rejected before analytics.
A valid-looking charting column in the snapshot does not admit a new filter.

## Response and errors

Successful Scout JSON is the builder's report, with source fingerprints/manifest,
cohort, metric context, data quality, overall counts/rates, situations and warnings.
Optional comparison/uncertainty blocks remain absent unless requested; measured
nulls are retained. The HTTP model validates the exact top-level v2 envelope,
source shape and typed overall/situation metrics. Variable context, provenance
and method dictionaries remain JSON objects governed by the existing core
contracts, not independently reimplemented statistical validation in OpenAPI.

Successful Decision JSON is exactly the builder's contract v1: `evidence_kind`,
source/manifest, cohort, metric context, estimation policy, population, data quality,
Run then Pass candidates, comparison policy and warnings. Optional matched league
and uncertainty blocks remain absent unless requested. No model is executed or
model version invented: the response identifies descriptive observed calls and
`descriptive_only_v1`; source/model admission remains separately gated.

The Decision response model validates the envelope, source, nonnegative counts,
finite outcome/rate values, availability labels, two ordered candidates in selected
and baseline evidence, and the existing mandatory abstention fields. Variable
context, method and contrast dictionaries stay governed by core tests; the HTTP
layer does not repeat statistical calculations. Invalid output fails with a
sanitized 500, including any non-null preferred candidate. In particular:

- Empty cohorts return 200 with zero plays, null frequencies/outcomes and explicit
  reasons. A candidate absent from a nonempty cohort has frequency zero but null
  outcomes. All-missing candidate EPA preserves frequency and withholds outcomes.
- Candidate frequency uses all eligible cohort plays; candidate EPA and success
  use only that candidate's observed EPA. Games may overlap across candidates.
- `comparison.status` stays `insufficient_evidence`, with a null preferred call,
  regardless of count flags, mean differences, baselines or exploratory intervals.
  Descriptive contrasts are not causal, predictive or coaching recommendations.
- A Decision result is not Scout schema v2 and must not be sent to the Scout
  brief renderer. The existing React viewer consumes Scout and Decision in separate modes.

Empty cohorts return **200**, zero counts, null rates and the builder's warnings,
not 404. A syntactically valid but absent team such as `ZZZ` also gives an empty
cohort; it is not evidence that the team exists. Defense EPA remains opposing
offensive EPA, not sign-reversed defensive value. A returned retrospective
snapshot is not proof that the same information was available before the cutoff.

Errors always have the application envelope below (server/proxy failures outside
the application are not covered):

```json
{"error":{"code":"invalid_query","message":"Invalid report query; see the request contract.","fields":["before_week"]}}
```

| HTTP status | Error code | Meaning |
| --- | --- | --- |
| 400 | `body_not_supported` | Requests use query parameters only. |
| 414 | `query_too_long` | Raw query exceeds 2,048 bytes. |
| 422 | `invalid_query`, `duplicate_parameter` | Invalid/missing/extra options or repeated keys. |
| 422 | `season_unavailable`, `context_unavailable` | Snapshot season differs or required context columns are absent. |
| 503 | `report_busy` | Either a Scout or Decision builder is active; `Retry-After: 1` suggests a retry, not a completion guarantee. The code is retained for existing Scout clients. |
| 503 | `snapshot_not_ready` | Application lifespan has not loaded the snapshot. |
| 404 / 405 | `not_found` / `method_not_allowed` | Unknown route or method; 405 retains the `Allow` header. |
| 500 | `internal_error` | Unexpected builder/response-validation failure; no partial report. |

`fields` lists query names recognized **by the requested route**, or missing source columns for
`context_unavailable`; cross-field/unknown-option errors may have an empty list.
Rejected values, unknown keys, file paths, exception text and tracebacks are not
echoed. Operator-side server logs may contain diagnostic exceptions.

## Resource boundaries and limits

Startup permits at most 100,000 raw rows and 300 distinct eligible game IDs.
Those policies accommodate the pinned season and limit report work; they are
checked **after parsing**, not a streaming memory cap. The existing snapshot
loader separately bounds archive/decoded byte sizes. Larger-than-memory loading
is still unimplemented. Resampling is opt-in and capped at 1,000 repetitions.

The synchronous routes run in the framework's worker pool. One shared nonblocking lock
allows one builder across **both** routes per application instance and rejects overlapping
builders instead of queueing them; cleanup releases the slot after errors. It is
not a cross-process lock, a cap on all HTTP connections, a hard CPU deadline or a
measured throughput promise. Adding workers multiplies memory and concurrency.
Snapshot season/context validation and builder exceptions release that same slot.
Response serialization is outside the builder gate. No database, background
queue, result cache, deployment or general-purpose report service was added.

## Verification and replay

Core tests still need no installation; API tests use explicitly synthetic snapshots
with socket connections and the acquisition URL opener blocked:

```sh
.venv/api/bin/python -m pip install -c requirements/api-constraints.txt '.[api,test-api]'
.venv/api/bin/python -m pip check
PYTHONPATH=src .venv/api/bin/python -m unittest discover -s tests -v
PYTHONPATH=src .venv/api/bin/python -W error -m unittest discover -s tests_api -v
```

The constraints pin tested runtime/test versions, not wheel hashes or isolated
build tools. API extras are separate from dependency-free core CI jobs.
Starlette's current test client uses `httpx2`; the deprecated `httpx` fallback is
not needed. Tests run on Python 3.11/3.12/3.13 and cover response equivalence plus
independent counts, roles, empty cohorts, nulls, cutoffs, missing context, invalid
inputs, schema rejection, sanitized errors, startup integrity, in-memory source
stability, resource bounds and actual overlapping requests. A core subprocess
uses `-S` to prove the CLI works with site-package dependencies disabled.

On 2026-10-08 the pinned real snapshot's CAR/2024/REG/before-19 response, with
comparison, 1,000 resamples and seed 20261006, exactly matched the committed
[historical report](examples/car-2024-reg-before-week-19.report.json) under sorted
JSON serialization (including numeric types). Ten further offense/defense and
field/score/clock combinations matched the existing builder. Network was blocked
for these in-process replay checks. A separate real Uvicorn factory smoke test
on loopback returned 200 and the expected 984 plays; its process was then stopped.
This is transport integration evidence, not another independent raw-data audit,
statistical calibration, performance benchmark or deployed-service claim.

To replay the frozen report against the running service:

```sh
curl --silent --show-error --fail \
  'http://127.0.0.1:8000/v1/report?team=CAR&season=2024&before_week=19&compare_league=true&bootstrap_repetitions=1000&bootstrap_seed=20261006' \
  | python3 -c 'import json, pathlib, sys; actual=json.load(sys.stdin); expected=json.loads(pathlib.Path("docs/examples/car-2024-reg-before-week-19.report.json").read_text()); assert json.dumps(actual,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False); print("Exact canonical JSON match")'
```

Primary framework references reviewed 2026-10-08:
[FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/),
[query models and extra-field rejection](https://fastapi.tiangolo.com/tutorial/query-param-models/),
[error handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/),
[response models](https://fastapi.tiangolo.com/tutorial/response-model/), and
[Starlette TestClient/lifespan and httpx2](https://starlette.dev/testclient/).

### Decision transport verification — 2026-11-04

Nineteen new offline API tests cover full core-result equivalence, hand-counted
Run/Pass outcomes, missing/empty states, cutoffs, context filters, league evidence,
seeded uncertainty (withheld and supported intervals), request bounds, unsupported
inputs, shared snapshot stability, cross-route contention in both directions,
capacity recovery and sanitized response errors. A core subprocess additionally
builds decision evidence with `python -S`, keeping web dependencies optional.
Existing Scout API/browser fixtures remain unchanged.

The eight requests in the unchanged [pinned decision-audit receipt](evidence/pbp-2024-23370d5d10f8.decision-audit.json)
also passed through this endpoint with network access blocked. Sorted JSON matched
the direct core builder exactly, including numeric types; counts, candidate means,
baselines and uncertainty summaries matched the frozen independent audit within
its existing absolute tolerance. This is transport verification on retrospective
data, not another model/calibration audit, performance benchmark or availability claim.
The same already acquired snapshot, hashes and license records were reused.

To reproduce the eight HTTP/core comparisons in-process with the optional API/test
dependencies installed, run from the repository root (no local server required):

```sh
PYTHONPATH=src .venv/api/bin/python - <<'PY'
import json
from pathlib import Path
from fastapi.testclient import TestClient
from opponent_intelligence.api import create_app
from opponent_intelligence.decision import DecisionRequest, build_decision_evidence
from opponent_intelligence.ingestion import load_snapshot
snapshot = Path('data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06').resolve()
cases = json.loads(Path('docs/evidence/pbp-2024-23370d5d10f8.decision-audit.json').read_text())['cases']
dataset = load_snapshot(snapshot)
label = 'nflverse 2024 retrospective snapshot; local transport replay'
with TestClient(create_app(snapshot=snapshot, source_label=label)) as client:
    for case in cases:
        request = case['request']
        params = {k: str(v).lower() if isinstance(v, bool) else v for k, v in request.items()}
        response = client.get('/v1/decision', params=params)
        assert response.status_code == 200, response.text
        expected = build_decision_evidence(dataset, DecisionRequest(**request), source_label=label)
        assert json.dumps(response.json(), sort_keys=True, allow_nan=False) == json.dumps(expected, sort_keys=True, allow_nan=False)
        print(case['id'], 'matches core JSON')
PY
```

Framework query/response references above were rechecked on 2026-11-04, alongside
[Pydantic after-model validation](https://docs.pydantic.dev/latest/concepts/validators/).
Pinned dependencies were reused; no package upgrade was needed.
