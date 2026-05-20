# Phase 2.5 audit — drt

**N (active hostname-corpus rows):** 13
**Strict-FP:** 10 (76.92%)
**AMBIGUOUS:** 3 (23.08%)
**Worst-case-FP (FP+AMB):** 100.0%
**Band (strict):** >30% (HALT)

## Strict-FP rows (rejection target)

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `drt-backup.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=backup |
| `drt-config.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=config |
| `drt-db.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=db |
| `drt-logs.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=logs |
| `drt-media.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=media |
| `drt-production.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=production |
| `drt-public.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=public |
| `drt-support.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=support |
| `drt-test.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=test |
| `drt-videos.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=videos |

## AMBIGUOUS rows (operator review required)

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `drtinc.com` | 85 | vendor_controlled_hostname | no_match::apex=drtinc.com |
| `drtstorage.blob.core.windows.net` | 85 | vendor_controlled_hostname | vendor_tenant_on_third_party_cloud::blob.core.windows.net |
| `www.drtinc.com` | 85 | vendor_controlled_hostname | no_match::apex=drtinc.com |
