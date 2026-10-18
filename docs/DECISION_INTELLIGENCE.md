# NFL Decision Intelligence — direction and architecture

Decision recorded 2026-10-15. This evolves **the existing repository**, not a new
product implementation. Scout works today; the first offline Decision Lab evidence
contract was implemented on 2026-10-17, with matched candidate league baselines on
2026-10-18. Decision API/UI and new models remain planned.
The repository/CLI/package names and schema-v2 report contract remain unchanged.
See [ROADMAP](../ROADMAP.md) and [STATUS](STATUS.md) for shipped capabilities.

## Two modes, one evidence pipeline

**Scout / Analysis** preserves detailed historical exploration: offense or defense,
exclusive week cutoff, situational filters, tendencies, EPA, success, down/distance
splits, matched league context, uncertainty, missingness, provenance and downloadable
reports/briefs. The current React viewer is this mode, even though its displayed
branding has not yet changed. It is not a head-to-head matchup prediction.

**Play Caller / Decision Lab** will let a user define a situation, choose a supported
call and compare alternatives. Begin with Run versus Pass evidence; no game mechanics
or unsupported playbook concepts. Show why an option appears stronger, not an opaque
score: frequency, outcomes, denominators, games, league differences and uncertainty.
Historical associations are not proof of causal optimality, guaranteed future
performance or a coaching recommendation. Do not display "evidence favors" solely
because one noisy point estimate is larger. Define the comparison/abstention policy
and limitations before adding a winner label. User-provided example numbers are
illustrations, not measurements to ship.

```text
Verified immutable PBP → typed Play/Dataset → situational cohort selection
                                                      ↓
                                      shared metrics/baselines/uncertainty
                                         ↙                         ↘
                             schema-v2 Scout report       future decision comparison
                                         ↓                         ↑
                                 API / CLI / briefs       validated optional layers/models
                                         ↓
                                    React Scout

future decision comparison → future decision API → React Decision Lab
```

`snapshots.py`/`ingestion.py` retain acquisition and hash verification; `pbp.py`
retains eligibility and typed observations. `cohort.py` and `metrics.py`, extracted
for the first offline slice, share selection and metric formulas between `report.py`
and `decision.py`; `uncertainty.py` remains the Scout resampling foundation. Extract
only primitives a tested slice needs; preserve existing report outputs. No second
fetcher, ingestion stack, statistical formulas in React, parallel repository, or
speculative framework.

## First foundation slice and interpretation gates

P1.4's bounded accessibility review is merged. The first **small offline decision
contract** is implemented and tested; see [contract v1](DECISION_CONTRACT.md) for
the request, exact filters, source audit, denominators and availability states.
It always abstains from ranking. Opt-in exact-matched candidate league baselines
now reuse the same selector, candidate summaries and null-preserving differences.
No endpoint/UI/model was added. Next, P1.5 adds candidate support/uncertainty and
comparison rules incrementally through the existing analytics primitives. The gates
below continue to apply; they are not claims that all decision capabilities are implemented.

- Define exact down and inclusive distance bounds (and whether any bucketing is
  allowed) explicitly. Scout still reports observed down/distance buckets; the
  offline decision contract filters on exact down and inclusive distance. Never
  silently widen a sparse cohort to another distance, team, season or time window.
- Retain season/type/exclusive cutoff and offense-relative field position, score,
  period/OT and clock semantics. Define impossible/unsupported situations and missing
  context handling. The current OT filter is a historical period selector, not an
  overtime decision model or rules simulator.
- Audit candidate semantics against eligible `Play.dropback`: sacks/scrambles are
  dropbacks; designed runs are the remaining eligible plays. These are observed
  categories, not a verified record of the huddle's intended call. RPOs and aborted
  plays require particular caution. Do not simply map raw `play_type=run` to Run.
- Frequency denominator: all eligible candidate plays in the selected situation.
  Candidate EPA and success use that candidate's observed EPA, with missing counts;
  success remains EPA > 0. Return both plays and distinct games per candidate.
  An unobserved candidate has zero frequency only when the parent cohort is nonempty;
  its outcome rates are unavailable, not zero. Empty-parent rates are unavailable.
- Apply identical situation/candidate rules to the available, same-role,
  leave-team-out league population. Retain coverage and explicit denominators;
  pooled league context is neither a full-league coverage guarantee nor opponent
  adjustment. No borrowing unmatched baseline cells to manufacture comparisons.
- Specify minimum evidence for each displayed estimate, interval and comparison.
  Keep point-estimate availability separate from insufficient evidence for ranking.
  Existing count flags and bootstrap gates are safeguards, not validated reliability
  thresholds for a new decision method. Test null/unavailable/withheld states and
  candidate-specific game support; keep paired game weights where populations overlap.
- Start with offense decisions. Defense summaries retain offensive production
  **allowed**, with no EPA sign flip or relabeling offensive success as stops.
  Test reciprocal role selection. Opponent-specific history, if later enabled, must
  be separately labeled, supported and temporally matched; it cannot be combined
  with offense history into an invented matchup projection.

Selection bias matters: teams choose different calls for different situations,
personnel and opponents. Restricting observed context does not eliminate unmeasured
confounding. EPA in the source is already a model-derived historical outcome; it is
not our newly validated expected outcome for an unplayed call. A pre-week cutoff
does not prove that the source revision or model existed before that week.

## Separate evidence layers

| Layer | Purpose | Admission gate |
| --- | --- | --- |
| PBP (implemented) | Broad situations, observed run/dropback, EPA/success and pre-play context | Existing immutable manifest, schema/eligibility validation and source audit |
| Charting / participation (deferred) | Directly observed personnel, formation, play-action/RPO/motion when available | Source-specific license, immutable hashes, verified play-ID joins, duplication/missingness/coverage and release-time audit |
| Tracking (deferred) | Player movement, spacing and route/coverage research | Competition-specific rights, coordinate/time semantics, identity joins, validated labels and temporal splits |
| Decision models (deferred) | EP/WP, fourth-down action values, eventually richer ranking | Versioned artifacts/features, task/assumptions, independent parity/error/calibration checks and historically valid inputs |

Missing advanced data stays missing; no fallback to a convenient PBP proxy. Each
supplementary source needs its own immutable manifest, retrieval and upstream
timestamps, archive/decoded hashes, attribution/terms, joins, excluded/unmatched
rows and release-availability evidence. Model manifests additionally need code and
artifact versions/hashes, feature order/encoding, target, training dates and runtime.

## Initial open-source desk review (2026-10-15)

This is a **screening decision**, not completed integration, a full source audit or
independent validation of model outputs. No model/data artifacts were installed,
redistributed or converted. Favor validated reuse/adaptation over needless rebuilding.

### nfl4th — evaluate in P1.6; fourth-down mode remains later

Reviewed upstream commit `aca8c66fee105c1e5355c0daf962f64d4353e42b`:
[MIT license](https://github.com/nflverse/nfl4th/blob/aca8c66fee105c1e5355c0daf962f64d4353e42b/LICENSE.md),
[dependencies](https://github.com/nflverse/nfl4th/blob/aca8c66fee105c1e5355c0daf962f64d4353e42b/DESCRIPTION),
[method/limitations](https://github.com/nflverse/nfl4th/blob/aca8c66fee105c1e5355c0daf962f64d4353e42b/README.md),
[input vignette](https://github.com/nflverse/nfl4th/blob/aca8c66fee105c1e5355c0daf962f64d4353e42b/vignettes/articles/nfl4th.Rmd)
and [WP transformation](https://github.com/nflverse/nfl4th/blob/aca8c66fee105c1e5355c0daf962f64d4353e42b/R/apply_win_prob.R).
It compares go/punt/field-goal outcomes using WP, not Run versus Pass causal effects.
The R/nflfastR/XGBoost/mgcv stack is not a drop-in Python dependency. The user-input
wrapper looks up game context including spread/totals/roof; timeout/kickoff context
is also needed. Our typed dataset omits several inputs. No request-time lookup is
acceptable: independently version any required pre-acquired context.

Upstream documents omissions including kicker/weather specificity and some return/
penalty outcomes. Validate possession/sign changes, time runoff, transition states,
OT/rules-era applicability and action expectations before use. First compare an
offline pinned R reference against independent boundary/example calculations;
only then decide between isolated reference execution, compatible artifact reuse,
or justified Python adaptation. Historical training/artifact availability is not
established by a historical season argument. Preserve MIT notices if reusing code;
software licensing is not blanket permission for all data consumed by wrappers.

### fastrmodels — candidate model artifacts, not a ready decision policy

Reviewed commit `75c7b68bc49535370236c38c9826265da075bd71`:
[MIT license](https://github.com/nflverse/fastrmodels/blob/75c7b68bc49535370236c38c9826265da075bd71/LICENSE.md),
[catalog](https://github.com/nflverse/fastrmodels/blob/75c7b68bc49535370236c38c9826265da075bd71/README.md),
[formats](https://github.com/nflverse/fastrmodels/blob/75c7b68bc49535370236c38c9826265da075bd71/R/data.R)
and [training script](https://github.com/nflverse/fastrmodels/blob/75c7b68bc49535370236c38c9826265da075bd71/data-raw/MODELS.R).
The R package provides EP/WP (with/without spread), completion, expected-pass,
expected-YAC and FG models. Most are raw XGBoost representations; FG is a GAM.
Python compatibility requires audited feature transformations, serialization/runtime
parity and independent golden-vector tests, not merely loading a file. The inspected
WP training script excludes ties and periods above four; that does not establish
validity for our OT filter or current rules. Latest artifacts are not necessarily
historically available models.

The author's [methodology](https://opensourcefootball.com/posts/2020-09-28-nflfastr-ep-wp-and-cp-models/)
describes season-level calibration and distinct feature sets. Completion models
use realized pass context such as air yards and QB hits: these must not become
pretend known inputs to a pre-play call selector. Expected-pass models describe
choice tendency, not which choice is best. Leave-one-season-out evaluation can
include seasons later than the held-out season; it is not our forward-time replay
protocol. Preserve upstream methodology context without claiming its historical
calibration validates a new decision policy, a newer artifact or Python conversion.

### Participation, FTN and tracking — no premature play-family claims

Reuse the completed [personnel/motion audit](PERSONNEL_MOTION.md), including pinned
dictionary evidence and source-specific CC-BY-SA-4.0 terms; do not repeat it as a
new ingestion project. [Participation](https://nflreadr.nflverse.com/articles/dictionary_participation.html)
and [FTN charting](https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html)
offer potential contextual fields. Participation is described from 2016, with
2023+ FTN data released after postseason; charting is described from 2022. Published
availability is not complete coverage or proof of pregame release for a given row.
P1.7 must acquire permitted snapshots and audit keys, cardinality and missingness
against our PBP before exposing any field. Do not inherit PBP's CC-BY-4.0 record.

The NFL's [Big Data Bowl repository](https://github.com/nfl-football-ops/Big-Data-Bowl)
provides a tracking schema, tutorial, one 2017 game and links to official rules.
It is a research starting point, not a blanket license for every competition's
data. Exact competition/dataset terms and redistribution rights remain unresolved
until a specific source is selected. Review those terms before acquisition; no
tracking code/data reuse is approved by this desk review. Python spatial analysis
is feasible in principle, but labels, tracking/PBP ID joins and temporal coverage
must be established first. Public research is methodological reference, not proof
that our own route/coverage labels work.

Inside/outside runs, quick/intermediate/deep passes, screens, play-action and RPO
are only candidates. Inside/outside zone, power, counter, mesh, flood, four verts,
levels and boot remain deferred absent defensible source labels or a validated
classifier. Pass depth/location cannot alone identify a route concept, and
shotgun/no-huddle cannot stand in for motion/personnel. For each future category
require semantics, source rights/provenance, sample adequacy, reproducible tests
and validation/error analysis when classified. Do not populate a menu with guesses.

## Model and AI policy

No LLM for natural-language input, templated explanations, branding or invented
football evidence. Deterministic analytics remain the default. Add learned methods
only for a measurable football task that improves a documented baseline: validated
play-family classification, expected outcomes, action ranking or opponent modeling.
Require a target and decision-time feature list; game/group separation; forward-time
train/validation/test splits; source/model release-time evidence; leakage checks;
baseline comparisons; calibration/error analysis where relevant; and limitations.
Split preprocessing and tuning too, not just rows. Record excluded states and
out-of-domain behavior. Models never invent observed EPA, success, WP or provenance.
EP/WP state values alone do not identify causal action values without a defensible
transition/outcome model and policy-evaluation assumptions.

## Storage decision and clean boundary

**No database now.** One bounded immutable snapshot is verified into memory once;
requests read it, and reports are portable files. There are no demonstrated mutable
user records, multi-snapshot joins or cross-process persistence needs. Retain the
small modular service. Revisit DuckDB for measured local analytical scan/join needs,
or PostgreSQL for demonstrated shared transactional needs, with workload/memory/
latency evidence and an ADR. This is an access-pattern decision, not a scale claim.

The 2026-10-15 run finished P1.4's repeatable synthetic browser/CI flow, not Decision
Lab. The 2026-10-16 [bounded accessibility review](ACCESSIBILITY.md) closes the local
surface boundary, with actual screen-reader/cross-browser coverage still unverified.
Next: begin P1.5 with only the first small offline contract slice. Preserve operational
evidence/case-study goals as P1.10; model/enrichment gates may explicitly defer an
integration so they do not force unvalidated features into the basic decision product.
No deployment, automatic merges or 8 AM automation changes are authorized here.
