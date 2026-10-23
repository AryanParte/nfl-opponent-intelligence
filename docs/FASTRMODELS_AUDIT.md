# fastrmodels EP/WP integration gate

Reviewed 2026-10-23. **Defer runtime integration; retain EP/WP artifacts as reuse
candidates.** This is P1.6's bounded source/interface audit, following the
[nfl4th audit](NFL4TH_AUDIT.md), not a new model, prediction service or validation
of football decisions. No binaries, R runtime or additional dataset were acquired,
executed, converted or redistributed. Scout and descriptive Run/Pass stay intact.

The [receipt](evidence/fastrmodels-2.1.0-interface-audit.json) is an offline audit
record, **not an adapter or acquisition manifest**. It records two source pins,
fifteen source-file identities, wrapper inputs, ordered model features, output
semantics and metadata for three EP/WP artifacts. The inspected runtime scope is
the standalone calculators, their selectors, feature mutations and model loader;
it is not a full review or port of the PBP builder.

## Pin the artifacts and their consumer separately

| Role | Resolved release commit | Root tree | Release date |
| --- | --- | --- | --- |
| fastrmodels 2.1.0 | `ca185baf7757c2992e57ce2bdf2f296c515465d8` | `75424601cec99d5cd4ecd636ac6a819efe91a2eb` | 2026-02-07 |
| nflfastR 6.0.0 | `917b14e5085f352d9b00d23628759773e7d411b5` | `71b6133789a8a6adfb0e5960991040abd32a0979` | 2026-09-18 |

The Git ref and Git commit endpoints resolved these identities; release metadata
alone is insufficient. See [fastrmodels release][fm-release] and
[nflfastR release][nf-release]. The earlier architecture review's fastrmodels
commit is retained as historical context; its tree matches this release tree.
This does not prove that present binaries were available for a historical game.

[fastrmodels][catalog] is a data package, not the feature-preparation engine.
Its [declaration][fm-description] requires R >= 4.1 and XGBoost >= 1.1, not an
exact runtime lock. [nflfastR's declaration][nf-description] requires fastrmodels
>= 2.1.0 and includes R transformation dependencies; those lower bounds do not
certify every possible R/Python combination. [The loader][loader] selects the
installed package object and passes raw vectors to `xgb.load.raw`; this inspected
inference path does not perform nfl4th-style request-time asset downloads.
Installation/acquisition must still be separate from our API and explicitly pinned.

## Targets and interface: state value is not call value

| Artifact | Target / output | Not established by that output |
| --- | --- | --- |
| `ep_model` | Seven next-scoring-event probabilities for this half; offense-relative EP | EPA for an unplayed call, Run/Pass ranking, causal action value |
| `wp_model` | Possession-team win probability without a spread feature | Tie-aware outcome probabilities, OT-state validity, action-specific WP |
| `wp_model_spread` | Possession-team WP with a time-decayed offense-relative pregame spread | Opponent-adjusted Run/Pass recommendation or historically available market information |

The checked-in [training recipe][training] labels EP as own/opponent TD, FG,
safety or no score; WP labels whether possession team equals the winner, excluding
tied outcomes and rows with `qtr > 4`. That excludes OT **states**, not necessarily
games later decided in OT. Exact artifact training windows remain unverified.

The [standalone calculators][calculators] assign EP probability columns in order:
`td_prob`, `opp_td_prob`, `fg_prob`, `opp_fg_prob`, `safety_prob`,
`opp_safety_prob`, `no_score_prob`. Their point weights are respectively
`7, -7, 3, -3, 2, -2, 0`. The fixed seven-point TD convention is not a fresh
PAT/two-point estimate. WP returns `wp` and `vegas_wp` on the 0–1 scale, not
percentage points. Neither calculator returns an action uncertainty interval.
The EP wrapper handles vector versus matrix predictions differently; row order,
class order and multi-row batching require parity checks before translation.

### Raw wrapper inputs versus current typed Play

EP requires ten raw columns; the combined WP wrapper requires twelve, even though
the no-spread model itself does not use a spread. Their union contains fourteen:

| Input(s) | Current typed evidence | Required decision before adaptation |
| --- | --- | --- |
| `season`, `posteam`, `down`, `ydstogo` | `season`, `offense`, `down`, `yards_to_go` present | Exact game state and canonical team semantics, not cohort ranges |
| `yardline_100`, `score_differential` | Nullable fields | Missing must remain unavailable; score is pre-play offense minus defense |
| `half_seconds_remaining`, `game_seconds_remaining` | Not retained directly; nullable `qtr` and quarter clock exist | Define/test regulation-only derivation and half/end boundaries; no OT substitution |
| `home_team`, `roof` | Not retained | Verified venue/home and roof source, no inference from offense or arbitrary defaults |
| `posteam_timeouts_remaining`, `defteam_timeouts_remaining` | Not retained | Verified pre-play counts, not assumed zero/three |
| `receive_2h_ko` | Not retained | Verified receiving-team context; caller-supplied bit in standalone WP |
| `spread_line` | Not retained | Home-favorite convention plus source timestamp; no fabricated market value |

Four union inputs are present, two nullable, two require a new validated
derivation, and six are absent. This is about typed `Play`, **not a claim of
absence from the full raw CSV**. No new raw-column/missingness audit occurred.
`DecisionRequest` supplies cohort ranges and an exclusive historical week cutoff,
not missing game-state context. Observed `epa` and `dropback` are not EP/WP
features; using their realized values to rank an unplayed call would change the
task and can introduce leakage.

### Feature transformations and path-specific assumptions

The receipt freezes the [selectors'][selectors] exact 18 EP, 11 WP and 12
spread-WP column orders. EP expands season into five eras and down into four
indicators, plus home and roof flags. [Feature mutation][mutations] codes missing,
open or closed roofs as retractable and puts every season after 2017 in one era.
These are upstream assumptions, not verified roof observations or validation for
every newer rules era. Reject unsupported/missing context in our eventual adapter
unless a separately justified policy explicitly admits it.

WP derives the home indicator, offense-relative spread, elapsed-game fraction,
decaying `spread_time` and time-scaled score differential (its magnitude grows;
a negative differential becomes more negative). The standalone wrapper
expects clocks and `receive_2h_ko`; it does **not** call `prepare_wp_data()`.
That separate helper can substitute a missing spread with 1.5 and infer kickoff
context from the game sequence. Do not accidentally import those behaviors into
a pre-play request. Likewise, bulk `get_preds()` can neutralize the EP home flag
when `location == Neutral`, but the standalone EP calculator calls the selector
directly. A reference experiment must name the entry point and cover this
difference; neither path is automatically a ground-truth venue interpretation.

## Artifact format, provenance and license boundary

The [catalog declarations][formats] describe six raw-vector XGBoost objects and
one FG GAM. The [serialization recipe][serialization] loads archive UBJ files,
re-exports raw UBJ vectors and stores them in compressed R `.rda` containers.
[Version notes][news] explicitly describe re-saving for XGBoost v3 compatibility.
Renaming `.rda` to `.ubj` is not conversion; packaged raw vectors and archive files
must not be called byte-identical based on their names or similar sizes.

The [archive API][archive] listed these assets on the audit date. All three
advertised digests were null, and **no bytes were downloaded or locally hashed**:

| Artifact | Package `.rda` size | Archive UBJ ID / size | Archive created |
| --- | ---: | --- | --- |
| EP | 2,864,452 | `253928625` / 9,737,452 | 2025-05-12 |
| WP | 26,776 | `253928623` / 106,951 | 2025-05-12 |
| Spread WP | 354,988 | `253928620` / 1,219,887 | 2025-05-12 |

The receipt preserves Git blob IDs for package files, asset IDs/dates and null
local SHA-256 values. A missing digest is unknown, not a hash mismatch, zero hash
or permission to claim verification. Future acquisition needs trusted provenance,
an explicitly reviewed source/asset identity, actual byte hashes and immutable
storage; a self-computed hash proves the acquired bytes' identity, not authorship
or training quality. These observed uploads do not establish first publication
of an equivalent model or row-level historical availability.

[XGBoost's model-IO documentation][xgb-io] distinguishes portable model formats
from unstable language memory snapshots. Direct UBJ reuse is a plausible Python
route, but feature order, raw-vector packaging, version behavior and predictions
still need independent checks. No unsafe pickle loader or automatic converter is
introduced. FG's GAM is a separate runtime problem, outside this EP/WP audit.

Both projects state MIT terms: [fastrmodels notice][fm-license] credits Sebastian
Carl and Ben Baldwin (2021), [nflfastR notice][nf-license] credits them (2020).
Retain notices/conditions for any substantial reuse. Those package statements
do not establish rights or historical availability for separately sourced training
data, market lines or future enrichments. Record the selected artifact's license
association and dependency notices before acquisition/redistribution. This audit
does not change our license or claim blanket data/legal clearance.

## Training evidence is not an artifact lineage certificate

The [training script][training] reads EP calibration data from a relative local
path and WP data from a mutable external URL; it sources helper paths from a
separate code context. Neither supplies a pinned training-data manifest or an
explicit final EP/WP season window. EP training weights use drive distance to the
next score and score margin. Future-derived labels/weights are training-only, not
known pre-decision evidence. Score differential itself is pre-play context used
by WP, but not an EP inference feature. The serialization recipe
reuses existing models; a serialization date does not imply retraining.

The authors' [methodology article][method] reports leave-one-season-out calibration
over historical seasons and season-grouped tuning. That is useful methodological
evidence, not an evaluation of these exact artifacts, our Python runtime or a new
decision policy. Holding out one season while training on other, possibly later
seasons differs from forward-time replay. We did not reproduce its results.
Exact binary training lineage, cutoff-time model/feature availability, modern-era
error and calibration remain unresolved. [Package tests][fm-tests] checking raw types/lengths
and [example calculator snapshots][upstream-tests] do not close those gaps.

CP, xYAC, xPass and FG remain deferred, not ignored competitors to EP/WP. Realized
pass context in CP/xYAC is not pre-call information; expected pass frequency is
not the best call. No unsupported play-family classification or action-ranking
model is implied by this catalog.

## Reuse / adapt / defer and the next bounded unit

- **Reuse candidate:** EP/WP artifacts and documented methodology, rather than
  retraining mature models without a measured reason. EP-only reference work is
  a smaller first experiment than simultaneous WP, spread and fourth-down support.
- **Adapt candidate:** exact Python transformations plus native UBJ inference,
  compared with an isolated pinned R reference. R retains upstream semantics but
  adds a runtime; Python reduces serving-runtime breadth but takes on transformation,
  packaging and parity maintenance. Neither cost nor latency was benchmarked here.
- **Defer production:** no validated context adapter, acquired/pinned bytes,
  reference parity, temporal validation or calibration. State EP/WP still need a
  defensible action-transition model before producing action values. Keep the
  existing preferred-call field null; no model dependency enters the core/API.

**Next P1.6 unit:** decide the smallest EP-only offline reference strategy using
these two audits: isolated R, direct UBJ/Python reuse or explicit deferral. Record
the terms/acquisition/runtime plan, independent golden-vector protocol and exit
criteria before installing/converting artifacts. Test protocols must cover era
edges, home/away/neutral context, roof missingness, down encoding, field/clock/
half boundaries, timeouts, multi-row class order and unsupported OT. Separate
parity from model quality; later validation needs temporal splits, baselines,
calibration/error analysis and release-time evidence. Do not bundle WP, data
enrichment, API/UI or fourth-down mode into that next unit.

## Offline checks and their limits

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p test_fastrmodels_audit.py -v
```

Tests guard the recorded input mappings against actual typed Play, ordered feature
and output inventories, distinct commit/tree pins, link coverage, absent hashes
and deferred admission. They use no network or optional dependency and do not
execute upstream models, attest binary contents or certify any probability.
Full local verification and remote CI are recorded in [STATUS](STATUS.md) and PR.

[fm-release]: https://api.github.com/repos/nflverse/fastrmodels/releases/tags/v2.1.0
[nf-release]: https://api.github.com/repos/nflverse/nflfastR/releases/tags/v6.0.0
[catalog]: https://github.com/nflverse/fastrmodels/blob/ca185baf7757c2992e57ce2bdf2f296c515465d8/README.md
[fm-description]: https://github.com/nflverse/fastrmodels/blob/ca185baf7757c2992e57ce2bdf2f296c515465d8/DESCRIPTION
[nf-description]: https://github.com/nflverse/nflfastR/blob/917b14e5085f352d9b00d23628759773e7d411b5/DESCRIPTION
[loader]: https://github.com/nflverse/nflfastR/blob/917b14e5085f352d9b00d23628759773e7d411b5/R/utils.R#L236-L256
[training]: https://github.com/nflverse/fastrmodels/blob/ca185baf7757c2992e57ce2bdf2f296c515465d8/data-raw/MODELS.R
[calculators]: https://github.com/nflverse/nflfastR/blob/917b14e5085f352d9b00d23628759773e7d411b5/R/ep_wp_calculators.R
[selectors]: https://github.com/nflverse/nflfastR/blob/917b14e5085f352d9b00d23628759773e7d411b5/R/helper_add_ep_wp.R#L93-L264
[mutations]: https://github.com/nflverse/nflfastR/blob/917b14e5085f352d9b00d23628759773e7d411b5/R/helper_add_nflscrapr_mutations.R#L760-L794
[formats]: https://github.com/nflverse/fastrmodels/blob/ca185baf7757c2992e57ce2bdf2f296c515465d8/R/data.R
[serialization]: https://github.com/nflverse/fastrmodels/blob/ca185baf7757c2992e57ce2bdf2f296c515465d8/data-raw/DATASET.R
[news]: https://github.com/nflverse/fastrmodels/blob/ca185baf7757c2992e57ce2bdf2f296c515465d8/NEWS.md
[archive]: https://api.github.com/repos/nflverse/fastrmodels/releases/tags/model_archive
[xgb-io]: https://xgboost.readthedocs.io/en/stable/tutorials/saving_model.html
[fm-license]: https://github.com/nflverse/fastrmodels/blob/ca185baf7757c2992e57ce2bdf2f296c515465d8/LICENSE.md
[nf-license]: https://github.com/nflverse/nflfastR/blob/917b14e5085f352d9b00d23628759773e7d411b5/LICENSE.md
[method]: https://opensourcefootball.com/posts/2020-09-28-nflfastr-ep-wp-and-cp-models/
[upstream-tests]: https://github.com/nflverse/nflfastR/blob/917b14e5085f352d9b00d23628759773e7d411b5/tests/testthat/test-ep_wp_calculators.R
[fm-tests]: https://github.com/nflverse/fastrmodels/blob/ca185baf7757c2992e57ce2bdf2f296c515465d8/tests/testthat/test-models.R
