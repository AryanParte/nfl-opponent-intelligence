# EP reference runtime: native stage verified, full reference incomplete

Observed 2026-10-26 after PR #31 merged. **R XGBoost 3.4.2.1 now builds and
loads from its verified upstream source in the pinned R 4.6.1 ARM64 image.**
The full nflfastR reference build failed at R package `curl` 8.1.0 because the
image lacks libcurl development headers (`curl/curl.h`); `pkg-config` is absent
too. This is a concrete native-dependency setup failure, not an incompatible EP
model, an access blocker requiring Aryan, or proof that the reference cannot run.
No NFL model was loaded or used to generate predictions. Production stays deferred.

## What is verified

- [Source lock](../validation/ep_runtime.lock.json): 43 source distributions,
  consisting of 40 required CRAN dependencies plus pinned XGBoost, fastrmodels and
  nflfastR. The fixed 2026-10-24 package index determines dependency order; XGBoost
  comes from upstream v3.4.2, **not** the mirror's older 3.2.1.1 package. Every
  archive has actual SHA-256/size, retained declaration/notice hashes and bounds.
  This is a **source-resolution lock**, not a complete native environment lock.
- The XGBoost release archive matches its published 2,749,031-byte size and
  `d7de76bdaf48e9e0bc84b27c0c42f15f3d831e624d102d6c019bab7027b3cabd` digest.
  Its R declaration is 3.4.2.1 and its bundled dmlc-core source is present.
  [Upstream build guidance](https://xgboost.readthedocs.io/en/stable/build.html#building-r-package-from-source)
  supports installation from the complete source checkout. No source patch,
  version downgrade, replacement model or production dependency was introduced.
- Full nflverse source commits match the previous protocol. Codeload timed out
  after three bounded attempts, leaving a truncated archive; it was preserved
  and excluded. Git transport recovered the exact release commits. `git archive`
  produced separately named, hashed archives, reproduced through the finished
  setup helper in fresh disposable directories. Git used: 2.50.1 (Apple Git-155).
  Changed archive bytes/toolchain output fail verification, not an automatic repin.
- Native build: R 4.6.1, XGBoost 3.4.2.1, jsonlite 2.0.0, data.table 1.18.6.1;
  existing Matrix 1.7-5; GNU C++ 13.3.0 and glibc 2.39. Compilation used two make
  workers, no network or GPU. An unprivileged, read-only, network-disabled check
  with one CPU and XGBoost `nthread=1` reproduced identical JSON twice.
- [Native receipt](evidence/ep-native-runtime.json) records all 34 installed R
  packages, the XGBoost shared-library hash and 20 linked native-library hashes,
  source lock, final Dockerfile, check-runner and local image identities. It
  explicitly records `full_reference_ready: false` and no model execution.
  Image IDs can change with build attestations even when filesystem layers match;
  a cached rebuild is not proof of independent, bit-for-bit compiler reproducibility.

## Sources, terms and unavoidable bundled assets

Original source archives/notices remain in the ignored cache and local image;
neither binaries nor images are published in this PR. Declared terms include MIT,
Apache-2.0, MPL-2.0, GPL and LGPL. jsonlite retains its bundled yajl notice; XGBoost
retains dmlc-core's notice. stringi's `LICENSE` contains its BSD-style terms,
GPL-covered LaTeX word-count component and Unicode/ICU third-party notices. The
source lock records the declarations and notice hashes, not a blanket legal opinion
or a claim that every bundled dataset has been independently licensed for reuse.
The pinned base image retains its interpreter/system notices; new native package
sources/terms/hashes still need a separate reviewed lock before the next build.

The complete packages necessarily contain more than EP. The
[bundled-asset inventory](evidence/ep-bundled-source-assets.json) records seven
fastrmodels model containers, 19 nflfastR data-like files and 27 nflreadr files,
including internal tables and upstream game/expected-output test fixtures. The
EP container exactly matches the previously acquired bytes. These additional
assets were only inventoried by filenames/bytes, not loaded, trained on, treated
as our golden capture, joined to PBP, served or redistributed. Other dependencies'
original examples/tests are also retained in their archives but not executed.
Package-source terms do not establish separate data rights, training windows,
calibration or historical availability. Do not remove assets and describe a
modified minimal package as the original.

## Reproduce the verified boundary

From the canonical clone with Python 3.11+ and Git:

```sh
# Explicit networked setup, fixed versions only. Valid cached files are offline.
PYTHONPATH=src python3 -m validation.ep_sources acquire \
  --git /Library/Developer/CommandLineTools/usr/bin/git
PYTHONPATH=src python3 -m validation.ep_sources verify
PYTHONPATH=src python3 -m validation.ep_sources prepare
```

Use `--git git` on other hosts. The helper reuses the existing bounded download
transport. Git clones have an overall 180-second timeout and low-speed bound;
commit equality is checked before archiving. Temporary downloads are verified
before atomic no-clobber publication. Corrupt existing files are preserved and
rejected. Archive links, traversal, duplicates and oversized expansion fail.
The prepared build context contains only verified copies, the source lock and
installer, with checksums; unrelated/partial cache files are excluded. Its name
binds lock and installer bytes. Existing changed contexts or setup locks require
inspection, not deletion or repair. No daemon start or package installation is
implicit in these commands.

With Docker already running, use the exact context printed by `prepare`:

```sh
ep_context=.cache/ep-reference/context-b0bf131850e7a9b248fc393a86d361a83e9dc49847f47a1cd8662f8364a7b152
docker build --target xgboost-runtime --network none --platform linux/arm64 \
  --pull=false --tag nfl-ep-xgboost:3.4.2.1-r4.6.1 \
  --file validation/ep_runtime.Dockerfile "$ep_context"
docker run --rm --pull never --platform linux/arm64 --network none --read-only \
  --user 65534:65534 --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m \
  --cap-drop ALL --security-opt no-new-privileges --cpus 1 --memory 512m \
  --pids-limit 64 \
  --mount "type=bind,src=$PWD/validation/ep_runtime_check.R,dst=/probe.R,readonly" \
  nfl-ep-xgboost:3.4.2.1-r4.6.1 Rscript --vanilla /probe.R
```

The native stage is experiment setup only. The Dockerfile's default/final
`reference-candidate` target is **known incomplete**, not a ready serving image.
The full install attempt verified all archive checksums, installed `cli`, then
stopped at `curl`; [failure excerpt](evidence/ep-reference-build-failure.txt).
That attempt preceded the final stage-name/comment split; its install commands
and source lock were unchanged. The native stage was verified again with the
final Dockerfile. Full logs stay in `.cache/ep-reference/`; the receipt retains
the failure log hash. The check's initial visible R config return was wrapped in
`invisible()` so the final stdout is JSON only; its offline replay then passed.

No ports or application servers were started by this experiment. Docker was
initially stopped, started explicitly and restored to stopped after verification.
No unrelated containers were running on the inspected startup; their configuration
was not changed. Local images, source archives and logs are retained for resumption.
Core/API/frontend environments and the daily automation are unchanged.

## Precise next unit

Resolve and verify the missing native development dependencies inside the pinned
container (starting with libcurl headers and pkg-config, then the remaining
packages' system requirements). Record exact packages, source/repository snapshot,
hashes, terms and any necessary base-library changes. Do not use a floating apt
upgrade, change host developer settings, silently downgrade R/XGBoost or weaken
the offline build. Reuse this source cache/native build layer.

Complete the full offline installation, record a full environment manifest,
verify installed fastrmodels EP bytes against the acquired container, and capture
actual upstream features/probabilities for the unchanged 25-case corpus with
offline replay. The independent Python candidate comes afterward. Native library
loadability alone does not establish EP compatibility, numerical parity, temporal
validity or football decision quality. No Run/Pass ranking, API/UI or new model
claim is unlocked by this setup work.
