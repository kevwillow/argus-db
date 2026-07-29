"""Phase-5 Step-6 coverage matrix orchestrator (MAC-45).

Loads the active ``identifiers`` set (rows with ``superseded_by IS NULL``),
pivots into the §6 Phase 5 #4 coverage matrix shape (rows = device_category
enum values from migration 0001 verbatim, cols = identifier_type enum values
from migration 0001 verbatim, cells carry record count + per-source_type
breakdown + confidence distribution), sweeps the four Phase-3 corpora for
per-vendor manufacturer-name corroboration counts (gap-analysis only — not
a confidence-uplift channel per §11 #8), and pre-tallies the §9 item 9
"Dropped from Talos export" bins for the Step-7 export worker.

Authority chain
---------------
- Bible §6 Phase 5 #4 — coverage matrix contract.
- Bible §9 item 9 — drop-tally reconciliation contract.
- Bible §7.5 — Talos export `_meta.dropped_in_export` block this pre-tally
  feeds.
- Bible §4.4 — Talos identifier_type → pattern_type mapping (drives
  ``ssid_pattern`` / ``device_fingerprint`` / oversized ``mac_range`` drops).
- Bible §8.2 — source-type confidence ceilings (annotation reference only).
- Bible §8.4 + §11 #12 — Pi self-exclude list.
- Bible §11 #13 — `device_category='unknown'` Talos-export ban.
- Bible §11 #14 — `source_type='procurement'` Talos-export ban.
- MAC-45 dispatch (HB35).

Read-only contract
------------------
This module performs ZERO writes against ``identifiers``. The §8.3 dedup
pass is closed at Step 5 (MAC-42); Step 6 reads. The Phase-3 corpora reads
are ``LIKE`` aggregate counts only — no mutations to staging tables either.

Stop-the-line clauses (raised as :class:`HaltCondition`)
--------------------------------------------------------
- ``§11_hard_rule_trip`` — defensive guard (no expected trips at HB35).
- ``new_§8.4_fp_class`` — a row that should be Talos-banned by an existing
  rule but isn't surfaced by the bin assignment (defense-in-depth check).
- ``unknown_source_type`` — a row whose ``source_type`` falls outside the
  §8.2 enum (would surface §4.2 schema drift).

When a halt fires, the orchestrator raises a non-zero exit; no DB writes
happen regardless because this module never writes.

Key shape mismatches the matrix surfaces (CP5 board-class gap-analysis;
NOT halts per dispatch "Coverage matrix shape gap" clause)
-----------------------------------------------------------------------
- 12 of the 12 ``device_category`` enum values are unrepresented except for
  ``unknown`` (62) and ``alpr`` (1) at HB35 — the §8.4 strict OUI-level
  posture binds.
- The 8 ``mac_range`` rows are all OUI-28 / OUI-36 prefixes (>256 entries
  each), so all 8 drop to ``oversized_mac_range`` per §4.4.
- The dispatch §6.1 column list mentions ``ssid`` / ``fcc_id`` which are
  not in the migration-0001 CHECK; the matrix uses the 9 verbatim enum
  values from migration 0001.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parents[1] / "argus.db"

VALIDATOR_AGENT_ID = "da137694-2efe-4589-8150-828dcab881fb"

# §4.1 + migration 0001 CHECK constraint enums — verbatim, in declaration order.
DEVICE_CATEGORIES: tuple[str, ...] = (
    "alpr",
    "imsi_catcher",
    "body_cam",
    "police_radio",
    "drone",
    "gunshot_detect",
    "hacking_tool",
    "covert_cam",
    "gps_tracker",
    "face_recog",
    "drone_detect",
    "unknown",
)

IDENTIFIER_TYPES: tuple[str, ...] = (
    "oui",
    "mac",
    "mac_range",
    "bssid",
    "ssid_exact",
    "ssid_pattern",
    "ble_uuid",
    "ble_service",
    "device_fingerprint",
    # CP13 (migration 0009) — Wave G structural fidelity. All three are
    # analytical-only (DROPPED-class per §4.4); they never reach the Lynceus
    # pattern table but are carried in the canonical DB.
    "ble_local_name",
    "ble_characteristic",
    "product_family_codename",
    # CP16 (§4.4) — CP14 identifier_type cluster (migrations 0011/0013/0014).
    # 3 MAP entries (new pattern_types) + 12 DROPPED-with-reason entries.
    # Coverage_matrix lag from sibling commit a4bc7b9 (export_lynceus.py CP16
    # patch) caught by MAC-92 Wave-B Phase-B dry-run when first CP16 rows
    # landed via Phase-A promotion. Same architectural-absorption gap class
    # as commit a4bc7b9's Phase-3-claim correction.
    "ble_manufacturer_id",          # MAP
    "drone_id_prefix",              # MAP
    "wifi_aware_service_name",      # MAP
    "icao_24bit_address",           # DROPPED
    "rf_channel",                   # DROPPED
    "burst_cadence_ms",             # DROPPED
    "bandwidth_mhz",                # DROPPED
    "device_class_id",              # DROPPED
    "rf_burst_duration",            # DROPPED
    "rf_protocol_constant",         # DROPPED
    "wifi_ie_element_id",           # DROPPED
    "bluetooth_le_pdu_type",        # DROPPED
    "wifi_frame_control_subtype",   # DROPPED
    "wifi_nan_param_signature",     # DROPPED
    "alpr_model",                   # DROPPED
)


# CP16 (§4.4) — DROPPED-with-reason lookup mirroring export_lynceus.py
# DROPPED_REASONS dict. Identifier_type → bin label (one-to-one). Used by
# `_assign_drop_bin` so coverage_matrix.py and export_lynceus.py classify
# CP14-cluster rows identically — the canonical-chain reconciliation gate
# in `db/validation/export_lynceus.py::_reconcile` relies on this parity.
DROPPED_REASONS: dict[str, str] = {
    "icao_24bit_address": "icao_24bit_address",
    "rf_channel": "rf_channel",
    "burst_cadence_ms": "burst_cadence_ms",
    "bandwidth_mhz": "bandwidth_mhz",
    "device_class_id": "device_class_id",
    "rf_burst_duration": "rf_burst_duration",
    "rf_protocol_constant": "rf_protocol_constant",
    "wifi_ie_element_id": "wifi_ie_element_id",
    "bluetooth_le_pdu_type": "bluetooth_le_pdu_type",
    "wifi_frame_control_subtype": "wifi_frame_control_subtype",
    "wifi_nan_param_signature": "wifi_nan_param_signature",
    "alpr_model": "alpr_model",
    # Migration 0018 / SAR-13 §S.3 — 14 net-new identifier_types added at
    # MAC-109. Default DROPPED-class pending board ratification of §4.4 MAP
    # additions (MAC-110 §E architectural firsts). Mirrors
    # export_lynceus.py::DROPPED_REASONS verbatim — the reconcile gate at
    # export_lynceus.py::_reconcile requires byte-identical parity.
    "ble_protocol_byte_table": "ble_protocol_byte_table",
    # `ble_service_uuid` removed at MAC-359 (absorbed MAC-388) — now a §4.4 MAP
    # survivor (→ ble_uuid, CP21 alias-collapse). SAR-18 parity: export_lynceus.py
    # IDENTIFIER_TYPE_TO_PATTERN_TYPE carries the MAP entry; neither module keeps
    # a ble_service_uuid drop bin. Bins here auto-derive from
    # DROPPED_REASONS.values(), so removal is sufficient.
    # `ble_company_id` removed at MAC-360 / CP47 (absorbed CP21 §4.4 MAP →
    # ble_manufacturer_id), symmetric to MAC-359's ble_service_uuid. SAR-18 parity:
    # export_lynceus.py IDENTIFIER_TYPE_TO_PATTERN_TYPE carries the MAP entry;
    # neither module keeps a ble_company_id drop bin. Bins here auto-derive from
    # DROPPED_REASONS.values(), so removal is sufficient.
    "frequency_band": "frequency_band",
    "ble_protocol_byte": "ble_protocol_byte",
    "operator_profile": "operator_profile",
    "x509_cert_sha256_prefix": "x509_cert_sha256_prefix",
    "ble_adv_interval": "ble_adv_interval",
    "ble_payload_offset": "ble_payload_offset",
    "firmware_sha256_hash": "firmware_sha256_hash",
    "network_endpoint": "network_endpoint",
    "firmware_image_variant": "firmware_image_variant",
    "qualcomm_chip_format_id": "qualcomm_chip_format_id",
    "firmware_branded_string": "firmware_branded_string",
    # MAC-117 / migration 0019 — round-2 vocab extension (7 net-new identifier_types
    # per SAR-13 §S.3 routing slate (A)). Default DROPPED-class pending §4.4
    # MAP ratification at next CP21 round. Mirrors export_lynceus.py::
    # DROPPED_REASONS verbatim — the reconcile gate at
    # export_lynceus.py::_reconcile requires byte-identical parity.
    "asdstan_message_type": "asdstan_message_type",
    "asdstan_enum_value": "asdstan_enum_value",
    "dji_protocol_struct_format": "dji_protocol_struct_format",
    "gpt_partition_uuid": "gpt_partition_uuid",
    "chipset_codename": "chipset_codename",
    "firmware_build_string": "firmware_build_string",
    "firmware_build_uuid": "firmware_build_uuid",
    # MAC-181 / migration 0023 — CP28(c) Wave H desktop-axis vendor-registered
    # non-BLE cluster DROPPED cases (2 entries). The sibling MAP case
    # (`vendor_document_uuid_cloud_reference`) lives in
    # export_lynceus.py::IDENTIFIER_TYPE_TO_PATTERN_TYPE per CP28(c) §4.4 posture.
    # Mirrors export_lynceus.py::DROPPED_REASONS verbatim — the reconcile
    # gate at export_lynceus.py::_reconcile requires byte-identical parity.
    "windows_installer_productcode_vendor_registered": "windows_installer_productcode_vendor_registered",
    "windows_com_clsid_vendor_registered": "windows_com_clsid_vendor_registered",
    # CP29 (migration 0024) — Wave I/I.5/I.6/I.7 vendor cloud-infrastructure
    # hostname corpus (3 net-new identifier_types). Default DROPPED-class
    # pending §4.4 MAP ratification at next CP21 round. Mirrors
    # export_lynceus.py::DROPPED_REASONS verbatim.
    "vendor_controlled_hostname": "vendor_controlled_hostname",
    "vendor_cloud_endpoint_url": "vendor_cloud_endpoint_url",
    "vendor_controlled_hostname_deprecated": "vendor_controlled_hostname_deprecated",
    # CP31 (migration 0025) — FCC EAS identifier-type cluster (2 net-new
    # identifier_types). Default DROPPED-class. Mirrors export_lynceus.py::
    # DROPPED_REASONS verbatim.
    "fcc_grantee_code": "fcc_grantee_code",
    "equipment_class_code": "equipment_class_code",
    # CP35 (mig-0028 / MAC-255) — NDPP §4.4 ratified DROP (option (b)). CP42 §2
    # (MAC-300, 2026-06-03) supersedes CP35 §215's descriptive-bin_label
    # sub-decision: DROPPED_REASONS is universally identity-keyed
    # (`DROPPED_REASONS[k] == k`). SAR-18 parity gate continues to require this
    # entry mirror export_lynceus.py::DROPPED_REASONS verbatim. The
    # `_compute_drop_tally` cp16-bin auto-init loop and `_drop_tally_to_dict`
    # `bins.update(t.cp16_dropped)` handle new bins automatically; no other
    # touch points in this module.
    "network_discovery_protocol_pattern": "network_discovery_protocol_pattern",
    # CP42 §1 (MAC-300, 2026-06-03) — imei_tac §4.4 consumer-side DROP
    # (analogue to CP35 NDPP). SAR-18 parity: this entry mirrors
    # export_lynceus.py::DROPPED_REASONS verbatim.
    "imei_tac": "imei_tac",
}

# §8.2 confidence-band ceilings — annotation reference only (no mutations).
SOURCE_TYPE_CEILINGS: dict[str, int] = {
    "official": 100,
    "regulatory": 95,
    "manufacturer_doc": 90,
    "procurement": 85,
    "academic": 90,
    "foia": 85,
    # CP36-extension (MAC-256) — judicial_filing inherits foia proxy-band
    # ceiling per §11 #8 invariant (CP36 confidence-preservation contract).
    "judicial_filing": 85,
    "crowdsourced": 75,
    "inferred": 70,
    # CP12 (bible §8.2) — vendor companion app static-analysis extract.
    # Outer band 60–95; sub-banded per identifier class (§8.2 table).
    "manufacturer_app": 95,
    # CP15 (bible §8.2) — authoritative numerical-allocation registries
    # (IEEE OUI, Bluetooth SIG company IDs, FAA RID, IANA). Single-source
    # ceiling 85; up to 95 with cross-band corroboration (§8.2 formula).
    "primary_registry": 85,
}

# §8.4 / §11 #12 Pi self-exclude OUIs.
PI_SELF_EXCLUDE_OUIS: frozenset[str] = frozenset(
    {"b8:27:eb", "dc:a6:32", "e4:5f:01", "28:cd:c1"}
)

# CP19 (§7.5) — source_type values excluded from the high-confidence Lynceus
# export regardless of confidence value. Single-source `inferred` /
# `crowdsourced` rows still satisfy CP18's ≥70 confidence floor (75 / 70
# ceilings per §8.2) but lack a §8.3 cross-band corroboration anchor, so
# they are not safe to publish on the high-confidence operational feed.
# The standard export (≥30 floor) retains them — they remain useful for
# wider-net rich-import consumers.
EXCLUDED_SOURCE_TYPES: frozenset[str] = frozenset({"inferred", "crowdsourced"})

# §4.4 generic/reserved BLE-UUID export suppression (MAC-359, CEO Ruling 3;
# absorbed at MAC-388). MUST mirror
# `export_lynceus.py::GENERIC_RESERVED_UUID_SUPPRESS` byte-for-byte:
# `_assign_drop_bin` and `export_lynceus.py::_classify_row` both bin a matching
# row as `generic_reserved_uuid` at the identical priority (after the §4.4
# type-drops, before the confidence/source gates), so `_reconcile`'s per-row
# map-vs-writer cross-check agrees. Do NOT update one module without the other.
GENERIC_RESERVED_UUID_SUPPRESS: frozenset[str] = frozenset(
    {"0000ffff-0000-1000-8000-00805f9b34fb"}
)

# CP39 §7.5 carve-out — must mirror `export_lynceus.py` constant of the same
# name. The two modules cross-check at `_reconcile`-time and halt on any
# divergence; do NOT update one without updating the other.
CP39_FLOCK_HUNT_CARVEOUT_URL_PATTERNS: tuple[str, ...] = (
    "deflock.me",
    "MaxwellDPS/Flock-You",
    "colonelpanichacks/flock-you",
    "GainSec/Flock-Safety-Trap",
    "GainSec/anti-crime-ecosystem-research",
    "GainSec/flock-safety-falcon",
    "DeflockJoplin/flock-you",
    "EthanThePhoenix38/flock-you",
    "FoggedLens/deflock-app",
    "NSM-Barii",
    "flock-back",
)


def _cp39_flock_hunt_carveout(source_url: str | None) -> bool:
    """Return True iff the row qualifies for the CP39 §7.5 carve-out."""
    if not source_url:
        return False
    return any(p in source_url for p in CP39_FLOCK_HUNT_CARVEOUT_URL_PATTERNS)

# §6.2 Phase-3 corroboration thresholds (dispatch verbatim).
HIGH_CORROBORATION_GRANTEES_FLOOR = 10
HIGH_CORROBORATION_PROCUREMENT_FLOOR = 10

# §4.4 mac_range expansion ceiling.
MAC_RANGE_EXPANSION_CEILING = 256

# MAC-535 §6.2 alias-tokenization defense (Finding 1). The naive comma-split of
# manufacturers.aliases yields corporate-suffix tokens ("Ltd.", "Inc.", "LLC",
# "THE", "Co.") that match a huge share of the FCC corpus (17.3% / 10.3% / 4.8%
# / 1.1% / 4.8% respectively against the 50,153-row fcc_grantees corpus),
# inflating per-vendor corroboration counts for 17 active vendors. The fix is a
# 3-layer defense:
#   1. Quote-aware splitting — current data does not consistently wrap comma-
#      containing values, but the discipline is structural (RFC-4180-lite):
#      a token begins after `, ` and ends at the next `, ` OR a `"`-wrapped
#      phrase. If future aliases ARE quoted, the parser handles them correctly.
#   2. Corporate-suffix stop-list — drop known-bogus tokens regardless of how
#      they were produced (defense-in-depth for unquoted-comma values that
#      slip through layer 1). Case-insensitive; matches the cto_ratification.md
#      Finding 2 catalogue verbatim.
#   3. Min-length floor — drop tokens of length ≤3 ("a", "ab", "THE" already
#      caught by stop-list; protects against future short-token false positives).
# See operator_review/MAC-535/tokenization_analysis.md for the full design +
# before/after corroboration table.
_CORP_SUFFIX_STOPLIST: frozenset[str] = frozenset({
    "ltd", "ltd.", "inc", "inc.", "llc", "co.", "co", "the",
})
_ALIAS_TOKEN_MIN_LEN = 4

# §7.5 Talos export confidence thresholds.
EXPORT_STANDARD_FLOOR = 30
EXPORT_HIGH_CONFIDENCE_FLOOR = 70


# ────────────────────────────────────────────────────────────────────────────
# Dataclasses
# ────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class HaltCondition:
    kind: str
    detail: str
    row_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class ActiveRow:
    id: int
    identifier: str
    identifier_type: str
    device_category: str
    manufacturer: Optional[str]
    source_type: str
    confidence: int
    # CP39 (v1.6.2.1) — source_url is required to evaluate the §7.5 floor
    # carve-out for named Flock-hunt project sources. Kept Optional only for
    # defensive backward-compat; the loader always populates it.
    source_url: Optional[str] = None


@dataclass(frozen=True)
class CellStats:
    """Per (device_category, identifier_type) cell."""

    device_category: str
    identifier_type: str
    n: int
    n_by_source_type: dict[str, int]
    min_conf: Optional[int]
    max_conf: Optional[int]
    median_conf: Optional[float]
    row_ids: tuple[int, ...]


@dataclass(frozen=True)
class VendorCorroboration:
    canonical_name: str
    aliases_used: tuple[str, ...]
    fcc_grantees_count: int
    procurement_records_count: int
    deployment_observations_count: int
    council_minutes_matters_count: int
    high_corroboration: bool
    active_identifier_count: int


@dataclass(frozen=True)
class DropBinTally:
    """§9 item 9 drop bins for one Lynceus export file.

    Each row is assigned to AT MOST one bin (priority order: procurement_only
    > unknown_category > device_fingerprint > ssid_pattern > ble_local_name
    > ble_characteristic > product_family_codename > oversized_mac_range >
    {CP16 12 DROPPED-class types in DROPPED_REASONS} > self_exclude_oui >
    below_confidence_threshold > excluded_source_type). Survivors → eligible
    for export.
    """

    file_label: str
    confidence_floor: int
    drop_pi_self_exclude: bool
    unknown_category: int
    # §4.4 (MAC-359; absorbed MAC-388) — generic/reserved BLE-UUID value
    # suppression bin.
    generic_reserved_uuid: int
    procurement_only: int
    self_exclude_oui: int
    below_confidence_threshold: int
    oversized_mac_range: int
    ssid_pattern: int
    # CP51 (§4.4, MAC-517) — ssid_pattern rows whose converted substring is
    # FP-held (generic/short stem). Mirrors export_lynceus.py's bin of the same
    # name so the per-row drop_assignments map reconciles with the writer.
    ssid_pattern_fp_hold: int
    device_fingerprint: int
    # CP13 (§4.4) — Wave G analytical-only types.
    ble_local_name: int
    ble_characteristic: int
    product_family_codename: int
    # CP16 (§4.4) — CP14 identifier_type cluster DROPPED-class types.
    # Bin keys mirror DROPPED_REASONS verbatim so `_drop_tally_to_dict`
    # produces a `bins` dict that reconciles 1:1 against export_lynceus.py's
    # `dropped_in_export` block.
    cp16_dropped: dict[str, int]
    # CP19 (§7.5) — source_type exclusion for the high-conf export (sits below
    # below_confidence_threshold in priority order so a row with
    # source_type='inferred'/'crowdsourced' AND conf<floor attributes the drop
    # to the more specific confidence reason).
    excluded_source_type: int
    survivors: int
    drop_assignments: dict[int, str]  # row_id → bin name (only dropped rows)


@dataclass(frozen=True)
class CoverageMatrixReport:
    pre_active_count: int
    cells: tuple[CellStats, ...]
    vendor_corroboration: tuple[VendorCorroboration, ...]
    drop_tally_standard: DropBinTally
    drop_tally_high_confidence: DropBinTally
    halts: tuple[HaltCondition, ...] = field(default_factory=tuple)


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")  # §11 #6 attestation: no writes possible
    return conn


def _load_active_rows(conn: sqlite3.Connection) -> list[ActiveRow]:
    cur = conn.execute(
        "SELECT id, identifier, identifier_type, device_category, "
        "manufacturer, source_type, confidence, source_url "
        "FROM identifiers WHERE superseded_by IS NULL ORDER BY id"
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
                source_type=r["source_type"],
                confidence=r["confidence"] if r["confidence"] is not None else 0,
                source_url=r["source_url"],
            )
        )
    return rows


def _compute_cells(rows: list[ActiveRow]) -> list[CellStats]:
    """Pivot active rows into (device_category, identifier_type) cells."""
    by_cell: dict[tuple[str, str], list[ActiveRow]] = {}
    for r in rows:
        key = (r.device_category, r.identifier_type)
        by_cell.setdefault(key, []).append(r)

    cells: list[CellStats] = []
    # Dense matrix: every (device_category, identifier_type) combo, even if 0.
    for dc in DEVICE_CATEGORIES:
        for it in IDENTIFIER_TYPES:
            members = by_cell.get((dc, it), [])
            if members:
                confs = [m.confidence for m in members]
                src_counts: dict[str, int] = {}
                for m in members:
                    src_counts[m.source_type] = src_counts.get(m.source_type, 0) + 1
                cells.append(
                    CellStats(
                        device_category=dc,
                        identifier_type=it,
                        n=len(members),
                        n_by_source_type=dict(sorted(src_counts.items())),
                        min_conf=min(confs),
                        max_conf=max(confs),
                        median_conf=statistics.median(confs),
                        row_ids=tuple(m.id for m in members),
                    )
                )
            else:
                cells.append(
                    CellStats(
                        device_category=dc,
                        identifier_type=it,
                        n=0,
                        n_by_source_type={},
                        min_conf=None,
                        max_conf=None,
                        median_conf=None,
                        row_ids=(),
                    )
                )
    return cells


def _split_alias_blob(blob: str) -> list[str]:
    """MAC-535 §6.2 tokenization layer-1: quote-aware split.

    The aliases blob is comma-separated. Two value shapes coexist in the live
    data:

    * Bare values: ``Hangzhou Hikvision Digital Technology Co., Ltd.``
      (no surrounding quotes; the embedded comma is unintentional artifact
      of manual alias construction — splits into 2 bogus tokens).
    * Quoted values (RFC-4180-lite): ``"Hangzhou Hikvision Digital Technology
      Co., Ltd."`` — the parser treats the quoted phrase as ONE token.

    This helper is a thin re-export of the canonical ``db.alias_parser.
    split_aliases`` so the RFC-4180-lite contract has exactly one
    implementation. Layer-2/3 (stop-list + min-length) defense is applied
    by ``_alias_tokens_for_vendor`` via ``_is_bogus_token`` below.
    """
    from db.alias_parser import split_aliases as _split_aliases_canonical

    return _split_aliases_canonical(blob)


def _is_bogus_token(tok: str) -> bool:
    """MAC-535 §6.2 tokenization layer-2/3: stop-list + min-length.

    Re-exported from the canonical ``db.alias_parser`` module so the
    bogus-token catalogue (verbatim from cto_ratification.md §Finding 2)
    has exactly one source of truth.
    """
    from db.alias_parser import is_bogus_token as _is_bogus_token_canonical

    return _is_bogus_token_canonical(tok)


def _alias_tokens_for_vendor(
    conn: sqlite3.Connection, canonical: str
) -> list[str]:
    row = conn.execute(
        "SELECT canonical_name, aliases FROM manufacturers WHERE canonical_name = ?",
        (canonical,),
    ).fetchone()
    if row is None:
        return [canonical]
    toks: list[str] = [row["canonical_name"]]
    if row["aliases"]:
        from db.alias_parser import filter_bogus_tokens as _filter_bogus_canonical

        toks += _filter_bogus_canonical(_split_alias_blob(row["aliases"]))
    return toks


def _or_like_count(
    conn: sqlite3.Connection, table: str, column: str, tokens: list[str]
) -> int:
    if not tokens:
        return 0
    where = " OR ".join([f"{column} LIKE ?"] * len(tokens))
    args = [f"%{t}%" for t in tokens]
    cur = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}", args)
    return cur.fetchone()[0]


def _compute_vendor_corroboration(
    conn: sqlite3.Connection, rows: list[ActiveRow]
) -> list[VendorCorroboration]:
    """Sweep four Phase-3 corpora for per-vendor name-corroboration counts."""
    by_vendor: dict[str, list[ActiveRow]] = {}
    for r in rows:
        if r.manufacturer:
            by_vendor.setdefault(r.manufacturer, []).append(r)

    out: list[VendorCorroboration] = []
    for canonical in sorted(by_vendor):
        toks = _alias_tokens_for_vendor(conn, canonical)
        fcc = _or_like_count(conn, "fcc_grantees", "grantee_name", toks)
        proc = _or_like_count(
            conn, "procurement_records", "vendor_canonical_name", toks
        )
        depl = _or_like_count(
            conn, "deployment_observations", "vendor_raw", toks
        )
        cmm = _or_like_count(
            conn, "council_minutes_matters", "vendor_canonical_name", toks
        )
        high = (
            fcc >= HIGH_CORROBORATION_GRANTEES_FLOOR
            and proc >= HIGH_CORROBORATION_PROCUREMENT_FLOOR
        )
        out.append(
            VendorCorroboration(
                canonical_name=canonical,
                aliases_used=tuple(toks),
                fcc_grantees_count=fcc,
                procurement_records_count=proc,
                deployment_observations_count=depl,
                council_minutes_matters_count=cmm,
                high_corroboration=high,
                active_identifier_count=len(by_vendor[canonical]),
            )
        )
    return out


def mac_range_size(identifier: str) -> int:
    """Return 2^remaining-bits for a colon-separated hex prefix.

    A `mac_range` identifier is a hex-prefix like ``10:63:a3:1`` (28-bit OUI-M)
    or ``00:50:c2:2a:5`` (36-bit OUI-S). The expansion size is ``2^(48-nbits)``
    where ``nbits = 4 * (count of hex chars without colons)``.
    """
    hex_chars = identifier.replace(":", "")
    nbits = len(hex_chars) * 4
    if nbits >= 48:
        return 1
    return 1 << (48 - nbits)


def matches_pi_self_exclude(identifier: str, identifier_type: str) -> bool:
    """Return True if identifier falls in the §8.4 Pi self-exclude OUI family."""
    ident = identifier.lower()
    if identifier_type == "oui":
        return ident in PI_SELF_EXCLUDE_OUIS
    if identifier_type in ("mac", "bssid"):
        prefix = ":".join(ident.split(":")[:3])
        return prefix in PI_SELF_EXCLUDE_OUIS
    if identifier_type == "mac_range":
        prefix = ":".join(ident.split(":")[:3])
        return prefix in PI_SELF_EXCLUDE_OUIS
    return False


# CP50 (§4.4, MAC-420) — ble_local_name literal-vs-template predicate. MUST be
# byte-identical to export_lynceus.py::_ble_local_name_is_template (the
# `db/validation/export_lynceus.py::_reconcile` cross-check halts on divergence).
_BLE_LOCAL_NAME_TEMPLATE_CHARS = "[]()?*+|<>%"


def _ble_local_name_is_template(value: str) -> bool:
    return any(ch in value for ch in _BLE_LOCAL_NAME_TEMPLATE_CHARS)


# CP51 (§4.4, MAC-517) — ssid_pattern → Lynceus 0.9.2 substring conversion.
# MUST be byte-identical to
# db/validation/export_lynceus.py::_ssid_pattern_to_substring (the
# export_lynceus.py `_reconcile` map-vs-writer cross-check halts on any
# divergence). coverage_matrix.py only needs the is-None (FP-hold) decision to
# assign the `ssid_pattern_fp_hold` drop bin; the exporter additionally emits
# the returned substrings. See the exporter's module comment for the rule.
_SSID_STEM_METACHARS = set(".^$*+?()[]{}|\\%")
_SSID_PATTERN_FP_HOLD_STEMS: frozenset[str] = frozenset({"lpr"})
_SSID_STEM_MIN_LEN = 3


def _ssid_pattern_to_substring(value: str) -> list[str] | None:
    """Convert an ``ssid_pattern`` value to Lynceus-0.9.2 substring(s).

    Returns the list of case-insensitive substrings to emit, or ``None`` when
    the row is FP-held and must drop to the ``ssid_pattern_fp_hold`` bin.
    """

    s = value.strip()
    if s.startswith("(?i)"):
        s = s[4:]
    if s.startswith("^"):
        s = s[1:]
    branches: list[str] | None = None
    if s.startswith("("):
        depth = 0
        close = None
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    close = i
                    break
        if close is not None:
            inner = s[1:close]
            if inner and not inner.startswith("?") and "|" in inner:
                branches = inner.split("|")
    if branches is None:
        branches = [s]
    out: list[str] = []
    for branch in branches:
        stem_chars: list[str] = []
        for ch in branch:
            if ch in _SSID_STEM_METACHARS:
                break
            stem_chars.append(ch)
        stem = "".join(stem_chars).strip()
        if len(stem) < _SSID_STEM_MIN_LEN or stem.lower() in _SSID_PATTERN_FP_HOLD_STEMS:
            return None
        out.append(stem)
    return out or None


def _assign_drop_bin(
    row: ActiveRow,
    confidence_floor: int,
    drop_pi_self_exclude: bool,
    drop_source_types: frozenset[str] = frozenset(),
) -> Optional[str]:
    """Return the drop-bin name a row falls into, or None if it survives.

    Priority order (a row can only drop for one reason):
      1. procurement_only            (§11 #14)
      2. unknown_category            (§11 #13)
      3. device_fingerprint          (§4.4)
      4. ssid_pattern                (§4.4)
      5. ble_local_name              (§4.4 CP13)
      6. ble_characteristic          (§4.4 CP13)
      7. product_family_codename     (§4.4 CP13)
      8. oversized_mac_range         (§4.4)
     8a. CP16 DROPPED_REASONS        (§4.4 CP16 — 12 analytical-only types)
      9. self_exclude_oui            (§8.4 / §11 #12 — high-conf file only)
     10. below_confidence_threshold  (§7.5)
     11. excluded_source_type        (§7.5 CP19 — high-conf file only; sits
                                      AFTER below_confidence_threshold so a
                                      crowdsourced/inferred row with conf<70
                                      attributes the drop to the more specific
                                      confidence reason; the CP19 filter only
                                      catches rows that would have survived
                                      every prior gate)
    """
    if row.source_type == "procurement":
        return "procurement_only"
    if row.device_category == "unknown":
        return "unknown_category"
    if row.identifier_type == "device_fingerprint":
        return "device_fingerprint"
    # §4.4 CP51 (MAC-517) — ssid_pattern MAP → Lynceus 0.9.2 substring. FP-held
    # rows (None conversion) drop to `ssid_pattern_fp_hold`; convertible rows
    # survive this gate and flow to the confidence / source gates below (mirror
    # of export_lynceus.py::_classify_row — its `_reconcile` cross-check halts on
    # any divergence).
    if row.identifier_type == "ssid_pattern":
        if _ssid_pattern_to_substring(row.identifier) is None:
            return "ssid_pattern_fp_hold"
    # CP13 / CP50 (§4.4, MAC-420) — ble_local_name: LITERAL advertised names
    # survive (MAP → feed, exact GAP local-name match); TEMPLATED / regex forms
    # drop to the ble_local_name bin (Lynceus v0.3 has no template matcher).
    # Mirror of export_lynceus.py::_classify_row — the `_reconcile` map-vs-writer
    # cross-check in export_lynceus.py halts on any divergence.
    if row.identifier_type == "ble_local_name" and _ble_local_name_is_template(
        row.identifier
    ):
        return "ble_local_name"
    # ble_characteristic + product_family_codename stay full-DROPPED (CP13).
    if row.identifier_type == "ble_characteristic":
        return "ble_characteristic"
    if row.identifier_type == "product_family_codename":
        return "product_family_codename"
    # SAR-18 (MAC-232 Step 9 board ratification 2026-05-22): `oversized_mac_range`
    # predicate is UNCONDITIONAL on mac_range rows. Matches
    # `db/validation/export_lynceus.py::_classify_row` lines 530-537. Previous
    # `> MAC_RANGE_EXPANSION_CEILING` strict-greater-than predicate was latent-
    # divergent from the exporter since v1.4.0; unmasked by MAC-232 Step 6 G-B
    # retroactive recat lifting id=9404 (Eagle Eye Networks, `64:33:b5:4/28`,
    # size=256) out of `unknown_category` into `cctv_camera`. Lynceus v0.3 has
    # no mac_range expansion logic; until that feature ships (CP34 §4.4 slot),
    # both classifiers MUST drop ALL mac_range rows unconditionally.
    if row.identifier_type == "mac_range":
        return "oversized_mac_range"
    # CP16 (§4.4) — CP14-cluster DROPPED-class types. Branch placement mirrors
    # `db/validation/export_lynceus.py::_classify_row` (after the 6 legacy
    # DROPPED branches, before the Pi self-exclude branch). DROPPED_REASONS
    # values are the bin labels.
    if row.identifier_type in DROPPED_REASONS:
        return DROPPED_REASONS[row.identifier_type]
    # §4.4 (MAC-359 CEO Ruling 3; absorbed MAC-388) — generic/reserved BLE-UUID
    # value suppression. Mirrors `export_lynceus.py::_classify_row` at the
    # identical priority (after the §4.4 type-drops, before the Pi self-exclude /
    # confidence gates) so the per-row drop_assignments map reconciles with the
    # writer.
    if row.identifier in GENERIC_RESERVED_UUID_SUPPRESS:
        return "generic_reserved_uuid"
    if drop_pi_self_exclude and matches_pi_self_exclude(
        row.identifier, row.identifier_type
    ):
        return "self_exclude_oui"
    if row.confidence < confidence_floor:
        return "below_confidence_threshold"
    # CP19 (§7.5) — high-conf-only source_type exclusion. `drop_source_types`
    # is empty for the standard export; it carries `EXCLUDED_SOURCE_TYPES`
    # ({'inferred', 'crowdsourced'}) for the high-conf export. A row reaching
    # this gate has passed every prior static filter; the bin captures the
    # CP19-specific drop attribution.
    if drop_source_types and row.source_type in drop_source_types:
        # CP39 §7.5 carve-out — see CP39_FLOCK_HUNT_CARVEOUT_URL_PATTERNS.
        if not _cp39_flock_hunt_carveout(row.source_url):
            return "excluded_source_type"
    return None


def _compute_drop_tally(
    rows: list[ActiveRow],
    *,
    file_label: str,
    confidence_floor: int,
    drop_pi_self_exclude: bool,
    drop_source_types: frozenset[str] = frozenset(),
) -> DropBinTally:
    bins: dict[str, int] = {
        "unknown_category": 0,
        # §4.4 (MAC-359; absorbed MAC-388) — generic/reserved BLE-UUID bin.
        "generic_reserved_uuid": 0,
        "procurement_only": 0,
        "self_exclude_oui": 0,
        "below_confidence_threshold": 0,
        "oversized_mac_range": 0,
        "ssid_pattern": 0,
        # CP51 (§4.4, MAC-517) — ssid_pattern FP-hold bin.
        "ssid_pattern_fp_hold": 0,
        "device_fingerprint": 0,
        # CP13 (§4.4) — Wave G analytical-only types.
        "ble_local_name": 0,
        "ble_characteristic": 0,
        "product_family_codename": 0,
        # CP19 (§7.5) — source_type exclusion bin (high-conf file only;
        # zero-init in both files so the bins dict shape is parallel and
        # reconciliation arithmetic carries through with no NULL-handling).
        "excluded_source_type": 0,
    }
    # CP16 (§4.4) — CP14 identifier_type cluster DROPPED-class types
    # initialized to zero (per-bin presence required for the bins-dict
    # increment in the loop below + reconciliation against export_lynceus.py).
    for cp16_bin in DROPPED_REASONS.values():
        bins[cp16_bin] = 0
    drop_assignments: dict[int, str] = {}
    survivors = 0
    for r in rows:
        bin_name = _assign_drop_bin(
            r,
            confidence_floor,
            drop_pi_self_exclude=drop_pi_self_exclude,
            drop_source_types=drop_source_types,
        )
        if bin_name is None:
            survivors += 1
        else:
            bins[bin_name] += 1
            drop_assignments[r.id] = bin_name
    return DropBinTally(
        file_label=file_label,
        confidence_floor=confidence_floor,
        drop_pi_self_exclude=drop_pi_self_exclude,
        unknown_category=bins["unknown_category"],
        generic_reserved_uuid=bins["generic_reserved_uuid"],
        procurement_only=bins["procurement_only"],
        self_exclude_oui=bins["self_exclude_oui"],
        below_confidence_threshold=bins["below_confidence_threshold"],
        oversized_mac_range=bins["oversized_mac_range"],
        ssid_pattern=bins["ssid_pattern"],
        ssid_pattern_fp_hold=bins["ssid_pattern_fp_hold"],
        device_fingerprint=bins["device_fingerprint"],
        ble_local_name=bins["ble_local_name"],
        ble_characteristic=bins["ble_characteristic"],
        product_family_codename=bins["product_family_codename"],
        cp16_dropped={k: bins[k] for k in DROPPED_REASONS.values()},
        excluded_source_type=bins["excluded_source_type"],
        survivors=survivors,
        drop_assignments=drop_assignments,
    )


def _check_halts(
    rows: list[ActiveRow],
    standard: DropBinTally,
    high_conf: DropBinTally,
) -> list[HaltCondition]:
    halts: list[HaltCondition] = []
    n = len(rows)

    # Reconciliation arithmetic — defense in depth.
    standard_sum = (
        standard.unknown_category
        + standard.generic_reserved_uuid  # §4.4 (MAC-359; absorbed MAC-388)
        + standard.procurement_only
        + standard.self_exclude_oui
        + standard.below_confidence_threshold
        + standard.oversized_mac_range
        + standard.ssid_pattern
        + standard.ssid_pattern_fp_hold  # CP51 (§4.4, MAC-517)
        + standard.device_fingerprint
        + standard.ble_local_name
        + standard.ble_characteristic
        + standard.product_family_codename
        + sum(standard.cp16_dropped.values())  # CP16 (§4.4) cluster
        + standard.excluded_source_type  # CP19 (§7.5) — zero for standard file
    )
    if standard_sum + standard.survivors != n:
        halts.append(
            HaltCondition(
                kind="drop_tally_reconciliation_failure",
                detail=(
                    f"Standard export drop-tally arithmetic failed: "
                    f"{standard_sum} dropped + {standard.survivors} survivors "
                    f"!= {n} active rows."
                ),
            )
        )
    high_conf_sum = (
        high_conf.unknown_category
        + high_conf.generic_reserved_uuid  # §4.4 (MAC-359; absorbed MAC-388)
        + high_conf.procurement_only
        + high_conf.self_exclude_oui
        + high_conf.below_confidence_threshold
        + high_conf.oversized_mac_range
        + high_conf.ssid_pattern
        + high_conf.ssid_pattern_fp_hold  # CP51 (§4.4, MAC-517)
        + high_conf.device_fingerprint
        + high_conf.ble_local_name
        + high_conf.ble_characteristic
        + high_conf.product_family_codename
        + sum(high_conf.cp16_dropped.values())  # CP16 (§4.4) cluster
        + high_conf.excluded_source_type  # CP19 (§7.5)
    )
    if high_conf_sum + high_conf.survivors != n:
        halts.append(
            HaltCondition(
                kind="drop_tally_reconciliation_failure",
                detail=(
                    f"High-confidence export drop-tally arithmetic failed: "
                    f"{high_conf_sum} dropped + {high_conf.survivors} survivors "
                    f"!= {n} active rows."
                ),
            )
        )

    # §11 #13 sentinel — every unknown-category row should be Talos-banned.
    surviving_unknown = [
        r for r in rows
        if r.device_category == "unknown" and r.id not in standard.drop_assignments
    ]
    if surviving_unknown:
        halts.append(
            HaltCondition(
                kind="new_unknown_category_export_leak",
                detail=(
                    f"{len(surviving_unknown)} rows with device_category='unknown' "
                    f"survived the standard export drop tally despite §11 #13."
                ),
                row_ids=tuple(r.id for r in surviving_unknown),
            )
        )

    # §11 #14 sentinel — every procurement-only row should be Talos-banned.
    surviving_procurement = [
        r for r in rows
        if r.source_type == "procurement" and r.id not in standard.drop_assignments
    ]
    if surviving_procurement:
        halts.append(
            HaltCondition(
                kind="new_procurement_only_export_leak",
                detail=(
                    f"{len(surviving_procurement)} procurement-only rows survived "
                    f"the standard export drop tally despite §11 #14."
                ),
                row_ids=tuple(r.id for r in surviving_procurement),
            )
        )

    # §8.2 source_type sanity — every active source_type should be in the §8.2 enum.
    unknown_st = sorted({r.source_type for r in rows} - SOURCE_TYPE_CEILINGS.keys())
    if unknown_st:
        halts.append(
            HaltCondition(
                kind="unknown_source_type",
                detail=(
                    f"Active rows carry source_type values not in §8.2 enum: "
                    f"{unknown_st}. §4.2 schema drift candidate."
                ),
            )
        )

    return halts


def run_coverage_matrix(conn: sqlite3.Connection) -> CoverageMatrixReport:
    """Run the read-only coverage matrix pass against the active set on ``conn``."""
    rows = _load_active_rows(conn)
    cells = _compute_cells(rows)
    vendor_xref = _compute_vendor_corroboration(conn, rows)

    standard = _compute_drop_tally(
        rows,
        file_label="argus_export.json",
        confidence_floor=EXPORT_STANDARD_FLOOR,
        drop_pi_self_exclude=False,  # §8.4: standard export keeps Pi OUIs
        drop_source_types=frozenset(),  # CP19: standard export keeps all source_types
    )
    high_conf = _compute_drop_tally(
        rows,
        file_label="argus_export_high_confidence.json",
        confidence_floor=EXPORT_HIGH_CONFIDENCE_FLOOR,
        drop_pi_self_exclude=True,  # §8.4 / §11 #12: high-conf drops Pi OUIs
        drop_source_types=EXCLUDED_SOURCE_TYPES,  # CP19 (§7.5): high-conf drops inferred + crowdsourced
    )

    halts = _check_halts(rows, standard, high_conf)

    return CoverageMatrixReport(
        pre_active_count=len(rows),
        cells=tuple(cells),
        vendor_corroboration=tuple(vendor_xref),
        drop_tally_standard=standard,
        drop_tally_high_confidence=high_conf,
        halts=tuple(halts),
    )


# ────────────────────────────────────────────────────────────────────────────
# Output emission
# ────────────────────────────────────────────────────────────────────────────


def report_to_dict(report: CoverageMatrixReport) -> dict:
    return {
        "pre_active_count": report.pre_active_count,
        "device_categories": list(DEVICE_CATEGORIES),
        "identifier_types": list(IDENTIFIER_TYPES),
        "cells": [
            {
                "device_category": c.device_category,
                "identifier_type": c.identifier_type,
                "n": c.n,
                "n_by_source_type": c.n_by_source_type,
                "min_conf": c.min_conf,
                "max_conf": c.max_conf,
                "median_conf": c.median_conf,
                "row_ids": list(c.row_ids),
            }
            for c in report.cells
        ],
        "vendor_corroboration": [
            {
                "canonical_name": v.canonical_name,
                "aliases_used": list(v.aliases_used),
                "fcc_grantees_count": v.fcc_grantees_count,
                "procurement_records_count": v.procurement_records_count,
                "deployment_observations_count": v.deployment_observations_count,
                "council_minutes_matters_count": v.council_minutes_matters_count,
                "high_corroboration": v.high_corroboration,
                "active_identifier_count": v.active_identifier_count,
            }
            for v in report.vendor_corroboration
        ],
        "drop_tally_standard": _drop_tally_to_dict(report.drop_tally_standard),
        "drop_tally_high_confidence": _drop_tally_to_dict(
            report.drop_tally_high_confidence
        ),
        "halts": [asdict(h) for h in report.halts],
    }


def _drop_tally_to_dict(t: DropBinTally) -> dict:
    bins: dict[str, int] = {
        "unknown_category": t.unknown_category,
        # §4.4 (MAC-359; absorbed MAC-388) — generic/reserved BLE-UUID bin.
        "generic_reserved_uuid": t.generic_reserved_uuid,
        "procurement_only": t.procurement_only,
        "self_exclude_oui": t.self_exclude_oui,
        "below_confidence_threshold": t.below_confidence_threshold,
        "oversized_mac_range": t.oversized_mac_range,
        "ssid_pattern": t.ssid_pattern,
        # CP51 (§4.4, MAC-517) — ssid_pattern FP-hold bin.
        "ssid_pattern_fp_hold": t.ssid_pattern_fp_hold,
        "device_fingerprint": t.device_fingerprint,
        # CP13 (§4.4) — Wave G analytical-only types.
        "ble_local_name": t.ble_local_name,
        "ble_characteristic": t.ble_characteristic,
        "product_family_codename": t.product_family_codename,
    }
    # CP16 (§4.4) — CP14 cluster DROPPED-class bins (12 entries).
    bins.update(t.cp16_dropped)
    # CP19 (§7.5) — source_type exclusion bin (high-conf only, zero in standard).
    bins["excluded_source_type"] = t.excluded_source_type
    return {
        "file_label": t.file_label,
        "confidence_floor": t.confidence_floor,
        "drop_pi_self_exclude": t.drop_pi_self_exclude,
        "bins": bins,
        "survivors": t.survivors,
        "reconciles": sum(bins.values()) + t.survivors,
        "drop_assignments": {str(k): v for k, v in sorted(t.drop_assignments.items())},
    }


def report_to_markdown(report: CoverageMatrixReport) -> str:
    lines: list[str] = []
    lines.append("# Phase-5 Step-6 coverage matrix (MAC-45)")
    lines.append("")
    lines.append(
        f"Generated by `db/validation/coverage_matrix.py` against the "
        f"active set (`superseded_by IS NULL`) of `db/argus.db`. "
        f"Active row count: **{report.pre_active_count}**."
    )
    lines.append("")
    lines.append(
        "Read-only pass. No identifier mutations. §8.3 dedup is closed at "
        "Step-5 (MAC-42). Phase-3 corroboration counts are NOT a §11 #8 "
        "uplift channel — gap-analysis only."
    )
    lines.append("")

    lines.append("## §11 attestations")
    lines.append("")
    lines.append("- **§11 #1 (no fabrication)** — every cell, vendor count, "
                 "and drop bin is computed from `db/argus.db` rows; no synthetic "
                 "values inserted.")
    lines.append("- **§11 #6 (no live fetches)** — `PRAGMA query_only = ON` "
                 "is set on the connection; the orchestrator cannot write and "
                 "fires zero outbound HTTP calls.")
    lines.append("- **§11 #7 (provenance carry-through)** — each cell's "
                 "`row_ids` field cites the source `identifiers.id` values; "
                 "the underlying provenance (`source_url`, `source_excerpt`) "
                 "lives unchanged on the cited rows.")
    lines.append("- **§11 #8 (no confidence drift)** — read-only pass; no "
                 "writes to `confidence`. Phase-3 corroboration counts are "
                 "annotation-only.")
    lines.append("- **§11 #11 (halt-the-line)** — defensive checks for "
                 "drop-tally reconciliation, unknown-source-type, "
                 "unknown-category export leak, and procurement-only export "
                 "leak. Halts at HB35: " +
                 (f"{len(report.halts)} (see Halts section)." if report.halts
                  else "0."))
    lines.append("- **§11 #13 (unknown-category Talos-banned)** — the "
                 "`unknown_category` bin captures every row with "
                 "`device_category='unknown'`; a survival is a halt.")
    lines.append("- **§11 #14 (procurement-only Talos-banned)** — the "
                 "`procurement_only` bin captures every row with "
                 "`source_type='procurement'`; a survival is a halt.")
    lines.append("")

    if report.halts:
        lines.append("## Halts")
        lines.append("")
        for h in report.halts:
            lines.append(f"- **`{h.kind}`** — {h.detail}")
            if h.row_ids:
                lines.append(f"  - row_ids: {list(h.row_ids)}")
        lines.append("")

    # ─── Coverage matrix ───────────────────────────────────────────────────
    lines.append("## §6.1 Coverage matrix (rows × cols)")
    lines.append("")
    lines.append(
        f"Rows = `device_category` enum ({len(DEVICE_CATEGORIES)} values, "
        f"migration 0001 verbatim). "
        f"Cols = `identifier_type` enum ({len(IDENTIFIER_TYPES)} values: 9 "
        f"from migration 0001 + 3 from migration 0009 / CP13 — `ble_local_name`, "
        f"`ble_characteristic`, `product_family_codename` — Wave G structural "
        f"fidelity, all DROPPED-class for Lynceus + CP16 cluster from "
        f"migrations 0011/0013/0014: 3 MAP — `ble_manufacturer_id`, "
        f"`drone_id_prefix`, `wifi_aware_service_name` — and "
        f"{len(DROPPED_REASONS)} DROPPED). "
        f"Cells show `n` only; per-source-type breakdown + confidence "
        f"distribution in the cell-detail table below."
    )
    lines.append("")
    header = "| device_category \\ identifier_type | " + " | ".join(IDENTIFIER_TYPES) + " | **row total** |"
    lines.append(header)
    lines.append("|" + "---|" * (len(IDENTIFIER_TYPES) + 2))
    cell_lookup: dict[tuple[str, str], CellStats] = {
        (c.device_category, c.identifier_type): c for c in report.cells
    }
    col_totals = {it: 0 for it in IDENTIFIER_TYPES}
    grand_total = 0
    for dc in DEVICE_CATEGORIES:
        row_cells = []
        row_total = 0
        for it in IDENTIFIER_TYPES:
            n = cell_lookup[(dc, it)].n
            row_cells.append(str(n) if n else ".")
            col_totals[it] += n
            row_total += n
        grand_total += row_total
        lines.append(f"| `{dc}` | " + " | ".join(row_cells) + f" | **{row_total}** |")
    col_totals_row = " | ".join(
        f"**{col_totals[it]}**" if col_totals[it] else "." for it in IDENTIFIER_TYPES
    )
    lines.append(f"| **col total** | {col_totals_row} | **{grand_total}** |")
    lines.append("")

    lines.append("### Non-empty cell detail")
    lines.append("")
    lines.append("| device_category | identifier_type | n | n_by_source_type | min_conf | max_conf | median_conf | row_ids |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for c in report.cells:
        if c.n == 0:
            continue
        st_str = ", ".join(f"{k}={v}" for k, v in c.n_by_source_type.items())
        rid_str = ", ".join(str(i) for i in c.row_ids[:8])
        if len(c.row_ids) > 8:
            rid_str += f" … +{len(c.row_ids) - 8}"
        lines.append(
            f"| `{c.device_category}` | `{c.identifier_type}` | {c.n} | {st_str} | "
            f"{c.min_conf} | {c.max_conf} | {c.median_conf} | {rid_str} |"
        )
    lines.append("")

    lines.append("### Shape-gap surface (CP5 board-class, NOT halt per dispatch)")
    lines.append("")
    empty_categories = [
        dc for dc in DEVICE_CATEGORIES
        if all(cell_lookup[(dc, it)].n == 0 for it in IDENTIFIER_TYPES)
    ]
    lines.append(
        f"- **Empty device_category rows:** {len(empty_categories)} of "
        f"{len(DEVICE_CATEGORIES)} (`{', '.join(empty_categories)}`). "
        f"Drives directly from §8.4 (\"Multi-purpose vendors are not "
        f"categorized at the OUI level\") — every Phase-3-inferred OUI sits "
        f"in `unknown` until model-level evidence lands."
    )
    empty_types = [
        it for it in IDENTIFIER_TYPES
        if all(cell_lookup[(dc, it)].n == 0 for dc in DEVICE_CATEGORIES)
    ]
    lines.append(
        f"- **Empty identifier_type cols:** {len(empty_types)} of "
        f"{len(IDENTIFIER_TYPES)} (`{', '.join(empty_types)}`). Enums declared "
        f"in §4.1 (migration 0001) and CP13 (migration 0009) without any "
        f"Tier-1/2/3/4 source promotion yet."
    )
    lines.append(
        "- **Dispatch §6.1 column-list typo:** the dispatch lists `ssid` and "
        "`fcc_id` which are NOT `identifiers.identifier_type` enum values "
        "(they are `ssid_exact` and Phase-4 `fcc_equipment_filings.fcc_id` "
        "respectively per §4.2). The matrix uses the migration-0001 enum verbatim."
    )
    lines.append(
        "- **Dispatch §6.1 device_category count typo:** the dispatch says "
        "\"13 device_category enum values\" — migration 0001 declares 12 "
        "and migration 0007 does not extend the CHECK. The matrix uses the "
        "12 enum values from migration 0001 verbatim."
    )
    lines.append("")

    # ─── Vendor corroboration ──────────────────────────────────────────────
    lines.append("## §6.2 Phase-3 cross-reference annotation (gap-analysis layer)")
    lines.append("")
    lines.append(
        "Per active vendor, count rows in the four Phase-3 corpora whose "
        "free-text vendor field matches `LIKE '%<canonical>%'` OR any of the "
        "`manufacturers.aliases` tokens (OR-semantics; no double-count)."
    )
    lines.append("")
    lines.append(
        "**Reminder per dispatch §6.2 + §11 #8:** corroboration counts are "
        "NOT a §8.3 dedup uplift channel. Confidence is locked at staging "
        "time per §8.2 source-type ceiling."
    )
    lines.append("")
    lines.append("| Vendor (canonical) | Active id rows | FCC grantees | Procurement | Deployment obs | Council matters | Tier |")
    lines.append("|---|---|---|---|---|---|---|")
    for v in report.vendor_corroboration:
        tier = "**HIGH**" if v.high_corroboration else "low"
        lines.append(
            f"| `{v.canonical_name}` | {v.active_identifier_count} | "
            f"{v.fcc_grantees_count} | {v.procurement_records_count} | "
            f"{v.deployment_observations_count} | "
            f"{v.council_minutes_matters_count} | {tier} |"
        )
    lines.append("")
    high_corr = [v.canonical_name for v in report.vendor_corroboration if v.high_corroboration]
    low_corr = [v.canonical_name for v in report.vendor_corroboration if not v.high_corroboration]
    lines.append(
        f"**Tier summary:** {len(high_corr)} vendor(s) at HIGH "
        f"corroboration (≥{HIGH_CORROBORATION_GRANTEES_FLOOR} grantees AND "
        f"≥{HIGH_CORROBORATION_PROCUREMENT_FLOOR} procurements): "
        f"{', '.join(f'`{v}`' for v in high_corr) if high_corr else '_(none)_'}. "
        f"{len(low_corr)} vendor(s) at low corroboration: "
        f"{', '.join(f'`{v}`' for v in low_corr) if low_corr else '_(none)_'}."
    )
    lines.append("")
    lines.append(
        "**Alias-noise caveat (CP5 board-class):** common-token aliases "
        "(`Axis`, `Flock`, `Harris`, `Jacobs`, `Parrot`) inflate counts via "
        "surname / county-name / figurative usage. The substring-LIKE sweep "
        "is intentionally permissive per dispatch (\"NOT identifier-level "
        "dedup — this is procurement-context only\"); a Step-7 export-time "
        "tightening would need a bible-amendment-grade word-boundary disambig "
        "predicate. Out of MAC-45 scope; flagged for CP5 surface."
    )
    lines.append("")
    lines.append(
        "**FCC-staleness caveat:** the `fcc_grantees` corpus is frozen at "
        "2021-03-22 (per §4.2 dataset_freeze_date on source_id=7). Post-2020 "
        "vendors (Flock Safety, Skydio etc.) show low FCC counts not because "
        "of vendor-attestation gaps but because the upstream mirror predates "
        "their FCC filings. Phase-4 owns the gap; out of MAC-45 scope."
    )
    lines.append("")

    # ─── Drop tallies ──────────────────────────────────────────────────────
    lines.append("## §6.3 / §9 item 9 \"Dropped from Talos export\" pre-tally")
    lines.append("")
    lines.append(
        "Each row is assigned to AT MOST one drop bin (priority order: "
        "`procurement_only` > `unknown_category` > `device_fingerprint` > "
        "`ssid_pattern` > `ble_local_name` > `ble_characteristic` > "
        "`product_family_codename` > `oversized_mac_range` > "
        "{CP16 DROPPED_REASONS} > `self_exclude_oui` > "
        "`below_confidence_threshold` > `excluded_source_type`). Survivors "
        "are eligible for the corresponding Lynceus export file. "
        "Reconciliation: `pre_active_count − sum(bins) = survivors`."
    )
    lines.append("")
    for tally in (report.drop_tally_standard, report.drop_tally_high_confidence):
        lines.append(f"### `{tally.file_label}` (confidence ≥ {tally.confidence_floor}; "
                     f"Pi self-exclude drop = {tally.drop_pi_self_exclude})")
        lines.append("")
        bins_table = [
            ("`unknown_category` (§11 #13)", tally.unknown_category),
            ("`generic_reserved_uuid` (§4.4 MAC-359)", tally.generic_reserved_uuid),
            ("`procurement_only` (§11 #14)", tally.procurement_only),
            ("`device_fingerprint` (§4.4)", tally.device_fingerprint),
            ("`ssid_pattern` (§4.4)", tally.ssid_pattern),
            ("`ssid_pattern_fp_hold` (§4.4 CP51 MAC-517)", tally.ssid_pattern_fp_hold),
            ("`ble_local_name` (§4.4 CP13)", tally.ble_local_name),
            ("`ble_characteristic` (§4.4 CP13)", tally.ble_characteristic),
            ("`product_family_codename` (§4.4 CP13)", tally.product_family_codename),
            ("`oversized_mac_range` (§4.4)", tally.oversized_mac_range),
        ]
        # CP16 (§4.4) — CP14 cluster DROPPED-class bins. Stable insertion
        # order matches DROPPED_REASONS dict order so the markdown rendering
        # is deterministic across runs.
        for cp16_bin in DROPPED_REASONS.values():
            bins_table.append(
                (f"`{cp16_bin}` (§4.4 CP16)", tally.cp16_dropped[cp16_bin])
            )
        bins_table.extend(
            [
                ("`self_exclude_oui` (§8.4 / §11 #12)", tally.self_exclude_oui),
                ("`below_confidence_threshold` (§7.5)", tally.below_confidence_threshold),
                ("`excluded_source_type` (§7.5 CP19)", tally.excluded_source_type),
            ]
        )
        lines.append("| Bin | Count |")
        lines.append("|---|---|")
        for name, count in bins_table:
            lines.append(f"| {name} | {count} |")
        sum_bins = sum(c for _, c in bins_table)
        lines.append(f"| **sum(bins)** | **{sum_bins}** |")
        lines.append(f"| **survivors → eligible entries** | **{tally.survivors}** |")
        lines.append(f"| **reconciliation** | "
                     f"**{report.pre_active_count} − {sum_bins} = {tally.survivors}** "
                     f"{'✅' if report.pre_active_count - sum_bins == tally.survivors else '❌'} |")
        lines.append("")
    lines.append("")

    lines.append("### mac_range secondary-constraint note (CP5 board-class)")
    lines.append("")
    mac_range_rows = [
        c for c in report.cells if c.identifier_type == "mac_range" and c.n > 0
    ]
    total_mr = sum(c.n for c in mac_range_rows)
    lines.append(
        f"- All {total_mr} active `mac_range` rows are OUI-28 (28-bit, 1,048,576 "
        f"entries) or OUI-36 (36-bit, 4096 entries) prefixes — both far "
        f"exceed §4.4's 256-entry expansion ceiling. They drop to "
        f"`unknown_category` in the tally above (priority order puts §11 #13 "
        f"first), but they would ALSO drop to `oversized_mac_range` if their "
        f"`device_category` were ever lifted off `unknown` without an "
        f"export-time `mac_range`-expansion strategy. The two drop reasons "
        f"are not exclusive; the priority order picks one for arithmetic. "
        f"CP5 board-class surface: a per-OUI `unknown`-only-fallback or a "
        f"§4.4 amendment to permit OUI-prefix routing without expansion "
        f"would unblock these for Talos."
    )
    lines.append("")

    return "\n".join(lines) + "\n"


# ────────────────────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────────────────────


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DB_PATH), help="Path to argus.db")
    parser.add_argument(
        "--out-dir",
        default=str(Path(__file__).resolve().parents[2] / "extraction_outputs" / "mac45"),
        help="Output directory for coverage_matrix.{md,json}",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full report as JSON to stdout instead of summary table.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Compute the report but do not write artifacts to --out-dir.",
    )
    args = parser.parse_args(argv)

    conn = _connect(Path(args.db))
    try:
        report = run_coverage_matrix(conn)
    finally:
        conn.close()

    if not args.no_write:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "coverage_matrix.md").write_text(report_to_markdown(report))
        (out_dir / "coverage_matrix_report.json").write_text(
            json.dumps(report_to_dict(report), indent=2, default=str)
        )

    payload = report_to_dict(report)
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(f"Pre-active identifiers:                       {report.pre_active_count}")
        print(f"Cells ({len(DEVICE_CATEGORIES)} dc × "
              f"{len(IDENTIFIER_TYPES)} it = "
              f"{len(DEVICE_CATEGORIES) * len(IDENTIFIER_TYPES)}):"
              f"           {len(report.cells)}")
        print(f"Non-empty cells:                              "
              f"{sum(1 for c in report.cells if c.n > 0)}")
        print(f"Vendor corroboration entries:                 "
              f"{len(report.vendor_corroboration)}")
        ds = report.drop_tally_standard
        dh = report.drop_tally_high_confidence
        print(f"Standard export survivors (≥{ds.confidence_floor}):"
              f" {ds.survivors:3d}  (dropped: "
              f"{report.pre_active_count - ds.survivors})")
        print(f"High-conf export survivors (≥{dh.confidence_floor}):"
              f" {dh.survivors:3d}  (dropped: "
              f"{report.pre_active_count - dh.survivors})")
        print(f"Halts:                                        {len(report.halts)}")
        for h in report.halts:
            print(f"  HALT [{h.kind}]: {h.detail}")

    return 1 if report.halts else 0


if __name__ == "__main__":
    raise SystemExit(main())
