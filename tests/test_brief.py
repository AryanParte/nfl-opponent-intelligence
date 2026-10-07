"""Rendering and saved-input contracts; all generated play records are synthetic."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import io
import json
from pathlib import Path
import random
import re
from string import punctuation
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from opponent_intelligence.brief import main, render_brief
from opponent_intelligence.pbp import Dataset, OPTIONAL_COLUMNS, Play, load_csv
from opponent_intelligence.report import build_report


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "synthetic_pbp.csv"


def visible(text):
    """Read literal Markdown escapes for exact, hand-calculated text assertions."""
    return re.sub(r"\\([" + re.escape(punctuation) + r"])", r"\1", text)


def set_at(value, path, replacement):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


class BriefTests(unittest.TestCase):
    def report(self, **changes):
        options = dict(team="CAR", season=2024, before_week=3,
                       source_label="Synthetic verification fixture; not real NFL observations")
        options.update(changes)
        return build_report(load_csv(FIXTURE), **options)

    def clustered_report(self, constant=False):
        plays = []
        for index in range(5):
            row = Play(game_id=f"SYNTHETIC_{index}", play_id=1, season=2024, season_type="REG", week=1,
                       offense="CAR", defense="ATL", down=1, yards_to_go=10,
                       dropback=index % 2 == 0 if not constant else False,
                       epa=float(index - 2) if not constant else 0.0)
            plays += [row, replace(row, play_id=2, offense="ATL", defense="CAR", epa=row.epa + 1)]
        source = Dataset(tuple(plays), "0" * 64, len(plays), {})
        return build_report(source, team="CAR", season=2024, before_week=2, source_label="Synthetic typed records",
                            compare_league=True, bootstrap_repetitions=200, bootstrap_seed=0)

    def invoke(self, content, args=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch("sys.stdin", io.StringIO(content)), redirect_stdout(stdout), redirect_stderr(stderr), \
                patch("socket.socket", side_effect=AssertionError("network forbidden")):
            code = main(["--report", "-"] if args is None else args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_hand_calculated_counts_rates_differences_and_traceability(self):
        report = self.report(compare_league=True)
        text = visible(render_brief(report))
        self.assertIn("| Dropback rate (all eligible plays) | 50.0% | 100.0% | -50.0 pp |", text)
        self.assertIn("| Success rate (observed EPA only) | 60.0% | 100.0% | -40.0 pp |", text)
        self.assertIn("| EPA per observed play | 0.040 | 3.000 | -2.960 |", text)
        self.assertIn("| Overall | selected | 6 / 2 | 3 / 3 | 5 / 1 | plays, EPA |", text)
        self.assertIn("| Overall | baseline | 1 / 1 | 1 / 0 | 1 / 0 | plays, EPA |", text)
        self.assertIn("| Down 2, medium | selected | 0.0% | unavailable | unavailable |", text)
        self.assertIn("| Down 2, short | unavailable | unavailable | unavailable |", text)
        self.assertIn("week < 3 (exclusive)", text)
        self.assertIn("Synthetic verification fixture; not real NFL observations", text)
        self.assertIn("| data_quality.input_rows | 14 |", text)
        expected = sha256(json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                                     allow_nan=False).encode()).hexdigest()
        self.assertIn(expected, text)
        self.assertIn(sha256(FIXTURE.read_bytes()).hexdigest(), text)

    def test_pure_deterministic_offline_and_key_order_independent(self):
        report = self.report(compare_league=True, bootstrap_repetitions=200)
        original, state = deepcopy(report), random.getstate()
        with patch("socket.socket", side_effect=AssertionError("network forbidden")):
            first = render_brief(report)
            self.assertEqual(first, render_brief(json.loads(json.dumps(report, sort_keys=True))))
            self.assertEqual(first, render_brief(report))
        self.assertEqual(report, original)
        self.assertEqual(random.getstate(), state)
        self.assertTrue(first.endswith("\n"))
        self.assertFalse(first.endswith("\n\n"))

    def test_defense_keeps_offensive_sign_and_success_not_stops(self):
        text = visible(render_brief(self.report(team="ATL", side="defense")))
        self.assertIn("ATL defense", text)
        self.assertIn("opposing offenses facing this defense", text)
        self.assertIn("not defensive stops", text)
        self.assertIn("| EPA per observed play | 0.050 |", text)
        self.assertIn("| Success rate (observed EPA only) | 75.0% |", text)
        self.assertIn("| Overall | selected | 5 / 1 | 3 / 2 | 4 / 1 | plays, EPA |", text)

    def test_absent_comparison_and_uncertainty_differ_from_requested_empty(self):
        plain = render_brief(self.report())
        self.assertIn("No baseline or comparison is inferred", plain)
        self.assertIn("Play-count warnings alone do not estimate uncertainty", plain)
        empty = visible(render_brief(self.report(before_week=1, compare_league=True, bootstrap_repetitions=200)))
        self.assertNotIn("Not requested", empty)
        self.assertIn("No selected-team situations", empty)
        self.assertIn("unavailable (undefined_estimate)", empty)
        self.assertIn("| uncertainty.performed_repetitions | 0 |", empty)
        self.assertIn("| Dropback rate (all eligible plays) | unavailable | unavailable | unavailable |", empty)
        baseline_only = visible(render_brief(self.report(team="NYJ", compare_league=True, bootstrap_repetitions=200)))
        self.assertIn("No selected-team situations", baseline_only)
        self.assertIn("| Overall | baseline | 7 / 2 | 4 / 3 | 6 / 1 | plays, EPA |", baseline_only)

    def test_zero_epa_missing_epa_and_separate_thresholds(self):
        source = load_csv(FIXTURE)
        for epa, expected in ((0.0, "0.000"), (None, "unavailable")):
            modified = replace(source, plays=tuple(replace(p, epa=epa) for p in source.plays))
            report = build_report(modified, team="CAR", season=2024, before_week=3,
                                  source_label="Synthetic", minimum_plays=6)
            text = visible(render_brief(report))
            self.assertIn(f"| EPA per observed play | {expected} |", text)
            self.assertIn("| Dropback rate (all eligible plays) | 50.0% |", text)
            if epa is None:
                self.assertIn("| Overall | selected | 6 / 2 | 3 / 3 | 0 / 6 | EPA |", text)
            else:
                self.assertIn("| Success rate (observed EPA only) | 0.0% |", text)
        text = visible(render_brief(self.report(minimum_plays=6)))
        self.assertIn("| Overall | selected | 6 / 2 | 3 / 3 | 5 / 1 | EPA |", text)

    def test_combined_contexts_preserve_zero_unbounded_and_offense_coordinates(self):
        source = load_csv(FIXTURE)
        source = replace(source, plays=tuple(replace(p, yardline_100=20, score_differential=0,
                                                     qtr=5, quarter_seconds_remaining=0) for p in source.plays),
                         optional_columns=OPTIONAL_COLUMNS)
        report = build_report(source, team="ATL", side="defense", season=2024, before_week=3,
                              source_label="Synthetic", yardline_min=0, yardline_max=20,
                              score_max=0, period="OT", clock_max=0, compare_league=True)
        text = visible(render_brief(report))
        for field, expected in (("field_position.minimum_inclusive", "0.0"), ("field_position.maximum_inclusive", "20.0"),
                                ("score_differential.minimum_inclusive", "null"), ("score_differential.maximum_inclusive", "0"),
                                ("period.label", "OT"), ("clock.minimum_inclusive", "0"), ("clock.maximum_inclusive", "0")):
            self.assertIn(f"| cohort.{field} | {expected} |", text)
        self.assertIn("| data_quality.clock_filter.plays_after_filter | 5 |", text)
        self.assertIn("| league_comparison.data_quality.clock_filter.plays_after_filter | 2 |", text)

    def test_situation_matching_uses_keys_not_list_positions(self):
        report = self.report(compare_league=True, bootstrap_repetitions=200)
        report["league_comparison"]["situations"].reverse()
        report["uncertainty"]["situations"].reverse()
        text = visible(render_brief(report))
        self.assertIn("| Down 1, long | baseline | 100.0% | 100.0% | 3.000 |", text)
        self.assertIn("| Down 2, short | baseline | unavailable | unavailable | unavailable |", text)
        self.assertLess(text.index("| Down 1, long"), text.index("| Down 2, short"))

    def test_interval_units_counts_and_all_unavailable_states_are_visible(self):
        sparse = visible(render_brief(self.report(compare_league=True, bootstrap_repetitions=200)))
        self.assertIn("unavailable (insufficient_games)", sparse)
        self.assertIn("unavailable (undefined_estimate)", sparse)
        constant = visible(render_brief(self.clustered_report(constant=True)))
        self.assertIn("unavailable (degenerate_interval)", constant)
        report = self.clustered_report()
        overall = report["uncertainty"]["overall"]
        # Hand-specified, explicitly synthetic presentation cases, not bootstrap validation.
        overall["selected"]["dropback_rate"]["interval"] = {"lower": 0.125, "upper": 0.875}
        overall["selected"]["epa_per_play"]["interval"] = {"lower": -0.25, "upper": 0.125}
        difference = overall["difference"]["success_rate_pp"]
        difference.update(interval={"lower": -12.5, "upper": 34.0}, status="ok")
        item = overall["selected"]["success_rate"]
        item.update(interval=None, status="too_few_valid_replicates", valid_replicates=180, undefined_replicates=20)
        text = visible(render_brief(report))
        self.assertIn("[12.5%, 87.5%] (ok)", text)
        self.assertIn("[-12.5 pp, 34.0 pp] (ok)", text)
        self.assertIn("[-0.250, 0.125] (ok)", text)
        self.assertIn("| Overall | selected: success_rate | unavailable (too_few_valid_replicates) | selected=5 | yes | 180 / 20 |", text)
        self.assertIn("not calibrated coverage", text)
        self.assertIn("available intervals condition on defined draws", text)

    def test_every_uncertainty_entry_and_report_warning_is_retained(self):
        report = self.report(compare_league=True, bootstrap_repetitions=200)
        rendered = visible(render_brief(report))
        block = rendered.split("## Exploratory game-level uncertainty\n", 1)[1].split("## Source and provenance", 1)[0]
        self.assertEqual(len(re.findall(r"^\| (?:Overall|Down \d, \w+) \|", block, flags=re.M)), 45)
        for section in (report, report["league_comparison"], report["uncertainty"]):
            for warning in section["warnings"]:
                self.assertIn(warning, rendered)

    def test_markdown_html_links_tables_and_controls_are_literal_data(self):
        report = self.report()
        report["source"]["label"] = 'Synthetic | <img src=x>\n# false heading ![track](https://invalid.test) `code` &lt;b&gt;\u202e'
        report["warnings"].append("```\n- [danger](javascript:alert(1))\x00")
        text = render_brief(report)
        self.assertNotRegex(text, r"(?<!\\)<img")
        self.assertNotIn("![track]", text)
        self.assertNotIn("\n# false", text)
        self.assertNotIn("[danger]", text)
        self.assertNotIn("\u202e", text)
        self.assertNotIn("\x00", text)
        self.assertIn(r"\|", text)
        self.assertIn(r"\<img", text)
        self.assertIn(r"\\u202e", text)

    def test_missing_unsupported_non_json_and_nonfinite_inputs_fail(self):
        for value in (None, [], "report", {}, {"schema_version": 1}, {"schema_version": True}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                render_brief(value)
        for path, value in ((("schema_version",), 3), (("overall",), []), (("source", "label"), ""),
                            (("source", "sha256"), "not-a-fingerprint"), (("cohort", "side"), "both"),
                            (("cohort", "team"), "not a team"),
                            (("metric_context", "interpretation"), "stops"), (("warnings",), "warning"),
                            (("extra",), float("nan")), (("extra",), float("inf")), (("extra",), object()),
                            (("extra",), {0: "not a string key"})):
            report = self.report()
            set_at(report, path, value)
            with self.subTest(path=path, value=value), self.assertRaises(ValueError):
                render_brief(report)

    def test_inconsistent_metrics_counts_nulls_rates_and_flags_fail(self):
        for key, value in (("plays", True), ("games", 7), ("dropbacks", -1), ("designed_runs", 1),
                           ("epa_observations", 6), ("dropback_rate", 0.9), ("success_rate", None),
                           ("success_rate", 1.1), ("success_rate", 0.5), ("epa_per_play", "0.04"), ("small_sample", False),
                           ("small_epa_sample", 1)):
            report = self.report()
            report["overall"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                render_brief(report)
        report = self.report(before_week=1)
        report["overall"]["epa_per_play"] = 0.0
        with self.assertRaisesRegex(ValueError, "null"):
            render_brief(report)
        report = self.report(before_week=1)
        report["situations"] = [dict(report["overall"], down=1, distance="long")]
        with self.assertRaisesRegex(ValueError, "observed plays"):
            render_brief(report)

    def test_inconsistent_source_and_population_ledgers_fail(self):
        for path, value in ((("data_quality", "input_rows"), 15),
                            (("data_quality", "eligible_rows_outside_cohort"), 3),
                            (("data_quality", "excluded_rows_by_reason", "kneel"), -1),
                            (("league_comparison", "data_quality", "excluded_selected_team_rows"), 5),
                            (("league_comparison", "data_quality", "plays_after_context_filters"), 2),
                            (("league_comparison", "data_quality", "filter_order"), ["period"])):
            report = self.report(compare_league=True)
            set_at(report, path, value)
            with self.subTest(path=path), self.assertRaises(ValueError):
                render_brief(report)

    def test_context_semantics_and_stage_accounting_cannot_silently_change(self):
        source = load_csv(FIXTURE)
        source = replace(source, plays=tuple(replace(p, yardline_100=20, score_differential=0,
                                                     qtr=4, quarter_seconds_remaining=120) for p in source.plays),
                         optional_columns=OPTIONAL_COLUMNS)
        original = build_report(source, team="CAR", season=2024, before_week=3, source_label="Synthetic",
                                yardline_max=20, score_max=0, period="Q4", clock_max=120)
        for path, value in ((("cohort", "field_position", "perspective"), "defense"),
                            (("cohort", "field_position", "minimum_inclusive"), 30),
                            (("cohort", "score_differential", "maximum_inclusive"), 0.5),
                            (("cohort", "period", "label"), "OT"), (("cohort", "clock", "timing"), "post_play"),
                            (("cohort", "clock", "maximum_inclusive"), 901),
                            (("data_quality", "clock_filter", "missing_quarter_seconds_remaining"), 1),
                            (("data_quality", "filter_order"), ["clock", "period", "score_differential", "field_position"])):
            report = deepcopy(original)
            set_at(report, path, value)
            with self.subTest(path=path), self.assertRaises(ValueError):
                render_brief(report)

    def test_invalid_comparisons_and_bucket_alignment_fail(self):
        for path, value in ((("cohort", "before_week_exclusive"), 4), (("overall_difference", "epa_per_play"), 2.96),
                            (("population", "excluded_team"), "ATL"), (("population", "scope"), "entire_league"),
                            (("population", "teams"), ["ATL", "ATL"]), (("population", "team_count"), 32),
                            (("population", "shared_games_with_selected"), 10), (("situations",), []),
                            (("difference_convention",), "baseline_minus_selected"),
                            (("situations", 1, "difference", "epa_per_play"), 0)):
            report = self.report(compare_league=True)
            set_at(report["league_comparison"], path, value)
            with self.subTest(path=path), self.assertRaises(ValueError):
                render_brief(report)
        for block in ("situations", "league_comparison", "uncertainty"):
            report = self.report(compare_league=True, bootstrap_repetitions=200)
            rows = report[block] if block == "situations" else report[block]["situations"]
            rows.append(deepcopy(rows[0]))
            with self.subTest(block=block), self.assertRaisesRegex(ValueError, "duplicate"):
                render_brief(report)

    def test_invalid_uncertainty_metadata_support_units_bounds_and_counts_fail(self):
        paths = ((("method",), "future_method"), (("nominal_level",), 0.8), (("seed",), True),
                 (("repetitions",), 10), (("resampling_games",), 99), (("performed_repetitions",), 199),
                 (("shared_game_weights",), False), (("situations",), []),
                 (("overall", "selected", "epa_per_play", "unit"), "points_total"),
                 (("overall", "selected", "epa_per_play", "support_games", "selected"), 6),
                 (("overall", "selected", "epa_per_play", "few_games"), False),
                 (("overall", "selected", "epa_per_play", "valid_replicates"), 201),
                 (("overall", "selected", "epa_per_play", "status"), "reliable"),
                 (("overall", "selected", "epa_per_play", "interval"), None),
                 (("overall", "selected", "epa_per_play", "interval"), {"lower": 2, "upper": 1}),
                 (("overall", "selected", "dropback_rate", "interval"), {"lower": -0.1, "upper": 0.9}))
        for path, value in paths:
            report = self.clustered_report()
            set_at(report["uncertainty"], path, value)
            with self.subTest(path=path), self.assertRaises(ValueError):
                render_brief(report)

    def test_snapshot_provenance_and_license_are_preserved_not_reauthenticated(self):
        report = self.report()
        manifest = json.loads((ROOT / "docs/evidence/pbp-2024-23370d5d10f8.manifest.json").read_text())
        report["source"].update(snapshot=manifest, sha256=manifest["decoded_csv"]["sha256"],
                                 label="Synthetic rendering case using copied provenance metadata; not a real-data finding")
        original = deepcopy(report)
        text = visible(render_brief(report))
        for value in (manifest["archive"]["sha256"], manifest["retrieved_at_utc"], manifest["source"]["download_url"],
                      manifest["source"]["asset_updated_at_utc"], "CC-BY-4.0", "nflverse play-by-play data"):
            self.assertIn(value, text)
        self.assertIn("not revalidated by this renderer", text)
        self.assertEqual(report, original)
        report["source"]["snapshot"]["decoded_csv"]["sha256"] = "1" * 64
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            render_brief(report)
        del original["source"]["snapshot"]["license"]
        with self.assertRaisesRegex(ValueError, "license"):
            render_brief(original)

    def test_cli_file_stdin_and_subprocess_are_identical_and_offline(self):
        report = self.report(compare_league=True, bootstrap_repetitions=200)
        content = json.dumps(report)
        expected = render_brief(report)
        self.assertEqual(self.invoke(content), (0, expected, ""))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(content, encoding="utf-8")
            self.assertEqual(self.invoke("", ["--report", str(path)]), (0, expected, ""))
            script = "import socket; socket.socket=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network forbidden')); from opponent_intelligence.brief import main; raise SystemExit(main())"
            result = subprocess.run([sys.executable, "-c", script, "--report", str(path)],
                                    capture_output=True, text=True, cwd=ROOT, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, expected)
            self.assertEqual(path.read_text(), content)

    def test_cli_invalid_json_duplicates_limits_and_encoding_have_no_partial_output(self):
        for content in ("", "null", "[]", "{", '{"schema_version":2,"schema_version":1}',
                        '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}', json.dumps(self.report()) + "garbage"):
            code, stdout, stderr = self.invoke(content)
            self.assertEqual(code, 2)
            self.assertEqual(stdout, "")
            self.assertTrue(stderr.startswith("error:"))
        with patch("opponent_intelligence.brief.MAX_REPORT_BYTES", 50):
            self.assertEqual(self.invoke("x" * 51)[0:2], (2, ""))
            self.assertEqual(self.invoke("é" * 30)[0:2], (2, ""))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            for content in (b"\xff", b"x" * 51):
                path.write_bytes(content)
                with patch("opponent_intelligence.brief.MAX_REPORT_BYTES", 50):
                    self.assertEqual(self.invoke("", ["--report", str(path)])[0:2], (2, ""))
            self.assertEqual(self.invoke("", ["--report", str(Path(directory) / "missing")])[0:2], (2, ""))

    def test_committed_examples_are_exactly_reproducible_without_raw_data(self):
        for name in ("synthetic", "car-2024-reg-before-week-19"):
            with self.subTest(name=name), patch("socket.socket", side_effect=AssertionError("network forbidden")):
                report = json.loads((ROOT / "docs/examples" / f"{name}.report.json").read_text(encoding="utf-8"))
                expected = (ROOT / "docs/examples" / f"{name}.md").read_text(encoding="utf-8")
                self.assertEqual(render_brief(report), expected)
                if name == "synthetic":
                    self.assertEqual(report, self.report(compare_league=True, bootstrap_repetitions=200, bootstrap_seed=0))
                    self.assertEqual(expected, render_brief(self.report(compare_league=True, bootstrap_repetitions=200, bootstrap_seed=0)))
                else:
                    self.assertEqual(report["overall"]["plays"], 984)
                    self.assertEqual(report["overall"]["games"], 17)
                    self.assertEqual(report["overall"]["dropbacks"], 626)
                    self.assertEqual(report["source"]["snapshot"]["license"]["identifier"], "CC-BY-4.0")


if __name__ == "__main__":
    unittest.main()
