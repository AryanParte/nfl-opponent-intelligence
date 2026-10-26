"""Offline source-lock/setup tests; no real downloads, Docker, R or predictions."""

from copy import deepcopy
from hashlib import sha256
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from opponent_intelligence.snapshots import SnapshotError
from validation import ep_sources as sources


class EPSourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.cache = self.root / "cache"
        self.cache.mkdir()
        self.body = self.archive({"example/LICENSE": b"invented notice", "example/DESCRIPTION": b"synthetic"})
        self.record = dict(package="example", version="1", filename="example_1.tar.gz",
                           acquisition="https", url="https://example.invalid/source",
                           archive_root="example", size_bytes=len(self.body),
                           sha256=sha256(self.body).hexdigest(), uncompressed_bytes=24,
                           declared_license="Synthetic test only",
                           terms_files={"example/LICENSE": sha256(b"invented notice").hexdigest()})

    def archive(self, files, special=None):
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w:gz") as tar:
            for name, raw in files.items():
                info = tarfile.TarInfo(name)
                info.size = len(raw)
                tar.addfile(info, io.BytesIO(raw))
            if special:
                tar.addfile(special)
        return output.getvalue()

    def write(self, body=None):
        path = self.cache / self.record["filename"]
        path.write_bytes(self.body if body is None else body)
        return path

    def test_real_lock_source_pins_and_no_silent_xgboost_downgrade(self):
        lock = sources.load_lock()
        self.assertEqual(len(lock["packages"]), 43)
        records = {p["package"]: p for p in lock["packages"]}
        self.assertEqual(records["xgboost"]["version"], "3.4.2.1")
        self.assertEqual(records["xgboost"]["sha256"],
                         "d7de76bdaf48e9e0bc84b27c0c42f15f3d831e624d102d6c019bab7027b3cabd")
        artifact = json.loads((sources.LOCK.parent.parent / "docs/evidence/ep-package-acquisition.json").read_text())
        ep = [d for d in records["fastrmodels"]["bundled_data"] if d["path"].endswith("/ep_model.rda")][0]
        self.assertEqual(ep["sha256"], artifact["files"]["ep_model.rda"]["sha256"])
        self.assertEqual(len(records["fastrmodels"]["bundled_data"]), 7)
        self.assertTrue(all(p["terms_files"] for p in lock["packages"]))

    def test_lock_rejects_wrong_runtime_paths_urls_commits_and_duplicate_order(self):
        lock = sources.load_lock()
        mutations = [lambda l: l.update(schema_version=True), lambda l: l.update(base_image="latest"),
                     lambda l: l["packages"][0].update(filename="../unsafe.tar.gz"),
                     lambda l: l["packages"][0].update(url="https://example.invalid"),
                     lambda l: l["packages"][0].update(size_bytes=True),
                     lambda l: l["packages"][0].update(terms_files={}),
                     lambda l: l["packages"][0].update(archive_root="../unsafe"),
                     lambda l: l["install_order"].reverse(),
                     lambda l: l["packages"].append(l["packages"][0]),
                     lambda l: next(p for p in l["packages"] if p["package"] == "nflfastR").update(commit="main")]
        for mutate in mutations:
            changed = deepcopy(lock)
            mutate(changed)
            with patch.object(sources, "_read_json", return_value=changed):
                with self.assertRaises(SnapshotError):
                    sources.load_lock()

    def test_valid_archive_is_verified_without_extraction(self):
        path = self.write()
        sources.verify_source(path, self.record)
        self.assertEqual(list(self.cache.iterdir()), [path])

    def test_corrupt_or_symlink_source_is_not_repaired(self):
        path = self.write(b"corrupt")
        with patch.object(sources, "_download") as download:
            with self.assertRaises(SnapshotError):
                sources.acquire_source(self.record, self.cache)
        download.assert_not_called()
        self.assertEqual(path.read_bytes(), b"corrupt")
        path.unlink()
        path.symlink_to(self.root / "missing")
        with self.assertRaises(SnapshotError):
            sources.acquire_source(self.record, self.cache)

    def test_safe_member_and_notice_checks_even_with_updated_archive_hash(self):
        link = tarfile.TarInfo("example/link")
        link.type, link.linkname = tarfile.SYMTYPE, "/etc/passwd"
        duplicate = tarfile.TarInfo("example/LICENSE")
        bodies = [self.archive({"../escape": b"bad"}), self.archive({"/example/LICENSE": b"bad"}),
                  self.archive({"wrong/LICENSE": b"bad"}), self.archive({"example/LICENSE": b"wrong"}),
                  self.archive({"example/LICENSE": b"invented notice"}, link),
                  self.archive({"example/LICENSE": b"invented notice"}, duplicate)]
        for raw in bodies:
            record = self.record | {"size_bytes": len(raw), "sha256": sha256(raw).hexdigest()}
            with self.assertRaises(SnapshotError):
                sources.verify_source(self.write(raw), record)

    def test_download_is_bounded_then_verified_and_existing_cache_is_offline(self):
        def download(url, path, limit, timeout, attempts):
            self.assertEqual((url, limit, timeout, attempts),
                             (self.record["url"], len(self.body), 30, 3))
            path.write_bytes(self.body)
        with patch.object(sources, "_download", side_effect=download) as downloader:
            path = sources.acquire_source(self.record, self.cache)
            self.assertEqual(sources.acquire_source(self.record, self.cache), path)
        self.assertEqual(downloader.call_count, 1)
        self.assertEqual(list(self.cache.iterdir()), [path])

    def test_normalized_duplicate_paths_fail_even_when_notices_and_sizes_match(self):
        raw = self.archive({"example/LICENSE": b"invented notice",
                            "example/DESCRIPTION": b"synthetic",
                            "example/EXTRA": b"first", "example/./EXTRA": b"second"})
        record = self.record | {"size_bytes": len(raw), "sha256": sha256(raw).hexdigest(),
                                "uncompressed_bytes": 35}
        with self.assertRaisesRegex(SnapshotError, "unsafe/duplicate"):
            sources.verify_source(self.write(raw), record)

    def test_failed_download_does_not_publish_partial_bytes(self):
        def partial(url, path, *args, **kwargs):
            path.write_bytes(b"partial")
            raise SnapshotError("synthetic interrupted transfer")
        with patch.object(sources, "_download", side_effect=partial):
            with self.assertRaises(SnapshotError):
                sources.acquire_source(self.record, self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_git_tag_mismatch_stops_before_archive_publication(self):
        record = self.record | dict(acquisition="git_archive", tag="v1", commit="a" * 40,
                                    source_repository="https://example.invalid/repo.git")
        with patch.object(sources.subprocess, "run") as run, patch.object(
                sources.subprocess, "check_output", return_value="b" * 40):
            with self.assertRaisesRegex(SnapshotError, "tag no longer"):
                sources.acquire_source(record, self.cache, git="/test/git")
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0][0], "/test/git")
        self.assertEqual(run.call_args.kwargs["timeout"], 180)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_matching_git_commit_is_archived_verified_and_reused_offline(self):
        record = self.record | dict(acquisition="git_archive", tag="v1", commit="a" * 40,
                                    source_repository="https://example.invalid/repo.git")
        def run(command, **kwargs):
            if "archive" in command:
                self.assertEqual(kwargs, {"check": True, "timeout": 60})
                self.assertEqual(command[-1], record["commit"])
                self.assertIn("--prefix=example/", command)
                target = next(arg.removeprefix("--output=") for arg in command if arg.startswith("--output="))
                Path(target).write_bytes(self.body)
        with patch.object(sources.subprocess, "run", side_effect=run) as invoked, patch.object(
                sources.subprocess, "check_output", return_value=record["commit"] + "\n") as revision:
            path = sources.acquire_source(record, self.cache, git="/test/git")
            self.assertEqual(sources.acquire_source(record, self.cache, git="/test/git"), path)
        self.assertEqual(invoked.call_count, 2)
        self.assertEqual(revision.call_count, 1)
        self.assertEqual(path.read_bytes(), self.body)
        self.assertEqual(list(self.cache.iterdir()), [path])

    def test_concurrent_publication_never_overwrites_other_file(self):
        def download(url, path, *args, **kwargs):
            path.write_bytes(self.body)
            self.write(b"other writer")
        with patch.object(sources, "_download", side_effect=download):
            with self.assertRaises(SnapshotError):
                sources.acquire_source(self.record, self.cache)
        self.assertEqual((self.cache / self.record["filename"]).read_bytes(), b"other writer")

    def prepare(self):
        lock = self.root / "ep_runtime.lock.json"
        lock.write_text("synthetic lock bytes")
        with patch.object(sources, "LOCK", lock), patch.object(sources, "load_lock", return_value={"packages": [self.record]}):
            return sources.prepare(self.cache)

    def test_context_contains_only_verified_sources_and_reuses_identical_bytes(self):
        self.write()
        (self.cache / "ignored-partial.tar.gz").write_bytes(b"interrupted prior download")
        context = self.prepare()
        self.assertEqual(context, self.prepare())
        self.assertEqual({p.name for p in context.iterdir()},
                         {self.record["filename"], "ep_runtime.lock.json", "ep_install.R", "sources.sha256"})
        for line in (context / "sources.sha256").read_text().splitlines():
            digest, name = line.split("  ")
            self.assertEqual(digest, sha256((context / name).read_bytes()).hexdigest())

    def test_context_corruption_and_stale_guard_are_preserved(self):
        self.write()
        context = self.prepare()
        changed = context / self.record["filename"]
        changed.write_bytes(b"changed context")
        with self.assertRaises(SnapshotError):
            self.prepare()
        self.assertEqual(changed.read_bytes(), b"changed context")
        guard = self.root / ".ep-context.lock"
        guard.write_text("other process")
        with self.assertRaisesRegex(SnapshotError, "lock exists"):
            self.prepare()
        self.assertEqual(guard.read_text(), "other process")

    def test_source_cache_symlink_is_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.cache, target_is_directory=True)
        with self.assertRaises(SnapshotError):
            sources.acquire_source(self.record, alias)
        with self.assertRaises(SnapshotError):
            sources.prepare(alias)


class EPRuntimeEvidenceTests(unittest.TestCase):
    def test_native_receipt_is_bound_but_full_reference_is_unavailable(self):
        root = sources.LOCK.parent.parent
        receipt = json.loads((root / "docs/evidence/ep-native-runtime.json").read_text())
        for field, path in (("source_lock_sha256", sources.LOCK),
                            ("dockerfile_sha256", sources.LOCK.with_name("ep_runtime.Dockerfile")),
                            ("runner_sha256", sources.LOCK.with_name("ep_runtime_check.R"))):
            self.assertEqual(receipt[field], sha256(path.read_bytes()).hexdigest())
        native = receipt["native_receipt"]
        packages = {p["Package"]: p["Version"] for p in native["installed_packages"]}
        self.assertEqual(packages["xgboost"], "3.4.2.1")
        self.assertEqual(native["xgboost_config"]["nthread"], 1)
        self.assertFalse(native["nflfastr_installed"])
        for key in ("full_reference_ready", "model_executed", "predictive_validation"):
            self.assertIs(native[key], False)
        self.assertIs(receipt["model_predictions_available"], False)
        self.assertEqual(receipt["full_reference_build"]["status"], "failed")
        self.assertEqual(receipt["full_reference_build"]["package"], "curl")

    def test_bundled_assets_include_internal_and_test_data_not_just_ep(self):
        root = sources.LOCK.parent.parent
        assets = json.loads((root / "docs/evidence/ep-bundled-source-assets.json").read_text())["packages"]
        self.assertEqual({name: len(rows) for name, rows in assets.items()},
                         {"fastrmodels": 7, "nflfastR": 19, "nflreadr": 27})
        nfl_paths = {row["path"] for row in assets["nflfastR"]}
        prefix = "nflfastR-" + sources.SOURCE_COMMITS["nflfastR"]
        self.assertIn(prefix + "/R/sysdata.rda", nfl_paths)
        self.assertIn(prefix + "/tests/testthat/expected_ep.rds", nfl_paths)
        self.assertIn(prefix + "/tests/testthat/2019/2019_01_GB_CHI.rds", nfl_paths)
        for record in sources.load_lock()["packages"]:
            for row in record.get("bundled_data", []):
                self.assertIn(row, assets[record["package"]])
