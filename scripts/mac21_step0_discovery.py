"""MAC-21 Phase 4 Wave-A Step 0 — GitHub anchored-mining discovery.

Discovery + scope ratification only (per §7.1 SourceWorker scope + SAR-6 #1):
- NO writes to db/argus.db
- NO `raw_observations` rows
- NO LLM calls (regex+keyword sweep only)

Surfaces enumerated via REST API (publisher-provided alternative under
SAR-4 — github.com/robots.txt disallows /*/raw/, /search$, /*q=, /gist/;
robots.txt header explicitly names the API as the legitimate path):

  1. Repository search   /search/repositories?q={vendor}+sort:stars
  2. Issue search        /search/issues?q={vendor}+is:issue
  3. Vendor org pages    /orgs/{slug} (curated guesses)

  Code search via /search/code requires authentication — DEFERRED to
  Step 1 PAT-provisioning approval; documented in ratification comment.

  Public gist search via /search/gists — REMOVED from Wave-A scope by the
  worker as low-yield-noise tax; gist results in repo-search/issue-search
  already surface via repo authorship. Also deferred behind PAT if
  re-included at Step 1.

Outputs all under raw/github/<run-ts>/_step0/:
  - per_vendor_repos.json     (search/repositories results, 34 vendors)
  - per_vendor_issues.json    (search/issues results, 34 vendors)
  - org_enumeration.json      (curated vendor-org probe)
  - _manifest.json            (call accounting, rate-limit headers)
  - logs/mac21_step0_discovery_<run-ts>.log
"""
from __future__ import annotations

import hashlib
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "ArgusSourceWorker/0.1 (Phase4 Wave-A Step 0 discovery; +https://github.com/argus-project)"
TIMEOUT_S = 30
SEARCH_SPACING_S = 7.0  # 10/min unauth -> safe at 7s
CORE_SPACING_S = 1.5

REPO_ROOT = Path("/home/kev/argus")
TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
OUT = REPO_ROOT / "raw" / "github" / TS / "_step0"
OUT.mkdir(parents=True, exist_ok=True)
LOG = REPO_ROOT / "logs" / f"mac21_step0_discovery_{TS}.log"
LOG.parent.mkdir(parents=True, exist_ok=True)


# 34 manufacturers (canonical names from db/argus.db `manufacturers` table)
VENDORS = [
    "Avigilon", "Axis Communications", "Axon", "Berla", "BRINC", "BriefCam",
    "Cellebrite", "Clearview AI", "Cradlepoint", "Dedrone",
    "Digital Receiver Technology", "DJI", "DroneShield", "Engility",
    "Flock Safety", "Genetec", "Getac", "Hak5", "Harris", "Jacobs", "Kenwood",
    "KeyW", "L3Harris", "Magnet Forensics", "Motorola Solutions", "Parrot",
    "Rekor", "Reveal", "Septier", "Sierra Wireless", "Skydio", "SoundThinking",
    "Vigilant Solutions", "WatchGuard",
]

# Curated vendor-org guesses (most vendors have NO public org; absence is
# itself a §11 #1 finding). Source: vendor SDK documentation references seen
# in MAC-13/MAC-19 fetches.
VENDOR_ORG_GUESSES = {
    "DJI": ["dji-sdk", "dji"],
    "Parrot": ["Parrot-Developers", "ARDroneSDK3"],
    "Hak5": ["hak5", "hak5darren"],
    "Skydio": ["Skydio"],
    "Sierra Wireless": ["sierrawireless"],
    "Cradlepoint": ["cradlepoint"],
    "BRINC": ["BRINC-Drone", "BRINC-Drones"],
    "Cellebrite": ["cellebrite"],
    "Magnet Forensics": ["magnetforensics"],
    "Berla": ["BerlaCorp"],
    "Genetec": ["Genetec"],
    "Avigilon": ["avigilon"],
    "Axis Communications": ["AxisCommunications"],
    "Motorola Solutions": ["MotorolaSolutions"],
    "L3Harris": ["L3Harris"],
    "Axon": ["axon"],
    "DroneShield": ["DroneShield"],
    "Dedrone": ["Dedrone"],
    "Flock Safety": ["FlockSafety", "flock-safety"],
    "Rekor": ["RekorAI", "RekorSystems"],
    "WatchGuard": ["WatchGuard"],
    "Reveal": ["RevealMedia"],
    "Getac": ["getac"],
    "BriefCam": ["briefcam"],
    "Clearview AI": ["clearviewai"],
    "SoundThinking": ["SoundThinking", "ShotSpotterInc"],
    "Vigilant Solutions": ["VigilantSolutions"],
    "Kenwood": ["kenwood"],
    "Harris": ["harris"],
    # No guesses for: Engility, Jacobs, KeyW, Septier, Digital Receiver
    # Technology — likely no public GitHub presence (defense-only / private).
}


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def http_get(url: str, accept: str = "application/vnd.github+json") -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    ctx = ssl.create_default_context()
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S, context=ctx) as r:
            body = r.read()
            return {
                "status": r.status,
                "final_url": r.geturl(),
                "headers": dict(r.headers),
                "body": body,
                "byte_count": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "elapsed_s": round(time.time() - t0, 3),
                "error": None,
            }
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        return {
            "status": e.code,
            "final_url": url,
            "headers": dict(e.headers) if hasattr(e, "headers") else {},
            "body": body,
            "byte_count": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "elapsed_s": round(time.time() - t0, 3),
            "error": f"HTTPError {e.code}",
        }
    except Exception as e:
        return {
            "status": None,
            "final_url": url,
            "headers": {},
            "body": b"",
            "byte_count": 0,
            "sha256": "",
            "elapsed_s": round(time.time() - t0, 3),
            "error": repr(e),
        }


def short_repo_record(item: dict) -> dict:
    """Compact a /search/repositories item to inventory shape."""
    return {
        "full_name": item.get("full_name"),
        "html_url": item.get("html_url"),
        "description": (item.get("description") or "")[:200],
        "stars": item.get("stargazers_count"),
        "language": item.get("language"),
        "fork": item.get("fork"),
        "archived": item.get("archived"),
        "default_branch": item.get("default_branch"),
        "size_kb": item.get("size"),
        "updated_at": item.get("updated_at"),
        "license": (item.get("license") or {}).get("spdx_id") if item.get("license") else None,
        "owner": (item.get("owner") or {}).get("login"),
    }


def short_issue_record(item: dict) -> dict:
    return {
        "title": (item.get("title") or "")[:200],
        "html_url": item.get("html_url"),
        "state": item.get("state"),
        "comments": item.get("comments"),
        "created_at": item.get("created_at"),
        "repository_url": item.get("repository_url"),
        "user_login": (item.get("user") or {}).get("login"),
    }


def main() -> int:
    log(f"MAC-21 Step-0 discovery start; out={OUT}")
    manifest = {
        "run_ts": TS,
        "user_agent": UA,
        "vendors_count": len(VENDORS),
        "calls": {"search_repos": 0, "search_issues": 0, "core_orgs": 0},
        "rate_limit_seen": [],
    }

    # ─── Surface 1: /search/repositories per vendor ─────────────────────────
    repos_by_vendor: dict[str, dict] = {}
    log(f"Surface 1: /search/repositories — {len(VENDORS)} vendors @ {SEARCH_SPACING_S}s spacing")
    for i, vendor in enumerate(VENDORS, 1):
        q = urllib.parse.quote_plus(f'"{vendor}"')
        url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=10"
        r = http_get(url)
        manifest["calls"]["search_repos"] += 1
        rl = {
            "vendor": vendor,
            "endpoint": "search/repositories",
            "limit": r["headers"].get("X-RateLimit-Limit"),
            "remaining": r["headers"].get("X-RateLimit-Remaining"),
            "reset": r["headers"].get("X-RateLimit-Reset"),
        }
        manifest["rate_limit_seen"].append(rl)
        if r["status"] == 200:
            data = json.loads(r["body"])
            items = [short_repo_record(it) for it in data.get("items", [])[:10]]
            repos_by_vendor[vendor] = {
                "query": f'"{vendor}"',
                "total_count": data.get("total_count"),
                "items": items,
            }
            log(f"  [{i:2d}/{len(VENDORS)}] {vendor}: {data.get('total_count')} total, top {len(items)} captured (rl_remaining={rl['remaining']})")
        else:
            repos_by_vendor[vendor] = {
                "query": f'"{vendor}"',
                "error": r["error"],
                "status": r["status"],
                "body_excerpt": r["body"][:200].decode(errors="replace"),
            }
            log(f"  [{i:2d}/{len(VENDORS)}] {vendor}: ERROR status={r['status']} {r['error']}")
        time.sleep(SEARCH_SPACING_S)

    (OUT / "per_vendor_repos.json").write_text(json.dumps(repos_by_vendor, indent=2))
    log(f"Wrote per_vendor_repos.json")

    # ─── Surface 2: /search/issues per vendor ───────────────────────────────
    issues_by_vendor: dict[str, dict] = {}
    log(f"Surface 2: /search/issues — {len(VENDORS)} vendors @ {SEARCH_SPACING_S}s spacing")
    for i, vendor in enumerate(VENDORS, 1):
        q = urllib.parse.quote_plus(f'"{vendor}" is:issue')
        url = f"https://api.github.com/search/issues?q={q}&sort=comments&order=desc&per_page=10"
        r = http_get(url)
        manifest["calls"]["search_issues"] += 1
        rl = {
            "vendor": vendor,
            "endpoint": "search/issues",
            "limit": r["headers"].get("X-RateLimit-Limit"),
            "remaining": r["headers"].get("X-RateLimit-Remaining"),
            "reset": r["headers"].get("X-RateLimit-Reset"),
        }
        manifest["rate_limit_seen"].append(rl)
        if r["status"] == 200:
            data = json.loads(r["body"])
            items = [short_issue_record(it) for it in data.get("items", [])[:10]]
            issues_by_vendor[vendor] = {
                "query": f'"{vendor}" is:issue',
                "total_count": data.get("total_count"),
                "items": items,
            }
            log(f"  [{i:2d}/{len(VENDORS)}] {vendor}: {data.get('total_count')} total, top {len(items)} captured (rl_remaining={rl['remaining']})")
        else:
            issues_by_vendor[vendor] = {
                "query": f'"{vendor}" is:issue',
                "error": r["error"],
                "status": r["status"],
                "body_excerpt": r["body"][:200].decode(errors="replace"),
            }
            log(f"  [{i:2d}/{len(VENDORS)}] {vendor}: ERROR status={r['status']} {r['error']}")
        time.sleep(SEARCH_SPACING_S)

    (OUT / "per_vendor_issues.json").write_text(json.dumps(issues_by_vendor, indent=2))
    log(f"Wrote per_vendor_issues.json")

    # ─── Surface 3: vendor org pages (curated guesses) ──────────────────────
    org_results: dict[str, dict] = {}
    log(f"Surface 3: vendor org enumeration — {sum(len(v) for v in VENDOR_ORG_GUESSES.values())} probes @ {CORE_SPACING_S}s spacing")
    for vendor, slugs in VENDOR_ORG_GUESSES.items():
        org_results[vendor] = []
        for slug in slugs:
            url = f"https://api.github.com/orgs/{urllib.parse.quote(slug)}"
            r = http_get(url)
            manifest["calls"]["core_orgs"] += 1
            rl = {
                "vendor": vendor,
                "slug": slug,
                "endpoint": "orgs/{slug}",
                "limit": r["headers"].get("X-RateLimit-Limit"),
                "remaining": r["headers"].get("X-RateLimit-Remaining"),
                "reset": r["headers"].get("X-RateLimit-Reset"),
            }
            manifest["rate_limit_seen"].append(rl)
            rec: dict = {"slug": slug, "status": r["status"]}
            if r["status"] == 200:
                d = json.loads(r["body"])
                rec.update({
                    "name": d.get("name"),
                    "html_url": d.get("html_url"),
                    "public_repos": d.get("public_repos"),
                    "blog": d.get("blog"),
                    "description": (d.get("description") or "")[:200],
                    "type": d.get("type"),
                    "created_at": d.get("created_at"),
                })
            elif r["status"] == 404:
                rec["note"] = "not_found_under_orgs_slug"
            else:
                rec["error"] = r["error"]
            org_results[vendor].append(rec)
            log(f"  {vendor}/{slug}: status={r['status']} (rl_remaining={rl['remaining']})")
            time.sleep(CORE_SPACING_S)

    (OUT / "org_enumeration.json").write_text(json.dumps(org_results, indent=2))
    log(f"Wrote org_enumeration.json")

    # ─── Manifest write ─────────────────────────────────────────────────────
    manifest["closed_at"] = datetime.now(timezone.utc).isoformat()
    (OUT / "_manifest.json").write_text(json.dumps(manifest, indent=2))
    log(f"Wrote _manifest.json — total calls: search_repos={manifest['calls']['search_repos']}, search_issues={manifest['calls']['search_issues']}, core_orgs={manifest['calls']['core_orgs']}")
    log("MAC-21 Step-0 discovery DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
