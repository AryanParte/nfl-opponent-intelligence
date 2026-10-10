# Engineering status

As of the scheduled run on 2026-10-10, P1.4's local viewer adds an opt-in matched
league comparison over the existing snapshot API. It shows observed coverage,
selected/baseline denominators, same-bucket metrics, signed differences, missing/
empty states and every baseline warning. The checkbox uses the existing explicit
submit/cancel/stale-response flow. See [viewer setup and evidence](WEB.md).
All 196 core and 21 API tests pass locally on Python 3.11/3.12/3.13; 99 frontend
tests, type-check/build and real-snapshot browser checks pass on Node 24.19.0.
No formulas, API routes, report defaults, raw bytes, database, deployment or daily
automation changed. The core CLI still needs no third-party dependencies.

P1.3 remains complete within its PBP-only scope; personnel/motion enrichment is
deferred under the [source decision](PERSONNEL_MOTION.md), not inferred from
shotgun/no-huddle or text. P1.2 stays complete for the pinned snapshot. Calibration,
cross-game dependence, opponent adjustment, historical information availability,
richer UI controls and deployment remain open. Reports are descriptive, not two-team
projections or validated scouting recommendations.

## Canonical repository and migration

- Remote: https://github.com/AryanParte/nfl-opponent-intelligence
- Stable clone: `/Users/aryanparte/Documents/nfl-opponent-intelligence`
- Working branch: `codex/league-comparison-view`, started from updated
  `origin/main` at `fcba137` after observing PR #14 merged. Continue this branch's
  existing PR while unmerged; do not merge or enable auto-merge. The prior checkout
  was clean and matched its upstream, with no unpublished commits. Only `main`
  remained on the remote; no open PRs or review feedback remained. History is preserved.
- Publication/remote verification for this unit: consult the PR for
  `codex/league-comparison-view` for its exact published SHA, attribution and CI
  receipt. Local checks below are not a claim that remote CI has run.
- Previous viewer review: [PR #14](https://github.com/AryanParte/nfl-opponent-intelligence/pull/14),
  merged at `fcba137`; the merge tree matches feature head `01cb6cd`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37989125545)
  passed all seven jobs. No open PRs/reviews remained and the prior checkout was
  clean, matching upstream. Baseline 196 core / 21 API / 51 frontend tests passed.
- Previous API review: [PR #13](https://github.com/AryanParte/nfl-opponent-intelligence/pull/13),
  merged at `39af171`; its tree matches final feature head `495b0e2`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37861277858)
  passed all six jobs. The previous checkout was clean and matched its upstream;
  no open PRs or relevant review feedback remained. All 196 core / 20 API baseline
  tests passed locally before this unit. Earlier missing automatic runs are
  historical observations, not a blocker observed in this run.
- Previous availability review: [PR #12](https://github.com/AryanParte/nfl-opponent-intelligence/pull/12),
  merged at `9f9a647`; its tree exactly matched final feature head `62bdcc1`.
  [Final-head CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37830532360)
  was rechecked as successful. No new merged-main run was present at this manual
  run's start; all 195 baseline tests passed locally before development.
- Previous brief review: [PR #11](https://github.com/AryanParte/nfl-opponent-intelligence/pull/11),
  merged at `5fd1adc`; its tree exactly matched final feature head `955bc2d`.
  [Final-head CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37694474942)
  was rechecked as successful. No new merged-main CI run was present at this run's
  start; the baseline 181 tests passed locally before development.
- Previous uncertainty review: [PR #10](https://github.com/AryanParte/nfl-opponent-intelligence/pull/10),
  merged at `07ee523`; final feature-head CI passed at `624aa81`. Its merge tree
  exactly matched that verified feature head. No new merged-main run was present
  at this run's start; the baseline 161 tests passed locally before development.
- Previous comparison review: [PR #9](https://github.com/AryanParte/nfl-opponent-intelligence/pull/9),
  merged at `af19425`; merged-main CI passed on that exact SHA.
- Previous clock review: [PR #8](https://github.com/AryanParte/nfl-opponent-intelligence/pull/8),
  merged at `bbf4299`; final-head CI passed at `d82316a`.
- Previous score review: [PR #7](https://github.com/AryanParte/nfl-opponent-intelligence/pull/7),
  merged at `7f4bfb3`. Its final-head CI passed at `98bd84d`; the preceding branch
  was clean and matched upstream. No open PRs or review feedback remained at this
  run's start.
- Previous field-position review:
  [PR #6](https://github.com/AryanParte/nfl-opponent-intelligence/pull/6), merged at
  `5d12321`. Its final-head CI passed; no open PRs or review feedback remained at
  this run's start. The clean preceding branch matched its upstream exactly.
- Previous defense-side review:
  [PR #5](https://github.com/AryanParte/nfl-opponent-intelligence/pull/5), merged at
  `de354ac`. No open PRs or review feedback remained at this run's start.
- Previous analytical integration review:
  [PR #4](https://github.com/AryanParte/nfl-opponent-intelligence/pull/4), merged at
  `8ed98e6`.
- Previous acquisition review: [PR #3](https://github.com/AryanParte/nfl-opponent-intelligence/pull/3),
  merged at `78623c6`.
- Previous review: [PR #2](https://github.com/AryanParte/nfl-opponent-intelligence/pull/2),
  merged on 2026-09-29.
- Migration review: [PR #1](https://github.com/AryanParte/nfl-opponent-intelligence/pull/1),
  merged on 2026-09-29. Inspect current open PRs before selecting new work.
- Preserved foundation commit: `ba72f50700ff77f031e738f64c55217ffd5ad59c`
- Review base: `main`, initially seeded with that exact preserved snapshot.
- Author/committer: `Aryan Parte <134340600+AryanParte@users.noreply.github.com>`;
  GitHub's commit API confirms both are linked to `AryanParte`.

No earlier commits existed. All original project files were captured in the
foundation commit, pushed, and recovered by cloning GitHub into the stable path.
The initial clone matched the original files byte-for-byte excluding Git metadata
and Python caches. Local/remote branch SHAs matched, and all 18 tests passed from
the stable clone. Future work continues here; the old outputs checkout is retired.

The existing `daily-sports-portfolio-engineering` task remains active at 8 AM
America/New_York. Its prompt now requires remote sync, stable-clone recovery,
verified commit identity, one meaningful unit, tests, complete-diff self-review,
updated documents, commit, push, remote-SHA verification, and PR review.
This run did not modify, duplicate, disable, or reschedule it.

## Verification

### P1.4 comparison viewer — 2026-10-10

The frontend suite now has 99 tests. Seven new endpoint-generated synthetic
fixtures expand the existing three to cover comparison on/off, both roles, no
selected observations, no baseline, neither population, missing baseline EPA and
baseline-only situation buckets. Independent expectations check percentage-point
units and offense-relative defense signs. Tests reject bad coverage/exclusion,
role/cohort mismatch, wrong difference units/signs/nulls, malformed ledgers, duplicate
or absent bucket keys and missing requested comparison. Warning markup renders
literally rather than executing.
Checkbox edits abort in-flight work and cannot display late comparison responses.
The existing 196 core and 21 API tests pass on all three supported Python versions;
API fixture replay stays network-blocked and byte-exact. Clean locked frontend
install, tests, type-check and build pass on Node 24.19.0. Dependencies and CI
configuration are unchanged.

An isolated Chrome 154 loopback check reproduced the frozen CAR 2024 REG-before-19
comparison exactly through the unchanged API. The baseline has 32,351 plays,
272 games, 31 observed teams and 17 shared games; selected counts stay 984 / 17.
Displayed differences are +3.4 pp dropback rate, -2.6 pp success and -0.064 EPA/play.
All 12 selected situation keys are present; an expanded 1/long bucket matches its
own baseline. Defense and toggle-off flows pass, with no external page requests
or page errors. Desktop/mobile rendering was inspected, with no page overflow at
390px. [Screenshot](examples/league-comparison-view.png) is real retrospective
output, not a new source audit, browser CI, latency benchmark or inference claim.

Self-review retained baseline-only buckets in overall counts without demanding
displayed baseline rows sum to the overall baseline. It validates difference
arithmetic/units against the returned metrics (1e-9 absolute tolerance) while
rendering API values, never computing a replacement estimate. Rounded negative
zero is normalized, reordered rows join by down/distance identity, and test queries
were scoped to distinguish collapsed duplicate text from the visible matching row.
The complete diff was checked for default changes, hidden warnings, temporal/
coverage claims, nullable measurements, API coupling and unrelated scope. No raw
source data, core/API code, dependencies or automation settings changed.
Exact remote SHA, attribution and CI receipts belong in this feature PR.

### P1.4 local report viewer — 2026-10-09

Fifty-one frontend tests cover consumed schema/identity/provenance validation,
counts/nulls/zeroes, roles, query bounds and fixed-route requests, malicious text,
loading/empty/error/retry/timeout states, edit/unmount cancellation and late-response
suppression. Tests use explicitly synthetic endpoint responses, never remote NFL
data. The twenty-first Python API test regenerates the committed browser fixtures
exactly through FastAPI with network blocked. The API fixture writer was extracted
for reuse; fixed stored gzip blocks/OS byte remove platform/compressor variance.
All 196 core and 21 API tests pass on Python 3.11/3.12/3.13, and frontend tests,
type-check/build and clean `npm ci` pass with Node 24.19.0. npm reported zero known
vulnerabilities at install time, not a comprehensive security audit.

Chrome 154 on loopback verified no initial report fetch, the pinned CAR offense
(984 plays / 17 games), defense and empty cutoff through the real Vite proxy/API.
It observed no page errors or external page requests. Vite returned 403 for an
attempt to read repository content outside `web/`. Desktop/mobile layouts were
inspected, with no document overflow at 390px; wide table scrolling stays local
to its region. See the [captured desktop](examples/local-report-view.png). This is
local integration evidence, not browser CI, an accessibility certification or a
throughput benchmark. No new source data was acquired.

Self-review corrected acceptance of real acquisition timestamps (`+00:00`, not
only `Z`) and added regression coverage. It corrected short-distance wording to
include zero, retained unavailable EPA cells in individual situations even when
overall values are zero, separated Node config tests from the DOM environment,
kept source attribution visible and widened the mobile season selector. It also
added impossible-date and bucket-count partition checks, exact JSON media-type
handling, and an own-property guard for the safe error-message lookup. The
decoder deliberately rejects unrequested advanced blocks/filters rather than
mislabeling their absence or hiding returned calculations. Display rounding does
not alter API measurements. The complete diff was reviewed for stale/mismatched
cohorts, denominator/role errors, data exposure, source claims and scope.

The CI workflow adds one Node frontend job to the existing six Python jobs.
Exact published SHA, attribution and final CI receipts are recorded in the PR;
the local evidence above does not by itself claim a remote pass.

### P1.4 local API slice — 2026-10-08 manual run

All 196 core and 20 API tests pass on Python 3.11/3.12/3.13, including API tests
with warnings treated as errors and `pip check` for the optional environments.
Clean 3.11/3.12 environments installed the constrained extras; core isolation is
also checked with `python -S`. CI retains three dependency-free core jobs and
adds three separately installed optional-API jobs. No CI trigger/settings or daily
automation changes were made; publication and exact-head CI receipts belong in
the feature PR.

The 20 API methods cover independent synthetic metrics, exact builder equivalence,
both roles, season/cutoff selection, empty/null states, all optional context groups,
comparison/resampling, required/scalar/cross-field validation, path/URL/label/extra
rejection, duplicate keys, methods/bodies, raw query bounds, startup verification,
stable resident data, resource boundaries, concurrent 503 responses and recovery,
sanitized internal/response errors and OpenAPI. Every test blocks network calls.

The pinned real snapshot reproduced the frozen historical report exactly under
sorted JSON serialization with comparison and 1,000 resamples (seed 20261006).
Ten additional CAR offense/defense and context combinations matched the core
builder. These replay checks blocked network access and retained the original
archive and decoded hashes. A separate loopback Uvicorn factory smoke returned
200 with 984 plays; its process was stopped. This is transport compatibility,
not a new independent data audit, throughput benchmark or calibrated inference.
See [API replay instructions](API.md#verification-and-replay).

Self-review replaced Starlette's deprecated `httpx` test fallback with its current
`httpx2` client, tested malformed/invalid/nonfinite outputs, explicit/default seed
boundaries, absent clock versus period-only support, and retained the dataset in
a local request reference. The full diff was checked for accidental analytics
changes, optional-dependency coupling, path/data exposure, stale source selection,
concurrency cleanup, misleading completeness and temporal claims. The models
validate the v2 envelope/metrics, while variable method/context blocks retain the
core's JSON contract. Limits are per application instance, not hard latency,
streaming-memory, authentication or multi-worker guarantees.

### Existing offline pipeline

From the project root:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m opponent_intelligence \
  --csv tests/fixtures/synthetic_pbp.csv \
  --source-label 'Synthetic verification fixture; not real NFL observations' \
  --team CAR --season 2024 --before-week 3
```

Both commands passed locally. The fixture yields six cohort plays, three
dropbacks, five observed EPA values, 0.04 EPA/play, and 0.6 success rate. The 25
existing pipeline tests remain intact. Nineteen acquisition tests cover source
metadata, hashes, retries, interrupted bodies, byte limits, gzip errors, cache
corruption, revision retention, atomic publication failures, and CLI behavior.
Network is blocked in acquisition tests, including their CLI subprocess. Nineteen
snapshot integration tests covered verified provenance, corruption/mutation,
season matching, raw/adapter reconciliation, missingness, empty data, CLI errors,
defense/field-position reports retaining manifests, and raw versus eligible optional
missingness. Fourteen defense tests check independent numerical expectations,
multiple opponents, default
offense compatibility, situations, positive/negative/zero/missing EPA, cutoffs,
empty cohorts, reciprocal selections, count partitions, and API/CLI validation.
Sixteen field-position tests cover bounds (including zero/equal/fractional values),
missing versus absent columns, scoped missingness, invalid inputs, no partial JSON,
reciprocal selection, and unfiltered compatibility. No real dataset is required.

Eighteen score-filter tests now cover signed/equal/open-ended bounds, ties versus
missing, precise whole-point parsing, absent columns, invalid values, exclusion
precedence, pre/post-play separation, scoped/overlapping missingness, both roles,
combined counts, retained EPA denominators, cutoffs, empty results, unchanged
unfiltered/field-only JSON, and all-or-nothing CLI errors. A twentieth snapshot
integration test adds raw/eligible score missingness, combined CLI filtering, and
manifest/hash preservation. The existing 93 tests pass unchanged.

The synthetic defense command in README.md also passes: five plays, three
dropbacks, four observed EPA values, 0.05 EPA/play, and 0.75 offensive success
allowed. The original fixture is unchanged and intentionally lacks `yardline_100`;
field-position tests generate separate synthetic inputs. No default denominator
or metric formula changed.

The same verified snapshot has 3,542 raw missing positions, zero missing/invalid
positions on its 34,902 eligible plays, and eligible values 1..99. With network
blocked, 576 filtered reports match independent raw selections and Decimal EPA
calculations; all eligible position/identity pairs reconcile. The 192 corresponding
unfiltered reports match the previous merged implementation exactly. See the
[field-position evidence and replay](REAL_DATA_AUDIT.md#field-position-extension-2026-10-02)
for ranges, counts, tolerance, and limits. No raw data was changed or committed.

The score extension found 2,713 raw missing scores, zero among eligible plays,
and eligible scores -46..46. All 34,902 raw/adapter score identities and source
`posteam_score - defteam_score` values match. Pre/post scores differ on 1,456
eligible plays. Independent raw selection and Decimal EPA calculations match 2,304
score-only/combined reports across both roles, and 576 reports without a score
filter exactly match merged PR #6. See the
[score evidence and replay](REAL_DATA_AUDIT.md#score-extension-2026-10-03).

Seventeen new clock tests and a twenty-first snapshot integration test bring the
suite to 130. They cover exact parsing, inclusive/equal/one-sided bounds, Q1–Q4
versus all OT periods, zero and missing values, absent headers (including empty
cohorts), exclusions, multiple missing contexts, both roles, unchanged no-time
JSON, retained EPA denominators, exclusive cutoffs, and CLI/snapshot provenance.
Review added malformed-clock CLI coverage even without a requested time filter,
and made the `--clock-max` help explicit about requiring a period. The preexisting
112 tests and original fixture remain unchanged.

The read-only CSV audit found five missing raw clocks, zero missing raw periods,
and neither missing among 34,902 eligible plays. Every eligible period/clock pair
matches the adapter, and quarter seconds match source start-of-play `time`.
Two eligible plays start at zero seconds. There are 174 REG OT plays, all qtr 5;
multi-period OT is synthetic coverage, not a finding from this artifact. Independent
raw/Decimal calculations match 7,680 period/clock reports and all their situation
measurements; 768 no-time reports exactly match merged PR #7. See the
[clock evidence and replay](REAL_DATA_AUDIT.md#clock-extension-2026-10-04).

Fifteen new comparison tests and a twenty-second snapshot integration test bring
the suite to 146. Independently calculated synthetic expectations distinguish
pooled rates from team-average rates; leave-team-out role selection; shared games;
matching versus absent buckets; missing EPA; empty populations; percentage-point
units; separate play/EPA warnings; and four-stage baseline missingness accounting.
Opt-in adds only the comparison block. The original 130 tests remain intact.

The read-only CSV audit matched 2,048 comparisons and their bucket differences to
raw selections/Decimal calculations, with exact count/coverage/ledger checks and
floating tolerance `1e-12`. The corresponding 2,048 ordinary reports match merged
PR #8 exactly. The CAR late-Q4 example has only 27 other offenses after filtering;
the corresponding CAR defense cohort is empty while its baseline remains valid.
Observed coverage is never silently labeled a complete league. See the
[baseline evidence and replay](REAL_DATA_AUDIT.md#league-baseline-extension-2026-10-05).

Fourteen new uncertainty tests and a twenty-third snapshot integration test bring
the suite to 161. All 3,125 ordered resamples of a five-game synthetic population
match independently expanded play arithmetic and a separate quantile routine.
Cases cover unequal game sizes, shared-game contrasts, every support/validity
boundary, missing EPA, empty cohorts and matching buckets, degenerate intervals,
unchanged report fields, temporal/context selection, both roles, seeded replay,
row-order invariance, global RNG isolation, and offline CLI/snapshot provenance.

The read-only pinned CSV check reconciled eight requested reports and every
reported situation against independent raw selections, Decimal game sums, joint
weight matrices, and NumPy percentiles (exact counts/statuses; `1e-12` absolute
numeric tolerance). Eight ordinary reports match merged PR #9 exactly. The check
exposes one/two-game early cohorts and a zero-game defense cohort, with intervals
correctly withheld. Full-season intervals retain the few-game warning. See the
[uncertainty evidence and replay](REAL_DATA_AUDIT.md#uncertainty-extension-2026-10-06)
and [method contract](UNCERTAINTY.md). These checks do not validate coverage.

Twenty new brief tests bring the suite to 181. They check hand-calculated rates,
counts and differences; offense/defense labels; zero/missing/empty/unrequested
states; every uncertainty status and its support/draw counts; context and bucket
alignment; inconsistent saved reports; metadata escaping; bounded file/stdin input;
and offline subprocess replay. Both committed JSON/Markdown examples match
byte-for-byte on all three runtimes, and the synthetic example also regenerates
from the original fixture. Snapshot notices and fingerprints remain unchanged.

The renderer accepted 32 pinned CAR combinations across role, early/full-season
cutoff, unrestricted/Q4 clock range, comparison, and uncertainty settings. Original
JSON was unchanged and source fingerprints retained. This is report-to-brief
integration evidence, not an independent re-audit of raw metrics or calibration.
The real example contains 984 plays / 17 games / 626 dropbacks before REG week 19
and is explicitly retrospective. The source was acquired in 2026. See
[brief contract and replay](BRIEFS.md) and [the example](examples/car-2024-reg-before-week-19.md).
A separate bundled Markdown parser and network-blocked headless preview confirmed
literal hostile labels, readable tables, and no horizontal overflow at 1280 pixels;
neither parser nor browser is a project runtime/test dependency.

The two PR #9 CI attempts on October 5 failed before test execution because GitHub
could not allocate hosted runners, with an internal server error. After the merge,
[main verification](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37382909725)
passed all 146 then-current tests and the synthetic demo on Python 3.11/3.12/3.13
at `af19425`. This resolves the previous pending CI note without a code change.
The [PR #10 implementation verification](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37473511186)
passed all three Python jobs at `f07b378`; each job's logs confirm 161 tests and
the synthetic demo passed. The existing workflow was dispatched manually after
no automatic run appeared. See the PR description for verification of any later
documentation-only publication head. The prior
[PR #8 final-head CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37219963174)
passed Python 3.11/3.12/3.13. Prior runs needed manual dispatch of the existing
workflow when no automatic run appeared. No workflow code, repository settings,
or daily automation changed.

The [PR #10 final-head run](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37473756050)
was rechecked as successful on `624aa81`. The
[PR #11 implementation run](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/37694342796)
passed at `36aaff3`: all three Python jobs ran 181 tests and the synthetic demo
successfully, confirmed in job logs. The existing workflow was manually dispatched
after no automatic run appeared. See the PR description for exact-head verification
of the later documentation-only publication commit; no workflow settings changed.

## Personnel/motion availability evidence (2026-10-08)

Fourteen new tests bring the suite to 195, passing locally on all three supported
Python versions. The offline inventory verifies source bytes and inventories 20
exact candidate names on raw versus adapter-eligible rows. Absent columns have null
counts, not invented missing/false observations. Tests cover all-missing and empty
populations, excluded-only coverage, unrecognized numeric flags, no text/alias
inference, malformed inputs, corrupt bytes, BOM identity, replay and blocked-network
CLI execution. Non-missing strings are deliberately not called semantic validation.

The [frozen JSON](evidence/pbp-2024-23370d5d10f8.availability.json) replays exactly
from the unchanged pinned snapshot. A separate raw CSV/Decimal check matched all
20 candidates' raw/eligible counts and binary partitions, with 49,492 / 34,902
rows. Six candidate columns are present; fourteen (including personnel and
`is_motion`) are absent. No new data was downloaded. Supplementary 2024 assets
were checked only through release metadata, not data coverage or local byte hashes.

The [source review](PERSONNEL_MOTION.md) pins nflreadr definitions and distinguishes
PBP CC BY 4.0 from participation/charting CC BY-SA 4.0. Recent personnel delivery
is post-season; documentation of a charting cadence is not proof of historical
availability. The scope decision defers enrichment pending separate terms,
provenance, joins, coverage and time-aware validation. Existing reporting remains
unchanged; P1.3 acceptance is complete without claiming those additional metrics.

## Raw acquisition evidence

`PYTHONPATH=src python3 -m opponent_intelligence.fetch --season 2024` downloaded
the real archive, matched GitHub's published digest, and recorded an immutable
manifest. The 19,362,351-byte compressed artifact decodes to 99,483,794 bytes;
the decoded hash also matches the separately published CSV asset. Offline reuse
with the network blocked passed and preserved the original manifest.

See [INGESTION.md](INGESTION.md) and the
[committed manifest](evidence/pbp-2024-23370d5d10f8.manifest.json) for IDs, hashes,
retrieval/update times, source terms, limits, and replay instructions. Raw data
remains ignored by Git. Acquisition supports only 2024 and validates bytes/gzip
integrity. The new offline `--snapshot` report path separately validates required
analytical fields, checks all row seasons, and includes the source manifest.

See [REAL_DATA_AUDIT.md](REAL_DATA_AUDIT.md) and its committed JSON evidence for
observed coverage, missingness, exact row reconciliation, replay commands, and
four independently cross-checked cohort totals. No contract relaxation was needed.

## Current data contract

Only the nine documented nflverse play-type labels are recognized. Unknown labels
fail with a line number and value, including on otherwise excluded rows. Missing
markers remain accepted and are counted separately under `missing_play_type`.
Identity checks still precede exclusions. Named categories remain case-sensitive;
the adapter does not silently repair typos or infer categories from other fields.
See docs/DATA_CONTRACT.md for the exact policy and source references.

## Follow-up

Inspect current PR CI and reviews first. Next, continue P1.4 with optional pre-play
field-position controls, reusing the API's inclusive `yardline_min` / `yardline_max`
bounds and defaults. Show offense-relative coordinates for both roles and ordered
selected/baseline missing-context accounting; expand response identity checks and
fixtures for filtered cohorts. Keep computation in the existing builder. Score/
clock filters, uncertainty display, downloads, browser CI and broader accessibility
review remain unfinished.
Do not add storage for this single-snapshot view or imply a public deployment.
The API must not accept arbitrary paths or fetch per request.
The brief and availability decision exist; do not rebuild them or silently add
personnel/motion enrichment. See [PERSONNEL_MOTION.md](PERSONNEL_MOTION.md),
[BRIEFS.md](BRIEFS.md), [METRICS.md](METRICS.md), and [UNCERTAINTY.md](UNCERTAINTY.md).
Coverage simulation and improved cross-game/small-sample methods remain unverified.
External schedule/gamebook reconciliation, historical availability, backup, and
larger-than-memory ingestion remain documented limitations, not completed claims.

The host's `/usr/bin/git` Xcode shim fails. The installed
`/Library/Developer/CommandLineTools/usr/bin/git` works. An unrelated ancestor Git
repository exists, so always verify the project root before staging anything.
