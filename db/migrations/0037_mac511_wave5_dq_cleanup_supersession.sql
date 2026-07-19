-- ============================================================================
-- Script:    0037_mac511_wave5_dq_cleanup_supersession.sql
-- Status:    STAGED — NOT APPLIED at write time to the repo working tree, BUT
--            (per MAC-511 Wave-5 Phase C) this migration IS applied to the
--            canonical db/argus.db in the same staged commit that regenerates
--            exports (STAGE ONLY — no push, no tag). It is a SEPARATE wave from
--            the armed v1.6.12 push gate (MAC-493, HEAD 3e34cbc) and ships in
--            its own board ingest+push gate (v1.6.13 / next wave). Slot 0037 is
--            free — verified by direct working-tree read (highest live = 0036,
--            MAC-489). schema_version is NOT bumped (data-only withdrawal; no
--            schema change) — stays at 33.
-- Purpose:   Wave-5 data-quality cleanup. Withdraw 43 active identifier rows
--            whose stored `identifier` value is NOT a valid identifier — it is
--            a scrape / APK string-pool concatenation artifact, an RFC-2606
--            reserved-placeholder domain, or a programming-language token
--            mis-typed as a hostname. All 43 currently reach the Lynceus feed
--            (confidence>=30; in fact all 43 are >=70 so they also reach the
--            high-confidence feed) — this is exactly the placeholder/junk the
--            operator saw in the watchlist (MAC-511 board ask; example given
--            `xt***13` — a Lynceus rendering of a junk value).
-- Scope:     43 rows in two identifier_types:
--              network_endpoint            22 (all conf=70, source mac349_apk_static)
--              vendor_controlled_hostname  21 (conf 85-90, source wave_i CP29 corpus)
-- Buckets (each row has a one-line rationale in its fp_supersession.reason):
--   A_apk_string_pool_glue (22 network_endpoint) — a real Samsara/cloud URL
--        prefix glued (no separator) to adjacent APK string-pool bytes:
--        foreign-locale UI labels (Geen/Ich/Ihnen/Nessuna/Incidencia/Sfaturi/
--        Numero/Jeanette/Gut), camelCase component names, a second https:// URL
--        (44324), a timezone+regex run (44315), or asset-name+code glue
--        (44328/44329 `.png`+letters). Removing the glued tail would leave a
--        valid URL; the STORED value is corrupt.
--   B_scrape_glue (10 vendor_controlled_hostname) — a real hostname prefix
--        (`api.meraki.com`, `dashboard.meraki.com`, `www.hcaptcha.com`,
--        `forums.expo.dev`, `mktorest.com`) glued to a dictionary-word run
--        (`.commaseparatedcall...`, `.commithookeffect...`, `combineeventhandlers`);
--        the `.com`/`.dev` TLD is followed by non-DNS letters => runaway string.
--   C_reserved_placeholder_domain (10 vendor_controlled_hostname) — RFC-2606
--        reserved names `example.com` / `exemple.com` (fr) / `ejemplo.com` (es),
--        bare or with a glued/permission/localized tail. Never a real vendor.
--   D_code_token_not_hostname (1 vendor_controlled_hostname) — id 29477
--        `javax.xml.xmlconstants` is the Java class `javax.xml.XMLConstants`
--        (OSS SDK string), not a hostname.
-- KEEP (explicitly spared look-alikes, NOT in this migration):
--   * Clean long support URLs: verizonconnect/samsara/motorola KB & install
--     guides (well-formed `#UUID-...`/`#h_01...`/slug anchors), fleetio,
--     flocksafety API endpoints, axon/verizon privacy URLs.
--   * Real spyware/hacking_tool IOC domains from Amnesty Tech / mvt-project:
--     `todoinfonet.com`, `track-your-fedex-package.com/.org`,
--     `do-itonyour-own.com`, `recover-your-body.xyz`, `tw.itter.me` — high-value
--     indicators, NOT junk.
--   * Legit vendor subdomains that merely CONTAIN `.com`/`.it` mid-string:
--     `*.commerce.boschsecurity.com`, `*.itsm.northropgrumman.com`,
--     `usgov.commandcentral.com`, `hellasjournal.company`,
--     `api-docs.rhombus.community`, `*.turn.*.webrtc.connect.axis.com`,
--     `*.motorolasolutions.com`, `*.magnetforensics.com`, `*.l3harris.com`.
--   * Valid registry codes / short codes and regex/wildcard patterns
--     (ssid_pattern, network_endpoint wildcards) untouched.
--   * FLAGGED FOR CEO REVIEW (deliberately NOT withdrawn here — borderline or
--     policy): the 261-row conf=0 `fp_class:third_party_oss_sdk_root` cohort
--     (already feed-excluded); truncations/brand tokens `www.unicode`,
--     `hppki.honeywell`, `wisenet`, `peticaonline.comv`; `localhost:54664`;
--     `*.tcomlp.com.tcomlp.com` (real crt.sh cert SAN); Samsara borderline
--     URLs 44317/44309/44314/44323/44308/44301; `test-example.sandbox.meraki.com`.
-- Fan-out: verified 0 rows reference any of the 43 via superseded_by or
--          paired_identifier_id (MAC-512 Phase B aggregate check).
-- json_valid: all 43 target rows have valid-JSON notes (swept pre-stage,
--          MAC-512); json_set merges a new $.fp_supersession key, preserving
--          all existing top-level keys (§11 #17 carve-out audit invariant).
-- Mechanism: CP32 §9 'withdrawn-without-successor' tri-state self-loop —
--          superseded_by = id + confidence = 0. The canonical active-set
--          filter `WHERE superseded_by IS NULL` drops them from the Lynceus
--          feed. Mirror of MAC-477 (mig-0034/0035/0036) + MAC-489. No row is
--          deleted — full provenance + cite + prior_confidence retained for
--          audit and reversibility (§11 #1).
-- Reversibility: to revert a row: superseded_by=NULL,
--          confidence=notes.$.fp_supersession.prior_confidence, and remove the
--          $.fp_supersession key. The backup
--          /home/kev/argus-backups/argus.db.mac511_precleanup_20260719T034701Z.bak
--          (integrity_check ok, source sha256 fea9decafc54e5e9...) is the net.
-- Re-apply safety: each UPDATE pins superseded_by IS NULL; the strict pre-guard
--          blocks re-application (0 of 43 expected-active remain on a 2nd run ->
--          CHECK(ok=1) fails -> full rollback, zero mutation). Verified on a
--          throwaway copy before canonical apply (MAC-512).
-- Authority: MAC-511 board request; MAC-512 CTO survey + ratification.
-- ============================================================================
-- APPLY-TIME PRECONDITION (operator): backup already exists (do not re-backup) —
--   /home/kev/argus-backups/argus.db.mac511_precleanup_20260719T034701Z.bak
-- ============================================================================

BEGIN TRANSACTION;

-- ---- strict pre-condition guard (all-or-nothing) ------------------------
-- Aborts the whole transaction unless EXACTLY 43 active target rows are
-- present right now (22 network_endpoint conf=70 + 21 vendor_controlled_hostname
-- conf 85-90, all superseded_by IS NULL). CHECK(ok=1) fails -> rollback.
CREATE TEMP TABLE _mig0037_pre (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0037_pre(ok) SELECT CASE WHEN (
  SELECT COUNT(*) FROM identifiers
   WHERE id IN (26974,26977,26978,26995,27026,26998,27040,27050,27051,27052,27053,27054,27055,27056,27057,27064,27128,27207,27247,27251,29477,44302,44305,44306,44307,44310,44311,44312,44315,44316,44319,44320,44321,44322,44324,44325,44326,44327,44328,44329,44330,44313,44318)
     AND superseded_by IS NULL
     AND confidence >= 30
) = 43 THEN 1 ELSE 0 END;

-- ==== Bucket A — APK string-pool glue (22 network_endpoint, conf 70) =========
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-512','board_issue','MAC-511',
        'wave','wave_5_dq_cleanup',
        'mig','0037_mac511_wave5_dq_cleanup_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'bucket','A_apk_string_pool_glue',
        'reason','Corrupted APK string-pool concatenation: a real Samsara/cloud URL prefix glued (no separator) to adjacent extracted string-pool bytes (foreign-locale UI label, camelCase component name, a second https:// URL, or asset-name+code run). Source cohort mac349_apk_static. The stored identifier is not a valid endpoint; removing the glued tail would leave a valid URL. Not a scanner identifier.',
        'source_cohort','mac349_apk_static',
        'prior_confidence', confidence,
        'date','2026-07-19'))
WHERE id IN (44302,44305,44306,44307,44310,44311,44312,44313,44315,44316,44318,44319,44320,44321,44322,44324,44325,44326,44327,44328,44329,44330)
  AND identifier_type = 'network_endpoint'
  AND superseded_by IS NULL;

-- ==== Bucket B — scrape glue (10 vendor_controlled_hostname, conf 85-90) =====
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-512','board_issue','MAC-511',
        'wave','wave_5_dq_cleanup',
        'mig','0037_mac511_wave5_dq_cleanup_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'bucket','B_scrape_glue',
        'reason','Corrupted scrape concatenation (wave_i CP29 vendor-hostname corpus): a real hostname prefix glued to a dictionary-word run so the TLD (.com/.dev) is followed by non-DNS letters, producing a runaway string that is not a resolvable hostname. Not a scanner identifier.',
        'source_cohort','wave_i_v1_4_0_cp29',
        'prior_confidence', confidence,
        'date','2026-07-19'))
WHERE id IN (26974,26977,26978,26995,26998,27026,27064,27128,27207,27251)
  AND identifier_type = 'vendor_controlled_hostname'
  AND superseded_by IS NULL;

-- ==== Bucket C — reserved-placeholder domain (10 vendor_controlled_hostname) =
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-512','board_issue','MAC-511',
        'wave','wave_5_dq_cleanup',
        'mig','0037_mac511_wave5_dq_cleanup_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'bucket','C_reserved_placeholder_domain',
        'reason','RFC-2606 reserved-placeholder domain (example.com / exemple.com [fr] / ejemplo.com [es]), bare or with a glued / Android-permission / localized-word tail. A reserved documentation name, never a real vendor hostname. Not a scanner identifier.',
        'source_cohort','wave_i_v1_4_0_cp29',
        'prior_confidence', confidence,
        'date','2026-07-19'))
WHERE id IN (27040,27050,27051,27052,27053,27054,27055,27056,27057,27247)
  AND identifier_type = 'vendor_controlled_hostname'
  AND superseded_by IS NULL;

-- ==== Bucket D — code token mis-typed as hostname (1 vendor_controlled_hostname)
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-512','board_issue','MAC-511',
        'wave','wave_5_dq_cleanup',
        'mig','0037_mac511_wave5_dq_cleanup_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'bucket','D_code_token_not_hostname',
        'reason','javax.xml.xmlconstants is the Java class javax.xml.XMLConstants (a third-party OSS SDK string constant), not a hostname. Same fp_class as the conf=0 third_party_oss_sdk_root cohort, but this row was left at conf=85 and reaches the feed. Not a scanner identifier.',
        'source_cohort','wave_i_v1_4_0_cp29',
        'prior_confidence', confidence,
        'date','2026-07-19'))
WHERE id = 29477
  AND identifier_type = 'vendor_controlled_hostname'
  AND superseded_by IS NULL;

-- ---- strict post-condition guard ---------------------------------------
-- Exactly 43 target rows now withdrawn (superseded_by = id, confidence = 0).
-- Else abort the whole transaction.
CREATE TEMP TABLE _mig0037_post (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0037_post(ok) SELECT CASE WHEN (
  SELECT COUNT(*) FROM identifiers
   WHERE id IN (26974,26977,26978,26995,27026,26998,27040,27050,27051,27052,27053,27054,27055,27056,27057,27064,27128,27207,27247,27251,29477,44302,44305,44306,44307,44310,44311,44312,44315,44316,44319,44320,44321,44322,44324,44325,44326,44327,44328,44329,44330,44313,44318)
     AND superseded_by = id
     AND confidence = 0
) = 43 THEN 1 ELSE 0 END;

DROP TABLE _mig0037_pre;
DROP TABLE _mig0037_post;

COMMIT;

-- Post-apply expected state:
--   43 rows: superseded_by = id, confidence = 0 — dropped from the Lynceus feed
--   (active-set filter WHERE superseded_by IS NULL). Active identifiers
--   43177 -> 43134. Each type's feed contribution drops by its bucket count:
--     network_endpoint            -22
--     vendor_controlled_hostname  -21
--   No schema change (schema_version stays 33). No other row touched. All 43
--   rows + cites + prior_confidence retained in notes.$.fp_supersession.
