# FTN-to-PBP coverage audit

Reviewed 2026-11-02. This second bounded **P1.7** slice joins the already acquired
[FTN artifact](FTN_CHARTING_AUDIT.md) to the existing verified PBP snapshot **offline**.
All 34,902 eligible 2024 REG+POST PBP plays match exactly one FTN row. Matching does
not establish charting accuracy, field applicability or pregame availability.
No field, play family or feature rate is admitted to Scout or Decision Lab.

**Follow-up, 2026-11-03:** the [field admission policy](FTN_FIELD_POLICY.md) now
records explicit defer decisions and tests the PBP-only consumer boundary. The
next unit is P1.8's Decision API; the evidence in this coverage receipt is unchanged.

## Reproducible sources

The [aggregate receipt][receipt] embeds the two original manifests, separately
retaining source attribution, license, retrieval and asset-update times. No data
was downloaded or refreshed for this audit. It hashes the same decoded bytes it
parses, after the existing snapshot verifiers have checked integrity.

| Source | SHA-256 |
| --- | --- |
| PBP gzip | `23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06` |
| Decoded PBP CSV | `6ae564c2c49378ec531303292966caee596982278b9fcdad9c9dd0a0dc16bfa7` |
| FTN CSV | `6faae8118cc13ce62589210d553733128ed35e558671009b4a7a8fc5c674c2cb` |

FTN's manifest still records `joined_to_pbp: false` as the original acquisition
boundary. It is preserved, not rewritten to describe this later derived audit.
This receipt records the join separately. Extraction/update/retrieval timestamps
are not first-publication or row-level information-availability timestamps.

FTN-derived counts in this document and the receipt are attributed to **FTN Data
via nflverse** under [CC BY-SA 4.0][sa]; the PBP contribution is attributed to
**nflverse play-by-play data**, [CC BY 4.0][by]. The combined aggregate receipt is
offered under CC BY-SA 4.0. Modification: aggregate join/coverage/encoding counts;
no row-level redistribution. No endorsement is implied. Source CSVs and retained
notices stay in the ignored immutable caches. This scoped aggregate audit does
not authorize future enriched downloads or change the software's license.

## Join and denominator contract

`validation/ftn_coverage.py` reuses the production PBP loader for eligibility,
exclusions, typed plays and dropbacks. The only additional PBP parse builds a raw
key set, so a charted administrative/excluded play is not confused with a missing
PBP record. The FTN CSV parser is shared with the previous contract audit.

- Match `(game_id, play_id)` to `(nflverse_game_id, nflverse_play_id)`; FTN's own
  IDs are a separate namespace. Both source key domains must be complete and unique.
- Normalize numeric IDs exactly, including whole `.0` forms. Reject ambiguous
  duplicate, missing/invalid keys, inconsistent game/season/week, malformed CSV or
  a non-2024 snapshot. No first-row deduplication, fuzzy matching or repairs.
- Left-join **every eligible PBP play** to zero or one FTN row. Missing EPA does
  not exclude a play from coverage. Retain non-matches in denominators.
- **Run** is an eligible non-dropback; **Pass** includes sacks and scrambles.
  This snapshot contains 19,897 raw pass rows plus 1,133 raw run/dropback rows,
  so using raw `play_type` would misclassify the latter.
- Group by offense team or defense team, season type, week and candidate. Defense
  groups describe the opposing offense's call; they are not defensive calls.
  Do not add offense and defense views together: each separately partitions PBP.
- Counts are retrospective, pooled over the full 2024 REG+POST snapshot. No
  historical cutoff, predictive evaluation, causal effect or feature rate is claimed.

| Population | Plays | Games | Matched | Unmatched |
| --- | ---: | ---: | ---: | ---: |
| All eligible PBP | 34,902 | 285 | 34,902 | 0 |
| Run | 13,872 | 285 | 13,872 | 0 |
| Pass / dropback | 21,030 | 285 | 21,030 | 0 |

Raw PBP has 49,492 rows; 1,446 lack a play type, 12,996 have excluded play types,
and 148 are two-point attempts under the loader's ordered exclusion policy.
FTN has 48,031 rows: 34,902 match eligible PBP, 13,129 match excluded PBP, and
zero lack a raw PBP counterpart. There are 1,461 raw PBP rows without FTN, all
outside the eligible cohort. This is coverage against these two snapshots,
not an independently reconciled NFL schedule or proof of complete charting.

## Field states and findings

For each of 22 contextual fields, overall and candidate summaries partition
**all eligible plays** into the following disjoint states. These are encoding/
domain checks, not counts of applicable, observed football measurements.

| State | Meaning |
| --- | --- |
| `unmatched` | No FTN row for this PBP key; distinct from every matched-row state |
| `absent_column` | Matched row, but this field is absent from the FTN header |
| `missing_value` | Matched field is exactly blank or `NA` |
| `unknown_code` | Hash, QB location or read code is outside its pinned 2024 dictionary domain |
| `invalid_value` | Flag is not literal `TRUE/FALSE`, or a count fails the audit's exact integer 0–11 check |
| `recognized_code` | Token is in the dictionary domain; applicability remains unverified |
| `integer_0_to_11` | Encoding/range only for backfield/box/blitzer/pass-rusher counts, including zero |
| `literal_true` / `literal_false` | Literal flag encoding; neither implies a validated measurement denominator |

The numeric 0–11 check is an explicit audit plausibility bound for player counts,
not a new upstream guarantee. It does not resolve zero's field-specific meaning
or whether an exceptional play should fall outside that range. Unknown or invalid
values remain counted; nothing is silently set to zero, false or a valid family.

| Eligible field issue | Run | Pass | Total |
| --- | ---: | ---: | ---: |
| Undocumented `qb_location=0` | 40 | 228 | 268 |
| Undocumented `starting_hash=0` | 35 | 229 | 264 |
| Pass-rusher count outside audit range (`45`) | 0 | 1 | 1 |

There are no absent columns or blank/NA values on eligible rows, and all 15 flags
have recognized boolean encodings. That does **not** make their negative values
applicable evidence. Hash and QB-location issue populations can overlap; do not
add field totals to infer the number of distinct affected plays. Another 11,337
unknown hash and 11,337 unknown QB-location values occur on excluded PBP rows.
The zero code therefore is not confined to ineligible/special-team situations.

The receipt contains **2,280 observed role/team/season-type/week/candidate groups**.
Each compact JSON row follows `stratum_columns`, retaining play/game support,
matched play/game support and unmatched plays. Its sparse `field_issues` mapping
counts absent/missing/unknown/invalid states only; an omitted issue means zero
for that observed group, not a validated measurement. Full encoding partitions
remain in `overall` and `by_candidate`. No synthetic groups are generated for
bye weeks or unobserved team/candidate combinations. Empty cohorts have zero
counts, never an invented rate. Game support is not additive across candidates.

## What the producer inspection establishes

Inspected [nflverse-ftn's transformation][producer], [API reader][api],
[update script][update], [producer dictionary][producer-dictionary] and [MIT
notice][mit] at commit `8ba8955b93856cabc9c50ca25d6d3812adb45ae3`.
The transformation's Git blob is `7d7e6ca7d1819c274728a4d9f728ed33c2d8ef9c`.
No upstream implementation was copied, installed or executed; no credentialed FTN
endpoint was accessed. This source inspection is not build attestation for the
2025 asset. The newer pinned nflreadr dictionary remains the code-domain reference,
including its season-specific explanation of `read_thrown=0`.

The inspected transformation replaces empty strings with NA, passes hash/QB
position through, converts flags through integer/logical representations and
records extraction time. It does not provide a per-field applicability mask or
document an interpretation for the unknown hash/QB zero codes. It also does not
show a blanket NA-to-false replacement. This narrows the cause: the audited CSV's
false/zero values cannot simply be blamed on that transformation filling all
missing values. It does **not** resolve how the upstream charting/API assigns
defaults, non-applicable values or true negative observations.

The updater replaces rows for refreshed games and republishes season files.
It is not an append-only revision history or proof of when each observation first
became public. Retrospective joins cannot establish leakage-safe replay.

## Reproduce and verification

From the canonical clone, using existing explicit snapshots; **no network**:

```sh
pbp_snapshot=data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06
ftn_snapshot=data/raw/nflverse/ftn_charting/2024/6faae8118cc13ce62589210d553733128ed35e558671009b4a7a8fc5c674c2cb
PYTHONPATH=src python3 -m validation.ftn_coverage \
  --pbp-snapshot "$pbp_snapshot" --ftn-snapshot "$ftn_snapshot" \
  | cmp - docs/evidence/ftn-2024-6faae8118cc1-pbp-23370d5d10f8.coverage.json
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_ftn*.py' -v
```

`--output` creates a new file exclusively. Corrupt snapshots or failed joins
produce no partial JSON, never trigger downloads and never edit source manifests.
With a different truthful acquisition time, compare hashes/counts/source identity
separately; do not copy a past timestamp to manufacture byte-for-byte replay.

Eighteen new offline tests use invented inputs for join cardinality, key namespaces,
exact IDs/context, exclusions, missing EPA, unmatched/absent/missing/unknown/invalid
states, Run/Pass and defensive interpretation, empty/postseason groups, bounds,
source identity, deterministic order, receipt partitions and no-clobber output.
CI reads only aggregate evidence, never the real CSV. A separate raw CSV/Decimal
calculation, importing no audit/production selectors, reconciled joins, candidate
counts, every stratum's plays/games and all issue counts. See [STATUS](STATUS.md)
and the [learning log](../LEARNING_LOG.md) for final project checks/self-review.

## Admission follow-up

The [2026-11-03 field policy](FTN_FIELD_POLICY.md) completes the planned
field-by-field admission/defer review, with explicit applicability, null states,
candidate denominators and regression tests. All 22 contextual fields remain
audit-only. Advance to P1.8's **PBP-only decision endpoint**; do not repeat this
acquisition/join audit or infer play families from proxies. No production charting,
model/ranking or new source is implied by this completed coverage gate.

[receipt]: evidence/ftn-2024-6faae8118cc1-pbp-23370d5d10f8.coverage.json
[sa]: https://creativecommons.org/licenses/by-sa/4.0/
[by]: https://creativecommons.org/licenses/by/4.0/
[producer]: https://github.com/nflverse/nflverse-ftn/blob/8ba8955b93856cabc9c50ca25d6d3812adb45ae3/R/nflverse.R
[api]: https://github.com/nflverse/nflverse-ftn/blob/8ba8955b93856cabc9c50ca25d6d3812adb45ae3/R/api.R
[update]: https://github.com/nflverse/nflverse-ftn/blob/8ba8955b93856cabc9c50ca25d6d3812adb45ae3/exec/update_ftn.R
[producer-dictionary]: https://github.com/nflverse/nflverse-ftn/blob/8ba8955b93856cabc9c50ca25d6d3812adb45ae3/ftn_data_dictionary.csv
[mit]: https://github.com/nflverse/nflverse-ftn/blob/8ba8955b93856cabc9c50ca25d6d3812adb45ae3/LICENSE.md
