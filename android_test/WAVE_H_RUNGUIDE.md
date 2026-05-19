# Wave H — Desktop Setup-App Static-Analysis Extraction Runguide

**Target:** extend Wave G's APK static-analysis methodology to desktop vendor applications across Windows / macOS / Linux. Recover BLE service UUIDs, default SSID patterns, MAC OUI validation patterns, product-family taxonomy, ONVIF capability strings, SNMP enterprise OIDs, mDNS service types, and network-protocol magic bytes from publicly downloadable VMS clients, drone firmware tooling, network-device configurators, and admin desktop applications.

**Audience:** Claude Code (extraction-side; autonomous within sandbox).

**Style precedent:** mirrors `WAVE_G_RUNBOOK` § structure with Wave G' iOS deferral applied to a sibling axis (desktop, not iOS). All cumulative CP17 / CP20 / CP23 / CP24 / CP26 / CP27 amendments baked in from the start.

**Bible anchors:** §2.1 surveillance-tech vendor categories (this run touches VMS / drone tooling / cellular routers / body-cam / acoustic / forensics), §2.2 out-of-scope (public-data-only — see §6 below), §8.2 vendor-app identifier sub-band ladder (CP17 operator-vs-installer cohort thesis), §11 #1 no fabrication, §11 #2 no non-public data, §11 #3 no PII, §11 #8 within-source-re-extraction-not-corroboration (CP24 sub-rule), §11 #15 no decompiled vendor source committed, §11 #16 Feist facts-only + `notes.upstream_license_posture` canonical sentinel, CP26 §8 semantic-validation as default §4 match-scoring step, CP27 §2.4 empirical-premise verification precondition (§3.0 probe slot below).

**Authority chain (proposed):** MAC-1 → MAC-52 (Wave G plan) → CP17 operator-vs-installer cohort thesis → **MAC-179 (Wave H plan; this runguide).**

---

## §0 — Scope

### What this run does

1. **Discovery (§3.1).** Enumerates publicly downloadable desktop installers + portable distributions for the 49 vendors in the v1.2.0 canonical lexicon, plus a 12-vendor expansion list of VMS-class adjacent vendors not yet in the lexicon. Records per-vendor `documented_absence` rows for vendors with no public desktop distribution.
2. **Acquisition (§3.2).** Downloads installers from vendor public download pages (no auth-gated trials beyond freely-self-issued accounts; no LE-only distribution channels). SHA-256 + provenance URL + capture-timestamp recorded for every binary. Raw binaries land at `raw/vendor_desktop/<vendor>/<product>/<version>/<sha256>.{exe,msi,pkg,dmg,deb,rpm,zip}`; gitignored per §11 #15.
3. **Extraction (§3.3 — §3.6).** Per-cohort static-analysis pipelines:
   - **Cohort A (Electron):** `asar extract` → JS source walk → string-scan via Wave G v4 extractor (parser-agnostic at the candidate-walk layer; only needs decompiled-source-tree path).
   - **Cohort B (.NET):** `ilspycmd` / `dnSpy` → C# decompile → string-scan.
   - **Cohort C (Java desktop):** `jadx` (already in toolchain from Wave G) → Java source → string-scan.
   - **Cohort D (Native Windows .exe / macOS Mach-O / Linux ELF):** `binwalk` / `7z` extraction of installer payloads + GNU `strings` + `Ghidra` headless decompile (function names + string xrefs only; no full decompile preserved per §11 #15).
   - **Cohort E (firmware images):** `binwalk` + `unsquashfs` / `cpio` extraction → filesystem walk → string-scan on configuration files, embedded HTML/JS, init scripts. (See §3.6 license-posture analysis BEFORE any cohort-E extraction fires — many firmware images carry restrictive EULAs.)
4. **Calibration (§3.7).** Mirrors Wave G's calibration-window discipline: process first 2 vendors per cohort, freeze extractor, surface FP classes, codify in SAR-12 (proposed; SAR-11 covered Wave G mobile FP classes).
5. **Staging (§7).** All findings stage to `extraction_outputs/wave_h_pre_v1/per_vendor/<vendor>/{candidates,fp_findings,extraction_counts,manifest}.json` mirroring Wave G shape. No DB writes. Validator promotes downstream.
6. **Handoff (§11).** Single `HANDOFF_TO_VALIDATOR.md` plus per-cohort `analysis_log.md` for the 2 calibration vendors per cohort.

### What this run does NOT do

- **No DB writes.** Read-only snapshot at `argus/db/argus.db`. All outputs to `extraction_outputs/wave_h_pre_v1/`. Schema baseline expectation `schema_version=22` post-MAC-178 close (§2.5).
- **No promotion to identifiers.** Validator's job downstream; same as Wave G handoff posture.
- **No LE-only distribution acquisition.** Per §11 #2: no leaked installers, no cracked downloads, no scraped vendor-extranet content the operator isn't entitled to. Vendors flagged LE-only at Wave G (Axon Capture/View, Motorola WavePush, WatchGuard V300) stay flagged — emit `documented_absence` rows with `absence_reason='LE-only_distribution_per_wave_g_finding'`.
- **No EULA-circumvention extraction (§3.6 gate).** Per CP12 §12 EULA-conflict-policy: (a) hostile EULA + low yield-value → exclude; (c) standard reverse-engineering clause + standard yield-value → include (boilerplate prohibition preempted by §1201 + 37 CFR §201.40(b) in US). §3.6 below makes the per-vendor EULA call BEFORE acquisition fires.
- **No PII extraction.** Desktop apps often surface installer-time POC fields (e.g. "Registered to: <name>"); these are dropped at staging per §11 #3.
- **No active-attack / detection-logic output.** Identifier candidates only; detection rules live in Lynceus per §11 #4 / §11 #5.
- **No decompiled vendor source committed to git.** Per §11 #15: raw binaries at `raw/vendor_desktop/` are gitignored; decompiled trees live in workspace-scratch under `/home/kev/argus-internal/desktop_test/scratch/<vendor>/` and are cleaned at run-end; only extracted candidates (value + relative path inside decompile output + ≤200-char source_excerpt) land in staging.
- **No within-source re-extraction conflation.** Per CP24 §11 #8: if a Wave H vendor's desktop product overlaps the same vendor's Wave G mobile app on a given identifier value (e.g. Avigilon ACC desktop confirms a UUID already extracted from Avigilon ACC Mobile), that is NOT a cross-source corroboration. It IS provenance enrichment (two attestations within the vendor's own published surface). Stage as a vendor-internal re-attestation note in `cross_vendor_attestations.json`; do NOT route into `cross_source_corroborations.json` (which is reserved for genuinely independent sources — FCC EAS, USAspending, court records, etc.).

### Pre-flight schema baseline expectation

`schema_version=22` after MAC-178 close (CP27 §-text-only, no migration; 0022 `fcc_citation_deferred_queue` from MAC-101 partial-deliverable wave is the last migration). Verify at §2.5; halt and surface if different.

---

## §1 — Source profile

| Field | Value |
|---|---|
| `sources.name` | `Vendor Desktop Application Static Analysis — Wave H` |
| `sources.url` | n/a (multi-source aggregation; per-vendor URLs land in `manufacturers.notes.wave_h_source_urls[]`) |
| `sources.source_type` | `vendor_documentation` (existing enum value; same as Wave G `vendor_application_static_analysis` band would land if codified — for now reuse `vendor_documentation` per CP15 source-type ceiling) |
| Tier | 1 |
| License | per-vendor; see §3.6. Default class `NO_LICENSE_DECLARED_FACTS_ONLY` per §11 #16; specific EULAs surface as `EULA_RESTRICTED` (drop) or `RE_PERMITTED_PER_1201` (include). |
| License attribution (verbatim) | per-vendor; captured at acquisition-time from the vendor's EULA / license page; ≤200 chars stored in `notes.license_attribution`. |
| Auth | none (public download pages only; self-issued trial accounts only where the trial signup page itself is unauthenticated). |
| Rate limit | per-vendor download-server-imposed; respect robots.txt + Crawl-delay. ~50 binaries total across the wave; well under any reasonable ceiling. |
| Per-row stable URL | the vendor's public download page at acquisition timestamp; recorded per-candidate in `source_url`. |
| Confidence band | 80-95 per §8.2 vendor-app identifier sub-band ladder (CP17). BLE service UUIDs 80-95; product-family taxonomy 90-95; default SSIDs 70-85; default credentials 60-80 (default-to-hold if ambiguous). |
| Auth shape annotation | `public_download_no_auth` for vendor public pages; `self_issued_trial_account` for trial-gated downloads (Milestone, Genetec, Lenel). |

### Why `vendor_documentation` source_type (not a new enum value)

Wave G mobile-app extraction lands at `vendor_documentation` under CP15's source-type ceiling discipline — the source-type field encodes the *band* of source authority, and vendor's own published distribution (mobile or desktop) is the same band of authority. Promoting Wave H to a separate enum value would multiply the enum without adding band-distinction information that the confidence model can't already encode via the §8.2 sub-band ladder. If post-Wave-H evidence warrants a dedicated `vendor_application_static_analysis` enum value (e.g. Lynceus wants to filter Wave-G+H findings as a class), that's a CP28 candidate — out of scope here.

### Why per-vendor license posture (not a single class)

Desktop EULAs vary far more than mobile-app store-distributed EULAs. Mobile is Google-Play-mediated (boilerplate Play Developer Distribution Agreement + per-app EULA, mostly preemptable by §1201). Desktop EULAs include: vendor-direct click-through agreements, packaged installer EULAs, separate firmware EULAs distinct from installer EULAs, and (in cohort E) embedded device firmware EULAs that may differ from the desktop tool's EULA. §3.6 makes the per-vendor call before acquisition fires.

---

## §2 — Preconditions

### §2.1 — Workspace + gitignore

Wave H operates exclusively under `/home/kev/argus-internal/desktop_test/`. The Wave G `android_test/` workspace is left untouched. Outputs land under `desktop_test/extraction_outputs/wave_h_pre_v1/`. Raw binaries land under `desktop_test/raw/vendor_desktop/` (gitignored). Scratch decompile trees live under `desktop_test/scratch/<vendor>/` (gitignored; cleaned at run-end per §11 #15).

### §2.2 — Gitignore precondition

Confirm `.gitignore` covers both `desktop_test/raw/` and `desktop_test/scratch/`:

```bash
grep -E "^desktop_test/(raw|scratch)/" /home/kev/argus-internal/.gitignore
```

If either is missing: halt; surface; operator extends `.gitignore` before §3 fires. The §11 #15 binding rule is structural; gitignore is its operational enforcement.

### §2.3 — Source not already admitted

```sql
SELECT id, name FROM sources WHERE name LIKE '%Wave H%' OR name LIKE '%Desktop Static Analysis%';
```

If non-empty: halt; re-scope with operator. Wave H source-row admission is net-new this session.

### §2.4 — Toolchain present

Verify the desktop extraction toolchain is installed at `desktop_test/tools/`:

```bash
# Cohort A (Electron)
which asar || npm install -g @electron/asar  # ~10 MB
# Cohort B (.NET)
which ilspycmd || dotnet tool install --global ilspycmd  # ~30 MB
# Cohort C (Java desktop) — inherits Wave G jadx
test -x /home/kev/argus-internal/android_test/tools/jadx/bin/jadx && echo jadx_present
# Cohort D (Native)
which binwalk strings file
which ghidraRun || echo "Ghidra absent — install Ghidra 11.1+ at desktop_test/tools/ghidra/"
# Cohort E (firmware)
which unsquashfs cpio
```

If any cohort's required tooling is absent: halt; surface; operator decides whether to install (in-scope) or descope that cohort (acceptable — Wave H is cohort-decomposable).

### §2.5 — Schema baseline check

```sql
SELECT MAX(version) FROM schema_version;
```

Expected: `22`. If anything other than 22: halt; surface; schema drift would invalidate the `manufacturers.aliases` comma-string contract + the §3.3 ONVIF/SNMP staging shape this runguide assumes.

### §2.6 — Vendor public-download-page reachability spot-check

Verify three vendor download pages are reachable from the workspace network egress (cohort representatives):

```bash
curl -sI -A "Mozilla/5.0 (Argus Wave H research; contact: kev@…)" \
  https://www.verkada.com/command/desktop/ \
  https://www.milestonesys.com/downloads/ \
  https://www.dji.com/downloads/softwares/dji-assistant-2-for-mavic
```

Expected: HTTP 200 (or 301/302 to a 200) on all three. If any returns 403/404/Cloudflare-challenge: log in `precondition_log.md` but do NOT halt — vendor-specific reachability is handled at §3.2 per-vendor with Wayback fallback (Wave-B2 precedent at MAC-18).

### §2.7 — Exit gates

Same precedent as SAM.gov / SEC EDGAR runguides: if any §2.1–§2.5 gate fails → halt + `STOP_THE_LINE_*.md` in output dir + surface. §2.6 reachability is informational. §3.6 EULA-posture gate is per-vendor; per-vendor halt does NOT halt the wave.

---

## §3.0 — Empirical-Premise Verification Probe (CP27 §2.4)

**Per CP27 §2.4: before §3.1 bulk dispatch fires, every load-bearing premise of this runguide MUST be empirically verified against the live source within the same calendar day as dispatch (24-hour staleness ceiling).**

### Load-bearing premises (per-cohort)

| Premise | Verification | Expected outcome |
|---|---|---|
| **P1** — Verkada Command desktop installer is downloadable from `https://www.verkada.com/command/desktop/` without authentication | `curl -sI -A <UA> <url>` returns 200 + `Content-Type: application/octet-stream` on the direct installer URL (or 200 + HTML on the landing page with a clearly fetchable installer link) | CLEAN POSITIVE |
| **P2** — Milestone XProtect Smart Client free download is gated only by a self-issued trial account (not by LE-vetted vendor signup) | Reach `https://www.milestonesys.com/downloads/` → free product list includes "XProtect Essential+" or "XProtect Smart Client" → signup page is open-self-issue | CLEAN POSITIVE |
| **P3** — DJI Assistant 2 (Windows or macOS variant) is publicly downloadable from `https://www.dji.com/downloads/` | Landing page lists Assistant 2 variants for ≥3 DJI product families with direct .exe / .pkg download links | CLEAN POSITIVE |
| **P4** — Wave G `wave_g_extractor.py` v4 candidate-walk layer is parser-agnostic w.r.t. decompiled-source-tree input | Spot-test: point the extractor at a 3-file synthetic JS tree containing one BLE UUID string in a `.js` source; extractor surfaces the candidate without modification | CLEAN POSITIVE |
| **P5** — `electron/asar` extracts a publicly downloadable Electron app's `app.asar` to a directory tree of JS source without an Electron-runtime gate | Test against any small public Electron app (e.g., a GitHub-released Electron demo); `asar extract` yields a directory of `.js` files | CLEAN POSITIVE |
| **P6** — `ilspycmd` decompiles a publicly downloadable .NET WPF app to C# source without an obfuscator-gate that defeats string extraction | Test against a non-obfuscated open-source .NET WPF app from GitHub releases; `ilspycmd <exe>` yields C# source with readable string literals | CLEAN POSITIVE |
| **P7** — Cradlepoint NCOS firmware images are publicly downloadable from `https://customer.cradlepoint.com/s/article/NCOS-Releases` (or the equivalent public release-notes page) without authentication | `curl -sI <one specific NCOS .bin URL>` returns 200 + `Content-Type: application/octet-stream`. **High-risk premise** — Wave-B2 byte-level survey at MAC-18 noted Cradlepoint kb pages were Salesforce-gated. | INCONCLUSIVE acceptable — if firmware download itself is gated, Cohort E descopes Cradlepoint without halting other cohorts |
| **P8** — `manufacturers.aliases` is comma-string TEXT (not a separate table) — extraction must append to the comma-string with NULL-guard semantics, NOT INSERT into a sibling table | `PRAGMA table_info(manufacturers);` shows `aliases TEXT` column; no `manufacturer_aliases` sibling table exists | CLEAN POSITIVE |
| **P9** — `raw_observations.source_excerpt` has no CHECK constraint (capture full verbatim as the unredacted audit anchor); `identifiers.source_excerpt` is ≤200 (per CP23 schema-truth correction) | `SELECT sql FROM sqlite_master WHERE type='table' AND name IN ('raw_observations','identifiers');` — verify CHECK on `identifiers.source_excerpt` is `≤200`, no CHECK on `raw_observations.source_excerpt` | CLEAN POSITIVE |
| **P10** — Schema version is `22` (CP27 §-text-only; no migration); no migration `0023*.sql` exists on disk that the runguide's premises don't account for | `SELECT MAX(version) FROM schema_version;` returns 22; `ls argus/db/migrations/` ends at `0022_*.sql` | CLEAN POSITIVE |

### Probe decision rule (CP27)

- **CLEAN POSITIVE on all premises** → §3.1 dispatch authorized.
- **CLEAN NEGATIVE on P1–P6, P8–P10** → halt; runguide returns to drafting; CEO disposition required.
- **CLEAN NEGATIVE on P7 (Cradlepoint firmware gating)** → Cohort E Cradlepoint descopes; emit `documented_absence` row; remaining cohorts proceed.
- **INCONCLUSIVE on any premise** → halt; CEO disposition required.

### Probe output artifact

Emit `extraction_outputs/wave_h_pre_v1/_probe_log.md` capturing per-premise probe command + observed outcome + UTC timestamp + CLEAN POSITIVE / NEGATIVE / INCONCLUSIVE disposition. The probe log is the audit anchor for the §2.4 staleness ceiling.

---

## §3 — Methodology

### §3.1 — Per-cohort vendor target list

**Cohort A — Electron VMS clients** (expected highest yield; Wave G calibration extrapolation suggests Electron apps are ~Android-equivalent in identifier density per LOC):

| Vendor | Product | Distribution |
|---|---|---|
| Verkada | Command (desktop) | Public download, no auth |
| Eagle Eye Networks | EEN Viewer | Public download, no auth |
| Rhombus Systems | Console | Public download, no auth |
| Avigilon (Motorola) | Alta Aware | Public download, no auth |
| Skydio | Pilot (web bundle, downloadable as Electron) | Public download, no auth |
| Verkada | Command Connector (separate Electron-class binary) | Public download, no auth |

**Cohort B — .NET / WPF VMS clients** (medium-high yield expected; .NET decompiles cleanly when not obfuscated):

| Vendor | Product | Distribution |
|---|---|---|
| Milestone Systems | XProtect Smart Client | Self-issued trial account |
| Genetec | Security Desk (Security Center workstation) | Self-issued trial account |
| Lenel S2 (Honeywell) | OnGuard | Self-issued trial account |
| Honeywell | Pro-Watch | Self-issued trial account |
| Tyco / Software House (Johnson Controls) | C-CURE 9000 client | Self-issued trial account |
| Gallagher | Command Centre client | Self-issued trial account |
| Axon | Axon View XL (Windows desktop — flagged at Wave G handoff §6 as runbook-misclassified) | Public download (if available) or `documented_absence` |

**Cohort C — Native C++ VMS clients** (medium yield expected; native decompile slower + lower readability than .NET / Electron):

| Vendor | Product | Distribution |
|---|---|---|
| Avigilon (Motorola) | Control Center (ACC) Client | Public download, no auth |
| Bosch | Video Management System (BVMS) Operator Client | Self-issued trial account |
| Hanwha Vision | WAVE / WAVE Sync (Windows variant) | Public download, no auth |
| i-PRO (formerly Panasonic Security) | i-PRO Surveillance | Public download, no auth |
| Pelco (Motorola) | VideoXpert | Public download, no auth |
| Axis Communications | Axis Camera Station + Axis Companion | Public download, no auth |
| Mobotix | MxManagementCenter (MxMC) | Public download, no auth |

**Cohort D — Drone firmware tooling** (high yield expected per Wave G calibration; firmware tooling is installer-cohort-equivalent for drones):

| Vendor | Product | Distribution |
|---|---|---|
| DJI | Assistant 2 (per-product-family variants: Mavic, Phantom, Matrice, Agras) | Public download, no auth |
| DJI | Terra (photogrammetry / mission planning) | Public download, no auth |
| Skydio | Skydio Pilot (desktop Electron variant if exists; web JS bundle if not) | Public download, no auth |
| Parrot | FreeFlight 7 desktop (if exists) | Public download, no auth |
| Autel Robotics | Explorer Desktop / Autel Smart Controller updater | Public download, no auth |

**Cohort E — Network device firmware images + configurators** (variable yield; firmware extraction is the deepest analysis; §3.6 EULA-posture gate is most likely to halt here):

| Vendor | Product | Distribution |
|---|---|---|
| Cradlepoint (Ericsson) | NCOS firmware (.bin) for IBR900 / IBR1700 / R1900 | **High-risk per Wave-B2 byte-level survey at MAC-18 — Salesforce-gated knowledge base; verify at §3.0 P7** |
| Sierra Wireless (Semtech) | ALEOS firmware for AirLink GX/RV/MG90 | **High-risk — Wave-B2 noted source.sierrawireless.com is login-gated** |
| Hak5 | Cloud C2 (Linux ELF; desktop variant of the server) | Public download (Hak5 is research-toolkit vendor; permissive posture) |
| Axis Communications | Axis Device Manager + firmware images | Public download, no auth |

**Cohort F — Sanctioned-vendor configurators** (special EULA + OFAC/EAR posture; §3.6 gates most strongly here):

| Vendor | Product | Distribution + Notes |
|---|---|---|
| Hikvision | iVMS-4200 (Windows desktop client) | Public download via hikvision.com — OFAC SDN + BIS Entity List; data is fact (Feist), but acquisition surfaces OFAC review per §3.6 sub-gate |
| Dahua | SmartPSS | Public download via dahuasecurity.com — same OFAC/BIS posture |
| Uniview | EZStation | Public download via uniview.com — Entity List 2022; same posture |

**Cohort G — Adjacent / new-to-lexicon VMS** (12-vendor expansion):

| Vendor | Product | Distribution |
|---|---|---|
| 3xLOGIC | ViGiL Client | Public download |
| Salient Systems | CompleteView | Self-issued trial |
| Exacq (Johnson Controls) | exacqVision Client | Public download |
| Digital Watchdog (DW) | DW Spectrum IPVMS | Public download |
| Vivotek | VAST 2 / VSS | Public download |
| Lumen / Intransa | (legacy; deprecated lookup) | likely `documented_absence` |
| Senstar / Stellar Cyber | Senstar Symphony | Self-issued trial |
| ipConfigure | Orchid Core VMS | Public download (open-source-adjacent) |
| Camcloud | (cloud-only — no desktop) | `documented_absence` |
| Eagle Eye / IC Realtime | (sister to cohort A) | Public download |
| Wisenet (Hanwha sub-brand) | Wisenet WAVE Sync | Same as Hanwha Cohort C |
| Verint (formerly Vidient) | Op-Center | Self-issued trial |

**Cohort H — Forensics + acoustic + drone-detection** (where desktop tooling is publicly distributed):

| Vendor | Product | Distribution |
|---|---|---|
| Cellebrite | Cellebrite Reader (read-only viewer for UFED exports; publicly downloadable, unlike full UFED) | Public download via cellebrite.com |
| Magnet Forensics | Magnet AXIOM (trial-gated) | Self-issued trial |
| BriefCam | (typically server-side; `documented_absence` likely) | TBD |
| SoundThinking (ShotSpotter) | (no desktop tool; `documented_absence`) | TBD |
| Dedrone | (server-side / on-prem; likely `documented_absence`) | TBD |
| DroneShield | (similar; likely `documented_absence`) | TBD |

### §3.2 — Acquisition workflow per vendor

1. Vendor public download page → identify the canonical current-version installer. Capture the page URL + version string + observed-at UTC timestamp.
2. If self-issued trial is required: register a research-shaped account using `wave_h_research_<n>@<operator-controlled-domain>`. Do NOT use a personal email. Document the registration page URL + the trial duration + any acceptance-of-terms clicked. The EULA / terms accepted at trial registration is the per-vendor license posture for §3.6.
3. Download the installer. Hash with `sha256sum`. Record: `<vendor>/<product>/<version>/<sha256>.<ext>` provenance row in `raw/vendor_desktop/_provenance.json`.
4. If installer is an MSI / .pkg / .deb / .rpm with verifiable signature, capture the signing certificate's Subject + Issuer (catches multi-purpose-vendor shifts — e.g. Avigilon-now-Motorola signed binaries).
5. Move to §3.3 cohort-specific extraction.

### §3.3 — Cohort-specific extraction

**Cohort A (Electron):**

```bash
# Extract installer payload (NSIS .exe / Squirrel .nupkg / .dmg / .deb)
7z x <installer> -o<scratch>/<vendor>/extracted/
# Locate app.asar
find <scratch>/<vendor>/extracted/ -name 'app.asar' -o -name 'app-*.asar'
# Extract
asar extract <path>/app.asar <scratch>/<vendor>/asar_out/
# Point Wave G extractor at the asar_out tree
python3 /home/kev/argus-internal/android_test/tools/extraction/wave_g_extractor.py \
  --input-tree <scratch>/<vendor>/asar_out/ \
  --output-dir <staging>/<vendor>/ \
  --extractor-mode desktop_electron_cohort_a
```

The `--extractor-mode` flag is a new arg the runguide proposes adding to the v4 extractor (one-line passthrough; sets a `cohort_label` field on every emitted candidate). If the operator prefers to leave the v4 extractor untouched, set the cohort label at the staging-aggregation step instead.

**Cohort B (.NET):**

```bash
# Locate primary .exe (often <Product>.exe alongside many DLLs)
ilspycmd -p -o <scratch>/<vendor>/dotnet_out/ <installer-extracted>/<product>.exe
# Recursively decompile referenced DLLs
for dll in <installer-extracted>/*.dll; do
  ilspycmd -p -o <scratch>/<vendor>/dotnet_out/ "$dll" || true
done
# Wave G extractor on the C# tree
python3 wave_g_extractor.py --input-tree <scratch>/<vendor>/dotnet_out/ \
  --output-dir <staging>/<vendor>/ --extractor-mode desktop_dotnet_cohort_b
```

**Cohort C (Native C++ — Ghidra headless):**

```bash
# Strings-first pass (cheap, broad)
strings -n 8 -a <installer-extracted>/<product>.exe > <scratch>/<vendor>/strings_<product>.txt
# Ghidra headless for function names + string xrefs
$GHIDRA_HOME/support/analyzeHeadless <scratch>/<vendor>/ghidra_proj <product>_proj \
  -import <installer-extracted>/<product>.exe -postScript ExportSymbolsAndStrings.java
# Wave G extractor on the strings dump (with a native-cohort regex tweak)
python3 wave_g_extractor.py --input-tree <scratch>/<vendor>/strings_<product>.txt \
  --output-dir <staging>/<vendor>/ --extractor-mode desktop_native_cohort_c
```

**Cohort D (drone firmware tooling — variable native + .NET):** apply Cohort B or C per binary type. DJI Assistant 2 is largely native C++ with Qt; ilspycmd doesn't apply. Treat as Cohort C.

**Cohort E (firmware images):**

```bash
# Identify filesystem
binwalk <firmware>.bin
# Extract (typical: SquashFS + uImage)
binwalk -e <firmware>.bin
# Walk extracted filesystem
find _<firmware>.bin.extracted/ -type f \( -name '*.conf' -o -name '*.cfg' -o -name '*.html' -o -name '*.js' -o -name '*.json' -o -name '*.xml' \) \
  -exec strings -n 8 {} \; > <scratch>/<vendor>/firmware_strings.txt
# Wave G extractor
python3 wave_g_extractor.py --input-tree <scratch>/<vendor>/firmware_strings.txt \
  --output-dir <staging>/<vendor>/ --extractor-mode desktop_firmware_cohort_e
```

### §3.4 — Identifier classes extracted (per CP17 + new Wave H additions)

| Class | Wave G coverage | Wave H additions | Sub-band (CP17) |
|---|---|---|---|
| `ble_service_uuid` | yes | yes (same regex) | 80-95 |
| `ble_characteristic_uuid` | yes | yes | 80-95 |
| `vendor_template_namespace_uuid` | yes (Getac suffix observation) | yes | 75-90 |
| `default_ssid` | yes | yes | 70-85 |
| `default_credential` | yes | yes (default-to-hold) | 60-80 |
| `mac_oui_validation` | yes | yes | 75-90 |
| `product_family_marketing_name` | yes | yes | 90-95 |
| `product_family_internal_codename` | yes (Penguin / Hazyhiwire) | yes | 85-95 |
| `device_type_enum_value` | yes | yes | 90-95 |
| `onvif_capability_string` | n/a (mobile rarely surfaces ONVIF) | **new** — ONVIF profile capability literals from VMS clients (`Profile S`, `Profile T`, `Profile G`, vendor-specific extensions) | 75-90 |
| `snmp_enterprise_oid` | n/a | **new** — IANA-registered enterprise OIDs hardcoded in VMS clients (`.1.3.6.1.4.1.<vendor>`) cross-reference against IANA registry | 85-95 (IANA registry is canonical) |
| `mdns_service_type` | n/a (mobile uses), uncommon | **new** — `_axis-video._tcp` / `_pelco._tcp` / etc. service types | 75-90 |
| `network_protocol_magic_bytes` | n/a | **new** — proprietary protocol magic bytes (e.g. Axis VAPIX header magic, Hikvision SDK header, ONVIF SOAP magic) | 70-85 (magic bytes are easy to FP; require ≥2 cross-references in the binary) |
| `firmware_filename_pattern` | yes (Penguin OTA filenames) | yes | 80-95 |
| `update_endpoint_url` | partial | **new** — hardcoded update / cloud API endpoint URLs (vendor-controlled domains attest vendor ownership of those endpoints) | 75-90 |

### §3.5 — Match-scoring discipline (CP26 §8 semantic-validation)

Per **CP26 §8** codified at the cycle-5 wave: any match-scoring step against a textual source MUST validate semantic relationship between the vendor-token and the surrounding-context anchor BEFORE promoting the match. Text-pattern match is necessary but NOT sufficient for STRONG promotion. Documented FP classes from Wave G + CP26 carry forward; Wave H surfaces new ones (codify in SAR-12 calibration window):

- **Third-party library co-occurrence** (Wave G calibration) — UUID appears in a `node_modules/<lib>/` or `vendor/<lib>/` path → drop. Especially common in Electron (massive `node_modules` trees).
- **Bundled-fork detection** (Wave G calibration) — WebRTC / Twilio / Agora forks; carries vendor-internal namespace but is third-party bundled. Cohort A is expected to surface this in spades.
- **Framework UUID FP classes** (Wave G calibration) — `RFC6455_WEBSOCKET_GUID`, `ANDROID_AUDIOEFFECT_UUIDS`, `ANDROIDX_WORK_UUIDS` already codified. Wave H likely surfaces: `.NET_DEVCLASS_GUIDS` (Windows device class GUIDs in driver-adjacent code paths), `COM_INTERFACE_GUIDS` (COM/OLE registry GUIDs — these are NOT vendor BLE UUIDs even if shape matches), `WIX_INSTALLER_GUIDS` (WiX MSI installer component GUIDs).
- **OEM-licensing-engine FP** — many VMS clients embed third-party licensing engines (FlexLM, Wibu CodeMeter, Sentinel HASP); their fingerprints are licensing-vendor identifiers, not surveillance-vendor identifiers.

### §3.6 — Per-vendor license-posture / EULA gate

**Before §3.2 acquisition fires for any vendor**, evaluate the per-vendor EULA posture:

1. Read the EULA / license page linked from the vendor's download page or surfaced at trial-signup-time.
2. Search for clauses: "reverse engineer", "decompile", "disassemble", "security research", "no benchmarking".
3. Categorize:
   - **Category (a) — hostile EULA + low yield-value**: drop. Emit `documented_absence` row with `absence_reason='EULA_RESTRICTED_low_yield'`.
   - **Category (b) — hostile EULA + high yield-value**: surface to board (`_BOARD_REVIEW_<vendor>_eula.md`). Do NOT acquire pending board disposition.
   - **Category (c) — standard reverse-engineering boilerplate + standard yield-value**: include. Standard boilerplate prohibition is preempted by §1201 + 37 CFR §201.40(b) in US for good-faith security research. Record EULA verbatim clause (≤200 chars) at `notes.license_attribution`.
   - **Category (d) — anti-circumvention clause specifically targeting security research**: drop. Emit `documented_absence` row with `absence_reason='EULA_RESTRICTED_security_research_carveout'`.
4. **Sanctioned-vendor sub-gate (Cohort F)**: for Hikvision / Dahua / Uniview, the EULA is one axis; OFAC SDN + BIS Entity List + DOD CMC list posture is another. The current Argus discipline at CP20 §11 #16 + §11 #2 is: data is fact (Feist), and Argus does not transact with the sanctioned entity (no purchase, no license fee, no API access). Public website downloads of free desktop clients land at the same posture as any other public vendor distribution. **However**, downloading from a Chinese-government-cloud-mirrored endpoint (e.g. `download.hikvision.com.cn` rather than `hikvision.com`) is a separate sub-gate — prefer the .com endpoint where both exist; if only the .cn endpoint is available, surface to operator for disposition.

### §3.7 — Calibration window (Wave G parallel)

Per Wave G discipline: process the first 2 vendors per cohort, then **freeze the extractor + the cohort-specific FP class set + the disambig module** before the remaining N-2 vendors in that cohort run. Surface novel FP classes in `calibration_window_findings.md` per cohort. The calibration window is the discipline anchor for SAR-12 codification proposals.

---

## §4 — Confidence + provenance

### §4.1 — Per-row confidence at staging time

Default per-row confidence = midpoint of relevant §3.4 sub-band. Adjustments per Wave G precedent:

- **SAR-7 / SAR-8 / SAR-9 corroboration** (Wave G existing) — composes naturally with Wave H findings.
- **CP17 cohort lift / decline** — installer-cohort (Cohorts B, C, D, E, F when configurator) gets default-midpoint; operator-cohort variants surface as product-family-only, lower confidence.
- **CP24 within-source-re-extraction discipline** — if Wave H Avigilon ACC Desktop surfaces the same UUID as Wave G Avigilon ACC Mobile, that is NOT a §8.3 corroboration lift. It IS provenance enrichment; stage at `cross_vendor_attestations.json` (separate from `cross_source_corroborations.json`).
- **CP26 §8 semantic-validation** — text-pattern match + context anchor is a default §4 match-scoring sub-step. Wave H's higher native / .NET / Electron string-literal density makes false-positive risk HIGHER than Wave G mobile; tighter context windows recommended.

### §4.2 — Source URL provenance per candidate

Every Wave H candidate carries:

- `source_url` — the vendor's public download page at acquisition time (NOT the installer URL itself, which often expires; the canonical product page URL is the stable anchor).
- `source_url_secondary` — the installer URL at acquisition time + SHA-256.
- `source_excerpt` — ≤200 chars verbatim from the decompiled source line that surfaces the candidate, with the candidate value highlighted. Per CP23 schema-truth: `identifiers.source_excerpt` ≤200, `raw_observations.source_excerpt` no CHECK.
- `decompile_relative_path` — relative path within the scratch decompile tree where the candidate was found. Stays scratch-internal per §11 #15; surfaces in `manifest.json` only.
- `decompile_tool` + `decompile_tool_version` — `asar@<v>` / `ilspycmd@<v>` / `Ghidra@<v>` / `binwalk@<v>` for the audit trail.

### §4.3 — `notes.upstream_license_posture` canonical sentinel (CP21)

Every promoted identifier from Wave H carries the canonical sentinel key `notes.upstream_license_posture` per CP21:

- For vendors with `RE_PERMITTED_PER_1201` license posture: `notes.upstream_license_posture='vendor_eula_re_permitted_per_1201_facts_only'`.
- For vendors with `NO_LICENSE_DECLARED_FACTS_ONLY` license posture: `notes.upstream_license_posture='no_license_declared_facts_only'`.
- For sanctioned-vendor Cohort F: `notes.upstream_license_posture='sanctioned_vendor_public_distribution_facts_only'` (new sentinel value — codify in CP28 candidate if it lands).

---

## §5 — Halt criteria (composes with §6 #5)

Halt the wave (write `STOP_THE_LINE_*.md`, surface to operator) if any of:

1. §2.1–§2.5 precondition fails.
2. §3.0 CLEAN NEGATIVE on P1–P6, P8–P10, or INCONCLUSIVE on any premise.
3. §3.6 surfaces ≥3 Category-(b) vendors (high-yield + hostile EULA) in a single dispatch — operator may want to re-batch as a board-review wave instead of inline halting.
4. Decompile tooling fails on ≥30% of any cohort's vendors (signals tooling-side bug, not vendor-side variance).
5. Any candidate value matches a known **fabrication signature** (e.g. a UUID that matches a publicly-documented FP class like `RFC6455_WEBSOCKET_GUID`) at promotion-staging-time — should have been caught at extraction, escape signals a regression in the v4 extractor. Halt to surface the regression.
6. Verbatim source_excerpt exceeds 200 chars for any candidate routed to `identifiers` staging (CP23 schema-truth).
7. Any candidate value carries PII (named individual, badge, license plate, home address, phone, email of a real person not a corporate role-address). PII discipline is §11 #3.

Halt the **cohort** (continue other cohorts) if:

8. §3.0 CLEAN NEGATIVE on P7 (Cohort E firmware gating premise).
9. §3.6 surfaces a Category-(d) vendor (security-research-targeting EULA) in that cohort.
10. Acquisition fails on ≥30% of that cohort's vendors (network / Cloudflare / etc.).

---

## §6 — Output structure

```
extraction_outputs/wave_h_pre_v1/
├── _probe_log.md                          # §3.0 CP27 §2.4 verification probes
├── _provenance.json                       # raw/vendor_desktop/ provenance index
├── manifest.json                          # session metadata
├── per_vendor/
│   └── <vendor_slug>/
│       ├── apk_manifest.json              # (rename for desktop: binary_manifest.json)
│       ├── candidates.json
│       ├── fp_findings.json
│       ├── extraction_counts.json
│       ├── analysis_log.md                # calibration vendors only (2 per cohort)
│       └── source_excerpts/<cls>_<n>.txt  # full source_excerpt per candidate (≤200 for identifiers tier, no cap for raw_observations tier)
├── calibration/
│   ├── calibration_window_findings.md     # per-cohort calibration journey
│   ├── proposed_fp_classes.json           # candidates for SAR-12
│   ├── proposed_disambig_additions.py
│   └── raw_pre_calibration_snapshots/<cohort>/<vendor>/
├── cross_vendor_attestations.json         # CP24 within-vendor across-product re-attestation (NOT §8.3 lift)
├── cross_source_corroborations.json       # Wave H findings that corroborate non-Wave-H sources (FCC EAS / USAspending / etc.) — §8.3 lift candidates
├── manufacturer_enrichment_records.json   # per-vendor product-family taxonomy + EULA posture + signing cert subject
├── source_admission_metadata.json         # §7 contract
└── HANDOFF_TO_VALIDATOR.md                # session close-out
```

---

## §7 — Source admission metadata template

```json
{
  "name": "Vendor Desktop Application Static Analysis — Wave H",
  "url": null,
  "source_type": "vendor_documentation",
  "tier": 1,
  "license": "per_vendor",
  "license_attribution": "per-vendor EULA captured at acquisition; see manufacturer_enrichment_records.json[].eula_excerpt",
  "notes_json": {
    "session_admission": "wave_h_pre_v1",
    "admission_date_utc": "...",
    "runguide_path": "new data 5.18/wave_h_desktop_setup_app_runguide.md",
    "cycle_completion_state": "...",
    "next_cycle_dispatch_scheduled_for_utc": "...",
    "next_cycle_dispatch_runguide_path": "...",
    "partial_yield_metrics_at_admission": {},
    "license_posture": "per_vendor",
    "access_mode": "public_download_no_auth + self_issued_trial_account (per-vendor split documented in manufacturer_enrichment_records.json)",
    "access_mode_reason": "Wave H acquisition is split between vendor public download pages and vendor-issued open-self-signup trial accounts. No LE-vetted distribution, no leaked installers, no scraped extranet content.",
    "cohorts_processed": ["A_electron","B_dotnet","C_native_cpp","D_drone_firmware_tooling","E_firmware_images","F_sanctioned_vendor_configurators","G_adjacent_vms","H_forensics_acoustic_drone_detection"],
    "vendors_processed": 0,
    "vendors_documented_absence": 0,
    "binaries_acquired": 0,
    "binaries_failed_acquisition": 0,
    "candidates_total": 0,
    "candidates_by_class": {},
    "fp_findings_total": 0,
    "fp_classes_novel_for_sar_12": [],
    "cross_vendor_attestations_total": 0,
    "cross_source_corroborations_total": 0,
    "calibration_freeze_timestamp_per_cohort": {},
    "eula_posture_disposition_counts": {"category_a_drop": 0, "category_b_board_review": 0, "category_c_include": 0, "category_d_drop": 0},
    "sanctioned_vendor_findings_count": 0,
    "extraction_tools_used": ["asar","ilspycmd","jadx","ghidra","binwalk","unsquashfs","strings"],
    "extraction_tools_versions": {}
  },
  "last_fetched_at": "...",
  "last_status": "..."
}
```

---

## §8 — Cross-references

- Bible §2.1 surveillance-tech categories — this wave touches categories 1, 5, 6, 7, 8, 9, 10, 11, 12.
- Bible §2.2 out-of-scope — public-data-only binding.
- Bible §8.2 vendor-app identifier sub-band ladder — Wave H inherits CP17 ladder.
- Bible §11 #2 (no non-public data), §11 #3 (no PII), §11 #15 (no decompiled source committed), §11 #16 (Feist facts-only + canonical sentinel).
- CP12 §12 EULA-conflict-policy — Wave H §3.6 is the operational expression.
- CP15 source-type ceiling — Wave H reuses `vendor_documentation` rather than expanding the enum.
- CP17 operator-vs-installer cohort thesis (Wave G origin) — Wave H tests whether the thesis generalizes from mobile to desktop (expected: yes, with the same yield-shape per cohort).
- CP20 §11 #16 + CP21 canonical sentinel + CP23 sources.notes_json folding — all binding on Wave H staging.
- CP24 §11 #8 within-source-re-extraction-not-corroboration sub-rule — Wave H operationalizes the "within-vendor across-product" extension via `cross_vendor_attestations.json`.
- CP26 §8 semantic-validation as default §4 match-scoring step — Wave H §3.5 binding.
- CP27 §2.4 empirical-premise verification precondition — Wave H §3.0 binding.
- Wave G `wave_g_extractor.py` v4 + SAR-11 FP classes — Wave H inherits, extends SAR-12.

---

## §9 — Closing-loop summary fields (handoff template)

Headline metric: **net-new vendor BLE service+characteristic UUIDs surfaced across cohorts A through H, with per-cohort yield-shape comparison vs Wave G operator/installer baseline.**

Secondary metrics (per §6 `source_admission_metadata.json` `notes` block):

- Vendors processed (of ~50 targets across 8 cohorts)
- Vendors emitted as `documented_absence` (and per-cohort reason breakdown)
- Binaries acquired / acquisition-failed
- Candidates by class (especially the 5 new Wave H identifier classes: `onvif_capability_string`, `snmp_enterprise_oid`, `mdns_service_type`, `network_protocol_magic_bytes`, `update_endpoint_url`)
- Novel FP classes surfaced for SAR-12 codification (Wave G surfaced 15+; Wave H is expected to surface a different set per the Electron / .NET / native cohort-shape diversity)
- Cross-vendor attestations (within-vendor cross-product, NOT §8.3 lift)
- Cross-source corroborations (Wave H findings that overlap FCC EAS / USAspending / SEC EDGAR / court records — §8.3 lift candidates)
- EULA-posture disposition counts (category a/b/c/d)
- Operator-vs-installer-cohort-thesis-validation finding (does the Wave G mobile thesis generalize to desktop? expected yes for VMS clients which are admin-cohort, mixed for drone tooling which is closer to operator-cohort)
- Sanctioned-vendor Cohort F findings (separate report; OFAC/EAR audit-trail anchor)
- Any cycle patch inputs surfaced

---

## §10 — What this wave does NOT change

- No schema migration. Wave H runs against schema_version=22 baseline; no new tables, no new columns, no enum extensions. (If post-handoff calibration suggests a dedicated `vendor_application_static_analysis` source_type enum value would help Lynceus filter Wave G + H findings as a class, that's a CP28 candidate.)
- No bible §-text amendment. Wave H is operational within existing §11 + CP17 + CP20 + CP21 + CP23 + CP24 + CP26 + CP27 envelope.
- No downstream-consumer changes. Lynceus / Talos consume Wave H findings through the same `argus_export*` shape as Wave G findings.

---

*This runguide is the Wave G' desktop-axis sibling. Wave G' iOS-axis remains future work; the two siblings are independent and can be sequenced in either order. Wave H is sequenced first per CEO disposition that the desktop yield-projection (Electron app density + .NET decompile cleanness + DJI Assistant 2 native richness) materially exceeds the iOS projection given iOS's tighter store-distribution model and stronger native obfuscation.*
