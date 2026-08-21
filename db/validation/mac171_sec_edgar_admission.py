"""MAC-171 P3 — SEC EDGAR admission + RG5 yield ingest + corroboration reversal.

Five disjoint write paths, applied in order against ``db/argus.db``:

  1. INSERT one ``sources`` row for SEC EDGAR (source_type=disclosure_filing,
     tier=1). License-into-notes folding per CP23 cycle-1 finding #1
     (PUBLIC_DOMAIN in notes_json). user_agent_used field has operator
     email replaced with ``<operator_redacted_per_SAR5>`` per CEO Q4
     adjudication at MAC-171 35ebb1bf + SAR-5 PII token convention.
  2. UPSERT 21 product families into ``manufacturers.notes.disclosed_products``
     across mfg_id 15 (Axon, 11 products), mfg_id 26 (SoundThinking,
     3 products — DROP "prevent" per CEO Q1 paste-not-cite), mfg_id 5
     (Rekor, 7 products — DROP "Automatic License Plate Recognition" per
     CEO category-not-product call). Idempotent on existing (product_family
     per mfg) — re-runs skip already-present entries.
  3. INSERT 5 net-new ``procurement_records`` rows for SSTI customer
     attestations from SEC 10-K Item 1/Item 7. source_type='regulatory'
     (SEC mandatory-disclosure filing is the strict §8.2-band fit; CP23 §1
     carve-out — new disclosure_filing source-tier does NOT lift per-row
     promotion-pipeline band). confidence=85 (single-source band; no
     §8.3 lift). Idempotent on (source_url) where each row carries a
     synthesized ``#sec_extraction:`` fragment for uniqueness.
  4. UPDATE ``procurement_records.id=86738`` — retract MAC-172 §4
     ``notes.cross_source_corroboration[]`` entry for SSTI × DHS Item 1A
     (§11 #1 FP — Congressional IG-investigation request, not customer
     attestation per MAC-171 §C #5). Append parallel
     ``notes.cross_source_corroboration_reversals[]`` audit entry per
     CP25 §1 schema. Idempotent — re-runs detect existing reversal entry
     by marker_key.
  5. Stage 32 operator-review rows under
     ``extraction_outputs/mac171/operator_review/`` (worker's CWD per
     [feedback_argus_working_repo_canonical_path], NOT ~/argus-internal/):
     28 aggregate-concentration + 3 §11 #1 FPs (SSTI×ICE, SSTI×DHS,
     Rekor×FBI) + 1 ambiguous (SSTI×FBI Item 1A). No DB write.

§11 hard-rule compliance:
  - §11 #1 no fabrication — every row carries verbatim SEC 10-K excerpts
    + section-anchored EDGAR URLs (fair-use ≤30-word cap respected);
    3 FPs + 1 ambiguous deferred to disk-stage rather than promoted.
  - §11 #3 PII — operator email sanitized in sources.notes_json.
  - §11 #7 provenance is the database — every INSERT/UPDATE carries
    source_url + source_excerpt + per-row marker_key in notes.
  - §11 #8 no confidence drift — Step 4 is a corroboration-marker
    retraction (not a confidence change); §8.3 lift was never applied to
    id=86738 so no companion ``confidence_history[]`` entry needed.
  - §11 #14 procurement-only never exported to Lynceus — these rows stay
    procurement-side; no identifier-promotion happens here.

Run from repo root::

    python3 db/validation/mac171_sec_edgar_admission.py --dry-run
    python3 db/validation/mac171_sec_edgar_admission.py --commit
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DB = REPO_ROOT / "db" / "argus.db"
HANDOFF_DIR = (
    Path.home()
    / "argus-internal"
    / "extraction_outputs"
    / "sec_edgar_admission"
)
STAGE_DIR = REPO_ROOT / "extraction_outputs" / "mac171" / "operator_review"

DISPATCH = "MAC-171"
SESSION = "sec_edgar_admission"
CP_REVERSAL_ANCHOR = "CP25 §1"
SAR5_TOKEN = "<operator_redacted_per_SAR5>"
SEC_EDGAR_NAME = "SEC EDGAR"
SEC_EDGAR_URL = "https://www.sec.gov/edgar"
SOURCE_EXCERPT_MAX = 200  # procurement_records.source_excerpt CHECK cap
SSTI_MFG_ID = 26
CONFIDENCE = 85  # §8.2 single-source band; no §8.3 lift per CP23 §1

# MAC-172 markers on id=86738 to retract (§11 #1 FP per MAC-171 §C #5).
# Note: MAC-172 §4 added TWO markers to id=86738 — one keyed by id=86738's own
# award_id (HSSS0116C0028) and one keyed by id=86737's award_id (70US0921C70090087);
# both carry the SAME FP excerpt (Congressional IG-investigation request). Both
# get retracted at MAC-171 per CP25 §1. Companion observation: id=86737 was
# never marked by MAC-172 despite both rows being the DHS USSS cohort — the FP
# disposition makes that omission moot.
ROLLBACK_TARGET_PR_ID = 86738
ROLLBACK_MARKER_KEYS = [
    (
        "rg5_sec_edgar::"
        "https://www.sec.gov/Archives/edgar/data/1351636/000119312526132104/ssti-20251231.htm"
        "::HSSS0116C0028"
    ),
    (
        "rg5_sec_edgar::"
        "https://www.sec.gov/Archives/edgar/data/1351636/000119312526132104/ssti-20251231.htm"
        "::70US0921C70090087"
    ),
]
ROLLBACK_RATIONALE = (
    "§11 #1 FP — SEC Item 1A excerpt describes Congressional IG-investigation "
    "request, not a DHS customer relationship (MAC-171 §C #5 walkthrough; "
    "CEO ratification at MAC-171 35ebb1bf)."
)


@dataclass
class StepResult:
    name: str
    proposed: int
    applied: int
    skipped_idempotent: int
    notes: list[str] = field(default_factory=list)


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sanitize_ua_email(ua: str) -> str:
    """Replace any e-mail-shaped token in the UA string with SAR-5 token."""
    import re
    return re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        SAR5_TOKEN,
        ua,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Source-row construction (SEC EDGAR admission)
# ─────────────────────────────────────────────────────────────────────────────


def build_sources_notes() -> dict[str, Any]:
    handoff_meta_path = HANDOFF_DIR / "source_admission_metadata.json"
    with handoff_meta_path.open() as f:
        meta_list = json.load(f)
    assert len(meta_list) == 1, "expected single SEC EDGAR entry in handoff"
    meta = meta_list[0]
    src_notes = dict(meta.get("notes_json", {}))
    # CP23 cycle-1 finding #1 — license-into-notes folding.
    src_notes["license"] = meta["license"]
    src_notes["license_attribution"] = meta["license_attribution"]
    # CEO Q4 adjudication — sanitize operator email per SAR-5 token.
    if "user_agent_used" in src_notes:
        src_notes["user_agent_used"] = _sanitize_ua_email(src_notes["user_agent_used"])
        src_notes["user_agent_sanitization_at_utc"] = _now_iso()
        src_notes["user_agent_sanitization_anchor"] = "MAC-171 §A + CEO Q4"
    # Dispatch markers.
    src_notes["dispatch"] = DISPATCH
    src_notes["paperclip_admission_session"] = SESSION
    src_notes["validator_handoff_path"] = (
        "~/argus-internal/extraction_outputs/sec_edgar_admission/HANDOFF_TO_VALIDATOR.md"
    )
    return src_notes


def step_1_insert_source(conn: sqlite3.Connection, *, commit: bool) -> StepResult:
    notes = []
    existing = conn.execute(
        "SELECT id FROM sources WHERE name = ? OR url = ?",
        (SEC_EDGAR_NAME, SEC_EDGAR_URL),
    ).fetchone()
    if existing is not None:
        notes.append(f"SEC EDGAR sources row already present at id={existing[0]} — skipping")
        return StepResult(
            name="step_1_insert_source",
            proposed=1,
            applied=0,
            skipped_idempotent=1,
            notes=notes,
        )
    src_notes = build_sources_notes()
    if commit:
        cur = conn.execute(
            """
            INSERT INTO sources (name, url, source_type, tier,
                                  last_fetched_at, last_status, notes)
            VALUES (?, ?, 'disclosure_filing', 1, ?, 'success', ?)
            """,
            (
                SEC_EDGAR_NAME,
                SEC_EDGAR_URL,
                src_notes.get("admission_date_utc") or _now_iso(),
                json.dumps(src_notes, sort_keys=True),
            ),
        )
        new_id = cur.lastrowid
        notes.append(f"sources INSERT applied; new id={new_id}")
    else:
        notes.append("sources INSERT proposed (dry-run)")
    notes.append(
        f"UA sanitized: {'yes' if SAR5_TOKEN in src_notes.get('user_agent_used','') else 'n/a (no email pattern found)'}"
    )
    return StepResult(
        name="step_1_insert_source",
        proposed=1,
        applied=1 if commit else 0,
        skipped_idempotent=0,
        notes=notes,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Manufacturer enrichments (21 products across 3 mfgs)
# ─────────────────────────────────────────────────────────────────────────────


ENRICHMENTS = {
    15: {
        "canonical_name": "Axon",
        "products": [
            ("TASER", "Item 1"),
            ("Axon Body", "Item 1"),
            ("Axon Fleet", "Item 1"),
            ("Axon Evidence", "Item 1"),
            ("Axon Records", "Item 1"),
            ("Axon Respond", "Item 1"),
            ("Axon Air", "Item 1A"),
            ("Dedrone", "Item 1A"),
            ("Sky-Hero", "Item 1A"),
            ("TASER 10", "Item 7"),
            ("Axon Body 4", "Item 7"),
        ],
        "source_url": (
            "https://www.sec.gov/Archives/edgar/data/1069183/"
            "000162828026011360/axon-20251231.htm"
        ),
    },
    26: {
        "canonical_name": "SoundThinking",
        "products": [
            ("ShotSpotter", "Item 1"),
            ("SafetySmart", "Item 1"),
            ("CrimeTracer", "Item 1"),
            ("ResourceRouter", "Item 1"),
        ],
        "source_url": (
            "https://www.sec.gov/Archives/edgar/data/1351636/"
            "000119312526132104/ssti-20251231.htm"
        ),
    },
    5: {
        "canonical_name": "Rekor",
        "products": [
            ("Rekor One", "Item 1"),
            ("Rekor Command", "Item 1"),
            ("Rekor Discover", "Item 1"),
            ("Rekor Scout", "Item 1"),
            ("Rekor CarCheck", "Item 1"),
            ("Rekor Edge", "Item 1"),
            ("Waycare", "Item 1"),
        ],
        "source_url": (
            "https://www.sec.gov/Archives/edgar/data/1697851/"
            "000143774926010647/rekr20251231_10k.htm"
        ),
    },
}


def step_2_enrich_manufacturers(conn: sqlite3.Connection, *, commit: bool) -> StepResult:
    total_proposed = sum(len(v["products"]) for v in ENRICHMENTS.values())
    applied = 0
    skipped = 0
    notes_out: list[str] = []
    for mfg_id, spec in ENRICHMENTS.items():
        row = conn.execute(
            "SELECT canonical_name, notes FROM manufacturers WHERE id = ?",
            (mfg_id,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"manufacturer id={mfg_id} not found")
        canonical_name, notes_raw = row
        if canonical_name != spec["canonical_name"]:
            raise RuntimeError(
                f"mfg id={mfg_id} canonical_name mismatch: "
                f"DB has {canonical_name!r}, expected {spec['canonical_name']!r}"
            )
        # manufacturers.notes is freeform TEXT: 34 rows store prose, 1 row
        # (mfg_id=205 Johnson Matthey via MAC-170) stores JSON. To support
        # the brief's `manufacturers.notes.disclosed_products` UPSERT, wrap
        # prose into {description, disclosed_products} on first touch.
        notes_text = (notes_raw or "").strip()
        if notes_text.startswith("{") and notes_text.endswith("}"):
            mfg_notes = json.loads(notes_text)
        elif notes_text:
            mfg_notes = {
                "description": notes_text,
                "description_preserved_from_prose_at_utc": _now_iso(),
                "shape_migration_dispatch": DISPATCH,
            }
        else:
            mfg_notes = {}
        disclosed = mfg_notes.setdefault("disclosed_products", [])
        existing_pf = {
            d.get("product_family") for d in disclosed if isinstance(d, dict)
        }
        per_mfg_added = 0
        for product_family, section_ref in spec["products"]:
            if product_family in existing_pf:
                skipped += 1
                continue
            disclosed.append({
                "product_family": product_family,
                "sec_filing_source_url": spec["source_url"],
                "section_ref": section_ref,
                "admission_dispatch": DISPATCH,
                "admission_session": SESSION,
                "added_at_utc": _now_iso(),
            })
            applied += 1
            per_mfg_added += 1
        if per_mfg_added > 0 and commit:
            conn.execute(
                "UPDATE manufacturers SET notes = ? WHERE id = ?",
                (json.dumps(mfg_notes, sort_keys=True), mfg_id),
            )
        notes_out.append(
            f"mfg_id={mfg_id} ({canonical_name}): +{per_mfg_added} products "
            f"(existing total now {len(disclosed)})"
        )
    return StepResult(
        name="step_2_enrich_manufacturers",
        proposed=total_proposed,
        applied=applied if commit else 0,
        skipped_idempotent=skipped,
        notes=notes_out,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Procurement records — 5 SSTI customer attestations
# ─────────────────────────────────────────────────────────────────────────────


SSTI_BASE_URL = (
    "https://www.sec.gov/Archives/edgar/data/1351636/"
    "000119312526132104/ssti-20251231.htm"
)
SSTI_CANONICAL = "SOUNDTHINKING, INC."
SSTI_NORMALIZED = "soundthinking"  # per db/normalize_vendor.py

# The 5 valid customer-attestation rows per MAC-171 §C + CEO authorized
# write-set. Indices match the order in the handoff named_government_customers
# JSON (after dropping #1 ICE, #5 DHS, #6 FBI-ambig, #9 Rekor FBI).
PROCUREMENT_ROWS = [
    {
        "row_key": "ssti_item1_nypd",
        "handoff_index": 1,
        "agency_name": "New York Police Department",
        "agency_geographic_scope": "US-NY",
        "section_ref": "Item 1",
        "excerpt": (
            "ides a complete case management solution for detectives and "
            "supervisors in local, state and federal law enforcement "
            "agencies. It has been used by the New York Police Department "
            "for years"
        ),
        "product_family_hint": "CrimeTracer",
    },
    {
        "row_key": "ssti_item1_nyc",
        "handoff_index": 2,
        "agency_name": "City of New York",
        "agency_geographic_scope": "US-NY",
        "section_ref": "Item 1",
        "excerpt": (
            "e United States. As of December 31, 2025, we had 291 SafePointe "
            "lanes under contract. For the year ended December 31, 2025, "
            "our largest customer, the City of New York,"
        ),
        "product_family_hint": None,
    },
    {
        "row_key": "ssti_item1_chicago",
        "handoff_index": 3,
        "agency_name": "City of Chicago",
        "agency_geographic_scope": "US-IL",
        "section_ref": "Item 1",
        "excerpt": (
            "he City of New York, accounted for 29% of our revenues. For the "
            "year ended December 31, 2024, our two largest customers, the "
            "City of New York and the City"
        ),
        "product_family_hint": None,
    },
    {
        "row_key": "ssti_item7_nycpd_renewal",
        "handoff_index": 6,
        "agency_name": "New York City Police Department",
        "agency_geographic_scope": "US-NY",
        "section_ref": "Item 7",
        "excerpt": (
            "coverage areas, $3.7 million increase in revenue from New York "
            "City, $3.5 million of catch-up revenue from two three-year "
            "contract renewals with the New York City Police Department "
            "which were"
        ),
        "product_family_hint": None,
    },
    {
        "row_key": "ssti_item7_nypd_commission",
        "handoff_index": 7,
        "agency_name": "NYPD",
        "agency_geographic_scope": "US-NY",
        "section_ref": "Item 7",
        "excerpt": (
            "keting expense decreased by $2.0 million, primarily due to $1.7 "
            "million in commission expense related to brokerage services for "
            "the contract with the NYPD in 2024 without a corresponding service"
        ),
        "product_family_hint": None,
    },
]


def _ssti_source_url(row_key: str) -> str:
    """Compose source_url with fragment for per-row idempotency uniqueness."""
    return f"{SSTI_BASE_URL}#sec_extraction:{row_key}"


def step_3_insert_procurement(conn: sqlite3.Connection, *, commit: bool) -> StepResult:
    proposed = len(PROCUREMENT_ROWS)
    applied = 0
    skipped = 0
    notes_out: list[str] = []
    for row in PROCUREMENT_ROWS:
        url = _ssti_source_url(row["row_key"])
        existing = conn.execute(
            "SELECT id FROM procurement_records WHERE source_url = ?", (url,)
        ).fetchone()
        if existing is not None:
            skipped += 1
            notes_out.append(f"skip {row['row_key']} — already present at id={existing[0]}")
            continue
        excerpt = (row["excerpt"] or "")[:SOURCE_EXCERPT_MAX]
        per_row_notes = {
            "dispatch": DISPATCH,
            "paperclip_admission_session": SESSION,
            "row_key": row["row_key"],
            "handoff_index": row["handoff_index"],
            "sec_filing": "ssti-20251231 (10-K, FY2025)",
            "section_ref": row["section_ref"],
            "source_admission_session": "sec_edgar",
            "captured_at_utc": _now_iso(),
            "extraction_method": "named_customer_textual_attestation",
            "confidence_band": "§8.2 regulatory 80-95; conf=85 single-source per CEO MAC-171 35ebb1bf",
            "license": "PUBLIC_DOMAIN",
            "product_family_hint": row["product_family_hint"],
        }
        if commit:
            conn.execute(
                """
                INSERT INTO procurement_records (
                    agency_name, agency_geographic_scope, vendor_canonical_name,
                    product_family, contract_amount_usd, contract_date,
                    source_url, source_type, source_excerpt, confidence,
                    captured_at, linked_identifier_id, notes,
                    vendor_canonical_normalized
                ) VALUES (?, ?, ?, ?, NULL, NULL, ?, 'regulatory', ?, ?,
                          CURRENT_TIMESTAMP, NULL, ?, ?)
                """,
                (
                    row["agency_name"],
                    row["agency_geographic_scope"],
                    SSTI_CANONICAL,
                    row["product_family_hint"],
                    url,
                    excerpt,
                    CONFIDENCE,
                    json.dumps(per_row_notes, sort_keys=True),
                    SSTI_NORMALIZED,
                ),
            )
        applied += 1
        notes_out.append(f"insert {row['row_key']} agency={row['agency_name']}")
    return StepResult(
        name="step_3_insert_procurement",
        proposed=proposed,
        applied=applied if commit else 0,
        skipped_idempotent=skipped,
        notes=notes_out,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Cross-source corroboration reversal on id=86738 (CP25 §1)
# ─────────────────────────────────────────────────────────────────────────────


def step_4_reverse_corroboration(conn: sqlite3.Connection, *, commit: bool) -> StepResult:
    notes_out: list[str] = []
    row = conn.execute(
        "SELECT notes FROM procurement_records WHERE id = ?",
        (ROLLBACK_TARGET_PR_ID,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"target procurement_records.id={ROLLBACK_TARGET_PR_ID} not found")
    pr_notes = json.loads(row[0] or "{}")
    reversals = pr_notes.setdefault("cross_source_corroboration_reversals", [])
    existing_reversal_keys = {r.get("marker_key") for r in reversals}
    keys_to_process = [k for k in ROLLBACK_MARKER_KEYS if k not in existing_reversal_keys]
    if not keys_to_process:
        notes_out.append(
            f"idempotent: all {len(ROLLBACK_MARKER_KEYS)} reversal entries "
            f"already present on id={ROLLBACK_TARGET_PR_ID}"
        )
        return StepResult(
            name="step_4_reverse_corroboration",
            proposed=len(ROLLBACK_MARKER_KEYS),
            applied=0,
            skipped_idempotent=len(ROLLBACK_MARKER_KEYS),
            notes=notes_out,
        )
    corr_list = pr_notes.get("cross_source_corroboration", [])
    pre_count = len(corr_list)
    pr_notes["cross_source_corroboration"] = [
        m for m in corr_list if m.get("marker_key") not in keys_to_process
    ]
    removed = pre_count - len(pr_notes["cross_source_corroboration"])
    if removed == 0 and keys_to_process:
        notes_out.append(
            f"WARN: no cross_source_corroboration[] entries matched the "
            f"{len(keys_to_process)} target marker_key(s); appending reversal "
            "entries anyway for audit-trail completeness"
        )
    for key in keys_to_process:
        reversals.append({
            "at_utc": _now_iso(),
            "marker_key": key,
            "rationale": ROLLBACK_RATIONALE,
            "dispatch": DISPATCH,
            "cp_anchor": CP_REVERSAL_ANCHOR,
        })
    if commit:
        conn.execute(
            "UPDATE procurement_records SET notes = ? WHERE id = ?",
            (json.dumps(pr_notes, sort_keys=True), ROLLBACK_TARGET_PR_ID),
        )
    notes_out.append(
        f"reversals appended: +{len(keys_to_process)}; removed {removed} "
        f"cross_source_corroboration[] entries; reversals[] now has "
        f"{len(reversals)} total"
    )
    return StepResult(
        name="step_4_reverse_corroboration",
        proposed=len(ROLLBACK_MARKER_KEYS),
        applied=len(keys_to_process) if commit else 0,
        skipped_idempotent=len(ROLLBACK_MARKER_KEYS) - len(keys_to_process),
        notes=notes_out,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Disk-stage 32 operator-review rows
# ─────────────────────────────────────────────────────────────────────────────


def step_5_disk_stage(conn: sqlite3.Connection, *, commit: bool) -> StepResult:
    notes_out: list[str] = []
    proposed = 0
    applied = 0
    skipped = 0
    STAGE_DIR.mkdir(parents=True, exist_ok=True)

    # Subset A — 28 aggregate-concentration rows (schema-rejected by NOT NULL).
    aggr_src = HANDOFF_DIR / "aggregate_concentration_only.json"
    with aggr_src.open() as f:
        aggr_rows = json.load(f)
    aggr_dst = STAGE_DIR / "aggregate_concentration_28.json"
    proposed += len(aggr_rows)
    if aggr_dst.exists():
        skipped += len(aggr_rows)
        notes_out.append(f"skip aggregate (already staged at {aggr_dst.name})")
    else:
        if commit:
            with aggr_dst.open("w") as f:
                json.dump(
                    {
                        "dispatch": DISPATCH,
                        "session": SESSION,
                        "staged_at_utc": _now_iso(),
                        "disposition": (
                            "operator-review tier; schema-rejected for "
                            "procurement_records (agency_name NOT NULL); useful "
                            "aggregate-financial context without specific-agency "
                            "anchor"
                        ),
                        "row_count": len(aggr_rows),
                        "rows": aggr_rows,
                    },
                    f,
                    indent=2,
                    sort_keys=True,
                )
        applied += len(aggr_rows)
        notes_out.append(f"wrote {len(aggr_rows)} aggregate rows → {aggr_dst.name}")

    # Subset B — 3 §11 #1 false-positives + 1 ambiguous.
    nc_src = HANDOFF_DIR / "named_government_customers.json"
    with nc_src.open() as f:
        all_nc = json.load(f)
    # Indices match the handoff order; FP set + ambiguous set per MAC-171 §C.
    fp_set = {
        # SSTI × ICE Item 1 — about competitors' practices
        (0, "Immigration and Customs Enforcement", "Item 1"),
        # SSTI × DHS Item 1A — Congressional IG-investigation request
        (4, "Department of Homeland Security", "Item 1A"),
        # Rekor × FBI Item 1 — CJIS compliance certification
        (8, "Federal Bureau of Investigation", "Item 1"),
    }
    ambig_set = {
        # SSTI × FBI Item 1A — historical 2011 reference; meaning truncated
        (5, "Federal Bureau of Investigation", "Item 1A"),
    }
    fp_rows: list[dict[str, Any]] = []
    ambig_rows: list[dict[str, Any]] = []
    for i, row in enumerate(all_nc):
        key = (i, row.get("matched_agency"), row.get("section_ref"))
        if key in fp_set:
            tagged = dict(row)
            tagged["mac171_disposition"] = "false_positive"
            tagged["mac171_rationale"] = {
                "Immigration and Customs Enforcement": (
                    "Excerpt describes COMPETITORS' data-sharing practices, not "
                    "SSTI's own customer relationship with ICE."
                ),
                "Department of Homeland Security": (
                    "Excerpt describes Congressional IG-investigation request, not "
                    "a customer relationship between SSTI and DHS."
                ),
                "Federal Bureau of Investigation": (
                    "Excerpt describes Rekor mobile-app compliance with FBI CJIS "
                    "standards, not a customer relationship."
                ),
            }.get(row.get("matched_agency"), "Operator review.")
            fp_rows.append(tagged)
        elif key in ambig_set:
            tagged = dict(row)
            tagged["mac171_disposition"] = "ambiguous"
            tagged["mac171_rationale"] = (
                "Historical 2011 FBI reference; meaning truncated by 30-word "
                "fair-use cap. USAspending shows 2009–2013 FBI×SSTI contracts; "
                "deferred to operator-review per CEO Q2 — no DB write either way."
            )
            ambig_rows.append(tagged)
    assert len(fp_rows) == 3, f"expected 3 FPs, got {len(fp_rows)}"
    assert len(ambig_rows) == 1, f"expected 1 ambiguous, got {len(ambig_rows)}"

    fp_dst = STAGE_DIR / "named_customer_false_positives_3.json"
    proposed += 3
    if fp_dst.exists():
        skipped += 3
        notes_out.append(f"skip FPs (already staged at {fp_dst.name})")
    else:
        if commit:
            with fp_dst.open("w") as f:
                json.dump(
                    {
                        "dispatch": DISPATCH,
                        "session": SESSION,
                        "staged_at_utc": _now_iso(),
                        "disposition": "§11 #1 false-positives — DO NOT promote",
                        "row_count": 3,
                        "rows": fp_rows,
                    },
                    f,
                    indent=2,
                    sort_keys=True,
                )
        applied += 3
        notes_out.append(f"wrote 3 FP rows → {fp_dst.name}")

    ambig_dst = STAGE_DIR / "named_customer_ambiguous_1.json"
    proposed += 1
    if ambig_dst.exists():
        skipped += 1
        notes_out.append(f"skip ambiguous (already staged at {ambig_dst.name})")
    else:
        if commit:
            with ambig_dst.open("w") as f:
                json.dump(
                    {
                        "dispatch": DISPATCH,
                        "session": SESSION,
                        "staged_at_utc": _now_iso(),
                        "disposition": "ambiguous — operator review",
                        "row_count": 1,
                        "rows": ambig_rows,
                    },
                    f,
                    indent=2,
                    sort_keys=True,
                )
        applied += 1
        notes_out.append(f"wrote 1 ambiguous row → {ambig_dst.name}")

    # README pointer for the staging directory.
    readme_dst = STAGE_DIR / "README.md"
    if not readme_dst.exists() and commit:
        readme_dst.write_text(
            f"""# MAC-171 P3 SEC EDGAR — operator-review staging

Dispatch: [{DISPATCH}](<TRACKER_URL>issues/{DISPATCH})
Session: {SESSION}
Staged at (UTC): {_now_iso()}

## Contents

| File | Rows | Disposition |
|---|---|---|
| `aggregate_concentration_28.json` | 28 | Operator-review tier. `procurement_records.agency_name` NOT NULL rejects rows without a specific-agency anchor; useful aggregate-financial context (e.g. "largest customer accounted for 29% of revenues") retained on disk only. |
| `named_customer_false_positives_3.json` | 3 | §11 #1 false-positives identified in MAC-171 §C walkthrough — SSTI×ICE (about competitors), SSTI×DHS Item 1A (about Congressional IG-investigation request), Rekor×FBI Item 1 (about CJIS compliance). DO NOT promote. |
| `named_customer_ambiguous_1.json` | 1 | SSTI×FBI Item 1A historical-2011 reference; meaning truncated by 30-word fair-use cap. USAspending FBI rows stand independently at conf=85 (no §8.3 lift). Operator may re-fetch fuller filing context to adjudicate; no DB write either way absent operator confirmation. |

## Provenance

Source extraction outputs live at `~/argus-internal/extraction_outputs/sec_edgar_admission/`:
- `aggregate_concentration_only.json` (28 rows)
- `named_government_customers.json` (9 rows; 5 promoted to `procurement_records`, 3 FPs + 1 ambiguous staged here)

CEO ratification at [`35ebb1bf`](<TRACKER_URL>issues/MAC-171#comment-35ebb1bf-d99b-46d3-b31b-c15b2399dfa5); Validator §7.4 walkthrough at [`727ffcf0`](<TRACKER_URL>issues/MAC-171#comment-727ffcf0-8875-4580-a4b8-908a06ee81cb).
"""
        )
        notes_out.append(f"wrote {readme_dst.name}")

    return StepResult(
        name="step_5_disk_stage",
        proposed=proposed,
        applied=applied if commit else 0,
        skipped_idempotent=skipped,
        notes=notes_out,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────────────────────────────────────


STEPS = [
    step_1_insert_source,
    step_2_enrich_manufacturers,
    step_3_insert_procurement,
    step_4_reverse_corroboration,
    step_5_disk_stage,
]


def run(commit: bool) -> int:
    if not DB.exists():
        print(f"FATAL: DB not found at {DB}", file=sys.stderr)
        return 2
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("BEGIN IMMEDIATE")
    results: list[StepResult] = []
    try:
        for step in STEPS:
            results.append(step(con, commit=commit))
        if commit:
            con.commit()
        else:
            con.rollback()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

    # ── pretty-print summary
    mode = "COMMIT" if commit else "DRY-RUN"
    print(f"\n== MAC-171 ingest summary ({mode}) ==")
    for r in results:
        print(
            f"  {r.name}: proposed={r.proposed} applied={r.applied} "
            f"skipped_idempotent={r.skipped_idempotent}"
        )
        for n in r.notes:
            print(f"    - {n}")

    # ── post-state snapshot (paste-not-cite preamble inputs)
    if commit:
        con = sqlite3.connect(DB)
        cur = con.cursor()
        cur.execute("SELECT count(*) FROM sources")
        sources_n = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM identifiers")
        ident_n = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM identifiers WHERE superseded_by IS NULL")
        ident_live = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM behavioral_signatures")
        bs_n = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM procurement_records")
        pr_n = cur.fetchone()[0]
        cur.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
        ver = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM raw_observations")
        ro_n = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM manufacturers")
        mfg_n = cur.fetchone()[0]
        con.close()
        print("\n== post-write state ==")
        print(f"  schema_version        = {ver}")
        print(f"  sources               = {sources_n}")
        print(f"  manufacturers         = {mfg_n}")
        print(f"  identifiers_total     = {ident_n}")
        print(f"  identifiers_live      = {ident_live}")
        print(f"  procurement_records   = {pr_n}")
        print(f"  raw_observations      = {ro_n}")
        print(f"  behavioral_signatures = {bs_n}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="MAC-171 P3 SEC EDGAR ingest")
    p.add_argument("--commit", action="store_true", help="commit writes to DB + disk")
    p.add_argument("--dry-run", action="store_true", help="default; no writes")
    args = p.parse_args(argv)
    if args.commit and args.dry_run:
        print("ERROR: --commit and --dry-run are mutually exclusive", file=sys.stderr)
        return 2
    return run(commit=args.commit)


if __name__ == "__main__":
    sys.exit(main())
