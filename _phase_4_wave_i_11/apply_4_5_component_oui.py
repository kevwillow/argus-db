"""
MAC-190 Phase 4 §4.5 — Apply 2 component-supplier OUI enrichments.

Append component_supplier_ouis JSON fragment to manufacturers.notes for:
- Autel Robotics (id=206): OUI 00:01:22 (Trend Communications, Ltd.) — WiFi/networking chipset embedded reference
- Hikvision (id=209):       OUI 00:05:00 (Cisco Systems, Inc)        — WiFi/networking chipset embedded reference

Framing per plan: supply-chain metadata; NOT a vendor identifier promotion.
"""

import sqlite3, json, datetime
from pathlib import Path

DB = '/home/kev/argus/db/argus.db'
PLAN = '/home/kev/argus-internal/wave_i_pre_v1/wave_i_11_reconciliation/RECONCILIATION_PLAN_FOR_PAPERCLIP_V1_4_1.json'
LOG = Path('/home/kev/argus/_phase_4_wave_i_11/component_supplier_oui_log.md')
NOW = datetime.datetime.now(datetime.UTC).isoformat()

with open(PLAN) as f:
    plan = json.load(f)
props = plan['component_supplier_oui_enrichment']['proposals']

conn = sqlite3.connect(DB)
cur = conn.cursor()

log = ["# §4.5 Component-supplier OUI enrichment log — MAC-190 Phase 4", f"Captured: {NOW}", ""]

cur.execute("BEGIN")
try:
    for p in props:
        mid = p['target_manufacturer_id']
        name = p['target_canonical_name']
        fragment = p['proposed_fragment']['component_supplier_ouis'][0]
        log.append(f"## {name} (id={mid})")
        row = cur.execute("SELECT id, canonical_name, notes FROM manufacturers WHERE id=?", (mid,)).fetchone()
        if not row:
            log.append(f"  - **HALT-NOT-FOUND**: manufacturers.id={mid}")
            continue
        cur_notes = json.loads(row[2]) if row[2] else {}
        existing = cur_notes.get('component_supplier_ouis', [])
        log.append(f"  - pre: existing component_supplier_ouis = {existing}")
        # Idempotent guard
        if any(x.get('oui') == fragment['oui'] for x in existing):
            log.append(f"  - SKIP: OUI {fragment['oui']} already in component_supplier_ouis")
            continue
        # Annotate fragment with provenance
        annotated = dict(fragment)
        annotated['integration_dispatch'] = 'MAC-190'
        annotated['cp_anchor'] = 'phase_4_§4.5_component_supplier_metadata'
        annotated['integration_at_utc'] = NOW
        existing.append(annotated)
        cur_notes['component_supplier_ouis'] = existing
        new_notes = json.dumps(cur_notes)
        cur.execute("UPDATE manufacturers SET notes=? WHERE id=?", (new_notes, mid))
        assert cur.rowcount == 1
        log.append(f"  - **APPLY**: appended OUI {fragment['oui']} ({fragment['supplier_organization']})")
        log.append(f"  - post: component_supplier_ouis count={len(existing)}")
    conn.commit()
    print("COMMIT OK")
except Exception as ex:
    conn.rollback()
    print(f"ROLLBACK: {ex}")
    raise

# Verification readback
log.append("")
log.append("## Verification readback")
for mid in [206, 209]:
    row = cur.execute("SELECT id, canonical_name, json_extract(notes, '$.component_supplier_ouis') FROM manufacturers WHERE id=?", (mid,)).fetchone()
    log.append(f"- mid={mid} {row[1]}: component_supplier_ouis = {row[2]}")

LOG.write_text("\n".join(log))
print(f"Wrote {LOG}")
