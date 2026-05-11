# Bible §8.4 Amendment Draft — Defensive-Tool Operator-Side Exclusion (G-15)

**Status:** DRAFT for CEO ratification (§11 #11). CEO-authored under Wave-A ratification run authorization 2026-05-11. NOT applied to Bible HEAD.
**Trigger:** Phase 6α (`EFForg/rayhunter`) — Rayhunter is a defensive surveillance-detection tool that runs ON Argus operator hardware (the human-CEO operates an Orbic RC400L per `research_leads/rayhunter_orbic_field_pcaps.md`). The Orbic's USB VID:PID `0x05c6:0xf601`, `/dev/diag` interface, and the Rayhunter-supported modem family (FY UZ801, PinePhone/Quectel, Wingtech CT2MHS01, T-Mobile TMOHS1, TP-Link M7350/M7310, Orbic RC400L) are operator-side identifiers that MUST NOT be exported to Lynceus as surveillance targets.
**Drafted by:** CEO (Argus Wave-A ratification run, 2026-05-11) under explicit human-CEO §11 #11 delegation.
**Gate:** G-15 (queue entry `raw/wave_a/_ceo_gates_queue_2026-05-11.md`).
**Dispatch §3 advisory priority:** apply G-15 FIRST among bible amendments — operator-hardware self-exclude prevents accidental Lynceus inclusion.

---

## 1. Current §8.4 (verbatim — pre-Wave-A close, post-CP13 HEAD)

(Refer to `_bible_amendment_la_bit_draft_2026-05-11.md` §1 for the verbatim block — identical pre-amendment baseline.)

**Existing precedent (Pi self-exclude bullet, copy-pasted from current §8.4):**

> - **Pi self-exclude list (running scanner's own hardware).** Lynceus runs on a Raspberry Pi, which has well-known OUIs:
>   - `b8:27:eb` (older Pi boards)
>   - `dc:a6:32` (Pi 4 era)
>   - `e4:5f:01` (recent boards)
>   - `28:cd:c1` (more recent)
>
>   These OUIs MUST NOT appear in the Lynceus high-confidence export, regardless of source confidence. They appear in the standard export (`argus_export.json`) with `severity='low'` and a description noting "informational — common in DIY hardware." This exclusion list is hard-coded in the export worker (§7.5) and tallied in the coverage report under `self_exclude_oui`. (See also §11 #12.)

The defensive_tool amendment extends this exact mechanic to a different operator-side hardware class.

---

## 2. The finding

### 2.1 Argus operator-side stack

The human-CEO operates the following hardware/software stack for Argus field work:
- **Hardware:** Orbic RC400L hotspot (Verizon rebrand of a Wingtech reference design). USB VID:PID `0x05c6:0xf601` enumerates a vendor-specific Qualcomm diagnostic interface.
- **Defensive tool:** EFForg/rayhunter running on the Orbic. Captures cellular signaling at the diag interface for IMSI-catcher detection.
- **Storage path:** `/dev/diag` — the modem diagnostic char device exposed by Qualcomm modems running in vendor-debug mode.

### 2.2 Rayhunter-supported modem family (forward-proofing per Phase-2 §2.3)

Phase-2 self-review §2.3 mandates: "the rule must scale to other Rayhunter-supported modems." Rayhunter's README lists the following supported targets, with concrete USB VID:PIDs and firmware-version markers extracted from the 6α surfacing (`raw/wave_a/EFForg_rayhunter/20260511T053123Z_surfacing.md` "Other supported-device fingerprints" + "Orbic RC400L modem-firmware identifiers" tables):

| Vendor / Model | USB VID:PID | Source provenance (6α surfacing) | Status |
|---|---|---|---|
| Orbic RC400L (Verizon) — modem mode | `0x05c6:0xf601` | `installer/src/orbic.rs:45-46` | Primary — CEO's field unit |
| Orbic RC400L (Verizon) — alt mode A | `0x05c6:0xf626` | `installer/src/orbic.rs:496` | Mode variant |
| Orbic RC400L (Verizon) — alt mode B | `0x05c6:0xf622` | `installer/src/orbic.rs:532` | Mode variant |
| Kajeet RC400L | identical hardware to Orbic (`0x05c6:0xf601`/`0xf626`/`0xf622`) | `doc/orbic.md` | Marketing rebrand |
| FY UZ801 | `0x05c6:0x90b6` (Qualcomm WCN36xx PRONTO) | `installer/src/uz801.rs:111` | Supported |
| PinePhone / PinePhone Pro | `0x2C7C:0x0125` (Quectel EG25-G) | `installer/src/pinephone.rs:18-19` | Supported |
| Wingtech CT2MHS01 | firmware version `CT2MHS01_0.04.55` at `/etc/wt_version` (no specific VID:PID surfaced) | `installer/src/wingtech.rs:13-15` | Supported (firmware-version-anchored) |
| T-Mobile TMOHS1 | firmware version `TMOHS1_00.05.20` (Wingtech OEM) | `installer/src/tmobile.rs:3-5` | Supported (firmware-version-anchored) |
| TP-Link M7350 / M7310 | hardware revs M7350 v3/v5/v9, M7310 v1 (no specific VID:PID surfaced) | `installer/src/tplink.rs:60-78` | Supported (hardware-rev-anchored) |

Vendor `0x05c6` is Qualcomm Inc. (well-known USB-IF assignment) — shared by Orbic and FY UZ801. Vendor `0x2C7C` is Quectel (Quectel-branded PinePhone modem). The self-exclude routes the VID:PID values directly; firmware-version-anchored and hardware-rev-anchored entries route via the `device_fingerprint` identifier_type with structured `notes` (consistent with §4 note 1).

Forward-proofing rule: the self-exclude list admits ANY Rayhunter-published supported-modem identifier without re-ratification. Rationale: any device on the Rayhunter supported-modem list is by definition operator-side for an Argus-class user — that's what the support means. Adding hardware to the Rayhunter list is upstream's curation; Argus mirrors it.

### 2.3 The structural difference from Pi self-exclude

| Aspect | Pi self-exclude (existing §8.4) | Defensive-tool self-exclude (this amendment) |
|---|---|---|
| Identifier shape | 3-byte IEEE OUI | USB VID:PID + diag device path + modem hardware product code |
| Storage | `identifier_type='oui'` | Mixed: future `usb_vid_pid` type, current `device_fingerprint` shape |
| List size | 4 entries (well-bounded, slow-growing) | ~8 entries (Rayhunter-supported modems) + future additions |
| Updates | Manual at next bible amendment | Mirrors Rayhunter upstream supported-modem list |

The structural difference is at the *identifier_type* level — Pi self-exclude is OUI-shaped; defensive-tool self-exclude is multi-shape (USB VID:PID, diag-path, and OUIs for the supported modems' Wi-Fi/BLE radios). The export-disposition mechanic is identical.

---

## 3. Proposed amendment

### 3.1 Option chosen: **Option A — extend §8.4 in place** (parallel to Pi self-exclude bullet)

**Rationale:** Same FP-prevention axis as the existing Pi self-exclude (operator-side hardware must not appear in the surveillance-target export). Same mechanic (hard-coded list, severity=low on standard export, banned from high-confidence export, tallied in coverage report). Sub-rule under §8.4, not peer-section.

**Not Option B (new §8.5 defensive-tool section):** Same reasoning as Pi self-exclude precedent — it's a §8.4 bullet, not a new section.
**Not Option C (extend §11 #12 with another #N):** §11 #12 codifies the Pi-specific rule; this amendment is the §8.4 mechanism that §11 #12 references. The §8.4 amendment is the structural seat; §11 update is the hard-rule companion (see §3.3 below).

### 3.2 Amendment text (copy-pasteable into PROJECT_BIBLE.md)

Insert as a new bullet in §8.4, **immediately after** the existing **Pi self-exclude list** bullet:

> - **Defensive-tool operator-side hardware self-exclude.** Hardware used by Argus operators to RUN defensive-tool software (e.g., Rayhunter for IMSI-catcher detection) must NOT appear in the Lynceus high-confidence export, regardless of source confidence. The Argus operator stack is by definition not a surveillance target. Three-layer exclusion list:
>   - **Modem hardware identifiers (USB VID:PID + diag interface):**
>     - `usb_vid_pid: 05c6:f601` — Orbic RC400L (Verizon) primary modem mode and Kajeet rebrand (same hardware).
>     - `usb_vid_pid: 05c6:f626` — Orbic RC400L alt mode A.
>     - `usb_vid_pid: 05c6:f622` — Orbic RC400L alt mode B.
>     - `usb_vid_pid: 05c6:90b6` — FY UZ801 (Qualcomm WCN36xx PRONTO).
>     - `usb_vid_pid: 2c7c:0125` — PinePhone / PinePhone Pro (Quectel EG25-G).
>     - `device_path: /dev/diag` — Qualcomm modem diagnostic char device (signals vendor-debug-mode modem; not specific to one OEM).
>   - **Rayhunter-supported modem family — firmware-version / hardware-rev anchored** (no specific VID:PID surfaced yet; route via `device_fingerprint`):
>     - Wingtech CT2MHS01 (firmware `CT2MHS01_0.04.55` at `/etc/wt_version`)
>     - T-Mobile TMOHS1 (firmware `TMOHS1_00.05.20`; Wingtech OEM)
>     - TP-Link M7350 (hardware revs v3/v5/v9)
>     - TP-Link M7310 (hardware rev v1)
>   - **List forward-proofs to mirror Rayhunter upstream curation** — when Rayhunter adds a new supported modem (with concrete VID:PID or firmware-version-anchored identifier), Argus mirrors it at the next ingest cycle without re-ratification.
>   - **Defensive-tool software identifiers (do not stage as surveillance signatures):**
>     - EFForg/rayhunter binary hashes, install paths, and configuration patterns observed on operator hardware are NOT staged as behavioral_signatures rows — they are operator-side tooling, not threat surface.
>
>   **Disposition mechanics (mirrors Pi self-exclude precedent):**
>   - These identifiers MUST NOT appear in the Lynceus high-confidence export under any confidence level.
>   - They appear in the standard export (`argus_export.json`) with `severity='low'` and a description noting "informational — Argus operator-side defensive-tool hardware (Rayhunter target list); not a surveillance target."
>   - The exclusion list is hard-coded in the export worker (§7.5) and tallied in the coverage report under `self_exclude_defensive_tool` (separate bucket from `self_exclude_oui` for the Pi list).
>   - When a new identifier matches the Rayhunter-supported list at promotion time, it routes to this self-exclude bucket automatically — no manual review required.
>
>   **Forward-proofing.** When Rayhunter upstream adds a new supported modem, Argus mirrors the addition at the next ingest cycle without re-ratification. The amendment is shaped to track upstream curation rather than enumerate a closed list. (See also §11 #12 update below — operator-stack exclusion is a hard rule across both Pi and defensive-tool branches.)

### 3.3 §11 #12 update (parallel hard-rule companion)

Edit §11 #12 in place to reference both branches:

> 12. **Operator-stack self-exclude.** Argus operator-side hardware MUST NOT appear in the Lynceus high-confidence export. This covers:
>     - **Lynceus host hardware** (Raspberry Pi OUIs per §8.4 Pi self-exclude bullet).
>     - **Defensive-tool hardware** (Rayhunter-supported modems per §8.4 defensive-tool self-exclude bullet, including the CEO's Orbic RC400L).
>     The exclusion is mandatory regardless of source confidence. Standard-export inclusion at `severity='low'` is permitted and documented per §8.4.

### 3.4 BIBLE_AMENDMENTS.md CP14 entry stub

```
4.4 G-15 Defensive-tool operator-side hardware self-exclude

Surfaced: Wave-A Phase 6α (EFForg/rayhunter). Argus operator (human-CEO)
runs Orbic RC400L + Rayhunter; the supported-modem family (8 device types
incl. Orbic + PinePhone/Quectel + Wingtech + TP-Link variants) defines
the operator-side hardware boundary.
Resolution: §8.4 extended with defensive-tool self-exclude bullet (mirrors
Pi self-exclude mechanic at USB VID:PID + diag-interface + modem-product
layers). §11 #12 updated to reference both Pi and defensive-tool branches
as one operator-stack hard rule. List forward-proofs to mirror Rayhunter
upstream supported-modem curation without re-ratification.
```

---

## 4. Edge cases NOT covered (validator-side discipline)

1. **Identifier-type for USB VID:PID values.** The current `identifiers.identifier_type` enum (post-CP13) does NOT include `usb_vid_pid`. Two options at validator-side promotion:
   - (a) Stage as `device_fingerprint` with `identifier='05c6:f601'` and a structured `notes` field describing the shape. Works with current schema.
   - (b) Wait for a future migration to add `usb_vid_pid` as a first-class identifier_type. Recommend deferring until a non-self-exclude USB VID:PID value surfaces (currently zero).
   - Phase 4 promotion-cycle-1: stage Orbic as `device_fingerprint` per Option (a). No migration needed for the self-exclude to function.
2. **Rayhunter target list drift.** Rayhunter upstream may add or remove supported modems between Argus heartbeats. The amendment's "forward-proofs to mirror upstream" language ratifies the principle but doesn't bind validator-side mirror frequency. Recommend: re-check upstream supported-modem list at every Argus version-bump (currently roughly every 2-4 weeks).
3. **Modem hardware also used as surveillance target.** Some of the Rayhunter-supported modems (e.g., Quectel EG25-G) are ALSO used in non-defensive contexts (drones, IoT, industrial). The exclusion applies to the *operator-side* attribution; a Quectel EG25-G observed in a drone identifier role still promotes to identifiers under the drone attribution lens. Disposition: the self-exclude is a Lynceus-export-side rule, not an `identifiers`-table-side rule. The row exists; the export drops it.
4. **Multiple operators with different defensive-tool stacks.** Argus is currently single-operator (CEO/Kev). If the deployment evolves to multi-operator (a Lynceus federation), each operator's defensive-tool stack would need its own self-exclude list. Deferred — not Wave-A scope.
5. **Defensive tools beyond Rayhunter.** Future amendments may add other defensive-tool ecosystems (e.g., SnoopSnitch, FBOR, srsRAN-based detectors). Each adds its own self-exclude bullet following this pattern. CP14 batch ratifies Rayhunter only; subsequent CPs handle additions.

---

## 5. Composition with other §8.4 rules (CP14 batch interactions)

- **Pi self-exclude (existing):** Composes — both are operator-stack self-excludes under §11 #12. Same export-side mechanic. Pi covers Lynceus host; defensive-tool covers Rayhunter modems.
- **G-1 protocol-container:** Independent. Protocol-container OUIs are surveillance-target identifiers (drone emitters); defensive-tool list is operator-side.
- **G-4 LA-bit:** Independent (no overlap with the listed Rayhunter-supported modems or Orbic VID:PID).
- **G-13.3 hardware-anchor:** Composes — see G-13.3 §5 "Defensive-tool exclusion takes precedence." A Snapdragon-anchored Orbic still self-excludes from Lynceus high-conf export per this amendment.

---

## 6. Forward expectation

- Phase 4-6 ingest may surface additional Rayhunter-supported modems with concrete USB VID:PID values. Each lands in the self-exclude bucket at promotion time.
- If Rayhunter upstream forks or merges with another defensive-tool project, the supported-modem list inheritance follows the new upstream — the amendment's forward-proofing language doesn't bind to one repo URL.
- Hardware-anchor evidence (G-13.3) for operator-side modems (e.g., the Quectel EG25-G Snapdragon platform) lands as a normal `device_fingerprint` row but with the defensive-tool exclusion firing at export.

---

## 7. Cross-references

- **`raw/wave_a/_ceo_gates_queue_2026-05-11.md` G-15** — original gate
- **`raw/wave_a/_phase4_aggregation_2026-05-11.md` / `_phase6_aggregation_2026-05-11.md`** — Phase 6α (rayhunter) surfacing detail
- **`research_leads/rayhunter_orbic_field_pcaps.md`** — operator-side context (CEO operates Orbic RC400L)
- **PROJECT_BIBLE.md §8.4 Pi self-exclude bullet** — structural precedent (this amendment copies the mechanic)
- **PROJECT_BIBLE.md §7.5** — export worker (the hard-coded self-exclude list lives here)
- **PROJECT_BIBLE.md §11 #12** — operator-stack hard rule (updated in §3.3 of this draft)
- **`db/migrations/_drafts/0012_paired_identifier_id.sql.draft`** — no direct interaction (defensive-tool list does NOT use paired_identifier_id)
- **§11 #11:** This is a draft; ratification + the `BIBLE_AMENDMENTS.md` CP14 entry are CEO's at apply time.
