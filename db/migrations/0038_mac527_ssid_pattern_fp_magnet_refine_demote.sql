-- ============================================================================
-- Script:    0038_mac527_ssid_pattern_fp_magnet_refine_demote.sql
-- Status:    STAGED — applied to the canonical db/argus.db in the same staged
--            commit that regenerates exports (STAGE ONLY — no push, no tag).
--            Ships in the normal v1.6.15 board push gate (CTO ratifies; board
--            owns the push). Slot 0038 is free — verified by direct working-tree
--            read (highest live = 0037, MAC-511). schema_version is NOT bumped
--            (data-only refine/withdrawal; no schema change) — stays at 33.
-- Issue:     MAC-527 (parent MAC-516) — spawned by the MAC-522 WiGLE re-mine.
-- Provisional CP:  CP52 (numbered pending board CP-finalization, same caveat as
--            the provisional CP51 in BIBLE_AMENDMENTS.md — CP48-51 still
--            board-un-finalized).
--
-- Purpose:   Fix a downstream-consumer false-positive defect baked into the
--            SHIPPED v1.6.14 export. CP51/MAC-517 unlocked all active
--            `ssid_pattern` rows into the Lynceus 0.9.2 matcher, which matches
--            each converted substring as a CASE-INSENSITIVE BARE SUBSTRING
--            (`? LIKE '%'||needle||'%' COLLATE NOCASE`,
--            export_lynceus.py:98/611, Lynceus db.py:1126). The MAC-522 WiGLE
--            re-mine (operator_review/MAC-522/cto_wigle_ratification.md) fired
--            the SAME contains-query against WiGLE and proved 14 of the 32
--            shipped substrings are SEVERE FP magnets: a consumer scanner
--            running Lynceus 0.9.2 mislabels ordinary home/business WiFi as
--            surveillance (e.g. `flock`→"Schneeflocke", `Penguin`→112k home
--            nets, `dji`→"Fidji", `oxygen`→"Oxygen.Net Krakow",
--            `iCSee`→"LogisticsEE"). CEO product call (MAC-527, one-way door,
--            not re-opened here): refine/demote the 14 SEVERE substrings by
--            rule; leave the 12 LOW-FP stems alone; tighten the 6 MODERATE only
--            where cheap and lossless. The structural fix (Lynceus matcher
--            hardening: min-len>=5 + word/`_`/`-` boundary anchoring) is a
--            separate board-owned lever tracked under MAC-517/MAC-356 — this
--            migration does NOT block on it and deliberately keeps every REFINE
--            row in canonical so the stems can be relaxed back once the matcher
--            is hardened.
--
-- Mechanism (two, both pure-DB, NO code change — the byte-mirrored
--            `_ssid_pattern_to_substring` helper in export_lynceus.py /
--            coverage_matrix.py is untouched; it re-derives every substring from
--            the new stored values, so the `_reconcile` cross-check stays green):
--   (A) WITHDRAW — CP32 §9 'withdrawn-without-successor' tri-state self-loop:
--       `superseded_by = id` + `confidence = 0`. Row leaves the active set
--       (exports filter `superseded_by IS NULL`), so its substring stops
--       shipping AND the row drops from the CSV/active count. Used for the
--       categorically-wrong-identifier rows (rule 1) and the bare-stem drops
--       with no salvageable device form whose vendor retains rich coverage
--       (rule 2/3). The verbatim original value is preserved in the row (only
--       superseded_by/confidence change) so a future migration can un-withdraw.
--   (B) REFINE — in-place `identifier` UPDATE to a delimiter-anchored form
--       `(?i)^(X_|X-).*` (or the mine-confirmed `MAVIC_`/`Mavic-`). The export
--       SPLITs the leading `(a|b)` alternation and takes each literal branch as
--       a stem, so the shipped substrings become `x_` and `x-` — which require
--       a `_`/`-` boundary and thereby kill the confirmed mid-word FPs
--       (`inspirefreewifi`, `parrothead`, `bananafish`, `williamsabc`,
--       `LogisticsEE`, `Handelsagentur`-class noise). The verbatim original
--       regex (which encoded model lists) is preserved in THIS FILE (old→new
--       below) for the matcher-hardening relax-back.
--
-- Notes column: NOT modified. 10 of the 17 target rows carry CP39 text-suffix
--   corruption (`… } | cp39_conf_lift:…`, json_valid(notes)=0), so a json_set
--   merge would NULL them (§11 #17). The migration file + the provisional CP52
--   BIBLE amendment are the audit trail for the per-row disposition (0037 could
--   annotate notes only because all its rows were clean-JSON).
--
-- Fan-out: verified 0 rows reference any of the 17 targets via `superseded_by`
--   or `paired_identifier_id` (MAC-527 pre-stage aggregate check, empty result).
--
-- Marquee-coverage guard (rule 3, cited per vendor from the live-DB identifier
--   inventory; every dropped/refined vendor RETAINS >=1 working identifier —
--   never drop the last identifier for a marquee vendor):
--   * Flock Safety (flock×3, Penguin WITHDRAWN): retains 38 oui + 4 mac +
--     5 ssid_exact (`Flock`/`Flock-230503`/`Flock-*`) + 7 ble_service +
--     ble_service_uuid + 10 ble_local_name + FS Ext Battery (kept, LOW-FP).
--   * DJI (dji WITHDRAWN; phantom/mavic/inspire REFINED): retains 15 oui +
--     51 drone_id_prefix + ble_manufacturer_id + refined mavic/phantom stems.
--   * Parrot (parrot/anafi REFINED): retains 5 oui + ble_company_id +
--     ble_manufacturer_id + fcc_grantee + asdstan_enum_value.
--   * Motorola Solutions / Vigilant (vigilant WITHDRAWN): retains 10 oui +
--     ble_service_uuid + ble_local_name + ble_company_id + fcc_grantee.
--   * Magnet Forensics (magnet WITHDRAWN): retains 2 network_discovery_protocol
--     _pattern + 2 product_family_codename (kept in canonical).
--   * Oxygen Forensics (oxygen WITHDRAWN): retains 1 network_discovery_protocol
--     _pattern + 3 product_family_codename + 3 vendor_controlled_hostname.
--   * MSAB (msab/xry REFINED, not dropped): retains firmware_branded_string +
--     network_discovery_protocol_pattern + 3 product_family_codename.
--   * iCSee / Xiongmai (iCSee): ssid_pattern is its SOLE identifier → REFINED,
--     never dropped (rule 3).  V380/Macrovideo (V380 REFINED): sole-family →
--     lossless CEO-blessed `V380`→`V380_`/`V380-`.
--   * `alpr` (id 44469): category-acronym leakage, NO manufacturer → clean
--     withdraw (rule 1, no vendor to preserve).
--
-- LEAVE ALONE (NOT in this migration — for the record):
--   12 LOW-FP stems: skydio, genetec, autovu, FS Ext Battery, graykey,
--     grayshift, HDMiniCam, MATECAM, SPYSITE, CamHipro, BLACKLENS, EUROSPY.
--   4 MODERATE stems left bare (distinctive tokens / sole identifiers where a
--     tighten would risk recall for little FP payoff): autel, elsag, iMiniCam,
--     MVSPT. (The other 2 MODERATE — mavic, V380 — ARE refined below.)
--   The 6 `unknown`-category router rows (mp70/ibr/airlink/cradlepoint/rv50/
--     es450) never reach the ssid gate; `lpr` (44470) stays FP-held.
--
-- Predicted export delta (ISOLATED at the v1.6.14 / active-43,134 baseline,
--   Wave-6 ids 44659-44666 excluded — mirrors the CP51 isolation; PROVEN by the
--   throwaway regen recorded in operator_review/MAC-527/):
--     surviving_ssid_rows 33 → 24 ; substring_records 32 → 34
--       (+9 refine-splits −7 withdrawn substrings) ;
--       split_expansions 1 → 10 ; nocase_deduped 2 → 0
--     standard feed record_count 977 → 979 (+2) ;
--     high-confidence feed 481 → 479 (−2: flock, Penguin withdrawn) ;
--     CSV active 43,134 → 43,125 (−9 withdrawn) ;
--     argus_run_id CHANGES (active-set fingerprint changed — a real DB write,
--       unlike the CP51 export-only flip).
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- (A) WITHDRAW — 9 rows (CP32 §9 self-loop + confidence 0). Idempotent:
--     matches only while still active (superseded_by IS NULL).
-- ---------------------------------------------------------------------------
-- Flock Safety — bare case-variants (rule 3, no salvageable form: Schneeflocke/
-- RockFlock/flockportal; Flock covered by ssid_exact Flock-* + 38 oui + BLE).
UPDATE identifiers SET superseded_by = id, confidence = 0
  WHERE id = 559 AND identifier = 'flock'    AND identifier_type = 'ssid_pattern' AND superseded_by IS NULL;
UPDATE identifiers SET superseded_by = id, confidence = 0
  WHERE id = 560 AND identifier = 'Flock'    AND identifier_type = 'ssid_pattern' AND superseded_by IS NULL;
UPDATE identifiers SET superseded_by = id, confidence = 0
  WHERE id = 561 AND identifier = 'FLOCK'    AND identifier_type = 'ssid_pattern' AND superseded_by IS NULL;
-- Flock Penguin device-class codename (rule 3, no Flock-Penguin AP form; 112k
-- home-net FPs GreenPenguin/PurplePenguin/Bad_penguin; Flock covered as above).
UPDATE identifiers SET superseded_by = id, confidence = 0
  WHERE id = 563 AND identifier = 'Penguin'  AND identifier_type = 'ssid_pattern' AND superseded_by IS NULL;
-- Motorola/Vigilant (rule 3, common English word "Be Vigilant"; no device form;
-- Motorola covered by 10 oui + BLE).
UPDATE identifiers SET superseded_by = id, confidence = 0
  WHERE id = 44465 AND identifier = '(?i)^vigilant[_-]?.*' AND identifier_type = 'ssid_pattern' AND superseded_by IS NULL;
-- `alpr` category-acronym leakage (rule 1; internal category label, no vendor).
UPDATE identifiers SET superseded_by = id, confidence = 0
  WHERE id = 44469 AND identifier = '(?i)^alpr[_-]?.*'     AND identifier_type = 'ssid_pattern' AND superseded_by IS NULL;
-- Magnet Forensics — forensic SOFTWARE, no field AP (rule 1); vendor kept via
-- network_discovery_protocol_pattern + product_family_codename.
UPDATE identifiers SET superseded_by = id, confidence = 0
  WHERE id = 39610 AND identifier = '(?i)^magnet[_-]?(forensic|axiom|acquire).*' AND identifier_type = 'ssid_pattern' AND superseded_by IS NULL;
-- Oxygen Forensics — forensic SOFTWARE, no field AP (rule 1); vendor kept via
-- network_discovery_protocol_pattern + product_family_codename + hostname.
UPDATE identifiers SET superseded_by = id, confidence = 0
  WHERE id = 41839 AND identifier = '(?i)^oxygen[_-]?forensic.*' AND identifier_type = 'ssid_pattern' AND superseded_by IS NULL;
-- DJI bare `dji` (rule 2, 3-char severe magnet "Fidji"/base64; redundant with
-- the refined mavic/phantom stems below + 15 DJI oui + 51 drone_id_prefix).
UPDATE identifiers SET superseded_by = id, confidence = 0
  WHERE id = 35597 AND identifier = 'dji[-_].+' AND identifier_type = 'ssid_pattern' AND superseded_by IS NULL;

-- ---------------------------------------------------------------------------
-- (B) REFINE — 8 rows, in-place `identifier` UPDATE to a delimiter-anchored
--     form. Idempotent: matches only the verbatim original value.
-- ---------------------------------------------------------------------------
-- DJI Phantom  (SEVERE; CEO-specified Phantom_/Phantom- form).
UPDATE identifiers SET identifier = '(?i)^(phantom_|phantom-).*'
  WHERE id = 35598 AND identifier = 'phantom[-_]?[0-9].*' AND superseded_by IS NULL;
-- DJI Mavic    (MODERATE; mine-confirmed MAVIC_AIR-/Mavic- naming).
UPDATE identifiers SET identifier = '(?i)^(mavic_|mavic-).*'
  WHERE id = 35599 AND identifier = 'mavic[-_]?(pro|air|mini|[0-9]).*' AND superseded_by IS NULL;
-- DJI Inspire  (SEVERE; drone-family delimiter form, kills inspirefreewifi).
UPDATE identifiers SET identifier = '(?i)^(inspire_|inspire-).*'
  WHERE id = 35600 AND identifier = 'inspire[-_]?[0-9].*' AND superseded_by IS NULL;
-- Parrot       (SEVERE; drone-family delimiter form, kills parrothead).
UPDATE identifiers SET identifier = '(?i)^(parrot_|parrot-).*'
  WHERE id = 35601 AND identifier = 'parrot[-_]?(anafi|bebop|disco|mambo).*' AND superseded_by IS NULL;
-- Parrot Anafi (SEVERE; delimiter form, kills bananafish/HanaFinancial).
UPDATE identifiers SET identifier = '(?i)^(anafi_|anafi-).*'
  WHERE id = 35602 AND identifier = 'anafi[-_]?.*' AND superseded_by IS NULL;
-- MSAB XRY     (SEVERE, shared row; delimiter form for BOTH branches, kills
--              williamsabc/WPAHMSABMVA and base64-xry noise; MSAB kept).
UPDATE identifiers SET identifier = '(?i)^(msab_|msab-|xry_|xry-).*'
  WHERE id = 39613 AND identifier = '(?i)^(msab|xry)[_-]?.*' AND superseded_by IS NULL;
-- iCSee/Xiongmai (SEVERE, SOLE identifier → refine not drop; kills LogisticsEE/
--              PublicSeeburg/VicsEero mid-word "icsee").
UPDATE identifiers SET identifier = '(?i)^(iCSee_|iCSee-).*'
  WHERE id = 44620 AND identifier = 'iCSee%' AND superseded_by IS NULL;
-- V380/Macrovideo (MODERATE, CEO-blessed lossless V380→V380_/V380-).
UPDATE identifiers SET identifier = '(?i)^(V380_|V380-).*'
  WHERE id = 44618 AND identifier = 'V380%' AND superseded_by IS NULL;

COMMIT;
