"""Independent, invented candidate-baseline examples; not real team evidence."""

import csv
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from opponent_intelligence.decision import DecisionRequest, build_decision_evidence
from opponent_intelligence.metrics import metric_difference
from opponent_intelligence.pbp import OPTIONAL_COLUMNS, REQUIRED_COLUMNS, load_csv


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_pbp.csv"
LABEL = "Invented league comparison test rows; not real NFL observations"


class DecisionLeagueTests(unittest.TestCase):
    def setUp(self):
        self.request = DecisionRequest(team="CAR", season=2024, before_week=3,
                                       down=3, distance_min=4, distance_max=4, compare_league=True)

    def dataset(self, changes):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "synthetic.csv"
        with FIXTURE.open(newline="") as handle:
            base = dict(next(csv.DictReader(handle)), game_id="SYNTHETIC_CAR_ATL",
                        down="3", ydstogo="4", yardline_100="38", score_differential="-3",
                        qtr="4", quarter_seconds_remaining="134", epa="2")
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=REQUIRED_COLUMNS + OPTIONAL_COLUMNS)
            writer.writeheader()
            for index, change in enumerate(changes, 1):
                row = dict(base, play_id=str(index))
                row.update(change)
                writer.writerow(row)
        return load_csv(path)

    def evidence(self, dataset, **changes):
        return build_decision_evidence(dataset, replace(self.request, **changes), source_label=LABEL)

    def pooled_dataset(self):
        atl = {"posteam": "ATL", "defteam": "CAR"}
        no = {"posteam": "NO", "defteam": "TB", "game_id": "SYNTHETIC_NO_TB"}
        run = {"play_type": "run", "qb_dropback": "0"}
        return self.dataset([
            {}, dict(run, epa="-1"), dict(run, epa="NA"),
            dict(atl, epa="1"), dict(atl, epa="-1"), dict(atl, epa="NA"),
            dict(no, epa="3"), dict(atl, **run, epa="0"), dict(no, **run, epa="NA"),
        ])

    def test_baseline_is_opt_in_and_does_not_change_selected_evidence(self):
        dataset = self.pooled_dataset()
        plain = self.evidence(dataset, compare_league=False)
        compared = self.evidence(dataset)
        self.assertNotIn("league_comparison", plain)
        self.assertIn("league_comparison", compared)
        del compared["league_comparison"]
        self.assertEqual(compared, plain)
        default = DecisionRequest(team="CAR", season=2024, before_week=3,
                                  down=3, distance_min=4, distance_max=4)
        self.assertFalse(default.compare_league)

    def test_compare_flag_rejects_truthy_or_falsy_non_booleans(self):
        dataset = self.dataset([])
        for value in (0, 1, "true", "false", None, [], {}, 1.0):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "compare_league must be a boolean"):
                self.evidence(dataset, compare_league=value)

    def test_original_fixture_has_one_matching_other_offense(self):
        result = self.evidence(load_csv(FIXTURE), down=1, distance_min=10, distance_max=10)
        league = result["league_comparison"]
        self.assertEqual(league["population"], {
            "scope": "available_source_only", "side": "offense", "team_field": "posteam",
            "excluded_team": "CAR", "weighting": "pooled_plays", "plays": 1, "games": 1,
            "teams": ["ATL"], "team_count": 1, "shared_games_with_selected": 1,
        })
        run, passed = league["candidates"]
        self.assertEqual((run["frequency"], passed["frequency"]), (0, 1))
        self.assertEqual((run["plays"], passed["plays"]), (0, 1))
        self.assertEqual(passed["epa_per_play"], 3)
        self.assertAlmostEqual(passed["difference"]["epa_per_play"], -2.4)
        self.assertAlmostEqual(run["difference"]["frequency_pp"], 100 / 3)
        self.assertAlmostEqual(passed["difference"]["frequency_pp"], -100 / 3)
        self.assertEqual(passed["difference"]["success_rate_pp"], 0)
        self.assertIsNone(run["difference"]["epa_per_play"])
        self.assertIsNone(run["difference"]["success_rate_pp"])
        self.assertEqual(run["availability"]["outcomes"], "unobserved_candidate")
        self.assertEqual(league["data_quality"]["excluded_selected_team_rows"], 6)
        self.assertEqual(league["data_quality"]["plays_before_context_filters"], 1)

    def test_hand_calculated_pooled_candidates_are_not_team_mean_averages(self):
        result = self.evidence(self.pooled_dataset(), minimum_plays=4)
        league = result["league_comparison"]
        run, passed = league["candidates"]
        # Pass: ATL EPA [1, -1, missing], NO [3]. Pool 3 observed EPA, not 2 team means.
        self.assertEqual((passed["plays"], passed["games"], passed["epa_observations"], passed["missing_epa"]), (4, 2, 3, 1))
        self.assertEqual(passed["epa_per_play"], 1)
        self.assertNotEqual(passed["epa_per_play"], (0 + 3) / 2)
        self.assertAlmostEqual(passed["success_rate"], 2 / 3)
        self.assertAlmostEqual(passed["frequency"], 4 / 6)
        self.assertEqual(passed["frequency_denominator"], 6)
        self.assertFalse(passed["small_sample"])
        self.assertTrue(passed["small_epa_sample"])
        self.assertEqual((run["plays"], run["games"], run["epa_observations"], run["missing_epa"]), (2, 2, 1, 1))
        self.assertEqual((run["epa_per_play"], run["success_rate"]), (0, 0))
        self.assertAlmostEqual(run["frequency"], 2 / 6)
        self.assertTrue(run["small_sample"])
        self.assertEqual((league["population"]["plays"], league["population"]["games"]), (6, 2))
        self.assertEqual(league["population"]["shared_games_with_selected"], 1)
        for candidate in (run, passed):
            self.assertEqual(candidate["coverage"], {"teams": ["ATL", "NO"], "team_count": 2,
                                                      "shared_games_with_selected_candidate": 1})
        self.assertEqual(result["population"], {"plays": 3, "games": 1})

    def test_candidate_differences_have_explicit_units_direction_and_denominators(self):
        league = self.evidence(self.pooled_dataset())["league_comparison"]
        run, passed = league["candidates"]
        self.assertEqual(league["difference_convention"], "selected_minus_baseline")
        self.assertEqual(league["difference_units"], {"frequency_pp": "percentage_points",
                                                      "epa_per_play": "expected_points_per_observed_play",
                                                      "success_rate_pp": "percentage_points"})
        self.assertAlmostEqual(run["difference"]["frequency_pp"], 100 / 3)
        self.assertAlmostEqual(passed["difference"]["frequency_pp"], -100 / 3)
        self.assertEqual(run["difference"]["epa_per_play"], -1)
        self.assertEqual(run["difference"]["success_rate_pp"], 0)
        self.assertEqual(passed["difference"]["epa_per_play"], 1)
        self.assertAlmostEqual(passed["difference"]["success_rate_pp"], 100 / 3)

    def test_exact_matching_rejects_other_times_types_downs_distances_and_contexts(self):
        other = {"posteam": "ATL", "defteam": "CAR", "epa": "99"}
        excluded = ({"season": "2025"}, {"week": "3"}, {"season_type": "POST"},
                    {"down": "2"}, {"ydstogo": "5"}, {"yardline_100": "39"},
                    {"score_differential": "-2"}, {"qtr": "3"}, {"quarter_seconds_remaining": "135"})
        dataset = self.dataset([{}, dict(other, epa="-0.5"), *[dict(other, **change) for change in excluded]])
        result = self.evidence(dataset, yardline_min=38, yardline_max=38, score_min=-3, score_max=-3,
                               period="Q4", clock_min=134, clock_max=134)
        league = result["league_comparison"]
        self.assertEqual(league["population"]["plays"], 1)
        self.assertEqual(league["candidates"][1]["epa_per_play"], -0.5)
        self.assertEqual(league["cohort"], {key: value for key, value in result["cohort"].items() if key != "team"})
        self.assertEqual(league["data_quality"]["eligible_rows_same_season_type_before_week"], 8)

    def test_unmatched_baseline_never_uses_nearby_bucket_or_overall_values(self):
        for changes in ([{"ydstogo": "5"}], [{"down": "2"}], [{"ydstogo": "5"}, {"down": "2"}]):
            with self.subTest(changes=changes):
                dataset = self.dataset([{}, *[dict(change, posteam="ATL", defteam="CAR") for change in changes]])
                league = self.evidence(dataset)["league_comparison"]
                self.assertEqual(league["population"]["plays"], 0)
                self.assertEqual(league["population"]["teams"], [])
                for candidate in league["candidates"]:
                    self.assertEqual(candidate["availability"], {"frequency": "empty_cohort", "outcomes": "empty_cohort"})
                    self.assertIsNone(candidate["frequency"])
                    self.assertTrue(all(value is None for value in candidate["difference"].values()))

    def test_requested_distance_range_includes_both_endpoints_without_reweighting(self):
        dataset = self.dataset([{}, *[{"posteam": "ATL", "defteam": "CAR", "ydstogo": str(distance),
                                      "epa": str(distance)} for distance in (3, 4, 5, 6)]])
        league = self.evidence(dataset, distance_min=3, distance_max=5)["league_comparison"]
        self.assertEqual(league["population"]["plays"], 3)
        self.assertEqual(league["candidates"][1]["epa_per_play"], 4)
        self.assertEqual(league["cohort"]["distance"]["minimum_inclusive"], 3)
        self.assertEqual(league["cohort"]["distance"]["maximum_inclusive"], 5)
        self.assertTrue(any("context mixes within requested ranges may differ" in w for w in league["warnings"]))

    def test_overtime_zero_clock_matches_both_populations_and_all_recorded_ot_periods(self):
        other = {"posteam": "ATL", "defteam": "CAR"}
        dataset = self.dataset([{"qtr": "5", "quarter_seconds_remaining": "0"},
                                *[dict(other, qtr=str(qtr), quarter_seconds_remaining=str(clock))
                                  for qtr, clock in ((4, 0), (5, 0), (6, 0), (6, 1))]])
        result = self.evidence(dataset, period="OT", clock_min=0, clock_max=0)
        self.assertEqual(result["population"]["plays"], 1)
        self.assertEqual(result["league_comparison"]["population"]["plays"], 2)
        ledger = result["league_comparison"]["data_quality"]
        self.assertEqual(ledger["period_filter"]["outside_period"], 1)
        self.assertEqual(ledger["clock_filter"]["outside_range"], 1)
        self.assertIsNone(result["league_comparison"]["cohort"]["period"]["maximum_inclusive"])

    def test_absent_baseline_candidate_zero_frequency_is_not_zero_efficiency(self):
        dataset = self.dataset([{"play_type": "run", "qb_dropback": "0"},
                                {"posteam": "ATL", "defteam": "CAR"}])
        run, passed = self.evidence(dataset)["league_comparison"]["candidates"]
        self.assertEqual(run["frequency"], 0)
        self.assertEqual(run["difference"]["frequency_pp"], 100)
        self.assertIsNone(run["epa_per_play"])
        self.assertIsNone(run["difference"]["epa_per_play"])
        self.assertEqual(passed["difference"]["frequency_pp"], -100)
        self.assertIsNone(passed["difference"]["success_rate_pp"])

    def test_missing_baseline_epa_keeps_frequency_and_blocks_outcome_differences(self):
        dataset = self.dataset([{}, {"posteam": "ATL", "defteam": "CAR", "epa": "NA"}])
        league = self.evidence(dataset)["league_comparison"]
        passed = league["candidates"][1]
        self.assertEqual((passed["plays"], passed["games"], passed["missing_epa"], passed["frequency"]), (1, 1, 1, 1))
        self.assertEqual(passed["availability"]["outcomes"], "missing_epa")
        self.assertEqual(passed["difference"], {"frequency_pp": 0, "epa_per_play": None, "success_rate_pp": None})
        self.assertTrue(any("Missing baseline EPA" in warning for warning in league["warnings"]))

    def test_missing_selected_epa_never_borrows_baseline_outcomes(self):
        dataset = self.dataset([{"epa": "NA"}, {"posteam": "ATL", "defteam": "CAR"}])
        result = self.evidence(dataset)
        self.assertEqual(result["candidates"][1]["availability"]["outcomes"], "missing_epa")
        passed = result["league_comparison"]["candidates"][1]
        self.assertEqual(passed["epa_per_play"], 2)
        self.assertIsNone(passed["difference"]["epa_per_play"])
        self.assertIsNone(passed["difference"]["success_rate_pp"])

    def test_empty_selected_cohort_preserves_baseline_without_inventing_selected_evidence(self):
        dataset = self.dataset([{"posteam": "ATL", "defteam": "CAR"}])
        result = self.evidence(dataset)
        self.assertEqual(result["population"], {"plays": 0, "games": 0})
        self.assertEqual(result["league_comparison"]["population"]["plays"], 1)
        self.assertEqual(result["league_comparison"]["candidates"][1]["epa_per_play"], 2)
        for candidate in result["league_comparison"]["candidates"]:
            self.assertTrue(all(value is None for value in candidate["difference"].values()))
        self.assertEqual(result["league_comparison"]["population"]["shared_games_with_selected"], 0)

    def test_empty_source_or_only_selected_team_produces_empty_baseline(self):
        for dataset in (self.dataset([]), self.dataset([{}])):
            with self.subTest(input_rows=dataset.input_rows):
                league = self.evidence(dataset)["league_comparison"]
                self.assertEqual(league["population"]["plays"], 0)
                self.assertEqual(league["population"]["team_count"], 0)
                for candidate in league["candidates"]:
                    self.assertEqual(candidate["frequency_denominator"], 0)
                    self.assertIsNone(candidate["frequency"])
                    self.assertTrue(all(value is None for value in candidate["difference"].values()))

    def test_coverage_is_filtered_candidate_specific_and_excludes_offense_not_games(self):
        dataset = self.dataset([
            {}, {"play_type": "run", "qb_dropback": "0"},
            {"posteam": "ATL", "defteam": "CAR", "play_type": "run", "qb_dropback": "0"},
            {"posteam": "NO", "defteam": "TB", "game_id": "SYNTHETIC_NO_TB", "epa": "NA"},
            {"posteam": "BAL", "defteam": "PIT", "game_id": "SYNTHETIC_BAL_PIT"},
            {"posteam": "TB", "defteam": "NO", "game_id": "SYNTHETIC_NO_TB", "ydstogo": "5"},
        ])
        league = self.evidence(dataset)["league_comparison"]
        self.assertEqual(league["population"]["teams"], ["ATL", "BAL", "NO"])
        self.assertEqual(league["population"]["games"], 3)
        self.assertEqual(league["population"]["shared_games_with_selected"], 1)
        run, passed = league["candidates"]
        self.assertEqual(run["coverage"], {"teams": ["ATL"], "team_count": 1, "shared_games_with_selected_candidate": 1})
        self.assertEqual(passed["coverage"], {"teams": ["BAL", "NO"], "team_count": 2, "shared_games_with_selected_candidate": 0})
        self.assertEqual((passed["games"], passed["epa_observations"], passed["missing_epa"]), (2, 1, 1))

    def test_candidate_mapping_also_counts_baseline_scramble_as_pass(self):
        dataset = self.dataset([{}, {"posteam": "ATL", "defteam": "CAR", "play_type": "run", "qb_dropback": "1"}])
        run, passed = self.evidence(dataset)["league_comparison"]["candidates"]
        self.assertEqual((run["plays"], passed["plays"]), (0, 1))
        self.assertEqual((run["frequency"], passed["frequency"]), (0, 1))

    def test_independent_population_ledgers_and_ordered_missingness_reconcile(self):
        other = {"posteam": "ATL", "defteam": "CAR"}
        changes = ({}, {"yardline_100": "NA", "score_differential": "NA"},
                   {"yardline_100": "39"}, {"score_differential": "NA"}, {"score_differential": "-2"},
                   {"qtr": "NA"}, {"qtr": "3"}, {"quarter_seconds_remaining": "NA"},
                   {"quarter_seconds_remaining": "135"}, {"down": "2"}, {"ydstogo": "5"})
        dataset = self.dataset([{}, {"yardline_100": "NA"}, *[dict(other, **change) for change in changes],
                                {"play_type": "no_play"}])
        result = self.evidence(dataset, yardline_min=38, yardline_max=38, score_min=-3, score_max=-3,
                               period="Q4", clock_min=134, clock_max=134)
        ledger = result["league_comparison"]["data_quality"]
        self.assertEqual((ledger["eligible_rows_same_season_type_before_week"], ledger["excluded_selected_team_rows"],
                          ledger["plays_before_context_filters"], ledger["plays_after_context_filters"]), (13, 2, 11, 1))
        self.assertEqual(ledger["filter_order"], ["field_position", "score_differential", "period", "clock", "down", "distance"])
        previous = 11
        for name in ledger["filter_order"]:
            stage = ledger[name + "_filter"]
            field = result["cohort"][name]["field"]
            self.assertEqual(stage["plays_before_filter"], previous)
            self.assertEqual(previous, stage["missing_" + field] + stage["outside_period" if name == "period" else "outside_range"]
                             + stage["plays_after_filter"])
            previous = stage["plays_after_filter"]
        self.assertEqual(ledger["score_differential_filter"]["missing_score_differential"], 1)
        self.assertEqual(result["data_quality"]["field_position_filter"]["plays_before_filter"], 2)
        self.assertEqual(result["data_quality"]["input_rows"], 14)
        self.assertEqual(result["data_quality"]["excluded_rows_by_reason"], {"non_run_pass": 1})
        self.assertEqual(result["data_quality"]["eligible_rows_outside_cohort"], 12)
        self.assertEqual(len([w for w in result["league_comparison"]["warnings"] if "no imputation" in w]), 4)

    def test_cohort_metadata_is_copied_not_aliased_and_provenance_remains_full_source(self):
        dataset = self.pooled_dataset()
        result = self.evidence(dataset)
        self.assertEqual(result["source"], {"label": LABEL, "sha256": dataset.source_sha256})
        self.assertEqual(result["data_quality"]["input_rows"], 9)
        result["league_comparison"]["cohort"]["down"]["minimum_inclusive"] = 4
        result["league_comparison"]["data_quality"]["filter_order"].append("invented")
        result["league_comparison"]["candidates"][1]["mapping"]["equals"] = 9
        self.assertEqual(result["cohort"]["down"]["minimum_inclusive"], 3)
        self.assertEqual(result["data_quality"]["filter_order"], ["down", "distance"])
        self.assertEqual(result["candidates"][1]["mapping"]["equals"], 1)

    def test_comparison_remains_withheld_even_with_defined_differences_and_clear_count_flags(self):
        dataset = self.pooled_dataset()
        with patch("builtins.open", side_effect=AssertionError("unexpected file IO")), \
             patch("socket.create_connection", side_effect=AssertionError("unexpected network IO")):
            first = self.evidence(dataset, minimum_plays=1)
            second = self.evidence(dataset, minimum_plays=1)
        self.assertEqual(first, second)
        self.assertEqual(json.loads(json.dumps(first, allow_nan=False)), first)
        self.assertTrue(all(not c["small_epa_sample"] for c in first["league_comparison"]["candidates"]))
        self.assertEqual({key: first["comparison"][key] for key in
                          ("status", "preferred_candidate", "reason")},
                         {"status": "insufficient_evidence", "preferred_candidate": None,
                          "reason": "candidate_comparison_not_validated"})
        self.assertNotIn("uncertainty", first)
        self.assertNotIn("uncertainty", first["league_comparison"])

    def test_shared_metric_difference_preserves_zero_and_propagates_undefined_values(self):
        self.assertEqual(metric_difference(0, 0), 0)
        self.assertEqual(metric_difference(0.25, 0.5, scale=100), -25)
        self.assertEqual(metric_difference(1, -1), 2)
        for left, right in ((None, 0), (0, None), (None, None)):
            self.assertIsNone(metric_difference(left, right, scale=100))


if __name__ == "__main__":
    unittest.main()
