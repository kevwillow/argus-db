# MAC-192 §6.8 — `gimlet.flocksafety.com` (inferred-only) DEFERRED

Captured: 2026-05-20

**Per dispatch §6.8 + Wave I.14a annex §5 + §11 #1 discipline**: the only inferred-only candidate from sub-pass 41 is explicitly excluded from MAC-192 promotion.

## Candidate detail

- Identifier: `gimlet.flocksafety.com`
- Inferred from: `dev-gimlet` token observed in Flock device-side code (GainSec sub-pass 41)
- Proposed manufacturer: Flock Safety
- Proposed type: vendor_controlled_hostname
- Class: inferred-only (no direct observation of the hostname; only the `dev-gimlet` prefix appears in source)

## Why deferred (§11 #1 no fabrication)

The `gimlet.flocksafety.com` FQDN is **not directly observed** in any extracted artifact. It is inferred from:
1. `dev-gimlet` prefix in code
2. Flock's `*.flocksafety.com` vendor-controlled domain pattern (113 sibling hosts already in canonical)
3. Plausibility that a `gimlet` service would expose `gimlet.flocksafety.com` analogously to other `dev-<name>` patterns

Per §11 #1 (no fabrication), inferred-only candidates without a direct observation cite are NOT promoted. This is a single-source inferred chain.

## CEO discretion (cross-source attestation)

Per Wave I.14a annex §5 and `paperclip_integration_decisions_pending[3]` (gimlet.flocksafety.com cross-source attestation decision): if Paperclip cross-references any external source (e.g., DNS enumeration via sibling-vendor recon corpus, CT log surfacing of a `gimlet.flocksafety.com` cert) at v1.4.2 or later, this candidate may be promoted under §8.3 single→multi-source uplift rules.

## Discipline

- §11 #1 no fabrication: ✓ — inferred-only; held.
- §11 #7 provenance: would need a direct observation cite before promotion.
- §11 #11 amendment-log: this defer is plan-source-authored, no new amendment.
