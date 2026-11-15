"""Local launcher lifecycle and real proxy contracts; no external football data."""

import builtins
import csv
import importlib.util
import json
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.request import ProxyHandler, build_opener

from tests_api.synthetic_snapshot import write_snapshot


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("start_local", ROOT / "scripts/start_local.py")
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)
LABEL = 'SYNTHETIC local launcher fixture; invented plays and acquisition metadata'
HTTP = build_opener(ProxyHandler({}))


class LocalStartupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="nfl local start-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        with (ROOT / "tests/fixtures/synthetic_pbp.csv").open(newline="") as stream:
            rows = [row for row in csv.DictReader(stream) if row["season"] == "2024"]
        self.snapshot = write_snapshot(self.directory, rows, list(rows[0]))
        # Fail visibly instead of reusing/killing a reviewer's existing services.
        launcher.preflight(self.snapshot, LABEL)
        self.args = ["--snapshot", str(self.snapshot), "--source-label", LABEL]

    def assert_ports_free(self):
        launcher.preflight(self.snapshot, LABEL)

    def test_actual_api_viewer_requests_and_sigint_cleanup(self):
        before = {p.name: p.read_bytes() for p in self.snapshot.iterdir()}
        with (self.directory / "launcher.log").open("w+") as output:
            process = subprocess.Popen([sys.executable, str(ROOT / "scripts/start_local.py"), *self.args],
                                       cwd=self.directory, stdout=output, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 45
                while True:
                    output.seek(0)
                    log = output.read()
                    if "Ready: http://127.0.0.1:5173/" in log:
                        break
                    self.assertIsNone(process.poll(), log)
                    self.assertLess(time.monotonic(), deadline, log)
                    time.sleep(0.1)
                with HTTP.open("http://127.0.0.1:5173/", timeout=5) as response:
                    self.assertIn(b'<div id="root">', response.read())
                paths = (
                    "/api/v1/report?team=CAR&season=2024&before_week=3",
                    "/api/v1/decision?team=CAR&season=2024&before_week=3&down=1&distance_min=0&distance_max=100",
                )
                documents = []
                for path in paths:
                    with HTTP.open("http://127.0.0.1:5173" + path, timeout=5) as response:
                        document = json.load(response)
                    self.assertEqual(document["source"]["label"], LABEL)
                    documents.append(document)
                self.assertEqual(documents[0]["overall"]["plays"], 6)
                self.assertAlmostEqual(documents[0]["overall"]["epa_per_play"], 0.04)
                decision = documents[1]
                self.assertEqual(decision["contract_version"], 1)
                self.assertEqual(decision["population"], {"plays": 3, "games": 2})
                run, passed = decision["candidates"]
                self.assertEqual((run["candidate"], run["plays"], run["epa_per_play"]), ("run", 1, 0.0))
                self.assertEqual((passed["candidate"], passed["plays"]), ("pass", 2))
                self.assertAlmostEqual(passed["epa_per_play"], 0.6)
                self.assertIsNone(decision["comparison"]["preferred_candidate"])
                process.send_signal(signal.SIGINT)
                self.assertEqual(process.wait(timeout=12), 0)
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=12)
        self.assert_ports_free()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.snapshot.iterdir()})

    def test_missing_snapshot_and_invalid_labels_start_nothing(self):
        for args in (
            ["--snapshot", str(self.directory / "missing"), "--source-label", LABEL],
            [*self.args[:-1], " "], [*self.args[:-1], "a" * 301],
        ):
            with self.subTest(args=args), patch.object(launcher.subprocess, "Popen") as spawn:
                self.assertEqual(launcher.main(args), 1)
                spawn.assert_not_called()
        self.assert_ports_free()

    def test_missing_dependencies_start_nothing(self):
        with patch.object(launcher.importlib.util, "find_spec", return_value=None), \
                patch.object(launcher.subprocess, "Popen") as spawn:
            self.assertEqual(launcher.main(self.args), 1)
            spawn.assert_not_called()

    def test_occupied_port_is_left_untouched(self):
        for port in launcher.PORTS:
            with self.subTest(port=port), socket.socket() as owner:
                owner.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                owner.bind(("127.0.0.1", port))
                owner.listen()
                with patch.object(launcher, "wait_ready") as ready:
                    self.assertEqual(launcher.main(self.args), 1)
                    ready.assert_not_called()
                self.assertEqual(owner.getsockname(), ("127.0.0.1", port))
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    connection, _ = owner.accept()
                    connection.close()

    def test_corrupt_snapshot_fails_without_ready_or_live_services(self):
        (self.snapshot / "manifest.json").write_text("{}")
        result = subprocess.run([sys.executable, str(ROOT / "scripts/start_local.py"), *self.args],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Ready: ", result.stdout)
        self.assertIn("API exited", result.stderr)
        self.assert_ports_free()

    def test_viewer_start_failure_cleans_already_running_api(self):
        real_spawn = subprocess.Popen
        children = []

        def spawn(command, **options):
            if command[0] != sys.executable:
                command = [sys.executable, "-c", "raise SystemExit(7)"]
            child = real_spawn(command, **options)
            children.append(child)
            return child

        with patch.object(launcher.subprocess, "Popen", side_effect=spawn):
            # preflight uses subprocess.run too; run it before intercepting Popen.
            with patch.object(launcher, "preflight", return_value=("node", ROOT / "web/node_modules/vite/bin/vite.js")):
                self.assertEqual(launcher.main(self.args), 1)
        self.assertEqual(len(children), 2)
        self.assertTrue(all(child.poll() is not None for child in children))
        self.assert_ports_free()


    def test_unsupported_node_version_starts_nothing(self):
        for version in ("v23.0.0", "v24.14.9", "v25.0.0", "unparseable"):
            with self.subTest(version=version), patch.object(launcher.subprocess, "run") as probe:
                probe.return_value.stdout = version
                with self.assertRaisesRegex(launcher.StartupError, "Unsupported Node"):
                    launcher.preflight(self.snapshot, LABEL)

    def test_service_exit_after_ready_stops_the_other_service(self):
        ready = launcher.wait_ready
        children = []

        def fail_after_ready(url, owned, stopping):
            ready(url, owned, stopping)
            if len(owned) == 2:
                children.extend(owned)
                owned[0][1].terminate()
                owned[0][1].wait(timeout=5)

        with patch.object(launcher, "wait_ready", side_effect=fail_after_ready):
            self.assertEqual(launcher.main(self.args), 1)
        self.assertEqual(len(children), 2)
        self.assertTrue(all(child.poll() is not None for _, child in children))
        self.assert_ports_free()

    def test_cleanup_forces_an_unresponsive_owned_process_to_exit(self):
        ready = self.directory / "stubborn-ready"
        program = ("import signal, time; from pathlib import Path; "
                   "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                   "Path(__import__('sys').argv[1]).touch(); time.sleep(60)")
        child = subprocess.Popen([sys.executable, "-c", program, str(ready)], start_new_session=True)
        try:
            deadline = time.monotonic() + 5
            while not ready.exists():
                self.assertIsNone(child.poll())
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.05)
            with patch.object(launcher, "STOP_SECONDS", 0.2):
                launcher.stop_children([("stubborn fixture", child)])
            self.assertEqual(child.returncode, -signal.SIGKILL)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait()

    def test_startup_timeout_cleans_process_even_when_shutdown_output_is_closed(self):
        real_spawn = subprocess.Popen
        children = []

        def spawn(command, **options):
            child = real_spawn([sys.executable, "-c", "import time; time.sleep(60)"], **options)
            children.append(child)
            return child

        def broken_shutdown_output(message, **options):
            if message.startswith("Stopping"):
                raise BrokenPipeError("output reader closed")
            builtins.print(message, **options)

        with patch.object(launcher, "preflight", return_value=("node", Path("unused"))), \
                patch.object(launcher.subprocess, "Popen", side_effect=spawn), \
                patch.object(launcher, "print", side_effect=broken_shutdown_output, create=True), \
                patch.object(launcher, "STARTUP_SECONDS", 0.2):
            self.assertEqual(launcher.main(self.args), 1)
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].poll())
        self.assert_ports_free()


if __name__ == "__main__":
    unittest.main()
