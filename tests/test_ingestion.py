"""Synthetic, network-free tests of snapshot-to-analysis provenance and auditing."""

from contextlib import redirect_stderr, redirect_stdout
import csv
from dataclasses import replace
import gzip
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from opponent_intelligence import audit, ingestion, snapshots
from opponent_intelligence.__main__ import main
from opponent_intelligence.pbp import DataValidationError, REQUIRED_COLUMNS, load_csv
from opponent_intelligence.report import build_report


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_pbp.csv"


class IngestionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        with FIXTURE.open(newline="") as source:
            # A snapshot is season-specific; the manual-CSV fixture intentionally
            # includes another season to test filtering. Leave that fixture intact.
            self.rows = [row for row in csv.DictReader(source) if row["season"] == "2024"]
        network = patch.object(snapshots, "urlopen", side_effect=AssertionError("network forbidden"))
        network.start()
        self.addCleanup(network.stop)

    def snapshot(self, *, rows=None, raw=None):
        if raw is None:
            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=REQUIRED_COLUMNS)
            writer.writeheader()
            writer.writerows(self.rows if rows is None else rows)
            raw = buffer.getvalue().encode()
        archive = gzip.compress(raw, mtime=0)
        release = {"id": 100, "tag_name": "pbp", "assets": [{
            "id": 200, "name": snapshots.ASSET_NAME, "size": len(archive),
            "state": "uploaded", "updated_at": "2025-02-10T00:00:00Z",
            "browser_download_url": snapshots.ASSET_URL,
            "digest": "sha256:" + sha256(archive).hexdigest(),
        }]}
        responses = []
        for payload in (json.dumps(release).encode(), archive):
            response = io.BytesIO(payload)
            response.status = 200
            response.headers = {"Content-Length": str(len(payload))}
            responses.append(response)
        with patch.object(snapshots, "urlopen", side_effect=responses):
            directory = snapshots.fetch_snapshot(self.root, refresh=True)
        return directory, raw

    def report(self, dataset, **changes):
        options = dict(team="CAR", season=2024, before_week=3, source_label="Synthetic snapshot")
        options.update(changes)
        return build_report(dataset, **options)

    def test_snapshot_and_plain_csv_have_identical_measurements(self):
        directory, raw = self.snapshot()
        plain_path = self.root / "same.csv"
        plain_path.write_bytes(raw)
        before = (directory / "manifest.json").read_bytes()
        dataset = ingestion.load_snapshot(directory)
        self.assertEqual(dataset.source_sha256, sha256(raw).hexdigest())
        self.assertNotEqual(dataset.source_sha256, directory.name)
        report = self.report(dataset)
        manifest = report["source"].pop("snapshot")
        self.assertEqual(report, self.report(load_csv(plain_path)))
        self.assertEqual(report["overall"]["plays"], 6)
        self.assertEqual(report["overall"]["dropbacks"], 3)
        self.assertEqual(report["overall"]["epa_observations"], 5)
        self.assertAlmostEqual(report["overall"]["epa_per_play"], 0.04)
        self.assertEqual(manifest, json.loads(before))
        self.assertEqual((directory / "manifest.json").read_bytes(), before)

    def test_report_preserves_source_identity_without_sharing_mutable_manifest(self):
        directory, _ = self.snapshot()
        dataset = ingestion.load_snapshot(directory)
        first = self.report(dataset)
        first["source"]["snapshot"]["source"]["asset_id"] = -1
        second = self.report(dataset)
        self.assertEqual(second["source"]["snapshot"]["source"]["asset_id"], 200)
        self.assertEqual(second["source"]["snapshot"]["license"]["identifier"], "CC-BY-4.0")

    def test_explicit_snapshot_does_not_follow_current_pointer(self):
        first, _ = self.snapshot()
        second, _ = self.snapshot(rows=[dict(self.rows[0], epa="99")])
        self.assertNotEqual(first, second)
        self.assertEqual(self.report(ingestion.load_snapshot(first))["overall"]["plays"], 6)
        self.assertEqual(self.report(ingestion.load_snapshot(second))["overall"]["plays"], 1)

    def test_bom_is_preserved_in_decoded_hash(self):
        _, raw = self.snapshot()
        directory, raw = self.snapshot(raw=b"\xef\xbb\xbf" + raw)
        dataset = ingestion.load_snapshot(directory)
        self.assertEqual(dataset.source_sha256, sha256(raw).hexdigest())
        self.assertEqual(len(dataset.plays), 9)

    def test_foreign_season_is_rejected_even_on_excluded_rows(self):
        for kind in ("pass", "no_play", ""):
            with self.subTest(kind=kind):
                directory, _ = self.snapshot(rows=[dict(self.rows[0], season="2025", play_type=kind)])
                with self.assertRaisesRegex(DataValidationError, "CSV line 2: row season"):
                    ingestion.load_snapshot(directory)
        directory, _ = self.snapshot()
        with self.assertRaisesRegex(ValueError, "requested season"):
            self.report(ingestion.load_snapshot(directory), season=2025)
        directory, _ = self.snapshot(rows=[dict(self.rows[0], game_id="", season="2025")])
        with self.assertRaisesRegex(DataValidationError, "game_id must be present"):
            ingestion.load_snapshot(directory)

    def test_verified_bytes_still_require_analytical_validation(self):
        cases = (
            [dict(self.rows[0], play_type="passs")],
            [dict(self.rows[0], down="")],
            [self.rows[0], dict(self.rows[0], play_id="1.0")],
        )
        for rows in cases:
            with self.subTest(rows=rows):
                directory, _ = self.snapshot(rows=rows)
                with self.assertRaises(DataValidationError):
                    ingestion.load_snapshot(directory)
        directory, _ = self.snapshot(raw=b"\xffinvalid utf8")
        with self.assertRaises(UnicodeError):
            ingestion.load_snapshot(directory)

    def test_cache_corruption_never_produces_a_report(self):
        directory, _ = self.snapshot()
        (directory / snapshots.ASSET_NAME).write_bytes(b"corrupt")
        with self.assertRaises(snapshots.SnapshotError):
            ingestion.load_snapshot(directory)

    def test_actual_decoded_bytes_are_rechecked_after_verification(self):
        directory, raw = self.snapshot()
        original_verify = snapshots.verify_snapshot

        def mutate_after_verification(path):
            manifest = original_verify(path)
            (path / snapshots.ASSET_NAME).write_bytes(gzip.compress(raw.replace(b"0.8", b"9.8")))
            return manifest
        with patch.object(ingestion, "verify_snapshot", side_effect=mutate_after_verification):
            with self.assertRaisesRegex(snapshots.SnapshotError, "decoded CSV differs"):
                ingestion.load_snapshot(directory)

    def test_second_read_is_bounded_and_handles_gzip_failures(self):
        directory, _ = self.snapshot()
        with patch.object(ingestion, "MAX_DECODED_BYTES", 10):
            with self.assertRaisesRegex(snapshots.SnapshotError, "decoded CSV differs"):
                ingestion.load_snapshot(directory)
        manifest = snapshots.verify_snapshot(directory)
        for body in (b"invalid", gzip.compress(b"valid")[:-4]):
            with self.subTest(body=body):
                (directory / snapshots.ASSET_NAME).write_bytes(body)
                with patch.object(ingestion, "verify_snapshot", return_value=manifest):
                    with self.assertRaisesRegex(snapshots.SnapshotError, "invalid or truncated"):
                        ingestion.load_snapshot(directory)

    def test_audit_reconciles_independent_counts_coverage_and_missingness(self):
        # Add one administrative missing type and a type-labeled kneel. Their
        # absent flags are valid because exclusion by type precedes those flags.
        excluded = dict(self.rows[7], play_id="999", play_type="NA")
        kneel = dict(excluded, play_id="1000", play_type="qb_kneel")
        directory, _ = self.snapshot(rows=self.rows + [excluded, kneel])
        result = audit.audit_snapshot(directory)
        self.assertEqual(result["input"]["rows"], 15)
        self.assertEqual(result["input"]["column_count"], 15)
        self.assertEqual(result["input"]["play_type_counts"]["<missing>"], 1)
        self.assertEqual(result["input"]["required_column_missing_counts"]["epa"], 4)
        self.assertEqual(result["input"]["required_column_missing_counts"]["down"], 4)
        self.assertEqual(result["adapter"]["eligible_rows"], 9)
        self.assertEqual(result["adapter"]["excluded_rows_by_reason"], {
            "kneel": 1, "spike": 1, "two_point_attempt": 1, "non_run_pass": 2, "missing_play_type": 1,
        })
        self.assertEqual(result["adapter"]["by_season_type"], [
            {"season_type": "REG", "input_games": 3, "eligible_games": 3,
             "eligible_rows": 8, "dropbacks": 5, "epa_observations": 7, "offenses": ["ATL", "CAR"]},
            {"season_type": "POST", "input_games": 1, "eligible_games": 1,
             "eligible_rows": 1, "dropbacks": 1, "epa_observations": 1, "offenses": ["CAR"]},
        ])
        self.assertEqual(result["input"]["coverage"], [
            {"season_type": "REG", "week": 1, "rows": 12, "games": 1},
            {"season_type": "REG", "week": 2, "rows": 1, "games": 1},
            {"season_type": "REG", "week": 3, "rows": 1, "games": 1},
            {"season_type": "POST", "week": 19, "rows": 1, "games": 1},
        ])
        self.assertEqual(result["reconciliation"], {
            "accounted_rows": 15, "duplicate_play_keys": 0,
            "raw_and_adapter_eligible_identities_match": True,
        })

    def test_audit_checks_metadata_on_excluded_rows_and_game_consistency(self):
        for changes in ({"week": "0"}, {"season_type": "PRE"}, {"week": "2"}):
            with self.subTest(changes=changes):
                excluded = dict(self.rows[7], **changes)
                directory, _ = self.snapshot(rows=[self.rows[0], excluded])
                with self.assertRaisesRegex(DataValidationError, "CSV line 3:"):
                    audit.audit_snapshot(directory)

    def test_audit_detects_eligibility_and_row_accounting_disagreement(self):
        directory, _ = self.snapshot()
        dataset = ingestion.load_snapshot(directory)
        for altered in (replace(dataset, plays=dataset.plays[1:]),
                        replace(dataset, plays=(replace(dataset.plays[0], play_id=9999),) + dataset.plays[1:]),
                        replace(dataset, input_rows=999)):
            with self.subTest(altered=altered.input_rows):
                with patch.object(audit, "_snapshot_dataset", return_value=altered):
                    with self.assertRaises(DataValidationError):
                        audit.audit_snapshot(directory)

    def test_empty_and_all_excluded_snapshots_remain_auditable(self):
        for rows in ([], [self.rows[7]]):
            with self.subTest(rows=rows):
                directory, _ = self.snapshot(rows=rows)
                result = audit.audit_snapshot(directory)
                self.assertEqual(result["adapter"]["eligible_rows"], 0)
                self.assertEqual(result["reconciliation"]["accounted_rows"], len(rows))
                self.assertIsNone(self.report(ingestion.load_snapshot(directory))["overall"]["epa_per_play"])

    def test_report_and_audit_clis_are_offline_deterministic_and_all_or_nothing(self):
        directory, _ = self.snapshot()
        args = ["--snapshot", str(directory), "--team", "CAR", "--season", "2024",
                "--before-week", "3", "--source-label", "Synthetic snapshot"]
        for entry, options in ((main, args), (audit.main, ["--snapshot", str(directory)])):
            outputs = []
            for _ in range(2):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    self.assertEqual(entry(options), 0)
                outputs.append(stdout.getvalue())
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(json.loads(outputs[0])["source"]["snapshot"]["source"]["asset_id"], 200)
        (directory / snapshots.ASSET_NAME).write_bytes(b"corrupt")
        for entry, options in ((main, args), (audit.main, ["--snapshot", str(directory)])):
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                self.assertEqual(entry(options), 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("error:", stderr.getvalue())

    def test_cli_requires_exactly_one_input(self):
        common = ["--team", "CAR", "--season", "2024", "--before-week", "3", "--source-label", "Synthetic"]
        for options in (common, common + ["--csv", str(FIXTURE), "--snapshot", str(self.root)]):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main(options)
            self.assertEqual(error.exception.code, 2)

    def test_snapshot_cli_reports_semantic_failures_without_partial_json(self):
        for rows in ([dict(self.rows[0], play_type="passs")],
                     [dict(self.rows[0], season="2025")]):
            directory, _ = self.snapshot(rows=rows)
            for entry, options in (
                (main, ["--snapshot", str(directory), "--team", "CAR", "--season", "2024",
                        "--before-week", "3", "--source-label", "Synthetic"]),
                (audit.main, ["--snapshot", str(directory)]),
            ):
                stdout, stderr = io.StringIO(), io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    self.assertEqual(entry(options), 2)
                self.assertEqual(stdout.getvalue(), "")
                self.assertIn("CSV line 2:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
