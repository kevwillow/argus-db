# HB-008 — Phase 8 Honeywell admission + cert-chain enrichment COMPLETE

**Dispatch:** [MAC-195](/MAC/issues/MAC-195)
**Parent:** [MAC-184](/MAC/issues/MAC-184) — v1.4.1 Stage 1 integration
**Backup:** `db/argus.db.mac195_pre_phase8_backup` (291 MB, taken 2026-05-20 16:22 UTC)
**Apply script:** `_phase_8_honeywell_admission/apply_phase_8_honeywell_landing.py`
**Apply log:** `_phase_8_honeywell_admission/phase_8_apply_log.md`

## Pre / post DB state

| Metric | Pre | Post | Delta |
|---|---|---|---|
| `manufacturers` row count | 51 | 51 | 0 |
| `identifiers WHERE superseded_by IS NULL` | 34,910 | 34,910 | 0 |
| `PRAGMA integrity_check` | ok | ok | — |

**Count expectation drift surfaced:** dispatch expected `51 → 52`; actual `51 → 51`. Reason: Honeywell was already admitted as `canonical_name='Honeywell'` (id=211) via [MAC-104b](/MAC/issues/MAC-104b) / [MAC-178](/MAC/issues/MAC-178) on 2026-05-18 as a documented-absence stub. Deliverable #1 resolves as a NO-OP idempotent landing under the same canonical name. The halt criterion is worded "Honeywell already exists under a *different* canonical_name" — current state is *same* canonical_name, so the halt does not fire; proceeding with enrichment was the correct interpretation. **Surfaced for board ratification.**

## Per-deliverable outcome

### Deliverable 1 — Honeywell admission → **NO-OP (already admitted)**

- `manufacturers.canonical_name = 'Honeywell'` already present (id=211).
- UNIQUE constraint on `canonical_name` would reject any duplicate INSERT.
- Prior admission anchor preserved untouched in `notes.documented_absence` /
  `notes.admission_basis = 'documented_absence_only'` /
  `notes.admission_dispatch_ref = 'MAC-104b'` /
  `notes.admission_integration_ref = 'MAC-178'`.
- §11 #7 provenance preserved: the MAC-104b/MAC-178 admission stub is untouched.

### Deliverable 2 — §6.4 alias enrichment → **APPLIED**

- Appended `HoneywellSecurityGroup` to `Honeywell.aliases` (now 42 comma-separated entries; previously 41).
- Logged provenance to `notes.mac195_alias_enrichment[0]`:
  ```json
  {
    "appended_alias": "HoneywellSecurityGroup",
    "tier": 3,
    "source": "ct_log_common_name (Wave I.14a sub-pass 43)",
    "phase_6_staging_dispatch": "MAC-192",
    "integration_dispatch": "MAC-195",
    "cp_anchor": "phase_8_honeywell_landing_§6.4_alias_enrichment",
    "integration_at_utc": "2026-05-20T20:23:29.083126+00:00"
  }
  ```
- SAR-15 GENERIC_RISK_CANONICALS guard: PASS (vendor-anchored, not generic).
- Alias collision pre-check: clean (HoneywellSecurityGroup not present in any other manufacturer's aliases or canonical_name).

### Deliverable 3a — §6.5 cert-issuer supply-chain → **APPLIED**

- Appended to `notes.cert_issuer_supply_chain[0]`:
  - `ct_log_cert_total: 3628`
  - `top_5_issuer_organizations`: `[["DigiCert Inc", 1428], ["\"VeriSign", 1003], ["Honeywell International Inc.", 843], ["\"GeoTrust", 145], ["GlobalSign nv-sa", 116]]`
  - `attribution_status: "confirmed_via_sar_13_5_bucket_audit"` (preserved from staging doc)
  - `wave_i_14a_subpass: "43"`, `phase_6_staging_dispatch: "MAC-192"`, `integration_dispatch: "MAC-195"`
- SAR-13.5 bucket-attribution discipline preserved.

### Deliverable 3b — §6.5 honeywell_acs_division_attestation → **APPLIED**

- Appended to `notes.honeywell_acs_division_attestation[0]`:
  - `division: "ACS (Automation and Control Solutions)"`
  - `code_signing_ca_cn: "Honeywell CodeSign RSA CA"`
  - `code_signing_branch: "dubai_android_releasekey"`
  - `device_models_attested: ["CT45", "CT40"]`
  - `evidence`: 7 firmware-embedded code-signing certs (Wave I.7 + I.8 firmware archives) all with issuer_dn `'C=US, O=Honeywell International Inc., OU=ACS, CN=Honeywell CodeSign RSA CA'`
  - `attribution_status: "confirmed_via_sar_13_5_bucket_audit"` (preserved from staging doc)
- SAR-13.5 bucket-attribution discipline preserved.

## Discipline envelope attestation

- **SAR-13 + §3399 — PRAGMA + sqlite_master schema check:** `manufacturers` table CREATE has no CHECK constraints; sole constraint is `UNIQUE(canonical_name)`. PRAGMA integrity_check `ok` pre and post.
- **SAR-13.5 — bucket-attribution discipline:** preserved verbatim on cert_issuer + ACS attestation entries (`attribution_status='confirmed_via_sar_13_5_bucket_audit'`).
- **SAR-15 — GENERIC_RISK_CANONICALS guard:** `HoneywellSecurityGroup` is vendor-anchored (matches existing `Honeywell *` alias prefix family); guard PASS.
- **§11 #1 (no fabrication):** alias evidence chains to ct_log Wave I.14a sub-pass 43; cert-chain evidence chains to honeywell-firmware S3 bucket (Wave I.7 + I.8 firmware archives).
- **§11 #7 (provenance preserved):** existing `documented_absence` + admission-anchor keys untouched; new keys appended; transaction atomic; rollback path covered.
- **§11 #8 (no confidence drift):** NOT APPLICABLE — this is alias/notes enrichment on a stub admission row, no identifier promotion, no confidence change.
- **§11 #11 (amendment-log discipline):** not invoked — Honeywell admission is a row-level no-op; enrichments are additive notes/alias appends on an existing row.

## Idempotency attestation

Re-running `apply_phase_8_honeywell_landing.py` after first successful run produces:
- `alias_skipped_idempotent: 1` (alias presence detected case-insensitive on normalized form)
- `cert_issuer_skipped_idempotent: 1` (matched on `integration_dispatch ∈ {MAC-192, MAC-195}` + `ct_log_cert_total=3628`)
- `acs_attestation_skipped_idempotent: 1` (matched on `code_signing_ca_cn` + `device_models_attested` tuple)
- Zero state mutation on re-run; transactionally atomic.

## Hand-off

- **Status:** `done`.
- **Parent next-phase trigger:** [MAC-184](/MAC/issues/MAC-184) should wake CEO. Phase 8 lands independently of CP30 and Numerex (per dispatch's coordination notes); these may proceed in parallel and Phase 9 (post-CP30 §7.2 Phase 7-bis re-dispatch) becomes the natural next dispatch once CP30 + Numerex land.
- **Board-class surface:** the dispatch's count-expectation drift (51→52 expected vs 51→51 actual) is a coordination-note artifact, not a hard-rule trip. Surface in the heartbeat comment so the board has it on record; no ratification gate required.
