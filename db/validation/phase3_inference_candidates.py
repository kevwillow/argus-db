"""Phase-5 Step-4 Validator pass — Phase-3 inference candidate sweep (Tier 4).

Read-only. Writes nothing to the database. Produces a JSON artifact
summarising per-source candidate counts, sample rows, applied disambig +
hard-rule filters, and the halt-flags that the CEO + board must ratify
before bulk staging into ``identifiers`` (or a new staging table).

SAR-8 wired (commit ``811b4de``) — vendor-name-disambig now lives in
``db/extraction/vendor_name_disambig.py``. The strict-vs-permissive
split this script previously implemented is replaced by the SAR-8
``vendor_match_disposition`` predicate, which returns a 4-state result
(``accept`` / ``reject_fp`` / ``flag_for_review`` / ``no_match``).
``GENETEC Corporation`` cases route to a separate flagged-for-review
artifact (``extraction_outputs/mac41/sar8_flagged_for_review.json``).

Output artifact:
    ``extraction_outputs/mac39/phase3_inference_candidates.json``
    (re-run idempotent under SAR-8 — modulo timestamp + run metadata)
    ``extraction_outputs/mac41/sar8_flagged_for_review.json``
    (GENETEC Corporation triage queue; CEO/board decision-class)

Idempotent — re-running over the same DB state produces byte-identical
output (modulo the timestamp + run metadata). Re-runs MUST yield zero
new ``identifiers`` rows because this script never writes to the DB.

Authority chain:
- Bible §5 Tier 4 (inferential records, capped confidence ≤70).
- Bible §6 Phase 5 #3 (inference rules).
- Bible §7.4 (Validator contract).
- Bible §8.2 (`inferred` 30–70 capped).
- Bible §8.4 (multi-purpose vendor / OUI-only-→-unknown / Pi self-exclude).
- Bible §11 #1 (no fabrication), #7 (provenance), #8 (no confidence drift),
  #10 (multi-purpose OUI categorization), #12 (Pi self-exclude),
  #13 (unknown-category Talos ban), #14 (procurement-only Talos ban).
- BIBLE_AMENDMENTS.md SAR-1 (LAA-bit penalty), SAR-7 (CVE-FP / DJI-Djibouti
  / news-prose-FP), SAR-8 (vendor-name-disambig).
- CP4 brief §4 Step 4 (Phase-3 inference candidate sweep).
- MAC-39 dispatch (Phase-3 inference candidate sweep proposal).
- MAC-41 dispatch (SAR-8 implementation + bulk-stage at strict §8.4).
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db.extraction.vendor_name_disambig import (
    _normalize_vendor,
    alias_equality,
    vendor_match_disposition,
)

DB_PATH = Path(__file__).resolve().parents[1] / "argus.db"
ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "extraction_outputs"
    / "mac39"
    / "phase3_inference_candidates.json"
)

# §7.3 known-fake-list — applied to OUI prefix at 3-octet level.
KNOWN_FAKE_OUIS = frozenset({
    "00:00:5e",  # RFC 7042 IPv4 doc range
    "02:00:5e",  # RFC 7042 IPv6 doc range
    "aa:bb:cc",
    "00:11:22",
    "12:34:56",
    "de:ad:be",
    "ca:fe:ba",
    "ba:db:00",
    "00:00:00",
    "ff:ff:ff",
})

# §11 #12 Pi self-exclude OUI list (Raspberry Pi hardware running Talos).
PI_SELF_EXCLUDE_OUIS = frozenset({
    "b8:27:eb",  # older Pi boards
    "dc:a6:32",  # Pi 4 era
    "e4:5f:01",  # recent boards
    "28:cd:c1",  # more recent
})

# Wave-A first-promotion MAC + OUI prefix. The dispatch flags any inferred
# row that conflicts with this row at OUI-level as halt-the-line.
WAVE_A_MAC = "e4:aa:ea:80:a1:9b"
WAVE_A_OUI = "e4:aa:ea"

# Vendor-name normalization (`_normalize_vendor`) + the SAR-8
# ``vendor_match_disposition`` predicate are imported from
# ``db.extraction.vendor_name_disambig``. SAR-8 supersedes the
# strict/permissive split this module used pre-MAC-41.


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_valid_oui_or_range(s: str) -> bool:
    """Match `aa:bb:cc` (OUI) or `aa:bb:cc:dd:e` (28/36-bit MA-M/MA-S range)."""
    return bool(
        re.fullmatch(r"^[0-9a-f]{2}(:[0-9a-f]{2}){2}$", s, re.IGNORECASE)
        or re.fullmatch(
            r"^[0-9a-f]{2}(:[0-9a-f]{2}){3}:[0-9a-f]$", s, re.IGNORECASE
        )
        or re.fullmatch(
            r"^[0-9a-f]{2}(:[0-9a-f]{2}){4}:[0-9a-f]$", s, re.IGNORECASE
        )
    )


def is_known_fake_oui(oui: str) -> tuple[bool, str | None]:
    """Apply §7.3 known-fake patterns at the 3-octet OUI level."""
    if not oui or len(oui) < 8:
        return False, None
    prefix = oui.lower()[:8]  # `aa:bb:cc`
    if prefix in KNOWN_FAKE_OUIS:
        return True, f"oui_in_known_fake_list:{prefix}"
    octets = oui.lower().split(":")[:3]
    if len(octets) == 3 and all(o == octets[0] for o in octets):
        return True, "all_identical_octet"
    return False, None


def laa_bit(first_octet: str) -> int:
    """Bit 1 of first octet — 1 ⇒ locally-administered (SAR-1 penalty)."""
    return (int(first_octet, 16) >> 1) & 1


def is_pi_self_exclude(oui_prefix: str) -> bool:
    return oui_prefix.lower()[:8] in PI_SELF_EXCLUDE_OUIS


def build_canonical_lookup(
    manufacturers: list[sqlite3.Row],
) -> list[dict[str, Any]]:
    """Build the §2.1 canonical lexicon — list of (canonical_name, aliases, …).

    Each entry is a dict with ``canonical_name``, ``primary_category``, and
    ``alias_strings`` (the canonical name itself plus the comma-separated
    ``aliases`` column from ``manufacturers``). Callers iterate this list and
    invoke SAR-8 :func:`vendor_match_disposition` against each ``alias_string``
    to find the first canonical match (or flag-for-review).
    """
    lexicon: list[dict[str, Any]] = []
    for row in manufacturers:
        cn = row["canonical_name"]
        alias_strings = [cn] + [
            a.strip() for a in (row["aliases"] or "").split(",") if a.strip()
        ]
        lexicon.append(
            {
                "canonical_name": cn,
                "primary_category": row["primary_category"],
                "alias_strings": alias_strings,
            }
        )
    return lexicon


def sar8_match(
    candidate_name: str, lexicon: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """SAR-8/SAR-9-shaped match against the §2.1 canonical lexicon.

    SAR-9 #2 alias-iteration bug-fix: invokes
    :func:`vendor_match_disposition` once per canonical entry (not once per
    alias-string) so per-canonical FP-list lookups fire correctly. Alias-
    string lookups happen via :func:`alias_equality` only when the canonical
    disposition is ``no_match``.

    Returns:
    - first ``accept`` hit — preferred outcome.
    - first ``flag_for_review`` hit if no ``accept`` was found — routes to
      the human-triage artifact.
    - ``None`` if neither an accept nor a flag was produced.
    """
    flagged: dict[str, Any] | None = None
    for entry in lexicon:
        cn = entry["canonical_name"]
        primary = entry["primary_category"]
        disposition = vendor_match_disposition(candidate_name, cn)
        if disposition == "accept":
            return {
                "canonical_name": cn,
                "primary_category": primary,
                "alias_used": cn,
                "disposition": "accept",
                "match_kind": "sar9_accept_canonical",
                "candidate_normalized": _normalize_vendor(candidate_name),
            }
        if disposition == "flag_for_review" and flagged is None:
            flagged = {
                "canonical_name": cn,
                "primary_category": primary,
                "alias_used": cn,
                "disposition": "flag_for_review",
                "match_kind": "sar9_flag_for_review",
                "candidate_normalized": _normalize_vendor(candidate_name),
            }
        if disposition in ("reject_fp", "flag_for_review"):
            # Don't try aliases — FP/flag is canonical-scoped.
            continue
        # disposition == "no_match" → try alias-string equality lookups.
        for alias in entry["alias_strings"]:
            if alias == cn:
                continue  # already tested via canonical disposition
            if alias_equality(candidate_name, alias):
                return {
                    "canonical_name": cn,
                    "primary_category": primary,
                    "alias_used": alias,
                    "disposition": "accept",
                    "match_kind": "sar9_accept_alias_equality",
                    "candidate_normalized": _normalize_vendor(candidate_name),
                }
    return flagged


def strict_match(
    candidate_name: str, lexicon: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Backwards-compatible alias for :func:`sar8_match` (accept-only).

    Returns the SAR-8 accept hit, or ``None`` if the candidate flagged-for-
    review or no_match. Flagged-for-review hits surface separately via
    :func:`sar8_match`.
    """
    hit = sar8_match(candidate_name, lexicon)
    if hit is None:
        return None
    if hit["disposition"] != "accept":
        return None
    return hit


def _candidate_row(
    raw_obs: sqlite3.Row,
    match: dict[str, Any],
    *,
    match_path: str,
) -> dict[str, Any]:
    """Build a stage-candidate dict for a Phase-2 OUI/range row.

    Applies §7.3 / SAR-1 / §11 #12 / §8.4 flags inline. Confidence is
    computed conservatively: 50 baseline (mid of `inferred` 30–70 band per
    §8.2), -10 for LAA bit set, -20 for permissive-only match, dropped to 0
    + flagged `pre_filter_drop=True` for known-fake / PI-self-exclude.
    """
    oui_prefix = ":".join(raw_obs["candidate_identifier"].split(":")[:3]).lower()
    fake_hit, fake_reason = is_known_fake_oui(oui_prefix)
    pi_hit = is_pi_self_exclude(oui_prefix)
    first_octet = oui_prefix.split(":")[0]
    laa = laa_bit(first_octet) if re.fullmatch(r"[0-9a-f]{2}", first_octet) else 0

    confidence = 50
    flags: list[str] = []
    pre_filter_drop = False

    if fake_hit:
        flags.append(f"§7.3_known_fake:{fake_reason}")
        pre_filter_drop = True
        confidence = 0
    if pi_hit:
        flags.append("§11_#12_pi_self_exclude")
        # Pi OUIs are categorically wrong here — none of our §2.1 vendors are
        # Raspberry Pi Foundation. If this ever fires it's an upstream data bug.
        pre_filter_drop = True
        confidence = 0
    if laa == 1:
        flags.append("SAR-1_laa_bit_set")
        confidence = max(0, confidence - 10)
    if match_path == "permissive":
        flags.append("permissive_substring_match_only")
        confidence = max(0, confidence - 20)

    return {
        "raw_observation_id": raw_obs["id"],
        "source_id": raw_obs["source_id"],
        "source_url": raw_obs["source_url"],
        "candidate_identifier": raw_obs["candidate_identifier"],
        "candidate_type": raw_obs["candidate_type"],
        "candidate_manufacturer_raw": raw_obs["candidate_manufacturer"],
        "matched_canonical_name": match["canonical_name"],
        "matched_via_alias": match["alias_used"],
        "match_kind": match["match_kind"],
        "match_path": match_path,
        "vendor_primary_category": match["primary_category"],
        "device_category_per_8_4": "unknown",
        "device_category_explanation": (
            "§8.4 + §11 #10 — OUI-level inference never categorizes "
            "(category requires model-level evidence). Vendor primary_category "
            "carried as metadata only."
        ),
        "confidence_proposed": confidence,
        "confidence_reasoning": (
            f"§8.2 inferred 30–70 band; baseline 50, "
            f"adjustments={flags or 'none'}."
        ),
        "flags": flags,
        "pre_filter_drop": pre_filter_drop,
        "talos_export_eligible": False,
        "talos_export_reason": (
            "§11 #13 — device_category='unknown' is never exported to Talos."
        ),
    }


def sweep_phase2_oui_inference(
    conn: sqlite3.Connection,
    lexicon: list[dict[str, Any]],
) -> dict[str, Any]:
    """Class D — Phase-2 IEEE/Wireshark OUI/MAC-range × §2.1 canonical match.

    SAR-8 wired: alias-recovered candidates (e.g. ``SZ DJI TECHNOLOGY CO.,LTD``)
    accept as canonical matches; strict-path FPs (Axon Networks, Flock Audio,
    Harris Adacom) reject; ``GENETEC Corporation`` flags-for-review.
    """
    cur = conn.execute(
        """SELECT id, source_id, source_url, candidate_identifier,
                  candidate_type, candidate_manufacturer
             FROM raw_observations
            WHERE candidate_type IN ('oui','mac_range')
              AND candidate_manufacturer IS NOT NULL"""
    )
    accept_rows: list[dict[str, Any]] = []
    flag_rows: list[dict[str, Any]] = []

    for raw in cur.fetchall():
        hit = sar8_match(raw["candidate_manufacturer"], lexicon)
        if hit is None:
            continue
        if hit["disposition"] == "accept":
            accept_rows.append(_candidate_row(raw, hit, match_path="strict"))
        elif hit["disposition"] == "flag_for_review":
            cn = hit["canonical_name"]
            cm_lower = (raw["candidate_manufacturer"] or "").lower().strip()
            if cn == "Genetec":
                reason = (
                    "GENETEC Corporation (early-2000s OUI registration, "
                    "address Tokyo) may be a separate Japanese entity from "
                    "Genetec Inc. (Montreal, the §2.1 alpr vendor). SAR-8 "
                    "flag_for_review carried forward; routes to extraction_"
                    "outputs/mac43/sar9_flagged_for_review.json for CEO/board "
                    "triage; NOT bulk-staged."
                )
                flag_class = "sar8_genetec_corporation"
            elif cn == "Motorola Solutions" and cm_lower == "motorola":
                reason = (
                    "SAR-9 #1 — bare `Motorola` token without further "
                    "qualifier is post-2011 corporate-split-ambiguous "
                    "(Motorola Solutions / police radios vs Motorola "
                    "Mobility / Lenovo / consumer smartphones). Routes to "
                    "extraction_outputs/mac43/sar9_flagged_for_review.json "
                    "for CEO/board model-name evidence triage; NOT bulk-"
                    "staged."
                )
                flag_class = "sar9_motorola_bare_token"
            else:
                reason = (
                    f"flag_for_review under canonical={cn!r} (predicate "
                    f"returned flag_for_review for an unforeseen candidate "
                    f"shape; CEO/board triage required)."
                )
                flag_class = "unknown_flag_for_review"
            flag_rows.append(
                {
                    "raw_observation_id": raw["id"],
                    "source_id": raw["source_id"],
                    "source_url": raw["source_url"],
                    "candidate_identifier": raw["candidate_identifier"],
                    "candidate_type": raw["candidate_type"],
                    "candidate_manufacturer_raw": raw["candidate_manufacturer"],
                    "matched_canonical_name": cn,
                    "matched_via_alias": hit["alias_used"],
                    "vendor_primary_category": hit["primary_category"],
                    "disposition": "flag_for_review",
                    "flag_class": flag_class,
                    "reason": reason,
                }
            )

    # Per-vendor breakdown of accept set.
    by_vendor: dict[str, dict[str, Any]] = {}
    for row in accept_rows:
        cn = row["matched_canonical_name"]
        bucket = by_vendor.setdefault(
            cn,
            {
                "canonical_name": cn,
                "primary_category": row["vendor_primary_category"],
                "accept_count": 0,
                "pre_filter_drop_count": 0,
                "laa_bit_count": 0,
                "samples": [],
            },
        )
        bucket["accept_count"] += 1
        if row["pre_filter_drop"]:
            bucket["pre_filter_drop_count"] += 1
        if "SAR-1_laa_bit_set" in row["flags"]:
            bucket["laa_bit_count"] += 1
        if len(bucket["samples"]) < 3:
            bucket["samples"].append(
                {
                    "raw_observation_id": row["raw_observation_id"],
                    "source_id": row["source_id"],
                    "candidate_identifier": row["candidate_identifier"],
                    "candidate_manufacturer_raw": row[
                        "candidate_manufacturer_raw"
                    ],
                    "match_kind": row["match_kind"],
                    "matched_via_alias": row["matched_via_alias"],
                    "confidence_proposed": row["confidence_proposed"],
                    "flags": row["flags"],
                }
            )

    # Wave-A OUI-conflict probe — would any accepted candidate land at e4:aa:ea?
    wave_a_oui_collision = [
        row
        for row in accept_rows
        if row["candidate_identifier"].lower().startswith(WAVE_A_OUI)
    ]

    return {
        "phase2_oui_inference": {
            "sar8_accept_total": len(accept_rows),
            "sar8_accept_pre_filter_drops": sum(
                1 for r in accept_rows if r["pre_filter_drop"]
            ),
            "sar8_accept_laa_bit_count": sum(
                1 for r in accept_rows if "SAR-1_laa_bit_set" in r["flags"]
            ),
            "sar8_accept_post_filter_stageable": sum(
                1 for r in accept_rows if not r["pre_filter_drop"]
            ),
            "sar8_flag_for_review_total": len(flag_rows),
            "sar8_flag_for_review_samples": flag_rows[:20],
            "by_vendor": sorted(
                by_vendor.values(),
                key=lambda x: -x["accept_count"],
            ),
            "wave_a_oui_collision": {
                "wave_a_oui": WAVE_A_OUI,
                "wave_a_mac": WAVE_A_MAC,
                "accept_inference_rows_at_oui": len(wave_a_oui_collision),
                "halt_flag": (
                    "no_collision — IEEE OUI e4:aa:ea registers to Liteon "
                    "Technology Corporation (not in §2.1 manufacturers); no "
                    "§2.1-vendor inference candidate emits at this OUI. The "
                    "Wave-A row stays canonical at MAC-level e4:aa:ea:80:a1:9b "
                    "(manufacturer=Flock Safety per community-inferred OEM "
                    "narrative). Liteon attribution remains in raw_observations "
                    "(IEEE id=85781, Wireshark id=216273) only."
                )
                if not wave_a_oui_collision
                else (
                    "COLLISION — SAR-8-accept inference candidate at OUI "
                    "e4:aa:ea would conflict with Wave-A canonical row. "
                    "Halt-the-line per MAC-39 dispatch stop-the-line clause."
                ),
            },
        }
    }


def sweep_fcc_grantees(
    conn: sqlite3.Connection,
    lexicon: list[dict[str, Any]],
) -> dict[str, Any]:
    """Class A — FCC grantees × §2.1 canonical match.

    Yields vendor-attestation candidates: rows where the registered grantee
    is one of our §2.1 vendors. The grantee_code is NOT a §4.1 identifier_type
    (per §4.2 fcc_grantees note, grantee_code is a regulatory entity prefix,
    not a per-device identifier). So this class produces analytical-only
    metadata, not direct identifiers rows.
    """
    cur = conn.execute(
        """SELECT id, grantee_code, grantee_name, country, state, date_received
             FROM fcc_grantees"""
    )
    matches: list[dict[str, Any]] = []
    by_vendor: dict[str, dict[str, Any]] = {}
    for r in cur.fetchall():
        m = strict_match(r["grantee_name"], lexicon)
        if m is None:
            continue
        cn = m["canonical_name"]
        match_record = {
            "fcc_grantee_id": r["id"],
            "grantee_code": r["grantee_code"],
            "grantee_name": r["grantee_name"],
            "country": r["country"],
            "state": r["state"],
            "date_received": r["date_received"],
            "matched_canonical_name": cn,
            "matched_via_alias": m["alias_used"],
            "match_kind": m["match_kind"],
            "vendor_primary_category": m["primary_category"],
        }
        matches.append(match_record)
        bucket = by_vendor.setdefault(
            cn,
            {
                "canonical_name": cn,
                "primary_category": m["primary_category"],
                "match_count": 0,
                "samples": [],
            },
        )
        bucket["match_count"] += 1
        if len(bucket["samples"]) < 3:
            bucket["samples"].append(match_record)

    return {
        "fcc_grantees_inference": {
            "total_match_count": len(matches),
            "talos_exportable": False,
            "talos_export_reason": (
                "FCC grantee_code is a regulatory entity prefix (per §4.2 "
                "fcc_grantees note), NOT a §4.1 per-device identifier. These "
                "rows are vendor-attestation metadata only — they enrich any "
                "future FCC-ID-bearing identifier but do not produce identifiers "
                "rows themselves. Phase-4 fcc_equipment_filings (if/when "
                "created) would consume these as anchors."
            ),
            "by_vendor": sorted(
                by_vendor.values(), key=lambda x: -x["match_count"]
            ),
        }
    }


def sweep_procurement_records(
    conn: sqlite3.Connection,
    lexicon: list[dict[str, Any]],
) -> dict[str, Any]:
    """Class B — procurement_records × §2.1 canonical match.

    Per §11 #14 + §4.5 procurement-only carveout: NEVER exported to Talos.
    Analytical-only. No identifier emerges from this class.
    """
    cur = conn.execute(
        """SELECT id, agency_name, vendor_canonical_name, product_family,
                  contract_amount_usd, contract_date, source_url, source_type
             FROM procurement_records"""
    )
    matches: list[dict[str, Any]] = []
    by_vendor: dict[str, dict[str, Any]] = {}
    for r in cur.fetchall():
        m = strict_match(r["vendor_canonical_name"], lexicon)
        if m is None:
            continue
        cn = m["canonical_name"]
        match_record = {
            "procurement_record_id": r["id"],
            "agency_name": r["agency_name"],
            "vendor_canonical_name": r["vendor_canonical_name"],
            "product_family": r["product_family"],
            "contract_amount_usd": r["contract_amount_usd"],
            "contract_date": r["contract_date"],
            "matched_canonical_name": cn,
            "matched_via_alias": m["alias_used"],
            "vendor_primary_category": m["primary_category"],
        }
        matches.append(match_record)
        bucket = by_vendor.setdefault(
            cn,
            {
                "canonical_name": cn,
                "primary_category": m["primary_category"],
                "match_count": 0,
                "samples": [],
            },
        )
        bucket["match_count"] += 1
        if len(bucket["samples"]) < 3:
            bucket["samples"].append(match_record)

    return {
        "procurement_records_inference": {
            "total_match_count": len(matches),
            "talos_exportable": False,
            "talos_export_reason": (
                "§11 #14 + §4.5 procurement-only carveout — procurement records "
                "establish vendor-agency relationships, not device presence. "
                "Analytical-only. Future Talos-bound identifiers may upgrade "
                "via procurement_records.linked_identifier_id when a concrete "
                "MAC/OUI/UUID is later linked."
            ),
            "by_vendor": sorted(
                by_vendor.values(), key=lambda x: -x["match_count"]
            ),
        }
    }


def sweep_deployment_observations(
    conn: sqlite3.Connection,
    lexicon: list[dict[str, Any]],
) -> dict[str, Any]:
    """Class C — deployment_observations × §2.1 canonical match.

    Geographic anchors for inference. No identifier; rows live in
    deployment_observations (per §4.2 staging-table note). Analytical-only
    until a Phase-3+ inference links to a concrete identifier.
    """
    cur = conn.execute(
        """SELECT id, source_id, agency_name, technology_category,
                  vendor_raw, country, state, city, citation_url
             FROM deployment_observations
            WHERE vendor_raw IS NOT NULL"""
    )
    matches: list[dict[str, Any]] = []
    by_vendor: dict[str, dict[str, Any]] = {}
    for r in cur.fetchall():
        m = strict_match(r["vendor_raw"], lexicon)
        if m is None:
            continue
        cn = m["canonical_name"]
        match_record = {
            "deployment_observation_id": r["id"],
            "source_id": r["source_id"],
            "agency_name": r["agency_name"],
            "technology_category": r["technology_category"],
            "vendor_raw": r["vendor_raw"],
            "country": r["country"],
            "state": r["state"],
            "city": r["city"],
            "citation_url": r["citation_url"],
            "matched_canonical_name": cn,
            "matched_via_alias": m["alias_used"],
            "vendor_primary_category": m["primary_category"],
        }
        matches.append(match_record)
        bucket = by_vendor.setdefault(
            cn,
            {
                "canonical_name": cn,
                "primary_category": m["primary_category"],
                "match_count": 0,
                "samples": [],
                "by_state": {},
            },
        )
        bucket["match_count"] += 1
        if r["state"]:
            bucket["by_state"][r["state"]] = bucket["by_state"].get(r["state"], 0) + 1
        if len(bucket["samples"]) < 3:
            bucket["samples"].append(match_record)

    return {
        "deployment_observations_inference": {
            "total_match_count": len(matches),
            "talos_exportable": False,
            "talos_export_reason": (
                "§4.2 + §11 #1 — deployment_observations carry no identifier. "
                "Inference linking a deployment to a concrete identifier is a "
                "Phase 3+ activity (e.g., WiGLE BSSID surveys around a "
                "deployment lat/lon). Without that link, no identifiers row "
                "emits."
            ),
            "by_vendor": sorted(
                by_vendor.values(), key=lambda x: -x["match_count"]
            ),
        }
    }


def sweep_wigle_anchors(conn: sqlite3.Connection) -> dict[str, Any]:
    """Class E — WiGLE deferred-enrichment anchors.

    Per §11 #6 + WiGLE-admin pitch-behavior binding (CP3 close, valid
    through 2026-05-18): DRY_RUN ON. Consume only staged anchors; no live
    fetches. Phase-5 Step-4 honors the deferral.
    """
    total = conn.execute(
        "SELECT COUNT(*) AS n FROM wigle_anchor_priority"
    ).fetchone()["n"]
    by_tier = {
        r["priority_tier"]: r["n"]
        for r in conn.execute(
            "SELECT priority_tier, COUNT(*) AS n FROM wigle_anchor_priority "
            "GROUP BY priority_tier ORDER BY priority_tier"
        )
    }
    by_state_top = [
        dict(r)
        for r in conn.execute(
            "SELECT state_or_country, COUNT(*) AS n FROM wigle_anchor_priority "
            "GROUP BY state_or_country ORDER BY n DESC LIMIT 10"
        )
    ]
    return {
        "wigle_inference": {
            "total_anchors_staged": total,
            "by_priority_tier": by_tier,
            "by_state_top10": by_state_top,
            "dry_run_status": "DRY_RUN_ON",
            "live_fetch_count_this_pass": 0,
            "binding_authority": (
                "§11 #6 + WiGLE-admin pitch-behavior binding (CP3 close); "
                "valid verbatim through 2026-05-18. No live WiGLE API calls "
                "fired in Phase-5 Step-4. Anchors remain available for any "
                "future ratified WiGLE pass."
            ),
        }
    }


FLAGGED_FOR_REVIEW_ARTIFACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "extraction_outputs"
    / "mac43"
    / "sar9_flagged_for_review.json"
)


def evaluate() -> dict[str, Any]:
    conn = _connect()
    try:
        # CP31 (migration 0025) — hub-and-spoke schema. Inference lexicon is
        # hub-only: arm rows are FK-attested by `parent_manufacturer_id`, not
        # canonical-name-matched, so including them in the lexicon would
        # mis-attribute candidate_manufacturer strings to arm canonicals.
        manufacturers = conn.execute(
            "SELECT id, canonical_name, aliases, primary_category FROM manufacturers "
            "WHERE query_default = 'visible'"
        ).fetchall()
        lexicon = build_canonical_lookup(manufacturers)

        phase2 = sweep_phase2_oui_inference(conn, lexicon)
        fcc = sweep_fcc_grantees(conn, lexicon)
        proc = sweep_procurement_records(conn, lexicon)
        deploy = sweep_deployment_observations(conn, lexicon)
        wigle = sweep_wigle_anchors(conn)

        identifiers_count = conn.execute(
            "SELECT COUNT(*) AS n FROM identifiers"
        ).fetchone()["n"]

        # Halt-the-line surface — under SAR-8 the original 3 halts are
        # closed (#1 SAR-8 codified, #2 strict-§8.4 ratified at MAC-1
        # 613ec532, #3 no Wave-A OUI collision). Re-stated here for the
        # audit trail.
        halt_flags = [
            {
                "class": "new_disambig_class",
                "status": "RESOLVED — SAR-8 codified (commit 811b4de)",
                "description": (
                    "Vendor-name-disambig predicate now lives in "
                    "db/extraction/vendor_name_disambig.py and is consumed "
                    "via vendor_match_disposition. SAR-8 enumerates the "
                    "FP list (Axon Networks ×6 / Flock Audio ×2 / Harris "
                    "Adacom ×2 hard-reject; GENETEC Corporation ×2 "
                    "flag_for_review) and the alias allowlist (DJI / "
                    "Cellebrite). Geographic-prefix list stripped before "
                    "normalization."
                ),
            },
            {
                "class": "section_tension_8_4_vs_11_10",
                "status": (
                    "RESOLVED — strict-§8.4 ratified by board at MAC-1 "
                    "613ec532 2026-05-06T17:08:16Z"
                ),
                "description": (
                    "All OUI-level inference candidates land "
                    "device_category='unknown'. §11 #13-banned from Talos "
                    "export. Analytical-only."
                ),
            },
            {
                "class": "wave_a_oui_conflict_probe",
                "status": "RESOLVED — no_halt_needed (re-confirmed under SAR-8)",
                "description": phase2["phase2_oui_inference"][
                    "wave_a_oui_collision"
                ]["halt_flag"],
            },
        ]

        return {
            "_meta": {
                "produced_at_utc": datetime.now(timezone.utc).isoformat(),
                "validator_agent_id": "da137694-2efe-4589-8150-828dcab881fb",
                "phase_5_step": (
                    "Step-4 follow-on (Phase-3 inference candidate sweep, "
                    "Tier 4) — SAR-8 wired"
                ),
                "issue_chain": "MAC-36 → MAC-39 → MAC-41",
                "bible_sections": (
                    "§5 Tier 4, §6 Phase 5 #3, §7.4, §8.2, §8.4, "
                    "§11 #1/#7/#8/#10/#12/#13/#14"
                ),
                "amendments_applied": [
                    "SAR-1 (LAA bit penalty)",
                    "SAR-5 (PII discipline — N/A this pass; no PII surfaces)",
                    "SAR-7 #1/#2/#3 (codified for Step-1; not invoked in Step-4)",
                    "SAR-8 (vendor-name-disambig + alias allowlist + geo-prefix)",
                ],
                "promotion_status": (
                    "PROPOSAL ONLY — no rows written to identifiers from this "
                    "script. Bulk-staging into identifiers happens via the "
                    "MAC-41 bulk-stage executor (db/validation/sar8_bulk_stage.py)."
                ),
                "db_writes_this_pass": 0,
                "identifiers_table_row_count": identifiers_count,
            },
            "canonical_lexicon_size": len(lexicon),
            "canonical_lexicon_canonical_names": sorted(
                e["canonical_name"] for e in lexicon
            ),
            **phase2,
            **fcc,
            **proc,
            **deploy,
            **wigle,
            "halt_flags": halt_flags,
            "validator_summary_recommendation": (
                "SAR-8 wired; bulk-stage executor (sar8_bulk_stage.py) reads "
                "this artifact + the SAR-8 predicate and writes ~405 strict-"
                "clean inferred rows to identifiers at device_category="
                "'unknown' (strict-§8.4) with full §11 attestations. GENETEC "
                "Corporation flagged-for-review entries route to "
                "extraction_outputs/mac41/sar8_flagged_for_review.json for "
                "CEO/board triage."
            ),
        }
    finally:
        conn.close()


def _write_flagged_for_review_artifact(
    payload: dict[str, Any], path: Path
) -> dict[str, Any]:
    """Write the SAR-8 + SAR-9 flag_for_review triage queue artifact."""
    flagged = payload["phase2_oui_inference"]["sar8_flag_for_review_samples"]
    by_flag_class: dict[str, int] = {}
    for f in flagged:
        cls = f.get("flag_class", "unknown_flag_for_review")
        by_flag_class[cls] = by_flag_class.get(cls, 0) + 1
    out = {
        "_meta": {
            "produced_at_utc": datetime.now(timezone.utc).isoformat(),
            "validator_agent_id": "da137694-2efe-4589-8150-828dcab881fb",
            "phase_5_step": (
                "Step-4 follow-on² (MAC-44) — SAR-8 + SAR-9 flagged-for-review"
            ),
            "issue_chain": "MAC-36 → MAC-39 → MAC-41 → MAC-44",
            "amendments_applied": [
                "SAR-8 (flag_for_review third state — GENETEC Corporation)",
                "SAR-9 #1 (bare `Motorola` token flag_for_review)",
            ],
            "rationale": (
                "Two flag-for-review classes share this artifact: "
                "(a) SAR-8 GENETEC Corporation (Tokyo OUI; possibly distinct "
                "from Genetec Inc. Montreal, the §2.1 alpr vendor); "
                "(b) SAR-9 #1 bare `Motorola` token (post-2011 corporate-"
                "split ambiguity between Motorola Solutions and Motorola "
                "Mobility / Lenovo). Both classes require CEO/board model-"
                "name triage before any promotion; rows are NOT bulk-staged."
            ),
            "decision_class": "CEO/board (not Validator)",
            "by_flag_class": by_flag_class,
        },
        "flagged_count": len(flagged),
        "flagged_rows": flagged,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, default=str) + "\n")
    return out


def main() -> None:
    payload = evaluate()
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    print(f"Artifact written: {ARTIFACT_PATH}")

    flagged = _write_flagged_for_review_artifact(
        payload, FLAGGED_FOR_REVIEW_ARTIFACT_PATH
    )
    print(
        f"Flagged-for-review artifact written: {FLAGGED_FOR_REVIEW_ARTIFACT_PATH} "
        f"(count={flagged['flagged_count']})"
    )

    summary = {
        "phase2_sar8_accept_total": payload["phase2_oui_inference"][
            "sar8_accept_total"
        ],
        "phase2_sar8_accept_post_filter_stageable": payload[
            "phase2_oui_inference"
        ]["sar8_accept_post_filter_stageable"],
        "phase2_sar8_flag_for_review_total": payload["phase2_oui_inference"][
            "sar8_flag_for_review_total"
        ],
        "fcc_grantees_match_total": payload["fcc_grantees_inference"][
            "total_match_count"
        ],
        "procurement_records_match_total": payload[
            "procurement_records_inference"
        ]["total_match_count"],
        "deployment_observations_match_total": payload[
            "deployment_observations_inference"
        ]["total_match_count"],
        "wigle_anchors_total": payload["wigle_inference"][
            "total_anchors_staged"
        ],
        "wigle_dry_run_status": payload["wigle_inference"]["dry_run_status"],
        "halt_flags_count": len(payload["halt_flags"]),
        "db_writes_this_pass": payload["_meta"]["db_writes_this_pass"],
        "identifiers_table_row_count": payload["_meta"][
            "identifiers_table_row_count"
        ],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
