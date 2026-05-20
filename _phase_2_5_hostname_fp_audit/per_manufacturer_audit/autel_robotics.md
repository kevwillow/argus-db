# Phase 2.5 audit — autel_robotics

**N (active hostname-corpus rows):** 61
**Strict-FP:** 8 (13.11%)
**AMBIGUOUS:** 3 (4.92%)
**Worst-case-FP (FP+AMB):** 18.03%
**Band (strict):** 10-30% (moderate over-promotion → demote sweep)

## Strict-FP rows (rejection target)

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `air.aloft.rocks` | 85 | vendor_controlled_hostname | known_fp_root::aloft.rocks |
| `api.openweathermap.org` | 85 | vendor_controlled_hostname | known_fp_root::openweathermap.org |
| `cert.startcom.org` | 85 | vendor_controlled_hostname | known_fp_root::startcom.org |
| `greenrobot.org` | 85 | vendor_controlled_hostname | known_fp_root::greenrobot.org |
| `modelb-d4935.firebaseio.com` | 85 | vendor_controlled_hostname | known_fp_root::firebaseio.com |
| `openapi.baidu.com` | 85 | vendor_controlled_hostname | known_fp_root::baidu.com |
| `playready.directtaps.net` | 85 | vendor_controlled_hostname | known_fp_root::playready.directtaps.net |
| `www.hamcrest.com` | 85 | vendor_controlled_hostname | known_fp_root::hamcrest.com |

## AMBIGUOUS rows (operator review required)

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `metadata.google.internal` | 85 | vendor_controlled_hostname | no_match::apex=google.internal |
| `org.dom4j.io.doucmentsource` | 85 | vendor_controlled_hostname | no_match::apex=io.doucmentsource |
| `www.jstott.me.uk` | 85 | vendor_controlled_hostname | no_match::apex=me.uk |

## TP rows (50) — first 25

| identifier | confidence | identifier_type | reason |
|---|---:|---|---|
| `account.autelrobotics.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autelrobotics.com |
| `ai.autelrobotics.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::autelrobotics.com |
| `apac.maxiacademy.autel.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autel.com |
| `app.autelrobotics.com` | 97 | vendor_controlled_hostname | vendor_owned_root::autelrobotics.com |
| `autel-inspection-realfix-activity-testus.autel.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autel.com |
| `autel.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autel.com |
| `autelapac.maxiacademy.autel.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autel.com |
| `autelmail.autel.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autel.com |
| `autelpilot.com` | 85 | vendor_controlled_hostname | vendor_name_token_in_apex::autel::autelpilot.com |
| `autelrobotics.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autelrobotics.com |
| `chinahq.maxiacademy.autel.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autel.com |
| `clawbox.autel.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autel.com |
| `clouddisk.autelrobotics.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autelrobotics.com |
| `confluence.autelrobotics.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::autelrobotics.com |
| `dealer.autelrobotics.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autelrobotics.com |
| `dev.autelrobotics.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::autelrobotics.com |
| `developer.autelrobotics.cn` | 85 | vendor_controlled_hostname | vendor_name_token_in_apex::autelrobotics::autelrobotics.cn |
| `developer.autelrobotics.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autelrobotics.com |
| `drone-logs.autelrobotics.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autelrobotics.com |
| `eaglesnest.autelrobotics.cn` | 85 | vendor_controlled_hostname | vendor_name_token_in_apex::autelrobotics::autelrobotics.cn |
| `eaglesnest.autelrobotics.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autelrobotics.com |
| `europe.maxiacademy.autel.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autel.com |
| `fly.autelrobotics.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autelrobotics.com |
| `imea.maxiacademy.autel.com` | 85 | vendor_controlled_hostname | vendor_owned_root::autel.com |
| `jira.autelrobotics.com` | 87 | vendor_controlled_hostname_deprecated | vendor_owned_root::autelrobotics.com |

*(25 additional TP rows omitted)*
