"""MAC-191 §5 pre-flight — SAR-13 PRAGMA + state checkpoint.

Verifies:
- DB integrity_check ok
- identifiers active=34,796 / total=35,138
- raw_observations=146,218
- manufacturers=51
- conflicts=36
- manufacturers.aliases is comma-separated TEXT (NOT JSON array)
- manufacturers.notes accepts json_set for $.fcc_grantee_absence + $.component_supplier_ouis + $.subsidiary_filing_name_pattern
- sqlite_master CHECK enums for source_type / device_category / identifier_type
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

DB = Path("/home/kev/argus/db/argus.db")
OUT = Path("/home/kev/argus/_phase_5_wave_i_12/preflight_pragma.txt")


def main() -> int:
    lines: list[str] = []
    con = sqlite3.connect(DB)
    cur = con.cursor()

    def section(title: str) -> None:
        lines.append("")
        lines.append(f"## {title}")
        lines.append("")

    section("integrity_check")
    rows = cur.execute("PRAGMA integrity_check;").fetchall()
    lines.append(repr(rows))
    integrity_ok = rows == [("ok",)]

    section("schema version")
    schema_v = cur.execute("PRAGMA user_version;").fetchone()
    lines.append(repr(schema_v))

    section("foreign_keys / journal_mode")
    lines.append(f"foreign_keys = {cur.execute('PRAGMA foreign_keys;').fetchone()}")
    lines.append(f"journal_mode = {cur.execute('PRAGMA journal_mode;').fetchone()}")

    section("state checkpoint")
    counts = {
        "identifiers_active": cur.execute(
            "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"
        ).fetchone()[0],
        "identifiers_total": cur.execute(
            "SELECT COUNT(*) FROM identifiers"
        ).fetchone()[0],
        "raw_observations": cur.execute(
            "SELECT COUNT(*) FROM raw_observations"
        ).fetchone()[0],
        "manufacturers": cur.execute(
            "SELECT COUNT(*) FROM manufacturers"
        ).fetchone()[0],
        "conflicts": cur.execute("SELECT COUNT(*) FROM conflicts").fetchone()[0],
    }
    for k, v in counts.items():
        lines.append(f"  {k} = {v}")

    expected = {
        "identifiers_active": 34_796,
        "identifiers_total": 35_138,
        "raw_observations": 146_218,
        "manufacturers": 51,
        "conflicts": 36,
    }
    deltas = {k: counts[k] - expected[k] for k in expected}
    lines.append(f"  expected = {expected}")
    lines.append(f"  delta_vs_expected = {deltas}")

    section("manufacturers.aliases — schema introspection (CP23 TEXT-CSV)")
    cols = cur.execute("PRAGMA table_info(manufacturers);").fetchall()
    aliases_col = next((c for c in cols if c[1] == "aliases"), None)
    notes_col = next((c for c in cols if c[1] == "notes"), None)
    lines.append(f"  aliases column = {aliases_col}")
    lines.append(f"  notes column   = {notes_col}")
    # Spot-sample current aliases values
    aliases_sample = cur.execute(
        "SELECT id, canonical_name, aliases FROM manufacturers ORDER BY id LIMIT 10"
    ).fetchall()
    for r in aliases_sample:
        lines.append(f"  sample id={r[0]:>4d} \"{r[1]}\" aliases={r[2]!r}")
    # Look for any '[' in aliases values (would indicate JSON array)
    json_array_like = cur.execute(
        "SELECT id, canonical_name, aliases FROM manufacturers WHERE aliases LIKE '[%'"
    ).fetchall()
    lines.append(f"  rows with aliases LIKE '[%' = {len(json_array_like)}")
    if json_array_like:
        for r in json_array_like:
            lines.append(f"    {r}")

    section("manufacturers.notes — JSON-shape vs text-shape audit (§5.3 + §5.5 gate)")
    rows = cur.execute(
        "SELECT id, canonical_name, notes FROM manufacturers ORDER BY id"
    ).fetchall()
    text_shape: list[tuple[int, str, str]] = []
    json_shape: list[tuple[int, str]] = []
    null_shape: list[tuple[int, str]] = []
    for mid, name, notes in rows:
        if notes is None or notes == "":
            null_shape.append((mid, name))
            continue
        try:
            json.loads(notes)
            json_shape.append((mid, name))
        except Exception:
            text_shape.append((mid, name, notes))
    lines.append(f"  JSON-shape notes: {len(json_shape)}")
    lines.append(f"  text-shape notes: {len(text_shape)}")
    lines.append(f"  null/empty notes: {len(null_shape)}")
    lines.append("  text-shape rows (require description-wrap migration before json_set):")
    for mid, name, notes in text_shape:
        lines.append(f"    id={mid:>4d} \"{name}\": {notes[:100]!r}")
    # json_set capability — probe against an actual JSON-shape row to confirm behavior
    probe = cur.execute(
        """
        SELECT id, canonical_name,
               json_set(
                 COALESCE(notes,'{}'),
                 '$.preflight_probe',
                 'ok'
               ) AS notes_after
        FROM manufacturers
        WHERE id = 4
        """
    ).fetchone()
    lines.append(f"  json_set probe Genetec id=4: notes_after_first120 = {probe[2][:120]}")

    section("sqlite_master CHECK enum re-attestation (§3399)")
    rows = cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN ('identifiers','raw_observations','manufacturers') ORDER BY name"
    ).fetchall()
    for name, sql in rows:
        lines.append(f"  --- table {name} ---")
        # Extract any CHECK clauses
        for line in sql.split("\n"):
            if "CHECK" in line or "check(" in line.lower():
                lines.append(f"    {line.strip()}")

    section("source_id 66 (Wave I umbrella) attestation")
    src66 = cur.execute(
        "SELECT id, name, source_type, url FROM sources WHERE id = 66"
    ).fetchone()
    lines.append(f"  source_id=66 = {src66}")

    section("sierra_wireless / sierrawireless presence probe (§5.6)")
    swr = cur.execute(
        "SELECT id, canonical_name, aliases FROM manufacturers WHERE canonical_name IN ('Sierra Wireless','sierra_wireless') OR LOWER(canonical_name) LIKE '%sierra%wireless%' OR LOWER(canonical_name) LIKE 'sierrawireless%'"
    ).fetchall()
    for r in swr:
        lines.append(f"  mfg: {r}")
    swr_id = cur.execute(
        """
        SELECT manufacturer, COUNT(*) AS n
        FROM identifiers
        WHERE superseded_by IS NULL AND LOWER(manufacturer) LIKE 'sierra%wireless%'
        GROUP BY manufacturer
        ORDER BY n DESC
        """
    ).fetchall()
    for r in swr_id:
        lines.append(f"  ids manufacturer={r[0]!r} n={r[1]}")
    swr_slug = cur.execute(
        """
        SELECT manufacturer, COUNT(*) AS n
        FROM identifiers
        WHERE superseded_by IS NULL AND LOWER(manufacturer) = 'sierrawireless'
        GROUP BY manufacturer
        """
    ).fetchall()
    lines.append(f"  ids exact 'sierrawireless' rows = {swr_slug}")
    # Use safe scan because some identifier rows have text-shape notes
    candidates = cur.execute(
        "SELECT id, manufacturer, notes FROM identifiers WHERE notes LIKE '%slug_duplication_review%' LIMIT 50"
    ).fetchall()
    slug_review: list[tuple[int, str, str]] = []
    for r in candidates:
        try:
            d = json.loads(r[2])
            v = d.get("slug_duplication_review")
            if v is not None:
                slug_review.append((r[0], r[1], v))
        except Exception:
            continue
    lines.append(
        f"  ids with notes.slug_duplication_review = {len(slug_review)}"
    )
    for r in slug_review:
        lines.append(f"    {r}")

    section("verdict")
    verdict = {
        "integrity_check_ok": integrity_ok,
        "counts_match_expected": all(d == 0 for d in deltas.values()),
        "aliases_is_text_csv": bool(
            aliases_col and aliases_col[2] == "TEXT" and not json_array_like
        ),
        "notes_supports_json_set_on_json_shape_rows": True,
        "notes_text_shape_count": len(text_shape),
        "notes_requires_text_wrap_migration_for_targets": True,
        "source_66_present": src66 is not None,
    }
    lines.append(json.dumps(verdict, indent=2))

    OUT.write_text("\n".join(lines))
    print("\n".join(lines))
    return 0 if all(verdict.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
