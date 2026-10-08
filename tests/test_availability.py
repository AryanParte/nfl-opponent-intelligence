"""Synthetic, offline availability counts: absent is not missing or false."""

from contextlib import redirect_stderr, redirect_stdout
import csv
import gzip
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from opponent_intelligence import availability, snapshots
from opponent_intelligence.pbp import REQUIRED_COLUMNS


FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_pbp.csv"


class AvailabilityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        with FIXTURE.open(newline="") as source:
            self.base = next(csv.DictReader(source))
        # Four invented plays: eligible run and pass, a punt, and a kneel.
        # Missingness on excluded rows must not contaminate eligible counts.
        self.rows = [
            dict(self.base, play_id="1", play_type="run", qb_dropback="0", shotgun="0", no_huddle="1",
                 offense_personnel="1 RB, 1 TE, 3 WR", is_motion="FALSE", desc="motion word"),
            dict(self.base, play_id="2.0", play_type="pass", shotgun="1.00", no_huddle="0",
                 offense_personnel=" NA ", is_motion="TRUE", desc="ordinary text"),
            dict(self.base, play_id="3", play_type="punt", shotgun="", no_huddle="NULL",
                 offense_personnel="2 RB, 2 TE, 1 WR", is_motion="NaN", desc=""),
            dict(self.base, play_id="4", qb_kneel="1", shotgun="1", no_huddle="0",
                 offense_personnel="", is_motion="NA", desc=""),
        ]
        network = patch.object(snapshots, "urlopen", side_effect=AssertionError("network forbidden"))
        network.start()
        self.addCleanup(network.stop)

    def snapshot(self, rows=None, *, fields=None, raw=None):
        rows = self.rows if rows is None else rows
        if raw is None:
            buffer = io.StringIO(newline="")
            fields = list(self.rows[0]) if fields is None else fields
            writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
            raw = buffer.getvalue().encode()
        archive = gzip.compress(raw, mtime=0)
        digest = sha256(archive).hexdigest()
        directory = self.root / digest
        directory.mkdir(exist_ok=True)
        manifest = {
            "schema_version": 1, "season": 2024,
            "retrieved_at_utc": "2026-10-08T00:00:00Z",
            "source": {
                "release_api_url": snapshots.RELEASE_API, "release_tag": "pbp",
                "release_id": 100, "asset_id": 200, "asset_name": snapshots.ASSET_NAME,
                "download_url": snapshots.ASSET_URL, "size_bytes": len(archive),
                "sha256": digest, "asset_updated_at_utc": "2025-02-10T00:00:00Z",
            },
            "archive": {"sha256": digest, "size_bytes": len(archive)},
            "decoded_csv": {"sha256": sha256(raw).hexdigest(), "size_bytes": len(raw)},
            "license": snapshots._license_notice(),
        }
        (directory / snapshots.ASSET_NAME).write_bytes(archive)
        (directory / "manifest.json").write_text(json.dumps(manifest))
        return directory, raw

    def test_raw_and_eligible_denominators_and_binary_counts(self):
        directory, _ = self.snapshot()
        result = availability.audit_availability(directory)
        self.assertEqual(result["scope"]["raw_rows"], 4)
        self.assertEqual(result["scope"]["eligible_rows"], 2)
        self.assertEqual(result["scope"]["excluded_rows_by_reason"], {"kneel": 1, "non_run_pass": 1})
        shotgun = result["fields"]["shotgun"]
        self.assertEqual(shotgun["raw"], {
            "status": "observed", "rows": 4, "non_missing": 3, "missing": 1,
            "binary_counts": {"zero": 1, "one": 2, "other": 0},
        })
        self.assertEqual(shotgun["eligible"], {
            "status": "observed", "rows": 2, "non_missing": 2, "missing": 0,
            "binary_counts": {"zero": 1, "one": 1, "other": 0},
        })
        self.assertEqual(result["fields"]["no_huddle"]["eligible"]["binary_counts"]["one"], 1)

    def test_absent_columns_have_null_counts_not_false_observations(self):
        directory, _ = self.snapshot(fields=list(REQUIRED_COLUMNS))
        result = availability.audit_availability(directory)
        self.assertEqual(set(result["fields"]), set(availability.CANDIDATE_FIELDS))
        for field in result["fields"].values():
            self.assertEqual(field, {"column_present": False, "raw": None, "eligible": None})

    def test_all_missing_is_distinct_from_absent_and_no_rows(self):
        rows = [dict(row, offense_personnel=marker) for row, marker in zip(self.rows, ("", "NA", "nan", " Null "))]
        directory, _ = self.snapshot(rows)
        field = availability.audit_availability(directory)["fields"]["offense_personnel"]
        self.assertTrue(field["column_present"])
        self.assertEqual(field["raw"], {"status": "all_missing", "rows": 4, "non_missing": 0, "missing": 4})
        self.assertEqual(field["eligible"]["missing"], 2)
        directory, _ = self.snapshot([])
        field = availability.audit_availability(directory)["fields"]["offense_personnel"]
        self.assertTrue(field["column_present"])
        self.assertEqual(field["raw"], {"status": "no_rows", "rows": 0, "non_missing": 0, "missing": 0})

    def test_observed_only_on_excluded_plays_is_not_eligible_coverage(self):
        rows = [dict(row, offense_personnel="" if i < 2 else "2 RB, 1 TE, 2 WR")
                for i, row in enumerate(self.rows)]
        directory, _ = self.snapshot(rows)
        field = availability.audit_availability(directory)["fields"]["offense_personnel"]
        self.assertEqual(field["raw"]["non_missing"], 2)
        self.assertEqual(field["eligible"]["status"], "all_missing")
        directory, _ = self.snapshot(rows[2:])
        field = availability.audit_availability(directory)["fields"]["offense_personnel"]
        self.assertEqual(field["raw"]["status"], "observed")
        self.assertEqual(field["eligible"]["status"], "no_rows")

    def test_unknown_binary_values_are_counted_not_silently_coerced(self):
        for value in ("2", "-1", "false", "0.1", "inf", "bogus"):
            with self.subTest(value=value):
                directory, _ = self.snapshot([dict(self.rows[0], shotgun=value)])
                group = availability.audit_availability(directory)["fields"]["shotgun"]["eligible"]
                self.assertEqual(group["non_missing"], 1)
                self.assertEqual(group["binary_counts"], {"zero": 0, "one": 0, "other": 1})

    def test_exact_names_only_and_text_is_not_interpreted(self):
        rows = [dict(row, motion="TRUE") for row in self.rows]
        fields = [name for name in self.rows[0] if name != "is_motion"] + ["motion"]
        directory, _ = self.snapshot(rows, fields=fields)
        result = availability.audit_availability(directory)
        self.assertFalse(result["fields"]["is_motion"]["column_present"])
        self.assertEqual(result["fields"]["desc"]["eligible"]["non_missing"], 2)
        self.assertNotIn("motion word", json.dumps(result))
        self.assertNotIn("motion_rate", json.dumps(result))

    def test_non_missing_charting_values_are_not_semantic_validation(self):
        directory, _ = self.snapshot([dict(self.rows[0], offense_personnel="not a personnel code", is_motion="nonsense")])
        result = availability.audit_availability(directory)
        for name in ("offense_personnel", "is_motion"):
            self.assertEqual(result["fields"][name]["eligible"]["non_missing"], 1)
            self.assertNotIn("binary_counts", result["fields"][name]["eligible"])

    def test_bom_hash_and_manifest_are_preserved_without_mutation(self):
        _, raw = self.snapshot()
        directory, raw = self.snapshot(raw=b"\xef\xbb\xbf" + raw)
        before = (directory / "manifest.json").read_bytes()
        first = availability.audit_availability(directory)
        self.assertEqual(first, availability.audit_availability(directory))
        self.assertEqual(first["source"]["sha256"], sha256(raw).hexdigest())
        self.assertEqual(first["source"]["snapshot"], json.loads(before))
        self.assertEqual(before, (directory / "manifest.json").read_bytes())

    def test_all_weeks_and_both_season_types_are_audited(self):
        rows = [dict(self.rows[0], week="1"), dict(self.rows[1], game_id="POST", week="22", season_type="POST")]
        directory, _ = self.snapshot(rows)
        result = availability.audit_availability(directory)
        self.assertEqual(result["scope"]["eligible_season_types"], ["REG", "POST"])
        self.assertIsNone(result["scope"]["week_cutoff"])
        self.assertEqual(result["scope"]["eligible_rows"], 2)

    def test_invalid_source_fails_before_any_cli_output(self):
        invalid_rows = [
            self.rows + [self.rows[0]],
            [dict(self.rows[0], season="2025")],
            [dict(self.rows[0], play_type="passs")],
        ]
        for rows in invalid_rows:
            directory, _ = self.snapshot(rows)
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                result = availability.main(["--snapshot", str(directory)])
            self.assertEqual(result, 2)
            self.assertEqual(out.getvalue(), "")
            self.assertTrue(err.getvalue().startswith("error: "))

    def test_ragged_or_duplicate_headers_are_not_silently_counted(self):
        _, raw = self.snapshot()
        header, body = raw.split(b"\r\n", 1)
        cases = (header + b",shotgun\n" + body, header + b"\n" + body + b"short,row\n")
        for malformed in cases:
            with self.subTest(raw=malformed[:40]):
                directory, _ = self.snapshot(raw=malformed)
                with self.assertRaises(ValueError):
                    availability.audit_availability(directory)

    def test_counts_are_row_order_invariant_and_do_not_depend_on_source_path(self):
        first, _ = self.snapshot()
        second, _ = self.snapshot(list(reversed(self.rows)))
        a, b = availability.audit_availability(first), availability.audit_availability(second)
        self.assertNotEqual(a.pop("source")["sha256"], b.pop("source")["sha256"])
        self.assertEqual(a, b)

    def test_corrupted_snapshot_and_bad_encoding_fail_closed(self):
        directory, _ = self.snapshot()
        (directory / snapshots.ASSET_NAME).write_bytes(b"corruption")
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            availability.audit_availability(directory)
        directory, _ = self.snapshot(raw=b"\xffinvalid UTF-8")
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(availability.main(["--snapshot", str(directory)]), 2)
        self.assertEqual(out.getvalue(), "")
        self.assertTrue(err.getvalue().startswith("error: "))

    def test_cli_subprocess_is_offline_and_matches_api(self):
        directory, _ = self.snapshot()
        code = (
            "import runpy\nfrom unittest.mock import patch\n"
            "with patch('socket.socket.connect', side_effect=AssertionError('network forbidden')), "
            "patch('socket.create_connection', side_effect=AssertionError('network forbidden')):\n"
            "    runpy.run_module('opponent_intelligence.availability', run_name='__main__')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code, "--snapshot", str(directory)],
            text=True, capture_output=True, check=False,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout), availability.audit_availability(directory))


if __name__ == "__main__":
    unittest.main()
