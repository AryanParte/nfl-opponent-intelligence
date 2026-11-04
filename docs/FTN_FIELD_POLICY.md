# FTN field admission decision

Decision date: **2026-11-03**. Scope: the single pinned 2024 FTN/PBP snapshot pair
and the existing Scout / offline Run-vs-Pass product. **All 22 contextual FTN
fields remain audit-only. None is admitted to serving, feature rates, call-family
classification, candidate ranking or model features.** This closes P1.7's first
artifact admission review with an explicit defer decision; the next unit is
P1.8's PBP-only Decision API. It is not an indefinite dependency on more charting.

This decision preserves the acquired sources, tested join and useful descriptive
audit evidence. It does not say these fields can never be used. The narrower
claim is that this review has not established the measurement/denominator contract
needed to expose them honestly in this product. No second pipeline or unused
runtime policy engine is added to enforce a capability the product does not offer.

## Evidence considered

- [Artifact/terms audit](FTN_CHARTING_AUDIT.md): separately hashed FTN CSV and
  source notices; CC BY-SA 4.0, distinct from PBP's CC BY 4.0.
- [Join/coverage audit](FTN_COVERAGE.md): all 34,902 eligible PBP plays match once;
  268 unknown QB locations, 264 unknown hashes and one out-of-range pass-rusher
  value. Complete joins and syntactically recognized fields are not applicability.
- The [pinned nflreadr dictionary][dictionary], rechecked against the [current
  official dictionary][live], documents what the fields are intended to describe.
  It does not supply a row-level applicable/observed mask or resolve the zero codes.
- The [pinned producer transformation][producer] preserves empty-to-NA and converts
  flags through integer/logical representations; it does not establish that every
  FALSE in the released file means an observed negative. The producer-linked FTN
  Google document could not be retrieved in this run and was not used as evidence.
  No credentialed endpoint or new dataset was accessed.

The existing [coverage receipt][receipt] illustrates why applicability matters:

| Raw encoding in eligible PBP cohort | Run (13,872 plays) | Pass/dropback (21,030 plays) |
| --- | ---: | ---: |
| RPO literal TRUE | 888 | 373 |
| Motion literal TRUE | 6,760 | 10,472 |
| Play-action literal FALSE | 13,872 | 16,253 |
| Screen-pass literal FALSE | 13,872 | 19,145 |
| Recognized `read_thrown` code | 13,872 | 21,030 |

These are **encoding counts, not approved feature frequencies or call-family
labels**. RPO appears in both observed Run and Pass, so it cannot replace their
exclusive `qb_dropback` partition. A documented read code on every Run does not
prove a pass progression occurred. FALSE on a Run can be consistent with a feature
being non-applicable; that alone does not prove a valid negative observation.
No cross-feature independence, exclusivity, accuracy or causal claim follows.

FTN-derived counts here retain **FTN Data via nflverse** attribution under
[CC BY-SA 4.0][sa], with **nflverse play-by-play data** under [CC BY 4.0][by].
Modification: selected aggregate encoding counts from the existing joined receipt;
no row-level redistribution. Original manifests, hashes, notices and retrieval
times remain unchanged. No endorsement or clearance of future enriched exports
is implied. Software licensing remains separate.

## Field-by-field decisions

Every row below is **defer serving; retain raw audit evidence**. A candidate
denominator is a proposed population to investigate, not an approved denominator.
Observed Run/Pass means the existing dropback policy, not verified intended calls.

| Field | Meaning / possible population | Evidence required before reconsideration |
| --- | --- | --- |
| `starting_hash` | Ball hash; eligible scrimmage plays | Normalize only L/M/R; preserve undocumented 0 as unknown. Validate observation/applicability and coverage before a hash-conditioned cohort. |
| `qb_location` | QB position before snap; eligible plays | U/S/P describe QB alignment, not the entire formation. Resolve unknown/non-applicable handling and validate coded observations; never fill from PBP shotgun. |
| `n_offense_backfield` | Players in backfield at snap | Define treatment of QB and missing/default zero. A count is not RB/TE/WR personnel or a run family. |
| `n_defense_box` | Defenders in box at snap | Validate the charted box definition and zero/default/applicability handling. Counts within 0–11 alone are insufficient. |
| `is_no_huddle` | Huddle behavior | Establish observed true/false coverage and timing semantics. Do not silently substitute PBP no-huddle or use it as motion. |
| `is_motion` | Movement before or at snap | Validate positive/negative observation mask over eligible plays. This does not identify the mover, motion path or at-snap-only motion. |
| `is_play_action` | Charted play-action pass | Specify intended-versus-executed pass/dropback scope, sacks/scrambles and observed negatives. Run FALSE is not automatically an observed non-play-action event. |
| `is_screen_pass` | Charted screen pass | Define call/throw/dropback scope and aborted/sack cases. Short air yards or pass location is not a screen label. |
| `is_rpo` | Charted run-pass option | Validate observation mask for both candidates, handoff/throw treatment and overlap with other flags. Do not relabel RPO as an exclusive third candidate. |
| `is_trick_play` | Charted trick play | Establish operational definition, eligible events and positive/negative charting validation. |
| `is_qb_out_of_pocket` | QB movement during play | Define opportunities and observation mask. This is realized behavior, not an automatically available pre-call feature. |
| `is_interception_worthy` | Charted pass assessment | Define eligible throws and assessment criteria, charting validation and negative observations; not all dropbacks. |
| `is_throw_away` | Charted throwaway | Identify actual throw opportunities and non-throw handling; do not treat all Run/sack FALSE as observed throwaway negatives. |
| `read_thrown` | Throw progression/read category | Validate actual-throw applicability. The 2023+ primary-read code 0 must not become missing, or a real read on a non-throw. Retain year-specific semantics. |
| `is_catchable_ball` | Charted catchability | Define eligible pass opportunities and defended/uncatchable/non-target handling; do not infer from completion alone. |
| `is_contested_ball` | Contact around catch opportunity | Establish the charting opportunity definition and observed negatives; neither every dropback nor every completion is automatically the denominator. |
| `is_created_reception` | Exceptional reception assessment | Validate reception/opportunity scope and subjective classification; do not use all Pass as the denominator. |
| `is_drop` | Charted receiver drop | Define catchable opportunities and observed negatives; an incomplete pass is not a drop proxy. |
| `is_qb_sneak` | Charted QB sneak | Validate intended/observed sneak definition and positive/negative labels before a family. Short distance, QB rush or run-gap text is not sufficient. |
| `n_blitzers` | Charted blitzer count | Define qualifying pressure/rush opportunities and zero/default meaning. Box count is not a substitute. |
| `n_pass_rushers` | Charted pass-rusher count | Explain or quarantine invalid 45, never silently repair it. Validate measurement/range and applicable opportunities; zero is not automatically missing or a verified no-rusher event. |
| `is_qb_fault_sack` | QB responsibility on a sack | Require a validated sack/opportunity population and assessment semantics; all non-sack FALSE must not inflate a responsibility rate denominator. |

The other seven columns are IDs, season/week and extraction time. They support
identity/provenance only, not additional football features. No personnel, named
route concept, inside/outside run, pass-depth family or mutually exclusive action
taxonomy is admitted by these decisions. Participation remains unacquired; Big
Data Bowl/tracking source selection and rights review are deferred later work,
not a prerequisite for P1.8.

## Null states and denominator contract for future admission

This is a **design contract**, not new JSON returned by the current API. Existing
unrecognized filters fail with HTTP 422; they are never silently applied.

1. A deferred feature has no estimate: value, numerator and observation
   denominator are **null**, with a defer reason. Do not render zero or an empty
   set as proof of no observed feature. Available encoding counts stay explicitly
   labeled as audit diagnostics.
2. A missing join, absent column, missing token, unknown code and invalid value
   remain distinct. A recognized token is still only `applicability_unverified`
   until an explicit field rule is justified. `not_applicable` requires that rule;
   neither FALSE nor zero alone supplies it.
3. For a future admitted boolean field and candidate j, define an applicable,
   observed subset A_j. Its feature frequency would be observed TRUE / (observed
   TRUE + observed FALSE) **within A_j**, not within all joined rows. Expose eligible
   plays, applicable observations, exclusions by reason and distinct games together.
   If A_j is empty, the estimate is null, never 0%. Unknown applicability is not an
   observed negative or an inferred `not_applicable` row.
4. Candidate call frequency remains N_j / N_all for the selected eligible PBP
   cohort: zero for an unobserved candidate in a nonempty cohort, null when the
   entire cohort is empty. Feature missingness must not change that denominator. A deliberately
   field-conditioned cohort would be a different, explicit request with its own
   exclusion ledger and identically conditioned league baseline.
5. EPA/success need their own nonmissing EPA counts within the requested cohort;
   charting cannot fill missing EPA or invent success. Candidate/play and game
   support must be shown separately. Existing count warnings do not validate a
   new measurement, an uncertainty interval or a preferred call.
6. Validate field observations and denominator rules independently, including
   positive and negative cases, ambiguous plays, missingness by team/week/candidate
   and all relevant joins. Version the policy/source and any label-validation
   evidence. No universal sample-size threshold can replace these checks.

Pre-snap football semantics do not mean the chart was publicly available pregame.
Post-play assessments and revised retrospective values cannot be future predictors
without explicit temporal validation. Any future model needs its own train/test,
calibration, baseline and leakage review. Source semantics alone do not approve
enriched distribution; review that intended use separately under the source terms.

## Regression evidence and next step

`tests/test_enrichment_boundary.py` changes only supplemental columns in invented
PBP CSVs. All 22 charting fields are varied through literal TRUE/FALSE, blank/NA,
zero and invalid values. Plausible codes and deliberately conflicting flags,
personnel/formation/text/location/depth proxies and outcome-like extras cannot
change typed plays, exclusions, Scout offense/defense, matched baselines,
exploratory intervals, candidate classification or abstention. Source fingerprints
must change with changed bytes; every other report field must remain equal.
Hand-counted outcomes and missing/empty cases supplement those comparisons.

The API test puts valid-looking charting columns inside a synthetic verified
snapshot, then confirms requested charting/family filters are rejected **before**
the report builder runs. Header presence is not permission to expose a capability.
These tests establish today's isolation boundary, not future enrichment correctness.
There is no new production parser, normalizer, schema or policy dependency.

Next: a narrow optional FastAPI decision endpoint over the existing immutable
PBP snapshot and `build_decision_evidence` contract v1. Preserve Scout schema v2,
bound bootstrap cost, test request/response/errors/concurrency and carry provenance,
denominators, warnings and abstention intact. No charting/model feature, database,
UI or deployment is required for that unit.

[dictionary]: https://github.com/nflverse/nflreadr/blob/23f915a5be30415aeaa0c5c80cd23b2c69cda122/data-raw/dictionary_ftn_charting.csv
[live]: https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html
[producer]: https://github.com/nflverse/nflverse-ftn/blob/8ba8955b93856cabc9c50ca25d6d3812adb45ae3/R/nflverse.R
[receipt]: evidence/ftn-2024-6faae8118cc1-pbp-23370d5d10f8.coverage.json
[sa]: https://creativecommons.org/licenses/by-sa/4.0/
[by]: https://creativecommons.org/licenses/by/4.0/
