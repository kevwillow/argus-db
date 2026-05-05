"""MAC-21 Step-0 sample-verification — fetch 5 candidate repos and run a
byte-level regex+keyword sweep (zero-LLM) to project Wave-A yield surface.

Targets chosen for representativeness:
  1. hak5/usbrubberducky-payloads     — first-party setup-doc cohort
  2. dji-sdk/Mobile-SDK-Android       — first-party SDK source (BLE UUIDs likely)
  3. cradlepoint/sdk-samples          — cop-car cluster (MAC-1 standing advisory)
  4. 0xXyc/flock-you-wifi-recon       — third-party recon tool (Flock SSID anchor)
  5. f1yaw4y/FlockSquawk              — third-party Flock detector

Per-repo we fetch a small set of high-yield-likely files:
  - README.md (any case) via raw.githubusercontent.com
  - For SDK repos: 1-2 representative source headers (constants.h, *Bluetooth*,
    Connection*, *Default*) discovered via /repos/{o}/{r}/contents/ root listing

Byte-level regex/keyword anchors (per MAC-19 Step-1.5b survey methodology):
  - mac_anchored      \b[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}\b
  - ble_uuid_anchored \b[0-9A-Fa-f]{8}-([0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\b
  - fcc_id_anchored   \b[A-Z][A-Z0-9]{2}-?[A-Z0-9]{1,14}\b (FCC ID grantee+model)
  - ssid_kw           case-insensitive `\bssid\b` literal token
  - default_creds_kw  default password / login / credential / passphrase tokens
  - vendor_proximity  vendor-name occurrence

Output:
  raw/github/<run-ts>/_step0_sample/<owner>__<repo>/<file>
  raw/github/<run-ts>/_step0_sample/_byte_level_survey.json
  raw/github/<run-ts>/_step0_sample/_byte_level_survey.txt
  logs/mac21_step0_sample_verify_<run-ts>.log
"""
from __future__ import annotations

import hashlib
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "ArgusSourceWorker/0.1 (Phase4 Wave-A Step 0 sample verify; +https://github.com/argus-project)"
TIMEOUT_S = 30
SPACING_S = 1.5
DISCOVERY_RUN = "20260505T162207Z"  # parent discovery batch

REPO_ROOT = Path("/home/kev/argus")
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT = REPO_ROOT / "raw" / "github" / DISCOVERY_RUN / "_step0_sample"
OUT.mkdir(parents=True, exist_ok=True)
LOG = REPO_ROOT / "logs" / f"mac21_step0_sample_verify_{TS}.log"


SAMPLE_REPOS = [
    # (owner, repo, default_branch_guess, vendor_canonical, files_to_pull)
    ("hak5", "usbrubberducky-payloads", "master", "Hak5",
     ["README.md", "payloads/library/wifi/README.md"]),
    ("dji-sdk", "Mobile-SDK-Android", "master", "DJI",
     ["README.md"]),
    ("cradlepoint", "sdk-samples", "master", "Cradlepoint",
     ["README.md"]),
    ("0xXyc", "flock-you-wifi-recon", "main", "Flock Safety",
     ["README.md"]),
    ("f1yaw4y", "FlockSquawk", "main", "Flock Safety",
     ["README.md"]),
]


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    print(line)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def http_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    ctx = ssl.create_default_context()
    t0 = time.time()
    for branch_attempt in (False,):  # single attempt, branch-fallback handled by caller
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ctx) as r:
                body = r.read()
                return {
                    "status": r.status, "final_url": r.geturl(),
                    "content_type": r.headers.get("Content-Type", ""),
                    "byte_count": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "elapsed_s": round(time.time() - t0, 3),
                    "body": body, "error": None,
                }
        except urllib.error.HTTPError as e:
            body = e.read() if hasattr(e, "read") else b""
            return {
                "status": e.code, "final_url": url, "content_type": "",
                "byte_count": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "elapsed_s": round(time.time() - t0, 3),
                "body": body, "error": f"HTTPError {e.code}",
            }
        except Exception as e:
            return {
                "status": None, "final_url": url, "content_type": "",
                "byte_count": 0, "sha256": "",
                "elapsed_s": round(time.time() - t0, 3),
                "body": b"", "error": repr(e),
            }


# ─── Anchor regexes (mirroring MAC-19 step1.5b survey definitions) ──────────
RE_MAC = re.compile(r"\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b")
RE_UUID = re.compile(r"\b[0-9A-Fa-f]{8}-(?:[0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\b")
RE_FCC = re.compile(r"\b[A-Z][A-Z0-9]{2}-?[A-Z0-9]{4,14}\b")
RE_SSID_KW = re.compile(r"\bssid\b", re.IGNORECASE)
RE_BLE_KW = re.compile(r"\b(?:ble|bluetooth low energy)\b", re.IGNORECASE)
RE_DEFAULT_CRED = re.compile(
    r"\bdefault\s+(?:password|passwd|login|credential|user(?:name)?|passphrase|pin)\b",
    re.IGNORECASE,
)
RE_PASSWORD_LITERAL = re.compile(r'(?:^|\W)password\s*[:=]\s*[\'"]?[^\s\'"]{4,40}',
                                 re.IGNORECASE | re.MULTILINE)


def sweep(text: str, vendor: str) -> dict:
    return {
        "byte_count": len(text.encode("utf-8")),
        "mac_anchored": len(RE_MAC.findall(text)),
        "ble_uuid_anchored": len(RE_UUID.findall(text)),
        "fcc_id_anchored": len(RE_FCC.findall(text)),
        "ssid_kw": len(RE_SSID_KW.findall(text)),
        "ble_kw": len(RE_BLE_KW.findall(text)),
        "default_creds_kw": len(RE_DEFAULT_CRED.findall(text)),
        "password_literal_kw": len(RE_PASSWORD_LITERAL.findall(text)),
        "vendor_proximity": len(re.findall(rf"\b{re.escape(vendor)}\b",
                                           text, re.IGNORECASE)),
    }


def main() -> int:
    log(f"MAC-21 Step-0 sample-verify start; out={OUT}")
    survey = {"run_ts": TS, "discovery_batch": DISCOVERY_RUN, "repos": []}

    for owner, repo, branch, vendor, files in SAMPLE_REPOS:
        log(f"\n=== {owner}/{repo} ({vendor}) ===")
        rdir = OUT / f"{owner}__{repo}"
        rdir.mkdir(parents=True, exist_ok=True)
        rec = {"owner": owner, "repo": repo, "vendor": vendor, "files": []}
        for fname in files:
            url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{fname}"
            r = http_get(url)
            # branch fallback if 404
            if r["status"] == 404 and branch != "main":
                fb = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{fname}"
                log(f"  {fname}: 404 on {branch}; retry main")
                time.sleep(SPACING_S)
                r = http_get(fb)
                url = fb
            elif r["status"] == 404 and branch != "master":
                fb = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{fname}"
                log(f"  {fname}: 404 on {branch}; retry master")
                time.sleep(SPACING_S)
                r = http_get(fb)
                url = fb

            file_rec = {
                "url": url, "status": r["status"], "byte_count": r["byte_count"],
                "sha256": r["sha256"], "content_type": r["content_type"],
                "elapsed_s": r["elapsed_s"], "error": r["error"],
            }
            if r["status"] == 200 and r["body"]:
                # persist raw
                safe_name = fname.replace("/", "__")
                (rdir / safe_name).write_bytes(r["body"])
                # decode for sweep (best-effort)
                try:
                    text = r["body"].decode("utf-8")
                except UnicodeDecodeError:
                    text = r["body"].decode("utf-8", errors="replace")
                file_rec["sweep"] = sweep(text, vendor)
                log(f"  {fname}: status=200 bytes={r['byte_count']} "
                    f"mac={file_rec['sweep']['mac_anchored']} "
                    f"uuid={file_rec['sweep']['ble_uuid_anchored']} "
                    f"fcc={file_rec['sweep']['fcc_id_anchored']} "
                    f"ssid_kw={file_rec['sweep']['ssid_kw']} "
                    f"ble_kw={file_rec['sweep']['ble_kw']} "
                    f"creds_kw={file_rec['sweep']['default_creds_kw']} "
                    f"pw_literal={file_rec['sweep']['password_literal_kw']} "
                    f"vendor_prox={file_rec['sweep']['vendor_proximity']}")
            else:
                log(f"  {fname}: status={r['status']} ({r['error']})")
            rec["files"].append(file_rec)
            time.sleep(SPACING_S)
        survey["repos"].append(rec)

    # ─── Aggregate roll-up ───────────────────────────────────────────────
    agg = {"mac_anchored": 0, "ble_uuid_anchored": 0, "fcc_id_anchored": 0,
           "ssid_kw": 0, "ble_kw": 0, "default_creds_kw": 0,
           "password_literal_kw": 0, "byte_count": 0,
           "files_status_200": 0, "files_total": 0}
    for r in survey["repos"]:
        for f in r["files"]:
            agg["files_total"] += 1
            if f.get("status") == 200:
                agg["files_status_200"] += 1
                s = f.get("sweep", {})
                for k in ("mac_anchored", "ble_uuid_anchored", "fcc_id_anchored",
                          "ssid_kw", "ble_kw", "default_creds_kw",
                          "password_literal_kw", "byte_count"):
                    agg[k] += s.get(k, 0)
    survey["aggregate"] = agg

    (OUT / "_byte_level_survey.json").write_text(json.dumps(survey, indent=2))
    txt = ["MAC-21 Step-0 sample-verification byte-level survey",
           f"Run: {TS}",
           f"Discovery batch: {DISCOVERY_RUN}",
           "",
           "Per-repo per-file sweep:"]
    for r in survey["repos"]:
        txt.append(f"\n[{r['owner']}/{r['repo']}] vendor={r['vendor']}")
        for f in r["files"]:
            url = f.get("url", "?")
            if f.get("status") == 200 and "sweep" in f:
                s = f["sweep"]
                txt.append(f"  {url}")
                txt.append(f"    bytes={f['byte_count']} mac={s['mac_anchored']} uuid={s['ble_uuid_anchored']} "
                           f"fcc={s['fcc_id_anchored']} ssid_kw={s['ssid_kw']} ble_kw={s['ble_kw']} "
                           f"creds_kw={s['default_creds_kw']} pw_literal={s['password_literal_kw']} "
                           f"vendor_prox={s['vendor_proximity']}")
            else:
                txt.append(f"  {url}  status={f.get('status')} {f.get('error')}")
    txt.append("\n" + "=" * 60)
    txt.append(f"WAVE-A SAMPLE AGGREGATE ({agg['files_status_200']}/{agg['files_total']} files status=200, "
               f"{agg['byte_count']:,} bytes):")
    txt.append(f"  mac_anchored        = {agg['mac_anchored']}")
    txt.append(f"  ble_uuid_anchored   = {agg['ble_uuid_anchored']}")
    txt.append(f"  fcc_id_anchored     = {agg['fcc_id_anchored']}")
    txt.append(f"  ssid_kw             = {agg['ssid_kw']}")
    txt.append(f"  ble_kw              = {agg['ble_kw']}")
    txt.append(f"  default_creds_kw    = {agg['default_creds_kw']}")
    txt.append(f"  password_literal_kw = {agg['password_literal_kw']}")
    (OUT / "_byte_level_survey.txt").write_text("\n".join(txt))
    log("\nMAC-21 Step-0 sample-verify DONE")
    log(f"Aggregate: {agg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
