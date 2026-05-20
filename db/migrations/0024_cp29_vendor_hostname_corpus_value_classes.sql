-- ============================================================================
-- Migration: 0024_cp29_vendor_hostname_corpus_value_classes
-- Purpose:   Extend `identifiers.identifier_type` CHECK enum with 3 net-new
--            values per CP29 — the Wave I/I.5/I.6/I.7 vendor cloud-infrastructure
--            hostname corpus extraction. Final CHECK cardinality:
--            51 prior (post-CP28) + 3 net-new (CP29) = 54 values cumulatively.
-- Surfaced:  ~/argus-internal/wave_i_pre_v1/                  (Wave I main —
--                12,212 hostnames across 8 extraction classes; manifest.json
--                §candidates_by_value_class).
--            ~/argus-internal/wave_i_pre_v1/wave_i_5_deep_extension/
--                (+26 hostnames + cert metadata + Wayback historical + bucket
--                attribution; manifest_wave_i_5.json).
--            ~/argus-internal/wave_i_pre_v1/wave_i_6_continuation/
--                (+193 novel hostnames + Honeywell firmware bucket
--                acquisition + GitHub vendor org enum;
--                deprecated_hostname_verified.json sub-pass 7 NXDOMAIN-
--                verified 568 deprecated; manifest_wave_i_6.json).
--            ~/argus-internal/wave_i_pre_v1/wave_i_7_continuation/
--                (+159 novel hostnames + firmware deep-extract partial +
--                GitHub source mining + cross-source re-synthesis;
--                wave_i_lift_candidates_synthesis.json — 108 §8.3 lift
--                candidates pre-authored; manifest_wave_i_7.json).
--            Cumulative: 12,590 unique hostname candidates + 568 NXDOMAIN-
--                verified deprecated + 108 pre-authored §8.3 lifts +
--                2 Honeywell OTA signing certs from firmware.
-- Authority: Board "Argus v1.4.0 Integration Ship" dispatch on MAC-183
--            (Paperclip CEO comment id `575aca55-9843-4e1f-811f-e20436e06e12`,
--            2026-05-20T00:08:31Z). Phase 1 §1.1 conservative-codification
--            gate: codify only value_classes with empirical observations ≥1.
--            5 candidate value_classes evaluated; 3 codified (vendor_controlled_
--            hostname 12,620 attestations; vendor_cloud_endpoint_url 419 as
--            alternate; vendor_controlled_hostname_deprecated 568 NXDOMAIN-
--            verified); 2 deferred (vendor_asn_prefix 0; vendor_controlled_ip
--            0 across all cert IP-SAN sub-passes — defer to CP30/migration 0025
--            pending empirical observation).
-- Bible:     §11 #1   no fabrication — every new CHECK enum value cites
--                     empirical canon: Wave I cumulative manifest +
--                     deprecated_hostname_verified.json sub-pass 7 +
--                     candidate_value_class_alternates carrying
--                     vendor_cloud_endpoint_url across 419 attestations.
--            §11 #7   no main-table promotion without provenance — schema
--                     only here; row-level promotion happens in Phase 5
--                     after this migration applies, with raw_observations
--                     FK-chain via promoted_identifier_id.
--            §11 #8   no confidence drift — confidence column unchanged;
--                     CP29 sub-band ladder lives in BIBLE_AMENDMENTS.md
--                     (75-90 default / 85-95 cross-source / 95-99 firmware-
--                     cert ceiling per CP24 cross-source independence).
--            §11 #11  amendment-log discipline — sibling to BIBLE_AMENDMENTS
--                     CP29 entry (composed alongside this migration in the
--                     MAC-183 v1.4.0 cycle, anchored on this migration's
--                     commit hash per feedback_bible_amendment_child_issue_
--                     id_ordering).
--            §11 #15  no decompiled vendor source in git index — N/A;
--                     schema-only. Wave I.6 firmware ZIPs + Wave I.7
--                     unsquashed contents stay sandbox-isolated at
--                     ~/argus-internal/. Only extracted findings (hostnames
--                     + 2 OTA signing certs) flow into canonical row-level
--                     state in Phase 5.
--            §11 #16  facts-only promotion from public-but-unlicensed
--                     sources — binds row-level provenance at Phase 5
--                     promotion time, not at schema-extension time. Each
--                     CP29 sources row carries license_posture +
--                     upstream_license_posture defaults per CP21.
-- Pattern:   SQLite table-rebuild per 0009 / 0011 / 0013 / 0014 / 0018 /
--            0019 / 0023 precedent. PRAGMA foreign_keys=OFF outside
--            transaction; CREATE _new with extended CHECK; INSERT SELECT *
--            (column-preserving copy); DROP old; RENAME _new → old;
--            recreate 6 indexes verbatim from 0023; foreign_key_check;
--            schema_version bump; COMMIT; foreign_keys=ON.
-- Risk:      Low. Pure additive enum extension. Column shape unchanged from
--            0019 (16 columns + paired_identifier_id + pair_kind from 0012 =
--            17 cols). All 22,633 rows (22,553 active + 80 superseded)
--            preserved via INSERT SELECT *.
-- ============================================================================
--
-- Migration-slot allocation chain of record:
--   0001-0019  see 0019 header for the full chain through round-2 vocab
--   0020 = source_type enum extension (CP23 cycle-3 judicial/disclosure)
--   0021 = procurement_vendor_canonical_normalized
--   0022 = fcc_citation_deferred_queue
--   0023 = identifier_type CHECK extension CP28 — Wave H desktop-axis
--          (3 net-new values; 51-value cumulative CHECK)
--   0024 = identifier_type CHECK extension CP29 — Wave I/I.5/I.6/I.7 vendor
--          cloud-infrastructure hostname corpus — this migration
--          (3 net-new values; 54-value cumulative CHECK)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Cumulative CHECK enum (51 prior + 3 net-new = 54 values total)
-- ─────────────────────────────────────────────────────────────────────────────
-- The 51 prior values are paste-verified verbatim against the live
-- `identifiers` table CHECK clause sourced from migrations 0001 (9) +
-- 0009 (3) + 0011 (1) + 0013 (13) + 0014 (1) + 0018 (14) + 0019 (7) +
-- 0023 (3). Per feedback_cumulative_check_enum_across_sequenced_migrations,
-- the rebuild-pattern migration MUST carry forward ALL prior CHECK enum
-- values, not just its own delta.
--
-- The 3 net-new types (CP29 codification per Phase 0 §0.4 conservative gate):
--   1. `vendor_controlled_hostname`
--                                       — Vendor-owned cloud-infrastructure
--                                       hostnames (e.g. `hppki.honeywell.com`,
--                                       `duss.djicorp.com`, `*.flock-cdn.com`).
--                                       Confidence ladder per CP29 §2:
--                                       75-90 single-source default; 85-95
--                                       cross-source (CP24 independence);
--                                       95-99 firmware-embedded cert chain
--                                       (e.g. Honeywell OTA CodeSign RSA CA).
--                                       Empirical Wave I/I.5/I.6/I.7
--                                       cumulative: 12,620 attestation rows
--                                       over 12,590 unique hostnames across
--                                       8 extraction source_classes (B
--                                       crt.sh dominant at 11,551; A binary
--                                       extraction 587; I_github_readme 211;
--                                       I_github_source 159; F subdomain
--                                       enum 133; D + D_bucket_enum_deep
--                                       60; C cloud_doc 8; A_bucket_payload_
--                                       firmware 8/4-unique; J_package_
--                                       registry 4).
--                                       §4.4 posture: MAP (vendor-controlled
--                                       hostnames lift into Lynceus relevance
--                                       window as passively-scannable vendor
--                                       cloud endpoint signatures).
--   2. `vendor_cloud_endpoint_url`
--                                       — Vendor-controlled cloud endpoint
--                                       URL with path component embedding a
--                                       vendor-recognizable signature (e.g.
--                                       `https://duss.djicorp.com/functional-
--                                       document/<uuid>` — superset relation
--                                       to CP28 `vendor_document_uuid_cloud_
--                                       reference` which captures just the
--                                       UUID half). Confidence ladder per
--                                       CP29 §2: 80-90 default; 90-97 with
--                                       binary + CT log + sitemap multi-
--                                       source corroboration.
--                                       Empirical Wave I cumulative: 419
--                                       attestations carrying vendor_cloud_
--                                       endpoint_url in the candidate_value_
--                                       class_alternates field (not as
--                                       primary; co-extant URL-pattern
--                                       variant on the same hostname).
--                                       §4.4 posture: MAP (URL-shape variant
--                                       of vendor_controlled_hostname; same
--                                       relevance window).
--   3. `vendor_controlled_hostname_deprecated`
--                                       — Vendor-owned hostname previously
--                                       publicly resolvable, NXDOMAIN-verified
--                                       deprecated (no current DNS A/AAAA
--                                       record). Retained as historical
--                                       attribution anchor + supersession
--                                       chain pivot. Confidence ladder per
--                                       CP29 §2: 80-90 default (NXDOMAIN
--                                       active-verification at extraction
--                                       time is the dominant evidence; the
--                                       hostname's historical observation
--                                       in vendor binaries / CT logs /
--                                       Wayback captures contributes
--                                       attribution lineage).
--                                       Empirical Wave I.6 sub-pass 7:
--                                       deprecated_hostname_verified.json
--                                       classifications.confirmed_
--                                       deprecated_nxdomain = 568 of 964
--                                       probed.
--                                       §4.4 posture: DROPPED for active
--                                       passive-scan (no current DNS
--                                       resolution); MAP for historical
--                                       attribution / supersession analysis.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- CP29 deferred candidates (NOT codified in this migration)
-- ─────────────────────────────────────────────────────────────────────────────
-- `vendor_asn_prefix` (Wave I class G): asn_findings.json total=0; class G
--   halted with url_pattern_issue carry-forward to Wave I'/Wave J. Defer
--   codification to CP30 / migration 0025 pending empirical observation per
--   conservative ≥1-evidence gate. Bible CP29 §3 records the defer.
--
-- `vendor_controlled_ip` (Wave I.5+I.6+I.7 cert IP SAN sub-passes): 0/0
--   surfaced across all three deep passes (I.5 PEM fetch rate-limited; I.6
--   total=0; I.7 sub-pass 11 partial killed at hikvision 0 IP SANs from 31
--   certs). Defer codification to CP30 / migration 0025 pending empirical
--   observation. Bible CP29 §3 records the defer.
--
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 hard-rule discipline (cite verbatim per 0009 / 0011 / 0013 / 0014 / 0018
-- / 0019 / 0023)
-- ─────────────────────────────────────────────────────────────────────────────
--   §11 #1   no fabrication — Wave I cumulative manifest +
--              deprecated_hostname_verified.json + 419-alternate count
--              are the empirical canon for each codified value_class.
--   §11 #7   no main-table promotion without provenance — schema-only
--              here; Phase 5 binds raw_observations FK-chain to identifiers.
--   §11 #8   no confidence drift — confidence column unchanged; CP29
--              ladder lives in BIBLE_AMENDMENTS.md.
--   §11 #11  amendment-log discipline — sibling to BIBLE_AMENDMENTS CP29
--              entry composed alongside this migration in MAC-183 v1.4.0
--              cycle.
--   §11 #15  no decompiled vendor source in git index — Wave I.6 firmware
--              ZIPs + Wave I.7 unsquashed contents stay sandbox-isolated
--              at ~/argus-internal/. Schema-only here; row-level Phase 5
--              writes carry only EXTRACTED FINDINGS into canonical.
--   §11 #16  facts-only promotion from public-but-unlicensed sources —
--              binds row-level provenance at Phase 5 routing-execution
--              time. Phase 3 source admissions carry license_posture +
--              upstream_license_posture defaults per CP21.
-- ─────────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = OFF;

BEGIN;

-- ─── identifiers table rebuild ──────────────────────────────────────────────
-- Column list reflects post-0023 state (17 columns total: 9 from 0001 + 1 from
-- 0012 paired_identifier_id/pair_kind addition + remaining cols stable through
-- 0019/0023). CHECK enum carries forward all 51 prior values + adds 3 net-new
-- (54 cumulative values).
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
                          -- CP29 (migration 0024 — this migration) — Wave I/I.5/
                          -- I.6/I.7 vendor cloud-infrastructure hostname corpus (3)
                          'vendor_controlled_hostname',
                          'vendor_cloud_endpoint_url',
                          'vendor_controlled_hostname_deprecated'
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

-- Column-preserving copy. All 17 columns enumerated implicitly via SELECT *;
-- only the CHECK enum changes vs the pre-rebuild table.
INSERT INTO identifiers_new SELECT * FROM identifiers;

DROP TABLE identifiers;

ALTER TABLE identifiers_new RENAME TO identifiers;

-- ─── Recreate indexes (carry forward from 0023) ─────────────────────────────
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
    (24, '0024_cp29_vendor_hostname_corpus_value_classes');

COMMIT;

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - MAC-183 (this dispatch's parent issue — v1.4.0 vendor cloud-infrastructure
--   hostname corpus integration ship)
-- - MAC-183 dispatch `comment-575aca55-9843-4e1f-811f-e20436e06e12`
--   (board CEO dispatch 2026-05-20T00:08:31Z)
-- - ~/argus-internal/wave_i_pre_v1/manifest.json (Wave I main manifest)
-- - ~/argus-internal/wave_i_pre_v1/wave_i_5_deep_extension/manifest_wave_i_5.json
-- - ~/argus-internal/wave_i_pre_v1/wave_i_6_continuation/manifest_wave_i_6.json
-- - ~/argus-internal/wave_i_pre_v1/wave_i_7_continuation/manifest_wave_i_7.json
-- - ~/argus-internal/wave_i_pre_v1/wave_i_6_continuation/
--     deprecated_hostname_verified.json (568 NXDOMAIN-verified)
-- - ~/argus-internal/wave_i_pre_v1/wave_i_7_continuation/
--     wave_i_lift_candidates_synthesis.json (108 §8.3 lift candidates)
-- - ~/argus-internal/wave_i_integration/_preflight/cp29_candidate_counts.json
--     (this migration's empirical-anchor inputs)
-- - db/migrations/0023_identifier_type_check_extension_cp28.sql (immediate-prior
--   identifier_type enum extension; cumulative CHECK carry-forward source)
-- - BIBLE_AMENDMENTS.md CP29 entry (this migration's amendment-log sibling,
--   composed in the same cycle and anchored on this migration's commit hash)
-- - SAR-13 entry in BIBLE_AMENDMENTS.md (this dispatch codifies SAR-13
--   schema-fabrication discipline as a sibling forensic; informs Phase 1.2
--   PRAGMA verification of every column name + type prior to SQL drafting)
-- - SAR-13.5 entry in BIBLE_AMENDMENTS.md (this dispatch codifies SAR-13.5
--   bucket attribution discipline; informs Phase 2.3 SAR-13.5 gate)
-- - feedback_cumulative_check_enum_across_sequenced_migrations.md
-- - feedback_enum_amendment_needs_schema_migration_sibling.md
-- - feedback_bible_amendment_child_issue_id_ordering.md
-- - feedback_bible_amendment_downstream_consumer_audit.md
