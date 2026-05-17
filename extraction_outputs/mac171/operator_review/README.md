# MAC-171 P3 SEC EDGAR — operator-review staging

Dispatch: [MAC-171](/MAC/issues/MAC-171)
Session: sec_edgar_admission
Staged at (UTC): 2026-05-17T06:27:10Z

## Contents

| File | Rows | Disposition |
|---|---|---|
| `aggregate_concentration_28.json` | 28 | Operator-review tier. `procurement_records.agency_name` NOT NULL rejects rows without a specific-agency anchor; useful aggregate-financial context (e.g. "largest customer accounted for 29% of revenues") retained on disk only. |
| `named_customer_false_positives_3.json` | 3 | §11 #1 false-positives identified in MAC-171 §C walkthrough — SSTI×ICE (about competitors), SSTI×DHS Item 1A (about Congressional IG-investigation request), Rekor×FBI Item 1 (about CJIS compliance). DO NOT promote. |
| `named_customer_ambiguous_1.json` | 1 | SSTI×FBI Item 1A historical-2011 reference; meaning truncated by 30-word fair-use cap. USAspending FBI rows stand independently at conf=85 (no §8.3 lift). Operator may re-fetch fuller filing context to adjudicate; no DB write either way absent operator confirmation. |

## Provenance

Source extraction outputs live at `~/argus-internal/extraction_outputs/sec_edgar_admission/`:
- `aggregate_concentration_only.json` (28 rows)
- `named_government_customers.json` (9 rows; 5 promoted to `procurement_records`, 3 FPs + 1 ambiguous staged here)

CEO ratification at [`35ebb1bf`](/MAC/issues/MAC-171#comment-35ebb1bf-d99b-46d3-b31b-c15b2399dfa5); Validator §7.4 walkthrough at [`727ffcf0`](/MAC/issues/MAC-171#comment-727ffcf0-8875-4580-a4b8-908a06ee81cb).
