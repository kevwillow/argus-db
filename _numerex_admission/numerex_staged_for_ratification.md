# Numerex Corporation — staged proposal for CEO + board ratification

**Mirrors Honeywell precedent shape** (`_phase_6_wave_i_14a/honeywell_staged_for_phase_8.md`). Validator stages; CEO + board ratify; integration dispatch applies the schema mutation.

---

## §A — alias-of-existing append (Sierra Wireless, mfr.id=21)

- target_canonical: `Sierra Wireless` (mfr.id=21)
- aliases_to_append: `Numerex Corporation`, `Numerex Corp.`, `Numerex Corp`, `Numerex`
- action: APPEND to `manufacturers.aliases` (CSV in current schema) — preserve existing aliases `Sierra Wireless AirLink, Semtech Sierra, Sierra Wireless Inc, Sierra Wireless Inc., SIERRA WIRELESS AMERICA, INC`
- attribution_status: confirmed_via_sec_edgar_8k_2017-12-08_accession_0001193125-17-364672
- research_log_ref: `_numerex_admission/numerex_research_log.md`
- integration_dispatch: MAC-196
- precedent_anchor: `_phase_6_wave_i_14a/honeywell_staged_for_phase_8.md` §6.4 shape

---

## §B — `manufacturers.notes.acquired_subsidiaries[]` enrichment proposal

Stage the following structured entry onto `manufacturers.notes` for mfr.id=21 (Sierra Wireless). Honeywell precedent uses `notes.honeywell_acs_division_attestation`; the analogous shape here is an `acquired_subsidiaries[]` array entry per acquired brand.

```json
{
  "target_canonical_name": "Sierra Wireless",
  "acquired_subsidiary": {
    "legal_name": "Numerex Corp.",
    "common_brand_name": "Numerex Corporation",
    "state_of_incorporation": "Pennsylvania",
    "irs_ein": "11-2948749",
    "sec_cik": "0000870753",
    "sec_commission_file_number": "000-22920",
    "last_headquarters": "400 Interstate North Parkway SE, Suite 1350, Atlanta, GA 30339",
    "sic_code": "3669",
    "sic_description": "Communications Equipment, NEC",
    "merger_agreement_date_utc": "2017-08-02",
    "merger_closing_date_utc": "2017-12-07",
    "merger_consideration_summary": "stock-for-stock; 0.1800 Sierra Wireless common shares per Numerex Class A Common share; 3,588,784 SW shares total",
    "merger_sub_entity": "Wireless Acquisition Sub, Inc. (wholly-owned Sierra Wireless subsidiary)",
    "post_merger_status": "wholly-owned subsidiary of Sierra Wireless, Inc.",
    "deregistration_form": "15-12G",
    "deregistration_filed_utc": "2017-12-18",
    "deregistration_accession": "0001193125-17-371533",
    "primary_citation": {
      "filing_type": "8-K",
      "accession": "0001193125-17-364672",
      "filed_utc": "2017-12-08",
      "report_date_utc": "2017-12-07",
      "primary_document": "d503004d8k.htm",
      "source_url": "https://www.sec.gov/Archives/edgar/data/870753/000119312517364672/d503004d8k.htm",
      "local_capture": "_numerex_admission/8k_2017-12-08_2026-05-20T20-24-38Z.htm"
    },
    "submissions_citation": {
      "source_url": "https://data.sec.gov/submissions/CIK0000870753.json",
      "local_capture": "_numerex_admission/edgar_submissions_CIK870753_2026-05-20T20-24-29Z.json"
    },
    "fcc_eas_grantee_code_under_subsidiary_name": null,
    "fcc_eas_grantee_lookup_attestation": "0 rows in fcc_grantees (sid=7) matching grantee_name LIKE '%Numerex%' — subsidiary does not hold a grantee code under its own legal name; downstream FCC filings inferred to roll up under Sierra Wireless's LL9/N7N/PNF/QQL/TWV grantee cluster (per §7.2 surface)."
  },
  "research_log_ref": "_numerex_admission/numerex_research_log.md",
  "integration_dispatch": "MAC-196"
}
```

---

## §C — what NOT to apply in this dispatch

- Do NOT INSERT a new `manufacturers` row for Numerex.
- Do NOT INSERT any new `fcc_grantees` rows for Numerex (none exist under its legal name; §3.1 of research log).
- Do NOT promote any §7.2 cohort identifier into `identifiers` here — that work is blocked on the separate CP31-class CHECK enum amendment per `section_7_2_halt_surface.md`.
- Do NOT alter `Sierra Wireless` row's `primary_category` (currently `NULL`); Numerex's M2M/IoT-telematics scope confirms the conservative `unknown` default per Bible §4.

---

## §D — application sequencing (post-ratification)

Once CEO + board ratify:

1. Integration dispatch UPDATE `manufacturers` row id=21:
   - `aliases` = existing CSV + `,Numerex Corporation,Numerex Corp.,Numerex Corp,Numerex`
   - `notes` = JSON-merge `notes.acquired_subsidiaries` ← append the §B object
2. Re-run idempotency: this UPDATE is idempotent on aliases (dedup before append) and on the structured-notes entry (keyed by `legal_name == "Numerex Corp."`).
3. Coordination: post-ratification, the 9 V3 fccid.io rows in the §7.2 cohort that name `Numerex Corporation` become resolvable to Sierra Wireless and are unblocked for the Phase 7-bis re-dispatch (still gated on CP31-class CHECK enum amendment for `fcc_grantee_code` / `equipment_class_code`).

---

## §E — halt criteria — none fired (see research log §7)

Submitted for ratification.
