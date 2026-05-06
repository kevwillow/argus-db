"""MAC-37 SAR-7 retroactive count delta.

Read-only sweep of Wave-D (court/FOIA) + Wave-E (news/forums) standing-advisory
archives. Counts SAR-7 #2 + SAR-7 #3 retroactive reclassifications (NO row
promotion — count-only per MAC-37 hard-rule §11 #7 carve-out for this step).

Outputs JSON to stdout + a copy under
`extraction_outputs/mac37/sar7_retro_delta.json` for durability.

§11 #6 / WiGLE binding: this script reads only already-staged bytes; no
network fetches.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Add repo root to sys.path so we can import db.extraction.* without install.
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from db.extraction.fcc_grantees_allowlist import (  # noqa: E402
    FCC_ID_RE,
    is_commercial_model_name_fp,
    is_country_jurisdiction_context_fp,
    validate_fcc_id_match,
)

WAVE_D_ROOT = REPO / "raw/court_foia/20260506T030500Z"
WAVE_E_ROOT = REPO / "raw/news_forums/20260506T052423Z"

CONTEXT_WINDOW = 50  # SAR-7 #2 / #3 ±50-char context window (binding spec)

# Search regex for FCC-ID shape in raw bytes.
RE_FCC_ID_TIGHT = re.compile(
    rb"\b([A-Z0-9]{3}|[A-Z0-9]{5})-([A-Z0-9]{4,14})\b"
)
# DJI vendor token (the SAR-7 #2 seed). Survey sweep targets DJI specifically;
# generalization to other vendors covered by predicate test cases.
RE_DJI = re.compile(rb"\b(?:DJI|Dji)\b")

# HTML cleaning (mirrors the wave-fetch cleaning pipeline).
TAG_STRIP = re.compile(rb"<[^>]+>")
WS_COL = re.compile(rb"\s+")
SCRIPT_STRIP = re.compile(rb"<script\b[^>]*>.*?</script>", re.S | re.I)
STYLE_STRIP = re.compile(rb"<style\b[^>]*>.*?</style>", re.S | re.I)


def clean_bytes(raw: bytes, suffix: str) -> bytes:
    s = suffix.lower()
    if s in (".json", ".xml"):
        return raw
    if s in (".html", ".htm"):
        body = SCRIPT_STRIP.sub(b" ", raw)
        body = STYLE_STRIP.sub(b" ", body)
        body = TAG_STRIP.sub(b" ", body)
        return WS_COL.sub(b" ", body)
    return raw


def iter_archive_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.name.startswith("_"):
            # Skip survey/manifest output to avoid double-counting recursive runs.
            continue
        yield p


def context_window_for(text: bytes, start: int, end: int) -> bytes:
    ws = max(0, start - CONTEXT_WINDOW)
    we = end + CONTEXT_WINDOW
    return text[ws:we]


def sweep_archive(root: Path) -> dict:
    """Return per-archive SAR-7 #2 / #3 retro counts."""
    files_scanned = 0
    bytes_scanned = 0

    # SAR-7 #2 — DJI vendor mentions classified by country/jurisdiction context.
    sar7_2_dji_total_mentions = 0
    sar7_2_dji_country_jurisdiction_fp = 0
    sar7_2_dji_real_vendor_mention = 0
    sar7_2_dji_examples_fp: list[str] = []
    sar7_2_dji_examples_real: list[str] = []

    # SAR-7 #3 — FCC-ID matches reclassified as commercial-model-name FP.
    sar7_3_fcc_id_total_matches = 0
    sar7_3_commercial_model_name_fp = 0
    sar7_3_examples: list[dict] = []

    for fp in iter_archive_files(root):
        try:
            raw = fp.read_bytes()
        except OSError:
            continue
        files_scanned += 1
        bytes_scanned += len(raw)
        clean = clean_bytes(raw, fp.suffix)

        # SAR-7 #2 — DJI scan
        for m in RE_DJI.finditer(clean):
            sar7_2_dji_total_mentions += 1
            ctx = context_window_for(clean, m.start(), m.end())
            try:
                ctx_str = ctx.decode("utf-8", "replace")
            except Exception:
                ctx_str = ctx.decode("latin-1", "replace")
            is_fp, reason = is_country_jurisdiction_context_fp("DJI", ctx_str)
            if is_fp:
                sar7_2_dji_country_jurisdiction_fp += 1
                if len(sar7_2_dji_examples_fp) < 5:
                    sar7_2_dji_examples_fp.append(
                        f"{fp.relative_to(REPO)} :: {reason} :: "
                        f"{ctx_str.strip()[:140]}"
                    )
            else:
                sar7_2_dji_real_vendor_mention += 1
                if len(sar7_2_dji_examples_real) < 3:
                    sar7_2_dji_examples_real.append(
                        f"{fp.relative_to(REPO)} :: "
                        f"{ctx_str.strip()[:140]}"
                    )

        # SAR-7 #3 — FCC-ID-shape scan
        for m in RE_FCC_ID_TIGHT.finditer(clean):
            sar7_3_fcc_id_total_matches += 1
            matched_id = m.group(0).decode("ascii", "replace")
            ctx = context_window_for(clean, m.start(), m.end())
            try:
                ctx_str = ctx.decode("utf-8", "replace")
            except Exception:
                ctx_str = ctx.decode("latin-1", "replace")
            is_fp, reason = is_commercial_model_name_fp(
                matched_id, ctx_str,
            )
            if is_fp:
                sar7_3_commercial_model_name_fp += 1
                if len(sar7_3_examples) < 10:
                    sar7_3_examples.append({
                        "file": str(fp.relative_to(REPO)),
                        "matched_id": matched_id,
                        "reason": reason,
                        "context": ctx_str.strip()[:140],
                    })

    return {
        "files_scanned": files_scanned,
        "bytes_scanned": bytes_scanned,
        "sar7_2_dji_total_mentions": sar7_2_dji_total_mentions,
        "sar7_2_dji_country_jurisdiction_fp": (
            sar7_2_dji_country_jurisdiction_fp
        ),
        "sar7_2_dji_real_vendor_mention": sar7_2_dji_real_vendor_mention,
        "sar7_2_dji_examples_fp": sar7_2_dji_examples_fp,
        "sar7_2_dji_examples_real": sar7_2_dji_examples_real,
        "sar7_3_fcc_id_total_matches": sar7_3_fcc_id_total_matches,
        "sar7_3_commercial_model_name_fp": sar7_3_commercial_model_name_fp,
        "sar7_3_examples": sar7_3_examples,
    }


def main() -> int:
    out = {
        "issue": "MAC-37",
        "rule": "SAR-7 retroactive count delta — count-only, no promotion",
        "wave_d": {
            "root": str(WAVE_D_ROOT.relative_to(REPO)),
            **sweep_archive(WAVE_D_ROOT),
        },
        "wave_e": {
            "root": str(WAVE_E_ROOT.relative_to(REPO)),
            **sweep_archive(WAVE_E_ROOT),
        },
    }
    out_dir = REPO / "extraction_outputs/mac37"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "sar7_retro_delta.json"
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True))
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
