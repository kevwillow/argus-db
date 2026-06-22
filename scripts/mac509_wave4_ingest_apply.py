#!/usr/bin/env python3
"""MAC-509 — Wave-4 CONSOLIDATED INGEST (CTO-led, board-AUTHORIZED) — canonical write.

Applies the board-ratified Wave-4 consolidated ingest slate (MAC-456 board go,
comment 96f74dac "Sounds good. Proceed.") to canonical ``db/argus.db``, FROM the
authoritative gate doc MAC-493 #document-ingest-gate (rev dee51e3b). Gate sequence:
per-lane ratify (MAC-496/497/498/499) -> CEO roll-up -> board OK (MAC-456) ->
INGEST (this script) -> export regen (separate step) -> board PUSH (CEO/board, NOT
here). NO push, NO tag. db/argus.db is gitignored.

Board-approved slate applied here (11 INSERT + 1 recat):

  C2 fleet telematics / AVL (8 oui -> automotive_telematics, conf 80, global,
     IEEE MA-L primary_registry; parity with shipped Sierra Wireless / Samsara):
    00:0a:99 CalAmp Wireless Networks Inc ; 64:fc:8c Zonar Systems ;
    2c:42:05 / 58:a7:48 / 70:e4:6e / 50:df:95 Lytx ;
    7c:a2:36 Verizon Connect ; 94:8f:ee Verizon Telematics.
    Verizon resolution: IEEE lists "Verizon Connect" (Alpharetta) and "Verizon
    Telematics" (Atlanta) as DISTINCT MA-L registrants. Verizon Telematics was
    rebranded Verizon Connect (2018) but the OUI registrant strings differ, so each
    identifier row keeps its cite-faithful IEEE registrant name; the alias is noted.

  C3 ALPR expansion (1 oui + 1 fcc grantee -> alpr):
    00:17:3d Neology -> oui / alpr, conf 85, global, IEEE MA-L. FEED-reaching.
    2AKNF Neology -> fcc_grantee_code / alpr, conf 85, FCC EAS grantees. Registry-
      internal (fcc_grantee_code is NOT a Lynceus feed pattern; 0 feed). Parity with
      shipped Remington Elsag VTF (id 44457), Leonardo 2AKB2/2ATWB (44458/44459).
    RECAT (board YES): id 21364 70:b3:d5:1c:5/36 mac_range ELSAG 'unknown' -> 'alpr'.
      mac_range is not a feed type -> registry-internal, 0 feed. Matches the shipped
      Remington Elsag ALPR line; notes JSON-merged (no text-suffix concat).

  C4 retail people-counting (1 oui):
    20:c3:a4 RetailNext -> oui / cctv_camera, conf 80, global, IEEE MA-L (board took
    the cctv_camera recommendation; no people_counter mint). FEED-reaching.

  NOT here: C1 (net-new 0), 45 Ubiquiti held-out, Leonardo defense mac_ranges (HOLD),
  Meraki CMX block, manufacturers hub-and-spoke registry rows (separately curated,
  non-feed; flagged to CEO), MAC-477 contamination sweep (own board gate).

Net-new feed projection (DELTA, measured at regen): +10 standard / +10 high-confidence
/ +11 active. NOTE: the gate doc's ABSOLUTE targets (1,052/479/43,285) assumed the
PRE-MAC-477 baseline; MAC-477 Track-A (commit 8cfed9f) is already applied to this
canonical DB (active 43,274 -> 43,166; standard 1,042 -> 935; hc 469 -> 468), so the
true post-ingest absolutes are ~945 / ~478 / 43,177. The DELTA is the proof.

Migration-safety (same battery as wave-2 MAC-419 / wave-3 MAC-490): backup-first
(timestamped + .sha256, gitignored db/argus.db*.bak); re-query live baseline with
STOP-on-out-of-band-drift; insert via AUTOINCREMENT (no explicit id); cite-paste
source_excerpt = exact IEEE/FCC bytes; fresh JSON notes (json.dumps, never text-suffix
concat); recat notes JSON-merged by property; json_valid sweep over every touched row;
per-row lookup uniqueness (idempotent skip on (identifier, identifier_type)); FULL-
COLUMN reconstruction diff vs the backup (only allowed change = id 21364 recat; only
allowed adds = the 11 new ids; zero deletes); invariant rollback.

Usage:
  python3 scripts/mac509_wave4_ingest_apply.py --db <path> [--no-backup]
                                               [--expect-total N] [--expect-active N] [--force]

NO export regen here (separate step). NO push. NO tag.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXPECT_TOTAL = 43829   # canonical baseline (post v1.6.11 + MAC-477 Track-A, schema 33)
EXPECT_ACTIVE = 43166  # active (superseded_by IS NULL), post MAC-477 withdrawal of 108
EXPECT_SCHEMA = 33
PRIOR_MAXID = 44647    # new rows must land strictly above this
ISSUE = "MAC-509"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
IEEE_URL = "https://standards-oui.ieee.org/oui/oui.csv"
FCC_URL = "https://opendata.fcc.gov/Engineering/FCC-EAS-Grantee-Codes/3b3k-34jp"

# ── ELSAG recat (board YES) ─────────────────────────────────────────────────
RECAT_ID = 21364
RECAT_FROM = "unknown"
RECAT_TO = "alpr"
RECAT_EXPECT_TYPE = "mac_range"
RECAT_EXPECT_MFR = "ELSAG"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def trunc(s, n=200):
    if s is None:
        return None
    return s if len(s) <= n else s[:n]


def N(**extra):
    d = {"wave": "wave4", "ingest_issue": ISSUE, "applied_utc": NOW}
    d.update(extra)
    return json.dumps(d, ensure_ascii=False)


# ── 11 INSERT rows (cite-paste source_excerpt = exact bytes verified at author time) ──
ROWS = [
    # C2 fleet telematics / AVL (MAC-497) — automotive_telematics, conf 80, global
    dict(identifier="00:0a:99", identifier_type="oui", device_category="automotive_telematics",
         manufacturer="CalAmp Wireless Networks Inc", confidence=80, source_url=IEEE_URL,
         source_type="primary_registry", geographic_scope="global",
         source_excerpt="MA-L,000A99,Calamp Wireless Networks Inc,101-5540 Ferrier Street Town of Mount-Royal Quebec CA H4P 1M2",
         notes=N(lane="C2", issue="MAC-497", cohort="fleet_telematics", basis="IEEE MA-L; CalAmp AVL/telematics; existing automotive_telematics category (Samsara/Sierra parity)")),
    dict(identifier="64:fc:8c", identifier_type="oui", device_category="automotive_telematics",
         manufacturer="Zonar Systems", confidence=80, source_url=IEEE_URL,
         source_type="primary_registry", geographic_scope="global",
         source_excerpt="MA-L,64FC8C,Zonar Systems,18200 Cascade Ave South Seattle WA US 98118",
         notes=N(lane="C2", issue="MAC-497", cohort="fleet_telematics", basis="IEEE MA-L; Zonar fleet telematics")),
    dict(identifier="2c:42:05", identifier_type="oui", device_category="automotive_telematics",
         manufacturer="Lytx", confidence=80, source_url=IEEE_URL,
         source_type="primary_registry", geographic_scope="global",
         source_excerpt="MA-L,2C4205,Lytx,9785 Towne Centre Drive San Diego CA US 92121",
         notes=N(lane="C2", issue="MAC-497", cohort="fleet_telematics", basis="IEEE MA-L; Lytx DriveCam fleet AVL")),
    dict(identifier="58:a7:48", identifier_type="oui", device_category="automotive_telematics",
         manufacturer="Lytx", confidence=80, source_url=IEEE_URL,
         source_type="primary_registry", geographic_scope="global",
         source_excerpt="MA-L,58A748,Lytx,9785 Towne Centre Drive San Diego CA US 92121",
         notes=N(lane="C2", issue="MAC-497", cohort="fleet_telematics", basis="IEEE MA-L; Lytx (same registrant block)")),
    dict(identifier="70:e4:6e", identifier_type="oui", device_category="automotive_telematics",
         manufacturer="Lytx", confidence=80, source_url=IEEE_URL,
         source_type="primary_registry", geographic_scope="global",
         source_excerpt="MA-L,70E46E,Lytx,9785 Towne Centre Drive San Diego CA US 92121",
         notes=N(lane="C2", issue="MAC-497", cohort="fleet_telematics", basis="IEEE MA-L; Lytx (same registrant block)")),
    dict(identifier="50:df:95", identifier_type="oui", device_category="automotive_telematics",
         manufacturer="Lytx", confidence=80, source_url=IEEE_URL,
         source_type="primary_registry", geographic_scope="global",
         source_excerpt="MA-L,50DF95,Lytx,9785 Towne Centre Drive San Diego CA US 92121",
         notes=N(lane="C2", issue="MAC-497", cohort="fleet_telematics", basis="IEEE MA-L; Lytx (same registrant block)")),
    dict(identifier="7c:a2:36", identifier_type="oui", device_category="automotive_telematics",
         manufacturer="Verizon Connect", confidence=80, source_url=IEEE_URL,
         source_type="primary_registry", geographic_scope="global",
         source_excerpt="MA-L,7CA236,Verizon Connect,5055 North Point Pkwy Alpharetta GA US 30022",
         notes=N(lane="C2", issue="MAC-497", cohort="fleet_telematics", basis="IEEE MA-L; Verizon Connect (Alpharetta) fleet telematics")),
    dict(identifier="94:8f:ee", identifier_type="oui", device_category="automotive_telematics",
         manufacturer="Verizon Telematics", confidence=80, source_url=IEEE_URL,
         source_type="primary_registry", geographic_scope="global",
         source_excerpt="MA-L,948FEE,Verizon Telematics,2002 Summit Blvd Atlanta GA US 30319",
         notes=N(lane="C2", issue="MAC-497", cohort="fleet_telematics", basis="IEEE MA-L; Verizon Telematics (Atlanta) — distinct MA-L registrant from Verizon Connect; rebranded Verizon Connect 2018", alias_of="Verizon Connect")),
    # C3 ALPR expansion (MAC-498) — alpr
    dict(identifier="00:17:3d", identifier_type="oui", device_category="alpr",
         manufacturer="Neology", confidence=85, source_url=IEEE_URL,
         source_type="primary_registry", geographic_scope="global",
         source_excerpt="MA-L,00173D,Neology,13000 Gregg Street Suite A Poway CA US 92064",
         notes=N(lane="C3", issue="MAC-498", cohort="alpr_expansion", basis="IEEE MA-L; Neology RFID/ALPR tolling+LPR; existing alpr category. FEED-reaching")),
    dict(identifier="2AKNF", identifier_type="fcc_grantee_code", device_category="alpr",
         manufacturer="Neology", confidence=85, source_url=FCC_URL,
         source_type="primary_registry", geographic_scope=None,
         source_excerpt="2AKNF | Neology | United States (FCC EAS grantee; Poway CA; received 2016-12-14)",
         notes=N(lane="C3", issue="MAC-498", cohort="alpr_expansion", basis="FCC EAS grantee; registry-internal (fcc_grantee_code not a Lynceus feed pattern; 0 feed); parity Remington Elsag VTF / Leonardo 2AKB2/2ATWB")),
    # C4 retail people-counting (MAC-499) — cctv_camera (board took recommendation)
    dict(identifier="20:c3:a4", identifier_type="oui", device_category="cctv_camera",
         manufacturer="RetailNext", confidence=80, source_url=IEEE_URL,
         source_type="primary_registry", geographic_scope="global",
         source_excerpt='MA-L,20C3A4,RetailNext,"60 S. Market St, 10th Floor San Jose CA US 95113"',
         notes=N(lane="C4", issue="MAC-499", cohort="retail_people_counting", basis="IEEE MA-L; RetailNext Aurora = Sony megapixel camera w/ onboard person-detection; board cctv_camera (no people_counter mint). FEED-reaching")),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--expect-total", type=int, default=EXPECT_TOTAL)
    ap.add_argument("--expect-active", type=int, default=EXPECT_ACTIVE)
    ap.add_argument("--force", action="store_true", help="proceed despite baseline drift")
    args = ap.parse_args()
    DB: Path = args.db
    if not DB.exists():
        print(f"FATAL: db not found {DB}")
        return 2

    con = sqlite3.connect(str(DB), isolation_level=None)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    def one(sql, a=()):
        return cur.execute(sql, a).fetchone()[0]

    # ---- preconditions (STOP on out-of-band drift) ----
    schema = one("SELECT MAX(version) FROM schema_version")
    total = one("SELECT COUNT(*) FROM identifiers")
    active = one("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL")
    maxid = one("SELECT MAX(id) FROM identifiers")
    print(f"baseline: schema={schema} total={total} active={active} maxid={maxid}")
    drift = []
    if schema != EXPECT_SCHEMA:
        drift.append(f"schema {schema}!={EXPECT_SCHEMA}")
    if total != args.expect_total:
        drift.append(f"total {total}!={args.expect_total}")
    if active != args.expect_active:
        drift.append(f"active {active}!={args.expect_active}")
    if maxid != PRIOR_MAXID:
        drift.append(f"maxid {maxid}!={PRIOR_MAXID}")
    if drift and not args.force:
        print(f"STOP: baseline drift {drift} (use --force to override)")
        return 3

    # ---- backup-first ----
    pre_sha = sha256_of(DB)
    print(f"pre-sha {pre_sha[:16]}")
    bak = None
    if not args.no_backup:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bak = DB.with_name(DB.name + f".mac509_pre_apply_{stamp}.bak")
        shutil.copy2(DB, bak)
        bak.with_name(bak.name + ".sha256").write_text(f"{pre_sha}  {bak.name}\n")
        print(f"backup -> {bak.name}")

    cur.execute("BEGIN")
    try:
        # ---- ELSAG recat (id 21364 unknown -> alpr; JSON-merge notes) ----
        r = cur.execute("SELECT identifier, identifier_type, device_category, manufacturer, notes "
                        "FROM identifiers WHERE id=?", (RECAT_ID,)).fetchone()
        if r is None:
            raise RuntimeError(f"RECAT precondition fail: id{RECAT_ID} absent")
        if r["identifier_type"] != RECAT_EXPECT_TYPE:
            raise RuntimeError(f"RECAT precondition fail: id{RECAT_ID} type={r['identifier_type']} != {RECAT_EXPECT_TYPE}")
        if (r["manufacturer"] or "") != RECAT_EXPECT_MFR:
            raise RuntimeError(f"RECAT precondition fail: id{RECAT_ID} mfr={r['manufacturer']!r} != {RECAT_EXPECT_MFR}")
        if r["device_category"] == RECAT_TO:
            recat = "already alpr (idempotent skip)"
        elif r["device_category"] == RECAT_FROM:
            # JSON-merge: preserve all existing properties, add recat provenance.
            try:
                base = json.loads(r["notes"]) if r["notes"] else {}
                if not isinstance(base, dict):
                    base = {"_prior_notes": r["notes"]}
            except Exception:
                base = {"_prior_notes": r["notes"]}
            base["mac509_recat"] = f"{RECAT_FROM}->{RECAT_TO} (Wave-4 C3 MAC-498; board YES; ELSAG ALPR line parity w/ Remington Elsag)"
            base["mac509_recat_applied_utc"] = NOW
            merged = json.dumps(base, ensure_ascii=False)
            cur.execute("UPDATE identifiers SET device_category=?, notes=? "
                        "WHERE id=? AND device_category=? AND identifier_type=?",
                        (RECAT_TO, merged, RECAT_ID, RECAT_FROM, RECAT_EXPECT_TYPE))
            recat = f"recat {RECAT_FROM}->{RECAT_TO}"
        else:
            raise RuntimeError(f"RECAT precondition fail: id{RECAT_ID} cat={r['device_category']!r} not in (unknown,alpr)")
        print(f"RECAT id{RECAT_ID}: {recat}")

        # ---- 11 INSERTs (idempotent on (identifier, identifier_type)) ----
        INS = ("INSERT INTO identifiers (identifier, identifier_type, device_category, manufacturer, "
               "confidence, source_url, source_type, source_excerpt, geographic_scope, first_seen, "
               "last_verified, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)")
        inserted, skipped, new_ids = [], [], []
        for row in ROWS:
            exists = cur.execute(
                "SELECT id FROM identifiers WHERE identifier=? AND identifier_type=?",
                (row["identifier"], row["identifier_type"])).fetchone()
            if exists:
                skipped.append((row["identifier"], row["identifier_type"], exists["id"]))
                continue
            cur.execute(INS, (
                row["identifier"], row["identifier_type"], row["device_category"], row["manufacturer"],
                row["confidence"], row["source_url"], row["source_type"], trunc(row["source_excerpt"]),
                row["geographic_scope"], NOW, NOW, row["notes"]))
            new_ids.append(cur.lastrowid)
            inserted.append((row["identifier"], row["identifier_type"], row["device_category"], cur.lastrowid))

        # ---- json_valid sweep over every touched row (new + recat) ----
        touched = list(new_ids) + [RECAT_ID]
        ph = ",".join("?" * len(touched))
        bad = one(f"SELECT COUNT(*) FROM identifiers WHERE id IN ({ph}) AND json_valid(notes)=0", touched)
        if bad:
            raise RuntimeError(f"json_valid=0 on {bad} touched rows")
        if new_ids:
            phn = ",".join("?" * len(new_ids))
            longx = one(f"SELECT COUNT(*) FROM identifiers WHERE id IN ({phn}) AND source_excerpt IS NOT NULL AND length(source_excerpt)>200", new_ids)
            if longx:
                raise RuntimeError(f"source_excerpt>200 on {longx} new rows")
            minnew = one(f"SELECT MIN(id) FROM identifiers WHERE id IN ({phn})", new_ids)
            if minnew <= maxid:
                raise RuntimeError(f"new id {minnew} collides with prior maxid {maxid}")

        # ---- FULL-COLUMN reconstruction diff vs backup ----
        recon_ok = True
        if bak is not None:
            cols = "id,identifier,identifier_type,device_category,manufacturer,model,confidence,source_url,source_type,source_excerpt,geographic_scope,notes,superseded_by,paired_identifier_id,pair_kind,severity"
            bcon = sqlite3.connect(f"file:{bak}?mode=ro", uri=True)
            bcon.row_factory = sqlite3.Row
            pre = {x["id"]: tuple(x) for x in bcon.execute(f"SELECT {cols} FROM identifiers").fetchall()}
            bcon.close()
            post = {x["id"]: tuple(x) for x in cur.execute(f"SELECT {cols} FROM identifiers").fetchall()}
            added = set(post) - set(pre)
            deleted = set(pre) - set(post)
            changed = {i for i in (set(pre) & set(post)) if pre[i] != post[i]}
            print(f"RECON vs backup: added={len(added)} deleted={len(deleted)} changed={sorted(changed)}")
            if deleted:
                recon_ok = False
                print(f"  FAIL: {len(deleted)} rows deleted (expected 0)")
            if added != set(new_ids):
                recon_ok = False
                print(f"  FAIL: added set != new_ids ({len(added)} vs {len(new_ids)})")
            allowed_changed = {RECAT_ID} if recat.startswith("recat") else set()
            if changed != allowed_changed:
                recon_ok = False
                print(f"  FAIL: changed set {sorted(changed)} != allowed {sorted(allowed_changed)}")

        print(f"\nINSERTED {len(inserted)}  SKIPPED {len(skipped)}  RECAT {recat}")
        for t in inserted:
            print(f"  + id{t[3]:<6} {t[1]:<18} {t[2]:<22} {t[0]}")
        for s in skipped:
            print(f"  = SKIP (exists id{s[2]}) {s[1]:<18} {s[0]}")

        if not recon_ok:
            cur.execute("ROLLBACK")
            print("\nROLLED BACK (reconstruction invariant failed).")
            return 4

        cur.execute("COMMIT")
    except Exception as e:
        cur.execute("ROLLBACK")
        print(f"\nROLLED BACK: {e}")
        return 5

    post_sha = sha256_of(DB)
    post_total = one("SELECT COUNT(*) FROM identifiers")
    post_active = one("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL")
    print(f"\nCOMMITTED. post-sha {post_sha[:16]}")
    print(f"post: total={post_total} (+{post_total-total}) active={post_active} (+{post_active-active})")
    if bak is not None:
        print(f"backup={bak.name} pre-sha={pre_sha[:16]}")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
