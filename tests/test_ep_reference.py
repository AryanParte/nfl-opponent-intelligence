"""Protocol checks and deliberate capture corruption; no real model predictions."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from validation import ep_reference as ep


ROOT = Path(__file__).resolve().parents[1]


def synthetic_capture(language):
    """Invented probabilities/identifiers solely to exercise the comparator."""
    fixture, digest = ep.load_fixture()
    rows = [{"id": case["id"], "features": list(case["features"]),
             "probabilities": [0.2, 0.1, 0.15, 0.05, 0.1, 0.05, 0.35], "ep": 1.1}
            for case in fixture["accepted"]]
    # Distinct known values catch prediction-row swaps even when IDs stay fixed.
    rows[1]["probabilities"] = [0.1, 0.2, 0.15, 0.05, 0.1, 0.05, 0.35]
    rows[1]["ep"] = -0.3
    return {
        "protocol_version": 1, "probability_origin": "synthetic_test", "fixture_sha256": digest,
        "source_commits": dict(ep.SOURCE_COMMITS), "model_sha256": "a" * 64,
        "artifact_manifest_sha256": "b" * 64,
        "runtime": {"language": language, "version": "synthetic-version",
                    "xgboost_version": "synthetic-version", "platform": "synthetic-platform",
                    "environment_sha256": "c" * 64, "runner_sha256": "d" * 64},
        "feature_order": list(ep.FEATURES), "class_order": list(ep.CLASSES),
        "batch": rows, "single": deepcopy(rows),
    }


class EPReferenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.fingerprint = ep.load_fixture()
        self.reference = synthetic_capture("R")
        self.candidate = synthetic_capture("Python")

    def compare(self):
        return ep.compare_captures(self.reference, self.candidate)

    def test_corpus_matches_hand_written_features_and_expected_rejections(self):
        self.assertEqual((len(self.fixture["accepted"]), len(self.fixture["rejected"])), (25, 16))
        # load_fixture validates all independently written rows against the oracle.
        states = [self.fixture["base_state"] | case["overrides"] for case in self.fixture["accepted"]]
        self.assertEqual({state["down"] for state in states}, {1, 2, 3, 4})
        self.assertEqual({state["roof"] for state in states}, {"outdoors", "dome", "open", "closed"})
        self.assertTrue({1999, 2001, 2002, 2005, 2006, 2013, 2014, 2017, 2018, 2024}
                        <= {state["season"] for state in states})
        self.assertEqual({state["qtr"] for state in states}, {1, 2, 3, 4})
        self.assertEqual(len(self.fingerprint), 64)

    def test_protocol_stays_aligned_with_pinned_audit(self):
        audit = json.loads((ROOT / "docs/evidence/fastrmodels-2.1.0-interface-audit.json").read_text())
        self.assertEqual(list(ep.FEATURES), audit["feature_order"]["ep"])
        self.assertEqual(list(ep.CLASSES), audit["outputs"]["ep"]["class_order"])
        self.assertEqual(list(ep.POINTS), audit["outputs"]["ep"]["points_weights"])
        for repository, pin in ep.SOURCE_COMMITS.items():
            self.assertEqual(pin, audit["sources"][f"nflverse/{repository}"]["commit"])
        self.assertIn(self.fingerprint, (ROOT / "docs/EP_REFERENCE_PROTOCOL.md").read_text())

    def test_no_missing_extra_coerced_or_unbounded_state_inputs(self):
        base = self.fixture["base_state"]
        for field in base:
            with self.subTest(missing=field):
                state = dict(base)
                del state[field]
                with self.assertRaises(ep.ProtocolError):
                    ep.feature_oracle(state)
        with self.assertRaises(ep.ProtocolError):
            ep.feature_oracle(base | {"epa": 4})
        for field in ("season", "qtr", "quarter_seconds_remaining", "down", "ydstogo",
                      "posteam_timeouts_remaining", "defteam_timeouts_remaining"):
            for value in (None, True, "1", 1.0, -1, 10 ** 400):
                with self.subTest(field=field, value_type=type(value).__name__):
                    with self.assertRaises(ep.ProtocolError):
                        ep.feature_oracle(base | {field: value})
        for value in (None, True, "50", float("nan"), float("inf"), 10 ** 400):
            with self.assertRaises(ep.ProtocolError):
                ep.feature_oracle(base | {"yardline_100": value})
        for value in (0, None, True):
            with self.assertRaises(ep.ProtocolError):
                ep.feature_oracle(base | {"neutral_site": value})
        with self.assertRaises(ep.ProtocolError):
            ep.feature_oracle(base | {"away_team": "CAR"})

    def test_half_clocks_zero_and_fractional_field_are_not_silently_repaired(self):
        base = self.fixture["base_state"]
        for quarter, clock, expected in ((1, 0, 900), (2, 900, 900), (2, 0, 0),
                                         (3, 900, 1800), (4, 134, 134), (4, 0, 0)):
            self.assertEqual(ep.feature_oracle(base | {"qtr": quarter,
                             "quarter_seconds_remaining": clock})[0], expected)
        self.assertEqual(ep.feature_oracle(base | {"yardline_100": 38.5})[1], 38.5)
        self.assertEqual(ep.feature_oracle(base | {"posteam_timeouts_remaining": 0})[-2], 0)

    def test_fixture_drift_duplicate_ids_and_false_rejections_fail(self):
        changed_bytes = ep.FIXTURE.read_bytes() + b"\n"
        with patch.object(Path, "read_bytes", return_value=changed_bytes):
            with self.assertRaisesRegex(ep.ProtocolError, "pinned corpus"):
                ep.load_fixture()
        for corrupt in ("features", "id", "rejection", "version", "label"):
            fixture = deepcopy(self.fixture)
            if corrupt == "features":
                fixture["accepted"][0]["features"][0] = 900
            elif corrupt == "id":
                fixture["rejected"][0]["id"] = "baseline"
            elif corrupt == "rejection":
                fixture["rejected"][0]["overrides"] = {}
            elif corrupt == "version":
                fixture["protocol_version"] = True
            else:
                fixture["label"] = "Real NFL forecasts"
            with self.subTest(corrupt=corrupt), self.assertRaises(ep.ProtocolError):
                ep.validate_fixture(fixture)

    def test_synthetic_agreement_is_not_artifact_or_predictive_validation(self):
        before = deepcopy((self.reference, self.candidate))
        result = self.compare()
        self.assertEqual(result["status"], "capture_comparison_pass")
        self.assertEqual(result["probability_origin"], "synthetic_test")
        self.assertEqual(result["cases"], 25)
        self.assertIs(result["artifact_bytes_attested"], False)
        self.assertIs(result["predictive_validation"], False)
        self.assertEqual((self.reference, self.candidate), before)

    def test_all_class_signs_and_weights_are_checked(self):
        for index, expected_ep in enumerate((7, -7, 3, -3, 2, -2, 0)):
            with self.subTest(index=index):
                self.reference, self.candidate = synthetic_capture("R"), synthetic_capture("Python")
                for capture in (self.reference, self.candidate):
                    for mode in ("batch", "single"):
                        for row in capture[mode]:
                            row["probabilities"] = [int(i == index) for i in range(7)]
                            row["ep"] = expected_ep
                self.compare()
                self.candidate["batch"][0]["ep"] = expected_ep + 0.5
                with self.assertRaises(ep.ProtocolError):
                    self.compare()

    def test_capture_identity_mismatches_or_missing_hashes_fail(self):
        for key, value in (("fixture_sha256", "f" * 64), ("source_commits", {}),
                           ("model_sha256", "e" * 64), ("artifact_manifest_sha256", "f" * 64),
                           ("probability_origin", "model_capture"), ("protocol_version", True)):
            self.candidate = synthetic_capture("Python")
            self.candidate[key] = value
            with self.subTest(key=key), self.assertRaises(ep.ProtocolError):
                self.compare()
        for key in ("model_sha256", "artifact_manifest_sha256"):
            for value in (None, "", "0" * 64, "x" * 64):
                self.candidate = synthetic_capture("Python")
                self.candidate[key] = value
                with self.assertRaises(ep.ProtocolError):
                    self.compare()

    def test_missing_runtime_or_unexpected_capture_keys_fail(self):
        for key in self.candidate["runtime"]:
            self.candidate = synthetic_capture("Python")
            del self.candidate["runtime"][key]
            with self.subTest(key=key), self.assertRaises(ep.ProtocolError):
                self.compare()
        self.candidate = synthetic_capture("Python")
        self.candidate["runtime"]["language"] = "R"
        with self.assertRaises(ep.ProtocolError):
            self.compare()
        self.candidate = synthetic_capture("Python")
        self.candidate["preferred_call"] = "pass"
        with self.assertRaises(ep.ProtocolError):
            self.compare()
        for key, value in (("version", ""), ("xgboost_version", None), ("platform", "  "),
                           ("environment_sha256", "0" * 64), ("runner_sha256", None)):
            self.candidate = synthetic_capture("Python")
            self.candidate["runtime"][key] = value
            with self.subTest(key=key), self.assertRaises(ep.ProtocolError):
                self.compare()

    def test_feature_class_and_row_reordering_cannot_pass(self):
        for key in ("feature_order", "class_order", "batch", "single"):
            self.candidate = synthetic_capture("Python")
            self.candidate[key] = list(reversed(self.candidate[key]))
            with self.subTest(key=key), self.assertRaises(ep.ProtocolError):
                self.compare()
        self.candidate = synthetic_capture("Python")
        self.candidate["batch"][0]["features"][0] = 900
        with self.assertRaises(ep.ProtocolError):
            self.compare()
        self.candidate = synthetic_capture("Python")
        self.candidate["single"].pop()
        with self.assertRaises(ep.ProtocolError):
            self.compare()
        self.candidate = synthetic_capture("Python")
        for mode in ("batch", "single"):
            left, right = self.candidate[mode][:2]
            left["probabilities"], right["probabilities"] = right["probabilities"], left["probabilities"]
            left["ep"], right["ep"] = right["ep"], left["ep"]
        with self.assertRaisesRegex(ep.ProtocolError, "cross-runtime"):
            self.compare()

    def test_invalid_probability_shapes_values_and_normalization_fail(self):
        for values in ([0.1] * 7, [0.2] * 7, [1] + [0] * 5, [True] + [0] * 6,
                       [float("nan")] + [0] * 6, [float("inf")] + [0] * 6,
                       [-0.1, 1.1, 0, 0, 0, 0, 0], ["1"] + [0] * 6):
            self.candidate = synthetic_capture("Python")
            self.candidate["batch"][0]["probabilities"] = values
            with self.assertRaises(ep.ProtocolError):
                self.compare()

    def test_invalid_ep_values_cannot_pass(self):
        for value in (None, True, "1.1", float("nan"), float("inf"), -8, 8, 0, 10 ** 400):
            self.candidate = synthetic_capture("Python")
            self.candidate["batch"][0]["ep"] = value
            with self.assertRaises(ep.ProtocolError):
                self.compare()

    def test_batch_single_and_cross_runtime_mismatches_fail(self):
        # Internally consistent but different distributions: preserve weighted EP.
        alternative = [0.2, 0.1, 0.16, 0.06, 0.1, 0.05, 0.33]
        self.candidate["batch"][0]["probabilities"] = alternative
        with self.assertRaisesRegex(ep.ProtocolError, "batch/single"):
            self.compare()
        self.candidate["single"][0]["probabilities"] = list(alternative)
        with self.assertRaisesRegex(ep.ProtocolError, "cross-runtime"):
            self.compare()

    def test_absolute_tolerances_do_not_normalize_or_mask_probability_drift(self):
        for mode in ("batch", "single"):
            self.candidate[mode][0]["probabilities"][0] += 0.5e-6
            self.candidate[mode][0]["probabilities"][1] -= 0.5e-6
            self.candidate[mode][0]["ep"] += 7e-6
        self.compare()
        self.candidate = synthetic_capture("Python")
        for mode in ("batch", "single"):
            self.candidate[mode][0]["probabilities"][0] += 2e-6
            self.candidate[mode][0]["probabilities"][2] -= 2e-6
            self.candidate[mode][0]["ep"] += 8e-6
        with self.assertRaisesRegex(ep.ProtocolError, "probability mismatch"):
            self.compare()

    def test_replay_reports_only_input_protocol_not_model_execution(self):
        result = subprocess.run([sys.executable, "-m", "validation.ep_reference"], cwd=ROOT,
                                text=True, capture_output=True, check=True)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["status"], "synthetic_input_protocol_pass")
        self.assertEqual(receipt["fixture_sha256"], self.fingerprint)
        self.assertEqual(receipt["model_predictions"], "not_acquired_or_executed")
        self.assertEqual((receipt["accepted_cases"], receipt["rejected_cases"]), (25, 16))
