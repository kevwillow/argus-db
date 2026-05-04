# Argus — Project State

**Current phase:** 1 — Schema & Foundation **(Checkpoint 1 signed off; Correction Pass 3 applied; ready to dispatch Phase 2)**
**Last checkpoint passed:** 1 (signed off 2026-05-04T03:23:31Z by user comment [d08ee4a8](/MAC/issues/MAC-1#comment-d08ee4a8-e525-4c19-9886-89f0f95bf1c3))
**Next checkpoint:** 2 — Tier 1 structured-source staging populated. Spot-check 20 random records. User approval to proceed.
**Status:** MAC-2 cleared (closing this heartbeat). MAC-1 reassigned to CEO `in_progress` for Phase 2 hire request + dispatch. Source Worker(s) to be hired per the from-scratch hiring rule.

## Active sub-agents
- **DBArchitect** (`6c93a466-d498-49e0-b7af-3fc0d08eb2b0`) — Phase 1 complete. Off-rotation until Phase 5 export design (or sooner if §4.1 enum extension for `in_vehicle_router` becomes blocking).

## Last action
CEO heartbeat 2026-05-04T03:2xZ — Correction Pass 3 + Phase 2 dispatch prep:
1. **Bible edit (§2.1 + §12).** Added §2.1 #5 "In-vehicle LTE/WiFi routers — Cradlepoint (IBR900/R1900-class), Sierra Wireless (MG90/AirLink-class)" between old #4 (police radios) and old #5 (drones). Renumbered old #5–#11 → #6–#12. Chose option (b) over option (a): a separate row keeps each §2.1 item one emitter class with consistent radio physics — LTE+WiFi backhaul is genuinely distinct from P25/VHF voice. User explicitly noted "in-vehicle routers aren't radios"; option (b) honors that. Also added `device_cluster_id` design question to §12 Open per user direction (initial lean: scanner-side correlation belongs in Talos, but holding for explicit decision).
2. **Manufacturers seed update (32 → 34).** Added Cradlepoint and Sierra Wireless rows in the police_radio→drone gap (matching new §2.1 #5 position). Both rows use `primary_category=NULL` (mirrors Motorola Solutions / L3Harris multi-purpose pattern) because the §4.1 device_category enum does not yet have an `in_vehicle_router` value — surfacing as a future enum-extension decision when Phase 2/3 actually ingests the first router identifier. Renumbered §2.1 # references throughout the seed comments (#5→#6 drones, #6→#7 gunshot, #7→#8 hacking, #10→#11 face_recog, #11→#12 drone_detect; Rekor's `#1, #10` → `#1, #11`). 25/25 dedup tests pass; argus_cli status clean; verified 34-vendor count + Cradlepoint/Sierra Wireless rows present.
3. **BIBLE_AMENDMENTS Correction Pass 3 entry** logged. Bible commit hash backfilled.
4. **Phase 2 hire request** queued via `paperclip-create-agent` skill — Source Worker for Tier 1 structured sources (IEEE OUI registry, Wireshark manuf, EFF Atlas of Surveillance, DeFlock). Brief includes the standing Flock + cop-cars advisory (high-value targets — surface anything interesting; not a scope narrowing).

## Research leads (Phase 3/4 breadcrumbs)

These are leads to follow — not commitments, not active work. Captured per user direction (MAC-1 comment [d08ee4a8](/MAC/issues/MAC-1#comment-d08ee4a8-e525-4c19-9886-89f0f95bf1c3)) so the breadcrumbs survive context drift between phases. Source Workers/Extraction Workers should pick these up at the relevant phase and report back with findings.

- **Flock SSID pattern (Phase 3/4).** Flock cameras likely emit a maintenance/installer WiFi network with an SSID convention along the lines of `Flock-{serial}` or similar (per public installer materials). Confirming the exact pattern from Flock FCC filings (grantee 2AKWH-class — needs verification) and installer documentation would yield a Tier-0 SSID-pattern record the Pi scanner can act on at high confidence even before any concrete MAC/OUI lands. Hold the actual scraping for Phase 3/4 (FCC ID workflow + manufacturer doc mining) — capture the lead now so it doesn't get lost.
- **FCC grantee-prefix harvesting (Phase 3 — alongside FCC ID workflow).** Identify FCC grantee codes for Flock, Motorola Solutions (APX, V300/V500), Axon (Body 2/3/4, Fleet 3), Cradlepoint (IBR/R-series), Sierra Wireless (AirLink/MG90), L3Harris (XL-series), DJI (Matrice LE), Skydio. Bulk-lookup §7.2 sources by grantee code rather than per-product searches; each grantee filing typically yields multiple OUIs + frequency ranges + internal photos in one pass. Higher yield per query than vendor-name searches.
- **City council minutes + municipal procurement portals (Phase 3/4 — alongside SAM.gov).** SAM.gov covers federal-side procurement, but Flock + body-cam + LPR deployments at municipal level often surface in city council minutes, police-commission meeting agendas, and small-city procurement portals. These are higher-yield than vendor websites for the "where is this deployed" mapping (which then feeds DeFlock + Atlas of Surveillance geo-priors). Worth a dedicated Source Worker workstream in Phase 3 or Phase 4 unstructured wave.
- **Cop-car emitter cluster (standing context for Source Workers, not a research lead per se).** A patrol car is a multi-emitter cluster: Motorola APX (P25 radio), Axon Fleet 3 dashcam (WiFi+BLE), Getac laptop (WiFi+BT), Cradlepoint/Sierra Wireless in-car router (LTE+WiFi), body cam BLE (Axon/Reveal/WatchGuard), driver phone. When any one of these is found in a deployment, the others are usually present too — useful for cross-corroboration during validation, and an argument for the §12 `device_cluster_id` question above.

## Open questions for human
- **§4.1 device_category enum extension** — Cradlepoint/Sierra Wireless are seeded with `primary_category=NULL` (multi-purpose pattern) because the enum doesn't yet have an `in_vehicle_router` value. _Blocking? n; flag at Phase 2 dispatch when the first router OUI/MAC actually lands. Future Correction Pass material._
- **§12 `device_cluster_id` design call** — added by Correction Pass 3. User holding for explicit decision; initial lean is scanner-side. Surface at Checkpoint 5 if unresolved by then. _Blocking? n_
- **WiGLE API credentials before Checkpoint 2** — user said "in your hands before you hit Checkpoint 2." User reconfirmed in MAC-1 d08ee4a8. _Blocking? n; required before Phase 3 Step-0 estimate fires._
- **Final project name confirmation at Checkpoint 5.** _Blocking? n_
- **`argus_record_id` upsert semantics in Talos v0.2 seeder** (BIBLE_AMENDMENTS SAR-2). _Blocking? n_

## Recent log (last 25 entries)
- 2026-05-04T02:30Z      CEO created Phase-1 subtask MAC-2 (`3e8c4825`) assigned to DBArchitect.
- 2026-05-04T02:35–02:37Z DBArchitect built migrations + init_db + manufacturers seed (32 vendors) + procurement_records + dedup module + 25 unit tests + argus_cli.py.
- 2026-05-04T02:42Z      DBArchitect returned MAC-2 `in_review` to CEO with original Checkpoint 1 summary (comment `765d6d31`).
- 2026-05-04T02:46Z      CEO verified artifacts; posted Checkpoint 1 review (comment `caba4a10`); reassigned MAC-2 to user `in_review`.
- 2026-05-04T02:52:55Z  Wake — MAC-1 comment 5d75988d: corrections approved BUT Phase-1 approval rescinded; require BIBLE_AMENDMENTS.md + re-issued Checkpoint 0.
- 2026-05-04T02:55Z      CEO blocked MAC-2 on MAC-1 (status=blocked, reassigned to DBArchitect).
- 2026-05-04T02:56Z      CEO wrote `BIBLE_AMENDMENTS.md`; commit `ab2e45c` (Correction Pass 1 + SAR-1 + SAR-2).
- 2026-05-04T02:57Z      CEO posted re-issued Checkpoint 0 status on MAC-1 (comment `4a7eb700`); state committed `9dc3cd9`.
- 2026-05-04T03:00:37Z  Wake — MAC-1 comment f08cd82b: ✅ Checkpoint 0 re-signed-off, ✅ Phase 1 re-approved, "re-validate don't rebuild," fill §11 #11 with the BIBLE_AMENDMENTS discipline rule, log Correction Pass 2, add SAR preamble note.
- 2026-05-04T03:0xZ      CEO applied §11 #11 fill (`1cfbbd4`), backfilled hash (`8590292`), added SAR preamble note. Reassigned MAC-2 to DBArchitect `todo` with re-validation spec; state committed `95bdd53`.
- 2026-05-04T03:07:33Z  Wake — MAC-1 comment 404742ab: user narrowed V1 focus to **Flock cameras + cop cars**. CEO surfaced bible gap (no Cradlepoint / Sierra Wireless in §2.1) and asked scope-vs-priority.
- 2026-05-04T03:11:25Z  Wake — MAC-2 comment ca3f4b75: DBArchitect Checkpoint 1 re-validation **complete, no deltas**. Schema/dedup/CLI/seed all match HEAD `8590292`.
- 2026-05-04T03:13:41Z  Wake — MAC-1 comment 13461971: user clarified Flock + cop cars is a soft prior, NOT scope narrowing or priority reweighting. No SAR-3, no Correction Pass 3 from this steer alone.
- 2026-05-04T03:23:31Z  Wake — MAC-1 comment d08ee4a8: 🟢 **Checkpoint 1 signed off.** Cradlepoint/Sierra Wireless gap approved as Correction Pass 3 (independent of the Flock advisory). device_cluster_id → §12. Research leads → PROJECT_STATE. Phase 2 hire request next, brief Source Workers with the standing Flock + cop-cars advisory.
- 2026-05-04T03:2xZ      CEO this heartbeat: applied Correction Pass 3 (§2.1 #5 added — option b; renumbered #5–#11 → #6–#12); added device_cluster_id question to §12 Open; updated manufacturers seed (32 → 34) with Cradlepoint + Sierra Wireless; renumbered §2.1 # references in seed comments; rebuilt argus.db; 25/25 dedup tests pass; argus_cli status clean; logged Correction Pass 3 in BIBLE_AMENDMENTS; added research leads section above. Closing MAC-2 done. Phase 2 Source Worker hire request next.

## Notes for human review
- **Cradlepoint/Sierra Wireless seeded with `primary_category=NULL`.** The §4.1 device_category enum does not yet have an `in_vehicle_router` value. Mirrors the Motorola Solutions / L3Harris multi-purpose-vendor pattern. The enum extension is a deliberate future decision: surface at Phase 2 dispatch if/when the first router OUI/MAC actually needs a category, not a Correction Pass 3 deliverable.
- **§2.1 number renumbering cascade was bounded.** Bible §2.1, seed comments in `db/migrations/0001_initial.sql`. PROJECT_STATE.md line-13 (in the historical log) references `#8/#9` — left as-is because that entry describes the state at the time it was written (32-vendor seed, pre-renumber) and is historical record, not live cross-reference. Going forward, all §2.1 # refs in new entries use the post-Correction-Pass-3 numbering.
