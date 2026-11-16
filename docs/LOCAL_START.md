# Run the local portfolio app

Scout and Run/Pass Decision Lab run in the same React app. This path uses your
Python environment and Node, with one terminal and no Docker requirement. The
launcher is supported on **macOS and Linux** (use WSL on Windows; native Windows
process cleanup is not supported). Use Python **3.11–3.13** and Node **24.19.0**
(`web/.nvmrc`; supported range 24.15+ within major 24).

## One-time setup

Clone the existing repository, then run setup from its root:

```sh
git clone https://github.com/AryanParte/nfl-opponent-intelligence.git
cd nfl-opponent-intelligence
python3 -m venv .venv/local
.venv/local/bin/python -m pip install -c requirements/api-constraints.txt '.[api]'
npm --prefix web ci
```

Install/select Node with your normal version manager before `npm ci`. Package
installation needs network access. Nothing installs automatically on startup.
The optional API dependencies stay out of the standard-library reporting core.

Choose an existing immutable 2024 PBP snapshot, or explicitly acquire one once:

```sh
PYTHONPATH=src .venv/local/bin/python -m opponent_intelligence.fetch --season 2024
```

This separate command needs network access on first acquisition, verifies source
bytes and prints the saved snapshot directory. Read [source terms and acquisition
limits](INGESTION.md). Upstream revisions can change the content-addressed path;
use the path and retrieval date from **your** resulting manifest, not a hard-coded
historical hash. Normal reports do not require freshness or continued acquisition.
No raw NFL season files are committed to this repository.

## Start both services

Replace the placeholders with the immutable directory and its accurate provenance:

```sh
.venv/local/bin/python scripts/start_local.py \
  --snapshot '/absolute/path/to/the/content-addressed-snapshot-directory' \
  --source-label 'nflverse 2024 retrospective snapshot; acquired YYYY-MM-DD UTC'
```

Relative paths are resolved from your current directory; quotes preserve spaces.
The snapshot must contain its manifest and archive, not a mutable `current.json`
pointer. The API performs the existing hash/schema validation before serving.
No download, fallback, data rewrite or analytics calculation is added by startup.

Wait for **Ready**, then open **http://127.0.0.1:5173/**. Both services share this
terminal's logs. The launcher starts the API on loopback port 8000, waits for its
startup, then starts Vite on loopback port 5173 using the existing same-origin
proxy. It uses the Python interpreter that invoked the script and the installed
local Vite entry point; it does not invoke an installer or create a daemon.

- **Scout:** choose team, offense/defense, historical cutoff and optional context,
  build the report, inspect denominators/league/support, and download report JSON.
- **Decision Lab:** select an offensive situation, compare observed Run/Pass
  evidence, optionally label your own call, and download decision JSON. The app
  withholds a preferred call; descriptive differences are not causal recommendations.
- Select controls matching your snapshot. Default CAR / 2024 / before week 19 is
  an example query, not preloaded evidence. Downloads retain the original validated
  response; local call selection does not alter Decision evidence.

**Ctrl-C stops both services**, including their owned helper processes. SIGTERM
also shuts them down. If either service fails, the launcher exits unsuccessfully
and stops the other; no automatic restart or background monitoring occurs.
It requests graceful shutdown, waits up to five seconds, then terminates remaining
owned process groups. Forced OS termination of the launcher (SIGKILL/power loss)
cannot perform cleanup; if that happens, stop the specific services you started.

## When startup fails

- Missing Python packages or Vite/Node: use the setup above in the same environment.
- Port 8000 or 5173 in use: stop that service yourself, then retry. The launcher
  refuses to reuse or kill existing servers and never chooses alternate ports.
- Missing/corrupt snapshot or invalid label: check the selected directory and
  manifest; the original API error remains visible. Do not change expected hashes
  to accept unexplained bytes. Source labels must be nonblank and at most 300 characters.
- Startup taking more than 30 seconds per service: inspect the printed error and
  local resources. This is a bounded local startup check, not a load benchmark.

The [separate-terminal setup](API.md#install-and-start) and [optional API
container](CONTAINER.md) remain available. The launcher owns both local processes;
stop it before using the container on port 8000. To use that container, run the
viewer separately with `npm --prefix web run dev`. No frontend container,
orchestration, public hosting or database is needed for portfolio v1.

## Verify the launcher

With the optional API dependencies and `web/node_modules` installed, from the root:

```sh
PYTHONPATH=src .venv/local/bin/python -W error -m unittest discover -s tests_local -v
```

These tests create only temporary **synthetic** snapshots with invented acquisition
metadata; they never fetch real NFL data. They exercise real API/Vite/proxy requests,
unchanged snapshot bytes, occupied-port refusal, startup errors/timeouts, service
exit and graceful/forced cleanup. Ports 8000/5173 must be free. CI runs them before
the existing Chromium suite, which separately covers both modes and native JSON
downloads. Local success is not proof of universal browser support or football
model validity.

Implementation references: Python [child sessions/processes](https://docs.python.org/3/library/subprocess.html)
and [signal handling](https://docs.python.org/3/library/signal.html), and the
[Vite CLI](https://vite.dev/guide/cli.html). The launcher keeps the existing Vite
proxy/file restrictions and one-worker API contract.
