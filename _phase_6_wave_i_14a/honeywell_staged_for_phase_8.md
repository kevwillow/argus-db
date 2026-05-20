
## §6.4 alias enrichment stage

- ct_log_common_name: 'HoneywellSecurityGroup'
- matched_canonical: 'Honeywell'
- tier: 3
- action: APPEND to manufacturers.aliases for Honeywell (after Phase 8 finalizes admission)
- integration_dispatch: MAC-192
- cp_anchor: phase_6_§6.4_alias_enrichment_honeywell_staged



## §6.4 alias enrichment stage

- ct_log_common_name: 'HoneywellSecurityGroup'
- matched_canonical: 'Honeywell'
- tier: 3
- action: APPEND to manufacturers.aliases for Honeywell (after Phase 8 finalizes admission)
- integration_dispatch: MAC-192
- cp_anchor: phase_6_§6.4_alias_enrichment_honeywell_staged



## §6.5 cert-issuer vendor row stage

- vendor: 'Honeywell'
- ct_log_cert_total: 3628
- top_5_issuer_organizations: [["DigiCert Inc", 1428], ["\"VeriSign", 1003], ["Honeywell International Inc.", 843], ["\"GeoTrust", 145], ["GlobalSign nv-sa", 116]]
- attribution_status: confirmed_via_sar_13_5_bucket_audit
- integration_dispatch: MAC-192
- cp_anchor: phase_6_§6.5_cert_issuer_supply_chain
- action: APPEND to manufacturers.notes.cert_issuer_supply_chain for Honeywell at Phase 8 (after admission finalized)


## §6.5 honeywell_acs_division_attestation stage

- evidence: "7 firmware-embedded code-signing certs (Wave I.7 + I.8 firmware archives) all have issuer_dn='C=US, O=Honeywell International Inc., OU=ACS, CN=Honeywell CodeSign RSA CA'"
- manufacturers_notes_enrichment proposal:
  ```json
  {
  "target_canonical_name": "Honeywell",
  "division": "ACS (Automation and Control Solutions)",
  "code_signing_ca_cn": "Honeywell CodeSign RSA CA",
  "code_signing_branch": "dubai_android_releasekey",
  "device_models_attested": [
    "CT45",
    "CT40"
  ]
}
  ```
- attribution_status: confirmed_via_sar_13_5_bucket_audit
- integration_dispatch: MAC-192
- cp_anchor: phase_6_§6.5_cert_issuer_supply_chain_acs_attestation
- action: at Phase 8, append to Honeywell.notes.honeywell_acs_division_attestation as a structured entry

