"""Offline synthetic transport/context tests; no Docker, R or football predictions."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from opponent_intelligence.snapshots import SnapshotError
from validation import ep_native as native


class EPNativeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.cache = self.root / "archives"
        self.cache.mkdir()
        self.body = b"synthetic archive bytes, not a Debian package"
        self.record = {"filename": "example_1_arm64.deb", "url": "https://example.invalid/fixture",
                       "size_bytes": len(self.body), "sha256": sha256(self.body).hexdigest()}
        self.path = self.cache / self.record["filename"]

    def test_real_lock_keeps_base_and_exact_seven_additions(self):
        lock = native.load_lock()
        self.assertEqual({p["package"]: p["version"] for p in lock["packages"]}, native.VERSIONS)
        self.assertEqual(lock["base_image"], native.ep_sources.IMAGE)
        self.assertEqual(lock["resolution"]["upgraded"], 0)
        self.assertEqual(lock["resolution"]["removed"], 0)
        self.assertEqual(lock["resolution"]["newly_installed"], 7)
        self.assertEqual(len({p["copyright_sha256"] for p in lock["packages"]}), 3)

    def test_lock_rejects_identity_transport_size_terms_and_signature_drift(self):
        mutations = [
            lambda x: x.update(schema_version=True), lambda x: x.update(base_image="latest"),
            lambda x: x.update(snapshot="latest"), lambda x: x.update(platform="linux/amd64"),
            lambda x: x["packages"].append(x["packages"][0]),
            lambda x: x["packages"][0].update(version="new"),
            lambda x: x["packages"][0].update(filename="../escape.deb"),
            lambda x: x["packages"][0].update(architecture="amd64"),
            lambda x: x["packages"][0].update(size_bytes=True),
            lambda x: x["packages"][0].update(size_bytes=33 * 1024 * 1024),
            lambda x: x["packages"][0].update(sha256="bad"),
            lambda x: x["packages"][0].update(url="https://example.invalid/a.deb"),
            lambda x: x["packages"][0].update(copyright_path="/etc/passwd"),
            lambda x: x["packages"][0].update(copyright_sha256="bad"),
            lambda x: x["packages"][0].update(notice_licenses="MIT"),
            lambda x: x["packages"][0].update(notice_licenses=[None]),
            lambda x: x["packages"][0].update(notice_licenses=[]),
            lambda x: x.update(ubuntu_keyring_sha256="bad"),
            lambda x: x["signed_releases"].pop(),
            lambda x: x["signed_releases"][0].update(file="../InRelease"),
            lambda x: x["signed_releases"][0].update(sha256="bad"),
            lambda x: x["signed_releases"][0].update(valid_signature="wrong signer"),
        ]
        lock = native.load_lock()
        for i, change in enumerate(mutations):
            with self.subTest(mutation=i):
                changed = deepcopy(lock)
                change(changed)
                with patch.object(native, "_read_json", return_value=changed):
                    with self.assertRaises(SnapshotError):
                        native.load_lock()

    def test_archive_hash_size_and_regular_file_are_required(self):
        for body in (b"truncated", b"x" * len(self.body)):
            self.path.write_bytes(body)
            with self.assertRaises(SnapshotError):
                native.verify_deb(self.path, self.record)
        self.path.unlink()
        self.path.mkdir()
        with self.assertRaises(SnapshotError):
            native.verify_deb(self.path, self.record)

    def test_acquisition_is_bounded_and_valid_cache_is_offline(self):
        def download(url, path, limit, timeout, attempts):
            self.assertEqual((url, limit, timeout, attempts),
                             (self.record["url"], len(self.body), 30, 3))
            path.write_bytes(self.body)
        with patch.object(native, "_download", side_effect=download) as call:
            self.assertEqual(native.acquire(self.record, self.cache), self.path)
            self.assertEqual(native.acquire(self.record, self.cache), self.path)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(list(self.cache.iterdir()), [self.path])

    def test_bad_existing_file_is_preserved_without_network_or_repair(self):
        self.path.write_bytes(b"preserve me")
        with patch.object(native, "_download") as call:
            with self.assertRaises(SnapshotError):
                native.acquire(self.record, self.cache)
        call.assert_not_called()
        self.assertEqual(self.path.read_bytes(), b"preserve me")

    def test_links_and_symlink_cache_ancestors_are_rejected(self):
        self.path.symlink_to(self.root / "missing")
        with self.assertRaises(SnapshotError):
            native.acquire(self.record, self.cache)
        alias = self.root / "alias"
        alias.symlink_to(self.cache, target_is_directory=True)
        with self.assertRaises(SnapshotError):
            native.acquire(self.record, alias / "child")
        with self.assertRaises(SnapshotError):
            native.prepare(alias)

    def test_interrupted_or_corrupt_transfer_never_publishes(self):
        def interrupted(url, path, *args, **kwargs):
            path.write_bytes(b"partial")
            raise SnapshotError("synthetic interruption")
        def corrupt(url, path, *args, **kwargs):
            path.write_bytes(b"x" * len(self.body))
        for transfer in (interrupted, corrupt):
            with patch.object(native, "_download", side_effect=transfer):
                with self.assertRaises(SnapshotError):
                    native.acquire(self.record, self.cache)
            self.assertEqual(list(self.cache.iterdir()), [])

    def test_concurrent_publication_does_not_overwrite_and_can_reuse_matching_bytes(self):
        for other in (b"other writer", self.body):
            def download(url, path, *args, **kwargs):
                path.write_bytes(self.body)
                self.path.write_bytes(other)
            with patch.object(native, "_download", side_effect=download):
                if other == self.body:
                    self.assertEqual(native.acquire(self.record, self.cache), self.path)
                else:
                    with self.assertRaises(SnapshotError):
                        native.acquire(self.record, self.cache)
            self.assertEqual(self.path.read_bytes(), other)
            self.path.unlink()

    def setup_context(self):
        self.path.write_bytes(self.body)
        self.source = self.root / "source-context"
        self.source.mkdir()
        for name in ("r-source.tar.gz", "ep_runtime.lock.json", "ep_install.R", "sources.sha256"):
            (self.source / name).write_text("synthetic source context " + name)
        self.recipe = self.root / "ep_native.Dockerfile"
        self.recipe.write_text("FROM xgboost-runtime AS full-reference\nRUN native-and-R-install\n")
        self.original = self.root / "ep_runtime.Dockerfile"
        self.original.write_text("FROM pinned-base AS xgboost-runtime\nRUN native-compile\n"
                                 "FROM xgboost-runtime AS reference-candidate\nRUN old-failure\n")
        self.installer = self.root / "ep_native_install.R"
        self.installer.write_text("synthetic native installer")
        self.lock = self.root / "ep_native.lock.json"
        self.lock.write_text("synthetic native lock")

    def prepare(self):
        with patch.object(native.ep_sources, "prepare", return_value=self.source), \
                patch.object(native, "load_lock", return_value={"packages": [self.record]}), \
                patch.object(native, "RECIPE", self.recipe), patch.object(native, "LOCK", self.lock), \
                patch.object(native, "INSTALLER", self.installer):
            return native.prepare(self.cache)

    def test_context_is_curated_hashed_and_reuses_native_stage(self):
        self.setup_context()
        (self.cache / "ignored-partial.deb").write_bytes(b"partial unrelated acquisition")
        context = self.prepare()
        self.assertEqual(context, self.prepare())
        self.assertEqual({p.name for p in context.iterdir()}, {
            "r-source.tar.gz", "ep_runtime.lock.json", "ep_install.R", "sources.sha256",
            "ep_native.lock.json", "ep_native_install.R", self.record["filename"], "Dockerfile"})
        recipe = (context / "Dockerfile").read_text()
        self.assertTrue(recipe.startswith("FROM pinned-base AS xgboost-runtime\nRUN native-compile\n"))
        self.assertIn("AS full-reference", recipe)
        self.assertNotIn("old-failure", recipe)
        checked = set()
        for line in (context / "sources.sha256").read_text().splitlines():
            digest, name = line.split("  ")
            checked.add(name)
            self.assertEqual(digest, sha256((context / name).read_bytes()).hexdigest())
        self.assertEqual(checked, {p.name for p in context.iterdir()} - {"sources.sha256"})

    def test_existing_context_corruption_is_not_repaired(self):
        self.setup_context()
        context = self.prepare()
        changed = context / self.record["filename"]
        changed.write_bytes(b"other writer")
        with self.assertRaisesRegex(SnapshotError, "bytes differ"):
            self.prepare()
        self.assertEqual(changed.read_bytes(), b"other writer")
        self.assertFalse((self.root / ".ep-native-context.lock").exists())

    def test_existing_context_symlink_or_extra_file_is_not_followed_or_deleted(self):
        self.setup_context()
        context = self.prepare()
        saved = self.root / "saved-context"
        context.rename(saved)
        context.symlink_to(saved, target_is_directory=True)
        with self.assertRaises(SnapshotError):
            self.prepare()
        self.assertTrue(context.is_symlink())
        context.unlink()
        saved.rename(context)
        (context / "unexpected").write_text("preserve")
        with self.assertRaises(SnapshotError):
            self.prepare()
        self.assertEqual((context / "unexpected").read_text(), "preserve")

    def test_stale_context_guard_is_preserved(self):
        self.setup_context()
        guard = self.root / ".ep-native-context.lock"
        guard.write_text("another process")
        with self.assertRaisesRegex(SnapshotError, "lock exists"):
            self.prepare()
        self.assertEqual(guard.read_text(), "another process")

    def test_bad_archive_or_native_stage_boundary_stops_context_creation(self):
        self.setup_context()
        self.path.write_bytes(b"bad")
        with self.assertRaises(SnapshotError):
            self.prepare()
        self.path.write_bytes(self.body)
        self.original.write_text("FROM unrelated-stage\n")
        with self.assertRaisesRegex(SnapshotError, "boundary changed"):
            self.prepare()
        self.assertEqual(list(self.root.glob("full-context-*")), [])

    def test_changed_installer_or_recipe_creates_distinct_context_without_overwriting(self):
        self.setup_context()
        first = self.prepare()
        self.installer.write_text("updated synthetic installer")
        second = self.prepare()
        self.recipe.write_text("FROM xgboost-runtime AS full-reference\nRUN different-install\n")
        third = self.prepare()
        self.assertEqual(len({first, second, third}), 3)
        self.assertEqual((first / self.installer.name).read_text(), "synthetic native installer")

    def test_copy_corruption_is_rejected_and_staging_cleaned(self):
        self.setup_context()
        copy = native.shutil.copyfile
        def corrupt(source, target):
            copy(source, target)
            Path(target).write_bytes(b"changed while copying")
        with patch.object(native.shutil, "copyfile", side_effect=corrupt):
            with self.assertRaisesRegex(SnapshotError, "changed while copying"):
                self.prepare()
        self.assertEqual(list(self.root.glob("full-context-*")), [])
        self.assertFalse((self.root / ".ep-native-context.lock").exists())


class EPFullRuntimeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.root = native.LOCK.parent.parent
        self.receipt = json.loads((self.root / "docs/evidence/ep-full-runtime.json").read_text())

    def test_receipt_binds_locks_installers_recipe_and_runner(self):
        self.assertEqual(set(self.receipt["inputs"]), {
            "validation/ep_native.lock.json", "validation/ep_native.sources",
            "validation/ep_native.py", "validation/ep_native_audit.R",
            "validation/ep_native_install.R", "validation/ep_native.Dockerfile",
            "validation/ep_full_runtime_check.R", "validation/ep_runtime.lock.json",
            "validation/ep_runtime.Dockerfile", "validation/ep_install.R"})
        for path, digest in self.receipt["inputs"].items():
            self.assertEqual(sha256((self.root / path).read_bytes()).hexdigest(), digest, path)
        runtime = self.receipt["runtime"]
        self.assertEqual(runtime["native_lock_sha256"], self.receipt["inputs"]["validation/ep_native.lock.json"])
        self.assertEqual(runtime["source_lock_sha256"], self.receipt["inputs"]["validation/ep_runtime.lock.json"])
        prefix = native.RECIPE.with_name("ep_runtime.Dockerfile").read_text().split(
            "FROM xgboost-runtime AS reference-candidate\n")[0]
        recipe_hash = sha256((prefix + native.RECIPE.read_text()).encode()).hexdigest()
        self.assertEqual(runtime["dockerfile_sha256"], recipe_hash)
        self.assertEqual(self.receipt["build"]["dockerfile_sha256"], recipe_hash)
        self.assertEqual(self.receipt["base_image"], native.ep_sources.IMAGE)
        self.assertEqual(self.receipt["native_source_audit"]["signed_releases"], native.load_lock()["signed_releases"])
        notices = {p["package"]: p for p in self.receipt["native_source_audit"]["packages"]}
        for p in native.load_lock()["packages"]:
            for field in ("version", "architecture", "sha256", "copyright_sha256"):
                self.assertEqual(notices[p["package"]][field], p[field])
        self.assertEqual(self.receipt["offline_replay"], "identical_json_twice")

    def test_installed_packages_match_locks_with_no_native_upgrades(self):
        runtime = self.receipt["runtime"]
        r_packages = {p["Package"]: p["Version"] for p in runtime["installed_r_packages"]}
        for p in native.ep_sources.load_lock()["packages"]:
            self.assertEqual(r_packages[p["package"]], p["version"])
        native_packages = {p["package"]: p for p in runtime["installed_native_packages"]}
        for p in native.load_lock()["packages"]:
            self.assertEqual(native_packages[p["package"]]["version"], p["version"])
            self.assertEqual(native_packages[p["package"]]["architecture"], "arm64")
        install = runtime["native_installation"]
        self.assertEqual(install["upgraded"], 0)
        self.assertEqual(install["removed"], 0)
        self.assertEqual(set(install["added"]), set(native.VERSIONS))
        self.assertEqual(install["after_count"] - install["before_count"], 7)
        self.assertEqual(len(native_packages), install["after_count"])
        self.assertNotIn("tcltk", runtime["required_r_packages"])
        self.assertEqual(runtime["unresolved_optional_libraries"], [{
            "path": "/usr/local/lib/R/library/tcltk/libs/tcltk.so",
            "libraries": ["libtcl8.6.so", "libtk8.6.so"]}])

    def test_equality_is_not_prediction_or_parity_evidence(self):
        runtime = self.receipt["runtime"]
        prior = json.loads((self.root / "docs/evidence/ep-r-object-inspection.json").read_text())["inspection"]
        for field in ("container_sha256", "raw_bytes", "raw_sha256"):
            self.assertEqual(runtime[field], prior[field])
        self.assertIs(runtime["installed_package_equality_verified"], True)
        self.assertIs(runtime["full_reference_installed"], True)
        for field in ("persisted_raw_export", "model_executed", "prediction_capture_available", "predictive_validation"):
            self.assertIs(runtime[field], False)
        self.assertEqual(runtime["xgboost_config"]["nthread"], 1)
