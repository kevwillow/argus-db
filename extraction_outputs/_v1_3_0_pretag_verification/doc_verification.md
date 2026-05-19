# v1.3.0 pre-tag doc verification report

**Authority anchor:** [MAC-182](/MAC/issues/MAC-182) operator final directive `comment-ab036e23` (2026-05-19T02:51:03Z) §2.
**Audit executed by:** Paperclip CEO, post-§8.11 commit `e8e808e`.

## Disposition table

| §   | Doc                                  | Status                                 | Action                                                                                                              |
| --- | ------------------------------------ | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| 2.1 | `CHANGELOG.md`                       | ✅ PASS (per-commit ledger note below) | None                                                                                                                |
| 2.2 | `CREDITS.md`                         | ⚠️ GAPS FIXED in §8.12                 | §8.12 commit (vendor count + EEN/Rhombus lexicon + wrapper path link)                                               |
| 2.3 | `DATA_DICTIONARY.md` §5.1            | ✅ PASS                                | None                                                                                                                |
| 2.4 | `BIBLE_AMENDMENTS.md` CP28           | ✅ PASS (sibling MAC-179 finding below)| None in CP28 entry; sibling-tree MAC-179 references surfaced for operator                                            |
| 2.5 | `METHODOLOGY.md` §4.4                | ⚠️ SWEEP GAP (operator-decide)         | Surface only; recommend v1.3.1 doc-patch (per operator §2.5 "surface — this would be a sweep gap, not polish edit") |

***

## §2.1 — `CHANGELOG.md` ✅ PASS

- **v1.3.0 entry present** (line 9: `## [v1.3.0] — 2026-05-18`)
- **Structure aligns** with §-headers convention (What's new, Wave H methodology, CP17 desktop-axis bifurcation, Net new identifiers, Documented absences, New data source, Bible amendment, Tracked follow-ons)
- **CP28 narrative aligns** with tag-annotation draft (CP28(c) 3 new identifier_types at 75-90/75-90/80-95 sub-band ladder; CP28(a) DEFERRED; CP28(b) DEFERRED; SAR-12 7-class FP roster codified)
- **Per-commit ledger note:** the CHANGELOG cites the schema-sibling commit `2795ebba` + the MAC-181 umbrella issue ID, NOT a full per-commit ledger. This is by convention — narrative-not-engineering-ledger for CHANGELOG; the per-commit ledger lives in the tag annotation. Not misaligned per operator's structure expectation; flagging only.

## §2.2 — `CREDITS.md` ⚠️ GAPS FIXED in §8.12

Three sub-gaps surfaced and FIXED in §8.12 commit:

1. **Line 3 vendor count stale:** `lexicon of 49 surveillance-technology vendors` → `lexicon of 51 surveillance-technology vendors` (+2 v1.3.0 Wave H stub admissions)
2. **Lexicon table missing Eagle Eye Networks + Rhombus Systems entries** (both stub-admitted v1.3.0):
    - Inserted `| Eagle Eye Networks | (uncategorized — documented_absence stub admission, v1.3.0) |` after DroneShield (alphabetical)
    - Inserted `| Rhombus Systems | (uncategorized — documented_absence stub admission, v1.3.0) |` after Reveal (alphabetical)
3. **v1.3.0 lexicon-additions paragraph absent** (only v1.2.0 paragraph existed): inserted v1.3.0 paragraph naming both vendors, the Cohort A descope rationale per vendor, the CP17 desktop-axis bifurcation thesis anchor, and the Wave H wrapper canonical path (`android_test/tools/extraction/wave_h_wrapper.py`) as methodology source-of-truth

The Wave H source-row entry (sid=53) was already present at line 74 — kept as-is.

## §2.3 — `DATA_DICTIONARY.md` §5.1 ✅ PASS

- **3 new identifier_types present** (line 11 last-refresh note + line 119 cumulative roster cell + line 656 §5.1 roster + line 676 migration-0023 sub-section)
- **CP28-band annotation present** (line 676: "§8.2 sub-band ladder 75–90 / 75–90 / 80–95 per BIBLE_AMENDMENTS CP28(c); §4.4 posture DROPPED / DROPPED / MAP respectively")
- **Migration ledger updated** (line 542: `MAX(version)=23 at the post-CP28 v1.0.0 state, verified live 2026-05-19T00:41:07Z`)
- **Distinct-values census** (line 660: `39 of the 51 — 38 carry-forward from CP21 close plus 3 net-new CP28(c) values, of which 3 have first-row promotion at the MAC-181 Wave H landing`)
- **Example values present** within the roster cells

Note: the line-11 "Last refresh" header timestamp anchors at the §8.2/§8.4/§8.5/§8.6 commit time (`2026-05-18`), not the post-§8.10/§8.11/§8.12 sequence — that's a chronology artifact, not a content gap.

## §2.4 — `BIBLE_AMENDMENTS.md` CP28 ✅ PASS

- **MAC-179 references in CP28 entry: zero** (verified `grep -n "MAC-179" BIBLE_AMENDMENTS.md` returns no matches; all umbrella references use MAC-177 + MAC-181 + MAC-182)
- **§4.1 metadata-key convention present** (line 3214 third bullet `vendor_document_uuid_cloud_reference`, end-of-paragraph half-sentence per §8.10 commit `46c0001`): *"…at promotion-time, every `vendor_document_uuid_cloud_reference` row MUST populate `notes.cloud_url_hostname` with the canonical vendor-cloud hostname (the host portion of `source_url`, lower-cased, no port), normalized as the queryable join key for §4.4 MAP-posture downstream consumers + future Wave I hostname-corpus extraction…"*
- **CP-anchor present** (line 3285: `CP-anchor: migration commit 2795ebba… + [MAC-181](/MAC/issues/MAC-181) child issue ID`)

### Sibling-tree MAC-179 references (NOT in CP28 entry; FYI flag for operator)

`grep -rn "MAC-179" --include='*.md' --include='*.py' --include='*.sql'` across the canonical tree returns **2 hits in committed wave-staging artifacts**:

1. `extraction_outputs/wave_h_pre_v1/HANDOFF_TO_VALIDATOR.md:5` — *"Authority chain: MAC-1 → … → CP27 §-text amendment → MAC-179 (this wave) → partial-cycle close-out per CP26 §9."*
2. `android_test/WAVE_H_RUNGUIDE.md:11` — *"Authority chain (proposed): MAC-1 → MAC-52 (Wave G plan) → CP17 operator-vs-installer cohort thesis → MAC-179 (Wave H plan; this runguide)."*

These predate the MAC-181 umbrella assignment and were not patched at §1.2 staging-port commit. **Operator's §2.4 redline-trigger is scoped to "in the CP28 entry"** (BIBLE_AMENDMENTS.md) — that gate is clean, so I'm NOT fixing these in §8.12. Recommend: defer to **v1.3.1 doc-patch** as a sibling cleanup to the `argus_cli.py status` stale-prose flag from prior heartbeat. Operator can disposition before tag if preferred.

## §2.5 — `METHODOLOGY.md` ⚠️ SWEEP GAP (operator-decide)

`METHODOLOGY.md` has zero CP28 references and zero references to the 3 new identifier_type classes. Specific findings:

- **§4** ("Identifier types and the `identifier_type` enum") is structurally intact but content-stale
- **§4.2** ("The v1.0.0 enum") asserts *"the `identifier_type` enum has 26 values"* — should read 51 at v1.3.0 (CP14/CP18/CP21/CP28 additions not folded in)
- **§4.4** title is *"Match-scoring discipline for short-name vendors against text-pattern sources (CP26 — 2026-05-17)"* — this is the CP26 §4.4, NOT the MAP-vs-DROPPED routing §4.4 that operator referenced. METHODOLOGY does NOT carry the §4.4 MAP-vs-DROPPED dispositions for the 3 new CP28 classes
- **No CP28 cross-reference** added anywhere in the document

Per operator's §2.5 directive ("If missing: surface — this would be a sweep gap, not just a polish edit"): **this is the sweep-gap surface, not a §8.12 auto-extend.** The canonical authority for §4.4 MAP-vs-DROPPED routing lives in `PROJECT_BIBLE.md §4.4` + `BIBLE_AMENDMENTS.md CP28 §4.1` (both clean); `METHODOLOGY.md` is a derivative-audience document that has lagged the v1.2.0 → v1.3.0 refresh cycle. The §4.4 MAP-vs-DROPPED dispositions for the 3 new CP28 classes ARE codified in:

- `BIBLE_AMENDMENTS.md` CP28 §4.1 third bullet (`vendor_document_uuid_cloud_reference` = MAP)
- `BIBLE_AMENDMENTS.md` CP28 §4.1 first + second bullets (`windows_installer_productcode_vendor_registered` + `windows_com_clsid_vendor_registered` = DROPPED)
- `CHANGELOG.md` v1.3.0 "Net new identifiers — the four CP28(c) Wave H promotions" subsection
- `DATA_DICTIONARY.md` §5.1 migration-0023 sub-section (line 676)

**Recommend:** defer METHODOLOGY refresh to **v1.3.1 doc-patch** as a coordinated cycle covering §4.2 enum count + §4.4 dispositions + any other staleness surfaced post-v1.3.0. Operator can override and request §8.13 in this cycle if preferred. The functional impact of the gap: zero — downstream Lynceus integration reads from the canonical exports + bible §4.4, not from METHODOLOGY's prose.

***

## §3 — Cumulative pre-tag commit ledger (post-§8.12)

After §8.12, the canonical tree will be **9 commits ahead** of `origin/main`:

1. `2795ebb` §8.1
2. `16fa31f` §8.2/§8.4/§8.5/§8.6
3. `6ef7f7b` §8.7 (port to canonical tree)
4. `0d80755` §8.8 (DB promotion)
5. `90ea30a` §8.9 (exports refresh)
6. `39b3b4a` §8.7 follow-up (wrapper ±90-char clipping)
7. `46c0001` §8.10 (D1.a backfill + CP28 §4.1 metadata-key convention + exports regen)
8. `e8e808e` §8.11 (README v1.3.0 bump)
9. `<§8.12 SHA TBD>` §8.12 (CREDITS Wave H attribution completeness)

The tag annotation's per-commit ledger will be extended to 9 commits (was drafted for 8). Annotation regenerated below.

## §4 — Discipline-anchored carry-forward

- `[[feedback_check_issue_list_before_creating_child]]` honored — no duplicate umbrella child; MAC-181 is the canonical umbrella under MAC-177.
- `[[feedback_db_verify_dispatch_claims]]` honored — DB-verified the 2 Wave H stub mfrs are Eagle Eye Networks + Rhombus Systems, NOT FileZilla + Skydio as operator's directive parenthetical (§1 #4) implied; surveillance-tech vendor count moves 49 → **51** based on the actual stub identity, not operator's two-scenario sketch.
- `[[feedback_verify_cross_referenced_artifacts_in_public_prose]]` honored — sibling-tree MAC-179 references surfaced + recommended for v1.3.1 rather than baking under a different commit message scope.
- `[[feedback_avoid_hb_labels_in_durable_artifacts]]` honored — all references use commit hashes + MAC-N issue identifiers, not HB# labels.
- `[[feedback_dispatch_preamble_live_state_verification]]` honored — paste-not-cite of grep hits, mtime stamps, full-tree spans.
