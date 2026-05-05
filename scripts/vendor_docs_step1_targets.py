"""Wave B Step 1 vendor target list (MAC-13).

Source of truth for the 22 reachable vendors enumerated in MAC-12 Step 0
discovery matrix (Item 1) ratified at comment 3310563e.

Berla skipped per SAR-4 verbatim Disallow read.
BRINC held for CEO Wayback ratification at first encounter.
Harris StingRay = no-public-surface aside (zero fetch).

Each vendor entry binds:
- slug: filesystem-safe vendor identifier (matches Step 0 manifest where applicable)
- canonical: bible-canonical vendor name
- robots_url: robots.txt URL fetched per §11 #6
- robots_note: verbatim Disallow + chosen path summary
- crawl_delay_s: minimum inter-request delay (default 2.0; SoundThinking 10.0)
- urls: ordered list of (kind, url) tuples to fetch
    kind = robots | sitemap | product_landing | spec_doc | install_guide |
           sdk_doc | fcc_search | footer_license | docs_landing
- fcc_grantees: list of grantee codes (from MAC-7 fcc_grantees table) for FCC
    EAS GenericSearch sampling — None means no known grantee
- license_observation: per Step 0 manifest pattern (verbatim copyright + verdict)
"""

from __future__ import annotations

VENDORS = [
    # ============================================================
    # Already-sampled at Step 0 (re-fetch under new batch timestamp)
    # ============================================================
    {
        "slug": "flock_safety",
        "canonical": "Flock Safety",
        "robots_url": "https://www.flocksafety.com/robots.txt",
        "robots_note": "robots.txt allows; only /blog-audiences/ and /use-case-filters/ disallowed",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.flocksafety.com/sitemap.xml"),
            ("product_landing", "https://www.flocksafety.com/products/license-plate-readers"),
            ("product_landing", "https://www.flocksafety.com/products/falcon"),
            ("product_landing", "https://www.flocksafety.com/products/raven"),
            ("product_landing", "https://www.flocksafety.com/products/condor"),
            ("product_landing", "https://www.flocksafety.com/products/sparrow"),
        ],
        "fcc_grantees": [],
        "license_observation": "© 2026 Flock Safety — proprietary all-rights-reserved",
    },
    {
        "slug": "motorola_solutions_apx",
        "canonical": "Motorola Solutions",
        "robots_url": "https://www.motorolasolutions.com/robots.txt",
        "robots_note": "robots.txt allows /en_us/products/...; only /non-navigational-pages/, /myaccount/, /search.html, /404.html disallowed",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.motorolasolutions.com/sitemap.xml"),
            ("product_landing", "https://www.motorolasolutions.com/en_us/products/two-way-radios/project-25-radios/portable-radios/apx-next/apx-next-start.html"),
            ("product_landing", "https://www.motorolasolutions.com/en_us/products/body-cameras/v300-body-camera.html"),
            ("product_landing", "https://www.motorolasolutions.com/en_us/products/in-car-video/m500-in-car-video-system.html"),
            ("product_landing", "https://www.motorolasolutions.com/en_us/products/two-way-radios/project-25-radios/mobile-radios/apx-mobile.html"),
            ("product_landing", "https://www.motorolasolutions.com/en_us/products/avigilon-h6a-cameras.html"),
        ],
        "fcc_grantees": ["YJJ"],
        "license_observation": "All rights reserved — proprietary",
    },
    {
        "slug": "axon",
        "canonical": "Axon",
        "robots_url": "https://www.axon.com/robots.txt",
        "robots_note": "robots.txt Allow: /*; only HR + non-Argus UA help paths blocked",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.axon.com/sitemap.xml"),
            ("product_landing", "https://www.axon.com/products/axon-body-3"),
            ("product_landing", "https://www.axon.com/products/axon-body-4"),
            ("product_landing", "https://www.axon.com/products/axon-fleet-3"),
            ("product_landing", "https://www.axon.com/products/taser-10"),
            ("product_landing", "https://www.axon.com/products/axon-dock"),
        ],
        "fcc_grantees": ["2AGVG"],
        "license_observation": "Axon proprietary — all rights reserved (SPA, footer client-rendered)",
    },
    {
        "slug": "cradlepoint_docs",
        "canonical": "Cradlepoint",
        "robots_url": "https://docs.cradlepoint.com/robots.txt",
        "robots_note": "SAR-4 routing — main host Disallow: /wp-content/uploads/. Alt: docs.cradlepoint.com Allow: /home, /reader/*, /viewer/document/*, /api/khub/documents/*/content (explicit allowlist for official docs)",
        "crawl_delay_s": 2.0,
        "urls": [
            ("docs_landing", "https://docs.cradlepoint.com/home"),
            ("product_landing", "https://www.cradlepoint.com/products/endpoints/"),
            ("product_landing", "https://www.cradlepoint.com/products/endpoints/r1900/"),
            ("product_landing", "https://www.cradlepoint.com/products/endpoints/e3000/"),
            ("product_landing", "https://www.cradlepoint.com/products/endpoints/ibr1700/"),
            ("docs_landing", "https://docs.cradlepoint.com/reader/2sQTeQXxs5Q9eEYJBh~vog/Tlhkbo3Tt6F0R8h1Onf7eA"),
        ],
        "fcc_grantees": ["UXX"],
        "license_observation": "Cradlepoint / Ericsson — proprietary; SPA portal shell",
    },
    {
        "slug": "skydio",
        "canonical": "Skydio",
        "robots_url": "https://www.skydio.com/robots.txt",
        "robots_note": "robots.txt Allow: /; only /modals/ disallowed",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.skydio.com/sitemap.xml"),
            ("product_landing", "https://www.skydio.com/x10"),
            ("product_landing", "https://www.skydio.com/x10d"),
            ("product_landing", "https://www.skydio.com/x2"),
            ("product_landing", "https://www.skydio.com/dock"),
            ("sdk_doc", "https://docs.skydio.com/"),
        ],
        "fcc_grantees": ["2ATQR"],
        "license_observation": "© 2026 Skydio, Inc — proprietary all-rights-reserved",
    },
    # ============================================================
    # Remaining 17 (Step 1 first-time fetch)
    # ============================================================
    {
        "slug": "sierra_wireless",
        "canonical": "Sierra Wireless / Semtech",
        "robots_url": "https://www.sierrawireless.com/robots.txt",
        "robots_note": "Yoast empty Disallow (open). Semtech: Disallow /uploads/*.html, /hubfs/, etc.; product pages allowed",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.sierrawireless.com/sitemap_index.xml"),
            ("product_landing", "https://www.sierrawireless.com/products-and-solutions/routers-gateways/"),
            ("product_landing", "https://www.sierrawireless.com/products-and-solutions/routers-gateways/airlink-mp70/"),
            ("product_landing", "https://www.sierrawireless.com/products-and-solutions/routers-gateways/airlink-xr80/"),
            ("product_landing", "https://www.semtech.com/products/wireless-rf"),
        ],
        "fcc_grantees": ["TWV"],
        "license_observation": "Semtech / Sierra Wireless — proprietary all-rights-reserved",
    },
    {
        "slug": "l3harris",
        "canonical": "L3Harris",
        "robots_url": "https://www.l3harris.com/robots.txt",
        "robots_note": "Allow /core/*.css/.js/.gif/.jpg/.svg; Disallow /core/, /profiles/, /README.md (admin only); product pages allowed",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.l3harris.com/sitemap.xml"),
            ("product_landing", "https://www.l3harris.com/all-capabilities/xl-extreme-portable-radio"),
            ("product_landing", "https://www.l3harris.com/all-capabilities/xl-200p-portable-radio"),
            ("product_landing", "https://www.l3harris.com/all-capabilities/xl-converge-portable-radio"),
            ("product_landing", "https://www.l3harris.com/all-capabilities/xl-185m-mobile-radio"),
        ],
        "fcc_grantees": [],
        "license_observation": "© L3Harris — proprietary all-rights-reserved",
    },
    {
        "slug": "genetec",
        "canonical": "Genetec",
        "robots_url": "https://www.genetec.com/robots.txt",
        "robots_note": "Heavy carve-out: Disallow /binaries/content/assets/genetec/{reports,ebooks,guidebooks,whitepapers,infographics}/; product pages allowed; partner-login docs are §11 #2 territory (not fetched)",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.genetec.com/sitemap.xml"),
            ("product_landing", "https://www.genetec.com/products/unified-security/security-center"),
            ("product_landing", "https://www.genetec.com/products/operations/streamvault"),
            ("product_landing", "https://www.genetec.com/products/license-plate-recognition/autovu"),
            ("product_landing", "https://www.genetec.com/products/connected-officer/citigraf"),
        ],
        "fcc_grantees": [],
        "license_observation": "Genetec — proprietary all-rights-reserved",
    },
    {
        "slug": "vigilant_solutions",
        "canonical": "Vigilant Solutions",
        "robots_url": "https://www.vigilantsolutions.com/robots.txt",
        "robots_note": "Yoast empty Disallow (open); legacy holding page redirects to motorolasolutions.com",
        "crawl_delay_s": 2.0,
        "urls": [
            ("product_landing", "https://www.vigilantsolutions.com/"),
            ("product_landing", "https://www.motorolasolutions.com/en_us/products/license-plate-recognition.html"),
        ],
        "fcc_grantees": ["NCV"],
        "license_observation": "Vigilant Solutions / Motorola PSA — proprietary all-rights-reserved",
    },
    {
        "slug": "avigilon_alta",
        "canonical": "Avigilon Alta",
        "robots_url": "https://www.avigilon.com/robots.txt",
        "robots_note": "Disallow /cpresources/, /vendor/, /.env, /cache/ (admin); product pages allowed",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.avigilon.com/sitemap.xml"),
            ("product_landing", "https://www.avigilon.com/alta"),
            ("product_landing", "https://www.avigilon.com/alta/products/access-control"),
            ("product_landing", "https://www.avigilon.com/alta/products/video"),
            ("product_landing", "https://www.avigilon.com/alta/products/aware"),
        ],
        "fcc_grantees": ["2ANC5"],
        "license_observation": "Avigilon (Motorola Solutions) — proprietary all-rights-reserved",
    },
    {
        "slug": "rekor",
        "canonical": "Rekor",
        "robots_url": "https://www.rekor.ai/robots.txt",
        "robots_note": "Sitemap-only robots.txt (fully open)",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.rekor.ai/sitemap.xml"),
            ("product_landing", "https://www.rekor.ai/scout"),
            ("product_landing", "https://www.rekor.ai/discover"),
            ("product_landing", "https://www.rekor.ai/command"),
            ("product_landing", "https://www.rekor.ai/automatic-license-plate-recognition"),
        ],
        "fcc_grantees": [],
        "license_observation": "Rekor Systems — proprietary all-rights-reserved",
    },
    {
        "slug": "reveal_media",
        "canonical": "Reveal Media",
        "robots_url": "https://www.revealmedia.com/robots.txt",
        "robots_note": "Disallow /cpresources/, /cdn-cgi/; product pages allowed",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.revealmedia.com/sitemap.xml"),
            ("product_landing", "https://www.revealmedia.com/products/d-series"),
            ("product_landing", "https://www.revealmedia.com/products/k-series"),
            ("product_landing", "https://www.revealmedia.com/products/dems"),
        ],
        "fcc_grantees": ["2AL26"],
        "license_observation": "Reveal Media — proprietary all-rights-reserved",
    },
    {
        "slug": "watchguard",
        "canonical": "WatchGuard (Motorola PSA)",
        "robots_url": "https://www.motorolasolutions.com/robots.txt",
        "robots_note": "Inherits Motorola Sols robots (allow product paths)",
        "crawl_delay_s": 2.0,
        "urls": [
            ("product_landing", "https://www.motorolasolutions.com/en_us/products/in-car-video.html"),
            ("product_landing", "https://www.motorolasolutions.com/en_us/products/in-car-video/v300-body-camera.html"),
            ("product_landing", "https://www.motorolasolutions.com/en_us/products/in-car-video/m500-in-car-video-system.html"),
            ("product_landing", "https://www.motorolasolutions.com/en_us/products/body-cameras/4re-in-car-video-system.html"),
        ],
        "fcc_grantees": ["YJV"],
        "license_observation": "WatchGuard / Motorola Solutions — proprietary all-rights-reserved",
    },
    {
        "slug": "getac",
        "canonical": "Getac",
        "robots_url": "https://www.getac.com/robots.txt",
        "robots_note": "Disallow /pdf/ blocks PDF spec sheets at canonical path. SAR-4 alt: product pages at /products/* allowed; spec downloads via /support/manuals/* (Step 1 verify)",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.getac.com/sitemap.xml"),
            ("product_landing", "https://www.getac.com/us/products/laptops/"),
            ("product_landing", "https://www.getac.com/us/products/tablets/"),
            ("product_landing", "https://www.getac.com/us/products/laptops/b360/"),
            ("product_landing", "https://www.getac.com/us/products/tablets/k120/"),
        ],
        "fcc_grantees": ["QYL", "MAU"],
        "license_observation": "Getac — proprietary all-rights-reserved",
    },
    {
        "slug": "dji",
        "canonical": "DJI",
        "robots_url": "https://www.dji.com/robots.txt",
        "robots_note": "Massive disallow list but /<product>/specs and dl.djicdn.com/* allowed",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.dji.com/sitemap.xml"),
            ("product_landing", "https://www.dji.com/mavic-3-enterprise/specs"),
            ("product_landing", "https://www.dji.com/matrice-30/specs"),
            ("product_landing", "https://www.dji.com/matrice-300/specs"),
            ("product_landing", "https://www.dji.com/dock-2/specs"),
            ("product_landing", "https://www.dji.com/mavic-3-pro/specs"),
        ],
        "fcc_grantees": ["2AS9X", "2AS9W", "2AS9V"],
        "license_observation": "DJI / SZ DJI Technology — proprietary all-rights-reserved",
    },
    {
        "slug": "parrot",
        "canonical": "Parrot",
        "robots_url": "https://www.parrot.com/robots.txt",
        "robots_note": "Drupal standard (admin only); product pages allowed",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.parrot.com/sitemap.xml"),
            ("product_landing", "https://www.parrot.com/us/drones/anafi-usa"),
            ("product_landing", "https://www.parrot.com/us/drones/anafi-ai"),
            ("product_landing", "https://www.parrot.com/us/drones/anafi"),
        ],
        "fcc_grantees": ["2AG6I"],
        "license_observation": "Parrot Drones SAS — proprietary all-rights-reserved",
    },
    {
        "slug": "soundthinking",
        "canonical": "SoundThinking",
        "robots_url": "https://www.soundthinking.com/robots.txt",
        "robots_note": "Crawl-delay: 10 (10s/req — MUST enforce client-side); only /wp-json/ blocked",
        "crawl_delay_s": 10.0,
        "urls": [
            ("sitemap", "https://www.soundthinking.com/sitemap_index.xml"),
            ("product_landing", "https://www.soundthinking.com/law-enforcement/shotspotter/"),
            ("product_landing", "https://www.soundthinking.com/law-enforcement/casebuilder/"),
            ("product_landing", "https://www.soundthinking.com/law-enforcement/safepointe/"),
        ],
        "fcc_grantees": ["WLI"],
        "license_observation": "SoundThinking (fmly ShotSpotter) — proprietary all-rights-reserved",
    },
    {
        "slug": "hak5",
        "canonical": "Hak5",
        "robots_url": "https://docs.hak5.org/robots.txt",
        "robots_note": "docs.hak5.org is the cleaner surface (404 robots.txt = no restriction); hak5.org Shopify policy allows non-checkout flows",
        "crawl_delay_s": 2.0,
        "urls": [
            ("docs_landing", "https://docs.hak5.org/hak5-docs"),
            ("docs_landing", "https://docs.hak5.org/wifi-pineapple"),
            ("docs_landing", "https://docs.hak5.org/bash-bunny"),
            ("docs_landing", "https://docs.hak5.org/packet-squirrel"),
            ("docs_landing", "https://docs.hak5.org/lan-turtle"),
            ("docs_landing", "https://docs.hak5.org/key-croc"),
        ],
        "fcc_grantees": [],
        "license_observation": "Hak5 LLC — Mintlify-hosted docs; proprietary all-rights-reserved",
    },
    {
        "slug": "cellebrite",
        "canonical": "Cellebrite",
        "robots_url": "https://cellebrite.com/robots.txt",
        "robots_note": "Yoast standard (admin paths only); product pages allowed; UFED technical docs paywalled to LE — out of scope per §11 #2",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://cellebrite.com/sitemap_index.xml"),
            ("product_landing", "https://cellebrite.com/en/ufed/"),
            ("product_landing", "https://cellebrite.com/en/inseyets/"),
            ("product_landing", "https://cellebrite.com/en/premium/"),
            ("product_landing", "https://cellebrite.com/en/responder/"),
        ],
        "fcc_grantees": [],
        "license_observation": "Cellebrite — proprietary all-rights-reserved (LE-customer-only docs §11 #2 not fetched)",
    },
    {
        "slug": "magnet_forensics",
        "canonical": "Magnet Forensics",
        "robots_url": "https://www.magnetforensics.com/robots.txt",
        "robots_note": "Yoast empty Disallow (open); AXIOM/GrayKey technical docs are customer-only — out of scope per §11 #2",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.magnetforensics.com/sitemap_index.xml"),
            ("product_landing", "https://www.magnetforensics.com/products/magnet-axiom/"),
            ("product_landing", "https://www.magnetforensics.com/products/magnet-graykey/"),
            ("product_landing", "https://www.magnetforensics.com/products/magnet-verakey/"),
            ("product_landing", "https://www.magnetforensics.com/products/magnet-review/"),
        ],
        "fcc_grantees": [],
        "license_observation": "Magnet Forensics — proprietary all-rights-reserved (customer-only docs §11 #2 not fetched)",
    },
    {
        "slug": "dedrone",
        "canonical": "Dedrone",
        "robots_url": "https://www.dedrone.com/robots.txt",
        "robots_note": "Disallow *?cta_guid=*, *page=*, */page/*, *rss.xml (URL-param/pagination noise); product pages allowed",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.dedrone.com/sitemap.xml"),
            ("product_landing", "https://www.dedrone.com/products"),
            ("product_landing", "https://www.dedrone.com/products/dedronesensor-rf-360"),
            ("product_landing", "https://www.dedrone.com/products/dedronetracker-ai"),
            ("product_landing", "https://www.dedrone.com/products/dedronedefender"),
        ],
        "fcc_grantees": ["2AO3N"],
        "license_observation": "Dedrone Holdings — proprietary all-rights-reserved",
    },
    {
        "slug": "droneshield",
        "canonical": "DroneShield",
        "robots_url": "https://www.droneshield.com/robots.txt",
        "robots_note": "AI-UA blocks (anthropic-ai, ClaudeBot, GPTBot, etc.) — Argus UA NOT a blocked AI UA. User-agent: * catch-all only blocks /config, /search, /account, /commerce, /api, /static; product pages allowed under custom Argus UA",
        "crawl_delay_s": 2.0,
        "urls": [
            ("sitemap", "https://www.droneshield.com/sitemap.xml"),
            ("product_landing", "https://www.droneshield.com/products/dronegun-tactical"),
            ("product_landing", "https://www.droneshield.com/products/dronesentry"),
            ("product_landing", "https://www.droneshield.com/products/rfpatrol"),
            ("product_landing", "https://www.droneshield.com/products/dronesentry-x"),
        ],
        "fcc_grantees": [],
        "license_observation": "DroneShield Ltd — proprietary all-rights-reserved",
    },
]

DOCUMENTED_SKIPS = [
    {
        "slug": "berla",
        "canonical": "Berla",
        "skip_reason": "robots.txt User-agent: * / Disallow: / fully blocks all UAs. SAR-4 verdict: skip + document. No legitimate alternative; Berla iVe technical docs are LE-trade-secret anyway. Wayback fallback NOT used (ToS-mirrored content; SAR-4 spirit = do not bypass robots via Wayback).",
        "robots_routing_evidence": "User-agent: *\\nDisallow: /",
        "fetched": False,
    },
    {
        "slug": "harris_stingray",
        "canonical": "Harris StingRay",
        "skip_reason": "Bible §2.1 #2 sealed/restricted; expect zero public vendor doc surface. Documented absence per §11 #1 (no fabrication). Phase 5 inference owns IMSI-catcher attribution from secondary sources (FOIA, court filings — Wave D territory).",
        "robots_routing_evidence": "n/a — no public vendor surface to query",
        "fetched": False,
    },
]

DEFERRED_RATIFICATION = [
    {
        "slug": "brinc",
        "canonical": "BRINC",
        "deferred_reason": "Primary host TLS-broken (cert is *.co.net, expired 2020). Wayback fallback only with explicit CEO ratification at first encounter. Step 1 attempts canonical host once to formally confirm TLS failure; surfaces ratification request in deliverable comment. Do NOT use -k insecure bypass per SAR-4 spirit.",
        "primary_url": "https://www.brinc.com/lemur",
        "robots_url": "https://www.brinc.com/robots.txt",
    },
]


def vendor_count_summary() -> dict:
    return {
        "fetched": len(VENDORS),
        "documented_skips": len(DOCUMENTED_SKIPS),
        "deferred_ratification": len(DEFERRED_RATIFICATION),
        "total_target_list_step0_matrix": 24,
        "harris_aside": 1,
    }


if __name__ == "__main__":
    import json as _json
    summary = vendor_count_summary()
    print(_json.dumps(summary, indent=2))
    print(f"\nVendor slugs ({len(VENDORS)}):")
    for v in VENDORS:
        urls = len(v["urls"])
        cd = v["crawl_delay_s"]
        print(f"  - {v['slug']:30s} {urls} URLs, crawl_delay={cd}s")
    print(f"\nDocumented skips ({len(DOCUMENTED_SKIPS)}):")
    for s in DOCUMENTED_SKIPS:
        print(f"  - {s['slug']}")
    print(f"\nDeferred ratification ({len(DEFERRED_RATIFICATION)}):")
    for d in DEFERRED_RATIFICATION:
        print(f"  - {d['slug']}")
