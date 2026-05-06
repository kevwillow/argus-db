"""MAC-44 Step-E spot-check — randomized ≥15 staged rows verification.

Per dispatch §Step E: walk a randomized sample of staged rows and verify
- No bare-`Motorola` rows promoted (should all route to flag_for_review).
- No `Motorola Mobility` / `(Wuhan)` / `Lenovo` rows promoted under
  `Motorola Solutions`.
- No `WatchGuard Technologies` rows promoted under `WatchGuard`.
- No `Harris Adacom` rows promoted under `Harris`.
- Per-vendor distribution makes corpus sense.
"""

from __future__ import annotations

import json
import random
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "db" / "argus.db"
OUT_PATH = Path(__file__).resolve().parent / "sar9_spot_check_report.json"

SAMPLE_SIZE = max(15, 120 // 10)  # ≥10% or 15, whichever is larger
RANDOM_SEED = 20260506  # deterministic for re-run idempotency at Validator level


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    staged = conn.execute(
        """SELECT i.id AS identifier_id, i.identifier, i.identifier_type,
                  i.device_category, i.manufacturer, i.confidence,
                  i.source_url, i.source_type, i.source_excerpt, i.notes,
                  i.superseded_by,
                  ro.id AS raw_obs_id,
                  ro.candidate_manufacturer AS candidate_manufacturer_raw
             FROM identifiers i
             LEFT JOIN raw_observations ro
                    ON ro.promoted_identifier_id = i.id
            WHERE i.source_type = 'inferred'
            ORDER BY i.id"""
    ).fetchall()
    staged_count = len(staged)

    rng = random.Random(RANDOM_SEED)
    sample = rng.sample(staged, k=min(SAMPLE_SIZE, staged_count))

    findings: list[dict] = []
    halt_class_triggers: list[str] = []

    for row in sample:
        cm_raw = (row["candidate_manufacturer_raw"] or "").strip()
        cm_lower = cm_raw.lower()
        manufacturer = row["manufacturer"]
        finding = {
            "identifier_id": row["identifier_id"],
            "raw_observation_id": row["raw_obs_id"],
            "identifier": row["identifier"],
            "identifier_type": row["identifier_type"],
            "device_category": row["device_category"],
            "manufacturer": manufacturer,
            "confidence": row["confidence"],
            "source_type": row["source_type"],
            "candidate_manufacturer_raw": cm_raw,
            "checks": {},
        }
        # Check 1 — bare Motorola not promoted.
        if cm_lower in ("motorola",):
            finding["checks"]["bare_motorola_not_promoted"] = "FAIL"
            halt_class_triggers.append(
                f"identifier_id={row['identifier_id']}: bare Motorola promoted"
            )
        else:
            finding["checks"]["bare_motorola_not_promoted"] = "ok"
        # Check 2 — Motorola Mobility / (Wuhan) / Lenovo not under Solutions.
        bad_solutions_substrings = ("mobility", "(wuhan)", "lenovo")
        if manufacturer == "Motorola Solutions" and any(
            s in cm_lower for s in bad_solutions_substrings
        ):
            finding["checks"]["motorola_mobility_not_under_solutions"] = "FAIL"
            halt_class_triggers.append(
                f"identifier_id={row['identifier_id']}: Mobility/Wuhan/Lenovo "
                f"under Motorola Solutions"
            )
        else:
            finding["checks"]["motorola_mobility_not_under_solutions"] = "ok"
        # Check 3 — WatchGuard Technologies not under WatchGuard.
        if (
            manufacturer == "WatchGuard"
            and "watchguard technologies" in cm_lower
        ):
            finding["checks"]["watchguard_technologies_not_under_video"] = "FAIL"
            halt_class_triggers.append(
                f"identifier_id={row['identifier_id']}: WatchGuard "
                f"Technologies under WatchGuard"
            )
        else:
            finding["checks"]["watchguard_technologies_not_under_video"] = "ok"
        # Check 4 — Harris Adacom not under Harris.
        if manufacturer == "Harris" and "harris adacom" in cm_lower:
            finding["checks"]["harris_adacom_not_under_harris"] = "FAIL"
            halt_class_triggers.append(
                f"identifier_id={row['identifier_id']}: Harris Adacom under Harris"
            )
        else:
            finding["checks"]["harris_adacom_not_under_harris"] = "ok"
        # Check 5 — confidence in §8.2 inferred band (30-70).
        if not (30 <= row["confidence"] <= 70):
            finding["checks"]["confidence_in_inferred_band"] = "FAIL"
            halt_class_triggers.append(
                f"identifier_id={row['identifier_id']}: confidence "
                f"{row['confidence']} outside §8.2 inferred 30-70 band"
            )
        else:
            finding["checks"]["confidence_in_inferred_band"] = "ok"
        # Check 6 — device_category='unknown' (strict §8.4 binding).
        if row["device_category"] != "unknown":
            finding["checks"]["device_category_unknown"] = "FAIL"
            halt_class_triggers.append(
                f"identifier_id={row['identifier_id']}: device_category="
                f"{row['device_category']!r} (expected 'unknown')"
            )
        else:
            finding["checks"]["device_category_unknown"] = "ok"
        # Check 7 — superseded_by NULL at staging time (canonical row).
        if row["superseded_by"] is not None:
            finding["checks"]["superseded_by_null"] = "FAIL"
            halt_class_triggers.append(
                f"identifier_id={row['identifier_id']}: superseded_by="
                f"{row['superseded_by']!r} (expected NULL at staging)"
            )
        else:
            finding["checks"]["superseded_by_null"] = "ok"
        # Check 8 — provenance carry-over (source_url + source_excerpt non-empty).
        if not row["source_url"] or not row["source_excerpt"]:
            finding["checks"]["provenance_carried"] = "FAIL"
            halt_class_triggers.append(
                f"identifier_id={row['identifier_id']}: missing provenance "
                f"(source_url={row['source_url']!r} / source_excerpt="
                f"{row['source_excerpt']!r})"
            )
        else:
            finding["checks"]["provenance_carried"] = "ok"
        findings.append(finding)

    # Per-vendor distribution sanity — Motorola Solutions count should be ≤ ~25.
    per_vendor_dist = {}
    for r in staged:
        per_vendor_dist[r["manufacturer"]] = (
            per_vendor_dist.get(r["manufacturer"], 0) + 1
        )

    motorola_count = per_vendor_dist.get("Motorola Solutions", 0)
    motorola_count_ok = motorola_count <= 25
    if not motorola_count_ok:
        halt_class_triggers.append(
            f"Motorola Solutions count {motorola_count} exceeds dispatch "
            f"~25 expectation"
        )

    out = {
        "_meta": {
            "produced_at_utc": datetime.now(timezone.utc).isoformat(),
            "validator_agent_id": "da137694-2efe-4589-8150-828dcab881fb",
            "phase_5_step": "Step-4 follow-on² (MAC-44) — Step E spot-check",
            "issue_chain": "MAC-36 → MAC-39 → MAC-41 → MAC-44",
            "amendments_applied": [
                "SAR-1 (LAA-bit penalty)",
                "SAR-7 #1/#2/#3 (codified upstream)",
                "SAR-8 (vendor-name-disambig)",
                "SAR-9 #1/#2/#3 (Motorola corporate-split FP + caller "
                "restructure + WatchGuard Technologies hard-reject)",
            ],
            "random_seed": RANDOM_SEED,
            "sample_size": len(sample),
            "staged_total": staged_count,
            "sample_pct": (
                round(100.0 * len(sample) / staged_count, 2)
                if staged_count
                else 0
            ),
        },
        "halt_class_triggered": bool(halt_class_triggers),
        "halt_class_triggers": halt_class_triggers,
        "per_vendor_distribution": per_vendor_dist,
        "motorola_solutions_count_within_dispatch_band": motorola_count_ok,
        "checks": findings,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"Spot-check report written: {OUT_PATH}")
    print(json.dumps(
        {
            "halt_class_triggered": out["halt_class_triggered"],
            "halt_class_triggers": halt_class_triggers,
            "sample_size": len(sample),
            "staged_total": staged_count,
            "motorola_solutions_count": motorola_count,
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
