-- Migration: 0045_mac580_alias_suffix_completion.sql
-- MAC-580 completes MAC-569 by merging every standalone corporate-suffix token
-- with its immediate predecessor. Cross-vendor pairs remain separate because
-- neither member is a pure corporate suffix. Applied by
-- scripts/mac580_alias_suffix_completion_apply.py after its independent check.

BEGIN IMMEDIATE;

CREATE TEMP TABLE _mig0045_pre (ok INTEGER CHECK (ok = 1));

INSERT INTO _mig0045_pre(ok)
SELECT CASE WHEN (SELECT MAX(version) FROM schema_version) = 34 THEN 1 ELSE 0 END;

INSERT INTO _mig0045_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM schema_version
    WHERE name = '0045_mac580_alias_suffix_completion'
) = 0 THEN 1 ELSE 0 END;

INSERT INTO _mig0045_pre(ok)
SELECT CASE WHEN (
    SELECT COUNT(*) FROM pragma_table_info('manufacturers')
    WHERE name IN ('id', 'canonical_name', 'aliases')
) = 3 THEN 1 ELSE 0 END;

INSERT INTO schema_version (version, name)
VALUES (35, '0045_mac580_alias_suffix_completion');

COMMIT;
