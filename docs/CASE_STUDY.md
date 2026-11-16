# Three retrospective football walkthroughs

This small demo package shows how to ask a football question, inspect the sample
and stop where the evidence stops. It reuses the completed Scout and Run/Pass
builders; it adds no model, dataset or statistical formula. All three cases use
CAR offense, 2024 regular season, with **no field-position, score, period or clock
restriction**. They describe historical cohorts, not fully specified game states.

The two Decision cases were already included in the eight predeclared
[2026-10-20 audit situations](DECISION_AUDIT.md). They are curated here to illustrate
ordinary and thin evidence, not selected to validate a strategy or win a hypothesis
test. The [capture receipt](examples/portfolio-replay.json) records exact requests,
artifact hashes and the application commit used for the screenshots.

## Inputs and provenance

These examples use the existing nflverse PBP snapshot acquired **2026-09-30 UTC**,
with upstream asset update **2026-08-13**:

- Archive SHA-256: `23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06`
- Decoded CSV SHA-256: `6ae564c2c49378ec531303292966caee596982278b9fcdad9c9dd0a0dc16bfa7`
- Source label: `nflverse 2024 retrospective snapshot; acquired 2026-09-30 UTC`
- Attribution: **nflverse play-by-play data**, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
  per the acquisition manifest and [recorded source terms](INGESTION.md).
  The JSON, tables and screenshots are derived aggregates/presentations; no raw
  season rows are redistributed. The manifest's unchanged-archive statement
  describes the input, not the absence of transformations in these artifacts.

Week cutoffs are exclusive. Acquiring revised 2024 data in 2026 does not establish
2024 information availability; these are retrospective software demonstrations,
not historically deployed predictions. [Metric definitions](METRICS.md) apply:
Pass includes eligible sacks/scrambles; Run is non-dropback. Success is EPA > 0.
Frequency uses the parent cohort's eligible plays; each candidate's EPA/success
uses its observed EPA. Every cohort below has zero missing EPA. Game counts for
Run and Pass can overlap and must not be added as independent samples.

## 1. Scout: put the season in league context

**Question:** What did CAR's offense do over the observed regular season, and how
did the aggregate compare with other offenses in the same historical window?

In Scout, set CAR / offense / 2024 / REG / before week **19**. Leave all optional
context bounds blank, enable **Compare with other teams in the same role**, and
set bootstrap repetitions **1000**, seed **20261006**. Keep the default count
warning threshold **30**, then select **Build report**.

| Measure | CAR offense | Other offenses, pooled |
| --- | ---: | ---: |
| Eligible plays / games | 984 / 17 | 32,351 / 272 |
| Dropbacks / eligible plays | 626 / 984 (63.6%) | 19,490 / 32,351 (60.2%) |
| Observed EPA / missing EPA | 984 / 0 | 32,351 / 0 |
| EPA per observed play | −0.052 | +0.011 |
| Offensive success | 41.4% | 44.0% |

CAR's observed dropback rate is **3.4 percentage points higher**, while EPA/play
is **0.064 lower** and success **2.6 percentage points lower**. This is a
pooled-play comparison under the same window, not an adjustment for opponent
strength or for each offense's mixture of situations. It does not show what
would have happened had CAR changed its run/pass policy.

Inspect down/distance splits, the league coverage, warnings and support intervals
before making a more specific statement. [Open the saved historical brief](examples/car-2024-reg-before-week-19.md)
or [full Scout JSON](examples/car-2024-reg-before-week-19.report.json).
The README's [Scout screenshot](examples/portfolio-scout.png) shows this exact query.

## 2. Decision Lab: narrow the question to first-and-ten

**Question:** How do observed Run and Pass outcomes look on first-and-ten, rather
than across all of CAR's offensive situations?

In Decision Lab, set CAR / 2024 / REG / before week **19**, exact down **1**,
minimum and maximum yards to go **10**. Leave optional context bounds blank,
enable **Compare with other offenses**, and set bootstrap repetitions **200**,
seed **17**. Keep count warning threshold **30**, then **Compare Run and Pass**.

| Evidence | Run | Pass |
| --- | ---: | ---: |
| Plays / parent plays (frequency) | 189 / 387 (48.8%) | 198 / 387 (51.2%) |
| Games with the candidate | 17 | 17 |
| Observed EPA / missing EPA | 189 / 0 | 198 / 0 |
| EPA per observed play | +0.048 | +0.022 |
| Offensive success | 42.9% | 43.9% |
| Other-offense candidate plays | 6,373 | 6,293 |
| Other-offense candidate EPA/play | −0.098 | +0.094 |
| CAR minus baseline EPA/play | +0.146 | −0.072 |

The league baseline matches first-and-ten in the same window, excludes CAR as
the selected offense and pools **12,666 plays / 272 games / 31 other offenses**.
Seventeen games are shared with the selected cohort. Each call's baseline is
compared with that same call, not with the pooled Run+Pass average.

The selected Run and Pass EPA averages are both positive in this narrower cohort,
even though Scout's whole-season average is negative. The different questions
have different denominators. That contrast makes situational analysis useful;
it does not make Run the better call. The observed calls happened on different
plays, and selection/confounding are not removed by these filters.

The selected EPA intervals are approximately **[−0.057, +0.150]** for Run and
**[−0.107, +0.131]** for Pass, with 17 supporting games each and a few-games
warning. These are exploratory nominal 95% game-bootstrap intervals from just
200 draws, not calibrated forecasts. Comparing their overlap is not a test of
Run versus Pass; the direct Pass-minus-Run contrast has no implemented interval.
Both modes keep their own denominators and warnings visible.

Optionally select **Your call: Pass** or **Run**. It marks a row, does not fetch new
evidence, and does not grade the choice. Download the JSON: the returned
`comparison.preferred_candidate` remains `null`, and your local annotation is not
part of the evidence. See the [saved Decision JSON](examples/portfolio-first-and-ten.decision.json)
and [actual UI screenshot](examples/portfolio-decision.png).

## 3. Decision Lab: keep a thin sample honest

**Question:** What can we say about CAR on exactly third-and-four before week 10?

Keep the Decision settings above, changing before week to **10**, down to **3**,
and both distance bounds to **4**. Rebuild the evidence; do not widen the cohort
because a result looks noisy or inconvenient. The parent sample is **13 plays
across 8 games**.

| Evidence | Run | Pass |
| --- | ---: | ---: |
| Plays / parent plays (frequency) | 3 / 13 (23.1%) | 10 / 13 (76.9%) |
| Games with the candidate | 3 | 7 |
| Observed EPA / missing EPA | 3 / 0 | 10 / 0 |
| EPA per observed play | −0.510 | −0.052 |
| Offensive success | 33.3% | 40.0% |
| Selected EPA interval | Withheld: insufficient games | [−1.556, +1.107] |

Both calls have fewer than the default 30-play warning threshold. Run's EPA
interval is **null**, with `insufficient_games`, three supporting games, 191 valid
and nine undefined bootstrap draws. Frequency instead has eight supporting games:
a game with no Run still informs the frequency denominator. An unavailable EPA
interval is not a zero-width interval and does not make the estimate certain.

The matched baseline has **258 plays / 113 games / 31 other offenses**. Seven
games are shared with CAR, giving a resampling union of **114**, not 121. The
larger baseline cannot replace CAR's small sample. Pass was more frequent and
had less-negative observed EPA here, but no preferred call is returned. See the
[complete sparse-cohort JSON](examples/portfolio-third-and-four.decision.json)
for the baseline, missingness ledgers and all interval states.

## Reproduce the artifacts

Follow [local setup](LOCAL_START.md) first. Exact numerical replay needs the
**original pinned snapshot directory, archive and acquisition manifest** above.
If you do not have those bytes, use the committed aggregate reports and screenshots
to inspect the recorded evidence. You can acquire a currently published snapshot
and run the same queries, but results may change. Do not substitute today's asset,
forge old acquisition metadata or overwrite the reference reports to claim a match.

From the repository root, start the existing launcher with the verified snapshot:

```sh
snapshot_dir=data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06
.venv/local/bin/python scripts/start_local.py \
  --snapshot "$snapshot_dir" \
  --source-label 'nflverse 2024 retrospective snapshot; acquired 2026-09-30 UTC'
```

Use the UI settings above, or request the same evidence through Vite's existing
loopback proxy from another terminal. Commands write only to a temporary replay
directory, not the reference artifacts:

```sh
replay_dir="$(mktemp -d)"
curl --fail --silent --show-error \
  'http://127.0.0.1:5173/api/v1/report?team=CAR&season=2024&before_week=19&compare_league=true&bootstrap_repetitions=1000&bootstrap_seed=20261006' \
  -o "$replay_dir/scout.json"
curl --fail --silent --show-error \
  'http://127.0.0.1:5173/api/v1/decision?team=CAR&season=2024&before_week=19&down=1&distance_min=10&distance_max=10&compare_league=true&bootstrap_repetitions=200&bootstrap_seed=17' \
  -o "$replay_dir/first-ten.json"
curl --fail --silent --show-error \
  'http://127.0.0.1:5173/api/v1/decision?team=CAR&season=2024&before_week=10&down=3&distance_min=4&distance_max=4&compare_league=true&bootstrap_repetitions=200&bootstrap_seed=17' \
  -o "$replay_dir/third-four.json"
.venv/local/bin/python - "$replay_dir" <<'PY_REPLAY'
import json
import sys
from pathlib import Path

replayed = Path(sys.argv[1])
examples = Path('docs/examples')
for actual, expected in [
    ('scout.json', 'car-2024-reg-before-week-19.report.json'),
    ('first-ten.json', 'portfolio-first-and-ten.decision.json'),
    ('third-four.json', 'portfolio-third-and-four.decision.json'),
]:
    assert json.loads((replayed / actual).read_text()) == json.loads((examples / expected).read_text()), actual
    print(f'Matched {actual}')
PY_REPLAY
```

JSON comparison ignores formatting but retains every returned field. The original
Scout reference is pretty-printed; the two new Decision files retain decoded API
response bytes, checked against actual browser downloads. Floating-point rendering
may differ across future runtimes; investigate a mismatch rather than relaxing
expectations to accept it. The independent raw-record audit below uses its explicit
absolute tolerance of `1e-12` and checks counts exactly.

Stop the launcher with Ctrl-C. The existing independent audit can then run offline:

```sh
PYTHONPATH=src .venv/local/bin/python -m validation.decision_audit \
  --snapshot "$snapshot_dir" \
  --check docs/evidence/pbp-2024-23370d5d10f8.decision-audit.json
```

That audit reconciles all 34,902 eligible identities and eight declared situations,
including these two Decision cohorts, directly from raw rows. It checks independent
Decimal point estimates and expanded-game resampling; it does not validate football
causality, EPA's model or nominal coverage. [Audit details](DECISION_AUDIT.md).

On 2026-11-16, the audit receipt replayed exactly; the three API responses matched
the saved artifacts, both Decision browser downloads matched their decoded response
bytes, and the screenshots were visually reviewed. They show the results section
at 1440 × 1100, not the full form or every disclosure. No football conclusions
were added beyond the descriptive comparisons above.

## Optional three-minute demo outline

1. **0:00–0:45:** Open Scout; show the full-season cohort, denominators and league
   context. Explain the exclusive cutoff and retrospective source date.
2. **0:45–1:45:** Switch to first-and-ten in Decision Lab. Read the two samples,
   matching candidate baselines and no-preferred-call state. Mark a call, then
   download the unchanged JSON and inspect its provenance.
3. **1:45–2:30:** Switch to third-and-four before week 10. Explain why Run's
   frequency and EPA have different game support and why bounds are withheld.
4. **2:30–3:00:** Show the shared Python/API/React architecture and independent
   audit, then Ctrl-C to stop both services. State the statistical limitations.

Recording a video is optional. The runnable app, evidence, screenshots and tests
satisfy this local portfolio v1; broader production or modeling work is not required.
