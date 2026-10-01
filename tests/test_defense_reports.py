"""Independent synthetic expectations for defense selection, not NFL findings."""

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import unittest

from opponent_intelligence.pbp import Dataset, Play
from opponent_intelligence.report import build_report


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_pbp.csv"


class DefenseReportTests(unittest.TestCase):
    def setUp(self):
        base = Play("SYNTHETIC_A", 1, 2024, "REG", 1, "CAR", "ATL", 1, 10, True, 0.8)
        self.plays = (
            base,
            replace(base, play_id=2, down=2, yards_to_go=3, dropback=False, epa=0.2),
            replace(base, play_id=3, down=3, yards_to_go=7, epa=-1.2),
            replace(base, play_id=4, epa=0.4),
            replace(base, play_id=5, down=2, yards_to_go=6, dropback=False, epa=None),
            # Same game but ATL is on offense, not defense.
            replace(base, play_id=6, offense="ATL", defense="CAR", epa=3.0),
            # A second opponent facing ATL in the next week.
            replace(base, game_id="SYNTHETIC_B", week=2, offense="NO", down=4, yards_to_go=1, epa=0),
            replace(base, game_id="SYNTHETIC_B", play_id=2, week=2, offense="ATL", defense="NO", epa=-0.7),
            replace(base, game_id="SYNTHETIC_TARGET", week=3, epa=99),
            replace(base, game_id="SYNTHETIC_POST", season_type="POST", week=19, epa=8),
            replace(base, game_id="SYNTHETIC_NEXT_YEAR", season=2025, epa=88),
            replace(base, game_id="SYNTHETIC_OTHER_DEFENSE", week=2, defense="TB", epa=77),
        )
        # Pure report tests start from already validated typed records. Exclusions
        # are synthetic adapter accounting, not reclassified by the report.
        self.dataset = Dataset(self.plays, "0" * 64, 16, {"non_run_pass": 3, "two_point_attempt": 1})

    def report(self, **changes):
        options = dict(team="ATL", side="defense", season=2024, before_week=3,
                       source_label="Synthetic typed records; not real NFL observations")
        options.update(changes)
        return build_report(self.dataset, **options)

    def set_plays(self, plays):
        plays = tuple(plays)
        self.dataset = replace(self.dataset, plays=plays,
                               input_rows=len(plays) + sum(self.dataset.exclusions.values()))

    def test_hand_calculated_defense_metrics_include_multiple_opponents(self):
        overall = self.report()["overall"]
        self.assertEqual(overall["plays"], 6)
        self.assertEqual(overall["games"], 2)
        self.assertEqual(overall["dropbacks"], 4)
        self.assertEqual(overall["designed_runs"], 2)
        self.assertEqual(overall["epa_observations"], 5)
        self.assertEqual(overall["missing_epa"], 1)
        self.assertAlmostEqual(overall["dropback_rate"], 4 / 6)
        self.assertAlmostEqual(overall["epa_per_play"], 0.04)
        self.assertEqual(overall["success_rate"], 3 / 5)

    def test_schema_names_team_role_and_metric_perspective(self):
        result = self.report()
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["cohort"], {
            "team": "ATL", "side": "defense", "season": 2024, "season_type": "REG",
            "before_week_exclusive": 3, "minimum_plays_warning": 30,
        })
        self.assertEqual(result["metric_context"], {
            "perspective": "offense", "interpretation": "allowed", "success_condition": "epa > 0",
        })
        self.assertTrue(any("not sign-flipped" in warning for warning in result["warnings"]))

    def test_default_side_is_explicit_offense_and_measurements_are_unchanged(self):
        default = build_report(self.dataset, team="ATL", season=2024, before_week=3,
                               source_label="Synthetic typed records; not real NFL observations")
        self.assertEqual(default, self.report(side="offense"))
        self.assertEqual(default["cohort"]["side"], "offense")
        self.assertEqual(default["metric_context"]["interpretation"], "produced")
        self.assertEqual(default["overall"]["plays"], 2)
        self.assertAlmostEqual(default["overall"]["epa_per_play"], 1.15)

    def test_situation_splits_use_opponent_offense_down_distance(self):
        rows = {(r["down"], r["distance"]): r for r in self.report()["situations"]}
        self.assertEqual(set(rows), {(1, "long"), (2, "short"), (2, "medium"),
                                     (3, "long"), (4, "short")})
        self.assertEqual(rows[(1, "long")]["plays"], 2)
        self.assertEqual(rows[(1, "long")]["dropbacks"], 2)
        self.assertAlmostEqual(rows[(1, "long")]["epa_per_play"], 0.6)
        self.assertIsNone(rows[(2, "medium")]["epa_per_play"])
        self.assertEqual(rows[(3, "long")]["epa_per_play"], -1.2)
        self.assertEqual(rows[(4, "short")]["success_rate"], 0)
        self.assertEqual(sum(r["plays"] for r in rows.values()), 6)
        self.assertEqual(sum(r["epa_observations"] for r in rows.values()), 5)

    def test_epa_and_success_are_not_inverted_for_defense(self):
        for epa, success in ((0.8, 1), (-1.2, 0), (0.0, 0)):
            with self.subTest(epa=epa):
                self.set_plays((replace(self.plays[0], epa=epa),))
                result = self.report()["overall"]
                self.assertEqual(result["epa_per_play"], epa)
                self.assertEqual(result["success_rate"], success)

    def test_missing_epa_keeps_play_call_denominator_and_separate_warnings(self):
        result = self.report(minimum_plays=6)
        self.assertFalse(result["overall"]["small_sample"])
        self.assertTrue(result["overall"]["small_epa_sample"])
        self.assertTrue(any("Missing EPA" in warning for warning in result["warnings"]))
        self.set_plays((replace(self.plays[0], epa=None),))
        overall = self.report()["overall"]
        self.assertEqual(overall["plays"], 1)
        self.assertEqual(overall["dropback_rate"], 1)
        self.assertIsNone(overall["epa_per_play"])
        self.assertIsNone(overall["success_rate"])

    def test_defense_filters_target_week_season_and_season_type(self):
        self.assertEqual(self.report(before_week=2)["overall"]["plays"], 5)
        self.assertEqual(self.report(before_week=3)["overall"]["plays"], 6)
        self.assertEqual(self.report(before_week=4)["overall"]["plays"], 7)
        self.assertEqual(self.report(before_week=23)["overall"]["plays"], 7)
        self.assertEqual(self.report(before_week=23, season_type="POST")["overall"]["epa_per_play"], 8)
        self.assertEqual(self.report(season=2025)["overall"]["epa_per_play"], 88)

    def test_empty_defense_cohort_returns_null_rates_and_role_metadata(self):
        for changes in ({"before_week": 1}, {"team": "GB"}):
            with self.subTest(changes=changes):
                result = self.report(**changes)
                self.assertEqual(result["overall"]["plays"], 0)
                self.assertEqual(result["situations"], [])
                self.assertEqual(result["cohort"]["side"], "defense")
                self.assertEqual(result["metric_context"]["interpretation"], "allowed")
                for field in ("dropback_rate", "epa_per_play", "success_rate"):
                    self.assertIsNone(result["overall"][field])

    def test_one_matchup_has_identical_offense_and_defense_metrics(self):
        # One offense/defense matchup contains the exact same plays in either view.
        self.set_plays(self.plays[:5])
        offense = self.report(team="CAR", side="offense")
        defense = self.report()
        for field in ("overall", "situations", "data_quality", "source"):
            self.assertEqual(offense[field], defense[field])

    def test_swapping_team_roles_preserves_selected_measurements(self):
        original = self.report()
        self.set_plays(
            replace(p, offense=p.defense, defense=p.offense) for p in self.plays
        )
        mirrored = self.report(side="offense")
        for field in ("overall", "situations", "data_quality"):
            self.assertEqual(original[field], mirrored[field])

    def test_team_partitions_reconcile_without_summing_game_counts_or_rates(self):
        # Nine eligible REG/week 1-2 plays, eight observed EPA, seven dropbacks.
        for side, teams in (("offense", ("ATL", "CAR", "NO")),
                            ("defense", ("ATL", "CAR", "NO", "TB"))):
            with self.subTest(side=side):
                totals = [self.report(team=team, side=side)["overall"] for team in teams]
                self.assertEqual(sum(r["plays"] for r in totals), 9)
                self.assertEqual(sum(r["epa_observations"] for r in totals), 8)
                self.assertEqual(sum(r["dropbacks"] for r in totals), 7)

    def test_exclusions_and_source_are_not_recomputed_for_defense(self):
        result = self.report()
        self.assertEqual(result["data_quality"], {
            "input_rows": 16, "eligible_rows_all_teams": 12,
            "excluded_rows_by_reason": {"non_run_pass": 3, "two_point_attempt": 1},
            "eligible_rows_outside_cohort": 6,
        })
        self.assertEqual(result["source"]["sha256"], "0" * 64)
        quality = result["data_quality"]
        self.assertEqual(quality["input_rows"], result["overall"]["plays"]
                         + quality["eligible_rows_outside_cohort"]
                         + sum(quality["excluded_rows_by_reason"].values()))

    def test_invalid_side_is_never_silently_treated_as_offense(self):
        for side in ("", "Defense", "defence", "both", "defense ", None, True, 1, [], {}):
            with self.subTest(side=side):
                with self.assertRaisesRegex(ValueError, "side must be offense or defense"):
                    self.report(side=side)

    def test_cli_defense_is_deterministic_and_rejects_invalid_side_without_json(self):
        command = [sys.executable, "-m", "opponent_intelligence", "--csv", str(FIXTURE),
                   "--team", "ATL", "--side", "defense", "--season", "2024", "--before-week", "3",
                   "--source-label", "Synthetic verification fixture; not real NFL observations"]
        first = subprocess.run(command, capture_output=True, text=True, check=True)
        second = subprocess.run(command, capture_output=True, text=True, check=True)
        self.assertEqual(first.stdout, second.stdout)
        result = json.loads(first.stdout)
        self.assertEqual(result["cohort"]["side"], "defense")
        self.assertEqual(result["overall"]["plays"], 5)
        self.assertEqual(result["overall"]["dropbacks"], 3)
        self.assertEqual(result["overall"]["epa_observations"], 4)
        self.assertAlmostEqual(result["overall"]["epa_per_play"], 0.05)
        invalid = command.copy()
        invalid[invalid.index("--side") + 1] = "both"
        failed = subprocess.run(invalid, capture_output=True, text=True)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(failed.stdout, "")
        self.assertIn("invalid choice", failed.stderr)


if __name__ == "__main__":
    unittest.main()
