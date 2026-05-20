"""
MAC-190 Phase 4 §4.3 — Apply manufacturer-text attribution UPDATEs.

Scope (after §4.2 SAR-15 GENERIC_RISK_CANONICALS guard):
  - IEEE high_confidence: 11 entries / 13 rows  (PROMOTE)
  - SIG high_confidence:  5 entries /  5 rows  (PROMOTE)
  - IEEE conditional:    8 entries / 8 rows   (DEFER per §4.2)
  - FAA conditional:     1 entry  / 2 rows   (DEFER per §4.2)
  - Wireshark axis:     63 entries / 274 rows (DEFER — spec-ambiguity §11 #11)

Mode: single transaction; log every UPDATE; halt-per-row on
  - sentinel row (mfr=NULL, conf=0) -> skip
  - id not found / superseded       -> halt that row, continue batch
"""

import sqlite3
import json
import datetime
from pathlib import Path

DB = '/home/kev/argus/db/argus.db'
PLAN = '/home/kev/argus-internal/wave_i_pre_v1/wave_i_11_reconciliation/RECONCILIATION_PLAN_FOR_PAPERCLIP_V1_4_1.json'
LOG = Path('/home/kev/argus/_phase_4_wave_i_11/manufacturer_text_updates_log.md')

with open(PLAN) as f:
    plan = json.load(f)

mtau = plan['manufacturer_text_attribution_updates']['updates']

DEFER_AXES = {'wireshark_manuf'}  # spec-ambiguity defer
DEFER_PER_ENTRY_REASON = {}  # filled below


def axis_disposition(axis_name, entry):
    """Return ('apply', None) or ('defer', reason)."""
    if axis_name in DEFER_AXES:
        return ('defer', 'spec-ambiguity: Wireshark axis targets raw_observations.candidate_manufacturer not identifiers.manufacturer; surface as §11 #11')
    if entry.get('plan_inclusion') == 'included_conditional':
        return ('defer', 'SAR-15 GENERIC_RISK_CANONICALS conditional review DEFER per _phase_4_wave_i_11/conditional_review_log.md')
    return ('apply', None)


conn = sqlite3.connect(DB)
cur = conn.cursor()

log_lines = []
log_lines.append("# §4.3 Manufacturer-text UPDATE log — MAC-190 Phase 4 Wave I.11")
log_lines.append(f"Captured: {datetime.datetime.now(datetime.UTC).isoformat()}Z")
log_lines.append("")
log_lines.append("## Per-entry application log")
log_lines.append("")

stats = {'applied': 0, 'skipped_sentinel': 0, 'skipped_not_found': 0,
         'skipped_superseded': 0, 'deferred_entries': 0, 'deferred_rows': 0}

cur.execute("BEGIN")
try:
    for axis_name, entries in mtau.items():
        log_lines.append(f"### Axis: {axis_name}")
        log_lines.append("")
        for e in entries:
            dispo, reason = axis_disposition(axis_name, e)
            if dispo == 'defer':
                stats['deferred_entries'] += 1
                stats['deferred_rows'] += e.get('rows_affected', 0)
                log_lines.append(f"- **DEFER** raw='{e['raw_manufacturer_text']}' rows_in_plan={e['rows_affected']} -> {e['proposed_canonical_name']} | reason: {reason}")
                continue
            raw_text = e['raw_manufacturer_text']
            new_mfg = e['proposed_canonical_name']
            # Resolve all matching active identifier rows
            rows = cur.execute(
                "SELECT id, manufacturer, confidence, superseded_by FROM identifiers WHERE manufacturer=? AND superseded_by IS NULL",
                (raw_text,)
            ).fetchall()
            if not rows:
                log_lines.append(f"- **HALT-ROW** raw='{raw_text}' -> {new_mfg} | 0 active rows match — entry skipped (sample_ids={e.get('sample_identifier_ids')})")
                stats['skipped_not_found'] += 1
                continue
            log_lines.append(f"- **APPLY** raw='{raw_text}' -> {new_mfg} (canonical id={e.get('proposed_manufacturer_id')}, tier={e.get('match_tier')}, methodology={e.get('match_methodology')})")
            for rid, old_mfg, conf, sup in rows:
                # Skip Phase 2.5 sentinel rows (defensive — should not match anyway since mfr=NULL)
                if old_mfg is None and conf == 0:
                    log_lines.append(f"  - id={rid} **SKIP-SENTINEL** (mfr=NULL conf=0)")
                    stats['skipped_sentinel'] += 1
                    continue
                if sup is not None:
                    log_lines.append(f"  - id={rid} **SKIP-SUPERSEDED** (superseded_by={sup})")
                    stats['skipped_superseded'] += 1
                    continue
                cur.execute(
                    "UPDATE identifiers SET manufacturer=? WHERE id=? AND superseded_by IS NULL",
                    (new_mfg, rid)
                )
                assert cur.rowcount == 1, f"UPDATE id={rid} affected {cur.rowcount} rows"
                log_lines.append(f"  - id={rid} old='{old_mfg}' -> new='{new_mfg}' ✓")
                stats['applied'] += 1
        log_lines.append("")
    conn.commit()
    print("COMMIT OK")
except Exception as ex:
    conn.rollback()
    print(f"ROLLBACK: {ex}")
    raise

# Post-conditions
log_lines.append("## Summary")
log_lines.append("")
log_lines.append(f"- applied row UPDATEs: {stats['applied']}")
log_lines.append(f"- skipped sentinel rows: {stats['skipped_sentinel']}")
log_lines.append(f"- skipped not-found entries: {stats['skipped_not_found']}")
log_lines.append(f"- skipped superseded rows: {stats['skipped_superseded']}")
log_lines.append(f"- deferred entries: {stats['deferred_entries']}")
log_lines.append(f"- deferred rows (in-plan rows_affected sum): {stats['deferred_rows']}")
log_lines.append("")
log_lines.append("## Verification queries (post-apply)")
log_lines.append("")
# Spot-check a few
for sample_id in [5520, 13043, 6883, 17151, 1549, 1817, 2872, 3189]:
    r = cur.execute("SELECT id, identifier, manufacturer, confidence, source_excerpt FROM identifiers WHERE id=?", (sample_id,)).fetchone()
    log_lines.append(f"- id={sample_id}: manufacturer='{r[2]}' (post-update)")

LOG.write_text("\n".join(log_lines))
print(f"Wrote {LOG}")
print(f"Stats: {stats}")
