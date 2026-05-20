# Phase 7-bis fccid.io 177-row promotions log

**Dispatch:** [MAC-201](/MAC/issues/MAC-201)
**Parent:** [MAC-184](/MAC/issues/MAC-184) v1.4.1 Stage 1 integration
**Carved-out source:** [MAC-194](/MAC/issues/MAC-194) §7.2 halt
**CP31 ratification:** [MAC-197](/MAC/issues/MAC-197) (migration 0025 at `40b166e`)
**Branch HEAD pre-apply:** `cbb0cd7`
**Pre-apply DB backup:** `db/argus.db.mac201_pre_phase7bis_backup`

## Discipline envelope active

- §11 #1 (no fabrication) · §11 #7 (provenance) · §11 #8 (no conf drift)
- §11 #11 (amendment-log) · §11 #13 (device_category=`unknown` → DROP from high-conf export, by design)
- CP15 single-source crowdsourced ceiling: conf = 75
- SAR-9 canonical+alias manufacturer resolution
- CP31 routing rule: all 2AG → Parrot Automotive id=222
- MAC-196 routing rule: Numerex Corporation → Sierra Wireless id=21


## Wave I.14b (V2)

extraction_run_id = 114 · plan rows = 53


**Wave I.14b (V2) summary:** promoted grantee=0 (reused 53) · promoted equipment_class=0 (reused 53) · raw_observations inserted=0 · arm-routed (id=222)=0 · halts=0


## Wave I.14c (V3)

extraction_run_id = 115 · plan rows = 124


**Wave I.14c (V3) summary:** promoted grantee=0 (reused 124) · promoted equipment_class=0 (reused 124) · raw_observations inserted=0 · arm-routed (id=222)=19 · halts=0


## Pre / Post counts

| Metric | Pre | Post | Δ |
|--------|----:|-----:|---:|
| identifiers active (superseded_by IS NULL) | 34,968 | 34,968 | +0 |
| raw_observations | 146,573 | 146,573 | +0 |