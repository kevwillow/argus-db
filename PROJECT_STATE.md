# Argus — Project State

**Current phase:** 0 — Bootstrap (correction pass complete)
**Last checkpoint passed:** 0 (approved by human at 2026-05-04T02:08:46Z)
**Next checkpoint:** 1 — Schema & Foundation (DB Architect dispatch, *blocked on human approval of corrected bible*)
**Status:** awaiting human review of the corrected bible before Phase 1 dispatch

## Active sub-agents
- _(none — Phase 0 is CEO-direct work; sub-agent dispatch begins Phase 1 with the DB Architect)_

## Last action
Bible correction pass applied (10 corrections from MAC-1 comment ab234b68). Bible end-to-end internal-consistency check passed with two minor wording reconciliations (§6 Phase 5 file descriptions and §7.5 Don'ts ≥30 floor) and one numbering smell flagged (§11 has a placeholder at #11 to preserve the user-prescribed numbering of new entries 12–14). PROJECT_STATE updated. Ready to commit and reassign MAC-1 to human for Phase-1 approval.

## Open questions for human
- WiGLE API credentials before Phase 3 starts (now also blocks the new Phase 3 Step-0 budget estimate / Checkpoint 3a). _Blocking? n_ (not until Phase 3)
- Final project name confirmation at Checkpoint 5. _Blocking? n_
- DB Architect dispatch approval at Checkpoint 1. _Blocking? y_ (held pending human review of corrected bible)
- `argus_record_id` upsert semantics in Talos v0.2 seeder (new — added by Correction 8 review). _Blocking? n_ (resolves before Phase 5 export design)

## Recent log (last 25 entries)
- 2026-05-04T02:04:44Z  Wake — MAC-1 assigned to CEO with kickoff prompt + bible pointer.
- 2026-05-04T02:07:00Z  Bible read; recital posted on MAC-1; reassigned to human awaiting Checkpoint 0.
- 2026-05-04T02:08:46Z  Checkpoint 0 approved. Open items resolved (threshold=70, inference cap=70, name=Argus provisional). State-file schema specified.
- 2026-05-04T02:10:34Z  Created `/home/kev/argus/{db,raw,exports,agents,logs}`.
- 2026-05-04T02:10:34Z  Copied `PROJECT_BIBLE.md` from `/home/kev/Talos/` to project root.
- 2026-05-04T02:10:34Z  Wrote `KICKOFF.md` with kickoff prompt + Checkpoint-0 resolution addendum.
- 2026-05-04T02:10:34Z  Wrote initial `PROJECT_STATE.md` (this file) per human's prescribed schema.
- 2026-05-04T02:10:34Z  Wrote `.gitignore` (raw/ excluded; db/ binaries excluded; standard Python/editor noise excluded).
- 2026-05-04T02:10:34Z  `git init` + initial commit.
- 2026-05-04T02:10:34Z  Posted Checkpoint 1 report to MAC-1; reassigned to human.
- 2026-05-04T02:14:08Z  Wake — MAC-1 comment ab234b68: 10-correction bible pass before Phase 1.
- 2026-05-04T02:21:34Z  Correction 1 applied — §4.4 Talos export mapping table (oui/mac/bssid/ssid_exact/ble_uuid pass; ssid_pattern, mac_range >256, device_fingerprint dropped; ble_service collapsed to ble_uuid).
- 2026-05-04T02:21:34Z  Correction 2 applied — §4.5 severity derivation by device_category; severity ≠ confidence; procurement-only carveout.
- 2026-05-04T02:21:34Z  Correction 3 applied — §7.5 per-record description format (≤80 chars, no URLs, vendor + product + short context).
- 2026-05-04T02:21:34Z  Correction 4 applied — §8.4 unknown-category never exported; Pi self-exclude OUIs (`b8:27:eb`, `dc:a6:32`, `e4:5f:01`, `28:cd:c1`).
- 2026-05-04T02:21:34Z  Correction 5 applied — §7.3 + §7.4 enumerated fake-MAC reject list (RFC 7042 IPv4/IPv6 doc ranges, common doc patterns, all-identical, monotonic +1).
- 2026-05-04T02:21:34Z  Correction 6 applied — §7.3 LAA-bit confidence penalty (cap ≤40 unless source explicitly attests).
- 2026-05-04T02:21:34Z  Correction 7 applied — §6 Phase 3 Step-0 WiGLE budget estimate; new Checkpoint 3a sub-checkpoint blocking WiGLE queries.
- 2026-05-04T02:21:34Z  Correction 8 applied — §7.5 Talos export JSON shape (`_meta.dropped_in_export` keys; `argus_record_id` stable across re-runs).
- 2026-05-04T02:21:34Z  Correction 9 applied — §11 new don'ts #12 (Pi OUI exclude in high-conf), #13 (unknown-category never exported), #14 (procurement-only never exported); placeholder at #11 preserves user-prescribed numbering.
- 2026-05-04T02:21:34Z  Correction 10 applied — §9 deliverables expanded to five files; new item 9 requires "Dropped from Talos export" tally that reconciles with `_meta.dropped_in_export`.
- 2026-05-04T02:21:34Z  Internal-consistency pass — verified §4.4↔§4.5↔§7.5 cross-references, §11 #12/#13/#14 references, §9 item 9 ↔ §7.5 `_meta.dropped_in_export` key parity. Two reconciliations applied: §6 Phase 5 step 5 file descriptions tightened to match §9 item 2; §7.5 Don'ts ≥30 floor explicit for both Talos files.
- 2026-05-04T02:21:34Z  §12 Open Questions updated — confidence threshold and output naming marked resolved by this correction pass; new question added for `argus_record_id` upsert semantics; WiGLE creds and project name remain open.
- 2026-05-04T02:21:34Z  Posting correction-pass report to MAC-1; will commit bible + state with prescribed message and reassign to human for Phase-1 approval.

## Notes for human review
- §11 entry #11 is a placeholder. The correction prescribed entries 12, 13, 14 explicitly; renumbering would break the in-text references I added (e.g., §7.5 references "§11 #13"). The placeholder preserves both the user's numbering and the cross-references. Replace, leave, or renumber per preference.
- §4.5 mentions "procurement-only records (`source_type='procurement'` with no MAC/OUI/UUID, only an agency-bought-vendor mapping)" but §4.1 makes `identifier` and `identifier_type` NOT NULL, so such records cannot live in the `identifiers` table as currently spec'd. The DB Architect (§7.1) will need to decide where these procurement-only records live (e.g., a dedicated `procurement` table, or treated as `sources`/observations). Flagged here as a Phase-1 design question; not blocking the bible commit because the rule "never export procurement-only to Talos" is correct regardless of where the records live.
