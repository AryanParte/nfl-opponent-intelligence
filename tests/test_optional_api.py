"""Core commands must remain usable with every site-package dependency disabled."""

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


class OptionalAPITests(unittest.TestCase):
    def test_core_cli_without_site_packages(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-S", "-m", "opponent_intelligence", "--csv",
             str(root / "tests/fixtures/synthetic_pbp.csv"), "--source-label", "Synthetic isolation test",
             "--team", "CAR", "--season", "2024", "--before-week", "3"],
            env={**os.environ, "PYTHONPATH": str(root / "src")}, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["overall"]["plays"], 6)


if __name__ == "__main__":
    unittest.main()
