# EP reference runtime: full installation and EP byte equality verified

Observed during the 2026-10-27 run after PR #32 merged. **The complete pinned R
reference now installs offline, and installed fastrmodels EP bytes exactly match
the previously acquired artifact.** Seven separately locked Ubuntu packages fix
the missing development headers/tools without upgrading or removing any existing
package. R 4.6.1, XGBoost 3.4.2.1 and the 43-source R lock remain unchanged.
This completes environment setup, **not prediction capture, numerical parity or
football validation**. No booster was constructed and no prediction API was called.
Production integration stays deferred; the next unit is the fixed-corpus R capture.

## Current full reference evidence

The [native lock](../validation/ep_native.lock.json) records seven ARM64 archives:
libcurl4-openssl-dev 8.5.0-2ubuntu10.16; libicu-dev and icu-devtools 74.2-1ubuntu3.1;
and libpkgconf3, pkgconf-bin, pkgconf and pkg-config 1.8.1-2build1. R `curl` needs
libcurl headers; R `stringi` uses the existing system ICU 74.2 plus matching headers,
avoiding a bundled ICU download. Compiler/make and zoneinfo were already available.

Resolution used the fixed `20261026T000000Z` Ubuntu snapshot, noble/main+universe
with noble-updates/security, and the pinned base image's Ubuntu archive keyring.
APT simulated **0 upgraded, 7 newly installed, 0 removed**; the offline installer
then independently checked all 270 existing installed packages unchanged and
exactly seven additions. Existing libcurl4t64/libicu74 versions already matched.
The [snapshot service](https://snapshot.ubuntu.com/) and
[Ubuntu guide](https://ubuntu.com/server/docs/how-to/software/snapshot-service/)
describe date-pinned archive retrieval. The retained
[source configuration](../validation/ep_native.sources) disables only historical
metadata expiry, **not signatures or hashes**; never use it to change the host's APT.
Three InRelease files have verified signatures by Ubuntu's 2018 archive key
`F6ECB3762474EDA9D21B7022871920D1991BC93C`; exact metadata/keyring hashes are locked.
APT verified its package indexes; selected archive sizes/hashes were reconciled to
that metadata. `ep_native_audit.R` separately rechecks the preserved signed release
files, archive control fields/bytes and retained copyright identities offline.
It is not a replacement for APT's authenticated index resolution.

The [full runtime receipt](evidence/ep-full-runtime.json) records:

- the successful network-disabled build, input/recipe/log hashes and local image ID;
- all 74 installed R packages, 277 installed system packages, 46 R shared-library
  hashes and 86 resolved native-library hashes, compiler/glibc and one-thread settings;
- installed-package equality for the 9,737,490-byte raw EP payload, SHA-256
  `14a4b7e0c115d3f46fc9f341a024874b0dbcf44b30bb1f426d4f59b6f175335a`;
- two identical unprivileged, read-only, network-disabled runtime-check results.

The base's optional `tcltk.so` lacks `libtcl8.6.so`/`libtk8.6.so`. The audit initially
failed here; dependency inspection confirmed Tcl/Tk is outside nflfastR's required
closure. The final check explicitly records this exact headless-GUI limitation and
fails on any other missing library. No unrelated GUI package was installed. This
is a reference runtime, not a claim that every optional R feature works.

Intentionally wrong container and raw hashes each fail before a success receipt.
The successful build emitted R's `skipping pax global extended headers` warning
for the exact Git archives; their bytes were not changed. The XGBoost layer was
reused from the verified cache. Repeated inspection is not independent bit-for-bit
compiler reproducibility, inference compatibility or an EP accuracy measurement.

## Preserved native-stage evidence — 2026-10-26

The previous full build stopped at R `curl` 8.1.0 because `curl/curl.h` and
pkg-config were absent. Its failure and native-only receipts remain historical
evidence; they are not the current full-reference status.

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
The pinned base image retains its interpreter/system notices. The new native lock
separately records the exact Ubuntu archive and copyright hashes. Those full notices
were reviewed and are retained in each `.deb` and the image: ICU's MIT notices and
GPL-3 Debian packaging, curl/ISC/BSD/X11/OLDAP and component-specific exceptions,
and pkgconf's ISC/BSD/X11 with its GPL-covered `pkg.m4` exception. The lock's license
labels summarize notice sections, not a blanket license for the entire environment.
No source archives, binaries, images or model payloads are committed/published.

The complete packages necessarily contain more than EP. The
[bundled-asset inventory](evidence/ep-bundled-source-assets.json) records seven
fastrmodels model containers, 19 nflfastR data-like files and 27 nflreadr files,
including internal tables and upstream game/expected-output test fixtures. The
EP container exactly matches the previously acquired bytes. The prior audit only
inventoried these files. Complete package installation now necessarily processes
bundled data into R lazy-load databases; the equality check explicitly deserializes
EP only. No other model inference, training, historical analysis, PBP join, serving,
redistribution or use of bundled expected outputs as our golden capture occurred.
Other dependencies' original examples/tests remain in archives but are not executed.
Package-source terms do not establish separate data rights, training windows,
calibration or historical availability. Do not remove assets and describe a
modified minimal package as the original.

## Reproduce the current boundary

From the canonical clone with Python 3.11+ and Git:

```sh
# Explicit networked setup, fixed versions only. Valid cached files are offline.
PYTHONPATH=src python3 -m validation.ep_sources acquire \
  --git /Library/Developer/CommandLineTools/usr/bin/git
PYTHONPATH=src python3 -m validation.ep_sources verify
PYTHONPATH=src python3 -m validation.ep_sources prepare
PYTHONPATH=src python3 -m validation.ep_native acquire
PYTHONPATH=src python3 -m validation.ep_native verify
PYTHONPATH=src python3 -m validation.ep_native prepare
```

Use `--git git` on other hosts. The helper reuses the existing bounded download
transport. Git clones have an overall 180-second timeout and low-speed bound;
commit equality is checked before archiving. Temporary downloads are verified
before atomic no-clobber publication. Corrupt existing files are preserved and
rejected. Archive links, traversal, duplicates and oversized expansion fail.
The prepared build context contains only verified copies, the source lock and
installer, with checksums; unrelated/partial cache files are excluded. Its name
binds lock and installer bytes. Existing changed contexts or setup locks require
inspection, not deletion or repair. The native helper follows the same bounded
download/no-clobber policy, consumes the reviewed fixed lock (no fresh APT
resolution), and creates a content-addressed full context containing only the
verified sources, `.deb` files, locks, installers and composed Dockerfile. Every
file including that recipe is checksummed. It reuses the original native-stage
instructions, rather than copying a second compiler recipe. No daemon start or
host/container package installation is implicit in these setup commands.

With Docker already running, use the exact full context printed by `prepare`:

```sh
ep_context=.cache/ep-reference/full-context-b969db69a9c38219e328552946c8c9727ffd2fed1404880ee626361018d9b552
docker build --target full-reference --network none --platform linux/arm64 \
  --pull=false --tag nfl-ep-reference:20261027 \
  --file "$ep_context/Dockerfile" "$ep_context"
docker image inspect nfl-ep-reference:20261027 --format '{{.Id}} {{.Os}}/{{.Architecture}}'

# Verify the acquisition before deserializing it; this does not download data.
ep_artifact=.cache/ep-reference/artifacts/f1a434b6f6f67fcb2195d0aeb6cf5d7dd88c7a09
PYTHONPATH=src python3 -m validation.ep_acquire --verify "$ep_artifact"
# Use the exact image ID just inspected; this is the locally observed build ID.
ep_image=sha256:47039639b7368c88714e61f85abf719bf508668d20a639f8a051115622c63552
docker run --rm --pull never --platform linux/arm64 --network none --read-only \
  --user 65534:65534 --tmpfs /tmp:rw,nosuid,nodev,noexec,size=128m \
  --cap-drop ALL --security-opt no-new-privileges --cpus 1 --memory 768m \
  --pids-limit 64 \
  --env EP_CONTAINER_SHA256=fa45093d478fdd4534fa48860678ff99d597a67c340821db075c47fdab9102af \
  --env EP_RAW_SHA256=14a4b7e0c115d3f46fc9f341a024874b0dbcf44b30bb1f426d4f59b6f175335a \
  --mount "type=bind,src=$PWD/$ep_artifact,dst=/artifact,readonly" \
  --mount "type=bind,src=$PWD/validation/ep_full_runtime_check.R,dst=/probe.R,readonly" \
  "$ep_image" Rscript --vanilla /probe.R
```

Rebuilt image IDs/library hashes may differ with compiler output/attestations;
record the new environment rather than overwriting this historical receipt. The
old `ep_runtime.Dockerfile` and its `reference-candidate` failure are preserved for
the previous receipt; use the **composed full-context Dockerfile** above now.
The check's scratch raw payload dies with the container; immutable raw export and
actual feature/probability capture belong to the next unit. The full log remains
at `.cache/ep-reference/full-runtime-build-2026-10-27.log`, with its hash in the receipt.

Optional provenance re-audit: `ep_native_audit.R` expects the exact lock at
`/validation/ep_native.lock.json`, preserved authenticated APT lists and seven
archives under `/native/lists` and `/native/archives`, and writable container-only
`/tmp`. Mount them read-only in the same isolated image. Those preserved lists are
in `.cache/ep-reference/native-20261026`; `ep_native acquire` only downloads locked
archives, not APT metadata. A fresh metadata audit must retrieve the same signed
snapshot using the reviewed `.sources` file and verify the locked InRelease hashes.
Never resolve against the current moving mirror or alter this lock automatically.

No ports or application servers are needed by this experiment. Docker was
initially stopped, started explicitly and restored to stopped after verification.
No unrelated containers were running on the inspected startup; their configuration
was not changed. Local images, source archives and logs are retained for resumption.
Core/API/frontend environments and the daily automation are unchanged.

## Precise next unit

The 2026-10-28 [actual R capture/export](EP_R_CAPTURE.md) completes the next boundary
using this exact image: 25 synthetic cases, actual upstream matrices/probabilities,
single/batch and untraced replay checks, immutable raw export and exact offline
reproduction. Do not repeat this setup or change its pins to proceed.

Next is the independent isolated Python candidate/parity experiment with the same
raw bytes and fixed corpus, separately recorded Python dependency terms/hashes,
its own feature encoding and the unchanged comparison tolerances. The R capture
does not establish cross-runtime parity, calibration, temporal validity or football
decision quality. No Run/Pass ranking, API/UI, WP or new dataset is unlocked.
