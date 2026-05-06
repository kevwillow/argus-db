"""Argus Phase-4/Phase-5 extraction utilities.

Reusable disambig modules surfaced from Wave-A Step-1.5b carry-forward:
- fcc_grantees_allowlist: cross-reference fcc_id_anchored regex hits against
  Phase-3 fcc_grantees lexicon + CVE/CWE/NIST stop-list.
- ble_uuid_disambig: URL-context exclusion + protocol-context inclusion gate
  for ble_uuid_anchored regex hits.

Source-of-truth ratification: MAC-23 close (Ratifications 1+2) +
MAC-25 dispatch §10/§11. Both modules MUST be Phase-5-reusable per the
ratified architecture (codification, not one-shot).
"""
