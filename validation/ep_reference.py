"""Repository-only EP experiment protocol. No model loading, downloads or serving.

The feature oracle and synthetic corpus precede any R/Python prediction capture.
Comparing captures checks arithmetic/identity consistency, not their authenticity,
calibration, historical availability or suitability for choosing a play.
See NOTICE.md for upstream feature-encoding attribution.
"""

from hashlib import sha256
import json
from math import fsum, isfinite
from pathlib import Path
import re


FIXTURE = Path(__file__).with_name("fixtures") / "ep_reference_cases.json"
FIXTURE_SHA256 = "5d2a4282a838e2757a0ebf948587919a28799ab5fc05ebb4b4e70bee10ac2bc9"
SOURCE_COMMITS = {
    "fastrmodels": "ca185baf7757c2992e57ce2bdf2f296c515465d8",
    "nflfastR": "917b14e5085f352d9b00d23628759773e7d411b5",
}
FEATURES = (
    "half_seconds_remaining", "yardline_100", "home", "retractable", "dome",
    "outdoors", "ydstogo", "era0", "era1", "era2", "era3", "era4", "down1",
    "down2", "down3", "down4", "posteam_timeouts_remaining", "defteam_timeouts_remaining",
)
CLASSES = ("td_prob", "opp_td_prob", "fg_prob", "opp_fg_prob", "safety_prob",
           "opp_safety_prob", "no_score_prob")
POINTS = (7, -7, 3, -3, 2, -2, 0)
PROBABILITY_ATOL = 1e-6
EP_ATOL = 1e-5
STATE_KEYS = {"season", "home_team", "away_team", "posteam", "neutral_site", "roof",
              "qtr", "quarter_seconds_remaining", "down", "ydstogo", "yardline_100",
              "posteam_timeouts_remaining", "defteam_timeouts_remaining"}


class ProtocolError(ValueError):
    """A predeclared experiment condition or capture invariant was violated."""


def _require(condition, message):
    if not condition:
        raise ProtocolError(message)


def _keys(value, expected, label):
    _require(isinstance(value, dict) and set(value) == set(expected), f"{label}: keys differ")


def _number(value):
    # Do not coerce strings/bools or overflow float conversion of large integers.
    return type(value) in (int, float) and (type(value) is int or isfinite(value))


def _integer(value, low, high, label):
    _require(type(value) is int and low <= value <= high, f"{label}: outside integer domain")


def feature_oracle(state):
    """Strict synthetic-experiment domain, NOT upstream validation or a Play adapter."""
    _keys(state, STATE_KEYS, "state")
    _integer(state["season"], 1999, 2024, "season")
    _integer(state["qtr"], 1, 4, "qtr")
    _integer(state["quarter_seconds_remaining"], 0, 900, "quarter_seconds_remaining")
    _integer(state["down"], 1, 4, "down")
    _integer(state["ydstogo"], 1, 99, "ydstogo")
    for key in ("posteam_timeouts_remaining", "defteam_timeouts_remaining"):
        _integer(state[key], 0, 3, key)
    yardline = state["yardline_100"]
    _require(_number(yardline) and 0 < yardline < 100, "yardline_100: outside field interior")
    _require(state["ydstogo"] <= yardline, "ydstogo: beyond goal line")
    _require(state["neutral_site"] is False, "neutral_site: unsupported or unknown")
    for key in ("home_team", "away_team", "posteam"):
        value = state[key]
        _require(isinstance(value, str) and re.fullmatch(r"[A-Z]{2,3}", value) is not None,
                 f"{key}: expected a synthetic team code")
    _require(state["home_team"] != state["away_team"], "away_team: must differ from home")
    _require(state["posteam"] in (state["home_team"], state["away_team"]),
             "posteam: not one of the game's teams")
    roof = state["roof"]
    _require(roof in ("outdoors", "dome", "open", "closed"), "roof: unsupported or missing")
    season = state["season"]
    era = sum(season > boundary for boundary in (2001, 2005, 2013, 2017))
    half_clock = state["quarter_seconds_remaining"] + (900 if state["qtr"] in (1, 3) else 0)
    return [half_clock, yardline, int(state["posteam"] == state["home_team"]),
            int(roof in ("open", "closed")), int(roof == "dome"), int(roof == "outdoors"),
            state["ydstogo"], *(int(era == i) for i in range(5)),
            *(int(state["down"] == i) for i in range(1, 5)),
            state["posteam_timeouts_remaining"], state["defteam_timeouts_remaining"]]


def _exact_vector(actual, expected, label):
    _require(isinstance(actual, list) and len(actual) == len(expected), f"{label}: shape differs")
    _require(all(_number(a) and a == e for a, e in zip(actual, expected)), f"{label}: values differ")


def validate_fixture(fixture):
    _keys(fixture, ("protocol_version", "label", "base_state", "accepted", "rejected"), "fixture")
    _require(type(fixture["protocol_version"]) is int and fixture["protocol_version"] == 1,
             "fixture: unsupported version")
    _require(fixture["label"] == "Synthetic protocol cases; not NFL observations or predictions",
             "fixture: missing synthetic label")
    feature_oracle(fixture["base_state"])
    ids = set()
    for group in ("accepted", "rejected"):
        cases = fixture[group]
        _require(isinstance(cases, list) and 1 <= len(cases) <= 128, f"{group}: invalid case count")
        for case in cases:
            _keys(case, ("id", "overrides", "features" if group == "accepted" else "error"), group)
            identifier = case["id"]
            _require(isinstance(identifier, str) and
                     re.fullmatch(r"[a-z0-9-]{1,64}", identifier) is not None and identifier not in ids,
                     "fixture: invalid or duplicate case id")
            ids.add(identifier)
            _require(isinstance(case["overrides"], dict), f"{identifier}: invalid overrides")
            state = fixture["base_state"] | case["overrides"]
            if group == "accepted":
                _exact_vector(case["features"], feature_oracle(state), identifier)
            else:
                _require(isinstance(case["error"], str) and bool(case["error"]), "invalid error label")
                try:
                    feature_oracle(state)
                except ProtocolError as exc:
                    _require(case["error"] in str(exc), f"{identifier}: wrong rejection")
                else:
                    raise ProtocolError(f"{identifier}: rejected state was accepted")


def load_fixture(path=FIXTURE):
    raw = Path(path).read_bytes()
    fingerprint = sha256(raw).hexdigest()
    _require(fingerprint == FIXTURE_SHA256, "fixture bytes differ from the pinned corpus")
    fixture = json.loads(raw)
    validate_fixture(fixture)
    return fixture, fingerprint


def _digest(value, label):
    _require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None
             and value != "0" * 64, f"{label}: expected a recorded SHA-256")


def _prediction(row, label):
    probabilities = row["probabilities"]
    _require(isinstance(probabilities, list) and len(probabilities) == 7,
             f"{label}: probability shape differs")
    _require(all(_number(p) and 0 <= p <= 1 for p in probabilities), f"{label}: invalid probability")
    _require(abs(fsum(probabilities) - 1) <= PROBABILITY_ATOL, f"{label}: probabilities do not sum to one")
    ep = row["ep"]
    _require(_number(ep) and -7 <= ep <= 7, f"{label}: invalid EP")
    _require(abs(ep - fsum(p * w for p, w in zip(probabilities, POINTS))) <= EP_ATOL,
             f"{label}: EP disagrees with class weights")


def _close_rows(left, right, label):
    _require(all(abs(a - b) <= PROBABILITY_ATOL
                 for a, b in zip(left["probabilities"], right["probabilities"])),
             f"{label}: probability mismatch")
    _require(abs(left["ep"] - right["ep"]) <= EP_ATOL, f"{label}: EP mismatch")


def _capture(capture, fixture, fixture_hash, language):
    _keys(capture, ("protocol_version", "probability_origin", "fixture_sha256", "source_commits",
                    "model_sha256", "artifact_manifest_sha256", "runtime", "feature_order",
                    "class_order", "batch", "single"), language)
    _require(type(capture["protocol_version"]) is int and capture["protocol_version"] == 1,
             "capture: unsupported version")
    _require(capture["probability_origin"] in ("model_capture", "synthetic_test"), "unknown probability origin")
    _require(capture["fixture_sha256"] == fixture_hash, "fixture identity mismatch")
    _require(capture["source_commits"] == SOURCE_COMMITS, "source pin mismatch")
    _require(capture["feature_order"] == list(FEATURES), "feature order mismatch")
    _require(capture["class_order"] == list(CLASSES), "class order mismatch")
    for key in ("model_sha256", "artifact_manifest_sha256"):
        _digest(capture[key], key)
    runtime = capture["runtime"]
    _keys(runtime, ("language", "version", "xgboost_version", "platform", "environment_sha256",
                    "runner_sha256"), "runtime")
    _require(runtime["language"] == language, "runtime language mismatch")
    for key in ("version", "xgboost_version", "platform"):
        _require(isinstance(runtime[key], str) and bool(runtime[key].strip()), f"runtime: missing {key}")
    for key in ("environment_sha256", "runner_sha256"):
        _digest(runtime[key], key)
    for mode in ("batch", "single"):
        rows = capture[mode]
        _require(isinstance(rows, list) and len(rows) == len(fixture["accepted"]), f"{mode}: case count mismatch")
        for row, case in zip(rows, fixture["accepted"]):
            _keys(row, ("id", "features", "probabilities", "ep"), mode)
            _require(row["id"] == case["id"], f"{mode}: case order mismatch")
            _exact_vector(row["features"], case["features"], f"{mode}/{case['id']}")
            _prediction(row, f"{mode}/{case['id']}")
    for batch, single in zip(capture["batch"], capture["single"]):
        _close_rows(batch, single, f"{language}: batch/single/{batch['id']}")


def compare_captures(reference, candidate, fixture_path=FIXTURE):
    """Check captures against the fixed corpus. Metadata is not byte attestation."""
    fixture, fixture_hash = load_fixture(fixture_path)
    _capture(reference, fixture, fixture_hash, "R")
    _capture(candidate, fixture, fixture_hash, "Python")
    for key in ("probability_origin", "model_sha256", "artifact_manifest_sha256"):
        _require(reference[key] == candidate[key], f"{key}: captures use different evidence")
    for mode in ("batch", "single"):
        for left, right in zip(reference[mode], candidate[mode]):
            _close_rows(left, right, f"cross-runtime/{mode}/{left['id']}")
    return {"status": "capture_comparison_pass", "probability_origin": reference["probability_origin"],
            "cases": len(fixture["accepted"]), "fixture_sha256": fixture_hash,
            "artifact_bytes_attested": False, "predictive_validation": False}


if __name__ == "__main__":
    corpus, fingerprint = load_fixture()
    print(json.dumps({"status": "synthetic_input_protocol_pass", "fixture_sha256": fingerprint,
                      "accepted_cases": len(corpus["accepted"]), "rejected_cases": len(corpus["rejected"]),
                      "model_predictions": "not_acquired_or_executed"}, indent=2))
