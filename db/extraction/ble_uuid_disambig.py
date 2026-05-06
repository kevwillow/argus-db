"""BLE UUID disambig — URL-context exclusion + protocol-context inclusion.

Surface: Ratification 2 from MAC-23 close + MAC-25 dispatch §11. Wave-A
Step-1.5b surfaced 8 ble_uuid_anchored regex hits (6 unique) — every one
was a false positive from one of these classes:
    1. GitBook social-preview URL  (https://...gitbook.io/.../assets/<uuid>)
    2. GitHub repo-asset URL       (.../assets/<uuid>?token=...)
    3. Firebase storage URL        (https://firebasestorage.googleapis.com/...)
    4. Scarf.sh tracking pixel     (https://static.scarf.sh/a.png?x-pxid=<uuid>)
    5. Microsoft Graph tenant ID   (graph.microsoft.com/.../<tenant-uuid>)

The gate is two-pass:
    Pass A — **EXCLUDE** if the ±50ch window before the UUID match contains
             any of the URL-context tokens (`://`, `assets/`, `?token=`,
             `gitbook.io`, `scarf.sh`, `firebasestorage`, `graph.microsoft`).
    Pass B — **REQUIRE** at least one BLE-protocol token within ±50ch:
             `BLE`, `Bluetooth`, `service UUID`, `characteristic UUID`,
             `GATT`, `advertised services`.

Both passes must succeed. A hit that passes A but fails B → drop with
reason `no_ble_protocol_anchor`. A hit that fails A → drop with reason
`url_context_<token>`.

Phase-5 reuse: every future regex pass that yields ble_uuid candidates
flows through `validate_ble_uuid_match()`.

§7.3 / §11 #1: a regex hit is a candidate, NOT an extracted record. This
gate moves the line between "candidate" and "stageable hit".
"""
from __future__ import annotations

import re
from typing import Iterable

CONTEXT_WINDOW_CHARS = 50  # ±50ch per MAC-23 ratification 2

# Pass-A excluders. Case-insensitive substring tests against pre-context.
URL_CONTEXT_EXCLUDERS = (
    "://",
    "/assets/",
    "?token=",
    "gitbook.io",
    "scarf.sh",
    "firebasestorage",
    "graph.microsoft",
    "googleusercontent",
    "githubusercontent.com/repos/",  # GH asset CDN
    "x-pxid=",                       # scarf.sh tracking pixel param
)

# Pass-B includers. Case-insensitive substring tests against ±50 window.
BLE_PROTOCOL_INCLUDERS = (
    "ble",
    "bluetooth",
    "service uuid",
    "service-uuid",
    "characteristic uuid",
    "characteristic-uuid",
    "gatt",
    "advertised services",
    "advertised service",
    "bt-le",
    "low energy",
    "gattservice",   # iOS CoreBluetooth class shape
    "cbuuid",        # iOS CoreBluetooth class shape
    "uuidservice",   # Android API shape
)


def _pre_context(text: str, match_start: int) -> str:
    return text[max(0, match_start - CONTEXT_WINDOW_CHARS):match_start].lower()


def _full_window(text: str, match_start: int, match_end: int) -> str:
    win_start = max(0, match_start - CONTEXT_WINDOW_CHARS)
    win_end = min(len(text), match_end + CONTEXT_WINDOW_CHARS)
    return text[win_start:win_end].lower()


def has_url_context(pre_context: str) -> tuple[bool, str]:
    for tok in URL_CONTEXT_EXCLUDERS:
        if tok in pre_context:
            return True, tok
    return False, ""


def has_ble_protocol_context(window: str) -> tuple[bool, str]:
    for tok in BLE_PROTOCOL_INCLUDERS:
        if tok in window:
            return True, tok
    return False, ""


def validate_ble_uuid_match(
    matched_uuid: str,
    *,
    text: str,
    match_start: int,
    match_end: int,
) -> tuple[bool, str]:
    """Return (is_valid, reason).

    is_valid=True  → passes both URL-context exclusion and protocol-context
                     inclusion. Safe to stage as a candidate.
    is_valid=False → reject. `reason` names the gate that fired.
    """
    if not matched_uuid:
        return False, "empty"

    pre = _pre_context(text, match_start)
    excluded, tok = has_url_context(pre)
    if excluded:
        return False, f"url_context_excluder:{tok}"

    window = _full_window(text, match_start, match_end)
    included, tok = has_ble_protocol_context(window)
    if not included:
        return False, "no_ble_protocol_anchor"

    return True, f"ok:protocol={tok}"


def filter_ble_uuid_hits(
    hits: Iterable[tuple[str, int, int]],
    *,
    text: str,
) -> tuple[list[tuple[str, int, int]], list[tuple[str, str]]]:
    """Bulk-filter helper. hits = [(uuid, start, end), ...].

    Returns (kept, dropped_with_reason).
    """
    kept: list[tuple[str, int, int]] = []
    dropped: list[tuple[str, str]] = []
    for uuid, s, e in hits:
        ok, reason = validate_ble_uuid_match(uuid, text=text, match_start=s, match_end=e)
        if ok:
            kept.append((uuid, s, e))
        else:
            dropped.append((uuid, reason))
    return kept, dropped


# ─── Smoke tests (run via `python -m db.extraction.ble_uuid_disambig`) ─


def _self_test() -> None:
    UUID_RE = re.compile(
        r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
    )
    # Pos cases (real BLE UUIDs in protocol context):
    pos_texts = [
        "The BLE service UUID is 2edd98e8-ffbc-4563-ac18-195382de3bce, exposed as a custom characteristic.",
        "GATT advertised service: 31ffe27e-667c-48ff-8a14-8029d44dfb66",
        "Bluetooth peripheral exposes the 382e30a0-10c0-4ab0-88b4-db27e9331a23 characteristic UUID for telemetry.",
    ]
    # Neg cases: surfaced FP-class from Step-1.5b
    neg_texts = [
        # GitBook asset URL (case 1)
        "See https://static.gitbook.io/static/assets/2edd98e8-ffbc-4563-ac18-195382de3bce.png for diagram.",
        # GH asset with token (case 2)
        "Image at https://user-images.githubusercontent.com/repos/foo/assets/31ffe27e-667c-48ff-8a14-8029d44dfb66?token=ABC123",
        # Firebase storage (case 3)
        "Cached at https://firebasestorage.googleapis.com/v0/b/proj.appspot.com/o/382e30a0-10c0-4ab0-88b4-db27e9331a23",
        # Scarf.sh pixel (case 4)
        "<img src=\"https://static.scarf.sh/a.png?x-pxid=6f2a02e9-1e43-4820-bad1-905631856dc2\"/>",
        # MS Graph tenant (case 5)
        "Authenticate via https://graph.microsoft.com/v1.0/tenants/b660370d-bc6e-4410-b8e4-0f8d48daffaf/users",
        # No-context UUID (no protocol anchor in window):
        "Random UUID d3590ed6-52b3-4102-aeff-aad2292ab01c assigned at startup.",
    ]
    fails = 0
    print("--- POS cases (expect kept) ---")
    for t in pos_texts:
        m = UUID_RE.search(t)
        assert m, f"regex failed on: {t}"
        ok, reason = validate_ble_uuid_match(m.group(0), text=t, match_start=m.start(), match_end=m.end())
        status = "PASS" if ok else "FAIL"
        if not ok:
            fails += 1
        print(f"  {status:4s} {m.group(0)}  -> {reason}")
    print("--- NEG cases (expect dropped) ---")
    for t in neg_texts:
        m = UUID_RE.search(t)
        assert m, f"regex failed on: {t}"
        ok, reason = validate_ble_uuid_match(m.group(0), text=t, match_start=m.start(), match_end=m.end())
        status = "PASS" if not ok else "FAIL"
        if ok:
            fails += 1
        print(f"  {status:4s} {m.group(0)}  -> {reason}")
    n = len(pos_texts) + len(neg_texts)
    print(f"--- {n - fails}/{n} pass ---")
    raise SystemExit(0 if fails == 0 else 1)


if __name__ == "__main__":
    _self_test()
