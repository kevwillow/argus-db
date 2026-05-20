# Phase 2.5 audit — verkada

**N (active hostname-corpus rows):** 9
**Strict-FP:** 3 (33.33%)
**AMBIGUOUS:** 0 (0.0%)
**Worst-case-FP (FP+AMB):** 33.33%
**Band (strict):** >30% (HALT)

## Strict-FP rows (rejection target)

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `verkada-assets.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=assets |
| `verkada-firmware.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=firmware |
| `verkada-internal.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=internal |

## TP rows (6) — first 25

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `apidocs.verkada.com` | 85 | vendor_controlled_hostname | vendor_owned_root::verkada.com |
| `docs.verkada.com` | 85 | vendor_controlled_hostname | vendor_owned_root::verkada.com |
| `help.verkada.com` | 85 | vendor_controlled_hostname | vendor_owned_root::verkada.com |
| `partners.verkada.com` | 85 | vendor_controlled_hostname | vendor_owned_root::verkada.com |
| `status.verkada.com` | 85 | vendor_controlled_hostname | vendor_owned_root::verkada.com |
| `store.verkada.com` | 85 | vendor_controlled_hostname | vendor_owned_root::verkada.com |
