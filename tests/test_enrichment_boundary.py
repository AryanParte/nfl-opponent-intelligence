"""Unadmitted charting/proxy columns cannot change validated PBP evidence.

All rows and supplemental values are invented, including deliberately conflicting
labels. This tests consumer isolation, not FTN charting accuracy or field semantics.
"""

from copy import deepcopy
import csv
from dataclasses import replace
from hashlib import sha256
import io
from pathlib import Path
import tempfile
import unittest

from opponent_intelligence.decision import DecisionRequest, build_decision_evidence
from opponent_intelligence.pbp import OPTIONAL_COLUMNS, REQUIRED_COLUMNS, load_csv
from opponent_intelligence.report import build_report


LABEL = "Invented enrichment-boundary fixture; not real NFL observations"
CHARTING_FIELDS = (
    "starting_hash", "qb_location", "n_offense_backfield", "n_defense_box",
    "is_no_huddle", "is_motion", "is_play_action", "is_screen_pass", "is_rpo",
    "is_trick_play", "is_qb_out_of_pocket", "is_interception_worthy", "is_throw_away",
    "read_thrown", "is_catchable_ball", "is_contested_ball", "is_created_reception",
    "is_drop", "is_qb_sneak", "n_blitzers", "n_pass_rushers", "is_qb_fault_sack",
)
# Text, formation, player counts, location/depth and outcome-like fields must not
# become fallback classifications, observations or denominators.
PROXIES = ("shotgun", "no_huddle", "offense_personnel", "offense_formation",
           "desc", "pass_location", "air_yards", "run_location", "run_gap",
           "play_family", "success", "expected_epa")


class EnrichmentBoundaryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.rows = []
        # Five games support the existing exploratory game-bootstrap path. Each
        # offense has one Run, one pass and one raw-run scramble per game.
        for week in range(1, 6):
            for offense, defense, epas in (("CAR", "ATL", ("1", "-1", "NA")),
                                           ("ATL", "CAR", ("-2", "1", "2"))):
                for (play_type, dropback), epa in zip((("run", "0"), ("pass", "1"), ("run", "1")), epas):
                    self.rows.append({
                        "game_id": f"SYNTHETIC_ENRICHMENT_{week}", "play_id": str(len(self.rows) + 1),
                        "season": "2024", "season_type": "REG", "week": str(week),
                        "posteam": offense, "defteam": defense, "play_type": play_type,
                        "down": "3", "ydstogo": "4", "qb_dropback": dropback,
                        "qb_kneel": "0", "qb_spike": "0", "two_point_attempt": "0", "epa": epa,
                        "yardline_100": "38", "score_differential": "-3",
                        "qtr": "4", "quarter_seconds_remaining": "134",
                    })
        self.rows.append(self.rows[1] | {"game_id": "SYNTHETIC_FUTURE", "week": "6", "epa": "100"})
        for i, extra in enumerate(({"qb_kneel": "1"}, {"qb_spike": "1"},
                                   {"two_point_attempt": "1"}, {"play_type": "no_play"}), 100):
            self.rows.append(self.rows[0] | {"play_id": str(i)} | extra)
        self.options = dict(team="CAR", season=2024, before_week=6,
                            yardline_max=38, score_max=-3, period="Q4", clock_max=134,
                            compare_league=True, bootstrap_repetitions=200, bootstrap_seed=7)
        self.request = DecisionRequest(**self.options, down=3, distance_min=4, distance_max=4)

    def dataset(self, rows, supplemental=None):
        fields = (*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS)
        if supplemental is not None:
            fields = (*fields, *supplemental)
            rows = [row | supplemental for row in rows]
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        raw = stream.getvalue().encode()
        path = self.directory / "invented.csv"
        path.write_bytes(raw)
        result = load_csv(path)
        self.assertEqual(result.source_sha256, sha256(raw).hexdigest())
        return result

    def assert_only_fingerprint_changed(self, original, augmented):
        expected, actual = deepcopy(original), deepcopy(augmented)
        self.assertNotEqual(expected["source"].pop("sha256"), actual["source"].pop("sha256"))
        self.assertEqual(actual, expected)  # Preserve every other output field.

    def test_charting_tokens_cannot_change_scout_roles_baselines_or_intervals(self):
        base = self.dataset(self.rows)
        for token in ("TRUE", "FALSE", "NA", "", "0", "invalid"):
            augmented = self.dataset(self.rows, dict.fromkeys(CHARTING_FIELDS, token))
            self.assertEqual(augmented.plays, base.plays)
            self.assertEqual(augmented.exclusions, {"kneel": 1, "spike": 1,
                                                  "two_point_attempt": 1, "non_run_pass": 1})
            for side in ("offense", "defense"):
                with self.subTest(token=token, side=side):
                    original = build_report(base, source_label=LABEL, side=side, **self.options)
                    report = build_report(augmented, source_label=LABEL, side=side, **self.options)
                    self.assert_only_fingerprint_changed(original, report)
                    self.assertEqual(report["overall"]["plays"], 15)
                    self.assertEqual(report["overall"]["dropbacks"], 10)
                    self.assertIn("uncertainty", report)

    def test_plausible_charting_and_proxies_cannot_reclassify_or_rank_run_pass(self):
        base = self.dataset(self.rows)
        charting = dict.fromkeys(CHARTING_FIELDS, "FALSE") | {
            "qb_location": "S", "starting_hash": "L", "read_thrown": "0",
            "n_offense_backfield": "2", "n_defense_box": "7", "n_blitzers": "1",
            "n_pass_rushers": "4", "is_motion": "TRUE", "is_play_action": "TRUE",
            "is_rpo": "TRUE", "is_screen_pass": "TRUE",
        }
        proxies = dict(zip(PROXIES, ("1", "1", "1 RB, 1 TE, 3 WR", "SHOTGUN",
            "motion screen inside zone mesh", "short middle", "2", "left", "guard",
            "screen", "1", "100")))
        for supplemental in (charting, proxies, charting | proxies):
            with self.subTest(fields=tuple(supplemental)):
                augmented = self.dataset(self.rows, supplemental)
                original = build_decision_evidence(base, self.request, source_label=LABEL)
                result = build_decision_evidence(augmented, self.request, source_label=LABEL)
                self.assert_only_fingerprint_changed(original, result)
                run, passed = result["candidates"]
                self.assertEqual((run["plays"], passed["plays"]), (5, 10))
                self.assertEqual((run["frequency_denominator"], passed["frequency_denominator"]), (15, 15))
                self.assertEqual((run["epa_observations"], passed["epa_observations"]), (5, 5))
                self.assertEqual((run["epa_per_play"], passed["epa_per_play"]), (1, -1))
                self.assertEqual((run["success_rate"], passed["success_rate"]), (1, 0))
                self.assertEqual(passed["missing_epa"], 5)
                self.assertIsNone(result["comparison"]["preferred_candidate"])
                self.assertEqual(result["comparison"]["status"], "insufficient_evidence")
                self.assertIn("uncertainty", result)

    def test_extra_fields_cannot_fill_missing_context_or_outcomes_or_an_empty_cohort(self):
        rows = deepcopy(self.rows)
        rows[0]["yardline_100"] = "NA"
        rows[6]["epa"] = "NA"
        base = self.dataset(rows)
        augmented = self.dataset(rows, dict.fromkeys(CHARTING_FIELDS, "TRUE") | {
            "shotgun": "1", "success": "1", "expected_epa": "100", "play_family": "RPO"})
        for before_week in (6, 1):
            request = replace(self.request, before_week=before_week)
            original = build_decision_evidence(base, request, source_label=LABEL)
            report = build_decision_evidence(augmented, request, source_label=LABEL)
            self.assert_only_fingerprint_changed(original, report)
            run, passed = report["candidates"]
            if before_week == 6:
                self.assertEqual(report["data_quality"]["field_position_filter"]["missing_yardline_100"], 1)
                self.assertEqual((run["plays"], run["epa_observations"], run["missing_epa"]), (4, 3, 1))
                self.assertEqual((run["frequency_denominator"], passed["frequency_denominator"]), (14, 14))
                self.assertEqual(run["epa_per_play"], 1)
                self.assertEqual(passed["missing_epa"], 5)
            else:
                for candidate in (run, passed):
                    self.assertEqual(candidate["plays"], 0)
                    for metric in ("frequency", "epa_per_play", "success_rate"):
                        self.assertIsNone(candidate[metric])


if __name__ == "__main__":
    unittest.main()
