# Historical opponent brief: CAR offense — 2024 REG

**Source label (caller supplied):** Synthetic verification fixture\; not real NFL observations

Descriptive cohort evidence, not a matchup forecast, opponent adjustment, or play recommendation. Rendering does not authenticate the source or reconstruct information available at game time.

**Window:** season 2024, REG, week < 3 (exclusive). This boundary is a requested cutoff, not proof of complete weekly coverage.

**Role:** the selected offense. Success means offensive EPA > 0; dropbacks include sacks and scrambles.

## At a glance

- Sample: 6 eligible plays across 2 observed games; 5 observed EPA values and 1 missing.
- Dropbacks: 3 / 6 (50.0%). Success: 60.0% of observed EPA. EPA per observed play: 0.040.
- Read these as historical descriptions only. Sample warnings and all requested interval states are reported below; hundreds of plays do not establish independent evidence.

**Report fingerprint (canonical JSON SHA-256):** `7c6c42d4cd3e659170e7eb23704becbb4e97e345fe6b6599273e5c268074ac93`

**Input fingerprint (decoded CSV SHA-256):** `2e5fcfc23152b3e36c1e5e81c64fbd5432010f72d13cacb142c2fb61266e7648`

Brief format v1; report schema v2. Full provenance and accounting follow below.

## Cohort and requested contexts

| Report field | Recorded value |
| --- | --- |
| cohort\.before\_week\_exclusive | 3 |
| cohort\.minimum\_plays\_warning | 30 |
| cohort\.season | 2024 |
| cohort\.season\_type | REG |
| cohort\.side | offense |
| cohort\.team | CAR |

Context fields retain the offense's coordinates: yardline_100 is distance to the opposing goal line; score is offense minus defense. Clock is pre-play seconds within the selected period (OT groups all overtime periods). Absent context keys mean no filter; null score bounds are unbounded, not zero. Active filters run field position → score → period → clock after team/season/week selection.

## Overall measurements

| Metric | Selected | Matching baseline | Selected − baseline |
| --- | --- | --- | --- |
| Dropback rate \(all eligible plays\) | 50\.0\% | 100\.0\% | \-50\.0 pp |
| Success rate \(observed EPA only\) | 60\.0\% | 100\.0\% | \-40\.0 pp |
| EPA per observed play | 0\.040 | 3\.000 | \-2\.960 |

Rates are displayed as percentages; rate differences are percentage points (pp), not percent change. EPA and its differences are expected points per observed play. Values are rounded for display only; unavailable is not zero. Positive differences mean numerically higher, not universally better.

## Sample support and missingness

Play/EPA warnings use the requested threshold of 30 separately. They are not significance tests. Game counts overlap across situations and must not be summed.

| Scope | Population | Plays \/ games | Dropbacks \/ designed runs | EPA observed \/ missing | Below threshold |
| --- | --- | --- | --- | --- | --- |
| Overall | selected | 6 \/ 2 | 3 \/ 3 | 5 \/ 1 | plays\, EPA |
| Overall | baseline | 1 \/ 1 | 1 \/ 0 | 1 \/ 0 | plays\, EPA |
| Down 1\, long | selected | 3 \/ 2 | 2 \/ 1 | 3 \/ 0 | plays\, EPA |
| Down 1\, long | baseline | 1 \/ 1 | 1 \/ 0 | 1 \/ 0 | plays\, EPA |
| Down 2\, short | selected | 1 \/ 1 | 0 \/ 1 | 1 \/ 0 | plays\, EPA |
| Down 2\, short | baseline | 0 \/ 0 | 0 \/ 0 | 0 \/ 0 | plays\, EPA |
| Down 2\, medium | selected | 1 \/ 1 | 0 \/ 1 | 0 \/ 1 | plays\, EPA |
| Down 2\, medium | baseline | 0 \/ 0 | 0 \/ 0 | 0 \/ 0 | plays\, EPA |
| Down 3\, long | selected | 1 \/ 1 | 1 \/ 0 | 1 \/ 0 | plays\, EPA |
| Down 3\, long | baseline | 0 \/ 0 | 0 \/ 0 | 0 \/ 0 | plays\, EPA |

Dropback denominator = plays; success and EPA denominators = observed EPA. Missing EPA does not remove a play from dropback counts. Source fields: overall and situations; baseline counts: league_comparison.overall and league_comparison.situations[].baseline.

## Down/distance measurements

Short = 0–3 yards to go, medium = 4–6, long = 7+. Only selected-team observed buckets are listed. These are descriptive product buckets, not standardized scouting grades.

| Scope | Population | Dropback rate | Success rate | EPA \/ observed play |
| --- | --- | --- | --- | --- |
| Down 1\, long | selected | 66\.7\% | 66\.7\% | 0\.400 |
| Down 1\, long | baseline | 100\.0\% | 100\.0\% | 3\.000 |
| Down 2\, short | selected | 0\.0\% | 100\.0\% | 0\.200 |
| Down 2\, short | baseline | unavailable | unavailable | unavailable |
| Down 2\, medium | selected | 0\.0\% | unavailable | unavailable |
| Down 2\, medium | baseline | unavailable | unavailable | unavailable |
| Down 3\, long | selected | 100\.0\% | 0\.0\% | \-1\.200 |
| Down 3\, long | baseline | unavailable | unavailable | unavailable |

## Matching league comparison

Available-source baseline: 1 observed other teams in the same role; 1 games shared with the selected cohort. Counts are pooled across plays, not averaged across teams. This does not certify full league coverage.

| Population field | Recorded value |
| --- | --- |
| league\_comparison\.population\.excluded\_team | CAR |
| league\_comparison\.population\.scope | available\_source\_only |
| league\_comparison\.population\.shared\_games\_with\_selected | 1 |
| league\_comparison\.population\.side | offense |
| league\_comparison\.population\.team\_count | 1 |
| league\_comparison\.population\.team\_field | posteam |
| league\_comparison\.population\.teams | \[\"ATL\"\] |
| league\_comparison\.population\.weighting | pooled\_plays |

| Scope | Dropback difference | Success difference | EPA difference |
| --- | --- | --- | --- |
| Overall | \-50\.0 pp | \-40\.0 pp | \-2\.960 |
| Down 1\, long | \-33\.3 pp | \-33\.3 pp | \-2\.600 |
| Down 2\, short | unavailable | unavailable | unavailable |
| Down 2\, medium | unavailable | unavailable | unavailable |
| Down 3\, long | unavailable | unavailable | unavailable |

Differences are selected minus matching baseline. Missing matches remain unavailable; overall data is not substituted. Baseline-only buckets are not displayed, so baseline situation counts need not sum to baseline overall. Overall context mixes may differ despite matching filters. Source: league_comparison.overall_difference and situations[].difference.

## Exploratory game-level uncertainty

Nominal 95% pointwise percentile intervals, not calibrated coverage, significance tests, or predictions. Whole games are resampled; repeated teams/opponents across games remain dependent. Support/validity gates are application policies. More draws do not add observed games.

| Method field | Recorded value |
| --- | --- |
| uncertainty\.few\_games\_warning\_below | 20 |
| uncertainty\.method | game\_cluster\_percentile\_v1 |
| uncertainty\.minimum\_support\_games | 5 |
| uncertainty\.minimum\_valid\_fraction | 0\.95 |
| uncertainty\.nominal\_level | 0\.95 |
| uncertainty\.performed\_repetitions | 200 |
| uncertainty\.quantile\_method | linear\_n\_minus\_1 |
| uncertainty\.random\_generator | python\_random\.Random\.randrange |
| uncertainty\.repetitions | 200 |
| uncertainty\.resampling\_games | 2 |
| uncertainty\.resampling\_population | selected\_and\_baseline\_union |
| uncertainty\.resampling\_unit | game\_id |
| uncertainty\.seed | 0 |
| uncertainty\.shared\_game\_weights | true |

| Scope | Population\: metric | Interval or status | Supporting games | Few games\? | Valid \/ undefined draws |
| --- | --- | --- | --- | --- | --- |
| Overall | selected\: dropback\_rate | unavailable \(insufficient\_games\) | selected\=2 | yes | 200 \/ 0 |
| Overall | selected\: success\_rate | unavailable \(insufficient\_games\) | selected\=2 | yes | 200 \/ 0 |
| Overall | selected\: epa\_per\_play | unavailable \(insufficient\_games\) | selected\=2 | yes | 200 \/ 0 |
| Overall | baseline\: dropback\_rate | unavailable \(insufficient\_games\) | baseline\=1 | yes | 154 \/ 46 |
| Overall | baseline\: success\_rate | unavailable \(insufficient\_games\) | baseline\=1 | yes | 154 \/ 46 |
| Overall | baseline\: epa\_per\_play | unavailable \(insufficient\_games\) | baseline\=1 | yes | 154 \/ 46 |
| Overall | difference\: dropback\_rate\_pp | unavailable \(insufficient\_games\) | baseline\=1\; selected\=2 | yes | 154 \/ 46 |
| Overall | difference\: success\_rate\_pp | unavailable \(insufficient\_games\) | baseline\=1\; selected\=2 | yes | 154 \/ 46 |
| Overall | difference\: epa\_per\_play | unavailable \(insufficient\_games\) | baseline\=1\; selected\=2 | yes | 154 \/ 46 |
| Down 1\, long | selected\: dropback\_rate | unavailable \(insufficient\_games\) | selected\=2 | yes | 200 \/ 0 |
| Down 1\, long | selected\: success\_rate | unavailable \(insufficient\_games\) | selected\=2 | yes | 200 \/ 0 |
| Down 1\, long | selected\: epa\_per\_play | unavailable \(insufficient\_games\) | selected\=2 | yes | 200 \/ 0 |
| Down 1\, long | baseline\: dropback\_rate | unavailable \(insufficient\_games\) | baseline\=1 | yes | 154 \/ 46 |
| Down 1\, long | baseline\: success\_rate | unavailable \(insufficient\_games\) | baseline\=1 | yes | 154 \/ 46 |
| Down 1\, long | baseline\: epa\_per\_play | unavailable \(insufficient\_games\) | baseline\=1 | yes | 154 \/ 46 |
| Down 1\, long | difference\: dropback\_rate\_pp | unavailable \(insufficient\_games\) | baseline\=1\; selected\=2 | yes | 154 \/ 46 |
| Down 1\, long | difference\: success\_rate\_pp | unavailable \(insufficient\_games\) | baseline\=1\; selected\=2 | yes | 154 \/ 46 |
| Down 1\, long | difference\: epa\_per\_play | unavailable \(insufficient\_games\) | baseline\=1\; selected\=2 | yes | 154 \/ 46 |
| Down 2\, short | selected\: dropback\_rate | unavailable \(insufficient\_games\) | selected\=1 | yes | 154 \/ 46 |
| Down 2\, short | selected\: success\_rate | unavailable \(insufficient\_games\) | selected\=1 | yes | 154 \/ 46 |
| Down 2\, short | selected\: epa\_per\_play | unavailable \(insufficient\_games\) | selected\=1 | yes | 154 \/ 46 |
| Down 2\, short | baseline\: dropback\_rate | unavailable \(undefined\_estimate\) | baseline\=0 | yes | 0 \/ 200 |
| Down 2\, short | baseline\: success\_rate | unavailable \(undefined\_estimate\) | baseline\=0 | yes | 0 \/ 200 |
| Down 2\, short | baseline\: epa\_per\_play | unavailable \(undefined\_estimate\) | baseline\=0 | yes | 0 \/ 200 |
| Down 2\, short | difference\: dropback\_rate\_pp | unavailable \(undefined\_estimate\) | baseline\=0\; selected\=1 | yes | 0 \/ 200 |
| Down 2\, short | difference\: success\_rate\_pp | unavailable \(undefined\_estimate\) | baseline\=0\; selected\=1 | yes | 0 \/ 200 |
| Down 2\, short | difference\: epa\_per\_play | unavailable \(undefined\_estimate\) | baseline\=0\; selected\=1 | yes | 0 \/ 200 |
| Down 2\, medium | selected\: dropback\_rate | unavailable \(insufficient\_games\) | selected\=1 | yes | 154 \/ 46 |
| Down 2\, medium | selected\: success\_rate | unavailable \(undefined\_estimate\) | selected\=0 | yes | 0 \/ 200 |
| Down 2\, medium | selected\: epa\_per\_play | unavailable \(undefined\_estimate\) | selected\=0 | yes | 0 \/ 200 |
| Down 2\, medium | baseline\: dropback\_rate | unavailable \(undefined\_estimate\) | baseline\=0 | yes | 0 \/ 200 |
| Down 2\, medium | baseline\: success\_rate | unavailable \(undefined\_estimate\) | baseline\=0 | yes | 0 \/ 200 |
| Down 2\, medium | baseline\: epa\_per\_play | unavailable \(undefined\_estimate\) | baseline\=0 | yes | 0 \/ 200 |
| Down 2\, medium | difference\: dropback\_rate\_pp | unavailable \(undefined\_estimate\) | baseline\=0\; selected\=1 | yes | 0 \/ 200 |
| Down 2\, medium | difference\: success\_rate\_pp | unavailable \(undefined\_estimate\) | baseline\=0\; selected\=0 | yes | 0 \/ 200 |
| Down 2\, medium | difference\: epa\_per\_play | unavailable \(undefined\_estimate\) | baseline\=0\; selected\=0 | yes | 0 \/ 200 |
| Down 3\, long | selected\: dropback\_rate | unavailable \(insufficient\_games\) | selected\=1 | yes | 154 \/ 46 |
| Down 3\, long | selected\: success\_rate | unavailable \(insufficient\_games\) | selected\=1 | yes | 154 \/ 46 |
| Down 3\, long | selected\: epa\_per\_play | unavailable \(insufficient\_games\) | selected\=1 | yes | 154 \/ 46 |
| Down 3\, long | baseline\: dropback\_rate | unavailable \(undefined\_estimate\) | baseline\=0 | yes | 0 \/ 200 |
| Down 3\, long | baseline\: success\_rate | unavailable \(undefined\_estimate\) | baseline\=0 | yes | 0 \/ 200 |
| Down 3\, long | baseline\: epa\_per\_play | unavailable \(undefined\_estimate\) | baseline\=0 | yes | 0 \/ 200 |
| Down 3\, long | difference\: dropback\_rate\_pp | unavailable \(undefined\_estimate\) | baseline\=0\; selected\=1 | yes | 0 \/ 200 |
| Down 3\, long | difference\: success\_rate\_pp | unavailable \(undefined\_estimate\) | baseline\=0\; selected\=1 | yes | 0 \/ 200 |
| Down 3\, long | difference\: epa\_per\_play | unavailable \(undefined\_estimate\) | baseline\=0\; selected\=1 | yes | 0 \/ 200 |

Source: uncertainty.overall and uncertainty.situations, matched by down/distance. Undefined draws are counted and excluded; available intervals condition on defined draws. The status ok means available under this method, not reliable inference. A displayed narrow/rounded interval is not certainty; consult full-precision JSON. Five-game and 95%-valid gates withhold unsupported results; few_games warns below 20 on any required side.

## Source and provenance

Recorded metadata from the supplied report, not revalidated by this renderer. The report fingerprint identifies its canonical JSON content, not an authenticity signature.

| Report field | Recorded value |
| --- | --- |
| source\.label | Synthetic verification fixture\; not real NFL observations |
| source\.sha256 | 2e5fcfc23152b3e36c1e5e81c64fbd5432010f72d13cacb142c2fb61266e7648 |

No acquisition manifest supplied. The label is caller supplied; no source license or acquisition date is inferred.

## Row accounting

| Report field | Recorded count \/ value |
| --- | --- |
| data\_quality\.eligible\_rows\_all\_teams | 10 |
| data\_quality\.eligible\_rows\_outside\_cohort | 4 |
| data\_quality\.excluded\_rows\_by\_reason\.kneel | 1 |
| data\_quality\.excluded\_rows\_by\_reason\.non\_run\_pass | 1 |
| data\_quality\.excluded\_rows\_by\_reason\.spike | 1 |
| data\_quality\.excluded\_rows\_by\_reason\.two\_point\_attempt | 1 |
| data\_quality\.input\_rows | 14 |

| Baseline field | Recorded count \/ value |
| --- | --- |
| league\_comparison\.data\_quality\.eligible\_rows\_same\_season\_type\_before\_week | 7 |
| league\_comparison\.data\_quality\.excluded\_selected\_team\_rows | 6 |
| league\_comparison\.data\_quality\.filter\_order | \[\] |
| league\_comparison\.data\_quality\.plays\_after\_context\_filters | 1 |
| league\_comparison\.data\_quality\.plays\_before\_context\_filters | 1 |

Filter-stage counts are conditional on prior survivors. Removals are already included in outside-cohort counts; do not add nested counts or the baseline ledger to the source totals again.

## Limitations and report warnings

Eligible completed run/pass plays only: kneels, spikes, conversions, non-run/pass and nullified/no-play outcomes are excluded. Designed runs are an outcome-based proxy, not film-verified intent. Personnel, motion and opponent strength are not controlled. Upstream EPA-model uncertainty, revisions and historical information availability are not resolved by a week cutoff or bootstrap.

### report.warnings

- Descriptive completed\-play tendencies\; no opponent adjustment or causal claims\.
- Week filtering does not reconstruct historical source availability or EPA model training\.
- Missing EPA is excluded only from EPA and success\-rate denominators\.

### league\_comparison.warnings

- Baseline uses only available source plays\; full league coverage is not certified\.
- Pooled descriptive differences are not opponent adjustment or predictive validation\.
- Overall context mixes may differ\; compare matching down\/distance rows\, not a reweighted overall score\.
- Plays within games are dependent\; selected and baseline populations may share games and opponents\.

### uncertainty.warnings

- Exploratory pointwise percentile intervals\, not calibrated coverage\, significance tests\, or predictions\.
- Whole\-game resampling retains within\-game dependence\; repeated teams\/opponents across games remain dependent\.
- Five\-game and 95\%\-valid gates are application safeguards\, not statistical reliability guarantees\; few games remain fragile\.
- Undefined resamples are counted and excluded\; any reported bounds condition on defined replicates\.
- Constant or near\-zero\-width percentile intervals are withheld\, not interpreted as certainty\.
- Selection is fixed before resampling\; source availability\, missing\-data bias\, and upstream EPA model uncertainty are not estimated\.
