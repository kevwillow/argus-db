-- ============================================================================
-- Migration: 0043_mac569_alias_rfc4180_quote_normalize.sql
-- Status:    STAGED — data-only normalize for MAC-569.
--
-- Purpose:   Re-encode every row of ``manufacturers.aliases`` into the
--            canonical RFC-4180-lite form: alias values that contain a
--            comma are wrapped in double quotes; bare values are bare.
--            Pre-MAC-569 data stored comma-bearing values unquoted, which
--            produced phantom corporate-suffix tokens ("Ltd.", "Inc.",
--            "LLC", "Co.") when naive comma-split was applied by the 5+
--            consumers of the column. The MAC-535 defense-in-depth patch
--            in ``coverage_matrix._alias_tokens_for_vendor`` (Finding 1)
--            stopped the §6.2 corroboration inflation but left the
--            underlying data defect in place. This migration normalizes
--            the wire format so every consumer — not just §6.2 — sees
--            the structural meaning correctly.
--
-- Authority: operator_review/MAC-569/fix_proof.md + the canonical
--            ``db/alias_parser.recombine_and_quote_normalize`` pure
--            function (also imported by the apply script).
--
-- Mechanism: per-row recombine + quote-wrap via the apply script
--            ``scripts/mac569_alias_quote_normalize_apply.py``. The
--            transform is a 2-step pure function on the aliases blob:
--              1. RECOMBINE — walk the naive-split tokens; if a token is
--                 a corporate-suffix fragment (Ltd./Inc./LLC/...) AND
--                 its predecessor ends in a corporate-suffix word
--                 boundary, merge them with ", " join (this recovers
--                 the original comma-bearing alias value).
--              2. QUOTE-WRAP — for every resulting string that contains
--                 a comma, wrap it in double quotes (this brings the
--                 blob into the canonical RFC-4180-lite form).
--            The apply script writes each row's new aliases blob via
--            UPDATE then runs this SQL file for the version bump.
--
-- Re-apply safety: the apply script enforces pre-conditions inline
-- (zero rows already carry quoted aliases at apply time; schema_version
-- baseline = 33). The schema_version bump in this file is the durable
-- record; re-running on a partially-migrated DB will refuse to apply
-- the version bump (pre-condition (c) below) AND the apply script's
-- idempotency guard refuses to touch already-canonical rows (the
-- transform is idempotent on canonical input — verified at
-- ``tests/test_alias_parser.py::test_recombine_and_quote_normalize_is_idempotent_on_pre_quoted_input``).
--
-- Apply discipline: run from the repository root with
-- ``scripts/mac569_alias_quote_normalize_apply.py``. The sqlite3 CLI
-- alone cannot apply this migration — the per-row transform requires
-- the Python ``recombine_and_quote_normalize`` function. The apply
-- script sources this SQL file for the schema_version bump after the
-- data update succeeds.
--
-- schema_version: 33 → 34 (data-only; no DDL).
-- ============================================================================

BEGIN IMMEDIATE;

-- ---- Strict pre-condition guard (all-or-nothing) ---------------------------
-- Aborts the whole transaction unless the world is exactly as expected at
-- apply time. CHECK(ok=1) on the TEMP table → rolling back on any failure.

CREATE TEMP TABLE _mig0043_pre (
    ok INTEGER CHECK (ok = 1)
);

-- (a) schema_version baseline is 33 (no prior 0043 bump). The apply script
--     has already performed the per-row UPDATE before this file runs; the
--     baseline check is the durable re-apply safety net.
INSERT INTO _mig0043_pre(ok)
SELECT CASE WHEN (
    SELECT MAX(version) FROM schema_version
) = 33 THEN 1 ELSE 0 END;

-- (b) manufacturers table has the expected shape (canonical schema present).
INSERT INTO _mig0043_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM pragma_table_info('manufacturers')
     WHERE name IN ('canonical_name', 'aliases', 'parent_manufacturer_id',
                    'is_arm', 'query_default')
) = 5 THEN 1 ELSE 0 END;

-- (c) No prior 0043 schema_version entry exists (catch a previous partial
--     apply that bumped the version but somehow got re-invoked).
INSERT INTO _mig0043_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM schema_version WHERE name = '0043_mac569_alias_rfc4180_quote_normalize'
) = 0 THEN 1 ELSE 0 END;

-- (d) identifiers total is identical to active + superseded (tautology check;
--     this migration does not touch identifiers but the test catches schema
--     corruption that would silently permit a wrong-shape write).
INSERT INTO _mig0043_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM identifiers
) = (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL) +
       (SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NOT NULL)
THEN 1 ELSE 0 END;

-- (e) At least one manufacturer row exists with non-empty aliases (regression
--     catch — the migration is data-only and must touch at least one row,
--     otherwise the apply script's "0 rows modified" branch is a problem).
INSERT INTO _mig0043_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM manufacturers
     WHERE aliases IS NOT NULL AND aliases != ''
) > 0 THEN 1 ELSE 0 END;

-- ---- The schema_version bump (34) -----------------------------------------
-- The apply script writes each row's normalized aliases via UPDATE before
-- this statement runs. The version bump is the durable record that the
-- data has been normalized.
INSERT INTO schema_version (version, name)
SELECT 34, '0043_mac569_alias_rfc4180_quote_normalize'
 WHERE (SELECT MAX(version) FROM schema_version) = 33;

COMMIT;
