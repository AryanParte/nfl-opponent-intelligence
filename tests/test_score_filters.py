"""Invented score situations: no numbers in these tests are real NFL findings."""

import csv
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from opponent_intelligence.pbp import DataValidationError, REQUIRED_COLUMNS, load_csv
from opponent_intelligence.report import build_report


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_pbp.csv"


class ScoreFilterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "input.csv"
        with FIXTURE.open(newline="") as source:
            base = dict(next(csv.DictReader(source)), game_id="SYNTHETIC_SCORE_A",
                        yardline_100="20", score_differential="0", score_differential_post="99")
        self.rows = [
            dict(base, play_id="1", score_differential="-7", epa="0.8"),
            dict(base, play_id="2", score_differential="-1", yardline_100="10",
                 play_type="run", qb_dropback="0", down="2", ydstogo="3", epa="-0.4"),
            dict(base, play_id="3", epa="0"),
            dict(base, play_id="4", score_differential="7", yardline_100="80",
                 play_type="run", qb_dropback="0", epa=""),
            dict(base, play_id="5", score_differential="NA", yardline_100="10", epa="0.9"),
            dict(base, play_id="6", score_differential="-7", yardline_100="NA", epa="0.1"),
            dict(base, play_id="7", score_differential="NA", yardline_100="NA", epa="0.2"),
            dict(base, play_id="8", yardline_100="5", play_type="run", qb_dropback="0",
                 down="3", ydstogo="5", epa=""),
            dict(base, play_id="9", score_differential="7", epa="-0.2"),
            dict(base, game_id="SYNTHETIC_TARGET", week="3", epa="99"),
            dict(base, game_id="SYNTHETIC_POST", season_type="POST", week="19", epa="9"),
            dict(base, game_id="SYNTHETIC_NEXT_YEAR", season="2025", epa="8"),
            dict(base, play_id="13", posteam="ATL", defteam="CAR", score_differential="7", epa="5"),
            dict(base, play_id="14", play_type="no_play", score_differential="unused"),
            dict(base, game_id="SYNTHETIC_SCORE_B", week="2", posteam="NO",
                 score_differential="-3", epa="-0.6"),
        ]
        self.dataset = load_csv(self.write_rows())

    def write_rows(self, rows=None, *, omit=()):
        columns = REQUIRED_COLUMNS + ("yardline_100", "score_differential", "score_differential_post")
        columns = tuple(name for name in columns if name not in omit)
        rows = self.rows if rows is None else rows
        with self.path.open("w", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=columns)
            writer.writeheader()
            writer.writerows({k: v for k, v in row.items() if k not in omit} for row in rows)
        return self.path

    def report(self, **changes):
        options = dict(team="CAR", season=2024, before_week=3,
                       source_label="Synthetic score records; not real NFL observations")
        options.update(changes)
        return build_report(self.dataset, **options)

    def test_optional_scores_parse_exact_whole_points_without_historical_caps(self):
        self.assertEqual(self.dataset.optional_columns, ("yardline_100", "score_differential"))
        self.assertEqual([p.score_differential for p in self.dataset.plays[:9]],
                         [-7, -1, 0, 7, None, -7, None, 0, 7])
        for value, expected in (("-7.00", -7), (" +125 ", 125), ("-125", -125),
                                ("-0", 0), ("9007199254740993.0", 9007199254740993)):
            with self.subTest(value=value):
                dataset = load_csv(self.write_rows([dict(self.rows[0], score_differential=value)]))
                self.assertEqual(dataset.plays[0].score_differential, expected)
                self.assertIs(type(dataset.plays[0].score_differential), int)

    def test_missing_markers_are_not_ties_or_imputed_from_post_play_scores(self):
        for value in ("", " ", "NA", "nan", " null "):
            with self.subTest(value=value):
                self.dataset = load_csv(self.write_rows([dict(self.rows[0], score_differential=value)]))
                self.assertIsNone(self.dataset.plays[0].score_differential)
                self.assertEqual(self.report()["overall"]["plays"], 1)
                filtered = self.report(score_min=0, score_max=0)
                self.assertEqual(filtered["overall"]["plays"], 0)
                self.assertIsNone(filtered["overall"]["success_rate"])
                self.assertEqual(filtered["data_quality"]["score_differential_filter"]["missing_score_differential"], 1)
                self.assertTrue(any("Missing score_differential" in w for w in filtered["warnings"]))

    def test_absent_score_header_fails_even_when_another_filter_leaves_no_plays(self):
        self.dataset = load_csv(self.write_rows(omit=("score_differential",)))
        self.assertEqual(self.report()["overall"]["plays"], 9)
        for changes in ({}, {"yardline_max": 0}, {"team": "GB"}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "requires.*score_differential"):
                self.report(score_max=0, **changes)
        self.dataset = load_csv(self.write_rows([], omit=("score_differential",)))
        with self.assertRaisesRegex(ValueError, "requires.*score_differential"):
            self.report(score_max=0)

    def test_invalid_scores_fail_with_line_context_even_outside_the_cohort(self):
        for value in ("0.1", "7.000000000000000001", "-inf", "inf", "+nan", "seven",
                      "1e2", "1e999999", "1_0", "0x10", "1,000", "７"):
            with self.subTest(value=value), self.assertRaisesRegex(DataValidationError, "CSV line 3: score_differential:"):
                load_csv(self.write_rows([self.rows[0], dict(self.rows[9], score_differential=value)]))

    def test_excluded_rows_do_not_require_valid_score_context(self):
        for change in ({"play_type": "no_play"}, {"play_type": "NA"}, {"two_point_attempt": "1"},
                       {"qb_kneel": "1"}, {"qb_spike": "1"}):
            with self.subTest(change=change):
                dataset = load_csv(self.write_rows([dict(self.rows[0], score_differential="unused", **change)]))
                self.assertEqual(dataset.plays, ())
                self.assertEqual(sum(dataset.exclusions.values()), 1)

    def test_unfiltered_and_field_only_reports_ignore_score_values(self):
        before = [self.report(), self.report(yardline_max=20)]
        self.dataset = replace(self.dataset, plays=tuple(replace(p, score_differential=None)
                                                        for p in self.dataset.plays))
        self.assertEqual(before, [self.report(score_min=None, score_max=None), self.report(yardline_max=20)])
        for report in before:
            self.assertNotIn("score_differential", report["cohort"])
            self.assertNotIn("score_differential_filter", report["data_quality"])
            self.assertNotIn("filter_order", report["data_quality"])

    def test_inclusive_signed_bounds_allow_ties_and_one_unbounded_end(self):
        cases = (({"score_max": -1}, 3), ({"score_min": 1}, 2),
                 ({"score_min": 0, "score_max": 0}, 2), ({"score_min": 0}, 4),
                 ({"score_max": 0}, 5), ({"score_min": -7, "score_max": -7}, 2),
                 ({"score_min": -125, "score_max": 125}, 7))
        for bounds, expected in cases:
            with self.subTest(bounds=bounds):
                result = self.report(**bounds)
                self.assertEqual(result["overall"]["plays"], expected)
                self.assertEqual(result["cohort"]["score_differential"], {
                    "field": "score_differential", "minimum_inclusive": bounds.get("score_min"),
                    "maximum_inclusive": bounds.get("score_max"), "perspective": "offense",
                    "missing_policy": "exclude",
                })
        self.assertEqual(self.report()["overall"]["plays"], 9)

    def test_score_only_metrics_use_selected_play_and_observed_epa_denominators(self):
        result = self.report(score_min=-7, score_max=0, minimum_plays=5)
        self.assertEqual(result["overall"], {
            "plays": 5, "games": 1, "dropbacks": 3, "designed_runs": 2, "dropback_rate": 3 / 5,
            "epa_observations": 4, "missing_epa": 1, "epa_per_play": 0.125, "success_rate": 0.5,
            "small_sample": False, "small_epa_sample": True,
        })
        self.assertEqual(result["data_quality"]["score_differential_filter"], {
            "plays_before_filter": 9, "missing_score_differential": 2,
            "outside_range": 2, "plays_after_filter": 5,
        })
        self.assertEqual(result["data_quality"]["filter_order"], ["score_differential"])
        tied = self.report(score_min=0, score_max=0)["overall"]
        self.assertEqual((tied["plays"], tied["epa_observations"], tied["epa_per_play"], tied["success_rate"]),
                         (2, 1, 0, 0))
        missing_epa = self.report(score_max=0, yardline_min=5, yardline_max=5)["overall"]
        self.assertEqual((missing_epa["plays"], missing_epa["missing_epa"], missing_epa["dropback_rate"]), (1, 1, 0))
        self.assertIsNone(missing_epa["epa_per_play"])
        self.assertIsNone(missing_epa["success_rate"])

    def test_combined_filters_count_each_removed_play_once_in_explicit_order(self):
        result = self.report(yardline_max=20, score_min=-7, score_max=0, minimum_plays=4)
        quality = result["data_quality"]
        self.assertEqual(quality["filter_order"], ["field_position", "score_differential"])
        self.assertEqual(quality["field_position_filter"], {
            "plays_before_filter": 9, "missing_yardline_100": 2, "outside_range": 1, "plays_after_filter": 6,
        })
        self.assertEqual(quality["score_differential_filter"], {
            "plays_before_filter": 6, "missing_score_differential": 1, "outside_range": 1, "plays_after_filter": 4,
        })
        self.assertEqual(quality["eligible_rows_outside_cohort"], 10)
        self.assertEqual(quality["input_rows"], 15)
        self.assertEqual(quality["input_rows"], 4 + 10 + sum(quality["excluded_rows_by_reason"].values()))
        metrics = result["overall"]
        self.assertEqual((metrics["plays"], metrics["dropbacks"], metrics["epa_observations"], metrics["missing_epa"]),
                         (4, 2, 3, 1))
        self.assertAlmostEqual(metrics["epa_per_play"], 0.4 / 3)
        self.assertEqual(metrics["success_rate"], 1 / 3)
        self.assertFalse(metrics["small_sample"])
        self.assertTrue(metrics["small_epa_sample"])
        self.assertEqual([(r["down"], r["distance"], r["plays"]) for r in result["situations"]],
                         [(1, "long", 2), (2, "short", 1), (3, "medium", 1)])
        self.assertTrue(any("1 of 6" in w and "Missing score_differential" in w for w in result["warnings"]))

    def test_defense_never_flips_the_score_sign_or_epa(self):
        result = self.report(team="ATL", side="defense", score_min=-7, score_max=0, yardline_max=20)
        metrics = result["overall"]
        self.assertEqual((metrics["plays"], metrics["games"], metrics["dropbacks"], metrics["epa_observations"]),
                         (5, 2, 3, 4))
        self.assertAlmostEqual(metrics["epa_per_play"], -0.05)
        self.assertEqual(metrics["success_rate"], 1 / 4)
        self.assertEqual(result["metric_context"]["interpretation"], "allowed")
        self.assertEqual(self.report(team="CAR", side="defense", score_min=1)["overall"]["plays"], 1)
        self.assertEqual(self.report(team="CAR", side="defense", score_max=-1)["overall"]["plays"], 0)

    def test_reciprocal_matchup_measurements_are_identical(self):
        offense = self.report(before_week=2, yardline_max=20, score_max=0)
        defense = self.report(team="ATL", side="defense", before_week=2, yardline_max=20, score_max=0)
        for key in ("overall", "situations", "source", "data_quality"):
            self.assertEqual(offense[key], defense[key])

    def test_score_filter_preserves_exclusive_week_and_season_boundaries(self):
        for selection, expected in (({"before_week": 1}, 0), ({"before_week": 3}, 2),
                                    ({"before_week": 4}, 3), ({"season": 2025}, 1),
                                    ({"season_type": "POST", "before_week": 19}, 0),
                                    ({"season_type": "POST", "before_week": 23}, 1)):
            with self.subTest(selection=selection):
                self.assertEqual(self.report(score_min=0, score_max=0, **selection)["overall"]["plays"], expected)

    def test_missingness_is_scoped_to_team_time_and_preceding_field_filter(self):
        rows = self.rows.copy()
        for index in (9, 10, 11, 12, 14):
            rows[index] = dict(rows[index], score_differential="NA")
        self.dataset = load_csv(self.write_rows(rows))
        self.assertEqual(self.report(score_max=0)["data_quality"]["score_differential_filter"]["missing_score_differential"], 2)
        combined = self.report(yardline_max=20, score_max=0)
        self.assertEqual(combined["data_quality"]["score_differential_filter"]["missing_score_differential"], 1)

    def test_only_pre_play_score_matters_even_if_post_play_score_is_unusable(self):
        expected = self.report(score_max=0)
        rows = [dict(row, score_differential_post="unusable") for row in self.rows]
        self.dataset = load_csv(self.write_rows(rows))
        actual = self.report(score_max=0)
        self.assertNotEqual(expected.pop("source"), actual.pop("source"))
        self.assertEqual(expected, actual)

    def test_empty_unmatched_or_fully_filtered_cohorts_have_null_rates(self):
        for rows, options in (([], {}), (self.rows, {"team": "GB"}),
                              (self.rows, {"score_min": 2, "score_max": 6}),
                              (self.rows, {"yardline_max": 0})):
            with self.subTest(options=options):
                self.dataset = load_csv(self.write_rows(rows))
                result = self.report(**({"score_max": 0} | options))
                self.assertEqual(result["overall"]["plays"], 0)
                self.assertEqual(result["situations"], [])
                for key in ("epa_per_play", "success_rate", "dropback_rate"):
                    self.assertIsNone(result["overall"][key])

    def test_score_filter_does_not_require_field_position_column(self):
        self.dataset = load_csv(self.write_rows(omit=("yardline_100",)))
        self.assertEqual(self.report(score_max=0)["overall"]["plays"], 5)
        with self.assertRaisesRegex(ValueError, "requires.*yardline_100"):
            self.report(score_max=0, yardline_max=20)

    def test_invalid_api_bounds_cannot_silently_disable_or_round_filters(self):
        for name in ("score_min", "score_max"):
            for value in (0.0, -0.5, float("nan"), float("inf"), True, False, "0", [], {}):
                with self.subTest(name=name, value=value), self.assertRaisesRegex(ValueError, name):
                    self.report(**{name: value})
        with self.assertRaisesRegex(ValueError, "score_min.*score_max"):
            self.report(score_min=1, score_max=0)

    def test_cli_is_deterministic_and_errors_emit_no_partial_json(self):
        command = [sys.executable, "-m", "opponent_intelligence", "--csv", str(self.path),
                   "--team", "CAR", "--season", "2024", "--before-week", "3",
                   "--source-label", "Synthetic score records; not real NFL observations"]
        good = command + ["--yardline-max", "20", "--score-min", "-7", "--score-max", "0"]
        first = subprocess.run(good, check=True, capture_output=True, text=True)
        second = subprocess.run(good, check=True, capture_output=True, text=True)
        self.assertEqual(first.stdout, second.stdout)
        reordered = subprocess.run(command + ["--score-max", "0", "--score-min", "-7", "--yardline-max", "20"],
                                   check=True, capture_output=True, text=True)
        self.assertEqual(first.stdout, reordered.stdout)
        self.assertEqual(json.loads(first.stdout)["overall"]["plays"], 4)
        for arguments in (("--score-min", "1", "--score-max", "0"), ("--score-max", "0.0"),
                          ("--score-max", "nan"), ("--score-max", "inf")):
            with self.subTest(arguments=arguments):
                failed = subprocess.run(command + list(arguments), capture_output=True, text=True)
                self.assertEqual(failed.returncode, 2)
                self.assertEqual(failed.stdout, "")
                self.assertIn("error:", failed.stderr)
        self.write_rows(omit=("score_differential",))
        failed = subprocess.run(good, capture_output=True, text=True)
        self.assertEqual((failed.returncode, failed.stdout), (2, ""))
        self.assertIn("requires", failed.stderr)
        self.write_rows([dict(self.rows[0], score_differential="0.5")])
        failed = subprocess.run(good, capture_output=True, text=True)
        self.assertEqual((failed.returncode, failed.stdout), (2, ""))
        self.assertIn("CSV line 2: score_differential:", failed.stderr)


if __name__ == "__main__":
    unittest.main()
