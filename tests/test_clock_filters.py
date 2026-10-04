"""Invented pre-play clock situations, not real NFL observations."""

import csv
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from opponent_intelligence.pbp import DataValidationError, OPTIONAL_COLUMNS, REQUIRED_COLUMNS, load_csv
from opponent_intelligence.report import build_report


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_pbp.csv"


class ClockFilterTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "input.csv"
        with FIXTURE.open(newline="") as source:
            base = dict(next(csv.DictReader(source)), game_id="SYNTHETIC_CLOCK_A",
                        yardline_100="20", score_differential="-7", qtr="4",
                        quarter_seconds_remaining="120", game_seconds_remaining="999",
                        time="unused", end_clock_time="unused")
        self.rows = [
            dict(base, play_id="1", epa="0.8"),
            dict(base, play_id="2", quarter_seconds_remaining="0", score_differential="-1",
                 yardline_100="10", play_type="run", qb_dropback="0", down="2", ydstogo="3", epa="-0.4"),
            dict(base, play_id="3", quarter_seconds_remaining="121", score_differential="0", epa="0"),
            dict(base, play_id="4", quarter_seconds_remaining="900", score_differential="7",
                 yardline_100="80", play_type="run", qb_dropback="0", epa=""),
            dict(base, play_id="5", quarter_seconds_remaining="NA", epa="0.9"),
            dict(base, play_id="6", qtr="NA", quarter_seconds_remaining="NA", epa="0.1"),
            dict(base, play_id="7", qtr="NA", quarter_seconds_remaining="NA",
                 yardline_100="NA", score_differential="NA", epa="0.2"),
            dict(base, play_id="8", quarter_seconds_remaining="60", score_differential="0",
                 yardline_100="5", play_type="run", qb_dropback="0", down="3", ydstogo="5", epa=""),
            dict(base, play_id="9", qtr="2", quarter_seconds_remaining="60", epa="-0.2"),
            dict(base, play_id="10", qtr="5", quarter_seconds_remaining="60", epa="0.4"),
            dict(base, play_id="11", qtr="6", play_type="run", qb_dropback="0", epa="-0.6"),
            dict(base, play_id="12", quarter_seconds_remaining="60", score_differential="NA", epa="0.3"),
            dict(base, play_id="13", quarter_seconds_remaining="60", yardline_100="NA", epa="0.7"),
            dict(base, game_id="SYNTHETIC_TARGET", week="3", epa="99"),
            dict(base, game_id="SYNTHETIC_POST", season_type="POST", week="19", epa="9"),
            dict(base, game_id="SYNTHETIC_NEXT_YEAR", season="2025", epa="8"),
            dict(base, play_id="17", posteam="ATL", defteam="CAR", epa="5"),
            dict(base, play_id="18", play_type="no_play", qtr="unused", quarter_seconds_remaining="unused"),
            dict(base, game_id="SYNTHETIC_CLOCK_B", week="2", posteam="NO", epa="-0.6"),
        ]
        self.dataset = load_csv(self.write_rows())

    def write_rows(self, rows=None, *, omit=()):
        columns = REQUIRED_COLUMNS + OPTIONAL_COLUMNS + ("game_seconds_remaining", "time", "end_clock_time")
        columns = tuple(name for name in columns if name not in omit)
        with self.path.open("w", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=columns)
            writer.writeheader()
            writer.writerows({k: v for k, v in row.items() if k not in omit}
                             for row in (self.rows if rows is None else rows))
        return self.path

    def report(self, **changes):
        options = dict(team="CAR", season=2024, before_week=3,
                       source_label="Synthetic clock records; not real NFL observations")
        options.update(changes)
        return build_report(self.dataset, **options)

    def test_optional_time_values_are_exact_integers_and_preserve_zero(self):
        self.assertEqual(self.dataset.optional_columns, OPTIONAL_COLUMNS)
        self.assertEqual((self.dataset.plays[1].qtr, self.dataset.plays[1].quarter_seconds_remaining), (4, 0))
        for qtr, seconds, expected in (("+4.00", " 120.0 ", (4, 120)), ("6", "900", (6, 900)),
                                       ("9007199254740993", "-0", (9007199254740993, 0))):
            with self.subTest(qtr=qtr, seconds=seconds):
                play = load_csv(self.write_rows([dict(self.rows[0], qtr=qtr,
                                                    quarter_seconds_remaining=seconds)])).plays[0]
                self.assertEqual((play.qtr, play.quarter_seconds_remaining), expected)
                self.assertIs(type(play.qtr), int)
                self.assertIs(type(play.quarter_seconds_remaining), int)

    def test_missing_markers_do_not_become_zero_or_use_alternative_clocks(self):
        for field in ("qtr", "quarter_seconds_remaining"):
            for value in ("", " ", "NA", "nan", " null "):
                with self.subTest(field=field, value=value):
                    self.dataset = load_csv(self.write_rows([dict(self.rows[0], **{field: value})]))
                    self.assertIsNone(getattr(self.dataset.plays[0], field))
                    self.assertEqual(self.report()["overall"]["plays"], 1)
                    result = self.report(period="Q4", clock_max=120)
                    self.assertEqual(result["overall"]["plays"], 0)
                    quality = result["data_quality"]["period_filter" if field == "qtr" else "clock_filter"]
                    self.assertEqual(quality["missing_" + field], 1)
                    self.assertTrue(any("Missing " + field in w for w in result["warnings"]))

    def test_invalid_values_fail_on_eligible_rows_even_outside_cohort(self):
        malformed = ("1.1", "1.000000000000000001", "inf", "-inf", "+nan", "four", "1e2", "1_0", "４")
        for field, values in (("qtr", malformed + ("0", "-1")),
                              ("quarter_seconds_remaining", malformed + ("-1", "901"))):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaisesRegex(
                    DataValidationError, "CSV line 3: " + field + ":",
                ):
                    load_csv(self.write_rows([self.rows[0], dict(self.rows[13], **{field: value})]))

    def test_excluded_rows_do_not_require_valid_time_fields(self):
        for change in ({"play_type": "no_play"}, {"play_type": "NA"}, {"two_point_attempt": "1"},
                       {"qb_kneel": "1"}, {"qb_spike": "1"}):
            with self.subTest(change=change):
                dataset = load_csv(self.write_rows([dict(self.rows[0], qtr="unused",
                                                        quarter_seconds_remaining="unused", **change)]))
                self.assertEqual(dataset.plays, ())
                self.assertEqual(sum(dataset.exclusions.values()), 1)

    def test_absent_headers_are_distinct_from_missing_even_on_empty_cohorts(self):
        for field in ("qtr", "quarter_seconds_remaining"):
            for rows in (self.rows, []):
                self.dataset = load_csv(self.write_rows(rows, omit=(field,)))
                self.assertNotIn(field, self.dataset.optional_columns)
                for selection in ({}, {"team": "GB"}, {"yardline_max": 0}, {"score_max": -99}):
                    with self.subTest(field=field, selection=selection), self.assertRaisesRegex(
                        ValueError, "requires.*" + field,
                    ):
                        self.report(period="Q4", clock_max=120, **selection)

    def test_period_only_needs_no_clock_position_or_score_header(self):
        self.dataset = load_csv(self.write_rows(omit=("quarter_seconds_remaining", "yardline_100", "score_differential")))
        result = self.report(period="Q4")
        self.assertEqual(result["overall"]["plays"], 8)
        self.assertNotIn("clock", result["cohort"])
        self.assertNotIn("clock_filter", result["data_quality"])
        self.assertEqual(result["data_quality"]["filter_order"], ["period"])

    def test_regulation_periods_are_separate_from_every_overtime_period(self):
        for period, expected in (("Q1", 0), ("Q2", 1), ("Q3", 0), ("Q4", 8), ("OT", 2)):
            with self.subTest(period=period):
                result = self.report(period=period)
                self.assertEqual(result["overall"]["plays"], expected)
                lower = 5 if period == "OT" else int(period[1])
                self.assertEqual(result["cohort"]["period"], {
                    "field": "qtr", "label": period, "minimum_inclusive": lower,
                    "maximum_inclusive": None if period == "OT" else lower, "missing_policy": "exclude",
                })
        overtime = self.report(period="OT", clock_max=120)["overall"]
        self.assertEqual((overtime["plays"], overtime["dropbacks"]), (2, 1))
        self.assertAlmostEqual(overtime["epa_per_play"], -0.1)

    def test_clock_bounds_are_inclusive_and_omitted_ends_default_to_zero_or_900(self):
        cases = (({"clock_max": 120}, 5, 0, 120), ({"clock_min": 120}, 3, 120, 900),
                 ({"clock_min": 120, "clock_max": 120}, 1, 120, 120),
                 ({"clock_max": 0}, 1, 0, 0), ({"clock_min": 900}, 1, 900, 900),
                 ({"clock_min": 0}, 7, 0, 900))
        for bounds, count, lower, upper in cases:
            with self.subTest(bounds=bounds):
                result = self.report(period="Q4", **bounds)
                self.assertEqual(result["overall"]["plays"], count)
                self.assertEqual(result["cohort"]["clock"], {
                    "field": "quarter_seconds_remaining", "minimum_inclusive": lower,
                    "maximum_inclusive": upper, "unit": "seconds", "timing": "pre_play", "missing_policy": "exclude",
                })
        self.dataset = load_csv(self.write_rows([dict(self.rows[0], qtr="5", quarter_seconds_remaining="600"),
                                                dict(self.rows[1], qtr="6", quarter_seconds_remaining="900")]))
        self.assertEqual(self.report(period="OT", clock_min=600)["overall"]["plays"], 2)

    def test_clock_metrics_use_surviving_plays_and_observed_epa_denominators(self):
        result = self.report(period="Q4", clock_max=120, minimum_plays=5)
        metrics = result["overall"]
        self.assertAlmostEqual(metrics.pop("epa_per_play"), 0.35)
        self.assertEqual(metrics, {
            "plays": 5, "games": 1, "dropbacks": 3, "designed_runs": 2, "dropback_rate": 3 / 5,
            "epa_observations": 4, "missing_epa": 1, "success_rate": 3 / 4,
            "small_sample": False, "small_epa_sample": True,
        })
        self.assertEqual(result["data_quality"]["period_filter"], {
            "plays_before_filter": 13, "missing_qtr": 2, "outside_period": 3, "plays_after_filter": 8,
        })
        self.assertEqual(result["data_quality"]["clock_filter"], {
            "plays_before_filter": 8, "missing_quarter_seconds_remaining": 1, "outside_range": 2, "plays_after_filter": 5,
        })
        self.assertEqual(result["data_quality"]["filter_order"], ["period", "clock"])
        self.assertTrue(any("1 of 8" in w and "Missing quarter_seconds_remaining" in w for w in result["warnings"]))
        missing_epa = self.report(period="Q4", clock_min=900)["overall"]
        self.assertEqual((missing_epa["plays"], missing_epa["missing_epa"], missing_epa["dropback_rate"]), (1, 1, 0))
        self.assertIsNone(missing_epa["epa_per_play"])
        self.assertIsNone(missing_epa["success_rate"])

    def test_all_filters_remove_each_play_once_in_fixed_order(self):
        result = self.report(yardline_max=20, score_min=-7, score_max=0, period="Q4", clock_max=120, minimum_plays=3)
        quality = result["data_quality"]
        self.assertEqual(quality["filter_order"], ["field_position", "score_differential", "period", "clock"])
        self.assertEqual(quality["field_position_filter"], {
            "plays_before_filter": 13, "missing_yardline_100": 2, "outside_range": 1, "plays_after_filter": 10,
        })
        self.assertEqual(quality["score_differential_filter"], {
            "plays_before_filter": 10, "missing_score_differential": 1, "outside_range": 0, "plays_after_filter": 9,
        })
        self.assertEqual(quality["period_filter"], {
            "plays_before_filter": 9, "missing_qtr": 1, "outside_period": 3, "plays_after_filter": 5,
        })
        self.assertEqual(quality["clock_filter"], {
            "plays_before_filter": 5, "missing_quarter_seconds_remaining": 1, "outside_range": 1, "plays_after_filter": 3,
        })
        self.assertEqual(quality["input_rows"], 19)
        self.assertEqual(quality["eligible_rows_outside_cohort"], 15)
        self.assertEqual(quality["input_rows"], 3 + 15 + sum(quality["excluded_rows_by_reason"].values()))
        self.assertEqual((result["overall"]["dropbacks"], result["overall"]["epa_observations"]), (1, 2))
        self.assertAlmostEqual(result["overall"]["epa_per_play"], 0.2)
        self.assertEqual(result["overall"]["success_rate"], 1 / 2)
        self.assertFalse(result["overall"]["small_sample"])
        self.assertTrue(result["overall"]["small_epa_sample"])
        self.assertEqual([(r["down"], r["distance"], r["plays"]) for r in result["situations"]],
                         [(1, "long", 1), (2, "short", 1), (3, "medium", 1)])

    def test_defense_preserves_epa_sign_and_counts_multiple_opponents(self):
        result = self.report(team="ATL", side="defense", period="Q4", clock_max=120)
        metrics = result["overall"]
        self.assertEqual((metrics["plays"], metrics["games"], metrics["dropbacks"], metrics["epa_observations"]), (6, 2, 4, 5))
        self.assertAlmostEqual(metrics["epa_per_play"], 0.16)
        self.assertEqual(metrics["success_rate"], 3 / 5)
        self.assertEqual(result["metric_context"]["interpretation"], "allowed")
        offense = self.report(period="Q4", clock_max=120, before_week=2)
        defense = self.report(team="ATL", side="defense", period="Q4", clock_max=120, before_week=2)
        for key in ("overall", "situations", "source", "data_quality"):
            self.assertEqual(offense[key], defense[key])

    def test_week_season_type_and_role_boundaries_precede_time_filters(self):
        for selection, expected in (({"before_week": 1}, 0), ({"before_week": 3}, 5),
                                    ({"before_week": 4}, 6), ({"season": 2025}, 1),
                                    ({"season_type": "POST", "before_week": 19}, 0),
                                    ({"season_type": "POST", "before_week": 23}, 1), ({"side": "defense"}, 1)):
            with self.subTest(selection=selection):
                self.assertEqual(self.report(period="Q4", clock_max=120, **selection)["overall"]["plays"], expected)
        rows = self.rows.copy()
        for index in (13, 14, 15, 16, 18):
            rows[index] = dict(rows[index], qtr="NA", quarter_seconds_remaining="NA")
        self.dataset = load_csv(self.write_rows(rows))
        quality = self.report(period="Q4", clock_max=120)["data_quality"]
        self.assertEqual(quality["period_filter"]["missing_qtr"], 2)
        self.assertEqual(quality["clock_filter"]["missing_quarter_seconds_remaining"], 1)

    def test_no_time_filter_preserves_existing_reports_and_metadata(self):
        selections = ({}, {"yardline_max": 20}, {"score_max": 0}, {"yardline_max": 20, "score_max": 0})
        before = [self.report(**selection) for selection in selections]
        self.dataset = replace(self.dataset, plays=tuple(replace(p, qtr=None, quarter_seconds_remaining=None)
                                                        for p in self.dataset.plays))
        self.assertEqual(before, [self.report(period=None, clock_min=None, clock_max=None, **s) for s in selections])
        for result in before:
            for name in ("period", "clock"):
                self.assertNotIn(name, result["cohort"])
                self.assertNotIn(name + "_filter", result["data_quality"])
        self.dataset = load_csv(FIXTURE)
        self.assertEqual(self.report()["overall"]["plays"], 6)
        self.assertEqual(self.dataset.optional_columns, ())

    def test_only_source_period_clock_matters_not_alternative_or_end_clocks(self):
        before = self.report(period="Q4", clock_max=120)
        rows = [dict(row, time="00:00", game_seconds_remaining="0", end_clock_time="00:00") for row in self.rows]
        self.dataset = load_csv(self.write_rows(rows))
        after = self.report(period="Q4", clock_max=120)
        self.assertNotEqual(before.pop("source"), after.pop("source"))
        self.assertEqual(before, after)

    def test_empty_unmatched_and_fully_filtered_cohorts_have_null_rates(self):
        for rows, options in (([], {}), (self.rows, {"team": "GB"}), (self.rows, {"period": "Q1"}),
                              (self.rows, {"clock_min": 1, "clock_max": 59}), (self.rows, {"yardline_max": 0})):
            with self.subTest(options=options):
                self.dataset = load_csv(self.write_rows(rows))
                result = self.report(**({"period": "Q4", "clock_max": 120} | options))
                self.assertEqual(result["overall"]["plays"], 0)
                self.assertEqual(result["situations"], [])
                for key in ("epa_per_play", "success_rate", "dropback_rate"):
                    self.assertIsNone(result["overall"][key])

    def test_invalid_api_parameters_never_silently_disable_or_round_time_filters(self):
        for value in ("", "q4", "5", "Q5", 4, True, [], {}):
            with self.subTest(period=value), self.assertRaisesRegex(ValueError, "period must"):
                self.report(period=value)
        for name in ("clock_min", "clock_max"):
            with self.assertRaisesRegex(ValueError, "requires an explicit period"):
                self.report(**{name: 0})
            for value in (-1, 901, 0.0, 0.5, float("nan"), float("inf"), True, False, "0", [], {}):
                with self.subTest(name=name, value=value), self.assertRaisesRegex(ValueError, name):
                    self.report(period="Q4", **{name: value})
        with self.assertRaisesRegex(ValueError, "clock_min.*clock_max"):
            self.report(period="Q4", clock_min=121, clock_max=120)

    def test_cli_is_deterministic_flag_order_independent_and_all_or_nothing(self):
        command = [sys.executable, "-m", "opponent_intelligence", "--csv", str(self.path),
                   "--team", "CAR", "--season", "2024", "--before-week", "3",
                   "--source-label", "Synthetic clock records; not real NFL observations"]
        flags = [("--yardline-max", "20"), ("--score-max", "0"), ("--period", "Q4"), ("--clock-max", "120")]
        outputs = [subprocess.run(command + [value for pair in pairs for value in pair],
                                  check=True, capture_output=True, text=True).stdout
                   for pairs in (flags, flags, list(reversed(flags)))]
        self.assertEqual(outputs, [outputs[0]] * 3)
        self.assertEqual(json.loads(outputs[0]), self.report(yardline_max=20, score_max=0, period="Q4", clock_max=120))
        for flags in (["--clock-max", "120"], ["--period", "Q5"], ["--period", "q4"],
                      ["--period", "Q4", "--clock-max", "120.5"], ["--period", "Q4", "--clock-min", "-1"],
                      ["--period", "Q4", "--clock-min", "900", "--clock-max", "120"]):
            with self.subTest(flags=flags):
                failed = subprocess.run(command + flags, capture_output=True, text=True)
                self.assertEqual(failed.returncode, 2)
                self.assertEqual(failed.stdout, "")
                self.assertIn("error:", failed.stderr)
        self.write_rows(omit=("qtr",))
        failed = subprocess.run(command + ["--period", "Q4"], capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(failed.stdout, "")
        self.assertIn("requires the qtr", failed.stderr)
        self.write_rows([dict(self.rows[0], quarter_seconds_remaining="120.000000000000000001")])
        failed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(failed.stdout, "")
        self.assertIn("CSV line 2: quarter_seconds_remaining:", failed.stderr)


if __name__ == "__main__":
    unittest.main()
