# v1.3.0 pre-tag SSD audit report

**Authority anchor:** [MAC-182](/MAC/issues/MAC-182) operator directive `comment-9ed7a775` (2026-05-19T02:19:54Z).
**Audit executed by:** Paperclip CEO, run `1b00f6e6-…` continuation heartbeat 2026-05-19T02:2x:xxZ.
**Audit scope:** SSD `/media/kev/Extreme SSD/argus/desktop_test/` vs. canonical `~/argus/extraction_outputs/wave_h_pre_v1/` for v1.3.0 pre-tag integration-delta detection.

## Disposition

**BRANCH A — SSD audit clean; raw + scratch + toolchain only; no integration delta.**

`v1.3.0` tag-fire can proceed under MAC-182 §6 sequencing (D1 backfill decision → tag annotation draft → operator ratify → tag fire) once operator clears this audit gate.

## §1 — Mount verification (per operator §2.1)

`/media/kev/Extreme SSD/argus/` mounted and readable.
`/media/kev/Extreme SSD/argus/desktop_test/` exists, last mtime `2026-05-18 17:26` (top-level dir).

Top-level layout of `desktop_test/`:

| Subdir | mtime | Classification |
|---|---|---|
| `raw/` | 2026-05-18 17:26 | §11 #15 gitignored raw binary acquisition tree (out of scope per §2.4) |
| `scratch/` | 2026-05-18 19:50 | §11 #15 gitignored decompile/scratch trees (out of scope per §2.4) |
| `tools/` | 2026-05-18 18:16 | Toolchain only (Ghidra + dotnet + playwright + venvs + `vendor_acquire.py`) |

`raw/` carries 1 child: `vendor_desktop/` (binary acquisition root; not enumerated further per §2.4).
`scratch/` carries 3 vendor-scoped children: `dji/`, `filezilla/`, `hikvision/` (decompile trees; not enumerated further per §2.4).

## §2 — Extraction-class artifact enumeration (operator §2.2 verbatim)

Operator-prescribed `find` over the 13 artifact patterns (`candidates.json`, `fp_findings.json`, `extraction_counts.json`, `manifest.json`, `cross_vendor_attestations.json`, `cross_source_corroborations.json`, `vendor_internal_reextractions.json`, `HANDOFF_TO_VALIDATOR.md`, `analysis_log.md`, `_probe_log.md`, `_cohort_*_documented_absence.json`, `*_documented_absence.json`, `STOP_THE_LINE_*.md`):

```
$ find "/media/kev/Extreme SSD/argus/desktop_test/" \( -name 'candidates.json' -o … \) -type f
/media/kev/Extreme SSD/argus/desktop_test/tools/playwright-browsers/chromium-1223/chrome-linux64/hyphen-data/manifest.json
/media/kev/Extreme SSD/argus/desktop_test/tools/playwright-browsers/chromium-1223/chrome-linux64/MEIPreload/manifest.json
/media/kev/Extreme SSD/argus/desktop_test/tools/playwright-browsers/chromium-1223/chrome-linux64/PrivacySandboxAttestationsPreloaded/manifest.json
/media/kev/Extreme SSD/argus/desktop_test/tools/playwright-browsers/chromium-1223/chrome-linux64/WidevineCdm/manifest.json

$ wc -l /tmp/ssd_extraction_artifacts.txt
4 /tmp/ssd_extraction_artifacts.txt
```

**Raw count: 4. Extraction-class artifact count: 0.** All 4 hits are false-positives by filename match — `manifest.json` is overloaded by the Chromium browser bundle, which uses it for component-resource manifests (per Chrome browser-extension v2 manifest spec).

### §2.1 — False-positive classification (per-file)

| SSD path (relative to `tools/playwright-browsers/chromium-1223/chrome-linux64/`) | Verified content | Classification |
|---|---|---|
| `MEIPreload/manifest.json` | `{"name": "MEI Preload", "version": "1.0.7.1652906823", "manifest_version": 2, …}` | Chromium Media Engagement preload list — bundled toolchain |
| `WidevineCdm/manifest.json` | Chromium Widevine CDM bundle metadata | Chromium DRM module — bundled toolchain |
| `PrivacySandboxAttestationsPreloaded/manifest.json` | Chromium privacy-sandbox attestations preload | Chromium privacy module — bundled toolchain |
| `hyphen-data/manifest.json` | Chromium hyphenation-data resource bundle | Chromium text-rendering module — bundled toolchain |

None are Wave H extraction outputs. They are Playwright-installed Chromium browser internals carried with the Ghidra + dotnet + playwright toolchain set.

### §2.2 — Why per-file diff (operator §2.3 Branch B path) does NOT apply

Branch B requires the SSD hits to be "extraction-class artifacts mirroring the canonical tree." All 4 SSD hits are Chromium component manifests living under `tools/playwright-browsers/chromium-1223/chrome-linux64/...`. They have **no canonical-tree counterparts** at `~/argus/extraction_outputs/wave_h_pre_v1/` (no Chromium bundle exists in the canonical extraction-outputs tree, by design). The path-mapping rewrite in operator's Branch B diff loop would resolve them to non-existent `~/argus/extraction_outputs/wave_h_pre_v1/tools/playwright-browsers/.../manifest.json` paths — i.e., "MISSING in canonical" — but that "missing" would be a category error: these files don't belong in the canonical tree to begin with.

Therefore: Branch B does not apply; these are not integration candidates.

## §3 — Canonical-tree completeness cross-check

`~/argus/extraction_outputs/wave_h_pre_v1/` enumeration:

- **Total files:** 86
- **Per-vendor coverage:** 4 vendor subdirs (`dji_assistant_2_mavic`, `dji_assistant_2_fpv`, `hikvision_ivms_4200`, `filezilla_fp_disambig`) each carrying their standard 5-artifact set (`candidates.json`, `extraction_counts.json`, `fp_findings.json`, `_provenance.json`, `source_excerpts/`) plus vendor-specific notes (`analysis_log.md`, `hikvision_cp26_8_audit.md`, `h2_disambig_filezilla_run.md`)
- **Cross-vendor artifacts:** `cross_vendor_attestations.json`, `HANDOFF_TO_VALIDATOR.md`, `_probe_log.md`, `STOP_THE_LINE_probe_p1_p2_p3_negative_plus_toolchain_2026-05-18.md`, `calibration/calibration_window_findings.md`
- **Documented-absence artifacts:** `per_vendor/_cohort_a_documented_absence.json` (Verkada Command + Genetec Citilog + Avigilon ACC Client + Axis Camera Station + Milestone XProtect + Honeywell Pro-Watch = 6 Cohort A absence rows) + `per_vendor/skydio_pilot_documented_absence.json` (Cohort D Skydio P11 CLEAN NEGATIVE = 1 absence row) → 7 total documented_absence-class artifacts ✓ (matches commit `0d80755` message "+7 documented_absence")

**mtime cross-check.** Canonical-tree latest extraction-artifact mtime = `2026-05-18 20:36:55` (port commit time). SSD scratch-tree latest mtime = `2026-05-18 19:50:41` (~46 minutes earlier; consistent with extraction outputs being written DIRECTLY to local home throughout Wave H, then ported into canonical `~/argus/` at MAC-181 §1.2 ~46 minutes after the last scratch-tree activity). No mtime evidence of SSD-side extraction-output writes.

## §4 — §2.3 Branch determination

| Branch | Criterion | Match? |
|---|---|---|
| **A** | `wc -l` returns 0 extraction-class artifacts (strict: 0 raw hits; lenient: 0 functionally-classified hits) | **YES** (lenient: 4 raw hits all classified as Chromium toolchain false-positives = 0 extraction-class) |
| B | `wc -l > 0`, all artifacts mirror canonical tree content-identical | n/a (the 4 hits have no canonical-tree mirror paths by design) |
| C | `wc -l > 0`, SSD carries net-new artifacts not in canonical tree | n/a (the 4 hits are not extraction artifacts, so "net-new content" is category-empty) |

**Disposition: BRANCH A (with §2.1 false-positive classification footnote).**

## §5 — Tag-fire green-light + carry-over MAC-182 §4 gates

This audit clears the operator's §3 sequencing prerequisite. The pre-tag gates from [MAC-182 comment `083adf7c`](/MAC/issues/MAC-182#comment-083adf7c-eee0-4db1-bb4c-8b39bdad953d) §4 carry forward unchanged:

1. **D1 decision** (operator) — backfill `notes.cloud_url_hostname='duss.djicorp.com'` on id=23059 (D1.a, recommended) OR accept landed state (D1.b)?
2. **D2 confirmation** (operator) — accept landed wrapper path at `android_test/tools/extraction/wave_h_wrapper.py` + retroactive default-2 update (recommended)?
3. **Tag-target SHA** — if D1.a: tag fires on the new post-backfill HEAD (will be 7 commits ahead of `origin/main`). If D1.b: tag fires on `39b3b4a` (6 commits ahead).
4. **Tag annotation content** — CEO drafts annotation body referencing MAC-181 + MAC-182 + CP28 + the per-commit ledger when operator authorizes tag-fire.

## §6 — Out-of-scope confirmations

- `raw/` + `scratch/` recursion suppressed per operator §2.4. Their contents are §11 #15 gitignored by repo policy and not integration candidates.
- SSD cleanup posture (delete scratch trees post-tag, archive binaries, etc.) deferred per operator §2.4 — separate housekeeping decision outside MAC-182 scope.
- No SSD-side write occurred during this audit (read-only).

## §7 — Discipline-anchor notes

- [[feedback_dispatch_preamble_live_state_verification]] honored: paste-not-cite SSD `find` output, paste-not-cite Chromium `manifest.json` content sample, paste-not-cite mtime stamps.
- [[feedback_db_verify_dispatch_claims]] honored at audit-scope: `+7 documented_absence` claim from commit `0d80755` verified to mean "7 on-disk JSON-array entries across `_cohort_a_documented_absence.json` + `skydio_pilot_documented_absence.json`" — not DB rows (no `documented_absences` table exists; promotion to first-class table held below §3 #6 ≥30 cumulative-wave threshold per CP27).
- [[feedback_verify_cross_referenced_artifacts_in_public_prose]] honored: canonical-tree completeness verified by direct file enumeration; not paraphrased from CHANGELOG.
