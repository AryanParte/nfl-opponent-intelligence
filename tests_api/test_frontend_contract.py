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
    "offense": dict(team="CAR", season=2024, before_week=3, side="offense", season_type="REG", compare_league=False),
    "defense": dict(team="ATL", season=2024, before_week=3, side="defense", season_type="REG", compare_league=False),
    "empty": dict(team="CAR", season=2024, before_week=1, side="offense", season_type="REG", compare_league=False),
}
QUERIES.update({name + "_comparison": query | {"compare_league": True} for name, query in list(QUERIES.items())})
QUERIES.update({
    "empty_selected_comparison": QUERIES["offense_comparison"] | {"team": "ZZZ"},
    "empty_baseline_comparison": QUERIES["offense_comparison"] | {"season_type": "POST", "before_week": 20},
    "missing_epa_comparison": QUERIES["offense_comparison"],
    "baseline_only_bucket_comparison": QUERIES["offense_comparison"],
})
QUERIES.update({
    "field_unfiltered": QUERIES["offense_comparison"],
    "field_before_first_week": QUERIES["empty_comparison"] | {"yardline_max": 20},
    "field_offense": QUERIES["offense"] | {"yardline_max": 20},
    "field_offense_comparison": QUERIES["offense_comparison"] | {"yardline_max": 20},
    "field_defense_comparison": QUERIES["defense_comparison"] | {"yardline_max": 20},
    "field_full_range": QUERIES["offense_comparison"] | {"yardline_min": 0, "yardline_max": 100},
    "field_lower_only": QUERIES["offense_comparison"] | {"yardline_min": 80},
    "field_zero": QUERIES["offense_comparison"] | {"yardline_max": 0},
    "field_fractional": QUERIES["offense_comparison"] | {"yardline_min": 20.5, "yardline_max": 20.5},
    "field_empty": QUERIES["offense_comparison"] | {"yardline_min": 21, "yardline_max": 79},
    "field_missing_baseline": QUERIES["offense_comparison"] | {"yardline_max": 20},
    "field_all_missing": QUERIES["offense_comparison"] | {"yardline_min": 0},
})
QUERIES.update({
    "score_unfiltered": QUERIES["offense_comparison"],
    "score_offense": QUERIES["offense"] | {"score_min": -7, "score_max": 0},
    "score_comparison": QUERIES["offense_comparison"] | {"score_min": -7, "score_max": 0},
    "score_defense": QUERIES["defense_comparison"] | {"score_min": -7, "score_max": 0},
    "score_lower_only": QUERIES["offense_comparison"] | {"score_min": 1},
    "score_upper_only": QUERIES["offense_comparison"] | {"score_max": -7},
    "score_tied": QUERIES["offense_comparison"] | {"score_min": 0, "score_max": 0},
    "score_input_limits": QUERIES["offense_comparison"] | {"score_min": -1000, "score_max": 1000},
    "score_empty": QUERIES["offense_comparison"] | {"score_min": -6, "score_max": -1},
    "score_all_missing": QUERIES["offense_comparison"] | {"score_max": 0},
    "score_missing_baseline": QUERIES["offense_comparison"] | {"score_max": 0},
    "score_missing_epa": QUERIES["offense_comparison"] | {"score_max": 0},
    "score_field": QUERIES["offense_comparison"] | {"yardline_max": 20.5, "score_min": -7, "score_max": 0},
    "score_field_defense": QUERIES["defense_comparison"] | {"yardline_max": 20.5, "score_min": -7, "score_max": 0},
    "score_before_first_week": QUERIES["empty_comparison"] | {"yardline_max": 20.5, "score_max": 0},
})


def field_position_rows(rows, *, missing_baseline=False, all_missing=False):
    """Invented positions; keep the original no-column fixture unchanged.

    CAR's six eligible REG-before-3 plays have 0, 20, 100, missing, 20.5,
    and 80 yards to goal. ATL's single baseline play has 20 (or missing).
    This makes default/inclusive bounds, zero, EPA and position missingness
    independently checkable. Values on excluded/later plays must not leak in.
    """
    first_game = {"1": "0", "2": "20", "3": "100", "4": "", "5": "20.5", "10": "20"}
    variant = []
    for row in rows:
        position = first_game.get(row["play_id"], "") if row["game_id"] == "SYNTHETIC_2024_01_A" else "80"
        if all_missing or (missing_baseline and row["posteam"] == "ATL"):
            position = ""
        variant.append(row | {"yardline_100": position})
    return variant


def score_rows(rows, name):
    """Invented pre-play scores, not substituted outcomes or real observations.

    CAR: scores -7, 0, 7, missing, missing, 14 on the six eligible plays.
    Add four invented ATL baseline plays: 0 at 20 yards to goal, 7 at 80,
    missing at missing, missing at 20. Its original play has -7 at 20.
    With field <=20.5, each population retains 3 then score [-7, 0]
    retains 2. Missing-at-both is counted at field position, not twice.
    """
    scores = {"1": "-7", "2": "0", "3": "7", "10": "-7"}
    variant = [row | {"score_differential": scores.get(row["play_id"], "")
        if row["game_id"] == "SYNTHETIC_2024_01_A" else "14"} for row in field_position_rows(rows)]
    baseline = next(row for row in variant if row["posteam"] == "ATL")
    for play_id, score, position in (("11", "0", "20"), ("12", "7", "80"),
                                      ("13", "", ""), ("14", "", "20")):
        variant.append(baseline | {"play_id": play_id, "score_differential": score, "yardline_100": position})
    if name == "score_missing_epa":
        variant = [row | {"epa": ""} for row in variant]
    if name in ("score_all_missing", "score_missing_baseline"):
        variant = [row | {"score_differential": ""}
            if name == "score_all_missing" or row["posteam"] == "ATL" else row for row in variant]
    return variant


def browser_fixtures():
    with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
        for target in ("opponent_intelligence.snapshots.urlopen", "socket.create_connection", "socket.socket.connect"):
            stack.enter_context(patch(target, side_effect=AssertionError("network forbidden")))
        with (ROOT / "tests/fixtures/synthetic_pbp.csv").open(newline="") as source:
            rows = [row for row in csv.DictReader(source) if row["season"] == "2024"]
        result = {}
        for name, query in QUERIES.items():
            # All variants remain invented observations, never altered real data.
            variant = rows
            if name == "missing_epa_comparison":
                variant = [row | {"epa": ""} if row["posteam"] == "ATL" else row for row in rows]
            elif name == "baseline_only_bucket_comparison":
                variant = [row | {"down": "4", "ydstogo": "1"} if row["posteam"] == "ATL" else row for row in rows]
            elif name.startswith("field_"):
                variant = field_position_rows(rows, missing_baseline=name == "field_missing_baseline",
                                              all_missing=name == "field_all_missing")
            elif name.startswith("score_"):
                variant = score_rows(rows, name)
            directory = write_snapshot(Path(temporary), variant, list(variant[0]))
            with TestClient(create_app(snapshot=directory,
                source_label="Synthetic API/browser fixture; invented observations and provenance, not real NFL data")) as client:
                params = {key: str(value).lower() if isinstance(value, bool) else value for key, value in query.items()}
                response = client.get("/v1/report", params=params)
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
