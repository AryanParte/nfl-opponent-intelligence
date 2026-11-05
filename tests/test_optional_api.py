"""Core commands must remain usable with every site-package dependency disabled."""

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


class OptionalAPITests(unittest.TestCase):
    def test_decision_builder_without_site_packages(self):
        root = Path(__file__).resolve().parents[1]
        script = """
import json
from pathlib import Path
from opponent_intelligence.decision import DecisionRequest, build_decision_evidence
from opponent_intelligence.pbp import load_csv
result = build_decision_evidence(
    load_csv(Path('tests/fixtures/synthetic_pbp.csv')),
    DecisionRequest(team='CAR', season=2024, before_week=3, down=1,
                    distance_min=10, distance_max=10), source_label='Invented isolation fixture',
)
print(json.dumps(result, allow_nan=False))
"""
        result = subprocess.run(
            [sys.executable, "-S", "-c", script], cwd=root,
            env={**os.environ, "PYTHONPATH": str(root / "src")}, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads(result.stdout)
        self.assertEqual(evidence["contract_version"], 1)
        self.assertEqual(evidence["population"]["plays"], 3)
        self.assertIsNone(evidence["comparison"]["preferred_candidate"])

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
