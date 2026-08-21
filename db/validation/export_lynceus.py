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
    # CP51 (§4.4, MAC-517) — ssid_pattern MAP → Lynceus 0.9.2 `ssid_pattern`
    # matcher (case-insensitive substring containment: `? LIKE '%'||needle||'%'
    # COLLATE NOCASE`, db.py:1126). Superseded the stale "no regex in v0.2" DROP:
    # the board (MAC-516) pinned Lynceus 0.9.2 as substring-not-regex, so every
    # active ssid_pattern value is converted to a Lynceus-safe leading-literal
    # substring via `_ssid_pattern_to_substring` and emitted here. FP-hold rows
    # (generic/short stems) return None from that helper and drop to the
    # `ssid_pattern_fp_hold` bin instead. Mirror in
    # coverage_matrix.py::_assign_drop_bin (the `_reconcile` cross-check halts on
    # any divergence).
    "ssid_pattern": "ssid_pattern",  # MAP — CP51 Lynceus-0.9.2 substring (MAC-517)
    "ble_uuid": "ble_uuid",
    "ble_service": "ble_uuid",
    # CP21 (§4.4) — alias-collapse to existing `ble_uuid` per the CP13
    # `ble_service → ble_uuid` precedent (BLE service UUIDs ARE UUIDs for
    # Lynceus). Ratified in the PROJECT_BIBLE.md §4.4 mapping table (CP21 /
    # MAC-101 board sign-off e246a32a) but never implemented in this writer —
    # the DROPPED_REASONS entry below carried a stale "awaiting §4.4 alias
    # confirm" comment. MAC-359 closed the code-vs-Bible gap; absorbed here at
    # MAC-388 (parent MAC-387) — MAC-359 half ONLY (the symmetric MAC-360
    # `ble_company_id` half stays HELD/DROPPED, id4884). CP-ref is the existing
    # CP21 (NOT a new CP — the parked-bundle "CP46" draft slot is superseded by
    # this absorption; see BIBLE_AMENDMENTS CP45 reconciliation note).
    "ble_service_uuid": "ble_uuid",  # MAP — CP21 alias-collapse (MAC-359, absorbed at MAC-388)
    "mac_range": None,  # expand or DROP per §4.4 (≤256 → expand else drop)
    "device_fingerprint": None,  # DROPPED per §4.4
    # CP13 (§4.4) — Wave G analytical-only types. All three are DROPPED-class:
    # carried in the canonical DB but never reach the Lynceus pattern table.
    #
    # Apply-time correction (MAC-543, 2026-07-28): the CP13 blanket DROP for
    # `ble_local_name` was SUPERSEDED by CP50 (§4.4, MAC-420) — it is now a
    # conditional MAP and its sole entry lives below with the CP50 rationale.
    # A stale duplicate `"ble_local_name": None` key survived here inside the
    # same dict literal; Python last-key-wins already resolved the mapping to
    # the CP50 MAP, so removing it is a no-op on all three consumer artifacts
    # (proof: operator_review/MAC-543/noop_proof.md). It is removed because a
    # keep-first dedup codemod, an alphabetical re-sort, or a bad merge would
    # have silently flipped the CP50 MAP back to DROPPED with no error and no
    # test failure. See the DUPLICATE-KEY GUARD below.
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
    # CP50 (§4.4, MAC-420) — ble_local_name LITERAL advertised-name exact match.
    # Conditional MAP: only literal values reach this entry; templated/regex forms
    # are DROPPED earlier in _classify_row via _ble_local_name_is_template. Argus
    # exports unconditionally regardless of Lynceus scanner local-name support
    # state (architectural-separation policy). Proposed slot CP50 — CP48=§11#22
    # reserved, CP49 contested by MAC-478/489 drafts; board finalizes CP numbering
    # at the push gate (see operator_review/MAC-490).
    "ble_local_name": "ble_local_name",  # MAP — CP50 literal advertised-name exact match
    # CP21 (§4.4) — symmetric to the MAC-359 ble_service_uuid alias-collapse:
    # `ble_company_id` IS the SIG company-id variant of `ble_manufacturer_id`
    # (PROJECT_BIBLE.md:279, board e246a32a, MAC-101 §2.5). Un-held at MAC-360 /
    # CP47. MUST ride the ingest gate COUPLED with the id23052 '67'->'0x0043'
    # normalize (scripts/mac360_cp47_ble_company_id_normalize_apply.py) — a regen
    # before that mutation lands would ship the malformed decimal '67'. id4884
    # (ble_manufacturer_id 0x0043, unknown) is unknown-banned → no feed dup.
    "ble_company_id": "ble_manufacturer_id",  # MAP — CP21 §4.4 alias-collapse (MAC-360 / CP47)
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
    # `ble_service_uuid` MOVED to IDENTIFIER_TYPE_TO_PATTERN_TYPE (MAP → ble_uuid)
    # at MAC-359 — CP21 §4.4 alias-collapse, code-vs-Bible gap closed (absorbed
    # at MAC-388). No drop bin retained for it (see bins dict below).
    # `ble_company_id` MOVED to IDENTIFIER_TYPE_TO_PATTERN_TYPE (MAP → ble_manufacturer_id)
    # at MAC-360 / CP47 — CP21 §4.4 alias-collapse, symmetric to MAC-359's
    # ble_service_uuid. No drop bin retained (see bins dict below). Rides the
    # ingest gate coupled with the id23052 normalize.
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
    # CP35 (mig-0028 / MAC-255) — NDPP §4.4 ratified DROP (option (b)). CP42 §2
    # (MAC-300, 2026-06-03) supersedes CP35 §215's descriptive-bin_label
    # sub-decision: the identity-keyed convention (DROPPED_REASONS[k] == k)
    # is restored universally. CP35's substantive ratification (DROP for NDPP
    # per cross-repo-scope-respecting Lynceus v0.3 scanner pathway argument)
    # is intact; only the bin_label shape is amended. Descriptive rationale
    # moves to the sibling DROPPED_REASONS_RATIONALE dict below.
    "network_discovery_protocol_pattern": "network_discovery_protocol_pattern",
    # CP42 §1 (MAC-300, 2026-06-03) — imei_tac §4.4 consumer-side DROP
    # (analogue to CP35 NDPP). IMEI/TAC values are GSMA Type Allocation Code
    # registry metadata, not RF-broadcast wire patterns observable by
    # Lynceus's passive-scanner architecture. CP33 §2.2 (gate G-C) admitted
    # the schema-side slot forward-compatibly with zero promoted rows; CP42
    # §1 closes the §4.4 consumer-side gap with a DROP-with-reason entry,
    # preserving the canonical schema slot for future v1.5.x cohort backfill.
    "imei_tac": "imei_tac",
}


# CP42 §2 (MAC-300, 2026-06-03) — sibling rationale dict. DROPPED_REASONS keys
# stay identity-keyed (bin_label == identifier_type); the descriptive "why
# DROPPED" rationale for entries that carry one (NDPP, imei_tac) lives here.
# Audit-trail use only — not consulted by the classifier (`_classify_row`
# returns `DROPPED_REASONS[identifier_type]` and never reads this dict).
# Future DROPPED_REASONS additions that need a non-trivial rationale beyond
# the inline DROPPED_REASONS comment SHOULD add a paired entry here for the
# §4.4 audit-trail.
DROPPED_REASONS_RATIONALE: dict[str, str] = {
    "network_discovery_protocol_pattern": (
        "Awaiting Lynceus v0.3 scanner_support for "
        "network_discovery_protocol_pattern matching "
        "(CP35 §215 cross-repo scope)"
    ),
    "imei_tac": (
        "GSMA Type Allocation Code registry metadata; not RF-broadcast wire "
        "pattern observable by Lynceus passive scanners (CP35 NDPP §4.4 "
        "precedent)"
    ),
}


# ---------------------------------------------------------------------------
# DUPLICATE-KEY GUARD (MAC-543) — §11 halt-the-line discipline applied to the
# §4.4 mapping tables themselves.
#
# `IDENTIFIER_TYPE_TO_PATTERN_TYPE` is the single source of truth for what
# reaches the Lynceus feed. A duplicate key inside the dict literal is
# resolved silently by Python (last wins) — no error, no test failure, no
# dangerous-looking diff — so which of the two entries wins depends on source
# ORDER, and any keep-first dedup codemod / alphabetical re-sort / bad merge
# can invert a MAP into a DROP. MAC-543 found exactly that: a stale CP13
# `"ble_local_name": None` shadowed by the CP50 MAP entry.
#
# Two checks, catching two different failure modes:
#   (1) `_assert_no_duplicate_dict_keys` re-parses THIS module's own source and
#       halts if ANY dict literal in the file (module-level or nested) declares
#       more constant key entries than it resolves to. Catches a duplicate being
#       (re-)introduced anywhere, not just in the §4.4 tables.
#   (2) the explicit CP50 value assertions below. Catches the case a dedup
#       CANNOT catch — a reviewer deleting the surviving entry and keeping the
#       shadowed one, which leaves zero duplicates but flips the mapping.
#
# Both raise (never `assert`) so `python -O` cannot strip them.
# ---------------------------------------------------------------------------
def _assert_no_duplicate_dict_keys() -> None:
    """Halt if any dict literal in this file declares a duplicate constant key.

    Covers every dict literal in the module, nested ones included. Only constant
    keys are compared — computed keys cannot be resolved statically and are
    skipped rather than guessed at.

    Silent no-op when the source is unreadable (frozen/zipped import); the
    explicit CP50 assertions below are the unconditional backstop.
    """
    import ast

    try:
        source = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, NameError):  # pragma: no cover — frozen import
        return

    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        literal_keys = [
            key.value for key in node.keys if isinstance(key, ast.Constant)
        ]
        if len(literal_keys) != len(set(literal_keys)):
            duplicates = sorted(
                {key for key in literal_keys if literal_keys.count(key) > 1}
            )
            raise RuntimeError(
                "HALT (§11, MAC-543): duplicate key(s) in the dict literal at "
                f"{Path(__file__).name}:{node.lineno} — {duplicates}. Python "
                "resolves these silently by source order; a §4.4 mapping entry "
                "may be shadowed. Delete the stale entry, do NOT rely on "
                "last-key-wins."
            )


_assert_no_duplicate_dict_keys()

# CP50 (§4.4, MAC-420) — `ble_local_name` MUST stay a MAP. Value-level check:
# survives a dedup that keeps the wrong entry, which check (1) cannot see.
if IDENTIFIER_TYPE_TO_PATTERN_TYPE.get("ble_local_name") != "ble_local_name":
    raise RuntimeError(
        "HALT (§4.4 CP50, MAC-420/MAC-543): IDENTIFIER_TYPE_TO_PATTERN_TYPE"
        "['ble_local_name'] must MAP to 'ble_local_name' (literal advertised-"
        "name exact match). Got "
        f"{IDENTIFIER_TYPE_TO_PATTERN_TYPE.get('ble_local_name')!r}. Templated "
        "values are DROPPED earlier in _classify_row via "
        "_ble_local_name_is_template — the type-level entry is NOT the drop."
    )

# CP13 siblings that CP50 did NOT lift — pin them so the correction above is
# not over-applied to the other two Wave G analytical-only types.
for _cp13_dropped in ("ble_characteristic", "product_family_codename"):
    if IDENTIFIER_TYPE_TO_PATTERN_TYPE.get(_cp13_dropped, "sentinel") is not None:
        raise RuntimeError(
            f"HALT (§4.4 CP13, MAC-543): {_cp13_dropped!r} must stay "
            "DROPPED-class (None) in IDENTIFIER_TYPE_TO_PATTERN_TYPE."
        )
del _cp13_dropped


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

# CP39 §7.5 carve-out — named Flock-hunt project source URL patterns.
# Rows whose source_url contains any of these substrings bypass the
# EXCLUDED_SOURCE_TYPES gate. Rationale (v1.6.2.1 board ratification): these
# upstream projects have shipped releases with active users, which is
# sufficient external verification for high-confidence-export admission even
# though source_type stays honest (`crowdsourced`/`inferred`/`academic`).
# Named and bounded — does NOT open the floor for arbitrary crowdsourced
# rows. See `docs/engineering/BIBLE_AMENDMENTS.md` Correction Pass 39.
# Coordinated sibling: `coverage_matrix.py` must use the identical set (the
# `_reconcile` map-vs-writer cross-check halts on any divergence).
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


# §4.4 generic/reserved BLE-UUID export suppression (MAC-359, CEO Ruling 3;
# absorbed at MAC-388 / MAC-387). Value-keyed (not type-keyed) suppression of
# structurally non-discriminating UUIDs that survive the §4.4
# `ble_service_uuid -> ble_uuid` MAP but are false-positive magnets at Lynceus.
# Policy-consistent with the existing §4.4 "overly-coarse" DROP rationale (cf.
# `wifi_ie_element_id`): a reserved / placeholder SIG UUID carries near-zero
# match discrimination and would fire on unrelated multi-vendor hardware.
# Currently: SIG 16-bit 0xFFFF (`0000ffff-...`), reserved/placeholder, observed
# multi-vendor (id 23051, Motorola Solutions WAVE APK). Suppressing at export
# keeps the real canonical row intact (no DB deletion) while withholding it from
# the consumer feed; the drop is counted in the `generic_reserved_uuid` bin
# (visible in the coverage report — no silent suppression). Coordinated sibling:
# `coverage_matrix.py::GENERIC_RESERVED_UUID_SUPPRESS` must use the identical set
# (the `_reconcile` map-vs-writer cross-check halts on any divergence).
GENERIC_RESERVED_UUID_SUPPRESS: frozenset[str] = frozenset(
    {"0000ffff-0000-1000-8000-00805f9b34fb"}
)

# §4.4 mac_range expansion ceiling.
MAC_RANGE_EXPANSION_CEILING = 256

# §7.5 description-format constraint (CP8 flat form ≤80 chars).
DESCRIPTION_MAX_CHARS = 80

# CP8 description-format fallbacks (verbatim).
DESCRIPTION_VENDOR_UNATTRIBUTED = "Unattributed identifier"

# CP7 default geographic_scope filter (US-deployed Lynceus instances).
DEFAULT_GEOGRAPHIC_SCOPE_FILTER: tuple[str, ...] = ("US",)

# ---------------------------------------------------------------------------
# MAC-742 item 3 — continent rollup, as a RUNTIME expansion.
#
# BE HONEST ABOUT THE YIELD: this returns 0 additional rows today, and that is
# measured, not estimated. Across 43,088 active rows the registry holds exactly
# one non-US regional code (`GB`, id 23042) and that row is
# `device_category='unknown'`, which is binned before the geography gate is ever
# reached. Every other row is NULL, `global`, or `US`. This parameter is
# capability for data we do not have yet, not a yield lever. Do not cite it as
# one.
#
# Why a rollup and not a stored value: continent-as-stored-value was REJECTED by
# CEO ruling 1c34bdf7-76e2-41f9-9b65-38b56093b240. A continent token in the
# column would be a fourth vocabulary in an already-mixed column, and it does not
# compare against an ISO token in EITHER direction — a row stamped `EU` fails a
# filter of ('US','GB','DE'), and a row stamped `DE` fails a filter of ('EU',).
# The comparison is an exact match after a comma split (`_passes_geographic_scope`
# below), so the expansion has to happen before that function sees anything.
# `_passes_geographic_scope` is deliberately UNCHANGED by MAC-742.
#
# Note the token collision this design sidesteps: `AF`, `AS`, `NA` and `SA` are
# BOTH continent codes here and assigned ISO-3166 alpha-2 country codes
# (Afghanistan, American Samoa, Namibia, Saudi Arabia). They are disambiguated by
# living behind a SEPARATE flag rather than by sharing one token space with
# country codes — which is a second, independent argument for the rollup over a
# stored continent value.
#
# Membership follows the common 7-continent assignment of ISO-3166-1 alpha-2,
# dependencies included with their governing region. 246 codes.
# ---------------------------------------------------------------------------
CONTINENT_ISO3166_ALPHA2: dict[str, tuple[str, ...]] = {
    "AF": (  # Africa (58)
        "DZ", "AO", "BJ", "BW", "BF", "BI", "CM", "CV", "CF", "TD", "KM", "CG",
        "CD", "CI", "DJ", "EG", "GQ", "ER", "ET", "GA", "GM", "GH", "GN", "GW",
        "KE", "LS", "LR", "LY", "MG", "MW", "ML", "MR", "MU", "YT", "MA", "MZ",
        "NA", "NE", "NG", "RE", "RW", "SH", "ST", "SN", "SC", "SL", "SO", "ZA",
        "SS", "SD", "SZ", "TZ", "TG", "TN", "UG", "EH", "ZM", "ZW",
    ),
    "AN": ("AQ", "BV", "GS", "HM", "TF"),  # Antarctica (5)
    "AS": (  # Asia (51)
        "AF", "AM", "AZ", "BH", "BD", "BT", "BN", "KH", "CN", "CY", "GE", "HK",
        "IN", "ID", "IR", "IQ", "IL", "JP", "JO", "KZ", "KP", "KR", "KW", "KG",
        "LA", "LB", "MO", "MY", "MV", "MN", "MM", "NP", "OM", "PK", "PS", "PH",
        "QA", "SA", "SG", "LK", "SY", "TW", "TJ", "TH", "TL", "TR", "TM", "AE",
        "UZ", "VN", "YE",
    ),
    "EU": (  # Europe (51)
        "AL", "AD", "AT", "BY", "BE", "BA", "BG", "HR", "CZ", "DK", "EE", "FO",
        "FI", "FR", "DE", "GI", "GR", "GG", "HU", "IS", "IE", "IM", "IT", "JE",
        "LV", "LI", "LT", "LU", "MT", "MD", "MC", "ME", "NL", "MK", "NO", "PL",
        "PT", "RO", "RU", "SM", "RS", "SK", "SI", "ES", "SJ", "SE", "CH", "UA",
        "GB", "VA", "AX",
    ),
    "NA": (  # North America, incl. Central America and the Caribbean (41)
        "AI", "AG", "AW", "BS", "BB", "BZ", "BM", "BQ", "VG", "CA", "KY", "CR",
        "CU", "CW", "DM", "DO", "SV", "GL", "GD", "GP", "GT", "HT", "HN", "JM",
        "MQ", "MX", "MS", "NI", "PA", "PR", "BL", "KN", "LC", "MF", "PM", "VC",
        "SX", "TT", "TC", "US", "VI",
    ),
    "OC": (  # Oceania (26)
        "AS", "AU", "CK", "FJ", "PF", "GU", "KI", "MH", "FM", "NR", "NC", "NZ",
        "NU", "NF", "MP", "PW", "PG", "PN", "WS", "SB", "TK", "TO", "TV", "UM",
        "VU", "WF",
    ),
    "SA": (  # South America (14)
        "AR", "BO", "BR", "CL", "CO", "EC", "FK", "GF", "GY", "PY", "PE", "SR",
        "UY", "VE",
    ),
}


def expand_continent_filter(continents: tuple[str, ...]) -> tuple[str, ...]:
    """Expand continent codes to their ISO-3166 alpha-2 children, deduped.

    Pure and total: no DB access, no I/O. The returned tuple is sorted so an
    export's ``_meta.geographic_scope_filter`` is byte-stable across runs — an
    unordered set would make two identical exports diff.

    Raises ``KeyError`` on an unknown continent code; callers surface that as a
    CLI error rather than silently exporting a narrower feed than asked for.
    """
    out: set[str] = set()
    for code in continents:
        out.update(CONTINENT_ISO3166_ALPHA2[code])
    return tuple(sorted(out))

# Deterministic UUID5 namespace anchor — locks ``argus_run_id`` to the data.
# This namespace UUID itself is a UUID5(NAMESPACE_DNS, "argus.export.v1") so
# the choice is reproducible from this codebase alone (no opaque magic value).
ARGUS_RUN_ID_NAMESPACE: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_DNS, "argus.export.v1")


class Halt(Exception):
    """Stop-the-line signal raised on any §11 trip or reconciliation mismatch."""


# MAC-611 (remediation of MAC-570) — Bluetooth SIG registry boundary.
#
# `ble_company_id` is the SIG *Company Identifier* registry (16-bit assigned
# numbers). Values at or above 0xFC00 are NOT company identifiers: that block is
# the SIG *Member UUID* range (`assigned_numbers/uuids/member_uuids.yaml`), which
# renders as the 16-bit alias of a 128-bit base UUID
# (`0000FCxx-0000-1000-8000-00805F9B34FB`) and belongs to `ble_uuid` / the
# MAC-477 GATT-binding rule.
#
# `IDENTIFIER_TYPE_TO_PATTERN_TYPE` maps every `ble_company_id` to the Lynceus
# `ble_manufacturer_id` wire type (CP21 §4.4 alias-collapse, MAC-360 / CP47).
# A member-UUID value riding that MAP would ship as a manufacturer ID no
# consumer can match, and would invite vendor-evidence adjudication against the
# wrong registry. Export must HALT on it rather than silently repair it: the
# fix is a separately ratified canonical retype, not an exporter rewrite.
BLE_SIG_MEMBER_UUID_FLOOR: int = 0xFC00


def _ble_company_id_value(identifier: str) -> int | None:
    """Parse a `ble_company_id` identifier to its integer SIG assigned number.

    Returns None when the value does not parse — an unparsed value is itself a
    type-integrity defect and is halted by the caller rather than waived.
    """

    raw = identifier.strip()
    try:
        if raw.lower().startswith("0x"):
            return int(raw, 16)
        return int(raw, 0)
    except (TypeError, ValueError):
        return None


def _assert_ble_registry_type(row: ActiveRow) -> None:
    """MAC-611 gate 1 — BLE registry-type integrity, PRE-classification.

    Raised before ``_classify_row`` so a member-UUID-range value never reaches
    the `ble_company_id -> ble_manufacturer_id` MAP at all.
    """

    if row.identifier_type != "ble_company_id":
        return
    value = _ble_company_id_value(row.identifier)
    if value is None:
        raise Halt(
            "HALT ble_registry_type_mismatch (MAC-611): "
            f"identifiers.id={row.id} identifier_type='ble_company_id' "
            f"identifier={row.identifier!r} does not parse as a SIG assigned "
            "number. An unparsed value cannot be proven to sit below the "
            f"member-UUID floor 0x{BLE_SIG_MEMBER_UUID_FLOOR:04X}; it requires "
            "a separately ratified canonical correction."
        )
    if value >= BLE_SIG_MEMBER_UUID_FLOOR:
        raise Halt(
            "HALT ble_registry_type_mismatch (MAC-611): "
            f"identifiers.id={row.id} identifier_type='ble_company_id' "
            f"identifier={row.identifier!r} (0x{value:04X}) sits at or above the "
            f"Bluetooth SIG member-UUID floor 0x{BLE_SIG_MEMBER_UUID_FLOOR:04X}. "
            "That block is the SIG member-UUID registry, not the company-identifier "
            "registry, so this row must not ride the CP21 §4.4 "
            "`ble_company_id -> ble_manufacturer_id` MAP. Route it through the "
            "MAC-477 GATT/member-UUID binding rule and retype it canonically; "
            "the exporter must not repair it."
        )


@dataclass(frozen=True)
class ActiveRow:
    """A single ``identifiers`` row in the active set."""

    id: int
    identifier: str
    identifier_type: str
    device_category: str
    manufacturer: str | None
    model: str | None
    confidence: int | None  # MAC-336: NULL for rows staged without a §8.2 ceiling
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


# CP50 (§4.4, MAC-420) — ble_local_name literal-vs-template predicate. A literal
# advertised name (e.g. "Flock", "FS Ext Battery", "whistle3") is an exact GAP
# complete-local-name string Lynceus can match byte-for-byte. A template carries
# regex/family metacharacters (e.g. "flock[_-]?", "(cellebrite|ufed)[_-]?",
# "flipper <name>") and stays DROPPED until Lynceus gains a template matcher.
# MUST be byte-identical to coverage_matrix.py::_ble_local_name_is_template
# (the _reconcile cross-check halts on any divergence).
_BLE_LOCAL_NAME_TEMPLATE_CHARS = "[]()?*+|<>%"


def _ble_local_name_is_template(value: str) -> bool:
    return any(ch in value for ch in _BLE_LOCAL_NAME_TEMPLATE_CHARS)


# CP51 (§4.4, MAC-517, MAC-752) — ssid_pattern → Lynceus 0.9.2 substring
# conversion.  Lynceus 0.9.2 matches `ssid_pattern` as a case-insensitive
# SUBSTRING (`? LIKE '%'||needle||'%' COLLATE NOCASE`, db.py:1126) — NOT
# regex/PCRE/POSIX/glob (board-confirmed at MAC-516).  This helper reduces
# each stored `ssid_pattern` value to the Lynceus-safe substring(s) to emit:
#   1. strip a leading `(?i)` inline flag and a leading `^` anchor;
#   2. if the value is a leading alternation `(a|b|...)`, SPLIT into one
#      substring per branch AND APPEND the leading literal of the post-group
#      remainder — e.g. `(?i)^(hail|king|queen)storm[_-]?.*` →
#      ["hailstorm", "kingstorm", "queenstorm"] (MAC-752).  This stops the
#      pre-MAC-752 bug where the alternation kept only the inner branches
#      and dropped the literal after the group, producing bare-word FP
#      magnets (`hail` / `king` / `queen` matching "Thailand", "Viking",
#      "Parking" etc.);
#   3. for non-alternation rows the leading literal extends through
#      `[_-]?` optional delimiter blocks AND through mandatory
#      `(a|b|...)` groups (the MAC-752 follow-up to fix CEO Finding B).
#      `(?i)^arlo[_-]?(cam|pro|ultra|setup).*` →
#      ["arlocam", "arlopro", "arloultra", "arlosetup"] — concatenating
#      the prefix with each branch of the mandatory post-group alternation.
#      A REQUIRED `[abc]` bracket (no `?` after) is not a delimiter block
#      and the leading-literal run stops at `[`;
#   4. a branch whose own leading literal is truncated by an INTERNAL
#      metachar (e.g. `wifi[_-]?pineapple` → leading run `wifi`, truncated
#      at `[`) is rendered fully, not FP-held — the `wifi[_-]?pineapple`
#      branch of the Hak5 alternation now emits `wifipineapple` rather
#      than the bare `wifi` magnet.  The CEO call (Finding B comment,
#      2026-08-20) was "either render it fully or FP-hold the row";
#      rendering fully preserved the Hak5 product coverage AT MAC-752.
#      SUPERSEDED at MAC-761: rule 5 below now FP-holds the whole row on
#      its `pineapple` branch, so nothing from id 44726 is emitted and
#      this rendering no longer preserves any Hak5 coverage.  The
#      rendering rule itself still stands; only its coverage consequence
#      is void.  See the MAC-761 paragraph below;
#   5. FP gate (post-extension): the STRICT BASE leading literal of each
#      branch (the run of literal chars before any `[_-]?` block or
#      `(...)` group) is checked against `_SSID_PATTERN_FP_HOLD_STEMS`.
#      Holding the BASE (not the concatenated stem) preserves the
#      MAC-517 disposition that `lpr` holds a `(?i)^lpr[_-]?cam.*` row
#      regardless of how far the `[_-]?` extension would reach.  A stem
#      shorter than `_SSID_STEM_MIN_LEN` is also FP-held.
# Board disposition (MAC-517 plan) ships the distinctive 3-char brand
# tokens `dji` / `xry` but holds the generic acronym `lpr` (License
# Plate Reader); MAC-752 extends the hold-set to `digital` (7-char
# generic prefix), `flock` (5-char generic English/German word matching
# "Schneeflocke" / "RockFlock"), the 3-4 char acronyms `msab` and `xry`
# (matching `williamsabc` / `WPAHMSABMVA` / `base64xryrandom` when
# shipped bare from id 44720's unsafe `(msab|xry)[_-]?.*` shape), and
# `stingray` (9-char Harris IMSI-catcher product name that is also a
# generic English word — CEO Finding B explicit "your call"; held on
# defense-in-depth grounds: Lynceus 0.9.2 substring matching against
# `[_-]?` patterns turns the anchored `^stingray` into an unanchored
# `stingray` that matches Chevrolet, the animal, the movie, etc.).
# MAC-761 extends the hold-set to `pineapple` (9-char Hak5 product name
# that is also a common English noun): shipped bare with
# `description: "Hak5 hacking_tool"`, so under Lynceus 0.9.2 substring
# semantics `Pineapple Cafe WiFi` is labelled an attack tool.
# COST, MEASURED — NOT near-zero.  The board's original ruling assumed
# `hak5` and `wifipineapple` were siblings that would survive the hold.
# They are not siblings: all three are alternation branches of the SINGLE
# canonical row id 44726, `(?i)^(pineapple|hak5|wifi[_-]?pineapple).*`.
# The FP gate sits in the per-branch loop and returns None for the WHOLE
# row on its first held base, so holding `pineapple` withdraws `hak5`,
# `pineapple` and `wifipineapple` together — three emitted entries, not
# one (the ssid_pattern split-expansion).  Measured residual Hak5
# coverage at v1.8.0 is ZERO in both feeds: the `ble_local_name` rows are
# templates and drop at CP50, and the `hak5.org`
# `vendor_controlled_hostname` rows are export-dropped by type.  Hak5
# ships in no v1.8.0 feed.
# That cost is ACCEPTED, on the board's stated bar: a mislabelled
# `Pineapple Cafe WiFi` is a lie the consumer cannot detect, while a
# coverage gap is one Lynceus can.  Restoring the two safe branches
# requires refining row 44726 to `(?i)^(hak5|wifi[_-]?pineapple).*`,
# which is a DATA change and a migration, not a hold-set change — the
# hold-set is row-level and cannot express it.  MAC-765 owns that
# restoration.
#
# MAC-765 DISPOSITION (2026-08-20) — the hold on `pineapple` is RETAINED.
# The restoration above is written as
# `db/migrations/_drafts/0063_mac765_44726_pineapple_branch_split.sql.draft`
# (STAGED, NOT APPLIED — applying to canonical is a CEO ruling).  MAC-765
# required an explicit retire-or-keep decision on this stem once the branch
# is gone, rather than leaving it open.  Decision: KEEP, and the reason is
# measured, not assumed.  After the split the two surviving branches have
# strict bases `hak5` and `wifi` (the latter stops at the `[` metachar), so
# NO surviving branch has strict base `pineapple` — removing the stem from
# this set leaves row 44726 emitting a byte-identical
# `['hak5', 'wifipineapple']`.  Retention therefore costs ZERO coverage,
# and it still fails closed if a later harvest re-admits a row whose strict
# base is bare `pineapple` (0059's WAVE-9 harvest did exactly that class of
# re-admission for `msab`/`xry`, cf. mig-0062).  A deny-list entry that
# currently matches nothing is a forward-looking policy statement, which is
# NOT the same defect as a hardcoded metric that no input can move — that
# one was arm (a)'s literal `7/7`, repaired under MAC-765.
# MUST be byte-identical to coverage_matrix.py::_ssid_pattern_to_substring
# — the `_reconcile` map-vs-writer cross-check halts on any divergence.
_SSID_STEM_METACHARS = set(".^$*+?()[]{}|\\%")
_SSID_PATTERN_FP_HOLD_STEMS: frozenset[str] = frozenset({
    "lpr",      # License Plate Reader generic acronym (MAC-517)
    "digital",  # 7-char generic prefix; survives as magnet (MAC-752)
    "flock",    # 5-char generic English/German word (MAC-752)
    "msab",     # 4-char acronym; matches williamsabc / WPAHMSABMVA (MAC-752)
    "xry",      # 3-char acronym; matches base64xryrandom (MAC-752)
    "stingray", # 9-char Harris IMSI-catcher product + generic English word
                # (CEO Finding B, 2026-08-20; held on defense-in-depth
                # grounds rather than risk an unanchored bare-stem FP)
    "pineapple",# 9-char Hak5 product + common English noun; ships bare with
                # `Hak5 hacking_tool`, so `Pineapple Cafe WiFi` reads as an
                # attack tool. Co-branches `hak5` / `wifipineapple` are on
                # the SAME row 44726 and drop WITH it: Hak5 ships in no
                # v1.8.0 feed. Cost accepted; MAC-765 owns restoration
                # (CEO ruling Option A, MAC-761, 2026-08-20)
})
_SSID_STEM_MIN_LEN = 3


def _strict_base(s: str) -> str:
    """Strict leading-literal run of ``s`` (no extension), stops at the first
    metachar.  Used to identify the FP-hold-checked base of each branch
    regardless of how far the post-base extension would otherwise reach.
    MAC-752.
    """
    out: list[str] = []
    for ch in s:
        if ch in _SSID_STEM_METACHARS:
            break
        out.append(ch)
    return "".join(out).strip()


def _parse_stems(s: str) -> list[str] | None:
    """Walk ``s`` collecting emitted stems.

    Skips `[_-]?` optional delimiter blocks.  Splits on mandatory
    `(a|b|...)` groups (each branch must be a literal run; any branch
    whose own leading literal is truncated by an internal metachar
    returns None — the row is FP-held, because that branch is not
    safely renderable as a substring stem).

    Returns the list of emitted stems (one per branch in the cartesian
    product of nested alternations), or ``None`` when FP-held.  MAC-752.
    """
    stems: list[str] = [""]
    pos = 0
    n = len(s)
    while pos < n:
        ch = s[pos]
        if ch == "(":
            # Find matching close paren (depth-balanced).
            depth = 0
            close: int | None = None
            for i in range(pos, n):
                if s[i] == "(":
                    depth += 1
                elif s[i] == ")":
                    depth -= 1
                    if depth == 0:
                        close = i
                        break
            if close is None:
                break
            # Optional group `(...)`?  Skip the whole thing.
            if close + 1 < n and s[close + 1] == "?":
                pos = close + 2
                continue
            inner = s[pos + 1:close]
            # Non-capturing / flag group `(?:...)` or `(??...)`?  Skip the
            # body but stay at the close paren so trailing content can still
            # attach.
            if inner.startswith("?"):
                pos = close + 1
                continue
            if "|" in inner:
                # Mandatory alternation: split into branches and concat.
                branches = inner.split("|")
                new_stems: list[str] = []
                for prefix in stems:
                    for branch in branches:
                        branch_chars: list[str] = []
                        has_metachar = False
                        for c in branch:
                            if c in _SSID_STEM_METACHARS:
                                has_metachar = True
                                break
                            branch_chars.append(c)
                        # Branch whose own leading literal is truncated by
                        # an internal metachar: the bare prefix is a magnet.
                        # The CEO allowed "render fully OR FP-hold the row"
                        # (Finding B).  We render fully (concat the prefix
                        # with the rest of the branch up to the next
                        # metachar) — the truncated bare prefix never ships.
                        # But if the branch has its OWN internal metachar
                        # beyond the leading run (e.g. `wifi[_-]?pineapple`
                        # → leading `wifi`, internal `[`), the branch
                        # stem after the prefix concatenation would itself
                        # truncate.  We continue past the metachar by
                        # walking through optional blocks the same way the
                        # main loop does; if that walk also hits a
                        # non-optional metachar, we return None below.
                        if has_metachar:
                            # Try to render the branch FULLY: walk past
                            # `[_-]?` optional blocks inside the branch.
                            full_branch_chars: list[str] = list(prefix)
                            bpos = 0
                            bn = len(branch)
                            while bpos < bn:
                                bc = branch[bpos]
                                if bc == "[":
                                    bend = branch.find("]", bpos)
                                    if bend == -1:
                                        return None
                                    binner = branch[bpos + 1:bend]
                                    if (
                                        set(binner) <= {"_", "-"}
                                        and bend + 1 < bn
                                        and branch[bend + 1] == "?"
                                    ):
                                        bpos = bend + 2
                                        continue
                                    else:
                                        return None
                                elif bc in _SSID_STEM_METACHARS:
                                    return None
                                full_branch_chars.append(bc)
                                bpos += 1
                            full_branch = "".join(full_branch_chars).strip()
                            if not full_branch:
                                return None
                            new_stems.append(full_branch)
                        else:
                            branch_stem = "".join(branch_chars).strip()
                            if not branch_stem:
                                return None
                            new_stems.append(prefix + branch_stem)
                stems = new_stems
                pos = close + 1
                continue
            # Mandatory group without alternation: skip the body.
            pos = close + 1
            continue
        if ch == "[":
            end = s.find("]", pos)
            if end == -1:
                break
            inner = s[pos + 1:end]
            if set(inner) <= {"_", "-"} and end + 1 < n and s[end + 1] == "?":
                pos = end + 2  # skip the `[_-]?` block
                continue
            break  # required `[abc]` bracket — leading-literal run ends here
        if ch in _SSID_STEM_METACHARS:
            break
        # Literal char — extend every emitted stem.
        for i in range(len(stems)):
            stems[i] = stems[i] + ch
        pos += 1
    return stems


def _ssid_pattern_to_substring(value: str) -> list[str] | None:
    """Convert an ``ssid_pattern`` value to Lynceus-0.9.2 substring(s).

    Returns the list of case-insensitive substrings to emit, or ``None`` when
    the row is FP-held and must drop to the ``ssid_pattern_fp_hold`` bin.
    See the module comment above for the deterministic rule.
    """

    s = value.strip()
    if s.startswith("(?i)"):
        s = s[4:]
    if s.startswith("^"):
        s = s[1:]

    # Detect a LEADING alternation `(a|b|...)`.  We split into branches
    # and re-parse each branch against the post-group remainder, so the
    # post-group `[_-]?` blocks and mandatory `(...)` groups apply to
    # every emitted stem.
    branches: list[str] | None = None
    post_group_start = len(s)
    if s.startswith("("):
        depth = 0
        close: int | None = None
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
            # Only a simple capturing alternation `(a|b|...)` splits; a
            # non-capturing / flag group `(?...)` or a group with no `|`
            # falls through to single-stem processing.
            if inner and not inner.startswith("?") and "|" in inner:
                branches = inner.split("|")
                post_group_start = close + 1

    if branches is not None:
        # Leading alternation path: each branch is parsed against the
        # post-group remainder.  Branches whose STRICT BASE is in the FP
        # hold set are skipped at the row level — one held base holds the
        # whole row.
        out: list[str] = []
        for branch in branches:
            stems = _parse_stems(branch + s[post_group_start:])
            if stems is None:
                return None
            sb = _strict_base(branch)
            if sb.lower() in _SSID_PATTERN_FP_HOLD_STEMS:
                return None
            if len(sb) < _SSID_STEM_MIN_LEN:
                return None
            out.extend(stems)
        return out or None

    # Single-stem path: parse the whole string.  FP-hold check is on the
    # strict base of the WHOLE string so the MAC-517 `lpr` disposition
    # continues to hold for `lpr[_-]?cam.*` regardless of how far the
    # `[_-]?` extension reaches.
    stems = _parse_stems(s)
    if stems is None:
        return None
    sb = _strict_base(s)
    if sb.lower() in _SSID_PATTERN_FP_HOLD_STEMS:
        return None
    if len(sb) < _SSID_STEM_MIN_LEN:
        return None
    return stems or None


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

    # CP51 (§4.4, MAC-517) — holder for the converted ssid_pattern substring(s),
    # set by the ssid_pattern gate below and consumed at the survivor branch.
    ssid_substrings: list[str] | None = None
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
    # §4.4 CP51 (MAC-517) — ssid_pattern MAP → Lynceus 0.9.2 substring. Convert
    # to the leading-literal substring(s); a None result is an FP-hold and drops
    # to `ssid_pattern_fp_hold`. Survivors flow through the confidence / source /
    # geo gates below (a low-confidence or excluded-source ssid_pattern row still
    # attributes to the more specific gate, as for every other type). Mirror in
    # coverage_matrix.py::_assign_drop_bin (the `_reconcile` cross-check halts on
    # any divergence).
    if row.identifier_type == "ssid_pattern":
        ssid_substrings = _ssid_pattern_to_substring(row.identifier)
        if ssid_substrings is None:
            return "ssid_pattern_fp_hold", []
    # §4.4 CP13 / CP50 (MAC-420) — ble_local_name: LITERAL advertised names reach
    # the feed (exact GAP complete-local-name match; MAP entry below). TEMPLATED /
    # regex forms (vendor pattern families carrying metacharacters) stay DROPPED —
    # Lynceus v0.3 has no template/regex local-name matcher. See
    # `_ble_local_name_is_template`. Mirror in coverage_matrix.py::_assign_drop_bin
    # (the `_reconcile` map-vs-writer cross-check halts on any divergence).
    if row.identifier_type == "ble_local_name" and _ble_local_name_is_template(
        row.identifier
    ):
        return "ble_local_name", []
    # ble_characteristic + product_family_codename stay full-DROPPED (CP13).
    if row.identifier_type == "ble_characteristic":
        return "ble_characteristic", []
    if row.identifier_type == "product_family_codename":
        return "product_family_codename", []
    # §4.4 — mac_range expand or drop.
    if row.identifier_type == "mac_range":
        # Live branch (MAC-596 handback). Every active mac_range row whose
        # device_category is not 'unknown' — that is, every row that cleared
        # the §11 #13 priority gate above — falls through to this return.
        # Such rows are non-zero in the live identifiers set today; the
        # `oversized_mac_range` bin in `_meta.dropped_in_export` reflects
        # their actual count and reconciles against the count of `mac_range`
        # rows whose `device_category != 'unknown'` in the canonical DB.
        # The ≤256-entry expansion logic stays codified for a future row
        # that fits the ceiling, but no active mac_range fits today: every
        # one is an OUI-28 / OUI-36 sub-allocation vastly exceeding the
        # ceiling, so the bare `oversized_mac_range` drop is the only path
        # actually exercised. Reopening `mac_range` as a promote path is a
        # CEO-class decision and is explicitly NOT being requested here.
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
    # §4.4 (MAC-359 CEO Ruling 3; absorbed at MAC-388) — generic/reserved
    # BLE-UUID suppression. Sits AFTER the §4.4 type-drops and BEFORE the
    # confidence/source gates: the drop reason is structural (a reserved,
    # non-discriminating UUID value), not confidence- or source-based, so it
    # must attribute regardless of those. `coverage_matrix.py::_assign_drop_bin`
    # carries the identical gate at the identical priority (reconcile parity).
    if row.identifier in GENERIC_RESERVED_UUID_SUPPRESS:
        return "generic_reserved_uuid", []
    # §8.4 / §11 #12 — Pi self-exclude OUI list (high-confidence file only).
    if (
        apply_pi_self_exclude
        and row.identifier_type == "oui"
        and row.identifier in PI_SELF_EXCLUDE_OUIS
    ):
        return "self_exclude_oui", []
    # §7.5 — confidence floor. A NULL confidence (e.g. the Gate-1 v3 / MAC-334
    # promotions staged without a §8.2 ceiling assignment) is treated as below
    # ANY floor and binned `below_confidence_threshold`. The None-guard is the
    # gate-level fix (NOT a load-time coercion): it excludes NULL-confidence
    # rows from the confidence-gated JSON exports WITHOUT mutating
    # `row.confidence`, so the rich-import CSV keeps the confidence column
    # faithful to the DB (empty/NULL, not `0`). This mirrors
    # `coverage_matrix.py`'s NULL→0 load-coercion at the *classification*
    # layer — both modules bin a NULL-confidence row as
    # `below_confidence_threshold`, so `_reconcile` agrees (it halts on any
    # divergence). MAC-336.
    if row.confidence is None or row.confidence < confidence_threshold:
        return "below_confidence_threshold", []
    # CP19 (§7.5) — high-conf-only source_type exclusion. A row reaching this
    # gate has cleared every prior static filter (incl. CP18's ≥70 floor for
    # the high-conf file); the CP19 bin captures rows excluded for lack of a
    # §8.3 cross-band corroboration anchor. Standard export (≥30 floor)
    # passes inferred/crowdsourced through. Mirrors
    # `coverage_matrix.py::_assign_drop_bin`'s identical late-priority gate.
    if apply_excluded_source_type and row.source_type in EXCLUDED_SOURCE_TYPES:
        # CP39 §7.5 carve-out: rows from named Flock-hunt project sources
        # bypass the EXCLUDED_SOURCE_TYPES gate. See module-level constant
        # CP39_FLOCK_HUNT_CARVEOUT_URL_PATTERNS for the named set.
        if not _cp39_flock_hunt_carveout(row.source_url):
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
    # CP51 (§4.4, MAC-517) — a surviving ssid_pattern row emits one entry per
    # converted substring (usually one; two for the single leading-alternation
    # SPLIT). `pattern` is the substring actually shipped, and `argus_record_id`
    # hashes `("ssid_pattern"|substring)` so each emitted pattern is a distinct,
    # re-run-stable record (a SPLIT must not collide two records on the source
    # regex). Cross-row NOCASE dedup of these substrings happens once, in
    # `_build_export`, since it needs whole-file state the per-row classifier
    # lacks.
    if ssid_substrings is not None:
        return None, [
            TalosEntry(
                pattern=substring,
                pattern_type=pattern_type,
                description=description,
                argus_record_id=_sar10_hash("ssid_pattern", substring),
            )
            for substring in ssid_substrings
        ]
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


def _classify_emitted_key_collision(rows: list[ActiveRow]) -> str:
    """Diagnostic label for a duplicate emitted-key group (MAC-570 taxonomy).

    Classification is DIAGNOSTIC ONLY. It never participates in the rejection
    predicate — see ``_assert_emitted_keys_unique``.
    """

    if len({r.device_category for r in rows}) > 1:
        return "CATEGORY_CONTRADICTION"
    manufacturers = {r.manufacturer for r in rows}
    if None in manufacturers and len(manufacturers) > 1:
        return "ATTRIBUTED_VS_NULL_VENDOR"
    return "DEDUP_MISS"


def _assert_emitted_keys_unique(
    *,
    file_label: str,
    emitted: list[tuple[ActiveRow, TalosEntry]],
) -> None:
    """MAC-611 gate 2 — no duplicate emitted key at all (remediates MAC-570).

    The predicate is literal and unconditional::

        len(entries) == len({e.argus_record_id for e in entries})
        len(entries) == len({(e.pattern_type, e.pattern) for e in entries})

    BOTH halves are load-bearing:

    * ``argus_record_id`` is the Lynceus *upsert* key (SAR-10 over
      ``{identifier_type}|{normalized_identifier}``). Two entries sharing it
      race on ingest and last-write-wins decides the shipped row.
    * ``(pattern_type, pattern)`` is the Lynceus *wire-match* key. A §4.4 alias
      (CP21 ``ble_company_id -> ble_manufacturer_id``, CP21 ``ble_service_uuid
      -> ble_uuid``) collapses distinct Argus identifier_types onto one wire
      key while SAR-10 *correctly* assigns them different ``argus_record_id``
      values. An id-only guard is blind to that class — the live
      ``ble_manufacturer_id|0x0019`` pair (ids 4925, 35776) is the armed
      tripwire.

    This gate **HALTS. It never collapses.** Collapsing duplicates to the last
    entry is the defect, not the repair: it moves last-write-wins out of the
    consumer and into the exporter, and ships the contradiction silently.
    Emitting fewer entries than were built must raise.

    Originating canonical row ids are carried for *diagnostics only*. They never
    waive multiplicity — two duplicate entries produced by a single row halt
    exactly as two entries from two rows do.

    Scope note (CEO amendment, MAC-611): the predicate is scoped to EMITTED
    entries, not to canonical ``(identifier_type, identifier)`` groups. A shared
    canonical pair is only a contradiction when the identifier_type carries
    device identity. Class-valued types — ``equipment_class_code`` today, where
    one FCC equipment class legitimately spans many grantees — share by
    construction, and a canonical-scope predicate would fire false halts on
    correct data. Do not widen this predicate across identifier types without
    first proving the type asserts identity.
    """

    by_record_id: dict[str, list[tuple[ActiveRow, TalosEntry]]] = {}
    by_wire_key: dict[tuple[str, str], list[tuple[ActiveRow, TalosEntry]]] = {}
    for row, entry in emitted:
        by_record_id.setdefault(entry.argus_record_id, []).append((row, entry))
        by_wire_key.setdefault((entry.pattern_type, entry.pattern), []).append(
            (row, entry)
        )

    dup_ids = {k: v for k, v in by_record_id.items() if len(v) > 1}
    dup_wire = {k: v for k, v in by_wire_key.items() if len(v) > 1}
    if not dup_ids and not dup_wire:
        return

    # One line per colliding group, keyed on the wire key so a §4.4 alias
    # collapse and an upsert-key collision report as one finding when they
    # coincide. Groups are union-ordered and deterministic.
    groups: dict[tuple[str, str], list[tuple[ActiveRow, TalosEntry]]] = dict(dup_wire)
    for pairs in dup_ids.values():
        key = (pairs[0][1].pattern_type, pairs[0][1].pattern)
        groups.setdefault(key, by_wire_key[key])

    redundant = sum(len(v) - 1 for v in groups.values())
    lines: list[str] = []
    classes: dict[str, int] = {}
    for (pattern_type, pattern), pairs in sorted(groups.items()):
        rows = [r for r, _ in pairs]
        label = _classify_emitted_key_collision(rows)
        classes[label] = classes.get(label, 0) + 1
        record_ids = sorted({e.argus_record_id for _, e in pairs})
        lines.append(
            f"- {','.join(record_ids)}  {pattern_type}|{pattern}  "
            f"ids={sorted(r.id for r in rows)}  {label}"
        )
    summary = "; ".join(f"{n} {label}" for label, n in sorted(classes.items()))
    raise Halt(
        f"HALT duplicate_emitted_key (MAC-611/{file_label}): {len(groups)} "
        f"duplicate emitted-key groups; {redundant} redundant entries; "
        f"{summary}. The gate HALTS and never collapses — resolve the "
        "contradiction canonically (supersession / category correction), then "
        "re-export.\n" + "\n".join(lines)
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
    record_count: int,
    ssid_pattern_emission: dict[str, int],
) -> dict[str, Any]:
    """Build the §7.5 ``_meta`` block (CP7 augments with scope filter).

    ``record_count`` is the true feed record count (``len(entries)``). For every
    identifier_type except ``ssid_pattern`` this equals the row-based survivor
    count ``source_record_count − sum(bins)``; CP51 (§4.4, MAC-517) ssid_pattern
    substring conversion can fan out (leading-alternation SPLIT) or collapse
    (NOCASE dedup), so the two diverge by exactly
    ``split_expansions − nocase_deduped`` — recorded in ``ssid_pattern_emission``
    for the coverage-report cross-check.
    """

    return {
        "argus_version": str(schema_version),
        "exported_at": exported_at,
        "record_count": record_count,
        "confidence_threshold": confidence_threshold,
        "geographic_scope_filter": list(geographic_scope_filter),
        "argus_run_id": argus_run_id,
        "source_record_count": source_record_count,
        "dropped_in_export": bins,
        # CP51 (§4.4, MAC-517) — ssid_pattern substring-emission accounting.
        "ssid_pattern_emission": ssid_pattern_emission,
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
        # §4.4 (MAC-359; absorbed at MAC-388) — generic/reserved BLE-UUID
        # value-suppression bin.
        "generic_reserved_uuid": 0,
        "ssid_pattern": 0,
        # CP51 (§4.4, MAC-517) — ssid_pattern rows whose converted substring is
        # FP-held (generic/short stem). Distinct from `ssid_pattern`, which now
        # only fires if a legacy hard-drop path is ever reintroduced (0 today).
        "ssid_pattern_fp_hold": 0,
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
        # "ble_service_uuid" removed at MAC-359 (absorbed MAC-388) — now
        # MAP→ble_uuid (CP21), no drop bin.
        # "ble_company_id" removed at MAC-360 / CP47 — now MAP→ble_manufacturer_id
        # (CP21), no drop bin.
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
        # CP35 (mig-0028 / MAC-255) — NDPP §4.4 ratified DROP. Identity-keyed
        # per CP42 §2 (MAC-300) supersedure of CP35 §215's descriptive-bin_label
        # sub-decision; rationale lives in DROPPED_REASONS_RATIONALE.
        "network_discovery_protocol_pattern": 0,
        # CP42 §1 (MAC-300) — imei_tac §4.4 consumer-side DROP. See
        # DROPPED_REASONS_RATIONALE for the GSMA Type Allocation Code
        # registry-metadata rationale.
        "imei_tac": 0,
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
        # MAC-611 gate 1 — BLE registry-type integrity, strictly BEFORE
        # `_classify_row` so a SIG member-UUID value never reaches the CP21 §4.4
        # `ble_company_id -> ble_manufacturer_id` MAP.
        _assert_ble_registry_type(row)
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
    # MAC-611 — each surviving entry keeps its originating canonical row so the
    # emitted-key gate can name the colliding ids. The row half is diagnostic
    # context only; it never participates in the rejection predicate.
    emitted: list[tuple[ActiveRow, TalosEntry]] = []
    surviving_ssid_row_ids: set[int] = set()
    for row, entry in survivor_rows:
        if _passes_geographic_scope(
            row,
            geographic_scope_filter=geographic_scope_filter,
            is_high_confidence=is_high_confidence,
        ):
            emitted.append((row, entry))
            if entry.pattern_type == "ssid_pattern":
                surviving_ssid_row_ids.add(row.id)
        else:
            bin_assignments[row.id] = "geographic_scope_mismatch"
            bins["geographic_scope_mismatch"] += 1
    # CP51 (§4.4, MAC-517) — cross-row NOCASE dedup of ssid_pattern substrings.
    # Lynceus matches ssid_pattern case-insensitively, so `flock` / `Flock` /
    # `FLOCK` (three distinct canonical rows) collapse to one feed record. Done
    # here (whole-file state) rather than in the per-row classifier. Kept
    # deterministic by preserving survivor order (rows are id-ordered) and
    # keeping the first occurrence of each lowercased substring.
    ssid_entries_pre_dedup = sum(
        1 for _, e in emitted if e.pattern_type == "ssid_pattern"
    )
    deduped: list[tuple[ActiveRow, TalosEntry]] = []
    seen_ssid: set[str] = set()
    nocase_deduped = 0
    for row, entry in emitted:
        if entry.pattern_type == "ssid_pattern":
            key = entry.pattern.lower()
            if key in seen_ssid:
                nocase_deduped += 1
                continue
            seen_ssid.add(key)
        deduped.append((row, entry))
    emitted = deduped
    # MAC-611 gate 2 — final emitted-key uniqueness. Placement is load-bearing:
    # AFTER `_reconcile`, the CP7 geographic filter and the intentional CP51
    # `ssid_pattern` NOCASE collapse (so the only surviving multiplicity is
    # unintended), and BEFORE `_build_meta` and payload serialization (so no
    # duplicate key can be counted into `_meta` or written to disk).
    _assert_emitted_keys_unique(file_label=file_label, emitted=emitted)
    entries: list[TalosEntry] = [entry for _, entry in emitted]
    # SPLIT expansion count: emitted ssid substrings (pre-dedup) beyond one per
    # surviving ssid row — i.e. the leading-alternation fan-out (only `(msab|xry)`
    # today). record_count is the true feed record count (entry-based); it differs
    # from the row-based survivor count `len(rows) − sum(bins)` by exactly
    # `split_expansions − nocase_deduped`, surfaced in `_meta.ssid_pattern_emission`
    # for the coverage-report cross-check.
    split_expansions = ssid_entries_pre_dedup - len(surviving_ssid_row_ids)
    ssid_pattern_emission = {
        "surviving_ssid_rows": len(surviving_ssid_row_ids),
        "substring_records": ssid_entries_pre_dedup - nocase_deduped,
        "split_expansions": split_expansions,
        "nocase_deduped": nocase_deduped,
    }
    meta = _build_meta(
        schema_version=schema_version,
        confidence_threshold=confidence_threshold,
        geographic_scope_filter=geographic_scope_filter,
        argus_run_id=argus_run_id,
        exported_at=exported_at,
        source_record_count=len(rows),
        bins=bins,
        record_count=len(entries),
        ssid_pattern_emission=ssid_pattern_emission,
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
    matrix_sha256: str,
    coverage_matrix_report: dict[str, Any],
) -> str:
    """Stitch the §6 Phase 5 #4 + §9 item 9 coverage_report.md.

    Embeds the MAC-45 matrix verbatim as the matrix section seed, then layers
    the §9 item 9 drop tally with full reconciliation against both Talos
    files' ``_meta.dropped_in_export`` blocks.

    ``matrix_sha256`` is the provenance anchor for the embedded matrix and is
    a CONTENT hash, not a commit cite (MAC-703). The line it feeds previously
    read "(commit ``6853780``)"; that sha stopped resolving at the MAC-610
    history rewrite, so a shipped artifact whose job is to document provenance
    was carrying a provenance claim that no longer resolved. A content hash
    survives a rewrite because it is a property of the bytes, not of the
    object graph. The caller hashes the raw file bytes rather than
    ``matrix_md.encode()`` so the printed value matches ``sha256sum`` even if
    the file ever picks up CRLF, which ``Path.read_text`` would silently
    translate away.
    """

    standard_meta = standard_payload["_meta"]
    high_meta = high_payload["_meta"]
    standard_bins = standard_meta["dropped_in_export"]
    high_bins = high_meta["dropped_in_export"]
    source_count = len(rows)

    def fmt_bin_table(bins: dict[str, int], label: str, threshold: int) -> str:
        bin_rows = [
            ("unknown_category (§11 #13)", bins["unknown_category"]),
            ("generic_reserved_uuid (§4.4 MAC-359)", bins["generic_reserved_uuid"]),
            ("procurement_only (§11 #14)", bins["procurement_only"]),
            ("device_fingerprint (§4.4)", bins["device_fingerprint"]),
            ("ssid_pattern (§4.4)", bins["ssid_pattern"]),
            ("ssid_pattern_fp_hold (§4.4 CP51 MAC-517)", bins["ssid_pattern_fp_hold"]),
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
            # ble_service_uuid removed at MAC-359 (absorbed MAC-388) — now MAP→ble_uuid (CP21); no drop bin.
            # ble_company_id removed at MAC-360 / CP47 — now MAP→ble_manufacturer_id (CP21); no drop bin.
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
            # MAC-181 / migration 0023 — CP28(c) Wave H desktop-axis cluster.
            (
                "windows_installer_productcode_vendor_registered (§4.4 CP28c)",
                bins["windows_installer_productcode_vendor_registered"],
            ),
            (
                "windows_com_clsid_vendor_registered (§4.4 CP28c)",
                bins["windows_com_clsid_vendor_registered"],
            ),
            # CP29 (migration 0024) — Wave I vendor cloud-infrastructure cluster.
            ("vendor_controlled_hostname (§4.4 CP29)", bins["vendor_controlled_hostname"]),
            ("vendor_cloud_endpoint_url (§4.4 CP29)", bins["vendor_cloud_endpoint_url"]),
            (
                "vendor_controlled_hostname_deprecated (§4.4 CP29)",
                bins["vendor_controlled_hostname_deprecated"],
            ),
            # CP31 (migration 0025) — FCC EAS identifier-type cluster.
            ("fcc_grantee_code (§4.4 CP31)", bins["fcc_grantee_code"]),
            ("equipment_class_code (§4.4 CP31)", bins["equipment_class_code"]),
            # CP35 (mig-0028 / MAC-255) — NDPP ratified DROP. Identity-keyed
            # per CP42 §2 (MAC-300) supersedure of CP35 §215.
            (
                "network_discovery_protocol_pattern (§4.4 CP35)",
                bins["network_discovery_protocol_pattern"],
            ),
            # CP42 §1 (MAC-300) — imei_tac §4.4 consumer-side DROP.
            ("imei_tac (§4.4 CP42 §1)", bins["imei_tac"]),
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
        payload = standard_payload if label == "argus_export.json" else high_payload
        emitted = len(payload["entries"])
        survivor_rows = source_count - total
        # CP51 (§4.4, MAC-517) — feed record count is entry-based; it diverges
        # from the row-based survivor count by the ssid_pattern SPLIT / NOCASE
        # fan-out, so reconciliation is `source − dropped + split − dedup = entries`.
        emission = payload["_meta"]["ssid_pattern_emission"]
        split_expansions = emission["split_expansions"]
        nocase_deduped = emission["nocase_deduped"]
        reconciled = survivor_rows + split_expansions - nocase_deduped
        check = (
            "✅"
            if reconciled == emitted == payload["_meta"]["record_count"]
            else "❌"
        )
        lines.append(f"| **sum(dropped_in_export)** | **{total}** |")
        lines.append(f"| **survivor rows** (source − dropped) | **{survivor_rows}** |")
        lines.append(
            f"| ssid_pattern SPLIT expansions (+) | +{split_expansions} |"
        )
        lines.append(
            f"| ssid_pattern NOCASE dedup (−) | −{nocase_deduped} |"
        )
        lines.append(f"| **entries.length** (feed records) | **{emitted}** |")
        lines.append(
            f"| **reconciliation** | **{source_count} − {total} + "
            f"{split_expansions} − {nocase_deduped} = {reconciled}** {check} |"
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
        "UUID5 over the active-set fingerprint; re-runs on unchanged DB state produce the "
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
        "1. **`argus_export.json`**: operational alert feed. Minimal entry shape "
        "`{pattern, pattern_type, description, argus_record_id}`. CP7 "
        "`geographic_scope_filter` applied; CP8 ≤80-char flat description applied; "
        "severity owned operator-side per CP8 sub-B. Sized for low-bandwidth / "
        "streaming / alert-oriented ingest."
    )
    md_parts.append(
        "2. **`argus_export.csv`**: rich-import feed. Full canonical row shape "
        "with 15 columns including `argus_record_id` (SAR-10), `description` "
        "(CP8 flat, byte-identical to the JSON-feed `description` via shared "
        "`_format_description`), `first_seen`, `last_verified`. Unfiltered: all "
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
        "- **§11 #1 (no fabrication)**: every entry, drop tally, and bin count is "
        "derived from `db/argus.db` rows + the MAC-45 `coverage_matrix_report.json` "
        "drop_assignments map; no synthetic values inserted; no fallback heuristics."
    )
    md_parts.append(
        "- **§11 #6 (read-only)**: `PRAGMA query_only = ON` set on the connection. "
        "Zero outbound HTTP. No staging-table writes."
    )
    md_parts.append(
        "- **§11 #7 (provenance carry-through)**: every entry's `argus_record_id` "
        "is the `identifiers.id` value; underlying provenance (`source_url`, "
        "`source_excerpt`) lives unchanged on the cited row. The CSV export carries "
        "the full provenance fields."
    )
    md_parts.append(
        "- **§11 #11 (halt-the-line)**: drop-tally mismatch vs MAC-45 `drop_assignments` "
        "map is a halt; description-overflow (>80 char) is a halt; §4.4 / §4.5 "
        "schema drift is a halt. Halts at HB36: 0."
    )
    md_parts.append(
        "- **§11 #12 (Pi self-exclude OUI)**: `b8:27:eb`, `dc:a6:32`, `e4:5f:01`, "
        "`28:cd:c1` ban applied to `argus_export_high_confidence.json`; "
        "tally bin `self_exclude_oui` populated. (HB36: 0 active Pi OUI rows; "
        "guard is in place for any future Phase-5 reopening.)"
    )
    md_parts.append(
        "- **§11 #13 (unknown-category Talos-banned)**: every row with "
        "`device_category='unknown'` lands in the `unknown_category` bin and never "
        "appears in either Talos JSON file."
    )
    md_parts.append(
        "- **§11 #14 (procurement-only Lynceus-banned)**: defense-in-depth gate; the "
        "`identifiers` table cannot hold a `source_type='procurement'` row that lacks "
        "an identifier per §4.1, but the gate is wired regardless."
    )
    md_parts.append(
        "- **CP7 (geographic_scope export-time filter)**: applied AFTER static "
        "MAC-45 reconciliation as a runtime parameter. `global` passes "
        "unconditionally; ISO-code matches against the filter pass; `unknown` / "
        "NULL passes the standard export but fails the high-confidence export. "
        "Default filter = `[\"US\"]`."
    )
    md_parts.append(
        "- **CP19 (§7.5 source_type exclusion on high-conf export)**: "
        "`source_type IN ('inferred', 'crowdsourced')` is excluded from "
        "`argus_export_high_confidence.json` regardless of confidence value. "
        "Single-source `inferred`/`crowdsourced` rows lack a §8.3 cross-band "
        "corroboration anchor; tally bin `excluded_source_type` captures the "
        "drop attribution. Standard export retains these rows for "
        "wider-net rich-import consumers."
    )
    md_parts.append(
        "- **CP8 (description format + severity reframe)**: flat `{vendor} "
        "{device_category}` ≤80 chars (CP8 sub-correction A); fallbacks "
        "`\"{vendor} unknown\"` and `\"Unattributed identifier\"`. "
        "`severity` field dropped from export shape (CP8 sub-correction B); "
        "owned operator-side via Lynceus's `severity_overrides.yaml`."
    )
    md_parts.append(
        "- **SAR-10 (`argus_record_id`)**: 16-hex-char SHA-256 prefix of "
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
        f"`extraction_outputs/mac45/coverage_matrix.md` (sha256 `{matrix_sha256}`). "
        "Verify with `sha256sum extraction_outputs/mac45/coverage_matrix.md`. It is "
        "embedded here verbatim per §9 item 3 ('coverage_report.md exists and shows "
        "category coverage with honest gap analysis'); the upstream module owns the "
        "matrix derivation."
    )
    md_parts.append("")
    md_parts.append("```markdown")
    md_parts.append(matrix_md.rstrip())
    md_parts.append("```")
    md_parts.append("")
    md_parts.append("## §9 item 9: Dropped from Talos export (Step-6 reconciliation)")
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
        f"and halts on any mismatch vs the MAC-45 map; no silent re-tally."
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
        f"{json.dumps(standard_bins, sort_keys=True)} → survivor rows "
        f"{source_count - sum(standard_bins.values())} (reconciles {source_count}); "
        f"feed records {standard_meta['record_count']} after CP51 ssid_pattern "
        f"emission {json.dumps(standard_meta['ssid_pattern_emission'], sort_keys=True)}."
    )
    md_parts.append(
        f"- MAC-45 `drop_tally_high_confidence.bins` = "
        f"{json.dumps(mac45_high['bins'], sort_keys=True)} → survivors "
        f"{mac45_high['survivors']} (reconciles {mac45_high['reconciles']})."
    )
    md_parts.append(
        f"- Step-6 `argus_export_high_confidence.json._meta.dropped_in_export` = "
        f"{json.dumps(high_bins, sort_keys=True)} → survivor rows "
        f"{source_count - sum(high_bins.values())} (reconciles {source_count}); "
        f"feed records {high_meta['record_count']} after CP51 ssid_pattern "
        f"emission {json.dumps(high_meta['ssid_pattern_emission'], sort_keys=True)}."
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
        "Tier 4 read remains open for CP5 surface; quantified row counts per "
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
    # Hash the raw bytes, not `matrix_md`: the value is printed into
    # coverage_report.md for an operator to check with `sha256sum` (MAC-703).
    matrix_sha256 = hashlib.sha256(coverage_matrix_md_path.read_bytes()).hexdigest()

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
        matrix_sha256=matrix_sha256,
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
        default=None,
        help=(
            "CP7 export-time filter on identifiers.geographic_scope. "
            "Comma-separated ISO codes (e.g. 'US' or 'NL,AU'). Default: 'US'."
        ),
    )
    parser.add_argument(
        "--continent-filter",
        type=str,
        default=None,
        help=(
            "Roll a continent up to its ISO-3166 alpha-2 children and filter on "
            "those (MAC-742). Comma-separated, from "
            f"{{{', '.join(sorted(CONTINENT_ISO3166_ALPHA2))}}}. Expanded at "
            "argument-parse time; the stored column is never compared against a "
            "continent token. Given alone it REPLACES the 'US' default; combined "
            "with --geographic-scope-filter the two are unioned. Yields 0 "
            "additional rows against canonical today -- see "
            "CONTINENT_ISO3166_ALPHA2."
        ),
    )
    args = parser.parse_args()

    scope_codes = tuple(
        part.strip()
        for part in (args.geographic_scope_filter or "").split(",")
        if part.strip()
    )
    continent_codes = tuple(
        part.strip().upper()
        for part in (args.continent_filter or "").split(",")
        if part.strip()
    )

    # `default=None` distinguishes "flag absent" from "flag present but empty".
    # Collapsing those two would make `--geographic-scope-filter ''` silently
    # export the 'US' default instead of erroring, which is the behaviour this
    # branch had before --continent-filter existed. Preserved deliberately.
    if args.geographic_scope_filter is not None and not scope_codes:
        raise SystemExit(
            "--geographic-scope-filter must contain at least one ISO code."
        )
    if args.continent_filter is not None and not continent_codes:
        raise SystemExit(
            "--continent-filter must contain at least one continent code."
        )

    if continent_codes:
        unknown = [c for c in continent_codes if c not in CONTINENT_ISO3166_ALPHA2]
        if unknown:
            raise SystemExit(
                f"--continent-filter: unknown continent code(s) {', '.join(unknown)}. "
                f"Known: {', '.join(sorted(CONTINENT_ISO3166_ALPHA2))}."
            )
        # A continent given ALONE replaces the 'US' default rather than unioning
        # with it: defaulting is not choosing, and silently keeping US in an
        # export somebody asked to scope to Europe would be a wrong feed, not a
        # generous one. An EXPLICIT --geographic-scope-filter is a choice, so
        # that one is honoured and unioned.
        scope_codes = tuple(
            sorted(set(scope_codes) | set(expand_continent_filter(continent_codes)))
        )

    geographic_scope_filter = scope_codes or DEFAULT_GEOGRAPHIC_SCOPE_FILTER
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
