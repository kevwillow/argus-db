"""Tests for argus_gui.py — the local search UI.

Covers the traps that would let the GUI show WRONG data rather than no data:

  * the export's first physical line is a `# meta:` comment, not the header.
    Feeding it to DictReader yields one bogus column and every value empty,
    which renders as an empty database rather than an error.
  * `notes` and `source_excerpt` are published verbatim and contain arbitrary
    text, so every rendered value must be HTML-escaped.
  * `source_url` carries internal schemes (`argus-internal://`,
    `manufacturer_app://`) that must not become clickable links.

Skips cleanly when exports/ is absent so a partial checkout does not fail.
"""
import csv
import io
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GUI = REPO / "argus_gui.py"
CSV_PATH = REPO / "exports" / "argus_export.csv"

pytestmark = pytest.mark.skipif(not GUI.exists(), reason="argus_gui.py not present")


@pytest.fixture(scope="module")
def gui():
    spec = importlib.util.spec_from_file_location("argus_gui", GUI)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["argus_gui"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def rows(gui):
    if not CSV_PATH.exists():
        pytest.skip("exports/argus_export.csv not present")
    data, _meta = gui.load_csv(CSV_PATH)
    return data


# --------------------------------------------------------------- loading

def test_meta_comment_is_not_treated_as_the_header(gui, rows):
    """The regression this guards: DictReader on the raw file makes the
    `# meta:` line the header, producing rows whose only key is that comment."""
    assert rows, "no rows parsed"
    assert "identifier" in rows[0]
    assert not any(k.startswith("# meta") for k in rows[0])


def test_meta_is_parsed_into_a_dict(gui):
    _rows, meta = gui.load_csv(CSV_PATH)
    assert "record_count" in meta
    assert meta["record_count"].isdigit()


def test_row_count_matches_the_meta_record_count(gui):
    """Line count is NOT row count: notes is multi-line and published verbatim."""
    data, meta = gui.load_csv(CSV_PATH)
    assert len(data) == int(meta["record_count"])


def test_a_shifted_header_raises_rather_than_serving_misaligned_data(gui, tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("# meta: record_count=1\ncol_a,col_b\n1,2\n", encoding="utf-8")
    with pytest.raises(SystemExit) as ei:
        gui.load_csv(bad)
    assert "identifier" in str(ei.value)


# --------------------------------------------------------------- search

def test_facet_filter_is_exact_not_substring(gui, rows):
    res = gui.search(rows, {"identifier_type": "oui"})
    assert res
    assert {r["identifier_type"] for r in res} == {"oui"}
    # 'oui' must not drag in 'ble_uuid' or 'oui36'-style values
    assert not any(r["identifier_type"] != "oui" for r in res)


def test_text_search_spans_multiple_columns(gui, rows):
    res = gui.search(rows, {"q": "hikvision"})
    assert res
    for r in res[:25]:
        blob = " ".join(str(r.get(f) or "") for f in (
            "identifier", "manufacturer", "model", "description",
            "device_category", "identifier_type", "source_url", "notes")).lower()
        assert "hikvision" in blob


def test_confidence_floor_excludes_below(gui, rows):
    res = gui.search(rows, {"cmin": 85})
    assert res
    assert all(int(r["confidence"]) >= 85 for r in res if str(r["confidence"]).strip())


def test_manufacturer_is_substring_and_case_insensitive(gui, rows):
    res = gui.search(rows, {"manufacturer": "AXON"})
    assert res
    assert all("axon" in (r["manufacturer"] or "").lower() for r in res)


def test_filters_combine_as_AND(gui, rows):
    a = gui.search(rows, {"identifier_type": "mac_range"})
    b = gui.search(rows, {"identifier_type": "mac_range", "device_category": "cctv_camera"})
    assert 0 < len(b) < len(a)
    assert all(r["device_category"] == "cctv_camera" for r in b)


def test_empty_query_returns_everything(gui, rows):
    assert len(gui.search(rows, {})) == len(rows)


def test_facet_counts_sum_to_the_result_set(gui, rows):
    res = gui.search(rows, {"identifier_type": "oui"})
    counts = gui.facet_counts(res)
    for field, pairs in counts.items():
        assert sum(n for _v, n in pairs) == len(res), field


# --------------------------------------------------------------- rendering

def test_internal_scheme_urls_are_not_linkified(gui):
    for scheme in ("argus-internal://x/y", "manufacturer_app://com.foo@1.0",
                   "apkcombo:com.foo__1.0__apkcombo.xapk"):
        out = gui.linkify(scheme)
        assert "<a " not in out, f"{scheme} became a clickable link"
        assert "plain" in out


def test_http_urls_are_linkified_with_noopener(gui):
    out = gui.linkify("https://standards-oui.ieee.org/oui/oui.csv")
    assert out.startswith("<a ")
    assert 'rel="noopener noreferrer"' in out
    assert 'target="_blank"' in out


def test_html_is_escaped(gui):
    payload = '<script>alert(1)</script>" onmouseover="x'
    out = gui.e(payload)
    assert "<script>" not in out
    assert "&lt;script&gt;" in out
    assert '"' not in out or "&quot;" in out


def test_rendered_page_loads_no_external_assets(gui, rows):
    page = gui.render(rows[:5], len(rows), {}, gui.facet_counts(rows[:5]),
                      {"record_count": "5"}, 1, "test")
    assets = re.findall(r'<(?:script|link|img)\b[^>]*?(?:src|href)="([^"]+)"', page, re.I)
    external = [a for a in assets if a.startswith(("http://", "https://", "//"))]
    assert not external, f"external asset loads: {external}"
    assert "<script" not in page.lower(), "page must ship no JavaScript"


def test_rendered_page_escapes_a_hostile_row(gui):
    hostile = {f: "" for f in gui.FIELDS}
    hostile.update({"identifier": '<img src=x onerror=alert(1)>', "confidence": "85",
                    "notes": '</td></tr><script>alert(2)</script>',
                    "source_url": "javascript:alert(3)"})
    page = gui.render([hostile], 1, {}, gui.facet_counts([hostile]),
                      {"record_count": "1"}, 1, "test")
    assert "<img src=x" not in page
    assert "<script>alert(2)</script>" not in page
    assert 'href="javascript:' not in page


def test_confidence_select_keeps_the_submitted_floor(gui, rows):
    """REGRESSION: render() is passed the RAW query, which has no `cmin_raw`, so
    the select always showed "any". Re-submitting the form then silently dropped
    the floor."""
    page = gui.render(rows[:3], len(rows), {"cmin": "85"}, gui.facet_counts(rows[:3]),
                      {"record_count": "3"}, 1, "test")
    selected = re.findall(r'<option value="([^"]*)" selected>', page)
    assert selected == ["85"], selected


def test_facet_and_pager_links_round_trip_reserved_characters(gui, rows):
    """REGRESSION: links were built with html.escape, not URL-encoding. `&` in a
    manufacturer split the query and `+` in text decoded as a space, so Next and
    every facet link dropped the filter (627 matches -> page 2 of 43,126)."""
    from html import unescape
    from urllib.parse import parse_qs, urlparse
    q = {"manufacturer": "Leggett & Platt", "q": "a+b #c=d%"}
    page = gui.render(rows[:3], 500, q, gui.facet_counts(rows[:3]),
                      {"record_count": "3"}, 1, "test")
    hrefs = [unescape(h) for h in re.findall(r'href="(\?[^"]*)"', page)]
    assert any("page=2" in h for h in hrefs), "pager link missing"
    for h in hrefs:
        got = {k: v[0] for k, v in parse_qs(urlparse(h).query).items()}
        assert got.get("manufacturer") == q["manufacturer"], (h, got)
        assert got.get("q") == q["q"], (h, got)


# --------------------------------------------------------------- server

def test_server_serves_and_filters(gui, rows):
    import threading
    from http.server import ThreadingHTTPServer
    from urllib.request import urlopen

    gui.Handler.rows = rows
    gui.Handler.meta = {"record_count": str(len(rows))}
    gui.Handler.mfr_list = ["axon"]
    srv = ThreadingHTTPServer(("127.0.0.1", 0), gui.Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        body = urlopen(f"http://127.0.0.1:{port}/").read().decode()
        assert f"{len(rows):,}" in body
        filt = urlopen(f"http://127.0.0.1:{port}/?identifier_type=oui").read().decode()
        expect = len(gui.search(rows, {"identifier_type": "oui"}))
        assert f"of {expect:,}" in filt
        api = json.loads(urlopen(f"http://127.0.0.1:{port}/api?identifier_type=oui").read())
        assert api and all(r["identifier_type"] == "oui" for r in api)
    finally:
        srv.shutdown()


def test_security_headers_present(gui, rows):
    import threading
    from http.server import ThreadingHTTPServer
    from urllib.request import urlopen

    gui.Handler.rows = rows[:10]
    gui.Handler.meta = {"record_count": "10"}
    gui.Handler.mfr_list = []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), gui.Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        h = urlopen(f"http://127.0.0.1:{port}/").headers
        assert h["X-Content-Type-Options"] == "nosniff"
        assert h["Referrer-Policy"] == "no-referrer"
        assert "default-src 'none'" in h["Content-Security-Policy"]
    finally:
        srv.shutdown()


def test_no_inline_event_handlers_because_the_csp_forbids_script(gui, rows):
    """Regression: the page shipped onchange="this.form.submit()" on the confidence
    select while the response CSP is `default-src 'none'` with no script-src. The
    handler was silently dead, so choosing a confidence floor did nothing and the
    table kept showing rows below it. Any inline handler is unreachable under this
    CSP, so none may exist."""
    page = gui.render(rows[:3], len(rows), {}, gui.facet_counts(rows[:3]),
                      {"record_count": "3"}, 1, "test")
    handlers = re.findall(r'\son[a-z]+\s*=', page, re.I)
    assert not handlers, f"inline event handlers cannot run under our CSP: {handlers}"
    assert "javascript:" not in page.lower()


def test_every_filter_control_lives_inside_the_form(gui, rows):
    """With no JS, a control outside the form can never be submitted."""
    page = gui.render(rows[:3], len(rows), {}, gui.facet_counts(rows[:3]),
                      {"record_count": "3"}, 1, "test")
    form = page[page.index("<form"):page.index("</form>")]
    for name in ("q", "manufacturer", "cmin"):
        assert f'name="{name}"' in form, f"{name} control is outside the form"


def test_layout_has_a_narrow_viewport_rule(gui, rows):
    """Regression: a fixed 260px sidebar beside the table overflowed a 390px
    viewport horizontally."""
    page = gui.render(rows[:3], len(rows), {}, gui.facet_counts(rows[:3]),
                      {"record_count": "3"}, 1, "test")
    assert "@media" in page, "no responsive rule; narrow viewports overflow"
    assert "tablewrap" in page, "table is not inside a scroll container"


# --------------------------------------------------- notes humanising

def test_split_notes_handles_all_four_shapes(gui):
    """`notes` is machine-written and published verbatim. Across the export:
    99.6% valid JSON, 132 rows carry prose AFTER the closing brace (the CP39
    shape), 43 are plain text. json.loads rejects the suffix shape outright,
    which would silently drop the structured half."""
    d, prose, failed = gui.split_notes('{"a": 1}')
    assert d == {"a": 1} and prose == "" and not failed

    d, prose, failed = gui.split_notes('{"a": 1} ratified by CEO comment 3daf49f0')
    assert d == {"a": 1}, "structured half was dropped"
    assert prose == "ratified by CEO comment 3daf49f0"
    assert not failed

    d, prose, failed = gui.split_notes("plain prose, no json at all")
    assert d is None and prose.startswith("plain") and not failed

    d, _prose, failed = gui.split_notes('{"a": 1')
    assert d is None and failed, "truncated json must be reported, not silently dropped"

    assert gui.split_notes("") == (None, "", False)


def test_fmt_value_renders_types_readably(gui):
    assert gui.fmt_value(None) == "&mdash;"
    assert gui.fmt_value([]) == "&mdash;"
    assert gui.fmt_value(True) == "yes"
    assert gui.fmt_value(False) == "no"
    assert gui.fmt_value(["a", "b"]) == "a, b"
    out = gui.fmt_value({"from": 85, "to": 95, "at_utc": "2026-05-20T00:00:00Z",
                         "rationale": "phase 5 uplift"})
    assert "85" in out and "95" in out and "2026-05-20" in out and "phase 5 uplift" in out


def test_humanize_notes_escapes_hostile_content(gui):
    """notes is verbatim machine output; it must not be able to inject markup."""
    out = gui.humanize_notes('{"vendor":"<script>alert(1)</script>",'
                             '"_raw":"<img src=x onerror=y>"}')
    assert "<script>alert" not in out
    assert "<img src=x" not in out
    assert "&lt;script&gt;" in out


def test_humanize_notes_groups_and_keeps_raw(gui):
    raw = ('{"ieee_registry":"MA-S","cp29_confidence_band":"default",'
           '"apk_sha256":"abc123","dispatch":"MAC-99-stream-1","wave":"wave_i"}')
    out = gui.humanize_notes(raw)
    assert "Attribution" in out and "Confidence" in out and "Provenance" in out
    assert "IEEE registry block" in out, "key was not translated to plain english"
    # workflow keys are present but demoted behind a disclosure
    assert "internal workflow fields" in out
    assert "raw notes" in out, "the verbatim value must stay reachable"
    assert "MA-S" in out


def test_humanize_notes_survives_every_row_in_the_export(gui, rows):
    """A renderer that throws on one row takes the whole page down."""
    bad = []
    for r in rows:
        try:
            gui.humanize_notes(r.get("notes") or "")
        except Exception as ex:          # pragma: no cover
            bad.append((r.get("identifier"), repr(ex)[:120]))
            if len(bad) > 5:
                break
    assert not bad, f"humanize_notes raised on {len(bad)} rows: {bad[:3]}"


# ------------------------------------------------- cross-model review findings
# Six defects found 2026-09-13 by an out-of-family review (GLM 5.3) framed as
# "what does this program make POSSIBLE", and each confirmed locally before
# being fixed. Every one was invisible to the author's own tests, which were
# concentrated on HTML escaping -- the class the page was already immune to.

def test_brace_inside_a_json_string_does_not_truncate_the_scan(gui):
    """The CP39 split scanned for a matching `}` without tracking string
    context, so a brace inside a string literal ended the scan early, the
    prefix failed to parse, and the whole row silently degraded to
    'unparseable notes'. The prior test only asserted it did not RAISE."""
    raw = '{"note": "ratified at 14:00} by CEO", "vendor": "Acme"} trailing prose'
    d, prose, failed = gui.split_notes(raw)
    assert d == {"note": "ratified at 14:00} by CEO", "vendor": "Acme"}
    assert prose == "trailing prose"
    assert not failed
    # escaped quotes must not fool it either
    d2, _p2, f2 = gui.split_notes(r'{"a": "he said \"}\" loudly"} tail')
    assert d2 == {"a": 'he said "}" loudly'} and not f2


def test_deeply_nested_value_does_not_raise(gui):
    """fmt_value recursed with no depth guard, OUTSIDE any try. One row with
    deep nesting raised RecursionError and took the whole page down."""
    deep = {"a": 1}
    for _ in range(2000):
        deep = {"x": deep}
    out = gui.fmt_value(deep)
    assert "nested too deeply" in out


def test_long_list_output_is_capped(gui):
    """The flat-list join was the ONE uncapped output path; every other branch
    truncated. 5000 x 400 chars rendered a ~2 MB cell from a single row."""
    out = gui.fmt_value(["A" * 400] * 5000)
    assert len(out) < 60_000, f"uncapped: {len(out):,} chars"
    assert "more" in out, "truncation must be disclosed, not silent"


def test_from_to_only_arrows_under_a_real_history_key(gui):
    """Any dict carrying from+to rendered as a provenance arrow, so a
    row-controlled {"from":"police","to":"military"} was visually identical to
    a vetted confidence_history entry. Misrepresentation needing no injection."""
    spoof = gui.fmt_value({"from": "police", "to": "military"})
    assert "&rarr;" not in spoof, "arbitrary dict still renders as provenance"
    real = gui.fmt_value(
        {"from": 85, "to": 95, "at_utc": "2026-05-20T00:00:00Z", "rationale": "uplift"},
        0, True)
    assert "&rarr;" in real, "genuine confidence_history must still render as a history line"


def test_bidi_controls_are_neutralised(gui):
    """html.escape does not touch U+202E, so a stored identifier could render
    as a DIFFERENT identifier. For an exact-identifier database that is a
    fidelity defect, not a cosmetic one."""
    out = gui.e("70:1a:d5‮vil")
    assert "‮" not in out
    assert "&lt;RLO&gt;" in out, "the control must be shown, not silently stripped"
    for cp in (0x200E, 0x200F, 0x202A, 0x202D, 0x2066, 0x2069):
        assert chr(cp) not in gui.e(f"x{chr(cp)}y")


def test_response_blocks_framing(gui, rows):
    """default-src 'none' does NOT imply frame-ancestors. Without it any site
    the user visits can iframe this local UI."""
    import threading
    from http.server import ThreadingHTTPServer
    from urllib.request import urlopen
    gui.Handler.rows = rows[:5]
    gui.Handler.meta = {"record_count": "5"}
    gui.Handler.mfr_list = []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), gui.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        h = urlopen(f"http://127.0.0.1:{srv.server_address[1]}/").headers
        assert "frame-ancestors 'none'" in h["Content-Security-Policy"]
        assert "base-uri 'none'" in h["Content-Security-Policy"]
        assert h["X-Frame-Options"] == "DENY"
    finally:
        srv.shutdown()


def test_unexpected_host_header_is_rejected(gui, rows):
    """Binding 127.0.0.1 does NOT defeat DNS rebinding. A page served from
    http://evil.example:PORT whose DNS is re-pointed at 127.0.0.1 reaches this
    server with Host: evil.example:PORT, and the browser treats script and
    response as same-origin -- so CORS never engages and /api is readable.
    Rejecting an unexpected Host is the only server-side defence.
    Identified by cross-model review 2026-09-13 (codex gpt-5.6-sol)."""
    import http.client
    import threading
    from http.server import ThreadingHTTPServer

    gui.Handler.rows = rows[:20]
    gui.Handler.meta = {"record_count": "20"}
    gui.Handler.mfr_list = []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), gui.Handler)
    port = srv.server_address[1]
    gui.Handler.allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def status(host: str | None) -> int:
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        c.putrequest("GET", "/api", skip_host=True, skip_accept_encoding=True)
        if host is not None:
            c.putheader("Host", host)
        c.endheaders()
        code = c.getresponse().status
        c.close()
        return code

    try:
        assert status(f"127.0.0.1:{port}") == 200
        assert status(f"localhost:{port}") == 200
        assert status(f"evil.example:{port}") == 421, "DNS-rebinding Host was accepted"
        assert status(None) == 421, "missing Host was accepted"
    finally:
        srv.shutdown()
