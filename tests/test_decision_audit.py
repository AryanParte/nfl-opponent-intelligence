"""Test the raw-record oracle and its ability to catch broken production results."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import csv
from dataclasses import replace
from decimal import Decimal, getcontext, localcontext
from io import StringIO
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from opponent_intelligence.decision import DecisionRequest, build_decision_evidence
from opponent_intelligence.pbp import _load_csv_bytes
from validation import decision_audit as audit


FIELDS = ("game_id", "play_id", "season", "season_type", "week", "posteam", "defteam",
          "play_type", "down", "ydstogo", "qb_dropback", "qb_kneel", "qb_spike",
          "two_point_attempt", "epa", "yardline_100", "score_differential", "qtr",
          "quarter_seconds_remaining")


def row(**changes):
    return dict(game_id="SYNTHETIC_A", play_id=1, season=2024, season_type="REG", week=1,
                posteam="CAR", defteam="ATL", play_type="run", down=3, ydstogo=4,
                qb_dropback=0, qb_kneel=0, qb_spike=0, two_point_attempt=0, epa=0,
                yardline_100=38, score_differential=-3, qtr=4,
                quarter_seconds_remaining=134) | changes


def encoded(rows):
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, FIELDS)
    writer.writeheader()
    writer.writerows(dict(item, play_id=i) for i, item in enumerate(rows))
    return stream.getvalue().encode()


def invented_games():
    rows = []
    for game in range(5):
        for team, defense, offset in (("CAR", "ATL", 0), ("ATL", "CAR", 1)):
            for flag, count in ((0, game + 1), (1, 6 - game)):
                rows.extend(row(game_id=f"SYNTHETIC_{game}", week=game + 1,
                                posteam=team, defteam=defense, qb_dropback=flag,
                                play_type="run" if flag == 0 else "pass",
                                epa=game - 2 + offset) for _ in range(count))
    return rows


class DecisionAuditTests(unittest.TestCase):
    def setUp(self):
        self.request = DecisionRequest(team="CAR", season=2024, before_week=19,
                                       down=3, distance_min=4, distance_max=4,
                                       compare_league=True, bootstrap_repetitions=200,
                                       bootstrap_seed=17)

    def run_audit(self, rows, request=None):
        raw = encoded(rows)
        return audit.reconcile(raw, _load_csv_bytes(raw), [("invented", request or self.request)])

    def test_hand_calculated_points_dropback_mapping_and_null_states(self):
        rows = [row(), row(play_type="pass", qb_dropback=1, epa=2),
                row(play_type="run", qb_dropback=1, epa=4),
                row(posteam="ATL", defteam="CAR", play_type="pass", qb_dropback=1, epa=6)]
        result = self.run_audit(rows)["cases"][0]
        run, passed = result["selected"]
        self.assertEqual((run["plays"], run["epa_per_play"], run["success_rate"]), (1, 0.0, 0.0))
        self.assertEqual((passed["plays"], passed["epa_per_play"], passed["success_rate"]), (2, 3.0, 1.0))
        self.assertEqual(passed["frequency"], 2 / 3)
        self.assertEqual(result["baseline"][1]["difference"]["epa_per_play"], -3.0)
        self.assertEqual(result["baseline"][0]["frequency"], 0.0)
        self.assertIsNone(result["baseline"][0]["epa_per_play"])
        self.assertEqual(result["uncertainty"]["selected_epa"]["run"]["status"], "insufficient_games")

    def test_missing_epa_does_not_remove_calls_and_zero_is_observed(self):
        result = self.run_audit([row(), row(epa="NA"), row(qb_dropback=1, epa="")])["cases"][0]
        run, passed = result["selected"]
        self.assertEqual((run["plays"], run["epa_observations"], run["missing_epa"]), (2, 1, 1))
        self.assertEqual(run["frequency_denominator"], 3)
        self.assertIsNone(passed["epa_per_play"])
        reference = audit.raw_reference(audit.raw_eligible(encoded([row(qb_dropback=1, epa="")])), self.request)
        self.assertEqual(reference["candidates"][1]["availability"]["outcomes"], "missing_epa")
        self.assertEqual(result["uncertainty"]["selected_epa"]["pass"]["support_games"], {"selected": 0})

    def test_eligibility_and_temporal_boundaries_are_independent_of_builder(self):
        rows = [row(), row(qb_kneel=1), row(qb_spike=1), row(two_point_attempt=1),
                row(play_type="no_play"), row(play_type=""), row(week=19, epa=1000),
                row(season_type="POST", week=19, epa=2000), row(season=2025, epa=3000)]
        result = self.run_audit(rows)
        self.assertEqual(result["eligible_rows"], 4)
        self.assertEqual(result["cases"][0]["selected"][0]["plays"], 1)
        self.assertEqual(self.run_audit(rows, replace(self.request, before_week=1))["cases"][0]["selected"][0]["plays"], 0)
        post = self.run_audit(rows, replace(self.request, season_type="POST", before_week=23))
        self.assertEqual(post["cases"][0]["selected"][0]["epa_per_play"], 2000)

    def test_all_context_stages_missingness_defaults_and_exact_bounds(self):
        rows = [row(), row(yardline_100=""), row(score_differential=""), row(qtr=""),
                row(quarter_seconds_remaining=""), row(yardline_100=39), row(score_differential=-2),
                row(qtr=5), row(quarter_seconds_remaining=135), row(down=2), row(ydstogo=5)]
        request = replace(self.request, yardline_min=38, yardline_max=38, score_min=-3, score_max=-3,
                          period="Q4", clock_min=134, clock_max=134)
        result = self.run_audit(rows, request)["cases"][0]
        self.assertEqual(result["selected"][0]["plays"], 1)
        reference = audit.raw_reference(audit.raw_eligible(encoded(rows)), request)
        self.assertEqual(reference["data_quality"]["filter_order"],
                         ["field_position", "score_differential", "period", "clock", "down", "distance"])
        self.assertEqual(reference["data_quality"]["score_differential_filter"]["plays_before_filter"], 9)
        for field in ("yardline_100", "score_differential", "qtr", "quarter_seconds_remaining"):
            self.assertEqual(sum(v.get("missing_" + field, 0) for v in reference["data_quality"].values()
                                 if isinstance(v, dict)), 1)
        # Explicit zero differs from omitted bounds; OT includes periods >=5.
        self.run_audit(rows + [row(qtr=6, quarter_seconds_remaining=0)],
                       replace(self.request, period="OT", clock_max=0, yardline_max=100, score_max=0))

    def test_seeded_expanded_row_oracle_and_selected_only(self):
        rows = invented_games()
        paired = self.run_audit(rows)["cases"][0]
        self.assertEqual(paired["uncertainty"]["checked_entries"], 18)
        self.assertEqual(paired["uncertainty"]["selected_epa"]["run"]["status"], "ok")
        self.assertEqual(paired["uncertainty"]["selected_epa"]["run"]["support_games"], {"selected": 5})
        selected = self.run_audit(rows, replace(self.request, compare_league=False))["cases"][0]
        self.assertNotIn("baseline", selected)
        self.assertEqual(selected["uncertainty"]["checked_entries"], 6)
        plain = self.run_audit(rows, replace(self.request, bootstrap_repetitions=None, bootstrap_seed=None))
        self.assertNotIn("uncertainty", plain["cases"][0])

    def test_reference_does_not_call_production_selection_metrics_or_sampler(self):
        rows = audit.raw_eligible(encoded(invented_games()))
        with patch("opponent_intelligence.cohort.filter_context", side_effect=AssertionError("selector reused")), \
             patch("opponent_intelligence.metrics.summarize_plays", side_effect=AssertionError("metrics reused")), \
             patch("opponent_intelligence.uncertainty._bootstrap_rows", side_effect=AssertionError("sampler reused")), \
             patch.object(audit, "build_decision_evidence", side_effect=AssertionError("builder reused")):
            self.assertEqual(audit.raw_reference(rows, self.request)["population"]["plays"], 35)

    def test_mutated_results_are_detected_with_precise_paths(self):
        mutations = (
            (("candidates", 0, "frequency"), -1),
            (("candidates", 1, "epa_per_play"), 100),
            (("candidates", 0, "games"), 100),
            (("league_comparison", "candidates", 1, "difference", "epa_per_play"), 100),
            (("data_quality", "distance_filter", "plays_after_filter"), 100),
            (("uncertainty", "candidates", 0, "selected", "epa_per_play", "support_games", "selected"), 100),
            (("uncertainty", "candidates", 0, "selected", "epa_per_play", "interval", "lower"), 100),
            (("uncertainty", "candidates", 1, "difference", "frequency_pp", "valid_replicates"), 0),
            (("comparison", "preferred_candidate"), "pass"),
            (("cohort", "before_week_exclusive"), 23),
            (("uncertainty", "resampling_unit"), "play_id"),
            (("source", "sha256"), "incorrect"),
        )
        for keys, value in mutations:
            with self.subTest(keys=keys):
                def faulty(*args, **kwargs):
                    result = deepcopy(build_decision_evidence(*args, **kwargs))
                    node = result
                    for key in keys[:-1]:
                        node = node[key]
                    node[keys[-1]] = value
                    return result
                with patch.object(audit, "build_decision_evidence", side_effect=faulty), \
                     self.assertRaises(audit.AuditMismatch) as error:
                    self.run_audit(invented_games())
                self.assertIn(str(keys[-1]), str(error.exception))

    def test_source_hash_and_eligible_identity_disagreements_fail(self):
        raw = encoded([row()])
        parsed = _load_csv_bytes(raw)
        with self.assertRaisesRegex(audit.AuditMismatch, "fingerprint"):
            audit.reconcile(raw + b"\n", parsed, [])
        with self.assertRaisesRegex(audit.AuditMismatch, "identities"):
            audit.reconcile(raw, replace(parsed, plays=()), [])
        with_manifest = replace(parsed, source_manifest={"season": 2024, "revision": "verified"})
        def corrupt_manifest(dataset, *args, **kwargs):
            dataset.source_manifest["revision"] = "changed"
            return build_decision_evidence(dataset, *args, **kwargs)
        with patch.object(audit, "build_decision_evidence", side_effect=corrupt_manifest), \
             self.assertRaisesRegex(audit.AuditMismatch, "source.snapshot.revision"):
            audit.reconcile(raw, with_manifest, [("invented", self.request)])

    def test_quantiles_support_and_valid_draw_gate_boundaries(self):
        values = [Decimal(i) for i in range(200)]
        result = audit.interval(values, {"selected": 5}, 200, "proportion")
        self.assertEqual(result["interval"], {"lower": 4.975, "upper": 194.025})
        for support, expected in ((0, "undefined_estimate"), (4, "insufficient_games")):
            self.assertEqual(audit.interval(values, {"selected": support}, 200, "")["status"], expected)
        self.assertEqual(audit.interval(values[:189], {"selected": 5}, 200, "")["status"], "too_few_valid_replicates")
        self.assertEqual(audit.interval(values[:190], {"selected": 5}, 200, "")["status"], "ok")
        self.assertEqual(audit.interval([Decimal(0)] * 200, {"selected": 5}, 200, "")["status"], "degenerate_interval")

    def test_numeric_comparison_is_strict_and_finite(self):
        audit.check(1 + 5e-13, 1.0)
        for actual, expected in ((True, 1), (1.0, 1), (float("nan"), 0.0),
                                 (float("inf"), 0.0), (0, None), (1.0000001, 1.0),
                                 ({}, {"missing": 1}), ([1], [])):
            with self.subTest(actual=actual), self.assertRaises(audit.AuditMismatch):
                audit.check(actual, expected)

    def test_determinism_context_isolation_and_no_network(self):
        rows = invented_games()
        state, precision = random.getstate(), getcontext().prec
        first = self.run_audit(rows)
        with localcontext() as context, \
             patch("socket.create_connection", side_effect=AssertionError("network forbidden")):
            context.prec = 7
            self.assertEqual(first, self.run_audit(rows))
        self.assertEqual(first, self.run_audit(list(reversed(rows))))
        self.assertEqual((state, precision), (random.getstate(), getcontext().prec))
        self.assertEqual(json.loads(json.dumps(first, allow_nan=False)), first)

    def test_pinned_source_rejection_and_cli_failures_have_no_partial_json(self):
        with patch.object(audit, "_read_snapshot", return_value=(b"wrong", {"archive": {"sha256": "wrong"}})), \
             self.assertRaisesRegex(audit.AuditMismatch, "pinned"):
            audit.audit_snapshot(Path("unused"))
        with tempfile.TemporaryDirectory() as temporary:
            saved = Path(temporary) / "receipt.json"
            saved.write_text('{"version": 1}')
            for receipt, expected_code in (({"version": 1}, 0), ({"version": 2}, 1),
                                           ({"version": True}, 1), ({"version": 1.0}, 1)):
                out, err = StringIO(), StringIO()
                with patch.object(audit, "audit_snapshot", return_value=receipt), redirect_stdout(out), redirect_stderr(err):
                    code = audit.main(["--snapshot", "unused", "--check", str(saved)])
                self.assertEqual(code, expected_code)
                self.assertEqual(saved.read_text(), '{"version": 1}')
                if code:
                    self.assertEqual(out.getvalue(), "")
                    self.assertIn("saved receipt differs", err.getvalue())
                else:
                    self.assertEqual(json.loads(out.getvalue()), receipt)
                    self.assertEqual(err.getvalue(), "")

    def test_committed_receipt_matches_fixed_case_definitions_and_reconciles_counts(self):
        path = Path(__file__).resolve().parents[1] / "docs/evidence/pbp-2024-23370d5d10f8.decision-audit.json"
        receipt = json.loads(path.read_text())
        self.assertEqual(receipt["source"]["archive"]["sha256"], audit.ARCHIVE_SHA256)
        self.assertEqual(receipt["source"]["decoded_csv"]["sha256"], audit.CSV_SHA256)
        self.assertEqual(receipt["eligible_rows"], 34902)
        self.assertEqual([case["id"] for case in receipt["cases"]], [name for name, _ in audit.CASES])
        for case, (_, options) in zip(receipt["cases"], audit.CASES):
            expected = dict(team="CAR", season=2024, before_week=19, down=1,
                            distance_min=10, distance_max=10, season_type="REG",
                            compare_league=True, minimum_plays=30,
                            bootstrap_repetitions=200, bootstrap_seed=17) | options
            self.assertEqual(case["request"], expected)
            self.assertRegex(case["reference_sha256"], "^[0-9a-f]{64}$")
            for side, population in (("selected", "population"), ("baseline", "baseline_population")):
                self.assertEqual(sum(c["plays"] for c in case[side]), case[population]["plays"])
                for c in case[side]:
                    self.assertEqual(c["frequency_denominator"], case[population]["plays"])
                    self.assertEqual(c["epa_observations"] + c["missing_epa"], c["plays"])
            self.assertEqual(sum(case["uncertainty"]["status_counts"].values()), 18)


if __name__ == "__main__":
    unittest.main()
