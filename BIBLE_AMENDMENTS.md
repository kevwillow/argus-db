# Argus — Bible Amendments Log

This file is the audit trail for every in-place edit to `PROJECT_BIBLE.md`. Per user instruction (MAC-1 comment [5d75988d](/MAC/issues/MAC-1#comment-5d75988d-c267-4e0d-982c-0007a6f2fa36) on 2026-05-04):

- Every in-place bible edit pairs with an amendment-log entry.
- Sub-agent-level rule additions and interpretive guidance also go here, even when they do not modify the bible text itself.
- Each amendment entry must link the git commit that applied the change.

**SAR convention.** A "SAR" (Sub-Agent Rule) entry captures interpretive guidance, clarifications, or rules that bind one or more sub-agents but do not warrant editing the bible text. Use a SAR when the bible's existing wording is correct as written and the additional guidance is contextual, illustrative, or operational rather than contractual. SAR entries live in the **Sub-agent rule additions and interpretive guidance** section below, are numbered SAR-1, SAR-2, …, and identify the sub-agent(s) they bind.

The bible itself is the contract; this file is the changelog.

---

## Correction Pass 1 — Talos export integration

**Date:** 2026-05-04
**Commit:** `26e44a3` — `docs(bible): correction pass — Talos export schema, severity mapping, false-positive guards`
**Source:** MAC-1 user comment [ab234b68](/MAC/issues/MAC-1#comment-ab234b68-9876-4ee9-9eb4-f2d9c3d0a7d8)
**Status:** Acknowledged and approved by user in MAC-1 comment [5d75988d](/MAC/issues/MAC-1#comment-5d75988d-c267-4e0d-982c-0007a6f2fa36)

### Corrections applied

1. **§4.4 (new)** — Talos export type-mapping table. `oui`/`mac`/`bssid`/`ssid_exact`/`ble_uuid` direct-pass; `ble_service`→`ble_uuid`; `ssid_pattern`/`device_fingerprint` dropped; `mac_range` expanded only if ≤256 entries; coverage report tallies the drops.
2. **§4.5 (new)** — Severity derived from `device_category`, NOT from confidence. high: imsi_catcher / alpr / covert_cam / hacking_tool / gps_tracker / face_recog. med: drone_detect / body_cam / drone. low: police_radio / gunshot_detect. Procurement-only records never exported to Talos.
3. **§7.5** — Talos-export per-record description format: ≤80 chars, no URLs, no "see source", `{vendor} {product family} ({short context})`; truncation falls back to `{category} device`.
4. **§8.4** — `device_category='unknown'` never exported to Talos under any confidence level. Pi self-exclude OUI list hard-coded: `b8:27:eb`, `dc:a6:32`, `e4:5f:01`, `28:cd:c1` (banned from high-confidence export; allowed in standard at `severity=low` only).
5. **§7.3 + §7.4** — Enumerated fake-MAC reject list: RFC 7042 IPv4 (`00:00:5e:00:53:00`–`ff`) and IPv6 (`02:00:5e:10:00:00:00:01`–`ff`) doc ranges, common patterns (`aa:bb:cc:dd:ee:ff`, `de:ad:be:ef:*:*`, `ca:fe:ba:be:*:*`, `ba:db:00:b5:*:*`, all-zero, all-ones, etc.), all-identical-octet MACs, strictly monotonic +1 octet sequences. Validator routes matches to `conflicts` with `reason='known_fake_pattern'`.
6. **§7.3** — LAA-bit confidence penalty: scraped MACs with the locally-administered bit set (bit 1 of the first octet) get `confidence ≤ 40` and a `lab_bit_set` note unless the source explicitly attests broadcast use. (See sub-agent rule below for the corrected interpretation of the example list.)
7. **§6 Phase 3** — New Step-0 WiGLE budget estimate; new 🛑 **Checkpoint 3a** sub-checkpoint blocks WiGLE queries until human approves the budget plan.
8. **§7.5** — Talos export JSON file shape: `_meta` block (`argus_version`, `exported_at`, `record_count`, `confidence_threshold`, `argus_run_id`, `source_record_count`, 7-key `dropped_in_export`); `entries` shape with `argus_record_id` stable across re-runs for downstream upsert semantics.
9. **§11** — New hard-rules don'ts: #12 (Pi OUI ban from high-conf), #13 (`unknown` category never exported), #14 (procurement-only never exported). #11 left as a `(reserved)` placeholder to keep the user-prescribed numbering of #12/#13/#14 stable.
10. **§9** — Deliverables expanded to 5 files; new item 9 requires "Dropped from Talos export" tally that reconciles `source_record_count − sum(dropped) = entries.length` against the §7.5 `_meta.dropped_in_export` keys.

### Internal-consistency reconciliations applied during the read

- **§6 Phase 5 step 5 file descriptions** were stale relative to §9 item 2; updated to match (`argus_export.json` = "all confidences ≥30, applies §4.4/§4.5"; `argus_export_high_confidence.json` = "confidence ≥70").
- **§7.5 Don'ts** wording for the confidence floor was ambiguous; reworded to "do not export <30 to *any* Talos export file" so the §9 item 2 ≥30 floor is enforced everywhere.

### §12 Open Questions impact

Resolved by this pass (struck through in §12):
- Confidence threshold for default scanner export → 70 high-conf, 30 standard.
- Output file naming → `argus.db`, `argus_export.json`, `argus_export_high_confidence.json`, `argus_export.csv`.

New open question added by Correction 8 review:
- Does Talos's seeder need to support `argus_record_id` stable-id upsert in v0.2, or can re-imports be destructive (drop-and-reload)?

---

## Correction Pass 2 — §11 #11 placeholder filled with bible-amendment-log discipline

**Date:** 2026-05-04
**Commit:** `1cfbbd4` — `docs(bible): fill §11 #11 placeholder — bible amendment log discipline`
**Source:** MAC-1 user comment [f08cd82b](/MAC/issues/MAC-1#comment-f08cd82b-747e-4b34-aa6a-11bbfd0cc067) decision #4
**Status:** Applied as a normal in-place edit; logged here per §11 #11 (now self-binding).

### Correction applied

1. **§11 #11** — replaced the `(reserved)` placeholder with:

   > **Do not skip the `BIBLE_AMENDMENTS.md` log entry when making in-place bible edits or adding sub-agent-level rules.** The git diff is the source of truth, but the amendment log is the human-readable trail. An undocumented amendment is a process violation regardless of whether the edit itself is correct.

   This makes BIBLE_AMENDMENTS discipline a Critical Don't, on par with the other §11 hard rules. Numbering of #12/#13/#14 is unchanged (placeholder fill, not insertion).

### Why this is a single-entry pass

This pass touches a single line of bible text. The user explicitly authorized it as a one-line correction (decision #4 of the f08cd82b sign-off) and asked that it nonetheless be logged here so the meta rule is itself documented under the very discipline it codifies — preserving the audit-trail invariant from heartbeat zero.

### §12 Open Questions impact

None. §12 unchanged.

---

## Correction Pass 3 — §2.1 in-vehicle LTE/WiFi routers + §12 device_cluster_id question

**Date:** 2026-05-04
**Commit:** `76231f0` — `docs(bible): correction pass 3 — §2.1 in-vehicle LTE/WiFi routers + §12 device_cluster_id`
**Source:** MAC-1 user comment [d08ee4a8](/MAC/issues/MAC-1#comment-d08ee4a8-e525-4c19-9886-89f0f95bf1c3)
**Status:** Approved by user in the same comment ("Approved as Correction Pass 3"). Bible edit applied; manufacturers seed updated (32 → 34); device_cluster_id question added to §12; research leads logged in PROJECT_STATE.md per same comment.

### Corrections applied

1. **§2.1 (new #5)** — Added `In-vehicle LTE/WiFi routers` as a new device category between old #4 (police radios) and old #5 (police drones). Vendors named: **Cradlepoint** (IBR900-series, R1900-series mobile routers) and **Sierra Wireless** (AirLink GX/RV-series, MG90 mobile routers). Rationale: every modern patrol car carries an in-cabin LTE+WiFi router as the data link for laptops, dashcams, and body-cam offload. This is a distinct emitter class from §2.1 #4 police radios — different physics (LTE+WiFi vs P25/VHF), different vendors, different form factor. Conflating them under "police radios" would have muddied the per-category coverage report.

2. **§2.1 placement choice — option (b) over option (a).** User offered both: (a) extend §2.1 #4 to "Police radios and in-vehicle communications" or (b) insert a new §2.1 category between #4 and #5. Chose **(b)**: each §2.1 row should map to one emitter class with consistent radio physics. The user themselves noted "in-vehicle routers aren't radios" — option (a) would have permanently encoded that semantic conflation; option (b) costs only a one-time renumber. Renumber: old §2.1 #5 → #6, #6 → #7, #7 → #8, #8 → #9, #9 → #10, #10 → #11, #11 → #12.

3. **§12 (Open Questions)** — Added `device_cluster_id` design question: "Should the schema add a `device_cluster_id` column to support correlating multiple emitters to one vehicle/operator (e.g., 6 MACs = 1 patrol car = APX radio + Cradlepoint router + Axon dashcam + Getac laptop + body cam + driver phone), or leave clustering to scanner-side logic?" User's initial lean is scanner-side (Argus = identifiers, Talos = correlation). Held for explicit decision; surface at Checkpoint 5 if unresolved.

### Out-of-bible artifact updates that pair with this pass

- **`db/migrations/0001_initial.sql`** — added Cradlepoint + Sierra Wireless seed rows (manufacturers count 32 → 34); renumbered §2.1 # references throughout the seed comments (old #5–#11 bumped to #6–#12, including Rekor's combined `#1, #10` reference → `#1, #11`). Both new vendor rows use `primary_category=NULL` because the §4.1 device_category enum does not yet have an `in_vehicle_router` value (pattern mirrors Motorola Solutions / L3Harris multi-purpose entries). Verified by re-running `init_db.py` (clean rebuild), `argus_cli.py status` (manufacturers: 34), and `pytest tests/` (25/25 pass).
- **`PROJECT_STATE.md`** — added a "Research leads" section per user direction in the same comment: Flock SSID-pattern hunt (Phase 3/4), FCC grantee-prefix harvesting (Phase 3 alongside FCC ID workflow), and city council minutes / municipal procurement portals (Phase 3/4 alongside SAM.gov). Plus a fourth entry capturing the cop-car emitter cluster as standing context for Source Workers.

### §4.1 enum gap — deliberate non-correction in this pass

The §4.1 `device_category` enum does not have an `in_vehicle_router` value. Cradlepoint and Sierra Wireless are therefore seeded with `primary_category=NULL` (multi-purpose pattern). This is a known gap that will need a future Correction Pass when Phase 2/3 actually ingests the first router OUI/MAC. Left out of this pass intentionally because:

1. The user's directive scoped Correction Pass 3 to §2.1 + manufacturers seed + §12 device_cluster_id + research leads — not §4.1.
2. The enum is a CHECK constraint with downstream Talos export implications (§4.5 severity mapping is keyed on category). Touching it without a Phase 2 trigger would be premature.
3. Until Phase 2/3 finds a real Cradlepoint/Sierra OUI to ingest, the gap costs nothing — manufacturers seed alone doesn't insert into `identifiers`.

Tracked in PROJECT_STATE.md "Open questions for human" so it surfaces at the next relevant checkpoint.

### §12 Open Questions impact

Net add of one question (device_cluster_id). No struck-through resolutions in this pass.

### Why this is structurally a renumber pass

Option (b) was chosen for taxonomic clarity (each §2.1 item = one emitter class). The mechanical cost is a one-time renumber from old #5–#11 to new #6–#12 across:

- Bible §2.1 itself (lines 40–51 of `PROJECT_BIBLE.md`).
- Seed comments in `db/migrations/0001_initial.sql` (every `(§2.1 #N)` reference for vendors at old #5–#11).

References elsewhere were checked:

- `BIBLE_AMENDMENTS.md` — Correction Pass 1 mentions §2.1 in passing without item numbers.
- `PROJECT_STATE.md` — one historical-log reference to §2.1 #8/#9 (old numbering, describing the 32-vendor state at the time). Left unchanged as historical record; new entries use the post-pass numbering.
- `PROJECT_BIBLE.md` outside §2.1 — every other section references §2.1 categories by name (e.g., "every vendor in §2.1") rather than by number. No cascading rewrites needed.

DBArchitect's MAC-2 comments referencing old §2.1 # numbering are immutable run history and are not retroactively rewritten.

---

## Correction Pass 4 — §4.2 supporting-table addition: `deployment_observations`

**Date:** 2026-05-04
**Commit:** `d81de3b` — `docs(bible): correction pass 4 — §4.2 deployment_observations supporting-table addition`
**Source:** [MAC-5](/MAC/issues/MAC-5) SourceWorker schema-fit proposal comment [1037c17e](/MAC/issues/MAC-5#comment-1037c17e-48f4-4ab9-9df7-466af011dbbe); CEO ratification this heartbeat.
**Status:** Bible §4.2 edit applied this commit. Migration `db/migrations/0002_deployment_observations.sql` to be authored by SourceWorker on resume; the bible-at-HEAD is the authoritative shape the migration must match.

### Correction applied

1. **§4.2** — Added `deployment_observations` as a new supporting table to the bullet list (between `raw_observations` and `extraction_runs`). Tightened the existing `raw_observations` description to clarify it is the staging table for rows carrying an actual or candidate identifier from the §4.1 `identifier_type` enum — explicit so the new sister table's role is unambiguous.

   The bullet text:

   > **`deployment_observations`** — staging table for Tier 1 sources that yield agency × technology × location × vendor metadata but **no** MAC/OUI/SSID/UUID identifier (EFF Atlas of Surveillance, DeFlock). Identifier columns intentionally absent — promotion to `identifiers` requires a Phase 3+ inference linking a deployment to a concrete identifier candidate (§11 #1). Idempotency keyed by `(source_id, source_row_key)` where `source_row_key` is the source's stable per-row natural key (e.g. Atlas's `AOSNUMBER`).

### Why a new table, not a `raw_observations` extension

The MAC-5 SourceWorker proposal weighed two options: (A) extend `raw_observations` with a new `candidate_type='deployment_record'` value and a synthetic composite key in `candidate_identifier`, or (B) a dedicated `deployment_observations` table. Chose **(B)**:

1. **Schema honesty.** `raw_observations.candidate_identifier` is documented in `0001_initial.sql` as a *pre-normalization identifier* (real or candidate, drawn from the §4.1 enum). Atlas rows have no identifiers (§11 #1). Stuffing `eff_atlas:AOS000001` into `candidate_identifier` is a category error that pollutes every Phase 3/5 read of that column.
2. **Phase 3/5 query shape.** Phase 3 WiGLE radius queries and Phase 5 geographic + categorical corroboration want clean `WHERE state='TX' AND vendor_raw='Flock Safety'` joins, not `WHERE candidate_type='deployment_record' AND json_extract(notes,'$.state')='TX'`.
3. **MAC-6 absorbs cleanly.** DeFlock has the same shape (deployment metadata + lat/lon + vendor + agency). One additional table absorbs both Tier 1 deployment sources without a second schema decision.
4. **Bounded cost.** One additive migration, one row in `argus_cli status`, no main-table impact.
5. **Precedent.** §4.5 already carved `procurement_records` into a separate table for the same structural-honesty reason at MAC-2 / Phase 1 (option (a) in the DBArchitect proposal, signed off at Checkpoint 1). This is the same pattern: schema shape follows source shape; staging tables are not a single bag.

### Migration shape (worker-built; ratified here)

The migration file authored by SourceWorker (`db/migrations/0002_deployment_observations.sql`) creates `deployment_observations` with: `id`, `source_id` FK→`sources` (ON DELETE SET NULL), `extraction_run_id` FK→`extraction_runs` (ON DELETE SET NULL), `source_url` NOT NULL, `source_row_key` NOT NULL, `agency_name`, `agency_type`, `juris_type`, `city`, `county`, `state`, `country`, `lat`, `lon`, `technology_category`, `vendor_raw`, `citation_url`, `source_excerpt` (CHECK ≤200 chars), `captured_at` DEFAULT CURRENT_TIMESTAMP, `processed_at`, `notes` (JSON). Indexes on `source_id`, `extraction_run_id`, `state`, `vendor_raw`, `technology_category`. Unique index on `(source_id, source_row_key)` for idempotency. `INSERT OR IGNORE INTO schema_version (version, name) VALUES (2, '0002_deployment_observations')` bump.

No CHECK constraint on `technology_category` or `vendor_raw` — raw category strings vary across sources, canonical-name matching is Phase 5 inference, not staging-time coercion (§7.2).

### Out-of-bible observation — `procurement_records` is also missing from §4.2

While editing §4.2 for this pass, noted that `procurement_records` (created in MAC-2 / Phase 1 per §4.5 carveout, signed off at Checkpoint 1) was never reflected in the §4.2 enumeration. This is a documentation gap from CP1-era — predates this pass and is **not** corrected here. Surfaced for user judgment whether to roll a tidiness pass (e.g. CP5) or leave it as known historical drift; CEO is not editing it without explicit direction per the strategic-steers-as-soft-priors guidance.

### §12 Open Questions impact

None. §12 unchanged.

### Ratifications bundled with this CEO action (no bible text edit, but binding)

The MAC-5 ratification this heartbeat also locks in three operational decisions that travel with the migration but are not bible edits:

1. **`source_type='crowdsourced'`** for Atlas — per §8.2 confidence band 50–75 honestly reflects single-citation deployment claims from public reporting; aligns with the MAC-4 Wireshark `manuf` precedent.
2. **§11 #3 PII handling for Atlas Summary field** — redact `rank+name` patterns to `[REDACTED-PERSON]` markers in `notes` JSON before insert; preserve full Summary verbatim in `raw/eff_atlas/<ts>/` per §7.2; log redaction count + AOSNUMBER list in `extraction_runs.notes`. Phase 5 promotion runs a stricter pass.
3. **`source_url` per row** = the Atlas dataset URL (`https://atlasofsurveillance.org/download.csv`), not Atlas's per-row `Link 1` (which is the *external* journalistic citation Atlas itself cites — structurally distinct from "the source we are attributing to"). The DDL has a separate `citation_url` field for `Link 1`.

These are routine §8.2 / §11 #3 / §7.2 applications, not bible edits — so they ride in this CP4 entry as ratification context rather than as separate SARs.

---

## Correction Pass 5 — Phase 2 → Phase 3 ride-along: §4.1 in_vehicle_router enum + §4.5 severity + §4.2 procurement_records doc + §12 geographic_scope

**Date:** 2026-05-04
**Commit:** `b2a8dac` — `docs(bible): correction pass 5 — §4.1 in_vehicle_router + §4.5 severity + §4.2 procurement_records doc + §12 geographic_scope`
**Source:** [MAC-1](/MAC/issues/MAC-1) user comment [a7edae6f](/MAC/issues/MAC-1#comment-a7edae6f-6c7a-493e-82f2-fa088942a1a9) (Checkpoint 2 sign-off + Phase 3 dispatch decisions)
**Status:** Bible edits applied this commit; SAR-3 (separate entry below) ratifies the `device_cluster_id` lean as binding-but-not-final.

### Corrections applied

1. **§4.1 main-table `device_category` enum** — added `in_vehicle_router` between `police_radio` and `drone`. Bible enum now lists 12 §2.1-derived values (was 11). Pairs with §2.1 #5 (added in CP3) so the bible-text enum and §2.1's category list are in sync. The schema CHECK on `identifiers.device_category` in `db/migrations/0001_initial.sql` still carries the 11-value enum + `unknown` (12 total) — see "Schema follow-through" below for the deferral reasoning.

2. **§4.5 severity-derivation table** — added `in_vehicle_router | low | routine LE infrastructure (data backhaul, not covert and not personal-threat-model)` between `police_radio` and `gunshot_detect`. Severity = `low` per board direction in `a7edae6f` ("matches `police_radio` reasoning: routine LE infrastructure, not covert or personal-threat-model"). Reasoning column phrasing parallels the existing `police_radio` row.

3. **§4.2 supporting tables — `procurement_records` documentation gap filled.** Added `procurement_records` bullet between `deployment_observations` and `extraction_runs`. The table itself was created in MAC-2 / Phase 1 per the §4.5 procurement carveout (option a, separate-table; signed off at Checkpoint 1) but was never reflected in the §4.2 enumeration — surfaced as out-of-bible observation at CP4, held per the strategic-steers-as-soft-priors rule, ratified for fix at Checkpoint 2 sign-off (`a7edae6f` decision #3 third bullet). Bullet wording follows the `deployment_observations` precedent — single sentence, identifies the role + idempotency upgrade-path (`linked_identifier_id` FK) + §4.5 / §11 #14 cross-reference.

4. **§12 — added `geographic_scope` Open Question.** Bundles two adjacent realities surfaced at Checkpoint 2: (a) DeFlock holds ~849 international ALPR nodes that are dead weight in a US-deployed Talos scanner; (b) DeFlock holds private-sector retail-ALPR records that the Phase-2 board call placed out-of-scope for V1 but kept in staging for potential V2 reconsideration. Single export-time categorical filter handles both axes — records stay in `deployment_observations`, export shape changes. Decision deferred to Phase 5 alongside the Talos export design (§7.5).

### Schema follow-through (deferred — no migration in this pass)

The §4.1 enum text in the bible now lists `in_vehicle_router`. The schema CHECK constraint on `identifiers.device_category` in `db/migrations/0001_initial.sql` (lines 61–66) does **not** yet include the new value, and `manufacturers.primary_category` for Cradlepoint/Sierra Wireless is still `NULL` rather than `'in_vehicle_router'`. This drift is intentional and time-boxed:

1. **Staging is unaffected.** `raw_observations.candidate_category` carries no CHECK constraint (line 167 of the migration), so Phase 3 staging works without any schema change. MAC-7 onwards can record `candidate_category='in_vehicle_router'` immediately if a Cradlepoint/Sierra grantee FCC filing is found.
2. **`manufacturers.primary_category` carries no CHECK either** (line 104), so updating Cradlepoint/Sierra's `primary_category` from `NULL` to `'in_vehicle_router'` is a pure data update — no schema migration needed when the time comes — but it would clobber existing seed state on `init_db.py` re-run. Defer to a paired DBArchitect task that touches the seed and updates the row in place rather than re-init.
3. **The CHECK only fires on promotion.** `identifiers.device_category` is the only CHECK that needs extending, and that fires only when Phase 4/5 promotes a candidate to `identifiers`. Until that happens, the bible-text enum and the schema CHECK can disagree without ingest impact.

A future migration `db/migrations/0003_*.sql` will extend the CHECK to 13 values when the first Cradlepoint/Sierra promotion is on the table — DBArchitect work, paired with the manufacturers seed update for primary_category. Tracked in PROJECT_STATE.md "Open" for visibility.

### Why CP5 bundles four edits as one pass

The board explicitly framed all four items as a single "bible-tidy ride-along" landing before Phase 3 dispatch. Each edit is small (1–4 lines) and they all derive from a single user decision in `a7edae6f`. Bundling matches the CP3 ride-along precedent (one user decision → one CP entry → multiple in-place edits) and avoids the noise of CP5/CP6/CP7/CP8 spread across the same heartbeat.

### §12 Open Questions impact

- **Net add of one question** (`geographic_scope` filter for the high-confidence Talos export, decision deferred to Phase 5).
- **`device_cluster_id`** stays open in §12 but its lean is now ratified as binding-but-not-final via SAR-3 below.
- **No struck-through resolutions** in this pass.

### Out-of-bible artifact updates that pair with this pass

- **`PROJECT_STATE.md`** — Header flipped to "Phase 2 closed, Phase 3 dispatching"; CP5 + SAR-3 entries logged in the bible-amendments status section; queued schema follow-through (`db/migrations/0003_*.sql` for `identifiers.device_category` CHECK extension + Cradlepoint/Sierra `primary_category` seed update) noted as deferred DBArchitect task.
- **No code change.** No migration authored, no module touched, no test re-run — this pass is bible text only.

---

## Correction Pass 6 — §4.2 add `fcc_grantees` staging table; document stale-mirror handling pattern

**Date:** 2026-05-04
**Commit:** `35900f0` — `docs(bible): correction pass 6 — §4.2 add fcc_grantees + stale-mirror handling pattern (MAC-7)`
**Source:** [MAC-7](/MAC/issues/MAC-7) Step-2 ratification + Step-2 ingest delivery [comment 094eae0a](/MAC/issues/MAC-7#comment-094eae0a-701e-4925-97c7-11493a2af60e). CP6 ride-along reservation was made at Step-2 ratification (CEO-owned, lands at MAC-7 close per the dispatch contract).
**Status:** Bible edit applied this commit. Two operational ratifications (§11 #3 corporate-comms read for FCC `contact_name`; staleness-ceiling notes-shape pattern) bundle as ride-along context inside this CP entry — NOT separate SARs (per the MAC-5 codification: routine §11 #3 / §7.2 / §8.2 applications inside a Correction Pass don't need SAR numbering).

### Corrections applied

1. **§4.2 supporting tables — `fcc_grantees` documentation added.** New bullet between `procurement_records` and `extraction_runs`. Mirrors the `deployment_observations` precedent (CP4) and the `procurement_records` precedent (CP5) — single bullet, identifies role + idempotency + stale-mirror requirement + identifier-free reasoning. The table itself was created in MAC-7 Step 2 via `db/migrations/0003_fcc_grantees.sql` (12 columns + UNIQUE on `(source_id, source_row_key)` + 4 indexes; mirrors `0002_deployment_observations.sql` shape; staged 50,153 rows from opendata.fcc.gov dataset `3b3k-34jp`).

### Operational ratifications bundled as ride-along context

These are routine rule applications, not new interpretive guidance — they ride here under the MAC-5 codification rather than spawning separate SARs.

1. **§11 #3 corporate-comms read.** FCC `contact_name` is mandatory federal-regulatory disclosure of a corporate-comms compliance contact (per FCC EAS form structure). The §11 #3 worked example ("officer's name, badge, home address") targets law-enforcement-personnel PII in a surveillance-target context. FCC corporate compliance contacts are a structurally distinct shape:
   - The MAC-5/MAC-6 person regex (`rank-token + [A-Z][a-z]+`) does NOT fire on this column in practice — independent CEO verification across all 44,241 populated `contact_name` rows returns exactly 2 corporate false positives (`Michael Chief Executive Officer`, `Captain Giannakos`) and zero officer-shape PII.
   - Stage-as-is on `contact_name` per Q4 ratification at Step 2 with explicit Phase-5 reconsider hook recorded in both `extraction_runs.notes` rows for source_id=7. Raw CSV preserved verbatim on disk per §7.2 audit trail (sha256 `5cd60fbe…0ee80cbd`).
   - **Reversibility:** if Phase 5 review (or board direction earlier) calls for a stricter PII gate, the column is recoverable via raw-CSV replay + simple DROP/redact migration; data shape is preserved.

2. **Staleness-ceiling handling pattern.** When an upstream mirror is documented stale (here: opendata.fcc.gov 3b3k-34jp frozen at 2021-03-22; `rowsUpdatedAt=2021-03-22T07:04:51Z`), the source `notes` JSON MUST carry:
   - `dataset_freeze_date` — ISO date of the upstream's last refresh, sourced verbatim from the mirror's metadata
   - `rows_updated_at_utc` — the upstream's own claimed timestamp, sourced verbatim
   - `staleness_warning` — human-readable description of what the freeze means for coverage and which Phase owns the gap
   - `extraction_runs.notes` for every run on a stale-mirror source carries the same staleness block + a Phase-5 reconsider hook tying the staleness to its downstream consequence
   - Tier classification is unaffected by staleness (USGOV public-domain authority is tier=1 regardless of mirror freshness; staleness affects fitness-for-purpose, not source authority — `tier` and `last_status` describe what the source IS, while `notes` describes what it currently HAS)
   - The Checkpoint brief that closes the Phase MUST surface stale-mirror coverage gaps as load-bearing findings (here: Flock Safety + 2021-04→2026-05 grantee gap routed to Phase 4 LLM-extraction worker)

### Schema follow-through (no further deferral introduced by this pass)

CP6 lands an applied migration (`0003_fcc_grantees.sql`) — no deferral. The CP5 schema-follow-through deferral (§4.1 `device_category` CHECK extension + Cradlepoint/Sierra `primary_category` seed update) **renumbers**: CP5's reference to "A future migration `db/migrations/0003_*.sql`" should now be read as **`0004_*.sql`** (DBArchitect recall trigger for the next promotion event or before MAC-8/9/10 if a Cradlepoint/Sierra grantee surfaces in Phase 3 staging requiring promotion). PROJECT_STATE.md "Open" section will reflect the renumber on the next state commit.

### Why CP6 stands alone

CP6 derives from a single source-ingest delivery (MAC-7 Step 2) with one new staging table + one operational read of an existing rule + one new operational pattern. CP5 was the multi-edit bundle from a single user decision; CP6 is a single per-source ride-along, matching the CP4 precedent (one source delivery → one CP → one new bullet + ride-along context).

### Out-of-bible artifact updates that pair with this pass

- **`db/migrations/0003_fcc_grantees.sql`** — applied at MAC-7 Step 2 (commit `b5df4e5`); 12 columns + UNIQUE backstop + 4 indexes. The migration shape was approved at Step 2 ratification ([comment 0e95c40a](/MAC/issues/MAC-7#comment-0e95c40a-54fd-4690-b582-e3892cfa8450)).
- **`db/sources/fcc_id.py`** — applied at MAC-7 Step 2 (commit `b5df4e5`); mirrors `eff_atlas.py` shape; uses `--raw-subdir` flag for no-re-fetch idempotency replay (MAC-5/MAC-6 precedent).
- **`PROJECT_STATE.md`** — flipped to reflect MAC-7 Step 2 closed + MAC-8 SAM.gov queued; CP6 entry logged in the bible-amendments status section; CP5's deferred-migration reference renumber noted (was `0003_*.sql`, now `0004_*.sql`).

---

## Sub-agent rule additions and interpretive guidance

This section captures rules that bind sub-agents but do not edit the bible text. New entries append below; do not rewrite history.

### SAR-1 — §7.3 LAA-bit examples are illustrative, not exhaustive

**Date:** 2026-05-04
**Source:** MAC-1 user comment [5d75988d](/MAC/issues/MAC-1#comment-5d75988d-c267-4e0d-982c-0007a6f2fa36)
**Bible commit:** none (no edit required)
**Binds:** Extraction Worker (§7.3), Validator (§7.4), DB Architect when wiring fake-MAC checks

The §7.3 LAA-bit examples (`02:*`, `06:*`, `0a:*`, `ae:*`) are a partial illustrative set, **not** an exhaustive list. The governing rule is **"bit 1 of the first octet is set"** — i.e., the first octet's least-significant bit pair `xxxxxx1x`. Implementations MUST test the rule directly:

```python
def has_laa_bit(mac_first_octet: int) -> bool:
    return bool(mac_first_octet & 0b00000010)
```

Any first-octet value where `(octet & 0x02) != 0` is locally-administered (e.g. `02`, `06`, `0a`, `0e`, `12`, `16`, `1a`, `1e`, …, `ae`, …, `fe`). Do NOT hard-code the four-prefix list.

### SAR-2 — Talos `argus_record_id` upsert semantics: human's lean is upsert

**Date:** 2026-05-04
**Source:** MAC-1 user comment [5d75988d](/MAC/issues/MAC-1#comment-5d75988d-c267-4e0d-982c-0007a6f2fa36)
**Bible commit:** none (no edit; tracked in §12 already)
**Binds:** DB Architect (when designing `argus_record_id` stability), future Export Worker, downstream Talos design

The user's stated lean for the open question on Talos v0.2 upsert semantics is **upsert** (preserves user-side annotations on Talos when re-importing later Argus versions). The final answer is a Talos design call and is not yet authoritative. Argus implementation should:

- Keep `argus_record_id` stable across re-exports of the same canonical record (already required by §7.5).
- Assume upsert is the likely target so the export shape and the Talos seeder contract converge.
- Surface this assumption explicitly at Checkpoint 5 if Talos design has not formally resolved it by then.

### SAR-3 — `device_cluster_id` lean is scanner-side: Argus identifies, Talos correlates

**Date:** 2026-05-04
**Source:** [MAC-1](/MAC/issues/MAC-1) user comment [a7edae6f](/MAC/issues/MAC-1#comment-a7edae6f-6c7a-493e-82f2-fa088942a1a9) (Checkpoint 2 sign-off, decision #3 second bullet)
**Bible commit:** paired with CP5 (no §12 edit — the question stays open per the user's "lean = scanner-side, but holding for explicit Phase 5 close" framing)
**Binds:** future Export Worker (when hired for Phase 5), DBArchitect (when designing the export shape and any cluster-correlation join), Phase 5 export design generally

The §12 open question on `device_cluster_id` (added in CP3) is now ratified as **lean = scanner-side** with binding-but-not-final force:

- **Argus's job is identifiers.** The canonical Argus database holds atomic identifier records (one MAC = one row; one OUI = one row; one SSID pattern = one row). Each row already carries enough metadata (`device_category`, `manufacturer`, `geographic_scope`, `notes`) to participate in a cluster join *at scan time* without Argus pre-computing the cluster.
- **Talos's job is correlation.** Cluster recognition (e.g., "these 6 MACs co-located within 30s within 50m = 1 patrol car") is a streaming inference over scanner observations, not a static property of the watchlist. Encoding `device_cluster_id` in the Argus export bakes in a single clustering hypothesis that the scanner cannot override or refine, which is the wrong split of responsibilities.
- **Phase 5 export shape consequence.** The Talos export schema (§7.5 / §4.4) does **not** include a `device_cluster_id` column. The Export Worker's job is per-record emission; the Pi scanner's correlation logic builds clusters from observed co-occurrence using the per-record metadata Argus already provides.
- **Schema consequence.** No `device_cluster_id` column is added to the `identifiers` table or any export view. If a future Phase 5 review surfaces a concrete correlation use case Argus can serve better than the scanner (e.g., grantee-FCC-ID-derived OEM bundling that Talos can't reconstruct), the question reopens.

The §12 entry stays open under the strategic-steers-as-soft-priors discipline — final close happens at Phase 5 export design alongside the geographic_scope decision (CP5).

### SAR-4 — §11 #6 robots.txt routing rule: legitimate alternatives only, never ignore

**Date:** 2026-05-04
**Source:** [MAC-1](/MAC/issues/MAC-1) user comment [ae94e4eb](/MAC/issues/MAC-1#comment-ae94e4eb-e56e-4d2e-9141-2171b438ae0a)
**Bible commit:** none (codifies the §11 #6 application standard for source discovery; no §11 text edit needed — the hard rule already exists, this entry binds the implementation pattern)
**Binds:** Source Worker (during source discovery + Step-1 ratification proposal), DBArchitect (when designing source-discovery flow or evaluating new endpoints), future Extraction Worker (when discovering supplementary sources), CEO (when ratifying source-fit proposals that mention robots.txt friction)

**The rule (board-stated, verbatim):** "§11 #6 hard rule means we route around robots.txt blocks by finding legitimate alternative endpoints (CDN, bulk download, official API, FOIA archive), never by ignoring the block. If no legitimate alternative exists, the source is skipped and documented in `coverage_report.md`."

**How to apply:**

- When a source's `robots.txt` blocks an automated path (e.g. `Disallow: /api/`), the Source Worker MUST search for a legitimate alternative: a CDN endpoint the site's own frontend reads, a published bulk-download URL, an official API with explicit terms, a FOIA archive, or an upstream the site is mirroring (e.g. OSM under DeFlock).
- A legitimate alternative is **not a workaround**. It is a different access path the data publisher openly provides. The disallow is about the API contract, not about the data being forbidden. Hitting `cdn.deflock.me` instead of the robots-disallowed `deflock.org/api/` (MAC-6) is the canonical example.
- If no legitimate alternative exists, the source is **skipped**. Document the skip + the alternatives considered + why none qualified in `coverage_report.md` (Phase 5 deliverable per §6 + §13). Do NOT escalate to "ask user for permission to ignore" — §11 #6 is a hard rule, not a soft preference, and there is no escape hatch.
- The Step-1 ratification proposal (MAC-5 / MAC-6 / MAC-7 onwards two-step shape) MUST quote the source's `robots.txt` verbatim and state the chosen endpoint's relationship to the disallow rule (covered by Allow / different host / different path / explicit license override).
- **Phase 3 sources (FCC EAS, SAM.gov, council minutes, WiGLE) are expected to have zero robots.txt friction** — all have explicit public-access paths. WiGLE's constraint is rate-limiting, which is a budget question (Checkpoint 3a), not a robots.txt question. Source Workers should not invent robots.txt issues where none exist.

**Application precedent recorded:** MAC-6 DeFlock — `deflock.org/robots.txt` carries `Disallow: /api/` for `User-agent: *`; SourceWorker chose Path B (`cdn.deflock.me`, the DeFlock-published frontend's own CDN host) over Path A (`deflock.org/api/`, blocked); CEO ratified at 2026-05-04T~05:38Z; Phase 2 source 4/4 staged 101,597 deployment records under this rule. SAR-4 codifies the implementation pattern that worked.

### SAR-5 — [MAC-11](/MAC/issues/MAC-11) council-minutes scope discipline: format-fit cap, not jurisdiction-count cap

**Date:** 2026-05-04
**Source:** [MAC-1](/MAC/issues/MAC-1) user comment [1c5831f3](/MAC/issues/MAC-1#comment-1c5831f3-a673-4da2-a449-f3a47683a68a)
**Bible commit:** none (no §6 / §7.2 / §11 edit; binds the implementation pattern for the MAC-11 dispatch + Step-1 ratification + Step-2 ingest). Codified at user direction ("Codify the revised scope as a SAR before `MAC-11` dispatch.")
**Binds:** Source Worker (MAC-11 source discovery, Step-1 ratification proposal, Step-2 ingest), CEO (when ratifying Step-1 proposal and Step-2 delivery)

**The rule (board-stated, paraphrased decision-bearing language verbatim).** For [MAC-11](/MAC/issues/MAC-11) (city/county council minutes + municipal procurement portals — Phase 3 source 4/4), the scope discipline is **format-fit, not jurisdiction-count**. The earlier "top-10 jurisdiction cap" framing is rescinded ("that was overcautious on my part"). The 10-jurisdiction list below is a **starting batch**, not a ceiling.

**How to apply:**

1. **Starting batch (anchor, not ceiling).** Begin with the top-10 jurisdictions:
   - San Diego (CA)
   - Detroit (MI)
   - San Francisco (CA)
   - Chicago (IL)
   - New York City (NY)
   - Norfolk (VA)
   - Las Vegas Metro (NV)
   - Irvine (CA)
   - Albuquerque (NM)
   - Hampton (VA)
   These validate the scrape pattern and confirm yield-per-effort. After the starting batch closes, fan out by feasibility — any US jurisdiction with a structured procurement portal or machine-readable agenda is in scope.
   - **Why:** Argus is a national database. Capping at top metros bakes in urban bias. Smaller jurisdictions are exactly where surveillance gear lands without journalism coverage — that is where Argus adds the most marginal value over Atlas of Surveillance.

2. **Format restriction is the real cap.** Structured procurement portals and machine-readable agendas only. If a jurisdiction's data is PDF-locked or requires OCR/LLM extraction, **stop and relocate that jurisdiction to Phase 4** (LLM extraction worker). Do not invent in-Phase-3 OCR pipelines for individual jurisdictions.
   - **Why:** Phase 3 owns structured public-data ingest. PDF / OCR / LLM extraction is the Phase-4 pattern per §6 and the Phase-4 worker is designed for it. Forcing PDF mining inside Phase 3 erodes the structural distinction between phases and inflates the per-jurisdiction effort budget past calibration.

3. **Vendor sweep restriction.** Use the existing 24-vendor target list from [MAC-8](/MAC/issues/MAC-8) (Group A + Group B union, including the 16 [MAC-7](/MAC/issues/MAC-7)-gap vendors). Do **not** run open-ended `"ALPR"` / `"surveillance"` / similar generic keyword queries against jurisdiction portals.
   - **Why:** Argus is a vendor-attribution database, not a generic surveillance-mention database. Vendor-name keyword discipline has held since [MAC-3](/MAC/issues/MAC-3) and stays binding here.

4. **Per-jurisdiction effort stop rule (worker-defined, ratified at Step 1).** The Source Worker MUST propose a concrete per-jurisdiction extraction-effort budget in the Step-1 ratification proposal (units worker-chosen — e.g., HTTP-call count, wall-clock minutes, parser-line count, retries, page-cap, or a composite). The CEO ratifies the budget at Step-1. Once Step-2 begins, if a jurisdiction's structured-data extraction exceeds the ratified budget, **stop, log the partial state in `extraction_runs.notes`, and move on**. The effort/yield ratio is the cap, not raw row count.
   - **Why:** A small town with one record at low extraction cost is fine; a mid-size city requiring custom per-page parsing is not. Yield-per-effort is the load-bearing fitness signal. Worker-defined budget keeps the cap calibrated to actual jurisdiction data shapes the worker discovers, rather than CEO-guessed numbers ahead of discovery.

5. **No PII surfacing — §11 #3 same posture as [MAC-5](/MAC/issues/MAC-5).** Aggressive person-regex redaction. Log redaction sites in `extraction_runs.notes` (count + site descriptors, never raw redacted strings). Raw artifacts preserved per §7.2 audit trail. The §11 #3 corporate-comms read carved out at [MAC-7](/MAC/issues/MAC-7) for FCC `contact_name` does **not** apply here — council minutes name elected officials, contracting officers, citizen commenters, and police-department personnel, all squarely inside §11 #3's worked-example shape ("officer's name, badge, home address"). Default-to-redact, not stage-as-is.
   - **Why:** Council minutes mix structured procurement metadata with unstructured public-comment narrative; the §11 #3 surveillance-target framing applies. The recall-first redaction posture from MAC-5 ("redact even at FP cost when source can carry PII") is the calibrated choice, not the zero-PII whitelist posture from MAC-6 (which presumed a PII-excluding source schema) or the corporate-comms carve-out from MAC-7 (which presumed a federal-regulatory disclosure surface).

6. **Discovery approach (worker-proposed at Step-1).** The Source Worker MUST propose a strategy in the Step-1 ratification proposal for *finding* US jurisdictions with structured procurement portals or machine-readable agendas beyond the top-10 starting batch. Concrete starting points the board named: USA.gov state and local government directory, Munirevs, Granicus, OpenGov, or whatever directory infrastructure the worker discovers. Do **not** attempt to enumerate every US municipality manually.
   - **Why:** A "find every US municipality with a structured portal" enumeration is multiplicatively expensive and brittle. Directory-driven discovery (vendor-of-vendors infrastructure like Granicus / OpenGov / Munirevs) lets one HTTP call return many qualifying jurisdictions. The worker proposes the discovery approach because they will be the one running it; CEO ratifies it.

**Application timing.** SAR-5 binds at **MAC-11 dispatch** (the council-minutes / municipal-procurement source). It does NOT bind [MAC-10](/MAC/issues/MAC-10) (DeFlock vendor-attribution backfill — derivation against existing `procurement_records` reseller chains, no jurisdiction-portal scraping). Sequence per board direction at [comment 1c5831f3](/MAC/issues/MAC-1#comment-1c5831f3-a673-4da2-a449-f3a47683a68a): [MAC-9](/MAC/issues/MAC-9) (WiGLE Step-0 budget, `in_progress`) continues in parallel; [MAC-10](/MAC/issues/MAC-10) (easy win) → [MAC-11](/MAC/issues/MAC-11) (council minutes, this SAR binds).

**Why this is a SAR, not a Correction Pass.** No bible text is being edited. The bible's existing §6 Phase 3 / §7.2 source-discovery / §11 #3 PII / §11 #6 robots.txt rules already cover the contractual surface; SAR-5 captures the implementation pattern for the council-minutes source-class specifically. CP convention is reserved for in-place bible edits + multi-edit bundles from a single user decision (see CP1–CP6 precedent); SAR convention covers single-source-class operational guidance (see SAR-3 / SAR-4 precedent).

### SAR-6 — Phase 4 per-wave checkpoint discipline (Step 0 ratification, status-class wave-end comment, ~50% yield-per-heartbeat stop-line)

**Date:** 2026-05-04
**Source:** [MAC-1](/MAC/issues/MAC-1) user comment [05af14d6](/MAC/issues/MAC-1#comment-05af14d6-2c0c-45b8-b166-647d27e35c9e) (Checkpoint 3 sign-off + Phase 4 dispatch authorization). Codified at user direction ("One additional discipline for Phase 4 (not a blocker, just lock it in)").
**Bible commit:** none (binds Phase 4 implementation pattern; no §6 Phase 4 / §7 / §8 / §11 text edit needed — the bible's existing Phase 4 wave-list, §7.3 Extraction Worker spec, and §10 "ship narrow, then widen" / yield-per-effort posture already cover the contractual surface; SAR-6 captures the operational discipline the board added at Phase 4 dispatch authorization)
**Binds:** Source Worker (when assigned Phase 4 wave components within their structural-format competence), Extraction Worker (when hired/assigned for Phase 4 PDF/HTML/text mining waves per §7.3), CEO (per-wave Step-0 ratification + status-class wave-end review + stop-line authorization decisions)

**The rule (board-stated, paraphrased decision-bearing language verbatim):**

- Each wave gets a **Step 0 ratification** (worker proposes scope + target vendor/source list, CEO ratifies before any extraction fires) — same two-step pattern as Phase 3.
- **Wave-end status comments** to the board (not full wakes — status-class only) reporting yield-per-effort. Format: records added, confidence distribution, vendor coverage delta vs prior waves, time elapsed.
- **Stop-line if any wave's yield-per-heartbeat falls below ~50% of expected.** That's a "stop, comment, reassign" trigger so the board can authorize early-cut, scope adjustment, or move to next wave. "Don't burn 12 heartbeats on Wave A if waves 1–4 are returning nothing."

**Rationale (board-stated):** "Phase 4 is the longest phase and the most LLM-cost-intensive. Per-wave checkpoints prevent runaway scope without requiring full board wakes."

**How to apply:**

1. **Per-wave Step 0 ratification (mandatory, mirrors Phase 3 two-step shape).** Each Phase 4 wave (B → A → C → D → E per board endorsement, see #4 below) opens with a Step 0 dispatch where the worker proposes:
   - **Scope:** target vendor/source list (vendors for Wave B, repos/keyword anchors for Wave A, paper venues + keywords for Wave C, jurisdictions/case categories for Wave D, news outlets / forum subreddits + cap rationale for Wave E).
   - **Per-source effort budget unit** (worker-chosen — e.g., HTTP-call count, wall-clock minutes, parser-line count, page-cap, retries, or composite — mirroring SAR-5 #4).
   - **Expected yield bands** (records / unique identifiers / confidence distribution by `source_type` per §8.2).
   - **Wave success-vs-stop-line decision criteria** (the worker's own ~50% baseline projection that the stop-line below tests against).
   - **Schema-fit recommendation** with draft DDL if a new staging table is needed (mirroring MAC-5 / MAC-6 / MAC-7 / MAC-11 Step-1 shape; CP ride-along reserved if new §4.2 entry warranted).
   CEO ratifies before any extraction fires. **No code commits, DB writes, migration authoring, or network fetches between dispatch and ratification.** Step 0 is non-fire by construction.

2. **Status-class wave-end comments (visibility, not action-required).** On wave close (success-end OR stop-line trip), the worker posts a status comment to the wave's [MAC-N](/MAC/issues/MAC-1) (and a one-line summary to MAC-1 for board visibility). Verbatim format the board prescribed:
   - **Records added** (count by `source_type`, `device_category`, `identifier_type`)
   - **Confidence distribution** (bucketed against §8.2 bands — `≥90`, `75–89`, `50–74`, `<50`)
   - **Vendor coverage delta vs prior waves** (which §2.1 vendors gained identifier-bearing rows that did not have them before this wave)
   - **Time elapsed** (heartbeats consumed; CEO-class clock, not wall-clock)
   These comments are **status-class, not wake-class**. Board reads them on the standing wake-board cadence per board steer [`31445dcf`](/MAC/issues/MAC-1#comment-31445dcf-5e4f-40ce-92c1-0d3a7fd35bae) — they do **not** trigger immediate board action.

3. **~50% yield-per-heartbeat stop-line (worker-derived baseline, ratified at Step 0).** The "expected" baseline is the worker's own Step-0 yield projection (item 1 above). If observed yield-per-heartbeat falls **below ~50% of that projection** sustained across the measurement window the worker proposed at Step 0, the worker MUST:
   - **Stop** further extraction in the wave.
   - **Comment** on the wave's MAC-N with: current observed yield, the Step-0 baseline being tested against, what's been tried, and a recommended path forward.
   - **Reassign** the wave issue to CEO `in_review`.
   The CEO authorizes one of: (a) early-cut at current state and move to next wave, (b) scope adjustment / target-list trim and resume, or (c) wave abandonment with carry-forward to Phase 5 deferred-enrichment.
   - **Why ~50% (board-stated rationale):** matches the SAR-5 spirit (yield/effort ratio is the cap) and the bible §10 "ship narrow, then widen" / "prefer fewer high-quality records to many low-quality ones" posture. The threshold is approximate, not pixel-perfect — the binding is "trip when measurable underperformance is sustained," not a precise arithmetic gate. The worker's Step-0 projection IS the gate; the ~50% is the stop-line band against that projection.
   - **Do not** burn additional heartbeats past stop-line trip without explicit CEO authorization. Mirrors the bible §11 "Stop. Comment. Reassign. Do not guess." rule, scoped to wave-level yield rather than schema/source ambiguity.

4. **Wave ordering: B → A → C → D → E** (board-endorsed at this comment).
   - **Why B first (board-stated rationale):** "Wave B yields a richer vendor lexicon (default SSIDs, BLE UUIDs, model numbers, FCC test-report content) that *then* makes Wave A's GitHub discovery far more targeted. Searching GitHub for 'Flock' alone is noisy; searching for specific SSID patterns or model numbers extracted from Wave B manufacturer docs is precise. B → A compounds yield in a way A → B does not."
   - **Compounding effect.** Each wave's output anchors the next wave's search. Wave A's GitHub discovery uses Wave B's SSID/UUID/model lexicon. Wave C's academic search uses cumulative B+A vendor-specific terminology. Wave D's court/FOIA targeting uses cumulative B+A+C deployment-and-vendor knowledge. Wave E's news/forum cap inherits all prior precision.
   - **Step-0 dispatches reuse this lexicon:** the Step-0 proposal for waves A onward MUST include "search anchors derived from prior waves" as part of the scope justification. CEO ratifies the anchor list at each wave's Step 0.

5. **CEO autonomy class for Phase 4 (consistent with board steer [`31445dcf`](/MAC/issues/MAC-1#comment-31445dcf-5e4f-40ce-92c1-0d3a7fd35bae) 21:40Z + Phase 4 dispatch authorization at this comment).**
   - **CEO-class (autonomous, no board wake):** per-wave Step-0 ratifications, mid-wave Step-1/Step-2 ratifications on the existing two-step shape, wave success-end status comments (status-class), CP4 brief authoring at Phase 4 close, and CP6+ ride-along bible amendments triggered by per-wave schema-fit decisions.
   - **Board-class (wake-board criteria):** wave stop-line trips (CEO comments on wave + MAC-1 with the stop-line + recommended path; board authorizes early-cut / scope adjustment / abandonment), CP4 sign-off at Phase 4 close, and §11 hard-rule triggers within a wave (PII surface beyond bounded redaction, ToS violation, recurrent fabrication).
   - **Status-class (visibility, not action-required):** per-wave wave-end status comments (item 2 above), including stop-line-adjacent informational reports the worker chooses to surface that don't trip the stop-line definition.

**Application timing.** SAR-6 binds at **Wave B Step 0 dispatch** (this heartbeat, post-CP3 sign-off) and applies to every subsequent Phase 4 wave (A, C, D, E) until CP4 closes Phase 4. It does **not** retroactively bind Phase 3 (closed at MAC-11 ratification per board steer [`31445dcf`](/MAC/issues/MAC-1#comment-31445dcf-5e4f-40ce-92c1-0d3a7fd35bae) 21:40Z). It does **not** alter the WiGLE deferred-enrichment posture (independent decision frame, 2026-05-18 timeout, see [`feedback_wigle_deferred_enrichment.md`](feedback_wigle_deferred_enrichment.md)).

**Why this is a SAR, not a Correction Pass.** No bible text is edited. The bible's existing §6 Phase 4 wave list (A/B/C/D/E definition), §7.3 Extraction Worker spec, §8.2 confidence bands, §10 ship-narrow-then-widen / yield-per-effort posture, and §11 #1/#7/#8 hard rules already define the structural surface; SAR-6 captures the per-wave operational discipline the board added at Phase 4 dispatch authorization. Mirrors SAR-5's relationship to §6 Phase 3 / §7.2 / §11 (single-phase-class operational guidance bundle, board-stated, no in-place edit). The CP convention remains reserved for in-place bible edits driven by per-wave schema-fit decisions during Phase 4 (e.g., a future CP7 if Wave B chooses a new `vendor_doc_observations` staging table).

### SAR-7 — Step-2.0 disambig bundle (CVE-FP allowlist + DJI/Djibouti FP class + news/forum-prose-FP class)

**Date:** 2026-05-06
**Source:** [MAC-35](/MAC/issues/MAC-35) CP4 brief authoring under CEO autonomy per HB27 sign-off [`0c252e39`](/MAC/issues/MAC-1#comment-0c252e39-f552-4996-8492-4148bf8284a4); board ratification via approval [`bf95a897`](/MAC/approvals/bf95a897-834c-473e-99f1-63d6cefd4b06) at 2026-05-06T11:43:05Z.
**Bible commit:** SAR-7 entry committed paired with this amendment-log landing; no bible-text edit.
**Binds:** Extraction Worker (§7.3), Validator (§7.4), `db/extraction/fcc_grantees_allowlist.py` and equivalent vendor-mention disambig surfaces.

**The rule (3 sub-items, single bundled amendment).** SAR-7 is operational guidance for the existing §7.3/§7.4 disambig surface — no §4 / §11 enumeration extension. Mirrors SAR-1 (interpretive guidance for §7.3 LAA-bit examples).

#### SAR-7 #1 — CVE-FP allowlist (codification, already partially live)

The CVE/CWE/NIST shape was implemented in `STOP_LIST_PATTERNS` of `db/extraction/fcc_grantees_allowlist.py` (Wave-A close, MAC-25 commit `aed1e96`) but never amendment-logged. SAR-7 #1 codifies the implementation under §11 #11 amendment-log discipline:

- Any `fcc_id_anchored` match that also matches `^CVE-\d{4}(-\d{4,7})?$`, `^CWE-\d{1,4}$`, or NIST NVD shape is rejected as `reason='cve_security_advisory_fp'`.
- Wave-C ([MAC-28](/MAC/issues/MAC-28)) is the test case: 40-paper academic corpus with constant CVE references; the stop-list caught all of them. Wave-A Step-1.5b survey originally surfaced `CVE-2025` as one of 2 FP hits.

**Reasoning.** Academic and security-research literature uses CVE/CWE shape constantly; without the stop-list, every paper citing a CVE would surface as an `fcc_id_anchored` hit and pollute Phase-5 promotion candidates.

#### SAR-7 #2 — DJI/Djibouti FP class (vendor-name vs country-code disambig)

When a `vendor_mention` regex pass counts string occurrences of `DJI` (the §2.1 #6 drone-vendor short name), reject occurrences where the surrounding ±50-char context matches a country/jurisdiction shape:

- ISO 3166-1 alpha-3 country code position (e.g., `Republic of Djibouti`, `country: DJI`, `jurisdiction code DJI`)
- Court-filing jurisdictional context (`District of DJI`, `case venue DJI`)
- FOIA-released document jurisdictional metadata block

**Reasoning.** `DJI` is both the drone vendor and the ISO 3166-1 alpha-3 code for Djibouti. Wave-D ([MAC-31](/MAC/issues/MAC-31)) court/FOIA prose and Wave-E ([MAC-33](/MAC/issues/MAC-33)) news prose carry both contexts. Wave-D survey (`raw/court_foia/20260506T030500Z/_step1_5b_survey.json`) produced 0 `fcc_id_anchored` hits for DJI — but vendor-mention density count (which feeds Phase-5 cross-reference scoring) is FP-prone without this gate. `DJI` is also a real FCC grantee code (`Seragen Diagnostics`, unrelated to drones) — the grantee allowlist gate alone never disambiguates the drone-vs-country-vs-grantee cases.

**False-negative leaning.** A real DJI drone FCC filing (post-2013 applicant) would have a 5-char grantee prefix (e.g., `2AGUI-…`), not the 3-char `DJI` shape — so this rule does not interfere with real DJI drone identifier promotion. Phase-5 Validator + standing-advisory cross-reference catches anything missed.

**Implementation.** New `is_country_jurisdiction_context_fp(vendor, context_text)` predicate in `db/extraction/fcc_grantees_allowlist.py`, applied at vendor-mention scoring time (Step-1.5b survey + Phase-5 cross-reference scoring).

#### SAR-7 #3 — News/forum-prose commercial-model-name FP class

If a `fcc_id_anchored` regex match has surrounding ±50-char context matching `<vendor-name>\s+<prefix>-<digits>`, where:

1. `<vendor-name>` is from the §2.1 / 24-vendor canonical lexicon (carries from MAC-7/MAC-8/MAC-11 + MAC-21 anchors), AND
2. `<digits>` is 3–4 digits (matching commercial-model-name shape, not the 4–14-char FCC product-code range), AND
3. The matched grantee prefix's `fcc_grantees.grantee_name` does **not** match the vendor name in the surrounding context (i.e., `MBR` resolves to `Esselte Dymo`, not `Cradlepoint`),

Then reject as `reason='commercial_model_name_fp'` and route to a count-only disambig drop log (analogous to `fcc_id_grantee_allowlist_drops`).

**Source.** Surfaced by [MAC-33](/MAC/issues/MAC-33) Wave-E Step-1.5b survey (`raw/news_forums/20260506T052423Z/_step1_5b_survey.json`, run log `logs/mac33_step1_5b_run_20260506T054543Z.log`). 2 strict-gate hits in `e5_stackexchange/queries/Cradlepoint_serverfault/search.json`: `MBR-1200` and `MBR-1000`. `MBR` is a real FCC grantee code (`Esselte Dymo N V`, label printers) but surrounding prose says `Cradlepoint MBR-1200` — the Cradlepoint Mobile Broadband Router product line, not an FCC ID.

**Sibling cases to specify defensively.** Cradlepoint IBR-N family, Sierra Wireless GX-/RV-/MG-series, Motorola APX-series (`APX-6000`/`APX-7000`/`APX-8000`), Cisco/Juniper router model nomenclature. Rule shape catches the class, not just the seed.

**False-negative leaning.** A real Cradlepoint FCC filing under a 5-char post-2013 grantee prefix (e.g., `2AABC-XYZ12345`) would not match the FP shape (5-char prefix, 8-char product code). Edge case: a real 3-char Cradlepoint grantee filing (legacy applicants) would pass the gate via item 3 (grantee-name-vs-vendor-context check).

**Implementation.** New `is_commercial_model_name_fp(match, context_text)` predicate in `db/extraction/fcc_grantees_allowlist.py`, called from `validate_fcc_id_match()` after the existing CVE/CWE/NIST stop-list gate. Drop count surfaces in Step-1.5b survey output as a new `fcc_id_commercial_model_name_fp_drops` field, parallel to `fcc_id_grantee_allowlist_drops`.

#### SAR-7 catch-all — application timing and binding scope

- **Binds at Phase-5 Validator dispatch.** SAR-7 is codified now (CP4 sign-off) but the implementation lands as Phase-5 Validator scope (separate issue, dispatched on this same CP4 ratification).
- **Does not retroactively rewrite Phase-4 wave dispositions.** Wave-B/B2/C/D/E early-cuts stand as ratified; SAR-7 explains and codifies the FP classes that were observed but does not reopen the path-decisions. Wave-E `MBR-1200`/`MBR-1000` reclassify retroactively as `fcc_id_commercial_model_name_fp_drops` (count-only); the path-(a) early-cut already-ratified by approval [`4444343b`](/MAC/approvals/4444343b-d02d-4e8c-a6a3-06b3f8935b51) stands.
- **§7.3 / §7.4 contractual surface unchanged.** SAR-7 is operational guidance for `db/extraction/fcc_grantees_allowlist.py` and the equivalent vendor-mention disambig surface.
- **Why a SAR, not a Correction Pass.** No bible text is being edited. Mirrors SAR-1's relationship to §7.3 (interpretive guidance binding implementation, not contract) and SAR-3/SAR-4/SAR-5/SAR-6's pattern of single-decision interpretive bundles.

**CP4 brief reference.** Full Phase-4 close + Phase-5 dispatch readiness context lives in `/home/kev/argus/CP4_BRIEF.md` (commit `dff9e6e`, board-ratified via approval [`bf95a897`](/MAC/approvals/bf95a897-834c-473e-99f1-63d6cefd4b06)).

---

### SAR-8 — Vendor-name-disambig predicate (alias allowlist + geographic-prefix handling)

**Date:** 2026-05-06
**Source:** [MAC-39](/MAC/issues/MAC-39) Phase-5 Step-4 halt-flag #1 surfaced by Validator at [`dd521ad3`](/MAC/issues/MAC-39#comment-dd521ad3-11f5-4c3c-855b-b84429ebbcb3) 2026-05-06T15:20:07Z; CEO surfaced to board at MAC-1 [`4bd6644c`](/MAC/issues/MAC-1#comment-4bd6644c-e2be-42f9-9acf-7856b828e1dd) 16:40:29Z; board ratification via MAC-1 [`613ec532`](/MAC/issues/MAC-1#comment-613ec532-d8cb-4f0f-a35b-c811e2864d7d) 2026-05-06T17:08:16Z, approving option (a)+(c) combined and rejecting (b) ("mixing confidence-band signals with FP-flagging signals at the wrong layer").
**Bible commit:** SAR-8 entry committed paired with this amendment-log landing; no bible-text edit.
**Binds:** Extraction Worker (§7.3), Validator (§7.4), new `db/extraction/vendor_name_disambig.py` module + future extractor passes.

**The rule.** When matching candidate vendor strings against the §2.1 / 24-vendor canonical lexicon (Phase-3 inference, Phase-4 retroactive sweeps, future extractor passes), the predicate must:

1. **Reject prefix-token false-positives** where the candidate string carries a tokenizable prefix that collides with a §2.1 canonical name but the full normalized string is a distinct entity. Concrete cases observed at MAC-39:
    - `Axon Networks Inc.` ≠ Axon Enterprise (×6 hits)
    - `Flock Audio Inc.` ≠ Flock Safety (×3 hits)
    - `Harris Adacom Corp` ≠ Harris Corp (×2 hits)
    - `GENETEC Corporation` may be distinct from Genetec Inc. (×2 hits — flag for human review)

2. **Recover canonical-name matches** under geographic-prefix variations. Concrete cases observed at MAC-39:
    - `SZ DJI TECHNOLOGY CO.,LTD` (Shenzhen-prefix; canonical IEEE registration name for DJI) → matches `dji`
    - `CelleBrite Mobile Synchronization` (early-2000s OUI; same entity as today's Cellebrite) → matches `cellebrite`

3. **Maintain a per-vendor alias allowlist** keyed by canonical §2.1 name. Allowlist entries are explicit string variants that the predicate accepts as canonical-vendor matches. Entries in the FP list (item 1) are explicit string variants the predicate rejects.

4. **Geographic-prefix handling:** `SZ` (Shenzhen), `Shenzhen`, `SZ.`, `Shenzhen Co.,` and similar 2–10-char geographic prefixes are stripped before normalization comparison. Do not strip US state/city prefixes when they carry separate legal-entity meaning (e.g., `New York Axon` is not Axon Enterprise).

**Reasoning.** MAC-39 Phase-3 inference candidate sweep surfaced 12 strict-path FPs and 20 permissive-path missed-TPs at OUI×§2.1 vendor matching. The strict-path FPs are real false matches (Axon Networks ≠ Axon Enterprise); the permissive-path missed-TPs are real entity matches obscured by IEEE registration name conventions (DJI registers as `SZ DJI TECHNOLOGY CO.,LTD`). Rule shape captures both classes via a single allowlist-driven module rather than ad-hoc regex.

**Implementation directive (per board (a)+(c) approval).**
- New module `db/extraction/vendor_name_disambig.py` carrying:
    - `_normalize_vendor(name: str) -> str` (moved from MAC-39 sweep code; canonical normalization predicate shared across extractor passes)
    - `is_canonical_vendor_match(candidate: str, vendor_canonical: str) -> bool` (allowlist-driven match predicate; consumes FP list + alias allowlist)
    - `VENDOR_FP_LIST` (constant, 12+ FP cases enumerated above)
    - `VENDOR_ALIAS_ALLOWLIST` (constant, 20+ alias variants enumerated above; per-canonical-vendor keyed)
    - `GEOGRAPHIC_PREFIX_LIST` (constant; `SZ`, `Shenzhen`, etc.)
- Tests required: positive (each alias accepts) + negative (each FP rejects) + edge (`GENETEC Corporation` flagged for human review, not silently accepted/rejected).
- Wired into Phase-5 Step-4 follow-on (SAR-8 application against MAC-39 candidate set + bulk-stage); Phase-4 retroactive sweeps re-run post-implementation; future extractor passes inherit.

**False-negative leaning.** The allowlist is an explicit-add predicate. Vendors with ambiguous corporate naming (e.g., overseas subsidiaries with significant rebranding) require explicit alias entries. Phase-5 inference sweep surfaces unknown-alias counts in the bulk-staging deliverable comment.

**Rejected option (b) — for the record.** Emit permissive-only matches at confidence ≤ 30 as FP-pending was rejected by board reasoning: "mixing confidence-band signals with FP-flagging signals at the wrong layer. Confidence reflects source/methodology certainty; FP review is a separate discipline. Keep them clean." (MAC-1 [`613ec532`](/MAC/issues/MAC-1#comment-613ec532-d8cb-4f0f-a35b-c811e2864d7d)).

**Application timing and binding scope.**
- **Binds at Phase-5 Step-4 follow-on dispatch.** SAR-8 codified now; implementation lands as Validator-execution against MAC-39 candidate set.
- **Does not retroactively rewrite Phase-4 wave dispositions** (Wave-B/B2/A/C/D/E early-cuts and Wave-A row promotion stand). SAR-8 governs Phase-5 inference + future extractor passes.
- **§7.3 / §7.4 contractual surface unchanged.** SAR-8 is operational guidance for the new disambig module + future extractor pass surfaces.
- **Why a SAR, not a Correction Pass.** No bible text is being edited. Mirrors SAR-7's relationship to §7.3/§7.4 (operational guidance binding implementation, not contract).

**MAC-39 reference.** Full halt-flag context + per-source candidate counts lives in MAC-39 Validator deliverable [`dd521ad3`](/MAC/issues/MAC-39#comment-dd521ad3-11f5-4c3c-855b-b84429ebbcb3); CEO halt-flag surface to board at MAC-1 [`4bd6644c`](/MAC/issues/MAC-1#comment-4bd6644c-e2be-42f9-9acf-7856b828e1dd); board ratification at MAC-1 [`613ec532`](/MAC/issues/MAC-1#comment-613ec532-d8cb-4f0f-a35b-c811e2864d7d).

### SAR-9 — Motorola Mobility/Solutions corporate-split FP class (+ SAR-8 alias-iteration bug-fix + WatchGuard Technologies/Video disambig)

**Date:** 2026-05-06
**Source:** [MAC-41](/MAC/issues/MAC-41) Phase-5 Step-4 follow-on bulk-stage halt-flag surfaced by Validator post-staging spot-check (3 commits 1d684ce/65860f4/d317550, 411 inferred rows staged then rolled back); halt-flag artifact at `extraction_outputs/mac41/sar8_bulk_stage_halt_flag.json`. Board ratification via approval [`234faaa7`](/MAC/approvals/234faaa7-e1c0-40fd-a247-f82cb588fc23) approved 2026-05-06T18:05:53Z, bundling SAR-9 codification + SAR-8 alias-iteration bug-fix + WatchGuard Technologies hard-reject.
**Bible commit:** SAR-9 entry committed paired with this amendment-log landing; no bible-text edit. §2.1 lexicon `Motorola Solutions` aliases column re-scoped per item (1) below.
**Binds:** Extraction Worker (§7.3), Validator (§7.4), `db/extraction/vendor_name_disambig.py` module (extends SAR-8 list contents + restructures caller surface).

**The rule.** SAR-9 augments SAR-8 with three additional disambig classes surfaced by Step-4 follow-on bulk-stage. The Validator MUST apply these alongside the SAR-8 predicate before promoting candidates to staged-`inferred` band:

1. **Motorola Mobility/Solutions corporate-split FP class.** When matching candidate vendor strings against the §2.1 `Motorola Solutions` canonical entry, the predicate MUST reject candidate strings carrying any of the substrings `mobility`, `(wuhan)`, `lenovo` (case-insensitive). These attribute to **Motorola Mobility / Lenovo** (consumer smartphones, post-2011 corporate-split entity), a corporate entity distinct from **Motorola Solutions** (police radios, the §2.1 vendor). Concrete corpus impact at MAC-41: 240 `Motorola Mobility LLC, a Lenovo Company` rows + 32 `Motorola (Wuhan) Mobility Technologies Communication Co., Ltd.` rows = 272 FP rows (66% of the 411-row Step-4 follow-on bulk-stage).

   - **Bare `Motorola` token routes to `flag_for_review`** pending model-name evidence: `APX` / `V300` / `V500` / `Vigilant` / business-light-radio shape ⇒ Solutions; consumer-smartphone shape ⇒ Mobility/Lenovo; ambiguous shape ⇒ human triage.
   - **§2.1 `Motorola Solutions` aliases column re-scoped:** drop bare `Motorola` (ambiguous post-2011); keep model-line aliases only (`Motorola APX`, `Motorola V300`, `Motorola V500`, `Motorola Vigilant`).

2. **SAR-8 alias-iteration bug-fix (caller-restructure).** The SAR-8 module's `VENDOR_FP_LIST` is keyed by canonical_name only (`Harris`, `Axon`, `Flock Safety`, `Genetec`), but the prior caller (`db.validation.phase3_inference_candidates.sar8_match` + `db.validation.sar8_bulk_stage._classify`) iterated over alias-strings, so `VENDOR_FP_LIST.get('Harris Corporation')` returned `[]` and the FP-substring check (`'harris adacom' in candidate_lower`) never fired — `HARRIS ADACOM CORPORATION` × 2 slipped through to the staged set despite being SAR-8-enumerated FPs.

   - **Fix shape (board-approved):** restructure the caller to invoke `vendor_match_disposition(candidate, canonical_name)` **once per canonical** (not once per alias-string), with an alias-equality predicate handling alias-string lookups. Bundle implementation with SAR-9 (one commit, not two) — the alias-bug fix is a caller-restructure that touches the same SAR-8 surface as the Motorola/WatchGuard FP-list extensions.

3. **WatchGuard Technologies (firewall) vs §2.1 WatchGuard Video (body-cam) disambig.** Add `watchguard technologies` as a `VENDOR_FP_LIST` hard-reject entry under canonical `WatchGuard`. The IEEE OUI vendor `WatchGuard Technologies, Inc.` is a network firewall vendor distinct from `WatchGuard Video` (the §2.1 police body-cam vendor). Concrete corpus impact at MAC-41: 4 FP rows (firewall) vs 2 TP rows (`WatchGuard Video` body-cam).

   - **No flag-for-review path.** The corporate-entity distinction is clear (firewall vendor vs body-cam vendor) and 4 rows is enough signal to commit to a hard-reject codification rather than kicking the can to flagged-for-review triage.
   - **Future-Wave caveat (recorded):** if a future Wave surfaces WatchGuard Technologies firewalls in surveillance/police adjacency (i.e., the firewall vendor legitimately ships into the §2.1 device-category space), this codification needs amendment. Current corpus has no such evidence.

**Reasoning.** MAC-41 Step-4 follow-on bulk-stage (411 rows inserted at strict §8.4 / `device_category='unknown'`) tripped a post-staging spot-check halt under the dispatch's stop-the-line clause ("New disambig class beyond SAR-8 → halt + comment; do NOT bundle silently"). Validator rolled back all 411 rows under §11 #11 discipline (audit ledger row inserted, `raw_observations.promoted_identifier_id` pointers cleared, Wave-A canonical `identifiers.id=1` preserved) and surfaced 3 halt-flags rather than silently bundling them into the staged set. The 66% FP rate on Motorola alone is non-trivial corpus-density signal — propose-don't-promote was the right discipline. Post-fix expected staged count drops from 411 to ~135 TPs (still a thin Phase-5 outcome — acceptable per §11 #8 propose-don't-promote-without-second-source).

**Implementation directive (per board approval [`234faaa7`](/MAC/approvals/234faaa7-e1c0-40fd-a247-f82cb588fc23)).**
- Update `db/extraction/vendor_name_disambig.py`:
    - Extend `VENDOR_FP_LIST['Motorola Solutions']` with substring-reject entries for `mobility`, `(wuhan)`, `lenovo`.
    - Add bare-`Motorola` flag-for-review semantics (third return state, mirrors GENETEC Corporation handling at SAR-8).
    - Extend `VENDOR_FP_LIST['WatchGuard']` with hard-reject entry for `watchguard technologies`.
- Update `db/extraction/vendor_name_disambig.py` callers (`db.validation.phase3_inference_candidates.sar8_match` + `db.validation.sar8_bulk_stage._classify`):
    - Restructure to invoke `vendor_match_disposition(candidate, canonical_name)` once per canonical entry (not once per alias-string).
    - Add dedicated alias-equality predicate for alias-string lookups.
- Re-scope §2.1 `Motorola Solutions` aliases column: drop bare `Motorola`; keep `Motorola APX`, `Motorola V300`, `Motorola V500`, `Motorola Vigilant`.
- Tests required: positive (`Motorola Solutions Inc.`, `MOTOROLA SOLUTIONS MALAYSIA SDN. BHD.`, model-line aliases) + negative (`Motorola Mobility LLC, a Lenovo Company`, `Motorola (Wuhan) Mobility Technologies`, `WatchGuard Technologies, Inc.`) + flag-for-review (bare `Motorola` token) + alias-iteration regression (`HARRIS ADACOM CORPORATION` rejects under restructured caller).
- Re-run bulk-stage post-fix: expected ~135 staged inferred rows (down from 411). Idempotent re-run produces byte-identical artifacts (modulo timestamp).

**Application timing and binding scope.**
- **Binds at Phase-5 Step-4 follow-on² dispatch (MAC-43).** SAR-9 codified now; implementation lands as Validator-execution against the MAC-41 SAR-8-applied candidate set, with the alias-iteration bug-fix bundled.
- **Does not retroactively rewrite Phase-4 wave dispositions** (Wave-A row promotion stands; identifiers.id=1 Flock Safety MAC preserved through MAC-41 rollback).
- **§7.3 / §7.4 contractual surface unchanged.** SAR-9 extends SAR-8 operational guidance; no bible-text edit beyond the §2.1 `Motorola Solutions` aliases column re-scope.
- **Why a SAR, not a Correction Pass.** Mirrors SAR-7 / SAR-8 relationship to §7.3/§7.4 (operational guidance binding implementation, not contract). The §2.1 alias re-scope is a lexicon-content change, not a §-text change.

**Bundling rationale.** Bundling SAR-8 alias-iteration bug-fix with SAR-9 codification (single ratification gate, single commit) was board-approved despite covering one amendment-log change (SAR-9) and one implementation-class change (alias-bug). Reasoning: the alias-bug fix is a caller-restructure that touches the same SAR-8 surface as the Motorola/WatchGuard FP-list extensions; bundling keeps blast radius contained at one validator-execution dispatch.

**Validator-quality acknowledgment.** This is the second consecutive halt-flag surface from Validator (SAR-8 at [MAC-39](/MAC/issues/MAC-39), SAR-9 here at [MAC-41](/MAC/issues/MAC-41)). Pattern is the §11 #11 + propose-don't-promote contract working as specified, not a Validator-process problem. Surface-and-ratify discipline is exactly what bounded-but-not-fully-enumerated SAR-N-class disambig classes require.

**MAC-41 reference.** Full halt-flag context + per-class FP/TP/ambiguous counts + rollback ledger lives in `extraction_outputs/mac41/sar8_bulk_stage_halt_flag.json`; Validator deliverable comment at MAC-41 [`a9404b0c`](/MAC/issues/MAC-41#comment-a9404b0c-33bc-490f-9b8a-4402d2ae8630); board approval at [`234faaa7`](/MAC/approvals/234faaa7-e1c0-40fd-a247-f82cb588fc23).

---

## Checkpoint 5 sign-off — Phase-5 close + §12 disposition slate

**Date:** 2026-05-06
**Source:** [MAC-47](/MAC/issues/MAC-47) CP5 brief authoring under CEO autonomy per board comprehensive forward-runway authorization at MAC-1 [`613ec532`](/MAC/issues/MAC-1#comment-613ec532-d8cb-4f0f-a35b-c811e2864d7d) 2026-05-06T17:08:16Z. Brief at `/home/kev/argus/CP5_BRIEF.md` (commit `28bab20`). Board ratification via approval [`71ef8139`](/MAC/approvals/71ef8139-c76c-4b1b-8971-b22720b7363d) approved 2026-05-06T20:17:10Z.
**Bible commit:** §12 dispositions land paired with this amendment-log entry (no §-text edits beyond §12 reorganization).

**The disposition slate.** Board ratified CP5 brief as the Phase-5 close artifact. Per CP5_BRIEF §4 + §7, the §12 Open-Questions slate is reorganized as follows:

### §12 dispositions ratified at CP5

| § / question | Disposition at CP5 | Notes |
|---|---|---|
| Project name "Argus" | **RESOLVED — final v1 name.** | Argus owns identifier-canonical-state + Talos-bound exports; Talos owns scanner-side scanning + correlation; "MAC" is the Paperclip issue-prefix only. |
| `device_cluster_id` schema column | **RESOLVED — SAR-3 lean confirmed final.** | Argus identifies, Talos correlates. No Argus-side schema change; correlation logic owned by Talos team. |
| MuckRock API vs search | **RESOLVED — moot.** | Phase-4 Wave-D path-(a) early-cut ([MAC-31](/MAC/issues/MAC-31)) used search; corpus-ceiling held at 0. |
| Inference 70-cap binding | **RESOLVED — 70-cap binding for inferred rows confirmed final.** | No current row pressure on the cap (all Phase-5 inferred rows landed at 50–55 per SAR-1 LAA-bit penalty + strict §8.4 conf=50 starting band). |
| Single-product §2.1 vendor OUI categorization (narrow §11 #10 vs strict §8.4) | **DEFERRED — to Wave-F / Phase-6.** | CP5_BRIEF §3.1 surfaced row-count visibility per disposition: ~18 of 62 inferred rows would flip under narrow read; all 17 stay below conf=70 high-conf band. Board ratified CEO path-(a): accept v0.1 with strict §8.4. Narrow-read carve-out queued for Wave-F / Phase-6 once model-level evidence raises a vendor cluster's per-row band into 70-cap territory. |
| §4.4 256-entry `mac_range` expansion ceiling | **DEFERRED — to Talos integration handoff.** | All 8 active `mac_range` rows are OUI-28/OUI-36 sub-allocations vastly exceeding §4.4's expansion ceiling. Board ratified CEO path-(c): defer routing semantics to Talos integration handoff (jointly bound between Argus export shape and Talos seeder protocol). |
| `argus_record_id` upsert semantics | **BOUND TO TALOS HANDOFF.** | Argus-side stable-id is in place (`argus_run_id` deterministic UUID5; `argus_record_id` = `identifiers.id`). Talos-side upsert vs destructive drop-and-reload is the open piece. SAR-2 lean (upsert) holds as intended direction; binding decision is bilateral. |
| `geographic_scope` filter for high-confidence Talos export | **OPEN — held for explicit board direction.** | CEO-recommended path: configurable string column on `identifiers`, default US, filter at export-time — would land as Correction Pass 7. Wave-A row currently at NULL placeholder; deferrable to Talos integration handoff. |
| WiGLE API credentials | **OPEN — pitch-binding carries forward.** | Pitch-behavior binding holds verbatim through 2026-05-18 (12 days remaining at HB36). |

### Phase-5 close attestations

- **§11 #1 (no fabrication):** held end-to-end across Phase-5. Wave-A row promotion source-attested; inferred rows explicit FP/TP/flag-for-review classification (SAR-8 + SAR-9); zero synthetic-value insertions.
- **§11 #6 (no live fetches at validation/export):** held. MAC-39/MAC-41/MAC-42/MAC-44/MAC-45/MAC-46 ran with `PRAGMA query_only = ON` or under controlled-write contracts. Zero outbound HTTP at Phase-5.
- **§11 #7 (provenance carry-through):** held. Every staged row carries `source_url` + `source_excerpt` + `extraction_run_id` lineage; `argus_record_id` = `identifiers.id` exposed at export time.
- **§11 #8 (no identifier promotion without ratification):** held. Wave-A row promoted only after MAC-38 §11 #8 ratification gate; inferred rows held at staged-`inferred` band; 4 inferred singletons held at conf=50 rather than uplifted absent cross-source corroboration.
- **§11 #11 (halt-the-line propose-don't-promote):** fired twice (MAC-39 SAR-8, MAC-41 SAR-9), both surfaced via Validator post-staging spot-check, both ratified live without additional rollback. The contract working as specified.
- **§11 #12, #13, #14:** all preserved end-to-end across MAC-45 + MAC-46 cross-checks; reconciliation halts at 0.

### Phase-5 close invariants (HB36)

- `identifiers` rowcount **121 total / 63 active** (1 Wave-A `alpr/mac` Flock Safety at conf=60 + 54 `unknown/oui` inferred at conf=55 + 8 `unknown/mac_range` inferred at conf=50–55).
- Talos export survivors: **1 standard / 0 high-conf** (Wave-A Flock at standard).
- `argus_run_id`: `25ded783-2dd0-537a-9067-5c0d7ceb05ce` (deterministic UUID5; idempotent across re-runs of unchanged DB state).
- Schema version `7`. Pre-state backup at `db/argus.db.pre_mac42_step5_backup` retained.

### Forward path

- **Default disposition (α — ongoing-maintenance).** Board ratified CP5 without selecting a downstream path; per CP5_BRIEF §7, default to (α). v0.1 ships; Wave-F + Talos handoff queued for explicit board direction at the next heartbeat.
- **(β) Wave-F dispatch** (model-level evidence sweep) and **(γ) Talos integration handoff** remain available as explicit board calls.
- **Autonomy-mode framework expires at CP5 sign-off** per HB35 boundary; board-class authority returns to default for any post-CP5 work.

**Why this is a checkpoint sign-off, not a Correction Pass / SAR.** No bible §-text edited; the §12 reorganization is the Open-Questions section being maintained per its own discipline. CP5 sign-off mirrors CP4 sign-off precedent (board-ratified close + bible-amendment-log entry recording the close + §12 disposition slate without bible §-text edit).

**MAC-47 reference.** CP5 brief at `/home/kev/argus/CP5_BRIEF.md` (commit `28bab20`); approval [`71ef8139`](/MAC/approvals/71ef8139-c76c-4b1b-8971-b22720b7363d).

---

## Correction Pass 7 — `geographic_scope` §12 #1 resolution + export-time filter

**Date:** 2026-05-07
**Source:** Lynceus v0.3 integration handoff bundle (path-γ); HB39 10-item bundled ratification proposal at MAC-1 [`f6c6e206`](/MAC/issues/MAC-1#comment-f6c6e206-51f5-4bee-a7db-b062d96cdf41); doc [`lynceus_v03_integration`](/MAC/issues/MAC-1#document-lynceus_v03_integration). Board ratification via comment [`4f075253`](/MAC/issues/MAC-1#comment-4f075253-2eae-4ea3-9db5-c67c6f02e012) 2026-05-07T17:10:13Z (six-pick + two-halt-flag bundle approved as recommended).
**Bible commit:** §12 #1 (Open) resolution + §7.5 export-time filter directive land paired with this amendment-log entry. Schema unchanged — `identifiers.geographic_scope TEXT` exists in 0001 schema since CP-0 (line 77 of `db/migrations/0001_initial.sql`).

**The resolution.** CP7 closes the §12 question "Configurable `geographic_scope` filter for the high-confidence Lynceus export." Resolution: **export-time categorical filter on `identifiers.geographic_scope`, default-on for high-confidence export, configurable.** Records remain in canonical DB regardless; only the export shape filters.

**Implementation directive (export-time logic, no schema change).**
- **Per-record population at extraction time.** Every `identifiers` row populates `geographic_scope` per §4.1 spec (ISO country/region codes, comma-sep, or `global`). Source-class defaults: structured-source rows inherit the source's country-of-origin (Atlas/DeFlock = `US` for US ALPRs, `NL`/`AU`/`IT` etc. for non-US deployments; FCC = `US`; SAM.gov = `US`; IEEE = `global`). Inferred rows inherit from the corroborating evidence's geographic-scope; `unknown` if no evidence; `global` for vendor-OUI-only rows where deployment geography is unknowable.
- **Wave-A row backfill.** The Wave-A Flock Safety MAC (`identifiers.id=1`) is currently NULL placeholder per CP5 carry-forward; backfill to `US` (Flock Safety is US-headquartered, US-deployed; source = DeFlock US-jurisdiction record).
- **Export-time filter.** Lynceus-bound exports (`argus_export.json`, `argus_export_high_confidence.json`) accept a `geographic_scope_filter` parameter. Default = `["US"]` for both exports (US-deployed Lynceus instances). Records with `geographic_scope` matching ANY filter element pass; records with `global` pass unconditionally; records with `unknown` pass into the standard export but NOT the high-confidence export. Records filtered out are tallied in `_meta.dropped_in_export` under a new key `geographic_scope_mismatch`.
- **Operator override.** Lynceus operators in non-US jurisdictions (e.g. `["NL"]`, `["AU"]`, `["EU"]`) configure via export CLI flag; Argus does NOT bake the filter into the canonical DB.

**§4.4 / §7.5 update directive.** §7.5 export shape adds `geographic_scope_mismatch` to `_meta.dropped_in_export`. Coverage report (§9 item 9) updates to include geographic-scope tally. §4.4 references `geographic_scope` as an export-time consideration alongside the type-mapping table.

**§12 disposition.** §12 #1 (Open) → **RESOLVED at CP7**. Strikethrough form preserves audit trail. The "Two adjacent realities" reasoning (DeFlock international ALPR + private-sector retail ALPR) holds: (a) is handled by the geographic_scope filter; (b) (private-sector / sector filter) remains at strict §8.4 unknown-category gate per CP5 disposition — sector is not currently a column.

**Why a Correction Pass, not a SAR.** §12 question resolution + §7.5 export-shape contract update + §4.4 cross-reference touch the bible's main §-text contract surface. Mirrors CP1/CP2 precedent for export-shape contract amendments.

**Lynceus-side migration cost.** Zero — Lynceus consumes filtered output; the filter is fully Argus-side.

---

## Correction Pass 8 — Description ceiling + §4.5 severity reframe-as-historical + §12 SAR-2 carry-forward amendment

**Date:** 2026-05-07
**Source:** Lynceus v0.3 integration handoff bundle (path-γ) — Lynceus engineer's Section 3 (description shape) + Section 4 (severity ownership) verbatim asks. Board ratification via comment [`4f075253`](/MAC/issues/MAC-1#comment-4f075253-2eae-4ea3-9db5-c67c6f02e012) 2026-05-07T17:10:13Z (Halt-flag #2 ✅ + Pick #2 ✅ + Pick #4 ✅).
**Bible commit:** §7.5 description-format directive update + §4.5 superseded-historical banner land paired with this amendment-log entry.
**Binds:** Export Worker (§7.5), all future export modules; Lynceus integration test cycle.

### Sub-correction A — Description format (§7.5)

**The change.** §7.5's description-format directive narrows from "≤80 char `{vendor} {product family or generic name} ({short context})`" to **"≤80 char flat `{vendor} {device_category}`"** per Lynceus's verbatim Section 3 ask. Drop the rich-seed pattern (e.g. `"Flock Safety ALPR camera"`); use flat form (`"Flock Safety alpr"`).

**Fallback patterns (Lynceus's ask):**
- Vendor known, category unknown: `"Unknown vendor {vendor}"` → reshaped to `"{vendor} unknown"` to keep `{vendor}` head-of-string convention.
- Vendor unknown (e.g. inferred from OUI without canonical-name match): `"Unattributed identifier"`.
- Both known: `"{vendor} {device_category}"` (flat). Examples: `"Flock Safety alpr"`, `"Hak5 hacking_tool"`, `"Axon body_cam"`.

**Why ≤80 not Lynceus's max.** Lynceus accepts longer descriptions but the alert-UI surface benefits from the tighter ceiling; the flat template fits comfortably within 80 chars for all current §2.1 vendor × device_category combinations.

**§7.5 examples updated.** Old examples (`"Hak5 WiFi Pineapple (pentest gear)"`, `"Axon Body 3 body camera"`, `"Apple Find My / AirTag service"`) struck; replaced with flat form (`"Hak5 hacking_tool"`, `"Axon body_cam"`, `"Apple ble_service"`).

### Sub-correction B — §4.5 severity reframe-as-historical

**The change.** §4.5 ("Severity for Lynceus export") gets a banner at section head: **"⚠️ Superseded as of CP8 (2026-05-07): severity is owned operator-side via Lynceus's `severity_overrides.yaml` file. Argus does NOT emit `severity` in the export shape. Section retained for audit-trail / historical-reasoning continuity."** §4.5's text body is preserved verbatim below the banner; future export modules MUST NOT consult §4.5 for severity values.

**Why reframe-as-historical, not full strike.** §4.5 contains the original severity-mapping reasoning (which Lynceus operators may consult when building their override file). Striking the section breaks the reasoning chain. The banner makes the supersession unambiguous while preserving the audit trail.

**§7.5 export shape update.** The `entries[]` schema drops the `severity` field. `_meta.dropped_in_export` retains all current keys; no new key needed (severity is no longer a category).

**Operator-override architecture (codified in CP10 below).** Lynceus operators configure severity per-vendor / per-device_category / per-record via `severity_overrides.yaml` operator-side. Argus ships vendor-attribution facts; Lynceus owns alerting policy.

### Sub-correction C — §12 SAR-2 carry-forward amendment

**The change.** §12 "Bound to Talos integration handoff" entry on `argus_record_id` upsert semantics gets text amendment from "lean is upsert" to **"v1 algorithm: `sha256(type|identifier)[:16]` hashes the §8.3 dedup key, stable across re-runs / confidence drift / source edits / vendor reattribution"** per SAR-10 ratification (below). The §12 entry itself migrates to "Resolved at CP8 (2026-05-07)" via SAR-10 binding.

**Why a Correction Pass, not a SAR.** §7.5 description-format contract + §4.5 superseded-historical banner + §12 disposition reorg all touch bible §-text. Mirrors CP1/CP2/CP5 precedent.

**Lynceus-side migration cost.** Zero for description (Lynceus accepts the flat form). Zero for severity (Lynceus's override file design absorbs the responsibility). One record (the Wave-A snapshot test artifact `d4bfc29b7d63f7b1`) needs re-import under the SAR-10 hash — see SAR-10 entry below.

---

## Correction Pass 9 — Talos → Lynceus rename slate (forward-looking contract surface)

**Date:** 2026-05-07
**Source:** Lynceus v0.3 integration handoff (path-γ) — Lynceus is the canonical name for the downstream consumer (Raspberry Pi RF security monitor; formerly working-name "Talos"). Board ratification via comment [`4f075253`](/MAC/issues/MAC-1#comment-4f075253-2eae-4ea3-9db5-c67c6f02e012) 2026-05-07T17:10:13Z (Pick #5 ✅ — α: keep `argus_export*.json` filenames + bible `Talos`→`Lynceus` rename throughout).
**Bible commit:** §-by-§ rename of `Talos`→`Lynceus` in PROJECT_BIBLE.md forward-looking contract surface lands paired with this amendment-log entry.
**Binds:** All future Argus documentation, exports, comments, integration artifacts.

### Rename scope

**File names UNCHANGED.** `argus_export.json` + `argus_export_high_confidence.json` + `argus_export.csv` retain existing naming convention per board's preserve-existing-convention directive. Export module function names + variable names + DB column names remain unchanged (e.g. `argus_record_id`, `argus_run_id`, `_meta` keys). Only natural-language references in PROJECT_BIBLE.md prose surface flip.

**§-by-§ rename slate (PROJECT_BIBLE.md §-text only).**
- **§4.4** "Talos export mapping" → **"Lynceus export mapping"** (header + body prose).
- **§4.5** "Severity for Talos export" → **"Severity for Lynceus export (superseded — see CP8)"** (paired with CP8's superseded-historical banner).
- **§6 Phase 5** prose references (Talos-consumable, Talos-bound) → Lynceus-consumable / Lynceus-bound.
- **§7.5** "Talos exports only" / "Talos-bound files" / "Talos seeder" → Lynceus equivalents.
- **§8.4** "Pi self-exclude list (running scanner's own hardware)" — "Talos runs on a Raspberry Pi" → "Lynceus runs on a Raspberry Pi".
- **§9** "Dropped from Talos export" → "Dropped from Lynceus export"; per-file Talos-consumable annotations → Lynceus-consumable.
- **§11 #12, #13, #14** — "Talos export" / "to Talos" → Lynceus equivalents.
- **§12 (Open + Resolved)** entries referencing Talos → Lynceus, with one exception (see Historical-record carve-out below).

### Historical-record carve-out (NOT renamed)

**BIBLE_AMENDMENTS.md historical entries (CP1 through CP6 + SAR-1 through SAR-9 + CP5 sign-off block).** These are the historical record. The board's "Talos was working-name through CP5" reasoning IS the historical truth. Retroactive rename would falsify the audit trail. Future amendment-log entries (CP7+ / SAR-10+) use Lynceus from inception.

**PROJECT_STATE.md historical heartbeat blocks.** Heartbeat-by-heartbeat record; not renamed. Future heartbeat blocks use Lynceus.

**CP4_BRIEF.md, CP5_BRIEF.md.** Frozen artifacts of their respective checkpoint sign-offs; not renamed.

**§12 "Resolved at CP5 sign-off" subsection in PROJECT_BIBLE.md.** Item 1 ("Project name") references "Talos owns scanner-side scanning + correlation" as part of the resolved boundary statement. This subsection IS in PROJECT_BIBLE.md (forward-looking contract) but it ALSO documents a CP5-sign-off boundary call. The board's resolution at CP5 used "Talos" as the working name; CP9 amends the boundary statement to read "Lynceus owns scanner-side scanning + correlation" per CP9 board ratification. Audit trail preserved via CP9 amendment-log entry.

**Why a Correction Pass, not a SAR.** Touches bible §-text contract surface across §4.4 / §4.5 / §6 / §7.5 / §8.4 / §9 / §11 / §12. CP1/CP2/CP5 precedent.

**Lynceus-side migration cost.** Zero — rename is internal to Argus's bible documentation surface.

---

## Correction Pass 10 — §11 #10 narrow-read v0.1 cutover + operator-override-as-FP-layer principle

**Date:** 2026-05-07
**Source:** Lynceus v0.3 integration handoff (path-γ) — board override of CP5 path-(a) deferral via Lynceus's `severity_overrides.yaml` operator-side architecture making FP-suppression revisable space. Board ratification via comment [`4f075253`](/MAC/issues/MAC-1#comment-4f075253-2eae-4ea3-9db5-c67c6f02e012) 2026-05-07T17:10:13Z (Pick #6 ✅ — full 17-row flip approved).
**Bible commit:** §11 #10 narrow-read carve-out codification + §-text update lands paired with this amendment-log entry. Argus DB row mutation: 17 rows flip `device_category` from `unknown` to specific category at v0.1 cutover.

### The codification (CP10 verbatim per board)

> *"Narrow §11 #10 read includes any §2.1 vendor whose product line includes the canonical surveillance category, regardless of whether the vendor also makes consumer/commercial variants of that category. Argus ships vendor-attribution facts; FP-suppression for multi-purpose vendors is handled by Lynceus operator-override file (`severity_overrides.yaml`), not by Argus-side gatekeeping. This preserves the most informative data export while delegating filtering to operator policy where context is known."*

### The 17-row flip (v0.1 cutover)

| Vendor | Current category | Flipped category | Rows | Source-class |
|---|---|---|---|---|
| DJI | `unknown` | `drone` | 13 | OUI inference (IEEE) |
| Flock Safety | `unknown` | `alpr` | 1 | inferred (non-Wave-A) |
| Skydio | `unknown` | `drone` | 1 | OUI inference (IEEE) |
| Cellebrite | `unknown` | `hacking_tool` | 1 | OUI inference |
| SoundThinking | `unknown` | `gunshot_detect` | 1 | OUI inference |

Total: **17 rows** flip. Hak5 listed prospectively (rule applies if Hak5 OUIs surface in future Wave; current set has 0 Hak5 OUIs).

**All 17 rows stay below conf=70.** Per CP5_BRIEF §3.1 row-count visibility, all 17 inferred rows currently sit at conf=50–55 per SAR-1 LAA-bit penalty + strict §8.4 starting band; they remain in `argus_export.json` (standard) but NOT `argus_export_high_confidence.json` until corroboration uplifts confidence.

### Operator-override-as-FP-layer architecture (codified)

**Argus side (data layer).** Argus ships factual vendor-attribution. Multi-purpose vendor records flow into the export with their factually-correct category attribution. No FP-suppression at the data layer.

**Lynceus side (alerting layer).** Lynceus operators configure `severity_overrides.yaml` per their threat model and operational context. Examples:
```yaml
vendor_overrides:
  - vendor: DJI
    severity: low   # or 'suppress' to drop entirely from alert UI
  - vendor: Skydio
    severity: low
```

**Why the architecture works.** Vendor attribution is factually correct and stable. Severity / suppression policy depends on operator context (urban vs rural, recreational drone density, threat model) which Argus cannot know. Operators see all DJI broadcasts (visibility); operators tune alert behavior (signal-to-noise).

### Explicit FP-risk callout (DJI primary, Skydio prospective)

**DJI integration handoff documentation (verbatim per board).**

> *"DJI is the highest-FP-risk vendor in the narrow-read set due to consumer market dominance (Mavic / Mini / Air series significantly outnumber LE-deployed Matrice 300/350 hardware in field broadcasts). Lynceus operators in dense urban or recreational drone-flying areas should expect frequent DJI matches; if FP volume is operationally noisy, suppress via `vendor_overrides: - vendor: DJI` entry in `severity_overrides.yaml`. Argus does not gatekeep this at the data layer because vendor-attribution is factually correct and operators benefit from visibility into all DJI broadcasts even when adjusting alert behavior."*

**Same callout pattern applies prospectively to Skydio** (if FP volume becomes operational concern) **and any future multi-purpose vendor added to §2.1.**

### §11 #10 §-text update directive

§11 #10 ("Do not categorize at the OUI level for multi-purpose vendors") gets a CP10 carry-forward amendment: the rule's enforcement is REFRAMED — Argus-side categorization of single-product-line §2.1 vendors (per CP10's narrow read) is permitted; FP-suppression for multi-purpose vendors is delegated to Lynceus operator-override layer. §8.4 references CP10 for the narrow-read carve-out.

### §12 disposition

§12 "Deferred at CP5 sign-off → Wave-F / Phase-6" entry on "Single-product §2.1 vendor OUI categorization at export time" → **RESOLVED at CP10 (2026-05-07)** with narrow-read v0.1 cutover. The deferral preserved in strikethrough.

**Why a Correction Pass, not a SAR.** §11 #10 contract amendment + §8.4 cross-reference + §12 disposition reorg + DB row mutation (17 rows flip). Mirrors CP3/CP5 precedent for §11 / §12 contract changes.

**Lynceus-side migration cost.** Lynceus engineer SHOULD include `severity_overrides.yaml` template + DJI/Skydio default-suppress example in the Lynceus integration test cycle delivery.

---

## Correction Pass 11 — Lynceus integration: dual-artifact contract (JSON-as-operational-feed + CSV-as-rich-import)

**Date:** 2026-05-07
**Source:** HB46 board JSON-vs-CSV reconciliation question at MAC-1 [`3e612a85`](/MAC/issues/MAC-1#comment-3e612a85-e2b4-4922-89ed-3552062cc25e) 19:35:34Z + CEO HB46 CP11 ratification proposal at [`447781e0`](/MAC/issues/MAC-1#comment-447781e0-d17d-4da3-a4dd-39f8552ed9b7) 19:41:23Z. Board ratification via comment [`cf5eeb79`](/MAC/issues/MAC-1#comment-cf5eeb79-d5dd-4ee2-b9ed-d148d224c533) 2026-05-07T20:08:08Z (sub-A + sub-B + sub-C bundle approved, with sub-A expanded to include `first_seen` + `last_verified`; `fcc_id` deferred to v1.1).
**Bible commit:** §7.5 dual-artifact contract sub-section + §6 Phase 5 #4 CSV description update land paired with this amendment-log entry.
**Binds:** Export Worker (§7.5), Lynceus integration test cycle, `lynceus-import-argus` v0.3 import CLI consumer.

### The reconciliation

`Lynceus_integration_spec_for_Argus.txt` Section 2 ratified board-side post-HB40 with a 5-required-+-11-optional-preserved per-entry field set ("no lossy conversion" principle). HB40 Pick #3 (Item 5 sequencing) had deferred per-entry-provenance expansion of the JSON `entries[]` shape pending exactly that Section 2 spec landing. The spec landed without an explicit CP-class notification routed back to Argus; Pick #3 became orphaned; the JSON exporter shipped the v1 §7.5 minimal entry shape (`pattern, pattern_type, description, argus_record_id`) per CP8-narrowed scope.

CP11 reconciles the divergence via a **dual-artifact contract** rather than a single-artifact bloat: `argus_export.json` stays minimal (operational alert feed shape), `argus_export.csv` becomes the rich-import feed carrying full provenance for Lynceus's `watchlist_metadata` side-table import. This satisfies Lynceus's "no lossy conversion" principle (provenance carried in the canonical-import path) AND preserves the JSON's small-payload framing for future streaming/runtime alert-feed use cases per `Lynceus_integration_spec_for_Argus.txt` section 7's "Argus global export, Lynceus operator-side filtering" framing.

### Sub-correction A — `argus_export.csv` shape extension (§7.5 + §6 Phase 5 #4)

The change. `argus_export.csv` field_order extends from 12 columns to 15:

```
argus_record_id, id, identifier, identifier_type, device_category, manufacturer,
model, confidence, source_type, source_url, source_excerpt, geographic_scope,
description, first_seen, last_verified, notes
```

**Population logic:**
- `argus_record_id` — call `db.export.argus_record_id.argus_record_id(row.identifier_type, row.identifier)` per SAR-10. 16-char hex.
- `description` — call existing `_format_description(row)` from JSON-write path (CP8 ≤80-char flat); fallback chain (`{vendor} {device_category}` → `{vendor} unknown` → `Unattributed identifier`) preserved verbatim. **Single source of truth — the same function powers both JSON and CSV.**
- `first_seen` — direct from `identifiers.first_seen` column (DATETIME).
- `last_verified` — direct from `identifiers.last_verified` column (DATETIME).
- `fcc_id` — **deferred to v1.1** (board ratification clause). Requires JOIN against `fcc_grantees`; defer until identified-need surfaces; revisit if Lynceus integration test surfaces a hard need.

**Filter posture.** CSV remains **unfiltered** (all active rows; currently 63). Operators apply geographic / category / confidence filters at Lynceus-side import per `Lynceus_integration_spec_for_Argus.txt` section 7 "Argus global export, Lynceus operator-side filtering" framing. CP7 `geographic_scope_filter` continues to apply to JSON only; does NOT apply to CSV.

### Sub-correction B — §7.5 dual-artifact contract sub-section

The change. §7.5 grows a new sub-section codifying the dual-artifact split:

> **Lynceus integration shape: dual-artifact contract — CP11 (2026-05-07) directive.**
>
> The v0.1 export ships two consumer-grade artifacts targeting distinct Lynceus consumer-side use cases:
>
> 1. **`argus_export.json`** — operational alert feed. Minimal entry shape `{pattern, pattern_type, description, argus_record_id}` per row. Designed for low-bandwidth / streaming / alert-oriented ingest. CP7 `geographic_scope_filter` applied (default `("US",)` plus `global` unconditional pass). CP8 ≤80-char flat description applied. Severity owned operator-side per CP8 sub-B. Companion file `argus_export_high_confidence.json` follows the same shape with `confidence_threshold=70`.
>
> 2. **`argus_export.csv`** — rich-import feed. Full canonical row shape with 15 columns per CP11 sub-A: `argus_record_id, id, identifier, identifier_type, device_category, manufacturer, model, confidence, source_type, source_url, source_excerpt, geographic_scope, description, first_seen, last_verified, notes`. **Unfiltered** — all active rows regardless of CP7 filter. Operators apply geographic / category / confidence filters at Lynceus-side import time.
>
> The split exists because: (a) JSON is sized for runtime alert-feed consumption where small payloads matter; (b) CSV carries full provenance for the import-once / store-in-watchlist_metadata workflow per Lynceus v0.3 schema migration 004. Together the two artifacts satisfy `Lynceus_integration_spec_for_Argus.txt` Section 2's "no lossy conversion" principle without bloating the alert-feed JSON.
>
> Symbol-table fields not present in either artifact (`fcc_id` requires JOIN against `fcc_grantees`): not exported in v1.0; deferred to v1.1+ as identified-need surfaces.
>
> Supersedes the HB39 Lynceus integration handoff doc §5.4 proposal ("ADD all 5 fields per-entry"). Spec compliance achieved via dual-artifact split rather than single-artifact bloat.

### Sub-correction C — `coverage_report.md` documents the artifact split

The change. `_build_coverage_report_md()` in `db/validation/export_lynceus.py` adds a new top-level section describing the dual-artifact contract + which artifact serves which Lynceus consumer-side use case (runtime alerts vs import-once provenance). Auto-regenerates on next export run.

### Sub-correction D — §6 Phase 5 #4 CSV description update

The change. §6 Phase 5 #4 line currently reading `argus_export.csv (human-readable, all canonical records)` updates to `argus_export.csv (rich-import feed; 15 columns per CP11; all active records, unfiltered)`.

**Why a Correction Pass, not a SAR.** §7.5 dual-artifact contract sub-section + §6 Phase 5 #4 line update + DB-export shape contract amendment all touch bible §-text. Mirrors CP7/CP8 precedent for export-shape contract amendments.

**Lynceus-side migration cost.** Zero for the v0.3 import CLI (`lynceus-import-argus`) — it consumes CSV and `watchlist_metadata` already has destination columns for the four new fields per Lynceus migration 004. No re-import beyond the standard CP11 sample-export redelivery cycle. JSON consumers (none in v0.3; future streaming alert ingest will benefit from the small-payload framing).

**Carry-forward rule.** Per [`feedback_text_replace_narrative_historical_safety`](memory) (codified at HB45): MAC-51 implementation dispatch MUST require explicit historical-narrative preservation for any text-replace operations across PROJECT_STATE.md / BIBLE_AMENDMENTS.md / coverage_report.md narrative; the v1 §7.5 minimal-entry-shape is the canonical contract for HB42 baseline and prior, and historical references to it stay intact.

---

## SAR-10 — `argus_record_id` algorithm: `sha256(type|identifier)[:16]`

**Date:** 2026-05-07
**Source:** Lynceus v0.3 integration handoff (path-γ) — Halt-flag #1 surfaced at HB39 (`argus_record_id` divergence between Wave-A snapshot hex `d4bfc29b7d63f7b1` and v1 Talos integer-id export; integer NOT stable under §8.3 dedup-driven supersede + reattribution per Lynceus's expected events). Board ratification via comment [`4f075253`](/MAC/issues/MAC-1#comment-4f075253-2eae-4ea3-9db5-c67c6f02e012) 2026-05-07T17:10:13Z (Halt-flag #1 ✅ — strong endorsement; codify as SAR-10 + CP8 §12 carry-forward text amendment).
**Bible commit:** SAR-10 amendment-log entry lands paired with CP8 §12 carry-forward text amendment (above). No further bible §-text edit.
**Binds:** Export Worker (§7.5), all future export modules, Lynceus seeder integration handoff.

**The algorithm.** `argus_record_id = sha256(f"{identifier_type}|{normalized_identifier}").hexdigest()[:16]`.

**Inputs:**
- `identifier_type`: §4.1 enum value (e.g. `mac`, `oui`, `bssid`, `ssid_exact`, `ble_uuid`, `mac_range`, etc.). Lowercase, no whitespace.
- `normalized_identifier`: per §4.3 normalization rules (MAC `aa:bb:cc:dd:ee:ff` lowercase colon-separated; OUI `aa:bb:cc` lowercase; UUID lowercase 8-4-4-4-12; SSIDs exact-as-broadcast).

**Output:** First 16 hex chars of the SHA-256 digest. Treated as opaque string; not human-meaningful, not human-derivable.

**Stability under §8.3 dedup events.**
| Event | argus_record_id behavior |
|---|---|
| Re-run of unchanged DB | identical hash (bit-for-bit) |
| Confidence drift (e.g. 50 → 65 → 70) | identical hash (confidence not in input) |
| Source edit (source_url changes, source_excerpt changes) | identical hash (source not in input) |
| Vendor reattribution under §8.3 (e.g. SAR-9 Motorola Mobility/Solutions split) | identical hash (manufacturer not in input) |
| Identifier merge under §8.3 (two records collapsing to one canonical) | dropped record's hash gone; surviving record's hash unchanged |
| Identifier supersede under §8.3 (`superseded_by` pointer set) | superseding record's hash unchanged; superseded record dropped from export |

**Stability under §11 #11 rollback.** Rollback drops the staged row; argus_record_id never persisted to export, so no Lynceus-side cleanup needed.

**Why this algorithm vs prior alternatives.**
- **`identifiers.id` (integer PK).** Drops on `superseded_by` reattribution (the dropped row's `id` never reappears; the surviving row's `id` is from a different lineage). Fails Lynceus's "stable across vendor reattribution" expected event.
- **`f"{run_id}|{id}"`.** `run_id` changes per export run; fails Lynceus's "stable across re-runs" expected event.
- **Hash of full record (vendor / confidence / source).** Mutates on confidence drift / source edits / vendor reattribution. Fails 3 of Lynceus's 4 expected events.
- **Hash of (type | identifier) only.** ✅ All 4 expected events stable. Hashes the immutable §8.3 dedup key.

**Implementation directive.**
- **Module:** Add `db/export/argus_record_id.py` with single function `argus_record_id(identifier_type: str, normalized_identifier: str) -> str` returning the 16-hex-char digest.
- **Export Worker (§7.5) integration.** Replace existing `entries[].argus_record_id` population with the SAR-10 algorithm. The `_meta.dropped_in_export` tally is unaffected.
- **Lynceus seeder integration.** Use `argus_record_id` as the upsert key (replaces the prior integer-id-as-upsert-key plan). Re-import on each Argus export = idempotent under unchanged DB state.
- **Tests required.**
    - Determinism: same input → same output (10× repetition, byte-identical).
    - Stability under confidence drift: row at conf=50 vs conf=70 → same hash.
    - Stability under source edit: row at source_url=A vs source_url=B → same hash.
    - Stability under vendor reattribution: row reattributed Motorola Mobility → Motorola Solutions → same hash (provided identifier unchanged).
    - Differentiation: different `identifier_type` for same identifier string → different hash; different identifier for same type → different hash.
    - Collision space: 16 hex chars = 64 bits = 1.8e19 distinct values; collision probability negligible at v1 row-count scale (<10k).

**Lynceus-side migration cost.**
- **One record** in the Wave-A snapshot test artifact (hex `d4bfc29b7d63f7b1`) needs re-import under the SAR-10 hash. The Wave-A canonical row is `identifiers.id=1`, `identifier_type='mac'`, `identifier='e4:aa:ea:80:a1:9b'` (Flock Safety alpr). New `argus_record_id` = `sha256("mac|e4:aa:ea:80:a1:9b").hexdigest()[:16]` (computed at export time). Notify Lynceus engineer in the integration test cycle delivery.

**§12 carry-forward (CP8 sub-correction C).** §12 "Bound to Talos integration handoff → `argus_record_id` upsert semantics" entry → **RESOLVED at SAR-10 (2026-05-07)**. Text amendment from "lean is upsert" to "v1 algorithm: `sha256(type|identifier)[:16]` hashes the §8.3 dedup key, stable across re-runs / confidence drift / source edits / vendor reattribution."

**Why a SAR, not a Correction Pass.** Operational rule binding export module implementation; no bible §-text contract change beyond §12 disposition reorg (handled by CP8 sub-correction C). Mirrors SAR-1/SAR-7/SAR-8/SAR-9 precedent for module-binding operational rules.

**Bundling rationale (CP7 + CP8 + CP9 + CP10 + SAR-10).** Five amendments bundled at one ratification gate per board's six-pick + two-halt-flag bundled approval at [`4f075253`](/MAC/issues/MAC-1#comment-4f075253-2eae-4ea3-9db5-c67c6f02e012). Reasoning: all five derive from the same Lynceus v0.3 integration handoff document; landing them as a coordinated commit preserves the audit trail's single-source attribution; Lynceus integration test cycle (downstream item) gates on all five being landed before a Lynceus-shaped sample export can be produced.

---

## SAR-11 — Wave G framework-UUID + third-party-library FP suppression (chunked Priority A/B/C/D)

**Date:** 2026-05-13
**Source:** Wave G pre-v1 autonomous static-analysis session 2026-05-10 (MAC-52 [`ddc193cd`](/MAC/issues/MAC-52#comment-ddc193cd-0dec-4fab-a83c-30b04f79506b); deliverables surfaced at MAC-1 [`5b000045`](/MAC/issues/MAC-1#comment-5b000045-1265-4be4-88b2-dfeaac46c6df) HB56). Board-ratified chunking structure at MAC-1 [`e492ac66`](/MAC/issues/MAC-1#comment-e492ac66-7109-412a-acb3-8db1d247310d) HB57 §E.2. SAR-11 codification landed at CP17 coordinated commit per HB99/HB101 drafts.
**Bible commit:** SAR-11 amendment-log entry lands paired with CP17 coordinated commit (this entry).
**Binds:** ExtractionWorker (Wave G `wave_g_extractor.py` FP-filter pipeline + `looks_like_third_party_lib()` path heuristic), Validator (§11 #7 promotion gate — pre-v1 candidates classified per these FP-classes at promotion-time).

**Authoritative machine-readable scope:** `android_test/extraction_outputs/wave_g_pre_v1/calibration/proposed_fp_classes.json` (16 calibration-window classes + 7 cohort-B-E classes + 1 Priority-A bug fix + ambiguous/validator-review cases). The §-text below summarizes the discipline; the JSON catalog is the operational reference for ExtractionWorker.

### Priority A — `looks_like_third_party_lib()` path-filter bug fix (immediate)

**Bug.** Wave G calibration surfaced that `looks_like_third_party_lib()` in `wave_g_extractor.py` required `/sources/<pkg>` (leading slash) but jadx emits relative paths starting `sources/<pkg>` (no leading slash). Path-based FP filter never matched; ~30 vendor-1 + ~60 vendor-2 FPs leaked through as candidates.

**Fix.** Replace leading-slash requirement with substring match supporting (a) jadx layout `sources/<pkg>`, (b) apktool smali layout `smali_classesN/<pkg>` + `smali/<pkg>`, (c) prefix-without-leading-slash forms. Priority A is the immediate operational fix that unblocks all downstream FP-class disambig.

### Priority B — high-evidence-count FP classes (single chunk)

Classes surfaced ≥4× in calibration window across two vendors:

- **`android_audioeffect_framework_uuid`** (BLE service UUID FP). Android `AudioEffect` framework identifiers (Mobile NS, AEC, AGC, etc.) used by WebRTC / AudioEffect API. Pattern: `-0002a5d5c51b` suffix is the AudioEffect vendor namespace. Disambig: exact value match + suffix pattern.
- **`bundled_fork_path`** (BLE service UUID FP). Apps bundling forked WebRTC / Twilio / Agora / LiveKit / tvo library code under non-standard top-level package paths. Disambig: path-substring match on `sources/livekit/`, `sources/tvo/`, `sources/org/webrtc/`, `sources/com/twilio/`, `sources/io/agora/`.
- **`third_party_analytics_sdk_application_id`** (BLE service UUID FP). UUIDs hardcoded as configuration IDs for FullStory / Datadog / LaunchDarkly / Sentry / Mapbox / Amplitude / Mixpanel / Bugsnag / Segment / Intercom / Pendo / Auth0 / Firebase / Crashlytics / Branch / Google. Disambig: line-context token set (BUILD_ID, APPLICATION_ID, PROJECT_ID, CLIENT_ID, API_KEY, SDK_KEY, APP_ID, vendor-specific prefixes, MAPBOX_TOKEN, GOOGLE_APP_ID) + cross-site value-propagation.
- **`kotlin_compose_composable_or_identifier_name`** (SSID FP). Strings matching SSID prefix that are actually Jetpack Compose composable function names, color names, theme names, UI element names. Disambig: pure-CamelCase shape check + UI-suffix match + Compose-keyword in line + `.smali` / `res/values/` source-path check.
- **`no_wifi_api_context_in_line`** (SSID filter requirement). SSID candidates MUST appear in same source line as a WiFi-related API token (`SSID`, `WifiConfiguration`, `WifiManager`, `WifiNetworkSpecifier`, `ScanResult`, `setSSID`, `getSsid`). Without WiFi context, vendor-prefixed strings are almost always UI element names or branding strings, not WiFi SSIDs.
- **`shared_preferences_or_json_key_name`** (credential FP). Short identifier-like values matched on field-declaration / preference-key context tokens (`KEY`, `getString`, `putString`, `FIELD`, `HEADER`, `EXTRA_`, `@SerializedName`, `@JsonProperty`).
- **`screaming_snake_case_constant_value`** (credential FP). Standalone SCREAMING_SNAKE_CASE values ≥8 chars containing underscores. Almost always Java/Kotlin constants, not credentials.
- **`transistorsoft_cordova_plugin`** (all categories FP). `transistorsoft.*` is a third-party Cordova plugin company. Surfaces in Cordova-based apps. Added to `looks_like_third_party_lib()` prefix list.

### Priority C — lower-evidence + cohort-B-E FP classes (single chunk)

Classes surfaced 1-3× in calibration or surfaced in cohort-B-E review:

- **`rfc6455_websocket_accept_magic`** (BLE service UUID FP). RFC 6455 WebSocket Accept-magic GUID `258eafa5-e914-47da-95ca-c5ab0dc85b11`. Used by any okhttp3/OkHttp-based app. Disambig: exact value match.
- **`androidx_work_workmanager_internal_uuid`** (BLE service UUID FP). androidx.work WorkManager internal placeholder UUID `95ed6082-b8e9-46e8-a73f-ff56f00f5d9d`. Disambig: exact value match.
- **`decompiler_string_concat_artifact`** (credential FP). jadx-decompiled string concatenation artifacts (leading `'+ `, trailing ` +'`, `'+ this.X'` inside value, ` + identifier + ` inside value). Disambig: regex pattern match on value.
- **`library_namespace_constant`** (credential FP). Values prefixed with `com.X.Y` / `io.X.Y` / `sdk.X.Y` namespaces. Disambig: value-prefix match.
- **`screaming_snake_case_constant_name`** (credential FP). Java idiom `static final String FOO_BAR = "FOO_BAR"`. Disambig: regex match on declaration pattern + value equals var name.
- **`template_placeholder_value`** (credential FP, cohort-B). `{refreshToken}`, `${X}`, `<X>`, `%s`, `%d` are template placeholders. Disambig: regex match on value shape.
- **`logback_or_log4j_error_message_string`** (credential FP, cohort-B). Long English-prose strings containing word "token" as part of error template. Disambig: value starts with error phrase + spaces in value + >30 chars.
- **`value_level_propagated_post_processing`** (all categories FP). Post-extraction join: if a (value_class, value) pair is FP-classified at any site, demote all candidates with same pair to FP. Disambig: post-extraction join on value.
- **`xmp_image_metadata`** (cohort-B). XMP image-metadata UUIDs in PNG/JPEG/MP4 binary headers and `META-INF/MANIFEST.MF` entries. Not BLE.
- **`date_misparsed_as_mac_oui`** (cohort-C). 6-octet date-formatted hex (e.g., `20:26:05:10:03:08`) misparsed as MAC OUI. Disambig: shape-check against ISO-8601-numeric form.
- **`placeholder_mac_oui_values`** (cohort-C). Documentation/test placeholder MAC OUI values (`aa:bb:cc:dd:ee:ff`, `01:02:03:04:05:06`, `de:ad:be:ef:*`). Disambig: explicit reject list per bible §7.3.
- **`rxjava_meta_inf_build_host_uuid`** (cohort-D). RxJava library `META-INF/MANIFEST.MF` Build-Host UUID surfacing in any RxJava-using app. Disambig: META-INF path + Build-Host context.
- **`uuid_v1_timeuuid_in_json_test_fixtures`** (cohort-D). UUID v1 time-based UUIDs in JSON test-fixture files. Disambig: UUID-version check + JSON-test-fixture path heuristic.
- **`json_test_fixture_company_id_uuids`** (cohort-D). UUID-shaped strings in JSON test-fixture `company_id` / `account_id` / `org_id` fields.
- **`microsoft_msal_azure_ad_uuids`** (cohort-E). Microsoft MSAL / Azure AD application/tenant UUIDs used for OAuth authentication. Disambig: MSAL package-name path + AzureAD context tokens.

### Priority D — Validator-judgment cases (per author labeling)

Cases the calibration surfaced but where author/Validator labels each instance individually rather than via a uniform FP rule:

- **`vendor_brand_string`** (proposed sub-class). Brand-only matches (literal vendor company name appearing in the vendor's own app). Distinct from true product-family taxonomy. Proposed confidence band: 50-70 (informational, not actionable). Reserve product-family 90-95 band for true sub-product names.
- **Ambiguous product-family hits** (per-instance Validator judgment). Examples surfaced in calibration: Flock `Raven` confirmed real Flock Raven audio sensor; promote at 90-95. Other ambiguous CamelCase product-name candidates: Validator labels per-instance per-context.

**Operational sequencing.** Priority A bug fix lands in the CP17-D code-sibling commit per standard CP precedent (CP14/CP15/CP16 paired-commit pattern). Priorities B + C codify as a single chunk in this SAR-11 row. Priority D labels emerge per-candidate at Validator-promotion time; aggregate findings may seed a future SAR-11 amendment if patterns crystallize.

**Composition with bible rules.** SAR-11 composes with bible §11 #1 (no fabrication — FP-classed candidates do NOT promote to `identifiers`), §11 #4 (no detection logic — SAR-11 is FP suppression, not scanner rule), §11 #6 (no ToS violations — calibration runs on legally-acquired binaries per §11 #15 license posture), §11 #7 (no promotion without provenance — Priority A bug fix ensures provenance-bearing candidates aren't lost to incorrect FP filter), §11 #8 (no confidence drift — FP demotion is a category-correction not a confidence-floor change).

---

## Correction Pass 12 — Wave G (Phase 6) vendor companion app static analysis: §8.2 `manufacturer_app` confidence bands + §11 #15 license-posture rule + §12 three open questions

**Date:** 2026-05-08
**Source:** [MAC-52](/MAC/issues/MAC-52) — Wave G ratification proposal at plan document rev 1 (`c4c12502`); board ratification via comment [`ddc193cd`](/MAC/issues/MAC-52#comment-ddc193cd-0dec-4fab-a83c-30b04f79506b) 2026-05-08T05:24:21Z (request_confirmation `df6ce24d` auto-superseded by ratifying board comment per `supersedeOnUserComment: true`; comment text is the authoritative ratification with detailed direction across all 10 §11 decision points).
**Bible commit:** §8.2 `manufacturer_app` row + sub-banding table + §11 #15 new hard-rule + §12 three new open questions land paired with this amendment-log entry.
**Binds:** SourceWorker (Wave G Step 0/1), ExtractionWorker (Wave G Step 2), Validator (Wave G post-Step-2 promotion), CEO orchestrator, future quarterly refresh routine.

**Naming note.** The board comment authorized these amendments as "Correction Pass 11"; CP11 is already taken by the Lynceus dual-artifact contract (commit `c2ef963`). Landed here as **CP12** to preserve audit-trail uniqueness; surfaced for board acknowledgement at MAC-52 close. Substance unchanged from board direction.

### Corrections applied

1. **§8.2 — add `manufacturer_app` source_type with five-class sub-banding.** Outer band `60–95`. Sub-bands per identifier class:
   - Hardcoded BLE service UUIDs (128-bit or 16-bit-in-context) → `80–95` (BLE specs require service UUID for discovery; vendor app must contain canonical value).
   - Default SSID patterns (vendor-prefix WiFi names) → `70–85` (clear vendor attestation; hardware match TBV at scan time).
   - Default credential strings (plaintext only; encoded/hashed dropped) → `60–80` (vendor-attested at app version; firmware may have rotated).
   - MAC OUI from validation code path → `75–90` (cross-checks against IEEE Tier-1 registry; disagreement → manual flag).
   - Product-family taxonomy (model names, internal hardware IDs) → `90–95` (vendor's own product naming inside their own app).

   Default per-row confidence at extraction time = midpoint of relevant sub-band. SAR-7/SAR-8/SAR-9 corroboration adjusts up; framework-string proximity, single-app-only surfacing, or cross-vendor-default appearance adjusts down. SAR-11 (proposed; gated on Step-2 calibration of first 2 vendor apps) handles framework-UUID and third-party-BLE-library FP classes if calibration shows >5% FP rate from those sources. §8.4 strict-promotion rule (≥80) applies as written.

2. **§11 #15 — new hard-rule: do not commit decompiled vendor app source code, raw APK/IPA contents, or extracted decompile artifacts to the git index.** Operational details: raw APK/IPA binaries land at `raw/vendor_apps/<vendor>/<app_package_id>/<version>/<sha256>.{apk,ipa}` for provenance only and are gitignored; decompiled `.java` / smali / dumped Mach-O headers live in workspace-only scratch directories during ExtractionWorker runs and are cleaned at end of run; only extracted identifier *candidates* (value + relative file path within the decompile output) land in `raw_observations`. The git index never contains vendor-proprietary source. This codifies the §11 #2 license-posture confirmation the board called out under "Bible amendments authorized" — operationalizing the §1201 + 37 CFR §201.40(b) reverse-engineering exemption boundary (research permitted; redistribution of decompiled source not).

3. **§12 — three new open questions under a new "Wave G (Phase 6)" subhead.**
   - **DMCA-takedown counter-notice template.** Pre-draft a counter-notice template under §512(g) at `wave_g/LEGAL_POSTURE.md` for cases where a vendor issues a DMCA takedown for a Wave G finding in published exports. Reliance: §1201 + §201.40(b); identifiers are facts (Feist), not copyrightable expression; Argus does not republish vendor source. Cross-reference from `THREAT_MODEL.md` at public-release prep so external readers understand the legal grounding. Surface for board review at Wave G Step 0 close.
   - **EULA-conflict-policy.** Per-vendor judgment criteria for app-EULA conflicts with reverse-engineering: (a) hostile EULA + low yield-value → exclude; (b) hostile EULA + high yield-value → surface to board; (c) standard reverse-engineering clause + standard yield-value → include (boilerplate prohibition is preempted by §1201 in US); (d) anti-circumvention clause specifically targeting security research → exclude (rare). Borderline cases come back to board. Surface specific vendor EULA concerns as Step-0 ground-truth deliverable.
   - **Wave-G-vs-Wave-G.5 iOS deferral rationale.** Wave G is Android-first because Apple FairPlay encrypts most app binaries (decryption requires jailbroken iOS device) and most surveillance vendors with iOS apps also publish Android — Android-first captures the same vendor coverage at lower legal/operational cost. Wave G.5 / Phase 7 surfaces as a separate board-class proposal *after* Wave G Steps 1+2 complete and Android yield is empirically known. Specific Wave G.5 trigger: Step 0 surfaces a vendor that has *only* iOS app and significant yield-value — flag for targeted Wave G.5 dispatch.

### §11 #11 self-binding satisfied

This entry is itself the §11 #11 amendment-log entry pairing for the §8.2 + §11 #15 + §12 in-place edits. Bible HEAD bumps from `c2ef963` (CP11) to the CP12 commit landed alongside this entry.

### Wave G dispatch sequencing (board-ratified, executed across heartbeats post-CP12)

Per board ratification comment [`ddc193cd`](/MAC/issues/MAC-52#comment-ddc193cd-0dec-4fab-a83c-30b04f79506b):

1. CP12 lands (this commit) — coordinated bible amendment.
2. CEO creates Wave G Step 0 child issue under MAC-1 (`status=backlog`, assignee=SourceWorker `9cf8ff12-…`). **No execution.** Wave G holds in backlog until: (i) Lynceus integration test confirms (engineer-side; board-routed); (ii) [MAC-50](/MAC/issues/MAC-50) public-release planning deliverables document lands; (iii) public release v1.0.0 ships.
3. Post-v1.0.0 ship: Wave G Step 0 dispatch fires as fresh board-class proposal (autonomous mode expired at CP5; CEO honors that).
4. Steps 1+2 follow standard wave pattern under sustained-execution + chain-don't-exit; calibration window = first 2 vendor apps fully processed; SAR-11 codified if Step-2 calibration shows >5% framework-UUID FP rate.
5. Validator promotes Wave G findings to Layer 1 per §11 #8 gate.
6. v1.1.0 release with Wave G yield baked in.
7. Quarterly refresh cron deploys post-v1.1.0 ship: cron `0 9 1 */3 *` (1st of Jan/Apr/Jul/Oct, 09:00 UTC), skip-on-overlap, no-catch-up, ≤4h wall-clock per fire.

### Decision points ratified at this gate (board direction recorded for audit trail)

Quoting board direction at [`ddc193cd`](/MAC/issues/MAC-52#comment-ddc193cd-0dec-4fab-a83c-30b04f79506b) verbatim per decision point:

1. **Download channel** — APKMirror primary; APKPure secondary; `gplay-api` / `gplaycli` tertiary (only if APK unavailable on archives; document Google ToS gray-area exposure per-vendor); vendor direct download quaternary (preferred when available — vendor-attested distribution). Per-vendor channel selection ratified at Step 0 close.
2. **Vendor list** — 20 Android-first + 5 indirect (per plan §2). Step 0's first deliverable is per-vendor availability ground-truth; flag vendors with no public Android app for Wave G.5 (iOS-only) deferred scope. Board edge-case direction recorded: Cellebrite (predominantly enterprise; surface availability + recommended scope), Hak5 (consumer/maker; ground-truth at Step 0), Harris (almost zero consumer footprint; defer to Wave G.5 with FOIA-firmware path), DJI (multi-app footprint — DJI Fly, GO 4, RC, Matrice — analyze all in scope; cohort by app rather than collapsing).
3. **SAR-11 gate** — gated on Step-2 calibration; calibration window = first 2 vendor apps fully processed. Critical FP-class enumeration board-supplied: OS framework UUIDs (Apple Find My, Apple Continuity, Android system, Bluetooth GATT standards `0x180F` / `0x1800` etc.); third-party BLE library UUIDs (Nordic Semi UART `6e400001-b5a3-f393-e0a9-e50e24dcca9e`, TI BLE stack defaults, Espressif chipset); cross-vendor SDK UUIDs (RxBluetooth, Polidea RxAndroidBle, BluetoothKit); generic Bluetooth standard service UUIDs (battery, device info, generic access/attribute); third-party analytics SDK UUIDs (Firebase, Crashlytics, Amplitude). Validator must explicitly sweep these classes during 2-app calibration and surface findings as SAR-11 candidate scope. **No promotion to Layer 1 until calibration completes and SAR-11 (if needed) lands.** If calibration surfaces no novel FP classes, surface that determination explicitly rather than codifying a no-op SAR.
4. **Retention threshold** — 5 GB LFS escalation gate approved (20–40 apps × ~100 MB ≈ 2–4 GB raw + ~1–2 GB multi-version + ~1 GB iOS headroom). If Step 1 download volume approaches 5 GB, worker stops + reassigns CEO; CEO surfaces LFS-vs-prune decision to board.
5. **Cadence** — quarterly cron `0 9 1 */3 *` approved, skip-on-overlap + no-catch-up; runtime budget per cron ≤4h wall-clock; halt + alert on overrun.
6. **Kill-switch** — approved. Trip criteria: 0 BLE UUIDs across first 2 apps after FP filtering = trip; 0 SSIDs after FP filtering = trip; 0 credentials after FP filtering = trip. Any single class tripping = surface to board (don't auto-continue). All three tripping = strong signal hypothesis is wrong; board reassesses sequencing.
7. **Sequencing — Path A (sequential, not interleaved).** Wave G executes AFTER public release v1.0.0 ships. Wave G yield ships as v1.1.0. Strict order: Lynceus integration test confirms → [MAC-50](/MAC/issues/MAC-50) deliverables document lands → public-release prep work executes → v1.0.0 ships → Wave G Step 0 fires as fresh board-class proposal → Steps 1+2 + calibration + ratification → SAR-11 codified if needed → Validator promotion → v1.1.0 release with Wave G yield. Wave G remains in `backlog` until v1.0.0 ships.
8. **EULA conflict policy** — DMCA §1201 security-research exemption + §201.40(b) cover static analysis of legally-acquired binaries. Per-vendor judgment criteria recorded under §12 EULA-conflict-policy entry. Document §1201 reliance in `wave_g/LEGAL_POSTURE.md`; cross-reference from `THREAT_MODEL.md` at public-release prep.
9. **iOS scope** — deferred to Wave G.5 / Phase 7 (Apple FairPlay encryption + Android-first vendor coverage justification). Specific exception: Step 0 surfaces a vendor with iOS-only significant-yield → flag for targeted Wave G.5 dispatch.
10. **Budget envelope** — Step 0 ≤5 heartbeats; Step 1 ≤10 heartbeats (sustained-execution covers ~5–10 vendor downloads per heartbeat); Step 2 ≤30 heartbeats; total ≤50 heartbeats wall-clock for Steps 0–2 combined. Budget overrun trip: any stage exceeds its cap by >50% → worker halts + surfaces to CEO. Estimated wall-clock with sustained-execution + chain-don't-exit active: 2–4 days.

### Worker assignments (no new hires required)

- Step 0 + Step 1: **SourceWorker** (`9cf8ff12-53c3-4f83-837f-3142d8d1d151`).
- Step 2: **ExtractionWorker** (`1347736c-…`).
- Post-Step-2 Layer-1 promotion: **Validator** (per existing Phase-5 §11 #8 promotion gate).

### §12 Open Questions impact

Three new open questions added under a new "Wave G (Phase 6)" subhead per #3 above. No existing §12 entries resolved by this pass. WiGLE pitch-binding and pre-CP5 deferred items unchanged.

### Why a Correction Pass, not a SAR

§8.2 outer-table addition + §11 hard-rule addition + §12 question additions all touch bible §-text. Mirrors CP1 / CP3 / CP5 / CP6 / CP7 / CP8 / CP9 / CP10 / CP11 precedent for bible §-text contract amendments.

---

## Correction Pass 13 — CP12 schema sibling: §4.1 `identifier_type` + `source_type` enum extensions (Wave G structural fidelity)

**Date:** 2026-05-10
**Source:** [MAC-54](/MAC/issues/MAC-54) — Validator dispatch authored to close the §11 #11 amendment-log gap surfaced at HB62 (pre-flight Step-0 schema-enum BLOCKER: CP12 added `manufacturer_app` to §8.2 source_type sub-banding without a sibling schema migration). Board ratification of Path X (single coordinated migration) at MAC-1 [`9d568fa7`](/MAC/issues/MAC-1#comment-9d568fa7-edc0-4d68-a7dd-fb40d4cd919e) 2026-05-10 HB63. CEO Step-0 ratification of the dispatch at MAC-54 [`34c908b8`](/MAC/issues/MAC-54#comment-34c908b8-0a66-4a6f-a3a5-4aa6d2bc5470) 2026-05-10.
**Bible commit:** §4.1 `identifier_type` enum row + §4.1 `source_type` enum row + §4.4 Lynceus-mapping new-row entries land paired with this amendment-log entry; migration `db/migrations/0009_manufacturer_app_and_identifier_type_extensions.sql` + wrapper `db/validation/migration_0009_verify.py` land in the same coordinated commit.
**Binds:** Validator (§11 #7 promotion gate, §7.4 record validation), ExtractionWorker (raw_observations staging shape for Wave G outputs), Export Worker (§7.5 / §4.4 Lynceus mapping for the three new identifier types — all DROPPED-class per analytical-only fidelity), SourceWorker (registers vendor companion app sources with `source_type='manufacturer_app'`).

### Why this Correction Pass exists

CP12 (commit `90132fa`, 2026-05-08) added `manufacturer_app` to §8.2 source_type sub-banding to define the confidence band for Wave G (Phase 6) vendor companion app static-analysis output, but did not land the sibling schema migration. The `identifiers.source_type` and `sources.source_type` CHECK constraints from `0001_initial.sql` (lines 71–75 and 120–124) still reject the value, structurally blocking Wave G narrow-scope promotion (21 candidates: 6 BLE UUIDs + 1 BLE local name + 14 Flock DeviceType taxonomy values).

In parallel, the Wave G pre-v1 deliverables (2026-05-10 HB56, MAC-1 [`5b000045`](/MAC/issues/MAC-1#comment-5b000045-1265-4be4-88b2-dfeaac46c6df)) surfaced three new identifier classes that do not fit the existing §4.1 `identifier_type` enum without semantic-loss collapse:

- **BLE local name** (the literal string `Penguin` broadcast over GAP scan response) — distinct from a service or characteristic UUID; collapsing to `ble_uuid` or `ssid_pattern` would falsify the structural surface.
- **BLE characteristic UUID** (paired with the `ble_service` UUID in GATT, surfaced as distinct in the Wave G handoff) — distinct from a service-level UUID; preserving the distinction matches §4.4's DROPPED-class analytical-only fidelity convention.
- **Product-family codename** (vendor's internal taxonomy strings — Flock's `DeviceType` enum values surfaced from operator-app static analysis) — vendor's own product naming inside their own app per §8.2 sub-banding (90–95 band).

Board HB63 ratified **Path X — single coordinated migration** to close both the schema-sibling gap and the structural-fidelity gap in one commit.

### Corrections applied

1. **§4.1 `identifiers.identifier_type` enum row** — extended from 9 values to 12. New values appended:
   - `ble_local_name`
   - `ble_characteristic`
   - `product_family_codename`

2. **§4.1 `identifiers.source_type` enum row** — extended from 8 values to 9. New value appended:
   - `manufacturer_app` (CP12 schema sibling)

3. **§4.4 Lynceus export mapping** — three new rows added to the `identifier_type → pattern_type` collapse table. All three new types map to **DROPPED-class** (analytical-only, no Lynceus surface):
   - `ble_local_name` → (DROPPED) — Lynceus has no GAP local-name match in v0.3; carried in canonical DB for analytical reuse.
   - `ble_characteristic` → (DROPPED) — Lynceus discovers by service UUID, not characteristic; carried analytically. (Distinct from `ble_service`, which collapses to `ble_uuid`.)
   - `product_family_codename` → (DROPPED) — taxonomy / cohort strings; analytical-only.

4. **Schema migration `0009_manufacturer_app_and_identifier_type_extensions.sql`** — table-rebuild pattern (SQLite CHECK constraints are table-level; per https://sqlite.org/lang_altertable.html section 7). Three CHECK constraints extended in a single coordinated commit:
   - `identifiers.identifier_type` ← + 3 values (above)
   - `identifiers.source_type` ← + 1 value (above)
   - `sources.source_type` ← + 1 value (above; mirrors §4.1 enum-parity convention)

   Self-referencing FK `identifiers.superseded_by → identifiers(id)` preserved across the rebuild via the standard `PRAGMA foreign_keys = OFF` envelope + `PRAGMA foreign_key_check` integrity assertion before commit. Schema version bumps 8 → 9.

5. **Wrapper `db/validation/migration_0009_verify.py`** — operationalizes the §11 #11 spot-check around the rebuild: pre/post row-count parity (121 identifiers + 12 sources), index-set preservation (5 identifiers indexes + 1 sources index), self-FK map preservation, post-state `PRAGMA foreign_key_check` returns 0 rows, CHECK enum extensions present in post-state DDL, canary INSERT smoke-test for each new enum value inside a SAVEPOINT (rolled back to leave zero residue), audit row written to `extraction_runs`. Idempotency boundary — re-runs short-circuit on `MAX(version) FROM schema_version >= 9`. Mirrors MAC-48 `cp7_cp10_v01_cutover.py` precedent.

### §11 hard-rule discipline (cite verbatim from bible HEAD `90132fa`, pre-CP13 lines)

- **§11 #1 (no fabrication)** — every new CHECK enum value cites canon: `manufacturer_app` from CP12 §8.2 + BIBLE_AMENDMENTS.md CP12 entry; the three new identifier-types from `android_test/extraction_outputs/wave_g_pre_v1/HANDOFF_TO_VALIDATOR.md` §"Headline findings" + board HB63 Path X ratification.
- **§11 #7 (no promotion to main table without provenance)** — migration is schema-only; zero `identifiers` row writes. Wave G narrow-scope promotion is the subsequent MAC-55 dispatch under the §11 #7 promotion gate; CP13 unblocks the schema surface without bypassing the gate.
- **§11 #8 (no confidence drift)** — no `confidence` column writes; no row mutations beyond the column-preserving `INSERT INTO X_new SELECT * FROM X` rebuild copy.
- **§11 #11 (amendment-log discipline)** — this entry IS the §11 #11 closure for the CP12 schema-sibling gap. The discipline rule binds CP-class edits to amendment-log entries; CP12 paired §8.2 and §11 #15 with the amendment log but missed the §4.1 schema-row sibling. CP13 closes the gap and operationalizes the rule per `feedback_enum_amendment_needs_schema_migration_sibling` codified at HB63.
- **§11 #15 (no decompiled vendor source in git index)** — N/A; schema migration carries no decompile artifacts.

### Sequencing post-acceptance (per board HB63 ratification)

1. **MAC-54 ratified** (this commit) — coordinated commit lands: migration 0009 SQL + wrapper + CP13 amendment-log entry + §4.1 / §4.4 PROJECT_BIBLE.md edits. CEO performs §11 #11 amendment-text review + line-by-line SQL review at the ratification gate.
2. Migration applies on local DB (CEO-class action via the wrapper); schema CHECK constraints extended; schema_version → 9.
3. CEO dispatches MAC-55 — narrow-scope promotion contract (21 entries: 6 BLE UUIDs at conf 80–95, 1 BLE local name "Penguin" at conf 70–85, 14 Flock DeviceType taxonomy at conf 90–95) to Validator.
4. Board ratifies MAC-55 promotion contract.
5. Validator runs §11 #7 / §11 #8 promotion gate on 21 entries; entries land in `identifiers` with appropriate `(identifier_type, source_type)` per the now-extended schema. Per §4.4 mapping (above), the 14 product_family_codename + 1 ble_local_name + (paired) ble_characteristic rows go DROPPED-class at export; the 6 ble_service / ble_uuid pairs flow through to Lynceus `pattern_type='ble_uuid'`.

### §12 Open Questions impact

No existing §12 entries resolved by this pass. CP12 Wave G (Phase 6) §12 entries (DMCA counter-notice template, EULA-conflict-policy, Wave-G-vs-Wave-G.5 iOS deferral rationale) unchanged. WiGLE pitch-binding and pre-CP5 deferred items unchanged.

### Why a Correction Pass, not a SAR

§4.1 enum-row extensions + §4.4 Lynceus-mapping additions are in-place bible §-text edits. CP-class is the right framing per CP11 / CP12 precedent for bible §-text contract amendments. SAR is reserved for operational-rule binding without bible §-text change.

### §11 #11 self-binding satisfied

This entry is itself the §11 #11 amendment-log pairing for the §4.1 / §4.4 in-place edits in this coordinated commit. Bible HEAD bumps from `90132fa` (CP12) to the CP13 commit landed alongside this entry.

---

## Correction Pass 14 — Wave-A close: §8.4 four-amendment batch (G-1/G-4/G-13.3/G-15) + §11 #12 expansion + 5 schema migrations

**Date:** 2026-05-11
**Source:** [MAC-63](/MAC/issues/MAC-63) — Wave-A CEO Ratification Run. Human-CEO (Kev) delegated Bible §11 #11 amendment authority to CEO Claude for this run because they wanted to review the *output* rather than the *inputs* one-by-one. Phase 1 (drafting) ratified by board comment [`02ad16b0`](/MAC/issues/MAC-63#comment-02ad16b0-c8a2-47cd-831d-26e067c8a822); Phase 2 (CEO-skeptic self-review with §8.2 vs §8.3 catch + 4 revisions) ratified by board [`bbb71be5`](/MAC/issues/MAC-63#comment-bbb71be5-67fa-48ea-8c4c-8a1fc3797c0a); Phase 3 DDL fold-in ratified by board [`6516a9af`](/MAC/issues/MAC-63#comment-6516a9af-9d73-4134-b8f4-cc44085e63ef); Phase 3 application + this coordinated commit at heartbeat 2026-05-11.
**Bible commit:** PROJECT_BIBLE.md §8.4 four-amendment batch + §11 #12 expansion + BIBLE_AMENDMENTS.md CP14 entry (this entry) + 4 draft files moved from `raw/wave_a/_bible_amendment_*` to `bible/history/cp14/` for audit trail. Single coordinated commit titled "CP14: §8.4 four-amendment batch (G-1/G-4/G-13.3/G-15)".
**Schema-sibling commits (5 separate migration commits per dispatch §3.1):**
  - `db/migrations/0010_behavioral_signatures.sql` (new TABLE per MAC-58 §5 Option B)
  - `db/migrations/0011_ble_manufacturer_id_identifier_type_extension.sql` (G-3)
  - `db/migrations/0012_paired_identifier_id.sql` (G-7 — paired_identifier_id + pair_kind columns)
  - `db/migrations/0013_drone_rid_and_proprietary_protocol_identifier_types_extension.sql` (G-9 + Phase-4 fold-in; 13 new types)
  - `db/migrations/0014_surveillance_metadata_identifier_types_extension.sql` (G-10 alpr_model only; operator_profile HELD as G-17)
  - `db/schema_post_cp14.sql` (audit dump; schema_version=14)
**Binds:** Validator (§11 #7 promotion gate — Phase-4 promotion-cycle-1 next heartbeat under the §8.4 amendments + new schema), ExtractionWorker (raw_observations staging shape for the 13 new identifier_types from 0013), Export Worker (§7.5 — new `self_exclude_defensive_tool` bucket per G-15; `pair_kind` interactions in the export shape), SourceWorker (Wave-B+ continues staging into the now-extended schema).

### Why this Correction Pass exists

Wave-A (autonomous-run dispatch 2026-05-11 covering Phases 1-2-3-4-6) extracted ~1,162 candidate observations across 14 returned agents + 1 Opus sub-agent (G-4 LA-bit amendment draft). Wave-A produced 16 CEO gates (G-1 through G-16 with sub-items) representing Bible amendment candidates, schema-migration drafts, and validator-side discipline questions. The CEO Ratification Run consolidates the four §8.4 amendment-class gates into a single coordinated CP14 batch:

- **G-1** standards-body protocol-container OUI lens (FA:0B:BC ASD-STAN n=5, 50:6F:9A Wi-Fi Alliance NAN n=3, 90:3A:E6 Parrot dual-lens n=4)
- **G-4** Locally-administered (U/L=1) OUI pairing discipline (sub-agent draft 2026-05-11; bit-math verified Phase 2; DB sibling-presence verified for 60:60:1f id=431/509 DJI)
- **G-13.3** Hardware-anchor model-level evidence (Phase-2 self-review aligned with §8.2 source-bands; dropped initial parallel H1/H2/H3 tier framing; Falcon-gen1 ↔ Snapdragon 625 single-source ceiling 75 under `crowdsourced` band)
- **G-15** Defensive-tool operator-side hardware self-exclude (Pi self-exclude mechanic extended to USB VID:PID + diag-interface + Rayhunter-supported modem family; §11 #12 update in parallel)

In parallel, five schema migrations sibling these amendments per "coordinated commit" discipline:

- **0010** new `behavioral_signatures` TABLE per MAC-58 §5 Option B (board decision 2026-05-09). 42 staged behavioral signatures HELD from promotion (single-source per §8.3; Wave-B targets NDSS 2025 Marlin + Rayhunter PCAPs).
- **0011** adds `ble_manufacturer_id` to identifier_type CHECK enum (G-3). 22+ staged from Wave-A.
- **0012** adds `paired_identifier_id` + `pair_kind` columns to identifiers (G-7 multi-gate enabler for G-4/G-2/G-1/G-13.3). pair_kind enum: 4 values + NULL (la_bit_flip / frdid_sibling / vendor_as_container / firmware_generation). Static-MAC tracker INTENTIONALLY EXCLUDED — handle via notes-JSON per dispatch §2.5.
- **0013** adds 13 new identifier_types covering Drone-RID + proprietary RF-protocol cluster (G-9 + Phase-4 fold-in per dispatch §3.1.4). Renamed from `0013_drone_rid_identifier_types_extension.sql` to current name per board direction 6516a9af.
- **0014** adds `alpr_model` (G-10 partial). `operator_profile` HELD as new gate G-17 (operators-table vs identifier-type architectural call — deferred to validator-side review).

Phase-2 self-review surfaced a load-bearing §8.2-vs-§8.3 catch: the original Wave-A dispatch §2.2 stated "Bible §8.3 caps single-source hypotheses at confidence 60" but §8.3 is actually dedup logic — the operative cap is §8.2 source-type bands. The G-13.3 amendment now aligns with §8.2 directly (no parallel tier system). Board ratified at bbb71be5. This is the kind of self-review the dispatch was designed to catch.

### Corrections applied

1. **§8.4 first bullet edit (multi-purpose vendors)** — added explicit reference to the new "Model-level evidence — what counts" sub-rule below.

2. **§8.4 NEW BULLET: "Model-level evidence — what counts (hardware-anchor sub-rule)"** (G-13.3) — formalizes three evidence shapes (direct firmware-binary inspection / paper-report inference / community attribution); explicitly composes with §8.2 source-type bands; explicitly does NOT introduce a parallel tier system; specifies `pair_kind='firmware_generation'` for generation-pairing rows; specifies `device_fingerprint` identifier_type for chipset/PMIC anchor rows with `manufacturer='Qualcomm'` / `model=<vendor>-<gen>`.

3. **§8.4 NEW BULLET: "Protocol-container OUI lens (third-lens discipline)"** (G-1) — formalizes the three OUI lenses (chip-vendor, product-vendor, protocol-container); specifies dual-lens vendor-as-container handling via `pair_kind='vendor_as_container'`; within-lens corroboration discipline (FRDID single-source held; FA:0B:BC promotion-ready).

4. **§8.4 NEW BULLET: "Locally-administered (U/L=1) OUI pairing discipline"** (G-4) — sub-agent draft 2026-05-11 ratifies as-is per bit-math verification (Phase 2 §2.6). Three dispositions (sibling-present-same-vendor / sibling-absent / sibling-present-different-vendor). Precedence rule with protocol-container lens (check protocol-container FIRST).

5. **§8.4 NEW BULLET: "Defensive-tool operator-side hardware self-exclude"** (G-15) — Pi self-exclude mechanic extended. Three-layer exclusion list: USB VID:PID values (5 concrete from 6α surfacing — Orbic 3 modes + UZ801 + PinePhone Quectel), firmware/hardware-rev-anchored modems (4 entries: Wingtech CT2MHS01, T-Mobile TMOHS1, TP-Link M7350/M7310), and forward-proofing language mirroring Rayhunter upstream curation. Standard export at `severity='low'`; coverage_report bucket `self_exclude_defensive_tool` (separate from `self_exclude_oui`).

6. **§11 #12 expansion** — original Pi-only rule expanded to "Operator-stack self-exclude" covering (a) Lynceus host (Pi) and (b) defensive-tool hardware (Rayhunter-supported modems). Mandatory regardless of source confidence.

7. **Schema migrations applied (5)** — see Schema-sibling commits header above. Each applied with `PRAGMA foreign_keys = OFF / BEGIN / apply / PRAGMA foreign_key_check / PRAGMA integrity_check / COMMIT / PRAGMA foreign_keys = ON` envelope per dispatch §3.1. End-state schema_version=14; 154 identifiers rows preserved across 4 table rebuilds; 27-value cumulative `identifier_type` enum; 0 behavioral_signatures rows (gated on Wave-B second-source).

### §11 hard-rule discipline (cite verbatim from bible HEAD pre-CP14 / post-CP13)

- **§11 #1 (no fabrication)** — every §8.4 amendment cites concrete Wave-A surfacing provenance:
  - G-1: 1d + 2c + 4a + 4b + 4c surfacings (FA:0B:BC at n=5)
  - G-4: 1a + 1c + 2a surfacings (n=3 device-MAC LA); sub-agent draft math + DB sibling verification (Phase 2 §2.6)
  - G-13.3: 6ε direct firmware-binary inspection (ALPR-DDR-FIREHOSE.mbn) + 6δ paper inference
  - G-15: 6α (EFForg/rayhunter `installer/src/*` surfacing for USB VID:PIDs)
- **§11 #2 (no non-public data)** — feedback memo `feedback_supply_chain_pki_lineage.md` re-classed G-13.1 Xiaomi-PKI finding OUT of §11 amendment status; intelligence-style supply-chain discipline, not hard rule. Cert fingerprints recorded as public-CA material only (no key material).
- **§11 #7 (no promotion without provenance)** — schema-only this CP; promotion is Phase 4 next heartbeat (the §8.4 amendments inform Phase-4 disposition).
- **§11 #8 (no confidence drift)** — no confidence-column writes; the four amendments codify promotion-time disposition rules (paired-identifier, lens-classification, hardware-anchor source-band, defensive-tool self-exclude).
- **§11 #11 (amendment-log discipline)** — this entry IS the §11 #11 closure for the CP14 coordinated commit. The discipline rule binds CP-class edits to amendment-log entries; CP14 pairs four §8.4 amendments + §11 #12 expansion + five schema migrations with this single amendment-log entry.
- **§11 #12 (operator-stack self-exclude)** — expanded in this CP from Pi-only to operator-stack-wide (Pi + Rayhunter-supported defensive-tool hardware).
- **§11 #15 (no decompiled vendor source in git index)** — N/A; no decompile artifacts in this CP.

### Resolved §12 questions

No existing §12 entries closed by this pass. The Wave-A surfacings extended Argus's coverage at the schema + bible levels rather than resolving prior open questions.

### New open §12 questions

1. **Static-MAC tracker sub-class architecture.** Phase 3b (`seemoo-lab/AirGuard`) surfaced a distinct opposite-pattern sub-class to G-4 LA-bit: Tile, Chipolo, Pebblebee emit STATIC MACs by design. AirGuard's risk-evaluation algorithm treats them as a first-class architecture distinction ("dynamic-MAC tracker" vs "static-MAC tracker"). CP14 0012's `pair_kind` enum INTENTIONALLY EXCLUDES `static_mac_tracker` per dispatch §2.5 ("different security architecture; handle via notes-JSON until a third sub-class is needed"). Open question: at what n of static-MAC observations does Argus introduce a structural pair_kind value or a separate identifier shape? Currently n=3 (Tile + Chipolo + Pebblebee). Forward expectation: Wave-D/E may surface additional static-MAC ecosystems (LoRa-side trackers, industrial asset trackers) that push the question.

2. **operator_profile architecture (G-17).** Three corporate operators surfaced in Wave-A Phase 3c (Lowe's Q1373493, Home Depot Q864407, Simon Property Group Q2287759). These deploy surveillance hardware but don't manufacture it. CP14 0014 HELD operator_profile from identifier_type extension; deferred to validator-side review. Options: (A) new identifier_type value (rejected — shape mismatch; operators are entities not products), (B) new `operators` table parallel to `manufacturers` + `procurement_records`, or (C) fold into procurement_records (rejected — conflates buys with deploys). CEO recommendation Option B. Trigger for resolution: Wave-D or Wave-E surfaces ≥10 operator_profile candidates OR Lynceus integration team requests operators-table support.

3. **FAA RID single-authoritative-federal-source vs ≥3-source rule.** Wave-A Phase 3a staged 481 drone_id_prefix instances from the FAA RID lookup (4783-record SQLite at FAA publicDOCRev 2025-11-28 build). The dispatch §4.1 cut-off rules require `independent_source_count ≥ 3` for Phase-4 promotion. FAA RID is a single authoritative federal source. Open question for human-CEO Phase-4 disposition: does single-authoritative-federal-source waive the ≥3 rule for this 481-row batch? Currently HELD from promotion-cycle-1 per dispatch §6 ("surfacing this is your job; deciding it is human-CEO's"). Will be flagged in the Phase 4 candidates document and Phase 5 handoff doc.

### Sequencing post-acceptance (per board ratification 6516a9af)

1. **Phase 3 application** (this commit batch — 2026-05-11): 5 migrations applied as 5 separate commits + schema dump commit + CP14 coordinated commit (this entry's home) + feedback memos commit.
2. **Phase 4 promotion-cycle-1** (next heartbeat): generate `raw/wave_a/_promotion_cycle_1_candidates_2026-05-11.md` per dispatch §4.1; self-review the candidates with skeptical eyes; promote survivors atomically; route 3 known conflict cases (G-6 Pelco/Motorola Solutions on 00:04:7D, 4c Parrot 90:3A:E6 parser/test contradiction, 6γ AIMSICD DF_id=4 ambiguity) to `conflicts` table per §4.2. Regenerate `coverage_report.md`.
3. **Phase 5 handoff** (subsequent heartbeat): `raw/wave_a/_ratification_run_2026-05-11.md` containing migrations applied + bible amendments applied + feedback memo filed + promotion-cycle-1 results + promotion-cycle-2 queue + updated gates queue snapshot + FAA RID §6 disposition flag + PROJECT_STATE.md HB update.

### Why a Correction Pass, not separate SARs

§8.4 four-amendment batch + §11 #12 expansion + 5 schema migrations all touch bible §-text and identifier-table schema. CP-class is the right framing per CP11 / CP12 / CP13 precedent for coordinated bible §-text + schema amendments. SAR is reserved for operational-rule binding without bible §-text change.

### §11 #11 self-binding satisfied

This entry is itself the §11 #11 amendment-log pairing for the §8.4 four-amendment batch + §11 #12 expansion + five schema migrations landed in this coordinated commit + the schema dump audit + the separately-committed feedback memos. Bible HEAD bumps from `1c67bea` (MAC-57 CP13 export fix) to the CP14 coordinated commit landed alongside this entry. Schema_version bumps from 9 (post-CP13) to 14 (post-0014).

---

## Correction Pass 15 — §8.2 `primary_registry` source-type band (resolves FAA RID + SIG-registry structural-equivalence finding)

**Date:** 2026-05-11
**Source:** [MAC-63](/MAC/issues/MAC-63) reopened-via-comment dispatch [`c0e91b23`](/MAC/issues/MAC-63#comment-c0e91b23-ba74-4ebe-8d3e-e6fe94c67f0e) 2026-05-11 with fresh §11 #11 delegation scoped to: CP15 ratification (with 3 board-flagged refinements to the Phase-5 draft) + migration 0015 + promotion-cycle-2 (483 rows) + final handoff. Original surfacing: Wave-A Phase 3a 481 FAA RID `drone_id_prefix` rows (alphafox02/DragonSync) + Wave-A 1a/2+ Apple `0x004C` + XUNTONG `0x09C8` `ble_manufacturer_id` rows. Board's reframe at MAC-63 [`fe2beeee`](/MAC/issues/MAC-63#comment-fe2beeee-2571-475e-86f6-edc99f99ecad) 2026-05-11. Phase-1 ratification at MAC-63 [`f00e9120`](/MAC/issues/MAC-63#comment-f00e9120-e92d-4226-af25-60bd075951b7).
**Bible commit:** PROJECT_BIBLE.md §8.2 source-band table edit (insert `primary_registry` row + narrow `official` description) + new §8.2 `primary_registry` sub-rule + PROJECT_BIBLE.md §12 FAA RID question `RESOLVED by CP15 2026-05-11` append + BIBLE_AMENDMENTS.md CP15 entry (this entry) + draft moved from `raw/wave_a/_bible_amendment_cp15_primary_registry_draft_2026-05-11.md` to `bible/history/cp15/`. Single coordinated commit titled "CP15: §8.2 primary_registry source-type band (resolves FAA RID + SIG-registry structural-equivalence finding)".
**Binds:** Validator (§11 #7 promotion gate — promotion-cycle-2 will sweep the 483-row HOLD batch at conf=85 single-source under the new band), Export Worker (§7.5 — `primary_registry` rows flow to Lynceus high-confidence export when `device_category ≠ 'unknown'` per §11 #13; FAA RID `drone_id_prefix` rows with category=`drone` qualify, SIG company-IDs at category=`unknown` excluded by §11 #13 carveout), SourceWorker (post-CP15 ingest of registry-direct citations classifies under `primary_registry`).

### Why this Correction Pass exists

Three Wave-A surfacings (FAA RID via alphafox02/DragonSync Phase 3a; Apple `0x004C` + XUNTONG `0x09C8` `ble_manufacturer_id` Phase 1a/2+) share a structural shape that the pre-CP15 §8.2 source-band table did not accommodate cleanly:

- Authoritative numerical-allocation registries (IEEE OUI, Bluetooth SIG company IDs, FAA RID, IANA) where the issuing authority IS the source-of-truth for what the identifier means.
- MAC-63 promotion-cycle-1 dispatch §4.1 ≥3-independent-sources cut-off was structurally ill-defined for these — "what does `1581Fxxx` mean at FAA?" has one source-of-truth, not three.
- Existing `official` band conflated registry-issuance with regulatory-filing; existing `crowdsourced` band capped at 75 (too low for registry-direct citations).

The board reframe at `fe2beeee` and CP15 ratification dispatch at `c0e91b23` direct: split the gap. Move IEEE OUI registry from `official` (which keeps FCC filings + court-verifiable government filings) into a new `primary_registry` band, alongside FAA RID + SIG company IDs + IANA assignments + similar issuer-of-record registries.

### Corrections applied

1. **§8.2 source-band table** — inserted new row `primary_registry` (70–85 single-source; up to 95 cross-band corroboration) between existing `official` and `regulatory` bands.

2. **§8.2 `official` band description** — narrowed to court-verifiable government filings only (FCC EAS, FAA enforcement orders, court-ordered disclosures). IEEE OUI registry migrates to `primary_registry`.

3. **§8.2 `primary_registry` sub-rule** — added immediately after the source-band table (and before the existing `manufacturer_app` sub-banding section). Defines:
   - Canonical examples (IEEE OUI, Bluetooth SIG, FAA RID, IANA)
   - Distinguishing-issuer test (source-of-truth-for-meaning vs third-party-assertion vs court-verifiable-filing)
   - Confidence ceiling rationale (70–85 single-source; up to 95 cross-band corroboration per §8.3 formula)
   - Waiver of ≥3-independent-sources cut-off (primary_registry-only; other bands keep their cut-off rules)
   - **Reclassification discipline (§11 #8 boundary)** — reclassification from `crowdsourced`/`inferred` to `primary_registry` requires direct registry source_url, NOT ancestry chain (Phase-1 refinement 1.2 closes the "ancestry chain establishes the registry-issuer citation" loophole that the draft had pre-refinement)
   - **Multi-registry edge case** — most-direct citation wins; registry-internal reassignment routes to `conflicts` table with `reason='registry_reassignment'` (Phase-1 refinement 1.3 narrows the draft's original speculative authority-ranking framing)
   - Composition with CP14 §8.4 lenses (G-1, G-3, G-7, G-9)

4. **PROJECT_BIBLE.md §12 FAA RID question** — appended `RESOLVED by CP15 2026-05-11` marker to the "Wave-A (CP14)" subhead's "§8.2 source_type band for FAA RID-class primary-source registries" bullet. Per the fresh-ratification-supersedes-mutation discipline, did NOT remove the question — appended the resolution marker.

5. **Draft archival** — moved `raw/wave_a/_bible_amendment_cp15_primary_registry_draft_2026-05-11.md` to `bible/history/cp15/` for audit trail (CP14 precedent).

### Phase-1 refinements to the draft (per board direction `c0e91b23`)

Three refinements applied before this coordinated commit:

1. **§5 source-ancestry-scope acknowledgment** — added paragraph noting the future-CP reclassification sweep is bounded by source ancestry (sources.id=1 IEEE bulk-load covers ~91,727 raw_observations rows), not identifier count. "No data loss" framing preserved; sweep scoping is a future-CP planning task.
2. **§11 #8 reclassification tightening (closed the "ancestry chain" loophole)** — replaced the draft's permissive "WHEN the row's ancestry chain establishes the registry-issuer citation" phrasing with a strict-direct-source_url requirement. A third-party citation chain reaching a registry no longer qualifies; a new raw_observations row citing the registry directly is required.
3. **§3.1 multi-registry narrow** — dropped the draft's speculative "higher-authority registry" framing (which would have required CP15 to legislate registry-authority-ranking without precedent) in favor of "most-direct citation wins"; registry-internal reassignment routes to conflicts table.

Phase-1 verification report at MAC-63 [`7642f54a`](/MAC/issues/MAC-63#comment-7642f54a-cc85-4740-9436-e376a7f56815). Board's pre-Phase-2 grep check at `f00e9120` caught a `§2.2 / §2.3 drift` (the tightened reclassification rule was in §2.3 audit-stub but missing from §2.2 bible-text); fixed before this coordinated commit so the bible-binding portion carries the same tightened rule as the audit-trail entry.

### §11 hard-rule discipline

- **§11 #1 (no fabrication)** — every `primary_registry` citation must name the registry-issuer AND include `source_url` pointing at the issuer's own publication (FAA's database URL, SIG's registry URL, IEEE's MA-L assignment record URL, etc.). Third-party-repo citations of the same identifier remain `crowdsourced`.
- **§11 #7 (provenance)** — `primary_registry` rows carry the same `raw_observations` ancestry discipline as other promotion paths (Bible §7.3 worker-role separation; `raw_observations.source_url` + `source_excerpt` populated from the registry-issuer publication).
- **§11 #8 (no confidence drift)** — single-source `primary_registry` promotes to 70–85; corroboration follows §8.2 formula. Reclassification from `crowdsourced`/`inferred` to `primary_registry` is permissible ONLY when the row's existing `source_url` already points DIRECTLY at the registry issuer's own publication. Reclassification is band-correction within preserved provenance, NOT a provenance shortcut. (Phase-1 refinement 1.2 closes the "ancestry chain" loophole.)
- **§11 #11 (amendment-log discipline)** — this CP15 entry is the amendment-log closure for the §8.2 amendment in this coordinated commit. The bible-text amendment (§8.2 sub-rule) carries the same tightened reclassification language as this audit-trail entry, per the §11 #11 coordinated-commit discipline (pre-Phase-2 grep check at `f00e9120` caught and fixed an earlier drift between the two).
- **§11 #13** — N/A directly; CP15 doesn't touch `device_category` rules. Composes with §11 #13 at promotion-cycle-2: SIG company-IDs (`0x004C` Apple, `0x09C8` XUNTONG) classify as `device_category='unknown'` per §8.4 multi-purpose-vendor discipline + §11 #13 excludes them from Lynceus high-confidence export. FAA RID `drone_id_prefix` rows classify as `device_category='drone'` (FAA RID scope is drones) and qualify for high-conf export.

### Sequencing post-acceptance (per dispatch `c0e91b23` Phase-3 onward)

1. **CP15 ratifies at this commit.** Bible HEAD bumps from `9c31603` (post-MAC-63-Wave-A state) to the CP15 commit.
2. **Schema-sibling migration `0015_primary_registry_source_type_extension.sql`** (Phase-3 dispatch) adds `primary_registry` to `identifiers.source_type` + `sources.source_type` CHECK enums via the SQLite table-rebuild pattern (per 0009 precedent). Cumulative-CHECK-enum discipline per `feedback_migration_sequence_cumulative_enum_carryforward.md` — each table's CHECK must include every prior CP's contribution + `primary_registry`.
3. **Promotion-cycle-2** (Phase-5/6 dispatch) sweeps the three CP15-unblocked HOLD batches:
   - FAA RID 481 `drone_id_prefix` rows (alphafox02/DragonSync 3a; sources.id=23)
   - Apple `0x004C` `ble_manufacturer_id`
   - XUNTONG `0x09C8` `ble_manufacturer_id`
   483 rows total, all single-source `primary_registry`, ceiling 85.
4. **Sources reclassification (Wave-B+ batch task)** — IEEE OUI bulk-load source row migrates from `source_type='regulatory'` (current) to `source_type='primary_registry'`. Backfill of existing identifiers rows whose ancestry traces back to IEEE OUI is bounded by source ancestry (~91,727 raw_observations rows; substantial subset of identifiers rows) — sweep scoping is a future-CP planning task. CP15 ratifies the band, not the migration plan. (Phase-1 refinement 1.1 acknowledges the scope.)

### §12 Open Questions impact

- **RESOLVED:** "§8.2 source_type band for FAA RID-class primary-source registries" (Wave-A (CP14) subhead; original surfacing from MAC-63 Wave-A `72c0323` §12 finalization commit). Marked `RESOLVED by CP15 2026-05-11` in PROJECT_BIBLE.md §12; bullet preserved per fresh-ratification-supersedes-mutation discipline (append, don't remove).
- **No new §12 questions added by CP15.** The two other Wave-A (CP14) §12 questions (static-MAC tracker sub-class, operator_profile architecture) remain open per their original framing.

### Why a Correction Pass, not a SAR

§8.2 source-band table edit + new §8.2 sub-rule + §12 question resolution all touch bible §-text. CP-class is the right framing per CP11/CP12/CP13/CP14 precedent for in-place bible §-text amendments. SAR is reserved for interpretive sub-agent rules without bible §-text change.

### §11 #11 self-binding satisfied

This entry is itself the §11 #11 amendment-log pairing for the §8.2 edits in this coordinated commit. Bible HEAD bumps from `9c31603` (post-MAC-63-Wave-A state) to the CP15 coordinated commit landed alongside this entry. Schema-sibling migration 0015 is the next deliverable (Phase-3 dispatch), tracking the CP15 amendment's contract with the database schema.

---

## Correction Pass 16 — §4.4 Lynceus mapping for CP14 identifier_type cluster

**Date:** 2026-05-12
**Source:** [MAC-75](/MAC/issues/MAC-75) CP16 dispatch. Trigger: MAC-63 Phase 5 HALT (CP14→§4.4 downstream-consumer gap; second post-memo recurrence of the bible-amendment-downstream-consumer-update pattern after CP12→CP13 + CP13→MAC-57). Six-phase verify-and-halt dispatch under fresh CEO §11 #11 delegation 2026-05-12. Phase ratifications at: Phase 1 [`ee60c712`](/MAC/issues/MAC-75#comment-ee60c712-fcef-4795-a1ac-8727e70b8045), Phase 2 [`5b9212ce`](/MAC/issues/MAC-75#comment-5b9212ce-5276-4fb6-9bd7-dae62d2e53f3), Phase 3 [`369cb7c7`](/MAC/issues/MAC-75#comment-369cb7c7-269d-48fe-a0b6-e2d5cd369a15), Phase 4 [`dbfb5da6`](/MAC/issues/MAC-75#comment-dbfb5da6-a3a2-4434-99d7-da9b46d9acd8).
**Authority:** Fresh CEO §11 #11 delegation 2026-05-12 (MAC-75 wake comment [`017df17b`](/MAC/issues/MAC-75#comment-017df17b-1798-4606-bdae-5723bdb7ef25)).
**Bible commit:** PROJECT_BIBLE.md §4.4 (15 new mapping rows + 3 new pattern_type introductions + architectural-separation paragraph) + BIBLE_AMENDMENTS.md CP16 entry (this entry) + bible-amendment draft moved from `raw/wave_a/_bible_amendment_cp16_lynceus_mapping_draft_2026-05-12.md` to `bible/history/cp16/`. Single coordinated commit titled "CP16: §4.4 Lynceus mapping for CP14 identifier_type cluster".
**Code-sibling commit (paired, second commit per CP14/CP15 precedent):** `db/validation/export_lynceus.py` (3 MAP dict additions + new `DROPPED_REASONS` dict + new `_classify_row` branch + `bins` initializer expansion + `fmt_bin_table` rendering expansion + `mac_range` stale-comment refresh) + `tests/test_export_lynceus.py` (union-assertion + structural-invariant + new MAP/DROPPED assertions) + `feedback_bible_amendment_downstream_consumer_audit.md` (memory-rule strengthening: S.1 case-study + S.2 + S.3 + S.4 + S.5 + S.6). Code-patch draft retired from `db/validation/_drafts/` (first instance of code-patch staging mirroring `db/migrations/_drafts/` shape per new memo S.5). Commit titled "chore(export): CP16 Lynceus mapping coordinated patch + memory-rule strengthening".
**Binds:** Export Worker (§7.5 — 3 new pattern_type values + 12 DROPPED-reason buckets in coverage report; runtime aggregation/reconciliation surfaces extended), Validator (§11 #7 promotion-cycle-2 sweep of 417 HOLD candidates now unblocked post-CP16), Lynceus integration team (independent sequencing of the 3 new pattern_types into v0.4+ scanner-config schema; consumer-carries-capability-state posture explicit).

### Why this Correction Pass exists

CP14 added 15 new `identifier_type` enum values via migrations 0011/0013/0014 but did NOT update §4.4 Lynceus mapping or `IDENTIFIER_TYPE_TO_PATTERN_TYPE` in lockstep. The feedback memo codifying parallel-sibling-commit discipline existed (authored after CP12→CP13 schema gap; refined after CP13→MAC-57 export gap), but the CP14 batch missed it — the discipline rule lived in memory but did not propagate into dispatch templates as an explicit phase. MAC-63 Phase-5 export-regen attempt 2026-05-11 surfaced the gap on the 417-row promotion-cycle-2 candidate batch (Apple `0x004C` + XUNTONG `0x09C8` + FAA RID 415 drone_id_prefix). CP16 closes the gap and strengthens the memo with explicit dispatch-checkpoint language (S.1), cumulative-full-enum audit sub-rule (S.2), recurrence-count audit trail (S.3), composition discipline (S.4), code-patch staging shape (S.5), and architectural-absorption sub-rule (S.6).

### Items

1. **§4.4 Lynceus mapping table** — 15 new rows in CP14 migration-source order (0011 → 0013 cluster → 0014). 3 MAP cases introduce new `pattern_type` values: `ble_manufacturer_id` (BLE adv manuf_data parsing), `drone_id_prefix` (Remote ID across WiFi NAN/Beacon/BLE Legacy 4.x; BLE5 LE Coded PHY capability boundary documented), `wifi_aware_service_name` (capability-gated by Lynceus NAN support; consumer-carries-state posture). 12 DROPPED cases carry explicit hardware/architectural rationale + upgrade-path-X-unlocks framing where applicable (current-hardware-not-permanent posture).
2. **Architectural-separation paragraph** in §4.4 — explicit "Argus and Lynceus are parallel tracks, not a serial dependency" statement; runtime match coverage gated by Lynceus's track separately from Argus's apply-time export. Addresses the framing concern surfaced at Phase-3 ratification by board addition of self-review item #6.
3. **Code-sibling patch (export_lynceus.py)** — 3 new dict entries for MAP types; new `DROPPED_REASONS` dict for the 12 DROPPED types; one new `_classify_row` branch keyed on `DROPPED_REASONS`. Existing 6 legacy DROPPED branches preserved (stable, working). `bins` dict initializer (line 584 region) and `fmt_bin_table` bin_rows tuple (line 681 region) extended with 12 new bin labels — Phase-4 dry-run caught the Phase-3 architectural-absorption claim that "no code change needed" was wrong; revisions A applied. `mac_range` stale "HB36" comment refreshed in-pass per Phase 2 board direction `5b9212ce`.
4. **Test-fixture sibling update (test_export_lynceus.py)** — `test_type_mapping_covers_every_identifier_type` rewritten to assert `set(IDENTIFIER_TYPE_TO_PATTERN_TYPE.keys()) | set(DROPPED_REASONS.keys())` covers the full 27-value post-CP14 enum + structural-invariant that the two surfaces don't overlap. `test_type_mapping_drops_match_44_verbatim` extended with assertions on the 3 new MAP entries + all DROPPED_REASONS bin labels. Phase-4 audit-trail note: this test existed at CP13 and would have caught the CP14 §4.4 gap at apply time if anyone had run it; the strengthened memo's S.1 + new S.1 case-study sub-rule cite this concrete case for future dispatches.
5. **Memory rule strengthening (feedback_bible_amendment_downstream_consumer_audit.md)**:
   - **S.1** Explicit dispatch-checkpoint language — every CP/SAR adding values to a field with downstream consumers MUST include a "downstream-consumer audit" phase by name in the dispatch §2 phase breakdown, verify-and-halt before apply.
   - **S.1 case-study sub-rule** (board-requested at Phase 4 ratification `dbfb5da6`) — concrete case study citing `tests/test_export_lynceus.py:99-115`'s CP13-hardcoded 12-key assertion as the CP14 fixture-side miss that would have caught the §4.4 gap. Abstract rules get violated; case-study rules stick.
   - **S.2** Cumulative-audit-runs-against-FULL-enum — the audit checks the ENTIRE field's value set, not just the CP's new additions; affirmative "clean beyond [CP-N]" anchor or explicit latent-gap list. Phase 2 of MAC-75 produced the first such anchor ("clean beyond CP14 additions").
   - **S.3** Recurrence-count audit trail with dual-framing (post-memo count = 2 per board direction; full historical count = 3 preserved for audit-trail).
   - **S.4** Composition discipline with Validator-side companion memo + cumulative-CHECK-enum memo.
   - **S.5** Code-patch staging shape — `<code-module>/_drafts/<patch>.<ext>.draft` for sibling code patches, mirroring `db/migrations/_drafts/`. `db/validation/_drafts/` introduced by CP16 is the first instance.
   - **S.6** Architectural-absorption sub-rule (board-requested at Phase 4 ratification `dbfb5da6`) — claims about "X composes naturally with new Y without code changes" require runtime exercise against actual data, not just static-analysis confirmation. Common blind spot: the data structure under a composable loop may itself be enumerated exhaustively elsewhere. CP16 Phase-3 architectural-validation claim about `_reconcile()` was wrong because Phase 3 didn't dry-run; Phase 4 dry-run caught it. Pre-Phase-5 dispatches that make architectural-absorption claims now require Phase-4-style runtime exercise.

### Discipline-strengthening

The codified memory rule (post-MAC-55) caught CP13→MAC-57 retroactively but did not prevent CP14's recurrence at dispatch-design time. CP16's S.1+S.6 strengthening adds:
- Dispatch-template checkpoint language so future dispatches enumerate §4.4 + IDENTIFIER_TYPE_TO_PATTERN_TYPE + relevant test fixtures + relevant hardcoded-enumeration surfaces as an explicit phase.
- Cumulative-full-enum sub-rule catches any latent earlier-CP gaps the rule missed retroactively.
- Concrete case study (S.1 sub-rule) makes the test-fixture audit memorable rather than abstract.
- Architectural-absorption sub-rule (S.6) prevents Phase-3-style over-ratification of composability claims without runtime evidence.
- Second post-memo recurrence is the trigger for this strengthening; if S.1+S.6 work as designed, recurrence count stays at 2 going forward.

### Resolved §12 questions

None directly. CP16 closes the operational finding logged by MAC-63 G-18 (CP14→§4.4 mapping gap) but the finding was not a §12 open question.

### New open §12 questions

None. Phase 1 audit's 3 pause-for-human flags were ratified without surfacing new §12-class structural questions; Phase 2 cumulative audit confirmed no latent §4.4 surfaces are open post-CP16.

### §11 hard-rule discipline

- **§11 #1 (no fabrication)** — every DROPPED row has explicit hardware / architectural / sub-protocol rationale; no "out of scope" placeholders. Every MAP row names the canonical match-surface mechanism.
- **§11 #11 (coordinated commit)** — bible + amendment log + draft move land in commit 1 (this entry); code patch + test update + memo strengthening + code-patch-draft retirement land in commit 2 (paired sibling commit per CP14/CP15 precedent).
- **§11 #12 / §11 #13** — unchanged. CP16's type-level DROPPED-with-reason composes with row-level §11 #13 unknown-category carveout; both fire independently at export time. §11 #12 operator-stack self-exclude applies orthogonally on OUI / VID:PID rows.

### Sequencing post-acceptance

1. **CP16 ratifies at this commit + paired code-sibling commit.** Bible HEAD bumps from `3b37e69` (post-CP15 + migration 0016 LICENSE column) to the CP16 commit.
2. **Promotion-cycle-2 unblocked** — MAC-63 Phase 6/7 can resume on a separate dispatch. 417 candidates (415 FAA RID `drone_id_prefix` + Apple `0x004C` + XUNTONG `0x09C8`) become promotion-eligible at conf=85 single-source under post-CP15 `primary_registry` band + post-CP16 §4.4 disposition. Predicted post-CP16 high-confidence Lynceus export delta: +417 entries (each `device_category ≠ 'unknown'` per §11 #13; FAA RID rows = `drone`, SIG company-ID rows = TBD per row analysis — XUNTONG/Apple at `device_category='unknown'` per CP15 §11 #13 carveout would NOT ride high-conf export; FAA RID 415 at `device_category='drone'` would).
3. **Lynceus integration sequencing** — independent of Argus-side timing. Lynceus team adds `ble_manufacturer_id` / `drone_id_prefix` / `wifi_aware_service_name` to v0.4+ scanner-config schema at their own pace. Argus-side export ships unconditionally with the new pattern_types per consumer-carries-capability-state posture.

### Why a Correction Pass, not a SAR

§4.4 mapping table edit + new architectural-separation paragraph + sibling code patch + sibling test update all touch bible §-text and downstream-consumer code surfaces. CP-class is the right framing per CP11/CP12/CP13/CP14/CP15 precedent for coordinated bible §-text + sibling-implementation amendments. SAR is reserved for interpretive sub-agent rules without bible §-text change.

### §11 #11 self-binding satisfied

This CP16 entry is the §11 #11 amendment-log pairing for the §4.4 amendment in the coordinated commit. Bible HEAD bumps from `3b37e69` (post-CP15 + migration 0016) to the CP16 commit landed alongside this entry. Schema-version unchanged (CP16 is a mapping-table + code-patch CP, not a schema CP).

---

## Correction Pass 17 — §8.2 manufacturer_app coalesce-pass + SAR-11 chunked codification + WAVE_G_RUNBOOK §3 + §11 #7 + scan-ignore landing

**Date:** 2026-05-13
**Source:** Track E CP16 proposal-shape surfaced at MAC-1 [`a8b17428`](/MAC/issues/MAC-1#comment-a8b17428-0032-49ed-9f56-e9b4b6ac018c) HB73 2026-05-11 (12-unit envelope; HB70 9 high-level → expanded per HB73). CP16-1 through CP16-7 META decisions ratified at HB74 [`bb5c58a8`](/MAC/issues/MAC-1#comment-bb5c58a8-0723-4afa-b5a8-618f4b7dafd4) 2026-05-12 (12-unit enumeration locked + single coordinated commit + §8.2 coalesce-pass + single SAR-11 row with A/B/C sub-rules + Runbook §3 corrections + path-γ MAC-53 re-base + slot-0016 verify-wrapper test). **Renumbered to CP17 at HB98 [`71077702`](/MAC/issues/MAC-1#comment-71077702-c932-4121-a2b0-646272829404) 2026-05-13** post-bible-CP16-numbering-collision finding: bible CP16 had already committed at `d37e9dc` for §4.4 Lynceus mapping (MAC-75 dispatch). Track E retained the META ratifications carried forward as CP17 META. CP17 scope-refresh per HB98 status audit collapsed the original 12-unit envelope to 4 components (CP17-A SAR-11 + CP17-B §8.2 coalesce + CP17-C Runbook + CP17-D coordinated-commit-composition) plus 1 paired code-sibling. Composition surfaced HB102 [`f63db2dd-placeholder`]; board prose-quality ratification batch HB103 [`e7405643`](/MAC/issues/MAC-1#comment-e7405643-77f2-4635-a97e-4ca661f8cd65); commit-firing HB104.
**Bible commit:** This entry + SAR-11 row insert into BIBLE_AMENDMENTS.md § Sub-agent rule additions + PROJECT_BIBLE.md §8.2 manufacturer_app block replacement + android_test/WAVE_G_RUNBOOK.md §3 + §11 #7 + .gitleaksignore + .trufflehogignore + .gitignore §11 #15 carveout) + paired code-sibling commit (android_test/tools/extraction/wave_g_extractor.py Priority A bug fix, already-applied during Wave G calibration 2026-05-10; this commit is the first-git-tracked occurrence) + state-rotation commit (PROJECT_STATE.md HB102+HB103+HB104 close).
**Binds:** ExtractionWorker (Wave G `wave_g_extractor.py` FP-filter pipeline + cohort-distinction queue-ordering + `vendor_template_namespace_uuid` extraction logic per §8.2 sub-banding rule + SAR-11 Priority A/B/C FP-class disambig at extraction-time), Validator (§11 #7 promotion gate + SAR-11 Priority D Validator-judgment per-candidate labeling + short-ID-walking inference for `vendor_template_namespace_uuid` templates per §8.2 sub-rule), Lynceus integration team (no immediate consumer-side effect; `vendor_template_namespace_uuid` identifier_type lands at first-promotion-time with schema sibling per `feedback_enum_amendment_needs_schema_migration_sibling.md` forward-looking-codification caveat).

### Why this Correction Pass exists

Wave G pre-v1 autonomous static-analysis session 2026-05-10 (MAC-52 [`ddc193cd`](/MAC/issues/MAC-52#comment-ddc193cd-0dec-4fab-a83c-30b04f79506b)) surfaced two structural findings + one large operational artifact set: (a) the operator-vs-installer cohort distinction (operator apps yield product-family taxonomy ONLY; installer/pairing apps yield BLE/SSID/credential identifiers), (b) the `vendor_template_namespace_uuid` sub-class observation (Getac BWC Viewer's 2-UUID shared-suffix `-1b7f-430ea194e6cf` pattern), (c) the 23 novel FP classes + 1 Priority-A bug fix (path-filter `looks_like_third_party_lib()` leading-slash mismatch) from the calibration-window + cohort-B-E analysis. HB57 §E ladder [`e492ac66`](/MAC/issues/MAC-1#comment-e492ac66-7109-412a-acb3-8db1d247310d) ratified the 8-item bundle for CP14 coordinated commit; CP14's actual commit body landed only the §8.4 four-amendment batch + §11 #12 expansion + 5 schema migrations, deferring SAR-11 + §8.2 sub-amends + Runbook corrections to a future CP. Track E proposal-shape surfaced the deferred bundle at HB73 with 12-unit envelope expansion; HB74 META-ratified the chunked structure; HB98 surfaced + resolved the bible-CP16-vs-Track-E-CP16 numbering collision; HB99-HB101 drafted the four CP17-A/B/C/D component §-texts; HB102 composed the 3-commit coordinated landing; HB103 dispositioned two structural-integrity flags (hunk-staging discipline + decompile-carveout scope-narrowing). This CP17 lands the deferred bundle.

### Corrections applied

1. **SAR-11 chunked codification (CP17-A; HB99 [`d1588ea1`](/MAC/issues/MAC-1#comment-d1588ea1-8da5-4195-a2b8-e8153e786042)).** New SAR-11 row in BIBLE_AMENDMENTS.md § Sub-agent rule additions, structured per HB57 §E.2 board-ratified chunking (Priority A `looks_like_third_party_lib()` jadx/apktool/prefix-without-leading-slash three-layout support; Priority B 8 high-evidence FP classes; Priority C 15 lower-evidence + cohort-B-E FP classes; Priority D Validator-judgment per-author labeling). Authoritative machine-readable scope at `android_test/extraction_outputs/wave_g_pre_v1/calibration/proposed_fp_classes.json`.

2. **§8.2 manufacturer_app coalesce-pass (CP17-B; HB100 ratified at MAC-1 [`cd305c6a`](/MAC/issues/MAC-1#comment-cd305c6a-30f9-4133-a855-498643dcf890)).** PROJECT_BIBLE.md §8.2 `manufacturer_app sub-banding` block replaced verbatim by expanded block. Four sub-amends folded into single forward-write per CP16-3 META carried as CP17-3: (a) cohort distinction paragraph (operator-facing vs installer/pairing/technician; Wave G evidence base of 8 operator apps yielding 0 BLE UUIDs vs 2 installer apps yielding 6 unique vendor BLE UUIDs), (b) new `vendor_template_namespace_uuid` sub-band 75-90 + ExtractionWorker 4-step recipe, (c) product-family taxonomy row split into three rows (`marketing_name` / `internal_codename` / `device_type_enum_value`; all at 90-95 sub-band), (d) closing-paragraph SAR-11 reference updated from "(proposed; gated on Step-2 calibration)" to "(ratified at Correction Pass 17, 2026-05-13)" + new "Typical cohort" column on sub-banding table.

3. **WAVE_G_RUNBOOK §3 8 package-name corrections + vendor-unavailable block (CP17-C 2a; HB101).** Runbook §3 vendor target list updated with Wave G calibration discoveries: Flock Safety (operator + installer two-app deployment); SoundThinking (`alerts` not `respondr`); Axon (`com.evidence` + `com.evidence.flex` LE-only; View XL Windows-platform-mismatch); Cradlepoint (`.manager` suffix); Hak5 (`org.hak5.pineappleconnector`; Cloud C2 desktop/web platform-mismatch); Autel Robotics (`com.autelrobotics.explorer`); Avigilon (`com.avigilon.acc_mobile`); Genetec (`com.genetec.platformmobile`). Vendor-unavailable-on-Android documentation block absorbs 11 vendors per HB57 §E.8.

4. **WAVE_G_RUNBOOK §3 scan-command lines paragraph (CP17-C 2b).** New paragraph after vendor-unavailable block documents canonical secret-scanning pre-commit workflow: `gitleaks git --no-banner` (fingerprint allowlist via `.gitleaksignore`) + `trufflehog git file://. --exclude-paths=.trufflehogignore --no-update --json` (path-exclusion via `.trufflehogignore`). Pre-commit checkpoint per §11 #11 amendment-log discipline composition.

5. **WAVE_G_RUNBOOK §11 #7 Option B-broad replacement (CP17-C 2c).** §-text replacement codifies window-around-match whenever line >200 chars regardless of file type, with `excerpt_type` field REQUIRED on every candidate. 4-class enumeration: `full_line` / `window` (with `match_offset_in_window`) / `binary` (hex-encoded) / `other`. Fabrication discipline per project-bible §11 #1 still binds; relaxation widens source-line-length permitted, not evidence-fidelity required. **Distinct from project-bible §11 #7** (same numbering, different surface).

6. **`.gitleaksignore` + `.trufflehogignore` git-track landing (CP17-C-paired).** Both files exist at repo root with substantive content (gitleaks fingerprint allowlist + trufflehog path-exclusion list); triaged at MAC-50 [`2714377b`] + board-ratified at MAC-59 [`b4d9afa0`]. `git add` lands them in CP17-D bible-amendment coordinated commit. Each entry carries `# FP:` comment per `feedback_strategic_steers.md` audit-trail discipline.

7. **Paired code-sibling: `wave_g_extractor.py` Priority A bug fix (per CP17-A SAR-11 Priority A immediate clause).** `looks_like_third_party_lib()` patched per HB99 SAR-11 §-text: three-layout support for jadx (`sources/<pkg>`), apktool smali (`smali_classesN/<pkg>` + `smali/<pkg>`), and prefix-without-leading-slash forms. Fix was applied during Wave G calibration 2026-05-10; this commit is the first-git-tracked occurrence of the corrected extractor. Lands as paired second commit per CP14/CP15/CP16 precedent (NOT in bible-amendment commit body — code/bible separation discipline preserved).

8. **`.gitignore` §11 #15 decompile-source carveout extension.** Add `android_test/raw/` + `android_test/extraction_outputs/` exclusions. `android_test/tools/` NOT excluded per HB103 Flag 2 disposition (workflow code is not decompile-source per §11 #15 intent). `android_test/WAVE_G_RUNBOOK.md` git-tracked at sandbox path per HB102 §1d option (A) + HB103 Flag 2 alignment.

### Composition with §11 hard rules

- **§11 #1 (no fabrication)** — SAR-11 Priority A bug fix preserves provenance-bearing candidates that the leading-slash mismatch had been incorrectly FP-classing. §11 #7 Option B-broad window-around-match relaxation explicitly preserves verbatim-source-text fidelity; fabrication-risk profile unchanged.
- **§11 #4 (no detection logic)** — SAR-11 is FP suppression INSIDE the extraction pipeline; not scanner detection rules. Downstream consumer (Lynceus) detection logic unchanged.
- **§11 #6 (no ToS violations)** — Wave G calibration ran on legally-acquired binaries per §11 #15 license posture; SAR-11 codifies FP-suppression rules derived from the calibration. No ToS implications.
- **§11 #7 (no promotion without provenance)** — Priority A bug fix ensures provenance-bearing candidates aren't lost to incorrect FP filter; promotion gate semantics unchanged.
- **§11 #8 (no confidence drift)** — FP demotion is category-correction not confidence-floor change; existing promotion-cycle confidence-band rules unchanged. `vendor_template_namespace_uuid` 75-90 sub-band sits below hardcoded-BLE-service tier (80-95) per §8.2 attestation-strength logic.
- **§11 #11 (amendment-log discipline)** — this CP17 entry is the amendment-log pairing for the §8.2 §-text + SAR-11 row + Runbook corrections in the coordinated commit. Bible HEAD bumps from `1fd254a` to CP17 commit.
- **§11 #12 (operator-stack self-exclude)** — unchanged; CP17 doesn't touch the Pi-OUI or Rayhunter-supported-modem self-exclude lists.
- **§11 #13 (unknown-category Lynceus-banned)** — unchanged; CP17 doesn't touch the unknown-category carveout.
- **§11 #15 (no decompiled-source commit)** — operationalized by the new `.gitignore` carveout (`android_test/raw/` + `android_test/extraction_outputs/` excluded; workflow code + WAVE_G_RUNBOOK.md NOT excluded per HB103 Flag 2 disposition). Vendor-derived artifacts continue NOT entering git index; workflow code + runbook documentation gain tracked-at-sandbox-path status for stable git-history anchor.

### Sequencing post-acceptance

1. **CP17 ratifies at this commit.** Bible HEAD bumps from `1fd254a` to CP17 commit SHA.
2. **Paired code-sibling commit** (`wave_g_extractor.py` Priority A bug fix; already-applied at Wave G calibration) lands immediately after the bible-amendment commit per CP14/CP15/CP16 precedent.
3. **State-rotation commit** (PROJECT_STATE.md HB102+HB103+HB104 close + post-CP17 baseline) lands after the code-sibling commit.
4. **Schema-migration sibling for `vendor_template_namespace_uuid` identifier_type defers to first-promotion-time** per `feedback_enum_amendment_needs_schema_migration_sibling.md` forward-looking-codification caveat (HB101 codified extension).
5. **Validator-promotion of Wave G pre-v1 staged candidates** per §11 #8 gate + ratified SAR-11 (path-γ authorized via HB57 §E.3 [`e492ac66`] override of MAC-53 three pre-conditions for path-γ shape specifically).
6. **Round-2 ExtractionWorker dispatch** (installer-class additions per path-γ shape) — separate dispatch when scope-proposal surfaces post-v1.0.0.
7. **Wave G' / Phase 7 iOS** (full Wave G yield ships v1.1.0) remains gated post-v1.0.0 per CP12 Path-A sequencing.

### §12 Open Questions impact

- **WAVE_G_RUNBOOK §11 #7 source_excerpt cap relaxation** (HB56 pre-v1 deliverable; HB57 §E.1 ratification) — **RESOLVED at CP17 (2026-05-13)** via §11 #7 Option B-broad replacement with `excerpt_type` field. Distinct from project-bible §11 #7.
- **Wave G Step 0 path-γ scope** (HB57 §E.3 path-γ override) — **PARTIALLY RESOLVED** at HB57; CP17-A SAR-11 codification + Priority A bug fix complete the immediate Wave G pre-v1 deliverables. Full Wave G Step 0 fires per CP12 sequencing post-v1.0.0.
- **Bible §8.2 manufacturer_app four sub-amends** (HB56 board surface; HB57 §E.4 ratification) — **RESOLVED at CP17 (2026-05-13)** via §8.2 manufacturer_app coalesce-pass single forward-write.
- **Runbook §3 8 package-name corrections** (HB56 board surface; HB57 §E.7 ratification) — **RESOLVED at CP17 (2026-05-13)** via Runbook §3 vendor target list update + vendor-unavailable-on-Android documentation block.
- **Skydio Enterprise alt-channel scope-proposal** (HB57 §E.6 ratification) — **CARRIED FORWARD**; 1-paragraph tracking entry at `research_leads/skydio_enterprise_alt_channel.md` lands at first-Wave-B+ heartbeat post-v1.0.0 per HB103 disposition.
- **DMCA-takedown counter-notice template** (bible §12 deferred-item) — **PARTIALLY RESOLVED at CP16 (2026-05-12) + LEGAL_POSTURE.md HB96 (2026-05-13)**; project-side legal-posture grounding lives publicly at `LEGAL_POSTURE.md`; verbatim §512(g) counter-notice template stays customized-per-takedown rather than pre-drafted.

### §11 #11 self-binding satisfied

This CP17 entry is the §11 #11 amendment-log pairing for the §8.2 + SAR-11 + Runbook amendments in the coordinated commit. Bible HEAD bumps from `1fd254a` to the CP17 commit landed alongside this entry. Schema-version unchanged (CP17 is a §-text + SAR-row + runbook + repo-hygiene CP; the `vendor_template_namespace_uuid` schema sibling defers to first-promotion-time per `feedback_enum_amendment_needs_schema_migration_sibling.md` forward-looking-codification caveat).

---

═══════════════════════════════════════════════════════════════════════
SAR-12 — Dispatch-Preamble Live-State Verification
═══════════════════════════════════════════════════════════════════════

**Date:** 2026-05-13
**Codification surface:** BIBLE_AMENDMENTS.md (this entry — canonical) +
  /home/kev/argus/feedback_s7_dispatch_preamble_live_state_verification.md
  (ExtractionWorker reference) +
  /home/kev/.claude/projects/.../memory/feedback_dispatch_preamble_live_state_verification.md
  (CEO-side reference)
**Binding scope:** All three actor classes that author dispatches —
  board, CEO orchestrator, ExtractionWorker (Claude Code).
**Status:** Acknowledged and approved by board; sibling memos to land
  post-ratification.

---

## §1 — Rule

Dispatch authoring (board-side, CEO-side, ExtractionWorker-side) MUST
run a pre-flight live-state verification before asserting any of the
following classes of fact in dispatch text. The verification result
MUST be pasted inline in the dispatch text with a timestamp, not
cited by external reference.

  (a) Baseline row counts
      e.g., "N staged behavioral_signatures from Wave-A"

  (b) API or schema field names
      e.g., "documentNumber field in FAA endpoint"

  (c) Enum membership in identifier_type, source_type, or
      device_category
      e.g., "§2.1 #14 category name"

  (d) Source completion state
      e.g., "USAspending is a Wave-C-new source"

  (e) CP / SAR / memo boundary claims
      e.g., "per CP14", "ratified at SAR-9", "deferred per
      feedback_X.md caveat"

## §2 — Verification paths per class

Each class has a specific verification path. The verification result
MUST be pasted inline in the dispatch text, not cited externally.
Citation can hide stale data; paste with timestamp is reproducible.

  Class (a) — Baseline row counts
    Path: SELECT COUNT(*) from the live DB against the relevant
          filter.
    Paste: count + filter clause + timestamp inline.
    Example:
      $ sqlite3 db/argus.db "SELECT COUNT(*) FROM raw_observations
        WHERE candidate_type='behavioral_signature' AND
        promotion_status IS NULL;"
      33
      (as of 2026-05-13T17:00:00Z)

    Methodology-specification clarification (added post-recurrence
    #7, 2026-05-14):

    For counts where multiple counting methodologies are structurally
    valid (Wave-X-candidate-level vs canonical-row-level; by-source
    vs by-row; by-tracking-number vs by-prefix; by-DB-row vs by-
    distinct-key; etc.), the paste-result inline MUST specify which
    methodology the count uses.

    Concrete case study: SAR-12 recurrence #7 at CP19 §6.6 (MAC-88
    sweep pre-flight) — board dispatch §0 cited 90/325 Scope 1/2
    partition (Wave-B-candidate-level counting: 90 Wave-B candidate
    entries collided with Wave-A); CEO live re-derivation surfaced
    80/335 (Wave-A-row-level counting: 80 Wave-A rows whose
    identifier matched any Wave-B canonical identifier); 10-row
    delta is within-Wave-B duplicates (same drone_id_prefix under
    multiple FAA DOC tracking numbers). Both counts are correct
    under their respective methodologies; ambiguity over which
    methodology was being asserted caused the first post-codification
    SAR-12 recurrence.

    Methodology must be specified at the paste-result, not deferred
    to a later clarification. Sentinel phrasings: "...by-row count
    over identifiers" / "...candidate-level count over Wave-X
    staging" / "...distinct-key count grouped by source_id" / etc.
    If a count is ambiguous-by-methodology and the dispatch text
    needs only ONE specific cardinality, choose the methodology
    that matches the downstream usage of the assertion (typically
    canonical-row-level for DB-side queries, candidate-level for
    staging-side queries).

  Class (b) — API or schema field names
    Path: Fetch one sample record from the live API; OR inspect
          the live schema for the table/column.
    Paste: actual field name + sample value inline.
    Example:
      $ curl -s https://uasdoc.faa.gov/api/v1/publicDOCRev/OOP000000046
        | jq '.publicRevision | keys'
      ["fccIdentifier","serialNumberDescription","serialNumberEnd",
       "serialNumberStart", ...]
      (NOT documentNumber; field name is trackingNumber on the
       LIST endpoint, serialNumber* on DETAIL)

  Class (c) — Enum membership
    Path: grep current PROJECT_BIBLE.md and BIBLE_AMENDMENTS.md
          for the enum definition; verify against any subsequent
          CP-class extensions.
    Paste: §-section heading + commit SHA + extracted enum line
           inline.
    Example:
      $ grep -n "device_category" PROJECT_BIBLE.md | head -1
      112:| `device_category` | TEXT NOT NULL | enum from §2.1
          (alpr, imsi_catcher, body_cam, police_radio,
           in_vehicle_router, drone, gunshot_detect, hacking_tool,
           covert_cam, gps_tracker, face_recog, drone_detect) |
      (12 values; bible HEAD <commit-SHA>; no §2.1 #14 exists)

  Class (d) — Source completion state
    Path: Check live sources table + extraction_runs ledger.
          Convention: a source is "complete" if it has rows in the
          target table AND has at least one extraction_runs row
          with status='ok'. Per CEO memo-discipline note dated
          2026-05-13, "source completion state" requires checking
          BOTH sources.last_fetched_at (staging signal) AND
          extraction_runs.started_at (ingestion signal).
    Paste: source.id + name + last_fetched_at + last extraction_runs
           row + target table row count inline.
    Example:
      $ sqlite3 db/argus.db "SELECT s.id, s.name, s.last_fetched_at,
        e.started_at, e.records_out FROM sources s LEFT JOIN
        extraction_runs e ON e.source_id=s.id WHERE s.name LIKE
        '%USAspending%' ORDER BY e.started_at DESC LIMIT 1;"
      8 | USAspending federal contracts | 2026-05-04T... |
        2026-05-04T... | 43483
      (USAspending = src 8; DONE at 43,483 procurement_records;
       NOT a Wave-C-new source)

  Class (e) — CP / SAR / memo boundary claims
    Path: grep BIBLE_AMENDMENTS.md for the CP/SAR entry; grep the
          filesystem for the cited memo across all relevant agent
          memory directories.
    Paste: heading line + on-disk file path inline. If the citation
           doesn't resolve, paste "MEMO-NOT-FOUND-ON-DISK" or
           equivalent and surface as a fact-without-verification
           event before proceeding.
    Example:
      $ find /home/kev/argus /home/kev/.claude -name
        "feedback_enum_amendment_needs_schema_migration_sibling.md"
      /home/kev/argus/feedback_enum_amendment_needs_schema_migration_sibling.md
      (authored 2026-05-13T15:55Z; resolves cleanly)

## §3 — Binding scope nuance

Per the multi-actor memo-scope finding surfaced in MAC-87 follow-up:
discipline rules don't bind agents that don't read them. Agent memory
directories are per-actor-class:

  - CEO orchestrator: /home/kev/.claude/projects/<paperclip-uuid>/memory/
  - argus worker context: /home/kev/.claude/projects/-home-kev-argus/memory/
  - other paperclip-company agent contexts: various

S.7's three-surface landing matches the three-actor binding precisely
so each actor reads the rule in their own context. Any future SAR or
memo intended to bind multiple actor classes MUST land canonical text
in each actor's read-path; landing in only one surface and assuming
cross-actor binding is a class-(e)-adjacent error.

## §4 — Anchored case studies

The four-recurrence pattern that triggered S.7 codification (plus the
fifth recurrence discovered during S.7 authoring itself). Each case
is anchored to a durable location per
feedback_avoid_hb_labels_in_durable_artifacts.md.

### Case 1 — Wave-B Marlin baseline count drift (class a)

Dispatch cited "42 staged behavioral_signatures" against actual 33
in raw_observations. Anchor:
  raw/wave_b/_wave_b_bulk_load_2026-05-13.md §3 Board Elevation Item #1

The "42" propagated from earlier Wave-A reporting without
verification at dispatch authoring time. CC validated against live DB
state during pre-flight context load and surfaced the correction.

### Case 2 — Wave-B FAA documentNumber field name drift (class b)

Dispatch §3.3.3 cited documentNumber as the prefix-bearing field on
the FAA RID API. Actual field is trackingNumber on the LIST endpoint
and serialNumberStart/End on the DETAIL endpoint (prefix derived via
LCP). Anchor:
  raw/wave_b/_wave_b_bulk_load_2026-05-13.md (Source 3 stop-the-line
  section, FAA API-shape decision)

The dispatch asserted field shape without fetching a sample record
first; CC halted at stop-the-line discipline rather than improvising
past the gap.

### Case 3 — Wave-C FCC EAS §2.1 #14 invention + sources.id=7 band
mismatch (classes c + d)

Dispatch invented §2.1 #14 for Hak5 (actual §2.1 #8) and asserted
source_type_hint='regulatory' for fcc_grantees (existing sources.id=7
has different band classification). Anchor:
  raw/wave_c/fcc_eas/2026-05-13T18-04-01Z_surfacing.md

CC caught both during pre-flight context load.

### Case 4 — Wave-C USAspending proposed-but-done (class d)

Board proposed USAspending as a Wave-C-new source. Actual: USAspending
= sources.id=8 = 43,483 procurement_records, completed Phase 3 at
2026-05-04 (MAC-8). Anchor:
  MAC-87 snapshot doc §4.2

Crossed the codify threshold (fourth recurrence).

### Case 5 — CP17 phantom-memo citation cascade (class e)

CP17 BIBLE_AMENDMENTS.md entry cited
feedback_enum_amendment_needs_schema_migration_sibling.md which did
not exist on disk at CP17 authoring time. The phantom citation
propagated into MAC-87 §1.4 + §8.2 and CEO memory entries before
verification surfaced it during S.7 authoring. Anchor:
  /home/kev/argus/feedback_enum_amendment_needs_schema_migration_sibling.md
  (memo authored retroactively 2026-05-13T15:55Z per disposition
  option (i) — bibliographic repair) + MAC-87 §8.2 (board awareness
  of the cascade)

Demonstrates that S.7 class (e) verification protects against
citation cascades where a single unverified reference propagates
across surfaces.

### Case 6 — Bible line 112 device_category enum drift vs. live schema (class c)

SAR-12 class (c) example applied to its own commit revealed a
set-membership drift between PROJECT_BIBLE.md line 112
(`alpr, ..., in_vehicle_router, ..., drone_detect` — 12 values)
and the live schema CHECK constraint
(`alpr, ..., drone_detect, unknown` — 12 values). 11-of-12 overlap;
bible has `in_vehicle_router` (§2.1 narrative #5; schema-migration
sibling deferred per
feedback_enum_amendment_needs_schema_migration_sibling.md); schema
has `unknown` (§8.4 / line 537 / §11 #13). MAC-87 §2.5 had asserted
"no drift, matches verbatim" without set-membership verification.
Anchor:
  PROJECT_BIBLE.md line 112 (corrected in the same commit appending
  this case study) + MAC-87 follow-up thread comment d521e669 / f095dfc7

Demonstrates S.7 class (c)'s drift-catching refinement: enum
verification requires comparing BOTH bible-side AND schema-side, not
just confirming each independently. The error class — asserting "no
drift" or "matches verbatim" without set-membership paste-result — is
structurally distinct from the four pre-S.7 recurrences that asserted
positive facts without verification. Same rule applies (class c,
paste-result inline) but the absence-of-drift framing needs the
comparison paste itself, not just citing each side. Codified in the
CEO sibling memo at authoring time.

### Case 10 — MAC-116 §2.3 sweep all 4 sub-items no-op at decomposition time (class a/b decomposition-time-projection-stale sub-class)

CEO sub-dispatch MAC-116 (MAC-101 Stream 1 §2.3 Wave-B+ sources
reclassification sweep) authored 4 per-sub-item §0 baseline-count
projections sourced from CP19-prep notes (~90 FAA listDocs URL-upgrade
candidates, ~325 jlrjr primary_registry rows for band-downgrade,
per-row IEEE upgrade candidates, sources.id=7 'regulatory' band).
Validator ran §6.0 pre-flight count queries at heartbeat start;
**all 4 sub-items tripped the 5%-divergence threshold simultaneously**:

| Sub-item | Decomposition-time projection | Live live-DB | Disposition |
|---|---|---|---|
| (a) 90 FAA listDocs source_url upgrade candidates | 90 | **0** | already absent (MAC-63/MAC-88 closeout post-state) |
| (b) 325 jlrjr primary_registry rows for downgrade | 325 | **0** | already crowdsourced (MAC-88 [`c12bedd`](https://github.com/CascadeForge/argus/commit/c12bedd) jlrjr-refinement post-state) |
| (c) per-row IEEE upgrade candidates | variable | **degenerate** | all 17,844 IEEE rows already primary_registry post-state |
| (d) sources.id=7 in `regulatory` band | `regulatory` | **`primary_registry`** | CP15 §8.2 strict-reading direction-reversal; FCC EAS grantee data is registry-class allocator, not filing-class regulatory |

All four projections were stale assumptions from CP19-prep notes that pre-dated MAC-63/MAC-88/MAC-96 closeouts. Aggregate baselines (identifiers active = 22,464, source_reclassifications = 809, sources = 43) all matched verbatim — the staleness was strictly at the per-sub-item cohort level.

Anchor:
  MAC-116 surface-back comment (Validator §6.0 pre-flight + per-sub-item §6.1-§6.4 disposition tables) + this case study commit + CEO sibling memo `feedback_db_verify_dispatch_claims.md` recurrence #2

Demonstrates a structurally new sub-class: **decomposition-time-projection-stale** — distinct from prior class (a)/(b)/(c) sub-classes. The dispatch authoring did the aggregate-level live-state pre-flight correctly (per S.7 §6.0 5%-divergence threshold) but failed to run per-sub-item count queries at decomposition time. Aggregate baselines can match while per-sub-item cohorts have already drifted to post-state from prior sweeps. The refinement: when DECOMPOSING an aggregate dispatch into per-sub-item child issues with §0 baseline counts, the decomposing agent (CEO or sub-CEO) MUST run each per-sub-item count query at decomposition time, not just the aggregate-level baseline. Validator's §6.0 check is the final defense; this rule prevents the Validator round-trip in the first place.

This is also the **first sources-row vs identifiers-row band-labeling inconsistency** surfaced (sub-item (d)). Sources 1/2/3/7 carry historic `regulatory` band assertions in `sources.source_type` while the identifiers-row data has been correctly labeled `primary_registry` post-CP15. Deferred to single-purpose post-ship work per CEO recommendation + board MAC-101 [`dd7bd55c`](/MAC/issues/MAC-101#comment-dd7bd55c) ratification — not ship-blocking (identifiers-row data correctly labeled, exports unaffected); requires downstream-consumer audit before flip per S.1; new sub-rule (sources-row metadata vs identifiers-row reclassification) needs explicit codification that benefits from its own dedicated heartbeat. Documented in README §3.2 (per dispatch §3.2 contribution-guidance section) as "known sources-row metadata discrepancy (pre-CP15 vestige; identifiers-row data correctly labeled; cleanup queued post-ship)".

Codified in CEO sibling memo `feedback_db_verify_dispatch_claims.md` recurrence #2 (extension to the dispatch-claim-verification rule covering decomposition-time-projection too, not just dispatch-authoring-time).

## §5 — Inline demonstration

The first dispatch under S.7 will demonstrate the discipline by
including the pre-flight as the first §-section of the dispatch
text. Each assertion class touched by the dispatch gets a paste-
result inline. The discipline is most useful when it's visible at
consumption time, not buried in authoring notes.

Subsequent dispatches inherit the pattern. Over time, dispatches
develop a standard "pre-flight" preamble shape that consumers
(other agents, future board members, anyone reading the dispatch
record) can scan to verify the dispatch's working model before
acting on its instructions.

## §6 — Recurrence accounting

Per the recurrence-count audit-trail discipline established at the
S.3 sub-rule level of feedback_bible_amendment_downstream_consumer_audit.md:

  - Recurrence #1 (pre-S.7): Wave-B Marlin 42→33 baseline drift
  - Recurrence #2 (pre-S.7): Wave-B FAA documentNumber field
  - Recurrence #3 (pre-S.7): Wave-C FCC EAS §2.1 #14 + band mismatch
  - Recurrence #4 (pre-S.7): Wave-C USAspending proposed-but-done
  - Recurrence #5 (during-S.7-authoring): CP17 phantom-memo cascade
  - Recurrence #6 (during-SAR-12-ratification): bible line 112
    device_category enum drift vs. live schema; "no drift" absence-
    assertion failure mode (class c)
  - Recurrence #7 (post-codification, MAC-88 sweep pre-flight
    2026-05-14): partition-count drift on FAA Scope 1/2 baseline
    (board §0 paste-result cited 90/325 from Wave-B-candidate-level
    counting; CEO live re-derivation showed 80/335 at Wave-A-row-
    level; the 10-row delta is within-Wave-B duplicates — same
    drone_id_prefix under multiple FAA DOC numbers). Cardinality-
    mismatch class — class (a) baseline cited at one counting
    granularity but consumed at another. Informational, not
    blocking; CEO surfaced + proceeded with 80/335 per board
    ratification at MAC-88 [`a1dab600`](/MAC/issues/MAC-88#comment-a1dab600-e64b-4327-89b3-4a4e3ee4ef05).
    First post-codification recurrence; 2 more before meta-revision
    trigger per §6 threshold.
  - Recurrence #8 (post-codification, MAC-100 dispatch §2
    authoring 2026-05-14): class (b) rule-scope error on §11 #13
    unknown-category exclusion. CEO's MAC-100 dispatch §2 asserted
    `device_category='unknown' is excluded only from high-conf
    per §11 #13, NOT from standard`. Worker (ExtractionWorker
    MAC-100) verified at dispatch start: PROJECT_BIBLE.md §7.5
    line 598 + §11 #13 wording both apply to Lynceus under
    ANY confidence level — i.e., BOTH `argus_export.json`
    AND `argus_export_high_confidence.json` exclude unknown-cat.
    `db/validation/export_lynceus.py:391-393` matches the bible.
    Worker correctly did not propagate the error; standard
    export stayed at 455 (not 455+Class_A=3,900) and worker
    surfaced the divergence in handback as halt-and-surface
    informational finding. No work stoppage; the dispatch
    assertion was load-bearing on dispatch §2 row 4 expectation
    but worker's S.7 class (b) verification at dispatch start
    caught it. CEO surface anchor: MAC-100 §2 reconciliation
    table + commit [`ddc9b30`](https://...).

    Class (b) rule-scope errors are structurally distinct from
    class (b) field-name errors (FAA `documentNumber` →
    `trackingNumber` from earlier recurrences). The rule-scope
    sub-class concerns assertions about WHICH downstream consumers
    a rule applies to, not WHICH field names exist on an API
    response. Both share the class (b) pattern of "asserted
    fact about shape; verify against live source before
    consuming". Worth flagging as a sub-class of (b) for future
    S.7 audit-trail granularity if recurrences continue.

    Second post-codification recurrence; 1 more before meta-
    revision trigger per §6 threshold.
  - Recurrence #9 (post-codification, MAC-101 dispatch §2.1
    authoring 2026-05-14): class (b)-adjacent **table-scope
    sub-class** — distinct from class (b) field-name (FAA
    `documentNumber`→`trackingNumber` pre-S.7 recurrences) and
    class (b) rule-scope (#8 §11 #13 unknown-cat). Board's
    MAC-101 dispatch §2.1 (Item A — manufacturers-table-cross-
    check predicate) asserted `manufacturers` table as a corporate-
    entity registry with expected ~60/75 clears under canonical-
    exact + alias-exact + compound-token tolerance. Validator
    paste-verified at MAC-102 [`7260d2d9`](/MAC/issues/MAC-102#comment-7260d2d9): `manufacturers` is the
    §2.1 surveillance-tech canonical lexicon (34 curated rows —
    Avigilon, Axon, Cellebrite, DJI, Flock Safety, etc.), not a
    general corporate-entity registry. None of the 75 Class B
    candidate vendors (Becton Dickinson medical, Atlas Copco
    compressors, Lumiplan Duhamel signage, etc.) are surveillance-
    tech vendors → as-spec predicate yielded 0/75, not the
    asserted ~60. Validator's halt at §7 case 4 was correct;
    marking `attempted=true` under a mis-scoped predicate would
    have silently consumed the re-entry surface for future
    broader sweeps. CEO ratified option β (multi-registry positive-
    evidence: extend xcheck to `fcc_grantees` 50,153 rows +
    `procurement_records.recipient_name`) at MAC-102 [`ad5a564d`](/MAC/issues/MAC-102#comment-ad5a564d).
    Final outcome: 13/75 cleared (all via `fcc_grantees`).

    Table-scope sub-class structurally distinct from field-name
    + rule-scope: concerns assertions about the SEMANTIC BASIS
    of a named table (lexicon vs registry vs audit-index) and
    the expected match-rate prediction grounded in that basis.
    All three are class (b) "shape claim about source-of-truth";
    they differ in which dimension of "shape" (field names vs
    rule applicability vs table semantics) is the load-bearing
    claim. Worth tracking the sub-class taxonomy for future
    S.7 audit-trail granularity if recurrences continue.

    Board ratification at MAC-101 [`4c7144b8`](/MAC/issues/MAC-101#comment-4c7144b8) (2026-05-14):
    "class (b)-adjacent SAR-12 recurrence #9 — table-scope sub-
    class rather than field-name or rule-scope. Worth tracking
    in the recurrence chain. **Two more before §6 meta-revision
    trigger.**" Board's "two more" framing supersedes the literal
    "three post-codification" threshold-count language below (the
    threshold is now sub-class-aware: post-codification recurrence
    re-counts WITHIN a sub-class, not across sub-classes). Recurrence
    #7 (cardinality-mismatch class a), #8 (rule-scope class b),
    and #9 (table-scope class b) are each a distinct sub-class's
    first occurrence — meta-revision triggers only if a SAME-sub-
    class recurrence occurs three times. Flagged for explicit
    §6 threshold-language revision at next memo-refinement cycle.

    Sibling CEO-side memo: `feedback_predicate_spec_table_semantics_audit.md`
    codifies the table-semantics declaration discipline (lexicon
    vs registry vs audit-index basis) as a CEO sub-dispatch
    decomposition gate. Pre-existing memo flagged the discipline-
    evolution candidate at MAC-101 close; board's recurrence #9
    declaration is the corresponding board-side audit-trail entry.
  - Recurrence #10 (post-codification, MAC-101 dispatch §2.3
    child sub-issue MAC-116 authoring 2026-05-14): class (a)/(b)-
    adjacent **decomposition-time-projection-stale sub-class** —
    structurally distinct from #7 cardinality-mismatch, #8
    rule-scope, and #9 table-scope. CEO sub-dispatch MAC-116
    (Wave-B+ sources reclassification sweep) authored 4 per-sub-
    item §0 baseline-count projections sourced from CP19-prep
    notes that pre-dated MAC-63/MAC-88/MAC-96 closeouts. Validator
    §6.0 pre-flight count queries tripped the 5%-divergence
    threshold on **all 4 sub-items simultaneously**: (a) 90 → 0,
    (b) 325 → 0, (c) per-row degenerate, (d) `regulatory` →
    `primary_registry` direction-reversal. Aggregate baselines
    (22,464 / 809 / 43) all matched verbatim; staleness was
    strictly at per-sub-item cohort level. Full case study at
    SAR-12 §4 Case 10 above.

    Decomposition-time-projection-stale sub-class structurally
    distinct from prior sub-classes: concerns assertions where
    the dispatch-authoring agent correctly ran aggregate-level
    pre-flight but failed to run per-sub-item count queries at
    decomposition time. Aggregate baselines can match verbatim
    while per-sub-item cohorts have drifted to post-state from
    prior sweeps. Worth tracking the sub-class taxonomy:
    (a) cardinality-mismatch, (b) rule-scope, (c) table-scope,
    (d) decomposition-time-projection-stale.

    Board ratification at MAC-101 [`dd7bd55c`](/MAC/issues/MAC-101#comment-dd7bd55c) 2026-05-14:
    "decomposition-time-projection-stale is structurally distinct
    sub-class from #7 cardinality / #8 rule-scope / #9 table-scope.
    The class (a)/(b) sub-class taxonomy continues to bifurcate.
    CEO's discipline refinement at feedback_db_verify_dispatch_claims.md
    recurrence #2 is the right rule extension."

    Sibling CEO-side memo: `feedback_db_verify_dispatch_claims.md`
    recurrence #2 codifies the decomposition-time-projection-verification
    refinement (per-sub-item count queries at decomposition time,
    not just aggregate-level baseline). Pre-existing memo authored
    at MAC-116 decomposition; board's recurrence #10 declaration
    is the corresponding board-side audit-trail entry.

Future S.7 recurrences (if any post-codification) get appended to
this list with anchor + class. The original "three recurrences
post-S.7 would trigger a CP-class revision of S.7 itself" threshold
is superseded by the board's recurrence #9 framing: meta-revision
triggers on three SAME-sub-class recurrences (not three total
post-codification). Threshold-language revision queued for next
memo-refinement cycle (THIS dispatch's §2.1(d) item).

Sub-class taxonomy so far (post-codification):
  - (a) cardinality-mismatch class — recurrence #7 (one occurrence)
  - (b) rule-scope class — recurrence #8 (one occurrence)
  - (c) table-scope class — recurrence #9 (one occurrence)
  - (d) decomposition-time-projection-stale class — recurrence #10 (one occurrence)

No sub-class has hit the three-recurrence meta-revision threshold;
each post-codification recurrence has been a distinct sub-class first
instance, which is consistent with S.7's broad-strokes coverage but
suggests the sub-class taxonomy will keep bifurcating as new
dispatch-shape edge cases surface.

## §7 — Composition with prior discipline

S.7 composes with:

  - feedback_bible_amendment_downstream_consumer_audit.md (S.1
    through S.6) — S.1 case-study sub-rule precedent for anchored
    case studies; S.3 recurrence-count audit trail; S.6
    architectural-absorption pattern (over-ratification at static-
    analysis time, caught at runtime)
  - feedback_enum_amendment_needs_schema_migration_sibling.md —
    sibling-write discipline for schema migrations at first
    promotion
  - feedback_verify_cross_referenced_artifacts_in_public_prose.md —
    parent discipline that S.7 class (e) operationalizes
  - feedback_avoid_hb_labels_in_durable_artifacts.md — anchor
    discipline for case studies (S.7 §4)

S.7 specifically addresses dispatch-authoring-time verification gaps;
the adjacent disciplines address consumer-side, schema-side, or
artifact-durability concerns. The four together form a coherent
pre-flight + downstream + sibling-write + anchor discipline stack
for any dispatch-class work.

## §8 — Codification surfaces

  | Surface | Purpose | Author |
  |---|---|---|
  | BIBLE_AMENDMENTS.md `## SAR-12` | Canonical board-side codification; public-shippable | Board (this entry) |
  | /home/kev/argus/feedback_s7_dispatch_preamble_live_state_verification.md | ExtractionWorker reference | CEO post-SAR-12 |
  | /home/kev/.claude/projects/.../memory/feedback_dispatch_preamble_live_state_verification.md | CEO-side reference | CEO post-SAR-12 |

Sibling memos mirror this canonical text substantively. Surface-
specific framing is allowed (worker examples in worker context, CEO
examples in CEO context) but the rule body, verification paths, and
binding scope remain identical across surfaces.

═══════════════════════════════════════════════════════════════════════


═══════════════════════════════════════════════════════════════════════
Correction Pass 18 — §7.5 + §9 behavioral_signatures sibling export
═══════════════════════════════════════════════════════════════════════

## Correction Pass 18 — §7.5 + §9 behavioral_signatures sibling export file (`argus_export_behavioral_signatures.json`)

**Date:** 2026-05-13
**Source:** Board MAC-88 ratification dispatch [`459daaca`](/MAC/issues/MAC-88#comment-459daaca-ef04-46b1-b337-4480e548ca0a) §3 Item A (board selected Option 2 over CEO's Option 1 at MAC-88 surface-back).
**Bible commit:** This entry + PROJECT_BIBLE.md §7.5 "Behavioral-signatures sibling export — CP18 directive" block insertion + §7.5 Don't bullet addition + §9 deliverables list addition (`argus_export_behavioral_signatures.json`) + §9 item 9 reconciliation-arithmetic section-naming extension. Bible HEAD bumps from `d33491c` to this CP18 commit.
**Status:** Ratified by board at MAC-88 reopen-via-comment 2026-05-13T23:58Z. CEO authors the §-text amendment + amendment-log entry; worker dispatch (ExtractionWorker) lands the export-script code-sibling commit + first generated `argus_export_behavioral_signatures.json` + coverage report extension. Phase C closes at MAC-88 surface-back on worker completion.
**Binds:** ExtractionWorker (new export-script code-sibling commit implementing the §7.5 CP18 shape; first run; reconciliation arithmetic against `behavioral_signatures` table state; coverage-report extension), Validator (no change; behavioral_signatures promotion gates were ratified at MAC-91 Wave-B promotion-cycle-3 close), Lynceus integration team (no change; new export file is Rayhunter-bound not Lynceus-bound), Rayhunter integration (downstream consumer; out-of-Argus migration to read from the new export file lands at Rayhunter v0.X work — surface as separate MAC issue if/when needed).

### Why this Correction Pass exists

MAC-88 Wave-B validation closed 2026-05-13T23:24Z with the first substantive population of the `behavioral_signatures` table (0 → 55 rows; Marlin 53 + 2 Wave-A unlocks at conf=80 via §8.3 academic-corroboration math). The MAC-92 ExtractionWorker handback surfaced §4.4 — at confidence floor ≥70, all 55 behavioral_signatures qualified for export, but `behavioral_signatures` rows have no wire-pattern string suitable for the existing §7.5 high-conf JSON shape `{pattern, pattern_type, description, argus_record_id}`. ExtractionWorker halted-and-surfaced as a CP-class question with three options. Board selected Option 2 (sibling export file) over Option 1 (status-quo, defer to Rayhunter direct-DB-reads) and Option 3 (discriminated-union `entry_kind` field, discouraged per Lynceus-export-shape-purity discipline).

Board's Option 2 reasoning (paraphrased from dispatch §3): direct DB reads couple consumers to schema; the CP14 migration 0010 design specifically established behavioral_signatures as a canonical surface that downstream consumers should read from a stable contract. The sibling file preserves §7.5 contract purity AND gives Rayhunter the canonical surface it needs. Cost: one additional export file paid once. Benefit: consumer-side decoupling from schema evolution (CHECK-enum extensions like 5G_SA / 5G_FR2 / 5G_FR1 if surfaced).

### Corrections applied

1. **§7.5 (new "Behavioral-signatures sibling export — CP18 directive" block).** Inserted after the CP11 dual-artifact paragraph, before the "**Don'ts:**" section. Specifies the new file name (`argus_export_behavioral_signatures.json`), per-record shape `{signature_name, cellular_generation, threshold_json, confidence, argus_record_id}`, `_meta` block (two-key `dropped_in_export`: `below_confidence_threshold` + `unknown_category`), `argus_record_id` recipe (`sha256('behavioral_signature|' + signature_name + '|' + source_id + '|' + cellular_generation_or_NULL_literal)[:16]`), confidence threshold (`70` matching §7.5 canonical high-conf floor), and the alternatives-considered narrative documenting the Option 1 / 2 / 3 decision.

2. **§7.5 Don't bullet (new).** Added: "Do not include `behavioral_signatures` rows in the Lynceus-bound exports (`argus_export.json` / `argus_export_high_confidence.json` / `argus_export.csv`). They export to the sibling file `argus_export_behavioral_signatures.json` per the CP18 directive above. Mixing them into the wire-pattern-keyed Lynceus exports would violate the load-bearing `{pattern, pattern_type, description, argus_record_id}` contract."

3. **§9 deliverables list (item 2 — `exports/` enumeration).** Added new bullet `argus_export_behavioral_signatures.json (Rayhunter-consumable sibling export per CP18; confidence ≥70; shape per §7.5 CP18 directive; behavioral_signatures table rows only)`. Also extended the trailing sentence of item 2 to note that the new file conforms to the §7.5 CP18 sibling-export shape and reconciles independently of the Lynceus-bound files.

4. **§9 item 9 reconciliation-arithmetic.** Extended the existing "Dropped from Lynceus export" reconciliation-arithmetic sentence with a parallel "Behavioral-signatures export reconciliation" section requirement: `behavioral_signatures` source-record count − `below_confidence_threshold` − `unknown_category` = `argus_export_behavioral_signatures.json` `entries` count, matching the `_meta.dropped_in_export` two-key block.

### Confidence threshold rationale (≥70, not ≥80)

The board's dispatch §3 explicitly invited the CEO's read on the right threshold. Two options were on the table:

- **≥70** — matches §7.5 canonical high-conf Lynceus floor; symmetric with `argus_export_high_confidence.json`; consumer-side filtering (Rayhunter strict-mode) can apply tighter floors operator-side.
- **≥80** — matches the §8.3 academic-band corroboration ceiling (Marlin sigs land at conf=80); more conservative for behavioral-signature export specifically.

CEO selected **≥70** for the following reasons:

1. **Contract purity.** The canonical §7.5 high-conf floor is ≥70 per the codified floor-discipline. Bending the floor for one consumer's potential preference fragments the contract; future export files would each get their own ad-hoc floor with no governing rationale.
2. **Internal vs export concern.** The "academic-band 80" framing is internal corroboration math (§8.3 confidence assignment), not export-shape policy. Export filtering operates at the floor; consumer-side tighter filtering operates at the consumption layer. These are different concerns and shouldn't conflate.
3. **Forward-proofing.** Future behavioral_signatures from non-academic sources at conf 70-79 (e.g., a regulatory advisory mentioning a specific cellular-detection signature) would be exported under ≥70 and excluded under ≥80. Excluding them at the export layer loses information that the consumer would otherwise have visibility to.
4. **Today-vs-tomorrow neutrality.** All 55 current rows sit at conf=80 exactly (MAC-91 close: min=max=avg=80.0 uniform). Both ≥70 and ≥80 produce identical 55-row export for the current data. The choice is forward-only.

If a future Rayhunter integration finds the ≥70 floor too noisy for some operator class, the operator-side override file (mirroring Lynceus's `severity_overrides.yaml` CP8 architecture) is the right place to handle it. The export-floor decision is "what's the load-bearing canonical floor for the contract"; that answer is ≥70 today and changes only with a coordinated CP-class amendment, not with per-consumer preference.

### Composition with §11 hard rules

- **§11 #1 (no fabrication)** — unchanged; new export file mirrors verbatim DB content for `signature_name` / `cellular_generation` / `threshold_json` / `confidence` fields. No transformation that could introduce fabrication.
- **§11 #7 (no promotion without provenance)** — unchanged; behavioral_signatures promotion gate (the Validator-side §8.3 corroboration check) is the load-bearing provenance discipline; the export file mirrors post-promotion state.
- **§11 #8 (no confidence drift)** — unchanged; export filter (≥70) operates on the stored confidence value without modification.
- **§11 #11 (amendment-log discipline)** — this CP18 entry is the amendment-log pairing for the §7.5 + §9 §-text changes in the coordinated commit. Bible HEAD bumps from `d33491c` to the CP18 commit alongside this entry.
- **§11 #13 (unknown-category Lynceus-banned)** — composes via the new `_meta.dropped_in_export.unknown_category` key; behavioral_signatures rows with `device_category='unknown'` (none today; forward-proofing) will be excluded from the sibling export at the same governance level as identifiers rows are excluded from Lynceus high-conf.

### Sequencing post-acceptance

1. **CP18 ratifies at this commit.** Bible HEAD bumps from `d33491c` to CP18 commit SHA.
2. **Paired code-sibling commit** (ExtractionWorker dispatch — new export script implementing §7.5 CP18 shape + first run generating `exports/argus_export_behavioral_signatures.json` + coverage report extension). Lands as a separate commit per CP14/CP15/CP16/CP17 precedent (code/bible separation discipline preserved).
3. **State-rotation commit** (PROJECT_STATE.md post-CP18 rotation). Lands at MAC-88 Phase C surface-back (separate heartbeat) after the code-sibling commit closes.
4. **First export reconciliation** at the worker's first-run delivery: 55 rows in DB; expected 55 entries in `argus_export_behavioral_signatures.json`; 0 dropped (all conf=80 ≥70 and none unknown-category in current data).
5. **Rayhunter v0.X migration** (downstream consumer) to read from the new export file — out-of-Argus follow-on; surface as separate MAC issue if/when needed per dispatch §6 OUT-of-scope notation.

### §12 Open Questions impact

- **`behavioral_signatures` Lynceus export shape** (MAC-88 §4.3 Item 1; board's CP-class halt-and-surface from MAC-92 §4.4) — **RESOLVED at CP18 (2026-05-13)** via the sibling-export-file directive above.

### §11 #11 self-binding satisfied

This CP18 entry is the §11 #11 amendment-log pairing for the §7.5 + §9 §-text changes in the coordinated commit. Bible HEAD bumps from `d33491c` to the CP18 commit landed alongside this entry. Schema-version unchanged (CP18 is a §-text export-shape CP; no DB migration touched — the behavioral_signatures table + cellular_generation CHECK + UNIQUE constraint were already CP14 migration 0010 stable).

═══════════════════════════════════════════════════════════════════════


═══════════════════════════════════════════════════════════════════════
Correction Pass 19 — §4.2 source_reclassifications + §7.5 source_type exclusion + §11 #8 audit-trail sub-rule
═══════════════════════════════════════════════════════════════════════

## Correction Pass 19 — §4.2 + §7.5 + §11 #8 — coordinated audit-trail + source_type exclusion landing

**Date:** 2026-05-14
**Source:** MAC-88 board ratification dispatch [`a1dab600`](/MAC/issues/MAC-88#comment-a1dab600-e64b-4327-89b3-4a4e3ee4ef05) (§2 audit-trail framing Option α ratified + §5 high-conf source_type exclusion A3 ratified). CEO pre-flight at [`99bb1438`](/MAC/issues/MAC-88#comment-99bb1438-30a5-4e69-9164-69cacbda649a) surfaced both items.
**Bible commit:** This entry + PROJECT_BIBLE.md §4.2 supporting-table addition + §7.5 source-type exclusion sub-block + §7.5 Don't bullet + §11 #8 sub-rule + migration 0017 (db/migrations/0017_source_reclassifications.sql). Coordinated commit per board explicit bundling.
**Status:** Ratified at MAC-88 a1dab600 2026-05-14. Worker dispatches (Validator full sweep + ExtractionWorker export regen) block on this commit landing.
**Binds:** Validator (sweep execution writes source_reclassifications audit entries per row in same transaction as identifier-row UPDATEs; per-row reclassification_reason must be substantive), ExtractionWorker (post-sweep Lynceus high-conf export regen MUST honor CP19 source_type exclusion + new excluded_source_type _meta key), DBArchitect (migration 0017 sibling commit per established CP14/15/16 pattern), CEO (Phase C surface-back enumerates first population stats + reconciliation arithmetic + architectural firsts).

### Why this Correction Pass exists

MAC-88 Wave-B+ sources reclassification sweep dispatch surfaced two coupled CP-class items at pre-flight:

1. **§11 #8 audit-trail discipline** — the Scope 2 downgrade (335 FAA RID rows from `primary_registry` band to `crowdsourced`) is the first row-level confidence-band DOWNGRADE on already-promoted canonical rows. Prior CPs produced new rows / new bands / upward reclassification, never downward. The existing audit surfaces (git history + extraction_runs + amendment-log) don't make per-row reclassification queryable as a forensic surface. CEO surfaced 4 options at MAC-88 §5.2 (α separate audit table / β raw_observations FK column / γ both / δ rely on git history). Board ratified **Option α** at a1dab600 §2.

2. **High-conf export source_type semantics** — under CP18's ≥70 floor, the 335 Scope 2 downgrades would stay in `argus_export_high_confidence.json` at the new conf=75 value (75 ≥ 70). Board §3.3 expectation was that they drop out (correctness-regression-fix per §11 #8 strict reading: rows whose provenance doesn't support primary_registry shouldn't anchor high-confidence-export semantics). CEO surfaced 3 sub-options at MAC-88 §5.5 (A1 accept +14 lift / A2 revert to ≥80 floor / A3 add source_type exclusion). Board ratified **Option A3** at a1dab600 §5.

The two items are coupled: the audit-table captures the pre/post snapshot for each Scope 2 downgrade, AND the source_type exclusion makes the downgrade actually affect high-conf export semantics. Landing them in one coordinated CP19 commit aligns the audit-trail surface with the export-policy change in a single board-ratification anchor.

### Corrections applied

1. **§4.2 (new bullet — supporting tables).** Added `source_reclassifications` bullet per §3.1 above. Sister to `deployment_observations` (CP4) and `procurement_records` (CP5 sibling carveout). One additive migration (0017), no main-table impact.

2. **§7.5 (new "Source-type exclusion for high-conf export — CP19 directive" sub-block).** Inserted after the CP18 sibling-export directive block, before the Don'ts section. Specifies the new exclusion (`inferred` + `crowdsourced` source_types excluded regardless of confidence value), the rationale (band-meaning coupling), and the orthogonality with §7.5 ≥70 floor + §11 #13 unknown-cat carveout.

3. **§7.5 (new Don't bullet).** Added: "Do not include records with `source_type IN ('inferred', 'crowdsourced')` in `argus_export_high_confidence.json`."

4. **§7.5 _meta extension.** `_meta.dropped_in_export` gains the `excluded_source_type` key (parallel to existing 8 keys). The ExtractionWorker code-sibling commit per CP19 worker dispatch lands the export-script implementation.

5. **§11 #8 sub-rule (new).** Extended §11 #8 with the CP19 sub-rule about row-level reclassification audit-trail discipline. Audit entries land in `source_reclassifications` table per migration 0017 + §4.2 above, in the same transaction as the identifier-row UPDATE.

### Confidence threshold composition (CP18 + CP19)

CP18 ratified ≥70 floor for `argus_export_high_confidence.json`. CP19 layers source_type exclusion on top, orthogonally. The composite filter for high-conf inclusion is now:

```
confidence >= 70
AND device_category != 'unknown'
AND source_type NOT IN ('inferred', 'crowdsourced')
AND geographic_scope passes CP7 filter
```

Standard export (`argus_export.json`) retains ≥30 floor without source_type exclusion. CSV (`argus_export.csv`) is unfiltered per CP11. Behavioral_signatures sibling (`argus_export_behavioral_signatures.json`) retains CP18 ≥70 floor without CP19 source_type exclusion (different shape; doesn't have source_type per row in same way).

### Composition with §11 hard rules

- **§11 #1 (no fabrication)** — unchanged; CP19 doesn't touch provenance discipline beyond strengthening the audit-trail.
- **§11 #7 (no promotion without provenance)** — unchanged.
- **§11 #8 (no confidence drift upward without corroboration)** — extended with the CP19 sub-rule (per §3.3 Option A above). Audit-trail discipline composes naturally with the existing rule; no contradiction with the upward-drift constraint.
- **§11 #11 (amendment-log discipline)** — this CP19 entry IS the amendment-log pairing for the §-text edits in the coordinated commit. Bible HEAD bumps from `ab2cc6a` to the CP19 commit.
- **§11 #13 (unknown-category Lynceus-banned)** — orthogonal to CP19; both filters compose AND-ed in high-conf export.

### Sequencing post-acceptance

1. **CP19 ratifies at this commit.** Bible HEAD bumps from `ab2cc6a` to CP19 commit SHA. Schema version 16 → 17 via migration 0017.
2. **Validator dispatch (sibling-blocked)** — full sweep execution across Scopes 1-4 with per-row `source_reclassifications` audit entries. Validator's commit lands AFTER CP19 (it depends on the migration 0017 table being available).
3. **ExtractionWorker dispatch (blocked by Validator)** — post-sweep Lynceus high-conf export regen honoring CP19 source_type exclusion + new `excluded_source_type` _meta key. Coverage report regen with both CP18 + CP19 reconciliation sections.
4. **CEO Phase C surface-back** — handoff doc, PROJECT_STATE.md rotation, architectural-firsts capture.

### §12 Open Questions impact

None. CP19 doesn't open or close any §12 open question.

### §11 #11 self-binding satisfied

This CP19 entry is the §11 #11 amendment-log pairing for the §-text + schema-migration in the coordinated commit. Bible HEAD bumps from `ab2cc6a` to the CP19 commit landed alongside this entry. Schema version 16 → 17.

═══════════════════════════════════════════════════════════════════════
Correction Pass 20 — SAR-13 per-shape mapper precedent + §11 #16 facts-only promotion from public-but-unlicensed sources
═══════════════════════════════════════════════════════════════════════

## Correction Pass 20 — SAR-13 per-shape mapper precedent + §11 #16 facts-only promotion from public-but-unlicensed sources

**Date:** 2026-05-14
**Source:** MAC-104 Validator surface-back [`3e34d5d0`](/MAC/issues/MAC-104#comment-3e34d5d0-c5b6-4e88-b5aa-220266c3cc04) §6.4 + §6.5 Q1/Q2/Q4/Q6 batched ratification slate. Originating dispatch: MAC-101 Item C Phase 2 [`c81b8df5`](/MAC/issues/MAC-101#comment-c81b8df5-38a5-473f-9638-518c74e47849). Validator commit at staging: [`0921003`](/MAC/issues/MAC-104) (365 deferred-dir rows triaged; 0 promotions; 1 §7.3 reject; 364 HOLDs).
**Bible commit:** This entry + PROJECT_BIBLE.md §11 #16 (new hard rule) + SAR-13 section addition. Coordinated commit per established CP14/15/16/19 bible-pairing pattern.
**Status:** Ratified at MAC-104 CEO response 2026-05-14. Sibling commits (child issues MAC-108 Phase-1 mapper rerun, MAC-109 migration 0011 identifier_types extension + bx_sig routing, MAC-110 Validator close-out) block on this commit landing.
**Binds:** ExtractionWorker (Phase-1 mapper template per SAR-13 §S.2; rerun against 199 source-url-direct violations), DBArchitect (migration 0011 identifier_types CHECK enum extension per Q1 18-type slate; behavioral_signatures backfill per S.3 routing for 6 detector-internal types), Validator (Q3 Flock-attribution promotion, Q4 facts-only promotion per new §11 #16, Q5 §8.3 e4:aa:ea uplift with CP19 audit entry, Q7 attribution_conflict file; post-MAC-108/109 re-triage of 199+85 unblocked rows), CEO (MAC-101 close aggregation pending child landings).

### Why this Correction Pass exists

MAC-104 (MAC-101 Item C Phase 2) is the first substantive heartbeat against the MAC-63 deferred-dir backlog. The Validator's batched surface-back raised seven CP-class questions; four (Q1, Q2, Q4, Q6) are discipline codifications that the bible must hold before downstream execution can land coherently. Three (Q3, Q5, Q7) are row-level execution calls that compose against existing §8.4 + §8.3 + §4.2 discipline and don't require bible amendment — they ride along in the child-issue dispatches.

The four discipline calls are coupled at the cohort level:

1. **Per-shape mapper precedent (Q6).** The 4-shape decomposition Phase 1 used (flat-list / typed-bucket / diff-against-upstream / firmware-binary-mining) kept the Validator's disposition cascade deterministic across 10 deferred dirs with materially different per-repo identifier shapes. Without codification, future deferred-dir cohorts have no protocol-of-record for shape decomposition.
2. **Mapper URL template (Q2).** 199 of 365 Phase-1 rows (54.5%) failed §11 #1 source-url-direct because mappers for repo-aggregated-README cohorts used `<repo>#<section_anchor>` rather than `<repo>/blob/<sha>/README.md#<section>`. The fix is mechanical (template change), not semantic — but the template requirement belongs as an SAR-13 sub-rule so future Phase-1 mappers don't recur.
3. **identifier_type vs behavioral_signatures routing (Q1).** 24 candidate_types staged; 6 are detector-internal patterns (tunable thresholds, logcat detection strings, threat-level enums, OEM probe commands, wireshark filters, modem device paths) that belong in `behavioral_signatures.signature_name` (free TEXT, no enum constraint) rather than `identifiers.identifier_type` (CHECK-enum-constrained). The routing principle composes with the existing §4.2 behavioral_signatures table semantics — codifying it prevents migration-0011-style enum sprawl for detector-internal patterns.
4. **NO_LICENSE_DECLARED public-but-unlicensed source promotion (Q4).** src=39 EthanThePhoenix38/flock-you-camera-detector fork carries an explicit `NO_LICENSE_DECLARED` sentinel and 20 OUI observations. Facts (OUI values) are uncopyrightable per *Feist v. Rural Telephone Service* (499 U.S. 340 (1991)); the source's compilation arrangement may carry unclear copyright posture but the individual factual claims do not. This pattern will recur (community-research repos often lack explicit licenses); codifying the Argus posture as a §11 hard rule prevents per-source ad-hoc deliberation.

Landing these four as a single coordinated CP20 aligns the bible discipline with the child-issue dispatches that execute against it.

### Corrections applied

**A — SAR-13 (new sub-agent rule) per-shape mapper precedent codification.** Inserted after SAR-12 in BIBLE_AMENDMENTS.md. SAR-13 carries three sub-rules:

- **S.1 — Per-shape mapper decomposition for community-research-repo cohorts.** When a Wave-N cohort spans more than one community-research repo with materially different per-repo identifier shapes, the per-shape mapper IS the canonical Phase-1 implementation — not a single union-of-shapes mapper. Sub-classes recognized: (a) **flat-list** — single repository file enumerates identifiers one-per-line or one-per-row (typical: OUI lists, MAC fingerprint lists); (b) **typed-bucket** — repository organizes identifiers by typed sub-sections (BLE services, manufacturer IDs, advertisement intervals); (c) **diff-against-upstream-fork** — identifiers staged as a delta over a known upstream collection (fork commits add net-new rows); (d) **firmware-binary-mining** — identifiers extracted from vendor-shipped firmware binaries via static analysis (Qualcomm MBN strings, NXP MFBL constants, etc.). The per-shape mapper produces clean candidate_type + source_row_key tuples per shape sub-class.
- **S.2 — Mapper URL template (mandatory `/blob/<sha>/<path>#<anchor>` form).** Every Phase-1 mapper output row MUST carry `source_url` in `<repo>/blob/<sha>/<path>#L<line>` form OR `<repo>/blob/<sha>/<path>#<section-anchor>` form for README-anchored content. The bare `<repo>#<anchor>` form is NON-COMPLIANT — it lacks the commit-pinned file path required by §11 #1 (source-url-direct gate). README content anchors as `<repo>/blob/<sha>/README.md#<section>`, NOT as `<repo>#<section>`. This sub-rule retroactively binds the MAC-104 199-row source-url-direct violation cohort to mapper rerun before re-triage (per MAC-108 dispatch).
- **S.3 — identifier_type vs behavioral_signatures routing for novel candidate types.** When a Phase-1 mapper surfaces a novel candidate_type, the routing decision between `identifiers.identifier_type` (CHECK-enum-constrained) and `behavioral_signatures.signature_name` (free TEXT) follows the **device-naming vs detector-internal-pattern boundary**:
  - **identifier_type (CHECK-enum extension via migration):** types that *name a device or device-anchor* — chipset format ids, firmware hashes, BLE service UUIDs, BLE company IDs, RF channel/frequency/protocol constants tied to a vendor product, ALPR camera model strings, x509 cert prefixes embedded in vendor firmware. These rows answer "what device is this?" at query time.
  - **behavioral_signatures.signature_name (free TEXT, no enum):** patterns that describe *detector-side observation surfaces* — tunable thresholds (signal-strength deltas), logcat detection strings (SMS-pattern signatures), threat-level enums (detector-internal state machines), OEM probe commands (modem service-mode hooks), wireshark display-filter strings (tshark traffic patterns), modem-side device paths (`/dev/smd*` AT-command interface paths). These rows answer "what does the detector look for?" at runtime — they belong with the existing 55 behavioral_signatures rows seeded from Wave-A cellular-paper analysis (src=37 NDSS Marlin et al.) rather than as new identifier-type-CHECK entries.

**Decision rule for ambiguous cases:** if the candidate is *vendor-anchored* (the OUI/chipset/binary that ships it is in scope §2.1), route to `identifier_type`. If the candidate is *purpose-anchored* (the value names what to detect, not what is detecting), route to `behavioral_signatures`. When unclear after one heartbeat of deliberation, default to behavioral_signatures (the free-TEXT table has no migration cost; identifier_type CHECK enums require schema migrations).

**B — §11 #16 (new hard rule) facts-only promotion from public-but-unlicensed sources.** Inserted as new §11 #16 in PROJECT_BIBLE.md after §11 #15. Verbatim text:

> 16. **Public-but-unlicensed-source facts-only promotion.** When a public source (community GitHub repo, blog, forum) lacks an explicit license declaration (a `NO_LICENSE_DECLARED` sentinel or the absence of a `LICENSE` file), Argus MAY extract and promote *factual claims* (identifier values, manufacturer attributions, operational context) under the *Feist v. Rural Telephone Service* (499 U.S. 340 (1991)) facts-not-copyrightable doctrine. Argus MUST NOT redistribute the *compilation arrangement* (copying a list-snippet verbatim into `source_excerpt`, mirroring repository structure, or reproducing the source's selection/organization beyond what a single-fact citation requires). Per-row provenance discipline: `source_url` cites the upstream file at a pinned commit (per §11 #1); `source_excerpt` captures the minimal factual context needed for audit (typically the identifier value plus a single-sentence Argus-authored operational note); `notes.upstream_license_posture` records the source's declared posture (`'NO_LICENSE_DECLARED'`, `'MIT'`, etc.) for audit trail. Confidence ceiling follows §8.2 source-band rules (community = `crowdsourced` 50-75; ratification-required cases default to ≤70). This rule composes with §11 #2 (no non-public data — `NO_LICENSE_DECLARED` public repos remain public, so §11 #2 is satisfied) and §11 #15 (no decompiled vendor app source committed — applies orthogonally to any source class). (CP20 — 2026-05-14.)

**C — Validator interpretive guidance for MAC-104 cohort execution (companion to SAR-13 + §11 #16, not bible-binding but documented here for cross-reference).** Q3, Q5, Q7 execute under existing discipline:

- **Q3 (src=38 DeflockJoplin 3 net-new Flock-context MACs):** Promote with `manufacturer='Flock Safety'` (product-vendor lens per §8.4 dual-lens discipline, consistent with id=1 Wave-A precedent), `notes.oui_registry_assignee='Liteon Technology Corporation'` (chip-vendor lens retained for audit), `source_type='crowdsourced'`, `confidence` ≤70 per §8.2 + dispatch §2 ceiling.
- **Q5 (e4:aa:ea §8.3 multi-source corroboration uplift):** Apply §8.3 corroboration formula `min(99, max(originals) + 5) = min(99, 65+5) = 70` to existing id=1 (the Wave-A first Flock detector ratified row at conf=65). UPDATE id=1 confidence 65 → 70 with CP19 `source_reclassifications` audit entry (`reclassification_reason='§8.3 corroboration uplift from src=38 + src=39 multi-source Flock-context observation'`). Separately INSERT a new `oui=e4:aa:ea` row at conf=70 (crowdsourced ceiling) capturing OUI granularity that the existing id=1 MAC-level row doesn't. The new OUI row does NOT enter `argus_export_high_confidence.json` (CP19 source_type exclusion: `crowdsourced` is excluded regardless of confidence). It does enter `argus_export.json` and `argus_export.csv` (no source_type exclusion there).
- **Q7 (src=40 FoggedLens Motorola/Vigilant single-profile attribution_conflict):** File the row as a `conflicts` table entry with `reason='attribution_history_pending_ma_verification'` per memory rule that M&A/registration history claims require verification before validator handoff. Defer resolution to the standing M&A-verification pass (no separate child issue spawned; backlog item).

### §11 hard-rule discipline (cite verbatim from bible HEAD `c883cec`, pre-CP20 lines)

CP20 introduces §11 #16 as a new hard rule. Composition with existing §11 hard rules:

- **§11 #1 (no fabrication)** — composes naturally; §11 #16 binds source_url + source_excerpt provenance discipline for facts-only promotion, preserving §11 #1 strictness.
- **§11 #2 (no non-public data)** — composes orthogonally; §11 #16 explicitly scopes to public-but-unlicensed sources. A `NO_LICENSE_DECLARED` public GitHub repo is public; §11 #2 is satisfied.
- **§11 #7 (no promotion without provenance)** — composes naturally; §11 #16 requires per-row source_url + source_excerpt + `notes.upstream_license_posture` for facts-only promotion. Provenance discipline strengthened, not weakened.
- **§11 #8 (no confidence drift upward without corroboration)** — composes naturally; §11 #16 caps facts-only promotions at §8.2 crowdsourced band (50-75) absent explicit cross-validation. CP19 audit-trail discipline applies if a facts-only-promoted row later upgrades via corroboration.
- **§11 #11 (amendment-log discipline)** — this CP20 entry IS the amendment-log pairing for the §11 #16 + SAR-13 additions in the coordinated commit. Bible HEAD bumps from `c883cec` to the CP20 commit.
- **§11 #15 (no decompiled vendor app source committed)** — composes orthogonally; §11 #15 binds the *content type* committed to git, §11 #16 binds the *license posture* of the source upstream of extraction. Both compose AND-ed.

### Sequencing post-acceptance (child issue ladder)

1. **CP20 ratifies at this commit.** Bible HEAD bumps from `c883cec` to CP20 commit SHA. Schema version unchanged (CP20 is §-text + SAR addition; no DB migration touched). PROJECT_BIBLE.md §11 #16 inserted. BIBLE_AMENDMENTS.md SAR-13 + CP20 entry appended.
2. **MAC-108 (ExtractionWorker, immediate)** — Phase-1 mapper rerun for 199 source-url-direct violations under SAR-13 S.2. Rerun produces corrected `source_url` values for affected rows; Validator re-triage unblocks 199 rows for Q1-banded promotion.
3. **MAC-109 (DBArchitect, immediate, parallel to MAC-108)** — Migration 0011 identifier_types extension adding 18 new types per Q1 slate (ble_protocol_byte_table, rf_channel, alpr_model, ble_service_uuid, ble_company_id, frequency_band, ble_protocol_byte, operator_profile, x509_cert_sha256_prefix, ble_adv_interval, rf_protocol_constant, ble_payload_offset, firmware_sha256_hash, network_endpoint, firmware_image_variant, qualcomm_chip_format_id, firmware_branded_string, rf_burst_duration). Per feedback memory `feedback_cumulative_check_enum_across_sequenced_migrations.md` the migration MUST carry forward ALL prior identifier_type enum values, not just the 18 deltas. Sibling: behavioral_signatures routing for 6 detector-internal types per SAR-13 S.3 (tunable_threshold, wireshark_field, logcat_detection_string, threat_level_enum, modem_device_path, oem_service_mode_command — backfill executes against the 38 affected raw_observations rows via Validator re-triage in MAC-110).
4. **MAC-110 (Validator, blocked by MAC-108 + MAC-109)** — Immediate-actionable Q3 + Q5 + Q7 (3 MACs + 1 uplift + 1 OUI insert + 1 conflict file = ~6 row-level operations) AND post-MAC-108/109 re-triage of 199 mapper-corrected rows + 123 vocab-extension-cleared rows. CP19 audit entry on Q5 uplift. Per-source_id batched transactions. Full export regen at close.
5. **MAC-101 close (CEO, blocked by MAC-110)** — Parent close-aggregation comment, PROJECT_STATE.md rotation, architectural-firsts capture, MAC-63 deferred-dir backlog status update (10 of 10 dirs flushed; MAC-101 fully closed).

### §12 Open Questions impact

- **Q1 vocab-extension slate routing** — RESOLVED at SAR-13 S.3 (18 → identifier_type via migration 0011; 6 → behavioral_signatures via S.3 routing).
- **Q2 Phase-1 mapper template** — RESOLVED at SAR-13 S.2 (mandatory `/blob/<sha>/<path>#<anchor>` form, rerun directive for 199 violations).
- **Q4 NO_LICENSE_DECLARED facts-only promotion** — RESOLVED at §11 #16 (Feist-grounded facts-only promotion permitted with provenance + audit-posture discipline).
- **Q6 per-shape mapper codification** — RESOLVED at SAR-13 S.1 (4-shape sub-class decomposition canonical for future deferred-dir cohorts).

New §12 questions opened: none.

### Why a Correction Pass, not separate SARs

CP20 introduces (a) a new SAR (SAR-13 with 3 sub-rules) AND (b) a new §11 hard rule (#16). Per CP14 / CP19 precedent, when an amendment-batch touches BOTH the SAR catalog AND PROJECT_BIBLE.md §-text in a single coordinated commit, the pairing surfaces as a Correction Pass rather than separate SAR + standalone §-text edit. The CP-class wrapper preserves the discipline that "every bible §-text edit pairs with an amendment-log entry under §11 #11."

### §11 #11 self-binding satisfied

This CP20 entry is the §11 #11 amendment-log pairing for the SAR-13 section addition + §11 #16 §-text addition in the coordinated commit. Bible HEAD bumps from `c883cec` to the CP20 commit landed alongside this entry. Schema version unchanged (16 → 16; no migration).

---

## SAR-13 — Per-shape mapper precedent + URL template + identifier_type vs behavioral_signatures routing

**Origin:** MAC-104 Validator surface-back [`3e34d5d0`](/MAC/issues/MAC-104#comment-3e34d5d0-c5b6-4e88-b5aa-220266c3cc04) §6.4 Q6 + Q2 + Q1 batched ratification slate. CEO ratified at MAC-104 close 2026-05-14. Bible-binding: SAR-13 carries three sub-rules (S.1, S.2, S.3) per CP20 §A above. Verbatim §S.1 / §S.2 / §S.3 text lives under CP20 §A — this header anchors SAR-13 in the sub-agent rule catalog. Future deferred-dir cohort dispatches cite SAR-13 in their Phase-1 mapper acceptance criteria.

### S.1 — Per-shape mapper decomposition for community-research-repo cohorts

[See CP20 §A above for full text.]

### S.2 — Mapper URL template (mandatory `/blob/<sha>/<path>#<anchor>` form)

[See CP20 §A above for full text.]

### S.3 — identifier_type vs behavioral_signatures routing for novel candidate types

[See CP20 §A above for full text.]

---

## SAR-14 — Bible-amendment child-issue-ID-ordering discipline

**Origin:** CP20 [`8de7309`](https://github.com/CascadeForge/argus/commit/8de7309) drafted bible-text referencing downstream child issues by DRAFT IDs (MAC-105/106/107) before the Paperclip system assigned actual IDs. System assigned MAC-108/MAC-109/MAC-110 to the three CEO-spawned children. Required fix commit [`dd26b59`](https://github.com/CascadeForge/argus/commit/dd26b59) to remap the bible references to landed reality per `feedback_bible_amendment_downstream_consumer_audit.md` discipline. Pattern surfaced at MAC-101 close §6.3.f; board flagged as "worth a small SAR-class refinement at next memo-refinement cycle" at MAC-101 [`4c7144b8`](/MAC/issues/MAC-101#comment-4c7144b8) 2026-05-14. Codified here per MAC-101 §2.1(c) dispatch directive.

**Bible-binding:** SAR-14 binds bible-amendment authors (CEO, sub-CEO, and workers when surfacing bible-class changes via halt-and-surface). It pairs with `feedback_bible_amendment_downstream_consumer_audit.md` (S.8 append-don't-mutate sub-rule) — the existing downstream-consumer-audit memo covers the FIX behavior when a collision is found; SAR-14 covers the PREVENT behavior to avoid the collision in the first place.

### §1 — The rule

When a bible amendment will reference downstream child issues by ID (e.g., `Child issues to follow: MAC-X mapper rerun, MAC-Y migration, MAC-Z close-out`), the authoring agent MUST land the child issues FIRST and capture their actual system-assigned identifiers BEFORE writing the bible memo. Do not draft predictive IDs in the bible.

**Forward-only authoring ordering:**

1. Decompose work into child issues + spawn them via `POST /api/companies/{companyId}/issues` (capture returned `identifier` field).
2. Confirm system-assigned identifiers by reading the response.
3. Interleave the captured IDs into the bible memo draft.
4. Commit the bible amendment with consistent IDs throughout the §-text + amendment-log entry + sequencing-post-acceptance section + any cross-references.

**If ordering must be reversed** (rare; bible memo must commit before children spawn for some operational reason): use placeholder text in the bible memo such as "Child issues to be spawned post-ratification; identifiers captured in dispatch follow-on comment." Do NOT use draft IDs that may collide with system-assigned ranges. The follow-on comment on the parent issue captures the actual IDs as a separate audit-trail entry.

### §2 — Case study

**CP20 (2026-05-14) initial commit [`8de7309`](https://github.com/CascadeForge/argus/commit/8de7309)** referenced draft IDs MAC-105/106/107 across:
- `### Status` (next-action enumeration)
- `### Binds` (worker dispatch references)
- `### Sequencing post-acceptance` (child-issue ladder)
- `### S.2` (URL-template-discipline rerun child)

System actually assigned MAC-108/MAC-109/MAC-110 to the three CEO-spawned children. (MAC-105/106 had become unrelated productivity-review issues; MAC-107 was a duplicate-spawn against the MAC-104 scope and was cancelled-as-superseded.) Required fix commit [`dd26b59`](https://github.com/CascadeForge/argus/commit/dd26b59) to remap 7 bible-text occurrences per `feedback_bible_amendment_downstream_consumer_audit.md` discipline.

Fix-commit anchor in dd26b59:
> The MAC-105/MAC-106/MAC-107 identifiers used in CP20 §"Status" / §"Binds" / §"Sequencing post-acceptance" / §S.2 were draft predictions; the system assigned MAC-108/MAC-109/MAC-110 to the three child issues spawned by CEO heartbeat. ... Updating the bible references to match landed reality per feedback_bible_amendment_downstream_consumer_audit.md.

Cost: one corrective commit + bible HEAD bump (`8de7309` → `dd26b59`). Avoidable cost; reordering authoring would have prevented it entirely.

### §3 — Composition with prior discipline

SAR-14 composes with:

- `feedback_bible_amendment_downstream_consumer_audit.md` S.8 (append-don't-mutate audit-table discipline) — S.8 is the FIX behavior when a collision/drift surfaces; SAR-14 is the PREVENT behavior at authoring time. Both share the root: bible-text references to other surfaces must match landed reality, not drafted predictions.
- `feedback_avoid_hb_labels_in_durable_artifacts.md` — anchor discipline for durable artifacts. SAR-14 specifically governs MAC-issue identifiers (a class of durable artifact); the broader rule against drift-prone labels (HB#, sprint #, etc.) applies to all anchors.
- SAR-12 class (e) — citation discipline (memos resolve on disk). SAR-14 governs the parallel discipline for issue-ID citations (resolve to landed system-assigned IDs, not draft IDs).

The three together form a coherent anchor-stability stack for any bible amendment that cites external surfaces.

### §4 — Codification surfaces (sibling memo + audit-trail entry)

| Surface | Purpose | Author |
|---|---|---|
| `BIBLE_AMENDMENTS.md` SAR-14 (this entry) | Canonical board-side codification; public-shippable; binds bible-amendment authors | Board (this entry, MAC-101 §2.1(c) ratification) |
| `feedback_bible_amendment_child_issue_id_ordering.md` (CEO memory) | CEO-side reference + decomposition-time checklist | CEO post-CP20 dd26b59 fix |

Both files convey the same rule. SAR-14 (board-side) is canonical for binding scope; CEO-memory copy is the decomposition-time checklist surface.

### §5 — Forward expectation

If a future bible amendment surfaces a collision pattern that SAR-14 doesn't cover (e.g., a different anchor class: approval IDs, run IDs, commit SHAs from a yet-to-land sibling branch), the discipline carries forward with extension to that anchor class. The principle: **bible-text references must resolve to landed reality, not predictions**.

Bible HEAD bumps with this entry. Schema unchanged. Docs-only commit per the small-bible-amendment precedent (ab2cc6a / 047a273 / 9322500).

---
