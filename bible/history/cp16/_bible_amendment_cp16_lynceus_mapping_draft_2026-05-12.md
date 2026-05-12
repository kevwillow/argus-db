# Bible §4.4 Amendment Draft — Lynceus mapping for CP14 identifier_type cluster (CP16)

**Status:** DRAFT for CEO ratification (§11 #11). CEO-authored under MAC-75 CP16 dispatch authorization 2026-05-12. **NOT applied** to Bible HEAD; ratification + the BIBLE_AMENDMENTS.md CP16 entry + Phase-5 coordinated commit follows Phase 4 self-review.
**Trigger:** MAC-63 Phase-5 HALT-level finding — post-CP14 `identifiers.identifier_type` enum carries 27 values; `PROJECT_BIBLE.md` §4.4 Lynceus mapping table and `db/validation/export_lynceus.py` `IDENTIFIER_TYPE_TO_PATTERN_TYPE` dict carry only 12. The 15 CP14-cluster types added by migrations 0011/0013/0014 (`ble_manufacturer_id`, the 13-type Drone-RID + proprietary-protocol fold-in, `alpr_model`) have no §4.4 disposition, which means `export_lynceus.py:373` raises `Halt` on any promoted row carrying one of those types.
**Pre-CP16 second-recurrence:** This is the second recurrence of the bible-amendment-downstream-consumer-update pattern. First recurrence: CP12 §8.2 `manufacturer_app` source-type added without 0009 schema-migration sibling (caught at MAC-54 pre-flight). Second-recurrence: CP13 §4.4 mapping table added 3 types without `IDENTIFIER_TYPE_TO_PATTERN_TYPE` sibling (caught at MAC-55 Step-4 export-regen halt; forced MAC-57 dispatch). The discipline rule `feedback_bible_amendment_downstream_consumer_audit.md` was codified after the first recurrence; CP16 is the corrective action for the second recurrence and strengthens the rule with explicit dispatch-checkpoint language so a third recurrence becomes structurally harder.
**Drafted by:** CEO (Argus CP16 dispatch run, 2026-05-12).
**Cross-refs:** CP12 (manufacturer_app schema-sibling miss), CP13 (Wave-G §4.4 mapping additions in lockstep — the discipline that worked), CP14 (the 15 identifier_type additions across migrations 0011/0013/0014), CP15 (just-landed `primary_registry` band; unblocks promotion-cycle-2 once CP16 lands), `feedback_bible_amendment_downstream_consumer_audit.md`, `feedback_cumulative_check_enum_across_sequenced_migrations.md`.

---

## 1. Current §4.4 (verbatim — Bible HEAD `3b37e69` post-CP15 + migration 0016 LICENSE column on `deployment_observations`)

**Phase-4 finding:** between Phase 1 audit (when HEAD was `e663ae5`) and Phase 4 dry-run (this section), migration 0016 LICENSE column landed concurrently on a separate track (`3b37e69` 2026-05-12). 0016 touches `deployment_observations`, not `identifier_type` or `source_type`, so the cumulative-CHECK-enum carryforward audit from Phase 2 still holds clean. HEAD citations throughout this draft updated from `e663ae5` to `3b37e69`.

The current §4.4 Lynceus mapping table has 12 rows:

| Argus `identifier_type` | Lynceus `pattern_type` | Notes |
|---|---|---|
| `oui` | `oui` | direct pass |
| `mac` | `mac` | direct pass |
| `bssid` | `mac` | a BSSID *is* a MAC for Lynceus's purposes |
| `ssid_exact` | `ssid` | direct pass |
| `ssid_pattern` | (DROPPED) | Lynceus has no regex support in v0.2; record in coverage report |
| `ble_uuid` | `ble_uuid` | direct pass |
| `ble_service` | `ble_uuid` | collapsed; BLE service UUIDs *are* UUIDs for Lynceus |
| `mac_range` | (expand or DROP) | expand into individual MACs at export ONLY if range ≤256 entries; otherwise drop |
| `device_fingerprint` | (DROPPED) | analytical-only |
| `ble_local_name` | (DROPPED) | CP13 |
| `ble_characteristic` | (DROPPED) | CP13 |
| `product_family_codename` | (DROPPED) | CP13 |

The §4.4 table is the canonical contract between Argus's richer `identifier_type` enum and Lynceus's fixed `pattern_type ∈ {mac, oui, ssid, ble_uuid}` schema. Per §4.4: "Lynceus cannot be modified to accept Argus's richer enum; Argus does the collapsing."

The 15 CP14-cluster types have no entry. Any `identifiers` row holding one of them and reaching the survivor branch of `_classify_row()` raises `Halt`. MAC-63 promotion-cycle-2 (FAA RID 415 + Apple `0x004C` + XUNTONG `0x09C8` — 417 rows total) cannot run until CP16 ratifies.

---

## 2. The CP16 amendment

### 2.1 Option chosen: **Option A — in-place §4.4 amendment with 15 new rows + 3 new `pattern_type` values**

**Rationale.** The structural shape (a mapping table from Argus enum to Lynceus pattern_type, with explicit DROPPED branches for analytically-only types) is the right shape and is already working for the 12 existing rows. CP16 extends the table; it does not reshape it. The CP13 precedent (3 new DROPPED-class rows added in lockstep with the dict + the early-return branches in `_classify_row`) is the template — CP16 follows the same shape at larger scale (3 MAP + 12 DROPPED).

**Not Option B (per-row MAP-or-DROP decision deferred to validator runtime):** validator routing is downstream of source-band classification; the type-level MAP-vs-DROPPED decision is structurally an Argus-bible question (which identifier_types Lynceus's hardware envelope can plausibly match against), not a per-row validator-runtime call.
**Not Option C (Lynceus-side schema expansion to absorb the new types directly):** §4.4 explicitly forbids this — "Lynceus cannot be modified to accept Argus's richer enum; Argus does the collapsing." Lynceus team owns scanner code; bible owns the type-mapping contract.
**Not Option D (defer CP14-cluster mapping to a future CP after Lynceus integration team weighs in):** the promotion-cycle-2 batch (417 rows) is blocked behind §4.4 resolution; deferring extends the block. The 3 new `pattern_type` values are documented for Lynceus-side sequencing without requiring their concurrent landing.

### 2.2 Per-type dispositions (the substantive judgment, board-ratified at MAC-75 Phase 1)

All 15 dispositions ratified at MAC-75 comment `ee60c712` 2026-05-12. **Tally: 3 MAP, 12 DROPPED.**

#### MAP cases (3) — new `pattern_type` values introduced

| identifier_type | Pattern_type | Lynceus-side scanner work | Capability boundary |
|---|---|---|---|
| `ble_manufacturer_id` | **`ble_manufacturer_id`** (new) | parse `manuf_data[0:2]` (2-byte SIG company ID) from BLE advertising packets | Low cost — most off-the-shelf BLE scanners already parse manufacturer-specific data |
| `drone_id_prefix` | **`drone_id_prefix`** (new) | parse ASTM F3411-22a Remote ID frames across WiFi NAN action / WiFi Beacon vendor IE / BLE Legacy 4.x adv | Moderate cost — multi-PHY scanner code. **Current-hardware capability boundary:** BLE5 LE Coded PHY decode is a baseline-Pi BLE-chipset limitation; WiFi NAN/Beacon is the structural majority of Remote ID coverage on baseline hardware. Documented as current-hardware-not-permanent. |
| `wifi_aware_service_name` | **`wifi_aware_service_name`** (new) | parse WiFi NAN service-discovery frames; match UTF-8 service-name strings | Capability-gated — depends on Lynceus chipset/firmware NAN support. Capability state belongs with consumer (Lynceus), not with Argus: hardware-cannot-observe is the DROPPED criterion; operator-might-not-have-enabled is not. |

#### DROPPED cases (12) — explicit-reason filter, no export

| identifier_type | Reason | Upgrade path (current-hardware-not-permanent) |
|---|---|---|
| `icao_24bit_address` | Out-of-band RF. ADS-B operates at 1090 MHz; Pi BLE/WiFi scanner cannot observe without an additional receiver. | RTL-SDR add-on unlocks ADS-B reception. |
| `rf_channel` | Parametric metadata, not a pattern-match value. Channel is a derived property of an observation, not a wire-observable identifier string. | Architectural — would require a different `pattern_type` shape (parametric-property matching), not a hardware upgrade. |
| `burst_cadence_ms` | Parametric metadata. Temporal property of a burst, not a match value. | Architectural — see `rf_channel`. |
| `bandwidth_mhz` | Parametric metadata. Spectral-occupancy property, not a match value. | Architectural — see `rf_channel`. |
| `device_class_id` | Semantic enum, not match value. Proprietary-protocol device-class labels are categorization-time attributes. | Architectural — see `rf_channel`. |
| `rf_burst_duration` | Parametric metadata (float ms). Temporal property, not a match value. | Architectural — see `rf_channel`. |
| `rf_protocol_constant` | Sub-protocol-level / requires SDR. PHY-layer constants (sync words, frame markers) are not surfaced by the Linux WiFi/BT subsystem to userspace at the baseline Pi capability envelope. | SDR-based scanning (RTL-SDR, HackRF, etc.) unlocks PHY-layer match. |
| `wifi_ie_element_id` | Overly-coarse / sub-protocol-level. The 1-byte IE tag (0–255) alone is structurally too coarse to function as a match value (element_id=221 matches every vendor-specific IE ever broadcast). | A future richer pattern_type (e.g., `wifi_ie_payload_fingerprint`) covering element_id + content fingerprint would be a different type, not this one. |
| `bluetooth_le_pdu_type` | Overly-coarse 4-bit enum. PDU-type values are link-layer markers; every advertising device emits one of a handful. | Architectural — see `wifi_ie_element_id`. |
| `wifi_frame_control_subtype` | Overly-coarse enum. Same shape rationale as `bluetooth_le_pdu_type`. | Architectural — see `wifi_ie_element_id`. |
| `wifi_nan_param_signature` | Derived multi-field aggregate, not a discrete match value. NAN parameter signatures are computed over multiple service-info fields; Lynceus's pattern engine matches single identifier strings. | Future Lynceus capability — multi-field signature matching would be a new `pattern_type`, not this one. |
| `alpr_model` | Vendor-internal taxonomy, not RF-broadcast. Values are product-name strings ("Flock Safety Falcon", "Motorola Vigilant", etc.) sourced from deflock-app reports / vendor docs / visual ID. Structurally identical to the existing DROPPED `product_family_codename`. Migration 0014 §47 explicitly identifies `alpr_model` as a *"Companion type to the existing product_family_codename"*. | Not applicable — vendor-internal taxonomy is structurally unreachable to RF-scanning regardless of hardware. |

### 2.3 §11 #13-style export disposition

**DROPPED rows are fully excluded from `argus_export.json`** (both standard and high-confidence files). They are tallied in the coverage-report `dropped_count_by_*` buckets and live in canonical Argus DB only. This preserves the existing pattern (current DROPPED types — `ssid_pattern`, `device_fingerprint`, `mac_range`, `ble_local_name`, `ble_characteristic`, `product_family_codename` — already follow this pattern via the `_classify_row()` early-return-with-empty-list shape).

Severity-as-export-channel was retired at CP8 (operator-side via Lynceus `severity_overrides.yaml`); CP16 does not re-introduce it. §11 #13 row-level `device_category='unknown'` carveout is independent and composes on top — fires regardless of MAP/DROPPED at the type level.

### 2.4 Amendment text (copy-pasteable into PROJECT_BIBLE.md §4.4)

**Insert 15 new rows into the §4.4 mapping table, in CP14-source order** (matching the migration-comment ordering established by 0011 → 0013 → 0014; MAP/DROPPED interleave naturally per disposition):

```markdown
| `ble_manufacturer_id` | `ble_manufacturer_id` | added Correction Pass 16; **new pattern_type** — Lynceus scanner parses 2-byte SIG company ID from BLE advertising manufacturer-specific data field. Canonical match surface for the post-CP15 BLE manufacturer-ID cluster (Apple `0x004C`, XUNTONG `0x09C8`, etc.) |
| `drone_id_prefix` | `drone_id_prefix` | added Correction Pass 16; **new pattern_type** — Lynceus scanner parses ASTM F3411-22a Remote ID frames across WiFi NAN action / WiFi Beacon vendor IE / BLE Legacy 4.x advertising. **Current-hardware capability boundary:** BLE5 LE Coded PHY decode is a baseline-Pi-BLE-chipset limitation; coverage on baseline hardware is dominated by the WiFi-NAN/Beacon Remote ID variants. Documented as current-hardware-not-permanent; future-chipset-capable operators gain coverage automatically without §4.4 amendment. |
| `icao_24bit_address` | (DROPPED) | added Correction Pass 16; **out-of-band RF.** ADS-B operates at 1090 MHz; Lynceus baseline Pi BLE/WiFi scanner cannot observe without an additional receiver. **Current-hardware DROPPED** — RTL-SDR upgrade path unlocks observability for future operators. |
| `rf_channel` | (DROPPED) | added Correction Pass 16; **parametric metadata.** RF channel is a derived property of an observation, structurally not a wire-observable identifier string. Lynceus `pattern_type` shape requires discrete match values. |
| `burst_cadence_ms` | (DROPPED) | added Correction Pass 16; parametric metadata (temporal property of an emitter, not a match value). |
| `bandwidth_mhz` | (DROPPED) | added Correction Pass 16; parametric metadata (spectral-occupancy property of a signal, not a match value). |
| `device_class_id` | (DROPPED) | added Correction Pass 16; semantic enum (proprietary-protocol device-class label, categorization-time attribute, not a wire-observable identifier string). |
| `rf_burst_duration` | (DROPPED) | added Correction Pass 16; parametric metadata (temporal property of a burst, not a match value). |
| `rf_protocol_constant` | (DROPPED) | added Correction Pass 16; **sub-protocol-level / requires SDR.** PHY-layer constants (sync words, frame markers) are not surfaced by the Linux WiFi/BT subsystem to userspace at the baseline Pi capability envelope. SDR-based scanning (RTL-SDR, HackRF) unlocks PHY-layer match for future hardware-upgraded operators. |
| `wifi_aware_service_name` | `wifi_aware_service_name` | added Correction Pass 16; **new pattern_type** — Lynceus scanner parses WiFi NAN service-discovery frames, matches UTF-8 service-name strings. Capability-gated by Lynceus-side NAN support; Argus exports unconditionally per the consumer-carries-capability-state posture (hardware-cannot-observe is the DROPPED criterion at §4.4, operator-might-not-have-enabled is not). |
| `wifi_ie_element_id` | (DROPPED) | added Correction Pass 16; **overly-coarse / sub-protocol-level.** The 1-byte IE tag (0–255) alone is structurally too coarse to function as a Lynceus pattern match value. A future richer `pattern_type` (e.g., `wifi_ie_payload_fingerprint`) covering element_id + content fingerprint would be a different type. |
| `bluetooth_le_pdu_type` | (DROPPED) | added Correction Pass 16; overly-coarse 4-bit link-layer enum (ADV_IND / ADV_NONCONN_IND / SCAN_REQ etc.); structurally not a useful match value on its own. |
| `wifi_frame_control_subtype` | (DROPPED) | added Correction Pass 16; overly-coarse 802.11 frame-control subtype enum; same shape rationale as `bluetooth_le_pdu_type`. |
| `wifi_nan_param_signature` | (DROPPED) | added Correction Pass 16; derived multi-field aggregate over NAN service-info fields, not a discrete match value. Lynceus's pattern engine matches single identifier strings, not multi-field signature aggregates. Future Lynceus signature-matching capability would be a new `pattern_type`. |
| `alpr_model` | (DROPPED) | added Correction Pass 16; **vendor-internal taxonomy, not RF-broadcast.** Values are product-name strings ("Flock Safety Falcon", "Motorola Vigilant", "Genetec AutoVu", etc.) sourced from deflock-app reports / vendor docs / visual identification. Companion type to the already-DROPPED `product_family_codename` (CP13 §4.4); both classes are analytical-only. Concrete ALPR-camera identifier rows flow via `oui` / `mac` / `bssid` / `ssid_exact` types where present; `alpr_model` is the analytical taxonomy column. |
```

**Ordering note:** rows above appear in CP14 migration-source order (0011 first, then the 0013 13-type cluster in its own internal order, then 0014's `alpr_model`). MAP and DROPPED rows interleave naturally per disposition — no separate MAP-vs-DROPPED partition, matching the existing §4.4 table's interleaved shape.

### 2.5 New `pattern_type` values — Lynceus integration team call-out

CP16 introduces **3 new `pattern_type` values** that don't exist in the current Lynceus pattern table.

**Architectural separation — Argus and Lynceus are parallel tracks, not a serial dependency.** CP16 ratification on the Argus side unblocks promotion-cycle-2 (415 FAA RID `drone_id_prefix` rows + 2 SIG `ble_manufacturer_id` rows) and the post-promotion export-regen, immediately. Those rows ride the export at apply time regardless of Lynceus-side scanner-code state. If a running Lynceus instance does not yet support a new `pattern_type` at scan time (the scanner code hasn't been updated, the capability is declared OFF, etc.), the entries are silently unmatched at runtime — consumer-side unknown-pattern handling per Lynceus's own scanner contract. The export pipeline does not error; the entries are not dropped on the Argus side; canonical Argus DB carries the full promotion. CP16 is NOT blocked on Lynceus's scanner-code implementation, and the bible amendment text MUST NOT read as if it were.

Implementation-cost notes below are surfaced for Lynceus integration team **sequencing** so they can plan capability-on milestones independently — not as Argus-side preconditions for the export landing the new entries.

1. **`ble_manufacturer_id`** — 4-hex-char string match (e.g., `"0x09C8"` for XUNTONG, `"0x004C"` for Apple). Scanner parses BLE advertising manufacturer-specific data field (`manuf_data[0:2]`). Implementation cost: **low** — most off-the-shelf BLE scanner libraries already surface this field.
2. **`drone_id_prefix`** — 9-char ANSI/CTA-2063-A Serial Number prefix string match (e.g., `"1581F08Q3"`). Scanner parses Remote ID frames across multiple PHYs: WiFi NAN action frames, WiFi Beacon vendor IEs, BLE Legacy 4.x advertising. Implementation cost: **moderate** — multi-PHY parser code. BLE5 LE Coded PHY decode at baseline Pi BLE chipset is a known capability boundary (firmware-level limitation); coverage on baseline hardware is dominated by the WiFi-NAN/Beacon variants. Future better-BLE-chipset operators gain LE Coded PHY coverage automatically without §4.4 amendment.
3. **`wifi_aware_service_name`** — UTF-8 service-name string match. Scanner parses WiFi NAN service-discovery frames. Implementation cost: **moderate** — capability-gated by Lynceus-side WiFi NAN support; on chipsets/firmware/userspace tooling lacking NAN, scanner declares the capability OFF and Argus rows of this type are silently unmatched at scan-time. Per the consumer-carries-capability-state posture, Argus exports unconditionally.

Lynceus integration team can sequence the three pattern_types independently: `ble_manufacturer_id` is the lowest-cost and would unblock the 2-row Apple/XUNTONG cluster at runtime once supported; `drone_id_prefix` would unlock runtime matching of the 415-row FAA RID cluster; `wifi_aware_service_name` is forward-looking (no current Argus rows of this type as of post-CP15 state). All three rows-on-export land at Argus's apply-time regardless of Lynceus sequencing; runtime *match coverage* is gated by Lynceus's track, separately.

---

## 3. `db/validation/export_lynceus.py` coordinated patch (sibling commit)

Per `feedback_bible_amendment_downstream_consumer_audit.md` (and the CP13 lockstep precedent), §4.4 amendment lands in coordinated commit with the code patch updating `IDENTIFIER_TYPE_TO_PATTERN_TYPE`. The code patch is staged separately at `db/validation/_drafts/export_lynceus_cp16_patch.py.draft` (new staging path under `db/validation/_drafts/`, mirroring the `db/migrations/_drafts/` discipline).

The patch shape (per Phase 2 §4 board-ratified design call + Phase 4 self-review revisions):

1. **3 new MAP entries appended to `IDENTIFIER_TYPE_TO_PATTERN_TYPE`** at the same indentation as existing rows. Tagged `# CP16 — new pattern_type` for grep-ability.
2. **New `DROPPED_REASONS` dict** with the 12 new CP14-cluster DROPPED types as keys, mapping to bin-label strings (one per type). This is the lean-refactor structure that lets Phase 3+ DROPPED additions land as data, not code.
3. **One new branch in `_classify_row()`** checking `if row.identifier_type in DROPPED_REASONS: return (DROPPED_REASONS[row.identifier_type], [])` — placed BEFORE the dict lookup at line 370, AFTER the existing 6 explicit DROPPED branches (which stay untouched per "preserve stable working code" discipline).
4. **Comment noting the 6 legacy branches** could fold into the same dict in a future hygiene-pass commit; out of CP16 scope. The legacy branches stay verbatim.
5. **`bins` dict initializer expansion** (Phase-4 revision A): add 12 new zero-init entries to the `bins: dict[str, int]` initializer at lines 584-597 so the `bins[drop_bin] += 1` aggregation loop succeeds when the new branch fires. The Phase 3 architectural claim that this needed no code change was **wrong** — the live initializer is exhaustively enumerated, not dict-default-keyed. Phase 4 dry-run confirmed the gap.
6. **`fmt_bin_table` bin_rows expansion** (Phase-4 revision A): add 12 new rows to the coverage-report markdown rendering tuple at lines 681-693 (each row tagged `(§4.4 CP16)` matching existing `(§4.4 CP13)` tag style). Same exhaustive-enumeration pattern as `bins`; same need for explicit extension.
7. **`mac_range` stale-comment refresh** (Phase-4 revision C; per Phase 2 board direction `5b9212ce`): replace the stale "HB36" anchor in the mac_range branch (live file lines 354-358) with a structural anchor. One-line scope; in-pass refresh.
8. **Reconciliation hardening** — the defensive `Halt` at line 373 stays as-is (catches any future enum addition that lands without §4.4 update); the new branch lets intentionally-DROPPED types pass through cleanly without tripping the defensive halt.

See `db/validation/_drafts/export_lynceus_cp16_patch.py.draft` for the verbatim code patch.

### 3.1 Test-fixture sibling update (Phase-4 revision B)

`tests/test_export_lynceus.py` is a fixture-side consumer of the §4.4 contract: `test_type_mapping_covers_every_identifier_type` (lines 99-115) hard-codes a 12-key expected set and asserts set-equality on `IDENTIFIER_TYPE_TO_PATTERN_TYPE.keys()`. CP16's dict expansion breaks this assertion; the test must be updated to assert the UNION of `IDENTIFIER_TYPE_TO_PATTERN_TYPE.keys()` and `DROPPED_REASONS.keys()` covers the full post-CP14 enum (27 values), and to add a structural invariant that the two surfaces have no key overlap.

Phase-4 audit-trail note: this test existed at CP13 but was not updated at CP14. Running `pytest tests/test_export_lynceus.py::test_type_mapping_covers_every_identifier_type` during CP14 apply would have failed and caught the §4.4 mapping gap before MAC-63 Phase 5 surfaced it — the strengthened memory rule's S.1 dispatch-checkpoint language now mandates this fixture-side audit during dispatch authoring. Patch shape staged in §4.3 of the code-patch draft.

---

## 4. Edge cases NOT covered (validator-side discipline)

1. **A row of CP14-cluster type already in `identifiers` table.** Audit of post-CP15 state confirms no CP14-cluster type rows have been promoted to `identifiers` (the prior 415+2 promotion-cycle-2 candidates are still in `raw_observations` HOLD per MAC-63 Phase-5 HALT). CP16 applies cleanly with zero existing rows to retro-classify.
2. **Lynceus scanner declares capability OFF for `wifi_aware_service_name`.** Argus exports unconditionally; Lynceus skips at scan-time. The export is forward-compatible with capability-on Lynceus instances; legacy capability-off instances see the entries as unmatched, no error.
3. **A future CP adds an identifier_type without §4.4 update.** The defensive `Halt` at line 373 catches it. The strengthened memory rule (Phase 3.3) adds explicit dispatch-checkpoint language so CP authors include §4.4 + dict audit as a Phase-N checkpoint by default, preventing the recurrence at dispatch-design time rather than catching it at export-regen time.
4. **An existing MAP entry's `pattern_type` is invalidated by a Lynceus-side schema change.** Out of scope. Lynceus team owns the scanner-config schema; if a `pattern_type` is retired Lynceus-side, that triggers a coordinated CP, not a unilateral §4.4 edit.
5. **A new BLE5 LE Coded PHY capability becomes baseline.** No §4.4 amendment needed — `drone_id_prefix` already MAPs; coverage improves automatically. The current-hardware-not-permanent framing was chosen specifically to avoid §4.4 ripple from hardware-envelope shifts.

---

## 5. BIBLE_AMENDMENTS.md CP16 entry stub

```
## Correction Pass 16 — §4.4 Lynceus mapping for CP14 identifier_type cluster

**Date:** 2026-05-12
**Source:** [MAC-75](/MAC/issues/MAC-75) CP16 dispatch. Trigger: MAC-63 Phase 5 HALT
(CP14→§4.4 downstream-consumer gap; second recurrence of the bible-amendment-
downstream-consumer-update pattern after the CP12→CP13 schema gap caught at
MAC-54 + CP13→MAC-57 export gap caught at MAC-55).
**Authority:** Fresh CEO §11 #11 delegation 2026-05-12 (MAC-75 wake comment `017df17b`).
**Bible commit:** PROJECT_BIBLE.md §4.4 (15 new mapping rows + 3 new pattern_type
introductions) + BIBLE_AMENDMENTS.md CP16 entry (this entry) + draft moved from
raw/wave_a/_bible_amendment_cp16_lynceus_mapping_draft_2026-05-12.md to
bible/history/cp16/. Single coordinated commit titled
"CP16: §4.4 Lynceus mapping for CP14 identifier_type cluster".
**Code-sibling commit (paired, second commit per CP14/CP15 precedent):**
db/validation/export_lynceus.py IDENTIFIER_TYPE_TO_PATTERN_TYPE additions
(3 MAP) + new DROPPED_REASONS dict (12 entries) + new _classify_row branch +
feedback_bible_amendment_downstream_consumer_audit.md strengthening +
draft moved from db/validation/_drafts/ to live path. Commit titled
"chore(export): CP16 Lynceus mapping coordinated patch + memory-rule strengthening".
**Binds:** Export Worker (§7.5 — new 3 pattern_type values + 12 DROPPED-reason buckets
in coverage report), Validator (§11 #7 promotion-cycle-2 sweep of 417 HOLD candidates
post-CP16 ratification), Lynceus integration team (sequencing the 3 new pattern_types
into the v0.4 scanner-config schema).

### Why this Correction Pass exists

CP14 added 15 new `identifier_type` enum values via migrations 0011/0013/0014 but
did NOT update §4.4 Lynceus mapping or IDENTIFIER_TYPE_TO_PATTERN_TYPE in lockstep.
The feedback memo codifying parallel-sibling-commit discipline existed (authored
after CP12→CP13 schema gap and refined after CP13→MAC-57 export gap), but the
CP14 batch missed it — the discipline rule didn't have explicit dispatch-checkpoint
language. MAC-63 Phase-5 HALT surfaced the gap; CP16 closes it and strengthens
the rule.

### Items

1. **§4.4 Lynceus mapping table** — 15 new rows (3 MAP + 12 DROPPED). MAP cases
   introduce 3 new pattern_type values for Lynceus team (ble_manufacturer_id,
   drone_id_prefix, wifi_aware_service_name). DROPPED cases carry explicit
   hardware/architectural rationale + upgrade-path-X-unlocks framing where
   applicable (current-hardware-not-permanent posture per board direction).
2. **export_lynceus.py code patch (sibling commit)** — 3 new dict entries
   for MAP types; new DROPPED_REASONS dict for the 12 DROPPED types; one new
   _classify_row branch keyed on DROPPED_REASONS. Existing 6 legacy DROPPED
   branches preserved (stable, working; future-hygiene-pass-only refactor
   target).
3. **Memory rule strengthening** (feedback_bible_amendment_downstream_consumer_audit.md):
   explicit dispatch-checkpoint language ("CP/SAR dispatches that add enum
   values MUST include §4.4 + IDENTIFIER_TYPE_TO_PATTERN_TYPE audit as an
   explicit Phase-N self-review checkpoint"), cumulative-audit-runs-against-
   FULL-enum sub-rule (catches latent earlier-CP gaps, not just the new
   additions), second-recurrence audit-trail entry referencing CP16.

### Discipline-strengthening

The codified memory rule (post-MAC-55) caught CP13→MAC-57 retroactively
but did not prevent CP14's recurrence at dispatch-design time. CP16's
strengthening adds:
- Explicit dispatch-template checkpoint language so future dispatches
  enumerate §4.4 + IDENTIFIER_TYPE_TO_PATTERN_TYPE audit as a phase by
  default.
- Cumulative-full-enum sub-rule: the audit checks the ENTIRE enum, not
  just the CP's new additions. This catches any latent earlier-CP slips
  the rule missed retroactively.
- Second-recurrence audit-trail entry: CP12→CP13 (first), CP14→CP16
  (second). Each entry documents the dispatch design at the time and
  the catch path. A third-recurrence would be a structural pattern
  rather than a one-off; if the strengthened rule fires properly,
  recurrence count stays at 2.

### Resolved §12 questions

None directly. CP16 closes the open structural finding logged by MAC-63
G-18 (CP14→§4.4 mapping gap) but the finding was operational, not §12.
Future Lynceus integration sequencing for the 3 new pattern_types is not
a §12 open question — it's an outbound coordination task to a known team.

### New open §12 questions

None expected. Phase 1 audit's 3 pause-for-human flags were ratified
without surfacing new §12-class structural questions; the audit confirms
no latent §4.4 surfaces are open post-CP16.

### §11 hard-rule discipline

- §11 #1 (no fabrication) — every DROPPED row has explicit hardware /
  architectural / sub-protocol rationale; no "out of scope" placeholders.
- §11 #11 (coordinated commit) — bible + amendment log + draft move +
  memory memo update + code patch land as paired commits per CP14/CP15
  precedent (bible-text commit + code-sibling commit).
- §11 #12 / §11 #13 — unchanged. CP16's type-level DROPPED-with-reason
  composes with row-level §11 #13 unknown-category carveout; both fire
  independently at export time. §11 #12 operator-stack self-exclude
  applies orthogonally on OUI / VID:PID rows; CP16 doesn't touch it.

### §11 #11 self-binding satisfied

This CP16 entry is the §11 #11 amendment-log pairing for the §4.4
amendment in the coordinated commit. Bible HEAD bumps from `3b37e69`
(post-CP15 + migration 0016 LICENSE column) to the CP16 commit.
Schema-version unchanged (no schema migration; CP16 is a mapping-
table + code-patch CP, not a schema CP).
```

---

## 6. Cross-references

- **MAC-75 dispatch** `017df17b` 2026-05-12 (CP16 fresh §11 #11 delegation)
- **MAC-75 Phase 1 audit** `29d87c46` 2026-05-12 (the 15 dispositions, ratified `ee60c712`)
- **MAC-75 Phase 2 sweep** `0cb3e387` 2026-05-12 (cumulative full-enum audit; clean beyond CP14, ratified `5b9212ce`)
- **MAC-63 Phase 5 HALT finding** at `raw/wave_a/_promotion_cycle_2_candidates_2026-05-11.md` §0 (the original surfacing)
- **CP12 manufacturer_app schema-sibling miss** (first recurrence — caught at MAC-54)
- **CP13 §4.4 + dict lockstep** in BIBLE_AMENDMENTS.md (the discipline pattern CP14 missed and CP16 restores)
- **CP14 four-amendment + 5-migration commit** `06cc501`/`72c0323`/`d13e12a` (the 15 identifier_type additions that needed §4.4 mapping)
- **CP15 primary_registry band** `1e83517`/`e663ae5` (just-landed; unblocks promotion-cycle-2 once CP16 closes the §4.4 gap)
- **Migration 0016 LICENSE column** `3b37e69` 2026-05-12 (concurrent unrelated track; doesn't touch identifier_type or source_type; bumps HEAD between Phase 1 audit and Phase 4 dry-run)
- **`feedback_bible_amendment_downstream_consumer_audit.md`** (rule strengthened by CP16)
- **`feedback_cumulative_check_enum_across_sequenced_migrations.md`** (audit-confirmed-clean by Phase 2)
- **`db/migrations/_drafts/`** (staging-path precedent for `db/validation/_drafts/`)

---

## 7. §11 #11 statement

This is a CEO-authored draft under MAC-75 §11 #11 fresh delegation 2026-05-12. **NOT applied** to Bible HEAD; Phase 4 self-review pass follows; Phase 5 coordinated commit applies bible + code + memo updates together. Per dispatch §2 verify-and-halt discipline: this Phase 3 draft is the staging deliverable, awaiting board self-review-pass-readiness before Phase 4 begins.
