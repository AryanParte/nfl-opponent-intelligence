"""Inspect the pinned EP object in an already-pulled, network-disabled R image.

No daemon startup, image pull, package installation, persisted raw export,
prediction or capture comparison. Docker/R are optional experiment tools only.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from uuid import uuid4

from opponent_intelligence.snapshots import SnapshotError
from validation.ep_acquire import verify


IMAGE = "rocker/r-ver@sha256:fb487cf8a2029fc1dbc17621cf41ac913d49ac74a1ff9e27bf9bbc982e55d08d"
RUNNER = Path(__file__).with_name("ep_inspect.R")
PLATFORM = "linux/arm64"


def inspect(directory):
    directory = Path(directory)
    manifest = verify(directory)
    directory = directory.resolve(strict=True)
    runner = RUNNER.resolve(strict=True)
    runner_hash = sha256(runner.read_bytes()).hexdigest()
    container_name = f"nfl-ep-probe-{uuid4().hex}"
    # Docker's --mount mini-language must not interpret path text as extra options.
    if any("," in str(path) or "\n" in str(path) for path in (directory, runner)):
        raise SnapshotError("unsupported comma/newline in experiment mount path")
    container_sha = manifest["files"]["ep_model.rda"]["sha256"]
    command = [
        "docker", "run", "--name", container_name, "--rm", "--pull", "never", "--platform", PLATFORM,
        "--network", "none", "--read-only", "--user", "65534:65534",
        "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,size=128m",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--cpus", "1", "--memory", "512m", "--pids-limit", "64",
        "--env", f"EP_CONTAINER_SHA256={container_sha}",
        "--mount", f"type=bind,src={directory},dst=/artifact,readonly",
        "--mount", f"type=bind,src={runner},dst=/probe.R,readonly",
        IMAGE, "Rscript", "--vanilla", "/probe.R",
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=45)
    except subprocess.SubprocessError as exc:
        # Killing a Docker client on timeout need not stop its container. Remove
        # only this uniquely named, disposable probe (no writable host mounts).
        cleanup = subprocess.run(["docker", "rm", "--force", container_name], check=False,
                                 capture_output=True, text=True, timeout=15)
        if cleanup.returncode != 0:
            raise SnapshotError(f"R probe failed; unable to confirm cleanup of {container_name}") from exc
        raise
    try:
        probe = json.loads(result.stdout)
        keys = {"status", "r_version", "platform", "container_sha256", "object_name", "object_type",
                "raw_bytes", "raw_sha256", "prefix_hex", "installed_package_equality_verified",
                "model_executed"}
        valid = (isinstance(probe, dict) and set(probe) == keys
                 and probe["status"] == "raw_object_inspected" and probe["r_version"] == "4.6.1"
                 and probe["platform"] == "aarch64-unknown-linux-gnu"
                 and probe["container_sha256"] == container_sha
                 and probe["object_name"] == "ep_model" and probe["object_type"] == "raw"
                 and type(probe["raw_bytes"]) is int and 0 < probe["raw_bytes"] <= 16 * 1024 * 1024
                 and isinstance(probe["raw_sha256"], str)
                 and re.fullmatch(r"[0-9a-f]{64}", probe["raw_sha256"]) is not None
                 and probe["raw_sha256"] != "0" * 64
                 and isinstance(probe["prefix_hex"], str)
                 and re.fullmatch(r"[0-9a-f]{32}", probe["prefix_hex"]) is not None
                 and probe["installed_package_equality_verified"] is False
                 and probe["model_executed"] is False)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise SnapshotError("invalid R inspection receipt")
    # Detect input/runner edits during the probe; retain immutable identities.
    if verify(directory) != manifest or sha256(runner.read_bytes()).hexdigest() != runner_hash:
        raise SnapshotError("acquisition manifest or runner changed during inspection")
    return {"schema_version": 1, "image": IMAGE, "platform": PLATFORM,
            "network": "none", "root_filesystem": "read_only", "cpu_limit": 1,
            "runner_sha256": runner_hash,
            "probe_driver_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "acquisition_manifest_sha256": sha256((directory / "manifest.json").read_bytes()).hexdigest(),
            "inspection": probe, "prediction_capture_available": False,
            "predictive_validation": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = inspect(args.snapshot)
    except (OSError, SnapshotError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"EP object inspection failed: {exc}\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
