# Independent Python EP candidate — bounded parity evidence

2026-10-29: the independent Python candidate passes the unchanged 25-case
[EP reference protocol](EP_REFERENCE_PROTOCOL.md), using the exact raw payload
from the [R capture](EP_R_CAPTURE.md). This closes the bounded engineering parity
gate, **not** a football validation or production-admission gate. Scout and the
descriptive Run/Pass engine are unchanged. No training, real-data prediction,
WP, action ranking, endpoint, UI or mandatory dependency was added.

## What ran and what passed

The candidate independently validates full state inputs and constructs the 18
features; it imports neither the feature oracle nor R predictions. The driver
passes only the already verified state-only input, raw model and environment
receipt. Python records the matrix read back from the actual `DMatrix`, not the
test oracle. The seven class probabilities come from native `Booster.predict`;
EP uses signed scoring-event weights `7,-7,3,-3,2,-2,0` from the current possession
team's perspective. This is a state value, not EPA or a Run/Pass action value.

| Check | Observed result | Predeclared requirement |
| --- | --- | --- |
| Actual feature vectors, row IDs and feature/class order | All 25 cases match exactly | Exact match |
| Maximum R/Python absolute probability difference, batch and singles | `4.656612890424627e-10` | At most `1e-6` |
| Maximum R/Python absolute EP difference, batch and singles | `3.259629019827792e-9` points | At most `1e-5` points |
| Python batch versus singles | Exactly equal | Same fixed tolerances |
| Separate offline Python execution | Identical capture bytes | Independent replay |
| Unsupported protocol states | All 16 rejected by the independent encoder | Fail closed |

Each execution performs one batch and 25 single-row predictions, CPU-only with
one inference thread. The process has networking denied, filesystem writes
restricted to its fresh capture directory, a 45-second CPU limit, 60-second wall
timeout and 1 MiB per-file output limit. Earlier captures/failure logs are never
overwritten. A separate installed-file/runtime check runs before and after it.
The 22 offline regression tests need no NumPy, XGBoost, compiler, R, Docker or
network. CI replays committed text evidence; it does **not** rebuild or execute
the native model. Synthetic unit-test probabilities remain separate from the
committed actual model captures.

The corpus still excludes OT, neutral venues, missing roof/team/timeouts,
out-of-domain years and impossible/unsupported field/distance states. These are
experimental admission rules, not restrictions added to Scout. Zero-clock inputs
are encoding probes, not a claim that terminal EP is zero. No tolerated error,
source pin, model byte or synthetic case was changed to obtain the pass.

## Runtime, sources and terms

Reference: R 4.6.1 / R XGBoost **3.4.2.1**, Linux ARM64. Candidate: Python **3.13.2** /
Python XGBoost **3.4.2**, macOS **26.6.2 ARM64**. These are different binding version
strings for the same native release; no R version string is substituted for Python.

At inspection, PyPI exposed XGBoost through 3.4.1, not 3.4.2. The already verified
[v3.4.2 source release](https://github.com/dmlc/xgboost/releases/tag/v3.4.2)
contains a 3.4.2 Python binding and native source at commit
`fdf0888bedddbd444d72994d845c59b3ca182c5b`. It was built separately on this Mac,
not replaced with a different release or an R-produced shared library. The source
archive SHA-256 is `d7de76bdaf48e9e0bc84b27c0c42f15f3d831e624d102d6c019bab7027b3cabd`.
See upstream [build options](https://xgboost.readthedocs.io/en/stable/build.html)
and [model-file portability limits](https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html).

[The wheel lock](../validation/ep_python.lock.json) records exact PyPI metadata
URLs, wheel URLs, upload times, sizes, hashes, dependency declarations and retained
notice hashes. Only seven selected wheels were downloaded; no extras or Linux-only
NCCL dependency was installed. [Hash requirements](../validation/ep_python_requirements.txt)
mirror that lock. Setup validates bytes, ZIP paths/expansion bounds, package identity
and notices before any installation; an existing bad cache is rejected, not repaired.

| Dependency | Version | Role / retained terms |
| --- | --- | --- |
| NumPy | 2.3.4 | Runtime; BSD primary and bundled notices |
| SciPy | 1.16.3 | Runtime; BSD primary and bundled notices |
| scikit-build-core | 0.11.6 | Build backend; Apache-2.0 and vendored notices |
| packaging | 25.0 | Build dependency; Apache-2.0 OR BSD-2-Clause |
| pathspec | 0.12.1 | Unmodified build dependency; MPL-2.0 |
| CMake | 3.31.10 | Build tool; packaging Apache/BSD, CMake BSD and component notices |
| Ninja | 1.13.0 | Build tool; Apache-2.0 and authors notice |

The pre-existing Python installation bootstrapped pip 25.0 (MIT primary with
vendored notices); it was not downloaded or globally upgraded. Its installed files
are included in the environment inventory. XGBoost's Apache-2.0 source/wheel notice
and both nflverse MIT notices remain retained in the caches/attribution chain.
Bundled components can have different terms: the lock is a notice inventory, not
a claim that every wheel is uniformly BSD/Apache. No dependency or model binary
is redistributed in Git. Any future redistribution must retain applicable notices
and source obligations. No separate charting/tracking dataset is licensed here.

The first build failed before XGBoost compilation: automatic SDK selection chose
MacOSX27.0.sdk, whose `arm64e.x1` stubs the installed linker could not parse. Its
source tree and `build.log` remain at `.cache/ep-python/builds/source-xzu1euzp/`.
The successful retry explicitly selected the existing **MacOSX26.5.sdk**, Apple
clang 21.0.0, deployment target 15.0, two build jobs, and `USE_OPENMP`, `USE_CUDA`,
`USE_NCCL` all OFF. No system developer setting, SDK, global package or model pin
was changed. This wheel has no libomp dependency. Build and inference were offline.

## Evidence and limits

- [Actual Python capture](evidence/ep-python-capture.json), SHA-256
  `4427d81e45418f5c3fa8adade72dc55f34fe22ca1a4fa0b03a19c491297fc2de`.
- [Environment receipt](evidence/ep-python-environment.json), SHA-256
  `6689d53532e1c20d83aa686c833a8022d3b4be6a8802ac6e0ef2c37bf4ca3b6a`:
  interpreter launcher/framework, installed package inventories, native library,
  compiler/linker/SDK settings, source, wheel, build cache/log and runner identities.
- [Capture manifest](evidence/ep-python-manifest.json), SHA-256
  `0db7175af4413603579af1d98902a484c99fbd6fb9951588ca975a01268e18bb`:
  R-reference manifest, Python driver, output hashes and comparison result.
- Raw model SHA-256 remains
  `14a4b7e0c115d3f46fc9f341a024874b0dbcf44b30bb1f426d4f59b6f175335a`.
- Locally built wheel SHA-256:
  `c507c0fcbe42cd903d251c1f34214ebbed960c56cc95e612f5c87fb37aa342b0`;
  installed native library SHA-256:
  `3f39fef4307b30ea5c8a41fd238be9e0cca6b3051997f03e61d5fb5d1ec37fee`.

Final local captures are `.cache/ep-python/captures/python-tqo0qs7t/` and
`python-ijv72fzp/`; capture/environment/empty logs agree byte-for-byte. Capture
timestamps are naturally different. The successful build remains under
`.cache/ep-python/builds/source-ec8me10q/`. No Docker daemon was needed or started.

This is repeatable inference in the recorded local environment, **not** a claim
of bit-reproducible native builds or a hermetic portable macOS image. The installed
file inventory excludes generated bytecode/RECORD; macOS system libraries are
identified by OS/linkage, not a complete redistributable OS lock. Wheel timestamps,
installation paths and host tooling can affect a rebuild. A new host must create
its own reviewed environment receipt and rerun comparison; never copy old hashes
as an assertion of its runtime. Hashes and local receipts establish consistency,
not independent attestation, training lineage or historical availability.

## Reproduce without changing production environments

Run from the canonical clone. Existing verified R export/acquisition caches are
required; recover them using the existing [R instructions](EP_R_CAPTURE.md), not
another artifact or a reserialized booster. Runtime acquisition is explicit and
separate from inference. The candidate and driver are outside the installed package.

For the current prepared environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/api-313/bin/python -m validation.ep_python_setup --verify
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/ep-python/bin/python -m validation.ep_python_capture --capture
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/api-313/bin/python -m validation.ep_python_capture --verify .cache/ep-python/captures/python-tqo0qs7t
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/api-313/bin/python -m unittest discover -s tests -p test_ep_python.py -v
```

The capture command needs permission to create a nested macOS sandbox and write
the project cache. It does not download anything. On another platform, stop and
review the runtime plan; do not silently install a newer wheel. A failed capture
reports its retained directory/logs. `--verify` checks local bytes/arithmetic,
not fresh native inference. The committed environment must not be overwritten by
an automated attempt to repair drift.

For a new **macOS ARM64 / Python 3.13.2** setup, first inspect the lock/notices,
then explicitly acquire wheels with `python -m validation.ep_python_setup --acquire`.
Create `.venv/ep-python` only if it does not already exist. Install with:

```sh
.venv/api-313/bin/python -m venv .venv/ep-python
.venv/ep-python/bin/python -m pip install --no-cache-dir --no-index --no-deps --require-hashes --find-links .cache/ep-python/wheels -r validation/ep_python_requirements.txt
PYTHONPATH=src .venv/api-313/bin/python -m validation.ep_python_setup --prepare-source
```

Use the new source directory printed by the last command. The exact successful
build invocation (substitute only its newly allocated source/output paths) was:

```sh
PATH="$PWD/.venv/ep-python/bin:/usr/bin:/bin" \
DEVELOPER_DIR=/Library/Developer/CommandLineTools \
SDKROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk \
MACOSX_DEPLOYMENT_TARGET=15.0 \
CC=/Library/Developer/CommandLineTools/usr/bin/clang \
CXX=/Library/Developer/CommandLineTools/usr/bin/clang++ \
CMAKE_BUILD_PARALLEL_LEVEL=2 PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
/usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' \
.venv/ep-python/bin/python -m pip wheel --no-cache-dir --no-deps --no-build-isolation --no-index \
  --config-settings=cmake.define.USE_OPENMP=OFF \
  --config-settings=cmake.define.USE_CUDA=OFF \
  --config-settings=cmake.define.USE_NCCL=OFF \
  --config-settings=cmake.define.CMAKE_OSX_SYSROOT=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk \
  --config-settings=cmake.define.CMAKE_OSX_DEPLOYMENT_TARGET=15.0 \
  --wheel-dir .cache/ep-python/builds/source-ec8me10q/wheels \
  .cache/ep-python/builds/source-ec8me10q/xgboost/python-package
```

Retain stdout/stderr as `build.log` beside that source directory. Inspect and hash
the new wheel; install it with a local hash-pinned requirement, `--no-index
--no-deps --require-hashes`, then run `pip check`. Record that build with
`python -m validation.ep_python_environment --build <build-directory> --output <new-receipt.json>`
under the experiment interpreter and `PYTHONPATH=src`. Pass that receipt using
`ep_python_capture --capture --environment <new-receipt.json>`. The inventory
checks pip 25.0 as bootstrapped here; a different bootstrap is a reviewed runtime
change, not a reason to fabricate matching hashes. No source build is performed
automatically by the normal application or CI.

## Admission decision and next unit

P1.6's bounded artifact/runtime/feature parity evaluation is complete. **Defer
production EP/WP and action values.** Unknown artifact training lineage/release-time
availability, missing typed context, unsupported-state policies, temporal holdouts,
baseline comparisons and calibration/error analysis remain admission gates.
Identical computations can still be identically unsuitable for a football task.
State EP alone cannot rank Run versus Pass. Keep preferred-call output withheld.

Next: the first narrow P1.7 FTN charting source audit, extending the existing
[personnel/motion review](PERSONNEL_MOTION.md). Refresh primary-source terms and
release metadata; acquire at most one reviewed 2024 artifact with a separate
immutable manifest, hashes and attribution; inventory join-key/schema availability
before any analytical integration. Full join/missingness coverage follows before
exposing a play family. Do not redo runtime setup, add models to serving, invent
motion/RPO from proxies, or treat retrospective charting as available in-season.
