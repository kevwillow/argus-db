# Argus — Project State

**Current phase:** 1 — Schema & Foundation (executing)
**Last checkpoint passed:** 0 (approved 2026-05-04T02:08:46Z); Phase-1 entry approved 2026-05-04T02:24:48Z
**Next checkpoint:** 1 — Schema verified, dedup logic tested. Approval to proceed to Phase 2.
**Status:** Phase-1 deliverables built; MAC-2 ready to be reassigned to CEO at Checkpoint 1 for human sign-off.

## Active sub-agents
- **DBArchitect** (`6c93a466-d498-49e0-b7af-3fc0d08eb2b0`, `idle`) — owns Phase 1 per bible §7.1: schema, manufacturers seed, `argus_cli.py`, dedup module, dedup unit tests. Reports to CEO. Adapter: `claude_local`, cwd `/home/kev/argus`. Heartbeats off; wake-on-demand. Currently assigned MAC-2 (`3e8c4825-126e-4dd5-9c5d-8c6547eaf12b`).

## Last action
DB Architect hire was approved (decided 2026-05-04T02:26:28Z) and re-confirmed by user via MAC-1 comment c15be093 at 2026-05-04T02:29:30Z ("hire is aproved proceed"). Same comment thread also clarified that Argus is a from-scratch project and that agents must be hired individually for this company (no reuse from any other project). CEO created Phase-1 subtask MAC-2 under MAC-1 and assigned it to DBArchitect with the full Phase-1 scope, hard rules, and the §4.5 procurement-records design question to surface at Checkpoint 1. MAC-1 kept in `in_progress` as the live orchestration thread.

## Open questions for human
- WiGLE API credentials before Phase 3 starts (also gates Checkpoint 3a budget estimate). _Blocking? n_ (not until Phase 3)
- Final project name confirmation at Checkpoint 5. _Blocking? n_
- `argus_record_id` upsert semantics in Talos v0.2 seeder (added by Correction 8 review). _Blocking? n_ (resolves before Phase 5 export design)
- ~~§4.5 procurement-only-record table structure~~ — **resolved by DBArchitect at Checkpoint 1**: separate `procurement_records` table created in `db/migrations/0001_initial.sql` (option (a) per AGENTS.md). Rationale documented in the migration header. Awaiting CEO/human sign-off at Checkpoint 1.

## Recent log (last 25 entries)
- 2026-05-04T02:04:44Z  Wake — MAC-1 assigned to CEO with kickoff prompt + bible pointer.
- 2026-05-04T02:07:00Z  Bible read; recital posted on MAC-1; reassigned to human awaiting Checkpoint 0.
- 2026-05-04T02:08:46Z  Checkpoint 0 approved. Open items resolved (threshold=70, inference cap=70, name=Argus provisional).
- 2026-05-04T02:10:34Z  Created `/home/kev/argus/{db,raw,exports,agents,logs}`; bible+kickoff+state+gitignore committed; first git commit.
- 2026-05-04T02:14:08Z  Wake — MAC-1 comment ab234b68: 10-correction bible pass before Phase 1.
- 2026-05-04T02:21:34Z  Corrections 1–10 applied to bible; internal-consistency pass; §12 Open Questions updated; correction-pass report posted to MAC-1.
- 2026-05-04T02:24:48Z  Wake — MAC-1 comment c429a878: "Phase 1 approved. you may proceed".
- 2026-05-04T02:25:33Z  Checked out MAC-1 (status → in_progress under run `3f7b89f2`).
- 2026-05-04T02:26:26Z  DB Architect hire request submitted (agent `6c93a466`, approval `64740d34`). Status `pending_approval`.
- 2026-05-04T02:26:50Z  Wrote DB Architect AGENTS.md (bible §7.1 scope, §11 hard rules, Phase-1 deliverables, §4.5 procurement design question).
- 2026-05-04T02:26:28Z  DB Architect hire auto-approved by board.
- 2026-05-04T02:26:14Z  Wake — MAC-1 comment 7cd0d753: user clarified Argus is a from-scratch project; agents must be hired individually (no reuse).
- 2026-05-04T02:29:30Z  Wake — MAC-1 comment c15be093: "hire is aproved proceed".
- 2026-05-04T02:30Z      CEO checked out MAC-1, created Phase-1 subtask MAC-2 (`3e8c4825`) assigned to DBArchitect, parented under MAC-1. Posted dispatch comment on MAC-1; MAC-1 kept `in_progress`.
- 2026-05-04T02:35Z      DBArchitect woke on MAC-2 assignment. Wrote `db/migrations/0001_initial.sql` (full §4 schema + indexes + enum CHECKs + `manufacturers` seed of 32 vendors + new `procurement_records` table per §4.5 carveout decision). Built `db/init_db.py`; applied migration to `db/argus.db`; counts verified (manufacturers=32, all other tables=0). Re-run idempotent.
- 2026-05-04T02:36Z      Implemented `db/dedup.py` per §8.3 as DB-free pure functions: `is_duplicate`, `merge_cluster`, `find_duplicate_clusters`, `dedup`. Added `tests/test_dedup.py` with 25 tests covering all 5 required cases (identical, MAC-within-OUI, confidence cap=99, supersedes pointers, notes append). All 25 pass under pytest 9.0.3 in `.venv`.
- 2026-05-04T02:37Z      Wrote `argus_cli.py` with `status`/`query`/`export`/`validate`. `status` prints schema version, table counts, current phase from PROJECT_STATE.md; `query` does exact match + OUI-prefix lookup; `export`/`validate` are Phase-5 stubs that print the deferral notice.

## Notes for human review
- Next CEO heartbeat-relevant event is DBArchitect reassigning MAC-2 back to me with `in_review` at Checkpoint 1. CEO will then bring the schema/dedup/procurement-decision package to the user for sign-off before Phase 2.
- §11 entry #11 in the bible is still a placeholder (preserved to keep the user's prescribed numbering of #12/#13/#14 stable). Replace, leave, or renumber per preference.
- §4.5 procurement-only records are spec'd to live somewhere, but the §4.1 `identifiers` table NOT NULL constraints rule out the main table. DB Architect will surface a recommendation (default: separate `procurement_records` table) at Checkpoint 1; CEO will not pre-decide it.
