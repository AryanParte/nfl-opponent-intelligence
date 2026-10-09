"""HTTP contracts against explicitly synthetic, content-addressed local snapshots."""

from concurrent.futures import ThreadPoolExecutor
import csv
from dataclasses import replace
import json
from pathlib import Path
import tempfile
from threading import Event
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from opponent_intelligence import api, snapshots
from opponent_intelligence.ingestion import load_snapshot
from opponent_intelligence.report import build_report
from tests_api.synthetic_snapshot import write_snapshot


ROOT = Path(__file__).resolve().parents[1]
LABEL = "Synthetic API fixture; not real NFL observations"
QUERY = {"team": "CAR", "season": 2024, "before_week": 3}


class ReportAPITests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        with (ROOT / "tests/fixtures/synthetic_pbp.csv").open(newline="") as source:
            self.rows = [r for r in csv.DictReader(source) if r["season"] == "2024"]
        for target in ("opponent_intelligence.snapshots.urlopen", "socket.create_connection",
                       "socket.socket.connect"):
            guard = patch(target, side_effect=AssertionError("network forbidden"))
            guard.start()
            self.addCleanup(guard.stop)
        self.directory = self.snapshot(self.rows)
        self.dataset = load_snapshot(self.directory)
        self.app = api.create_app(snapshot=self.directory, source_label=LABEL)

    def snapshot(self, rows):
        return write_snapshot(self.root, rows, list(rows[0]) if rows else list(self.rows[0]))

    def expected(self, **options):
        return build_report(self.dataset, source_label=LABEL, **(QUERY | options))

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(set(response.json()), {"error"})
        self.assertEqual(set(response.json()["error"]), {"code", "message", "fields"})
        self.assertEqual(response.json()["error"]["code"], code)
        self.assertNotIn(str(self.root), response.text)
        return response.json()["error"]

    def test_default_response_is_unchanged_schema_v2_with_independent_totals(self):
        with TestClient(self.app) as client:
            response = client.get("/v1/report", params=QUERY)
        self.assertEqual(response.status_code, 200, response.text)
        report = response.json()
        self.assertEqual(report, self.expected())
        self.assertEqual(report["schema_version"], 2)
        self.assertEqual(report["overall"]["plays"], 6)
        self.assertEqual(report["overall"]["epa_observations"], 5)
        self.assertEqual(report["overall"]["missing_epa"], 1)
        self.assertEqual(report["overall"]["dropback_rate"], 0.5)
        self.assertEqual(report["overall"]["success_rate"], 0.6)
        self.assertAlmostEqual(report["overall"]["epa_per_play"], 0.04)
        self.assertEqual(report["source"]["label"], LABEL)
        self.assertEqual(report["source"]["snapshot"], self.dataset.source_manifest)
        self.assertNotIn("uncertainty", report)
        self.assertNotIn("league_comparison", report)

    def test_defense_keeps_offense_relative_epa_and_success(self):
        with TestClient(self.app) as client:
            report = client.get("/v1/report", params=QUERY | {"team": "ATL", "side": "defense"}).json()
        self.assertEqual(report, self.expected(team="ATL", side="defense"))
        self.assertEqual(report["overall"]["plays"], 5)
        self.assertAlmostEqual(report["overall"]["epa_per_play"], 0.05)
        self.assertEqual(report["overall"]["success_rate"], 0.75)
        self.assertEqual(report["metric_context"]["interpretation"], "allowed")

    def test_empty_cohorts_return_nulls_and_warnings_not_not_found(self):
        with TestClient(self.app) as client:
            for options in ({"before_week": 1}, {"team": "ZZZ"}):
                with self.subTest(options=options):
                    response = client.get("/v1/report", params=QUERY | options)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json(), self.expected(**options))
                    self.assertIsNone(response.json()["overall"]["dropback_rate"])
                    self.assertTrue(any("No eligible plays" in x for x in response.json()["warnings"]))

    def test_postseason_and_exclusive_cutoff(self):
        with TestClient(self.app) as client:
            options = {"season_type": "POST", "before_week": 20}
            report = client.get("/v1/report", params=QUERY | options).json()
            self.assertEqual(report, self.expected(**options))
            self.assertEqual(report["overall"]["plays"], 1)
            self.assertEqual(report["overall"]["epa_per_play"], 6)

    def test_comparison_and_uncertainty_preserve_every_core_field(self):
        with TestClient(self.app) as client:
            for repetitions in (200, 1000):
                options = {"compare_league": "true", "bootstrap_repetitions": repetitions, "bootstrap_seed": 0}
                first = client.get("/v1/report", params=QUERY | options)
                second = client.get("/v1/report", params=QUERY | options)
                self.assertEqual(first.status_code, 200, first.text)
                self.assertEqual(first.content, second.content)
                self.assertEqual(first.json(), self.expected(**(options | {"compare_league": True})))
            off = client.get("/v1/report", params=QUERY | {"compare_league": "false"}).json()
            self.assertNotIn("league_comparison", off)
            for options in ({"bootstrap_repetitions": 200},
                            {"bootstrap_repetitions": 200, "bootstrap_seed": 4294967295}):
                response = client.get("/v1/report", params=QUERY | options)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json(), self.expected(**options))

    def test_combined_contexts_missingness_and_zero_bounds(self):
        rows = [dict(row, yardline_100="20", score_differential="0", qtr="4", quarter_seconds_remaining="0")
                for row in self.rows]
        rows[0]["yardline_100"] = "NA"
        rows[1]["quarter_seconds_remaining"] = ""
        directory = self.snapshot(rows)
        options = dict(yardline_max=20, score_min=0, score_max=0, period="Q4", clock_max=0)
        app = api.create_app(snapshot=directory, source_label=LABEL)
        with TestClient(app) as client:
            response = client.get("/v1/report", params=QUERY | options)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), build_report(load_snapshot(directory), source_label=LABEL, **QUERY, **options))
        self.assertEqual(response.json()["overall"]["plays"], 4)
        self.assertEqual(response.json()["data_quality"]["clock_filter"]["missing_quarter_seconds_remaining"], 1)

    def test_invalid_scalars_are_rejected_before_building(self):
        invalid = (
            {"team": "car"}, {"team": "CＡR"}, {"team": "../secret"}, {"before_week": 0},
            {"before_week": 24}, {"before_week": "1.2"}, {"before_week": "true"},
            {"season": 1998}, {"side": "both"}, {"season_type": "PRE"}, {"period": "q4"},
            {"minimum_plays": 0}, {"minimum_plays": 100001}, {"yardline_max": "NaN"},
            {"yardline_min": "Infinity"}, {"yardline_max": 101}, {"score_min": "-0.2"},
            {"score_max": 1001}, {"score_min": -1001}, {"clock_max": 901},
            {"bootstrap_repetitions": 199}, {"bootstrap_repetitions": 1001},
            {"bootstrap_seed": -1}, {"bootstrap_repetitions": 200, "bootstrap_seed": 4294967296},
            {"compare_league": "1"}, {"compare_league": "True"}, {"team": ""},
        )
        with TestClient(self.app) as client, patch.object(api, "build_report") as builder:
            for options in invalid:
                with self.subTest(options=options):
                    self.assert_error(client.get("/v1/report", params=QUERY | options), 422, "invalid_query")
            builder.assert_not_called()

    def test_missing_required_parameters_and_cross_field_errors(self):
        with TestClient(self.app) as client, patch.object(api, "build_report") as builder:
            for field in QUERY:
                params = {k: v for k, v in QUERY.items() if k != field}
                error = self.assert_error(client.get("/v1/report", params=params), 422, "invalid_query")
                self.assertEqual(error["fields"], [field])
            for options in ({"yardline_min": 30, "yardline_max": 20}, {"score_min": 1, "score_max": 0},
                            {"clock_min": 120, "clock_max": 119, "period": "Q4"},
                            {"clock_max": 0}, {"bootstrap_seed": 0}):
                self.assert_error(client.get("/v1/report", params=QUERY | options), 422, "invalid_query")
            builder.assert_not_called()

    def test_snapshot_season_and_required_context_columns_are_enforced(self):
        with TestClient(self.app) as client, patch.object(api, "build_report") as builder:
            self.assert_error(client.get("/v1/report", params=QUERY | {"season": 2025}), 422, "season_unavailable")
            for options, field in (({"yardline_max": 20}, "yardline_100"),
                                   ({"score_max": 0}, "score_differential"), ({"period": "OT"}, "qtr")):
                error = self.assert_error(client.get("/v1/report", params=QUERY | options), 422, "context_unavailable")
                self.assertEqual(error["fields"], [field])
            builder.assert_not_called()

        directory = self.snapshot([dict(row, qtr="4") for row in self.rows])
        with TestClient(api.create_app(snapshot=directory, source_label=LABEL)) as client:
            self.assertEqual(client.get("/v1/report", params=QUERY | {"period": "Q4"}).status_code, 200)
            error = self.assert_error(client.get("/v1/report", params=QUERY | {"period": "Q4", "clock_max": 0}),
                                      422, "context_unavailable")
            self.assertEqual(error["fields"], ["quarter_seconds_remaining"])

    def test_extra_parameters_cannot_select_paths_urls_or_labels(self):
        with TestClient(self.app) as client, patch.object(api, "build_report") as builder:
            for key in ("snapshot", "csv", "path", "url", "source_label", "refresh", "unknown"):
                response = client.get("/v1/report", params=QUERY | {key: "/private/secret"})
                self.assert_error(response, 422, "invalid_query")
                self.assertNotIn("/private/secret", response.text)
            builder.assert_not_called()

    def test_duplicate_parameters_body_methods_and_routes(self):
        with TestClient(self.app) as client:
            self.assert_error(client.get("/v1/report?team=CAR&%74eam=ATL&season=2024&before_week=3"),
                              422, "duplicate_parameter")
            self.assert_error(client.request("GET", "/v1/report", params=QUERY, json={"snapshot": "/private/secret"}),
                              400, "body_not_supported")
            self.assert_error(client.post("/v1/report"), 405, "method_not_allowed")
            for path in ("/v1/report/", "/private/secret", "/docs", "/redoc"):
                self.assert_error(client.get(path), 404, "not_found")

    def test_query_limit_is_checked_before_parsing(self):
        with TestClient(self.app) as client, patch.object(api, "build_report") as builder:
            self.assert_error(client.get("/v1/report?" + "x" * 2049), 414, "query_too_long")
            self.assert_error(client.get("/v1/report?" + "x" * 2048), 422, "invalid_query")
            builder.assert_not_called()

    def test_snapshot_loaded_once_and_runtime_changes_do_not_replace_it(self):
        with patch.object(api, "load_snapshot", wraps=load_snapshot) as loader:
            with TestClient(self.app) as client:
                first = client.get("/v1/report", params=QUERY)
                (self.directory / snapshots.ASSET_NAME).write_bytes(b"corrupted after startup")
                (self.root / "current.json").write_text('{"snapshot_sha256":"different"}')
                with patch.dict("os.environ", {"NFL_OI_SNAPSHOT": "/private/secret"}):
                    second = client.get("/v1/report", params=QUERY)
                self.assertEqual(first.content, second.content)
            loader.assert_called_once_with(self.directory)
        with self.assertRaises(ValueError), TestClient(self.app):
            pass

    def test_startup_failure_never_serves_an_unverified_dataset(self):
        (self.directory / "manifest.json").write_text("{}")
        with self.assertRaises(ValueError), TestClient(self.app):
            pass
        other = self.snapshot([dict(self.rows[0], season="2025")])
        with self.assertRaises(ValueError), TestClient(api.create_app(snapshot=other, source_label=LABEL)):
            pass

    def test_config_is_explicit_and_operator_only(self):
        with patch.dict("os.environ", {}, clear=True), self.assertRaisesRegex(ValueError, "NFL_OI_SNAPSHOT"):
            api.app_from_env()
        for label in ("", " ", "x" * 301):
            with self.assertRaises(ValueError):
                api.create_app(snapshot=self.directory, source_label=label)
        with self.assertRaises(ValueError):
            api.create_app(snapshot=Path("relative"), source_label=LABEL)
        with patch.dict("os.environ", {"NFL_OI_SNAPSHOT": str(self.directory), "NFL_OI_SOURCE_LABEL": LABEL}):
            with TestClient(api.app_from_env()) as client:
                self.assertEqual(client.get("/v1/report", params=QUERY).json(), self.expected())

    def test_resource_limits_fail_startup_and_allow_exact_boundaries(self):
        # These load stubs isolate the API's own bounds from the already-tested parser.
        for rows in (100000, 100001):
            with patch.object(api, "load_snapshot", return_value=replace(self.dataset, input_rows=rows)):
                if rows == 100001:
                    with self.assertRaisesRegex(ValueError, "limits"), TestClient(self.app):
                        pass
                else:
                    with TestClient(self.app):
                        pass
        for games in (300, 301):
            plays = tuple(replace(self.dataset.plays[0], game_id=f"SYNTHETIC_{i}") for i in range(games))
            with patch.object(api, "load_snapshot", return_value=replace(self.dataset, plays=plays)):
                if games == 301:
                    with self.assertRaisesRegex(ValueError, "limits"), TestClient(self.app):
                        pass
                else:
                    with TestClient(self.app):
                        pass

    def test_one_active_report_and_capacity_recovers(self):
        entered, release = Event(), Event()

        def slow_report(*args, **kwargs):
            entered.set()
            if not release.wait(5):
                raise AssertionError("test release timed out")
            return build_report(*args, **kwargs)

        with TestClient(self.app) as client, ThreadPoolExecutor(max_workers=1) as pool:
            with patch.object(api, "build_report", side_effect=slow_report):
                first = pool.submit(client.get, "/v1/report", params=QUERY)
                try:
                    self.assertTrue(entered.wait(5))
                    busy = client.get("/v1/report", params=QUERY)
                    self.assert_error(busy, 503, "report_busy")
                    self.assertEqual(busy.headers["retry-after"], "1")
                finally:
                    release.set()
                self.assertEqual(first.result(timeout=5).status_code, 200)
            self.assertEqual(client.get("/v1/report", params=QUERY).status_code, 200)

    def test_internal_and_response_errors_are_sanitized_and_release_capacity(self):
        with TestClient(self.app, raise_server_exceptions=False) as client:
            with patch.object(api, "build_report", side_effect=RuntimeError("/private/secret")):
                failed = client.get("/v1/report", params=QUERY)
                self.assert_error(failed, 500, "internal_error")
                self.assertNotIn("/private/secret", failed.text)
            bad_rate = self.expected()
            bad_rate["overall"]["dropback_rate"] = 1.1
            nonfinite = self.expected()
            nonfinite["overall"]["epa_per_play"] = float("nan")
            for invalid in ({"schema_version": 99, "secret": "/private/secret"}, bad_rate, nonfinite):
                with patch.object(api, "build_report", return_value=invalid):
                    failed = client.get("/v1/report", params=QUERY)
                    self.assert_error(failed, 500, "internal_error")
                    self.assertNotIn("secret", failed.text)
            self.assertEqual(client.get("/v1/report", params=QUERY).status_code, 200)

    def test_app_without_lifespan_returns_unavailable_not_partial_report(self):
        client = TestClient(self.app)
        self.addCleanup(client.close)
        self.assert_error(client.get("/v1/report", params=QUERY), 503, "snapshot_not_ready")

    def test_openapi_documents_v2_and_stable_error_shape(self):
        with TestClient(self.app) as client:
            schema = client.get("/openapi.json").json()
        operation = schema["paths"]["/v1/report"]["get"]
        self.assertEqual(set(schema["paths"]), {"/v1/report"})
        fields = {p["name"] for p in operation["parameters"]}
        self.assertEqual(fields, set(api.ReportQuery.model_fields))
        self.assertNotIn("snapshot", fields)
        self.assertEqual(operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
                         "#/components/schemas/ReportResponse")
        self.assertEqual(schema["components"]["schemas"]["ReportResponse"]["properties"]["schema_version"]["const"], 2)
        for status in ("400", "422", "414", "500", "503"):
            self.assertEqual(operation["responses"][status]["content"]["application/json"]["schema"]["$ref"],
                             "#/components/schemas/ErrorResponse")


if __name__ == "__main__":
    unittest.main()
