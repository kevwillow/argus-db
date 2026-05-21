# §5.2 Alias enrichment log — MAC-191 Phase 5
Captured: 2026-05-20T19:23:10.715029+00:00

## Pipeline counts
  total plan proposals: 304
  high-confidence + PROMOTE: 238
  §5.4 DEFER (skipped): 66

## id=1 "Flock Safety"
  current_aliases (n=1): ['Flock']
  - SKIP-IDENTITY-CANONICAL: alias='Flock Safety' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='Flock Safety Inc' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 90}
  - SKIP-DUPLICATE-CSV: alias='Flock' already in aliases (axis=deployment_observations_variants tier=2)
  - APPLY: alias='Vigilant Solutions, Flock Safety' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 5}
  - APPLY: alias='Motorola Solutions, Flock Safety' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 4}
  - APPLY: alias='Axon, Flock Safety' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 3}
  - APPLY: alias='Flock Safety, Selex' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 3}
  - SKIP-DUPLICATE-CSV: alias='flock' already in aliases (axis=deployment_observations_variants tier=2)
  - APPLY: alias='American Traffic Solutions, Flock Safety' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='Axon, Flock Safety, Platescan' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='FLOCK SAFETY' matches canonical_name (axis=deployment_observations_variants tier=1)
  - SKIP-IDENTITY-CANONICAL: alias='FLock Safety' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias="Flock Safety's" axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 1}
  - APPLY: alias='Flock Safety, Dura Tech' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 1}
  - APPLY: alias='Flock Safety, Ubicquia Inc.' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 1}
  - APPLY: alias='Flock Safety, Vigilant Solutions, Obsidian Integration' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 1}
  - APPLY: alias='Flock Safety;Motorola Solutions' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 1}
  - APPLY: alias='Fotokite, Flock Safety' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='Flock Group Inc.' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 490} [conditional-PROMOTE]
  - APPLY: alias='Flock Surveillance' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 3} [conditional-PROMOTE]
  - APPLY: alias='Flock Safetu' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 1} [conditional-PROMOTE]
  - APPLY: alias='Flock Saftey' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 1} [conditional-PROMOTE]
## id=2 "Vigilant Solutions"
  current_aliases (n=1): ['Vigilant']
  - SKIP-IDENTITY-CANONICAL: alias='Vigilant Solutions' matches canonical_name (axis=deployment_observations_variants tier=1)
  - SKIP-DUPLICATE-CSV: alias='Vigilant' already in aliases (axis=deployment_observations_variants tier=2)
## id=3 "Motorola Solutions"
  current_aliases (n=4): ['Motorola Vigilant', 'Motorola APX', 'Motorola V300', 'Motorola V500']
  - APPLY: alias='Motorola Solutions Canada Inc.' axis=fcc_grantees tier=3 ev={"grantee_name": "Motorola Solutions Canada Inc.", "sample_grantee_code": "JAA", "fcc_row_count": 1}
  - APPLY: alias='Motorola Solutions Germany GmbH' axis=fcc_grantees tier=3 ev={"grantee_name": "Motorola Solutions Germany GmbH", "sample_grantee_code": "OSA", "fcc_row_count": 1}
  - APPLY: alias='MOTOROLA SOLUTIONS CONNECTIVITY, INC.' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "motorola solutions connectivity", "rows": 96, "total_award_usd": 10252734.38}
  - SKIP-IDENTITY-CANONICAL: alias='Motorola Solutions' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='Flock Safety, Motorola Solutions' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 10}
  - APPLY: alias='Motorola Solutions L6Q' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 4}
  - APPLY: alias='Axon, Motorola Solutions' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 2}
## id=4 "Genetec"
  current_aliases (n=0): []
  - SKIP-IDENTITY-CANONICAL: alias='Genetec' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='Flock Safety, Genetec' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
## id=5 "Rekor"
  current_aliases (n=0): []
  - APPLY: alias='REKOR RECOGNITION SYSTEMS, INC.' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "rekor recognition systems", "rows": 90, "total_award_usd": 4684979.83}
  - SKIP-IDENTITY-CANONICAL: alias='Rekor' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='Rekor Systems' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 38}
  - SKIP-IDENTITY-CANONICAL: alias='rekor' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='ELSAG, Rekor' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='Rekor Scout' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
## id=6 "Avigilon"
  current_aliases (n=0): []
  - APPLY: alias='Avigilon Corporation' axis=fcc_grantees tier=3 ev={"grantee_name": "Avigilon Corporation", "sample_grantee_code": "2ANC5", "fcc_row_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='Avigilon' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=7 "Axis Communications"
  current_aliases (n=2): ['Axis', 'Axis Communications AB']
  - SKIP-IDENTITY-CANONICAL: alias='Axis Communications' matches canonical_name (axis=deployment_observations_variants tier=1)
  - SKIP-DUPLICATE-CSV: alias='AXIS' already in aliases (axis=deployment_observations_variants tier=2)
  - SKIP-DUPLICATE-CSV: alias='Axis' already in aliases (axis=deployment_observations_variants tier=2)
## id=8 "Harris"
  current_aliases (n=1): ['Harris Corporation']
  - APPLY: alias='Harris Corporation RF Communications Division' axis=fcc_grantees tier=3 ev={"grantee_name": "Harris Corporation RF Communications Division", "sample_grantee_code": "AQZ", "fcc_row_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='harris' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='Harris Corp.' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 20} [conditional-PROMOTE]
## id=9 "L3Harris"
  current_aliases (n=1): ['L3Harris Technologies']
  - APPLY: alias='L3HARRIS TECHNOLOGIES INTEGRATED SYSTEMS L.P.' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris technologies integrated systems l p", "rows": 1897, "total_award_usd": 3841247
  - APPLY: alias='L3HARRIS GLOBAL COMMUNICATIONS, INC.' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris global communications", "rows": 639, "total_award_usd": 4856208041.14}
  - APPLY: alias='L3HARRIS NEXGEN COMMUNICATIONS LLC' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris nexgen communications", "rows": 106, "total_award_usd": 2435766463.5}
  - APPLY: alias='L3HARRIS FUZING AND ORDNANCE SYSTEMS, INC.' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris fuzing and ordnance systems", "rows": 76, "total_award_usd": 2064013059.78}
  - APPLY: alias='L3HARRIS INTERSTATE ELECTRONICS CORPORATION' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris interstate electronics", "rows": 111, "total_award_usd": 1998674599.4}
  - APPLY: alias='L3HARRIS MARITIME SERVICES INC' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris maritime services", "rows": 232, "total_award_usd": 759886995.16}
  - APPLY: alias='L3HARRIS FORCEX, INC.' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris forcex", "rows": 68, "total_award_usd": 484304265.97}
  - APPLY: alias='L3HARRIS CINCINNATI ELECTRONICS CORPORATION' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris cincinnati electronics", "rows": 108, "total_award_usd": 302737357.16}
  - APPLY: alias='L3HARRIS MUSTANG TECHNOLOGY GROUP, L.P.' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris mustang technology group l p", "rows": 51, "total_award_usd": 222375542.03}
  - APPLY: alias='L3HARRIS MARITIME POWER & ENERGY SOLUTIONS, INC' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris maritime power energy solutions", "rows": 308, "total_award_usd": 217042339.85
  - APPLY: alias='L3HARRIS UNMANNED SYSTEMS, INC' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris unmanned systems", "rows": 19, "total_award_usd": 59580988.06}
  - APPLY: alias='L3HARRIS RELEASE & INTEGRATED SOLUTIONS LTD' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris release integrated solutions", "rows": 14, "total_award_usd": 20045064.94}
  - APPLY: alias='L3HARRIS OPEN WATER POWER INC' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris open water power", "rows": 2, "total_award_usd": 3808528.61}
  - APPLY: alias='L3HARRIS KIGRE, INC' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris kigre", "rows": 2, "total_award_usd": 1452748.27}
  - APPLY: alias='L3HARRIS MICREO PTY. LIMITED' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "l3harris micreo", "rows": 1, "total_award_usd": 864638.1}
  - SKIP-IDENTITY-CANONICAL: alias='l3harris' matches canonical_name (axis=deployment_observations_variants tier=1)
  - SKIP-IDENTITY-CANONICAL: alias='L3Harris' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=10 "Digital Receiver Technology"
  current_aliases (n=3): ['DRT', 'DRTBox', 'DRT Inc.']
  - APPLY: alias='DRT STRATEGIES, INC.' axis=usaspending tier=4 ev={"vendor_canonical_normalized": "drt strategies", "rows": 85, "total_award_usd": 202152437.64}
  - APPLY: alias='TSS - DRT JOINT VENTURE, LIMITED LIABILITY CORPORATION' axis=usaspending tier=4 ev={"vendor_canonical_normalized": "tss - drt joint venture limited liability", "rows": 2, "total_award_usd": 41267042.7300
  - SKIP-IDENTITY-CANONICAL: alias='Digital Receiver Technology' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=12 "KeyW"
  current_aliases (n=1): ['KeyW Corporation']
  - APPLY: alias='The KEYW Corporation' axis=fcc_grantees tier=3 ev={"grantee_name": "The KEYW Corporation", "sample_grantee_code": "2AFYU", "fcc_row_count": 1}
  - SKIP-DUPLICATE-CSV: alias='THE KEYW CORPORATION' already in aliases (axis=usaspending tier=3)
  - APPLY: alias='KEYW CORPORATION, THE' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "keyw corporation the", "rows": 10, "total_award_usd": 10819305.23}
## id=13 "Jacobs"
  current_aliases (n=2): ['Jacobs Engineering', 'Jacobs Solutions Inc.']
  - APPLY: alias='Jacobs Chuck Bilz Company' axis=fcc_grantees tier=3 ev={"grantee_name": "Jacobs Chuck Bilz Company", "sample_grantee_code": "LI4", "fcc_row_count": 1}
  - APPLY: alias='Jacobs Electronics Inc' axis=fcc_grantees tier=3 ev={"grantee_name": "Jacobs Electronics Inc", "sample_grantee_code": "JNU", "fcc_row_count": 1}
  - APPLY: alias='Jacobs and Associates' axis=fcc_grantees tier=3 ev={"grantee_name": "Jacobs and Associates", "sample_grantee_code": "AR5", "fcc_row_count": 1}
  - APPLY: alias='JACOBS ENGINEERING GROUP INC' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "jacobs engineering group", "rows": 2535, "total_award_usd": 2051215086.77}
  - APPLY: alias='JACOBS BV A JOINT VENTURE' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "jacobs bv a joint venture", "rows": 11, "total_award_usd": 87629475.12}
  - APPLY: alias='JACOBS GOVERNMENT SERVICES CO' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "jacobs government services", "rows": 46, "total_award_usd": 62250607.83}
  - APPLY: alias='BAKER JACOBS JV' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "baker jacobs jv", "rows": 7, "total_award_usd": 37374556.47}
  - APPLY: alias='JACOBS USAE JOINT VENTURE' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "jacobs usae joint venture", "rows": 3, "total_award_usd": 7654555.0}
  - APPLY: alias='STANTEC JACOBS BUCHART HORN JOINT VENTURE' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "stantec jacobs buchart horn joint venture", "rows": 13, "total_award_usd": 6532375.74}
  - SKIP-IDENTITY-CANONICAL: alias='jacobs' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='Jacobs Technology' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 13}
  - SKIP-DUPLICATE-CSV: alias='Jacobs Engineering' already in aliases (axis=deployment_observations_variants tier=2)
## id=15 "Axon"
  current_aliases (n=1): ['TASER International (legacy)']
  - APPLY: alias='Axon Enterprise, Inc' axis=fcc_grantees tier=3 ev={"grantee_name": "Axon Enterprise, Inc", "sample_grantee_code": "X4G", "fcc_row_count": 1} [conditional-PROMOTE]
  - APPLY: alias='AXON ENTERPRISE, INC.' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "axon enterprise", "rows": 550, "total_award_usd": 389532506.56} [conditional-PROMOTE]
  - SKIP-IDENTITY-CANONICAL: alias='Axon' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='Axon Enterprise' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 62} [conditional-PROMOTE]
  - APPLY: alias='Axon Body-2' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1} [conditional-PROMOTE]
  - APPLY: alias='Axon Flex' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1} [conditional-PROMOTE]
## id=16 "Reveal"
  current_aliases (n=1): ['Reveal Media']
  - APPLY: alias='Reveal Media Limited' axis=fcc_grantees tier=3 ev={"grantee_name": "Reveal Media Limited", "sample_grantee_code": "2AL26", "fcc_row_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='Reveal' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=17 "WatchGuard"
  current_aliases (n=2): ['WatchGuard Video', 'WatchGuard Video (legacy)']
  - APPLY: alias='Enforcement Video, LLC (d.b.a. WatchGuard Video)' axis=fcc_grantees tier=3 ev={"grantee_name": "Enforcement Video, LLC (d.b.a. WatchGuard Video)", "sample_grantee_code": "YJV", "fcc_row_count": 1}
  - APPLY: alias='WatchGuard Technologies, Inc.' axis=fcc_grantees tier=3 ev={"grantee_name": "WatchGuard Technologies, Inc.", "sample_grantee_code": "Q6G", "fcc_row_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='WatchGuard' matches canonical_name (axis=deployment_observations_variants tier=1)
  - SKIP-IDENTITY-CANONICAL: alias='Watchguard' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='L3, WatchGuard' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='Motorola WatchGuard' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='watchguard' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=18 "Getac"
  current_aliases (n=1): ['Getac Technology Corporation']
  - APPLY: alias='Getac Technology Corp.' axis=fcc_grantees tier=3 ev={"grantee_name": "Getac Technology Corp.", "sample_grantee_code": "MAU", "fcc_row_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='Getac' matches canonical_name (axis=deployment_observations_variants tier=1)
  - SKIP-IDENTITY-CANONICAL: alias='getac' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=19 "Kenwood"
  current_aliases (n=0): []
  - APPLY: alias='JVC KENWOOD Corporation' axis=fcc_grantees tier=3 ev={"grantee_name": "JVC KENWOOD Corporation", "sample_grantee_code": "ASI", "fcc_row_count": 2}
  - APPLY: alias='Kenwood Communications Corporation' axis=fcc_grantees tier=3 ev={"grantee_name": "Kenwood Communications Corporation", "sample_grantee_code": "FS5", "fcc_row_count": 1}
  - APPLY: alias='Kenwood Corporation, Communication Equipment Division' axis=fcc_grantees tier=3 ev={"grantee_name": "Kenwood Corporation, Communication Equipment Division", "sample_grantee_code": "N77", "fcc_row_count":
  - APPLY: alias='Kenwood Ltd' axis=fcc_grantees tier=3 ev={"grantee_name": "Kenwood Ltd", "sample_grantee_code": "2AKUU", "fcc_row_count": 1}
  - APPLY: alias='Kenwood USA Corporation' axis=fcc_grantees tier=3 ev={"grantee_name": "Kenwood USA Corporation", "sample_grantee_code": "ALH", "fcc_row_count": 2}
## id=20 "Cradlepoint"
  current_aliases (n=2): ['Cradlepoint Inc.', 'Ericsson Cradlepoint']
  - SKIP-IDENTITY-CANONICAL: alias='cradlepoint' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=21 "Sierra Wireless"
  current_aliases (n=2): ['Sierra Wireless AirLink', 'Semtech Sierra']
  - APPLY: alias='Sierra Wireless Inc' axis=fcc_grantees tier=3 ev={"grantee_name": "Sierra Wireless Inc", "sample_grantee_code": "LL9", "fcc_row_count": 1}
  - APPLY: alias='Sierra Wireless Inc.' axis=fcc_grantees tier=3 ev={"grantee_name": "Sierra Wireless Inc.", "sample_grantee_code": "N7N", "fcc_row_count": 2}
  - APPLY: alias='SIERRA WIRELESS AMERICA, INC' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "sierra wireless america", "rows": 1, "total_award_usd": 11348725.3}
## id=22 "DJI"
  current_aliases (n=1): ['Da-Jiang Innovations']
  - APPLY: alias='DJI Innovations Technology Co., Ltd.' axis=fcc_grantees tier=3 ev={"grantee_name": "DJI Innovations Technology Co., Ltd.", "sample_grantee_code": "QT9", "fcc_row_count": 1}
  - APPLY: alias='SZ DJI BaiWang Technology Co.,Ltd' axis=fcc_grantees tier=3 ev={"grantee_name": "SZ DJI BaiWang Technology Co.,Ltd", "sample_grantee_code": "2AHAY", "fcc_row_count": 1}
  - APPLY: alias='SZ DJI Osmo Technology Co.,Ltd.' axis=fcc_grantees tier=3 ev={"grantee_name": "SZ DJI Osmo Technology Co.,Ltd.", "sample_grantee_code": "2ANDR", "fcc_row_count": 1}
  - APPLY: alias='SZ DJI Software Technology Co., Ltd.' axis=fcc_grantees tier=3 ev={"grantee_name": "SZ DJI Software Technology Co., Ltd.", "sample_grantee_code": "2AHAN", "fcc_row_count": 1}
  - APPLY: alias='SZ DJI TECHNOLOGY CO. LTD' axis=fcc_grantees tier=3 ev={"grantee_name": "SZ DJI TECHNOLOGY CO. LTD", "sample_grantee_code": "2AS9V", "fcc_row_count": 3}
  - APPLY: alias='SZ DJI TECHNOLOGY CO., LTD' axis=fcc_grantees tier=3 ev={"grantee_name": "SZ DJI TECHNOLOGY CO., LTD", "sample_grantee_code": "SS3", "fcc_row_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='DJI' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='Autel, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 14}
  - APPLY: alias='Aeryon Labs, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 2}
  - APPLY: alias='Draganfly Innovations, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 2}
  - APPLY: alias='Parrot, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 2}
  - APPLY: alias='3DR, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='AceCore, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='Autel Robotics, Brincs, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='Axon, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='BRINC, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - SKIP-DUPLICATE-CSV: alias='Brinc, DJI' already in aliases (axis=deployment_observations_variants tier=3)
  - APPLY: alias='Dronium, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='HSE, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='Inspire and DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='Lockheed Martin, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='MAVIC, Autel, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='MAXSUR, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='Nightingale Blackbird, Aardvark Tactical, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='UAV Solutions, Yuneec, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='Yuneec, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='dji' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='exH2O, DJI' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
## id=23 "Skydio"
  current_aliases (n=0): []
  - SKIP-IDENTITY-CANONICAL: alias='Skydio' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='DJI, Skydio' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 4}
  - APPLY: alias='Brinc, DJI, Skydio' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='DJI, Parrot, Skydio' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
## id=24 "BRINC"
  current_aliases (n=1): ['BRINC Drones']
  - SKIP-IDENTITY-CANONICAL: alias='Brinc' matches canonical_name (axis=deployment_observations_variants tier=1)
  - SKIP-IDENTITY-CANONICAL: alias='brinc' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='Autel Robotics, Brinc' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 2}
  - APPLY: alias='DJI, Autel Robotics, Brinc' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 2}
  - APPLY: alias='Autel, DJI, BRINC' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='BRINC' matches canonical_name (axis=deployment_observations_variants tier=1)
  - SKIP-DUPLICATE-CSV: alias='Brinc Drones' already in aliases (axis=deployment_observations_variants tier=2)
  - APPLY: alias='DJI, Brinc' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
## id=25 "Parrot"
  current_aliases (n=0): []
  - APPLY: alias='PARROT FAURECIA AUTOMOTIVE SAS' axis=fcc_grantees tier=3 ev={"grantee_name": "PARROT FAURECIA AUTOMOTIVE SAS", "sample_grantee_code": "2AGKO", "fcc_row_count": 1}
  - APPLY: alias='Parrot Faurecia Automotive S.A.S' axis=fcc_grantees tier=3 ev={"grantee_name": "Parrot Faurecia Automotive S.A.S", "sample_grantee_code": "2AT94", "fcc_row_count": 1}
  - APPLY: alias='PARROT DRONE SAS' axis=fcc_grantees tier=3 ev={"grantee_name": "PARROT DRONE SAS", "sample_grantee_code": "2AG6I", "fcc_row_count": 1} [conditional-PROMOTE]
  - SKIP-IDENTITY-CANONICAL: alias='Parrot' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=26 "SoundThinking"
  current_aliases (n=1): ['ShotSpotter']
  - SKIP-IDENTITY-CANONICAL: alias='SoundThinking' matches canonical_name (axis=deployment_observations_variants tier=1)
  - SKIP-DUPLICATE-CSV: alias='ShotSpotter' already in aliases (axis=deployment_observations_variants tier=2)
  - SKIP-DUPLICATE-CSV: alias='Shotspotter' already in aliases (axis=deployment_observations_variants tier=2)
  - SKIP-IDENTITY-CANONICAL: alias='Soundthinking' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='Shotspotter Connect' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 1}
  - APPLY: alias='SoundThinking | ShotSpotter' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='soundthinking' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=28 "Cellebrite"
  current_aliases (n=0): []
  - APPLY: alias='CELLEBRITE FEDERAL SOLUTIONS, INC.' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "cellebrite federal solutions", "rows": 11, "total_award_usd": 1436591.83}
  - SKIP-IDENTITY-CANONICAL: alias='cellebrite' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=29 "Magnet Forensics"
  current_aliases (n=2): ['Magnet', 'GrayKey (product)']
  - APPLY: alias='MAGNET FORENSICS USA INC' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "magnet forensics usa", "rows": 187, "total_award_usd": 15851461.12}
## id=30 "Berla"
  current_aliases (n=0): []
  - SKIP-IDENTITY-CANONICAL: alias='berla' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=31 "BriefCam"
  current_aliases (n=0): []
  - SKIP-IDENTITY-CANONICAL: alias='BriefCam' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='Millenium Products Inc / BriefCam Corp' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='Motorola Solutions, BriefCam' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
## id=32 "Clearview AI"
  current_aliases (n=1): ['Clearview']
  - SKIP-IDENTITY-CANONICAL: alias='Clearview AI' matches canonical_name (axis=deployment_observations_variants tier=1)
  - SKIP-DUPLICATE-CSV: alias='Clearview' already in aliases (axis=deployment_observations_variants tier=2)
## id=33 "Dedrone"
  current_aliases (n=0): []
  - APPLY: alias='Dedrone Holdings, Inc.' axis=fcc_grantees tier=3 ev={"grantee_name": "Dedrone Holdings, Inc.", "sample_grantee_code": "2AO3N", "fcc_row_count": 1}
  - APPLY: alias='DEDRONE DEFENSE LLC' axis=usaspending tier=3 ev={"vendor_canonical_normalized": "dedrone defense", "rows": 10, "total_award_usd": 1897461.0}
  - SKIP-IDENTITY-CANONICAL: alias='dedrone' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=206 "Autel Robotics"
  current_aliases (n=2): ['Autel', 'Autel Intelligent Technology Corp.']
  - APPLY: alias='Autel Corporation' axis=fcc_grantees tier=4 ev={"grantee_name": "Autel Corporation", "sample_grantee_code": "CMJ", "fcc_row_count": 1}
  - APPLY: alias='Autel Intelligent Tech. Corp., Ltd.' axis=fcc_grantees tier=4 ev={"grantee_name": "Autel Intelligent Tech. Corp., Ltd.", "sample_grantee_code": "WQ8", "fcc_row_count": 1}
  - APPLY: alias='Autel Intelligent Technology Co.,Ltd' axis=fcc_grantees tier=4 ev={"grantee_name": "Autel Intelligent Technology Co.,Ltd", "sample_grantee_code": "XPR", "fcc_row_count": 1}
  - APPLY: alias='Autel Robotics Co., Ltd.' axis=fcc_grantees tier=3 ev={"grantee_name": "Autel Robotics Co., Ltd.", "sample_grantee_code": "2AGNT", "fcc_row_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='Autel Robotics' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='DJI, Autel Robotics' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 8}
  - SKIP-DUPLICATE-CSV: alias='Autel' already in aliases (axis=deployment_observations_variants tier=2)
  - APPLY: alias='DJI, Autel' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 2}
  - APPLY: alias='Autel Robotics, DJI, Loki' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 1}
  - APPLY: alias='Brinc, Autel' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 1}
  - APPLY: alias='DJI, Autel Robotics, Brincs, Loki' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 1}
  - APPLY: alias='Sky-Hero, Autel Robotics' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - APPLY: alias='Yuneec, Autel Robotics' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
## id=208 "Dahua"
  current_aliases (n=2): ['Zhejiang Dahua Technology', 'Dahua Technology']
  - APPLY: alias='Zhejiang Dahua Technology Co. Ltd.' axis=fcc_grantees tier=3 ev={"grantee_name": "Zhejiang Dahua Technology Co. Ltd.", "sample_grantee_code": "ZTS", "fcc_row_count": 1}
  - APPLY: alias='Zhejiang Dahua Vision Technology Co., Ltd' axis=fcc_grantees tier=3 ev={"grantee_name": "Zhejiang Dahua Vision Technology Co., Ltd", "sample_grantee_code": "SVN", "fcc_row_count": 1}
  - SKIP-DUPLICATE-CSV: alias='Dahua Technology' already in aliases (axis=deployment_observations_variants tier=2)
  - SKIP-IDENTITY-CANONICAL: alias='Dahua' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=209 "Hikvision"
  current_aliases (n=3): ['Hangzhou Hikvision Digital Technology', 'HikCentral', 'HikConnect']
  - APPLY: alias='Hangzhou Hikvision Digital Technology Co., Ltd.' axis=fcc_grantees tier=3 ev={"grantee_name": "Hangzhou Hikvision Digital Technology Co., Ltd.", "sample_grantee_code": "2ADTD", "fcc_row_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='Hikvision' matches canonical_name (axis=deployment_observations_variants tier=1)
  - SKIP-IDENTITY-CANONICAL: alias='hikvision' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=210 "Verkada"
  current_aliases (n=2): ['Verkada Command', 'Verkada Inc']
  - SKIP-IDENTITY-CANONICAL: alias='Verkada' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='Verkada Inc.' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 33}
  - SKIP-IDENTITY-CANONICAL: alias='verkada' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=211 "Honeywell"
  current_aliases (n=4): ['Honeywell Pro-Watch', 'Honeywell International', 'Honeywell Building Technologies', 'Honeywell International Inc.']
  - APPLY: alias='HONEYWELL FEDERAL MANUFACTURING & TECHNOLOGY' axis=fcc_grantees tier=3 ev={"grantee_name": "HONEYWELL FEDERAL MANUFACTURING & TECHNOLOGY", "sample_grantee_code": "VGK", "fcc_row_count": 1}
  - APPLY: alias='Honeywell (Beijing) Technology Solutions Lab Co.,Ltd.' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell (Beijing) Technology Solutions Lab Co.,Ltd.", "sample_grantee_code": "2ARTN", "fcc_row_count
  - APPLY: alias='Honeywell (China) Co., LTD' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell (China) Co., LTD", "sample_grantee_code": "2ACA7", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Access Systems' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Access Systems", "sample_grantee_code": "R7W", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Analytics' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Analytics", "sample_grantee_code": "U5C", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Analytics Asia Pacific Co., Ltd.' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Analytics Asia Pacific Co., Ltd.", "sample_grantee_code": "2AISE", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Analytics Inc' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Analytics Inc", "sample_grantee_code": "2ACSZ", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Communication Networks Division' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Communication Networks Division", "sample_grantee_code": "A33", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Enraf' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Enraf", "sample_grantee_code": "LOM", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Fed' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Fed", "sample_grantee_code": "AZC", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Global Tracking Ltd' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Global Tracking Ltd", "sample_grantee_code": "2AJND", "fcc_row_count": 1}
  - APPLY: alias='Honeywell GmbH' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell GmbH", "sample_grantee_code": "2AF7K", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Hearing Technologies AS' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Hearing Technologies AS", "sample_grantee_code": "O5W", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Inc' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Inc", "sample_grantee_code": "B7F", "fcc_row_count": 6}
  - APPLY: alias='Honeywell Inc Residential Division' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Inc Residential Division", "sample_grantee_code": "EUA", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Incorporated' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Incorporated", "sample_grantee_code": "EGM", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Integrated Technology (China) Co., Ltd' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Integrated Technology (China) Co., Ltd", "sample_grantee_code": "2AVFQ", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Integrated Technology(China) Co.,LTD' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Integrated Technology(China) Co.,LTD", "sample_grantee_code": "2AJAW", "fcc_row_count": 1}
  - APPLY: alias='Honeywell International (Commerical Avionics Products)' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell International (Commerical Avionics Products)", "sample_grantee_code": "PKE", "fcc_row_count"
  - APPLY: alias='Honeywell International Inc' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell International Inc", "sample_grantee_code": "2ASE2", "fcc_row_count": 2}
  - APPLY: alias='Honeywell International Inc. (Alerton)' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell International Inc. (Alerton)", "sample_grantee_code": "2AQ7A", "fcc_row_count": 1}
  - APPLY: alias='Honeywell International Incorporated' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell International Incorporated", "sample_grantee_code": "C4P", "fcc_row_count": 1}
  - APPLY: alias='Honeywell International, Inc.' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell International, Inc.", "sample_grantee_code": "2AD9A", "fcc_row_count": 2}
  - APPLY: alias='Honeywell Keyboard Division' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Keyboard Division", "sample_grantee_code": "GJK", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Regelsysteme GmbH' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Regelsysteme GmbH", "sample_grantee_code": "2AAVN", "fcc_row_count": 1}
  - APPLY: alias='Honeywell S.r.l.' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell S.r.l.", "sample_grantee_code": "2ACDR", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Safety Products USA, Inc.' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Safety Products USA, Inc.", "sample_grantee_code": "2AJKI", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Security Sensor CoE' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Security Sensor CoE", "sample_grantee_code": "2ABC8", "fcc_row_count": 1}
  - APPLY: alias='Honeywell Sensing and Control' axis=fcc_grantees tier=3 ev={"grantee_name": "Honeywell Sensing and Control", "sample_grantee_code": "XJL", "fcc_row_count": 1}
  - APPLY: alias='Micro Switch Division of Honeywell' axis=fcc_grantees tier=3 ev={"grantee_name": "Micro Switch Division of Honeywell", "sample_grantee_code": "F6X", "fcc_row_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='honeywell' matches canonical_name (axis=deployment_observations_variants tier=1)
  - SKIP-IDENTITY-CANONICAL: alias='Honeywell' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=214 "PIPS Technology"
  current_aliases (n=4): ['PIPS Technology / Neology', 'Neology', 'AutoVu (legacy)', '3M (legacy)']
  - SKIP-IDENTITY-CANONICAL: alias='PIPS Technology' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='Neology / PIPS' axis=deployment_observations_variants tier=4 ev={"deployment_observation_count": 1}
## id=215 "Wolfcom"
  current_aliases (n=1): ['Wolfcom Enterprises']
  - SKIP-IDENTITY-CANONICAL: alias='Wolfcom' matches canonical_name (axis=deployment_observations_variants tier=1)
  - SKIP-IDENTITY-CANONICAL: alias='WOLFCOM' matches canonical_name (axis=deployment_observations_variants tier=1)
  - APPLY: alias='Motorola, Wolfcom' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
  - SKIP-IDENTITY-CANONICAL: alias='WolfCom' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=218 "Digital Ally"
  current_aliases (n=3): ['Digital Ally Inc', 'FleetVU', 'BodyVU']
  - SKIP-IDENTITY-CANONICAL: alias='Digital Ally' matches canonical_name (axis=deployment_observations_variants tier=1)
## id=219 "Aerodome"
  current_aliases (n=1): ['Aerodome DFR']
  - APPLY: alias='DJI, Flock Safety, Aerodome' axis=deployment_observations_variants tier=3 ev={"deployment_observation_count": 1}
## id=220 "Eagle Eye Networks"
  current_aliases (n=1): ['Eagle Eye']
  - APPLY: alias='Eagle Eye Networks B.V.' axis=fcc_grantees tier=3 ev={"grantee_name": "Eagle Eye Networks B.V.", "sample_grantee_code": "2AQEO", "fcc_row_count": 1}
  - APPLY: alias='Eagle Eye Sales Inc.' axis=fcc_grantees tier=4 ev={"grantee_name": "Eagle Eye Sales Inc.", "sample_grantee_code": "2AA8G", "fcc_row_count": 1}
  - SKIP-DUPLICATE-CSV: alias='Eagle Eye' already in aliases (axis=deployment_observations_variants tier=2)

## Post-state spot-check
  id=1 "Flock Safety": aliases="Flock,Flock Safety Inc,Vigilant Solutions, Flock Safety,Motorola Solutions, Flock Safety,Axon, Flock Safety,Flock Safety, Selex,American Traffic Solutions, Flock Safety,Axon, Flock Safety, Platescan,Flock Safety's,Flock Safety, Dura Tech,Flock Safety, Ubicquia Inc.,Flock Safety, Vigilant Solutions, Obsidian Integration,Flock Safety;Motorola Solutions,Fotokite, Flock Safety,Flock Group Inc.,Flock Surveillance,Flock Safetu,Flock Saftey"
  id=2 "Vigilant Solutions": aliases='Vigilant'
  id=4 "Genetec": aliases='Flock Safety, Genetec'
  id=7 "Axis Communications": aliases='Axis, Axis Communications AB'
  id=8 "Harris": aliases='Harris Corporation,Harris Corporation RF Communications Division,Harris Corp.'
  id=15 "Axon": aliases='TASER International (legacy),Axon Enterprise, Inc,AXON ENTERPRISE, INC.,Axon Enterprise,Axon Body-2,Axon Flex'
  id=25 "Parrot": aliases='PARROT FAURECIA AUTOMOTIVE SAS,Parrot Faurecia Automotive S.A.S,PARROT DRONE SAS'
  id=29 "Magnet Forensics": aliases='Magnet, GrayKey (product),MAGNET FORENSICS USA INC'
  id=32 "Clearview AI": aliases='Clearview'

## Totals
  applied = 172
  skip-duplicate-CSV = 15
  skip-identity-canonical = 51
  §5.4 deferred = 66
  halted = 0