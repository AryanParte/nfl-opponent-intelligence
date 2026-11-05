"""Run/Pass HTTP evidence over invented, verified snapshots; no network access."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import csv
from pathlib import Path
import tempfile
from threading import Event
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from opponent_intelligence import api, snapshots
from opponent_intelligence.decision import DecisionRequest, build_decision_evidence
from opponent_intelligence.ingestion import load_snapshot
from tests_api.synthetic_snapshot import write_snapshot


ROOT = Path(__file__).resolve().parents[1]
LABEL = "Invented decision API fixture; not real NFL observations"
QUERY = dict(team="CAR", season=2024, before_week=3, down=1, distance_min=10, distance_max=10)
SCOUT_QUERY = dict(team="CAR", season=2024, before_week=3)


class DecisionAPITests(unittest.TestCase):
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
        return write_snapshot(self.root, rows, list(rows[0]))

    def expected(self, dataset=None, **options):
        return build_decision_evidence(
            self.dataset if dataset is None else dataset,
            DecisionRequest(**(QUERY | options)), source_label=LABEL,
        )

    def assert_error(self, response, status, code):
        self.assertEqual(response.status_code, status, response.text)
        self.assertEqual(set(response.json()), {"error"})
        detail = response.json()["error"]
        self.assertEqual(set(detail), {"code", "message", "fields"})
        self.assertEqual(detail["code"], code)
        self.assertNotIn(str(self.root), response.text)
        self.assertNotIn("/private/secret", response.text)
        return detail

    def test_default_preserves_contract_and_independent_candidate_totals(self):
        with TestClient(self.app) as client:
            response = client.get("/v1/decision", params=QUERY)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result, self.expected())
        self.assertEqual(result["contract_version"], 1)
        self.assertNotIn("schema_version", result)
        self.assertEqual(result["population"], {"plays": 3, "games": 2})
        run, passed = result["candidates"]
        self.assertEqual((run["plays"], passed["plays"]), (1, 2))
        # The raw run-shaped scramble stays in Pass. A kneel/spike/conversion
        # and the extreme week-3 EPA cannot enter this exact first-and-ten cohort.
        self.assertEqual((run["frequency_denominator"], passed["frequency_denominator"]), (3, 3))
        self.assertEqual((run["frequency"], passed["frequency"]), (1 / 3, 2 / 3))
        self.assertEqual((run["epa_per_play"], run["success_rate"]), (0, 0))
        self.assertAlmostEqual(passed["epa_per_play"], 0.6)
        self.assertEqual(passed["success_rate"], 1)
        self.assertEqual(result["source"]["snapshot"], self.dataset.source_manifest)
        self.assertEqual(result["source"]["sha256"], self.dataset.source_sha256)
        self.assertEqual(result["source"]["label"], LABEL)
        self.assertIsNone(result["comparison"]["preferred_candidate"])
        self.assertEqual(result["comparison"]["status"], "insufficient_evidence")
        self.assertNotIn("league_comparison", result)
        self.assertNotIn("uncertainty", result)

    def test_matched_baseline_keeps_denominators_nulls_and_abstention(self):
        with TestClient(self.app) as client:
            response = client.get("/v1/decision", params=QUERY | {"compare_league": "true", "minimum_plays": 1})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result, self.expected(compare_league=True, minimum_plays=1))
        baseline = result["league_comparison"]
        self.assertEqual(baseline["population"]["excluded_team"], "CAR")
        self.assertEqual(baseline["population"]["teams"], ["ATL"])
        run, passed = baseline["candidates"]
        self.assertEqual(run["frequency"], 0)
        self.assertIsNone(run["epa_per_play"])
        self.assertIsNone(run["difference"]["epa_per_play"])
        self.assertEqual(run["availability"]["outcomes"], "unobserved_candidate")
        self.assertAlmostEqual(passed["difference"]["epa_per_play"], -2.4)
        self.assertAlmostEqual(passed["difference"]["frequency_pp"], -100 / 3)
        self.assertEqual(result["comparison"], self.expected()["comparison"])

    def test_empty_and_missing_outcomes_remain_distinct_from_zero(self):
        with TestClient(self.app) as client:
            for options in ({"before_week": 1}, {"team": "ZZZ"}, {"distance_min": 9, "distance_max": 9}):
                with self.subTest(options=options):
                    response = client.get("/v1/decision", params=QUERY | options | {"compare_league": "true"})
                    self.assertEqual(response.status_code, 200, response.text)
                    result = response.json()
                    self.assertEqual(result, self.expected(**options, compare_league=True))
                    self.assertEqual(result["population"]["plays"], 0)
                    self.assertTrue(all(c["frequency"] is None for c in result["candidates"]))
                    self.assertTrue(all(c["availability"]["outcomes"] == "empty_cohort" for c in result["candidates"]))
            # Second down, 3..6: two Run rows, only one observed EPA; no Pass.
            options = dict(down=2, distance_min=3, distance_max=6)
            result = client.get("/v1/decision", params=QUERY | options).json()
            self.assertEqual(result, self.expected(**options))
            run, passed = result["candidates"]
            self.assertEqual((run["plays"], run["epa_observations"], run["missing_epa"]), (2, 1, 1))
            self.assertEqual((run["frequency"], run["epa_per_play"], run["success_rate"]), (1, 0.2, 1))
            self.assertEqual(passed["frequency"], 0)
            self.assertEqual(passed["availability"]["outcomes"], "unobserved_candidate")
            options = dict(down=2, distance_min=6, distance_max=6)
            result = client.get("/v1/decision", params=QUERY | options).json()
            self.assertEqual(result, self.expected(**options))
            self.assertEqual(result["candidates"][0]["availability"]["outcomes"], "missing_epa")
            self.assertIsNone(result["candidates"][0]["epa_per_play"])
            self.assertEqual(result["candidates"][0]["frequency"], 1)

    def test_cutoff_postseason_and_exact_situation_do_not_widen(self):
        cases = [
            ({"before_week": 2}, 2),
            ({"before_week": 4}, 4),
            ({"season_type": "POST", "before_week": 19}, 0),
            ({"season_type": "POST", "before_week": 20}, 1),
            ({"down": 4, "distance_min": 0, "distance_max": 100}, 0),
            ({"distance_min": 9, "distance_max": 9}, 0),
        ]
        with TestClient(self.app) as client:
            for options, count in cases:
                with self.subTest(options=options):
                    response = client.get("/v1/decision", params=QUERY | options)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json(), self.expected(**options))
                    self.assertEqual(response.json()["population"]["plays"], count)

    def test_context_filters_preserve_order_missingness_and_observed_zero(self):
        rows = [dict(row, yardline_100="20", score_differential="-3", qtr="4", quarter_seconds_remaining="0")
                for row in self.rows]
        rows[0]["yardline_100"] = "NA"
        rows[3]["quarter_seconds_remaining"] = ""
        directory = self.snapshot(rows)
        options = dict(yardline_min=20, yardline_max=20, score_min=-3, score_max=-3,
                       period="Q4", clock_min=0, clock_max=0, compare_league="true")
        with TestClient(api.create_app(snapshot=directory, source_label=LABEL)) as client:
            response = client.get("/v1/decision", params=QUERY | options)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result, self.expected(load_snapshot(directory), **(options | {"compare_league": True})))
        self.assertEqual(result["population"]["plays"], 1)
        self.assertEqual(result["candidates"][0]["epa_per_play"], 0)
        quality = result["data_quality"]
        self.assertEqual(quality["filter_order"],
                         ["field_position", "score_differential", "period", "clock", "down", "distance"])
        self.assertEqual(quality["field_position_filter"]["missing_yardline_100"], 1)
        self.assertEqual(quality["clock_filter"]["missing_quarter_seconds_remaining"], 1)
        self.assertEqual(result["league_comparison"]["population"]["plays"], 1)

    def test_ot_and_present_but_all_missing_context_are_honest(self):
        for period, expected in (("5", 3), ("6", 3), ("", 0)):
            with self.subTest(period=period):
                directory = self.snapshot([dict(row, qtr=period, quarter_seconds_remaining="0") for row in self.rows])
                with TestClient(api.create_app(snapshot=directory, source_label=LABEL)) as client:
                    response = client.get("/v1/decision", params=QUERY | {"period": "OT", "clock_max": 0})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["population"]["plays"], expected)
                self.assertEqual(response.json(), self.expected(load_snapshot(directory), period="OT", clock_max=0))

    def test_opt_in_uncertainty_is_bounded_reproducible_and_retains_withheld_states(self):
        with TestClient(self.app) as client:
            for repetitions, seed in ((200, None), (1000, 4294967295)):
                options = {"bootstrap_repetitions": repetitions, "compare_league": "true"}
                if seed is not None:
                    options["bootstrap_seed"] = seed
                first = client.get("/v1/decision", params=QUERY | options)
                second = client.get("/v1/decision", params=QUERY | options)
                self.assertEqual(first.status_code, 200, first.text)
                self.assertEqual(first.content, second.content)
                result = first.json()
                self.assertEqual(result, self.expected(**(options | {"compare_league": True})))
                frequency = result["uncertainty"]["candidates"][0]["selected"]["frequency"]
                self.assertEqual(frequency["status"], "insufficient_games")
                self.assertIsNone(result["comparison"]["preferred_candidate"])
            # Explicit false is not truthy; resampling may also be selected-only.
            response = client.get("/v1/decision", params=QUERY | {
                "compare_league": "false", "bootstrap_repetitions": 200,
            })
            self.assertEqual(response.status_code, 200, response.text)
            result = response.json()
            self.assertEqual(result, self.expected(bootstrap_repetitions=200))
            self.assertNotIn("league_comparison", result)

    def test_five_game_supported_intervals_cross_http_without_changing_policy(self):
        rows = []
        for game in range(5):
            for team, defense, offset in (("CAR", "ATL", 0), ("ATL", "CAR", 2)):
                for passing in (0, 1):
                    rows.append(self.rows[0] | {
                        "game_id": f"INVENTED_DECISION_{game}", "week": str(game + 1),
                        "posteam": team, "defteam": defense, "play_id": str(offset + passing),
                        "play_type": "pass" if passing else "run", "qb_dropback": str(passing),
                        "epa": str(game - 2 + passing + offset),
                    })
        directory = self.snapshot(rows)
        options = dict(before_week=6, compare_league="true", bootstrap_repetitions=200, bootstrap_seed=7)
        with TestClient(api.create_app(snapshot=directory, source_label=LABEL)) as client:
            response = client.get("/v1/decision", params=QUERY | options)
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result, self.expected(load_snapshot(directory), **(options | {"compare_league": True})))
        for candidate, expected_epa in zip(result["candidates"], (0, 1)):
            self.assertEqual((candidate["plays"], candidate["games"], candidate["epa_per_play"]), (5, 5, expected_epa))
        for candidate in result["uncertainty"]["candidates"]:
            self.assertEqual(candidate["selected"]["epa_per_play"]["status"], "ok")
            self.assertIsNotNone(candidate["selected"]["epa_per_play"]["interval"])
            self.assertEqual(candidate["difference"]["epa_per_play"]["status"], "degenerate_interval")
        self.assertIsNone(result["comparison"]["preferred_candidate"])

    def test_invalid_options_are_rejected_before_either_builder(self):
        invalid = (
            {"down": 0}, {"down": 5}, {"down": "true"}, {"down": "1.5"},
            {"distance_min": -1}, {"distance_max": 101}, {"distance_min": "NaN"},
            {"distance_max": "1.5"}, {"distance_min": 11},
            {"team": "car"}, {"team": "CＡR"}, {"team": "../secret"}, {"team": ""},
            {"season": 1998}, {"season": 10000}, {"season_type": "PRE"},
            {"before_week": 0}, {"before_week": 24}, {"before_week": "1.2"},
            {"yardline_min": "NaN"}, {"yardline_max": "Infinity"}, {"yardline_max": 101},
            {"yardline_min": 20, "yardline_max": 19},
            {"score_min": "-0.2"}, {"score_max": 1001}, {"score_min": -1001},
            {"score_min": 1, "score_max": 0}, {"period": "q4"}, {"clock_max": 0},
            {"period": "Q4", "clock_max": 901}, {"period": "Q4", "clock_min": 2, "clock_max": 1},
            {"minimum_plays": 0}, {"minimum_plays": 100001},
            {"compare_league": "True"}, {"compare_league": "1"},
            {"bootstrap_repetitions": 199}, {"bootstrap_repetitions": 1001},
            {"bootstrap_seed": 0}, {"bootstrap_repetitions": 200, "bootstrap_seed": -1},
            {"bootstrap_repetitions": 200, "bootstrap_seed": 4294967296},
        )
        with (
            TestClient(self.app) as client,
            patch.object(api, "build_decision_evidence") as decision,
            patch.object(api, "build_report") as report,
        ):
            for options in invalid:
                with self.subTest(options=options):
                    self.assert_error(client.get("/v1/decision", params=QUERY | options), 422, "invalid_query")
            decision.assert_not_called()
            report.assert_not_called()

    def test_required_fields_and_route_specific_sanitization(self):
        with TestClient(self.app) as client, patch.object(api, "build_decision_evidence") as builder:
            for field in QUERY:
                params = {k: v for k, v in QUERY.items() if k != field}
                detail = self.assert_error(client.get("/v1/decision", params=params), 422, "invalid_query")
                self.assertEqual(detail["fields"], [field])
            # Down is recognized by Decision but is still an unknown Scout option.
            detail = self.assert_error(client.get("/v1/report", params=SCOUT_QUERY | {"down": 1}),
                                       422, "invalid_query")
            self.assertEqual(detail["fields"], [])
            builder.assert_not_called()

    def test_reject_unsupported_roles_opponents_families_sources_and_models(self):
        fields = {"is_motion": "TRUE", "is_play_action": "TRUE", "is_rpo": "TRUE",
                  "is_screen_pass": "TRUE", "qb_location": "S", "n_defense_box": "7",
                  "shotgun": "1", "offense_personnel": "1 RB, 1 TE, 3 WR", "play_family": "screen"}
        directory = self.snapshot([row | fields for row in self.rows])
        with (
            TestClient(api.create_app(snapshot=directory, source_label=LABEL)) as client,
            patch.object(api, "build_decision_evidence") as builder,
        ):
            for name, value in list(fields.items()) + [
                ("side", "offense"), ("side", "defense"), ("opponent", "ATL"),
                *[(name, "/private/secret") for name in
                  ("snapshot", "csv", "path", "url", "source_label", "refresh", "model", "candidate")],
            ]:
                with self.subTest(name=name, value=value):
                    response = client.get("/v1/decision", params=QUERY | {name: value})
                    detail = self.assert_error(response, 422, "invalid_query")
                    self.assertEqual(detail["fields"], [])
                    self.assertNotIn(name, response.text)
            builder.assert_not_called()

    def test_context_and_season_errors_release_shared_capacity(self):
        with TestClient(self.app) as client, patch.object(api, "build_decision_evidence") as builder:
            for options, code, fields in (
                ({"season": 2025}, "season_unavailable", ["season"]),
                ({"yardline_max": 20, "score_max": 0, "period": "Q4", "clock_max": 0},
                 "context_unavailable", ["qtr", "quarter_seconds_remaining", "score_differential", "yardline_100"]),
                ({"team": "ZZZ", "yardline_max": 20}, "context_unavailable", ["yardline_100"]),
            ):
                detail = self.assert_error(client.get("/v1/decision", params=QUERY | options), 422, code)
                self.assertEqual(detail["fields"], fields)
                self.assertEqual(client.get("/v1/report", params=SCOUT_QUERY).status_code, 200)
            builder.assert_not_called()

    def test_duplicate_body_length_method_and_route_guards(self):
        with TestClient(self.app) as client, patch.object(api, "build_decision_evidence") as builder:
            self.assert_error(client.get("/v1/decision?down=1&%64own=2"), 422, "duplicate_parameter")
            self.assert_error(client.request("GET", "/v1/decision", params=QUERY,
                                             json={"path": "/private/secret"}), 400, "body_not_supported")
            self.assert_error(client.request("GET", "/v1/decision", params=QUERY,
                                             headers={"Transfer-Encoding": "chunked"}), 400, "body_not_supported")
            self.assert_error(client.get("/v1/decision?" + "x" * 2049), 414, "query_too_long")
            self.assert_error(client.get("/v1/decision?" + "x" * 2048), 422, "invalid_query")
            for method in ("POST", "PUT", "DELETE"):
                response = client.request(method, "/v1/decision")
                self.assert_error(response, 405, "method_not_allowed")
                self.assertIn("GET", response.headers["allow"])
            self.assert_error(client.get("/v1/decision/"), 404, "not_found")
            builder.assert_not_called()

    def test_both_routes_share_one_snapshot_and_ignore_runtime_file_changes(self):
        with patch.object(api, "load_snapshot", wraps=load_snapshot) as loader:
            with TestClient(self.app) as client:
                decision = client.get("/v1/decision", params=QUERY)
                scout = client.get("/v1/report", params=SCOUT_QUERY)
                self.assertEqual(decision.status_code, 200)
                self.assertEqual(scout.status_code, 200)
                (self.directory / snapshots.ASSET_NAME).write_bytes(b"corrupt after startup")
                with (
                    patch.dict("os.environ", {"NFL_OI_SNAPSHOT": "/private/secret"}),
                    patch.object(api, "load_snapshot", side_effect=AssertionError("no request reload")),
                ):
                    self.assertEqual(client.get("/v1/decision", params=QUERY).content, decision.content)
                    self.assertEqual(client.get("/v1/report", params=SCOUT_QUERY).content, scout.content)
                self.assertEqual(decision.json()["source"], scout.json()["source"])
            loader.assert_called_once_with(self.directory)
        with self.assertRaises(ValueError), TestClient(self.app):
            pass

    def test_decision_and_scout_overlap_in_both_directions_without_a_second_builder(self):
        for route, params, name, original in (
            ("/v1/decision", QUERY, "build_decision_evidence", build_decision_evidence),
            ("/v1/report", SCOUT_QUERY, "build_report", api.build_report),
        ):
            with self.subTest(active=route):
                entered, release = Event(), Event()

                def slow_builder(*args, **kwargs):
                    entered.set()
                    if not release.wait(5):
                        raise AssertionError("test release timed out")
                    return original(*args, **kwargs)

                with TestClient(self.app) as client, ThreadPoolExecutor(max_workers=1) as pool:
                    with patch.object(api, name, side_effect=slow_builder) as builder:
                        first = pool.submit(client.get, route, params=params)
                        try:
                            self.assertTrue(entered.wait(5))
                            for busy_route, busy_params in (("/v1/decision", QUERY), ("/v1/report", SCOUT_QUERY)):
                                busy = client.get(busy_route, params=busy_params)
                                self.assert_error(busy, 503, "report_busy")
                                self.assertEqual(busy.headers["retry-after"], "1")
                            builder.assert_called_once()
                        finally:
                            release.set()
                        self.assertEqual(first.result(timeout=5).status_code, 200)
                    self.assertEqual(client.get("/v1/decision", params=QUERY).status_code, 200)
                    self.assertEqual(client.get("/v1/report", params=SCOUT_QUERY).status_code, 200)

    def test_internal_errors_are_sanitized_and_release_shared_capacity(self):
        with TestClient(self.app, raise_server_exceptions=False) as client:
            with patch.object(api, "build_decision_evidence", side_effect=RuntimeError("/private/secret")):
                self.assert_error(client.get("/v1/decision", params=QUERY), 500, "internal_error")
            self.assertEqual(client.get("/v1/decision", params=QUERY).status_code, 200)
            self.assertEqual(client.get("/v1/report", params=SCOUT_QUERY).status_code, 200)

    def test_response_errors_cannot_publish_invalid_rates_shapes_or_preferred_calls(self):
        good = self.expected(compare_league=True)
        bad_results = []
        for path, value in (
            (("contract_version",), 2), (("evidence_kind",), "predictive"),
            (("source", "snapshot"), None), (("population", "plays"), -1),
            (("candidates", 0, "frequency"), 1.01), (("candidates", 1, "epa_per_play"), float("nan")),
            (("candidates", 1, "plays"), "2"), (("candidates", 0, "availability", "outcomes"), "guessed"),
            (("candidates", 1, "candidate"), "run"), (("candidates",), [good["candidates"][0]]),
            (("comparison", "preferred_candidate"), "pass"), (("comparison", "status"), "validated"),
            (("comparison", "policy_version"), "unreviewed"),
            (("league_comparison", "candidates", 0, "success_rate"), float("inf")),
            (("league_comparison", "candidates", 0, "difference", "epa_per_play"), float("nan")),
            (("league_comparison", "candidates", 1, "candidate"), "run"),
            (("secret",), "/private/secret"),
        ):
            changed = deepcopy(good)
            target = changed
            for part in path[:-1]:
                target = target[part]
            target[path[-1]] = value
            bad_results.append((path, changed))
        with TestClient(self.app, raise_server_exceptions=False) as client:
            for path, invalid in bad_results:
                with self.subTest(path=path), patch.object(api, "build_decision_evidence", return_value=invalid):
                    self.assert_error(client.get("/v1/decision", params=QUERY | {"compare_league": "true"}),
                                      500, "internal_error")
            self.assertEqual(client.get("/v1/decision", params=QUERY).status_code, 200)
            self.assertEqual(client.get("/v1/report", params=SCOUT_QUERY).status_code, 200)

    def test_without_lifespan_is_unavailable(self):
        with TestClient(self.app) as client:
            self.assertEqual(client.get("/v1/decision", params=QUERY).status_code, 200)
        # Outside lifespan, both before startup and after teardown must abstain.
        for app in (self.app, api.create_app(snapshot=self.directory, source_label=LABEL)):
            client = TestClient(app)
            self.addCleanup(client.close)
            self.assert_error(client.get("/v1/decision", params=QUERY), 503, "snapshot_not_ready")

    def test_openapi_separates_decision_and_scout_contracts(self):
        with TestClient(self.app) as client:
            schema = client.get("/openapi.json").json()
        operation = schema["paths"]["/v1/decision"]["get"]
        params = {p["name"]: p for p in operation["parameters"]}
        self.assertEqual(set(params), (set(api.ReportQuery.model_fields) - {"side"})
                         | {"down", "distance_min", "distance_max"})
        self.assertEqual({name for name, p in params.items() if p["required"]}, set(QUERY))
        self.assertEqual(params["bootstrap_repetitions"]["schema"]["anyOf"][0]["maximum"], 1000)
        self.assertEqual(operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"],
                         "#/components/schemas/DecisionResponse")
        models = schema["components"]["schemas"]
        self.assertEqual(models["DecisionResponse"]["properties"]["contract_version"]["const"], 1)
        self.assertEqual(models["DecisionComparison"]["properties"]["preferred_candidate"]["type"], "null")
        self.assertEqual(models["ReportResponse"]["properties"]["schema_version"]["const"], 2)
        for status in ("400", "422", "414", "500", "503"):
            self.assertEqual(operation["responses"][status]["content"]["application/json"]["schema"]["$ref"],
                             "#/components/schemas/ErrorResponse")


if __name__ == "__main__":
    unittest.main()
