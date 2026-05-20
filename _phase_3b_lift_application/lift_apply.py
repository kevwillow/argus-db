"""Phase 3b §3.4 §8.3 lift application.

Dispatch: MAC-189
Authority: PROJECT_BIBLE.md §11 #8 (no confidence drift) + CP29 §8.2 ceilings
SAR-13 preflight: PRAGMA verified before SQL (run separately).

Algorithm:
1. Load 132 lift candidates from wave_i_9_lift_candidates_synthesis.json
2. For each candidate:
   a. Resolve identifier_id via (hostname, identifier_type='vendor_controlled_hostname', manufacturer=canonical)
   b. Skip if not found in canonical (probably not yet promoted)
   c. Skip + log if target was demoted in Phase 2.5 (superseded_by IS NOT NULL)
   d. CP24 cross-source independence: ≥2 distinct source_classes (operational reading
      per Phase 3a CEO-ratified Halt-3 promotions). Halt + surface single-class.
   e. Compute new_confidence = min(99, max(current, 90) + 5), with 90 being the upper
      of the default band [75,90] per synthesis bands.
   f. Apply value_class ceiling per CP29 §8.2:
        vendor_controlled_hostname: 95 (cross-source) / 99 (firmware-cert)
        vendor_cloud_endpoint_url: 97 (cross-source)
        vendor_controlled_hostname_deprecated: 87 (single-source max)
   g. UPDATE only if new > current.
3. Transaction per manufacturer (batched).
4. Emit lift_application_log.md + skipped_demoted.md.
"""
import sqlite3
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

DB = 'db/argus.db'
SYNTHESIS = '/home/kev/argus-internal/wave_i_pre_v1/wave_i_9_continuation/wave_i_9_lift_candidates_synthesis.json'
OUT_DIR = '/home/kev/argus/_phase_3b_lift_application'
DRY_RUN = '--apply' not in sys.argv

# The identifiers.manufacturer column for hostname-corpus rows stores vendor SLUGS
# (lowercase underscored: 'cisco_meraki', 'dji', 'autel_robotics'), NOT the
# manufacturers.canonical_name. The slug used in the synthesis JSON IS the value
# stored in identifiers.manufacturer — pass-through identity mapping, with
# fallback aliases for slug variants observed in canon vs synthesis.
VENDOR_SLUG_ALIASES = {
    # synthesis_slug: db_slug_to_also_try
    'sierra_wireless': ['sierra_wireless', 'sierrawireless'],
    'sierrawireless': ['sierrawireless', 'sierra_wireless'],
}

CEILINGS = {
    'vendor_controlled_hostname': 95,
    'vendor_cloud_endpoint_url': 97,
    'vendor_controlled_hostname_deprecated': 87,
}


def main():
    d = json.load(open(SYNTHESIS))
    cands = d['candidates']

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    def resolve(hostname, mfr_slug):
        mfr_candidates = VENDOR_SLUG_ALIASES.get(mfr_slug, [mfr_slug])
        for itype in ('vendor_controlled_hostname',
                      'vendor_cloud_endpoint_url',
                      'vendor_controlled_hostname_deprecated'):
            for mfr in mfr_candidates:
                r = cur.execute(
                    "SELECT id, confidence, identifier_type, manufacturer, "
                    "superseded_by, source_url, notes "
                    "FROM identifiers WHERE identifier = ? AND identifier_type = ? "
                    "AND manufacturer = ?",
                    (hostname, itype, mfr),
                ).fetchall()
                if r:
                    return r
        return []

    results = {
        'resolved_active': [],
        'resolved_demoted': [],
        'unresolved': [],
        'halt_single_class': [],
        'halt_ceiling_exceeded': [],
        'halt_no_mfr_mapping': [],
        'no_op_already_at_or_above': [],
        'lifts_to_apply': [],
    }

    for c in cands:
        host = c['hostname']
        vslug = c['vendor']
        sources = c.get('source_classes', [])
        bases = c.get('lift_basis', 'unknown')
        waves = c.get('waves_involved', [])
        band_default = c['candidate_confidence_band_default']
        band_lifted = c['candidate_confidence_band_lifted']

        # identifiers.manufacturer stores vendor slugs verbatim
        canon = vslug
        rows = resolve(host, canon)
        if not rows:
            results['unresolved'].append({
                'hostname': host, 'vendor': vslug, 'mfr': canon,
                'source_classes': sources,
            })
            continue

        for r in rows:
            ident_id = r['id']
            cur_conf = r['confidence']
            itype = r['identifier_type']
            superseded = r['superseded_by']

            if superseded is not None:
                results['resolved_demoted'].append({
                    'identifier_id': ident_id,
                    'hostname': host,
                    'manufacturer': canon,
                    'identifier_type': itype,
                    'current_confidence': cur_conf,
                    'superseded_by': superseded,
                    'source_classes': sources,
                })
                continue

            # CP24 cross-source independence: ≥2 source_classes
            if len(sources) < 2:
                results['halt_single_class'].append({
                    'identifier_id': ident_id,
                    'hostname': host,
                    'manufacturer': canon,
                    'identifier_type': itype,
                    'current_confidence': cur_conf,
                    'source_classes': sources,
                })
                continue

            # Lift formula
            lift_evidence_conf = band_default[1]  # upper of default band
            new_conf_raw = min(99, max(cur_conf, lift_evidence_conf) + 5)

            # Apply value_class ceiling
            ceiling = CEILINGS.get(itype, 99)
            new_conf = min(new_conf_raw, ceiling)

            if new_conf > 99:
                results['halt_ceiling_exceeded'].append({
                    'identifier_id': ident_id, 'hostname': host,
                    'computed': new_conf_raw, 'ceiling': ceiling,
                })
                continue

            if new_conf <= cur_conf:
                results['no_op_already_at_or_above'].append({
                    'identifier_id': ident_id,
                    'hostname': host,
                    'manufacturer': canon,
                    'identifier_type': itype,
                    'current_confidence': cur_conf,
                    'computed_new': new_conf,
                    'ceiling': ceiling,
                    'source_classes': sources,
                })
                continue

            results['lifts_to_apply'].append({
                'identifier_id': ident_id,
                'hostname': host,
                'manufacturer': canon,
                'identifier_type': itype,
                'current_confidence': cur_conf,
                'new_confidence': new_conf,
                'lift_basis': bases,
                'source_classes': sources,
                'waves_involved': waves,
                'ceiling': ceiling,
                'band_default': band_default,
                'band_lifted': band_lifted,
            })

    # Summary
    print('=== SUMMARY ===')
    for k, v in results.items():
        print(f'  {k}: {len(v)}')

    # Save full results for inspection
    with open(os.path.join(OUT_DIR, 'lift_evaluation_results.json'), 'w') as f:
        json.dump(results, f, indent=2)

    if DRY_RUN:
        print()
        print('DRY-RUN — no SQL writes. Re-run with --apply to commit.')
        return results

    # Apply lifts in per-manufacturer transactions
    now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    by_mfr = defaultdict(list)
    for lift in results['lifts_to_apply']:
        by_mfr[lift['manufacturer']].append(lift)

    applied = 0
    for mfr, lifts in by_mfr.items():
        try:
            cur.execute("BEGIN")
            for lift in lifts:
                ident_id = lift['identifier_id']
                new_conf = lift['new_confidence']

                # Read notes for confidence_history audit-trail (CP24 §3 sub-rule b)
                r = cur.execute("SELECT notes, confidence FROM identifiers WHERE id = ? AND superseded_by IS NULL", (ident_id,)).fetchone()
                if not r:
                    raise RuntimeError(f"identifier_id={ident_id} not found or demoted at apply-time")
                cur_conf_at_apply = r['confidence']
                if cur_conf_at_apply != lift['current_confidence']:
                    # Race condition: another process modified row between eval and apply
                    raise RuntimeError(f"race: identifier_id={ident_id} conf was {lift['current_confidence']} at eval, {cur_conf_at_apply} at apply")
                if new_conf <= cur_conf_at_apply:
                    continue

                notes = json.loads(r['notes']) if r['notes'] else {}
                hist = notes.get('confidence_history', [])
                hist.append({
                    'at_utc': now_iso,
                    'from': cur_conf_at_apply,
                    'to': new_conf,
                    'rationale': f'phase_3b_§3.4_§8.3_lift: cross-class corroboration via source_classes={lift["source_classes"]}',
                    'dispatch': 'MAC-189',
                    'cp_anchor': 'CP29_§8.2_cross_source_lift',
                })
                notes['confidence_history'] = hist

                # Cross-source corroboration marker per CP24 §2 audit-trail
                cs = notes.get('cross_source_corroboration', [])
                cs.append({
                    'at_utc': now_iso,
                    'lift_basis': lift['lift_basis'],
                    'source_classes_independent': lift['source_classes'],
                    'waves_involved': lift['waves_involved'],
                    'dispatch': 'MAC-189',
                    'phase': 'v1.4.1_stage_1_phase_3b',
                })
                notes['cross_source_corroboration'] = cs

                cur.execute(
                    "UPDATE identifiers SET confidence = ?, notes = ? "
                    "WHERE id = ? AND superseded_by IS NULL",
                    (new_conf, json.dumps(notes), ident_id),
                )
                applied += 1
            con.commit()
            print(f'committed: mfr={mfr} n={len(lifts)}')
        except Exception as e:
            con.rollback()
            print(f'ROLLBACK: mfr={mfr} error={e}')
            raise

    print(f'\nTotal lifts applied: {applied}')
    return results


if __name__ == '__main__':
    main()
