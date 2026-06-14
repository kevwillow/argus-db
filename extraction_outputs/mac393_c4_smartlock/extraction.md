# MAC-406 — Cohort 4 EXTRACTION: Consumer smart locks

**Worker:** ExtractionWorker · **Phase:** extraction (STAGE ONLY — no DB write, no ingest, no migration, no export regen, no push) · **Parent:** [MAC-393](/MAC/issues/MAC-393) · **Harvest:** [MAC-397](/MAC/issues/MAC-397) (CTO-ratified) · **Generated:** 2026-06-14
**Module:** `db/sources/cohort4_smartlock.py` · **Tests:** `tests/test_cohort4_smartlock.py` (17 pass) · **Output:** `extraction_outputs/mac393_c4_smartlock/candidates.json`
**device_category:** ⚠ proposed **`smart_lock`** — does NOT exist (verified `count=0`). Every candidate tagged `category_pending_board_ratification`. Mint-vs-map is a **board one-way-door at the ingest gate** — this phase does not assume it and does not write the category.

> Re-derived **every** field from on-disk raw bytes (re-grepped IEEE oui.csv + re-scanned the 4 pinned APK dex pools), never trusted from the harvest summary. APK sha256 self-verified at build (fail-loud on drift). `db/argus.db` opened `mode=ro`.

---

## 1. Headline — authoritative counts (the harvest "~79" is now resolved)

| identifier_type | promote | flagged-ambiguous | excluded | net-new vs held |
|---|---|---|---|---|
| `oui` (IEEE primary_registry) | **2** (Kwikset, Yale) | 4 (ASSA-conglomerate) | — | all 6 NET-NEW |
| `ble_service_uuid` (128-bit, APK GATT) | **54** | 11 | 31 | all NET-NEW |
| `ble_company_id` / 16-bit `ble_service_uuid` | 0 | 0 | — | **0 net-new** (registry fully bulk-loaded → recat only) |
| **TOTAL clean-promote** | **56** | 15 | 31 | — |

### Authoritative dedup'd 128-bit GATT count (replaces harvest "~79")
Scanning all 4 companion APKs' `classes*.dex` string pools (pure-stdlib `zipfile`+regex, deterministic):

```
96  distinct custom-128 UUIDs across the 4 APKs
–17  cross-vendor magnets   (≥2 unrelated vendor APKs — shared chipset/BLE-SDK; §11 #21 cited co-occurrence)
=79  vendor-unique          (← matches the harvest "~79"; this is the real figure, not approximate)
–14  vendor-unique but SDK/placeholder/non-BLE (excluded on a cited structural ground)
=65  genuine vendor-distinct GATT  (← the CTO "≈65" estimate, now exact)
–11  flagged-ambiguous      (boilerplate-node / ASCII-embedded — conf 40, NOT clean-promoted; §11 #1)
=54  clean-promote 128-bit GATT candidates
```

Per-vendor genuine vendor-distinct GATT (promote / flagged / vendor-unique-excluded → vendor-unique total):

| vendor (app) | promote | flagged | vu-excluded | vendor-unique |
|---|---|---|---|---|
| Kwikset `com.kwikset.blewifi` (pure-play lock) | **23** | 0 | 0 | 23 |
| Schlage `com.allegion.leopard` (pure-play lock) | **1** | 0 | 4 | 5 |
| August/Yale `com.august.luna` | **17** | 9 | 0 | 26 |
| Ultraloq `com.utec.utec` (U-tec multi-product app) | **13** | 2 | 10 | 25 |
| **total** | **54** | **11** | **14** | **79** |

---

## 2. §11 #1 byte-faithfulness — the surface CTO did NOT certify at harvest

Every promoted/flagged 128-bit GATT UUID is proven against the **exact `classesN.dex` constant bytes** it cites. `candidates.json[*].raw_payload` records `{dex_entry, byte_form, apk_sha256, package}`; `source_excerpt` IS the verbatim dex constant byte-form. The test `test_gatt_byte_faithful_to_dex` re-extracts every dex blob and asserts `byte_form.encode() in blob` and `byte_form.lower() == identifier` for all 65 genuine vendor-distinct UUIDs. Examples (byte-paste, case as stored):

- **Kwikset** `classes.dex` — `4D050010-766C-42C4-8944-42BC98FC2D09` … `4D0500A2-766C-42C4-8944-42BC98FC2D09` (22 service/char sharing base `766c-42c4-8944-42bc98fc2d09`) + `D4305C76-7A89-4990-9395-9E054E1B4CD3`.
- **Schlage** `com.allegion.leopard.apk!classes2.dex` — `ce85ad03-0f20-4aed-abe5-b7407dd7cacc` (the single clean vendor-distinct value; APK is Schlage's ONLY net-new surface).
- **August** `classes3.dex` — `E295C550-69D0-11E4-B116-123B93F75CBA`…`E295C554` (5); `52e4c6be-0f96-425c-89{0,1,2}0-ddcef680f636` (3).
- **Ultraloq** `com.utec.utec.apk!classes6.dex` — `01FF5550/51/52-BA5E-F4EE-5CA1-EB1E5E4B1CE0` (3).

---

## 3. Lock-GATT vs bundled-SDK separation

### 3.1 Cross-vendor magnets EXCLUDED (17, by cited co-occurrence — §11 #21 / CP44)
Confirmed the harvest's **16 SDK magnets** exactly, + the all-zero placeholder:
- `258eafa5-…` — **all 4** apps (universal BLE-library magnet).
- Nordic UART `6e400001/2/3-…-dcca9e` (3); Nordic DFU `1d14d6ee`, `da2e7828`, `8d53dc1d`, `984227f3`, `515d6767` (5); `f7bf3564` (1) — Kwikset + (Ultraloq | Schlage).
- TI OAD `f000ffc0..c5-0451-4000-b000-0` (6) — Kwikset + Ultraloq.
- `00000000-…` all-zero placeholder — all 4.

### 3.2 Vendor-unique but EXCLUDED on a cited structural ground (14)
- **Known-fake (§7.3 → `conflicts`, `reason='known_fake_pattern'`):** `ffffffff-…` (all-F), `00010203-0405-0607-0809-0a0b0c0d{1910,1912,2b10,2b11,2b12}` (Ultraloq, monotonic +1 sequential placeholder — 5).
- **Apple HomeKit ecosystem (cross-vendor, not the lock's own GATT):** `00000014-…-0026bb765291` (HomeKit base), `486f6d65-6b69-7400-…` (ASCII "Homekit") — Schlage.
- **Non-BLE Docker v1 UUIDs** (node `02:42:ac:12:00:02` = Docker default bridge): `d861b25a-…` (Schlage), `84ce5c4e`/`84ce7201-…` (Ultraloq) — 3.
- **Bundled-SDK Nordic UART variant:** `6e400001/2/3-…-dcca1e` (Ultraloq — Nordic NUS base with a customized final segment `dcca1e` vs the standard `dcca9e`) — 3.

### 3.3 Flagged-ambiguous — conf 40, NOT clean-promoted (11; §11 #1 conservative)
Vendor-unique, but the value itself carries a copy/sample signature → emitted as candidates at confidence 40 with `notes.ambiguous_extraction=true`, surfaced for CTO/Validator adjudication:
- **August `bd4ac610..616-0b45-11e3-8ffd-0800200c9a66`** (7) — v1 UUID family, node `08:00:20:0c:9a:66` = **Sun Microsystems OUI**, the `java.util.UUID` javadoc / Android-BLE-tutorial sample node → likely boilerplate, not a vendor-generated service.
- **August `bb392ec0-…` / `c06c8400-…-0002a5d5c51b`** (2) — v1 UUIDs sharing a globally-administered (real) OUI node → possible copied/sample service.
- **Ultraloq `73631912` / `73632b12-6965-6e65-7269-736669727374`** (2) — UUID whose suffix decodes to ASCII text → sentinel/sample-like, not a confirmed GATT UUID.

### 3.4 Clean-promote (54) — vendor-distinct lock GATT
Everything vendor-unique that passes the magnet + known-fake + SDK-signature + boilerplate filters. `manufacturer_app` band, single-source, **confidence 80** (Kwikset/Schlage/August) / **78** (Ultraloq — the `com.utec.utec` "Xthings Home" app may span multiple U-tec product lines; UUID is vendor-distinct but product-within-vendor is not certain). `service_vs_characteristic` left **undetermined** — the GATT role is not asserted from dex strings (§11 #1; the Validator/board can resolve service vs characteristic).

---

## 4. OUI candidates (6 NET-NEW, IEEE primary_registry)

Cite-pasted verbatim from `oui.csv` (sha `fad18e77…`). SAR-1 LAA-bit test applied to each first octet → all globally-administered (clear), no penalty. §7.3 known-fake check → all pass.

**Promote (clean consumer-lock attribution):**
- `10:a4:50` **Kwikset** — conf 85 — `MA-L,10A450,Kwikset,110 Sargent Dr. New Haven CT US 06511` (pure-play residential lock brand).
- `b0:44:9c` **Yale** — conf 82 — `MA-L,B0449C,Assa Abloy AB - Yale,…Malmö SE` (cohort vendor "Yale Assure"; Yale also makes commercial hardware).

**Flagged-ambiguous (conglomerate / not product-anchored — conf ≤45, `ambiguous_extraction`):**
- `98:1b:b5` ASSA ABLOY Korea iRevo (45) · `14:a1:bf` ASSA ABLOY Korea Unilock (45) — ASSA Korea residential-lock subsidiaries, not cohort vendors, not product-anchored in the cleared slate.
- `00:17:7a` ASSA ABLOY AB (40, parent conglomerate, commercial+consumer) · `dc:c0:eb` ASSA ABLOY CÔTE PICARDE (40, FR door-hardware division).

---

## 5. Held recat-candidates (NOT promoted — gated on the taxonomy mint)

BLE registry is fully bulk-loaded → **net-new = 0**; these contribute *recategorization* only and are recorded, not staged for insert:
- OUIs: **U-tec Group** `0c:7f:ed:8/28` id7200 (Ultraloq maker, strong recat) · **Spectrum Brands** `70:b3:d5:25:4/36` id21039 (Kwikset parent, multi-division caveat) · **ASSA ABLOY(GuangZhou)** `e8:6c:c7:1/28` id9448 · **Allegion PLC** `fa:14:66` id37014.
- **Wyze do-not-double-promote** (MAC-397 ruling 2): `a4:da:22:2/28` id9748 + id44484-88 already `cctv_camera`. **No Wyze candidate emitted** — company-level OUI cannot be split Lock vs Cam without a product-level cite. `com.hualai` SKIPPED (ruling 3).
- BLE company-IDs (held `ble_manufacturer_id`, unknown): August `0x01D1` id4507 · Yale `0x0BDE` id2106 · Allegion `0x013B` id4648 · Wyze `0x0870` id2926 · Spectrum `0x0356` id4155 · ASSA `0x012E` id4661.
- **Typing quirk** (MAC-397 ruling 4): the 4 16-bit service UUIDs `0xFE24`/`0xFCF4`/`0xFD7B`/`0xFCBF` are stored under `identifier_type='ble_company_id'` (pre-existing bulk-load artifact, DB-confirmed). **Noted, NOT "fixed" here.**

---

## 6. Deltas vs harvest

1. **Kwikset count resolved** — harvest cited "22 (table) vs 23 (sources.json)". Authoritative = **23** (22 `4d0500XX` family + `d4305c76`). The "22" omitted `d4305c76`.
2. **Authoritative GATT figures** — harvest "~79" was vendor-unique (now exact: 79); "75 per-APK sum" used Schlage=1 (clean) instead of Schlage's 5 vendor-unique; CTO "≈65" genuine is now exact: **65** (54 clean + 11 flagged). No surface lost, just made precise.
3. **All 16 SDK magnets confirmed** by independent co-occurrence; +1 all-zero placeholder also cross-vendor → 17 total in the magnet bucket.
4. **No new FP/exclusion** beyond harvest. The `258eafa5` "all-4" claim is byte-confirmed (present in all 4). No new restrictive/ToS-forbidden source encountered.

---

## 7. Hard-gate compliance

- ✅ **§11 #1 cite-paste / nothing from memory** — every OUI is a verbatim oui.csv substring; every GATT UUID byte-matches its `classesN.dex` constant (re-extracted in the test). Ambiguous/boilerplate families flagged conf 40, not over-extracted.
- ✅ **§11 #3 / SAR-5 PII** — `pii_redaction_count=0`; org legal-entity names + IEEE registry addresses only; person-name regex applied (mechanism unit-tested with a synthetic positive). No APK code copied (§11 #15 facts-only; values + dex location + sha only).
- ✅ **§11 #7 source_excerpt ≤200** — app-enforced via `clip()` (truncate + `…` marker); positive+negative tests; every emitted candidate verified ≤200.
- ✅ **§11 #8 no confidence drift** — single-source staging (manufacturer_app 78–80; primary_registry 40–85).
- ✅ **§11 #13 export-ban** — smart_lock is export-banned until minted; ingest+regen gated on the board taxonomy decision.
- ✅ **§11 #21 cross-vendor exclusion** — by cited co-occurrence (≥2 vendor APKs), not from memory.
- ✅ **STAGE ONLY** — no `db/argus.db` write, no ingest, no migration, no export regen, no push. `source_row_key = sha256(doc_url|type|identifier)` recorded per candidate for downstream idempotency.

---

## 8. Handback

Extraction complete. Net-new surface: **6 OUIs** (2 clean-promote Kwikset/Yale + 4 flagged ASSA-conglomerate) + **54 clean-promote 128-bit GATT** (+11 flagged-ambiguous) from the 4 companion APKs; BLE-registry net-new = 0 (recat only). Authoritative dedup'd 128-bit GATT count delivered (96 distinct → 79 vendor-unique → 65 genuine → 54 clean-promote). Byte-faithfulness of all 65 genuine GATT UUIDs proven against the dex constants — the surface CTO deferred at harvest.

**Reassigning to CTO** for verify → DBArchitect ingest, with decisions surfaced: (1) the `smart_lock` taxonomy mint (board one-way-door @ ingest); (2) disposition of the 11 flagged-ambiguous GATT + 4 flagged ASSA-conglomerate OUIs; (3) the held recat slate (unknown→smart_lock) gated on the mint; (4) the 16-bit-UUID-stored-as-`ble_company_id` typing quirk (Validator/DBArchitect). Did **not** write `db/argus.db`.
