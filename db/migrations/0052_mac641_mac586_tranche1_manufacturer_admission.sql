-- Migration: 0052_mac641_mac586_tranche1_manufacturer_admission.sql
--
-- MAC-641 admits MAC-586 tranche 1: the atlas_per_row_citation support class.
-- CEO ratification: operator_review/MAC-586/ceo_verify/RATIFICATION.md, comment
-- e020abb1-a704-4898-b39a-a0aa914adb19, at HEAD 91a8af0.
--
-- GENERATED from operator_review/MAC-586/proposed_manufacturers.tsv by
-- operator_review/MAC-641/gen_migration.py. Do not hand-edit; re-generate.
-- `gen_migration.py --check` byte-compares this file against a fresh generation.
--
-- SCOPE, as corrected by MAC-641's P1 variant sweep:
--   23 atlas_per_row_citation proposals
--  - 3 adjudicated DUPLICATE of an existing canonical  (PenLink, Coban, PIPS)
--  = 20 canonicals MINTED
--  + 3 alias routings onto existing ids 290 / 217 / 214
--
-- The CEO ratification named PenLink alone (correction 1, found at difflib ratio
-- 0.933). Coban and PIPS are the SAME defect shape and were invisible to every
-- gate run before this one: difflib normalises by combined length, so a short
-- needle inside a longer incumbent name collapses far below the mandated 0.82
-- threshold -- Coban ~ Coban Technologies scores 0.435, PIPS ~ PIPS Technology
-- scores 0.421. p1_variant_sweep.py ARM B (whole-word token containment) is what
-- surfaces them. Minting either would have created a second canonical for a firm
-- the registry already carries, which is the net regression correction 1 forbids.
--
-- Recovery is UNCHANGED by the correction: 28 entities / 962 rows, 21.4% of the
-- 4,488-row gap. An alias routing resolves a gap row exactly as a mint does, which
-- is why the ratification measures recovery by set union against the gap rather
-- than by sum(observation_rows). Do not quote 65% or 77.7%; those are all-43
-- figures. The 20 DeFlock-feed-only proposals are held for MAC-591.
--
-- 6 data brokers land with primary_category NULL (LexisNexis, TransUnion, Thomson
-- Reuters, Skopenow, Chorus Intelligence, Peregrine). Verified on the DDL at write
-- time, not on the §2.1 convention: primary_category carries NO CHECK, the column
-- comment reads 'NULL when multi-purpose', and 96 of 240 live rows are NULL. No
-- data-broker category is minted; that was declined as a Bible CP and a one-way door.
--
-- DDL: none. schema_version remains 35 and is asserted, not bumped.
--
-- notes is NOT touched on the three routing targets. id=290 (Pen-Link) carries
-- prose notes scoring json_valid=0, so json_set on it raises (CP39 defect). 34 of
-- 240 live rows are json_valid=0; the post-condition asserts that population is
-- unchanged, proving the write degraded no JSON.

BEGIN IMMEDIATE;

-- ============================ PRECONDITIONS =============================
-- CORRECTED (MAC-641 apply, CEO ratification 1f5d4ded): the previous text here
-- read "CHECK (ok = 1) aborts the whole transaction on any 0." That is FALSE and
-- BIBLE_AMENDMENTS.md:6072 (MAC-535, Finding 2) already says so: the sqlite3 CLI
-- does not auto-rollback on a CHECK violation without -bail. The violation aborts
-- the offending STATEMENT, not the script, and the runner walks on to the writes.
--
-- What actually gates every write below is the SECOND arm, not this CHECK: each
-- write carries `AND (SELECT COUNT(*) FROM _mig0052_pre) = 8`. A failed guard
-- leaves this temp table short of 8 rows, so every write matches zero rows and the
-- migration degrades to a clean no-op. That arm is apply-method-independent -- it
-- holds under the bare CLI *and* under conn.executescript(), whereas `.bail on` is
-- a dot-command that breaks the python path. Do not copy this file's shape without
-- copying the count=8 arm; the CHECK alone inherits the mig-0041 half-apply defect.
CREATE TEMP TABLE _mig0052_pre (ok INTEGER CHECK (ok = 1));

-- schema_version is exactly 35 (no DDL migration has landed since)
INSERT INTO _mig0052_pre(ok) SELECT CASE WHEN
    (SELECT MAX(version) FROM schema_version) = 35
THEN 1 ELSE 0 END;

-- this migration has not already been applied
--
-- VACUOUS BY CONSTRUCTION -- kept only to hold the slot, never to be relied on.
-- This file is data-only and deliberately does NOT bump schema_version (see the
-- header and the final post-condition, both of which assert it stays 35). Nothing
-- in the fleet ever writes the name below, so this COUNT is 0 on a virgin DB and 0
-- on an already-applied DB alike: the guard cannot fire. It is NOT what makes this
-- migration re-apply-safe. Verified at apply time: mig-0048 and mig-0049 carry the
-- same shape and the same vacuity -- schema_version tops out at 35 (= 0045), the
-- last migration that self-recorded via `INSERT INTO schema_version (version, name)`.
--
-- Re-apply is actually caught by the five STATE preconditions below -- the 240-row
-- count, the 20-name non-existence check, and the three alias-routing byte checks.
-- Measured on a scratch copy: a second apply fails exactly those 5 of 8 and writes
-- nothing. Consequence to carry forward (MAC-661): after this applies there is no
-- DB-side record that 0052 ran; "applied" is provable only from the data state.
INSERT INTO _mig0052_pre(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM schema_version
      WHERE name = '0052_mac641_mac586_tranche1_manufacturer_admission') = 0
THEN 1 ELSE 0 END;

-- manufacturers is at the 240-row state this file was generated against
INSERT INTO _mig0052_pre(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM manufacturers) = 240
THEN 1 ELSE 0 END;

-- the json_valid=0 notes population is the known 34 (CP39 residue)
INSERT INTO _mig0052_pre(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM manufacturers
      WHERE notes IS NOT NULL AND TRIM(notes) <> '' AND json_valid(notes) = 0) = 34
THEN 1 ELSE 0 END;

-- none of the 20 minted names already resolves as a canonical, case-insensitively.
-- The MAC-586 admission gate was `v in existing` -- exact-case -- so this widening
-- is load-bearing, not ceremonial.
INSERT INTO _mig0052_pre(ok) SELECT CASE WHEN (
    SELECT COUNT(*) FROM manufacturers WHERE LOWER(canonical_name) IN (
        'crimewatch',
        'fusus',
        'lexisnexis',
        'ibm',
        'coreforce',
        'geolitica',
        'transunion',
        'thomson reuters',
        'lenslock',
        'panasonic',
        'pro-vision',
        'vievu',
        'skopenow',
        'verra mobility',
        'vintra',
        'chorus intelligence',
        'peregrine',
        'physical sciences',
        'safety vision',
        'kustom signals'
    )
) = 0 THEN 1 ELSE 0 END;

-- each alias-routing target exists under exactly the canonical_name adjudicated,
-- and carries exactly the aliases blob this file was generated against. A rename
-- or a concurrent alias edit retargets the routing silently otherwise.
INSERT INTO _mig0052_pre(ok) SELECT CASE WHEN (
    SELECT COUNT(*) FROM manufacturers
     WHERE id = 217 AND canonical_name = 'Coban Technologies'
       AND aliases IS 'Coban Tech'
) = 1 THEN 1 ELSE 0 END;   -- Coban routes onto id=217
INSERT INTO _mig0052_pre(ok) SELECT CASE WHEN (
    SELECT COUNT(*) FROM manufacturers
     WHERE id = 214 AND canonical_name = 'PIPS Technology'
       AND aliases IS 'PIPS Technology / Neology, Neology, AutoVu (legacy), 3M (legacy), Neology / PIPS'
) = 1 THEN 1 ELSE 0 END;   -- PIPS routes onto id=214
INSERT INTO _mig0052_pre(ok) SELECT CASE WHEN (
    SELECT COUNT(*) FROM manufacturers
     WHERE id = 290 AND canonical_name = 'Pen-Link'
       AND aliases IS NULL
) = 1 THEN 1 ELSE 0 END;   -- PenLink routes onto id=290

-- ======================== PRECONDITION GATE =============================
-- Every write below is gated on all 8 preconditions having
-- landed a row. CHECK (ok = 1) aborts one statement; it does NOT abort the run
-- unless sqlite3 was invoked with -bail. Verified on a copy of the live DB: with
-- id=217's aliases tampered so the routing precondition fails, bare
-- `sqlite3 db < mig.sql` prints the CHECK failure and then commits all 20 INSERTs,
-- taking manufacturers 240 -> 260 with a precondition provably violated. The gate
-- below turns that half-apply into a clean no-op under any runner.
--
-- Apply with:  sqlite3 -bail db/argus.db < db/migrations/0052_....sql

-- ============================== MINT (20) ================================
INSERT INTO manufacturers (canonical_name, aliases, primary_category, source_url, notes)
SELECT canonical_name, aliases, primary_category, source_url, notes FROM (
  SELECT 'CRIMEWATCH' AS canonical_name, NULL AS aliases, 'cctv_camera' AS primary_category,
         'https://crimewatch.net/us/az/gila/payson-pd/281034/webforms/camera-registry' AS source_url,
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 173, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}' AS notes
  UNION ALL SELECT 'Fusus', NULL, 'cctv_camera',
         'https://cityofsangabriel.fususregistry.com',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 156, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'LexisNexis', 'LexisNexis Risk Solutions', NULL,
         'https://www.howardcountymd.gov/sites/default/files/2023-04/Current%20Contracts%2004.10.2023.pdf',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 136, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'IBM', NULL, 'network_surveillance',
         'https://www.brennancenter.org/sites/default/files/2019-10/2019_10_LNS_%28NYPD%29Surveillance_Final.pdf',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 98, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'Coreforce', NULL, 'body_cam',
         'https://www.prnewswire.com/news-releases/georgias-dekalb-county-police-department-chooses-bodyworn-as-its-exclusive-body-camera-solution-300301433.html',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 76, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'Geolitica', 'PredPol', 'network_surveillance',
         'https://www.MuckRock.com/foi/ocala-10232/predpol-documents-ocala-ocala-police-department-ocala-fl-34471-63108/#comms',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 52, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'TransUnion', NULL, NULL,
         'https://www.elizabethton.org/news_detail_T2_R239.php',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 24, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'Thomson Reuters', NULL, NULL,
         'https://www.canton-mi.org/AgendaCenter/ViewFile/Minutes/_09272022-756',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 23, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'LensLock', 'Lenslock', 'body_cam',
         'https://fox40.com/news/local-news/roseville-city-council-unanimously-approves-body-cameras-for-police-department/',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 13, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'Panasonic', NULL, 'body_cam',
         'https://www.county.org/TAC/media/TACMedia/County%20Magazine/Past%20Issues/2016/CountyMag_JanFeb2016.pdf',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 12, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'Pro-Vision', 'Pro-vision, ProVision, Provision', 'body_cam',
         'https://www.documentcloud.org/documents/6953136-Oklahoma-DAC-14-JAG-LLE-Congressional-Award.html',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 11, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'VieVu', 'VIEVU, Vievu, Vievue', 'body_cam',
         'https://www.eastbaytimes.com/2018/05/30/ebt-l-bodycams-0530/',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 11, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'Skopenow', NULL, NULL,
         'https://www.law360.com/articles/1450472/lapd-case-sheds-light-on-agencies-social-media-monitoring',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 7, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'Verra Mobility', NULL, 'alpr',
         'https://bbpd.org/boynton-beach-police-enhance-license-plate-recognition-program/',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 6, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'Vintra', NULL, 'cctv_camera',
         'https://www.montclairnjusa.org/UserFiles/Servers/Server_5276204/File/Government/Mayor%20&%20Township%20Council/2019%20Meeting%20Agendas/03-19-19/R-19-064.pdf',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 6, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'Chorus Intelligence', 'Chorus Intellegence', NULL,
         'https://chorusintel.com/ccso-chorus-partnership/',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 5, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'Peregrine', NULL, NULL,
         'https://www.peregrine.io/customer-stories/seconds-save-lives-the-amarillo-police-department-s-real-time-revolution',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 5, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'Physical Sciences', NULL, 'drone',
         'https://drydenwire.com/news/highspeed-chase-in-barron-county-results-in-arrest/',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 5, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'Safety Vision', NULL, 'body_cam',
         'https://www.oswego.edu/news/story/university-police-issues-body-worn-cameras-patrol-officers',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 5, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
  UNION ALL SELECT 'Kustom Signals', NULL, 'body_cam',
         'https://www.documentcloud.org/documents/24549373-srt-bwc-micro-grantee-award-2023',
         '{"admission": {"issue": "MAC-641", "observation_rows_at_proposal": 2, "proposal": "MAC-586", "ratification": "operator_review/MAC-586/ceo_verify/RATIFICATION.md", "support_class": "atlas_per_row_citation", "tranche": 1}, "description": "MAC-586 tranche-1 admission (atlas_per_row_citation)."}'
) WHERE (SELECT COUNT(*) FROM _mig0052_pre) = 8;

-- ====================== ALIAS ROUTINGS (3 targets) =======================
-- Duplicates of an existing canonical. Routed as aliases; no canonical minted.
-- New values are written as literals rather than concatenated, so the resulting
-- bytes are reviewable here and cannot depend on the incumbent value at run time.
-- Coban Technologies (id=217): += 'Coban'
UPDATE manufacturers SET aliases = 'Coban Tech, Coban'
 WHERE id = 217 AND canonical_name = 'Coban Technologies'
   AND aliases IS 'Coban Tech'
   AND (SELECT COUNT(*) FROM _mig0052_pre) = 8;
-- PIPS Technology (id=214): += 'PIPS'
UPDATE manufacturers SET aliases = 'PIPS Technology / Neology, Neology, AutoVu (legacy), 3M (legacy), Neology / PIPS, PIPS'
 WHERE id = 214 AND canonical_name = 'PIPS Technology'
   AND aliases IS 'PIPS Technology / Neology, Neology, AutoVu (legacy), 3M (legacy), Neology / PIPS'
   AND (SELECT COUNT(*) FROM _mig0052_pre) = 8;
-- Pen-Link (id=290): += 'PenLink', 'Penlink'
UPDATE manufacturers SET aliases = 'PenLink, Penlink'
 WHERE id = 290 AND canonical_name = 'Pen-Link'
   AND aliases IS NULL
   AND (SELECT COUNT(*) FROM _mig0052_pre) = 8;

-- ============================ POST-CONDITIONS ============================
-- What SQL can assert EXACTLY. The lens-faithful set-membership test (P3) needs
-- db.alias_parser.split_aliases, which SQL cannot replicate without re-committing
-- the MAC-569 delimiter defect; it runs in operator_review/MAC-641/p3_membership.py
-- against the migrated DB and is the authoritative P3 gate.
CREATE TEMP TABLE _mig0052_post (ok INTEGER CHECK (ok = 1));

-- all 8 preconditions landed a row, so the write gate opened.
-- Asserted explicitly: if it did not open, every write above no-opped and the
-- remaining post-conditions would report an unchanged DB as a failure without
-- ever naming the cause.
INSERT INTO _mig0052_post(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM _mig0052_pre) = 8
THEN 1 ELSE 0 END;

-- exactly 20 rows added: 240 -> 260
INSERT INTO _mig0052_post(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM manufacturers) = 260
THEN 1 ELSE 0 END;

-- every minted name is present exactly once (set membership, not a count)
INSERT INTO _mig0052_post(ok) SELECT CASE WHEN (
    SELECT COUNT(*) FROM manufacturers WHERE canonical_name IN (
        'CRIMEWATCH',
        'Fusus',
        'LexisNexis',
        'IBM',
        'Coreforce',
        'Geolitica',
        'TransUnion',
        'Thomson Reuters',
        'LensLock',
        'Panasonic',
        'Pro-Vision',
        'VieVu',
        'Skopenow',
        'Verra Mobility',
        'Vintra',
        'Chorus Intelligence',
        'Peregrine',
        'Physical Sciences',
        'Safety Vision',
        'Kustom Signals'
    )
) = 20 THEN 1 ELSE 0 END;

-- each routing target carries exactly the expected aliases bytes
INSERT INTO _mig0052_post(ok) SELECT CASE WHEN (
    SELECT COUNT(*) FROM manufacturers
     WHERE id = 217 AND aliases = 'Coban Tech, Coban'
) = 1 THEN 1 ELSE 0 END;   -- Coban Technologies
INSERT INTO _mig0052_post(ok) SELECT CASE WHEN (
    SELECT COUNT(*) FROM manufacturers
     WHERE id = 214 AND aliases = 'PIPS Technology / Neology, Neology, AutoVu (legacy), 3M (legacy), Neology / PIPS, PIPS'
) = 1 THEN 1 ELSE 0 END;   -- PIPS Technology
INSERT INTO _mig0052_post(ok) SELECT CASE WHEN (
    SELECT COUNT(*) FROM manufacturers
     WHERE id = 290 AND aliases = 'PenLink, Penlink'
) = 1 THEN 1 ELSE 0 END;   -- Pen-Link

-- no canonical was minted for any adjudicated duplicate
INSERT INTO _mig0052_post(ok) SELECT CASE WHEN (
    SELECT COUNT(*) FROM manufacturers WHERE LOWER(canonical_name) IN (
        'coban',
        'pips',
        'penlink'
    )
) = 0 THEN 1 ELSE 0 END;

-- the write degraded no JSON: the json_valid=0 population is unchanged
INSERT INTO _mig0052_post(ok) SELECT CASE WHEN
    (SELECT COUNT(*) FROM manufacturers
      WHERE notes IS NOT NULL AND TRIM(notes) <> '' AND json_valid(notes) = 0) = 34
THEN 1 ELSE 0 END;

-- every minted row carries valid JSON notes
INSERT INTO _mig0052_post(ok) SELECT CASE WHEN (
    SELECT COUNT(*) FROM manufacturers
     WHERE canonical_name IN (
        'CRIMEWATCH',
        'Fusus',
        'LexisNexis',
        'IBM',
        'Coreforce',
        'Geolitica',
        'TransUnion',
        'Thomson Reuters',
        'LensLock',
        'Panasonic',
        'Pro-Vision',
        'VieVu',
        'Skopenow',
        'Verra Mobility',
        'Vintra',
        'Chorus Intelligence',
        'Peregrine',
        'Physical Sciences',
        'Safety Vision',
        'Kustom Signals'
     ) AND json_valid(notes) = 1
) = 20 THEN 1 ELSE 0 END;

-- no DDL: schema_version is untouched
INSERT INTO _mig0052_post(ok) SELECT CASE WHEN
    (SELECT MAX(version) FROM schema_version) = 35
THEN 1 ELSE 0 END;

DROP TABLE _mig0052_pre;
DROP TABLE _mig0052_post;

COMMIT;
