"""Offline source-audit consistency; no upstream model execution or attestation."""

from datetime import datetime
import json
from pathlib import Path
import re
from typing import get_args, get_type_hints
import unittest

from opponent_intelligence.pbp import Play


ROOT = Path(__file__).resolve().parents[1]


class FastrmodelsAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = json.loads((ROOT / "docs/evidence/fastrmodels-2.1.0-interface-audit.json")
                               .read_text(encoding="utf-8"))

    def test_independently_recorded_commit_tree_pairs_and_doc_links(self):
        self.assertEqual(self.audit["audit_schema_version"], 1)
        pairs = {
            "nflverse/fastrmodels": ("ca185baf7757c2992e57ce2bdf2f296c515465d8",
                                    "75424601cec99d5cd4ecd636ac6a819efe91a2eb"),
            "nflverse/nflfastR": ("917b14e5085f352d9b00d23628759773e7d411b5",
                                 "71b6133789a8a6adfb0e5960991040abd32a0979"),
        }
        self.assertEqual(set(self.audit["sources"]), set(pairs))
        for repository, source in self.audit["sources"].items():
            self.assertEqual((source["commit"], source["tree"]), pairs[repository])
            self.assertEqual(source["tag"], "v" + source["version"])
            for sha in source["source_blobs"].values():
                self.assertRegex(sha, r"^[0-9a-f]{40}$")
        doc = (ROOT / "docs/FASTRMODELS_AUDIT.md").read_text(encoding="utf-8")
        links = re.findall(r"https://github.com/(nflverse/[^/]+)/blob/([^/]+)/([^\s#]+)", doc)
        self.assertTrue(links)
        for repository, commit, path in links:
            source = self.audit["sources"][repository]
            self.assertEqual(commit, source["commit"])
            self.assertIn(path, source["source_blobs"])
        self.assertEqual(
            {(repository, path) for repository, _, path in links},
            {(repository, path) for repository, source in self.audit["sources"].items()
             for path in source["source_blobs"]},
        )

    def test_raw_wrapper_inventory_is_not_model_feature_inventory(self):
        # Transcribed from the pinned standalone calculators, not generated from
        # the receipt. In particular, WP wrapper requires a spread for BOTH outputs.
        ep = {"season", "home_team", "posteam", "roof", "half_seconds_remaining",
              "yardline_100", "down", "ydstogo", "posteam_timeouts_remaining",
              "defteam_timeouts_remaining"}
        wp = {"receive_2h_ko", "score_differential", "home_team", "posteam",
              "half_seconds_remaining", "game_seconds_remaining", "spread_line",
              "down", "ydstogo", "yardline_100", "posteam_timeouts_remaining",
              "defteam_timeouts_remaining"}
        for name, expected in (("ep", ep), ("wp", wp)):
            self.assertEqual(set(self.audit["wrapper_inputs"][name]), expected)
            self.assertEqual(len(self.audit["wrapper_inputs"][name]), len(expected))
        self.assertEqual(set(self.audit["play_mapping"]), ep | wp)
        self.assertNotIn("epa", ep | wp)
        self.assertNotIn("dropback", ep | wp)

    def test_direct_mapping_and_nullability_agree_with_current_play(self):
        hints = get_type_hints(Play)
        direct = {"season": "season", "posteam": "offense", "down": "down",
                  "ydstogo": "yards_to_go", "yardline_100": "yardline_100",
                  "score_differential": "score_differential"}
        for upstream, field in direct.items():
            item = self.audit["play_mapping"][upstream]
            with self.subTest(upstream=upstream):
                self.assertEqual(item["fields"], [field])
                nullable = type(None) in get_args(hints[field])
                self.assertEqual(item["state"], "nullable" if nullable else "present")

    def test_missing_inputs_and_clock_derivation_are_not_fabricated(self):
        hints = get_type_hints(Play)
        missing = {"home_team", "roof", "posteam_timeouts_remaining",
                   "defteam_timeouts_remaining", "receive_2h_ko", "spread_line"}
        actual = {name for name, item in self.audit["play_mapping"].items()
                  if item["state"] == "missing"}
        self.assertEqual(actual, missing)
        for name in missing:
            self.assertNotIn(name, hints)
            self.assertEqual(self.audit["play_mapping"][name]["fields"], [])
        for clock in ("half_seconds_remaining", "game_seconds_remaining"):
            item = self.audit["play_mapping"][clock]
            self.assertNotIn(clock, hints)
            self.assertEqual(item["state"], "derivation_requires_validation")
            self.assertEqual(item["fields"], ["qtr", "quarter_seconds_remaining"])
            for field in item["fields"]:
                self.assertIn(type(None), get_args(hints[field]))

    def test_ordered_model_features_preserve_encoding_and_spread_position(self):
        ep = ["half_seconds_remaining", "yardline_100", "home", "retractable",
              "dome", "outdoors", "ydstogo", "era0", "era1", "era2", "era3",
              "era4", "down1", "down2", "down3", "down4",
              "posteam_timeouts_remaining", "defteam_timeouts_remaining"]
        wp = ["receive_2h_ko", "home", "half_seconds_remaining", "game_seconds_remaining",
              "Diff_Time_Ratio", "score_differential", "down", "ydstogo", "yardline_100",
              "posteam_timeouts_remaining", "defteam_timeouts_remaining"]
        self.assertEqual(self.audit["feature_order"], {
            "ep": ep, "wp": wp, "wp_spread": [wp[0], "spread_time", *wp[1:]],
        })
        for features in self.audit["feature_order"].values():
            self.assertEqual(len(features), len(set(features)))

    def test_ep_classes_units_and_signs_remain_distinct_from_wp(self):
        outputs = self.audit["outputs"]
        self.assertEqual(outputs["ep"]["class_order"], ["td_prob", "opp_td_prob",
                         "fg_prob", "opp_fg_prob", "safety_prob", "opp_safety_prob",
                         "no_score_prob"])
        self.assertEqual(outputs["ep"]["points_weights"], [7, -7, 3, -3, 2, -2, 0])
        self.assertEqual(outputs["ep"]["unit"], "expected_points")
        self.assertEqual(outputs["wp"]["columns"], ["wp", "vegas_wp"])
        self.assertEqual(outputs["wp"]["unit"], "probability")

    def test_artifact_metadata_does_not_manufacture_missing_digests_or_lineage(self):
        artifacts = self.audit["artifacts"]
        self.assertEqual(len(artifacts), 3)
        self.assertEqual({item["name"] for item in artifacts},
                         {"ep_model", "wp_model", "wp_model_spread"})
        self.assertEqual(len({item["archive"]["asset_id"] for item in artifacts}), 3)
        for item in artifacts:
            with self.subTest(model=item["name"]):
                self.assertEqual(item["package_path"], f"data/{item['name']}.rda")
                self.assertRegex(item["git_blob_sha1"], r"^[0-9a-f]{40}$")
                self.assertGreater(item["package_bytes"], 0)
                self.assertEqual(item["archive"]["name"], item["name"] + ".ubj")
                self.assertGreater(item["archive"]["bytes"], 0)
                self.assertIsNone(item["archive"]["api_advertised_digest"])
                self.assertIsNone(item["local_sha256"])
                self.assertIsNone(item["verified_training_window"])
                created = datetime.fromisoformat(item["archive"]["created_at"])
                updated = datetime.fromisoformat(item["archive"]["updated_at"])
                self.assertIsNotNone(created.tzinfo)
                self.assertLessEqual(created, updated)
                self.assertLessEqual(updated.date().isoformat(), self.audit["observed_on"])

    def test_static_audit_retains_separate_admission_gates(self):
        assessment = self.audit["assessment"]
        self.assertEqual(assessment["decision"], "defer_runtime_integration")
        for field in ("artifact_bytes_acquired", "parity_validated", "calibration_validated",
                      "historical_availability_established"):
            self.assertIs(assessment[field], False)
        self.assertEqual(set(assessment["remaining_gates"]), {
            "artifact_terms_and_local_hashes", "exact_R_Python_runtimes_and_serialization",
            "training_lineage_and_release_time_evidence",
            "validated_game_state_inputs_and_transforms",
            "independent_reference_parity_and_boundary_vectors",
            "temporal_holdouts_baselines_and_calibration",
            "action_transition_model_before_action_values",
        })
        self.assertEqual(set(assessment["deferred_catalog"]),
                         {"cp_model", "fg_model", "xpass_model", "xyac_model"})
