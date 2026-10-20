# Pinned Run/Pass reconciliation — 2026-10-20

The offline P1.5 evidence builder passed independent raw-record checks for eight
predeclared retrospective situations in the existing 2024 nflverse snapshot.
This validates selected software calculations, **not** EPA's underlying model,
95% statistical coverage, play-calling intent, causal effects or future performance.
No production analytics, API, frontend, dependency, model or source bytes changed.

## Source and exact replay

The [aggregate receipt](evidence/pbp-2024-23370d5d10f8.decision-audit.json) retains
the original acquisition manifest, source attribution, requests, point estimates,
support examples and verification fingerprints. Inputs are the same immutable
archive acquired on **2026-09-30 UTC**, with upstream update **2026-08-13**:

- Archive SHA-256: `23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06`
- Decoded CSV SHA-256: `6ae564c2c49378ec531303292966caee596982278b9fcdad9c9dd0a0dc16bfa7`
- Attribution: nflverse play-by-play data, [CC BY 4.0 source terms](https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md).
  This artifact derives aggregate audit results; it redistributes no raw rows.
  The manifest's unchanged-archive statement describes the input, not an absence
  of transformations in these derived aggregates.

Rechecked the pinned [nflreadr PBP dictionary](https://github.com/nflverse/nflreadr/blob/dca0b7f6c02f18a4d6e644b03f6d8ec8757d2265/data-raw/dictionary_pbp.csv)
for dropbacks, sacks/scrambles, distance, offense-relative EPA/field position,
pre-play score and quarter clock. Run is non-dropback; Pass includes eligible
scrambles even when raw `play_type` is `run`. No new source or rights assumption.

From the repository root, Python 3.11–3.13, standard library only:

```sh
snapshot_dir=data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06
PYTHONPATH=src python3 -m validation.decision_audit \
  --snapshot "$snapshot_dir" \
  --check docs/evidence/pbp-2024-23370d5d10f8.decision-audit.json
```

JSON is printed only after every check passes. A calculation mismatch exits nonzero
with a field path; nothing replaces the receipt. No downloads, mutable pointer,
fallback snapshot or server. Missing pinned bytes must be restored, not replaced
by today's upstream release. `--check` also compares the original retrieval
receipt exactly: a new acquisition of identical bytes can have a different
timestamp and is not silently relabeled as the saved acquisition.

## Independence and check boundary

`validation/decision_audit.py` is repository-only verification code, excluded from
the installed `src` package and never used for product requests. It reuses existing
bounded snapshot verification and the production CSV adapter, then separately:

1. Enumerates raw eligible identities and matches the exact **34,902-identity** set.
2. Selects raw season/type/exclusive week, offense and exact-context cohorts.
   Both populations' ordered missing/outside/retained ledgers and coverage agree.
3. Uses 50-digit local `Decimal` arithmetic over source strings for pooled
   frequencies, observed-EPA means, EPA > 0 success and selected-minus-league
   differences. No production selector or metric supplies expected values.
4. Expands sampled games into repeated raw rows, not production sufficient totals.
   Both calls/populations share the declared sorted game union, **200 draws,
   seed 17** and documented RNG sequence. Quantiles use Python's separate
   [inclusive interpolation](https://docs.python.org/3.13/library/statistics.html#statistics.quantiles),
   not the production percentile helper.
5. Checks **144** interval entries: support, units, valid/undefined counts, status
   and any bounds, plus literal method/gate metadata, basic cohort identity,
   source fingerprints/manifest and the mandatory no-ranking state.

Counts, nulls, states and flags match exactly; numerical estimates/bounds use
absolute-only tolerance `1e-12`, rejecting non-finite values. The compact receipt
shows candidate points, population coverage, selected EPA intervals and status
totals. Each `reference_sha256` fingerprints the complete declared expected-field
subset using sorted-key JSON; replay recalculates and checks all of it, not just
the visible examples. It is not a hash of the entire production response.
Uncompared presentation text remains covered by existing contract tests.
This is not an exhaustive audit of all queries or independent gamebook completeness.

## Observed results

All requests use season 2024, matched other-offense baselines and
`minimum_plays=30`. Unless noted, type is REG and cutoff is before week 19.
Ranges were fixed **before inspecting outcomes**, not widened for more support.
Counts describe eligible Run/Pass only, not every legal call.

| Case | Selected plays / parent games | Run / Pass plays | League plays / parent games |
| --- | ---: | ---: | ---: |
| CAR 1st & 10, before week 1 | 0 / 0 | 0 / 0 | 0 / 0 |
| CAR 1st & 10, before week 3 | 37 / 2 | 17 / 20 | 1,442 / 32 |
| CAR 1st & 10, full REG cutoff | 387 / 17 | 189 / 198 | 12,666 / 272 |
| CAR 3rd & 4, before week 10 | 13 / 8 | 3 / 10 | 258 / 113 |
| CAR 3rd & 1–4, yards to goal 0–50, score ≤0, Q4 clock 0–300 | 5 / 5 | 1 / 4 | 102 / 86 |
| CAR 2nd & 0–10, OT | 5 / 4 | 3 / 2 | 47 / 14 |
| KC POST 3rd & 1–4, before week 23 | 10 / 3 | 3 / 7 | 110 / 13 |
| CAR POST 1st & 10, before week 23 | 0 / 0 | 0 / 0 | 619 / 13 |

Parent/candidate games overlap; do not sum them as independent observations.
Midseason third-and-four has eight selected and 113 baseline games, seven shared:
the resampling union has **114 games**, not 121.

Across 144 interval entries: **66 `ok`, 48 `insufficient_games`, 30
`undefined_estimate`**. Other states are covered synthetically, not invented in real
observations. Early CAR first-and-ten has 34/200 undefined selected draws; its
two-game support takes precedence and bounds stay withheld. Late close-range
frequency has five parent support games, but Run EPA has one and Pass EPA four.
A league sample cannot supply missing team evidence.

Full-season CAR first-and-ten Run EPA/play is about **0.047879**, Pass **0.022208**.
Exploratory selected intervals are approximately **[-0.057345, 0.149851]** and
**[-0.106741, 0.130660]**, respectively; both have 17 support games and a few-games
warning. These are reconciliation examples, **not** a Run-versus-Pass test or
recommendation. Every production comparison retains `preferred_candidate: null`.

## Verification and limits

Exact receipt replay passed on Python 3.11/3.12/3.13 with networking blocked.
Synthetic tests include hand calculations, zero/missing EPA, observed dropback
semantics, exclusions, temporal/exact-context boundaries, support states, RNG/
decimal isolation, source mismatch and deliberate production-result mutations.
Altered points, support, bounds, ledgers, method/cohort identity, ranking or source
hashes must fail. Core CI uses invented inputs only; no real data download.

The pinned eligible rows have no missing EPA or active optional context, so this
audit cannot empirically validate those missingness branches; synthetic tests do.
Two hundred draws check implementation parity, not Monte Carlo precision or
calibrated coverage. Matching this source/procedure does not validate annotations,
upstream EPA, intended calls, causal effects, cross-game dependence or selection
bias. A 2026 retrieval is not proof of information availability in 2024.

Next: document justified comparison/abstention and opponent-evidence policy.
Keep ranking withheld and opponent adjustment deferred unless defensible;
no decision API/UI/model is introduced by this audit.
