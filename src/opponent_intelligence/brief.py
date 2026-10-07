"""Deterministic offline Markdown from saved report JSON; never fetches or re-fits."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from string import punctuation
import sys
import unicodedata

from .brief_validation import canonical_report
from .uncertainty import DIFFERENCES, METRICS


MAX_REPORT_BYTES = 4 * 1024 * 1024
DISTANCE_ORDER = {"short": 0, "medium": 1, "long": 2}


def _escape(value) -> str:
    # Values are data, never Markdown/HTML. Collapse line breaks before embedding
    # in headings, tables or lists; make control/bidi format characters visible.
    text = " ".join(str(value).split())
    text = "".join(f"\\u{ord(char):04x}" if unicodedata.category(char) in ("Cc", "Cf", "Cs")
                   else char for char in text)
    return "".join("\\" + char if char in punctuation else char for char in text)


def _table(headers: tuple, rows: list) -> str:
    lines = ["| " + " | ".join(_escape(cell) for cell in headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(_escape(cell) for cell in row) + " |" for row in rows)
    return "\n".join(lines)


def _flatten(value, path: str) -> list:
    if isinstance(value, dict) and value:
        return [row for key in sorted(value) for row in _flatten(value[key], f"{path}.{key}")]
    if isinstance(value, list) and any(isinstance(child, (dict, list)) for child in value):
        return [row for index, child in enumerate(value) for row in _flatten(child, f"{path}[{index}]")]
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=True, allow_nan=False)
    return [(path, text)]


def _number(value, places: int, scale: int = 1, suffix: str = "") -> str:
    if value is None:
        return "unavailable"
    rounded = round(value * scale, places)
    if rounded == 0:
        rounded = 0.0  # Avoid presenting signed rounded zero as a directional finding.
    return f"{rounded:.{places}f}{suffix}"


def _metric(value, key: str) -> str:
    if key.endswith("_pp"):
        return _number(value, 1, suffix=" pp")
    if key == "epa_per_play":
        return _number(value, 3)
    return _number(value, 1, scale=100, suffix="%")


def _sections(report: dict) -> list:
    selected = {(r["down"], r["distance"]): r for r in report["situations"]}
    comparison = report.get("league_comparison")
    baseline = {(r["down"], r["distance"]): r for r in comparison["situations"]} if comparison else {}
    uncertainty = report.get("uncertainty")
    intervals = {(r["down"], r["distance"]): r for r in uncertainty["situations"]} if uncertainty else {}
    keys = [None, *sorted(selected, key=lambda k: (k[0], DISTANCE_ORDER[k[1]]))]
    result = []
    for key in keys:
        scope = "Overall" if key is None else f"Down {key[0]}, {key[1]}"
        populations = {"selected": report["overall"] if key is None else selected[key]}
        difference = None
        if comparison:
            populations["baseline"] = comparison["overall"] if key is None else baseline[key]["baseline"]
            difference = comparison["overall_difference"] if key is None else baseline[key]["difference"]
        bounds = (uncertainty["overall"] if key is None else intervals[key]) if uncertainty else None
        result.append((scope, populations, difference, bounds))
    return result


def render_brief(report: dict) -> str:
    """Render validated v2 JSON without changing it; output has one trailing newline.

    Identical reports produce identical Markdown. No current date, filesystem path,
    network request, reclassification, new metric estimate, or bootstrap is added.
    The fingerprint covers canonical JSON, including fields not summarized here.
    """
    canonical = canonical_report(report)
    fingerprint = sha256(canonical.encode("utf-8")).hexdigest()
    cohort, source = report["cohort"], report["source"]
    comparison, uncertainty = report.get("league_comparison"), report.get("uncertainty")
    sections = _sections(report)
    side = cohort["side"]
    overall = report["overall"]
    title = f"{cohort['team']} {side} — {cohort['season']} {cohort['season_type']}"
    parts = [
        f"# Historical opponent brief: {_escape(title)}",
        f"**Source label (caller supplied):** {_escape(source['label'])}",
        "Descriptive cohort evidence, not a matchup forecast, opponent adjustment, or play recommendation. "
        "Rendering does not authenticate the source or reconstruct information available at game time.",
        f"**Window:** season {_escape(cohort['season'])}, {_escape(cohort['season_type'])}, "
        f"week < {_escape(cohort['before_week_exclusive'])} (exclusive). "
        "This boundary is a requested cutoff, not proof of complete weekly coverage.",
        ("**Role:** opposing offenses facing this defense. EPA stays offense-relative; "
         "success means offensive EPA > 0, not defensive stops." if side == "defense" else
         "**Role:** the selected offense. Success means offensive EPA > 0; dropbacks include sacks and scrambles."),
        "## At a glance",
        f"- Sample: {overall['plays']} eligible plays across {overall['games']} observed games; "
        f"{overall['epa_observations']} observed EPA values and {overall['missing_epa']} missing.\n"
        f"- Dropbacks: {overall['dropbacks']} / {overall['plays']} ({_metric(overall['dropback_rate'], 'dropback_rate')}). "
        f"Success: {_metric(overall['success_rate'], 'success_rate')} of observed EPA. "
        f"EPA per observed play: {_metric(overall['epa_per_play'], 'epa_per_play')}.\n"
        "- Read these as historical descriptions only. Sample warnings and all requested interval states "
        "are reported below; hundreds of plays do not establish independent evidence.",
        f"**Report fingerprint (canonical JSON SHA-256):** `{fingerprint}`\n\n"
        f"**Input fingerprint (decoded CSV SHA-256):** `{source['sha256']}`\n\n"
        "Brief format v1; report schema v2. Full provenance and accounting follow below.",
        "## Cohort and requested contexts",
        _table(("Report field", "Recorded value"), _flatten(cohort, "cohort")),
        "Context fields retain the offense's coordinates: yardline_100 is distance to the opposing goal line; "
        "score is offense minus defense. Clock is pre-play seconds within the selected period (OT groups all overtime periods). "
        "Absent context keys mean no filter; null score bounds are unbounded, not zero. "
        "Active filters run field position → score → period → clock after team/season/week selection.",
        "## Overall measurements",
    ]
    labels = ("Dropback rate (all eligible plays)", "Success rate (observed EPA only)", "EPA per observed play")
    headers = ("Metric", "Selected", "Matching baseline", "Selected − baseline") if comparison else ("Metric", "Selected")
    rows = []
    for key, delta, label in zip(METRICS, DIFFERENCES, labels):
        row = [label, _metric(overall[key], key)]
        if comparison:
            row += [_metric(comparison["overall"][key], key), _metric(comparison["overall_difference"][delta], delta)]
        rows.append(row)
    parts += [_table(headers, rows),
              "Rates are displayed as percentages; rate differences are percentage points (pp), not percent change. "
              "EPA and its differences are expected points per observed play. Values are rounded for display only; "
              "unavailable is not zero. Positive differences mean numerically higher, not universally better.",
              "## Sample support and missingness",
              f"Play/EPA warnings use the requested threshold of {cohort['minimum_plays_warning']} separately. "
              "They are not significance tests. Game counts overlap across situations and must not be summed."]
    counts = []
    measurements = []
    differences = []
    for scope, populations, difference, _ in sections:
        for name, row in populations.items():
            warnings = ", ".join(label for key, label in (("small_sample", "plays"), ("small_epa_sample", "EPA")) if row[key]) or "none"
            counts.append((scope, name, f"{row['plays']} / {row['games']}",
                           f"{row['dropbacks']} / {row['designed_runs']}",
                           f"{row['epa_observations']} / {row['missing_epa']}", warnings))
            if scope != "Overall":
                measurements.append((scope, name, *(_metric(row[k], k) for k in METRICS)))
        if difference is not None:
            differences.append((scope, *(_metric(difference[k], k) for k in DIFFERENCES)))
    parts += [_table(("Scope", "Population", "Plays / games", "Dropbacks / designed runs", "EPA observed / missing", "Below threshold"), counts),
              "Dropback denominator = plays; success and EPA denominators = observed EPA. "
              "Missing EPA does not remove a play from dropback counts. Source fields: overall and situations; "
              "baseline counts: league_comparison.overall and league_comparison.situations[].baseline.",
              "## Down/distance measurements",
              "Short = 0–3 yards to go, medium = 4–6, long = 7+. Only selected-team observed buckets are listed. "
              "These are descriptive product buckets, not standardized scouting grades.",
              _table(("Scope", "Population", "Dropback rate", "Success rate", "EPA / observed play"), measurements)
              if measurements else "No selected-team situations are observed in this cohort.",
              "## Matching league comparison"]
    if comparison:
        population = comparison["population"]
        parts += [f"Available-source baseline: {population['team_count']} observed other teams in the same role; "
                  f"{population['shared_games_with_selected']} games shared with the selected cohort. "
                  "Counts are pooled across plays, not averaged across teams. This does not certify full league coverage.",
                  _table(("Population field", "Recorded value"), _flatten(population, "league_comparison.population")),
                  _table(("Scope", "Dropback difference", "Success difference", "EPA difference"), differences),
                  "Differences are selected minus matching baseline. Missing matches remain unavailable; "
                  "overall data is not substituted. Baseline-only buckets are not displayed, so baseline situation "
                  "counts need not sum to baseline overall. Overall context mixes may differ despite matching filters. "
                  "Source: league_comparison.overall_difference and situations[].difference."]
    else:
        parts.append("Not requested in this report. No baseline or comparison is inferred.")
    parts.append("## Exploratory game-level uncertainty")
    if uncertainty:
        metadata = {k: v for k, v in uncertainty.items() if k not in ("overall", "situations", "warnings")}
        parts += ["Nominal 95% pointwise percentile intervals, not calibrated coverage, significance tests, or predictions. "
                  "Whole games are resampled; repeated teams/opponents across games remain dependent. "
                  "Support/validity gates are application policies. More draws do not add observed games.",
                  _table(("Method field", "Recorded value"), _flatten(metadata, "uncertainty"))]
        intervals = []
        for scope, populations, _, bounds in sections:
            for name in [*populations, *(["difference"] if comparison else [])]:
                keys = DIFFERENCES if name == "difference" else METRICS
                for key in keys:
                    item = bounds[name][key]
                    interval = item["interval"]
                    value = (f"[{_metric(interval['lower'], key)}, {_metric(interval['upper'], key)}] (ok)"
                             if interval else f"unavailable ({item['status']})")
                    support = "; ".join(f"{side}={count}" for side, count in sorted(item["support_games"].items()))
                    intervals.append((scope, f"{name}: {key}", value, support, "yes" if item["few_games"] else "no",
                                      f"{item['valid_replicates']} / {item['undefined_replicates']}"))
        parts += [_table(("Scope", "Population: metric", "Interval or status", "Supporting games", "Few games?", "Valid / undefined draws"), intervals),
                  "Source: uncertainty.overall and uncertainty.situations, matched by down/distance. "
                  "Undefined draws are counted and excluded; available intervals condition on defined draws. "
                  "The status ok means available under this method, not reliable inference. "
                  "A displayed narrow/rounded interval is not certainty; consult full-precision JSON. "
                  "Five-game and 95%-valid gates withhold unsupported results; few_games warns below 20 on any required side."]
    else:
        parts.append("Not requested in this report. Play-count warnings alone do not estimate uncertainty.")
    parts += ["## Source and provenance",
              "Recorded metadata from the supplied report, not revalidated by this renderer. "
              "The report fingerprint identifies its canonical JSON content, not an authenticity signature.",
              _table(("Report field", "Recorded value"), _flatten(source, "source"))]
    if "snapshot" not in source:
        parts.append("No acquisition manifest supplied. The label is caller supplied; no source license or acquisition date is inferred.")
    else:
        parts.append("Transformation: this brief summarizes the supplied cohort metrics from the recorded snapshot; "
                     "the renderer does not change raw data. Snapshot license attribution and source URLs are recorded above.")
    parts += ["## Row accounting",
              _table(("Report field", "Recorded count / value"), _flatten(report["data_quality"], "data_quality"))]
    if comparison:
        parts.append(_table(("Baseline field", "Recorded count / value"),
                            _flatten(comparison["data_quality"], "league_comparison.data_quality")))
    parts += ["Filter-stage counts are conditional on prior survivors. Removals are already included in outside-cohort counts; "
              "do not add nested counts or the baseline ledger to the source totals again.", "## Limitations and report warnings",
              "Eligible completed run/pass plays only: kneels, spikes, conversions, non-run/pass and nullified/no-play outcomes "
              "are excluded. Designed runs are an outcome-based proxy, not film-verified intent. "
              "Personnel, motion and opponent strength are not controlled. Upstream EPA-model uncertainty, revisions and "
              "historical information availability are not resolved by a week cutoff or bootstrap."]
    for name, block in (("report", report), ("league_comparison", comparison), ("uncertainty", uncertainty)):
        if block is not None:
            parts.append(f"### {_escape(name)}.warnings")
            parts.append("\n".join("- " + _escape(w) for w in block["warnings"]) or "No additional warnings recorded.")
    return "\n\n".join(parts) + "\n"


def _unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value: str):
    raise ValueError(f"non-finite JSON number: {value}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render saved schema-v2 report JSON as an offline historical Markdown brief.")
    parser.add_argument("--report", required=True, help="UTF-8 report JSON file, or - for stdin (maximum 4 MiB)")
    args = parser.parse_args(argv)
    try:
        if args.report == "-":
            content = sys.stdin.read(MAX_REPORT_BYTES + 1).encode("utf-8")
        else:
            with Path(args.report).open("rb") as source:
                content = source.read(MAX_REPORT_BYTES + 1)
        if len(content) > MAX_REPORT_BYTES:
            raise ValueError("report exceeds 4 MiB limit")
        report = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
        result = render_brief(report)
    except (OSError, ValueError, RecursionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(result, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
