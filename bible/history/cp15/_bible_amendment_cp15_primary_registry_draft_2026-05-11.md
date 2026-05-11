# Bible §8.2 Amendment Draft — `primary_registry` source-type band (CP15)

**Status:** DRAFT for CEO ratification (§11 #11). CEO-authored under MAC-63 Wave-A Ratification Run authorization 2026-05-11 — Phase 5 deliverable per board direction at MAC-63 [`2b2cb0cf`](/MAC/issues/MAC-63#comment-2b2cb0cf-7796-4a43-a39e-f16d77a435f6). **NOT applied** to Bible HEAD; CP15 ratification is a separate human-CEO heartbeat after Wave-A close. This draft IS the Phase 5 substantive deliverable.
**Trigger:** Three structurally-equivalent §8.2 source-band questions surfaced during MAC-63 Phase 4 promotion-cycle-1:
1. FAA RID 481 `drone_id_prefix` rows (alphafox02/DragonSync Wave-A 3a) — single authoritative federal-numerical-allocation source; dispatch §4.1's "≥3 independent sources" cut-off is structurally ill-defined for "what does `1581Fxxx` mean at FAA?"
2. Apple `0x004C` ble_manufacturer_id (Wave-A 1a + 2a + others) — Bluetooth SIG company-identifier registry is the source-of-truth for "what does `0x004C` mean at SIG?"
3. XUNTONG `0x09C8` ble_manufacturer_id (Wave-A 1a + 2+ others) — same structural shape as Apple

Board's reframe at MAC-63 [`fe2beeee`](/MAC/issues/MAC-63#comment-fe2beeee-2571-475e-86f6-edc99f99ecad) 2026-05-11: "asking for 'three independent sources' of what 1581Fxxx means is structurally ill-defined because FAA's registry IS the source of truth." A new §8.2 source-band resolves all three.
**Drafted by:** CEO (Argus Wave-A Ratification Run, Phase 5).
**Cross-refs:** G-1 (protocol-container OUI lens — SDO-assigned OUIs are registry-issued by Wi-Fi Alliance / ASD-STAN / etc.), G-3 (`ble_manufacturer_id` — SIG-issued), G-7 (`paired_identifier_id` — composes with primary_registry), G-9 (`drone_id_prefix` — FAA-issued; 481-row HOLD batch is the canonical example).

---

## 1. Current §8.2 (verbatim — pre-CP15 / post-CP14 / Bible HEAD `421b4b5`)

The current §8.2 source-type confidence band table:

| Source type | Default confidence range |
|---|---|
| `official` (IEEE registry, FCC filing) | 90–100 |
| `regulatory` (gov't filing, court order text) | 80–95 |
| `manufacturer_doc` (vendor spec sheet) | 75–90 |
| `procurement` (SAM.gov, state portals) | 70–85 (proves *purchase*, not *deployment*) |
| `academic` (peer-reviewed or conference) | 70–90 |
| `foia` (released documents) | 65–85 |
| `crowdsourced` (WiGLE, DeFlock) | 50–75 |
| `manufacturer_app` (vendor companion APK/IPA static-analysis extract) | 60–95 (sub-banded by identifier class — see below) |
| `inferred` (derived) | 30–70, capped |
| News, forums, unverified | 20–50 |

Plus the §8.2 corroboration mechanic: "Two independent sources at 70 each can corroborate to a single record at 85." And the §8.3 dedup formula: `min(99, max(originals) + 5)` on merge.

**The structural gap:** the current `official` band lumps **IEEE registry assignments** (which ARE numerical-allocation registries — IEEE is the issuing authority for what an OUI means) together with **FCC filings** (which are regulatory submissions about deployed devices). These are different shapes of provenance with different failure modes. The "IEEE registry" half of `official` is structurally identical to FAA RID (FAA-issued drone-prefix registry), Bluetooth SIG company-identifier registry, IANA assignments — all of them are *authoritative numerical-allocation registries* where the issuer IS the source of truth for what the identifier means.

The "FCC filing" half of `official` is structurally similar to other `regulatory` filings (court-verifiable, third-party-citable, contested-in-court). It already lives near the `regulatory` band's ceiling (95).

CP15 splits the gap: move IEEE OUI registry into a new `primary_registry` band alongside FAA RID + SIG company IDs + IANA assignments. The `official` band keeps FCC filings (which are §regulatory by nature) and any future court-verifiable filings.

---

## 2. The CP15 amendment

### 2.1 Option chosen: **Option A — new §8.2 source-type band**

**Rationale:** Three structurally-equivalent Wave-A surfacings (FAA RID + SIG Apple/XUNTONG) deserve a structurally-distinct source-band. Forcing them into `crowdsourced` (which is what Wave-A staging defaulted to) caps confidence at 75 even though the originating registry IS authoritative. Forcing them into `regulatory` over-attributes (FAA RID and SIG IDs are not court-verifiable in the regulatory-filing sense — they're issuer-of-record records). The CP14 G-13.3 §8.2-alignment work explicitly preserved §8.2 as the canonical source-banding mechanism (per Phase 2 catch ratified by board at MAC-63 `bbb71be5`); CP15 extends that mechanism cleanly rather than introducing a parallel ceiling system.

**Not Option B (broaden `official` to include all authoritative registries):** `official` currently spans IEEE + FCC at 90–100; broadening would dilute the band semantically (FCC court-verifiability is a stronger claim than numerical-allocation-registry-issuance).
**Not Option C (case-by-case waiver of ≥3-source cut-off):** The dispatch §4.1 cut-off has good reasons. Per-case waivers would erode the discipline. A new source-band makes the rule structural rather than ad-hoc.
**Not Option D (defer to validator-side discretion):** Validator routes; it doesn't make §8.2 contract decisions. CP15 is a bible-§-text amendment so validator follows the same discipline as Phase-4 CEO-class promotion.

### 2.2 Amendment text (copy-pasteable into PROJECT_BIBLE.md)

**Edit §8.2 source-band table to insert a new row** (in canonical order — between `official` and `regulatory`):

| Source type | Default confidence range |
|---|---|
| `official` (FCC filing, court order text — the regulatory-filing half) | 90–100 |
| **`primary_registry` (authoritative numerical-allocation registries — see §8.2 sub-rule below)** | **70–85 single-source; up to 95 with cross-band corroboration** |
| `regulatory` (gov't filing, court order text — non-`official`-tier regulatory provenance) | 80–95 |
| ... (rest unchanged) | ... |

**And edit the `official` band description** to note its narrowed scope (IEEE OUI registry moves OUT to `primary_registry`):

| Source type | Default confidence range |
|---|---|
| `official` (court-verifiable government filings — FCC EAS, FAA enforcement orders, court-ordered disclosures) | 90–100 |

**Add a new §8.2 sub-rule** immediately after the source-band table, before the existing `manufacturer_app` sub-banding section:

> **`primary_registry` sub-banding (added Correction Pass 15 for the FAA RID + Bluetooth SIG + IEEE OUI registry cluster).**
>
> `primary_registry` covers authoritative numerical-allocation registries maintained by standards bodies, standards-development organizations (SDOs), or regulatory authorities where the registry IS the source-of-truth for what the identifier means. Canonical examples:
>
>   - **IEEE OUI registry** (MA-L 24-bit, MA-M 28-bit, MA-S 36-bit). IEEE assigns OUI blocks; the registry record IS the canonical attribution of OUI → manufacturer. (Migrates FROM `official` band into `primary_registry`.)
>   - **Bluetooth SIG company-identifier registry.** SIG assigns 16-bit BLE company IDs; the registry IS the canonical attribution of `0x004C` → Apple, etc.
>   - **FAA ANSI/CTA-2063-A RID registry.** FAA assigns drone serial-number prefixes; the registry IS the canonical attribution of `1581Fxxx` → DJI, `1748xxxx` → Autel, etc.
>   - **IANA assignments.** When Argus eventually ingests IANA-managed namespaces (port numbers, protocol numbers, etc.), they land here.
>
> **Distinguishing test (apply at ingest time):** ask "is this source the source-of-truth for what the identifier *means*, or is it a third-party assertion about meaning?"
>   - Registry-as-issuer → `primary_registry`.
>   - Third-party citing the registry → `crowdsourced` (50–75 band) or `manufacturer_doc` (75–90 band) per existing rules.
>   - Court-verifiable government filing about a deployed instance → `regulatory` (80–95 band) or `official` (90–100 band).
>
> **Confidence ceiling rationale:**
>   - **70–85 single-source** for `primary_registry`. The floor of 70 sits above `crowdsourced`'s ceiling of 75 (registry issuance carries more authority than community curation). The ceiling of 85 sits below `regulatory`'s 95 (registries are issuer-of-record but not court-verifiable in the regulatory-filing sense) and below `manufacturer_doc`'s 90 (the registry can name a manufacturer, but the manufacturer's own spec sheet may carry additional model-level detail the registry doesn't capture).
>   - **Up to 95 with cross-band corroboration.** When a `primary_registry` row is additionally corroborated by `regulatory` or `manufacturer_doc` sources, §8.3 corroboration formula (`min(99, max(originals) + 5)`) applies. Example: IEEE OUI registry (primary_registry, 85) + FCC EAS test report citing the same OUI (regulatory, 90) corroborates to a single record at confidence min(99, max(85,90)+5) = 95.
>
> **Waiver of ≥3-independent-sources cut-off for `primary_registry`.** The Phase-4 promotion-cycle cut-off requiring `independent_source_count ≥ 3` does NOT apply to `primary_registry` rows. The waiver is `primary_registry`-only — other source-band cut-off rules remain in force. Justification: asking for "three independent sources" of what `1581Fxxx` means at FAA is structurally ill-defined — FAA's registry IS the source of truth, and there is no parallel source-of-truth to corroborate against. A single primary_registry citation IS sufficient evidence under §11 #1 (no fabrication) because the registry's own publication is verifiable.
>
> **Reclassification discipline (§11 #8 boundary).** Reclassification of an existing `identifiers` row from `crowdsourced` / `inferred` to `primary_registry` is permissible ONLY when the row's existing `source_url` already points DIRECTLY at the registry issuer's own publication (FAA's database URL, SIG's company-identifier registry URL, IEEE's MA-L assignment record URL, etc.). If the `source_url` points at a third-party citation — community repo, blog post, aggregator, even an academic paper that cites the registry — the row stays in its current band. To establish `primary_registry` classification, a new `raw_observations` row citing the registry directly is required, per §11 #1 provenance discipline. Reclassification is a band-correction within preserved provenance, NOT a provenance shortcut. The §11 #8 "no confidence drift" rule composes: band-correction with the new ceiling re-applies to a row whose direct provenance qualifies; rows whose direct provenance is third-party stay capped at their current band's ceiling regardless of upstream-registry ancestry.
>
> **Composition with existing §8.4 lenses (CP14 cross-references):**
>   - **G-1 protocol-container OUI lens.** SDO-assigned OUIs (`FA:0B:BC` ASD-STAN, `50:6F:9A` Wi-Fi Alliance) classify as `primary_registry` when sourced from the SDO's own registry, and as `crowdsourced` when sourced from a community repo citing the SDO. CP15 + G-1 compose: protocol-container lens governs `device_category` semantics; `primary_registry` band governs confidence.
>   - **G-3 `ble_manufacturer_id`.** SIG-assigned values like `0x004C` Apple + `0x09C8` XUNTONG are `primary_registry` when sourced from the SIG company-identifier registry. Wave-A community-repo citations remain `crowdsourced` 50–75; SIG-registry direct citation lifts to `primary_registry` 70–85.
>   - **G-7 `paired_identifier_id` + `pair_kind`.** Independent. Pairing discipline operates on identifier structure (LA-bit flip, vendor-as-container, firmware-generation); source-band classification is orthogonal.
>   - **G-9 `drone_id_prefix`.** FAA RID is the canonical `primary_registry` case driving CP15. The 481-row FAA RID batch HELD from Phase-4 promotion-cycle-1 promotes at confidence 85 per `primary_registry` single-source rule once CP15 ratifies.

### 2.3 BIBLE_AMENDMENTS.md CP15 entry stub

```
## Correction Pass 15 — §8.2 primary_registry source-type band

**Date:** 2026-05-11 (drafted); ratification deferred to separate
human-CEO heartbeat after Wave-A close per board direction at MAC-63
[`2b2cb0cf`].
**Source:** [MAC-63](/MAC/issues/MAC-63) Wave-A CEO Ratification Run
Phase 5. Surfaced from FAA RID 481-row HOLD batch + Apple 0x004C +
XUNTONG 0x09C8 structural-equivalence finding. Board reframe at MAC-63
[`fe2beeee`] 2026-05-11.

### Why this Correction Pass exists

Three Wave-A surfacings (FAA RID via alphafox02/DragonSync Phase 3a;
Apple 0x004C + XUNTONG 0x09C8 ble_manufacturer_id Phase 1a/2+) share a
structural shape that the current §8.2 source-band table does NOT
accommodate cleanly:

  - Authoritative numerical-allocation registries (IEEE OUI, Bluetooth
    SIG company IDs, FAA RID, IANA) where the issuing authority IS the
    source-of-truth for what the identifier means.
  - Dispatch §4.1 ≥3-independent-sources cut-off is structurally
    ill-defined for these — "what does 1581Fxxx mean at FAA?" has one
    source-of-truth, not three.
  - Existing `official` band conflates registry-issuance with
    regulatory-filing; existing `crowdsourced` band caps at 75 (too
    low for registry-direct citations).

### Corrections applied

  1. **§8.2 source-band table** — insert new row `primary_registry`
     (70–85 single-source; up to 95 cross-band corroboration) between
     existing `official` and `regulatory` bands.
  2. **§8.2 `official` band description** — narrow to court-verifiable
     government filings only (FCC EAS, FAA enforcement orders, court-
     ordered disclosures). IEEE OUI registry migrates to
     `primary_registry`.
  3. **§8.2 `primary_registry` sub-rule** — added immediately after the
     source-band table; defines the distinguishing-issuer test,
     confidence ceiling rationale, ≥3-source-cut-off waiver, and
     composition with §8.4 CP14 lenses (G-1/G-3/G-7/G-9).

### Sequencing post-acceptance

  1. CP15 ratifies at the human-CEO ratification heartbeat (board
     determines ratification timing — out of MAC-63 scope).
  2. Schema-sibling migration `0015_primary_registry_source_type_extension.sql`
     adds `primary_registry` to `identifiers.source_type` + `sources.source_type`
     CHECK enums (table-rebuild per 0009 precedent).
  3. Promotion-cycle-2 sweeps the three CP15-unblocked HOLD batches:
       - FAA RID 481 drone_id_prefix rows (alphafox02/DragonSync 3a)
       - Apple 0x004C ble_manufacturer_id (Wave-A multi-phase)
       - XUNTONG 0x09C8 ble_manufacturer_id (Wave-A multi-phase)
     483 rows total, all single-source primary_registry, ceiling 85.
  4. Sources reclassification (Wave-B+): IEEE OUI bulk-load source row
     (currently source_type='regulatory') migrates to
     source_type='primary_registry'. Backfill 154 existing identifiers
     rows whose ancestry traces back to IEEE OUI — confidence values
     hold because §8.2 ceiling for primary_registry (85) >= existing
     IEEE-anchored conf values (none exceed 85 today).

### §11 hard-rule discipline

  - §11 #1 (no fabrication) — every primary_registry citation must
    name the registry-issuer AND include source_url pointing at the
    issuer's own publication (FAA's database, SIG's registry, IEEE's
    MA-L assignment record, etc.). Third-party-repo citations of the
    same identifier remain crowdsourced.
  - §11 #7 (provenance) — primary_registry rows carry the same
    raw_observations ancestry discipline as other promotion paths
    (Bible §7.3 worker-role separation; raw_observations.source_url
    + source_excerpt populated from the registry-issuer publication).
  - §11 #8 (no confidence drift) — single-source primary_registry
    promotes to 70–85; corroboration follows §8.2 formula.
    Reclassification from `crowdsourced` / `inferred` to
    `primary_registry` is permissible ONLY when the row's existing
    source_url already points DIRECTLY at the registry issuer's own
    publication (FAA's database URL, SIG's company-identifier registry
    URL, IEEE's MA-L assignment record URL, etc.). If the source_url
    points at a third-party citation — community repo, blog post,
    aggregator, even an academic paper that cites the registry — the
    row stays in its current band. To establish `primary_registry`
    classification, a new `raw_observations` row citing the registry
    directly is required, per §11 #1 provenance discipline.
    Reclassification is a band-correction within preserved provenance,
    NOT a provenance shortcut. (Phase-1 refinement 1.2 per board
    direction `c0e91b23` 2026-05-11: closes the "ancestry chain"
    loophole — a chain of citations from blog → registry would have
    qualified under the draft's original phrasing; the tightened rule
    requires the row's own source_url to be the direct registry citation.)
  - §11 #11 — this CP15 entry is the amendment-log closure for the
    §8.2 amendment in this coordinated commit.
```

---

## 3. Edge cases NOT covered (validator-side discipline)

1. **Multi-registry assignment for the same identifier.** Rare case: an identifier appears in two primary registries (e.g., an IEEE-issued OUI also referenced in an FAA filing as part of a drone-prefix assignment). Validator-side disposition: take the most-direct registry citation (the registry that ISSUES the identifier value) as `primary_registry`; secondary citations classify per their own source nature.

  **Edge sub-case NOT covered by CP15:** registry-internal reassignment (e.g., IEEE reassigns a defunct company's OUI to a successor). Route such cases to the `conflicts` table with `reason='registry_reassignment'` for human-CEO disposition. A future CP may codify reassignment-discipline if frequency warrants. CP15 explicitly does NOT legislate this case. (Phase-1 refinement 1.3 per board direction `c0e91b23` 2026-05-11: replaced the original draft's "higher-authority registry" framing — which would have required CP15 to define an authority-ranking between registries without supporting precedent — with a "most-direct citation" rule that doesn't legislate speculative ranking. Reassignment edge-case explicitly routed to conflicts table rather than codified in CP15.)
2. **Registry deprecation / supersession.** If a primary_registry retires (e.g., a deprecated IANA assignment), legacy rows holding the deprecated value classify as `crowdsourced` at re-promotion time per "source-no-longer-issuing" rule. Wave-B+ scope.
3. **Forgery / spoofing of registry citations.** If a Wave-A source claims to cite a registry but the citation is fabricated (e.g., source_url points at a non-existent FAA RID record), validator's §11 #1 audit catches it. Same audit discipline as for other source-types.
4. **Bluetooth SIG private-company-identifier assignments.** SIG offers both public-registry and private (NDA-gated) company-ID assignments. Argus only ingests public-registry citations per §11 #2 (no non-public data). The private NDA tier is structurally excluded.
5. **Cross-band normalization of historical IEEE-OUI rows.** Pre-CP15, IEEE OUI rows in `identifiers` carry `source_type='inferred'` or `source_type='crowdsourced'` (per Wave-A 1a + bulk-load patterns). Post-CP15 Wave-B sweep migrates these to `source_type='primary_registry'` where the provenance chain qualifies; confidence values hold (no §11 #8 drift, just re-classification).

---

## 4. Composition with other CP14 amendments (regression check)

- **G-1 protocol-container OUI lens.** Composes. Protocol-container OUIs (`FA:0B:BC`, `50:6F:9A`) that source from SDO-issued registries lift to `primary_registry` at promotion; community-repo citations remain `crowdsourced`. Lens (device_category semantics) + source-band (confidence) are orthogonal axes.
- **G-4 LA-bit U/L-flip pairing.** Composes. LA-variant rows (like the new id=566 DJI `62:60:1f`) inherit `source_type` from their single Wave-A source — that's `crowdsourced` for tesorrells/RF-Drone-Detection. If a future Wave-B FAA-registry-issued LA-variant emerges, it would be `primary_registry`. Pair_kind classification doesn't change with source-band reclassification.
- **G-13.3 hardware-anchor.** Composes. Hardware-anchor evidence stays per CP14 G-13.3: firmware-binary inspection from a community-published binary is `crowdsourced` 50–75; from a manufacturer doc is `manufacturer_doc` 75–90; from a regulatory disclosure is `regulatory` 80–95. None of these are `primary_registry` (chipset numbers like MSM8953 aren't registry-issued in the FAA RID / SIG sense — they're vendor-assigned model numbers).
- **G-15 defensive-tool self-exclude.** Independent. Self-exclude is an export-side discipline (§7.5); source-band classification is an ingest-side discipline (§8.2). They compose only at the validator-routing layer.

---

## 5. Forward expectation

- **CP15 ratification heartbeat** lands the §8.2 amendment + the schema migration 0015 (table-rebuild adding `primary_registry` to `identifiers.source_type` + `sources.source_type` CHECK enums). Per cumulative-CHECK-enum discipline (`feedback_cumulative_check_enum_across_sequenced_migrations.md`), 0015's CHECK must enumerate every prior CP's source_type contribution + `primary_registry`.
- **Promotion-cycle-2** sweeps the three CP15-unblocked HOLD batches (483 rows total). FAA RID 481 promotes single-source at confidence 85. Apple `0x004C` + XUNTONG `0x09C8` promote single-source at the same ceiling (SIG registry is the source-of-truth; Wave-A multi-phase citations corroborate but don't lift above 85 unless a cross-band source — regulatory FCC filing or manufacturer spec — adds).
- **Sources reclassification (Wave-B+ batch task).** IEEE OUI registry source (`sources.id=1`) migrates from `source_type='regulatory'` to `source_type='primary_registry'`. Bulk-load `identifiers` rows promoted FROM that source can re-classify forward at re-promotion or at a dedicated reclassification heartbeat. No data loss; just band-correction.

  **Scope acknowledgment** (added Phase-1 refinement 1.1 per board direction `c0e91b23` 2026-05-11): the reclassification sweep is bounded by source ancestry, not identifier count. IEEE bulk-load source (`sources.id=1`) ancestry covers ~91,727 `raw_observations` rows; an unknown but substantial subset of existing `identifiers` rows promote via that ancestry. The "no data loss" framing holds — confidence values are preserved by band-corrected reclassification — but the sweep is structurally larger than a single Wave-B target. Scoping the sweep is a future-CP planning task; CP15 ratifies the band, not the migration plan.
- **Future Wave surfacings** that ingest IANA / IEEE / SIG / FAA-direct citations get the right source-band on first ingestion via the ExtractionWorker dispatch (mechanical translation per CP14 Path B precedent).

---

## 6. Cross-references

- **MAC-63 dispatch** [`843f306b`](/MAC/issues/MAC-63#comment-843f306b-3e4d-493a-b58e-38a731687943) Wave-A CEO Ratification Run
- **MAC-63 board reframe** [`fe2beeee`](/MAC/issues/MAC-63#comment-fe2beeee-2571-475e-86f6-edc99f99ecad) (original `primary_registry` framing for FAA RID)
- **MAC-63 Phase 5 dispatch** [`2b2cb0cf`](/MAC/issues/MAC-63#comment-2b2cb0cf-7796-4a43-a39e-f16d77a435f6) (CP15 amendment-draft spec)
- **CP14 §8.4 four-amendment commit** `06cc501` (composes with this CP15 §8.2 amendment)
- **§12 finalization commit** `72c0323` (the §12 question 3 was the structural framing for this CP15 work)
- **Promotion-cycle-1 close** at MAC-63 [`ae0e9c33`] (the 5-write cohort + 3 HOLDS for CP15)
- **`db/migrations/0009_manufacturer_app_and_identifier_type_extensions.sql`** (table-rebuild precedent for the future 0015 migration)
- **`feedback_cumulative_check_enum_across_sequenced_migrations.md`** (discipline for the future 0015 cumulative CHECK)
- **G-1 / G-3 / G-7 / G-9** in `raw/wave_a/_ceo_gates_queue_2026-05-11.md` (cross-amendment composition references)

---

## 7. §11 #11 statement

This is a CEO-authored draft; ratification + the `BIBLE_AMENDMENTS.md` CP15 entry are the CEO's at apply time. Per board direction `2b2cb0cf`: "Don't apply CP15 in Phase 5. Just draft to the same standard as the CP14 amendment drafts. CP15 ratification is a separate human-CEO heartbeat after Wave-A close." MAC-63 closes with this draft filed; CP15 application is a future heartbeat scoped separately.
