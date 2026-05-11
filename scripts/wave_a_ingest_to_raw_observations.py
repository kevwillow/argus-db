#!/usr/bin/env python3
"""Wave-A surfacing JSON → raw_observations mechanical ingestion.

Path B per MAC-63 board direction `d3d1bbda` 2026-05-11. Wave-A surfacings on
disk are already in raw_observations shape (file/line provenance, candidate_*
fields). This script translates them mechanically — no re-mining, no new
extraction; just JSON-to-row.

Per board direction:
- source_url MUST be the public upstream URL (github.com/<org>/<repo>/blob/
  <SHA>/<path>#L<line>) per Bible §11 #1 "working source_url" discipline.
- Local Wave-A surfacing artifact path goes in notes JSON, NEVER as source_url.
- candidate_type values aligned with post-CP14 27-value identifier_type enum
  where applicable; non-enum candidate_types (e.g. behavioral_signature)
  preserve as-is for behavioral_signatures-table routing.
- Defensive: db/argus.db.pre_wave_a_ingest_backup created before any writes.

Per Bible §7.3: this would normally be ExtractionWorker scope. Board direction
authorized CEO-class direct ingestion this run since it's mechanical translation
of already-staged artifacts (~1 heartbeat).
"""

import sqlite3
import json
import os
import hashlib
import shutil
from datetime import datetime, timezone

REPO = '/home/kev/argus'
DB = f'{REPO}/db/argus.db'
WAVE_A_DIR = f'{REPO}/raw/wave_a'
NOW = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
AGENT_ID = '62a86779-651b-4c59-8773-cee9e0f53334'  # CEO


# Source registration: one entry per Wave-A repo. URL = upstream repo URL.
# source_type = 'crowdsourced' for community repos (GitHub research code) —
# the SDO content they expose lifts via §8.2 corroboration at promotion time,
# not by SOURCE-row classification (per board reframe at fe2beeee + d3d1bbda
# — SIG/IEEE/FAA-registry classification is the pending CP15 §8.2 question).
WAVE_A_SOURCES = {
    'MaxwellDPS_Flock-You-Android': {
        'name': 'GitHub: MaxwellDPS/Flock-You-Android (Wave-A 1a)',
        'url': 'https://github.com/MaxwellDPS/Flock-You-Android',
        'source_type': 'crowdsourced',
        'tier': 2,
    },
    'judcrandall_lookout.py': {
        'name': 'GitHub: judcrandall/lookout.py (Wave-A 1a/1b)',
        'url': 'https://github.com/judcrandall/lookout.py',
        'source_type': 'crowdsourced',
        'tier': 2,
    },
    'tesorrells_RF-Drone-Detection': {
        'name': 'GitHub: tesorrells/RF-Drone-Detection (Wave-A 1c)',
        'url': 'https://github.com/tesorrells/RF-Drone-Detection',
        'source_type': 'crowdsourced',
        'tier': 2,
    },
    'opendroneid_opendroneid-core-c': {
        'name': 'GitHub: opendroneid/opendroneid-core-c (Wave-A 1d; ASTM/ASD-STAN reference impl)',
        'url': 'https://github.com/opendroneid/opendroneid-core-c',
        'source_type': 'crowdsourced',
        'tier': 1,
    },
    'colonelpanichacks_flock-you': {
        'name': 'GitHub: colonelpanichacks/flock-you (Wave-A 2a)',
        'url': 'https://github.com/colonelpanichacks/flock-you',
        'source_type': 'crowdsourced',
        'tier': 2,
    },
    'colonelpanichacks_oui-spy': {
        'name': 'GitHub: colonelpanichacks/oui-spy (Wave-A 2b)',
        'url': 'https://github.com/colonelpanichacks/oui-spy',
        'source_type': 'crowdsourced',
        'tier': 2,
    },
    'colonelpanichacks_Sky-Spy': {
        'name': 'GitHub: colonelpanichacks/Sky-Spy (Wave-A 2c)',
        'url': 'https://github.com/colonelpanichacks/Sky-Spy',
        'source_type': 'crowdsourced',
        'tier': 2,
    },
    'alphafox02_DragonSync': {
        'name': 'GitHub: alphafox02/DragonSync + FAA RID lookup submodule (Wave-A 3a)',
        'url': 'https://github.com/alphafox02/DragonSync',
        'source_type': 'crowdsourced',
        'tier': 1,
    },
    'seemoo-lab_AirGuard': {
        'name': 'GitHub: seemoo-lab/AirGuard (Wave-A 3b; multi-tracker BLE catalog)',
        'url': 'https://github.com/seemoo-lab/AirGuard',
        'source_type': 'crowdsourced',
        'tier': 1,
    },
    'opendroneid_receiver-android': {
        'name': 'GitHub: opendroneid/receiver-android (Wave-A 4a)',
        'url': 'https://github.com/opendroneid/receiver-android',
        'source_type': 'crowdsourced',
        'tier': 1,
    },
    'opendroneid_wireshark-dissector': {
        'name': 'GitHub: opendroneid/wireshark-dissector (Wave-A 4b)',
        'url': 'https://github.com/opendroneid/wireshark-dissector',
        'source_type': 'crowdsourced',
        'tier': 1,
    },
    'cyber-defence-campus_RemoteIDReceiver': {
        'name': 'GitHub: cyber-defence-campus/RemoteIDReceiver (Wave-A 4c; HSLU thesis)',
        'url': 'https://github.com/cyber-defence-campus/RemoteIDReceiver',
        'source_type': 'crowdsourced',
        'tier': 2,
    },
    'proto17_dji_droneid': {
        'name': 'GitHub: proto17/dji_droneid (Wave-A 4e)',
        'url': 'https://github.com/proto17/dji_droneid',
        'source_type': 'crowdsourced',
        'tier': 2,
    },
    'nixxxo_tagfinder': {
        'name': 'GitHub: nixxxo/tagfinder (Wave-A 4h)',
        'url': 'https://github.com/nixxxo/tagfinder',
        'source_type': 'crowdsourced',
        'tier': 2,
    },
    'EFForg_rayhunter': {
        'name': 'GitHub: EFForg/rayhunter (Wave-A 6α; defensive_tool per CP14 G-15)',
        'url': 'https://github.com/EFForg/rayhunter',
        'source_type': 'crowdsourced',
        'tier': 1,
    },
    'eylonK14_IMSICatcherDetector': {
        'name': 'GitHub: eylonK14/IMSICatcherDetector (Wave-A 6β; README-aspirational)',
        'url': 'https://github.com/eylonK14/IMSICatcherDetector',
        'source_type': 'crowdsourced',
        'tier': 3,
    },
    'CellularPrivacy_AIMSICD': {
        'name': 'GitHub: CellularPrivacy/AIMSICD (Wave-A 6γ; IMSI-detector cluster)',
        'url': 'https://github.com/CellularPrivacy/AIMSICD',
        'source_type': 'crowdsourced',
        'tier': 2,
    },
    'GainSec_Flock-Safety-Trap-Shooter-Sniffer-Alarm': {
        'name': 'GitHub: GainSec/Flock-Safety-Trap-Shooter-Sniffer-Alarm (Wave-A 6ζ)',
        'url': 'https://github.com/GainSec/Flock-Safety-Trap-Shooter-Sniffer-Alarm',
        'source_type': 'crowdsourced',
        'tier': 2,
    },
}


# candidate_type normalization map. Wave-A's pre-CP14 staging used some
# variant names that the CP14 enum unified. Mechanical translation maps
# them here; non-enum candidate_types (behavioral_signature etc.) preserve
# as-is — they will be routed to behavioral_signatures table at promotion.
CANDIDATE_TYPE_NORMALIZE = {
    'ble_service_uuid': 'ble_service',     # CP14 enum uses 'ble_service'
    'ble_uuid_128': 'ble_uuid',            # alias
    # 'ble_device_name_substring' stays as-is — G-12 vocab normalization
    # call deferred; the type isn't in the CP14 enum but raw_observations
    # has no CHECK, so it stages. Validator merges with ble_local_name vs
    # ble_device_name_substring at G-12 resolution.
}


def normalize_candidate_type(ct):
    """Map Wave-A staging vocab to post-CP14 enum where applicable.
    Returns (normalized_type, was_normalized)."""
    if ct in CANDIDATE_TYPE_NORMALIZE:
        return CANDIDATE_TYPE_NORMALIZE[ct], True
    return ct, False


def source_row_key(source_url, candidate_identifier, candidate_type):
    """Compute sha256 hex of (source_url|candidate_identifier|candidate_type).
    Matches existing WiGLE-era source_row_key pattern (64-char hex)."""
    key_str = f'{source_url}|{candidate_identifier}|{candidate_type}'
    return hashlib.sha256(key_str.encode()).hexdigest()


def extract_observations(json_data, slug):
    """Yield normalized observation dicts from a Wave-A JSON, handling the
    multiple top-level shapes Wave-A used.

    Standard shapes (handled):
      - observations[] list
      - candidates[] list
      - candidate_identifiers[] list (alphafox02 variant)
      - identifiers[] list (nixxxo_tagfinder, opendroneid_receiver-android)
      - identifiers{} dict-of-lists (AIMSICD, eylonK14)

    Non-standard shapes (skipped, returned via skipped_count):
      - findings_catalog_51_summary, firmware_binary_mining, etc. (per-repo
        custom shapes). These ~217 observations stage in a secondary batch
        if/when their JSON shape is normalized.
    """
    # Build repo_meta for source_url construction (when obs lacks source_url)
    sm = json_data.get('source_metadata') or json_data.get('run_metadata') or {}
    repo_meta = {
        'repo_url': sm.get('repo_url') or sm.get('repo'),
        'commit_sha': sm.get('commit_sha') or sm.get('source_commit_sha'),
    }
    # Per board direction d3d1bbda 2026-05-11 + log-scan recovery 2026-05-11:
    # when source_metadata is empty but the run log captured `git rev-parse HEAD`,
    # apply the recovered SHA + repo URL as overrides.
    SHA_OVERRIDES = {
        'opendroneid_receiver-android': {
            'repo_url': 'https://github.com/opendroneid/receiver-android',
            'commit_sha': 'ed44ea3f16ce63be655454021ccda53413d13419',
        },
        'eylonK14_IMSICatcherDetector': {
            'repo_url': 'https://github.com/eylonK14/IMSICatcherDetector',
            'commit_sha': '634551457a1497a8e1dcd51128ccb673acdbdb5c',
        },
    }
    if slug in SHA_OVERRIDES:
        if not repo_meta.get('repo_url'):
            repo_meta['repo_url'] = SHA_OVERRIDES[slug]['repo_url']
        if not repo_meta.get('commit_sha'):
            repo_meta['commit_sha'] = SHA_OVERRIDES[slug]['commit_sha']
    for key in ('observations', 'candidates', 'candidate_identifiers'):
        if key in json_data and isinstance(json_data[key], list):
            for obs in json_data[key]:
                yield normalize_observation(obs, slug, list_key=key, repo_meta=repo_meta)
            return
    if 'identifiers' in json_data:
        inner = json_data['identifiers']
        if isinstance(inner, list):
            for obs in inner:
                yield normalize_observation(obs, slug, list_key='identifiers', repo_meta=repo_meta)
            return
        if isinstance(inner, dict):
            # AIMSICD / eylonK14 pattern — values can be lists or single dicts
            for sub_key, sub_val in inner.items():
                if isinstance(sub_val, list):
                    for obs in sub_val:
                        if isinstance(obs, dict):
                            yield normalize_observation(obs, slug, list_key=f'identifiers.{sub_key}', candidate_type_override=sub_key, repo_meta=repo_meta)
                elif isinstance(sub_val, dict):
                    yield normalize_observation(sub_val, slug, list_key=f'identifiers.{sub_key}', candidate_type_override=sub_key, repo_meta=repo_meta)
            return


def normalize_observation(obs, slug, list_key, candidate_type_override=None, repo_meta=None):
    """Normalize a single observation dict from any Wave-A JSON variant
    into the raw_observations row shape.

    repo_meta: optional dict of {'repo_url': ..., 'commit_sha': ...} extracted
    from the JSON's source_metadata. Used to construct source_url when the
    observation lacks one but has source_file_relative + source_line.
    """
    # Field aliases across variants
    ident = (
        obs.get('candidate_identifier')
        or obs.get('candidate_value')          # alphafox02 variant
        or obs.get('raw_extracted_value')      # rayhunter variant
        or obs.get('identifier')
        or obs.get('value')
    )
    ct = (
        obs.get('candidate_type')
        or candidate_type_override
        or obs.get('type')
    )
    cat = obs.get('candidate_category') or obs.get('category')
    mfg = obs.get('candidate_manufacturer') or obs.get('manufacturer')
    conf = obs.get('confidence') or obs.get('candidate_confidence')
    src_url = obs.get('source_url')
    src_file = obs.get('source_file_relative')
    src_line = obs.get('source_line')
    excerpt = obs.get('source_excerpt')
    obs_notes = obs.get('notes')
    ctx_before = obs.get('context_before')
    ctx_after = obs.get('context_after')

    # Construct source_url from repo_meta + source_file_relative + source_line
    # when the observation didn't include one. Per board direction d3d1bbda:
    # source_url MUST be public commit-SHA-anchored URL. Construct only when
    # commit_sha is present in repo metadata.
    if not src_url and repo_meta and repo_meta.get('repo_url') and repo_meta.get('commit_sha') and src_file:
        line_anchor = f'#L{src_line}' if src_line else ''
        src_url = f'{repo_meta["repo_url"]}/blob/{repo_meta["commit_sha"]}/{src_file}{line_anchor}'

    # Trim source_excerpt to 200 chars per identifiers schema CHECK precedent
    if excerpt and len(excerpt) > 200:
        excerpt = excerpt[:197] + '...'

    return {
        'candidate_identifier': ident,
        'candidate_type': ct,
        'candidate_category': cat,
        'candidate_manufacturer': mfg,
        'confidence': conf,
        'source_url': src_url,
        'source_file_relative': src_file,
        'source_line': src_line,
        'source_excerpt': excerpt,
        'obs_notes': obs_notes,
        'context_before': ctx_before,
        'context_after': ctx_after,
        'list_key': list_key,
    }


def main():
    # Defensive backup
    backup = f'{DB}.pre_wave_a_ingest_backup'
    if not os.path.exists(backup):
        shutil.copy(DB, backup)
        print(f'backup: {backup}')

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    print(f'pre schema_version: {c.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]}')
    print(f'pre raw_observations: {c.execute("SELECT COUNT(*) FROM raw_observations").fetchone()[0]}')
    print(f'pre sources: {c.execute("SELECT COUNT(*) FROM sources").fetchone()[0]}')
    print(f'pre extraction_runs: {c.execute("SELECT COUNT(*) FROM extraction_runs").fetchone()[0]}')

    summary = {}

    # Iterate Wave-A repos
    for slug, src_meta in WAVE_A_SOURCES.items():
        repo_dir = f'{WAVE_A_DIR}/{slug}'
        if not os.path.isdir(repo_dir):
            print(f'SKIP {slug}: dir missing')
            continue
        json_files = [f for f in os.listdir(repo_dir) if f.endswith('.json')]
        if not json_files:
            print(f'SKIP {slug}: no JSON')
            continue
        json_path = f'{repo_dir}/{json_files[0]}'
        try:
            data = json.load(open(json_path))
        except Exception as e:
            print(f'SKIP {slug}: JSON parse error: {e}')
            continue

        # Register source (idempotent — INSERT OR IGNORE on url UNIQUE)
        c.execute(
            "INSERT OR IGNORE INTO sources (name, url, source_type, tier, last_fetched_at, last_status, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (src_meta['name'], src_meta['url'], src_meta['source_type'], src_meta['tier'], NOW, 'ok',
             f'Wave-A repo registered 2026-05-11 via wave_a_ingest_to_raw_observations.py per MAC-63 board direction d3d1bbda (Path B). Slug: {slug}')
        )
        src_row = c.execute("SELECT id FROM sources WHERE url=?", (src_meta['url'],)).fetchone()
        src_id = src_row[0]

        # Extract observations
        observations = list(extract_observations(data, slug))
        valid_obs = [o for o in observations if o['candidate_identifier'] and o['source_url']]
        skipped_obs = len(observations) - len(valid_obs)

        # Register extraction_run
        c.execute(
            "INSERT INTO extraction_runs (agent_id, source_id, started_at, finished_at, records_in, records_out, errors, status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (AGENT_ID, src_id, NOW, NOW, len(observations), len(valid_obs), skipped_obs, 'ok',
             f'Wave-A {slug} mechanical ingestion. Source JSON: {json_path}. Per MAC-63 board direction d3d1bbda 2026-05-11 (Path B). Skipped {skipped_obs} obs lacking candidate_identifier or source_url.')
        )
        run_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Insert raw_observations rows
        inserted = 0
        duplicates = 0
        type_normalized = 0
        for o in valid_obs:
            normalized_ct, was_normalized = normalize_candidate_type(o['candidate_type'])
            if was_normalized:
                type_normalized += 1

            # Build notes JSON with file/line provenance per board direction
            # (local artifact path goes here, NEVER as source_url)
            notes = {
                'wave_a_surfacing_path': json_path,
                'wave_a_list_key': o['list_key'],
                'source_file_relative': o['source_file_relative'],
                'source_line': o['source_line'],
                'context_before': o['context_before'],
                'context_after': o['context_after'],
                'obs_notes': o['obs_notes'],
                'wave_a_repo_url': src_meta['url'],
            }
            if was_normalized:
                notes['candidate_type_original'] = o['candidate_type']
                notes['candidate_type_normalized'] = normalized_ct

            row_key = source_row_key(o['source_url'], o['candidate_identifier'], normalized_ct)

            # Check for duplicate by source_row_key
            existing = c.execute("SELECT id FROM raw_observations WHERE source_row_key=?", (row_key,)).fetchone()
            if existing:
                duplicates += 1
                continue

            c.execute(
                """INSERT INTO raw_observations
                   (source_id, extraction_run_id, source_url, raw_payload,
                    candidate_identifier, candidate_type, candidate_category, candidate_manufacturer,
                    source_excerpt, captured_at, notes, source_row_key)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (src_id, run_id, o['source_url'], None,
                 o['candidate_identifier'], normalized_ct, o['candidate_category'], o['candidate_manufacturer'],
                 o['source_excerpt'], NOW, json.dumps(notes), row_key)
            )
            inserted += 1

        summary[slug] = {
            'src_id': src_id,
            'run_id': run_id,
            'observations_in_json': len(observations),
            'valid_obs': len(valid_obs),
            'skipped_missing_fields': skipped_obs,
            'inserted': inserted,
            'duplicates_skipped': duplicates,
            'type_normalized': type_normalized,
        }
        print(f'  {slug}: src_id={src_id} run_id={run_id} json={len(observations)} valid={len(valid_obs)} inserted={inserted} dup={duplicates} type_norm={type_normalized}')

    # Final verification
    conn.commit()
    print()
    print(f'post raw_observations: {c.execute("SELECT COUNT(*) FROM raw_observations").fetchone()[0]}')
    print(f'post sources: {c.execute("SELECT COUNT(*) FROM sources").fetchone()[0]}')
    print(f'post extraction_runs: {c.execute("SELECT COUNT(*) FROM extraction_runs").fetchone()[0]}')
    print(f'integrity_check: {c.execute("PRAGMA integrity_check").fetchall()}')
    print(f'foreign_key_check: {c.execute("PRAGMA foreign_key_check").fetchall()}')

    # Summary by candidate_type
    print()
    print('=== Cumulative candidate_type distribution (raw_observations, source_id >= 16) ===')
    for r in c.execute("SELECT candidate_type, COUNT(*) FROM raw_observations WHERE source_id >= 16 GROUP BY candidate_type ORDER BY 2 DESC").fetchall():
        print(f'  {r[0]}: {r[1]}')

    conn.close()
    return summary


if __name__ == '__main__':
    main()
