# extraction_outputs/mac523_phase1/shodan_raw/ — content manifest

The 41 raw Shodan capture files that were under `shodan_raw/` were **removed from
git history** (MAC-717): one of them, `F1_upnp_module.json`, embedded a live
third-party Google OAuth client secret plus account PII that a scanned host was
serving, which GitHub push-protection correctly blocked. Raw captured HTTP/scan
response bodies carry whatever the scanned host served and must not be tracked;
the `shodan_raw/` layer is now gitignored (see `.gitignore`).

This manifest preserves provenance by content: anyone holding the raw files
out-of-band can verify them against these sha256 digests. The promoted output
of this harvest (`candidates_oui.json`, migration `0044`, the 8 ratified
`cctv_camera` OUIs) is unaffected and remains tracked.

Files: 41  Total bytes: 10,576,869

| file | sha256 | bytes |
|---|---|---:|
| `A1_port1900_ipcam.json` | `acc4b9f7946a271a96a312bb6b04844494151487d8abe4eb69161e2f6a75d540` | 25,407 |
| `A2_port1900_dvr.json` | `cf2254e2c2aeb4e4c1878abedba7a4b041245333f53ea422ef8ecdef17d33abf` | 184,014 |
| `A3_port1900_nvr.json` | `703ba36c0ff9ba419c3f2e520c18c0a540ff1d48e64946c61b5cdae7696b0120` | 100,157 |
| `A4_port1900_ptz.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `A5_port1900_networkcam.json` | `8e5eec48e7429e6a755443c68d5567a974113d90a1e85f9a34a9656fa1d3114a` | 222,409 |
| `B10_port1900_geovision.json` | `8871d3f7ea9ce858a3d9f9fa6ca658e0cd92294978cfc76e8c459a80de535c7e` | 3,749 |
| `B1_port1900_hikvision.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `B2_port1900_dahua.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `B3_port1900_axis.json` | `024d933ca07683cc52f0c552d3d660988055faccf64e63fabcd24e5cf0b6e27f` | 148,387 |
| `B4_port1900_vivotek.json` | `562175b607ef1f7bf104567f701f8f2ea2f47fb53136889b997ee51a0722d25b` | 248,973 |
| `B5_port1900_uniview.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `B6_port1900_hanwha.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `B7_port1900_bosch.json` | `15689b31ab3834a93542bd5610dad322af4da2eb36abf4e00ba82af90a8ceaf4` | 10,558 |
| `B8_port1900_avigilon.json` | `b716935512478abd41dc58e0e5e3bad3129c4810d5fc3fa7ed57fd0959238420` | 179,748 |
| `B9_port1900_pelco.json` | `615fbfb7103f4cb82edd1d95084a29cadc3159ebd09ec4af02dfe9ce485c5500` | 51,363 |
| `C1_port1900_has_screenshot_t.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `C2_port1900_no_screenshot.json` | `9cbee87a87d8f70265666914e25ea893a4ce05d29dbe15d27c3ae1b89458bdb8` | 390,334 |
| `C3_port1900_stunnel.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `D1_port1900_country_us.json` | `6b758a35bb782416485dd38993c96b476a5acaefe874a39e319aa0a1b5c1e5d4` | 408,047 |
| `E1_port1900_alpr.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `E2_port1900_surveillance.json` | `2c08d68fbb3315b75ce937f1120bd9f14baf56d56104b96bbb74c268802074dd` | 32,957 |
| `E3_port1900_dome.json` | `29b734db3750d1dabf466bec76ff06910f4c0255e9bd24763cb6f3999a7ae7eb` | 20,737 |
| `E4_port1900_bullet.json` | `7c338b807781bd8e08aece3a5c928268f7b663a60c04e872398efcd9c42abb23` | 13,634 |
| `F1_upnp_module.json` | `f1327590ebc062add6b1f5c1ac8dd677318090216e61a41ca8ea3d1de5a707f5` | 8,289,822 |
| `F2_port1900_product_camera.json` | `dedce07b36a77d74a19745e12ffd9e4c60f4224a1e58426cae7b374def261167` | 225,996 |
| `G1_port1900_xm.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `G2_port1900_jovision.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `G3_port1900_ens.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `G4_port1900_wansview.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `G5_port1900_sannce.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `G6_port1900_annke.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `G7_port1900_zavio.json` | `1532a968283d3c05030bc06df7a358adf9b1fbf5a4121d0461c69095c5b2dfd5` | 14,030 |
| `G8_port1900_arecont.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `H1_port1900_h264.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `H2_port1900_h265.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `H3_port1900_onvif.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `H4_port1900_rtsp.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `I1_port1900_genetec.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `J1_port1900_flock.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `J2_port1900_verkada.json` | `78b0d5b43911fa6c242b88b156589c0c9d92939aff268e97b9e91e971cf8134a` | 31 |
| `_summary.json` | `baba0f547ee9af450354dc3da9e4bec37e58787d195a7ae68b5054e23b221b79` | 5,865 |

