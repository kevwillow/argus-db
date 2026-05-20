#!/usr/bin/env python3
"""Phase 7-bis Wave I.14b + I.14c fccid.io 177-row re-dispatch (post-CP31).

MAC-201 (parent MAC-184), carved out of MAC-194 §7.2 halt.

Inputs (read-only):
  /media/kev/Extreme SSD/argus-archive-2026-05-20/wave_i_pre_v1/
    wave_i_14b_external_remine/EXTRACTION_PLAN_V2_FOR_PAPERCLIP_V1_4_1.json (53)
    wave_i_14c_unfreeze/EXTRACTION_PLAN_V3_FOR_PAPERCLIP_V1_4_1.json       (124)

Schema bindings (CP31 / migration 0025):
  identifiers.identifier_type admits 'fcc_grantee_code', 'equipment_class_code'
  identifiers.pair_kind admits 'fcc_grantee_equipment_class'
  manufacturers id=222 'Parrot Automotive' (is_arm=1, query_default='hidden_arm')

Discipline:
  §11 #1 (no fabrication) | §11 #7 (provenance) | §11 #8 (no conf drift)
  §11 #11 (amendment-log) | §11 #13 (device_category='unknown' default DROP from high-conf)
  CP15 single-source crowdsourced ceiling: conf = 75
  SAR-9 canonical+alias manufacturer resolution; HALT if not found.

Promotion shape (per dispatch §7.2-bis):
  Per distinct (grantee_code, manufacturer) tuple → 1 identifier row (type='fcc_grantee_code')
  Per distinct (equipment_class, manufacturer) tuple → 1 identifier row
      (type='equipment_class_code', paired_identifier_id → grantee row,
       pair_kind='fcc_grantee_equipment_class')
  Per plan row → 2 raw_observations rows (full provenance per identifier)

Idempotency: re-running on same DB state produces zero new identifier rows
  (caches existing (identifier, type, mfr) tuples).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

DB = 'db/argus.db'
ROOT = Path('/media/kev/Extreme SSD/argus-archive-2026-05-20/wave_i_pre_v1')
PLAN_V2 = ROOT / 'wave_i_14b_external_remine' / 'EXTRACTION_PLAN_V2_FOR_PAPERCLIP_V1_4_1.json'
PLAN_V3 = ROOT / 'wave_i_14c_unfreeze' / 'EXTRACTION_PLAN_V3_FOR_PAPERCLIP_V1_4_1.json'

AGENT_ID = 'da137694-2efe-4589-8150-828dcab881fb'  # Validator
SOURCE_ID = 51              # fccid.io
SOURCE_TYPE = 'crowdsourced'
CONF_CEIL = 75              # CP15 single-source crowdsourced ceiling
DEVICE_CATEGORY = 'unknown'  # dispatch §11 #13 default; CP32 will add 'automotive_telematics'

# SAR-9 canonical+alias resolution for the V2+V3 grantee_name surface.
# Each entry derived from sqlite_master canonical_name / aliases inspection.
NAME_TO_CANONICAL: dict[str, tuple[str, int, str]] = {
    'Motorola Solutions, Inc.': ('Motorola Solutions', 3, 'canonical-suffix-strip ", Inc."'),
    'Sierra Wireless Inc.':     ('Sierra Wireless',   21, 'alias-match "Sierra Wireless Inc."'),
    'Sierra Wireless Inc':      ('Sierra Wireless',   21, 'alias-match "Sierra Wireless Inc"'),
    'Sierra Wireless, Inc.':    ('Sierra Wireless',   21, 'canonical-suffix-strip ", Inc."'),
    'Sierra Wireless, Inc':     ('Sierra Wireless',   21, 'canonical-suffix-strip ", Inc"'),
    'Axon Enterprise, Inc':     ('Axon',              15, 'alias-match "Axon Enterprise, Inc"'),
    'Cradlepoint, Inc.':        ('Cradlepoint',       20, 'alias-match "Cradlepoint Inc." (canonical-suffix-strip)'),
    'Enforcement Video, LLC (d.b.a. WatchGuard Video)':
                                ('WatchGuard',        17, 'alias-match (FCC EAS d/b/a)'),
    'Numerex Corporation':      ('Sierra Wireless',   21, 'MAC-196 absorption (Sierra Wireless alias)'),
    'Harris Corporation':       ('Harris',             8, 'alias-match "Harris Corporation"'),
    'Reveal Media Limited':     ('Reveal',            16, 'alias-match "Reveal Media Limited"'),
    'SZ DJI BaiWang Technology Co.,Ltd':
                                ('DJI',               22, 'alias-match (DJI subsidiary)'),
    'Ericsson Enterprise Wireless Solutions, Inc.':
                                ('Cradlepoint',       20, 'Ericsson 2020 acquisition (UXX grantee shared) — §11 #11 surface'),
    'PARROT DRONE SAS':         ('Parrot Automotive', 222, 'CP31 routing rule (2AG → arm; §4 device-category provenance surface)'),
    'PARROT FAURECIA AUTOMOTIVE SAS':
                                ('Parrot Automotive', 222, 'CP31 alias-match (arm canonical_name aliases)'),
}


def resolve_manufacturer(grantee_code: str, grantee_name: str) -> tuple[str | None, int | None, str]:
    # CP31 §2 routing rule: all 2AG → Parrot Automotive id=222 (regardless of grantee_name).
    if grantee_code == '2AG':
        if grantee_name in NAME_TO_CANONICAL:
            return NAME_TO_CANONICAL[grantee_name]
        return ('Parrot Automotive', 222, 'CP31-routing-rule (2AG → arm; unknown grantee_name)')
    if grantee_name in NAME_TO_CANONICAL:
        return NAME_TO_CANONICAL[grantee_name]
    return (None, None, 'HALT-not-resolved')


def truncate_excerpt(s: str | None, max_len: int = 200) -> str | None:
    if not s:
        return s
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + '…'


def _grantee_code(row: dict, plan: str) -> str:
    if plan == 'v3':
        return row['grantee_code_3char']
    # V2 derives from FCC ID prefix (3-char or 5-char grantee).
    # All 17 grantee codes observed across V2+V3 are 3-char; safe to use [:3].
    return row['fcc_id'][:3]


def apply_wave(conn: sqlite3.Connection, wave_label: str, plan: str, plan_rows: list[dict],
               log_lines: list[str], halts: list[dict]) -> dict:
    cur = conn.cursor()

    notes_in = json.dumps({
        'dispatch': 'MAC-201', 'wave': wave_label, 'cohort_size': len(plan_rows),
        'phase': '7-bis (post-CP31 §7.2 re-dispatch)',
    })
    cur.execute(
        "INSERT INTO extraction_runs (agent_id, source_id, status, notes) "
        "VALUES (?, ?, 'running', ?)",
        (AGENT_ID, SOURCE_ID, notes_in),
    )
    run_id = cur.lastrowid

    log_lines.append(f'\n## {wave_label}\n\nextraction_run_id = {run_id} · plan rows = {len(plan_rows)}\n')

    # Pre-warm idempotency caches from existing identifiers
    grantee_cache: dict[tuple[str, str], int] = {}
    equip_cache: dict[tuple[str, str], int] = {}
    for r in cur.execute(
        "SELECT id, identifier, manufacturer FROM identifiers WHERE identifier_type='fcc_grantee_code'"
    ).fetchall():
        grantee_cache[(r[1], r[2])] = r[0]
    for r in cur.execute(
        "SELECT id, identifier, manufacturer FROM identifiers WHERE identifier_type='equipment_class_code'"
    ).fetchall():
        equip_cache[(r[1], r[2])] = r[0]

    # Per-(ec, mfr) tuple → set of grantee codes paired in this run (for notes annotation)
    equip_grantee_index: dict[tuple[str, str], set[str]] = {}

    promoted_g = reused_g = promoted_e = reused_e = ro_inserted = 0
    arm_routed = 0
    wave_halts: list[dict] = []

    for idx, row in enumerate(plan_rows, 1):
        gc = _grantee_code(row, plan)
        gn = row.get('grantee_name', '')
        ec = row.get('equipment_class_code')
        fcc_id = row.get('fcc_id', '')
        source_url = row['source_url']
        excerpt_full = row.get('source_excerpt') or ''
        excerpt_id = truncate_excerpt(excerpt_full, 200)

        mfr, mfr_id, routing_note = resolve_manufacturer(gc, gn)
        if mfr is None:
            wave_halts.append({
                'plan_row': idx, 'fcc_id': fcc_id, 'grantee_code': gc, 'grantee_name': gn,
                'reason': 'manufacturer_not_resolved', 'dispatch_halt_criterion': '#2 (no auto-admit)',
            })
            log_lines.append(f'- HALT row {idx}: fcc_id={fcc_id} grantee_name={gn!r} — manufacturer not resolved')
            continue

        if mfr_id == 222:
            arm_routed += 1

        # ── grantee_code identifier (per-(gc, mfr) unique) ───────────────────
        key_g = (gc, mfr)
        if key_g not in grantee_cache:
            cur.execute(
                """INSERT INTO identifiers (
                    identifier, identifier_type, device_category, manufacturer,
                    confidence, source_url, source_type, source_excerpt,
                    first_seen, last_verified, notes
                ) VALUES (?, 'fcc_grantee_code', ?, ?, ?, ?, ?, ?,
                          datetime('now'), datetime('now'), ?)""",
                (gc, DEVICE_CATEGORY, mfr, CONF_CEIL, source_url, SOURCE_TYPE, excerpt_id,
                 json.dumps({
                     'phase': '7-bis', 'wave': wave_label, 'dispatch': 'MAC-201',
                     'routing_note': routing_note, 'manufacturer_id': mfr_id,
                     'grantee_name_attested': gn,
                     'fcc_grantees_anchor_present': gc not in ('2AG', '2AH', '2AL'),
                 })),
            )
            grantee_cache[key_g] = cur.lastrowid
            promoted_g += 1
        else:
            reused_g += 1
        gid = grantee_cache[key_g]

        # ── equipment_class_code identifier (per-(ec, mfr) unique, paired) ───
        key_e = (ec, mfr)
        equip_grantee_index.setdefault(key_e, set()).add(gc)
        if key_e not in equip_cache:
            cur.execute(
                """INSERT INTO identifiers (
                    identifier, identifier_type, device_category, manufacturer,
                    confidence, source_url, source_type, source_excerpt,
                    first_seen, last_verified, notes,
                    paired_identifier_id, pair_kind
                ) VALUES (?, 'equipment_class_code', ?, ?, ?, ?, ?, ?,
                          datetime('now'), datetime('now'), ?,
                          ?, 'fcc_grantee_equipment_class')""",
                (ec, DEVICE_CATEGORY, mfr, CONF_CEIL, source_url, SOURCE_TYPE, excerpt_id,
                 json.dumps({
                     'phase': '7-bis', 'wave': wave_label, 'dispatch': 'MAC-201',
                     'equipment_class_label': (row.get('equipment_class_label') or '')[:200],
                     'paired_grantee_code_first': gc,
                     'paired_grantee_codes': [gc],
                     'manufacturer_id': mfr_id,
                 }),
                 gid),
            )
            equip_cache[key_e] = cur.lastrowid
            promoted_e += 1
        else:
            reused_e += 1

        # ── raw_observations (provenance chain, 2 per plan row) ──────────────
        # source_row_key composed `<fcc_id>::<candidate_type>` to satisfy
        # idx_raw_obs_source_row UNIQUE(source_id, source_row_key) — one row
        # per identifier_type per FCC ID. INSERT OR IGNORE for idempotency.
        for cand_id, cand_type, prom_id in [
            (gc, 'fcc_grantee_code', gid),
            (ec, 'equipment_class_code', equip_cache[key_e]),
        ]:
            srk = f'{fcc_id}::{cand_type}'
            cur.execute(
                """INSERT OR IGNORE INTO raw_observations (
                    source_id, extraction_run_id, source_url, raw_payload,
                    candidate_identifier, candidate_type, candidate_category,
                    candidate_manufacturer, source_excerpt, processed_at,
                    promoted_identifier_id, notes, source_row_key
                ) VALUES (?, ?, ?, ?, ?, ?, 'unknown', ?, ?, datetime('now'), ?, ?, ?)""",
                (SOURCE_ID, run_id, source_url, json.dumps(row),
                 cand_id, cand_type, mfr, excerpt_full, prom_id,
                 json.dumps({
                     'phase': '7-bis', 'wave': wave_label, 'dispatch': 'MAC-201',
                     'fcc_id': fcc_id, 'routing_note': routing_note,
                 }),
                 srk),
            )
            if cur.rowcount == 1:
                ro_inserted += 1

    # Post-loop: update equip rows whose (ec, mfr) tuple paired with >1 grantee_code.
    for (ec, mfr), gcs in equip_grantee_index.items():
        if len(gcs) > 1:
            eid = equip_cache[(ec, mfr)]
            existing_notes = cur.execute(
                "SELECT notes FROM identifiers WHERE id=?", (eid,)
            ).fetchone()[0]
            n = json.loads(existing_notes) if existing_notes else {}
            n['paired_grantee_codes'] = sorted(gcs)
            n['paired_grantee_codes_note'] = (
                'pair_kind FK captures first-seen grantee; full grantee list here for §11 #7 provenance'
            )
            cur.execute("UPDATE identifiers SET notes=? WHERE id=?", (json.dumps(n), eid))

    halts.extend(wave_halts)

    # Finalize extraction_run
    cur.execute(
        "UPDATE extraction_runs SET status=?, finished_at=datetime('now'), "
        "records_in=?, records_out=?, errors=?, notes=? WHERE id=?",
        ('ok' if not wave_halts else 'partial',
         len(plan_rows), promoted_g + promoted_e + ro_inserted, len(wave_halts),
         json.dumps({
             'dispatch': 'MAC-201', 'wave': wave_label,
             'phase': '7-bis (post-CP31)', 'cohort_size': len(plan_rows),
             'promoted_grantee_identifiers': promoted_g,
             'reused_grantee_identifiers': reused_g,
             'promoted_equipment_class_identifiers': promoted_e,
             'reused_equipment_class_identifiers': reused_e,
             'raw_observations_inserted': ro_inserted,
             'arm_routed_count': arm_routed,
             'halts': wave_halts,
         }),
         run_id),
    )

    summary = {
        'wave': wave_label, 'extraction_run_id': run_id,
        'plan_rows': len(plan_rows),
        'promoted_grantee': promoted_g, 'reused_grantee': reused_g,
        'promoted_equip': promoted_e, 'reused_equip': reused_e,
        'raw_obs_inserted': ro_inserted,
        'arm_routed_count': arm_routed,
        'halts': len(wave_halts),
    }
    log_lines.append(
        f'\n**{wave_label} summary:** '
        f'promoted grantee={promoted_g} (reused {reused_g}) · '
        f'promoted equipment_class={promoted_e} (reused {reused_e}) · '
        f'raw_observations inserted={ro_inserted} · '
        f'arm-routed (id=222)={arm_routed} · halts={len(wave_halts)}\n'
    )
    return summary


def main() -> int:
    v2_payload = json.loads(PLAN_V2.read_text())
    v3_payload = json.loads(PLAN_V3.read_text())
    v2 = v2_payload['fccid_io_content_promotions']
    v3 = v3_payload['fccid_io_extended_promotions']

    if len(v2) != 53 or len(v3) != 124:
        raise SystemExit(f'plan-row count mismatch: V2={len(v2)} V3={len(v3)} (expected 53 + 124)')

    conn = sqlite3.connect(DB)
    conn.execute('PRAGMA foreign_keys = ON')

    pre_active = conn.execute(
        'SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL'
    ).fetchone()[0]
    pre_ro = conn.execute('SELECT COUNT(*) FROM raw_observations').fetchone()[0]
    print(f'PRE: identifiers active={pre_active}, raw_observations={pre_ro}')

    log_lines = [
        '# Phase 7-bis fccid.io 177-row promotions log',
        '',
        '**Dispatch:** [MAC-201](/MAC/issues/MAC-201)',
        '**Parent:** [MAC-184](/MAC/issues/MAC-184) v1.4.1 Stage 1 integration',
        '**Carved-out source:** [MAC-194](/MAC/issues/MAC-194) §7.2 halt',
        '**CP31 ratification:** [MAC-197](/MAC/issues/MAC-197) (migration 0025 at `40b166e`)',
        '**Branch HEAD pre-apply:** `cbb0cd7`',
        '**Pre-apply DB backup:** `db/argus.db.mac201_pre_phase7bis_backup`',
        '',
        '## Discipline envelope active',
        '',
        '- §11 #1 (no fabrication) · §11 #7 (provenance) · §11 #8 (no conf drift)',
        '- §11 #11 (amendment-log) · §11 #13 (device_category=`unknown` → DROP from high-conf export, by design)',
        '- CP15 single-source crowdsourced ceiling: conf = 75',
        '- SAR-9 canonical+alias manufacturer resolution',
        '- CP31 routing rule: all 2AG → Parrot Automotive id=222',
        '- MAC-196 routing rule: Numerex Corporation → Sierra Wireless id=21',
        '',
    ]
    halts: list[dict] = []

    conn.execute('BEGIN')
    s_b = apply_wave(conn, 'Wave I.14b (V2)', 'v2', v2, log_lines, halts)
    conn.commit()

    conn.execute('BEGIN')
    s_c = apply_wave(conn, 'Wave I.14c (V3)', 'v3', v3, log_lines, halts)
    conn.commit()

    post_active = conn.execute(
        'SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL'
    ).fetchone()[0]
    post_ro = conn.execute('SELECT COUNT(*) FROM raw_observations').fetchone()[0]
    print(f'POST: identifiers active={post_active} (Δ +{post_active - pre_active}), raw_observations={post_ro} (Δ +{post_ro - pre_ro})')

    log_lines.append('\n## Pre / Post counts\n')
    log_lines.append('| Metric | Pre | Post | Δ |')
    log_lines.append('|--------|----:|-----:|---:|')
    log_lines.append(f'| identifiers active (superseded_by IS NULL) | {pre_active:,} | {post_active:,} | +{post_active - pre_active:,} |')
    log_lines.append(f'| raw_observations | {pre_ro:,} | {post_ro:,} | +{post_ro - pre_ro:,} |')

    summary = {
        'dispatch': 'MAC-201',
        'pre': {'identifiers_active': pre_active, 'raw_observations': pre_ro},
        'post': {'identifiers_active': post_active, 'raw_observations': post_ro},
        'delta': {
            'identifiers_active': post_active - pre_active,
            'raw_observations': post_ro - pre_ro,
        },
        'wave_i_14b': s_b,
        'wave_i_14c': s_c,
        'halts': halts,
    }

    Path('_phase_7_bis_fccid/promotions_log.md').write_text('\n'.join(log_lines))
    Path('_phase_7_bis_fccid/promotions_summary.json').write_text(json.dumps(summary, indent=2))
    conn.close()
    print('\n=== summary ===')
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
