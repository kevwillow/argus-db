# Phase 8 — Honeywell admission + cert-chain enrichment landing
Dispatch: MAC-195   Captured: 2026-05-20T20:23:38.258820+00:00

## Pre-flight
- manufacturers count: 51
- identifiers (non-superseded) count: 34910
- PRAGMA integrity_check: ok

## Honeywell canonical row resolved: id=211, canonical='Honeywell'

## Deliverable 1 — Admission
Honeywell already admitted via MAC-104b/MAC-178 on 2026-05-18 as a documented-absence stub. Canonical_name='Honeywell' (same name as requested admission target). UNIQUE constraint on canonical_name would reject a duplicate INSERT; admission resolves as a NO-OP.
Note for board ratification: dispatch's 51→52 pre/post count expectation was based on stale assumption that Honeywell was not yet admitted. Actual pre-state: 51 (Honeywell already at id=211).

## Deliverable 2 — §6.4 alias enrichment
SKIP-IDEMPOTENT: alias 'HoneywellSecurityGroup' already present in Honeywell.aliases.

## Deliverable 3a — §6.5 cert-issuer supply-chain enrichment
SKIP-IDEMPOTENT: cert_issuer_supply_chain entry already present (matched on ct_log_cert_total=3628).

## Deliverable 3b — §6.5 honeywell_acs_division_attestation
SKIP-IDEMPOTENT: honeywell_acs_division_attestation entry already present (matched on code_signing_ca_cn + device_models).

## Post-flight
- manufacturers count: 51 (pre=51)
- identifiers (non-superseded) count: 34910 (pre=34910)
- PRAGMA integrity_check: ok

## Post-state Honeywell readback
- id: 211
- canonical_name: Honeywell
- aliases (count): 42 comma-separated entries
- aliases (last 3): ['Honeywell Sensing and Control', 'Micro Switch Division of Honeywell', 'HoneywellSecurityGroup']
- notes top-level keys: ['admission_basis', 'admission_date_utc', 'admission_dispatch_ref', 'admission_integration_ref', 'cert_issuer_supply_chain', 'description', 'documented_absence', 'honeywell_acs_division_attestation', 'mac195_alias_enrichment']
- mac195_alias_enrichment len: 1
- cert_issuer_supply_chain len: 1
- honeywell_acs_division_attestation len: 1
- documented_absence len (preserved): 1

## Per-outcome counts
  admission_no_op: 1
  alias_applied: 0
  alias_skipped_idempotent: 1
  cert_issuer_applied: 0
  cert_issuer_skipped_idempotent: 1
  acs_attestation_applied: 0
  acs_attestation_skipped_idempotent: 1
  halt: 0