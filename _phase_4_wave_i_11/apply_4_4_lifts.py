"""
MAC-190 Phase 4 §4.4 — Apply 20 cross-axis §8.3 lifts.

Mechanic: CP24 cross-axis corroboration via (hostname, hard_id) pair.
  new_conf = min(99, max(host_conf, hard_id_conf) + 5)
  capped_conf = min(new_conf, value_class_ceiling(row))
  per-row: UPDATE confidence to capped_conf IFF capped_conf > current AND row not superseded.

Ceilings (CP29 §2 + §8.2 source-type bands):
  hostname:
    - vendor_controlled_hostname:           cross-source 95 (firmware-cert 99)
    - vendor_controlled_hostname_deprecated: 87 (no cross-source band)
    - vendor_cloud_endpoint_url:            cross-source 97
  hard_id (per source_type for primary_registry; per identifier_type for others):
    - source_type=primary_registry:         cross-band corroboration ceiling 95
    - source_type=manufacturer_app + ble_*: 95 outer (CP12/CP17 sub-band)
    - source_type=crowdsourced:             ceiling 75 (HALT cross-band uplift; §11 #8 ambiguity)
    - source_type=inferred:                 ceiling 70 (HALT cross-band uplift; §11 #8 ambiguity)

Audit-trail (Phase 3b precedent):
  notes.confidence_history[] append: {at_utc, from, to, rationale, dispatch, cp_anchor}
  notes.cross_source_corroboration[] append: {at_utc, basis, paired_row_id, paired_identifier, dispatch, cp_anchor}
"""

import sqlite3, json, datetime
from pathlib import Path

DB = '/home/kev/argus/db/argus.db'
PLAN = '/home/kev/argus-internal/wave_i_pre_v1/wave_i_11_reconciliation/RECONCILIATION_PLAN_FOR_PAPERCLIP_V1_4_1.json'
LOG = Path('/home/kev/argus/_phase_4_wave_i_11/cross_axis_lift_log.md')
NOW = datetime.datetime.now(datetime.UTC).isoformat()

with open(PLAN) as f:
    plan = json.load(f)
cands = plan['cross_axis_lift_candidates']['candidates']

# CP29 ceilings by value_class + §8.2 ceilings by source_type
HOSTNAME_CEILING = {
    'vendor_controlled_hostname': 95,            # cross-source band upper (CP29 §2)
    'vendor_controlled_hostname_deprecated': 87, # no cross-source band; single-source upper (CP29 §2)
    'vendor_cloud_endpoint_url': 97,             # cross-source band upper (CP29 §2)
}
HARD_ID_CEILING_BY_SOURCE = {
    'primary_registry': 95,   # §8.2 cross-band-corroboration ceiling
    'manufacturer_app': 95,   # §8.2 outer band (sub-band ceilings reach 95)
    'manufacturer_doc': 90,   # §8.2 band ceiling
    'regulatory': 95,          # §8.2 band ceiling
    'official': 100,           # §8.2 (no cap)
}
# crowdsourced / inferred → HALT per §11 #8 cross-band uplift ambiguity


def row_ceiling(row):
    """Determine ceiling for a row given its (identifier_type, source_type)."""
    itype, stype = row['identifier_type'], row['source_type']
    if itype in HOSTNAME_CEILING:
        return HOSTNAME_CEILING[itype]
    if stype in HARD_ID_CEILING_BY_SOURCE:
        return HARD_ID_CEILING_BY_SOURCE[stype]
    return None  # halt sentinel


def fetch(cur, rid):
    r = cur.execute(
        "SELECT id, identifier, identifier_type, manufacturer, confidence, source_type, superseded_by, notes FROM identifiers WHERE id=?",
        (rid,)
    ).fetchone()
    if not r:
        return None
    return {
        'id': r[0], 'identifier': r[1], 'identifier_type': r[2],
        'manufacturer': r[3], 'confidence': r[4], 'source_type': r[5],
        'superseded_by': r[6], 'notes': r[7]
    }


def merge_notes(existing_notes, history_entry, corro_entry):
    if existing_notes:
        try:
            n = json.loads(existing_notes)
            if not isinstance(n, dict):
                n = {'_legacy_notes': existing_notes}
        except Exception:
            n = {'_legacy_notes': existing_notes}
    else:
        n = {}
    n.setdefault('confidence_history', []).append(history_entry)
    n.setdefault('cross_source_corroboration', []).append(corro_entry)
    return json.dumps(n)


conn = sqlite3.connect(DB)
cur = conn.cursor()

log = []
log.append("# §4.4 Cross-axis §8.3 lift log — MAC-190 Phase 4 Wave I.11")
log.append(f"Captured: {NOW}")
log.append("")
log.append("## Per-candidate disposition")
log.append("")

stats = {'apply_row_updates': 0, 'no_op': 0, 'halt_superseded': 0,
         'halt_crowdsourced_ambiguity': 0, 'halt_inferred_ambiguity': 0,
         'halt_unknown_ceiling': 0, 'candidates_applied': 0, 'candidates_halted': 0}

cur.execute("BEGIN")
try:
    for c in cands:
        name = c['canonical_name']
        pair = c['lift_target_pair']
        log.append(f"### {name} (mid={c['manufacturer_id']})")
        host = fetch(cur, pair['hostname_row_id'])
        hard = fetch(cur, pair['hard_id_row_id'])
        if host is None or hard is None:
            log.append(f"- **HALT-NOT-FOUND**: host={host} hard={hard}")
            stats['candidates_halted'] += 1
            log.append("")
            continue

        # Skip if either row is superseded
        if host['superseded_by'] is not None or hard['superseded_by'] is not None:
            log.append(f"- **HALT-SUPERSEDED**: host_sup={host['superseded_by']} hard_sup={hard['superseded_by']} (DRT-class)")
            stats['halt_superseded'] += 1
            stats['candidates_halted'] += 1
            log.append("")
            continue

        # Compute lift
        new_conf = min(99, max(host['confidence'], hard['confidence']) + 5)
        log.append(f"- pair: host id={host['id']} type={host['identifier_type']} src={host['source_type']} conf={host['confidence']}")
        log.append(f"        hard id={hard['id']} type={hard['identifier_type']} src={hard['source_type']} conf={hard['confidence']}")
        log.append(f"- §8.3 formula: min(99, max({host['confidence']}, {hard['confidence']}) + 5) = {new_conf}")

        # Per-row ceiling + halt-ambiguity
        any_halt = False
        for label, row in [('host', host), ('hard_id', hard)]:
            if row['source_type'] in ('crowdsourced', 'inferred'):
                ambiguity = row['source_type']
                log.append(f"- **HALT-AMBIGUITY[{label}]**: row id={row['id']} source_type={ambiguity}; cross-band uplift ambiguity per §11 #8 + §8.2 (band-of-record cap vs §8.3 formula). Surface as Stage 2 amendment-log candidate.")
                stats[f'halt_{ambiguity}_ambiguity'] += 1
                any_halt = True
        if any_halt:
            stats['candidates_halted'] += 1
            log.append("")
            continue

        # Per-row apply
        applied_this_candidate = False
        for label, row in [('host', host), ('hard_id', hard)]:
            ceiling = row_ceiling(row)
            if ceiling is None:
                log.append(f"- **HALT-UNKNOWN-CEILING[{label}]**: row id={row['id']} type={row['identifier_type']} src={row['source_type']} — no ceiling table entry")
                stats['halt_unknown_ceiling'] += 1
                continue
            capped = min(new_conf, ceiling)
            if capped <= row['confidence']:
                log.append(f"- no-op[{label}] id={row['id']} current={row['confidence']} capped={capped} (ceiling={ceiling})")
                stats['no_op'] += 1
                continue
            history_entry = {
                'at_utc': NOW,
                'from': row['confidence'],
                'to': capped,
                'rationale': f"phase_4_§4.4_§8.3_cross_axis_lift: pair=({host['id']},{hard['id']}) host_type={host['identifier_type']} hard_type={hard['identifier_type']}",
                'dispatch': 'MAC-190',
                'cp_anchor': 'CP24_§8.3_cross_axis_lift',
            }
            corro_entry = {
                'at_utc': NOW,
                'basis': 'cross_axis_§8.3_corroboration',
                'paired_row_id': hard['id'] if label == 'host' else host['id'],
                'paired_identifier': hard['identifier'] if label == 'host' else host['identifier'],
                'paired_identifier_type': hard['identifier_type'] if label == 'host' else host['identifier_type'],
                'paired_source_type': hard['source_type'] if label == 'host' else host['source_type'],
                'dispatch': 'MAC-190',
                'cp_anchor': 'CP24_§8.3_cross_axis_lift',
            }
            merged = merge_notes(row['notes'], history_entry, corro_entry)
            cur.execute(
                "UPDATE identifiers SET confidence=?, notes=? WHERE id=? AND superseded_by IS NULL",
                (capped, merged, row['id'])
            )
            assert cur.rowcount == 1
            log.append(f"- **APPLY[{label}]** id={row['id']} conf {row['confidence']}→{capped} (ceiling={ceiling}, formula={new_conf})")
            stats['apply_row_updates'] += 1
            applied_this_candidate = True
        if applied_this_candidate:
            stats['candidates_applied'] += 1
        log.append("")

    conn.commit()
    print("COMMIT OK")
except Exception as ex:
    conn.rollback()
    print(f"ROLLBACK: {ex}")
    raise

log.append("## Summary")
log.append(f"- candidates total: {len(cands)}")
log.append(f"- candidates with ≥1 row applied: {stats['candidates_applied']}")
log.append(f"- candidates halted: {stats['candidates_halted']}")
log.append(f"- row UPDATEs applied: {stats['apply_row_updates']}")
log.append(f"- row-level no-ops (already at/above capped): {stats['no_op']}")
log.append(f"- halts: superseded={stats['halt_superseded']}, crowdsourced_ambiguity={stats['halt_crowdsourced_ambiguity']}, inferred_ambiguity={stats['halt_inferred_ambiguity']}, unknown_ceiling={stats['halt_unknown_ceiling']}")

LOG.write_text("\n".join(log))
print(f"Wrote {LOG}")
print(json.dumps(stats, indent=2))
