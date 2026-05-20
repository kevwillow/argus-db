# Phase 2.5 audit — lenel

**N (active hostname-corpus rows):** 4
**Strict-FP:** 2 (50.0%)
**AMBIGUOUS:** 0 (0.0%)
**Worst-case-FP (FP+AMB):** 50.0%
**Band (strict):** >30% (HALT)

## Strict-FP rows (rejection target)

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `lenel-backup.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=backup |
| `lenel-downloads.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=downloads |

## TP rows (2) — first 25

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `kb.lenels2.com` | 85 | vendor_controlled_hostname | vendor_owned_root::lenels2.com |
| `portal.lenels2.com` | 85 | vendor_controlled_hostname | vendor_owned_root::lenels2.com |
