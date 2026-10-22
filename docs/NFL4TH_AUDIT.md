# nfl4th integration gate — source/interface audit

Reviewed 2026-10-22. **Defer runtime integration.** Reuse nfl4th as a methodological
reference for a later **go / punt / field-goal** mode; it does not provide Run vs
Pass action values. Scout and the descriptive-only Decision Lab contract remain
unchanged. This completes the first P1.6 audit, not P1.6 model validation.

The [machine-readable receipt](evidence/nfl4th-1.0.7-interface-audit.json) records
source identities, current Python field mappings and observed asset metadata.
It is an audit record, **not an executable adapter or acquisition manifest**.
No R, third-party code, model binaries or additional football data were installed,
converted or redistributed. No predictions, parity or calibration were tested.

## Version and terms boundary

The audit pins the currently resolved `v1.0.7` commit
`00bc3573f7e740244dc5dcbc7588f31dbd56254d`, not a branch or version string alone.
The [release][release] was published 2026-03-25; its API `target_commitish` is
`886c61a329be47f3bb294e1a5ab65806cf4db39f`, different from the
[resolved tag][tag]. Preserve that distinction rather than claiming identical
identities. The receipt stores the resolved tree and GitHub-reported source blob
IDs. These identify inspected text; they are not local binary SHA-256 verification.
The earlier [October 15 desk review](DECISION_INTELLIGENCE.md) retains its original
pin. Every source file listed in this receipt has the same blob ID at that earlier
pin; the complete repository trees are not claimed identical.

The [package declaration][description] requires R >= 4.1 and nflfastR >= 5.2.0,
plus dependencies including XGBoost, mgcv, nflreadr and dplyr, without an exact
runtime lock. The [MIT notice][license] names Ben Baldwin (2021); preserve its
notice/conditions if reusing code. This establishes the package's stated terms,
not blanket clearance for schedule data, market inputs, training data or separately
downloaded assets. Asset-specific provenance/terms and transitive dependency
notices remain a gate before redistribution or integration. Existing PBP terms
and manifests remain untouched. This is an engineering admission decision, not
legal clearance.

## Input compatibility: a cohort is not a game state

The upstream [manual example][example] has thirteen inputs. Our current typed
`Play` can supply some, but `DecisionRequest` describes a historical cohort, not
a fully specified upcoming game. “Missing” below means **absent from the typed
contract**, not proven absent from the original raw CSV. No new raw-column audit
was performed.

| nfl4th manual input | Existing typed `Play` | Admission requirement |
| --- | --- | --- |
| `home_team`, `away_team` | Not retained | Do not equate offense/defense to home/away or parse a game ID as verified venue context |
| `posteam` | `offense` | Validate team alias normalization and membership in the game |
| `type` | `season_type` | Explicit `REG -> reg`, `POST -> post`; unknown values must fail |
| `season` | `season` | A matching schedule entry is required; year alone does not validate a rules era |
| `qtr`, `quarter_seconds_remaining` | Same names, nullable | Require an exact regulation state; no default for missing time, no OT claim |
| `ydstogo` | `yards_to_go` | One distance, not an inclusive cohort range |
| `yardline_100` | Same name, nullable float | Offense-relative; discrete punt-table lookup needs a documented fractional/edge policy |
| `score_differential` | Same name, nullable | Pre-play offense-relative score, not final margin |
| `home_opening_kickoff` | Not retained | Verify kickoff/second-half possession coding, never invent it |
| `posteam_timeouts_remaining`, `defteam_timeouts_remaining` | Not retained | Verified pre-play counts; missing is not zero or three |

Five inputs are absent, four are nullable, four are present but still require
semantic validation. These are **not** thirteen production-ready fields.
`before_week` is an exclusive history cutoff, not a schedule-game identifier.
Our clock/score/yardline ranges cannot be collapsed to midpoints without a new,
validated estimand. Neither opponent conditioning nor kickoff/timeouts are part of
`DecisionRequest` today. The core eligibility policy retains run/dropback plays,
not the full punt/FG decision universe; its frequencies cannot become fourth-down
action probabilities.

### Hidden context and entry-path differences

In [the wrapper][wrapper], supplying `type` bypasses the nflfastR-shaped cleaning
path. That cleaning path keeps fourth downs, regulation (`qtr <= 4`) and plays
with more than 15 game seconds left; the manual path does not apply those same
filters. Missing `runoff` defaults to zero. The wrapper returns original rows
with ten joined model outputs; it is not input validation for our API.

[Preparation][helpers] forces `down=4`, removes supplied schedule-derived fields
and rejoins a cached schedule by home team, away team, type and season—not game ID
or week. Supplying our own spread/roof columns would not bypass that lookup.
Before any adapter: enforce down/time support, exactly one matching game,
complete context, canonical team aliases and no accidental row multiplication.
These are proposed safety checks, not claims that an actual schedule collision
was measured. Schedule rows derive market totals/spreads, roof categories and
era flags. Clock and second-half possession transformations are also model inputs.
Never infer decision-time availability from a retrospective schedule's presence.

## Outputs and modeling assumptions

| Output | Meaning / unit |
| --- | --- |
| `first_down_prob` | Modeled conversion probability, not EPA-based success rate |
| `wp_succeed`, `wp_fail` | Conditional WP after go succeeds/fails |
| `go_wp`, `punt_wp`, `fg_wp` | Expected WP for the original possession team under each action |
| `fg_make_prob` | Modeled field-goal make probability |
| `make_fg_wp`, `miss_fg_wp` | Conditional WP after a make/miss |
| `go_boost` | 100 × (go WP − best non-go WP), in percentage points |

Probabilities use the 0–1 scale, not EPA units. [The wrapper][wrapper] substitutes
zero for unavailable punt WP when computing the non-go maximum; do not silently
copy that into an API's unavailable-action semantics. No output is a Run/Pass
ranking or an uncertainty interval. Conditional `wp_succeed` is not a guarantee.

[Action construction][actions] weights hypothetical states: the go model uses
76 gain categories (−10 through 65), collapsing goal-crossing gains to touchdowns;
punt outcomes come from a field-position table; field goals combine make/miss WP.
Go includes a downstream two-point/PAT calculation. State transitions change
possession, score, distance and time; assumed six-second play duration, optional
successful-go runoff, 25-yard-line post-score possession and kneel-out heuristics
need rules-era and boundary tests. These are source assumptions, not newly
validated football rules. No Run/Pass selector conditions this go distribution.

[WP calculation][wp] recomputes EP for hypothetical states, then averages a custom
home-team WP model with nflfastR's possession-team WP after normalizing both to
the original offense. A Python port must match feature order, encoding and sign
changes, not merely load XGBoost bytes. The source selection lists
`home_timeouts_remaining` twice: resolve actual dplyr/runtime behavior and expected
model features in reference tests before porting. This observation alone is not
proof of an upstream prediction defect. Existing observed EPA must not substitute
for the hypothetical-state EP/WP computation.

The upstream [limitations][readme] include omitted go turnover returns, no
punter/returner-specific punt estimates and no kicker/weather-specific FG estimates,
plus omitted return/penalty outcomes. Our supported-scope decision therefore
remains conservative: no team-specific coaching advice, OT/current-rule guarantee,
causal optimum, guaranteed performance or independent validation claim.

## Dependencies outside the package pin

| Dependency | Source behavior | Required admission evidence |
| --- | --- | --- |
| Schedule | `nflreadr::load_schedules()`, cached separately | Permitted immutable snapshot, hashes, game-key/cardinality/missingness audit and pre-decision release evidence |
| Go and home-WP models | `model_archive/fd_model.rds`, `wp_model.rds` downloaded on a cache miss | Exact asset bytes/digests, serialization/runtime, feature schema, terms and training lineage |
| FG, punt and two-point components | Bundled `R/sysdata.rda`; build script downloads a two-point artifact | Pin built package contents and component lineage; source scripts alone do not attest binary training inputs |
| nflfastR EP/WP | Dependency calls during hypothetical-state evaluation | Separate pinned model/runtime evaluation; the next fastrmodels unit is not skipped |
| Precomputed boost | Mutable release asset joined to PBP by game/play IDs in the fast loader | Separate verified receipt, provenance/coverage/join audit; never assume historical availability |

Sources: [cache implementation][cache], [load-time cache policy][startup],
[model/schedule loaders][helpers], [bundled-data build][build],
[fast wrapper][wrapper] and [precompute writer][precompute]. Schedule cache can
be removed on package load unless retention is configured. Model caches use
unversioned filenames and raw-format checks, not content hashes: two machines
with the same package can retain different assets. No wrapper download or cache
mutation may run inside our request handler. A future model layer must consume
explicitly pre-acquired, verified local inputs or report unavailable.

### Observed asset metadata, not downloaded bytes

The receipt records IDs, sizes, API-advertised SHA-256 digests and timestamps for
five relevant assets. All `local_sha256` values are null. The
[model archive][archive] lists `fd_model.rds` (9,107,324 bytes), `wp_model.rds`
(2,422,111 bytes), and build-time `two_pt_model.ubj` (25,193 bytes), created
2026-02-04. [Infrastructure metadata][infrastructure] lists the combined boost
asset created 2026-10-22 and the 2024-season asset created 2025-09-03. A release's
older publication date does not date every later asset or its contents. Asset
timestamps establish these observed uploads, not original model publication,
training cutoffs, per-row availability or the existence of an equivalent model
before an old game. No local digest has been substituted with an advertised one.

## Training and historical availability: unresolved lineage

The checked-in [go/two-point training script][go-training] selects 2014–2019
third/fourth-down data for go and 2010–2019 data for two-point models, with
`week <= 17`. It recodes first-down penalties into gains and clips gain labels.
Its five-fold XGBoost CV is not an explicit temporal holdout; no historical
generalization or calibration conclusion follows from it here. The
[punt/FG script][kick-training] uses 2010–2019 punts but a runtime-current-season
upper bound for FG training. Source dates alone do not tell us when the bundled
FG bytes were trained.

Crucially, the [archive conversion script][conversion] obtains go/home-WP models
from a different repository's mutable paths and changes serialization for
compatibility. It does not establish that the inspected training scripts generated
the release assets above. Home-WP training lineage and all exact binary training
windows remain unverified in this bounded audit. Do not relabel script windows
as verified artifact windows. Dependency EP/WP lineage is a separate missing link.
Historical “as-of” validation needs both training cutoffs and time-stamped feature
availability, especially market lines and revised schedules. A current model used
on old plays is retrospective analysis unless those gates are met.

## Reuse / adapt / defer decision and next experiment

- **Reuse as reference:** action-state enumeration and original-offense WP
  interpretation for a later fourth-down mode, with the documented limitations.
- **Adapt only after evidence:** compare an isolated, fully pinned offline R
  reference with independently hand-checked state transitions and golden vectors.
  Native Python XGBoost reuse may avoid retraining but still needs encoding/parity;
  mgcv and R transformations prevent claiming a drop-in Python port. No option
  is selected or implemented yet; no mature model is rebuilt just to avoid R.
- **Defer runtime/model integration:** missing typed context, separate mutable
  assets, incomplete terms/lineage, no temporal validation/calibration and no
  independent reference outputs. Preserve the null preferred-call policy.

After the separate **fastrmodels audit**, decide whether a small acquisition and
offline R-reference experiment is justified. It must lock allowed assets and
runtime versions, independently verify hashes, and test home/away possession,
turnovers/TDs, first-down/goal-line states, missing punt support, quarter/half/end
boundaries, timeout/runoff assumptions, all output units and unavailable cases.
OT remains rejected until explicitly supported. Then compare baseline/error/
calibration results with season-separated validation; parity alone is not model
quality or causal validation. No API/UI integration is part of this audit.

## Offline regression checks and limits

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -p test_nfl4th_audit.py -v
```

These tests check the receipt against the actual `Play`/`DecisionRequest` fields
and nullable annotations, its source pin/link identities, interface inventory,
metadata-versus-verified-hash distinction and deferred state. A changed contract
requires a deliberate re-audit, not automatic field mapping. The tests need no
network or optional dependency. They **do not** execute upstream code, attest
remote contents or validate a single probability. Full project regressions and
publication evidence belong in [STATUS](STATUS.md) and the PR.

[release]: https://api.github.com/repos/nflverse/nfl4th/releases/tags/v1.0.7
[tag]: https://api.github.com/repos/nflverse/nfl4th/git/ref/tags/v1.0.7
[description]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/DESCRIPTION
[license]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/LICENSE.md
[example]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/tests/testthat/test-wrapper.R
[wrapper]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/R/wrapper.R
[helpers]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/R/helpers.R
[actions]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/R/decision_functions.R
[wp]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/R/apply_win_prob.R
[readme]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/README.md
[cache]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/R/cache.R
[startup]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/R/zzz.R
[build]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/data-raw/build_sysdata.R
[precompute]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/data-raw/_save_computed_numbers.R
[archive]: https://api.github.com/repos/nflverse/nfl4th/releases/tags/model_archive
[infrastructure]: https://api.github.com/repos/nflverse/nfl4th/releases/tags/nfl4th_infrastructure
[go-training]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/data-raw/_go_for_it_and_2pt_models.R
[kick-training]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/data-raw/_punt_and_fg_models.R
[conversion]: https://github.com/nflverse/nfl4th/blob/00bc3573f7e740244dc5dcbc7588f31dbd56254d/data-raw/model_archive.R
