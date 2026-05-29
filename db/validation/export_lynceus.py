"""Phase-5 Step-6 Lynceus export writer (MAC-46 + MAC-48 §B2).

Generates the four §6 Phase 5 #5 / §9 item 2 deliverables in ``argus/exports/``:

1. ``argus_export.json`` — Lynceus-consumable, confidence floor 30, applies
   §4.4 type mapping + §7.5 description-format constraints + CP7
   geographic_scope filter (default ``["US"]``).
2. ``argus_export_high_confidence.json`` — Lynceus-consumable, confidence
   floor 70, applies §8.4 / §11 #12 Pi self-exclude OUI ban + CP7 filter
   (and rejects ``geographic_scope IN ('unknown', NULL)`` per CP7).
3. ``argus_export.csv`` — human-readable, all 63 active canonical rows
   (no Lynceus filtering).
4. ``coverage_report.md`` — coverage matrix + gap analysis + §9 item 9
   "Dropped from Lynceus export" tally reconciliation against the
   ``_meta.dropped_in_export`` blocks of the two Lynceus files.

Authority chain
---------------
- Bible §4.4 — identifier_type → pattern_type mapping (verbatim).
- Bible §4.5 — device_category → severity mapping (SUPERSEDED at CP8;
  severity owned operator-side via Lynceus's ``severity_overrides.yaml``;
  no severity emitted in export shape).
- Bible §7.5 — Lynceus export shape, ``_meta.dropped_in_export`` block,
  description-format constraints (CP8 flat form), idempotency contract.
- Bible §8.4 + §11 #12 — Pi self-exclude OUI list.
- Bible §11 #6 — read-only DB access during export pass
  (``PRAGMA query_only = ON``).
- Bible §11 #13 — ``device_category='unknown'`` Lynceus-export ban.
- Bible §11 #14 — ``source_type='procurement'`` Lynceus-export ban.
- BIBLE_AMENDMENTS.md CP7 — ``geographic_scope`` export-time filter.
- BIBLE_AMENDMENTS.md CP8 — flat ``{vendor} {device_category}`` description
  ≤80 char, severity reframed-as-historical (dropped from output shape).
- BIBLE_AMENDMENTS.md SAR-10 — ``argus_record_id =
  sha256(type|identifier)[:16]`` (the §8.3 dedup-key hash, stable under
  re-runs / confidence drift / source edits / vendor reattribution).
- MAC-45 ``coverage_matrix_report.json`` — drives drop_assignments map +
  pre-tallied bin counts; the writer reconciles static-bin classifications
  against this map and halts on any mismatch (no silent re-tally). The
  CP7 geographic_scope filter is applied AFTER static reconciliation as
  a runtime parameter, so its tally is not in MAC-45's pre-tally.
- MAC-46 dispatch (HB36); MAC-48 §B2 dispatch (HB41).

Read-only contract
------------------
``PRAGMA query_only = ON`` is set immediately after open. Re-running the
writer over an unchanged DB produces byte-identical files modulo the
``exported_at`` field (the only time-varying surface). ``argus_run_id`` is
a deterministic UUID5 derived from the active canonical set hash, so it
collapses to a stable identifier when the input is unchanged.

Stop-the-line clauses
---------------------
- Drop-tally mismatch vs MAC-45 reconciliation → halt + raise.
- Unexpected ``identifier_type`` or ``source_type`` outside the §4.1 enum
  → halt + raise.
- Unknown row in active set not present in MAC-45 ``drop_assignments`` map
  → halt + raise (means MAC-45 input is stale relative to Step-6 input).
- Unknown bin label in MAC-45 map → halt + raise.

Per dispatch §11 #1 / #6 / #7 / #11 / #12 / #13 / #14: the writer halts
the line on any rule trip; it never silently massages the output to make
the reconciliation pass.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db.export.argus_record_id import argus_record_id as _sar10_hash

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "db" / "argus.db"
EXPORTS_DIR = REPO_ROOT / "exports"
COVERAGE_MATRIX_REPORT_PATH = (
    REPO_ROOT / "extraction_outputs" / "mac45" / "coverage_matrix_report.json"
)
COVERAGE_MATRIX_MD_PATH = (
    REPO_ROOT / "extraction_outputs" / "mac45" / "coverage_matrix.md"
)

# §4.4 Lynceus pattern_type mapping (verbatim).
IDENTIFIER_TYPE_TO_PATTERN_TYPE: dict[str, str | None] = {
    "oui": "oui",
    "mac": "mac",
    "bssid": "mac",
    "ssid_exact": "ssid",
    "ssid_pattern": None,  # DROPPED per §4.4 (no regex in Lynceus v0.2)
    "ble_uuid": "ble_uuid",
    "ble_service": "ble_uuid",
    "mac_range": None,  # expand or DROP per §4.4 (≤256 → expand else drop)
    "device_fingerprint": None,  # DROPPED per §4.4
    # CP13 (§4.4) — Wave G analytical-only types. All three are DROPPED-class:
    # carried in the canonical DB but never reach the Lynceus pattern table.
    "ble_local_name": None,  # DROPPED — no GAP local-name match in Lynceus v0.3
    "ble_characteristic": None,  # DROPPED — Lynceus discovers by service UUID, not characteristic
    "product_family_codename": None,  # DROPPED — vendor-internal taxonomy / cohort strings
    # CP16 (§4.4) — CP14 identifier_type cluster MAP cases (3 new pattern_types).
    # The 12 CP14-cluster DROPPED types live in DROPPED_REASONS below (lean-
    # refactor per board direction at MAC-75 5b9212ce). See PROJECT_BIBLE.md
    # §4.4 amendment for per-type rationale + Lynceus-side scanner work notes
    # + architectural-separation paragraph (Argus and Lynceus are parallel
    # tracks; Argus exports unconditionally regardless of Lynceus scanner
    # support state).
    "ble_manufacturer_id": "ble_manufacturer_id",  # MAP — new pattern_type; BLE adv manuf_data[0:2] match
    "drone_id_prefix": "drone_id_prefix",  # MAP — new pattern_type; Remote ID prefix string match (WiFi NAN/Beacon/BLE Legacy 4.x); BLE5 LE Coded PHY is a current-hardware boundary
    "wifi_aware_service_name": "wifi_aware_service_name",  # MAP — new pattern_type; WiFi NAN service-name UTF-8 match; capability-gated by Lynceus-side NAN support (consumer-carries-state)
    # CP28 (§4.4) — Wave H desktop-axis vendor-registered non-BLE cluster MAP case (1 entry).
    # Two sibling DROPPED-class types live in DROPPED_REASONS below.
    "vendor_document_uuid_cloud_reference": "vendor_document_uuid_cloud_reference",  # MAP — vendor-controlled cloud-hostname half lifts into Lynceus relevance window (e.g. duss.djicorp.com); Lynceus-side scanner work item to add a cloud-hostname pattern_type
}


# CP16 (§4.4) — CP14 identifier_type cluster DROPPED cases (12 entries).
# Per board direction at MAC-75 5b9212ce: 12 CP14-cluster DROPPED types live
# here keyed on identifier_type → bin_label string. _classify_row gets ONE
# new branch (below) checking this dict; existing 6 explicit early-return
# branches (device_fingerprint, ssid_pattern, ble_local_name, ble_characteristic,
# product_family_codename, mac_range) stay verbatim — stable, working, no
# regression risk.
#
# Future hygiene-pass-only: the 6 legacy branches could fold into this same
# dict if a later commit wants to consolidate. Out of CP16 scope.
DROPPED_REASONS: dict[str, str] = {
    "icao_24bit_address": "icao_24bit_address",  # Out-of-band RF (1090 MHz ADS-B; SDR upgrade path)
    "rf_channel": "rf_channel",  # Parametric metadata, not a wire-observable identifier
    "burst_cadence_ms": "burst_cadence_ms",  # Parametric metadata
    "bandwidth_mhz": "bandwidth_mhz",  # Parametric metadata
    "device_class_id": "device_class_id",  # Semantic enum, not match value
    "rf_burst_duration": "rf_burst_duration",  # Parametric metadata
    "rf_protocol_constant": "rf_protocol_constant",  # Sub-protocol-level / SDR-required
    "wifi_ie_element_id": "wifi_ie_element_id",  # Overly-coarse 1-byte tag
    "bluetooth_le_pdu_type": "bluetooth_le_pdu_type",  # Overly-coarse 4-bit enum
    "wifi_frame_control_subtype": "wifi_frame_control_subtype",  # Overly-coarse enum
    "wifi_nan_param_signature": "wifi_nan_param_signature",  # Derived multi-field aggregate
    "alpr_model": "alpr_model",  # Vendor-internal taxonomy, not RF-broadcast (companion to product_family_codename)
    # Migration 0018 / SAR-13 §S.3 — 14 net-new identifier_types added at
    # MAC-109. Default DROPPED-class pending board ratification of §4.4 MAP
    # additions (MAC-110 §E architectural firsts). Each carries the same
    # "carried in canonical DB but not in Lynceus pattern table v0.1"
    # disposition as the CP16 cluster.
    "ble_protocol_byte_table": "ble_protocol_byte_table",  # Sub-protocol byte table; not wire-pattern
    "ble_service_uuid": "ble_service_uuid",  # Service-uuid variant of ble_service; awaiting §4.4 alias confirm
    "ble_company_id": "ble_company_id",  # Company-id variant of ble_manufacturer_id; awaiting §4.4 alias confirm
    "frequency_band": "frequency_band",  # Parametric (GSM900/DCS1800/etc.) — not wire-pattern
    "ble_protocol_byte": "ble_protocol_byte",  # Sub-field byte — too coarse for Lynceus match
    "operator_profile": "operator_profile",  # G-17 corporate operator entity — analytical-only
    "x509_cert_sha256_prefix": "x509_cert_sha256_prefix",  # Firmware-anchored cert; Lynceus has no cert-prefix pattern_type
    "ble_adv_interval": "ble_adv_interval",  # Parametric advertisement interval — not wire-pattern
    "ble_payload_offset": "ble_payload_offset",  # Sub-field byte offset — too coarse
    "firmware_sha256_hash": "firmware_sha256_hash",  # Firmware blob hash — not RF-broadcast
    "network_endpoint": "network_endpoint",  # Cloud endpoint — out-of-band IP/DNS; not RF-pattern
    "firmware_image_variant": "firmware_image_variant",  # Vendor-internal taxonomy
    "qualcomm_chip_format_id": "qualcomm_chip_format_id",  # Chip-format id — not wire-pattern
    "firmware_branded_string": "firmware_branded_string",  # Branded string — too vague for match
    # MAC-117 / migration 0019 — round-2 vocab extension (7 net-new identifier_types
    # per SAR-13 §S.3 routing slate (A)). Default DROPPED-class pending §4.4
    # MAP ratification at next CP21 round. Same "carried in canonical DB but
    # not in Lynceus pattern table v0.1" disposition as the mig-0018 cluster.
    "asdstan_message_type": "asdstan_message_type",  # ASTM Remote ID broadcast enum class — awaiting §4.4 MAP review
    "asdstan_enum_value": "asdstan_enum_value",  # ASTM Remote ID field-encoded enum (ua_category/id_type/height_type/location_source)
    "dji_protocol_struct_format": "dji_protocol_struct_format",  # DJI Drone-ID broadcast struct format — awaiting §4.4 MAP review
    "gpt_partition_uuid": "gpt_partition_uuid",  # Device-side storage layout UUID — not RF-broadcast
    "chipset_codename": "chipset_codename",  # Firmware-anchored device model class — not wire-pattern
    "firmware_build_string": "firmware_build_string",  # Firmware build version string — not RF-broadcast
    "firmware_build_uuid": "firmware_build_uuid",  # Firmware build GUID — not RF-broadcast
    # MAC-181 / migration 0023 — CP28(c) Wave H desktop-axis vendor-registered
    # non-BLE cluster DROPPED cases (2 entries). The sibling MAP case
    # (`vendor_document_uuid_cloud_reference`) lives in
    # IDENTIFIER_TYPE_TO_PATTERN_TYPE above per CP28(c) §4.4 posture.
    "windows_installer_productcode_vendor_registered": "windows_installer_productcode_vendor_registered",  # Install/registry context only; low passive-scan utility
    "windows_com_clsid_vendor_registered": "windows_com_clsid_vendor_registered",  # Install/registry context only; low passive-scan utility
    # CP29 (migration 0024) — Wave I/I.5/I.6/I.7 vendor cloud-infrastructure
    # hostname corpus (3 net-new identifier_types). Default DROPPED-class
    # pending §4.4 MAP ratification at next CP21 round. Mirrors the §4.4
    # CP28(c) sibling MAP precedent (`vendor_document_uuid_cloud_reference`)
    # which is the only currently-promoted cloud-hostname identifier_type;
    # the CP29 corpus types remain DROPPED-class until per-type MAP
    # ratification lifts them individually. All current live rows carry
    # `device_category='unknown'` and tally via the §11 #13 carve-out;
    # adding them to DROPPED_REASONS aligns §4.4 disposition discipline
    # without changing live row classifications.
    "vendor_controlled_hostname": "vendor_controlled_hostname",  # Vendor cloud-hostname corpus; Lynceus-side scanner work item to add cloud-hostname pattern_type
    "vendor_cloud_endpoint_url": "vendor_cloud_endpoint_url",  # Cloud endpoint URL — out-of-band IP/DNS; not RF-broadcast pattern
    "vendor_controlled_hostname_deprecated": "vendor_controlled_hostname_deprecated",  # Deprecated vendor hostname — carried for audit, not in match table
    # CP31 (migration 0025) — FCC EAS identifier-type cluster (2 net-new
    # identifier_types). Default DROPPED-class — FCC grantee/equipment-class
    # codes are regulatory entity IDs, not RF-broadcast wire-pattern values
    # observable by Lynceus's passive scanners. Promoting them would require
    # a Lynceus-side scanner pathway that doesn't exist (FCC IDs are vendor-
    # registration metadata, not on-air broadcast strings). All current live
    # rows carry `device_category='unknown'` and tally via the §11 #13
    # carve-out.
    "fcc_grantee_code": "fcc_grantee_code",  # FCC EAS grantee code — regulatory entity ID; not RF-broadcast wire pattern
    "equipment_class_code": "equipment_class_code",  # FCC EAS equipment-class code — regulatory ID; not RF-broadcast wire pattern
    # CP35 (mig-0028 / MAC-255) — NDPP §4.4 disposition. Option (b) DROP
    # ratified at MAC-255 (option (a) MAP would require sibling Lynceus v0.3
    # scanner work for a new `discovery_protocol_signature` pattern_type,
    # cross-repo coordination outside the v1.5.3 ship-gate scope). 18 NDPP
    # rows preserved in canonical `identifiers` for future export-time
    # admission once Lynceus v0.3 ships. Bin_label `NDPP_pending_lynceus_v0_3_scanner_support`
    # carries the pending-rationale verbatim per the CP35 ratification dispatch;
    # this is the first DROPPED_REASONS entry whose bin_label differs from
    # the identifier_type string (all prior entries are identity-keyed). Mirrors
    # CP16 default DROP posture (12 DROPPED vs 3 MAP for CP14 cluster).
    "network_discovery_protocol_pattern": "NDPP_pending_lynceus_v0_3_scanner_support",
}

# §4.5 severity mapping — SUPERSEDED at CP8 (2026-05-07).
# Severity is now owned operator-side via Lynceus's ``severity_overrides.yaml``;
# the export shape no longer emits ``severity``. The mapping below is retained
# only for audit-trail / historical-reasoning continuity per CP8 sub-correction
# B; future export shape changes MUST NOT consult this table for severity
# values.
_DEVICE_CATEGORY_TO_SEVERITY_HISTORICAL: dict[str, str] = {
    "imsi_catcher": "high",
    "alpr": "high",
    "covert_cam": "high",
    "hacking_tool": "high",
    "gps_tracker": "high",
    "face_recog": "high",
    "drone_detect": "med",
    "body_cam": "med",
    "drone": "med",
    "police_radio": "low",
    "in_vehicle_router": "low",
    "gunshot_detect": "low",
}

# §8.4 / §11 #12 Pi self-exclude OUIs (the running-scanner hardware family).
PI_SELF_EXCLUDE_OUIS: frozenset[str] = frozenset(
    {"b8:27:eb", "dc:a6:32", "e4:5f:01", "28:cd:c1"}
)

# CP19 (§7.5) — source_type values excluded from the high-confidence Lynceus
# export regardless of confidence value. Single-source `inferred` /
# `crowdsourced` rows still satisfy CP18's ≥70 confidence floor (75 / 70
# ceilings per §8.2) but lack a §8.3 cross-band corroboration anchor, so
# they are not safe to publish on the high-confidence operational feed.
# The standard export (≥30 floor) retains them — wider-net rich-import
# consumers still benefit. Mirrors `coverage_matrix.py::EXCLUDED_SOURCE_TYPES`;
# the two modules must classify CP19 rows identically (`_reconcile` halts on
# any mismatch).
EXCLUDED_SOURCE_TYPES: frozenset[str] = frozenset({"inferred", "crowdsourced"})

# §4.4 mac_range expansion ceiling.
MAC_RANGE_EXPANSION_CEILING = 256

# §7.5 description-format constraint (CP8 flat form ≤80 chars).
DESCRIPTION_MAX_CHARS = 80

# CP8 description-format fallbacks (verbatim).
DESCRIPTION_VENDOR_UNATTRIBUTED = "Unattributed identifier"

# CP7 default geographic_scope filter (US-deployed Lynceus instances).
DEFAULT_GEOGRAPHIC_SCOPE_FILTER: tuple[str, ...] = ("US",)

# Deterministic UUID5 namespace anchor — locks ``argus_run_id`` to the data.
# This namespace UUID itself is a UUID5(NAMESPACE_DNS, "argus.export.v1") so
# the choice is reproducible from this codebase alone (no opaque magic value).
ARGUS_RUN_ID_NAMESPACE: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_DNS, "argus.export.v1")


class Halt(Exception):
    """Stop-the-line signal raised on any §11 trip or reconciliation mismatch."""


@dataclass(frozen=True)
class ActiveRow:
    """A single ``identifiers`` row in the active set."""

    id: int
    identifier: str
    identifier_type: str
    device_category: str
    manufacturer: str | None
    model: str | None
    confidence: int
    source_type: str
    source_url: str
    source_excerpt: str | None
    notes: str | None
    geographic_scope: str | None
    first_seen: str | None
    last_verified: str | None


@dataclass(frozen=True)
class TalosEntry:
    """A single entry written to ``argus_export*.json``.

    ``argus_record_id`` is the SAR-10 hash (16-hex-char SHA-256 prefix of
    ``f"{identifier_type}|{normalized_identifier}"``); not the integer PK.
    Severity is no longer emitted (CP8 sub-correction B: severity owned
    operator-side via Lynceus's ``severity_overrides.yaml``).
    """

    pattern: str
    pattern_type: str
    description: str
    argus_record_id: str


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only = ON;")
    return con


def _load_active_rows(con: sqlite3.Connection) -> list[ActiveRow]:
    cur = con.execute(
        """
        SELECT id, identifier, identifier_type, device_category, manufacturer,
               model, confidence, source_type, source_url, source_excerpt,
               notes, geographic_scope, first_seen, last_verified
        FROM identifiers
        WHERE superseded_by IS NULL
        ORDER BY id ASC
        """
    )
    rows: list[ActiveRow] = []
    for r in cur.fetchall():
        rows.append(
            ActiveRow(
                id=r["id"],
                identifier=r["identifier"],
                identifier_type=r["identifier_type"],
                device_category=r["device_category"],
                manufacturer=r["manufacturer"],
                model=r["model"],
                confidence=r["confidence"],
                source_type=r["source_type"],
                source_url=r["source_url"],
                source_excerpt=r["source_excerpt"],
                notes=r["notes"],
                geographic_scope=r["geographic_scope"],
                first_seen=r["first_seen"],
                last_verified=r["last_verified"],
            )
        )
    return rows


def _load_schema_version(con: sqlite3.Connection) -> int:
    cur = con.execute("SELECT MAX(version) AS v FROM schema_version")
    row = cur.fetchone()
    return int(row["v"])


def _load_drop_assignments(report_path: Path) -> dict[str, dict[str, str]]:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    return {
        "argus_export.json": payload["drop_tally_standard"]["drop_assignments"],
        "argus_export_high_confidence.json": payload["drop_tally_high_confidence"][
            "drop_assignments"
        ],
    }


def _derive_argus_run_id(rows: list[ActiveRow]) -> str:
    """Deterministic UUID5 from the canonical-set fingerprint.

    The fingerprint binds id + identifier + identifier_type + device_category
    + manufacturer + confidence; same DB state ⇒ same UUID. This is what
    makes re-runs byte-identical modulo the ``exported_at`` field.
    """

    fingerprint_parts = [
        f"{r.id}|{r.identifier}|{r.identifier_type}|{r.device_category}|"
        f"{r.manufacturer or ''}|{r.confidence}|{r.source_type}"
        for r in rows
    ]
    fingerprint = "\n".join(fingerprint_parts).encode("utf-8")
    digest = hashlib.sha256(fingerprint).hexdigest()
    return str(uuid.uuid5(ARGUS_RUN_ID_NAMESPACE, digest))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_datetime(value: str | None) -> str:
    """Normalize a `DATETIME` column value to canonical ISO-8601 UTC with `Z`.

    Per CP22 (bible §7.5 sub-amend), the canonical timestamp format for
    `first_seen` and `last_verified` in `argus_export.csv` is ISO-8601 UTC
    with `Z` suffix at seconds precision: ``"YYYY-MM-DDTHH:MM:SSZ"``. The
    `identifiers` table column type is `DATETIME` (SQLite-typeless TEXT)
    with no SQL-level format constraint, and historical write paths produced
    at least four distinct shapes:

    - empty (``""`` or ``NULL``): ``""`` (preserved)
    - ISO-8601 with offset (``"2026-05-14T06:13:42.204792+00:00"``): coerced
      to UTC, microseconds dropped, emitted as Z form.
    - ISO-8601 with `Z` (``"2026-05-11T18:21:50Z"``): idempotent.
    - space-separated (``"2026-05-06 00:30:28"``): treated as UTC, emitted
      as Z form.
    - date-only (``"2026-05-10"``): emitted as midnight UTC Z form
      (``"2026-05-10T00:00:00Z"``); preserves the only signal the row
      carries (write path lost intra-day precision).

    Any input that does not parse into one of the above shapes raises
    `ValueError` so a future write-path emitting a fifth shape surfaces
    immediately rather than silently producing malformed CSV (the F6
    smoke-test class of bug).
    """
    if value is None or value == "":
        return ""
    raw = value.strip()
    # ISO-8601 with explicit offset or `Z` — Python 3.11+ `fromisoformat`
    # accepts both. Coerce to UTC, drop microseconds, emit Z form.
    if "T" in raw:
        normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"unparseable ISO-8601 timestamp: {value!r}") from exc
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    # Space-separated `YYYY-MM-DD HH:MM:SS` — historical write-path form.
    if " " in raw:
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise ValueError(f"unparseable space-separated timestamp: {value!r}") from exc
        return dt.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Date-only `YYYY-MM-DD` — midnight UTC.
    if len(raw) == 10 and raw.count("-") == 2:
        try:
            dt = datetime.strptime(raw, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"unparseable date-only timestamp: {value!r}") from exc
        return dt.replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise ValueError(f"unrecognized timestamp shape: {value!r}")


def _format_description(row: ActiveRow) -> str:
    """Build a §7.5-compliant description ≤80 chars per CP8 flat form.

    CP8 ladder (verbatim):
    - Vendor unknown → ``"Unattributed identifier"``.
    - Vendor known, category unknown → ``"{vendor} unknown"``.
    - Both known → ``"{vendor} {device_category}"``.

    Defensive: if the constructed string exceeds the §7.5 80-char ceiling
    (only reachable if a §2.1 vendor name + device_category > 80 chars; in
    practice all current §2.1 combinations fit comfortably), fall back to
    ``"Unattributed identifier"``. The classifier still halts on overflow
    via ``_classify_row`` as defense-in-depth against generator drift.
    """

    vendor = (row.manufacturer or "").strip()
    if not vendor:
        return DESCRIPTION_VENDOR_UNATTRIBUTED
    if row.device_category == "unknown":
        candidate = f"{vendor} unknown"
    else:
        candidate = f"{vendor} {row.device_category}"
    if len(candidate) <= DESCRIPTION_MAX_CHARS:
        return candidate
    return DESCRIPTION_VENDOR_UNATTRIBUTED


def _classify_row(
    row: ActiveRow,
    *,
    confidence_threshold: int,
    apply_pi_self_exclude: bool,
    apply_excluded_source_type: bool = False,
) -> tuple[str | None, list[TalosEntry]]:
    """Classify a row for a Lynceus export file (static gates only).

    Returns ``(drop_bin, entries)``. If ``drop_bin`` is None the row is a
    survivor and ``entries`` is non-empty. Bin priority is the dispatch's
    canonical order:

        procurement_only > unknown_category > device_fingerprint
        > ssid_pattern > ble_local_name > ble_characteristic
        > product_family_codename > oversized_mac_range
        > {CP16 DROPPED_REASONS} > self_exclude_oui
        > below_confidence_threshold > excluded_source_type

    The §11 #14 procurement bin sits above §11 #13 unknown_category because
    procurement-only rows have no concrete identifier at all and are never
    in the main `identifiers` table by design (§4.5); the gate is here as
    defense-in-depth.

    The CP13 type-drop bins (`ble_local_name`, `ble_characteristic`,
    `product_family_codename`) sit above the confidence-floor gate and the
    Pi self-exclude gate, so an analytical-only Wave G row is binned by its
    type regardless of confidence (matches the existing handling of
    `device_fingerprint` and `ssid_pattern`).

    The CP19 ``excluded_source_type`` bin (§7.5) sits AFTER the confidence
    floor: a row with `source_type ∈ {inferred, crowdsourced}` AND
    `confidence < threshold` attributes the drop to the more specific
    confidence reason; the CP19 bin only catches rows that would otherwise
    have survived every prior gate. Gated by `apply_excluded_source_type`
    (True for the high-confidence file, False for the standard file).

    The CP7 ``geographic_scope_mismatch`` bin is NOT applied here — it is a
    runtime parameter applied in ``_apply_geographic_scope_filter()`` after
    static reconciliation against MAC-45.
    """

    # §11 #14 — procurement-only ban (defense-in-depth: should not appear
    # in `identifiers` per §4.1 + §4.5, but check anyway).
    if row.source_type == "procurement":
        return "procurement_only", []
    # §11 #13 — unknown-category ban.
    if row.device_category == "unknown":
        return "unknown_category", []
    # §4.4 — device_fingerprint dropped.
    if row.identifier_type == "device_fingerprint":
        return "device_fingerprint", []
    # §4.4 — ssid_pattern dropped (no regex in Lynceus v0.2).
    if row.identifier_type == "ssid_pattern":
        return "ssid_pattern", []
    # §4.4 CP13 — Wave G analytical-only types. All three are DROPPED-class:
    # carried in the canonical DB but never reach the Lynceus pattern table.
    if row.identifier_type == "ble_local_name":
        return "ble_local_name", []
    if row.identifier_type == "ble_characteristic":
        return "ble_characteristic", []
    if row.identifier_type == "product_family_codename":
        return "product_family_codename", []
    # §4.4 — mac_range expand or drop.
    if row.identifier_type == "mac_range":
        # The expansion logic stays codified for the case of a non-`unknown`-
        # category mac_range row reaching this gate. Currently no such row
        # exists in the active identifiers set (all live mac_range rows have
        # category='unknown' and hit the §11 #13 unknown_category gate above);
        # the branch fires only on a future Phase-5 reopening or category-
        # correction promotion that lifts a mac_range out of unknown.
        return "oversized_mac_range", []
    # §4.4 CP16 — CP14 identifier_type cluster DROPPED-with-reason filter.
    # 12 new analytical-only types from migrations 0011/0013/0014; carried
    # in the canonical DB but never reach the Lynceus pattern table. See
    # PROJECT_BIBLE.md §4.4 (CP16 amendment) for per-type rationale.
    # Future hygiene-pass-only: the 6 legacy branches above (device_fingerprint,
    # ssid_pattern, ble_local_name, ble_characteristic, product_family_codename,
    # mac_range) could fold into DROPPED_REASONS in a later cleanup commit.
    # Out of CP16 scope.
    if row.identifier_type in DROPPED_REASONS:
        return DROPPED_REASONS[row.identifier_type], []
    # §8.4 / §11 #12 — Pi self-exclude OUI list (high-confidence file only).
    if (
        apply_pi_self_exclude
        and row.identifier_type == "oui"
        and row.identifier in PI_SELF_EXCLUDE_OUIS
    ):
        return "self_exclude_oui", []
    # §7.5 — confidence floor.
    if row.confidence < confidence_threshold:
        return "below_confidence_threshold", []
    # CP19 (§7.5) — high-conf-only source_type exclusion. A row reaching this
    # gate has cleared every prior static filter (incl. CP18's ≥70 floor for
    # the high-conf file); the CP19 bin captures rows excluded for lack of a
    # §8.3 cross-band corroboration anchor. Standard export (≥30 floor)
    # passes inferred/crowdsourced through. Mirrors
    # `coverage_matrix.py::_assign_drop_bin`'s identical late-priority gate.
    if apply_excluded_source_type and row.source_type in EXCLUDED_SOURCE_TYPES:
        return "excluded_source_type", []

    pattern_type = IDENTIFIER_TYPE_TO_PATTERN_TYPE.get(row.identifier_type)
    if pattern_type is None:
        # Defensive: any §4.4 mapping miss not caught above is a bug.
        raise Halt(
            f"row id={row.id} identifier_type={row.identifier_type} has no "
            "§4.4 mapping but reached the survivor branch — §4.4 schema drift?"
        )
    description = _format_description(row)
    if len(description) > DESCRIPTION_MAX_CHARS:
        raise Halt(
            f"row id={row.id} description '{description}' exceeds "
            f"{DESCRIPTION_MAX_CHARS}-char §7.5 ceiling"
        )
    return None, [
        TalosEntry(
            pattern=row.identifier,
            pattern_type=pattern_type,
            description=description,
            argus_record_id=_sar10_hash(row.identifier_type, row.identifier),
        )
    ]


def _passes_geographic_scope(
    row: ActiveRow,
    *,
    geographic_scope_filter: tuple[str, ...],
    is_high_confidence: bool,
) -> bool:
    """CP7 export-time filter: True if row passes the geographic_scope gate.

    Rules (verbatim from BIBLE_AMENDMENTS.md CP7):
    - ``global`` passes unconditionally.
    - Match against any element of ``geographic_scope_filter`` (case-sensitive
      on ISO codes; comma-sep handled per §4.1) → pass.
    - ``unknown`` (or NULL): passes the standard export, fails the
      high-confidence export.
    - Else: fail.
    """

    raw = (row.geographic_scope or "").strip()
    if not raw or raw == "unknown":
        return not is_high_confidence
    if raw == "global":
        return True
    # §4.1 allows comma-separated lists of ISO codes — split and match any.
    row_codes = {part.strip() for part in raw.split(",") if part.strip()}
    return any(code in row_codes for code in geographic_scope_filter)


def _reconcile(
    *,
    file_label: str,
    rows: list[ActiveRow],
    bin_assignments: dict[int, str | None],
    expected: dict[str, str],
) -> None:
    """Halt on any mismatch vs MAC-45's drop_assignments map.

    The MAC-45 map is the contract: every active row id appears either as
    a drop bin OR is absent (survivor). The writer's classification must
    match exactly. Any disagreement halts.
    """

    expected_int = {int(k): v for k, v in expected.items()}
    actual_drops = {row_id: bin_label for row_id, bin_label in bin_assignments.items() if bin_label is not None}
    # Every MAC-45 drop must equal the writer's classification.
    for row_id, expected_bin in expected_int.items():
        actual_bin = bin_assignments.get(row_id)
        if actual_bin != expected_bin:
            raise Halt(
                f"{file_label}: row id={row_id} writer-classified as "
                f"{actual_bin!r} but MAC-45 drop_assignments map says "
                f"{expected_bin!r} — STOP-THE-LINE per dispatch (do NOT silently re-tally)."
            )
    # Every writer drop must equal the MAC-45 expectation (catches extras).
    for row_id, actual_bin in actual_drops.items():
        if row_id not in expected_int:
            raise Halt(
                f"{file_label}: row id={row_id} writer-classified as "
                f"{actual_bin!r} but MAC-45 has no entry — input drift, "
                "STOP-THE-LINE."
            )
    # Active row set vs MAC-45 source set must match: every active row id
    # must be either dropped or surviving per writer.
    writer_ids = {row.id for row in rows}
    mac45_ids = set(expected_int.keys()) | {
        row.id
        for row in rows
        if bin_assignments.get(row.id) is None
    }
    if writer_ids != mac45_ids:
        # MAC-45 only carries drop_assignments (drops). Active-but-not-dropped
        # rows are survivors and aren't in the map. So the only valid
        # mismatch is "writer has a row id not in MAC-45 drop list AND not
        # surviving" — which would already trip the actual_drops loop above.
        # This branch is defense-in-depth.
        raise Halt(
            f"{file_label}: active row id set {writer_ids} disagrees with "
            f"MAC-45 reconstruction {mac45_ids} — STOP-THE-LINE."
        )


def _build_meta(
    *,
    schema_version: int,
    confidence_threshold: int,
    geographic_scope_filter: tuple[str, ...],
    argus_run_id: str,
    exported_at: str,
    source_record_count: int,
    bins: dict[str, int],
) -> dict[str, Any]:
    """Build the §7.5 ``_meta`` block (CP7 augments with scope filter)."""

    return {
        "argus_version": str(schema_version),
        "exported_at": exported_at,
        "record_count": source_record_count - sum(bins.values()),
        "confidence_threshold": confidence_threshold,
        "geographic_scope_filter": list(geographic_scope_filter),
        "argus_run_id": argus_run_id,
        "source_record_count": source_record_count,
        "dropped_in_export": bins,
    }


# §11 #3 export-time email-shape guard (MAC-217). Defense-in-depth: future
# ingest leaks must not silently re-introduce PII into v1.4.1+ exports.
_PII_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# MAC-288 Phase 6 surfaced a false-positive class: APK / IPA / AAR package
# source_urls of the shape `com.foo.bar@1.2.3.apk` (Android package@version
# with software-container suffix) match the email regex but are not PII.
# These suffixes are not real DNS TLDs, so the carve-out cannot mask a
# legitimately-deliverable address. §11 #11 amendment surfaced to CEO.
_SOFTWARE_PACKAGE_SUFFIXES = (".apk", ".ipa", ".aar", ".jar", ".deb", ".rpm", ".xpi")


def _assert_no_email_pii(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    raw_matches = _PII_EMAIL_RE.findall(text)
    matches = [m for m in raw_matches if not m.lower().endswith(_SOFTWARE_PACKAGE_SUFFIXES)]
    if matches:
        sample = matches[:3]
        raise Halt(
            f"§11 #3 export-guard FAILED for {path.name}: {len(matches)} email-shape token(s) "
            f"found. Sample (up to 3): {sample}. Refusing to emit PII-bearing export."
        )


def _write_json(path: Path, payload: dict[str, Any]) -> int:
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    path.write_text(text, encoding="utf-8")
    _assert_no_email_pii(path)
    return len(text.encode("utf-8"))


def _write_csv(path: Path, rows: list[ActiveRow], schema_version: int, exported_at: str) -> int:
    """Write the rich-import CSV (all active canonicals, no CP7 filter).

    CP11 dual-artifact contract: this is the rich-import feed for Lynceus.
    The 15-column shape carries `argus_record_id` (SAR-10 hash), `description`
    (CP8 flat ≤80-char form, byte-identical to the JSON-feed `description`
    via shared `_format_description`), and the `first_seen`/`last_verified`
    columns directly from the `identifiers` table. Operators apply
    geographic / category / confidence filters at Lynceus-side import.
    """

    header_meta = (
        f"# meta: schema_version={schema_version}, exported_at={exported_at}, "
        f"record_count={len(rows)}, confidence_threshold=0\n"
    )
    field_order = [
        "argus_record_id",
        "id",
        "identifier",
        "identifier_type",
        "device_category",
        "manufacturer",
        "model",
        "confidence",
        "source_type",
        "source_url",
        "source_excerpt",
        "geographic_scope",
        "description",
        "first_seen",
        "last_verified",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(header_meta)
        writer = csv.DictWriter(fh, fieldnames=field_order, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "argus_record_id": _sar10_hash(row.identifier_type, row.identifier),
                    "id": row.id,
                    "identifier": row.identifier,
                    "identifier_type": row.identifier_type,
                    "device_category": row.device_category,
                    "manufacturer": row.manufacturer or "",
                    "model": row.model or "",
                    "confidence": row.confidence,
                    "source_type": row.source_type,
                    "source_url": row.source_url,
                    "source_excerpt": (row.source_excerpt or "").replace("\r\n", "\n"),
                    "geographic_scope": row.geographic_scope or "",
                    "description": _format_description(row),
                    "first_seen": _normalize_datetime(row.first_seen),
                    "last_verified": _normalize_datetime(row.last_verified),
                    "notes": (row.notes or "").replace("\r\n", "\n"),
                }
            )
    _assert_no_email_pii(path)
    return path.stat().st_size


def _build_export(
    *,
    rows: list[ActiveRow],
    file_label: str,
    confidence_threshold: int,
    apply_pi_self_exclude: bool,
    schema_version: int,
    argus_run_id: str,
    exported_at: str,
    expected_drop_assignments: dict[str, str],
    geographic_scope_filter: tuple[str, ...] = DEFAULT_GEOGRAPHIC_SCOPE_FILTER,
    apply_excluded_source_type: bool = False,
) -> tuple[dict[str, Any], dict[int, str | None]]:
    """Classify every row, reconcile vs MAC-45 (static gates), apply CP7
    geographic_scope filter post-reconciliation, return the §7.5 payload.

    Bin order in ``bins`` dict follows priority order; ``geographic_scope_mismatch``
    sits at the tail because it is a runtime parameter applied after MAC-45
    reconciliation and is independent of the static classification surface.
    """

    bins: dict[str, int] = {
        "unknown_category": 0,
        "ssid_pattern": 0,
        "device_fingerprint": 0,
        # CP13 (§4.4) — Wave G analytical-only types (DROPPED-class).
        "ble_local_name": 0,
        "ble_characteristic": 0,
        "product_family_codename": 0,
        "oversized_mac_range": 0,
        # CP16 (§4.4) — CP14 identifier_type cluster DROPPED-class types.
        # Keys match DROPPED_REASONS values one-to-one (one zero-init per
        # new CP16 bin label) so the aggregation loop `bins[drop_bin] += 1`
        # succeeds for the new branch's returns. Phase-3 architectural claim
        # that this needed no code change was wrong; Phase-4 dry-run caught
        # the gap. See feedback memo S.6 (architectural-absorption sub-rule).
        "icao_24bit_address": 0,
        "rf_channel": 0,
        "burst_cadence_ms": 0,
        "bandwidth_mhz": 0,
        "device_class_id": 0,
        "rf_burst_duration": 0,
        "rf_protocol_constant": 0,
        "wifi_ie_element_id": 0,
        "bluetooth_le_pdu_type": 0,
        "wifi_frame_control_subtype": 0,
        "wifi_nan_param_signature": 0,
        "alpr_model": 0,
        # Migration 0018 / SAR-13 §S.3 — 14 net-new identifier_types from MAC-109.
        # See DROPPED_REASONS for rationale.
        "ble_protocol_byte_table": 0,
        "ble_service_uuid": 0,
        "ble_company_id": 0,
        "frequency_band": 0,
        "ble_protocol_byte": 0,
        "operator_profile": 0,
        "x509_cert_sha256_prefix": 0,
        "ble_adv_interval": 0,
        "ble_payload_offset": 0,
        "firmware_sha256_hash": 0,
        "network_endpoint": 0,
        "firmware_image_variant": 0,
        "qualcomm_chip_format_id": 0,
        "firmware_branded_string": 0,
        # MAC-117 / migration 0019 — 7 net-new identifier_types per SAR-13 §S.3
        # routing slate (A). See DROPPED_REASONS for rationale.
        "asdstan_message_type": 0,
        "asdstan_enum_value": 0,
        "dji_protocol_struct_format": 0,
        "gpt_partition_uuid": 0,
        "chipset_codename": 0,
        "firmware_build_string": 0,
        "firmware_build_uuid": 0,
        # MAC-181 / migration 0023 — CP28(c) Wave H desktop-axis vendor-registered
        # non-BLE cluster DROPPED-class types (2). See DROPPED_REASONS for rationale.
        # The sibling MAP case (`vendor_document_uuid_cloud_reference`) lives in
        # IDENTIFIER_TYPE_TO_PATTERN_TYPE; it doesn't need a bin here.
        "windows_installer_productcode_vendor_registered": 0,
        "windows_com_clsid_vendor_registered": 0,
        # CP29 (migration 0024) — Wave I vendor cloud-infrastructure hostname
        # corpus (3 net-new). See DROPPED_REASONS for rationale.
        "vendor_controlled_hostname": 0,
        "vendor_cloud_endpoint_url": 0,
        "vendor_controlled_hostname_deprecated": 0,
        # CP31 (migration 0025) — FCC EAS identifier-type cluster (2 net-new).
        # See DROPPED_REASONS for rationale.
        "fcc_grantee_code": 0,
        "equipment_class_code": 0,
        # CP35 (mig-0028 / MAC-255) — NDPP §4.4 ratified DROP. Bin_label is
        # the pending-rationale string (not the identifier_type) per CP35
        # dispatch; the bins dict keys must match DROPPED_REASONS values
        # one-to-one or `bins[drop_bin] += 1` would KeyError.
        "NDPP_pending_lynceus_v0_3_scanner_support": 0,
        "procurement_only": 0,
        "self_exclude_oui": 0,
        "below_confidence_threshold": 0,
        # CP19 (§7.5) — source_type exclusion bin. Zero-init in BOTH files so
        # the dict shape is parallel; only the high-conf file populates non-zero
        # via `apply_excluded_source_type=True`. The standard export keeps
        # `excluded_source_type=0` per CP19 narrow-targeting directive.
        "excluded_source_type": 0,
        "geographic_scope_mismatch": 0,
    }
    bin_assignments: dict[int, str | None] = {}
    survivor_rows: list[tuple[ActiveRow, TalosEntry]] = []
    for row in rows:
        drop_bin, row_entries = _classify_row(
            row,
            confidence_threshold=confidence_threshold,
            apply_pi_self_exclude=apply_pi_self_exclude,
            apply_excluded_source_type=apply_excluded_source_type,
        )
        bin_assignments[row.id] = drop_bin
        if drop_bin is not None:
            bins[drop_bin] += 1
        else:
            for entry in row_entries:
                survivor_rows.append((row, entry))
    # Static-gate reconciliation against MAC-45 happens BEFORE the CP7
    # geographic filter — MAC-45 captures the static priors only.
    _reconcile(
        file_label=file_label,
        rows=rows,
        bin_assignments=bin_assignments,
        expected=expected_drop_assignments,
    )
    # CP7 geographic_scope filter (runtime parameter, post-reconciliation).
    is_high_confidence = confidence_threshold >= 70
    entries: list[TalosEntry] = []
    for row, entry in survivor_rows:
        if _passes_geographic_scope(
            row,
            geographic_scope_filter=geographic_scope_filter,
            is_high_confidence=is_high_confidence,
        ):
            entries.append(entry)
        else:
            bin_assignments[row.id] = "geographic_scope_mismatch"
            bins["geographic_scope_mismatch"] += 1
    meta = _build_meta(
        schema_version=schema_version,
        confidence_threshold=confidence_threshold,
        geographic_scope_filter=geographic_scope_filter,
        argus_run_id=argus_run_id,
        exported_at=exported_at,
        source_record_count=len(rows),
        bins=bins,
    )
    payload = {
        "_meta": meta,
        "entries": [
            {
                "pattern": e.pattern,
                "pattern_type": e.pattern_type,
                "description": e.description,
                "argus_record_id": e.argus_record_id,
            }
            for e in sorted(entries, key=lambda e: e.argus_record_id)
        ],
    }
    return payload, bin_assignments


def _build_coverage_report_md(
    *,
    rows: list[ActiveRow],
    standard_payload: dict[str, Any],
    high_payload: dict[str, Any],
    schema_version: int,
    argus_run_id: str,
    matrix_md: str,
    coverage_matrix_report: dict[str, Any],
) -> str:
    """Stitch the §6 Phase 5 #4 + §9 item 9 coverage_report.md.

    Embeds the MAC-45 matrix verbatim as the matrix section seed, then layers
    the §9 item 9 drop tally with full reconciliation against both Talos
    files' ``_meta.dropped_in_export`` blocks.
    """

    standard_meta = standard_payload["_meta"]
    high_meta = high_payload["_meta"]
    standard_bins = standard_meta["dropped_in_export"]
    high_bins = high_meta["dropped_in_export"]
    source_count = len(rows)

    def fmt_bin_table(bins: dict[str, int], label: str, threshold: int) -> str:
        bin_rows = [
            ("unknown_category (§11 #13)", bins["unknown_category"]),
            ("procurement_only (§11 #14)", bins["procurement_only"]),
            ("device_fingerprint (§4.4)", bins["device_fingerprint"]),
            ("ssid_pattern (§4.4)", bins["ssid_pattern"]),
            ("ble_local_name (§4.4 CP13)", bins["ble_local_name"]),
            ("ble_characteristic (§4.4 CP13)", bins["ble_characteristic"]),
            ("product_family_codename (§4.4 CP13)", bins["product_family_codename"]),
            ("oversized_mac_range (§4.4)", bins["oversized_mac_range"]),
            # CP16 (§4.4) — CP14 identifier_type cluster DROPPED-class types.
            ("icao_24bit_address (§4.4 CP16)", bins["icao_24bit_address"]),
            ("rf_channel (§4.4 CP16)", bins["rf_channel"]),
            ("burst_cadence_ms (§4.4 CP16)", bins["burst_cadence_ms"]),
            ("bandwidth_mhz (§4.4 CP16)", bins["bandwidth_mhz"]),
            ("device_class_id (§4.4 CP16)", bins["device_class_id"]),
            ("rf_burst_duration (§4.4 CP16)", bins["rf_burst_duration"]),
            ("rf_protocol_constant (§4.4 CP16)", bins["rf_protocol_constant"]),
            ("wifi_ie_element_id (§4.4 CP16)", bins["wifi_ie_element_id"]),
            ("bluetooth_le_pdu_type (§4.4 CP16)", bins["bluetooth_le_pdu_type"]),
            ("wifi_frame_control_subtype (§4.4 CP16)", bins["wifi_frame_control_subtype"]),
            ("wifi_nan_param_signature (§4.4 CP16)", bins["wifi_nan_param_signature"]),
            ("alpr_model (§4.4 CP16)", bins["alpr_model"]),
            # Migration 0018 / SAR-13 §S.3 — MAC-109 vocab-extension cluster.
            ("ble_protocol_byte_table (§4.4 mig0018)", bins["ble_protocol_byte_table"]),
            ("ble_service_uuid (§4.4 mig0018)", bins["ble_service_uuid"]),
            ("ble_company_id (§4.4 mig0018)", bins["ble_company_id"]),
            ("frequency_band (§4.4 mig0018)", bins["frequency_band"]),
            ("ble_protocol_byte (§4.4 mig0018)", bins["ble_protocol_byte"]),
            ("operator_profile (§4.4 mig0018)", bins["operator_profile"]),
            ("x509_cert_sha256_prefix (§4.4 mig0018)", bins["x509_cert_sha256_prefix"]),
            ("ble_adv_interval (§4.4 mig0018)", bins["ble_adv_interval"]),
            ("ble_payload_offset (§4.4 mig0018)", bins["ble_payload_offset"]),
            ("firmware_sha256_hash (§4.4 mig0018)", bins["firmware_sha256_hash"]),
            ("network_endpoint (§4.4 mig0018)", bins["network_endpoint"]),
            ("firmware_image_variant (§4.4 mig0018)", bins["firmware_image_variant"]),
            ("qualcomm_chip_format_id (§4.4 mig0018)", bins["qualcomm_chip_format_id"]),
            ("firmware_branded_string (§4.4 mig0018)", bins["firmware_branded_string"]),
            # MAC-117 / migration 0019 — round-2 vocab extension cluster.
            ("asdstan_message_type (§4.4 mig0019)", bins["asdstan_message_type"]),
            ("asdstan_enum_value (§4.4 mig0019)", bins["asdstan_enum_value"]),
            ("dji_protocol_struct_format (§4.4 mig0019)", bins["dji_protocol_struct_format"]),
            ("gpt_partition_uuid (§4.4 mig0019)", bins["gpt_partition_uuid"]),
            ("chipset_codename (§4.4 mig0019)", bins["chipset_codename"]),
            ("firmware_build_string (§4.4 mig0019)", bins["firmware_build_string"]),
            ("firmware_build_uuid (§4.4 mig0019)", bins["firmware_build_uuid"]),
            # CP35 (mig-0028 / MAC-255) — NDPP ratified DROP. Bin label is the
            # pending-rationale string verbatim per CP35 dispatch.
            (
                "NDPP_pending_lynceus_v0_3_scanner_support (§4.4 CP35)",
                bins["NDPP_pending_lynceus_v0_3_scanner_support"],
            ),
            ("self_exclude_oui (§8.4 / §11 #12)", bins["self_exclude_oui"]),
            ("below_confidence_threshold (§7.5)", bins["below_confidence_threshold"]),
            ("excluded_source_type (§7.5 CP19)", bins["excluded_source_type"]),
            ("geographic_scope_mismatch (CP7)", bins["geographic_scope_mismatch"]),
        ]
        lines = [
            f"#### `{label}` (confidence ≥ {threshold})",
            "",
            "| Bin | Count |",
            "|---|---|",
        ]
        total = 0
        for name, n in bin_rows:
            lines.append(f"| {name} | {n} |")
            total += n
        survivors = source_count - total
        check = "✅" if survivors == len(standard_payload["entries"] if label == "argus_export.json" else high_payload["entries"]) else "❌"
        lines.append(f"| **sum(dropped_in_export)** | **{total}** |")
        lines.append(
            f"| **survivors → entries.length** | **{survivors}** |"
        )
        lines.append(
            f"| **reconciliation** | **{source_count} − {total} = {survivors}** {check} |"
        )
        return "\n".join(lines)

    by_category: dict[str, int] = {}
    for row in rows:
        by_category[row.device_category] = by_category.get(row.device_category, 0) + 1
    by_source_type: dict[str, int] = {}
    for row in rows:
        by_source_type[row.source_type] = by_source_type.get(row.source_type, 0) + 1
    by_identifier_type: dict[str, int] = {}
    for row in rows:
        by_identifier_type[row.identifier_type] = by_identifier_type.get(row.identifier_type, 0) + 1

    def fmt_dist(d: dict[str, int]) -> str:
        return ", ".join(f"`{k}`={v}" for k, v in sorted(d.items()))

    md_parts: list[str] = []
    md_parts.append("# Argus Phase-5 coverage report")
    md_parts.append("")
    md_parts.append(
        "Generated by `db/validation/export_lynceus.py` (MAC-46) against the active "
        f"set (`superseded_by IS NULL`) of `db/argus.db`. Active row count: **{source_count}**. "
        f"Schema version: **{schema_version}**. `argus_run_id`: `{argus_run_id}` (deterministic "
        "UUID5 over the active-set fingerprint — re-runs on unchanged DB state produce the "
        "same UUID)."
    )
    md_parts.append("")
    md_parts.append(
        "Read-only pass (`PRAGMA query_only = ON`). No identifier mutations. §8.3 dedup "
        "is closed at Step-5 (MAC-42); Step-6 reads. The MAC-45 coverage matrix at "
        "`extraction_outputs/mac45/coverage_matrix.md` is embedded verbatim as the "
        "Section 1 matrix; this report adds the §9 item 9 drop-tally reconciliation "
        "block and the Section 3 high-level distribution summary."
    )
    md_parts.append("")
    md_parts.append("## Lynceus integration: dual-artifact contract (CP11)")
    md_parts.append("")
    md_parts.append(
        "The v0.1 export ships two consumer-grade artifacts targeting distinct "
        "Lynceus consumer-side use cases:"
    )
    md_parts.append("")
    md_parts.append(
        "1. **`argus_export.json`** — operational alert feed. Minimal entry shape "
        "`{pattern, pattern_type, description, argus_record_id}`. CP7 "
        "`geographic_scope_filter` applied; CP8 ≤80-char flat description applied; "
        "severity owned operator-side per CP8 sub-B. Sized for low-bandwidth / "
        "streaming / alert-oriented ingest."
    )
    md_parts.append(
        "2. **`argus_export.csv`** — rich-import feed. Full canonical row shape "
        "with 15 columns including `argus_record_id` (SAR-10), `description` "
        "(CP8 flat — byte-identical to the JSON-feed `description` via shared "
        "`_format_description`), `first_seen`, `last_verified`. Unfiltered — all "
        "active rows regardless of CP7 filter. Operators apply geographic / "
        "category / confidence filters at Lynceus-side import per "
        "`Lynceus_integration_spec_for_Argus.txt` section 7."
    )
    md_parts.append("")
    md_parts.append(
        "The split satisfies Lynceus's \"no lossy conversion\" principle (Section 2 "
        "spec) without bloating the alert-feed JSON. `fcc_id` deferred to v1.1."
    )
    md_parts.append("")
    md_parts.append("## §11 attestations")
    md_parts.append("")
    md_parts.append(
        "- **§11 #1 (no fabrication)** — every entry, drop tally, and bin count is "
        "derived from `db/argus.db` rows + the MAC-45 `coverage_matrix_report.json` "
        "drop_assignments map; no synthetic values inserted; no fallback heuristics."
    )
    md_parts.append(
        "- **§11 #6 (read-only)** — `PRAGMA query_only = ON` set on the connection. "
        "Zero outbound HTTP. No staging-table writes."
    )
    md_parts.append(
        "- **§11 #7 (provenance carry-through)** — every entry's `argus_record_id` "
        "is the `identifiers.id` value; underlying provenance (`source_url`, "
        "`source_excerpt`) lives unchanged on the cited row. The CSV export carries "
        "the full provenance fields."
    )
    md_parts.append(
        "- **§11 #11 (halt-the-line)** — drop-tally mismatch vs MAC-45 `drop_assignments` "
        "map is a halt; description-overflow (>80 char) is a halt; §4.4 / §4.5 "
        "schema drift is a halt. Halts at HB36: 0."
    )
    md_parts.append(
        "- **§11 #12 (Pi self-exclude OUI)** — `b8:27:eb`, `dc:a6:32`, `e4:5f:01`, "
        "`28:cd:c1` ban applied to `argus_export_high_confidence.json`; "
        "tally bin `self_exclude_oui` populated. (HB36: 0 active Pi OUI rows; "
        "guard is in place for any future Phase-5 reopening.)"
    )
    md_parts.append(
        "- **§11 #13 (unknown-category Talos-banned)** — every row with "
        "`device_category='unknown'` lands in the `unknown_category` bin and never "
        "appears in either Talos JSON file."
    )
    md_parts.append(
        "- **§11 #14 (procurement-only Lynceus-banned)** — defense-in-depth gate; the "
        "`identifiers` table cannot hold a `source_type='procurement'` row that lacks "
        "an identifier per §4.1, but the gate is wired regardless."
    )
    md_parts.append(
        "- **CP7 (geographic_scope export-time filter)** — applied AFTER static "
        "MAC-45 reconciliation as a runtime parameter. `global` passes "
        "unconditionally; ISO-code matches against the filter pass; `unknown` / "
        "NULL passes the standard export but fails the high-confidence export. "
        "Default filter = `[\"US\"]`."
    )
    md_parts.append(
        "- **CP19 (§7.5 source_type exclusion on high-conf export)** — "
        "`source_type IN ('inferred', 'crowdsourced')` is excluded from "
        "`argus_export_high_confidence.json` regardless of confidence value. "
        "Single-source `inferred`/`crowdsourced` rows lack a §8.3 cross-band "
        "corroboration anchor; tally bin `excluded_source_type` captures the "
        "drop attribution. Standard export retains these rows for "
        "wider-net rich-import consumers."
    )
    md_parts.append(
        "- **CP8 (description format + severity reframe)** — flat `{vendor} "
        "{device_category}` ≤80 chars (CP8 sub-correction A); fallbacks "
        "`\"{vendor} unknown\"` and `\"Unattributed identifier\"`. "
        "`severity` field dropped from export shape (CP8 sub-correction B); "
        "owned operator-side via Lynceus's `severity_overrides.yaml`."
    )
    md_parts.append(
        "- **SAR-10 (`argus_record_id`)** — 16-hex-char SHA-256 prefix of "
        "`{identifier_type}|{normalized_identifier}` per `db/export/argus_record_id.py`. "
        "Hashes the §8.3 dedup key; stable under re-runs / confidence drift / "
        "source edits / vendor reattribution."
    )
    md_parts.append("")
    md_parts.append(
        "Idempotency: re-running the writer on unchanged DB state produces "
        "byte-identical files modulo `_meta.exported_at`. `argus_run_id` is a "
        "deterministic UUID5 over the active-set fingerprint; `argus_record_id` "
        "values are deterministic SAR-10 hashes."
    )
    md_parts.append("")
    md_parts.append("## §6 Phase 5 #4 coverage matrix (MAC-45 verbatim)")
    md_parts.append("")
    md_parts.append(
        "The matrix below is the MAC-45 coverage matrix at "
        "`extraction_outputs/mac45/coverage_matrix.md` (commit `6853780`). It is "
        "embedded here verbatim per §9 item 3 ('coverage_report.md exists and shows "
        "category coverage with honest gap analysis'); the upstream module owns the "
        "matrix derivation."
    )
    md_parts.append("")
    md_parts.append("```markdown")
    md_parts.append(matrix_md.rstrip())
    md_parts.append("```")
    md_parts.append("")
    md_parts.append("## §9 item 9 — Dropped from Talos export (Step-6 reconciliation)")
    md_parts.append("")
    md_parts.append(
        "Each active canonical row is assigned to AT MOST one drop bin per file. "
        "Bin priority order matches MAC-45's pre-tally: `procurement_only > "
        "unknown_category > device_fingerprint > ssid_pattern > ble_local_name "
        "> ble_characteristic > product_family_codename > oversized_mac_range "
        "> self_exclude_oui > below_confidence_threshold`. Survivors flow to the "
        "Lynceus export's `entries` array. Reconciliation: "
        "`source_record_count − sum(dropped_in_export) = entries.length`."
    )
    md_parts.append("")
    md_parts.append(
        f"Pre-tally source: MAC-45 `coverage_matrix_report.json` "
        f"(`drop_tally_standard` + `drop_tally_high_confidence`). The Step-6 writer "
        f"(this module) re-derives every row's bin assignment by classifier "
        f"and halts on any mismatch vs the MAC-45 map — no silent re-tally."
    )
    md_parts.append("")
    md_parts.append(fmt_bin_table(standard_bins, "argus_export.json", 30))
    md_parts.append("")
    md_parts.append(fmt_bin_table(high_bins, "argus_export_high_confidence.json", 70))
    md_parts.append("")
    md_parts.append("### MAC-45 ↔ Step-6 cross-check")
    md_parts.append("")
    mac45_std = coverage_matrix_report["drop_tally_standard"]
    mac45_high = coverage_matrix_report["drop_tally_high_confidence"]
    md_parts.append(
        f"- MAC-45 `drop_tally_standard.bins` = "
        f"{json.dumps(mac45_std['bins'], sort_keys=True)} → survivors "
        f"{mac45_std['survivors']} (reconciles {mac45_std['reconciles']})."
    )
    md_parts.append(
        f"- Step-6 `argus_export.json._meta.dropped_in_export` = "
        f"{json.dumps(standard_bins, sort_keys=True)} → survivors "
        f"{standard_meta['record_count']} (reconciles {source_count})."
    )
    md_parts.append(
        f"- MAC-45 `drop_tally_high_confidence.bins` = "
        f"{json.dumps(mac45_high['bins'], sort_keys=True)} → survivors "
        f"{mac45_high['survivors']} (reconciles {mac45_high['reconciles']})."
    )
    md_parts.append(
        f"- Step-6 `argus_export_high_confidence.json._meta.dropped_in_export` = "
        f"{json.dumps(high_bins, sort_keys=True)} → survivors "
        f"{high_meta['record_count']} (reconciles {source_count})."
    )
    md_parts.append(
        "- Conclusion: per-bin equality + per-row `drop_assignments` equality verified "
        "by `_reconcile()` for both files; halts at 0."
    )
    md_parts.append("")
    md_parts.append("## §6.3 distribution summary (Step-6 layer over the matrix)")
    md_parts.append("")
    md_parts.append(
        "Single-axis tallies of the active canonical set, derived directly from the "
        "63 active `identifiers` rows (no Talos filtering). These are the same rows "
        "that flow to `argus_export.csv`."
    )
    md_parts.append("")
    by_geographic_scope: dict[str, int] = {}
    for row in rows:
        key = (row.geographic_scope or "unknown").strip() or "unknown"
        by_geographic_scope[key] = by_geographic_scope.get(key, 0) + 1
    md_parts.append(f"- **By `device_category`:** {fmt_dist(by_category)}")
    md_parts.append(f"- **By `identifier_type`:** {fmt_dist(by_identifier_type)}")
    md_parts.append(f"- **By `source_type`:** {fmt_dist(by_source_type)}")
    md_parts.append(
        f"- **By `geographic_scope` (CP7):** {fmt_dist(by_geographic_scope)}"
    )
    standard_filter = standard_meta.get("geographic_scope_filter", [])
    high_filter = high_meta.get("geographic_scope_filter", [])
    md_parts.append(
        f"- **CP7 filter applied:** standard={standard_filter}, "
        f"high-confidence={high_filter} (records with `geographic_scope` "
        f"matching ANY filter element pass; `global` passes unconditionally; "
        f"`unknown`/NULL passes standard but fails high-confidence)."
    )
    md_parts.append("")
    md_parts.append(
        "## §7.5 description-format compliance (Talos exports only)"
    )
    md_parts.append("")
    surviving_entries = standard_payload["entries"]
    if surviving_entries:
        md_parts.append(
            "Every surviving entry's `description` field was checked against the "
            f"§7.5 ≤{DESCRIPTION_MAX_CHARS}-char ceiling. Halts at HB36: 0."
        )
        md_parts.append("")
        md_parts.append("| argus_record_id | description | length |")
        md_parts.append("|---|---|---|")
        for e in surviving_entries:
            md_parts.append(
                f"| {e['argus_record_id']} | `{e['description']}` | {len(e['description'])} |"
            )
    else:
        md_parts.append(
            "No surviving entries at HB36. The §7.5 description-format ceiling is "
            "still enforced in the writer (`_format_description` + `_classify_row`); "
            "the gate fires on the first survivor that comes back from a future "
            "Phase-5 reopening."
        )
    md_parts.append("")
    md_parts.append("## CP5 board-class surfaces (open + tracked from MAC-45)")
    md_parts.append("")
    md_parts.append(
        "These items were flagged by the MAC-45 coverage matrix as CP5 board-class "
        "but are NOT halts at HB36 per dispatch. They surface here as the Step-6 "
        "input into the Step-7 CP5 brief (MAC-47):"
    )
    md_parts.append("")
    md_parts.append(
        "1. **Empty-row gap.** 10 of 12 `device_category` enum values have zero "
        "active rows (`imsi_catcher, body_cam, police_radio, drone, gunshot_detect, "
        "hacking_tool, covert_cam, gps_tracker, face_recog, drone_detect`). §8.4 "
        "strict-OUI-level posture binds: every Phase-3-inferred OUI sits in `unknown` "
        "until model-level evidence lands."
    )
    md_parts.append(
        "2. **Empty-col gap.** 6 of 9 `identifier_type` enum values have zero "
        "active rows (`bssid, ssid_exact, ssid_pattern, ble_uuid, ble_service, "
        "device_fingerprint`). The Tier 1/2/3/4 mining pipeline has not yet "
        "promoted into these surfaces."
    )
    md_parts.append(
        "3. **Single-product §2.1 vendor categorization.** Strict §8.4 binds at "
        "HB36 (board-ratified MAC-1 [`613ec532`](/MAC/issues/MAC-1#comment-"
        "613ec532-d8cb-4f0f-a35b-c811e2864d7d) 2026-05-06). The narrow §11 #10 / "
        "Tier 4 read remains open for CP5 surface — quantified row counts per "
        "disposition are upstream input to the eventual decision per Bible §12 "
        "open-question 612-row item."
    )
    md_parts.append(
        "4. **Alias-noise caveat in vendor corroboration.** Common-token aliases "
        "(`Axis`, `Flock`, `Harris`, `Jacobs`, `Parrot`) inflate Phase-3 corroboration "
        "counts in the MAC-45 vendor table via surname / county-name / figurative "
        "usage. CP5 surface; no Step-6 mutation."
    )
    md_parts.append(
        "5. **FCC-staleness caveat.** `fcc_grantees` is frozen at 2021-03-22 (§4.2 "
        "dataset_freeze_date on source_id=7). Post-2020 vendors (Flock Safety, "
        "Skydio etc.) under-count not for vendor-attestation gaps but because the "
        "upstream mirror predates their FCC filings. Phase-4 owns the gap."
    )
    md_parts.append(
        "6. **Mac_range secondary-constraint.** All 8 active `mac_range` rows are "
        "OUI-28/OUI-36 prefixes (>256 entries). They drop to `unknown_category` "
        "first per priority order; they would ALSO hit `oversized_mac_range` if "
        "ever lifted off `unknown` without a §4.4 amendment for OUI-prefix routing "
        "without expansion. Two drop reasons are not exclusive."
    )
    md_parts.append("")
    md_parts.append("## File output reconciliation")
    md_parts.append("")
    md_parts.append(
        "| File | Path | record_count | source_record_count |"
    )
    md_parts.append("|---|---|---|---|")
    md_parts.append(
        f"| Talos standard | `argus/exports/argus_export.json` | "
        f"{standard_meta['record_count']} | {source_count} |"
    )
    md_parts.append(
        f"| Talos high-conf | `argus/exports/argus_export_high_confidence.json` | "
        f"{high_meta['record_count']} | {source_count} |"
    )
    md_parts.append(
        f"| CSV (full canonical) | `argus/exports/argus_export.csv` | "
        f"{source_count} | {source_count} |"
    )
    md_parts.append(
        f"| Coverage matrix (MAC-45) | "
        f"`extraction_outputs/mac45/coverage_matrix.md` | (matrix) | {source_count} |"
    )
    md_parts.append("")
    return "\n".join(md_parts) + "\n"


def run(
    *,
    db_path: Path = DB_PATH,
    exports_dir: Path = EXPORTS_DIR,
    coverage_matrix_report_path: Path = COVERAGE_MATRIX_REPORT_PATH,
    coverage_matrix_md_path: Path = COVERAGE_MATRIX_MD_PATH,
    geographic_scope_filter: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Generate all four Step-6 deliverables and return a summary dict.

    ``geographic_scope_filter`` is the CP7 export-time filter; defaults to
    ``("US",)``. Operators in non-US jurisdictions configure via this param
    (e.g. ``("NL",)``, ``("AU",)``, ``("EU", "GB")``).
    """

    geographic_scope_filter = (
        DEFAULT_GEOGRAPHIC_SCOPE_FILTER
        if geographic_scope_filter is None
        else tuple(geographic_scope_filter)
    )

    if not coverage_matrix_report_path.exists():
        raise Halt(
            f"MAC-45 coverage_matrix_report.json not found at "
            f"{coverage_matrix_report_path} — Step-6 cannot reconcile without it."
        )
    coverage_report_payload = json.loads(
        coverage_matrix_report_path.read_text(encoding="utf-8")
    )
    drop_assignments = _load_drop_assignments(coverage_matrix_report_path)
    matrix_md = coverage_matrix_md_path.read_text(encoding="utf-8")

    exports_dir.mkdir(parents=True, exist_ok=True)
    con = _open_readonly(db_path)
    try:
        rows = _load_active_rows(con)
        schema_version = _load_schema_version(con)
    finally:
        con.close()

    if not rows:
        raise Halt("active identifiers set is empty — refusing to write empty exports.")

    argus_run_id = _derive_argus_run_id(rows)
    exported_at = _utc_now_iso()

    # 1) argus_export.json
    standard_payload, _ = _build_export(
        rows=rows,
        file_label="argus_export.json",
        confidence_threshold=30,
        apply_pi_self_exclude=False,
        schema_version=schema_version,
        argus_run_id=argus_run_id,
        exported_at=exported_at,
        expected_drop_assignments=drop_assignments["argus_export.json"],
        geographic_scope_filter=geographic_scope_filter,
    )
    standard_path = exports_dir / "argus_export.json"
    standard_size = _write_json(standard_path, standard_payload)

    # 2) argus_export_high_confidence.json
    high_payload, _ = _build_export(
        rows=rows,
        file_label="argus_export_high_confidence.json",
        confidence_threshold=70,
        apply_pi_self_exclude=True,
        schema_version=schema_version,
        argus_run_id=argus_run_id,
        exported_at=exported_at,
        expected_drop_assignments=drop_assignments["argus_export_high_confidence.json"],
        geographic_scope_filter=geographic_scope_filter,
        apply_excluded_source_type=True,  # CP19 (§7.5): high-conf-only source_type filter
    )
    high_path = exports_dir / "argus_export_high_confidence.json"
    high_size = _write_json(high_path, high_payload)

    # 3) argus_export.csv
    csv_path = exports_dir / "argus_export.csv"
    csv_size = _write_csv(csv_path, rows, schema_version, exported_at)

    # 4) coverage_report.md
    coverage_md_text = _build_coverage_report_md(
        rows=rows,
        standard_payload=standard_payload,
        high_payload=high_payload,
        schema_version=schema_version,
        argus_run_id=argus_run_id,
        matrix_md=matrix_md,
        coverage_matrix_report=coverage_report_payload,
    )
    coverage_path = exports_dir / "coverage_report.md"
    coverage_path.write_text(coverage_md_text, encoding="utf-8")
    _assert_no_email_pii(coverage_path)
    coverage_size = coverage_path.stat().st_size

    return {
        "argus_run_id": argus_run_id,
        "exported_at": exported_at,
        "schema_version": schema_version,
        "active_row_count": len(rows),
        "outputs": {
            "argus_export.json": {
                "path": str(standard_path),
                "size_bytes": standard_size,
                "record_count": standard_payload["_meta"]["record_count"],
                "dropped_in_export": standard_payload["_meta"]["dropped_in_export"],
            },
            "argus_export_high_confidence.json": {
                "path": str(high_path),
                "size_bytes": high_size,
                "record_count": high_payload["_meta"]["record_count"],
                "dropped_in_export": high_payload["_meta"]["dropped_in_export"],
            },
            "argus_export.csv": {
                "path": str(csv_path),
                "size_bytes": csv_size,
                "record_count": len(rows),
            },
            "coverage_report.md": {
                "path": str(coverage_path),
                "size_bytes": coverage_size,
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--exports-dir", type=Path, default=EXPORTS_DIR)
    parser.add_argument(
        "--coverage-matrix-report",
        type=Path,
        default=COVERAGE_MATRIX_REPORT_PATH,
    )
    parser.add_argument(
        "--coverage-matrix-md",
        type=Path,
        default=COVERAGE_MATRIX_MD_PATH,
    )
    parser.add_argument(
        "--geographic-scope-filter",
        type=str,
        default=",".join(DEFAULT_GEOGRAPHIC_SCOPE_FILTER),
        help=(
            "CP7 export-time filter on identifiers.geographic_scope. "
            "Comma-separated ISO codes (e.g. 'US' or 'NL,AU'). Default: 'US'."
        ),
    )
    args = parser.parse_args()
    geographic_scope_filter = tuple(
        part.strip() for part in args.geographic_scope_filter.split(",") if part.strip()
    )
    if not geographic_scope_filter:
        raise SystemExit(
            "--geographic-scope-filter must contain at least one ISO code."
        )
    summary = run(
        db_path=args.db,
        exports_dir=args.exports_dir,
        coverage_matrix_report_path=args.coverage_matrix_report,
        coverage_matrix_md_path=args.coverage_matrix_md,
        geographic_scope_filter=geographic_scope_filter,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
