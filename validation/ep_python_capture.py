"""Offline experiment driver; the candidate never reads reference predictions."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

from validation import ep_acquire, ep_reference, ep_r_capture
from validation import ep_python_candidate as candidate, ep_python_environment as runtime


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / ".cache/ep-reference/captures/r-d01f69c0298f72cae1e7699b325fe91c3a959c1bcc07ff3d9d147cff67b032b6"
ENVIRONMENT = ROOT / "docs/evidence/ep-python-environment.json"
ARTIFACT = ROOT / ep_acquire.DEFAULT_CACHE / ep_acquire.SNAPSHOT_NAME
OUTPUTS = ("capture.json", "environment.json", "stdout.log", "stderr.log")
EXECUTION = {"network": "denied", "writes": "capture directory only",
             "cpu_seconds_limit": 45, "wall_seconds_limit": 60, "output_bytes_limit": 1048576}


def command(reference, environment, directory):
    profile = ('(version 1)(allow default)(deny network*)(deny file-write*)'
               f'(allow file-write* (subpath {json.dumps(str(directory))}) (literal "/dev/null"))')
    return ["/usr/bin/sandbox-exec", "-p", profile, sys.executable, "-B", str(runtime.RUNNER),
            "--model", str(reference / "ep_model.ubj"), "--input", str(reference / "input.json"),
            "--environment", str(environment), "--output", str(directory / "capture.json")]


def limits():
    resource.setrlimit(resource.RLIMIT_CPU, (45, 45))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))


def execute(argv, directory):
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
           "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1"}
    # No custom import/library injection into the isolated candidate process.
    for key in ("PYTHONPATH", "PYTHONHOME", "DYLD_LIBRARY_PATH", "DYLD_INSERT_LIBRARIES"):
        env.pop(key, None)
    with (directory / "stdout.log").open("xb") as stdout, (directory / "stderr.log").open("xb") as stderr:
        subprocess.run(argv, check=True, timeout=60, env=env, stdout=stdout, stderr=stderr,
                       preexec_fn=limits)


def verify(directory, reference=REFERENCE):
    """Integrity + arithmetic replay; no native execution or predictive claim."""
    ep_r_capture.verify(reference, ARTIFACT)
    ep_reference._require({p.name for p in directory.iterdir()} == set(OUTPUTS) | {"manifest.json"},
                          "Python capture inventory differs")
    manifest = json.loads(ep_r_capture.read(directory / "manifest.json"))
    ep_reference._require(set(manifest) == {"schema_version", "captured_at_utc", "driver_sha256",
                          "reference_manifest_sha256", "execution", "files", "comparison"}
                          and set(manifest["files"]) == set(OUTPUTS) and manifest["execution"] == EXECUTION,
                          "Python manifest contract differs")
    ep_reference._require(type(manifest["schema_version"]) is int and manifest["schema_version"] == 1,
                          "Python manifest version differs")
    offset = datetime.fromisoformat(manifest["captured_at_utc"]).utcoffset()
    ep_reference._require(offset is not None and offset.total_seconds() == 0, "capture time must be UTC")
    for name in OUTPUTS:
        raw = ep_r_capture.read(directory / name)
        ep_reference._require(manifest["files"][name] == {"sha256": ep_r_capture.digest(raw), "size_bytes": len(raw)},
                              f"Python capture bytes differ: {name}")
    ep_reference._require(ep_r_capture.read(directory / "stdout.log") == b"", "unexpected candidate stdout")
    environment = json.loads(ep_r_capture.read(directory / "environment.json"))
    observed = json.loads(ep_r_capture.read(directory / "capture.json"))
    ep_reference._require(observed["runtime"]["version"] == environment["python_version"] == "3.13.2"
                          and observed["runtime"]["xgboost_version"] == environment["packages"]["xgboost"]["version"] == "3.4.2"
                          and observed["runtime"]["platform"] == environment["platform"] == "macos-arm64"
                          and environment["dependency_lock_sha256"] == runtime.digest_file(runtime.setup.LOCK)
                          and environment["inventory_script_sha256"] == runtime.digest_file(Path(runtime.__file__)),
                          "recorded runtime identity drift")
    ep_reference._require(observed["runtime"]["environment_sha256"] == runtime.digest_file(directory / "environment.json")
                          and observed["runtime"]["runner_sha256"] == runtime.digest_file(runtime.RUNNER)
                          and environment["runner_sha256"] == runtime.digest_file(runtime.RUNNER), "candidate identity drift")
    ep_reference._require(manifest["driver_sha256"] == runtime.digest_file(Path(__file__))
                          and manifest["reference_manifest_sha256"] == runtime.digest_file(reference / "manifest.json"),
                          "driver/reference drift")
    result = ep_reference.compare_captures(json.loads(ep_r_capture.read(reference / "capture.json")), observed)
    ep_reference._require(result == manifest["comparison"], "comparison receipt differs")
    return manifest


def capture(reference=REFERENCE, environment=ENVIRONMENT, cache=ROOT / ".cache/ep-python/captures"):
    ep_r_capture.verify(reference, ARTIFACT)
    runtime.verify_environment(environment)
    ep_reference._require(runtime.digest_file(reference / "input.json") == candidate.INPUT_SHA256,
                          "fixed state input differs")
    ep_reference._require(not any(p.is_symlink() for p in (cache, *cache.parents)), "symlink capture cache")
    cache.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="python-", dir=cache))
    # Each invocation is an independent replay; exclusive creation never repairs
    # or overwrites earlier evidence. Failed output/logs stay available to inspect.
    (directory / "environment.json").write_bytes(ep_r_capture.read(environment))
    try:
        execute(command(reference, directory / "environment.json", directory), directory)
        runtime.verify_environment(environment)
        observed = json.loads(ep_r_capture.read(directory / "capture.json"))
        comparison = ep_reference.compare_captures(json.loads(ep_r_capture.read(reference / "capture.json")), observed)
        manifest = {"schema_version": 1, "captured_at_utc": datetime.now(timezone.utc).isoformat(),
                    "driver_sha256": runtime.digest_file(Path(__file__)),
                    "reference_manifest_sha256": runtime.digest_file(reference / "manifest.json"),
                    "execution": EXECUTION,
                    "files": {name: {"sha256": ep_r_capture.digest(raw), "size_bytes": len(raw)}
                              for name in OUTPUTS for raw in [ep_r_capture.read(directory / name)]},
                    "comparison": comparison}
        (directory / "manifest.json").write_bytes(ep_r_capture.encode(manifest))
        verify(directory, reference)
    except (Exception, KeyboardInterrupt) as exc:
        raise ValueError(f"Python capture failed; evidence retained at {directory}: {exc}") from exc
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--capture", action="store_true")
    action.add_argument("--verify", type=Path)
    parser.add_argument("--reference", type=Path, default=REFERENCE)
    parser.add_argument("--environment", type=Path, default=ENVIRONMENT)
    args = parser.parse_args()
    directory = capture(args.reference, args.environment) if args.capture else args.verify
    manifest = verify(directory, args.reference)
    print(json.dumps({"directory": str(directory), "comparison": manifest["comparison"]}, indent=2))


if __name__ == "__main__":
    main()
