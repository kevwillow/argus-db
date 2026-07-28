"""MAC-523 Phase 1 — extract OUI candidates from Phase 1 raw, run all four kill tests,
re-query canonical DB for net-new confirmation, write deliverable JSONs.

Reuses Phase 0's proven regex/discipline (extract_and_netnew.py + adjudicate.py)
adapted to read extraction_outputs/mac523_phase1/shodan_raw/.
"""
import json, re, pathlib, sqlite3, collections, sys

RAW = pathlib.Path("extraction_outputs/mac523_phase1/shodan_raw")
OUT_DIR = pathlib.Path("extraction_outputs/mac523_phase1")

# Proven Phase 0 regexes — word-boundary-correct to avoid the `classid` SSID FP
MAC_DELIM = re.compile(r'(?<![0-9A-Fa-f:\-])([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}|[0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){5})(?![0-9A-Fa-f:\-])')
SSID_KEY  = re.compile(r'(?<![A-Za-z])ssid["\']?\s*[:=]\s*["\']?([^"\',;\r\n<]{1,32})', re.I)
UDN_RE    = re.compile(r'"udn"\s*:\s*"uuid:([0-9a-fA-F\-]{36})"')

# Pass 1 — extract MACs / UUIDs / model metadata from raw responses
mac_src = collections.defaultdict(set)  # MAC -> set of (module, file) origins
ssid_hits = []
udn_vals = []
udn_owner = collections.defaultdict(set)  # UDN -> set of manufacturer strings
recs = 0
files_processed = []
for f in sorted(RAW.glob("*.json")):
    if f.name.startswith("_"):  # skip _summary.json
        continue
    files_processed.append(f.name)
    body = json.loads(f.read_text())
    if not isinstance(body, dict) or "matches" not in body:
        continue
    for m in body["matches"]:
        recs += 1
        blob = json.dumps(m)
        for g in MAC_DELIM.finditer(blob):
            mac_src[g.group(1).upper().replace("-", ":")].add(((m.get("_shodan") or {}).get("module"), f.name))
        for g in SSID_KEY.finditer(blob):
            ssid_hits.append((g.group(1), blob[max(0, g.start()-80):g.end()+40]))
        for g in UDN_RE.finditer(blob):
            udn_vals.append((g.group(1), (m.get("_shodan") or {}).get("module"), blob[max(0, g.start()-140):g.end()+40]))
        mfr = ((m.get("upnp") or {}).get("manufacturer") or m.get("product") or "?").strip()
        for g in UDN_RE.finditer(blob):
            udn_owner[g.group(1)].add(mfr)

print(f"records scanned            : {recs}")
print(f"SSID hits (boundary-correct): {len(ssid_hits)}   <-- 0 expected per Phase 0")
print(f"delimited MACs   distinct  : {len(mac_src)}")

# UUIDv1 node-part -> MAC (RFC 4122: version nibble == '1' at position 14)
udn_mac = {}
for u, mod, ctx in udn_vals:
    parts = u.split("-")
    if len(parts) == 5 and parts[2][0] == "1":
        node = parts[4].upper()
        udn_mac[":".join(node[i:i+2] for i in range(0, 12, 2))] = (u, ctx, mod)

print(f"UPnP UDN values            : {len(udn_vals)} (distinct {len({u for u,_,_ in udn_vals})}); UUIDv1 w/ MAC node-part: {len(udn_mac)}")

all_macs = {**{k: (None, None, None) for k in mac_src}, **udn_mac}
ouis = sorted({m[:8].replace(":", "") for m in all_macs})
print(f"\ndistinct OUI candidates    : {len(ouis)} -> {ouis[:20]}{'...' if len(ouis) > 20 else ''}")

# Pass 2 — IEEE bit test
def bits(oui):
    b = int(oui[:2], 16)
    return ("MULTICAST-invalid" if b & 1 else ("LOCALLY-ADMIN-invalid" if b & 2 else "unicast/global-OK"))

oui_verdict = {o: bits(o) for o in ouis}
killed_bit = [o for o in ouis if oui_verdict[o] != "unicast/global-OK"]
print(f"\n--- IEEE bit test ---")
print(f"killed by bit test (multicast or locally-admin): {len(killed_bit)} -> {killed_bit}")

# Pass 3 — IEEE MA-L resolution
ieee_path = pathlib.Path("raw/ieee_oui/oui_20260728T213418Z.txt")
ieee_assignees = {}
with ieee_path.open() as f:
    for line in f:
        if "(hex)" in line:
            parts = line.split()
            if len(parts) >= 3:
                # format: "XX-XX-XX   (hex)\t\tVendor Name"
                hex_prefix = parts[0].replace("-", "").upper()
                # take everything after (hex) as the assignee
                idx = line.find("(hex)")
                if idx >= 0:
                    assignee = line[idx:].split("\t", 1)[-1].strip()
                    if assignee:
                        ieee_assignees[hex_prefix] = assignee

print(f"\n--- IEEE MA-L resolution ---")
print(f"IEEE MA-L registry entries loaded: {len(ieee_assignees)}")

not_in_ieee = [o for o in ouis if o not in ieee_assignees]
print(f"OUI candidates absent from MA-L: {len(not_in_ieee)} -> {not_in_ieee}")

# Pass 4 — SDK-default hub dedup (UDN observed under >1 manufacturer)
sdk_hub_udns = {u: sorted(owners) for u, owners in udn_owner.items() if len(owners) > 1}
sdk_hub_node_parts = set()
for u in sdk_hub_udns:
    parts = u.split("-")
    if len(parts) == 5 and parts[2][0] == "1":
        sdk_hub_node_parts.add(parts[4][:6].upper())
print(f"\n--- SDK-default hub dedup ---")
print(f"UDN values observed under >1 manufacturer: {len(sdk_hub_udns)}")
for u, owners in list(sdk_hub_udns.items())[:5]:
    print(f"  {u}  -> {owners}")
print(f"OUI-prefixes from SDK-default hubs: {len(sdk_hub_node_parts)} -> {sorted(sdk_hub_node_parts)}")

# Pass 5 — canonical DB net-new check (READ-ONLY)
con = sqlite3.connect("file:db/argus.db?mode=ro", uri=True)
held = []
absent = []
survivors = []
killed = {
    "bit_test": killed_bit,
    "not_in_ieee": not_in_ieee,
    "sdk_hub": sorted(sdk_hub_node_parts),
}

for o in ouis:
    if o in killed_bit:
        continue
    if o in not_in_ieee:
        continue
    if o in sdk_hub_node_parts:
        continue
    r = con.execute(
        """SELECT identifier, manufacturer, device_category FROM identifiers
           WHERE identifier_type='oui' AND superseded_by IS NULL
           AND REPLACE(REPLACE(UPPER(identifier),':',''),'-','')=?""",
        (o,)).fetchone()
    if r:
        held.append({"oui": o, "identifier": r[0], "manufacturer": r[1], "device_category": r[2]})
    else:
        absent.append(o)
        survivors.append(o)

print(f"\n--- NET-NEW FLOOR (vs {con.execute('SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL').fetchone()[0]} active rows) ---")
print(f"ALREADY HELD n={len(held)}")
for h in held: print(f"   {h['oui']}  held as {h['identifier']!r} mfr={h['manufacturer']!r} cat={h['device_category']!r}")
print(f"ABSENT / net-new candidate n={len(absent)} -> {absent}")

# Write deliverables
candidates = []
for o in survivors:
    # gather evidence + manufacturer + model from each match
    evidence_chunks = []
    manufacturers = set()
    model_names = set()
    model_descs = set()
    channels = set()
    shodan_query = None
    observed_count = 0
    for f in sorted(RAW.glob("*.json")):
        if f.name.startswith("_"): continue
        body = json.loads(f.read_text())
        if not isinstance(body, dict) or "matches" not in body: continue
        for m in body["matches"]:
            blob = json.dumps(m)
            hit = False
            channel = None
            for g in MAC_DELIM.finditer(blob):
                if g.group(1).upper().replace("-", ":")[:8].replace(":", "") == o:
                    evidence_chunks.append(blob[max(0, g.start()-60):g.end()+60])
                    hit = True
                    channel = "banner-literal"
            for g in UDN_RE.finditer(blob):
                parts = g.group(1).split("-")
                if len(parts) == 5 and parts[2][0] == "1":
                    node = parts[4].upper()
                    mac = ":".join(node[i:i+2] for i in range(0,12,2))
                    if mac[:8].replace(":", "") == o:
                        evidence_chunks.append(blob[max(0, g.start()-60):g.end()+60])
                        hit = True
                        channel = "uuidv1-node"
            if hit:
                observed_count += 1
                upnp = m.get("upnp") or {}
                if upnp.get("manufacturer"): manufacturers.add(upnp["manufacturer"].strip())
                if upnp.get("model_name"): model_names.add(upnp["model_name"].strip())
                if upnp.get("model_description"): model_descs.add(upnp["model_description"].strip())
                if channel: channels.add(channel)
                # capture the query name from filename
                shodan_query = shodan_query or f.name

    candidates.append({
        "oui": o,
        "ieee_assignee": ieee_assignees.get(o, "?"),
        "channel": sorted(channels) or ["unknown"],
        "evidence_bytes": evidence_chunks[0] if evidence_chunks else "",
        "manufacturer": sorted(manufacturers),
        "model_name": sorted(model_names),
        "model_description": sorted(model_descs),
        "shodan_query": shodan_query,
        "observed_count": observed_count,
    })

# Build killed.json entries
killed_json = {
    "bit_test": killed_bit,
    "not_in_ieee": not_in_ieee,
    "sdk_hub_udns": [{"udn": u, "manufacturers": owners} for u, owners in sdk_hub_udns.items()],
    "sdk_hub_node_parts": sorted(sdk_hub_node_parts),
    "already_held": held,
    "summary": {
        "total_oui_candidates": len(ouis),
        "killed_bit_test": len(killed_bit),
        "killed_not_in_ieee": len(not_in_ieee),
        "killed_sdk_hub": len(sdk_hub_node_parts),
        "killed_already_held": len(held),
        "net_new_survivors": len(survivors),
    }
}

(OUT_DIR / "candidates_oui.json").write_text(json.dumps(candidates, indent=1))
(OUT_DIR / "killed.json").write_text(json.dumps(killed_json, indent=1))
print(f"\nWrote {OUT_DIR / 'candidates_oui.json'} ({len(candidates)} rows)")
print(f"Wrote {OUT_DIR / 'killed.json'}")
