"""Explicit native dependency cache/context setup for the isolated R experiment.

Never starts Docker, installs host packages or resolves floating versions.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tarfile
import tempfile

from opponent_intelligence.snapshots import SnapshotError, _download, _read_json
from validation import ep_sources


LOCK = Path(__file__).with_name("ep_native.lock.json")
INSTALLER = LOCK.with_name("ep_native_install.R")
RECIPE = LOCK.with_name("ep_native.Dockerfile")
CACHE = Path(".cache/ep-reference/native-20261026/archives")
SNAPSHOT = "20261026T000000Z"
URL_PREFIX = f"https://snapshot.ubuntu.com/ubuntu/{SNAPSHOT}/pool/main/"
VERSIONS = {
    "icu-devtools": "74.2-1ubuntu3.1", "libicu-dev": "74.2-1ubuntu3.1",
    "libcurl4-openssl-dev": "8.5.0-2ubuntu10.16", "libpkgconf3": "1.8.1-2build1",
    "pkgconf-bin": "1.8.1-2build1", "pkgconf": "1.8.1-2build1", "pkg-config": "1.8.1-2build1",
}


def load_lock():
    lock = _read_json(LOCK)
    try:
        packages = lock["packages"]
        if (type(lock["schema_version"]) is not int or lock["schema_version"] != 1
                or lock["snapshot"] != SNAPSHOT or lock["base_image"] != ep_sources.IMAGE
                or lock["platform"] != ep_sources.PLATFORM or not isinstance(packages, list)
                or len(packages) != len(VERSIONS)
                or {p["package"]: p["version"] for p in packages} != VERSIONS):
            raise SnapshotError("unexpected native lock identity")
        if not re.fullmatch(r"[0-9a-f]{64}", lock["ubuntu_keyring_sha256"]):
            raise SnapshotError("invalid Ubuntu keyring identity")
        releases = lock["signed_releases"]
        expected_releases = {f"snapshot.ubuntu.com_ubuntu_{SNAPSHOT}_dists_{suite}_InRelease"
                             for suite in ("noble", "noble-updates", "noble-security")}
        if (not isinstance(releases, list) or len(releases) != 3
                or {r["file"] for r in releases} != expected_releases):
            raise SnapshotError("unexpected signed repository metadata")
        for r in releases:
            if (not re.fullmatch(r"[0-9a-f]{64}", r["sha256"])
                    or not isinstance(r["valid_signature"], str)
                    or not r["valid_signature"].startswith(
                        "[GNUPG:] VALIDSIG F6ECB3762474EDA9D21B7022871920D1991BC93C ")):
                raise SnapshotError("invalid repository signature record")
        for p in packages:
            filename = f"{p['package']}_{p['version']}_arm64.deb"
            if (p["architecture"] != "arm64" or p["filename"] != filename
                    or type(p["size_bytes"]) is not int or not 0 < p["size_bytes"] <= 32 * 1024 * 1024
                    or not re.fullmatch(r"[0-9a-f]{64}", p["sha256"])
                    or not re.fullmatch(r"[0-9a-f]{64}", p["copyright_sha256"])
                    or p["copyright_path"] != f"/usr/share/doc/{p['package']}/copyright"
                    or not re.fullmatch(re.escape(URL_PREFIX) + r"[a-z]/[a-z0-9-]+/" + re.escape(filename), p["url"])
                    or not isinstance(p["notice_licenses"], list) or not p["notice_licenses"]
                    or not all(isinstance(n, str) and n.strip() for n in p["notice_licenses"])):
                raise SnapshotError("invalid native package record")
    except (KeyError, TypeError, ValueError) as exc:
        raise SnapshotError(f"invalid native dependency lock: {exc}") from exc
    return lock


def verify_deb(path, record):
    path = Path(path)
    if (path.is_symlink() or not path.is_file() or path.stat().st_size != record["size_bytes"]
            or sha256(path.read_bytes()).hexdigest() != record["sha256"]):
        raise SnapshotError(f"native archive identity mismatch: {path.name}")


def _safe_cache(cache):
    cache = Path(cache)
    if any(p.is_symlink() for p in (cache, *cache.parents)):
        raise SnapshotError("native cache must not traverse symlinks")
    return cache


def acquire(record, cache=CACHE):
    cache = _safe_cache(cache)
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / record["filename"]
    if destination.exists() or destination.is_symlink():
        verify_deb(destination, record)
        return destination
    with tempfile.TemporaryDirectory(prefix=".ep-deb-", dir=cache) as temporary:
        stage = Path(temporary) / record["filename"]
        _download(record["url"], stage, record["size_bytes"], timeout=30, attempts=3)
        verify_deb(stage, record)
        try:
            destination.hardlink_to(stage)
        except FileExistsError:
            verify_deb(destination, record)
    return destination


def prepare(cache=CACHE):
    lock = load_lock()
    cache = _safe_cache(cache)
    source_context = ep_sources.prepare()
    # Reuse the exact existing native build instructions/layer. No copied compiler recipe.
    original = RECIPE.with_name("ep_runtime.Dockerfile").read_text()
    prefix, marker, _ = original.partition("FROM xgboost-runtime AS reference-candidate\n")
    if not marker:
        raise SnapshotError("upstream native-stage recipe boundary changed")
    recipe = (prefix + RECIPE.read_text()).encode()
    files = {p.name: p for p in source_context.iterdir() if p.name != "sources.sha256"}
    files.update({LOCK.name: LOCK, INSTALLER.name: INSTALLER})
    for p in lock["packages"]:
        path = cache / p["filename"]
        verify_deb(path, p)
        files[p["filename"]] = path
    identities = {name: sha256(p.read_bytes()).hexdigest() for name, p in sorted(files.items())}
    identities["Dockerfile"] = sha256(recipe).hexdigest()
    context_id = sha256(json.dumps(identities, sort_keys=True).encode()).hexdigest()
    context = source_context.parent / f"full-context-{context_id}"
    guard = source_context.parent / ".ep-native-context.lock"
    try:
        with guard.open("x"):
            pass
    except FileExistsError as exc:
        raise SnapshotError("native context lock exists; preserve and inspect it") from exc
    try:
        with tempfile.TemporaryDirectory(prefix=".ep-native-context-", dir=context.parent) as temporary:
            stage = Path(temporary) / "context"
            stage.mkdir()
            for name, path in files.items():
                shutil.copyfile(path, stage / name)
                if sha256((stage / name).read_bytes()).hexdigest() != identities[name]:
                    raise SnapshotError("context input changed while copying")
            (stage / "Dockerfile").write_bytes(recipe)
            checksums = "".join(f"{digest}  {name}\n" for name, digest in sorted(identities.items()))
            (stage / "sources.sha256").write_text(checksums, encoding="utf-8")
            if context.exists() or context.is_symlink():
                if (context.is_symlink() or not context.is_dir()
                        or {p.name for p in context.iterdir()} != set(identities) | {"sources.sha256"}):
                    raise SnapshotError("existing native context differs; preserve and inspect it")
                for path in stage.iterdir():
                    target = context / path.name
                    if target.is_symlink() or not target.is_file() or target.read_bytes() != path.read_bytes():
                        raise SnapshotError("existing native context bytes differ; preserve and inspect it")
            else:
                stage.rename(context)
    finally:
        guard.unlink()
    return context


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("acquire", "verify", "prepare"))
    args = parser.parse_args()
    try:
        lock = load_lock()
        cache = _safe_cache(CACHE)
        for p in lock["packages"]:
            if args.action == "acquire":
                acquire(p, cache)
            else:
                verify_deb(cache / p["filename"], p)
        context = str(prepare(cache)) if args.action == "prepare" else None
    except (OSError, ValueError, tarfile.TarError, EOFError) as exc:
        parser.exit(1, f"EP native setup failed: {exc}\n")
    print(json.dumps({"status": "native_sources_verified", "packages": len(lock["packages"]),
                      "context": context, "model_executed": False}, indent=2))


if __name__ == "__main__":
    main()
