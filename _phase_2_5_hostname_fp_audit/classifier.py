#!/usr/bin/env python3
"""MAC-188 Phase 2.5 hostname-corpus FP audit classifier.

Population: identifiers WHERE identifier_type IN (vendor_controlled_hostname,
vendor_cloud_endpoint_url, vendor_controlled_hostname_deprecated)
AND superseded_by IS NULL. N=12,243 across 52 manufacturers.

Classifier rules (applied in order, first match wins):
1. KNOWN_FP_ROOTS — registrable apex/known third-party platform/tooling. FP.
2. TRIVIAL_OR_INVALID — empty/literal-like/non-domain shape. FP.
3. vendor-owned-root match — hostname ends with one of the vendor's canonical
   roots (per VENDOR_OWNED_ROOTS map seeded from MAC-187 hb_003a survivor set
   + manufacturer-name token). TP.
4. anything else → AMBIGUOUS.

Per CP29 §1 / §2 vendor-ownership predicate: "Vendor-owned cloud-infrastructure
hostname" requires the apex to be vendor-owned. CP29 §2 admits hostname-only
shape for vendor-tenant on third-party cloud (e.g., DJI Terra Alibaba OSS) when
the hostname IS the endpoint signature — handled via the AMBIGUOUS bucket so a
human auditor can confirm the vendor-tenant binding.

Apex extraction uses a conservative public-suffix-like approach: split on '.',
take last 2 labels for generic TLDs, last 3 for known multi-part TLDs
(co.uk, ac.jp, gov.cn, com.cn, co.jp, etc.) — sufficient at audit-survey
fidelity; AMBIGUOUS bucket is the safety net.
"""

import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "db" / "argus.db"
OUT = Path(__file__).resolve().parent

# ─── KNOWN_FP_ROOTS ──────────────────────────────────────────────────────────
# Third-party platform / tooling / CDN / analytics / standards / public CA /
# generic hosting / package-registry / SaaS / docs platforms.
# Apex set; classifier matches via "hostname ends with .APEX or == APEX".
# Anchored on Wave I _phase_2_fp_scrub disambig classes + MAC-187 hb_003 Halt-1
# empirical disposition + MAC-187 hb_003a Stage-2-candidate carve-outs +
# new pollution surfaced in MAC-188 spot-check.

KNOWN_FP_ROOTS = {
    # CDNs / asset hosts
    "cloudfront.net", "fastly.net", "jsdelivr.net", "unpkg.com",
    "akamaihd.net", "gstatic.com", "googleusercontent.com",
    "cdninstagram.com", "shopifycdn.com", "cloudinary.com", "imgix.net",
    "akamai.net", "b-cdn.net", "cloudflare.com", "jsdelivr.com",
    "cdnjs.com", "ggpht.com",
    # CN tech-giant ecosystems (cross-attribution to non-CN-giant vendors = FP)
    "xiaomi.com", "huawei.com", "alipay.com", "oppomobile.com",
    "meizu.com", "line.me", "vmall.com",
    # OSS infra surfaced in DJI AMBIGUOUS bucket
    "geoserver.org", "eleme.io", "polymer-project.org", "errorprone.info",
    "exslt.org", "freegeoip.net", "geojson.org", "gnome.org",
    "linuxtv.org", "xiph.org", "harfbuzz.org", "iptc.org",
    "jquery.org", "js.foundation", "jsbin.com",
    "qbox.me", "symcb.com", "icl.com", "invisible-island.net",
    "jcraft.com", "thaiopensource.com", "mit-license.org",
    "json.org", "json-c.com", "fontforge.org", "fontforge.net",
    "fontspring.com", "kennethreitz.com", "mongoose-os.com",
    "openssl.org", "boringssl.org", "swtch.com", "graphics.cornell.edu",
    "math.utah.edu", "ee.princeton.edu", "csail.mit.edu",
    "ucla.edu", "csun.edu", "cs.ru.nl", "cs.utah.edu",
    "media.mit.edu", "cs.cmu.edu", "cs.princeton.edu",
    "ee.unimelb.edu.au", "cse.unsw.edu.au", "ist.psu.edu",
    "psy.miami.edu", "math.umass.edu", "math.utexas.edu",
    "umiacs.umd.edu", "isi.edu", "es.gnu.org", "savannah.gnu.org",
    "savannah.nongnu.org", "scratch.mit.edu", "graphviz.org",
    "ffmpeg.org", "videolan.org", "sox.sourceforge.net",
    "haxx.se",  # curl
    "actionbarsherlock.com", "ormlite.com", "journeyapps.com",
    "messagepush.org",
    "directtaps.net", "openweathermap.org", "tuxfamily.org",
    "startcom.org", "greenrobot.org", "skyward.io", "scipy.org",
    "u-blox.com", "aloft.rocks", "hamcrest.com", "adobepartneroffer.com",
    "fb.gg", "goo.gle", "android.asset",
    "expo.dev", "swmansion.com", "khronos.org", "git.io",
    "launchdarkly.com", "umbrella.com", "eascdn.net",
    "playready.directtaps.net",
    # Analytics / telemetry / crash / push / attribution
    "sentry.io", "datadoghq.com", "mixpanel.com", "segment.com",
    "google-analytics.com", "googletagmanager.com", "hotjar.com",
    "amplitude.com", "fullstory.com", "bugsnag.com", "crashlytics.com",
    "appsflyer.com", "branch.io", "snowplow.com", "doubleclick.net",
    "newrelic.com", "rollbar.com", "raygun.io", "logentries.com",
    "loggly.com", "papertrailapp.com",
    "bugly.qq.com",  # Tencent crash reporting
    "youla.io",
    # IdP / OAuth
    "auth0.com", "okta.com", "onelogin.com", "pingidentity.com",
    "microsoftonline.com", "oktapreview.com", "oauth2.googleapis.com",
    # Standards / IANA / governance
    "w3.org", "ietf.org", "iana.org", "rfc-editor.org", "unicode.org",
    "isoc.org", "icann.org", "nist.gov", "open-std.org", "iso.org",
    "ieee.org",
    # OS / SDK / docs platforms (Apple/MS/Google/Oracle/etc.)
    "apple.com", "microsoft.com", "google.com", "googleapis.com",
    "developer.android.com", "support.apple.com", "learn.microsoft.com",
    "developers.google.com", "oracle.com", "java.com", "jetbrains.com",
    "aka.ms", "msdn.microsoft.com", "docs.microsoft.com",
    "support.microsoft.com", "android.googlesource.com",
    "developer.intel.com", "intel.com", "amd.com",
    "schemas.microsoft.com", "schemas.openxmlformats.org",
    "developer.bluetooth.org", "bluetooth.com", "wi-fi.org",
    "developer.chrome.com", "googlecode.com",
    "firebase.com", "firebaseio.com", "googleapis.cn",
    "qualcomm.com", "nvidia.com", "ti.com",
    "mozilla.org", "wireshark.org", "opensource.org",
    # CAs / PKI / installer / build infra
    "installshield.com", "flexerasoftware.com", "flexnetoperations.com",
    "innosetup.com", "jrsoftware.org", "digicert.com", "symantec.com",
    "verisign.com", "thawte.com", "globalsign.com", "entrust.com",
    "usertrust.com", "comodoca.com", "geotrust.com", "letsencrypt.org",
    "omniroot.com", "godaddy.com",
    # Code hosts / dev platforms / docs hosts
    "github.com", "gitlab.com", "bitbucket.org", "sourceforge.net",
    "readthedocs.org", "readthedocs.io", "rtfd.io", "rtfd.org",
    "npmjs.com", "npmjs.org", "pypi.org", "pypi.python.org",
    "rubygems.org", "packagist.org", "crates.io", "rust-lang.org",
    "maven.apache.org", "mavenrepository.com", "central.maven.org",
    "spring.io", "stackoverflow.com", "stackexchange.com",
    "superuser.com", "serverfault.com", "askubuntu.com",
    "medium.com", "wordpress.com", "blogspot.com",
    "codepen.io", "jsfiddle.net", "codesandbox.io", "replit.com",
    "glitch.com", "godbolt.org", "regex101.com", "cubic-bezier.com",
    "easings.net", "caniuse.com",
    "freebsd.org", "freebsoft.org", "gnu.org", "fsf.org",
    "linuxfromscratch.org", "kernel.org", "linux.org",
    "wikipedia.org", "wikimedia.org", "wiktionary.org",
    "archive.org", "web.archive.org",
    "reddit.com", "ycombinator.com", "news.ycombinator.com",
    "twitter.com", "x.com", "facebook.com", "linkedin.com", "youtube.com",
    "vimeo.com", "instagram.com", "tiktok.com",
    "discord.com", "discord.gg", "discourse.org", "slack.com",
    "trello.com", "atlassian.net", "atlassian.com",
    "david-dm.org", "snyk.io", "dependabot.com", "renovate.com",
    "shields.io", "travis-ci.org", "travis-ci.com", "circleci.com",
    "appveyor.com", "azure-pipelines.io",
    # Generic / example / test / homepage placeholders
    "example.com", "example.org", "example.net", "foo.com", "bar.com",
    "test.com", "localhost", "c2.com",
    "earthlink.net", "verizon.net", "comcast.net", "att.net",
    "aol.com", "yahoo.com", "msn.com", "live.com", "outlook.com",
    # Academic / research / personal homepages
    "uiuc.edu", "mit.edu", "stanford.edu", "berkeley.edu", "cmu.edu",
    "aist-nara.ac.jp", "u-tokyo.ac.jp",
    # File hosts / generic SaaS
    "dropbox.com", "dropboxusercontent.com", "box.com", "wetransfer.com",
    "mega.nz", "mediafire.com", "rapidshare.com",
    "evernote.com", "notion.so", "airtable.com", "asana.com",
    "monday.com", "clickup.com", "basecamp.com",
    "salesforce.com", "force.com", "hubspot.com", "intercom.io",
    "zendesk.com",
    # LLVM / open source infra
    "llvm.org",
    # JS / mobile dev infra
    "chromium.org", "v8.dev", "nodejs.org", "ember-cli.com",
    # Misc oddities surfaced in DJI spot-check
    "skydrive.live.com", "onedrive.live.com",
    "browserify.org", "browserified.com",
    "huya.com",  # third-party live streaming (Tencent ecosystem)
    "caminobrowser.org", "freebsoft.org",
    # CN tech giants where the manufacturer is NOT one of them
    "qq.com", "tencent.com", "alibaba.com", "alibabacloud.com",
    "aliyun.com", "weibo.com", "baidu.com",
}

# Hostnames that are likely valid vendor-cloud-endpoint shapes (vendor-tenant
# on third-party cloud) — these are AMBIGUOUS rather than FP. Per CP29 §2
# shape variance noted in MAC-187 hb_003a for terra-sz-...aliyuncs.com.
THIRD_PARTY_CLOUD_PLATFORMS = {
    "s3.amazonaws.com", "amazonaws.com", "aliyuncs.com",
    "azurewebsites.net", "blob.core.windows.net",
    "cloudapp.azure.com", "appspot.com",
    "herokuapp.com", "github.io", "gitlab.io",
    "netlify.app", "vercel.app", "pages.dev",
    "amazonaws-china.com",
}

# Per-manufacturer canonical vendor-owned roots (seeded from MAC-187 hb_003a
# survivors + manufacturer-name token + common subsidiary domains).
# Forward-compatible: missing manufacturers fall through to manufacturer-name
# heuristic only (slug match).
VENDOR_OWNED_ROOTS = {
    "dji": [
        "dji.com", "dji.net", "djicdn.com", "djicorp.com", "djiservice.org",
        "djiservices.com", "dji-services.com", "dji-usrd.com", "skypixel.com",
        "dbeta.me", "rcdroneairsports.com", "djistatic.com", "aasky.net",
    ],
    "axon": ["axon.com", "axon.io", "evidence.com", "taser.com", "axoncloud.com"],
    "honeywell": [
        "honeywell.com", "honeywellaerospace.com",
        "honeywellprocess.com", "honeywellaidc.com", "honeywellpmt.com",
        "buildingcontrols.honeywell.com",
    ],
    "jacobs": ["jacobs.com", "jacobsbus.com", "jacobssolutions.com"],
    "l3harris": ["l3harris.com", "l3t.com", "l-3com.com"],
    "axis_communications": ["axis.com", "axiscommunications.com"],
    "harris": ["harris.com", "harriscorp.com"],
    "motorola_solutions": [
        "motorolasolutions.com", "motorola.com", "motorolasi.com",
        "ms.motorolasolutions.com",
    ],
    "hikvision": [
        "hikvision.com", "hik-online.com", "hikvisioneurope.com",
        "hik-connect.com", "ezvizlife.com", "ys7.com",
        "guardingvision.com", "pyronixcloud.com", "ltspartnerconnect.com",
        "ezviz.com", "ezvizteam.com",
    ],
    "cellebrite": ["cellebrite.com", "ufedupdate.com", "myreports.cellebrite.com"],
    "cisco_meraki": [
        "meraki.com", "meraki.net", "meraki.cisco.com", "cisco.com",
        "ciscomeraki.com",
    ],
    "meraki": ["meraki.com", "meraki.net"],
    "johnson_matthey": ["matthey.com", "jmcatalysts.com"],
    "skydio": ["skydio.com"],
    "genetec": ["genetec.com"],
    "soundthinking": ["soundthinking.com", "shotspotter.com"],
    "getac": ["getac.com"],
    "dedrone": ["dedrone.com"],
    "sierra_wireless": [
        "sierrawireless.com", "sierra-wireless.com", "swi-tbx.com",
        "airvantage.net",
    ],
    "sierrawireless": ["sierrawireless.com"],
    "kenwood": ["kenwood.com", "kenwoodusa.com"],
    "cradlepoint": ["cradlepoint.com", "netcloudmanager.com", "cradlepointecm.com"],
    "dahua": [
        "dahuatech.com", "dahuasecurity.com", "dahua.com",
        "easy4ipcloud.com", "lechange.com", "dolynkcloud.com",
        "dolynksecurity.com", "ecosightsecurity.com", "cossecurity.com",
        "dahuaddns.com", "imou.com",
    ],
    "flock_safety": ["flocksafety.com", "flock.com"],
    "verkada": ["verkada.com"],
    "avigilon": ["avigilon.com", "ava.uk", "avasecurity.com"],
    "rekor": ["rekor.ai", "rekorsystems.com"],
    "rhombus_systems": ["rhombus.com", "rhombussystems.com"],
    "eagle_eye_networks": ["een.com", "eagleeyenetworks.com"],
    "briefcam": ["briefcam.com"],
    "vigilant_solutions": ["vigilantsolutions.com", "vigilantsystems.com"],
    "magnet_forensics": ["magnetforensics.com"],
    "berla": ["berla.co", "iversitybytes.com"],
    "watchguard": ["watchguard.com", "watchguardvideo.com"],
    "digital_ally": ["digitalally.com"],
    "coban_technologies": ["cobantech.com", "coban.com"],
    "wolfcom": ["wolfcomusa.com", "wolfcom.com"],
    "clearview_ai": ["clearview.ai"],
    "droneshield": ["droneshield.com"],
    "parrot": ["parrot.com", "parrotpaltus.com"],
    "brinc": ["brincdrones.com", "brinc.com"],
    "keyw": ["keywcorp.com", "keyw.com"],
    "septier": ["septier.com"],
    "engility": ["engility.com"],
    "utility_inc": ["utility.com"],
    "drt": ["drtsolutions.net", "digitalreceiver.com"],
    "reveal": ["revealmedia.com"],
    "lenel": ["lenel.com", "lenels2.com"],
    "pips_technology": ["pipstechnology.com", "pips.com"],
    "autel_robotics": ["autelrobotics.com", "autel.com"],
    "bluepoint_alert": ["bluepointalert.com"],
    "hak5": ["hak5.org", "hakshop.com", "shop.hak5.org"],
}


def apex_of(hostname: str) -> str:
    """Conservative effective-apex extractor. Handles common multi-part TLDs."""
    if not hostname:
        return hostname
    h = hostname.lower().strip(".")
    parts = h.split(".")
    if len(parts) < 2:
        return h
    last = parts[-1]
    second = parts[-2] if len(parts) >= 2 else ""
    # Multi-part TLD heuristics
    multi_part_tlds = {
        ("co", "uk"), ("ac", "uk"), ("gov", "uk"), ("org", "uk"),
        ("co", "jp"), ("ac", "jp"), ("ne", "jp"), ("or", "jp"),
        ("co", "kr"), ("ac", "kr"),
        ("com", "cn"), ("gov", "cn"), ("org", "cn"), ("net", "cn"),
        ("com", "au"), ("net", "au"), ("org", "au"), ("gov", "au"),
        ("com", "br"), ("com", "mx"), ("com", "ar"),
        ("co", "in"), ("gov", "in"),
        ("com", "tw"), ("org", "tw"),
        ("com", "hk"), ("com", "sg"),
        ("com", "ru"),
    }
    if (second, last) in multi_part_tlds and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def manufacturer_name_tokens(manufacturer: str) -> set:
    """Tokens to substring-match against hostname for vendor-name heuristic."""
    if not manufacturer:
        return set()
    raw = manufacturer.lower()
    parts = re.split(r"[\s_\-]+", raw)
    toks = {raw.replace(" ", "").replace("-", "").replace("_", "")}
    toks.update(p for p in parts if len(p) >= 4)  # skip tiny tokens
    return {t for t in toks if t}


SYNTHETIC_S3_SUFFIXES = {
    "backup", "config", "dev", "db", "logs", "media", "production", "prod",
    "public", "support", "test", "videos", "uploads", "assets", "downloads",
    "firmware", "internal", "storage", "data",
}


def is_malformed_concatenated(h: str) -> bool:
    """Extraction-pollution signal — conservative.

    True extraction-artifacts surfaced in cisco_meraki AMBIGUOUS were
    hostnames where multiple distinct hosts got concatenated into a single
    long gibberish label (e.g. mid-hostname embeds dictionary-attack-style
    word salads). Vendors legitimately use short organizational subdomain
    labels (.net., .us., .gov., .dev., .ai.) so those alone are NOT a signal.

    Conservative rule: single-label > 40 chars without enough hyphenation
    to suggest natural multi-word naming (>=3 hyphens or >=2 consecutive
    vowel-cluster boundaries). Or overall hostname length > 120 chars."""
    if len(h) > 120:
        return True
    for label in h.split("."):
        if len(label) > 40 and label.count("-") < 3:
            return True
    return False


def classify(identifier: str, manufacturer: str) -> tuple:
    """Return (verdict, reason). verdict in {TP, FP, AMBIGUOUS}."""
    if not identifier or not isinstance(identifier, str):
        return ("FP", "empty_or_non_string")
    h = identifier.lower().strip()
    if not h or " " in h or "/" in h or h.startswith(".") or h.endswith(".") \
       or not re.match(r"^[a-z0-9._\-:]+$", h):
        return ("FP", "non_domain_shape")
    if h.count(".") < 1 and h not in ("localhost",):
        return ("FP", "no_dot_shape")
    if is_malformed_concatenated(h):
        return ("FP", "malformed_concatenated_extraction_artifact")

    apex = apex_of(h)

    # 1. KNOWN_FP_ROOTS check (whole-string or apex/suffix)
    for fp_root in KNOWN_FP_ROOTS:
        if h == fp_root or h.endswith("." + fp_root) or apex == fp_root:
            return ("FP", f"known_fp_root::{fp_root}")

    # 2. Third-party cloud platform handling
    for tp_cloud in THIRD_PARTY_CLOUD_PLATFORMS:
        if h.endswith("." + tp_cloud) or h == tp_cloud or apex == tp_cloud:
            mfr_toks = manufacturer_name_tokens(manufacturer)
            host_prefix = h[: -len(tp_cloud) - 1] if h.endswith("." + tp_cloud) else h
            if any(tok in host_prefix for tok in mfr_toks):
                # Synthetic-pattern detection: <vendor>-<common-suffix>
                # appearing across many vendors → very likely seeded
                # extraction-pollution, not real vendor-tenant. Treat as FP.
                tail = host_prefix.split(".")[0]  # first label
                m = re.match(r"^[a-z0-9_]+-([a-z0-9_]+)$", tail)
                if m and m.group(1) in SYNTHETIC_S3_SUFFIXES:
                    return ("FP",
                            f"synthetic_vendor_tenant_pattern::{tp_cloud}::"
                            f"suffix={m.group(1)}")
                return ("AMBIGUOUS",
                        f"vendor_tenant_on_third_party_cloud::{tp_cloud}")
            return ("FP", f"third_party_cloud_no_vendor_tenant::{tp_cloud}")

    # 3. Vendor-owned root match → TP
    if manufacturer in VENDOR_OWNED_ROOTS:
        for vroot in VENDOR_OWNED_ROOTS[manufacturer]:
            if h == vroot or h.endswith("." + vroot):
                return ("TP", f"vendor_owned_root::{vroot}")

    # 4. Manufacturer-name token in apex → soft TP (but lower confidence)
    mfr_toks = manufacturer_name_tokens(manufacturer)
    apex_label = apex.split(".")[0] if apex else ""
    for tok in mfr_toks:
        if len(tok) >= 4 and tok in apex_label:
            return ("TP", f"vendor_name_token_in_apex::{tok}::{apex}")

    # 5. Fallthrough → AMBIGUOUS
    return ("AMBIGUOUS", f"no_match::apex={apex}")


def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, identifier, identifier_type, manufacturer, confidence, source_type
        FROM identifiers
        WHERE identifier_type IN ('vendor_controlled_hostname',
                                  'vendor_cloud_endpoint_url',
                                  'vendor_controlled_hostname_deprecated')
          AND superseded_by IS NULL
        ORDER BY manufacturer, identifier
    """)
    rows = cur.fetchall()

    per_mfr = defaultdict(lambda: {"TP": [], "FP": [], "AMBIGUOUS": []})
    for row in rows:
        _id, ident, itype, mfr, conf, stype = row
        verdict, reason = classify(ident, mfr)
        per_mfr[mfr][verdict].append({
            "id": _id,
            "identifier": ident,
            "identifier_type": itype,
            "confidence": conf,
            "source_type": stype,
            "reason": reason,
        })

    # Compute summary
    summary = []
    for mfr in sorted(per_mfr.keys(), key=lambda m: -(
            len(per_mfr[m]["TP"]) + len(per_mfr[m]["FP"]) + len(per_mfr[m]["AMBIGUOUS"])
    )):
        tp = len(per_mfr[mfr]["TP"])
        fp = len(per_mfr[mfr]["FP"])
        amb = len(per_mfr[mfr]["AMBIGUOUS"])
        n = tp + fp + amb
        fp_rate = (fp / n * 100) if n else 0.0
        amb_rate = (amb / n * 100) if n else 0.0
        # Conservative FP rate counts AMBIGUOUS as not-FP (lower bound).
        # Worst-case FP rate counts AMBIGUOUS as FP (upper bound).
        summary.append({
            "manufacturer": mfr,
            "n": n, "tp": tp, "fp": fp, "ambiguous": amb,
            "fp_rate_pct": round(fp_rate, 2),
            "ambiguous_rate_pct": round(amb_rate, 2),
            "fp_rate_worst_case_pct": round((fp + amb) / n * 100, 2) if n else 0.0,
        })

    OUT.mkdir(exist_ok=True)
    with open(OUT / "per_manufacturer_summary.json", "w") as f:
        json.dump({
            "total_n": sum(s["n"] for s in summary),
            "per_manufacturer": summary,
        }, f, indent=2)

    # Detailed dump
    with open(OUT / "per_manufacturer_classifications.json", "w") as f:
        json.dump(per_mfr, f, indent=2)

    print(f"Total rows classified: {sum(s['n'] for s in summary)}")
    print()
    print(f'{"manufacturer":<28s} {"n":>6s} {"TP":>6s} {"FP":>6s} {"AMB":>6s} '
          f'{"FP%":>7s} {"AMB%":>7s} {"worst%":>7s}  band')
    print("-" * 96)
    for s in summary:
        band = "≤10" if s["fp_rate_pct"] <= 10 else \
               "10-30" if s["fp_rate_pct"] <= 30 else ">30"
        wband = "≤10" if s["fp_rate_worst_case_pct"] <= 10 else \
                "10-30" if s["fp_rate_worst_case_pct"] <= 30 else ">30"
        print(f'{s["manufacturer"]:<28s} {s["n"]:>6d} {s["tp"]:>6d} '
              f'{s["fp"]:>6d} {s["ambiguous"]:>6d} '
              f'{s["fp_rate_pct"]:>6.2f}% {s["ambiguous_rate_pct"]:>6.2f}% '
              f'{s["fp_rate_worst_case_pct"]:>6.2f}%  {band}/{wband}')


if __name__ == "__main__":
    main()
