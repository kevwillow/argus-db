#!/usr/bin/env python3
"""MAC-365 apkcombo APK fetcher (playwright path, per MAC-349 method).

HARVEST ONLY. Fetches a vendor companion/installer APK from apkcombo to
raw/vendor_apps/<vendor>/<pkg>/<version>/<sha256>.apk (gitignored, §11 #15).
Binary is provenance-only; no decompile, no extraction, no DB write.

Usage: python3 mac365_apkcombo_fetch.py <vendor> <slug> <pkg> [<download-path-fragment>]
"""
import hashlib
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
ROOT = Path("/home/kev/argus")


def fetch(vendor: str, slug: str, pkg: str, frag: str | None) -> int:
    listing = f"https://apkcombo.com/{slug}/{pkg}/"
    dl_page = listing + (f"download/{frag}" if frag else "download/apk")
    tmp = ROOT / "raw" / "vendor_apps" / vendor / pkg / "_dl.tmp"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA, accept_downloads=True)
        page = ctx.new_page()
        page.goto(dl_page, wait_until="domcontentloaded", timeout=60000)
        # apkcombo runs a /checkin fingerprint handshake then enables a.variant
        time.sleep(6)
        link = None
        for sel in ("a.variant", "a.fc-button", "a[href*='apkcombo.org']",
                    "a[href$='.apk']", "a[href$='.xapk']"):
            loc = page.locator(sel)
            if loc.count() > 0:
                link = loc.first
                break
        if link is None:
            print(f"NO_DOWNLOAD_LINK on {dl_page}", file=sys.stderr)
            browser.close()
            return 2
        try:
            with page.expect_download(timeout=180000) as dl_info:
                link.click()
            dl = dl_info.value
            dl.save_as(str(tmp))
        except Exception as e:  # noqa: BLE001
            print(f"DOWNLOAD_FAIL {pkg}: {e}", file=sys.stderr)
            browser.close()
            return 3
        browser.close()
    data = tmp.read_bytes()
    h = hashlib.sha256(data).hexdigest()
    suffix = "xapk" if data[:2] == b"PK" and b"manifest.json" in data[:4000] else "apk"
    # name by sha256 under version dir; version filled by caller via env not known here
    out = tmp.parent / "_unsorted" / f"{h}.{suffix}"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp.rename(out)
    print(f"OK {pkg} bytes={len(data)} sha256={h} -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit(fetch(a[0], a[1], a[2], a[3] if len(a) > 3 else None))
