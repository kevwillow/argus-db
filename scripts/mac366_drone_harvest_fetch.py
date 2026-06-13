#!/usr/bin/env python3
"""MAC-366 Cohort 3 (Drones) — non-APK harvest fetcher.

HARVEST ONLY (no extraction / no DB write / no migration / no push). Pulls the
three Remote-ID provenance artifact families and pins them to disk:

  1. FAA UAS Remote-ID public DOC API rows (sid 36, docType=rid) per vendor
     -> raw/faa_uas_rid/<ts>/<vendor>.json  (public-API JSON)
  2. opendroneid / DragonSync / dji_droneid family repos pinned at HEAD (§11 #1)
     -> raw/drone_remoteid_family/<ts>/<repo>.tar.gz + opendroneid.h beacon header
  3. Bluetooth-SIG company-identifier registry (sid 34) — currency re-check only;
     canonical copy already lives at raw/bluetooth_sig/<ts>_company_identifiers.yaml.

APK binaries (Skydio com.skydio.r3 / com.skydio.enterprise XAPK, Autel
com.autel.explorer APK) are fetched separately via scripts/mac365_apkcombo_fetch.py
(playwright path, MAC-349 method) and land gitignored under
raw/vendor_apps/<vendor>/<pkg>/<version>/<sha256>.{apk,xapk} per §11 #15.

Usage:  python3 scripts/mac366_drone_harvest_fetch.py <UTC-timestamp>
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path("/home/kev/argus")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

FAA_RID = "https://uasdoc.faa.gov/api/v1/publicDOCRev/"
FAA_VENDORS = ["DJI", "Parrot", "Skydio", "Autel", "Anduril"]

# (sid, owner/repo, pinned HEAD commit) — verified via `git ls-remote ... HEAD`
REPOS: list[tuple[int, str, str]] = [
    (19, "opendroneid/opendroneid-core-c", "4b266c7c33e5299bfbe8427ed8518e869e3a7d7f"),
    (25, "opendroneid/receiver-android", "ed44ea3f16ce63be655454021ccda53413d13419"),
    (26, "opendroneid/wireshark-dissector", "d12670fede3aa4e336cfa326528782abfc864a10"),
    (27, "cyber-defence-campus/RemoteIDReceiver", "2212ee6ded567931c7a716f94112596808d380d7"),
    (23, "alphafox02/DragonSync", "2cf6fdcfe9dbe3bdebcbd728428ba50fb1974747"),
    (28, "proto17/dji_droneid", "7c6dddad563724df93132e91b89e74650182ea1e"),
    (22, "colonelpanichacks/Sky-Spy", "159dd4a4102d01744d5912e0605a9485025aa5dd"),
]

SIG_YAML = ("https://bitbucket.org/bluetooth-SIG/public/raw/main/"
            "assigned_numbers/company_identifiers/company_identifiers.yaml")


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310
        return r.read()


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch_faa(ts: str) -> None:
    out = ROOT / "raw" / "faa_uas_rid" / ts
    out.mkdir(parents=True, exist_ok=True)
    for v in FAA_VENDORS:
        url = f"{FAA_RID}?itemsPerPage=200&pageIndex=0&docType=rid&search={v}"
        body = _get(url)
        (out / f"{v.lower()}.json").write_bytes(body)
        d = json.loads(body)["data"]
        print(f"[faa] {v}: total={d['totalItems']} rows={len(d['items'])} "
              f"sha={_sha(body)[:12]}")


def pin_repos(ts: str) -> None:
    out = ROOT / "raw" / "drone_remoteid_family" / ts
    out.mkdir(parents=True, exist_ok=True)
    for sid, repo, pinned in REPOS:
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / repo.split("/")[1]
            subprocess.run(["git", "clone", "--quiet", "--depth", "1",
                            f"https://github.com/{repo}", str(dst)], check=True)
            got = subprocess.run(["git", "-C", str(dst), "rev-parse", "HEAD"],
                                 capture_output=True, text=True, check=True).stdout.strip()
            status = "OK" if got == pinned else f"MISMATCH got={got}"
            tarpath = out / f"{dst.name}.tar.gz"
            with tarfile.open(tarpath, "w:gz") as tf:
                tf.add(dst, arcname=dst.name)
            print(f"[repo] sid{sid} {repo} HEAD={status} "
                  f"tar_sha={_sha(tarpath.read_bytes())[:16]}")
    # beacon-structure header (ASTM F3411 / ASD-STAN reference impl)
    od = REPOS[0][2]
    hdr = _get(f"https://raw.githubusercontent.com/opendroneid/opendroneid-core-c/"
               f"{od}/libopendroneid/opendroneid.h")
    (out / "opendroneid.h").write_bytes(hdr)
    print(f"[repo] opendroneid.h sha={_sha(hdr)[:12]} bytes={len(hdr)}")


def check_sig() -> None:
    live = _sha(_get(SIG_YAML))
    cached = sorted((ROOT / "raw" / "bluetooth_sig").glob("*_company_identifiers.yaml"))
    if cached:
        local = _sha(cached[-1].read_bytes())
        print(f"[sig] live={live[:16]} local={local[:16]} "
              f"{'MATCH' if live == local else 'DRIFT'} ({cached[-1].name})")
    else:
        print(f"[sig] live={live[:16]} (no cached copy)")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    ts = sys.argv[1]
    fetch_faa(ts)
    pin_repos(ts)
    check_sig()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
