# Argus — Project State

**Current phase:** 1 — Schema & Foundation (dispatch in flight)
**Last checkpoint passed:** 0 (approved 2026-05-04T02:08:46Z); Phase-1 entry approved 2026-05-04T02:24:48Z
**Next checkpoint:** 1 — Schema verified, dedup logic tested. Approval to proceed to Phase 2.
**Status:** Phase 1 dispatch awaiting board approval of DB Architect hire (approval id `64740d34-51b7-43c6-aeab-426db5965095`)

## Active sub-agents
- **DBArchitect** (`6c93a466-d498-49e0-b7af-3fc0d08eb2b0`, `pending_approval`) — owns Phase 1 per bible §7.1: schema, manufacturers seed, `argus_cli.py`, dedup module, dedup unit tests. Reports to CEO. Adapter: `claude_local`, cwd `/home/kev/argus`. Heartbeats off; wake-on-demand.

## Last action
Phase 1 entry approved by user (MAC-1 comment c429a878 at 2026-05-04T02:24:48Z: "Phase 1 approved. you may proceed"). CEO checked out MAC-1, drafted DB Architect hire request, and submitted it to the board. Hire is `pending_approval`. Wrote DB Architect's `AGENTS.md` instructions (bible §7.1 scope, §11 hard rules, Phase-1 deliverables, the §4.5 procurement-only design question to surface at Checkpoint 1). Cannot dispatch the Phase-1 subtask until the hire is approved.

## Open questions for human
- **DB Architect hire approval** (approval `64740d34-51b7-43c6-aeab-426db5965095`). _Blocking? y_ — gates all Phase-1 dispatch.
- WiGLE API credentials before Phase 3 starts (also gates Checkpoint 3a budget estimate). _Blocking? n_ (not until Phase 3)
- Final project name confirmation at Checkpoint 5. _Blocking? n_
- `argus_record_id` upsert semantics in Talos v0.2 seeder (added by Correction 8 review). _Blocking? n_ (resolves before Phase 5 export design)
- §4.5 procurement-only-record table structure (separate `procurement_records` table vs. `raw_observations`-only). DB Architect will surface a recommendation at Checkpoint 1.

## Recent log (last 25 entries)
- 2026-05-04T02:04:44Z  Wake — MAC-1 assigned to CEO with kickoff prompt + bible pointer.
- 2026-05-04T02:07:00Z  Bible read; recital posted on MAC-1; reassigned to human awaiting Checkpoint 0.
- 2026-05-04T02:08:46Z  Checkpoint 0 approved. Open items resolved (threshold=70, inference cap=70, name=Argus provisional).
- 2026-05-04T02:10:34Z  Created `/home/kev/argus/{db,raw,exports,agents,logs}`; bible+kickoff+state+gitignore committed; first git commit.
- 2026-05-04T02:14:08Z  Wake — MAC-1 comment ab234b68: 10-correction bible pass before Phase 1.
- 2026-05-04T02:21:34Z  Corrections 1–10 applied to bible; internal-consistency pass; §12 Open Questions updated; correction-pass report posted to MAC-1.
- 2026-05-04T02:24:48Z  Wake — MAC-1 comment c429a878: "Phase 1 approved. you may proceed".
- 2026-05-04T02:25:33Z  Checked out MAC-1 (status → in_progress under run `3f7b89f2`).
- 2026-05-04T02:26:26Z  DB Architect hire request submitted (agent `6c93a466`, approval `64740d34`). Status `pending_approval`. Source-issue link to MAC-1 set.
- 2026-05-04T02:26:50Z  Wrote DB Architect AGENTS.md (bible §7.1 scope, §11 hard rules, Phase-1 deliverables list, §4.5 procurement-only design question to surface at Checkpoint 1).
- _(commit + MAC-1 comment + reassign to user pending in this same heartbeat)_

## Notes for human review
- The Phase-1 subtask (the actual schema/CLI/dedup work) will be created **after** the board approves the DB Architect hire. Paperclip will wake the CEO on approval (`PAPERCLIP_APPROVAL_ID` injected); CEO will then file the subtask under MAC-1 and assign it to DBArchitect.
- §11 entry #11 in the bible is still a placeholder (preserved to keep the user's prescribed numbering of #12/#13/#14 stable). Replace, leave, or renumber per preference.
- §4.5 procurement-only records are spec'd to live somewhere, but the §4.1 `identifiers` table NOT NULL constraints rule out the main table. DB Architect will surface a recommendation (default: separate `procurement_records` table) at Checkpoint 1; CEO will not pre-decide it.
