"""Explicit wheel/source preparation for the optional native Python EP experiment.

Downloads only reviewed hash-pinned wheels; never installs packages or executes
their code. Source build and offline installation are separate documented steps.
"""

import argparse
from email.parser import BytesParser
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import stat
import tarfile
import tempfile
import zipfile

from opponent_intelligence.snapshots import SnapshotError, _download
from validation import ep_sources


LOCK = Path(__file__).with_name("ep_python.lock.json")
CACHE = Path(".cache/ep-python/wheels")
VERSIONS = {"numpy": "2.3.4", "scipy": "1.16.3", "scikit-build-core": "0.11.6",
            "packaging": "25.0", "pathspec": "0.12.1", "cmake": "3.31.10", "ninja": "1.13.0"}


def require(condition, message):
    if not condition:
        raise SnapshotError(message)


def load_lock():
    lock = json.loads(LOCK.read_bytes())
    require(lock["schema_version"] == 1 and type(lock["schema_version"]) is int and
            lock["python_version"] == "3.13.2" and lock["platform"] == "macos-arm64" and
            lock["xgboost_version"] == "3.4.2", "unexpected Python experiment identity")
    records = lock["wheels"]
    require(len(records) == len(VERSIONS) and
            {p["name"]: p["version"] for p in records} == VERSIONS, "wheel versions differ")
    require(len({p["filename"] for p in records}) == len(records), "duplicate wheel filename")
    for p in records:
        require(re.fullmatch(r"[A-Za-z0-9_.-]+\.whl", p["filename"]) is not None and
                re.fullmatch(r"[0-9a-f]{64}", p["sha256"]) is not None and
                type(p["size_bytes"]) is int and 0 < p["size_bytes"] < 64 * 1024 * 1024,
                "invalid wheel identity/bound")
        require(p["url"].startswith("https://files.pythonhosted.org/packages/") and
                p["url"].endswith("/" + p["filename"]), "unreviewed wheel host/path")
        require(isinstance(p.get("license_review"), str) and bool(p["license_review"]) and
                isinstance(p.get("notice_hashes"), dict) and bool(p["notice_hashes"]) and
                all(isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v)
                    for v in p["notice_hashes"].values()), "missing/invalid notice review")
    source = next(p for p in ep_sources.load_lock()["packages"] if p["package"] == "xgboost")
    require((lock["source_archive"], lock["source_sha256"], lock["source_commit"]) ==
            (source["filename"], source["sha256"], source["commit"]), "XGBoost source drift")
    return lock


def verify_wheel(path, record):
    require(not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file(),
            "wheel must be a regular file without symlink ancestors")
    require(path.stat().st_size == record["size_bytes"], "wheel size differs")
    require(sha256(path.read_bytes()).hexdigest() == record["sha256"], "wheel digest differs")
    notices, metadata, names, size = {}, [], set(), 0
    with zipfile.ZipFile(path) as archive:
        for item in archive.infolist():
            p = PurePosixPath(item.filename)
            require(not p.is_absolute() and ".." not in p.parts and "\\" not in item.filename
                    and p not in names and not stat.S_ISLNK(item.external_attr >> 16),
                    "unsafe/duplicate wheel member")
            names.add(p)
            size += item.file_size
            require(size <= 512 * 1024 * 1024 and len(names) <= 25000, "wheel expansion limit")
            name = p.name.lower()
            if (name.startswith(("license", "licence", "copying", "copyright")) or
                    any(part.lower() in ("licenses", "licences") for part in p.parts)
                    and p.suffix.lower() not in (".py", ".pyc")):
                if not item.is_dir():
                    require(item.file_size <= 1024 * 1024, "oversized notice")
                    notices[item.filename] = sha256(archive.read(item)).hexdigest()
            if item.filename.endswith(".dist-info/METADATA"):
                require(item.file_size <= 1024 * 1024, "oversized metadata")
                metadata.append(BytesParser().parsebytes(archive.read(item)))
    require(len(metadata) == 1 and bool(notices), "missing metadata/notices")
    info = metadata[0]
    require(info["Name"].lower().replace("_", "-") == record["name"] and
            info["Version"] == record["version"], "wheel metadata identity differs")
    if "notice_hashes" in record:
        require(notices == record["notice_hashes"], "wheel notice identities differ")
    return {"name": record["name"], "version": info["Version"], "notice_hashes": notices,
            "license_declaration_header": (info["License-Expression"] or info["License"] or "").split("\n")[0],
            "license_classifiers": [v for v in info.get_all("Classifier", []) if v.startswith("License")],
            "requires_dist": info.get_all("Requires-Dist", []), "uncompressed_bytes": size}


def acquire(record, cache=CACHE):
    cache = Path(cache)
    require(not any(p.is_symlink() for p in (cache, *cache.parents)), "symlink cache path")
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / record["filename"]
    if path.exists() or path.is_symlink():
        verify_wheel(path, record)
        return path
    with tempfile.TemporaryDirectory(prefix=".wheel-", dir=cache) as temporary:
        staged = Path(temporary) / path.name
        _download(record["url"], staged, record["size_bytes"], timeout=30, attempts=3)
        verify_wheel(staged, record)
        try:
            path.hardlink_to(staged)
        except FileExistsError:
            verify_wheel(path, record)
    return path


def prepare_source(parent):
    source = next(p for p in ep_sources.load_lock()["packages"] if p["package"] == "xgboost")
    archive = ep_sources.CACHE / source["filename"]
    ep_sources.verify_source(archive, source)
    parent = Path(parent)
    require(not any(p.is_symlink() for p in (parent, *parent.parents)), "symlink build path")
    parent.mkdir(parents=True, exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix="source-", dir=parent))
    with tarfile.open(archive) as bundle:
        bundle.extractall(destination, filter="data")
    return destination / source["archive_root"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--acquire", action="store_true")
    action.add_argument("--verify", action="store_true")
    action.add_argument("--prepare-source", action="store_true")
    args = parser.parse_args()
    lock = load_lock()
    if args.prepare_source:
        print(prepare_source(Path(".cache/ep-python/builds")))
        return
    for record in lock["wheels"]:
        path = acquire(record) if args.acquire else CACHE / record["filename"]
        print(json.dumps(verify_wheel(path, record)))


if __name__ == "__main__":
    main()
