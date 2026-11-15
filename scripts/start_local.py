"""Run the existing API and Vite viewer together; macOS/Linux, no installation."""

import argparse
import importlib.util
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


ROOT = Path(__file__).resolve().parents[1]
PORTS = (8000, 5173)
STARTUP_SECONDS = 30
STOP_SECONDS = 5


class StartupError(Exception):
    pass


def preflight(snapshot, label):
    if os.name != "posix":
        raise StartupError("Use macOS, Linux or WSL for this local launcher.")
    if not snapshot.is_dir() or not (snapshot / "manifest.json").is_file():
        raise StartupError("Choose an existing immutable snapshot directory containing manifest.json; see docs/LOCAL_START.md.")
    if not label.strip() or len(label) > 300:
        raise StartupError("Source label must be nonblank and at most 300 characters.")
    if any(importlib.util.find_spec(name) is None for name in ("fastapi", "uvicorn")):
        raise StartupError("API dependencies are missing from this Python environment; follow docs/LOCAL_START.md.")
    node = shutil.which("node")
    vite = ROOT / "web/node_modules/vite/bin/vite.js"
    if node is None or not vite.is_file():
        raise StartupError("Select Node 24.19.0 and run npm --prefix web ci first; see docs/LOCAL_START.md.")
    version = subprocess.run([node, "--version"], capture_output=True, text=True,
                             timeout=5, check=True).stdout.strip()
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", version)
    if not match or not (24, 15, 0) <= tuple(map(int, match.groups())) < (25, 0, 0):
        raise StartupError("Unsupported Node version; select Node 24.19.0 (web/.nvmrc).")
    for port in PORTS:
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError as exc:
                raise StartupError(f"Port {port} is unavailable. Stop its owner yourself; no existing service was changed.") from exc
    return node, vite


def check_children(children):
    for name, child in children:
        code = child.poll()
        if code is not None:
            raise StartupError(f"{name} exited (code {code}); see its output above.")


def wait_ready(url, children, stopping):
    # Ignore machine HTTP proxies: these readiness requests are loopback-only.
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + STARTUP_SECONDS
    while not stopping():
        check_children(children)
        if time.monotonic() >= deadline:
            raise StartupError(f"Local service did not become ready within {STARTUP_SECONDS}s: {url}")
        try:
            with opener.open(url, timeout=0.5) as response:
                if response.status == 200:
                    check_children(children)
                    return
        except (URLError, OSError):
            pass
        time.sleep(0.1)


def stop_children(children):
    # Each child owns a new POSIX session. Signal only these process groups, never
    # an arbitrary process found by name/port. Include Vite's helper descendants.
    def send(child, sig):
        try:
            os.killpg(child.pid, sig)
        except ProcessLookupError:
            pass

    for _, child in children:
        send(child, signal.SIGTERM)
    deadline = time.monotonic() + STOP_SECONDS
    for _, child in children:
        try:
            child.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
    for _, child in children:
        send(child, signal.SIGKILL)  # Also clean helpers left after a leader exits.
        child.wait()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True,
                        help="Existing content-addressed snapshot directory; never downloaded by this command")
    parser.add_argument("--source-label", required=True, help="Accurate provenance label (1–300 characters)")
    args = parser.parse_args(argv)
    children = []
    stop_requested = False

    def request_stop(signum, frame):
        nonlocal stop_requested
        stop_requested = True

    previous = {}
    try:
        snapshot = args.snapshot.expanduser().resolve()
        node, vite = preflight(snapshot, args.source_label)
        previous = {sig: signal.signal(sig, request_stop) for sig in (signal.SIGINT, signal.SIGTERM)}
        env = {key: value for key, value in os.environ.items() if not key.startswith("UVICORN_")}
        env.update(PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1",
                   NFL_OI_SNAPSHOT=str(snapshot), NFL_OI_SOURCE_LABEL=args.source_label)
        services = (
            ("API", [sys.executable, "-m", "uvicorn", "opponent_intelligence.api:app_from_env",
                     "--factory", "--host", "127.0.0.1", "--port", "8000", "--workers", "1",
                     "--lifespan", "on", "--no-proxy-headers", "--timeout-graceful-shutdown", "5"],
             ROOT, "http://127.0.0.1:8000/openapi.json"),
            ("Viewer", [node, str(vite), "--host", "127.0.0.1", "--port", "5173",
                        "--strictPort", "--clearScreen", "false"],
             ROOT / "web", "http://127.0.0.1:5173/"),
        )
        for name, command, cwd, url in services:
            if stop_requested:
                return 0
            print(f"Starting {name}…", flush=True)
            child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                     start_new_session=True)
            children.append((name, child))
            wait_ready(url, children, lambda: stop_requested)
        if not stop_requested:
            print("Ready: http://127.0.0.1:5173/ — Scout + Decision Lab. Ctrl-C stops both services.", flush=True)
        while not stop_requested:
            check_children(children)
            time.sleep(0.2)
        return 0
    except (StartupError, OSError, subprocess.SubprocessError) as exc:
        print(f"Local startup failed: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        for sig in previous:
            signal.signal(sig, signal.SIG_IGN)
        try:
            if children:
                try:
                    print("Stopping local services…", flush=True)
                except OSError:
                    pass  # A closed output pipe must not prevent process cleanup.
                stop_children(children)
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)


if __name__ == "__main__":
    raise SystemExit(main())
