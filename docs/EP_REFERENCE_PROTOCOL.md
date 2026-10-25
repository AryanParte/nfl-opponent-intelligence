# EP-only reference strategy and executable protocol

Decision: 2026-10-24. **Use an isolated pinned R/nflfastR reference first, then
compare a native Python/XGBoost candidate using the same extracted model bytes.**
This closes P1.6's strategy/protocol unit, not its model-parity gate. Production
integration remains deferred. No model bytes, R environment or XGBoost dependency
were acquired, installed or executed in this unit; no golden model predictions
exist yet. Scout, its EPA calculations and the descriptive Run/Pass layer are unchanged.

Follow-up, 2026-10-25: [artifact acquisition and object preflight](EP_ACQUISITION.md)
now verify the EP container and raw object in digest-pinned base R. The paragraphs
above describe the original protocol unit; acquisition receipts now exist
separately. The full inference environment and actual prediction capture remain
unfinished. The dated mirror supplies XGBoost 3.2.1.1, not the proposed 3.4.2.1;
resolve the pinned upstream source-build route without silently changing versions.

The [fastrmodels audit](FASTRMODELS_AUDIT.md) and [nfl4th audit](NFL4TH_AUDIT.md)
already establish source/interface limits. Do not repeat those audits or rebuild
their models. Today adds an executable, repository-only acceptance protocol in
[`validation/ep_reference.py`](../validation/ep_reference.py), not a production
adapter or a second ingestion stack. It is outside the installed `src` package.

## Choice and tradeoffs

| Option | Benefit | Cost / decision |
| --- | --- | --- |
| Isolated R reference, then Python candidate | Keeps the pinned upstream feature/output path as a separate reference; avoids training a replacement | Two experimental environments/locks. **Selected**, offline only; R is not a new serving dependency |
| Direct archive UBJ + Python without R | Fewer environments and potentially a small serving runtime | Does not independently establish R feature/class/batch semantics or package/archive equivalence. **Not sufficient as the first reference** |
| Defer all model experiments | Keeps the descriptive product deployable without new scientific claims | No evidence about reuse feasibility. **Production remains deferred**, but the small offline reference is worth testing |
| Port/retrain the models or call R per HTTP request | Could customize behavior | Unjustified training/maintenance burden or serving complexity. **Rejected for this slice** |

These are architectural tradeoffs, not measured latency, cost or football-quality
results. State EP estimates the value of the next scoring event this half; it
cannot choose Run/Pass without an additional defensible transition/outcome model.

## Artifact and terms plan — one model, no archive substitution

Use the audited **package EP object** at fastrmodels source commit
`ca185baf7757c2992e57ce2bdf2f296c515465d8`, not a mutable latest release or the
similarly named archive asset. Its `data/ep_model.rda` Git blob is
`f1a434b6f6f67fcb2195d0aeb6cf5d7dd88c7a09` (2,864,452 bytes in the audit).
Use nflfastR consumer commit `917b14e5085f352d9b00d23628759773e7d411b5`.

Before loading anything, the next unit must:

1. Acquire only reviewed, pinned package sources/artifacts in an explicit setup
   step; preserve the source URL, retrieval time, version/commit, observed upstream
   dates, sizes and locally computed SHA-256. Check the package object's Git blob
   identity using Git's blob framing, not by comparing SHA-1 of unframed file bytes.
2. Retain the fastrmodels/nflfastR MIT notices and source-to-artifact association;
   inspect the selected runtime and all dependency notices. These terms do not
   license separate historical data or establish training lineage. Do not commit
   raw/model binaries or assert that the archive UBJ equals the package payload.
3. Verify the installed package's source/artifact identity. Load the inspected
   `.rda` into a separate environment, require exactly its expected raw EP object,
   and compare its bytes to the installed package's EP object before export.
   Export **those raw bytes** to a separate immutable file.
   R's [binary I/O](https://stat.ethz.ch/R-manual/R-devel/library/base/html/readBin.html)
   supports writing raw vectors. Hash the extracted payload and record its parent
   `.rda` hash and extraction runner hash. This is not renaming a container or
   re-saving a booster with potentially different serialization.
4. Feed that payload to R's raw loader and, later, Python's native UBJ model loader.
   Both captures must reference the same payload and acquisition-manifest hashes.
   Use only trusted, reviewed model bytes; no pickle/automatic conversion fallback.
   [XGBoost's portability guarantee](https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html)
   distinguishes model files from memory snapshots; it does not establish our
   feature parity, model calibration or action quality.

No acquisition manifest or byte hash is fabricated today. The prior audit's null
local hashes remain null. An acquired-byte hash establishes identity, not authorship,
training-window validity or decision-time availability. Training lineage stays
unknown unless independently evidenced.

## Runtime and execution plan

Provisional reference targets are **R 4.6.1** and **R XGBoost 3.4.2.1**: the former
is listed in [CRAN's source archive](https://cran.r-project.org/src/base/R-4/),
and the latter is the R package version in the
[XGBoost v3.4.2 declaration](https://raw.githubusercontent.com/dmlc/xgboost/v3.4.2/R-package/DESCRIPTION).
The declaration specifies R >= 4.3 and C++17 and states Apache-2.0 terms; these
are requirements/terms, **not a tested lock**. Use the two exact nflverse source
pins above. A later Python candidate targets a separate Python 3.13.2 environment
and the matching XGBoost release, with its actual binding version recorded.
Do not substitute an R package version string for the Python binding version.

At this run, `R`/`Rscript` were not on PATH; Docker was, but no daemon/image or
runtime compatibility was tested. Provision the reference in an isolated
experiment environment (a digest-pinned container is acceptable, not deployment),
without changing system developer settings, API/core environments or global R
libraries. No container/image configuration is shipped here.

Record exact runtime patch versions, OS/architecture, compiler/native libraries,
CPU/thread settings, resolved transitive packages and source/archive hashes before
prediction capture. An isolated R project library with a
[renv lock](https://rstudio.github.io/renv/articles/renv.html) can record package
resolution; it is not a substitute for the interpreter/system record. Record the
environment manifest/lock hash and runner-file hash in every capture. Disable
automatic restore/download behavior during inference; setup is a separate networked
phase. Run offline, CPU-only, one thread, no training, tuning, WP or schedule lookup.
Do not call an untested environment reproducible or silently change pins to make
an installation pass. Preserve any failed compatibility result and reassess it.

The R reference calls the pinned `calculate_expected_points()` standalone path
and records its actual feature matrix and seven probability columns. It must
compute features itself, not copy expected vectors into its capture. Run the
same cases as a batch and one row at a time. The later Python candidate computes
its own features; it must not import this oracle or use R predictions as its own.

## Predeclared synthetic domain and corpus

The [corpus](../validation/fixtures/ep_reference_cases.json) has **25 accepted and
16 rejected** cases. Full states are its base plus each explicit override. Its
manually written feature vectors precede model output: eras on both sides of all
four boundaries, all downs, home/away, four roof states, quarter/half boundaries,
zero clock, field interior and timeout counts. The oracle independently encodes
them using the audited 18-column order. Team codes are synthetic labels, not a
verified schedule or roster lookup.

This experiment intentionally restricts years to 1999–2024, regulation quarters,
non-neutral venues, known roofs (`outdoors`, `dome`, `open`, `closed`), interior
field positions and positive whole-yard distance no greater than distance to goal.
These are **test-protocol choices**, not an assertion about upstream model training
coverage, universally valid NFL states or the broader Scout contract. Unknown,
extra, non-finite and wrongly typed input is rejected; no bool/string coercion.
Missing timeouts/home/venue/roof and OT are not defaulted. The season range does
not turn retrospective model output into historically available evidence.

Quarter clocks are integer 0–900. Q1/Q3 add 900 to form half time; Q2/Q4 do not.
Zero-clock cases are encoding/boundary probes, **not automatically terminal states**
or expected EP=0. Field endpoints 0/100 and distance zero are deferred from this
narrow experiment rather than guessed. Neutral-site and missing-roof cases are
rejected before inference: upstream standalone/bulk paths differ, and the missing
roof mapping is not an observed venue. Later admission needs a separate justified
policy and tests; do not weaken the protocol to increase coverage.

## Capture comparison and numerical criteria

`compare_captures(reference, candidate)` requires two explicit dictionaries:

- Protocol version, corpus byte SHA-256, both source commits, extracted model
  SHA-256, acquisition-manifest SHA-256 and `probability_origin`.
- Runtime language (`R` / `Python`), exact version strings, platform,
  environment-manifest SHA-256 and runner SHA-256. Their actual files/bytes must
  be verified separately; this comparator checks recorded identity consistency.
- Exact feature and class order, plus `batch` and `single` rows in corpus order.
  Every row has its case ID, actual 18 features, seven probabilities and EP.

Require exact features and identities; finite probabilities in [0,1]; sum within
absolute **1e-6** of one; and EP within **1e-5 points** of the signed seven-class
weighted sum. Check each probability across runtimes and batch/single within
absolute **1e-6**, and EP within **1e-5**. No relative tolerance, clipping,
renormalization, row sorting or silent class reordering. These are predeclared
engineering tolerances, not calibrated statistical uncertainty. Investigate a
mismatch; do not relax tolerances without a documented versioned decision.

The tests use deliberately invented probability vectors labeled `synthetic_test`
and fake identities. They exercise rejection of corrupt class/row alignment,
non-finite/boolean values, wrong sums/signs/units, missing metadata and mismatched
artifacts. They are **not golden model predictions**. Real runners must label
captured outputs `model_capture`; mixed origins fail. A successful comparison
returns `capture_comparison_pass`, always with `artifact_bytes_attested: false`
and `predictive_validation: false`. It cannot certify that a claimed runner was
executed or that either model is correct. Keep the evidence files and replay logs.

Replay the current zero-model preflight and tests:

```sh
PYTHONPATH=src python3 -m validation.ep_reference
PYTHONPATH=src python3 -m unittest discover -s tests -p test_ep_reference.py -v
```

The preflight reports `synthetic_input_protocol_pass` and explicitly unavailable
model predictions. No capture file is written. Expected current corpus SHA-256:
`5d2a4282a838e2757a0ebf948587919a28799ab5fc05ebb4b4e70bee10ac2bc9`.
The loader enforces this digest before parsing; changed cases require an explicit
versioned protocol review and pin update, not a regenerated acceptance standard.
The feature encoding's upstream notice is retained in [validation/NOTICE](../validation/NOTICE.md).

## Exit criteria and precise next unit

**Next:** reuse the verified EP acquisition, resolve/verify the intended XGBoost
source build and transitive dependency terms/hashes, provision/lock the isolated
R reference and capture its actual features/probabilities for this fixed
corpus, with a reproducible offline rerun. Stop that unit at an audited R capture
or a concrete compatibility/terms blocker; no Python serving integration, WP,
new real data, enrichment or API/UI. Do not use these synthetic cases to tune models.

Only afterward compare the independent Python candidate and record maximum errors,
batch/single checks and unchanged source/model/environment identities. A numeric
parity pass still leaves training lineage, temporal holdouts, baselines, modern-era
calibration/error analysis, historically available features and model releases
unresolved. If those cannot be evidenced, production use remains deferred and
P1.7/P1.8 may proceed descriptively without a model. No action ranking, winner
label or fourth-down mode is unlocked by this protocol.
