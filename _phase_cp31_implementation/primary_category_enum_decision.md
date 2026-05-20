# CP31 — `manufacturers.primary_category` enum decision (PRAGMA pre-flight)

**Date:** 2026-05-20
**Author:** DBArchitect (agent 6c93a466-d498-49e0-b7af-3fc0d08eb2b0)
**Issue:** MAC-198
**Parent:** MAC-184 (v1.4.1 Stage 1 integration) / MAC-197 (CP31 plan accept `d59e6af5`)

## Question

The dispatch (MAC-198 §3) asks whether `manufacturers.primary_category` already carries a value that fits Parrot Faurecia Automotive (REUSE), or whether the CHECK enum must be extended to admit `automotive_telematics` (EXTEND).

## PRAGMA verification — live schema (paste-not-cite)

Live DDL for `manufacturers` (sourced from `sqlite_master.sql` on `db/argus.db`,
schema version 24 immediately pre-CP31):

```sql
CREATE TABLE manufacturers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name  TEXT NOT NULL UNIQUE,
    aliases         TEXT,           -- comma-separated alternate names
    primary_category TEXT,          -- best-fit §2.1 category, NULL when multi-purpose
    source_url      TEXT NOT NULL,  -- where the canonical name comes from (bible itself is fine)
    notes           TEXT,
    added_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

**`primary_category` is plain `TEXT NULL`. There is NO `CHECK` constraint on this column.** The bible §4.2 entry for `manufacturers` likewise carries no `primary_category` enum spec (column shape only documented inline at §4.3 manufacturer-matching prose).

## In-use `primary_category` value distribution (51 rows pre-CP31)

```
  12  NULL
   8  body_cam
   7  alpr
   6  imsi_catcher
   6  drone
   4  hacking_tool
   2  unknown
   2  face_recog
   2  drone_detect
   1  police_radio
   1  gunshot_detect
```

All non-NULL values are §2.1-style device-category strings (matching the
`identifiers.device_category` CHECK enum vocabulary). None covers automotive
infotainment / telematics.

## Decision

**Neither REUSE nor EXTEND — SKIP.** The dispatch's binary presupposes an
existing CHECK enum to extend. The live schema has none. Adding a `CHECK`
constraint not present in bible §4 would be **SAR-13 schema fabrication**
(inventing constraints beyond the bible spec) — the same anti-pattern the
SAR-13 + sub-rule §3399 pre-flight discipline exists to prevent.

The new Parrot Automotive arm row will carry `primary_category = 'automotive_telematics'`
as a **free-form TEXT value**, fully admitted by the existing schema. No
CHECK is added or modified for this column in migration 0025.

This decision narrows the migration's CHECK-enum surface to two columns
(`identifiers.identifier_type`, `identifiers.pair_kind`) plus the hub-and-spoke
column additions on `manufacturers`. Net effect for primary_category: a new
free-form value enters the value-class space; future migrations may codify
device-category-vs-non-device-category as a CHECK if/when the bible §4
formally specs one.

## Cross-references

- Bible §4.1, §4.2, §4.3 (manufacturers spec — no `primary_category` CHECK)
- Bible §11 anti-fabrication discipline
- SAR-13 + sub-rule §3399 PRAGMA-first discipline (migration 0024 header)
- MAC-197 CP31 plan rev `d59e6af5` board-accept
- MAC-198 dispatch (this issue) §3 PRAGMA-verify step
