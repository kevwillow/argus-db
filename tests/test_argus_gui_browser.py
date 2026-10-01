"""Browser end-to-end tests for argus_gui.py.

Marked `browser`: Playwright and a downloaded Chromium are NOT repository
dependencies, so these skip on a bare clone and are excluded from the computed
`public` tier. `ARGUS_REQUIRE_ALL=1` turns the skip into a collection failure.

WHY THESE EXIST
---------------
Every check here corresponds to a bug that shipped and that the DOM-level unit
tests could not see:

  1. The response CSP is `default-src 'none'` with no script-src, so the
     confidence select's inline `onchange="this.form.submit()"` never ran. The
     control looked fine and silently returned rows below the chosen floor.
  2. Consequence of 1: rows under the floor rendered.
  3. A fixed 260px sidebar beside the table overflowed a 390px viewport.
  4. `fieldset` carries a browser-default `min-inline-size: min-content`, which
     blocked the flex child from shrinking, so facet counts clipped -- mac_range
     rendered as "17,8". A DOM assertion on this PASSED while the pixels were
     cut, because inner_text() reads the DOM, not the render. The check here is
     geometric for that reason.
  5. Expanding a provenance row reflowed every other column.
"""
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GUI = REPO / "argus_gui.py"
CSV = REPO / "exports" / "argus_export.csv"

pytestmark = [
    pytest.mark.browser,
    pytest.mark.skipif(not GUI.exists() or not CSV.exists(),
                       reason="argus_gui.py or exports/argus_export.csv absent"),
]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, str(GUI), "--no-browser", "--port", str(port)],
        cwd=str(REPO), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):                      # wait for bind, don't sleep blind
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.4):
                break
        except OSError:
            time.sleep(0.25)
    else:                                    # pragma: no cover
        proc.terminate()
        pytest.fail("argus_gui.py did not start")
    yield base
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:        # pragma: no cover
        proc.kill()


@pytest.fixture(scope="module")
def page(server):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pg = browser.new_page(viewport={"width": 1440, "height": 950})
        pg.errors, pg.external = [], []
        pg.on("pageerror", lambda e: pg.errors.append(str(e)))
        pg.on("request", lambda r: pg.external.append(r.url)
              if not r.url.startswith(server) else None)
        yield pg
        pg.close()          # close the page before the browser, else Playwright
        browser.close()     # logs a TargetClosedError during teardown


def test_page_loads_with_full_corpus(page, server):
    page.goto(server, wait_until="networkidle")
    assert page.locator("tbody tr").count() == 50
    assert "43,126" in page.content()
    assert not page.errors, page.errors[:3]


def test_loads_no_external_resources(page, server):
    """A surveillance-detection tool must not phone out. No CDN, no fonts."""
    page.external.clear()
    page.goto(server, wait_until="networkidle")
    assert not page.external, page.external[:5]
    assert "<script" not in page.content().lower()


def test_facet_click_filters_and_toggles_off(page, server):
    page.goto(server, wait_until="networkidle")
    page.locator("aside .facet a").first.click()
    page.wait_for_load_state("networkidle")
    assert page.locator("aside .facet a.on").count() == 1
    before = page.locator(".count").inner_text()
    page.locator("aside .facet a.on").first.click()
    page.wait_for_load_state("networkidle")
    assert page.locator("aside .facet a.on").count() == 0
    assert page.locator(".count").inner_text() != before


def test_confidence_floor_actually_applies(page, server):
    """REGRESSION 1+2: the inline onchange was dead under our own CSP, so the
    floor silently did nothing. Every control must submit via the form."""
    page.goto(server, wait_until="networkidle")
    page.select_option("select[name=cmin]", "90")
    page.click("aside button")
    page.wait_for_load_state("networkidle")
    assert "cmin=90" in page.url
    below = [c for c in page.locator("td.conf").all_inner_texts()
             if c.strip().isdigit() and int(c) < 90]
    assert not below, f"rows below the chosen floor rendered: {below[:5]}"


def test_no_inline_handlers_survive_in_the_served_page(page, server):
    import re
    page.goto(server, wait_until="networkidle")
    handlers = re.findall(r"\son[a-z]+\s*=", page.content(), re.I)
    assert not handlers, f"inline handlers cannot run under our CSP: {handlers}"


def test_facet_counts_are_not_clipped(page, server):
    """REGRESSION 4: fieldset's default min-inline-size blocked flex shrink, so
    counts were cut off. GEOMETRIC, not textual -- inner_text() reads the DOM
    and passed while the pixels were clipped."""
    page.goto(server, wait_until="networkidle")
    clipped = page.evaluate(
        """() => [...document.querySelectorAll('aside .facet .n')].filter(n =>
             n.getBoundingClientRect().right >
             n.closest('aside').getBoundingClientRect().right).length""")
    assert clipped == 0, f"{clipped} facet counts clipped by the sidebar"
    texts = [t.strip() for t in page.locator("aside .facet .n").all_inner_texts()]
    assert "17,828" in texts


def test_expanding_a_row_does_not_reflow_columns(page, server):
    """REGRESSION 5: opening provenance widened its column and moved every other."""
    page.goto(server, wait_until="networkidle")
    sel = "tbody tr:first-child td:nth-child(3)"
    before = page.evaluate(f"document.querySelector('{sel}').getBoundingClientRect().width")
    page.locator("tbody tr:first-child > td > details").first.locator("> summary").click()
    page.wait_for_timeout(200)
    after = page.evaluate(f"document.querySelector('{sel}').getBoundingClientRect().width")
    assert abs(before - after) < 2, f"columns reflowed {before:.0f} -> {after:.0f}"


def test_provenance_shows_humanised_notes(page, server):
    page.goto(server, wait_until="networkidle")
    det = page.locator("tbody tr:first-child > td > details").first
    det.locator("> summary").click()
    page.wait_for_timeout(200)
    text = det.locator(".prov").first.inner_text()
    for field in ("source_type", "source_url", "excerpt", "record id"):
        assert field in text
    assert "raw notes" in text, "the verbatim value must stay reachable"


def test_no_horizontal_overflow_on_a_phone_viewport(page, server):
    """REGRESSION 3."""
    page.set_viewport_size({"width": 390, "height": 844})
    try:
        page.goto(server, wait_until="networkidle")
        overflow = page.evaluate(
            "document.documentElement.scrollWidth > document.documentElement.clientWidth")
        assert not overflow
    finally:
        page.set_viewport_size({"width": 1440, "height": 950})


def test_internal_scheme_urls_are_never_links(page, server):
    page.goto(f"{server}/?q=argus-internal", wait_until="networkidle")
    assert page.locator('a[href^="argus-internal"]').count() == 0
    assert page.locator('a[href^="javascript:"]').count() == 0


def test_empty_state_and_pagination(page, server):
    page.goto(f"{server}/?q=zzzznotarealthingzzzz", wait_until="networkidle")
    assert page.locator(".empty").count() == 1
    page.goto(server, wait_until="networkidle")
    page.locator(".pager a").last.click()
    page.wait_for_load_state("networkidle")
    assert "page=2" in page.url
    assert page.locator("tbody tr").count() > 0


def test_confidence_floor_survives_a_second_search(page, server):
    """REGRESSION: the select re-rendered as "any", so typing new text and
    pressing Search silently dropped the floor."""
    page.goto(f"{server}/?cmin=85", wait_until="networkidle")
    assert page.locator("select[name=cmin]").input_value() == "85"
    page.fill("input[name=q]", "axon")
    page.click("aside button")
    page.wait_for_load_state("networkidle")
    assert "cmin=85" in page.url
    below = [c for c in page.locator("td.conf").all_inner_texts()
             if c.strip().isdigit() and int(c) < 85]
    assert not below, f"floor dropped on re-search: {below[:5]}"


def test_next_page_keeps_a_filter_containing_ampersand(page, server):
    """REGRESSION: `&` was html-escaped, not URL-encoded, so Next went from
    627 matches to page 2 of the whole corpus."""
    page.goto(f"{server}/?manufacturer=%26", wait_until="networkidle")
    count = page.locator(".count").inner_text().split(" of ")[1]
    page.locator(".pager a").last.click()
    page.wait_for_load_state("networkidle")
    assert "page=2" in page.url
    assert page.locator(".count").inner_text().split(" of ")[1] == count
    assert page.locator("input[name=manufacturer]").input_value() == "&"
