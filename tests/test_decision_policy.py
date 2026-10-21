"""Invented descriptive contrasts, never evidence of an NFL call's superiority."""

from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import json
import unittest
from unittest.mock import patch

from opponent_intelligence.decision import DecisionRequest, build_decision_evidence
from opponent_intelligence.pbp import Dataset, OPTIONAL_COLUMNS, Play


def invented_dataset(run_epa, pass_epa):
    rows = []
    for dropback, values in ((False, run_epa), (True, pass_epa)):
        for index, value in enumerate(values):
            rows.append(Play(
                game_id=f"SYNTHETIC_POLICY_{index:03}", play_id=len(rows),
                season=2024, season_type="REG", week=1, offense="CAR", defense="ATL",
                down=3, yards_to_go=4, dropback=dropback, epa=value,
                yardline_100=38, score_differential=-3, qtr=4, quarter_seconds_remaining=134,
            ))
    return Dataset(tuple(rows), "synthetic-policy-not-a-real-source", len(rows), {},
                   optional_columns=OPTIONAL_COLUMNS)


class DecisionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.request = DecisionRequest(team="CAR", season=2024, before_week=3,
                                       down=3, distance_min=4, distance_max=4)

    def evidence(self, dataset, **options):
        return build_decision_evidence(dataset, replace(self.request, **options),
                                       source_label="Invented policy tests; not NFL observations")

    def assert_abstention(self, comparison):
        self.assertEqual(comparison["status"], "insufficient_evidence")
        self.assertEqual(comparison["reason"], "candidate_comparison_not_validated")
        self.assertIsNone(comparison["preferred_candidate"])
        self.assertEqual(comparison["policy_version"], "descriptive_only_v1")
        self.assertEqual(comparison["opponent_evidence"],
                         {"status": "deferred", "reason": "opponent_conditioning_not_validated"})
        contrast = comparison["descriptive_contrast"]
        self.assertEqual(contrast["population"], "selected_offense")
        self.assertEqual(contrast["direction"], "pass_minus_run")
        self.assertEqual(contrast["uncertainty"], {"status": "not_implemented", "interval": None})

    def test_independent_hand_calculation_and_units(self):
        # Run: 3 plays, 2 observed EPA (0, -2). Pass: 2 observed EPA (1, 3).
        result = self.evidence(invented_dataset([0, -2, None], [1, 3]))
        comparison = result["comparison"]
        self.assert_abstention(comparison)
        self.assertEqual(comparison["descriptive_contrast"]["metrics"], {
            "frequency_pp": {"value": (2 / 5 - 3 / 5) * 100, "unit": "percentage_points",
                             "status": "available", "unavailable_candidates": {}},
            "epa_per_play": {"value": 3, "unit": "expected_points_per_observed_play",
                             "status": "available", "unavailable_candidates": {}},
            "success_rate_pp": {"value": 100, "unit": "percentage_points",
                                "status": "available", "unavailable_candidates": {}},
        })
        self.assertEqual([c["epa_observations"] for c in result["candidates"]], [2, 2])
        self.assertEqual([c["frequency_denominator"] for c in result["candidates"]], [5, 5])

    def test_negative_and_exact_zero_differences_are_available_not_abstention_tests(self):
        for run, passed, expected in (([2], [-1], -3), ([0], [0], 0), ([1], [1], 0)):
            with self.subTest(run=run, passed=passed):
                comparison = self.evidence(invented_dataset(run, passed))["comparison"]
                self.assert_abstention(comparison)
                metrics = comparison["descriptive_contrast"]["metrics"]
                self.assertEqual(metrics["epa_per_play"]["value"], expected)
                self.assertEqual(metrics["frequency_pp"]["value"], 0)
                self.assertTrue(all(m["status"] == "available" for m in metrics.values()))
                self.assertTrue(all(m["unavailable_candidates"] == {} for m in metrics.values()))

    def test_empty_cohort_has_nulls_and_both_candidate_reasons(self):
        comparison = self.evidence(invented_dataset([], []))["comparison"]
        self.assert_abstention(comparison)
        for metric in comparison["descriptive_contrast"]["metrics"].values():
            self.assertEqual(metric["status"], "unavailable")
            self.assertIsNone(metric["value"])
            self.assertEqual(metric["unavailable_candidates"], {"run": "empty_cohort", "pass": "empty_cohort"})

    def test_absent_candidate_keeps_real_zero_frequency_not_zero_outcomes(self):
        for run, passed, absent, frequency in (([], [1], "run", 100), ([1], [], "pass", -100)):
            with self.subTest(absent=absent):
                comparison = self.evidence(invented_dataset(run, passed))["comparison"]
                self.assert_abstention(comparison)
                metrics = comparison["descriptive_contrast"]["metrics"]
                self.assertEqual(metrics["frequency_pp"]["value"], frequency)
                self.assertEqual(metrics["frequency_pp"]["status"], "available")
                self.assertEqual(metrics["frequency_pp"]["unavailable_candidates"], {})
                for key in ("epa_per_play", "success_rate_pp"):
                    self.assertIsNone(metrics[key]["value"])
                    self.assertEqual(metrics[key]["status"], "unavailable")
                    self.assertEqual(metrics[key]["unavailable_candidates"], {absent: "unobserved_candidate"})

    def test_missing_epa_reasons_are_candidate_specific_and_never_inferred_from_zero(self):
        cases = (([None], [0], {"run": "missing_epa"}),
                 ([0], [None], {"pass": "missing_epa"}),
                 ([None], [None], {"run": "missing_epa", "pass": "missing_epa"}),
                 ([], [None], {"run": "unobserved_candidate", "pass": "missing_epa"}))
        for run, passed, reasons in cases:
            with self.subTest(reasons=reasons):
                metrics = self.evidence(invented_dataset(run, passed))["comparison"]["descriptive_contrast"]["metrics"]
                self.assertEqual(metrics["frequency_pp"]["status"], "available")
                for key in ("epa_per_play", "success_rate_pp"):
                    self.assertIsNone(metrics[key]["value"])
                    self.assertEqual(metrics[key]["status"], "unavailable")
                    self.assertEqual(metrics[key]["unavailable_candidates"], reasons)

    def test_threshold_and_large_count_cannot_unlock_ranking_or_hide_values(self):
        dataset = invented_dataset([0, -1, None] * 20, [3, 2, None] * 20)
        low = self.evidence(dataset, minimum_plays=1)
        high = self.evidence(dataset, minimum_plays=10000)
        self.assertTrue(all(not c["small_epa_sample"] for c in low["candidates"]))
        self.assertTrue(all(c["small_epa_sample"] for c in high["candidates"]))
        self.assertEqual(low["comparison"], high["comparison"])
        self.assert_abstention(low["comparison"])

    def test_nonoverlapping_ok_candidate_intervals_do_not_rank_or_supply_contrast_bounds(self):
        # 20 invented game clusters, each with three plays of each call.
        source = invented_dataset([i % 2 for i in range(20)], [3 + i % 2 for i in range(20)])
        rows = tuple(replace(p, play_id=p.play_id * 3 + copy) for p in source.plays for copy in range(3))
        result = self.evidence(replace(source, plays=rows, input_rows=len(rows)),
                               bootstrap_repetitions=200, bootstrap_seed=7)
        run, passed = [c["selected"]["epa_per_play"] for c in result["uncertainty"]["candidates"]]
        self.assertEqual((run["status"], passed["status"]), ("ok", "ok"))
        self.assertLess(run["interval"]["upper"], passed["interval"]["lower"])
        self.assertTrue(all(not c["small_epa_sample"] for c in result["candidates"]))
        self.assert_abstention(result["comparison"])

    def test_league_and_resampling_never_change_selected_contrast(self):
        selected = invented_dataset([-1, 0, None], [1, 3])
        expected = self.evidence(selected)["comparison"]
        # League EPA can be opposite or far larger without changing this comparison.
        for epa in (-100, 100):
            others = tuple(replace(p, play_id=p.play_id + 100, offense="ATL", defense="CAR", epa=epa)
                           for p in selected.plays)
            source = replace(selected, plays=selected.plays + others, input_rows=2 * selected.input_rows)
            for options in ({"compare_league": True}, {"bootstrap_repetitions": 200},
                            {"compare_league": True, "bootstrap_repetitions": 200, "bootstrap_seed": 9}):
                with self.subTest(epa=epa, options=options):
                    self.assertEqual(self.evidence(source, **options)["comparison"], expected)

    def test_baseline_never_fills_missing_selected_outcomes(self):
        source = invented_dataset([None], [None])
        others = tuple(replace(p, play_id=p.play_id + 100, offense="ATL", defense="CAR", epa=4)
                       for p in source.plays)
        both = replace(source, plays=source.plays + others, input_rows=4)
        self.assertEqual(self.evidence(both, compare_league=True)["comparison"], self.evidence(source)["comparison"])

    def test_only_current_exact_offense_cohort_supplies_the_comparison(self):
        source = invented_dataset([-1], [1])
        excluded = [replace(source.plays[1], **change, play_id=100 + index) for index, change in enumerate(
            ({"week": 3}, {"season": 2025}, {"season_type": "POST"}, {"offense": "NO"},
             {"down": 2}, {"yards_to_go": 5}, {"yardline_100": 39}, {"score_differential": 0},
             {"qtr": 5}, {"quarter_seconds_remaining": 135}))]
        bounds = dict(yardline_max=38, score_max=-3, period="Q4", clock_max=134)
        both = replace(source, plays=source.plays + tuple(excluded), input_rows=12)
        result = self.evidence(both, **bounds)
        self.assertEqual(result["population"]["plays"], 2)
        self.assertEqual(result["comparison"], self.evidence(source, **bounds)["comparison"])

    def test_opponent_and_defensive_decision_options_are_rejected_not_ignored(self):
        for key, value in (("opponent", "ATL"), ("side", "defense"), ("rank", True),
                           ("policy_version", "invented")):
            with self.subTest(key=key), self.assertRaises(TypeError):
                self.evidence(invented_dataset([-1], [1]), **{key: value})

    def test_opponent_identity_changes_do_not_create_matchup_adjustment(self):
        source = invented_dataset([-1], [1])
        other = replace(source, plays=tuple(replace(p, defense="NO") for p in source.plays))
        self.assertEqual(self.evidence(source)["comparison"], self.evidence(other)["comparison"])
        for options, changes in (({"down": 4}, {"down": 4}), ({"period": "OT"}, {"qtr": 5})):
            # Unsupported decision semantics cannot be unlocked by historical selectors.
            historical = replace(source, plays=tuple(replace(p, **changes) for p in source.plays))
            result = self.evidence(historical, **options)
            self.assertEqual(result["population"]["plays"], 2)
            self.assert_abstention(result["comparison"])

    def test_arithmetic_reconciles_with_exact_rational_expectations(self):
        samples = ([], [None], [0], [-2, 1], [1, None, 3], [0, 0, -1, 2])
        for run in samples:
            for passed in samples:
                result = self.evidence(invented_dataset(run, passed))["comparison"]
                self.assert_abstention(result)
                expected = {"frequency_pp": None, "epa_per_play": None, "success_rate_pp": None}
                if run or passed:
                    expected["frequency_pp"] = Fraction(100 * (len(passed) - len(run)), len(run) + len(passed))
                observed_run, observed_pass = ([v for v in values if v is not None] for values in (run, passed))
                if observed_run and observed_pass:
                    expected["epa_per_play"] = (Fraction(sum(observed_pass), len(observed_pass))
                                                - Fraction(sum(observed_run), len(observed_run)))
                    expected["success_rate_pp"] = 100 * (Fraction(sum(v > 0 for v in observed_pass), len(observed_pass))
                                                         - Fraction(sum(v > 0 for v in observed_run), len(observed_run)))
                for key, value in expected.items():
                    with self.subTest(run=run, passed=passed, metric=key):
                        actual = result["descriptive_contrast"]["metrics"][key]["value"]
                        if value is None:
                            self.assertIsNone(actual)
                        else:
                            self.assertAlmostEqual(actual, float(value), places=12)

    def test_result_is_isolated_reproducible_json_without_io_or_implicit_resampling(self):
        source = invented_dataset([-1, None], [1, 0])
        original = deepcopy(source)
        with patch("builtins.open", side_effect=AssertionError("no files")), \
             patch("socket.create_connection", side_effect=AssertionError("no network")), \
             patch("opponent_intelligence.decision.build_candidate_uncertainty", side_effect=AssertionError("no sampling")):
            first = self.evidence(source)
            second = self.evidence(replace(source, plays=tuple(reversed(source.plays))))
            self.assertEqual(first, second)
            self.assertEqual(json.loads(json.dumps(first, allow_nan=False)), first)
            first["comparison"]["descriptive_contrast"]["metrics"]["epa_per_play"]["value"] = 99
            first["comparison"]["opponent_evidence"]["status"] = "invented"
            self.assertEqual(self.evidence(source), second)
        self.assertEqual(source, original)


if __name__ == "__main__":
    unittest.main()
