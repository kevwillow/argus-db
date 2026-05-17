-- ============================================================================
-- Migration: 0021_procurement_vendor_canonical_normalized
-- Purpose:   Add `vendor_canonical_normalized TEXT NOT NULL DEFAULT ''` column
--            on `procurement_records` with a supporting index, materializing
--            the deterministic alias-collapse key used by cross-validation
--            against `manufacturers.canonical_name` / `manufacturers.aliases`.
--            Pre-computing the join key beats per-query alias-aware JOIN at
--            43,483-row scale (CEO Path B ruling per CP23).
-- Surfaced:  ~/argus-internal/new data 5.16/schema_contract_patch_cycle3.md
--            §1 finding #4 (2026-05-16 US-domestic pivot mega-session). CEO
--            ruling at MAC-169 dispatch 2026-05-17: pre-compute as a column
--            rather than a materialized view, for query-plan-friendliness
--            and forward-compat with future INSERT paths.
-- Authority: CEO MAC-169 dispatch (CP23 coordinated amendment).
-- Bible:     §11 #11 — schema changes are CEO-only ratification post-board.
--            CP23 BIBLE_AMENDMENTS entry is the §-text + amendment-log pairing
--            for this migration in the coordinated commit set.
-- Pattern:   ALTER TABLE ADD COLUMN (single-file additive change; not a table
--            rebuild). NOT NULL DEFAULT '' satisfies SQLite's nullable-column
--            promotion semantics for existing rows. Index added immediately
--            for cross-validation query coverage.
-- Risk:      Low. Pure additive column; existing rows default to '' until
--            the companion Python backfill (db/backfill_0021.py) writes the
--            normalized values. After backfill, all 43,483 rows carry a
--            non-empty normalized key (subject to upstream USAspending blanks,
--            spot-checked at zero in the live DB at CP23 authoring time).
-- Backfill:  Run as a separate Python step immediately after migration
--            applies; see `db/backfill_0021.py` for the deterministic
--            normalization implementation. The normalization algorithm is
--            also documented in DATA_DICTIONARY.md §-procurement_records.
-- ============================================================================
--
-- Migration-slot allocation chain of record:
--   0001-0019  see 0019 / 0020 headers for the full chain
--   0020 = source_type enum extension — CP23 cycle-3 §1 finding #2
--   0021 = procurement_records.vendor_canonical_normalized — CP23 cycle-3 §1
--          finding #4 (this migration; additive column + index)
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Normalization algorithm (apply in order; document in DATA_DICTIONARY)
-- ─────────────────────────────────────────────────────────────────────────────
-- Input:  vendor_canonical_name (upstream USAspending verbatim recipient name)
-- Output: vendor_canonical_normalized (alias-collapse join key)
--
-- 1. LOWER()
-- 2. Strip ALL punctuation (chars in: . , ; : ' " ( ) [ ] { } / \ ` ~ ! @ # $
--    % ^ & * + = | < > ?)
-- 3. Collapse runs of whitespace → single space
-- 4. Strip leading/trailing whitespace
-- 5. Strip trailing whole-word suffix tokens (matched case-insensitively after
--    step 1, possibly with a preceding comma already stripped at step 2;
--    apply repeatedly until no terminal suffix matches):
--      inc, incorporated, corp, corporation, llc, l l c, ltd, limited, plc,
--      co, company, lp, llp, gmbh, ag, sa, pty, bv
-- 6. Re-strip whitespace
-- 7. If empty result, store '' (NOT NULL with default '')
--
-- Example: "AXON ENTERPRISE, INC." → "axon enterprise"
-- Example: "BERLA Corporation"      → "berla"
-- Example: "L 3 HARRIS TECHNOLOGIES INC" → "l 3 harris technologies"
--
-- ─────────────────────────────────────────────────────────────────────────────
-- Bible §11 hard-rule discipline
-- ─────────────────────────────────────────────────────────────────────────────
-- §11 #1  no fabrication — the normalized column is a deterministic
--   derivation of upstream verbatim values. No new identifier values minted;
--   no source attributions altered.
-- §11 #7  no main-table promotion without provenance — schema-only column
--   addition; vendor_canonical_normalized is a cross-validation join key
--   only. The verbatim `vendor_canonical_name` remains the upstream
--   provenance anchor.
-- §11 #8  no confidence drift — no confidence-column writes. The new column
--   informs cross-validation match candidates; promotion-band logic still
--   binds on §8.2 source_type tiers.
-- §11 #11 amendment-log discipline — this migration is the schema-sibling
--   to CP23 BIBLE_AMENDMENTS.md entry (coordinated commit).
--
-- ─────────────────────────────────────────────────────────────────────────────

PRAGMA foreign_keys = ON;

-- Add the normalized join-key column. NOT NULL DEFAULT '' satisfies SQLite's
-- promotion semantics for existing 43,483 rows; backfill runs as a separate
-- Python step (db/backfill_0021.py) immediately after this migration applies.
ALTER TABLE procurement_records
    ADD COLUMN vendor_canonical_normalized TEXT NOT NULL DEFAULT '';

-- Cross-validation queries against the column carry through this index
-- (joins to manufacturers.canonical_name on a normalized form, equality
-- lookups against pre-computed keys, etc.).
CREATE INDEX IF NOT EXISTS idx_procurement_records_vendor_canonical_normalized
    ON procurement_records (vendor_canonical_normalized);

INSERT OR IGNORE INTO schema_version (version, name) VALUES
    (21, '0021_procurement_vendor_canonical_normalized');

-- ─────────────────────────────────────────────────────────────────────────────
-- Cross-references
-- ─────────────────────────────────────────────────────────────────────────────
-- - BIBLE_AMENDMENTS.md CP23 entry (coordinated commit — schema-sibling
--   reference; CP23 documents the vendor matching discipline in
--   PROJECT_BIBLE.md §-text)
-- - ~/argus-internal/new data 5.16/schema_contract_patch_cycle3.md §1 finding
--   #4 (cycle-3 source-of-truth for the verbatim-not-canonical drift and
--   the pre-compute-vs-per-query-join decision)
-- - DATA_DICTIONARY.md §-procurement_records (normalization algorithm prose
--   reference for downstream-consumer audit)
-- - db/backfill_0021.py (companion Python backfill — deterministic
--   normalization implementation)
-- - db/migrations/0006_raw_observations_source_row_key.sql (precedent for
--   ALTER TABLE ADD COLUMN + index in a single .sql migration)
