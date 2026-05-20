#!/usr/bin/env python3
"""Generate per-manufacturer audit MD files for §2.5.2 dispatch deliverable.

Scope: every manufacturer with strict-FP rate ≥10% OR worst-case ≥30%, plus
the >30% halt cohort even if N is small. Pure-TP manufacturers and ≤10%
manufacturers with no AMBIGUOUS pool get a single-line entry in the index.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
PMA = OUT / "per_manufacturer_audit"
PMA.mkdir(exist_ok=True)

with open(OUT / "per_manufacturer_classifications.json") as f:
    d = json.load(f)
with open(OUT / "per_manufacturer_summary.json") as f:
    summary = json.load(f)["per_manufacturer"]

s_by_mfr = {s["manufacturer"]: s for s in summary}


def band(rate):
    if rate <= 10:
        return "≤10% (well-calibrated)"
    if rate <= 30:
        return "10-30% (moderate over-promotion → demote sweep)"
    return ">30% (HALT)"


def fmt_row(r):
    return (f"| `{r['identifier']}` | {r['confidence']} | "
            f"{r['identifier_type']} | {r['reason']} |")


# Index file
index_lines = [
    "# Phase 2.5 hostname-corpus FP audit — index",
    "",
    "Dispatch: MAC-188. Population: 12,243 active hostname-corpus rows "
    "(`vendor_controlled_hostname` + `vendor_cloud_endpoint_url` + "
    "`vendor_controlled_hostname_deprecated` where `superseded_by IS NULL`).",
    "",
    "Classifier: `_phase_2_5_hostname_fp_audit/classifier.py`. Methodology:",
    "TP = vendor-owned root match; FP = known third-party / synthetic-pattern "
    "/ CN-tech-giant cross-attribution / malformed extraction artifact; "
    "AMBIGUOUS = no confident match either way.",
    "",
    "Bands per SAR-14 calibration discipline (strict-FP-rate basis): ",
    "≤10% well-calibrated · 10-30% sweep-demote band · >30% HALT.",
    "",
    "## Per-manufacturer disposition",
    "",
    "| Manufacturer | N | TP | FP | AMB | strict-FP% | worst-case-FP% | "
    "band (strict) |",
    "|---|---:|---:|---:|---:|---:|---:|---|",
]
for s in summary:
    index_lines.append(
        f"| {s['manufacturer']} | {s['n']} | {s['tp']} | {s['fp']} | "
        f"{s['ambiguous']} | {s['fp_rate_pct']}% | "
        f"{s['fp_rate_worst_case_pct']}% | {band(s['fp_rate_pct'])} |"
    )
with open(PMA / "_index.md", "w") as f:
    f.write("\n".join(index_lines) + "\n")
print(f"wrote: {PMA / '_index.md'}")

# Detailed per-manufacturer MDs for those in 10-30% sweep band or >30% halt band
detailed_target_mfrs = [
    s["manufacturer"] for s in summary if s["fp_rate_pct"] > 10
]
for mfr in detailed_target_mfrs:
    s = s_by_mfr[mfr]
    lines = [
        f"# Phase 2.5 audit — {mfr}",
        "",
        f"**N (active hostname-corpus rows):** {s['n']}",
        f"**Strict-FP:** {s['fp']} ({s['fp_rate_pct']}%)",
        f"**AMBIGUOUS:** {s['ambiguous']} ({s['ambiguous_rate_pct']}%)",
        f"**Worst-case-FP (FP+AMB):** {s['fp_rate_worst_case_pct']}%",
        f"**Band (strict):** {band(s['fp_rate_pct'])}",
        "",
        "## Strict-FP rows (rejection target)",
        "",
        "| identifier | confidence | identifier_type | reason |",
        "|---|---:|---|---|",
    ]
    for r in d[mfr]["FP"]:
        lines.append(fmt_row(r))
    if d[mfr]["AMBIGUOUS"]:
        lines.extend([
            "",
            "## AMBIGUOUS rows (operator review required)",
            "",
            "| identifier | confidence | identifier_type | reason |",
            "|---|---:|---|---|",
        ])
        for r in d[mfr]["AMBIGUOUS"]:
            lines.append(fmt_row(r))
    if d[mfr]["TP"]:
        lines.extend([
            "",
            f"## TP rows ({len(d[mfr]['TP'])}) — first 25",
            "",
            "| identifier | confidence | identifier_type | reason |",
            "|---|---:|---|---|",
        ])
        for r in d[mfr]["TP"][:25]:
            lines.append(fmt_row(r))
        if len(d[mfr]["TP"]) > 25:
            lines.append(
                f"\n*({len(d[mfr]['TP']) - 25} additional TP rows omitted)*"
            )
    with open(PMA / f"{mfr}.md", "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote: {PMA / f'{mfr}.md'}")

# Novel FP patterns codification
novel = {
    "schema_version": 1,
    "stage": "mac188_phase_2_5_hostname_fp_audit",
    "anchor_ratification_pending": True,
    "anchor_ratification_target": "CEO via MAC-188 halt + surface",
    "fp_classes": {
        "synthetic_vendor_tenant_pattern": {
            "shape": "<vendor-token>-<common-suffix>.s3.amazonaws.com",
            "common_suffix_set": [
                "backup", "config", "dev", "db", "logs", "media",
                "production", "prod", "public", "support", "test",
                "videos", "uploads", "assets", "downloads",
                "firmware", "internal", "storage", "data",
            ],
            "rationale": (
                "Same synthetic suffix set repeats across multiple vendors "
                "(reveal, drt, lenel, verkada, parrot, jacobs, honeywell, "
                "cisco_meraki, dji, harris, dahua) with no per-bucket "
                "verification that the bucket actually resolves under the "
                "vendor's AWS account. Pattern matches generative seeding "
                "rather than vendor-cloud-endpoint evidence. CP29 §2 admits "
                "vendor-tenant-on-third-party-cloud ONLY when the hostname "
                "IS the endpoint signature with bucket-attestation; the "
                "synthetic-suffix shape fails that gate."
            ),
            "verdict": "FP",
            "affected_manufacturers_observed": [
                "reveal", "drt", "lenel", "verkada", "parrot", "jacobs",
                "honeywell", "cisco_meraki", "dji", "harris", "dahua",
            ],
        },
        "cn_tech_giant_cross_attribution": {
            "shape": "<subdomain>.<cn-tech-giant-apex> attributed to non-"
                     "CN-tech-giant manufacturer",
            "cn_tech_giant_apex_set": [
                "qq.com", "tencent.com", "alibaba.com", "alibabacloud.com",
                "aliyun.com", "weibo.com", "baidu.com", "xiaomi.com",
                "huawei.com", "alipay.com", "oppomobile.com", "meizu.com",
                "line.me", "vmall.com",
            ],
            "rationale": (
                "CN-tech-giant ecosystem hostnames (xiaomi/huawei/meizu/"
                "alipay push SDK, line.me messaging, vmall.com Huawei "
                "store) appear in vendor SDK manifests as SDK dependencies "
                "rather than vendor-controlled infrastructure. Attribution "
                "to the SDK-integrating vendor (e.g., Hikvision, Dahua) is "
                "incorrect under CP29 §1 vendor-ownership predicate."
            ),
            "verdict": "FP",
            "affected_manufacturers_observed": [
                "dji", "hikvision", "dahua", "autel_robotics",
            ],
        },
        "third_party_oss_sdk_root": {
            "shape": "hostname under non-vendor OSS / standards / CDN / "
                     "tooling / cert-authority apex",
            "apex_examples": [
                "googlecode.com", "llvm.org", "googleusercontent.com",
                "gnome.org", "linuxtv.org", "xiph.org", "openweathermap.org",
                "u-blox.com", "tuxfamily.org", "scipy.org", "skyward.io",
                "khronos.org", "expo.dev", "launchdarkly.com",
                "swmansion.com", "actionbarsherlock.com", "ormlite.com",
                "haxx.se", "journeyapps.com", "ggpht.com", "qbox.me",
            ],
            "rationale": (
                "Vendor SDK / Wave I extraction surfaced third-party OSS "
                "library / SDK / CDN / cert-authority roots cited in "
                "binaries or READMEs. Per CP29 §1 these are NOT "
                "vendor-controlled hostnames; the binary mention is a "
                "dependency-graph signal, not a vendor-infrastructure "
                "signal."
            ),
            "verdict": "FP",
            "affected_manufacturers_observed": [
                "dji", "parrot", "autel_robotics", "dahua", "hikvision",
            ],
        },
        "malformed_concatenated_extraction_artifact": {
            "shape": "single-label > 40 chars without sufficient hyphenation "
                     "(<3 hyphens), OR overall hostname length > 120 chars",
            "rationale": (
                "Wave I extraction-time pipeline (regex-based hostname "
                "harvest) occasionally produced concatenated-host artifacts "
                "where multiple distinct hosts merged into a single gibberish "
                "label. Surfaced empirically in cisco_meraki AMBIGUOUS bucket."
            ),
            "verdict": "FP",
            "affected_manufacturers_observed": ["cisco_meraki", "dji"],
        },
    },
    "next_action": (
        "CEO ratifies (a) the four FP classes above as canonical FP "
        "patterns for v1.5.0 disambig codification, (b) the supersession "
        "mechanic for FP-demotion (no v1.4.0 precedent — must pick: "
        "MAC-110 reclassification supersession pattern adapted for "
        "FP-class, novel sentinel-row-pointer pattern, or conflicts-table "
        "routing with `notes.fp_demoted=true` flag on identifiers row), "
        "(c) the disposition for 5 manufacturers in >30% halt band plus "
        "4 manufacturers in 10-30% sweep band."
    ),
}
with open(OUT / "novel_fp_patterns.json", "w") as f:
    json.dump(novel, f, indent=2)
print(f"wrote: {OUT / 'novel_fp_patterns.json'}")
