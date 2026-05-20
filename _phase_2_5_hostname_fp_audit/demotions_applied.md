# MAC-188 Phase 2.5 — demotions applied (audit trail)

**Dispatch:** MAC-188 / Phase 2.5 hostname-corpus FP audit
**Applied at (UTC):** 2026-05-20T18:27:49Z
**Mechanic:** Q1.A (CEO-ratified) — MAC-110-style reclassification supersession. INSERT new row with `manufacturer=NULL` + `confidence=0` + `device_category='unknown'` + `notes.fp_demoted=true` + `notes.fp_class` + `notes.supersedes_identifier_id`. UPDATE old row's `superseded_by` to point at new row. Single transaction per manufacturer batch.

## Pre/post counts

| Metric | Pre | Post | Δ |
|---|---:|---:|---:|
| identifiers total | 34876 | 35138 | +262 |
| identifiers active (`superseded_by IS NULL`) | 34796 | 34796 | +0 |

Note: active count unchanged because each demotion swaps an old `mfr=<vendor>/conf=85` row for a new `mfr=NULL/conf=0` sentinel row. Both rows live in `identifiers`; the active filter promotes the sentinel.

## Per-manufacturer summary

| Manufacturer | Demotions applied | Scope-extension rationale |
|---|---:|---|
| reveal | 4 | ALL 4 rows demoted per >30% halt-band disposition (CEO ratified Q3 — `manufacturers` row retained for Stage 2 orphaned-manufacturer cleanup). |
| drt | 10 | 10 rows demoted per >30% halt-band; 3 survivors retained (drtinc.com x2 TP + drtstorage.blob AMBIGUOUS carry-forward). |
| lenel | 2 | 2 rows demoted per >30% halt-band; 2 survivors retained (real ACS vendor). |
| sierrawireless | 1 | 1 row demoted per >30% halt-band; 1 surviving TP row marked `notes.slug_duplication_review='see_phase_5'` (slug-merge deferred to Wave I.12). |
| verkada | 3 | 3 rows demoted per >30% halt-band; 6 survivors retained. |
| dji | 194 | 194 rows demoted per 10-30% sweep-demote band (originally; post-reclassification rate 44.5% — band moved to halt but cohort already named). Scope extends from initial 50-sample to FULL manufacturer subset (CEO-ratified §2.5.4 sweep). |
| parrot | 13 | 13 rows demoted per 10-30% sweep-demote band. Scope: FULL manufacturer subset. |
| autel_robotics | 11 | 11 rows demoted per 10-30% sweep-demote band. Scope: FULL manufacturer subset. |
| dahua | 24 | 24 rows demoted per 10-30% sweep-demote band. Scope: FULL manufacturer subset. 1 AMBIGUOUS row (dahua-cdn.s3) carry-forwarded. |
| **TOTAL** | **262** | |

## Per-fp_class summary (CP31 candidate breakdown)

| fp_class | Demotions | Description |
|---|---:|---|
| `third_party_oss_sdk_root` | 213 | OSS / SDK / CDN / CA / standards / personal-blog root cited as dependency-graph signal (not vendor-owned). |
| `synthetic_vendor_tenant_pattern` | 29 | `<vendor-token>-<common-suffix>.<third_party_cloud_apex>` over 19-entry synthetic suffix set. CP29 §2 bucket-attestation gate failed. |
| `cn_tech_giant_cross_attribution` | 20 | CN-tech-giant ecosystem (xiaomi/huawei/meizu/alipay/qq/etc.) cross-attributed to non-CN-tech-giant vendor. CP29 §1 vendor-ownership predicate violation. |

## Per-row before/after (paste-not-cite)

Format: `old_id → new_id  |  identifier  |  fp_class  |  classifier_reason`

| Manufacturer | old_id | new_id | identifier | fp_class | classifier_reason |
|---|---:|---:|---|---|---|
| reveal | 34685 | 35306 | `reveal-assets.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=assets` |
| reveal | 34686 | 35307 | `reveal-backup.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=backup` |
| reveal | 34687 | 35308 | `reveal-internal.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=internal` |
| reveal | 34688 | 35309 | `reveal-prod.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=prod` |
| drt | 28086 | 35310 | `drt-backup.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=backup` |
| drt | 35292 | 35311 | `drt-config.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=config` |
| drt | 35290 | 35312 | `drt-db.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=db` |
| drt | 35287 | 35313 | `drt-logs.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=logs` |
| drt | 35286 | 35314 | `drt-media.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=media` |
| drt | 28087 | 35315 | `drt-production.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=production` |
| drt | 28088 | 35316 | `drt-public.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=public` |
| drt | 35291 | 35317 | `drt-support.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=support` |
| drt | 35288 | 35318 | `drt-test.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=test` |
| drt | 35285 | 35319 | `drt-videos.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=videos` |
| lenel | 33986 | 35320 | `lenel-backup.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=backup` |
| lenel | 33987 | 35321 | `lenel-downloads.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=downloads` |
| sierrawireless | 35301 | 35322 | `sierrawireless.github.com` | `third_party_oss_sdk_root` | `known_fp_root::github.com` |
| verkada | 35227 | 35323 | `verkada-assets.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=assets` |
| verkada | 35228 | 35324 | `verkada-firmware.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=firmware` |
| verkada | 35229 | 35325 | `verkada-internal.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=internal` |
| dji | 27664 | 35326 | `amazonaws-china.com` | `third_party_oss_sdk_root` | `third_party_cloud_no_vendor_tenant::amazonaws-china.com` |
| dji | 27667 | 35327 | `android-gifview.googlecode.com` | `third_party_oss_sdk_root` | `known_fp_root::googlecode.com` |
| dji | 27668 | 35328 | `api-m.huya.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::huya.com` |
| dji | 27689 | 35329 | `bitbucket.org` | `third_party_oss_sdk_root` | `known_fp_root::bitbucket.org` |
| dji | 27692 | 35330 | `bugly.qq.com` | `third_party_oss_sdk_root` | `known_fp_root::bugly.qq.com` |
| dji | 27693 | 35331 | `bugs.llvm.org` | `third_party_oss_sdk_root` | `known_fp_root::llvm.org` |
| dji | 27694 | 35332 | `c2.com` | `third_party_oss_sdk_root` | `known_fp_root::c2.com` |
| dji | 27695 | 35333 | `caminobrowser.org` | `third_party_oss_sdk_root` | `known_fp_root::caminobrowser.org` |
| dji | 27697 | 35334 | `casper.beckman.uiuc.edu` | `third_party_oss_sdk_root` | `known_fp_root::uiuc.edu` |
| dji | 27699 | 35335 | `chasen.aist-nara.ac.jp` | `third_party_oss_sdk_root` | `known_fp_root::aist-nara.ac.jp` |
| dji | 27707 | 35336 | `codepen.io` | `third_party_oss_sdk_root` | `known_fp_root::codepen.io` |
| dji | 27713 | 35337 | `crashpad.googlecode.com` | `third_party_oss_sdk_root` | `known_fp_root::googlecode.com` |
| dji | 27714 | 35338 | `crt.usertrust.com` | `third_party_oss_sdk_root` | `known_fp_root::usertrust.com` |
| dji | 27715 | 35339 | `cubic-bezier.com` | `third_party_oss_sdk_root` | `known_fp_root::cubic-bezier.com` |
| dji | 27716 | 35340 | `cybertrust.omniroot.com` | `third_party_oss_sdk_root` | `known_fp_root::omniroot.com` |
| dji | 27717 | 35341 | `david-dm.org` | `third_party_oss_sdk_root` | `known_fp_root::david-dm.org` |
| dji | 27720 | 35342 | `devel.freebsoft.org` | `third_party_oss_sdk_root` | `known_fp_root::freebsoft.org` |
| dji | 27721 | 35343 | `developer.bluetooth.org` | `third_party_oss_sdk_root` | `known_fp_root::developer.bluetooth.org` |
| dji | 27722 | 35344 | `developer.chrome.com` | `third_party_oss_sdk_root` | `known_fp_root::developer.chrome.com` |
| dji | 27723 | 35345 | `developer.intel.com` | `third_party_oss_sdk_root` | `known_fp_root::developer.intel.com` |
| dji | 35279 | 35346 | `dji-backup.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=backup` |
| dji | 35283 | 35347 | `dji-config.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=config` |
| dji | 35280 | 35348 | `dji-dev.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=dev` |
| dji | 27724 | 35349 | `dji-fly.firebaseio.com` | `third_party_oss_sdk_root` | `known_fp_root::firebaseio.com` |
| dji | 35281 | 35350 | `dji-media.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=media` |
| dji | 27725 | 35351 | `dji-pilot.firebaseio.com` | `third_party_oss_sdk_root` | `known_fp_root::firebaseio.com` |
| dji | 35282 | 35352 | `dji-storage.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=storage` |
| dji | 27733 | 35353 | `dn-dji-videos.qbox.me` | `third_party_oss_sdk_root` | `known_fp_root::qbox.me` |
| dji | 27734 | 35354 | `dn-djidl2.qbox.me` | `third_party_oss_sdk_root` | `known_fp_root::qbox.me` |
| dji | 27735 | 35355 | `docs.geoserver.org` | `third_party_oss_sdk_root` | `known_fp_root::geoserver.org` |
| dji | 27740 | 35356 | `element.eleme.io` | `third_party_oss_sdk_root` | `known_fp_root::eleme.io` |
| dji | 27741 | 35357 | `elements.polymer-project.org` | `third_party_oss_sdk_root` | `known_fp_root::polymer-project.org` |
| dji | 27747 | 35358 | `errorprone.info` | `third_party_oss_sdk_root` | `known_fp_root::errorprone.info` |
| dji | 27750 | 35359 | `evintl-ccrt.gwww.gicert.com` | `third_party_oss_sdk_root` | `known_fp_root::gicert.com` |
| dji | 27751 | 35360 | `exslt.org` | `third_party_oss_sdk_root` | `known_fp_root::exslt.org` |
| dji | 27760 | 35361 | `foo.com` | `third_party_oss_sdk_root` | `known_fp_root::foo.com` |
| dji | 27761 | 35362 | `freegeoip.net` | `third_party_oss_sdk_root` | `known_fp_root::freegeoip.net` |
| dji | 27763 | 35363 | `g.symcb.com` | `third_party_oss_sdk_root` | `known_fp_root::symcb.com` |
| dji | 27764 | 35364 | `g1.symcb.com` | `third_party_oss_sdk_root` | `known_fp_root::symcb.com` |
| dji | 27765 | 35365 | `g2.symcb.com0l` | `third_party_oss_sdk_root` | `known_fp_root::symcb.com0l` |
| dji | 27766 | 35366 | `geo0.ggpht.com` | `third_party_oss_sdk_root` | `known_fp_root::ggpht.com` |
| dji | 27767 | 35367 | `geo1.ggpht.com` | `third_party_oss_sdk_root` | `known_fp_root::ggpht.com` |
| dji | 27768 | 35368 | `geo2.ggpht.com` | `third_party_oss_sdk_root` | `known_fp_root::ggpht.com` |
| dji | 27769 | 35369 | `geo3.ggpht.com` | `third_party_oss_sdk_root` | `known_fp_root::ggpht.com` |
| dji | 27770 | 35370 | `geojson.org` | `third_party_oss_sdk_root` | `known_fp_root::geojson.org` |
| dji | 27771 | 35371 | `git.gnome.org` | `third_party_oss_sdk_root` | `known_fp_root::gnome.org` |
| dji | 27772 | 35372 | `git.linuxtv.org` | `third_party_oss_sdk_root` | `known_fp_root::linuxtv.org` |
| dji | 27773 | 35373 | `git.xiph.org` | `third_party_oss_sdk_root` | `known_fp_root::xiph.org` |
| dji | 27774 | 35374 | `googleappengine.googlecode.com` | `third_party_oss_sdk_root` | `known_fp_root::googlecode.com` |
| dji | 27775 | 35375 | `gperftools.googlecode.com` | `third_party_oss_sdk_root` | `known_fp_root::googlecode.com` |
| dji | 27788 | 35376 | `harfbuzz.org` | `third_party_oss_sdk_root` | `known_fp_root::harfbuzz.org` |
| dji | 27789 | 35377 | `home.earthlink.net` | `third_party_oss_sdk_root` | `known_fp_root::earthlink.net` |
| dji | 27809 | 35378 | `icl.com` | `third_party_oss_sdk_root` | `known_fp_root::icl.com` |
| dji | 27813 | 35379 | `info.yahoo.com` | `third_party_oss_sdk_root` | `known_fp_root::yahoo.com` |
| dji | 27815 | 35380 | `invisible-island.net` | `third_party_oss_sdk_root` | `known_fp_root::invisible-island.net` |
| dji | 27816 | 35381 | `iptc.org` | `third_party_oss_sdk_root` | `known_fp_root::iptc.org` |
| dji | 27822 | 35382 | `jquery.org` | `third_party_oss_sdk_root` | `known_fp_root::jquery.org` |
| dji | 27823 | 35383 | `js.foundation` | `third_party_oss_sdk_root` | `known_fp_root::js.foundation` |
| dji | 27824 | 35384 | `jsbin.com` | `third_party_oss_sdk_root` | `known_fp_root::jsbin.com` |
| dji | 27825 | 35385 | `jsfiddle.net` | `third_party_oss_sdk_root` | `known_fp_root::jsfiddle.net` |
| dji | 27827 | 35386 | `lao-dictionary.googlecode.com` | `third_party_oss_sdk_root` | `known_fp_root::googlecode.com` |
| dji | 27829 | 35387 | `lh3.ggpht.com` | `third_party_oss_sdk_root` | `known_fp_root::ggpht.com` |
| dji | 27830 | 35388 | `lh4.ggpht.com` | `third_party_oss_sdk_root` | `known_fp_root::ggpht.com` |
| dji | 27831 | 35389 | `lh5.ggpht.com` | `third_party_oss_sdk_root` | `known_fp_root::ggpht.com` |
| dji | 27832 | 35390 | `lh6.ggpht.com` | `third_party_oss_sdk_root` | `known_fp_root::ggpht.com` |
| dji | 27833 | 35391 | `libcxx.llvm.org` | `third_party_oss_sdk_root` | `known_fp_root::llvm.org` |
| dji | 27834 | 35392 | `libcxxabi.llvm.org` | `third_party_oss_sdk_root` | `known_fp_root::llvm.org` |
| dji | 27835 | 35393 | `libphonenumber.googlecode.com` | `third_party_oss_sdk_root` | `known_fp_root::googlecode.com` |
| dji | 27836 | 35394 | `libusb.info` | `third_party_oss_sdk_root` | `known_fp_root::libusb.info` |
| dji | 27837 | 35395 | `libusb.org` | `third_party_oss_sdk_root` | `known_fp_root::libusb.org` |
| dji | 27842 | 35396 | `llvm.org` | `third_party_oss_sdk_root` | `known_fp_root::llvm.org` |
| dji | 27843 | 35397 | `lodash.com` | `third_party_oss_sdk_root` | `known_fp_root::lodash.com` |
| dji | 27844 | 35398 | `log.getdropbox.com` | `third_party_oss_sdk_root` | `known_fp_root::getdropbox.com` |
| dji | 27846 | 35399 | `m.imeitou.com` | `third_party_oss_sdk_root` | `known_fp_root::imeitou.com` |
| dji | 27850 | 35400 | `materialdesignicons.com` | `third_party_oss_sdk_root` | `known_fp_root::materialdesignicons.com` |
| dji | 27851 | 35401 | `mathiasbynens.be` | `third_party_oss_sdk_root` | `known_fp_root::mathiasbynens.be` |
| dji | 27852 | 35402 | `mesonet.agron.iastate.edu` | `third_party_oss_sdk_root` | `known_fp_root::iastate.edu` |
| dji | 27853 | 35403 | `mikepenz.com` | `third_party_oss_sdk_root` | `known_fp_root::mikepenz.com` |
| dji | 27857 | 35404 | `modp.com` | `third_party_oss_sdk_root` | `known_fp_root::modp.com` |
| dji | 27860 | 35405 | `mths.be` | `third_party_oss_sdk_root` | `known_fp_root::mths.be` |
| dji | 27862 | 35406 | `narwhaljs.org` | `third_party_oss_sdk_root` | `known_fp_root::narwhaljs.org` |
| dji | 27863 | 35407 | `nedbatchelder.com` | `third_party_oss_sdk_root` | `known_fp_root::nedbatchelder.com` |
| dji | 27864 | 35408 | `netflixoss.ci.cloudbees.com` | `third_party_oss_sdk_root` | `known_fp_root::cloudbees.com` |
| dji | 27865 | 35409 | `npmjs.org` | `third_party_oss_sdk_root` | `known_fp_root::npmjs.org` |
| dji | 27867 | 35410 | `opendocs.alipay.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::alipay.com` |
| dji | 27868 | 35411 | `openmp.llvm.org` | `third_party_oss_sdk_root` | `known_fp_root::llvm.org` |
| dji | 27869 | 35412 | `osm.org` | `third_party_oss_sdk_root` | `known_fp_root::osm.org` |
| dji | 27870 | 35413 | `oss.sgi.com` | `third_party_oss_sdk_root` | `known_fp_root::sgi.com` |
| dji | 27873 | 35414 | `paulirish.com` | `third_party_oss_sdk_root` | `known_fp_root::paulirish.com` |
| dji | 27875 | 35415 | `philbit.com` | `third_party_oss_sdk_root` | `known_fp_root::philbit.com` |
| dji | 27876 | 35416 | `pki-crl.symauth.com` | `third_party_oss_sdk_root` | `known_fp_root::symauth.com` |
| dji | 27877 | 35417 | `pki.intel.com` | `third_party_oss_sdk_root` | `known_fp_root::intel.com` |
| dji | 27878 | 35418 | `pod.tst.eu` | `third_party_oss_sdk_root` | `known_fp_root::tst.eu` |
| dji | 27879 | 35419 | `protobuf.googlecode.com` | `third_party_oss_sdk_root` | `known_fp_root::googlecode.com` |
| dji | 27891 | 35420 | `receive.utmiss.com` | `third_party_oss_sdk_root` | `known_fp_root::utmiss.com` |
| dji | 27894 | 35421 | `registry.npm.taobao.org` | `cn_tech_giant_cross_attribution` | `known_fp_root::taobao.org` |
| dji | 27895 | 35422 | `relaxng.org` | `third_party_oss_sdk_root` | `known_fp_root::relaxng.org` |
| dji | 27897 | 35423 | `rentzsch.com` | `third_party_oss_sdk_root` | `known_fp_root::rentzsch.com` |
| dji | 27901 | 35424 | `rosettacode.org` | `third_party_oss_sdk_root` | `known_fp_root::rosettacode.org` |
| dji | 27903 | 35425 | `s1.symcb.com` | `third_party_oss_sdk_root` | `known_fp_root::symcb.com` |
| dji | 27904 | 35426 | `s2.symcb.com0e` | `third_party_oss_sdk_root` | `known_fp_root::symcb.com0e` |
| dji | 27905 | 35427 | `sctp-refimpl.googlecode.com` | `third_party_oss_sdk_root` | `known_fp_root::googlecode.com` |
| dji | 27908 | 35428 | `selenium.googlecode.com` | `third_party_oss_sdk_root` | `known_fp_root::googlecode.com` |
| dji | 27910 | 35429 | `silver.arm.com` | `third_party_oss_sdk_root` | `known_fp_root::silver.arm.com` |
| dji | 27911 | 35430 | `site.icu-project.org` | `third_party_oss_sdk_root` | `known_fp_root::icu-project.org` |
| dji | 27912 | 35431 | `sizzlejs.com` | `third_party_oss_sdk_root` | `known_fp_root::sizzlejs.com` |
| dji | 27913 | 35432 | `skal.planet-d.net` | `third_party_oss_sdk_root` | `known_fp_root::planet-d.net` |
| dji | 27914 | 35433 | `skia.org` | `third_party_oss_sdk_root` | `known_fp_root::skia.org` |
| dji | 27915 | 35434 | `sourceware.org` | `third_party_oss_sdk_root` | `known_fp_root::sourceware.org` |
| dji | 27923 | 35435 | `support.googlecode.com` | `third_party_oss_sdk_root` | `known_fp_root::googlecode.com` |
| dji | 27924 | 35436 | `svgwg.org` | `third_party_oss_sdk_root` | `known_fp_root::svgwg.org` |
| dji | 27925 | 35437 | `sw.blackmagicdesign.com` | `third_party_oss_sdk_root` | `known_fp_root::blackmagicdesign.com` |
| dji | 27926 | 35438 | `t.symcb.com` | `third_party_oss_sdk_root` | `known_fp_root::symcb.com` |
| dji | 27927 | 35439 | `talloc.samba.org` | `third_party_oss_sdk_root` | `known_fp_root::samba.org` |
| dji | 27928 | 35440 | `tempuri.org` | `third_party_oss_sdk_root` | `known_fp_root::tempuri.org` |
| dji | 35305 | 35441 | `terra-sz-hc1pro-cloudapi.oss-cn-shenzhen.aliyuncs.com` | `third_party_oss_sdk_root` | `third_party_cloud_no_vendor_tenant::aliyuncs.com` |
| dji | 27935 | 35442 | `transgaming.com` | `third_party_oss_sdk_root` | `known_fp_root::transgaming.com` |
| dji | 27936 | 35443 | `trevp.net` | `third_party_oss_sdk_root` | `known_fp_root::trevp.net` |
| dji | 27937 | 35444 | `trolltech.com` | `third_party_oss_sdk_root` | `known_fp_root::trolltech.com` |
| dji | 27943 | 35445 | `underscorejs.org` | `third_party_oss_sdk_root` | `known_fp_root::underscorejs.org` |
| dji | 27944 | 35446 | `unlicense.org` | `third_party_oss_sdk_root` | `known_fp_root::unlicense.org` |
| dji | 27945 | 35447 | `upgrade.dj2006.net` | `third_party_oss_sdk_root` | `known_fp_root::dj2006.net` |
| dji | 27946 | 35448 | `valgrind.org` | `third_party_oss_sdk_root` | `known_fp_root::valgrind.org` |
| dji | 27949 | 35449 | `webk.it` | `third_party_oss_sdk_root` | `known_fp_root::webk.it` |
| dji | 27950 | 35450 | `weibo.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::weibo.com` |
| dji | 27951 | 35451 | `wiki.commonjs.org` | `third_party_oss_sdk_root` | `known_fp_root::wiki.commonjs.org` |
| dji | 27952 | 35452 | `wiki.osgeo.org` | `third_party_oss_sdk_root` | `known_fp_root::wiki.osgeo.org` |
| dji | 27953 | 35453 | `wiki.squid-cache.org` | `third_party_oss_sdk_root` | `known_fp_root::squid-cache.org` |
| dji | 27956 | 35454 | `www.3waylabs.com` | `third_party_oss_sdk_root` | `known_fp_root::3waylabs.com` |
| dji | 27957 | 35455 | `www.7-zip.org` | `third_party_oss_sdk_root` | `known_fp_root::7-zip.org` |
| dji | 27958 | 35456 | `www.adel.nursat.kz` | `third_party_oss_sdk_root` | `known_fp_root::nursat.kz` |
| dji | 27962 | 35457 | `www.alphassl.com` | `third_party_oss_sdk_root` | `known_fp_root::alphassl.com` |
| dji | 27967 | 35458 | `www.azillionmonkeys.com` | `third_party_oss_sdk_root` | `known_fp_root::azillionmonkeys.com` |
| dji | 27969 | 35459 | `www.bilibili.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::bilibili.com` |
| dji | 27971 | 35460 | `www.brynosaurus.com` | `third_party_oss_sdk_root` | `known_fp_root::brynosaurus.com` |
| dji | 27973 | 35461 | `www.certplus.com` | `third_party_oss_sdk_root` | `known_fp_root::certplus.com` |
| dji | 27975 | 35462 | `www.chromestatus.com` | `third_party_oss_sdk_root` | `known_fp_root::chromestatus.com` |
| dji | 27978 | 35463 | `www.css` | `third_party_oss_sdk_root` | `known_fp_root::www.css` |
| dji | 27979 | 35464 | `www.dabeaz.com` | `third_party_oss_sdk_root` | `known_fp_root::dabeaz.com` |
| dji | 27980 | 35465 | `www.daemonology.net` | `third_party_oss_sdk_root` | `known_fp_root::daemonology.net` |
| dji | 27987 | 35466 | `www.douyin.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::douyin.com` |
| dji | 27989 | 35467 | `www.ecma-international.org` | `third_party_oss_sdk_root` | `known_fp_root::ecma-international.org` |
| dji | 27991 | 35468 | `www.elecard.com` | `third_party_oss_sdk_root` | `known_fp_root::elecard.com` |
| dji | 27997 | 35469 | `www.fisglobal.com` | `third_party_oss_sdk_root` | `known_fp_root::fisglobal.com` |
| dji | 27998 | 35470 | `www.flotcharts.org` | `third_party_oss_sdk_root` | `known_fp_root::flotcharts.org` |
| dji | 27999 | 35471 | `www.getui.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::getui.com` |
| dji | 28000 | 35472 | `www.google` | `third_party_oss_sdk_root` | `known_fp_root::www.google` |
| dji | 28002 | 35473 | `www.hortcut` | `third_party_oss_sdk_root` | `known_fp_root::www.hortcut` |
| dji | 28003 | 35474 | `www.icon` | `third_party_oss_sdk_root` | `known_fp_root::www.icon` |
| dji | 28004 | 35475 | `www.inkscape.org` | `third_party_oss_sdk_root` | `known_fp_root::inkscape.org` |
| dji | 28005 | 35476 | `www.interpretation` | `third_party_oss_sdk_root` | `known_fp_root::www.interpretation` |
| dji | 28007 | 35477 | `www.jcip.net` | `third_party_oss_sdk_root` | `known_fp_root::jcip.net` |
| dji | 28008 | 35478 | `www.jclark.com` | `third_party_oss_sdk_root` | `known_fp_root::jclark.com` |
| dji | 28010 | 35479 | `www.keynectis.com` | `third_party_oss_sdk_root` | `known_fp_root::keynectis.com` |
| dji | 28011 | 35480 | `www.khronos.org` | `third_party_oss_sdk_root` | `known_fp_root::khronos.org` |
| dji | 28012 | 35481 | `www.kuaishou.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::kuaishou.com` |
| dji | 28014 | 35482 | `www.language` | `third_party_oss_sdk_root` | `known_fp_root::www.language` |
| dji | 28016 | 35483 | `www.lib.utexas.edu` | `third_party_oss_sdk_root` | `known_fp_root::utexas.edu` |
| dji | 28018 | 35484 | `www.linux-usb.org` | `third_party_oss_sdk_root` | `known_fp_root::linux-usb.org` |
| dji | 28019 | 35485 | `www.linuxfoundation.org` | `third_party_oss_sdk_root` | `known_fp_root::linuxfoundation.org` |
| dji | 28020 | 35486 | `www.linuxvideo.org` | `third_party_oss_sdk_root` | `known_fp_root::linuxvideo.org` |
| dji | 28025 | 35487 | `www.math.sci.hiroshima-u.ac.jp` | `third_party_oss_sdk_root` | `known_fp_root::hiroshima-u.ac.jp` |
| dji | 28026 | 35488 | `www.mesa3d.org` | `third_party_oss_sdk_root` | `known_fp_root::mesa3d.org` |
| dji | 28027 | 35489 | `www.midnight-commander.org` | `third_party_oss_sdk_root` | `known_fp_root::midnight-commander.org` |
| dji | 28031 | 35490 | `www.monkey.org` | `third_party_oss_sdk_root` | `known_fp_root::monkey.org` |
| dji | 28032 | 35491 | `www.movable-type.co.uk` | `third_party_oss_sdk_root` | `known_fp_root::movable-type.co.uk` |
| dji | 28037 | 35492 | `www.netlib.org` | `third_party_oss_sdk_root` | `known_fp_root::netlib.org` |
| dji | 28038 | 35493 | `www.oasis-open.org` | `third_party_oss_sdk_root` | `known_fp_root::oasis-open.org` |
| dji | 28039 | 35494 | `www.ogre3d.org` | `third_party_oss_sdk_root` | `known_fp_root::ogre3d.org` |
| dji | 28040 | 35495 | `www.onvif.org` | `third_party_oss_sdk_root` | `known_fp_root::onvif.org` |
| dji | 28041 | 35496 | `www.openstreetmap.org` | `third_party_oss_sdk_root` | `known_fp_root::openstreetmap.org` |
| dji | 28042 | 35497 | `www.oppo.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::oppo.com` |
| dji | 28043 | 35498 | `www.phreedom.org` | `third_party_oss_sdk_root` | `known_fp_root::phreedom.org` |
| dji | 28044 | 35499 | `www.polymer-project.org` | `third_party_oss_sdk_root` | `known_fp_root::polymer-project.org` |
| dji | 28048 | 35500 | `www.qq.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::qq.com` |
| dji | 28049 | 35501 | `www.recent` | `third_party_oss_sdk_root` | `known_fp_root::www.recent` |
| dji | 28053 | 35502 | `www.seanpatrickobrien.com` | `third_party_oss_sdk_root` | `known_fp_root::seanpatrickobrien.com` |
| dji | 28054 | 35503 | `www.squid-cache.org` | `third_party_oss_sdk_root` | `known_fp_root::squid-cache.org` |
| dji | 28056 | 35504 | `www.strongtalk.org` | `third_party_oss_sdk_root` | `known_fp_root::strongtalk.org` |
| dji | 28057 | 35505 | `www.style` | `third_party_oss_sdk_root` | `known_fp_root::www.style` |
| dji | 28058 | 35506 | `www.suitable.com` | `third_party_oss_sdk_root` | `known_fp_root::suitable.com` |
| dji | 28059 | 35507 | `www.symauth.com` | `third_party_oss_sdk_root` | `known_fp_root::symauth.com` |
| dji | 28062 | 35508 | `www.text-decoration` | `third_party_oss_sdk_root` | `known_fp_root::www.text-decoration` |
| dji | 28063 | 35509 | `www.torchmobile.com` | `third_party_oss_sdk_root` | `known_fp_root::torchmobile.com` |
| dji | 28064 | 35510 | `www.tortall.net` | `third_party_oss_sdk_root` | `known_fp_root::tortall.net` |
| dji | 28067 | 35511 | `www.umeng.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::umeng.com` |
| dji | 28068 | 35512 | `www.usertrust.com` | `third_party_oss_sdk_root` | `known_fp_root::usertrust.com` |
| dji | 28069 | 35513 | `www.vivo.com.cn` | `cn_tech_giant_cross_attribution` | `known_fp_root::vivo.com.cn` |
| dji | 28070 | 35514 | `www.webmproject.org` | `third_party_oss_sdk_root` | `known_fp_root::webmproject.org` |
| dji | 28071 | 35515 | `www.wencodeuricomponent` | `third_party_oss_sdk_root` | `known_fp_root::www.wencodeuricomponent` |
| dji | 28072 | 35516 | `www.winimage.com` | `third_party_oss_sdk_root` | `known_fp_root::winimage.com` |
| dji | 28073 | 35517 | `www.world` | `third_party_oss_sdk_root` | `known_fp_root::www.world` |
| dji | 28074 | 35518 | `www.years` | `third_party_oss_sdk_root` | `known_fp_root::www.years` |
| dji | 28075 | 35519 | `xmlsoft.org` | `third_party_oss_sdk_root` | `known_fp_root::xmlsoft.org` |
| parrot | 34589 | 35520 | `api.skyward.io` | `third_party_oss_sdk_root` | `known_fp_root::skyward.io` |
| parrot | 34610 | 35521 | `docs.scipy.org` | `third_party_oss_sdk_root` | `known_fp_root::scipy.org` |
| parrot | 34613 | 35522 | `eigen.tuxfamily.org` | `third_party_oss_sdk_root` | `known_fp_root::tuxfamily.org` |
| parrot | 34619 | 35523 | `offline-live1.services.u-blox.com` | `third_party_oss_sdk_root` | `known_fp_root::u-blox.com` |
| parrot | 34620 | 35524 | `offline-live2.services.u-blox.com` | `third_party_oss_sdk_root` | `known_fp_root::u-blox.com` |
| parrot | 34622 | 35525 | `parrot-backup.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=backup` |
| parrot | 34623 | 35526 | `parrot-dev.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=dev` |
| parrot | 34624 | 35527 | `parrot-ff6.firebaseio.com` | `third_party_oss_sdk_root` | `known_fp_root::firebaseio.com` |
| parrot | 34625 | 35528 | `parrot-production.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=production` |
| parrot | 34626 | 35529 | `parrot-public.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=public` |
| parrot | 34627 | 35530 | `parrot-uploads.s3.amazonaws.com` | `synthetic_vendor_tenant_pattern` | `synthetic_vendor_tenant_pattern::s3.amazonaws.com::suffix=uploads` |
| parrot | 34637 | 35531 | `skyward.io` | `third_party_oss_sdk_root` | `known_fp_root::skyward.io` |
| parrot | 34642 | 35532 | `www.adobepartneroffer.com` | `third_party_oss_sdk_root` | `known_fp_root::adobepartneroffer.com` |
| autel_robotics | 23160 | 35533 | `air.aloft.rocks` | `third_party_oss_sdk_root` | `known_fp_root::aloft.rocks` |
| autel_robotics | 23162 | 35534 | `api.openweathermap.org` | `third_party_oss_sdk_root` | `known_fp_root::openweathermap.org` |
| autel_robotics | 23169 | 35535 | `cert.startcom.org` | `third_party_oss_sdk_root` | `known_fp_root::startcom.org` |
| autel_robotics | 23183 | 35536 | `greenrobot.org` | `third_party_oss_sdk_root` | `known_fp_root::greenrobot.org` |
| autel_robotics | 23190 | 35537 | `metadata.google.internal` | `third_party_oss_sdk_root` | `known_fp_root::google.internal` |
| autel_robotics | 23191 | 35538 | `modelb-d4935.firebaseio.com` | `third_party_oss_sdk_root` | `known_fp_root::firebaseio.com` |
| autel_robotics | 23192 | 35539 | `openapi.baidu.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::baidu.com` |
| autel_robotics | 23193 | 35540 | `org.dom4j.io.doucmentsource` | `third_party_oss_sdk_root` | `known_fp_root::io.doucmentsource` |
| autel_robotics | 23197 | 35541 | `playready.directtaps.net` | `third_party_oss_sdk_root` | `known_fp_root::playready.directtaps.net` |
| autel_robotics | 23212 | 35542 | `www.hamcrest.com` | `third_party_oss_sdk_root` | `known_fp_root::hamcrest.com` |
| autel_robotics | 23213 | 35543 | `www.jstott.me.uk` | `third_party_oss_sdk_root` | `known_fp_root::me.uk` |
| dahua | 27421 | 35544 | `access.line.me` | `cn_tech_giant_cross_attribution` | `known_fp_root::line.me` |
| dahua | 27422 | 35545 | `actionbarsherlock.com` | `third_party_oss_sdk_root` | `known_fp_root::actionbarsherlock.com` |
| dahua | 27425 | 35546 | `androidpush-prod.messagepush.org` | `third_party_oss_sdk_root` | `known_fp_root::messagepush.org` |
| dahua | 27427 | 35547 | `api.line.me` | `cn_tech_giant_cross_attribution` | `known_fp_root::line.me` |
| dahua | 27440 | 35548 | `curl.haxx.se` | `third_party_oss_sdk_root` | `known_fp_root::haxx.se` |
| dahua | 27448 | 35549 | `fb.gg` | `third_party_oss_sdk_root` | `known_fp_root::fb.gg` |
| dahua | 27453 | 35550 | `goo.gle` | `third_party_oss_sdk_root` | `known_fp_root::goo.gle` |
| dahua | 27457 | 35551 | `journeyapps.com` | `third_party_oss_sdk_root` | `known_fp_root::journeyapps.com` |
| dahua | 27475 | 35552 | `open.oppomobile.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::oppomobile.com` |
| dahua | 27476 | 35553 | `ormlite.com` | `third_party_oss_sdk_root` | `known_fp_root::ormlite.com` |
| dahua | 27482 | 35554 | `registry.npmjs.org` | `third_party_oss_sdk_root` | `known_fp_root::npmjs.org` |
| dahua | 27483 | 35555 | `render.alipay.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::alipay.com` |
| dahua | 27484 | 35556 | `schema.getpostman.com` | `third_party_oss_sdk_root` | `known_fp_root::getpostman.com` |
| dahua | 27485 | 35557 | `sj.qq.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::qq.com` |
| dahua | 27486 | 35558 | `source.icu-project.org` | `third_party_oss_sdk_root` | `known_fp_root::icu-project.org` |
| dahua | 27487 | 35559 | `squareup.com` | `third_party_oss_sdk_root` | `known_fp_root::squareup.com` |
| dahua | 27507 | 35560 | `www.cryptopp.com` | `third_party_oss_sdk_root` | `known_fp_root::cryptopp.com` |
| dahua | 27510 | 35561 | `www.grinninglizard.com` | `third_party_oss_sdk_root` | `known_fp_root::grinninglizard.com` |
| dahua | 27511 | 35562 | `www.isc.org` | `third_party_oss_sdk_root` | `known_fp_root::isc.org` |
| dahua | 27513 | 35563 | `www.libpng.org` | `third_party_oss_sdk_root` | `known_fp_root::libpng.org` |
| dahua | 27514 | 35564 | `www.linfo.org` | `third_party_oss_sdk_root` | `known_fp_root::linfo.org` |
| dahua | 27517 | 35565 | `www.tenpay.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::tenpay.com` |
| dahua | 27518 | 35566 | `www.vivo.com` | `cn_tech_giant_cross_attribution` | `known_fp_root::vivo.com` |
| dahua | 27519 | 35567 | `www.xfa.org` | `third_party_oss_sdk_root` | `known_fp_root::xfa.org` |

## Discipline checklist

- ✅ SAR-13 PRAGMA + CHECK enum verified pre-sweep (hb_002_5_halt heartbeat).
- ✅ SAR-14 inline calibration — full audit completed; per-manufacturer FP rates above the 10% threshold drove demotions; <10% manufacturers carry forward unchanged.
- ✅ §11 #1 no fabrication — actual identifier strings preserved; new sentinel rows carry `notes.classifier_reason` linking to specific reason string.
- ✅ §11 #7 provenance — every demotion preserves the old row in `identifiers` with full source_url / source_excerpt / notes; superseded-row preservation per §6.4.
- ✅ §11 #8 demotions via supersession (not inline confidence edits) — Q1.A CEO-ratified mechanic followed exactly.
- ✅ §11 #11 amendment-log discipline — 4 novel FP classes codified in `provisional_classifier_rules.json` as CP31 candidates; SAR-17 candidate proposed (canonical FP-demotion mechanic).
- ✅ Single transaction per manufacturer batch; rollback on per-row failure (no rollback fired this sweep).
- ✅ AMBIGUOUS rows carry-forward marked `notes.audit_review_required=true` (Q2.A); not silently demoted.
- ✅ sierrawireless surviving TP row marked `notes.slug_duplication_review='see_phase_5'` (Q3 — no slug merge in this pass).

## Next-action gates

- Phase 2.5 closes `done`. Parent MAC-184 wakes CEO via `issue_children_completed`. MAC-189 (Phase 3b) auto-unblocks for the 22 lift candidates re-evaluation against the post-demote canon.
- Stage 2 carry-forwards: (a) SAR-17 canonical FP-demotion mechanic; (b) CP31 four novel FP classes; (c) reveal orphaned-manufacturer cleanup; (d) sierrawireless slug-merge in Phase 5; (e) audit_review_queue (143 rows) for v1.4.2 / Stage 2 operator-review pass; (f) 64 non-cohort FP rows for v1.4.2 sweep.
