#!/usr/bin/env python3
"""Argus local search GUI.

A single-file, dependency-free browser UI for searching the Argus export.

    python3 argus_gui.py

Then open http://127.0.0.1:8787 (it opens automatically unless --no-browser).

DESIGN NOTES — why it is shaped this way
----------------------------------------
* READS THE EXPORT, NOT THE DATABASE. `db/argus.db` is gitignored (.gitignore:12
  `db/*.db`) and is ~330 MB, so a fresh public clone has no database at all. The
  CLI already solved this with `--source auto`; this GUI takes the same view and
  reads `exports/argus_export.csv`, which every clone has. Pass --db to read the
  database instead when you happen to have one.

* LOCALHOST ONLY, BY DEFAULT AND ON PURPOSE. Argus exists so people can detect
  surveillance equipment. A hosted instance would accumulate a log of who
  searched which surveillance identifiers from which address -- a record of
  people checking whether they are being surveilled. That is the asymmetry the
  project exists to narrow, so the server binds 127.0.0.1, logs nothing, and
  makes no outbound request. --host is available but warns.

* NO NETWORK ASSETS. All CSS and JS are inline. The page renders with no CDN, no
  fonts, no analytics, and works fully offline.

* FACETS ARE CHOSEN FROM THE DATA. 77% of rows carry device_category='unknown',
  so category is a poor primary axis. identifier_type (51 values) and
  source_type (10) partition the corpus far better, and manufacturer (18,749
  values) is a search box rather than a dropdown. `model` is populated on 0.1%
  of rows and is deliberately not a facet.
"""
from __future__ import annotations

import argparse
import csv
import html
import io
import json
import os
import re
import sqlite3
import sys
import threading
import webbrowser
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

REPO = Path(__file__).resolve().parent
DEFAULT_CSV = REPO / "exports" / "argus_export.csv"
DEFAULT_DB = REPO / "db" / "argus.db"

# Columns the UI reads. Kept explicit so an export column re-order cannot
# silently shift meaning.
FIELDS = [
    "argus_record_id", "id", "identifier", "identifier_type", "device_category",
    "manufacturer", "model", "confidence", "source_type", "source_url",
    "source_excerpt", "geographic_scope", "description", "first_seen",
    "last_verified", "notes",
]
FACETS = ["identifier_type", "device_category", "source_type", "geographic_scope"]
PAGE_SIZE = 50


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------

def load_csv(path: Path) -> tuple[list[dict], dict]:
    """Load the export CSV.

    The first physical line is a `# meta:` comment, not the header. Feeding it
    to DictReader yields a single bogus column and every value empty -- a silent
    failure that looks like an empty database, so it is asserted rather than
    assumed. Fields are also multi-line (notes is published verbatim), so the
    csv module does the parsing; line counting would be wrong.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    first, _, rest = text.partition("\n")
    meta = {}
    if first.startswith("# meta:"):
        for part in first[len("# meta:"):].split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                meta[k.strip()] = v.strip()
    else:  # no meta comment: treat the whole file as CSV
        rest = text
    rows = list(csv.DictReader(io.StringIO(rest)))
    if rows and "identifier" not in rows[0]:
        raise SystemExit(
            f"{path}: parsed header has no 'identifier' column -- got "
            f"{list(rows[0])[:4]}. The file layout changed; refusing to serve "
            f"data that may be misaligned."
        )
    return rows, meta


def load_db(path: Path) -> tuple[list[dict], dict]:
    """Load active rows from the SQLite database (read-only)."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cols = ("id, identifier, identifier_type, device_category, manufacturer, "
            "model, confidence, source_type, source_url, source_excerpt, "
            "geographic_scope, first_seen, last_verified, notes")
    rows = [dict(r) for r in con.execute(
        f"SELECT {cols} FROM identifiers WHERE superseded_by IS NULL")]
    ver = con.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    con.close()
    for r in rows:
        r.setdefault("argus_record_id", "")
        r.setdefault("description", "")
    return rows, {"schema_version": str(ver), "source": "database"}


# --------------------------------------------------------------------------
# Query
# --------------------------------------------------------------------------

def norm(s) -> str:
    return (s or "").strip()


def search(rows: list[dict], q: dict) -> list[dict]:
    text = norm(q.get("q")).lower()
    mfr = norm(q.get("manufacturer")).lower()
    cmin = q.get("cmin")
    out = []
    for r in rows:
        ok = True
        for f in FACETS:
            want = q.get(f)
            if want and norm(r.get(f)) != want:
                ok = False
                break
        if not ok:
            continue
        if mfr and mfr not in norm(r.get("manufacturer")).lower():
            continue
        if cmin is not None:
            try:
                if int(norm(r.get("confidence")) or 0) < cmin:
                    continue
            except ValueError:
                continue
        if text:
            hay = " ".join(norm(r.get(f)) for f in (
                "identifier", "manufacturer", "model", "description",
                "device_category", "identifier_type", "source_url", "notes")).lower()
            if text not in hay:
                continue
        out.append(r)
    return out


def facet_counts(rows: list[dict]) -> dict:
    return {f: Counter(norm(r.get(f)) or "(blank)" for r in rows).most_common()
            for f in FACETS}


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

# Bidirectional and invisible formatting controls. html.escape does not touch
# these, so a value containing U+202E renders as a DIFFERENT identifier than the
# one stored -- in a database whose product is exact identifiers, that is a
# fidelity defect, not a cosmetic one. Replaced with a visible marker rather
# than stripped, so the row is never silently altered.
_BIDI = {
    0x200E: "<LRM>", 0x200F: "<RLM>", 0x061C: "<ALM>",
    0x202A: "<LRE>", 0x202B: "<RLE>", 0x202C: "<PDF>",
    0x202D: "<LRO>", 0x202E: "<RLO>",
    0x2066: "<LRI>", 0x2067: "<RLI>", 0x2068: "<FSI>", 0x2069: "<PDI>",
}
_BIDI_RE = re.compile("[" + "".join(chr(c) for c in _BIDI) + "]")


def e(s) -> str:
    t = str(s if s is not None else "")
    if _BIDI_RE.search(t):
        t = _BIDI_RE.sub(lambda m: _BIDI[ord(m.group(0))], t)
    return html.escape(t, quote=True)


def linkify(url: str) -> str:
    """Render a source URL as a link only when it is a real http(s) URL.

    Many source_url values are internal schemes (argus-internal://,
    manufacturer_app://) that must not become clickable links.
    """
    u = norm(url)
    if u.startswith(("http://", "https://")):
        return f'<a href="{e(u)}" target="_blank" rel="noopener noreferrer">{e(u)}</a>'
    return f'<span class="plain">{e(u)}</span>' if u else ""


# --------------------------------------------------------------------------
# notes humanising
#
# `notes` is published verbatim and is machine-written: 99.6% of rows are JSON,
# 132 carry a prose suffix after the closing brace (the CP39 shape), 43 are
# plain text. Rendered raw it is a wall of internal workflow keys. This turns it
# into grouped, plain-English fields and keeps the raw text one click away.
# --------------------------------------------------------------------------

# key -> (plain english label, group)
NOTE_KEYS = {
    # what the identifier IS and who it belongs to
    "vendor": ("Vendor", "attribution"),
    "surveillance_vendor_flag": ("Flagged as surveillance vendor", "attribution"),
    "ieee_registry": ("IEEE registry block", "attribution"),
    "ieee_assignment_raw_hex": ("IEEE assignment (hex)", "attribution"),
    "assignment_block_size_bits": ("Assignment block size", "attribution"),
    "ieee_self_attributed": ("Self-attributed to IEEE", "attribution"),
    "classification": ("Classification", "attribution"),
    "sig_value_decimal": ("Bluetooth SIG value (decimal)", "attribution"),
    "cp29_value_class": ("Identifier class", "attribution"),
    "value_class_alternates": ("Other possible classes", "attribution"),
    # how confident, and why
    "cp29_confidence_band": ("Confidence band", "confidence"),
    "cp29_band_rationale": ("Why this band", "confidence"),
    "\u00a78.3_lift_applied": ("Corroboration lift applied", "confidence"),
    "attestation_count": ("Independent attestations", "confidence"),
    "source_classes_observed": ("Source classes seen", "confidence"),
    "confidence_history": ("Confidence history", "confidence"),
    "cross_source_corroboration": ("Cross-source corroboration", "confidence"),
    # where it came from
    "raw_observation_id": ("Raw observation id", "provenance"),
    "sha256": ("SHA-256", "provenance"),
    "apk_sha256": ("APK SHA-256", "provenance"),
    "apk_version": ("APK version", "provenance"),
    "packages": ("Android packages", "provenance"),
    "mac349_apk_static": ("From static APK analysis", "provenance"),
    "upstream_license_posture": ("Upstream licence", "provenance"),
    "pii_review_disposition": ("PII review outcome", "provenance"),
    "pii_review_rationale": ("PII review reasoning", "provenance"),
    # free prose
    "_raw": ("Note", "narrative"),
    "_legacy_notes": ("Note", "narrative"),
}
# internal workflow bookkeeping: real, but not what a reader is looking for
INTERNAL_PREFIXES = ("dispatch", "parent_dispatch", "wave", "session_admission",
                     "bucket_origin", "audit", "_parse_error")
GROUP_ORDER = [("narrative", "Note"), ("attribution", "Attribution"),
               ("confidence", "Confidence"), ("provenance", "Provenance")]


def split_notes(raw: str):
    """Return (parsed_dict_or_None, trailing_prose, parse_failed).

    132 rows carry prose AFTER the closing brace; json.loads rejects the whole
    string, which would drop the structured half. Scan to the matching brace and
    treat the remainder as prose.
    """
    n = (raw or "").strip()
    if not n:
        return None, "", False
    if not n.startswith(("{", "[")):
        return None, n, False
    try:
        return json.loads(n), "", False
    except Exception:
        pass
    # The scan MUST respect string context. A naive depth counter treats a `}`
    # inside a JSON string literal as the close of the object, truncates there,
    # fails to parse the prefix, and silently degrades the whole row to
    # "unparseable notes" -- losing the structured half while every test that
    # only asserts "does not raise" still passes. Found by cross-model review
    # 2026-09-13; latent on today's corpus (0 of 43,083 rows) and live the
    # moment any row carries a brace inside a string.
    depth = 0
    in_str = False
    esc = False
    for i, ch in enumerate(n):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(n[:i + 1]), n[i + 1:].strip(), False
                except Exception:
                    return None, n, True
    return None, n, True


MAX_LIST_ITEMS = 40          # the flat-list join was the one uncapped path
MAX_VALUE_DEPTH = 12         # fmt_value recursed with no guard: one deeply
                             # nested row raised RecursionError OUTSIDE any try
                             # and took the whole page down


def fmt_value(v, depth: int = 0, history: bool = False) -> str:
    if v is None:
        return "&mdash;"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, float)):
        return e(v)
    if depth >= MAX_VALUE_DEPTH:
        return '<span class="dim">&hellip; (nested too deeply to display)</span>'
    if isinstance(v, list):
        if not v:
            return "&mdash;"
        shown, extra = v[:MAX_LIST_ITEMS], len(v) - MAX_LIST_ITEMS
        tail = f' <span class="dim">&hellip; +{extra} more</span>' if extra > 0 else ""
        if all(isinstance(x, (str, int, float)) for x in shown):
            return ", ".join(e(x) for x in shown) + tail
        return "<br>".join(fmt_value(x, depth + 1, history) for x in shown) + tail
    if isinstance(v, dict):
        # from/to renders as a provenance arrow ONLY under a key we recognise as
        # a history field. Keyed off `history` rather than the shape, because any
        # row-controlled dict carrying from+to would otherwise be rendered
        # identically to a vetted confidence_history entry -- misrepresentation
        # that needs no injection at all.
        if history and {"from", "to"} <= set(v):
            when = str(v.get("at_utc", ""))[:10]
            why = v.get("rationale") or v.get("basis") or ""
            return f'{e(v["from"])} &rarr; {e(v["to"])}' + (f' <span class="dim">({e(when)})</span>' if when else "") + \
                   (f'<br><span class="dim">{e(str(why)[:160])}</span>' if why else "")
        return "<br>".join(f'<span class="dim">{e(k)}</span> {fmt_value(x, depth + 1, history)}'
                           for k, x in list(v.items())[:8])
    s = str(v)
    return e(s if len(s) <= 400 else s[:400] + "\u2026")


def humanize_notes(raw: str) -> str:
    data, prose, failed = split_notes(raw)
    if data is None:
        if not prose:
            return '<span class="dim">&mdash;</span>'
        label = "unparseable notes" if failed else "note"
        return f'<div class="nv"><span class="dim">{label}</span> {e(prose[:800])}</div>'
    if not isinstance(data, dict):
        return f'<div class="nv">{fmt_value(data)}</div>'

    groups, internal, unknown = {}, [], []
    for k, v in data.items():
        if k in NOTE_KEYS:
            label, grp = NOTE_KEYS[k]
            groups.setdefault(grp, []).append((label, v))
        elif any(k.startswith(p) for p in INTERNAL_PREFIXES) or k.endswith("_audit"):
            internal.append((k, v))
        else:
            unknown.append((k, v))

    out = []
    if prose:
        out.append(f'<div class="ngrp"><div class="nh">Note</div>'
                   f'<div class="nv">{e(prose[:600])}</div></div>')
    for key, title in GROUP_ORDER:
        if key not in groups:
            continue
        out.append(f'<div class="ngrp"><div class="nh">{title}</div>')
        for label, v in groups[key]:
            out.append(f'<div class="nv"><span class="nk">{e(label)}</span> '
                       f'{fmt_value(v, 0, label in ("Confidence history", "Cross-source corroboration"))}</div>')
        out.append("</div>")
    if unknown:
        out.append('<div class="ngrp"><div class="nh">Other</div>')
        for k, v in unknown[:12]:
            out.append(f'<div class="nv"><span class="nk">{e(k.replace("_"," "))}</span> {fmt_value(v)}</div>')
        out.append("</div>")
    if internal:
        items = "".join(f'<div class="nv"><span class="nk">{e(k.replace("_"," "))}</span> {fmt_value(v)}</div>'
                        for k, v in internal)
        out.append(f'<details class="nint"><summary>internal workflow fields '
                   f'({len(internal)})</summary>{items}</details>')
    out.append(f'<details class="nint"><summary>raw notes</summary>'
               f'<pre class="nraw">{e(raw[:4000])}</pre></details>')
    return "".join(out)


PAGE_CSS = """
:root{--bg:#0f1115;--panel:#171a21;--line:#262b36;--fg:#e6e9ef;--dim:#9aa4b2;
--accent:#5aa9ff;--chip:#1f2530;--ok:#41c98a;--warn:#e2b341}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.5 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
header{padding:14px 20px;border-bottom:1px solid var(--line);background:var(--panel);
display:flex;gap:16px;align-items:baseline;flex-wrap:wrap;position:sticky;top:0;z-index:5}
h1{font-size:16px;margin:0;letter-spacing:.3px}
.meta{color:var(--dim);font-size:12px}
.wrap{display:grid;grid-template-columns:280px 1fr;gap:0;align-items:start}
.tablewrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
@media (max-width:860px){
 .wrap{grid-template-columns:1fr}
 aside{position:static;max-height:none;border-right:0;border-bottom:1px solid var(--line)}
 header{position:static}
 main{padding:14px 12px}
 table{min-width:640px}
}
aside{padding:16px 14px;border-right:1px solid var(--line);position:sticky;top:53px;min-width:0;
max-height:calc(100vh - 53px);overflow:auto}
main{padding:16px 20px;min-width:0}
fieldset{border:1px solid var(--line);border-radius:8px;margin:0 0 14px;padding:10px;
min-width:0;min-inline-size:0}
legend{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.08em;padding:0 4px}
input,select{width:100%;background:var(--chip);color:var(--fg);border:1px solid var(--line);
border-radius:6px;padding:7px 8px;font:inherit}
input:focus,select:focus{outline:2px solid var(--accent);outline-offset:-1px}
button{background:var(--accent);color:#05121f;border:0;border-radius:6px;padding:8px 12px;
font:600 13px/1 inherit;cursor:pointer}
button.sec{background:var(--chip);color:var(--fg);border:1px solid var(--line)}
.row{display:flex;gap:8px;margin-top:10px}
table{width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed}
col.c-id{width:23%}col.c-ty{width:10%}col.c-mf{width:14%}col.c-ca{width:12%}
col.c-cf{width:5%}col.c-pv{width:36%}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--dim);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.06em}
tbody tr:hover{background:#141821}
code{background:var(--chip);padding:1px 5px;border-radius:4px;font-size:12px;
font-family:ui-monospace,SFMono-Regular,Menlo,monospace;word-break:break-all}
.chip{display:inline-block;background:var(--chip);border:1px solid var(--line);border-radius:99px;
padding:1px 8px;font-size:11px;color:var(--dim)}
.conf{font-weight:700}
.c-hi{color:var(--ok)} .c-mid{color:var(--warn)} .c-lo{color:var(--dim)}
details{margin-top:6px}
summary{cursor:pointer;color:var(--accent);font-size:12px}
.prov{background:#0c0e13;border:1px solid var(--line);border-radius:6px;padding:10px;margin-top:8px}
td{overflow-wrap:anywhere}
.prov div{margin:4px 0;font-size:12px;color:var(--dim);word-break:break-word}
.prov b{color:var(--fg);font-weight:600}
.plain{color:var(--dim)}
.dim{color:var(--dim)}
.ngrp{margin:8px 0 0}
.nh{color:var(--accent);font-size:10px;text-transform:uppercase;letter-spacing:.08em;
border-bottom:1px solid var(--line);padding-bottom:2px;margin-bottom:4px}
.nv{font-size:12px;margin:3px 0;color:var(--fg);word-break:break-word}
.nk{color:var(--dim);display:inline-block;min-width:130px}
.nint summary{font-size:11px;color:var(--dim);margin-top:8px}
.nraw{white-space:pre-wrap;word-break:break-all;font-size:11px;color:var(--dim);
background:#090b0f;border-radius:4px;padding:8px;margin:6px 0 0;max-height:240px;overflow:auto}
a{color:var(--accent)}
.count{color:var(--dim);font-size:12px;margin-bottom:10px}
.pager{display:flex;gap:8px;align-items:center;margin-top:16px}
.facet a{display:flex;justify-content:space-between;gap:8px;padding:3px 4px;border-radius:4px;
text-decoration:none;color:var(--fg);font-size:12px;align-items:baseline}
.facet a>span:first-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
.facet .n{flex:0 0 auto;font-variant-numeric:tabular-nums}
.facet a:hover{background:var(--chip)}
.facet a.on{background:var(--accent);color:#05121f;font-weight:600}
.facet .n{color:var(--dim)}
.facet a.on .n{color:#05121f}
.empty{padding:40px;text-align:center;color:var(--dim)}
"""


def query_href(q: dict) -> str:
    """A `?query` string safe to drop into an href attribute. URL-encode first
    (so `&`, `+`, `#` in a value survive the round trip), THEN html-escape for
    the attribute. html.escape alone turns `&` into `&amp;`, which the browser
    decodes straight back into a separator."""
    return "?" + html.escape(urlencode(
        {k: v for k, v in q.items() if v not in (None, "")}))


def render(rows_page, total, q, facets, meta, page, src_label):
    def sel(name, value):
        cur = dict(q)
        if norm(cur.get(name)) == value:
            cur.pop(name, None)
        else:
            cur[name] = value
        cur.pop("page", None)
        return query_href(cur)

    parts = [f"""<!doctype html><meta charset="utf-8">
<title>Argus search</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>{PAGE_CSS}</style>
<header><h1>Argus</h1>
<span class="meta">{total:,} matching &middot; {meta.get('record_count','?')} total &middot;
source: {e(src_label)} &middot; exported {e(meta.get('exported_at','?'))}</span>
<span class="meta">local only &middot; nothing leaves this machine</span></header>
<div class="wrap"><aside><form method="get">
<fieldset><legend>text</legend>
<input name="q" value="{e(q.get('q',''))}" placeholder="identifier, model, notes...">
<div class="row"><button>Search</button><a class="sec" href="/" style="text-decoration:none">
<button type="button" class="sec">Reset</button></a></div></fieldset>
<fieldset><legend>manufacturer</legend>
<input name="manufacturer" list="mfrs" value="{e(q.get('manufacturer',''))}" placeholder="e.g. axon">
</fieldset>
<fieldset><legend>min confidence</legend>
<select name="cmin">"""]
    for v in ("", "30", "50", "70", "85", "90"):
        s = " selected" if norm(str(q.get("cmin") or "")) == v else ""
        parts.append(f'<option value="{v}"{s}>{v or "any"}</option>')
    parts.append("</select></fieldset>")
    for f in FACETS:
        parts.append(f'<fieldset class="facet"><legend>{f.replace("_"," ")}</legend>')
        for val, n in facets[f][:14]:
            on = " on" if norm(q.get(f)) == val else ""
            parts.append(f'<a class="{on.strip()}" href="{sel(f, val)}" title="{e(val)} ({n:,})">'
                         f'<span>{e(val)}</span><span class="n">{n:,}</span></a>')
        parts.append("</fieldset>")
    parts.append("</form></aside><main>")
    parts.append(f'<div class="count">showing {len(rows_page)} of {total:,}</div>')
    if not rows_page:
        parts.append('<div class="empty">No rows match those filters.</div>')
    else:
        parts.append("<div class=\"tablewrap\"><table>"
                     "<colgroup><col class=\"c-id\"><col class=\"c-ty\"><col class=\"c-mf\">"
                     "<col class=\"c-ca\"><col class=\"c-cf\"><col class=\"c-pv\"></colgroup>"
                     "<thead><tr><th>identifier</th><th>type</th><th>manufacturer</th>"
                     "<th>category</th><th>conf</th><th>provenance</th></tr></thead><tbody>")
        for r in rows_page:
            try:
                c = int(norm(r.get("confidence")) or 0)
            except ValueError:
                c = 0
            cls = "c-hi" if c >= 85 else ("c-mid" if c >= 70 else "c-lo")
            desc = norm(r.get("description")) or norm(r.get("model"))
            parts.append(
                f"<tr><td><code>{e(r.get('identifier'))}</code>"
                + (f'<div class="meta">{e(desc[:110])}</div>' if desc else "")
                + f"</td><td><span class=\"chip\">{e(r.get('identifier_type'))}</span></td>"
                f"<td>{e(r.get('manufacturer'))}</td>"
                f"<td>{e(r.get('device_category'))}</td>"
                f"<td class=\"conf {cls}\">{e(r.get('confidence'))}</td>"
                "<td><details><summary>source</summary><div class=\"prov\">"
                f"<div><b>source_type</b> {e(r.get('source_type'))}</div>"
                f"<div><b>source_url</b> {linkify(r.get('source_url'))}</div>"
                f"<div><b>excerpt</b> {e(norm(r.get('source_excerpt'))[:400])}</div>"
                f"<div><b>geographic_scope</b> {e(r.get('geographic_scope')) or '<i>null</i>'}</div>"
                f"<div><b>first_seen</b> {e(r.get('first_seen'))} &middot; "
                f"<b>last_verified</b> {e(r.get('last_verified'))}</div>"
                f"<div><b>record id</b> <code>{e(r.get('argus_record_id'))}</code></div>"
                f"{humanize_notes(norm(r.get('notes')))}"
                "</div></details></td></tr>")
        parts.append("</tbody></table></div>")
        pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        if pages > 1:
            def pg(n):
                cur = dict(q); cur["page"] = n
                return query_href(cur)
            parts.append('<div class="pager">')
            if page > 1:
                parts.append(f'<a href="{pg(page-1)}"><button type="button" class="sec">Prev</button></a>')
            parts.append(f'<span class="meta">page {page} of {pages:,}</span>')
            if page < pages:
                parts.append(f'<a href="{pg(page+1)}"><button type="button" class="sec">Next</button></a>')
            parts.append("</div>")
    parts.append("</main></div>")
    return "".join(parts)


# --------------------------------------------------------------------------
# Server
# --------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    rows: list[dict] = []
    meta: dict = {}
    mfr_list: list[str] = []
    src_label = "exports/argus_export.csv"

    def log_message(self, *a):  # no request logging, by design
        pass

    # Binding 127.0.0.1 does NOT defeat DNS rebinding. A page on
    # http://evil.example:8787 whose DNS is re-pointed at 127.0.0.1 reaches this
    # server with Host: evil.example:8787; the browser still considers script and
    # response same-origin, so CORS never engages and the JSON is readable. The
    # only server-side defence is to reject a Host we did not expect. Confirmed
    # by cross-model review 2026-09-13 (codex gpt-5.6-sol).
    # Explicitly configured by main(). When EMPTY the check falls back to the
    # server's own bound address rather than rejecting everything: an empty set
    # meaning "deny all" fails closed but also breaks every programmatic use of
    # this handler, which is a footgun rather than a security property.
    allowed_hosts: set = set()

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").strip().lower()
        if not host:
            return False            # HTTP/1.1 requires Host; absence is hostile
        if self.allowed_hosts:
            return host in self.allowed_hosts
        addr, port = self.server.server_address[:2]
        return host in {f"{addr}:{port}", f"localhost:{port}",
                        f"127.0.0.1:{port}", f"[::1]:{port}"}

    def do_GET(self):
        if not self._host_ok():
            body = (b"Rejected: unexpected Host header.\n"
                    b"This server answers only on its bound address, to prevent "
                    b"DNS-rebinding reads from a website you are visiting.\n")
            self.send_response(421)          # Misdirected Request
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        u = urlparse(self.path)
        if u.path == "/datalist":
            body = ("<datalist id=\"mfrs\">" +
                    "".join(f"<option value=\"{e(m)}\">" for m in self.mfr_list[:800]) +
                    "</datalist>").encode()
            return self._send(body, "text/html; charset=utf-8")
        if u.path == "/api":
            qs = parse_qs(u.query)
            q = {k: v[0] for k, v in qs.items()}
            res = search(self.rows, self._coerce(q))
            return self._send(json.dumps(res[:500], indent=1).encode(), "application/json")
        if u.path not in ("/", "/index.html"):
            return self._send(b"not found", "text/plain", 404)
        qs = parse_qs(u.query)
        q = {k: v[0] for k, v in qs.items()}
        cq = self._coerce(q)
        res = search(self.rows, cq)
        try:
            page = max(1, int(q.get("page", 1)))
        except ValueError:
            page = 1
        start = (page - 1) * PAGE_SIZE
        body = render(res[start:start + PAGE_SIZE], len(res), q,
                      facet_counts(res), self.meta, page, self.src_label)
        body = body.replace("</aside>", '</aside>').replace(
            "<datalist", "<datalist")  # placeholder keeps structure explicit
        body += ("<datalist id=\"mfrs\">" +
                 "".join(f"<option value=\"{e(m)}\">" for m in self.mfr_list[:800]) +
                 "</datalist>")
        return self._send(body.encode("utf-8"), "text/html; charset=utf-8")

    @staticmethod
    def _coerce(q: dict) -> dict:
        out = dict(q)
        try:
            out["cmin"] = int(q["cmin"]) if norm(q.get("cmin")) else None
        except ValueError:
            out["cmin"] = None
        return out

    def _send(self, body: bytes, ctype: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        # frame-ancestors is NOT implied by default-src. Without it any website
        # the user visits can iframe this local UI. X-Frame-Options is sent too
        # for the older parsers that ignore frame-ancestors.
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
                         "form-action 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    ap = argparse.ArgumentParser(description="Local browser UI for searching the Argus export.")
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--db", type=Path, default=None,
                    help="read the SQLite database instead of the CSV export")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--host", default="127.0.0.1",
                    help="bind address; anything other than 127.0.0.1 exposes the UI")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()

    if a.db:
        if not a.db.exists():
            print(f"database not found: {a.db}", file=sys.stderr)
            return 2
        rows, meta = load_db(a.db)
        label = str(a.db)
    else:
        if not a.csv.exists():
            print(f"export not found: {a.csv}\n"
                  f"Argus ships exports/ in every clone; run from the repo root.", file=sys.stderr)
            return 2
        rows, meta = load_csv(a.csv)
        label = str(a.csv.relative_to(REPO)) if a.csv.is_relative_to(REPO) else str(a.csv)

    meta.setdefault("record_count", f"{len(rows):,}")
    Handler.rows = rows
    Handler.meta = meta
    Handler.src_label = label
    Handler.mfr_list = [m for m, _ in Counter(
        norm(r.get("manufacturer")) for r in rows if norm(r.get("manufacturer"))).most_common()]

    if a.host != "127.0.0.1":
        print(f"WARNING: binding {a.host} exposes this UI beyond your machine.\n"
              f"         Argus is a surveillance-detection database; a shared instance\n"
              f"         accumulates a record of who searched which identifiers.\n", file=sys.stderr)

    # Every spelling of the bound address a legitimate browser may send.
    Handler.allowed_hosts = {
        f"{a.host}:{a.port}", f"localhost:{a.port}",
        f"127.0.0.1:{a.port}", f"[::1]:{a.port}",
    }
    if a.port == 80:
        Handler.allowed_hosts |= {a.host, "localhost", "127.0.0.1"}

    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    url = f"http://{a.host}:{a.port}"
    print(f"Argus GUI  {len(rows):,} rows from {label}\n{url}   (ctrl-c to stop)")
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
