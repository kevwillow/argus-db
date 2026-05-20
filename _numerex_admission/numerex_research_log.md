# Numerex Corporation — manufacturer admission research log

**Dispatch:** [MAC-196](/MAC/issues/MAC-196)
**Parent:** [MAC-184](/MAC/issues/MAC-184) v1.4.1 Stage 1 integration
**Surfaced by:** [MAC-194](/MAC/issues/MAC-194) §7.2 halt-surface
**Precedent:** Honeywell admission staging — `_phase_6_wave_i_14a/honeywell_staged_for_phase_8.md`
**Status:** research complete; recommendation = **alias-of-existing** (Sierra Wireless, mfr.id=21); stage proposal authored; awaiting CEO + board ratification.

---

## 1. Question

The `Numerex Corporation` string appears in the 9-row subset of the Wave I.14c V3 fccid.io extraction plan (177-row §7.2 cohort) and is NOT in the canonical `manufacturers` lexicon (51 rows pre-Phase-8). Per dispatch §7.2 halt criterion #4 (manufacturer not in canonical lexicon → halt + surface; no auto-admit), this research dispatch determines:

1. Is Numerex an independent manufacturer or a subsidiary of an admitted one?
2. If subsidiary → append as alias of parent. If independent → admit new row.
3. Device-category mapping (§4)?
4. Grantee-code linkage (cross-attest against `fcc_grantees` sid=7)?

---

## 2. Primary-source corporate identity (§11 #1 — no fabrication; §11 #7 — provenance)

### 2.1 SEC EDGAR registrant lookup

- **Registrant name:** NUMEREX CORP /PA/
- **CIK:** 0000870753
- **State of incorporation:** Pennsylvania (charter)
- **IRS EIN:** 11-2948749
- **Headquarters (last filing of record):** 400 Interstate North Parkway SE, Suite 1350, Atlanta, GA 30339
- **SIC:** 3669 — Communications Equipment, NEC
- **Commission File Number:** 000-22920
- **Filing status as of today (2026-05-20):** deregistered — Form 15-12G filed 2017-12-18

**Source URL:** `https://data.sec.gov/submissions/CIK0000870753.json`
**Local capture:** `_numerex_admission/edgar_submissions_CIK870753_2026-05-20T20-24-29Z.json`
**Fetched at (UTC):** 2026-05-20T20:24:29Z
**Provenance preserved:** full submissions JSON pinned to raw repo location above per §11 #7.

### 2.2 Acquisition by Sierra Wireless — primary 8-K citation

**Filing:** Numerex Corp. Form 8-K dated December 7, 2017 (the "Closing Date"), filed December 8, 2017
**Accession:** 0001193125-17-364672
**Primary document:** `d503004d8k.htm`
**Source URL:** `https://www.sec.gov/Archives/edgar/data/870753/000119312517364672/d503004d8k.htm`
**Local capture:** `_numerex_admission/8k_2017-12-08_2026-05-20T20-24-38Z.htm`
**Fetched at (UTC):** 2026-05-20T20:24:38Z

**Source excerpt (verbatim, Item 2.01):**

> Item 2.01. Completion of Acquisition or Disposition of Assets. On the Closing Date, pursuant to the terms of the Merger Agreement, Merger Sub merged with and into Numerex, with Numerex surviving as a wholly-owned subsidiary of Sierra Wireless (the "Merger"). … Sierra Wireless issued 3,588,784 common shares as consideration for the Merger (including Numerex stock options, other equity-based awards and warrants).

**Source excerpt (verbatim, Item 1.02):**

> On December 7, 2017 (the "Closing Date"), in connection with the consummation of the previously announced Agreement and Plan of Merger, dated as of August 2, 2017 (the "Merger Agreement"), by and among Sierra Wireless, Inc. ("Sierra Wireless"), Wireless Acquisition Sub, Inc., a direct, wholly-owned subsidiary of Sierra Wireless ("Merger Sub"), and Numerex Corp. ("Numerex") …

### 2.3 Structured corporate-history facts

| Field | Value | Primary source |
|---|---|---|
| Merger Agreement signed | 2017-08-02 | 8-K accession 0001193125-17-364672, Item 1.02 verbatim |
| Merger consummated (Closing Date) | 2017-12-07 | 8-K accession 0001193125-17-364672, Item 2.01 verbatim |
| Acquirer | Sierra Wireless, Inc. | 8-K Item 2.01 |
| Merger structure | Wireless Acquisition Sub, Inc. (wholly-owned Sierra Wireless subsidiary) merged with and into Numerex Corp.; Numerex survived as a wholly-owned Sierra Wireless subsidiary | 8-K Item 2.01 |
| Consideration | 0.1800 Sierra Wireless common shares per Numerex Class A Common share (stock-for-stock); total 3,588,784 SW shares issued | 8-K Item 2.01 |
| Deregistration | Form 15-12G filed 2017-12-18 (accession 0001193125-17-371533) | EDGAR submissions JSON |

### 2.4 Conclusion of §2

Numerex Corporation is a **defunct, deregistered Pennsylvania corporation** that became a **wholly-owned subsidiary of Sierra Wireless, Inc.** on **2017-12-07**. Numerex was not an independent legal entity continuously after that date. As of the Form 15-12G filed 2017-12-18, Numerex had no further SEC reporting obligations.

---

## 3. FCC grantee-code linkage

### 3.1 Direct grantee lookup (sid=7 — `fcc_grantees` table)

Searched `fcc_grantees` (sid=7, FCC EAS open-data CSV anchor) for direct attribution to Numerex Corporation:

```sql
SELECT id, grantee_code, grantee_name, mailing_address, city, state, country, date_received
FROM fcc_grantees
WHERE grantee_name LIKE '%Numerex%';
```

**Result:** 0 rows. Numerex Corporation does **not** hold a direct FCC EAS grantee code under its own legal name.

Cross-checked by HQ address (`400 Interstate North Parkway`, ZIP `30339`) and possible historical brands (`Cellemetry`, `Uplink`):

```sql
SELECT * FROM fcc_grantees WHERE mailing_address LIKE '%Interstate North%' OR mailing_address LIKE '%30339%';
```

**Result:** No grantee tied to Numerex's known HQ address.

### 3.2 Inferred linkage to §7.2 17-grantee cohort

Per `_phase_7_fccid_attestations/section_7_2_halt_surface.md`, the 17 grantee codes named in the V2+V3 cohort include the Sierra Wireless cluster:

- `LL9` Sierra Wireless Inc
- `N7N` Sierra Wireless Inc.
- `PNF` Sierra Wireless, Inc
- `QQL` Sierra Wireless, Inc.
- `TWV` Sierra Wireless, Inc.

The most plausible explanation for `Numerex Corporation` appearing as the vendor-label string on 9 V3 fccid.io rows in a 17-grantee cohort that contains none of Numerex's own codes is that **fccid.io is surfacing the applicant-of-record (or prior brand) string on filings whose underlying FCC EAS grantee attribution rolls up to Sierra Wireless's grantee codes** — i.e., post-acquisition rebadging of legacy Numerex filings or Sierra Wireless filings that retained "Numerex Corporation" branding in fccid.io's metadata. This is consistent with §2.2 — Numerex became a wholly-owned Sierra Wireless subsidiary 2017-12-07, and Sierra Wireless inherits the grantee universe.

**Caveat for the validator/CEO:** the actual per-row grantee_code → vendor_label mapping for the 9 Numerex rows is in the Wave I.14c V3 extraction plan (carried in the MAC-194 dispatch, not duplicated in the repo). The above is the *inferred* linkage. Per §11 #1 we surface it as inferred, not asserted; final disposition during Phase 7-bis re-dispatch (post-CP31) should confirm grantee_code per row from the plan and pin the per-row provenance.

### 3.3 No chained-admission gap

Sierra Wireless is already in the canonical lexicon (mfr.id=21). No upstream parent of Numerex is missing. **Halt-criterion (chained admission gap) does NOT fire.**

---

## 4. Device category mapping (§4)

Numerex's product line, per its final SIC code (3669 Communications Equipment, NEC) and pre-acquisition product portfolio, was **M2M / IoT cellular gateway modules** (machine-to-machine wireless connectivity for SCADA, asset tracking, security/alarm telemetry, fleet telematics). This maps to Sierra Wireless's core business (cellular wireless modules and gateways).

Per Bible §4 default for non-LE-anchored vendors, the canonical mapping is `device_category = unknown` unless a positive law-enforcement / public-safety equipment match is later sourced. Numerex's M2M/IoT-telematics positioning does **not** automatically qualify it as law-enforcement equipment, so no §4 device_category gap is introduced — `unknown` is the conservative default and matches Sierra Wireless's current row (which carries `primary_category = NULL`).

**No CEO ratification needed for §4** — this is the default disposition.

---

## 5. Discipline envelope re-attestation

| Rule | Outcome |
|---|---|
| **SAR-13 + §3399** PRAGMA + sqlite_master CHECK enum re-attestation | N/A for alias append (no CHECK constraint on `manufacturers.aliases`). |
| **SAR-15** GENERIC_RISK_CANONICALS guard | "Numerex" / "Numerex Corporation" / "Numerex Corp" — vendor-anchored corporate name (Pennsylvania charter, EIN 11-2948749). Not a generic shape. PASS. |
| **§11 #1** no fabrication | All corporate-history facts cited to primary SEC filings with verbatim source_excerpts and source_urls (§2.2, §2.3). |
| **§11 #6** ToS for external fetches | SEC EDGAR / data.sec.gov — public open data, User-Agent set per SEC guidelines. |
| **§11 #7** provenance preserved | Raw 8-K HTM + EDGAR submissions JSON pinned to `_numerex_admission/` with UTC fetch timestamps. |
| **§11 #11** amendment-log discipline | Manufacturer admission is **not** a CP-class amendment per precedent (prior admissions = schema-row inserts/updates without Bible memo). Validator surfaces; CEO + board ratify. |

---

## 6. Recommendation

**RECOMMEND: alias-of-existing.** Append `Numerex Corporation` (and tighter variant `Numerex Corp.`) to `manufacturers.aliases` on mfr.id=21 (Sierra Wireless), with a structured `notes.acquired_subsidiaries[]` entry capturing the acquisition citation.

### Rationale

1. Numerex became a wholly-owned subsidiary of Sierra Wireless on 2017-12-07 (primary 8-K, §2.2 verbatim). It is not an independent entity from that date forward.
2. Numerex holds **no** direct FCC EAS grantee code under its own legal name (§3.1) — the 9 V3 fccid.io rows must roll up under another grantee in the cohort, and the only plausible parent in the cohort is Sierra Wireless's LL9/N7N/PNF/QQL/TWV cluster.
3. Per Honeywell precedent: subsidiary brand → alias append, not new manufacturer row. Mirrors the existing `Sierra Wireless AirLink`, `Semtech Sierra` aliases already on mfr.id=21 (which itself reflects Sierra Wireless's 2023-01 acquisition by Semtech captured as alias rather than new row).

### Do NOT

- Do not admit Numerex as a new manufacturer row (would split a single legal-entity lineage across two `manufacturers.id` values, breaking dedup invariants downstream).
- Do not create new `fcc_grantees` rows for Numerex — there are no Numerex-attributed grantee codes in sid=7 to ingest (§3.1).
- Do not promote any §7.2 cohort identifier into `identifiers` in this dispatch — that work is blocked on the separate CP31-class CHECK enum amendment (`fcc_grantee_code` / `equipment_class_code`) per §7.2 halt-surface.

---

## 7. Halt criteria — none fired

| Halt criterion | Status |
|---|---|
| Numerex subsidiary of mfr NOT in lexicon → chained admission gap | NOT fired — Sierra Wireless already in lexicon (mfr.id=21). |
| Grantee_code attribution ambiguous (e.g., holding-co with unrelated vendors) | NOT fired — Numerex has no direct grantee_code; the parent Sierra Wireless cluster is unambiguous. |
| Acquisition-history citations conflict | NOT fired — primary 8-K + EDGAR submissions JSON agree (single transaction, 2017-12-07 close). |
| §4 device_category gap | NOT fired — `unknown` default is correct. |
| §8.2 source_class question | NOT fired — corporate-history attestation is SEC primary-source (top-tier), source_class not in question. |

---

## 8. Next-step deliverable

Stage doc: `_numerex_admission/numerex_staged_for_ratification.md` — mirrors Honeywell precedent shape; proposes the alias append for mfr.id=21 plus structured `notes.acquired_subsidiaries[]` enrichment. Validator does NOT apply; CEO + board ratify, then post-ratification SQL UPDATE proceeds via integration dispatch.
