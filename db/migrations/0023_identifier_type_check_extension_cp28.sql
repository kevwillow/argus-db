-- ============================================================================
-- Migration: 0023_identifier_type_check_extension_cp28
-- Purpose:   Extend `identifiers.identifier_type` CHECK enum with 3 net-new
--            values per CP28 (c) — the Wave H desktop-axis vendor-registered
--            non-BLE identifier cluster surfaced by the wave_h pre-v1
--            extraction (DJI Assistant 2 Mavic + FPV + Hikvision iVMS-4200).
--            Final CHECK cardinality: 48 prior + 3 net-new = 51 values
--            cumulatively.
-- Surfaced:  ~/argus-internal/desktop_test/extraction_outputs/wave_h_pre_v1/
--              HANDOFF_TO_VALIDATOR.md §11(c) (CP28 candidate flag (c) for
--              the three vendor-registered non-BLE classes surfaced
--              empirically across Mavic + FPV + iVMS-4200).
--            ~/argus-internal/new data 5.18/wave_h_desktop_setup_app_runguide.md
--              (parent runguide for the Wave H wrapper extraction pass).
-- Authority: CEO disposition on MAC-177 (`comment 0d15de7b`) §7 "approve full
--            path"; ratified into MAC-181 cycle scope as the schema-sibling
--            of the CP28 BIBLE_AMENDMENTS.md entry (composed alongside
--            this migration, anchored on this migration's commit hash per
--            `feedback_bible_amendment_child_issue_id_ordering`).
-- Bible:     §11 #1   no fabrication — every new CHECK enum value cites
--                     empirical canon: HANDOFF §11(c) names the four
--                     vendor-attested non-BLE identifiers + the three
--                     identifier classes those four map to.
--            §11 #7   no main-table promotion without provenance — schema
--                     only here; the four-row promotion happens in §8.8 of
--                     MAC-181 after this migration applies.
--            §11 #8   no confidence drift — confidence column unchanged;
--                     CP28(c) sub-band ladder is documented in BIBLE_AMENDMENTS
--                     (75-90 / 75-90 / 80-95 per CEO disposition).
--            §11 #11  amendment-log discipline — sibling to BIBLE_AMENDMENTS
--                     CP28 entry (composed in this same MAC-181 cycle, per
--                     `feedback_enum_amendment_needs_schema_migration_sibling`).
--            §11 #15  no decompiled vendor source in git index — N/A; schema
--                     only. Wave H wrapper code lives at canonical path
--                     `~/argus/scripts/extraction/wave_h_wrapper.py` (ported
--                     elsewhere in the MAC-181 cycle); extracted binary
--                     contents are SSD-only per HANDOFF §12.
--            §11 #16  facts-only promotion from public-but-unlicensed
--                     sources — applies at row-level promotion (§8.8), not
--                     at schema-extension time.
-- Pattern:   SQLite table-rebuild per 0009 / 0011 / 0013 / 0014 / 0018 / 0019
--            precedent. PRAGMA foreign_keys=OFF outside transaction; CREATE
--            _new with extended CHECK; INSERT SELECT * (column-preserving
--            copy); DROP old; RENAME _new → old; recreate indexes;
--            foreign_key_check; schema_version bump; COMMIT;
--            foreign_keys=ON.
-- Risk:      Low. Pure additive enum extension. Column shape unchanged from
--            0019 (16 columns). All 22,549 active rows preserved via
--            INSERT SELECT *.
-- ============================================================================
--
-- Migration-slot allocation chain of record:
--   0001-0019  see 0019 header for the full chain through round-2 vocab
--   0020 = source_type enum extension (CP23 cycle-3 judicial/disclosure)
--   0021 = procurement_vendor_canonical_normalized
--   0022 = fcc_citation_deferred_queue
--   0023 = identifier_type CHECK extension CP28 — this migration
--          (3 net-new values; 51-value cumulative CHECK)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Cumulative CHECK enum (48 prior + 3 net-new = 51 values total)
-- ─────────────────────────────────────────────────────────────────────────────
-- The 48 prior values are paste-verified verbatim against the live `identifiers`
-- table CHECK clause from migrations 0001 (9) + 0009 (3) + 0011 (1) + 0013 (13)
-- + 0014 (1) + 0018 (14) + 0019 (7). Per
-- `feedback_cumulative_check_enum_across_sequenced_migrations`, the rebuild-
-- pattern migration MUST carry forward ALL prior CHECK enum values, not just
-- its own delta.
--
-- The 3 net-new types (CP28 (c) per HANDOFF §11(c); CEO ratification on
-- MAC-177 disposition `0d15de7b`):
--   1. `windows_installer_productcode_vendor_registered`
--                                       — MSI/InstallShield ProductCode GUIDs
--                                       registered by vendor desktop installers
--                                       (Hikvision iVMS-4200 main package +
--                                       Multilingual Wizard sub-package surface
--                                       `9A25302D-...` + `CE2F96D0-...` in
--                                       `SOFTWARE\Microsoft\Windows\CurrentVersion
--                                       \Uninstall\{...}` registry contexts).
--                                       Empirical Wave H seed: 2 unique values
--                                       in iVMS-4200 v3.13.0.5_Multilingual.
--                                       §4.4 posture: DROPPED (install-time
--                                       registry context; low passive-scan
--                                       utility for Lynceus's BLE/WiFi-axis
--                                       relevance window). §8.2 sub-band:
--                                       75-90 per CP28(c) ladder.
--   2. `windows_com_clsid_vendor_registered`
--                                       — Windows COM Class IDs registered by
--                                       vendor desktop installers (DJI
--                                       Assistant 2 DJIBrowser surface
--                                       `054AAE20-...` in
--                                       `Software\Classes\CLSID\{...}\LocalServer32`
--                                       registry context). Empirical Wave H
--                                       seed: 1 unique value in DJI Assistant 2
--                                       Mavic 2.0.14.
--                                       §4.4 posture: DROPPED (install-time
--                                       registry context; low passive-scan
--                                       utility). §8.2 sub-band: 75-90 per
--                                       CP28(c) ladder.
--   3. `vendor_document_uuid_cloud_reference`
--                                       — Vendor-controlled cloud-hosted
--                                       document UUID embedded in vendor-
--                                       owned cloud endpoint URL (DJI surface
--                                       `f4d4dbf5-...` embedded in
--                                       `https://duss.djicorp.com/functional-
--                                       document/f4d4dbf5-...`). Empirical
--                                       Wave H seed: 1 unique value with
--                                       cross-product attestation (Mavic + FPV
--                                       Assistant 2 binaries; CP24 within-
--                                       vendor-cross-product).
--                                       §4.4 posture: MAP (vendor-controlled
--                                       hostname half — `duss.djicorp.com` —
--                                       lifts into Lynceus relevance window
--                                       as a passively-scannable vendor cloud
--                                       endpoint signature). §8.2 sub-band:
--                                       80-95 per CP28(c) ladder.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- CP28 (a) / (b) deferral footnote — schema-only here; no enum impact
-- ─────────────────────────────────────────────────────────────────────────────
-- CP28 (a) `vendor_application_static_analysis` source_type enum:
--   DEFERRED per CEO disposition. Wave G mobile + Wave H desktop both land
--   under `vendor_documentation` per CP15 source-type ceiling. The band-
--   distinction is encoded via the §8.2 sub-band ladder + the
--   `notes.session_admission` field on per-wave sources rows. No new
--   `source_type` CHECK enum value in this migration.
--
-- CP28 (b) `sanctioned_vendor_public_distribution_facts_only` license-posture
--   sentinel: DEFERRED per CEO disposition. Anchor weakened post-CP26 §8
--   re-class (the 2 surviving Hikvision UUIDs re-class as MSI ProductCode FPs,
--   not BLE — see HANDOFF §11(b)). Re-fire as CP-of-its-own at Cohort F
--   completion (post-Dahua + Uniview acquisition unblock).
--
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 hard-rule discipline (cite verbatim per 0009 / 0011 / 0013 / 0014 / 0018
-- / 0019)
-- ─────────────────────────────────────────────────────────────────────────────
--   §11 #1   no fabrication — every new CHECK enum value cites empirical
--              canon: HANDOFF §11(c) names the four vendor-attested non-BLE
--              identifiers + the three classes those four map to.
--   §11 #7   no main-table promotion without provenance — schema-only here;
--              promotion of the 4-row Wave H batch happens in §8.8 of MAC-181
--              after this migration applies.
--   §11 #8   no confidence drift — confidence column unchanged; CP28(c)
--              sub-band ladder is documented in BIBLE_AMENDMENTS.
--   §11 #11  amendment-log discipline — sibling to BIBLE_AMENDMENTS CP28
--              entry composed alongside this migration in the MAC-181 cycle.
--   §11 #15  no decompiled vendor source in git index — N/A; schema-only.
--   §11 #16  facts-only promotion from public-but-unlicensed sources —
--              binds row-level provenance at routing-execution time, not at
--              schema-extension time. Wave H sources row carries
--              `license_posture='per_vendor'` +
--              `upstream_license_posture='no_license_declared_facts_only'`
--              defaults per CP21.
-- ─────────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
-- Column list reflects post-0019 state (16 columns; paired_identifier_id +
-- pair_kind from 0012 preserved verbatim). CHECK enum carries forward all 48
-- prior values + adds 3 net-new (51 cumulative values).
CREATE TABLE identifiers_new (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier        TEXT NOT NULL,
    identifier_type   TEXT NOT NULL CHECK (identifier_type IN (
                          -- Pre-CP13 (0001 initial) — 9 values
                          'oui', 'mac', 'mac_range', 'bssid',
                          'ssid_exact', 'ssid_pattern',
                          'ble_uuid', 'ble_service',
                          'device_fingerprint',
                          -- CP13 (migration 0009) — Wave G structural fidelity (3)
                          'ble_local_name', 'ble_characteristic',
                          'product_family_codename',
                          -- CP14 (migration 0011) — G-3 BLE SIG manufacturer IDs (1)
                          'ble_manufacturer_id',
                          -- CP14 (migration 0013) — Drone-RID + proprietary
                          -- protocol cluster (13)
                          'drone_id_prefix',
                          'icao_24bit_address',
                          'rf_channel',
                          'burst_cadence_ms',
                          'bandwidth_mhz',
                          'device_class_id',
                          'rf_burst_duration',
                          'rf_protocol_constant',
                          'wifi_aware_service_name',
                          'wifi_ie_element_id',
                          'bluetooth_le_pdu_type',
                          'wifi_frame_control_subtype',
                          'wifi_nan_param_signature',
                          -- CP14 (migration 0014) — surveillance metadata (1)
                          'alpr_model',
                          -- CP20 (migration 0018) — SAR-13 §S.3 vendor-anchored
                          -- / device-naming cluster (14)
                          'ble_protocol_byte_table',
                          'ble_service_uuid',
                          'ble_company_id',
                          'frequency_band',
                          'ble_protocol_byte',
                          'operator_profile',
                          'x509_cert_sha256_prefix',
                          'ble_adv_interval',
                          'ble_payload_offset',
                          'firmware_sha256_hash',
                          'network_endpoint',
                          'firmware_image_variant',
                          'qualcomm_chip_format_id',
                          'firmware_branded_string',
                          -- MAC-117 (migration 0019) — round-2 vocab
                          -- extension (7) per §1 routing slate (A)
                          'asdstan_message_type',
                          'asdstan_enum_value',
                          'dji_protocol_struct_format',
                          'gpt_partition_uuid',
                          'chipset_codename',
                          'firmware_build_string',
                          'firmware_build_uuid',
                          -- CP28 (migration 0023 — this migration) — Wave H
                          -- desktop-axis vendor-registered non-BLE cluster (3)
                          'windows_installer_productcode_vendor_registered',
                          'windows_com_clsid_vendor_registered',
                          'vendor_document_uuid_cloud_reference'
                      )),
    device_category   TEXT NOT NULL CHECK (device_category IN (
                          'alpr', 'imsi_catcher', 'body_cam', 'police_radio',
                          'drone', 'gunshot_detect', 'hacking_tool',
                          'covert_cam', 'gps_tracker', 'face_recog',
                          'drone_detect', 'unknown'
                      )),
    manufacturer      TEXT,
    model             TEXT,
    confidence        INTEGER CHECK (confidence BETWEEN 0 AND 100),
    source_url        TEXT NOT NULL,
    source_type       TEXT NOT NULL CHECK (source_type IN (
                          'official', 'regulatory', 'procurement',
                          'academic', 'foia', 'crowdsourced',
                          'inferred', 'manufacturer_doc',
                          'manufacturer_app',
                          -- CP15 (migration 0015) — primary_registry
                          'primary_registry'
                      )),
    source_excerpt    TEXT CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200),
    geographic_scope  TEXT,
    first_seen        DATETIME,
    last_verified     DATETIME,
    notes             TEXT,
    superseded_by     INTEGER REFERENCES identifiers(id) ON DELETE SET NULL,
    -- CP14 (migration 0012) — paired-identifier discipline
    paired_identifier_id INTEGER REFERENCES identifiers(id) ON DELETE SET NULL,
    pair_kind            TEXT CHECK (
                             pair_kind IS NULL
                             OR pair_kind IN (
                                 'la_bit_flip',
                                 'frdid_sibling',
                                 'vendor_as_container',
                                 'firmware_generation'
                             )
                         )
);

-- Column-preserving copy. All 16 columns enumerated implicitly via SELECT *;
-- only the CHECK enum changes vs the pre-rebuild table.
INSERT INTO identifiers_new SELECT * FROM identifiers;

DROP TABLE identifiers;

ALTER TABLE identifiers_new RENAME TO identifiers;

-- ─── Recreate indexes (carry forward from 0019) ─────────────────────────────
CREATE INDEX IF NOT EXISTS idx_identifiers_identifier
    ON identifiers(identifier);
CREATE INDEX IF NOT EXISTS idx_identifiers_type
    ON identifiers(identifier_type);
CREATE INDEX IF NOT EXISTS idx_identifiers_category
    ON identifiers(device_category);
CREATE INDEX IF NOT EXISTS idx_identifiers_superseded
    ON identifiers(superseded_by);
CREATE INDEX IF NOT EXISTS idx_identifiers_ident_type
    ON identifiers(identifier, identifier_type);
CREATE INDEX IF NOT EXISTS idx_identifiers_paired
    ON identifiers(paired_identifier_id);

-- ─── FK integrity assertion ──────────────────────────────────────────────────
PRAGMA foreign_key_check;

-- ─── Version bump ────────────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (23, '0023_identifier_type_check_extension_cp28');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - MAC-181 (this dispatch's parent issue — v1.3.0 release sweep cycle)
-- - MAC-177 disposition `comment-0d15de7b-25a9-4f1e-bb40-65f00bc30fce`
--   (CEO ratification of CP28(c) "approve full path" 2026-05-18)
-- - ~/argus-internal/desktop_test/extraction_outputs/wave_h_pre_v1/
--     HANDOFF_TO_VALIDATOR.md §11(c) (empirical anchor for the 3 new types)
-- - db/migrations/0019_identifier_types_round2.sql (immediate-prior
--   identifier_type enum extension; cumulative CHECK carry-forward source)
-- - BIBLE_AMENDMENTS.md CP28 entry (this migration's amendment-log sibling,
--   composed in the same cycle and anchored on this migration's commit hash)
-- - feedback_cumulative_check_enum_across_sequenced_migrations.md
-- - feedback_enum_amendment_needs_schema_migration_sibling.md
-- - feedback_bible_amendment_child_issue_id_ordering.md
-- - feedback_bible_amendment_downstream_consumer_audit.md (§S.6.1 — this
--   migration is the schema-half of the worker-autonomous-absorption cycle)
