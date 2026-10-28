"""Offline runner/mutation tests. Mock model bytes and outputs are NOT real evidence."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from validation import ep_r_capture as runner, ep_reference as protocol


class EPRCaptureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.artifact = self.root / "artifact"
        self.artifact.mkdir()
        for name in ("manifest.json", "LICENSE.md", "DESCRIPTION"):
            (self.artifact / name).write_bytes(b"synthetic unit-test artifact")
        self.raw = b"synthetic model, never executed"
        self.cache = self.root / "captures"
        self.environment = json.loads(runner.ENVIRONMENT.read_bytes())
        self.environment["runtime"]["raw_sha256"] = runner.digest(self.raw)
        self.environment["runtime"]["raw_bytes"] = len(self.raw)
        self.environment["acquisition_manifest_sha256"] = runner.digest(
            (self.artifact / "manifest.json").read_bytes())
        envfile = self.root / "environment.json"
        envfile.write_bytes(runner.encode(self.environment))
        for p in (patch.object(runner, "ENVIRONMENT", envfile),
                  patch.object(runner, "RAW_SHA256", runner.digest(self.raw)),
                  patch.object(runner, "RAW_BYTES", len(self.raw)),
                  patch.object(runner.ep_acquire, "verify", return_value={"files": {
                      "ep_model.rda": {"sha256": "e" * 64}}})):
            p.start()
            self.addCleanup(p.stop)

    def fake_execute(self, staged, artifact, payload, identity, environment):
        fixture, _ = protocol.load_fixture()
        rows = [{"id": c["id"], "features": c["features"],
                 "probabilities": [0.2, 0.1, 0.15, 0.05, 0.1, 0.05, 0.35], "ep": 1.1}
                for c in fixture["accepted"]]
        # This mocked runner intentionally impersonates the file contract only.
        # These probabilities/bytes must NEVER be published as actual model evidence.
        capture = {"protocol_version": 1, "probability_origin": "model_capture",
            "fixture_sha256": payload["fixture_sha256"], "source_commits": protocol.SOURCE_COMMITS,
            "model_sha256": runner.RAW_SHA256,
            "artifact_manifest_sha256": payload["artifact_manifest_sha256"],
            "runtime": {"language": "R", "version": environment["runtime"]["r_version"],
                        "xgboost_version": "3.4.2.1", "platform": environment["runtime"]["platform"],
                        "environment_sha256": identity["environment_sha256"],
                        "runner_sha256": identity["runner_sha256"]},
            "feature_order": list(protocol.FEATURES), "class_order": list(protocol.CLASSES),
            "batch": rows, "single": deepcopy(rows)}
        observation = {"status": "upstream_reference_captured", "traced_predictions": 26,
            "verified_raw_loads": 26, "untraced_batch_identical": True,
            "input_sha256": identity["input_sha256"], "model_sha256": runner.RAW_SHA256,
            "model_bytes": runner.RAW_BYTES, "installed_package_equality_verified": True,
            "xgboost_config": environment["runtime"]["xgboost_config"]}
        (staged / "ep_model.ubj").write_bytes(self.raw)
        for name, value in (("capture.json", capture), ("observation.json", observation),
                            ("runtime-check.json", environment["runtime"])):
            (staged / name).write_bytes(runner.encode(value))
        for name in ("runtime.log", "capture.log"):
            (staged / name).write_bytes(b"")

    def publish(self):
        with patch.object(runner, "execute", side_effect=self.fake_execute):
            return runner.capture(self.artifact, self.cache)

    def test_preflight_passes_only_full_accepted_states_not_oracle_vectors(self):
        payload, identity, environment = runner.inputs(self.artifact)
        fixture, fingerprint = protocol.load_fixture()
        self.assertEqual(len(payload["states"]), 25)
        self.assertEqual(payload["fixture_sha256"], fingerprint)
        for state, case in zip(payload["states"], fixture["accepted"]):
            self.assertEqual(set(state), {"id", "state"})
            self.assertEqual(state["state"], fixture["base_state"] | case["overrides"])
            self.assertEqual(set(state["state"]), protocol.STATE_KEYS)
        self.assertNotIn("features", runner.encode(payload).decode())
        self.assertNotIn("probabilities", runner.encode(payload).decode())
        self.assertEqual(identity["input_sha256"], runner.digest(runner.encode(payload)))
        self.assertEqual(environment, self.environment)

    def test_changed_environment_source_or_acquisition_fails_before_execution(self):
        for mutation in (lambda x: x["inputs"].update({"validation/ep_install.R": "f" * 64}),
                         lambda x: x["inputs"].update({"../escape": "f" * 64}),
                         lambda x: x.update(acquisition_manifest_sha256="f" * 64),
                         lambda x: x["runtime"].update(raw_sha256="f" * 64)):
            environment = deepcopy(self.environment)
            mutation(environment)
            runner.ENVIRONMENT.write_bytes(runner.encode(environment))
            with patch.object(runner, "execute") as execute:
                with self.assertRaises(protocol.ProtocolError):
                    runner.capture(self.artifact, self.cache)
                execute.assert_not_called()
            self.assertFalse(self.cache.exists())

    def test_no_clobber_cache_reuse_is_offline_and_preserves_exact_files(self):
        destination = self.publish()
        before = {p.name: p.read_bytes() for p in destination.iterdir()}
        with patch.object(runner, "execute") as execute:
            self.assertEqual(runner.capture(self.artifact, self.cache), destination)
            execute.assert_not_called()
        self.assertEqual(before, {p.name: p.read_bytes() for p in destination.iterdir()})
        manifest = runner.verify(destination, self.artifact)
        self.assertFalse(manifest["validation"]["python_parity"])
        self.assertFalse(manifest["validation"]["predictive_validation"])
        self.assertFalse(manifest["validation"]["artifact_bytes_attested"])

    def test_corrupt_cache_and_extra_files_are_never_repaired(self):
        destination = self.publish()
        (destination / "ep_model.ubj").write_bytes(b"preserve corrupt bytes")
        with patch.object(runner, "execute") as execute:
            with self.assertRaises(protocol.ProtocolError):
                runner.capture(self.artifact, self.cache)
            execute.assert_not_called()
        self.assertEqual((destination / "ep_model.ubj").read_bytes(), b"preserve corrupt bytes")
        (destination / "extra").write_bytes(b"unrelated")
        with self.assertRaisesRegex(protocol.ProtocolError, "inventory"):
            runner.verify(destination, self.artifact)

    def test_manifest_drift_is_not_accepted_as_success(self):
        destination = self.publish()
        path = destination / "manifest.json"
        original = json.loads(path.read_bytes())
        for mutation in (lambda x: x.update(schema_version=True),
                         lambda x: x["identity"].update(runner_sha256="f" * 64),
                         lambda x: x["validation"].update(python_parity=True),
                         lambda x: x["files"].pop("LICENSE.md"),
                         lambda x: x["files"]["capture.log"].update(sha256="f" * 64)):
            manifest = deepcopy(original)
            mutation(manifest)
            path.write_bytes(runner.encode(manifest))
            with self.assertRaises(protocol.ProtocolError):
                runner.verify(destination, self.artifact)

    def test_reference_validator_does_not_claim_cross_runtime_parity(self):
        destination = self.publish()
        result = protocol.validate_reference(json.loads((destination / "capture.json").read_bytes()))
        self.assertEqual(result["status"], "reference_capture_protocol_pass")
        self.assertEqual(result["cases"], 25)
        self.assertFalse(result["python_parity"])

    def test_capture_numeric_feature_order_identity_and_observation_drift_fail(self):
        destination = self.publish()
        payload, identity, environment = runner.inputs(self.artifact)
        path = destination / "capture.json"
        original = json.loads(path.read_bytes())
        for mutation in (lambda x: x.update(probability_origin="synthetic_test"),
                         lambda x: x["runtime"].update(runner_sha256="f" * 64),
                         lambda x: x.update(artifact_manifest_sha256="f" * 64),
                         lambda x: x["feature_order"].reverse(),
                         lambda x: x["class_order"].reverse(),
                         lambda x: x["batch"][0]["features"].__setitem__(0, 900),
                         lambda x: x["single"][0].update(ep=0),
                         lambda x: x["batch"][0]["probabilities"].__setitem__(0, 0.9)):
            changed = deepcopy(original)
            mutation(changed)
            path.write_bytes(runner.encode(changed))
            with self.assertRaises(protocol.ProtocolError):
                runner.validate_outputs(destination, payload, identity, environment)
        path.write_bytes(runner.encode(original))
        path = destination / "observation.json"
        original = json.loads(path.read_bytes())
        for key, value in (("verified_raw_loads", 25), ("traced_predictions", 25),
                           ("untraced_batch_identical", False), ("input_sha256", "f" * 64)):
            path.write_bytes(runner.encode(original | {key: value}))
            with self.assertRaisesRegex(protocol.ProtocolError, "observation"):
                runner.validate_outputs(destination, payload, identity, environment)

    def test_raw_export_input_and_runtime_are_checked_independently_of_manifest(self):
        destination = self.publish()
        context = runner.inputs(self.artifact)
        for name, raw in (("ep_model.ubj", b"wrong"), ("input.json", b"{}"),
                          ("runtime-check.json", b"{}")):
            path = destination / name
            before = path.read_bytes()
            path.write_bytes(raw)
            with self.assertRaises(protocol.ProtocolError):
                runner.validate_outputs(destination, *context)
            path.write_bytes(before)

    def test_failure_retains_partial_logs_and_never_publishes(self):
        def fail(staged, *args):
            (staged / "capture.log").write_bytes(b"synthetic failure")
            raise subprocess.CalledProcessError(1, ["fake-runner"])
        with patch.object(runner, "execute", side_effect=fail):
            with self.assertRaisesRegex(protocol.ProtocolError, "staging/logs retained"):
                runner.capture(self.artifact, self.cache)
        pending = list(self.cache.iterdir())
        self.assertEqual(len(pending), 1)
        self.assertTrue(pending[0].name.startswith(".pending-"))
        self.assertEqual((pending[0] / "capture.log").read_bytes(), b"synthetic failure")
        self.assertFalse((pending[0] / "manifest.json").exists())

    def test_lock_and_existing_destination_prevent_concurrent_overwrite(self):
        self.cache.mkdir()
        (self.cache / ".capture.lock").write_text("another run")
        with patch.object(runner, "execute") as execute:
            with self.assertRaises(FileExistsError):
                runner.capture(self.artifact, self.cache)
            execute.assert_not_called()
        self.assertEqual((self.cache / ".capture.lock").read_text(), "another run")

    def test_destination_appearing_during_execution_is_preserved(self):
        _, identity, _ = runner.inputs(self.artifact)
        destination = self.cache / ("r-" + runner.digest(runner.encode(identity)))
        def concurrent(staged, *args):
            self.fake_execute(staged, *args)
            destination.mkdir()
            (destination / "user-file").write_text("preserve me")
        with patch.object(runner, "execute", side_effect=concurrent):
            with self.assertRaisesRegex(protocol.ProtocolError, "destination appeared"):
                runner.capture(self.artifact, self.cache)
        self.assertEqual((destination / "user-file").read_text(), "preserve me")

    def test_invalid_or_naive_timestamp_is_not_a_valid_receipt(self):
        destination = self.publish()
        path = destination / "manifest.json"
        original = json.loads(path.read_bytes())
        for timestamp in (None, "invalid", "2026-10-28T12:00:00", "2026-10-28T12:00:00+01:00"):
            path.write_bytes(runner.encode(original | {"captured_at_utc": timestamp}))
            with self.assertRaises(protocol.ProtocolError):
                runner.verify(destination, self.artifact)

    def test_symlink_paths_and_oversized_files_are_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(protocol.ProtocolError):
            runner.capture(self.artifact, alias / "cache")
        path = self.root / "large"
        path.write_bytes(b"12345")
        with self.assertRaises(protocol.ProtocolError):
            runner.read(path, 4)
        with self.assertRaises(protocol.ProtocolError):
            runner.read(alias / "large")

    def test_input_drift_during_run_is_not_published(self):
        original = runner.inputs(self.artifact)
        changed = deepcopy(original)
        changed[1]["runner_sha256"] = "f" * 64
        with patch.object(runner, "inputs", side_effect=[original, changed]), \
                patch.object(runner, "execute", side_effect=self.fake_execute):
            with self.assertRaisesRegex(protocol.ProtocolError, "inputs changed"):
                runner.capture(self.artifact, self.cache)
        self.assertFalse(list(self.cache.glob("r-*")))

    def test_docker_command_disables_network_privilege_pulls_and_bounds_resources(self):
        command = runner.docker_command("sha256:test", "unique-test", [
            (self.artifact, "/artifact", False), (self.cache, "/output", True)])
        for option, value in (("--network", "none"), ("--pull", "never"), ("--cpus", "1"),
                              ("--memory", "768m"), ("--pids-limit", "64"),
                              ("--user", "65534:65534"), ("--cap-drop", "ALL")):
            self.assertEqual(command[command.index(option) + 1], value)
        self.assertIn("--read-only", command)
        self.assertIn(f"type=bind,src={self.artifact},dst=/artifact,readonly", command)
        self.assertIn(f"type=bind,src={self.cache},dst=/output", command)
        self.assertNotIn("/var/run/docker.sock", " ".join(command))
        with self.assertRaises(protocol.ProtocolError):
            runner.docker_command("image", "name", [(Path("/bad,path"), "/in", False)])

    def test_timeout_removes_only_owned_container_and_retains_logs(self):
        out, err = self.root / "out", self.root / "err"
        with patch.object(runner.subprocess, "run", side_effect=[
                subprocess.TimeoutExpired(["docker"], 60), subprocess.CompletedProcess([], 0)]) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                runner.run_container(["docker", "run"], "ep-capture-owned", out, err)
        self.assertEqual(run.call_args_list[0].kwargs["timeout"], 60)
        self.assertEqual(run.call_args_list[1].args[0], ["docker", "rm", "-f", "ep-capture-owned"])
        self.assertTrue(out.exists() and err.exists())

    def test_missing_image_does_not_execute_or_download(self):
        payload, identity, environment = runner.inputs(self.artifact)
        with patch.object(runner.subprocess, "run", side_effect=subprocess.CalledProcessError(1, [])), \
                patch.object(runner, "run_container") as run:
            with self.assertRaises(subprocess.CalledProcessError):
                runner.execute(self.root, self.artifact, payload, identity, environment)
            run.assert_not_called()

    def test_runtime_drift_stops_before_inference(self):
        payload, identity, environment = runner.inputs(self.artifact)
        def audit(command, name, stdout, stderr):
            stdout.write_bytes(b"{}")
            stderr.write_bytes(b"")
        inspected = subprocess.CompletedProcess([], 0, stdout=f"{identity['image_id']} linux/arm64\n")
        with patch.object(runner.subprocess, "run", return_value=inspected), \
                patch.object(runner, "run_container", side_effect=audit) as run:
            with self.assertRaisesRegex(protocol.ProtocolError, "installed runtime differs"):
                runner.execute(self.root, self.artifact, payload, identity, environment)
            self.assertEqual(run.call_count, 1)


class CommittedRReferenceTests(unittest.TestCase):
    """Integrity checks on recorded real R outputs, without rerunning a model in CI."""

    def setUp(self):
        self.directory = runner.ROOT / "docs/evidence"
        self.raw = (self.directory / "ep-r-reference-capture.json").read_bytes()
        self.capture = json.loads(self.raw)
        self.manifest = json.loads((self.directory / "ep-r-reference-manifest.json").read_bytes())

    def test_recorded_capture_matches_protocol_and_prepublished_corpus(self):
        result = protocol.validate_reference(self.capture)
        self.assertEqual(result, self.manifest["validation"])
        self.assertEqual(self.capture["probability_origin"], "model_capture")
        self.assertEqual(self.capture["batch"], self.capture["single"])
        self.assertFalse(result["python_parity"])
        self.assertFalse(result["predictive_validation"])

    def test_capture_binds_actual_runner_protocol_environment_and_payload(self):
        identity = self.manifest["identity"]
        for key, path in (("driver_sha256", Path(runner.__file__)),
                          ("runner_sha256", runner.RUNNER),
                          ("protocol_sha256", Path(protocol.__file__)),
                          ("environment_sha256", runner.ENVIRONMENT)):
            self.assertEqual(identity[key], runner.digest(path.read_bytes()))
        self.assertEqual(self.manifest["files"]["capture.json"],
                         {"sha256": runner.digest(self.raw), "size_bytes": len(self.raw)})
        self.assertEqual(self.manifest["files"]["ep_model.ubj"],
                         {"sha256": runner.RAW_SHA256, "size_bytes": runner.RAW_BYTES})
        self.assertEqual(self.capture["runtime"]["runner_sha256"], identity["runner_sha256"])
        self.assertEqual(self.capture["runtime"]["environment_sha256"], identity["environment_sha256"])

    def test_capture_is_not_accidentally_replaced_with_the_comparator_stub(self):
        # These checks catch accidental fixture substitution, not forged evidence.
        probabilities = [tuple(row["probabilities"]) for row in self.capture["batch"]]
        self.assertGreater(len(set(probabilities)), 10)
        self.assertTrue(any(row["ep"] < 0 for row in self.capture["batch"]))
        self.assertTrue(any(row["ep"] > 0 for row in self.capture["batch"]))
        self.assertNotIn((0.2, 0.1, 0.15, 0.05, 0.1, 0.05, 0.35), probabilities)
        raw = (self.directory / "ep-r-reference-observation.json").read_bytes()
        self.assertEqual(self.manifest["files"]["observation.json"],
                         {"sha256": runner.digest(raw), "size_bytes": len(raw)})
        observation = json.loads(raw)
        self.assertEqual(observation["traced_predictions"], 26)
        self.assertEqual(observation["verified_raw_loads"], 26)
        self.assertIs(observation["untraced_batch_identical"], True)


if __name__ == "__main__":
    unittest.main()
