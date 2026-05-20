# Phase 2.5 audit — dahua

**N (active hostname-corpus rows):** 101
**Strict-FP:** 13 (12.87%)
**AMBIGUOUS:** 13 (12.87%)
**Worst-case-FP (FP+AMB):** 25.74%
**Band (strict):** 10-30% (moderate over-promotion → demote sweep)

## Strict-FP rows (rejection target)

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `access.line.me` | 85 | vendor_controlled_hostname | known_fp_root::line.me |
| `actionbarsherlock.com` | 85 | vendor_controlled_hostname | known_fp_root::actionbarsherlock.com |
| `androidpush-prod.messagepush.org` | 85 | vendor_controlled_hostname | known_fp_root::messagepush.org |
| `api.line.me` | 85 | vendor_controlled_hostname | known_fp_root::line.me |
| `curl.haxx.se` | 85 | vendor_controlled_hostname | known_fp_root::haxx.se |
| `fb.gg` | 85 | vendor_controlled_hostname | known_fp_root::fb.gg |
| `goo.gle` | 85 | vendor_controlled_hostname | known_fp_root::goo.gle |
| `journeyapps.com` | 85 | vendor_controlled_hostname | known_fp_root::journeyapps.com |
| `open.oppomobile.com` | 85 | vendor_controlled_hostname | known_fp_root::oppomobile.com |
| `ormlite.com` | 85 | vendor_controlled_hostname | known_fp_root::ormlite.com |
| `registry.npmjs.org` | 85 | vendor_controlled_hostname | known_fp_root::npmjs.org |
| `render.alipay.com` | 85 | vendor_controlled_hostname | known_fp_root::alipay.com |
| `sj.qq.com` | 85 | vendor_controlled_hostname | known_fp_root::qq.com |

## AMBIGUOUS rows (operator review required)

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `dahua-cdn.s3.amazonaws.com` | 85 | vendor_controlled_hostname | vendor_tenant_on_third_party_cloud::s3.amazonaws.com |
| `schema.getpostman.com` | 85 | vendor_controlled_hostname | no_match::apex=getpostman.com |
| `source.icu-project.org` | 85 | vendor_controlled_hostname | no_match::apex=icu-project.org |
| `squareup.com` | 85 | vendor_controlled_hostname | no_match::apex=squareup.com |
| `www.cryptopp.com` | 85 | vendor_controlled_hostname | no_match::apex=cryptopp.com |
| `www.grinninglizard.com` | 85 | vendor_controlled_hostname | no_match::apex=grinninglizard.com |
| `www.isc.org` | 85 | vendor_controlled_hostname | no_match::apex=isc.org |
| `www.libpng.org` | 85 | vendor_controlled_hostname | no_match::apex=libpng.org |
| `www.linfo.org` | 85 | vendor_controlled_hostname | no_match::apex=linfo.org |
| `www.quickddns.com` | 85 | vendor_controlled_hostname | no_match::apex=quickddns.com |
| `www.tenpay.com` | 85 | vendor_controlled_hostname | no_match::apex=tenpay.com |
| `www.vivo.com` | 85 | vendor_controlled_hostname | no_match::apex=vivo.com |
| `www.xfa.org` | 85 | vendor_controlled_hostname | no_match::apex=xfa.org |

## TP rows (75) — first 25

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `activity.dahuasecurity.com` | 85 | vendor_controlled_hostname | vendor_owned_root::dahuasecurity.com |
| `android-messagepush-tu.dolynkcloud.com` | 85 | vendor_controlled_hostname | vendor_owned_root::dolynkcloud.com |
| `api.dahuasecurity.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::dahuasecurity.com |
| `app.dahuatech.com` | 85 | vendor_controlled_hostname | vendor_owned_root::dahuatech.com |
| `app.easy4ipcloud.com` | 85 | vendor_controlled_hostname | vendor_owned_root::easy4ipcloud.com |
| `cirsbus.dahuatech.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::dahuatech.com |
| `cjhb.dahuatech.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::dahuatech.com |
| `cpanel.cpanel.dahuasecurity.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::dahuasecurity.com |
| `cpanel.dahuasecurity.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::dahuasecurity.com |
| `cpanel.newus.dahuasecurity.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::dahuasecurity.com |
| `cpcalendars.cpanel.dahuasecurity.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::dahuasecurity.com |
| `cpcalendars.newus.dahuasecurity.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::dahuasecurity.com |
| `cpcontacts.cpanel.dahuasecurity.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::dahuasecurity.com |
| `cpcontacts.newus.dahuasecurity.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::dahuasecurity.com |
| `cpqcdownload.dahuasecurity.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::dahuasecurity.com |
| `dahuasecurity.com` | 85 | vendor_controlled_hostname | vendor_owned_root::dahuasecurity.com |
| `dahuatech.com` | 85 | vendor_controlled_hostname | vendor_owned_root::dahuatech.com |
| `dh-it-elearnings-public.ns01.s3.dahuatech.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::dahuatech.com |
| `dmsspushproxy-testing.easy4ipcloud.com` | 85 | vendor_controlled_hostname | vendor_owned_root::easy4ipcloud.com |
| `domainapi.dahuatech.com` | 85 | vendor_controlled_hostname | vendor_owned_root::dahuatech.com |
| `dvlec.lechange.com` | 85 | vendor_controlled_hostname | vendor_owned_root::lechange.com |
| `dwms.dahuasecurity.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::dahuasecurity.com |
| `fcmcellphonepush.ecosightsecurity.com` | 85 | vendor_controlled_hostname | vendor_owned_root::ecosightsecurity.com |
| `funcshop.lechange.com` | 85 | vendor_controlled_hostname | vendor_owned_root::lechange.com |
| `gdp.dahuatech.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::dahuatech.com |

*(50 additional TP rows omitted)*
