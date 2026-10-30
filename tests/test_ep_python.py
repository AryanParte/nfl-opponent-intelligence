"""Offline tests; fabricated wheel/prediction fixtures are never model evidence."""

import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from opponent_intelligence.snapshots import SnapshotError
from validation import ep_python_candidate as candidate, ep_python_setup as setup
from validation import ep_python_environment as environment, ep_python_capture as driver
from validation import ep_reference as protocol, ep_r_capture as reference


class EPCandidateTests(unittest.TestCase):
    def test_independent_encoder_matches_all_predeclared_cases(self):
        fixture, _ = protocol.load_fixture()
        for case in fixture["accepted"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(candidate.encode_state(fixture["base_state"] | case["overrides"]), case["features"])
        self.assertEqual(candidate.FEATURES, protocol.FEATURES)
        self.assertEqual(candidate.CLASSES, protocol.CLASSES)

    def test_all_rejected_protocol_cases_fail_closed(self):
        fixture, _ = protocol.load_fixture()
        for case in fixture["rejected"]:
            with self.subTest(case=case["id"]), self.assertRaises(ValueError):
                candidate.encode_state(fixture["base_state"] | case["overrides"])

    def test_missing_extra_coerced_nonfinite_and_contradictory_values(self):
        fixture, _ = protocol.load_fixture()
        base = fixture["base_state"]
        for key in base:
            missing = dict(base)
            del missing[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                candidate.encode_state(missing)
        invalid = [{"extra": 1}, {"home_team": "CAR", "away_team": "CAR"}, {"roof": []}]
        for key in ("season", "qtr", "quarter_seconds_remaining", "down", "ydstogo",
                    "posteam_timeouts_remaining", "defteam_timeouts_remaining"):
            invalid.extend({key: value} for value in (None, True, 1.0, "1", -1, 10000))
        invalid.extend({"yardline_100": v} for v in (True, None, float("nan"), float("inf"), -float("inf"), 10**500))
        invalid.extend({key: value} for key in ("home_team", "away_team", "posteam") for value in ([], None, "car", "C", "CARS"))
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                candidate.encode_state(base | values)

    def test_candidate_has_no_oracle_or_reference_imports(self):
        tree = ast.parse(Path(candidate.__file__).read_text())
        allowed = {"argparse", "hashlib", "json", "math", "pathlib", "platform", "re", "numpy", "xgboost"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name.split(".")[0] in allowed for alias in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertIn(node.module.split(".")[0], allowed)
        self.assertNotIn("features", protocol.load_fixture()[0]["base_state"])

    def test_signed_ep_and_probability_failures(self):
        values = [0.2, 0.1, 0.15, 0.05, 0.1, 0.05, 0.35]
        self.assertAlmostEqual(candidate.rows(["synthetic"], [[0] * 18], [values])[0]["ep"], 1.1)
        for probabilities in ([1], [0] * 7, [float("nan")] * 7, [True] * 7, [-1, 2, 0, 0, 0, 0, 0]):
            with self.assertRaises(ValueError):
                candidate.rows(["synthetic"], [[0] * 18], [probabilities])
        with self.assertRaisesRegex(ValueError, "row count"):
            candidate.rows(["synthetic"], [], [values])

    def test_capture_serialization_does_not_round_probabilities(self):
        result = {"protocol_version": 1, "batch": [{"probabilities": [0.12345678901234567]}],
                  "single": [{"probabilities": [0.12345678901234567]}]}
        self.assertEqual(json.loads(candidate.serialize_capture(result)), result)
        self.assertEqual(candidate.serialize_capture(result), candidate.serialize_capture(result))

    def test_read_rejects_oversize_and_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            path = root / "payload"
            path.write_bytes(b"123")
            self.assertEqual(candidate.read(path, 3), b"123")
            with self.assertRaises(ValueError):
                candidate.read(path, 2)
            alias = root / "alias"
            alias.symlink_to(path)
            with self.assertRaises(ValueError):
                candidate.read(alias, 3)


class EPWheelTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.path = self.root / "example-1-py3-none-any.whl"

    def make_wheel(self, extra=None, metadata=b"Name: example\nVersion: 1\n"):
        with zipfile.ZipFile(self.path, "w") as wheel:
            wheel.writestr("example-1.dist-info/METADATA", metadata)
            wheel.writestr("example-1.dist-info/licenses/LICENSE", "Synthetic test notice, not a real license")
            if extra is not None:
                wheel.writestr(extra, "synthetic")
        return {"name": "example", "version": "1", "filename": self.path.name,
                "size_bytes": self.path.stat().st_size, "sha256": sha256(self.path.read_bytes()).hexdigest(),
                "url": "https://example.invalid/synthetic.whl"}

    def test_real_lock_and_install_requirements_agree(self):
        lock = setup.load_lock()
        requirements = (setup.LOCK.parent / "ep_python_requirements.txt").read_text()
        self.assertEqual(len(lock["wheels"]), 7)
        for record in lock["wheels"]:
            self.assertIn(f"{record['name']}=={record['version']} --hash=sha256:{record['sha256']}", requirements)
            self.assertTrue(record["notice_hashes"])

    def test_lock_rejects_identity_transport_and_terms_drift(self):
        original = setup.LOCK.read_bytes()
        invalid = [lambda x: x.update(schema_version=True), lambda x: x.update(python_version="3.14"),
                   lambda x: x.update(source_sha256="a" * 64), lambda x: x["wheels"].append(x["wheels"][0]),
                   lambda x: x["wheels"][0].update(filename="../escape.whl"),
                   lambda x: x["wheels"][0].update(version="latest"),
                   lambda x: x["wheels"][0].update(url="https://evil.invalid/file.whl"),
                   lambda x: x["wheels"][0].update(size_bytes=True),
                   lambda x: x["wheels"][0].update(sha256="bad"),
                   lambda x: x["wheels"][0].update(notice_hashes={}),
                   lambda x: x["wheels"][0].update(license_review="")]
        lock_path = self.root / "lock.json"
        for mutate in invalid:
            lock = json.loads(original)
            mutate(lock)
            lock_path.write_text(json.dumps(lock))
            with patch.object(setup, "LOCK", lock_path), self.assertRaises(SnapshotError):
                setup.load_lock()

    def test_wheel_hash_metadata_and_notices_are_verified(self):
        record = self.make_wheel()
        audit = setup.verify_wheel(self.path, record)
        record["notice_hashes"] = audit["notice_hashes"]
        self.assertEqual(setup.verify_wheel(self.path, record), audit)
        for field, value in (("sha256", "0" * 64), ("size_bytes", 0), ("name", "wrong"),
                             ("version", "2"), ("notice_hashes", {"wrong": "0" * 64})):
            with self.assertRaises(SnapshotError):
                setup.verify_wheel(self.path, record | {field: value})

    def test_unsafe_wheel_members_rejected(self):
        for member in ("../escape", "/absolute", "a\\escape"):
            with self.subTest(member=member), self.assertRaises(SnapshotError):
                setup.verify_wheel(self.path, self.make_wheel(member))
        symlink = zipfile.ZipInfo("link")
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.assertRaises(SnapshotError):
            setup.verify_wheel(self.path, self.make_wheel(symlink))

    def test_bounded_acquisition_offline_reuse_and_corrupt_no_clobber(self):
        record = self.make_wheel()
        raw = self.path.read_bytes()
        cache = self.root / "cache"
        def download(url, path, limit, timeout, attempts):
            self.assertEqual((url, limit, timeout, attempts), (record["url"], len(raw), 30, 3))
            path.write_bytes(raw)
        with patch.object(setup, "_download", side_effect=download) as transport:
            destination = setup.acquire(record, cache)
            self.assertEqual(setup.acquire(record, cache), destination)
        self.assertEqual(transport.call_count, 1)
        destination.write_bytes(b"preserve corrupt cache")
        with patch.object(setup, "_download") as transport, self.assertRaises(SnapshotError):
            setup.acquire(record, cache)
        transport.assert_not_called()
        self.assertEqual(destination.read_bytes(), b"preserve corrupt cache")

    def test_symlink_cache_and_failed_download_never_publish(self):
        record = self.make_wheel()
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(SnapshotError):
            setup.acquire(record, alias)
        cache = self.root / "cache"
        with patch.object(setup, "_download", side_effect=TimeoutError), self.assertRaises(TimeoutError):
            setup.acquire(record, cache)
        self.assertEqual(list(cache.iterdir()), [])


class EPDriverTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def test_command_is_offline_bounded_to_output_and_has_no_reference_predictions(self):
        command = driver.command(self.root / "reference", self.root / "environment.json", self.root / "output")
        self.assertEqual(command[:2], ["/usr/bin/sandbox-exec", "-p"])
        for restriction in ("(deny network*)", "(deny file-write*)", '(literal "/dev/null")'):
            self.assertIn(restriction, command[2])
        self.assertIn(str(self.root / "reference/input.json"), command)
        self.assertNotIn(str(self.root / "reference/capture.json"), command)
        self.assertNotIn(str(protocol.FIXTURE), command)

    def test_subprocess_limits_and_failure_logs_are_preserved(self):
        with patch.dict(driver.os.environ, {"PYTHONPATH": "bad", "DYLD_INSERT_LIBRARIES": "bad"}), \
                patch.object(driver.subprocess, "run", side_effect=subprocess.TimeoutExpired("synthetic", 60)) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                driver.execute(["synthetic-never-executed"], self.root)
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs["timeout"], 60)
        self.assertTrue(kwargs["check"])
        self.assertNotIn("PYTHONPATH", kwargs["env"])
        self.assertNotIn("DYLD_INSERT_LIBRARIES", kwargs["env"])
        self.assertEqual(kwargs["env"]["OMP_NUM_THREADS"], "1")
        self.assertTrue((self.root / "stderr.log").is_file())
        with patch.object(driver.resource, "setrlimit") as set_limit:
            kwargs["preexec_fn"]()
        self.assertEqual(set_limit.call_args_list[0].args, (driver.resource.RLIMIT_CPU, (45, 45)))
        self.assertEqual(set_limit.call_args_list[1].args, (driver.resource.RLIMIT_FSIZE, (1048576, 1048576)))

    def test_runtime_drift_rejected_without_inference(self):
        lock = setup.load_lock()
        receipt = {"schema_version": 1, "dependency_lock_sha256": environment.digest_file(setup.LOCK),
                   "source_archive_sha256": lock["source_sha256"], "source_commit": lock["source_commit"],
                   "packages": {"synthetic": "1"}}
        path = self.root / "environment.json"
        path.write_text(json.dumps(receipt))
        with patch.object(environment, "inspect_runtime", return_value={"packages": {"synthetic": "1"}}):
            self.assertEqual(environment.verify_environment(path), receipt)
        with patch.object(environment, "inspect_runtime", return_value={"packages": {"synthetic": "2"}}), \
                self.assertRaisesRegex(SnapshotError, "runtime drift"):
            environment.verify_environment(path)

    def test_preflight_failure_prevents_execution_and_directory_creation(self):
        cache = self.root / "new-captures"
        with patch.object(reference, "verify", side_effect=ValueError("reference drift")), \
                patch.object(driver, "execute") as execute, self.assertRaisesRegex(ValueError, "reference drift"):
            driver.capture(cache=cache)
        execute.assert_not_called()
        self.assertFalse(cache.exists())


class EPCommittedEvidenceTests(unittest.TestCase):
    """Replay real committed text receipts, not fresh native execution in CI."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        evidence = driver.ROOT / "docs/evidence"
        self.reference = self.root / "reference"
        self.reference.mkdir()
        for name, source in (("manifest.json", "ep-r-reference-manifest.json"),
                             ("capture.json", "ep-r-reference-capture.json")):
            (self.reference / name).write_bytes((evidence / source).read_bytes())
        self.output = self.root / "python"
        self.output.mkdir()
        for name in ("capture", "environment", "manifest"):
            (self.output / f"{name}.json").write_bytes((evidence / f"ep-python-{name}.json").read_bytes())
        for name in ("stdout.log", "stderr.log"):
            (self.output / name).write_bytes(b"")
        # Binary/environment attestation is a separate explicit local command.
        verification = patch.object(reference, "verify")
        verification.start()
        self.addCleanup(verification.stop)

    def verify(self):
        return driver.verify(self.output, self.reference)

    def test_committed_actual_capture_replays_without_optional_dependencies(self):
        manifest = self.verify()
        self.assertEqual(manifest["comparison"]["cases"], 25)
        self.assertEqual(manifest["comparison"]["probability_origin"], "model_capture")
        self.assertFalse(manifest["comparison"]["predictive_validation"])
        self.assertFalse(manifest["comparison"]["artifact_bytes_attested"])
        observed = json.loads((self.output / "capture.json").read_bytes())
        self.assertEqual(observed["batch"], observed["single"])

    def test_changed_capture_bytes_rejected_and_not_repaired(self):
        path = self.output / "capture.json"
        path.write_bytes(b"corrupt; preserve")
        with self.assertRaisesRegex(ValueError, "bytes differ"):
            self.verify()
        self.assertEqual(path.read_bytes(), b"corrupt; preserve")

    def test_manifest_mutations_rejected(self):
        path = self.output / "manifest.json"
        original = json.loads(path.read_bytes())
        mutations = (lambda x: x.update(schema_version=True), lambda x: x.update(captured_at_utc="2026-10-29T12:00:00"),
                     lambda x: x.update(driver_sha256="0" * 64), lambda x: x.update(reference_manifest_sha256="0" * 64),
                     lambda x: x["comparison"].update(predictive_validation=True),
                     lambda x: x["execution"].update(network="allowed"), lambda x: x["files"].update(extra={}))
        for mutate in mutations:
            changed = deepcopy(original)
            mutate(changed)
            path.write_text(json.dumps(changed))
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.verify()

    def test_rehashed_semantically_wrong_capture_rejected(self):
        capture_path = self.output / "capture.json"
        manifest_path = self.output / "manifest.json"
        original = json.loads(capture_path.read_bytes())
        manifest = json.loads(manifest_path.read_bytes())
        mutations = (lambda x: x["runtime"].update(version="3.14.0"),
                     lambda x: x["runtime"].update(runner_sha256="0" * 64),
                     lambda x: x["class_order"].reverse(), lambda x: x["batch"][0]["features"].reverse(),
                     lambda x: x["batch"][0].update(ep=7))
        for mutate in mutations:
            changed = deepcopy(original)
            mutate(changed)
            raw = reference.encode(changed)
            capture_path.write_bytes(raw)
            manifest["files"]["capture.json"] = {"sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)}
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                self.verify()

    def test_extra_file_and_symlink_are_rejected(self):
        extra = self.output / "unexpected"
        extra.write_bytes(b"preserve")
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.verify()
        extra.unlink()
        path = self.output / "capture.json"
        target = self.root / "outside.json"
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.verify()


if __name__ == "__main__":
    unittest.main()
