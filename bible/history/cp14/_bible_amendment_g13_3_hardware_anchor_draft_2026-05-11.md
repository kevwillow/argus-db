# Bible §8.4 Amendment Draft — Hardware-Anchor Model-Level Evidence (G-13.3)

**Status:** DRAFT for CEO ratification (§11 #11). CEO-authored under Wave-A ratification run authorization 2026-05-11. NOT applied to Bible HEAD.
**Trigger:** Phase 6ε (`GainSec/flock-safety-falcon-sparrow-alpr-edl-firehose`) hardware-anchored Flock Falcon-gen1 to Snapdragon 625 (MSM8953 / APQ8053) + PM8953 PMIC + PMI8950 companion. Phase 6δ (white paper NVS analysis) inferred MSM8956 (Snapdragon 650) for a different Flock device generation.
**Drafted by:** CEO (Argus Wave-A ratification run, 2026-05-11) under explicit human-CEO §11 #11 delegation.
**Gate:** G-13.3 (queue entry `raw/wave_a/_ceo_gates_queue_2026-05-11.md` plus appended G-13.3 update).

---

## 1. Current §8.4 (verbatim — pre-Wave-A close, post-CP13 HEAD)

(Refer to `_bible_amendment_la_bit_draft_2026-05-11.md` §1 for the verbatim block — identical pre-amendment baseline.)

**Adjacent context:** §8.4's first bullet establishes that "Category requires model-level evidence" — an OUI alone never gets a `device_category` other than `unknown`. This amendment formalizes what counts as model-level evidence at the **chipset / hardware-anchor** layer, which is structurally distinct from the RF/MAC layer at which Argus's existing Flock evidence operates.

---

## 2. The hardware-anchor finding

### 2.1 Phase 6ε — Falcon-gen1 chipset extraction (single-source authoritative)

`ALPR-DDR-FIREHOSE.mbn` (354 KB Qualcomm signed Multi-Binary flashing tool, Phase 6ε):

| Component | Identifier | Source |
|---|---|---|
| SoC | Qualcomm Snapdragon 625 (MSM8953 / APQ8053) | Binary string + Qualcomm SecTools signer + DDR profile constants |
| PMIC primary | PM8953 | Same binary |
| PMIC companion | PMI8950 | Same binary |
| Bootloader signing key | Xiaomi Root CA 1 (Beijing) | See `feedback_supply_chain_pki_lineage.md` |

The MBN flashing tool is the device-side firmware payload — its existence is irrefutable evidence that Falcon-gen1 hardware uses these chipsets. This is **first-class model-level evidence**.

### 2.2 Phase 6δ — different-generation chipset inference (single-source hypothesis)

`GainSec/anti-crime-ecosystem-research` white paper NVS analysis surfaces **MSM8956 (Snapdragon 650)** for a different Flock device generation (referred to in the paper as Falcon/Sparrow/Flex variants per the paper's Flock-Lockee taxonomy).

**Difference between 6ε and 6δ evidence shapes:**
- 6ε = direct firmware-binary inspection. The MBN file IS the artifact running on hardware.
- 6δ = paper inference from NVS partition strings + analysis. One step removed from the device.

**Most likely interpretation:** 6ε = Falcon-gen1 (Snapdragon 625), 6δ = Falcon-gen2 or LPR/Compute-Box (Snapdragon 650). These are adjacent Qualcomm chipset numbers from the same SoC generation family.

### 2.3 Ratification disposition — Phase-2 self-review §2.2 question answered (REVISED)

Dispatch §2.2 asks: "Does your amendment ratify the hypothesis as bible-binding, or as 'model-level evidence pending corroboration'? Pick correctly; flag if ambiguous."

**Answer: the LENS-LEVEL rule is bible-binding; SPECIFIC GEN-MAPPINGS are 'model-level evidence pending corroboration' under existing §8.2 source-type bands (NOT a parallel H1/H2/H3 tier system).**

- The rule that *chipset binary inspection counts as model-level evidence* is a category-rule and ratifies into §8.4 unambiguously. It opens the structural slot for hardware-anchored attribution.
- **Phase-2 correction (2026-05-11):** the Phase-1 draft introduced parallel "Tier H1/H2/H3" promotion ceilings (H1=80, H2=60, H3=40). This was structurally wrong — Argus already has a source-type taxonomy in §8.2 with explicit confidence bands. The hardware-anchor amendment composes with §8.2, it does NOT replace it. **Drop the H1/H2/H3 framing.** Use §8.2's existing source-type bands directly.
- **Source-type classification for hardware-anchor evidence:**
  - **GainSec firmware-binary inspection (6ε)** classifies as `crowdsourced` per §8.2 (50–75 band). GainSec is community-published security research; the binary IS first-hand, but the repo provenance + the Falcon-attribution-via-repo-name chain is community-sourced. Phase-1 H1 ceiling of 80 was too high. Conservative ceiling: 75.
  - **GainSec white-paper inference (6δ)** classifies as `crowdsourced` same band; lower floor because of the inference step. Conservative single-source ceiling: 65 (within the 50–75 crowdsourced band).
  - **Future Flock teardown reportage from established outlets** could classify as `academic` (70–90) if peer-reviewed/conference, or `crowdsourced` (50–75) if blog-shape. Per-source determination.
  - **Future FCC EAS database citation** (test report with chipset spec) classifies as `regulatory` (80–95) — direct regulatory filing provenance.
- **Specific gen-mapping confidence at promotion time (Phase 4):**
  - Falcon-gen1 ↔ Snapdragon 625: single `crowdsourced` H1-shape source → confidence cap 75. With second-source corroboration to a `manufacturer_doc` or `regulatory` finding, lifts via §8.2 corroboration formula (`min(99, max(originals) + 5)`).
  - Falcon-gen2 ↔ Snapdragon 650: single `crowdsourced` H2-shape source → confidence cap 65. Same corroboration mechanics for uplift.
- Both hardware-anchored rows are linked via `paired_identifier_id` with `pair_kind='firmware_generation'` per the 0012 migration (CP14 sibling).

---

## 3. Proposed amendment

### 3.1 Option chosen: **Option A — extend §8.4 in place**

**Rationale:** §8.4's first bullet already establishes the principle that category requires model-level evidence. The hardware-anchor extension formalizes WHAT counts at the chipset layer — same axis, sub-rule of the existing "model-level evidence" requirement. In-place extension preserves §8.4 cohesion. No new section needed.

**Not Option B (new §8.5 hardware-anchor section):** The hardware-anchor rule is operationally close to the multi-purpose-vendor / Pi-self-exclude rules — same FP-prevention axis, same promotion-time disposition. Splitting into §8.5 would dilute §8.4.
**Not Option C (extend §8.3 corroboration arithmetic):** §8.3 governs source-count arithmetic; this amendment governs what counts as a source SHAPE. Different axis.

### 3.2 Amendment text (copy-pasteable into PROJECT_BIBLE.md)

**Edit §8.4 first bullet in place** (the "Multi-purpose vendors are not categorized at the OUI level" bullet) and **add a follow-up bullet** immediately after it. Adjust the existing bullet to reference the new one:

> - **Multi-purpose vendors are not categorized at the OUI level.** Motorola Solutions makes police radios *and* hospital pagers *and* warehouse scanners. An OUI alone never gets a `device_category` other than `unknown`. **Category requires model-level evidence** — see the model-level evidence sub-rule below for what counts.
>   - **Unknown-category Lynceus carveout.** (existing text — unchanged.)
>
> - **Model-level evidence — what counts (hardware-anchor sub-rule).** Acceptable forms of "model-level evidence" for lifting `device_category` beyond OUI-level `unknown`:
>   - **Direct firmware-binary inspection.** Chipset / SoC / PMIC constants extracted from a vendor-signed firmware binary running on the device (Qualcomm MBN, Mediatek SCATTER, NXP MFBL, etc.). The binary IS the artifact running on hardware; the chipset string is a first-hand observation. Provenance classification (per §8.2): the *attribution chain* (binary → product) is community-sourced when the binary is community-redistributed (e.g., GainSec repo) and `crowdsourced`-banded (50–75); regulatory-sourced when the binary is recovered via FCC test report and `regulatory`-banded (80–95); manufacturer-sourced when obtained directly from vendor documentation and `manufacturer_doc`-banded (75–90). Phase-4 promotion confidence MUST honor the §8.2 source-band ceiling — the binary-inspection observation does NOT itself lift confidence above its source-band cap.
>   - **Paper / report inference.** Chipset inference from indirect evidence (NVS partition string analysis, schematic/diagram OCR, teardown reportage, white-paper analysis). One step removed from the device. Classified per §8.2 same as above (community paper = `crowdsourced` 50–75; peer-reviewed = `academic` 70–90; regulatory disclosure = `regulatory` 80–95).
>   - **Community attribution / forum claim.** Unverified attribution from a community source classifies as `crowdsourced` or `News, forums, unverified` (20–50) per §8.2. Set `rationale_pending_verification` flag for the 20–50 case.
>
>   **No parallel tier system.** The hardware-anchor sub-rule composes with §8.2 source-bands; it does not introduce a parallel ceiling structure. Confidence at promotion = §8.2 band cap, lifted by §8.2 corroboration formula (`min(99, max(originals) + 5)`) when independent sources corroborate.
>
>   **Generation pairing.** When hardware-anchor evidence identifies multiple chipsets associated with successive product generations of the same vendor (e.g., Falcon-gen1 Snapdragon 625 + Falcon-gen2 Snapdragon 650), the rows MUST be paired via `paired_identifier_id` with `pair_kind='firmware_generation'` (per migration 0012). The paired-identifier discipline lets validator queries return both generations when the vendor + product-family is the query target.
>
>   **Identifier-type for hardware-anchor rows.** Chipset / PMIC anchors are NOT `oui` / `mac` rows. They are `device_fingerprint` type rows with the chipset designation as the `identifier` value (e.g., `'MSM8953'` / `'PM8953'`) and `manufacturer='Qualcomm'`, `model=<vendor>-<gen>` (e.g., `'Flock Falcon gen1'`). The vendor whose product anchors the chipset is the `model` field, NOT the `manufacturer` (which stays Qualcomm — the chipset maker is the canonical IEEE-registrant analogue here).

### 3.3 BIBLE_AMENDMENTS.md CP14 entry stub (REVISED Phase 2)

```
4.3 G-13.3 Hardware-anchor model-level evidence

Surfaced: Wave-A Phase 6ε (GainSec/flock-safety-falcon-sparrow firmware
binary inspection of ALPR-DDR-FIREHOSE.mbn — Snapdragon 625 / PM8953 /
PMI8950 confirmed for Falcon-gen1) + Phase 6δ (GainSec white paper NVS
inference of Snapdragon 650 for adjacent Falcon generation).
Resolution: §8.4 extended with model-level evidence sub-rule formalizing
direct firmware-binary inspection, paper/report inference, and community-
attribution as acceptable model-level evidence shapes; provenance bands
follow §8.2 source-type taxonomy (no parallel tier system introduced).
Paired_identifier_id 'firmware_generation' enum value (migration 0012)
supports gen1↔gen2 row pairing. Disposition: rule ratifies bible-binding;
specific gen-mappings promote at §8.2 ceiling (gen1 + gen2 both
`crowdsourced` 50-75 at single-source — both cap at 75 / 65 respectively
pending higher-band corroboration via §8.2 formula).
```

---

## 4. Edge cases NOT covered (validator-side discipline)

1. **Multi-chipset products.** Some surveillance products use multiple SoCs (e.g., a primary application processor + a cellular baseband + a separate vision/ML accelerator). Validator-side: each chipset gets its own hardware-anchor row, paired via `paired_identifier_id` with `pair_kind=NULL` (siblings within one product) or via a separate sibling-type if a future amendment introduces one. CP14 batch doesn't fold in multi-chipset pairing as a `pair_kind`; deferred to Wave-B if a concrete instance surfaces.
2. **Reused chipsets across vendors.** Snapdragon 625 is in dozens of consumer phones in addition to Falcon-gen1. The `model` field disambiguates by vendor-product, but coverage-report tallies must NOT count the chipset row as a "Snapdragon 625" emitter — it's a Falcon-gen1 emitter that happens to use Snapdragon 625. The `manufacturer='Qualcomm'` + `model='Flock Falcon gen1'` shape is intentional — the chipset is the IEEE-analog identifier; the product is the model.
3. **Chipset family vs specific part.** MSM8953 and APQ8053 are sibling SKUs of the Snapdragon 625 family (modem-enabled vs application-only). Validator stages each detected variant separately; family-level aggregation happens at query time, not at promotion.
4. **Boot-ROM signing keys are not hardware-anchors.** Qualcomm secure boot keys signed by SDO/CA roots (e.g., Xiaomi Root CA 1 in the 6ε MBN) are **supply-chain intelligence**, not hardware-anchor evidence. See `feedback_supply_chain_pki_lineage.md` for that disposition. The hardware-anchor amendment is specifically about chipset/SoC/PMIC identification — signing keys are an orthogonal layer.
5. **FCC ID lookup as Tier H2 source.** The FCC EAS database (`fcc_grantees` table, MAC-7 ingest) often lists chipset families in the test report. Validator may discover that some Tier-H2 chipset inferences are already corroborable from existing Argus data without external WebFetch — preferred over external corroboration.

---

## 5. Composition with other §8.4 rules (CP14 batch interactions)

- **G-1 protocol-container:** Independent. Chipset anchors are device-side identification; protocol-container OUIs are payload encapsulation. They compose only when a chipset-anchored device emits a protocol-container-prefixed payload (e.g., a Drone-RID-emitting drone with known Snapdragon SoC — both rows exist independently, neither requires the other).
- **G-4 LA-bit:** Independent. LA-bit pairing operates on MAC identifiers; hardware-anchor operates on chipset identifiers. Different identifier_type slots.
- **G-15 defensive_tool:** Composes. Defensive-tool hardware (Orbic RC400L per G-15) HAS a chipset anchor (the modem SoC). The defensive_tool exclusion list takes precedence — a Snapdragon-anchored Orbic still self-excludes from Lynceus high-confidence export per §11 #12.

---

## 6. Forward expectation

- Phase 4/5/6 ingest of additional Flock variants (Bravo / Sparrow / Flex / Picard / Raven per 6δ codename catalog) likely surfaces additional chipset anchors. Each generation maps to its own gen-pair sibling under `pair_kind='firmware_generation'`.
- DJI drone SoCs (Hisilicon variants) are a forward target for Wave-B+ firmware-mining. Same H1/H2/H3 tier structure applies.
- Stingray / IMSI-catcher hardware (Harris StingRay II, Hailstorm) is a forward target where FOIA-obtained schematic excerpts could land Tier-H2 evidence. Per current §11 #2 (no non-public data), only FOIA-released material qualifies.
- Cellebrite / forensic-extraction tools: chipset anchors are a forward target via teardown reportage (Tier H2).

---

## 7. Cross-references

- **`raw/wave_a/_ceo_gates_queue_2026-05-11.md` G-13** (3 sub-items) — original gate
- **`raw/wave_a/_ceo_gates_queue_2026-05-11.md` G-13.3 update** — Snapdragon 625 vs 650 gen distinction
- **`raw/wave_a/_phase4_aggregation_2026-05-11.md`** — Phase 6ε hardware-anchor extraction detail
- **`raw/wave_a/_phase6_aggregation_2026-05-11.md`** — Phase 6δ NVS inference detail
- **`feedback_supply_chain_pki_lineage.md`** (companion artifact this CP14 batch) — orthogonal Xiaomi-CA finding
- **`db/migrations/_drafts/0012_paired_identifier_id.sql.draft`** — `pair_kind='firmware_generation'` enum value
- **`feedback_agent_asserted_history_needs_verification.md`** — generational mapping inference discipline (gen1/gen2 mapping is single-source H1+H2 evidence; external corroboration desirable)
- **§11 #11:** This is a draft; ratification + the `BIBLE_AMENDMENTS.md` CP14 entry are CEO's at apply time.
