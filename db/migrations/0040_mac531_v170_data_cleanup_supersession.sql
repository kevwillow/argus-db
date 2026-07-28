-- ============================================================================
-- Script:    0040_mac531_v170_data_cleanup_supersession.sql
-- Status:    STAGED. Applied to the canonical db/argus.db in the same staged
--            commit (STAGE ONLY — no push, no tag; MAC-424 binding rule).
--            Slot 0040 is free — verified by direct working-tree read
--            (highest live = 0039 MAC-528; nothing named 004* anywhere in the
--            tree, committed or untracked). schema_version is NOT bumped
--            (data-only; no schema change) — stays at 33.
-- Purpose:   MAC-531 v1.7.0 data-cleanup pass — junk-row review, MAC-511
--            Wave-5 style (mirror of mig-0037). Withdraw 16 active identifier
--            rows whose stored `identifier` is not a usable scanner identifier:
--            scrape/string-pool scheme glue, third-party OSS/standards roots
--            mis-attributed to a surveillance vendor, hostnames truncated at a
--            non-TLD boundary, an Android platform token, a dotless bare brand
--            token, an RFC-6761 special-use loopback host, an unresolvable
--            (inert) upstream-typo domain, and one duplicate BLE company id in
--            non-canonical form. PLUS one in-place case normalization (lane I).
-- Scope:     16 withdrawals across three identifier_types +
--             1 normalization (fcc_grantee_code, export-dropped type).
--              vendor_controlled_hostname  13 (conf 75-90, wave_i CP29 + deep_github)
--              network_endpoint             2 (conf 65, 80)
--              ble_company_id               1 (conf 65)
-- Provenance of the sweep: heuristic scan over all 42,686 active feed-reaching
--            rows (operator_review/MAC-531/scan_junk.py, read-only), then
--            per-row cite-paste of source_url / source_excerpt / notes.
--            Buckets that fired but were 100% false positives are recorded in
--            the KEEP list below so the next pass does not re-litigate them.
--
-- Buckets (each row carries a one-line rationale in its fp_supersession.reason):
--   A_scrape_scheme_glue (2 vendor_controlled_hostname) — a real host glued to
--        the leading bytes of the NEXT URL in the same string pool, so the host
--        run terminates in a scheme token: `account.meraki-go.cn`+`http`,
--        `ap.meraki.com`+`.ws`+`http`. Terminal labels `cnhttp` / `wshttp` are
--        not delegated TLDs. Same corruption class as mig-0037 bucket B.
--   B_third_party_oss_root (6 vendor_controlled_hostname) — ubiquitous
--        third-party OSS / standards / protocol / SDK roots harvested out of a
--        vendor APK string pool and mis-attributed as vendor-controlled:
--        bouncycastle.org (crypto lib), jabber.org (public XMPP),
--        java.sun.com + www.sun.com (Java XML namespace/DTD roots),
--        www.slf4j.org (logging facade), test.baidu (Baidu SDK root, also a
--        `test.` placeholder subdomain). These are FP-magnets — ANY app
--        bundling the library carries the string. Identical class to the
--        214-row conf=0 `fp_class:third_party_oss_sdk_root` cohort and to
--        mig-0037 bucket D (id 29477 `javax.xml.xmlconstants`); ids 29475/29476
--        are the immediate id-neighbours of that already-withdrawn row and were
--        missed by the Wave-5 pass.
--   C_truncated_hostname (3 vendor_controlled_hostname) — a real host truncated
--        at a non-TLD boundary: `www.hik` (hikvision.com), `www.unicode`
--        (unicode.org — also a standards body, not a Honeywell vendor host),
--        `hppki.honeywell` (honeywell.com). None of `.hik` / `.unicode` /
--        `.honeywell` is a delegated TLD, so none can ever resolve.
--   D_platform_token_not_hostname (1 vendor_controlled_hostname) — id 29254
--        `android.asset` is the Android WebView asset-scheme / AAPT platform
--        token (`file:///android_asset/`), not a hostname. Same treatment as
--        mig-0037 bucket D.
--   E_dotless_bare_token (1 vendor_controlled_hostname) — id 35803 `wisenet`
--        is a bare brand token with no dot, typed as a hostname; its only cite
--        is a bioinformatics research-software JSON (`wisenet.biotools.json`)
--        for an unrelated homonym tool. Doubly invalid: not a hostname, and a
--        homonym-collision cite. NOTE the sibling id 35807
--        product_family_codename `wisenet` is a REAL Hanwha product family and
--        is deliberately NOT touched (its value is correct; only the weak cite
--        is flagged to the umbrella).
--   F_special_use_loopback (1 network_endpoint) — id 38594 `localhost:54664`.
--        RFC-6761 special-use loopback name; cite is the DEFAULT fallback in a
--        third-party SDR crate ("tries `http://localhost:54664` as the
--        default"). A scanner cannot detect a remote device via loopback, and
--        every host on earth "matches" — pure FP-magnet.
--   G_inert_unresolvable_tld (1 network_endpoint) — id 39378
--        `peticaonline.comv`. `.comv` is not a delegated TLD, so the value can
--        never resolve and can never match: the row is INERT, not merely
--        low-value. Flagged for CEO review by MAC-511 and deliberately left
--        then; this pass IS that review. NOTE: the cite is an authoritative
--        academic IOC feed (mvt-project intellexa_predator/domains.txt) whose
--        published line reads `peticaonline.comv`, so the withdrawal rests on
--        "inert / cannot ever match", NOT on "our extraction is corrupt". If
--        the board prefers cite-faithful retention this is the one row to
--        reverse — reversal is a single UPDATE (see Reversibility below).
--   H_duplicate_noncanonical (1 ble_company_id) — id 22841 `0x4C` is the same
--        SIG company id as id 22842 `0x004C` (both cited to the same
--        tagfinder.py file, lines 396 and 102) but written with 2 hex digits.
--        709 of the 715 active ble_company_id rows use the 4-hex-digit form.
--        This is the ONLY row in this migration that uses the CP32 §9
--        SUCCESSOR semantics (superseded_by = 22842, the surviving twin) rather
--        than the self-loop — per the tri-semantic rule, a withdrawal that HAS
--        a successor must point at it.
--   I_normalize_case (1 fcc_grantee_code, NOT a withdrawal) — id 39541
--        `2a2v6` is the only lowercase value among 218 active
--        fcc_grantee_code rows; its own source_url is `https://fccid.io/2A2V6`,
--        i.e. the cite proves the canonical casing. It has NO twin, so
--        withdrawing it would DESTROY a real Flipper Devices grantee code.
--        Corrected in place to `2A2V6`. fcc_grantee_code is export-DROPPED
--        (DROPPED_REASONS, export_lynceus.py) so the feed delta is zero.
--        This lane is deliberately called out because the MAC-531 brief asked
--        for a *withdrawal* migration — the board may strike lane I without
--        affecting lanes A-H.
--
-- KEEP (explicitly spared look-alikes — recorded so the next pass does not
--       re-litigate them; each was surfaced by a heuristic and cleared by cite):
--   * `.test.` as a SUBDOMAIN label in real crt.sh cert SANs — 40 rows
--     (izik.test.cellebrite.com, *.test.dev.bi.com, casebuilder.test.
--     soundthinking.com, api.test.agent-auth.internal.samsara.com, ...).
--     RFC-2606 reserves `.test` as a TLD only; these are genuine issued certs.
--   * Real delegated gTLD/ccTLD terminal labels that merely look odd:
--     `hellasjournal.company`, `api-docs.rhombus.community`,
--     `digitalplatforms.co.zw`, `group.nec` (NEC operates the `.nec` brand
--     gTLD; cite is a certspotter issuance), and the Amnesty Tech / mvt-project
--     Cytrox+Predator IOC domains `cyber.country`, `heaven.army`,
--     `mytrips.quest`, `sniper.pet`, `xf.actor`, `youtube.voto`, `9o.gg`,
--     `amazing.lab`, plus the `.ws` (Samoa) IOC domains `bit-li.ws`,
--     `bity.ws`, `mlinks.ws`, `msas.ws`. High-value indicators, NOT junk.
--   * `android.getac.com` — a real Getac host (matched an `^android\.` probe).
--   * `*.tcomlp.com.tcomlp.com` (id 36210) — a genuine observed cert SAN
--     ("SAN=*.tcomlp.com.tcomlp.com issued for tcomlp.com"); a real vendor
--     misconfiguration in CT logs, cite-faithful. Spared by MAC-511; spared
--     again here for the same reason.
--   * `fi-walk-` (id 44615, ble_local_name) — trailing hyphen is a genuine
--     device-name PREFIX (siblings `fi-db`, `fi-backhaul-db`), not truncation.
--   * The 5 remaining uppercase-hex ble_company_id rows (22842 `0x004C`,
--     22866, 22868, 22869, 22870) — a CASING question for CP47/MAC-360, not
--     junk. Flagged to the v1.7.0 umbrella as a separate normalization item;
--     deliberately NOT folded into this pass.
--   * All 336 rows added since MAC-511 (ids 44331-44666: Verizon Connect
--     support URLs, BLE UUIDs, OUIs, FCC codes, Wave-6) — swept, zero junk.
--   * `product_family_codename` id 35807 `wisenet` — real Hanwha product
--     family; only its cite is weak (flagged, not withdrawn).
--
-- Fan-out: verified 0 rows reference any of the 16 via superseded_by or
--          paired_identifier_id (aggregate COUNT, not a spot check).
-- json_valid: all 17 touched rows have valid-JSON notes (swept over the exact
--          mutation scope BEFORE staging — 17/17 json_valid=1). json_set merges
--          a new $.fp_supersession key and preserves every existing top-level
--          key (§11 #17 audit invariant; no text-suffix concat — CP39 rule).
-- Mechanism: CP32 §9 tri-semantic supersession.
--          Lanes A-G: 'withdrawn-without-successor' self-loop
--            (superseded_by = id, confidence = 0)  — 15 rows.
--          Lane H:    'withdrawn-with-successor'
--            (superseded_by = 22842, confidence = 0) — 1 row.
--          Lane I:    in-place value normalization — 1 row, NOT a withdrawal.
--          The canonical active-set filter `WHERE superseded_by IS NULL` drops
--          all 16. No row is deleted — full provenance + cite +
--          prior_confidence retained for audit and reversibility (§11 #1).
-- Expected deltas (predicted; the umbrella owns the single consolidated regen):
--          active identifiers  43,132 -> 43,116  (-16)
--          Lynceus standard feed  -1 pattern  (only id 22841 reaches the feed:
--            ble_company_id MAPs to ble_manufacturer_id, export_lynceus.py:151.
--            The other 15 are export-DROPPED: `vendor_controlled_hostname` and
--            `network_endpoint` are both in DROPPED_REASONS, export_lynceus.py
--            :203 and :234 — same reason mig-0037's 43-row withdrawal left the
--            feed unchanged at 945/478.)
--          Lynceus high-confidence feed  UNCHANGED (id 22841 is conf 65 < 70).
--          Lane I feed delta  ZERO (fcc_grantee_code is in DROPPED_REASONS).
-- Reversibility: to revert a withdrawal: superseded_by = NULL,
--          confidence = notes.$.fp_supersession.prior_confidence, and remove
--          the $.fp_supersession key. To revert lane I: set identifier back to
--          '2a2v6' and remove $.dq_normalization. The backup
--          /home/kev/argus-backups/argus.db.mac531_precleanup_20260728T160259Z.bak
--          (integrity_check ok, source sha256
--          8738edaeef11fdd7937e0e17faddbaa9fc2c3d07a5bf58e936da74efefd90907)
--          is the net.
-- Re-apply safety: every UPDATE pins `superseded_by IS NULL` (lanes A-H) or the
--          exact pre-value (lane I); the strict pre-guard blocks re-application
--          (0 of 16 expected-active remain on a 2nd run -> CHECK(ok=1) fails ->
--          full rollback, zero mutation). Proven on a throwaway copy before the
--          canonical apply.
-- Interaction with mig-0039 (MAC-528, Flock-* ssid_exact id 22910): row sets
--          are DISJOINT. mig-0039 was APPLIED to canonical by another run
--          DURING the MAC-531 survey (active 43,133 -> 43,132, id 22910 now
--          superseded_by=22910 conf=0); the MAC-531 backup and every number
--          in this header are measured POST-0039. Order-independent either way.
-- Authority: MAC-531 (board-added v1.7.0 data-cleanup pass), child of the
--          MAC-530 v1.7.0 consolidated-release umbrella.
-- ============================================================================
-- APPLY-TIME PRECONDITION (operator): backup already exists (do not re-backup) —
--   /home/kev/argus-backups/argus.db.mac531_precleanup_20260728T160259Z.bak
-- ============================================================================

BEGIN TRANSACTION;

-- ---- strict pre-condition guard (all-or-nothing) ------------------------
-- Aborts the whole transaction unless EXACTLY 16 active withdrawal targets are
-- present right now (all superseded_by IS NULL, all confidence >= 30) AND the
-- lane-H successor 22842 is itself active AND the lane-I row still holds its
-- exact pre-value. CHECK(ok=1) fails -> rollback, zero mutation.
CREATE TEMP TABLE _mig0040_pre (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0040_pre(ok) SELECT CASE WHEN (
  (SELECT COUNT(*) FROM identifiers
    WHERE id IN (22841,26975,26987,27237,29254,29475,29476,29598,29666,29684,
                 34582,35293,35295,35803,38594,39378)
      AND superseded_by IS NULL
      AND confidence >= 30) = 16
  AND (SELECT COUNT(*) FROM identifiers
        WHERE id = 22842 AND identifier = '0x004C'
          AND identifier_type = 'ble_company_id' AND superseded_by IS NULL) = 1
  AND (SELECT COUNT(*) FROM identifiers
        WHERE id = 39541 AND identifier = '2a2v6'
          AND identifier_type = 'fcc_grantee_code' AND superseded_by IS NULL) = 1
  AND (SELECT COUNT(*) FROM identifiers
        WHERE id IN (22841,26975,26987,27237,29254,29475,29476,29598,29666,29684,
                     34582,35293,35295,35803,38594,39378,39541)
          AND json_valid(notes) = 0) = 0
) THEN 1 ELSE 0 END;

-- ==== Lane A — scrape / string-pool scheme glue (2 vendor_controlled_hostname)
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-531','board_issue','MAC-530',
        'wave','v1_7_0_data_cleanup',
        'mig','0040_mac531_v170_data_cleanup_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'bucket','A_scrape_scheme_glue',
        'reason','Corrupted string-pool concatenation: a real vendor host glued (no separator) to the leading bytes of the next URL in the same pool, so the host run terminates in a scheme token (cnhttp / wshttp) that is not a delegated TLD. The stored value can never resolve. Same corruption class as mig-0037 bucket B. Not a scanner identifier.',
        'source_cohort','wave_i_v1_4_0_cp29',
        'prior_confidence', confidence,
        'date','2026-07-28'))
WHERE id IN (26975,26987)
  AND identifier_type = 'vendor_controlled_hostname'
  AND superseded_by IS NULL;

-- ==== Lane B — third-party OSS/standards root (6 vendor_controlled_hostname) =
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-531','board_issue','MAC-530',
        'wave','v1_7_0_data_cleanup',
        'mig','0040_mac531_v170_data_cleanup_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'bucket','B_third_party_oss_root',
        'reason','Ubiquitous third-party OSS / standards / protocol / SDK root harvested from a vendor APK string pool and mis-attributed as vendor-controlled (bouncycastle.org, jabber.org, java.sun.com, www.sun.com, www.slf4j.org, test.baidu). Any application bundling the library carries the string, so the row is a false-positive magnet with no attribution value. Identical class to the conf=0 fp_class:third_party_oss_sdk_root cohort and to mig-0037 bucket D (id 29477). Not a scanner identifier.',
        'source_cohort','wave_i_v1_4_0_cp29',
        'prior_confidence', confidence,
        'date','2026-07-28'))
WHERE id IN (27237,29475,29476,29598,29684,34582)
  AND identifier_type = 'vendor_controlled_hostname'
  AND superseded_by IS NULL;

-- ==== Lane C — truncated hostname (3 vendor_controlled_hostname) =============
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-531','board_issue','MAC-530',
        'wave','v1_7_0_data_cleanup',
        'mig','0040_mac531_v170_data_cleanup_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'bucket','C_truncated_hostname',
        'reason','Hostname truncated at a non-TLD boundary during extraction (www.hik -> hikvision.com, www.unicode -> unicode.org, hppki.honeywell -> honeywell.com). None of .hik / .unicode / .honeywell is a delegated TLD, so the stored value can never resolve. www.unicode is additionally a standards body, not a Honeywell vendor host. Not a scanner identifier.',
        'source_cohort','wave_i_v1_4_0_cp29',
        'prior_confidence', confidence,
        'date','2026-07-28'))
WHERE id IN (29666,35293,35295)
  AND identifier_type = 'vendor_controlled_hostname'
  AND superseded_by IS NULL;

-- ==== Lane D — platform token mis-typed as hostname (1) ======================
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-531','board_issue','MAC-530',
        'wave','v1_7_0_data_cleanup',
        'mig','0040_mac531_v170_data_cleanup_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'bucket','D_platform_token_not_hostname',
        'reason','android.asset is the Android WebView asset-scheme / AAPT platform token (file:///android_asset/), not a hostname; .asset is not a delegated TLD. Same treatment as mig-0037 bucket D (javax.xml.xmlconstants). Not a scanner identifier.',
        'source_cohort','wave_i_v1_4_0_cp29',
        'prior_confidence', confidence,
        'date','2026-07-28'))
WHERE id = 29254
  AND identifier_type = 'vendor_controlled_hostname'
  AND superseded_by IS NULL;

-- ==== Lane E — dotless bare brand token (1) ==================================
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-531','board_issue','MAC-530',
        'wave','v1_7_0_data_cleanup',
        'mig','0040_mac531_v170_data_cleanup_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'bucket','E_dotless_bare_token',
        'reason','Bare brand token with no dot, typed as a hostname. Its only cite is a bioinformatics research-software JSON (wisenet.biotools.json) for an unrelated homonym tool, so the row is invalid twice over: not a hostname, and a homonym-collision cite. The sibling product_family_codename row (id 35807, real Hanwha Wisenet family) is deliberately NOT touched. Not a scanner identifier.',
        'source_cohort','mac232_v1_5_0_stage1_deep_github',
        'prior_confidence', confidence,
        'date','2026-07-28'))
WHERE id = 35803
  AND identifier_type = 'vendor_controlled_hostname'
  AND superseded_by IS NULL;

-- ==== Lane F — RFC-6761 special-use loopback (1 network_endpoint) ============
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-531','board_issue','MAC-530',
        'wave','v1_7_0_data_cleanup',
        'mig','0040_mac531_v170_data_cleanup_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'bucket','F_special_use_loopback',
        'reason','RFC-6761 special-use loopback name (localhost:54664). The cite is the DEFAULT fallback URL in a third-party SDR crate, not a vendor-controlled endpoint. A scanner cannot detect a remote device via loopback and every host matches it — a pure false-positive magnet. Not a scanner identifier.',
        'source_cohort','wave_k_20260524_cohort5',
        'prior_confidence', confidence,
        'date','2026-07-28'))
WHERE id = 38594
  AND identifier_type = 'network_endpoint'
  AND superseded_by IS NULL;

-- ==== Lane G — inert / unresolvable TLD (1 network_endpoint) =================
UPDATE identifiers
SET superseded_by = id,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-531','board_issue','MAC-530',
        'wave','v1_7_0_data_cleanup',
        'mig','0040_mac531_v170_data_cleanup_supersession',
        'mechanism','cp32_sec9_withdrawn_without_successor_self_loop',
        'bucket','G_inert_unresolvable_tld',
        'reason','peticaonline.comv terminates in .comv, which is not a delegated TLD, so the value can never resolve and can never match: the row is INERT. Flagged for review by MAC-511 and left pending; this pass is that review. NOTE the upstream cite (mvt-project intellexa_predator/domains.txt) publishes this exact string, so the withdrawal rests on inertness, not on extraction corruption — this is the one row in mig-0040 the board may prefer to retain on cite-faithfulness grounds. Reversal is a single UPDATE.',
        'source_cohort','wave_k_20260524_cohort2',
        'prior_confidence', confidence,
        'date','2026-07-28'))
WHERE id = 39378
  AND identifier_type = 'network_endpoint'
  AND superseded_by IS NULL;

-- ==== Lane H — duplicate in non-canonical form, WITH successor (1) ===========
-- CP32 §9 tri-semantic: this withdrawal HAS a surviving twin, so superseded_by
-- points at that successor (22842) rather than self-looping.
UPDATE identifiers
SET superseded_by = 22842,
    confidence = 0,
    notes = json_set(notes, '$.fp_supersession', json_object(
        'audit_issue','MAC-531','board_issue','MAC-530',
        'wave','v1_7_0_data_cleanup',
        'mig','0040_mac531_v170_data_cleanup_supersession',
        'mechanism','cp32_sec9_withdrawn_with_successor',
        'successor_id',22842,
        'bucket','H_duplicate_noncanonical',
        'reason','0x4C is the same BLE SIG company id as the surviving row 22842 (0x004C) — both cited to the same tagfinder.py file (lines 396 and 102) — but written with 2 hex digits instead of 4. 709 of 715 active ble_company_id rows use the 4-hex-digit form. ble_company_id MAPs into the Lynceus feed as ble_manufacturer_id, so this malformed duplicate emits a feed pattern no consumer can match. Withdrawn to its canonical twin.',
        'source_cohort','tagfinder_py',
        'prior_confidence', confidence,
        'date','2026-07-28'))
WHERE id = 22841
  AND identifier_type = 'ble_company_id'
  AND identifier = '0x4C'
  AND superseded_by IS NULL;

-- ==== Lane I — in-place case normalization (1 fcc_grantee_code) ==============
-- NOT a withdrawal. The cite itself (https://fccid.io/2A2V6) proves the
-- canonical uppercase form; this is the only lowercase value among 218 active
-- fcc_grantee_code rows, and it has no twin, so withdrawing it would destroy a
-- real Flipper Devices grantee code. fcc_grantee_code is export-DROPPED, so the
-- feed delta is zero. The board may strike this lane without affecting A-H.
UPDATE identifiers
SET identifier = '2A2V6',
    notes = json_set(notes, '$.dq_normalization', json_object(
        'audit_issue','MAC-531','board_issue','MAC-530',
        'wave','v1_7_0_data_cleanup',
        'mig','0040_mac531_v170_data_cleanup_supersession',
        'kind','case_normalization',
        'prior_value','2a2v6',
        'reason','Only lowercase value among 218 active fcc_grantee_code rows; FCC EAS grantee codes are uppercase and the row own cite (https://fccid.io/2A2V6) carries the canonical form. Corrected in place rather than withdrawn — no twin exists, so a withdrawal would destroy a real identifier. Export-dropped type: zero feed delta.',
        'date','2026-07-28'))
WHERE id = 39541
  AND identifier_type = 'fcc_grantee_code'
  AND identifier = '2a2v6'
  AND superseded_by IS NULL;

-- ---- strict post-condition guard ---------------------------------------
-- (1) exactly 15 self-loop withdrawals, (2) lane H points at its successor,
-- (3) lane I holds the corrected value, (4) the successor 22842 is untouched,
-- (5) notes stayed valid JSON across the whole mutation scope.
-- Any miss aborts the whole transaction.
CREATE TEMP TABLE _mig0040_post (ok INTEGER CHECK (ok = 1));
INSERT INTO _mig0040_post(ok) SELECT CASE WHEN (
  (SELECT COUNT(*) FROM identifiers
    WHERE id IN (26975,26987,27237,29254,29475,29476,29598,29666,29684,
                 34582,35293,35295,35803,38594,39378)
      AND superseded_by = id AND confidence = 0) = 15
  AND (SELECT COUNT(*) FROM identifiers
        WHERE id = 22841 AND superseded_by = 22842 AND confidence = 0) = 1
  AND (SELECT COUNT(*) FROM identifiers
        WHERE id = 39541 AND identifier = '2A2V6' AND superseded_by IS NULL) = 1
  AND (SELECT COUNT(*) FROM identifiers
        WHERE id = 22842 AND identifier = '0x004C' AND superseded_by IS NULL
          AND confidence = 65) = 1
  AND (SELECT COUNT(*) FROM identifiers
        WHERE id IN (22841,26975,26987,27237,29254,29475,29476,29598,29666,29684,
                     34582,35293,35295,35803,38594,39378,39541)
          AND json_valid(notes) = 0) = 0
) THEN 1 ELSE 0 END;

DROP TABLE _mig0040_pre;
DROP TABLE _mig0040_post;

COMMIT;

-- Post-apply expected state:
--   16 rows withdrawn (15 self-loop + 1 to successor 22842), confidence = 0 —
--   all dropped from the canonical active set (`WHERE superseded_by IS NULL`).
--   Active identifiers 43,132 -> 43,116.
--   Per-type active delta:
--     vendor_controlled_hostname  -13
--     network_endpoint             -2
--     ble_company_id               -1
--   Lynceus standard feed -1 pattern (id 22841 only); high-confidence feed
--   unchanged. 1 row normalized in place (39541, export-dropped type).
--   No schema change (schema_version stays 33). No other row touched. All 16
--   rows + cites + prior_confidence retained in notes.$.fp_supersession.
