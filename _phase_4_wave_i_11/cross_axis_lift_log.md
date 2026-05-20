# §4.4 Cross-axis §8.3 lift log — MAC-190 Phase 4 Wave I.11
Captured: 2026-05-20T18:59:47.910788+00:00

## Per-candidate disposition

### Axon (mid=15)
- pair: host id=24037 type=vendor_controlled_hostname src=primary_registry conf=85
        hard id=450 type=oui src=primary_registry conf=80
- §8.3 formula: min(99, max(85, 80) + 5) = 90
- **APPLY[host]** id=24037 conf 85→90 (ceiling=95, formula=90)
- **APPLY[hard_id]** id=450 conf 80→90 (ceiling=95, formula=90)

### Honeywell (mid=211)
- pair: host id=35294 type=vendor_controlled_hostname src=manufacturer_app conf=99
        hard id=3725 type=ble_manufacturer_id src=primary_registry conf=85
- §8.3 formula: min(99, max(99, 85) + 5) = 99
- no-op[host] id=35294 current=99 capped=95 (ceiling=95)
- **APPLY[hard_id]** id=3725 conf 85→95 (ceiling=95, formula=99)

### Jacobs (mid=13)
- pair: host id=23122 type=vendor_controlled_hostname src=primary_registry conf=97
        hard id=467 type=mac_range src=primary_registry conf=85
- §8.3 formula: min(99, max(97, 85) + 5) = 99
- no-op[host] id=23122 current=97 capped=95 (ceiling=95)
- **APPLY[hard_id]** id=467 conf 85→95 (ceiling=95, formula=99)

### Harris (mid=8)
- pair: host id=28545 type=vendor_controlled_hostname_deprecated src=primary_registry conf=87
        hard id=419 type=oui src=primary_registry conf=85
- §8.3 formula: min(99, max(87, 85) + 5) = 92
- no-op[host] id=28545 current=87 capped=87 (ceiling=87)
- **APPLY[hard_id]** id=419 conf 85→92 (ceiling=95, formula=92)

### DJI (mid=22)
- pair: host id=23064 type=vendor_controlled_hostname src=manufacturer_app conf=97
        hard id=423 type=oui src=primary_registry conf=85
- §8.3 formula: min(99, max(97, 85) + 5) = 99
- no-op[host] id=23064 current=97 capped=95 (ceiling=95)
- **APPLY[hard_id]** id=423 conf 85→95 (ceiling=95, formula=99)

### Hikvision (mid=209)
- pair: host id=23068 type=vendor_controlled_hostname src=primary_registry conf=97
        hard id=23043 type=ble_service_uuid src=manufacturer_app conf=87
- §8.3 formula: min(99, max(97, 87) + 5) = 99
- no-op[host] id=23068 current=97 capped=95 (ceiling=95)
- **APPLY[hard_id]** id=23043 conf 87→95 (ceiling=95, formula=99)

### Cellebrite (mid=28)
- pair: host id=23077 type=vendor_controlled_hostname src=primary_registry conf=97
        hard id=443 type=oui src=primary_registry conf=85
- §8.3 formula: min(99, max(97, 85) + 5) = 99
- no-op[host] id=23077 current=97 capped=95 (ceiling=95)
- **APPLY[hard_id]** id=443 conf 85→95 (ceiling=95, formula=99)

### Skydio (mid=23)
- pair: host id=23152 type=vendor_controlled_hostname src=primary_registry conf=97
        hard id=446 type=oui src=primary_registry conf=85
- §8.3 formula: min(99, max(97, 85) + 5) = 99
- no-op[host] id=23152 current=97 capped=95 (ceiling=95)
- **APPLY[hard_id]** id=446 conf 85→95 (ceiling=95, formula=99)

### Genetec (mid=4)
- pair: host id=23112 type=vendor_controlled_hostname src=primary_registry conf=97
        hard id=428 type=oui src=primary_registry conf=85
- §8.3 formula: min(99, max(97, 85) + 5) = 99
- no-op[host] id=23112 current=97 capped=95 (ceiling=95)
- **APPLY[hard_id]** id=428 conf 85→95 (ceiling=95, formula=99)

### SoundThinking (mid=26)
- pair: host id=23156 type=vendor_controlled_hostname src=primary_registry conf=97
        hard id=417 type=oui src=primary_registry conf=85
- §8.3 formula: min(99, max(97, 85) + 5) = 99
- no-op[host] id=23156 current=97 capped=95 (ceiling=95)
- **APPLY[hard_id]** id=417 conf 85→95 (ceiling=95, formula=99)

### Kenwood (mid=19)
- pair: host id=32954 type=vendor_controlled_hostname_deprecated src=primary_registry conf=87
        hard id=420 type=oui src=primary_registry conf=85
- §8.3 formula: min(99, max(87, 85) + 5) = 92
- no-op[host] id=32954 current=87 capped=87 (ceiling=87)
- **APPLY[hard_id]** id=420 conf 85→92 (ceiling=95, formula=92)

### Cradlepoint (mid=20)
- pair: host id=23091 type=vendor_controlled_hostname src=primary_registry conf=97
        hard id=455 type=oui src=primary_registry conf=85
- §8.3 formula: min(99, max(97, 85) + 5) = 99
- no-op[host] id=23091 current=97 capped=95 (ceiling=95)
- **APPLY[hard_id]** id=455 conf 85→95 (ceiling=95, formula=99)

### Dahua (mid=208)
- pair: host id=27426 type=vendor_controlled_hostname_deprecated src=primary_registry conf=87
        hard id=23046 type=ble_service_uuid src=manufacturer_app conf=87
- §8.3 formula: min(99, max(87, 87) + 5) = 92
- no-op[host] id=27426 current=87 capped=87 (ceiling=87)
- **APPLY[hard_id]** id=23046 conf 87→92 (ceiling=95, formula=92)

### Parrot (mid=25)
- pair: host id=23134 type=vendor_controlled_hostname src=primary_registry conf=97
        hard id=416 type=oui src=primary_registry conf=85
- §8.3 formula: min(99, max(97, 85) + 5) = 99
- no-op[host] id=23134 current=97 capped=95 (ceiling=95)
- **APPLY[hard_id]** id=416 conf 85→95 (ceiling=95, formula=99)

### KeyW (mid=12)
- pair: host id=33064 type=vendor_controlled_hostname_deprecated src=primary_registry conf=87
        hard id=469 type=mac_range src=primary_registry conf=85
- §8.3 formula: min(99, max(87, 85) + 5) = 92
- no-op[host] id=33064 current=87 capped=87 (ceiling=87)
- **APPLY[hard_id]** id=469 conf 85→92 (ceiling=95, formula=92)

### BRINC (mid=24)
- pair: host id=26515 type=vendor_controlled_hostname_deprecated src=primary_registry conf=87
        hard id=909 type=drone_id_prefix src=crowdsourced conf=75
- §8.3 formula: min(99, max(87, 75) + 5) = 92
- **HALT-AMBIGUITY[hard_id]**: row id=909 source_type=crowdsourced; cross-band uplift ambiguity per §11 #8 + §8.2 (band-of-record cap vs §8.3 formula). Surface as Stage 2 amendment-log candidate.

### WatchGuard (mid=17)
- pair: host id=35247 type=vendor_controlled_hostname_deprecated src=primary_registry conf=87
        hard id=429 type=oui src=primary_registry conf=85
- §8.3 formula: min(99, max(87, 85) + 5) = 92
- no-op[host] id=35247 current=87 capped=87 (ceiling=87)
- **APPLY[hard_id]** id=429 conf 85→92 (ceiling=95, formula=92)

### Septier (mid=11)
- pair: host id=34729 type=vendor_controlled_hostname_deprecated src=primary_registry conf=87
        hard id=488 type=mac_range src=inferred conf=50
- §8.3 formula: min(99, max(87, 50) + 5) = 92
- **HALT-AMBIGUITY[hard_id]**: row id=488 source_type=inferred; cross-band uplift ambiguity per §11 #8 + §8.2 (band-of-record cap vs §8.3 formula). Surface as Stage 2 amendment-log candidate.

### Digital Receiver Technology (mid=10)
- **HALT-SUPERSEDED**: host_sup=35310 hard_sup=None (DRT-class)

### Avigilon (mid=6)
- pair: host id=23216 type=vendor_controlled_hostname src=manufacturer_app conf=85
        hard id=434 type=oui src=primary_registry conf=85
- §8.3 formula: min(99, max(85, 85) + 5) = 90
- **APPLY[host]** id=23216 conf 85→90 (ceiling=95, formula=90)
- **APPLY[hard_id]** id=434 conf 85→90 (ceiling=95, formula=90)

## Summary
- candidates total: 20
- candidates with ≥1 row applied: 17
- candidates halted: 3
- row UPDATEs applied: 19
- row-level no-ops (already at/above capped): 15
- halts: superseded=1, crowdsourced_ambiguity=1, inferred_ambiguity=1, unknown_ceiling=0