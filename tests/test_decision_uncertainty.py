"""Invented exact cohorts; independently expand games instead of using engine totals."""

from copy import deepcopy
from dataclasses import replace
from itertools import chain, product
import json
from math import isclose
import random
from statistics import quantiles
import unittest
from unittest.mock import patch

from opponent_intelligence.decision import DecisionRequest, build_decision_evidence
from opponent_intelligence.pbp import Dataset, OPTIONAL_COLUMNS, Play
from opponent_intelligence.report import build_report


def invented_rows(games=5):
    rows = []
    for game in range(games):
        for offense, defense, offset in (("CAR", "ATL", 0), ("ATL", "CAR", 3)):
            for dropback in (False, True):
                count = (game % 5 + 1) if not dropback else (6 - game % 5)
                if offense == "ATL" and not dropback:
                    count *= 2
                for _ in range(count):
                    rows.append(Play(
                        game_id=f"SYNTHETIC_G{game:02}", play_id=len(rows),
                        season=2024, season_type="REG", week=game % 18 + 1,
                        offense=offense, defense=defense, down=3, yards_to_go=4,
                        dropback=dropback, epa=float((1 - game if dropback else game - 2) + offset),
                        yardline_100=38, score_differential=-3, qtr=4, quarter_seconds_remaining=134,
                    ))
    return rows


def dataset(rows):
    return Dataset(tuple(rows), "explicitly-invented-uncertainty", len(rows), {},
                   optional_columns=OPTIONAL_COLUMNS)


class DecisionUncertaintyTests(unittest.TestCase):
    def setUp(self):
        self.rows = invented_rows()
        self.request = DecisionRequest(team="CAR", season=2024, before_week=19,
                                       down=3, distance_min=4, distance_max=4,
                                       compare_league=True, bootstrap_repetitions=200, bootstrap_seed=7)

    def evidence(self, rows=None, **changes):
        return build_decision_evidence(dataset(self.rows if rows is None else rows),
                                       replace(self.request, **changes),
                                       source_label="Invented candidate bootstrap; not NFL observations")

    def test_all_3125_five_game_draws_match_independent_expanded_play_calculations(self):
        draws = list(product(range(5), repeat=5))
        expected = {candidate: {side: [[], [], []] for side in ("selected", "baseline", "difference")}
                    for candidate in ("run", "pass")}
        for draw in draws:
            expanded = [p for game in draw for p in self.rows if p.game_id == f"SYNTHETIC_G{game:02}"]
            for candidate, flag in (("run", False), ("pass", True)):
                estimates = {}
                for side, team in (("selected", "CAR"), ("baseline", "ATL")):
                    parent = [p for p in expanded if p.offense == team]
                    calls = [p for p in parent if p.dropback == flag]
                    epa = [p.epa for p in calls if p.epa is not None]
                    estimates[side] = (len(calls) / len(parent), sum(v > 0 for v in epa) / len(epa),
                                       sum(epa) / len(epa))
                estimates["difference"] = tuple((a - b) * scale for a, b, scale in
                                                 zip(estimates["selected"], estimates["baseline"], (100, 100, 1)))
                for side, values in estimates.items():
                    for target, value in zip(expected[candidate][side], values):
                        target.append(value)
        with patch("opponent_intelligence.uncertainty.Random") as generator:
            generator.return_value.randrange.side_effect = chain.from_iterable(draws)
            result = self.evidence(bootstrap_repetitions=3125)["uncertainty"]
            # One joint frame, not separate draws for calls or populations.
            self.assertEqual(generator.return_value.randrange.call_count, 5 * 3125)
        self.assertEqual(result["resampling_games"], 5)
        self.assertEqual(result["performed_repetitions"], 3125)
        self.assertTrue(result["shared_game_weights"])
        for row in result["candidates"]:
            for side in ("selected", "baseline", "difference"):
                names = ("frequency_pp", "success_rate_pp", "epa_per_play") if side == "difference" else (
                    "frequency", "success_rate", "epa_per_play")
                for metric, values in zip(names, expected[row["candidate"]][side]):
                    with self.subTest(candidate=row["candidate"], side=side, metric=metric):
                        actual = row[side][metric]
                        support = {s: 5 for s in ("selected", "baseline")} if side == "difference" else {side: 5}
                        self.assertEqual(actual["support_games"], support)
                        self.assertEqual((actual["valid_replicates"], actual["undefined_replicates"]), (3125, 0))
                        lower, *_, upper = quantiles(values, n=40, method="inclusive")
                        if isclose(lower, upper, rel_tol=1e-12, abs_tol=1e-12):
                            self.assertEqual(actual["status"], "degenerate_interval")
                            self.assertIsNone(actual["interval"])
                        else:
                            self.assertEqual(actual["status"], "ok")
                            self.assertAlmostEqual(actual["interval"]["lower"], lower)
                            self.assertAlmostEqual(actual["interval"]["upper"], upper)
        # Paired common game effects cancel from the EPA contrast, even though
        # marginal intervals vary. Subtracting marginal endpoints would be wrong.
        for row in result["candidates"]:
            self.assertEqual(row["selected"]["epa_per_play"]["status"], "ok")
            self.assertEqual(row["baseline"]["epa_per_play"]["status"], "ok")
            self.assertEqual(row["difference"]["epa_per_play"]["status"], "degenerate_interval")

    def test_opt_in_preserves_point_evidence_and_dataset_and_uses_no_io(self):
        source = dataset(self.rows)
        original = deepcopy(source)
        with patch("builtins.open", side_effect=AssertionError("file IO forbidden")), \
             patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
            for comparison in (False, True):
                request = replace(self.request, compare_league=comparison)
                enabled = build_decision_evidence(source, request, source_label="Invented")
                with patch("opponent_intelligence.uncertainty.Random", side_effect=AssertionError("opt-out sampled")):
                    plain = build_decision_evidence(source, replace(request, bootstrap_repetitions=None,
                                                                    bootstrap_seed=None), source_label="Invented")
                self.assertNotIn("uncertainty", plain)
                self.assertEqual(json.loads(json.dumps(enabled, allow_nan=False)), enabled)
                enabled.pop("uncertainty")
                self.assertEqual(enabled, plain)
        self.assertEqual(source, original)

    def test_frequency_uses_parent_games_but_epa_support_uses_observed_candidate_games(self):
        rows = [replace(p, epa=None) if not p.dropback and p.game_id != "SYNTHETIC_G00" else p for p in self.rows]
        result = self.evidence(rows)
        run, passed = result["uncertainty"]["candidates"]
        self.assertEqual(result["candidates"][0]["games"], 5)
        self.assertEqual(run["selected"]["frequency"]["support_games"], {"selected": 5})
        self.assertEqual(run["selected"]["frequency"]["status"], "ok")
        for metric in ("epa_per_play", "success_rate"):
            self.assertEqual(run["selected"][metric]["support_games"], {"selected": 1})
            self.assertEqual(run["selected"][metric]["status"], "insufficient_games")
            self.assertEqual(passed["selected"][metric]["support_games"], {"selected": 5})
        rows = [p for p in self.rows if p.dropback or p.game_id == "SYNTHETIC_G00"]
        result = self.evidence(rows)
        self.assertEqual(result["candidates"][0]["games"], 1)
        self.assertEqual(result["uncertainty"]["candidates"][0]["selected"]["frequency"]["support_games"], {"selected": 5})

    def test_absent_candidate_frequency_zero_is_degenerate_not_undefined(self):
        result = self.evidence([p for p in self.rows if p.dropback])
        self.assertEqual(result["candidates"][0]["frequency"], 0)
        run = result["uncertainty"]["candidates"][0]
        for side in ("selected", "baseline", "difference"):
            frequency = run[side]["frequency_pp" if side == "difference" else "frequency"]
            self.assertEqual(frequency["status"], "degenerate_interval")
            self.assertEqual(frequency["valid_replicates"], 200)
            self.assertIsNone(frequency["interval"])
            self.assertEqual(run[side]["epa_per_play"]["status"], "undefined_estimate")
            self.assertEqual(run[side]["epa_per_play"]["undefined_replicates"], 200)

    def test_all_missing_epa_keeps_frame_and_frequency_not_outcome_support(self):
        result = self.evidence([replace(p, epa=None) for p in self.rows])["uncertainty"]
        self.assertEqual(result["resampling_games"], 5)
        for candidate in result["candidates"]:
            self.assertEqual(candidate["selected"]["frequency"]["status"], "ok")
            self.assertEqual(candidate["selected"]["epa_per_play"]["support_games"], {"selected": 0})
            self.assertEqual(candidate["difference"]["epa_per_play"]["undefined_replicates"], 200)

    def test_constant_zero_outcomes_are_observed_but_bounds_are_withheld(self):
        result = self.evidence([replace(p, epa=0) for p in self.rows])["uncertainty"]
        for candidate in result["candidates"]:
            for side in ("selected", "baseline", "difference"):
                for metric in ("epa_per_play", "success_rate_pp" if side == "difference" else "success_rate"):
                    self.assertEqual(candidate[side][metric]["status"], "degenerate_interval")
                    self.assertIsNone(candidate[side][metric]["interval"])
                    self.assertEqual(candidate[side][metric]["valid_replicates"], 200)

    def test_difference_requires_both_sides_candidate_epa_support(self):
        for sparse_team, sparse_side in (("CAR", "selected"), ("ATL", "baseline")):
            rows = [replace(p, epa=None) if (p.offense == sparse_team and not p.dropback
                                            and p.game_id != "SYNTHETIC_G00") else p for p in self.rows]
            run = self.evidence(rows)["uncertainty"]["candidates"][0]
            expected = {"selected": 5, "baseline": 5, sparse_side: 1}
            self.assertEqual(run["difference"]["epa_per_play"]["support_games"], expected)
            self.assertEqual(run["difference"]["epa_per_play"]["status"], "insufficient_games")
            self.assertEqual(run["difference"]["frequency_pp"]["support_games"], {"selected": 5, "baseline": 5})

    def test_baseline_only_draws_are_undefined_not_redrawn_or_zero_filled(self):
        extra = replace(self.rows[-1], game_id="SYNTHETIC_Z_BASELINE_ONLY", play_id=999)
        with patch("opponent_intelligence.uncertainty.Random") as generator:
            generator.return_value.randrange.return_value = 5
            result = self.evidence(self.rows + [extra])["uncertainty"]
            self.assertEqual(generator.return_value.randrange.call_count, 200 * 6)
        for candidate in result["candidates"]:
            for metric in candidate["selected"].values():
                self.assertEqual(metric["status"], "too_few_valid_replicates")
                self.assertEqual((metric["valid_replicates"], metric["undefined_replicates"]), (0, 200))
            for metric in candidate["difference"].values():
                self.assertEqual(metric["status"], "too_few_valid_replicates")
            # Parent ATL plays exist in all draws, even though Run does not.
            self.assertEqual(candidate["baseline"]["frequency"]["valid_replicates"], 200)

    def test_empty_populations_preserve_both_candidates_without_fallback(self):
        for rows, comparison in (([], False), ([], True),
                                 ([p for p in self.rows if p.offense == "CAR"], True),
                                 ([p for p in self.rows if p.offense == "ATL"], True)):
            with self.subTest(comparison=comparison, rows=len(rows)):
                result = self.evidence(rows, compare_league=comparison)["uncertainty"]
                self.assertEqual([c["candidate"] for c in result["candidates"]], ["run", "pass"])
                self.assertEqual(result["performed_repetitions"], 200 if rows else 0)
                for candidate in result["candidates"]:
                    if comparison:
                        for metric in candidate["difference"].values():
                            self.assertIsNone(metric["interval"])
                            self.assertEqual(metric["status"], "undefined_estimate")
                    else:
                        self.assertNotIn("baseline", candidate)
                        self.assertNotIn("difference", candidate)
                    if not rows:
                        for metric in candidate["selected"].values():
                            self.assertEqual((metric["valid_replicates"], metric["undefined_replicates"]), (0, 0))

    def test_support_gate_counts_games_not_plays_and_does_not_unlock_ranking(self):
        for games in (1, 4, 5, 20):
            result = self.evidence(invented_rows(games), minimum_plays=1)
            for row in result["uncertainty"]["candidates"]:
                epa = row["selected"]["epa_per_play"]
                self.assertEqual(epa["support_games"], {"selected": games})
                self.assertEqual(epa["few_games"], games < 20)
                self.assertEqual(epa["status"], "insufficient_games" if games < 5 else "ok")
            self.assertIsNone(result["comparison"]["preferred_candidate"])
            self.assertEqual(result["comparison"]["reason"], "candidate_comparison_not_validated")
        rows = [replace(self.rows[0], play_id=i, epa=float(i)) for i in range(500)]
        result = self.evidence(rows, minimum_plays=1)
        self.assertFalse(result["candidates"][0]["small_sample"])
        self.assertEqual(result["uncertainty"]["candidates"][0]["selected"]["epa_per_play"]["status"], "insufficient_games")

    def test_exact_valid_fraction_gate_with_candidate_absent_draws(self):
        # G05 has only Pass on both sides: Run frequency is defined zero but Run
        # outcomes are absent. All five other games have Run EPA support.
        rows = self.rows + [replace(p, game_id="SYNTHETIC_G05") for p in self.rows if p.dropback and p.game_id == "SYNTHETIC_G00"]
        for missing in (10, 11):
            indices = [5] * missing + [0 if i % 2 else 4 for i in range(200 - missing)]
            with patch("opponent_intelligence.uncertainty.Random") as generator:
                generator.return_value.randrange.side_effect = chain.from_iterable([i] * 6 for i in indices)
                run = self.evidence(rows)["uncertainty"]["candidates"][0]
            for side in ("selected", "baseline"):
                self.assertEqual(run[side]["frequency"]["valid_replicates"], 200)
                self.assertEqual(run[side]["epa_per_play"]["valid_replicates"], 200 - missing)
                self.assertEqual(run[side]["epa_per_play"]["undefined_replicates"], missing)
                self.assertEqual(run[side]["epa_per_play"]["status"], "ok" if missing == 10 else "too_few_valid_replicates")
            self.assertEqual(run["difference"]["epa_per_play"]["undefined_replicates"], missing)

    def test_selected_only_ignores_other_offenses_and_comparison_includes_baseline_only_games(self):
        extra = replace(self.rows[-1], game_id="SYNTHETIC_Z_BASELINE_ONLY", play_id=999)
        without = self.evidence(compare_league=False)["uncertainty"]
        self.assertEqual(without, self.evidence(self.rows + [extra], compare_league=False)["uncertainty"])
        self.assertEqual((without["resampling_population"], without["resampling_games"], without["shared_game_weights"]),
                         ("selected", 5, False))
        with_baseline = self.evidence(self.rows + [extra])["uncertainty"]
        self.assertEqual(with_baseline["resampling_games"], 6)
        self.assertEqual(with_baseline["resampling_population"], "selected_and_baseline_union")

    def test_all_filters_apply_before_defining_the_resampling_frame(self):
        changes = ({"season": 2025}, {"season_type": "POST"}, {"week": 19},
                   {"down": 2}, {"yards_to_go": 5}, {"yardline_100": 39}, {"yardline_100": None},
                   {"score_differential": -2}, {"score_differential": None}, {"qtr": 3}, {"qtr": None},
                   {"quarter_seconds_remaining": 135}, {"quarter_seconds_remaining": None})
        outside = [replace(p, game_id=f"SYNTHETIC_OUTSIDE_{i}", **change)
                   for i, change in enumerate(changes) for p in (self.rows[0], self.rows[-1])]
        filters = dict(yardline_min=38, yardline_max=38, score_min=-3, score_max=-3,
                       period="Q4", clock_min=134, clock_max=134)
        self.assertEqual(self.evidence(self.rows + outside, **filters)["uncertainty"], self.evidence(**filters)["uncertainty"])
        self.assertEqual(self.evidence(before_week=1)["uncertainty"]["resampling_games"], 0)

    def test_seed_order_rng_and_json_reproducibility(self):
        state = random.getstate()
        first = self.evidence()["uncertainty"]
        self.assertEqual(random.getstate(), state)
        self.assertEqual(first, self.evidence()["uncertainty"])
        self.assertEqual(first, self.evidence(list(reversed(self.rows)))["uncertainty"])
        self.assertNotEqual(first["candidates"], self.evidence(bootstrap_seed=13)["uncertainty"]["candidates"])
        self.assertEqual(self.evidence(bootstrap_seed=None), self.evidence(bootstrap_seed=0))

    def test_option_validation_is_bounded_strict_and_applies_to_empty_data(self):
        for repetitions in (True, False, 0, 199, 10001, 200.0, "200", [], {}):
            with self.subTest(repetitions=repetitions), self.assertRaisesRegex(ValueError, "bootstrap_repetitions"):
                self.evidence([], bootstrap_repetitions=repetitions)
        for seed in (True, False, -1, 2**32, 0.0, "0", [], {}):
            with self.subTest(seed=seed), self.assertRaisesRegex(ValueError, "bootstrap_seed"):
                self.evidence([], bootstrap_seed=seed)
        with self.assertRaisesRegex(ValueError, "requires"):
            self.evidence([], bootstrap_repetitions=None, bootstrap_seed=0)
        result = self.evidence([], bootstrap_repetitions=10000, bootstrap_seed=2**32 - 1)["uncertainty"]
        self.assertEqual((result["repetitions"], result["seed"], result["performed_repetitions"]), (10000, 2**32 - 1, 0))

    def test_pass_frequency_matches_scout_and_defense_retains_offense_sign(self):
        options = dict(team="CAR", season=2024, before_week=19, source_label="Invented",
                       compare_league=True, bootstrap_repetitions=200, bootstrap_seed=7)
        scout = build_report(dataset(self.rows), **options)
        swapped = [replace(p, offense=p.defense, defense=p.offense) for p in self.rows]
        defense = build_report(dataset(swapped), side="defense", **options)
        self.assertEqual(scout["uncertainty"], defense["uncertainty"])
        run, passed = self.evidence()["uncertainty"]["candidates"]
        for side in ("selected", "baseline", "difference"):
            metric = "frequency_pp" if side == "difference" else "frequency"
            scout_metric = "dropback_rate_pp" if side == "difference" else "dropback_rate"
            self.assertEqual(passed[side][metric], scout["uncertainty"]["overall"][side][scout_metric])
            a, b = run[side][metric]["interval"], passed[side][metric]["interval"]
            self.assertAlmostEqual(a["lower"], (0 if side == "difference" else 1) - b["upper"])
            self.assertAlmostEqual(a["upper"], (0 if side == "difference" else 1) - b["lower"])


if __name__ == "__main__":
    unittest.main()
