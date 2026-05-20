"""MAC-192 §6.2 — apply Wave I.14a retroactive identifier promotions.

Surfaces handled in one pass:

A. §6.2-identifierrow: INSERT identifiers rows for the 113 actionable candidates
   (114 plan candidates minus 1 Wave I.13 api.dbeta.me halt per §11 #1 — see
   preflight_pragma.md). Includes:
     - 2 academic (sid=41 GainSec, sid=43 DroneSecurity)
     - 111 community (sid 16/18/20/21/22/23/24/26/28/30/32)
     - 0 wave_i_13 (api.dbeta.me halted)

   For each: verify raw_observations row still exists + promoted_identifier_id IS
   NULL, resolve manufacturer via canonical_name+aliases (halt if not found),
   route Honeywell candidates to staging file (do NOT insert), INSERT identifier
   with source_type inherited from sources.source_type, confidence = upper bound
   of proposed_confidence_band, source_url + source_excerpt chained from
   raw_observations, then UPDATE raw_observations.promoted_identifier_id.

   Idempotent: skip if an identifier already exists matching
   (identifier, identifier_type) with `mac192` in notes.

B. §6.2-android: append 15 Flock device-side Android package names to
   `manufacturers.notes.android_packages[]` for Flock Safety. Pattern matches
   Phase 5 §5.5 shape per dispatch.

C. §6.2-apisurfaces: append 12 Flock Collins admin REST paths to
   `manufacturers.notes.api_surfaces.collins[]` and 15 Flock-targeted CVEs to
   `manufacturers.notes.cve_inventory[]` for Flock Safety.

D. §6.2-typevocabgap: append 10 community-repo type-vocab-gap items to
   `manufacturers.notes.type_vocabulary_gap_observations[]` for the routed
   manufacturers (Parrot wifi_vendor_specific_oui + various DJI behavioral
   descriptors).

Discipline:
- Wrap each Class batch in its own transaction. On exception → rollback.
- Provenance per §11 #7: every identifier INSERT chains to raw_observations.id;
  every notes-entry carries integration_dispatch='MAC-192' + cp_anchor +
  integration_at_utc.
- Confidence per §11 #8: proposed_confidence_band upper bound, no drift.
- device_category mapping: raw_obs.candidate_category → identifiers 12-value
  enum per existing canonical convention (surveillance_camera→unknown,
  fleet_router→unknown, gunshot_sensor→gunshot_detect, body_cam_trigger →
  body_cam, in_car_camera → body_cam, forensics → hacking_tool).
"""

from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path

DB = Path("/home/kev/argus/db/argus.db")
PLAN = Path(
    "/home/kev/argus-internal/wave_i_pre_v1/wave_i_14a_canonical_remine/"
    "RECONCILIATION_PLAN_V3_FOR_PAPERCLIP_V1_4_1.json"
)
LOG = Path("/home/kev/argus/_phase_6_wave_i_14a/identifier_promotion_log.md")
HONEYWELL_STAGE = Path(
    "/home/kev/argus/_phase_6_wave_i_14a/honeywell_staged_for_phase_8.md"
)

NOW = datetime.datetime.now(datetime.UTC).isoformat()
CP_ANCHOR = "phase_6_wave_i_14a_retroactive_promotion"

# raw_observations.candidate_category -> identifiers.device_category (12-value enum)
CATEGORY_MAP = {
    "alpr": "alpr",
    "drone": "drone",
    "imsi_catcher": "imsi_catcher",
    "body_cam": "body_cam",
    "body_cam_trigger": "body_cam",
    "in_car_camera": "body_cam",
    "police_radio": "police_radio",
    "gunshot_sensor": "gunshot_detect",
    "shotspotter": "gunshot_detect",
    "raven_gunshot_detector": "gunshot_detect",
    "surveillance_camera": "unknown",
    "fleet_router": "unknown",
    "forensics": "hacking_tool",
    "gps_tracker": "gps_tracker",
    "face_recog": "face_recog",
    "drone_detect": "drone_detect",
    "covert_cam": "covert_cam",
    "hacking_tool": "hacking_tool",
    "unknown": "unknown",
}

# Canonical-name resolver: map plan's proposed_manufacturer text -> canonical_name.
# All 14 unique 114-candidate mfrs already exact-match canonical (verified at
# preflight), so this is identity. Kept for explicit halt-on-unknown discipline.


def load_canonical_map(con: sqlite3.Connection) -> dict[str, tuple[int, str]]:
    """Return {lookup_key_lower: (mfr_id, canonical_name)} from canonical_name+aliases."""
    out: dict[str, tuple[int, str]] = {}
    for mid, canon, aliases in con.execute(
        "SELECT id, canonical_name, aliases FROM manufacturers"
    ):
        out[canon.lower()] = (mid, canon)
        if aliases:
            for a in aliases.split(","):
                a = a.strip()
                if a:
                    out.setdefault(a.lower(), (mid, canon))
    return out


def resolve_mfr(name: str, cmap: dict[str, tuple[int, str]]) -> tuple[int, str] | None:
    return cmap.get(name.lower())


def parse_notes(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {"description": raw}


def truncate200(s: str | None) -> str | None:
    if s is None:
        return None
    return s if len(s) <= 200 else s[:197] + "..."


def is_honeywell(mfr: str) -> bool:
    return mfr.lower().startswith("honeywell")


def apply_identifier_row(
    cur: sqlite3.Cursor,
    candidate: dict,
    source_origin: str,
    cmap: dict[str, tuple[int, str]],
    log: list[str],
    honeywell_log: list[str],
) -> tuple[str, int | None]:
    """Apply a single identifier-row candidate. Returns (outcome, identifier_id)."""
    raw_id = candidate["raw_obs_id"]
    proposed_type = candidate["proposed_identifier_type"]
    mfr_name = candidate["proposed_manufacturer"]
    band = candidate["proposed_confidence_band"]
    conf = band[1]  # upper bound (CP29 ceiling, no drift)
    cls = candidate.get("class", "?")
    excerpt_plan = candidate.get("evidence_excerpt") or candidate.get("excerpt") or ""

    # Honeywell stage-not-insert per dispatch envelope
    if is_honeywell(mfr_name):
        honeywell_log.append(
            f"- raw_obs_id={raw_id} | type={proposed_type} | candidate="
            f"{candidate.get('candidate_identifier','')!r} | proposed_band="
            f"{band} | class={cls} | rationale={candidate.get('rationale','')[:200]!r}"
        )
        return ("honeywell_staged", None)

    # Resolve manufacturer canonical
    resolved = resolve_mfr(mfr_name, cmap)
    if resolved is None:
        log.append(
            f"  HALT raw_obs={raw_id}: mfr='{mfr_name}' not in canonical lexicon"
        )
        return ("halt_unresolved_mfr", None)
    _mfr_id, canonical_name = resolved

    # Fetch raw_observation
    row = cur.execute(
        """SELECT id, source_id, source_url, candidate_identifier, candidate_category,
                  candidate_manufacturer, source_excerpt, promoted_identifier_id, notes
           FROM raw_observations WHERE id = ?""",
        (raw_id,),
    ).fetchone()
    if row is None:
        log.append(f"  HALT raw_obs={raw_id}: missing from raw_observations")
        return ("halt_missing_raw_obs", None)
    if row[7] is not None:
        log.append(
            f"  SKIP raw_obs={raw_id}: promoted_identifier_id already set"
            f" (id={row[7]})"
        )
        return ("skip_already_promoted", row[7])

    raw_source_url = row[2]
    raw_excerpt = row[6]
    raw_cat = row[4] or "unknown"
    candidate_identifier = candidate.get("candidate_identifier") or row[3]

    # device_category mapping
    device_cat = CATEGORY_MAP.get(raw_cat, "unknown")

    # source_type inheritance
    src_type_row = cur.execute(
        "SELECT source_type FROM sources WHERE id = ?", (row[1],)
    ).fetchone()
    if src_type_row is None:
        log.append(f"  HALT raw_obs={raw_id}: source_id={row[1]} missing in sources")
        return ("halt_missing_source", None)
    source_type = src_type_row[0]

    # Idempotency: prior MAC-192 row?
    existing = cur.execute(
        """SELECT id FROM identifiers WHERE identifier = ? AND identifier_type = ?
                  AND superseded_by IS NULL AND notes LIKE '%MAC-192%'""",
        (candidate_identifier, proposed_type),
    ).fetchone()
    if existing:
        log.append(
            f"  SKIP-IDEMPOTENT raw_obs={raw_id}: identifier already at"
            f" id={existing[0]}"
        )
        return ("skip_idempotent", existing[0])

    # Excerpt selection: prefer raw_obs excerpt; fall back to plan excerpt.
    excerpt = truncate200(raw_excerpt or excerpt_plan)

    notes_payload = {
        "integration_dispatch": "MAC-192",
        "cp_anchor": CP_ANCHOR,
        "integration_at_utc": NOW,
        "candidate_source": source_origin,
        "candidate_class": cls,
        "raw_observation_id": raw_id,
        "plan_confidence_band": band,
        "plan_rationale": candidate.get("rationale"),
        "wave_i_14a_subpass": candidate.get("subpass", "41/42"),
    }

    cur.execute(
        """INSERT INTO identifiers (
              identifier, identifier_type, device_category, manufacturer,
              model, confidence, source_url, source_type, source_excerpt,
              geographic_scope, first_seen, last_verified, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            candidate_identifier,
            proposed_type,
            device_cat,
            canonical_name,
            None,
            conf,
            raw_source_url,
            source_type,
            excerpt,
            None,
            NOW,
            NOW,
            json.dumps(notes_payload),
        ),
    )
    new_id = cur.lastrowid

    # Chain raw_observations
    cur.execute(
        "UPDATE raw_observations SET promoted_identifier_id = ? WHERE id = ?",
        (new_id, raw_id),
    )

    return ("inserted", new_id)


def section_a_identifierrow(
    con: sqlite3.Connection, plan: dict, cmap, log: list[str]
) -> dict:
    """Apply 113 identifier-row promotions (114 minus 1 halted)."""
    cur = con.cursor()
    arc = plan["academic_remine_promotion_candidates"]
    crc = plan["community_repo_remine_promotion_candidates"]
    w13 = plan["wave_i_13_dji_hikvision_endpoints"]

    candidates: list[tuple[dict, str]] = []
    for c in arc["identifiers_table_candidates"]:
        candidates.append((c, "academic_subpass_41"))
    for c in crc["identifiers_table_candidates"]:
        candidates.append((c, "community_subpass_42"))
    for c in w13.get("net_new_promotion_proposals", []):
        # api.dbeta.me lacks raw_obs_id + source_url -> halt per §11 #1
        if c.get("candidate_identifier") == "api.dbeta.me":
            log.append(
                "  HALT-SURFACE wave_i_13 api.dbeta.me: plan-input lacks"
                " source_url + raw_obs_id; held per §11 #1"
            )
            continue
        candidates.append((c, "wave_i_13_subpass_44"))

    log.append(f"\n## §6.2-identifierrow ({len(candidates)} actionable candidates)")
    counts = {
        "inserted": 0,
        "skip_already_promoted": 0,
        "skip_idempotent": 0,
        "honeywell_staged": 0,
        "halt_unresolved_mfr": 0,
        "halt_missing_raw_obs": 0,
        "halt_missing_source": 0,
    }
    honeywell_log: list[str] = []

    cur.execute("BEGIN")
    try:
        for c, origin in candidates:
            outcome, _ident_id = apply_identifier_row(
                cur, c, origin, cmap, log, honeywell_log
            )
            counts[outcome] = counts.get(outcome, 0) + 1
        con.commit()
    except Exception:
        con.rollback()
        raise

    log.append(f"\n  per-outcome counts: {counts}")
    return {"counts": counts, "honeywell_log": honeywell_log}


def section_b_android(con: sqlite3.Connection, plan: dict, cmap, log: list[str]) -> int:
    """Append 15 Flock device-side Android packages to manufacturers.notes."""
    cur = con.cursor()
    arc = plan["academic_remine_promotion_candidates"]
    proposal = next(
        (
            e
            for e in arc["enrichment_proposals"]
            if e["target"] == "manufacturers.notes.android_packages"
        ),
        None,
    )
    if not proposal:
        log.append("\n## §6.2-android: no proposal found in plan")
        return 0

    mfr_name = proposal["manufacturer"]
    resolved = resolve_mfr(mfr_name, cmap)
    if resolved is None:
        log.append(f"\n## §6.2-android HALT: mfr={mfr_name!r} not canonical")
        return 0
    mid, canonical = resolved

    log.append(
        f"\n## §6.2-android (15 Flock device-side android packages → "
        f"manufacturers.notes.android_packages; mfr_id={mid} canonical={canonical!r})"
    )

    cur.execute("BEGIN")
    try:
        row = cur.execute(
            "SELECT notes FROM manufacturers WHERE id = ?", (mid,)
        ).fetchone()
        notes = parse_notes(row[0])
        existing_pkgs = notes.get("android_packages", [])
        existing_keys = {
            (e.get("package_name"), e.get("integration_dispatch"))
            for e in existing_pkgs
        }
        appended = 0
        for pkg in proposal["packages"]:
            key = (pkg["package"], "MAC-192")
            if key in existing_keys:
                continue
            entry = {
                "package_name": pkg["package"],
                "device_role": pkg.get("device_role"),
                "raw_observation_id": pkg["raw_obs_id"],
                "evidence": proposal.get("evidence"),
                "note": proposal.get("note"),
                "integration_dispatch": "MAC-192",
                "cp_anchor": CP_ANCHOR,
                "integration_at_utc": NOW,
            }
            existing_pkgs.append(entry)
            appended += 1
        notes["android_packages"] = existing_pkgs
        cur.execute(
            "UPDATE manufacturers SET notes = ? WHERE id = ?",
            (json.dumps(notes), mid),
        )
        con.commit()
    except Exception:
        con.rollback()
        raise

    log.append(f"  appended: {appended}; post-state count: {len(existing_pkgs)}")
    return appended


def section_c_apisurfaces(
    con: sqlite3.Connection, plan: dict, cmap, log: list[str]
) -> tuple[int, int]:
    """Append 12 Collins REST paths + 15 CVEs to manufacturers.notes for Flock."""
    cur = con.cursor()
    arc = plan["academic_remine_promotion_candidates"]
    api_prop = next(
        (
            e
            for e in arc["enrichment_proposals"]
            if e["target"] == "manufacturers.notes.api_surfaces.collins"
        ),
        None,
    )
    cve_prop = next(
        (
            e
            for e in arc["enrichment_proposals"]
            if e["target"] == "manufacturers.notes.cve_inventory"
        ),
        None,
    )
    mfr_name = api_prop["manufacturer"] if api_prop else "Flock Safety"
    resolved = resolve_mfr(mfr_name, cmap)
    if resolved is None:
        log.append(f"\n## §6.2-apisurfaces HALT: mfr={mfr_name!r} not canonical")
        return (0, 0)
    mid, canonical = resolved

    log.append(
        f"\n## §6.2-apisurfaces (12 Collins REST + 15 CVEs → "
        f"manufacturers.notes for mfr_id={mid} {canonical!r})"
    )

    cur.execute("BEGIN")
    try:
        row = cur.execute(
            "SELECT notes FROM manufacturers WHERE id = ?", (mid,)
        ).fetchone()
        notes = parse_notes(row[0])

        # api_surfaces.collins
        api_appended = 0
        if api_prop:
            api_surfaces = notes.get("api_surfaces", {})
            collins = api_surfaces.get("collins", [])
            existing_paths = {
                e.get("path")
                for e in collins
                if isinstance(e, dict) and e.get("integration_dispatch") == "MAC-192"
            }
            for p in api_prop["paths"]:
                if p in existing_paths:
                    continue
                collins.append(
                    {
                        "path": p,
                        "service": api_prop.get("service"),
                        "scope": api_prop.get("scope"),
                        "redacted_count": api_prop.get("redacted_count"),
                        "redacted_rationale": api_prop.get("redacted_rationale"),
                        "integration_dispatch": "MAC-192",
                        "cp_anchor": CP_ANCHOR,
                        "integration_at_utc": NOW,
                    }
                )
                api_appended += 1
            api_surfaces["collins"] = collins
            notes["api_surfaces"] = api_surfaces

        # cve_inventory
        cve_appended = 0
        if cve_prop:
            cve_inv = notes.get("cve_inventory", [])
            existing_cves = {
                e.get("cve")
                for e in cve_inv
                if isinstance(e, dict) and e.get("integration_dispatch") == "MAC-192"
            }
            for c in cve_prop["cves"]:
                if c.get("cve") in existing_cves:
                    continue
                cve_inv.append(
                    {
                        **c,
                        "scope_class": cve_prop.get("class"),
                        "integration_dispatch": "MAC-192",
                        "cp_anchor": CP_ANCHOR,
                        "integration_at_utc": NOW,
                    }
                )
                cve_appended += 1
            notes["cve_inventory"] = cve_inv

        cur.execute(
            "UPDATE manufacturers SET notes = ? WHERE id = ?",
            (json.dumps(notes), mid),
        )
        con.commit()
    except Exception:
        con.rollback()
        raise

    log.append(
        f"  api_surfaces.collins appended: {api_appended};"
        f" cve_inventory appended: {cve_appended}"
    )
    return (api_appended, cve_appended)


def section_d_typevocabgap(
    con: sqlite3.Connection, plan: dict, cmap, log: list[str]
) -> int:
    """Append 10 type-vocab-gap observations to manufacturers.notes by routed mfr."""
    cur = con.cursor()
    crc = plan["community_repo_remine_promotion_candidates"]
    items = crc.get("enrichment_proposals_type_vocabulary_gap", [])
    log.append(f"\n## §6.2-typevocabgap ({len(items)} items)")

    # Group by mapped_manufacturer
    by_mfr: dict[str, list[dict]] = {}
    for it in items:
        by_mfr.setdefault(it["mapped_manufacturer"], []).append(it)

    total_appended = 0
    cur.execute("BEGIN")
    try:
        for mfr_name, group in by_mfr.items():
            if is_honeywell(mfr_name):
                log.append(
                    f"  STAGE-HONEYWELL mfr={mfr_name!r}: {len(group)} items not"
                    " applied (Phase 8 will pick up)"
                )
                continue
            resolved = resolve_mfr(mfr_name, cmap)
            if resolved is None:
                log.append(
                    f"  HALT mfr={mfr_name!r}: not in canonical (group of {len(group)})"
                )
                continue
            mid, canonical = resolved
            row = cur.execute(
                "SELECT notes FROM manufacturers WHERE id = ?", (mid,)
            ).fetchone()
            notes = parse_notes(row[0])
            tvg = notes.get("type_vocabulary_gap_observations", [])
            existing_keys = {
                (e.get("raw_observation_id"), e.get("candidate"))
                for e in tvg
                if isinstance(e, dict) and e.get("integration_dispatch") == "MAC-192"
            }
            appended_here = 0
            for it in group:
                key = (it["raw_obs_id"], it.get("candidate"))
                if key in existing_keys:
                    continue
                tvg.append(
                    {
                        "candidate": it.get("candidate"),
                        "candidate_type": it.get("candidate_type"),
                        "raw_observation_id": it["raw_obs_id"],
                        "source_id": it.get("source_id"),
                        "rationale": it.get("rationale"),
                        "excerpt": it.get("excerpt"),
                        "class": it.get("class"),
                        "integration_dispatch": "MAC-192",
                        "cp_anchor": CP_ANCHOR,
                        "integration_at_utc": NOW,
                    }
                )
                appended_here += 1
                total_appended += 1
            notes["type_vocabulary_gap_observations"] = tvg
            cur.execute(
                "UPDATE manufacturers SET notes = ? WHERE id = ?",
                (json.dumps(notes), mid),
            )
            log.append(
                f"  applied mfr={canonical!r} (id={mid}): {appended_here} items"
                f"; post-state count={len(tvg)}"
            )
        con.commit()
    except Exception:
        con.rollback()
        raise

    return total_appended


def main() -> int:
    plan = json.loads(PLAN.read_text())
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")  # extra safety even though schema is FK-off

    cmap = load_canonical_map(con)

    log: list[str] = []
    log.append("# §6.2 identifier promotion log — MAC-192 Phase 6 Wave I.14a")
    log.append(f"Captured: {NOW}")
    log.append("")

    # Section A — 113 identifier-row promotions
    a_result = section_a_identifierrow(con, plan, cmap, log)

    # Section B — 15 Flock android packages
    b_appended = section_b_android(con, plan, cmap, log)

    # Section C — 12 Collins REST + 15 CVEs
    c_api, c_cve = section_c_apisurfaces(con, plan, cmap, log)

    # Section D — 10 type-vocab-gap items
    d_appended = section_d_typevocabgap(con, plan, cmap, log)

    # Post-state readback
    cur = con.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL"
        " AND notes LIKE '%MAC-192%'"
    )
    mac192_active = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL")
    total_active = cur.fetchone()[0]

    log.append("")
    log.append("## Post-state readback")
    log.append(f"- identifiers active total: {total_active}")
    log.append(f"- identifiers active with MAC-192 tag: {mac192_active}")
    log.append("")
    log.append("## Section summary")
    log.append(f"- §6.2-identifierrow: {a_result['counts']}")
    log.append(f"- §6.2-android: appended={b_appended}")
    log.append(f"- §6.2-apisurfaces: api={c_api} cve={c_cve}")
    log.append(f"- §6.2-typevocabgap: appended={d_appended}")

    # Write Honeywell stage file
    if a_result["honeywell_log"]:
        HONEYWELL_STAGE.write_text(
            "# MAC-192 Phase 6 — Honeywell-targeted rows staged for Phase 8\n\n"
            f"Captured: {NOW}\n\n"
            "Per dispatch envelope: Honeywell-targeted promotions are NOT applied"
            " in Phase 6 (no manufacturer row mutation outside Phase 8 dispatch"
            " scope). Phase 8 (Honeywell admission) will pick up these candidates"
            " post-admission.\n\n"
            "## §6.2 identifierrow stage\n\n"
            + "\n".join(a_result["honeywell_log"])
            + "\n"
        )

    LOG.write_text("\n".join(log))
    print(
        f"§6.2 done. identifierrow={a_result['counts']} android={b_appended}"
        f" api={c_api} cve={c_cve} typevocabgap={d_appended}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
