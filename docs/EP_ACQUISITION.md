# EP artifact acquisition and isolated R object preflight

Observed 2026-10-25, after PR #30 merged. **The package EP container is acquired
and byte-verified; a disposable offline R process inspected its raw object. No
XGBoost inference, model probabilities, installed-package equality, runtime
parity or football-quality validation has occurred.** This completes the
acquisition/object-preflight prerequisite, not the full R reference capture.

## Evidence boundary

| Representation | Verified observation |
| --- | --- |
| Pinned package `data/ep_model.rda` | 2,864,452 bytes; Git blob `f1a434b6f6f67fcb2195d0aeb6cf5d7dd88c7a09`; SHA-256 `fa45093d478fdd4534fa48860678ff99d597a67c340821db075c47fdab9102af` |
| Object loaded by base R | Exactly one `ep_model`, type `raw`, no attributes; 9,737,490 bytes; SHA-256 `14a4b7e0c115d3f46fc9f341a024874b0dbcf44b30bb1f426d4f59b6f175335a` |
| Similarly named archive UBJ | Prior audit metadata says 9,737,452 bytes; not acquired or asserted equivalent |
| Actual EP predictions | Unavailable; no inference dependency installed |

The [acquisition manifest](evidence/ep-package-acquisition.json) records the exact
fastrmodels 2.1.0 commit, source URLs, acquisition timestamp, observed release time,
Git-framed blob hashes, local SHA-256/size and pinned MIT notice/declaration.
The [R inspection receipt](evidence/ep-r-object-inspection.json) binds that manifest,
R runner, Python driver and image digest. Raw bytes were written only to disposable
container scratch space to hash them, not exported as a final installed-package
payload. The leading bytes are recorded as hex, not decoded as text or treated as
proof of XGBoost compatibility. An exploratory text-print attempt correctly failed
on embedded NUL bytes; the committed probe uses hex and subsequently passed.

Only the EP container, its `LICENSE.md` and `DESCRIPTION` were downloaded from
fastrmodels. No WP/CP/xYAC/FG model, training dataset or NFL observation was acquired.
The original audit's null local hashes are preserved as a historical record.
Source/package terms do not establish training-data rights, first publication,
training seasons, calibration, historical availability or action values.

## Replay without changing production dependencies

From the canonical repository, using Python 3.11+:

```sh
# Explicit networked setup, fixed reviewed URLs; existing valid cache is offline.
PYTHONPATH=src python3 -m validation.ep_acquire --acquire

# Explicit offline verification; never repairs or refreshes a corrupt snapshot.
PYTHONPATH=src python3 -m validation.ep_acquire --verify \
  .cache/ep-reference/artifacts/f1a434b6f6f67fcb2195d0aeb6cf5d7dd88c7a09
```

`ep_acquire.py` reuses the existing bounded HTTP transport: 30-second socket
timeouts, at most three attempts and fixed byte limits. It adds model-specific
Git-blob verification, retained notices and atomic directory publication. An
exclusive setup lock serializes writers; an existing/stale lock fails explicitly
and needs inspection, not automatic deletion. Cache hits rehash every pinned file
and validate the manifest without network access. Corrupt, extra, missing or
symlinked files fail without replacement. The cache is ignored by Git. No model
binary is redistributed in this PR; only text evidence/receipts are committed.

With Docker already running, explicitly acquire the reviewed **ARM64** image:

```sh
docker pull --platform linux/arm64 \
  rocker/r-ver@sha256:fb487cf8a2029fc1dbc17621cf41ac913d49ac74a1ff9e27bf9bbc982e55d08d
PYTHONPATH=src python3 -m validation.ep_probe --snapshot \
  .cache/ep-reference/artifacts/f1a434b6f6f67fcb2195d0aeb6cf5d7dd88c7a09
```

The [Rocker image documentation](https://rocker-project.org/images/versioned/r-ver.html)
describes fixed-R images and architecture limitations. This digest actually ran
R 4.6.1 on `aarch64-unknown-linux-gnu`; only that platform was exercised. Base R and
its bundled packages are available in this image, not the planned inference stack.
Image pinning records the base filesystem; it is not a complete model runtime lock.

The Python probe verifies the artifact before launching Docker, refuses automatic
pulls, and uses an unprivileged UID, read-only root and mounts, no network, dropped
capabilities, no new privileges, one CPU, 512 MiB memory, 64-process limit and
bounded disposable scratch space. It mounts only the artifact directory and R
script, never the Docker socket, home, raw PBP or entire repository. The R runner
checks the container hash again before `load()`. Its separate environment must
contain exactly the expected unclassed raw object. Probe timeouts/errors trigger
cleanup of only its uniquely named container; cleanup failures are reported.
The helper neither starts/stops Docker nor installs packages. Docker was started
manually for this run and returned to its prior stopped state after verification;
its auto-started unrelated services were not edited. The pulled image remains
cached for a future run; no global R installation or developer setting changed.

## Runtime setup finding — do not silently downgrade

The [protocol](EP_REFERENCE_PROTOCOL.md) proposed R XGBoost **3.4.2.1** but had not
resolved an installable lock. On this run, both of these exact source URLs returned
HTTP 404:

- `https://cran.r-project.org/src/contrib/xgboost_3.4.2.1.tar.gz`
- `https://packagemanager.posit.co/cran/2026-10-24/src/contrib/xgboost_3.4.2.1.tar.gz`

Inside the R image, `available.packages()` against the dated mirror reported
XGBoost **3.2.1.1**, jsonlite 2.0.0, data.table 1.18.6.1, dplyr 1.2.1,
nflfastR 6.0.0 and fastrmodels 2.1.0. These are observed package-index entries, not
installed packages, immutable source hashes or a resolved dependency lock.

An alternative exists: [upstream v3.4.2](https://github.com/dmlc/xgboost/releases/tag/v3.4.2)
resolved to source commit `fdf0888bedddbd444d72994d845c59b3ca182c5b`.
The release advertised `xgboost-src-3.4.2.tar.gz`, asset ID `565276642`,
2,749,031 bytes and SHA-256
`d7de76bdaf48e9e0bc84b27c0c42f15f3d831e624d102d6c019bab7027b3cabd`.
That source archive was **not downloaded or locally verified**. The R declaration
states 3.4.2.1 / Apache-2.0. [Upstream build guidance](https://xgboost.readthedocs.io/en/stable/build.html#building-r-package-from-source)
requires source/submodule and compiler handling; a Git tag alone is not a built
R package or a dependency lock. No version substitution was made, and no claim
that this source build is impossible is intended.

## Tests, limitations and precise continuation

Offline tests use invented artifact bytes and mocked R output. They cover pins,
Git framing versus plain SHA-1, manifests, corruption even after metadata
rehashing, immutable cache reuse, publication/transport failures, writer locks,
symlinks, mount-option injection, input/runner drift, bounded Docker invocation
and owned-container cleanup. Receipt tests check consistency, not binary
attestation. Core CI never downloads a model, starts Docker or installs R.
Actual local container inspection and offline replay are recorded separately.

**Next unit:** resolve and verify the pinned XGBoost source-build route and its
transitive R/native dependencies, retain their terms/hashes and lock the isolated
reference environment. Then install the pinned nflfastR/fastrmodels sources,
verify installed EP bytes against this acquired container, and capture actual
features/probabilities for the unchanged 25-case corpus with an offline rerun.
Any unavoidable bundled package assets must be inventoried explicitly; do not
execute additional models or relabel a modified/minimal package as the original.
Stop at an audited R capture or a concrete build/terms failure. The independent
Python candidate, calibration/temporal assessment, API/UI and ranking remain later.
The original R-capture acceptance item is still open; this prerequisite does not
unlock a preferred call or change Scout's EPA calculations.
