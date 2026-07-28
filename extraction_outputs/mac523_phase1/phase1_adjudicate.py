"""MAC-523 Phase 1 — final adjudication (5th kill test = entity-boundary / surveillance-class binding).

Per PHASE0_REPORT.md §4-§5, the entity-boundary check is a MANUAL review.
Phase 1's evidence is mixed (broad `upnp` query hit web admin UIs, Linux bridges,
consumer electronics in addition to surveillance devices). Automated terms over-fire
on common UPnP fields, so this script applies the manual decisions and records the
reasoning for each OUI.

Reads:  extraction_outputs/mac523_phase1/candidates_oui.json  (24 net-new from extract)
        extraction_outputs/mac523_phase1/shodan_raw/*.json    (raw Shodan responses)
        extraction_outputs/mac523_phase1/killed.json          (extract kills: bit/MA-L/SDK-hub/held)
Writes: extraction_outputs/mac523_phase1/candidates_oui.json  (final, with device_category)
        extraction_outputs/mac523_phase1/killed.json           (with entity_boundary kills)
        extraction_outputs/mac523_phase1/run_log.md            (appended with adjudication)
"""
import json, pathlib

OUT_DIR = pathlib.Path("extraction_outputs/mac523_phase1")
RAW = OUT_DIR / "shodan_raw"

# Manual disposition per OUI — entity-boundary / surveillance-class binding.
# Each entry: disposition -> ("keep", "unknown", "cctv_camera") + reason
MANUAL = {
    # ---- KEEP (surveillance-class, model-bound to camera/DVR/NVR) ----
    "000E53": ("cctv_camera", "AV TECH CORPORATION — Product.Type=DVR observed in evidence (cmd.php page); single-product surveillance vendor per §2.1"),
    "00115F": ("cctv_camera", "ITX Security Co., Ltd. — Network Camera model observed; Phase 0 confirmed"),
    "001B9D": ("cctv_camera", "Novus Security Sp. z o.o. — model_name 'DVR (192.168.10.10)' observed; Novus is surveillance vendor"),
    "001C27": ("cctv_camera", "Sunell Electronics — model EN-CDUM-008-2 (Eagle Eye Networks bridge) observed; Sunell is CCTV manufacturer"),
    "00224E": ("cctv_camera", "SEEnergy Corp. — model_description 'Network Video Recorder' observed"),
    "64255E": ("cctv_camera", "Observint (Alibi brand) — model AC-VS-NC114FA observed; Alibi is Observint's surveillance brand"),
    "E061B2": ("cctv_camera", "HANGZHOU ZENOINTEL TECHNOLOGY — model 'DVR/Tilt' observed across 109 unique hosts; high-density deployment indicator"),

    # ---- KEEP at unknown (multi-purpose vendor / general block) ----
    "002401": ("unknown",     "D-Link Corporation — no model bound; general-vendor block per §11 #10"),
    "0080F0": ("unknown",     "Panasonic Communications Co., Ltd. — Network Camera model observed; multi-purpose vendor per §11 #10 (Phase 0 confirmed)"),
    "00A784": ("cctv_camera", "ITX security — Network Camera model observed; single-product surveillance vendor (Phase 0 confirmed)"),
    "080023": ("unknown",     "Panasonic Communications Co., Ltd. — Network Camera / i-PRO Network Camera observed; multi-purpose vendor per §11 #10 (Phase 0 confirmed)"),
    "B0C554": ("unknown",     "D-Link International — Outdoor Day & Night Dome Network Camera / Outdoor Bullet Network Camera observed; general-vendor block per dispatch rule (Phase 0 confirmed)"),
    "BCC342": ("unknown",     "Panasonic Communications Co., Ltd. — Network Camera / i-PRO Network Camera observed; multi-purpose vendor per §11 #10 (Phase 0 confirmed)"),

    # ---- KILL (entity-boundary / non-surveillance class) ----
    "000000": ("kill", "XEROX CORPORATION (IEEE registry) — but American Dynamics Inc. VideoEdge NVR observed in same OUI match. OUI not registered to AD; likely placeholder MAC in NVR config (00:00:00:XX:XX:XX pattern) — not real NIC assignment. Entity-boundary kill."),
    "000100": ("kill", "EQUIP'TRANS — evidence contains `docker0\\ngateway\\nether\\n00:01:00:01:00:01` (Linux bridge / veth interface); software-defined interface MAC, not device identity. Entity-boundary kill."),
    "001788": ("kill", "Philips Lighting BV (Signify) — model 'Philips hue bridge 2015' / 'Philips hue Personal Wireless Lighting' observed; consumer smart-home lighting, NOT surveillance. Non-surveillance class."),
    "001C7F": ("kill", "Check Point Software Technologies — evidence contains `managedBySmp`, `cssSuffix`, `login_bg3.png`, `macAddr` from a Check Point firewall admin web UI; NIC of management interface, not surveillance device. Entity-boundary kill."),
    "2C00AB":  ("kill", "Commscope (ARRIS) — model 'ARRIS NVG443B' / 'Frontier-NVG443B' observed; ARRIS NVG443B is a Frontier Communications fiber-optic home gateway (ONT). Non-surveillance class."),
    "70CA97":  ("kill", "Ruckus Wireless — model 'Ruckus Wireless ZoneDirector' / 'ZD1200' observed; ZoneDirector is a wireless LAN controller, NOT surveillance. Non-surveillance class."),
    "9C65EE":  ("kill", "Zhone Technologies — model 'DASAN-GPON-ONU-RG-H660GM' observed; GPON-ONU is a fiber-optic network terminal, NOT surveillance. Non-surveillance class."),
    "B479C8":  ("kill", "Ruckus Wireless — model 'Ruckus Wireless ZoneDirector' / 'ZD1200' observed; same as 70CA97. Non-surveillance class."),
    "C089AB":  ("kill", "Commscope (ARRIS) — model 'ARRIS NVG443B' / 'Frontier-NVG443B' observed; same as 2C00AB. Non-surveillance class."),
    "ECB5FA":  ("kill", "Philips Lighting BV (Signify) — same as 001788. Non-surveillance class."),
    "F03575":  ("kill", "Hui Zhou Gaoshengda Technology — evidence contains `LOCATION: http://192.168.1.4:8060/` (Roku ECP port) and `WAKEUP: MAC=f0:35:75:35:68:c3;Timeout=10`; Roku streaming device, NOT surveillance. Non-surveillance class."),
}


def best_evidence_for_oui(oui, files, prefer_surveillance=True):
    """Return the strongest evidence chunk for an OUI. Prefer surveillance-class observations."""
    surveillance_chunks = []
    other_chunks = []
    for f in files:
        if f.name.startswith("_"):
            continue
        body = json.loads(f.read_text())
        if not isinstance(body, dict) or "matches" not in body:
            continue
        for m in body["matches"]:
            m_blob = json.dumps(m)
            if oui.lower() not in m_blob.lower() and oui.upper() not in m_blob:
                continue
            upnp = m.get("upnp") or {}
            chunk = {
                "evidence_bytes": m_blob[max(0, m_blob.lower().find(oui.lower())-100):
                                         m_blob.lower().find(oui.lower())+250] if oui.lower() in m_blob.lower()
                                         else m_blob[:400],
                "manufacturer": (upnp.get("manufacturer") or "").strip(),
                "model_name": (upnp.get("model_name") or "").strip(),
                "model_description": (upnp.get("model_description") or "").strip(),
                "source_file": f.name,
                "ip_str": m.get("ip_str"),
                "port": m.get("port"),
                "module": (m.get("_shodan") or {}).get("module"),
            }
            mfr_lower = chunk["manufacturer"].lower()
            mdl_lower = (chunk["model_name"] + " " + chunk["model_description"]).lower()
            surv_signal = any(t in mfr_lower + " " + mdl_lower
                              for t in ["camera", "dvr", "nvr", "video", "surveillance", "alpr", "hikvision", "dahua", "axis"])
            if surv_signal:
                surveillance_chunks.append(chunk)
            else:
                other_chunks.append(chunk)
    return (surveillance_chunks[0] if prefer_surveillance and surveillance_chunks
            else (other_chunks[0] if other_chunks else None))


# Read extract output (24 net-new) and extract kills (bit/MA-L/SDK-hub/held)
extracted = json.loads((OUT_DIR / "candidates_oui.json").read_text())
existing_kills = json.loads((OUT_DIR / "killed.json").read_text())

raw_files = sorted(RAW.glob("*.json"))

final_survivors = []
entity_boundary_kills = []
for c in extracted:
    oui = c["oui"]
    if oui not in MANUAL:
        print(f"WARN: {oui} not in MANUAL — defaulting to kill")
        entity_boundary_kills.append({"oui": oui, "ieee_assignee": c["ieee_assignee"], "kill_reason": "no-manual-decision"})
        continue

    disposition = MANUAL[oui]
    if disposition[0] == "kill":
        entity_boundary_kills.append({
            "oui": oui,
            "ieee_assignee": c["ieee_assignee"],
            "kill_reason": "entity_boundary_or_non_surveillance",
            "review_note": disposition[1],
        })
        continue

    device_category, reason = disposition
    best = best_evidence_for_oui(oui, raw_files, prefer_surveillance=True)
    out = {
        "oui": oui,
        "ieee_assignee": c["ieee_assignee"],
        "channel": c.get("channel", ["unknown"]),
        "evidence_bytes": (best["evidence_bytes"] if best else c.get("evidence_bytes", "")),
        "manufacturer": [best["manufacturer"]] if best and best["manufacturer"] else c.get("manufacturer", []),
        "model_name": [best["model_name"]] if best and best["model_name"] else c.get("model_name", []),
        "model_description": [best["model_description"]] if best and best["model_description"] else c.get("model_description", []),
        "shodan_query": (best["source_file"] if best else c.get("shodan_query")),
        "observed_count": c.get("observed_count", 0),
        "device_category": device_category,
        "category_reason": reason,
    }
    final_survivors.append(out)

# Merge entity-boundary kills into killed.json
existing_kills["entity_boundary_or_non_surveillance"] = entity_boundary_kills
existing_kills["summary"]["entity_boundary_killed"] = len(entity_boundary_kills)
existing_kills["summary"]["net_new_survivors"] = len(final_survivors)
existing_kills["summary"]["final_total_distinct_ouis"] = existing_kills["summary"]["total_oui_candidates"]

# Summary
print(f"Total distinct OUI candidates  : {existing_kills['summary']['total_oui_candidates']}")
print(f"Survived all 5 kill tests      : {len(final_survivors)}")
for k, v in existing_kills["summary"].items():
    if "killed" in k or "survivors" in k:
        print(f"  {k:32s} : {v}")
print()
print(f"=== Final survivors ({len(final_survivors)}) ===")
for c in final_survivors:
    print(f"  {c['oui']}  {c['ieee_assignee'][:35]:<35}  cat={c['device_category']:<13}  observed={c['observed_count']}")
print()
print(f"=== Entity-boundary / non-surv kills ({len(entity_boundary_kills)}) ===")
for k in entity_boundary_kills:
    print(f"  {k['oui']}  {k['ieee_assignee'][:35]:<35}  {k['review_note'][:80]}")

(OUT_DIR / "candidates_oui.json").write_text(json.dumps(final_survivors, indent=1))
(OUT_DIR / "killed.json").write_text(json.dumps(existing_kills, indent=1))
print(f"\nWrote {OUT_DIR / 'candidates_oui.json'} ({len(final_survivors)} rows)")
print(f"Wrote {OUT_DIR / 'killed.json'}")
