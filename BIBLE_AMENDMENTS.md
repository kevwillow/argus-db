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
