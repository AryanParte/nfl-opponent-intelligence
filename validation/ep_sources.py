"""Explicit, pinned source setup for the optional R experiment (never serving)."""

import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile

from opponent_intelligence.snapshots import SnapshotError, _download, _read_json
from validation.ep_probe import IMAGE, PLATFORM
from validation.ep_reference import SOURCE_COMMITS


LOCK = Path(__file__).with_name("ep_runtime.lock.json")
INSTALLER = Path(__file__).with_name("ep_install.R")
CACHE = Path(".cache/ep-reference/runtime-sources")


def load_lock():
    lock = _read_json(LOCK)
    try:
        _validate_lock(lock)
    except (KeyError, TypeError, ValueError) as exc:
        raise SnapshotError(f"invalid R source lock: {exc}") from exc
    return lock


def _validate_lock(lock):
    if (type(lock.get("schema_version")) is not int or lock.get("schema_version") != 1
            or lock.get("base_image") != IMAGE
            or lock.get("platform") != PLATFORM or lock.get("r_version") != "4.6.1"):
        raise SnapshotError("unexpected R runtime lock identity")
    packages = lock["packages"]
    if not isinstance(packages, list) or not 1 <= len(packages) <= 64:
        raise SnapshotError("invalid source package count")
    names = [p["package"] for p in packages]
    if (names != lock["install_order"] or len(set(names)) != len(names)
            or len({p["filename"] for p in packages}) != len(names)):
        raise SnapshotError("duplicate/misordered runtime packages")
    versions = {p["package"]: p["version"] for p in packages}
    for name, version in {"nflfastR": "6.0.0", "fastrmodels": "2.1.0", "xgboost": "3.4.2.1"}.items():
        if versions.get(name) != version:
            raise SnapshotError("required reference package version changed/missing")
    for record in packages:
        if (not re.fullmatch(r"[A-Za-z0-9_.-]+\.tar\.gz", record["filename"])
                or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])
                or type(record["size_bytes"]) is not int
                or not 0 < record["size_bytes"] <= 64 * 1024 * 1024
                or type(record["uncompressed_bytes"]) is not int
                or not 0 < record["uncompressed_bytes"] <= 256 * 1024 * 1024
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", record["archive_root"])
                or not isinstance(record["terms_files"], dict)
                or not isinstance(record["declared_license"], str)
                or not record["declared_license"] or not record["terms_files"]):
            raise SnapshotError("invalid source lock record")
        for name, digest in record["terms_files"].items():
            if (not name.startswith(record["archive_root"] + "/") or ".." in name.split("/")
                    or not re.fullmatch(r"[0-9a-f]{64}", digest)):
                raise SnapshotError("invalid source notice lock")
        if record["acquisition"] == "https":
            expected = ("https://github.com/dmlc/xgboost/releases/download/v3.4.2/xgboost-src-3.4.2.tar.gz"
                        if record["package"] == "xgboost" else
                        f"https://packagemanager.posit.co/cran/2026-10-24/src/contrib/{record['filename']}")
            if record["url"] != expected:
                raise SnapshotError("unreviewed source URL")
        elif record["acquisition"] == "git_archive":
            if (record["package"] not in SOURCE_COMMITS
                    or record["source_repository"] != f"https://github.com/nflverse/{record['package']}.git"
                    or record["tag"] != "v" + record["version"]):
                raise SnapshotError("unreviewed Git source")
        else:
            raise SnapshotError("unsupported source acquisition")
        if record["package"] in SOURCE_COMMITS:
            if record.get("commit") != SOURCE_COMMITS[record["package"]]:
                raise SnapshotError("nflverse source commit changed")


def verify_source(path, record):
    """Check locked compressed bytes, safe members and retained notice identities."""
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size != record["size_bytes"]:
        raise SnapshotError(f"source file/size mismatch: {path.name}")
    if sha256(path.read_bytes()).hexdigest() != record["sha256"]:
        raise SnapshotError(f"source digest mismatch: {path.name}")
    seen, size, terms = set(), 0, {}
    root = record["archive_root"]
    with tarfile.open(path) as archive:
        for member in archive:
            name = PurePosixPath(member.name)
            if (name in seen or name.is_absolute() or ".." in name.parts
                    or not name.parts or name.parts[0] != root
                    or not (member.isfile() or member.isdir())):
                raise SnapshotError("unsafe/duplicate source archive member")
            seen.add(name)
            size += member.size
            if size > 256 * 1024 * 1024 or len(seen) > 20000:
                raise SnapshotError("source archive expansion exceeds experiment limit")
            if member.name in record["terms_files"]:
                if not member.isfile() or member.size > 1024 * 1024:
                    raise SnapshotError("invalid source notice")
                terms[member.name] = sha256(archive.extractfile(member).read()).hexdigest()
    if terms != record["terms_files"] or size != record["uncompressed_bytes"]:
        raise SnapshotError("source contents/notice identity mismatch")


def acquire_source(record, cache=CACHE, git="git"):
    """Fixed HTTPS or exact Git release; stage before publication, never repair."""
    cache = Path(cache)
    if any(p.is_symlink() for p in (cache, *cache.parents)):
        raise SnapshotError("source cache must not traverse symlinks")
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / record["filename"]
    if destination.exists() or destination.is_symlink():
        verify_source(destination, record)
        return destination
    with tempfile.TemporaryDirectory(prefix=".ep-source-", dir=cache) as temporary:
        stage = Path(temporary) / record["filename"]
        if record["acquisition"] == "https":
            _download(record["url"], stage, record["size_bytes"], timeout=30, attempts=3)
        elif record["acquisition"] == "git_archive":
            checkout = Path(temporary) / "source"
            subprocess.run([git, "-c", "http.lowSpeedLimit=1024", "-c", "http.lowSpeedTime=30",
                            "clone", "--depth", "1", "--branch", record["tag"],
                            record["source_repository"], str(checkout)], check=True, timeout=180)
            commit = subprocess.check_output([git, "-C", str(checkout), "rev-parse", "HEAD"],
                                             text=True, timeout=15).strip()
            if commit != record["commit"]:
                raise SnapshotError("upstream release tag no longer matches pinned commit")
            subprocess.run([git, "-C", str(checkout), "archive", "--format=tar.gz",
                            f"--prefix={record['archive_root']}/", f"--output={stage.resolve()}",
                            commit], check=True, timeout=60)
        else:
            raise SnapshotError("unsupported source acquisition")
        verify_source(stage, record)
        # Hard-link publication is atomic and cannot overwrite another writer.
        try:
            destination.hardlink_to(stage)
        except FileExistsError:
            verify_source(destination, record)
    return destination


def prepare(cache=CACHE):
    """Build context is a verified copy; do not send partial/unrelated cache files."""
    lock = load_lock()
    cache = Path(cache)
    if any(p.is_symlink() for p in (cache, *cache.parents)):
        raise SnapshotError("source cache must not traverse symlinks")
    identity = sha256(LOCK.read_bytes() + INSTALLER.read_bytes()).hexdigest()
    context = cache.parent / f"context-{identity}"
    guard = cache.parent / ".ep-context.lock"
    try:
        with guard.open("x"):
            pass
    except FileExistsError as exc:
        raise SnapshotError("context setup lock exists; inspect before retrying") from exc
    try:
        return _prepare_context(lock, cache, context)
    finally:
        guard.unlink()


def _prepare_context(lock, cache, context):
    script = INSTALLER
    expected = {p["filename"] for p in lock["packages"]} | {"sources.sha256", "ep_runtime.lock.json", "ep_install.R"}
    with tempfile.TemporaryDirectory(prefix=".ep-context-", dir=cache.parent) as temporary:
        stage = Path(temporary) / "context"
        stage.mkdir()
        for record in lock["packages"]:
            verify_source(cache / record["filename"], record)
            shutil.copyfile(cache / record["filename"], stage / record["filename"])
            verify_source(stage / record["filename"], record)
        shutil.copyfile(LOCK, stage / LOCK.name)
        shutil.copyfile(script, stage / script.name)
        lines = [f"{sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in sorted(stage.iterdir())]
        (stage / "sources.sha256").write_text("".join(lines), encoding="utf-8")
        if context.exists():
            if context.is_symlink() or not context.is_dir() or {p.name for p in context.iterdir()} != expected:
                raise SnapshotError("existing context differs; preserve and inspect it")
            for p in stage.iterdir():
                target = context / p.name
                if target.is_symlink() or not target.is_file() or p.read_bytes() != target.read_bytes():
                    raise SnapshotError("existing context bytes differ; preserve and inspect it")
        else:
            stage.rename(context)
    return context


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("acquire", "verify", "prepare"))
    parser.add_argument("--git", default="git", help="Git executable; never changes global Git settings")
    args = parser.parse_args()
    try:
        lock = load_lock()
        for record in lock["packages"]:
            if args.action == "acquire":
                acquire_source(record, git=args.git)
            else:
                verify_source(CACHE / record["filename"], record)
        context = str(prepare()) if args.action == "prepare" else None
    except (OSError, ValueError, tarfile.TarError, EOFError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"EP runtime source setup failed: {exc}\n")
    print(json.dumps({"status": "runtime_sources_verified", "packages": len(lock["packages"]),
                      "lock_sha256": sha256(LOCK.read_bytes()).hexdigest(), "context": context,
                      "model_executed": False}, indent=2))


if __name__ == "__main__":
    main()
