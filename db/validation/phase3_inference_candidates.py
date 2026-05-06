"""Phase-5 Step-4 Validator pass — Phase-3 inference candidate sweep (Tier 4).

Read-only. Writes nothing to the database. Produces a JSON artifact
summarising per-source candidate counts, sample rows, applied disambig +
hard-rule filters, and the halt-flags that the CEO + board must ratify
before bulk staging into ``identifiers`` (or a new staging table).

Why JSON-artifact-only (not direct insert into ``identifiers``):
    The MAC-39 dispatch enumerates "any new disambig class beyond the
    SAR-7 trio → halt + surface; do NOT bundle silently". The Phase-2
    IEEE/Wireshark `candidate_manufacturer` field carries free-text
    vendor names (`SZ DJI TECHNOLOGY CO.,LTD`, `Motorola Solutions
    Inc.`, `Avigilon Alta`, `WatchGuard Video` vs. `WatchGuard
    Technologies, Inc.`, etc.). Matching against the §2.1 canonical
    list requires a normalized vendor-name disambig, which is a
    SAR-7-class predicate this script implements as ``_normalize_vendor``
    + the strict/permissive split. CEO + board ratify the disambig
    posture (and any §8.4-vs-§11-#10 carveout) before promotion.

Output artifact:
    ``extraction_outputs/mac39/phase3_inference_candidates.json``

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
- CP4 brief §4 Step 4 (Phase-3 inference candidate sweep).
- MAC-39 dispatch.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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

# Vendor-name normalization suffixes — stripped to align IEEE / Wireshark
# free-text vendor names with the §2.1 canonical-list. Lowercased; order
# matters (longest first to handle `, inc.` before `, inc`).
_VENDOR_SUFFIX_STRIPS = (
    ", inc.", ", inc", " inc.", " inc",
    ", ltd.", ", ltd", " ltd.", " ltd",
    ", llc", " llc",
    ", ulc", " ulc",
    " corporation", " corp.", " corp",
    " co.,ltd", " co., ltd", " co.,ltd.", " co., ltd.",
    " co.,ltd.", " co.ltd.", " co. ltd",
    " co., limited", ", limited", " limited",
    " technologies", " technology",
    " sa", " ag", " ab", " gmbh", " bv", " plc", " spa",
    ", s.a.", " s.a.",
    ", inc", " holdings",
)


def _normalize_vendor(name: str) -> str:
    """Vendor-name disambig predicate — strip corporate suffixes + punctuation.

    NOTE: This is a NEW SAR-class disambig predicate (beyond SAR-7 #1/#2/#3).
    Per MAC-39 dispatch stop-the-line: any new disambig class halts + surfaces.
    The predicate is implemented for the strict/permissive split surfaced in
    the artifact, NOT silently applied at promotion time.
    """
    if not name:
        return ""
    s = name.lower().strip()
    # Drop trailing punctuation in chunks.
    changed = True
    while changed:
        changed = False
        for suf in _VENDOR_SUFFIX_STRIPS:
            if s.endswith(suf):
                s = s[: -len(suf)].rstrip(" ,.;:")
                changed = True
                break
    # Collapse whitespace + remove comma/period/semicolon punctuation.
    s = re.sub(r"[,;:.]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


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
) -> dict[str, dict[str, Any]]:
    """Build a normalized-vendor-name → canonical-row lookup from §2.1 set.

    Returns a dict keyed by normalized name (lowercase, suffix-stripped),
    valued by ``{canonical_name, primary_category, alias_used}``. The §2.1
    aliases column is comma-separated.
    """
    lookup: dict[str, dict[str, Any]] = {}
    for row in manufacturers:
        cn = row["canonical_name"]
        primary_category = row["primary_category"]
        alias_list = [cn] + [
            a.strip() for a in (row["aliases"] or "").split(",") if a.strip()
        ]
        for alias in alias_list:
            norm = _normalize_vendor(alias)
            if not norm:
                continue
            # First registration wins; aliases shouldn't conflict across vendors.
            if norm not in lookup:
                lookup[norm] = {
                    "canonical_name": cn,
                    "primary_category": primary_category,
                    "alias_used": alias,
                }
    return lookup


def strict_match(
    candidate_name: str, canonical_lookup: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    """Strict normalized match — full-string equality after suffix-strip.

    Falls back to alias-prefix-equality (`alias` then a delimiter) for
    sub-brand names like `Avigilon Alta` (matches `Avigilon`) and
    `WatchGuard Video` (matches `WatchGuard`). Multi-token sub-brands
    where the alias is a prefix-token-match are accepted.
    """
    norm = _normalize_vendor(candidate_name)
    if not norm:
        return None
    if norm in canonical_lookup:
        match = dict(canonical_lookup[norm])
        match["match_kind"] = "exact_normalized"
        match["candidate_normalized"] = norm
        return match
    # Prefix-token match — `avigilon alta` starts-with `avigilon` + space.
    for alias_norm, row in canonical_lookup.items():
        if norm.startswith(alias_norm + " "):
            match = dict(row)
            match["match_kind"] = "prefix_token"
            match["candidate_normalized"] = norm
            return match
    return None


def permissive_match(
    candidate_name: str, canonical_lookup: dict[str, dict[str, Any]]
) -> dict[str, Any] | None:
    """Permissive substring match — alias-substring-in-candidate-normalized.

    This is the intentionally-noisy match the strict path is filtering out.
    Surfaced separately so the CEO + board can review the FP density.
    """
    norm = _normalize_vendor(candidate_name)
    if not norm:
        return None
    for alias_norm, row in canonical_lookup.items():
        if alias_norm and alias_norm in norm:
            match = dict(row)
            match["match_kind"] = "permissive_substring"
            match["candidate_normalized"] = norm
            return match
    return None


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


_STRICT_PATH_FP_PROBE_NEEDLES: tuple[tuple[str, str, str, str], ...] = (
    # (canonical_match, candidate_substring, why_fp, suspect_other_vendor)
    (
        "Axon",
        "axon networks",
        "Axon Networks Inc. is a network-gear vendor distinct from Axon "
        "Enterprise (TASER International legacy / body-cam vendor in §2.1).",
        "Axon Networks Inc. (unaffiliated network gear)",
    ),
    (
        "Flock Safety",
        "flock audio",
        "Flock Audio Inc. is a Canadian audio-equipment company unrelated "
        "to Flock Safety (the §2.1 alpr vendor). The bare alias `Flock` in "
        "manufacturers.aliases captures both.",
        "Flock Audio Inc. (audio equipment)",
    ),
    (
        "Genetec",
        "genetec corporation",
        "GENETEC Corporation (early-2000s OUI registration, address Tokyo) "
        "may be a separate Japanese entity from Genetec Inc. (Montreal, the "
        "§2.1 alpr vendor). Verify before staging — the OUIs `00:0a:b1` "
        "predate Genetec Inc.'s typical FCC/IEEE-registration era.",
        "GENETEC Corporation (possibly distinct entity)",
    ),
    (
        "Harris",
        "harris adacom",
        "HARRIS ADACOM CORPORATION is a 1990s networking-products vendor "
        "distinct from Harris Corporation (the §2.1 imsi_catcher vendor).",
        "Harris Adacom Corporation",
    ),
)

_PERMISSIVE_PATH_LIKELY_TP_NEEDLES: tuple[tuple[str, str, str], ...] = (
    # (canonical_match, candidate_substring, reason_likely_tp)
    (
        "DJI",
        "sz dji technology",
        "SZ DJI TECHNOLOGY CO.,LTD is the canonical IEEE-registered name "
        "for DJI (§2.1 drone vendor). Strict-path missed it because the "
        "company-prefix `SZ ` (Shenzhen) doesn't suffix-strip; normalization "
        "yields `sz dji` ≠ `dji`. CEO should ratify whether this is added "
        "to manufacturers.aliases or whether the predicate handles geographic "
        "prefixes natively.",
    ),
    (
        "Cellebrite",
        "cellebrite mobile synchronization",
        "CelleBrite Mobile Synchronization (early 2000s OUI) is the same "
        "entity as Cellebrite (the §2.1 hacking_tool vendor) — Cellebrite "
        "originated as a mobile-data-sync company before pivoting to "
        "forensics.",
    ),
)


def _probe_strict_fps(
    strict_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return strict-path rows that match the FP probe needles."""
    hits: list[dict[str, Any]] = []
    for row in strict_rows:
        manuf_l = (row["candidate_manufacturer_raw"] or "").lower()
        for canonical, needle, why, suspect in _STRICT_PATH_FP_PROBE_NEEDLES:
            if (
                row["matched_canonical_name"] == canonical
                and needle in manuf_l
            ):
                hits.append(
                    {
                        "raw_observation_id": row["raw_observation_id"],
                        "source_id": row["source_id"],
                        "candidate_identifier": row["candidate_identifier"],
                        "candidate_manufacturer_raw": row[
                            "candidate_manufacturer_raw"
                        ],
                        "matched_canonical_name": canonical,
                        "fp_reason": why,
                        "suspect_other_vendor": suspect,
                    }
                )
                break
    return hits


def _probe_permissive_tps(
    permissive_only_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return permissive-only rows that match the missed-TP probe needles."""
    hits: list[dict[str, Any]] = []
    for row in permissive_only_rows:
        manuf_l = (row["candidate_manufacturer_raw"] or "").lower()
        for canonical, needle, reason in _PERMISSIVE_PATH_LIKELY_TP_NEEDLES:
            if (
                row["matched_canonical_name"] == canonical
                and needle in manuf_l
            ):
                hits.append(
                    {
                        "raw_observation_id": row["raw_observation_id"],
                        "source_id": row["source_id"],
                        "candidate_identifier": row["candidate_identifier"],
                        "candidate_manufacturer_raw": row[
                            "candidate_manufacturer_raw"
                        ],
                        "matched_canonical_name": canonical,
                        "missed_tp_reason": reason,
                    }
                )
                break
    return hits


def sweep_phase2_oui_inference(
    conn: sqlite3.Connection,
    canonical_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Class D — Phase-2 IEEE/Wireshark OUI/MAC-range × §2.1 canonical match."""
    cur = conn.execute(
        """SELECT id, source_id, source_url, candidate_identifier,
                  candidate_type, candidate_manufacturer
             FROM raw_observations
            WHERE candidate_type IN ('oui','mac_range')
              AND candidate_manufacturer IS NOT NULL"""
    )
    strict_rows: list[dict[str, Any]] = []
    permissive_only_rows: list[dict[str, Any]] = []
    seen_strict_ids: set[int] = set()

    for raw in cur.fetchall():
        s_match = strict_match(raw["candidate_manufacturer"], canonical_lookup)
        if s_match is not None:
            strict_rows.append(_candidate_row(raw, s_match, match_path="strict"))
            seen_strict_ids.add(raw["id"])

    cur = conn.execute(
        """SELECT id, source_id, source_url, candidate_identifier,
                  candidate_type, candidate_manufacturer
             FROM raw_observations
            WHERE candidate_type IN ('oui','mac_range')
              AND candidate_manufacturer IS NOT NULL"""
    )
    for raw in cur.fetchall():
        if raw["id"] in seen_strict_ids:
            continue
        p_match = permissive_match(raw["candidate_manufacturer"], canonical_lookup)
        if p_match is not None:
            permissive_only_rows.append(
                _candidate_row(raw, p_match, match_path="permissive")
            )

    strict_path_fp_probes = _probe_strict_fps(strict_rows)
    permissive_path_likely_tps = _probe_permissive_tps(permissive_only_rows)

    # Per-vendor breakdown, strict path.
    by_vendor: dict[str, dict[str, Any]] = {}
    for row in strict_rows:
        cn = row["matched_canonical_name"]
        bucket = by_vendor.setdefault(
            cn,
            {
                "canonical_name": cn,
                "primary_category": row["vendor_primary_category"],
                "strict_count": 0,
                "pre_filter_drop_count": 0,
                "laa_bit_count": 0,
                "samples": [],
            },
        )
        bucket["strict_count"] += 1
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
                    "confidence_proposed": row["confidence_proposed"],
                    "flags": row["flags"],
                }
            )

    # Wave-A OUI-conflict probe — would any strict candidate land at e4:aa:ea?
    wave_a_oui_collision = [
        row
        for row in strict_rows
        if row["candidate_identifier"].lower().startswith(WAVE_A_OUI)
    ]

    # Permissive-only sample for FP review.
    permissive_only_samples = permissive_only_rows[:20]

    return {
        "phase2_oui_inference": {
            "strict_match_total": len(strict_rows),
            "strict_match_pre_filter_drops": sum(
                1 for r in strict_rows if r["pre_filter_drop"]
            ),
            "strict_match_laa_bit_count": sum(
                1 for r in strict_rows if "SAR-1_laa_bit_set" in r["flags"]
            ),
            "strict_match_post_filter_stageable": sum(
                1 for r in strict_rows if not r["pre_filter_drop"]
            ),
            "permissive_only_total": len(permissive_only_rows),
            "permissive_only_samples": permissive_only_samples,
            "by_vendor": sorted(
                by_vendor.values(),
                key=lambda x: -x["strict_count"],
            ),
            "strict_path_fp_probes": {
                "count": len(strict_path_fp_probes),
                "samples": strict_path_fp_probes[:20],
                "interpretation": (
                    "These rows match the strict-path predicate but are likely "
                    "false positives — distinct corporate entities sharing a "
                    "vendor-token prefix. CEO should ratify whether to (a) "
                    "tighten the predicate (e.g., per-vendor allowlist of "
                    "alias variants), (b) add the FP entities to a vendor-name "
                    "blocklist, or (c) accept the FP rate at the staged "
                    "device_category='unknown' confidence floor."
                ),
            },
            "permissive_path_likely_tps": {
                "count": len(permissive_path_likely_tps),
                "samples": permissive_path_likely_tps[:20],
                "interpretation": (
                    "These rows are in the permissive-only bucket but are "
                    "likely true positives the strict-path missed. The most "
                    "important miss is `SZ DJI TECHNOLOGY CO.,LTD` — DJI's "
                    "canonical IEEE registration name. CEO should ratify "
                    "whether to add `SZ DJI` (and similar geographic-prefix "
                    "variants) to manufacturers.aliases, or whether the "
                    "predicate should handle geographic prefixes natively."
                ),
            },
            "wave_a_oui_collision": {
                "wave_a_oui": WAVE_A_OUI,
                "wave_a_mac": WAVE_A_MAC,
                "strict_inference_rows_at_oui": len(wave_a_oui_collision),
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
                    "COLLISION — strict inference candidate at OUI e4:aa:ea "
                    "would conflict with Wave-A canonical row. Halt-the-line "
                    "per MAC-39 dispatch stop-the-line clause."
                ),
            },
        }
    }


def sweep_fcc_grantees(
    conn: sqlite3.Connection,
    canonical_lookup: dict[str, dict[str, Any]],
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
        m = strict_match(r["grantee_name"], canonical_lookup)
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
    canonical_lookup: dict[str, dict[str, Any]],
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
        m = strict_match(r["vendor_canonical_name"], canonical_lookup)
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
    canonical_lookup: dict[str, dict[str, Any]],
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
        m = strict_match(r["vendor_raw"], canonical_lookup)
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


def evaluate() -> dict[str, Any]:
    conn = _connect()
    try:
        manufacturers = conn.execute(
            "SELECT id, canonical_name, aliases, primary_category FROM manufacturers"
        ).fetchall()
        canonical_lookup = build_canonical_lookup(manufacturers)

        phase2 = sweep_phase2_oui_inference(conn, canonical_lookup)
        fcc = sweep_fcc_grantees(conn, canonical_lookup)
        proc = sweep_procurement_records(conn, canonical_lookup)
        deploy = sweep_deployment_observations(conn, canonical_lookup)
        wigle = sweep_wigle_anchors(conn)

        identifiers_count = conn.execute(
            "SELECT COUNT(*) AS n FROM identifiers"
        ).fetchone()["n"]

        # Halt-the-line surface — the dispatch enumerates three halt classes.
        halt_flags = []

        # Halt #1 — vendor-name-disambig is a NEW SAR-class predicate.
        strict_fp_count = phase2["phase2_oui_inference"][
            "strict_path_fp_probes"
        ]["count"]
        permissive_tp_count = phase2["phase2_oui_inference"][
            "permissive_path_likely_tps"
        ]["count"]
        halt_flags.append(
            {
                "class": "new_disambig_class",
                "description": (
                    "_normalize_vendor + strict-vs-permissive split is a "
                    "vendor-name-disambig predicate beyond the SAR-7 trio. "
                    "Concrete failures surfaced this pass: "
                    f"{strict_fp_count} strict-path FPs (Axon Networks Inc. "
                    f"≠ Axon Enterprise; Flock Audio Inc. ≠ Flock Safety; "
                    f"Harris Adacom Corp ≠ Harris Corp; GENETEC Corporation "
                    f"may be distinct from Genetec Inc.) and "
                    f"{permissive_tp_count} permissive-path likely-TPs "
                    f"(SZ DJI TECHNOLOGY CO.,LTD is the canonical IEEE "
                    f"DJI registration but strict-path drops it because the "
                    f"`SZ ` geographic prefix doesn't suffix-strip). "
                    "Both classes need CEO ratification before bulk staging."
                ),
                "stop_the_line_clause": (
                    "MAC-39 dispatch — 'Any new disambig class beyond SAR-7 "
                    "trio → halt + surface; do NOT bundle silently.'"
                ),
                "ceo_ratification_ask": (
                    "(a) Is the vendor-name-disambig predicate in this script "
                    "the right shape to codify as a SAR-amendment "
                    "(e.g., SAR-8) before bulk staging?  "
                    "(b) Should the strict-path be the only one that emits "
                    "candidates, or should permissive-only matches be staged "
                    "at confidence ≤30 and treated as FP-pending?  "
                    "(c) Should `_normalize_vendor` live in a shared module "
                    "(e.g., db/extraction/vendor_normalize.py) so future "
                    "extractor passes use the same predicate?"
                ),
            }
        )

        # Halt #2 — §8.4 vs §11 #10 tension on OUI-level categorization.
        halt_flags.append(
            {
                "class": "section_tension_8_4_vs_11_10",
                "description": (
                    "§8.4 says 'An OUI alone never gets a device_category "
                    "other than unknown' (broad rule); §11 #10 says 'Do not "
                    "categorize at the OUI level for multi-purpose vendors' "
                    "(narrower). Bible §5 Tier 4 example #1 ('Manufacturer Y's "
                    "only product is body cameras → flag as body_cam category') "
                    "is in tension with §8.4. Single-product vendors in §2.1 "
                    "include Flock (alpr), DJI (drone), Skydio (drone), "
                    "Cellebrite (hacking_tool), Hak5 (hacking_tool), "
                    "ShotSpotter/SoundThinking (gunshot_detect), etc."
                ),
                "stop_the_line_clause": (
                    "Phase-5 Step-4 conservative posture: device_category="
                    "'unknown' for ALL OUI-level inference candidates "
                    "(strict-§8.4 read). Any deviation requires a SAR-amendment."
                ),
                "ceo_ratification_ask": (
                    "Is the strict-§8.4 read (device_category='unknown' for ALL "
                    "OUI-level inference, regardless of vendor primary_category) "
                    "correct? If so, all 525-ish strict candidates land "
                    "device_category='unknown' and are §11 #13-banned from Talos "
                    "export — the inference pass produces analytical-only "
                    "records, with §11 #13 reconciling against §6 Phase 5 #4 "
                    "coverage matrix. If a SAR-amendment carves out single-"
                    "product vendors, those candidates would Talos-export at "
                    "the vendor primary_category. Recommendation: hold strict-"
                    "§8.4 in Step-4; revisit at CP5 alongside the export design."
                ),
            }
        )

        # Halt #3 — Wave-A OUI-conflict probe (clean: no §2.1 inference at the OUI).
        halt_flags.append(
            {
                "class": "wave_a_oui_conflict_probe",
                "description": phase2["phase2_oui_inference"][
                    "wave_a_oui_collision"
                ]["halt_flag"],
                "result": "no_halt_needed",
                "ceo_ratification_ask": (
                    "Confirm the Wave-A canonical row stays at MAC-level "
                    "granularity; IEEE OUI e4:aa:ea Liteon attribution remains "
                    "in raw_observations only and is NOT promoted to "
                    "identifiers as an inference row. (Phase-5 Step-5 dedup "
                    "pass will not see a conflict here either.)"
                ),
            }
        )

        return {
            "_meta": {
                "produced_at_utc": datetime.now(timezone.utc).isoformat(),
                "validator_agent_id": "da137694-2efe-4589-8150-828dcab881fb",
                "phase_5_step": "Step-4 (Phase-3 inference candidate sweep, Tier 4)",
                "issue_chain": "MAC-36 → MAC-39",
                "bible_sections": (
                    "§5 Tier 4, §6 Phase 5 #3, §7.4, §8.2, §8.4, "
                    "§11 #1/#7/#8/#10/#12/#13/#14"
                ),
                "amendments_applied": [
                    "SAR-1 (LAA bit penalty)",
                    "SAR-5 (PII discipline — N/A this pass; no PII surfaces)",
                    "SAR-7 #1/#2/#3 (codified for Step-1; not invoked in Step-4)",
                ],
                "promotion_status": (
                    "PROPOSAL ONLY — no rows written to identifiers. CEO + "
                    "board ratify the disambig predicate + §8.4-vs-§11-#10 "
                    "tension before bulk staging. JSON-artifact-only schema "
                    "fit per MAC-39 dispatch (Validator picks cleanest)."
                ),
                "db_writes_this_pass": 0,
                "identifiers_table_row_count": identifiers_count,
            },
            "canonical_manufacturer_lookup_size": len(canonical_lookup),
            "canonical_manufacturer_lookup_keys_sample": sorted(
                canonical_lookup.keys()
            )[:30],
            **phase2,
            **fcc,
            **proc,
            **deploy,
            **wigle,
            "halt_flags": halt_flags,
            "validator_summary_recommendation": (
                "Hold bulk staging until CEO ratifies (a) the vendor-name-"
                "disambig predicate as a new SAR class (SAR-8 candidate), "
                "(b) the §8.4-vs-§11-#10 tension resolution (recommend strict "
                "§8.4: device_category='unknown' for all OUI-level inference), "
                "(c) Wave-A OUI-conflict-probe result (no conflict; Liteon stays "
                "in raw_observations). Per-source candidate counts surfaced; "
                "halt-flags surfaced; no §11 hard-rule trips beyond the new-"
                "disambig class. Recommend chaining to Step-5 dedup once CEO "
                "ratifies the disambig posture; the strict-path can then bulk-"
                "stage to identifiers (or a new staging table) for dedup."
            ),
        }
    finally:
        conn.close()


def main() -> None:
    payload = evaluate()
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(payload, indent=2, default=str) + "\n")
    print(f"Artifact written: {ARTIFACT_PATH}")
    summary = {
        "phase2_strict_match_total": payload["phase2_oui_inference"][
            "strict_match_total"
        ],
        "phase2_strict_match_post_filter_stageable": payload[
            "phase2_oui_inference"
        ]["strict_match_post_filter_stageable"],
        "phase2_permissive_only_total": payload["phase2_oui_inference"][
            "permissive_only_total"
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
