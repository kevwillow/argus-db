# Phase 2.5 audit — parrot

**N (active hostname-corpus rows):** 75
**Strict-FP:** 13 (17.33%)
**AMBIGUOUS:** 0 (0.0%)
**Worst-case-FP (FP+AMB):** 17.33%
**Band (strict):** 10-30% (moderate over-promotion → demote sweep)

## Strict-FP rows (rejection target)

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `api.skyward.io` | 85 | vendor_controlled_hostname | known_fp_root::skyward.io |
| `docs.scipy.org` | 85 | vendor_controlled_hostname | known_fp_root::scipy.org |
| `eigen.tuxfamily.org` | 85 | vendor_controlled_hostname | known_fp_root::tuxfamily.org |
| `offline-live1.services.u-blox.com` | 85 | vendor_controlled_hostname | known_fp_root::u-blox.com |
| `offline-live2.services.u-blox.com` | 85 | vendor_controlled_hostname | known_fp_root::u-blox.com |
| `parrot-backup.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=backup |
| `parrot-dev.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=dev |
| `parrot-ff6.firebaseio.com` | 85 | vendor_controlled_hostname | known_fp_root::firebaseio.com |
| `parrot-production.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=production |
| `parrot-public.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=public |
| `parrot-uploads.s3.amazonaws.com` | 85 | vendor_controlled_hostname | synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=uploads |
| `skyward.io` | 85 | vendor_controlled_hostname | known_fp_root::skyward.io |
| `www.adobepartneroffer.com` | 85 | vendor_controlled_hostname | known_fp_root::adobepartneroffer.com |

## TP rows (62) — first 25

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `academy-legacy.parrot.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::parrot.com |
| `academy.parrot.com` | 85 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `accounts-api.parrot.com` | 85 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `accounts.parrot.com` | 97 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `activities.parrot.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::parrot.com |
| `api-flower-power-pot.parrot.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::parrot.com |
| `api.parrot.com` | 85 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `apiflowerpower.parrot.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::parrot.com |
| `appcentral.parrot.com` | 97 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `central-us.starfish.parrot.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::parrot.com |
| `central.starfish.parrot.com` | 85 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `community.parrot.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::parrot.com |
| `community.stage.parrot.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::parrot.com |
| `crma-flowerpower.parrot.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::parrot.com |
| `customers.parrot.com` | 85 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `debian.parrot.com` | 85 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `dev-academy.parrot.com` | 85 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `dev-api.parrot.com` | 85 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `dev-customers.parrot.com` | 85 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `dev-developer.parrot.com` | 85 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `dev-overpass.parrot.com` | 85 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `dev-support.parrot.com` | 85 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `dev-tiles.parrot.com` | 85 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `dev-www.parrot.com` | 85 | vendor_controlled_hostname | vendor_owned_root::parrot.com |
| `dev.central.starfish.parrot.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::parrot.com |

*(37 additional TP rows omitted)*
