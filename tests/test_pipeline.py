import csv
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from opponent_intelligence.pbp import DataValidationError, REQUIRED_COLUMNS, load_csv
from opponent_intelligence.report import build_report


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_pbp.csv"


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.dataset = load_csv(FIXTURE)

    def report(self, **overrides):
        options = dict(team="CAR", season=2024, before_week=3, source_label="Synthetic test fixture")
        options.update(overrides)
        return build_report(self.dataset, **options)

    def modified_csv(self, **updates):
        with FIXTURE.open(newline="") as handle:
            row = next(csv.DictReader(handle))
        row.update(updates)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "input.csv"
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
            writer.writeheader()
            writer.writerow(row)
        return path

    def test_hand_calculated_cohort_metrics(self):
        overall = self.report()["overall"]
        self.assertEqual(overall["plays"], 6)
        self.assertEqual(overall["games"], 2)
        self.assertEqual(overall["dropbacks"], 3)
        self.assertEqual(overall["designed_runs"], 3)
        self.assertEqual(overall["dropback_rate"], 0.5)
        self.assertEqual(overall["epa_observations"], 5)
        self.assertEqual(overall["missing_epa"], 1)
        self.assertAlmostEqual(overall["epa_per_play"], 0.04)
        self.assertEqual(overall["success_rate"], 0.6)

    def test_sacks_and_scrambles_are_dropbacks(self):
        # Row 3 is a sack-shaped pass; row 4 is a run-shaped QB scramble.
        self.assertTrue(self.dataset.plays[2].dropback)
        self.assertTrue(self.dataset.plays[3].dropback)

    def test_exclusions_and_cohort_reconcile_to_source(self):
        quality = self.report()["data_quality"]
        self.assertEqual(quality["input_rows"], 14)
        self.assertEqual(quality["excluded_rows_by_reason"],
                         {"kneel": 1, "non_run_pass": 1, "spike": 1, "two_point_attempt": 1})
        self.assertEqual(quality["eligible_rows_all_teams"], 10)
        self.assertEqual(quality["eligible_rows_outside_cohort"], 4)
        self.assertEqual(sum(quality["excluded_rows_by_reason"].values()) + 10, 14)

    def test_target_week_is_excluded(self):
        self.assertEqual(self.report(before_week=2)["overall"]["plays"], 5)
        self.assertEqual(self.report(before_week=3)["overall"]["plays"], 6)
        self.assertEqual(self.report(before_week=4)["overall"]["plays"], 7)

    def test_regular_season_does_not_include_playoffs(self):
        self.assertEqual(self.report(before_week=23)["overall"]["plays"], 7)
        self.assertEqual(self.report(before_week=23, season_type="POST")["overall"]["plays"], 1)

    def test_other_offense_and_season_are_excluded(self):
        self.assertEqual(self.report(team="ATL")["overall"]["epa_per_play"], 3.0)
        self.assertEqual(self.report(season=2025)["overall"]["epa_per_play"], 5.0)

    def test_empty_cohort_is_not_zero_efficiency(self):
        overall = self.report(before_week=1)["overall"]
        self.assertEqual(overall["plays"], 0)
        for name in ("dropback_rate", "epa_per_play", "success_rate"):
            self.assertIsNone(overall[name])

    def test_missing_epa_does_not_erase_play_tendency(self):
        dataset = load_csv(self.modified_csv(epa="NA"))
        report = build_report(dataset, team="CAR", season=2024, before_week=2, source_label="Synthetic")
        self.assertEqual(report["overall"]["plays"], 1)
        self.assertEqual(report["overall"]["dropback_rate"], 1.0)
        self.assertIsNone(report["overall"]["success_rate"])

    def test_zero_epa_is_observed_but_not_a_success(self):
        dataset = load_csv(self.modified_csv(epa="0"))
        report = build_report(dataset, team="CAR", season=2024, before_week=2, source_label="Synthetic")
        self.assertEqual(report["overall"]["epa_observations"], 1)
        self.assertEqual(report["overall"]["success_rate"], 0.0)

    def test_small_sample_flags_have_separate_denominators(self):
        overall = self.report(minimum_plays=6)["overall"]
        self.assertFalse(overall["small_sample"])
        self.assertTrue(overall["small_epa_sample"])

    def test_down_distance_boundaries(self):
        base = self.dataset.plays[0]
        plays = tuple(replace(base, play_id=i, yards_to_go=distance)
                      for i, distance in enumerate((0, 3, 4, 6, 7, 10)))
        self.dataset = replace(self.dataset, plays=plays)
        situations = self.report()["situations"]
        self.assertEqual([(item["distance"], item["plays"]) for item in situations],
                         [("short", 2), ("medium", 2), ("long", 2)])

    def test_source_hash_is_of_exact_input(self):
        self.assertEqual(self.dataset.source_sha256, sha256(FIXTURE.read_bytes()).hexdigest())

    def test_invalid_data_fails_with_line_context(self):
        for change in ({"down": "2.5"}, {"epa": "inf"}, {"qb_dropback": ""},
                       {"posteam": ""}, {"defteam": "CAR"}, {"season_type": "UNKNOWN"},
                       {"play_id": "nan"}, {"ydstogo": "-1"}, {"week": "0"},
                       {"qb_dropback": "0"}):
            with self.subTest(change=change):
                with self.assertRaisesRegex(DataValidationError, "CSV line 2:"):
                    load_csv(self.modified_csv(**change))

    def test_unknown_play_types_fail_with_line_and_value(self):
        for play_type in ("passs", "PASS", "Run", "sack", "kick_of", "unknown", "0", "N/A"):
            with self.subTest(play_type=play_type):
                with self.assertRaisesRegex(DataValidationError, "CSV line 2: play_type:") as error:
                    load_csv(self.modified_csv(play_type=play_type))
                self.assertIn(repr(play_type), str(error.exception))

    def test_unknown_play_type_cannot_hide_behind_exclusions(self):
        for change in ({"two_point_attempt": "1"}, {"qb_kneel": "1"}, {"qb_spike": "1"},
                       {"season": "2025"}, {"week": "18"}, {"posteam": "ATL", "defteam": "CAR"}):
            with self.subTest(change=change):
                with self.assertRaisesRegex(DataValidationError, "play_type:"):
                    load_csv(self.modified_csv(play_type="new_upstream_type", **change))

    def test_documented_non_run_pass_types_remain_valid_exclusions(self):
        # An independent contract list, not the implementation's allowlist.
        for play_type in ("punt", "field_goal", "kickoff", "extra_point",
                          "qb_kneel", "qb_spike", "no_play"):
            with self.subTest(play_type=play_type):
                dataset = load_csv(self.modified_csv(
                    play_type=f" {play_type} ", down="", ydstogo="", posteam="", defteam="",
                    epa="", qb_dropback="", qb_kneel="", qb_spike="", two_point_attempt="",
                ))
                self.assertEqual(dataset.plays, ())
                self.assertEqual(dataset.input_rows, 1)
                self.assertEqual(dataset.exclusions, {"non_run_pass": 1})

    def test_missing_play_types_have_separate_audited_exclusions(self):
        for play_type in ("", " ", "NA", "na", "NaN", " null "):
            with self.subTest(play_type=play_type):
                self.dataset = load_csv(self.modified_csv(
                    play_type=play_type, down="", ydstogo="", posteam="", defteam="",
                    epa="", qb_dropback="", qb_kneel="", qb_spike="", two_point_attempt="",
                ))
                report = self.report()
                self.assertEqual(report["data_quality"], {
                    "input_rows": 1, "eligible_rows_all_teams": 0,
                    "eligible_rows_outside_cohort": 0,
                    "excluded_rows_by_reason": {"missing_play_type": 1},
                })
                self.assertEqual(report["overall"]["plays"], 0)
                self.assertIsNone(report["overall"]["dropback_rate"])
                self.assertIsNone(report["overall"]["epa_per_play"])
                self.assertIsNone(report["overall"]["success_rate"])

    def test_play_type_filter_does_not_bypass_identity_validation(self):
        for play_type in ("no_play", "qb_kneel", "NA"):
            with self.subTest(play_type=play_type):
                with self.assertRaisesRegex(DataValidationError, "game_id must be present"):
                    load_csv(self.modified_csv(play_type=play_type, game_id=""))
                path = self.modified_csv(play_type=play_type, play_id="1.0")
                with FIXTURE.open(newline="") as source, path.open("a", newline="") as handle:
                    row = next(csv.DictReader(source))
                    csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS).writerow(row)
                with self.assertRaisesRegex(DataValidationError, "CSV line 3: duplicate play key"):
                    load_csv(path)

    def test_recognized_exclusions_do_not_change_eligible_metrics(self):
        before = self.report()
        with FIXTURE.open(newline="") as source:
            rows = list(csv.DictReader(source))
        rows.extend((dict(rows[0], play_id="999", play_type="NA"),
                     dict(rows[0], play_id="1000", play_type="field_goal")))
        path = self.modified_csv()
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        self.dataset = load_csv(path)
        after = self.report()
        self.assertEqual(after["overall"], before["overall"])
        self.assertEqual(after["situations"], before["situations"])
        self.assertEqual(after["data_quality"], {
            "input_rows": 16, "eligible_rows_all_teams": 10,
            "eligible_rows_outside_cohort": 4,
            "excluded_rows_by_reason": {"kneel": 1, "non_run_pass": 2,
                                        "spike": 1, "two_point_attempt": 1,
                                        "missing_play_type": 1},
        })

    def test_duplicate_keys_fail_even_when_integer_serialization_differs(self):
        path = self.modified_csv(play_id="1.0")
        with path.open("a", newline="") as handle:
            with FIXTURE.open(newline="") as source:
                row = next(csv.DictReader(source))
            csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS).writerow(row)
        with self.assertRaisesRegex(DataValidationError, "duplicate play key"):
            load_csv(path)

    def test_missing_columns_and_wrong_row_width_fail(self):
        path = self.modified_csv()
        for content, message in (("game_id,play_id\na,1\n", "missing required columns"),
                                 (",".join(REQUIRED_COLUMNS) + "\na,1\n", "row width"),
                                 ("game_id,game_id\na,a\n", "duplicate column")):
            with self.subTest(message=message):
                path.write_text(content)
                with self.assertRaisesRegex(DataValidationError, message):
                    load_csv(path)

    def test_missing_markers_and_numeric_serialization(self):
        for value in ("", "NA", "NaN", "null"):
            with self.subTest(value=value):
                dataset = load_csv(self.modified_csv(epa=value, play_id="1.0", qb_dropback="1.0"))
                self.assertIsNone(dataset.plays[0].epa)

    def test_invalid_report_arguments(self):
        for change in ({"before_week": 0}, {"season": 1}, {"minimum_plays": 0},
                       {"before_week": 2.5}, {"before_week": True}, {"source_label": " "}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.report(**change)

    def test_cli_is_deterministic_and_has_no_partial_success_on_error(self):
        command = [sys.executable, "-m", "opponent_intelligence", "--csv", str(FIXTURE),
                   "--team", "CAR", "--season", "2024", "--before-week", "3",
                   "--source-label", "Synthetic test fixture"]
        first = subprocess.run(command, capture_output=True, text=True, check=True)
        second = subprocess.run(command, capture_output=True, text=True, check=True)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(json.loads(first.stdout)["overall"]["plays"], 6)
        invalid = command.copy()
        invalid[invalid.index("--before-week") + 1] = "0"
        failed = subprocess.run(invalid, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(failed.stdout, "")
        self.assertIn("error:", failed.stderr)

    def test_cli_rejects_unknown_play_type_after_valid_rows(self):
        path = self.modified_csv()
        with FIXTURE.open(newline="") as source, path.open("a", newline="") as handle:
            row = next(csv.DictReader(source))
            row.update(play_id="999", play_type="passs")
            csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS).writerow(row)
        command = [sys.executable, "-m", "opponent_intelligence", "--csv", str(path),
                   "--team", "CAR", "--season", "2024", "--before-week", "3",
                   "--source-label", "Synthetic test fixture"]
        failed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(failed.stdout, "")
        self.assertIn("CSV line 3: play_type:", failed.stderr)
        self.assertIn("'passs'", failed.stderr)


if __name__ == "__main__":
    unittest.main()
