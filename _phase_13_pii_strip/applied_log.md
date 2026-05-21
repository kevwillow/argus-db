# MAC-217 §8.2 PII-strip — applied log

**Dispatch:** [MAC-217](/MAC/issues/MAC-217) — §8.2 PII-strip + MAC-209 export re-fire (DBArchitect)
**Branch:** `v1.4.1-integration-stage-1`
**Predecessor commit:** `bb7ec17` (MAC-216 §8.1 Phase 5 wave_i_12 close)
**Applied at (UTC):** `2026-05-21T14:23:34Z`
**Board approval:** [`8a2ac74d-1397-4fb9-9605-a068ab29131f`](/MAC/approvals/8a2ac74d-1397-4fb9-9605-a068ab29131f) via [MAC-184 comment `52b916e1`](/MAC/issues/MAC-184#comment-52b916e1-398e-4b48-a049-a08b0e1e7519)
**CEO revised dispatch:** [MAC-217 comment `668ed6b8`](/MAC/issues/MAC-217#comment-668ed6b8-9584-4b7c-94ba-3c9336f1973f)
**Backup:** `db/argus.db.mac217_pre_pii_strip_backup` sha256 `8c21dd2caee353578e961d1d3d3f215156c7da72eb8dbebb4e05523b3eafc84a` (313,360,384 bytes)

## Scope (CEO 6:6:4 = 16 row mutations)

### Track A — regex strip 12 source_excerpt rows

Email-shape tokens replaced with `[email-redacted]` in both the identifiers row and its single paired promoted raw_observation. Originals recoverable via `notes.original_source_excerpt_hash` (sha256 of pre-strip value).

| ident_id | identifier | paired ro_id | original_hash (first 16) |
|---:|---|---:|---|
| 5230 | `5c:85:7e:4/28` | 224705 | `45e15…` (idents) / `ce169…` (ros)¹ |
| 11234 | `8c:1f:64:de:6/36` | 232023 | per-row in `applied_log.json` |
| 11725 | `70:b3:d5:93:1/36` | 232636 | per-row in `applied_log.json` |
| 12739 | `70:b3:d5:ee:b/36` | 233968 | per-row in `applied_log.json` |
| 13780 | `70:b3:d5:10:b/36` | 235323 | per-row in `applied_log.json` |
| 20999 | `70:b3:d5:9f:d/36` | 234093 | per-row in `applied_log.json` |

¹ Hashes per-row in `_phase_13_pii_strip/applied_log.json`.

**Sample redacted excerpt** (ident_id=5230, MA-M registrant line):
```
MA-M,5C857E4,Shenzhen IP3 Century Intelligent Technology CO.,Ltd,[email-redacted] Shenzhen  CN 518057
```

Per-row provenance keys merged into existing `notes` JSON (no key clobber):
- `notes.original_source_excerpt_hash` = sha256 of pre-strip excerpt
- `notes.pii_stripped_at` = `2026-05-21T14:23:34Z`
- `notes.pii_strip_dispatch` = `MAC-217`

### Track B — demote 4 vendor_controlled_hostname identifier-is-PII rows

| ident_id | identifier (was PII) | source_url |
|---:|---|---|
| 31582 | `brian.harvie@escg.jacobs.com` | `https://crt.sh/?q=%25.jacobs.com&output=json` |
| 32059 | `michael.fohey@escg.jacobs.com` | `https://crt.sh/?q=%25.jacobs.com&output=json` |
| 32060 | `michele.katz@escg.jacobs.com` | `https://crt.sh/?q=%25.jacobs.com&output=json` |
| 32511 | `walter.jennings@escg.jacobs.com` | `https://crt.sh/?q=%25.jacobs.com&output=json` |

**Chosen demote mechanic:** `superseded_by = id` self-loop sentinel.

Rationale: `db/validation/export_lynceus.py:292` filters `WHERE superseded_by IS NULL`, so a self-loop automatically removes the row from all 4 lynceus outputs without a schema migration or synthetic `source_reclassifications` row. The 5th export (`argus_export_behavioral_signatures.json`) queries a different table; VCH rows do not appear there. Mechanic is reversible (single `UPDATE … SET superseded_by = NULL`); identifier and `source_excerpt` are left untouched on demoted rows (recovery + audit trail per §11 #7).

**Sample demote provenance** (ident_id=31582 `notes` keys, JSON-merged):
```json
{
  "demoted_at":      "2026-05-21T14:23:34Z",
  "demote_dispatch": "MAC-217",
  "demote_reason":   "pii_identifier_value",
  "demote_mechanic": "superseded_by_self_loop"
}
```

Pre-existing keys (`cp29_value_class`, `cp29_confidence_band`, `upstream_license_posture`, etc.) preserved unchanged.

### §11 #3 export-time email-shape guard

Added to both export entry points so any future ingest leak fail-closes on emission:

- `db/validation/export_lynceus.py` — `_assert_no_email_pii(path)` called after `_write_json`, `_write_csv`, and the `coverage_report.md` write.
- `db/validation/export_behavioral_signatures.py` — same helper called after `_write_json` and the `patch_coverage_report` write.

**Synthetic poison test result:**
```
=== Poison test 1: lynceus guard ===
PASS: lynceus guard halted as expected: §11 #3 export-guard FAILED for tmpbsb66zj0.json: 1 email-shape token(s) found.
=== Poison test 2: behavioral_signatures guard ===
PASS: behavioral_signatures guard halted as expected: §11 #3 export-guard FAILED for tmpbf1t4p15.json: 1 email-shape token(s) found.
=== Poison test 3: clean body (negative control) ===
PASS: clean body accepted (negative control)
```

## SAR-13 PRAGMA pre-flight

```
integrity_check = [('ok',)]
quick_check     = [('ok',)]
foreign_key_check = []
```

Performed both at session-start (before backup) and inside the apply transaction (before the first UPDATE).

## Transaction discipline

All 16 row mutations applied in a single `BEGIN IMMEDIATE` transaction. Rollback on any of:
- Row not found / already superseded
- `identifier_type` mismatch vs expected
- `notes` non-JSON or not a JSON object
- Regex sub produced no change
- Post-strip excerpt still contains email shape
- `UPDATE rowcount != 1`

Final pre-commit sanity verified zero residual PII on the 12 stripped rows and zero active VCH-email idents. Transaction committed cleanly.

## Re-fire — MAC-209 5-export regeneration

Run order (matches MAC-209 Phase 12 heartbeat sequence):
1. `venv/bin/python3 -m db.validation.coverage_matrix` — bin-classify post-strip active set
2. `venv/bin/python3 -m db.validation.export_lynceus` — emits 4 outputs (json × 2, csv, coverage_report.md)
3. `venv/bin/python3 -m db.validation.export_behavioral_signatures` — emits 5th + patches CP18 section into coverage_report.md

### Post-strip artifact metadata

| file | size (bytes) | mtime (UTC) | sha256 prefix |
|---|---:|---|---|
| `exports/argus_export.json` | 88,747 | `2026-05-21T14:39:54Z` | `6bf780af373e2f43…` |
| `exports/argus_export_high_confidence.json` | 20,951 | `2026-05-21T14:39:54Z` | `733ba3f08c3583c6…` |
| `exports/argus_export.csv` | 21,394,309 | `2026-05-21T14:39:54Z` | `b3395700f39b47e0…` |
| `exports/argus_export_behavioral_signatures.json` | 69,361 | `2026-05-21T14:40:01Z` | `9f4ab6064019871d…` |
| `exports/coverage_report.md` | 1,522,766 | `2026-05-21T14:40:01Z` | `aad5b0205e383b17…` |

### Active count delta vs MAC-209 baseline

- MAC-209 baseline: `active_count_post_v1_4_1_stage_1 = 34968`
- MAC-217 delta: `−4` (Track B demotions)
- Post-MAC-217 active: `34964` (matches CSV `record_count = 34964`)

The CSV size shrank 21,395,866 → 21,394,309 bytes (−1,557) — net of 4 dropped rows + 12 source_excerpt redactions.

`exports/_export_manifest.json` is **intentionally not regenerated** here; it documents the MAC-209 Phase 12 baseline narrative and is the authoritative record for that dispatch. MAC-217 is an additive in-stage correction with its own provenance trail (this file + commit message). Future re-baseline (e.g., next export-cycle dispatch) should regenerate the manifest from the then-current state.

## Zero-PII grep verification

```
$ grep -rE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' exports/argus_export.csv exports/argus_export*.json exports/coverage_report.md
(no output — zero matches)
```

§11 #3 envelope restored. PASS.

## Discipline envelope

- §11 #1 paste-not-cite — counts, sample row, hashes inline above
- §11 #3 PII discipline — restored; export-time guard makes it durable
- §11 #6 read-only DB pass — exports use `PRAGMA query_only = ON` per their docstrings
- §11 #7 provenance — Track A hash recoverable via notes; Track B identifier untouched
- §11 #8 no confidence drift on Track A; Track B intentionally changes active-envelope inclusion under board approval `8a2ac74d`
- SAR-13 PRAGMA clean pre-flight (both pre-backup and pre-mutation)
- `[[feedback_scoped_updates_via_source_row_key]]` — all UPDATEs scoped by `id IN (…)`
- `[[feedback_argus_working_repo_canonical_path]]` — `~/argus/` canonical

## Refs

- Parent: [MAC-211](/MAC/issues/MAC-211) Phase 13 v1.4.1-rc1 ship
- Sibling predecessor: [MAC-216](/MAC/issues/MAC-216) §8.1 cycle-trail gap remediation
- Sibling consumer: [MAC-212](/MAC/issues/MAC-212) SAR-15.5 audit (auto-unblocks on this close)
- Punted: [MAC-218](/MAC/issues/MAC-218) — 8 orphan raw_observations PII tidy (post-Stage-1 backlog)
