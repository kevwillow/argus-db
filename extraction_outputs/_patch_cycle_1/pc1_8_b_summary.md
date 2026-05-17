# Patch Cycle 1.8.B — In-Repo Summary

**Trigger:** PC1.8.A bulk re-fire halted at JAAPW1008 on §6 #8 PII surfacing (16 hits: 3 real Motorola contact items + 5 dupes + 10 false positives). Diagnostic showed the load-bearing issue was framing: §6 #8 was originally written for *exceptional* PII surfaces (test-report engineer signature blocks suggesting wrong-version download); the §3-prep summary extended it to HTML index pages where PII is *structural* (every fccid.io filing page renders FCC EAS compliance-contact block by regulator design). Halting on every grantee made the run infeasible.

**Applied:** 2026-05-17.
**Dispatch:** MAC-101.

---

## Patches landed

### In-repo (this commit)

| Change | Scope |
|---|---|
| `scripts/mac101_fccid_pull.py` — drop `scan_for_pii` call from `process_one_filing` | Patch 1.8.B.1 |
| `scripts/mac101_fccid_pull.py` — add `pii_strip_excerpt` + `PII_STRIP_PATTERNS` for §4.5 | Patch 1.8.B.2 (code side) |
| `scripts/mac101_fccid_pull.py` — enumeration-state persistence (`enumeration_state.json` load/save shortcut around Phase 1+2) | PC1.8.B Step 4 resume mechanic |
| `scripts/mac101_fccid_pull.py` — `bulk_run_stream_b_zero_yield` manifest flag stamping | Patch 1.8.B.5 |

### Out-of-tree (operator staging at `new data 5.17/fccid_io_admission_runguide.md`)

| Patch | Anchor |
|---|---|
| 1.8.B.2 — new §4.5 source_excerpt PII-strip pass | inserted between §4.4 and §5 |
| 1.8.B.3 — §6 #8 framing clarification (PDF-only; HTML out-of-scope) | replaced §6 #8 statement |

### Documentation (gitignored under `extraction_outputs/fccid_io_admission/`)

| Patch | Artifact |
|---|---|
| 1.8.B.4 — JAAPW1008 disposition | `_pc1_8_b_disposition.md` |
| 1.8.B.5 — Stream B 0/14 wave-level data point | `_pc1_8_b_disposition.md` + manifest flag |
| 1.8.B.6 — Rejected alternatives (Options B/C/D) | logged inline in patch doc; no separate artifact |

---

## §4.5 smoke test (PC1.8.B Step 2) — PASSED

Synthetic excerpt: `"BLE service UUID 12345678-1234-1234-1234-123456789ABC. For technical inquiries contact chuck.powers@motorolasolutions.com or call 202-371-6904."`

Redacted output: `"BLE service UUID 12345678-1234-1234-1234-123456789ABC. For technical inquiries contact <REDACTED_EMAIL> or call <REDACTED_PHONE>."`

Counts: `{email: 1, phone_us: 1, phone_intl: 0, badge_id: 0, total: 2}` — matches dispatch expectation exactly.

Edge-case probes all behaved reasonably:
- UUID preserved
- Template placeholder email redacted (defensive)
- International phone format redacted via `phone_intl`
- Badge ID redacted
- Cookie-style 10-digit numeric (`pub_site.1779056618`) correctly NOT redacted (strict area-code regex skips non-phone numerics)
- Toll-free phone digits stripped (cosmetic: leading `1-` country code preserved; no PII leak)

No edge cases warrant PC1.9 surface.

---

## Stream B 0/14 calibration data (PC1.8.B.5)

Empirical from PC1.8.A bulk_run.log: **all 14 zero-EAS-match vendors returned 0 grantee codes**. Stamped to manifest:

```json
"bulk_run_stream_b_zero_yield": true,
"bulk_run_stream_b_zero_yield_evidence": [
  "BRINC: 0", "Berla: 0", "BriefCam: 0", "Cellebrite: 0", "Clearview AI: 0",
  "DroneShield: 0", "Engility: 0", "Genetec: 0", "Hak5: 0", "Magnet Forensics: 0",
  "Rekor: 0", "Septier: 0", "SoundThinking: 0", "Vigilant Solutions: 0"
]
```

Wave-level carry-forward: MAC-102 ISED Stream B will face the same OEM-module reality. PC1.8.B-equivalent calibration footnote recommended before MAC-102 fires.

---

## Resume preparation

**Enumeration state reconstructed from cached HTMLs** (no network): `enumeration_state.json` populated with all 2440 unique FCC IDs by re-parsing the 48 cached `raw/fccid_io/{grantee}_index.html` files with PC1.8.A's fixed regex. Reconstruction matches PC1.8.A bulk_run.log's "Phase 1+2 complete: 2440 unique FCC IDs in scope" exactly.

When the next bulk-run fires, `run_bulk` detects `enumeration_state.json` and skips Phase 1+2 (~13 min saved). Phase 3 begins immediately.

Top-5 grantees by FCC ID count (from reconstruction):
- `AZ4` Motorola Solutions: 660
- `ABZ` Motorola Solutions: 659
- `SS3` DJI Technology: 210
- `N7N` Sierra Wireless: 195
- `QYL` Getac: 164

These 5 grantees alone account for ~75% (1888/2440) of the dispatch scope. Wall-clock projection at observed smoke-test pace (~5-10 sec per FCC ID) suggests Phase 3 will likely trigger the 2h canary (<40% completion) or the 4h 43m hard cap before completing the full 2440. Partial-deliverable disposition expected at §3→§4 CEO check-in.

---

## Verification

```
grep -c '§6 #8 PII surfaced on fccid.io HTML' scripts/mac101_fccid_pull.py  →  0  (HTML halt removed)
grep -c 'def scan_for_pii'                     scripts/mac101_fccid_pull.py  →  1  (definition retained)
grep -c 'scan_for_pii('                         scripts/mac101_fccid_pull.py  →  1  (definition only; no call sites)
grep -c 'def pii_strip_excerpt'                 scripts/mac101_fccid_pull.py  →  1  (§4.5 fn present)
grep -c 'enumeration_state_path'                scripts/mac101_fccid_pull.py  →  5  (load + save mechanics)
grep -c 'bulk_run_stream_b_zero_yield'          scripts/mac101_fccid_pull.py  →  2  (manifest stamp logic)
```

Runguide:
- `§4.5 — source_excerpt PII-strip pass (NEW: PC1.8.B)` present
- `§6 #8` updated to "PII surfacing in PDF documents" with HTML-out-of-scope clarification

---

## Next step

PC1.8.B Step 4: re-fire bulk run. Phase 1+2 skipped via cached `enumeration_state.json`; Phase 3 begins with 2440 FCC IDs in scope. Halt criteria active (2h canary, 12 GB storage, 4h 43m hard cap, §6 #5e queue integrity). §6 #8 reframed to PDF-only — won't trip on HTML again.
