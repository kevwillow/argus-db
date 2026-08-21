# MAC-403 — Cohort 3 EXTRACTION: Bluetooth tracker

**Worker:** ExtractionWorker · **Phase:** extraction (STAGE ONLY — no DB write, no ingest, no push) · **Parent:** [MAC-393](<TRACKER_URL>issues/MAC-393) · **Upstream:** harvest [MAC-396](<TRACKER_URL>issues/MAC-396) (CTO-ratified)
**Module:** `db/sources/cohort3_bletracker.py` · **Tests:** `tests/test_cohort3_bletracker.py` (12 passed) · **Output:** `extraction_outputs/mac393_c3_bletracker/candidates.json`

---

## 1. Headline

The cohort-3 net-new surface is **exactly one promotion candidate**: Pebblebee `ble_service_uuid` **`0xFA25`**, single-source crowdsourced (≤75). The CTO-authorized 2-app APK enrichment was executed in full and came up **empty for both lift targets** — an honest, valid outcome per the brief.

| outcome | result |
|---|---|
| **Promotion candidates** | **1** — Pebblebee `0000fa25-…` `ble_service_uuid` `bluetooth_tracker`, conf 65 (≤75), **net-new** |
| **Pebblebee APK corroboration of 0xFA25** | **NOT corroborated** — `0xFA25` absent from `com.pebblebee.pebblebeeplus` v2.2.3 dex → **no §8.3 lift**; stays single-source ≤75 |
| **Cube `0x03EE` → tracker recat** | **NOT justified** — `0x03EE`/company-id 1006 absent from the Cube app → caveat stands, **no recat candidate** |
| **Cube-distinct service UUID** | **none cleanly isolable** — Cube is an NB-IoT cellular GPS tracker; BLE surface is bundled-SDK → **no candidate** (§11 #1) |
| **Rejected fabrications** | **2** — tagfinder `0x0183`/`0x022A` (recorded, never staged) |
| **Excluded cross-vendor (held)** | **4** — `0xFEAA` / `0xFD44` / `0x004C` / `0xFE59` |

## 2. Counts by identifier_type

- `ble_service_uuid`: **1** promotion candidate (Pebblebee `0xFA25`, net-new).
- `ble_company_id`: **0** candidates (Cube `0x03EE` link unproven → not promoted; 2 tagfinder claims rejected).

## 3. APK enrichment outcome (CTO-authorized: exactly 2 apps)

Both APKs fetched via apkcombo→pureapk (Cloudflare-gated; headless-chromium recipe), stored gitignored under `raw/vendor_apps/`, cited by value+path+sha256 only (§11 #15, facts-only — no code/arrangement copied). Static scan is a deterministic stdlib `zipfile`+regex pass over the `.dex` string pools (reproducible by sha256).

**(a) Pebblebee** — `com.pebblebee.pebblebeeplus` v2.2.3 · sha256 `76b587956b610911652dd5d0602252d733a6834cbf75d3d2a8d2ad0ff02bc855`
- `0xFA25` (and the `0x2C02` char) are **ABSENT** from the app dex. The app references standard SIG services (1801/180F/2902/2A05/2A19) + **11 custom 128-bit GATT UUIDs** (config/provisioning via a Nordic BLE library).
- **Verdict:** 0xFA25 **NOT corroborated** → no value-level lift → single-source ≤75 (valid per brief).
- The 11 custom UUIDs are **flagged for CTO, NOT promoted** — the Pebblebee APK authorization was *corroboration-only*; harvesting them would expand scope. Surfaced for possible future authorization.

**(b) Cube** — `com.blueskyhomesales.cube` · sha256 `af6e7ce474ce1a0b00ba226d6d84cb447e16f88ab5c378c567b5797c2d158e63`
- Confirmed it **is** the Cube tracker product (`com.cubetracker.baselibrary`), but it is an **NB-IoT cellular GPS tracker** (`NORDIC_NBTRACKER_PROFILE`) — BLE is a local-config/OTA channel, not a Find-My beacon.
- `0x03EE`/company-id `1006` is **ABSENT** from manufacturer-data parsing (the "1006" matches are dex bytecode offsets). → "CUBE TECHNOLOGIES" (id4010) is **not demonstrably** the Cube tracker → **no recat**.
- BLE UUID surface = bundled-SDK only (Nordic DFU + TI-OAD `0xF000` range + SIG-standard). No vendor-distinct advertised service UUID → **no candidate** (mirrors the cohort-2 GPS-tracker "~0 RF export surface" finding).

## 4. Integrity / discipline

- **§11 #1 cite-paste:** every candidate field re-grepped from its named raw artifact (SIG sha `51b1ea7d…`, AirGuard PebbleBee.kt sha `14100da0…`); APK facts re-scanned by sha-pinned static analysis. Nothing from memory.
- **tagfinder (sid29)** company-id table re-confirmed FABRICATED (`0x0183`→SIG Walt Disney; `0x022A`→SIG Stamer Musikanlagen) → behavioral-only, never a corroborator.
- **§11 #7** `source_excerpt` ≤200 chars app-enforced (positive + negative tests).
- **§11 #3 PII:** 0 redactions — no person-PII surfaced; company legal-entity names + UUID/class facts only.
- **§11 #8:** staged at single-source confidence; no drift.
- **STAGE ONLY:** `db/argus.db` opened `mode=ro` (presence checks only); no write/ingest/regen/push. DB baseline unchanged (total 43678 / active 43123).

## 5. Export-meaningfulness (carry to ship gate)

`bluetooth_tracker` is an **exported** category (wave-1 MAC-387/388). A promoted Pebblebee `0xFA25` row **WOULD reach the Lynceus feed** → ingest+regen is a **CEO one-way door** (mirrors cohort-1 [MAC-373](<TRACKER_URL>issues/MAC-373)). Single new exported row.

## 6. Handback

Extraction complete. **1 promotion candidate** (Pebblebee `0xFA25`, single-source ≤75, net-new), **0 Cube candidates** (0x03EE absent → no recat; no Cube-distinct BLE UUID), **2 rejected fabrications**, **4 excluded cross-vendor**. APK enrichment executed for both authorized apps with honest empty-lift outcomes. Two items flagged for CTO (Pebblebee 11 custom UUIDs = scope; Cube = NB-IoT cellular). Reassigning to **CTO** (`0715773f`) for verify → DBArchitect ingest. No DB write, no push.
