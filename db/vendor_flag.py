"""Anchored derivation of ``identifiers.notes.surveillance_vendor_flag`` — MAC-691.

Why this module exists
----------------------
``notes.surveillance_vendor_flag`` claims *"this row's manufacturer IS surveillance
vendor V"*. It was populated by a bare containment test (``V in manufacturer``) and
that test is not an identity test. Measured over the **full** flagged set on
canonical (103 rows carrying a non-NULL flag), the bare-containment basis fails on
the majority — ``Ring`` fires on ``KOZO KEIKAKU ENGINEERING``, ``ENGINEERING``,
``HEARING``, ``SPRING`` and ``BOEHRINGER``; ``Axon`` on ``MAXON INDUSTRIES`` and
``Saxonar``; ``Tile`` on ``NINGBO FOTILE KITCHENWARE``; ``DJI`` on
``Avedis Zildjian``; ``Nest`` on ``Nestlé``.

This is the **fourth** call site of the MAC-542 defect class. ``db/entity_boundary.py``
was created (MAC-585) precisely so there would be exactly one implementation of the
predicate; this column never called it. The correction therefore lives here, in code,
next to the matcher it governs — a rule that lives only in a migration recurs the next
time the column is written.

The predicate
-------------
A flag ``V`` HOLDS on a row iff some **surface form** of ``V`` entity-boundary-matches
the row's own ``manufacturer`` — uppercase, split on runs of non-alphanumerics, needle
required as a *contiguous whole-token run* in the haystack
(``db.entity_boundary.boundary_match``). Bare containment is never sufficient.

Two arms, reported separately so a keeper's basis is auditable:

``canonical``  the bare vendor string boundary-matches ``manufacturer``.
``alias``      a *safe* ``manufacturers.aliases`` surface form does.

Alias safety — why the alias arm is guarded, not raw
----------------------------------------------------
``manufacturers.aliases`` is a known-contaminated corpus. ``db/matching_policy.py``
records the measurement verbatim for ``DJI``: *"alias blob is contaminated with
co-mentions: 31 of 48 parsed aliases are short bare tokens including Autel, Axon,
Parrot, Yuneec, BRINC, 3DR"*. Expanding ``DJI`` to those forms would let a row whose
manufacturer is ``Autel Robotics`` keep a ``DJI`` flag — boundary-valid and identity-
wrong, which is the same defect one layer up. So the alias arm drops:

1. every vendor named in ``matching_policy.DEFERRED_CANONICALS`` (alias blob measured
   UNSAFE — the ratified finding is reused, not re-derived here);
2. every alias that is itself another ``manufacturers.canonical_name`` (entity
   conflation, the MAC-608 shape);
3. MAC-535 §6.2 bogus tokens, via ``db.alias_parser.filter_bogus_tokens``.

Every drop is *returned*, never silently applied — ``SurfaceForms.dropped`` carries
the reason per form.

WHAT THIS MODULE DOES NOT DO
----------------------------
Boundary is necessary, not sufficient. Most of this column's vocabulary is short
single tokens (``Ring``, ``Nest``, ``Tile``, ``Axon``, ``AVer``, ``DJI``) and
``db/entity_boundary.py`` is explicit that those boundary-match surnames and ordinary
usage as readily as the vendor. ``residual_short_token_risk`` reports which keepers
rest on such a token so the caller can adjudicate them; substituting this module for
that adjudication reintroduces the defect.

This module also does not decide the vendor **pool**. ``pool_from_db`` reads the pool
off the column's own existing values, which is circular by construction and is stated
as such: the pool's provenance is undocumented on HEAD. Deriving *new* flags from that
pool is a data-shape decision with an owner, not a matcher concern.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from db.alias_parser import filter_bogus_tokens, split_aliases
from db.entity_boundary import boundary_match, is_short_single_token

NOTES_KEY = "surveillance_vendor_flag"
NOTES_PATH = f"$.{NOTES_KEY}"


@dataclass(frozen=True)
class SurfaceForms:
    """The admissible surface forms of one vendor, with every rejection recorded."""

    vendor: str
    canonical: str
    aliases: tuple[str, ...] = ()
    dropped: tuple[tuple[str, str], ...] = ()  # (form, reason)
    in_manufacturers: bool = False

    @property
    def all_forms(self) -> tuple[str, ...]:
        return (self.canonical,) + self.aliases


@dataclass(frozen=True)
class FlagVerdict:
    """Whether a flag holds on a row, and on which arm."""

    holds: bool
    arm: Optional[str] = None  # 'canonical' | 'alias' | None
    matched_form: Optional[str] = None
    reason: str = ""
    short_token_basis: bool = False


def _deferred_canonicals() -> dict[str, str]:
    """The ratified UNSAFE-alias-blob set. Imported lazily: ``matching_policy``
    pulls in the MAC-542 screen and is heavier than this module needs to be at
    import time, and a missing/renamed policy must fail loudly here rather than
    silently widen the alias arm."""
    from db.matching_policy import DEFERRED_CANONICALS

    return DEFERRED_CANONICALS


def surface_forms(conn: sqlite3.Connection, vendor: str) -> SurfaceForms:
    """Admissible surface forms for ``vendor``, alias arm guarded (see module doc)."""
    canonical = vendor.strip()
    dropped: list[tuple[str, str]] = []

    row = conn.execute(
        "SELECT canonical_name, aliases FROM manufacturers "
        "WHERE LOWER(canonical_name) = LOWER(?)",
        (canonical,),
    ).fetchone()
    if row is None:
        return SurfaceForms(
            vendor=vendor,
            canonical=canonical,
            dropped=(("<alias arm>", "vendor is not a manufacturers.canonical_name"),),
            in_manufacturers=False,
        )

    canonical_db = row[0] if not isinstance(row, sqlite3.Row) else row["canonical_name"]
    blob = row[1] if not isinstance(row, sqlite3.Row) else row["aliases"]

    deferred = _deferred_canonicals()
    if canonical_db in deferred:
        return SurfaceForms(
            vendor=vendor,
            canonical=canonical_db,
            dropped=(
                (
                    "<alias arm>",
                    "matching_policy.DEFERRED_CANONICALS: " + deferred[canonical_db],
                ),
            ),
            in_manufacturers=True,
        )

    others = {
        r[0].strip().lower()
        for r in conn.execute(
            "SELECT canonical_name FROM manufacturers "
            "WHERE LOWER(canonical_name) <> LOWER(?)",
            (canonical_db,),
        )
        if r[0]
    }

    kept: list[str] = []
    for alias in split_aliases(blob):
        if not filter_bogus_tokens([alias]):
            dropped.append((alias, "MAC-535 §6.2 bogus token"))
            continue
        if alias.strip().lower() in others:
            dropped.append((alias, "entity conflation: is another canonical_name"))
            continue
        kept.append(alias)

    return SurfaceForms(
        vendor=vendor,
        canonical=canonical_db,
        aliases=tuple(kept),
        dropped=tuple(dropped),
        in_manufacturers=True,
    )


def flag_holds(
    manufacturer: Optional[str], flag: object, forms: Optional[SurfaceForms] = None
) -> FlagVerdict:
    """Does ``flag`` hold on a row whose manufacturer is ``manufacturer``?

    ``forms`` is optional: without it only the ``canonical`` arm is evaluated, which
    is the strictly conservative reading and is what the acceptance property requires.
    """
    if not isinstance(flag, str) or not flag.strip():
        return FlagVerdict(False, reason=f"flag is not a vendor name: {flag!r}")
    if not manufacturer or not manufacturer.strip():
        return FlagVerdict(False, reason="row carries no manufacturer to anchor against")

    vendor = flag.strip()
    if boundary_match(vendor, manufacturer):
        return FlagVerdict(
            True,
            arm="canonical",
            matched_form=vendor,
            reason="canonical name boundary-matches manufacturer",
            short_token_basis=is_short_single_token(vendor),
        )

    if forms is not None:
        for alias in forms.aliases:
            if boundary_match(alias, manufacturer):
                return FlagVerdict(
                    True,
                    arm="alias",
                    matched_form=alias,
                    reason="ratified alias boundary-matches manufacturer",
                    short_token_basis=is_short_single_token(alias),
                )

    return FlagVerdict(
        False,
        reason="no surface form boundary-matches manufacturer; the existing flag "
        "rests on bare containment",
    )


def pool_from_db(conn: sqlite3.Connection) -> list[str]:
    """Distinct non-NULL string flags currently on the column.

    Circular by construction — see the module docstring. Provided so a caller can
    measure the gain arm without hardcoding a vocabulary that has no ratified source.
    """
    return sorted(
        {
            r[0].strip()
            for r in conn.execute(
                "SELECT DISTINCT json_extract(notes, ?) FROM identifiers "
                "WHERE notes IS NOT NULL AND json_valid(notes) "
                "AND json_extract(notes, ?) IS NOT NULL",
                (NOTES_PATH, NOTES_PATH),
            )
            if isinstance(r[0], str) and r[0].strip()
        }
    )


@dataclass
class SweepResult:
    """Full-set re-derivation, reported as a DELTA (never a pinned absolute total)."""

    n_evaluated: int = 0
    kept: list[dict] = field(default_factory=list)
    lost: list[dict] = field(default_factory=list)

    @property
    def delta_lose(self) -> int:
        return len(self.lost)

    @property
    def delta_keep(self) -> int:
        return len(self.kept)

    def residual_short_token_risk(self) -> list[dict]:
        """Keepers whose basis is a short single token — boundary-valid, still
        needing MAC-542 §5 adjudication before they can be treated as identity."""
        return [k for k in self.kept if k["short_token_basis"]]


def sweep_existing_flags(conn: sqlite3.Connection, use_alias_arm: bool = True) -> SweepResult:
    """Re-derive every existing non-NULL flag. Sweeps the FULL set, never a sample."""
    rows = conn.execute(
        "SELECT id, manufacturer, device_category, identifier_type, superseded_by, "
        "       json_extract(notes, ?) AS flag "
        "FROM identifiers "
        "WHERE notes IS NOT NULL AND json_valid(notes) "
        "  AND json_extract(notes, ?) IS NOT NULL "
        "ORDER BY id",
        (NOTES_PATH, NOTES_PATH),
    ).fetchall()

    cache: dict[str, SurfaceForms] = {}
    out = SweepResult(n_evaluated=len(rows))
    for r in rows:
        rid, mfr, cat, itype, superseded, flag = r[0], r[1], r[2], r[3], r[4], r[5]
        forms = None
        if use_alias_arm and isinstance(flag, str) and flag.strip():
            key = flag.strip()
            if key not in cache:
                cache[key] = surface_forms(conn, key)
            forms = cache[key]
        v = flag_holds(mfr, flag, forms)
        rec = {
            "id": rid,
            "flag": flag,
            "manufacturer": mfr,
            "device_category": cat,
            "identifier_type": itype,
            "active": superseded is None,
            "arm": v.arm,
            "matched_form": v.matched_form,
            "reason": v.reason,
            "short_token_basis": v.short_token_basis,
        }
        (out.kept if v.holds else out.lost).append(rec)
    return out
