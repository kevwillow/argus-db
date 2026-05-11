# Bible §8.4 Amendment Draft — LA-bit U/L-flip Detection Rule

**Status:** DRAFT for CEO ratification (§11 #11). Sub-agent authored under autonomous-run authorization 2026-05-11. NOT applied to Bible HEAD.
**Trigger:** n=3 reached at Wave-A Phase 2a return.
**Drafted by:** Opus sub-agent invoked via paperclip-framework-equivalent escalation.
**Gate:** G-4 (queue entry `raw/wave_a/_ceo_gates_queue_2026-05-11.md`).

---

## 1. Current §8.4 (verbatim)

> ### 8.4 False-positive prevention
>
> The single biggest risk to this database is over-claiming. Specific guardrails:
>
> - **Multi-purpose vendors are not categorized at the OUI level.** Motorola Solutions makes police radios *and* hospital pagers *and* warehouse scanners. An OUI alone never gets a `device_category` other than `unknown`. Category requires model-level evidence.
>   - **Unknown-category Lynceus carveout.** Records with `device_category='unknown'` (the multi-purpose vendor case) are NEVER exported to Lynceus under any confidence level. Lynceus cannot do anything useful with "unknown category" records — they would either be dropped (silently losing data) or fire as low-severity noise (training the user to ignore alerts). They remain in the canonical Argus database for analytical purposes only. The coverage report must tally these as "analytical-only records" separately from "exported records." (See also §11 #13.)
> - **Procurement ≠ deployment.** An agency buying a Stingray doesn't put one on every patrol car. Procurement records add geographic context but never raise an identifier above 85 confidence by themselves.
> - **MAC randomization warning.** Modern phones and some modern surveillance gear randomize MACs. Note this in the export readme so the scanner doesn't generate false alerts on randomized devices.
> - **Test data filter.** Reject identifiers matching known documentation/example ranges (RFC 7042, locally administered ranges with obvious patterns, vendor demo addresses). The full reject list is enumerated in §7.3 and applied by the validator (§7.4).
> - **Pi self-exclude list (running scanner's own hardware).** Lynceus runs on a Raspberry Pi, which has well-known OUIs:
>   - `b8:27:eb` (older Pi boards)
>   - `dc:a6:32` (Pi 4 era)
>   - `e4:5f:01` (recent boards)
>   - `28:cd:c1` (more recent)
>
>   These OUIs MUST NOT appear in the Lynceus high-confidence export, regardless of source confidence. They appear in the standard export (`argus_export.json`) with `severity='low'` and a description noting "informational — common in DIY hardware." This exclusion list is hard-coded in the export worker (§7.5) and tallied in the coverage report under `self_exclude_oui`. (See also §11 #12.)

**Adjacent rule (§7.3, "LAA-bit confidence penalty"):** Scraped MACs with U/L=1 get `confidence ≤ 40` and a `lab_bit_set` note unless the source explicitly attests broadcast use. This is the *intake* discipline; §8.4 currently has no *promotion-time / dedup-time* discipline for LA-bit identifiers.

---

## 2. The 3 observations

### 2.1 U/L-bit math verification

The U/L bit is bit-1 of the first octet (`xxxxxx1x` ⇒ locally-administered). Verification:

| Stage | Identifier | First octet binary | bit-1 | U/L=0 sibling |
|---|---|---|---|---|
| Phase 1c | `62:60:1F` | `0x62` = `0110_0010` | **1** (LA) | `60:60:1F` |
| Phase 1a | `86:25:19` | `0x86` = `1000_0110` | **1** (LA) | `84:25:19` *(bit-1 cleared: `1000_0100` = `0x84`)* |
| Phase 2a | `82:6B:F2` | `0x82` = `1000_0010` | **1** (LA) | `80:6B:F2` *(bit-1 cleared: `1000_0000` = `0x80`)* |

Note: the briefing memo specified `80:25:19` / `84:6B:F2` as the siblings for the Phase 1a / 2a cases, but those values clear bit-2 (`0x04`), not bit-1 (`0x02`). The U/L bit per IEEE 802 is bit-1 (mask `0x02`). The correct U/L=0 siblings (mask `0x02` cleared) are **`84:25:19`** and **`80:6B:F2`**. Both sibling-pair forms checked below.

### 2.2 IEEE-sibling lookup in Argus (`/home/kev/argus/db/argus.db`)

| Identifier looked up | Rows | Detail |
|---|---|---|
| `60:60:1F` (DJI IEEE sibling of `62:60:1F`) | **2** | `id=431` DJI / drone / conf=55 / `inferred`; `id=509` DJI / unknown / conf=50 / `inferred` |
| `84:25:19` (correct U/L=0 sibling of `86:25:19`) | 0 | absent |
| `80:25:19` (briefing's named sibling) | 0 | absent |
| `80:6B:F2` (correct U/L=0 sibling of `82:6B:F2`) | 0 | absent |
| `84:6B:F2` (briefing's named sibling) | 0 | absent |
| `62:60:1F`, `86:25:19`, `82:6B:F2` (the LA OUIs themselves) | 0 | absent — all three are still in staging, not promoted |

**Summary:** only the DJI case has its IEEE-assigned sibling present in Argus. The Flock and unknown-attribution cases have no IEEE sibling in the database yet (which does NOT mean the IEEE-assigned OUI doesn't exist — the IEEE registry may assign `80:6B:F2` and `84:25:19` to vendors we simply haven't ingested).

---

## 3. Proposed amendment

### 3.1 Option chosen: **Option A — extend §8.4 in place**

**Rationale:** §7.3 already owns the intake-side LAA penalty; §8.4 is the natural home for the *promotion-time pairing-and-dedup* discipline, and an in-place bullet keeps the rule next to the existing FP-prevention guardrails without inflating the section count.

**Not Option B (new §8.5):** LA-bit pairing is a sub-rule of FP-prevention, not peer to §8.1–§8.4.
**Not Option C (fold under source-lens):** Source-lens governs *how a source attests*; LA-bit pairing governs *structural relationships between identifiers*. Different axis. They compose, but the LA rule has its own arithmetic/dedup content that source-lens language doesn't encode.

### 3.2 Amendment text (copy-pasteable into PROJECT_BIBLE.md)

Insert as a new bullet in §8.4, between the **MAC randomization warning** and **Test data filter** bullets:

> - **Locally-administered (U/L=1) OUI pairing discipline.** When the validator promotes a staged OUI whose first octet has bit-1 set (`xxxxxx1x`, i.e., locally-administered per IEEE 802), it MUST first check whether the **U/L=0 sibling** (same OUI with bit-1 of the first octet cleared, mask `& 0xFD`) is already an IEEE-assigned record in `identifiers`. Three dispositions:
>   - **Sibling present, same vendor context as the staged LA OUI** → promote the LA variant as a *paired identifier* linked to the IEEE-assigned parent. Both rows persist. Confidence for the LA child inherits the §7.3 intake penalty (cap ≤ 40 unless the source attests broadcast use) but the corroboration bonus from the paired IEEE sibling may raise it up to the source-type ceiling per §8.2. Add a structured note on both rows recording the pairing (see §3.3 below for the note format; a `paired_identifier_id` schema column is a queued discussion, not a current requirement).
>   - **Sibling absent in Argus** → hold the LA OUI at the §7.3 intake confidence (≤ 40) with `rationale_pending_verification`. Promote only when a second independent source corroborates the same LA OUI in the same vendor context (§8.2 corroboration rule). Do not synthesize an IEEE-sibling row from the LA OUI alone.
>   - **Sibling present but assigned to a different vendor than the staged LA OUI's attributed context** → route the staged LA OUI to the `conflicts` table per §4.2 with `reason='la_bit_sibling_vendor_mismatch'`. Resolution requires manual review; do not auto-promote.
>
>   The U/L-flip relationship is *necessary but not sufficient* for pairing: bit-1 of an LA OUI is a 1-bit fact, not an attestation that the device firmware deterministically emits the LA variant. A second observation in the same vendor context (or vendor documentation attesting the LA variant) is required before the paired-identifier disposition fires. Without that second observation, the disposition is "hold at low confidence" — single-observation LA OUIs do not promote on the strength of the bit-flip alone.

### 3.3 Note format for paired LA OUIs

Until a `paired_identifier_id` column is ratified (§5), record pairing in `notes` as one line:

```
la_pair: {"role": "ieee_parent" | "la_child", "sibling_id": <int>, "sibling_value": "<oui>", "trigger": "u_l_flip_bit1"}
```

Validator parses this on promotion to avoid coverage-report double-counting and to group paired rows in the Lynceus export `description`.

---

## 4. Default disposition for validator-side promotion

Mapped to the 3 current observations:

| Staged LA OUI | Sibling status | Disposition under amended §8.4 |
|---|---|---|
| `62:60:1F` (Phase 1c, DJI) | IEEE sibling `60:60:1F` **present**, same vendor (DJI), drone category | Promote as paired identifier child of `id=431` (the categorized DJI row); record `la_pair` note on both rows; inherit confidence ≤ 40 unless second-source corroboration arrives in later Wave-A phases |
| `86:25:19` (Phase 1a, attribution unclear) | Correct sibling `84:25:19` **absent**; briefing's `80:25:19` also absent | Hold at `≤ 40` with `rationale_pending_verification`. No promotion until a second source observes the same OUI in a vendor-attributable context |
| `82:6B:F2` (Phase 2a, Flock — DeflockJoplin curated) | Correct sibling `80:6B:F2` **absent**; briefing's `84:6B:F2` also absent | Hold at `≤ 40` with `rationale_pending_verification`. The curated-list provenance is a second source-touch but the list mixes IEEE-assigned and LA OUIs without distinction (per Phase 2a surfacing), so it does not constitute an independent corroboration of the LA OUI specifically — wait for a third source or a vendor-doc attestation |

Disposition for the conflicting-vendor case is hypothetical until an instance surfaces; the rule is enumerated for forward robustness.

---

## 5. Schema implication

**Verdict: notes-JSON for now; queue a new G-7 gate for a `paired_identifier_id` column.**

Reasoning:

- The existing `identifiers` schema already has `superseded_by INTEGER REFERENCES identifiers(id)` — self-reference precedent. A `paired_identifier_id INTEGER REFERENCES identifiers(id) ON DELETE SET NULL` column is a structurally identical extension.
- Queueing the migration as a separate gate decouples the amendment ratification (low cost, immediate value) from the migration ratification (higher cost — requires Lynceus export schema review per §7.5 `_meta` and CP11 CSV column-count rules). The notes-JSON form is forward-compatible — a one-shot backfill `UPDATE identifiers SET paired_identifier_id = json_extract(notes,'$.la_pair.sibling_id') WHERE notes LIKE '%la_pair:%'` promotes JSON to column without data loss.
- The column is a *multi-gate enabler*: it also serves G-1 (standards-body OUI lens) and G-2 (FRDID annotation, where the pair is across two IEEE-assigned OUIs, not a U/L-flip). Worth standalone queueing rather than folding into the §8.4 amendment.

**Action requested of CEO at ratification:** open **G-7** in the gates queue. Sub-agent has NOT modified the queue file (§11 #11). Suggested entry:

> ## G-7 — `paired_identifier_id` schema column (schema migration)
>
> - **Phase surfaced:** sub-agent G-4 draft 2026-05-11 (forward dependency for U/L-flip pairing, FRDID annotation G-2, protocol-container lens G-1)
> - **Decision shape:** New nullable column `paired_identifier_id INTEGER REFERENCES identifiers(id) ON DELETE SET NULL` on `identifiers`. Migration `0012_paired_identifier_id_column.sql`. Parallel to `superseded_by`.
> - **Sub-agent disposition:** Not pre-drafted. Awaits CEO direction on whether to fold into G-3 (`ble_manufacturer_id`) migration as a combined `0011_` or stand alone.
> - **Default-if-silent:** Hold. Use notes-JSON `la_pair:` per §8.4 amendment until ratified.

---

## 6. Forward expectation

n=3 today; Phase 2b/2c/3/4/5 still running. Behaviors as n grows:

- **More LA OUIs with IEEE siblings present:** paired-identifier dispositions fire automatically; coverage report tallies a new bucket `la_paired_promotions`. No bible change.
- **More LA OUIs without siblings** (the `82:6B:F2` shape): accumulate at ≤ 40 until corroboration. If one accumulates 3+ independent source-touches without an IEEE sibling ever surfacing, that's a new surfacing for CEO ruling — amendment holds them safely until then.
- **Conflicting-vendor case:** zero observed; `conflicts` routing is robust to first occurrence.
- **Edge case the amendment does NOT cover:** LA OUI promoted before its IEEE sibling lands later in another phase. **Mitigation (validator implementation, not bible):** when an IEEE OUI lands, sweep for orphan LA children with matching `(value & ~0x02) == new_ieee_value` and re-evaluate. Flag for validator implementer.

Amendment scales linearly with sample size; no re-draft unless a structurally new LA pattern surfaces (multi-octet LA ranges, IPv6-mapped MACs, non-Ethernet 802 identifiers).

---

## 7. Cross-references

- **G-1 (protocol-container OUI lens):** Independent of G-4 (standards-body OUIs are U/L=0, no U/L-flip interaction). BUT the `paired_identifier_id` column under §5 is the same enabler G-1 would need for parent-child standards-body-OUI ↔ device-MAC modeling. Recommend G-1 + G-7 co-ratify; G-4 uses notes-JSON stop-gap until then.
- **G-2 (FRDID dedup-catalog annotation):** FRDID `6A:5C:35` ↔ ASD-STAN `FA:0B:BC` is a paired-identifier relation across two IEEE-assigned OUIs (both U/L=0). NOT covered by this amendment. Same `paired_identifier_id` column (§5) would serve.
- **G-3 (`ble_manufacturer_id`):** Orthogonal.
- **§7.3 LAA-bit intake penalty:** Composes — §7.3 sets the confidence floor (≤ 40); §8.4 amendment governs the lift mechanics (pair / hold / conflict).
- **Feedback memo 2026-05-10 (observation-vs-registration source-lens):** Composes — LA OUIs are observation-lens evidence by construction; this amendment is the structural pairing rule applied after the source-lens evaluation.
- **§11 #11:** This is a draft; ratification + `BIBLE_AMENDMENTS.md` entry are CEO's at next heartbeat.
