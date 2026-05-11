-- ============================================================================
-- DRAFT MIGRATION — NOT APPLIED — QUEUED FOR CEO RATIFICATION
-- ============================================================================
-- Filename intentionally ends in `.sql.draft`. CEO promotes to
-- `0013_drone_rid_and_proprietary_protocol_identifier_types_extension.sql`
-- at Phase 3 application time.
--
-- Migration: 0013_drone_rid_and_proprietary_protocol_identifier_types_extension
-- Purpose:   Extend `identifiers.identifier_type` CHECK enum with thirteen
--            new types clustered around Drone Remote ID (FAA/ASD-STAN) and
--            the proprietary RF-protocol catalog surfaced by Wave-A Phases
--            3a/4a/4b/4c/4d/4e/4h.
-- Surfaced:  Wave-A Phase 3a (alphafox02/DragonSync + faa-rid-lookup
--            submodule — 481 drone_id_prefix instances from 4783-record FAA
--            SQLite at FAA publicDOCRev 2025-11-28 build); +Phase 4a/4b
--            (opendroneid wireshark dissector + Android receive paths);
--            +Phase 4c (HSLU thesis on prEN 4709-002); +Phase 4d (RUB-SysSec
--            DroneSecurity DJI proprietary 76-identifier catalog); +Phase 4e
--            (proto17/dji_droneid extensions); +Phase 4h (nixxxo/tagfinder
--            BLE adv parsing).
-- Authority: CEO Wave-A Ratification Run dispatch 2026-05-11 §1 + §3.1.4
--            (fold-in 8 additional types) + board comment bbb71be5 2026-05-11
--            (rename to "_and_proprietary_protocol_" to capture scope beyond
--            Drone-RID proper).
-- Bible:     §11 #11 — schema changes are CEO-only ratification. This draft
--            is a proposal, not an application.
-- Pattern:   SQLite table-rebuild per 0009 precedent. Same mechanics as
--            0011 and 0012 siblings in the CP14 batch.
-- Risk:      Medium-low. Table rebuild touches every existing identifiers
--            row (column-preserving INSERT SELECT). CHECK constraint
--            extends by 13 values; column shape unchanged.
-- ============================================================================
--
-- Migration-slot allocation chain of record (CP14 batch update):
--   0010 = behavioral_signatures NEW TABLE (CP14)
--   0011 = ble_manufacturer_id identifier_type extension (CP14)
--   0012 = paired_identifier_id column on identifiers (CP14)
--   0013 = drone-RID + proprietary-protocol identifier_types extension
--          (CP14 — this migration; 13-type fold-in)
--   0014 = surveillance-metadata identifier_types extension (CP14 —
--          alpr_model only; operator_profile HELD as G-17)
--
-- File renamed per board direction bbb71be5: previously named
-- `0013_drone_rid_identifier_types_extension.sql.draft`. The 8-type
-- fold-in pushes scope beyond Drone Remote ID proper into proprietary
-- RF-protocol territory (DJI proprietary catalog, Bluetooth LE PDU
-- subtypes, Wi-Fi Aware service names, etc.). The conceptual cluster
-- (RF surveillance-target identification) holds — single coordinated
-- migration cleaner than splitting to 0013+0015.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- The 13 new identifier_type values
-- ─────────────────────────────────────────────────────────────────────────────
-- Drone-RID cluster (original 0013 scope per gates queue G-9):
--   1. drone_id_prefix         — FAA ANSI/CTA-2063-A serial prefix → manufacturer/
--                                make/model mapping (e.g., `1581Fxxx` DJI;
--                                `1748xxxx` Autel; `1668xxxx` Skydio; `1588E04xx`
--                                Parrot). 481 instances staged from FAA RID
--                                lookup (4783-record SQLite, FAA publicDOCRev
--                                2025-11-28).
--   2. icao_24bit_address      — ADS-B / UAT 24-bit hex aircraft addresses
--                                (e.g., `xxxxxx` hex format). 1 conceptual
--                                instance staged from 3a.
--   3. rf_channel              — Standardized RF center frequencies in MHz
--                                (1090 ADS-B, 978 UAT, 5800 FPV, 5756.5 DJI O4,
--                                2399.5/2414.5/2429.5/2444.5/2459.5 DJI DroneID
--                                2.4G, 5776.5/5796.5 DJI O4 5.8G). 12 staged
--                                (4 from 3a + 8 from 4e).
--   4. burst_cadence_ms        — Deterministic RF-burst period in milliseconds
--                                (e.g., 600 ms DJI DroneID). 1 staged from 4e.
--   5. bandwidth_mhz           — RF channel bandwidth specification (10 MHz
--                                occupied; 15.36 MHz LTE-derived total-with-
--                                guard for DJI DroneID). 2 staged from 4e.
--
-- Phase-4 fold-in (dispatch §3.1.4 — proprietary protocol cluster):
--   6. device_class_id         — opendroneid spec UA-Type enum values (Aeroplane,
--                                Helicopter/Multirotor, Gyroplane, etc.).
--                                Surfaced by 4a/4b/4c protocol-enum extraction.
--   7. rf_burst_duration       — Deterministic RF-burst duration values (paired
--                                with burst_cadence_ms; the burst is `duration`
--                                ms wide repeated every `cadence` ms).
--   8. rf_protocol_constant    — Protocol-defined magic numbers and constants
--                                (e.g., DJI DroneID CRC polys `0x3692`/`0x11021`,
--                                Gold seed `0x12345678` from 4d).
--   9. wifi_aware_service_name — Wi-Fi Aware (NAN) service identifier strings.
--                                Distinct shape from BLE service UUIDs.
--  10. wifi_ie_element_id      — IEEE 802.11 Information Element IDs surfaced
--                                by wireshark dissector (4b) and Drone-RID
--                                wrapping detection.
--  11. bluetooth_le_pdu_type   — BLE PDU type values (4-bit field per BLE
--                                spec). Used by Drone-RID Beacon LE Legacy
--                                detection and tracker-MAC distinguishers.
--  12. wifi_frame_control_subtype — IEEE 802.11 Frame Control subtype values
--                                (e.g., Management/Control/Data with sub-
--                                discrimination). Surfaced by 4b.
--  13. wifi_nan_param_signature — Composite Wi-Fi Aware parameter signature
--                                (e.g., `04:09:50:6F:9A:13` from 4b). Longer
--                                than 3-byte OUI; structurally distinct.
--                                NOTE: this is the new identifier type that
--                                handles the `88:69:19:9D:92:09` 6-byte NaN
--                                service ID case flagged in G-1 §4 note 1.
--
-- §8.2 source-banding for these types (per board ratification of revised
-- G-13.3 framing; same discipline applies):
--   - 481 drone_id_prefix from FAA RID lookup → single authoritative federal
--     source. Dispatch §4.1 flags this as a §6 human-CEO call (single-
--     authoritative-federal-source vs ≥3-source rule). HOLD these from
--     promotion-cycle-1 promotion pending §6 disposition.
--   - DJI proprietary identifiers from 4d (RUB-SysSec) → `academic` band
--     70–90 (NDSS 2023 paper-backed).
--   - opendroneid spec values from 4a/4b/4c → `official` band 90–100 (the
--     specs are SDO publications).
--
-- §11 hard-rule discipline (cite verbatim per 0009 precedent header):
--   §11 #1  no fabrication — every promoted row has source_url +
--             source_excerpt + raw_observations ancestor
--   §11 #7  schema-only here; promotion happens in Phase 4
--   §11 #8  no confidence drift; same §7.3 intake-side discipline
--   §11 #11 amendment-log discipline — coordinated commit pairs with
--             BIBLE_AMENDMENTS.md CP14 entry
--
-- ─────────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
-- Column list reflects post-0012 state (paired_identifier_id + pair_kind
-- added by 0012 in the Phase-3 application sequence). CHECK enum extended
-- with 13 new values (cumulative count: 26 valid identifier_type values).
CREATE TABLE identifiers_new (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    identifier        TEXT NOT NULL,
    identifier_type   TEXT NOT NULL CHECK (identifier_type IN (
                          -- Pre-CP13 (0001 initial)
                          'oui', 'mac', 'mac_range', 'bssid',
                          'ssid_exact', 'ssid_pattern',
                          'ble_uuid', 'ble_service',
                          'device_fingerprint',
                          -- CP13 (migration 0009) — Wave G structural fidelity
                          'ble_local_name', 'ble_characteristic',
                          'product_family_codename',
                          -- CP14 (migration 0011) — G-3 BLE SIG manufacturer IDs
                          'ble_manufacturer_id',
                          -- CP14 (migration 0013 — this migration) — Drone-RID
                          -- cluster (G-9 original scope)
                          'drone_id_prefix',
                          'icao_24bit_address',
                          'rf_channel',
                          'burst_cadence_ms',
                          'bandwidth_mhz',
                          -- CP14 (migration 0013 — this migration) — Phase-4
                          -- proprietary-protocol fold-in (dispatch §3.1.4)
                          'device_class_id',
                          'rf_burst_duration',
                          'rf_protocol_constant',
                          'wifi_aware_service_name',
                          'wifi_ie_element_id',
                          'bluetooth_le_pdu_type',
                          'wifi_frame_control_subtype',
                          'wifi_nan_param_signature'
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
                          'manufacturer_app'
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

-- Column-preserving copy. All 16 columns enumerated; only the CHECK enum
-- and (in 0014) one more enum value will change in subsequent migrations.
INSERT INTO identifiers_new SELECT * FROM identifiers;

DROP TABLE identifiers;

ALTER TABLE identifiers_new RENAME TO identifiers;

-- ─── Recreate indexes (carry forward from 0009 + 0012) ──────────────────────
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
    (13, '0013_drone_rid_and_proprietary_protocol_identifier_types_extension');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - raw/wave_a/_phase4_aggregation_2026-05-11.md (4a/4b/4c/4d/4e/4h surfacing
--   detail; 8-type fold-in source)
-- - raw/wave_a/_phase2_aggregation_2026-05-11.md (Phase 2 totals + carryover)
-- - raw/wave_a/_ceo_gates_queue_2026-05-11.md G-9
-- - raw/wave_a/alphafox02_DragonSync/20260511T051056Z_surfacing.md
--   (FAA RID provenance; 481 drone_id_prefix)
-- - raw/wave_a/_phase2_self_review_2026-05-11.md (board ratification anchor)
-- - db/migrations/0009_manufacturer_app_and_identifier_type_extensions.sql
--   (table-rebuild precedent)
-- - db/migrations/_drafts/0011_ble_manufacturer_id_identifier_type_extension.sql.draft
--   (immediate predecessor; cumulative-enum carry-forward)
-- - db/migrations/_drafts/0014_surveillance_metadata_identifier_types_extension.sql.draft
--   (immediate successor; carries alpr_model on top)
