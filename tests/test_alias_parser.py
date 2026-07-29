"""MAC-569 / MAC-535 — canonical alias parser tests.

Covers the canonical ``db.alias_parser`` module:
  * RFC-4180-lite quote-aware splitting
  * MAC-535 §6.2 bogus-token filter (defense-in-depth)
  * Recombine-and-quote-normalize (the MAC-569 migration's transform)

All tests are pure (no DB); the apply-script tests against a throwaway
in-memory DB live alongside the apply script under
``scripts/test_mac569_alias_quote_normalize_apply.py`` (separate test
file because the apply script is invoked via subprocess).
"""

from __future__ import annotations

import pytest

from db.alias_parser import (
    CORP_SUFFIX_STOPLIST,
    FRAGMENT_SUFFIX_PATTERN,
    TRAILING_CORP_SUFFIX,
    filter_bogus_tokens,
    is_bogus_token,
    recombine_and_quote_normalize,
    split_aliases,
    standalone_corp_suffix_tokens,
)


# ── split_aliases — bare form (no quotes) ────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, []),
        ("", []),
        ("Flock", ["Flock"]),
        ("Vigilant", ["Vigilant"]),
        # Whitespace handling
        ("  whitespace pad ,  inner  ,, empty ", ["whitespace pad", "inner", "empty"]),
        # Multiple tokens
        ("Motorola Vigilant, Motorola APX, Motorola V300",
         ["Motorola Vigilant", "Motorola APX", "Motorola V300"]),
    ],
)
def test_split_aliases_bare_form(raw: str | None, expected: list[str]) -> None:
    """Bare (unquoted) input: comma is the only separator, whitespace stripped."""
    assert split_aliases(raw) == expected


# ── split_aliases — quote-aware (RFC-4180-lite) ──────────────────────────────


def test_split_aliases_quoted_value_with_embedded_comma() -> None:
    """A quoted phrase containing a comma is ONE token."""
    blob = ('Hangzhou Hikvision Digital Technology, "Hangzhou Hikvision '
            'Digital Technology Co., Ltd.",EZVIZ,HiLook')
    toks = split_aliases(blob)
    assert toks == [
        "Hangzhou Hikvision Digital Technology",
        "Hangzhou Hikvision Digital Technology Co., Ltd.",
        "EZVIZ",
        "HiLook",
    ]


def test_split_aliases_handles_trailing_and_double_commas() -> None:
    """Edge cases: trailing comma, doubled comma, leading comma, whitespace-only token."""
    toks = split_aliases("a,,b, ,c,")
    assert toks == ["a", "b", "c"]


def test_split_aliases_unterminated_quote_falls_back_to_bare_read() -> None:
    """Defensive: an unterminated quote reads the rest of the blob as one bare token.

    Canonical data never has this shape (MAC-569 migration guarantees terminated
    quotes), but the parser must not crash on partial input — it treats the rest
    of the blob as a single bare token preserving the comma literal.
    """
    toks = split_aliases('"unterminated phrase, more text,b')
    # The whole tail (including the unterminated quote's opening and the
    # comma) is preserved verbatim as one bare token.
    assert toks == ["unterminated phrase, more text,b"]


def test_split_aliases_only_quoted_phrase() -> None:
    """A single quoted phrase with no other tokens is preserved intact."""
    assert split_aliases('"Foo, Inc."') == ["Foo, Inc."]


def test_split_aliases_multiple_quoted_phrases() -> None:
    """Multiple quoted phrases separated by commas are preserved intact."""
    blob = '"Foo, Inc.","Bar LLC","Baz, Ltd."'
    assert split_aliases(blob) == ["Foo, Inc.", "Bar LLC", "Baz, Ltd."]


# ── is_bogus_token / filter_bogus_tokens (MAC-535 §6.2 layer 2/3 defense) ──


@pytest.mark.parametrize(
    "tok,bogus",
    [
        # Pure corporate-suffix fragments (case-insensitive, verbatim catalogue)
        ("Ltd.", True),
        ("ltd.", True),
        ("LTD", True),
        ("Inc.", True),
        ("inc", True),
        ("INC", True),
        ("Inc", True),
        ("LLC", True),
        ("llc", True),
        ("Co.", True),
        ("co.", True),
        ("CO", True),
        ("the", True),
        ("THE", True),
        # Real aliases must survive
        ("Flock", False),
        ("Hikvision", False),
        ("Motorola Solutions", False),
        ("Honeywell (Beijing) Technology Solutions Lab Co.,Ltd.", False),
        ("Draganfly Innovations", False),
        # Min-length floor (length < 4 → bogus)
        ("ab", True),
        ("a", True),
        ("", True),
        ("L3H", True),  # 3 chars → bogus by min-length floor
        # Length-4 non-stop-list tokens survive
        ("L3Ha", False),  # 4 chars, not on stop-list, NOT bogus
        ("Flock", False),
    ],
)
def test_is_bogus_token(tok: str, bogus: bool) -> None:
    assert is_bogus_token(tok) is bogus


def test_is_bogus_token_substring_match_survives() -> None:
    """A real alias containing the substring 'Inc' must NOT be flagged bogus
    (e.g. 'Axon Enterprise, Inc' must survive). The stop-list is exact-token,
    not substring."""
    assert not is_bogus_token("Axon Enterprise, Inc")
    assert not is_bogus_token("LTD Inc")
    assert not is_bogus_token("Reolink Digital Technology Co.")


def test_filter_bogus_tokens_drops_only_bogus() -> None:
    """filter_bogus_tokens preserves real aliases and drops MAC-535 §6.2 bogus ones."""
    toks = ["Flock", "Ltd.", "Co", "Hikvision", "THE"]
    assert filter_bogus_tokens(toks) == ["Flock", "Hikvision"]


def test_corp_suffix_stoplist_matches_cto_catalogue() -> None:
    """The stop-list is verbatim from MAC-533 §cto_ratification.md §Finding 2.

    Any future addition MUST come with a sibling amendment-log entry that
    updates (constant + catalogue + analysis doc) together — see MAC-535
    tokenization_analysis.md §2 test discipline.
    """
    expected = {"ltd", "ltd.", "inc", "inc.", "llc", "co.", "co", "the"}
    assert set(CORP_SUFFIX_STOPLIST) == expected


# ── recombine_and_quote_normalize (the MAC-569 transform) ──────────────────


@pytest.mark.parametrize(
    "raw,expected_blob,expected_phantoms",
    [
        # Empty / None
        (None, "", 0),
        ("", "", 0),
        # No phantom tokens (no commas inside any alias value) → unchanged
        ("Flock", "Flock", 0),
        ("Flock, Motorola, Vigilant", "Flock, Motorola, Vigilant", 0),
        # One comma-bearing alias: split + quote-wrap + 1 phantom recovered
        ("Hangzhou Hikvision Digital Technology Co., Ltd.,EZVIZ,HiLook",
         '"Hangzhou Hikvision Digital Technology Co., Ltd.", EZVIZ, HiLook',
         1),
        # Multiple comma-bearing aliases (Hikvision DJI shape)
        ("Da-Jiang Innovations,DJI Innovations Technology Co., Ltd.,SZ DJI BaiWang Technology Co.,Ltd,SZ DJI Osmo Technology Co.,Ltd.,SZ DJI Software Technology Co., Ltd.",
         'Da-Jiang Innovations, "DJI Innovations Technology Co., Ltd.", "SZ DJI BaiWang Technology Co., Ltd", "SZ DJI Osmo Technology Co., Ltd.", "SZ DJI Software Technology Co., Ltd."',
         4),
    ],
)
def test_recombine_and_quote_normalize(
    raw: str | None, expected_blob: str, expected_phantoms: int
) -> None:
    blob, phantoms = recombine_and_quote_normalize(raw)
    assert blob == expected_blob
    assert phantoms == expected_phantoms


def test_recombine_and_quote_normalize_is_idempotent_on_pre_quoted_input() -> None:
    """An already-normalized blob round-trips through the transform unchanged."""
    raw = '"Hangzhou Hikvision Digital Technology Co., Ltd.", EZVIZ, HiLook'
    blob, phantoms = recombine_and_quote_normalize(raw)
    assert blob == raw
    assert phantoms == 0


def test_recombine_and_quote_normalize_preserves_cross_vendor_phrases() -> None:
    """Cross-vendor compounds like 'Autel, DJI' are NOT phantom — they are
    legitimate separate aliases that happen to share a comma in the original
    record. The normalize pass preserves them as two bare tokens because
    neither contains an embedded comma after the bare-token parse."""
    raw = "Autel, DJI, Aeryon Labs, DJI"
    blob, phantoms = recombine_and_quote_normalize(raw)
    assert phantoms == 0
    assert blob == "Autel, DJI, Aeryon Labs, DJI"


def test_recombine_and_quote_normalize_merges_name_suffix_shape() -> None:
    raw = "TASER International (legacy), Axon Enterprise, Inc, AXON ENTERPRISE, INC."
    blob, phantoms = recombine_and_quote_normalize(raw)
    assert blob == 'TASER International (legacy), "Axon Enterprise, Inc", "AXON ENTERPRISE, INC."'
    assert phantoms == 2


def test_recombine_and_quote_normalize_preserves_cross_vendor_pairs_at_scale() -> None:
    raw = "Flock Safety, Motorola Solutions, Autel, DJI, Aeryon Labs, DJI, Parrot, DJI"
    blob, phantoms = recombine_and_quote_normalize(raw)
    assert blob == raw
    assert phantoms == 0


def test_standalone_suffix_check_is_independent_of_merge_context() -> None:
    adversarial = "ACME CORPORATION, INC., GLOBEX HOLDINGS, LLC, INITECH GROUP, Ltd."
    assert standalone_corp_suffix_tokens(adversarial) == ["INC.", "LLC", "Ltd."]


def test_recombine_and_quote_normalize_phantom_count_is_bounded() -> None:
    """The phantom count is bounded by the count of corporate-suffix
    fragments in the naive split. The number is small on canonical data
    (per MAC-535 §2 cataloguing; see tokenization_analysis.md)."""
    # The MC-535 catalogued phantom-token catalogue — none of these on canonical
    # data should produce a phantom count > 7 for any single manufacturer.
    blob, phantoms = recombine_and_quote_normalize(
        "Da-Jiang Innovations,"
        "DJI Innovations Technology Co., Ltd.,"
        "SZ DJI BaiWang Technology Co.,Ltd,"
        "SZ DJI Osmo Technology Co.,Ltd.,"
        "SZ DJI Software Technology Co., Ltd."
    )
    # 4 phantoms: Ltd. (×3) and Ltd (×1)
    assert phantoms == 4


# ── Pattern invariants (regression catch for catalogue drift) ──────────────


def test_fragment_suffix_pattern_catalogue_frozen() -> None:
    """The fragment-suffix catalogue is the canonical reference for the
    recombine step. Edits MUST come with a sibling amendment-log entry."""
    # The pattern matches Ltd./Inc./Corp./Co./LLC/L.P./LP/PTY/GmbH/
    # S.A./S.r.l./S.p.A./AB/AG/SA/BV/PLC/AS — verbatim from MAC-535 Finding 2
    # extended for the MAC-569 recombine step (additional regional suffixes
    # observed in the canonical blob).
    assert _matches_fragment("Ltd.")
    assert _matches_fragment("ltd.")
    assert _matches_fragment("Inc.")
    assert _matches_fragment("inc")
    assert _matches_fragment("INC")
    assert _matches_fragment("LLC")
    assert _matches_fragment("L.P.")
    assert _matches_fragment("PTY")
    assert _matches_fragment("GmbH")
    assert _matches_fragment("S.A.")
    assert _matches_fragment("S.r.l.")
    assert _matches_fragment("S.p.A.")
    assert _matches_fragment("AB")
    assert _matches_fragment("AG")
    assert _matches_fragment("SA")
    assert _matches_fragment("BV")
    assert _matches_fragment("PLC")
    assert _matches_fragment("AS")
    # Negative
    assert not _matches_fragment("Honeywell")
    assert not _matches_fragment("Hangzhou Hikvision")
    assert not _matches_fragment("Hangzhou Hikvision Digital Technology Co.")


def _matches_fragment(tok: str) -> bool:
    return bool(FRAGMENT_SUFFIX_PATTERN.match(tok.strip()))


def test_trailing_corp_suffix_pattern() -> None:
    """The trailing-suffix pattern catches the left half of a split
    comma-bearing alias. E.g. 'Hangzhou ... Digital Technology Co.' matches."""
    assert _ends_with_corp("Hangzhou Hikvision Digital Technology Co.")
    assert _ends_with_corp("Reolink Digital Technology Co.")
    assert _ends_with_corp("Motorola Solutions Canada Inc.")
    # Negative
    assert not _ends_with_corp("Hangzhou Hikvision Digital Technology")
    assert not _ends_with_corp("Flock")
    assert not _ends_with_corp("")


def _ends_with_corp(tok: str) -> bool:
    return bool(TRAILING_CORP_SUFFIX.search(tok))
