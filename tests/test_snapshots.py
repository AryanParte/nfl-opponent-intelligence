"""Offline acquisition tests: every response and release record is synthetic."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta
import errno
import gzip
from hashlib import sha256
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from opponent_intelligence import fetch, snapshots


class Response(io.BytesIO):
    status = 200

    def __init__(self, body, *, length="auto"):
        super().__init__(body)
        self.headers = {} if length is None else {
            "Content-Length": str(len(body)) if length == "auto" else str(length),
        }


class InterruptedResponse(Response):
    def read(self, size=-1):
        if self.tell():
            raise TimeoutError("synthetic interrupted transfer")
        return super().read(min(size, 10))


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.cache = Path(temporary.name) / "cache"
        self.root = self.cache / "pbp" / "2024"
        self.csv = (Path(__file__).parent / "fixtures" / "synthetic_pbp.csv").read_bytes()
        self.archive = gzip.compress(self.csv, mtime=0)
        self.digest = sha256(self.archive).hexdigest()
        sleep_patch = patch.object(snapshots.time, "sleep")
        self.sleep = sleep_patch.start()
        self.addCleanup(sleep_patch.stop)
        network_patch = patch.object(snapshots, "urlopen", side_effect=AssertionError("network forbidden"))
        network_patch.start()
        self.addCleanup(network_patch.stop)

    def release(self, body=None):
        body = self.archive if body is None else body
        return {"id": 100, "tag_name": "pbp", "assets": [{
            "id": 200, "name": "play_by_play_2024.csv.gz", "size": len(body),
            "state": "uploaded", "updated_at": "2025-02-10T00:00:00Z",
            "browser_download_url": snapshots.ASSET_URL,
            "digest": "sha256:" + sha256(body).hexdigest(),
        }]}

    def responses(self, body=None, release=None):
        body = self.archive if body is None else body
        release = self.release(body) if release is None else release
        return [Response(json.dumps(release).encode()), Response(body)]

    def acquire(self, **options):
        with patch.object(snapshots, "urlopen", side_effect=self.responses()):
            return snapshots.fetch_snapshot(self.cache, **options)

    def assert_no_publication(self):
        self.assertFalse((self.root / "current.json").exists())
        self.assertFalse(list(self.root.glob("*")))

    def test_snapshot_records_source_and_both_byte_fingerprints(self):
        with patch.object(snapshots, "urlopen", side_effect=self.responses()) as opener:
            directory = snapshots.fetch_snapshot(self.cache)
        self.assertEqual(directory, self.root / self.digest)
        self.assertEqual([call.args[0].full_url for call in opener.call_args_list],
                         [snapshots.RELEASE_API, snapshots.ASSET_URL])
        self.assertTrue(all(call.kwargs["timeout"] == 30 for call in opener.call_args_list))
        self.assertEqual((directory / snapshots.ASSET_NAME).read_bytes(), self.archive)
        manifest = snapshots.verify_snapshot(directory)
        self.assertEqual(manifest["archive"], {"size_bytes": len(self.archive), "sha256": self.digest})
        self.assertEqual(manifest["decoded_csv"],
                         {"size_bytes": len(self.csv), "sha256": sha256(self.csv).hexdigest()})
        self.assertEqual(manifest["source"]["asset_id"], 200)
        self.assertEqual(manifest["source"]["release_id"], 100)
        self.assertEqual(manifest["source"]["asset_updated_at_utc"], "2025-02-10T00:00:00Z")
        self.assertEqual(datetime.fromisoformat(manifest["retrieved_at_utc"]).utcoffset(), timedelta(0))
        self.assertEqual(manifest["license"]["identifier"], "CC-BY-4.0")
        self.assertEqual(json.loads((self.root / "current.json").read_text()),
                         {"snapshot_sha256": self.digest})
        self.assertFalse(list(self.root.glob(".fetch-*")))

    def test_cache_hit_is_offline_and_preserves_the_original_manifest(self):
        directory = self.acquire()
        original = (directory / "manifest.json").read_bytes()
        with patch.object(snapshots, "urlopen", side_effect=AssertionError("network forbidden")) as opener:
            self.assertEqual(snapshots.fetch_snapshot(self.cache), directory)
        opener.assert_not_called()
        self.assertEqual((directory / "manifest.json").read_bytes(), original)

    def test_same_bytes_on_refresh_do_not_rewrite_provenance(self):
        directory = self.acquire()
        original = (directory / "manifest.json").read_bytes()
        changed_metadata = self.release()
        changed_metadata["assets"][0]["id"] = 201
        with patch.object(snapshots, "urlopen", side_effect=self.responses(release=changed_metadata)):
            self.assertEqual(snapshots.fetch_snapshot(self.cache, refresh=True), directory)
        self.assertEqual((directory / "manifest.json").read_bytes(), original)
        self.assertFalse(list(self.root.glob(".fetch-*")))

    def test_revision_creates_a_new_snapshot_without_altering_old_files(self):
        first = self.acquire()
        old_manifest = (first / "manifest.json").read_bytes()
        updated = gzip.compress(self.csv.replace(b"0.8", b"0.9"), mtime=0)
        with patch.object(snapshots, "urlopen", side_effect=self.responses(updated)):
            second = snapshots.fetch_snapshot(self.cache, refresh=True)
        self.assertNotEqual(first, second)
        self.assertEqual((first / snapshots.ASSET_NAME).read_bytes(), self.archive)
        self.assertEqual((first / "manifest.json").read_bytes(), old_manifest)
        self.assertEqual(snapshots.verify_snapshot(second)["archive"]["sha256"], sha256(updated).hexdigest())
        self.assertEqual(json.loads((self.root / "current.json").read_text())["snapshot_sha256"], second.name)

    def test_transient_http_and_network_failures_retry_with_bounded_backoff(self):
        unavailable = HTTPError(snapshots.RELEASE_API, 503, "synthetic", {}, io.BytesIO())
        responses = self.responses()
        with patch.object(snapshots, "urlopen", side_effect=[unavailable, responses[0],
                                                           TimeoutError(), responses[1]]) as opener:
            snapshots.fetch_snapshot(self.cache, attempts=3, timeout=5)
        self.assertEqual(opener.call_count, 4)
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [1, 1])
        self.assertTrue(all(call.kwargs["timeout"] == 5 for call in opener.call_args_list))

    def test_retry_discards_partial_bytes_instead_of_appending_them(self):
        metadata, valid = self.responses()
        with patch.object(snapshots, "urlopen", side_effect=[metadata, InterruptedResponse(self.archive), valid]):
            directory = snapshots.fetch_snapshot(self.cache)
        self.assertEqual((directory / snapshots.ASSET_NAME).read_bytes(), self.archive)
        self.sleep.assert_called_once_with(1)

    def test_retry_exhaustion_and_permanent_http_errors_do_not_publish(self):
        with patch.object(snapshots, "urlopen", side_effect=URLError("synthetic")) as opener:
            with self.assertRaisesRegex(snapshots.SnapshotError, "after 3 attempts"):
                snapshots.fetch_snapshot(self.cache)
        self.assertEqual(opener.call_count, 3)
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [1, 2])
        for status in (401, 403, 404):
            with self.subTest(status=status):
                error = HTTPError(snapshots.RELEASE_API, status, "synthetic", {}, io.BytesIO())
                with patch.object(snapshots, "urlopen", side_effect=error) as opener:
                    with self.assertRaisesRegex(snapshots.SnapshotError, f"HTTP {status}"):
                        snapshots.fetch_snapshot(self.cache)
                self.assertEqual(opener.call_count, 1)
                self.assert_no_publication()

    def test_incomplete_content_length_retries_without_selecting_partial_data(self):
        metadata, good = self.responses()
        with patch.object(snapshots, "urlopen", side_effect=[metadata,
                Response(self.archive[:-10], length=len(self.archive)), good]):
            directory = snapshots.fetch_snapshot(self.cache)
        snapshots.verify_snapshot(directory)
        self.sleep.assert_called_once_with(1)

    def test_invalid_release_metadata_fails_before_downloading_an_asset(self):
        changes = [("digest", None), ("digest", "sha256:short"), ("size", True),
                   ("size", 0), ("size", snapshots.MAX_ARCHIVE_BYTES + 1),
                   ("browser_download_url", "https://example.com/untrusted.gz"),
                   ("state", "new"), ("id", -1), ("updated_at", "2025-02-10")]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                release = self.release()
                release["assets"][0][key] = value
                with patch.object(snapshots, "urlopen", side_effect=self.responses(release=release)) as opener:
                    with self.assertRaises(snapshots.SnapshotError):
                        snapshots.fetch_snapshot(self.cache)
                self.assertEqual(opener.call_count, 1)
                self.assert_no_publication()
        for release in ({}, [], {**self.release(), "tag_name": "not-pbp"},
                        {**self.release(), "assets": []},
                        {**self.release(), "assets": self.release()["assets"] * 2}):
            with self.subTest(release=release):
                with patch.object(snapshots, "urlopen", return_value=Response(json.dumps(release).encode())):
                    with self.assertRaises(snapshots.SnapshotError):
                        snapshots.fetch_snapshot(self.cache)
                self.assert_no_publication()

    def test_invalid_json_oversized_and_unbounded_length_responses_fail(self):
        for response in (Response(b"not json"), Response(b"{}", length="invalid"),
                         Response(b"{}", length="9" * 5000), Response(b"{}", length="\u0662"),
                         Response(b'{"id":' + b"9" * 5000 + b"}"),
                         Response(b'{"nested":' + b"[" * 2000 + b"0" + b"]" * 2000 + b"}"),
                         Response(b"{}", length=snapshots.MAX_METADATA_BYTES + 1)):
            with self.subTest(response=response):
                with patch.object(snapshots, "urlopen", return_value=response):
                    with self.assertRaises(snapshots.SnapshotError):
                        snapshots.fetch_snapshot(self.cache)
                self.assert_no_publication()
        with patch.object(snapshots, "MAX_METADATA_BYTES", 10), \
                patch.object(snapshots, "urlopen", return_value=Response(b"x" * 11, length=None)):
            with self.assertRaisesRegex(snapshots.SnapshotError, "byte limit"):
                snapshots.fetch_snapshot(self.cache)
        self.assert_no_publication()

    def test_wrong_digest_invalid_gzip_and_expansion_limit_do_not_publish(self):
        changed = bytearray(self.archive)
        changed[4] ^= 1  # Gzip timestamp changes bytes, but leaves the stream decodable.
        with patch.object(snapshots, "urlopen", side_effect=self.responses(bytes(changed), self.release())):
            with self.assertRaisesRegex(snapshots.SnapshotError, "fingerprint mismatch"):
                snapshots.fetch_snapshot(self.cache)
        broken_crc = bytearray(self.archive)
        broken_crc[-8] ^= 1
        for corrupt in (b"not gzip", self.archive[:-8], bytes(broken_crc), gzip.compress(b"", mtime=0)):
            with self.subTest(corrupt=corrupt[:12]):
                with patch.object(snapshots, "urlopen", side_effect=self.responses(corrupt)):
                    with self.assertRaises(snapshots.SnapshotError):
                        snapshots.fetch_snapshot(self.cache)
                self.assert_no_publication()
        with patch.object(snapshots, "MAX_DECODED_BYTES", 10), \
                patch.object(snapshots, "urlopen", side_effect=self.responses()):
            with self.assertRaisesRegex(snapshots.SnapshotError, "byte limit"):
                snapshots.fetch_snapshot(self.cache)
        self.assert_no_publication()

    def test_failed_refresh_leaves_previous_snapshot_and_pointer_unchanged(self):
        directory = self.acquire()
        pointer = (self.root / "current.json").read_bytes()
        manifest = (directory / "manifest.json").read_bytes()
        with patch.object(snapshots, "urlopen", side_effect=self.responses(b"invalid gzip")):
            with self.assertRaises(snapshots.SnapshotError):
                snapshots.fetch_snapshot(self.cache, refresh=True)
        self.assertEqual((self.root / "current.json").read_bytes(), pointer)
        self.assertEqual((directory / "manifest.json").read_bytes(), manifest)
        self.assertEqual((directory / snapshots.ASSET_NAME).read_bytes(), self.archive)
        self.assertFalse(list(self.root.glob(".fetch-*")))

    def test_corrupt_cache_fails_without_network_or_silent_repair(self):
        directory = self.acquire()
        archive_path = directory / snapshots.ASSET_NAME
        archive_path.write_bytes(b"corrupt cache")
        with patch.object(snapshots, "urlopen", side_effect=AssertionError("network forbidden")):
            with self.assertRaisesRegex(snapshots.SnapshotError, "fingerprint mismatch"):
                snapshots.fetch_snapshot(self.cache)
        self.assertEqual(archive_path.read_bytes(), b"corrupt cache")

    def test_invalid_pointer_manifest_and_symlinks_are_rejected(self):
        directory = self.acquire()
        pointer = self.root / "current.json"
        pointer.write_text(json.dumps({"snapshot_sha256": "../outside"}))
        with self.assertRaisesRegex(snapshots.SnapshotError, "pointer"):
            snapshots.fetch_snapshot(self.cache)
        pointer.write_text(json.dumps({"snapshot_sha256": self.digest}))
        manifest_path = directory / "manifest.json"
        original = manifest_path.read_bytes()
        for value in ({}, [], {**json.loads(original), "season": 2025},
                      {**json.loads(original), "season": 2024.0},
                      {**json.loads(original), "decoded_csv": {"sha256": "wrong"}}):
            with self.subTest(value=value):
                manifest_path.write_text(json.dumps(value))
                with self.assertRaises(snapshots.SnapshotError):
                    snapshots.fetch_snapshot(self.cache)
        manifest_path.write_bytes(original)
        link = self.root / ("f" * 64)
        link.symlink_to(directory, target_is_directory=True)
        with self.assertRaisesRegex(snapshots.SnapshotError, "symbolic link"):
            snapshots.verify_snapshot(link)

    def test_pointer_publication_failure_leaves_a_recoverable_complete_snapshot(self):
        with patch.object(snapshots, "urlopen", side_effect=self.responses()), \
                patch.object(snapshots.os, "replace", side_effect=OSError("synthetic disk error")):
            with self.assertRaisesRegex(OSError, "disk error"):
                snapshots.fetch_snapshot(self.cache)
        self.assertFalse((self.root / "current.json").exists())
        snapshots.verify_snapshot(self.root / self.digest)
        self.assertEqual(self.acquire(), self.root / self.digest)

    def test_concurrent_publication_reuses_a_complete_verified_snapshot(self):
        def publish_first(candidate, destination):
            shutil.copytree(candidate, destination)
            raise FileExistsError(errno.EEXIST, "another fetch published first")

        with patch.object(snapshots, "urlopen", side_effect=self.responses()), \
                patch.object(Path, "rename", autospec=True, side_effect=publish_first):
            directory = snapshots.fetch_snapshot(self.cache)
        snapshots.verify_snapshot(directory)
        self.assertEqual(json.loads((self.root / "current.json").read_text())["snapshot_sha256"], self.digest)
        self.assertFalse(list(self.root.glob(".fetch-*")))

    def test_publication_error_does_not_change_the_selected_snapshot(self):
        first = self.acquire()
        pointer = (self.root / "current.json").read_bytes()
        updated = gzip.compress(self.csv.replace(b"0.8", b"0.9"), mtime=0)
        with patch.object(snapshots, "urlopen", side_effect=self.responses(updated)), \
                patch.object(Path, "rename", side_effect=PermissionError(errno.EACCES, "synthetic")):
            with self.assertRaises(PermissionError):
                snapshots.fetch_snapshot(self.cache, refresh=True)
        self.assertEqual((self.root / "current.json").read_bytes(), pointer)
        snapshots.verify_snapshot(first)
        self.assertFalse((self.root / sha256(updated).hexdigest()).exists())
        self.assertFalse(list(self.root.glob(".fetch-*")))

    def test_invalid_options_fail_before_network_or_cache_writes(self):
        for change in ({"season": 2025}, {"season": True}, {"attempts": 0}, {"attempts": 6},
                       {"attempts": True}, {"attempts": 1.5}, {"timeout": 0}, {"timeout": -1},
                       {"timeout": float("nan")}, {"timeout": float("inf")}, {"timeout": 121},
                       {"timeout": True}, {"timeout": 10**1000}):
            with self.subTest(change=change), patch.object(snapshots, "urlopen") as opener:
                with self.assertRaises(snapshots.SnapshotError):
                    snapshots.fetch_snapshot(self.cache, **change)
                opener.assert_not_called()
                self.assertFalse(self.cache.exists())

    def test_cli_outputs_verified_paths_and_no_partial_success_on_error(self):
        directory = self.acquire()
        # Block network inside the subprocess too, even if cache behavior regresses.
        script = ("import runpy\nfrom unittest.mock import patch\n"
                  "with patch('opponent_intelligence.snapshots.urlopen', "
                  "side_effect=AssertionError('network forbidden')):\n"
                  "    runpy.run_module('opponent_intelligence.fetch', run_name='__main__')\n")
        command = [sys.executable, "-c", script, "--season", "2024",
                   "--cache-dir", str(self.cache)]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["snapshot_sha256"], self.digest)
        self.assertEqual(payload["archive_path"], str((directory / snapshots.ASSET_NAME).resolve()))
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = fetch.main(["--season", "2024", "--cache-dir", str(self.cache), "--attempts", "0"])
        self.assertEqual(status, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("error:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
