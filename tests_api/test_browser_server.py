"""Lifecycle and safety checks for the synthetic live-browser harness."""

import asyncio
import os
import socket
import unittest
from unittest.mock import patch

from opponent_intelligence.ingestion import load_snapshot
from opponent_intelligence.report import build_report
from tests_api import browser_server


class BrowserServerTests(unittest.TestCase):
    def exercise_server(self, *, fail):
        directories = []
        real_create_app = browser_server.create_app

        def capture(snapshot, **kwargs):
            directories.append(snapshot)
            self.assertIn("SYNTHETIC", kwargs["source_label"])
            dataset = load_snapshot(snapshot)
            report = build_report(dataset, team="CAR", season=2024, before_week=3,
                                  yardline_max=20, score_min=-7, score_max=0,
                                  period="Q4", clock_max=120, source_label=kwargs["source_label"])
            self.assertEqual(report["overall"]["plays"], 3)
            self.assertEqual(report["overall"]["epa_observations"], 2)
            self.assertAlmostEqual(report["overall"]["epa_per_play"], 0.2)
            return real_create_app(snapshot=snapshot, **kwargs)

        def run(_app, **kwargs):
            self.assertEqual(kwargs["host"], "127.0.0.1")
            self.assertEqual(kwargs["port"], 8000)
            self.assertTrue(directories[0].is_dir())
            with socket.socket() as connection, self.assertRaisesRegex(AssertionError, "outbound"):
                connection.connect(("127.0.0.1", 9))
            if fail:
                raise RuntimeError("simulated startup failure")
            async def lifecycle():
                async with _app.router.lifespan_context(_app):
                    self.assertTrue(directories[0].exists())
            asyncio.run(lifecycle())
            # Must happen during lifespan shutdown, before Uvicorn re-raises SIGTERM.
            self.assertFalse(directories[0].parent.exists())

        with patch.dict(os.environ, {"NFL_OI_SNAPSHOT": "/never-read-an-operator-snapshot"}), \
                patch.object(browser_server, "create_app", side_effect=capture), \
                patch.object(browser_server.uvicorn, "run", side_effect=run):
            if fail:
                with self.assertRaisesRegex(RuntimeError, "simulated startup"):
                    browser_server.main()
            else:
                browser_server.main()
        self.assertEqual(len(directories), 1)
        self.assertFalse(directories[0].parent.exists())

    def test_valid_synthetic_snapshot_and_owned_directory_cleanup(self):
        self.exercise_server(fail=False)

    def test_owned_directory_cleanup_after_startup_failure(self):
        self.exercise_server(fail=True)
