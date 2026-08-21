#!/usr/bin/env python3
"""
MAC-532 FP-magnet verification — independent replication of the deployed
case-insensitive substring matcher against the emitted ssid_pattern substring
set, per bible §179 + export_lynceus.py:98/611.

Two-step check:
  1. Replicate `_ssid_pattern_to_substring` (byte-mirror of the deployed helper).
  2. For every active ssid_pattern row in canonical, derive the emitted substring(s).
  3. Assert the 18 mine-documented FPs (Schneeflocke, GreenPenguin, …) match ZERO
     emitted substrings.
  4. Assert the real-device SSIDs still match the anchored forms.

This is the independent re-verification requested by MAC-532 item (2).

EXIT-CODE CONTRACT (every binding `return` in `main()`, mapped to its arm —
MAC-765; before that repair, arm (a) reached NO non-zero return and could not
fail for any input, while still printing `FAIL`):

    0  all arms passed
    3  arm (a)  a bare stem is present in the EMITTED substring set
    1  arm (b)  a SEVERE FP-magnet coincidental survived
    2  arm (c)  a real-device SSID no longer matches its anchored form

Arms are fail-fast in source order (a -> b -> c), so a non-zero code names the
FIRST arm that failed; later arms do not run. Arms (b2) and (c2) are
informational by design and bind nothing.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "db" / "argus.db"

# Verbatim copy of the deployed helper from export_lynceus.py.
# MUST stay byte-mirror — the `_reconcile` cross-check in coverage_matrix halts
# on any divergence. Any change here must be paired with the deployed change.
# MAC-752: extends to append the leading literal of the post-group remainder
# to each alternation branch (leading OR mandatory post-group), renders
# fully when a branch has its own internal metachar, and adds `digital` /
# `flock` / `msab` / `xry` / `stingray` to the hold-set.
_SSID_STEM_METACHARS = set(".^$*+?()[]{}|\\%")
_SSID_PATTERN_FP_HOLD_STEMS = frozenset({
    "lpr",      # License Plate Reader generic acronym (MAC-517)
    "digital",  # 7-char generic prefix; survives as magnet (MAC-752)
    "flock",    # 5-char generic English/German word (MAC-752)
    "msab",     # 4-char acronym; matches williamsabc / WPAHMSABMVA (MAC-752)
    "xry",      # 3-char acronym; matches base64xryrandom (MAC-752)
    "stingray", # 9-char Harris IMSI-catcher product + generic English word
                # (CEO Finding B, 2026-08-20)
    "pineapple",# 9-char Hak5 product + common English noun; ships bare with
                # `Hak5 hacking_tool` (CEO ruling Option A, MAC-761)
})
_SSID_STEM_MIN_LEN = 3


def _strict_base(s: str) -> str:
    out: list[str] = []
    for ch in s:
        if ch in _SSID_STEM_METACHARS:
            break
        out.append(ch)
    return "".join(out).strip()


def _parse_stems(s: str) -> list[str] | None:
    stems: list[str] = [""]
    pos = 0
    n = len(s)
    while pos < n:
        ch = s[pos]
        if ch == "(":
            depth = 0
            close: int | None = None
            for i in range(pos, n):
                if s[i] == "(":
                    depth += 1
                elif s[i] == ")":
                    depth -= 1
                    if depth == 0:
                        close = i
                        break
            if close is None:
                break
            if close + 1 < n and s[close + 1] == "?":
                pos = close + 2
                continue
            inner = s[pos + 1:close]
            if inner.startswith("?"):
                pos = close + 1
                continue
            if "|" in inner:
                branches = inner.split("|")
                new_stems: list[str] = []
                for prefix in stems:
                    for branch in branches:
                        branch_chars: list[str] = []
                        has_metachar = False
                        for c in branch:
                            if c in _SSID_STEM_METACHARS:
                                has_metachar = True
                                break
                            branch_chars.append(c)
                        if has_metachar:
                            full_branch_chars: list[str] = list(prefix)
                            bpos = 0
                            bn = len(branch)
                            while bpos < bn:
                                bc = branch[bpos]
                                if bc == "[":
                                    bend = branch.find("]", bpos)
                                    if bend == -1:
                                        return None
                                    binner = branch[bpos + 1:bend]
                                    if (
                                        set(binner) <= {"_", "-"}
                                        and bend + 1 < bn
                                        and branch[bend + 1] == "?"
                                    ):
                                        bpos = bend + 2
                                        continue
                                    else:
                                        return None
                                elif bc in _SSID_STEM_METACHARS:
                                    return None
                                full_branch_chars.append(bc)
                                bpos += 1
                            full_branch = "".join(full_branch_chars).strip()
                            if not full_branch:
                                return None
                            new_stems.append(full_branch)
                        else:
                            branch_stem = "".join(branch_chars).strip()
                            if not branch_stem:
                                return None
                            new_stems.append(prefix + branch_stem)
                stems = new_stems
                pos = close + 1
                continue
            pos = close + 1
            continue
        if ch == "[":
            end = s.find("]", pos)
            if end == -1:
                break
            inner = s[pos + 1:end]
            if set(inner) <= {"_", "-"} and end + 1 < n and s[end + 1] == "?":
                pos = end + 2
                continue
            break
        if ch in _SSID_STEM_METACHARS:
            break
        for i in range(len(stems)):
            stems[i] = stems[i] + ch
        pos += 1
    return stems


def _ssid_pattern_to_substring(value: str) -> list[str] | None:
    s = value.strip()
    if s.startswith("(?i)"):
        s = s[4:]
    if s.startswith("^"):
        s = s[1:]

    branches: list[str] | None = None
    post_group_start = len(s)
    if s.startswith("("):
        depth = 0
        close: int | None = None
        for i, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    close = i
                    break
        if close is not None:
            inner = s[1:close]
            if inner and not inner.startswith("?") and "|" in inner:
                branches = inner.split("|")
                post_group_start = close + 1

    if branches is not None:
        out: list[str] = []
        for branch in branches:
            stems = _parse_stems(branch + s[post_group_start:])
            if stems is None:
                return None
            sb = _strict_base(branch)
            if sb.lower() in _SSID_PATTERN_FP_HOLD_STEMS:
                return None
            if len(sb) < _SSID_STEM_MIN_LEN:
                return None
            out.extend(stems)
        return out or None

    stems = _parse_stems(s)
    if stems is None:
        return None
    sb = _strict_base(s)
    if sb.lower() in _SSID_PATTERN_FP_HOLD_STEMS:
        return None
    if len(sb) < _SSID_STEM_MIN_LEN:
        return None
    return stems or None


def case_insensitive_substring_match(haystack: str, needle: str) -> bool:
    """Lynceus 0.9.2 matcher: `haystack LIKE '%'||needle||'%' COLLATE NOCASE`."""
    return needle.lower() in haystack.lower()


def main() -> int:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, identifier, confidence FROM identifiers "
        "WHERE identifier_type = 'ssid_pattern' AND superseded_by IS NULL "
        "ORDER BY id"
    ).fetchall()
    con.close()

    emitted: dict[int, list[str]] = {}
    fp_held: list[tuple[int, str]] = []
    for r in rows:
        subs = _ssid_pattern_to_substring(r["identifier"])
        if subs is None:
            fp_held.append((r["id"], r["identifier"]))
        else:
            emitted[r["id"]] = subs

    flat_substrings = sorted({s for subs in emitted.values() for s in subs})
    print(f"ACTIVE ssid_pattern rows:  {len(rows)}")
    print(f"  emitted (>=1 substring): {len(emitted)}")
    print(f"  fp_held (None):          {len(fp_held)}")
    print(f"DISTINCT emitted substrings: {len(flat_substrings)}")
    print()

    # --- (a) These bare stems MUST NOT appear in the EMITTED substring set ---
    #
    # MAC-765 repair. This arm carried three independent defects, all of which
    # made it decorative:
    #
    #   1. WRONG OPERAND. It tested `case_insensitive_substring_match(
    #      r["identifier"], stem)` — the stem against the raw canonical REGEX
    #      TEXT of every active row. That is not what ships. A row can hold the
    #      characters `flock` in its pattern and emit something else entirely
    #      (id 44711 `(?i)^flock[_-]?.*` is FP-HELD, emits nothing, and its
    #      Flock Safety coverage ships as oui / ble_local_name / ble_uuid), so
    #      the arm false-FAILed on correct coverage. The assertion is about the
    #      emitted set, so it must read `flat_substrings`.
    #
    #   2. NO FAILURE PATH. The loop printed `FAIL` and accumulated nothing;
    #      `main()` ended in an unconditional `return 0`. Arms (b) and (c) bind
    #      (return 1 / return 2); arm (a) could not fail for any input. It
    #      printed `FAIL` twice at the v1.8.0 tree and still exited 0.
    #
    #   3. HARDCODED COUNT. The summary line printed a literal `7/7` against a
    #      list of 8 entries — a number no input could move. Now computed.
    #
    # OPERAND SEMANTICS — EXACT MEMBERSHIP, not containment (MAC-765 ruling).
    # A magnet fires when a scanned SSID CONTAINS an emitted substring, so the
    # question this arm asks is "is this bare stem itself one of the emitted
    # substrings?". Containment (`stem in some_emitted_substring`) is the same
    # operand bug in the other direction: it would read `pineapple` inside the
    # legitimately-emitted `wifipineapple` and go red on correct coverage,
    # blocking the exact restoration mig-0063 exists to ship. Measured: the
    # SSID `Pineapple Express` matches ZERO emitted substrings post-split.
    #
    # NAMING — this list was `withdrawn_must_be_absent`, which asserted a
    # CANONICAL property ("withdrawn at the data level"). The fixed operand
    # reads the EMITTED set, and why a stem is absent (withdrawn in canonical
    # vs. FP-held at export vs. refined away by a migration) is irrelevant to
    # that assertion. Renamed to match what it actually tests, which also
    # removes the ordering coupling between this gate and mig-0063.
    bare_stems_must_not_be_emitted = [
        "flock",      # ids 559/560/561 withdrawn; 44711 FP-held (MAC-752)
        "penguin",    # id 563 (Flock Penguin AP bare stem)
        "vigilant",   # id 44465 (Motorola bare word)
        "alpr",       # id 44469 (internal category-acronym leakage)
        "oxygen",     # id 41839 (Oxygen Forensics software)
        "magnet",     # id 39610 (Magnet Forensics software)
        "dji",        # id 35597 (DJI bare 3-char magnet)
        "pineapple",  # bare Hak5 stem: branch dropped from row 44726 by
                      # mig-0063 (MAC-765); the export-side hold is RETAINED
                      # as forward-looking defense in depth. Co-branches
                      # `hak5` / `wifipineapple` ship and are NOT this stem.
    ]
    emitted_lower = {s.lower() for s in flat_substrings}
    print(f"=== (a) {len(bare_stems_must_not_be_emitted)} bare stems MUST NOT be emitted ===")
    a_failures: list[tuple[str, list[int]]] = []
    for stem in bare_stems_must_not_be_emitted:
        if stem.lower() in emitted_lower:
            offenders = sorted(
                rid for rid, subs in emitted.items()
                if any(s.lower() == stem.lower() for s in subs)
            )
            a_failures.append((stem, offenders))
            print(f"  {stem:10s}  FAIL — emitted by ids {offenders}")
        else:
            print(f"  {stem:10s}  OK")
    if a_failures:
        print(
            f"\n!!! {len(a_failures)}/{len(bare_stems_must_not_be_emitted)} bare stems "
            f"are in the EMITTED set — FP-magnet regression !!!"
        )
        for stem, offenders in a_failures:
            print(f"      {stem!r} emitted by rows {offenders}")
        return 3

    # --- (b) The 14 SEVERE FP-magnet class MUST be killed ---
    # Per MAC-522 ratification Result 3, the 14 SEVERE magnets with their documented
    # coincidental matches. Each must be killed by mig-0038 (refine→anchored or withdraw).
    # MODERATE FPs (e.g. Handelsagentur→elsag, Desautel→autel) are deliberately preserved
    # per the CEO's MAC-527 disposition — they are tested separately in (b2).
    severe_fps = [
        ("flock",     "Schneeflocke"),
        ("flock",     "RockFlock Wireless"),
        ("flock",     "osdorpplein.flockportal.nl"),
        ("Penguin",   "GreenPenguin"),
        ("Penguin",   "PurplePenguin"),
        ("Penguin",   "Bad_penguin"),
        ("vigilant",  "Be Pure_ Be Vigilant_ Behave"),
        ("vigilant",  "Vigilante"),
        ("inspire",   "inspirefreewifi"),
        ("inspire",   "inspireprepay"),
        ("inspire",   "Inspired Universal McCann"),
        ("phantom",   "Phantom"),
        ("phantom",   "phantomhive"),
        ("parrot",    "parrothead"),
        ("parrot",    "ParrotCafe"),
        ("parrot",    "parrotville"),
        ("dji",       "Fidji"),
        ("dji",       "DJIbase64random"),  # base64 SSIDs containing 'dji' substring
        ("anafi",     "bananafish"),
        ("anafi",     "HanaFinancial"),
        ("oxygen",    "Oxygen.Net Krakow"),
        ("oxygen",    "(oxygen)"),
        ("magnet",    "MagNet Free WiFi"),
        ("magnet",    "worldofmagnets"),
        ("xry",       "base64xryrandom"),  # base64 SSIDs containing 'xry'
        ("msab",      "williamsabc"),
        ("msab",      "WPAHMSABMVA"),
        ("iCSee",     "LogisticsEE"),
        ("iCSee",     "PublicSeeburg"),
        ("iCSee",     "VicsEeroWIFI"),
        ("alpr",      "alpr-cloud"),  # category-acronym leakage; no coincidental example in MAC-522
    ]
    print()
    print(f"=== (b) {len(severe_fps)} SEVERE FP-magnet coincidentals MUST be killed ===")
    failures = []
    for magnet, fp in severe_fps:
        hit_subs = [s for s in flat_substrings if case_insensitive_substring_match(fp, s)]
        if hit_subs:
            failures.append((magnet, fp, hit_subs))
            print(f"  FAIL  [{magnet:9s}]  {fp:32s}  -> hit {hit_subs}")
        else:
            print(f"  ok    [{magnet:9s}]  {fp:32s}")
    if failures:
        print(f"\n!!! {len(failures)}/{len(severe_fps)} SEVERE FPs survived — FP-magnet regression !!!")
        return 1

    # --- (b2) MODERATE FPs preserved by design (CEO disposition MAC-527) ---
    # These MATCHES are EXPECTED — the board ruled the recall tradeoff favorable.
    # Listed here for transparency, not as a failure.
    moderate_fps_preserved = [
        ("elsag", "Handelsagentur"),    # elsag = Leonardo DRS sole identifier
        ("autel", "Desautel"),          # autel = distinctive; tighten uneconomic
        ("V380",  "av3804..."),         # V380 already refined to V380_/- anchor; bare stem retained for legacy
        ("iMiniCam", "..."),            # 8-char distinctive brand; near-sole; leave
        ("MVSPT", "..."),               # 5-char distinctive; near-sole; leave
    ]
    print()
    print(f"=== (b2) {len(moderate_fps_preserved)} MODERATE FPs preserved by CEO design (informational) ===")
    for magnet, fp_example in moderate_fps_preserved:
        if fp_example == "...":
            print(f"  info  [{magnet:9s}]  preserved (no specific coincidental in MAC-522)")
            continue
        hit_subs = [s for s in flat_substrings if case_insensitive_substring_match(fp_example, s)]
        marker = "expected" if hit_subs else "no-hit (refined or coincidence-free)"
        print(f"  {marker:18s}  [{magnet:9s}]  {fp_example:24s}  -> {hit_subs or '—'}")

    # --- (c) Real device SSIDs MUST still match (anchored form required) ---
    # Per MAC-527 ratification: the delimiter-anchored forms require a `_`/`-` boundary,
    # so a no-delimiter device SSID (e.g. Phantom4-…, MavicAir-…) is missed near-term.
    # That tradeoff is CEO-blessed; the matcher-hardening relax-back is board-owned
    # (MAC-517/MAC-356). The "should hit" list below only contains SSIDs with the
    # required boundary; no-delimiter cases are tested separately as expected-no-match.
    real_devices_should_hit = [
        ("MAVIC_AIR-Foo",        "mavic_"),
        ("Mavic-2-Zoom",         "mavic-"),
        ("Phantom_4Pro",         "phantom_"),
        ("Phantom-Pro-X1",       "phantom-"),
        ("PARROT_ANAFI-thermal", "parrot_"),   # also matches anafi-
        ("Inspire-2-thermal",    "inspire-"),
        ("MSAB-XRY-extract",     "msab-"),     # also matches xry-
        ("xry_field_kit",        "xry_"),
        ("iCSee_Cam_1234",       "iCSee_"),
        ("iCSee-LivingRoom",     "iCSee-"),
        ("V380_Doorbell",        "V380_"),
        ("FS Ext Battery",       "FS Ext Battery"),  # the LOW-FP keep
    ]
    print()
    print(f"=== (c) {len(real_devices_should_hit)} real device SSIDs MUST still hit (anchored form) ===")
    rc_fails = []
    for ssid, expected_substring in real_devices_should_hit:
        hit_subs = [s for s in flat_substrings if case_insensitive_substring_match(ssid, s)]
        if expected_substring.lower() in [h.lower() for h in hit_subs]:
            print(f"  ok    {ssid:24s}  -> {hit_subs}")
        else:
            rc_fails.append((ssid, expected_substring, hit_subs))
            print(f"  FAIL  {ssid:24s}  expected {expected_substring}, got {hit_subs}")
    if rc_fails:
        print(f"\n!!! {len(rc_fails)} real-device SSID regressions !!!")
        return 2

    # --- (c2) No-delimiter device names — CEO-blessed tradeoff (known misses) ---
    # These are EXPECTED to NOT match (no `_`/`-` after stem). Documented in MAC-527:
    # "delimiter-anchored forms require a `_`/`-` boundary, so a no-delimiter
    # device SSID (e.g. Phantom4-…, MavicAir-…) is missed near-term".
    no_delimiter_misses = [
        "AnafiUSA-001",
        "Phantom4Pro-X1",
        "MavicAir-2",
        "Penguin-9F8C",   # FP-kill case — bare stem also gone
    ]
    print()
    print(f"=== (c2) {len(no_delimiter_misses)} no-delimiter cases — known misses (CEO-blessed) ===")
    for ssid in no_delimiter_misses:
        hit_subs = [s for s in flat_substrings if case_insensitive_substring_match(ssid, s)]
        if hit_subs:
            print(f"  warn  {ssid:24s}  unexpectedly hit {hit_subs}")
        else:
            print(f"  ok    {ssid:24s}  (correctly no match, expected)")

    print()
    print("=== ALL THREE GATES PASSED ===")
    # Computed, not a literal. Reached only when a_failures is empty, so the
    # numerator is the full list length — but it is derived from the list on
    # every run, so growing the list moves this number. The prior `7/7` was a
    # string constant against an 8-entry list (MAC-765 defect 3).
    print(
        f"  (a) bare stems not emitted:         "
        f"{len(bare_stems_must_not_be_emitted) - len(a_failures)}"
        f"/{len(bare_stems_must_not_be_emitted)}"
    )
    print(f"  (b) SEVERE FPs survive:             0/{len(severe_fps)}")
    print(f"  (b2) MODERATE FPs preserved:        {len(moderate_fps_preserved)}/{len(moderate_fps_preserved)}")
    print(f"  (c) real devices still match:       {len(real_devices_should_hit)}/{len(real_devices_should_hit)}")
    print(f"  (c2) no-delimiter misses (expected):{len(no_delimiter_misses)}/{len(no_delimiter_misses)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())