#!/usr/bin/env python3
"""
MAC-385 F2 — canonical DB write (Parts A + B), backup-first, ONE session.

Authority chain: MAC-384 CEO ruling -> MAC-385 execution (CTO-sequenced).
Parent: MAC-382. Lane: canonical write to db/argus.db.

Part A — withdraw 23 known-fake placeholder OUIs (§7.4 / §11 #11) via the
         MAC-291 precedent: self-loop demote (superseded_by = id) + notes
         JSON property-merge ("mac385_withdraw") + 5 conflicts rows
         (reason='known_fake_pattern', one per distinct value), mirroring
         conflicts id 4 (the 00:00:00 all-zero withdraw).

Part B — COLLAPSE-safe collapse of 138 redundant rows into 28 lowest-id
         canonicals (DROPPED-class, export-neutral). ZERO confidence lift on
         ANY row (§11 #8 cardinal rule). Light "mac385_collapse" notes merge
         for traceability. superseded_by = <canonical>.

Hard constraints:
  - NEVER text-suffix concat notes — JSON property-merge only (json.loads/dumps).
  - Do NOT touch confidence / identifier / device_category / manufacturer /
    source_* on any row.
  - No export regen, no git commit, no push. Schema stays 31 (data pass).

Idempotent: re-running skips rows already in their target state. If a row's
pre-state diverges from the predicted (e.g. a sibling run moved it), the script
STOPS and reports rather than forcing.

Usage:
    python3 scripts/mac385_f2_apply.py [--db db/argus.db] [--dry-run]
"""

import argparse
import datetime
import json
import sqlite3
import sys

APPLIED_BY_AGENT_ID = "6c93a466"
DISPATCH_ISSUE = "MAC-385"
PARENT_ISSUE = "MAC-382/MAC-384"
AUTHORITY_CHAIN = (
    "MAC-384 CEO ruling -> MAC-385 execution (CTO-sequenced)"
)
MUTATION_PATTERN = "superseded_by_self_loop_demote_plus_notes_audit_append"

# ── Part A: 23 withdraw ids grouped by their fake placeholder value ──────────
PART_A = {
    "01:00:00": [36683, 36687, 36698, 36703, 36707],
    "01:02:03": [36622, 36625],
    "01:30:00": [36684, 36688, 36699, 36704, 36708],
    "02:00:00": [36685, 36689, 36700, 36701, 36705, 36709],
    "00:30:00": [36682, 36686, 36697, 36702, 36706],
}

# Per-value §7.3 defect sub-class + reason (brief §Part A step 2)
PART_A_DEFECT = {
    "01:00:00": (
        "section_7_3_invalid_oui__ig_multicast_bit_set",
        "I/G multicast-bit set; HH:MM:SS time-interval placeholder string "
        "mis-extracted as MAC OUI from CCTV polling-interval ternary excerpt",
    ),
    "01:30:00": (
        "section_7_3_invalid_oui__ig_multicast_bit_set",
        "I/G multicast-bit set; HH:MM:SS time-interval placeholder string "
        "mis-extracted as MAC OUI from CCTV polling-interval ternary excerpt",
    ),
    "02:00:00": (
        "section_7_3_invalid_oui__ul_laa_bit_set_round_placeholder",
        "U/L LAA-bit set + round placeholder; HH:MM:SS time-interval string "
        "mis-extracted as MAC OUI from CCTV polling-interval ternary excerpt",
    ),
    "01:02:03": (
        "section_7_3_invalid_oui__strictly_monotonic_sequence",
        "strictly-monotonic +1 octet sequence (01-02-03); synthetic placeholder, "
        "not a registered OUI",
    ),
    "00:30:00": (
        "section_7_3_invalid_oui__same_source_family_time_interval_string",
        "same-source-family time-interval-string mis-extraction; all 5 rows share "
        "source_url manufacturer_app://com.tiandy.easyliveplus@5.35.2#78b9bbec and "
        "the same synthetic ternary excerpt containing 01:00:00/01:30:00/02:00:00 "
        "polling-interval durations",
    ),
}

# ── Part B: 28 canonical <- [supersede ids] groups (lowest-id canonical) ─────
PART_B = {
    # product_family_codename
    38453: ([38454, 38455, 38456, 38457, 38458, 38459, 38460, 38461, 38462,
             38463, 38464, 38465, 38466, 38467, 38468, 38469, 38470, 38471,
             38472, 38473, 38474, 38475, 38476, 38477, 38478, 38479, 38480,
             38481, 38482, 38483, 38484, 38485, 38486, 38487, 38488, 38489,
             38490, 38491, 38493, 38495, 38496, 38497, 38498, 38499, 38500,
             38501, 38507, 38513, 38518], "stingray"),
    38522: ([38525, 38526, 38527, 38531, 38532, 38533, 38535, 38536, 38537,
             38539, 38540, 38541, 38542, 38543, 38544], "graykey"),
    38547: ([38551, 38554, 38557, 38560, 38563, 38565, 38567, 38569, 38571,
             38573, 38575], "Inspire 1"),
    38492: ([38494, 38502, 38504, 38508, 38510, 38511, 38512, 38514, 38516,
             38517], "kingfish"),
    38519: ([38520, 38521, 38524, 38530, 38534, 38538], "grayshift"),
    38546: ([38550, 38553, 38556, 38559, 38562], "Inspire 2"),
    38566: ([38568, 38570, 38572, 38574, 38576], "Matrice 100"),
    38545: ([38549, 38552, 38555, 38558, 38561], "Matrice 200"),
    38503: ([38505, 38506, 38509, 38515], "amberjack"),
    38436: ([38438, 38439, 38440, 38441], "ufed reports"),
    38446: ([38447, 38448, 38449], "axon body 3"),
    38442: ([38443, 38444, 38445], "axon body 4"),
    38450: ([38451, 38452], "axon body 2"),
    38432: ([38433, 38437], "ufed physical"),
    # equipment_class_code (each +1)
    37040: ([37139], "2AHAY-S5121601"),
    37042: ([37140], "2AHAY-SR6G1601"),
    37037: ([37141], "2AHAY-WM3301601"),
    37066: ([37153], "2ANDR-DF03223"),
    37064: ([37152], "2ANDR-DF03323"),
    37100: ([37157], "2ANDR-OE1002105"),
    37079: ([37146], "2ANDR-OK2002209"),
    37102: ([37154], "2ANDR-OT2132010"),
    37060: ([37168], "2ANDR-P04P23"),
    37092: ([37170], "2ANDR-P11C2022"),
    37058: ([37158], "2ANDR-P14C23"),
    37070: ([37156], "2ANDR-PP1012023"),
    37074: ([37147], "2ANDR-RX32303"),
    # firmware_branded_string
    38430: ([38431], "version 7.15.1.1"),
}


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def property_merge(notes_text, key, payload):
    """JSON property-merge: parse, add key, dump. NEVER text-suffix concat."""
    obj = json.loads(notes_text)  # raises if not valid JSON — fail loud
    if not isinstance(obj, dict):
        raise ValueError(f"notes is not a JSON object: {notes_text[:60]}")
    obj[key] = payload
    return json.dumps(obj, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="db/argus.db")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    applied_at = utc_now()
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Flatten Part A id->value
    part_a_ids = []
    for value, ids in PART_A.items():
        for i in ids:
            part_a_ids.append((i, value))

    # Flatten Part B id->canonical, group
    part_b_rows = []
    for canon, (sup_ids, group) in PART_B.items():
        for i in sup_ids:
            part_b_rows.append((i, canon, group))

    all_ids = [i for i, _ in part_a_ids] + [i for i, _, _ in part_b_rows]
    if len(set(all_ids)) != 161:
        print(f"FATAL: expected 161 distinct mutation ids, got "
              f"{len(set(all_ids))}", file=sys.stderr)
        sys.exit(2)

    # ── Precondition re-query: every target must be superseded_by IS NULL ────
    qmarks = ",".join("?" for _ in all_ids)
    cur.execute(
        f"SELECT id, identifier_type, superseded_by, confidence, notes "
        f"FROM identifiers WHERE id IN ({qmarks})", all_ids)
    live = {r["id"]: r for r in cur.fetchall()}

    missing = [i for i in all_ids if i not in live]
    if missing:
        print(f"FATAL: {len(missing)} target ids missing from DB: {missing}",
              file=sys.stderr)
        sys.exit(2)

    # Part A target self-loop state: superseded_by == id means already done.
    # Part B target state: superseded_by == canonical means already done.
    target_state = {}
    for i, _ in part_a_ids:
        target_state[i] = i
    for i, canon, _ in part_b_rows:
        target_state[i] = canon

    already_done = []
    diverged = []
    todo = []
    for i in all_ids:
        sb = live[i]["superseded_by"]
        if sb is None:
            todo.append(i)
        elif sb == target_state[i]:
            already_done.append(i)
        else:
            diverged.append((i, sb, target_state[i]))

    if diverged:
        print("FATAL: rows diverged from predicted pre-state (sibling run?). "
              "STOP, hand back to CTO:", file=sys.stderr)
        for i, sb, tgt in diverged:
            print(f"  id={i} superseded_by={sb} (expected NULL or {tgt})",
                  file=sys.stderr)
        sys.exit(3)

    print(f"[precheck] {len(todo)} to mutate, {len(already_done)} already in "
          f"target state (idempotent skip), 0 diverged")

    # json_valid sweep BEFORE (over the rows we will mutate)
    bad_before = [i for i in todo if live[i]["notes"] is None
                  or not _json_ok(live[i]["notes"])]
    if bad_before:
        print(f"FATAL: {len(bad_before)} rows have NULL/invalid JSON notes "
              f"before mutation (property-merge unsafe): {bad_before}",
              file=sys.stderr)
        sys.exit(4)
    print(f"[precheck] json_valid(notes) BEFORE: {len(todo)}/{len(todo)} valid")

    if args.dry_run:
        print("[dry-run] no writes performed.")
        conn.close()
        return

    # ── Part A apply ────────────────────────────────────────────────────────
    a_applied = 0
    for i, value in part_a_ids:
        if i not in todo:
            continue
        defect_class, reason = PART_A_DEFECT[value]
        payload = {
            "defect_class": defect_class,
            "defect_value": value,
            "defect_slot": "oui",
            "dispatch_issue": DISPATCH_ISSUE,
            "parent_issue": PARENT_ISSUE,
            "authority_chain": AUTHORITY_CHAIN,
            "applied_at_utc": applied_at,
            "applied_by_agent_id": APPLIED_BY_AGENT_ID,
            "mutation_pattern": MUTATION_PATTERN,
            "reason": reason,
        }
        merged = property_merge(live[i]["notes"], "mac385_withdraw", payload)
        cur.execute(
            "UPDATE identifiers SET superseded_by = id, notes = ? "
            "WHERE id = ? AND superseded_by IS NULL",
            (merged, i))
        if cur.rowcount != 1:
            raise RuntimeError(f"Part A id={i} update affected "
                               f"{cur.rowcount} rows (expected 1)")
        a_applied += 1

    # ── Part A conflicts rows (one per distinct value) ──────────────────────
    # Idempotency-guarded: skip a value if a MAC-385 known_fake_pattern row for
    # that defect_value already exists (so re-running does NOT duplicate).
    conflicts_inserted = []
    conflicts_skipped = []
    for value, ids in PART_A.items():
        defect_class, _ = PART_A_DEFECT[value]
        cur.execute(
            "SELECT id FROM conflicts "
            "WHERE reason='known_fake_pattern' "
            "  AND resolved_by = ? "
            "  AND json_extract(resolution_notes,'$.authority')='MAC-385' "
            "  AND json_extract(resolution_notes,'$.defect_value')=?",
            (f"{APPLIED_BY_AGENT_ID} (MAC-385)", value))
        existing = cur.fetchone()
        if existing is not None:
            conflicts_skipped.append((existing[0], value))
            continue
        res_notes = json.dumps({
            "reject_reason": "known_fake_pattern",
            "known_fake_class": defect_class,
            "defect_value": value,
            "row_ids": ids,
            "authority": "MAC-385",
        }, ensure_ascii=False)
        cur.execute(
            "INSERT INTO conflicts "
            "(identifier_a_id, identifier_b_id, raw_observation_id, reason, "
            " resolved_by, resolution_notes) "
            "VALUES (NULL, NULL, NULL, 'known_fake_pattern', ?, ?)",
            (f"{APPLIED_BY_AGENT_ID} (MAC-385)", res_notes))
        conflicts_inserted.append((cur.lastrowid, value))

    # ── Part B apply (ZERO confidence lift; superseded_by = canonical) ───────
    b_applied = 0
    for i, canon, group in part_b_rows:
        if i not in todo:
            continue
        payload = {
            "canonical": canon,
            "group": group,
            "reason": "redundant_same_source_excerpt",
            "dispatch_issue": DISPATCH_ISSUE,
            "applied_at_utc": applied_at,
            "applied_by_agent_id": APPLIED_BY_AGENT_ID,
        }
        merged = property_merge(live[i]["notes"], "mac385_collapse", payload)
        cur.execute(
            "UPDATE identifiers SET superseded_by = ?, notes = ? "
            "WHERE id = ? AND superseded_by IS NULL",
            (canon, merged, i))
        if cur.rowcount != 1:
            raise RuntimeError(f"Part B id={i} update affected "
                               f"{cur.rowcount} rows (expected 1)")
        b_applied += 1

    conn.commit()
    print(f"[apply] Part A self-loop demotes: {a_applied}")
    print(f"[apply] Part A conflicts inserted: "
          f"{[c for c in conflicts_inserted]}")
    if conflicts_skipped:
        print(f"[apply] Part A conflicts already present (idempotent skip): "
              f"{[c for c in conflicts_skipped]}")
    print(f"[apply] Part B collapse supersessions: {b_applied}")

    # json_valid sweep AFTER
    cur.execute(
        f"SELECT COUNT(*) FROM identifiers WHERE id IN ({qmarks}) "
        f"AND (notes IS NULL OR json_valid(notes)=0)", all_ids)
    bad_after = cur.fetchone()[0]
    print(f"[verify] json_valid(notes) AFTER over 161 scope: "
          f"{'PASS (0 invalid)' if bad_after == 0 else f'FAIL ({bad_after})'}")

    conn.close()


def _json_ok(text):
    try:
        json.loads(text)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    main()
