"""FTN tests use only invented CSV/HTTP bodies; no real dataset or network in CI."""

from contextlib import redirect_stderr, redirect_stdout
import csv
from hashlib import sha1, sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from opponent_intelligence import snapshots as transport
from validation import ftn_contract as contract, ftn_snapshot as ftn


ROOT = Path(__file__).resolve().parents[1]


def csv_bytes(rows, fields=contract.FIELDS):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def row(**updates):
    value = dict.fromkeys(contract.FIELDS, "NA")
    value.update(ftn_game_id="1", ftn_play_id="10", nflverse_game_id="2024_01_CAR_ATL",
                 nflverse_play_id="100", season="2024", week="1", qb_location="S",
                 starting_hash="L", read_thrown="0", is_motion="FALSE",
                 date_pulled="2025-09-01T00:00:00Z")
    return value | updates


class Response(io.BytesIO):
    status = 200

    def __init__(self, raw):
        super().__init__(raw)
        self.headers = {"Content-Length": str(len(raw))}


class FTNSnapshotTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.cache = Path(temporary.name).resolve() / "cache"
        self.raw = csv_bytes([row(), row(ftn_play_id="11", nflverse_play_id="101")])
        self.docs = {name: f"Invented notice/definition: {name}\n".encode() for name in ftn.SOURCE_FILES}
        specs = {name: (ftn.SOURCE_FILES[name][0],
                       sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest(), len(raw))
                 for name, raw in self.docs.items()}
        for p in (patch.object(ftn, "ASSET_SHA256", sha256(self.raw).hexdigest()),
                  patch.object(ftn, "ASSET_BYTES", len(self.raw)),
                  patch.dict(ftn.SOURCE_FILES, specs, clear=True),
                  patch.object(transport, "urlopen", side_effect=AssertionError("network forbidden"))):
            p.start()
            self.addCleanup(p.stop)

    def release(self):
        identity = ftn.release_identity()
        return {"id": identity["release_id"], "tag_name": identity["release_tag"],
                "published_at": identity["release_published_at_utc"], "assets": [{
                    "id": identity["asset_id"], "name": ftn.ASSET_NAME, "state": "uploaded",
                    "browser_download_url": ftn.ASSET_URL, "size": len(self.raw),
                    "digest": f"sha256:{ftn.ASSET_SHA256}",
                    "created_at": identity["asset_created_at_utc"],
                    "updated_at": identity["asset_updated_at_utc"],
                }]}

    def responder(self, release=None):
        bodies = {ftn.RELEASE_API: json.dumps(release or self.release()).encode(),
                  ftn.ASSET_URL: self.raw}
        bodies.update({f"{ftn.SOURCE_ROOT}/{ftn.SOURCE_FILES[name][0]}": raw
                       for name, raw in self.docs.items()})

        def respond(request, *, timeout):
            self.assertEqual(timeout, 30)
            expected = ("application/vnd.github+json" if request.full_url == ftn.RELEASE_API
                        else "application/octet-stream")
            self.assertEqual(request.get_header("Accept"), expected)
            return Response(bodies[request.full_url])
        return respond

    def acquire(self):
        with patch.object(transport, "urlopen", side_effect=self.responder()) as opener:
            directory = ftn.acquire(self.cache)
        self.assertEqual(opener.call_count, 5)
        return directory

    def test_uses_shared_bounded_transport_and_records_separate_terms(self):
        self.assertIs(ftn._download, transport._download)
        directory = self.acquire()
        manifest = ftn.verify(directory)
        self.assertEqual(directory.name, sha256(self.raw).hexdigest())
        self.assertEqual(ftn.read_csv(directory), self.raw)
        self.assertEqual(manifest["source"]["license"]["identifier"], "CC-BY-SA-4.0")
        self.assertFalse(manifest["source"]["historical_row_availability_verified"])
        self.assertFalse(manifest["source"]["joined_to_pbp"])
        self.assertEqual(set(manifest["files"]), {ftn.ASSET_NAME, *self.docs})
        self.assertEqual(list(self.cache.iterdir()), [directory])

    def test_cache_reuse_and_audit_are_offline_and_preserve_original_manifest(self):
        directory = self.acquire()
        before = (directory / "manifest.json").read_bytes()
        self.assertEqual(ftn.acquire(self.cache), directory)
        first = contract.audit(directory)
        self.assertEqual(first, contract.audit(directory))
        self.assertEqual(first["source_manifest"], ftn.verify(directory))
        self.assertEqual(first["parsed_csv_sha256"], sha256(self.raw).hexdigest())
        self.assertEqual((directory / "manifest.json").read_bytes(), before)

    def test_changed_release_metadata_fails_before_data_download(self):
        mutations = [lambda r: r.update(tag_name="pbp"), lambda r: r.update(id=119740650.0),
                     lambda r: r["assets"].append(r["assets"][0]),
                     lambda r: r["assets"].clear(),
                     lambda r: r["assets"][0].update(size=len(self.raw) + 1),
                     lambda r: r["assets"][0].update(digest="sha256:" + "0" * 64),
                     lambda r: r["assets"][0].update(updated_at="2026-10-30T00:00:00Z"),
                     lambda r: r["assets"][0].update(browser_download_url="https://example.invalid/"),
                     lambda r: r["assets"][0].update(state="new")]
        for mutate in mutations:
            release = self.release()
            mutate(release)
            with patch.object(transport, "urlopen", side_effect=self.responder(release)) as opener:
                with self.assertRaises(transport.SnapshotError):
                    ftn.acquire(self.cache)
            self.assertEqual(opener.call_count, 1)
            self.assertEqual(list(self.cache.iterdir()), [])

    def test_malformed_release_does_not_bypass_pin(self):
        for value in ({}, {"assets": None}, {"assets": [None]}, {"assets": "bad"}):
            with self.assertRaises(transport.SnapshotError):
                ftn._check_release(value)

    def test_corruption_cannot_be_hidden_by_rehashing_manifest(self):
        directory = self.acquire()
        raw = self.raw.replace(b"CAR", b"LAR")
        (directory / ftn.ASSET_NAME).write_bytes(raw)
        path = directory / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["files"][ftn.ASSET_NAME]["sha256"] = sha256(raw).hexdigest()
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(transport.SnapshotError, "SHA-256"):
            ftn.acquire(self.cache)
        self.assertEqual((directory / ftn.ASSET_NAME).read_bytes(), raw)

    def test_bad_download_hash_size_or_document_never_publishes(self):
        for bad in (b"", self.raw[:-1], self.raw + b"x", self.raw.replace(b"CAR", b"LAR")):
            with patch.object(ftn, "_download", side_effect=lambda url, path, *a, **k: path.write_bytes(
                    json.dumps(self.release()).encode() if url == ftn.RELEASE_API else bad)):
                with self.assertRaises(transport.SnapshotError):
                    ftn.acquire(self.cache)
            self.assertEqual(list(self.cache.iterdir()), [])
        original = self.docs["load_ftn_charting.R"]
        self.docs["load_ftn_charting.R"] = b"X" * len(original)
        with patch.object(transport, "urlopen", side_effect=self.responder()):
            with self.assertRaisesRegex(transport.SnapshotError, "Git blob"):
                ftn.acquire(self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_transfer_and_publication_errors_leave_no_partial_snapshot(self):
        with patch.object(ftn, "_download", side_effect=transport.SnapshotError("transfer")):
            with self.assertRaises(transport.SnapshotError):
                ftn.acquire(self.cache)
        with patch.object(transport, "urlopen", side_effect=self.responder()), patch.object(
                ftn.os, "rename", side_effect=PermissionError("publish")):
            with self.assertRaises(PermissionError):
                ftn.acquire(self.cache)
        self.assertEqual(list(self.cache.iterdir()), [])

    def test_manifest_drift_and_json_type_coercions_fail(self):
        directory = self.acquire()
        path = directory / "manifest.json"
        original = path.read_bytes()
        mutations = [lambda m: m.update(extra=1), lambda m: m.update(schema_version=True),
                     lambda m: m.update(retrieved_at_utc="2024-01-01"),
                     lambda m: m["source"].update(season=2024.0),
                     lambda m: m["source"].update(joined_to_pbp=0),
                     lambda m: m["source"]["license"].update(identifier="CC-BY-4.0"),
                     lambda m: m["files"][ftn.ASSET_NAME].update(url="https://example.invalid"),
                     lambda m: m.update(files=None)]
        for mutate in mutations:
            manifest = json.loads(original)
            mutate(manifest)
            path.write_text(json.dumps(manifest))
            with self.assertRaises(transport.SnapshotError):
                ftn.verify(directory)

    def test_existing_lock_empty_destination_and_symlink_are_not_replaced(self):
        self.cache.mkdir()
        lock = self.cache / ".acquire.lock"
        lock.write_text("preserve active writer")
        with self.assertRaisesRegex(transport.SnapshotError, "lock"):
            ftn.acquire(self.cache)
        self.assertEqual(lock.read_text(), "preserve active writer")
        lock.unlink()
        destination = self.cache / ftn.ASSET_SHA256
        destination.mkdir()
        with self.assertRaises(transport.SnapshotError):
            ftn.acquire(self.cache)
        self.assertEqual(list(destination.iterdir()), [])
        alias = self.cache.parent / "alias"
        alias.symlink_to(self.cache, target_is_directory=True)
        with self.assertRaises(transport.SnapshotError):
            ftn.acquire(alias)

    def test_snapshot_extra_missing_or_linked_files_fail(self):
        directory = self.acquire()
        extra = directory / "extra"
        extra.touch()
        with self.assertRaises(transport.SnapshotError):
            ftn.verify(directory)
        extra.unlink()
        path = directory / "manifest.json"
        saved = self.cache / "saved.json"
        path.rename(saved)
        with self.assertRaises(transport.SnapshotError):
            ftn.verify(directory)
        path.symlink_to(saved)
        with self.assertRaises(transport.SnapshotError):
            ftn.verify(directory)

    def test_mutation_after_manifest_verification_is_caught_before_parsing(self):
        directory = self.acquire()
        verified = ftn.verify(directory)

        def mutate(_):
            (directory / ftn.ASSET_NAME).write_bytes(self.raw.replace(b"CAR", b"LAR"))
            return verified
        with patch.object(ftn, "verify", side_effect=mutate):
            with self.assertRaisesRegex(transport.SnapshotError, "SHA-256"):
                contract.audit(directory)

    def test_offline_cli_output_no_clobber_and_failure_has_no_partial_json(self):
        directory = self.acquire()
        output = self.cache / "audit.json"
        args = ["ftn-contract", "--snapshot", str(directory), "--output", str(output)]
        with patch("sys.argv", args):
            contract.main()
        before = output.read_bytes()
        with patch("sys.argv", args), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            contract.main()
        self.assertEqual(output.read_bytes(), before)
        stdout = io.StringIO()
        with patch("sys.argv", args[:3]), redirect_stdout(stdout):
            contract.main()
        self.assertEqual(stdout.getvalue().encode(), before)
        (directory / ftn.ASSET_NAME).write_bytes(b"bad")
        stdout = io.StringIO()
        with (patch("sys.argv", args[:3]), redirect_stdout(stdout),
              redirect_stderr(io.StringIO()), self.assertRaises(SystemExit)):
            contract.main()
        self.assertEqual(stdout.getvalue(), "")


class FTNInventoryTests(unittest.TestCase):
    def setUp(self):
        p = patch.object(transport, "urlopen", side_effect=AssertionError("network forbidden"))
        p.start()
        self.addCleanup(p.stop)

    def test_hand_counted_keys_distinguish_groups_excess_and_affected_rows(self):
        rows = [row(), row(nflverse_play_id="100.0"), row(nflverse_play_id="101"),
                row(nflverse_play_id="NA"), row(nflverse_play_id="1e2"),
                row(nflverse_game_id="unknown")]
        counts = contract.inventory(csv_bytes(rows))["keys"]["nflverse"]["counts"]
        self.assertEqual(counts, {"missing_key_rows": 1, "invalid_key_rows": 2,
            "valid_key_rows": 3, "distinct_keys": 2, "distinct_games": 1,
            "duplicate_key_groups": 1, "rows_in_duplicate_groups": 2, "duplicate_excess_rows": 1})

    def test_exact_id_normalization_rejects_imprecision_aliases_and_bad_shapes(self):
        for value in ("-1", "1.5", "1e2", "NaN", "Infinity", " 100", "100 ",
                      "9007199254740993", "2147483648", "１２", "True"):
            self.assertIsNone(contract._integer(value))
        self.assertEqual(contract._integer("000100.00"), 100)
        self.assertEqual(contract._integer("0"), 0)
        self.assertEqual(contract._integer("2147483647"), 2147483647)
        for value in ("2024_1_CAR_ATL", "2024_01_car_ATL", "2024_01_CAR_ATL "):
            self.assertIsNone(contract._game(value))

    def test_absent_columns_empty_and_all_missing_are_distinct(self):
        empty = contract.inventory(csv_bytes([]))
        self.assertEqual(empty["raw_rows"], 0)
        self.assertEqual(empty["columns"]["is_motion"]["counts"], {"missing_rows": 0, "nonmissing_rows": 0})
        missing = contract.inventory(csv_bytes([row(is_motion="NA"), row(is_motion="")]))
        self.assertEqual(missing["columns"]["is_motion"]["counts"], {"missing_rows": 2, "nonmissing_rows": 0})
        absent = contract.inventory(b"unrelated\nFALSE\n")
        self.assertEqual(absent["columns"]["is_motion"], {"column_present": False, "counts": None})
        self.assertIsNone(absent["keys"]["nflverse"]["counts"])
        self.assertIsNone(absent["source_extraction_time"])
        self.assertEqual(absent["undocumented_columns"], ["unrelated"])

    def test_literal_flags_do_not_coerce_missing_numeric_or_unknown_to_false(self):
        values = ("TRUE", "FALSE", "NA", "", "0", "1", "false", "NULL")
        report = contract.inventory(csv_bytes([row(is_motion=v) for v in values]))
        self.assertEqual(report["logical_encodings"]["is_motion"],
                         {"true_rows": 1, "false_rows": 1, "unrecognized_rows": 4})
        self.assertEqual(report["columns"]["is_motion"]["counts"]["missing_rows"], 2)

    def test_undocumented_zero_location_is_not_valid_or_missing(self):
        report = contract.inventory(csv_bytes([row(qb_location=v) for v in ("0", "P", "U", "S", "NA", "secret")]))
        self.assertEqual(report["documented_codes"]["qb_location"],
                         {"P": 1, "S": 1, "U": 1, "outside_documented_codes": 2})
        self.assertNotIn("secret", json.dumps(report))
        self.assertEqual(report["columns"]["qb_location"]["counts"]["missing_rows"], 1)

    def test_source_timestamps_are_not_available_at_and_invalid_stays_explicit(self):
        values = ("2024-01-01T02:00:00+02:00", "2025-01-01T00:00:00Z", "2024-01-01",
                  "2024-01-01T00:00:00", "2024-02-30T00:00:00Z", "NA", "")
        dates = contract.inventory(csv_bytes([row(date_pulled=v) for v in values]))["source_extraction_time"]
        self.assertEqual(dates, {"valid_rows": 2, "invalid_rows": 3,
            "minimum_utc": "2024-01-01T00:00:00+00:00", "maximum_utc": "2025-01-01T00:00:00+00:00"})

    def test_context_requires_same_2024_season_week_and_records_missing(self):
        rows = [row(), row(season="2023"), row(week="2"), row(week="NA"),
                row(nflverse_game_id="2024_23_CAR_ATL", week="23"),
                row(nflverse_game_id="bad"), row(week="1.0")]
        self.assertEqual(contract.inventory(csv_bytes(rows))["game_season_week_consistency"],
            {"matching_rows": 2, "missing_rows": 1, "inconsistent_or_invalid_rows": 4})

    def test_malformed_header_encoding_quotes_and_ragged_rows_fail(self):
        for raw in (b"", b"a,a\n1,2\n", b"a,\n1,2\n", b" a,b\n1,2\n",
                    b"a,b\n1\n", b"a\n1,2\n", b'a\n"unterminated', b"a\n\xff"):
            with self.assertRaises(transport.SnapshotError):
                contract.inventory(raw)

    def test_bounded_input_and_row_counts(self):
        with patch.object(contract, "MAX_BYTES", 3), self.assertRaises(transport.SnapshotError):
            contract.inventory(b"a\n1\n")
        with patch.object(contract, "MAX_ROWS", 1), self.assertRaises(transport.SnapshotError):
            contract.inventory(b"a\n1\n2\n")

    def test_order_invariance_bom_and_count_partitions(self):
        rows = [row(is_motion="TRUE"), row(nflverse_play_id="101", is_motion="FALSE"), row(is_motion="NA")]
        expected = contract.inventory(csv_bytes(rows))
        self.assertEqual(expected, contract.inventory(b"\xef\xbb\xbf" + csv_bytes(list(reversed(rows)))))
        for column in expected["columns"].values():
            self.assertEqual(sum(column["counts"].values()), 3)
        for name, flags in expected["logical_encodings"].items():
            self.assertEqual(sum(flags.values()) + expected["columns"][name]["counts"]["missing_rows"], 3)

    def test_committed_aggregate_receipt_retains_pins_and_no_integration_claims(self):
        report = json.loads((ROOT / "docs/evidence/ftn-2024-6faae8118cc1.contract.json").read_text())
        self.assertEqual(report["source_manifest"]["source"], ftn.source_identity())
        self.assertEqual(report["parsed_csv_sha256"], ftn.ASSET_SHA256)
        self.assertEqual(report["source_manifest"]["files"][ftn.ASSET_NAME]["size_bytes"], ftn.ASSET_BYTES)
        for name, (_, blob, size) in ftn.SOURCE_FILES.items():
            observed = report["source_manifest"]["files"][name]
            self.assertEqual((observed["git_blob_sha1"], observed["size_bytes"]), (blob, size))
        for name in ("join_to_pbp_performed", "charting_accuracy_validated", "historical_row_availability_verified"):
            self.assertIs(report[name], False)
        self.assertEqual(report["play_families_approved"], [])
        self.assertEqual(report["receipt_license"]["identifier"], "CC-BY-SA-4.0")
        data = report["inventory"]
        self.assertEqual(data["header"], list(contract.FIELDS))
        self.assertEqual(data["raw_rows"], 48031)
        for column in data["columns"].values():
            self.assertTrue(column["column_present"])
            self.assertEqual(sum(column["counts"].values()), data["raw_rows"])
        for name, flags in data["logical_encodings"].items():
            self.assertEqual(sum(flags.values()), data["columns"][name]["counts"]["nonmissing_rows"])
        for name, codes in data["documented_codes"].items():
            self.assertEqual(sum(codes.values()), data["columns"][name]["counts"]["nonmissing_rows"])
        for key in data["keys"].values():
            self.assertEqual(key["counts"]["distinct_keys"], data["raw_rows"])
            self.assertEqual(key["counts"]["distinct_games"], 285)
            self.assertEqual(key["counts"]["duplicate_excess_rows"], 0)


if __name__ == "__main__":
    unittest.main()
