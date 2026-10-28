"""Explicit offline R reference capture; Docker is optional and never auto-started.

No production imports of this runner, downloads, training or Python inference.
All model execution uses the previously inspected, digest-addressed local image.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from uuid import uuid4

from validation import ep_acquire, ep_reference


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "validation/ep_r_capture.R"
ENVIRONMENT = ROOT / "docs/evidence/ep-full-runtime.json"
AUDIT = ROOT / "validation/ep_full_runtime_check.R"
RAW_SHA256 = "14a4b7e0c115d3f46fc9f341a024874b0dbcf44b30bb1f426d4f59b6f175335a"
RAW_BYTES = 9737490
LIMIT = 1024 * 1024
OUTPUTS = {"ep_model.ubj": RAW_BYTES, "capture.json": LIMIT,
           "observation.json": LIMIT, "input.json": LIMIT, "runtime-check.json": LIMIT,
           "runtime.log": LIMIT, "capture.log": LIMIT, "LICENSE.md": 16384,
           "DESCRIPTION": 16384}


def require(condition, message):
    if not condition:
        raise ep_reference.ProtocolError(message)


def read(path, limit=LIMIT):
    path = Path(path)
    require(not any(p.is_symlink() for p in (path, *path.parents)), "symlink input/output")
    require(path.is_file(), f"not a regular file: {path.name}")
    with path.open("rb") as source:
        raw = source.read(limit + 1)
    require(len(raw) <= limit, f"oversized file: {path.name}")
    return raw


def digest(raw):
    return sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def inputs(artifact):
    """Verify setup; send only accepted state inputs, never expected vectors, to R."""
    acquisition = ep_acquire.verify(artifact)
    environment_bytes = read(ENVIRONMENT)
    environment = json.loads(environment_bytes)
    require(environment["runtime"]["raw_sha256"] == RAW_SHA256, "raw payload pin differs")
    require(environment["runtime"]["raw_bytes"] == RAW_BYTES, "raw payload size differs")
    for relative, expected in environment["inputs"].items():
        require(Path(relative).parts[0] == "validation" and ".." not in Path(relative).parts,
                "invalid environment input path")
        require(digest(read(ROOT / relative)) == expected, f"runtime input drift: {relative}")
    manifest_hash = digest(read(artifact / "manifest.json"))
    require(manifest_hash == environment["acquisition_manifest_sha256"], "acquisition identity drift")
    fixture, fixture_hash = ep_reference.load_fixture()
    payload = {
        "states": [{"id": c["id"], "state": fixture["base_state"] | c["overrides"]}
                   for c in fixture["accepted"]],
        "fixture_sha256": fixture_hash, "source_commits": ep_reference.SOURCE_COMMITS,
        "artifact_manifest_sha256": manifest_hash, "model_sha256": RAW_SHA256,
        "container_sha256": acquisition["files"]["ep_model.rda"]["sha256"],
        "environment_sha256": digest(environment_bytes),
    }
    identity = {"input_sha256": digest(encode(payload)),
                "runner_sha256": digest(read(RUNNER)),
                "driver_sha256": digest(read(Path(__file__))),
                "protocol_sha256": digest(read(Path(ep_reference.__file__))),
                "environment_sha256": digest(environment_bytes),
                "image_id": environment["local_image_id"]}
    return payload, identity, environment


def docker_command(image, name, mounts):
    command = ["docker", "run", "--rm", "--pull", "never", "--name", name,
               "--network", "none", "--read-only", "--user", "65534:65534",
               "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
               "--cpus", "1", "--memory", "768m", "--pids-limit", "64",
               "--tmpfs", "/tmp:rw,noexec,nosuid,size=96m"]
    for source, target, writable in mounts:
        require("," not in str(source), "Docker mount path contains a comma")
        command += ["--mount", f"type=bind,src={source},dst={target}" +
                    ("" if writable else ",readonly")]
    return command + [image]


def run_container(command, name, stdout, stderr):
    """Bound the offline process; a timeout removes only this uniquely named run."""
    try:
        with stdout.open("xb") as out, stderr.open("xb") as err:
            subprocess.run(command, check=True, timeout=60, stdout=out, stderr=err)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        subprocess.run(["docker", "rm", "-f", name], check=False, timeout=15,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        raise
    read(stdout)
    read(stderr)


def execute(staged, artifact, payload, identity, environment):
    image = identity["image_id"]
    require(re.fullmatch(r"sha256:[0-9a-f]{64}", image) is not None,
            "image is not digest addressed")
    inspected = subprocess.run(["docker", "image", "inspect", image, "--format",
                                "{{.Id}} {{.Os}}/{{.Architecture}}"],
                               check=True, timeout=15, capture_output=True, text=True)
    require(inspected.stdout.strip() == f"{image} {environment['platform']}",
            "local image identity/platform differs")
    name = "ep-audit-" + uuid4().hex
    command = docker_command(image, name, [(artifact, "/artifact", False), (AUDIT, "/probe.R", False)])
    # Docker options must precede the image name.
    command[-1:-1] = ["-e", f"EP_CONTAINER_SHA256={payload['container_sha256']}",
                      "-e", f"EP_RAW_SHA256={RAW_SHA256}"]
    run_container(command + ["Rscript", "--vanilla", "/probe.R"], name,
                  staged / "runtime-check.json", staged / "runtime.log")
    require(json.loads(read(staged / "runtime-check.json")) == environment["runtime"],
            "installed runtime differs from the reviewed manifest")
    name = "ep-capture-" + uuid4().hex
    command = docker_command(image, name, [(artifact, "/artifact", False),
        (RUNNER, "/runner.R", False), (staged / "input.json", "/input.json", False),
        (staged, "/output", True)])
    # Only generated output is writable. Do not mount the repository or Docker socket.
    run_container(command + ["Rscript", "--vanilla", "/runner.R"], name,
                  staged / "capture.stdout", staged / "capture.log")
    require(read(staged / "capture.stdout") == b"", "unexpected capture stdout")
    (staged / "capture.stdout").unlink()


def validate_outputs(directory, payload, identity, environment):
    raw = read(directory / "ep_model.ubj", RAW_BYTES)
    require(len(raw) == RAW_BYTES and digest(raw) == RAW_SHA256, "raw export identity differs")
    require(read(directory / "input.json") == encode(payload), "state input changed")
    require(json.loads(read(directory / "runtime-check.json")) == environment["runtime"],
            "runtime receipt changed")
    capture = json.loads(read(directory / "capture.json"))
    result = ep_reference.validate_reference(capture)
    require(capture["probability_origin"] == "model_capture", "not an actual model capture")
    require(capture["model_sha256"] == RAW_SHA256 and
            capture["artifact_manifest_sha256"] == payload["artifact_manifest_sha256"],
            "capture artifact identity differs")
    require(capture["runtime"] == {
        "language": "R", "version": environment["runtime"]["r_version"],
        "xgboost_version": "3.4.2.1", "platform": environment["runtime"]["platform"],
        "environment_sha256": identity["environment_sha256"],
        "runner_sha256": identity["runner_sha256"]}, "capture runtime identity differs")
    observation = json.loads(read(directory / "observation.json"))
    require(observation == {"status": "upstream_reference_captured", "traced_predictions": 26,
        "verified_raw_loads": 26, "untraced_batch_identical": True,
        "input_sha256": identity["input_sha256"], "model_sha256": RAW_SHA256,
        "model_bytes": RAW_BYTES, "installed_package_equality_verified": True,
        "xgboost_config": environment["runtime"]["xgboost_config"]}, "incomplete model observation")
    return result


def verify(directory, artifact):
    """Offline integrity replay, not a rerun of model inference or remote attestation."""
    payload, identity, environment = inputs(artifact)
    require(not directory.is_symlink() and directory.is_dir(), "invalid capture directory")
    require({p.name for p in directory.iterdir()} == set(OUTPUTS) | {"manifest.json"},
            "capture file inventory differs")
    manifest = json.loads(read(directory / "manifest.json"))
    require(set(manifest) == {"schema_version", "identity", "captured_at_utc", "files", "validation"},
            "manifest keys differ")
    require(type(manifest["schema_version"]) is int and manifest["schema_version"] == 1,
            "manifest version differs")
    require(manifest["identity"] == identity, "capture source/runtime drift; preserve old evidence")
    try:
        offset = datetime.fromisoformat(manifest["captured_at_utc"]).utcoffset()
        require(offset is not None and offset.total_seconds() == 0, "capture time must be UTC")
    except (TypeError, ValueError) as exc:
        raise ep_reference.ProtocolError("invalid UTC capture time") from exc
    require(set(manifest["files"]) == set(OUTPUTS), "manifest file inventory differs")
    for name, limit in OUTPUTS.items():
        raw = read(directory / name, limit)
        require(manifest["files"][name] == {"sha256": digest(raw), "size_bytes": len(raw)},
                f"capture file changed: {name}")
    for name in ("LICENSE.md", "DESCRIPTION"):
        require(read(directory / name) == read(artifact / name), "artifact notice changed")
    result = validate_outputs(directory, payload, identity, environment)
    require(manifest["validation"] == result, "validation receipt differs")
    return manifest


def capture(artifact, cache):
    artifact, cache = Path(artifact).absolute(), Path(cache).absolute()
    payload, identity, environment = inputs(artifact)
    require(not any(p.is_symlink() for p in (cache, *cache.parents)), "symlink cache path")
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / ("r-" + digest(encode(identity)))
    lock = cache / ".capture.lock"
    with lock.open("x"):
        pass
    try:
        if destination.exists() or destination.is_symlink():
            verify(destination, artifact)
            return destination
        staged = Path(tempfile.mkdtemp(prefix=".pending-", dir=cache))
        # Disposable staging is shared with the unprivileged container only.
        staged.chmod(0o777)
        (staged / "input.json").write_bytes(encode(payload))
        for name in ("LICENSE.md", "DESCRIPTION"):
            (staged / name).write_bytes(read(artifact / name))
        try:
            execute(staged, artifact, payload, identity, environment)
            require(inputs(artifact) == (payload, identity, environment), "inputs changed during execution")
            result = validate_outputs(staged, payload, identity, environment)
            records = {name: {"sha256": digest(raw), "size_bytes": len(raw)}
                       for name, limit in OUTPUTS.items() for raw in [read(staged / name, limit)]}
            manifest = {"schema_version": 1, "identity": identity,
                        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                        "files": records, "validation": result}
            (staged / "manifest.json").write_bytes(encode(manifest))
            verify(staged, artifact)
            # Exclusive lock + no existing destination. Never refresh/repair captures.
            require(not destination.exists() and not destination.is_symlink(),
                    "capture destination appeared during execution")
            staged.chmod(0o755)
            os.rename(staged, destination)
        except (Exception, KeyboardInterrupt) as exc:
            raise ep_reference.ProtocolError(f"capture failed; staging/logs retained at {staged}: {exc}") from exc
        return destination
    finally:
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--capture", action="store_true")
    action.add_argument("--verify", type=Path)
    parser.add_argument("--artifact", type=Path, default=ep_acquire.DEFAULT_CACHE / ep_acquire.SNAPSHOT_NAME)
    parser.add_argument("--output-cache", type=Path, default=Path(".cache/ep-reference/captures"))
    args = parser.parse_args()
    try:
        directory = capture(args.artifact, args.output_cache) if args.capture else args.verify
        manifest = verify(directory, args.artifact)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"EP R capture failed: {exc}\n")
    print(json.dumps({"status": "local_reference_capture_verified", "directory": str(directory),
                      "manifest_sha256": digest(read(directory / "manifest.json")),
                      "validation": manifest["validation"]}, indent=2))


if __name__ == "__main__":
    main()
