-- ============================================================================
-- Script:    0029_cp36_j5_proxy_relabel.sql
-- Sibling of: 0029_cp36_identifiers_source_type_enum_parity.sql
-- Purpose:   Post-CP36-enum-extension UPDATE: relabel the 116 J-5 CourtListener
--            rows admitted at MAC-250 Phase H with `source_type='foia'` as
--            CPN-A band-bucket proxy → canonical `source_type='judicial_filing'`
--            now admissible per mig-0029 enum extension.
-- Authority: MAC-251 dispatch — verbatim UPDATE shape from issue §Scope/Post-
--            migration UPDATE relabel. CP-slot ratified as CP36 at MAC-251
--            wake comment cb228e69 (option (b)).
-- Idempotency: WHERE clause is shape-stable. Re-running against an already-
--            relabeled DB matches 0 rows (source_type is no longer 'foia' on
--            those rows). Safe to re-run.
--
-- Selection rationale:
--   - The MAC-251 issue's example SQL referenced `source_id=48`, but the live
--     `identifiers` schema has no `source_id` column (verified via PRAGMA
--     table_info; rel is via `source_url`). The 116 J-5 rows are uniquely
--     identifiable by:
--       source_url LIKE 'https://www.courtlistener.com/docket/%'  (13 distinct
--                                                                  docket URLs)
--       AND source_type = 'foia'
--       AND notes LIKE '%"wave": "j_widenet"%'                    (confines to
--                                                                  MAC-250
--                                                                  Phase H)
--     Pre-migration count verified: 116 rows match exactly.
--
-- §11 envelope (re-asserted from mig-0029 header):
--   #1 No fabrication — relabel restores canonical truth (sources(sid=48)
--      already records source_type='judicial_filing').
--   #8 No confidence drift — confidence column not in SET clause; band-equiv
--      foia ↔ judicial_filing both in §8.2 65-85.
--   #17 Carve-out audit invariant — `cpn_a_proxy_relabel` is a new
--      sentinel-key block under notes; existing notes JSON keys preserved
--      verbatim by `json_set`.
-- ============================================================================

BEGIN TRANSACTION;

UPDATE identifiers
SET source_type = 'judicial_filing',
    notes = json_set(
        notes,
        '$.cpn_a_proxy_relabel',
        json_object(
            'date', '2026-05-24',
            'from', 'foia',
            'to', 'judicial_filing',
            'cp_anchor', 'CP36',
            'mig', '0029_cp36_identifiers_source_type_enum_parity',
            'reason', 'CHECK enum gap resolved via mig-0029; canonical source_type now matches sources(sid=48).source_type=judicial_filing'
        )
    )
WHERE source_url LIKE 'https://www.courtlistener.com/docket/%'
  AND source_type = 'foia'
  AND notes LIKE '%"wave": "j_widenet"%';

COMMIT;

-- Post-relabel expected state:
--   - 116 rows updated; source_type='judicial_filing'; notes carries
--     cpn_a_proxy_relabel sentinel block + all prior keys intact.
--   - identifiers.confidence column untouched on relabeled rows.
--   - identifiers row counts unchanged (column UPDATE, not row delta).
