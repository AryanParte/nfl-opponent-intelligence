# Personnel and motion availability decision

Reviewed 2026-10-08. **P1.3 is complete within its play-by-play-only scope.** The
historical brief works; personnel packages and motion rates are explicitly
deferred enrichment, not implemented features. No supplementary data was acquired
or joined, no paid source was accessed, and existing reports are unchanged.

## What the pinned artifact actually contains

The [replayable field inventory](evidence/pbp-2024-23370d5d10f8.availability.json)
audits the existing 2024 snapshot: 372 columns, 49,492 raw rows, and 34,902 eligible
run/pass plays across REG and POST, with no week cutoff. It retains the full
manifest, archive hash, decoded CSV hash, and source attribution. Eligibility is
the existing adapter's policy, not a new definition of plays.

| Candidate concept | Exact fields checked | Observed in pinned PBP | Decision |
| --- | --- | --- | --- |
| Personnel composition | `offense_personnel`, `defense_personnel`; offense/defense player and position lists | All six columns absent | No package rates or player-derived personnel |
| Detailed formation | `offense_formation`, `qb_location` | Both absent | Do not reconstruct formations from another indicator |
| Motion / related charting | `is_motion`, `is_play_action`, `is_rpo`, `is_no_huddle` | All absent | No motion, play-action, or RPO measurements |
| Backfield / box counts | `n_offense_backfield`, `n_defense_box` | Both absent | Not personnel composition even if later supplied |
| Shotgun / tempo indicators | `shotgun`, `no_huddle` | Both present and non-missing on all eligible plays | Direct indicators of their own concepts, not motion/personnel proxies; no new report support |
| Play descriptions and locations | `desc`, `pass_location`, `run_location`, `run_gap` | Present, with location missingness | Not a pre-snap personnel/motion measurement; no text inference |

For the two numeric binary context fields, independently checked counts are:

| Field and population | Rows | Zero | One | Missing | Other code |
| --- | ---: | ---: | ---: | ---: | ---: |
| `shotgun`, raw | 49,492 | 22,822 | 26,670 | 0 | 0 |
| `shotgun`, eligible | 34,902 | 10,199 | 24,703 | 0 | 0 |
| `no_huddle`, raw | 49,492 | 44,656 | 4,836 | 0 | 0 |
| `no_huddle`, eligible | 34,902 | 30,504 | 4,398 | 0 | 0 |

Raw denominators include administrative and excluded rows; they are not play-call
rates. The [PBP dictionary][pbp-dictionary] documents these binary fields separately
from pass/run location. Shotgun says nothing by itself about RB/TE composition;
tempo does not establish whether somebody moved before the snap. Locations are
play descriptions, not motion paths. These distinctions are our measurement-scope
decision, not a validation of upstream charting accuracy.

Only the 20 exact names in `availability.CANDIDATE_FIELDS` are inventoried. This
does not prove the absence of every possible alias or external source. Non-missing
text is not necessarily valid charting. An absent column has
`column_present: false` with null population summaries; a present column can have `all_missing`,
`no_rows`, or `observed` status. Neither missing nor absent means false/zero.
Unknown numeric codes in `shotgun`/`no_huddle` count as `other`, not false. The audit
does not add any candidate to the analytical adapter's accepted optional fields.

## Supplementary sources: documented availability, not validated coverage

Primary documentation and source code were inspected at nflreadr commit
`23f915a5be30415aeaa0c5c80cd23b2c69cda122`. These are separate datasets; a column
in their dictionary does not make it present in `play_by_play_2024.csv.gz`.

| Dataset | Useful documented fields | Timing and scope | Recorded terms |
| --- | --- | --- | --- |
| nflverse participation | Personnel strings, formation, player/position lists | 2016 onward; 2023+ supplied by FTN after the postseason, not an in-season feed | CC BY-SA 4.0; 2023+ credit FTN Data via nflverse, earlier credit NFL NextGenStats via nflverse |
| FTN charting via nflverse | `is_motion`, `is_play_action`, `is_rpo`, `qb_location`, backfield/box counts | Public subset from 2022 onward; documentation says charted within 48 hours of a game | CC BY-SA 4.0; credit FTN Data via nflverse |

See the immutable [participation loader][participation-loader] and
[dictionary][participation-dictionary], and [charting loader][charting-loader]
and [dictionary][charting-dictionary]. Participation identifies who/which positions
were on the field; it is not continuous tracking. FTN's motion flag combines
movement before **or** at the snap. It cannot alone isolate at-snap motion, its
type, trajectory, or speed. A backfield count is not a count of running backs.

The stated 48-hour charting schedule is not a measured publication SLA or evidence
that a particular row was available before a historical cutoff. Present-day files
may be revised. Recent participation's end-of-season delivery disqualifies it as
an assumed in-season historical feature source. Retrospective analysis remains a
separate possibility, clearly labeled as such.

On 2026-10-08 the release APIs listed these CSV assets:

| Release | Asset / ID | Bytes | Upstream update time |
| --- | --- | ---: | --- |
| [Participation release][participation-release] | `pbp_participation_2024.csv` / `289570937` | 49,688,308 | 2025-09-04 10:24:49 UTC |
| [Charting release][charting-release] | `ftn_charting_2024.csv` / `288253517` | 8,254,908 | 2025-09-01 01:29:37 UTC |

The API-advertised SHA-256 values were respectively
`b1f436a98b2a7759eb4ed1181e072a35c2666f9aeb356a49c943d28d6be6b0b9` and
`6faae8118cc13ce62589210d553733128ed35e558671009b4a7a8fc5c674c2cb`.
**These bytes were not downloaded or hashed locally.** Metadata confirms a listed
candidate asset, not its schema, completeness, joins, missingness, or historical
availability. Release URLs are mutable; any future acquisition must verify and
pin the actual bytes separately. An asset update time is not a row availability time.

## Licensing boundary

The existing PBP manifest records CC BY 4.0; the
[nflverse-data repository license][pbp-license] was rechecked at commit
`a78da18ca93f167bd0a2af274df48f539fa4153c`. Do not copy that notice onto FTN data:
the dataset-specific loaders above state **CC BY-SA 4.0**, a different license.
Preserve source-specific credit, license links, provenance and modification notices
separately if adding an enrichment.

The [Creative Commons summary][cc-by-sa] describes attribution and ShareAlike
conditions for distributed adaptations, and warns that additional rights may
matter. A future redistribution/export design must review the
[actual legal code][cc-code] and the intended combined artifact before release;
this audit does not decide that every computed statistic or all application code
inherits ShareAlike. It is a conservative engineering scope record, not legal
clearance. No repository license has been changed.

NGS tracking, competition-specific Big Data Bowl data, and commercial charting
are outside this audit's acquired inputs. No tracking access or redistribution
rights were established. Review the particular dataset's terms and get approval
for paid/access-controlled sources before expanding that scope.

## Reproduce and interpret the audit

Requires the already recorded snapshot locally. This command verifies both byte
representations, validates the existing PBP contract, and prints aggregate JSON:

```sh
snapshot_dir=data/raw/nflverse/pbp/2024/23370d5d10f8104d80d46a1fc5e61f4f6f5a3263fe96fe2dd629913cfcb08c06
PYTHONPATH=src python3 -m opponent_intelligence.availability --snapshot "$snapshot_dir" \
  | cmp - docs/evidence/pbp-2024-23370d5d10f8.availability.json
PYTHONPATH=src python3 -m unittest discover -s tests -p test_availability.py -v
```

`cmp` exits zero when output matches. The audit never fetches, follows
`current.json`, edits the cache, scans descriptions for motion, or changes report
denominators. It shares the adapter's eligible identities; it is not independent
validation of that adapter. A separate raw-record check during this run reconciled
all candidate counts using direct run/pass/flag selection and numeric comparisons.
Fourteen synthetic tests cover missing/absent/zero/empty distinctions, excluded-row
coverage, invalid numeric flags, exact names, unvalidated text, both season types,
duplicate/ragged input, corrupt snapshots, BOM fingerprints, deterministic counts,
and offline all-or-nothing CLI behavior. No real data or network is required in CI.

## Acceptance and next unit

P1.3 delivers role-labeled historical briefs, context filters, matched baselines,
explicit support/uncertainty states, provenance and examples. This audit satisfies
its remaining availability/licensing decision; it does **not** implement personnel
or motion analytics. The inference/calibration and historical-availability limits
in [UNCERTAINTY.md](UNCERTAINTY.md) and [BRIEFS.md](BRIEFS.md) remain.

Next: the first P1.4 FastAPI slice over the existing report builder, using one
explicitly configured immutable local snapshot (plus a synthetic test fixture).
Define and test request validation, report-schema-v2 responses, bounded expensive
options, and stable invalid-input errors. No request-selected filesystem paths,
automatic downloads, database, frontend, or deployment in that first unit. Keep
the core offline CLI working without API dependencies.

If enrichment is prioritized later, treat it as a separate reviewed unit:

1. Pin its own manifest, notices, retrieval time and bytes; keep datasets separate.
2. Audit key uniqueness and left-join to eligible PBP without dropping unmatched
   plays: participation `(nflverse_game_id, play_id)` or charting
   `(nflverse_game_id, nflverse_play_id)` to PBP `(game_id, play_id)`.
   Never join on the source-specific FTN IDs or concatenate uncertain aliases.
3. Reconcile coverage/missing/invalid values by team, week and play type before
   reporting rates. A rate denominator must be eligible **observed valid flags**,
   with unknown and unmatched counts reported separately; missing never becomes 0.
4. Specify field semantics and release-time evidence; distinguish retrospective
   description from pregame-available features. Review redistribution obligations
   for the intended output before publishing enriched examples or downloads.

[pbp-dictionary]: https://github.com/nflverse/nflreadr/blob/23f915a5be30415aeaa0c5c80cd23b2c69cda122/data-raw/dictionary_pbp.csv
[participation-loader]: https://github.com/nflverse/nflreadr/blob/23f915a5be30415aeaa0c5c80cd23b2c69cda122/R/load_participation.R
[participation-dictionary]: https://github.com/nflverse/nflreadr/blob/23f915a5be30415aeaa0c5c80cd23b2c69cda122/data-raw/dictionary_participation.csv
[charting-loader]: https://github.com/nflverse/nflreadr/blob/23f915a5be30415aeaa0c5c80cd23b2c69cda122/R/load_ftn_charting.R
[charting-dictionary]: https://github.com/nflverse/nflreadr/blob/23f915a5be30415aeaa0c5c80cd23b2c69cda122/data-raw/dictionary_ftn_charting.csv
[participation-release]: https://api.github.com/repos/nflverse/nflverse-data/releases/tags/pbp_participation
[charting-release]: https://api.github.com/repos/nflverse/nflverse-data/releases/tags/ftn_charting
[pbp-license]: https://github.com/nflverse/nflverse-data/blob/a78da18ca93f167bd0a2af274df48f539fa4153c/LICENSE.md
[cc-by-sa]: https://creativecommons.org/licenses/by-sa/4.0/
[cc-code]: https://creativecommons.org/licenses/by-sa/4.0/legalcode.en
