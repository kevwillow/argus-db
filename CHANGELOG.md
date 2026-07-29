# Changelog

All notable changes to Argus are documented in this file. The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project does not yet adopt semantic-versioning for the dataset shape itself, see "Schema versioning" below for the migration-ledger discipline.

## TL;DR

**Argus tracks surveillance vendor identifiers**, MAC ranges, FCC grantee codes, hostnames, certificate SANs, BLE company IDs, IMEI Type Allocation Codes, and dozens of other identifier classes, used by US law enforcement and adjacent surveillance deployments.

**Each version (v1.X.Y) bundles** a cycle of source admissions, manufacturer admissions, schema migrations, and bible-amendment ratifications. Headline metrics per version: schema_version, source count, manufacturer count, active identifier count, Lynceus high-confidence export count.

**To read entries below:** find your version of interest; the `### Schema` section lists migration deltas; the `### Data` section lists count deltas; the `### Bible amendments` section lists the formal discipline codifications (Correction Passes + SAR rules); the `### Halts encountered` section lists any halt-class issues that surfaced during the cycle and their ratifications.

**For the user-facing overview** of what Argus is and how to use the exports, start with [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md).

---

## v1.7.0 - 2026-07-28

Six lanes of finished work, shipped together. The board asked for one substantial release instead of a run of small ones, so everything that queued behind separate gates since v1.6.14 lands here: a false-positive fix to the SSID patterns, eight new identifiers, a junk-row cleanup, three new sources, and a large vendor-attribution import.

**About the version gap.** A v1.6.15 was assembled and staged in late July, then pulled before publication when the board decided against shipping the false-positive fix on its own. No `v1.6.15` tag exists and nothing was released under that name. Its content ships here, so the public history runs v1.6.14 to v1.7.0.

### If you consume the feeds, read this part

**The SSID patterns stop matching your neighbours.** A WiGLE re-mine ([MAC-522](/MAC/issues/MAC-522)) tested the 32 SSID substrings v1.6.14 shipped against real-world network data and found 14 of them hitting ordinary home and business WiFi. `flock` matched "Schneeflocke". `Penguin` matched 112,000 networks. `dji` matched "Fidji". `oxygen` matched "Oxygen.Net". Lynceus 0.9.2 compares these as bare substrings, ignoring case and word boundaries, so a scanner running v1.6.14 could label a neighbour's router a license plate reader. Migration `0038` withdraws 9 of those rows and rewrites 8 into delimiter-anchored forms, `mavic_` and `mavic-` in place of bare `mavic`. Measured against the shipped v1.6.14 feed, that removes 7 substrings (`flock`, `Penguin`, `dji`, `magnet`, `oxygen`, `vigilant`, `alpr`) and replaces 9 more with 18 anchored pairs.

Every vendor touched by that pass keeps a working identifier. In the standard feed Flock retains 38 OUIs, the `ssid_exact` entries `Flock` and `Flock-230503`, 6 BLE local names, 8 BLE UUIDs, 4 MACs and the `FS Ext Battery` pattern. DJI retains 15 OUIs, 51 drone-ID prefixes and the anchored `mavic` / `phantom` stems. Magnet, Oxygen and MSAB stay in the database through their product identifiers. `iCSee` and `V380` are the only identifiers their vendors have, so we tightened those rather than dropping them.

The cost: an anchored stem misses a device whose SSID carries no delimiter. We accept that until Lynceus gets minimum-length and word-boundary matching ([MAC-517](/MAC/issues/MAC-517), [MAC-356](/MAC/issues/MAC-356)), at which point the original stems, preserved verbatim inside migration `0038`, can be relaxed back.

**A dead pattern is gone.** The `ssid_exact` entry `Flock-*` never matched anything: the `*` is a literal character, not a wildcard, so Lynceus was looking for a network named `Flock-*`. Migration `0039` withdraws it (id 22910). The staged v1.6.15 notes cited `ssid_exact Flock-*` as live Flock coverage; the working SSID identifiers are `Flock` and `Flock-230503`, and the 38-OUI count in that line was and remains correct.

**Eight new identifiers**, ids 44659-44666 ([MAC-518](/MAC/issues/MAC-518), [MAC-519](/MAC/issues/MAC-519)). The DriveCam OUI `00:16:b2` and two Tianjin Hualai camera OUIs, `18:50:73` and `e4:aa:ec`, plus five FCC grantee codes covering Chipolo, Pebblebee, PB Inc, Netradyne and Nauto. The three OUIs reach the feeds; grantee codes do not, by design.

**Feed totals.** Standard 977 to **981**, high-confidence **481** on both sides, behavioral **132** unchanged. The high-confidence total holding still conceals real movement: three Flock entries left (`Flock-*`, `flock`, `Penguin`) and the three new OUIs arrived.

### Everything else

**Sixteen junk rows withdrawn** (migration `0040`, [MAC-531](/MAC/issues/MAC-531)). Thirteen hostnames that were never vendor infrastructure (`java.sun.com`, `jabber.org`, `www.bouncycastle.org`, `android.asset`, and scrape fragments such as `ap.meraki.com.wshttp`), two bad endpoints (`localhost:54664`, `peticaonline.comv`), and a `ble_company_id` written `0x4C` where the surviving row already carries the four-digit `0x004C`. One further row was corrected in place, FCC grantee code `2a2v6` to `2A2V6`. None of the 16 appeared in any shipped feed, confirmed by comparing the feeds entry by entry rather than reasoning about it.

**Three new sources**, 95 to 98. MuckRock's cell-site-simulator FOIA census and the ACLU's stingray disclosure compilation ([MAC-524](/MAC/issues/MAC-524), [MAC-526](/MAC/issues/MAC-526)) brought **7 procurement records** naming Harris and Digital Receiver Technology hardware at seven agencies, among them Rochester PD, Virginia State Police and Oakland PD. IPVM's public camera and VMS directory ([MAC-533](/MAC/issues/MAC-533)) is the third.

**Vendor attribution, 156 manufacturers to 240** (migration `0041`). The 84 additions are OEM arms of Hikvision (52) and Dahua (32), the rebadging brands those two sell through. Six aliases were attached to Hikvision (EZVIZ, HiLook, Hikmicro, HiWatch, Annke, LaView), and Amcrest and Lorex were linked to Dahua as their parent. The arms are marked hidden by default, so they change how a camera traces back to its real maker without padding vendor lists. No identifiers changed: this is attribution, not new coverage. Forty-four former Dahua OEM brands and 242 unverified vendor leads were held back rather than ingested.

### Schema

- **No schema change.** `schema_version` stays **33** (last schema-changing migration `0033`, CP46). All four migrations this cycle, `0038` / `0039` / `0040` / `0041`, are data-only: no DDL, no new `identifier_type` or `device_category` values (the category enum stays at **20**).

### Data

- **`identifiers` active:** 43,134 → **43,116** (net −18: +8 admitted, −9 false-positive stems, −1 dead `Flock-*`, −16 junk rows). Nothing is deleted; withdrawn rows stay as superseded history under the CP32 §9 self-loop.
- **`identifiers` total:** 43,840 → **43,848** (+8, the Wave-6 admissions).
- **`manufacturers`:** 156 → **240** (+84 OEM arms). **`sources`:** 95 → **98**. **behavioral signatures:** **214** (no change). **device-category enum:** **20** (no change). **`procurement_records` is deliberately not quoted as a coverage figure** — see "Known limitation" below.
- **Lynceus standard feed:** 977 → **981** (+21 entries / −17 entries). **high-confidence feed:** **481** → **481** (+3 / −3). **behavioral-signatures feed:** **132** (entry set byte-identical). **CSV:** **43,116** rows, matching the active count.
- **Fingerprint.** The standard and high-confidence feeds carry `argus_run_id` `06182438-91da-5a0d-91fa-6515dc86d921`; the behavioral feed carries `260b5777-99c8-5f75-8023-f4012242e7f4`. Canonical `db/argus.db` sha256 `b05c097b666ed0ae9c4034d5b77c0d532a397365a32cc20438b3d706c67cbbc0`. One consolidated regeneration ran against canonical after both database-write phases landed, and re-running it in an isolated directory reproduced all three consumer artifacts byte for byte.

### Known limitation

`procurement_records` holds 50,499 rows, and that number is not a surveillance-coverage figure. The
table was populated by delegating vendor matching to USAspending's server-side `keywords` filter,
which is bare containment over recipient name and award description with no word or entity boundary.
Re-matching every row on entity boundaries ([MAC-542](/MAC/issues/MAC-542)) finds **9,065 rows, 17.95%,
that match no vendor in the registry at any boundary** — `NATIONAL OIL DJIBOUTI SAS` on "DJI",
`FAXON ENGINEERING` on "AXON", `HAMILTON PACIFIC CHAMBERLAIN` on "BERLA", and 2,034 rows of Defense
Logistics Agency alprazolam repackaging caught on "ALPR". The boundary-valid total is 41,434. A
further tranche is held up only by a short single-token vendor name and is still under adjudication,
but its **disposition is not final and no coverage figure is quoted from it here**. The first pass
enumerated 8,658 rows while omitting four keyword families (`Axis`, `DRT`, `Magnet`, `Flock`) whose
bare tokens survive only in ingest provenance, never as registry vendor names;
[MAC-574](/MAC/issues/MAC-574) root-caused that omission, landed the tier selector as reviewable code
with a regression guard, and re-derived the partition at **8,960 rows across 456 clusters**. The
9,065 and 41,434 figures above are unaffected — every omitted row is boundary-clean and none falls
inside the 9,065 — and the correction is purely additive, so no already-adjudicated cluster moved.
The surviving count will be lower still once adjudication lands, so no coverage claim is made from
this table until MAC-542 lands.

**No shipped identifier is affected.** `procurement_records` is read by nothing under `db/export/`;
procurement-sourced rows are Talos-export-banned outright under bible §11 #14, with a standing
`new_procurement_only_export_leak` sentinel enforcing it; and only 7 of the 50,499 rows carry a
`linked_identifier_id` at all — **none of them among the 9,065**. No Lynceus feed entry, no CSV row and
no `identifiers.confidence` value moves.

It has exactly one consumer: the `exports/coverage_report.md` §6.2 vendor-corroboration table, whose
`procurement_records` counts gate the HIGH tier at a floor of 10. So §6.2 carries **two** independent
defects this cycle — the alias-tokenizer bug below, and the containment contamination above. Both are
reporting-only, and both are corrected at the next regeneration.

`exports/coverage_report.md` §6.2, the vendor-corroboration table, was generated before a tokenizer fix that landed in the same stack ([MAC-535](/MAC/issues/MAC-535)). Splitting vendor aliases on commas produced junk tokens out of corporate suffixes (`Ltd.`, `Inc.`, `LLC`), which inflated corroboration counts for 17 vendors; Hikvision reads 8,662 there where 2 is genuine. Re-running the fixed matcher at this commit changes 20 of 18,713 rows and moves the HIGH tier from 52 vendors to 37. Nothing else moves: the active count, the halt count and both feed drop tallies come out identical, and no `identifiers.confidence` value depends on this table. Those §6.2 tiers are reporting-only, and they are the same numbers every prior release shipped. They get corrected at the next regeneration.

### Bible amendments

- **CP52 (provisional), `ssid_pattern` false-positive refine and demote ([MAC-527](/MAC/issues/MAC-527)).** Drops categorically wrong stems (`oxygen` and `magnet` are forensic software with no field access point, `alpr` is an internal category acronym), refines device families to delimiter-anchored forms, and binds a marquee-coverage guard: no vendor loses its last working identifier. Carried in `docs/engineering/BIBLE_AMENDMENTS.md`. The board finalizes the CP number against the in-flight CP48-CP51 renumber.
- **§11 #21 reserved ([MAC-535](/MAC/issues/MAC-535)).** Any `UPDATE` in a migration that lacks a `UNIQUE` or `CHECK` backstop must be written so a second apply is harmless. Migration `0041` appends aliases without such a guard; canonical is clean and the file now carries a warning header.

### Halts encountered

- None. `coverage_matrix` `_reconcile` halts: **0**. The CSV reconciles to canonical active, 43,116 = 43,116. The export path took no database write, proved by identical sha256 before and after the regeneration.

---

## v1.6.15 (withdrawn before release)

Assembled 2026-07-27 as an isolated false-positive fix, then pulled at the board's direction in favour of one bundled release. No tag was cut and nothing was published under this version. Its content, the CP52 `ssid_pattern` remediation and migration `0038`, ships in v1.7.0 above.

---

## v1.6.14 - 2026-07-21

An **export-layer capability-flip release** on top of v1.6.13, isolated out of the in-flight Wave-6 gate ([MAC-517](/MAC/issues/MAC-517)) so the CP51 `ssid_pattern` change ships alone rather than riding a data cycle. It is **export-only: zero admissions, zero withdrawals, zero canonical database writes.** The database is byte-identical to v1.6.13 (DB post-sha `b406dff1...daa265`, unchanged because nothing was written), and the active-set fingerprint is unchanged — the standard feed's `argus_run_id` is `10b46f03-3d3a-5646-9279-48cbb8d469aa`, which matches the shipped v1.6.13 active set. What changes is the Lynceus export layer: **CP51 (provisional) re-pins the `ssid_pattern` disposition from the stale "Lynceus v0.2, no regex → DROP" assumption to Lynceus 0.9.2, which matches `ssid_pattern` as a case-insensitive substring** (`? LIKE '%' || needle || '%' COLLATE NOCASE`, Lynceus consumer `db.py:1126`), not a regex, after the board pinned the live matcher at 0.9.2 on [MAC-516](/MAC/issues/MAC-516). Previously section-4.4 export-dropped `ssid_pattern` rows now ship as leading-literal substring stems. The standard Lynceus feed moves **945 → 977** (**+32**, 100% `ssid_pattern`, nothing removed) and the high-confidence feed **478 → 481** (**+3**, 100% `ssid_pattern`); the behavioral-signatures feed is unchanged at **132**. There is **no schema migration** (schema_version stays **33**, last schema-changing migration `0033`, CP46) and no data change: active identifiers stay **43,134**, total identifiers stay **43,840**, manufacturers **156**, sources **95**, and the device-category enum **20** — all unchanged from v1.6.13. The CTO re-verified the two feed deltas and the `argus_run_id` directly against the committed export JSONs (isolated regen `db4933f` vs v1.6.13 baseline `02212cf`) and confirmed the four short-stem false-positive holds are absent from the feed rather than estimating them.

**Consumer note (binding).** The new `ssid_pattern` feed rows are substring stems that require **Lynceus 0.9.2 or newer** to consume. A Lynceus consumer older than 0.9.2 does not implement the `ssid_pattern` substring matcher and will not act on these +32 standard / +3 high-confidence entries. `ble_local_name` templates stay deferred — Lynceus 0.9.2 matches `ble_local_name` only by exact, case-sensitive equality, and substring/template matching is not available until Lynceus v1.4.3+, so `ble_local_name` is out of scope for this release.

### Schema

- **No migration this cycle.** schema_version stays **33** (last schema-changing migration `0033`, CP46). CP51 is an export-layer type-mapping change in `export_lynceus.py` / `coverage_matrix.py`; it touches no DDL, adds no `identifier_type` or `device_category` enum value (the enum stays at **20**), and writes nothing to the database.

### Data

- **`identifiers` active:** **43,134** (no change — zero admissions, zero withdrawals; this is an export-only release).
- **`identifiers` total:** **43,840** (no change).
- **`manufacturers`:** **156** (no change). **`sources`:** **95** (no change). **device-category enum:** **20** (no change).
- **Lynceus standard feed:** 945 → **977** (**+32**, 100% `ssid_pattern`, zero removed). **high-confidence feed:** 478 → **481** (**+3**, 100% `ssid_pattern`). **behavioral-signatures feed:** **132** (no change). **CSV:** 43,134 rows (unchanged; byte-identical to the v1.6.13 CSV modulo the per-run `exported_at` timestamp).
- **What the +32 / +3 are:** previously section-4.4 export-dropped `ssid_pattern` rows that Lynceus 0.9.2 can now match as case-insensitive substrings. Each surviving row emits one feed record per converted leading-literal substring; the standard-feed `argus_run_id` `10b46f03-3d3a-5646-9279-48cbb8d469aa` matches the shipped v1.6.13 active-set fingerprint, confirming the active set was not touched.
- **False-positive holds:** short or generic stems are FP-held (drop-bin `ssid_pattern_fp_hold`) so they never reach the feed. `lpr`, `ibr`, `rv50`, and `mp70` were confirmed absent from the standard feed.
- **DB post-sha:** `b406dff1209f1068945a668aeb23aacfead47cc9e516b315eddf8dedefdaa265` (unchanged from v1.6.13; the database is byte-identical because this release performs no canonical write).

### Bible amendments

- **CP51 (provisional) — `ssid_pattern` §4.4 MAP → Lynceus 0.9.2 case-insensitive substring; §179 POSIX-regex claim corrected ([MAC-517](/MAC/issues/MAC-517)).** The `export_lynceus.py` §4.4 type-mapping table and PROJECT_BIBLE §179 are re-pinned from the stale "Lynceus v0.2, no SSID regex" assumption to Lynceus 0.9.2 substring matching, after the board pinned the live Lynceus matcher at 0.9.2 on [MAC-516](/MAC/issues/MAC-516). Two prior statements are corrected as factually wrong: §179's "pattern fields use POSIX regex" and the §4.4 table's `ssid_pattern` "(DROPPED) … no regex support in v0.2" row. The amendment is carried in `docs/engineering/BIBLE_AMENDMENTS.md`; it is numbered **CP51 provisionally**, and the board finalizes the CP number against the in-flight CP48–CP50 renumber at the push gate.

### Halts encountered

- None.

---

## v1.6.13 - 2026-07-19

A **data-quality cleanup release** on top of v1.6.12, requested by the board ([MAC-511](/MAC/issues/MAC-511)) and staged as canonical write `937fefe` (DB post-sha `b406dff1...daa265`). It **withdraws 43 junk identifier rows by supersession** (migration `0037`, CP32 section 9 self-loop: `superseded_by = id`, `confidence = 0`, MAC-477 precedent, nothing deleted). The rows were APK string-pool concatenation glue, scrape-glue concatenations, RFC-2606 reserved-placeholder domains, and one Java class token mis-typed as a hostname, none of them real vendor identifiers. There is **no schema migration** this cycle: schema_version stays **33** (last schema-changing migration `0033`, CP46); `0037` is a data-only supersession pass with no DDL and no schema_version bump. Active identifier count moves **43,177 → 43,134** (-43); total identifiers stay **43,840**, since the 43 withdrawals are supersessions that retain the rows as history. All three Lynceus feeds are **unchanged** (standard **945**, high-confidence **478**, behavioral **132**): every withdrawn row was already section-4.4 export-dropped, because the `network_endpoint` and `vendor_controlled_hostname` types do not reach the Lynceus v0.2 feeds, so removing them moves the active and CSV counts but not the feed counts. The CTO re-verified the active, total, and cohort counts against the live database (DB sha `b406dff1...daa265`) and read the three feed counts below from the actual regen rather than estimating them.

### Schema

- **No migration this cycle.** schema_version stays **33** (last schema-changing migration `0033`, CP46). `0037` is a data-only supersession pass that withdraws rows without altering the schema; it does not extend the `device_category` enum, which stays at **20** values.

### Data

- **`identifiers` active:** 43,177 → **43,134** (-43 supersession withdrawals, zero admissions).
- **`identifiers` total:** **43,840** (no change; the 43 withdrawals are CP32 section 9 self-loop supersessions, which retain rows as history).
- **Withdrawn cohort (43 rows, migration `0037`):** 22 `network_endpoint` (APK string-pool concatenation glue) plus 21 `vendor_controlled_hostname`, of which 10 are scrape-glue concatenations, 10 are RFC-2606 reserved-placeholder (`example.com`) domains, and 1 is a Java class token mis-typed as a hostname.
- **`manufacturers`:** **156** (no change). **`sources`:** **95** (no change). **device-category enum:** **20** (no change).
- **Lynceus standard feed:** **945** (no change). **high-confidence feed:** **478** (no change). **behavioral-signatures feed:** **132** (no change). All three hold flat because `network_endpoint` and `vendor_controlled_hostname` are section-4.4 export-dropped types that never reach the Lynceus v0.2 feeds, so withdrawing these 43 rows moves the active and CSV counts and leaves every feed entry untouched. **CSV:** 43,134 rows, matching the active count.
- **DB post-sha:** `b406dff1209f1068945a668aeb23aacfead47cc9e516b315eddf8dedefdaa265` (canonical write `937fefe`).

### Bible amendments

- **None.** The withdrawal reuses the CP32 section 9 self-loop supersession mechanism (`superseded_by = id`, `confidence = 0`), which is existing discipline rather than a new amendment. No `BIBLE_AMENDMENTS.md` entry is recorded here.

### Halts encountered

- None.

---

## v1.6.12 - 2026-06-22

A **quality-correction + sourcing release** on top of v1.6.11, bundling two staged commits under one tag because the second sits on top of the first: the MAC-477 `ble_service_uuid` contamination cleanup (canonical write `8cfed9f`) and the Wave-4 consolidated ingest ([MAC-493](/MAC/issues/MAC-493), canonical write `7d3652d`, DB post-sha `fea9decafc54e5e9`). [MAC-477](/MAC/issues/MAC-477) **withdraws 108 string-pool `ble_service_uuid` false-positive rows** by supersession (migrations `0034`/`0035`/`0036`, from MAC-478/486/489) — GATT characteristic-UUID mis-types and string-pool artifacts that were never advertised service UUIDs and should not have reached the registry. Wave-4 ([MAC-493](/MAC/issues/MAC-493)) then **admits 11 net-new identifiers** (ids 44648-44658) across fleet telematics, ALPR, and retail people-counting, and recategorizes the ELSAG ALPR MAC range out of `unknown`. There is **no schema migration** this cycle: schema_version stays **33** (last schema-changing migration `0033`, CP46); the three MAC-477 migrations `0034`/`0035`/`0036` are data-only supersession passes (no DDL, no schema_version bump) and Wave-4 reuses existing categories. The net of the two movements is honest and intentional: active identifier count moves **43,274 → 43,177** (−97 net = 108 contamination withdrawals + 11 net-new admissions); the drop is the cleanup, not a regression — the dataset got *more* accurate. Total identifiers move **43,829 → 43,840** (+11; the 108 withdrawals are supersessions, which retain the rows as history, so total reflects only the admissions). The standard Lynceus feed moves **1,042 → 945** (−97) and the high-confidence feed **469 → 478** (+9); the behavioral-signatures feed is unchanged at **132**. Every admitted value traces to a quotable public source (IEEE OUI registry, FCC grantee registry); each lane was CTO-re-verified against the live database (DB sha `fea9decafc54e5e9`), and the feed deltas below were computed from the actual regen, not estimated.

**Honest feed-reach note (binding).** The standard feed's −97 is the sum of two separate movements, and they should be read apart. The MAC-477 withdrawal removes **107** entries from the standard feed (spanning **53** distinct `ble_service_uuid` values — contaminated UUIDs that appeared under multiple rows) and only **1** high-confidence entry: of the 108 withdrawn rows, only `d54ace3f-8e27-4718-aa17-019f0e318e14` cleared the ≥70 high-confidence floor, so the high-confidence feed fell by just 1 while the standard feed fell by 107. The Wave-4 ingest then adds back **+10** to both feeds: 10 of the 11 net-new rows reach the standard feed and all 10 are confidence ≥70, so they lift the standard and high-confidence feeds equally. The single Wave-4 row that does not reach the feed is the Neology FCC grantee code `2AKNF` (`fcc_grantee_code`), which is registry-internal — `fcc_grantee_code` is outside the Lynceus v0.2 watchlist schema. Net: standard 1,042 − 107 + 10 = **945**; high-confidence 469 − 1 + 10 = **478**; behavioral unchanged at **132**.

### What's new

- **Fleet-telematics OUIs reach the feed (+8).** Eight `automotive_telematics` OUIs (confidence 80) register as standard- and high-confidence-feed entries: CalAmp (`00:0a:99`), Zonar (`64:fc:8c`), four Lytx ranges (`2c:42:05`, `58:a7:48`, `70:e4:6e`, `50:df:95`), Verizon Connect (`7c:a2:36`), and Verizon Telematics (`94:8f:ee`). They reuse the existing `automotive_telematics` category (Samsara / Geotab precedent), so no mint is needed.
- **Neology ALPR identifiers (+2 captured, +1 feed).** The Neology OUI `00:17:3d` (`oui`, `alpr`, confidence 85) reaches both feeds; the Neology FCC grantee code `2AKNF` (`fcc_grantee_code`, `alpr`, confidence 85) is captured but registry-internal (no `fcc_grantee_code` reach in Lynceus v0.2). Neology is the parent of the curated PIPS ALPR line (manufacturer id 214).
- **RetailNext retail people-counting OUI (+1 feed).** The RetailNext OUI `20:c3:a4` (`cctv_camera`, confidence 80) registers as a feed entry.
- **ELSAG ALPR recategorized (`unknown → alpr`).** The ELSAG (Leonardo) MAC range `70:b3:d5:1c:5/36` (id 21364, `mac_range`, confidence 85) moves out of the export-suppressed `unknown` bin into `alpr`; its `notes` were JSON-merged by property (CP39-safe), not text-suffixed. The row was already in the registry, so this relabels rather than adds.
- **108 contaminated `ble_service_uuid` rows withdrawn (MAC-477).** A re-audit of the cctv-installer / Dahua / Wave-3 GATT lanes found 108 rows that were string-pool false positives or GATT characteristic-UUID mis-types, not advertised service UUIDs. They are withdrawn by supersession (migrations `0034`/`0035`/`0036`), removing 107 standard-feed and 1 high-confidence entry. The rows remain in the registry as superseded history; this is a contamination cleanup, not a data loss.

### Schema

- **No migration this cycle.** schema_version stays **33** (last schema-changing migration `0033`, CP46). The three MAC-477 migrations (`0034`/`0035`/`0036`) are data-only supersession passes that withdraw rows without altering the schema, and the Wave-4 ingest reuses existing categories — neither extends the `device_category` enum, which stays at **20** values.

### Data

- **`identifiers` active:** 43,274 → **43,177** (−97 net = 108 MAC-477 supersession withdrawals + 11 Wave-4 net-new admissions).
- **`identifiers` total:** 43,829 → **43,840** (+11; the 108 MAC-477 withdrawals are supersessions, which retain rows as history, so total reflects only the admissions).
- **Wave-4 net-new rows (ids 44648-44658):** 11 = 8 `automotive_telematics` + 2 `alpr` (1 `oui` + 1 `fcc_grantee_code`) + 1 `cctv_camera`. Plus the ELSAG id 21364 `unknown → alpr` recategorization (relabel, not net-new).
- **`manufacturers`:** **156** (no change — see attribution note). **`sources`:** **95** (no change). **device-category enum:** **20** (no change; all lanes reuse existing categories).
- **Manufacturer attribution note (load-bearing).** CalAmp, Zonar, and RetailNext are attributed via free-text `identifiers.manufacturer` rather than curated `manufacturers` rows, consistent with existing telematics vendors (Sierra Wireless, Motive, Omnitracs). Lytx (id 248), Verizon Connect (id 245), and Neology / PIPS (id 214) are already curated. The `manufacturers` count therefore stays 156; curating CalAmp / Zonar / RetailNext is logged as an optional fast-follow.
- **Lynceus standard feed:** 1,042 → **945** (−97 = −107 MAC-477 + 10 Wave-4). **high-confidence feed:** 469 → **478** (+9 = −1 MAC-477 + 10 Wave-4). **behavioral-signatures feed:** **132** (no change). **CSV:** 43,177 rows, matching the active count.

### Bible amendments

- **None landed in this commit.** The CP47 (`ble_company_id → ble_manufacturer_id` export MAP) and CP50 (`ble_local_name` literal/template split) ratifications proposed in v1.6.11 remain pending on [MAC-492](/MAC/issues/MAC-492); they carry their formal `BIBLE_AMENDMENTS.md` entries to the board push gate, consistent with the staging discipline. No new amendment is recorded here.

### Halts encountered

- None.

---

## v1.6.11 - 2026-06-20

A **multi-lane sourcing release** on top of v1.6.10: Wave 3 ([MAC-490](/MAC/issues/MAC-490), canonical write `84f0803`, DB post-sha `97765f5e`). It admits **19 net-new identifiers** (ids 44629-44647) across six harvest lanes, applies the CP47 `ble_company_id → ble_manufacturer_id` export MAP, and proposes the CP50 `ble_local_name` literal/template split. There is **no schema migration** this cycle: schema_version stays **33** (last migration `0033`, CP46). Active identifier count moves **43,255 → 43,274** (+19); total **43,810 → 43,829** (+19, all admissions active, zero supersessions). The standard Lynceus feed grows **1,014 → 1,042** (+28) and the high-confidence feed **464 → 469** (+5); the behavioral-signatures feed is unchanged at **132**. Every admitted value traces to a quotable public source (IEEE OUI registry, ASTM F3411 Remote ID, vendor APK and researcher-repo static analysis, Bluetooth-SIG assigned numbers); each lane was CTO-re-verified against the live database, and the feed deltas below were computed from the actual regen, not estimated.

**Honest feed-reach note (binding).** Two scope facts carry into this release. First, `ble_local_name` literals now reach the runtime feed under the CP50 split: 12 literal local-names are feed-visible, while 14 template local-names (wildcards and per-device suffixes that would over-match) stay held. Second, the cohort-1 spy-camera `ssid_pattern` families remain §4.4 EXPORT-DROPPED because Lynceus v0.2 has no regex matcher, so a scanner still does not alert on those SSIDs today; closing that gap is the deferred follow-up [MAC-420](/MAC/issues/MAC-420). Of the 19 net-new rows, 14 reach the standard JSON feed; the 5 that do not are `unknown`-category OUIs held out by the §11 #13 export ban.

### What's new

- **Drone Remote ID reaches the feed (lane B1, +4).** The ASTM F3411 Remote ID service-data UUID `0xFFFA` (`ble_service_uuid`) and the `org.opendroneid.remoteid` Wi-Fi Aware service name (`wifi_aware_service_name`) are vendor-agnostic Remote ID surfaces, joined by the Teal Drones (`b0:30:c8`) and uAvionix (`54:6f:71`) OUIs. A scanner now alerts on a broadcasting drone by its Remote ID service identifier regardless of airframe vendor.
- **Body-cam and gunshot-detection identifiers (lane B3, +3).** Two Utility, Inc. body-cam OUIs (`00:09:bc`, `00:16:ed`) plus the Flock Safety `00003000` GATT service UUID (`gunshot_detect`).
- **Camera and smart-lock OUIs (lanes B2 and B4, +6).** One Bosch Sicherheitssysteme camera OUI (`30:f0:28`, `cctv_camera`) and five `smart_lock` OUIs: August (`78:9c:85`), ASSA ABLOY (`00:17:7a`), iRevo (`98:1b:b5`), Unilock (`14:a1:bf`), and Côte Picarde (`dc:c0:eb`).
- **Google Find My Device anti-stalking UUID (lane B6, +1).** The Google FMDN sound service UUID `15190001-12f4-c226-88ed-2ac5579f2a85` (`ble_service_uuid`, `bluetooth_tracker`) is a first-party 128-bit identifier with low false-positive risk, admitted as a countersurveillance signal.
- **Smart-home OUIs captured, not feed-visible (lane B5, +5).** Five `unknown`-category OUIs (Nest x2, Lumi x2, SimpliSafe) land in the registry and CSV but are held out of both JSON feeds by the §11 #13 `unknown`-category export ban; they are security-system parents that do not cleanly attribute to a single surveillance category.
- **B7 `mesh_radio` mint DECLINED (board ethics ruling).** The proposed mesh-radio category (Meshtastic and activist-mesh hardware) was declined at the board ethics gate and feed-suppressed; nothing from that lane is ingested.

### Schema

- **No migration this cycle.** schema_version stays **33** (last migration `0033`, CP46). The two export-layer changes (CP47, CP50) operate in the Lynceus writer, not the canonical schema.

### Data

- **`identifiers` active:** 43,255 → **43,274** (+19 net-new admissions, zero supersessions).
- **`identifiers` total:** 43,810 → **43,829** (+19).
- **Wave-3 net-new rows (ids 44629-44647):** 19 = B1 4 + B2 1 + B3 3 + B4 5 + B5 5 + B6 1.
- **`manufacturers`:** **156** (no change). **`sources`:** **95** (no change). **device-category enum:** **20** (no change; all six lanes reuse existing categories).
- **Lynceus standard feed:** 1,014 → **1,042** (+28). 14 of the +28 are this wave's net-new feed-reaching rows; the remaining 14 are previously-captured rows surfaced into the feed by the CP47 `ble_company_id → ble_manufacturer_id` export MAP and the CP50 `ble_local_name` literal split. **high-confidence feed:** 464 → **469** (+5). **behavioral-signatures feed:** **132** (no change). **CSV:** 43,274 rows, matching the active count.

### Export-layer changes

- **CP47 (`ble_company_id → ble_manufacturer_id` §4.4 export MAP).** The symmetric companion to the CP21 `ble_service_uuid → ble_uuid` map, parked since MAC-360 on an id4884 collision, applies here. The value `id23052` is normalized `'67' → '0x0043'` (decimal to canonical hex) so the Bluetooth-SIG company identifier renders consistently. CP47 is applied to canonical in the Wave-3 ingest; its formal Bible amendment rides the board push gate with the rest of this stack.
- **CP50 (`ble_local_name` literal/template split, proposed).** The Lynceus writer now separates literal BLE local-names (exact GAP advertisement strings, feed-eligible) from template local-names (wildcards and per-device suffixes that would over-match, held). 12 literals reach the feed, 14 templates stay dropped. CP50 is proposed; its Bible amendment is reserved for the board push gate.

### Bible amendments

- **None landed in this commit.** CP47 (applied to canonical in the Wave-3 ingest, STAGE-ONLY) and CP50 (proposed) both carry their formal `BIBLE_AMENDMENTS.md` ratification to the board push gate, consistent with the staging discipline. No ratification is recorded ahead of board sign-off.

### Halts encountered

- None.

---

## v1.6.10 - 2026-06-14

A **multi-cohort data release** on top of v1.6.9: Wave 2 ([MAC-392](/MAC/issues/MAC-392) / [MAC-419](/MAC/issues/MAC-419), canonical write `3d5785b`), bundled with the board-ratified Axon body-cam GATT micro-increment ([MAC-352](/MAC/issues/MAC-352), board approval `879bbc33`, commit `8ea3352`). The two ship under one tag because MAC-352 is woven into the same canonical write and regen and cannot be cleanly separated. The cycle admits **132 net-new identifiers** across six device cohorts plus the body-cam increment, mints two durable device categories (`smart_lock`, `smart_home_hub`), and is the project's second schema migration in two cycles. schema_version moves **32 → 33** (migration `0033`, CP46). Active identifier count moves **43,123 → 43,255** (+132); total **43,678 → 43,810** (+132, all admissions active, zero supersessions). The standard Lynceus feed grows **900 → 1,014** (+114) and the high-confidence feed **351 → 464** (+113); the behavioral-signatures feed is unchanged at 132. Every admitted value traces to a quotable public source (IEEE OUI registry, Bluetooth-SIG assigned numbers, vendor APK static analysis, bounded WiGLE confirmation passes); each cohort was CTO-re-verified against the live database, and the feed deltas below were computed from the actual regen, not estimated.

**Honest feed-reach note (binding).** Not every captured row reaches the runtime feed. The 10 cohort-1 spy-cam `ssid_pattern` families and the 5 cohort-6 `ble_local_name` rows are **§4.4 EXPORT-DROPPED** in the Lynceus writer (`export_lynceus.py`: `ssid_pattern -> None`, "no regex in Lynceus v0.2"; `ble_local_name -> None`, "no GAP local-name match"). They are captured in the canonical registry and the full CSV, but their **Lynceus feed reach is 0** under v0.2. A scanner does **not** alert on these spy-cam SSIDs or tracker local-names today. Closing that gap (regex and local-name support in the Lynceus writer) is the deferred follow-up [MAC-420](/MAC/issues/MAC-420). Of the 132 net-new rows, 114 reach the standard JSON feed; the remaining 18 are registry-internal (10 `ssid_pattern` + 5 `ble_local_name` + 3 `ble_characteristic`).

### What's new

- **`smart_lock` is now a durable export category (cohort 4, +56 feed).** Consumer and commercial BLE smart locks contribute 56 feed rows: 54 GATT `ble_service_uuid` (August 17, Kwikset 23, Ultraloq 13, Schlage 1) plus 2 `oui` (Kwikset, Assa Abloy / Yale). One prior U-tec `mac_range` row (id 7200, confidence 85) is recategorized into `smart_lock`; it was already feed-visible, so it relabels rather than adds. A scanner now alerts on a nearby smart lock by its BLE service UUID or OUI.
- **`smart_home_hub` is now a durable export category (cohort 5, +1 feed).** The Samsung SmartThings hub `oui` lands as the first `smart_home_hub` feed row.
- **Pet and kid cellular trackers reach the feed (cohort 6, `gps_tracker`, +54 feed).** 53 GATT `ble_service_uuid` (Fi / Barking Labs 23, Whistle / Mars Petcare 20, Jiobit / Life360 10) plus 1 Whistle `oui` register as feed entries. A further 5 `ble_local_name` rows are captured but §4.4-dropped (see the feed-reach note), so the cohort stages 59 and reaches 54.
- **Bluetooth tracker (+1 feed, standard only).** The Pebblebee service UUID `0000fa25` lands as a `bluetooth_tracker` `ble_uuid` feed row. It is single-source and below the high-confidence source bar, so it appears in the standard feed only; this is the lone entry by which the standard delta (+114) exceeds the high-confidence delta (+113).
- **Axon body-worn camera BLE signatures (MAC-352 bundle, +2 feed).** The METROPOLIS and AXJANUS GATT service UUIDs from the Axon Evidence Capture app (`com.axon.one` v2.2.1, sha256 `8c50b579…`, confidence 70, `body_cam`) register as `ble_uuid` feed entries; their 3 bound `ble_characteristic` rows are captured but Lynceus-dropped (the scanner discovers by service UUID, not characteristic). `RESOLVABLECAMFV1` stays DROPPED pending the [MAC-416](/MAC/issues/MAC-416) advertised-service-data taxonomy.
- **Spy cameras captured, not yet feed-visible (cohort 1, `cctv_camera`).** 10 `ssid_pattern` families from the spy-cam APK and WiGLE pass land in the registry and CSV. Under Lynceus v0.2 they are §4.4-dropped and reach the feed by 0 (see the feed-reach note and [MAC-420](/MAC/issues/MAC-420)). Cohorts 2 (GPS) and 7 (wearables) contributed zero net-new admissible rows this wave.

### Schema

- **Migration `0033` (CP46).** Extends the `device_category` CHECK enum **+2 values (`smart_lock`, `smart_home_hub`)** on both host tables (`identifiers` + `behavioral_signatures`), preserving the CP32/CP33 dual-table parity invariant (verified: both enums carry 20 values, identical sets). schema_version **32 → 33**.

### Data

- **`identifiers` active:** 43,123 → **43,255** (+132 net-new admissions, zero supersessions).
- **`identifiers` total:** 43,678 → **43,810** (+132).
- **Wave-2 staged rows (ids 44502-44628):** 127 = cohort-4 56 + cohort-5 1 + cohort-6 59 + cohort-1 10 + cohort-3 1; plus the MAC-352 body-cam 5 = 132 net-new.
- **device-category enum:** 18 → **20** (+`smart_lock`, +`smart_home_hub`); 19 of 20 categories carry active rows.
- **`manufacturers`:** **156** (no change). **`sources`:** **95** (no change).
- **Lynceus standard feed:** 900 → **1,014** (+114 = cohort-4 56 + cohort-6 54 + cohort-3 1 + cohort-5 1 + MAC-352 2). **high-confidence feed:** 351 → **464** (+113, same set minus the single-source Pebblebee row). **behavioral-signatures feed:** **132** (no change). **CSV:** 43,255 rows, matching the active count.
- **Feed-membership note (load-bearing).** 114 of 132 net-new rows reach the JSON feeds. The 18 that do not are the 10 `ssid_pattern` + 5 `ble_local_name` (§4.4-dropped) + 3 `ble_characteristic` (scanner matches by service UUID). All 132 appear in `argus_export.csv`.

---

## v1.6.9 - 2026-06-14

A **data-shape release** on top of v1.6.8, the dedicated BLE-tracker fast-follow promised in the v1.6.8 notes (MAC-387). It does three coupled things: mints a durable `bluetooth_tracker` device category (the project's first schema migration since 0031), recategorizes the 46 captured tracker rows out of the export-suppressed `unknown` bin, and absorbs the ratified MAC-359 `ble_service_uuid → ble_uuid` export MAP so BLE service UUIDs reach the Lynceus feeds for the first time. **No new identifiers are sourced**, every value already landed in v1.6.8 and traces to its cohort-1 artifact (OpenHaystack, peer-reviewed Find-My teardowns, Bluetooth-SIG `0x004C`); this cycle is categorization + export-visibility only. schema_version moves **31 → 32**; manufacturers, sources, and the active identifier count are unchanged (43,123 active). The standard Lynceus feed grows **737 → 900** and the high-confidence feed **348 → 351**, as the BLE service-UUID map surfaces 163 previously-dropped rows (feed `ble_uuid` entries 8 → 171). One false-positive was caught and held during validation, the Apple/Google Exposure-Notification UUID `0xFD6F`, a cross-vendor magnet, recategorized back to `unknown` so it reaches neither feed.

### What's new

- **`bluetooth_tracker` is now a durable export category.** The board's #1 cohort, AirTag, Tile, Samsung SmartTag, Chipolo, and the AirGuard Find-My accessory UUIDs, is now export-visible. 46 rows move `unknown → bluetooth_tracker`: the 41 cohort-1 net-new from v1.6.8 (ids 44416-44456) plus 6 prior tagfinder service-UUID rows that belong (Samsung `0xfd5a`, Tile `0xfdcd`, Apple Find My `7dfc9002`/`7dfc9003`/`74278bda`/`0xfd44`), minus the `0xFD6F` false-positive. A scanner now alerts on a nearby AirTag or SmartTag by its BLE service UUID.
- **BLE service UUIDs reach the feed (MAC-359 map absorbed).** The ratified §4.4 `ble_service_uuid → ble_uuid` alias-collapse (CP21), parked since its draft, ships here because it is load-bearing for tracker visibility. Feed `ble_uuid` entries move 8 → 171. The symmetric `ble_company_id → ble_manufacturer_id` map (MAC-360) stays HELD on an unresolved id4884 collision and does **not** ride this release.
- **False-positive hygiene.** Validation flagged `0xFD6F` (id 44433), the Apple/Google Exposure-Notification service UUID, a cross-vendor magnet that would fire on unrelated contact-tracing hardware, and held it at `unknown` (MAC-390), so it is absent from both feeds. The `0x0075`/`0x02d0` company-ID-as-service-UUID corruptions and the `0xfe9f` Google-assigned UUID were excluded from the tracker set up front.

### Schema

- **Migration `0032` (CP45), first since 0031.** Extends the `device_category` CHECK enum **+1 value `bluetooth_tracker`** on both host tables (`identifiers` + `behavioral_signatures`), preserving the CP32/CP33 dual-table parity invariant. schema_version **31 → 32**.

### Data

- **`identifiers` active:** 43,123 → **43,123** (no change, 46 rows recategorized `unknown → bluetooth_tracker`; no admissions or withdrawals).
- **`identifiers` total:** **43,678** (no change).
- **device categories:** 17 → **18** (+`bluetooth_tracker`).
- **`manufacturers`:** **156** (no change). **`sources`:** **95** (no change).
- **Lynceus standard feed:** 737 → **900** (+163, BLE service-UUID surfacing). **high-confidence feed:** 348 → **351** (+3). **behavioral-signatures feed:** **132** (no change).

### Bible amendments

- **CP45**, mints `device_category='bluetooth_tracker'` (taxonomy +1, dual-table); narrows the §11 #13 `unknown`-category export ban to exclude this promoting category; absorbs the MAC-359 `ble_service_uuid → ble_uuid` export MAP. CP45 is the next-free slot above landed CP44 (the MAC-351 cross-vendor draft was folded into CP44, freeing the CP45 number); the CP46/CP47 references remain the MAC-359/MAC-360 draft reservations, MAC-359 is absorbed here, MAC-360 stays parked.

### Halts encountered

- None. The `0xFD6F` false-positive was caught by the Validator assertion battery (not a halt) and remediated via recategorization (MAC-390) plus an authoritative export re-regen and delta-verify (MAC-391).

---

## v1.6.8 - 2026-06-14

A **data release** on top of v1.6.7, and the widest-net sourcing cycle the project has run (MAC-362 / MAC-363). It admits **81 net-new identifiers** across five device cohorts plus a deferred-revival cleanup, and it withdraws 25 bad OUIs that had been shipping in the standard feed. Active identifier count moves **43,213 → 43,123**, because the cleanup outweighs the admissions. **No schema migration** (schema_version stays **31**), **+1 manufacturer** (155 → 156, Qualcomm), **+9 sources** (86 → 95). The Lynceus high-confidence feed grows **322 → 348**, the standard feed **736 → 737**, and the behavioral-signatures feed **125 → 132**. Every identifier traces to a quotable public source (IEEE OUI registry, Bluetooth SIG assigned numbers, FCC filings, APK static analysis, academic Find-My teardowns); none came from model memory. The board approved the push (approval `1598798c`) after an independent re-verification against the live database, a backup-first apply per cohort, and an operator-gated fast-forward.

### What's new

- **Consumer surveillance OUIs (+26, the feed-additive cohort).** Ring/Amazon, Wyze, Arlo, and Blink doorbell and camera MAC prefixes register as 26 net-new `oui` rows (ids 44471-44496), confidence 85, category `cctv_camera`. These are the only rows that reach the runtime Lynceus feeds this cycle, so a scanner now alerts on a nearby Ring or Wyze camera by its OUI. Doorbells land as `cctv_camera` for now; a dedicated `video_doorbell` subtype is queued (MAC-381).
- **Bluetooth trackers and stalkerware (+41, captured, feed-visibility queued).** AirTag, Tile, Samsung SmartTag, and Chipolo register 41 net-new BLE rows (36 `ble_service_uuid`, 3 `ble_characteristic`, 2 `ble_uuid`) from OpenHaystack and peer-reviewed Find-My teardowns plus Bluetooth-SIG company-ID `0x004C`. We declined the Apple MFi, Tile SDK, and Samsung SmartThings Find click-through licenses and stayed on the facts-only academic path. These land export-suppressed (`device_category='unknown'`); their feed-visibility ships in a dedicated fast-follow (MAC-387) so the new tracker category lands under the settled BLE export map.
- **ALPR and cop-car (+14).** Flock, Motorola/Vigilant, Genetec, and adjacent license-plate-reader vendors contribute 6 `ssid_pattern`, 5 `fcc_grantee_code`, and 3 `equipment_class_code` rows from APK package-ids and FCC filings, extending the v1.6.7 Flock/cop-car teardown method. All are Argus-internal types outside the Lynceus `{mac, oui, ssid, ble_uuid}` schema, so they sit in the CSV, not the JSON feeds.
- **Drones, body cams, and DeFlock (no net-new identifiers).** The drone cohort (DJI/Parrot/Skydio/Autel/Anduril) added 3 sources, 5 behavioral signatures, and a 13-row FCC-band reclassification, with no new identifier values. The body-cam and acoustic cohort (Axon/Motorola/ShotSpotter/Getac) confirmed zero net-new admissible surface, since all four vendors already carry coverage from prior waves. The DeFlock coordinate tier (sid 6, ODbL-1.0) was probed read-only and held: it is structurally coordinate-only, carries no Kismet-visible identifier, and stays in `deployment_observations` rather than crossing the ODbL share-alike door.
- **Deferred-revival cleanup.** Correctness fixes from the FoggedLens, OpenIPC, and MAC-337 revival pass: a source license correction (sid-86 to MIT), a FoggedLens source row, a Coban grantee re-attribution, and a 39-row Qualcomm `chipset_codename` re-attribution that registers Qualcomm as a manufacturer (id 326). All are export-DROPPED registry hygiene.
- **Standard-feed hygiene (-25 OUIs).** The cleanup withdrew 23 known-fake, locally-administered, and multicast OUIs that had been live in the standard feed (MAC-385) and corrected 2 cohort-2 mis-attributions (MAC-375). Withdrawing bad data is why the standard feed moves only +1 net against +26 admissions.

### Schema

- **No migrations this cycle.** Migration ledger stays **0001 through 0031**; schema_version stays **31**. The new cohorts use existing identifier-type and category slots. The `bluetooth_tracker` category mint waits for the MAC-387 fast-follow.

### Data

- **`identifiers` active:** 43,213 → **43,123** (-90: +81 net-new admissions, outweighed by ~173 supersessions from the MAC-385 known-fake collapse-and-withdraw and the MAC-375 correction).
- **`identifiers` total:** 43,595 → **43,678** (+83).
- **`manufacturers`:** 155 → **156** (+1, Qualcomm).
- **`sources`:** 86 → **95** (+9: academic Find-My and OpenHaystack for trackers, drone vendor and FAA-RID, consumer mirrors, FoggedLens).
- **`behavioral_signatures` export records:** 125 → **132** (+7, drone footprints).
- **Lynceus high-confidence export records:** 322 → **348** (+26 consumer-camera OUIs at confidence 85). **Standard export records:** 736 → **737** (+26 consumer, -23 MAC-385, -2 MAC-375). **CSV:** 43,123 rows, matching the active count.
- **Export-membership note (load-bearing).** Only the 26 consumer-camera OUIs reach the US-filtered JSON feeds. The 41 BLE-tracker rows stay export-suppressed pending MAC-387; the ALPR `ssid_pattern` / `fcc_grantee_code` / `equipment_class_code`, the drone `fcc_grantee_code`, and the revival `chipset_codename` rows are Argus-internal types outside the Lynceus schema. All admitted rows appear in `argus_export.csv`.

### Bible amendments

- **CP44, cross-vendor-constant exclusion gate (§11 #21).** One consolidated correction pass folding the earlier provisional CP44/CP45 work: a constant that shows up across unrelated vendor apps (the `0xFE59` / `258eafa5-…` class) is not a single-vendor device signature, so it is excluded by name. Committed `8a4fab3`.

### Halts encountered

- **None.** Each cohort applied backup-first with an independent re-verification, and the validator battery (including lookup-tuple uniqueness) passed on every promotion batch. The 311 MB pre-apply database snapshots were caught outside `.gitignore` at the ship-gate and excluded before any commit.

## v1.6.7 - 2026-06-12

A **data release** layered on top of v1.6.6. It admits **+290** identifiers across two cohorts: the R2 SoC chipset set held back from v1.6.6, and the Flock / cop-car Android-app static-analysis cluster. Active identifier count **42,923 → 43,213**. **No schema migration** (schema_version stays **31**), **+14 manufacturers** (141 → 155), **+10 sources** (76 → 86). The Lynceus JSON feeds hold flat (high-confidence **322**, standard **736**) because every new row is an Argus-internal type, `chipset_codename`, `vendor_controlled_hostname`, `network_endpoint`, outside the Lynceus `{mac, oui, ssid, ble_uuid}` watchlist schema; all 290 land in the full CSV (43,213 rows). Both cohorts were operator-approved after an independent re-validation against the live database, a backup-first apply, and an operator-gated push.

### What's new

- **R2 SoC chipset batch (+79).** Gate-1C of the R2 cohort, board-ruled Option A (MAC-345). 13 silicon component vendors register as a distinct `component_vendor` category, kept separate from end-product OEMs: HiSilicon, Rockchip, Ambarella, SigmaStar, Goke, Fullhan, Ingenic, Novatek, Anyka, Allwinner, GrainMedia, Xiongmai, Texas Instruments. **79 net-new `chipset_codename` rows** promote from the OpenIPC firmware corpus (90 staged minus 11 build-flavor variants), sourced `crowdsourced` / tier-2. Board approval `9e011eb8`; shipped first as the untagged increment `e1e2fae`.
- **Flock / cop-car APK cluster (+211).** Vendor mobile apps for the surveillance and fleet-telematics vendors, fetched with a headless browser (real Chromium against the public app mirrors, no credentials, no anti-bot circumvention) and static-analyzed with `apk_harness.py` (MAC-348 / MAC-349 / MAC-350). **+211 net-new** after an exact-match dedup against 15,942 live host / endpoint / UUID values: 47 `vendor_controlled_hostname` + 164 `network_endpoint`, all confidence 70 / `manufacturer_app`. By vendor: Verizon Connect 83, Samsara 38, Flock Safety 36, Fleetio 29, Axon 13, SoundThinking 6, Motorola Solutions 6. **Fleetio** registers as a new manufacturer (id 325). The set includes the Flock Safety app `com.flocksafety.sweetwater` itself. Board approval `ba63493f`.
- **BLE UUID discipline.** The harness flagged 81 raw 128-bit strings as candidate `ble_service_uuid` rows. A GATT-context trace dropped all 81 for this release: a raw string match is not a device-pairing UUID without a real `BluetoothGattService` bind. The cross-vendor `258eafa5-…` value, present in six unrelated vendor apps, is excluded by name. The drop ledger ships at `exports/v1.6.7_admission_exclusion_record.md`. A later trace confirmed two Axon UUIDs with genuine GATT context; those land in a follow-up increment, not here.
- **§7.5 hygiene.** One employee email and eight credential-bearing URLs found in the binaries were dropped, never staged. No secret values surfaced.

### Schema

- **No migrations this cycle.** Migration ledger stays **0001 through 0031**; schema_version stays **31**. The `component_vendor` manufacturer category, the `manufacturer_app` source tier, and the `chipset_codename` / `network_endpoint` identifier types all use existing slots.

### Data

- **`identifiers` active:** 42,923 → **43,213** (+290: SoC +79, APK +211).
- **`identifiers` total:** 43,305 → **43,595**.
- **`manufacturers`:** 141 → **155** (+14: 13 `component_vendor` + Fleetio).
- **`sources`:** 76 → **86** (+10: OpenIPC firmware for the SoC batch; 2 vendor-direct + 7 apkcombo for the APK cluster).
- **`behavioral_signatures` export records:** 125 (unchanged).
- **Lynceus high-confidence export records:** 322 (unchanged). **Standard export records:** 736 (unchanged).
- **Export-membership note (load-bearing).** Every v1.6.7 row sits outside the Lynceus `{mac, oui, ssid, ble_uuid}` schema: `chipset_codename` carries `geographic_scope=global`, and the APK hosts and endpoints are not Lynceus identifier classes. The US-filtered JSON feeds hold at 322 / 736; all 290 appear in `argus_export.csv` (43,213 rows).

### Bible amendments

- **None ratified this cycle.** **CP45** (cross-vendor BLE exclusion) was drafted: a BLE UUID seen across unrelated vendor apps is shared-SDK evidence, not a per-vendor device identifier, so it does not admit without per-vendor GATT confirmation. Its ratification and ledger entry are deferred to a follow-up increment.

### Halts encountered

- **None blocking.** The apkcombo `com.evidence.flex` 410 (a delisted Axon Fleet variant) was logged as an honest-absence. The GATT-context trace, the backup-first apply, and the export regeneration came back clean.

## v1.6.6 - 2026-06-11

A **data release** layered on top of v1.6.5. It covers two waves admitted in the same cycle: the Wave WideNet acquisition pass and the R2 new-vendor cohort that v1.6.5 deferred. Active identifier count **41,716 → 42,923** (+1,207). **No schema migration** (schema_version stays **31**), **+15 manufacturers** (126 → 141, the first net-new manufacturers in several releases), **+2 sources** (74 → 76). Both waves were operator-approved after an independent re-validation against the live database, a backup-first apply, and an operator-gated push.

### What's new

- **Wave WideNet acquisition (+185).** A registry-and-acquisition pass over certificate-transparency logs, FCC filings, and vendor mobile surfaces (MAC-329): 45 `fcc_grantee_code` + 24 `product_family_codename` + 11 `ble_uuid` + 103 `vendor_controlled_hostname` (Cellebrite, Oxygen Forensics, Eagle Eye, recovered with a per-row CT-log provenance triple) + 2 endpoint rows (WatchGuard, Reveal). Two sources register: `certspotter` (`primary_registry`, RFC 6962 CT logs) and `fcc.report` (`regulatory`). The 185 rows admit at **confidence=NULL** pending a later corroboration pass; the export pipeline gained a None-guard at the confidence gate so the NULL-confidence rows carry through cleanly (`38467df`, MAC-336). 27 rows were rejected to `conflicts` rather than promoted: 25 false-positive FCC grantee codes and 2 Motorola consumer OUIs.
- **R2 new-vendor cohort, Gate-1A + Gate-1B (+1,022).** The new-vendor data deferred from v1.6.5 (MAC-339 / MAC-341). **15 surveillance brands register** as manufacturers, ACTi, Amcrest, Brivo, Digital Watchdog, GeoVision, HID Global, Lorex, March Networks, Mobotix, Openpath, Reolink, Speco, Swann, Teledyne FLIR, i-PRO, unlocking **51 registry rows** (20 `oui` + 3 `mac_range` + 28 `fcc_grantee_code`). **Reolink firmware** lands at full volume: 860 `firmware_sha256_hash` + 111 `firmware_branded_string`, each with a SHA-256 and provenance from the `reolink-fw-archive` `pak_info.json`. Board approval `06436619`. The SoC component-vendor batch (90 `chipset_codename`) stayed held this release pending the board's component-vendor category ruling; it ships in v1.6.7.

### Schema

- **No migrations this cycle.** Migration ledger stays **0001 through 0031**; schema_version stays **31**. All admitted `identifier_type`s use existing CHECK-enum slots.

### Data

- **`identifiers` active:** 41,716 → **42,923** (+1,207: WideNet +185, R2 +1,022).
- **`identifiers` total:** 42,098 → **43,305**.
- **`manufacturers`:** 126 → **141** (+15 surveillance brands).
- **`sources`:** 74 → **76** (+2: `certspotter`, `fcc.report`).
- **`conflicts`:** 36 → **63** (+27 WideNet rejections, not promoted).
- **`behavioral_signatures` export records:** 125 (unchanged).
- **Lynceus high-confidence export records:** 305 → **322** (+17). **Standard export records:** 719 → **736** (+17).
- **Export-membership note.** The +17 to both Lynceus feeds comes from the R2 registry `oui` rows, which are Lynceus-mappable. The WideNet rows do not reach the feeds: they admit at confidence=NULL, and their `vendor_controlled_hostname` / `fcc_grantee_code` / `product_family_codename` types sit outside the Lynceus `{mac, oui, ssid, ble_uuid}` schema. All 1,207 appear in `argus_export.csv` (42,923 rows).

### Bible amendments

- **None ratified this cycle.** The manufacturer admissions apply the existing §8 registration discipline; the WideNet rejections apply the existing SAR false-positive rules. No new doctrine was introduced.

### Halts encountered

- **One, resolved.** The export `None < int` confidence-gate crash surfaced when the 185 NULL-confidence WideNet rows first reached `export_lynceus.py`, the prior active set carried no NULL-confidence rows. A None-guard at the §7.5 classify gate plus two regression tests fixed it (MAC-336, `38467df`) before the release shipped. The backup-first apply and export regeneration otherwise came back clean.

## v1.6.5 - 2026-06-06

A **data release** layered on top of v1.6.4. It promoted **+208** validated, registry-sourced identifiers gathered from public registry pulls plus a firmware unpack of Dahua and Axis devices. Active identifier count **41,508 → 41,716**. **No schema migration** (schema_version stays **31**), **0 new `identifier_type` slots**, **0 new sources** (74), **0 new manufacturers** (126, all 33 attributed vendors were already registered). The release was operator-approved after an independent re-validation against the live database, a backup-first apply, and an operator-gated push.

### What's new

- **Registry promotion (+208).** Net-new public-registry identifiers, each carrying `source_url` + extraction method + `last_verified`, deduped against the live database (0 collisions), confidence bands §8.2-conformant (`primary_registry` 80-85, `regulatory` 88-90, `manufacturer_doc` 85). By type: `oui` **+133** (444→577), `mac_range` **+19** (17,806→17,825), `fcc_grantee_code` **+44** (95→139), `vendor_controlled_hostname` **+5** (12,055→12,060), `firmware_sha256_hash` **+3** (17→20), `product_family_codename` **+2** (265→267), `firmware_branded_string` **+2** (30→32). Top vendors: Hikvision, Dahua, Hanwha, Trimble, Bosch Security, Uniview, Axon, Samsara, Verkada, Avigilon.
- **Firmware binwalk (5 of the 12 firmware-attached rows).** A public Dahua IPC-HX5X3X "Rhea" build + Dahua Eos4 + Axis 206W firmware were `binwalk`/`unsquashfs`'d read-only; the **3 `firmware_sha256_hash` rows retain SHA-256 provenance and the binaries are not committed** (gitignored working data). Hardcoded `easy4ip.com` / `cpplusddns.com` / `axiscam.net` hostnames + `Rhea`/`Eos4` codenames extracted. No DRM circumvention (the obfuscated 2025 build was **not** bypassed).
- **Governance dispositions (operator-ratified):** **Cisco Meraki ×57 OUIs excluded**, vendor-wide registrant spans MV cameras + MR/MS/MX networking; cannot isolate the surveillance line (existing §8.4 multi-purpose-vendor discipline). New-vendor **+1,112** (15 surveillance brands + 13 SoC component vendors + 860 Reolink firmware hashes) **deferred to v1.6.6** pending manufacturer registration + a component-vendor attribution policy + a Reolink-volume decision. Deferrals confirmed: `cid` (0 surveillance registrants), `matter_vendor_id` (full 432-vendor DCL pull → ~2 adjacent, already covered), Nordic GATT vocab, USB/PCI capture VIDs (skip-and-surface).

### Schema

- **No migrations this cycle.** Migration ledger stays **0001 through 0031**; schema_version stays **31**. All 7 promoted `identifier_type`s and 3 `source_type`s use existing CHECK-enum slots.

### Data

- **`identifiers` active:** 41,508 → **41,716** (+208 INSERT).
- **`identifiers` total:** 41,890 → **42,098**.
- **`sources`:** 74 (unchanged). **`manufacturers`:** 126 (unchanged). **`behavioral_signatures`:** 201 (unchanged).
- **Lynceus high-confidence export records:** 178 → **305** (+127).
- **Lynceus standard export records:** 592 → **719** (+127).
- **Behavioral signatures export records:** 125 (unchanged).
- **Export-delta re-derivation note (load-bearing).** The Lynceus export delta is **+127, not +152**, and is derived from the **regenerated files**, not a projection. Of the 152 Lynceus-mappable rows (133 `oui` + 19 `mac_range`): 127 `oui` land; **6 `oui` drop** as `device_category='unknown'` (§8.4 / §11 #13 unknown-category carveout); **all 19 `mac_range` drop** because §4.4 maps `mac_range → None` (expand-if-≤256-MACs else `oversized_mac_range`) and every range is a 28-bit block (≫256). The pre-ratification dry-run's "19 mac_range → mac / +152" was incorrect on the `mac_range` mapping; the canonical **+208** promote is unaffected. The 44 `fcc_grantee_code` + 5 `vendor_controlled_hostname` + 3 `firmware_sha256_hash` + 2 `product_family_codename` + 2 `firmware_branded_string` are Argus-internal (not in the Lynceus `{mac,oui,ssid,ble_uuid}` schema); all 208 appear in the full CSV export (41,716 rows).

### Bible amendments

- **None this cycle.** No new rule was introduced, the Meraki exclusion applies the existing §8.4 multi-purpose-vendor discipline, and the deferrals are scheduling, not doctrine. **Possible future clarification flagged (not yet written):** a §4.4 note that `mac_range` promotions do not add to the Lynceus watchlist (they are expanded or dropped), so registry-OUI cycles should project Lynceus changes from concrete-category `oui` rows only.

### Halts encountered

- **None.** The independent re-validation, backup-first apply, and the coverage-matrix and export regeneration all came back clean (0 halts).

## v1.6.4 - 2026-06-05

A **notes / data update** layered on top of v1.6.3: a single correction that restores a higher confidence level and `severity='high'` to one validated group of 19 identifiers, reversing a down-weighting from the previous release. **No records were added or removed, and there was no schema migration this cycle**; the only change is a confidence and severity adjustment plus an added `notes` marker on those 19 rows, landed at commit `3b6eb32`. Active identifier count stays at **41,508**; schema_version stays **31**.

### What's new

- **Restored confidence for the EthanThePhoenix38 detection data.** A follow-up review re-examined the earlier `chip_vendor_oui_24` down-weighting in light of two things: (a) a Lynceus interface update that now shows the matched OUI alongside the Flock label in alerts, which closes the ambiguity that prompted the original false-positive report; and (b) careful curation of the source data from the EthanThePhoenix38/flock-you-camera-detector project, which removed false positives. The 19 rows (ids 22810-22828, `geographic_scope='US'`) move from the earlier conf=60 / severity=NULL state back to **conf=85 / severity='high'**, keeping the existing `notes.crowdsourced_breadth_tier='chip_vendor_oui_24'` value and adding a new `notes.cp43_basis='path_ii_negative_evidence_curation_with_lynceus_disambiguation'` marker (the earlier history is retained alongside it). A second group (ids 35618-35635, from the colonelpanichacks/flock-you source, `geographic_scope=NULL`) keeps the earlier down-weighting and was deliberately left out of scope.
- **Important dependency.** This confidence restoration depends on the Lynceus interface continuing to show the matched OUI in alerts. If that display is dropped so users see only the bare vendor label, the original false-positive concern returns and **this change must be re-examined**. This caveat is recorded in the changelog, CREDITS, and `docs/engineering/BIBLE_AMENDMENTS.md`.

### Schema

- **No migrations this cycle.** CP43 is a notes / data mutation only. The migration ledger stays at **0001 through 0031**; schema_version stays **31**.

### Data

- **`identifiers` active:** 41,508 (unchanged; no INSERT/DELETE this cycle).
- **`identifiers` total:** 41,890 (unchanged).
- **`severity='high'` cohort:** 255 (v1.6.3 ship) → **274** (post-CP43; +19 Cohort A rows re-promoted).
- **`sources`:** 74 (unchanged). **`manufacturers`:** 126 (unchanged). **`behavioral_signatures`:** 201 (unchanged).
- **Lynceus high-confidence export records:** 159 (v1.6.3 ship) → **178** (post-CP43; +19, exactly ids 22810-22828; CP7 `geographic_scope='US'` filter unchanged).
- **Lynceus standard export records:** 592 (unchanged, the 19 rows already cleared the conf≥30 floor at conf=60, so standard-export membership is unaffected).
- **Behavioral signatures export records:** 125 (unchanged).

### Bible amendments

- **CP43** (`docs/engineering/BIBLE_AMENDMENTS.md:5589`), Selective revert of CP40 for negative-evidence-validated /24 OUI cohorts (Cohort A re-promotion; Cohort B retained under CP40).

### Halts encountered

- None. The 19-row change landed at commit `3b6eb32` and passed an independent read-only verification battery (8/8) against that commit before the documentation and export work began.

## v1.6.3 - 2026-06-03

A **notes, severity, and code-correctness update** layered on top of the v1.6.2 data. **No records were added or removed from `identifiers` this cycle**, every change is a column addition, a notes update, or a consumer-export fix. It also includes the v1.6.2.1 content (the new severity column and the Flock-hunt floor carve-out), which had been held back and never separately tagged. Active identifier count stays at **41,508**; schema_version advances **30 → 31** (the column added in v1.6.2.1 is the schema this release ships).

### What's new

- **Chip-vendor OUI correction.** A field-finder run on 2026-06-02 found that 37 rows in the lifted Flock-hunt group were Wi-Fi chip-vendor OUIs wrongly marked as Flock-attested. This change moves those rows out of `severity='high'`, with a `notes.cp40_marker` value recording the correction. The `severity='high'` group moves from 292 active rows down to 255.
- **Documented the operator-override rule and closed two vendor paper-trails.** A new rule in the project spec governs how an operator may make a single manual database correction to fix drift: it must be individually authorized, limited to one statement, captured before and after, backed up with a checksum, cross-referenced in the handoff, and read-only afterward. Separately, the `manufacturers.notes.arm_flip_history` records for Avigilon (id=6) and Pelco (id=254) were filled in to document ownership changes that were left unrecorded when those vendors were first added.
- **Export-correctness fixes.** Two fixes to the Lynceus export code (`db/validation/export_lynceus.py`): the first restores the correct handling that drops `imei_tac` rows from the consumer mapping (a mis-annotation had changed it); the second restores the identity-keyed `DROPPED_REASONS` convention after a regression had overwritten it with positional keys.
- **Included the v1.6.2.1 content.** The new `identifiers.severity` column (`high`/`medium`/`low`/`NULL`) and the §7.5 floor carve-out for named Flock-hunting project sources (DeFlock, the `flock-you` family, GainSec's Flock research repos, and similar, 10 named sources) first landed at commit `233a634` on 2026-06-03 and were held back; v1.6.3 is their first public ship. See the v1.6.2.1 section below for the full detail.

### Schema

- **mig-0031** (`identifiers.severity` column add) is the v1.6.3 ship anchor, already documented at v1.6.2.1, but re-mentioned here because v1.6.2.1 was never separately tagged; the v1.6.3 stack is its first public ship cycle.
- **No additional migrations this cycle.** CP40 / CP41 / CP42 §1 / CP42 §2 are all data / notes / code mutations, not schema mutations. The migration ledger stays at **0001 through 0031**.

### Data

- **`identifiers` active:** 41,508 (unchanged from v1.6.2; no INSERT/DELETE this cycle).
- **`identifiers` total:** 41,890 (unchanged).
- **`severity='high'` cohort:** 0 (pre-v1.6.2.1, column didn't exist) → 292 (CP39 narrow-scope landing at v1.6.2.1) → **255** (post-CP40 Lynceus chip-vendor OUI remediation; -37 net).
- **`manufacturers.notes.arm_flip_history` backfill:** 2 rows (id=6 Avigilon + id=254 Pelco) per CP41.
- **`sources`:** 74 (unchanged). **`manufacturers`:** 126 (unchanged). **`behavioral_signatures`:** 201 (unchanged).
- **Lynceus high-confidence export records:** 146 (v1.6.2 baseline) → 178 (v1.6.2.1 CP39 narrow-fork lift) → **159** (v1.6.3 ship, post-CP40 chip-vendor remediation).
- **Lynceus standard export records:** 592 (unchanged).
- **Behavioral signatures export records:** 125 (unchanged).

### Bible amendments

- **CP40** (`docs/engineering/BIBLE_AMENDMENTS.md:5400`), Identifier-specificity gate on §7.5 floor carve-outs (chip-vendor OUI remediation).
- **CP41** (`docs/engineering/BIBLE_AMENDMENTS.md:5472`), §11 #18 ratification → ratified as §11 #20 + Avigilon/Pelco arm-flip paper-trail closure.
- **CP42 §1** (`docs/engineering/BIBLE_AMENDMENTS.md:5546`), `imei_tac` Lynceus §4.4 consumer-side disposition restoration.
- **CP42 §2** (`docs/engineering/BIBLE_AMENDMENTS.md:5569`), CP35 §215 supersedure: `DROPPED_REASONS` identity-keyed convention restored.

### Halts encountered

- **Amendment-slot numbering shift.** A bible amendment was first drafted for one rule slot (§11 #18) but landed at another (§11 #20) because other amendments claimed the intervening numbers first. It was corrected when the amendment was applied.
- **Wording correction in an amendment.** A clause in the same amendment was reworded when applied so its text matched the actual scope of the change.
- **Amendment-numbering collision.** Two separate changes were drafted against the same amendment number; the conflict was resolved by giving them distinct numbers.

## v1.6.2.1 - 2026-05-30

A **schema-bump patch** that adds a new optional `severity` column to the `identifiers` table and labels Flock Safety + Flock-context data as `severity='high'`, plus lifts a cohort of crowdsourced Flock-hunting data into the high-confidence export.

### What's new

- **New column: `identifiers.severity`**, optional enum (`high` / `medium` / `low` / `NULL`). Default `NULL`. Captures surveillance-impact class as an axis orthogonal to `confidence` (which captures identifier-veracity). Narrow scope this cycle: only Flock-attested rows are labeled `high`; everything else stays `NULL` pending future cycles.

- **Flock-hunt project carve-out, 124 identifiers promoted into the high-confidence export.** Rows whose source is one of the named Flock-hunting GitHub projects (DeFlock, the `flock-you` family, GainSec's Flock research repos, and similar, 10 named sources) are now admitted at confidence ≥85 with `severity='high'`, even though `source_type` remains `crowdsourced`/`inferred`/`academic`. The rationale: those upstream projects have been released and have active users, which is sufficient external verification for our purposes. This is the first carve-out to the strict `≥70 + excludes crowdsourced/inferred` floor on `argus_export_high_confidence.json`; it is named and bounded (does not open the floor for arbitrary crowdsourced lifts elsewhere).

- **All Flock Safety records now labeled `severity='high'`.** 231 Flock Safety identifiers + 61 partner/LE-context identifiers from Flock-hunting sources (SoundThinking, Hikvision-via-FlockYou, Axon-via-Flock-context, etc.) carry the new `severity='high'` field. Total `severity='high'` rows: **292**.

- **Manufacturer normalization (clerical sub-pass).** 67 rows previously labeled with lowercase `flock_safety` are now canonical `Flock Safety` (matching manufacturers.id=1). 39 NULL-manufacturer Qualcomm-chipset rows from a Flock-firmware repo are attributed to `Flock Safety` per the narrow plan's fallback rule; the underlying Qualcomm Snapdragon chipset family is captured in `notes` for a future cycle that may admit Qualcomm to the manufacturer lexicon.

### What stayed the same (intentional)

- **Earlier re-labeling takes precedence on third-party detection patterns.** 19 `ssid_pattern` rows that an earlier release (v1.6.0) re-labeled as `inferred/50` because they're third-party detection guesses about *other* vendors (Sierra Wireless, Cradlepoint, DJI, Parrot, Skydio, Autel, Grayshift, Magnet Forensics, MSAB, Oxygen Forensics) **keep their `inferred/50` classification AND keep `severity=NULL`**, even though they live in a Flock-hunting repository. This release's carve-out is for Flock-Safety-attributable data, not for arbitrary content hosted in those repositories.
- **False-positive caught.** One IEEE OUI row attributed to `Flock Audio Inc.` (a pro audio company, unrelated to Flock Safety surveillance) was excluded from the carve-out and the severity tag.

### By the numbers, compared with v1.6.2

| | v1.6.2 | v1.6.2.1 |
|---|---|---|
| Schema version | 30 | **31** (+1 column: `severity`) |
| Active identifiers | 41,508 | 41,508 (unchanged, labeling/lift only, no insert/delete) |
| Sources | 74 | 74 (unchanged) |
| Manufacturers | 126 | 126 (unchanged) |
| `manufacturer = 'Flock Safety'` (canonical) | 125 | **231** (+67 lowercase-normalize + 39 NULL-mfr attribution) |
| `manufacturer = 'flock_safety'` (lowercase) | 67 | 0 |
| `severity = 'high'` | 0 (column didn't exist) | **292** |
| Lynceus high-confidence export records | 146 | **178** (+32 from CP39, the Flock-hunt rows whose identifier_type maps to a Lynceus pattern survive the §4.4 mapping; the rest of the 124 lifts are DROPPED at §4.4 for type-mapping reasons unchanged by CP39) |
| Lynceus standard export records | 592 | 592 (unchanged, the +124 lifted rows were either already in standard export or DROPPED at §4.4) |
| Lynceus CSV export records | 41,508 | 41,508 (gains `severity` column) |

### Technical notes

- Schema migration `0031_cp39_severity_column_flock_carveout.sql`. Pattern: SQLite table-rebuild. All prior `CHECK` constraints carried forward verbatim.
- Bible amendment: CP39 in `docs/engineering/BIBLE_AMENDMENTS.md` (the §7.5 floor carve-out rule + the CP38 precedence sub-clause + the false-positive handling).
- Audit record: the change is logged in the `extraction_runs` table.
- Pre-action backup: `db/argus.db.pre_mig0031_20260530T151838Z.bak` (project's internal archive).

## v1.6.2 - 2026-05-29

This release adds **116 net-new identifiers** to the v1.6.0 corpus, deepening identifier coverage for existing surveillance-camera vendors (Hikvision, Uniview, Reolink, Bosch Security Systems, Verkada, Hanwha Vision, Dahua, Axis Communications, Avigilon, Eagle Eye Networks, Milestone, Rhombus, FLIR, WatchGuard Video) and the surveillance-camera SoC supply chain (HiSilicon, Texas Instruments, Ambarella, Novatek) across firmware build strings, chipset codenames, vendor-controlled hostnames, FCC equipment-class codes, network-discovery patterns, and other identifier types. The release also removes 36 documentation-pattern placeholder rows from the earlier CCTV integration.

**No schema migration, no new sources, no new manufacturers**, the new identifiers landed under existing source coverage (vendor portals + cert-transparency queries + FCC equipment-grantee filings + NVD CVE entries + companion-app APK extracts + IEEE OUI + web.archive.org), so schema stays at 30 and source / manufacturer counts stay at 74 / 126.

### What changed

- **Corrected promotion of 116 identifiers.** A revisited 116-row promotion landed in identifier id range `[42593, 42708]`, plus 8 confidence- or provenance-only lifts on previously-staged rows (two true cross-source corroboration lifts: id=27468 85→90, id=29328 90→95; six provenance-only lifts holding their prior confidence). An earlier version of this promotion would have lifted one row above the per-source confidence ceiling for `manufacturer_app` evidence; a mechanical re-verification against the spec caught it, and the corrected pipeline held the disposition. Every lifted row carries an audit note recording the correction.

- **Removal of 36 placeholder CCTV rows.** 36 documentation-pattern rows from the earlier CCTV integration were demoted (marked as superseded) with a structured audit record. Distribution: 18 OUI placeholders (`00:00:00` ×15, `01:01:01` ×2, `ff:ff:ff` ×1) plus 18 network-discovery-protocol-pattern placeholders (`224.0.0.251` ×3, `1900` ×2, `5353` ×1, `8000` ×12). All 36 rows are excluded from every Lynceus consumer export.

By the numbers, compared with the previous release:

| | v1.6.1 | v1.6.2 |
|---|---|---|
| Schema version | 30 | 30 (unchanged) |
| Active identifiers | 41,428 | **41,508** (+80 net: +116 promotion, -36 strip) |
| Total identifiers | 41,774 | 41,890 (+116; strip demotes are self-loops, not deletes) |
| Demoted (`superseded_by IS NOT NULL`) | 346 | 382 (+36) |
| Sources | 74 | 74 (unchanged) |
| Manufacturers | 126 | 126 (unchanged) |
| Behavioral signatures | 201 | 201 (unchanged) |
| Lynceus high-confidence export records | 146 | 146 (the 36 strip rows were already below the ≥70 cut) |
| Lynceus standard export records | 610 | 592 (-18 from the OUI strip; the 18 protocol-pattern strips were already excluded by the §4.4 NDPP drop bucket) |
| Lynceus CSV export records | 41,544 | 41,508 (-36, 1:1 with the strip demotes) |

### Technical notes

- Schema version stays at 30. No migrations.
- The latest bible amendments remain the `network_surveillance` device-category addition (schema-changing, at v1.6.0) and the FlockYou crowdsourced-SSID reconciliation (data-only, at v1.6.0). No new amendments this release.
- Full amendment records remain in the engineering bible (`docs/engineering/BIBLE_AMENDMENTS.md`).
- A backup of the pre-removal database snapshot is recorded in the `extraction_runs` table (`notes.backup_sha256`); the backup file itself is held in the project's internal archive, not in the public source tree.
- The 116 corrected-promote candidates this cycle were initially surfaced by a trial run of the Hermes / minimax m2.7 extraction tooling; the final records landed through the canonical extraction → validate → promotion pipeline.

## v1.6.1 - 2026-05-25

A **docs-only** patch over the v1.6.0 data ship. **No database change, no migrations, no promotions, no export-semantic change**, the schema version stays at 30 and the active identifier set stays at 41,428. This release makes the change log easier to read and tidies the repository.

### What changed

- **Plain-language rewrite of the v1.6.0 entry** (below), plus removal of internal release-cycle codenames from the visible prose of every version entry. These were internal shorthand that meant nothing to a reader of the public change log; the facts, counts, and dates behind them are unchanged. Every version entry is preserved.
- **Documentation refresh:** the data dictionary's live row-count snapshot was brought up to date with the v1.6.0 database (schema 30; 41,428 active identifiers; 126 manufacturers; 74 sources).
- **Repository hygiene:** internal planning and backup artifacts were removed from the canonical source tree (they remain preserved in the project's internal archive).

## v1.6.0 - 2026-05-25

This release substantially expands Argus's coverage of surveillance and security-vendor equipment, **+3,627 device identifiers** and **+34 manufacturers**, and adds several new vendor categories.

### What's new

New vendor categories now covered:

- **Facial recognition**, NEC NeoFace, Idemia, Cognitec, AnyVision/Oosto, Paravision, Rank One, DataWorks Plus, FaceFirst.
- **Mobile spyware**, NSO Group, Cytrox, Gamma Group (FinFisher), Hacking Team (Memento Labs), Candiru, QuaDream. Drawn from public Citizen Lab and Amnesty International forensic reports.
- **Lawful-intercept / network-surveillance platforms**, Pen-Link, SS8, Cognyte, Utimaco, Polaris Wireless, Trovicor.
- **Mobile forensic-extraction tools**, MSAB, Magnet Forensics / Grayshift, Oxygen Forensics, Detego, Compelson.
- **Counter-drone systems**, Aaronia, Hidden Level, Epirus, CACI SkyTracker, plus the Anduril product family.

By the numbers, compared with the previous release:

| | Before | After |
|---|---|---|
| Active identifiers | 37,801 | **41,428** |
| Manufacturers | 92 | **126** |
| Sources | 73 | **74** |
| Device categories | 16 | **17** |

The new source is CISA's Known Exploited Vulnerabilities (KEV) catalog. The new device category covers lawful-intercept and network-surveillance platforms, so they're no longer grouped with offensive hacking tools.

### Data-quality notes

- **Confidence re-labeling:** 19 Wi-Fi network-name (SSID) patterns, covering Sierra Wireless, Cradlepoint, and several drone makers, were re-labeled from "high confidence" down to "inferred." They originally came only from a community-built detection app, not from the vendors themselves, so the lower confidence is more honest. The data is kept; only its confidence and source label changed.

### Known follow-ups (planned for a later release)

- A few vendors couldn't be fully indexed this cycle because of rate limits on certificate-transparency lookups; recovery is planned.
- The companion scanning tool (Lynceus) will add support for the new network-surveillance category in an upcoming version.

### Technical notes

- Schema version 29 → 30. One migration adds the `network_surveillance` device category to both the identifiers and behavioral-signatures tables.
- Full amendment records live in the engineering bible (`docs/engineering/BIBLE_AMENDMENTS.md`).

## [v1.5.4], 2026-05-24

A **docs-only** patch that refreshes the canonical documentation surface to the v1.5.3 state. **No DB mutation, no migrations, no promotions, no export-semantic change.** `schema_version` stays at 29; the active identifier set stays at 37,801. This release exists because the v1.5.3 data ship intentionally shipped its data ahead of the doc refresh (separate ship cycles); v1.5.4 brings the prose into line with the database.

### Highlights

- Canonical docs reconciled to live state: `schema_version=29`, 37,801 active identifiers, 73 sources, 92 manufacturers, 201 behavioral signatures, 116 `judicial_filing` rows, 18 NDPP rows.
- `DATA_DICTIONARY.md` rolled forward two migrations (was pinned at schema 27): mig-0028 (CP34 `network_discovery_protocol_pattern`, `identifier_type` 57→58) and mig-0029 (CP36 `identifiers.source_type` parity, 10→13, `+judicial_filing`/`+disclosure_filing`/`+procurement_disclosure`).
- `CREDITS.md` per-source yield narratives corrected for the four newly-promoted sources (CourtListener 0→116 `judicial_filing`; fccid.io →687; Bluetooth SIG →705 `ble_company_id`; Wireshark →303) plus source_type / license-posture drift fixes.

### Docs deltas

- **`README.md`**, v1.5.2→v1.5.3 lead + "Most recent release" v1.5.3 narrative; active count 35,958→37,801; export records (standard 536→579); CSV "Records" corrected to the logical record count (37,801; the prior figure was a physical line count inflated by embedded newlines); amendment count 34→36.
- **`docs/internal/PROJECT_STATE.md`**, current-state header refreshed to v1.5.3-staged + new "v1.5.3 headline counts" table; the prior cycle table preserved as history.
- **`docs/internal/PLANNED_AND_FUTURE_UPDATES.md`**, carry-forward section appended (MAC-252 dedup hardening; MAC-261 NULL-manufacturer + Harris normalization; MAC-262 ledger-token alignment; J-1 heuristic-hardening; Cradlepoint/Cellebrite alias-expansion gate; 54-row Wayback queue) **plus an explicit "cohorts NOT extracted this wave" record**, facial-recognition-beyond-Clearview and mobile-spyware cohorts carry to v1.6.0 (0 vendors extracted; `manufacturers` unchanged at 92).
- **`docs/engineering/DATA_DICTIONARY.md`**, schema 27→29 refresh (17 stale-claim locations); migration ledger extended through 0029; true enum counts (identifier_type 58, device_category 16, source_type 13, pair_kind 5).
- **`CREDITS.md`**, 11 surgical drift-fixes (sid 4/34/48/51 v1.5.3 yields; source_type framing for sids 1/2/3; sid 7 Socrata 2021-03-22 freeze note; DeFlock OSM attribution; sid 15 MIT; v1.4.0 source-id tags). All per-release admission ledgers + the 92-vendor lexicon preserved.
- **`docs/engineering/PROJECT_BIBLE.md` + `BIBLE_AMENDMENTS.md`**, verified already-current through CP36 / CP36-extension (commit anchors `7e6160e`/`a89aaff`, `7666748`, `dda50b1` confirmed); no edit required.
- **`docs/engineering/METHODOLOGY.md`**, §7.5 PII discipline verified accurate; v1.0.0-frozen methodology snapshot intentionally not re-versioned (one optional `judicial_filing` band-reconciliation note left to the bible per its own defer-to-bible rule).

### Honest-absence dispositions (Phase K)

The v1.5.3 external-review evidence pull surfaced 7 honest-absence findings; all dispositioned, none blocking:

- The projected `_ceo_gates_queue` Phase-H deliverable shape was **formally retired** (gate-class items were routed inline via the MAC-250/251/252/253/255/256/257 issue comments by design); no retroactive backfill.
- Three sandbox audit artifacts backfilled: `_j1_unattributed_enumerated.json` (653 BLE-SIG protocol-primitive rows), `within_source_reextractions.json` (7 J-2 within-source rows), and `wall_clock_min` on five extraction JSONs.
- The facial-recognition / mobile-spyware cohort deprioritization is now durably recorded (PLANNED_AND_FUTURE_UPDATES).
- The 67 NULL-manufacturer rows + "Harris"/"Harris Corporation" attribution-form variance deferred to the v1.5.x data-hygiene queue (own ratification cycle).

### Schema

- **No change.** `schema_version` = 29 (unchanged). No migrations. (Documentation note: the live `schema_version` row 29 is stamped `0029_cp35_…` while the on-disk migration file is `0029_cp36_…`, a benign apply-time pre-re-anchor token mismatch; the structural schema is correct. Documented verbatim in DATA_DICTIONARY §4.13; an optional one-row ledger re-stamp is deferred to the v1.5.x data-hygiene queue.)

### Export verification

- Exports regenerated against the unchanged live DB and confirmed byte-identical to the v1.5.3 exports modulo the `_meta.exported_at` timestamp, confirming the docs refresh did not leak into export semantics.

## [v1.5.3], 2026-05-24

This release ships a **five-phase corpus expansion** (MAC-245; vendor / drone-RID / IMSI / GainSec / judicial-filing), together with three checkpoint ratifications: CP35, CP36, and the CP36-extension. It is a confidence-invariant release: every count delta is a new-row promotion or a source-label parity fix; no existing identifier's confidence was lifted without a second independent source (§11 #8).

### Highlights

- **Corpus expansion:** +1,843 net-new active identifiers (MAC-250), lifting the active set 35,958 → 37,801
- **`judicial_filing` source_type** admitted to the enum (migration 0029) and 116 court-filing rows relabeled from the `foia` band-bucket proxy, a label-parity fix that left the confidence column untouched (§11 #8 invariant)
- **`network_discovery_protocol_pattern` (NDPP)** Lynceus consumer-mapping ratified as DROP (§4.4); the 18 NDPP rows remain canonical in the DB, gated consumer-side until Lynceus v0.3 ships discovery-protocol-signature scanning
- **Coverage-matrix halt closed:** the `unknown_source_type` validator halt that fired against the 116 J-5 rows on every pass is now resolved (CP36-extension)

### Schema

- `schema_version`: 28 → 29
- `identifiers.source_type` enum: added `judicial_filing` (migration 0029, CP36 parity)

### Data

- Sources: 73 (unchanged)
- Manufacturers: 92 (unchanged)
- Active identifiers: 35,958 → 37,801 (+1,843)
- Behavioral signatures: 201 (unchanged)
- `judicial_filing` rows: 116 (confidence=75, relabeled from `foia`; confidence unchanged)
- NDPP rows: 18 (canonical; DROPPED-class for the Lynceus export per CP35)

### Export deltas (Lynceus / Rayhunter)

- Standard export (`argus_export.json`, confidence ≥30): 536 → 579 records (+43)
- High-confidence export (`argus_export_high_confidence.json`, confidence ≥70): 119 (unchanged count; cohort drift internal)
- The 116 `judicial_filing` rows do **not** surface on either Talos export, all carry DROPPED-class identifier types (`product_family_codename` 109 + `firmware_branded_string` 7) per §4.4. This is correct filtering, not a regression.
- `dropped_in_export.procurement_only` = 0 (§11 #14 parity)

### Bible amendments

- **CP35 (MAC-255):** §4.4 Lynceus consumer-mapping for `network_discovery_protocol_pattern` ratified as option (b) DROP, rationale `NDPP_pending_lynceus_v0_3_scanner_support`. 18 NDPP rows preserved in the canonical DB; consumer-side gating deferred to Lynceus v0.3 scanner support.
- **CP36 (MAC-251):** `identifiers.source_type` enum parity (migration 0029) + 116 J-5 relabel (`foia` → `judicial_filing`) under the §11 #8 confidence-invariant (confidence column untouched).
- **CP36-extension (MAC-256):** `SOURCE_TYPE_CEILINGS["judicial_filing"] = 85` added to `coverage_matrix.py`, closes the validator-side annotation-halt gap left when CP36 relabeled the source_type without updating the §8.2-sanity ceiling map in the same coordinated commit. Ceiling 85 inherits the `foia` band-ceiling proxy that landed the rows (§11 #8 invariant).

### Sibling-discipline

This cycle applied the downstream-consumer-audit discipline: each bible amendment was checked for sibling-commit obligations in its downstream consumers. CP35 surfaced the `export_lynceus.py` §4.4 mapping as a required sibling closure; CP36-extension surfaced the `coverage_matrix.py` ceiling map as a required sibling closure. Both were ratified and committed in-cycle rather than deferred.

### Halts encountered

- **`unknown_source_type` (coverage_matrix.py `_compute_halts`):** fired against the 116 J-5 `judicial_filing` rows after CP36's migration 0029 relabel, because the `SOURCE_TYPE_CEILINGS` §8.2-sanity map had not been updated in the same coordinated commit. Resolved by CP36-extension (MAC-256): the `coverage_report.md` halt-line transitioned `Halts at HB35: 1` → `0`.

## [v1.5.2], 2026-05-23

This release closes a parallel work cycle covering CCTV camera vendors (Track A) and IMEI TAC research (Track B), and folds in the v1.5.1 documentation restructure.

### Highlights

- Added 146 new active identifiers across 8 CCTV camera vendors
- New identifier type: `network_discovery_protocol_pattern`, covering vendor camera-discovery protocols (Hikvision SADP, Dahua AirKiss/SmartConfig, Axis ONVIF WS-Discovery, Tiandy SADP-style)
- Extractor upgraded to v5 with safer IMEI TAC handling, four new false-positive filters, and 43 additional cellular-modem vocabulary tokens
- New utility for correctly extracting base APKs from `.xapk`, `.apkm`, and `.apks` bundles (replaces a heuristic that was silently picking the wrong file)

### Schema

- `schema_version`: 27 → 28
- `identifier_type` enum: 57 → 58 values

### Data

- Sources: 73 (unchanged)
- Manufacturers: 92 (unchanged)
- Active identifiers: 35,812 → 35,958 (+146)
- Behavioral signatures: 201 (unchanged)

### Per-vendor identifier additions

Hikvision 46 · Tiandy 53 · Axis 21 · Verkada 10 · Avigilon 9 · Dahua 7

### IMEI TAC research, notable negative result

A 25-vendor sweep across cellular gateways, fleet telematics, mobile ID apps, trail cameras, ankle monitors, consumer GPS trackers, and drone pilot apps yielded zero unique IMEI TACs.

The reason matters: modern Android apps fetch TACs at runtime, dispatch them server-side, or hide numeric literals in encrypted strings. Companion-app analysis is no longer a productive way to harvest TACs.

Future TAC work will pivot to four better-suited sources:

- GSMA TAC API and public TAC list mirrors
- FCC OET authorization grant filings (grantee + product codes map to TAC ranges)
- OTA firmware analysis of cellular modules (Quectel, Sierra, u-blox)
- Android apps that bundle TAC lookup tables as assets (TacDB, IMEI Info, Phone INFO Samsung)

### Documentation

README, CHANGELOG, and project state docs refreshed and verified against the live database.

## [v1.5.0], 2026-05-22

This release significantly expands the manufacturer lexicon through parallel sessions covering military/federal and commercial/consumer device makers.

### Highlights

- Manufacturer lexicon: 52 → 92 vendors
- Three new device categories: `cctv_camera`, `persistent_surveillance`, `through_wall_radar`
- 848 new active identifiers
- New `imei_tac` identifier type (admitted for future use; no rows promoted this cycle)
- Most directly deployable additions: 35 FCC grantee codes and 2 ICAO 24-bit Mode-S addresses for CBP MQ-9 aircraft (via adsb.lol)

### Schema

- `schema_version`: 26 → 27
- `device_category` enum: 13 → 16 (in both `identifiers` and `behavioral_signatures`)
- `identifier_type` enum: 56 → 57

### Data

- Sources: 71 → 73 (added GitHub Code Search REST API and adsb.lol v2)
- Manufacturers: 52 → 92 (+40)
- Active identifiers: 34,964 → 35,812 (+848)

### New manufacturer cohorts

- Counter-drone / counter-UAS (11): Anduril, Fortem, Citadel Defense, Black Sage, D-Fend, AeroDefense, Echodyne, Liteye, Robin Radar, MyDefence, Sensofusion
- Border / persistent surveillance (6): Elbit Systems of America, General Atomics, TCOM, Persistent Surveillance Systems, Northrop Grumman, Lockheed Martin
- Through-wall radar (3): Camero, NIITEK, TiaLinx
- IMSI catcher (1): Rohde & Schwarz
- Fleet telematics (7): Geotab, Verizon Connect, Samsara, Motive, Lytx, Omnitracs, Trimble
- CCTV camera / VMS (7): Hanwha Vision, Bosch Security Systems, Milestone Systems, Pelco, Uniview, Tiandy, Vivotek
- Electronic monitoring (5): BI Incorporated, Attenti, STOP, Sentinel Offender Services, Track Group

### Retroactive recategorization

Seven existing camera vendors moved to the new `cctv_camera` primary category: Hikvision, Dahua, Axis Communications, Avigilon, Verkada, Eagle Eye Networks, Rhombus Systems.

### Documentation

README, CHANGELOG, data dictionary, credits, methodology, and project state docs all refreshed.

## [v1.4.1], 2026-05-21

This release adds automotive telematics as a tracked device category and introduces schema support for multi-arm manufacturer relationships (parent/subsidiary structure).

### Highlights

- New `automotive_telematics` device category
- Added FCC Equipment Authorization System identifier types
- First multi-arm vendor admission: Parrot Automotive as a hidden arm of Parrot

### Schema

- `schema_version`: 25 → 26
- `device_category` enum: 12 → 13 (across both `identifiers` and `behavioral_signatures` tables)
- `identifier_type` enum: 54 → 56 (added `fcc_grantee_code`, `equipment_class_code`)
- `pair_kind` enum: 4 → 5 (added `fcc_grantee_equipment_class`)
- `manufacturers` table: 3 new columns for parent/arm relationships (`parent_manufacturer_id`, `is_arm`, `query_default`)

### Data

- Sources: 66 → 71 (added 5 manufacturer apps: Hikvision Hik-Connect, Dahua DMSS, Motorola Solutions WAVE PTT, Parrot FreeFlight 6, DJI Industry Pilot)
- Manufacturers: 51 → 52 (+ Parrot Automotive)
- Active identifiers: 34,792 → 34,964 (+172)
- Raw observations: ~146,573

### Documentation

- New: `docs/internal/lynceus_handoff_v1_4_1.md`, integration handoff for downstream consumers
- README, CHANGELOG, data dictionary, credits, and methodology refreshed for v1.4.1

## [v1.4.0], 2026-05-20

### What's new in v1.4.0

Argus v1.4.0 lands the **vendor cloud-infrastructure hostname corpus** from a four-pass autonomous extraction effort. 12,590 cumulative unique hostnames flowed from 8 extraction source-classes through Phase 2 FP-scrub (97.21% survivor rate, flagged for manual top-50 GitHub-sourced calibration as carry-forward) into 12,239 net-new identifiers (11,674 `vendor_controlled_hostname` + 565 `vendor_controlled_hostname_deprecated`) across all 51 canonical vendors. Net active identifier count grows 22,553 → **34,792** (+54.3%); raw_observations 133,830 → 146,188 (+12,358 with full provenance lineage); sources 53 → 66 (+13: crt.sh CT logs + Wayback CDX + GitHub vendor first-party + 5 RIR RDAP endpoints + npm/PyPI/RubyGems + bucket payload class + a cloud-infrastructure extraction methodology umbrella).

The headline marquee finding is **`hppki.honeywell.com` promoted at confidence=99** (firmware-cert ceiling) via 4-source independent corroboration: 2 Honeywell OTA signing certificates recovered from CT40 Android firmware META-INF/com/android/otacert (issuer `C=US, O=Honeywell International Inc., OU=ACS, CN=Honeywell CodeSign RSA CA`; sha256 `60a8cf8feeb33926366776b395d6c8d9334bd8b42038b85563622ce0a1d0745b`) + crt.sh CT log attestation + binary Class A extraction + bucket payload Class A_bucket_payload_firmware. This is the strongest possible attribution chain in the Argus framework, firmware-embedded cert + vendor-signed code-signing CA + multi-source-class corroboration.

Migration 0024 extends the `identifier_type` CHECK enum 51 → 54 with three CP29 value classes (`vendor_controlled_hostname`, `vendor_cloud_endpoint_url`, `vendor_controlled_hostname_deprecated`). Two candidate CP29 value classes deferred per conservative ≥1-evidence gate: `vendor_asn_prefix` (class G halted url_pattern_issue; 0 findings) and `vendor_controlled_ip` (cert IP-SAN sub-passes 0/0/0 across the three follow-on passes). Both reserved for CP30 / migration 0025 when empirical observation surfaces.

### Source admissions (13 new)

| sid | name | source_type | source_class |
|---|---|---|---|
| 54 | Certificate Transparency Logs, crt.sh aggregator | primary_registry | B (CT log aggregator) |
| 55 | Internet Archive Wayback Machine, CDX | crowdsourced | K (public archive temporal) |
| 56 | GitHub, vendor first-party content | manufacturer_app | I (vendor source/README) |
| 57-61 | ARIN/RIPE/APNIC/LACNIC/AFRINIC RDAP | primary_registry | G (RIR; infrastructure-only admission for the next cycle) |
| 62-64 | npm Registry / PyPI / RubyGems | manufacturer_app | J (public package registry) |
| 65 | Vendor Public Cloud-Storage Bucket Payload (S3-class) | manufacturer_app | A_bucket_payload (SAR-13.5 attribution-gate-binding) |
| 66 | Vendor Cloud-Infrastructure Hostname Corpus Extraction | manufacturer_app | A/C/D/F umbrella (extraction methodology) |

Each admission carries `ratification_band` + `source_class_full_name` + admission metadata in `sources.notes` JSON per CP14/CP16 pattern. Source_type CHECK enum maps to closest existing value (no source_type enum extension this release; CP30 candidate for 5 new enum values deferred to the next cycle).

### Confidence-band ladder per CP29 §2

- **`vendor_controlled_hostname`**: 75-90 single-source default; 85-95 cross-source (CP24 independence); 95-99 firmware-embedded cert chain
- **`vendor_cloud_endpoint_url`**: 80-90 default; 90-97 with binary + CT log + sitemap multi-source corroboration
- **`vendor_controlled_hostname_deprecated`**: 80-87 default (NXDOMAIN-verified at extraction time)

### Phase 5 promotion empirical anchors (v1.4.0)

```
inserted identifiers:                  12,239
  vendor_controlled_hostname:          11,674
  vendor_controlled_hostname_deprecated:   565
per confidence band:
  conf=99 (firmware-cert ceiling):          1   (hppki.honeywell.com)
  conf=97 (cross-source + §8.3 lift):     108   (lifted candidates per CP24 independence)
  conf=87 (deprecated default high):      565   (NXDOMAIN-verified)
  conf=85 (default high single-source): 11,565   (most common, single CT-log attestation)
§8.3 lifts applied:                       108   (per wave_i_lift_candidates_synthesis.json)
raw_observations FK-chained:           12,358
```

### Manufacturer alias enrichment

6 novel Subject DN O / firmware-cert observations appended to canonical manufacturers.aliases:

- **Autel Robotics** (mfg_id=206): appended `Autel Intelligent Technology Corp.` (3 live-cert observations)
- **Axis Communications** (mfg_id=7): appended `Axis Communications AB` (2 live-cert observations)
- **Cisco Meraki** (mfg_id=207): appended `Meraki LLC` (2 live-cert observations)
- **Getac** (mfg_id=18): appended `Getac Technology Corporation` (1 live-cert observation)
- **Jacobs** (mfg_id=13): appended `Jacobs Solutions Inc.` (1 live-cert observation)
- **Honeywell** (mfg_id=211): appended `Honeywell International Inc.` (firmware OTA cert, added in post-ship corrective pass; the main Phase 6 enrichment script omitted Honeywell from its vendor-key-to-canonical mapping)

**Honeywell International Inc.** observed in firmware-embedded code-signing cert. Honeywell IS already in the canonical 51-vendor lexicon (mfg_id=211, canonical_name "Honeywell" with aliases "Honeywell Pro-Watch, Honeywell International, Honeywell Building Technologies"); the firmware-derived legal-entity string `Honeywell International Inc.` has been appended as a 4th alias to that row. (Post-ship corrective: the original Phase 6 enrichment script omitted `honeywell` from its vendor-key-to-canonical mapping and so missed this alias-merge during the main pass.)

### Bible amendments

- **CP29**, vendor hostname corpus value_classes (3 codified, 2 deferred)
- **SAR-13**, runguide-schema-fabrication discipline (PRAGMA-verify all column names + types prior to any SQL drafting against canonical schema)
- **SAR-13.5**, bucket attribution discipline (content-based attribution gate before any public-bucket-derived promotion; three-state classification: confirmed / rejected_slug_collision / ambiguous_operator_review_required)
- **SAR-15** *(post-ship codification, board comment 2026-05-20)*, per-vendor probe-scope discipline (per-vendor extraction passes must respect the rationale of the vendor's canonical admission; surfaced by 252 Johnson Matthey corporate-IT hostnames that surfaced from a vendor admitted for industrial-MAC-cohort completeness, not surveillance-axis hostname extraction; 252 rows flagged via `notes.scope_review_required=true` for next-cycle / v1.4.1 operator review per SAR-15)
- **SAR-15.5** *(post-ship codification, board comment 2026-05-20)*, Validator-role independent close-out audit discipline for large-ship cycles (≥10 phases / ≥10k promotions / ≥3 new sources / ≥1 new migration); surfaced by the Honeywell-in-lexicon miss the main self-executed pass missed

### Lynceus export disposition

`argus_export.json` (Lynceus, conf floor 30) and `argus_export_high_confidence.json` (Lynceus, conf floor 70) sizes are unchanged vs v1.3.0. All 12,239 v1.4.0 cloud-infrastructure hostnames carry `device_category='unknown'` (these are vendor attribution anchors, not device-pairable identifiers per §11 #13 ban) and are correctly DROPPED from Lynceus export at the §11 #13 device-category-unknown gate. They appear in `argus_export.csv` (full unfiltered corpus, now 34,792 records / 21 MB).

### Carry-forward queue (post-v1.4.0)

- payload.bin Android A/B OTA extraction tool for next-cycle access to inner-filesystem certs (only OTA-update certs recovered this cycle)
- GITHUB_TOKEN-authenticated rerun for higher rate posture on GitHub source mining
- Wayback CDX connectivity remediation
- `vendor_asn_prefix` + `vendor_controlled_ip` value-class observation (currently 0 empirical evidence; CP30/migration 0025 admission criteria)
- Manual top-50 GitHub-sourced calibration FP-rate anchor (Phase 2 §2.5)
- Honeywell International Inc. canonical-manufacturer admission decision (firmware-cert evidence in hand; operator ratification needed)
- CP30 source_type enum extension (5 candidate values: certificate_transparency_log, public_archive, vendor_first_party_source_code, public_package_registry, vendor_cloud_storage_payload)

### Schema migrations

- **0024**: identifier_type CHECK enum 51 → 54 (CP29 cluster), table-rebuild pattern per 0009/0011/0013/0014/0018/0019/0023 precedent; 22,633 rows preserved via INSERT SELECT *; 6 indexes recreated; FK integrity preserved.

## [v1.3.0], 2026-05-18

### What's new in v1.3.0

Argus v1.3.0 lands the **desktop-application static-analysis integration**, the first release in which the vendor-companion-app extraction methodology generalizes from the Android mobile axis to Windows / macOS / Linux desktop application binaries. Three vendor desktop applications + one FP-control binary (519 MB acquired total) ran through a thin `wave_h_wrapper.py` adapter over the unmodified mobile-axis regex-extraction core (per the CP27 §3.0 P4 disposition, v4 untouched), with extraction outputs surfaced as a partial-cohort pass covering Cohort D (drone tooling: DJI Assistant 2 Mavic + DJI Assistant 2 FPV; Skydio P11 CLEAN NEGATIVE = documented_absence) + Cohort F (sanctioned-vendor v1: Hikvision iVMS-4200) + an H2-disambig FP-control (FileZilla 3.70.5).

The headline empirical finding is **the desktop identifier-class surface differs from the mobile one** even within installer-cohort vendors that DO have desktop binaries. After the CP26 §8 semantic-validation audit pass, **net genuine `ble_service_uuid` candidates = 0** across all three real-vendor binaries. The 4 unique surviving UUID-shaped values all re-class as different identifier classes: 2× MSI ProductCodes (Hikvision iVMS-4200 main package + Multilingual Wizard sub-package), 1× COM CLSID (DJI Assistant 2 DJIBrowser LocalServer32), 1× cloud-document UUID (DJI Mavic + FPV cross-product attested in `https://duss.djicorp.com/functional-document/<UUID>`). These are vendor-controlled identifiers with empirical density worth promoting, they would be lost if the wrapper continued to filter them as "not genuine BLE UUIDs". CP28 codifies the three identifier-classes as first-class `identifier_type` enum values + migration 0023 extends the CHECK enum 48 → 51 to receive them.

The headline outcomes for downstream consumers: **22,553 active identifiers** (up from 22,549, +4 from this release's promotion), **53 sources** (up from 52; +1 `manufacturer_app` Vendor Desktop Application Static Analysis admission), **51 manufacturers** (up from 49; +2 stub admissions per MAC-178 P5 precedent, Eagle Eye Networks + Rhombus Systems via Cohort A absence-investigation), and a schema bumped from version 22 to **version 23** via one forward-only migration (the new `identifier_type` CHECK enum extension for the CP28 desktop non-BLE cluster).

### Vendor Desktop Application Static Analysis methodology

This release extends the Android APK static-analysis methodology to publicly downloadable desktop vendor applications across Windows / macOS / Linux. The methodology probes vendor binaries for: BLE service UUIDs, default SSID patterns, MAC OUI validation patterns, product-family taxonomy, ONVIF capability strings, SNMP enterprise OIDs, mDNS service types, and network-protocol magic bytes. The wrapper applies 7 supplemental SAR-12 FP-class filters codified across sessions 1 + 2 to suppress 188 desktop-platform-wide false positives that the v4 core alone would have promoted:

| # | SAR-12 FP class | Scope |
|---|---|---|
| 1 | `WINDOWS_SUPPORTEDOS_MANIFEST_GUIDS` | Microsoft application-manifest compatibility GUIDs (Vista / 7 / 8 / 8.1 / 10), every Windows installer embeds. |
| 2 | `WINDOWS_COM_INTERFACE_GUIDS` | Microsoft Windows SDK COM IIDs (`IID_IShellLinkA` + bulk-seeded from `combase.h`, `shobjidl.h`, `objidl.h`, `oaidl.h`, `unknwn.h`). |
| 3 | `WINDOWS_DEVCLASS_SETUP_GUIDS` | SetupAPI device-class GUIDs (USB / Media / Modem / Net / HID / 1394 / Image / MTP / etc.). |
| 4 | `LIBUSB_ASCII_IDENTIFIERS` | UUID-shaped ASCII strings inside libusb-win32-WDF library binary. |
| 5 | `THIRD_PARTY_DLL_PATH_PREFIXES` | UUID-class candidates whose `source_file_relative` path leaf starts with 3rd-party library prefixes (Qt5*, libcrypto-*, libssl-*, libeay32, msvcp*, msvcr*, vcruntime, libusb0, libusb-1.0, d3dcompiler_*, libegl, libglesv2, sqlite3, icu*, iconv, libffi, libxml2, zlib). |
| 6 | `WINDOWS_SXS_PUBLICKEYTOKEN` | 16-char hex publicKeyTokens in `<assemblyIdentity>` XML manifests. |
| 7 | `windows_installer_productcode_in_msi_context` | MSI/InstallShield ProductCode GUIDs in Windows Installer registry contexts (8 context markers incl. `\{`, `\Uninstall\{`, `InstallShield Wizard`). Codified post-Hikvision-CP26-§8-audit. |

The wrapper canonical path is `android_test/tools/extraction/wave_h_wrapper.py` (sibling to `wave_g_extractor.py`); the desktop runguide is `android_test/WAVE_H_RUNGUIDE.md` (sibling to `WAVE_G_RUNBOOK.md`). Desktop static-analysis extraction outputs are staged at `extraction_outputs/wave_h_pre_v1/` (HANDOFF + per-vendor candidates/fp_findings + cohort-absence rows + calibration findings).

### CP17 desktop-axis thesis bifurcation finding (marquee policy output)

The original CP17 cohort thesis (mobile origin) predicted that the operator-vs-installer cohort split would generalize from mobile to desktop. The desktop sessions 1 + 2 empirically refine this finding in two distinct dimensions:

**Dimension 1, cohort presence.** The operator-cohort desktop class has structurally dissolved into web/mobile across modern VMS + drone-tooling vendors. Session 1 confirmed this for VMS (5 of 6 Cohort A targets were web-only or UWP-MSIX, not Electron desktop, Cohort A descoped). Session 2 §3 confirms this for drone tooling (Skydio Pilot does not exist as a desktop application, Skydio's distribution is mobile + hardware-controller + cloud; documented_absence emitted). The installer-cohort desktop class persists (DJI Assistant 2 ships a desktop installer; Hikvision iVMS-4200 ships a desktop installer) but the operator-cohort class is empirically absent at the desktop axis in 2026.

**Dimension 2, identifier-class surface.** This is the NEW desktop finding the runguide did not predict. Even within installer-cohort desktop binaries that DO exist, the identifier-class surface differs from what mobile-axis extraction surfaced:

- **Mobile binaries yield genuine BLE service UUIDs** because the mobile companion is the BLE peripheral pairing endpoint. The phone IS the BLE central; the vendor app contains BLE service/characteristic UUIDs in code.
- **Desktop binaries yield MSI ProductCodes + COM CLSIDs + cloud-document UUIDs + vendor-cloud-endpoint hostnames**, not BLE protocol identifiers. The desktop client is for camera/drone management; the BLE pairing surface is in the camera/drone firmware (Cohort E) or in the mobile app, not in the desktop client.

**Policy implication for Lynceus + Talos:** Desktop findings should be consumed as a different identifier-class surface than mobile findings. A "BLE UUID + SSID" yield expectation that worked for mobile does NOT apply to desktop. The desktop value-add is in the **vendor cloud-endpoint discovery** layer (e.g., the `duss.djicorp.com` hostname surfaced from DJI Assistant 2 binaries), the **installer-time configuration surface** (MSI ProductCode + COM CLSID = vendor-controlled OS-integration identifiers), and **the absence-as-finding** (CP17 operator-cohort dissolution itself is a vendor-architectural-shift observation worth codifying). Future desktop-axis runguides should re-scope to vendor cloud-endpoint discovery + installer-config surface as headline metrics, not BLE UUIDs.

### Net new identifiers, the four CP28(c) desktop promotions

The 4 vendor-attested non-BLE UUIDs that CP26 §8 audit re-classed promote at the §8.2 sub-band ladder per CP28(c):

- **DJI `f4d4dbf5-ba4b-40db-9a44-f8395f3728cf`** (`vendor_document_uuid_cloud_reference`), cloud-document UUID embedded in DJI's `https://duss.djicorp.com/functional-document/f4d4dbf5-...` URL. Cross-product attested across DJI Assistant 2 Mavic 2.0.14 + DJI Assistant 2 FPV 2.1.2 (CP24 within-vendor-cross-product). Confidence 90 per the 80-95 sub-band ladder. §4.4 posture: **MAP**, the cloud-hostname half lifts into Lynceus's relevance window as a passively-scannable vendor cloud endpoint signature.

- **DJI `054aae20-4bea-4347-8a35-64a533254a9d`** (`windows_com_clsid_vendor_registered`), Windows COM Class ID for the DJIBrowser LocalServer32, surfaced from `Software\Classes\CLSID\{054AAE20-...}\LocalServer32` registry context in DJI Assistant 2 Mavic 2.0.14. Confidence 85 per the 75-90 sub-band ladder. §4.4 posture: **DROPPED**, install/registry context only; low passive-scan utility.

- **Hikvision `9a25302d-30c0-39d9-bd6f-21e6ec160475`** (`windows_installer_productcode_vendor_registered`), MSI ProductCode for iVMS-4200 v3.13.0.5_Multilingual main package, surfaced from `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{9A25302D-...}` registry context. Confidence 85 per the 75-90 sub-band ladder. §4.4 posture: **DROPPED**.

- **Hikvision `ce2f96d0-63d2-4b9c-a8d6-0d1a60840bd8`** (`windows_installer_productcode_vendor_registered`), MSI ProductCode for iVMS-4200 Multilingual Wizard sub-package, surfaced from `\{CE2F96D0-...}` registry context. Confidence 85 per the 75-90 sub-band ladder. §4.4 posture: **DROPPED**.

All 4 promoted identifiers carry single-source-at-promotion provenance (no §8.3 lift triggers fire, Cohort D's only independent vendor 2 was Skydio, which is P11 CLEAN NEGATIVE / documented_absence; no cross-vendor independent-source overlap to test). Per §11 #8, confidence stays at the §8.2 sub-band's empirical anchor; no drift.

### Documented absences, Cohort A + Skydio Cohort D

Session 1's Cohort A descope yielded **6 documented_absence rows** (Verkada Command, Genetec Citilog, Avigilon ACC Client, Axis Camera Station, Milestone XProtect, Honeywell Pro-Watch) anchored on the empirical observation that these vendors' "operator" client class has structurally dissolved into web/mobile distribution in 2026. Session 2 §3 added **1 Cohort D documented_absence row** (Skydio Pilot, P11 CLEAN NEGATIVE; Skydio's distribution is mobile + hardware-controller + cloud only; no desktop application). All 7 documented_absence rows are staged at `extraction_outputs/wave_h_pre_v1/per_vendor/_cohort_a_documented_absence.json` and `.../skydio_pilot_documented_absence.json`; they land in the appropriate canonical-state surface per current schema convention (the `documented_absence` first-class-table promotion remains held below the §3 #6 ≥30 cumulative-wave threshold per the CP27 surfacing).

### New data source

One source joined Argus in this release, bringing the source count from 52 to 53:

- **Vendor Desktop Application Static Analysis** (sid=53, `source_type='manufacturer_app'`, tier 1), the methodology covers publicly-downloadable vendor desktop applications across Windows / macOS / Linux. Admitted under the existing mobile-axis `manufacturer_app` enum per CP15 source-type ceiling (the proposed `vendor_application_static_analysis` enum value is CP28(a) DEFERRED per CEO disposition, the operational band-distinction is encoded via the §8.2 sub-band ladder + `notes.session_admission='wave_h_pre_v1'`). License posture: `per_vendor` + `upstream_license_posture='no_license_declared_facts_only'` defaults per CP21. Session 1 + 2 EULA disposition counts: category_a 0, category_b 0, category_c 3, category_d 0 (Hikvision iVMS-4200 download-agreement modal + DJI EULA + FileZilla GPLv2 all §3.6 (c) include).

### Bible amendment, Correction Pass 28 (CP28(c) identifier_type cluster + CP28(a)/(b) deferrals + SAR-12 7-FP-class codification + wrapper §-fragment)

This release's three CP28 candidate flags ratified as **`Correction Pass 28`**:

- **CP28(c)**, three new `identifier_type` CHECK enum values: `windows_installer_productcode_vendor_registered`, `windows_com_clsid_vendor_registered`, `vendor_document_uuid_cloud_reference`. §8.2 sub-band ladder 75-90 / 75-90 / 80-95; §4.4 posture DROPPED / DROPPED / MAP respectively. Schema landed via migration 0023.
- **CP28(a)** `vendor_application_static_analysis` source_type enum, **DEFERRED** per CEO disposition; band-distinction encoded via §8.2 sub-band ladder + `notes.session_admission`. Re-fire candidate post-desktop-continuation + next-cycle close.
- **CP28(b)** `sanctioned_vendor_public_distribution_facts_only` license-posture sentinel, **DEFERRED** per CEO disposition; empirical anchor weakened post-CP26 §8 audit. Re-fire candidate post-Cohort-F completion as CP-of-its-own (currently Dahua + Uniview acquisition blocked at Cloudflare).
- **Wrapper §-fragment**, ±90-char per-match windowed clipping discipline at the candidate-walk layer codified for next-runguide-template fold-in. Whole-line-with-overflow_dropped behavior deprecated for candidate-walk extraction.
- **SAR-12 7-FP-class roster codification**, the wrapper's final 7-class roster (listed above in the methodology section) is canonized for cross-wave consumption (source-of-truth remains the wrapper).

CP28 lands as the bible-amendment sibling of migration 0023 in the MAC-181 v1.3.0 release sweep cycle. CP-anchor: migration commit `2795ebba7866ad164121668321e213308aa87936` + [MAC-181](/MAC/issues/MAC-181) child issue ID. Bible HEAD bumps from the CP27 commit to the CP28 commit landed alongside this entry. Ratification surface: [MAC-177 disposition `comment-0d15de7b`](/MAC/issues/MAC-177#comment-0d15de7b-25a9-4f1e-bb40-65f00bc30fce) §7 "approve full path".

### Schema changes

One new migration landed this release (schema version 22 → 23):

- **0023, `identifier_type` CHECK enum extension CP28.** Pure additive enum extension (48 → 51 values) using the SQLite table-rebuild pattern from 0009 / 0011 / 0013 / 0014 / 0018 / 0019. Cumulative-CHECK discipline carries forward all 48 prior values verbatim + adds the 3 net-new CP28(c) values. PRAGMA integrity_check + quick_check both ok at apply time; 22,549 active rows preserved via INSERT SELECT *.

### Tracked follow-ons (post-v1.3.0)

- **Cohort F post-CP28 re-fire** (Dahua + Uniview; option 2 per [MAC-177 disposition](/MAC/issues/MAC-177#comment-0d15de7b-25a9-4f1e-bb40-65f00bc30fce) §5), queued as a separate child issue.
- **Next-cycle scope discussion**, hostname corpus → web SPA → iOS ranking ratified; separate child issue after v1.3.0 ships.
- **CP28(b) sentinel re-anchor** at Cohort F completion as CP-of-its-own.
- **CP28(a) re-fire** if Lynceus operationally requests filterable `vendor_application_static_analysis` source_type class post-next-cycle.

## [v1.2.0], 2026-05-18

### What's new in v1.2.0

Argus v1.2.0 lands the cycle-7 autonomous-overnight-wave integration. The wave brought **two new authoritative data sources** for the US FCC equipment-authorization ecosystem (fccid.io as a community aggregator + the official FCC EAS Filings UI as a distinct primary-registry source), **671 FCC ID discovery rows** staged under a new dual-citation-pair convention (the citation half awaits a separate async re-citation pass when FCC.gov egress is restored), and **16 net-new identifiers** from a static-analysis pass against four LE-adjacency vendor companion apps (Hikvision Hik-Connect, Dahua DMSS, Motorola WAVE PTT, Parrot FreeFlight 6). We also admitted **fourteen new manufacturer rows**, four for vendors whose identifiers we positively extracted (Hikvision, Dahua, Autel Robotics, Cisco Meraki) and ten stub rows for vendors whose identity we confirmed via absence-investigation (Verkada, Honeywell, Lenel, BluePoint Alert, PIPS Technology, Wolfcom, Utility Inc, Coban Technologies, Digital Ally, Aerodome).

Alongside the data lands, the wave produced a **bible amendment codifying empirical-premise verification as a runguide precondition**, five separate web-scrape runguides (MAC-102 ISED, MAC-103 BT SIG, MAC-105 USPTO Patents, MAC-107 GitHub Code Search, MAC-110 Ofcom) plus one internal extraction pass (MAC-101 PC1.7's `application_id`-vs-`grant_id` discovery) all surfaced load-bearing-premise failures during the same 8-hour autonomous window. The amendment introduces a new `§2.4 Empirical-Premise Verification Precondition` requiring runguides to ship a `§3.0` verification-probe section that completes CLEAN before any `§3.1` bulk dispatch fires. **The amendment landed in a follow-on commit as `Correction Pass 27`** after CEO + operator ratification on the [MAC-178](/MAC/issues/MAC-178) issue thread.

The headline outcomes for downstream consumers: **22,549 active identifiers** (up from 22,533, +16 from the MAC-104 companion-app promotion), **52 sources** (up from 50; +1 crowdsourced fccid.io + 1 regulatory FCC EAS Filings), **49 manufacturers** in the canonical vendor lexicon (up from 35), **133,825 raw_observations** rows (up from 133,134), and a schema bumped from version 21 to **version 22** via one forward-only migration (the new `fcc_citation_deferred_queue` staging table for the dual-citation pair pattern).

### New data sources

Two sources joined Argus in this release, bringing the source count from 50 to 52:

- **fccid.io** (sid=51, `crowdsourced` tier 2), a third-party aggregator of US FCC Equipment Authorization System filings. fccid.io mirrors the FCC's public filings catalog with a more navigable surface than the official `apps.fcc.gov` UI, but the upstream license is `NO_LICENSE_DECLARED`, Argus extracts facts under the Feist v. Rural Telephone facts-not-copyrightable doctrine, not via license inheritance. Compilation arrangement is not republished. This source feeds the new dual-citation-pair pattern (see below).

- **FCC Equipment Authorization System, Filings** (sid=52, `regulatory` tier 1), the official FCC EAS Filings UI at `apps.fcc.gov/oetcf/eas/reports/GenericSearch.cfm`. Distinct from the existing FCC EAS grantee-registration data file (source 7); the Filings UI gives per-FCC-ID filing surfaces (test reports, internal photos, RF exposure data) that the grantee CSV doesn't expose. **The source was admitted under a degraded-mode posture**: at extraction time FCC.gov egress was unreachable from the runtime host (Akamai-edge HTTP/2 INTERNAL_ERROR across `apps.fcc.gov`), so the 671 fccid.io discovery rows were staged with their FCC citation half deferred to an asynchronous re-citation pass. The source exists; the citation rows accumulate when egress is restored.

### Dual-citation deferred queue (new staging convention)

The cycle-7 wave introduces a **dual-citation pair pattern** for sources where the discovery surface (an aggregator) is distinct from the primary surface (the regulator). Each FCC ID observed at fccid.io carries a `notes.dual_citation_pair_id` field pointing to a row in the new `fcc_citation_deferred_queue` table. The queue row holds the discovery anchor (`fccid_io_source_url` + SHA-256 of the served HTML) and an opportunistic enrichment field (`fcc_grant_ids[]`, 564 of 671 queue rows carry these, extracted from the fccid.io page's grant-bold-content block; this lets a future async re-citation pass shortcut FCC.gov navigation from 5-step lookup to 1-step). When FCC.gov egress is restored, the validator's async re-citation pass drains the queue and emits paired regulatory-band citation rows. Until then, the discovery rows stay at the `crowdsourced` 50-75 confidence band; no confidence drift on the discovery anchor alone.

### MAC-104 companion-app net-new identifiers

The wave ran a static-analysis extraction pass against four LE-adjacency vendor companion apps (downloaded from apk-pure; decompiled with jadx + apktool; structured field extractions only, no decompiled source ever enters the DB per §11 #15). Net-new identifier yield:

- **Hikvision Hik-Connect** (`com.hikvision.hikconnect`), 1 BLE service UUID + 2 BLE characteristics, all anchored in the app's `HcpBluetoothServer` class. The Hik-Connect app is operator-cohort (cloud VMS / video doorbell), but the BLE pairing code path is installer-quality, vendor-named classes, paired `BluetoothGattService.equals(...)` / `getCharacteristic(...)` confirmations across multiple files.
- **Dahua DMSS** (`com.mm.android.DMSS`), 1 BLE service UUID + 1 BLE characteristic, paired in obfuscated class `sources/en/f.java`. Dahua DMSS substituted for the legacy `com.mm.android.direct.gdmsphone` (gDMSS Plus) which is documented-absent on both apk-pure and apk-mirror.
- **Motorola WAVE PTT** (`com.motorolasolutions.wave`), 2 BLE service UUIDs (one custom 128-bit, one 16-bit SIG-template) + 2 BLE characteristics, all anchored in `BluetoothLowEnergyPttValues` for the Milicom PTT Button accessory.
- **Parrot FreeFlight 6** (`com.parrot.freeflight6`), 1 BT SIG company-ID (67 / 0x0043 = Parrot SA) + 4 ASD-STAN drone-RID enums (`FR_30_OCTETS`, `ANSI_CTA_2063`, `FRENCH`, `EN4709_002`) + 1 ARSDK DRI feature class ID (41984 / 0xA400) + 1 ARSDK DRI command UID set. All anchored in `com/parrot/drone/sdkcore/arsdk/ArsdkFeatureDri.java`, clear-text Java, 262 lines; Parrot is the canonical drone vendor for which the entire ARSDK protocol + Drone-RID code path surfaces under Java decompilation.

All 16 promoted identifiers carry `confidence ∈ {75, 85, 87}` per CP17 manufacturer_app sub-banding (installer-cohort 80-95 → 87; CP14 drone-RID class hits → 85; 16-bit SIG-template lower anchor → 75). All single-source at promotion (`notes.single_source_at_promotion=true`); no §5.6 cross-source uplift applied (verified: no pre-existing rows match any candidate identifier).

**Four additional candidates held for SAR-12 schema-extension review:**
- 2 default credentials (`lc2014` LeChange SDK default password, `terminal` DMSS OAuth client_secret), no `default_credential` enum slot at v22 schema
- 1 vendor namespace UUID (Parrot Skyward UTM `0045b822-...`), handoff explicitly flags as NOT-a-BLE-service-UUID; no clean enum fit
- 1 DJI RTK serial-number template (`1APDF7Q0010001` from DJI Pilot NRTK setup default), handoff explicitly not-promoted-flagged; no `serial_number_template` enum slot

Each held row stages in `raw_observations` with `notes.hold_reason` + `notes.validator_review_recommendation`.

### Manufacturer enrichments

Fourteen new manufacturer rows joined the canonical lexicon (from 35 to 49):

- **Hikvision** (id=209) and **Dahua** (id=208), both admitted with NDAA Section 889 note (state/local LE deployments persist outside the federal-procurement bar; runguide §0 scope).
- **Autel Robotics** (id=206, primary_category=drone) and **Cisco Meraki** (id=207), positive-extraction admissions from MAC-104b/d.
- **Stub admissions** (10 vendors, primary_category set where the vendor's product line is unambiguous): Verkada, Honeywell, Lenel, BluePoint Alert, PIPS Technology, Wolfcom, Utility Inc, Coban Technologies, Digital Ally, Aerodome. Each carries `notes.admission_basis='documented_absence_only'`, the manufacturer identity was verified via absence-investigation (apk-pure 404 + apk-mirror "no results" + cohort-prediction reasoning) but no positive identifier extraction this wave.

**34 product-family taxonomy entries** added to seven manufacturers' `notes.product_family_taxonomy[]` arrays (additive; cross-APK observations of the same string are corroborating mentions and get separate entries, e.g. DJI "Mavic" appears once for DJI Fly + once for DJI Pilot = 2 entries, 1 distinct value). Distinct values: DJI (10), Hikvision (5), Motorola Solutions (4), Dahua (4), Parrot (3), Autel Robotics (2), Cisco Meraki (1).

**22 `documented_absence` JSON entries** applied to `manufacturers.notes.documented_absence[]` across 21 distinct vendor rows (DJI gets two entries: legacy `com.dji.go` + standalone `com.dji.mavicmini` folded into DJI Fly). Each entry carries `investigation_date_utc`, `investigation_dispatch_ref`, `channels_probed`, `outcome=categorical_absent`, `rationale` (one of `LE_only_distribution` / `federal_enterprise_managed` / `vendor_direct_NDA` / `controlled_distribution`), and the staging vendor_canonical for alias-trace continuity. Distribution: LE-only-distribution 9, federal-enterprise-managed 9, vendor-direct-NDA 3, controlled-distribution 1 (DroneShield RfPatrol, C-UAS / ITAR-adjacent; flagged for operator legal review before alt-channel pursuit).

### SAR-11 FP-class registry additions

Nineteen new SAR-11 FP-class proposals were baked into the canonical `proposed_fp_classes.json` registry per CEO §3 #5 ratification: **14 clean bulk-adds** (Docker/Jenkins build-host UUIDs, APK test fixtures, Motorola WAVE license GUID, Microsoft AppCenter / PDFBox / RN-Keychain library labels, NASA WorldWind constants, Autel password regex templates, Apache HttpClient context keys, RxJava build-host UUIDs, AndroidAnnotations cacerts default, XML layout TextView labels, Adobe XMP image metadata UUIDs) + **5 selective adds with `operator_review_note: "Hikvision/Dahua/drone-cohort overlap; flagged at MAC-104 cycle-7"`** (Alibaba Taobao security cipher key, Microsoft XML namespace UUID, Hikvision HTML doc-routing GUID, AMap location-SDK placeholder MACs, DJI api_debug.txt key). Each edge entry carries explicit `overlap_risk` prose so v3 extractor calibration applies exact-value-match-only, not generalization.

### Bible amendment, Correction Pass 27 (`§2.4` Empirical-Premise Verification Precondition)

The wave's six concrete failure-mode anchors (5 external runguides + 1 internal extraction pass) ratified as **`Correction Pass 27`, `§2.4 Empirical-Premise Verification Precondition`**: a new bible subsection requiring every runguide to ship a `§3.0` verification-probe section that completes CLEAN POSITIVE or CLEAN NEGATIVE before any `§3.1` bulk dispatch fires. INCONCLUSIVE outcomes halt the runguide; CEO disposition is required for any re-fire. The amendment also defines retroactive binding rules for runguides drafted-but-not-dispatched and runguides being re-dispatched.

CP27 landed as a single follow-on commit covering the `BIBLE_AMENDMENTS.md` CP27 entry, the `§2.4` insert into `PROJECT_BIBLE.md` (placed after `§2.3 A Note on Ambition`; before `§3 Architecture`), and this CHANGELOG flip. Schema version unchanged (CP27 is `§`-text only, no migration, no notes_json convention, no code-path sibling). Downstream-consumer audit: 10 runguides identified for retroactive `§3.0` adoption (8 "Must" cases enforced naturally at each runguide's next dispatch-firing gate per `§2.4`'s halt-before-fire contract; 2 "Should" cases fire lazily next time the completed runguides are touched). No separate tracking issue created, the discipline is structurally self-enforcing. Ratification surface: [MAC-178 disposition](/MAC/issues/MAC-178#comment-3029e567-c4e7-4dac-aff8-cd03b8c9a48a) (response to Validator draft [60301e62](/MAC/issues/MAC-178#comment-60301e62-da2e-4007-b975-b40caaf2c923)).

### Schema changes

One new migration landed this release (schema version 21 → 22):

- **0022, `fcc_citation_deferred_queue` staging table.** New table holds the discovery-row half of the dual-citation pair pattern (one row per FCC ID; `fcc_id` UNIQUE; `promoted_at NULL` = pending drain by the validator's async re-citation pass; index on `(promoted_at)` partial WHERE NULL for drain queries; index on `fcc_grant_ids_csv` for grant-ID-shortcut lookup). 671 rows seeded from the MAC-101 partial-deliverable wave.

### Conventions

- **Staging-JSON-vs-schema-column naming convention codified** (2026-05-17, patch cycle 1.6.C): staging JSON shapes emitted under `extraction_outputs/{runguide_slug}/` use `candidate_value` for human readability during validator review; the promoted `raw_observations` schema column is `candidate_identifier`. Validator handles the rename at promotion (one-to-one, no transformation). Documented in patch cycle 1 against the source-admission wave (10 runguides, MAC-101 through MAC-110). The patch cycle 2 wave (PC2.A through PC2.D) did not surface rename-at-promotion error pressure; the convention holds as written.

### Refreshed exports

All four canonical exports were regenerated against the post-cycle-7 active set:

| Export | Pre-cycle-7 | Post-cycle-7 | Delta |
|---|---|---|---|
| `argus_export.csv` (rich-import, all canonical rows) | 22,533 | **22,549** | +16 |
| `argus_export.json` (Lynceus, ≥30 confidence + §4.4 mapping) | 494 | 494 | +0 |
| `argus_export_high_confidence.json` (Lynceus, ≥70 + non-{crowdsourced, inferred}) | 113 | 113 | +0 |
| `argus_export_behavioral_signatures.json` (Rayhunter; unchanged this wave) | 55 | 55 | unchanged |

**Note on the JSON-export +0 delta:** the 16 MAC-104-promoted identifier_types (`ble_service_uuid`, `ble_characteristic`, `ble_company_id`, `asdstan_enum_value`, `device_class_id`, `rf_protocol_constant`) are all `§4.4 DROPPED-class` per CP16 / CP19 (mig-0018 cluster) / MAC-117 (mig-0019 round-2). Per the bible, DROPPED-class identifier_types are carried in the canonical DB (and the CSV rich-import feed) but NOT in the Lynceus pattern-table JSON exports, by design. The brief author's forecast of +20 standard-export rows + +6 to +14 high-confidence rows didn't account for this disposition. Whether to MAP some/all of these types into Lynceus is a separate `§4.4` amendment surface for a future CP cycle.

Also new: `exports/_export_manifest.json` ships the per-file size + SHA-256 + entry-count manifest with a delta-vs-forecast block, generation timestamp, and the §4.4 reasoning surfaced for downstream consumers.

### Post-CP27 runguide migrations (Patch Cycle 2)

Following the CP27 ratification, four web-scrape runguides identified at the CP27 §2.4 audit were migrated through Patch Cycle 2 (PC2.A through PC2.D) as in-repo summary commits accompanying out-of-tree runguide-file edits. All four are docs/runguide-internal only, no sources, identifiers, manufacturers, raw_observations, schema, or license posture changed. Each landed a `§3.0` empirical-premise verification block (CP27 §2.4 compliance) alongside the upstream-surface migration:

- **PC2.A, MAC-105 USPTO Patent Public Search migration** (`348f514`), legacy `patft.uspto.gov` decommissioned; runguide migrated to `ppubs.uspto.gov/pubwebapp/` + the authenticated `data.uspto.gov/api/manage` ODP endpoint (`USPTO_ODP_API_KEY` env-var convention). 4-probe `§3.0` verification block (Google Patents + PPubs JS-shell + USPTO ODP authenticated + Espacenet rate-block detection).
- **PC2.B, MAC-107 GitHub Code Search auth-required correction** (`fa967b1`), runguide corrected to reflect mandatory authentication for all `/search/*` queries since GitHub's 2022 GA change; rate limit clarified as 30 req/min on `/search/*`; 4-row SQL column-drift fix (`identifier_value → identifier`, `manufacturer_canonical_name → manufacturer`); 4-probe `§3.0` verification block with PAT scope sanity + account-identity capture for §11 #3 audit-log provenance.
- **PC2.C, MAC-102 ISED REL Spring Web Flow migration** (`164ceb2`), legacy `apc-cap.ic.gc.ca` Oracle PL/SQL endpoint decommissioned; runguide migrated to `sms-sgs.ic.gc.ca/equipmentSearch/searchRadioEquipments` Spring Web Flow surface; per-row + bulk-data URL templates deferred to v2 runguide (continuation-token discovery + POST-flow advance not yet captured); 4-probe `§3.0` verification block. OGL-Canada-2.0 license posture unchanged.
- **PC2.D, MAC-103 BT SIG Qualified Designs narrow-to-shallow** (`d66f986`), runguide narrowed from full companion-app linkage to shallow-surface QDID capture (`QDID + product_name + owner_company + reference_QDID`); cross-source linkage to `ble_manufacturer_id` preserved; Cloudflare WAF UA-shape rejection documented (browser-shape UA required; `argus-research/*` UA rejected); public POST search at `qualificationapi.bluetooth.com/api/Platform/Listings/Search`; SIG member gate noted for deeper surfaces.

The four-instance pattern (PC2.A through PC2.D, covering decommission / host-migration / auth-gating / Cloudflare-WAF failure modes) is documented at `extraction_outputs/_patch_cycle_2/pc2_d_summary.md` as empirical evidence supporting CP27 §2.4's halt-before-fire contract.

## [v1.1.0], 2026-05-17

### What's new in v1.1.0

Argus v1.1.0 broadens the project beyond pure equipment-identifier registries and into the corporate, judicial, and procurement records that anchor surveillance vendors to real-world entities. We added **seven new authoritative data sources** (taking the project from 43 sources to 50), **expanded our federal procurement coverage** by 2,560 net-new contract records, and **closed our first held entity**, Johnson Matthey PLC, by cross-checking it against the UK's official corporate registry.

Along the way we found and fixed seven small inconsistencies between our documentation and the actual database schema. These are codified in the amendment ledger so the next round of contributors doesn't trip over the same edges. We also introduced two new operating conventions: an explicit `access_mode` tag for sources we can't auto-scrape in one session (CAPTCHA-walled state corporate registries, paid-tier government databases), and a `cycle_completion_state` tag for sources that take multiple days to fully ingest. Both are described in plain language below.

The headline outcomes for downstream consumers: **22,533 active identifiers** (up from 22,532), **46,043 procurement records** (up from 43,483), **35 manufacturers** in the canonical vendor lexicon (Johnson Matthey is new), and a schema bumped from version 19 to **version 21** via two forward-only migrations.

### New data sources

Seven sources joined Argus in this release, bringing the source count from 43 to 50:

- **UK Companies House** (sid=44), the United Kingdom's official corporate registry, released under the Open Government Licence v3.0. We use it to confirm the corporate identity of UK-incorporated surveillance vendors against a primary government record. **This source enabled our first Class B hold closure: Johnson Matthey PLC (UK company #00033774), a London-headquartered chemistry and precious-metals firm**, was confirmed via Companies House cross-check and admitted to the canonical 35-entry manufacturer lexicon. Access is fully automated via the Companies House API.

- **Delaware Division of Corporations** (sid=45), Delaware is the registration state of record for a disproportionate share of US technology companies, so the Delaware corporate registry is a high-leverage source for vendor verification. The state's NameSearch web form is CAPTCHA-gated, so this source is recorded under the new `operator_manual_only` access convention: lookups happen via human-operated browser sessions rather than scripts.

- **California Secretary of State, Bizfile** (sid=46), California's corporate registry, the second-most-relevant US state for surveillance vendor lookups after Delaware. The Bizfile portal is gated by an Incapsula bot-challenge wall, so this is also an `operator_manual_only` source.

- **Texas Secretary of State SOSDirect** (sid=47), the Texas corporate registry. Useful for Texas-headquartered surveillance vendors. Access requires paid-tier authentication, so this is again `operator_manual_only`.

- **CourtListener / RECAP (Free Law Project)** (sid=48), a free, comprehensive judicial filings database covering US federal and state courts. CourtListener surfaces lawsuits, contract disputes, and federal court records that name surveillance vendors as parties. Metadata is dedicated to the public domain under CC0; full-text search requires an authenticated Bearer token.

- **SEC EDGAR** (sid=49), the US Securities and Exchange Commission's corporate-disclosure filings database. Public companies routinely name their major customers in 10-K annual reports and Item 1A risk-factor narratives; for surveillance vendors that file with the SEC, this lets us corroborate vendor-customer relationships against a primary public-domain regulatory source. EDGAR is automated via HTML parsing.

- **SAM.gov Entity Registration** (sid=50), the US federal procurement contractor-registration database. SAM.gov is the authoritative source for "is this vendor an active US federal contractor and what are their registered NAICS codes?", exactly the question that determines whether procurement evidence is admissible. Access is automated via the SAM.gov API. This source is recorded under the new `partial_pre_day1` cycle-completion convention because we hit the SAM.gov non-Federal-individual-account daily rate ceiling (~10 requests/day) before the first full sweep finished. Remaining queries continue across subsequent days; the source row was admitted at first-batch completion.

### Expanded federal procurement coverage

Federal procurement records grew by **2,560 net-new entries** (from 43,483 to 46,043) via a deep-extension pass against USAspending.gov, the canonical federal contract-award database. This nearly closes the previously-known gap between Argus's surveillance-vendor coverage and USAspending's actual surface area for those vendors.

Alongside the new rows, we landed **9,623 cross-source corroborations** from the SAM.gov ingestion cycle. **A corroboration here means: a fact we already had (a vendor's federal contract record) is now independently confirmed against a second, structurally different source (SAM.gov's contractor registration database).** When two independent sources agree on a fact, our confidence in that fact increases, and the corroboration is recorded in a per-row audit trail so downstream consumers can see the evidence chain.

Note for downstream consumers: alongside the +2,560 net-new procurement records, we **rolled 180 procurement_record confidence values back from 90 to 85**. These rows had been corroborated by a second pass against USAspending itself, but that's the same source observed twice, not two independent sources, so the confidence boost wasn't earned. The full audit trail is preserved per row in `notes.confidence_history[]`. This is exactly the kind of self-correction the audit trail is designed to surface.

### Schema changes

Two new migrations landed this release (schema version 19 → 21):

- **Migration 0020 (`source_type_enum_extension`)**, extends the `sources.source_type` enum with three new values (`judicial_filing`, `disclosure_filing`, `procurement_disclosure`) to properly classify the new judicial, SEC, and SAM.gov sources. Previously these would have fallen back silently to the generic `regulatory` bucket; now each source class has its own named tier.

- **Migration 0021 (`procurement_vendor_canonical_normalized`)**, adds a new `procurement_records.vendor_canonical_normalized` column. This is a deterministic, query-friendly normalization of each procurement record's vendor name: lowercased, punctuation stripped, corporate suffixes (`INC`, `CORP`, `LLC`, `LTD`, `PLC`) removed. For example, `'AXON ENTERPRISE, INC.'`, `'Axon Enterprise, Inc.'`, and `'AXON ENT INC'` now all collapse to `axon enterprise`, making cross-validation joins against the manufacturer lexicon dramatically more reliable. The column was backfilled across all 46,043 procurement records.

**What this means for downstream consumers:** check `MAX(version) FROM schema_version` at runtime; it should now read 21. If you query the `sources` table by `source_type`, you may now see three additional enum values. If you join against `procurement_records.vendor_canonical_name`, prefer the new `vendor_canonical_normalized` column instead, same data, dramatically better join semantics across 46k rows.

### New discipline conventions

Two new operating conventions were introduced. Both live in the `sources.notes` JSON field today and are described below in user terms; they may be promoted to first-class schema columns in a future release once the vocabulary stabilizes.

- **`access_mode`**, describes how Argus fetches a given source. Values: `automated_api` (queried via documented API), `automated_html_parse` (scraped from HTML without an anti-bot wall), `automated_with_auth` (automated but requires a token), `mixed_automated_manual` (some candidates automated, some manual), and `operator_manual_only` (all access is via a human-operated browser session, because the source is CAPTCHA-walled, bot-challenged, or otherwise structurally hostile to automation). **Important: the access mode is a mechanism descriptor, not a quality signal.** Operator-manual sources carry identical confidence bands and provenance discipline to automated sources. The four state-registry sources added this release (DE / CA / TX) and three secondary state holds are flagged `operator_manual_only`.

- **`cycle_completion_state`**, describes whether a source's data has been fully ingested or whether ingestion is paced across multiple days. Values: absent (source is complete; default reading), `partial_pre_day1` (admission landed before the first sweep finished), `partial_pacing_in_flight` (multi-day pacing run still active), `partial_pacing_exhausted` (multi-day pacing terminated short of completion). When this field is set, the source row also carries `next_cycle_dispatch_scheduled_for_utc`, `next_cycle_dispatch_runguide_path`, and `partial_yield_metrics_at_admission` so downstream consumers can see exactly where the partial state sits and when the next cycle is scheduled. **SAM.gov (sid=50) is the first consumer**, recorded as `partial_pre_day1`.

### Known limitations + what's coming

Argus's coverage is still **intentionally narrow at this baseline**, broader categories of surveillance equipment remain out of scope. The roadmap below frames what's queued.

**Currently held items:**

- **11 US state Secretary-of-State corporate holds** remain queued for operator-manual review against the DE / CA / TX registries.
- **Approximately 22 international corporate holds** remain queued. Bounded paths to closure are documented per jurisdiction.
- **3 operator-review items** surfaced from the SAM.gov ingestion cycle: a Vigilant Solutions inactive-registration probe, a Flock Safety brittle-alias normalization disagreement (Flock Safety vs "Funny Flock Farms LLC"), and a Motorola multi-entity disambiguation probe. All three are staged to the operator-review queue with full audit context.

**Carry-forward from v1.0.0:** the previously-documented v1.0.0 held items (31 behavioral_signatures pending second-source corroboration, 62 Class B sustained holds, 133 IEEE Private permanent holds, 142 round-2 vocabulary candidates) remain held under the same rationale, less the one Johnson Matthey closure this release. The v1.0.0 documented sources-row metadata discrepancy on sources 1/2/3/7 is unchanged.

**Note: a small number of `identifiers.notes` rows contain malformed JSON; downstream consumers using `json_extract()` against this column should fall back to JSON-text-LIKE patterns. Tracked for future fix.**

**Coming next:**

- Continued multi-day SAM.gov ingestion (cycle-6 dispatch scheduled).
- Continued operator-manual review against state corporate registries to close the 11 remaining US state holds and ~22 international holds.
- Additional community-source-acquisition waves, deferred from v1.0.0.
- iOS vendor companion-app coverage, deferred from v1.0.0.
- Skydio Enterprise alt-channel scope, deferred from v1.0.0.

### Internal architecture notes

This section preserves the discipline-architecture audit trail for the v1.1.0 release in the project's canonical idiom. The narrative is the body above; the ledger below is the binding contract.

**Bible amendment ledger (this release):**

- **CP23** @ bible HEAD ratification, coordinated amendment: wide-net cycle-{1,3,4} schema-contract patches + migrations 0020 + 0021 + downstream-consumer audit. Folds seven schema-contract drift findings (PROJECT_BIBLE.md §4.2 / §4.3 / §8.2 / §8.3 §-text additions; `manufacturers.aliases` comma-string clarification; source_excerpt per-table CHECK constraint cap table; `notes.access_mode` notes_json convention; license-into-notes folding contract; cross-validation column-name normalizations) and the two migrations into a single bible commit per the §11 #11 amendment-log discipline. Source patches: `new data 5.16/schema_contract_patch_cycle3.md`, `new data 5.16/schema_contract_patch_cycle4.md`, `new data 5.16/schema_contract_patch_notes_license.md`.
- **CP24** @ bible HEAD, §11 #8 within-source-re-extraction sub-rule + CP19 spirit-extension to `procurement_records` row-level audit-trail (`notes.confidence_history[]` convention) + "§5.2 +5 boost" citation hygiene correction. Within-source re-extraction (same upstream registry queried at two times by the same or different extraction sessions) is **not** a "second independent source" for §8.3 lift purposes. Provenance enrichment via `notes.corroborations[]` + `notes.corroboration_sessions[]` stays; confidence does not lift. The 180-row MAC-172 P4 USAspending deep-extension lift rollback (85 → 90 → 85) is the first consumer with full per-row audit-trail.
- **CP25** @ bible HEAD `2803ae1`, `cross_source_corroboration_reversals[]` audit-trail convention + CP24 §12 `n` recount supersession (SEC EDGAR × USAspending drops 2 → 0 after §11 #1 semantic review of MAC-171 P3 RG5 findings) + within-source-FP discipline-evolution carry-forward. First consumer is the MAC-171 id=86738 reversal UPDATE.
- **CP26** @ bible HEAD `64f381c`, SAM.gov cycle-5 day-0 partial fold (seven runguide-correction findings: probe-template UEI freshness, empirical rate ceiling, no-proactive-rate-limit-headers extraction discipline, operator-manual-queue file-format clarification, NAICS code revision drift, single-token alias fanout brittleness, snapshot-freshness pre-flight) + `cycle_completion_state` notes_json convention codification + within-source-FP discipline n=4 codification (text-pattern match + semantic-relationship validation as a default §4 match-scoring step). Source patch: `extraction_outputs/sam_gov_admission/STOP_THE_LINE_rate_ceiling.md`.

**Migration ledger entries (cumulative 1 → 21):**

- **0020 `source_type_enum_extension`** (applied 2026-05-17 05:07:17), `sources.source_type` CHECK enum 10 → 13 values: net-new `judicial_filing`, `disclosure_filing`, `procurement_disclosure`. Per CP23 / cycle-3 §1 finding #2. Table-rebuild per the 0009 / 0015 / 0018 / 0019 precedent. The 3 new bands are sources-tier taxonomy only; identifier-row promotion-pipeline confidence bands (§8.2) are unchanged.
- **0021 `procurement_vendor_canonical_normalized`** (applied 2026-05-17 05:07:32), `procurement_records.vendor_canonical_normalized TEXT NOT NULL DEFAULT ''` column + supporting B-tree index. Per CP23 / cycle-3 §1 finding #4 + CEO Path B ruling. Backfill populated all 46,043 rows; collapse ratio 0.9862 (1,157 distinct raw vendor_canonical_name values collapse to 1,141 distinct normalized values). Normalization algorithm canonical reference: `db/normalize_vendor.py::normalize_vendor_name` (pure function).

**MAC issue dispatch references:**

- **MAC-101**, baseline aggregate state (v1.0.0 reference).
- **MAC-168**, paperclip integration of CP23 (wide-net cycle-{1,3,4} schema-contract patches).
- **MAC-169 through MAC-174**, admission cycle dispatches (UK Companies House P2; SEC EDGAR P3; USAspending deep-extension P4; state SoS P5; CourtListener V4 P6).
- **MAC-172**, USAspending deep-extension P4 ingest (+2,560 net-new procurement_records; partial-ratify rollback of the 180-row lift; CP24 codification).
- **MAC-175**, SAM.gov cycle-5 admission close (sid=50 INSERT + 9,623-row cross-source corroboration UPDATE batch: Vigilant 56 + Motorola 9,545 + Genetec 22; CP26 codification).

**Source-tier license-posture vocabulary additions (CP23):**

- `OGL-3.0`, UK Companies House (sid=44).
- `PUBLIC_DOMAIN`, SEC EDGAR (sid=49), SAM.gov (sid=50).
- `US_STATE_PUBLIC_RECORDS`, Delaware / California / Texas SoS (sid=45 / 46 / 47).
- `CC0`, CourtListener / Free Law Project (sid=48).

All four compose with the pre-existing CP21 `notes.upstream_license_posture` canonical sentinel-key for per-row license-aware downstream consumer filtering. License lives inside `notes_json.license` (the contract refers to this as `notes_json`; the underlying column is `sources.notes` TEXT containing JSON), NOT as a top-level column, codified per the cycle-1 patch finding #1.

**Live-state verification (paste-not-cite per S.7):**

Verified 2026-05-17 against `db/argus.db`:

```
schema_version              = 21   (0021_procurement_vendor_canonical_normalized,  2026-05-17 05:07:32)
                                   (0020_source_type_enum_extension,               2026-05-17 05:07:17)
sources                     = 50   (was 43 in v1.0.0; +7 this release)
identifiers active          = 22,533  (superseded_by IS NULL; total rows 22,613 incl. 80 superseded)
procurement_records         = 46,043  (+2,560 net-new this release)
manufacturers               = 35   (+1: Johnson Matthey PLC, UK CH #00033774)
behavioral_signatures       = 131  (unchanged)
source_reclassifications    = 809  (unchanged this MAC-175 close)
PRAGMA integrity_check      = ok
```

**Cross-source corroboration accounting (this release):**

- **9,623 cross-source corroboration UPDATEs** landed from the SAM.gov cycle-5 admission (Vigilant 56 + Motorola 9,545 + Genetec 22). All UPDATEs honor CP24 sub-rule (b)'s `notes.confidence_history[]` per-row audit-trail.
- **180 within-source-reextraction rollbacks** (90 → 85) applied per CP24 §11 #8 sub-rule #1 (the USAspending deep-extension is the same source observed at two times, not a genuinely independent collector). Full per-row audit per CP24 sub-rule (b).
- **2 RG5 cross-corroboration markers** flagged at MAC-172 P4 ingest; 1 reversed at MAC-171 P3 ratification per CP25 §1 (id=86738; SEC × USAspending pair recount drops 2 → 0). The remaining marker is deferred to operator review pending fuller filing context.

**Open §12 questions surfaced this release (queued for future CP candidacy):**

- `access_mode` first-class column migration, gated on value-set stabilization (~1-2 more cycles of new-source evidence).
- Partial-cycle source-admission discipline first-class-column promotion (`cycle_completion_state`), gated on at least 2 distinct sources using non-absent values.
- Empirical-ceiling-probe runguide template, CP26 §3 candidate.
- `procurement_reclassifications` audit table promotion, gated on forensic-query pattern emergence at scale (current row-local `notes.confidence_history[]` convention is canonical).

---
## [v1.0.0], TBD release date

### What's included

Argus v1.0.0 ships the canonical surveillance-equipment-identifier database as a queryable SQLite artifact (`db/argus.db`, schema_version=19) plus four derived dataset exports under three licenses:

- **Pipeline** (AGPL-3.0-or-later), the migration + source-loader + extraction + validator + export code that reproduces the database from upstream sources.
- **Database / dataset** (ODbL-1.0; Atlas-derived rows quarantined under CC-BY-NC-SA-4.0 per upstream NC clause; per-row LICENSE column at `deployment_observations.LICENSE` enables downstream license-aware filtering), the canonical SQLite DB + the JSON/CSV exports at `exports/`.
- **Documentation** (CC-BY-SA-4.0), README, METHODOLOGY, DATA_DICTIONARY, CREDITS, SECURITY, THREAT_MODEL, LEGAL_POSTURE, CONTRIBUTING, CODE_OF_CONDUCT, this CHANGELOG.

#### Database content

- **14 user tables** at schema_version=19 (full schema reference in [DATA_DICTIONARY.md](DATA_DICTIONARY.md)):
  - **Canonical-state**: `identifiers` (Layer 1, the main table; 22,532 active rows + 80 superseded)
  - **Provenance + source**: `raw_observations` (133,134 rows), `sources` (43 sources), `manufacturers` (34-entry surveillance-tech vendor lexicon)
  - **Layer 2 + supporting**: `deployment_observations` (116,668 rows with per-row LICENSE column per migration 0016), `procurement_records` (43,483 rows), `fcc_grantees` (50,153 rows), `council_minutes_matters` (3 rows), `wigle_anchor_priority` (80,697 rows), `behavioral_signatures` (131 rows)
  - **Audit-trail**: `source_reclassifications` (809 rows, row-level reclassification audit table)
  - **Operational**: `conflicts` (20 rows), `extraction_runs` (106 rows), `schema_version` (migration ledger 1 → 19)
- **Active identifier rows by class** (22,532 total active):
  - **IEEE-anchored mac_range / OUI** rows at `primary_registry` band: ~17,800 rows across IEEE OUI MA-L / MA-M / MA-S + IEEE IAB registries
  - **FAA Remote ID `drone_id_prefix`** rows at `primary_registry` band: 427 rows (from alphafox02/DragonSync + post-validation promotion cycle)
  - **Bluetooth SIG `ble_manufacturer_id`** rows at `primary_registry` band (per migration 0011): 3,971 rows
  - **Community-research crowdsourced** rows: ~534 rows across drone Remote ID + BLE tracker catalogs + IMSI-catcher detection + ALPR-camera profiles
  - **Vendor companion-app `manufacturer_app`** rows (Hak5 / Flock Safety FS Installer / Getac BWC Viewer via vendor-app static analysis): 21 rows
  - **Inferred / cross-validation** rows: 4 rows (vendor-disambiguation + corroboration math)
- **Provenance rows** (`raw_observations`): 133,134 rows; every active identifier traceable to at least one source citation per METHODOLOGY §7 provenance discipline.
- **Deployment-location rows** (`deployment_observations`): 116,668 rows from EFF Atlas of Surveillance (15,071 CC-BY-NC-SA-4.0) + DeFlock (101,597 ODbL-1.0) with per-row LICENSE column quarantine.
- **Behavioral signatures** (`behavioral_signatures`): 131 rows (55 Marlin NDSS 2025 IMSI-catcher signatures + 38 backfilled from community IMSI-detector research + 38 round-2 review extensions).

#### Source families integrated

- **IEEE OUI registries** (MA-L 24-bit + MA-M 28-bit + MA-S 36-bit) at `primary_registry` band, vendor-to-OUI mappings; factual public registry data.
- **IEEE IAB registry** (36-bit legacy) at `primary_registry` band, predecessor allocations.
- **FCC EAS Equipment Authorization Grantee Registrations** at `primary_registry` band, 50,153-grantee corporate registrant lookup table; allowlist for `fcc_id_anchored` disambiguation and the vendor-disambiguation predicate.
- **FAA ANSI/CTA-2063-A Remote ID prefix registry** at `primary_registry` band, drone-class identifier-to-vendor attribution.
- **Bluetooth SIG company-identifier registry** at `primary_registry` band, BLE `ble_manufacturer_id` clusters.
- **EFF Atlas of Surveillance** (CC-BY-NC-SA-4.0 quarantine; NC clause carries forward), 15,071 deployment-location observations.
- **DeFlock** (ODbL-1.0; license-compatible with compilation license), 101,597 ALPR camera deployment-location observations.
- **USAspending.gov + Granicus Legistar**, federal/state/municipal procurement records (43,483 + 3 rows respectively).
- **Wireshark `manuf` file**, community-maintained OUI cross-reference for vendor-name curation.
- **NDSS 2025 Marlin IMSI-catcher research** at `academic` band, 53 behavioral-signature rows for cellular-detection signatures.
- **Vendor companion applications** (Hak5 docs / Flock Safety FS Installer / Getac BWC Viewer) at `manufacturer_app` band, BLE service UUIDs + default credentials + product-family taxonomy extracted via static analysis under the 17 USC §1201(j) + 37 CFR §201.40(b) security-research exemption.
- **22 canonical community-research GitHub repositories** at `crowdsourced` or `manufacturer_doc` band, drone Remote ID + BLE tracker catalogs + IMSI-catcher detection + ALPR-camera + flock-detection cohorts.
- **5 secondary-batch repositories** at `crowdsourced` or `academic` band with explicit license-posture annotations (AGPL-3.0 inherited / AGPL-3.0 declared / NO_LICENSE_DECLARED under the Feist facts-only doctrine / CC-BY-NC-ND-4.0 with research-use clause).

Full per-source attribution + upstream-license chain in [CREDITS.md](CREDITS.md).

### Methodology

[METHODOLOGY.md](METHODOLOGY.md) documents the methodology behind v1.0.0:

- **§3 Sources and source-type hierarchy**, 10-value `source_type` enum (`primary_registry` / `inferred` / `manufacturer_app` / `crowdsourced` / `official` / `manufacturer_doc` / `regulatory` / `procurement` / `academic` / `foia`) with confidence bands per source-class. The `primary_registry` band covers IEEE OUI / FCC EAS / FAA RID / Bluetooth SIG registry-class allocators with a 70-85 single-source ceiling.
- **§4 Identifier types**, 48-value `identifier_type` enum across three structural categories: wire-observable (route to Lynceus-bound JSON exports), parametric / sub-protocol / forensic (DROPPED-class, analytical only, CSV export only), and alias-collapse (route to existing pattern_type).
- **§5 Confidence model**, calibrated integer 0-99 (humility-margin invariant; schema-CHECK permits 0-100 with operational cap at 99) with source-type bands, `+5` corroboration boost, lowest-contributing-ceiling rule, `primary_registry` sub-banding, and `manufacturer_app` per-class sub-banding. Discrete confidence shapes diverge for `procurement_records` (continuous 0-100, no humility margin) and `council_minutes_matters` (discrete 70/75/80 per item-grading); see DATA_DICTIONARY §6.2.
- **§6 Dedup + reclassification logic**, collapses N citations of the same identifier to a single canonical row with corroboration chain preservation; superseded-row preservation discipline (`identifiers.superseded_by` pointer chain). Row-level reclassifications (band/confidence/source_url changes) land an entry in `source_reclassifications` with `sweep_event_id` grouping + pre/post snapshot + rationale anchor.
- **§7 Provenance discipline**, `raw_observations` as source-of-truth; `source_url` must be working at ingest + verbatim-preserved post-fetch (pinned-SHA + line-anchored URL template, e.g., `/blob/<sha>/<path>#<anchor>`); no-fabrication hard rule; third-party-citation-lineage boundary; no-PII discipline; amendment-log discipline.
- **Feist facts-only promotion**, public-but-unlicensed sources (NO_LICENSE_DECLARED) qualify for facts-only extraction under *Feist v. Rural Telephone Service* (499 U.S. 340 (1991)). Argus extracts factual claims (identifier values, manufacturer attributions); Argus does NOT republish the source's compilation arrangement. Per-row canonical sentinel: `notes.upstream_license_posture='NO_LICENSE_DECLARED'`.

### License posture

- **Code:** AGPL-3.0-or-later ([LICENSE](LICENSE)), network-use copyleft preserves source-availability for derivative scanners; AGPL-3.0 inheritance-compatible with community-contributed sources at `sources.id` 38/40/43.
- **Dataset:** ODbL-1.0 ([LICENSE-DATA](LICENSE-DATA)) with three-layer per-row license-posture composition:
  - **Layer 1** `sources.notes.license_posture` (per-source declaration; 6 distinct posture classes documented in LICENSE-DATA §2.1)
  - **Layer 2** `deployment_observations.LICENSE` (per-row NOT NULL column, migration 0016; Atlas rows quarantined under CC-BY-NC-SA-4.0 NC clause; DeFlock rows under ODbL-1.0)
  - **Layer 3** `identifiers.notes.upstream_license_posture` (per-promoted-identifier canonical sentinel key)
- **Documentation:** CC-BY-SA-4.0 ([LICENSE-DOCS](LICENSE-DOCS)), ShareAlike preserves the discipline-architecture open-availability for derivative documentation.
- **DMCA / takedown posture:** project-side doctrinal grounding is Feist factual-data + 17 USC §1201(j) security-research exemption + 37 CFR §201.40(b) + nominative fair use. Vendor attribution disputes route through a GitHub issue.

### Schema versioning

The migration ledger (`schema_version` table) tracks every applied migration. v1.0.0 ships at `MAX(version)=19`. Migrations are forward-only (no rollback); schema-changing PRs land paired with the project's amendment-log discipline ([BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md)). Downstream consumers should check `schema_version` at runtime when integrating against a downloaded `argus.db`.

**Migration ledger summary (1 → 19):**

- **0001** initial schema, `identifiers` + `raw_observations` + `sources` + `manufacturers` + `extraction_runs` + `conflicts` + `schema_version` + 5 enum CHECK constraints
- **0002-0005** supporting tables, `procurement_records`, `fcc_grantees`, `council_minutes_matters`, `wigle_anchor_priority`, `deployment_observations`
- **0006** PDF/SDK/FCC-report corpus support
- **0007** vendor companion app static analysis support
- **0008-0010** identifier-type extensions (`product_family_codename`, `ble_local_name`, `ble_characteristic`) + `behavioral_signatures` table + `ble_manufacturer_id` enum extension
- **0012-0014** LA-bit pairing (`paired_identifier_id` + `pair_kind`) + Drone-RID identifier_type cluster + ALPR/camera `alpr_model`
- **0015** `source_type='primary_registry'` band for IEEE OUI / FCC EAS / FAA RID / Bluetooth SIG registries
- **0016** `deployment_observations.LICENSE` per-row license tag (Atlas CC-BY-NC-SA-4.0 + DeFlock ODbL-1.0 quarantine)
- **0017** `source_reclassifications` audit table (row-level reclassification ledger)
- **0018** identifier_type enum extension (14 net-new types from community-research dir Phase 1)
- **0019** identifier_type enum extension (7 net-new types from round-2 vocabulary review; cumulative CHECK enum 41 → 48)

### Amendment ledger (v1.0.0 substantive amendments)

The full amendment log lives in [BIBLE_AMENDMENTS.md](BIBLE_AMENDMENTS.md). Below is the substantive-amendment summary for v1.0.0 release.

**Schema / data-shape amendments:**

- **`identifier_type` enum extension cluster**, added `product_family_codename`, `ble_local_name`, `ble_characteristic`.
- **LA-bit pairing**, added `paired_identifier_id` + `pair_kind` columns; Drone-RID identifier_type cluster; ALPR/camera `alpr_model` taxonomy.
- **`source_type='primary_registry'` band**, added for registry-class allocators (IEEE OUI / FCC EAS / FAA RID / Bluetooth SIG) with 70-85 single-source ceiling.
- **`source_type='manufacturer_app'` sub-banding**, vendor companion-app per-class confidence bands + cohort distinction (operator-facing vs installer/pairing-flow apps).
- **`behavioral_signatures` sibling export**, added `argus_export_behavioral_signatures.json` (Rayhunter-consumable).
- **`source_reclassifications` audit table**, added row-level reclassification ledger (`sweep_event_id` grouping + pre/post snapshot + rationale).
- **Lynceus mapping table updates**, populated the Lynceus identifier-type mapping entries for added `identifier_type` values.
- **`identifier_type` enum extensions**, added 14 net-new types from community-research dir Phase 1 + 7 net-new types from round-2 vocabulary review (cumulative CHECK enum 41 → 48).
- **`deployment_observations.LICENSE` per-row column**, added (NOT NULL; Atlas CC-BY-NC-SA-4.0 + DeFlock ODbL-1.0 quarantine).
- **`notes.upstream_license_posture` canonical sentinel-key**, established for facts-only promoted rows (`'NO_LICENSE_DECLARED'`).

**Integration / consumer-facing amendments:**

- **`argus_record_id` stable-identifier algorithm**, `sha256('<identifier_type>|<normalized_identifier>')[:16]`. Stable across re-runs, source-attribution changes, and confidence drift.
- **`geographic_scope` filter**, applied at export time.
- **Severity ownership**, moved operator-side via `severity_overrides.yaml`. Argus ships factual data; downstream consumers own alerting policy.
- **Multi-purpose-vendor carveout**, `device_category='unknown'` excluded from high-confidence Lynceus export.
- **Provenance discipline**, source-url-direct hard rule + per-shape mapper URL template (pinned-SHA + line-anchored).
- **Feist facts-only doctrine**, codified for public-but-unlicensed sources.

**Discipline-evolution amendments:**

- **"Argus identifies; Lynceus correlates"**, architectural boundary: Argus ships factual attribution data; downstream scanners own correlation and alerting.
- **Confidence-band ceiling rule**, corroborated confidence is bounded by the lowest contributing source-type band ceiling.
- **Vendor-disambiguation predicate**, Motorola Mobility / Solutions canonical split; WatchGuard Video / Technologies split.
- **LAA-bit confidence penalty**, locally-administered MAC addresses receive reduced confidence.
- **CVE false-positive allowlist + framework-UUID SDO-attestation discipline**, extraction-time false-positive classification.
- **Amendment-log discipline**, coordinated commits pair canonical-bible edits with this CHANGELOG and the per-row audit trail.
- **No-PII default-to-HOLD**, individual-attributed names without corporate-entity confirmation stay held.

### Pre-v1.0.0 history (major milestones)

The dataset was built over roughly two weeks of intensive multi-agent orchestration. Major milestones, in chronological order:

- **2026-05-04**, Argus working name confirmed; Tier-1 source acquisition complete (Atlas of Surveillance + DeFlock + IEEE OUI + Wireshark `manuf`).
- **2026-05-05 to 05-07**, PDF/HTML extraction waves; the architectural boundary between Argus and Lynceus codified (Argus ships factual attribution; Lynceus owns correlation); coordinated Lynceus integration commits (geographic_scope filter; severity operator-side; `argus_record_id`; multi-purpose-vendor carveout).
- **2026-05-08**, Vendor companion app static analysis admitted as a source class (under the 17 USC §1201(j) + 37 CFR §201.40(b) security-research exemption).
- **2026-05-11**, Community-research GitHub corpus acquired (24 repos); identifier-type extensions for LA-bit pairing, Drone Remote ID, and ALPR/camera taxonomy landed; promotion-cycle-1 closed.
- **2026-05-12**, Promotion-cycle-2 closed (~423 promotions); `primary_registry` source-type band introduced for registry-class allocators; 481 FAA RID drone_id_prefix promotions; Lynceus mapping populated for new identifier_types.
- **2026-05-13**, `manufacturer_app` sub-banding for vendor companion apps; behavioral_signatures sibling export (`argus_export_behavioral_signatures.json`); first behavioral_signatures population (0 → 55 from Marlin NDSS 2025); sources reclassification sweep (808 reclassifications); `source_reclassifications` audit table introduced.
- **2026-05-14**, Final release-readiness pass: IEEE PII triage and promotion (3,446 Class A); community-research deferred-dir Phase 2 close (145 promotions + 38 behavioral-signature backfills); Feist facts-only doctrine codified for public-but-unlicensed sources; final pre-release cleanup; v1.0.0 ship-readiness verified.

### Known limitations + post-v1.0.0 roadmap

Argus's v1.0.0 coverage is **intentionally narrow at this baseline**, do not assume comprehensive coverage of any specific surveillance equipment category. Expansion comes via the community contribution flow (standard GitHub PR + issue process) plus the following queued post-v1.0.0 work:

**Documented held items with rationale** (framed as "known held items; contribution welcome" not "incomplete data"):

- **31 behavioral_signatures** held pending second-source corroboration (substantive research-and-scrape work). Currently HELD with explicit rationale at `behavioral_signatures.notes`.
- **62 Class B sustained holds** (IEEE-derived individual-attributed-pii_sustain rows with `notes.registry_xcheck_attempted=true`), sustained per the PII default-to-HOLD rule; predominantly Lumiplan Duhamel ×9 (French digital-signage corporate; no FCC registration), individual-shaped names, and ~50 unique singletons with no surveillance-tech-vendor or FCC-grantee evidence.
- **133 IEEE Private permanent holds** (`pii_review_disposition='ieee_private_registrant_permanent_hold'`), IEEE OUI registrations declared as private at the registry source; ownership cannot be confirmed.
- **142 round-2 held rows** (107 vocabulary-extension candidates + 19 behavioral-signature deferred + 15 CVE false-positive entries filed to the conflicts table + 1 attribution-pending Motorola/Vigilant).
- **Known sources-row metadata discrepancy**, sources 1/2/3/7 carry historic `source_type='regulatory'` metadata pre-dating the source-type taxonomy refinement; identifier-row data is correctly labeled `primary_registry`. Cleanup queued post-ship. Downstream consumers filtering on `sources.source_type='primary_registry'` should also include `sources.id IN (1,2,3,7)` until the cleanup lands.

**Future-enrichment hooks (operationally inert at v1.0.0):**

- **WiGLE integration**, the `wigle_anchor_priority` table ships at v1.0.0 populated with 80,697 pre-computed priority rankings but operationally inert (WiGLE API gated on user's own quota grant per WiGLE Terms of Service). Post-grant, the WiGLE integration activates without re-derivation.

**Substantive expansion areas (planned post-v1.0.0):**

- **Future community-source-acquisition waves**, additional crowdsourced + community-OSINT + court/FOIA + news/forum source families pending admission-review under the project's source-admission workflow.
- **iOS vendor companion app coverage**, vendor companion app static analysis extended to iOS APK/IPA binaries (v1.0.0 was Android-first; iOS adds vendors with iOS-exclusive companion apps).
- **Skydio Enterprise alt-channel scope**, `com.skydio.enterprise` Android package is law-enforcement-only distribution; alt-channel sourcing approach is a future scope proposal.
- **107 round-2 vocabulary held candidates**, the operator may extend the `identifier_type` enum or accept the candidates as out-of-scope at a future amendment boundary.
- **Lynceus MAP extensions for net-new identifier_types**, `ble_service_uuid` and `ble_company_id` are already aliased to existing pattern_types; other net-new types are currently DROPPED-class. Lynceus integrators may surface specific MAP needs in v1.x patch releases.
- **License-posture composition extensions**, additional downstream-consumer guidance may emerge if new license-posture classes surface.

### Build process

Argus v1.0.0 was built using a multi-agent orchestration platform (Paperclip) with bible-as-contract discipline. Build-process detail in [METHODOLOGY.md §8](METHODOLOGY.md). Commit metadata reflects the agent-ensemble + human-operator authorship per the project's authorship discipline; full identity attribution lives in the git log + [CREDITS.md](CREDITS.md) "Build authorship" section.

**Reproducibility:** the migrations and source-loaders in this repo deterministically reproduce the database from upstream public sources; the agent ensemble is not required at runtime. Re-running the build against current upstream snapshots will yield drift from the v1.0.0-tagged DB because upstream sources change. **Tagged DB releases (downloadable from GitHub Releases) are the canonical artifact for downstream consumers.**

### Acknowledgments

Argus v1.0.0 is the product of public-record research and aggregation across 43 upstream sources + the canonical 34-entry surveillance-tech vendor lexicon. See [CREDITS.md](CREDITS.md) for full per-source attribution.

Particular thanks to the upstream data sources whose licenses make this work possible:

- **EFF + UNLV Reynolds School of Journalism Atlas of Surveillance** (CC-BY-NC-SA-4.0), the largest single deployment-observation corpus integrated (15,071 rows).
- **DeFlock** (ODbL-1.0), ALPR-camera deployment observations integrated under license-compatible terms (101,597 rows).
- **IEEE Standards Association OUI registries**, public factual data anchoring the entire OUI→manufacturer attribution chain (~70,000 rows across MA-L/MA-M/MA-S/IAB).
- **FCC Equipment Authorization System**, public regulatory data anchoring the `fcc_id_anchored` disambig allowlist (50,153 grantees).
- **FAA Remote ID public registry**, public registry data anchoring the drone-class `drone_id_prefix` identifier-type cluster (427 active rows).
- **Bluetooth SIG company-identifier registry**, `ble_manufacturer_id` allocations (3,971 active rows).
- **NDSS 2025 Marlin: Detecting IMSI-Catchers by Characterizing Identity Exposing Messages in Cellular Traffic**, academic foundation for the `behavioral_signatures` table (53 raw observations contributing 55+38=93 corroborated signatures).
- **22 canonical community-OSINT contributors** + **5 secondary-batch contributors**, public open-source-intelligence research repositories listed at [CREDITS.md §5](CREDITS.md).
- **GainSec / anti-crime-ecosystem-research + flock-safety-falcon-sparrow-alpr-edl-firehose**, firmware-binary-anchored extracts (CC-BY-NC-ND-4.0 with research-use clause + NO_LICENSE_DECLARED under the Feist facts-only regime).
- **Wireshark community**, `manuf` file cross-reference for vendor-name curation.

### Integrating with v1.0.0

This is the first tagged release; there is no prior version to migrate from. Downstream consumers integrating Argus for the first time:

1. Download the `argus.db` release artifact from this release's GitHub Releases page (canonical), or build-from-source per [SETUP.md](SETUP.md).
2. Verify `schema_version=19` via `python3 argus_cli.py status` (or directly: `SELECT MAX(version) FROM schema_version;`).
3. Read [METHODOLOGY.md §5](METHODOLOGY.md) (confidence model) before threshold-filtering rows for downstream-scanner watchlists.
4. Read [DATA_DICTIONARY.md §6.2](DATA_DICTIONARY.md) (confidence-shape divergence) before integrating cross-table corroboration logic.
5. Read [LICENSE-DATA §2.1 + §4](LICENSE-DATA) for per-row license-posture handling (CC-BY-NC-SA-4.0 NC clause carry-forward; ODbL-1.0 ShareAlike; Feist facts-only regime; AGPL-3.0 inheritance).
6. Implement the JSON/CSV consumer per the export shapes documented at METHODOLOGY §5.5; bind to `argus_record_id` (16-hex-char SHA-256 prefix, `sha256('<identifier_type>|<normalized_identifier>')[:16]`) as the stable consumer-facing identifier across re-runs.
7. Filter `deployment_observations` on the `LICENSE` column for derivative-use compliance:
   - Commercial deployments: exclude `WHERE LICENSE = 'CC-BY-NC-SA-4.0'` (Atlas rows; non-commercial use only)
   - Standard ODbL ShareAlike compliance: include all (DeFlock + Atlas non-commercial use is licensed)
8. For consumers using `csv.DictReader` against `argus_export.csv`: line 1 is a `# meta:` comment with schema/timestamp/record count; line 2 is the column header. Skip line 1 or use a sniffer-aware reader (e.g., `pd.read_csv(comment='#')`).

---

## Future releases

The project will tag releases when substantive new data, new source families, or schema-impacting changes land. Notable post-v1.0.0 work queued (per "Known limitations + post-v1.0.0 roadmap" above):

- **v1.0.x patch releases**, refresh post-integration of any new public-record source family that completes the source-admission workflow during the post-v1.0.0 cycle; refresh post-resolution of held items (behavioral_signatures second-source corroboration; Class B re-triage if new registries become available).
- **v1.1.0**, projected to ship iOS vendor companion app coverage + future community-source-acquisition waves + Skydio Enterprise alt-channel resolution.

Release cadence: tagged releases when substantive change accumulates; no fixed schedule. Higher-major-version releases (v2.x+) are not projected at the v1.0.0 baseline; they would be documented at the time the change set triggering them is approved.

---

## Canonical sources

Descriptive references used in this document map to canonical bible
anchors as follows. The canonical bible (`PROJECT_BIBLE.md` and the
amendment ledger `BIBLE_AMENDMENTS.md`) holds the authoritative
specification; this CHANGELOG is the public-facing summary.

| Descriptive reference (as used in this doc) | Canonical source |
|---|---|
| canonical 34-entry surveillance-tech vendor lexicon | `PROJECT_BIBLE.md` §2.1 |
| source-type ten-value enum / confidence-band ceilings | `PROJECT_BIBLE.md` §8.2 |
| `+5` corroboration boost / corroboration math | `PROJECT_BIBLE.md` §8.3 |
| confidence model | `PROJECT_BIBLE.md` §5 |
| Lynceus identifier-type mapping | `PROJECT_BIBLE.md` §4.4 |
| export-shape contract | `PROJECT_BIBLE.md` §7.5 |
| hard-rule set (source-url-direct, no-PII, provenance, confidence-ceiling, amendment-log, Feist facts-only) | `PROJECT_BIBLE.md` §11 |
| Feist facts-only doctrine / canonical sentinel-key | `PROJECT_BIBLE.md` §11 #16 |
| `source_type='primary_registry'` band introduction | `BIBLE_AMENDMENTS.md` CP15 |
| `identifier_type` extension cluster (`product_family_codename` + `ble_local_name` + `ble_characteristic`) | `BIBLE_AMENDMENTS.md` CP13 |
| LA-bit pairing + Drone-RID + ALPR/camera taxonomy | `BIBLE_AMENDMENTS.md` CP14 |
| `manufacturer_app` sub-banding + cohort distinction | `BIBLE_AMENDMENTS.md` CP17 |
| behavioral_signatures sibling export | `BIBLE_AMENDMENTS.md` CP18 |
| `source_reclassifications` audit table | `BIBLE_AMENDMENTS.md` CP19 |
| `argus_record_id` stable-identifier algorithm | `BIBLE_AMENDMENTS.md` SAR-10 |
| framework-UUID false-positive class catalog | `BIBLE_AMENDMENTS.md` SAR-11 |
| per-shape mapper precedent (per-shape mapper / URL template / identifier_type-vs-behavioral_signatures routing) | `BIBLE_AMENDMENTS.md` SAR-13 |
