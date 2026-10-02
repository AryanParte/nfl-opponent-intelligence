"""Synthetic contract tests; none of these values are NFL observations."""

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


class FieldPositionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        with FIXTURE.open(newline="") as source:
            base = dict(next(csv.DictReader(source)), game_id="SYNTHETIC_FIELD_A")
        self.rows = [
            dict(base, play_id="1", yardline_100="0", epa="0.8"),
            dict(base, play_id="2", yardline_100="20", play_type="run", qb_dropback="0", epa="-0.4"),
            dict(base, play_id="3", yardline_100="20.5", epa="0.1"),
            dict(base, play_id="4", yardline_100="100", epa="0"),
            dict(base, play_id="5", yardline_100="NA", play_type="run", qb_dropback="0", epa="0.9"),
            dict(base, play_id="6", yardline_100="10", play_type="run", qb_dropback="0", epa=""),
            dict(base, game_id="SYNTHETIC_TARGET", week="3", yardline_100="10", epa="99"),
            dict(base, game_id="SYNTHETIC_POST", season_type="POST", week="19", yardline_100="10", epa="9"),
            dict(base, game_id="SYNTHETIC_NEXT_YEAR", season="2025", yardline_100="10", epa="8"),
            dict(base, play_id="10", posteam="ATL", defteam="CAR", yardline_100="10", epa="5"),
            dict(base, play_id="11", play_type="no_play", yardline_100="unused"),
            dict(base, game_id="SYNTHETIC_FIELD_B", week="2", posteam="NO", yardline_100="15", epa="-0.6"),
        ]
        self.path = self.write_rows()
        self.dataset = load_csv(self.path)

    def write_rows(self, rows=None, *, include_column=True):
        path = self.root / "input.csv"
        columns = REQUIRED_COLUMNS + (("yardline_100",) if include_column else ())
        rows = self.rows if rows is None else rows
        if not include_column:
            rows = [{key: value for key, value in row.items() if key != "yardline_100"} for row in rows]
        with path.open("w", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def report(self, **changes):
        options = dict(team="CAR", season=2024, before_week=3,
                       source_label="Synthetic field-position records; not real NFL observations")
        options.update(changes)
        return build_report(self.dataset, **options)

    def test_optional_field_parses_fractional_and_endpoint_values(self):
        self.assertEqual(self.dataset.optional_columns, ("yardline_100",))
        self.assertEqual([p.yardline_100 for p in self.dataset.plays[:6]],
                         [0, 20, 20.5, 100, None, 10])
        self.assertEqual(self.dataset.input_rows, 12)
        self.assertEqual(self.dataset.exclusions, {"non_run_pass": 1})

    def test_absent_column_is_supported_only_without_a_filter(self):
        self.dataset = load_csv(self.write_rows(include_column=False))
        self.assertEqual(self.dataset.optional_columns, ())
        self.assertTrue(all(p.yardline_100 is None for p in self.dataset.plays))
        self.assertEqual(self.report()["overall"]["plays"], 6)
        with self.assertRaisesRegex(ValueError, "requires.*yardline_100"):
            self.report(yardline_max=20)

    def test_missing_markers_are_not_imputed_to_zero(self):
        for value in ("", " ", "NA", "nan", " null "):
            with self.subTest(value=value):
                self.dataset = load_csv(self.write_rows([dict(self.rows[0], yardline_100=value)]))
                self.assertIsNone(self.dataset.plays[0].yardline_100)
                self.assertEqual(self.report()["overall"]["plays"], 1)
                filtered = self.report(yardline_min=0, yardline_max=0)
                self.assertEqual(filtered["overall"]["plays"], 0)
                self.assertIsNone(filtered["overall"]["epa_per_play"])
                self.assertEqual(filtered["data_quality"]["field_position_filter"]["missing_yardline_100"], 1)

    def test_invalid_observed_values_fail_even_outside_report_cohort(self):
        for value in ("-0.1", "100.1", "inf", "-inf", "+nan", "twenty", "1e999"):
            with self.subTest(value=value):
                bad = dict(self.rows[6], yardline_100=value)
                with self.assertRaisesRegex(DataValidationError, "CSV line 3: yardline_100:"):
                    load_csv(self.write_rows([self.rows[0], bad]))

    def test_field_is_not_parsed_after_an_eligibility_exclusion(self):
        for change in ({"play_type": "no_play"}, {"two_point_attempt": "1"},
                       {"qb_kneel": "1"}, {"qb_spike": "1"}):
            with self.subTest(change=change):
                row = dict(self.rows[0], yardline_100="unused", **change)
                dataset = load_csv(self.write_rows([row]))
                self.assertEqual(dataset.plays, ())
                self.assertEqual(sum(dataset.exclusions.values()), 1)

    def test_unfiltered_output_is_unchanged_by_available_field_values(self):
        before = self.report()
        self.assertEqual(before, self.report(yardline_min=None, yardline_max=None))
        self.dataset = replace(self.dataset,
                               plays=tuple(replace(p, yardline_100=None) for p in self.dataset.plays))
        self.assertEqual(before, self.report())
        self.assertNotIn("field_position", before["cohort"])
        self.assertNotIn("field_position_filter", before["data_quality"])
        self.assertEqual(before["overall"]["plays"], 6)
        self.assertAlmostEqual(before["overall"]["epa_per_play"], 0.28)

    def test_hand_calculated_filtered_metrics_keep_missing_epa_in_play_counts(self):
        result = self.report(yardline_max=20, minimum_plays=3)
        metrics = result["overall"]
        self.assertEqual(metrics["plays"], 3)
        self.assertEqual(metrics["games"], 1)
        self.assertEqual(metrics["dropbacks"], 1)
        self.assertEqual(metrics["designed_runs"], 2)
        self.assertEqual(metrics["epa_observations"], 2)
        self.assertEqual(metrics["missing_epa"], 1)
        self.assertEqual(metrics["dropback_rate"], 1 / 3)
        self.assertAlmostEqual(metrics["epa_per_play"], 0.2)
        self.assertEqual(metrics["success_rate"], 0.5)
        self.assertFalse(metrics["small_sample"])
        self.assertTrue(metrics["small_epa_sample"])
        self.assertEqual(sum(r["plays"] for r in result["situations"]), 3)

    def test_effective_bounds_and_cohort_accounting_are_explicit(self):
        result = self.report(yardline_max=20)
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["cohort"]["field_position"], {
            "field": "yardline_100", "minimum_inclusive": 0, "maximum_inclusive": 20,
            "perspective": "offense", "missing_policy": "exclude",
        })
        quality = result["data_quality"]
        self.assertEqual(quality["field_position_filter"], {
            "plays_before_filter": 6, "missing_yardline_100": 1,
            "outside_range": 2, "plays_after_filter": 3,
        })
        self.assertEqual(quality["eligible_rows_outside_cohort"], 8)
        self.assertEqual(quality["input_rows"], result["overall"]["plays"]
                         + quality["eligible_rows_outside_cohort"]
                         + sum(quality["excluded_rows_by_reason"].values()))
        self.assertTrue(any("Missing yardline_100" in w for w in result["warnings"]))

    def test_both_bounds_are_inclusive_with_open_end_defaults_and_zero(self):
        for bounds, expected in (({"yardline_max": 20}, 3), ({"yardline_min": 50}, 1),
                                 ({"yardline_min": 20, "yardline_max": 20}, 1),
                                 ({"yardline_min": 20.5, "yardline_max": 20.5}, 1),
                                 ({"yardline_max": 0}, 1), ({"yardline_min": 100}, 1),
                                 ({"yardline_min": 0, "yardline_max": 100}, 5)):
            with self.subTest(bounds=bounds):
                self.assertEqual(self.report(**bounds)["overall"]["plays"], expected)
        # Requesting 0..100 still excludes unknown positions, unlike no filter.
        self.assertEqual(self.report()["overall"]["plays"], 6)

    def test_defense_uses_offense_coordinates_not_100_minus_yardline(self):
        result = self.report(team="ATL", side="defense", yardline_max=20)
        self.assertEqual(result["overall"]["plays"], 4)
        self.assertEqual(result["overall"]["games"], 2)
        self.assertEqual(result["overall"]["dropbacks"], 2)
        self.assertEqual(result["overall"]["epa_observations"], 3)
        self.assertAlmostEqual(result["overall"]["epa_per_play"], -0.2 / 3)
        self.assertEqual(result["overall"]["success_rate"], 1 / 3)
        self.assertEqual(result["metric_context"]["interpretation"], "allowed")
        self.assertEqual(result["data_quality"]["field_position_filter"]["plays_before_filter"], 7)

    def test_filter_preserves_exclusive_week_and_season_selection(self):
        for selection, expected in (({"before_week": 1}, 0), ({"before_week": 3}, 3),
                                    ({"before_week": 4}, 4), ({"season": 2025}, 1),
                                    ({"season_type": "POST", "before_week": 19}, 0),
                                    ({"season_type": "POST", "before_week": 23}, 1)):
            with self.subTest(selection=selection):
                self.assertEqual(self.report(yardline_max=20, **selection)["overall"]["plays"], expected)

    def test_reciprocal_matchup_has_identical_filtered_measurements(self):
        offense = self.report(before_week=2, yardline_max=20)
        defense = self.report(team="ATL", side="defense", before_week=2, yardline_max=20)
        for field in ("overall", "situations", "source", "data_quality"):
            self.assertEqual(offense[field], defense[field])

    def test_missingness_counts_are_scoped_after_team_and_time_selection(self):
        rows = self.rows.copy()
        for index in (6, 7, 8, 9, 11):
            rows[index] = dict(rows[index], yardline_100="NA")
        self.dataset = load_csv(self.write_rows(rows))
        result = self.report(yardline_max=20)
        self.assertEqual(result["data_quality"]["field_position_filter"], {
            "plays_before_filter": 6, "missing_yardline_100": 1,
            "outside_range": 2, "plays_after_filter": 3,
        })

    def test_present_column_with_empty_or_unmatched_cohort_returns_null_rates(self):
        for rows, changes in (([], {}), (self.rows, {"team": "GB"}),
                              (self.rows, {"yardline_min": 30, "yardline_max": 40})):
            with self.subTest(changes=changes):
                self.dataset = load_csv(self.write_rows(rows))
                result = self.report(**({"yardline_max": 20} | changes))
                self.assertEqual(result["overall"]["plays"], 0)
                self.assertEqual(result["situations"], [])
                for key in ("epa_per_play", "success_rate", "dropback_rate"):
                    self.assertIsNone(result["overall"][key])

    def test_invalid_api_bounds_never_silently_disable_the_filter(self):
        for name in ("yardline_min", "yardline_max"):
            for value in (-1, 101, float("nan"), float("inf"), True, "20", [], {}, 10**999):
                with self.subTest(name=name, value=value), self.assertRaisesRegex(ValueError, name):
                    self.report(**{name: value})
        with self.assertRaisesRegex(ValueError, "yardline_min.*yardline_max"):
            self.report(yardline_min=21, yardline_max=20)

    def test_cli_is_deterministic_and_invalid_filters_produce_no_partial_json(self):
        command = [sys.executable, "-m", "opponent_intelligence", "--csv", str(self.path),
                   "--team", "CAR", "--season", "2024", "--before-week", "3",
                   "--source-label", "Synthetic field-position records; not real NFL observations"]
        good = command + ["--yardline-max", "20"]
        first = subprocess.run(good, check=True, capture_output=True, text=True)
        second = subprocess.run(good, check=True, capture_output=True, text=True)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(json.loads(first.stdout)["overall"]["plays"], 3)
        for arguments in (("--yardline-min", "21", "--yardline-max", "20"),
                          ("--yardline-max", "nan"), ("--yardline-min", "-1")):
            with self.subTest(arguments=arguments):
                failed = subprocess.run(command + list(arguments), capture_output=True, text=True)
                self.assertEqual(failed.returncode, 2)
                self.assertEqual(failed.stdout, "")
                self.assertIn("error:", failed.stderr)
        self.write_rows(include_column=False)
        failed = subprocess.run(good, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(failed.stdout, "")
        self.assertIn("requires", failed.stderr)
        self.write_rows([self.rows[0], dict(self.rows[6], yardline_100="101")])
        failed = subprocess.run(good, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(failed.stdout, "")
        self.assertIn("CSV line 3: yardline_100:", failed.stderr)


if __name__ == "__main__":
    unittest.main()
