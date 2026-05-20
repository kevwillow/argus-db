# §6.4 alias enrichment log — MAC-192 Phase 6
Captured: 2026-05-20T19:50:21.695212+00:00
Proposals: 3

SAR-15 GENERIC_RISK_CANONICALS guard: tier-2/3 candidates with
industry-domain context per dispatch §6.4 — guard passes.

## 'Cellebrite DI LTD' → 'Cellebrite' (tier-3)
  SKIP-IDEMPOTENT: alias already present in 'Cellebrite'.aliases
## 'HoneywellSecurityGroup' → 'Honeywell' (tier-3)
  STAGED for Phase 8 (no Phase-6 mutation of Honeywell row)
## 'Verkada, Inc' → 'Verkada' (tier-2)
  SKIP-IDEMPOTENT: alias already present in 'Verkada'.aliases

## post-state Verkada: Verkada Command, Verkada Inc,Verkada Inc.

## post-state Cellebrite: CELLEBRITE FEDERAL SOLUTIONS, INC.,Cellebrite DI LTD

## post-state Honeywell: Honeywell Pro-Watch, Honeywell International, Honeywell Building Technologies, Honeywell International Inc.,HONEYWELL FEDERAL MANUFACTURING & TECHNOLOGY,Honeywell (Beijing) Technology Solutions Lab Co.,Ltd.,Honeywell (China) Co., LTD,Honeywell Access Systems,Honeywell Analytics,Honeywell Analytics Asia Pacific Co., Ltd.,Honeywell Analytics Inc,Honeywell Communication Networks Division,Honeywell Enraf,Honeywell Fed,Honeywell Global Tracking Ltd,Honeywell GmbH,Honeywell Hearing Technologies AS,Honeywell Inc,Honeywell Inc Residential Division,Honeywell Incorporated,Honeywell Integrated Technology (China) Co., Ltd,Honeywell Integrated Technology(China) Co.,LTD,Honeywell International (Commerical Avionics Products),Honeywell International Inc,Honeywell International Inc. (Alerton),Honeywell International Incorporated,Honeywell International, Inc.,Honeywell Keyboard Division,Honeywell Regelsysteme GmbH,Honeywell S.r.l.,Honeywell Safety Products USA, Inc.,Honeywell Security Sensor CoE,Honeywell Sensing and Control,Micro Switch Division of Honeywell

## Per-outcome counts
  applied: 0
  skipped_idempotent: 2
  honeywell_staged: 1
  halt: 0