"""Freeze actual API responses for browser tests without shipping a fake live API."""

from contextlib import ExitStack
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from opponent_intelligence.api import create_app
from tests_api.synthetic_snapshot import write_snapshot


ROOT = Path(__file__).resolve().parents[1]
QUERIES = {
    "offense": dict(team="CAR", season=2024, before_week=3, side="offense", season_type="REG"),
    "defense": dict(team="ATL", season=2024, before_week=3, side="defense", season_type="REG"),
    "empty": dict(team="CAR", season=2024, before_week=1, side="offense", season_type="REG"),
}


def browser_fixtures():
    with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
        for target in ("opponent_intelligence.snapshots.urlopen", "socket.create_connection", "socket.socket.connect"):
            stack.enter_context(patch(target, side_effect=AssertionError("network forbidden")))
        with (ROOT / "tests/fixtures/synthetic_pbp.csv").open(newline="") as source:
            rows = [row for row in csv.DictReader(source) if row["season"] == "2024"]
        directory = write_snapshot(Path(temporary), rows, list(rows[0]))
        client = stack.enter_context(TestClient(create_app(snapshot=directory,
            source_label="Synthetic API/browser fixture; invented observations and provenance, not real NFL data")))
        result = {}
        for name, query in QUERIES.items():
            response = client.get("/v1/report", params=query)
            if response.status_code != 200:
                raise AssertionError(response.text)
            result[name] = {"query": query, "report": response.json()}
        return result


class FrontendContractTests(unittest.TestCase):
    def test_committed_browser_fixtures_match_actual_api(self):
        expected = json.loads((ROOT / "web/src/__fixtures__/reports.json").read_text())
        self.assertEqual(browser_fixtures(), expected)


if __name__ == "__main__":
    # Emit to stdout for an explicit, reviewed fixture update; never fetch data.
    print(json.dumps(browser_fixtures(), indent=2, sort_keys=True, allow_nan=False))
