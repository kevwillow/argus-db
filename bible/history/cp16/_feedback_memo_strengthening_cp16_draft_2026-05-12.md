# Memory-rule strengthening draft — `feedback_bible_amendment_downstream_consumer_audit.md` (CP16)

**Status:** DRAFT for CEO ratification (Phase 3.3 of MAC-75 CP16 dispatch). **NOT applied** to the live memo at `~/.claude/projects/.../memory/feedback_bible_amendment_downstream_consumer_audit.md`. Phase 5 coordinated commit moves the strengthened content from this draft to the live memo in lockstep with the bible §4.4 amendment + the code patch.

**Live memo path:** `/home/kev/.claude/projects/-home-kev--paperclip-instances-default-workspaces-62a86779-651b-4c59-8773-cee9e0f53334/memory/feedback_bible_amendment_downstream_consumer_audit.md`

**Trigger:** Memory rule codified after MAC-55 closure prevented future occurrences of the CP12→CP13 first-recurrence pattern (manufacturer_app schema-sibling miss). It did NOT prevent the CP14→CP16 second-recurrence pattern (15 identifier_type values added without §4.4 Lynceus mapping sibling). The strengthening addresses three structural-discipline gaps surfaced by the second recurrence:

1. **Explicit dispatch-checkpoint language is missing.** The rule said "every downstream consumer must be updated in parallel sibling commits within the same coordinated landing" but did not specify WHEN in the CP/SAR dispatch the audit fires. CP14's dispatch had Phase 1 (drafting), Phase 2 (CEO-skeptic self-review), Phase 3 (DDL fold-in), Phase 4 (promotion) — none explicitly listed a §4.4 + IDENTIFIER_TYPE_TO_PATTERN_TYPE downstream-consumer audit as a checkpoint. The rule lived in memory but did not propagate into dispatch templates.

2. **Cumulative-audit-runs-against-FULL-enum sub-rule is missing.** The rule mentioned the consumer-audit checklist but did not specify that the audit checks the ENTIRE field's value set, not just the CP's new additions. If CP14 had audited only the 15 new types (which it didn't), it might still have missed an earlier-CP type that slipped through. The Phase 2 result of MAC-75 confirmed no such latent gaps exist post-CP14, but the rule needs language so future CPs can affirmatively re-anchor "clean beyond [CP-N] additions" as part of their audit.

3. **Recurrence-count tracking is missing.** The rule did not log historical recurrences. Without that audit trail, future CPs cannot tell whether a discipline failure is a first-time miss or a recurrence pattern. CP14→CP16 is the second recurrence; the strengthened rule logs it explicitly so a future third recurrence would be a structural pattern rather than a one-off.

---

## Strengthened memo text (copy-pasteable replacement for the live memo body)

The replacement is APPEND-AND-AMEND, not full-rewrite. The original rule body is preserved verbatim (so the audit trail of what was codified WHEN is preserved); the strengthening adds new sections at the end. Frontmatter `description` updates to reflect the strengthening.

```markdown
---
name: Bible amendments need parallel updates to ALL downstream consumers as sibling commits
description: When a CP/SAR-class bible amendment adds values to a field (enum extension, mapping table row, sub-band entry, etc.), every downstream code consumer must be updated in the same coordinated commit. Pre-flight audit at amendment-ratification time. Strengthened CP16: explicit dispatch-checkpoint language + cumulative-full-enum audit sub-rule + recurrence-count tracking.
type: feedback
originSessionId: c0e19be1-a303-4789-94e6-98563bb9e87d
---
When a CP/SAR-class bible amendment adds values to a field that downstream code consumes (enum entry, mapping-table row, sub-band, validator rule entry, export filter, coverage-report bin), every downstream consumer must be updated in parallel sibling commits within the same coordinated landing — not deferred to follow-up issues.

**Why:** Two same-shape gaps surfaced in succession during the MAC-55 cycle:
1. CP12 §8.2 source_type sub-band added `manufacturer_app` without 0009 schema-migration sibling → caught at MAC-54 pre-flight (BLOCKER on Wave G promotion).
2. CP13 §4.4 mapping table added `ble_local_name`/`ble_characteristic`/`product_family_codename` without `db/validation/export_lynceus.py` IDENTIFIER_TYPE_TO_PATTERN_TYPE sibling update → caught at MAC-55 Step 4 export-regen halt → forced MAC-57 dispatch + MAC-55 block.

The recurrence confirms structural discipline is needed. CP13 codified the schema-migration sibling rule, but generalizing to ALL downstream consumers wasn't done. Board explicitly endorsed extending the rule at [MAC-55 e828c89f](/MAC/issues/MAC-55#comment-e828c89f-c93a-4fa1-adef-437d865548ad).

**How to apply.** At CP/SAR amendment-ratification time (CEO's §11 #11 amendment-text + sibling-implementation review gate), enumerate ALL downstream consumers of the affected field and verify each has a parallel update queued in the coordinated commit. Consumer audit checklist for fields:

- **Schema CHECK constraints** (caught at INSERT time if missing — hard block) — `db/migrations/*.sql`
- **Lynceus export mapping table** — `db/validation/export_lynceus.py` IDENTIFIER_TYPE_TO_PATTERN_TYPE + `_classify_row()` + `bins` dict + `fmt_bin_table()` coverage rows
- **Validator promotion rules** — Validator hire-config runbook + §11 #7 / §11 #8 gate checks
- **Coverage matrix surfaces** — `extraction_outputs/mac45/coverage_matrix_report.json` + `coverage_matrix.md` pre-tally
- **Tests** — `tests/test_*.py` files exercising the amended field
- **Wave-A snapshot / canonical fixtures** if any field-value lookups are hardcoded

If a consumer is going to be updated in a follow-up rather than the coordinated commit, name it explicitly in the CP/SAR amendment-log entry and create the follow-up issue as a `blockedBy` dependency BEFORE the ratification gate closes — not after the gap fires.

Codification scope-call: this is a CEO-side gate rule (amendment-ratification). The Validator-side companion (Step 1 staging must dry-run the export worker for CP/SAR-recent values) is in [feedback_promotion_gate_needs_export_dryrun.md](feedback_promotion_gate_needs_export_dryrun.md). The two together form the bi-directional discipline: CEO audits at ratification, Validator dry-runs at promotion.

---

## Strengthening (added Correction Pass 16, 2026-05-12 — after CP14→CP16 second recurrence)

The original rule (above) codified the *what* (every downstream consumer must update in parallel sibling commits) but did not codify the *when* (which phase of a CP/SAR dispatch the audit fires) or the *scope* (audit the new values only, or the entire field's value set). CP14 missed the §4.4 + IDENTIFIER_TYPE_TO_PATTERN_TYPE sibling update for 15 identifier_type values added across migrations 0011/0013/0014; the gap was caught at MAC-63 Phase-5 export-regen attempt 2026-05-11 (the second recurrence of this pattern after CP13→MAC-57 was the first recurrence). The strengthening below addresses the structural-discipline gaps that allowed CP14's miss.

### S.1 — Explicit dispatch-checkpoint language

**Rule:** Every CP/SAR dispatch that adds values to a field with downstream code consumers MUST include an explicit "downstream-consumer audit" phase as a self-review checkpoint, named in the dispatch itself by phase number.

**How to apply:**
- When drafting a dispatch that touches an enum, mapping table, source-band, validator rule, export filter, or coverage-report bin, the dispatch §2 phase breakdown MUST include a phase titled "Downstream-consumer audit" (or equivalent) BEFORE the apply phase.
- The downstream-consumer-audit phase enumerates EVERY consumer of the affected field (per the §"How to apply" checklist above), checks each one's current value-set against the post-CP value-set, and reports drift.
- The downstream-consumer audit MUST verify-and-halt — the apply phase does not proceed until the audit is ratified.

**Why:** The CP14 dispatch had 4 phases (drafting / self-review / DDL fold-in / promotion) but none of them explicitly listed §4.4 + IDENTIFIER_TYPE_TO_PATTERN_TYPE audit as a self-review checkpoint. The discipline rule existed in memory but did not propagate into dispatch templates, so the audit fired ad-hoc (or didn't fire at all). Explicit dispatch-checkpoint language makes the audit a structural part of every applicable CP/SAR dispatch.

### S.2 — Cumulative-audit-runs-against-FULL-enum sub-rule

**Rule:** The downstream-consumer audit checks the ENTIRE field's value set, not just the CP's new additions. The audit affirmatively reports either:
- (a) "Clean beyond [CP-N] additions" — confirming no latent earlier-CP gaps slipped through, or
- (b) An explicit latent-gap list with disposition (fold into current CP if same shape; otherwise log a separate finding for future-CP scope).

**How to apply:**
- Mechanical sweep: list every value in the post-CP field enum; for each value, check presence in each downstream consumer (§4.4 table, IDENTIFIER_TYPE_TO_PATTERN_TYPE dict, schema CHECK, validator rules, coverage report, tests).
- Drift detection: any value missing from a consumer surface is a gap. Decide whether to fold into the current CP (same-shape gaps) or log separately (different-shape).
- Anchor the result: "Cumulative-audit result: clean beyond [CP-N] additions" becomes a referenceable audit-trail entry that future CPs can build on. Phase 2 of MAC-75 CP16 dispatch is the first instance of this discipline; the anchor "clean beyond CP14 additions" is now a baseline reference point for future CPs.

**Why:** The original rule said "every downstream consumer must be updated in parallel sibling commits" but did not specify that the audit checks the ENTIRE field, not just the CP's new additions. A CP could in principle audit only its new additions and miss an earlier-CP type that silently slipped through. Cumulative-full-enum audit catches latent gaps and anchors the "clean beyond" baseline.

### S.3 — Recurrence-count audit trail

**Rule:** Each instance of this discipline firing (catch or miss) is logged with explicit recurrence numbering so future CPs can tell whether the next firing is a one-off or a structural pattern.

**Historical recurrences (audit trail; chronological):**

1. **First recurrence: CP12 → CP13 schema gap (caught at MAC-54 pre-flight, 2026-05-09).**
   - Trigger: CP12 §8.2 source_type sub-band added `manufacturer_app` value without 0009 schema-migration sibling.
   - Catch path: MAC-54 pre-flight detected the gap before any rows promoted.
   - Disposition: CP13's coordinated commit landed the §8.2 amendment + 0009 schema migration together; first instance of the parallel-sibling-commit discipline.
   - Rule state after catch: discipline codified informally, no memo yet.

2. **Second recurrence: CP13 → MAC-57 export gap (caught at MAC-55 Step 4, 2026-05-09).**
   - Trigger: CP13 §4.4 mapping table added 3 Wave-G analytical-only types (`ble_local_name`, `ble_characteristic`, `product_family_codename`) without IDENTIFIER_TYPE_TO_PATTERN_TYPE sibling update.
   - Catch path: MAC-55 Step 4 export-regen halt; forced MAC-57 dispatch + MAC-55 block.
   - Disposition: MAC-57 landed the dict update; CP13's missed sibling commit closed retroactively.
   - Rule state after catch: original feedback memo (this file's pre-CP16 body) codified at MAC-55 e828c89f 2026-05-09. Discipline rule lived in memory; did not propagate into dispatch templates.

3. **Third recurrence: CP14 → CP16 §4.4 mapping gap (caught at MAC-63 Phase 5, 2026-05-11).**
   - Trigger: CP14 added 15 identifier_type enum values via migrations 0011/0013/0014 without §4.4 Lynceus mapping table sibling or IDENTIFIER_TYPE_TO_PATTERN_TYPE sibling update.
   - Catch path: MAC-63 Wave-A Ratification Run Phase 5 surfaced the gap pre-promotion-cycle-2 attempt; CC's own self-review per the codified memo. (The discipline rule fired correctly — it just did so retroactively, at promotion-time, rather than preventively, at dispatch-design-time.)
   - Disposition: MAC-75 CP16 dispatch closes the §4.4 + dict gap in a coordinated commit; memo strengthened with the three sub-rules (S.1 + S.2 + S.3) to prevent the next recurrence at dispatch-design time.
   - Rule state after catch: this strengthening section codified at MAC-75 Phase 5 close 2026-05-12.

**Forward expectation:**
- A fourth recurrence under the strengthened rule would indicate the dispatch-checkpoint language isn't propagating effectively into dispatch authoring practice; that would be a structural-template-discipline question, not a memo-strengthening question.
- Each future CP/SAR-class amendment that touches a downstream-consumer field affirmatively cites this memo + its strengthening section in the dispatch's §1 context load + §2 phase breakdown. The dispatch's downstream-consumer-audit phase reports either "clean beyond [CP-N-1] additions" or an explicit gap list.

### S.4 — How the strengthening composes with other memos

The strengthening preserves the bi-directional discipline established in the original memo:
- CEO-side gate (this memo) — audit fires at CP/SAR amendment-ratification dispatch time.
- Validator-side companion ([feedback_promotion_gate_needs_export_dryrun.md](feedback_promotion_gate_needs_export_dryrun.md)) — Step 1 staging must dry-run export worker for CP/SAR-recent values.

CP16 strengthens the CEO-side gate; the Validator-side companion is unchanged. If a future Validator-side miss surfaces, the corresponding companion memo strengthens independently. The two memos compose because they fire at different layers of the lifecycle (dispatch design vs. promotion staging).

The strengthening also aligns with [feedback_cumulative_check_enum_across_sequenced_migrations.md](feedback_cumulative_check_enum_across_sequenced_migrations.md) — that memo handles the *schema-migration* cumulative-CHECK carryforward; this memo's S.2 sub-rule handles the *downstream-consumer-audit* cumulative-full-enum sweep. The two are parallel disciplines at different stack layers (schema vs. application).

### S.5 — Code-patch staging discipline (added by CP16; structural-extension move)

CP16 introduced `db/validation/_drafts/` as a new staging directory, mirroring the established `db/migrations/_drafts/` pattern. This is the FIRST instance of code-patch staging using the parallel-`_drafts/` shape, and codifies the discipline for future CP/SAR code-sibling patches.

**Rule:** When a CP/SAR-class amendment requires a coordinated code-patch sibling (per the bi-directional-discipline composition with this memo and the Validator-side companion), the code patch stages at `<code-module>/_drafts/<patch_name>.py.draft` during Phase 3 (drafting) and Phase 4 (self-review), and moves to the live path during Phase 5 (apply) alongside the bible commit. Existing precedent paths:

- **Migrations:** `db/migrations/_drafts/` (established pre-CP12; first batch CP12 → migration 0009).
- **Validation/Export:** `db/validation/_drafts/` (established CP16 2026-05-12 with `export_lynceus_cp16_patch.py.draft`).

Future code-sibling patches in additional modules adopt the same shape (`<module>/_drafts/<name>.<ext>.draft`). The discipline-extension move is intentional: a single uniform shape across all sibling-commit code paths makes the audit trail predictable and the staging discipline structurally identical regardless of which code module gets the parallel update.

The discipline composes with §11 #11 (amendment-log discipline): the bible amendment in the CP/SAR coordinated commit names the staged code patch path so the audit trail explicitly links the bible-side amendment to the code-side staged patch. Phase 5 apply moves the draft to live and includes the move in the same commit.
```

---

## Cross-references for the strengthening

- **MAC-75 dispatch** `017df17b` 2026-05-12 (CP16 fresh §11 #11 delegation; explicit dispatch-checkpoint asks)
- **MAC-75 Phase 1 ratification** `ee60c712` 2026-05-12 (15-disposition ratification + override-with-rationale discipline confirmed)
- **MAC-75 Phase 2 ratification** `5b9212ce` 2026-05-12 ("clean beyond CP14 additions" anchor recorded; second-recurrence count correction acknowledged)
- **MAC-63 Phase 5 surfacing** at `raw/wave_a/_promotion_cycle_2_candidates_2026-05-11.md` §0 (the CP14→§4.4 gap finding that triggered MAC-75)
- **MAC-55 e828c89f** (original memo codification 2026-05-09 — preserves audit-trail of WHEN the discipline rule was first codified)
- **MAC-54 pre-flight catch** of CP12→CP13 (first recurrence; pre-memo)
- **MAC-57 dispatch** (CP13→export-regen gap retrospective fix; second recurrence in the historical count)
- **`feedback_promotion_gate_needs_export_dryrun.md`** (Validator-side companion memo; unchanged by CP16)
- **`feedback_cumulative_check_enum_across_sequenced_migrations.md`** (parallel discipline at schema-migration layer; unchanged by CP16)

---

## Recurrence-count clarification (Phase 2 board correction)

The Phase 2 verification report initially framed this as the **second recurrence** under the codified rule. Board correction at `5b9212ce`: "this is the second recurrence, not the third." The historical recurrences listed in S.3 above are numbered from the perspective of the *pattern of missed downstream-consumer updates*:

- **Recurrence #1 (CP12 → CP13)** = first instance of the discipline firing (caught at MAC-54 pre-flight, pre-memo).
- **Recurrence #2 (CP13 → MAC-57)** = first instance under the memo (caught at MAC-55 Step 4; the codification trigger).
- **Recurrence #3 (CP14 → CP16, THIS event)** = second post-memo recurrence; the trigger for this strengthening.

If counting only post-memo events, this is recurrence #2 — which matches the board's "second recurrence" framing. If counting all instances of the pattern (including pre-memo), this is recurrence #3 — which matches the conservative historical-audit-trail framing in S.3 above. **Both framings coexist in the memo:** the recurrence-count-tracking sub-rule (S.3) preserves the full historical sequence; the framing in conversational summaries leans on the post-memo-only count (matches board direction).

---

## §11 #11 statement

This is a CEO-authored memo-strengthening draft staged under MAC-75 §11 #11 fresh delegation 2026-05-12. **NOT applied** to the live memo. Phase 4 self-review pass reads this draft against the live memo and confirms the strengthening doesn't break composition with adjacent memos (per S.4); Phase 5 coordinated commit moves the strengthening into the live memo in lockstep with the bible §4.4 amendment + the code patch.
