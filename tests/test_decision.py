"""Hand-calculated, invented situations; no real NFL performance claims."""

import csv
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from opponent_intelligence.cohort import context_filters, filter_context, select_population
from opponent_intelligence.decision import DecisionRequest, build_decision_evidence
from opponent_intelligence.pbp import OPTIONAL_COLUMNS, REQUIRED_COLUMNS, load_csv
from opponent_intelligence.report import build_report


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_pbp.csv"
LABEL = "Invented decision test situations; not real NFL observations"


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.dataset = load_csv(FIXTURE)
        self.request = DecisionRequest(team="CAR", season=2024, before_week=3,
                                       down=1, distance_min=10, distance_max=10)

    def evidence(self, dataset=None, **changes):
        return build_decision_evidence(self.dataset if dataset is None else dataset,
                                       replace(self.request, **changes), source_label=LABEL)

    def contextual_dataset(self, changes, *, omit=()):
        """Load independently authored rows through the production CSV adapter."""
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "synthetic.csv"
        with FIXTURE.open(newline="") as handle:
            base = dict(next(csv.DictReader(handle)), game_id="SYNTHETIC_DECISION_A",
                        down="3", ydstogo="4", yardline_100="38", score_differential="-3",
                        qtr="4", quarter_seconds_remaining="134", epa="0.5")
        columns = tuple(field for field in REQUIRED_COLUMNS + OPTIONAL_COLUMNS if field not in omit)
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for index, change in enumerate(changes, 1):
                row = dict(base, play_id=str(index))
                row.update(change)
                writer.writerow({key: value for key, value in row.items() if key in columns})
        return load_csv(path)

    def test_exact_first_and_ten_candidate_counts_and_outcomes(self):
        result = self.evidence()
        run, passed = result["candidates"]
        self.assertEqual(result["contract_version"], 1)
        self.assertNotIn("schema_version", result)
        self.assertEqual(result["population"], {"plays": 3, "games": 2})
        self.assertEqual((run["candidate"], passed["candidate"]), ("run", "pass"))
        self.assertEqual((run["plays"], run["games"], passed["plays"], passed["games"]), (1, 1, 2, 1))
        self.assertAlmostEqual(run["frequency"], 1 / 3)
        self.assertAlmostEqual(passed["frequency"], 2 / 3)
        self.assertEqual((run["frequency_denominator"], passed["frequency_denominator"]), (3, 3))
        self.assertEqual((run["epa_per_play"], run["success_rate"], run["epa_observations"]), (0, 0, 1))
        self.assertAlmostEqual(passed["epa_per_play"], 0.6)
        self.assertEqual((passed["success_rate"], passed["epa_observations"]), (1, 2))
        self.assertEqual(passed["availability"], {"frequency": "available", "outcomes": "available"})
        self.assertEqual(result["metric_context"], {"perspective": "offense", "interpretation": "produced",
                                                    "success_condition": "epa > 0", "frequency_unit": "proportion"})

    def test_scramble_shaped_run_and_sack_shaped_pass_stay_in_pass(self):
        # The existing fixture's run/qb_dropback=1 is not a designed Run.
        self.assertEqual(self.evidence()["candidates"][1]["plays"], 2)
        run, passed = self.evidence(down=3, distance_min=7, distance_max=7)["candidates"]
        self.assertEqual((run["plays"], passed["plays"]), (0, 1))
        self.assertEqual((passed["epa_per_play"], passed["success_rate"]), (-1.2, 0))
        self.assertEqual(run["mapping"], {"source_field": "qb_dropback", "equals": 0})
        self.assertEqual(passed["mapping"], {"source_field": "qb_dropback", "equals": 1})

    def test_exact_distance_does_not_use_scout_buckets(self):
        dataset = self.contextual_dataset([{"ydstogo": str(distance)} for distance in (3, 4, 5, 6)])
        self.assertEqual(self.evidence(dataset, down=3, distance_min=4, distance_max=4)["population"]["plays"], 1)
        self.assertEqual(self.evidence(dataset, down=3, distance_min=4, distance_max=5)["population"]["plays"], 2)
        empty = self.evidence(dataset, down=3, distance_min=7, distance_max=7)
        self.assertEqual(empty["population"]["plays"], 0)
        self.assertTrue(any("no widening" in warning for warning in empty["warnings"]))

    def test_down_and_distance_extremes_are_exact_historical_selectors(self):
        for down in range(1, 5):
            for distance in (0, 100):
                with self.subTest(down=down, distance=distance):
                    dataset = self.contextual_dataset([{"down": str(down), "ydstogo": str(distance)}])
                    result = self.evidence(dataset, down=down, distance_min=distance, distance_max=distance)
                    self.assertEqual(result["population"]["plays"], 1)
                    self.assertEqual(result["cohort"]["down"]["minimum_inclusive"], down)

    def test_temporal_team_and_season_type_selection_is_exclusive(self):
        for changes, plays, epa in (({"before_week": 2}, 2, 0.6),
                                   ({"before_week": 3}, 3, 0.6),
                                   ({"before_week": 4}, 4, (0.8 + 0.4 + 8) / 3),
                                   ({"season": 2025}, 1, 5),
                                   ({"season_type": "POST", "before_week": 20}, 1, 6),
                                   ({"team": "ATL"}, 1, 3)):
            with self.subTest(changes=changes):
                result = self.evidence(**changes)
                self.assertEqual(result["population"]["plays"], plays)
                self.assertAlmostEqual(result["candidates"][1]["epa_per_play"], epa)
        self.assertEqual(self.evidence(season_type="POST", before_week=19)["population"]["plays"], 0)

    def test_ingestion_and_filter_accounting_preserves_full_source(self):
        result = self.evidence()
        quality = result["data_quality"]
        self.assertEqual((quality["input_rows"], quality["eligible_rows_all_teams"],
                          quality["eligible_rows_same_season_type_before_week"],
                          quality["team_plays_before_context_filters"],
                          quality["eligible_rows_outside_cohort"]), (14, 10, 7, 6, 7))
        self.assertEqual(quality["excluded_rows_by_reason"],
                         {"kneel": 1, "non_run_pass": 1, "spike": 1, "two_point_attempt": 1})
        self.assertEqual(quality["filter_order"], ["down", "distance"])
        self.assertEqual(quality["down_filter"], {"plays_before_filter": 6, "missing_down": 0,
                                                 "outside_range": 3, "plays_after_filter": 3})
        self.assertEqual(sum(c["plays"] for c in result["candidates"]), result["population"]["plays"])

    def test_absent_candidate_frequency_zero_but_outcomes_unavailable(self):
        run, _ = self.evidence(down=3, distance_min=7, distance_max=7)["candidates"]
        self.assertEqual((run["frequency"], run["frequency_denominator"], run["games"]), (0, 1, 0))
        self.assertIsNone(run["epa_per_play"])
        self.assertIsNone(run["success_rate"])
        self.assertEqual(run["availability"], {"frequency": "available", "outcomes": "unobserved_candidate"})

    def test_empty_parent_has_null_not_zero_frequencies(self):
        for changes in ({"before_week": 1}, {"team": "GB"}, {"down": 4}):
            with self.subTest(changes=changes):
                result = self.evidence(**changes)
                self.assertEqual(result["population"], {"plays": 0, "games": 0})
                for candidate in result["candidates"]:
                    self.assertEqual(candidate["frequency_denominator"], 0)
                    for name in ("frequency", "epa_per_play", "success_rate"):
                        self.assertIsNone(candidate[name])
                    self.assertEqual(candidate["availability"], {"frequency": "empty_cohort", "outcomes": "empty_cohort"})

    def test_all_missing_epa_does_not_remove_call_frequency(self):
        run, passed = self.evidence(down=2, distance_min=6, distance_max=6)["candidates"]
        self.assertEqual((run["plays"], run["games"], run["frequency"], run["missing_epa"]), (1, 1, 1, 1))
        self.assertEqual(run["epa_observations"], 0)
        self.assertIsNone(run["epa_per_play"])
        self.assertIsNone(run["success_rate"])
        self.assertEqual(run["availability"]["outcomes"], "missing_epa")
        self.assertEqual(passed["availability"]["outcomes"], "unobserved_candidate")

    def test_partial_missing_epa_and_small_sample_denominators(self):
        run, passed = self.evidence(down=2, distance_min=3, distance_max=6,
                                    minimum_plays=2)["candidates"]
        self.assertEqual((run["plays"], run["epa_observations"], run["missing_epa"]), (2, 1, 1))
        self.assertEqual((run["frequency"], run["epa_per_play"], run["success_rate"]), (1, 0.2, 1))
        self.assertFalse(run["small_sample"])
        self.assertTrue(run["small_epa_sample"])
        self.assertTrue(passed["small_sample"])

    def test_warning_threshold_never_unlocks_a_preferred_call(self):
        result = self.evidence(minimum_plays=1)
        self.assertTrue(all(not c["small_sample"] and not c["small_epa_sample"] for c in result["candidates"]))
        self.assertEqual(result["estimation_policy"], {"frequency_minimum_parent_plays": 1,
                                                       "outcome_minimum_epa_observations": 1,
                                                       "minimum_plays_warning": 1})
        self.assertEqual(result["comparison"], {"status": "insufficient_evidence", "preferred_candidate": None,
                                                "reason": "candidate_comparison_not_validated"})
        self.assertNotIn("league_comparison", result)
        self.assertNotIn("uncertainty", result)
        self.assertTrue(any("not implemented" in warning for warning in result["warnings"]))

    def test_invalid_core_request_values_fail_without_coercion(self):
        invalid = {
            "down": (True, 0, 5, 3.0, "3", None),
            "distance_min": (False, -1, 101, 4.0, "4", None),
            "distance_max": (True, -1, 101, 4.0, "4", None),
            "season": (True, 1998, 10000, "2024", 2024.0, None),
            "before_week": (True, 0, 24, 3.0, "3", None),
            "season_type": ("reg", "PRE", None, []),
            "minimum_plays": (True, 0, -1, 30.0, "30", None),
            "team": ("car", "C", "C4R", "CAR ", None, 1, []),
        }
        for field, values in invalid.items():
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.evidence(**{field: value})
        with self.assertRaisesRegex(ValueError, "distance_min must not exceed"):
            self.evidence(distance_min=11, distance_max=10)

    def test_source_label_and_request_type_are_required(self):
        for value in (None, "", "  ", 123):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "source_label"):
                build_decision_evidence(self.dataset, self.request, source_label=value)
        with self.assertRaisesRegex(TypeError, "DecisionRequest"):
            build_decision_evidence(self.dataset, {}, source_label=LABEL)

    def test_request_is_frozen_and_unsupported_options_cannot_be_silently_ignored(self):
        with self.assertRaises(FrozenInstanceError):
            self.request.down = 2
        for field, value in (("side", "defense"), ("opponent", "ATL"), ("play_family", "RPO"),
                             ("snapshot_path", "/tmp/data.csv"), ("bootstrap_repetitions", 100)):
            with self.subTest(field=field), self.assertRaises(TypeError):
                replace(self.request, **{field: value})

    def test_absent_optional_columns_fail_even_when_parent_cohort_is_empty(self):
        for field, changes in (("yardline_100", {"yardline_max": 38}),
                               ("score_differential", {"score_max": -3}),
                               ("qtr", {"period": "Q4"}),
                               ("quarter_seconds_remaining", {"period": "Q4", "clock_max": 134})):
            dataset = self.contextual_dataset([], omit=(field,))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "requires.*" + field):
                self.evidence(dataset, **changes)

    def test_context_bound_validation_is_shared(self):
        dataset = self.contextual_dataset([])
        cases = ({"yardline_min": True}, {"yardline_max": float("nan")},
                 {"yardline_max": float("inf")}, {"yardline_min": -1}, {"yardline_max": 101},
                 {"yardline_min": 40, "yardline_max": 30}, {"score_min": True}, {"score_max": -3.0},
                 {"score_min": 3, "score_max": 0}, {"period": "4"}, {"period": []},
                 {"clock_max": 134}, {"period": "Q4", "clock_min": True},
                 {"period": "Q4", "clock_min": -1}, {"period": "Q4", "clock_max": 901},
                 {"period": "Q4", "clock_min": 135, "clock_max": 134})
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.evidence(dataset, **changes)

    def test_missing_optional_values_are_excluded_only_when_requested(self):
        for field, changes, stage in (("yardline_100", {"yardline_max": 100}, "field_position"),
                                      ("score_differential", {"score_max": 0}, "score_differential"),
                                      ("qtr", {"period": "Q4"}, "period"),
                                      ("quarter_seconds_remaining", {"period": "Q4", "clock_max": 900}, "clock")):
            with self.subTest(field=field):
                dataset = self.contextual_dataset([{field: "NA"}])
                self.assertEqual(self.evidence(dataset, down=3, distance_min=4, distance_max=4)["population"]["plays"], 1)
                result = self.evidence(dataset, down=3, distance_min=4, distance_max=4, **changes)
                self.assertEqual(result["population"]["plays"], 0)
                self.assertEqual(result["data_quality"][stage + "_filter"]["missing_" + field], 1)
                self.assertTrue(any(field + "; no imputation" in warning for warning in result["warnings"]))

    def test_combined_context_filters_are_inclusive_and_ledger_reconciles(self):
        dataset = self.contextual_dataset([
            {}, {"play_type": "run", "qb_dropback": "0", "epa": "NA", "game_id": "SYNTHETIC_DECISION_B"},
            {"yardline_100": "NA", "score_differential": "NA"}, {"yardline_100": "39"},
            {"score_differential": "NA"}, {"score_differential": "-2"},
            {"qtr": "NA"}, {"qtr": "5"}, {"quarter_seconds_remaining": "NA"},
            {"quarter_seconds_remaining": "135"}, {"down": "2"}, {"ydstogo": "5"},
        ])
        result = self.evidence(dataset, down=3, distance_min=4, distance_max=4,
                               yardline_min=38, yardline_max=38, score_min=-3, score_max=-3,
                               period="Q4", clock_min=134, clock_max=134)
        self.assertEqual(result["population"], {"plays": 2, "games": 2})
        self.assertEqual([c["frequency"] for c in result["candidates"]], [0.5, 0.5])
        quality = result["data_quality"]
        self.assertEqual(quality["filter_order"], ["field_position", "score_differential", "period", "clock", "down", "distance"])
        previous = 12
        for name in quality["filter_order"]:
            stage = quality[name + "_filter"]
            missing = stage["missing_" + result["cohort"][name]["field"]]
            outside = stage["outside_period" if name == "period" else "outside_range"]
            self.assertEqual(stage["plays_before_filter"], previous)
            self.assertEqual(previous, missing + outside + stage["plays_after_filter"])
            previous = stage["plays_after_filter"]
        self.assertEqual(previous, 2)
        self.assertEqual(quality["score_differential_filter"]["missing_score_differential"], 1)
        self.assertEqual(quality["eligible_rows_outside_cohort"], 10)

    def test_overtime_includes_all_ot_periods_and_clock_zero_is_observed(self):
        dataset = self.contextual_dataset([{"qtr": "4", "quarter_seconds_remaining": "0"},
                                           {"qtr": "5", "quarter_seconds_remaining": "0"},
                                           {"qtr": "6", "quarter_seconds_remaining": "0"},
                                           {"qtr": "5", "quarter_seconds_remaining": "1"}])
        result = self.evidence(dataset, down=3, distance_min=4, distance_max=4,
                               period="OT", clock_min=0, clock_max=0)
        self.assertEqual(result["population"]["plays"], 2)
        self.assertIsNone(result["cohort"]["period"]["maximum_inclusive"])
        self.assertEqual(result["cohort"]["clock"]["maximum_inclusive"], 0)

    def test_reciprocal_scout_defense_keeps_offense_relative_context_and_epa(self):
        dataset = self.contextual_dataset([{}, {"play_type": "run", "qb_dropback": "0", "epa": "-0.5"}])
        bounds = dict(yardline_max=38, score_max=-3, period="Q4", clock_max=134)
        _, offense = select_population(dataset, team="CAR", season=2024, before_week=3)
        _, defense = select_population(dataset, team="ATL", side="defense", season=2024, before_week=3)
        self.assertEqual(offense, defense)
        self.assertEqual(filter_context(offense, context_filters(dataset, **bounds)),
                         filter_context(defense, context_filters(dataset, **bounds)))
        scout = build_report(dataset, team="ATL", side="defense", season=2024, before_week=3,
                             source_label=LABEL, **bounds)
        self.assertEqual(scout["metric_context"]["interpretation"], "allowed")
        self.assertEqual((scout["overall"]["epa_per_play"], scout["overall"]["success_rate"]), (0, 0.5))
        evidence = self.evidence(dataset, down=3, distance_min=4, distance_max=4, **bounds)
        run, passed = evidence["candidates"]
        self.assertEqual((run["epa_per_play"], passed["epa_per_play"]), (-0.5, 0.5))
        self.assertEqual(evidence["population"], {"plays": 2, "games": 1})
        self.assertEqual((run["games"], passed["games"]), (1, 1))  # Shared game, not two games.

    def test_provenance_is_copied_without_relabeling_or_mutation(self):
        # Deliberate stub tests propagation; snapshot loading/validation is tested separately.
        manifest = {"season": 2024, "synthetic_test_stub": {"values": [1]}}
        dataset = replace(self.dataset, source_manifest=manifest)
        result = self.evidence(dataset)
        self.assertEqual(result["source"], {"label": LABEL, "sha256": self.dataset.source_sha256,
                                            "snapshot": manifest})
        result["source"]["snapshot"]["synthetic_test_stub"]["values"].append(2)
        result["data_quality"]["excluded_rows_by_reason"]["kneel"] = 900
        self.assertEqual(manifest["synthetic_test_stub"]["values"], [1])
        self.assertEqual(dataset.exclusions["kneel"], 1)
        with self.assertRaisesRegex(ValueError, "differs from snapshot"):
            self.evidence(dataset, season=2025)

    def test_deterministic_json_serializable_and_no_io_after_loading(self):
        with patch("builtins.open", side_effect=AssertionError("unexpected file IO")), \
             patch("socket.create_connection", side_effect=AssertionError("unexpected network IO")):
            first = self.evidence()
            second = self.evidence()
        self.assertEqual(first, second)
        self.assertEqual(json.loads(json.dumps(first, allow_nan=False)), first)
        self.assertEqual(self.request.down, 1)
        self.assertEqual(self.dataset, load_csv(FIXTURE))


if __name__ == "__main__":
    unittest.main()
