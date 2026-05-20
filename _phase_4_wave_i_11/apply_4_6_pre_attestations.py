"""
MAC-190 Phase 4 §4.6 — Apply 58 Wave I.9 cross-axis pre-attestations.

Per dispatch §4.6:
  - Each pre-attestation INSERTs raw_observations row(s) linking the Phase 3a
    identifier_id to the cross-axis evidence, and triggers §8.3 lift evaluation.
  - id=35305 is superseded (Phase 2.5 demoted) → skip + log.

Mechanic (operationally faithful to §11 #1 + §11 #7):
  - Phase 3a Wave I.9 canonical targets:
      DJI: 4 rows (35302, 35303, 35304, 35305 superseded)
      Parrot: 0 rows (Wave I.9 phase 3a landed 0 Parrot identifiers)
      Cellebrite: 0 rows (Wave I.9 phase 3a landed 0 Cellebrite identifiers)
  - INSERT 1 raw_observations row per Phase 3a target row, carrying:
      - per-canonical pre-attestation count (DJI=35, plan §wave_i_9_cross_axis_pre_attestations)
      - sample hostnames enumerated in plan
      - cross-axis evidence pointer to existing canonical hard_id row
  - For non-superseded Phase 3a rows: re-evaluate §8.3 lift against post-§4.4
    hard_id state.
  - For Parrot/Cellebrite (no canonical Phase 3a target): log as carry-forward
    metadata — no INSERT (cannot fabricate identifier_id linkage per §11 #1).
"""

import sqlite3, json, datetime
from pathlib import Path

DB = '/home/kev/argus/db/argus.db'
PLAN = '/home/kev/argus-internal/wave_i_pre_v1/wave_i_11_reconciliation/RECONCILIATION_PLAN_FOR_PAPERCLIP_V1_4_1.json'
LOG = Path('/home/kev/argus/_phase_4_wave_i_11/cross_axis_pre_attestation_log.md')
NOW = datetime.datetime.now(datetime.UTC).isoformat()

with open(PLAN) as f:
    plan = json.load(f)
pre_attest = plan['wave_i_9_cross_axis_pre_attestations']
per_can = pre_attest['per_canonical']

# Per-canonical hard_id row IDs from §4.4 plan candidates (representative pair hard_id)
HARD_ID_BY_CANONICAL = {
    'DJI': 423,         # 8c:58:23 oui (lifted to 95 in §4.4)
    'Parrot': 416,      # 90:3a:e6 oui (lifted to 95 in §4.4)
    'Cellebrite': 443,  # 00:16:00 oui (lifted to 95 in §4.4)
}

conn = sqlite3.connect(DB)
cur = conn.cursor()

log = ["# §4.6 Wave I.9 cross-axis pre-attestation log — MAC-190 Phase 4", f"Captured: {NOW}", ""]
log.append("## Mechanic")
log.append("- Each Phase 3a Wave I.9 identifier row receives 1 INSERT raw_observations row attesting cross-axis pre-attestation evidence.")
log.append("- Per-canonical pre-attestation aggregate (35 DJI / 12 Parrot / 11 Cellebrite = 58) captured in notes.")
log.append("- Parrot/Cellebrite have 0 Phase 3a canonical rows → no INSERT possible (§11 #1); carry-forward as metadata-only.")
log.append("- 35305 superseded → INSERT raw_observations carry-forward row but SKIP lift.")
log.append("")

stats = {
    'inserts': 0,
    'lifts_applied': 0,
    'lifts_no_op': 0,
    'skipped_demoted': 0,
    'carry_forward_no_canonical_target': 0,
    'targets_total': 0,
}

cur.execute("BEGIN")
try:
    for can in per_can:
        name = can['canonical_name']
        log.append(f"## {name} (mid={can['manufacturer_id']})")
        log.append(f"- wave_i_9_hostname_count: {can['wave_i_9_hostname_count']}")
        log.append(f"- existing_hard_id_axis_rows: {can['existing_hard_id_axis_rows']}")
        log.append(f"- cross_axis_pre_attested: {can['cross_axis_pre_attested']}")
        log.append(f"- lift_eligible_at_promotion: {can['lift_eligible_at_promotion']}")
        log.append(f"- sample_hostnames_first_3: {[s['hostname'] for s in can['sample_hostnames_first_3']]}")

        if not can['cross_axis_pre_attested']:
            log.append("- **NO-OP**: not cross-axis pre-attested (no existing hard_id rows). No INSERT, no lift.")
            log.append("")
            continue

        # Find Phase 3a canonical targets for this canonical (notes LIKE '%v1.4.1_stage_1_phase_3a%')
        mfg_keys = {'DJI': 'dji', 'Parrot': 'parrot', 'Cellebrite': 'cellebrite'}
        mfg = mfg_keys.get(name, name.lower())
        phase_3a_rows = cur.execute(
            "SELECT id, identifier, identifier_type, confidence, source_type, superseded_by, notes FROM identifiers WHERE manufacturer=? AND notes LIKE '%v1.4.1_stage_1_phase_3a%'",
            (mfg,)
        ).fetchall()

        if not phase_3a_rows:
            log.append(f"- **CARRY-FORWARD**: 0 Phase 3a canonical rows for `{mfg}`. {can['wave_i_9_hostname_count']} pre-attestations stored as plan-metadata only (no INSERT — §11 #1 / no identifier_id target to link).")
            stats['carry_forward_no_canonical_target'] += can['wave_i_9_hostname_count']
            log.append("")
            continue

        hard_id_target = HARD_ID_BY_CANONICAL.get(name)
        if hard_id_target is None:
            log.append(f"- **HALT-NO-HARD-ID**: no hard_id row mapping for canonical={name}")
            log.append("")
            continue

        hard_id_row = cur.execute("SELECT id, identifier, identifier_type, confidence, source_type FROM identifiers WHERE id=? AND superseded_by IS NULL", (hard_id_target,)).fetchone()
        if not hard_id_row:
            log.append(f"- **HALT-HARD-ID-NOT-ACTIVE**: hard_id_target={hard_id_target} not active")
            log.append("")
            continue

        log.append(f"- cross-axis hard_id evidence: row id={hard_id_row[0]} identifier='{hard_id_row[1]}' type={hard_id_row[2]} conf={hard_id_row[3]} src={hard_id_row[4]}")

        for target_row in phase_3a_rows:
            stats['targets_total'] += 1
            tid, t_identifier, t_type, t_conf, t_src, t_sup, t_notes = target_row
            log.append(f"### Phase 3a target id={tid} `{t_identifier}` (type={t_type}, conf={t_conf}, src={t_src}, sup={t_sup})")

            # INSERT raw_observations row
            obs_notes = {
                'wave_origin': 'wave_i_9_delta',
                'phase': 'v1.4.1_stage_1_phase_4',
                'dispatch_ref': 'MAC-190',
                'cp_anchor': 'phase_4_§4.6_cross_axis_pre_attestation',
                'attestation_kind': 'wave_i_9_cross_axis_pre_attestation_evidence_of_evidence',
                'per_canonical_aggregate_count': can['wave_i_9_hostname_count'],
                'sample_hostnames_first_3': [s['hostname'] for s in can['sample_hostnames_first_3']],
                'sample_source_repos_first_3': [s['source_repo'] for s in can['sample_hostnames_first_3']],
                'cross_axis_evidence_hard_id_row_id': hard_id_row[0],
                'cross_axis_evidence_hard_id_identifier': hard_id_row[1],
                'cross_axis_evidence_hard_id_type': hard_id_row[2],
                'cross_axis_evidence_hard_id_confidence': hard_id_row[3],
                'lift_methodology_note': can['lift_methodology_note'],
                'target_superseded': t_sup is not None,
            }
            source_url = f"wave_i_aggregate://wave_i_11_reconciliation/cross_axis_pre_attestation/{name}/{t_identifier}"

            cur.execute(
                """INSERT INTO raw_observations
                   (source_id, source_url, candidate_identifier, candidate_type, candidate_category, candidate_manufacturer,
                    source_excerpt, captured_at, processed_at, promoted_identifier_id, notes, source_row_key)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    66,  # Wave I umbrella
                    source_url,
                    t_identifier,
                    t_type,
                    'unknown',
                    mfg,
                    None,
                    NOW,
                    NOW,
                    tid,
                    json.dumps(obs_notes),
                    f"wave_i_9_pre_attestation_{name}_{t_identifier}_{NOW[:10]}"
                )
            )
            stats['inserts'] += 1
            log.append(f"- INSERT raw_observations promoted_identifier_id={tid} source_url='{source_url}'")

            # Skip lift if superseded
            if t_sup is not None:
                log.append(f"- **SKIP-DEMOTED**: target id={tid} superseded_by={t_sup}; no lift per dispatch §4.6")
                stats['skipped_demoted'] += 1
                continue

            # §8.3 lift evaluation
            hard_conf = hard_id_row[3]
            new_conf = min(99, max(t_conf, hard_conf) + 5)
            # Ceiling per hostname value_class (CP29 §2)
            CEILING = {
                'vendor_controlled_hostname': 95,
                'vendor_controlled_hostname_deprecated': 87,
                'vendor_cloud_endpoint_url': 97,
            }
            ceiling = CEILING.get(t_type, 95)
            capped = min(new_conf, ceiling)
            if capped <= t_conf:
                log.append(f"- no-op: current={t_conf}, formula={new_conf}, capped={capped} (ceiling={ceiling})")
                stats['lifts_no_op'] += 1
                continue
            # Apply lift
            existing_notes = json.loads(t_notes) if t_notes else {}
            history_entry = {
                'at_utc': NOW,
                'from': t_conf,
                'to': capped,
                'rationale': f"phase_4_§4.6_§8.3_cross_axis_pre_attestation_lift: target_id={tid} hard_id_pair={hard_id_row[0]}",
                'dispatch': 'MAC-190',
                'cp_anchor': 'CP24_§8.3_cross_axis_pre_attestation',
            }
            corro_entry = {
                'at_utc': NOW,
                'basis': 'cross_axis_pre_attestation_§8.3_corroboration',
                'paired_row_id': hard_id_row[0],
                'paired_identifier': hard_id_row[1],
                'paired_identifier_type': hard_id_row[2],
                'paired_source_type': hard_id_row[4],
                'dispatch': 'MAC-190',
                'cp_anchor': 'CP24_§8.3_cross_axis_pre_attestation',
            }
            existing_notes.setdefault('confidence_history', []).append(history_entry)
            existing_notes.setdefault('cross_source_corroboration', []).append(corro_entry)
            new_notes = json.dumps(existing_notes)
            cur.execute("UPDATE identifiers SET confidence=?, notes=? WHERE id=? AND superseded_by IS NULL", (capped, new_notes, tid))
            assert cur.rowcount == 1
            log.append(f"- **LIFT-APPLIED**: id={tid} conf {t_conf}→{capped} (formula={new_conf}, ceiling={ceiling})")
            stats['lifts_applied'] += 1
        log.append("")

    conn.commit()
    print("COMMIT OK")
except Exception as ex:
    conn.rollback()
    print(f"ROLLBACK: {ex}")
    raise

log.append("## Summary")
for k, v in stats.items():
    log.append(f"- {k}: {v}")
log.append("")
log.append("## Note on '58 pre-attestation' headline count")
log.append("- DJI: 35 underlying pre-attestation hostnames → 4 INSERTs (one per Phase 3a row); 3 lift fires + 1 superseded skip.")
log.append("- Parrot: 12 pre-attestation hostnames → 0 INSERTs (no Phase 3a Parrot canonical row to link). Carry-forward metadata.")
log.append("- Cellebrite: 11 pre-attestation hostnames → 0 INSERTs (no Phase 3a Cellebrite canonical row). Carry-forward metadata.")
log.append(f"- Total INSERTs: {stats['inserts']} raw_observations rows representing 58 underlying pre-attestation hostnames per per-canonical aggregate captured in notes.")
log.append("- Stage 2 amendment-log candidate: the '58 → 4 INSERTs' compression is a §4.6 mechanic-clarity question (per-attestation vs per-target). Surface for CEO ratification.")

LOG.write_text("\n".join(log))
print(f"Wrote {LOG}")
print(json.dumps(stats, indent=2))
