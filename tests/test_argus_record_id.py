"""SAR-10 — `argus_record_id` algorithm tests.

Five test classes per BIBLE_AMENDMENTS.md SAR-10 implementation directive:
1. Determinism
2. Stability under confidence drift (caller does not pass confidence; the
   property is structural — confidence is not in the input domain).
3. Stability under source edit (caller does not pass source_url /
   source_excerpt; structural property).
4. Stability under vendor reattribution (caller does not pass manufacturer;
   structural property).
5. Differentiation (different type or different identifier → different hash).

Plus a small collision-space sanity check informed by the SAR-10 entry's
collision-space note (16 hex chars = 64 bits ≈ 1.8e19; v1 row-count scale
is <10k so collisions are negligible).
"""

from __future__ import annotations

import hashlib

import pytest

from db.export.argus_record_id import argus_record_id


WAVE_A_TYPE = "mac"
WAVE_A_IDENTIFIER = "e4:aa:ea:80:a1:9b"
WAVE_A_EXPECTED_HASH = "eea6f74486eea9c0"


class TestDeterminism:
    """Test #1 — same input → same output, byte-identical."""

    def test_repeated_call_is_byte_identical(self) -> None:
        first = argus_record_id(WAVE_A_TYPE, WAVE_A_IDENTIFIER)
        for _ in range(10):
            assert argus_record_id(WAVE_A_TYPE, WAVE_A_IDENTIFIER) == first

    def test_wave_a_canonical_hash_matches_ceo_precomputation(self) -> None:
        # SAR-10 §-spec: sha256("mac|e4:aa:ea:80:a1:9b")[:16].
        # CEO pre-computed at MAC-48 ratify [`915fb45d`] = eea6f74486eea9c0.
        assert (
            argus_record_id(WAVE_A_TYPE, WAVE_A_IDENTIFIER)
            == WAVE_A_EXPECTED_HASH
        )

    def test_hash_matches_explicit_sha256_prefix(self) -> None:
        # Re-derive against `hashlib` directly to guard against algorithm drift
        # in the implementation file.
        explicit = hashlib.sha256(
            f"{WAVE_A_TYPE}|{WAVE_A_IDENTIFIER}".encode("utf-8")
        ).hexdigest()[:16]
        assert argus_record_id(WAVE_A_TYPE, WAVE_A_IDENTIFIER) == explicit

    def test_output_shape_is_16_hex_chars(self) -> None:
        h = argus_record_id(WAVE_A_TYPE, WAVE_A_IDENTIFIER)
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    @pytest.mark.parametrize(
        "identifier_type,identifier",
        [
            ("mac", "e4:aa:ea:80:a1:9b"),
            ("oui", "e4:aa:ea"),
            ("bssid", "00:11:22:33:44:55"),
            ("ssid_exact", "FlockSafety_Camera_42"),
            ("ble_uuid", "0000180f-0000-1000-8000-00805f9b34fb"),
            ("ble_service", "0000180f-0000-1000-8000-00805f9b34fb"),
            ("mac_range", "e4:aa:ea:80:a1"),
        ],
    )
    def test_each_supported_type_yields_stable_hash(
        self, identifier_type: str, identifier: str
    ) -> None:
        h1 = argus_record_id(identifier_type, identifier)
        h2 = argus_record_id(identifier_type, identifier)
        assert h1 == h2
        assert len(h1) == 16


class TestConfidenceDriftStability:
    """Test #2 — hash invariant across confidence band changes.

    The property is structural: `argus_record_id` does not take confidence
    as input, so the same `(type, identifier)` pair across confidence-band
    changes (50 → 65 → 70 → 90) must collapse to the same hash.
    """

    def test_confidence_drift_does_not_alter_hash(self) -> None:
        # Simulated record at conf=50 and conf=70 — both yield the same hash
        # because the algorithm hashes only (type, identifier).
        baseline = argus_record_id("mac", "e4:aa:ea:80:a1:9b")
        for confidence_value in (30, 50, 55, 65, 70, 90, 100):
            # confidence_value is unused by the algorithm; this test asserts
            # that property holds across the full §8.2 confidence band.
            assert argus_record_id("mac", "e4:aa:ea:80:a1:9b") == baseline
            _ = confidence_value  # explicit no-op to document intent

    def test_post_dedup_uplift_keeps_hash(self) -> None:
        # §8.3 dedup-uplift: confidence rises when an independent source
        # corroborates. Hash must not move.
        pre = argus_record_id("oui", "e4:aa:ea")
        post = argus_record_id("oui", "e4:aa:ea")
        assert pre == post


class TestSourceEditStability:
    """Test #3 — hash invariant across `source_url` / `source_excerpt` edits.

    Source fields are NOT in the algorithm's input domain. Same `(type,
    identifier)` across any source-fields edit must yield the same hash.
    """

    def test_source_url_change_does_not_alter_hash(self) -> None:
        # Same MAC, simulated source_url edit (e.g. canonical-URL relocation
        # of DeFlock anchor). Hash must be stable.
        baseline = argus_record_id("mac", "e4:aa:ea:80:a1:9b")
        # Repeat call to assert structural property (algorithm has no source
        # field; the test documents the §11 #7 carry-through expectation).
        assert argus_record_id("mac", "e4:aa:ea:80:a1:9b") == baseline

    def test_source_excerpt_change_does_not_alter_hash(self) -> None:
        baseline = argus_record_id("mac", "e4:aa:ea:80:a1:9b")
        # Source excerpt edits (length / wording / re-fetch diff) must not
        # propagate to the hash.
        assert argus_record_id("mac", "e4:aa:ea:80:a1:9b") == baseline


class TestVendorReattributionStability:
    """Test #4 — hash invariant under §8.3 vendor reattribution.

    SAR-9 example: a row originally attributed to Motorola Mobility gets
    reattributed to Motorola Solutions when corporate-split FP class
    surfaces. The algorithm hashes only (type, identifier); manufacturer
    is NOT in the input domain. Same hash before and after.
    """

    def test_motorola_mobility_to_solutions_keeps_hash(self) -> None:
        # The OUI itself is unchanged; only the manufacturer attribution moves.
        baseline = argus_record_id("oui", "00:9a:cd")  # illustrative OUI
        # Post-reattribution: same hash.
        assert argus_record_id("oui", "00:9a:cd") == baseline

    def test_unattributed_to_attributed_keeps_hash(self) -> None:
        # An identifier that lifts from manufacturer=NULL → manufacturer=Foo.
        baseline = argus_record_id("mac", "aa:bb:cc:dd:ee:ff")
        assert argus_record_id("mac", "aa:bb:cc:dd:ee:ff") == baseline


class TestDifferentiation:
    """Test #5 — different type OR different identifier → different hash."""

    def test_different_identifier_yields_different_hash(self) -> None:
        a = argus_record_id("mac", "e4:aa:ea:80:a1:9b")
        b = argus_record_id("mac", "e4:aa:ea:80:a1:9c")  # one bit off
        assert a != b

    def test_different_type_same_identifier_yields_different_hash(self) -> None:
        # Same string `e4:aa:ea` interpreted as `oui` vs as a `bssid` prefix
        # yields different hashes — the type is part of the §8.3 dedup key.
        a = argus_record_id("oui", "e4:aa:ea")
        b = argus_record_id("mac_range", "e4:aa:ea")
        assert a != b

    def test_oui_vs_full_mac_yields_different_hash(self) -> None:
        a = argus_record_id("oui", "e4:aa:ea")
        b = argus_record_id("mac", "e4:aa:ea:80:a1:9b")
        assert a != b

    def test_ssid_case_distinguishes_hash(self) -> None:
        # §4.3 keeps SSIDs exact-as-broadcast; case matters.
        a = argus_record_id("ssid_exact", "FlockSafety")
        b = argus_record_id("ssid_exact", "flocksafety")
        assert a != b

    def test_collision_space_sanity_for_full_v1_set(self) -> None:
        # The SAR-10 collision-space note: 16 hex chars = 64 bits ≈ 1.8e19;
        # at v1 row-count <10k, collision probability is negligible. We test
        # the optimistic property: a synthetic 1k-row set produces 1k unique
        # hashes (no collisions in the small simulated set).
        synthetic = [
            argus_record_id("mac", f"e4:aa:ea:80:a1:{i:02x}") for i in range(256)
        ]
        synthetic += [argus_record_id("oui", f"e4:aa:{i:02x}") for i in range(256)]
        synthetic += [
            argus_record_id("bssid", f"aa:bb:cc:dd:ee:{i:02x}") for i in range(256)
        ]
        synthetic += [argus_record_id("ssid_exact", f"net_{i}") for i in range(256)]
        assert len(set(synthetic)) == len(synthetic) == 1024


class TestInputValidation:
    """Defense-in-depth — empty / non-string inputs must fail loudly."""

    def test_empty_type_raises(self) -> None:
        with pytest.raises(ValueError):
            argus_record_id("", "e4:aa:ea:80:a1:9b")

    def test_empty_identifier_raises(self) -> None:
        with pytest.raises(ValueError):
            argus_record_id("mac", "")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError):
            argus_record_id("   ", "e4:aa:ea:80:a1:9b")

    def test_non_string_type_raises(self) -> None:
        with pytest.raises(ValueError):
            argus_record_id(None, "e4:aa:ea:80:a1:9b")  # type: ignore[arg-type]

    def test_non_string_identifier_raises(self) -> None:
        with pytest.raises(ValueError):
            argus_record_id("mac", 12345)  # type: ignore[arg-type]
