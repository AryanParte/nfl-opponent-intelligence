"""Offline audit-record drift checks, not upstream model/output validation."""

from dataclasses import fields
from datetime import datetime
import json
from pathlib import Path
import re
from typing import get_args, get_type_hints
import unittest

from opponent_intelligence.decision import DecisionRequest
from opponent_intelligence.pbp import Play


ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "docs/evidence/nfl4th-1.0.7-interface-audit.json"


class Nfl4thAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_local_contract_drift_requires_explicit_reaudit(self):
        for contract in (Play, DecisionRequest):
            with self.subTest(contract=contract.__name__):
                self.assertEqual(self.audit["local_contract"][contract.__name__],
                                 [field.name for field in fields(contract)])

    def test_manual_interface_inventory_and_mapping(self):
        # Independently transcribed from the pinned upstream manual example.
        expected = {
            "home_team": None, "away_team": None, "posteam": "offense",
            "type": "season_type", "season": "season", "qtr": "qtr",
            "quarter_seconds_remaining": "quarter_seconds_remaining",
            "ydstogo": "yards_to_go", "yardline_100": "yardline_100",
            "score_differential": "score_differential", "home_opening_kickoff": None,
            "posteam_timeouts_remaining": None, "defteam_timeouts_remaining": None,
        }
        inputs = self.audit["manual_inputs"]
        self.assertEqual(len(inputs), len(expected))  # Also catches duplicate entries.
        self.assertEqual({item["upstream"]: item["play_field"] for item in inputs}, expected)

    def test_missing_and_nullable_classification_matches_typed_play(self):
        hints = get_type_hints(Play)
        for item in self.audit["manual_inputs"]:
            with self.subTest(input=item["upstream"]):
                field = item["play_field"]
                if field is None:
                    self.assertNotIn(item["upstream"], hints)
                    self.assertEqual(item["availability"], "missing_from_typed_play")
                else:
                    self.assertIn(field, hints)
                    nullable = type(None) in get_args(hints[field])
                    self.assertEqual(item["availability"], "nullable" if nullable else "present")
                    self.assertTrue(item["constraint"].strip())

    def test_source_identities_and_document_links_are_commit_pinned(self):
        self.assertEqual(self.audit["audit_schema_version"], 1)
        upstream = self.audit["upstream"]
        self.assertEqual(upstream["repository"], "nflverse/nfl4th")
        self.assertEqual(upstream["tag"], "v" + upstream["version"])
        # Git commit and its root tree are different objects. Independently
        # checked through the pinned Git commit endpoint, not the tag label.
        self.assertEqual((upstream["resolved_commit"], upstream["tree_sha1"]), (
            "00bc3573f7e740244dc5dcbc7588f31dbd56254d",
            "82a285d0b8f0d25e95b6544ab73259f1e06d88ae",
        ))
        for value in (upstream["resolved_commit"], upstream["tree_sha1"],
                      upstream["release_target_commitish"]):
            self.assertRegex(value, r"^[0-9a-f]{40}$")
        blobs = self.audit["source_blobs"]
        paths = {item["path"] for item in blobs}
        self.assertEqual(len(paths), len(blobs))
        for item in blobs:
            self.assertRegex(item["git_blob_sha1"], r"^[0-9a-f]{40}$")
        doc = (ROOT / "docs/NFL4TH_AUDIT.md").read_text(encoding="utf-8")
        links = re.findall(r"https://github.com/nflverse/nfl4th/blob/([^\s/]+)/([^\s)]+)", doc)
        self.assertTrue(links)
        for commit, path in links:
            with self.subTest(path=path):
                self.assertEqual(commit, upstream["resolved_commit"])
                self.assertIn(path, paths)

    def test_output_units_do_not_conflate_wp_epa_or_success(self):
        expected = {name: "probability" for name in (
            "first_down_prob", "wp_fail", "wp_succeed", "go_wp", "fg_make_prob",
            "miss_fg_wp", "make_fg_wp", "fg_wp", "punt_wp",
        )}
        expected["go_boost"] = "percentage_points"
        self.assertEqual(self.audit["output_units"], expected)

    def test_advertised_asset_hashes_are_not_local_verification(self):
        assets = self.audit["model_artifact_observations"]
        self.assertEqual({(asset["tag"], asset["name"]) for asset in assets}, {
            ("model_archive", "fd_model.rds"), ("model_archive", "wp_model.rds"),
            ("model_archive", "two_pt_model.ubj"),
            ("nfl4th_infrastructure", "pre_computed_go_boost.rds"),
            ("nfl4th_infrastructure", "pre_computed_go_boost_2024.rds"),
        })
        self.assertEqual(len(assets), 5)
        self.assertEqual(len({asset["asset_id"] for asset in assets}), len(assets))
        for asset in assets:
            with self.subTest(asset=asset["name"]):
                self.assertGreater(asset["asset_id"], 0)
                self.assertGreater(asset["bytes"], 0)
                self.assertRegex(asset["api_advertised_digest"], r"^sha256:[0-9a-f]{64}$")
                self.assertIsNone(asset["local_sha256"])
                created = datetime.fromisoformat(asset["created_at"])
                updated = datetime.fromisoformat(asset["updated_at"])
                self.assertIsNotNone(created.tzinfo)
                self.assertLessEqual(created, updated)
                self.assertLessEqual(updated.date().isoformat(), self.audit["observed_on"])

    def test_static_audit_cannot_be_mistaken_for_model_admission(self):
        assessment = self.audit["assessment"]
        self.assertEqual(assessment["decision"], "defer_runtime_integration")
        for flag in ("model_bytes_downloaded", "model_outputs_validated",
                     "historical_availability_established"):
            self.assertIs(assessment[flag], False)
        self.assertEqual(set(assessment["gates"]), {
            "asset_specific_terms_and_notices",
            "local_byte_hashes_and_exact_runtime_dependencies",
            "training_lineage_and_decision_time_feature_availability",
            "validated_state_inputs_and_schedule_join_cardinality",
            "independent_golden_vectors_and_R_Python_parity",
            "time_possession_overtime_and_rules_era_boundaries",
            "temporal_validation_baselines_and_calibration",
        })
