"""MAC-191 §5.6 — sierrawireless slug merge (Phase 2.5 Q3 deferral).

Per Phase 2.5 Q3 disposition (MAC-188): the lone `sierrawireless` slug row (id=35300)
duplicates the canonical `sierra_wireless` form (N=126 identifiers in same form).

Steps per dispatch §5.6:
1. Confirm `sierra_wireless` is the canonical form in `identifiers.manufacturer` (N=126).
2. Find slug-form rows (`manufacturer='sierrawireless'`) — expect 1 (id=35300).
3. UPDATE → `manufacturer='sierra_wireless'`.
4. Mark `notes.slug_duplication_review='resolved_phase_5_mac191'`.
5. No separate `sierrawireless` row in manufacturers table → no cleanup needed there.

Out-of-scope (Stage 2 candidate): 6 rows with manufacturer='Sierra Wireless' (TitleCase
with space) — these differ in case+format from canonical slug `sierra_wireless` but are
not slug-form variants per the dispatch §5.6 scope ("whatever the slug form is" implies
slug-style only).
"""
from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path

DB = Path("/home/kev/argus/db/argus.db")
LOG = Path("/home/kev/argus/_phase_5_wave_i_12/sierrawireless_slug_merge_log.md")
NOW = datetime.datetime.now(datetime.UTC).isoformat()


def main() -> int:
    con = sqlite3.connect(DB)
    cur = con.cursor()

    log: list[str] = []
    log.append("# §5.6 sierrawireless slug merge log — MAC-191 Phase 5")
    log.append(f"Captured: {NOW}")
    log.append("")
    log.append("## Pre-state")

    pre_canonical = cur.execute(
        "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL AND manufacturer = 'sierra_wireless'"
    ).fetchone()[0]
    pre_slug = cur.execute(
        "SELECT id, identifier, identifier_type, manufacturer, source_url FROM identifiers WHERE manufacturer = 'sierrawireless'"
    ).fetchall()
    pre_title = cur.execute(
        "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL AND manufacturer = 'Sierra Wireless'"
    ).fetchone()[0]

    log.append(f"  canonical slug 'sierra_wireless' active count = {pre_canonical}")
    log.append(f"  slug-form 'sierrawireless' rows = {len(pre_slug)}")
    for r in pre_slug:
        log.append(f"    id={r[0]} identifier={r[1]!r} type={r[2]} source_url={r[4]}")
    log.append(f"  TitleCase 'Sierra Wireless' active count = {pre_title} (out-of-scope; Stage 2)")

    if len(pre_slug) == 0:
        log.append("")
        log.append("## SKIP — no slug-form rows to merge.")
        log.append("Phase 2.5 carry-forward already resolved upstream.")
        LOG.write_text("\n".join(log))
        print("§5.6 SKIP — no slug-form rows")
        return 0

    # Halt check: verify identifier semantics are Sierra Wireless
    log.append("")
    log.append("## Halt check — vendor-identity verification")
    for r in pre_slug:
        ident = r[1]
        if "sierrawireless" not in ident.lower() and "sierra" not in ident.lower():
            log.append(
                f"  HALT id={r[0]} identifier={ident!r} — slug-form 'sierrawireless' "
                f"but identifier-content doesn't reference Sierra Wireless. SURFACE."
            )
            print(f"HALT id={r[0]} — vendor-identity mismatch")
            LOG.write_text("\n".join(log))
            return 1
        log.append(
            f"  id={r[0]} identifier={ident!r} — sierrawireless.com domain references Sierra Wireless ✓"
        )

    # Apply merge
    log.append("")
    log.append("## Apply merge")
    cur.execute("BEGIN")
    try:
        updated = 0
        notes_updated = 0
        for r in pre_slug:
            ident_id = r[0]
            # Read notes
            notes_row = cur.execute(
                "SELECT notes FROM identifiers WHERE id = ?", (ident_id,)
            ).fetchone()
            try:
                notes_d = json.loads(notes_row[0]) if notes_row[0] else {}
            except Exception:
                notes_d = {"_legacy_text_notes": notes_row[0]}
            old_review = notes_d.get("slug_duplication_review")
            notes_d["slug_duplication_review"] = "resolved_phase_5_mac191"
            notes_d["slug_duplication_resolution_dispatch"] = "MAC-191"
            notes_d["slug_duplication_resolution_at_utc"] = NOW
            notes_d["slug_duplication_pre_manufacturer"] = "sierrawireless"
            # Append manufacturer_text_history audit trail (per CP24 §3 sub-rule b shape)
            hist = notes_d.get("manufacturer_text_history", [])
            hist.append({
                "at_utc": NOW,
                "from": "sierrawireless",
                "to": "sierra_wireless",
                "rationale": "Phase 2.5 Q3 deferral resolved per dispatch §5.6 — slug-form merged into canonical sierra_wireless (N=126).",
                "dispatch": "MAC-191",
                "cp_anchor": "phase_5_§5.6_sierrawireless_slug_merge",
            })
            notes_d["manufacturer_text_history"] = hist
            new_notes = json.dumps(notes_d)
            cur.execute(
                "UPDATE identifiers SET manufacturer = 'sierra_wireless', notes = ? WHERE id = ?",
                (new_notes, ident_id),
            )
            assert cur.rowcount == 1
            updated += 1
            notes_updated += 1
            log.append(f"  APPLY id={ident_id}: 'sierrawireless' → 'sierra_wireless'")
            log.append(f"    notes.slug_duplication_review: {old_review!r} → 'resolved_phase_5_mac191'")
            log.append(f"    notes.manufacturer_text_history[] +1 audit entry")
        con.commit()
        log.append(f"  COMMIT: {updated} rows updated")
    except Exception as ex:
        con.rollback()
        log.append(f"  ROLLBACK: {ex!r}")
        raise

    # Post-state
    log.append("")
    log.append("## Post-state")
    post_canonical = cur.execute(
        "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL AND manufacturer = 'sierra_wireless'"
    ).fetchone()[0]
    post_slug = cur.execute(
        "SELECT COUNT(*) FROM identifiers WHERE manufacturer = 'sierrawireless'"
    ).fetchone()[0]
    log.append(f"  canonical slug 'sierra_wireless' active count = {post_canonical} (was {pre_canonical}; expect +{len(pre_slug)})")
    log.append(f"  slug-form 'sierrawireless' rows = {post_slug} (was {len(pre_slug)}; expect 0)")
    if post_canonical != pre_canonical + len(pre_slug):
        log.append(f"  WARN: canonical count delta != merged count")
    if post_slug != 0:
        log.append(f"  WARN: residual slug-form rows after merge")

    # Stage 2 surfacing
    log.append("")
    log.append("## Stage 2 candidates surfaced")
    log.append(f"- TitleCase 'Sierra Wireless' rows ({pre_title}) are out-of-scope for §5.6 (slug-form merge).")
    log.append("  These rows differ in case+format and may merit a separate canonical-form normalization")
    log.append("  in v1.5.0. Surface for CEO ratification.")

    LOG.write_text("\n".join(log))
    print(
        f"§5.6 merged={len(pre_slug)} pre_canonical={pre_canonical} post_canonical={post_canonical} title_oos={pre_title}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
