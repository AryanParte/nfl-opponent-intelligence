"""Independent, optional EP candidate for the fixed synthetic protocol only.

No oracle, R output, production package, downloads, training or serving imports.
Feature semantics are adapted from pinned nflfastR; see validation/NOTICE.md.
Run through ep_python_capture.py, which enforces offline execution and compares
the resulting evidence *after* this process has finished.
"""

import argparse
from hashlib import sha256
import json
from math import fsum, isfinite
from pathlib import Path
import platform
import re


FEATURES = ("half_seconds_remaining", "yardline_100", "home", "retractable", "dome",
            "outdoors", "ydstogo", "era0", "era1", "era2", "era3", "era4", "down1",
            "down2", "down3", "down4", "posteam_timeouts_remaining", "defteam_timeouts_remaining")
CLASSES = ("td_prob", "opp_td_prob", "fg_prob", "opp_fg_prob", "safety_prob",
           "opp_safety_prob", "no_score_prob")
STATE_KEYS = {"season", "qtr", "quarter_seconds_remaining", "yardline_100", "ydstogo",
              "down", "neutral_site", "home_team", "away_team", "posteam", "roof",
              "posteam_timeouts_remaining", "defteam_timeouts_remaining"}
RAW_SHA256 = "14a4b7e0c115d3f46fc9f341a024874b0dbcf44b30bb1f426d4f59b6f175335a"
INPUT_SHA256 = "c1a55f9b786f17134468892a62d4be7da18e7112031c3a7a7f448b64d5de496a"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encode_state(state):
    """Reject unsupported/missing states; never infer advanced observations."""
    require(isinstance(state, dict) and set(state) == STATE_KEYS, "state: keys differ")
    bounds = {"season": (1999, 2024), "qtr": (1, 4), "quarter_seconds_remaining": (0, 900),
              "down": (1, 4), "ydstogo": (1, 99), "posteam_timeouts_remaining": (0, 3),
              "defteam_timeouts_remaining": (0, 3)}
    for key, (low, high) in bounds.items():
        require(type(state[key]) is int and low <= state[key] <= high, f"{key}: unsupported")
    yardline = state["yardline_100"]
    require(type(yardline) in (int, float) and 0 < yardline < 100 and isfinite(yardline),
            "yardline_100: unsupported")
    require(state["ydstogo"] <= yardline, "ydstogo: beyond goal line")
    require(state["neutral_site"] is False, "neutral_site: unsupported")
    for key in ("home_team", "away_team", "posteam"):
        require(isinstance(state[key], str) and re.fullmatch(r"[A-Z]{2,3}", state[key]),
                f"{key}: unsupported")
    require(state["home_team"] != state["away_team"], "away_team: same as home")
    require(state["posteam"] in (state["home_team"], state["away_team"]), "posteam: not playing")
    roof = state["roof"]
    require(isinstance(roof, str) and roof in ("outdoors", "dome", "open", "closed"),
            "roof: unsupported")
    season = state["season"]
    if season <= 2001:
        era = 0
    elif season <= 2005:
        era = 1
    elif season <= 2013:
        era = 2
    elif season <= 2017:
        era = 3
    else:
        era = 4
    values = {name: 0 for name in FEATURES}
    values.update({"half_seconds_remaining": state["quarter_seconds_remaining"] +
                   (900 if state["qtr"] % 2 == 1 else 0),
                   "yardline_100": yardline, "home": int(state["posteam"] == state["home_team"]),
                   "retractable": int(roof == "open" or roof == "closed"),
                   "dome": int(roof == "dome"), "outdoors": int(roof == "outdoors"),
                   "ydstogo": state["ydstogo"], f"era{era}": 1, f"down{state['down']}": 1,
                   "posteam_timeouts_remaining": state["posteam_timeouts_remaining"],
                   "defteam_timeouts_remaining": state["defteam_timeouts_remaining"]})
    return [values[name] for name in FEATURES]


def read(path, limit):
    path = Path(path)
    require(not any(p.is_symlink() for p in (path, *path.parents)) and path.is_file(),
            "input is not a regular non-symlink file")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    require(len(raw) <= limit, "input size bound exceeded")
    return raw


def rows(ids, features, predictions):
    require(len(ids) == len(features) == len(predictions), "prediction row count differs")
    result = []
    for identifier, vector, probabilities in zip(ids, features, predictions):
        require(len(probabilities) == 7 and all(type(p) in (int, float) and isfinite(p)
                and 0 <= p <= 1 for p in probabilities), "invalid probabilities")
        require(abs(fsum(probabilities) - 1) <= 1e-6, "probability normalization differs")
        # The next scoring event this half, from the current possession team's
        # perspective. This is a state value, NOT a Run/Pass action value or EPA.
        ep = fsum(p * w for p, w in zip(probabilities, (7, -7, 3, -3, 2, -2, 0)))
        result.append({"id": identifier, "features": vector, "probabilities": probabilities, "ep": ep})
    return result


def capture(model_path, input_path, environment_path):
    # Optional imports intentionally live below the standard-library encoder.
    import numpy as np
    import xgboost as xgb
    from xgboost.libpath import find_lib_path

    raw = read(model_path, 9737490)
    require(len(raw) == 9737490 and sha256(raw).hexdigest() == RAW_SHA256, "raw model identity differs")
    input_raw = read(input_path, 1024 * 1024)
    require(sha256(input_raw).hexdigest() == INPUT_SHA256, "fixed state input identity differs")
    payload = json.loads(input_raw)
    environment_raw = read(environment_path, 1024 * 1024)
    environment = json.loads(environment_raw)
    require(platform.python_version() == "3.13.2" and xgb.__version__ == "3.4.2",
            "runtime version differs")
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "runtime platform differs")
    require(xgb.build_info() == environment["xgboost_build_info"], "native build differs")
    require(not xgb.build_info()["USE_CUDA"] and not xgb.build_info()["USE_OPENMP"], "CPU serial build required")
    native = Path(find_lib_path()[0])
    require(sha256(read(native, 64 * 1024 * 1024)).hexdigest() == environment["native_library_sha256"],
            "native library identity differs")
    require(sha256(read(Path(__file__), 1024 * 1024)).hexdigest() == environment["runner_sha256"],
            "candidate runner differs")
    ids = [entry["id"] for entry in payload["states"]]
    matrix = np.asarray([encode_state(entry["state"]) for entry in payload["states"]], dtype=np.float64)
    booster = xgb.Booster(params={"nthread": 1, "device": "cpu"})
    booster.load_model(bytearray(raw))
    booster.set_param({"nthread": 1, "device": "cpu"})
    config = json.loads(booster.save_config())["learner"]
    require(booster.num_features() == 18 and config["learner_model_param"]["num_class"] == "7"
            and config["objective"]["name"] == "multi:softprob", "model contract differs")

    def predict(selected_ids, values):
        data = xgb.DMatrix(values, feature_names=list(FEATURES), nthread=1)
        observed = data.get_data().toarray()
        require(np.array_equal(observed, values) and data.feature_names == list(FEATURES),
                "DMatrix features differ from encoder input")
        probabilities = booster.predict(data, strict_shape=True)
        require(probabilities.shape == (len(selected_ids), 7), "model output shape differs")
        return rows(selected_ids, observed.tolist(), probabilities.tolist())

    batch = predict(ids, matrix)
    single = [predict([identifier], matrix[i:i + 1])[0] for i, identifier in enumerate(ids)]
    return {"protocol_version": 1, "probability_origin": "model_capture",
            **{key: payload[key] for key in ("fixture_sha256", "source_commits", "model_sha256",
                                           "artifact_manifest_sha256")},
            "runtime": {"language": "Python", "version": platform.python_version(),
                        "xgboost_version": xgb.__version__, "platform": "macos-arm64",
                        "environment_sha256": sha256(environment_raw).hexdigest(),
                        "runner_sha256": environment["runner_sha256"]},
            "feature_order": list(FEATURES), "class_order": list(CLASSES), "batch": batch, "single": single}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--environment", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = capture(args.model, args.input, args.environment)
    require(not any(p.is_symlink() for p in args.output.parents), "symlink output directory")
    with args.output.open("xb") as output:
        output.write(serialize_capture(result))


def serialize_capture(result):
    """Readable headers plus one complete case per line, without float rounding."""
    header = {key: value for key, value in result.items() if key not in ("batch", "single")}
    text = json.dumps(header, sort_keys=True, indent=2, allow_nan=False)[:-2]
    for mode in ("batch", "single"):
        lines = [json.dumps(row, sort_keys=True, allow_nan=False) for row in result[mode]]
        text += f',\n  "{mode}": [\n    ' + ",\n    ".join(lines) + "\n  ]"
    return (text + "\n}\n").encode()


if __name__ == "__main__":
    main()
