# Local API container

P1.10's first packaging slice serves the existing Scout `/v1/report` and Decision
`/v1/decision` endpoints from one operator-selected immutable PBP snapshot. It
contains no frontend, database or research model runtime. The core and optional
API contracts are unchanged; see [API.md](API.md) for query/response definitions.
This is a local operating path, not a public deployment or football validation.

## Reviewed build inputs

Build from the canonical repository root with a running Docker Engine:

```sh
docker build --target api -f docker/api.Dockerfile -t nfl-oi-api:local .
```

Linux **amd64 and arm64**, CPython **3.13**, are the supported targets. Specify
`--platform linux/amd64` or `--platform linux/arm64` when cross-building; emulation
must be available to execute the target's build steps and tests. The default uses
the engine's native architecture. No image is pushed to a registry by this build
or by CI.

The official `python:3.13-slim-bookworm` base is pinned by index digest
`sha256:a5a7017efc5969e00ae2b91c8eb0631049a569652aa4ffc4501769049ae45c72`.
[docker/api-inputs.json](../docker/api-inputs.json) records the two selected platform
manifest digests and all 15 approved wheel files for the 14 runtime packages.
On 2026-11-14, downloaded bytes matched the exact PyPI release JSON SHA-256 values;
wheel metadata supplied the recorded license expressions. Versions match the
existing API constraints: no dependency upgrade or test extra is introduced.
Wheel distribution metadata/notices remain in `/opt/api-deps`; base-image notices
are retained.
[api-requirements.lock](../docker/api-requirements.lock) requires exact versions
and SHA-256 hashes, and the build accepts binary wheels only. The pinned base
contains Python **3.13.18** and pip **26.2.2**. It performs installation without
an isolated source build, compiler or separately resolved build backend. Reviewed
project Python sources are copied directly to `/app/opponent_intelligence`; the
project is not installed as a wheel in this image. Module invocation still works.
This closes the image's previously unpinned artifact/build-tool boundary without
changing the existing general-purpose API/test installation instructions.

The Dockerfile-specific ignore file denies the repository by default, then admits
only the direct package `.py` files and four named container input files. Each
re-included parent is re-excluded before admitting its children, preventing caches
or packaging metadata from entering via a parent exception. Raw/processed data,
`.git`, credentials, virtual environments, frontend/node dependencies, tests and
research artifacts are outside the build context and serving image. The separate
`context-audit` target exports the actual filtered context for verification; it is
not a runnable service image and must not be the normal build target.

Network access to the pinned registry image and PyPI wheels is needed on a cold
build. The serving process performs no acquisition. Pins and hashes identify
inputs, not a promise of byte-identical image IDs across builders: BuildKit,
image metadata/timestamps, attestations and local source changes can differ.
They also do not guarantee future registry availability or current security.
Update pins deliberately and rerun checks; never replace a changed wheel's expected
hash just to make an unexplained build failure disappear.

The approach follows Docker's [digest pinning, minimal contexts and non-root
build guidance](https://docs.docker.com/build/building/best-practices/), pip's
[hash-checked wheel installs](https://pip.pypa.io/en/stable/topics/secure-installs/)
and FastAPI's [single-process container guidance](https://fastapi.tiangolo.com/deployment/docker/).

## Configure and run on localhost

Acquire/verify a real snapshot separately using [INGESTION.md](INGESTION.md).
The container never downloads one. Set an absolute path to the existing
content-addressed directory and an accurate label; preserve the hash directory's
basename inside the container because the manifest verifier checks it.

```sh
snapshot_dir="$PWD/data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06"
snapshot_id="${snapshot_dir##*/}"
docker run --rm --name nfl-oi-api-local \
  --read-only --cap-drop ALL --security-opt no-new-privileges \
  --pids-limit 64 --memory 512m --cpus 1 \
  --publish 127.0.0.1:8000:8000 \
  --mount "type=bind,source=$snapshot_dir,target=/snapshots/$snapshot_id,readonly" \
  --env "NFL_OI_SNAPSHOT=/snapshots/$snapshot_id" \
  --env 'NFL_OI_SOURCE_LABEL=nflverse 2024 retrospective snapshot; acquired 2026-09-30 UTC' \
  nfl-oi-api:local
```

The recorded directory above is an example, not a request to fetch current bytes.
Use your actual immutable directory and label. `--mount` rejects a missing host
path instead of creating it. Files and parent directories must be readable and
traversable by numeric UID/GID **10001:10001**; the container does not chown them.
No privileged mode, Docker socket mount or root user is needed. The read-only
mount protects against writes from this container, not later edits on the host.
Startup verifies hashes/manifest and parses a resident snapshot before serving;
restart to adopt a different snapshot. No real snapshot is included in the image.

Inside the container Uvicorn listens on `0.0.0.0:8000` so Docker can forward the
host port. Only **127.0.0.1:8000** is published by this command. Do not remove that
host address or turn this local recipe into public hosting without a separate
deployment design. The normal bridge network permits outbound traffic; the app
has no acquisition path, and tests independently run it with networking disabled.
Loopback publishing is not an egress policy or authentication.

The exec-form command runs one Uvicorn process with `--workers 1`, required lifespan
startup and proxy-header trust disabled. Do not add reload, workers or replicas:
capacity protection and the resident snapshot are process-local. The 512 MiB,
one CPU and PID limits are tested with tiny synthetic data, not a realistic NFL
workload capacity benchmark. The root filesystem is read-only with all capabilities
dropped and new privileges disabled. Python bytecode writes are disabled; no
writable data volume is needed.

The Docker health check probes local `/openapi.json` after startup; it is a basic
liveness/readiness check, not a dataset freshness or analytics-quality assertion.
Startup exits nonzero for missing/blank configuration, a relative directory,
missing files or corrupt bytes. Configuration/startup logs are for the operator;
HTTP errors retain the existing sanitized envelope. `/docs` and `/redoc` stay off.

In a second terminal:

```sh
curl --get 'http://127.0.0.1:8000/v1/decision' \
  --data-urlencode 'team=CAR' --data-urlencode 'season=2024' \
  --data-urlencode 'before_week=19' --data-urlencode 'down=3' \
  --data-urlencode 'distance_min=4' --data-urlencode 'distance_max=4'
docker inspect --format '{{.State.Health.Status}}' nfl-oi-api-local
docker stop --time 5 nfl-oi-api-local
```

`--rm` removes that named container on exit; its image and the host snapshot remain.
Stop only the container you started, not unrelated containers or the Docker engine.
The existing Vite local viewer can use the same localhost API address. Frontend
container packaging is a separate next unit; no CORS, TLS or deployment changes
are implied here.

## Verification and refresh procedure

The standalone harness requires only host Python 3.11+ standard library and Docker;
it uses the existing synthetic snapshot factory, never the operator's real data.

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 \
  NFL_OI_CONTAINER_IMAGE=nfl-oi-api:local \
  python3 -m unittest discover -s tests_container -v
```

Eight checks exercise actual BuildKit context export; input/version/hash consistency;
non-root UID/GID; exact source tree and installed dependency versions; read-only
root/mount and disabled network; complete Scout offense/defense and Decision core
parity, including league/bootstrap evidence; independent Run/Pass expectations;
empty/error/cost boundaries; six invalid startup cases; and graceful SIGTERM.
A separate ephemeral loopback-only published port verifies the operating recipe.
Other HTTP checks run inside `--network none` containers. Tests use unique names,
register cleanup before creation, and remove their own containers and temporary
snapshots even on assertion failure. No `prune`, shared service shutdown or manual
change to an existing snapshot occurs. Test labels identify invented data/metadata.

CI adds one amd64 container job alongside the existing eight jobs. It builds from
reviewed inputs and runs these checks without installing the API on the host.
The Dockerfile has no new statistical formulas. Equality with core output verifies
packaging and transport, not causal validity, model calibration, historical feature
availability, full-season performance or future decision quality.

To review a dependency/base update:

1. Inspect the official Python image index/platform manifests and choose a new
   explicit digest. Record it in both Dockerfile stages and `api-inputs.json`.
2. Download the existing reviewed API roots with `pip download --only-binary=:all:`
   under the desired constraints, for CPython 3.13 (`--implementation cp --abi cp313`)
   and each `manylinux2014_x86_64` / `manylinux2014_aarch64` platform. Do this in
   separate temporary directories. Review any proposed version/closure change.
3. Verify each wheel SHA against its exact `https://pypi.org/pypi/NAME/VERSION/json`
   release record and inspect its `METADATA` and notices. Update the wheel inventory
   and all hashes in the lock together, retaining both architectures. No source
   distribution fallback or automatic acceptance of newly available artifacts.
4. Build and run the full container harness on both architectures; run core/API and
   frontend regressions as applicable. Record source revision, runtime/image IDs,
   actual checks and limits. Keep changes on a reviewed feature PR.

The repository-wide version-only API constraints continue serving Python 3.11–3.13
local/test environments. This narrower container lock is not a universal wheel
lock for those versions or other operating systems. Actual publication/CI evidence
and the next bounded unit are in [STATUS.md](STATUS.md).
