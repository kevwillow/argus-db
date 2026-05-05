# WiGLE-admin elevated-quota grant — response received

## Provenance

- **Date received (per board notification):** 2026-05-05 (board notified CEO via MAC-1 [`bd667afb`](/MAC/issues/MAC-1#comment-bd667afb-7d2a-4d19-8a6d-6fc02060b656) at 16:09:01.832Z UTC).
- **Pitch sent:** 2026-05-04 from board's personal email tied to the WiGLE.net account, per `feedback_third_party_account_etiquette.md`. Pitch text drafted by CEO at MAC-1 [`14eaba3a`](/MAC/issues/MAC-1#comment-14eaba3a) (CP3a 2026-05-04 — see PROJECT_STATE Phase-3 sign-off audit trail).
- **Pitch-behavior binding:** scope claims (rate-limit posture, no-burst discipline, public-source grounding, v1 private repo, shareable with trusted people) carry forward verbatim through 2026-05-18 per `feedback_pitch_behavior_binding.md`. The grant landing does NOT alter the binding — the same discipline holds.

## Grant terms (as relayed by board)

- **Quota:** 100 queries/day.
- **Effective ceiling:** ~3,000 queries/month, ~36,000 queries/year.
- **Conditions specified by WiGLE:** none reported by board. (If WiGLE reply text contained additional conditions, they live in board's email; CEO does not have direct access.)
- **Comparison vs prior planning envelope:** the 200,000-queries-per-30-day planning envelope CEO used at MAC-9 Step 1 / Step 2 (pre-grant projection) is **obsolete**. Real ceiling is the live grant.

## Original WiGLE-admin reply text

Not pasted into the board notification. Board may include the reply text in a follow-up if/when needed for provenance audit. Per `feedback_third_party_account_etiquette.md`, the WiGLE-admin email reply is the receipt of record and lives in board's email account; this file is the project-side reference for what the grant terms are.

## Operational implications (codified at MAC-1 [`bd667afb`](/MAC/issues/MAC-1#comment-bd667afb-7d2a-4d19-8a6d-6fc02060b656))

1. **Strike the 200k/30d planning envelope.** All MAC-9 Step 1 / Step 2 arithmetic anchored to that envelope is superseded by 100/day live ceiling.
2. **89k one-time enrichment pass against full 44,483 anchors is no longer feasible as a single sprint.** Becomes a year+ enrichment that fills in over time. No v1 deadline pressure — Talos enriches over time.
3. **Geographic prioritization is the load-bearing structure now:**
   - **T1 Maryland** fills in within ~2 weeks at quota (per board projection at [`bd667afb`](/MAC/issues/MAC-1#comment-bd667afb-7d2a-4d19-8a6d-6fc02060b656)).
   - **T1 + T2 East Coast** fills in within ~2–3 months.
   - **Full national** fills in over a year+.
4. **Pacing rule:** ~4 queries/hour, not bursty. Don't spend full daily quota in a 5-minute burst.
5. **Response-header quota-signal check on every query stays binding** (per CP3a ground-rule SAR / dispatch-contract clause originally codified for the larger envelope; carries forward verbatim).
6. **No retries on rate-limit/429 stays binding** (same — discipline survives the envelope change).
7. **DRY_RUN flip:** CEO-class autonomous once MAC-9 Step 1 contract is re-ratified against the 100/day ceiling. No further board approval needed for the flip itself.

## Audit-trail discipline (board steer)

> "Surface the re-planned MAC-9 Step 1 contract as a fresh ratification proposal — don't quietly mutate the existing one. Keep the audit trail clean."

Original MAC-9 Step 1 ratification at [`ea4db5e2`](/MAC/issues/MAC-9#comment-ea4db5e2-1735-42d6-950c-099ef8e6842b) (2026-05-04T18:34:20.952Z) preserved verbatim. Original Step 2 ratification at [`7f91b6da`](/MAC/issues/MAC-9#comment-7f91b6da-56a6-4667-8d04-51786e3ed5cf) preserved verbatim. Fresh ratification proposal posted as a separate clearly-labeled superseding comment.

## Pointers

- Pitch text (drafted by CEO, sent by board): MAC-1 [`14eaba3a`](/MAC/issues/MAC-1#comment-14eaba3a) (CP3a 2026-05-04).
- Original CEO Step 0 budget estimate: MAC-9 [`bcbb8494`](/MAC/issues/MAC-9#comment-bcbb8494-d461-42d8-b495-46cf2ed1ac0b).
- Grant notification: MAC-1 [`bd667afb`](/MAC/issues/MAC-1#comment-bd667afb-7d2a-4d19-8a6d-6fc02060b656).
- Project-side schema/pipeline state at grant landing: `db/sources/wigle.py`, `db/migrations/0004_wigle_anchor_priority.sql`, `wigle_anchor_priority` 80,697 rows staged DRY_RUN ON.
