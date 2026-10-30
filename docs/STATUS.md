# Engineering status

As of the daily run on 2026-10-30, the long-term direction is
**NFL Decision Intelligence**, with the current product preserved as **Scout /
Analysis** and a planned **Play Caller / Decision Lab** UI/API. The first offline
Run/Pass evidence contract includes matched candidate baselines and opt-in
candidate-level game support/exploratory intervals;
no ranking/model or mode switch is claimed. A separate FTN charting snapshot is
now audit-only, not a source consumed by these reports. The
[architecture decision](DECISION_INTELLIGENCE.md)
records shared pipeline boundaries, Run/Pass interpretation gates, an initial
primary-source model/data review, AI policy and the justified no-database decision.
P1.5–P1.9 now cover decision foundations, model evaluation, richer data audit, API
and UI; the prior operational/case-study milestone is preserved as P1.10.

P1.4's bounded surface is merged through PR #22; P1.5's descriptive foundation
is merged through PR #27, including the [comparison/abstention policy](DECISION_POLICY.md).
P1.6's [nfl4th](NFL4TH_AUDIT.md) and [fastrmodels](FASTRMODELS_AUDIT.md) audits
are merged through PR #29; the [EP-only reference protocol](EP_REFERENCE_PROTOCOL.md)
is merged through PR #30 and the [acquisition/object preflight](EP_ACQUISITION.md)
through PR #31; the native XGBoost build/R source lock is merged through PR #32,
and the full runtime/native lock/equality check through PR #33. The
[actual R capture/export](EP_R_CAPTURE.md), merged through PR #34, closes the reference gate for all 25
unchanged synthetic cases. Actual prediction inputs match the expected features;
probabilities/EP pass the fixed protocol, singles/batch/untraced replay agree,
and separate offline execution reproduces the capture and raw export byte-for-byte.
The [independent Python candidate](EP_PYTHON_PARITY.md), merged through PR #35,
passes the same fixed corpus with its own encoder, source-built runtime and exact
offline replay.
P1.6's bounded engineering evaluation is complete. Calibration, training lineage,
historical availability and production model admission remain unverified/deferred.

Today's [FTN 2024 artifact/contract audit](FTN_CHARTING_AUDIT.md) completes P1.7's
first bounded acquisition slice. Separate immutable CSV/notices/manifest, verified
source pins and raw schema/key/encoding inventory; no PBP join or serving enrichment.
Verification is below. Scout schema v2, the API, frontend, briefs, downloads and
all 71 API fixtures remain unchanged. No production dependency, model execution,
training, ranking or automation change. The only production-code adjustment is
an optional Accept header on the shared bounded transport; existing defaults remain.
Actual assistive-technology/cross-browser
gaps remain in the [bounded accessibility review](ACCESSIBILITY.md), not a WCAG
certification. Next: one offline FTN-to-PBP left-join/coverage audit, preserving
eligible rows and separating unmatched/unknown/invalid values by team/week/candidate.
Investigate placeholder/applicability semantics before approving any field.
No production exposure until joins/missingness are audited; no assumed historical
in-season availability, serving model, action ranking or endpoint.
The 8 AM automation is unchanged.

P1.3 remains complete within its PBP-only scope; personnel/motion enrichment is
deferred under the [source decision](PERSONNEL_MOTION.md), not inferred from
shotgun/no-huddle or text. P1.2 stays complete for the pinned snapshot. Calibration,
cross-game dependence, opponent adjustment, historical information availability,
assistive-technology/cross-browser coverage and deployment remain open. Reports are descriptive, not two-team
projections or validated scouting recommendations.

## Canonical repository and migration

- Remote: https://github.com/AryanParte/nfl-opponent-intelligence
- Stable clone: `/Users/aryanparte/Documents/nfl-opponent-intelligence`
- Working branch: `codex/ftn-charting-contract`, started from updated
  `origin/main` at `691a18a` after observing PR #35 merged. Do not merge or enable
  auto-merge, and do not duplicate this unit while its PR is unmerged. The prior checkout
  was clean and matched its upstream, with no unpublished commits. Only `main`
  remained on the remote; no open PRs or review feedback remained. History is preserved.
- Publication/remote verification for this unit: consult the PR for
  `codex/ftn-charting-contract` for its exact published SHA, attribution and CI
  receipt. Local checks below are not a claim that remote CI has run.
- Previous Python parity review: [PR #35](https://github.com/AryanParte/nfl-opponent-intelligence/pull/35),
  merged at `691a18a`. [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/40985169226)
  passed all eight jobs. No open PRs/reviews/comments remained; only main was on
  the remote. The clean prior checkout matched its upstream, with no unpublished
  commits. Baseline 408 core / 24 API tests passed on Python 3.13 before edits.
- Previous R capture review: [PR #34](https://github.com/AryanParte/nfl-opponent-intelligence/pull/34),
  merged at `fd2ff46`; its tree matches feature head `ca8ebe9`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/40783340205)
  passed all eight jobs. No open PRs/reviews/comments remained; only main remained
  on the remote. The previous clean checkout matched its upstream without unpublished
  commits. Baseline 386 core / 24 API tests passed on Python 3.13 before edits.
- Previous full runtime review: [PR #33](https://github.com/AryanParte/nfl-opponent-intelligence/pull/33),
  merged at `5ab95ef`; its tree matches feature head `06766af`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/40610740808)
  passed all eight jobs. No open PRs/reviews/comments remained; only main remained
  on the remote. The clean previous checkout matched its upstream with no unpublished
  commits. Baseline 365 core / 24 API tests passed on Python 3.13 before changes.
- Previous native source/build review: [PR #32](https://github.com/AryanParte/nfl-opponent-intelligence/pull/32),
  merged at `3ae5033`; its tree matches feature head `9639b9d`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/40402965896)
  passed all eight jobs. No open PRs/reviews/comments remained; only main remained
  on the remote. The previous clean checkout matched its upstream with no unpublished
  commits. Baseline 347 core / 24 API tests passed on Python 3.13 before changes.
- Previous EP acquisition review: [PR #31](https://github.com/AryanParte/nfl-opponent-intelligence/pull/31),
  merged at `142e38d`; its tree matches feature head `c22d7bc`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/40246493599)
  passed all eight jobs. No open PRs/reviews/comments remained; only main remained
  on the remote. The previous clean checkout matched its upstream, with no unpublished
  commits. Baseline 331 core / 24 API tests passed on Python 3.13 before changes.
- Previous EP protocol review: [PR #30](https://github.com/AryanParte/nfl-opponent-intelligence/pull/30),
  merged at `28ef5b3`; its tree matches feature head `69d26cc`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/40145358187)
  passed all eight jobs. No open PRs/reviews/comments remained; only main remained
  on the remote. The previous clean checkout matched its upstream, with no unpublished
  commits. Baseline 311 core / 24 API tests passed on Python 3.13 before changes.
- Previous fastrmodels audit review: [PR #29](https://github.com/AryanParte/nfl-opponent-intelligence/pull/29),
  merged at `143dd4b`; its tree matches feature head `03bed10`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/40021489084)
  passed all eight jobs. No open PRs/reviews/comments remained; only main remained
  on the remote. The previous clean checkout matched its upstream, with no unpublished
  commits. Baseline 296 core / 24 API tests passed on Python 3.13 before changes.
- Previous nfl4th audit review: [PR #28](https://github.com/AryanParte/nfl-opponent-intelligence/pull/28),
  merged at `df4cb2c`; its tree matches feature head `d01e76a`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/39851226389)
  passed all eight jobs. No open PRs/reviews/comments remained; only main remained
  on the remote. The previous clean checkout matched its upstream (no unpublished
  commits). Baseline 288 core / 24 API tests passed on Python 3.13 before changes.
- Previous comparison-policy review: [PR #27](https://github.com/AryanParte/nfl-opponent-intelligence/pull/27),
  merged at `a561ffa`. [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/39677114041)
  passed all eight jobs. No open PRs/reviews/comments remained; only main remained
  on the remote. The previous clean checkout matched its upstream (no unpublished
  commits). Before edits, baseline 281 core tests passed on Python 3.13.
- Previous real-cohort reconciliation review: [PR #26](https://github.com/AryanParte/nfl-opponent-intelligence/pull/26),
  merged at `e3e8674`. [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/39511918187)
  passed all eight jobs. No open PRs/reviews/comments remained; only main remained
  on the remote. The previous clean checkout matched its upstream (no unpublished
  commits). Baseline 267 core / 24 API tests passed on Python 3.13 before changes.
- Previous candidate-uncertainty review: [PR #25](https://github.com/AryanParte/nfl-opponent-intelligence/pull/25),
  merged at `571a3a9`; its tree matches feature head `5136091`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/39341179653)
  passed all eight jobs. No open PRs/reviews/comments remained. Baseline 254 core /
  24 API tests passed locally on Python 3.13 before changes; checkout was clean,
  matching upstream with no unpublished commits.
- Previous candidate-baseline review: [PR #24](https://github.com/AryanParte/nfl-opponent-intelligence/pull/24),
  merged at `6246a3b`; its tree matches feature head `c06c7fa`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/39146577536)
  passed all eight jobs. No open PRs/reviews/comments remained. Baseline 238 core /
  24 API tests passed locally before changes; the clean checkout matched upstream.
- Previous decision contract review: [PR #23](https://github.com/AryanParte/nfl-opponent-intelligence/pull/23),
  merged at `5010cd7`; its tree matches feature head `3e8425c`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/39070180088)
  passed all eight jobs. No open PRs or review feedback remained. Baseline
  218 core / 24 API / 672 frontend tests passed before implementation.
- Previous accessibility review: [PR #22](https://github.com/AryanParte/nfl-opponent-intelligence/pull/22),
  merged at `0c3c4a3`; its tree matches feature head `fbef667`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/38960749969)
  passed all eight jobs. No open PRs or review feedback remained. Baseline
  196 core / 24 API / 672 frontend tests passed before implementation.
- Previous browser CI/direction review: [PR #21](https://github.com/AryanParte/nfl-opponent-intelligence/pull/21),
  merged at `91129ea`; its tree matches feature head `491a503`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/38827620757)
  passed all eight jobs. No open PRs or review feedback remained. Baseline
  196 core / 24 API / 636 frontend tests passed; the first frontend attempt had
  worker-start/test timeouts, followed by a clean two-worker baseline. The final
  default-worker 672-test run also passed; no timeout/retry settings were loosened.
- Previous download review: [PR #20](https://github.com/AryanParte/nfl-opponent-intelligence/pull/20),
  merged at `b0fc74f`; its tree matches feature head `3d53724`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/38808695441)
  passed all seven jobs. No open PRs or review feedback remained. Baseline
  196 core / 22 API / 635 frontend tests passed before implementation.
- Previous uncertainty viewer review: [PR #19](https://github.com/AryanParte/nfl-opponent-intelligence/pull/19),
  merged at `bd7e39d`; its tree matches feature head `ed47af0`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/38657439450)
  passed all seven jobs. No open PRs or review feedback remained; the clean prior
  checkout matched upstream. Baseline 196 core / 22 API / 545 frontend tests passed.
- Previous period/clock viewer review: [PR #18](https://github.com/AryanParte/nfl-opponent-intelligence/pull/18),
  merged at `1b1a37e`; its tree matches feature head `c47ffea`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/38498188199)
  passed all seven jobs. No open PRs or review feedback remained; the clean prior
  checkout matched upstream. Baseline 196 core / 21 API / 418 frontend tests passed.
  A temporary connector transport failure was bypassed with bounded public GitHub
  reads; the connector recovered before publication. No access settings changed.
- Previous score viewer review: [PR #17](https://github.com/AryanParte/nfl-opponent-intelligence/pull/17),
  merged at `4872669`; its tree matches feature head `4e402a1`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/38312899520)
  passed all seven jobs. No open PRs or review feedback remained. The previous
  checkout was clean and matched upstream; baseline 196 core / 21 API / 290
  frontend tests passed before implementation.
- Previous field-position viewer review: [PR #16](https://github.com/AryanParte/nfl-opponent-intelligence/pull/16),
  merged at `a83a3c2`; its tree matches feature head `0a957cc`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/38160303213)
  passed all seven jobs. No open PRs or review feedback remained; the prior
  checkout was clean and matched upstream. Baseline 196 core / 21 API / 184
  frontend tests passed before implementation.
- Previous comparison viewer review: [PR #15](https://github.com/AryanParte/nfl-opponent-intelligence/pull/15),
  merged at `c9b9087`; the merge tree matches feature head `a3f1e71`.
  [Merged-main CI](https://github.com/AryanParte/nfl-opponent-intelligence/actions/runs/38094251935)
  passed all seven jobs. No open PRs or review findings remained; the previous
  checkout was clean and matched upstream. Baseline 196 core / 21 API / 99 frontend
  tests passed before implementation.
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

### P1.7 FTN artifact and raw contract audit — 2026-10-30

[Evidence/replay](FTN_CHARTING_AUDIT.md) and the [aggregate receipt](evidence/ftn-2024-6faae8118cc1.contract.json)
record one 8,254,908-byte CSV matching the reviewed SHA-256, plus pinned loader,
dictionary and MIT documentation notice. FTN data retains its own CC BY-SA 4.0
attribution; it never inherits PBP's CC BY 4.0 record. Changed release metadata,
bytes or notice identity fail closed, while existing cache files are preserved.

48,031 raw rows / 29 documented columns / 285 games; both composite key domains
are complete, valid-format and unique. No blank/NA tokens, but literal zero falls
outside documented QB-location codes on 11,605 rows and hash codes on 11,601.
All 15 logical columns use TRUE/FALSE; that is encoding, not applicability or
charting-accuracy validation. Extraction timestamps span November 2024 to September
2025, not proof of pregame/public availability. No PBP joins or rates were computed.

Twenty-three new offline tests cover acquisition/media-type/identity failures,
cache/notice preservation, exact IDs and duplicate accounting, missing/absent/
unknown states, date/context errors, bounded malformed CSV, parse-time mutation,
determinism and no-clobber CLI output. An independent raw-CSV/Decimal/Counter check
reconciles schema, keys/games, context, all field/logical/code counts and timestamp
bounds. The committed receipt replays byte-for-byte with network blocked on
Python 3.11/3.12/3.13. CI needs no real FTN dataset or extra dependency.

Final local checks: 431 core / 24 API on each supported Python, API warnings as
errors, no broken dependencies; 672 frontend tests, TypeScript/build and 14
Chromium cases pass. Full-diff review fixed the transport's FTN metadata Accept
header after an initial HTTP 415, tightened JSON type identity (False is not 0),
and preserved unknown code/applicability distinctions instead of claiming all
nonmissing data valid. No pins, statistical formulas or serving schema changed.
Exact-head remote CI, SHA and attribution belong in the PR. Next: the bounded
PBP join/coverage audit, not another acquisition or premature play-family exposure.

### P1.6 Independent Python EP candidate and parity — 2026-10-29

[Evidence and reproduction](EP_PYTHON_PARITY.md) record the separate Python 3.13.2 /
native XGBoost 3.4.2 macOS ARM64 runtime. Seven optional dependency wheels have
verified hashes, metadata and retained notices; pip 25.0 is the existing interpreter's
bootstrap. No core/API environment or production dependency changed. PyPI did not
provide the target binding, so the verified source archive was built offline.
The initial auto-selected SDK 27 build failed; its logs remain. Explicit installed
SDK 26.5 selection succeeds without changing system settings or version pins.

The independent encoder imports no oracle/reference predictions. Actual DMatrix
features match all 25 fixed cases; all 16 unsupported cases reject. Seven-class
probabilities and signed EP pass the unchanged comparator: maximum R/Python
probability difference `4.656612890424627e-10`, EP difference
`3.259629019827792e-9` points. Python singles/batch are identical. Two separate
network-denied, write-restricted captures produce identical capture/environment
bytes and empty logs. No training, real-data prediction or action values.

Final verification: 408 core and 24 API tests on each Python 3.11/3.12/3.13, with
API warnings treated as errors and no broken dependencies; 672 frontend tests,
TypeScript/production build and 14 Chromium cases with one worker/no retries.
The 22 new tests cover independent feature encoding, rejected/coerced/nonfinite
states, signed EP, wheel/notice/cache safeguards, runtime drift, process limits,
text-evidence replay and rehashed semantic corruption. CI does not install or run
the optional native experiment. The final runtime/capture integrity checks and
comparison also pass locally against the retained verified R artifact.

Complete-diff review removed Python license-helper source files from the notice
inventory, bound the actual Python framework as well as its launcher, tightened
manifest/runtime identity checks and retained full-precision readable captures.
A concurrent verification caught the intentionally stale environment receipt;
fresh capture/receipt generation and the final matrix resolve it, without relaxing
tests or tolerances. Raw sources/models/wheels/builds remain ignored and preserved.
Test servers exited; Docker was not started. Automation, Scout schema v2, API/UI
and source-data snapshots are unchanged. Exact publication SHA/CI is in the PR.

P1.6 evaluation is complete within this synthetic domain, not a model-quality
endorsement. Production model admission remains deferred on temporal lineage,
typed context/unsupported-state policy, held-out baselines and calibration.
Next is P1.7's one-artifact FTN source/contract audit; no duplicate runtime setup.

### P1.6 Actual upstream EP capture and immutable raw export — 2026-10-28

The bounded offline driver re-verifies the acquired artifact, fixed corpus and
complete installed environment, then executes the actual pinned nflfastR standalone
EP path. R receives only full accepted states, independently builds half-time,
and uses upstream features. Instrumentation records the actual XGBoost matrix and
verifies all 26 loader calls use the exact exported raw bytes. No expected vectors
or probabilities are passed into R. An additional untraced batch is strictly identical.

All 25 cases pass exact 18-feature checks and the unchanged seven-probability/EP
criteria. Maximum normalization error is approximately `5.75e-8`; maximum EP
arithmetic error is approximately `5.8e-15`. Singles and batch agree exactly.
A separate fresh-container replay has identical capture/raw/runtime/observation
bytes (manifest timestamps differ). [Method, text evidence and replay](EP_R_CAPTURE.md).
The 9,737,490-byte raw payload and notices stay in ignored immutable cache entries;
Git contains only code/text evidence. These are synthetic-situation model outputs,
not real observations, cross-runtime parity, calibrated forecasts or action values.

Baseline: 365 core / 24 API on Python 3.13. Twenty-one new offline tests cover
state-only inputs, byte/runtime/feature/output mutations, bounded Docker arguments,
timeouts, no-clobber publication, preserved failed logs, locks, source drift and
committed evidence integrity. CI does not execute R or establish receipt authenticity.
Final local verification and complete-diff findings are recorded in the daily
learning entry; exact-head publication, attribution and remote CI belong in the PR.

The first development capture failed during repeated trace cleanup after generating
outputs; its unpublished staging/logs are retained. Guarded cleanup fixes the
harness without changing source/model pins or relaxing tolerances. The preflight
CLI now says it does not execute predictions itself, rather than making a stale
repository-wide no-predictions claim. Its regression assertion was updated accordingly.

Next: independent isolated Python EP candidate with verified binding/dependency
terms/hashes, independent feature encoding and unchanged single/batch/cross-runtime
criteria on the same corpus/raw export. No serving integration, WP, new data,
training, preferred call, API/UI or automation change. Do not merge or enable auto-merge.

### P1.6 Full offline reference installation and EP byte equality — 2026-10-27

The [runtime note](EP_RUNTIME.md) and [receipt](evidence/ep-full-runtime.json)
record the seven-package native lock, exact snapshot/keyring/signed release hashes,
retained copyright review, offline build and complete installed environment.
APT resolution and the independent installation inventory agree: 270 existing
packages unchanged, seven additions, no upgrades or removals. R 4.6.1/XGBoost
3.4.2.1 and all 43 R source pins are unchanged. Cached native build layers were
reused; all remaining R packages installed with networking disabled.

The read-only/unprivileged check verifies installed fastrmodels EP equals the
acquired raw bytes and reproduces identical JSON twice. It records 74 installed
R packages, 277 system packages, 46 R shared libraries and 86 resolved native
libraries. An initial whole-image check exposed unused Tcl/Tk GUI libraries absent
from the headless base; the final check records that exact exception, verifies it
is outside the required reference closure, and fails on any other missing library.
Wrong container/raw hashes both fail without a success receipt. No model execution,
persisted raw export, prediction capture, parity or football validation is claimed.

Verification: 365 core / 24 API tests on each Python 3.11/3.12/3.13, API warnings
as errors and clean dependency checks; 672 frontend tests, TypeScript/build and
14 Chromium cases passed without relaxed settings. Eighteen new offline tests
cover locks, hash/size bounds, no-clobber publication, corrupt/symlink/partial cache
state, prepared-context integrity and evidence boundaries. Real native-source
audit and finalized context preparation also replayed successfully. Review added
exact retained-notice/signed-release checks and explicit optional-GUI handling.
The original failed-build/native receipts remain intact as dated history.

No production code/dependencies, model pins, API fixtures or daily automation
changed. Test-owned servers exited; Docker was restored to its prior stopped state,
retaining images/caches/logs. Published SHA, attribution and exact-head CI are
recorded in this branch's PR. Next: actual fixed-corpus R capture and immutable
raw export with bound identities, before the independent Python candidate.

### P1.6 Verified native XGBoost build and pinned R sources — 2026-10-26

The [runtime note](EP_RUNTIME.md) records the source/build boundary and exact replay.
The upstream v3.4.2 source archive's bytes match its published digest; its R package
3.4.2.1 builds and loads in the pinned R 4.6.1 ARM64 image. No older mirror version,
patched model or global R installation was substituted. Forty required CRAN
dependencies plus XGBoost/nflfastR/fastrmodels now have a source-resolution lock,
notice hashes and offline install order. This is not yet a full native environment
lock. The setup helper verifies archives before atomic no-clobber publication,
rejects corrupt caches and unsafe archive members, and prepares a verified context.
Pinned Git archives recovered both nflverse commits after bounded codeload failure;
fresh acquisition through the finished helper reproduced both hashes.

The native check ran unprivileged/read-only/network-disabled with one CPU and
XGBoost thread, reproducing identical JSON twice. It records 34 installed R
packages, compiler/glibc and 20 linked native-library hashes. The full offline
install verified all sources, installed `cli`, then failed building `curl` 8.1.0
because `curl/curl.h` is absent. The log excerpt/identity are retained. This is
missing native setup, not an EP compatibility failure or a request for user access.
Installed fastrmodels EP equality and model outputs remain unavailable.

Bundled-asset metadata covers seven fastrmodels models, 19 nflfastR data-like files
and 27 nflreadr files, including internal/game/expected-output fixtures. Those
assets were not used for inference, training, analysis or golden predictions;
package terms do not establish separate data rights or training lineage.

Verification: 347 core / 24 API tests on each Python 3.11/3.12/3.13, API warnings
as errors and clean dependency checks; 672 frontend tests, TypeScript/build and
14 Chromium cases passed without relaxed settings. Sixteen new offline tests
cover source/setup contracts and receipt consistency, not binary attestation.
All 43 cached sources verify offline. Review fixed normalized duplicate archive
paths and added exact-commit Git acquisition/reuse coverage. Context IDs bind both
lock and installer; the R check emits JSON only. No statistical formula, API
fixture, production dependency or automation changed. Test-owned servers exited;
Docker was restored to its prior stopped state, retaining caches/images/logs.
Publication SHA, attribution and exact-head CI are recorded in this branch's PR.

Next: lock native development dependencies (libcurl headers/pkg-config first),
finish offline installation, record the full environment, verify installed EP
bytes and capture/replay the unchanged corpus. No model/parity/ranking claim yet.

### P1.6 EP artifact acquisition and isolated R preflight — 2026-10-25

[Acquisition evidence](EP_ACQUISITION.md) records the pinned `.rda` Git blob and
SHA-256, separate raw-object hash, retained terms, exact image/runner/driver identities,
and offline replay. Only the EP container and two notice/metadata files were
acquired; model binaries stay in the ignored canonical cache. Base R loaded exactly
one unclassed raw object. The raw payload differs in byte length from the prior
archive metadata, so equivalence is not assumed. No XGBoost model was executed.

The R 4.6.1 ARM64 image is verified, not the full inference environment. The tested
3.4.2.1 CRAN/mirror URLs returned 404; the dated index reports 3.2.1.1. A pinned
upstream source release is identified for the next build/terms/hash-lock unit,
not installed or locally attested. The original R prediction-capture item stays open.

All 331 core / 24 API tests passed on Python 3.11/3.12/3.13, with API warnings as
errors and clean dependency checks. All 672 frontend tests, typecheck/build and
14 Chromium cases passed first attempt, unchanged settings. Twenty new offline
tests cover byte/manifest tampering, cache preservation, partial publication,
locks, symlinks, unsafe mount paths, probe identity and owned-container cleanup.
Actual offline R receipt replay was byte-identical. API fixtures are unchanged;
test-owned servers exited and ports 8000/5173 are free.

Complete-diff review added a writer lock, regular-file manifest validation,
mount-option rejection, runner/input
drift checks and cleanup of only the uniquely named probe after Docker-client
timeouts. It kept object inspection distinct from installed-package equality,
export, inference and predictive validity. An early raw-to-text diagnostic failed
on embedded NUL; the final probe records hex instead. No runtime pin, statistical
tolerance or evidence gate was relaxed. Docker was restored to its prior stopped
state; its image remains cached, and unrelated service configuration is unchanged.
All three Python core/API suites and offline artifact verification were rerun
after the final manifest-validation fix and passed.
Publication SHA, account attribution and exact-head CI are recorded in the PR.

### P1.6 EP-only reference strategy and executable protocol — 2026-10-24

[The protocol](EP_REFERENCE_PROTOCOL.md) selects isolated R/nflfastR first,
followed by an independent Python/XGBoost candidate with identical extracted
package EP bytes. The terms/acquisition/runtime plan distinguishes the package
container from the raw payload and archive asset, requires installed-object
identity checks, and retains the upstream feature-encoding notice. R 4.6.1 /
R XGBoost 3.4.2.1 are provisional targets, not a provisioned or tested lock.

The repository-only standard-library oracle/capture comparator and fixed corpus
cover 25 hand-specified accepted states and 16 rejected states. Fifteen tests
exercise feature/era/down/half-clock boundaries, strict missing/type rejection,
corpus/source/model/manifest identities, class order and point weights,
finite/normalized probabilities, EP consistency, batch/single and cross-runtime
agreement with predeclared absolute tolerances. Invented probabilities and fake
test hashes are explicitly synthetic; no golden model outputs are claimed.
Capture agreement never attests artifact bytes or predictive validity.

All 311 core / 24 API tests passed on each Python 3.11/3.12/3.13; API warnings
were errors and dependency checks were clean. All 672 frontend tests,
TypeScript/build and 14 synthetic Chromium cases passed first attempt without
relaxed settings. The zero-model preflight passed with corpus SHA-256
`5d2a4282a838e2757a0ebf948587919a28799ab5fc05ebb4b4e70bee10ac2bc9`.
Test-owned servers stopped and ports 8000/5173 are free.

Complete-diff review strengthened swapped-prediction-row detection with distinct
invented outputs even when case IDs stay fixed; added missing runtime/fingerprint
regressions and enforced the corpus byte pin before parsing; and made
parent-container/installed-object/payload verification explicit. Final core/API/
preflight checks passed again on all three Python versions after review.
It kept neutral/missing-roof rejection and zero-clock probes separate
from upstream applicability and terminal-state assumptions. No production code,
API fixture, data/model acquisition, runtime dependency or automation changed.
Exact-head publication/CI and attribution belong in this branch's PR. Next:
the single pinned artifact and isolated R reference capture, not serving integration.

### P1.6 fastrmodels EP/WP source/interface audit — 2026-10-23

[The audit](FASTRMODELS_AUDIT.md) pins fastrmodels 2.1.0 and its nflfastR 6.0.0
consumer separately, with fifteen source-file identities and ordered 18/11/12
EP/WP/spread-WP feature inventories. Of fourteen distinct raw wrapper inputs,
four are present, two nullable, two require validated clock derivation and six
are missing from typed Play. Raw CSV availability was not re-audited. The WP
wrapper calculates both spread/no-spread outputs; its twelve-input contract
differs from the eleven-feature no-spread model. Standalone/bulk paths differ
in neutral-site and missing-spread/kickoff handling. None supplies Run/Pass values.

Three package/archive artifact identities, sizes and dates are recorded without
acquiring bytes. Archive API digests were null; local hashes and verified training
windows remain null. MIT package notices do not certify separate data rights.
R-container/raw-vector/UBJ formats need explicit conversion/parity checks; source
recipes and release dates do not attest binary lineage or historical availability.
Reuse remains a candidate; runtime admission is deferred.

Eight new offline tests guard the typed-input mappings, missing/null/derived states,
ordered features/classes/units, source pin/link coverage, unknown digest/lineage
states and remaining admission gates. They do not execute or validate a model.
All 296 core / 24 API tests passed on each Python 3.11/3.12/3.13 (API warnings as
errors), with no broken dependencies. All 672 frontend tests, TypeScript/build and
14 synthetic Chromium tests passed first attempt; no settings were loosened.

Complete-diff review corrected the signed-score time-scaling description and
clarified that future-derived training labels/weights differ from observed pre-play
score context. It strengthened coverage so every recorded source file is linked,
and preserved original screening pins and earlier learning/PR records. No model,
data, runtime dependency, production code, API fixture or automation changed.
Exact-head remote CI/publication evidence belongs in this branch's PR. Next:
decide the bounded EP-only reference strategy, acquisition/runtime plan and
independent parity protocol before installing/converting artifacts.

### P1.6 nfl4th source/interface and availability audit — 2026-10-22

[The audit](NFL4TH_AUDIT.md) pins the resolved v1.0.7 source commit, sixteen
inspected file identities, thirteen manual input mappings and ten output units.
Five upstream inputs are missing from typed Play, four nullable and four present
subject to semantic checks. Cohort ranges/cutoffs are not single game states.
Separate schedule/model caches, precompute downloads, R/mgcv/XGBoost compatibility,
possession/time/rules assumptions and incomplete artifact training lineage prevent
runtime admission. Reuse as a methodology reference; defer integration.

The receipt captures five release-asset observations with advertised digests, IDs,
sizes and dates; no binary bytes were acquired, so every local digest is null.
The package version, resolved commit, root tree, release target and artifact dates
are separate identities. Training-script windows are not certified binary windows.
Terms are recorded as package statements, not blanket asset/data legal clearance.

Seven new offline tests guard actual Play/DecisionRequest field drift, nullable/
missing classifications, the independently transcribed manual interface, output
units, source links/pins, unverified digest status and the deferred assessment.
They do not attest upstream behavior, model outputs or historical availability.
All 288 core / 24 API tests pass on Python 3.11/3.12/3.13 (API warnings as errors);
dependency checks are clean. All 672 frontend tests, TypeScript/build and 14
synthetic Chromium integration tests passed first attempt. Test-owned servers
stopped; ports 8000/5173 are free. No retries/timeouts/assertions were loosened.

Complete-diff review corrected an initial commit-ID/tree-ID mixup using the Git
commit endpoint and added a fixed-pair regression assertion. The explicit tree
lookup reconfirmed all sixteen source blob IDs, also matching the earlier desk
review's source files (not its entire tree). Review kept missing typed inputs
distinct from unaudited raw-column availability, conditional WP distinct from EPA
success, API-advertised hashes distinct from verified bytes and source scripts
distinct from artifact lineage. Earlier learning records and PR history are kept.
Final core/API verification was rerun after review; exact-head remote CI and
attribution are recorded in this branch's PR. No production code, data, dependency,
API fixture or automation changed. Next is the separate bounded fastrmodels audit.

### P1.5 comparison/abstention and opponent-evidence policy — 2026-10-21

Fourteen new synthetic tests check hand-calculated and 36 exact-rational candidate
pairs, signs/percentage-point units, candidate-specific unavailable reasons,
missing/zero/empty outcomes, thresholds, league/interval isolation, non-overlapping
`ok` intervals without ranking, exact cutoffs/context, OT/fourth-down selection,
unsupported inputs and deterministic output without IO or implicit resampling.
The reciprocal Scout defense test now also checks that a positive Pass-minus-Run
contrast remains offensive production, not defensive stops or a sign reversal.
All 281 core / 24 API tests pass on each Python 3.11/3.12/3.13 (API warnings as
errors); dependency checks are clean. Baseline was 267 / 24 on Python 3.13.

Eight pinned real cohorts / 24 new contrast values match independently selected
raw-record Decimal calculations on all three Python versions with networking
blocked. All previous decision fields match merged `e3e8674` byte-for-byte after
removing only the three additive comparison fields. The original eight-case /
144-interval receipt replays exactly, including its unchanged source manifest.
Its fingerprints cover the original field subset, not the new policy fields;
[additional replay instructions](DECISION_POLICY.md#verification-and-next-boundary)
make that boundary explicit. No raw source was acquired or modified.

The first frontend run passed 665/672 tests; seven tests timed out with a shared
roughly 467-second stall (478.29 seconds total). The cause is unconfirmed; no
frontend source changed. The unchanged default-worker suite then passed all
672 tests in 6.43 seconds with no concurrent Python suite, followed by successful
TypeScript/build. No timeout, retry or assertion settings were changed. All
14 browser cases passed on the first browser run (46.7 seconds, retries disabled).
All 71 API fixtures remain unchanged; test-owned servers stopped and ports
8000/5173 are free afterward. These are local checks, not deployment evidence.

Complete-diff review distinguished arithmetic availability, interval capability
and preferred-call abstention; kept league differences out of the selected
contrast; checked null reasons, denominators, source/cutoff identity and exact-key
compatibility; strengthened reciprocal-role and nonempty OT/fourth-down coverage;
and corrected stale continuation notes that still requested completed baselines.
It also separated retrospective source disclosure from decision-time availability
requirements. Existing candidate/game support remains visible; no arbitrary
ranking/support threshold, opponent projection or interval is invented. Primary
field/method references were checked, with project policy distinguished from
source claims. No external code/model/data, new dependency, API/UI or automation
change. Next: the first bounded P1.6 nfl4th interface/terms/availability audit.

### P1.5 independent real-cohort reconciliation — 2026-10-20

Thirteen new synthetic oracle tests cover hand calculations, raw eligibility,
dropback mapping, missing/zero values, temporal and context boundaries, independent
sampling, support gates, numeric strictness, deterministic RNG/decimal isolation,
wrong-source rejection, fail-closed receipt checks, committed-case consistency
and twelve injected production-result mutations. All 267 core / 24 API tests pass
on Python 3.11/3.12/3.13, with API warnings as errors and clean dependency checks.
The pip cache was unavailable under sandbox permissions; no package changes were needed.

The eight real cases/144 interval entries and exact saved receipt replay pass on
all three Python versions with network connection creation blocked. Both pinned
hashes are enforced, and all 34,902 raw eligible identities agree with the adapter.
The compact aggregate receipt includes the unchanged acquisition/attribution
manifest; raw data remains ignored. Outcomes: 66 interval entries `ok`, 48
`insufficient_games`, 30 `undefined_estimate`. None unlocks a preferred call.

All 672 frontend tests, TypeScript/build and all 14 synthetic browser cases pass
(17.3 seconds, first run, no retries). API fixture replay keeps all 71 fixtures
unchanged. Test-owned servers shut down; no persistent localhost service was started.

Complete-diff review kept the oracle outside the installed product, made method/
cohort metadata checks explicit, added deliberate-corruption/receipt tests, and
separated derived-aggregate attribution from the original raw-archive manifest.
Source expectations are copied before the builder; exact saved-receipt comparisons
reject boolean/numeric type substitutions, with regression coverage for both.
The oracle uses a declared expected-field subset rather than claiming full-response
or external football validation. Real eligible rows have no missing EPA/context;
synthetic tests cover those branches. No runtime behavior, dependencies, raw source,
API/UI/model or automation change. Remaining: explicit comparison/abstention and
opponent-evidence policy; calibration and causal/predictive validation are not done.

### P1.5 candidate game support and exploratory uncertainty — 2026-10-19

All 254 core / 24 API tests pass on Python 3.11/3.12/3.13, API warnings as errors;
all pip checks are clean. All 672 frontend tests and type-check/build pass. The
71 API-produced fixtures remain unchanged. Six representative Scout uncertainty
outputs (comparison, selected-only, empty, absent populations and unmatched buckets)
match origin/main byte-for-byte, including JSON field order. The documented
synthetic decision example replays with withheld intervals, not invented certainty.

Sixteen new tests independently expand all 3,125 ordered draws of five invented
games and check pooled candidate statistics/paired differences using separate
quantiles. They cover parent-frequency versus observed-EPA support, both-sided
support gates, absent/empty/missing/zero states, exact 95%-valid boundaries, undefined
draws without redraws, fixed filters/cutoffs, immutable inputs, no IO, strict options,
no opt-out sampling, RNG isolation, candidate complementarity and reciprocal Scout
defense meaning. Clearing support/interval gates never unlocks a preferred call.

The first browser run passed 13/14 cases but the narrow accessibility scan timed
out at its existing 60-second limit. Trace inspection shows one browser evaluation
taking about 94 seconds; emitted scans had zero automatic violations (with existing
incomplete findings). The pause cause is unconfirmed. Preserved that synthetic
trace/error context under `/private/tmp/nfl-decision-browser.IT3LzJ/`; this local
diagnostic is not a persistent repository artifact. The unchanged full suite then
passed all 14 cases in 15.5 seconds, with no relaxed assertions/timeouts or configured
retries. Approved process IPC was used; test-owned ports 8000/5173 are free afterward.

Complete-diff review added asymmetric-support and baseline-only-draw regressions,
kept Scout serialization unchanged, and corrected stale architecture continuation
text. Rechecked existing primary bootstrap references; their cluster/paired methods
do not validate our five-game/95%-valid safeguards or NFL coverage. No new dependency,
data/model artifact, license assumption, frontend/API or automation change.
P1.5 still needs independent real-cohort reconciliation and an explicit remaining
comparison/opponent policy; cross-game dependence and calibration remain unresolved.

### P1.5 matched candidate league baselines — 2026-10-18

All 238 core / 24 API tests pass on Python 3.11/3.12/3.13, API warnings as errors;
pip checks find no broken requirements. All 672 frontend tests, type-check/build
and 14 pinned-Chromium browser cases pass without retries. The macOS browser suite
requires approved outside-sandbox process IPC; no assertions/timeouts were relaxed.
All 71 API-produced fixtures are unchanged. Owned loopback servers stop; ports
8000/5173 are free afterward. No dependency installation or raw-data acquisition.

Twenty new tests independently calculate invented pooled baselines and differences,
including unequal team/game weights, exact matching without bucket fallback,
inclusive range endpoints, OT periods/clock zero, cutoff/team/type isolation,
candidate-specific coverage and shared games, absent/empty/all-missing outcomes,
dropback mapping, ordered missingness, full-source accounting, copied metadata,
strict opt-in, deterministic JSON and no builder IO. Existing API fixture replay
guards the shared difference helper against changing Scout outputs.

Complete-diff review checked source/time/role isolation, conditional ledgers,
pooled denominators, null versus zero, sign/percentage-point units, overlapping
games and retained no-ranking state. It added explicit distance-range and OT
regressions and clarified within-range mix differences: identical filter bounds
do not standardize situations or make groups exchangeable. Rechecked the pinned
primary field dictionary; existing PBP attribution/manifests remain untouched.
No new license, dataset, model, intended-call classifier or causal claim is implied.

This completes the matched-baseline slice only. Per-metric candidate game support,
exploratory paired whole-game uncertainty, independent real-cohort reconciliation
and a justified comparison policy remain unfinished. Continue those contracts,
not a decision API/UI/model; do not declare an optimal call from point estimates.

### P1.5 offline Run/Pass contract — 2026-10-17

All 218 core / 24 API tests pass on Python 3.11/3.12/3.13, API warnings as errors;
pip checks find no broken requirements. All 672 frontend tests, type-check/build
and 14 pinned-Chromium browser cases pass. The first browser attempt was prevented
from launching by macOS sandbox Mach-port permissions, before any assertions;
the approved outside-sandbox run passed without changing tests/retries/timeouts.
All 71 generated API fixtures match the existing committed JSON. Owned loopback
servers stop afterward; ports 8000/5173 are free. No new packages were installed.

Twenty-two new tests independently reconcile synthetic first-and-ten, sack/scramble
mapping, exact-versus-bucket distances, bounds, cutoff/team/season/type isolation,
fourth-down/zero-distance selectors, empty/absent/missing outcomes, separate warning
denominators, ordered context exclusions, OT clock zero, reciprocal Scout defense,
unsupported options, provenance copying, deterministic JSON and no builder IO.
The contract rejects defense/opponent/model/path options rather than silently
ignoring them. Existing Scout defense still reports offensive production allowed.

Complete-diff review checked the extracted formulas/bounds, original full-source
accounting, conditional missingness, null versus zero, candidate game counts,
temporal exclusions, capability abstention and unchanged API/UI outputs. It caught
and corrected a documentation reference to the wrong snapshot-loader module.
The source audit pins the nflreadr dictionary and preserves existing PBP license
and manifest records. Labels avoid asserting intended calls from dropback flags;
aborted-play/RPO intent and all-snap frequencies cannot be recovered from these
typed observations. No downloaded data or model output is used as new evidence.

This is only selected-side descriptive evidence, not complete P1.5 acceptance.
Matched candidate baselines/differences, candidate-level uncertainty and independent
real-cohort reconciliation remain unfinished; all ranking stays withheld. Counts
and the existing 30-play warning do not validate causality, prediction or reliability.

### P1.4 bounded Scout accessibility — 2026-10-16

All 196 core / 24 API tests pass on Python 3.11/3.12/3.13, API warnings as errors,
with clean pip checks. Clean locked npm installation reports no known vulnerabilities;
672 frontend tests and type-check/build pass on Node 24.19.0. All 14 browser cases
pass in pinned Chromium, without retries. The 71 API-produced fixtures are unchanged.
Test-owned ports 8000/5173 are no longer listening after the run.

The first browser regression reproduced missing focus on the required period after
submitting a clock without it. Typed validation now carries field identities into
React without re-parsing messages or duplicating validation. Existing helper text
is retained, both ends of inverted ranges are identified, and valid seconds/seeds
are not marked invalid for a missing prerequisite. Tests cover every validation
branch, repeated submissions, clearing stale errors and asynchronous error focus.
Required-control/format instructions are explicit. Input/select borders now have
3.72:1 contrast against white rather than 2.20:1, checked from rendered styles.

Seven axe scan states per desktop/narrow context have zero automatic violations;
`incomplete` contrast entries remain for decorative glyphs and clipped/short table
cells. Review inspected these and preserved the full JSON, rather than suppressing
rules or equating zero violations with compliance. Browser tests cover all 15
controls' tab order, native correction, disclosures, named/captioned tables with
headers, focus outlines, arrow-key scrolling, exiting with Tab and 320px document
containment. Query/table screenshots were visually inspected. Actual screen-reader,
cross-browser, physical-device, browser-zoom and forced-colors checks did not run.
See [ACCESSIBILITY.md](ACCESSIBILITY.md) for exact evidence and follow-up.

Complete-diff review retained first-failed-rule semantics, bounded query options,
stale-response guards and error sanitization; no analytics/data/provenance or schema
changes. The new unmodified MPL-2.0 checker is dev-only and pinned. The automated
scans were already green before the independently failing keyboard regression;
both are needed. P1.4 closes within that bounded scope, not as public certification.

### P1.4 synthetic browser CI and direction update — 2026-10-15 manual run

All 196 core / 24 API tests pass on Python 3.11/3.12/3.13 with API warnings as
errors and clean dependency checks. All 636 frontend tests and type-check/build
pass on Node 24.19.0. Clean locked npm installation reports no known vulnerabilities.
Playwright 1.64.1 pins Chromium revision 1248 (156.0.8078.4 in this run); eight
desktop/narrow cases pass, then sixteen executions with `--repeat-each=2` pass
without retries. This is local macOS evidence; the PR's `browser` CI job separately
verifies Linux. All 71 existing API-produced frontend fixtures remain unchanged.

The test API uses the existing synthetic four-stage fixture in a temporary hashed
snapshot. CAR offense / ATL defense select the same three plays: EPA 0.8, -0.4,
missing; one game, two observed EPA, 0.2 EPA/play, 50% success and one dropback.
The single baseline play has EPA 3. No future-week/POST/excluded row enters these
queries. One-game bounds are withheld, not fabricated. Browser downloads preserve
actual response bytes and render via the offline Python CLI without another API
request. No real observations are used or acquired by this harness.

Review found that Uvicorn re-raises SIGTERM after application shutdown, bypassing
an outer temporary-directory context. Cleanup now occurs in the wrapped test-only
lifespan before signal replay, with the outer context retained for startup errors.
Lifecycle tests check this order, operator-config independence and denied outbound
connections. Live occupied-port probes check refusal to reuse either service,
preservation of the pre-existing owner, release of owned listeners and temporary
snapshot cleanup. Forced process termination remains a documented OS-temp cleanup
limitation, not a reason to touch real snapshots or another user's server.

Initial harness checks caught a wrong loader import, keyword-only factory/label
arguments and overly exact select-label locators. Corrected the harness; did not
weaken assertions, increase timeouts or change production code. Complete-diff
review keeps browser tests out of Vitest, includes them in TypeScript checks,
uses one worker/no retries, blocks unexpected browser requests and adds config
regressions. The architecture review separates model state values from action
values, post-play features from decision-time inputs, and software licenses from
dataset rights. No model outputs or richer-source joins were independently validated.

### P1.4 current-report JSON download — 2026-10-15

All 635 frontend tests, clean locked install and type-check/build pass on Node
24.19.0. All 196 core / 22 API tests pass on Python 3.11/3.12/3.13, with API warnings
as errors and clean dependency checks. Ninety added frontend cases cover all 71
unchanged API fixtures, byte-preserving Blob contents, safe filenames, additional
fields/Unicode/numeric spellings, empty/null results, invalid HTTP/JSON/cohort,
query edits, late/timeout responses, repeated clicks, replacement failure,
StrictMode and unmount cleanup. The test URL-store stub preserves the URL parser;
browser saving is checked separately, not inferred from jsdom link clicks.

Six actual pinned-snapshot API queries yielded seven native Chrome 155 downloads,
all identical to their decoded response text, with no additional report request.
Cases cover the frozen 1000-draw comparison, selected-only uncertainty, four-stage
defense/offense, an empty pre-week-1 frame and clearing comparison/bootstrap.
Filtered defense retains 3 selected / 136 baseline plays; filtered offense 0 / 139.
All six saved JSON files replay through the existing Python renderer; file/stdin
outputs match. Frozen CAR offense REG before week 19 (1000 draws, seed 20261006)
reproduces the committed historical Markdown byte-for-byte, including its report
fingerprint. Saving does not make the source pregame-available or validate inference.
Repeated download keeps one live URL; all 12 StrictMode-created URLs were revoked
once after removal. Mobile 390px keyboard Enter download and desktop/mobile visual
inspection passed, with no document overflow, external page requests or page errors.
Both owned servers were stopped. This is local integration evidence, not browser
CI, a cross-browser/screen-reader audit, benchmark or statistical calibration.

Complete-diff self-review preserved decoded text instead of fingerprint-changing
JavaScript serialization, added failed-replacement resource cleanup coverage, and
documented that filenames are neither unique report identities nor proof of a saved
file. No analytics, dependencies, source bytes, workflow or automation changed.
One local attempt had simultaneous roughly 53-second stalls/timeouts across seven
workers. The unchanged 635-test suite subsequently passed in 11.46 seconds and the
build passed, without increasing timeouts. The stall cause was not established;
independent remote CI is recorded on the PR.

### P1.4 exploratory uncertainty viewer — 2026-10-14

All 545 frontend tests, clean locked install and type-check/build pass on Node
24.19.0. All 196 core / 22 API tests pass on Python 3.11/3.12/3.13, with API warnings
treated as errors and clean dependency checks. Thirteen new synthetic endpoint
fixtures cover every interval status, selected-only/default seed, comparison,
defense, empty frames/populations, partial/missing EPA, baseline-only buckets,
20-game support and combined filters. The previous 58 fixtures are unchanged.
Two explicitly labeled controlled-RNG endpoint cases test the exact 190/200
valid-draw gate; they are not seed-replay or calibration evidence. Independent
pooled/support expectations complement replay. Mutation tests reject invalid
metadata, units, support, statuses, bounds, paired counts and situation identity;
UI tests cover unsafe text, invalid input, explicit retry and late-response handling.

Eight isolated Chrome 155 loopback queries passed on the unchanged pinned 2024
snapshot. CAR offense, REG before week 19, comparison on, 1000 draws and seed
20261006 exactly reproduces the frozen uncertainty, overall and comparison blocks.
There are 17 selected and 272 baseline games, with a 272-game union; selected
EPA bounds display -0.175 to 0.062, paired-difference bounds -0.190 to 0.049.
These are exploratory nominal bounds, not a calibrated finding or significance test.
Selected-only/default seed, defense, maximum seed, both-empty and four-stage
filtered queries passed. The filtered defense has three plays in one game, so its
intervals are withheld: 130 defined / 70 undefined of 200 draws. The same offense
query is empty while its baseline remains observed; before-week-1 performs zero
draws on an empty frame. Clearing bootstrap restores frozen overall/comparison
blocks exactly. Invalid text/seed-without-repetitions sends no request. No external
page requests/errors, mobile document overflow or keyboard-scroll issues occurred.
The desktop screenshot and 390px mobile layout were inspected; both owned servers
were stopped. These remain local checks, not browser CI, WCAG or load certification.

Complete-diff review added full-frame and subset/paired support consistency checks,
tested that bootstrap leaves filtered estimates unchanged, and kept seeds ungrouped
for copying back into the form. A test expectation was corrected to match existing
ASCII minus formatting. No analytical formulas, API/core code, source bytes,
dependencies, CI workflow or automation changed. Coverage and cross-game dependence
remain unvalidated; more draws do not supply more observed games.

### P1.4 period/clock viewer — 2026-10-13

All 418 frontend tests, a clean locked install and type-check/build pass on Node
24.19.0. All 196 core / 21 API tests pass on Python 3.11/3.12/3.13, with API
warnings treated as errors and clean `pip check` results. Fifty-eight synthetic
endpoint/browser fixtures replay with network blocked; the prior 37 are unchanged.
Twenty-one additions cover period-only versus explicit full-clock, an absent
clock column, all regulation quarters and OT periods 5/6, omitted clock ends,
zero, empty/missing populations, missing EPA, both roles and four-stage chains.
Independent count/EPA expectations complement exact endpoint replay. Mutation
tests reject wrong identity/units/timing, hidden or missing contexts, incorrect
order, disconnected ledgers, final-count mismatches and post-filter leave-team-out
counts. Interaction tests preserve invalid text, enforce a period even for zero,
clear/rebuild explicitly, ignore late responses and keep API error feedback safe.

Seven isolated Chrome 155 queries on the unchanged pinned 2024 snapshot passed.
For CAR 2024 REG before week 19, comparison on, field 0–20, score -7–0, Q4 0–120,
offense plays are **984 → 156 → 90 → 4 → 0** versus **32,351 → 4,991 → 2,244 →
426 → 139** baseline; defense is **1,131 → 218 → 96 → 18 → 3** versus **32,204 →
4,929 → 2,238 → 412 → 136**. Stage cells match the API and empty results remain
empty. Q4-only/full-clock, OT 0–120 and Q4 zero-clock also passed. Clearing all
context controls restores frozen overall/comparison blocks exactly. Invalid
`2:00` and a clock bound without period issue no request. No external page requests
or page errors occurred. Desktop and 390px mobile views were inspected, including
keyboard table scrolling with no document overflow. Both owned servers were stopped.

Self-review clarified earlier stage labels as intermediate, preserved schema v2
field-only compatibility and checked conditional missingness/global exclusion
accounting. The field caption now names season/week instead of ambiguous “time”
selection; period filtering happens later. Initial test selectors were corrected
to match accessible row names and actual help text, then verification reran.
No formulas, API/core code, dependencies, source bytes, CI or automation changed.
This is local integration evidence, not browser CI, a WCAG audit, load testing,
historical availability or statistical calibration. The screenshot and replay
details are in [the viewer guide](WEB.md#pre-play-period-and-clock).

### P1.4 pre-play score viewer — 2026-10-12

All 290 frontend tests, a clean locked install and type-check/build pass on Node
24.19.0. All 196 core and 21 API tests pass on Python 3.11/3.12/3.13, with API
warnings treated as errors and no broken requirements from `pip check`.
Thirty-seven endpoint-generated synthetic fixtures replay with network blocked;
the 22 previous fixtures are unchanged. Fifteen additions cover score-only and
field/score queries in both roles, ties and negative/positive bounds, unbounded
ends, API input limits, all-missing scores, missing baseline scores/EPA and emptiness.
Independent count/EPA expectations complement response replay. Both populations'
metadata, order, count partitions and stage linkage have rejection tests; input,
stale-edit, clear/rebuild and safe missing-column error behavior is tested.

Six Chrome 154 loopback queries on the unchanged pinned 2024 snapshot passed:
CAR 2024 REG before week 19, comparison on, with combined field 0–20 / score -7–0
in both roles; defense lower-only +7; offense upper-only -7; offense ties; and
cleared filters. Offense counts are selected 984 → 156 → 90 versus baseline
32,351 → 4,991 → 2,244; defense counts are 1,131 → 218 → 96 versus
32,204 → 4,929 → 2,238. These sequences mean before field → after field → after
score; neither stage has missing context for these real cohorts. Cleared overall
and comparison blocks exactly match the frozen historical report. A partial minus
sign sends no request. No external browser requests or page errors occurred.

Desktop and 390px mobile layouts were inspected, with no document overflow and
keyboard scrolling within the score table. The [screenshot](examples/pre-play-score-view.png)
is actual retrospective output. Both owned servers were stopped. These are local
integration checks, not a new raw-data audit, browser CI, physical-keyboard/WCAG
certification, a load test, calibrated inference or a neutral-game definition.

Full-diff self-review replaced the field-only final-count assumption with a
checked ordered chain and labeled field survivors as intermediate when needed.
It corrected unrestricted-field text that could imply retention despite a score
filter, kept missing-column feedback relevant to either context, and used a tight
tolerance for independently calculated floating-point EPA. Plain text score inputs
preserve invalid partial signs and avoid numeric keyboard hints that may omit minus.
The builder, API, source bytes, dependencies, workflows and automation are unchanged.
Exact-head remote CI, publication and attribution receipts belong in the feature PR.

### P1.4 field-position viewer — 2026-10-11

All 184 frontend tests pass, including twelve additional endpoint-generated
fixtures (22 total): both roles, comparison on/off, lower-only/upper-only/default/
full/zero/fractional bounds, an empty pre-week cohort, outside-range empty results,
all-missing positions and missing baseline context. The original ten fixtures are
unchanged. Independent synthetic expectations distinguish position and EPA
missingness and verify inclusive endpoints, offense-relative signs and count
partitions. Response mutations reject mismatched effective ranges/policies,
unexpected filters, malformed counts, after-filter team exclusion and unreconciled
temporal totals. Both bound edits abort/ignore late responses; malformed input
does not become an unfiltered query, and absent columns do not become empty data.

All 196 core / 21 API tests pass on Python 3.11/3.12/3.13 with API warnings treated
as errors; fixture replay blocks network. Optional environments pass `pip check`.
Node 24.19.0 clean `npm ci`, tests, type-check/build pass; npm reported zero known
vulnerabilities at install time, not a security certification. Dependencies and
CI configuration did not change.

An isolated Chrome 154 loopback check exercised six real-snapshot queries:
CAR offense and defense at 0–20, defense at 80–100 (omitted upper end), defense
at 20.5–20.5 and 0–0 (valid empty cohorts), and the cleared/unfiltered offense.
The 2024 REG-before-19 offense retains 156 of 984 selected plays versus 4,991 of
32,351 baseline plays; zero missing positions, 828 / 27,360 outside the range.
Defense retains 218 of 1,131 versus 4,929 of 32,204. Displayed counts match the API,
source hashes remain unchanged, and cleared-filter overall/comparison blocks
match the frozen historical report exactly. Invalid text sends no request.
Desktop/mobile views were inspected, with no document overflow at 390px,
keyboard-scrollable accounting tables, no external page requests or page errors.
The [screenshot](examples/field-position-view.png) is actual retrospective output;
these are integration checks, not a new raw-data audit, browser CI, WCAG
certification, calibrated inference or drive-level red-zone analysis.
Both owned test servers were stopped after verification.

Complete-diff self-review checked defaults, context identity, no-data versus
missing-column errors, pre-filter leave-team-out accounting, double-counted
exclusions, source/time claims, optional dependencies and scope. Text inputs with
decimal keyboards preserve invalid values for validation instead of the browser
sanitizing them to blank (which would omit the filter). Baseline exclusion uses
the selected **pre-filter** count, not displayed retained plays; nested cohort
fields are compared by value. Review added same-source unfiltered and zero-base
fixtures, clarified that each baseline play targets its own defense's goal line,
and corrected an initially clipped evidence screenshot. No core/API,
raw snapshot, dependencies, workflows, database or automation settings changed.
Publication, attribution and exact-head CI receipts belong in this feature PR.

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

Inspect current PR CI and reviews first; do not duplicate this unit while unmerged.
P1.5 is complete within descriptive-only scope: request/cohorts, candidate metrics,
matched league context, exploratory support/intervals, independent raw audit and
comparison/abstention/opponent policy. Do not rebuild these or unlock ranking from
counts, differences or nominal intervals. See [DECISION_POLICY.md](DECISION_POLICY.md).
The bounded P1.6 [nfl4th](NFL4TH_AUDIT.md) and
[fastrmodels EP/WP](FASTRMODELS_AUDIT.md) audits and
[EP-only reference strategy/protocol](EP_REFERENCE_PROTOCOL.md) are complete;
runtime use is deferred, not validated. The [EP acquisition/object preflight](EP_ACQUISITION.md)
is complete, and the [full runtime/native lock](EP_RUNTIME.md) now verifies offline
installation and installed-package EP equality. The [actual R capture](EP_R_CAPTURE.md)
now passes the fixed corpus, actual matrix/loader checks and exact offline replay.
The [independent Python candidate](EP_PYTHON_PARITY.md) also passes the unchanged
parity protocol. P1.6's bounded evaluation is complete; production EP/WP/action
values remain deferred. Do not redo setup, change pins/corpus/tolerances or infer
that training scripts attest release binaries. The first [FTN source/contract
audit](FTN_CHARTING_AUDIT.md) is now complete: separate immutable bytes, notices,
manifest and raw key/encoding evidence. Next: an offline left-join/cardinality and
coverage audit against existing pinned PBP, with eligible-row retention, explicit
unmatched/unknown/invalid counts by team/week/candidate and placeholder/applicability
investigation. No play-family exposure or historical-availability assumptions.
Preserve Scout schema v2 and the actual
assistive-technology/release-readiness gaps in [ACCESSIBILITY.md](ACCESSIBILITY.md)
without claiming conformance or restarting P1.4/browser CI.
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
