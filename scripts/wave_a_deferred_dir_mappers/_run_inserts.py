"""MAC-101 Item C Phase 1 runner — orchestrates per-slug INSERT into raw_observations.

One transaction per slug. Per-row INSERT OR IGNORE on UNIQUE(source_id, source_row_key)
(per migration 0006 idempotency contract). Creates a single extraction_runs row before
the batched INSERTs, captures its id, sets status='running' → 'ok' (or 'partial' if any
slug erred) at end.

Selects slugs by env var SLUGS (csv) or runs all that have _path_b_normalized.json output.
"""
import json, os, sqlite3, sys, importlib.util, time

MAPPERS = [
    ("eylonK14_IMSICatcherDetector",  31, None),
    ("nixxxo_tagfinder",              29, None),
    ("CellularPrivacy_AIMSICD",       32, None),
    ("cyber_defence_campus_RemoteIDReceiver", 27, None),
    ("DeflockJoplin_flock_you",                       None, "DeflockJoplin_SID"),
    ("EthanThePhoenix38_flock_you_camera_detector",   None, "EthanThePhoenix38_SID"),
    ("FoggedLens_deflock_app",                        None, "FoggedLens_SID"),
    ("GainSec_anti_crime_ecosystem_research",         None, "GainSec_anti_crime_SID"),
    ("GainSec_flock_safety_falcon_sparrow_alpr_edl_firehose", None, "GainSec_falcon_SID"),
    ("RUB_SysSec_DroneSecurity",                      None, "RUB_SysSec_SID"),
]


def load_module(mod_name):
    spec = importlib.util.spec_from_file_location(
        mod_name, f"scripts/wave_a_deferred_dir_mappers/{mod_name}.py"
    )
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def main():
    db_path = os.environ.get("ARGUS_DB", "db/argus.db")
    agent_id = "1347736c-16de-444c-9b2c-434321c2b025"
    only_slugs = set((os.environ.get("SLUGS") or "").split(",")) if os.environ.get("SLUGS") else None
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    # Single extraction_runs row covering this Phase 1 wave (per issue §4)
    cur.execute(
        "INSERT INTO extraction_runs(agent_id, source_id, status, notes) VALUES (?, NULL, 'running', ?)",
        (agent_id, "MAC-101 Item C Phase 1 — Wave-A deferred-dir per-shape mapping (10 slugs)"),
    )
    run_id = cur.lastrowid
    con.commit()
    print(f"extraction_runs.id = {run_id}")

    grand_in = 0; grand_out = 0; errors = 0; per_slug_report = []

    for slug_mod, fixed_sid, env_name in MAPPERS:
        if only_slugs and slug_mod not in only_slugs:
            continue
        # Resolve source_id
        if fixed_sid is not None:
            sid = fixed_sid
        elif env_name:
            v = os.environ.get(env_name)
            if not v:
                print(f"  SKIP {slug_mod}: env {env_name} not set (CEO §2 disposition pending)")
                per_slug_report.append((slug_mod, "SKIPPED_NO_SOURCE_ID", 0, 0))
                continue
            sid = int(v)
        else:
            raise RuntimeError(f"no source_id resolver for {slug_mod}")

        mod = load_module(slug_mod)
        try:
            rows = mod.emit(sid) if env_name else mod.emit()
        except Exception as e:
            print(f"  EMIT FAILED {slug_mod}: {e}")
            errors += 1
            per_slug_report.append((slug_mod, f"EMIT_FAILED:{e}", 0, 0))
            continue

        grand_in += len(rows)
        in_count = len(rows); inserted = 0; skipped = 0

        # Single transaction per slug per issue §5
        cur.execute("BEGIN")
        try:
            for r in rows:
                # App-level ≤200 char enforcement (defense in depth; mappers already trunc)
                exc = r.get("source_excerpt")
                if exc and len(exc) > 200:
                    raise ValueError(f"source_excerpt overflow ({len(exc)}>200) for {r.get('candidate_identifier')}")
                # Idempotency: skip if exists
                exists = cur.execute(
                    "SELECT id FROM raw_observations WHERE source_id=? AND source_row_key=? LIMIT 1",
                    (r["source_id"], r["source_row_key"]),
                ).fetchone()
                if exists:
                    skipped += 1
                    continue
                cur.execute("""
                    INSERT INTO raw_observations
                      (source_id, extraction_run_id, source_url, raw_payload,
                       candidate_identifier, candidate_type, candidate_category,
                       candidate_manufacturer, source_excerpt, captured_at,
                       processed_at, promoted_identifier_id, notes, source_row_key)
                    VALUES (?,?,?,?,?,?,?,?,?,?,NULL,NULL,?,?)
                """, (
                    r["source_id"], run_id, r["source_url"],
                    r.get("raw_payload") or json.dumps({}),
                    r["candidate_identifier"], r.get("candidate_type"),
                    r.get("candidate_category"), r.get("candidate_manufacturer"),
                    r.get("source_excerpt"),
                    r.get("captured_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    json.dumps(r.get("notes") or {}),
                    r["source_row_key"],
                ))
                inserted += 1
            con.commit()
            grand_out += inserted
            print(f"  {slug_mod}: in={in_count} inserted={inserted} dedup_skipped={skipped} source_id={sid}")
            per_slug_report.append((slug_mod, f"OK source_id={sid}", in_count, inserted))
        except Exception as e:
            con.rollback()
            print(f"  INSERT FAILED {slug_mod}: {e}")
            errors += 1
            per_slug_report.append((slug_mod, f"INSERT_FAILED:{e}", in_count, 0))

    # Finalize the run
    status = "ok" if errors == 0 else ("partial" if grand_out > 0 else "failed")
    cur.execute("""
        UPDATE extraction_runs
        SET finished_at=CURRENT_TIMESTAMP, records_in=?, records_out=?, errors=?, status=?,
            notes = COALESCE(notes,'') || ?
        WHERE id=?
    """, (grand_in, grand_out, errors, status,
          f"\nPer-slug:\n" + "\n".join(f"  {s}: {st} in={i} out={o}" for s,st,i,o in per_slug_report),
          run_id))
    con.commit()
    print(f"\nTotal: in={grand_in} out={grand_out} errors={errors} status={status} run_id={run_id}")
    return run_id, per_slug_report


if __name__ == "__main__":
    main()
