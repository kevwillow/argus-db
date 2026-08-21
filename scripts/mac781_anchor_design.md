# MAC-781 — Anchor design for the BIBLE_AMENDMENTS.md:4197 repair (Rev 3)

Status: **REV 3 — CEO sequencing correction applied (comment 103cbe96).
Lane now runs BEFORE the MAC-764 force-push (so the corrected export
rides the release), not after. Blocker edge moved from MAC-764 to
MAC-783 (Validator's reconcile-and-polish lane) so we do not have two
agents writing the DB and exports at once.**

Lane: DB Architect ([MAC-781](<TRACKER_URL>issues/MAC-781)).
Scope: `identifiers.notes` DML + `exports/argus_export.csv` regen.
Stage: STAGE-ONLY. No push, no tag.

## Rev 3 changelog (CEO comment 103cbe96)

| Change | Reason |
|---|---|
| Lane runs BEFORE MAC-764 force-push, not after | A fix that lands after the rewrite does not ride the single force-push that carries the release. |
| Blocker edge moved from MAC-764 to MAC-783 | MAC-783 (Validator) is the lane that reconciles every number the repo cites and lightly polishes README. Two agents writing the DB and exports at once is the failure to avoid. |
| `operator_review/MAC-781/ANCHOR_DESIGN.md` and `apply_migration.py` moved to `scripts/mac781_anchor_design.md` and `scripts/mac781_apply_migration.py` | MAC-764 rewrites `operator_review/` from the working tree. The local authority documents must live outside that scope. |
| Record-count invariant is `43126` exactly | `0064` is data-only against `identifiers.notes` with no DDL, so it must not admit, withdraw, or supersede a single row. |
| `is_arm = 1` (not `parent_manufacturer_id IS NOT NULL`) | CEO measurement-trap note: the OEM-arm predicate is `is_arm=1` (92 rows), not `parent_manufacturer_id IS NOT NULL` (94 rows). The MAC-781 lane does not touch this, but it is recorded so downstream consumers of the design doc do not repeat the misread. |
| CSV meta-line trap recorded | The CSV's first line is `# meta:` (a provenance comment), not the header. A naive `csv.reader` plus `next()` eats the meta line, treats the real header as data, and reports `43,127` instead of `43,126`. Skip the meta line explicitly when parsing the export. |

## Rev 2 changelog

| Change | Reason |
|---|---|
| Cite path is `docs/engineering/BIBLE_AMENDMENTS.md#...` (full repo-relative) | CEO §Q1.1 — root `BIBLE_AMENDMENTS.md` is a 7-line stub. Bare-path cite reproduces the exact bug being fixed. |
| Slug is `mac781-cp33-s2-1-cctv_camera` (ASCII only, no `§`) | CEO §Q1.2 — `§` percent-encodes to `%C2%A72.1` in URL fragments. Pattern is published in a CSV column read downstream by people who did not write it. |
| Anchor+clause gate ships in this change | CEO §Q1.3 — previous "no new gate required" claim was false. `check_doc_anchors.py` explicitly does NOT cover anchor or section references; the previous drift detector was a human trip-wire, which is exactly the failure class MAC-781 exists to fix. |
| Audit stamp uses `tracker URLs`, not `<TRACKER_URL>` | CEO §Q2.1 — proposed stamp reintroduced the token it strips. `POST-4` (`0 <TRACKER_URL> URLs survive`) would fail under the proposal's own stamp. |
| Strip rewrite is bare (no backticks) | CEO §Q2.2 — CSV data field, not rendered markdown. |
| POST-5 (`json_valid(notes)` shape preserved) is load-bearing | CEO §Q3 — option (a) plain-text suffix, `json_valid=0` for all 62 rows. POST-5 mechanically enforces this; not decorative. |

## 1. Findings pinned at `main` 1903c24

| Defect | Count | Affected rows (DB) | Affected notes |
|---|---|---|---|
| Half 1 — `BIBLE_AMENDMENTS.md:4197` is dead | 9 rows | `id IN (44677, 44703, 44704, 44705, 44706, 44707, 44708, 44709, 44710)` | JSON `$.category_correction_authority` |
| Half 2 — `<TRACKER_URL>` URLs in `notes` | 62 rows × 2 URLs = 124 occurrences | `id >= 413` board-ratification cohort | plain-text `Board ratifications:` line |

The two halves are **disjoint** — none of the 9 `:4197` rows carry `<TRACKER_URL>`
URLs (verified via `SELECT id FROM identifiers WHERE notes LIKE '%:4197%' AND notes LIKE '%<TRACKER_URL>%' AND superseded_by IS NULL` → 0 rows).

`docs/engineering/BIBLE_AMENDMENTS.md:4197` resolves to an `adsb.lol`
source bullet; the `cctv_camera` clause actually lives at `:4264` (off
by 67 lines). `PROJECT_BIBLE.md:323` is correct and preserved
byte-identically.

The 7-line stub at the repo root `BIBLE_AMENDMENTS.md` contains zero
`cctv_camera` matches and is preserved only for grep compatibility. It
is **not** the cited document; the cite targets
`docs/engineering/BIBLE_AMENDMENTS.md`.

## 2. Anchor design — Half 1

### What failed

The current cite is:

```
BIBLE_AMENDMENTS.md:4197 — `cctv_camera` 'Distinguishes general-purpose CCTV from existing `covert_cam`'; PROJECT_BIBLE.md:323 — `covert_cam` 'covert by definition'
```

A bare line number into a 6305-line living document silently drifted when
the document was edited between `:4197` and `:4264`. The line-number half
still *resolves* (so nothing errored), it just resolves to a wrong clause.
Worst failure mode: silent drift, no signal.

### What the CEO ruled out

A bare repoint to `:4264` is the same failure mode with a 6-month shelf
life. The fix must be structural AND mechanically checkable.

### Proposal — three-coordinate structural anchor + quoted clause + gate

Replace `:4197` with a **structurally-rooted anchor** whose identity is
defined by the document's own hierarchy, not its line count. Add an HTML
anchor inside the cited cell, and ship a gate that mechanically asserts
the anchor resolves to exactly one line and the quoted clause text in
`notes` still matches that line.

```
docs/engineering/BIBLE_AMENDMENTS.md#mac781-cp33-s2-1-cctv_camera — `cctv_camera` 'Distinguishes general-purpose CCTV from existing `covert_cam`'; PROJECT_BIBLE.md:323 — `covert_cam` 'covert by definition'
```

The slug `mac781-cp33-s2-1-cctv_camera` decomposes as:

| Token | Source | Stability |
|---|---|---|
| `mac781` | Lane that introduced the anchor | Permanent — added by this commit |
| `cp33` | The Correction Pass (CP33 = the cohort amendment cycle for `cctv_camera`) | Permanent — CP numbers never renumber |
| `s2-1` | Section within CP33 (`### §2.1 — device_category CHECK enum +3 net-new values`) | ASCII hyphenated form of `§2.1` — survives URL fragment encoding |
| `cctv_camera` | Row label inside the §2.1 cohort table | Drift-detectable by visual diff |

The anchor is implemented in `docs/engineering/BIBLE_AMENDMENTS.md` as
an explicit HTML anchor inserted inside the `cctv_camera` table cell
(line 4264):

```html
| `cctv_camera` <a id="mac781-cp33-s2-1-cctv_camera"></a> | Commercial/consumer | S2 | Distinguishes ... |
```

HTML anchors are part of GitHub-flavored markdown. The gate ships in
the same change.

### Drift detection — the gate, not the human

`scripts/check_doc_anchors.py` explicitly does **not** cover anchor or
section references; its own docstring names them in the not-covered
list. The previous proposal's "a reviewer clicking the anchor sees the
drift" was a human trip-wire. The `BIBLE_AMENDMENTS.md:4197` defect was
that it drifted with no signal — replacing silent failure with human-
noticed failure does not fix the failure class.

**Gate: `scripts/check_mac781_anchor_clause.py`**. Three arms:

1. **Anchor uniqueness** — `<a id="mac781-cp33-s2-1-cctv_camera"></a>`
   resolves to exactly one line in
   `docs/engineering/BIBLE_AMENDMENTS.md`. 0 matches = FAIL (anchor not
   placed). 2+ matches = FAIL (ambiguous).
2. **Clause match** — for every active row carrying the new anchor in
   `notes.category_correction_authority`, the quoted clause text after
   the anchor must be a substring of the document line the anchor
   resolves to. A mismatch is drift.
3. **Idempotency** — no row carries the OLD `:4197` substring after
   migration; no row carries both the OLD and NEW substrings.

The gate ships with a positive control: break the clause text in a
scratch copy of the document, run with `--positive-control <scratch>`,
the gate goes red with rc=1. Five pytest cases lock this behaviour at
`tests/test_check_mac781_anchor_clause.py`.

### Alternatives considered, why this won

| Option | Why rejected |
|---|---|
| Bare repoint to `:4264` | Same failure mode as `:4197`. CEO explicitly ruled out. |
| Section-only anchor (e.g. `#21`) | Heading anchor lands on the section but not the row — a reviewer clicking lands at the table top, not the `cctv_camera` cell. The cite loses row-level fidelity. |
| SHA256 of the quoted clause | Self-validating but opaque; a reader cannot manually verify the cite without running a hash. |
| Stub-path cite (`BIBLE_AMENDMENTS.md#...`) | The 7-line root stub contains zero `cctv_camera` matches. A cite to the stub is silent misresolution — the exact bug being fixed. CEO §Q1.1. |
| `§`-containing slug | `§` percent-encodes to `%C2%A72.1`. Published in a CSV column read downstream by people who did not write it. CEO §Q1.2. |
| Human trip-wire alone | Replaces silent failure with human-noticed failure; the entire defect was silent drift. CEO §Q1.3. |

## 3. Tracker URL strip — Half 2

### Pattern in canonical notes

The 62 affected rows carry this plain-text ratification history:

```
Board ratifications: strict-§8.4 MAC-1 [`613ec532`](<TRACKER_URL>issues/MAC-1#comment-613ec532-d8cb-4f0f-a35b-c811e2864d7d) 2026-05-06T17:08:16Z; SAR-9 [`234faaa7`](<TRACKER_URL>approvals/234faaa7-e1c0-40fd-a247-f82cb588fc23) 2026-05-06T18:05:53Z.
```

Two URL forms appear:
- `<TRACKER_URL>issues/MAC-N#comment-<32-hex>` — comment anchor
- `<TRACKER_URL>approvals/<uuid>` — approval anchor

### Proposal — strip the URL, keep the textual reference, BARE

Rewrite each URL to its textual reference form. The textual identifiers
(`MAC-N`, `SAR-N`, the comment hash, the approval uuid prefix) are
preserved; only the internal-tracker URL disappears. **Bare, no
backticks** (CSV data field, not rendered markdown).

```
Board ratifications: strict-§8.4 MAC-1 comment 613ec532 2026-05-06T17:08:16Z; SAR-9 approval 234faaa7 2026-05-06T18:05:53Z.
```

- `<TRACKER_URL>issues/MAC-1#comment-613ec532d8cb...` → `MAC-1 comment 613ec532` (drop the URL, keep 8-char hash prefix)
- `<TRACKER_URL>approvals/234faaa7-e1c0-40fd-a247-f82cb588fc23` → `SAR-9 approval 234faaa7` (drop the URL, keep 8-char uuid prefix)

### Drift detection

The textual references are stable identifiers in their own right.
`MAC-1` is the issue identifier; `SAR-9` is the SAR identifier; the
8-char prefixes are sufficient to disambiguate. A reader can grep
canonical for `MAC-1 comment 613ec532` and locate the original cite in
the operator's audit trail.

### Audit stamp — uses `tracker URLs`, NOT `<TRACKER_URL>`

Appended per row in plain-text suffix form. **The literal string
`<TRACKER_URL>` does not appear in the stamp** (would re-introduce the token
the strip is removing, fail POST-4 under the proposal's own acceptance
check).

```
mac781_audit: stripped 2 tracker URLs at <ISO8601>; pattern=mac781_v1_tracker_url_strip
```

The count plus the pattern name is sufficient to audit. Re-deriving
the original URL is what the operator audit trail is for.

## 4. Migration shape — `db/migrations/0061_mac781_argus_export_anchor_repair.sql`

Following the established pattern (MAC-705 dead-SHA drop, MAC-737 strict
8.4 amendment landing), the migration has three arms:

### Arm 1 — Pre-state guards

| Guard | Assertion |
|---|---|
| PRE-1 | `schema_version = 35` (no DDL bump) |
| PRE-2 | 9 rows match the `:4197` contract (by `id`, `superseded_by IS NULL`) |
| PRE-3 | 62 rows match the `<TRACKER_URL>` contract (by `notes` LIKE + `superseded_by IS NULL`) |
| PRE-4 | 0 rows overlap Half 1 and Half 2 |
| PRE-5 | Every Half-1 `notes` is well-formed JSON; every Half-2 `notes` is plain text (`json_valid=0`) |
| PRE-6 | Active row count = 43126 (DELTA = 0) |
| PRE-7 | No row is already stamped with `mac781_audit` substring (idempotency) |
| PRE-8 | The new anchor is unique (0 rows carry the new anchor substring pre-migration) |

### Arm 2 — Writes

**Half 1** — for the 9 rows, atomic `json_set`:

```sql
UPDATE identifiers
   SET notes = json_set(
       notes,
       '$.category_correction_authority',
       'docs/engineering/BIBLE_AMENDMENTS.md#mac781-cp33-s2-1-cctv_camera — `cctv_camera` ''Distinguishes general-purpose CCTV from existing `covert_cam`''; PROJECT_BIBLE.md:323 — `covert_cam` ''covert by definition'''
   )
 WHERE (SELECT COUNT(*) FROM _mac781_go) = 1
   AND id IN (44677, 44703, 44704, 44705, 44706, 44707, 44708, 44709, 44710)
   AND superseded_by IS NULL;
```

**Half 2** — for the 62 rows, atomic substring replace + plain-text
audit suffix. The 62 rows are plain text (`json_valid(notes) = 0`).
Rewrite happens in a single UPDATE using `replace()` on two patterns
per row:

```sql
UPDATE identifiers
   SET notes =
         replace(
           replace(
             replace(
               notes,
               '](<TRACKER_URL>issues/MAC-1#comment-613ec532d8cb-4f0f-a35b-c811e2864d7d)',
               '`MAC-1 comment 613ec532`'
             ),
             '](<TRACKER_URL>approvals/234faaa7-e1c0-40fd-a247-f82cb588fc23)',
             '`SAR-9 approval 234faaa7`'
           ),
           ...
         )
         || char(10) || 'mac781_audit: stripped 2 tracker URLs at <ISO8601>; pattern=mac781_v1_tracker_url_strip'
 WHERE (SELECT COUNT(*) FROM _mac781_go) = 1
   AND superseded_by IS NULL
   AND notes LIKE '%<TRACKER_URL>%'
   AND json_valid(notes) = 0;
```

The exact URL replacements are pre-computed from the contract JSONL
listing every distinct URL form across the 62 rows. The migration
loads the contract and applies `replace()` per URL.

### Arm 3 — Post-state guards

| Guard | Assertion |
|---|---|
| POST-1 | `schema_version = 35` (no DDL bump — DELTA from PRE-1) |
| POST-2 | Active row count = 43126 (DELTA = 0) |
| POST-3 | 9 rows carry the new anchor and 0 carry `:4197` |
| POST-4 | 62 rows carry 0 `<TRACKER_URL>` URLs AND 0 occurrences of `<TRACKER_URL>` anywhere in `notes` |
| POST-5 | No Half-2 row's `json_valid` flipped (was 0, still 0) — load-bearing per CEO §Q3 |
| POST-6 | Every Half-1 `category_correction_authority` references `docs/engineering/BIBLE_AMENDMENTS.md#mac781-cp33-s2-1-cctv_camera` |
| POST-7 | Every Half-2 row has the audit stamp (`mac781_audit:` substring present) |
| POST-8 | The new gate (`check_mac781_anchor_clause.py`) runs end-to-end: anchor resolves to 1 line, clause matches, db check passes |

POST-8 is the mechanical drift detector that replaces the human
trip-wire the previous proposal relied on.

## 5. Regen command + acceptance evidence

```
python db/validation/export_lynceus.py --exports-dir exports
python scripts/check_mac781_anchor_clause.py --expected-clause "Distinguishes general-purpose CCTV from existing \`covert_cam\`"
```

Acceptance evidence (CEO-ratified acceptance grep lines):

```
$ wc -l exports/argus_export.csv                                            # 47491
$ head -1 exports/argus_export.csv                                          # record_count=43126
$ grep -o '<TRACKER_URL>' exports/argus_export.csv | wc -l                          # 124 -> 0
$ grep -c 'BIBLE_AMENDMENTS.md:4197' exports/argus_export.csv               # 9 -> 0
$ grep -c 'mac781-cp33-s2-1-cctv_camera' exports/argus_export.csv            # 0 -> 9
$ grep -c '%C2%A7' exports/argus_export.csv                                 # -> 0
$ grep -c 'BIBLE_AMENDMENTS.md#' exports/argus_export.csv                   # -> 9, all path-qualified
$ grep -c 'docs/engineering/BIBLE_AMENDMENTS.md#mac781' exports/argus_export.csv  # -> 9
$ sqlite3 db/argus.db "SELECT COUNT(*) FROM identifiers WHERE superseded_by IS NULL;"  # 43126
```

A naive `csv.DictReader` binds the header to row 0's `# meta:` provenance
line and silently returns nothing for every field. Use a real parse that
skips the meta row. (The same trap is documented at
`scripts/check_doc_anchors.py` section 3.) A 0 from a naive parse is not
proof; positive control against the pre-migration export confirms.

## 6. Open decisions closed by Rev 2

| Decision | Rev 2 ruling |
|---|---|
| Cite path | `docs/engineering/BIBLE_AMENDMENTS.md#...` (full repo-relative) |
| Slug form | `mac781-cp33-s2-1-cctv_camera` (ASCII only, no `§`) |
| Drift gate | New `scripts/check_mac781_anchor_clause.py` ships in this change |
| Audit stamp text | `mac781_audit: stripped N tracker URLs at <ISO8601>; pattern=mac781_v1_tracker_url_strip` (no `<TRACKER_URL>` literal) |
| Strip rewrite form | Bare, no backticks |
| `notes` shape | Option (a) — plain-text suffix; `json_valid(notes)` stays 0 for all 62 rows |

## 7. Sequencing — MAC-764 dependency

The wake payload is explicit: *"Sequence after the MAC-764 purge lands,
so the corrected export is not rewritten underneath you."*

`git log --all --oneline | grep MAC-764` is empty — MAC-764 has not landed.

**Tooling carve-out (DONE before MAC-764)** — `scripts/anchor_resolve.py`
and `scripts/strip_tracker_links.py` were copied from
`operator_review/MAC-773/` BEFORE MAC-764 force-pushes (commit `bcee147`).
The originals live in `operator_review/`, which MAC-764 purges from
history. The new copies are tracked under `scripts/`, outside purge
scope. DML + regen still sequence behind MAC-764.

## 8. What is NOT in this proposal

Stated so omissions are not read as coverage:

- **Not in scope**: any edit to the `:4197` → `:4264` line in BIBLE_AMENDMENTS.md
  prose. The defect is in `identifiers.notes`; the cited clause is correct
  in BIBLE_AMENDMENTS.md at `:4264`. The fix is on the citing side, not
  the cited side.
- **Not in scope**: any other `:NNNN` cite that may also be drifting in
  `identifiers.notes`. A tree-wide census is a CEO scope decision; this
  lane touches only the 9 rows the wake payload named.
- **Not in scope**: the `<TRACKER_URL>` URLs in any other file. The wake payload
  scoped this to `exports/argus_export.csv` (the published feed). Other
  internal files are tracked elsewhere (e.g. `operator_review/MAC-773`
  for BIBLE_AMENDMENTS.md) or are out of scope.
- **Not in scope**: push, tag, merge. STAGE-ONLY. The board reserves every
  push.
- **Not in scope**: any other `BIBLE_AMENDMENTS.md` cite beyond the 9
  rows named. CEO §"Unchanged" ratifies the §8 omissions.

## 9. CEO rulings applied

Rev 2 applies the CEO ruling at comment `197bd963`:

| # | Decision | Status |
|---|---|---|
| 1 | Path correction: full repo-relative path | Applied |
| 2 | Slug form: ASCII only, no `§` | Applied |
| 3 | Anchor+clause gate ships in this change | Applied (`scripts/check_mac781_anchor_clause.py` + `tests/test_check_mac781_anchor_clause.py`) |
| 4 | Audit stamp: no `<TRACKER_URL>` literal | Applied |
| 5 | Strip rewrite: bare, no backticks | Applied |
| 6 | `notes` shape: option (a), POST-5 load-bearing | Applied |
| 7 | Tooling rescue before MAC-764 force-push | Done (commit `bcee147`) |

Once MAC-764 lands, the migration runs against the post-purge canonical.