# Phase 2.5 audit — reveal

**N (active hostname-corpus rows):** 4
**Strict-FP:** 4 (100.0%)
**AMBIGUOUS:** 0 (0.0%)
**Worst-case-FP (FP+AMB):** 100.0%
**Band (strict):** >30% (HALT)

## Strict-FP rows (rejection target)

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `reveal-assets.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=assets |
| `reveal-backup.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=backup |
| `reveal-internal.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=internal |
| `reveal-prod.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=prod |
