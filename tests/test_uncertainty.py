"""Explicitly synthetic cluster-bootstrap contracts and independent enumeration."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import replace
from itertools import chain, product
import io
import json
from pathlib import Path
import random
from statistics import quantiles
import unittest
from unittest.mock import patch

from opponent_intelligence.__main__ import main
from opponent_intelligence.pbp import Dataset, OPTIONAL_COLUMNS, Play
from opponent_intelligence.report import build_report
from opponent_intelligence.uncertainty import validate_bootstrap


def synthetic_plays(games=5):
    rows = []
    for game in range(games):
        for index in range(game + 1):
            row = Play(game_id=f"SYNTHETIC_G{game:02}", play_id=index, season=2024,
                       season_type="REG", week=game % 18 + 1, offense="CAR", defense="ATL",
                       down=1, yards_to_go=10, dropback=game % 2 == 0, epa=float(game - 2),
                       yardline_100=20, score_differential=-7, qtr=4, quarter_seconds_remaining=120)
            rows.extend([row, replace(row, play_id=index + 100, offense="ATL", defense="CAR",
                                      dropback=not row.dropback, epa=row.epa + 3)])
    return rows


def dataset(rows):
    return Dataset(tuple(rows), "explicitly-synthetic", len(rows), {}, optional_columns=OPTIONAL_COLUMNS)


class UncertaintyTests(unittest.TestCase):
    def setUp(self):
        self.rows = synthetic_plays()

    def report(self, rows=None, **changes):
        options = dict(team="CAR", season=2024, before_week=19,
                       source_label="Synthetic cluster-bootstrap records; not NFL data",
                       compare_league=True, bootstrap_repetitions=200, bootstrap_seed=7)
        options.update(changes)
        return build_report(dataset(self.rows if rows is None else rows), **options)

    def test_exhaustive_five_game_bootstrap_matches_independent_expanded_play_arithmetic(self):
        # Enumerate every ordered draw (5^5), replacing RNG only. Expectations
        # expand whole games into individual plays and use a different quantile
        # implementation, not the production game totals or percentile helper.
        draws = list(product(range(5), repeat=5))
        expected = {side: [[], [], []] for side in ("selected", "baseline", "difference")}
        for draw in draws:
            epa = [game - 2 for game in draw for _ in range(game + 1)]
            dropbacks = [game % 2 == 0 for game in draw for _ in range(game + 1)]
            selected = (sum(dropbacks) / len(epa), sum(v > 0 for v in epa) / len(epa), sum(epa) / len(epa))
            baseline = (1 - selected[0], 1.0, selected[2] + 3)
            difference = ((selected[0] - baseline[0]) * 100, (selected[1] - 1) * 100, -3.0)
            for side, values in (("selected", selected), ("baseline", baseline), ("difference", difference)):
                for output, value in zip(expected[side], values):
                    output.append(value)
        with patch("opponent_intelligence.uncertainty.Random") as generator:
            generator.return_value.randrange.side_effect = chain.from_iterable(draws)
            result = self.report(bootstrap_repetitions=len(draws))
            self.assertEqual(generator.return_value.randrange.call_count, 5 * len(draws))
        self.assertAlmostEqual(result["overall"]["epa_per_play"], 10 / 15)
        self.assertNotEqual(result["overall"]["epa_per_play"], sum(range(-2, 3)) / 5)
        uncertainty = result["uncertainty"]
        self.assertEqual(uncertainty["resampling_games"], 5)
        self.assertTrue(uncertainty["shared_game_weights"])
        for side, names in (("selected", ("dropback_rate", "success_rate", "epa_per_play")),
                            ("baseline", ("dropback_rate", "success_rate", "epa_per_play")),
                            ("difference", ("dropback_rate_pp", "success_rate_pp", "epa_per_play"))):
            for metric, values in zip(names, expected[side]):
                with self.subTest(side=side, metric=metric):
                    actual = uncertainty["overall"][side][metric]
                    self.assertEqual(actual["valid_replicates"], 3125)
                    self.assertEqual(actual["undefined_replicates"], 0)
                    if min(values) == max(values):
                        self.assertEqual(actual["status"], "degenerate_interval")
                        self.assertIsNone(actual["interval"])
                    else:
                        cuts = quantiles(values, n=40, method="inclusive")
                        self.assertEqual(actual["status"], "ok")
                        self.assertAlmostEqual(actual["interval"]["lower"], cuts[0])
                        self.assertAlmostEqual(actual["interval"]["upper"], cuts[-1])
        # The common game effect cancels exactly from EPA differences. Independent
        # draws for the two populations would falsely add variation to this contrast.
        self.assertEqual(uncertainty["situations"][0]["difference"], uncertainty["overall"]["difference"])

    def test_reproducible_seed_row_order_and_global_rng_isolation(self):
        state = random.getstate()
        first = self.report()["uncertainty"]
        self.assertEqual(random.getstate(), state)
        self.assertEqual(first, self.report()["uncertainty"])
        self.assertEqual(first, self.report(list(reversed(self.rows)))["uncertainty"])
        self.assertNotEqual(first["overall"], self.report(bootstrap_seed=123)["uncertainty"]["overall"])
        self.assertEqual(self.report(bootstrap_seed=None)["uncertainty"], self.report(bootstrap_seed=0)["uncertainty"])

    def test_opt_in_preserves_every_existing_field_and_dataset(self):
        source = dataset(self.rows)
        before = deepcopy(source)
        for comparison in (False, True):
            options = dict(team="CAR", season=2024, before_week=19, source_label="Synthetic",
                           compare_league=comparison, period="Q4", clock_max=120)
            ordinary = build_report(source, **options)
            enabled = build_report(source, **options, bootstrap_repetitions=200)
            enabled.pop("uncertainty")
            self.assertEqual(ordinary, enabled)
        self.assertEqual(source, before)

    def test_selected_only_has_no_baseline_and_uses_only_selected_games(self):
        extra = replace(self.rows[-1], game_id="SYNTHETIC_BASELINE_ONLY", play_id=999)
        result = self.report(self.rows + [extra], compare_league=False)["uncertainty"]
        self.assertEqual(result["resampling_population"], "selected")
        self.assertEqual(result["resampling_games"], 5)
        self.assertFalse(result["shared_game_weights"])
        self.assertEqual(list(result["overall"]), ["selected"])

    def test_support_counts_games_not_plays_and_is_independent_of_play_warning(self):
        for games in (1, 4, 5, 20):
            result = self.report(synthetic_plays(games), minimum_plays=1)["uncertainty"]
            epa = result["overall"]["selected"]["epa_per_play"]
            self.assertEqual(epa["support_games"], {"selected": games})
            self.assertEqual(epa["few_games"], games < 20)
            self.assertEqual(epa["status"], "insufficient_games" if games < 5 else "ok")
        many = [replace(self.rows[0], play_id=i, epa=float(i)) for i in range(500)]
        result = self.report(many, minimum_plays=1)
        self.assertFalse(result["overall"]["small_sample"])
        self.assertEqual(result["uncertainty"]["overall"]["selected"]["epa_per_play"]["status"], "insufficient_games")

    def test_epa_game_support_is_distinct_from_play_game_support(self):
        rows = [replace(p, epa=None) if p.game_id != "SYNTHETIC_G00" and p.offense == "CAR" else p for p in self.rows]
        result = self.report(rows)["uncertainty"]["overall"]
        self.assertEqual(result["selected"]["dropback_rate"]["support_games"], {"selected": 5})
        for metric in ("success_rate", "epa_per_play"):
            self.assertEqual(result["selected"][metric]["support_games"], {"selected": 1})
            self.assertEqual(result["selected"][metric]["status"], "insufficient_games")
            key = "success_rate_pp" if metric == "success_rate" else metric
            self.assertEqual(result["difference"][key]["support_games"], {"selected": 1, "baseline": 5})
        rows = [replace(p, epa=None) if p.offense == "CAR" else p for p in self.rows]
        result = self.report(rows)["uncertainty"]["overall"]
        self.assertEqual(result["selected"]["epa_per_play"]["status"], "undefined_estimate")
        self.assertEqual(result["selected"]["dropback_rate"]["status"], "ok")
        self.assertEqual(result["difference"]["epa_per_play"]["undefined_replicates"], 200)

    def test_undefined_draws_are_counted_and_valid_fraction_gate_has_exact_boundary(self):
        extra = [replace(self.rows[-1], game_id=f"SYNTHETIC_G{i:02}", epa=1) for i in range(5, 20)]
        for missing in (10, 11):
            # Draw baseline-only G19 for `missing` whole replications. Alternate
            # shared G00/G04 otherwise, keeping variation in defined EPA ratios.
            indices = [19] * missing + [0 if i % 2 else 4 for i in range(200 - missing)]
            with patch("opponent_intelligence.uncertainty.Random") as generator:
                generator.return_value.randrange.side_effect = chain.from_iterable([i] * 20 for i in indices)
                overall = self.report(self.rows + extra)["uncertainty"]["overall"]
            selected = overall["selected"]["epa_per_play"]
            self.assertEqual(selected["valid_replicates"], 200 - missing)
            self.assertEqual(selected["undefined_replicates"], missing)
            self.assertEqual(selected["status"], "ok" if missing == 10 else "too_few_valid_replicates")
            self.assertEqual(overall["baseline"]["epa_per_play"]["valid_replicates"], 200)
            self.assertEqual(overall["difference"]["epa_per_play"]["undefined_replicates"], missing)

    def test_empty_populations_remain_null_and_empty_frame_performs_no_draws(self):
        for rows, comparison in (([], False), ([], True), ([p for p in self.rows if p.offense == "ATL"], True),
                                 ([p for p in self.rows if p.offense == "CAR"], True)):
            result = self.report(rows, compare_league=comparison)["uncertainty"]
            if not rows:
                self.assertEqual(result["performed_repetitions"], 0)
                self.assertEqual(result["resampling_games"], 0)
            if not any(p.offense == "CAR" for p in rows):
                self.assertEqual(result["situations"], [])
                self.assertEqual(result["overall"]["selected"]["epa_per_play"]["status"], "undefined_estimate")
            if comparison:
                for metric in result["overall"]["difference"].values():
                    self.assertIsNone(metric["interval"])
                    self.assertEqual(metric["status"], "undefined_estimate")

    def test_constant_rates_and_zero_epa_do_not_masquerade_as_certainty(self):
        rows = [replace(p, epa=0.0, dropback=False) for p in self.rows]
        result = self.report(rows)["uncertainty"]["overall"]
        for population in result.values():
            for value in population.values():
                self.assertEqual(value["status"], "degenerate_interval")
                self.assertIsNone(value["interval"])
                self.assertEqual(value["valid_replicates"], 200)

    def test_each_situation_uses_its_own_support_and_never_overall_fallback(self):
        rows = [replace(p, down=2, yards_to_go=2) if p.offense == "CAR" else p for p in self.rows]
        result = self.report(rows)["uncertainty"]
        self.assertEqual(result["overall"]["baseline"]["epa_per_play"]["support_games"], {"baseline": 5})
        self.assertEqual(len(result["situations"]), 1)
        situation = result["situations"][0]
        self.assertEqual((situation["down"], situation["distance"]), (2, "short"))
        self.assertEqual(situation["baseline"]["epa_per_play"]["status"], "undefined_estimate")
        self.assertIsNone(situation["difference"]["epa_per_play"]["interval"])
        sparse = self.rows + [replace(self.rows[0], play_id=999, down=3, yards_to_go=5)]
        situation = self.report(sparse)["uncertainty"]["situations"][1]
        self.assertEqual(situation["selected"]["dropback_rate"]["status"], "insufficient_games")

    def test_all_filters_cutoffs_and_missing_context_apply_before_resampling(self):
        outside = [replace(self.rows[0], game_id=f"SYNTHETIC_OUTSIDE_{i}", **change)
                   for i, change in enumerate((dict(week=19), dict(season=2025), dict(season_type="POST"),
                                               dict(yardline_100=80), dict(score_differential=7),
                                               dict(qtr=2), dict(quarter_seconds_remaining=121),
                                               dict(yardline_100=None), dict(score_differential=None),
                                               dict(qtr=None), dict(quarter_seconds_remaining=None)))]
        outside += [replace(p, play_id=1000, offense="ATL", defense="CAR") for p in outside]
        filters = dict(yardline_max=20, score_max=-1, period="Q4", clock_max=120)
        self.assertEqual(self.report(self.rows + outside, **filters)["uncertainty"], self.report(**filters)["uncertainty"])
        self.assertEqual(self.report(before_week=1)["uncertainty"]["resampling_games"], 0)

    def test_defense_preserves_epa_direction_and_units(self):
        swapped = [replace(p, offense=p.defense, defense=p.offense) for p in self.rows]
        result = self.report(swapped, side="defense")["uncertainty"]
        self.assertEqual(result, self.report()["uncertainty"])
        self.assertEqual(result["overall"]["selected"]["dropback_rate"]["unit"], "proportion")
        self.assertEqual(result["overall"]["difference"]["dropback_rate_pp"]["unit"], "percentage_points")
        self.assertEqual(result["overall"]["difference"]["epa_per_play"]["unit"], "expected_points_per_observed_play")

    def test_option_validation_including_empty_data_and_explicit_zero_seed(self):
        for value in (True, False, 0, 199, 10001, 200.0, "200", [], {}):
            with self.subTest(repetitions=value), self.assertRaisesRegex(ValueError, "bootstrap_repetitions"):
                self.report([], bootstrap_repetitions=value)
        for value in (True, False, -1, 2**32, 0.0, "0", [], {}):
            with self.subTest(seed=value), self.assertRaisesRegex(ValueError, "bootstrap_seed"):
                self.report([], bootstrap_seed=value)
        with self.assertRaisesRegex(ValueError, "requires"):
            self.report([], bootstrap_repetitions=None, bootstrap_seed=0)
        self.assertIsNone(validate_bootstrap(None, None))
        self.assertEqual(validate_bootstrap(10000, 2**32 - 1), 2**32 - 1)

    def test_cli_is_deterministic_offline_and_errors_emit_no_partial_json(self):
        fixture = Path(__file__).parent / "fixtures" / "synthetic_pbp.csv"
        args = ["--csv", str(fixture), "--source-label", "Synthetic verification fixture",
                "--team", "CAR", "--season", "2024", "--before-week", "3", "--compare-league"]
        outputs = []
        for _ in range(2):
            stdout = io.StringIO()
            with patch("socket.socket", side_effect=AssertionError("network forbidden")), redirect_stdout(stdout):
                self.assertEqual(main(args + ["--bootstrap-repetitions", "200", "--bootstrap-seed", "0"]), 0)
            outputs.append(stdout.getvalue())
        self.assertEqual(outputs[0], outputs[1])
        result = json.loads(outputs[0])["uncertainty"]
        self.assertEqual(result["overall"]["selected"]["dropback_rate"]["support_games"], {"selected": 2})
        self.assertEqual(result["overall"]["selected"]["dropback_rate"]["status"], "insufficient_games")
        for extra in (["--bootstrap-seed", "0"], ["--bootstrap-repetitions", "199"]):
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(main(args + extra), 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("bootstrap_", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
