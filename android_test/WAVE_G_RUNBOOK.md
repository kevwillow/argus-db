# Wave G — Vendor Companion App Static Analysis Runbook

**Authority:** Board ratification at MAC-1 `ddc193cd` (2026-05-08T05:24:21Z).
Wave G plan landed at MAC-52. CP12 amendments live (`90132fa`).
MAC-53 child issue tracks the formal Paperclip-side execution; this
runbook drives the Claude Code pre-positioning session per Path A
sequencing override carved out at the user's discretion.

**Mission:** Static analysis of vendor companion Android APKs to extract
hardcoded surveillance-equipment identifiers (BLE service UUIDs, default
SSIDs, default credentials, MAC OUI validation patterns, product-family
taxonomy). Produces candidate findings for Paperclip Validator review.

**This session is DISCOVERY + EXTRACTION + CALIBRATION.**
**This session does NOT promote identifiers to Layer 1.**
**This session does NOT commit decompiled source to git.**

---

## 0. Critical hard rules (read first; binding throughout)

These are bible §11 hard rules. Violations halt the session.

- **§11 #1 — No fabrication.** Every extracted candidate must trace to a
  source file path + line + SHA256-anchored APK provenance. If you can't
  cite source, drop the candidate.

- **§11 #2 — No non-public data.** Only analyze APKs publicly available
  on Play Store, APKMirror, APKPure, or vendor-direct download. No
  pirated, leaked, or auth-gated binaries. DMCA §1201 + §201.40(b) cover
  static analysis of legally-acquired public binaries; scope stays
  inside that envelope.

- **§11 #6 — Robots/ToS posture.** APKMirror, APKPure, and vendor-direct
  download channels are clean. `gplay-api` is gray-zone for Google ToS;
  use only as last-resort fallback.

- **§11 #7 — source_excerpt cap (Option B-broad per CP17 ratify 2026-05-13).** Every candidate carries a `source_excerpt` field ≤200 characters verbatim from source. When the source line exceeds 200 characters (minified JS, obfuscated Kotlin, hybrid-app generated code, long config-line constants), capture a 200-char window centered on the matched value rather than dropping the candidate. Window-around-match applies regardless of file type. Each candidate carries an `excerpt_type` field disambiguating:

  - `full_line` — source line ≤200 chars; excerpt is the whole line verbatim.
  - `window` — source line >200 chars; excerpt is a 200-char window centered on the matched value with `match_offset_in_window` recorded (offset of the match start within the 200-char window).
  - `binary` — match in a binary file (rare; e.g., `.so` constant); excerpt is the hex-encoded 200-byte window centered on the match.
  - `other` — non-text source class not covered above (e.g., XMP metadata); excerpt-class annotated explicitly.

  The `excerpt_type` field is REQUIRED on every candidate, including `full_line` cases. This preserves audit-trail clarity and disambiguates the source-context-fidelity of each candidate's evidence. Fabrication discipline per bible §11 #1 still binds: every excerpt is verbatim from source (no paraphrase, no synthesis); the window-around-match relaxation widens the *source-line-length* permitted, not the *evidence-fidelity* required.

- **§11 #8 — NO promotion to identifiers.** Candidates land in JSON
  deliverables only. Paperclip Validator does promotion in the morning.
  Never write to `db/argus.db` `identifiers` table. Never run any code
  that mutates the database.

- **§11 #15 — No decompiled source in git.** Raw APKs at
  `raw/vendor_apps/<vendor>/<package>/<version>/<sha256>.apk` are
  gitignored (provenance-only). Decompile output is workspace-only and
  cleaned at end of run. Only candidate values + relative file paths
  land in candidate JSON.

- **Stop-the-line.** If you encounter ambiguity beyond what this runbook
  covers (new FP class, unexpected file shape, EULA hostility,
  authentication wall), halt and write a `STOP_THE_LINE.md` file in
  the deliverables directory describing what surfaced. Do not guess.

---

## 1. Working environment

**Host:** Linux Mint (apt-based; assume Mint 21.x or 22.x).

**Working directory:** `<repo>`

**Python venv:** `<repo>/venv`

If venv doesn't exist or doesn't have required packages, activate or
create:

```bash
cd <repo>
python3 -m venv venv 2>/dev/null
source venv/bin/activate
```

**Tooling installation (verify present, install if missing):**

```bash
# Java runtime (jadx requires JRE 11+)
java -version || sudo apt install -y default-jre

# jadx (Java/Kotlin decompiler) — install via release archive
which jadx || (
  cd /tmp
  wget -q https://github.com/skylot/jadx/releases/download/v1.5.0/jadx-1.5.0.zip
  unzip -q jadx-1.5.0.zip -d /tmp/jadx
  sudo cp -r /tmp/jadx /opt/jadx
  sudo ln -sf /opt/jadx/bin/jadx /usr/local/bin/jadx
)

# apktool (resource extraction)
which apktool || sudo apt install -y apktool

# androguard (programmatic APK analysis, Python)
pip show androguard >/dev/null 2>&1 || pip install androguard

# Standard utilities (almost certainly present)
which sha256sum unzip wget curl jq grep || sudo apt install -y \
  coreutils unzip wget curl jq grep
```

If any of these tool installs fail (network issue, permissions, etc.),
halt and write to `STOP_THE_LINE.md`. Don't proceed without working
tools.

---

## 2. Output directory structure

Create this layout at session start:
<repo>/
├── raw/
│   └── vendor_apps/                              # gitignored
│       └── <vendor>/<package>/<version>/<sha256>.apk
└── extraction_outputs/
└── wave_g_pre_v1/                            # session output root
├── manifest.json                         # session metadata
├── per_vendor/
│   └── <vendor>_<sha256_short>/
│       ├── apk_manifest.json             # SHA256 + version + source URL
│       ├── candidates.json               # extracted identifier candidates
│       ├── fp_findings.json              # FP class instances caught
│       └── analysis_log.md               # human-readable narrative
├── calibration/
│   ├── calibration_window_findings.md    # SAR-11 calibration narrative
│   ├── proposed_fp_classes.json          # SAR-11 candidate scope
│   └── disambig_module_recommendations.md
├── HANDOFF_TO_VALIDATOR.md               # what Paperclip needs to do next
└── STOP_THE_LINE.md                      # only if halt fires

Ensure `.gitignore` already excludes `raw/` and `extraction_outputs/`
appropriately. Verify before downloading any APK:

```bash
git check-ignore raw/vendor_apps/test.apk extraction_outputs/test.json
```

If either path is NOT ignored, halt and write to `STOP_THE_LINE.md`.

---

## 3. Vendor target list (20 Android-first priority)

Per CEO ratified plan + board sign-off. Cohort-ordered by expected
yield density:

**Cohort A — Surveillance-dominant single-product vendors (highest expected yield):**
1. Flock Safety — `com.flocksafety.sweetwater` (operator app) + `com.flocksafety.hazyhiwire` (installer app; primary BLE+identifier yield per Wave G macro thesis)
2. SoundThinking — `com.shotspotter.alerts` (formerly ShotSpotter Respondr; `com.shotspotter.respondr` is the legacy name)
3. Cellebrite — limited public Android footprint; Step 0 ground-truth (likely defer)

**Cohort B — Drone vendors (multi-app, high BLE/SSID density expected):**
4. DJI — `dji.go.v5` (DJI Fly), `dji.go.v4` (DJI GO 4), `com.dji.industry.pilot` (Matrice)
5. Skydio — `com.skydio.skydio` (Skydio app)
6. BRINC — `com.brinc.lemur` (LEMUR app, if available)
7. Parrot — `com.parrot.freeflight6`, `com.parrot.freeflight.pro`
8. Autel Robotics — `com.autelrobotics.explorer` (Autel Explorer; was previously listed as `com.autel.aaa` — different namespace)

**Cohort C — Body cam + LE-radio vendors:**
9. Axon — `com.evidence` (Axon Capture) + `com.evidence.flex` (Axon View) — both LE-only distribution (NOT on APKPure); **Axon View XL is Windows desktop**, not Android (prior `com.axon.viewxl` runbook entry was wrong)
10. Motorola Solutions — `com.motorolasolutions.wavepush` (LE-only), body-cam manager apps
11. WatchGuard — `com.watchguardvideo.v300mobile` (V300 mobile app; LE-only)
12. Getac — `com.getac.android.mobileappBWC` (Getac BWC Viewer; Step 0 resolved)
13. Reveal — body-cam companion (RS3-SX system uses desktop DEMS software; no public Android app found)

**Cohort D — Network + comms vendors:**
14. Cradlepoint — `com.cradlepoint.netcloud.manager` (NetCloud Manager; `.manager` suffix required)
15. Sierra Wireless — `com.sierrawireless.airvantage.mobile`
16. Hak5 — `org.hak5.pineappleconnector` (Pineapple Connector; Cloud C2 itself is desktop/web, not Android — prior `com.hak5.cloudc2` runbook entry was wrong)

**Cohort E — ALPR + camera systems:**
17. Genetec — `com.genetec.platformmobile` (Genetec Mobile; Step 0 resolved — was previously left as "Step 0 ground-truth")
18. Avigilon — `com.avigilon.acc_mobile` (ACC Mobile 3; underscore not camelCase — prior `com.avigilon.actcontrolcenter` runbook entry was wrong)
19. Rekor — companion app (Step 0 ground-truth)
20. Vigilant Solutions — companion app (Step 0 ground-truth)

For Cohort C/D/E vendors with "Step 0 ground-truth" notes, search
APKMirror first to confirm app exists. If no public Android app,
record in `manifest.json` under `vendor_unavailable_android` and skip
to next vendor.

**Vendor-unavailable-on-Android documentation (CP17 — Wave G pre-v1 evidence base 2026-05-10).** The Wave G pre-v1 calibration session confirmed 11 vendors unavailable on Android: BRINC (LEMUR uses custom controller; no public Android app exists), Skydio Enterprise (`com.skydio.enterprise` — APKPure delivered corrupt 4.5MB file with no EOCD ZIP marker; likely encrypted/protected for LE-only distribution; alt-channel scope-proposal worthwhile), Sierra Wireless (AirLink Registration mobile app exists but no public Android package found), Axon Capture (`com.evidence`) + Axon View (`com.evidence.flex`) (both LE-only), Axon View XL (Windows desktop, not Android — runbook entry was wrong), Motorola Solutions WavePush (`com.motorolasolutions.wavepush`; LE-only), WatchGuard V300 (`com.watchguardvideo.v300mobile`; LE-only), Reveal Media (RS3-SX system uses desktop DEMS software), Vigilant Solutions (no public Android app found), Parrot FreeFlight Pro (`com.parrot.freeflight.pro`; superseded by FreeFlight 6). Do NOT spend budget on unavailable vendors; document absence per bible §11 #1.

**Secret-scanning workflow (CP17 — added 2026-05-13).** Before any Wave G commit (or any commit broadly touching `android_test/extraction_outputs/`, `raw/wave_a/`, or vendor-app derivative artifacts), run the canonical secret-scanning pair:

```bash
# gitleaks — fingerprint-based FP allowlist via .gitleaksignore
gitleaks git --no-banner

# trufflehog — path-exclusion list via .trufflehogignore
trufflehog git file://. --exclude-paths=.trufflehogignore --no-update --json
```

Both `.gitleaksignore` (fingerprint allowlist) and `.trufflehogignore` (path-exclusion list) ship at repo root. Each entry carries a `# FP:` comment explaining the false-positive rationale per `feedback_strategic_steers.md` audit-trail discipline; reviewers distinguish FPs from accidentally-committed secrets via these comments. Both files were triaged at MAC-50 [comment `2714377b`] and board-ratified at MAC-59 [comment `b4d9afa0`]. A clean scan against these allowlists is a pre-commit checkpoint; failure to scan clean is a stop-the-line event per bible §11 #11 amendment-log discipline composition.

---

## 4. Per-vendor workflow

For each vendor in priority order, execute this workflow:

### 4.1 Discovery (Step 0)

1. Search APKMirror for the candidate package name(s) listed above
2. If found: record latest version + SHA256 from APKMirror's published
   manifest + download URL
3. If not found: try APKPure
4. If not found: try vendor-direct download (visit vendor.com, find
   any "download for Android" link)
5. If not found anywhere: record as `vendor_unavailable_android` and
   skip to next vendor
6. **Document EULA posture:** open the Play Store listing (or APKMirror
   metadata) and skim for hostile language toward reverse engineering
   or security research. If EULA explicitly prohibits reverse
   engineering AND the vendor is not high-yield-priority (Cohort A),
   skip and document. If hostile EULA + Cohort A vendor, halt and
   surface to STOP_THE_LINE.md for board judgment.

### 4.2 Download (Step 1)

```bash
mkdir -p raw/vendor_apps/<vendor>/<package>/<version>
cd raw/vendor_apps/<vendor>/<package>/<version>

# Download
wget -q "<download_url>" -O temp.apk

# Verify SHA256
sha256sum temp.apk
# Rename file to <sha256>.apk
mv temp.apk "$(sha256sum temp.apk | awk '{print $1}').apk"
```

Record in `extraction_outputs/wave_g_pre_v1/per_vendor/<vendor>_<sha256_short>/apk_manifest.json`:
- vendor name
- package name (e.g., `com.flocksafety.flockos`)
- version string
- download URL
- download timestamp UTC ISO 8601
- SHA256
- file size bytes
- channel used (APKMirror / APKPure / gplay-api / vendor-direct)
- EULA posture: clean / standard-RE-clause / hostile-but-included / hostile-and-skipped

### 4.3 Decompile (Step 2)

Decompile to a workspace directory. This is workspace-only; clean at
end of vendor processing.

```bash
WORKSPACE=$(mktemp -d /tmp/wave_g_decompile.XXXXXX)
cd "$WORKSPACE"

# jadx for Java/Kotlin source
jadx -d ./jadx_out "<repo>/raw/vendor_apps/<vendor>/<package>/<version>/<sha256>.apk" 2>jadx.log

# apktool for resources (strings.xml, AndroidManifest.xml)
apktool d "<repo>/raw/vendor_apps/<vendor>/<package>/<version>/<sha256>.apk" -o ./apktool_out 2>apktool.log

# androguard for programmatic AndroidManifest analysis (optional but useful)
python3 -c "
from androguard.core.bytecodes.apk import APK
apk = APK('<repo>/raw/vendor_apps/<vendor>/<package>/<version>/<sha256>.apk')
print('package:', apk.get_package())
print('main_activity:', apk.get_main_activity())
print('permissions:', apk.get_permissions())
"
```

If jadx fails (rare; usually obfuscation), document in analysis_log.md
and continue with apktool-only resource analysis. If both fail, skip
vendor with documented failure reason.

### 4.4 Extract (Step 2 continued)

Run extraction patterns over `jadx_out/` and `apktool_out/`:

#### Pattern set:

**A. 128-bit BLE service UUIDs:**
```bash
grep -rEn '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}' \
  jadx_out/ apktool_out/ > /tmp/ble_uuids.txt
```

**B. 16-bit BLE service UUIDs in BLE-service context:**
```bash
# Match patterns like 0xfd5a in code that mentions ParcelUuid / BluetoothGatt / ScanFilter
grep -rEn '(ParcelUuid|BluetoothGatt|ScanFilter|UUID).*0x[0-9a-fA-F]{4}' \
  jadx_out/ > /tmp/ble_short_uuids.txt
```

**C. Default SSID patterns (vendor-prefix WiFi names):**
```bash
# Vendor-prefix SSIDs in strings.xml + decompiled source
grep -rEn '"<vendor_prefix>[A-Za-z0-9_-]*"' apktool_out/res/values/strings.xml \
  jadx_out/ > /tmp/ssid_candidates.txt

# Common patterns: "Flock-XXXX", "Axon-Body-XXXX", "Cradlepoint-XXXX"
# Use vendor-specific prefix for targeted search
```

**D. MAC OUI validation patterns:**
```bash
# Hardcoded OUI validation (e.g. .startsWith("e4:aa:ea") or 0xe4aaea)
grep -rEn '"[0-9a-fA-F]{2}[:-]?[0-9a-fA-F]{2}[:-]?[0-9a-fA-F]{2}"' \
  jadx_out/ > /tmp/oui_candidates.txt
```

**E. Default credentials:**
```bash
# Common patterns: hardcoded "admin", "password", vendor-defaults
grep -rEn '("admin"|"password"|"admin123"|"<vendor>_default")' \
  jadx_out/ apktool_out/res/values/strings.xml > /tmp/cred_candidates.txt
```

**F. Product-family taxonomy:**
```bash
# Vendor-internal product names in strings + classes
grep -rEn 'Mavic|Inspire|Phantom|Matrice|Avata|Tello|Skydio|Lemur|Anafi' \
  jadx_out/ apktool_out/res/values/strings.xml > /tmp/taxonomy.txt
# (use vendor-appropriate model name list per vendor)
```

For each pattern hit:
- Extract the matched value
- Capture ≤200 chars verbatim source_excerpt (file path + line number + line content)
- Stage as candidate in `candidates.json`

### 4.5 Disambiguation pass

Apply FP filters BEFORE staging candidates. The `candidates.json`
output should ONLY contain candidates that survived disambig.

For BLE UUIDs, drop candidates matching any of these FP classes:

**A. Standard Bluetooth GATT service UUIDs (NEVER vendor-specific):**
00001800-0000-1000-8000-00805f9b34fb  # Generic Access
00001801-0000-1000-8000-00805f9b34fb  # Generic Attribute
0000180a-0000-1000-8000-00805f9b34fb  # Device Information
0000180f-0000-1000-8000-00805f9b34fb  # Battery Service
00001812-0000-1000-8000-00805f9b34fb  # HID
0000fe9f-0000-1000-8000-00805f9b34fb  # Google
0000fd5a-0000-1000-8000-00805f9b34fb  # Apple Find My

(Bluetooth SIG maintains the full registered list; any UUID matching
the `xxxxxxxx-0000-1000-8000-00805f9b34fb` template with a registered
short ID is a standard service, not vendor-specific.)

**B. Apple framework UUIDs:**
d0611e78-bbb4-4591-a5f8-487910ae4366  # Apple Continuity
9fa480e0-4967-4542-9390-d343dc5d04ae  # Apple Notification Center
7905f431-b5ce-4e99-a40f-4b1e122d00d0  # Apple ANCS

**C. Third-party BLE library UUIDs:**
6e400001-b5a3-f393-e0a9-e50e24dcca9e  # Nordic UART Service (NUS)
6e400002-b5a3-f393-e0a9-e50e24dcca9e  # Nordic UART RX
6e400003-b5a3-f393-e0a9-e50e24dcca9e  # Nordic UART TX
0000ffe0-0000-1000-8000-00805f9b34fb  # HM-10 / generic CC2541

**D. Build/test artifacts:**
- UUIDs found only in `*Test.java` or `__tests__` directories (drop)
- UUIDs in `BuildConfig.java` (usually app analytics IDs, not BLE; drop)
- UUIDs in Firebase/Crashlytics/Amplitude config files (drop)

For each FP-class hit, log in `fp_findings.json` with the FP class
name + UUID + source location. This is the SAR-11 calibration data.

### 4.6 Stage candidate

For each surviving candidate, write to
`extraction_outputs/wave_g_pre_v1/per_vendor/<vendor>_<sha256_short>/candidates.json`:

```json
{
  "vendor": "Flock Safety",
  "apk_sha256": "<full sha256>",
  "apk_package": "com.flocksafety.flockos",
  "apk_version": "<version>",
  "extraction_timestamp_utc": "<ISO 8601>",
  "candidates": [
    {
      "candidate_id": "<vendor>_<class>_<short_hash>",
      "candidate_class": "ble_service_uuid|ssid|credential|oui|product_family",
      "value": "<extracted value, normalized>",
      "source_file_relative": "jadx_out/com/flocksafety/.../FlockBLEService.java",
      "source_line": 142,
      "source_excerpt": "<≤200 chars verbatim>",
      "proposed_confidence_band": "80-95|70-85|60-80|75-90|90-95",
      "fp_filters_applied": ["standard_gatt_drop", "apple_framework_drop"],
      "vendor_proximity_signals": ["package_match", "class_name_match"]
    }
  ]
}
```

`proposed_confidence_band` per bible §8.2 manufacturer_app sub-banding:
- BLE service UUIDs: 80-95
- Default SSIDs: 70-85
- Default credentials: 60-80
- MAC OUI from validation: 75-90
- Product-family taxonomy: 90-95

These are **proposed**; Paperclip Validator finalizes confidence at
promotion time.

### 4.7 Cleanup

```bash
# Clean workspace; raw APK stays at raw/vendor_apps/ for provenance
rm -rf "$WORKSPACE"
```

---

## 5. Calibration window protocol (CRITICAL)

**The first 2 vendors fully processed are the calibration window.**

After Cohort A vendors 1 + 2 are fully processed (Flock Safety +
SoundThinking, ideally), STOP and analyze the FP findings before
proceeding to vendor 3.

Calibration analysis:

1. Read all `fp_findings.json` files from the first 2 vendors
2. Categorize FP classes encountered:
   - Already covered by FP filter set in §4.5? Document as "filter
     working as designed"
   - Novel FP class not in the §4.5 set? Document as **SAR-11
     candidate scope**
   - Edge case requiring judgment? Document as "stop-the-line for
     Validator review"
3. Update `extraction_outputs/wave_g_pre_v1/calibration/proposed_fp_classes.json`
   with novel classes found
4. Add new FP filter rules to a working draft module at
   `extraction_outputs/wave_g_pre_v1/calibration/proposed_disambig_additions.py`
   (don't write to `db/extraction/`; that's Validator territory in the
   morning)
5. **If novel FP classes were found:** apply the new filters
   retroactively to vendors 1 + 2 candidates before continuing. Update
   `candidates.json` files accordingly.
6. **If kill-switch criteria fire** (0 candidates after disambig
   across both calibration vendors), HALT. Write to STOP_THE_LINE.md.
   Don't proceed to vendor 3.
7. **If calibration looks healthy** (some real candidates surviving,
   FP filters catching noise as expected), proceed with cohort A
   vendor 3 onward.

---

## 6. Stop-the-line triggers

Halt session and write `STOP_THE_LINE.md` if any of these surface:

- Tooling install failed (couldn't get jadx/apktool/androguard working)
- APK download failed for >50% of attempted vendors (network/access issue)
- Cohort A calibration window kill-switch fires (zero candidates after disambig)
- Hostile EULA on Cohort A vendor (Flock/SoundThinking)
- Authentication wall preventing analysis (e.g., APK requires logged-in
  account to even start; no static analysis possible)
- Disk space concern (<5 GB free)
- Any §11 hard rule violation surfaces
- Confusion about whether candidate is novel surveillance ID vs
  generic library artifact (better to halt and let Validator decide
  than guess)

`STOP_THE_LINE.md` format:

```markdown
# STOP_THE_LINE — Wave G pre-v1 session

## What surfaced
<Brief description of what caused halt>

## State at halt
- Vendors completed: <list>
- Vendors in progress: <list>
- Candidates staged so far: <count>
- FP findings logged so far: <count>

## Recommended Validator action
<What Paperclip should do when reviewing in the morning>

## Files written
<List of deliverable files at halt>
```

---

## 7. Time/scope budget

This session targets ~8 hours of execution. Realistic per-stage
estimates:

- **Tooling setup + verification:** 15-30 min
- **Per-vendor full workflow (Steps 0+1+2 + disambig + stage):**
  20-45 min depending on app size + decompilation complexity
- **Calibration analysis (after vendors 1+2):** 30-45 min
- **Total for 20 vendors:** 7-15 hours theoretical

**Realistic 8-hour scope: process Cohort A + B + C completely (~13
vendors) + start Cohort D.** Don't push to finish all 20 if quality
suffers. Better to deliver 13 high-quality vendor analyses than 20
rushed.

If you hit an 8-hour wall and Cohort D + E are incomplete, that's
fine. Update `manifest.json` with completion state and write a
clean `HANDOFF_TO_VALIDATOR.md` reflecting actual coverage.

---

## 8. Final handoff package

At end of session (whether complete, partial, or stopped), produce
`extraction_outputs/wave_g_pre_v1/HANDOFF_TO_VALIDATOR.md`:

```markdown
# Wave G pre-v1 Validator handoff

## Session summary
- Start: <UTC ISO 8601>
- End: <UTC ISO 8601>
- Wall-clock duration: <hours>

## Coverage
- Vendors processed: X / 20
- Vendors with candidates: Y
- Vendors with no candidates (absence-documented): Z
- Vendors unavailable on Android: W
- Vendors halted on EULA: V

## Candidate totals (pre-Validator review)
- BLE service UUIDs: <count>
- Default SSIDs: <count>
- Default credentials: <count>
- MAC OUI patterns: <count>
- Product-family taxonomy entries: <count>

## SAR-11 calibration findings
- FP classes confirmed (already in §4.5 filter set): <count>
- FP classes novel (proposed SAR-11 scope): <count>
  - List with proposed disambig logic
- FP classes ambiguous (Validator review needed): <count>

## Recommended Validator next steps
1. Review proposed_fp_classes.json + proposed_disambig_additions.py
2. Codify SAR-11 if novel FP classes warrant it
3. Apply Validator promotion gate (§11 #8) per candidate
4. Surface findings to CEO for ratification + Layer 1 promotion
5. Update DATA_DICTIONARY.md with new manufacturer_app sub-banding
   evidence

## Files produced
- <list of all per-vendor candidates.json + fp_findings.json + analysis_log.md>
- calibration/ deliverables
- raw/vendor_apps/ APK files (provenance)

## Stop-the-line events
- <list any halts that surfaced during session>

## Notes for board
- <anything unexpected, edge case, or judgment call worth surfacing>
```

---

## 9. What this session does NOT do

Explicit non-goals (don't accidentally do these):

- **Do not write to `db/argus.db`.** No `INSERT`, no `UPDATE`, no
  schema changes. Read-only or no DB access at all.
- **Do not commit anything to git.** Decompile output is workspace-only.
- **Do not promote candidates to Layer 1.** Validator does that with
  §11 #8 discipline in the morning.
- **Do not codify SAR-11 in BIBLE_AMENDMENTS.md.** That's a CP-class
  edit; Paperclip CEO + board ratify in the morning.
- **Do not extend the bible.** Only Validator-or-CEO-or-board edits
  bible artifacts.
- **Do not run iOS / IPA extraction.** Wave G is Android-first per
  ratified scope; iOS is Wave G.5 / Phase 7 deferred.
- **Do not contact vendors directly.** Static analysis only.
- **Do not download APKs from sketchy mirrors.** APKMirror, APKPure,
  vendor-direct only.
- **Do not push past kill-switch.** If calibration window trips,
  halt.

---

## 10. References

- MAC-1 Wave G ratification: comment `ddc193cd` (2026-05-08T05:24:21Z)
- MAC-52 Wave G plan document (full CEO scope)
- MAC-53 Wave G Step 0 backlog issue (formal Paperclip dispatch container)
- CP12 bible amendment commit `90132fa`
- Bible §8.2 manufacturer_app confidence bands
- Bible §11 #15 decompiled-source-no-commit rule
- Bible §12 Wave G open questions (DMCA / EULA / iOS)
- This runbook lives at `<repo>/WAVE_G_RUNBOOK.md`

---

## 11. End-of-session checklist

Before declaring session done:

- [ ] Tooling installed and verified
- [ ] Output directory structure created
- [ ] APK manifests produced for all attempted vendors
- [ ] Candidates JSON produced for vendors with hits
- [ ] FP findings JSON produced for all vendors
- [ ] Calibration analysis completed (or halt documented)
- [ ] proposed_fp_classes.json written (even if empty)
- [ ] HANDOFF_TO_VALIDATOR.md written
- [ ] Workspace decompile directories cleaned (`/tmp/wave_g_decompile.*` removed)
- [ ] Raw APKs preserved at `raw/vendor_apps/` (gitignored)
- [ ] No git index changes (verify with `git status`)
- [ ] No DB writes (verify `db/argus.db` mtime unchanged)
- [ ] STOP_THE_LINE.md written if halt fired

End of runbook.
