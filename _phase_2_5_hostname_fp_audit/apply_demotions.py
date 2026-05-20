#!/usr/bin/env python3
"""MAC-188 Phase 2.5 — apply Q1.A demotion sweep across 9-manufacturer cohort.

Per CEO ratification (MAC-188 2026-05-20):
- Q1.A mechanic: insert new identifier row with manufacturer=NULL, confidence=0,
  device_category='unknown', notes.fp_demoted=true + fp_class + fp_demoted_at +
  demoted_by_dispatch='MAC-188' + supersedes_identifier_id; UPDATE old row's
  superseded_by to point at new row.
- Single transaction per manufacturer batch; rollback on per-row failure.
- AMBIGUOUS carry-forward: notes.audit_review_required=true (NOT demoted).
- sierrawireless surviving TP row gets notes.slug_duplication_review='see_phase_5'.

Inputs:
- db/argus.db (in-place mutation)
- _phase_2_5_hostname_fp_audit/per_manufacturer_classifications.json (the
  post-reclassification verdict from classifier.py latest run)

Outputs:
- db/argus.db mutated
- _phase_2_5_hostname_fp_audit/demotions_applied.md (audit trail)
- _phase_2_5_hostname_fp_audit/audit_review_queue.json (carry-forward list)
- _phase_2_5_hostname_fp_audit/_demotion_log.json (machine-readable trace)
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT.parent / "db" / "argus.db"

COHORT = [
    "reveal", "drt", "lenel", "sierrawireless", "verkada",
    "dji", "parrot", "autel_robotics", "dahua",
]

DISPATCH = "MAC-188"
NOW_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Anchor sets for fp_class derivation
SYNTHETIC_S3_SUFFIXES = {
    "backup", "config", "dev", "db", "logs", "media",
    "production", "prod", "public", "support", "test",
    "videos", "uploads", "assets", "downloads",
    "firmware", "internal", "storage", "data",
}
CN_TECH_GIANT_APEX = {
    "qq.com", "tencent.com", "alibaba.com", "alibabacloud.com",
    "aliyun.com", "weibo.com", "baidu.com", "xiaomi.com",
    "huawei.com", "alipay.com", "oppomobile.com", "oppo.com",
    "meizu.com", "line.me", "vmall.com", "bilibili.com",
    "douyin.com", "kuaishou.com", "vivo.com", "vivo.com.cn",
    "umeng.com", "getui.com", "tenpay.com", "taobao.org",
    "huya.com",
}


def derive_fp_class(reason: str) -> str:
    """Map classifier reason string → CP31 fp_class label."""
    if reason.startswith("synthetic_vendor_tenant_pattern"):
        return "synthetic_vendor_tenant_pattern"
    if reason == "malformed_concatenated_extraction_artifact":
        return "malformed_concatenated_extraction_artifact"
    if reason in ("non_domain_shape", "no_dot_shape", "empty_or_non_string"):
        return "malformed_concatenated_extraction_artifact"
    if reason.startswith("known_fp_root::"):
        root = reason.split("::", 1)[1]
        if root in CN_TECH_GIANT_APEX:
            return "cn_tech_giant_cross_attribution"
        return "third_party_oss_sdk_root"
    if reason.startswith("third_party_cloud_no_vendor_tenant::"):
        return "third_party_oss_sdk_root"
    if reason.startswith("vendor_tenant_on_third_party_cloud::"):
        # Shouldn't happen for FP bucket (those go AMBIGUOUS) — defensive
        return "synthetic_vendor_tenant_pattern"
    # Defensive fallthrough
    return "third_party_oss_sdk_root"


def load_classifications():
    p = ROOT / "per_manufacturer_classifications.json"
    with open(p) as f:
        return json.load(f)


def merge_notes(existing_notes: str, new_fields: dict) -> str:
    """Parse existing notes (JSON or freetext), add new_fields, return JSON string.

    If existing notes is non-JSON freetext, wrap it under
    `_original_notes_text` to preserve content. New canonical shape is JSON."""
    if existing_notes is None:
        return json.dumps(new_fields, separators=(",", ":"))
    s = existing_notes.strip()
    if not s:
        return json.dumps(new_fields, separators=(",", ":"))
    try:
        obj = json.loads(s)
        if not isinstance(obj, dict):
            obj = {"_original_notes_value": obj}
    except (json.JSONDecodeError, ValueError):
        obj = {"_original_notes_text": s}
    obj.update(new_fields)
    return json.dumps(obj, separators=(",", ":"))


def apply_sweep():
    conn = sqlite3.connect(str(DB))
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # Pre-flight counts
    pre = {}
    for row in cur.execute(
        "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"
    ):
        pre["active"] = row[0]
    for row in cur.execute("SELECT COUNT(*) FROM identifiers"):
        pre["total"] = row[0]

    d = load_classifications()
    demotion_log = []
    skipped_log = []

    for mfr in COHORT:
        if mfr not in d:
            continue
        fp_rows = d[mfr]["FP"]
        if not fp_rows:
            continue

        cur.execute("BEGIN")
        try:
            for row in fp_rows:
                old_id = row["id"]
                fp_class = derive_fp_class(row["reason"])

                # Re-read current canonical state for the row to validate it's
                # still active and to inherit its current field values.
                cur.execute(
                    "SELECT identifier, identifier_type, device_category, "
                    "manufacturer, model, confidence, source_url, source_type, "
                    "source_excerpt, geographic_scope, first_seen, last_verified, "
                    "notes, superseded_by "
                    "FROM identifiers WHERE id = ?",
                    (old_id,),
                )
                r = cur.fetchone()
                if r is None:
                    skipped_log.append({"id": old_id, "reason": "row_not_found"})
                    continue
                (orig_identifier, orig_itype, orig_dc, orig_mfr, orig_model,
                 orig_conf, orig_url, orig_stype, orig_excerpt, orig_geo,
                 orig_first_seen, orig_last_verified, orig_notes,
                 orig_superseded_by) = r

                if orig_superseded_by is not None:
                    # Already superseded — skip (idempotency).
                    skipped_log.append({
                        "id": old_id,
                        "reason": "already_superseded",
                        "superseded_by": orig_superseded_by,
                    })
                    continue

                # Per CEO Q1.A spec: insert new sentinel row.
                new_notes = json.dumps({
                    "fp_demoted": True,
                    "fp_class": fp_class,
                    "fp_demoted_at": NOW_UTC,
                    "demoted_by_dispatch": DISPATCH,
                    "supersedes_identifier_id": old_id,
                    "classifier_reason": row["reason"],
                }, separators=(",", ":"))

                cur.execute(
                    "INSERT INTO identifiers "
                    "(identifier, identifier_type, device_category, manufacturer, "
                    "model, confidence, source_url, source_type, source_excerpt, "
                    "geographic_scope, first_seen, last_verified, notes) "
                    "VALUES (?, ?, 'unknown', NULL, NULL, 0, ?, ?, NULL, ?, ?, ?, ?)",
                    (
                        orig_identifier,
                        orig_itype,
                        orig_url,
                        orig_stype,
                        orig_geo,
                        NOW_UTC,
                        NOW_UTC,
                        new_notes,
                    ),
                )
                new_id = cur.lastrowid

                cur.execute(
                    "UPDATE identifiers SET superseded_by = ? WHERE id = ?",
                    (new_id, old_id),
                )

                demotion_log.append({
                    "manufacturer": mfr,
                    "old_id": old_id,
                    "new_id": new_id,
                    "identifier": orig_identifier,
                    "identifier_type": orig_itype,
                    "pre_confidence": orig_conf,
                    "pre_manufacturer": orig_mfr,
                    "fp_class": fp_class,
                    "classifier_reason": row["reason"],
                })
            conn.commit()
            print(f"[demote] {mfr}: committed {len([x for x in demotion_log if x['manufacturer']==mfr])} demotions")
        except Exception as e:
            conn.rollback()
            print(f"[demote] {mfr}: ROLLED BACK — {type(e).__name__}: {e}")
            raise

    # ─── AMBIGUOUS carry-forward marking ────────────────────────────────────
    # Mark all AMBIGUOUS rows (cohort + non-cohort) with
    # notes.audit_review_required=true. Single transaction.
    cur.execute("BEGIN")
    try:
        amb_log = []
        for mfr, buckets in d.items():
            for row in buckets["AMBIGUOUS"]:
                _id = row["id"]
                cur.execute(
                    "SELECT notes, superseded_by FROM identifiers WHERE id = ?",
                    (_id,),
                )
                r = cur.fetchone()
                if r is None or r[1] is not None:
                    continue  # missing or already demoted
                merged = merge_notes(r[0], {
                    "audit_review_required": True,
                    "audit_review_dispatch": DISPATCH,
                    "audit_review_marked_at": NOW_UTC,
                    "audit_review_reason": row["reason"],
                })
                cur.execute(
                    "UPDATE identifiers SET notes = ? WHERE id = ?",
                    (merged, _id),
                )
                amb_log.append({"id": _id, "manufacturer": mfr,
                                "identifier": row["identifier"],
                                "reason": row["reason"]})
        conn.commit()
        print(f"[amb-mark] committed audit_review_required on {len(amb_log)} AMBIGUOUS rows")
    except Exception as e:
        conn.rollback()
        print(f"[amb-mark] ROLLED BACK — {type(e).__name__}: {e}")
        raise

    # ─── sierrawireless surviving TP row marking ─────────────────────────────
    cur.execute("BEGIN")
    try:
        # Find sierrawireless TP rows (active, post-demote)
        cur.execute(
            "SELECT id, identifier, notes FROM identifiers "
            "WHERE manufacturer = 'sierrawireless' "
            "AND identifier_type IN ('vendor_controlled_hostname', "
            "'vendor_cloud_endpoint_url', 'vendor_controlled_hostname_deprecated') "
            "AND superseded_by IS NULL"
        )
        siw_rows = cur.fetchall()
        siw_log = []
        for sid, sident, snotes in siw_rows:
            merged = merge_notes(snotes, {
                "slug_duplication_review": "see_phase_5",
                "slug_duplication_review_dispatch": DISPATCH,
                "slug_duplication_review_note": (
                    "sierrawireless slug duplicates sierra_wireless (N=126); "
                    "Phase 5 Wave I.12 alias enrichment handles merge"
                ),
            })
            cur.execute(
                "UPDATE identifiers SET notes = ? WHERE id = ?",
                (merged, sid),
            )
            siw_log.append({"id": sid, "identifier": sident})
        conn.commit()
        print(f"[siw-mark] committed slug_duplication_review on {len(siw_log)} sierrawireless surviving row(s)")
    except Exception as e:
        conn.rollback()
        print(f"[siw-mark] ROLLED BACK — {type(e).__name__}: {e}")
        raise

    # Post counts
    post = {}
    for row in cur.execute(
        "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"
    ):
        post["active"] = row[0]
    for row in cur.execute("SELECT COUNT(*) FROM identifiers"):
        post["total"] = row[0]

    # ─── Persist trace ──────────────────────────────────────────────────────
    with open(ROOT / "_demotion_log.json", "w") as f:
        json.dump({
            "dispatch": DISPATCH,
            "applied_at": NOW_UTC,
            "pre_counts": pre,
            "post_counts": post,
            "demotions": demotion_log,
            "skipped": skipped_log,
            "audit_review_marked": amb_log,
            "sierrawireless_slug_marked": siw_log,
        }, f, indent=2)

    print()
    print(f"=== SUMMARY ===")
    print(f"Pre  — active: {pre['active']:>6d}  total: {pre['total']:>6d}")
    print(f"Post — active: {post['active']:>6d}  total: {post['total']:>6d}")
    print(f"Δ active: {post['active'] - pre['active']:+d}  Δ total: {post['total'] - pre['total']:+d}")
    print(f"Demotions applied: {len(demotion_log)}")
    print(f"Audit-review-required marked: {len(amb_log)}")
    print(f"Sierrawireless slug-review marked: {len(siw_log)}")
    print(f"Skipped: {len(skipped_log)}")


if __name__ == "__main__":
    apply_sweep()
