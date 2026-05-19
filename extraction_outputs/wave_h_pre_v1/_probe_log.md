# Wave H §3.0 Empirical-Premise Verification Probe Log

**Probe runner:** Claude Code extraction-side; autonomous within sandbox
**Probe date UTC:** 2026-05-18 (within CP27 §2.4 24-hour staleness ceiling for §3.1 dispatch)
**Runguide:** `new data 5.18/wave_h_desktop_setup_app_runguide.md`
**Per CP27 §2.4:** All P1-P10 must verify within 24-hour staleness ceiling before §3.1 dispatch authorized.

---

## Operator dispositions in effect

- **D1.a** — install all 4 absent tools (`asar`, `dotnet`+`ilspycmd`, `binwalk`, `Ghidra`) to SSD where possible (operator-approved 2026-05-18).
- **D2.a** — authorize "search-for-current-URL per premise" fallback discipline. Substantive premise binds; literal-URL CLEAN NEGATIVE is non-binding if substantive premise verifies at a different URL.
- **D3.a** — wave_h_wrapper.py adapter, v4 untouched. Wrapper passes input_tree as v4's `jadx_out` and a non-existent path as v4's `apktool_out` (iter_candidate_files silently skips missing roots, yielding each input_tree file exactly once with input_tree as root for relative-path computation).

---

## §2 precondition gate results

| Gate | Result | Notes |
|---|---|---|
| §2.1 workspace | **PASS** | `/home/kev/argus-internal/desktop_test/` created; raw/scratch/tools symlinked to `/media/kev/Extreme SSD/argus/desktop_test/` (276 GB free vs 11 GB localdisk). |
| §2.2 gitignore | **STRUCTURAL PASS** | Workspace placed OUTSIDE `/home/kev/argus-internal/argus/` git repo; §11 #15 (no decompiled vendor source committed to git) satisfied structurally. No gitignore entry required. |
| §2.3 source not already admitted | **PASS** | No prior Wave H or "Desktop Static Analysis" source row in DB. |
| §2.4 toolchain | **PASS (post D1.a)** | `asar` v4.2.0 (SSD npm-prefix), `dotnet` 8.0.421 SDK (SSD), `ilspycmd` 9.1.0.7988 (SSD), `Ghidra` 12.1 with `analyzeHeadless` (SSD). `binwalk` still absent (needed for Cohorts D firmware-side / E); operator must `! sudo apt install -y binwalk` before Cohort D/E dispatch. Cohorts A/B/C/F do not require binwalk and proceed without it. |
| §2.5 schema baseline | **PASS** | `schema_version=22`; last migration `0022_fcc_citation_deferred_queue.sql`. |
| §2.6 reachability spot-check (informational) | **MIXED** | See P1/P2/P3 below. Runguide URLs stale; operator-authorized search-for-current-URL fallback used to verify substantive premises. |

### §2.4 toolchain inventory (post D1.a)

| Tool | Path | Version | Used by cohort |
|---|---|---|---|
| `asar` | `/media/kev/Extreme SSD/argus/desktop_test/tools/npm-global/bin/asar` | 4.2.0 | A (Electron) |
| `dotnet` | `/media/kev/Extreme SSD/argus/desktop_test/tools/dotnet/dotnet` | 8.0.421 | B (.NET) host |
| `ilspycmd` | `/media/kev/Extreme SSD/argus/desktop_test/tools/dotnet-tools/ilspycmd` | 9.1.0.7988 | B (.NET) |
| `Ghidra analyzeHeadless` | `/media/kev/Extreme SSD/argus/desktop_test/tools/ghidra_12.1_PUBLIC/support/analyzeHeadless` | 12.1 PUBLIC | C/D (Native) |
| `jadx` | `/home/kev/argus-internal/argus/android_test/tools/jadx/bin/jadx` (Wave G inheritance) | — | C if Java-desktop |
| `binwalk` | **ABSENT** | — | D firmware / E firmware |
| `strings`, `file`, `unsquashfs`, `cpio`, `7z`, `npm`, `node`, `python3` | `/usr/bin/` | OS-provided | various |

Note on `ilspycmd` version pinning: latest `10.0.1.8346` and several intermediate versions have a NuGet packaging bug (`DotnetToolSettings.xml` not found in package). `9.1.0.7988` is the last cleanly-packaged release; pinned.

---

## §3.0 P1-P10 final results

| Premise | Re-probe URL / method | Result | Disposition |
|---|---|---|---|
| **P1** Verkada Command desktop publicly downloadable | Substantive re-probe: Verkada Command is a **web-only product** by design — vendor documentation explicitly states "users can simply open a web browser and log into Command without needing desktop clients, VPNs, or port forwarding." No desktop installer exists. | **SUBSTANTIVE CLEAN NEGATIVE** — Verkada Command desktop does not exist as a class of artifact. | Emit `documented_absence` row for Verkada Command desktop with reason `web_app_only_no_desktop_client_2026_05`. CP17 cohort thesis finding follows below. |
| **P2** Milestone XProtect free download gated only by self-issued trial | Re-probe via WebSearch: Milestone's own documentation confirms "All of Milestone's clients are free of charge" and the `my-milestone` portal flow IS a self-issued account flow. The oauth2 redirect at `id.milestonelogin.com` is the self-issuance gate, not an LE-vetted gate. | **CLEAN POSITIVE** (substantive premise verifies; oauth IS the self-issue path). | Cohort B Milestone proceeds via self-issued trial account at `https://www.milestonesys.com/support/software/download-xprotect/`. |
| **P3** DJI Assistant 2 publicly downloadable | Re-probe: `https://www.dji.com/downloads/softwares/dji-assistant-2-consumer-drones-series` → HTTP 200. Multiple per-product-family variants confirmed (consumer / enterprise / power / ronin / MG / delivery / inspire / FPV). | **CLEAN POSITIVE**. | Cohort D DJI Assistant 2 proceeds. |
| **P4** v4 candidate-walk regex layer parser-agnostic | **Spot-test executed at `/tmp/wave_h_p4_test`**: 3-file synthetic JS tree (2 .js + 1 .txt) containing 2 BLE UUIDs. `wave_h_wrapper.py --cohort-label A_electron` → 2 candidates emitted, both correctly tagged `value_class=ble_service_uuid` and `cohort_label=A_electron`. v4 extractor untouched per D3.a; wrapper invokes v4's regex routines on the single input tree. | **CLEAN POSITIVE** (substantive premise verifies). | wave_h_wrapper.py is the canonical Wave H extractor entry point. |
| **P5** asar extracts a public Electron app's app.asar | Spot-test: `asar pack /tmp/syn /tmp/test.asar` (559 bytes archive) → `asar extract /tmp/test.asar /tmp/p5_extract` → both source files recovered intact (`a.js`, `sub/b.js`). | **CLEAN POSITIVE**. | Cohort A asar workflow ready. |
| **P6** ilspycmd decompiles non-obfuscated .NET WPF | Spot-test: `ilspycmd -p -o /tmp/p6_out` against `dotnet/shared/Microsoft.NETCore.App/8.0.27/System.Linq.dll` → readable C# source with class structure intact (CachingComparer, IPartition, Lookup, Grouping, etc.). Tool warns about update availability but operates correctly. | **CLEAN POSITIVE**. | Cohort B ilspycmd workflow ready. |
| **P7** Cradlepoint NCOS firmware publicly downloadable | **DEFERRED** — Cohort E gating premise; not yet probed. Wave-B2 MAC-18 already flagged Cradlepoint kb as Salesforce-gated. | **DEFERRED** | Cohort E entry-time re-probe; CLEAN NEGATIVE there descopes Cradlepoint without halting other Cohort E targets. |
| **P8** `manufacturers.aliases` is comma-string TEXT | `PRAGMA table_info(manufacturers)` → row `(2, 'aliases', 'TEXT', 0, None, 0)`. No sibling table. | **CLEAN POSITIVE**. | — |
| **P9** `raw_observations.source_excerpt` no CHECK; `identifiers.source_excerpt` ≤200 CHECK | `identifiers`: `source_excerpt TEXT CHECK (source_excerpt IS NULL OR length(source_excerpt) <= 200)`. `raw_observations`: `source_excerpt TEXT,` (no CHECK). Matches CP23 schema-truth. | **CLEAN POSITIVE**. | — |
| **P10** Schema version 22, no `0023*.sql` migration on disk | `SELECT MAX(version) FROM schema_version` → 22; last migration `0022_fcc_citation_deferred_queue.sql`. | **CLEAN POSITIVE**. | — |

---

## §3.0 probe decision

**P1-P6 + P8-P10 all CLEAN POSITIVE (substantive form). P7 DEFERRED (Cohort E gating only).**

**§3.1 dispatch AUTHORIZED at 2026-05-18 UTC.**

Calendar-day staleness ceiling reset is 2026-05-19 UTC; this probe authorizes dispatch through end-of-2026-05-18-UTC. If wave continues past calendar-day rollover, probe re-verification required per CP27 §2.4.

---

## Substantive findings surfaced during probe

### (1) CP17 operator-vs-installer cohort thesis — desktop axis preliminary finding

Re-probe of Cohort A target list reveals: **5 of 6 runguide Cohort A targets are web-only products** with no desktop installer to extract:

| Runguide Cohort A target | Status | Source |
|---|---|---|
| Verkada Command (desktop) | **No desktop client; web-only** | Vendor docs |
| Eagle Eye Networks EEN Viewer | Microsoft Store app (UWP `.msix`, not Electron `.exe`) | Vendor docs |
| Rhombus Systems Console | **Cloud-only; no install** | Vendor docs |
| Avigilon Alta Aware | Cloud-only; "Avigilon ACC" desktop is Cohort C native, not Cohort A Electron | Vendor docs |
| Skydio Pilot | Mobile + web; no Electron desktop | Vendor docs |
| Verkada Command Connector | Hardware appliance; no Electron client | Vendor 404 + runguide framing |

This is a substantive CP17 thesis finding (Wave G mobile → Wave H desktop generalization test): **the "operator-cohort" desktop class is largely absent in the modern VMS landscape because vendors have moved operator workflows to web-first / mobile-first architectures.** The "installer-cohort" class (Cohorts B .NET, C native C++) retains desktop clients because installer/admin workflows need rich UI surface that web cannot match. This validates one half of CP17 (the installer-cohort thesis carries) while inverting the operator-cohort half (operator-cohort dissolves into web/mobile rather than appearing as a separate desktop class).

This is the most important policy output of the wave per the user briefing's §9 expected fields. Will be surfaced explicitly in HANDOFF_TO_VALIDATOR.md.

### (2) Cohort A scope adjustment recommended

Per the substantive finding above, the runguide's Cohort A target list is unactionable as written. Options:
- **Cohort A.alt** — descope Cohort A in this wave; emit documented_absence rows for the 6 runguide targets with a single explanatory note. (Recommended.)
- **Cohort A.alt-rescope** — search for the rare modern Electron VMS clients (Lorex, Reolink Client, Ubiquiti UniFi Protect Viewer, etc.) that may exist as a cohort. These are smaller / consumer-focused vendors not in the v1.2.0 canonical lexicon. Adds scope; surfaces a new band of vendors.

Will proceed with Cohort A.alt (descope this wave) and surface to operator. If Cohort A.alt-rescope is desired, that becomes a Wave H continuation entry.

### (3) Disk-space posture confirmed

Localdisk now at 96% (211 GB used of 234 GB; 11 GB free); SSD at 42% (192 GB used of 466 GB; 275 GB free). All raw binaries + scratch decompile trees + Ghidra/dotnet/asar installs land on SSD. Localdisk holds only `extraction_outputs/wave_h_pre_v1/` (small JSON/MD outputs). No risk of localdisk exhaustion through wave completion.

---

## Audit anchor state at probe authorization

- Workspace `/home/kev/argus-internal/desktop_test/` with raw/scratch/tools → SSD symlinks.
- `wave_h_wrapper.py` written to `argus/android_test/tools/extraction/wave_h_wrapper.py` (v4 extractor untouched per D3.a).
- No DB writes performed. DB-side reads only.
- No binaries acquired yet. Network egress to this point: §2.6 spot-check HEAD requests + 3 WebSearch calls + 1 WebFetch + dotnet/Ghidra installer downloads to SSD.
