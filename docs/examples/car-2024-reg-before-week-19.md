# Historical opponent brief: CAR offense — 2024 REG

**Source label (caller supplied):** nflverse 2024 retrospective snapshot\; acquired 2026\-09\-30 UTC

Descriptive cohort evidence, not a matchup forecast, opponent adjustment, or play recommendation. Rendering does not authenticate the source or reconstruct information available at game time.

**Window:** season 2024, REG, week < 19 (exclusive). This boundary is a requested cutoff, not proof of complete weekly coverage.

**Role:** the selected offense. Success means offensive EPA > 0; dropbacks include sacks and scrambles.

## At a glance

- Sample: 984 eligible plays across 17 observed games; 984 observed EPA values and 0 missing.
- Dropbacks: 626 / 984 (63.6%). Success: 41.4% of observed EPA. EPA per observed play: -0.052.
- Read these as historical descriptions only. Sample warnings and all requested interval states are reported below; hundreds of plays do not establish independent evidence.

**Report fingerprint (canonical JSON SHA-256):** `bb8cb25e1632b48eb6d102b82358a9bfba0b8c7d7be56e190405f3dbc819ac33`

**Input fingerprint (decoded CSV SHA-256):** `6ae564c2c49378ec531303292966caee596982278b9fcdad9c9dd0a0dc16bfa7`

Brief format v1; report schema v2. Full provenance and accounting follow below.

## Cohort and requested contexts

| Report field | Recorded value |
| --- | --- |
| cohort\.before\_week\_exclusive | 19 |
| cohort\.minimum\_plays\_warning | 30 |
| cohort\.season | 2024 |
| cohort\.season\_type | REG |
| cohort\.side | offense |
| cohort\.team | CAR |

Context fields retain the offense's coordinates: yardline_100 is distance to the opposing goal line; score is offense minus defense. Clock is pre-play seconds within the selected period (OT groups all overtime periods). Absent context keys mean no filter; null score bounds are unbounded, not zero. Active filters run field position → score → period → clock after team/season/week selection.

## Overall measurements

| Metric | Selected | Matching baseline | Selected − baseline |
| --- | --- | --- | --- |
| Dropback rate \(all eligible plays\) | 63\.6\% | 60\.2\% | 3\.4 pp |
| Success rate \(observed EPA only\) | 41\.4\% | 44\.0\% | \-2\.6 pp |
| EPA per observed play | \-0\.052 | 0\.011 | \-0\.064 |

Rates are displayed as percentages; rate differences are percentage points (pp), not percent change. EPA and its differences are expected points per observed play. Values are rounded for display only; unavailable is not zero. Positive differences mean numerically higher, not universally better.

## Sample support and missingness

Play/EPA warnings use the requested threshold of 30 separately. They are not significance tests. Game counts overlap across situations and must not be summed.

| Scope | Population | Plays \/ games | Dropbacks \/ designed runs | EPA observed \/ missing | Below threshold |
| --- | --- | --- | --- | --- | --- |
| Overall | selected | 984 \/ 17 | 626 \/ 358 | 984 \/ 0 | none |
| Overall | baseline | 32351 \/ 272 | 19490 \/ 12861 | 32351 \/ 0 | none |
| Down 1\, short | selected | 10 \/ 6 | 4 \/ 6 | 10 \/ 0 | plays\, EPA |
| Down 1\, short | baseline | 315 \/ 189 | 82 \/ 233 | 315 \/ 0 | none |
| Down 1\, medium | selected | 12 \/ 9 | 6 \/ 6 | 12 \/ 0 | plays\, EPA |
| Down 1\, medium | baseline | 337 \/ 194 | 123 \/ 214 | 337 \/ 0 | none |
| Down 1\, long | selected | 401 \/ 17 | 208 \/ 193 | 401 \/ 0 | none |
| Down 1\, long | baseline | 13560 \/ 272 | 6819 \/ 6741 | 13560 \/ 0 | none |
| Down 2\, short | selected | 47 \/ 16 | 18 \/ 29 | 47 \/ 0 | none |
| Down 2\, short | baseline | 1794 \/ 272 | 671 \/ 1123 | 1794 \/ 0 | none |
| Down 2\, medium | selected | 88 \/ 17 | 50 \/ 38 | 88 \/ 0 | none |
| Down 2\, medium | baseline | 2498 \/ 272 | 1329 \/ 1169 | 2498 \/ 0 | none |
| Down 2\, long | selected | 185 \/ 17 | 137 \/ 48 | 185 \/ 0 | none |
| Down 2\, long | baseline | 6496 \/ 272 | 4716 \/ 1780 | 6496 \/ 0 | none |
| Down 3\, short | selected | 55 \/ 16 | 32 \/ 23 | 55 \/ 0 | none |
| Down 3\, short | baseline | 1920 \/ 272 | 980 \/ 940 | 1920 \/ 0 | none |
| Down 3\, medium | selected | 60 \/ 16 | 56 \/ 4 | 60 \/ 0 | none |
| Down 3\, medium | baseline | 1655 \/ 271 | 1510 \/ 145 | 1655 \/ 0 | none |
| Down 3\, long | selected | 96 \/ 17 | 91 \/ 5 | 96 \/ 0 | none |
| Down 3\, long | baseline | 3042 \/ 272 | 2791 \/ 251 | 3042 \/ 0 | none |
| Down 4\, short | selected | 19 \/ 10 | 13 \/ 6 | 19 \/ 0 | plays\, EPA |
| Down 4\, short | baseline | 492 \/ 231 | 238 \/ 254 | 492 \/ 0 | none |
| Down 4\, medium | selected | 6 \/ 3 | 6 \/ 0 | 6 \/ 0 | plays\, EPA |
| Down 4\, medium | baseline | 117 \/ 95 | 111 \/ 6 | 117 \/ 0 | none |
| Down 4\, long | selected | 5 \/ 4 | 5 \/ 0 | 5 \/ 0 | plays\, EPA |
| Down 4\, long | baseline | 125 \/ 98 | 120 \/ 5 | 125 \/ 0 | none |

Dropback denominator = plays; success and EPA denominators = observed EPA. Missing EPA does not remove a play from dropback counts. Source fields: overall and situations; baseline counts: league_comparison.overall and league_comparison.situations[].baseline.

## Down/distance measurements

Short = 0–3 yards to go, medium = 4–6, long = 7+. Only selected-team observed buckets are listed. These are descriptive product buckets, not standardized scouting grades.

| Scope | Population | Dropback rate | Success rate | EPA \/ observed play |
| --- | --- | --- | --- | --- |
| Down 1\, short | selected | 40\.0\% | 40\.0\% | 0\.137 |
| Down 1\, short | baseline | 26\.0\% | 51\.7\% | 0\.088 |
| Down 1\, medium | selected | 50\.0\% | 41\.7\% | 0\.039 |
| Down 1\, medium | baseline | 36\.5\% | 51\.6\% | \-0\.054 |
| Down 1\, long | selected | 51\.9\% | 42\.9\% | 0\.024 |
| Down 1\, long | baseline | 50\.3\% | 41\.9\% | \-0\.003 |
| Down 2\, short | selected | 38\.3\% | 55\.3\% | \-0\.025 |
| Down 2\, short | baseline | 37\.4\% | 54\.7\% | 0\.018 |
| Down 2\, medium | selected | 56\.8\% | 45\.5\% | \-0\.044 |
| Down 2\, medium | baseline | 53\.2\% | 48\.2\% | 0\.073 |
| Down 2\, long | selected | 74\.1\% | 34\.6\% | \-0\.093 |
| Down 2\, long | baseline | 72\.6\% | 42\.3\% | 0\.032 |
| Down 3\, short | selected | 58\.2\% | 52\.7\% | \-0\.051 |
| Down 3\, short | baseline | 51\.0\% | 59\.0\% | \-0\.036 |
| Down 3\, medium | selected | 93\.3\% | 41\.7\% | \-0\.018 |
| Down 3\, medium | baseline | 91\.2\% | 45\.1\% | 0\.056 |
| Down 3\, long | selected | 94\.8\% | 29\.2\% | \-0\.311 |
| Down 3\, long | baseline | 91\.7\% | 32\.0\% | \-0\.085 |
| Down 4\, short | selected | 68\.4\% | 57\.9\% | 0\.325 |
| Down 4\, short | baseline | 48\.4\% | 65\.2\% | 0\.511 |
| Down 4\, medium | selected | 100\.0\% | 16\.7\% | \-2\.247 |
| Down 4\, medium | baseline | 94\.9\% | 48\.7\% | 0\.245 |
| Down 4\, long | selected | 100\.0\% | 40\.0\% | 0\.008 |
| Down 4\, long | baseline | 96\.0\% | 31\.2\% | \-0\.561 |

## Matching league comparison

Available-source baseline: 31 observed other teams in the same role; 17 games shared with the selected cohort. Counts are pooled across plays, not averaged across teams. This does not certify full league coverage.

| Population field | Recorded value |
| --- | --- |
| league\_comparison\.population\.excluded\_team | CAR |
| league\_comparison\.population\.scope | available\_source\_only |
| league\_comparison\.population\.shared\_games\_with\_selected | 17 |
| league\_comparison\.population\.side | offense |
| league\_comparison\.population\.team\_count | 31 |
| league\_comparison\.population\.team\_field | posteam |
| league\_comparison\.population\.teams | \[\"ARI\"\, \"ATL\"\, \"BAL\"\, \"BUF\"\, \"CHI\"\, \"CIN\"\, \"CLE\"\, \"DAL\"\, \"DEN\"\, \"DET\"\, \"GB\"\, \"HOU\"\, \"IND\"\, \"JAX\"\, \"KC\"\, \"LA\"\, \"LAC\"\, \"LV\"\, \"MIA\"\, \"MIN\"\, \"NE\"\, \"NO\"\, \"NYG\"\, \"NYJ\"\, \"PHI\"\, \"PIT\"\, \"SEA\"\, \"SF\"\, \"TB\"\, \"TEN\"\, \"WAS\"\] |
| league\_comparison\.population\.weighting | pooled\_plays |

| Scope | Dropback difference | Success difference | EPA difference |
| --- | --- | --- | --- |
| Overall | 3\.4 pp | \-2\.6 pp | \-0\.064 |
| Down 1\, short | 14\.0 pp | \-11\.7 pp | 0\.050 |
| Down 1\, medium | 13\.5 pp | \-10\.0 pp | 0\.093 |
| Down 1\, long | 1\.6 pp | 1\.0 pp | 0\.028 |
| Down 2\, short | 0\.9 pp | 0\.6 pp | \-0\.043 |
| Down 2\, medium | 3\.6 pp | \-2\.7 pp | \-0\.117 |
| Down 2\, long | 1\.5 pp | \-7\.7 pp | \-0\.125 |
| Down 3\, short | 7\.1 pp | \-6\.3 pp | \-0\.014 |
| Down 3\, medium | 2\.1 pp | \-3\.5 pp | \-0\.074 |
| Down 3\, long | 3\.0 pp | \-2\.9 pp | \-0\.226 |
| Down 4\, short | 20\.0 pp | \-7\.3 pp | \-0\.186 |
| Down 4\, medium | 5\.1 pp | \-32\.1 pp | \-2\.492 |
| Down 4\, long | 4\.0 pp | 8\.8 pp | 0\.569 |

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
| uncertainty\.performed\_repetitions | 1000 |
| uncertainty\.quantile\_method | linear\_n\_minus\_1 |
| uncertainty\.random\_generator | python\_random\.Random\.randrange |
| uncertainty\.repetitions | 1000 |
| uncertainty\.resampling\_games | 272 |
| uncertainty\.resampling\_population | selected\_and\_baseline\_union |
| uncertainty\.resampling\_unit | game\_id |
| uncertainty\.seed | 20261006 |
| uncertainty\.shared\_game\_weights | true |

| Scope | Population\: metric | Interval or status | Supporting games | Few games\? | Valid \/ undefined draws |
| --- | --- | --- | --- | --- | --- |
| Overall | selected\: dropback\_rate | \[59\.7\%\, 67\.7\%\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Overall | selected\: success\_rate | \[37\.3\%\, 44\.7\%\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Overall | selected\: epa\_per\_play | \[\-0\.175\, 0\.062\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Overall | baseline\: dropback\_rate | \[59\.5\%\, 61\.0\%\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Overall | baseline\: success\_rate | \[43\.3\%\, 44\.7\%\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Overall | baseline\: epa\_per\_play | \[\-0\.006\, 0\.028\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Overall | difference\: dropback\_rate\_pp | \[\-0\.6 pp\, 7\.4 pp\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Overall | difference\: success\_rate\_pp | \[\-6\.7 pp\, 0\.9 pp\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Overall | difference\: epa\_per\_play | \[\-0\.190\, 0\.049\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Down 1\, short | selected\: dropback\_rate | \[10\.0\%\, 80\.0\%\] \(ok\) | selected\=6 | yes | 999 \/ 1 |
| Down 1\, short | selected\: success\_rate | \[0\.0\%\, 71\.5\%\] \(ok\) | selected\=6 | yes | 999 \/ 1 |
| Down 1\, short | selected\: epa\_per\_play | \[\-0\.317\, 0\.442\] \(ok\) | selected\=6 | yes | 999 \/ 1 |
| Down 1\, short | baseline\: dropback\_rate | \[21\.2\%\, 30\.8\%\] \(ok\) | baseline\=189 | no | 1000 \/ 0 |
| Down 1\, short | baseline\: success\_rate | \[46\.5\%\, 56\.8\%\] \(ok\) | baseline\=189 | no | 1000 \/ 0 |
| Down 1\, short | baseline\: epa\_per\_play | \[\-0\.010\, 0\.178\] \(ok\) | baseline\=189 | no | 1000 \/ 0 |
| Down 1\, short | difference\: dropback\_rate\_pp | \[\-17\.1 pp\, 53\.5 pp\] \(ok\) | baseline\=189\; selected\=6 | yes | 999 \/ 1 |
| Down 1\, short | difference\: success\_rate\_pp | \[\-52\.7 pp\, 21\.2 pp\] \(ok\) | baseline\=189\; selected\=6 | yes | 999 \/ 1 |
| Down 1\, short | difference\: epa\_per\_play | \[\-0\.425\, 0\.373\] \(ok\) | baseline\=189\; selected\=6 | yes | 999 \/ 1 |
| Down 1\, medium | selected\: dropback\_rate | \[20\.0\%\, 80\.0\%\] \(ok\) | selected\=9 | yes | 1000 \/ 0 |
| Down 1\, medium | selected\: success\_rate | \[16\.7\%\, 66\.7\%\] \(ok\) | selected\=9 | yes | 1000 \/ 0 |
| Down 1\, medium | selected\: epa\_per\_play | \[\-0\.284\, 0\.443\] \(ok\) | selected\=9 | yes | 1000 \/ 0 |
| Down 1\, medium | baseline\: dropback\_rate | \[31\.6\%\, 41\.5\%\] \(ok\) | baseline\=194 | no | 1000 \/ 0 |
| Down 1\, medium | baseline\: success\_rate | \[46\.9\%\, 56\.9\%\] \(ok\) | baseline\=194 | no | 1000 \/ 0 |
| Down 1\, medium | baseline\: epa\_per\_play | \[\-0\.226\, 0\.101\] \(ok\) | baseline\=194 | no | 1000 \/ 0 |
| Down 1\, medium | difference\: dropback\_rate\_pp | \[\-16\.5 pp\, 43\.9 pp\] \(ok\) | baseline\=194\; selected\=9 | yes | 1000 \/ 0 |
| Down 1\, medium | difference\: success\_rate\_pp | \[\-34\.5 pp\, 13\.8 pp\] \(ok\) | baseline\=194\; selected\=9 | yes | 1000 \/ 0 |
| Down 1\, medium | difference\: epa\_per\_play | \[\-0\.272\, 0\.539\] \(ok\) | baseline\=194\; selected\=9 | yes | 1000 \/ 0 |
| Down 1\, long | selected\: dropback\_rate | \[47\.5\%\, 56\.1\%\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Down 1\, long | selected\: success\_rate | \[38\.9\%\, 46\.6\%\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Down 1\, long | selected\: epa\_per\_play | \[\-0\.070\, 0\.112\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Down 1\, long | baseline\: dropback\_rate | \[49\.2\%\, 51\.3\%\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 1\, long | baseline\: success\_rate | \[41\.1\%\, 42\.8\%\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 1\, long | baseline\: epa\_per\_play | \[\-0\.023\, 0\.016\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 1\, long | difference\: dropback\_rate\_pp | \[\-2\.9 pp\, 6\.0 pp\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Down 1\, long | difference\: success\_rate\_pp | \[\-3\.1 pp\, 4\.7 pp\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Down 1\, long | difference\: epa\_per\_play | \[\-0\.067\, 0\.118\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Down 2\, short | selected\: dropback\_rate | \[23\.1\%\, 53\.3\%\] \(ok\) | selected\=16 | yes | 1000 \/ 0 |
| Down 2\, short | selected\: success\_rate | \[42\.2\%\, 70\.6\%\] \(ok\) | selected\=16 | yes | 1000 \/ 0 |
| Down 2\, short | selected\: epa\_per\_play | \[\-0\.202\, 0\.196\] \(ok\) | selected\=16 | yes | 1000 \/ 0 |
| Down 2\, short | baseline\: dropback\_rate | \[34\.9\%\, 39\.9\%\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 2\, short | baseline\: success\_rate | \[52\.3\%\, 57\.0\%\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 2\, short | baseline\: epa\_per\_play | \[\-0\.032\, 0\.064\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 2\, short | difference\: dropback\_rate\_pp | \[\-14\.6 pp\, 15\.9 pp\] \(ok\) | baseline\=272\; selected\=16 | yes | 1000 \/ 0 |
| Down 2\, short | difference\: success\_rate\_pp | \[\-13\.4 pp\, 16\.8 pp\] \(ok\) | baseline\=272\; selected\=16 | yes | 1000 \/ 0 |
| Down 2\, short | difference\: epa\_per\_play | \[\-0\.236\, 0\.177\] \(ok\) | baseline\=272\; selected\=16 | yes | 1000 \/ 0 |
| Down 2\, medium | selected\: dropback\_rate | \[48\.4\%\, 65\.5\%\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Down 2\, medium | selected\: success\_rate | \[37\.6\%\, 53\.5\%\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Down 2\, medium | selected\: epa\_per\_play | \[\-0\.272\, 0\.205\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Down 2\, medium | baseline\: dropback\_rate | \[51\.1\%\, 55\.3\%\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 2\, medium | baseline\: success\_rate | \[46\.3\%\, 50\.2\%\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 2\, medium | baseline\: epa\_per\_play | \[0\.027\, 0\.122\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 2\, medium | difference\: dropback\_rate\_pp | \[\-5\.0 pp\, 12\.8 pp\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Down 2\, medium | difference\: success\_rate\_pp | \[\-10\.9 pp\, 5\.3 pp\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Down 2\, medium | difference\: epa\_per\_play | \[\-0\.355\, 0\.143\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Down 2\, long | selected\: dropback\_rate | \[68\.0\%\, 80\.3\%\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Down 2\, long | selected\: success\_rate | \[26\.9\%\, 42\.9\%\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Down 2\, long | selected\: epa\_per\_play | \[\-0\.253\, 0\.053\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Down 2\, long | baseline\: dropback\_rate | \[71\.3\%\, 73\.8\%\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 2\, long | baseline\: success\_rate | \[41\.2\%\, 43\.5\%\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 2\, long | baseline\: epa\_per\_play | \[0\.000\, 0\.062\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 2\, long | difference\: dropback\_rate\_pp | \[\-4\.8 pp\, 7\.7 pp\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Down 2\, long | difference\: success\_rate\_pp | \[\-15\.5 pp\, 0\.4 pp\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Down 2\, long | difference\: epa\_per\_play | \[\-0\.289\, 0\.029\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Down 3\, short | selected\: dropback\_rate | \[47\.6\%\, 70\.7\%\] \(ok\) | selected\=16 | yes | 1000 \/ 0 |
| Down 3\, short | selected\: success\_rate | \[37\.8\%\, 64\.6\%\] \(ok\) | selected\=16 | yes | 1000 \/ 0 |
| Down 3\, short | selected\: epa\_per\_play | \[\-0\.542\, 0\.425\] \(ok\) | selected\=16 | yes | 1000 \/ 0 |
| Down 3\, short | baseline\: dropback\_rate | \[48\.5\%\, 53\.4\%\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 3\, short | baseline\: success\_rate | \[56\.8\%\, 61\.2\%\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 3\, short | baseline\: epa\_per\_play | \[\-0\.114\, 0\.043\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 3\, short | difference\: dropback\_rate\_pp | \[\-3\.9 pp\, 20\.2 pp\] \(ok\) | baseline\=272\; selected\=16 | yes | 1000 \/ 0 |
| Down 3\, short | difference\: success\_rate\_pp | \[\-21\.2 pp\, 5\.6 pp\] \(ok\) | baseline\=272\; selected\=16 | yes | 1000 \/ 0 |
| Down 3\, short | difference\: epa\_per\_play | \[\-0\.515\, 0\.461\] \(ok\) | baseline\=272\; selected\=16 | yes | 1000 \/ 0 |
| Down 3\, medium | selected\: dropback\_rate | \[87\.0\%\, 98\.6\%\] \(ok\) | selected\=16 | yes | 1000 \/ 0 |
| Down 3\, medium | selected\: success\_rate | \[30\.4\%\, 53\.3\%\] \(ok\) | selected\=16 | yes | 1000 \/ 0 |
| Down 3\, medium | selected\: epa\_per\_play | \[\-0\.456\, 0\.399\] \(ok\) | selected\=16 | yes | 1000 \/ 0 |
| Down 3\, medium | baseline\: dropback\_rate | \[89\.7\%\, 92\.7\%\] \(ok\) | baseline\=271 | no | 1000 \/ 0 |
| Down 3\, medium | baseline\: success\_rate | \[42\.8\%\, 47\.7\%\] \(ok\) | baseline\=271 | no | 1000 \/ 0 |
| Down 3\, medium | baseline\: epa\_per\_play | \[\-0\.031\, 0\.144\] \(ok\) | baseline\=271 | no | 1000 \/ 0 |
| Down 3\, medium | difference\: dropback\_rate\_pp | \[\-4\.6 pp\, 8\.1 pp\] \(ok\) | baseline\=271\; selected\=16 | yes | 1000 \/ 0 |
| Down 3\, medium | difference\: success\_rate\_pp | \[\-15\.3 pp\, 8\.4 pp\] \(ok\) | baseline\=271\; selected\=16 | yes | 1000 \/ 0 |
| Down 3\, medium | difference\: epa\_per\_play | \[\-0\.498\, 0\.354\] \(ok\) | baseline\=271\; selected\=16 | yes | 1000 \/ 0 |
| Down 3\, long | selected\: dropback\_rate | \[90\.2\%\, 99\.1\%\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Down 3\, long | selected\: success\_rate | \[20\.6\%\, 37\.0\%\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Down 3\, long | selected\: epa\_per\_play | \[\-0\.731\, 0\.067\] \(ok\) | selected\=17 | yes | 1000 \/ 0 |
| Down 3\, long | baseline\: dropback\_rate | \[90\.7\%\, 92\.7\%\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 3\, long | baseline\: success\_rate | \[30\.2\%\, 33\.6\%\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 3\, long | baseline\: epa\_per\_play | \[\-0\.152\, \-0\.020\] \(ok\) | baseline\=272 | no | 1000 \/ 0 |
| Down 3\, long | difference\: dropback\_rate\_pp | \[\-1\.6 pp\, 7\.9 pp\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Down 3\, long | difference\: success\_rate\_pp | \[\-11\.9 pp\, 5\.4 pp\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Down 3\, long | difference\: epa\_per\_play | \[\-0\.642\, 0\.169\] \(ok\) | baseline\=272\; selected\=17 | yes | 1000 \/ 0 |
| Down 4\, short | selected\: dropback\_rate | \[42\.9\%\, 90\.0\%\] \(ok\) | selected\=10 | yes | 1000 \/ 0 |
| Down 4\, short | selected\: success\_rate | \[36\.4\%\, 81\.5\%\] \(ok\) | selected\=10 | yes | 1000 \/ 0 |
| Down 4\, short | selected\: epa\_per\_play | \[\-0\.882\, 1\.677\] \(ok\) | selected\=10 | yes | 1000 \/ 0 |
| Down 4\, short | baseline\: dropback\_rate | \[43\.8\%\, 52\.8\%\] \(ok\) | baseline\=231 | no | 1000 \/ 0 |
| Down 4\, short | baseline\: success\_rate | \[60\.9\%\, 69\.7\%\] \(ok\) | baseline\=231 | no | 1000 \/ 0 |
| Down 4\, short | baseline\: epa\_per\_play | \[0\.234\, 0\.789\] \(ok\) | baseline\=231 | no | 1000 \/ 0 |
| Down 4\, short | difference\: dropback\_rate\_pp | \[\-4\.5 pp\, 41\.6 pp\] \(ok\) | baseline\=231\; selected\=10 | yes | 1000 \/ 0 |
| Down 4\, short | difference\: success\_rate\_pp | \[\-28\.9 pp\, 15\.7 pp\] \(ok\) | baseline\=231\; selected\=10 | yes | 1000 \/ 0 |
| Down 4\, short | difference\: epa\_per\_play | \[\-1\.381\, 1\.179\] \(ok\) | baseline\=231\; selected\=10 | yes | 1000 \/ 0 |
| Down 4\, medium | selected\: dropback\_rate | unavailable \(insufficient\_games\) | selected\=3 | yes | 956 \/ 44 |
| Down 4\, medium | selected\: success\_rate | unavailable \(insufficient\_games\) | selected\=3 | yes | 956 \/ 44 |
| Down 4\, medium | selected\: epa\_per\_play | unavailable \(insufficient\_games\) | selected\=3 | yes | 956 \/ 44 |
| Down 4\, medium | baseline\: dropback\_rate | \[90\.5\%\, 98\.3\%\] \(ok\) | baseline\=95 | no | 1000 \/ 0 |
| Down 4\, medium | baseline\: success\_rate | \[39\.7\%\, 57\.3\%\] \(ok\) | baseline\=95 | no | 1000 \/ 0 |
| Down 4\, medium | baseline\: epa\_per\_play | \[\-0\.347\, 0\.844\] \(ok\) | baseline\=95 | no | 1000 \/ 0 |
| Down 4\, medium | difference\: dropback\_rate\_pp | unavailable \(insufficient\_games\) | baseline\=95\; selected\=3 | yes | 956 \/ 44 |
| Down 4\, medium | difference\: success\_rate\_pp | unavailable \(insufficient\_games\) | baseline\=95\; selected\=3 | yes | 956 \/ 44 |
| Down 4\, medium | difference\: epa\_per\_play | unavailable \(insufficient\_games\) | baseline\=95\; selected\=3 | yes | 956 \/ 44 |
| Down 4\, long | selected\: dropback\_rate | unavailable \(insufficient\_games\) | selected\=4 | yes | 975 \/ 25 |
| Down 4\, long | selected\: success\_rate | unavailable \(insufficient\_games\) | selected\=4 | yes | 975 \/ 25 |
| Down 4\, long | selected\: epa\_per\_play | unavailable \(insufficient\_games\) | selected\=4 | yes | 975 \/ 25 |
| Down 4\, long | baseline\: dropback\_rate | \[92\.4\%\, 99\.2\%\] \(ok\) | baseline\=98 | no | 1000 \/ 0 |
| Down 4\, long | baseline\: success\_rate | \[22\.7\%\, 39\.8\%\] \(ok\) | baseline\=98 | no | 1000 \/ 0 |
| Down 4\, long | baseline\: epa\_per\_play | \[\-1\.038\, \-0\.052\] \(ok\) | baseline\=98 | no | 1000 \/ 0 |
| Down 4\, long | difference\: dropback\_rate\_pp | unavailable \(insufficient\_games\) | baseline\=98\; selected\=4 | yes | 975 \/ 25 |
| Down 4\, long | difference\: success\_rate\_pp | unavailable \(insufficient\_games\) | baseline\=98\; selected\=4 | yes | 975 \/ 25 |
| Down 4\, long | difference\: epa\_per\_play | unavailable \(insufficient\_games\) | baseline\=98\; selected\=4 | yes | 975 \/ 25 |

Source: uncertainty.overall and uncertainty.situations, matched by down/distance. Undefined draws are counted and excluded; available intervals condition on defined draws. The status ok means available under this method, not reliable inference. A displayed narrow/rounded interval is not certainty; consult full-precision JSON. Five-game and 95%-valid gates withhold unsupported results; few_games warns below 20 on any required side.

## Source and provenance

Recorded metadata from the supplied report, not revalidated by this renderer. The report fingerprint identifies its canonical JSON content, not an authenticity signature.

| Report field | Recorded value |
| --- | --- |
| source\.label | nflverse 2024 retrospective snapshot\; acquired 2026\-09\-30 UTC |
| source\.sha256 | 6ae564c2c49378ec531303292966caee596982278b9fcdad9c9dd0a0dc16bfa7 |
| source\.snapshot\.archive\.sha256 | 23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06 |
| source\.snapshot\.archive\.size\_bytes | 19362351 |
| source\.snapshot\.decoded\_csv\.sha256 | 6ae564c2c49378ec531303292966caee596982278b9fcdad9c9dd0a0dc16bfa7 |
| source\.snapshot\.decoded\_csv\.size\_bytes | 99483794 |
| source\.snapshot\.license\.attribution | nflverse play\-by\-play data |
| source\.snapshot\.license\.identifier | CC\-BY\-4\.0 |
| source\.snapshot\.license\.modifications | Archive retained byte\-for\-byte\; no data transformations\. |
| source\.snapshot\.license\.source\_url | https\:\/\/github\.com\/nflverse\/nflverse\-data\/blob\/main\/LICENSE\.md |
| source\.snapshot\.license\.url | https\:\/\/creativecommons\.org\/licenses\/by\/4\.0\/ |
| source\.snapshot\.retrieved\_at\_utc | 2026\-09\-30T00\:19\:00\.168819\+00\:00 |
| source\.snapshot\.schema\_version | 1 |
| source\.snapshot\.season | 2024 |
| source\.snapshot\.source\.asset\_id | 512957856 |
| source\.snapshot\.source\.asset\_name | play\_by\_play\_2024\.csv\.gz |
| source\.snapshot\.source\.asset\_updated\_at\_utc | 2026\-08\-13T12\:26\:27Z |
| source\.snapshot\.source\.download\_url | https\:\/\/github\.com\/nflverse\/nflverse\-data\/releases\/download\/pbp\/play\_by\_play\_2024\.csv\.gz |
| source\.snapshot\.source\.release\_api\_url | https\:\/\/api\.github\.com\/repos\/nflverse\/nflverse\-data\/releases\/tags\/pbp |
| source\.snapshot\.source\.release\_id | 58152862 |
| source\.snapshot\.source\.release\_tag | pbp |
| source\.snapshot\.source\.sha256 | 23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06 |
| source\.snapshot\.source\.size\_bytes | 19362351 |

Transformation: this brief summarizes the supplied cohort metrics from the recorded snapshot; the renderer does not change raw data. Snapshot license attribution and source URLs are recorded above.

## Row accounting

| Report field | Recorded count \/ value |
| --- | --- |
| data\_quality\.eligible\_rows\_all\_teams | 34902 |
| data\_quality\.eligible\_rows\_outside\_cohort | 33918 |
| data\_quality\.excluded\_rows\_by\_reason\.missing\_play\_type | 1446 |
| data\_quality\.excluded\_rows\_by\_reason\.non\_run\_pass | 12996 |
| data\_quality\.excluded\_rows\_by\_reason\.two\_point\_attempt | 148 |
| data\_quality\.input\_rows | 49492 |

| Baseline field | Recorded count \/ value |
| --- | --- |
| league\_comparison\.data\_quality\.eligible\_rows\_same\_season\_type\_before\_week | 33335 |
| league\_comparison\.data\_quality\.excluded\_selected\_team\_rows | 984 |
| league\_comparison\.data\_quality\.filter\_order | \[\] |
| league\_comparison\.data\_quality\.plays\_after\_context\_filters | 32351 |
| league\_comparison\.data\_quality\.plays\_before\_context\_filters | 32351 |

Filter-stage counts are conditional on prior survivors. Removals are already included in outside-cohort counts; do not add nested counts or the baseline ledger to the source totals again.

## Limitations and report warnings

Eligible completed run/pass plays only: kneels, spikes, conversions, non-run/pass and nullified/no-play outcomes are excluded. Designed runs are an outcome-based proxy, not film-verified intent. Personnel, motion and opponent strength are not controlled. Upstream EPA-model uncertainty, revisions and historical information availability are not resolved by a week cutoff or bootstrap.

### report.warnings

- Descriptive completed\-play tendencies\; no opponent adjustment or causal claims\.
- Week filtering does not reconstruct historical source availability or EPA model training\.

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
