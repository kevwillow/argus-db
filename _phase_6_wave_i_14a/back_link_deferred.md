# MAC-192 §6.7 — Class D back-link hygiene (141 rows) DEFERRED to v1.4.2

Captured: 2026-05-20

**Per dispatch §6.7**: optional Paperclip-side script. SKIPPED in MAC-192 heartbeat — time budget consumed by §6.2–§6.5. Carry-forward to v1.4.2.

## Counts

- Academic (sid=37 Marlin) back_link_suggestions: **2**
- Community (sids 16/18/20/21/22/23/24/26/28/30/31/32/33) back_link_suggestions_class_D: **139**
- **Total Class D back-link rows: 141**

These are `raw_observations` rows whose underlying identifier was already absorbed into canonical (either via behavioral_signatures or via IEEE OUI-registry cross-source paths). Their `raw_observations.promoted_identifier_id` remains NULL by column-semantics design — the back-link hygiene would populate `raw_observations.notes.absorbed_to` to provide a traceability hop.

## Why deferred (not a content gap)

Per `paperclip_integration_decisions_pending[3]`: "Optional Paperclip-side hygiene script; not a content gap." The 141 rows are already correctly classified — only the back-link annotation is missing. No identifier rows are missing, no behavioral_signatures are missing, no manufacturers.notes enrichment is missing.

## v1.4.2 carry-forward action

Apply `raw_observations.notes.absorbed_to = '<canonical_identifier_type>.id=<canonical_identifier_id>'` for each of the 141 rows. Plan input enumerates target IDs:
- Per-row `canonical_identifier_id`, `canonical_identifier_type`, `canonical_manufacturer` provided in `RECONCILIATION_PLAN_V3.{academic,community}_remine_promotion_candidates.back_link_suggestions{,_class_D}[]`.

## Discipline

- §11 #1 no fabrication: ✓ — no new identifiers promoted; back-link is observational metadata.
- §11 #7 provenance: ✓ — annotations cite plan-input canonical_identifier_id verbatim.
- §11 #11 amendment-log: this defer is plan-source-authored, no new amendment.
