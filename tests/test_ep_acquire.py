"""Offline mutation tests. All artifact bytes and mocked R outputs are invented."""

from hashlib import sha1, sha256
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from opponent_intelligence.snapshots import SnapshotError
from validation import ep_acquire as ep, ep_probe


ROOT = Path(__file__).resolve().parents[1]


class EPAcquireTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.cache = Path(temporary.name).resolve() / "cache"
        self.original_files = dict(ep.FILES)
        self.bodies = {"ep_model.rda": b"invented R container, not an executable model",
                       "LICENSE.md": b"synthetic license fixture", "DESCRIPTION": b"synthetic metadata"}
        self.spec = {name: (self.original_files[name][0],
                           sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest(),
                           len(raw) if name == "ep_model.rda" else 1024)
                     for name, raw in self.bodies.items()}
        spec_patch = patch.dict(ep.FILES, self.spec, clear=True)
        spec_patch.start()
        self.addCleanup(spec_patch.stop)
        download_patch = patch.object(ep, "_download", side_effect=self.download)
        self.downloader = download_patch.start()
        self.addCleanup(download_patch.stop)

    def download(self, url, target, limit, *, timeout, attempts):
        self.assertEqual(url, f"{ep.ROOT_URL}/{self.spec[target.name][0]}")
        self.assertEqual((limit, timeout, attempts), (self.spec[target.name][2], 30, 3))
        target.write_bytes(self.bodies[target.name])

    def acquire(self):
        return ep.acquire(self.cache)

    def alter_manifest(self, directory, mutate):
        path = directory / "manifest.json"
        manifest = json.loads(path.read_text())
        mutate(manifest)
        path.write_text(json.dumps(manifest))

    def test_real_pins_match_prior_audit_without_loading_a_model(self):
        audit = json.loads((ROOT / "docs/evidence/fastrmodels-2.1.0-interface-audit.json").read_text())
        source = audit["sources"]["nflverse/fastrmodels"]
        self.assertEqual(ep.COMMIT, source["commit"])
        self.assertEqual(ep.RELEASED_AT, source["release_published_at"])
        self.assertEqual(self.original_files["ep_model.rda"][1:],
                         (audit["artifacts"][0]["git_blob_sha1"], audit["artifacts"][0]["package_bytes"]))
        for name in ("LICENSE.md", "DESCRIPTION"):
            self.assertEqual(self.original_files[name][1], source["source_blobs"][name])

    def test_acquisition_pins_git_framing_sha256_terms_and_null_lineage(self):
        directory = self.acquire()
        manifest = ep.verify(directory)
        self.assertEqual(self.downloader.call_count, 3)
        self.assertEqual(directory.name, ep.SNAPSHOT_NAME)
        self.assertIsNone(manifest["source"]["verified_training_window"])
        self.assertEqual(manifest["source"]["license"]["identifier"], "MIT")
        for name, raw in self.bodies.items():
            self.assertEqual((directory / name).read_bytes(), raw)
            self.assertEqual(manifest["files"][name]["sha256"], sha256(raw).hexdigest())
            self.assertNotEqual(manifest["files"][name]["git_blob_sha1"], sha1(raw).hexdigest())
        self.assertEqual({p.name for p in self.cache.iterdir()}, {ep.SNAPSHOT_NAME})

    def test_verified_cache_is_reused_offline_without_changing_receipt(self):
        directory = self.acquire()
        before = (directory / "manifest.json").read_bytes()
        self.downloader.reset_mock()
        self.assertEqual(self.acquire(), directory)
        self.downloader.assert_not_called()
        self.assertEqual((directory / "manifest.json").read_bytes(), before)

    def test_corruption_cannot_be_hidden_by_rehashing_the_manifest(self):
        directory = self.acquire()
        changed = b"different synthetic bytes"
        (directory / "ep_model.rda").write_bytes(changed)
        self.alter_manifest(directory, lambda m: m["files"]["ep_model.rda"].update(
            sha256=sha256(changed).hexdigest(), size_bytes=len(changed)))
        self.downloader.reset_mock()
        with self.assertRaisesRegex(SnapshotError, "Git blob"):
            self.acquire()
        self.downloader.assert_not_called()
        self.assertEqual((directory / "ep_model.rda").read_bytes(), changed)

    def test_all_manifest_identity_and_fingerprint_changes_fail(self):
        directory = self.acquire()
        original = (directory / "manifest.json").read_bytes()
        mutations = [lambda m: m.update(schema_version=True), lambda m: m.update(extra="unexpected"),
                     lambda m: m.update(retrieved_at_utc="2024-01-01"),
                     lambda m: m["source"].update(commit="main"),
                     lambda m: m["source"].update(verified_training_window="1999-2024"),
                     lambda m: m["source"]["license"].update(identifier="CC-BY-4.0"),
                     lambda m: m["files"]["LICENSE.md"].update(url="https://example.invalid"),
                     lambda m: m["files"]["ep_model.rda"].update(sha256="0" * 64)]
        for mutate in mutations:
            (directory / "manifest.json").write_bytes(original)
            self.alter_manifest(directory, mutate)
            with self.assertRaises(SnapshotError):
                ep.verify(directory)

    def test_missing_extra_and_symlink_snapshot_files_fail(self):
        directory = self.acquire()
        extra = directory / "unexpected"
        extra.touch()
        with self.assertRaises(SnapshotError):
            ep.verify(directory)
        extra.unlink()
        path = directory / "LICENSE.md"
        path.unlink()
        with self.assertRaises(SnapshotError):
            ep.verify(directory)
        path.symlink_to(directory / "DESCRIPTION")
        with self.assertRaises(SnapshotError):
            ep.verify(directory)
        alias = self.cache / "alias"
        alias.symlink_to(directory, target_is_directory=True)
        with self.assertRaises(SnapshotError):
            ep.verify(alias)

    def test_invalid_download_never_publishes_and_cleans_only_temporary_files(self):
        for raw in (b"", b"corrupt", b"x" * (self.spec["ep_model.rda"][2] + 1)):
            with patch.object(ep, "_download", side_effect=lambda u, p, *a, **k: p.write_bytes(raw)):
                with self.assertRaises(SnapshotError):
                    self.acquire()
            self.assertEqual(list(self.cache.iterdir()), [])
        self.assertTrue(self.acquire().is_dir())

    def test_transport_failure_and_publication_failure_preserve_no_partial_cache(self):
        with patch.object(ep, "_download", side_effect=SnapshotError("synthetic transfer failure")):
            with self.assertRaises(SnapshotError):
                self.acquire()
        self.assertEqual(list(self.cache.iterdir()), [])
        with patch.object(ep.os, "rename", side_effect=PermissionError("synthetic publication failure")):
            with self.assertRaises(PermissionError):
                self.acquire()
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_lock_and_preexisting_empty_directory_are_preserved(self):
        self.cache.mkdir()
        lock = self.cache / ".acquire.lock"
        lock.write_text("another run")
        with self.assertRaisesRegex(SnapshotError, "lock exists"):
            self.acquire()
        self.assertEqual(lock.read_text(), "another run")
        lock.unlink()
        destination = self.cache / ep.SNAPSHOT_NAME
        destination.mkdir()
        with self.assertRaises(SnapshotError):
            self.acquire()
        self.assertTrue(destination.is_dir())
        self.assertEqual(list(destination.iterdir()), [])
        self.downloader.assert_not_called()

    def test_symlink_cache_and_manifest_fail_without_network(self):
        directory = self.acquire()
        manifest = directory / "manifest.json"
        saved = self.cache / "saved.json"
        manifest.rename(saved)
        manifest.mkdir()
        with self.assertRaisesRegex(SnapshotError, "regular file"):
            ep.verify(directory)
        manifest.rmdir()
        manifest.symlink_to(saved)
        with self.assertRaises(SnapshotError):
            ep.verify(directory)
        alias = self.cache.parent / "alias"
        alias.symlink_to(self.cache, target_is_directory=True)
        self.downloader.reset_mock()
        with self.assertRaises(SnapshotError):
            ep.acquire(alias)
        self.downloader.assert_not_called()

    def invented_probe(self, directory):
        return {"status": "raw_object_inspected", "r_version": "4.6.1",
                "platform": "aarch64-unknown-linux-gnu",
                "container_sha256": ep.verify(directory)["files"]["ep_model.rda"]["sha256"],
                "object_name": "ep_model", "object_type": "raw", "raw_bytes": 100,
                "raw_sha256": "a" * 64, "prefix_hex": "a" * 32,
                "installed_package_equality_verified": False, "model_executed": False}

    def test_probe_is_optional_offline_readonly_unprivileged_and_not_prediction_capture(self):
        directory = self.acquire()
        result = subprocess.CompletedProcess([], 0, json.dumps(self.invented_probe(directory)), "")
        with patch.object(ep_probe.subprocess, "run", return_value=result) as run:
            receipt = ep_probe.inspect(directory)
        command = run.call_args.args[0]
        for option, value in (("--network", "none"), ("--pull", "never"), ("--user", "65534:65534"),
                              ("--cap-drop", "ALL"), ("--cpus", "1"), ("--memory", "512m")):
            self.assertEqual(command[command.index(option) + 1], value)
        self.assertIn("--read-only", command)
        mounts = [command[i + 1] for i, part in enumerate(command) if part == "--mount"]
        self.assertEqual(len(mounts), 2)
        self.assertTrue(all(m.endswith(",readonly") for m in mounts))
        self.assertNotIn("--privileged", command)
        self.assertNotIn("--publish", command)
        self.assertEqual(run.call_args.kwargs["timeout"], 45)
        self.assertIs(receipt["prediction_capture_available"], False)
        self.assertIs(receipt["predictive_validation"], False)

    def test_probe_validates_artifact_before_starting_docker(self):
        directory = self.acquire()
        (directory / "ep_model.rda").write_bytes(b"corrupt")
        with patch.object(ep_probe.subprocess, "run") as run:
            with self.assertRaises(SnapshotError):
                ep_probe.inspect(directory)
        run.assert_not_called()

    def test_wrong_probe_identity_missing_fields_and_false_success_claims_fail(self):
        directory = self.acquire()
        base = self.invented_probe(directory)
        for field, value in (("r_version", "4.5.0"), ("container_sha256", "f" * 64),
                             ("raw_bytes", True), ("raw_sha256", None), ("raw_sha256", "0" * 64),
                             ("prefix_hex", "invalid"), ("object_name", "wp_model"),
                             ("model_executed", True), ("installed_package_equality_verified", True)):
            probe = base | {field: value}
            with patch.object(ep_probe.subprocess, "run", return_value=
                              subprocess.CompletedProcess([], 0, json.dumps(probe), "")):
                with self.assertRaises(SnapshotError):
                    ep_probe.inspect(directory)
        for raw in ("invalid JSON", "[]", "null", json.dumps(base | {"extra": True}), "{}"):
            with patch.object(ep_probe.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, raw, "")):
                with self.assertRaises(SnapshotError):
                    ep_probe.inspect(directory)

    def test_timeout_cleans_only_the_owned_named_probe(self):
        directory = self.acquire()
        with patch.object(ep_probe.subprocess, "run", side_effect=[
            subprocess.TimeoutExpired("docker", 45), subprocess.CompletedProcess([], 0, "", "")
        ]) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                ep_probe.inspect(directory)
        command = run.call_args_list[0].args[0]
        name = command[command.index("--name") + 1]
        self.assertRegex(name, r"^nfl-ep-probe-[0-9a-f]{32}$")
        self.assertEqual(run.call_args_list[1].args[0], ["docker", "rm", "--force", name])

    def test_failed_cleanup_is_not_reported_as_a_clean_exit(self):
        directory = self.acquire()
        with patch.object(ep_probe.subprocess, "run", side_effect=[
            subprocess.TimeoutExpired("docker", 45), subprocess.CompletedProcess([], 1, "", "failed")
        ]):
            with self.assertRaisesRegex(SnapshotError, "unable to confirm cleanup"):
                ep_probe.inspect(directory)

    def test_runner_change_during_probe_is_rejected(self):
        directory = self.acquire()
        runner = self.cache / "runner.R"
        runner.write_text("synthetic original runner")
        def changed(*args, **kwargs):
            runner.write_text("synthetic changed runner")
            return subprocess.CompletedProcess([], 0, json.dumps(self.invented_probe(directory)), "")
        with patch.object(ep_probe, "RUNNER", runner), patch.object(ep_probe.subprocess, "run", side_effect=changed):
            with self.assertRaisesRegex(SnapshotError, "runner changed"):
                ep_probe.inspect(directory)

    def test_mount_option_injection_is_rejected_before_docker(self):
        directory = self.acquire()
        alias = self.cache / "with,comma"
        directory.rename(alias)
        with patch.object(ep_probe.subprocess, "run") as run:
            with self.assertRaisesRegex(SnapshotError, "mount path"):
                ep_probe.inspect(alias)
        run.assert_not_called()

    def test_manifest_change_during_probe_is_rejected(self):
        directory = self.acquire()
        probe = self.invented_probe(directory)
        def changed(*args, **kwargs):
            self.alter_manifest(directory, lambda m: m.update(retrieved_at_utc="2026-01-01T00:00:00Z"))
            return subprocess.CompletedProcess([], 0, json.dumps(probe), "")
        with patch.object(ep_probe.subprocess, "run", side_effect=changed):
            with self.assertRaisesRegex(SnapshotError, "manifest or runner changed"):
                ep_probe.inspect(directory)


class EPRecordedEvidenceTests(unittest.TestCase):
    """Offline receipt consistency, not re-execution/attestation of model bytes."""

    def test_inspection_is_bound_to_acquisition_and_runner_files(self):
        manifest_path = ROOT / "docs/evidence/ep-package-acquisition.json"
        manifest = json.loads(manifest_path.read_text())
        probe = json.loads((ROOT / "docs/evidence/ep-r-object-inspection.json").read_text())
        self.assertEqual(probe["acquisition_manifest_sha256"], sha256(manifest_path.read_bytes()).hexdigest())
        self.assertEqual(probe["runner_sha256"], sha256(ep_probe.RUNNER.read_bytes()).hexdigest())
        self.assertEqual(probe["probe_driver_sha256"], sha256(Path(ep_probe.__file__).read_bytes()).hexdigest())
        self.assertEqual(probe["image"], ep_probe.IMAGE)
        self.assertEqual(manifest["source"], ep._identity())
        self.assertIsNone(manifest["source"]["verified_training_window"])
        for name, (relative, blob, _) in ep.FILES.items():
            self.assertEqual(manifest["files"][name]["git_blob_sha1"], blob)
            self.assertEqual(manifest["files"][name]["url"], f"{ep.ROOT_URL}/{relative}")
        self.assertEqual(probe["inspection"]["container_sha256"], manifest["files"]["ep_model.rda"]["sha256"])

    def test_raw_container_archive_and_prediction_evidence_are_not_conflated(self):
        probe = json.loads((ROOT / "docs/evidence/ep-r-object-inspection.json").read_text())
        inspection = probe["inspection"]
        self.assertEqual((inspection["object_name"], inspection["object_type"]), ("ep_model", "raw"))
        self.assertEqual(inspection["raw_bytes"], 9737490)
        self.assertNotEqual(inspection["raw_sha256"], inspection["container_sha256"])
        audit = json.loads((ROOT / "docs/evidence/fastrmodels-2.1.0-interface-audit.json").read_text())
        self.assertNotEqual(inspection["raw_bytes"], audit["artifacts"][0]["archive"]["bytes"])
        self.assertIs(inspection["installed_package_equality_verified"], False)
        self.assertIs(inspection["model_executed"], False)
        self.assertIs(probe["prediction_capture_available"], False)
        self.assertIs(probe["predictive_validation"], False)
