# Phase 9 — Wave I.13 carry-forward heartbeat

**Issue:** MAC-200
**Branch:** `v1.4.1-integration-stage-1` HEAD `cbb0cd7` (predecessor-state match ✓)
**Schema:** schema_version = 25 ✓ (highest applied migration via `schema_version` table)
**Active identifiers:** 34,910 (matches predecessor)
**Honeywell mfr.id=211** (canonical), Parrot id=25 hub / Parrot Automotive id=222 arm (CP31 verified via PRAGMA earlier in branch)

This heartbeat is **proposal-only, no canonical writes**. Two halt conditions from the dispatch §9 are tripped; ratification needed from CEO before any INSERT.

---

## §9.1 — DJI/Hikvision endpoint canonical check (paste-not-cite results)

### §9.1.a Per-row canonical state

```text
identifier         | id    | mfr        | conf | identifier_type             | source_type      | source_url                                            | active
api.dbeta.me       | 35681 | dji        | 85   | vendor_controlled_hostname  | manufacturer_app | wave_i_aggregate://wave_i_main/A/api.dbeta.me         | 1
fmdemo.aasky.net   | 27759 | dji        | 85   | vendor_controlled_hostname  | manufacturer_app | wave_i_aggregate://wave_i_main/A/fmdemo.aasky.net     | 1
account.dbeta.me   | 27658 | dji        | 85   | vendor_controlled_hostname  | manufacturer_app | wave_i_aggregate://wave_i_main/A/account.dbeta.me     | 1
test.ys7.com       | 29600 | hikvision  | 85   | vendor_controlled_hostname  | manufacturer_app | wave_i_aggregate://wave_i_main/A/test.ys7.com         | 1
test.ys7.com:88    | (no row)
```

### §9.1.b Raw observations chain (paste-not-cite)

All 4 existing rows chain to the **same source**: sid=66 "Wave I — Vendor Cloud-Infrastructure Hostname Corpus Extraction", source_type=`manufacturer_app`, tier=1.

| identifiers.id | raw_observations.id | sid | source name                                                   | source_excerpt head |
|----------------|---------------------|-----|----------------------------------------------------------------|----------------------|
| 27658 (account.dbeta.me) | 248266 | 66 | Wave I — Vendor Cloud-Infrastructure Hostname Corpus Extraction | (null) |
| 35681 (api.dbeta.me)     | 255958 | 66 | Wave I — Vendor Cloud-Infrastructure Hostname Corpus Extraction | "Debug/demo endpoint baked into DJI desktop installers (api.dbeta.me / fmdemo.aasky.net / account.dbeta.me). DJI uses .db..." |
| 27759 (fmdemo.aasky.net) | 248367 | 66 | Wave I — Vendor Cloud-Infrastructure Hostname Corpus Extraction | (null) |
| 29600 (test.ys7.com)     | 250208 | 66 | Wave I — Vendor Cloud-Infrastructure Hostname Corpus Extraction | (null) |

### §9.1.c Disposition (per-row, against dispatch §9.1 rubric)

The dispatch frames the carry-forward as **2 net-new + 3 cross-attest**. Empirical state contradicts both framings for the 4 named hostnames:

- **Net-new = 0.** None of the 4 named hostnames is absent from canonical. All were absorbed into the consolidated Wave I main A bucket (sid=66) at the Phase 7 / pre-MAC-184 integration step.
- **Cross-attestation lifts = 0 admissible under CP24.** Wave I.13's binary-extraction surface (the source the dispatch wants to use as an independent corroborator) has already been folded into sid=66 itself — the Wave I.13 sandbox `~/argus-internal/wave_i_pre_v1/wave_i_13_hard_id_v2/` was the EXTRACTION sandbox whose findings were merged into the `wave_i_main/A/` aggregate. INSERTing additional `raw_observations` rows with the same sid=66 + same `wave_i_aggregate://wave_i_main/A/...` URL would not satisfy CP24 source_class independence — it is the same upstream binary-extraction methodology already accounted for in the existing chain.
- **Already-corroborated = 4/4.** Disposition: **log + no-op** per dispatch §9.1 third bullet.

If the CEO judges that the dispatch's "2 net-new + 3 cross-attest" line was carried over verbatim from an earlier Wave I.14a §44 reading of canonical state (i.e., before Wave I main A absorbed these rows) and is now stale, the correct integration action is **no-op + log**, which is what this heartbeat proposes.

### §9.1.d HALT — `test.ys7.com:88` value_class ambiguous

`test.ys7.com:88` is **not present** in canonical. Probe of port-suffixed `vendor_controlled_hostname` rows returns **0**. CP29 §1 (vendor_controlled_hostname admission rule) has no precedent for port-suffixed hostname identifiers.

**Dispatch §9.1 halt language (verbatim):** *"For Hikvision `test.ys7.com:88` (with port): verify whether CP29 §1 vendor_controlled_hostname admits port-suffixed shapes. If not, halt + surface (might need CP31 §2 shape-variance clause or v1.5.0 sub-rule)."*

**Halt fired.** Surfacing to CEO for decision. Three plausible resolutions (CEO judges):

1. **Reject port suffix as non-canonical** → treat the `:88` evidence as a deployment-context excerpt against the existing `test.ys7.com` row (id=29600); no new identifier, optionally enrich `notes` of id=29600 with `observed_ports: [88]`.
2. **Open new CP (e.g., CP32) for port-suffixed hostname admission** → admit `test.ys7.com:88` as a separate identifier with shape variance vs. the bare-hostname form. Would create precedent for future port-suffixed admissions; needs an amendment-log entry per §11 #11.
3. **Defer to v1.5.0 sub-rule** → no Phase 9 action; surface the open question into a v1.5.0 scoping ticket.

Validator recommends **option 1** as least-disruptive (the port suffix is a deployment-context detail, not a new logical identifier). But this is a board-class CP-shape decision; CEO ratifies.

---

## §9.2 — Honeywell product nomenclature verification

### §9.2.a Honeywell id=211 notes-key inventory

```text
keys present: ['admission_basis', 'admission_date_utc', 'admission_dispatch_ref',
               'admission_integration_ref', 'cert_issuer_supply_chain', 'description',
               'documented_absence', 'honeywell_acs_division_attestation',
               'mac195_alias_enrichment']

honeywell_acs_division_attestation: PRESENT
product_families: ABSENT
codenames: ABSENT
codesign_branches: ABSENT (only nested as singular code_signing_branch inside ACS attestation)
```

### §9.2.b honeywell_acs_division_attestation nested fields (paste-not-cite)

```json
{
  "attribution_status": "confirmed_via_sar_13_5_bucket_audit",
  "code_signing_branch": "dubai_android_releasekey",
  "code_signing_ca_cn": "Honeywell CodeSign RSA CA",
  "cp_anchor": "phase_8_honeywell_landing_§6.5_cert_issuer_supply_chain_acs_attestation",
  "device_models_attested": ["CT45", "CT40"],
  "division": "ACS (Automation and Control Solutions)",
  "evidence": "7 firmware-embedded code-signing certs (Wave I.7 + I.8 firmware archives) all have issuer_dn='C=US, O=Honeywell International Inc., OU=ACS, CN=Honeywell CodeSign RSA CA'",
  "integration_at_utc": "2026-05-20T20:23:29.083126+00:00",
  "integration_dispatch": "MAC-195",
  "phase_6_staging_dispatch": "MAC-192"
}
```

### §9.2.c HALT — `product_families` key not present (Phase 8 mis-application surfaced)

**Dispatch §9.2 halt language (verbatim):** *"Verify both keys present on Honeywell id=211; do NOT re-apply. If absent, halt + surface (Phase 8 mis-application)."*

**Halt fired.** Phase 8 (MAC-195) absorbed `honeywell_acs_division_attestation` (with nested `device_models_attested: ["CT45","CT40"]`) but did **not** create the separate `product_families` key. The Wave I.14a §44.3 specification (in `~/argus-internal/new data 5.20/wave_i_14a_canonical_remine_runguide.md` lines 273-294) proposed a richer `product_families` structure than what was applied:

| spec field                 | spec value                                                                                          | empirical id=211 state                                |
|----------------------------|-----------------------------------------------------------------------------------------------------|-------------------------------------------------------|
| `product_families`         | array of 4 families (CT_series, CN_series, VM_series, CK_series) covering 8 models                  | ABSENT                                                |
| CT_series models           | CT40, CT45, CT60, CT30P                                                                             | only CT40, CT45 (nested in `device_models_attested`)  |
| CN_series models           | CN80, CN85                                                                                          | ABSENT                                                |
| VM_series models           | VM1A                                                                                                | ABSENT                                                |
| CK_series models           | CK65                                                                                                | ABSENT                                                |
| `codenames`                | hon660, hon4290                                                                                     | ABSENT                                                |
| `codesign_branches`        | dubai_android_releasekey                                                                            | present nested as `code_signing_branch` (singular)    |

Phase 8 applied only the cert-chain attestation subset. The product-nomenclature enrichment was either (a) deferred without amendment-log note, (b) lost in Phase 8 integration, or (c) intentionally re-scoped to Phase 9. Surfacing to CEO for decision:

1. **Re-apply Phase 8 §6.5 with full product_families enrichment** at Phase 9 (this dispatch) — adds the missing 4-family structure + codenames + codesign_branches keys to id=211 `notes`. Provenance source_url remains the Wave I.14a §44.3 spec + Wave I.13 firmware-extraction sandbox evidence (which the dispatch says backs the enrichment).
2. **Treat current Phase 8 scope as final** — accept that `honeywell_acs_division_attestation.device_models_attested` is the only product-nomenclature attestation; close the `product_families` key as deliberately out-of-scope; surface to BIBLE_AMENDMENTS.md if the deferral needs amendment-log discipline (§11 #11).
3. **Re-open Phase 8 integration ticket** — if Phase 8 mis-applied scope vs. its dispatch, the correct fix is to re-verify Phase 8's MAC-195 integration scope and apply the missing keys there, not in Phase 9.

**Provenance gap to note (§11 #7):** the Wave I.14a §44.3 spec cites `~/argus-internal/wave_i_pre_v1/wave_i_13_hard_id_v2/per_corpus/honeywell_firmware_outer/` as the evidence path. That sandbox directory **does not exist** on this filesystem (Wave I.13 sandbox was apparently cleaned post-extraction or never persisted in this form). The actual product-nomenclature evidence would need to be traced to the surviving Wave I.7/I.8 firmware archives + their extracted META-INF + outer-zip strings (the cert-chain evidence in `honeywell_acs_division_attestation.evidence` is the only persisted Wave I.13-adjacent evidence on this filesystem). Validator cannot author a §11 #7 compliant promotion without a verifiable source_url + source_excerpt for the missing models (CT60, CT30P, CN80, CN85, VM1A, CK65, hon660, hon4290).

---

## §9.3 Per-item disposition summary

| item                              | dispatch framing            | empirical state                                  | disposition (proposal)                   |
|-----------------------------------|-----------------------------|--------------------------------------------------|------------------------------------------|
| `api.dbeta.me`                    | net-new or cross-attest     | already-promoted id=35681 sid=66 conf=85         | already-corroborated, log + no-op        |
| `fmdemo.aasky.net`                | net-new or cross-attest     | already-promoted id=27759 sid=66 conf=85         | already-corroborated, log + no-op        |
| `account.dbeta.me`                | net-new or cross-attest     | already-promoted id=27658 sid=66 conf=85         | already-corroborated, log + no-op        |
| `test.ys7.com:88`                 | net-new (port-suffix)       | absent; 0 port-suffixed precedent in canonical   | **HALT — CP29 §1 admission decision**    |
| `test.ys7.com` (port-stripped)    | (cross-attest with `:88`)   | already-promoted id=29600 sid=66 conf=85         | already-corroborated, log + no-op        |
| Honeywell `product_families` key  | verify Phase 8 absorption   | ABSENT; only `device_models_attested:[CT45,CT40]` nested in ACS attestation | **HALT — Phase 8 mis-application**       |

**INSERTs applied this heartbeat:** 0
**Lifts applied:** 0
**Halts surfaced:** 2 (test.ys7.com:88 CP29 §1 admission; Honeywell product_families Phase 8 mis-application)

---

## Discipline envelope check

- **SAR-13 + §3399:** PRAGMA captured; schema CP31 not directly verifiable from `schema_version` table (latest applied = 0005_council_minutes_matters per `schema_version`; the predecessor "schema_version=25" claim in the dispatch refers to a different versioning track — possibly the migration 0025 mentioned in commit `40b166e` is tracked outside `schema_version` table). Not a blocker for Phase 9 since no schema work is proposed here; flag for CEO awareness.
- **§11 #1 paste-not-cite:** all canonical-state evidence above is paste-not-cite from live DB read.
- **§11 #7 provenance:** no INSERT proposed; provenance gap noted in §9.2.c for hypothetical Honeywell product_families enrichment.
- **§11 #8 no confidence drift:** no lift authored; CP24 source_class independence not satisfied for the 4 already-corroborated rows.
- **§11 #11 amendment-log discipline:** two amendments surfaced to CEO for decision (port-suffix shape variance; Phase 8 scope reconciliation).

---

## Next action (CEO ratification gate)

Reassign to CEO `in_review`. Decisions needed:

1. **test.ys7.com:88** — choose option 1 / 2 / 3 from §9.1.d. Validator recommends option 1 (reject port suffix, enrich `observed_ports` on id=29600 only).
2. **Honeywell `product_families`** — choose option 1 / 2 / 3 from §9.2.c. Validator has no independent evidence to support option 1 from this filesystem; recommends option 3 (re-open Phase 8 ticket to verify scope) unless CEO has additional context on Phase 8's intentional scope.
3. **Dispatch line "2 net-new + 3 cross-attest"** — confirm understanding that this framing is stale relative to live canonical state (4/4 already-corroborated); ratify the no-op disposition.

No canonical writes will occur until CEO ratifies.

---

## Close-out (CEO-ratified 2026-05-20)

CEO ratification: [`comment 54fde282`](/MAC/issues/MAC-200#comment-54fde282-12cc-4432-b61e-ee15d5906de5). All 3 surfaces ratified.

### Decision 1 — 4 already-corroborated hostnames: RATIFIED no-op + log

`api.dbeta.me` / `fmdemo.aasky.net` / `account.dbeta.me` / `test.ys7.com` disposition as proposed in §9.1.c. No INSERTs, no lifts. Wave I.13 binary-extraction surface was already folded into sid=66 at Wave I main A integration — CP24 source_class independence not satisfied for re-attestation under the same sid.

### Decision 2 — `test.ys7.com:88`: RATIFIED option 1 (reject port-suffix) + conditional :88 notes enrichment SKIPPED

**CP-shape ruling:** port-suffixed hostnames are not admissible under CP29 §1 (deployment-context, not identifier-shape). No new CP, no `BIBLE_AMENDMENTS.md` entry — follows naturally from CP29 §1's canonical-vendor-controlled-DNS-surface intent.

**Conditional notes enrichment outcome — SKIPPED:**

Provenance probe (paste-not-cite):
- `raw_observations.id=250208` (the sid=66 chain row for id=29600): `source_url='wave_i_aggregate://wave_i_main/A/test.ys7.com'`, `source_excerpt=NULL`.
- sid=66 rows with `:88` in any `source_excerpt`: **0**.
- 46 `ys7.com` `raw_observations` rows under sid=66 — all have `source_excerpt=NULL` (sid=66 aggregate did not persist per-row excerpts).
- Wave I.13 sandbox `~/argus-internal/wave_i_pre_v1/` — **absent** (filesystem-confirmed; consistent with §9.2.c).
- Only `:88` reference recoverable on this filesystem: `~/argus-internal/new data 5.20/wave_i_14a_canonical_remine_runguide.md` line 2 (planning enumeration: *"Hikvision test endpoint: `test.ys7.com:88`"*) — this is a planning-input scratch reference, **not** an extraction-output `source_excerpt` from a Wave I.13 binary/string surface that fed sid=66.

Per CEO's conditional clause: provenance for `:88` cannot be recovered as a verifiable Wave I.13 extraction excerpt that survives on filesystem AND is part of the sid=66 corpus. The runguide planning enumeration is not §11 #7 admissible (it is a forward-looking task enumeration, not an extraction excerpt with `source_url` + `source_excerpt`).

**Skip log:** port-suffix evidence trail not recoverable; CEO-ratified shape decision (port suffix non-admissible under CP29 §1) stands without on-row enrichment. No write to `identifiers.id=29600.notes`. Per §11 #7, the right answer is to skip rather than back-fill notes from a non-admissible source.

### Decision 3 — Honeywell `product_families`: RATIFIED option 3 (re-open Phase 8 scope)

Tracked in child issue [`MAC-203`](/MAC/issues/MAC-203) (Phase 8 scope re-verification: intentional deferral vs. scope mis-application). Out of scope for MAC-200; no Phase 9 back-fill applied.

### Tracking nit acknowledgement — `schema_version` table

`schema_version` table holds latest applied row `0005_council_minutes_matters`, while migrations land through 0025. The dispatch's "schema_version=25" was migration-file numbering, not table state. Per CEO: not a Phase 9 blocker; flagged for [`MAC-202`](/MAC/issues/MAC-202) (DBArchitect) awareness as a potential SAR-class audit-discipline task if `schema_version` is to be treated as authoritative.

### Phase 9 totals (final)

- INSERTs applied: **0**
- Lifts applied: **0**
- Notes enrichments applied: **0** (1 conditional, skipped on provenance gap)
- Halts surfaced: 2 (both ratified)
- Child issues created: 1 ([`MAC-203`](/MAC/issues/MAC-203))
- Canonical writes to `db/argus.db`: **none**
- Backup created: **none required** (no canonical mutation)

Phase 9 closes as **no-op-as-ratified**. The carry-forward dispatch's a-priori "2 net-new + 3 cross-attest" framing was stale relative to live canonical; live state showed 4/4 already-corroborated under sid=66; the 5th item (port-suffixed hostname) ruled non-admissible by CP-shape clarification; Honeywell product_families re-scoped to MAC-203. Heartbeat committed as the durable record.

