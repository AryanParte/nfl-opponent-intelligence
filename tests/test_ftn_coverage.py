"""Hand-counted, invented football rows; no real FTN data or network in CI."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import csv
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from opponent_intelligence import snapshots
from opponent_intelligence.pbp import DataValidationError, REQUIRED_COLUMNS
from validation import ftn_contract, ftn_coverage as coverage


def csv_bytes(rows, fields):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def pbp(play_id, **changes):
    return dict(game_id="2024_01_CAR_ATL", play_id=str(play_id), season="2024", week="1",
                season_type="REG", posteam="CAR", defteam="ATL", play_type="run", down="1",
                ydstogo="10", qb_dropback="0", qb_kneel="0", qb_spike="0",
                two_point_attempt="0", epa="0") | changes


def ftn(play_id, **changes):
    row = dict.fromkeys(ftn_contract.FIELDS, "NA")
    row.update(dict.fromkeys(coverage.FLAGS, "FALSE"))
    row.update(dict.fromkeys(coverage.COUNTS, "0"))
    row.update(nflverse_game_id="2024_01_CAR_ATL", nflverse_play_id=str(play_id),
               ftn_game_id="1", ftn_play_id=str(play_id), season="2024", week="1",
               starting_hash="L", qb_location="S", read_thrown="0")
    return row | changes


class FTNCoverageTests(unittest.TestCase):
    def setUp(self):
        network = patch.object(snapshots, "urlopen", side_effect=AssertionError("network forbidden"))
        network.start()
        self.addCleanup(network.stop)
        self.pbp = [
            pbp(1, epa="NA"),
            pbp(2, play_type="pass", qb_dropback="1"),
            pbp(3, qb_dropback="1"),  # a scramble: raw run, analytical Pass
            pbp(4, play_type="pass", qb_dropback="1", epa="-2"),  # unmatched dropback
            pbp(5, play_type="punt"), pbp(6, qb_kneel="1"),
            pbp(7, play_type="pass", qb_dropback="1", qb_spike="1"),
            pbp(8, two_point_attempt="1"),
            pbp(1, game_id="2024_02_CAR_NO", week="2", posteam="NO", defteam="CAR",
                play_type="pass", qb_dropback="1"),
            pbp(2, game_id="2024_02_CAR_NO", week="2", defteam="NO"),
        ]
        self.ftn = [ftn(1, qb_location="0"), ftn(2, starting_hash="NA", is_motion="TRUE",
                                              n_defense_box="12"),
                    ftn(3, qb_location="P", is_motion="NA"), ftn(5), ftn(6), ftn(8),
                    ftn(1, nflverse_game_id="2024_02_CAR_NO", week="2", ftn_game_id="2"),
                    ftn(999, nflverse_game_id="2024_03_CAR_TB", week="3", ftn_game_id="3")]

    def compare(self, pbp_rows=None, ftn_rows=None, fields=ftn_contract.FIELDS):
        return coverage.compare(csv_bytes(self.pbp if pbp_rows is None else pbp_rows, REQUIRED_COLUMNS),
                                csv_bytes(self.ftn if ftn_rows is None else ftn_rows, fields))

    def test_left_join_preserves_missing_epa_and_unmatched_plays(self):
        report = self.compare()
        self.assertEqual(report["join"], {
            "cardinality": "one-to-zero-or-one FTN row per eligible PBP play",
            "pbp_raw_rows": 10, "ftn_raw_rows": 8,
            "pbp_exclusions": {"non_run_pass": 1, "kneel": 1, "spike": 1, "two_point_attempt": 1},
            "eligible_pbp_rows": 6, "left_join_rows": 6, "raw_pbp_rows_without_ftn": 3,
            "ftn_rows_matching_eligible_pbp": 4, "ftn_rows_matching_excluded_pbp": 3,
            "ftn_rows_without_pbp": 1,
        })
        self.assertEqual({k: v for k, v in report["overall"].items() if k != "fields"},
                         dict(plays=6, games=2, matched_plays=4, matched_games=2, unmatched_plays=2))

    def test_candidates_use_dropback_not_raw_run_and_defense_does_not_reverse_calls(self):
        report = self.compare()
        run, pas = (report["by_candidate"][c] for c in ("run", "pass"))
        self.assertEqual((run["plays"], run["matched_plays"], pas["plays"], pas["matched_plays"]),
                         (2, 1, 4, 3))
        rows = [dict(zip(report["stratum_columns"], row)) for row in report["strata"]]
        car_defense = [r for r in rows if r["role"] == "defense" and r["team"] == "CAR"]
        self.assertEqual(len(car_defense), 1)
        self.assertEqual((car_defense[0]["week"], car_defense[0]["candidate"], car_defense[0]["plays"]),
                         (2, "pass", 1))  # NO's offense, not CAR's call
        for role in ("offense", "defense"):
            self.assertEqual(sum(r["plays"] for r in rows if r["role"] == role), 6)
            self.assertEqual(sum(r["unmatched_plays"] for r in rows if r["role"] == role), 2)

    def test_each_field_state_partitions_all_plays_without_turning_missing_into_false(self):
        report = self.compare()
        for summary in (report["overall"], *report["by_candidate"].values()):
            for counts in summary["fields"].values():
                self.assertEqual(sum(counts.values()), summary["plays"])
        flags = report["overall"]["fields"]["is_motion"]
        self.assertEqual({s: n for s, n in flags.items() if n},
                         {"literal_true": 1, "literal_false": 2, "missing_value": 1, "unmatched": 2})
        self.assertEqual(report["overall"]["fields"]["qb_location"]["unknown_code"], 1)
        self.assertEqual(report["overall"]["fields"]["n_defense_box"]["invalid_value"], 1)
        row = next(r for r in report["strata"] if r[:5] == ["offense", "CAR", "REG", 1, "pass"])
        self.assertEqual(row[-1], {"starting_hash": {"missing_value": 1},
                                  "n_defense_box": {"invalid_value": 1},
                                  "is_motion": {"missing_value": 1}})

    def test_absent_column_is_not_unmatched_or_missing_value(self):
        report = self.compare(fields=[f for f in ftn_contract.FIELDS if f != "is_rpo"])
        counts = report["overall"]["fields"]["is_rpo"]
        self.assertEqual({s: n for s, n in counts.items() if n}, {"absent_column": 4, "unmatched": 2})

    def test_literal_zero_has_field_specific_meaning_without_applicability_claims(self):
        self.assertEqual(coverage.field_state(ftn(1, qb_location="0"), "qb_location"), "unknown_code")
        self.assertEqual(coverage.field_state(ftn(1), "read_thrown"), "recognized_code")
        self.assertEqual(coverage.field_state(ftn(1), "n_blitzers"), "integer_0_to_11")
        for value in ("0", "1", "false", "TRUE ", "NULL"):
            self.assertEqual(coverage.field_state(ftn(1, is_motion=value), "is_motion"), "invalid_value")
        for value in ("-1", "12", "3.5", "1e1", "NaN", " 3"):
            self.assertEqual(coverage.field_state(ftn(1, n_blitzers=value), "n_blitzers"), "invalid_value")
        for value in ("0", "11", "3.0"):
            self.assertEqual(coverage.field_state(ftn(1, n_blitzers=value), "n_blitzers"), "integer_0_to_11")

    def test_duplicate_keys_fail_in_either_ftn_namespace_even_when_not_eligible(self):
        for extra in (ftn(1, ftn_play_id="100"), ftn("1.00", ftn_play_id="100"),
                      ftn(50, ftn_play_id="1"), ftn(999, nflverse_game_id="2024_03_CAR_TB",
                                                          week="3", ftn_game_id="3")):
            with self.subTest(extra=extra), self.assertRaisesRegex(snapshots.SnapshotError, "duplicate"):
                self.compare(ftn_rows=[*self.ftn, extra])

    def test_invalid_missing_keys_fail_instead_of_becoming_an_unexplained_nonmatch(self):
        for field, value in (("nflverse_play_id", "NA"), ("nflverse_play_id", "1e2"),
                             ("ftn_game_id", ""), ("ftn_play_id", "-1"),
                             ("nflverse_game_id", "unknown")):
            with self.subTest(field=field), self.assertRaisesRegex(snapshots.SnapshotError, "key"):
                self.compare(ftn_rows=[ftn(1, **{field: value})])
        for field in ("nflverse_game_id", "nflverse_play_id", "season", "week", "ftn_play_id"):
            with self.assertRaisesRegex(snapshots.SnapshotError, "requires"):
                self.compare(fields=[f for f in ftn_contract.FIELDS if f != field])

    def test_mismatched_ftn_season_week_are_rejected_including_orphan_rows(self):
        for changes in (dict(season="2023"), dict(week="NA"), dict(week="2"),
                        dict(nflverse_game_id="2024_23_CAR_ATL", week="23")):
            with self.assertRaisesRegex(snapshots.SnapshotError, "season/week"):
                self.compare(ftn_rows=[ftn(999, **changes)])

    def test_pbp_duplicate_and_invalid_rows_keep_production_validation(self):
        for rows in ([*self.pbp, pbp(1)], [pbp(1, season="2023")],
                     [pbp(1, qb_dropback="2")], [pbp(1, down="5")]):
            with self.assertRaises(DataValidationError):
                self.compare(pbp_rows=rows)
        for row in (pbp(1, week="2"), pbp("1e2"), pbp(1, game_id="BAD")):
            with self.assertRaisesRegex(snapshots.SnapshotError, "exact integer"):
                self.compare(pbp_rows=[row])

    def test_same_play_id_across_games_never_cross_matches(self):
        report = self.compare(ftn_rows=[ftn(1)])
        self.assertEqual(report["overall"]["matched_plays"], 1)
        self.assertEqual(report["by_candidate"]["pass"]["matched_plays"], 0)

    def test_excluded_and_orphan_ftn_rows_have_separate_encoding_counts(self):
        report = self.compare()
        outside = report["outside_eligible_pbp"]
        self.assertEqual(outside["matching_excluded_pbp"]["qb_location"], {"recognized_code": 3})
        self.assertEqual(outside["without_pbp"]["qb_location"], {"recognized_code": 1})

    def test_postseason_and_empty_candidates_are_not_fabricated(self):
        row = pbp(1, game_id="2024_19_CAR_ATL", week="19", season_type="POST")
        report = self.compare(pbp_rows=[row], ftn_rows=[])
        self.assertEqual(report["strata"][0][2:5], ["POST", 19, "run"])
        self.assertEqual(report["by_candidate"]["pass"]["plays"], 0)
        self.assertEqual(report["by_candidate"]["pass"]["games"], 0)
        empty = self.compare(pbp_rows=[], ftn_rows=[])
        self.assertEqual(empty["strata"], [])
        self.assertEqual(json.loads(coverage.encode(empty)), empty)

    def test_input_order_and_bom_leave_counts_unchanged_and_do_not_mutate_inputs(self):
        before = deepcopy((self.pbp, self.ftn))
        expected = self.compare()
        actual = self.compare(list(reversed(self.pbp)), list(reversed(self.ftn)))
        expected.pop("parsed_sha256")
        actual.pop("parsed_sha256")
        self.assertEqual(actual, expected)
        actual = coverage.compare(b"\xef\xbb\xbf" + csv_bytes(self.pbp, REQUIRED_COLUMNS),
                                  b"\xef\xbb\xbf" + csv_bytes(self.ftn, ftn_contract.FIELDS))
        actual.pop("parsed_sha256")
        self.assertEqual(actual, expected)
        self.assertEqual((self.pbp, self.ftn), before)

    def test_bounded_malformed_inputs_fail(self):
        raw = csv_bytes(self.pbp, REQUIRED_COLUMNS)
        with patch.object(coverage, "MAX_DECODED_BYTES", len(raw) - 1):
            with self.assertRaisesRegex(snapshots.SnapshotError, "oversized"):
                self.compare()
        for malformed in (b"", b"key,key\n1,2\n", b"a,b\n1\n", b"\xff"):
            with self.assertRaises(snapshots.SnapshotError):
                coverage.compare(raw, malformed)

    def test_audit_keeps_verified_sources_hashes_and_terms_separate(self):
        raw = csv_bytes(self.pbp, REQUIRED_COLUMNS)
        fraw = csv_bytes(self.ftn, ftn_contract.FIELDS)
        pbp_manifest = {"season": 2024, "license": {"identifier": "CC-BY-4.0"}}
        ftn_manifest = {"source": {"license": {"identifier": "CC-BY-SA-4.0"}}}
        with (patch.object(coverage, "_read_snapshot", return_value=(raw, pbp_manifest)) as pbp_read,
              patch.object(coverage.snapshot, "verify", return_value=ftn_manifest) as verify,
              patch.object(coverage.snapshot, "read_csv", return_value=fraw) as ftn_read):
            report = coverage.audit(Path("pbp"), Path("ftn"))
            pbp_read.assert_called_once_with(Path("pbp"))
            verify.assert_called_once_with(Path("ftn"))
            ftn_read.assert_called_once_with(Path("ftn"))
            self.assertEqual(report["source_manifests"], {"pbp": pbp_manifest, "ftn": ftn_manifest})
            self.assertEqual(report["parsed_sha256"], {"pbp_csv": sha256(raw).hexdigest(),
                                                     "ftn_csv": sha256(fraw).hexdigest()})
            for flag in ("charting_accuracy_validated", "field_applicability_validated",
                         "historical_row_availability_verified"):
                self.assertFalse(report[flag])
            self.assertEqual(report["play_families_approved"], [])
            self.assertEqual(report["receipt_license"]["identifier"], "CC-BY-SA-4.0")
            self.assertEqual(json.loads(coverage.encode(report)), report)
            pbp_manifest["season"] = 2023
            with self.assertRaisesRegex(snapshots.SnapshotError, "limited to 2024"):
                coverage.audit(Path("pbp"), Path("ftn"))

    def test_snapshot_verification_errors_stop_before_comparison(self):
        with (patch.object(coverage, "_read_snapshot", side_effect=snapshots.SnapshotError("bad PBP")),
              patch.object(coverage, "compare") as compare):
            with self.assertRaisesRegex(snapshots.SnapshotError, "bad PBP"):
                coverage.audit(Path("pbp"), Path("ftn"))
            compare.assert_not_called()
        with (patch.object(coverage, "_read_snapshot", return_value=(b"", {"season": 2024})),
              patch.object(coverage.snapshot, "verify", side_effect=snapshots.SnapshotError("bad FTN")),
              patch.object(coverage, "compare") as compare):
            with self.assertRaisesRegex(snapshots.SnapshotError, "bad FTN"):
                coverage.audit(Path("pbp"), Path("ftn"))
            compare.assert_not_called()

    def test_cli_no_clobber_and_validation_failure_emits_no_partial_receipt(self):
        report = self.compare()
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "receipt.json"
            args = ["ftn-coverage", "--pbp-snapshot", "pbp", "--ftn-snapshot", "ftn"]
            with patch.object(coverage, "audit", return_value=report):
                with patch("sys.argv", [*args, "--output", str(out)]):
                    coverage.main()
                first = out.read_bytes()
                self.assertEqual(json.loads(first), report)
                stdout = io.StringIO()
                with patch("sys.argv", args), redirect_stdout(stdout):
                    coverage.main()
                self.assertEqual(first.decode(), stdout.getvalue())
                with (patch("sys.argv", [*args, "--output", str(out)]),
                      redirect_stderr(io.StringIO()), self.assertRaises(SystemExit)):
                    coverage.main()
                self.assertEqual(first, out.read_bytes())
            stdout = io.StringIO()
            with (patch.object(coverage, "audit", side_effect=snapshots.SnapshotError("bad")),
                  patch("sys.argv", args), redirect_stdout(stdout), redirect_stderr(io.StringIO()),
                  self.assertRaises(SystemExit)):
                coverage.main()
            self.assertEqual(stdout.getvalue(), "")

    def test_committed_real_receipt_pins_and_every_stratum_reconcile_without_raw_data(self):
        path = Path(__file__).resolve().parents[1] / "docs/evidence/ftn-2024-6faae8118cc1-pbp-23370d5d10f8.coverage.json"
        report = json.loads(path.read_text())
        self.assertEqual(report["parsed_sha256"], {
            "pbp_csv": "6ae564c2c49378ec531303292966caee596982278b9fcdad9c9dd0a0dc16bfa7",
            "ftn_csv": "6faae8118cc13ce62589210d553733128ed35e558671009b4a7a8fc5c674c2cb",
        })
        self.assertEqual(report["parsed_sha256"]["pbp_csv"],
                         report["source_manifests"]["pbp"]["decoded_csv"]["sha256"])
        self.assertEqual(report["parsed_sha256"]["ftn_csv"],
                         report["source_manifests"]["ftn"]["files"]["ftn_charting_2024.csv"]["sha256"])
        self.assertEqual((report["overall"]["plays"], report["overall"]["games"],
                          report["overall"]["unmatched_plays"]), (34902, 285, 0))
        self.assertEqual(report["join"]["ftn_rows_matching_excluded_pbp"], 13129)
        self.assertEqual(report["join"]["ftn_rows_without_pbp"], 0)
        fields = report["overall"]["fields"]
        self.assertEqual(fields["qb_location"]["unknown_code"], 268)
        self.assertEqual(fields["starting_hash"]["unknown_code"], 264)
        self.assertEqual(fields["n_pass_rushers"]["invalid_value"], 1)
        for counts in fields.values():
            self.assertEqual(sum(counts.values()), 34902)
        self.assertEqual(len(report["strata"]), 2280)
        rows = [dict(zip(report["stratum_columns"], row)) for row in report["strata"]]
        for role in ("offense", "defense"):
            selected = [r for r in rows if r["role"] == role]
            self.assertEqual(sum(r["plays"] for r in selected), 34902)
            self.assertEqual(sum(r["matched_plays"] for r in selected), 34902)
            for field in coverage.FIELDS:
                for state in coverage.ISSUES:
                    self.assertEqual(sum(r["field_issues"].get(field, {}).get(state, 0)
                                         for r in selected), fields[field][state])
        self.assertEqual(coverage.encode(report), path.read_text())


if __name__ == "__main__":
    unittest.main()
