"""Hand-calculated, explicitly synthetic leave-team-out league comparisons."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import unittest

from opponent_intelligence.pbp import Dataset, OPTIONAL_COLUMNS, Play
from opponent_intelligence.report import build_report


def play(identifier, **changes):
    base = Play(game_id="SYNTHETIC_A", play_id=identifier, season=2024,
                season_type="REG", week=1, offense="CAR", defense="ATL",
                down=1, yards_to_go=10, dropback=True, epa=1.0,
                yardline_100=20, score_differential=-7, qtr=4, quarter_seconds_remaining=120)
    return replace(base, **changes)


class LeagueComparisonTests(unittest.TestCase):
    def setUp(self):
        self.selected = [play(1), play(2, dropback=False, epa=None),
                         play(3, game_id="SYNTHETIC_B", week=2, defense="NO",
                              down=2, yards_to_go=2, epa=-1.0)]
        self.others = [
            play(4, offense="ATL", defense="CAR", dropback=False, epa=2.0),
            play(5, game_id="SYNTHETIC_C", offense="NO", defense="TB", epa=-1.0),
            play(6, game_id="SYNTHETIC_C", offense="NO", defense="TB", epa=0.0),
            play(7, game_id="SYNTHETIC_D", week=2, offense="NO", down=2,
                 yards_to_go=2, dropback=False, epa=0.0),
            play(8, game_id="SYNTHETIC_D", week=2, offense="NO", down=3, yards_to_go=5, epa=None),
        ]
        self.outside = [play(9, game_id="SYNTHETIC_FUTURE", week=3, epa=99),
                        play(10, game_id="SYNTHETIC_FUTURE", week=3, offense="SEA", defense="NE", epa=99),
                        play(11, game_id="SYNTHETIC_POST", season_type="POST", week=19, offense="SEA", defense="NE", epa=99),
                        play(12, game_id="SYNTHETIC_NEXT", season=2025, offense="SEA", defense="NE", epa=99),
                        play(13, game_id="SYNTHETIC_POST", season_type="POST", week=19, epa=99),
                        play(14, game_id="SYNTHETIC_NEXT", season=2025, epa=99)]
        self.set_plays(self.selected + self.others + self.outside)

    def set_plays(self, plays):
        self.dataset = Dataset(tuple(plays), "synthetic-fingerprint", len(plays) + 2,
                               {"kneel": 1, "non_run_pass": 1}, optional_columns=OPTIONAL_COLUMNS)

    def report(self, **changes):
        options = dict(team="CAR", season=2024, before_week=3, minimum_plays=3,
                       source_label="Synthetic typed records; not NFL observations", compare_league=True)
        options.update(changes)
        return build_report(self.dataset, **options)

    def test_hand_calculated_pooled_baseline_and_differences(self):
        result = self.report()
        baseline = result["league_comparison"]
        self.assertEqual(baseline["overall"], {
            "plays": 5, "games": 3, "dropbacks": 3, "designed_runs": 2, "dropback_rate": 3 / 5,
            "epa_observations": 4, "missing_epa": 1, "epa_per_play": 0.25, "success_rate": 1 / 4,
            "small_sample": False, "small_epa_sample": False,
        })
        difference = baseline["overall_difference"]
        self.assertAlmostEqual(difference["dropback_rate_pp"], 100 * (2 / 3 - 3 / 5))
        self.assertEqual(difference["success_rate_pp"], 25)
        self.assertEqual(difference["epa_per_play"], -0.25)
        # An unweighted mean of ATL's 0/1 and NO's 3/4 is 0.375, not pooled 3/5.
        self.assertNotEqual(baseline["overall"]["dropback_rate"], (0 + 3 / 4) / 2)
        self.assertEqual(result["overall"]["plays"], 3)

    def test_population_coverage_is_observed_not_assumed_and_games_can_overlap(self):
        comparison = self.report()["league_comparison"]
        self.assertEqual(comparison["population"], {
            "scope": "available_source_only", "side": "offense", "excluded_team": "CAR",
            "team_field": "posteam", "teams": ["ATL", "NO"], "team_count": 2,
            "weighting": "pooled_plays", "shared_games_with_selected": 1,
        })
        self.assertEqual(comparison["difference_convention"], "selected_minus_baseline")
        self.assertEqual(comparison["situation_scope"], "selected_team_observed_buckets")
        self.assertEqual(comparison["data_quality"], {
            "eligible_rows_same_season_type_before_week": 8, "excluded_selected_team_rows": 3,
            "plays_before_context_filters": 5, "plays_after_context_filters": 5, "filter_order": [],
        })
        self.assertTrue(any("coverage is not certified" in w for w in comparison["warnings"]))
        self.assertTrue(any("not opponent adjustment" in w for w in comparison["warnings"]))
        self.assertTrue(any("may share games" in w for w in comparison["warnings"]))

    def test_situations_match_down_and_distance_not_overall_league_rate(self):
        rows = self.report()["league_comparison"]["situations"]
        self.assertEqual([(r["down"], r["distance"]) for r in rows], [(1, "long"), (2, "short")])
        self.assertEqual(rows[0]["baseline"]["plays"], 3)
        self.assertAlmostEqual(rows[0]["baseline"]["epa_per_play"], 1 / 3)
        self.assertAlmostEqual(rows[0]["difference"]["epa_per_play"], 2 / 3)
        self.assertAlmostEqual(rows[0]["difference"]["dropback_rate_pp"], 100 * (1 / 2 - 2 / 3))
        self.assertEqual(rows[1]["baseline"]["plays"], 1)
        self.assertEqual(rows[1]["difference"], {"dropback_rate_pp": 100, "success_rate_pp": 0, "epa_per_play": -1})
        self.assertTrue(rows[1]["baseline"]["small_sample"])
        # Baseline-only third/medium is included overall but no target comparison row is invented.
        self.assertEqual(sum(r["baseline"]["plays"] for r in rows), 4)

    def test_unavailable_matching_bucket_never_falls_back_to_overall(self):
        self.set_plays(self.selected + [p for p in self.others if p.down != 2])
        row = self.report()["league_comparison"]["situations"][1]
        self.assertEqual(row["baseline"]["plays"], 0)
        self.assertTrue(row["baseline"]["small_sample"])
        self.assertEqual(row["difference"], dict.fromkeys(("dropback_rate_pp", "success_rate_pp", "epa_per_play")))

    def test_defense_excludes_selected_defense_not_the_opposite_role_or_epa_sign(self):
        result = self.report(side="defense")
        comparison = result["league_comparison"]
        self.assertEqual(result["overall"]["plays"], 1)
        self.assertEqual(comparison["overall"]["plays"], 7)
        self.assertEqual(comparison["population"]["teams"], ["ATL", "NO", "TB"])
        self.assertEqual(comparison["population"]["team_field"], "defteam")
        self.assertEqual(comparison["population"]["side"], "defense")
        self.assertEqual(comparison["population"]["shared_games_with_selected"], 1)
        self.assertAlmostEqual(comparison["overall"]["epa_per_play"], -0.2)
        self.assertAlmostEqual(comparison["overall_difference"]["epa_per_play"], 2.2)
        self.assertAlmostEqual(comparison["overall_difference"]["success_rate_pp"], 80)
        self.assertEqual(result["metric_context"]["interpretation"], "allowed")

    def test_baseline_uses_exclusive_week_season_and_season_type_boundaries(self):
        for options, selected, baseline in (({"before_week": 1}, 0, 0), ({"before_week": 3}, 3, 5),
                                            ({"before_week": 4}, 4, 6), ({"season": 2025}, 1, 1),
                                            ({"season_type": "POST", "before_week": 19}, 0, 0),
                                            ({"season_type": "POST", "before_week": 23}, 1, 1)):
            with self.subTest(options=options):
                result = self.report(**options)
                self.assertEqual(result["overall"]["plays"], selected)
                self.assertEqual(result["league_comparison"]["overall"]["plays"], baseline)
                self.assertEqual(result["league_comparison"]["cohort"],
                                 {k: v for k, v in result["cohort"].items() if k != "team"})

    def test_every_context_filter_has_separate_conditional_baseline_accounting(self):
        others = [play(100 + i, offense="NO") for i in range(10)]
        updates = (
            dict(yardline_100=None, score_differential=None, qtr=None, quarter_seconds_remaining=None),
            dict(yardline_100=80), dict(score_differential=None, qtr=None),
            dict(score_differential=7), dict(qtr=None, quarter_seconds_remaining=None),
            dict(qtr=2), dict(quarter_seconds_remaining=None), dict(quarter_seconds_remaining=121),
            dict(epa=0.4), dict(offense="ATL", defense="CAR", quarter_seconds_remaining=0, dropback=False, epa=None),
        )
        self.set_plays(self.selected + [replace(p, **change) for p, change in zip(others, updates)])
        result = self.report(yardline_max=20, score_min=-7, score_max=0, period="Q4", clock_max=120)
        comparison = result["league_comparison"]
        quality = comparison["data_quality"]
        order = ["field_position", "score_differential", "period", "clock"]
        self.assertEqual(quality["filter_order"], order)
        for name, field, before in zip(order, OPTIONAL_COLUMNS, (10, 8, 6, 4)):
            with self.subTest(name=name):
                self.assertEqual(quality[name + "_filter"], {
                    "plays_before_filter": before, "missing_" + field: 1,
                    "outside_period" if name == "period" else "outside_range": 1,
                    "plays_after_filter": before - 2,
                })
                self.assertEqual(result["data_quality"][name + "_filter"]["plays_after_filter"], 3)
        self.assertEqual(quality["eligible_rows_same_season_type_before_week"], 13)
        self.assertEqual(quality["excluded_selected_team_rows"], 3)
        self.assertEqual(quality["plays_before_context_filters"], 10)
        self.assertEqual(quality["plays_after_context_filters"], 2)
        self.assertEqual(comparison["overall"]["dropback_rate"], 0.5)
        self.assertEqual(comparison["overall"]["epa_per_play"], 0.4)
        self.assertEqual(comparison["overall"]["missing_epa"], 1)
        self.assertEqual(sum("surviving plays with missing" in w for w in comparison["warnings"]), 4)
        self.assertEqual(comparison["cohort"]["clock"], result["cohort"]["clock"])

    def test_baseline_applies_signed_fractional_and_overtime_bounds_identically(self):
        self.set_plays([replace(self.selected[0], qtr=5, yardline_100=20.5, score_differential=7)] + [
            replace(self.others[0], qtr=6, yardline_100=20.5, score_differential=7),
            replace(self.others[1], qtr=4, yardline_100=20.5, score_differential=7),
            replace(self.others[2], qtr=5, yardline_100=20.4, score_differential=7),
            replace(self.others[3], qtr=5, yardline_100=20.5, score_differential=-7),
        ])
        result = self.report(period="OT", clock_min=120, clock_max=120,
                             yardline_min=20.5, yardline_max=20.5, score_min=7)
        self.assertEqual(result["overall"]["plays"], 1)
        self.assertEqual(result["league_comparison"]["overall"]["plays"], 1)
        self.assertEqual(result["league_comparison"]["overall"]["epa_per_play"], 2)
        self.assertEqual(result["league_comparison"]["population"]["teams"], ["ATL"])
        self.assertEqual(result["league_comparison"]["population"]["team_count"], 1)

    def test_missing_context_is_retained_when_that_filter_is_omitted(self):
        self.set_plays(self.selected + [replace(p, yardline_100=None, score_differential=None,
                                               qtr=None, quarter_seconds_remaining=None) for p in self.others])
        self.assertEqual(self.report()["league_comparison"]["overall"]["plays"], 5)
        self.assertEqual(self.report(period="Q4")["league_comparison"]["overall"]["plays"], 0)
        self.set_plays(self.selected + [replace(p, quarter_seconds_remaining=None) for p in self.others])
        self.assertEqual(self.report(period="Q4")["league_comparison"]["overall"]["plays"], 5)
        self.assertEqual(self.report(period="Q4", clock_min=0)["league_comparison"]["overall"]["plays"], 0)

    def test_empty_selected_baseline_or_both_keep_undefined_differences_null(self):
        for plays, target_count, baseline_count in ((self.selected, 3, 0), (self.others, 0, 5), ([], 0, 0)):
            with self.subTest(target=target_count, baseline=baseline_count):
                self.set_plays(plays)
                result = self.report()
                comparison = result["league_comparison"]
                self.assertEqual(result["overall"]["plays"], target_count)
                self.assertEqual(comparison["overall"]["plays"], baseline_count)
                self.assertTrue(all(v is None for v in comparison["overall_difference"].values()))
                if not target_count:
                    self.assertEqual(comparison["situations"], [])
                if not baseline_count:
                    self.assertEqual(comparison["population"]["teams"], [])
                    self.assertEqual(comparison["population"]["shared_games_with_selected"], 0)
                    self.assertTrue(any("No eligible baseline" in w for w in comparison["warnings"]))

    def test_missing_epa_on_either_side_does_not_erase_dropback_comparison(self):
        for missing_side in ("selected", "baseline"):
            with self.subTest(missing_side=missing_side):
                self.set_plays([replace(p, epa=None) if (p.offense == "CAR") == (missing_side == "selected") else p
                                for p in self.selected + self.others])
                difference = self.report()["league_comparison"]["overall_difference"]
                self.assertIsNone(difference["epa_per_play"])
                self.assertIsNone(difference["success_rate_pp"])
                self.assertAlmostEqual(difference["dropback_rate_pp"], 100 * (2 / 3 - 3 / 5))

    def test_baseline_small_play_and_epa_samples_are_separate(self):
        comparison = self.report(minimum_plays=5)["league_comparison"]
        self.assertFalse(comparison["overall"]["small_sample"])
        self.assertTrue(comparison["overall"]["small_epa_sample"])
        self.assertTrue(all(r["baseline"]["small_sample"] for r in comparison["situations"]))

    def test_opt_in_adds_only_comparison_without_mutating_dataset_or_legacy_report(self):
        before = deepcopy(self.dataset)
        for filters in ({}, {"yardline_max": 20}, {"score_max": 0}, {"period": "Q4", "clock_max": 120}):
            with self.subTest(filters=filters):
                legacy = self.report(compare_league=False, **filters)
                enabled = self.report(**filters)
                comparison = enabled.pop("league_comparison")
                self.assertEqual(enabled, legacy)
                self.assertEqual(before, self.dataset)
                comparison["cohort"]["minimum_plays_warning"] = 999
                if "clock" in comparison["cohort"]:
                    comparison["cohort"]["clock"]["maximum_inclusive"] = 1
                self.assertEqual(enabled, legacy)
        options = dict(team="CAR", season=2024, before_week=3, minimum_plays=3,
                       source_label="Synthetic typed records; not NFL observations")
        self.assertEqual(build_report(self.dataset, **options), self.report(compare_league=False))

    def test_invalid_opt_in_values_and_unavailable_context_headers_fail(self):
        for value in (None, 0, 1, "true", "false", [], {}):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "compare_league must be a boolean"):
                self.report(compare_league=value)
        self.set_plays([])
        self.dataset = replace(self.dataset, optional_columns=())
        for filters in ({"yardline_max": 20}, {"score_max": 0}, {"period": "Q4"}):
            with self.subTest(filters=filters), self.assertRaisesRegex(ValueError, "requires"):
                self.report(**filters)

    def test_cli_uses_original_synthetic_fixture_deterministically(self):
        fixture = Path(__file__).parent / "fixtures" / "synthetic_pbp.csv"
        command = [sys.executable, "-m", "opponent_intelligence", "--csv", str(fixture),
                   "--source-label", "Synthetic verification fixture; not real NFL observations",
                   "--team", "CAR", "--season", "2024", "--before-week", "3"]
        plain = subprocess.run(command, check=True, capture_output=True, text=True)
        first = subprocess.run(command + ["--compare-league"], check=True, capture_output=True, text=True)
        second = subprocess.run(command + ["--compare-league"], check=True, capture_output=True, text=True)
        self.assertEqual(first.stdout, second.stdout)
        result = json.loads(first.stdout)
        comparison = result.pop("league_comparison")
        self.assertEqual(result, json.loads(plain.stdout))
        self.assertEqual(comparison["overall"]["plays"], 1)
        self.assertEqual(comparison["overall"]["epa_per_play"], 3)
        self.assertAlmostEqual(comparison["overall_difference"]["epa_per_play"], -2.96)
        failed = subprocess.run(command + ["--compare-league", "--clock-max", "120"], capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(failed.stdout, "")
        self.assertIn("requires an explicit period", failed.stderr)


if __name__ == "__main__":
    unittest.main()
