# Argus — Bible Amendments Log

## TL;DR

The amendment log for Argus's formal spec ([`PROJECT_BIBLE.md`](PROJECT_BIBLE.md)). Every entry records a discipline-shaping discovery from a release cycle: schema migrations, source admissions, false-positive class codifications, identifier-type vocabulary extensions, downstream-consumer audit gates, and similar contractual evolutions.

Entries come in two classes. A **Correction Pass (CP)** is a numbered amendment with `§N` sub-sections that adds or refines a bible clause. Current ratified passes range from CP1 through CP33 (v1.5.0 ship state). A **Surprise Anti-Recurrence (SAR)** rule is a discipline pattern formalized after the n=3 occurrence threshold — it binds one or more sub-agent roles but does not necessarily edit the bible text. The current SAR roster runs SAR-1 through SAR-18 (v1.5.0 ship state).

First-time readers should start with [`../USER_GUIDE.md`](../USER_GUIDE.md) for the dataset overview, or [`../../CHANGELOG.md`](../../CHANGELOG.md) for the per-version summary. This file is the formal amendment record — load-bearing precision over readability. Each entry pairs with its git commit hash and the case studies that drove its codification.

---

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
| (b) 325 jlrjr primary_registry rows for downgrade | 325 | **0** | already crowdsourced (MAC-88 [`c12bedd`](https://github.com/kevwillow/argus-db/commit/c12bedd) jlrjr-refinement post-state) |
| (c) per-row IEEE upgrade candidates | variable | **degenerate** | all 17,844 IEEE rows already primary_registry post-state |
| (d) sources.id=7 in `regulatory` band | `regulatory` | **`primary_registry`** | CP15 §8.2 strict-reading direction-reversal; FCC EAS grantee data is registry-class allocator, not filing-class regulatory |

All four projections were stale assumptions from CP19-prep notes that pre-dated MAC-63/MAC-88/MAC-96 closeouts. Aggregate baselines (identifiers active = 22,464, source_reclassifications = 809, sources = 43) all matched verbatim — the staleness was strictly at the per-sub-item cohort level.

Anchor:
  MAC-116 surface-back comment (Validator §6.0 pre-flight + per-sub-item §6.1-§6.4 disposition tables) + this case study commit + CEO sibling memo `feedback_db_verify_dispatch_claims.md` recurrence #2

Demonstrates a structurally new sub-class: **decomposition-time-projection-stale** — distinct from prior class (a)/(b)/(c) sub-classes. The dispatch authoring did the aggregate-level live-state pre-flight correctly (per S.7 §6.0 5%-divergence threshold) but failed to run per-sub-item count queries at decomposition time. Aggregate baselines can match while per-sub-item cohorts have already drifted to post-state from prior sweeps. The refinement: when DECOMPOSING an aggregate dispatch into per-sub-item child issues with §0 baseline counts, the decomposing agent (CEO or sub-CEO) MUST run each per-sub-item count query at decomposition time, not just the aggregate-level baseline. Validator's §6.0 check is the final defense; this rule prevents the Validator round-trip in the first place.

This is also the **first sources-row vs identifiers-row band-labeling inconsistency** surfaced (sub-item (d)). Sources 1/2/3/7 carry historic `regulatory` band assertions in `sources.source_type` while the identifiers-row data has been correctly labeled `primary_registry` post-CP15. Deferred to single-purpose post-ship work per CEO recommendation + board MAC-101 [`dd7bd55c`](/MAC/issues/MAC-101#comment-dd7bd55c) ratification — not ship-blocking (identifiers-row data correctly labeled, exports unaffected); requires downstream-consumer audit before flip per S.1; new sub-rule (sources-row metadata vs identifiers-row reclassification) needs explicit codification that benefits from its own dedicated heartbeat. Documented in README §3.2 (per dispatch §3.2 contribution-guidance section) as "known sources-row metadata discrepancy (pre-CP15 vestige; identifiers-row data correctly labeled; cleanup queued post-ship)".

Codified in CEO sibling memo `feedback_db_verify_dispatch_claims.md` recurrence #2 (extension to the dispatch-claim-verification rule covering decomposition-time-projection too, not just dispatch-authoring-time).

### Case 11 — MAC-118 F2/F3 second-disposition authored from stale mental model (class (e) ratifier-disposition-stale-state sub-class)

CEO authored TWO contradictory dispositions on MAC-118 — the second authored from a stale mental model HOURS after the first had been ratified, executed, and the issue closed. Substantive state remained clean; the discipline failure is purely on the ratifier-author side (CEO).

**Full provenance chain (timestamps UTC; surfaces are MAC-118 comment ids):**

| Time | Actor | Surface | Event |
|---|---|---|---|
| 14:49Z | Validator (da137694) | [`7110a211`](/MAC/issues/MAC-118#comment-7110a211) | MAC-118 audit surface-back: F1 sentinel-key consistency + F2 sid=41 `<verify-in-mapper-from-LICENSE-file>` placeholder + F3 operator-path scrub (193 occurrences / 77 files) |
| **14:53Z** | **CEO** | **[`b012ac69`](/MAC/issues/MAC-118#comment-b012ac69)** | **First CEO ratification:** F1 → defer CP21 + F2 → Option (a) verify-in-mapper + F3 → Option B1+B2 scrub with carveouts |
| 15:03Z | Validator (commit) | [`106689b`](https://github.com/kevwillow/argus-db/commit/106689b) | F3 path scrub: 34 tracked files (23 Python B1 + 7 prose B2 + B2-extended); bible / §8.4 / wigle-grant-response carveouts preserved |
| 15:05Z | Validator (commit) | [`18c3d23`](https://github.com/kevwillow/argus-db/commit/18c3d23) | F2 sid=41 backfill: posture = `CC-BY-NC-ND-4.0_with_research_use_clause` + 14 promoted identifiers backfilled with `notes.upstream_license_posture` (canonical key per F1 deferred-ratification) |
| 15:08Z | Validator | [`ed4a51af`](/MAC/issues/MAC-118#comment-ed4a51af) | Surface-back: F2 + F3 commits landed; pre-ship gate PASS |
| 15:11Z | CEO | [`aeb1160d`](/MAC/issues/MAC-118#comment-aeb1160d) | Ratification close: MAC-118 → `done` |
| ... ~2h gap (parallel work on other MAC-101 items) ... | | | |
| **17:23Z** | **CEO** | **[`7547e0d6`](/MAC/issues/MAC-118#comment-7547e0d6)** | **SECOND CEO disposition: F2 → Option (b) defer-to-prose + F3 → spawn MAC-119 child for scrub.** Authored as if findings were still pending; did NOT paste-verify current state. |
| 17:24Z | CEO | MAC-119 filed | Spuriously filed F3 scrub child (REDUNDANT — F3 already landed at 15:03Z) |
| 17:28Z | Validator | [`91ecbb3e`](/MAC/issues/MAC-119#comment-91ecbb3e) | MAC-119 surface-back: "scrub already landed (commit `106689b`); recommend done" |
| 17:29Z | CEO | [`fc284872`](/MAC/issues/MAC-118#comment-fc284872) | **CEO reconciliation comment** — self-identifies as "dispatch-preamble-live-state-verification miss on the disposition author's part — rule applies symmetrically to CEO dispositions, not just dispatches" |
| 17:35Z | CEO | [`5789aeb8`](/MAC/issues/MAC-119#comment-5789aeb8) | MAC-119 → `done` (redundant scrub-already-done ratification) |

Anchor:
  MAC-118 thread [`7110a211`](/MAC/issues/MAC-118#comment-7110a211) → [`b012ac69`](/MAC/issues/MAC-118#comment-b012ac69) → [`ed4a51af`](/MAC/issues/MAC-118#comment-ed4a51af) → [`aeb1160d`](/MAC/issues/MAC-118#comment-aeb1160d) → [`7547e0d6`](/MAC/issues/MAC-118#comment-7547e0d6) → [`fc284872`](/MAC/issues/MAC-118#comment-fc284872) + commits [`18c3d23`](https://github.com/kevwillow/argus-db/commit/18c3d23) + [`106689b`](https://github.com/kevwillow/argus-db/commit/106689b) + CEO investigation surface-back MAC-101 [`78653abe`](/MAC/issues/MAC-101#comment-78653abe) + board ratification MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125)

**Class (e) ratifier-disposition-stale-state sub-class designation:** when a ratifier (CEO or board) authors a SECOND disposition on an issue that has already been ratified, executed, and closed at an earlier surface, without paste-verifying current state. Structurally distinct from class (d) decomposition-time-projection-stale (which is dispatch-authoring-time projection against live data; this is post-resolution disposition against already-landed reality).

Actor-neutral framing preferred per board ratification (MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125) §2): "ratifier-disposition-stale-state" applies symmetrically to CEO and board ratifications.

**Failure-mode classification** (per CEO investigation [`78653abe`](/MAC/issues/MAC-101#comment-78653abe) §2 + board ratification §1): the board's pre-investigation hypotheses — (i) worker-applied-without-surfacing / (ii) manual-edit-outside-dispatch / (iii) unrecorded-dispatch — were each explicitly tested against the evidence and none applied. The actual mode is class (e): CEO authored both dispositions; the second was authored from a stale mental model.

**Substantive outcome (zero harm):**

- 17:23Z second disposition did not propagate
- MAC-119 redundant filing caught by Validator surface-back at [`91ecbb3e`](/MAC/issues/MAC-119#comment-91ecbb3e) within 5 minutes
- Canonical state stays clean: sid=41 = `CC-BY-NC-ND-4.0_with_research_use_clause`, CREDITS.md (commit [`f1a3405`](https://github.com/kevwillow/argus-db/commit/f1a3405)) reflects, LICENSE-DATA §2.1 (commit [`ead49a3`](https://github.com/kevwillow/argus-db/commit/ead49a3)) references correctly
- No §11 hard-rule trip, no data corruption, no consumer-facing impact
- [`fc284872`](/MAC/issues/MAC-118#comment-fc284872) reconciliation comment captures the discipline lesson in audit-trail surface

**Discipline-self-catch shape:** the 17:29Z reconciliation comment self-identified the discipline failure without board intervention. This is the discipline-self-catch shape that makes S.7's audit-trail mechanism load-bearing — recurrence #11 represents the discipline working as designed (Validator + CEO + reconciliation chain caught the drift; canonical state stays clean).

Whether to extend S.7's authoring rule explicitly to ratifier-class actions is the (α)/(β) decision codified at §6 below (board selected (α) with explicit (β) escalation trigger).

### Case 12 — Fabricated GitHub org URL via deterministic-template construction (class (b) field-value sub-class with bidirectional repo↔memory leak path)

CEO authored a fabricated GitHub URL `https://github.com/CascadeForge/argus[.git OR /commit/<sha>]` across multiple bible-text edits, audit-trail entries, repo-doc edits, and memory files. The canonical operator URL is `https://github.com/kevwillow/argus-db`. The fabricated `CascadeForge` org-name is an operator-other-project-employee handle that propagated into Argus context across 25 in-repo + 11 in-memory occurrences before operator caught it at consumption time.

**Surfaced:** Board finding at MAC-124 [`e539cd41`](/MAC/issues/MAC-124#comment-e539cd41-0653-46e4-bdb1-b295eba13704) (2026-05-15) reviewing commit `81931d7`. The fabrication had been propagating since commit [`f45657d`](https://github.com/kevwillow/argus-db/commit/f45657d) (2026-05-14, prior CEO heartbeat).

**Origin + propagation chain:**

| Time | Surface | Event |
|---|---|---|
| 2026-05-14 (prior heartbeat) | bible commit [`f45657d`](https://github.com/kevwillow/argus-db/commit/f45657d) | First fabricated `CascadeForge/argus/commit/<sha>` URL introduced into PROJECT_BIBLE.md §3.1 device_category note |
| 2026-05-14 (subsequent prior heartbeats) | commits [`dfdb052`](https://github.com/kevwillow/argus-db/commit/dfdb052), [`bd1e0e1`](https://github.com/kevwillow/argus-db/commit/bd1e0e1), [`4803ccf`](https://github.com/kevwillow/argus-db/commit/4803ccf), [`47403e3`](https://github.com/kevwillow/argus-db/commit/47403e3), [`da8f21c`](https://github.com/kevwillow/argus-db/commit/da8f21c), [`9295af8`](https://github.com/kevwillow/argus-db/commit/9295af8) | Pattern propagated into BIBLE_AMENDMENTS.md (16×), PROJECT_STATE.md (4×), README.md (3× — 2 shields.io badges + 1 clone URL) |
| 2026-05-14 22:06Z | commit [`c9109de`](https://github.com/kevwillow/argus-db/commit/c9109de) | CEO (this session) introduced 1 new occurrence in SETUP.md Quickstart by drawing the pattern from the existing README clone-URL line as established convention |
| 2026-05-15 02:55Z | commit [`81931d7`](https://github.com/kevwillow/argus-db/commit/81931d7) | CEO modified README.md Quickstart `pip install` line; did NOT touch the existing CascadeForge clone-URL line because edit was scoped to `pip install` only — the fabrication survived intact |
| 2026-05-15 03:04Z | MAC-124 [`e539cd41`](/MAC/issues/MAC-124#comment-e539cd41-0653-46e4-bdb1-b295eba13704) | Board surface-back: "Commit 81931d7 introduced a fabricated GitHub URL... CascadeForge does not refer to anything in the Argus project" |
| 2026-05-15 03:05Z | MAC-124 [`acbf4eaa`](/MAC/issues/MAC-124#comment-acbf4eaa-8075-4876-bf19-9527acae433c) | CEO Phase 1 manifest: 25 in-repo + 11 in-memory occurrences traced + bidirectional leak-path identified |
| 2026-05-15 03:16Z | MAC-124 [`06e328ea`](/MAC/issues/MAC-124#comment-06e328ea-97ea-4377-a6b9-9b3d7c924755) | Board ratifies replacement values + GO Phase 2 bundled fix |
| 2026-05-15 (this commit) | this entry | Phase 2 fix landed: 24 in-repo replacements (25 minus 1 dropped CI badge) + 11 in-memory replacements + SAR-12 §4 Case 12 + §6 recurrence #12 + sub-rule clarification |

**Class (b) field-value sub-class designation:** distinct from prior (b) sub-classes. Recurrence #8 was rule-scope (`§11 #13 unknown-cat exclusion scope`); recurrence #9 was table-scope (`manufacturers` semantics); the pre-codification recurrences were field-name (FAA `documentNumber` → `trackingNumber`). This is **field-value** — the assertion is about the value of a variable inside a deterministic template (the `<org>` variable in the `https://github.com/<org>/<repo>/commit/<sha>` template). The template structure was stable; the variable substitution was fabricated.

**Bidirectional leak-path failure-mode insight:** the load-bearing finding from this recurrence is not the URL itself but the propagation mechanism. The fabrication seeded the repo at `f45657d`; CEO memory files captured the URL form when authoring close-of-close summaries (memory absorbed repo state); subsequent CEO heartbeats authoring new repo content drew the URL form from BOTH the existing repo state AND the memory files (memory reinforced repo). The repo↔memory loop is bidirectional: each surface seeded the other; each surface reinforced the other. Without paste-result verification at any intermediate consumption point, the fabrication propagated for ~24 hours across multiple commits, multiple memory files, and multiple agent heartbeats before operator caught it at MAC-124.

**Why discipline failed at consumption time:** the URL pattern looked like established repo convention (25 occurrences before this session's commits). Each new authoring drew from the established pattern as if from a verified source. The `https://github.com/<org>/<repo>/commit/<sha>` template shape masked the assertion as "just constructing a link from facts" — but the underlying `<org>=CascadeForge` value was itself a fabrication, not a fact.

**Substantive outcome:** zero data corruption (no DB writes), zero §11 hard-rule trip, zero consumer-facing impact (the fabricated URLs would have surfaced as 404s on click but the audit-trail anchors still pointed at the right SHAs). The repo-doc + memory-doc cleanup is mechanical; the load-bearing fix is the discipline codification (sub-rule below).

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
this list with anchor + class.

**Meta-revision threshold (canonical, sub-class-aware per MAC-101 §2.1(d) dispatch directive):**
A CP-class revision of S.7 itself triggers when three SAME-sub-class
recurrences accumulate post-codification — not three total post-
codification recurrences. This codifies the board's recurrence #9
framing at MAC-101 [`4c7144b8`](/MAC/issues/MAC-101#comment-4c7144b8) ("two more before §6 meta-revision
trigger" said in the context of recurrence #9 + the (c) table-scope
sub-class first instance). The sub-class-aware count is the load-
bearing rule; the prior "three total post-codification" framing is
historical and not binding.

  - Recurrence #11 (post-codification, MAC-118 F2/F3 second-disposition
    2026-05-14): class **(e) ratifier-disposition-stale-state** sub-
    class first instance. CEO authored TWO contradictory dispositions
    on MAC-118: first ratification at [`b012ac69`](/MAC/issues/MAC-118#comment-b012ac69) 14:53Z (F2 → Option (a)
    verify-in-mapper); Validator executed at commits [`18c3d23`](https://github.com/kevwillow/argus-db/commit/18c3d23) + [`106689b`](https://github.com/kevwillow/argus-db/commit/106689b)
    (15:03Z–15:05Z); CEO closed issue at [`aeb1160d`](/MAC/issues/MAC-118#comment-aeb1160d) (15:11Z). HOURS
    later at [`7547e0d6`](/MAC/issues/MAC-118#comment-7547e0d6) (17:23Z) CEO authored SECOND disposition
    (F2 → Option (b) defer-to-prose + F3 → spawn child) as if findings
    were still pending; spuriously filed MAC-119 redundant scrub child.
    Validator caught redundancy at [`91ecbb3e`](/MAC/issues/MAC-119#comment-91ecbb3e) (17:28Z); CEO posted
    reconciliation at [`fc284872`](/MAC/issues/MAC-118#comment-fc284872) (17:29Z) self-identifying the
    discipline failure ("dispatch-preamble-live-state-verification
    miss on the disposition author's part — rule applies symmetrically
    to CEO dispositions, not just dispatches"). Full case study at
    §4 Case 11 above.

    Ratifier-disposition-stale-state sub-class structurally distinct
    from prior sub-classes (a/b/c/d): concerns POST-RESOLUTION
    disposition-author actions on issues that already have ratified-
    and-executed audit-trail. Distinct from class (d) decomposition-
    time-projection-stale (which is dispatch-authoring-time projection
    against live data; class (e) is post-resolution disposition
    against already-landed reality). Actor-neutral framing per board
    ratification (MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125-5d4b-43bc-a136-b8353366f36b) §2):
    "ratifier-disposition-stale-state" applies symmetrically to CEO
    and board ratifications.

    Zero substantive harm: 17:23Z second disposition did not propagate;
    MAC-119 redundant filing caught within 5 minutes; canonical state
    stays clean (sid=41 = `CC-BY-NC-ND-4.0_with_research_use_clause`;
    CREDITS.md + LICENSE-DATA §2.1 reflect accurately); fc284872
    reconciliation captures discipline lesson in audit-trail.

    Board ratification at MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125-5d4b-43bc-a136-b8353366f36b) 2026-05-14: "Confirm
    SAR-12 recurrence #11 = class (e) CEO-disposition-stale-state.
    New sub-class first instance. Actor-neutral framing preferred:
    'ratifier-disposition-stale-state' applies symmetrically to CEO
    and board ratifications. Land canonical class (e) wording with
    the actor-neutral framing."
  - Recurrence #12 (post-codification, MAC-124 [`e539cd41`](/MAC/issues/MAC-124#comment-e539cd41-0653-46e4-bdb1-b295eba13704)
    2026-05-15): class **(b) field-value** sub-class first instance.
    CEO authored fabricated `https://github.com/CascadeForge/argus[.git
    OR /commit/<sha>]` URL across multiple bible-text edits, audit-
    trail entries, repo-doc edits, and memory files (canonical:
    `https://github.com/kevwillow/argus-db`). The fabricated `<org>`
    value (an operator-other-project-employee handle) propagated
    across 25 in-repo + 11 in-memory occurrences before operator
    caught it at consumption time on commit [`81931d7`](https://github.com/kevwillow/argus-db/commit/81931d7). Origin
    commit [`f45657d`](https://github.com/kevwillow/argus-db/commit/f45657d) (prior CEO heartbeat). Full case study at
    SAR-12 §4 Case 12 above.

    Field-value sub-class structurally distinct from prior (b) sub-
    classes (field-name + rule-scope + table-scope): concerns the
    VALUE of a variable inside an otherwise-deterministic-template
    construction (e.g., `<org>` inside the
    `https://github.com/<org>/<repo>/commit/<sha>` URL template).
    Distinct from class (a) cardinality-mismatch (which is about
    counting); distinct from class (e) ratifier-disposition-stale-
    state (which is post-resolution; this is authoring-time fabrication).

    **Bidirectional repo↔memory leak-path failure-mode insight:** the
    load-bearing finding from this recurrence is not the URL itself
    but the propagation mechanism. The fabrication seeded the repo at
    `f45657d`; CEO memory files captured the URL form when authoring
    close-of-close summaries (memory absorbed repo state); subsequent
    CEO heartbeats authoring new repo content drew the URL form from
    BOTH the existing repo state AND the memory files (memory
    reinforced repo). Each surface seeded the other; each surface
    reinforced the other. Without paste-result verification at any
    intermediate consumption point, the fabrication propagated for
    ~24 hours across multiple commits, multiple memory files, and
    multiple agent heartbeats before operator caught it.

    Board ratification at MAC-124 [`06e328ea`](/MAC/issues/MAC-124#comment-06e328ea-97ea-4377-a6b9-9b3d7c924755) 2026-05-15:
    "Investigation discipline reads clean. Bundle Phase 2 commit
    covering URL fix + memory cleanup + SAR-12 §4 Case 12 + §6
    recurrence #12 + sub-rule clarification per [§6 deterministic-
    template sub-rule] below. Cross-project context contamination
    flagged but not codified now (defer larger memory-isolation
    question to separate strategic conversation)."

**Sub-class taxonomy so far (post-codification; actor-neutral framing per board MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125-5d4b-43bc-a136-b8353366f36b) §2):**

  - (a) cardinality-mismatch class — recurrence #7 (one occurrence) — MAC-88 sweep FAA partition-count drift
  - (b) rule-scope class — recurrence #8 (one occurrence) — MAC-100 §11 #13 unknown-cat exclusion scope
  - (b) **field-value class** — recurrence #12 (one occurrence) — MAC-124 fabricated GitHub `<org>` URL
  - (c) table-scope class — recurrence #9 (one occurrence) — MAC-101 Item A manufacturers-table semantics
  - (d) decomposition-time-projection-stale class — recurrence #10 (one occurrence) — MAC-116 §2.3 sweep all 4 sub-items
  - (e) **ratifier-disposition-stale-state class** — recurrence #11 (one occurrence) — MAC-118 F2/F3 second-disposition

**Meta-pattern observation (board flagged at MAC-101 [`63b72454`](/MAC/issues/MAC-101#comment-63b72454-5555-4c71-adb6-1f15f7ebdc83) 2026-05-14 + threshold-crossing confirmed at MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125-5d4b-43bc-a136-b8353366f36b)):**
each post-codification recurrence (#7 through #11) has been a distinct
sub-class first instance. No sub-class has yet accumulated a second
occurrence, let alone hit the three-recurrence meta-revision threshold.
The discipline is generating new sub-classes faster than it accumulates
within-sub-class repeats — itself an interesting meta-pattern.

The five-class taxonomy threshold has been crossed: at recurrence #11
the meta-pattern is empirically established (5 first instances; 0
within-sub-class repeats). Two competing interpretations were
identified at MAC-101 [`78653abe`](/MAC/issues/MAC-101#comment-78653abe) §4:

  - (α) S.7's broad-strokes coverage is correct; sub-class bifurcation
    is the right audit-trail granularity; the discipline is succeeding
    (each fresh sub-class first instance is the discipline catching
    a new shape of pre-execution drift at the right time via §6.0
    5%-divergence threshold + audit-trail-event mechanism).
  - (β) S.7 has authoring-time blind spots that sub-class bifurcation
    is masking; the taxonomy keeps bifurcating because S.7's authoring
    rule isn't tight enough. A CP-class revision of S.7's verification
    paths (§2 per-class catalog) would be warranted to explicitly
    cover ratifier-class actions (or whatever the next surfacing
    sub-class is).

**Board ratification (α) selected with explicit (β) escalation trigger** at MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125-5d4b-43bc-a136-b8353366f36b) 2026-05-14 §3 (CEO had recommended (β) at MAC-101 [`78653abe`](/MAC/issues/MAC-101#comment-78653abe) §4):

**(α) reasoning (board-articulated):** the load-bearing question isn't "is the pattern common"; it's "does the pattern produce substantive harm that the existing audit-trail mechanism doesn't catch." Recurrence #11 produced zero substantive harm (17:23Z second disposition didn't propagate; MAC-119 caught within 5 minutes; canonical state stayed clean; fc284872 reconciliation captures the lesson). If the pattern is operationally common AND produces zero substantive harm because the discipline mechanism catches it, that's evidence the discipline is appropriately scoped — not evidence it needs tightening. Codifying a CP-class S.7 extension on n=1 for class (e) is heavy; better to escalate to (β) on n=2 if the (e) pattern recurs specifically.

**(β) escalation trigger (pre-committed at MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125-5d4b-43bc-a136-b8353366f36b) §3.2):** if a second class (e) recurrence (ratifier-disposition-stale-state) surfaces within the next 10 board+CEO heartbeats from this codification, escalate to (β) without further board deliberation. CP21 (or subsequent CP) extends S.7's authoring rule:

> "Any ratifier-class action (CEO or board) authoring forward-looking
> direction on an issue with existing audit-trail comments MUST paste-
> verify current issue state before authoring. Symmetric application
> of SAR-12 §2 verification paths to issue-level disposition events."

Trigger condition: **second class (e) recurrence specifically.** NOT "any sub-class recurrence" — the threshold fires on (e) re-occurrence, not on (a)/(b)/(c)/(d) which have different structural shapes. The (β) extension is specifically for the ratifier-disposition surface.

If the (β) trigger fires, CEO authors the extension dispatch without re-asking board — board's pre-commitment under (α) makes the (β) path conditional but pre-authorized.

**Board-vs-CEO divergence preservation note (per board MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125-5d4b-43bc-a136-b8353366f36b) §3.3 + §6):**
this codification represents the **first substantive board-vs-CEO ratification divergence on a discipline-evolution question** since the architecture took current shape. CEO recommended (β) with strong reasoning at MAC-101 [`78653abe`](/MAC/issues/MAC-101#comment-78653abe) §4; board considered, weighed evidence differently, selected (α) at MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125-5d4b-43bc-a136-b8353366f36b) §3.

Healthy deference shape: CEO surfaces (β) with clear argument → board considers, weights differently → board lands (α) with explicit (β) trigger → CEO honors ratification, doesn't relitigate. The architecture has decision authority on canonical contract changes resting with board; CEO surfaces best reasoning; board decides; CEO honors. Future discipline-evolution questions inherit this shape: recommendation + ratification + honored disposition + audit-trail preservation of the divergence reasoning. The discipline doesn't require board+CEO to always agree; it requires the divergence to be visible and the decision authority to be respected.

**Deterministic-template sub-rule clarification (codified per MAC-124 [`06e328ea`](/MAC/issues/MAC-124#comment-06e328ea-97ea-4377-a6b9-9b3d7c924755) board direction; recurrence #12 case study):**

URLs that follow deterministic templates (e.g., `https://github.com/<org>/<repo>/commit/<sha>`, `https://archive.org/wayback/<url>`, `https://api.fcc.gov/.../<id>`, etc.) require class (b) field-value verification on the variable parts (`<org>`, `<repo>`, root URL host) even when the template structure is itself stable. The deterministic shape masks the assertion as "just construction from facts" when the underlying facts themselves need verification.

The failure mode the recurrence #12 case study surfaces: the template `https://github.com/<org>/<repo>/commit/<sha>` is a stable construction shape (every well-known git host follows the same form). The `<sha>` value is a verifiable fact pulled from `git log`. The `<org>` and `<repo>` values look like they're being constructed from established repo convention — but if the established convention is itself a fabrication that propagated unchallenged, the construction inherits the fabrication.

**Verification discipline:** when authoring deterministic-template URLs (or any deterministic-template asserted values where the variable parts are class (b) field-value claims), paste-verify the variable parts at consumption time. For GitHub URLs specifically, the canonical `<org>/<repo>` value comes from `git config --get remote.origin.url` (or operator confirmation when no remote is configured) — NOT from grepping prior repo commits for the established pattern. Established repo convention can be a propagated fabrication; remote-URL inspection is the source-of-truth.

**Bidirectional propagation surface:** when a fabricated deterministic-template variable lands in a repo, downstream agent memory captures the value as "established repo state" and reinforces it in subsequent authoring. Memory-side cleanup is therefore part of the fix discipline (per MAC-124 [`06e328ea`](/MAC/issues/MAC-124#comment-06e328ea-97ea-4377-a6b9-9b3d7c924755) §3 board direction: "Memory and repo must stay consistent — bidirectional leak path means bidirectional fix"). Repo-only fixes leave the propagation pump primed for recurrence.

This sub-rule is a class (b) refinement, not a sixth top-level class. Future recurrences of class (b) field-value type get appended to §6 recurrence chain under existing class (b) accounting; the "third same-sub-class recurrence triggers meta-revision" rule applies to (b) field-value as it does to (b) rule-scope and (b) table-scope.

Future S.7 recurrences (if any post-codification) get appended to
this list with anchor + class.

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

**Origin:** CP20 [`8de7309`](https://github.com/kevwillow/argus-db/commit/8de7309) drafted bible-text referencing downstream child issues by DRAFT IDs (MAC-105/106/107) before the Paperclip system assigned actual IDs. System assigned MAC-108/MAC-109/MAC-110 to the three CEO-spawned children. Required fix commit [`dd26b59`](https://github.com/kevwillow/argus-db/commit/dd26b59) to remap the bible references to landed reality per `feedback_bible_amendment_downstream_consumer_audit.md` discipline. Pattern surfaced at MAC-101 close §6.3.f; board flagged as "worth a small SAR-class refinement at next memo-refinement cycle" at MAC-101 [`4c7144b8`](/MAC/issues/MAC-101#comment-4c7144b8) 2026-05-14. Codified here per MAC-101 §2.1(c) dispatch directive.

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

**CP20 (2026-05-14) initial commit [`8de7309`](https://github.com/kevwillow/argus-db/commit/8de7309)** referenced draft IDs MAC-105/106/107 across:
- `### Status` (next-action enumeration)
- `### Binds` (worker dispatch references)
- `### Sequencing post-acceptance` (child-issue ladder)
- `### S.2` (URL-template-discipline rerun child)

System actually assigned MAC-108/MAC-109/MAC-110 to the three CEO-spawned children. (MAC-105/106 had become unrelated productivity-review issues; MAC-107 was a duplicate-spawn against the MAC-104 scope and was cancelled-as-superseded.) Required fix commit [`dd26b59`](https://github.com/kevwillow/argus-db/commit/dd26b59) to remap 7 bible-text occurrences per `feedback_bible_amendment_downstream_consumer_audit.md` discipline.

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

═══════════════════════════════════════════════════════════════════════
Correction Pass 21 — coordinated amendment: §4.4 MAP entries + §11 #16 canonical sentinel-key + §8.2 strict-reading acknowledgment + SAR-12 §4 Case 11 + §6 recurrence #11 + sub-class (e) ratifier-disposition-stale-state + (α)/(β) decision + board-vs-CEO divergence preservation
═══════════════════════════════════════════════════════════════════════

## Correction Pass 21 — coordinated CP21 amendment

**Date:** 2026-05-14
**Source:** MAC-101 pre-ship dispatch [`fd6146a3`](/MAC/issues/MAC-101#comment-fd6146a3-ee4b-4d9a-a38d-623ba0cdb463) §2.6 coordinated CP21 directive; consolidating multiple board-ratified amendments into a single coordinated commit per dispatch §2.6 framing.

Specific items + ratification anchors:

- **§4.4 MAP entries (2 MAP + 12 DROP from mig-0018 + 7 DROP from mig-0019):** CEO §2.5 recommendation at MAC-101 [`4367e10b`](/MAC/issues/MAC-101#comment-4367e10b-ff72-486c-84e8-98f3fd7ac75d) + board ratification at MAC-101 [`e246a32a`](/MAC/issues/MAC-101#comment-e246a32a-5a28-467d-b20e-72901a5a3d88). MAC-117 closed at commits [`41da1d6`](https://github.com/kevwillow/argus-db/commit/41da1d6) (migration 0019) + [`30a0252`](https://github.com/kevwillow/argus-db/commit/30a0252) (routing execution); the 7 net-new identifier_types from mig-0019 fold into this CP21 batch per the same DROP framework.
- **§11 #16 canonical sentinel-key (`notes.upstream_license_posture`):** MAC-118 F1 CEO ratification at MAC-118 [`b012ac69`](/MAC/issues/MAC-118#comment-b012ac69) + reconfirmed at MAC-118 [`fc284872`](/MAC/issues/MAC-118#comment-fc284872) reconciliation + LICENSE-DATA §3 cross-reference at commit [`ead49a3`](https://github.com/kevwillow/argus-db/commit/ead49a3).
- **§8.2 strict-reading acknowledgment:** MAC-116 §2.3(d) sources.id=7 direction-reversal finding (dispatch projected `regulatory`, strict reading produces `primary_registry`) + board ratification at MAC-101 [`dd7bd55c`](/MAC/issues/MAC-101#comment-dd7bd55c) §2.
- **SAR-12 §4 Case 11 + §6 recurrence #11 + sub-class taxonomy extension (a/b/c/d/e):** CEO investigation surface-back at MAC-101 [`78653abe`](/MAC/issues/MAC-101#comment-78653abe) + board ratification + actor-neutral framing directive at MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125-5d4b-43bc-a136-b8353366f36b). Sub-class (e) ratifier-disposition-stale-state codified.
- **(α)/(β) decision + (β) escalation trigger pre-commitment:** board selected (α) at MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125-5d4b-43bc-a136-b8353366f36b) §3 (diverging from CEO recommendation of (β) at MAC-101 [`78653abe`](/MAC/issues/MAC-101#comment-78653abe) §4). (β) escalation trigger armed: second class (e) recurrence within next 10 board+CEO heartbeats from this codification escalates to (β) without further board deliberation.
- **Board-vs-CEO divergence preservation note:** first substantive board-vs-CEO ratification divergence on a discipline-evolution question since the architecture took current shape; per board MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125-5d4b-43bc-a136-b8353366f36b) §3.3 + §6.

**Bible commit:** This entry + PROJECT_BIBLE.md §4.4 +21 mapping rows + §11 #16 canonical sentinel-key sub-rule + §8.2 strict-reading acknowledgment + BIBLE_AMENDMENTS.md SAR-12 §4 Case 11 + §6 recurrence #11 + §6 sub-class taxonomy actor-neutral extension + §6 (α)/(β) decision + escalation trigger pre-commitment + board-vs-CEO divergence preservation note. Bible HEAD bumps from [`9979015`](https://github.com/kevwillow/argus-db/commit/9979015) (§6 threshold cleanup) → this CP21 commit.

**Status:** Ratified by board across multiple comments (e246a32a / dd7bd55c / 5d6a8125 / fc284872) over the MAC-101 pre-ship dispatch lifecycle. CEO authors the coordinated bible-text + amendment-log entry; no worker dispatch (no schema change; no migration; no DB-side execution).

**Binds:** Validator (no execution — §4.4 MAP additions are export-discipline reference; new DROPPED-class identifier_types default-handled by existing export pipeline per MAC-110 [`5f1bf2e`](https://github.com/kevwillow/argus-db/commit/5f1bf2e) DROPPED_REASONS extension + MAC-117 [`30a0252`](https://github.com/kevwillow/argus-db/commit/30a0252) migration 0019 DROPPED-class default), DBArchitect (none — no migration), ExtractionWorker (none — Phase-1 mappers + Validator-side promoters converge on canonical sentinel-key `notes.upstream_license_posture` per §11 #16 sub-rule going forward), Lynceus integration team (informational — §4.4 MAP grows by 21 entries; no new pattern_types to support; the 2 alias-collapses route to existing `ble_uuid` / `ble_manufacturer_id` pattern_types).

### Why this Correction Pass exists

MAC-101 pre-ship dispatch [`fd6146a3`](/MAC/issues/MAC-101#comment-fd6146a3-ee4b-4d9a-a38d-623ba0cdb463) authorized §2.6 coordinated CP21 amendment to bundle multiple bible-text touches that emerged across Stream 1 sub-items + Stream 2 surface-backs + the MAC-118 F1/F2/F3 investigation chain. Per dispatch §2.6: "Anything touching §-text in PROJECT_BIBLE.md coordinates as one CP if there are multiple touches; anything that's pure code or pure docs lands separately."

Five distinct touches consolidated:

1. §4.4 Lynceus mapping table — 21 net-new entries (14 from mig-0018 + 7 from mig-0019)
2. §11 #16 canonical sentinel-key sub-rule
3. §8.2 strict-reading acknowledgment
4. SAR-12 §4 Case 11 + §6 recurrence #11 + sub-class taxonomy extension
5. SAR-12 §6 (α)/(β) decision + (β) escalation trigger + board-vs-CEO divergence preservation

Each touch has independent ratification anchor (per Source enumeration above). The coordinated commit preserves the §2.6 dispatch directive while honoring per-touch audit-trail discipline.

### Corrections applied

1. **PROJECT_BIBLE.md §4.4 Lynceus mapping table (lines 148-176 + 21 new rows).** 2 MAP (alias-collapse) + 19 DROP entries appended:
   - **MAP (×2):** `ble_service_uuid → ble_uuid` (CP13 `ble_service` precedent); `ble_company_id → ble_manufacturer_id` (CP14 / migration 0011 precedent). Both alias-collapses per option α at MAC-101 §2.5.
   - **DROP (×12 from mig-0018):** `ble_protocol_byte_table`, `frequency_band`, `ble_protocol_byte`, `operator_profile`, `x509_cert_sha256_prefix`, `ble_adv_interval`, `ble_payload_offset`, `firmware_sha256_hash`, `network_endpoint`, `firmware_image_variant`, `qualcomm_chip_format_id`, `firmware_branded_string`. All forensic / parametric / sub-protocol-level / firmware-anchored; cite existing CP13/CP16 DROP precedents per row.
   - **DROP (×7 from mig-0019):** `asdstan_message_type`, `asdstan_enum_value`, `dji_protocol_struct_format`, `gpt_partition_uuid`, `chipset_codename`, `firmware_build_string`, `firmware_build_uuid`. CEO MAC-101 §2.5 prediction confirmed (forecast was "likely all DROP per broadcast-class-but-not-Lynceus-scannable analysis"). All 7 are broadcast-class enum values OR forensic firmware-anchored identifiers that don't function as single-string match values at the Lynceus pattern_type granularity.
   - Cumulative §4.4 mapping post-CP21: 27 pre-existing + 21 new = **48 cumulative mappings** matching live identifier_type CHECK enum count (post-mig-0019).
2. **PROJECT_BIBLE.md §11 #16 canonical sentinel-key sub-rule** appended to the §11 #16 entry. Canonical key: `notes.upstream_license_posture` (more discoverable than alt-key `notes.facts_only_basis`; alphabetically first in serializations; literal posture-value semantics). Alt-key form preserved on extant rows (no rewrite); new promotions land on canonical form forward-only.
3. **PROJECT_BIBLE.md §8.2 strict-reading acknowledgment** appended after the CP15 §8.2 `primary_registry` sub-banding section. When historical assertions place a source in `regulatory` band but CP15 §8.2 strict reading produces `primary_registry`, the CP15 strict reading governs. Sources 1/2/3/7 sources-row metadata cleanup queued post-ship; identifier-row data already correctly labeled.
4. **BIBLE_AMENDMENTS.md SAR-12 §4 Case 11** anchored case study (MAC-118 F2/F3 second-disposition-from-stale-mental-model with full provenance chain through 11 timestamped events from 14:49Z to 17:35Z). Demonstrates class (e) sub-class structural distinction from prior classes (a)/(b)/(c)/(d).
5. **BIBLE_AMENDMENTS.md SAR-12 §6 recurrence #11** with class (e) ratifier-disposition-stale-state designation (actor-neutral framing per board MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125-5d4b-43bc-a136-b8353366f36b) §2 directive).
6. **BIBLE_AMENDMENTS.md SAR-12 §6 sub-class taxonomy section** extended from 4 to 5 sub-classes with actor-neutral framing across all 5: (a) cardinality-mismatch / (b) rule-scope / (c) table-scope / (d) decomposition-time-projection-stale / (e) ratifier-disposition-stale-state.
7. **BIBLE_AMENDMENTS.md SAR-12 §6 (α)/(β) decision + (β) escalation trigger pre-commitment** codified. Board selected (α) at MAC-101 [`5d6a8125`](/MAC/issues/MAC-101#comment-5d6a8125-5d4b-43bc-a136-b8353366f36b) §3 with explicit (β) trigger: second class (e) recurrence within next 10 board+CEO heartbeats escalates to (β) without further board deliberation. (β) text drafted in bible for pre-commitment honor.
8. **BIBLE_AMENDMENTS.md SAR-12 §6 board-vs-CEO divergence preservation note** captured. First substantive board-vs-CEO ratification divergence on a discipline-evolution question since architecture took current shape. CEO recommended (β); board selected (α); CEO honored. Healthy deference shape documented for future inheritance.

### Composition with §11 hard rules

- **§11 #1 (no fabrication)** — unchanged; CP21 amendments add §-text covering already-ratified architectural decisions; no fabricated identifier values, no fabricated source attributions.
- **§11 #7 (no promotion without provenance)** — unchanged; CP21 amendments operate at bible-text + amendment-log layer; the canonical sentinel-key sub-rule (§11 #16) ensures provenance trail forward-only.
- **§11 #8 (no confidence drift)** — unchanged; the §8.2 strict-reading acknowledgment clarifies which band a source qualifies for under strict reading (CP15 codification); the sources-row metadata cleanup is queued post-ship and not in CP21 scope.
- **§11 #11 (amendment-log discipline)** — this CP21 entry is the §11 #11 amendment-log pairing for the §4.4 + §11 #16 + §8.2 §-text changes in the coordinated commit. Bible HEAD bumps from `9979015` to this CP21 commit alongside this entry.
- **§11 #13 (unknown-cat Lynceus-banned)** — unchanged; CP21 §4.4 MAP entries operate at identifier_type-mapping layer; device_category=unknown rows continue to be excluded from Lynceus exports per §11 #13 regardless of identifier_type MAP status.
- **§11 #16 (Feist facts-only)** — strengthened with canonical sentinel-key sub-rule (`notes.upstream_license_posture`); forward-only canonical-form convergence; extant rows preserved.

### Sequencing post-acceptance

1. **CP21 ratifies at this commit.** Bible HEAD bumps from `9979015` → CP21 commit SHA. Schema unchanged; no migration; no worker dispatch; no DB-side execution.
2. **No paired code-sibling commit needed.** §4.4 MAP additions are export-discipline reference; existing DROPPED_REASONS extensions at MAC-110 [`5f1bf2e`](https://github.com/kevwillow/argus-db/commit/5f1bf2e) + MAC-117 [`30a0252`](https://github.com/kevwillow/argus-db/commit/30a0252) already handle the 21 new identifier_types as DROPPED-class default. The 2 alias-collapse MAPs route to existing pattern_types (`ble_uuid` / `ble_manufacturer_id`) — no new Lynceus pattern_types to integrate.
3. **No paired state-rotation commit.** PROJECT_STATE.md already captures MAC-101 close-of-close at [`1e87b85`](https://github.com/kevwillow/argus-db/commit/1e87b85) + header refresh at [`1495984`](https://github.com/kevwillow/argus-db/commit/1495984) + lines-8-18 refresh at [`4de0233`](https://github.com/kevwillow/argus-db/commit/4de0233); CP21 amendments are bible-internal and do not surface to PROJECT_STATE rotation.
4. **(β) escalation trigger state tracked in CEO memory durables** — CEO records the trigger arm time (this commit timestamp) + the 10-heartbeat counter; if a second class (e) recurrence surfaces within the window, CEO authors the (β) extension dispatch per pre-commitment.

### §12 Open Questions impact

- **§4.4 MAP entries for mig-0018 + mig-0019 net-new identifier_types** — RESOLVED at CP21 per CEO §2.5 recommendation + board ratification. 14 + 7 = 21 net-new entries; all dispositioned (2 MAP + 19 DROP).
- **§11 #16 sentinel-key canonical form** — RESOLVED at CP21 per MAC-118 F1 board ratification.
- **§8.2 strict-reading vs historical assertion conflicts** — RESOLVED at CP21 per MAC-116 §2.3(d) finding + board ratification.
- **Sources 1/2/3/7 sources-row metadata cleanup** — DEFERRED post-ship per CEO recommendation + board ratification at MAC-101 [`dd7bd55c`](/MAC/issues/MAC-101#comment-dd7bd55c); CP21 §8.2 acknowledgment documents the disposition.

### §11 #11 self-binding satisfied

This CP21 entry is the §11 #11 amendment-log pairing for the §4.4 + §11 #16 + §8.2 §-text changes in the coordinated commit. Bible HEAD bumps from [`9979015`](https://github.com/kevwillow/argus-db/commit/9979015) to the CP21 commit landed alongside this entry. Schema-version unchanged (CP21 is a §-text + amendment-log CP; no DB migration touched). The §4.4 mapping table reaches 48 cumulative entries matching the live identifier_type CHECK enum (27 pre + 14 mig-0018 + 7 mig-0019 = 48; verified live at CP21 authoring time).

═══════════════════════════════════════════════════════════════════════


## Correction Pass 22 — §7.5 CSV timestamp canonical format (`first_seen` / `last_verified` ISO-8601 UTC `Z`)

**Date:** 2026-05-14
**Source:** MAC-124 F6 surface-back ([`1b4b77b4`](/MAC/issues/MAC-124#comment-1b4b77b4-91e2-4471-b2f0-8ea081379397)) + board ratification of Option (c) — Argus normalizes + Lynceus tolerates + bible codifies — at MAC-124 [`c077ba04`](/MAC/issues/MAC-124#comment-c077ba04-5bda-4df2-bbd3-6003e50d2a60).

**Bible commit:** This entry + PROJECT_BIBLE.md §7.5 sub-amend (canonical timestamp format directive + §7.5-column shape-vs-format audit findings) + `db/validation/export_lynceus.py::_normalize_datetime` helper + helper applied at CSV writer + `tests/test_export_lynceus.py` 7 new `_normalize_datetime` unit tests + 1 updated CP11 first_seen-shape assertion. Bible HEAD bumps from [previous CP21 HEAD] → this CP22 commit.

**Status:** Ratified by board at MAC-124 [`c077ba04`](/MAC/issues/MAC-124#comment-c077ba04-5bda-4df2-bbd3-6003e50d2a60). CEO authored coordinated bible-text + Argus-side normalization helper + Lynceus-side `_parse_date` multi-format tolerance (defense in depth) + paired test coverage on both sides; no schema change; no migration; no worker dispatch.

**Binds:** Validator (no execution — §7.5 sub-amend is export-discipline reference; helper applied at export_lynceus.py CSV writer time), DBArchitect (none — no migration), ExtractionWorker (none — write paths continue to emit any-shape DATETIME values; `_normalize_datetime` coerces at CSV emission time only), Lynceus integration team (informational — `_parse_date` extended to 4-format tolerant; canonical Z form is the v1.0+ contract; archived pre-CP22 exports continue to import via tolerance).

### Why this Correction Pass exists

The MAC-124 F6 smoke test (`lynceus-import-argus --dry-run` against `argus_export.csv` HEAD `851f76b`, board-authorized at MAC-124 [`330573f0`](/MAC/issues/MAC-124#comment-330573f0-97e5-40c5-9dcf-000af16c782e)) produced unexpected divergence from the §6.3 prediction: 50 imported / 53 errors instead of the predicted 103 imported / 0 errors. **All 53 errors were timestamp parse failures** rooted in a v0.3 contract gap the HB39 Lynceus-handoff bundle missed: `identifiers.first_seen` / `identifiers.last_verified` SQLite columns carry type `DATETIME` (typeless TEXT, no SQL constraint) and historical Argus write paths emit at least four distinct shapes — but Lynceus's `_parse_date` (with comment "UTC timestamps in Argus exports use this format") accepted only the space-separated `"%Y-%m-%d %H:%M:%S"` form, present in only 1 of 22,532 rows.

CP22 codifies the canonical CSV timestamp format, lands the Argus-side normalization, lands the Lynceus-side multi-format tolerance for backward compatibility, and surfaces adjacent §7.5 column shape-vs-format gaps as audit findings.

### Corrections applied

1. **PROJECT_BIBLE.md §7.5 sub-amend (`CSV timestamp canonical format — CP22 (2026-05-14) directive`)** appended after the CP11 sub-A clause. Codifies:
   - Canonical CSV emission: `"YYYY-MM-DDTHH:MM:SSZ"` (ISO-8601 UTC, Z suffix, seconds precision; matches `_meta.exported_at` precedent).
   - Date-only DB rows project to `"YYYY-MM-DDT00:00:00Z"` (preserves day signal).
   - Empty / NULL → empty string `""`.
   - Conservative emission helper raises `ValueError` on unrecognized shapes (future write paths surface immediately rather than silently producing malformed CSV).
   - Consumer-side disposition: Lynceus `_parse_date` is multi-format tolerant for archived-export backward compat (Argus normalizes + Lynceus tolerates = defense in depth).
2. **PROJECT_BIBLE.md §7.5 CP11 sub-A bullet for `first_seen` / `last_verified`** updated to reference CP22 normalization helper.
3. **PROJECT_BIBLE.md §7.5 column shape-vs-format audit (CP22 surface; not fixed in this dispatch)** appended to the CP22 sub-amend block. Five candidate findings flagged for future-CP queueing as drift surfaces: `identifier` normalization, `manufacturer`/`model` casing/whitespace/Unicode, `source_url` URL canonicalization, `notes` heterogeneous structured content, `confidence` 0-100 range docs gap. None ship-blocking for v1.0.0.
4. **`db/validation/export_lynceus.py::_normalize_datetime(value)`** helper added with full docstring covering accepted shapes + canonical output + raise-on-unrecognized-shape behavior. Applied to `row.first_seen` and `row.last_verified` immediately before `csv.DictWriter.writerow`.
5. **`tests/test_export_lynceus.py`** + 7 new `_normalize_datetime` unit tests covering empty/None, ISO-with-µs-offset, ISO-with-Z idempotency, space-separated, date-only, ISO-with-nonzero-offset → UTC coercion, and unrecognized-shape ValueError. Updated `test_csv_first_seen_non_empty_for_wave_a_row` assertion from `"2026-05-06 00:30:28"` (pre-CP22 space-separated form, which the test fixture still emits at the DB layer) to `"2026-05-06T00:30:28Z"` (post-CP22 normalized form). Full suite 69/69 → 76/76 passing.
6. **`~/lynceus-warden-main/src/lynceus/cli/import_argus.py::_parse_date(value)`** extended to multi-format tolerant. Tries ISO-with-Z (canonical) → ISO-with-offset → space-separated → date-only in priority order. Returns int Unix UTC timestamp or None for empty. Backward-compat with archived pre-CP22 exports.
7. **`~/lynceus-warden-main/tests/test_import_argus.py`** + 5 new `_parse_date` tolerance tests covering all 4 shapes + non-zero-offset coercion-to-UTC. Restored a `_wl_count` assertion to `test_malformed_date_logged_as_row_error` that was orphaned by the CP22 edit. Full suite 77/77 → 82/82 passing.

### Composition with §11 hard rules

- **§11 #1 (no fabrication)** — unchanged; CP22 amendments codify already-emitted-but-unspec'd format conventions.
- **§11 #8 (no confidence drift)** — unchanged; CP22 operates at CSV emission layer only; confidence values pass through unchanged.
- **§11 #11 (amendment-log discipline)** — this CP22 entry is the §11 #11 amendment-log pairing for the §7.5 sub-amend `+` `_normalize_datetime` helper `+` `_parse_date` tolerance commits. Bible HEAD bumps to the CP22 commit alongside this entry.

### Sequencing post-acceptance

1. **CP22 ratifies at this commit.** Bible HEAD bumps to CP22 commit SHA. Schema unchanged; no migration; no worker dispatch.
2. **CSV regen runs as Step 4 of F6 dispatch** to capture post-CP22 `argus_export.csv` with normalized `first_seen` / `last_verified` columns and a fresh sha256 anchor.
3. **Smoke test re-runs as Step 5 of F6 dispatch** (`lynceus-import-argus --dry-run` against the regenerated CSV). Expected output: Total 22,532 / Imported **103** / Errors **0** / mac_range 17,794 / unknown_type 4,635 / reconciliation holds.
4. **Decisions A1/A2/B1/B2 (enum extension scope + source_type discipline placement)** stay deferred per board direction at MAC-124 [`c077ba04`](/MAC/issues/MAC-124#comment-c077ba04-5bda-4df2-bbd3-6003e50d2a60); CP22 unblocks the 103-row clean baseline that A1/A2/B1/B2 builds on.

### §12 Open Questions impact

- **`first_seen` / `last_verified` canonical CSV format** — RESOLVED at CP22 per board ratification. Canonical: ISO-8601 UTC with `Z`, seconds precision. Pre-CP22 archived-export backward compat preserved Lynceus-side via `_parse_date` multi-format tolerance.
- **Adjacent §7.5 column shape-vs-format gaps (`identifier`, `manufacturer`/`model`, `source_url`, `notes`, `confidence` docs gap)** — SURFACED at CP22 audit. Not fixed in this dispatch; future CP candidates as drift surfaces.

### §11 #11 self-binding satisfied

This CP22 entry is the §11 #11 amendment-log pairing for the §7.5 sub-amend §-text changes in the coordinated commit. Bible HEAD bumps to the CP22 commit landed alongside this entry. Schema-version unchanged (CP22 is a §-text + helper + tests CP; no DB migration touched).

═══════════════════════════════════════════════════════════════════════


## Correction Pass 23 — coordinated amendment: wide-net cycle-{1,3,4} schema-contract patches + migrations 0020 + 0021 + downstream-consumer audit

**Date:** 2026-05-17
**Source:** MAC-169 dispatch (MAC-168 P1) — wide-net cycle-{1,3,4} schema-contract patches authored 2026-05-15 → 2026-05-16 and consolidated into a single coordinated bible-text + migrations + downstream-consumer audit per the [bible amendment downstream-consumer audit](feedback_bible_amendment_downstream_consumer_audit.md) discipline. Patch documents:

- `~/argus-internal/new data 5.16/schema_contract_patch_notes_license.md` — cycle-1 (5 drifts; license-into-notes folding, cross-validation column renames)
- `~/argus-internal/new data 5.16/schema_contract_patch_cycle3.md` — cycle-3 (7 findings; source_type enum gap, source_excerpt per-table caps, vendor_canonical_name verbatim semantics, agency_name concatenation, CourtListener token mandate, state SoS automated-access gating, manufacturers_aliases nonexistence)
- `~/argus-internal/new data 5.16/schema_contract_patch_cycle4.md` — cycle-4 (6 findings; CourtListener V4 mandatory, V4 schema divergence + result-count compression, /search/ rate ceiling, text-pattern entity-disambiguation discipline)
- `~/argus-internal/new data 5.16/state_sos_access_mode_admission_addendum.md` — `access_mode` notes_json convention spec
- `~/argus-internal/new data 5.16/paperclip_integration_priority_brief.md` — integration route map (gates P2-P6 on CP23)

**Bible commit:** This entry + PROJECT_BIBLE.md sibling §-text additions (§4.2 `sources.source_type` enum extension + new source-class bands; §4.2 `procurement_records` vendor_canonical_normalized column documentation; §4.2 `manufacturers.aliases` comma-string clarification; §4.3 source_excerpt per-table cap table + access_mode notes_json convention; §4.5 procurement-only carveout cross-reference unchanged; §8.2 vendor-matching alias-aware-join discipline; §8.3 short-vendor-name disambiguation discipline) + migration `db/migrations/0020_source_type_enum_extension.sql` + migration `db/migrations/0021_procurement_vendor_canonical_normalized.sql` + Python module `db/normalize_vendor.py` + backfill `db/backfill_0021.py` + DATA_DICTIONARY.md schema_version=21 refresh + METHODOLOGY.md disambiguation + alias-aware-join semantics. Bible HEAD bumps from [`c62dc1b`](https://github.com/kevwillow/argus-db/commit/c62dc1b) → this CP23 commit. **Schema version 19 → 21.**

**Status:** CEO-authored coordinated bible-text + migrations + downstream-consumer audit per the MAC-169 dispatch directive. Both migrations applied to `db/argus.db`; live verification clean (43 sources / 43,483 procurement_records / `PRAGMA integrity_check = ok` / 507/507 tests passing). Backfill of `vendor_canonical_normalized` populated all 43,483 procurement_records rows with non-empty normalized keys (zero upstream-blank inputs spot-checked).

**Binds:**
- Validator (no execution in this CP; P2-P6 dispatches do the per-source admissions under the new bands and the alias-aware-join cross-validation pattern).
- DBArchitect (this CP).
- ExtractionWorker (no execution; the access_mode notes_json convention applies to future runguides; manufacturers.aliases append semantics are forward-only).
- Lynceus integration team (informational — schema_version bumps 19 → 21; the new source_type values do not surface in Lynceus exports because Lynceus consumes `identifiers` rows not `sources` rows; the vendor_canonical_normalized column is internal cross-validation infrastructure, not an export surface).

### Why this Correction Pass exists

MAC-169 dispatch (CP23 coordinated amendment) gates Priorities 2-6 (UK Companies House, SEC EDGAR, USAspending deep-extension, State SoS, CourtListener) on CP23 ratification. Three patches authored across 2026-05-15 → 2026-05-16 surfaced schema-contract drift that pre-existing runguides had encoded incorrectly; folding the corrections into a single coordinated bible-text + migrations + audit avoids per-priority rework downstream and gives the future-state P2-P6 admissions a clean canonical reference.

### Live-state preamble (paste-not-cite per S.7)

Verified 2026-05-17 against `db/argus.db` (post-migration):

```
schema_version          = 21   (0021_procurement_vendor_canonical_normalized, 2026-05-17 05:07:32)
                              (0020_source_type_enum_extension,             2026-05-17 05:07:17)
                              (0019_identifier_types_round2,                2026-05-14 17:24:59)
identifiers_total       = 22,612
  non_superseded        = 22,532
  superseded            = 80
behavioral_signatures   = 131
sources                 = 43        (unchanged; P2-P6 admit new rows)
procurement_records     = 43,483    (unchanged; P3+P4 ingest)
manufacturers           = 34
source_reclassifications= 809
PRAGMA integrity_check  = ok
```

### Corrections applied

1. **Migration 0020 — `sources.source_type` enum extension (CP23 §-text addition + CEO Path B ruling).** Three net-new values appended to the `sources.source_type` CHECK enum via table-rebuild per the 0009 / 0015 / 0018 / 0019 precedent. Cumulative state: 10 prior + 3 net-new = 13 values. Live rebuild verified (43 sources rows preserved column-for-column; PRAGMA integrity_check ok; new values accepted, bogus rejected):
   - `judicial_filing`        — Court records and RECAP-class artifacts (CourtListener V4 admissions cycle-3 RG3). Replaces the silent fallback to `regulatory` previously applied at staging.
   - `disclosure_filing`      — SEC EDGAR + analogous corporate-disclosure filings (wide-net cycle-1 RG5 admission). Distinguishes corporate-self-disclosure from equipment-authorization regulatory records.
   - `procurement_disclosure` — Supplier-self-disclosure / vendor-side procurement artifacts. Distinguishes vendor-disclosed contracts from the agency-side procurement records that the existing `procurement` band covers.

   **The 3 new bands are source-tier taxonomy only.** Promotion-pipeline confidence bands (§8.2) bind on the identifier-row `source_type` (separate enum on the `identifiers` table; not extended in CP23), and identifier rows promoted from sources of these new classes still land under existing identifier source_type bands per §8.2 strict reading. The new sources-tier taxonomy is informational at the registry-of-sources tier; it does not lift any confidence ceiling.

2. **Migration 0021 — `procurement_records.vendor_canonical_normalized` column.** Per cycle-3 §1 finding #4 + CEO Path B ruling, a deterministic alias-collapse join key is materialized as a column (rather than a per-query alias-aware JOIN) for query-plan-friendliness at the 43,483-row scale and forward-compat with future INSERT paths. Schema change is a single ALTER TABLE ADD COLUMN NOT NULL DEFAULT '' + supporting B-tree index. Backfill populated via the companion `db/backfill_0021.py` (calls the pure function `db.normalize_vendor.normalize_vendor_name`). Live state post-backfill:

   ```
   total procurement_records:               43,483
   rows with non-empty normalized:          43,483
   distinct vendor_canonical_name:          1,157
   distinct vendor_canonical_normalized:    1,141    (collapse ratio 0.9862)
   ```

   Top alias-collapse wins (paste-not-cite):
   - `motorola solutions`                          — 3 distinct raw variants
   - `cellebrite` / `dedrone defense` / `engility` / `general dynamics information technology` — 2 distinct raw variants each

   Spot-check AXON: `'AXON ENTERPRISE, INC.'` → `'axon enterprise'`. SOUNDTHINKING: `'SOUNDTHINKING, INC.'` → `'soundthinking'`. BERLA: `'BERLA CORPORATION'` → `'berla'`. MOTOROLA: `'MOTOROLA SOLUTIONS, INC.'` → `'motorola solutions'`.

   **Normalization algorithm (apply in order; pure function over rows):**
   1. `LOWER()`
   2. Strip ALL punctuation (chars in `. , ; : ' " ( ) [ ] { } / \ \` ~ ! @ # $ % ^ & * + = | < > ?`)
   3. Collapse runs of whitespace → single space
   4. Strip leading/trailing whitespace
   5. Repeatedly strip trailing whole-word suffix tokens (matched case-insensitively after step 1; iterate until no terminal suffix remains): `incorporated`, `corporation`, `company`, `limited`, `gmbh`, `llc`, `l l c`, `ltd`, `plc`, `inc`, `corp`, `co`, `lp`, `llp`, `ag`, `sa`, `pty`, `bv`
   6. Re-strip whitespace
   7. Empty result → store `''` (column is NOT NULL DEFAULT `''`)

   Algorithm canonical reference: `db/normalize_vendor.py::normalize_vendor_name` (pure function, callable from cross-validation + tests without DB state). DATA_DICTIONARY.md §-procurement_records documents the prose for downstream-consumer audit.

3. **PROJECT_BIBLE.md §4.2 `sources` supporting-table entry** — expanded with the three new source_type values + reference to migration 0020.

4. **PROJECT_BIBLE.md §4.2 `procurement_records` supporting-table entry** — expanded with the `vendor_canonical_normalized` column documentation + reference to migration 0021 + normalization algorithm cross-reference to DATA_DICTIONARY.md.

5. **PROJECT_BIBLE.md §4.2 `manufacturers` clarification** — codified that aliases live as a comma-separated TEXT string on `manufacturers.aliases`, **NOT** in a separate `manufacturers_aliases` table (which does not exist). Append semantics: `aliases = aliases || ',new'` with NULL/empty guard. Lookup semantics: `WHERE aliases LIKE '%term%'`.

6. **PROJECT_BIBLE.md §4.3 source_excerpt per-table CHECK constraint cap table — CEO finding sub-block on cycle-3 §1 #3 contradiction.** This is the authoritative reference. **The cycle-3 patch §1 finding #3 source_excerpt cap claims contradict the live schema; CP23 codifies DB-verified actuals (verified 2026-05-17 against `db/argus.db` post-migration):**

   | Table | Live CHECK constraint | Cycle-3 patch §1 #3 claim |
   |---|---|---|
   | `identifiers` | `CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200)` | claimed ≤500 |
   | `raw_observations` | no CHECK constraint (plain TEXT) | claimed ≤500 |
   | `procurement_records` | `CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200)` | claimed ≤200 (correct) |
   | `council_minutes_matters` | `CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200)` | claimed TBD-verify |
   | `behavioral_signatures` | column does not exist | claimed TBD-verify |

   **DB-verified actuals supersede cycle-3 patch language wherever the two diverge.** Future runguides MUST consult this CP23 table for the canonical per-table cap; the cycle-3 patch document is legacy schema-truth-as-of-2026-05-16-with-known-drift on this single sub-item. The `identifiers` ≤200 cap is the live state post-0001 + CP14 batch rebuilds (matched the rebuild-pattern at each migration); the `raw_observations` lack-of-constraint is the live state per 0001 (app-level enforcement at 200 via `db/sources/vendor_docs.py::raise_on_overflow`, NOT a column CHECK; see 0006 migration header for the prose); `procurement_records` and `council_minutes_matters` both carry the ≤200 cap; `behavioral_signatures` has no source_excerpt column (provenance is captured via `source_id` + `source_file_relative` + `source_line` + `evidence_json` per the migration 0010 schema).

7. **PROJECT_BIBLE.md §4.3 `access_mode` notes_json convention** — codified the `notes.access_mode` field on `sources` rows. Documented value vocabulary (initial set; open for future extension):
   - `automated_api`             — source queried via documented API; end-to-end automated
   - `automated_html_parse`      — source queried via automated HTML scraping; no anti-bot wall
   - `automated_with_auth`       — automated, but requires API key / token / user-agent
   - `mixed_automated_manual`    — some candidates automated, some operator-manual (e.g., the intl_registries cycle 2 mix)
   - `operator_manual_only`      — all access is operator-manual via browser; automation structurally blocked (CAPTCHA, anti-bot wall, session gates)

   **Discipline guarantees (uniform across access_modes):** per-row provenance discipline + promotion-gate confidence band are IDENTICAL regardless of access_mode. The `access_mode` field is informational/operational only, NOT a confidence modifier. Operator-manual findings carry `notes.fetch_mechanism="operator_manual_browser"` per-row (row-level, complementing the source-level access_mode).

   **First-class column promotion deferred to future CP** once the value-set stabilizes (probably after 1-2 more cycles' worth of evidence; per cycle-3 addendum §6 default recommendation). Sources admitted prior to CP23 do NOT require backfill — absent-access_mode is equivalent to `automated_api` per backward compat.

8. **PROJECT_BIBLE.md §4.3 license-posture register additions** — codified four documented license-posture vocabulary values that live in `sources.notes.license` (NOT a CHECK constraint; the field remains free-form for future extension). Values registered at CP23:
   - `OGL-3.0`                   — UK Companies House cycle-1 admission; UK government Open Government Licence v3.0
   - `PUBLIC_DOMAIN`             — SEC EDGAR cycle-1 admission; US federal-government work product (17 USC §105)
   - `US_STATE_PUBLIC_RECORDS`   — DE / CA / TX state SoS cycle-3 admissions; US state public-records statutes (DE Title 8 §391, CA Gov Code §6253, TX Bus Org Code Ch 22)
   - `CC0`                       — CourtListener cycle-4 admission (Free Law Project metadata dedication)

   These compose with the pre-existing `notes.upstream_license_posture` canonical sentinel-key (CP21 §11 #16 sub-rule) for identifier-row promotion gates. Source-tier `notes.license` documents the upstream posture; identifier-tier `notes.upstream_license_posture` (CP21 canonical key) carries it forward to per-row license-aware downstream consumer filtering.

9. **PROJECT_BIBLE.md §8.2 cross-validation alias-aware-join discipline.** Per cycle-3 §1 finding #4 (`procurement_records.vendor_canonical_name` is upstream USAspending verbatim, NOT Argus-canonical), cross-validation queries against `procurement_records` MUST use the new `vendor_canonical_normalized` join key OR an alias-aware JOIN against `manufacturers.canonical_name`/`manufacturers.aliases`. Direct equality on `vendor_canonical_name` misses legitimate matches (e.g., "AXON ENTERPRISE INC" vs "Axon Enterprise, Inc." vs "AXON ENT INC" — all collapse to `axon enterprise` in the normalized column; 3 of 5 raw variants for "MOTOROLA SOLUTIONS, INC." were captured in the live backfill collapse). Per CP23 default discipline: the pre-computed `vendor_canonical_normalized` is the preferred join key at integration time.

10. **PROJECT_BIBLE.md §8.3 short-vendor-name disambiguation discipline** (per cycle-4 §1 finding #6 — the Berla collision). Short vendor names (≤6 chars or single-word) in text-pattern-matching sources without entity disambiguation produce false-positive STRONG matches against unrelated cases with overlapping vocabulary (Berla collision case study: "Berla Kay Strong v. Thomas Wesley Strong" is a family-court matter where "Berla" is a given name, NOT the digital-forensics vendor). Future text-pattern-source runguides MUST bake disambiguation into §4 match scoring rather than punting to integration-time review. Disambiguation options:
    - Co-occurrence filter (require the matched query token to appear alongside another known vendor-specific token within N words)
    - Entity-type tagging (filter to corporate-party-only matches if the source exposes party-role metadata)
    - Operator review of WEAK/STRONG candidates for short vendor names (≤6 chars or single-word) before promotion

    The cycle-3 RG3 Berla 3-case staging is captured with verbatim case_name + party_list for paperclip de-dupe at integration; future runguides bake disambiguation into match scoring upstream.

11. **PROJECT_BIBLE.md §4.3 license-into-notes folding contract** (cycle-1 finding #1, formalized). `sources` table license fields live INSIDE `notes_json`, NOT as top-level columns. Canonical sources-row JSON contract: top-level keys are `name`, `url`, `source_type`, `tier`, `notes_json`, `last_fetched_at` (DATETIME), `last_status` (TEXT); `notes_json` includes `license`, `license_attribution`, `license_posture` + per-admission audit fields. Runguide-validator contract is direct JSON-to-JSON without intermediate transformation. Translator script `extraction_outputs/_tooling/translate_license_to_notes.py` (cycle-1 patch §2) covers retroactive translation of already-staged outputs from runguides authored before this clarification.

12. **PROJECT_BIBLE.md §4.3 cross-validation column normalizations** (cycle-1 findings #2-#4, formalized). Cross-validation queries normalize to live schema columns:
    - `procurement_records`: `vendor_canonical_name` (NOT `awardee_name`), `agency_name` (NOT `awarding_agency`); split `agency_name` on `" / "` for hierarchical use (`{awarding_agency, awarding_sub_agency}`).
    - `council_minutes_matters`: `agency_name` + `agency_geographic_scope` (NOT `municipality`, single-field).
    - `raw_observations`: `candidate_identifier` (NOT `candidate_value`); `candidate_manufacturer` is a top-level column; vendor-side organization detail lives at `notes.$.organization_address`.
    - `identifiers`: `confidence` (NOT `current_confidence`).
    - `schema_version` is the singular table name (NOT plural).

### Schema migration siblings bound to CP23 (§11 #11 discipline)

- `db/migrations/0020_source_type_enum_extension.sql` — sources.source_type CHECK enum 10 → 13 values
- `db/migrations/0021_procurement_vendor_canonical_normalized.sql` — procurement_records.vendor_canonical_normalized column + index
- `db/normalize_vendor.py` — pure normalization function (binding for backfill + cross-validation + tests)
- `db/backfill_0021.py` — companion backfill (43,483 rows populated; idempotent — re-running overwrites with same deterministic value)

### Composition with §11 hard rules

- **§11 #1 (no fabrication)** — strengthened. The 3 new source_type bands codify taxonomy that was previously silent-fallback to `regulatory`; the `vendor_canonical_normalized` column is a deterministic derivation of upstream verbatim values; no new identifier values minted; no source attributions altered.
- **§11 #7 (no promotion without provenance)** — composes naturally. The new bands are source-tier taxonomy only; identifier-row promotion still binds on identifiers.source_type + identifiers.source_url per §8.1. The vendor_canonical_normalized column is a cross-validation join key — the verbatim vendor_canonical_name remains the upstream provenance anchor.
- **§11 #8 (no confidence drift)** — unchanged. No confidence-column writes in either migration. Future P2-P6 admissions land under per-band §8.2 ceilings; the new bands do not lift any ceiling.
- **§11 #11 (amendment-log discipline)** — this CP23 entry IS the §11 #11 amendment-log pairing for the §4.2/§4.3/§8.2/§8.3 §-text additions + migrations 0020/0021 + DATA_DICTIONARY/METHODOLOGY downstream-consumer audit in the coordinated commit set. Bible HEAD bumps from [`c62dc1b`](https://github.com/kevwillow/argus-db/commit/c62dc1b) to the CP23 commit.
- **§11 #16 (Feist facts-only)** — composes orthogonally. CP23 license-posture register adds 4 new posture values that may surface in future §11 #16 promotion paths via the canonical `notes.upstream_license_posture` sentinel-key (CP21); license-posture vocabulary registration does not alter §11 #16 promotion semantics.

### Verification artifacts (paste-not-cite per S.7)

Run AND captured verbatim from live `db/argus.db` post-CP23 migration:

```
# 1. PRAGMA integrity_check
ok

# 2. schema_version top-3
(21, '0021_procurement_vendor_canonical_normalized', '2026-05-17 05:07:32')
(20, '0020_source_type_enum_extension',             '2026-05-17 05:07:17')
(19, '0019_identifier_types_round2',                '2026-05-14 17:24:59')

# 3. sources count
43        # unchanged; P2-P6 admit new rows

# 4. procurement_records count
43,483    # unchanged; P3+P4 ingest

# 5. procurement_records with non-empty vendor_canonical_normalized
43,483    # 100% backfill coverage

# 6. Sample 5 AXON spot-check
'AXON ENTERPRISE, INC.'  -> 'axon enterprise'   (×5 distinct rows)

# 7. CP23 grep coverage (BIBLE_AMENDMENTS.md)
≥ 8 references             # header + sub-amends + sequencing + verification block

# 8. CP23 sibling-commit landings
grep "CP23" PROJECT_BIBLE.md DATA_DICTIONARY.md METHODOLOGY.md   # non-zero

# 9. Test suite smoke
tests/test_export_lynceus.py  76/76 passing  (CP22 baseline preserved)
tests/ full suite             507/507 passing
```

### Sequencing post-acceptance

1. **CP23 ratifies at this commit.** Bible HEAD bumps from [`c62dc1b`](https://github.com/kevwillow/argus-db/commit/c62dc1b) → this CP23 commit. Schema version 19 → 21 (migrations 0020 + 0021). DB row counts unchanged in this CP (P2-P6 do the per-source admissions and ingest).
2. **P2 (UK Companies House) unblocks** for CEO ratification dispatch immediately upon CP23 close.
3. **P3 (SEC EDGAR) + P6 (CourtListener)** unblock to admit under the new `disclosure_filing` / `judicial_filing` bands respectively (replacing the silent fallback to `regulatory` from cycle-3 staging).
4. **P4 (USAspending deep-extension)** unblocks to ingest 2,555 net-new + 2,718 corroboration rows using `vendor_canonical_normalized` as the preferred join key (per §8.2 CP23 discipline).
5. **P5 (State SoS)** unblocks to admit DE/CA/TX rows with `notes.access_mode="operator_manual_only"`.
6. **No paired state-rotation commit needed.** PROJECT_STATE.md schema-version reference will refresh organically at the next post-P6 close.

### §12 Open Questions impact

Resolved by CP23:
- **`source_type` enum extension** (cycle-3 finding #2) — RESOLVED at Path B (judicial_filing + disclosure_filing + procurement_disclosure added; migration 0020 applied).
- **Vendor alias normalization approach** (cycle-3 finding #4) — RESOLVED at pre-compute column (vendor_canonical_normalized; migration 0021 applied; 43,483 rows backfilled at 0.9862 collapse ratio).
- **Per-table source_excerpt cap discovery for `behavioral_signatures` + `council_minutes_matters`** (cycle-3 finding #3) — RESOLVED at CP23 §4.3 table (behavioral_signatures has no source_excerpt column; council_minutes_matters carries the ≤200 cap; full per-table table is the canonical reference).
- **`access_mode` placement** (cycle-3 addendum §6 item 4) — RESOLVED at notes_json field (deferred to first-class column once value-set stabilizes per cycle-3 addendum §6 default).
- **License-posture vocabulary** (cycle-1 finding #1 extension) — RESOLVED at notes_json field with 4 new registered values (OGL-3.0, PUBLIC_DOMAIN, US_STATE_PUBLIC_RECORDS, CC0).
- **Disambiguation discipline placement** (cycle-4 finding #6) — RESOLVED at bake-into-runguide §4 match scoring (per CP23 §8.3 + cycle-4 default recommendation).

Surfaced by CP23 (queued for future CP candidacy as evidence accumulates):
- **`access_mode` first-class column migration** — gated on value-set stabilization (~1-2 more cycles of new-source evidence).
- **Adjacent §7.5 column shape-vs-format audit findings (CP22 surface)** carried forward unchanged.

New §12 questions opened: none.

### §11 #11 self-binding satisfied

This CP23 entry is the §11 #11 amendment-log pairing for the §4.2/§4.3/§8.2/§8.3 §-text additions + migration 0020 + migration 0021 + DATA_DICTIONARY + METHODOLOGY downstream-consumer audit in the coordinated commit set. Bible HEAD bumps from [`c62dc1b`](https://github.com/kevwillow/argus-db/commit/c62dc1b) to the CP23 commit landed alongside this entry. Schema-version bumps 19 → 21 (sources rebuild for source_type CHECK extension + procurement_records column addition).

═══════════════════════════════════════════════════════════════════════

## Correction Pass 24 — §11 #8 within-source re-extraction sub-rule + CP19 spirit-extension to `procurement_records` + "§5.2 +5 boost" citation hygiene

**Date:** 2026-05-17
**Source:** MAC-172 CEO ratification dispatch [`8db00702`](/MAC/issues/MAC-172#comment-8db00702-c710-49de-ac3f-d4d054d3dba8) (Read B canon ruling on §11 #8 strict reading of within-source re-extraction; partial ratify + 180-row rollback dispatch + CP24 bible amendment scope). CEO dispatch followed Validator partial-ratification surface at MAC-172 [`00329646`](/MAC/issues/MAC-172#comment-00329646-4455-4280-9f19-6c77fe35b701) (§11 #8 reconciliation question flagged Read A as-applied + Read B rollback path) post the MAC-172 P4 USAspending deep-extension ingest at HEAD [`4a3f6dd`](https://github.com/kevwillow/argus-db/commit/4a3f6dd) (5 disjoint write paths landed: sid=8 notes merge + 2,555 net-new INSERTs + 180 corroboration UPDATEs lifted 85→90 + 2 RG5 cross-corroboration markers + 264-row residue staged).
**Bible commit:** This entry + PROJECT_BIBLE.md §11 #8 three new sub-rules + 180-row rollback artifact (`db/validation/usaspending_deep_admission/rollback_lift.py`) + per-row `notes.confidence_history[]` audit on the 180 rolled-back rows. Coordinated commit per established CP19/CP20/CP21/CP23 bible-pairing pattern.
**Status:** Ratified at MAC-172 8db00702 2026-05-17. Rollback execution lands in the same commit-set; per-row audit-trail discipline takes effect immediately for the `procurement_records` table.
**Binds:** Validator (P4-class procurement-record corroboration UPDATEs after CP24: provenance merge only, no +5 lift unless the corroborating source is a genuinely independent collector from the originating source; per-row `notes.confidence_history[]` audit on every `procurement_records.confidence` UPDATE), CEO + DBArchitect (future runguides + dispatches + handoffs cite **`§8.3 + §11 #8`** for corroboration-lift rule, NOT "§5.2 +5 boost"), ExtractionWorker (future deeper-extraction runguides classify their output as "provenance enrichment cycle" vs "cross-source corroboration cycle" at runguide-§-text time; the two are not interchangeable under CP24 strict reading).

### Why this Correction Pass exists

MAC-172 P4 USAspending deep-extension ingest landed cleanly per dispatch — all five write paths verified DB-clean at HEAD `4a3f6dd`. The Validator's partial-ratification surface explicitly flagged the §11 #8 independence question on Step 3 (180-row corroboration UPDATE +5 lift, 85→90):

> Two USAspending API queries (v1.0.0 admission `20260504T154706Z` vs deep-extension session `20260516T...`) against the same upstream registry are not independent sources. They are the same source observed at two times with different filter windows. Re-extraction validates extraction-time fidelity, coverage breadth, and upstream-record persistence — but **not** the §11 #8 cardinal test that an independent collector observed the same fact via different methodology.

CEO ratified **Read B** (strict-independence reading): the +5 lift in §8.3 is precisely a test of independence-of-collection; re-querying the same API tests no such thing. The 180-row lift rolled back to confidence=85 with per-row audit. Provenance enrichment (the merged `notes.corroborations[]` evidence + `notes.corroboration_sessions[]` session tags) stays.

The CP needs to do three coupled things:

1. Codify the §11 #8 within-source-re-extraction carve-out as a sub-rule so future P-class dispatches don't recur the pattern (Validator partial-ratify catches it after-the-fact, but the cleaner discipline is upstream at dispatch-design time).
2. Extend CP19's row-level reclassification audit-trail discipline to `procurement_records` — CP19's literal wording is `identifiers`-scoped (binds the dedicated `source_reclassifications` audit table per migration 0017). The MAC-172 rollback demonstrated that `procurement_records` row-level confidence changes need the same forensic surface. Implementation pattern: row-local `notes.confidence_history[]` array, not a parallel audit table (cheaper at the ~46k-row scale; promotion to a `procurement_reclassifications` audit table deferred to a future CP if forensic-query patterns demand it).
3. Correct the citation hygiene drift: "§5.2 +5 boost" wording has carried forward through MAC-168 dispatch + HANDOFF + brief; PROJECT_BIBLE.md has no §5.2 (§5 is "Source Catalog" with Tier subsections only). The +5 formula is `min(99, max(originals) + 5)` from §8.3; the independence prerequisite is §11 #8 + §8.2. Future cites go to `§8.3 + §11 #8`.

### Corrections applied

1. **§11 #8 sub-rule (CP24, 2026-05-17) — within-source re-extraction.** Within-source re-extraction (same upstream registry queried at two times by the same or different extraction sessions) is **not** a "second independent source" for §8.3 lift purposes. Provenance enrichment via `notes.corroborations[]` + `notes.corroboration_sessions[]` is correct and stays; confidence does not lift. Lift requires a genuinely independent collector — different upstream registry, different methodology. The canonical cross-source case at MAC-172 is `id=86738` (SoundThinking × DHS USSS) where SEC EDGAR `ssti-20251231.htm` (independent collector: SEC's mandatory-disclosure registry, different methodology from USAspending's award-data API) corroborates the USAspending procurement record — that two-row RG5 cross-corroboration set is genuine §11 #8-compliant corroboration; the 180-row within-USAspending re-extraction set is not.

2. **§11 #8 sub-rule (CP24, 2026-05-17) — `procurement_records` row-level audit-trail (CP19 spirit-extension).** Row-local `notes.confidence_history[]` array convention: every `procurement_records.confidence` UPDATE (outside of initial INSERT) MUST append `{at_utc, from, to, rationale, dispatch, cp_anchor}` to the row's `notes.confidence_history[]` array in the same transaction as the UPDATE. The CP19 literal wording is `identifiers`-scoped; CP24 carries the same forensic answer ("when, why, by which dispatch") to `procurement_records` via the notes-array convention. Rationale for notes-array vs parallel-audit-table: at the current ~46k-row scale, row-local audit is cheaper than schema migration; if forensic-query patterns later demand it, the array promotes to a `procurement_reclassifications` table mirroring `source_reclassifications` shape — that is a future-CP decision, not a CP24-time obligation.

3. **§11 #8 sub-rule (CP24, 2026-05-17) — citation hygiene.** "§5.2 +5 boost" is a miscite of the bible (PROJECT_BIBLE.md has no §5.2). Future handoffs, runguides, and dispatch templates MUST cite **§8.3 + §11 #8** for the corroboration-lift rule. METHODOLOGY.md's internal "§5.2 Corroboration boost — multi-source dedup" heading is a METHODOLOGY-document-internal anchor (not a bible citation) and remains valid as a cross-document internal reference within METHODOLOGY's structure. The bible's canonical citations are §8.3 + §11 #8 across all forward dispatch/runguide/handoff prose.

### Rollback execution (MAC-172 180-row lift reversal)

Per the CEO dispatch's rollback spec, applied in a single transaction against `db/argus.db` immediately before this CP24 entry lands:

```python
UPDATE procurement_records
SET confidence = 85, notes = ...  # notes.confidence_history[] appended
WHERE id = ? AND confidence = 90  # PK-scoped per SAR-13 §6 discipline
```

Pre-rollback state: 46,038 rows; 45,858 @ conf=85; 180 @ conf=90.
Post-rollback state: 46,038 rows; 46,038 @ conf=85; 0 @ conf=90. ✓ matches CEO spec.

Per-row audit: each of the 180 rows now carries a `notes.confidence_history[0]` entry with `{from: 90, to: 85, dispatch: "MAC-172", cp_anchor: "CP24-pending"}` + `rationale` quoting the §11 #8 strict-reading carve-out. `notes.corroborations[]` (2,718 evidence rows total across 180 targets) + `notes.corroboration_sessions[]` (the `usaspending_deep_admission_2026_05_16` session tag) preserved verbatim — that's pure provenance enrichment and is correct under both reads.

Post-rollback idempotency confirmed:
- `rollback_lift --commit` re-run: 0 applied, 0 candidate rows (no rows remain at conf=90 to roll back). ✓
- `ingest --commit` re-run: all 5 original steps report `skipped_idempotent=proposed`; the rollback did not undo the evidence merge or re-trigger any Step-2/3 write logic. ✓

### Composition with §11 hard rules

- **§11 #1 (no fabrication)** — unchanged; CP24 strengthens provenance discipline by codifying when re-extraction-evidence enriches notes vs lifts confidence.
- **§11 #7 (no promotion without provenance)** — unchanged.
- **§11 #8 (no confidence drift upward without corroboration)** — extended with three new sub-rules per §3 above. The strict-independence reading is now codified at sub-rule level so future P-class dispatches don't recur the within-source-re-extraction pattern.
- **§11 #11 (amendment-log discipline)** — this CP24 entry IS the amendment-log pairing for the §11 #8 three new sub-rules in the coordinated commit. Bible HEAD bumps from the CP23 commit to the CP24 commit landed alongside this entry.
- **§11 #14 (procurement-only never exported to Lynceus)** — orthogonal; CP24 row-level changes on `procurement_records` would not have leaked to Lynceus exports regardless of the conf=85 vs conf=90 question. Export-side blast radius of the original MAC-172 lift was zero. CP24 is a bible-fidelity correction, not a downstream-consumer impact correction.

### Sequencing post-acceptance

1. **CP24 ratifies at this commit.** Bible HEAD bumps from the CP23 commit to this CP24 commit. Schema version unchanged (21 → 21; CP24 is §-text + row-local notes-pattern; no schema migration).
2. **MAC-172 close.** Validator reassigns to CEO with `in_review` upon the CP24 commit + rollback artifact landing; CEO closes to `done` after DB-verify post-rollback matches spec.
3. **Future P-class procurement-record dispatch discipline.** Any future deeper-extraction runguide against a previously-admitted source MUST classify its outputs as "provenance enrichment cycle" (within-source re-extraction; notes-only merge; no lift) vs "cross-source corroboration cycle" (genuinely independent collector; +5 lift via §8.3 within the §11 #8 + §8.2 ceiling). The classification surfaces in the runguide §-text and downstream HANDOFF.
4. **No paired state-rotation commit needed.** PROJECT_STATE.md will refresh organically at the next post-MAC-172 close.

### §12 Open Questions impact

Resolved by CP24:
- **MAC-172 §11 #8 within-source re-extraction question** (Read A vs Read B) — RESOLVED at Read B (strict-independence reading is canon).

Surfaced by CP24 (queued for future CP candidacy as evidence accumulates):
- **`procurement_reclassifications` audit table promotion** — gated on forensic-query pattern emergence at scale. Current notes-array convention is canonical until query patterns demand sub-millisecond cross-row reclassification queries.
- **Cross-source corroboration enumeration discipline** — at what `n` of independent-collector cross-source pairs does Argus introduce a structural `cross_source_corroborations` table parallel to the `notes.cross_source_corroboration[]` row-local convention? Current `n=2` (RG5 SEC EDGAR × USAspending at MAC-172 id=86738). Forward expectation: P3 (SEC EDGAR full admission) + P6 (CourtListener) ingestion may push `n` enough to warrant the table.

### §11 #11 self-binding satisfied

This CP24 entry is the §11 #11 amendment-log pairing for the §11 #8 three new sub-rules in the coordinated commit set. Bible HEAD bumps from the CP23 commit to the CP24 commit landed alongside this entry. Schema version unchanged (CP24 is §-text + row-local notes-pattern; no migration).

═══════════════════════════════════════════════════════════════════════

## Correction Pass 25 — `cross_source_corroboration_reversals[]` audit-trail + CP24 §12 n-recount supersession + within-source-FP discipline-evolution carry-forward

**Date:** 2026-05-17
**Source:** MAC-171 CEO ratification dispatch [`35ebb1bf`](/MAC/issues/MAC-171#comment-35ebb1bf-d99b-46d3-b31b-c15b2399dfa5) (adjudications on the §7.4 validation report's four §H open questions; Q3 specifically authorized CP25 as a standalone single-sub-rule amendment over folding into CP24 per §S.8 append-don't-mutate). Validator §7.4 walk-through at MAC-171 [`727ffcf0`](/MAC/issues/MAC-171#comment-727ffcf0-8875-4580-a4b8-908a06ee81cb) surfaced three stop-the-line items in the SEC EDGAR P3 dispatch: 3 of 9 named-customer extractions were §11 #1 false-positives (SSTI×ICE about competitors, SSTI×DHS Item 1A about Congressional IG-investigation request, Rekor×FBI about CJIS compliance), 1 was ambiguous under the 30-word fair-use cap (SSTI×FBI Item 1A), and the 2 "STRONG" cross-source corroborations on USAspending procurement rows (id=86738 + 86741/86743/86744/86745/86747) were therefore invalid (FP) or undetermined (ambiguous). MAC-172's pre-existing `notes.cross_source_corroboration[]` marker on id=86738 required reversal under §11 #1.
**Bible commit:** This entry only. Schema version unchanged (CP25 is §-text + row-local notes-pattern; no schema migration). DB writes that consume CP25 §1 (the MAC-171 reversal UPDATE on id=86738) land in the immediately-following MAC-171 ingest commit per CEO's ordered execution-sequencing (bible CP first, DB writes second, disk-stage third).
**Status:** Ratified at MAC-171 35ebb1bf 2026-05-17. CP25 §1 schema is the contract that the MAC-171 reversal UPDATE writes against; CP25 §2 documents the SEC × USAspending `n` recount that the same UPDATE produces; CP25 §3 captures the observation that within-source FP identification at validation time is now a recurring CEO-class adjudication pattern.
**Binds:** Validator (any future retraction of a `notes.cross_source_corroboration[]` marker under §11 #1 or §11 #8 review MUST append a parallel `notes.cross_source_corroboration_reversals[]` audit entry per CP25 §1 schema in the same transaction as the corroboration-array UPDATE); CEO + ExtractionWorker (future runguide §-text avoids the within-source FP failure mode by including the §11 #1 customer-relationship-vs-textual-mention disambiguation as a default §4 match-scoring step rather than punting to validator-time review).

### Why this Correction Pass exists

CP24 codified the within-source re-extraction strict-reading carve-out (Read B canon) and surfaced two open questions in §12 — including the cross-source corroboration enumeration discipline gated on the `n` of independent-collector pairs. CP24 logged `n=2` (RG5 SEC EDGAR × USAspending at MAC-172 id=86738) as the canonical first instance of genuinely-independent §11 #8-compliant corroboration.

MAC-171's §7.4 walk-through against the same RG5 yield invalidated `n=2` after-the-fact: the SSTI × DHS Item 1A "STRONG match" excerpt is a Congressional IG-investigation reference, not a customer-relationship attestation. The "STRONG" pairing was a text-pattern-match artifact (agency-name token co-occurs with vendor-token within the §1A risk-factor narrative) that didn't survive §11 #1 semantic review. The SSTI × FBI Item 1A excerpt is similarly weak — historical 2011 reference whose meaning is masked by the 30-word fair-use cap; CEO adjudicated as defer-to-operator-review rather than re-fetch fuller filing context.

CP25 needs to do three coupled things:

1. Codify the `notes.cross_source_corroboration_reversals[]` audit-trail schema so the MAC-171 reversal UPDATE on id=86738 has a canonical contract to write against (parallel to CP24 sub-rule (b)'s `notes.confidence_history[]` pattern for procurement_records confidence changes — same forensic answer shape).
2. Document the CP24 §12 `n` supersession explicitly. CP24's surfacing block said "Current n=2 (RG5 SEC EDGAR × USAspending at MAC-172 id=86738)"; post-MAC-171 reversal, the canonical `n` for SEC EDGAR × USAspending drops to 0. The future-expectation prose ("P3 + P6 may push n enough to warrant the table") narrows: P6 CourtListener is now the only net-new RG5 candidate that could reach the table-creation trigger threshold.
3. Capture the within-source-FP-identification carry-forward observation. Within-source re-extraction was CP24's failure mode; within-source false-positive-identification (text-pattern match without semantic-relationship validation) is a parallel-but-distinct failure mode that MAC-172 had RG5 §3.5 + MAC-171 §C as two consecutive instances of. Flag as discipline-evolution candidate for future CP if frequency warrants a dedicated §11 sub-rule (matching CP24's path from "carve-out observed" → "sub-rule codified").

### Corrections applied

1. **§11 #8 sub-rule (CP25, 2026-05-17) — `cross_source_corroboration_reversals[]` audit-trail.** When a `notes.cross_source_corroboration[]` marker is retracted post-validation under §11 #1 or §11 #8 review, the retraction MUST append a parallel `notes.cross_source_corroboration_reversals[]` array entry in the same transaction as the corroboration-array UPDATE. Schema for each reversal entry (5 required keys):

   ```json
   {
     "at_utc": "<ISO-8601 timestamp of the reversal UPDATE>",
     "marker_key": "<the original cross_source_corroboration[] entry's marker_key, copied verbatim>",
     "rationale": "<short prose citing the §11 hard rule that triggered the retraction + the §-anchor evidence>",
     "dispatch": "<MAC-NNN issue identifier of the retracting dispatch>",
     "cp_anchor": "<canonical CP citation, e.g. 'CP25 §1'>"
   }
   ```

   The original `notes.cross_source_corroboration[]` entry is REMOVED from the array (not soft-deleted; the reversal-array IS the audit-trail). The marker_key copy preserves forensic recoverability — operators can grep the reversal-array for any historical marker without scanning the live corroboration-array. Composition with CP24 sub-rule (b): if the retracted corroboration had previously triggered a §8.3 +5 lift (and thus a `notes.confidence_history[]` UPDATE), the reversal-array entry composes with a separate `notes.confidence_history[]` rollback entry per CP24 sub-rule (b) — same transaction, two parallel audit-trail appends.

2. **CP24 §12 Open Questions supersession (CP25 §2, 2026-05-17) — cross-source corroboration enumeration recount.** CP24's surfacing block recorded `n=2` for the SEC EDGAR × USAspending cross-source pair count (the two RG5 "STRONG" pairings flagged in `extraction_outputs/sec_edgar_admission/cross_validation_findings_data.json`). Post-MAC-171 §C semantic review: SSTI × DHS is a §11 #1 false-positive (reverted at this dispatch via CP25 §1); SSTI × FBI is operator-review-deferred (no DB write either way pending fuller filing context). The canonical `n` for SEC EDGAR × USAspending drops from 2 → **0**. Forward expectation prose updates: P6 CourtListener is the only remaining RG5 candidate that could reach the `cross_source_attestations` table threshold (n≥1 first-instance, n≥2 table-creation trigger). The CP24 §12 prose itself remains untouched per §S.8 append-don't-mutate; CP25 §2 IS the supersession record.

3. **§11 carry-forward observation (CP25 §3, 2026-05-17) — within-source-FP discipline evolution.** Two consecutive validator-side adjudications now show within-source false-positive identification at validation time as a recurring CEO-class pattern: MAC-172 RG5 §3.5 (the original handoff flagged 7 OPERATOR-REVIEW pairs as not-corroborated-by-USAspending — implicitly an FP-suspect cohort) + MAC-171 §C (3 of 9 named-customer extractions were §11 #1 FPs on semantic review). Within-source FP identification is distinct from CP24's within-source re-extraction failure mode: re-extraction lifts conf without independent collection (procedural); FP-identification mis-attributes a relationship without semantic validation (substantive). CP25 §3 flags the pattern as a discipline-evolution candidate. Future-CP threshold: if a third comparable instance surfaces (validator catches FP-attribution after-the-fact at promotion-time), a dedicated §11 sub-rule codifying "text-pattern match + semantic-relationship-validation as a §4 match-scoring default" becomes the appropriate codification — matching CP24's evolution path from "carve-out observed in one dispatch" → "sub-rule codified after corrective ratification."

### Reversal execution (MAC-171 id=86738 cross_source_corroboration retraction)

Per CEO authorization at MAC-171 35ebb1bf, applied in the same transaction as the MAC-171 P3 ingest against `db/argus.db` immediately AFTER this CP25 entry lands:

```python
UPDATE procurement_records
SET notes = ...  # cross_source_corroboration[] entry removed + reversals[] appended
WHERE id = 86738  # PK-scoped per SAR-13 §6 discipline
```

Pre-reversal state: `notes.cross_source_corroboration[]` contains 1 entry (`marker_key="rg5_sec_edgar::…/ssti-20251231.htm::HSSS0116C0028"`, MAC-172 ratified).
Post-reversal state: `notes.cross_source_corroboration[]` empty (or key absent); `notes.cross_source_corroboration_reversals[]` contains 1 entry with `rationale="§11 #1 FP — SEC Item 1A excerpt describes Congressional IG-investigation request, not a DHS customer relationship"`, `dispatch="MAC-171"`, `cp_anchor="CP25 §1"`. Confidence unchanged at 85 (MAC-172 never applied the §8.3 lift to id=86738 because RG5 §3.1 didn't propose one for the cross-source marker — only for the corroborated USAspending row's audit-trail, which was rolled back at CP24; no CP24 sub-rule (b) `confidence_history[]` companion entry is needed at CP25 §1).

### Composition with §11 hard rules

- **§11 #1 (no fabrication)** — strengthened. CP25 §1 makes corroboration-marker retraction a first-class forensic surface; CP25 §3 flags the discipline-evolution path for catching FP-attribution at extraction time rather than validator time.
- **§11 #7 (no promotion without provenance)** — unchanged; CP25 §1 is provenance-retraction discipline, not provenance-relaxation.
- **§11 #8 (no confidence drift upward without corroboration)** — composed with CP24 sub-rules (a)+(b)+(c). CP25 §1 is the retraction-audit complement to CP24 sub-rule (b)'s lift-audit pattern. The two are parallel: lift-audit answers "when did confidence go up and why?"; retraction-audit answers "when was a corroboration marker pulled and why?". Same forensic shape, different trigger.
- **§11 #11 (amendment-log discipline)** — this CP25 entry IS the amendment-log pairing for the §11 #8 sub-rule (CP25 §1) + §12 Open Questions supersession (CP25 §2) + carry-forward observation (CP25 §3) in the coordinated commit. Bible HEAD bumps from the CP24 commit to the CP25 commit landed alongside this entry.
- **§11 #14 (procurement-only never exported to Lynceus)** — orthogonal; CP25 row-local changes on `procurement_records` would not have leaked to Lynceus exports regardless. CP25 is a bible-fidelity correction, not a downstream-consumer impact correction.

### Sequencing post-acceptance

1. **CP25 ratifies at this commit.** Bible HEAD bumps from the CP24 commit to this CP25 commit. Schema version unchanged (21 → 21; CP25 is §-text + row-local notes-pattern; no schema migration).
2. **MAC-171 ingest commit lands next.** The id=86738 reversal UPDATE consumes the CP25 §1 schema as its write contract. Same commit also carries the 1 source INSERT + 21 manufacturer-enrichment UPSERT + 5 net-new procurement_records + disk-stage operator-review files per CEO's authorized write-set.
3. **MAC-171 close.** Validator reassigns to CEO with `in_review` after the CP25 commit + MAC-171 ingest commit land; close comment carries the paste-not-cite state-row preamble per [feedback_dispatch_preamble_live_state_verification](/MAC/agents/ceo).
4. **No paired state-rotation commit needed.** PROJECT_STATE.md will refresh organically at the next post-MAC-171 close (CP25 + MAC-171 land together as the coordinated end-state).

### §12 Open Questions impact

Resolved by CP25:
- **`cross_source_corroboration_reversals[]` audit-trail codification** — RESOLVED at CP25 §1; the MAC-171 id=86738 UPDATE is the first consumer.

Updated by CP25:
- **Cross-source corroboration enumeration discipline** (CP24 §12) — `n` recount: SEC EDGAR × USAspending drops 2 → 0. P6 CourtListener remains the active n-candidate; table-creation trigger threshold unchanged (n≥2).

Surfaced by CP25 (queued for future CP candidacy as evidence accumulates):
- **Within-source FP identification as a dedicated §11 sub-rule** — gated on a third comparable instance per CP25 §3 carry-forward criterion. Current evidence: 2 instances (MAC-172 RG5 §3.5 implicit cohort + MAC-171 §C explicit walk-through).

### §11 #11 self-binding satisfied

This CP25 entry is the §11 #11 amendment-log pairing for the §11 #8 sub-rule + §12 Open Questions supersession + carry-forward observation in the coordinated commit set. Bible HEAD bumps from the CP24 commit to the CP25 commit landed alongside this entry. Schema version unchanged (CP25 is §-text + row-local notes-pattern; no migration).

═══════════════════════════════════════════════════════════════════════

## Correction Pass 26 — SAM.gov cycle-5 day-0 partial fold + `cycle_completion_state` notes_json convention + within-source-FP discipline n=4 codification

**Date:** 2026-05-17
**Source:** SAM.gov cycle-5 day-0 partial extraction halt at 2026-05-17T14:10:40Z per `~/argus-internal/extraction_outputs/sam_gov_admission/STOP_THE_LINE_rate_ceiling.md`. Seven patch findings accumulated against the v1.1.0 runguide narrative + the CEO-additive §11 carry-forward n-recount surfacing two NEW within-source FP classes at MAC-174 P6 (CourtListener) ratification (BRINC `rico_co_defendant_not_customer_relationship` + BRINC `court_filing_fee_not_contract_value`), bringing cumulative within-source-FP-identification instance count to n=4 ≥ the CP25 §3 carry-forward threshold (n=3 for "dedicated §11 sub-rule codification"). MAC-175 dispatch authorized this CP as the fold target before the SAM.gov sid=50 ingest commit per §S.8 ordered-commit-pair precedent (CP25 + MAC-171 P3, CP24 + MAC-172 rollback).
**Bible commit:** This entry only. Schema version unchanged (CP26 is §-text + row-local notes-pattern; no schema migration). DB writes that consume CP26 — the SAM.gov sid=50 admission with `cycle_completion_state="partial_pre_day1"` (the first consumer of the new convention) + the 9,623-row cross-source corroboration UPDATE batch (Vigilant 56 + Motorola 9,545 + Genetec 22) + the Genetec manufacturer-enrichment merge — land in the immediately-following MAC-175 ingest commit.
**Status:** Ratified at MAC-175 dispatch 2026-05-17. CP26 §3 (`cycle_completion_state` vocabulary) is the contract that the SAM.gov sid=50 INSERT writes against; CP26 §1–§7 capture the seven cycle-5 runguide-correction findings; CP26 §8 codifies the within-source-FP discipline as a dedicated §11 sub-rule per n=4 ≥ threshold supersession of CP25 §3 open-status.
**Binds:** Validator (any future source-admission INSERT whose extraction halted mid-cycle MUST carry `notes.cycle_completion_state` + companion fields per §3 vocabulary; any cross-source corroboration UPDATE batch MUST honor the per-row scoping discipline + audit-trail in `procurement_records.notes` per CP24 sub-rule (b) + CP25 §1 composition); CEO + ExtractionWorker (any future SAM.gov-class API source runguide MUST acknowledge the §2 empirical-ceiling + §3 no-rate-limit-headers + §6 single-token-alias-fanout brittleness as default extraction-runguide §-text discipline anchors); DBArchitect (any future schema-evolution discussion of a structural `cycle_state` column on `sources` is deferred until value-set stabilizes per §3 backward-compat precedent matching CP23 access_mode).

### Why this Correction Pass exists

SAM.gov cycle-5 launched against the v1.1.0 runguide narrative on 2026-05-17 with seven hidden assumptions whose violation halted the run at day-0 after 11 API calls (5 §2.6 endpoint-shape probes + 5 §4 successful vendor queries + 1 §4 429 halt). Five surfaced via mid-run extraction failures; one (single-token alias fanout brittleness) surfaced via the `weak_matches.json` Flock Safety → "Funny Flock Farms LLC" surprise hit; one (snapshot-freshness pre-flight) is a forward-looking discipline anchor for cycle-N≥6 kickoffs already informally agreed but not yet bible-canon. The seven findings need amendment-log codification per §11 #11 so v1.1.0 doc-sweep narrative can reference them by canonical CP citation rather than transient STOP_THE_LINE-doc citations.

In parallel, MAC-174 P6 (CourtListener V4 source admission) ratification surfaced two NEW within-source FP classes at sources.id=48 (BRINC `rico_co_defendant_not_customer_relationship` — 57-co-defendant RICO pro-se suit pattern where vendor co-presence ≠ vendor-customer relationship; BRINC `court_filing_fee_not_contract_value` — $405 amount = 28 USC §1914 filing fee, not vendor contract amount). These compose with the prior CP25 §3 instances (MAC-172 RG5 §3.5 implicit + MAC-171 §C explicit) to push the cumulative within-source FP-identification instance count to n=4. CP25 §3 set the codification threshold at n=3 for "dedicated §11 sub-rule codifying text-pattern match + semantic-relationship validation as a §4 match-scoring default." With n=4 ≥ 3, the threshold is satisfied and CP26 §8 codifies the sub-rule directly per the CP25 §3 prose's stated evolution path.

CP26 also introduces the `cycle_completion_state` notes_json convention as a new discipline anchor: partial-cycle source admissions are first-class explicit states rather than implicit "ingested but incomplete" surfaces. The SAM.gov sid=50 admission is the first consumer (`partial_pre_day1`) and exercises the full companion-field shape (`next_cycle_dispatch_scheduled_for_utc`, `next_cycle_dispatch_runguide_path`, `partial_yield_metrics_at_admission`).

### Corrections applied

1. **UEI correction discipline (CP26 §1, 2026-05-17) — runguide §2.6 probe-template UEI freshness.** v1.1.0 runguide §2.6 cited `ZQ4FBV4F1J88` as the Lockheed Martin probe-template UEI. Empirical SAM.gov query returned 0 records; Lockheed's current registration-resolved UEI is `KM99JJBNQ9M5` (registered 2025-10-23). Forward discipline: §2.6 probe templates MUST cite registration-resolved-as-of-runguide-authoring UEIs, and the runguide §-text MUST carry a freshness disclaimer noting that UEI values can rotate at re-registration. Snapshot freshness pre-flight (§7 below) should refresh the probe UEI before script kickoff for cycle-N≥6.

2. **SAM.gov rate ceiling (CP26 §2, 2026-05-17) — non-Federal individual account class ceiling.** Empirical observation at cycle-5: 5 §2.6 probes + 5 §4 successful queries + 1 §4 429 = 11 requests at first 429. Reset header was `Retry-After: <next UTC-midnight HTTP-date>`, not a delta-seconds value. The likely ceiling is **10 requests per UTC day for non-Federal individual accounts** — matching the lower-bound the operator pre-flagged ("10 requests/day non-Federal vs 1,000/day Federal" caveat). The v1.1.0 runguide's "1,000 req/hour authenticated" assumption is wrong for this account class by ~100×. Forward discipline: any SAM.gov-class API runguide MUST (a) carry the per-account-class empirical ceiling explicitly in §-text, (b) prefer a multi-day-pacing extraction shape over single-session for non-Federal accounts, (c) name the operator-tier-upgrade alternative explicitly so the operator can choose pacing vs key-tier-upgrade before dispatch.

3. **No proactive rate-limit headers (CP26 §3, 2026-05-17) — empirical-ceiling discovery discipline.** SAM.gov v3/entities responses expose `Retry-After` only on 429; no `X-RateLimit-Remaining` / `X-RateLimit-Limit` headers on 200 responses. Forward discipline: any extraction runguide for an API source MUST treat "no rate-limit-introspection headers" as a default-assume rather than default-trust; probe-to-discover ceiling is the safe pattern; documented-ceiling-trust requires explicit empirical validation in a low-stakes probe run before a real extraction.

4. **Operator-manual-queue file format clarification (CP26 §4, 2026-05-17) — consolidated-file convention.** v1.1.0 runguide §3.2 cited per-state breakdown files (`de_candidates.json` / `ca_candidates.json` / `tx_candidates.json`) at `extraction_outputs/us_state_sos_admission/operator_manual_queue/`. The actual on-disk shape from MAC-173 P5 (state SoS admission) is a single consolidated file `extraction_outputs/us_state_sos_admission/operator_manual_queue.json` with a top-level `queue` key. Forward discipline: operator-manual queues are CONSOLIDATED (one file per source admission, not per-jurisdiction breakdown); the consolidated convention composes with the `notes.access_mode="operator_manual_only"` CP23 access-mode value for source-tier surfacing.

5. **NAICS code revision drift (CP26 §5, 2026-05-17) — surveillance-adjacent NAICS list freshness.** The 2022 NAICS revision renumbered Software Publishers from `511210` → `513210`. Genetec's primary NAICS at SAM.gov is `513210`. v1.1.0 runguide §4.5 surveillance-adjacent NAICS list cited the pre-2022 `511210`. Forward discipline: surveillance-adjacent NAICS lists MUST cite the current code-revision; cycle-N runguides citing NAICS codes MUST carry a "live as of NAICS-revision YYYY" disclaimer. SAM.gov NAICS-list adjacency-flagging (`naics_surveillance_adjacency_flagged`) should compose code revisions across versions (e.g., flag both `511210` AND `513210` until pre-2022 references are fully aged out).

6. **Single-token alias fanout brittleness (CP26 §6, 2026-05-17) — alias-as-whole-word match discipline.** Cycle-5 ran a single-token alias fanout for Flock Safety (`aliases[0]='Flock'`) and matched *"Funny Flock Farms LLC"* — a substring-token-match that the operator surfaced as a normalization disagreement (input_normalized="flock safety" vs sam_gov_normalized="funny flock farms"). The match was correctly graded WEAK but exposed a structural brittleness. Forward discipline: alias-fanout for STRONG promotion MUST require either (a) alias-length ≥4 characters with whole-word containment in the candidate's normalized legal name, or (b) full canonical-name match (no fanout). Single-token short-alias fanouts (e.g., 4-letter or less) are permitted only for WEAK staging — never STRONG. The Flock Safety WEAK match is staged to operator-review-queue with `notes.brittle_alias_match=true` carrying this discipline forward.

7. **Snapshot-freshness pre-flight (CP26 §7, 2026-05-17) — cycle-N≥6 kickoff discipline.** Cycle-5's preconditions were partly stale (§3.2 path drift) without the runguide-defined pre-flight catching it; the validator caught it mid-run by inspecting `n=0` for the holds loop. Forward discipline: cycle-N≥6 kickoff templates MUST include a snapshot-freshness pre-flight step that refreshes held-input snapshots (per-state breakdown files, vendor-fanout target lists, probe-template UEIs) against the on-disk consolidated source before script invocation. The pre-flight surfaces as a §0 read-only verification phase in the runguide §-text and emits a "snapshot freshness verified at <UTC-timestamp>" emit-line at kickoff.

8. **§11 #8 sub-rule (CP26 §8, 2026-05-17) — text-pattern match + semantic-relationship validation as default §4 match-scoring step.** Per CP25 §3 carry-forward threshold (n=3 for dedicated §11 sub-rule codification): cumulative within-source FP-identification instance count is now n=4 with MAC-174 P6 surfacing TWO new FP-classes at `sources.id=48.notes.candidate_findings_for_future_cp_or_sar[]`:
   - `rico_co_defendant_not_customer_relationship` (BRINC pattern — 57+ co-defendants in pro-se RICO suit; vendor co-presence ≠ vendor-customer relationship)
   - `court_filing_fee_not_contract_value` (BRINC $405 = 28 USC §1914 statutory filing fee, not vendor contract value)

   Combined with prior CP25 §3 instances (MAC-172 RG5 §3.5 implicit cohort + MAC-171 §C explicit walk-through), cumulative n=4 ≥ codification threshold. Per CP25 §3 stated evolution path ("dedicated §11 sub-rule codifying 'text-pattern match + semantic-relationship validation as a §4 match-scoring default' becomes the appropriate codification"), CP26 §8 codifies the sub-rule directly:

   **Sub-rule text (CP26 §8):** Any match-scoring §4 step against a textual source (regulatory filings, judicial filings, news/forum, FOIA documents) MUST validate semantic relationship between the vendor-token and the surrounding-context anchor (customer, contractor, vendor, etc.) BEFORE promoting the match. Text-pattern match (vendor-token co-occurs with agency-token within N-word context) is necessary but NOT sufficient for STRONG promotion. The semantic-validation step MUST be a default §4 sub-step in the runguide §-text — punting to validator-time review is no longer the canonical pattern. Documented FP classes at codification (non-exhaustive; for runguide §-text hints):
   - Risk-factor-narrative co-occurrence (SSTI×DHS Item 1A: "Members of Congress requested IG investigation" — Congressional reference, not customer)
   - Compliance-attestation co-occurrence (Rekor×FBI CJIS-compliance certification — regulatory compliance reference, not customer)
   - Competitor-data-sharing co-occurrence (SSTI×ICE: about competitors' data-sharing practices, not own customer relationship)
   - Co-defendant co-presence (BRINC pattern: 57-co-defendant pro-se RICO suit — vendor named as defendant, not customer)
   - Statutory-amount co-occurrence (BRINC $405 = 28 USC §1914 statutory filing fee, not vendor contract value)

   The runguide §-text contract for any future textual-source extraction MUST cite CP26 §8 as the semantic-validation discipline anchor.

9. **`cycle_completion_state` notes_json convention (CP26 §9, 2026-05-17) — partial-cycle source admission explicit state.** New `sources.notes.cycle_completion_state` field with controlled vocabulary:

   | Value | Meaning |
   |---|---|
   | (field absent) | source is complete; canonical state (default backward-compat reading) |
   | `partial_pre_day1` | source admission landed before its first full data sweep completed; explicit incomplete-state flag pending next-cycle dispatch |
   | `partial_pacing_in_flight` | source is mid-multi-day pacing run; additional data expected in subsequent cycles |
   | `partial_pacing_exhausted` | source's multi-day pacing terminated short of completion; deferred to future cycle |

   Composition with CP23 `access_mode`: orthogonal — partial completion is a temporal state, access_mode is a mechanism state. The SAM.gov sid=50 case is `access_mode="automated_api"` + `cycle_completion_state="partial_pre_day1"`.

   Companion notes_json fields REQUIRED when `cycle_completion_state` is non-absent:
   - `next_cycle_dispatch_scheduled_for_utc` — ISO-8601 UTC timestamp of next planned dispatch
   - `next_cycle_dispatch_runguide_path` — relative path to the dispatch artifact
   - `partial_yield_metrics_at_admission` — JSON snapshot of yield-at-admission for audit comparison post-completion

   First-class column promotion deferred to a future CP once the value-set stabilizes (per cycle-3 addendum §6 default recommendation matching CP23 `access_mode` precedent). Absent-`cycle_completion_state` is equivalent to "complete" per backward compat — no migration of pre-CP26 sources required.

### Composition with §11 hard rules

- **§11 #1 (no fabrication)** — strengthened. CP26 §8 codifies the semantic-validation default that catches text-pattern-match FP-attribution at extraction time rather than validator time; reduces validator-time FP-catching dependency over time.
- **§11 #7 (no promotion without provenance)** — unchanged; CP26 §3+§4+§9 are provenance-discipline strengthening (forensic-recoverability of partial-cycle state + access-mode + per-row admission shape), not provenance-relaxation.
- **§11 #8 (no confidence drift upward without corroboration)** — composed with CP24 sub-rules (a)+(b)+(c) and CP25 §1. CP26 §8 is the extraction-time pre-promotion discipline complement to CP24 sub-rule (b)'s lift-audit + CP25 §1's retraction-audit patterns. Same forensic shape (text-pattern vs semantic-relationship): different lifecycle stage (extraction vs validator vs post-validator).
- **§11 #11 (amendment-log discipline)** — this CP26 entry IS the amendment-log pairing for the §11 #8 sub-rule (CP26 §8) + the seven cycle-5 runguide corrections (CP26 §1-§7) + the `cycle_completion_state` convention (CP26 §9) in the coordinated commit set. Bible HEAD bumps from the CP25 commit to the CP26 commit landed alongside this entry. The MAC-175 SAM.gov ingest commit immediately follows.
- **§11 #14 (procurement-only never exported to Lynceus)** — orthogonal; CP26 row-local changes on `procurement_records` (corroboration UPDATEs) would not leak to Lynceus exports regardless. CP26 is a bible-fidelity + extraction-discipline correction, not a downstream-consumer impact correction.

### Sequencing post-acceptance

1. **CP26 ratifies at this commit.** Bible HEAD bumps from the CP25 commit to this CP26 commit. Schema version unchanged (21 → 21; CP26 is §-text + row-local notes-pattern; no schema migration).
2. **MAC-175 ingest commit lands next.** The sid=50 SAM.gov INSERT consumes CP26 §9 as its `cycle_completion_state` write contract. Same commit also carries the 1 manufacturer enrichment merge (Genetec mfg_id=4) + 3 cross-source corroboration UPDATE batches (Vigilant 56 + Motorola 9,545 + Genetec 22, +5 lift each per §8.3 cross-source-not-within-source per CP24 §11 #8) + 2 WEAK + 1 PROBE staged to operator-review-queue + 1 normalization-disagreement audit-append per the dispatch §5 write actions.
3. **MAC-175 close.** Validator reassigns to CEO with `in_review` after the CP26 commit + MAC-175 ingest commit land; close comment carries the paste-not-cite state-row preamble per §S.7 dispatch-preamble live-state verification.
4. **Downstream-consumer absorption.** Sibling commits to PROJECT_BIBLE §4 (notes_json conventions block adds `cycle_completion_state` + companion fields) + DATA_DICTIONARY §4.3 (sources.notes vocabulary expansion to include the new `cycle_completion_state` controlled-vocabulary) per S.6.1 worker-autonomous absorption discipline. Both sibling commits land in the same coordinated commit set with the CP26 bible commit (Validator owns the sibling absorption for §-text-only CPs per DBArchitect-style discipline analogue).
5. **No paired state-rotation commit needed.** PROJECT_STATE.md will refresh organically at the next post-MAC-175 close.

### §12 Open Questions impact

Resolved by CP26:
- **Within-source FP identification as a dedicated §11 sub-rule** (CP25 §3 carry-forward) — RESOLVED at CP26 §8; n=4 ≥ threshold n=3 satisfies the codification trigger per CP25 §3 stated evolution path. Future textual-source runguides cite CP26 §8 as the semantic-validation discipline anchor.

Surfaced by CP26 (queued for future CP candidacy as evidence accumulates):
- **Partial-cycle source-admission discipline first-class-column promotion** — gated on `cycle_completion_state` value-set stabilization. Current vocabulary (3 controlled values + absent) is `notes_json`-only per backward-compat precedent matching CP23 `access_mode`. First-class column promotion deferred until at least 2 distinct sources have used non-absent `cycle_completion_state` (precedent: CP23 access_mode promotion is similarly deferred until value-set stabilizes). The SAM.gov sid=50 admission is the first consumer.
- **Empirical-ceiling-probe runguide template** — CP26 §3's "probe-to-discover ceiling" forward discipline may warrant a dedicated runguide-template §-text fragment that every API-source admission runguide inherits. Discipline-evolution candidate; not codified at CP26.

### §11 #11 self-binding satisfied

This CP26 entry is the §11 #11 amendment-log pairing for the §11 #8 sub-rule (CP26 §8) + the seven cycle-5 runguide corrections (CP26 §1-§7) + the `cycle_completion_state` convention (CP26 §9) in the coordinated commit set. Bible HEAD bumps from the CP25 commit to the CP26 commit landed alongside this entry. Schema version unchanged (CP26 is §-text + row-local notes-pattern; no migration).

═══════════════════════════════════════════════════════════════════════

## Correction Pass 27 — §2.4 Empirical-Premise Verification Precondition

**Date:** 2026-05-18
**Source:** Cycle-7 autonomous overnight wave (2026-05-17→2026-05-18) per [MAC-177](/MAC/issues/MAC-177) parent + [MAC-178](/MAC/issues/MAC-178) integration. Six concrete failure-mode anchors surfaced inside a single 8-hour window — 5 external web-scrape runguides ([MAC-102](/MAC/issues/MAC-102) ISED Canada REL, [MAC-103](/MAC/issues/MAC-103) BT SIG Qualified Designs, [MAC-105](/MAC/issues/MAC-105) USPTO Patent Text Mining, [MAC-107](/MAC/issues/MAC-107) GitHub Code Search, [MAC-110](/MAC/issues/MAC-110) Ofcom UK) all halted at empirically-falsified load-bearing premises, and 1 internal extraction patch ([MAC-101](/MAC/issues/MAC-101) PC1.7 `application_id`-vs-`grant_id` identifier-field-name miscall) caught the same class of failure mid-flight. The empirical density alone is the codification trigger.
**Bible commit:** This entry + the §2.4 insert into `PROJECT_BIBLE.md` (placed after §2.3 A Note on Ambition; before §3 Architecture). Schema version unchanged (22 → 22; CP27 is §-text only — process amendment, no migration, no notes_json convention).
**Status:** Ratified at MAC-178 dispatch 2026-05-18 per CEO disposition [3029e567](/MAC/issues/MAC-178#comment-3029e567-c4e7-4dac-aff8-cd03b8c9a48a) (response to Validator draft [60301e62](/MAC/issues/MAC-178#comment-60301e62-da2e-4007-b975-b40caaf2c923)). Draft ratified verbatim — no refinements applied to the §2.4 text or the 10-runguide downstream-consumer audit. The §4.4 DROPPED-class disposition surface raised at MAC-178 Priority 8 is **explicitly deferred** to a separate future CP cycle (candidate slot: CP28); it is NOT part of CP27.
**Binds:** CEO (any future runguide dispatch authorization MUST verify §3.0 verification-probe completion CLEAN POSITIVE before signing off on §3.1 bulk-extraction fire); Validator + ExtractionWorker (any pre-existing runguide being re-dispatched MUST re-run §3.0 probes at re-dispatch time regardless of prior calibration); Researcher (any new runguide drafted post-CP27 MUST ship a §3.0 verification-probe section as a published structural slot before any §3.1 dispatch fires).

### Why this Correction Pass exists

The cycle-7 autonomous wave (2026-05-17→2026-05-18, ~8 hours of autonomous extraction firing) hit six load-bearing-premise failures across five separate web-scrape runguides and one internal extraction pass. Each failure mode is independently structural — none are coincidental drift; each represents a class of premise that any runguide can carry. The clustering is the codification signal:

| Runguide / pass | Failure mode | Falsified load-bearing premise |
|---|---|---|
| [MAC-102](/MAC/issues/MAC-102) ISED Canada REL | Oracle PL/SQL gateway → Spring Web Flow migration | URL template + HTTP method + session model (form-flow `execution=...` token) |
| [MAC-103](/MAC/issues/MAC-103) BT SIG Qualified Designs | Launch Studio domain rename + auth-gate added | URL domain (`qualification.bluetooth.com` 301) + auth posture (`Layers` endpoint 401) + response-shape (Vue SPA vs server-rendered) |
| [MAC-105](/MAC/issues/MAC-105) USPTO PatFT | PatFT decommissioned ~2022; NXDOMAIN | endpoint existence (URL host no longer resolves) |
| [MAC-107](/MAC/issues/MAC-107) GitHub Code Search | Auth-required for ALL queries since 2022 GA | auth posture (unauthenticated 401, was 200) |
| [MAC-110](/MAC/issues/MAC-110) Ofcom UK | Cloudflare managed challenge JS gate added | request-shape (curl-able → JS-required) |
| [MAC-101](/MAC/issues/MAC-101) PC1.7 (fccid.io) | `application_id` field assumption empirically wrong | identifier-field name (Grant ID is the actual identifier, not Application ID) |

5 separate external runguides + 1 internal patch = 6 concrete failure-mode anchors across 5 organizations in a single autonomous-wave window. The discipline the wave kept evolving in real-time — runguide patch cycles + a mid-flight extraction-script fix — is the canonical bible expression of the discipline going forward. CP27 codifies it as a precondition on §3.1 dispatch.

### Corrections applied

1. **§2.4 (new) — Empirical-Premise Verification Precondition.** New subsection in `PROJECT_BIBLE.md` after §2.3 A Note on Ambition, before §3 Architecture. Verbatim §2.4 text:

   > **§2.4 — Empirical-Premise Verification Precondition (CP27).** Before any runguide's §3.1 bulk dispatch fires, the runguide's load-bearing premises MUST be empirically verified against the live source within the same calendar day as dispatch (24-hour staleness ceiling). Load-bearing premises include: URL templates, HTML/JSON response structure assumptions, authentication posture, rate-limit posture, identifier-pattern presence in the response surface, response-shape stability under documented filter / search parameter combinations, and the canonical identifier-field name (e.g. `application_id` vs `grant_id`) the §4 extraction expects.
   >
   > Verification probes are documented in **§3.0 of the runguide** (per the MAC-101 PC1.7 pattern, which was the first canonical instance of a §3.0 verification probe section). §3.0 probes must complete with one of two clean outcomes before §3.1 fires:
   > - **CLEAN POSITIVE** — every load-bearing premise holds; §3.1 dispatch authorized.
   > - **CLEAN NEGATIVE** — at least one load-bearing premise is empirically false; §3.1 dispatch **halted** under §6 #5; runguide returns to drafting per the patch-cycle convention; **CEO disposition required** before re-fire.
   >
   > **INCONCLUSIVE** outcomes (probe completed but result is ambiguous — e.g. partial reachability, response shape detected but not the expected schema, auth challenge surfaced but not fully diagnosed) **also halt** the runguide; CEO disposition required as for CLEAN NEGATIVE.
   >
   > **Retroactive binding:**
   > - Runguides **drafted but not yet dispatched** are subject to §2.4 retroactively; add §3.0 verification-probe section to their published structure before any future dispatch fires.
   > - Pre-existing runguides being **re-dispatched** (after a halt + patch cycle) are subject to §2.4 at re-dispatch time; the verification probe is mandatory regardless of any prior calibration the runguide may carry.
   > - Runguides that have **completed successfully** (e.g. MAC-101 fccid.io) are not retroactively halted, but should have §3.0 formalized post-hoc to preserve the verification-probe lineage for future Wave-N' re-dispatches of the same source.

2. **§3.0 runguide-template slot — `verification-probe` published structural slot.** Any new runguide drafted post-CP27 MUST include a §3.0 verification-probe section as a first-class structural slot ahead of §3.1 bulk dispatch. The slot's contract: a per-premise probe list, expected probe outcomes (CLEAN POSITIVE / CLEAN NEGATIVE / INCONCLUSIVE), and the halt-or-proceed decision rule. The slot composes with §6 #5 halt criteria (CLEAN NEGATIVE / INCONCLUSIVE both halt §3.1).

3. **§6 #5 halt-criteria composition.** §2.4 §3.0 probe outcomes integrate cleanly with the existing §6 #5 halt-criteria framework. CLEAN NEGATIVE and INCONCLUSIVE outcomes are first-class halt triggers; the runguide returns to drafting per the patch-cycle convention; CEO disposition is required before any re-fire of §3.1. No additional §6 amendment is needed — §6 #5 is the existing halt-criteria contract; §2.4 §3.0 just generates new triggers under it.

### Downstream-consumer audit (per [feedback_bible_amendment_downstream_consumer_audit](/MAC/issues/MAC-178#comment-3029e567-c4e7-4dac-aff8-cd03b8c9a48a) standing rule)

CP27 is a process amendment. No schema migration sibling. No code-path sibling (`export_lynceus.py` / `coverage_matrix.py` / `IDENTIFIER_TYPE_TO_PATTERN_TYPE` unaffected — discipline, not enum). No test-fixture sibling. **Consumer surface is runguides only.**

Ten runguides need retroactive §3.0 verification-probe sections — the 5 halted at minimum per the dispatch directive, plus the 5 drafted/completed for future-re-dispatch consistency:

| Runguide | MAC | Status | §3.0 priority | Suggested §3.0 probes |
|---|---|---|---|---|
| `ised_rel_admission_runguide.md` | [MAC-102](/MAC/issues/MAC-102) | halted | **Must, before v2 re-fire** | Spring-Web-Flow URL probe + form-field exfil + `execution=...` token shape |
| `bt_sig_qualified_designs_admission_runguide.md` | [MAC-103](/MAC/issues/MAC-103) | halted | **Must, before v2 re-fire** | `qualification.bluetooth.com` 301 chase + `Platform/Listings/Submission/{id}/Layers` 401 auth probe |
| `patent_text_mining_admission_runguide.md` | [MAC-105](/MAC/issues/MAC-105) | halted | **Must, before v2 re-fire** | NXDOMAIN check on USPTO PatFT; EPO Espacenet 403 vs OPS 200 probe; Google Patents JS-vs-XHR probe |
| `github_mass_search_admission_runguide.md` | [MAC-107](/MAC/issues/MAC-107) | halted | **Must, before v2 re-fire** | Unauthenticated Code Search probe (expect 401) + auth-tier probe with PAT |
| `ofcom_acma_admission_runguide.md` | [MAC-110](/MAC/issues/MAC-110) | halted | **Must, before v2 re-fire** | Cloudflare-challenge JS probe + Azure APIM vs public-API probe + ACMA RRL-vs-equipment-register schema probe |
| `fccid_io_admission_runguide.md` | [MAC-101](/MAC/issues/MAC-101) | completed (PC1.7 mid-flight patch) | **Should, post-hoc** | Formalize PC1.7's `application_id`-vs-`grant_id` probe as §3.0 |
| `wave_g_v2_playstore_expansion_runguide.md` | [MAC-104](/MAC/issues/MAC-104) | completed | **Should, post-hoc** | Codify apk-pure vs apk-mirror reachability + manifest BLE-permissions probe |
| `conference_proceedings_admission_runguide.md` | [MAC-108](/MAC/issues/MAC-108) | drafted, never dispatched | **Must, before first dispatch** | tesseract availability probe; PDF-archive reachability probe; OCR-grade self-test |
| `muckrock_foia_admission_runguide.md` | [MAC-109](/MAC/issues/MAC-109) | drafted, deferred (PII pre-pass safety) | **Must, before first dispatch** | MuckRock public-feed probe; PII-pre-pass tooling probe; FOIA-document schema probe |
| `wave_g_prime_ios_admission_runguide.md` | Wave-G' iOS | drafted, deferred (Apple ID) | **Must, before first dispatch** | Apple App Store reachability probe; IPA-fetch tooling probe; iOS-decompilation-framework probe |

**8 "Must" cases + 2 "Should" cases = 10 downstream consumers.** Per CEO disposition: the 8 "Must" cases enforce naturally at each runguide's next dispatch-firing gate — no separate tracking issue needed because the §2.4 contract halts §3.1 before fire (structurally self-enforcing). The 2 "Should" cases (MAC-101 + MAC-104, completed runguides) fire lazily next time those runguides are touched (e.g., MAC-101.v2 dispatch or Wave-G' v3 dispatch). Not gating MAC-178 close.

### Composition with §11 hard rules

- **§11 #1 (no fabrication)** — strengthened. §2.4 catches runguide premises that would otherwise produce empty/fabricated extraction yields when the live source no longer matches the assumed schema. The MAC-101 PC1.7 `application_id`-vs-`grant_id` instance is the canonical example: an extraction script writing to the wrong field name does not fabricate, but it produces yield-shape divergence that downstream consumers cannot diagnose without the §3.0 probe trail.
- **§11 #7 (no promotion without provenance)** — orthogonal-strengthening. §2.4 §3.0 probe artifacts (probe-script + observed-response snapshot + outcome classification) are provenance for the runguide-authoring step itself, not for any single row. Future audit of "why was this dispatch fired?" has a structured §3.0 anchor.
- **§11 #8 (no confidence drift upward without corroboration)** — orthogonal. §2.4 is pre-extraction; §11 #8 is mid- and post-extraction. CP27 does not modify §11 #8 sub-rule composition (CP24 / CP25 §1 / CP26 §8).
- **§11 #11 (amendment-log discipline)** — this CP27 entry IS the amendment-log pairing for the new §2.4 + the new §3.0 runguide-template slot. Bible HEAD bumps from the CP26 commit to the CP27 commit landed alongside this entry.
- **§11 #14 (procurement-only never exported to Lynceus)** — orthogonal; CP27 has no downstream-consumer impact on the procurement/Lynceus boundary.
- **§11 #15 (decompiled-output non-redistribution)** — orthogonal; CP27 is runguide-authoring discipline, not data-handling discipline.
- **§11 #16 (Feist facts-only)** — orthogonal; CP27 does not touch the Feist facts-only contract.

### Sequencing post-acceptance

1. **CP27 ratifies at this commit.** Bible HEAD bumps from the CP26 commit to this CP27 commit. Schema version unchanged (22 → 22; CP27 is §-text only — no schema migration, no notes_json convention).
2. **§2.4 insert into `PROJECT_BIBLE.md`** lands in the same commit (placed after §2.3 A Note on Ambition; before §3 Architecture).
3. **CHANGELOG.md v1.2.0 ledger updated** in the same commit — the "DRAFTED pending ratification" prose at the v1.2.0 narrative replaced with the "ratified as CP27" prose; the schema-version-unchanged status preserved.
4. **No downstream-consumer-runguide commits in this CP27 commit.** The 10-runguide retroactive §3.0 retrofits fire lazily at each runguide's next dispatch — naturally enforced by §2.4 halting §3.1 before fire. No separate tracking issue is created; structurally self-enforcing.
5. **No paired state-rotation commit needed.** PROJECT_STATE.md will refresh organically at the next post-MAC-178 close (MAC-178 itself is the close-out moment for the cycle-7 wave).
6. **Operator pushes after final review** per standing constraint at MAC-178 dispatch — all wave-integration commits including this CP27 commit are local-only through completion.

### §12 Open Questions impact

Resolved by CP27:
- **Runguide load-bearing-premise verification as a structural slot vs ad-hoc discipline** — RESOLVED at CP27 §2.4. The §3.0 verification-probe slot is now a published structural slot ahead of §3.1; INCONCLUSIVE and CLEAN NEGATIVE outcomes both halt under §6 #5 with CEO disposition required.

Surfaced by CP27 (queued for future CP candidacy):
- **§4.4 DROPPED-class MAP-vs-DROPPED routing amendment** — surfaced at MAC-178 Priority 8 disposition. The 6 identifier_types promoted in MAC-104 Wave-G v2 (`ble_service_uuid`, `ble_characteristic`, `ble_company_id`, `asdstan_enum_value`, `device_class_id`, `rf_protocol_constant`) are all §4.4 DROPPED-class per CP16/CP19/MAC-117. Candidates for future MAP promotion: `ble_service_uuid` → `ble_uuid` alias and `ble_company_id` → `ble_manufacturer_id` alias (Lynceus consumes these operationally). The remaining 4 carry explicit DROPPED rationale and probably stay DROPPED. **Deferred to a separate future CP cycle (candidate slot: CP28); explicitly NOT part of CP27.**
- **`documented_absence` first-class table promotion** — held at MAC-178 Priority 5 disposition. Cumulative count is ~22 entries; still below the §3 #6 ≥30 wave-cumulative threshold for table-promotion discussion. Revisit when cumulative count crosses the threshold.

### §11 #11 self-binding satisfied

This CP27 entry is the §11 #11 amendment-log pairing for the new §2.4 Empirical-Premise Verification Precondition + the new §3.0 runguide-template structural slot. Bible HEAD bumps from the CP26 commit to the CP27 commit landed alongside this entry. Schema version unchanged (CP27 is §-text only; no schema migration, no notes_json convention, no code-path sibling).

═══════════════════════════════════════════════════════════════════════

## Correction Pass 28 — Wave H desktop-axis vendor-registered non-BLE identifier_type cluster (3 net-new) + SAR-12 7-FP-class codification + wrapper ±90-char windowed-clipping discipline + CP28(a)/(b) deferrals

**Date:** 2026-05-18
**Source:** Wave H pre-v1 desktop static-analysis extraction (Cohort D drone tooling + Cohort F sanctioned-vendor v1) per [MAC-177](/MAC/issues/MAC-177) parent + [MAC-181](/MAC/issues/MAC-181) v1.3.0 release sweep. Three CP28 candidate flags surfaced empirically across 3 vendors × 4 binaries (Hikvision iVMS-4200 + DJI Assistant 2 Mavic + DJI Assistant 2 FPV + FileZilla FP-control); HANDOFF §11(a)(b)(c) in `extraction_outputs/wave_h_pre_v1/HANDOFF_TO_VALIDATOR.md`. CEO disposition on [MAC-177 comment 0d15de7b](/MAC/issues/MAC-177#comment-0d15de7b-25a9-4f1e-bb40-65f00bc30fce) §7 "approve full path" routes CP28(c) to ratification + CP28(a) to hold-under-CP15-ceiling + CP28(b) to anchor-weakened deferral.
**Schema sibling:** Migration [`0023_identifier_type_check_extension_cp28.sql`](../../db/migrations/0023_identifier_type_check_extension_cp28.sql) — applied at commit `2795ebba7866ad164121668321e213308aa87936`. Cumulative CHECK enum 48 → 51 values per `feedback_cumulative_check_enum_across_sequenced_migrations`. PRAGMA integrity_check + quick_check both ok at apply time; 22,549 active rows preserved via INSERT SELECT *.
**Bible commit:** This entry + the schema-sibling migration form the MAC-181 v1.3.0 cycle's amendment-log half. Bible HEAD bumps from the CP27 commit to the CP28 commit landed alongside this entry. Schema version bumps 22 → 23.
**Status:** Ratified at [MAC-181](/MAC/issues/MAC-181) dispatch 2026-05-18 per CEO disposition [`comment-0d15de7b`](/MAC/issues/MAC-177#comment-0d15de7b-25a9-4f1e-bb40-65f00bc30fce) §7 (board-class ratification of CP28(c) "approve full path" + CP28(a) "hold under CP15 ceiling" + CP28(b) "deferred post-Cohort-F"). The MAC-181 cycle is the coordinated-commit landing per the CP23/CP24/CP25 trio precedent + [[feedback_bible_amendment_downstream_consumer_audit]] §S.6.1 worker-autonomous absorption discipline.
**Binds:** Validator + ExtractionWorker (the 3 new `identifier_type` enum values are first-class promotion targets at §8.4 strict-promotion confidence ≥80 for `vendor_document_uuid_cloud_reference`, ≥75 for the two Windows-registry classes per §8.2 sub-band ladder); Lynceus consumer (CP28(c) §4.4 posture: `vendor_document_uuid_cloud_reference` MAPS into the Lynceus export window via the cloud-hostname half; the two Windows-registry classes are DROPPED-class per CP16 disposition); future Wave-H Continuation + Wave-I scope discussions (CP28(a) `vendor_application_static_analysis` source_type enum is held under the CP15 `manufacturer_app` ceiling — band-distinction encoded via §8.2 sub-band ladder + `notes.session_admission` — until empirical density triggers re-fire; CP28(b) `sanctioned_vendor_public_distribution_facts_only` license-posture sentinel is deferred post-Cohort-F completion as CP-of-its-own).

### Why this Correction Pass exists

Wave H pre-v1 desktop-axis static analysis (1 partial-cohort wave; 3 real-vendor binaries + 1 FP-control; 4 unique candidate UUID values across cohorts D + F) surfaced an empirical finding that the CP17 desktop-axis thesis did not predict: **even within installer-cohort desktop binaries that DO exist (DJI Assistant 2 + Hikvision iVMS-4200), the identifier-class surface differs from the Wave G mobile axis**. Wave G mobile yields genuine BLE service UUIDs because the phone IS the BLE central; the vendor app contains BLE service/characteristic UUIDs in code. Wave H desktop yields **MSI ProductCodes + COM CLSIDs + cloud-document UUIDs + vendor-cloud-endpoint hostnames** — not BLE protocol identifiers, but still vendor-controlled identifiers with empirical density worth promoting under non-BLE classes.

The CP26 §8 semantic-validation pass — re-applied across all 4 unique candidate UUIDs surfaced — re-classed all 4 as different identifier-class shapes:

| UUID value | Re-class | Vendor | Cohort |
|---|---|---|---|
| `f4d4dbf5-ba4b-40db-9a44-f8395f3728cf` | `vendor_document_uuid_cloud_reference` | DJI | D (Mavic + FPV cross-product attested per CP24) |
| `054aae20-4bea-4347-8a35-64a533254a9d` | `windows_com_clsid_vendor_registered` | DJI | D (Mavic; DJIBrowser LocalServer32) |
| `9a25302d-30c0-39d9-bd6f-21e6ec160475` | `windows_installer_productcode_vendor_registered` | Hikvision | F (iVMS-4200 main package) |
| `ce2f96d0-63d2-4b9c-a8d6-0d1a60840bd8` | `windows_installer_productcode_vendor_registered` | Hikvision | F (iVMS-4200 Multilingual Wizard sub-package) |

Net `ble_service_uuid` candidates = **0** after the CP26 §8 audit. The Wave H signal that does exist lives almost entirely in the 3 new non-BLE identifier classes. Forcing them into `fp_findings.json` would lose operational value (endpoint-fleet detection: deployed iVMS-4200 reports its MSI ProductCode through enterprise management tooling; deployed DJI Assistant 2 leaves the DJIBrowser COM CLSID registered in the Windows registry; both are detectable signals worth surfacing to Lynceus / downstream consumers). CP28(c) codifies these as first-class `identifier_type` enum values.

CP28 also codifies two operational disciplines that emerged during the wave:

1. **SAR-12 7-FP-class codification** — across sessions 1 + 2, the `wave_h_wrapper.py` accumulated 7 supplemental FP classes catching 188 desktop-platform-wide false-positive UUID-shape strings that v4 alone would have promoted. These are vendor-agnostic Windows-platform GUIDs (manifest compatibility GUIDs, COM IIDs from Windows SDK headers, SetupAPI device-class GUIDs, libusb ASCII identifiers, third-party DLL path prefixes, SxS publicKeyTokens, MSI ProductCodes in install-registry context). Source-of-truth remains the wrapper (`android_test/tools/extraction/wave_h_wrapper.py`); CP28 codifies the named-class roster for future-wave runguide consumption.

2. **Wrapper ±90-char windowed-clipping discipline** — at the candidate-walk layer, source_excerpt clipping was previously whole-line-with-overflow_dropped (v3 behavior; FileZilla H2 disambig demonstrated this misses 4 supportedOS UUIDs because the manifest XML lines exceed 200 chars and trip overflow_dropped before reaching the FP filter). The v4-with-session-2 wrapper clips per-match (±90 chars around the regex match end-points, ensuring the matched UUID itself + immediate context lands in `source_excerpt` even when the full line overflows). Discipline binds future runguide templates: per-match windowed clipping at the candidate-walk layer; whole-line overflow_dropped only as a fallback for matches whose ±90-char window itself exceeds 200 chars.

### Corrections applied

**§4.1 — three new `identifier_type` enum values (CP28(c)).** The `identifiers.identifier_type` CHECK enum extends 48 → 51 values via migration 0023:

1. **`windows_installer_productcode_vendor_registered`** — MSI/InstallShield ProductCode GUIDs registered by vendor desktop installers in Windows Installer registry contexts (`SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{...}` / `\Wow6432Node\...\Uninstall\{...}` / `\{ProductCode-GUID}` bracketed form / `InstallShield Wizard` markers). §8.2 sub-band: **75–90** (vendor-controlled identifier; install-time registry context; reasonable cross-extraction stability; band aligns with `manufacturer_doc` / `manufacturer_app` neighborhood). §4.4 posture: **DROPPED** — install/registry context only; low passive-scan utility for Lynceus's BLE/WiFi-axis relevance window. Empirical Wave H seed: 2 unique values in Hikvision iVMS-4200 v3.13.0.5_Multilingual.

2. **`windows_com_clsid_vendor_registered`** — Windows COM Class IDs registered by vendor desktop installers (`Software\Classes\CLSID\{...}\LocalServer32` / `\InprocServer32` registry contexts; vendor-name-anchored token in the immediate path). §8.2 sub-band: **75–90** (same logic as ProductCode class; vendor-controlled, install-time-registered, cross-extraction stable). §4.4 posture: **DROPPED** — install/registry context only; low passive-scan utility. Empirical Wave H seed: 1 unique value in DJI Assistant 2 Mavic 2.0.14 (DJIBrowser COM server).

3. **`vendor_document_uuid_cloud_reference`** — Vendor-controlled cloud-hosted document UUID embedded in vendor-owned cloud endpoint URL (e.g. `https://duss.djicorp.com/functional-document/<UUID>`). §8.2 sub-band: **80–95** (the cloud-hostname half is itself a vendor-controlled identifier worth cross-source-corroboration anchoring against FCC EAS filings + USAspending procurement records + court records; the per-document UUID-half raises the per-row provenance over registry-context classes). §4.4 posture: **MAP** — the vendor-controlled hostname half (`duss.djicorp.com`) lifts into Lynceus's relevance window as a passively-scannable vendor cloud endpoint signature; downstream consumers can surface "this network observed DJI cloud traffic" as a deployment signal. Empirical Wave H seed: 1 unique value (`f4d4dbf5-...`) with CP24 within-vendor-cross-product attestation (Mavic + FPV Assistant 2 binaries). **Metadata-key convention:** at promotion-time, every `vendor_document_uuid_cloud_reference` row MUST populate `notes.cloud_url_hostname` with the canonical vendor-cloud hostname (the host portion of `source_url`, lower-cased, no port), normalized as the queryable join key for §4.4 MAP-posture downstream consumers + future Wave I hostname-corpus extraction (the id=23059 inaugural row was backfilled at MAC-181 §8.10 commit per [MAC-182](/MAC/issues/MAC-182) operator directive 2026-05-19T02:27:53Z; the convention binds prospectively for all future promotions of this class).

**CP28(a) — `vendor_application_static_analysis` source_type enum value: DEFERRED.** Wave G mobile (Android APKs) + Wave H desktop both land under the existing `manufacturer_app` source_type enum per CP15 source-type ceiling (HANDOFF §9 used `vendor_documentation` as descriptive shorthand for the band; the actual landed source_type at MAC-181 promotion-time is `manufacturer_app`, mirroring the Wave G Flock FS Installer + Getac BWC Viewer precedent at sid=13/14). With ~20+ vendors now extracted across Wave G + Wave H via static-analysis methodology, the empirical density is meaningful, but per CEO disposition the operational band-distinction is encoded via the §8.2 sub-band ladder + the `notes.session_admission` field on per-wave `sources` rows rather than via a new `source_type` CHECK enum value. **Re-fire candidate:** if Wave H Continuation + Wave I both close with substantive new-vendor admissions and Lynceus operationally requests a filterable `vendor_application_static_analysis` source_type class (separate from generic FCC/SEC/SAM-vendor-doc admissions), surface as CP-of-its-own.

**CP28(b) — `sanctioned_vendor_public_distribution_facts_only` license-posture sentinel: DEFERRED.** Originally proposed in session 1 with empirical anchor of "Hikvision iVMS-4200 surfaces real BLE UUIDs that benefit from the new posture sentinel." The session 2 §1 CP26 §8 audit weakened this anchor — the 2 surviving Hikvision UUIDs re-class as MSI ProductCodes, not BLE. The sentinel's empirical anchor now rests on the FACT that Hikvision distributes publicly via .com (not .cn) AND the EULA-posture + sanctioned-vendor sub-gate workflow was cleared per CP20 §11 #16, NOT on identifier yield. Per CEO disposition, the sentinel **defers to post-Cohort-F completion as CP-of-its-own** — re-fire once Dahua + Uniview are also acquired (currently Cloudflare-blocked) and the empirical density is broader than a single sanctioned vendor.

**Wrapper §-fragment — ±90-char windowed clipping (next runguide template fold-in).** Future wave-extraction runguides MUST specify per-match windowed clipping at the candidate-walk layer: for each regex match `m` in a source-line `L`, clip `source_excerpt = L[max(0, m.start - 90) : min(len(L), m.end + 90)]` (subject to the §8.4 200-char hard cap, with overflow_dropped as a fallback only when the ±90-char window itself exceeds 200 chars). The whole-line-with-overflow_dropped behavior is deprecated for candidate-walk extraction; it remains valid only for fixed-shape line-anchored extractors where line-overflow is structurally exceptional rather than systemic. The wave_h_wrapper.py v0.2_post_session_2 is the canonical implementation reference.

**SAR-12 codification — 7 FP-class roster.** The `wave_h_wrapper.py` final roster of 7 supplemental FP classes is canonized for cross-wave consumption (source-of-truth remains the wrapper; this CP entry codifies the named-class roster for future-wave runguide consumption):

| # | Class | Scope |
|---|---|---|
| 1 | `WINDOWS_SUPPORTEDOS_MANIFEST_GUIDS` | Microsoft application-manifest compatibility GUIDs (Vista / 7 / 8 / 8.1 / 10) — every Windows installer embeds. |
| 2 | `WINDOWS_COM_INTERFACE_GUIDS` | Microsoft Windows SDK COM IIDs (`IID_IShellLinkA` + bulk-seeded from `combase.h`, `shobjidl.h`, `objidl.h`, `oaidl.h`, `unknwn.h`; expected ~500-2000 IIDs at full seed). |
| 3 | `WINDOWS_DEVCLASS_SETUP_GUIDS` | SetupAPI device-class GUIDs (USB / Media / Modem / Net / HID / 1394 / Image / MTP / USB_DEVICE / WCEUSBS / BUS_TYPE_USB). |
| 4 | `LIBUSB_ASCII_IDENTIFIERS` | UUID-shaped ASCII strings inside libusb-win32-WDF library binary. |
| 5 | `THIRD_PARTY_DLL_PATH_PREFIXES` | UUID-class candidates whose `source_file_relative` path leaf starts with 3rd-party library prefixes (Qt5*, libcrypto-*, libssl-*, libeay32, msvcp*, msvcr*, vcruntime, libusb0, libusb-1.0, d3dcompiler_*, libegl, libglesv2, sqlite3, icu*, iconv, libffi, libxml2, zlib). |
| 6 | `WINDOWS_SXS_PUBLICKEYTOKEN` | 16-char hex publicKeyTokens in `<assemblyIdentity>` XML manifests (Microsoft.Windows.Common-Controls / public assemblies / .NET Framework defaults). |
| 7 | `windows_installer_productcode_in_msi_context` | MSI/InstallShield ProductCode GUIDs in Windows Installer registry contexts (context-substring-based: 8 markers incl. `\{`, `\Uninstall\{`, `InstallShield Wizard`). Codified post-Hikvision-CP26-§8-audit (session 2). |

Aggregate Wave H effect: 188 FPs caught across 4 binaries; net 0 genuine `ble_service_uuid` candidates remain post-CP26-§8-audit; the 4 surviving UUIDs all re-class as one of the 3 new CP28(c) identifier_types.

### Downstream-consumer audit (per [[feedback_bible_amendment_downstream_consumer_audit]] standing rule)

CP28 is a coordinated schema + bible amendment with concrete downstream-consumer surfaces in this cycle and follow-on cycles:

| Consumer | Surface | Action in this MAC-181 cycle |
|---|---|---|
| Migration ledger | `db/migrations/0023_identifier_type_check_extension_cp28.sql` | **Landed at commit `2795ebba`** (this CP's schema sibling). |
| Schema-version ledger | `schema_version` row 23 | **Bumped** at migration-apply (22 → 23). |
| `DATA_DICTIONARY.md` | v22 → v23 refresh: L9 Scope schema_version; L543 migration ledger append; L607 `identifier_type` enum roster 48 → 51 with CP-band annotation. | **Updated in this cycle** (PRAGMA sweep + CHECK-extract pass per MAC-180 discipline). |
| `IDENTIFIER_TYPE_TO_PATTERN_TYPE` map in `scripts/export_lynceus.py` | §4.4 MAP posture for `vendor_document_uuid_cloud_reference` (MAPS; cloud-endpoint pattern type) + DROPPED posture for `windows_installer_productcode_vendor_registered` + `windows_com_clsid_vendor_registered`. | **Updated in this cycle** during exports refresh; `dropped_in_export` reconciliation surfaces the two DROPPED classes with rationale. |
| `coverage_matrix.py` / `coverage_report.md` | Three new identifier_type cells; per-confidence-band distribution. | **Regenerated in this cycle** post-promotion. |
| Wave H + Wave I runguide templates | ±90-char windowed-clipping discipline at candidate-walk layer (wrapper §-fragment). | **Codified in this CP**; lazy fold-in at next runguide draft cycle. |
| Wave H wrapper reference | SAR-12 7-FP-class roster source-of-truth = `android_test/tools/extraction/wave_h_wrapper.py`. | **Wrapper at canonical path** in this cycle (per §8.7 port); roster codified in this CP entry for cross-wave consumption. |
| Test fixtures | No new pytest fixtures required — the 3 new enum values are surfaced via the schema migration; no extractor-side regression suite expects the CHECK to reject the old set. | **No-op this cycle.** |

### Composition with §11 hard rules

- **§11 #1 (no fabrication)** — strengthened. CP28(c) codifies three new identifier classes anchored on 4 empirically-attested vendor-registered UUID values surfaced by CP26 §8 semantic-validation. No fabrication; HANDOFF §11(c) names the four anchors verbatim.
- **§11 #7 (provenance is the database)** — orthogonal-strengthening. The 4-row promotion lands with `source_url` + `source_excerpt` carrying the per-match-windowed-clipped registry/URL context per the wrapper §-fragment discipline. The Wave H sources row anchors at `name='Vendor Desktop Application Static Analysis — Wave H'`; the per-row `notes_json` carries the CP26 §8 re-class lineage for forensic traceability.
- **§11 #8 (no confidence drift)** — orthogonal. CP28 codifies the §8.2 sub-band ladder (75–90 / 75–90 / 80–95) for the three new classes; the 4 promoted rows land at single-source confidence within the ladder per the band's logic. No cross-source corroboration uplift applies in this MAC-181 batch (Cohort D's only independent vendor 2 is Skydio, which is P11 CLEAN NEGATIVE / `documented_absence`; no §8.3 lift triggers fire).
- **§11 #11 (amendment-log discipline)** — this CP28 entry IS the amendment-log pairing for migration 0023. CP-anchor = migration commit `2795ebba7866ad164121668321e213308aa87936` + this MAC-181 child issue. Bible HEAD bumps from the CP27 commit to the CP28 commit landed alongside this entry. Schema version bumps 22 → 23.
- **§11 #14 (procurement-only never exported to Lynceus)** — orthogonal; CP28 has no procurement-only surface impact. The Wave H sources row is `source_type='manufacturer_app'`, not `procurement`.
- **§11 #15 (decompiled-output non-redistribution)** — orthogonal-strengthening. The Wave H staging tree ported to canonical (`extraction_outputs/wave_h_pre_v1/`) contains candidates.json + fp_findings.json + provenance + analysis logs; **no decompiled vendor source** is in the git index. Extracted binary contents remain SSD-only per HANDOFF §12 (`/media/kev/Extreme SSD/argus/desktop_test/scratch/*`). The wrapper code (`wave_h_wrapper.py`) is filter/extraction discipline, not decompiled vendor source.
- **§11 #16 (Feist facts-only promotion from public-but-unlicensed sources)** — applies at row-level promotion. The Wave H sources row carries `license_posture='per_vendor'` + `upstream_license_posture='no_license_declared_facts_only'` defaults per CP21. The 4 promoted identifier rows inherit the facts-only posture; the upstream license posture binds at row-level (per `feedback_license_posture_canonical_key`: `notes.upstream_license_posture` is the canonical sentinel-key shape).

### Sequencing post-acceptance

1. **Migration 0023 applied** at commit `2795ebba`. PRAGMA integrity_check + quick_check both ok. 22,549 active rows preserved.
2. **CP28 ratifies at this commit.** Bible HEAD bumps from the CP27 commit to this CP28 commit. Schema version bumps 22 → 23.
3. **§4.1 update lands implicit-in-schema** via the new CHECK enum cardinality (no PROJECT_BIBLE.md §-text edit needed at this CP — the schema migration is the §4.1 surface). `DATA_DICTIONARY.md` v23 refresh in this same cycle covers the documentation half.
4. **§8.4 / §4.4 sibling decisions land in this same cycle**: the 3 new identifier_types are promoted as first-class targets at strict-promotion confidence ≥80 (specifically: 1 row at confidence 90 for `vendor_document_uuid_cloud_reference` cross-product-attested, 2 rows at confidence 85 for the Hikvision ProductCodes, 1 row at confidence 85 for the DJI COM CLSID; per the §8.2 sub-band ladder). The §4.4 MAP-vs-DROPPED posture binds at exports-refresh time in this same cycle.
5. **Wave H Continuation post-v1.3.0** scope re-fires CP28(a) and CP28(b) at Cohort F + at-least-one-of-Cohort-B/C close. CP28(a)/(b) are tracked as deferred CP-of-its-own candidates; not gating MAC-181 close.

### §12 Open Questions impact

Resolved by CP28:
- **CP28(c) `windows_*` + `vendor_document_uuid_cloud_reference` first-class identifier_type promotion** — RESOLVED at CP28. Three new enum values land via migration 0023; §8.2 sub-band ladder + §4.4 MAP/DROPPED posture documented.
- **§4.4 DROPPED-class MAP-vs-DROPPED routing amendment (CP27 surfaced candidate)** — PARTIALLY RESOLVED. The CP28(c) class `vendor_document_uuid_cloud_reference` lands as MAP-class (cloud-hostname half lifts into Lynceus relevance window). The two Windows-registry classes are DROPPED. The 6 CP27-surfaced existing identifier_types (`ble_service_uuid`, `ble_characteristic`, etc.) remain unchanged in this CP — that disposition is a separate future CP cycle.
- **Wrapper ±90-char windowed-clipping discipline** — RESOLVED at CP28 wrapper §-fragment. Future runguide templates inherit the discipline.
- **SAR-12 7-FP-class roster cross-wave consumption** — RESOLVED at CP28. Named-class roster codified for future-wave runguide consumption; source-of-truth remains the wrapper.

Surfaced by CP28 (queued for future CP candidacy):
- **CP28(a) `vendor_application_static_analysis` source_type enum value** — re-fire candidate post-Wave-H-Continuation + Wave-I close. Empirical density currently meaningful but operationally encoded via the §8.2 sub-band ladder + `notes.session_admission`.
- **CP28(b) `sanctioned_vendor_public_distribution_facts_only` license-posture sentinel** — re-fire candidate post-Cohort-F completion as CP-of-its-own. Empirical anchor weakened post-CP26 §8 audit; re-anchor at Cohort F close with broader sanctioned-vendor empirical density.
- **`documented_absence` first-class table promotion** — held at MAC-178 Priority 5 disposition (carried forward from CP27). Cumulative count post-Wave-H is ~29 entries (22 prior + 7 Wave H: 6 Cohort A + 1 Skydio Cohort D); below but approaching the §3 #6 ≥30 wave-cumulative threshold for table-promotion discussion. Revisit at next wave close.
- **CP17 desktop-axis thesis bifurcation finding** — HANDOFF §10 marquee output. The CP17 cohort thesis (operator-vs-installer cohort split predicted from Wave G mobile) is empirically refined into two distinct dimensions: (1) cohort presence (operator-cohort desktop class has structurally dissolved into web/mobile across modern VMS + drone tooling vendors); (2) identifier-class surface (installer-cohort desktop binaries yield non-BLE vendor identifiers, not BLE protocol identifiers). Wave I scoping should re-scope to vendor cloud-endpoint discovery + installer-config surface as headline metrics, NOT BLE UUIDs. **Codified as bible §-text finding; not a CP entry** — refer to HANDOFF §10 for the marquee policy paragraph.

### §11 #11 self-binding satisfied

This CP28 entry is the §11 #11 amendment-log pairing for migration `0023_identifier_type_check_extension_cp28` + the SAR-12 7-FP-class codification + the wrapper ±90-char windowed-clipping discipline + the CP28(a)/(b) deferrals. Bible HEAD bumps from the CP27 commit to the CP28 commit landed alongside this entry. CP-anchor: migration commit `2795ebba7866ad164121668321e213308aa87936` + [MAC-181](/MAC/issues/MAC-181) child issue ID. Schema version bumps 22 → 23.

═══════════════════════════════════════════════════════════════════════

Correction Pass 29 — Wave I/I.5/I.6/I.7 vendor cloud-infrastructure hostname corpus value_classes + SAR-13 schema-fabrication discipline + SAR-13.5 bucket attribution discipline

## Correction Pass 29 — vendor cloud-infrastructure hostname corpus value_classes (3 codified + 2 deferred)

### Scope

CP29 codifies three net-new `identifier_type` enum values empirically anchored by the cumulative 4-wave Wave I autonomous extraction effort (Wave I main 12,212 hostnames + I.5 26 + I.6 193 + I.7 159; 12,590 unique). Migration 0024 extends the CHECK enum 51 → 54. Two candidate value classes deferred per conservative ≥1-empirical-evidence gate; reserved for CP30 / migration 0025.

### §1 — Codified value_classes (3)

**`vendor_controlled_hostname`** — Vendor-owned cloud-infrastructure hostname (e.g. `hppki.honeywell.com`, `duss.djicorp.com`, vendor-apex subdomains observed in CT logs). Confidence ladder:

- 75-90 single-source default (predominantly Class B crt.sh CT log attestations)
- 85-95 cross-source corroboration (CP24 independence: ≥2 distinct extraction source-classes from genuinely independent providers)
- 95-99 firmware-embedded cert chain (vendor-signed code-signing CA + multi-source corroboration)

Empirical Wave I anchor: 12,620 attestation rows over 12,590 unique hostnames across 8 source-classes (B 11,551; A 587; I_github_readme 211; I_github_source 159; F 133; D+D_bucket_enum_deep 60; C 8; A_bucket_payload_firmware 8/4 unique; J 4).

**`vendor_cloud_endpoint_url`** — Vendor-controlled cloud endpoint URL with path component embedding a vendor-recognizable signature (URL-shape superset of CP28 `vendor_document_uuid_cloud_reference`). Confidence ladder:

- 80-90 single-source default
- 90-97 with binary + CT log + sitemap multi-source corroboration

Empirical Wave I anchor: 419 attestations carrying `vendor_cloud_endpoint_url` in the `candidate_value_class_alternates` field (URL-pattern variant co-extant on hostname).

**`vendor_controlled_hostname_deprecated`** — Vendor-owned hostname previously publicly resolvable, NXDOMAIN-verified deprecated. Retained as historical attribution anchor + supersession-chain pivot. Confidence ladder:

- 80-87 default (NXDOMAIN active-verification at extraction time is dominant evidence)

Empirical Wave I anchor: 568 NXDOMAIN-verified entries from Wave I.6 sub-pass 7 `deprecated_hostname_verified.json classifications.confirmed_deprecated_nxdomain=568`. 565 promoted into canonical identifiers (3 dropped at Phase 2 scrub).

### §2 — Confidence-band ladder (paste-not-cite)

| Value class | Single-source default | Cross-source | Firmware-cert ceiling |
|---|---|---|---|
| `vendor_controlled_hostname` | 75-90 | 85-95 | 95-99 |
| `vendor_cloud_endpoint_url` | 80-90 | 90-97 | — |
| `vendor_controlled_hostname_deprecated` | 80-87 | — | — |

Marquee Phase 5 anchor: **`hppki.honeywell.com`** promoted at confidence=99 via 4-source independent corroboration (2 Honeywell OTA signing certs from CT40 Android firmware META-INF/com/android/otacert + crt.sh CT log + binary Class A extraction + bucket payload `A_bucket_payload_firmware`). Issuer DN `C=US, O=Honeywell International Inc., OU=ACS, CN=Honeywell CodeSign RSA CA`; cert sha256 `60a8cf8feeb33926366776b395d6c8d9334bd8b42038b85563622ce0a1d0745b`. Strongest possible attribution chain in the framework — firmware-embedded cert + vendor-signed code-signing CA + multi-source-class corroboration.

### §3 — Deferred candidates (2; NOT codified in migration 0024)

**`vendor_asn_prefix`** — Wave I class G extraction; `asn_findings.json total=0`; class G halted with `url_pattern_issue` carry-forward to Wave I-prime. Per conservative ≥1-empirical-evidence gate, codification deferred. Reserved for CP30 / migration 0025 when ASN-prefix observation surfaces (likely Wave I-prime with RDAP url-pattern fix).

**`vendor_controlled_ip`** — Wave I.5 + I.6 + I.7 cert IP-SAN sub-passes returned 0/0/0 IP SANs:

- Wave I.5: crt.sh PEM fetch rate-limited (0/0)
- Wave I.6: total=0/0
- Wave I.7 sub-pass 11: partial-killed at hikvision after 0/31 IP SANs surfaced from 31 certs (budget-vs-yield tradeoff)

Deferred until empirical observation surfaces. Reserved for CP30 / migration 0025.

### §4 — Source admissions enabling CP29 (13 new sources, sid range 54-66)

| sid | source_class | first_admitted_in | ratification_band |
|---|---|---|---|
| 54 | B (CT log aggregator) | v1.4.0 | primary_registry_adjacent |
| 55 | K (public archive temporal) | v1.4.0 | community_public_archive |
| 56 | I (vendor first-party source/README) | v1.4.0 | vendor_published |
| 57-61 | G (5 RIR RDAP endpoints) | v1.4.0 | primary_registry |
| 62-64 | J (3 public package registries) | v1.4.0 | vendor_published |
| 65 | A_bucket_payload (vendor public cloud-storage payload) | v1.4.0 | vendor_published — SAR-13.5 attribution-gate-binding |
| 66 | A/C/D/F umbrella (Wave I extraction methodology) | v1.4.0 | extraction_methodology_umbrella |

Source_type CHECK enum maps to closest existing 13-value enum; semantic source_class + ratification_band live in `sources.notes` JSON per CP14/CP16 pattern. CP30 candidate for 5 new source_type enum values (certificate_transparency_log, public_archive, vendor_first_party_source_code, public_package_registry, vendor_cloud_storage_payload) deferred to Wave I-prime.

### §5 — Known limitations

- Single-vendor attestation ≠ ceiling promotion. Confidence ceiling of 90 for `vendor_controlled_hostname` single-source unless CP24 cross-source independence holds.
- §8.3 lift requires CP24 cross-source independence verification. Same-vendor's other binary repackaging ≠ independent source; two GitHub repos in same org ≠ independent.
- Wave I extraction-time pre-scrub was already extensive (Class B 5% calibration FP rate; Class A 481 fp_dropped of 1,214 surfaced). Cumulative Phase 2 FP-scrub survivor rate of 97.21% reflects extraction-time pre-scrub; carry-forward manual top-50 GitHub-sourced calibration to anchor empirical FP rate post-v1.4.0.
- `device_category='unknown'` is the default Phase 5 categorization for Wave I cloud-infrastructure hostnames (these are vendor attribution anchors, not device-pairable identifiers per §11 #13). All 12,239 v1.4.0 promotions correctly DROP from Lynceus export at the §11 #13 device-category-unknown gate.

### §11 #11 self-binding satisfied

This CP29 entry is the §11 #11 amendment-log pairing for migration `0024_cp29_vendor_hostname_corpus_value_classes` + SAR-13 entry + SAR-13.5 entry. CP-anchor: migration commit `<TBD-this-cycle>` + [MAC-183](/MAC/issues/MAC-183) child issue ID. Schema version bumps 23 → 24.

═══════════════════════════════════════════════════════════════════════

SAR-13 — Runguide-schema-fabrication discipline (PRAGMA-verify before SQL drafting)

## SAR-13 — Runguide-schema-fabrication discipline

### Codification

SAR-13 codifies the discipline that all runguide / dispatch SQL referencing canonical schema tables MUST be DB-verified at drafting time via `PRAGMA table_info(<table>)` against the live `~/argus/db/argus.db`, OR explicitly marked TBV (to-be-verified) with a §3.0 probe re-disposition required. Schema fabrication caught at integration time forces phase halt + operator review.

### Verification methodology

Before drafting any SQL that touches a canonical table:

1. `PRAGMA table_info(<table>)` against the live DB
2. Cross-reference EVERY column name + type against `DATA_DICTIONARY.md`
3. Inspect CREATE TABLE statement via `sqlite_master` for embedded CHECK constraints (PRAGMA table_info does NOT surface CHECKs — separate query required)
4. If any column name / type / CHECK enum value referenced in SQL does not exist in the live schema: HALT — do NOT fabricate

### Empirical anchor

**Origin** (codified): Wave I §3.0 probe (2026-05-19). Assistant Claude's runguide referenced `manufacturer_id` and `WHERE active=1` against the live `manufacturers` table that has NEITHER (actual id column is `id`; no `active` column exists). Caught pre-execution via the §3.0 probe SAR-12 §S.2 discipline; methodology adapted.

**Recurrence** (v1.4.0 MAC-183 integration): dispatch §0.2 / §10.1 reference `schema_migrations` table; live name is `schema_version` (per migration 0001 convention). Caught pre-SQL-drafting at Phase 0 §0.2 baseline verification. Phase 1 migration 0024 used correct table name.

**Recurrence** (v1.4.0 MAC-183 Phase 6): `deployment_observations.license` is NOT NULL with a CHECK enum (5 values: ODbL-1.0 / CC-BY-NC-SA-4.0 / public-domain / foia / unspecified). Initial Phase 6 multi_tenant_patterns insert used `license='CT_LOG_PUBLIC_OBSERVATIONAL_NON_PII'` (semantic but not enum-compliant); 106-row insert returned 0 errors but 0 rows committed (silent CHECK rejection). Caught post-insert via row-count delta = 0 anomaly investigation. PRAGMA table_info had captured `license TEXT NOT NULL` but NOT the CHECK enum — full schema-statement-via-sqlite_master query is the load-bearing methodology.

### Carry-forward refinement (post-v1.4.0)

The Wave I integration cycle surfaced a sub-rule: **PRAGMA table_info alone is insufficient for SAR-13.** Column types + NOT NULL surface, but CHECK constraints (including CHECK enums) do not. SAR-13 binding methodology MUST include `SELECT sql FROM sqlite_master WHERE type='table' AND name='<table>'` parsing for every CHECK clause that affects insert / update validation.

### §11 #11 self-binding satisfied

This SAR-13 entry is the bible-amendment sibling of CP29 + migration 0024 + SAR-13.5. Anchored at MAC-183 dispatch (Paperclip CEO comment `575aca55-9843-4e1f-811f-e20436e06e12`, 2026-05-20T00:08:31Z) + integration close.

═══════════════════════════════════════════════════════════════════════

SAR-13.5 — Bucket attribution discipline (content-based attribution gate before promotion)

## SAR-13.5 — Bucket attribution discipline

### Codification

SAR-13.5 codifies that bucket discovery via predictable-slug enumeration produces a high FP rate (~57% misattribution observed). Public-bucket promotion (any candidate with `source_class=A_bucket_payload` or `source_class=D_misconfig_bucket`) requires content-based attribution verification BEFORE any acquisition or identifier promotion fires.

### Verification methodology

1. Per-bucket attribution probe: filename semantic match + path structure match + optional DNS CNAME corroboration
2. Three-state classification per bucket:
   - **`confirmed`** — content matches vendor; promotion allowed
   - **`rejected_slug_collision`** — bucket exists but belongs to a different entity; DROP candidate; do NOT acquire
   - **`ambiguous_operator_review_required`** — content insufficient to attribute; operator review required before promotion
3. SAR-13.5 gate must be passed at Phase 2 FP-scrub time; candidates from `rejected_slug_collision` or `ambiguous_operator_review_required` buckets are DROPPED at Phase 2 §2.3

### Empirical anchor

**Origin** (codified): Wave I.5 sub-pass 1A surfaced 7 PUBLIC buckets via slug enumeration; Wave I.6 sub-pass 4 content-attribution gate reclassified only 1 as `confirmed` (Honeywell), 3 as `rejected_slug_collision` (e.g., `axon-cdn` belongs to ArtHaus burlesque gallery, NOT Axon), 3 as `ambiguous`. **57% misattribution rate** at slug-discovery time.

### Phase 2 binding (v1.4.0 MAC-183)

Per Phase 2 §2.3, `bucket_attribution_verification.json` was consulted for the cumulative corpus. 0 bucket attribution drops applied — buckets present in I.5/I.6 deltas were already attribution-vetted at sandbox time before flowing into v1.4.0 sandbox outputs. Source `vendor_public_bucket_payload` (sid=65) carries SAR-13.5 attribution-gate-binding in its admission notes; per-row Phase 5 promotion for `source_class=A_bucket_payload_firmware` requires bucket `attribution_status='confirmed'` (Honeywell OTA signing infrastructure confirmed, 3 surviving promotion rows).

### §11 #11 self-binding satisfied

This SAR-13.5 entry is the bible-amendment sibling of CP29 + migration 0024 + SAR-13. Anchored at MAC-183 dispatch + integration close.

═══════════════════════════════════════════════════════════════════════

SAR-15 — Per-vendor probe-scope discipline (vendor admission basis binds extraction scope)

## SAR-15 — Per-vendor probe-scope discipline

### Codification

SAR-15 codifies that **per-vendor probes during multi-vendor extraction must respect the rationale of the vendor's canonical admission**. A vendor admitted to the canonical lexicon for one specific axis (e.g., MAC-cohort completeness) should NOT be auto-included in extraction passes targeting a different axis (e.g., cloud-infrastructure hostname enumeration) without explicit operator ratification of the cross-axis probe.

### Methodology

Before any multi-vendor extraction pass that iterates over the canonical manufacturers lexicon:

1. **Read the admission basis** for each vendor from `manufacturers.notes` JSON (typical key: `added_via`, e.g., `'MAC-170 P2 (UK CH cycle-1 admission)'`).
2. **Apply axis-filter**: only include vendors whose admission basis aligns with the extraction's target axis. For surveillance-equipment hostname extraction, this means filtering OUT vendors admitted purely for industrial-MAC-cohort completeness, drone-MAC-cohort fills, or other non-surveillance-axis bases.
3. **Document the filter** in the extraction runguide §1 / §3.0 probe disposition.

### Empirical anchor

**Origin** (codified post-MAC-183 board feedback, 2026-05-20): Wave I v1.4.0 cumulative extraction probed all 51 canonical vendors uniformly and surfaced **252 corporate-infrastructure hostnames under `matthey.com` apex** (`ace.matthey.com`, `amer-sbc1.matthey.com`, `analyticalservices.matthey.com`, etc.). Johnson Matthey PLC (mfg_id=205) was admitted to canonical lexicon at MAC-170 P2 (2026-05-17) for the **40:f3:85 /28 MA-M sibling MAC cohort completeness**, not for surveillance-axis hostname extraction. The 252 matthey.com hostnames are vendor-controlled per CP29 §1 strict reading but are corporate-IT infrastructure rather than surveillance-axis attribution anchors.

**Disposition (this cycle):** 252 rows preserved in canonical (per §11 #7 audit-trail discipline; no destructive DELETE) but flagged via `identifiers.notes.scope_review_required=true` + `notes.scope_review_reason` + `notes.scope_review_event='mac183_postship_audit_2026_05_20'` to mark them for Wave I-prime / v1.4.1 operator review. Future Wave-X-style multi-vendor passes MUST apply the SAR-15 axis-filter before iterating.

### Carry-forward

- Wave I-prime / v1.4.1 axis-filter implementation in the per-vendor probe loop
- Operator-decision pass on the 252 JM rows: retain (if matthey.com infra is in-scope for downstream analyses) vs. supersede (if strict surveillance-axis bound applies)
- Any future canonical-lexicon admission record MUST explicitly state the **admission_axis** (surveillance-equipment / industrial-MAC-cohort / drone-MAC-cohort / etc.) in `manufacturers.notes` JSON for downstream extraction passes to filter against

### §11 #11 self-binding satisfied

This SAR-15 entry is the bible-amendment sibling of the MAC-183 post-ship audit (board comment `ddfb43d2-d87a-4fba-a12d-352b539f79fb`, 2026-05-20T00:54:23Z) + post-ship corrective commit `2d17b0d` + the 252-row JM scope-review-flag UPDATE pass.

═══════════════════════════════════════════════════════════════════════

SAR-15.5 — Validator-role independent close-out audit discipline for large-ship cycles

## SAR-15.5 — Validator-role independent close-out audit discipline

### Codification

SAR-15.5 codifies that **large multi-phase ship cycles (10+ phases or 10k+ identifier promotions) SHOULD include a Validator-role independent close-out audit pass** even when the CEO chooses self-execute routing. The Validator role re-derives empirical anchors from raw sandbox artifacts and cross-checks them against the CEO's outputs to catch lookup-table omissions, schema-fab slips, and miscount errors that single-executor passes miss.

### Methodology

Before declaring a large-ship cycle done:

1. **Spawn a Validator agent** (per the lead-orchestrated phases pattern in CLAUDE.md / `~/argus/agents/`).
2. **Validator independently re-derives** the cycle's headline empirical anchors from sandbox artifacts (cumulative-unique-host count, per-vendor breakdown, per-source-class breakdown, per-confidence-band breakdown, total raw_observations FK-chain count, novel-manufacturer-alias diff vs canonical lexicon, etc.).
3. **Validator cross-checks** the CEO-self-executed close report's claims against the independently-derived anchors. Discrepancies of any kind → halt + surface to operator before tag-push.
4. **Validator's report** is appended to the cycle's `INTEGRATION_FINAL_REPORT.md` as a sibling §A1 section.

### Empirical anchor

**Origin** (codified post-MAC-183 board feedback, 2026-05-20): The MAC-183 v1.4.0 cycle self-executed all 10 phases without a Validator role. The Phase 6 enrichment script omitted `honeywell` from its `VENDOR_KEY_TO_CANON` lookup table (because the I.6 vendor_legal_entity_observations file processed during Phase 6 didn't contain Honeywell — the Honeywell observation came from I.7 firmware certs in a separate file). The CEO's close report incorrectly stated "Honeywell not in canonical 51-vendor lexicon — logged for v1.4.1+ admission" when in fact Honeywell IS canonical (mfg_id=211 with existing aliases). A Validator-role independent re-derive of the manufacturer-alias diff would have cross-checked each observed Subject DN O against the actual canonical lexicon (not just the script's lookup table) and caught the slip pre-tag.

**Disposition (this cycle):** Honeywell alias appended post-ship via corrective commit `2d17b0d`. SAR-15.5 codifies the methodology so the next big-ship cycle (e.g., Wave I-prime / v1.5.0) routes through a Validator close-out audit by default.

### Threshold heuristic

Large-ship cycle threshold for SAR-15.5 application:
- ≥10 phases OR
- ≥10,000 identifier-row promotions OR
- ≥3 net-new sources OR
- ≥1 new schema migration

If ANY of these thresholds fire, the Validator close-out audit is required.

### §11 #11 self-binding satisfied

This SAR-15.5 entry is the bible-amendment sibling of SAR-15 + the MAC-183 post-ship audit narrative.

═══════════════════════════════════════════════════════════════════════

## Correction Pass 31 — FCC EAS identifier_type cluster + multi-arm manufacturer hub-and-spoke schema (CP30 reserved)

### Scope

CP31 codifies the FCC EAS grantee identifier_type cluster + the multi-arm manufacturer hub-and-spoke schema. Migration 0025 lands the schema (identifier_type CHECK enum 54 → 56, pair_kind 4 → 5, manufacturers +3 columns + Parrot conversion). 4-path downstream consumer audit at MAC-199 (commit `f9bcf22`) ratifies the runtime semantics. This commit closes the §11 #11 coordinated 2-commit shape per [MAC-197](/MAC/issues/MAC-197) board-accepted plan rev `d59e6af5`.

### CP30 reservation footnote

CP30 remains reserved for `vendor_asn_prefix` + `vendor_controlled_ip` codification per CP29 §3 — Wave I.10/I.13 falsified at zero-evidence, conservative ≥1-empirical-evidence gate holds. CP31 renumbers to skip CP30 without consuming the reservation slot; CP30 holds until ASN-prefix observation surfaces (likely Wave I-prime with RDAP url-pattern fix) and/or cert IP-SAN surface yields non-zero in a future cycle. Numbering precedent: CP29 reserved CP30 for these deferred items, CEO ratification at [MAC-184#comment-25b3ff0b](/MAC/issues/MAC-184#comment-25b3ff0b-f763-4291-90e9-490f1656a2c9) reclaimed CP31 for the FCC EAS cluster, deferred items re-reserved for CP32+ as they materialize.

### §1 — Codified amendments (5)

1. **`identifiers.identifier_type` CHECK enum +2** — `fcc_grantee_code` (3- to 5-char FCC EAS grantee prefix; regulatory entity identifier) + `equipment_class_code` (3-char FCC EAS equipment-class code; paired with grantee per §11 #7 provenance). Migration 0025 carries cumulative **54 → 56** enum values. PROJECT_BIBLE.md §4.4 mapping table updated with 2 new rows; both DROPPED per §11 #13 default at `device_category='unknown'`.

2. **`identifiers.pair_kind` CHECK enum +1** — `fcc_grantee_equipment_class`. Migration 0025 carries cumulative **4 → 5** enum values per CP14 paired-identifier discipline. Pair semantics: `grantee_code` is one identifier row; `equipment_class_code` is a sibling row with `paired_identifier_id` pointing back to the grantee row and `pair_kind='fcc_grantee_equipment_class'`.

3. **`manufacturers` hub-and-spoke schema extension** (3 new columns) — `parent_manufacturer_id INTEGER NULL REFERENCES manufacturers(id)`, `is_arm BOOLEAN NOT NULL DEFAULT 0`, `query_default TEXT NOT NULL DEFAULT 'visible' CHECK (query_default IN ('visible','hidden_arm'))`. Default queries against `manufacturers` MUST filter `WHERE query_default = 'visible'` unless explicitly auditing arm rows. PROJECT_BIBLE.md §4.6 codifies the full default-query rule + future-FK forward-looking binding.

4. **Parrot conversion** (inline data migration) — existing Parrot id=25 remains as hub (`is_arm=0, parent_manufacturer_id=NULL, query_default='visible', primary_category='drone'` preserved); new "Parrot Automotive" arm row inserted at id=222 with `parent_manufacturer_id=25, is_arm=1, query_default='hidden_arm', primary_category='automotive_telematics', aliases='PARROT FAURECIA AUTOMOTIVE SAS,Parrot Faurecia Automotive S.A.S'`.

5. **§8.2 fccid.io source-band re-attestation** — fccid.io (sid=51) is `crowdsourced`; single-source ceiling stays at **conf=75** per CP15. The Phase 7-bis 177-row §7.2 fccid.io cohort lands at conf=75 per row; §8.3 corroboration lift requires non-fccid independent source per CP24 cross-source independence. PROJECT_BIBLE.md §8.2 footnote paragraph appended.

### §2 — Multi-arm vendor schema semantics

Hub rows: `is_arm=0, parent_manufacturer_id=NULL, query_default='visible'`.
Arm rows: `is_arm=1, parent_manufacturer_id=<hub.id>, query_default='hidden_arm'`.

Arm rows surface only via three explicit paths:

- Explicit `WHERE query_default IN ('visible','hidden_arm')` (audit query)
- JOIN through `parent_manufacturer_id` (parent-child traversal)
- Direct FK reference from `identifiers.manufacturer_id` (per-identifier attestation; future-FK migration pending — see §3 below)

**Phase 7-bis attestation routing** (post-CP31, blocked on [MAC-196](/MAC/issues/MAC-196) Numerex close, which is landed at `1344f5d`): 2AG-attested fccid.io rows (177-row §7.2 cohort) point at the arm canonical (Parrot Automotive id=222), NOT the hub. Per-row `device_category` on those identifier rows depends on the §2.1 `identifiers.device_category` CHECK enum admitting an automotive-telematics value — see §6 below for the CP32 follow-up on this enum gap.

### §3 — Downstream consumer audit (4 paths) — post-MAC-199 actual

The CP31 plan §5 prescribed JOIN-based filtering at `exports/argus_export.csv` generator + `exports/lynceus_export.py`. MAC-199 surfaced an **architectural-state correction**:

> `db/validation/export_lynceus.py` (which produces all three exports — `argus_export.csv`, `argus_export_high_confidence.json`, the standard JSON) **does NOT JOIN `manufacturers` today**. The sole canonical-row query reads `identifiers.manufacturer` as denormalized TEXT. No `manufacturer_id` FK exists on `identifiers`.

**Arm-row protection in the v1.4.1 schema is implicit:** no identifier in the current canonical carries `manufacturer = 'Parrot Automotive'`, so the arm canonical cannot leak into any export. Adding `WHERE query_default='visible'` to a JOIN that doesn't exist would be code without effect.

**Forward-looking architectural binding (CP31 surface).** When a future migration adds `identifiers.manufacturer_id` as an FK (pre-staged by CP31's hub-and-spoke columns), the export-path JOIN MUST re-establish the visible-filter as `WHERE m.query_default = 'visible' OR id.manufacturer_id = m.id`. This binding is the canonical architectural commitment of CP31; future migration-design proposals consuming `identifiers.manufacturer_id` must paste-not-cite this requirement in their dispatch §1. Documented at `_phase_cp31_implementation/manufacturers_query_audit.md` §E in MAC-199 commit `f9bcf22`.

**Path-by-path post-MAC-199 disposition:**

1. **`exports/argus_export.csv` generator** — denormalized TEXT reads `identifiers.manufacturer`; no JOIN, no filter required at v1.4.1 schema. Future-FK forward-looking binding documented above.
2. **`exports/lynceus_export.py`** — same denormalized read; arm canonical absent from current data shape so arm rows DROP from high-conf JSON implicitly. Test §B in `tests/test_cp31_consumer_audit.py` synthesizes export queries to confirm arm canonical absence.
3. **`argus_cli.py status`** — MAC-198 added hub+arm split reporting line: `Manufacturers: 51 visible (hub) + 1 hidden (arm) = 52 total`. MAC-199 cross-verified.
4. **`project_knowledge_search` / live-query path audit** — 28 occurrences of `FROM manufacturers` / `JOIN manufacturers` classified at MAC-199. 4 hub-only live-query lexicon enumeration sites received the `WHERE query_default = 'visible'` filter in commit `f9bcf22`:
    - `db/validation/phase3_inference_candidates.py:730`
    - `db/validation/sar8_bulk_stage.py:134`
    - `db/sources/usaspending.py:391`
    - `db/validation/mac101_item_a_registry_xcheck.py:135`

   2 by-name lookup sites left neutral (caller controls intent — `db/validation/coverage_matrix.py:412`, `db/validation/wave_a_first_promotion.py:90`). 17 admission/promotion one-shot scripts left unfiltered (arms participate by design in admission flows). 2 migration+test files out of live-query scope. 2 doc references with no code change. 1 already-correct (argus_cli.py — MAC-198 split reporting).

### §4 — Plan baseline-count correction (Validator MAC-199 paste-not-cite nit)

The CP31 plan §1 #1 stated "53 total values (51 CP29 + 2 CP31)" for the `identifiers.identifier_type` enum cumulative-sweep. Live post-CP31 count is **56 values (54 pre-CP31 + 2 CP31)**, verified via `sqlite_master` CHECK enum parse against `~/argus/db/argus.db` post-migration 0025. CP29 §1 codified 3 net-new identifier_types (`vendor_controlled_hostname`, `vendor_cloud_endpoint_url`, `vendor_controlled_hostname_deprecated`) → migration 0024 extended the CHECK enum 51 → 54. The CP31 plan misstated the pre-CP31 baseline as 51 (stale by one CP cycle). Migration 0025's `+2 addition` is correct; the cumulative-sweep count was wrong. Non-blocking discipline note; surfaced via Validator MAC-199 paste-not-cite preamble per SAR-13 + §3399. Carry-forward refinement: dispatch authoring MUST DB-verify the pre-cycle baseline count via `sqlite_master` CHECK enum parse before stating cumulative totals (sub-rule of SAR-13).

### §5 — Sibling commits + empirical anchors

**Sibling commits (this CP cycle):**

- **Migration 0025 + Parrot conversion** (MAC-198 DBArchitect): commit `40b166e`
- **4-path consumer audit + 8 new tests** (MAC-199 Validator): commit `f9bcf22`
- **This bible amendment commit** (MAC-197 CEO close): commit `<this-commit>`

**Empirical anchors:**

- 2AG = Parrot Faurecia Automotive SAS (FCC EAS database); arm row id=222 codified
- 40 char-prefix shape: 3-5 char `fcc_grantee_code` + 3-char `equipment_class_code` (FCC ID composition `grantee_code + product_code`; equipment_class_code sibling to grantee — paired via `pair_kind='fcc_grantee_equipment_class'`)
- Single §7.0 api.dbeta.me Parrot-hub attestation pre-CP31 (no arm exposure risk at v1.4.1 ship-state)
- 177-row Phase 7-bis §7.2 fccid.io cohort (out-of-scope future ship; unblocked post-this-CP + MAC-196 landed at `1344f5d`)
- Board disposition: [MAC-184 comment 25b3ff0b](/MAC/issues/MAC-184#comment-25b3ff0b-f763-4291-90e9-490f1656a2c9) (Option 2C hub-and-spoke ratified)
- Live DB verification post-migration 0025: 56 identifier_types, 5 pair_kinds, 52 mfgs (51 hub + 1 arm), schema_version=25

### §6 — Carry-forward (CP32 candidates; NOT codified here)

Surfaced by MAC-199 + held for CP32 (or single-purpose follow-ups) per CEO disposition. None of these block v1.4.1 ship; all are forward-looking discipline items:

1. **§2.1 `device_category` CHECK enum extension** — admit `automotive_telematics` (or equivalent canonical) so 2AG-attested fccid.io identifiers can land at a §2.1-compliant `device_category` matching their arm's `primary_category`. The §2.1 enum is owned by `identifiers.device_category` (migration 0001; 12 values currently); `manufacturers.primary_category` carries NO CHECK constraint per MAC-198 SKIP decision so the arm's `primary_category='automotive_telematics'` was admissible without enum extension. Phase 7-bis 177-row cohort attestation routing WILL hit this gap at promotion-time; CP32 (or single-purpose enum-extension migration) required BEFORE Phase 7-bis. Test workaround at MAC-199 §C #4 used `device_category='drone'` to honor plan-intent within current schema constraints (arm-ness does not auto-exclude; per-row category check is independent of hub-vs-arm).

2. **Future `identifiers.manufacturer_id` FK migration** — pre-staged by CP31 hub-and-spoke columns. When this migration lands (no scheduled cycle; opportunistic when the next manufacturer-attribution refactor surfaces), the export-path JOIN MUST re-establish the visible-filter per §3 above. Migration-time binding text: `WHERE m.query_default = 'visible' OR id.manufacturer_id = m.id`. This carry-forward IS the architectural contract that gives CP31's hub-and-spoke columns their downstream effect.

3. **Stale `tests/test_type_mapping_covers_every_identifier_type`** — pre-existing failure surfaced by MAC-199 full-suite run (523 passed, 1 failed; failure pre-dates MAC-199). 5 types missing from `IDENTIFIER_TYPE_TO_PATTERN_TYPE ∪ DROPPED_REASONS` mapping table: 3 CP29 hostname types (`vendor_controlled_hostname`, `vendor_cloud_endpoint_url`, `vendor_controlled_hostname_deprecated`) + 2 CP31 FCC EAS types (`fcc_grantee_code`, `equipment_class_code`). Currently masked by §11 #13 unknown-category gate at export-time. CP32 (or single-purpose mapping-table sync) updates the lookup table to match the live CHECK enum.

4. **Exports/ regen post-MAC-196 + CP31** — `argus_export.csv` + `argus_export_high_confidence.json` were last regenerated 2026-05-20T00:43:59Z, pre-MAC-196 Numerex admission + pre-MAC-198 migration 0025. Operator-decision item: regen post-v1.4.1 ship to bring exports current with canonical DB state. Not a CP-class amendment; queued as a ship-prep task.

5. **Multi-arm vendor backlog** — Cisco/Meraki, Motorola Solutions, Harris RF vs Harris Aerial, Honeywell ACS division. Backlogged for arm-split at v1.4.2+ as identifiers surface attesting to specific arms; no urgency. CP31 ships only Parrot conversion; other splits ship per evidence arrival.

### §7 — Architectural firsts (CP31 cycle)

1. **First multi-arm hub-and-spoke schema** in the framework (3 net-new columns; first FK self-reference on `manufacturers`).
2. **First arm-canonical row** in the framework (`Parrot Automotive` id=222, `query_default='hidden_arm'`).
3. **First `pair_kind='fcc_grantee_equipment_class'` paired-identifier** (extends CP14 paired-identifier discipline to regulatory entity pairing).
4. **First explicit forward-looking FK architectural binding** in a CP memo (§3 + §6.2 above); CP31 codifies what a *future* migration MUST do, not what this cycle does.
5. **First "implicit protection via denormalized data shape"** documented as a discipline pattern — current-state protection is genuine but stops working at a future-FK migration; CP31 makes the binding explicit so the future migration cannot silently regress.
6. **First Validator-paste-not-cite-caught dispatch baseline arithmetic error** propagated into a CP memo (Validator's 51→54 nit at §4 above caught at MAC-199 close, not at plan-confirmation gate).

### §11 #11 self-binding satisfied

This CP31 entry is the §11 #11 amendment-log pairing for migration 0025 (`db/migrations/0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke.sql` at commit `40b166e`) + 4-path consumer audit at commit `f9bcf22` + this bible commit. CP-anchor: this commit + [MAC-197](/MAC/issues/MAC-197) closure. Schema version bumps 24 → 25.

═══════════════════════════════════════════════════════════════════════

## Correction Pass 32 — Stage 2 Phase 1 bundled codification (mig-0026 device_category extension + 9 narrative/discipline sub-sections)

### Scope

CP32 codifies a single bundled amendment with 10 sub-sections covering the Stage 2 Phase 1 dispatch ([MAC-220](/MAC/issues/MAC-220) parent [MAC-219](/MAC/issues/MAC-219)). Migration 0026 lands a single schema-level mutation — the `device_category` CHECK enum extension `+1 automotive_telematics` applied to BOTH `identifiers.device_category` and `behavioral_signatures.device_category`. The remaining nine sub-sections are narrative/discipline codifications folding three pending CP32 candidates (#6/#7/#8 from Stage 1 — MAC-206/MAC-207/MAC-209) plus six new amendments surfaced at MAC-217/MAC-198/MAC-199 close. Schema_version bumps 25 → 26.

### CP30 reservation footnote (preserved unchanged)

CP30 remains reserved for `vendor_asn_prefix` + `vendor_controlled_ip` codification per CP29 §3. CP32 numbering does NOT consume the CP30 reservation slot; CP30 holds until ASN-prefix observation surfaces (likely Wave I-prime with RDAP url-pattern fix) and/or cert IP-SAN surface yields non-zero in a future cycle. Precedent: CP31 already skipped CP30 by the same convention; CP32 carries the convention forward.

### Pre-commit Na_ sub-slot convention (codified inline at CP32 §1, applied at Phase 1)

Data-only addendum migrations sharing a numeric slot with a schema-mutating migration use a sub-letter suffix (`Na_…`) and apply after the main `N_` slot (lexical: `_` < `a`). Phase 1 reclassification of `0026_phase10_vendor_apk_sources_admission.sql` → `0026a_phase10_vendor_apk_sources_admission.sql` is the first application of this convention; no retroactive sweep of prior data-only entries is implied. The convention frees the `0026_` slot for the schema-mutating CP32 §1 migration without renumbering downstream cycles (which would have required per-line edits across the dispatch + bible text). Filename↔schema_version 1:1 holds for schema-mutating migrations (`N_…`); data-only addenda live alongside via `Na_/Nb_/…`. Rename commit: `398c8b8` (this branch).

### §1 — Codified amendments (10 sub-sections)

**Status legend:** **CODIFIED+LANDS** = bible text change + schema/code mutation in this CP. **CODIFIED** = bible text change only (narrative/discipline). **BINDING** = architectural commitment for a future migration (no current schema change).

1. **CP32 §1 — `device_category` CHECK enum extension `+1 automotive_telematics`** *(CODIFIED+LANDS)*

   Mechanism: migration 0026 (`db/migrations/0026_cp32_device_category_automotive_telematics.sql`) rebuilds BOTH `identifiers.device_category` (12 → 13) and `behavioral_signatures.device_category` (12 → 13). Per CEO pre-clearance (Phase 0 evidence `_preflight/preflight_evidence.md`): dual-table extend maintains enum parity across the two CHECK literals that share the conceptual device_category vocabulary. Downstream consumers (Lynceus, exports, coverage matrix) treat `device_category` as a single vocabulary regardless of host table.

   Origin: CP31 §6 #1 carry-forward — surfaced at MAC-199 for Phase 7-bis 177-row §7.2 fccid.io 2AG-attested cohort (Parrot Automotive arm canonical id=222 holds `primary_category='automotive_telematics'` on `manufacturers.primary_category` per CP31 inline conversion; identifier rows promoting to that arm need `device_category` to match).

   Affected paths: `db/migrations/0026_cp32_device_category_automotive_telematics.sql` (new), `PROJECT_BIBLE.md` §2.1 (vocabulary table +1 row), `db/argus.db` (schema=26, 0 row promotions land in this CP — schema slot opens; promotion is future evidence-arrival concern).

   Phase 1 audit (live DB post-mig-0026): `PRAGMA integrity_check=ok`, `MAX(schema_version.version)=26`, `identifiers` active=34964 unchanged, total=35310 unchanged, `behavioral_signatures`=201 unchanged, 4 self-loops preserved, `identifier_type` CHECK enum=56 (CP31 preserved), `pair_kind` CHECK enum=5 (CP31 preserved), `manufacturers` CP31 columns (`parent_manufacturer_id`, `is_arm`, `query_default`) preserved. Idempotency: 2nd-run produces byte-identical sqlite_master + data hashes; see `_phase_1_cp32_codification/idempotency_2nd_run.txt`.

2. **CP32 §2 — Future `identifiers.manufacturer_id` FK migration (architectural binding only)** *(BINDING)*

   Mechanism: no schema mutation in CP32. Codifies the architectural binding that when a future migration adds `identifiers.manufacturer_id INTEGER NULL REFERENCES manufacturers(id)`, every export-path JOIN MUST re-establish the visible-filter as `WHERE m.query_default = 'visible' OR id.manufacturer_id = m.id` per CP31 §3 (4-path downstream consumer audit). Status: BINDING only; FK migration is v1.5.0+ pending evidence-arrival (no current identifier row carries an arm-canonical manufacturer name as denormalized TEXT, so the arm-row protection is implicit at v1.4.1; future-FK migration MUST re-establish it explicitly).

   Origin: CP31 §6 #2 carry-forward; PROJECT_BIBLE.md §4.4 manufacturer architecture section already carries the binding text via CP31; CP32 §2 codifies it as a numbered amendment.

   Affected paths: `PROJECT_BIBLE.md` §4.4 (text already present per CP31 — CP32 §2 codifies the architectural status without further text mutation).

3. **CP32 §3 — Retire stale `test_type_mapping_covers_every_identifier_type`** *(CODIFIED+LANDS)*

   Mechanism: refactor `tests/test_export_lynceus.py::test_type_mapping_covers_every_identifier_type` from a hardcoded mig-0019 48-value `expected` set to a dynamic read of the live `identifier_type` CHECK enum from sqlite_master at test runtime. The new test asserts that every value in the live enum has a §4.4 disposition surface — either MAP (in `IDENTIFIER_TYPE_TO_PATTERN_TYPE`) or DROPPED (in `DROPPED_REASONS`). 5 currently-missing values land in `DROPPED_REASONS` as stubs: `vendor_controlled_hostname` (CP29), `vendor_cloud_endpoint_url` (CP29), `vendor_controlled_hostname_deprecated` (CP29), `fcc_grantee_code` (CP31), `equipment_class_code` (CP31). All 5 mirror verbatim into `coverage_matrix.py::DROPPED_REASONS` per the reconcile-gate parity contract; 5 zero-init bin keys added to `export_lynceus.py`'s bins dict (coverage_matrix.py auto-initializes via the existing `for cp16_bin in DROPPED_REASONS.values(): bins[cp16_bin] = 0` loop).

   Disposition: all 5 stubs are DROPPED-class pending §4.4 MAP ratification at a future CP, matching MAC-109/MAC-117/MAC-181 precedent. All currently-live rows with these identifier_types carry `device_category='unknown'` and tally via the §11 #13 unknown-category carve-out, so the addition does not change any live row's bin classification.

   Origin: CP31 §6 #3 carry-forward — pre-existing test failure surfaced by MAC-199 full-suite run (523 passed, 1 failed; failure pre-dated MAC-199).

   Affected paths: `tests/test_export_lynceus.py`, `db/validation/export_lynceus.py`, `db/validation/coverage_matrix.py`. PROJECT_BIBLE.md: no text change (test hygiene).

   Verified: 524/524 repo test suite passes post-refactor.

4. **CP32 §4 — Multi-arm vendor backlog admission cadence** *(CODIFIED — narrative)*

   Mechanism: `PROJECT_BIBLE.md` §4.6 (multi-arm hub-and-spoke) gains a sub-rule on admission cadence — `hidden_arm` rows admit only when identifier-rows attest to specific arms (not pre-emptive). The backlog (Cisco/Meraki, Motorola Solutions, Harris RF vs Harris Aerial, Honeywell ACS division) does NOT auto-promote to arm splits on a schedule; arm splits ship only when concrete identifier evidence surfaces attesting to a specific arm. CP31 shipped only Parrot conversion because that was the only multi-arm case with concrete evidence (Parrot Faurecia Automotive S.A.S aliases on the existing Parrot id=25 row).

   Origin: CP31 §6 #5 carry-forward.

   Affected paths: `PROJECT_BIBLE.md` §4.6 (sub-rule added).

5. **CP32 §5 — Lynceus exports regen cadence** *(CODIFIED — narrative)*

   Mechanism: `PROJECT_BIBLE.md` §7.5 (export discipline) gains a sub-rule — `argus_export.csv` + `argus_export.json` + `argus_export_high_confidence.json` regenerate per v1.4.x bundle, not per data-touching commit. The per-bundle cadence avoids export-noise commits between substantive bundle landings; consumers can rely on a stable export shape that tracks the canonical-DB bundle close (not a moving target across mid-bundle micro-commits).

   Origin: CP31 §6 #4 carry-forward — MAC-209 Phase 12 surfaced the cadence question (exports were last regenerated 2026-05-20T00:43:59Z, pre-MAC-196 + pre-MAC-198; v1.4.1 ship-prep included exports regen as a ship-prep task, not a continuous concern).

   Affected paths: `PROJECT_BIBLE.md` §7.5 (sub-rule added).

6. **CP32 §6 — §11 audit invariant — session-bounded admission carve-out + class-2 deferred → MAC-208 fork language** *(CODIFIED)*

   Mechanism: `PROJECT_BIBLE.md` §11 #17 sub-rule clarification (added at MAC-206 in Stage 1) is now first-class codified. CP32 §6 confirms the class-2 deferred → MAC-208 fork language already landed at Stage 1 inline §11 #17 text (5 `identifiers` rows ids 554-558 RAVEN_*, plus 1 `sources` row sid=7, all `{json}<concat>text` defects). The §11 #17 wave_g_pre_v1 21-row carve-out invariant — every `identifiers` row has a `raw_observations` predecessor OR carries `notes.direct_admission_carve_out=true` referencing `sources.notes`-level provenance — is reaffirmed as session-bounded and explicitly NOT a future admission pathway. The Stage 1 inline edit at PROJECT_BIBLE.md §11 #17 footer reference "(CP32 candidate #6 — pending CP32 bundle landing)" is replaced this CP with "(CP32 §6 — codified)".

   Origin: [MAC-206](/MAC/issues/MAC-206) Phase 10d Run 3 — β.3c CEO ratification at [MAC-206#90e6b70f](/MAC/issues/MAC-206#comment-90e6b70f-9f4d-4374-9655-d498e56982d2) 2026-05-20; companion [MAC-205](/MAC/issues/MAC-205) 21-row enumeration + Option A.

   Affected paths: `PROJECT_BIBLE.md` §11 #17 (status pointer flip from candidate → codified).

   Empirical anchor: 21 rows UPDATEd via `json_patch(notes, ?)` (first-run affected=21; idempotency re-run affected=0); composite WHERE: `id IN (533..553) AND source_url IN (<flock_url>, <getac_url>) AND json_extract(notes,'$.direct_admission_carve_out') IS NULL`. Backup pre-carve-out: `db/argus.db.mac206_pre_carveout_backup` sha256=`f346940861995b740c301fc520aab3500e2acebb158fcbe7aecb88f088c51bab`.

7. **CP32 §7 — Sandbox-absence HALT-fast-path default sub-rule** *(CODIFIED)*

   Mechanism: `PROJECT_BIBLE.md` §11 (dispatch-discipline envelope) gains a sub-rule — dispatch plan-inputs in cleaned `~/argus-internal/` (or analogous workspace-only) sandboxes → HALT-fast-path = default disposition, assuming the dispatch body anticipates this case with an explicit fast-path clause. The sandbox-clean condition is a discoverable precondition during pre-flight, not a mid-flight surprise; ratification can happen at HALT-comment time without per-record evidence enumeration. Forward-looking sub-rule: future dispatches that depend on `~/argus-internal/`-resident plan-inputs **SHOULD** specify a snapshot path under a versioned location (the argus repo) at dispatch time, with a fallback fast-path clause when the snapshot was not captured.

   Origin: [MAC-207](/MAC/issues/MAC-207) Phase 11 HALT ratified at [MAC-207#c4ec8740](/MAC/issues/MAC-207#comment-c4ec8740-36e4-42a9-bac6-cadd035bb110) 2026-05-21 (Option A all-73 DROP single-cycle close). Precedent: [MAC-200](/MAC/issues/MAC-200) §9.2.c first surfaced the same `~/argus-internal/wave_i_pre_v1/wave_i_13_hard_id_v2/` sandbox-absence (commit `518bbcd`); CP32 §7 codifies the discipline pattern MAC-200 exercised informally (n=2 precedent: MAC-200 + MAC-207).

   Affected paths: `PROJECT_BIBLE.md` §11 (sub-rule added as new bullet under dispatch-discipline section).

8. **CP32 §8 — MAC-206 carve-out export-drop attribution rule** *(CODIFIED + code stamp)*

   Mechanism: `PROJECT_BIBLE.md` §7.5 gains a sub-rule — drop attributions in `_meta.dropped_in_export` carry a specific rule reference. CP32 §8 codifies the specific case of the MAC-206 carve-out: the 21 wave_g_pre_v1 carve-out rows drop from Lynceus exports via the **§4.4 identifier_type → pattern_type mapping gate**, NOT via CP19 §8.2 crowdsourced-ceiling. Their `identifier_type` values (`ble_service`, `ble_characteristic`, `ble_local_name`, `product_family_codename`) are not in `IDENTIFIER_TYPE_TO_PATTERN_TYPE`, so they tally under `_meta.dropped_in_export.type_mapping_unmapped`. Their `source_type='manufacturer_app'` and confidence 82/87/92 are above all relevant floors — CP19 simply does not engage.

   Forward-looking implication: if a future cycle admits any of these 4 identifier_types into `IDENTIFIER_TYPE_TO_PATTERN_TYPE` (e.g., to surface BLE-service signatures in Lynceus scans), the carve-out rows WILL surface in exports at their current confidence. That admission MUST be deliberately coordinated with a §11 #17 applicability re-review.

   This is the first post-execution dispatch-reasoning correction landed as a CP entry rather than a feedback memory — prior dispatch-reasoning errors (e.g., MAC-176 forecast error on Johnson Matthey MA-M routing) landed as feedback memories; this one earns a CP entry because it composes directly with §11 #17 and constrains future BLE-service identifier_type admission decisions.

   Origin: [MAC-209](/MAC/issues/MAC-209) Phase 12 spot-check surfaced the mechanism correction; [[feedback_db_verify_dispatch_claims]] is the meta-discipline anchor.

   Affected paths: `PROJECT_BIBLE.md` §7.5 (sub-rule added); export-generator code stamp (no code change required at CP32 time — the export generators already emit `_meta.dropped_in_export.type_mapping_unmapped` bin entries per the CP16 split-structure; the rule reference is documentation-discipline at audit-time).

9. **CP32 §9 — `superseded_by` tri-state semantic clarification** *(CODIFIED)*

   Mechanism: `PROJECT_BIBLE.md` §4.4 gains a sub-rule clarifying that `identifiers.superseded_by` carries three distinct semantics:
   - **`NULL`** → row is **active** (canonical contract per §4.1; current count: 34,964 of 35,310 total).
   - **`<other_id>`** → row is **superseded by a successor** identifier row (the canonical merge semantic; 342 rows; e.g., dedup §8.3 merge-with-supersession; deprecated MACs).
   - **`<self_id>` (self-loop)** → row is **withdrawn without successor** (the §11 #3 PII-demotion semantic; 4 rows; MAC-217 Track B Jacobs `*.escg.jacobs.com` PII demotes — rows are §8.2 demoted to confidence=0 and self-loop-tagged so they're never surfaced as active and never point to an inappropriate successor; the self-loop is the "no successor exists" signal).

   This tri-state was implicit in the schema and surfaced through the MAC-217 Track B 4 self-loops; CP32 §9 makes it explicit so future consumer audits, JOIN logic, and active-set queries handle all three cases correctly. Active-set query convention: `WHERE superseded_by IS NULL` (the canonical filter; both `<other_id>` and `<self_id>` rows are non-active). Withdrawn-without-successor query convention: `WHERE superseded_by = id`.

   Origin: MAC-217 Track B (4 PII demotes); cross-ref `feedback_superseded_by_tri_semantic_post_mac217.md`.

   Affected paths: `PROJECT_BIBLE.md` §4.4 (sub-rule added). No schema mutation — the existing `superseded_by INTEGER REFERENCES identifiers(id) ON DELETE SET NULL` column has always admitted all three cases.

10. **CP32 §10 — §11 #3 export-time generator post-condition guard pattern** *(CODIFIED + code pattern reference)*

    Mechanism: `PROJECT_BIBLE.md` §11 #3 (PII discipline) gains a sub-rule — export generators MUST include post-condition guards for hard-rule-bound content shapes. Canonical template: `_assert_no_email_pii(path)` per MAC-217 implementation at 6 emission call sites (covering all 3 Lynceus export shapes × the both-floors-applied audit). The guard runs AFTER the export file is written, re-reads the file, and raises `Halt` if any post-write content violates the hard-rule predicate (in this case, regex-detected email PII).

    Forward-looking sub-rule: any §11 hard-rule that constrains export content shape SHOULD have a paired `_assert_no_<rule>_<violation>(path)` post-condition guard at every emission call site. This is the first framework-level codification of the pattern — prior PII-bounded checks lived only at the row-classification gate (`_classify_row` → drop bin), which is necessary but not sufficient: a bug in the classification gate or a future code-path that bypasses the gate (e.g., a custom export) would leak PII. The post-condition guard is defense-in-depth — it catches both classification-gate bugs AND new-code-path bypasses.

    Origin: [MAC-217](/MAC/issues/MAC-217) Phase 5 (Stage 1) — `_assert_no_email_pii(path)` implemented at 6 emission call sites in the §8.2 PII-strip commit (`50b8232`); cross-ref to the 12 source_excerpt redactions + 4 VCH demotions + this guard pattern.

    Affected paths: `PROJECT_BIBLE.md` §11 #3 (sub-rule added; code pattern reference). No new code in this CP — the guard pattern already lives at `db/validation/export_lynceus.py` post `50b8232`; CP32 §10 codifies it as a framework-level discipline rule.

### §2 — Architectural firsts (CP32 cycle)

1. **First `Na_` sub-slot convention** — data-only addendum migrations sharing a numeric slot with a schema-mutating migration use `Na_…` sub-letter suffix; CP32 §1 applies it to the 0026 slot (the first sub-slot use in the framework).
2. **First dual-table `device_category` CHECK enum sweep** — CP21 cumulative-full-enum spirit applied across two separate CHECK literals (`identifiers.device_category` + `behavioral_signatures.device_category`) in a single migration, maintaining enum parity for downstream consumers that treat the vocabulary as conceptually unified.
3. **First codified HALT-fast-path discipline pattern** (CP32 §7) — prior precedent (MAC-200 §9.2.c) exercised the pattern informally; CP32 §7 elevates it to a named discipline rule.
4. **First post-execution dispatch-reasoning correction landed as a CP entry** (CP32 §8) — prior dispatch-reasoning errors landed as feedback memories; CP32 §8 earns a CP entry because it composes with §11 #17 and constrains future identifier_type admission decisions.
5. **First framework-level export-time generator post-condition guard codification** (CP32 §10) — prior PII-bounded checks lived at the row-classification gate only; the post-condition guard is defense-in-depth against classification-gate bugs and new-code-path bypasses.
6. **First codified tri-state semantic on a SET-NULL FK column** (CP32 §9) — `identifiers.superseded_by` carries three distinct semantics (NULL/other-id/self-id) made explicit via bible text, no schema mutation.
7. **First bundled CP entry folding pre-existing Stage 1 candidate entries** — CP32 §6/§7/§8 each fold a previously-authored "CP32 Candidate #6/#7/#8" entry that anticipated the bundle landing; the original candidates land here as numbered sub-sections per the candidates' explicit "If CP32 lands as a single bundle commit, this entry's title will be renumbered to a sub-section" anticipation.

### §3 — Sibling commits + cross-references

**Sibling commits (this CP cycle, Phase 1 — MAC-220):**

- **Commit 1 — `git mv 0026_phase10_*.sql 0026a_phase10_*.sql`** (Na_ sub-slot rename): `398c8b8`
- **Commit 2 — Migration 0026 CP32 §1 schema landing**: `b0c5c9f`
- **Commit 3 — CP32 §3 test refactor + DROPPED_REASONS stubs**: `ed3f75d`
- **Commit 4 — This bible amendment + PROJECT_BIBLE.md text updates**: `<this-commit>`

**Cross-references:**

- [MAC-219](/MAC/issues/MAC-219) (v1.4.1 Stage 2 — CP32 + Docs + Final Tag parent)
- [MAC-220](/MAC/issues/MAC-220) (Phase 1 — CP32 codification + mig-0026 + test refactor + bible — THIS dispatch)
- [MAC-220 comment 5bb44924](/MAC/issues/MAC-220#comment-5bb44924-20fe-45b1-93bf-35ecdda2ee81) (CEO Option A-minimal disposition: 0026a_ rename + Na_ sub-slot convention)
- [MAC-205](/MAC/issues/MAC-205) + [MAC-206](/MAC/issues/MAC-206) — CP32 §6 wave_g_pre_v1 carve-out lineage
- [MAC-207](/MAC/issues/MAC-207) — CP32 §7 HALT-fast-path codification lineage
- [MAC-209](/MAC/issues/MAC-209) — CP32 §8 export-drop attribution lineage
- [MAC-217](/MAC/issues/MAC-217) — CP32 §9 tri-state semantic anchor (Track B 4 PII demotes) + CP32 §10 `_assert_no_email_pii(path)` precedent (commit `50b8232`)
- [MAC-197](/MAC/issues/MAC-197) (CP31 — origin of §6 #1-#5 carry-forwards now codified at CP32 §1/§2/§3/§4/§5)
- `db/migrations/0025_cp31_*.sql` (immediate-prior schema-mutating migration; baseline for CP32 §1 dual-table sweep)
- `db/migrations/0026_cp32_device_category_automotive_telematics.sql` (this CP — schema-version 26)
- `db/migrations/0026a_phase10_*.sql` (renamed from `0026_phase10_*.sql` at commit `398c8b8`; Na_ sub-slot precedent)

**Phase 1 audit deliverables:** `~/argus-internal/wave_i_4_1_integration_stage_2/_phase_1_cp32_codification/` (sqlite_master_before.txt, sqlite_master_after.txt, idempotency_2nd_run.txt, post_state_anchors.md, commit_log.md) + `_heartbeats/hb_001_cp32_codification_complete.md`.

### §4 — §11 envelope satisfied

- **§11 #1 (no fabrication):** all 10 sub-sections trace to dispatch §1.1 origin; CP32 §1 cites the CP31 (mig-0025) Parrot Automotive arm row admission as the empirical anchor for `automotive_telematics`; no row-level promotions land in CP32.
- **§11 #3 (PII discipline):** CP32 §10 strengthens the discipline by codifying the post-condition guard pattern. Phase 1 touches no identifier rows with PII; synthetic poison re-test deferred to Phase 4.
- **§11 #5 (phase boundaries):** mig-0026 is schema slot only; row-level use of `automotive_telematics` is a future Stage-2 validator concern (future dispatch).
- **§11 #7 (no promotion without provenance):** Phase 1 promotes no new identifiers.
- **§11 #8 (no confidence drift):** no §8.3 lifts.
- **§11 #11 (amendment-log discipline):** single bundled CP32 entry, 10 sub-sections, pre-existing Stage 1 candidates folded per their anticipation.
- **§11 anti-fabrication on CHECK constraints (SAR-13 §3399 PRAGMA-first discipline):** applied to CP32 §1 — pre-migration sqlite_master capture verifies the 12-value baseline on BOTH tables before the rebuild; post-migration capture verifies the 13-value result + preservation of all other CHECK constraints (identifier_type 56-value, pair_kind 5-value, source_type 10-value, cellular_generation 4-value, source_excerpt length, confidence range, query_default 2-value).

### §11 #11 self-binding satisfied

This CP32 entry is the §11 #11 amendment-log pairing for migration 0026 (`db/migrations/0026_cp32_device_category_automotive_telematics.sql` at commit `b0c5c9f`) + the 0026a_ rename (commit `398c8b8`) + the test refactor (commit `ed3f75d`) + this bible commit. CP-anchor: this commit + [MAC-220](/MAC/issues/MAC-220) closure. Schema version bumps 25 → 26.

═══════════════════════════════════════════════════════════════════════

## Deferral Note 1 — MAC-203 §44.3 Honeywell product nomenclature corpus deferred (no §11 #7 evidence trail surviving)

**Date:** 2026-05-20
**Commit:** `<this-commit>` — `docs(bible): MAC-203 Deferral Note 1 — §44.3 Honeywell product nomenclature corpus (no surviving §11 #7 evidence)` (self-referential per CP31 §5 precedent; resolve via `git log BIBLE_AMENDMENTS.md`)
**Source:** [MAC-203](/MAC/issues/MAC-203) Validator verdict comment `0ac4e5ae` (Path 1 — intentional scope narrowing — confirmed) on top of [MAC-200](/MAC/issues/MAC-200) §9.2.c Phase 9 Wave I.13 carry-forward heartbeat surface.
**Bible edit:** NONE — pure deferral note per §11 #11 amendment-log discipline for deliberate-deferral path. No PROJECT_BIBLE.md text mutated; no schema mutation; no DB writes. Schema_version unchanged at 25.

### §1 — What was deferred

Wave I.14a runguide §44.3 (`~/argus-internal/new data 5.20/wave_i_14a_canonical_remine_runguide.md` lines 273-294) proposed a structured `manufacturers.notes.product_families` enrichment on the v1.4.1 Honeywell admission with the following shape:

```json
{
  "target_canonical_name": "Honeywell International Inc.",
  "proposed_notes_enrichment": {
    "product_families": [
      {"family": "CT_series_mobile_computers", "models": ["CT40", "CT45", "CT60", "CT30P"], "category": "rugged_android_mobile_computer"},
      {"family": "CN_series", "models": ["CN80", "CN85"], "category": "rugged_handheld"},
      {"family": "VM_series", "models": ["VM1A"], "category": "vehicle_mount_computer"},
      {"family": "CK_series", "models": ["CK65"], "category": "mobile_computer"}
    ],
    "codenames": ["hon660", "hon4290"],
    "codesign_branches": ["dubai_android_releasekey"],
    "evidence": "Wave I.13 firmware extraction (~/argus-internal/wave_i_pre_v1/wave_i_13_hard_id_v2/per_corpus/honeywell_firmware_outer/)"
  }
}
```

The §44.3 spec's prescribed output artifact (`diagnostic_outputs/honeywell_product_nomenclature_enrichment.json`) was NEVER materialized — `find /home/kev/argus /home/kev/argus-internal -name 'honeywell_product_nomenclature_enrichment*'` returns zero hits.

### §2 — Why it was deferred (Path 1 — intentional scope narrowing — confirmed)

Phase 8 ([MAC-195](/MAC/issues/MAC-195)) was dispatched with a three-item scope, all of which were applied as written:

1. **Honeywell admission** to canonical `manufacturers` lexicon (51 → 52 rows).
2. **§6.4 alias enrichment** — `HoneywellSecurityGroup` tier-3 `ct_log_common_name` appended to `Honeywell.aliases` (key: `mac195_alias_enrichment`).
3. **§6.5 cert-issuer vendor row enrichment** — top 5 issuer organizations from the 3,628 ct_log certs; ACS division attestation (Honeywell ACS / `CN=Honeywell CodeSign RSA CA` / `dubai_android_releasekey` / `CT45`+`CT40` device models) appended to `Honeywell.notes` (keys: `cert_issuer_supply_chain` + `honeywell_acs_division_attestation`).

`product_families` / `codenames` / `codesign_branches` (plural) were **never** in the MAC-195 dispatch scope. `_phase_8_honeywell_admission/apply_phase_8_honeywell_landing.py` grep confirms zero references to any of those keys. The CT45+CT40 device-model attestation in the dispatch is framed as a sub-field of the cert-chain attestation under §6.5, NOT as a stand-alone product-nomenclature enrichment.

The §44.3 spec is a **Wave I.14a remine sub-pass proposal** authored as a forward-looking enrichment scaffold, not a Phase 8 deliverable. The v1.4.1 Stage 1 integration tree (MAC-184 → MAC-195) routed only the §6.4 alias + §6.5 cert-chain subsets through Phase 8.

### §3 — Why it cannot be re-applied at v1.4.1 ship (§11 #7 halt fires)

The §44.3-cited evidence path is **absent** from the filesystem:

```text
$ ls /home/kev/argus-internal/wave_i_pre_v1/
ls: cannot access '/home/kev/argus-internal/wave_i_pre_v1/': No such file or directory
```

This is consistent with the MAC-200 §9.1.d confirmation that the Wave I.13 sandbox does not survive on this filesystem.

Surviving Wave I.7/I.8 firmware-cert evidence (the layer that backed the §6.5 cert-chain attestation already absorbed at MAC-195) attests **CT45+CT40 only** (already integrated under `notes.honeywell_acs_division_attestation[0].device_models_attested`). No surviving extraction surface attests `CT60`, `CT30P`, `CN80`, `CN85`, `VM1A`, `CK65`, `hon660`, or `hon4290`.

The MAC-200 heartbeat and the §44.3 runguide itself are derivative/planning artifacts, NOT §11 #7-admissible source_url/source_excerpt anchors (precedent: MAC-200 §9.1.d Decision 2 ruling on the `test.ys7.com:88` skip-log — runguide planning enumeration is not §11 #7 admissible).

Per MAC-203 halt criteria (verbatim): *"If evidence cannot be traced to a verifiable source_url + source_excerpt for any of the missing models / codenames: HALT and surface that subset of the §44.3 spec as deferred-with-amendment-log-note (path 1 outcome)."*

### §4 — DB-verified post-MAC-203 state (no mutation)

```text
$ python3 (PRAGMA query_only=1)
id=211 name=Honeywell
TOP KEYS: ['admission_basis', 'admission_date_utc', 'admission_dispatch_ref',
           'admission_integration_ref', 'cert_issuer_supply_chain', 'description',
           'documented_absence', 'honeywell_acs_division_attestation',
           'mac195_alias_enrichment']
  product_families: ABSENT
  codenames: ABSENT
  codesign_branches: ABSENT
  honeywell_acs_division_attestation[0].device_models_attested: ['CT45', 'CT40']
  honeywell_acs_division_attestation[0].code_signing_branch: dubai_android_releasekey
```

Top-level keys on id=211 match the MAC-195 dispatch exactly. The three missing keys remain absent by design.

### §5 — Future re-application requires a fresh extraction

Re-application of `product_families` / `codenames` / `codesign_branches` on id=211 requires a future wave to re-collect Honeywell firmware nomenclature with §11 #7-compliant `source_url` + `source_excerpt` per missing model/codename. When (if) such a wave surfaces (e.g., a fresh Wave I.15+ firmware-extraction sandbox with surviving artifacts), it can dispatch a Phase-N+ product-nomenclature integration ticket against id=211 under its own `sweep_event_id`.

Per MAC-203 out-of-scope guard: **no** Phase-N+ re-application dispatch is queued at this time because there is no surviving evidence trail to re-apply from. This is not a CP32 candidate; it is a forward-looking re-application gate that fires only on evidence-arrival.

### §6 — Architectural firsts (this deferral entry)

1. **First standalone Deferral Note** in `BIBLE_AMENDMENTS.md` (no bible text edit, no schema mutation, no DB write — pure §11 #11 deliberate-deferral accountability trail).
2. **First documented case** of a Wave I.14a remine sub-pass proposal explicitly classified as out-of-scope vs. the v1.4.1 Stage 1 integration tree it referenced.
3. **First explicit precedent** that runguide §-spec proposals are NOT auto-promoted to dispatch scope — dispatch scope is what the dispatch enumerates; runguide proposals are scaffolds that may or may not be routed through a phase.

### §7 — Out-of-scope guard

- No Phase 9 ([MAC-200](/MAC/issues/MAC-200)) back-fill (closed scope per CEO ratification at MAC-200 close).
- No mutation to any Honeywell id=211 notes key besides the (now-verified-deferred) `product_families` / `codenames` / `codesign_branches` triad — and that triad remains ABSENT by deliberate scope.
- No CP-class amendment surfaced — the §44.3 spec's identifier-shape did not propose a new `identifier_type`; it was a `notes`-key enrichment proposal only.

### §8 — §11 #11 self-binding satisfied

This deferral entry IS the §11 #11 amendment-log pairing for the deliberate-deferral path ratified at MAC-203. No bible text was edited; no migration was applied; no DB write was made. The entry exists solely to preserve the audit-trail invariant that an undocumented deferral (even one ratified as Path 1) is a process violation regardless of whether the deferral decision itself is correct.

Branch: `v1.4.1-integration-stage-1` (MAC-203 is a v1.4.1 Stage 1 child of [MAC-184](/MAC/issues/MAC-184); no commit lands on `main` from this entry until v1.4.1 ships).

═══════════════════════════════════════════════════════════════════════


## CP32 Candidate #6 (folded into CP32 §6 — see Correction Pass 32 above) — Direct-admission carve-out (wave_g_pre_v1, 21 rows) + §11 #17 applicability-scope clause

**Date:** 2026-05-20
**Branch:** `v1.4.1-integration-stage-1`
**Commit:** Bible edit at `PROJECT_BIBLE.md §11 #17` landed at MAC-206 Phase 10d Run 3 heartbeat commit; CP32 bundle codification landed at [MAC-220](/MAC/issues/MAC-220) commit `<this-commit>`.
**Source:** [MAC-206](/MAC/issues/MAC-206) Phase 10d Run 3 — β.3c ratified at [MAC-206 comment 90e6b70f](/MAC/issues/MAC-206#comment-90e6b70f-9f4d-4374-9655-d498e56982d2) 2026-05-20 (CEO ratification)
**Status:** **CODIFIED** — folded into CP32 §6 above. This candidate entry preserved as expanded archival detail per its original "If CP32 lands as a single bundle commit, this entry's title will be renumbered to a sub-section of the CP32 entry" anticipation.
**Ratifying CEO comment:** [MAC-206#90e6b70f](/MAC/issues/MAC-206#comment-90e6b70f-9f4d-4374-9655-d498e56982d2) — β.3c (verbatim applicability language ratified)
**Companion CEO ratification:** [MAC-205](/MAC/issues/MAC-205) (disposition β + scope-handling Option A — 21 rows ratified for carve-out)

### §1 — What was edited

`PROJECT_BIBLE.md` §11 gained a new numbered entry **#17** with two stacked sub-bullets:

1. **§11 #17 (top-level rule)** — Direct-admission carve-out clause. States the amended audit invariant (raw_observations predecessor OR `notes.direct_admission_carve_out=true` referencing sources.notes provenance); session-bounds to `wave_g_pre_v1` (sids 13, 14; 21 rows enumerated at MAC-205); declares non-future-pathway; cites wave_g_pre_v1 intentionality anchors (`mac_55_step_2_run` + `authority_chain` on sources rows); contrasts with the 16 apkpure-sourced identifiers admitted *outside* wave_g_pre_v1 (ids 23043–23058) that carry raw_observations predecessors per the canonical contract.
2. **§11 #17 sub-bullet — Applicability scope** (CEO verbatim). Two excluded row classes:
    - **Class 1 (out-of-scope by era's convention):** 106 `identifiers` MAC-44 rationales + 21 `sources` MAC-63 templates + ~52,501 `raw_observations` FCC/IEEE address strings. **Future migrations MUST NOT JSON-ify them.** No backfill required or authorized.
    - **Class 2 (deferred intended-JSON repair):** 5 `identifiers` (ids 554-558, RAVEN_* services) + 1 `sources` (sid=7). Backfill required, deferred to [MAC-208](/MAC/issues/MAC-208).
    - id=539 (Flock Safety, sid=13) is class 2 but was forward-repaired in MAC-206 (carve-out UPDATE mechanically requires `json_valid(notes)=1`). The MAC-206 repair lifted suffix verbatim into `notes.corroboration_note_2026_05_10` + added `notes.repair_audit.sweep_event_id='mac206_id539_repair_2026_05_20'`. repair_audit + carve_out_audit events cross-reference each other on id=539's row.
3. **§11 #17 sub-bullet — Downstream-consumer applicability (MAC-206 Phase 3 sweep, 2026-05-20).** Records the in-heartbeat consumer sweep: `argus_cli.py`, `db/validation/export_lynceus.py`, `db/export/wave_a_snapshot_export.py` all read `identifiers.notes` as opaque-string (no json_extract); `db/validation/mac101_item_a_registry_xcheck.py` defensively guards with `WHERE json_valid(notes)` on raw_observations only. No consumer hard-requires global `json_valid(notes)=1` on identifiers. Adds an operational sub-rule binding future consumers that add `json_extract(notes,'$.X')` calls on columns where class-1 rows live.

### §2 — What was changed in the DB (paste-not-cite from MAC-206 Phase 10d Run 3)

- **Backup:** `db/argus.db.mac206_pre_carveout_backup` sha256 = `f346940861995b740c301fc520aab3500e2acebb158fcbe7aecb88f088c51bab`.
- **Phase 1.6 sibling repair (sweep_event_id `mac206_id539_repair_2026_05_20`):** 1 row UPDATEd (id=539). Pre-UPDATE: `json_valid(notes)=0`, length=446 chars, sha256=`7855e94df59f0642390a6d66481e23a98577aed560b0673a706c036262783786`. Post-UPDATE: `json_valid(notes)=1`, 4 original keys preserved (`apk_package`, `apk_version`, `sub_band`, `§8.3_boost_pending`) + `corroboration_note_2026_05_10` (suffix lifted verbatim) + `repair_audit` (with forward-ref to carve-out event + MAC-208 child-issue ref).
- **Phase 2 carve-out (sweep_event_id `mac206_wave_g_carveout_2026_05_20`):** 21 rows UPDATEd via `json_patch(notes, ?)` (first-run affected=21; idempotency re-run affected=0). Composite WHERE: `id IN (533..553) AND source_url IN (<flock_url>, <getac_url>) AND json_extract(notes,'$.direct_admission_carve_out') IS NULL`. Each row gained 7 carve-out top-level keys + `carve_out_audit` sub-object with `precondition_event` back-ref to the id=539 repair event + `child_issue_ref` to [MAC-208](/MAC/issues/MAC-208).
- **No migration applied.** No schema/enum change. The carve-out is a `notes` JSON addition only.
- **No fabrication.** Per §11 #1 paste-not-cite: id=539 suffix lifted verbatim (not paraphrased); all 21 rows' pre-existing keys preserved (json_patch is additive); audit metadata is timestamped + sweep_event_id-anchored.

### §3 — Why this is a candidate, not a numbered CP

CP31 landed at MAC-197 (`v1.4.1-integration-stage-1` HEAD at CP31 close). CP32 has 5 existing candidates queued; this is candidate #6. The final CP32 slot number is reserved for the bundle landing — if CP32 lands as a single bundle commit, this entry's title will be renumbered to a sub-section of the CP32 entry. If CP32 is split into CP32 + CP33, this entry may land as part of one of the bundle commits at the discretion of the bundle author. Either way, the carve-out clause + applicability clause MUST land in the same commit (they are conceptually paired per CEO ratification).

The bible text edit at §11 #17 has already been applied to `PROJECT_BIBLE.md` on `v1.4.1-integration-stage-1` as part of the MAC-206 Phase 10d Run 3 heartbeat; this BIBLE_AMENDMENTS.md entry pairs with that edit per §11 #11 self-binding.

### §4 — Cross-references

- MAC-206 Phase 10d execution heartbeat: `_phase_10_schema_anomaly/carve_out_execution.md` Run 3 (this same commit).
- Sibling [MAC-208](/MAC/issues/MAC-208) (v1.4.2 hygiene — repair 6 intended-JSON rows broken by `{json}<concat>text` defect): filed at MAC-206 Phase 10d Run 3 Step 2 with title-only stub body containing the verbatim scan paste of the 5 RAVEN_* + sid=7 rows. Not a blocker on MAC-206 or v1.4.1 Stage 1.
- MAC-205 scoping heartbeat: `_phase_10_schema_anomaly/orphan_scoping.md` §3 — 21-row enumeration.
- MAC-202 (sid=13 investigation) + MAC-204 (sid=13 rebind) — sibling MAC-184 children, both `done`.

### §5 — §11 #11 self-binding satisfied

This entry IS the §11 #11 pairing for the bible §11 #17 edit. The git commit applying both the bible edit and this entry is recorded above (commit hash filled in when committed). No undocumented amendment.

═══════════════════════════════════════════════════════════════════════


## CP32 Candidate #7 (folded into CP32 §7 — see Correction Pass 32 above) — Dispatch plan-input sandbox-absence HALT-fast-path default

**Date:** 2026-05-21
**Branch:** `v1.4.1-integration-stage-1`
**Commit:** CP32 bundle codification landed at [MAC-220](/MAC/issues/MAC-220) commit `<this-commit>`.
**Source:** [MAC-207](/MAC/issues/MAC-207) Phase 11 HALT — plan-input JSON sandbox-absence; ratified at [MAC-207 comment c4ec8740](/MAC/issues/MAC-207#comment-c4ec8740-36e4-42a9-bac6-cadd035bb110) 2026-05-21 (CEO ratification of Option A single-cycle all-73 DROP close).
**Status:** **CODIFIED** — folded into CP32 §7 above. This candidate entry preserved as expanded archival detail per its original Stage 1 candidate-state framing.
**Ratifying CEO comment:** [MAC-207#c4ec8740](/MAC/issues/MAC-207#comment-c4ec8740-36e4-42a9-bac6-cadd035bb110) — Option A approved (verbatim language ratified).
**Companion precedent:** [MAC-200](/MAC/issues/MAC-200) heartbeat §9.2.c (commit `518bbcd`) — first surfacing of the same `~/argus-internal/wave_i_pre_v1/wave_i_13_hard_id_v2/` sandbox-absence; CP32 candidate #7 codifies the discipline pattern that MAC-200 already exercised informally.

### §1 — Ratified amendment language (CEO verbatim, MAC-207#c4ec8740)

> **Dispatch plan-input sandbox-absence:** when a Stage 1 phase plan-input lives in a cleaned `~/argus-internal/` (or analogous workspace-only) sandbox and was not snapshotted to a versioned location at dispatch time, the phase's HALT-fast-path becomes the default disposition (assuming the dispatch body anticipates this case with an explicit fast-path clause). The sandbox-clean condition is a discoverable precondition during pre-flight, not a mid-flight surprise; ratification can happen at HALT-comment time without per-record evidence enumeration. Forward-looking sub-rule: future dispatches that depend on `~/argus-internal/`-resident plan-inputs **SHOULD** specify a snapshot path under a versioned location (the argus repo) at dispatch time, with a fallback fast-path clause when the snapshot was not captured.

### §2 — Triggering event (paste-not-cite)

MAC-207 dispatch §11.1 plan-input path: `~/argus-internal/wave_i_pre_v1/wave_i_13_hard_id_v2/fp_review_queue_wave_i_13_kept_for_ceo_disposition.json` (73 records expected).

Filesystem state at MAC-207 pre-flight (2026-05-20):

```text
$ ls -la ~/argus-internal/wave_i_pre_v1/wave_i_13_hard_id_v2/fp_review_queue_wave_i_13_kept_for_ceo_disposition.json
ls: cannot access ... : No such file or directory

$ ls -la /home/kev/argus-internal/wave_i_pre_v1/
ls: cannot access '/home/kev/argus-internal/wave_i_pre_v1/': No such file or directory

$ find /home/kev -maxdepth 6 -iname "*fp_review_queue*"            : (0 hits)
$ find /home/kev -maxdepth 7 -type d -iname "wave_i_13*"           : (0 hits)
$ find /home/kev -maxdepth 7 -type d -iname "wave_i_pre*"          : (0 hits)
```

Entire parent sandbox absent. Halt criterion #1 (verbatim from MAC-207 issue body: *"Plan-input JSON malformed or row count ≠ 73"*) fired in its strongest form. §11 #1 (no fabrication) blocked Validator from enumerating 73 records not on disk.

### §3 — Why HALT-fast-path was the correct default (CEO 5-fold reasoning, ratified verbatim)

1. **Wave I.13 DOUBLE-FALSIFICATION methodology** already established all 73 as DROP-default per dispatch §11.2 (sub-pass 41+42 + sub-pass 44).
2. **Per-record JSON unavailable** — sandbox absent per `ls`+`find` paste-not-cite; §11 #1 blocks enumeration of records not on disk.
3. **DROPs are log-only** — records were never promoted to `identifiers`, so canonical DB state is not mutated. Schema_version=25, identifiers active=34,968, sources=71, manufacturers=52 all unchanged after Option A.
4. **§11 #7 (audit-append-don't-mutate)** + **§11 #8 (corroboration independence)** are not engaged (no canonical row touched).
5. **MAC-207 issue body fast-path explicitly authorises** the single-cycle close when all 73 → DROP (verbatim: *"If all 73 → DROP (most likely outcome per memory + dispatch §11.2), single-cycle close: Validator surveys → CEO confirms all-DROP → Validator logs only (no canonical mutation) → done."*).

Options B (re-extract from Wave I.7/I.8 firmware) and C (defer to v1.5.0) were rejected by CEO:

- **B rejected** — multi-issue +3-5 day detour to regenerate a candidate list whose §11.2 default is already DROP. No information value; pure delay of Stage 1 ship-prep.
- **C rejected** — cancelling MAC-207 with a v1.5.0 carry-forward leaves Wave I.13 fp_review_queue in an indeterminate "is this still 73 or some other count" state through v1.4.1 → v1.5.0; cleaner to close under Stage 1 as ratified DROP.

### §4 — Forward-looking sub-rule (operational binding for future dispatches)

Future Stage 1+ phase dispatches whose plan-input lives in `~/argus-internal/` (or analogous workspace-only sandbox path) **SHOULD**:

1. **Specify a snapshot path under a versioned location** (the argus repo) at dispatch time — e.g., `~/argus/_phase_N_<topic>/inputs/<filename>.json` — so the input is committed alongside the phase code.
2. **Include an explicit fallback fast-path clause** in the dispatch body for the case where the snapshot was not captured (analogous to MAC-207 §11.2's *"all 73 → DROP single-cycle close"* clause).

Pre-flight discipline: dispatches lacking either provision will surface the sandbox-absence as a HARD HALT without a fast-path default, forcing a full re-dispatch cycle rather than a clean ratification.

This sub-rule is **operational guidance**, not a hard CHECK constraint — enforcement is at dispatch-authorship time (dispatcher discipline), not at schema-validation time.

### §5 — Architectural firsts (this candidate)

1. **First codified HALT-fast-path discipline pattern** in the framework — prior precedent (MAC-200 §9.2.c) exercised the pattern informally; CP32 candidate #7 elevates it to a named discipline rule.
2. **First explicit pre-flight precondition class** that warrants ratification-at-HALT-comment-time rather than full survey enumeration (the sandbox-clean condition is a discoverable precondition, distinct from mid-flight evidence-quality halts).
3. **First forward-looking sub-rule binding dispatch authorship** (rather than runtime enforcement) — establishes that dispatcher-side discipline is itself an amendment-log-relevant pattern.

### §6 — Cross-references

- MAC-207 Phase 11 heartbeat: `_phase_11_fp_review_queue/heartbeat.md` (this same commit).
- MAC-200 Phase 9 precedent: `_phase_9_wave_i_13_carry_forward/heartbeat.md` §9.2.c (commit `518bbcd`) — same sandbox surfaced as cleaned/unavailable.
- MAC-203 Deferral Note 1 (this file, above §44.3 Honeywell entry) — same sandbox surfaced as unavailable; ratified as Path 1 intentional scope narrowing.
- MAC-206 CP32 candidate #6 (this file, above) — companion candidate landed under the same v1.4.1 Stage 1 integration tree.

### §7 — §11 #11 self-binding satisfied

This entry IS the §11 #11 pairing for the MAC-207 HALT-fast-path ratification. The git commit applying this entry alongside the MAC-207 heartbeat close-out is recorded above (commit hash filled in when committed). No bible text edit was required (the rule lives only in BIBLE_AMENDMENTS.md as a candidate pending CP32 bundle close); no migration was applied; no DB write was made. Schema_version unchanged at 25.

Branch: `v1.4.1-integration-stage-1` (MAC-207 is a v1.4.1 Stage 1 child of [MAC-184](/MAC/issues/MAC-184); no commit lands on `main` from this entry until v1.4.1 ships).

═══════════════════════════════════════════════════════════════════════


## CP32 Candidate #8 (folded into CP32 §8 — see Correction Pass 32 above) — MAC-206 carve-out export-drop attribution (§4.4 type-mapping, NOT §8.2/CP19 crowdsourced-ceiling)

**Date:** 2026-05-21
**Branch:** `v1.4.1-integration-stage-1`
**Commit:** Originally landed alongside MAC-209 Phase 12 follow-up fixup commit (`6d33fa8`); CP32 bundle codification landed at [MAC-220](/MAC/issues/MAC-220) commit `<this-commit>`.
**Source:** [MAC-209](/MAC/issues/MAC-209) Phase 12 spot-check finding — surfaced by Validator at [comment ef215248](/MAC/issues/MAC-209#comment-ef215248-…) 2026-05-21.
**Status:** **CODIFIED** — folded into CP32 §8 above. This candidate entry preserved as expanded archival detail per its original Stage 1 candidate-state framing.
**Ratifying CEO note:** This candidate codifies a dispatch-reasoning correction surfaced post-execution: the MAC-206 dispatch implied carve-out rows would drop from Lynceus high-conf export via CP19 §8.2 crowdsourced-ceiling. Validator's MAC-209 spot-check found they actually drop at §4.4 type-mapping. CEO ratifies the corrected mechanism as the canonical explanation.

### §1 — Ratified amendment language

> **MAC-206 carve-out export-drop attribution sub-clause to §11 #17:** the 21 direct-admission carve-out rows (`identifiers.id IN (533..553)` with `notes.direct_admission_carve_out=true`) drop from `argus_export.json` (Lynceus standard) and `argus_export_high_confidence.json` (Lynceus high-conf) via the **§4.4 identifier_type → pattern_type mapping gate**: their identifier_types (`ble_service`, `ble_characteristic`, `ble_local_name`, `product_family_codename`) are not present in the Lynceus `IDENTIFIER_TYPE_TO_PATTERN_TYPE` lookup, so they're tallied under `_meta.dropped_in_export.type_mapping_unmapped`. They do **NOT** drop via CP19 §8.2 crowdsourced-ceiling — their `source_type` is `manufacturer_app` (not `crowdsourced`) and their `confidence` is 82/87/92 (above both the standard floor of 30 and the high-conf floor of 70). This distinction matters because future cycles MUST NOT assume "wave_g_pre_v1 carve-out rows are crowdsourced-ceiling-bound" — they're shape-bound via §4.4, which is a different invariant (the rows could be uplifted in confidence indefinitely and still drop, until §4.4 admits their identifier_type into the Lynceus map). Forward-looking implication: if a future cycle admits any of these 4 identifier_types into `IDENTIFIER_TYPE_TO_PATTERN_TYPE` (e.g., to surface BLE-service signatures in Lynceus scans), the carve-out rows WILL surface in exports at their current confidence. That admission should be deliberately coordinated with a §11 #17 applicability re-review.

### §2 — Triggering event (paste-not-cite from MAC-209)

MAC-209 Phase 12 §Phase 3 spot-check verified:

```text
identifiers WHERE direct_admission_carve_out=true → 21
  in argus_export.csv          → 21  (no filter)
  in argus_export.json         → 0   (Lynceus standard ≥30 + §4.4 type-map + CP7 geographic_scope)
  in argus_export_high_confidence.json → 0  (Lynceus high-conf ≥70 + §11 #12 Pi OUI ban + §4.4)
```

Source-typed distribution of the 21 rows (from DB query):

```text
source_type='manufacturer_app' at conf 82/87/92
identifier_type IN ('ble_service', 'ble_characteristic', 'ble_local_name', 'product_family_codename')
```

None of these identifier_types appear in `IDENTIFIER_TYPE_TO_PATTERN_TYPE` (the §4.4 map). They tally into `_meta.dropped_in_export.type_mapping_unmapped` along with the 41 `equipment_class_code` rows (CP31) and the 17 `fcc_grantee_code` rows (also CP31) — same drop bucket, same mechanism.

### §3 — Why the MAC-206 dispatch's CP19 reasoning was incorrect

MAC-206 dispatch Phase 3 acceptance criterion said:

> Confirm they do NOT promote into the ≥70 high-conf export (CP19 + §8.2 crowdsourced ceiling).

This was a CEO authoring error in the MAC-206 dispatch. CP19's crowdsourced-ceiling rule is band-bound (any `source_type='crowdsourced'` row tops out at 75, so they fall below the 70 high-conf floor only when their conf is calibrated downward; CP19 actually excludes them at 70 floor by *band-meaning ≠ confidence-value*, not by raw conf < 70). Either way, the 21 carve-out rows aren't `source_type='crowdsourced'` — they're `manufacturer_app`. So CP19 wasn't engaged at all.

The dispatch reasoning chain was correct in its **conclusion** (rows correctly absent from high-conf export) but **wrong in its mechanism**. Validator's MAC-209 spot-check caught it because Validator did the actual DB-query rather than trusting the dispatch claim — per [[feedback_db_verify_dispatch_claims]].

### §4 — Forward-looking sub-rule (operational binding)

Future dispatches that assert "rows X drop from Lynceus export because of mechanism Y" MUST cite the actual drop tally bucket in `_meta.dropped_in_export.*` and confirm via DB-query that the row's `source_type` + `identifier_type` + `confidence` align with mechanism Y's predicate, before baking the assertion into acceptance criteria. The discipline is not new (already covered by `[[feedback_db_verify_dispatch_claims]]`); this sub-clause flags Lynceus-export drop mechanisms specifically because they have **multiple superficially-applicable predicates** (§4.4 type-map vs §8.2 source-band vs §11 #12 OUI-ban vs §11 #13 unknown-category vs §11 #14 procurement vs CP7 geographic_scope) and the wrong attribution surfaces only at export-time spot-check, not at promotion-time.

### §5 — Architectural firsts (this candidate)

1. **First codified Lynceus-export drop-attribution discipline rule** — prior CP entries focused on what drops from export, not on which mechanism explains a given drop. This candidate elevates drop-attribution to a first-class audit concern.
2. **First post-execution dispatch-reasoning correction landed as a CP candidate** — prior dispatch-reasoning errors (e.g., MAC-176 forecast error on Johnson Matthey MA-M routing per [[feedback_forecast_identifier_type_from_prefix_suffix]]) landed as feedback memories; this one earns a CP entry because it composes directly with §11 #17 and constrains future BLE-service identifier_type admission decisions.

### §6 — Cross-references

- MAC-209 Phase 12 close-out: [comment ef215248](/MAC/issues/MAC-209#comment-ef215248-…) — paste-not-cite spot-check that surfaced the mechanism.
- MAC-206 CP32 candidate #6 (this file, above) — §11 #17 carve-out clause this candidate composes with.
- [[feedback_db_verify_dispatch_claims]] — meta-discipline this candidate operationalizes for Lynceus-export drops.

### §7 — §11 #11 self-binding satisfied

This entry IS the §11 #11 pairing for the MAC-209 surfaced dispatch-reasoning correction. The git commit applying this entry alongside STAGE_1_FINAL_REPORT.md is recorded above (commit hash filled in when committed). No bible text edit; no migration; no DB write. Schema_version unchanged at 25.

Branch: `v1.4.1-integration-stage-1` (MAC-209 is a v1.4.1 Stage 1 child of [MAC-184](/MAC/issues/MAC-184); no commit lands on `main` from this entry until v1.4.1 ships).

═══════════════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════════════

## Correction Pass 33 — v1.5.0 Lexicon-Expansion Wave (mig-0027 dual-table CHECK extension + 7 sub-section bundle codification + SAR-16/17/18)

### Scope

CP33 codifies a single bundled amendment with 7 sub-sections covering the [MAC-232](/MAC/issues/MAC-232) v1.5.0 lexicon-expansion-wave integration (Stage 1 + Stage 2). The cycle was a two-session parallel dispatch (S1 military/federal cohort + S2 commercial/consumer cohort). Migration 0027 lands a single dual-table schema-level mutation — the `device_category` CHECK enum extension `+3 (cctv_camera, persistent_surveillance, through_wall_radar)` applied to BOTH `identifiers.device_category` and `behavioral_signatures.device_category` (second framework dual-table CHECK literal extension after the CP32 §1 precedent) plus the `identifiers.identifier_type` CHECK enum `+1 imei_tac` forward-compatible admission. Schema_version bumps 26 → 27. The remaining sub-sections codify 40 net new manufacturer admissions + Pelco arm-under-MSI (id=254 — second framework `hidden_arm` row after Parrot Automotive id=222) + 848 net active identifier promotions + Step 6 G-B retroactive `cctv_camera` recategorization sweep (7 mfg + 31 ident rows; NDAA §889 attribution preserved on Hikvision + Dahua; BriefCam deferred to v1.5.x) + Step 7 disambig + FP-class triage + Step 8 v1.5.x/v1.6.0 backlog queue (the new `PLANNED_AND_FUTURE_UPDATES.md` repo file).

Three independent SAR codifications land alongside CP33 — **SAR-16** (alias-length-floor; lockheed-LM n=134 driving case), **SAR-17** (no-generic-product-aliases; mydefence-EAGLE n=41 driving case), **SAR-18** (classifier-predicate parity; Step 9 `oversized_mac_range` halt at id=9404 Eagle Eye Networks size=256 → Path β ratification within 50 minutes of halt-surface). SAR-16 + SAR-17 codify cohort-disambiguation extensions of SAR-15 GENERIC_RISK_CANONICALS pre-load; SAR-18 extends the CP21 cumulative-full-enum sweep spirit (CHECK constraint parity across migrations) to runtime classifier predicates and forward-binds future `_classify_row` additions to dual-table parity review at PR time.

### CP30 reservation footnote (preserved unchanged)

CP30 remains reserved for `vendor_asn_prefix` + `vendor_controlled_ip` codification per CP29 §3 (preserved through CP31 + CP32; CP33 does NOT consume the CP30 reservation slot).

### Status legend

**CODIFIED+LANDS** = bible text change + schema/code mutation in this CP. **CODIFIED** = bible text change only (narrative/discipline). **BINDING** = architectural commitment for a future migration (no current schema change). **DEFERRED** = item explicitly scope-narrowed to v1.5.x or v1.6.0 backlog per PLANNED_AND_FUTURE_UPDATES.md.

### §1 — v1.5.0 Stage 1 source admissions + dedups

**Cycle:** v1.5.0 Stage 1 (MAC-232)
**Branch:** `v1.5.0-integration-stage-1`
**Schema version:** unchanged at 26 at Step 2 close (Step 3 will bump to 27 if migrations are required)
**Net source admissions:** +2 (sid=72, 73). Sources 71 → 73.

### §1 — Two new sources admitted

1. **sid=72 — GitHub Code Search REST API**
   - URL: `https://api.github.com/search/code`
   - `source_type=crowdsourced`, `tier=3`
   - License posture: `NO_LICENSE_DECLARED` — per-finding factual extraction only per Feist v Rural (cf. §11 #16). Per-repo license inherits, but findings are facts-only (filename, line, sha, URL).
   - Auth: `GITHUB_TOKEN` PAT (30 authenticated req/min on code-search; 2.5s per-query pacing observed compliant)
   - Rationale: content-search surface distinct from sid=56 (`raw.githubusercontent.com`) which is known-file retrieval. Different access modes, different rate limits, different admission predicates.
   - Value-class ceiling: 75 (crowdsourced per CP15)
   - First used: `wave_v1_5_session_1_military_federal`
   - Compliance §11 #15: factual extraction only; not decompiled vendor source.

2. **sid=73 — adsb.lol v2 (FAA-registry-derived aircraft tracking)**
   - URL: `https://api.adsb.lol/v2/registration/`
   - `source_type=regulatory`, `tier=3`
   - License posture: `PUBLIC_DOMAIN_EQUIVALENT` (FAA Civil Aviation Registry-derived + live ADS-B broadcasts; FAA registry is 14 CFR Part 47 public record)
   - Auth: none (public API)
   - Rationale: adsbexchange now requires auth on v1 endpoints; adsb.lol provides equivalent ADS-B aggregator with free public API. Used for CBP MQ-9 Predator-B Mode-S (`icao_24bit_address`) extraction.
   - Value-class ceiling: 90 (regulatory per CP15)
   - First used: `wave_v1_5_session_1_military_federal`
   - Session 1 yield: 2/10 CBP MQ-9 tails — ABF68A for N870CB, ABFDF8 for N872CB.

### §2 — Two dedups logged (§11 #11 integration-time reconciliation)

These were proposed as net-new in S1/S2 runguides, but at integration time were found to already exist in canonical `sources` table. No new sid issued; all downstream citations route to the existing sid.

1. **crt.sh** — proposed by S1 #1; already admitted as **sid=54** ('Certificate Transparency Logs — crt.sh aggregator', URL `https://crt.sh/`). All S1 crt.sh citations at Step 5 (raw_observations admission) route to sid=54. Same dedup shape as fccid.io (G-E precedent ratified by board at MAC-232 dispatch).
2. **fccid.io** — proposed by S2 #5; already admitted as **sid=51** (URL `https://fccid.io/`). 21 S2 grantee citations route to sid=51 at Step 5. Per MAC-232 dispatch Step 1 #2 + G-G ratification.

Both dedups are integration-time reconciliations per §11 #11; neither requires a separate amendment slot — they are logged here for audit-trail completeness.

### §3 — Six deferrals enumerated by reason class

| # | Proposed source | Origin | Reason class | Deferral target |
|---|-----------------|--------|--------------|-----------------|
| 1 | DHS S&T via Wayback | S1 #3 | 0-yield (0 snapshots; would route to sid=55 Wayback CDX anyway) | v1.6.0 with alternative direct-access path |
| 2 | Google Play Store | S2 #1 | 0-yield (S2 `companion_app_extraction` dir empty; 0 files extracted) | v1.5.x — fabrication risk gate |
| 3 | ISED Canada Radio Equipment Search | S2 #2 | ~0-effective-yield (1 hit across S2 candidate JSON, likely false-positive substring) | v1.5.x |
| 4 | RRA Korea | S2 #3 | Unreachable from this network (per S2 `STOP_THE_LINE_rra_korea_unreachable.md`) | v1.5.x or v1.6.0 |
| 5 | ETSI | S2 #4 | ~0-effective-yield (1 hit, likely false-positive substring in grantee-codes file) | v1.5.x |
| 6 | State DOC Procurement Portals | S2 #6 | Operator-opt-in required (stage as operator-manual queue, NOT auto-admit) | v1.5.x with operator-decision dispatch |

### §4 — Architectural firsts

1. **First v1.5.0 source admission** — opens the v1.5.0 ship cycle's source-admission ledger at sid=72.
2. **First crowdsourced+NO_LICENSE_DECLARED source distinguishing two access surfaces of the same upstream platform (GitHub)** — sid=72 (api/search/code) vs sid=56 (raw.githubusercontent.com). Establishes precedent for admitting two sids per platform when access-mode/rate-limit/admission-predicate differ.
3. **First batch-level integration-time §11 #11 reconciliation logging 2 dedups in a single amendment-log entry** — prior dedups (e.g., MAC-232 G-E fccid.io precedent) were logged individually; this batches crt.sh + fccid.io.
4. **First deferral-table-by-reason-class in an amendment draft** — six-row deferral table with reason-class column establishes shape for future cycle integration-time deferral audits.

### §5 — Cross-references

- MAC-232 dispatch (G-A through G-G ratified by board).
- CP15 (value-class ceilings: `crowdsourced=75`, `regulatory=90`).
- §11 #11 (integration-time source dedup discipline).
- §11 #15 (factual extraction only; not decompiled vendor source — relevant to sid=72 GitHub Code Search compliance).
- §11 #16 (Feist v Rural facts-only doctrine — relevant to sid=72 NO_LICENSE_DECLARED license posture).
- CP32 candidate (BIBLE_AMENDMENTS.md prior entry on §11 #17 carve-out) — not amended here.

### §6 — §11 #11 self-binding pending

Final CP33 entry consolidating Steps 2-9 will satisfy §11 #11 with the consolidated git commit hash at Step 10 close. This Step 2 draft section is one of the parallel amendment-drafts being assembled; the commit applying this draft is referenced inline in the Step 2 close-out report at `~/argus-internal/wave_v1_5_lexicon_expansion/_integration_stage1/step2_source_admissions.md`.

═══════════════════════════════════════════════════════════════════════

### §2 — Schema extension mig-0027 CP33

**Cycle:** v1.5.0 Stage 1 (MAC-232)
**Branch:** `v1.5.0-integration-stage-1`
**Migration:** `db/migrations/0027_cp33_cctv_camera_persistent_surveillance_through_wall_radar_imei_tac.sql`
**Migration SHA256:** `86ba28b12d6638501aebd0374e64f7701f189fc39759643d6d065e5e305b31c4`
**Schema version:** 26 → 27 (bumped by mig-0027 footer)
**Authority:** Board ratification 2026-05-22 (comment 0ba8150f), gates G-A through G-G approved.

### §2.1 — `device_category` CHECK enum +3 net-new values (both host tables)

Three new values admitted with per-value rationale citing v1.5.0 sandbox-session cohort proposals (S1 `proposed_bible_amendment_additions.md` military/federal + S2 `proposed_bible_amendment_additions.md` commercial/consumer).

| New value | Cohort | Origin session | Rationale |
|-----------|--------|----------------|-----------|
| `cctv_camera` | Commercial/consumer | S2 | Distinguishes general-purpose CCTV from existing `covert_cam`; opens slot for the G-B retroactive recategorization of 7 vendors (executes at Step 6 AFTER this migration lands). G-B was board-ratified at 0ba8150f. |
| `persistent_surveillance` | Military/federal | S1 | Surveillance-blimp / wide-area-motion-imagery class (e.g., JLENS-lineage / Logos Technologies / Sierra Nevada Gorgon Stare derivatives). 0 rows promoted this cycle; schema slot opens for future v1.5.x evidence-arrival. |
| `through_wall_radar` | Military/federal | S1 | FCC §15.519 UWB-LE (ultra-wideband, low-emission) hand-held imaging radar. Distinct from `imsi_catcher` / `gps_tracker`. 0 rows promoted this cycle; schema slot opens for future v1.5.x evidence-arrival. |

Per CP32 precedent, the +3 extension applies to BOTH host tables of `device_category` CHECK literals:
- `identifiers.device_category`        13 → 16 values
- `behavioral_signatures.device_category` 13 → 16 values

### §2.2 — `identifier_type` CHECK enum +1 net-new value (`imei_tac`)

Single addition admitted as dual-proposal merge:
- S1 (military/federal cohort) proposed `imei_tac` in `proposed_bible_amendment_additions.md`.
- S2 (commercial/consumer cohort) proposed `imei_tac` independently in its `proposed_bible_amendment_additions.md`.
- Validator merged both into a single CHECK enum addition at MAC-232 v1.5.0 Stage 1 integration.

**Semantic scope:** GSMA TAC (Type Allocation Code) — first 8 digits of an IMEI identifying the model/variant. Distinct from MAC `oui` (different registry, different prefix length, different device class).

**Promotion ledger this cycle:** 0 rows. Per G-C (board-ratified), `imei_tac` is admitted **forward-compatible**: the schema slot opens for future v1.5.x cohort backfill; no row-level promotion is gated on this migration. Future v1.5.x cohort harvests from GSMA-derivative sources will use this identifier_type.

`identifiers.identifier_type` enum: 56 → 57 values.

### §2.3 — Dual-table CHECK extension per CP32 precedent

CP32 codified the dual-table enum-parity sweep for `device_category` (separate CHECK literals on `identifiers` and `behavioral_signatures` because they are NOT FK-linked — downstream consumers like Lynceus, exports, and the coverage matrix treat the category as a single conceptual vocabulary regardless of host table). CP33 §2 applies that precedent to the +3 extension:

| Host table | Pre-mig-0027 | Post-mig-0027 |
|------------|--------------|---------------|
| `identifiers.device_category`          | 13 | 16 |
| `behavioral_signatures.device_category` | 13 | 16 |

This keeps the two CHECK literals in lockstep per the CP21 cumulative-full-enum sweep spirit.

### §2.4 — G-E `pair_kind` no-op log entry (verbatim from validator G-E report)

Per board ratification G-E:

> "Dispatch claimed `pair_kind` CHECK was 4 values on disk; SAR-13 preflight (sqlite_master.sql read) verified the actual on-disk value is 5 (CP31 already shipped `fcc_grantee_equipment_class`). G-E: do NOT touch pair_kind; the dispatch's '+1 to make it 5' claim was stale because CP31 already landed it. mig-0027 carries forward the 5-value enum verbatim."

mig-0027 preserves the 5-value `pair_kind` enum verbatim from the post-0025 (CP31) state:
`la_bit_flip`, `frdid_sibling`, `vendor_as_container`, `firmware_generation`, `fcc_grantee_equipment_class` (CP31).

Post-mig-0027 row count: `pair_kind` enum unchanged at 5. Verified via sqlite_master DDL read in `_phase_3_cp33_preflight/sqlite_master_after.txt`.

### §2.5 — Schema version bump

| Item | Pre | Post |
|------|-----|------|
| `schema_version` MAX | 26 | 27 |
| Migration name      | `0026_cp32_device_category_automotive_telematics` | `0027_cp33_cctv_camera_persistent_surveillance_through_wall_radar_imei_tac` |
| Migration file SHA256 | n/a | `86ba28b12d6638501aebd0374e64f7701f189fc39759643d6d065e5e305b31c4` |

### §2.6 — Paste-not-cite post-state row counts

Verified post-migration via `_phase_3_cp33_preflight/verification.log`:

```
schema_version: (27, '0027_cp33_cctv_camera_persistent_surveillance_through_wall_radar_imei_tac')
identifiers total:           35,310   (unchanged from pre-mig-0027)
identifiers active:          34,964   (unchanged from pre-mig-0027)
behavioral_signatures:          201   (unchanged from pre-mig-0027)
sources:                         73   (unchanged; Step 2 admissions stable)
manufacturers:                   52   (unchanged from pre-mig-0027)

identifier_type CHECK:           57 values (was 56; +1 imei_tac)
identifiers.device_category:     16 values (was 13; +3 cctv_camera/persistent_surveillance/through_wall_radar)
behavioral_signatures.device_category: 16 values (was 13; +3 parity)
pair_kind CHECK:                  5 values (unchanged per G-E)

FK check:                        [] empty (no violations)
Indexes recreated:               10/10 (all carry-forward verbatim from 0026)

Test INSERT (imei_tac + cctv_camera):       PASS
Test INSERT (persistent_surveillance):      PASS
Test INSERT (through_wall_radar):           PASS
Test INSERT (bad enum value rejected):      PASS
Post-rollback row count:                    PASS (test rows discarded)
```

SAR-13 preflight evidence: `_phase_3_cp33_preflight/sqlite_master_before.txt` (CHECK DDL read PRIOR to migration; baseline 56/13/13/5 confirmed via sqlite_master.sql, NOT via PRAGMA table_info per SAR-13 sub-rule [[feedback_pragma_alone_insufficient_for_sar13]]).

### §2.7 — §11 #11 self-binding pending

Final CP33 entry consolidating Steps 2-9 will satisfy §11 #11 with the consolidated git commit hash at Step 10 close. This Step 3 draft section is one of the parallel amendment-drafts being assembled; the commit applying this draft is referenced inline in the Step 3 close-out report at `~/argus-internal/wave_v1_5_lexicon_expansion/_integration_stage1/step3_migration.md`.

═══════════════════════════════════════════════════════════════════════

### §3 — v1.5.0 Stage 1 manufacturer admissions (+40 net, 92 total)

**Status:** DRAFT — pending §11 #11 self-binding (commit-hash backfill at Stage 1 close).
**Authority:** MAC-232 board ratification 2026-05-22 (G-A through G-G).
**Schema:** No schema change; relies on mig-0027 CHECK enum extensions ratified in §2.

### §3.1 — Counts (per-cohort breakdown)

Manufacturers table delta `52 → 92` (+40 net). Composition:

| Cohort                       | Count | Source         |
|------------------------------|-------|----------------|
| counter-UAS (`drone_detect`) |    11 | Session 1 (military/federal) |
| `persistent_surveillance`    |     4 | Session 1 (military/federal) |
| `through_wall_radar`         |     3 | Session 1 (military/federal) |
| `imsi_catcher`               |     1 | Session 1 (military/federal) |
| `automotive_telematics`      |     6 | Session 2 (commercial/consumer) |
| `cctv_camera` (+1 arm)       |     6 | Session 2 (commercial/consumer) |
| `gps_tracker`                |     5 | Session 2 (commercial/consumer) |
| `unknown` (multi-purpose §11 #10) | 4 | NG/LM (S1) + Trimble/Bosch SS (S2) |
| **Total**                    |  **40** | (21 S1 + 19 S2; 2 SKIPs per board G-A/G-F) |

Arms delta `1 → 2` (Parrot Automotive carries forward; Pelco arm-under-MSI new).

### §3.2 — Pelco arm-under-MSI per G-A

Per board ratification G-A (2026-05-22), Pelco admitted as a CP31 §4.6 arm row under Motorola Solutions (`parent_manufacturer_id=3`), `is_arm=1`, `query_default='hidden_arm'`. The standalone Pelco row staged in Session 2 SQL was SKIPPED. Final row at id=254 with `notes.shape='arm_under_parent'`, `notes.parent_name='Motorola Solutions'`, `notes.parent_id=3`, `notes.g_a_ratification='2026-05-22 board ratified arm-under-MSI per CP31 §4.6'`.

### §3.3 — BI Incorporated standalone per G-F (Geo Group deferred)

Per board ratification G-F (2026-05-22), BI Incorporated admitted standalone (`parent_manufacturer_id=NULL`, `is_arm=0`, `query_default='visible'`). The arm row staged in Session 2 SQL was SKIPPED because the proposed parent ("Geo Group") is NOT-IN-LEXICON — admission of Geo Group as a manufacturer deferred to v1.5.x. Final row at id=258 with `notes.g_f_ratification='2026-05-22 board ratified standalone admission; Geo Group admission deferred to v1.5.x'`.

### §3.4 — Multi-purpose carveouts §11 #10

Four rows admitted as `primary_category='unknown'` with `notes.multi_purpose_carveout='§11 #10'`, mirroring the Cradlepoint / Sierra Wireless / Motorola Solutions precedent:

| id  | canonical_name           | session |
|-----|--------------------------|---------|
| 235 | Northrop Grumman         | S1      |
| 236 | Lockheed Martin          | S1      |
| 250 | Trimble                  | S2      |
| 252 | Bosch Security Systems   | S2      |

These rows DELIBERATELY remain at `primary_category='unknown'` post-backfill; the §4.5 backfill UPDATE WHERE clauses explicitly excluded them.

### §3.5 — NDAA §889 dual-format schema-truth observation

Session 2 staging SQL proposed NDAA attribution for Uniview + Tiandy using:
```
notes.ndaa_section_889_affected = true
notes.ndaa_attribution_note     = "NDAA §889 federal procurement bar applies; state/local LE deployments persist."
```

Existing canonical precedent (Hikvision id=209, Dahua id=208) uses a SINGLE differently-named field:
```
notes.ndaa_section_889_note = "NDAA Section 889 federally-restricted; state/local LE deployments persist outside the federal-procurement bar (runguide §0 scope)."
```

**Resolution applied this step:** BOTH formats were inserted into Uniview (id=255) + Tiandy (id=256) at INSERT time — the canonical `ndaa_section_889_note` field was added alongside the S2-staged keys to give downstream query-paths parity with Hikvision/Dahua precedent.

**Schema-truth observation:** Validator §8 Step 8 flagged this pre-execution. Going forward, either (a) future admissions should standardise on `ndaa_section_889_note` (canonical) OR (b) a SAR-style refinement should explicitly bless dual-format. Tracked for v1.5.x SAR slate as CP33-spirit downstream-consumer audit candidate (parallels SAR-13 sub-rules).

### §3.6 — WatchGuard Video parent='Motorola Solutions' backfill (§15.2 low-cost)

Per dispatch §15.2 bonus, WatchGuard Video (id=17) `notes` backfilled with:
```
notes.parent                    = "Motorola Solutions"
notes.parent_backfill_dispatch  = "MAC-232"
notes.parent_backfill_date_utc  = "2026-05-22"
```

This is a notes-only backfill (no `parent_manufacturer_id` FK promotion this cycle); future v1.5.x slate may consider promotion to true arm-under-parent shape pending re-classification review.

### §3.7 — NIITEK zero-source admission (§11 #1 cohort_prediction)

NIITEK (id=241, `primary_category='through_wall_radar'`) admitted with zero observed sources per Validator §4.3 (`extraction_yield_at_admission` shows 0 across FCC/USAspending/SEC/Wayback/crt.sh). Admission justified by §11 #1 cohort_prediction (parallel admissions Camero + TiaLinx in same cohort with sources >0). Flagged in `notes`:
```
notes.zero_source_admission = true
notes.low_confidence_flag   = true
```

This is the only zero-source admission in v1.5.0 Stage 1 Step 4. Future evidence-arrival re-application gate fires per [[project_mac203_deferral_note_close]] precedent if NIITEK observations surface.

### §3.8 — Anduril multi-product admission flag (future_arm_split_candidates queued)

Anduril Industries (id=223) admitted under primary_category='drone_detect' with `notes.multi_product_admission=true` and `notes.future_arm_split_candidates` enumerating five products spanning multiple device categories (Sentry Tower → persistent_surveillance, Anvil → drone_detect, Lattice OS → unknown_software_substrate, Roadrunner → drone_detect, Sentinel → drone_detect). Arm-split deferred to v1.5.x as candidate CP31 §4.6 expansion.

### §3.9 — Paste-not-cite post-state row counts

Verified post-INSERT/UPDATE via `_phase_4_admissions/verification.log`:

```
total: (92,)            -- manufacturers row count
arms: (2,)              -- is_arm=1 row count (Parrot Automotive + Pelco)

primary_category distribution (new rows id > 222):
  drone_detect            11
  cctv_camera              6
  automotive_telematics    6
  gps_tracker              5
  unknown                  4   (NG/LM/Trimble/Bosch SS §11 #10 carveouts)
  persistent_surveillance  4
  through_wall_radar       3
  imsi_catcher             1

Pelco (id=254):        parent_manufacturer_id=3 (MSI), is_arm=1, query_default='hidden_arm'
BI Incorporated (258): parent_manufacturer_id=NULL, is_arm=0, query_default='visible' (single row only)
WatchGuard (id=17):    notes.parent='Motorola Solutions', notes.parent_backfill_dispatch='MAC-232'
NIITEK (id=241):       notes.zero_source_admission=1, notes.low_confidence_flag=1
NDAA dual-format:      Uniview + Tiandy carry BOTH ndaa_section_889_note (canonical)
                       AND ndaa_section_889_affected + ndaa_attribution_note (S2-staged)

source_url NULL check:  empty (all 92 rows have non-null source_url)
notes JSON validity:    all 40 new rows pass json_valid() round-trip
schema_version:         27 (unchanged; mig-0027 from Step 3)
identifiers active:     34,964 (unchanged this step)
sources:                73 (unchanged this step)
```

### §3.10 — §11 #11 self-binding pending

Final CP33 entry consolidating Steps 2-9 will satisfy §11 #11 with the consolidated git commit hash at Stage 1 close. This Step 4 draft section is one of the parallel amendment-drafts being assembled; the commit applying this draft is referenced inline in the Step 4 close-out report at `~/argus-internal/wave_v1_5_lexicon_expansion/_integration_stage1/step4_manufacturer_admissions.md`.

═══════════════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════════════

### §4 — v1.5.0 Stage 1 Step 5 identifier promotions

**Dispatch:** MAC-232 v1.5.0 Stage 1 Step 5
**sweep_event_id:** `mac232_v1_5_0_stage1_step5_2026_05_22`
**Date:** {'total': 36158, 'active': 35812}  (post-state; this draft)
**Authority:** MAC-232 board ratification `0ba8150f` (G-G + G-C + G-D applied)

### §4.1 Per-identifier_type promotion counts

```
identifier_type                     count
----------------------------------- -----
network_endpoint                    747
fcc_grantee_code                    36
frequency_band                      24
vendor_controlled_hostname          21
product_family_codename             17
icao_24bit_address                  2
ble_company_id                      1
TOTAL                               848
```

### §4.2 Per-source_id citation counts

```
source_id  name                                                    count
---------- ------------------------------------------------------- -----
sid=54     crt.sh                                                  747
sid=51     fccid.io                                                60
sid=72     GitHub Code Search REST API                             38
sid=73     adsb.lol v2                                             2
sid=34     Bluetooth SIG company-identifier registry               1
```

### §4.3 §5.2/§8.3 +5 lift applied (vendors + row counts)

Cross-source §8.3 +5 lift applied per CP15 ceiling cap. **Within-source-only**
S1 vendors (Citadel Defense, Black Sage Technologies, MyDefence Communications,
Sensofusion, TiaLinx) excluded from lift per Validator Step 1 §4.2. **NIITEK**
excluded (zero-source admission; carries `low_confidence_flag` in identifier
rows when promoted in future cycles).

```
manufacturer                        lifted_rows
----------------------------------- -----------
Northrop Grumman                    172
Geotab                              70
Motive                              61
Samsara                             58
BI Incorporated                     56
Attenti                             52
Bosch Security Systems              48
Lockheed Martin                     43
TCOM                                40
Pelco                               27
Hanwha Vision                       10
Sentinel Offender Services          8
Uniview                             7
Tiandy                              6
Rohde & Schwarz                     5
Vivotek                             3
Lytx                                3
General Atomics                     3
Camero                              3
Verizon Connect                     2
Track Group                         2
STOP                                2
Omnitracs                           2
Milestone Systems                   2
D-Fend Solutions                    2
Trimble                             1
Fortem Technologies                 1
Elbit Systems of America            1
Echodyne                            1
AeroDefense                         1
TOTAL                               692
```

**Within-source S1 vendors (no lift this cycle):**
- Sensofusion (108 rows promoted at base ceiling)
- MyDefence Communications (47 rows promoted at base ceiling)
- TiaLinx (1 row promoted at base ceiling)
- Citadel Defense + Black Sage Technologies (no rows this cycle)

### §4.4 Dedup outcomes

```
INSERTs:                                    848
UPDATEs (cross-source bucket existing row): 0
Skipped — same source already attested:     29
Skipped — within-source §11 #8 not corrob:  0
Skipped — CHECK enum violation:             1
Skipped — corporate-attestation (sec/proc): 20
```

Corporate-attestation skips (20 rows) are sec_edgar_cik_anchor (2) +
sec_exhibit_21_subsidiary_confirmed (3) + procurement_vendor_canonical (15) —
not identifier-shaped; consumed by `manufacturers` table updates in Step 4.

### §4.5 G-G batch-reject

Per board G-G ruling on MAC-232, S1's `wayback_pdf_extracted_v2.json` and
`wayback_pdf_extracted_v2_scrubbed.json` were class-rejected without promotion:

```
wayback_pdf_extracted_v2.json:            255 rows skipped
  (240 product_family_codename + 12 network_endpoint + 3 frequency_band)
wayback_pdf_extracted_v2_scrubbed.json:   92 rows skipped
  (77 noisy product_family_codename per G-G + 12 network_endpoint + 3 freq_band)
TOTAL G-G batch-rejected:                  347 rows

G-G per-finding rejection (S2 codenames with HIGH fp_risk):
  'BVMS' / Bosch Security Systems  (fp_risk=HIGH, 11128 GitHub hits — too common)
  'satellite tracking of people' / STOP  (sentence fragment, not codename)
TOTAL G-G per-finding S2 rejected: 2 distinct codenames (×3 raw rows each)
```

Disposition: routed to Step 7 disambig closure for documentation; no canonical
DB row created. Sandbox candidate files preserved unchanged for audit trail.

### §4.6 Pelco PEL grantee ambiguity

Pelco 'PEL' fcc_grantee_code row staged with `notes.disposition=`
`'ambiguous_pending_resolution'` per Validator Step 1 §15.1. The 'PEL' grantee
code might be assigned to KCC (Korea Communications Commission), not FCC.
Resolution deferred to v1.5.x correction-cycle following FCC EAS direct
verification (currently unreachable per STOP_THE_LINE record).

**Staged confidence:** 75 (crowdsourced ceiling; no +5 cross-source lift
applied because Pelco is cross-source bucket vendor but lift+5=80 still capped
at ceiling=75).

### §4.7 NIITEK low-confidence-flag carry-forward

NIITEK identifier rows excluded from this Step 5 promotion (zero-source-admit
manufacturer; no identifier candidates surfaced in S1 sweeps). Future cycles
admitting NIITEK identifier rows MUST carry `notes.low_confidence_flag=true`
per CP33 §4 + manufacturer-table convention (set at Step 4 admission).

### §4.8 sweep_event_id minted

`mac232_v1_5_0_stage1_step5_2026_05_22` — single ID applied across all Step 5 substeps for audit traceability.
Identifier rows + raw_observations + extraction_runs all carry this ID in
`notes.sweep_event_id` (JSON path) per [[feedback_scoped_updates_via_source_row_key]]
traceability discipline.

**extraction_runs added this Step:** 9
(one per substep × per-source-route)

### §4.9 Paste-not-cite final counts

```
identifiers total  pre-Step 5:  35310
identifiers active pre-Step 5:  34964
identifiers total  post-Step 5: 36158
identifiers active post-Step 5: 35812
net delta:                     +  848

raw_observations added:        +  848
extraction_runs added:         +    9

total rows considered:        S1 774 + S2 534 = 1,308 raw candidates
INSERTs:                              848
UPDATEs (cross-source bucket):          0
Skipped (same-source/within/check):    30
Skipped (corporate attestation):       20
Skipped (G-G S1 batch-reject):        347
Skipped (G-G S2 per-finding):           2
S2 dup-row collapse (×3 → ×1):       63 raw → 21 INSERT pairs (codenames+endpoints)
```

### §4.10 — §11 #11 self-binding pending

Final CP33 consolidated entry at Stage 1 close will satisfy §11 #11 with the
git commit hash applying this Step 5 amendment-draft. The commit applying this
draft is referenced inline in the Step 5 close-out report at
`~/argus-internal/wave_v1_5_lexicon_expansion/_integration_stage1/step5_identifier_promotion.md`.

### §5 — v1.5.0 Stage 1 Step 6 retroactive `cctv_camera` recategorization (G-B)

**Cycle:** v1.5.0 Stage 1 (MAC-232)
**sweep_event_id:** `mac232_v1_5_0_stage1_step6_recat_2026_05_22`
**Authority:** Board ratification 2026-05-22 (comment 0ba8150f) — G-B approved.
**§11 #11 binding:** retroactive recategorization is bible-binding. This amendment-log entry preserves the per-row audit per [[feedback_bible_amendment_downstream_consumer_audit]] — downstream consumer (identifier rows) updated as sibling sweep.

### §5.1 Manufacturer rows recategorized (7 total; BriefCam deferred)

| id  | canonical            | from primary_category | to primary_category |
|-----|----------------------|-----------------------|---------------------|
| 209 | Hikvision            | NULL                  | cctv_camera         |
| 208 | Dahua                | NULL                  | cctv_camera         |
| 7   | Axis Communications  | alpr                  | cctv_camera         |
| 6   | Avigilon             | alpr                  | cctv_camera         |
| 210 | Verkada              | NULL                  | cctv_camera         |
| 220 | Eagle Eye Networks   | unknown               | cctv_camera         |
| 221 | Rhombus Systems      | unknown               | cctv_camera         |
| 31  | BriefCam             | face_recog            | **DEFERRED**        |

### §5.2 Identifier rows recategorized (31 total — downstream consumer audit)

| manufacturer        | rows | from device_category | to device_category |
|---------------------|------|----------------------|--------------------|
| Hikvision           | 14   | unknown              | cctv_camera        |
| Dahua               | 8    | unknown              | cctv_camera        |
| Axis Communications | 6    | unknown              | cctv_camera        |
| Avigilon            | 1    | unknown              | cctv_camera        |
| Eagle Eye Networks  | 1    | unknown              | cctv_camera        |
| Rhombus Systems     | 1    | unknown              | cctv_camera        |
| Verkada             | 0    | (no active rows)     | —                  |

Each updated row carries `notes.recategorization_history[]` with: from/to category, cycle, dispatch_ref, gate_ref, sweep_event_id, applied_utc, mfg_id.

### §5.3 NDAA §889 preservation

Hikvision (id=209) + Dahua (id=208) retain `notes.ndaa_section_889_note` verbatim ("NDAA Section 889 federally-restricted; state/local LE deployments persist outside the federal-procurement bar (runguide §0 scope).") — recategorization does NOT supersede the sanction note.

### §5.4 Legacy-text-notes wrapping (5 rows; Axis Communications)

5 identifier rows (id=415, 433, 448, 460, 470) had **plain-text** legacy notes from MAC-44 phase-5 step-4 follow-on² admission discipline (pre-JSON-notes convention). At update time, each plain-text payload was preserved in a JSON envelope as `{"legacy_text_notes": "<original text>", "recategorization_history": [...]}`. No data loss. CP34-pending candidate: schema-discipline sweep to normalize all legacy-text notes to JSON envelope shape.

### §5.5 BriefCam deferral rationale

BriefCam is an analytics layer on top of CCTV/ALPR — the operationally distinct value is `face_recog` (current) vs `cctv_camera` (could apply). Per board ratification G-B, defer to v1.5.x or later as an operator-decision sub-cycle.

### §5.6 Lynceus high-confidence export impact (§11 #13 carveout)

Pre-recat: 31 identifier rows for these 7 vendors had `device_category='unknown'` → excluded from Lynceus high-confidence export per §11 #13.
Post-recat: 31 identifier rows now `device_category='cctv_camera'` → eligible for Lynceus export (subject to confidence ≥85 + superseded_by IS NULL per METHODOLOGY §5).

Net Lynceus high-conf export uplift potential: up to 31 additional rows from these 7 vendors (subject to confidence ceiling per row at Step 9 regen).

### §5.7 Paste-not-cite post-state counts

```
SELECT primary_category, COUNT(*) FROM manufacturers GROUP BY primary_category;
  cctv_camera = 13 (6 new from S2 Step 4 + 7 retroactive from Step 6)
```

```
SELECT device_category, COUNT(*) FROM identifiers WHERE superseded_by IS NULL GROUP BY device_category;
  cctv_camera +31 (vs Step 5 close)
```


### §6 — v1.5.0 Stage 1 Step 7 disambig + FP-class triage

**Cycle:** v1.5.0 Stage 1 (MAC-232)
**Authority:** Board ratification 0ba8150f — G-G approved (codename batch-reject already applied at Step 5)
**Section discipline:** disambig queue triage + FP-class consolidation. SAR-class promotions (§9 below) for the 2 findings exceeding n=3 threshold.

### §6.1 — Schema-truth observation: S1 disambig queue composition

Dispatch claimed S1 disambig queue = 168 entries = 5 Phase A Elbit + 163 noisy Phase B codenames. **Inspection of `disambig_review_queue.json` shows all 168 entries are FCC grantee codes flagged for Elbit/Tadiran-alias substring disambig** (not codenames; not 163 vs 5 split). Validator §8 Step 9's "168 entries mostly Elbit/Tadiran subsidiary chain" was correct; dispatch's 5+163 breakdown was inaccurate. The G-G ratified codename batch-reject targeted a DIFFERENT staging file (`identifier_candidates/wayback_pdf_extracted_v2.json`, 347 rows — quantified at Step 5).

### §6.2 — 168 Elbit FCC grantee disambig disposition

168 entries deferred to v1.5.x **Elbit disambig sub-cycle**. Held at:
- `~/argus-internal/wave_v1_5_lexicon_expansion/session_1_military_federal/disambig_review_queue.json`
- Holding-pattern: NOT promoted to canonical this cycle (Step 5 promoted only the 15 high-confidence S1 fcc_grantee_codes, leaving these 168 as low-confidence candidates needing per-row anchor-verification).
- Future cycle requires: per-row regulatory anchor (FCC EAS direct or fccid.io verbatim grantee-name match) + reject those that match only via short alias substring ("Elbit" or "Tadiran" bare).

### §6.3 — S1 FP-class findings join SAR-15 GENERIC_RISK_CANONICALS pre-load

| finding_id | n | disposition |
|---|---|---|
| tcom_acronym_collision | 1 | join SAR-15 pre-load — require corporate-suffix anchor ('TCOM L.P.') |
| camero_substring_cameron_collision | 1 | join SAR-15 pre-load — require 'Camero-Tech' or 'Sago Systems' anchor |
| lockheed_lm_substring_collision | **134** | **promote to formal SAR-16 alias-length-floor discipline (see §9.1)** |
| mydefence_eagle_substring_collision | **41** | **promote to formal SAR-17 no-generic-product-aliases discipline (see §9.2)** |

### §6.4 — S2 FP-class findings join SAR-15

| class | disposition |
|---|---|
| motive_common_word_collision | join SAR-15; require fleet/ELD product-context + procurement-or-cellular anchor |
| sentinel_common_word_collision | join SAR-15; require offender-monitoring-context + state-DOC anchor |
| stop_short_name_allcaps_collision | join SAR-15; require SatTrack-of-People anchor AND state-DOC anchor (4-char allcaps highest-FP-risk class) |
| bosch_seo_collision | already in carveout (§11 #10); SAR-15 reinforcement note |
| trimble_surname_collision | already in carveout (§11 #10); SAR-15 reinforcement note |
| pelco_acquisition_chain_relationship | CP31 §4.6 arm-split applied at Step 4 (G-A); FP-class informational |

### §6.5 — S2 disambig queue (5 entries, post-workaround pass)

All 5 resolved by S2's workaround pass:
- Motive: FCC 2AQM7 grantee anchor confirmed
- STOP: FCC S5E grantee + Houston TX address anchor
- Sentinel: FCC VZL grantee anchor
- Bosch: §11 #10 multi-purpose carveout retained
- Trimble: §11 #10 multi-purpose carveout retained

No carry-forward to v1.5.x.

---

## SAR-16 — Alias-length-floor discipline (formal codification)

**Driven by:** v1.5.0 Stage 1 S1 finding `lockheed_lm_substring_collision` (n=134) exceeded SAR n=3 threshold.

**Rule:** When a manufacturer canonical name has an alias of length ≤3 characters (e.g., "LM" for Lockheed Martin, "BI" for BI Incorporated, "GE" for General Electric), that short alias MUST NOT be used as a bare substring match against any source corpus. Short aliases require additional anchor regex disambig:
- Word-boundary `\b` + corporate-suffix anchor (e.g., `\bLM\s+(?:Corp|Inc|Industries|Aeronautics)`), OR
- Procurement-context anchor (e.g., source field `awardee_uei` matches the canonical UEI), OR
- Product-context anchor (e.g., source field `description` contains canonical product family codename)

**Case study:** Lockheed Martin's bare 2-char alias "LM" substring-matched 134 unrelated FCC grantee entries ("Stockholm Precision Tools", "Guglielmi", "Alma Lasers", etc.). Required min-alias-length=4 floor for SAR-15 second-pass to suppress these FPs. The 134 FPs is well above the SAR n=3 codification threshold.

**Floor value:** **4 characters** minimum for bare substring matching. Aliases of length 1-3 require one of the additional anchor disciplines above.

**Implementation invariant:** SAR-15 GENERIC_RISK_CANONICALS pre-load shall enumerate every existing canonical with alias-length<4 and tag them in `notes.alias_length_floor_required=true`. New admissions with short aliases require explicit anchor regex at admission time.

**§11 #11 binding:** SAR-class amendment — formal bible-binding. Cross-references: [[feedback_per_vendor_probe_scope_discipline]] (SAR-15 + SAR-15.5 precedent), CP19 §5.2 spirit (FP-class promotion threshold).

---

## SAR-17 — No-generic-product-aliases discipline (formal codification)

**Driven by:** v1.5.0 Stage 1 S1 finding `mydefence_eagle_substring_collision` (n=41) exceeded SAR n=3 threshold.

**Rule:** Generic English-word product aliases (e.g., "EAGLE" for MyDefence's Eagle counter-UAS, "SENTINEL" for Sentinel Offender Services, "STOP" for Satellite Tracking of People, "ATLAS" for various vendors) MUST NOT be admitted as bare aliases in the `manufacturers.aliases` column. Generic product names require multi-word disambiguation:
- `<vendor> <product>` form (e.g., "MyDefence Eagle", not "EAGLE")
- `<product> <model>` form with vendor-specific suffix (e.g., "Eagle-NV", not "EAGLE")
- Per-product-family aliases stored in `notes.product_family_codenames[]` array (CP25 §3 precedent), NOT in the bare `aliases` column

**Case study:** MyDefence's "EAGLE" 5-char alias substring-matched 41 unrelated FCC grantee entries ("Eagle Industries", "Eagle Eye Networks" — separate vendor entirely, "EAGLE BROADBAND"). 41 FPs exceeds SAR n=3 codification threshold.

**Implementation invariant:** New admissions with product-family names that are common English nouns shall stage product names ONLY in `notes.product_family_codenames[]` (typed enrichment), NOT in the `aliases` column. Retroactive sweep of existing canonicals with short generic aliases is a CP34-pending candidate.

**§11 #11 binding:** SAR-class amendment — formal bible-binding. Cross-references: SAR-16 (alias-length-floor — together they form a 2-pronged alias-discipline regime), CP25 §3 (product_family_codenames typed enrichment).

---


### §7 — v1.5.0 Stage 1 Step 8 v1.5.x/v1.6.0 backlog queue

**Cycle:** v1.5.0 Stage 1 (MAC-232) Step 8
**Pointer:** Created `/PLANNED_AND_FUTURE_UPDATES.md` (new repo file) capturing deferred items from v1.5.0 Stage 1 integration.

### §7.1 v1.5.x patch backlog

- Avigilon + WatchGuard arm-under-MSI (SEC Exhibit 21 bonus from MSI 10-K FY2025)
- Elbit FCC grantee disambig sub-cycle (168 entries, sandbox-held)
- G-D DJI aliases hygiene amendment
- G-F Geo Group admission + BI arm-split
- G-B BriefCam recategorization operator-decision (deferred per board)

### §7.2 v1.6.0 new-cohort backlog

- Openpath Security, Silvus Technologies, VaaS International, RapidDeploy, Rave Wireless (SEC Ex21 bonus)
- 6 source re-attempts (DHS S&T direct, Google Play, ISED, ETSI, RRA Korea, State DOC) — 0-yield deferrals from v1.5.0 Stage 1

### §7.3 CP34-pending candidates (7 total)

1. Corporate-attestation routing at extraction time
2. S2 GitHub codename×3 dedup at extraction-time
3. identifier_type CHECK lacks `ip_address` (admit or route to network_endpoint)
4. Legacy-text-notes normalization sweep (CP-wide pre-JSON-notes residue)
5. Short-generic-alias migration to product_family_codenames (SAR-17 retroactive)
6. NDAA §889 attribution key normalization (single-field vs dual-field convention)
7. Validator-side dispatch live-state preamble verification sub-rule (3 drift incidents in v1.5.0 Stage 1)

### §7.4 §11 #11 binding

All items above carry forward into v1.5.x / v1.6.0 cycles. Full text + commit anchors live in `/PLANNED_AND_FUTURE_UPDATES.md`; this CP33 §7 entry is the bible-side pointer (per amendment-log discipline).


## SAR-18 — Classifier-Predicate Parity Discipline (`oversized_mac_range` exemplar)

**Driven by:** MAC-232 v1.5.0 Stage 1 Step 9 halt; board ratification 2026-05-22 (comment `d5de106b`).
**Authority:** §11 #11 amendment-log + cross-classifier parity invariant.

### Rule (verbatim per board)

> The `oversized_mac_range` predicate MUST be unconditional (drop ALL `mac_range` rows) until Lynceus `mac_range` expansion logic is built. `coverage_matrix.py` and `export_lynceus.py` classifiers MUST share the same predicate; future classifier additions require dual-table parity check at PR time.

### Driving case

At MAC-232 Step 6 G-B retroactive recategorization (commit `0e13b20`), row `id=9404` (Eagle Eye Networks, `64:33:b5:4/28`, OUI-28, `mac_range_size=256`) was lifted from `device_category='unknown'` → `cctv_camera`. This unmasked a latent classifier-divergence:

| Classifier | Predicate (pre-Path β) |
|---|---|
| `db/validation/coverage_matrix.py::_classify_row` (lines 561-565) | `mac_range_size(row.identifier) > 256` (strict greater-than) |
| `db/validation/export_lynceus.py::_classify_row` (lines 530-537) | UNCONDITIONAL once `unknown_category` gate clears |

At v1.4.1 ship: all 8 live `mac_range` rows had `device_category='unknown'`; both classifiers attributed to `unknown_category` first → divergence inert. The `export_lynceus.py` comment block at line 532-537 explicitly stated *"Currently no such row exists in the active identifiers set"* as a load-bearing assumption — that comment was true at v1.4.1 ship; Step 6 G-B violated it without updating either predicate.

Step 9 Stage B `_reconcile` at line 645 halted with verbatim:
```
Halt: argus_export.json: row id=9404 writer-classified as 'oversized_mac_range'
      but MAC-45 has no entry — input drift, STOP-THE-LINE.
```

### Resolution (Path β)

Patched `db/validation/coverage_matrix.py` lines 561-565 (this commit) to drop the `> MAC_RANGE_EXPANSION_CEILING` strict-greater-than predicate. The predicate now reads:

```python
if row.identifier_type == "mac_range":
    return "oversized_mac_range"
```

This matches `export_lynceus.py`'s posture. Both classifiers will agree on every `mac_range` row regardless of `mac_range_size`. id=9404 + id=470 + the other 6 `mac_range` rows all drop to `oversized_mac_range` and stay out of the Lynceus export.

Paths α (build expansion logic) and γ (re-revert id=9404 to `unknown`) were rejected:
- Path α: feature build deferred to v1.6.0+ under CP34 §4.4 slot (already queued in `PLANNED_AND_FUTURE_UPDATES.md`)
- Path γ: leaves divergence latent; would re-fire on any future mac_range below-ceiling recategorization

### Forward-going parity invariant

Future classifier rule additions in `_classify_row` of either module MUST:
1. Add the same rule (verbatim predicate) in BOTH modules in the same PR
2. Surface in the PR description as a "dual-table parity" note
3. Include a regression test that exercises the rule on at least one representative row

This discipline extends the CP21 cumulative-full-enum sweep spirit (which governs CHECK constraint parity across migrations) to **runtime classifier predicates**. Reviewers MUST verify both files at PR review time.

### CP34 §4.4 carry-forward

`§4.4 mac_range expansion-ceiling-boundary disposition` candidate already queued in `PLANNED_AND_FUTURE_UPDATES.md` v1.6.0 backlog. SAR-18 supersedes that candidate's "Path α" branch (build expansion); the queue entry now narrows to: *"if and when Lynceus v0.4+ ships a mac_range expansion strategy, lift SAR-18's unconditional-drop and unmask the expansion path. Both classifiers must remain in lockstep."*

### Cross-references

- MAC-232 Step 9 close-out: `~/argus-internal/wave_v1_5_lexicon_expansion/_integration_stage1/step9_lynceus_export.md`
- Step 6 G-B audit (the unmasking event): `_phase_6_recat/step6_audit.json` + commit `0e13b20`
- Prior dispatch-vs-actual schema-truth observations (3 total in v1.5.0 Stage 1): G-E pair_kind, Step 4 NDAA, Step 7 disambig composition
- Existing memory: [[feedback_bible_amendment_downstream_consumer_audit]] (sibling discipline for bible amendments → downstream consumers)


## Correction Pass 35 (draft — CP35-pending; ratification at next CP34 dispatch or sooner if operator wants) — §4.4 Lynceus mapping for `network_discovery_protocol_pattern` (mig-0028 / CP34 Wave G/H v1 admission)

**Origin:** MAC-239 Wave G/H v1 integration orchestration-completion pass, 2026-05-23.
**Authority:** DBArchitect-surfaced HALT-class downstream-consumer-update gap at canonical Lynceus export regen (see `_dbarchitect_signoff.md` §Task 5). Pending CEO ratification + dispatch.
**Status:** **DRAFT — CP35-pending.** Not ratified. Bible HEAD (`PROJECT_BIBLE.md` §4.4) NOT amended by this entry — that's CP35-ratification scope.

### Why this Correction Pass exists

Mig-0028 (CP34, this v1.5.2 cycle) admitted `network_discovery_protocol_pattern` (NDPP) to the `identifiers.identifier_type` CHECK enum. Eighteen NDPP rows were promoted under that CP from the Wave G/H v1 cohort (high-confidence `manufacturer_app` rows on `device_category='cctv_camera'` devices — Bosch, Axis, Hanwha, Pelco, Avigilon network-discovery-pattern observations from companion-app static analysis). The CP34 amendment landed the schema mutation + identifiers admission but **did not update the §4.4 Lynceus consumer-side mapping** in `db/validation/export_lynceus.py`.

At canonical Lynceus export regen (DBArchitect Task 5, 2026-05-23), `_classify_row` halted with:

```
Halt: row id=36716 identifier_type=network_discovery_protocol_pattern has no §4.4 mapping
but reached the survivor branch — §4.4 schema drift?
```

This is the **exact failure mode** codified in two operator-memory entries that pre-existed this cycle:

- [[feedback_promotion_gate_needs_export_dryrun]] — promotion gate Step 1 staging needs export-regen dry-run before declaring §11 #11 self-binding satisfied.
- [[feedback_bible_amendment_downstream_consumer_audit]] — bible amendments need parallel downstream-consumer updates as sibling commits.

CP34 (the Wave G/H v1 integration CP) did not surface this gap because the integration cycle's promotion gate did not run an export-regen dry-run as a precondition. The 18 NDPP rows reached the survivor branch (not dropped by §11 #13 / §11 #14 / §11 #12 / CP7 / SAR-18 unconditional `oversized_mac_range` drop) with no `IDENTIFIER_TYPE_TO_PATTERN_TYPE` mapping AND no `DROPPED_REASONS` entry — the explicit halt path in `export_lynceus.py`.

### Proposed amendment scope (to be ratified at CP35 dispatch)

§4.4 of `PROJECT_BIBLE.md` currently enumerates the disposition for each `identifiers.identifier_type` under the Argus → Lynceus consumer contract: either MAP (route to a Lynceus `pattern_type`) or DROP (with explicit rationale into `DROPPED_REASONS`). NDPP needs a §4.4 entry. Two disposition options frame the CP35 decision; both options are valid and the choice depends on Lynceus consumer-side roadmap clarity at ratification time.

#### Disposition option (a) — MAP to Lynceus `discovery_protocol_signature` pattern (new pattern_type in Lynceus v0.3)

Add NDPP to `IDENTIFIER_TYPE_TO_PATTERN_TYPE` with a new Lynceus-side pattern_type slot:

```python
IDENTIFIER_TYPE_TO_PATTERN_TYPE = {
    # …existing mappings…
    "network_discovery_protocol_pattern": "discovery_protocol_signature",  # CP35
}
```

Requires sibling work in the Lynceus repository: introduce `discovery_protocol_signature` as a recognized `pattern_type` in Lynceus v0.3+ scanner with semantics documented (matcher shape: regex/substring match on observed mDNS-SD / WS-Discovery / SSDP / ONVIF-WS-Discovery responses against the pattern body extracted from companion APK). This is sibling-CP work crossing the Argus ↔ Lynceus contract surface (cf. CP9 Talos → Lynceus rename slate + CP11 dual-artifact contract + CP16 §4.4 Lynceus mapping for the CP14 cluster — all prior precedents for `identifier_type → pattern_type` admission requiring parallel Lynceus consumer support).

#### Disposition option (b) — DROP with rationale `NDPP_pending_lynceus_v0_3_scanner_support`

Add NDPP to `DROPPED_REASONS` with explicit narrow rationale:

```python
DROPPED_REASONS = {
    # …existing entries…
    "network_discovery_protocol_pattern": "NDPP_pending_lynceus_v0_3_scanner_support",  # CP35
}
```

NDPP rows survive in `identifiers` (high-confidence cohort retained for future export-time admission once Lynceus consumer-side gains pattern support); they are deliberately dropped at export-time until Lynceus v0.3 ships scanner-side discovery-protocol-signature matching. This is the conservative posture: the 18 NDPP rows stay in DB as canonical evidence; only the export-side surface is gated.

This option mirrors the CP16 §4.4 cluster decision for several CP14-admitted identifier_types that were DROP'd pending Lynceus consumer-side support (cf. CP16 12 DROPPED entries vs 3 MAP). Default posture at CP35 ratification if Lynceus v0.3 roadmap is silent: **option (b)** — DROP with explicit pending-rationale.

### Sibling consumer files requiring parallel update (per [[feedback_bible_amendment_downstream_consumer_audit]] discipline)

CP35 ratification MUST land all of the following in a single coordinated commit (no partial application):

1. **`PROJECT_BIBLE.md` §4.4** — bible text amendment adding NDPP row to the §4.4 mapping table (either MAP or DROP per ratified option).
2. **`db/validation/export_lynceus.py`** — `_classify_row` consumer side: add NDPP to either `IDENTIFIER_TYPE_TO_PATTERN_TYPE` (option a) or `DROPPED_REASONS` (option b).
3. **`db/validation/coverage_matrix.py`** — `_classify_row` parity check (per SAR-18 classifier-predicate parity invariant). If option (b), NDPP routes to coverage-matrix "DROPPED" column with the same rationale string; if option (a), NDPP routes to a new pattern-type column.
4. **CP35 §11 #11 self-binding** — final CP35 entry must cite the consolidated git commit hash + verify both `_classify_row` modules agree.

### Evidence (CP35-pending citation slate)

- `_dbarchitect_signoff.md` §Task 5 — DBArchitect HALT-class disclosure on canonical Lynceus export regen at row id=36716.
- `~/argus/exports/v1_5_2_raw_snapshot/argus_export_high_confidence_20260523T030803Z.json` (sha `781e759c60b408220a41040a0205e20888aa4798cfc35740cf1871058c4d51c8`, 35,434 rows) — raw-snapshot export supplementing the stale canonical Lynceus export at v1.5.2 ship per Task 5 option (iii) default disposition.
- `~/argus/exports/v1_5_2_raw_snapshot/argus_export_full_20260523T030803Z.sql.gz` (sha `6d97c20ab3aebc9d26069e10cd4ef0e1b5f168dc24bbf4b6527ebc90b5c7bd84`) — full DB dump pair.
- `~/argus/extraction_outputs/mac45/coverage_matrix.md` + `coverage_matrix_report.json` — coverage matrix regenerated 0-halts against v1.5.2 DB; NDPP rows present in active set.
- Mig-0028 (`db/migrations/0028_cp34_*.sql`) — the CP34 schema mutation that admitted NDPP without sibling §4.4 amendment.
- Lynceus consumer-side roadmap (TBD at CP35 dispatch) — option (a) viability hinges on Lynceus v0.3 scanner support for `discovery_protocol_signature` pattern_type.

### Cross-references

- **Existing memory** [[feedback_promotion_gate_needs_export_dryrun]] — argues this exact failure mode should be caught at promotion-gate Step 1, not at post-CP export-regen. CP35 ratification should also tighten the promotion-gate runguide to require export-regen dry-run as a precondition (CP34 lacked this check; the gap reproduced here).
- **Existing memory** [[feedback_bible_amendment_downstream_consumer_audit]] — codifies the sibling-commit discipline that CP35 must satisfy.
- **CP16** — first §4.4 Lynceus mapping CP (for the CP14 cluster); same discipline shape, prior precedent for both MAP and DROP options.
- **CP34** (Wave G/H v1 integration, this cycle) — the upstream amendment that admitted NDPP without satisfying §4.4 sibling-commit discipline. CP35 closes that gap.
- **SAR-18** — classifier-predicate parity invariant; CP35 must satisfy SAR-18 by updating `coverage_matrix.py` in lockstep with `export_lynceus.py`.

### §11 #11 self-binding pending

This entry stages CP35 as draft. The §11 #11 self-binding clause activates at CP35 ratification: the consolidated commit hash applying the §4.4 amendment + sibling consumer updates (export_lynceus.py + coverage_matrix.py) + (if option a) the cross-repo Lynceus v0.3 commit must be enumerated here at ratification time. Currently UNRATIFIED — no commit, no binding.

═══════════════════════════════════════════════════════════════════════


## SAR-19 (draft — SAR-19-pending; ratification at next CP34 OR sooner if operator wants this codified before next dispatch cycle) — Dispatch-time pre-authorized DML requires corpus-wide diagnostic predicate (DBArchitect surface)

**Driven by:** MAC-239 Wave G/H v1 integration, DBArchitect Task 2 refusal of dispatch-pre-authorized DML on 815 `axis_communications` rows (`_dbarchitect_signoff.md` §Task 2), 2026-05-23.
**Authority:** Pending CEO ratification. Codification proposed at n=1 due to asymmetric §11 #1 fabrication risk; rationale enumerated below.
**Status:** **DRAFT — SAR-19-pending.** Bible HEAD `PROJECT_BIBLE.md` NOT amended by this entry.

### §1 — The rule

> Any dispatch that pre-authorizes DML (UPDATE / DELETE / non-idempotent INSERT against canonical DB) MUST carry an explicit `corpus_diagnostic_predicate` clause stating: (i) the read-only `SELECT … COUNT(*) WHERE …` predicate that defines the affected row scope; (ii) the expected row count matching the dispatch's framed problem; (iii) at least one corpus-wide adjacency check (a sibling `SELECT … GROUP BY …` query that surfaces whether the affected rows share a single semantic shape — same `source_url` / `source_type` / `identifier_type` / first-seen window — aligning with the framed problem, OR whether they are part of a broader corpus that contradicts the dispatch's framing).
>
> The subagent (DBArchitect or equivalent DML-executing role) executes the predicate as a precondition before executing the pre-authorized DML. If the corpus diagnostic returns row counts or shapes that contradict the dispatch's framing, the subagent MUST refuse execution and surface the diagnostic mismatch for CEO ratification — even with pre-authorization in hand.

### §2 — Why this discipline binds

Pre-authorization in a dispatch is a **necessary** condition for DML execution but is not **sufficient**. The dispatch author works from a mental model of the DB at dispatch-time; the DBArchitect executes against the actual DB at execution-time. Corpus-wide evidence visible at execution-time can contradict the dispatch's framing — and when it does, silent execution of mis-framed DML produces §11 #1-class fabrication shape (writing canonical state that does not match the evidence in the DB).

The DBArchitect retains diagnostic authority to refuse execution. This is structurally adjacent to the existing Validator-side [[feedback_scan_diagnostics_distinguish_convention_from_corruption]] discipline but on the DBArchitect surface (DML execution authority rather than read-only validation surface). It is also the DBArchitect-side mirror of the operator-side [[feedback_paste_not_cite_with_single_example_hides_fanout]] discipline (CEO must re-run aggregate count queries before ratifying scope rather than trusting "count + single illustrative row" prose).

### §3 — Driving case (n=1 — MAC-239 Wave G/H v1 integration, Task 2)

The MAC-239 dispatch framed 815 `axis_communications` rows under `device_category='unknown'` as drift requiring UPDATE to canonical `Axis Communications` + `device_category='cctv_camera'`. Pre-authorized DML:

```sql
UPDATE identifiers SET manufacturer='Axis Communications', device_category='cctv_camera'
WHERE manufacturer='axis_communications' AND device_category='unknown' AND superseded_by IS NULL;
```

DBArchitect executed the read-only corpus-wide diagnostic before executing the DML:

```sql
SELECT manufacturer, device_category, source_type, identifier_type, COUNT(*)
FROM identifiers
WHERE manufacturer IN ('axis_communications', 'Axis Communications')
  AND superseded_by IS NULL
GROUP BY 1,2,3,4 ORDER BY 1,5 DESC;
```

The diagnostic surfaced two findings that contradicted the dispatch's framing:

1. **All 815 affected rows are CP29 hostname corpus** (`identifier_type IN ('vendor_controlled_hostname', 'vendor_controlled_hostname_deprecated')` — 812 from `crt.sh` certificate transparency, 3 from `wave_i_aggregate`), with single first-seen window 2026-05-20T00:30:00Z. None are CCTV-product identifier types (no BLE / OUI / NDPP). Setting `device_category='cctv_camera'` on hostnames like `auth.axis.com` / `status.axis.com` / `developer.axis.com` is fabrication-shape — it conflates vendor-primary-line with per-hostname device-category attribution.
2. **The lowercase manufacturer convention is corpus-wide, not axis-specific.** A sibling group-by surfaced 11,978 lowercase rows across the full CP29 hostname corpus (axon=2436, honeywell=1742, jacobs=1253, l3harris=846, axis_communications=815, …) vs 23 Title Case rows (Attenti, Tiandy, Motive, Hanwha Vision, Flock Safety, Pelco, …) and 261 unattributed. Notably `Flock Safety` (Title Case, 2 rows) AND `flock_safety` (lowercase, 67 rows) co-exist for the same vendor — unambiguous evidence of systemic CP29 corpus normalization inconsistency, not axis-specific drift. The 23 Title Case rows are the actual drift relative to the 11,978-row lowercase convention.

Executing the dispatched DML would have written the **opposite** of the corpus convention (Title-Case-only update on 815 axis rows while leaving 11,163 other lowercase rows un-normalized), creating new inconsistency *within* CP29 — a §11 #1-class fabrication-shape outcome.

DBArchitect refused execution, surfaced the diagnostic mismatch in `_dbarchitect_signoff.md` §Task 2, and escalated to CEO. Default disposition: defer to standalone hygiene cycle with properly-scoped dispatch addressing the entire 12,242-row CP29 hostname corpus in one pass.

### §4 — Why codify at n=1 (asymmetric §11 #1 risk)

The codification-default at this project is to wait for n=3 occurrences before promoting an observation to a SAR. SAR-19 deviates from that default on asymmetric-risk grounds:

- **Cost of waiting for n=3**: future dispatches may continue to pre-authorize DML without `corpus_diagnostic_predicate`. If a future DBArchitect executes a similarly mis-framed pre-authorization, the DML lands silently, canonical state acquires §11 #1 fabrication shape, and the breach may not be detected until a downstream consumer-side audit fires — by which time the rows are mixed with thousands of unrelated rows and rollback becomes expensive (cf. MAC-202 / MAC-204 §10b sid=13 admit-then-rebind which required 20-row rebind across 5 vendor APKs to undo a similar mis-framing).
- **Cost of codifying at n=1**: a one-line dispatch-template addition (`corpus_diagnostic_predicate: <SQL>`) for every future DML-authorized dispatch. Marginal authoring overhead; zero risk.
- **Precedent**: SAR-13 was codified at n=1 (Wave G runguide schema fabrication) on similar asymmetric-risk grounds (silent fabrication outweighs codification cost). MAC-239 Task 2 establishes the same risk profile on the DBArchitect-DML surface.

The n=1 framing rationale is recorded explicitly so future ratification cannot mistake SAR-19 for a discipline-evolution candidate awaiting n=3.

### §5 — Bound surface (DBArchitect)

SAR-19 binds the **DBArchitect** subagent role specifically — the agent invoked with DML-execution authority against canonical `~/argus/db/argus.db`. It does NOT bind:

- Validator subagent (read-only DB authority; covered by [[feedback_scan_diagnostics_distinguish_convention_from_corruption]] sibling discipline).
- CEO/operator-surface paste-not-cite discipline (covered by [[feedback_paste_not_cite_with_single_example_hides_fanout]]).
- Worker subagents executing idempotent reads or self-contained schema migrations against their own scope.

SAR-19 fills the third surface in the discipline triad: validator (read), operator (ratify), DBArchitect (write).

### §6 — Forward application

At each future DML-authorized dispatch:

1. **Dispatch author** includes a `corpus_diagnostic_predicate` clause in the §0 baseline or dispatch-DML section, naming the read-only SQL the DBArchitect must execute before the authorized DML.
2. **DBArchitect** executes the diagnostic predicate as a precondition. If the result matches the dispatch's framing (expected row count + expected semantic shape), proceed with DML. If the result contradicts the framing, refuse execution + surface mismatch in signoff doc + escalate to CEO.
3. **Refusal is not failure.** A refusal-with-diagnostic-evidence is a successful DBArchitect outcome; silent mis-execution is the failure mode SAR-19 prevents.

### §7 — Codification surfaces

- `BIBLE_AMENDMENTS.md` (this entry; staged as draft).
- `~/argus/docs/runguide/dbarchitect_*.md` (TBD path — DBArchitect runguide if it exists; otherwise added at ratification time).
- Future operator dispatch templates for DBArchitect: add explicit `corpus_diagnostic_predicate` slot.
- Cross-reference in [[feedback_scoped_updates_via_source_row_key]] (existing memory; SAR-19 generalizes scope-discipline to the corpus-wide diagnostic predicate).

### §8 — Cross-references

- `_dbarchitect_signoff.md` §Task 2 (driving case, full audit).
- [[feedback_scan_diagnostics_distinguish_convention_from_corruption]] — Validator-side sibling discipline.
- [[feedback_paste_not_cite_with_single_example_hides_fanout]] — operator-side sibling discipline.
- [[feedback_scoped_updates_via_source_row_key]] — existing scope-discipline memo, narrower in scope than SAR-19.
- SAR-13 — n=1 codification precedent (asymmetric-risk justification).
- §11 #1 — fabrication-shape canonical authority (the harm SAR-19 prevents).

═══════════════════════════════════════════════════════════════════════


## §11 #18 (draft — §11 #18-pending; ratification at next CP34 cycle per Gate I-5 ratification at MAC-239 board comment 50ffacc8) — Operator-authorized in-cycle DML override pattern

**Origin:** Wave G/H v1 integration (MAC-239), Gate I-5 ratification 2026-05-23 — operator DEFER to next CP34 cycle. Draft language pre-authored by prior CEO pass at `~/argus-internal/wave_g_h_v1_integration/handoff/proposed_bible_amendment_additions.md`; this entry stages the draft into canonical bible-amendments file.
**Authority:** Board comment `50ffacc8` (2026-05-23) — "Gate I-5 — DEFER to next CP34 cycle; stage proposed_bible_amendment_additions.md entry with n=2 evidence + draft language."
**Status:** **DRAFT — §11 #18-pending.** Bible HEAD `PROJECT_BIBLE.md` §11 NOT amended by this entry — that's CP34 ratification scope.

### Draft language for §11 (to be ratified at next CP34)

> **#18 — Operator-authorized in-cycle DML override.** When dispatch §0 baseline
> verification surfaces a drift that should-have-shipped in a prior v1.5.x patch
> and the in-flight cycle's §11 envelope is read-only (no schema migration, no
> `identifiers` writes), the operator may authorize a single-statement DML
> override against the canonical DB via in-session reply. The pattern is
> constrained as follows:
>
> 1. **Authorization is per-statement and per-session.** Pre-authorization is
>    not permitted. The operator must reply in the active dispatch session with
>    explicit "patch it" (or equivalent) intent.
> 2. **Single-statement scope.** Multi-DML batches require dispatch-class
>    authorization (a new dispatch with explicit DML scope), not in-cycle
>    override.
> 3. **Drift-remediation only.** The override must address a baseline-drift
>    discovered at §0 verification; it is not a vehicle for new feature work.
> 4. **Mandatory pre-state and post-state capture** in an audit doc named
>    `OPERATOR_AUTHORIZED_OVERRIDE_<TOPIC>.md` in the cycle's worktree. Must
>    include the verbatim SQL, the row(s) affected, pre-state, post-state, and
>    operator authorization timestamp.
> 5. **Mandatory pre-patch backup.** Snapshot the canonical DB to
>    `argus.db.pre_<topic>_<UTC-timestamp>` with sha256 captured.
> 6. **Mandatory cross-reference in cycle handoff.** The cycle's
>    `INTEGRATION_HANDOFF.md` and any session-summary doc must cite the
>    override audit doc as `operator_authorized_exception[]`.
> 7. **Read-only thereafter.** After the override executes, the cycle returns
>    to read-only DB posture for the remainder of the run.

### Evidence (n=2 this v1.5.x cycle)

| Date | Topic | Audit doc | Backup | Authority |
|---|---|---|---|---|
| 2026-05-22 AM | Pelco (id=254) arm-tag DML | (Pelco override doc — referenced in [[project_mac239]] continuation; predates the Avigilon doc shape) | (Pelco pre-patch backup snapshot under `~/argus/db/`) | Operator in-session reply, dispatch ~2026-05-22T~17Z |
| 2026-05-22 PM | Avigilon (id=6) arm-tag DML | `~/argus-internal/wave_g_h_v1_track_a/OPERATOR_AUTHORIZED_OVERRIDE_AVIGILON_ARM_PATCH.md` | `~/argus/db/argus.db.pre_avigilon_arm_patch_20260522T220908Z` | Operator in-session reply, session-1779485836426, 2026-05-22T22:09:08Z |

### Why now (rationale for codification)

Two occurrences in a single v1.5.x cycle (within 6 hours of each other) establishes the pattern as load-bearing rather than one-off. Both:

- Were arm-tagging follow-ons (`parent_manufacturer_id` + `is_arm` + `query_default`) addressing pre-existing manufacturer-record drift carrying forward from v1.5.0 Stage 1 (MAC-232).
- Were authorized identically (single-statement DML; explicit operator in-session reply).
- Were logged identically (audit doc + backup + cross-reference into INTEGRATION_HANDOFF.md `operator_authorized_exception[]` slot).

Codifying the protocol prevents future cycles from re-litigating the authorization shape and ensures the audit-doc + backup discipline becomes mandatory rather than ad-hoc.

### Open question for operator at codification time

- Should the audit doc template be added to the canonical worktree under `~/argus/docs/runguide/operator_override_template.md` to standardize future audit-doc shape? Currently the n=2 docs were authored ad-hoc with slight format differences (the Avigilon doc shape is more verbose; the Pelco doc shape is leaner). At CP34 ratification, operator decision is requested on template standardization vs. continued ad-hoc-with-mandatory-fields posture.

### Cross-references

- Source draft: `~/argus-internal/wave_g_h_v1_integration/handoff/proposed_bible_amendment_additions.md` (pre-authored by prior CEO pass; this entry preserves the draft verbatim with added shape-conforming framing).
- Gate I-5 ratification: MAC-239 board comment `50ffacc8` (2026-05-23) — DEFER to next CP34.
- Cycle handoff: `~/argus-internal/wave_g_h_v1_integration/INTEGRATION_HANDOFF.md` references this staging file.
- Avigilon audit doc: `~/argus-internal/wave_g_h_v1_track_a/OPERATOR_AUTHORIZED_OVERRIDE_AVIGILON_ARM_PATCH.md` (load-bearing — operator can read for shape reference at CP34 ratification).
- Pelco audit doc + override log: referenced in MAC-239 continuation; `_operator_authorized_overrides_log.md` (n=2 entries — Pelco AM + Avigilon PM).
- Sibling discipline: SAR-19 (this same staging pass) — generalizes the DBArchitect-side refusal authority for dispatch-pre-authorized DML; SAR-19 + §11 #18 together form a 2-pronged DML-authorization regime where pre-authorization (SAR-19) and in-cycle override (§11 #18) are the two distinct paths to canonical-DB writes outside of standard schema-migration channels.

### §11 #11 self-binding pending

This entry stages §11 #18 as draft. §11 #11 self-binding activates at CP34 ratification: the consolidated commit hash applying the §11 #18 amendment to `PROJECT_BIBLE.md` §11 must be enumerated here at ratification time. Currently UNRATIFIED — no commit, no binding.

