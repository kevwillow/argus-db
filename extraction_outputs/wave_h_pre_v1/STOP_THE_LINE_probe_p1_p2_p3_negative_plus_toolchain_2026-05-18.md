# STOP THE LINE — Wave H §3.0 probe halt + §2.4 toolchain halt

**Date UTC:** 2026-05-18
**Wave:** H pre-v1 — desktop setup-app static-analysis extraction
**Runguide:** `new data 5.18/wave_h_desktop_setup_app_runguide.md`
**Halt authority:** runguide §5 #1 (§2 precondition fail), §5 #2 (§3.0 CLEAN NEGATIVE on P1-P6 / INCONCLUSIVE)

## Halt reasons (composed)

### (1) §2.4 toolchain absence — operator disposition required

Four cohort-required tools absent from the system:
- `asar` (Cohort A Electron) — `npm install -g @electron/asar` (~10 MB)
- `dotnet` + `ilspycmd` (Cohort B .NET, F sanctioned-vendor, partial G) — dotnet SDK ~700 MB or runtime ~80 MB + ilspycmd ~30 MB
- `binwalk` (Cohorts D drone-tooling, E firmware, C native) — apt package ~30 MB, **requires sudo**
- `Ghidra` (Cohorts C native, D drone-tooling) — ~1 GB

Localdisk at 96% utilization (11 GB free). Extreme SSD at 41% (276 GB free, mounted `/media/kev/Extreme SSD`). Operator has pre-authorized SSD-staging for raw + scratch data; tooling install location requires explicit operator disposition (SSD vs localdisk — sudo apt installs to system paths regardless).

### (2) §3.0 CLEAN NEGATIVE on P1, P2, P3 — URL staleness

| Premise | URL probed | Result |
|---|---|---|
| P1 Verkada Command desktop | `https://www.verkada.com/command/desktop/` | HTTP/2 404 (Cloudflare) |
| P2 Milestone XProtect free download | `https://www.milestonesys.com/downloads/` | 302 → oauth2 challenge BEFORE product listing |
| P3 DJI Assistant 2 publicly downloadable | `https://www.dji.com/downloads/softwares/dji-assistant-2-for-mavic` | HTTP/2 404 (sub-path stale) |

The underlying empirical premises (these vendors publicly distribute desktop apps; Milestone uses self-issued trial; DJI Assistant 2 exists and is publicly downloadable) are likely still true at different URLs — the runguide URLs are stale. Per CP27 §2.4 discipline, literal-URL CLEAN NEGATIVE is a halt requiring operator disposition: re-author runguide with current URLs vs. authorize "search-for-current-URL per premise" fallback discipline.

### (3) §3.0 CANNOT VERIFY on P5, P6 — treated as INCONCLUSIVE

`asar` and `ilspycmd` absent → cannot run the P5/P6 spot-tests. These resolve automatically once §2.4 toolchain disposition is settled.

### (4) §3.0 P4 partial-positive — wave_g_extractor CLI surface

Regex layer is parser-agnostic (per the substantive premise of P4); CLI surface is APK-specific (`--jadx-out` + `--apktool-out` required). Runguide §3.3 invocations reference `--input-tree` / `--extractor-mode` which do not exist. Two operator-disposition options below.

---

## Decisions requested

### D1 — Toolchain install posture

Per runguide §2.4: *"operator decides whether to install (in-scope) or descope that cohort."*

Options:
- **D1.a — Install all four tools** to enable all cohorts. Install `asar` via `npm install -g` (user-local), `ilspycmd` via `dotnet tool install --global` (requires dotnet SDK install — to SSD), `binwalk` via `apt` (system path, requires sudo), `Ghidra` extracted to SSD `/media/kev/Extreme SSD/argus/desktop_test/tools/ghidra/`.
- **D1.b — Install Cohort-A only** (`asar`) and start with the Electron cohort (highest expected yield per runguide §3.1 commentary). Defer .NET / native / firmware cohorts to a follow-on session.
- **D1.c — Descope per-cohort to the minimum-tooling subset** that runs with present tools alone. With only `jadx` + `strings` + `unsquashfs` + `cpio` + `7z` present, the only fully-tooled cohort would be a hypothetical Java-desktop cohort — but Wave H §3.1 has no pure Java-desktop cohort. Effectively, **no cohort is runnable without at least one new install**. So D1.c is functionally equivalent to "abort wave."

### D2 — Runguide URL staleness fallback discipline

Per CP27 §2.4 + §3.0 decision rule (literal-URL CLEAN NEGATIVE → halt; CEO disposition).

Options:
- **D2.a — Authorize "search-for-current-URL per premise" fallback discipline.** I will re-probe each premise by locating the current public download/landing page for the vendor product (via vendor.com root → site search, or via a known-current archive snapshot), and only declare CLEAN NEGATIVE if the substantive premise (public downloadability) fails. The runguide's specific URLs become non-binding; the named premises bind.
- **D2.b — Re-author the runguide with current URLs**, then re-probe in a follow-on session. Cleaner audit trail; more turnaround.

### D3 — wave_g_extractor.py CLI adapter

Per runguide §3.3 note: *"If the operator prefers to leave the v4 extractor untouched, set the cohort label at the staging-aggregation step instead."*

Options:
- **D3.a — Leave v4 extractor untouched; add a Wave H wrapper script** at `argus/android_test/tools/extraction/wave_h_wrapper.py` that accepts `--input-tree` + `--cohort-label`, then invokes the v4 extractor's regex routines directly against the single tree (or passes the same tree to both `--jadx-out` and `--apktool-out` since `iter_candidate_files` walks both roots and is tolerant to overlap). The cohort label is set at the wrapper's emit step.
- **D3.b — Add `--input-tree` / `--extractor-mode` flags to v4 extractor.** Touches the v4 extractor as a side effect of Wave H (more invasive). Risk: future Wave G re-runs need re-validation.

---

## Recommendation (extraction-side; non-binding)

- **D1.a** (install all four tools, SSD-targeted where possible) — Wave H's value-add is cross-cohort coverage; running Cohort A alone surfaces only the Electron yield-band and misses the cohort thesis generalization test.
- **D2.a** (search-for-current-URL fallback discipline) — runguide URL staleness is an authoring drift, not a substantive premise failure; the premises are testable.
- **D3.a** (wrapper script, v4 untouched) — preserves Wave G audit trail.

Awaiting operator disposition.

---

## State at halt (audit anchor)

- Workspace `desktop_test/` created at `/home/kev/argus-internal/desktop_test/` with raw/scratch/tools symlinked to SSD.
- No binaries acquired, no DB writes, no extraction outputs beyond this STOP_THE_LINE + `_probe_log.md`.
- DB-side preconditions all pass (§2.3 net-new admission, §2.5 schema=22, P8/P9/P10 schema-truth corrections all CLEAN POSITIVE).
