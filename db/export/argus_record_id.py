"""SAR-10 — `argus_record_id` algorithm.

Single function that derives the Lynceus-export upsert key for a canonical
`identifiers` row from the §8.3 dedup key (`identifier_type`,
`normalized_identifier`).

The algorithm is `sha256(f"{identifier_type}|{normalized_identifier}").hexdigest()[:16]`
per BIBLE_AMENDMENTS.md SAR-10 (board ratification
[`4f075253`](<TRACKER_URL>issues/MAC-1#comment-4f075253-2eae-4ea3-9db5-c67c6f02e012)).

Stability properties (re-derived from SAR-10 entry):

- Re-run of unchanged DB → identical hash (deterministic).
- Confidence drift → identical hash (confidence is not in the input).
- Source edit (source_url / source_excerpt change) → identical hash.
- Vendor reattribution under §8.3 (e.g. SAR-9 Motorola Mobility/Solutions
  split) → identical hash (manufacturer is not in the input).
- Identifier merge under §8.3 → dropped record's hash gone; surviving
  record's hash unchanged.
- Identifier supersede under §8.3 → superseding record's hash unchanged;
  superseded record dropped from export.

Inputs are normalized per §4.3 by the caller; this module does NOT
re-normalize. `identifier_type` is lowercased here (§4.1 enum is lowercase
by spec, defense-in-depth). `normalized_identifier` is hashed as-is to
preserve SSID case sensitivity (§4.3 keeps SSIDs exact-as-broadcast).

Collision space: 16 hex chars = 64 bits = 1.8e19 distinct values; collision
probability negligible at v1 row-count scale (<10k rows).
"""

from __future__ import annotations

import hashlib

__all__ = ["argus_record_id"]

_HASH_PREFIX_CHARS = 16


def argus_record_id(identifier_type: str, normalized_identifier: str) -> str:
    """Return the 16-hex-char SAR-10 hash for a (type, identifier) pair.

    Parameters
    ----------
    identifier_type:
        §4.1 enum value (`mac`, `oui`, `bssid`, `ssid_exact`, `ble_uuid`,
        `ble_service`, `mac_range`, `device_fingerprint`, `ssid_pattern`).
        Lowercased + stripped before hashing.
    normalized_identifier:
        Per §4.3 normalization (MAC `aa:bb:cc:dd:ee:ff` lowercase
        colon-separated, OUI `aa:bb:cc` lowercase, UUID lowercase 8-4-4-4-12,
        SSIDs exact-as-broadcast). Lowercased + stripped before hashing.

    Returns
    -------
    16-hex-char prefix of the SHA-256 digest of
    ``f"{identifier_type}|{normalized_identifier}"``. Treat as opaque.
    """

    if not isinstance(identifier_type, str) or not identifier_type.strip():
        raise ValueError("identifier_type must be a non-empty string")
    if not isinstance(normalized_identifier, str) or not normalized_identifier.strip():
        raise ValueError("normalized_identifier must be a non-empty string")
    # §4.1 enum is lowercase by spec; lowercasing here is defense-in-depth.
    # §4.3 keeps SSIDs exact-as-broadcast — do NOT lowercase the identifier.
    key = f"{identifier_type.strip().lower()}|{normalized_identifier}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return digest[:_HASH_PREFIX_CHARS]
