# Actual upstream EP reference capture

2026-10-28: the offline R-capture gate passes for the unchanged **25 accepted
synthetic situations** in the [predeclared protocol](EP_REFERENCE_PROTOCOL.md).
Sixteen unsupported cases still fail preflight before inference. These are model
outputs on artificial inputs, **not NFL observations, Python parity, calibrated
forecasts or Run/Pass action values**. Production Scout/Decision code is unchanged.

## What ran and what was observed

The [driver](../validation/ep_r_capture.py) re-verifies the acquired container,
manifest and notices, fixed fixture, runner/protocol hashes and full environment.
It checks the installed runtime in a separate offline container against the entire
[previous receipt](evidence/ep-full-runtime.json), not just version strings.
The [R runner](../validation/ep_r_capture.R) checks installed-package/raw-object
equality and writes the raw vector verbatim to `ep_model.ubj`. It neither renames
the `.rda` nor re-saves/converts a booster. Each export retains the original
fastrmodels MIT notice and DESCRIPTION, bound by file hashes. This package license
does not grant rights to separate datasets or establish training lineage.

Only the 25 accepted full states and identity metadata enter R; expected vectors
and probabilities never do. R constructs half-time from the quarter clock and
calls pinned `nflfastR::calculate_expected_points()` for one batch and 25 singles.
The upstream code builds the remaining features, loads EP and calculates outputs.

R's [trace facility](https://stat.ethz.ch/R-manual/R-devel/library/base/html/trace.html)
observes the actual `newdata` argument at `predict.xgb.Booster` entry and verifies
each `xgb.load.raw(buffer)` is loading the exact exported bytes. It does not replace
feature selection, models or predictions. The runner requires 26 observed matrix
calls and 26 verified raw loads, preserving row/column order. After removing both
traces, an additional batch call must be strictly identical to the traced batch.
No source file is patched inside the image. Trace bookkeeping stays in retained
stderr logs; no global warning suppression is added (upstream's own standalone
feature helper suppresses warnings internally).

Observed results:

- All 18 actual features match every manually specified row exactly.
- Seven output probabilities are finite, in [0,1], in the pinned class order.
  Maximum sum-to-one error: `5.750916853841659e-8`, below the unchanged `1e-6` limit.
- EP matches the signed next-score weights `(7, -7, 3, -3, 2, -2, 0)`; maximum
  arithmetic error approximately `5.8e-15` points, below the `1e-5` limit.
- Single and batch captured values match exactly, as does the untraced batch.
- A second fresh-container run in a separate cache produces byte-identical
  `capture.json`, `ep_model.ubj`, `observation.json` and `runtime-check.json`.
  Manifest timestamps legitimately differ. This is repeated execution, not an
  independent model implementation, environment rebuild or statistical validation.

Text evidence: [actual capture](evidence/ep-r-reference-capture.json),
[publication manifest](evidence/ep-r-reference-manifest.json),
[instrumentation observation](evidence/ep-r-reference-observation.json).
Capture SHA-256: `2b880780cec39288ab63d7c6f96f7ce979ff013af17228803eae48340dcbd562`.
Raw export: 9,737,490 bytes, SHA-256
`14a4b7e0c115d3f46fc9f341a024874b0dbcf44b30bb1f426d4f59b6f175335a`.
The [acquired parent](EP_ACQUISITION.md) remains unchanged. Model binaries, raw
exports and runtime caches are ignored, not committed. The validator's
`artifact_bytes_attested: false` describes its narrow dictionary-only check;
actual byte verification is performed separately by the driver/R runner. Neither
local receipts nor hashes are independent third-party attestations.

## Reproduce without network or new setup

From the stable clone, use a repository Python environment with `PYTHONPATH=src`.
Docker must already be running with the reviewed local image; this command never
starts Docker, pulls images, downloads data or repairs caches. The setup path is
[EP_RUNTIME.md](EP_RUNTIME.md) if the verified image is unavailable.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/api-313/bin/python -m validation.ep_r_capture --capture
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/api-313/bin/python -m validation.ep_r_capture --verify .cache/ep-reference/captures/r-d01f69c0298f72cae1e7699b325fe91c3a959c1bcc07ff3d9d147cff67b032b6
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/api-313/bin/python -m validation.ep_r_capture --capture --output-cache .cache/ep-reference/capture-replay-2026-10-28
```

An existing valid destination is verified without executing R again; choose a
separate cache for actual inference replay. The directory identity binds the
driver, R runner, protocol, state input, environment receipt and image. Verification
fails on source drift: use the matching Git revision to verify old evidence, not a
rewritten receipt. Corrupt entries, symlinks and existing capture locks are errors;
inspect interrupted locks before retrying. Failed runs retain `.pending-*` inputs
and logs but never publish a success manifest. Only disposable staging is writable
to the container; the artifact/scripts are read-only, with no repo or Docker socket
mounted. Published captures are logically immutable (replay checks hashes), not
OS write-protected against their owner.

Execution uses exact image ID
`sha256:47039639b7368c88714e61f85abf719bf508668d20a639f8a051115622c63552`,
Linux ARM64, R 4.6.1, XGBoost R 3.4.2.1, nflfastR 6.0.0 and fastrmodels 2.1.0.
Each container has no network, read-only root, UID/GID 65534, dropped capabilities,
no-new-privileges, one CPU/thread, 768 MiB memory limit, 64 PIDs and bounded tmpfs.
Each invocation has a 60-second timeout; timeout cleanup targets only its unique
container name. No ports or persistent servers are used by the experiment.
The recorded image is local ARM64 evidence, not a published portable image. An
independent rebuild/platform needs a separately verified environment receipt, not
a retagged image or silently rewritten old receipt. This run proves re-execution
on the recorded environment, not bit-for-bit reproducibility of compilation.

The first development attempt reached capture but failed during repeated trace
cleanup. Its logs remain in `.cache/ep-reference/captures/.pending-pznzeg7d`; it was
not published. Guarding cleanup fixes the harness without altering model outputs,
source pins, fixtures or tolerances. Final capture and replay both exit successfully.

## Boundary and next unit

Twenty-one offline tests cover runner safety/publication/error paths and text
evidence integrity; CI does not install R/Docker, rerun inference or prove that
receipts are authentic. Mock runner tests use explicitly synthetic bytes and
probabilities, kept separate from the recorded actual R output.

Next: independently prepare the isolated Python 3.13.2 / native XGBoost candidate,
record the exact Python binding/dependency artifact versions, hashes and terms,
and compare its own features and batch/single predictions on the unchanged corpus
using this same raw EP export. Do not import the feature oracle, copy R outputs,
relax tolerances or silently substitute a model/version. Report any incompatibility
before widening scope. No serving dependency, WP, real data, action ranking, API/UI
or model training is authorized by this reference success. Temporal availability,
training lineage, calibration and decision-quality evaluation remain open.
