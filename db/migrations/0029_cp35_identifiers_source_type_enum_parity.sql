-- ============================================================================
-- Migration: 0029_cp35_identifiers_source_type_enum_parity
-- Purpose:   CP35 — extend `identifiers.source_type` CHECK enum +3 net-new
--            values (10 → 13 cumulative) to achieve parity with the
--            `sources.source_type` enum (extended at CP23 / migration 0020):
--              - 'judicial_filing'
--              - 'disclosure_filing'
--              - 'procurement_disclosure'
--
-- Surfaced:  MAC-249 Phase G Validator CPN-A (enum-parity gap between
--            `sources.source_type` and `identifiers.source_type`); reproduced
--            at MAC-250 Phase H J-5 (CourtListener RECAP, sid=48) dispatch
--            where 116 rows landed with `source_type='foia'` as the
--            CEO-ratified §8.2 65-85 band-bucket proxy.
--
-- Authority: MAC-251 dispatch (post-Wave-J cleanup; CEO-authored issue spec
--            naming this migration and CP35 anchor explicitly). CEO
--            ratification of the CP-number assignment is the open question
--            being raised back to CEO at MAC-251 reassign; this migration's
--            filename and per-row `cp_anchor='CP35'` in the J-5 relabel
--            follow MAC-251 spec verbatim. If CEO renumbers the CP slot,
--            this migration filename + the per-row `cp_anchor` are the only
--            scope-affecting artifacts; a follow-up rename + UPDATE would
--            be required for either to change.
--
-- Bible:     §11 #1   no fabrication — relabel restores canonical truth
--                     (sources(sid=48).source_type already='judicial_filing'
--                     pre-migration; identifier-row source_type catches up
--                     to the canonical sources FK).
--            §11 #7   provenance preserved — source_url NOT NULL unchanged;
--                     per-row source_url cites the issuer (CourtListener
--                     docket URLs) directly. Identifier-row source_type
--                     band-floor confidence (75) unchanged; 'foia' and
--                     'judicial_filing' both fall in §8.2 65-85 "public-
--                     record disclosure" band.
--            §11 #8   no confidence drift — relabel is a column UPDATE,
--                     not a row delta; identifiers.confidence column not
--                     touched. 116 rows retain confidence=75 verbatim.
--            §11 #11  amendment-log discipline — CP35 BIBLE_AMENDMENTS.md
--                     entry pending CEO disambiguation of CP35 slot
--                     collision with the pre-existing CP35-draft NDPP §4.4
--                     Lynceus mapping entry. Schema-side migration ships
--                     this commit; bible amendment-log entry follows in
--                     a coordinated sibling commit per CEO ratification.
--            §11 #17  carve-out audit invariant — the post-migration UPDATE
--                     appends `notes.cpn_a_proxy_relabel` (a new JSON
--                     sentinel-key block); does NOT mutate existing audit
--                     JSON in the relabeled rows (confidence_history,
--                     fetched_content_sha256, cycle_completion_state, etc.
--                     all preserved verbatim).
--            SAR-13   PRAGMA-first → sqlite_master.sql-first discipline:
--                     CHECK enum verified via sqlite_master DDL read pre-
--                     migration. Live `identifiers.source_type` CHECK enum
--                     baseline = 10 values (verified 2026-05-24 against
--                     `db/argus.db` schema_version=28).
--
-- Pattern:   SQLite table-rebuild per 0009 / 0015 / 0018 / 0019 / 0020 /
--            0023 / 0024 / 0025 / 0027 / 0028 precedent. Vanilla SQLite
--            cannot ALTER CHECK in place; identifiers rebuilt. Foreign keys
--            disabled outside transaction; new table created with extended
--            enum + ALL prior CHECK constraints preserved verbatim
--            (identifier_type 59-value enum from CP34, device_category
--            16-value enum from CP33, source_type 10→13 enum EXTENDED here,
--            pair_kind 5-value enum from CP31); column-preserving INSERT
--            via SELECT *; DROP old; RENAME new; recreate indexes;
--            foreign_key_check; schema_version bump.
--
-- Idempotency:
--   - INSERT OR IGNORE INTO schema_version at footer makes version bump idempotent.
--   - Re-running against schema=29 DB produces identical sqlite_master
--     strings and identical row counts (column-preserving INSERT SELECT *).
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Cumulative CHECK enum for source_type (10 prior + 3 net-new = 13 values)
-- ─────────────────────────────────────────────────────────────────────────────
-- Per `feedback_cumulative_check_enum_across_sequenced_migrations`, the
-- rebuild-pattern migration MUST carry forward ALL prior CHECK enum values,
-- not just its own delta. The 10 prior values are paste-verified verbatim
-- against the live `identifiers` table CHECK clause from migration 0028 at
-- schema_version=28.
--
-- Live enum verification (2026-05-24 against db/argus.db, schema_version=28):
--   identifiers.source_type CHECK:
--     'official', 'regulatory', 'procurement',
--     'academic', 'foia', 'crowdsourced',
--     'inferred', 'manufacturer_doc',
--     'manufacturer_app',
--     'primary_registry'           = 10 values
--   sources.source_type CHECK (post-CP23 / mig-0020):
--     above 10 + 'judicial_filing', 'disclosure_filing',
--                'procurement_disclosure'  = 13 values
--
-- The 3 net-new values added here close the parity gap. Semantics inherited
-- from CP23 header notes (`db/migrations/0020_source_type_enum_extension.sql`):
--   1. 'judicial_filing'        — Court records and RECAP-class artifacts
--                                  (CourtListener V4 admission; the 116
--                                  J-5 rows relabeled post-migration).
--   2. 'disclosure_filing'      — SEC EDGAR + analogous corporate-
--                                  disclosure filings (cycle-1 RG5
--                                  admission; 0 identifier rows currently
--                                  carrying this band — forward-compat).
--   3. 'procurement_disclosure' — Supplier-self-disclosure / vendor-side
--                                  procurement artifacts (0 identifier rows
--                                  currently — forward-compat for future
--                                  vendor-disclosed contract ingestion).
--
-- Migration-slot allocation:
--   0025  = CP31 FCC EAS identifier_type cluster + hub-and-spoke
--   0026  = CP32 §1 device_category enum extension automotive_telematics
--   0026a = MAC-204 phase10 vendor APK source admissions (data-only)
--   0027  = CP33 §1-§2 — cctv_camera + persistent_surveillance + through_wall_radar + imei_tac
--   0028  = CP34 — network_discovery_protocol_pattern identifier_type
--   0029  = CP35 — this migration (identifiers.source_type enum parity with
--                  sources.source_type per CP23 trio)
-- ============================================================================

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
-- CHECK enum on source_type extended +3 (10 → 13 cumulative). ALL other
-- CHECK constraints preserved verbatim (identifier_type 59-value from CP34,
-- device_category 16-value from CP33, confidence range, pair_kind 5-value
-- from CP31). Column shape unchanged from post-CP34 state (17 columns).
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
                          -- CP28 (migration 0023) — Wave H desktop-axis vendor-
                          -- registered non-BLE cluster (3)
                          'windows_installer_productcode_vendor_registered',
                          'windows_com_clsid_vendor_registered',
                          'vendor_document_uuid_cloud_reference',
                          -- CP29 (migration 0024) — Wave I/I.5/I.6/I.7 vendor
                          -- cloud-infrastructure hostname corpus (3)
                          'vendor_controlled_hostname',
                          'vendor_cloud_endpoint_url',
                          'vendor_controlled_hostname_deprecated',
                          -- CP31 (migration 0025) — FCC EAS identifier-type
                          -- cluster (2)
                          'fcc_grantee_code',
                          'equipment_class_code',
                          -- CP33 (migration 0027) — GSMA TAC cluster (1; 0 rows
                          -- promoted at CP33; forward-compat carried forward)
                          'imei_tac',
                          -- CP34 (migration 0028) — Wave G/H v1 CCTV cohort
                          -- camera-discovery protocol pattern (Hikvision SADP,
                          -- Dahua AirKiss/SmartConfig, Tiandy SADP-style, Axis
                          -- ONVIF WS-Discovery). 18 high-conf promoted at CP34.
                          'network_discovery_protocol_pattern'
                      )),
    device_category   TEXT NOT NULL CHECK (device_category IN (
                          -- 0001 initial — 12 values
                          'alpr', 'imsi_catcher', 'body_cam', 'police_radio',
                          'drone', 'gunshot_detect', 'hacking_tool',
                          'covert_cam', 'gps_tracker', 'face_recog',
                          'drone_detect', 'unknown',
                          -- CP32 (migration 0026) — automotive telematics arm cluster
                          'automotive_telematics',
                          -- CP33 (migration 0027) — v1.5.0 cohort lexicon expansion (+3)
                          'cctv_camera',
                          'persistent_surveillance',
                          'through_wall_radar'
                      )),
    manufacturer      TEXT,
    model             TEXT,
    confidence        INTEGER CHECK (confidence BETWEEN 0 AND 100),
    source_url        TEXT NOT NULL,
    source_type       TEXT NOT NULL CHECK (source_type IN (
                          -- Pre-CP13 (0001 initial; 8 values)
                          'official', 'regulatory', 'procurement',
                          'academic', 'foia', 'crowdsourced',
                          'inferred', 'manufacturer_doc',
                          -- CP13 (migration 0009)
                          'manufacturer_app',
                          -- CP15 (migration 0015)
                          'primary_registry',
                          -- CP35 (this migration) — enum parity with
                          -- sources.source_type per CP23 trio; closes the
                          -- gap surfaced at MAC-249 Phase G Validator CPN-A.
                          'judicial_filing',
                          'disclosure_filing',
                          'procurement_disclosure'
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
                                 'firmware_generation',
                                 -- CP31 (migration 0025) — FCC EAS structural pairing
                                 'fcc_grantee_equipment_class'
                             )
                         )
);

-- Column-preserving copy. All columns implicit via SELECT *; only the
-- source_type CHECK enum changes vs the pre-rebuild table.
INSERT INTO identifiers_new SELECT * FROM identifiers;

DROP TABLE identifiers;

ALTER TABLE identifiers_new RENAME TO identifiers;

-- ─── Recreate identifiers indexes (carry forward verbatim from 0028) ────────
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

-- ─── Schema version bump ────────────────────────────────────────────────────
INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (29, '0029_cp35_identifiers_source_type_enum_parity');

COMMIT;

-- Post-migration foreign-key integrity check (outside transaction per SQLite docs).
PRAGMA foreign_key_check;

PRAGMA foreign_keys = ON;

-- ============================================================================
-- Post-migration state (expected):
--   - schema_version row (29, '0029_cp35_identifiers_source_type_enum_parity')
--   - identifiers.source_type CHECK accepts 13 values (10 prior + 3 new)
--   - identifiers row count unchanged (column-preserving INSERT SELECT *)
--   - All 6 identifiers indexes recreated
--   - sources / behavioral_signatures / other tables untouched
--
-- Post-migration relabel (executed as a separate scripted UPDATE, not bundled
-- in this migration so the schema migration stays purely structural):
--   - 116 J-5 rows (source_url LIKE 'https://www.courtlistener.com/docket/%'
--     AND source_type='foia' AND notes.wave='j_widenet') relabeled to
--     source_type='judicial_filing' with notes.cpn_a_proxy_relabel sentinel.
--   - See `db/migrations/0029_cp35_j5_proxy_relabel.sql` (sibling script).
-- ============================================================================
