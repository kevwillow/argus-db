# Lynceus engineer handoff — Argus v1.4.1

**Version:** v1.4.1 (Stage 1 rc1 tag `v1.4.1-rc1` at commit `6d33fa8` / annotated tag-object `e370777`; Stage 2 codification at `9f76fd7`; final v1.4.1 tag pending Phase 5)
**Predecessor:** v1.4.0 — commit `1c663ca` — 2026-05-19 20:52 EDT
**Stage 2 coordination:** [MAC-219](/MAC/issues/MAC-219) parent; Phase 1 ratified at [MAC-220](/MAC/issues/MAC-220); this handoff authored at [MAC-222](/MAC/issues/MAC-222) (Validator)
**DB:** `~/argus/db/argus.db` schema_version=26
**Date authored:** 2026-05-21

This document is a Lynceus-consumer-oriented summary of what changed in the Argus corpus between v1.4.0 and v1.4.1. Every count claim derives from a live `~/argus/db/argus.db` read; every commit cited resolves on `v1.4.1-integration-stage-1` at HEAD `9f76fd7`. Lynceus engineers should consume this against their ingest pipeline: schema-version accept-list, identifier_type enum, export shape, and `_meta.dropped_in_export` reconciliation.

---

## §1 — Ship metadata

| Anchor | v1.4.0 | v1.4.1 (this ship) | Source of truth |
|---|---|---|---|
| Tag commit | `1c663ca` | rc1 = `6d33fa8`; final tag pending Phase 5 | `git tag --list 'v1.*'` |
| Branch | `main` | `v1.4.1-integration-stage-1` (rc1) | `git branch --show-current` |
| `schema_version` | 24 | **26** | `MAX(version) FROM schema_version` |
| `identifiers` total | 34,872 (per draft baseline) | **35,310** | live DB |
| `identifiers` active (`superseded_by IS NULL`) | 34,792 | **34,964** | live DB |
| `identifiers` superseded (chained) | 80 | **342** | `superseded_by IS NOT NULL AND superseded_by != id` |
| `identifiers` withdrawn-no-successor (self-loop) | 0 | **4** | `superseded_by = id` |
| `manufacturers` | 51 | **52** (+1 arm row) | live DB |
| `sources` | 66 | **71** | live DB |
| `raw_observations` | 146,188 (per draft baseline) | **146,573** | live DB |
| `behavioral_signatures` | 201 | **201** (unchanged in v1.4.1) | live DB |

Pre-state anchors above the `v1.4.0` column are drawn from the v1.4.0-final Stage-1 close report; current-state column is verified against the live `argus.db` post Phase 1 (CP32 / mig-0026) landing. v1.4.0 schema=24 is consistent with `git ls-tree v1.4.0 -- db/migrations/` containing 24 migration files (0001–0024).

---

## §2 — Schema migration roll-up (mig-0022..0026)

Net delta v1.4.0 → v1.4.1: **+2 schema bumps** (mig-0025, mig-0026) plus one data-only addendum sharing schema slot 26 (mig-0026a).

| Migration | Applied | CP anchor | Scope |
|---|---|---|---|
| `0022_fcc_citation_deferred_queue` | 2026-05-18 | CP27 staging | New `fcc_citation_deferred_queue` table for deferred-fetch FCC-citation rows. **Already shipped at v1.4.0.** v1.4.0 → v1.4.1 net delta: none. |
| `0023_identifier_type_check_extension_cp28` | 2026-05-19 00:35 | CP28 | `identifier_type` CHECK enum +3 (Wave H desktop-axis vendor-registered non-BLE cluster: `windows_installer_productcode_vendor_registered`, `windows_com_clsid_vendor_registered`, `vendor_document_uuid_cloud_reference`). **Already shipped at v1.4.0** (file present in v1.4.0 tree). |
| `0024_cp29_vendor_hostname_corpus_value_classes` | 2026-05-20 00:22 | CP29 | `identifier_type` CHECK enum +3 (Wave I vendor cloud-infrastructure hostname corpus: `vendor_controlled_hostname`, `vendor_cloud_endpoint_url`, `vendor_controlled_hostname_deprecated`). **Already shipped at v1.4.0** (file present in v1.4.0 tree). |
| **`0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke`** | 2026-05-20 22:03 | CP31 | **NEW at v1.4.1.** `identifier_type` CHECK enum +2 (`fcc_grantee_code`, `equipment_class_code`); `pair_kind` CHECK enum +1 (`fcc_grantee_equipment_class`); `manufacturers` table +3 columns (`parent_manufacturer_id INTEGER NULL REFERENCES manufacturers(id)`, `is_arm BOOLEAN NOT NULL DEFAULT 0`, `query_default TEXT NOT NULL DEFAULT 'visible' CHECK (query_default IN ('visible','hidden_arm'))`); Parrot Automotive arm row id=222 inserted inline (first hub-and-spoke arm). |
| **`0026_cp32_device_category_automotive_telematics`** | 2026-05-21 16:54 | CP32 §1 | **NEW at v1.4.1.** `device_category` CHECK enum +1 (`automotive_telematics`) applied to BOTH `identifiers.device_category` AND `behavioral_signatures.device_category` (dual-table CHECK literal sweep — CP21 cumulative-enum spirit). Idempotency contract verified via 2nd-run audit. |
| `0026a_phase10_vendor_apk_sources_admission` | 2026-05-20 | CP32 §1 Na_ sub-slot precedent | **NEW at v1.4.1.** Data-only addendum (no schema mutation, no `schema_version` bump). 5 INSERT OR IGNORE INTO sources (sid 67–71: Hikvision Hik-Connect, Dahua DMSS, Motorola Solutions WAVE PTT, Parrot FreeFlight 6, DJI Industry Pilot — all `source_type='manufacturer_app'` tier 3). Originally `0026_phase10_vendor_apk_sources_admission.sql`; renamed at commit `398c8b8` per the new **`Na_` sub-slot convention** codified inline at CP32 §1 (data-only addendums sharing a numeric slot with a schema-mutating migration use `Na_…` lexical-after suffix). |

**Na_ sub-slot convention (forward-looking).** From v1.4.1 onward, filename↔schema_version 1:1 holds for schema-mutating migrations (`N_…`); data-only addendums live alongside via `Na_/Nb_/…`. CP32 §1 documents the precedent; no retroactive rename of prior data-only migrations is implied.

---

## §3 — Identifier-type enum delta v1.4.0 → v1.4.1

Net delta: **identifier_type CHECK enum widened 54 → 56** (+2 from CP31; CP29's +3 was already at v1.4.0). The full v1.4.1 enum has 56 values; the table below enumerates only the v1.4.1-new types.

| identifier_type | CP anchor | Active rows at v1.4.1 | Lynceus export disposition |
|---|---|---|---|
| `fcc_grantee_code` | CP31 (mig-0025) | 17 | **DROPPED — `_meta.dropped_in_export.type_mapping_unmapped`** per CP32 §3. Not in `IDENTIFIER_TYPE_TO_PATTERN_TYPE`; surfaces as a DROPPED stub in `db/validation/export_lynceus.py:DROPPED_REASONS` (commit `ed3f75d`). Future §4.4 MAP ratification would unlock surfacing in exports. |
| `equipment_class_code` | CP31 (mig-0025) | 41 | **DROPPED — `_meta.dropped_in_export.type_mapping_unmapped`** per CP32 §3. Same disposition as `fcc_grantee_code`. |

**Important reader note — CP29 5 deferred MAP types.** Three CP29-era types (`vendor_controlled_hostname`, `vendor_cloud_endpoint_url`, `vendor_controlled_hostname_deprecated`) plus the 2 CP31 types above land as 5 DROPPED stubs in `_meta.dropped_in_export.type_mapping_unmapped`. Stage 1 v1.4.0 already had the CP29 enum extension but had not codified the §4.4 MAP disposition; Stage 2 Phase 1 (CP32 §3 / commit `ed3f75d`) codifies the DROPPED disposition for all 5. **Effect for Lynceus consumers: these 5 will NOT surface in Lynceus exports at v1.4.1; future §4.4 MAP ratification at a later CP would unlock them.** No Lynceus enum extension required.

| Type | Active rows | Disposition |
|---|---|---|
| `vendor_controlled_hostname` (CP29) | 11,676 | DROPPED — `type_mapping_unmapped` |
| `vendor_cloud_endpoint_url` (CP29) | 1 | DROPPED — `type_mapping_unmapped` |
| `vendor_controlled_hostname_deprecated` (CP29) | 565 | DROPPED — `type_mapping_unmapped` |
| `fcc_grantee_code` (CP31) | 17 | DROPPED — `type_mapping_unmapped` |
| `equipment_class_code` (CP31) | 41 | DROPPED — `type_mapping_unmapped` |

**Device-category interaction.** All currently-live rows of the 5 stub types carry `device_category='unknown'`, so they additionally tally via the §11 #13 unknown-category carve-out. The addition of these 5 to `DROPPED_REASONS` did not change any live row's bin classification at v1.4.1 — they were already being dropped under the unknown-category gate; CP32 §3 codifies the disposition more precisely.

---

## §4 — Source admissions v1.4.0 → v1.4.1

Net delta: **+5 sources** (sids 67–71), all admitted via mig-0026a (commit `d48e50a`) under [MAC-204](/MAC/issues/MAC-204) Phase 10b (Hypothesis C — admit-then-rebind per CEO disposition on MAC-202).

| sid | Name | `source_type` | tier | License posture |
|---|---|---|---|---|
| 67 | Hikvision Hik-Connect (com.hikvision.hikconnect@6.11.631.0506) | `manufacturer_app` | 3 | Proprietary; static analysis only under 17 USC §1201(j) + 37 CFR §201.40(b); DMCA security-research carve-out applies. Per sid 13/14 envelope. |
| 68 | Dahua DMSS (com.mm.android.DMSS@2.4.14) | `manufacturer_app` | 3 | Same as sid 67. |
| 69 | Motorola Solutions WAVE PTT (com.motorolasolutions.wave@3.1.8.47141) | `manufacturer_app` | 3 | Same as sid 67. |
| 70 | Parrot FreeFlight 6 (com.parrot.freeflight6@6.7.6) | `manufacturer_app` | 3 | Same as sid 67. |
| 71 | DJI Industry Pilot (com.dji.industry.pilot@v1.9.0) | `manufacturer_app` | 3 | Same as sid 67. |

These five sources are **infrastructure-only at v1.4.1** — the row admissions that anchor identifier provenance to these sids land at future Stage-2 phases (validator promotion cycle) or Stage 3+ work. Lynceus consumers will see new identifier rows attributed to sids 67–71 in subsequent v1.4.x exports as evidence-arrival promotes them through Phase-5 validator gates.

**No source removals** between v1.4.0 and v1.4.1. The brief mentioned "wave-level" admission counts (Wave I + Wave I.4.1) that are larger than the +5 v1.4.0→v1.4.1 boundary — those wave-cumulative counts cover Stage-1 internal cycles, not the release boundary delta.

---

## §5 — Manufacturer admissions + multi-arm structure

Net delta: **+1 manufacturer** (`Parrot Automotive`, id=222) via mig-0025 (CP31) inline INSERT. **First multi-arm hub-and-spoke arm in the framework.**

| id | canonical_name | primary_category | is_arm | parent_manufacturer_id | Origin |
|---|---|---|---|---|---|
| 222 | Parrot Automotive | `automotive_telematics` | 1 | 25 (Parrot) | mig-0025 inline conversion; CP31 §4.6 hub-and-spoke first application |

**Multi-arm hub-and-spoke (CP31 §4.6) — what Lynceus needs to know.**

- Lynceus consumes `identifiers.manufacturer` as a per-row TEXT string. When the Parrot Automotive arm exports its first identifier (future Stage-2 validator dispatch), the vendor TEXT reads `"Parrot Automotive"` — operationally correct, no Lynceus code change required.
- The `manufacturers.query_default = 'hidden_arm'` filter is downstream-consumer-applied via the export path; Lynceus does not see hidden-arm rows directly. Export-path JOINs maintain a visible-filter (`WHERE m.query_default = 'visible' OR id.manufacturer_id = m.id`) per CP31 §3 4-path downstream audit.
- **Backlog discipline (CP32 §4):** future arm splits ship only when concrete identifier-row evidence attests to a specific arm. The backlog (Cisco/Meraki, Motorola Solutions, Harris RF vs Harris Aerial, Honeywell ACS division) does NOT auto-promote to arm splits on a schedule. Lynceus consumers should expect manufacturer admission/arm cadence to remain evidence-driven, not calendar-driven.

**Wave-level cumulative.** The "35 → 51 = +16 manufacturers" referred-to in some Stage 1 narrative captures Wave I admissions earlier in the Stage 1 cycle (Johnson Matthey id=205 through Rhombus Systems id=221 timestamped 2026-05-17 through 2026-05-19 00:51, ALL BEFORE the v1.4.0 tag at 2026-05-19 20:52). For the v1.4.0 → v1.4.1 release boundary specifically, the net delta is **+1 arm row** as enumerated above.

---

## §6 — Behavioral signatures delta

Net delta v1.4.0 → v1.4.1: **0 net-new rows** (`behavioral_signatures` count unchanged at 201).

CP18 contract holds verbatim. Distribution by `cellular_generation`:

| cellular_generation | count |
|---|---|
| NULL (multi-gen or N/A) | 175 |
| 3G | 10 |
| 4G | 8 |
| 2G | 7 |
| 5G_NSA | 1 |

CP32 §1 extended `behavioral_signatures.device_category` CHECK enum from 12 → 13 (+`automotive_telematics`) for **enum parity with `identifiers.device_category`**, but 0 row promotions land in v1.4.1 — the schema slot opens for future evidence-arrival.

Export shape unchanged: `argus_export_behavioral_signatures.json` ships per the CP18 contract. Current entry count in this regen cycle: 125 entries (matches Stage 1 close baseline).

---

## §7 — §11 #3 export PII guard pattern (CP32 §10)

**New framework-level discipline** codified at CP32 §10 — every emission call site in the Lynceus-export code path includes a post-condition guard `_assert_no_email_pii(path)` that re-reads the written file and raises `Halt` if any email-shape PII survived to disk.

| Module | `_assert_no_email_pii` call sites |
|---|---|
| `db/validation/export_lynceus.py` | 4 |
| `db/validation/export_behavioral_signatures.py` | 3 |
| **Total** | **7** |

The brief's "6 emission call sites" anchor is a documentation conservative count; live grep tally is 7. **Guard is ACTIVE — no regression direction.**

**What this means for Lynceus consumers.**

- Argus exports at v1.4.1 are PII-clean by **hard guarantee at write-time**, not just by row-classification gate. A bug in the upstream `_classify_row` gate or a new code-path that bypasses the gate would be caught by the post-condition guard before the file is published.
- Empirical evidence: `argus_export.csv` regex-scan for `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b` returns **0 matches** (verified per [MAC-217](/MAC/issues/MAC-217) §8.2 PII-strip — commit `50b8232`).
- Lynceus can drop any defensive PII-strip pre-checks it carries; the upstream guard makes them redundant. (Operator discretion — keeping a defense-in-depth check on Lynceus side is also reasonable.)
- Forward-looking sub-rule from CP32 §10: any future §11 hard-rule that constrains export content shape SHOULD ship paired with a `_assert_no_<rule>_<violation>(path)` post-condition guard at every emission call site. Lynceus consumers can anticipate this pattern recurring.

**Companion change — 4 PII-demote self-loops (CP32 §9).** Four Jacobs `*.escg.jacobs.com` rows were demoted in MAC-217 Track B due to cert-subject personal email PII discovered during the §8.2 PII-strip. These rows are now `superseded_by = id` (self-loop) and DO NOT surface as active. See §10 below for the `superseded_by` tri-state semantic.

---

## §8 — §4.4 type_mapping_unmapped bin growth

CP32 §3 added 5 new `DROPPED_REASONS` stubs to `db/validation/export_lynceus.py` + `db/validation/coverage_matrix.py` (mirrored for reconcile-gate parity per CP16 split-structure). The intent and effect:

| Stub | Pre-CP32 disposition | Post-CP32 disposition |
|---|---|---|
| `vendor_controlled_hostname` | Implicit DROP (no entry in `IDENTIFIER_TYPE_TO_PATTERN_TYPE`) | Explicit DROPPED stub in `DROPPED_REASONS` |
| `vendor_cloud_endpoint_url` | Same | Same |
| `vendor_controlled_hostname_deprecated` | Same | Same |
| `fcc_grantee_code` | Same | Same |
| `equipment_class_code` | Same | Same |

**Bin-growth interpretation for Lynceus.** The growth in `_meta.dropped_in_export.type_mapping_unmapped` between v1.4.0 and v1.4.1 reflects the **explicit codification of a pre-existing drop**, not a regression. Pre-CP32, these types dropped silently via the gate-by-absence pattern; post-CP32, they tally explicitly under `type_mapping_unmapped` and are surface-able in the coverage report. **The underlying data is unchanged**; the manifest narrative gained precision.

CP32 §8 codifies the attribution rule: drop attributions in `_meta.dropped_in_export` SHOULD carry a specific rule reference. The MAC-206 wave_g_pre_v1 carve-out (21 rows) drops via the **§4.4 identifier_type → pattern_type mapping gate** (not via CP19 §8.2 crowdsourced-ceiling — confidences 82/87/92 are above all relevant floors); they tally under `type_mapping_unmapped`. If a future cycle admits any of the carve-out's 4 identifier_types (`ble_service`, `ble_characteristic`, `ble_local_name`, `product_family_codename`) into `IDENTIFIER_TYPE_TO_PATTERN_TYPE`, the carve-out rows WILL surface in exports at their current confidence — a deliberate coordination with §11 #17 applicability re-review.

---

## §9 — Export regeneration cadence (CP32 §5)

**Codified at CP32 §5:** `argus_export.csv` + `argus_export.json` + `argus_export_high_confidence.json` + `argus_export_behavioral_signatures.json` + `coverage_report.md` regenerate **per v1.4.x bundle, not per data-touching commit.**

**Current export regen anchor:** post-[MAC-217](/MAC/issues/MAC-217) §8.2 PII-strip — commit `50b8232`. The current published exports are PII-stripped and reflect the schema=25 + CP31 state. After Phase 5 final v1.4.1 tag, a final exports re-fire MAY land if Phase 4 (downstream consumer audit) surfaces any divergence; if not, the `50b8232` regen anchors v1.4.1 ship.

**What this means for Lynceus consumers.**

- Expect a stable export shape that tracks the canonical-DB bundle close, not a moving target across mid-bundle micro-commits.
- Mid-cycle data-touching commits (validator promotions, dedup sweeps) will NOT individually trigger Lynceus-export regen. The bundle close does.
- For continuous-integration Lynceus consumers: track the `_export_manifest.json` regen timestamp + `_meta.argus_version`; do NOT poll for export deltas between bundle closes.
- For tag-driven Lynceus consumers (recommended): pull exports at the v1.4.x tag release artifacts.

`_meta.argus_version` in the current regen cycle is `"25"` (per `50b8232` pre-Phase-1 regen); post-Phase-5 re-fire (if any) will mirror `schema_version=26`. **Lynceus schema-version accept-list during the transition window: `["25", "26"]`**. Strict-equal at `"26"` should land post-Phase-5 cutover; see §F (open questions) below.

---

## §10 — Confidence floor + crowdsourced-ceiling discipline

**No change at v1.4.1 vs v1.4.0.**

| Anchor | Value | Source |
|---|---|---|
| `argus_export_high_confidence.json` confidence threshold | **≥70** | `_meta.confidence_threshold` |
| `argus_export.json` confidence threshold | **≥30** | §7.5 spec |
| `crowdsourced` ceiling (CP19) | **≤79** | §8.2 + CP19 codification |
| `manufacturer_app` floor (per sid 13/14 envelope) | **≥75** | §8.2 |
| `manufacturer_doc` band | **75–90** | §8.2 |
| `inferred` band | **40–65** | §8.2 |

**Important reader note — `superseded_by` tri-state semantic (CP32 §9).** A new framework-level clarification at CP32 §9 (no schema change, narrative-only) makes the tri-state semantic of `identifiers.superseded_by` explicit:

| `superseded_by` value | Meaning | Count at v1.4.1 |
|---|---|---|
| `NULL` | **active** — canonical contract per §4.1 | 34,964 |
| `<other_id>` | **superseded by a successor** (dedup §8.3 merge / deprecated MAC / canonical merge) | 342 |
| `<self_id>` (self-loop) | **withdrawn without successor** (§11 #3 PII demote semantic) | 4 |

**Active-set query convention for Lynceus mirror queries:** `WHERE superseded_by IS NULL`. The 4 self-loop rows do not surface in exports; the 342 successor-superseded rows likewise do not surface (canonical merge semantic — successor rows DO surface in their place).

---

## §11 — Known forward-looking deferrals

Items below are **NOT in v1.4.1 ship scope**; Lynceus consumers should anticipate them as future v1.4.2 / v1.5.0 work-items.

| Item | Origin | Status |
|---|---|---|
| **CP30 reservation — `vendor_asn_prefix` + `vendor_controlled_ip` codification** | CP29 §3 carry-forward | **RESERVED.** CP31 skipped CP30; CP32 skipped CP30; CP30 holds until ASN-prefix observation surfaces (likely Wave I-prime with RDAP url-pattern fix) and/or cert IP-SAN surface yields non-zero in a future cycle. Reservation footnote preserved verbatim in `BIBLE_AMENDMENTS.md` (CP31 header line). |
| **MAC-218 backlog — multi-source class-2 hygiene** | Stage 1 carry-forward | Open. No v1.4.1 admission discipline impact for Lynceus. |
| **MAC-208 backlog — class-2 deferred carve-out follow-up** | Stage 1 §11 #17 fork | Open. CP32 §6 codifies the wave_g_pre_v1 21-row carve-out as session-bounded; MAC-208 fork handles class-2 deferred follow-up at a future dispatch. |
| **§44.3 Honeywell product nomenclature corpus** | [MAC-203](/MAC/issues/MAC-203) Deferral Note 1 | Deferred — no surviving §11 #7 evidence trail at v1.4.1. Honeywell admission stands as canonical row id=211. |
| **Phase 7-bis 177-row fccid.io cohort** | [MAC-194](/MAC/issues/MAC-194) | Currently HALTed pending CP30/CP31 resolution; CP31+CP32 codifications now landed → first v1.4.2 work item. |
| **`ble_service_uuid` Lynceus accept-list MAP** | CP29 §6 + §4.4 alias confirm | Deferred. 30 SoundThinking `ble_service_uuid` rows at `confidence=85, device_category=gunshot_detect, source_type=crowdsourced` are present in the canonical DB but currently drop under `dropped_in_export.ble_service_uuid` because the Lynceus accept-list does not yet include `ble_service_uuid` as a shippable `pattern_type`. Decision driver for v1.4.2; see §F below. |
| **`identifiers.manufacturer_id` FK migration** | CP32 §2 (architectural binding only) | BINDING-only at v1.4.1. Future migration adds `manufacturers.id` FK to denormalized-TEXT `identifiers.manufacturer`; export-path JOINs MUST re-establish CP31 §3 visible-filter at the same time. v1.5.0+ scope. |

---

## §A — Architectural firsts at v1.4.1 (CP32 §2 enumeration)

Carrying these forward for Lynceus engineer's mental model of v1.4.1's framework-level shifts:

1. **First `Na_` sub-slot convention** — data-only addendum migrations sharing a numeric slot with a schema-mutating migration use `Na_…` lexical-after suffix. First application: mig-0026a (renamed from `0026_phase10_vendor_apk_sources_admission.sql` → `0026a_…sql` at commit `398c8b8`).
2. **First dual-table `device_category` CHECK enum sweep** — CP21 cumulative-full-enum spirit applied across two separate CHECK literals (`identifiers.device_category` + `behavioral_signatures.device_category`) in a single migration. Lynceus impact: schema=26 ships with enum parity; downstream consumers can rely on `device_category` as a single conceptual vocabulary regardless of host table.
3. **First codified HALT-fast-path discipline pattern** (CP32 §7) — sandbox-absence pre-flight HALTs are now the default disposition when the dispatch body anticipates the case with an explicit fast-path clause. No Lynceus impact; internal coordination discipline only.
4. **First post-execution dispatch-reasoning correction landed as a CP entry** (CP32 §8) — the MAC-206 carve-out export-drop attribution rule earns a CP entry (rather than a feedback memory) because it composes with §11 #17. Forward-looking implication for Lynceus: if `ble_service` / `ble_characteristic` / `ble_local_name` / `product_family_codename` get admitted to `IDENTIFIER_TYPE_TO_PATTERN_TYPE` in a future cycle, the 21 carve-out rows will surface in exports.
5. **First framework-level export-time generator post-condition guard codification** (CP32 §10) — discussed in §7 above.
6. **First codified tri-state semantic on a SET-NULL FK column** (CP32 §9) — `identifiers.superseded_by` tri-state, discussed in §10 above.
7. **First bundled CP entry folding pre-existing Stage 1 candidate entries** — CP32 §6/§7/§8 each fold a previously-authored Stage-1 "CP32 Candidate #6/#7/#8" entry that anticipated the bundle landing. Internal amendment-log discipline; no Lynceus impact.

---

## §B — Operational delta (concrete numbers)

All counts below are paste-not-cite per §11 #1, verified by the Phase 2 §2.1 spot-checks captured at `~/argus-internal/wave_i_4_1_integration_stage_2/_phase_2_lynceus_handoff/verification_spot_checks.md`.

- **1** SoundThinking row in current high-conf export (`d4:11:d6` OUI, `pattern_type=oui`, description "SoundThinking gunshot_detect", conf=95). 30 additional SoundThinking `ble_service_uuid` rows at `confidence=85, device_category=gunshot_detect` are present in `argus.db` but currently drop under `dropped_in_export.ble_service_uuid` because the Lynceus accept-list does not yet include `ble_service_uuid` as a shippable `pattern_type` (per `db/validation/export_lynceus.py:152` "awaiting §4.4 alias confirm"). See §F open question.
- **0** Flock Safety rows in current high-conf export match the verbose-BLE-local-name regex `FS Ext Battery|Penguin-|Flock-`. Flock Safety has **194 active rows** across many identifier_types in `argus.db`; 3 Flock BLE service rows surface in high-conf as `pattern_type=ble_uuid` with description "Flock Safety alpr" (Lynceus export collapses BLE service descriptions into `<Vendor> <category>` shape).
- **5** ceiling-band vendor-controlled-hostname lifts to conf=95 per [MAC-194](/MAC/issues/MAC-194) Phase 7-bis carry-forward into [MAC-201](/MAC/issues/MAC-201) §7.5-bis structural-anchor methodology — verbatim hostnames: `cellebrite.com`, `enterprise.dji.com`, `firmware.parrot.com`, `forum.developer.parrot.com`, `fh.dji.com`.
- **14** `fcc_grantee_code` rows lifted to conf=85 via §8.3 structural-anchor lift per [MAC-201](/MAC/issues/MAC-201) (the first §7.5-bis lift cycle). All 14 active.
- **4** Jacobs `*.escg.jacobs.com` rows withdrawn from canonical (`superseded_by = id` self-loop) per §11 #3 — cert-subject personal email PII discovered during [MAC-217](/MAC/issues/MAC-217) §8.2 PII-strip.
- **0** email-shape PII matches in `exports/argus_export.csv` — verified via regex `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b`.
- **High-confidence export record count:** 114 entries. **All-export record count:** 514. Reconciliation: `34,964 source → 514 record → 34,450 dropped` (all-export); `34,964 source → 114 record → 34,850 dropped` (high-conf).
- **DJI hostname corpus cleanup** — the [MAC-188](/MAC/issues/MAC-188) cumulative FP demote cycle superseded 261 `vendor_controlled_hostname[*]` rows under third-party-tooling FP classes; manifest narrative reports the cycle as `262 third_party_oss_sdk_root supersessions` (minor ±1 reconciliation delta noted in `_export_manifest.json`).

---

## §C — Recommended order of operations for Lynceus engineer

1. Wait for v1.4.1 final tag on `main` (Phase 5 close of [MAC-219](/MAC/issues/MAC-219)). Current rc1 is `v1.4.1-rc1` at commit `6d33fa8`, tag-object `e370777`.
2. Pull v1.4.1 release artifacts: `argus_export.json`, `argus_export.csv`, `argus_export_high_confidence.json`, `argus_export_behavioral_signatures.json`, `coverage_report.md`, `_export_manifest.json`.
3. Run §A–§B verification queries from this document against your local Argus snapshot to confirm parity (recommend re-running the §2.1 spot-checks from `~/argus-internal/wave_i_4_1_integration_stage_2/_phase_2_lynceus_handoff/verification_spot_checks.md` if you maintain an Argus mirror).
4. Add `automotive_telematics` to your `device_category` enum + `severity_overrides.yaml` (recommend severity=medium per §F.1).
5. If you have a `test_type_mapping` test analog, refactor it to read the enum dynamically at test runtime — the Argus-side pattern lands at commit `ed3f75d` (CP32 §3) and avoids brittle hardcoded enum length assertions across schema bumps.
6. Update Lynceus schema-version accept-list to include `"26"` (or both `"25"` and `"26"` during the transition window per §F.2).
7. Run Lynceus regression tests.

---

## §D — What did NOT change for Lynceus

- **Export contract:** CP7 geographic filter (US-only), CP8 description format (≤80 chars), CP11 dual-artifact (all-conf + high-conf), CP18 `behavioral_signatures` sibling export — all unchanged.
- **Confidence floor:** high-conf threshold remains ≥70 (per `_meta.confidence_threshold`).
- **§11 #13 `device_category='unknown'` filter** at export time — unchanged.
- **`behavioral_signatures` table consumption shape** — unchanged; CP18 contract holds. 125 entries in `argus_export_behavioral_signatures.json` this cycle.
- **`{pattern, pattern_type, description, argus_record_id}` per-record shape** — unchanged.

---

## §E — Cross-reference table

Every external path cited in §1–§D resolves at HEAD `9f76fd7`:

| Reference | Path | Status |
|---|---|---|
| Project bible | `~/argus/PROJECT_BIBLE.md` | ✓ |
| Bible amendments | `~/argus/BIBLE_AMENDMENTS.md` | ✓ |
| Stage 1 final report | `~/argus-internal/wave_i_4_1_integration_stage_1/STAGE_1_FINAL_REPORT.md` | ✓ |
| Phase 2 §2.1 spot-checks | `~/argus-internal/wave_i_4_1_integration_stage_2/_phase_2_lynceus_handoff/verification_spot_checks.md` | ✓ |
| Phase 2 divergence notes | `~/argus-internal/wave_i_4_1_integration_stage_2/_phase_2_lynceus_handoff/divergence_notes.md` | ✓ |
| Phase 1 audit deliverables | `~/argus-internal/wave_i_4_1_integration_stage_2/_phase_1_cp32_codification/` | ✓ |
| Phase 2 Validator attestation | `~/argus-internal/wave_i_4_1_integration_stage_2/_phase_2_validator_attestation/` | ✓ |
| Export module — Lynceus | `~/argus/db/validation/export_lynceus.py` | ✓ |
| Export module — behavioral signatures | `~/argus/db/validation/export_behavioral_signatures.py` | ✓ |
| Coverage matrix | `~/argus/db/validation/coverage_matrix.py` | ✓ |
| Exports — `argus_export.csv` | `~/argus/exports/argus_export.csv` | ✓ |
| Exports — `argus_export.json` | `~/argus/exports/argus_export.json` | ✓ |
| Exports — `argus_export_high_confidence.json` | `~/argus/exports/argus_export_high_confidence.json` | ✓ |
| Exports — `argus_export_behavioral_signatures.json` | `~/argus/exports/argus_export_behavioral_signatures.json` | ✓ |
| Exports — `coverage_report.md` | `~/argus/exports/coverage_report.md` | ✓ |
| Exports — `_export_manifest.json` | `~/argus/exports/_export_manifest.json` | ✓ |
| Migration 0025 (CP31) | `~/argus/db/migrations/0025_cp31_fcc_eas_identifier_type_cluster_plus_hub_and_spoke.sql` | ✓ |
| Migration 0026 (CP32 §1) | `~/argus/db/migrations/0026_cp32_device_category_automotive_telematics.sql` | ✓ |
| Migration 0026a (data-only) | `~/argus/db/migrations/0026a_phase10_vendor_apk_sources_admission.sql` | ✓ |

All MAC issue refs hyperlink as `[MAC-XYZ](/MAC/issues/MAC-XYZ)` per durable-artifact convention.

---

## §F — Open questions for Lynceus engineer (operator-discretion)

1. **Severity for `automotive_telematics`** — recommend `medium`. Surveillance-adjacent (fleet/cellular IoT) — not always primary surveillance gear; operator decides per site context.
2. **Lynceus schema-version backward-compat policy** — accept-list (`["25", "26"]`) during the Stage-2 transition window, or strict-equal (`"26"`) post-cutover? Recommend accept-list during the window; strict-equal post-Phase-5 final tag.
3. **`ble_service_uuid` alias confirm** — should `ble_service_uuid` alias to the existing `ble_uuid` `pattern_type` (i.e., into the Lynceus accept-list as a shippable type), or does Lynceus need a new `ble_service_uuid` `pattern_type`? If aliased, the 30 SoundThinking gunshot_detect BLE UUIDs would lift from `dropped_in_export.ble_service_uuid` into the high-conf export. Decision driver for v1.4.2.
4. **Future Phase 7-bis 177-row fccid.io cohort ship cadence** — currently HALTed pending CP30/CP31 resolution per [MAC-194](/MAC/issues/MAC-194); now that CP31 + CP32 codifications have landed, this is the first v1.4.2 work item.

---

*This document was authored under [MAC-222](/MAC/issues/MAC-222) (Phase 2 Validator dispatch). Every count claim derives from the live `~/argus/db/argus.db` at HEAD `9f76fd7`; every commit cited resolves on the `v1.4.1-integration-stage-1` branch. Reproducibility queries are captured at `~/argus-internal/wave_i_4_1_integration_stage_2/_phase_2_validator_attestation/`.*
