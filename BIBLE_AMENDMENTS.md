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
**Commit:** `<backfilled>` — `docs(bible): correction pass 5 — §4.1 in_vehicle_router + §4.5 severity + §4.2 procurement_records doc + §12 geographic_scope`
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
