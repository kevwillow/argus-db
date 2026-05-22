# Argus — Planned & Future Updates Queue

**Purpose:** v1.5.x patch + v1.6.0 backlog. Tracks deferred items from completed integration cycles.
**Discipline:** New items append at top of relevant section. Closed items move to "Completed" footer with commit anchor.
**Created:** 2026-05-22 (MAC-232 v1.5.0 Stage 1 Step 8).

---

## v1.5.x Patch Backlog (post-v1.5.0 ship; minor cycles)

### v1.5.x — Hub-and-spoke arm-split candidates (SEC Exhibit 21 bonus discoveries)

Pulled from v1.5.0 Stage 1 cohort SEC Exhibit 21 dossiers (MSI, GEO, TRMB, IOT FY2025 10-K filings):

| Candidate | Existing id | Parent | Evidence | Notes |
|-----------|-------------|--------|----------|-------|
| **Avigilon** arm-under-MSI | id=6 | id=3 Motorola Solutions | MSI 10-K FY2025 Exhibit 21 confirms "Avigilon Corporation (Canada)" as subsidiary | Same shape as Pelco arm-split landed in v1.5.0 Stage 1 (G-A). Apply at next patch with `is_arm=1, parent_manufacturer_id=3, query_default='hidden_arm'`. |
| **WatchGuard** arm-under-MSI | id=17 | id=3 Motorola Solutions | MSI 10-K confirms subsidiary | `notes.parent='Motorola Solutions'` backfill applied at v1.5.0 Stage 1 Step 4 (low-cost preview); full arm-split (is_arm=1) deferred. |

### v1.5.x — Disambig sub-cycle

| Item | Source | Volume | Notes |
|------|--------|--------|-------|
| **Elbit FCC grantee disambig** | `~/argus-internal/wave_v1_5_lexicon_expansion/session_1_military_federal/disambig_review_queue.json` | 168 entries | Per-row anchor-verification (FCC EAS direct or fccid.io verbatim) before canonical promotion. Estimated yield 5-20 confirmed Elbit/Tadiran subsidiary grantees from 168 candidates. Per [[CP33 §6.2]]. |

### v1.5.x — DJI aliases hygiene amendment (G-D)

Existing `manufacturers.id=22 (DJI)` aliases column contains a long comma-separated list of procurement-record vendor-bundling artifacts (`autel, dji`, `yuneec, dji`, `parrot, dji`, `lockheed martin, dji`). Per board G-D ratification: defer cleanup as separate amendment. Recommended approach:
- Audit DJI aliases for procurement-bundling contaminants
- Strip non-DJI vendor names from the comma-separated list
- Move legitimate DJI product family codenames (Mavic, Inspire, etc.) to `notes.product_family_codenames[]` (CP25 §3 typed enrichment per SAR-17)
- Surface in BIBLE_AMENDMENTS.md as a focused amendment-log entry

### v1.5.x — Geo Group admission + BI arm-split (G-F)

Per board G-F ratification: defer Geo Group admission + BI arm-split to v1.5.x. v1.5.0 Stage 1 admitted BI Incorporated as standalone. For v1.5.x:
- Admit Geo Group as new manufacturer (corporate parent)
- Flip BI Incorporated (id=258) to `is_arm=1, parent_manufacturer_id=<new Geo Group id>, query_default='hidden_arm'`
- Stage SEC Exhibit 21 evidence chain (GEO 10-K FY2025)

### v1.5.x — BriefCam recategorization decision (G-B deferred)

Per board G-B: BriefCam (id=31 currently `face_recog`) — defer cctv_camera vs face_recog disposition. Operator-decision required. Surface in dedicated dispatch.

---

## v1.6.0 New-cohort Backlog

### v1.6.0 — New manufacturer candidates (SEC Exhibit 21 bonus)

| Candidate | Domain | Cohort fit | Source |
|-----------|--------|------------|--------|
| **Openpath Security Inc.** | physical access control | adjacent to existing alpr/body_cam cohort | MSI 10-K FY2025 Exhibit 21 |
| **Silvus Technologies** | tactical MIMO radio | surveillance-adjacent; counter-UAS radio backhaul | MSI 10-K FY2025 Exhibit 21 |
| **VaaS International Holdings** | parent of Vigilant Solutions (Wave G v1.2.0) | arm-split candidate | MSI 10-K FY2025 |
| **RapidDeploy** | public-safety CAD | adjacent to body_cam/police_radio cohort | MSI 10-K FY2025 |
| **Rave Wireless** | emergency notification | adjacent to police_radio cohort | MSI 10-K FY2025 |

### v1.6.0 — Source re-attempts (0-yield deferrals from v1.5.0 Stage 1)

| Source | Status this cycle | Re-attempt path |
|--------|-------------------|-----------------|
| **DHS S&T** direct (not Wayback) | 0-yield via Wayback at v1.5.0; 403 anti-bot on www.dhs.gov direct | v1.6.0: alternative access path (residential IP? FOIA?) |
| **Google Play Store** companion-app extraction | empty `companion_app_extraction/` dir (0 files) at v1.5.0 | v1.6.0: dedicated companion-app sweep cycle |
| **ISED Canada** Radio Equipment Search | ~0-yield (1 hit; likely FP substring) at v1.5.0 | v1.6.0: dedicated Hanwha + cross-border Canadian-distributing vendor sweep |
| **ETSI Standards Database** | ~0-yield (1 hit; likely FP) at v1.5.0 | v1.6.0: dedicated European-vendor sweep (Bosch, Milestone, R&S) |
| **RRA Korea** Radio Equipment | unreachable from non-KR network at v1.5.0 | v1.6.0: KR-egress network (VPN, proxy) for Hanwha + Korean-vendor sweep |
| **State DOC Procurement Portals** | operator-opt-in pending at v1.5.0 | v1.6.0: per-state opt-in dispatch with CAPTCHA/Incapsula handling |

---

## CP34-Pending Candidates (next correction-pass cycle)

Discipline-evolution candidates surfaced during v1.5.0 Stage 1. Hold for monitoring; CP34 dispatch will fold these into formal bible-amendment cycle.

1. **Corporate-attestation routing** (Step 5 finding): Pre-route SEC EDGAR CIK anchors + Exhibit 21 + procurement_vendor_canonical at extraction time to the `manufacturers` / `procurement_records` workflows, not to `identifier_candidates`. Step 5 had to skip 20 such rows that weren't identifier-shaped. Future: dedicated extractor output channel.

2. **S2 GitHub codename×3 dedup at extraction-time** (Step 5 finding): Step 5 collapsed 63 raw rows to 21 distinct INSERTs due to upstream extractor duplicating each finding 3× (per per-vendor per-source per-cohort). Move dedup to extraction-time to reduce post-ingest collapse.

3. **identifier_type CHECK lacks `ip_address`** (Step 5 finding): 1 wayback_pdf row (Robin Radar `135.0.0.0` type=`ip_address`) was out-of-enum. Options: (a) admit `ip_address` as identifier_type (next CP), (b) route IPv4-shaped to existing `network_endpoint`.

4. **Legacy-text-notes normalization sweep** (Step 6 finding): 5 rows on Axis Communications (id=415, 433, 448, 460, 470 from MAC-44 era) had plain-text notes pre-dating the JSON-notes convention. Step 6 wrapped them into `{"legacy_text_notes": "<original>"}` JSON envelope at the recat-touch moment. CP34 sweep: scan all rows for non-JSON notes; wrap consistently.

5. **Short-generic-alias migration to product_family_codenames** (Step 7 / SAR-17 finding): Retroactive sweep of existing canonicals with short generic aliases (e.g., DJI's procurement-bundling artifacts, any vendor with single-word product aliases in the `aliases` column). Move to typed `notes.product_family_codenames[]` per CP25 §3 + SAR-17 discipline.

6. **NDAA §889 attribution key normalization** (Step 4 finding): Existing canonical Hikvision/Dahua use `notes.ndaa_section_889_note` (single-field); MAC-232 dispatch proposed (and S2 staged) `notes.ndaa_section_889_affected=true` + `notes.ndaa_attribution_note` (dual-key). Step 4 applied both formats to Uniview/Tiandy for query-path parity. CP34: pick canonical format + sweep all NDAA-tagged rows.

7. **Dispatch-claim-vs-actual schema-truth audit** (recurring): v1.5.0 Stage 1 surfaced 3 dispatch-claim drifts: pair_kind "4 values" (G-E), NDAA §889 precedent key shape (Step 4), S1 disambig queue composition (Step 7). CP34: codify a Validator-side "dispatch live-state preamble verification" sub-rule extending [[feedback_dispatch_preamble_live_state_verification]].

---

## Completed (v1.5.0 Stage 1 — MAC-232)

Items resolved in v1.5.0 Stage 1 — link to commit anchors for cycle-close audit:

- **WatchGuard Video parent backfill** — `notes.parent='Motorola Solutions'` applied at Step 4 commit `99d713b`
- **Pelco arm-under-MSI** — G-A applied at Step 4 commit `99d713b` (id=254, parent_manufacturer_id=3, is_arm=1)
- **CCTV retroactive recat (7 of 8)** — G-B applied at Step 6 commit `0e13b20`; BriefCam deferred
- **SAR-16 + SAR-17 codifications** — Step 7 commit `ecf6d4b`
- **2 new source admissions** — Step 2 commit `d73a788` (sid=72 GitHub Code Search REST + sid=73 adsb.lol v2)
- **mig-0027 CP33** — Step 3 commit `2128299` (schema 26→27; +3 device_category, +1 identifier_type)
- **848 net identifier promotions** — Step 5 commit `24ccfa5` (sweep_event_id `mac232_v1_5_0_stage1_step5_2026_05_22`)
