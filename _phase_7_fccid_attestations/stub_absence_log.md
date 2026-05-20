# Phase 7 §7.3 — Wave I.14c stub-page documented absence

**Dispatch ref:** [MAC-194](/MAC/issues/MAC-194) §7.3
**Plan source:** `/home/kev/argus-internal/wave_i_pre_v1/wave_i_14c_unfreeze/EXTRACTION_PLAN_V3_FOR_PAPERCLIP_V1_4_1.json` → `fccid_io_extended_stub_documented_absences[0]`
**Manufacturer:** Parrot (id=25) — selected via grantee_code_3char `2AG` → PARROT DRONE SAS canonical mapping
**Pattern:** Phase 5 §5.5 FCC absences (json_set on `manufacturers.notes.fcc_grantee_documented_absences[]`)

## Entry applied

```json
{
  "fcc_id": "2AG6IWCH01",
  "url": "https://fccid.io/2AG6IWCH01",
  "reason": "undersized body",
  "html_bytes": 15,
  "absence_basis": "fccid_io_stub_page",
  "source_dispatch": "MAC-194",
  "wave": "wave_i_14c_unfreeze",
  "captured_at_utc": "2026-05-20T00:00:00Z",
  "deep_mine_status": "v1_5_0_pending",
  "grantee_code_3char_inferred": "2AG",
  "grantee_name_inferred": "PARROT DRONE SAS"
}
```

## §11 discipline

- §11 #1 (no fabrication) — plan-input data preserved verbatim.
- §11 #7 (provenance) — fcc_id + url + reason chained to plan dispatch ref.
- §11 #8 (no confidence drift) — no identifier promoted; no confidence assigned.
