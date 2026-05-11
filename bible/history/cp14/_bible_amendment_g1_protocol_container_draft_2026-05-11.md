# Bible §8.4 Amendment Draft — Protocol-Container OUI Lens (G-1)

**Status:** DRAFT for CEO ratification (§11 #11). CEO-authored under Wave-A ratification run authorization 2026-05-11. NOT applied to Bible HEAD.
**Trigger:** G-1 sample-size cascade — `FA:0B:BC` ASD-STAN Beacon at n=5 (1d + 2c + 4a + 4b + 4c); `50:6F:9A` Wi-Fi Alliance NAN at n=3 (1d + 2c + 4c); `90:3A:E6` Parrot dual-lens at n=4 (1c + 2c + 3a + 4c).
**Drafted by:** CEO (Argus Wave-A ratification run, 2026-05-11) under explicit human-CEO §11 #11 delegation.
**Gate:** G-1 (queue entry `raw/wave_a/_ceo_gates_queue_2026-05-11.md`).

---

## 1. Current §8.4 (verbatim — pre-Wave-A close, post-CP13 HEAD)

(Refer to `_bible_amendment_la_bit_draft_2026-05-11.md` §1 for the verbatim block — identical pre-amendment baseline.)

**Adjacent context:** §4.1 (source provenance), §8.2 (source-type sub-banding incl. CP12 `manufacturer_app`), §8.3 (corroboration arithmetic). The protocol-container lens is a §8.4 FP-prevention extension because mis-assigning an SDO/protocol OUI as a "vendor OUI" is the most common false-positive failure mode for drone-RID and BLE-NAN identifiers.

---

## 2. The corroboration cascade

### 2.1 OUIs surfaced across Wave-A as protocol-container candidates

| OUI | Function | Sources | Wave-A count | Status |
|---|---|---|---|---|
| `FA:0B:BC` | ASD-STAN Beacon Drone-RID protocol-container | 1d + 2c + 4a + 4b + 4c | **n=5** | Promotion-ready |
| `50:6F:9A` | Wi-Fi Alliance NAN service prefix | 1d + 2c + 4c | **n=3** | Promotion-ready |
| `90:3A:E6` | Parrot — DUAL-LENS (product-vendor + protocol-container) | 1c + 2c + 3a + 4c | **n=4** | Promotion-ready as dual-lens (paired) |
| `88:69:19:9D:92:09` | NaN service ID (longer-than-OUI) | 1d + 4b | n=2 | Hold for Wave-B third-source |
| `6A:5C:35` | FRDID French national variant of ASD-STAN | 1d only | **n=1** | HOLD — single-source within Wave-A; external EU/FR firmware needed |

### 2.2 The lens distinction

A "vendor OUI" historically means **one of two**:
1. **Chip-vendor OUI** — IEEE-assigned to the silicon manufacturer (e.g., Qualcomm, Broadcom). Identifies the chipset, not the product.
2. **Product-vendor OUI** — IEEE-assigned to the device manufacturer (e.g., DJI's `60:60:1F`). Identifies the deployable product.

The Wave-A surfacings add a **third lens**:
3. **Protocol-container OUI** — IEEE/SDO-assigned to a standards body or protocol working group, used as a prefix wrapping a non-vendor-specific payload format. Examples: ASD-STAN Beacon (`FA:0B:BC`) wraps Drone-RID Bluetooth Legacy advertising; Wi-Fi Alliance (`50:6F:9A`) wraps NAN service messages. The OUI identifies the **encapsulation**, not the emitter's identity.

**Why the lens matters:** at promotion time, an OUI's `device_category` and `manufacturer` columns mean different things depending on which lens applies. A chip-vendor OUI categorized as `drone` would over-claim (the chipset is in N classes of device). A product-vendor OUI categorized as `drone` correctly attributes a specific product. A protocol-container OUI categorized as `drone` correctly identifies the **payload protocol** but tells you nothing about which product emitted it — every Drone-RID-emitting device wrapping its messages with ASD-STAN Beacon prefixes will show this OUI.

---

## 3. Proposed amendment

### 3.1 Option chosen: **Option A — extend §8.4 in place**

**Rationale:** §8.4 already owns the FP-prevention discipline including the Pi self-exclude list precedent (rule applies at promotion-time per-OUI). The protocol-container lens is structurally a same-class FP-prevention rule: misclassifying a protocol-container OUI as a vendor OUI is exactly the failure mode §8.4 exists to prevent. An in-place bullet preserves section-count and keeps the rule next to its peers (multi-purpose vendors / Pi self-exclude / MAC randomization). No need to add §8.5.

**Not Option B (new §8.5):** Same reasoning as the LA-bit draft — protocol-container lens is a sub-rule of FP-prevention, not peer to §8.1–§8.4.
**Not Option C (extend §4.1 source-lens framework):** §4.1 governs *how a source attests* (observation-lens vs registration-lens). Protocol-container lens governs *what the OUI identifies* (encapsulation vs emitter). Different axes; they compose at the validator but each has its own rule space.

### 3.2 Amendment text (copy-pasteable into PROJECT_BIBLE.md)

Insert as a new bullet in §8.4, between the **MAC randomization warning** and the **Locally-administered (U/L=1) OUI pairing discipline** bullets (the latter being G-4 from this same CP14 batch — see `_bible_amendment_la_bit_draft_2026-05-11.md`):

> - **Protocol-container OUI lens (third-lens discipline).** Some OUIs are IEEE-assigned to standards bodies or protocol working groups rather than to device-manufacturing vendors. When such an OUI is observed it identifies the **encapsulation format of a payload**, not the **identity of the emitting device**. The validator MUST distinguish three lenses at promotion time:
>   - **Chip-vendor lens** — OUI identifies the silicon (e.g., Qualcomm, Broadcom). `device_category='unknown'` unless model-level evidence; §8.4 multi-purpose-vendor discipline applies.
>   - **Product-vendor lens** — OUI identifies the deployable product (e.g., DJI's `60:60:1F`). `device_category` set by attribution; subject to §8.3 corroboration.
>   - **Protocol-container lens** — OUI is a standards-body / SDO assignment used as a prefix wrapping a payload format (e.g., ASD-STAN Beacon `FA:0B:BC`, Wi-Fi Alliance NAN `50:6F:9A`). `device_category` reflects the **payload protocol's typical emitter class** (e.g., `drone` for a Drone-RID protocol-container) and `manufacturer` is set to the SDO/working-group name (`'ASD-STAN'`, `'Wi-Fi Alliance'`), NOT to a device vendor. Multiple device vendors emit through the same protocol-container OUI; high-confidence individual-product attribution requires a second identifier (paired vendor OUI, device fingerprint, or model-level evidence per §8.2).
>
>   **Dual-lens case (vendor-as-container).** Some vendor OUIs carry BOTH lenses simultaneously — the OUI is product-vendor-assigned AND is used by that vendor as the encapsulation prefix for a Drone-RID or BLE-NAN payload. Parrot's `90:3A:E6` is the canonical example (Parrot products use the OUI as a MAC prefix AND as a vendor-IE prefix wrapping Drone-RID payloads). The validator records two paired identifiers rows linked via `paired_identifier_id` with `pair_kind='vendor_as_container'`: one row carries the product-vendor lens (`device_category=<product class>`), the other carries the protocol-container lens (`device_category=<payload protocol class>`). The validator picks the lens by observation context at query time.
>
>   **Within-lens corroboration discipline.** The protocol-container lens is a *category-level* rule (the lens exists); specific OUIs within the category each carry their own §8.3 corroboration counts. `FA:0B:BC` (n=5 Wave-A sources) is promotion-ready under the lens; `6A:5C:35` (FRDID, n=1 Wave-A source) is HELD at the §7.3 single-source confidence floor regardless of the lens's existence — promotion requires a second independent EU/FR transmitter-firmware source.

### 3.3 BIBLE_AMENDMENTS.md CP14 entry stub (for §3.2 of the dispatch coordinated commit)

```
4.2 G-1 standards-body protocol-container OUI lens

Surfaced: Wave-A Phases 1d (opendroneid/opendroneid-core-c) + 2c (Sky-Spy
+ xiao-c5-5g) + 4a/4b/4c (opendroneid receiver-android + wireshark-dissector
+ cyber-defence-campus HSLU thesis).
Sample size: FA:0B:BC at n=5; 50:6F:9A at n=3; 90:3A:E6 (dual-lens
vendor-as-container) at n=4; 88:69:19:9D:92:09 at n=2 (hold for Wave-B);
6A:5C:35 (FRDID) at n=1 (hold for external EU/FR firmware source).
Resolution: §8.4 extended with protocol-container lens distinction +
dual-lens vendor-as-container sub-case. Paired_identifier_id column landed
as 0012 sibling migration (G-7 enabler). FRDID stays single-source —
within-lens corroboration discipline rules apply to specific values, not
to the category-rule itself.
```

---

## 4. Edge cases NOT covered (validator-side discipline)

1. **NaN service ID values longer than 3-byte OUIs.** The `88:69:19:9D:92:09` form is a 6-byte NaN service ID, not a 3-byte OUI. The lens applies structurally — it's a protocol-container identifier — but the existing `identifiers.identifier_type='oui'` slot is shaped for 3-byte values. Validator-side: stage these under a separate type (`wifi_nan_param_signature` proposed in 0013 fold-in per dispatch §3.1.4) rather than as OUI rows.
2. **Wi-Fi Alliance OUIs other than `50:6F:9A`.** Wi-Fi Alliance has other registered OUIs that serve different roles (WPS, P2P, certification stickers). Lens classification per-OUI; do not generalize from `50:6F:9A` to all Wi-Fi Alliance OUIs.
3. **SDO OUI provenance verification.** For each candidate protocol-container OUI, the validator should verify the IEEE registry assignment matches the claimed SDO before promotion. `FA:0B:BC` per `feedback_agent_asserted_history_needs_verification.md` discipline — IEEE typically assigns U/L=0 MA-L blocks; a U/L=1 standards-body assignment may indicate a non-standard registry slot. (G-4 LA-bit interaction — handled by the LA-bit amendment §3.3 sibling-disposition rule when `pair_kind='la_bit_flip'` is wrong for a standards-body LA.)
4. **First-time-encountered SDOs.** When a new SDO OUI surfaces post-Wave-A, the validator stages it as `rationale_pending_verification` until the lens classification is independently corroborated (typically by a second source attesting the encapsulation use). Lens classification is itself a §8.2 corroboration target.
5. **Cross-protocol-container collisions.** If two SDOs are assigned the same OUI (none currently observed), the conflict-table routing per §4.2 applies — same mechanism as G-6 attribution disputes.

---

## 5. Composition with other §8.4 rules (CP14 batch interactions)

- **G-4 LA-bit:** Protocol-container OUIs with U/L=1 (e.g., `FA:0B:BC` first octet `0xFA = 1111_1010`, bit-1 = 1) interact non-trivially with the LA-bit pairing rule. Per G-4 draft §3.4 (forward expectation): "Edge case — LA OUI promoted before its IEEE sibling lands later in another phase. Mitigation: when an IEEE OUI lands, sweep for orphan LA children." Protocol-container LAs are typically self-assigned by the SDO and have no IEEE-assigned sibling. **Validator discipline:** when classifying an LA OUI, check the protocol-container lens FIRST (look up SDO registry / known protocol-container catalog); if matched, route as `pair_kind=NULL` (protocol-container, no pairing) rather than `pair_kind='la_bit_flip'` (which would assert a non-existent IEEE sibling). Adds a precedence rule between the two amendments.
- **G-13.3 firmware-generation:** Independent. Protocol-container OUIs do not have firmware generations (the OUI is registry-assigned, not chipset-anchored).
- **G-15 defensive_tool:** Independent. Protocol-container OUIs are surveillance-target identifiers (Drone-RID emitters), not operator-side defensive-tool hardware.

---

## 6. Forward expectation

- More protocol-container OUIs as Phase 5/6 ingests advance: Wi-Fi Alliance NAN, ASTM, 3GPP MBMS, CTIA, Bluetooth SIG mesh prefixes are all candidates.
- FRDID third-source: requires BlueMark/Dronetag firmware ingest OR an authoritative French national P1 profile document. Both are G-8 scope-expansion candidates (Wave-B+ territory).
- Dual-lens cases beyond Parrot: any vendor that operates a working group or contributes to an SDO carrying its OUI as a protocol-container is a candidate. Currently none observed beyond Parrot.

---

## 7. Cross-references

- **`raw/wave_a/_ceo_gates_queue_2026-05-11.md` G-1** — original gate
- **`raw/wave_a/_phase1_aggregation_2026-05-11.md` §4.1** — Phase 1d (opendroneid-core-c) initial surfacing
- **`raw/wave_a/colonelpanichacks_Sky-Spy/2026-05-11T05-00-35Z_surfacing.md`** — Phase 2c second-source corroboration
- **`raw/wave_a/_phase4_aggregation_2026-05-11.md`** — Phase 4a/4b/4c cascade to n=5
- **`raw/wave_a/_bible_amendment_la_bit_draft_2026-05-11.md` §7** — G-4 cross-reference (this draft composes the LA-bit precedence rule)
- **`db/migrations/_drafts/0012_paired_identifier_id.sql.draft`** — `pair_kind='vendor_as_container'` enum value for the dual-lens case
- **§11 #11:** This is a draft; ratification + the `BIBLE_AMENDMENTS.md` CP14 entry are CEO's at apply time.
