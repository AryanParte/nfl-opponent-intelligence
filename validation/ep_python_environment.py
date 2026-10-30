"""Record/check the local optional Python EP runtime; no installation or network."""

import argparse
from hashlib import sha256
from importlib import metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import zipfile

from validation import ep_python_setup as setup


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "validation/ep_python_candidate.py"


def digest_file(path):
    digest = sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def installed_packages():
    """Hash installed files, not just declared versions; exclude generated pyc/RECORD."""
    result = {}
    for name, version in (setup.VERSIONS | {"xgboost": "3.4.2", "pip": "25.0"}).items():
        distribution = metadata.distribution(name)
        setup.require(distribution.version == version, f"installed version differs: {name}")
        hashes = {}
        for relative in distribution.files or []:
            if relative.suffix == ".pyc" or relative.name == "RECORD":
                continue
            installed = Path(distribution.locate_file(relative))
            setup.require(installed.is_file() and not installed.is_symlink(), "missing/linked installed file")
            hashes[str(relative)] = digest_file(installed)
        setup.require(bool(hashes), "empty package inventory")
        result[name] = {"version": version, "files": len(hashes),
                        "installed_files_sha256": sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()}
    return result


def inspect_runtime():
    import xgboost
    from xgboost.libpath import find_lib_path

    setup.require(platform.python_version() == "3.13.2" and platform.system() == "Darwin"
                  and platform.machine() == "arm64", "requires Python 3.13.2/macOS ARM64")
    library = Path(find_lib_path()[0])
    linkage = subprocess.run(["/Library/Developer/CommandLineTools/usr/bin/otool", "-L", str(library)],
                             check=True, capture_output=True, text=True, timeout=15)
    return {"python_version": platform.python_version(), "os_version": platform.mac_ver()[0],
            "platform": "macos-arm64", "python_executable_sha256": digest_file(Path(sys.executable).resolve()),
            "python_framework_sha256": digest_file(Path(sys.base_prefix, "Python").resolve()),
            "packages": installed_packages(), "xgboost_build_info": xgboost.build_info(),
            "native_library_sha256": digest_file(library),
            "native_linkage": linkage.stdout.splitlines()[1:], "runner_sha256": digest_file(RUNNER),
            "inventory_script_sha256": digest_file(Path(__file__))}


def record_environment(build):
    lock = setup.load_lock()
    for record in lock["wheels"]:
        setup.verify_wheel(ROOT / setup.CACHE / record["filename"], record)
    wheels = list((build / "wheels").glob("xgboost-3.4.2-*.whl"))
    setup.require(len(wheels) == 1, "expected exactly one built XGBoost wheel")
    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        raw_library = archive.read("xgboost/lib/libxgboost.dylib")
        notices = {n: sha256(archive.read(n)).hexdigest() for n in archive.namelist()
                   if "/licenses/" in n and not n.endswith("/")}
    runtime = inspect_runtime()
    setup.require(sha256(raw_library).hexdigest() == runtime["native_library_sha256"], "installed library differs")
    setup.require(bool(notices), "built wheel missing notices")
    cache = build / "xgboost/python-package/build/py3-none-macosx_15_0_arm64/CMakeCache.txt"
    cache_text = cache.read_text()
    for expected in ("USE_OPENMP:BOOL=OFF", "USE_CUDA:BOOL=OFF", "USE_NCCL:BOOL=OFF",
                     "CMAKE_OSX_SYSROOT:PATH=/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk",
                     "CMAKE_OSX_DEPLOYMENT_TARGET:STRING=15.0"):
        setup.require(expected in cache_text, f"build configuration differs: {expected}")
    return {"schema_version": 1, **runtime,
            "source_archive_sha256": lock["source_sha256"], "source_commit": lock["source_commit"],
            "dependency_lock_sha256": digest_file(setup.LOCK),
            "build": {"network": "denied by sandbox-exec", "jobs": 2, "openmp": False,
                      "cuda": False, "nccl": False, "deployment_target": "15.0",
                      "sdk": "MacOSX26.5.sdk", "cmake_cache_sha256": digest_file(cache),
                      "log_sha256": digest_file(build / "build.log"),
                      "compiler": subprocess.run(["/Library/Developer/CommandLineTools/usr/bin/clang++", "--version"],
                                                 check=True, capture_output=True, text=True, timeout=15).stdout,
                      "compiler_sha256": digest_file("/Library/Developer/CommandLineTools/usr/bin/clang++"),
                      "linker_sha256": digest_file("/Library/Developer/CommandLineTools/usr/bin/ld"),
                      "sdk_settings_sha256": digest_file("/Library/Developer/CommandLineTools/SDKs/MacOSX26.5.sdk/SDKSettings.json")},
            "built_wheel": {"filename": wheel.name, "sha256": digest_file(wheel),
                            "size_bytes": wheel.stat().st_size, "notice_hashes": notices}}


def verify_environment(path):
    environment = json.loads(Path(path).read_bytes())
    lock = setup.load_lock()
    setup.require(type(environment["schema_version"]) is int and environment["schema_version"] == 1,
                  "environment schema drift")
    setup.require(environment["dependency_lock_sha256"] == digest_file(setup.LOCK), "dependency lock drift")
    setup.require(environment["source_archive_sha256"] == lock["source_sha256"] and
                  environment["source_commit"] == lock["source_commit"], "source identity drift")
    for key, value in inspect_runtime().items():
        setup.require(environment[key] == value, f"runtime drift: {key}")
    return environment


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    environment = record_environment(args.build)
    with args.output.open("xb") as destination:
        destination.write((json.dumps(environment, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
    print(json.dumps({"environment_sha256": digest_file(args.output), "output": str(args.output)}))


if __name__ == "__main__":
    main()
