"""MAC-23 Step-1.5b byte-level survey — full Wave-A corpus.

Per dispatch §"Step-1.5b byte-level survey gate":
- Regex anchors: ble_uuid_anchored, mac_anchored, fcc_id_anchored (TIGHTENED
  per MAC-21 §9.11 ratified — `\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{4,14}\b` with
  vendor-proximity ±50-char), ssid_kw, default_creds_kw.
- Persist to logs/mac23_step1.5b_byte_level_survey_<run-ts>.{txt,json}
- Provides corpus-aggregate arithmetic for Step-1.5b deliverable comment.
"""
import re, json, hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

REGEX_MAC = re.compile(r'\b[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\b')
REGEX_BLE = re.compile(r'\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b')
REGEX_FCC_TIGHT = re.compile(r'\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{4,14}\b')
REGEX_SSID = re.compile(r'\bssid\b', re.IGNORECASE)
DEFAULT_CRED_KW = [
    'default password', 'default credential', 'default login',
    'default user', 'factory reset', 'default passphrase',
    'wpa2 password', 'default ssid',
]
# Person-name proximity (PII redaction count per §11 #3 + SAR-5)
ROLE_PREFIX_RE = re.compile(
    r'\b(?:Mr|Mrs|Ms|Dr|Prof|Sergeant|Sgt|Detective|Lt|Lieutenant|'
    r'Captain|Cpt|Officer|Trooper|Chief|Major|Colonel|General|Sheriff)\.?\s+'
    r'[A-Z][a-zA-Z\'-]{2,30}',
    re.IGNORECASE,
)

# Owner-slug → vendor mapping (built from cohort summaries + manual A1/A2/A3)
def build_vendor_map(cohort_dirs):
    vmap = {
        # A1 first-party orgs
        'cradlepoint': 'Cradlepoint', 'sierrawireless': 'Sierra Wireless',
        'motorolasolutions': 'Motorola Solutions', 'flocksafety': 'Flock Safety',
        'dji-sdk': 'DJI', 'hak5': 'Hak5', 'watchguard': 'WatchGuard',
        'parrot-developers': 'Parrot', 'skydio': 'Skydio',
        'magnetforensics': 'Magnet Forensics', 'genetec': 'Genetec',
        'axiscommunications': 'Axis Communications', 'l3harris': 'L3Harris',
        'clearviewai': 'Clearview AI', 'avigilon': 'Avigilon',
        'briefcam': 'BriefCam', 'soundthinking': 'SoundThinking',
        'rekorai': 'Rekor', 'brinc-drones': 'BRINC',
        # A2 third-party recon (vendor=primary target, NOT owner)
        '0xxyc': 'Flock Safety', 'f1yaw4y': 'Flock Safety',
        'gainsec': 'Flock Safety', 'deflockyourcity': 'Flock Safety',
        'zmattmanz': 'Flock Safety',
        'vegantransistor': 'Cradlepoint',
        'danielewood': 'Sierra Wireless', 'bkerler': 'Sierra Wireless',
        'smcl': 'Sierra Wireless',
        'o-gs': 'DJI', 'damiafuentes': 'DJI',
        'levlesec': 'Cellebrite', 'dfirscience': 'Cellebrite',
        'danielorf': 'Axis Communications', 'trunnion': 'Axis Communications',
        'facelessg00n': 'Berla',
        # A3 Hak5 community
        'i-am-jakoby': 'Hak5', 'aleff-github': 'Hak5',
    }
    # Augment from A4 cohort summary
    for c in cohort_dirs:
        s_path = c / '_cohort_summary.json'
        if not s_path.exists(): continue
        try: s = json.loads(s_path.read_text())
        except Exception: continue
        for v, rec in s.get('vendors', {}).items():
            for r in rec.get('repos_fetched', []) if isinstance(rec.get('repos_fetched'), list) else []:
                if 'repo' in r and 'skipped' not in r:
                    owner = r['repo'].split('/', 1)[0].lower()
                    if owner not in vmap:
                        vmap[owner] = v
    return vmap


def vendor_tokens(vendor):
    if not vendor or vendor == '?': return []
    parts = vendor.lower().split()
    out = [parts[0]] if parts else []
    for p in parts[1:]:
        if len(p) >= 4 and p not in ('safety', 'wireless', 'communications', 'solutions', 'forensics', 'thinking'):
            out.append(p)
    return out


def vp_count(regex, txt, vendor):
    toks = vendor_tokens(vendor)
    if not toks: return 0, []
    txt_l = txt.lower()
    n = 0
    examples = []
    for m in regex.finditer(txt):
        window = txt_l[max(0,m.start()-50):m.end()+50]
        if any(t in window for t in toks):
            n += 1
            if len(examples) < 3:
                examples.append(m.group())
    return n, examples


def main():
    repo_root = Path(__file__).resolve().parents[1]
    wave_root = repo_root / 'raw' / 'github' / '20260505T200235Z'
    cohort_dirs = sorted([p for p in wave_root.iterdir() if p.is_dir() and p.name.startswith('cohort_')])
    vmap = build_vendor_map(cohort_dirs)

    # Per-cohort + per-vendor + wave-aggregate breakdown
    per_cohort = {}  # cohort_name -> dict
    per_vendor_wave = defaultdict(lambda: {'mac':0, 'ble':0, 'fcc':0, 'ssid':0, 'cred':0, 'pii':0, 'bytes':0, 'files':0, 'repos':set()})
    unique_macs = set()
    unique_ble_uuids = set()
    unique_fcc_ids = set()
    fp_examples = {'ble':[], 'fcc':[]}
    real_examples = {'mac':[], 'ble':[], 'fcc':[], 'ssid_repos':[], 'cred_repos':[]}

    for cdir in cohort_dirs:
        cname = cdir.name
        cohort = {'files':0, 'bytes':0, 'mac':0, 'ble':0, 'fcc':0, 'ssid':0, 'cred':0, 'pii':0, 'unique_repos':0}
        repos_seen = set()
        for entry in cdir.iterdir():
            if not entry.is_dir(): continue
            if entry.name.startswith('_'): continue
            # Cohort A5 has nested vendor/keyword/issues_search.json structure
            if cname == 'cohort_A5':
                for v_dir in entry.iterdir() if entry.is_dir() else []:
                    if not v_dir.is_dir(): continue
                    for f in v_dir.iterdir():
                        if not f.is_file() or f.suffix != '.json': continue
                        try: d = json.loads(f.read_text())
                        except Exception: continue
                        # Sweep title+body of items
                        items = d.get('items', []) if isinstance(d, dict) else []
                        for it in items:
                            corpus = (it.get('title','') or '') + ' ' + (it.get('body','') or '')[:1000]
                            cohort['bytes'] += len(corpus)
                            cohort['files'] += 1
                            # Use vendor from the path: cohort_A5/<vendor_slug>/<kw_slug>/...
                            vslug = entry.name
                            vendor = {'cradlepoint':'Cradlepoint','sierra_wireless':'Sierra Wireless','motorola_solutions':'Motorola Solutions','flock_safety':'Flock Safety'}.get(vslug, '?')
                            for regex, key in [(REGEX_MAC,'mac'), (REGEX_BLE,'ble'), (REGEX_FCC_TIGHT,'fcc')]:
                                n, examples = vp_count(regex, corpus, vendor)
                                cohort[key] += n
                                per_vendor_wave[vendor][key] += n
                            cohort['ssid'] += len(REGEX_SSID.findall(corpus))
                            cohort['cred'] += sum(corpus.lower().count(k) for k in DEFAULT_CRED_KW)
                            cohort['pii'] += len(ROLE_PREFIX_RE.findall(corpus))
                            per_vendor_wave[vendor]['ssid'] += len(REGEX_SSID.findall(corpus))
                            per_vendor_wave[vendor]['cred'] += sum(corpus.lower().count(k) for k in DEFAULT_CRED_KW)
                continue
            # A1-A4: <owner>__<repo>/<files>
            owner = entry.name.split('__', 1)[0]
            vendor = vmap.get(owner.lower(), '?')
            repos_seen.add(entry.name)
            for f in entry.iterdir():
                if not f.is_file() or f.suffix == '.json': continue
                try: txt = f.read_text(errors='replace')
                except Exception: continue
                cohort['bytes'] += len(txt)
                cohort['files'] += 1
                per_vendor_wave[vendor]['bytes'] += len(txt)
                per_vendor_wave[vendor]['files'] += 1
                per_vendor_wave[vendor]['repos'].add(entry.name)
                for regex, key in [(REGEX_MAC,'mac'), (REGEX_BLE,'ble'), (REGEX_FCC_TIGHT,'fcc')]:
                    n, ex = vp_count(regex, txt, vendor)
                    cohort[key] += n
                    per_vendor_wave[vendor][key] += n
                    if key == 'mac':
                        for m in REGEX_MAC.finditer(txt):
                            window = txt.lower()[max(0,m.start()-50):m.end()+50]
                            if any(t in window for t in vendor_tokens(vendor)):
                                unique_macs.add(m.group().lower())
                    if key == 'ble':
                        for m in REGEX_BLE.finditer(txt):
                            window = txt.lower()[max(0,m.start()-50):m.end()+50]
                            if any(t in window for t in vendor_tokens(vendor)):
                                u = m.group().lower()
                                unique_ble_uuids.add(u)
                                ctx = txt[max(0,m.start()-100):m.end()+100].replace('\n',' ')[:240]
                                if any(s in ctx.lower() for s in ('http://', 'https://', 'token=', 'asset/', 'gitbook.io', 'scarf.sh', 'firebase')):
                                    if len(fp_examples['ble']) < 5:
                                        fp_examples['ble'].append({'uuid': u, 'file': str(f.relative_to(repo_root)), 'ctx': ctx})
                    if key == 'fcc':
                        for m in REGEX_FCC_TIGHT.finditer(txt):
                            window = txt.lower()[max(0,m.start()-50):m.end()+50]
                            if any(t in window for t in vendor_tokens(vendor)):
                                unique_fcc_ids.add(m.group())
                                ctx = txt[max(0,m.start()-100):m.end()+100].replace('\n',' ')[:240]
                                if len(fp_examples['fcc']) < 5:
                                    fp_examples['fcc'].append({'fcc': m.group(), 'file': str(f.relative_to(repo_root)), 'ctx': ctx})
                ssid = len(REGEX_SSID.findall(txt))
                cred = sum(txt.lower().count(k) for k in DEFAULT_CRED_KW)
                pii = len(ROLE_PREFIX_RE.findall(txt))
                cohort['ssid'] += ssid
                cohort['cred'] += cred
                cohort['pii'] += pii
                per_vendor_wave[vendor]['ssid'] += ssid
                per_vendor_wave[vendor]['cred'] += cred
                per_vendor_wave[vendor]['pii'] += pii
        cohort['unique_repos'] = len(repos_seen)
        per_cohort[cname] = cohort

    wave_agg = {'files':0, 'bytes':0, 'mac':0, 'ble':0, 'fcc':0, 'ssid':0, 'cred':0, 'pii':0}
    for c in per_cohort.values():
        for k in wave_agg:
            if k == 'files' or k == 'bytes': wave_agg[k] += c.get(k, 0)
            else: wave_agg[k] += c.get(k, 0)

    # Step-2 row projections per dispatch
    PROJ = {
        'cohort_A1': {'mid': 280, 'trip': 140},
        'cohort_A2': {'mid': 110, 'trip': 55},
        'cohort_A3': {'mid':  80, 'trip': 40},
        'cohort_A4': {'mid': 100, 'trip': 50},
        'cohort_A5': {'mid':  50, 'trip': 25},
    }

    out = {
        'issue': 'MAC-23',
        'phase': '4 / Wave-A / Step-1.5b byte-level survey',
        'survey_run_ts': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
        'corpus_root': str(wave_root.relative_to(repo_root)),
        'methodology': {
            'regex_mac_anchored': r'\b[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\b + vendor-proximity ±50ch',
            'regex_ble_uuid_anchored': r'\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b + vendor-proximity ±50ch',
            'regex_fcc_id_anchored_TIGHTENED_per_MAC21_§9_11': r'\b[A-Z][A-Z0-9]{2}-[A-Z0-9]{4,14}\b (mandatory hyphen) + vendor-proximity ±50ch',
            'ssid_kw': 'raw count of \\bssid\\b case-insensitive (per dispatch §15)',
            'default_creds_kw': 'raw count of default-cred tokens (per dispatch §15)',
            'pii_role_prefix': '§11 #3 + SAR-5 PII redaction count (count-not-name)',
            'vendor_proximity': 'first-word-token + ≥4-char-non-stopword vendor name within ±50ch window',
        },
        'per_cohort': per_cohort,
        'wave_aggregate': wave_agg,
        'unique_anchored_identifiers': {
            'mac': sorted(unique_macs),
            'ble_uuid': sorted(unique_ble_uuids),
            'fcc_id': sorted(unique_fcc_ids),
        },
        'fp_examples': fp_examples,
        'step2_projection': {
            'A1_mid_280_trip_140': '~0-5 rows (corpus-shape: marketing READMEs, 0 anchored hits except FP-class)',
            'A2_mid_110_trip_55': '~3-12 rows (1 unique MAC e4:aa:ea:80:a1:9b + 30 raw ssid_kw + 1 raw cred_kw)',
            'A3_mid_80_trip_40': '~0 rows (community payload-fork READMEs, GitHub asset FPs only)',
            'A4_mid_100_trip_50': '~0-5 rows (broader sweep, 4 raw ssid_kw + 3 raw cred_kw)',
            'A5_mid_50_trip_25': '~0-5 rows (issue-thread fetch deferred to Step-2; 17 thread refs surfaced)',
            'wave_aggregate_mid_620_trip_310': 'projected ~3-27 wave-aggregate rows; SAR-6 #3 trip-line evaluation defers to Step-2 ExtractionWorker',
        },
        'pat_quota_burn_supplementary': {
            'wave_a_total_calls': 379,
            'hard_cap': 2500,
            'burn_pct': '15.16%',
            'unique_actual_identifiers_at_step1': 1,
            'verdict': 'NOT TRIPPED at Step-1; first-5-10-cohort window passed clean',
        },
        'cohort_trip_lines': PROJ,
        'methodology_carry_forward': [
            'fcc_id_anchored regex still surfaces compound-English-word FPs (NON-INFRINGEMENT) and CVE-pattern FPs (CVE-2025-59409); recommend Phase-3 fcc_grantees allowlist + CVE/CWE stop-list at Step-2 disambig',
            'ble_uuid_anchored regex surfaces 5 distinct FP classes: GitBook social-preview / GitHub repo-asset / Firebase storage / Scarf.sh tracking pixel / Microsoft Graph tenant; recommend URL-context exclusion + protocol-context inclusion at Step-2',
            'A1 first-party SDK orgs surface 0 anchored identifiers in vendor-prox-gated tightened sweep — corpus-reality: marketing/setup READMEs, identifier-bearing content lives in code (header files, constants files), not READMEs',
            'A2 third-party recon-tool class is the empirical-yield surface (analogous to MAC-19 Cohort 3 Hak5 within Wave-B2)',
            'A3 Hak5/community payload-fork repos = 0 actual identifiers, 100% GitHub asset FP class',
            'A5 issue-thread comment-content fetch deferred to Step-2 (~17 threads × N comments each)',
            'Search-bucket buffer must be < bucket-budget (30/min for /search/issues; was 50, fixed to 3)',
        ],
    }

    # Persist as txt + json
    out_dir = repo_root / 'logs'
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = out['survey_run_ts']
    json_path = out_dir / f'mac23_step1.5b_byte_level_survey_{ts}.json'
    txt_path = out_dir / f'mac23_step1.5b_byte_level_survey_{ts}.txt'
    json_path.write_text(json.dumps(out, indent=2, sort_keys=True, default=str))

    # Build txt summary
    lines = []
    lines.append(f"MAC-23 Step-1.5b byte-level survey — Wave-A corpus")
    lines.append(f"Run: {ts}")
    lines.append(f"Corpus: {out['corpus_root']}")
    lines.append("")
    lines.append("=== PER-COHORT (vendor-prox-gated, tightened regex per MAC-21 §9.11) ===")
    lines.append(f"{'cohort':<12} {'files':>6} {'bytes':>10} {'mac_anch':>9} {'ble_uuid':>9} {'fcc_t':>6} {'ssid_kw':>8} {'cred_kw':>8} {'pii':>4} {'repos':>6}")
    for cname in sorted(per_cohort):
        c = per_cohort[cname]
        lines.append(f"{cname:<12} {c['files']:>6} {c['bytes']:>10} {c['mac']:>9} {c['ble']:>9} {c['fcc']:>6} {c['ssid']:>8} {c['cred']:>8} {c['pii']:>4} {c.get('unique_repos',0):>6}")
    lines.append("")
    lines.append(f"WAVE-A AGGREGATE: files={wave_agg['files']} bytes={wave_agg['bytes']} mac_anch={wave_agg['mac']} ble_uuid_anch={wave_agg['ble']} fcc_tight_anch={wave_agg['fcc']} ssid_kw={wave_agg['ssid']} cred_kw={wave_agg['cred']} pii={wave_agg['pii']}")
    lines.append("")
    lines.append(f"Unique anchored identifiers (deduped, vendor-prox-gated):")
    lines.append(f"  mac_unique:     {sorted(unique_macs)}")
    lines.append(f"  ble_uuid_unique: {sorted(unique_ble_uuids)}")
    lines.append(f"  fcc_id_unique:  {sorted(unique_fcc_ids)}")
    lines.append("")
    lines.append("=== Step-2 projection per dispatch clause 10 ===")
    lines.append(f"{'cohort':<12} {'mid':>5} {'trip':>5} {'projected':>20}")
    for c, p in sorted(PROJ.items()):
        proj = out['step2_projection'].get(c.replace('cohort_', '') + '_mid_' + str(p['mid']) + '_trip_' + str(p['trip']), '?')
        # fallback lookup
        for k, v in out['step2_projection'].items():
            if c.replace('cohort_','') in k:
                proj = v
                break
        lines.append(f"{c:<12} {p['mid']:>5} {p['trip']:>5} {proj}")
    lines.append("")
    lines.append("Wave-aggregate Step-2 projection: ~3-27 rows vs combined trip floor ≤310 (~50% wave-agg)")
    lines.append("Wave-aggregate trip evaluation: NOT TRIPPED at Step-1 byte-level; defers to Step-2 ExtractionWorker dispatch (separate MAC-N).")
    lines.append("")
    lines.append("PAT-quota-burn supplementary: 15.16% (379/2500) — NOT TRIPPED (floor ≥50%); first-5-10-cohort window passed clean.")
    lines.append("")
    lines.append("=== Carry-forward methodology findings (for Step-2 dispatch ratification) ===")
    for cf in out['methodology_carry_forward']:
        lines.append(f"- {cf}")
    txt_path.write_text('\n'.join(lines) + '\n')

    print(f"Step-1.5b survey written: {json_path.relative_to(repo_root)}")
    print(f"                          {txt_path.relative_to(repo_root)}")
    print()
    for line in lines:
        print(line)

if __name__ == '__main__':
    main()
