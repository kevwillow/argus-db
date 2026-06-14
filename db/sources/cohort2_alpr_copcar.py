"""MAC-372 — Cohort 2 (ALPR / cop-car) EXTRACTION.

Turns the CTO-verified MAC-365 harvest manifest into structured identifier
candidates for CTO review -> DBArchitect ingest. EXTRACTION ONLY: emits
extraction_outputs/mac365_cohort2_alpr/candidates.json. NO DB write, NO ingest,
NO migration, NO export regen, NO push. Decompiled APK source NEVER enters the
git index (§11 #15 / 17 USC §1201) — only candidate value + relative path.

Targets (per MAC-363 Phase B / source-triage §3 cohort 2):
  Genetec AutoVu, ELSAG/Leonardo, Avigilon, Rekor, Motorola/Vigilant (LEARN).

Discipline (MAC-365 integrity rulings 1-9 + bible §7.3 / §8.2 / §8.3 / §4.4 / §11):
  1. OUI-not-bulk: vendor->OUI facts come from IEEE registry (sid 1/2/3), NOT the
     bundled oui.txt/csv copies in flock-you repos. Re-verified here against the
     authoritative raw/ieee_oui CSV — surfaced 2 repo mis-attributions.
  2. §8.3 value-level corroboration, not hub-and-spoke. No +5 lift for same-vendor.
  3. Researcher-confidence (85/80/75 in the .kt) discarded; §8.2 source-band ceiling.
  4. Observation-vs-registration lens annotated per candidate.
  5. §11 #3 / SAR-5 PII: FCC contact_name redacted (count logged in meta).
  6. ssid_pattern is export-DROPPED from both Lynceus exports (§4.4 no regex v0.2).
  7. db_presence annotated; disposition-tally kept separate from net-new floor.
  8. Penguin/Pigvision weak repo sourcing -> UNVERIFIED, second source required.
  9. Honest absences carried forward (ELSAG/Rekor-Scout/CarDetector no app).

Anti-hallucination: every .kt / .csv cite is re-grepped from its named raw artifact
on disk here (FileNotFoundError if missing). APK behavioral evidence is re-grepped
from the gitignored APK's DEX strings when the binary is present (best-effort —
the 404 MB corpus may be absent in CI), and embedded with its verified locus.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "db" / "argus.db"
OUT_DIR = REPO / "extraction_outputs" / "mac365_cohort2_alpr"

# --- raw artifact relative paths (provenance-only, gitignored) ---------------
SID16 = ("raw/flock_you_family/20260613T204753Z/_extracted/"
         "sid16__MaxwellDPS_Flock-You-Android__b3a203027689/"
         "Flock-You-Android-b3a2030276895ebf2439ad30724cace10de9c506")
A_SSID = f"{SID16}/app/src/main/java/com/flockyou/data/model/SsidPatterns.kt"
A_DET = f"{SID16}/app/src/main/java/com/flockyou/data/model/DetectionPatterns.kt"
A_IEEE_OUI = "raw/ieee_oui/20260613T203034Z_oui.csv"
A_FCC_JSON = "extraction_outputs/mac321_v166/raw/fcc_grantee_full.json"

SID16_COMMIT = "b3a2030276895ebf2439ad30724cace10de9c506"
SID16_URL = ("https://github.com/MaxwellDPS/Flock-You-Android/blob/"
             f"{SID16_COMMIT}/app/src/main/java/com/flockyou/data/model")
FCC_FROZEN_SHA = "5cd60fbe8654f6c146123e3c30cf4642fe17de98360d9d241b79b4460ee80cbd"
FCC_FROZEN_FREEZE = "2021-03-22"

# APK corpus (gitignored, §11 #15) — relative paths for the deliverable.
APK_VIGILANT = ("raw/vendor_apps/vigilant/com.vigilant.solutions.mobilecompanion/"
                "1.1.180312.1100/"
                "a627e3fa9191689c42e3e688c9600440a2bb3360e8beba26981c65fa4b0fad44.apk")
APK_REKOR = ("raw/vendor_apps/rekor/ai.rekor.rekorblue/1.5.92.0/"
             "5993cfff6c90e0f1e4a8f1e2e4a332f2e6e687117a303bdb5b6afe54ebca88cb.apk")

_file_cache: dict[str, list[str]] = {}


def _lines(rel: str) -> list[str]:
    if rel not in _file_cache:
        p = REPO / rel
        if not p.exists():
            raise FileNotFoundError(f"raw artifact missing: {rel}")
        _file_cache[rel] = p.read_text(encoding="utf-8", errors="replace").splitlines()
    return _file_cache[rel]


def _grep_line(rel: str, needle: str) -> tuple[int, str]:
    """Return (1-based line number, stripped line) of the first line containing
    needle. Raises if absent — anti-hallucination: a cite that cannot be re-found
    on disk is a fabrication and must not ship."""
    for i, ln in enumerate(_lines(rel), 1):
        if needle in ln:
            return i, ln.strip()
    raise AssertionError(f"cite not found in {rel}: {needle!r}")


def _ieee_oui_vendor(oui_hex: str) -> Optional[str]:
    """Authoritative OUI->vendor from the IEEE raw CSV (sid 1/2/3). oui_hex is
    6 hex chars, no separators, uppercase (e.g. 'F4CE36')."""
    for ln in _lines(A_IEEE_OUI):
        parts = ln.split(",", 2)
        if len(parts) >= 3 and parts[1].strip().upper() == oui_hex.upper():
            return parts[2].strip().strip('"')
    return None


def _excerpt(s: str, limit: int = 200) -> str:
    """§11 #7 ≤200-char source_excerpt — app-level enforced (truncate-with-marker;
    raw_observations has no DB CHECK per CP23 cap table)."""
    s = s.strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


@dataclass
class Candidate:
    identifier_type: str
    value: str
    source_sid: object               # int sid, or "needs_new_source_row:<key>"
    source_url: str
    relative_path: str               # raw/<...> within the gitignored tree
    proposed_confidence_ceiling: int  # §8.2 source-band ceiling
    db_presence: str                 # "net-new" | "already_in_db:id=<n>"
    source_lens: str                 # "observation" | "registration"
    manufacturer: Optional[str]
    device_category: str
    cite_excerpt: str
    notes: str = ""
    conflict_note: str = ""
    needs_new_source_row: Optional[str] = None
    recommend_confidence: Optional[int] = None  # conservative per-row recommend


@dataclass
class Behavioral:
    signature_name: str
    device_category: str
    cellular_generation: Optional[str]
    source_ref: str                  # "needs_new_source_row:<key>"
    relative_path: str
    evidence: list                   # list of {locus, note}
    proposed_confidence_ceiling: int
    notes: str = ""


def _db():
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def _id_lookup(cur, value: str, itype: Optional[str] = None) -> Optional[int]:
    q = ("select id from identifiers where lower(identifier)=lower(?) "
         "and superseded_by is null")
    args = [value]
    if itype:
        q += " and identifier_type=?"
        args.append(itype)
    cur.execute(q, args)
    r = cur.fetchone()
    return r[0] if r else None


# ── A. flock-you sid16 SSID regexes (crowdsourced, observation-lens) ──────────
# (regex value, needle-to-grep, file, manufacturer, device_category, verified?)
_SSID_ROWS = [
    ("(?i)^vigilant[_-]?.*", '"(?i)^vigilant[_-]?.*"', A_SSID, "Motorola Solutions", "alpr", True),
    ("(?i)^genetec[_-]?.*", '"(?i)^genetec[_-]?.*"', A_SSID, "Genetec", "alpr", True),
    ("(?i)^autovu[_-]?.*", '"(?i)^autovu[_-]?.*"', A_SSID, "Genetec", "alpr", True),
    ("(?i)^elsag.*", '"(?i)^elsag.*"', A_DET, "Leonardo DRS", "alpr", True),
    ("(?i)^alpr[_-]?.*", '"(?i)^alpr[_-]?.*"', A_SSID, None, "alpr", True),
    ("(?i)^lpr[_-]?cam.*", '"(?i)^lpr[_-]?cam.*"', A_SSID, None, "alpr", True),
    # Penguin / Pigvision — weak/uncited repo sourcing (ruling #8): UNVERIFIED.
    ("(?i)^penguin[_-]?.*", '"(?i)^penguin[_-]?.*"', A_SSID, "Penguin", "unknown", False),
    ("(?i)^pigvision[_-]?.*", '"(?i)^pigvision[_-]?.*"', A_SSID, "Pigvision", "unknown", False),
]


def _ssid_candidates(cur) -> list[Candidate]:
    out = []
    for value, needle, f, mfr, cat, verified in _SSID_ROWS:
        ln, text = _grep_line(f, needle)
        fname = f.split("/")[-1]
        existing = _id_lookup(cur, value, "ssid_pattern")
        presence = f"already_in_db:id={existing}" if existing else "net-new"
        notes = ("researcher-authored detection regex (single-source, sid16 "
                 "crowdsourced); NOT a confirmed broadcast observation. "
                 "Export-DROPPED from both Lynceus exports per §4.4 (no regex v0.2).")
        conflict = ""
        recommend = 75  # crowdsourced band ceiling
        if not verified:
            notes = ("WEAK/UNCITED vendor sourcing in repo (ruling #8) — UNVERIFIED. "
                     "Second independent source REQUIRED before promotion. " + notes)
            conflict = "unverified_vendor_sourcing — manifest flagged Penguin/Pigvision"
            recommend = 40  # §7.3 ambiguous: cap ≤40, note='ambiguous_extraction'
        out.append(Candidate(
            identifier_type="ssid_pattern", value=value, source_sid=16,
            source_url=f"{SID16_URL}/{fname}#L{ln}",
            relative_path=f, proposed_confidence_ceiling=75,
            recommend_confidence=recommend, db_presence=presence,
            source_lens="observation", manufacturer=mfr, device_category=cat,
            cite_excerpt=_excerpt(text), notes=notes, conflict_note=conflict,
        ))
    return out


# ── B. FCC grantee codes (sid 7 frozen primary_registry) ─────────────────────
# (grantee_code, mfr, device_category, alpr_relevance_note)
_GRANTEES = [
    ("VTF", "Remington Elsag", "alpr", "ALPR-relevant — ELSAG LE ALPR grantee (Brewster NY)"),
    ("2AKB2", "Leonardo", "alpr", "Leonardo S.p.a. — ELSAG/ALPR parent (Roma)"),
    ("2ATWB", "Leonardo", "alpr", "Leonardo S.p.a. second grantee (Roma)"),
    ("2ANPO", "Nordic Semiconductor", "unknown", "BLE chipmaker §11#10 multi-purpose (Trondheim)"),
    ("WCB", "SQF Trading Co.", "unknown", "WiFi/BT module maker — NOT LiteOn (Shenzhen); discrepancy flag"),
    # already-present in identifiers (annotation, not net-new):
    ("2ANC5", "Avigilon", "cctv_camera", "already fcc_grantee_code id in DB"),
    ("ABZ", "Motorola Solutions", "unknown", "already fcc_grantee_code id in DB"),
    ("N7N", "Sierra Wireless", "unknown", "already fcc_grantee_code id in DB; Flock Falcon V2 modem grantee"),
    ("UXX", "Cradlepoint", "unknown", "already fcc_grantee_code id in DB"),
    ("NCV", "Vigilant Systems Inc", "unknown", "frozen FCC = Vigilant Systems Inc / Klamath Falls OR"),
]


def _fcc_grantee_full(code: str) -> dict:
    """grantee_code/name only from the PII-stripped local frozen JSON (50,153 rows).
    City/state come from the DB fcc_grantees staging table (PII column excluded)."""
    data = json.loads((REPO / A_FCC_JSON).read_text())
    for row in data:
        if row.get("grantee_code") == code:
            return row
    raise AssertionError(f"grantee {code} not in frozen FCC JSON")


def _grantee_candidates(cur) -> tuple[list[Candidate], int]:
    out, redactions = [], 0
    # DB fcc_grantees staging (PII-aware) — surface code/name/city/state only.
    g = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    gc = g.cursor()
    for code, mfr, cat, note in _GRANTEES:
        frozen = _fcc_grantee_full(code)  # asserts presence in PII-stripped JSON
        gc.execute("select grantee_name, city, state, country, contact_name "
                   "from fcc_grantees where grantee_code=?", (code,))
        name, city, state, ctry, contact = gc.fetchone()
        if contact:
            redactions += 1  # §11 #3 / SAR-5: contact_name suppressed
        existing = _id_lookup(cur, code, "fcc_grantee_code")
        presence = f"already_in_db:id={existing}" if existing else "net-new"
        conflict = ""
        if code == "NCV" and existing:
            cur.execute("select manufacturer, device_category from identifiers "
                        "where id=?", (existing,))
            em, ec = cur.fetchone()
            conflict = (f"MIS-ATTRIBUTION: existing id={existing} labels NCV "
                        f"'{em}'/'{ec}' but frozen FCC sid7 = 'Vigilant Systems Inc' "
                        f"(Klamath Falls OR) != Vigilant Solutions. Verify (ruling).")
        loc = ", ".join(x for x in (city, state, ctry) if x)
        excerpt = _excerpt(f'"{code}","{name}",{loc} (FCC EAS frozen {FCC_FROZEN_FREEZE})')
        out.append(Candidate(
            identifier_type="fcc_grantee_code", value=code, source_sid=7,
            source_url="https://opendata.fcc.gov/Engineering/"
                       "FCC-EAS-Grantee-Codes/3b3k-34jp",
            relative_path=f"sid7 frozen CSV (sha256 {FCC_FROZEN_SHA[:12]}…, external/gitignored)",
            proposed_confidence_ceiling=85,  # primary_registry §8.2 CP21 strict reading
            db_presence=presence, source_lens="registration", manufacturer=mfr,
            device_category=cat, cite_excerpt=excerpt,
            notes=f"PII-stripped (code/name/city/state only). {note}",
            conflict_note=conflict,
        ))
    g.close()
    return out, redactions


# ── C. FCC equipment_class_code (full FCC IDs, sid 85 fcc.report live) ────────
# Confirmed on fcc.report grantee listing pages this run; equipment-class /
# frequency = honest-absence (not on listing page; FCC EAS grant exhibit unreached).
_FCC_IDS = [
    ("VTFADM3", "VTF", "Remington Elsag", "alpr", "2009-11-25",
     "Remington Elsag ALPR device; FCC ID confirmed on fcc.report/FCC-ID/VTF"),
    ("N7NRC76B", "N7N", "Sierra Wireless", "unknown", "2020-02-05",
     "Sierra RC76B LTE Cat-4 module — embedded in Flock Falcon V2 (teardown obs, "
     "ryanohoro.com/cehrp.org). Multi-purpose module §11#10 -> unknown, not alpr."),
    ("N7NRC76C", "N7N", "Sierra Wireless", "unknown", "2022-06-30",
     "Sierra RC76C LTE module; successor of RC76B. Multi-purpose §11#10 -> unknown."),
]


def _fcc_id_candidates(cur) -> list[Candidate]:
    out = []
    for fccid, grantee, mfr, cat, filed, note in _FCC_IDS:
        existing = _id_lookup(cur, fccid, "equipment_class_code")
        presence = f"already_in_db:id={existing}" if existing else "net-new"
        lens = "registration" if cat == "alpr" else "observation"
        out.append(Candidate(
            identifier_type="equipment_class_code", value=fccid, source_sid=85,
            source_url=f"https://fcc.report/FCC-ID/{grantee}/{fccid[len(grantee):]}",
            relative_path="sid85 fcc.report (live listing this run; exhibit not fetched)",
            proposed_confidence_ceiling=90,  # regulatory band (fcc.report)
            db_presence=presence, source_lens=lens, manufacturer=mfr,
            device_category=cat,
            cite_excerpt=_excerpt(f"FCC ID {fccid} — {mfr} — NEW DEVICE filed {filed} "
                                  f"(grantee {grantee})"),
            notes=("equipment-class code + frequency band = HONEST-ABSENCE (not on "
                   "fcc.report listing page; FCC EAS grant exhibit unreached). " + note),
            conflict_note="" if mfr != "Sierra Wireless"
            else "paired with fcc_grantee_code N7N per §11#7; component-module, "
                 "NOT a Flock-own identifier",
        ))
    return out


# ── F. Behavioral signatures (§5 / migration 0010) from APK teardown ─────────
_BEHAVIORALS = [
    Behavioral(
        signature_name="ALPR plate scan -> cloud upload -> hotlist hit-alert "
                        "(Vigilant LEARN companion)",
        device_category="alpr", cellular_generation=None,
        source_ref="needs_new_source_row:app:com.vigilant.solutions.mobilecompanion",
        relative_path=APK_VIGILANT, proposed_confidence_ceiling=80,
        evidence=[
            {"locus": "Lcom/vigilant/solutions/communicate/MCLPScanUpload;",
             "note": "LP (license-plate) scan -> upload"},
            {"locus": "Lcom/vigilant/solutions/communicate/LEARNInterface;",
             "note": "uploads detections to Vigilant LEARN cloud"},
            {"locus": "Lcom/vigilant/solutions/datastruct/VHitAlertInfo;",
             "note": "hit-alert on hotlist match"},
            {"locus": "Lcom/vigilant/solutions/xml/VHotlistAlertParser;",
             "note": "hotlist (BOLO) alert parsing"},
            {"locus": "Lcom/vigilant/solutions/datastruct/VAddHotPlateRequest;",
             "note": "hot-plate (watchlist) management"},
        ],
        notes="manufacturer_app installer/operator cohort; class descriptors "
              "re-grepped from gitignored DEX (decompiled source NOT committed, §11#15).",
    ),
    Behavioral(
        signature_name="ALPR plate recognition (OpenALPR) -> hotlist sync/match "
                        "(Rekor Blue)",
        device_category="alpr", cellular_generation=None,
        source_ref="needs_new_source_row:app:ai.rekor.rekorblue",
        relative_path=APK_REKOR, proposed_confidence_ceiling=80,
        evidence=[
            {"locus": "Lai/rekor/openalpr/AlprResultListener;",
             "note": "OpenALPR plate-recognition result callback"},
            {"locus": "Lai/rekor/openalpr/alprstream/model/AlprBestPlate;",
             "note": "best-plate selection from ALPR stream"},
            {"locus": "Lai/rekor/rekorblue/databinding/ActivityScanBinding;",
             "note": "scan activity"},
            {"locus": "hotlist_entry", "note": "DROP TABLE IF EXISTS hotlist_entry — local hotlist DB"},
            {"locus": "Hotlist syncing complete", "note": "hotlist sync log string"},
        ],
        notes="manufacturer_app; OpenALPR JNI engine (com/openalpr/jni). Class "
              "descriptors re-grepped from gitignored DEX (not committed, §11#15).",
    ),
]


def _verify_apk_evidence(b: Behavioral) -> str:
    """Best-effort re-grep of each evidence locus from the gitignored APK's DEX
    strings. Returns 'verified' | 'apk_absent' | 'MISSING:<locus>'. Keeps the
    decompiled source out of the git index — only the bounded locus string is used."""
    apk = REPO / b.relative_path
    if not apk.exists():
        return "apk_absent"
    try:
        with tempfile.TemporaryDirectory() as td:
            # split-APK bundle? extract inner base apk(s) first.
            subprocess.run(["unzip", "-o", "-q", str(apk), "-d", td],
                           check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            inner = list(Path(td).rglob("*.apk"))
            dexdir = Path(td) / "_dex"
            dexdir.mkdir(exist_ok=True)
            for ia in (inner or [apk]):
                subprocess.run(["unzip", "-o", "-q", str(ia), "classes*.dex", "-d", str(dexdir)],
                               check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            dexes = list(dexdir.glob("classes*.dex"))
            blob = b"".join(p.read_bytes() for p in dexes)
            for ev in b.evidence:
                if ev["locus"].encode() not in blob:
                    return f"MISSING:{ev['locus']}"
        return "verified"
    except Exception as e:  # pragma: no cover - environment-dependent
        return f"error:{e}"


def build() -> dict:
    with _db() as conn:
        cur = conn.cursor()
        ssid = _ssid_candidates(cur)
        grantees, redactions = _grantee_candidates(cur)
        fcc_ids = _fcc_id_candidates(cur)

    candidates = ssid + grantees + fcc_ids
    net_new = [c for c in candidates if c.db_presence == "net-new"]
    already = [c for c in candidates if c.db_presence != "net-new"]

    behaviorals = []
    for b in _BEHAVIORALS:
        d = asdict(b)
        d["apk_evidence_check"] = _verify_apk_evidence(b)
        behaviorals.append(d)

    # ── OUI dispositions (ruling #1 — annotation only, NOT crowdsourced candidates) ──
    oui_dispositions = _oui_dispositions()
    db_oui_misattributions = [
        {"oui": o["oui"], "db_id": o["db_presence"], "db_says": o["db_manufacturer"],
         "db_confidence": o["db_confidence"], "ieee_says": (o["ieee_authoritative"] or "").split(",")[0],
         "recommendation": o["DB_MIS_ATTRIBUTION"]}
        for o in oui_dispositions if "DB_MIS_ATTRIBUTION" in o
    ]
    grantee_conflicts = [
        {"value": c.value, "conflict": c.conflict_note}
        for c in grantees if c.conflict_note
    ]

    honest_absences = [
        "ELSAG/Leonardo — no public ALPR Android app (patrol-car hardware + web EOC); "
        "only FCC grantee (VTF/2AKB2) + sid16 SSID regex.",
        "Rekor Scout — desktop/Linux agent + web dashboard, no Android app.",
        "Vigilant CarDetector (standalone) — folded into Vigilant Mobile Companion; "
        "no standalone package.",
        "Genetec own-FCC grantee — absent from frozen sid7 set (post-2021-03-22 freeze "
        "gap); AutoVu SharpV/Cloudrunner FCC IDs not surfaced.",
        "APK BLE service UUIDs — 0 clean vendor UUIDs across all 6 ALPR APKs. Every "
        "128-bit UUID found is a cross-vendor SDK/framework constant (258eafa5 = "
        "board-ruled drop MAC-348/350, re-confirmed in rekor+avigilon×2; "
        "c06c8400/bb392ec0/9a04f079/e2719d58/edef8ba9 each appear in 2-3 unrelated "
        "vendor apps). No BluetoothGattService device binding -> none emitted (§11#1).",
        "APK default SSID patterns — 0; Cloudrunner installer's only WiFi/SSID strings "
        "are WebRTC/Android-framework (org.webrtc.NetworkMonitorAutoDetect), no vendor literal.",
        "Genetec + Avigilon behavioral signatures — apps obfuscated (Genetec) / "
        "server-side ALPR analytic not in mobile app (Avigilon ACC video viewer); "
        "no behavioral pattern extractable.",
        "Nordic OUI F4:CE:36 — IEEE-confirmed Nordic but ABSENT from DB; multi-purpose "
        "chipmaker (§11#10) + OUI-not-bulk (source from sid1/2/3 IEEE bulk, not sid16). "
        "Registry-gap flagged, NOT a cohort-2 candidate.",
    ]

    meta = {
        "issue": "MAC-372",
        "parent": "MAC-363",
        "worker": "ExtractionWorker (1347736c)",
        "scope": "EXTRACTION ONLY — candidates only; no DB write/ingest/migration/export/push",
        "input": "MAC-365 harvest manifest (CTO-verified)",
        "pii_redaction_count": redactions,
        "pii_note": "FCC contact_name suppressed (§11#3 / SAR-5); only code/name/city/state surfaced",
        "counts": {
            "identifier_candidates_total": len(candidates),
            "net_new": len(net_new),
            "already_in_db": len(already),
            "behavioral_signatures": len(behaviorals),
            "by_type_net_new": _by_type(net_new),
            "db_oui_misattributions": len(db_oui_misattributions),
            "grantee_conflicts": len(grantee_conflicts),
        },
        "db_conflicts_for_remediation": {
            "oui_misattributions": db_oui_misattributions,
            "grantee_misattributions": grantee_conflicts,
            "note": "EXTRACTION-ONLY surfaced these; NOT fixed here (no DB write). "
                    "DBArchitect/Validator remediation — §11 #1/#7/#8.",
        },
        "needs_new_source_rows": {
            "app:com.vigilant.solutions.mobilecompanion": {
                "proposed_name": "Vigilant Mobile Companion (LEARN) "
                                 "com.vigilant.solutions.mobilecompanion 1.1.180312.1100",
                "source_type": "manufacturer_app",
                "sha256": "a627e3fa9191689c42e3e688c9600440a2bb3360e8beba26981c65fa4b0fad44"},
            "app:ai.rekor.rekorblue": {
                "proposed_name": "Rekor Blue ai.rekor.rekorblue 1.5.92.0",
                "source_type": "manufacturer_app",
                "sha256": "5993cfff6c90e0f1e4a8f1e2e4a332f2e6e687117a303bdb5b6afe54ebca88cb"},
        },
    }

    return {
        "_meta": meta,
        "candidates": [asdict(c) for c in candidates],
        "behavioral_signatures": behaviorals,
        "oui_dispositions": oui_dispositions,
        "honest_absences": honest_absences,
    }


def _by_type(cands: list[Candidate]) -> dict:
    out: dict[str, int] = {}
    for c in cands:
        out[c.identifier_type] = out.get(c.identifier_type, 0) + 1
    return out


def _oui_dispositions() -> list[dict]:
    """Ruling #1: OUI->vendor facts come from IEEE (sid 1/2/3), not flock-you
    bundled/hardcoded copies. Re-verify each DetectionPatterns.kt OUI against the
    authoritative IEEE CSV AND the live DB; emit a disposition (NOT a candidate).

    Surfaces both: (a) repo-vs-IEEE mis-attributions (preventive — why sid16 is
    barred as an OUI source), and (b) DB-vs-IEEE mis-attributions — live identifier
    rows already promoted from sid16's wrong list, contradicting Argus's own IEEE
    registry. (b) is a §11 #1/#7/#8 conflict for DBArchitect/Validator remediation."""
    # Known brand-lineage acquisitions where IEEE registrant != current brand but
    # the repo's vendor label is defensible (NOT a mis-attribution).
    ACQUISITIONS = {
        "00:14:3E": "AirLink Communications acquired by Sierra Wireless (2007) — "
                    "Sierra Wireless AirLink product line; defensible lineage.",
    }
    rows = [
        ("00:0E:8E", "Sierra Wireless"), ("00:11:75", "Sierra Wireless"),
        ("00:14:3E", "Sierra Wireless"), ("00:A0:D5", "Sierra Wireless"),
        ("00:30:44", "Cradlepoint"), ("00:10:8B", "Cradlepoint"),
        ("EC:F4:51", "Cradlepoint"), ("F4:CE:36", "Nordic Semiconductor"),
        ("C0:A5:3E", "Nordic Semiconductor"), ("F0:5C:D5", "Nordic Semiconductor"),
    ]
    out = []
    with _db() as conn:
        cur = conn.cursor()
        for oui, repo_mfr in rows:
            ieee = _ieee_oui_vendor(oui.replace(":", ""))
            cur.execute("select id, manufacturer, confidence, source_type from identifiers "
                        "where lower(identifier)=? and identifier_type='oui' "
                        "and superseded_by is null", (oui.lower(),))
            r = cur.fetchone()
            db_id, db_mfr, db_conf, db_stype = r if r else (None, None, None, None)
            ieee_first = (ieee or "").split(",")[0].split()[0].lower() if ieee else ""
            repo_first = repo_mfr.split()[0].lower()
            agree = ieee_first == repo_first
            disp = {
                "oui": oui, "flock_you_claims": repo_mfr,
                "ieee_authoritative": ieee,
                "repo_matches_ieee": bool(agree) or oui in ACQUISITIONS,
                "db_presence": f"id={db_id}" if db_id else "absent",
                "db_manufacturer": db_mfr, "db_confidence": db_conf,
                "db_source_type": db_stype,
            }
            if oui in ACQUISITIONS:
                disp["lineage_note"] = ACQUISITIONS[oui]
            if not agree and ieee and oui not in ACQUISITIONS:
                disp["repo_flag"] = (f"REPO MIS-ATTRIBUTION — flock-you says {repo_mfr}, "
                                     f"IEEE says {ieee.split(',')[0]}. OUI-not-bulk validated.")
            # (b) the serious one: a live DB row contradicts IEEE.
            if db_id and ieee and not (db_mfr or "").split()[0].lower() == ieee_first \
                    and oui not in ACQUISITIONS:
                disp["DB_MIS_ATTRIBUTION"] = (
                    f"id={db_id} labels '{db_mfr}' (conf {db_conf}, {db_stype}) but IEEE "
                    f"says '{ieee.split(',')[0]}'. Sourced from sid16 hardcoded list "
                    f"(OUI-not-bulk violation already in DB). RECOMMEND DBArchitect "
                    f"re-attribute to IEEE ground truth or supersede; re-eval confidence.")
            elif db_id:
                disp["disposition"] = ("already_in_db, IEEE-consistent; sid16 adds "
                                       "observation-lens device-role only; 0 net-new")
            elif ieee:
                disp["disposition"] = ("IEEE-confirmed but absent from DB; registry-gap "
                                       "(sid1/2/3 bulk territory, §11#10 multi-purpose); not emitted")
            out.append(disp)
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result = build()
    out = OUT_DIR / "candidates.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=False) + "\n")
    m = result["_meta"]["counts"]
    print(f"wrote {out}")
    print(f"  net-new={m['net_new']} already_in_db={m['already_in_db']} "
          f"behavioral={m['behavioral_signatures']} by_type={m['by_type_net_new']}")
    print(f"  pii_redactions={result['_meta']['pii_redaction_count']}")
    for b in result["behavioral_signatures"]:
        print(f"  behavioral '{b['signature_name'][:40]}...' apk_check={b['apk_evidence_check']}")


if __name__ == "__main__":
    main()
