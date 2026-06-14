#!/usr/bin/env python3
"""MAC-398 cohort-5 (smart-home hubs / voice assistants) harvest scan.
STAGE ONLY — reads pinned raw artifacts + db/argus.db mode=ro. No writes to DB.
Vendors: Amazon Echo/Alexa, Google Nest Hub, Apple HomePod, Samsung SmartThings.
Subsidiaries annotated for cctv_camera double-promotion guard: Ring (Amazon), Nest (Google).
"""
import csv, re, sqlite3, sys

IEEE = {
    "MA-L": "raw/ieee_oui/20260613T203034Z_oui.csv",
    "MA-M": "raw/ieee_oui/20260613T203034Z_mam.csv",
    "MA-S": "raw/ieee_oui/20260613T203034Z_oui36.csv",
}
# vendor -> compiled org-name regex (case-insensitive, word-boundary where collision-prone)
VENDORS = {
    "Amazon":  re.compile(r"\bamazon\b|\blab126\b", re.I),
    "Google":  re.compile(r"\bgoogle\b", re.I),
    "Apple":   re.compile(r"\bapple\b", re.I),
    "Samsung": re.compile(r"\bsamsung\b", re.I),
    "Ring(Amazon-sub)":  re.compile(r"\bring\b", re.I),
    "Nest(Google-sub)":  re.compile(r"\bnest\b", re.I),
    "SmartThings(Samsung-sub)": re.compile(r"smartthings", re.I),
}

def to_oui_db(assignment, registry):
    a = assignment.lower()
    if registry == "MA-L":   # 24-bit, 6 hex
        return ":".join(a[i:i+2] for i in (0,2,4))               # 28:6f:b9
    if registry == "MA-M":   # 28-bit, 7 hex -> mac_range prefix oct:oct:oct:nibble
        return ":".join([a[0:2],a[2:4],a[4:6],a[6:7]])
    if registry == "MA-S":   # 36-bit, 9 hex
        return ":".join([a[0:2],a[2:4],a[4:6],a[6:7],a[7:8],a[8:9]])
    return a

con = sqlite3.connect("file:db/argus.db?mode=ro", uri=True)
cur = con.cursor()

# Preload DB oui + mac_range identifiers -> {identifier: (id, cat, mfr, type)}
dbidx = {}
for r in cur.execute("SELECT id,identifier,device_category,manufacturer,identifier_type FROM identifiers WHERE identifier_type IN ('oui','mac_range')"):
    dbidx[r[1].lower()] = (r[0], r[2], r[3], r[4])

def db_presence(dbform):
    # exact
    if dbform in dbidx:
        return dbidx[dbform]
    # MA-L 28:6f:b9 might be held as a mac_range prefix 28:6f:b9:x -> check prefix membership
    for k,v in dbidx.items():
        if k.startswith(dbform+":") or dbform.startswith(k+":"):
            return (v[0], v[1], v[2], v[3]+"(prefix-overlap "+k+")")
    return None

print("######## IEEE OUI MATCHES ########")
ieee_rows = []
for reg, path in IEEE.items():
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        rd = csv.reader(f)
        next(rd)  # header
        for row in rd:
            if len(row) < 3: continue
            registry, assignment, org = row[0], row[1], row[2]
            for v, rx in VENDORS.items():
                if rx.search(org):
                    dbform = to_oui_db(assignment, registry)
                    pres = db_presence(dbform)
                    ieee_rows.append((v, registry, assignment, dbform, org, pres))
# group by vendor
from collections import defaultdict
byv = defaultdict(list)
for x in ieee_rows: byv[x[0]].append(x)
for v in VENDORS:
    rows = byv.get(v, [])
    netnew = [r for r in rows if r[5] is None]
    held = [r for r in rows if r[5] is not None]
    print(f"\n== {v}: {len(rows)} OUI rows | NET-NEW {len(netnew)} | HELD {len(held)} ==")
    cats = defaultdict(int)
    for r in held: cats[r[5][1]] += 1
    if cats: print("   held device_category breakdown:", dict(cats))
    # print net-new (these are the candidate surface)
    for r in netnew[:60]:
        print(f"   NET-NEW {r[1]} {r[2]} -> {r[3]} | {r[4]!r}")
    if len(netnew) > 60: print(f"   ...(+{len(netnew)-60} more net-new)")

con.close()
