# Patch Cycle 1.7 — In-Repo Summary

**Trigger:** PC1 Step E.a smoke test (against runguide §3.4.1 dual-citation degraded mode) empirically established that fccid.io's 2026-05 HTML does NOT expose the `application_id` query parameter or any direct `apps.fcc.gov` link that the runguide assumed. Verified across 3 sample filings: `UXX-S1A415A` (Cradlepoint), `2AO3N-TH39P6ERPI` (Dedrone), `WLI-L3ALV900` (ShotSpotter). Original §6 #5b halt clause would fire on 100% of filings if retained.

**Applied:** 2026-05-17 (this session).
**Dispatch:** MAC-101.

---

## Patches landed (out-of-tree at `/home/kev/argus-internal/new data 5.17/fccid_io_admission_runguide.md`)

| Patch | Scope | Status |
|---|---|---|
| 1.7.A — §3.4.1 step 2 structural amendment | URL construction deferred from extraction to validator; minimal capture (FCC ID + fccid.io URL + HTML sha256) only | applied; verified by grep |
| 1.7.B — §6 halt criteria amendment | DROPPED original §6 #5b (always-fires under live state); NEW §6 #5d (Path C outcome gate); NEW §6 #5e (deferred queue integrity); §6 #5c retained from PC1.4 | applied; verified by grep |
| 1.7.C — §3.0 Path C investigation as Step 0 | New section inserted between `## §3` and `### §3.1`; 6-item investigation list with stability-verification across ≥3 filings; 3-outcome classification (CLEAN POSITIVE / CLEAN NEGATIVE / INCONCLUSIVE) | applied; verified by grep |
| 1.7.D — Deferred queue shape simplification | Removed `constructed_fcc_gov_url` + `url_construction_method` fields; added `fccid_io_source_url`, `fccid_io_html_sha256`, `opportunistic_enrichment` (nullable) | applied; verified by grep |
| 1.7.E — Validator-side re-citation pass | Documented 5-step default navigation + 1-step opportunistic-enrichment shortcut; `last_recitation_attempt_outcome` for permanent-failure preservation | applied; verified by grep |
| 1.7.F — Rejected alternatives | Path B (pre-compute FCC-ID-search URL — can't verify under outage); Path D (drop §3.4.1 — loses §7.4 pilot); conditional dual-mode patch (single-amendment cleaner) | doc-only, this summary |

## Verification greps (post-amendment)

```
grep -c 'application_id is NOT reliably present' fccid_io_admission_runguide.md  →  1  (expected 1)
grep -c '§3.0 — Path C investigation'            fccid_io_admission_runguide.md  →  1  (expected 1)
grep -c '§6 #5d'                                  fccid_io_admission_runguide.md  →  4  (expected ≥2; got 4)
grep -c 'opportunistic_enrichment'                fccid_io_admission_runguide.md  →  8  (expected ≥3; got 8)
```

Bonus: `§6 #5e`=1, `DROPPED §6 #5b`=1, `5-step` navigation=2 — all amendments landed.

---

## What PC1.7 preserves and why

**§7.4 third-party-citation-lineage boundary** remains load-bearing — strengthened actually, since:

- Patch 1.7.A explicitly removes any pre-validator construction of the FCC.gov URL. Aggregator does not even *claim* to know the regulator's filing URL until the validator can fetch and verify it. Eliminates the failure mode where a pre-computed URL could become a phantom citation if FCC.gov's URL convention changed during the outage.
- The discovery row (fccid.io, `crowdsourced` 50-75 band) stands on its own; the regulatory-band companion row only materializes after empirical validator-side FCC.gov navigation succeeds.

**Path A vs Path B trade-off**: Patch 1.7.A formalizes Path A (defer URL construction to validator). Path B (pre-compute FCC-ID-search URL at extraction time) was rejected because pre-computed URLs we can't verify against a reachable regulator are dead weight if FCC.gov's URL convention has changed during the outage. Validator at re-citation time can determine the current URL convention empirically; runguide author at 2026-05 cannot.

**Path C as an opportunistic enrichment, not a requirement**: §3.0 investigation runs as Step 0 to surface any fccid.io alternative endpoint that exposes `application_id`. If found and stability-verified, queue entries get an `opportunistic_enrichment` field that shortcuts the validator's 5-step navigation to 1-step. If NOT found (CLEAN NEGATIVE), §3 proceeds with the minimal queue shape; the run is not blocked.

---

## In-repo artifacts in this commit

- `extraction_outputs/_patch_cycle_1/pc1_7_summary.md` — this file
- (no other in-repo file changes)

## Out-of-tree edits applied alongside this commit

- `new data 5.17/fccid_io_admission_runguide.md` — Patches 1.7.A / 1.7.B / 1.7.C / 1.7.D / 1.7.E applied per find/replace specifications

## Next steps after this commit (per PC1.7 dispatch)

- **Step 2**: §3.0 Path C investigation execution (wall-clock 30-45 min soft / 60 min hard). Output: `extraction_outputs/fccid_io_admission/path_c_investigation.md`. Halt for CEO ack of outcome.
- **Step 3**: Update `scripts/mac101_fccid_pull.py` §3.4.1 branch per Patch 1.7.A minimal shape (+ opportunistic enrichment if Path C CLEAN POSITIVE; + §6 #5e integrity check).
- **Step 4**: Re-run smoke test against `2AO3N-TH39P6ERPI` (Dedrone, 4 test reports — richer than the Change-in-ID sample) end-to-end.
- **Step 5**: Wall-clock budget surface to CEO (PC1.7 actual spend vs §3 budget remaining; extension question).
- **Step 6**: Bulk §3.1 fire with 2h-canary measured from bulk-fire moment (NOT from PC1.7 start).
