# Phase 7 §7.4 — fccid.io filing URL inventory hand-off log

**Dispatch ref:** [MAC-194](/MAC/issues/MAC-194) §7.4
**Total URLs catalogued:** 947 (Wave I.14b 709 + Wave I.14c 238)
**Promoted to identifiers:** 0 (URL inventory is INFORMATIONAL only — feeds v1.5.0 deep-mine)
**Stage shape:** `manufacturers.notes.v1_5_0_filing_url_inventory[]`

## Per-manufacturer breakdown

| canonical_name | mfr_id | V2 (I.14b) | V3 (I.14c) | newly_appended | total_after_apply |
|---------------|-------:|-----------:|-----------:|---------------:|-----------------:|
| Axon | 15 | 0 | 6 | 6 | 6 |
| Cradlepoint | 20 | 0 | 7 | 7 | 7 |
| DJI | 22 | 0 | 4 | 4 | 4 |
| Harris | 8 | 0 | 30 | 30 | 30 |
| Motorola Solutions | 3 | 283 | 0 | 283 | 283 |
| Parrot | 25 | 0 | 20 | 20 | 20 |
| Sierra Wireless | 21 | 426 | 171 | 597 | 597 |

## Grantee → canonical mapping table

| FCC EAS grantee_name | canonical_name |
|----------------------|----------------|
| Axon Enterprise, Inc | Axon |
| Cradlepoint, Inc. | Cradlepoint |
| Harris Corporation | Harris |
| Motorola Solutions, Inc. | Motorola Solutions |
| PARROT DRONE SAS | Parrot |
| SZ DJI BaiWang Technology Co.,Ltd | DJI |
| Sierra Wireless Inc | Sierra Wireless |
| Sierra Wireless Inc. | Sierra Wireless |
| Sierra Wireless, Inc | Sierra Wireless |
| Sierra Wireless, Inc. | Sierra Wireless |

## §11 discipline

- §11 #1 (no fabrication) — plan-input data preserved; filing_id extracted from filing_url where parseable, else None.
- §11 #7 (provenance) — each entry chains to dispatch + source_wave; URLs are first-party fccid.io links.
- §11 #8 (no confidence drift) — no identifier promoted; no confidence assigned. URL inventory is informational scaffolding for v1.5.0.
- §11 #14 — applies at v1.5.0 deep-mine time, not now.
- SAR-13.5 — these are direct fccid.io scrape, no bucket-payload extraction; attribution_status not needed at this layer.
