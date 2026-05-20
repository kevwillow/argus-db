#!/usr/bin/env python3
"""Write demotions_applied.md + audit_review_queue.json from _demotion_log.json."""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent

with open(ROOT / "_demotion_log.json") as f:
    log = json.load(f)

# ─── demotions_applied.md ────────────────────────────────────────────────────
by_mfr = defaultdict(list)
for d in log["demotions"]:
    by_mfr[d["manufacturer"]].append(d)

by_class = defaultdict(list)
for d in log["demotions"]:
    by_class[d["fp_class"]].append(d)

lines = [
    "# MAC-188 Phase 2.5 — demotions applied (audit trail)",
    "",
    f"**Dispatch:** MAC-188 / Phase 2.5 hostname-corpus FP audit",
    f"**Applied at (UTC):** {log['applied_at']}",
    f"**Mechanic:** Q1.A (CEO-ratified) — MAC-110-style reclassification supersession. INSERT new row with `manufacturer=NULL` + `confidence=0` + `device_category='unknown'` + `notes.fp_demoted=true` + `notes.fp_class` + `notes.supersedes_identifier_id`. UPDATE old row's `superseded_by` to point at new row. Single transaction per manufacturer batch.",
    "",
    "## Pre/post counts",
    "",
    f"| Metric | Pre | Post | Δ |",
    f"|---|---:|---:|---:|",
    f"| identifiers total | {log['pre_counts']['total']} | {log['post_counts']['total']} | {log['post_counts']['total']-log['pre_counts']['total']:+d} |",
    f"| identifiers active (`superseded_by IS NULL`) | {log['pre_counts']['active']} | {log['post_counts']['active']} | {log['post_counts']['active']-log['pre_counts']['active']:+d} |",
    "",
    "Note: active count unchanged because each demotion swaps an old `mfr=<vendor>/conf=85` row for a new `mfr=NULL/conf=0` sentinel row. Both rows live in `identifiers`; the active filter promotes the sentinel.",
    "",
    "## Per-manufacturer summary",
    "",
    "| Manufacturer | Demotions applied | Scope-extension rationale |",
    "|---|---:|---|",
]
scope_notes = {
    "reveal": "ALL 4 rows demoted per >30% halt-band disposition (CEO ratified Q3 — `manufacturers` row retained for Stage 2 orphaned-manufacturer cleanup).",
    "drt": "10 rows demoted per >30% halt-band; 3 survivors retained (drtinc.com x2 TP + drtstorage.blob AMBIGUOUS carry-forward).",
    "lenel": "2 rows demoted per >30% halt-band; 2 survivors retained (real ACS vendor).",
    "sierrawireless": "1 row demoted per >30% halt-band; 1 surviving TP row marked `notes.slug_duplication_review='see_phase_5'` (slug-merge deferred to Wave I.12).",
    "verkada": "3 rows demoted per >30% halt-band; 6 survivors retained.",
    "dji": "194 rows demoted per 10-30% sweep-demote band (originally; post-reclassification rate 44.5% — band moved to halt but cohort already named). Scope extends from initial 50-sample to FULL manufacturer subset (CEO-ratified §2.5.4 sweep).",
    "parrot": "13 rows demoted per 10-30% sweep-demote band. Scope: FULL manufacturer subset.",
    "autel_robotics": "11 rows demoted per 10-30% sweep-demote band. Scope: FULL manufacturer subset.",
    "dahua": "24 rows demoted per 10-30% sweep-demote band. Scope: FULL manufacturer subset. 1 AMBIGUOUS row (dahua-cdn.s3) carry-forwarded.",
}
total = 0
for mfr in ["reveal","drt","lenel","sierrawireless","verkada","dji","parrot","autel_robotics","dahua"]:
    n = len(by_mfr.get(mfr, []))
    total += n
    lines.append(f"| {mfr} | {n} | {scope_notes.get(mfr,'')} |")
lines.append(f"| **TOTAL** | **{total}** | |")

lines.extend([
    "",
    "## Per-fp_class summary (CP31 candidate breakdown)",
    "",
    "| fp_class | Demotions | Description |",
    "|---|---:|---|",
])
class_desc = {
    "synthetic_vendor_tenant_pattern": "`<vendor-token>-<common-suffix>.<third_party_cloud_apex>` over 19-entry synthetic suffix set. CP29 §2 bucket-attestation gate failed.",
    "cn_tech_giant_cross_attribution": "CN-tech-giant ecosystem (xiaomi/huawei/meizu/alipay/qq/etc.) cross-attributed to non-CN-tech-giant vendor. CP29 §1 vendor-ownership predicate violation.",
    "third_party_oss_sdk_root": "OSS / SDK / CDN / CA / standards / personal-blog root cited as dependency-graph signal (not vendor-owned).",
    "malformed_concatenated_extraction_artifact": "Extraction-pipeline artifact (label >40 chars without sufficient hyphenation, length >120, or corrupted-TLD suffix shape).",
}
for cls, rows in sorted(by_class.items(), key=lambda kv: -len(kv[1])):
    lines.append(f"| `{cls}` | {len(rows)} | {class_desc.get(cls, '')} |")

# Per-row before/after table (compact)
lines.extend([
    "",
    "## Per-row before/after (paste-not-cite)",
    "",
    "Format: `old_id → new_id  |  identifier  |  fp_class  |  classifier_reason`",
    "",
    "| Manufacturer | old_id | new_id | identifier | fp_class | classifier_reason |",
    "|---|---:|---:|---|---|---|",
])
for mfr in ["reveal","drt","lenel","sierrawireless","verkada","dji","parrot","autel_robotics","dahua"]:
    for d in by_mfr.get(mfr, []):
        ident = d["identifier"]
        if len(ident) > 60:
            ident = ident[:57] + "..."
        lines.append(
            f"| {mfr} | {d['old_id']} | {d['new_id']} | `{ident}` | "
            f"`{d['fp_class']}` | `{d['classifier_reason']}` |"
        )

# Discipline checklist
lines.extend([
    "",
    "## Discipline checklist",
    "",
    "- ✅ SAR-13 PRAGMA + CHECK enum verified pre-sweep (hb_002_5_halt heartbeat).",
    "- ✅ SAR-14 inline calibration — full audit completed; per-manufacturer FP rates above the 10% threshold drove demotions; <10% manufacturers carry forward unchanged.",
    "- ✅ §11 #1 no fabrication — actual identifier strings preserved; new sentinel rows carry `notes.classifier_reason` linking to specific reason string.",
    "- ✅ §11 #7 provenance — every demotion preserves the old row in `identifiers` with full source_url / source_excerpt / notes; superseded-row preservation per §6.4.",
    "- ✅ §11 #8 demotions via supersession (not inline confidence edits) — Q1.A CEO-ratified mechanic followed exactly.",
    "- ✅ §11 #11 amendment-log discipline — 4 novel FP classes codified in `provisional_classifier_rules.json` as CP31 candidates; SAR-17 candidate proposed (canonical FP-demotion mechanic).",
    "- ✅ Single transaction per manufacturer batch; rollback on per-row failure (no rollback fired this sweep).",
    "- ✅ AMBIGUOUS rows carry-forward marked `notes.audit_review_required=true` (Q2.A); not silently demoted.",
    "- ✅ sierrawireless surviving TP row marked `notes.slug_duplication_review='see_phase_5'` (Q3 — no slug merge in this pass).",
    "",
    "## Next-action gates",
    "",
    "- Phase 2.5 closes `done`. Parent MAC-184 wakes CEO via `issue_children_completed`. MAC-189 (Phase 3b) auto-unblocks for the 22 lift candidates re-evaluation against the post-demote canon.",
    "- Stage 2 carry-forwards: (a) SAR-17 canonical FP-demotion mechanic; (b) CP31 four novel FP classes; (c) reveal orphaned-manufacturer cleanup; (d) sierrawireless slug-merge in Phase 5; (e) audit_review_queue (143 rows) for v1.4.2 / Stage 2 operator-review pass; (f) 64 non-cohort FP rows for v1.4.2 sweep.",
])

with open(ROOT / "demotions_applied.md", "w") as f:
    f.write("\n".join(lines) + "\n")
print(f"wrote: {ROOT / 'demotions_applied.md'}")

# ─── audit_review_queue.json ─────────────────────────────────────────────────
queue = {
    "schema_version": 1,
    "dispatch": "MAC-188",
    "marked_at": log["applied_at"],
    "carry_forward_basis": "Q2.A — strict AMBIGUOUS-row carry-forward (not silently demoted).",
    "stage_2_consumer": "v1.4.2 / Stage 2 operator-review pass + Lynceus integration audit-flag review",
    "total_rows": len(log["audit_review_marked"]),
    "by_manufacturer": {},
    "rows": log["audit_review_marked"],
}
mfr_counts = defaultdict(int)
for r in log["audit_review_marked"]:
    mfr_counts[r["manufacturer"]] += 1
queue["by_manufacturer"] = dict(sorted(mfr_counts.items(), key=lambda kv: -kv[1]))

with open(ROOT / "audit_review_queue.json", "w") as f:
    json.dump(queue, f, indent=2)
print(f"wrote: {ROOT / 'audit_review_queue.json'} ({len(log['audit_review_marked'])} rows)")
