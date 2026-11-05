"""Freeze real Decision API responses over invented observations, without network."""

from contextlib import ExitStack
import csv
from itertools import chain
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from opponent_intelligence.api import create_app
from tests_api.synthetic_snapshot import write_snapshot
from tests_api.test_frontend_contract import time_rows, uncertainty_rows


ROOT = Path(__file__).resolve().parents[1]
BASE = dict(team="CAR", season=2024, season_type="REG", before_week=3,
            down=1, distance_min=10, distance_max=10, compare_league=False)
QUERIES = {
    "selected": BASE,
    "league": BASE | {"compare_league": True},
    "empty": BASE | {"before_week": 1, "compare_league": True},
    "empty_selected": BASE | {"team": "ZZZ", "compare_league": True},
    "empty_baseline": BASE | {"season_type": "POST", "before_week": 20, "compare_league": True},
    "unobserved": BASE | {"down": 3, "distance_min": 7, "distance_max": 7},
    "missing_epa": BASE | {"down": 2, "distance_min": 6, "distance_max": 6, "compare_league": True},
    "distance_range": BASE | {"down": 2, "distance_min": 0, "distance_max": 100, "minimum_plays": 1},
    "context": BASE | {"yardline_max": 20, "score_min": -7, "score_max": 0,
                       "period": "Q4", "clock_max": 120, "compare_league": True},
    "overtime": BASE | {"period": "OT", "clock_min": 0, "clock_max": 120, "compare_league": True},
    "zero_clock": BASE | {"period": "Q4", "clock_min": 0, "clock_max": 0},
}
QUERIES.update({"bootstrap_" + name: BASE | {"before_week": 19, "compare_league": True,
                "bootstrap_repetitions": 200, "bootstrap_seed": 7}
                for name in ("selected", "comparison", "empty", "empty_selected", "unobserved", "missing_epa", "partial_epa",
                             "many_games", "sparse_draws", "valid_boundary")})
QUERIES["bootstrap_selected"].update(compare_league=False)
del QUERIES["bootstrap_selected"]["bootstrap_seed"]
QUERIES["bootstrap_empty"].update(before_week=1)
QUERIES["bootstrap_empty_selected"].update(team="ZZZ")


def decision_fixtures():
    with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
        for target in ("opponent_intelligence.snapshots.urlopen", "socket.create_connection", "socket.socket.connect"):
            stack.enter_context(patch(target, side_effect=AssertionError("network forbidden")))
        with (ROOT / "tests/fixtures/synthetic_pbp.csv").open(newline="") as source:
            rows = [row for row in csv.DictReader(source) if row["season"] == "2024"]
        result = {}
        for name, query in QUERIES.items():
            variant = rows
            if name in ("context", "overtime", "zero_clock"):
                variant = time_rows(rows, "time_four_stage")
            if name.startswith("bootstrap_"):
                variant = uncertainty_rows(rows, name.removeprefix("bootstrap_"))
            if name == "bootstrap_unobserved":
                variant = [row | {"qb_dropback": "1", "play_type": "pass"}
                           if row["posteam"] == "CAR" else row for row in variant]
            controlled = name in ("bootstrap_sparse_draws", "bootstrap_valid_boundary")
            if controlled:
                # Give each candidate five observed-EPA games; 15 baseline-only
                # games make selected-empty draws possible. All rows are invented.
                variant = []
                for game in range(20):
                    for team, defense in (("CAR", "ATL"), ("ATL", "CAR")):
                        if team == "CAR" and game >= 5:
                            continue
                        for call in range(2):
                            variant.append(rows[0] | {"game_id": f"SYNTHETIC_DECISION_{game:02}",
                                "play_id": str(call + (100 if team == "ATL" else 0)),
                                "posteam": team, "defteam": defense, "qb_dropback": str(call),
                                "play_type": "pass" if call else "run", "epa": str(game % 5 - 2 + call)})
            directory = write_snapshot(Path(temporary), variant, list(variant[0]))
            label = "Synthetic Decision API/browser fixture; invented observations and provenance, not real NFL data"
            if controlled:
                label += "; deliberately controlled draws test the valid-replicate gate, not a seed replay"
            with ExitStack() as request_stack, TestClient(create_app(snapshot=directory, source_label=label)) as client:
                if controlled:
                    missing = 11 if name == "bootstrap_sparse_draws" else 10
                    indices = [19] * missing + [0 if i % 2 else 4 for i in range(200 - missing)]
                    rng = request_stack.enter_context(patch("opponent_intelligence.uncertainty.Random"))
                    rng.return_value.randrange.side_effect = chain.from_iterable([i] * 20 for i in indices)
                params = {key: str(value).lower() if isinstance(value, bool) else value for key, value in query.items()}
                response = client.get("/v1/decision", params=params)
                if response.status_code != 200:
                    raise AssertionError(response.text)
                result[name] = {"query": query, "decision": response.json()}
        return result


class DecisionFrontendContractTests(unittest.TestCase):
    def test_frozen_decisions_match_actual_api(self):
        expected = json.loads((ROOT / "web/src/__fixtures__/decisions.json").read_text())
        self.assertEqual(decision_fixtures(), expected)


if __name__ == "__main__":
    # Explicit reviewed update only; the application never imports these fixtures.
    print(json.dumps(decision_fixtures(), indent=2, sort_keys=True, allow_nan=False))
