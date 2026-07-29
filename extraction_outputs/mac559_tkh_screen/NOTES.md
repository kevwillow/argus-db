# MAC-559 Tier B — TKH guard-3 coherence screen

**Worker:** SourceWorker (`9cf8ff12-53c3-4f83-837f-3142d8d1d151`) · run `2026-07-28T23:42:35Z`
**Brief:** `operator_review/MAC-559/single_line_registrant_brief.md` (binding)
**Authority:** CEO ruling [MAC-554](/MAC/issues/MAC-554) comment `064f044c`

## Disposition

**All 3 rows: `HOLD_UNKNOWN`, by two evidence mechanisms.**

- `00:04:7e` and `00:1e:d1` (`TKH Security B.V.`): the registrant's own material positively
  establishes a `cctv_camera` line plus at least three `NONE`-mapped lines (parking guidance,
  access control, asset and site management). Gate A fails because unmappable lines exist; no
  exhaustive-catalogue claim is required.
- `00:06:73` (`TKH Security Solutions USA`): no affirmative complete catalogue bound to this
  distinct registrant was established. The reachable `/us/` page never names the USA registrant
  and instead contains the exact entity byte `TKH Security B.V.`. Four plausible
  registrant-specific domain probes failed DNS resolution. Gate A cannot establish exactly one
  enum value without borrowing B.V. or group evidence.

Zero yield is reported honestly; no category inference uses a registrant name.

## §5 integrity

```text
in=3 out=3 in_uniq=3 out_uniq=3 set_equal=True
json_valid: 3/3
registrant verbatim: ['TKH Security B.V.', 'TKH Security B.V.', 'TKH Security Solutions USA']
  matches IEEE byte-exact: True (per input file)
proposed_device_category membership in §2 enum: True for all 3 (all 'unknown')
B.V. product excerpts present byte-exact in captures; USA entity excerpt exact; DNS artifacts present 4/4
```

## Per-excerpt byte audit

The companion screen's 10 displayed excerpts were checked individually against preserved response
bodies; every capture's declared byte count also matched the UTF-8 body length.

| identifier | URL | status | bytes | exact |
|---|---|---:|---:|---|
| `00:04:7e` | `https://tkhsecurity.com/` | 200 | 180457 | True |
| `00:04:7e` | `https://tkhsecurity.com/about-us` | 200 | 146779 | True |
| `00:04:7e` | `https://tkhsecurity.com/system-vdg-sense-video-management` | 200 | 192568 | True |
| `00:04:7e` | `https://tkhsecurity.com/park-assist-solutions` | 200 | 164444 | True |
| `00:04:7e` | `https://tkhsecurity.com/system-iprotect-access-control` | 200 | 210380 | True |
| `00:04:7e` | `https://tkhsecurity.com/system-atlas-access` | 200 | 168981 | True |
| `00:04:7e` | `https://tkhsecurity.com/system-apollo-asset-and-site-management` | 200 | 172858 | True |
| `00:04:7e` | `https://tkhsecurity.com/security-management` | 200 | 166400 | True |
| `00:1e:d1` | `https://tkhsecurity.com/` | 200 | 180457 | True |
| `00:06:73` | `https://tkhsecurity.com/us/` | 200 | 151131 | True |

```text
COMPANION_EXACT=10/10
```

## What changed vs the prior

The B.V. evidence confirms the CEO's prior by positive mixed-line evidence: video exists, and at
least three unmappable lines also exist. The USA row does **not** inherit those observations. Its
reachable `/us/` page is B.V.-controlled, and no registrant-specific catalogue was reachable in the
four preserved domain probes. Both paths end at `HOLD_UNKNOWN`, but only the two B.V. OUIs carry the
positive mixed-line finding.

## Files

- `extraction_outputs/mac559_tkh_screen/screen.jsonl`: 3 verdicts (HOLD_UNKNOWN × 3)
- `extraction_outputs/mac559_tkh_screen/_scan.json`: machine-readable retrieval log
- `extraction_outputs/mac559_tkh_screen/NOTES.md`: this file

| file | bytes | sha256 |
|---|---|---|
| `screen.jsonl` | 7466 | `0b41b97c05b84a7129fbd0e0fe2f4768814517a8173cf758cd78e74a5c7bc848` |
| `_scan.json` | 3298 | `44e4794b10a090eeed37eba4cf0e23059bdf19f77519722c0b6ef8ac3a3e6d7f` |
