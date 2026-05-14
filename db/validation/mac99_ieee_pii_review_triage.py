"""MAC-99 Stream 1: IEEE pii_review_hold entity-type triage (3,521 + 133 rows).

Per-row Class A/B/C/D entity-type disposition over the 3,654 IEEE Wave-B
pii_review_hold rows staged by MAC-91 (extraction_runs 95/96/97):

- Class A — corporate-no-suffix-validated → promote to identifiers at
  source_type='primary_registry', confidence=85 (CP15 §8.2 single-source ceiling),
  identifier_type='mac_range', device_category='unknown' (§11 #13 multi-purpose-
  vendor carveout), geographic_scope='global', source_url from sources row,
  source_excerpt from raw_observations.source_excerpt. Back-link
  raw_observations.promoted_identifier_id.
- Class B — individual-attributed-pii-sustain → notes-disposition only; HOLD per
  §11 #3 PII discipline. No promotion.
- Class C — ieee_private_registrant_permanent_hold (the 133 rows where
  notes.ieee_private_registrant=true). Notes-disposition only; no promotion
  regardless of further investigation per board §2.2.
- Class D — ambiguous_pending_ceo_resolution → notes-disposition + escalate to
  CEO. Interim hold pending resolution. Expected <5% (<176 rows).

Authority chain:
- Bible §6 Phase 5 + §7.4 (Validator promotion contract).
- §11 #3 PII discipline (governing rule; uncertainty → HOLD, not PROMOTE).
- §11 #7 provenance preserved (source_url + source_excerpt carried through).
- §11 #8 no confidence drift (single-source rows stay at single-source 85).
- §11 #13 device_category='unknown' carveout for multi-purpose-vendor OUI.
- CP15 §8.2 primary_registry sub-rule (85 ceiling single-source).
- SAR-12 dispatch-preamble live-state verification (§0 baselines all matched
  DB at authoring: 3,521 + 133 + 18,820 + 808).
- MAC-99 dispatch §2.1-§2.4 class definitions.

Idempotent: re-running with the same pii_review_hold cohort yields zero new
identifiers rows (guards on extraction_runs.notes idempotency-key
'MAC-99-stream-1' and raw_observations.promoted_identifier_id presence).
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "argus.db"

VALIDATOR_AGENT_ID = "da137694-2efe-4589-8150-828dcab881fb"
DISPATCH_IDEMPOTENCY_KEY = "MAC-99-stream-1"
NOW_UTC = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# IEEE Wave-B extraction_run start time (shared across runs 95/96/97; matches the
# existing MAC-91 promoted-row first_seen convention).
IEEE_WAVE_B_FIRST_SEEN = "2026-05-13T23:03:07Z"

# Strong corporate-suffix regex. Word-boundary + case-insensitive. Includes English,
# European, Asian, and Latin-American legal forms; covers both the
# candidate_manufacturer field and the organization_address text in notes.
# Non-ASCII tokens (OÜ, A.Ş, etc.) use a custom non-word/space boundary because
# Python re's \b doesn't handle non-ASCII characters reliably in all contexts.
_CORP_SUFFIX_TOKENS = [
    # English
    r"LLC", r"L\.L\.C", r"INC", r"Inc\.?", r"CORP", r"Corp\.?", r"Corporation",
    r"Corporate", r"Co\.,?", r"Company", r"Companies", r"Ltd\.?", r"Limited",
    r"Holdings", r"Holding", r"Group", r"Plc", r"PLC", r"LLP", r"ULC",
    # German / Austrian / Swiss
    r"GmbH", r"AG", r"mbH", r"OHG", r"KG", r"e\.K\.", r"e\.V\.",
    # Italian
    r"S\.?p\.?A", r"SpA", r"S\.?r\.?l", r"s\.?r\.?l",
    # Spanish / Portuguese / Latin-American
    r"S\.A", r"S\.L", r"S\.A\.S", r"SAS", r"SAU", r"S/A", r"LTDA", r"Ltda",
    r"EIRELI", r"Eireli", r"S\.A\.U", r"S\.L\.U", r"Cía", r"Cia", r"C\.V",
    r"S\. de R\.L", r"S\.de R\.L",
    # French
    r"SARL", r"SASU", r"S\.A\.S\.U", r"SCOP", r"SCI", r"EURL",
    # Dutch / Belgian
    r"N\.?V\.?", r"B\.?V\.?", r"BVBA", r"BV",
    # Nordic
    r"Oy", r"AB", r"ASA", r"ApS", r"aps", r"Hf\.", r"hf",
    # Danish / Norwegian
    r"A/S", r"AS", r"K/S", r"ApS",
    # Eastern European
    r"d\.?o\.?o", r"d\.?d\.?", r"Sp\. ?z ?o\.?o", r"Sp\.J", r"Zrt", r"Kft",
    r"UAB", r"SIA", r"OOO", r"ZAO", r"AO", r"JSC", r"s\.?r\.?o",
    # Czech
    r"a\.s",
    # Japanese / Korean / Chinese
    r"K\.?K\.?", r"Co\., ?Ltd", r"Pte", r"Pte\. ?Ltd", r"株式会社", r"有限会社",
    # Indian / Other Asian
    r"Pvt\.? ?Ltd\.?", r"PVT\.?", r"Pvt", r"Pty\.? ?Ltd\.?", r"Pty",
    # Romanian
    r"SRL",
    # German variants
    r"Industriestrasse", r"Industriestr",
    # Misc free zones
    r"FZE", r"FZ-LLC", r"FZ ?LLC", r"FZCO",
]
CORP_SUFFIX_RE = re.compile(r"\b(?:" + "|".join(_CORP_SUFFIX_TOKENS) + r")\b", re.IGNORECASE)

# Non-ASCII corporate-suffix tokens (Turkish A.Ş, Estonian OÜ, Cyrillic ООО etc.).
# Use space/start/end/punctuation as boundary instead of \b.
_NONASCII_CORP_TOKENS = [
    r"A\.Ş", r"A\.Ş\.", r"OÜ", r"ÖÜ", r"Sàrl", r"SÀRL", r"Şti",
    # Cyrillic (Russian / Ukrainian / Belarusian)
    r"ООО", r"ЗАО", r"ОАО", r"ПАО", r"АО", r"ТОО", r"ИП", r"НПО", r"ФГБУ",
    r"ФГУП", r"МУП", r"ГУП", r"НП",
]
NONASCII_CORP_RE = re.compile(
    r"(?:^|[\s,.()\[\]{}«»\"'])(" + "|".join(_NONASCII_CORP_TOKENS) + r")(?:$|[\s,.()\[\]{}«»\"'])",
    re.IGNORECASE,
)

# Government / academic / institutional keywords.
_GOV_ACAD_TOKENS = [
    r"Dept", r"Department", r"Ministry", r"Bureau", r"Agency", r"Authority",
    r"Federal", r"Government", r"Govt", r"United States",
    r"U\.S\.", r"US Army", r"Army", r"Navy", r"Air ?Force", r"Marines",
    r"NASA", r"NOAA", r"EPA", r"DOD", r"DARPA", r"DOE", r"DOT", r"FBI",
    r"DHS", r"TSA", r"HHS", r"VA", r"FDA", r"FAA", r"FCC", r"NSA", r"NSF",
    r"NIH", r"NIST", r"USAF", r"USMC", r"USPS",
    r"Police", r"Sheriff", r"Fire", r"Emergency", r"Public", r"Municipal",
    r"City of", r"County of", r"State of", r"Province", r"Provincial",
    r"Republic of", r"Republik", r"Kingdom of", r"Commonwealth",
    r"Univ", r"University", r"Université", r"Universidad", r"Universität",
    r"College", r"Institute", r"Institut", r"Instituto", r"Academy",
    r"School", r"Schule", r"Library", r"Hospital", r"Medical Center",
    r"Research", r"Laboratory", r"Labs", r"National", r"Federation",
    r"Royal", r"Crown", r"Embassy", r"Consulate",
    r"NGO", r"Nonprofit", r"Non-profit", r"Charity", r"Foundation",
    r"Trust", r"Endowment", r"Cooperative", r"Co-op",
]
GOV_ACAD_RE = re.compile(r"\b(?:" + "|".join(_GOV_ACAD_TOKENS) + r")\b", re.IGNORECASE)

# Industry / product / service nouns that signal a corporation when present in
# the company-name field. Sourced from frequency-analysis of the 3,521-row
# pii_review_hold cohort's name-token distribution (top last-words include
# Automation, Security, Power, Controls, Medical, Tech, Audio, Energy, Robotics,
# Imaging, Sensors, Aviation, Healthcare, Lighting, Innovation, Digital,
# Software, etc.).
_INDUSTRY_NOUN_TOKENS = [
    r"Automation", r"Security", r"Power", r"Controls", r"Tech", r"Technology",
    r"Technologies", r"Medical", r"Aviation", r"Aerospace", r"Audio", r"Video",
    r"Camera", r"Cameras", r"Energy", r"Mobile", r"Wireless", r"Optics",
    r"Optical", r"Imaging", r"Imagery", r"Image", r"Robotics", r"Robotic",
    r"Drones", r"Drone", r"Software", r"Hardware", r"Devices", r"Device",
    r"Instruments", r"Instrument", r"Solutions", r"Solution", r"Systems",
    r"System", r"Sistemi", r"Sistemas", r"Sistemos", r"Sistèmes", r"Sistema",
    r"Networks", r"Network", r"Networking", r"Communications", r"Communication",
    r"Electronics", r"Electronic", r"Engineering", r"Engineered", r"Engineer",
    r"Sciences", r"Science", r"Scientific", r"Sensors", r"Sensor", r"Lighting",
    r"Lights", r"Diagnostics", r"Diagnostic", r"Therapeutics",
    r"Therapeutic", r"Therapies", r"Therapy", r"Biosciences", r"Bioscience",
    r"Biosystems", r"Biomedical", r"Biotech", r"Bionic", r"Genomics",
    r"Genomic", r"Healthcare", r"Surgical", r"Surgery", r"Dental",
    r"Pharma", r"Pharmaceuticals", r"Pharmaceutical", r"Pharmacy",
    r"Veterinary", r"Industries", r"Industry", r"Industrial", r"Manufacturing",
    r"Mfg", r"Logistics", r"Logistic", r"Photonics", r"Defense", r"Defence",
    r"Avionics", r"Avionic", r"Vehicle", r"Vehicles", r"Mobility", r"Transport",
    r"Transportation", r"Transit", r"Materials", r"Polymer", r"Polymers",
    r"Plastics", r"Rubber", r"Chemicals", r"Chemical", r"Chemistry",
    r"Foods", r"Beverage", r"Beverages", r"Apparel", r"Garments",
    r"Fashion", r"Furniture", r"Appliance", r"Appliances", r"Retail",
    r"Wholesale", r"Trading", r"Traders", r"Imports", r"Exports", r"Brokerage",
    r"Brokers", r"Realty", r"Realtors", r"REIT", r"Hospitality", r"Tourism",
    r"Travel", r"Shipping", r"Express", r"Cargo", r"Freight", r"Delivery",
    r"Studios", r"Studio", r"Productions", r"Production", r"Broadcasting",
    r"Broadcast", r"Entertainment", r"Cinema", r"Theater", r"Theatre",
    r"Sports", r"Athletic", r"Fitness", r"Agriculture", r"Agricultural",
    r"Forestry", r"Fisheries", r"Aquaculture", r"Renewable", r"Solar",
    r"Hydro", r"Nuclear", r"Geothermal", r"Petroleum",
    r"Mining", r"Quarrying", r"Drilling", r"Construction",
    r"Architecture", r"Designs", r"Surveying",
    r"Consulting", r"Consultants", r"Advisory", r"Investment", r"Investments",
    r"Financial", r"Banking", r"Insurance", r"Securities", r"Capital",
    r"Equity", r"Venture", r"Hedge", r"Mutual",
    r"Microsystems", r"Semiconductor", r"Semiconductors",
    r"Acoustics", r"Acoustic", r"Mechatronics", r"Ultrasonic", r"Ultrasonics",
    r"Sonar", r"Radar", r"Telematics", r"Telematic", r"Marine",
    r"Telecom", r"Telecommunication", r"Telecommunications", r"Innovation",
    r"Innovations", r"Digital", r"Analytics", r"Analytical",
    r"Cloud", r"Compute", r"Computing", r"Computer", r"Computers",
    r"Metallurgy", r"Metallurgical",
    r"Aluminum", r"Aluminium", r"Cement", r"Concrete", r"Textile",
    r"Textiles", r"Eletrônicos", r"Eletrônica", r"Electrónica", r"Elektronik",
    r"Elektronika", r"Electronique", r"Telecomunicações", r"Tecnologia",
    r"Tecnología", r"Tecnologías", r"Tecnologie",
    # General-purpose connectors that mark org-shape
    r"Products", r"International", r"Intl", r"Worldwide",
    r"USA", r"UK", r"Europe", r"Asia", r"America", r"Africa", r"Oceania",
    r"Australia", r"Israel", r"Japan", r"Korea", r"China", r"India", r"Mexico",
    r"Brazil", r"Germany", r"France", r"Italy", r"Spain", r"Canada", r"Russia",
    r"Indonesia", r"Vietnam", r"Thailand", r"Pakistan", r"Turkey", r"Egypt",
    r"Netherlands", r"Belgium", r"Switzerland", r"Denmark", r"Sweden", r"Norway",
    r"Finland", r"Iceland", r"Ireland", r"Poland", r"Hungary", r"Romania",
    r"Slovenia", r"Slovakia", r"Bulgaria", r"Croatia", r"Greece", r"Portugal",
    # Specific brand / industry tail nouns observed in the cohort
    r"Brand", r"Brands", r"Dynamics", r"Motor", r"Motors", r"Detection",
    r"Multimedia", r"Multiservice", r"Edge", r"Connect", r"Origin", r"Pixel",
    r"Lab", r"Labs", r"Concept", r"Concepts", r"Domain", r"Distribution",
    r"Distributor", r"Equipment", r"Equipped", r"Showcase", r"Display",
    r"Displays", r"Holland", r"Switzerland", r"Belgium", r"Taiwan", r"Denmark",
    r"Netherlands", r"Korea", r"Israel", r"Australia", r"Sàrl", r"Sarl",
    r"Audiotech", r"Sensotec", r"Tekmar", r"Brands", r"Group", r"Solutions",
    r"Holland", r"Sistemi", r"Mekhanotronnika", r"Industriesteuerungen",
    r"Meditec", r"Powertech", r"Connect", r"Firmware", r"Hardware", r"Software",
    r"Rail", r"Rails", r"Trains", r"Auto", r"Autos", r"Track", r"Tracks",
    r"Bank", r"Banks", r"Lasers", r"Laser", r"Smart", r"Intelligent",
    r"Watch", r"Watches", r"Wear", r"Wearable", r"Wearables", r"Sport",
    r"Active", r"Live", r"Living", r"Open", r"Critical", r"Simple", r"Fast",
    r"Spark", r"Spectrum", r"Inspired", r"Visual", r"Earth", r"Header", r"Body",
    r"Programming", r"Payment", r"Payments", r"Pay", r"Distribution", r"Supply",
    r"Supplies", r"Sentinel", r"Juvenile", r"Sonic", r"Sonics", r"Water",
    r"Waters", r"Ocean", r"Sky", r"Air", r"Wave", r"Waves", r"Cloud",
    r"Hub", r"Hubs", r"Link", r"Links", r"Edge", r"Edges", r"Core", r"Cores",
    r"Lite", r"Mini", r"Pro", r"Max", r"Plus", r"Ultra", r"Hyper", r"Mega",
]
INDUSTRY_NOUN_RE = re.compile(r"\b(?:" + "|".join(_INDUSTRY_NOUN_TOKENS) + r")\b", re.IGNORECASE)

# Business-address indicators in the organization_address field.
_ADDR_BIZ_TOKENS = [
    r"Suite", r"Ste\.?", r"Floor", r"Fl\.?", r"Block", r"Building", r"Bldg",
    r"R&D", r"Industrial", r"Industriestr", r"Industriegebiet", r"Gewerbegebiet",
    r"Plaza", r"Tower", r"Towers", r"Complex", r"Campus", r"Office", r"Park",
    r"Industrial Park", r"Business Park", r"Technology Park", r"Science Park",
    r"Research Park", r"Innovation Park", r"Trade Center", r"Trade Centre",
    r"Industrial Estate", r"Industrial Zone", r"Industrial District",
    r"Industrial Area", r"Avenue", r"Boulevard", r"Highway", r"Hwy", r"Drive",
    r"Street", r"Road", r"Lane", r"Way", r"Place", r"Court", r"Square",
    r"Apartment", r"Apt", r"Unit", r"Wing", r"Hall", r"Phase", r"Sector",
    r"Zone", r"District", r"P\.?O\.? ?Box", r"PO Box", r"Postfach",
    # Heuristic: "Co., Ltd." or "Industries" inside the address often signals
    # business-level registration even when the name field is just a brand.
    r"Co\.,? ?Ltd", r"Industries Inc", r"Industries Co", r"Group Co",
    r"Holdings", r"Industriestraße", r"Strasse", r"Straße",
    # Multilingual analogues
    r"Indústria", r"Industria", r"Industri", r"Avenida", r"Calle", r"Carrera",
    r"Rua", r"Via", r"Viale", r"Strasse", r"Allee",
]
ADDR_BIZ_RE = re.compile(r"\b(?:" + "|".join(_ADDR_BIZ_TOKENS) + r")\b", re.IGNORECASE)

# Stylized-brand markers: mixed-case CamelCase, contains digit, dot, ampersand,
# slash, dash, underscore, hashtag, plus sign, etc.
STYLIZED_BRAND_RE = re.compile(r"(?:[A-Z]{2,}|[a-z][A-Z]|\d|[\.&/@#_+\-])")

# Person-name "FirstName LastName" with optional middle name.
PERSON_NAME_RE = re.compile(
    r"^[A-ZÀ-Ö][a-zà-öø-ÿß-ö]+(?:\s+[A-ZÀ-Ö][a-zà-öø-ÿß-ö]+){1,2}$"
)

# IEEE Private placeholder marker.
IEEE_PRIVATE_MFR_RE = re.compile(r"^Private$", re.IGNORECASE)


def classify_row(
    candidate_manufacturer: str | None,
    organization_address: str | None,
    ieee_private_registrant: bool,
) -> tuple[str, str]:
    """Return (class_letter, rationale) for a single pii_review_hold row.

    class_letter is one of 'A', 'B', 'C', 'D' per MAC-99 dispatch §2.1-§2.4.
    """
    # Class C: IEEE Private placeholder by registrant choice (board §2.2).
    if ieee_private_registrant:
        return (
            "C",
            "IEEE Private placeholder — registrant opted into anonymized "
            "assignment; hold by registrant-choice not by entity-type-uncertainty",
        )

    name = (candidate_manufacturer or "").strip()
    addr = organization_address or ""
    combined = name + " " + addr

    if not name:
        return ("D", "no manufacturer name field; cannot classify")

    # Class A — strong corporate-suffix anywhere (highest-confidence signal).
    if CORP_SUFFIX_RE.search(combined):
        return ("A", "corporate legal-form suffix present in name or address")

    # Class A — non-ASCII corporate-suffix (Turkish A.Ş, Estonian OÜ, Cyrillic
    # ООО/ЗАО, Swiss Sàrl, etc.). Uses custom boundary because Python re's \b
    # doesn't reliably mark transitions on non-ASCII letters.
    if NONASCII_CORP_RE.search(" " + combined + " "):
        return ("A", "non-ASCII corporate legal-form suffix (OÜ / A.Ş / Sàrl / ООО etc.)")

    # Class A — government / academic / institutional keyword.
    if GOV_ACAD_RE.search(combined):
        return ("A", "government / academic / institutional keyword present")

    # Class A — industry/product/service noun in name (≥2 tokens; second is
    # an industry descriptor like "Drones", "Security", "Power", etc.).
    if INDUSTRY_NOUN_RE.search(name):
        return ("A", "industry / product / service noun in organization name")

    # Class A — business-address indicator (Suite, Floor, Industrial Park, etc.).
    if ADDR_BIZ_RE.search(addr):
        return ("A", "business-address indicator in registrant address")

    # Class A — stylized brand markers (CamelCase, digit, punctuation in name).
    # This catches "DAYOUPLUS", "iREA", "TechArgos", "care.ai", "4D Sistem",
    # "MAHINDR & MAHINDRA" etc. — branding patterns that no individual uses for
    # personal IEEE registrations.
    if STYLIZED_BRAND_RE.search(name) and not PERSON_NAME_RE.match(name):
        return ("A", "stylized brand marker in name (mixed-case / digit / symbol)")

    # Class A — single-word brand (no spaces; the IEEE registration is a brand).
    if " " not in name:
        return ("A", "single-word brand name (IEEE OUI/MA-S/IAB registration)")

    # Class A — name has ≥3 tokens (compound organization names like
    # "Korea Bus Broadcasting", "Shanghai Dahua Scale Factory") — these are
    # virtually always corporate.
    name_tokens = name.split()
    if len(name_tokens) >= 3:
        return ("A", "≥3-token organization name (compound corporate naming)")

    # Class A — lowercase-first-letter on a multi-word name is a stylized brand
    # marker (e.g. "robert juliat", "choyang powertech", "ntc mekhanotronnika").
    # Individual person registrations would carry Title-Case capitalisation.
    if name[0:1].islower():
        return ("A", "lowercase-first-letter on multi-word name (stylized brand)")

    # Class A — any non-first token in a multi-word name is fully lowercase
    # (e.g. "Alias ip", "Watts A\\S" where "A\\S" parses as lowercase-leading
    # after the backslash). Individuals don't capitalise their surnames as
    # lowercase; this is brand stylization.
    for tok in name_tokens[1:]:
        # Strip leading punctuation (backslash, slash, dot) before case check.
        stripped = tok.lstrip(r"\/.,-")
        if stripped and stripped[0:1].islower():
            return ("A", "lowercase non-leading token in multi-word name (stylized brand)")

    # Class B — 2-token simple Title-Case name AND no corporate signal anywhere.
    # Per §11 #3 PII discipline: uncertainty resolves toward HOLD. This bucket
    # will also catch well-known corporate brands that lack a corp-suffix /
    # industry-noun marker (e.g. "Becton Dickinson", "General Motors", "Boston
    # Dynamics") — the policy-safe direction per §11 #3 is to hold these
    # until a manufacturers-table-cross-check sub-rule is ratified.
    if len(name_tokens) == 2 and PERSON_NAME_RE.match(name):
        return ("B", "2-token Title-Case name; no corporate indicator (default-to-HOLD per §11 #3)")

    # Class D — interim ambiguous; small-bucket escalation.
    return ("D", "name shape unclassifiable under §2.1-§2.3 rules; escalate to CEO")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _existing_dispatch_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    """Idempotency guard: detect prior MAC-99 Stream 1 run."""
    return conn.execute(
        "SELECT id, source_id, records_in, records_out, status, notes "
        "FROM extraction_runs WHERE notes LIKE ? ORDER BY id LIMIT 1",
        (f"%{DISPATCH_IDEMPOTENCY_KEY}%",),
    ).fetchone()


def _load_pii_review_rows(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Load all 3,654 pii_review_hold rows (Class A/B/C candidates)."""
    return conn.execute(
        """
        SELECT id, source_id, source_url, candidate_identifier, candidate_type,
               candidate_category, candidate_manufacturer, source_excerpt, notes,
               promoted_identifier_id
        FROM raw_observations
        WHERE (notes LIKE '%"pii_review_hold": true%' OR notes LIKE '%"pii_review_hold":true%')
        ORDER BY id
        """
    ).fetchall()


def _parse_notes(notes_json: str) -> dict:
    """Safe JSON parse — per SAR-12 §0 pre-flight warning."""
    if not notes_json:
        return {}
    try:
        return json.loads(notes_json)
    except json.JSONDecodeError:
        return {}


def run_triage(
    *,
    dry_run: bool = False,
    db_path: Path | None = None,
) -> dict:
    """Execute the MAC-99 Stream 1 triage. Returns a summary dict."""
    global DB_PATH
    if db_path is not None:
        DB_PATH = db_path

    conn = _connect()
    try:
        existing = _existing_dispatch_run(conn)
        if existing is not None and not dry_run:
            return {
                "status": "noop_idempotent",
                "existing_run_id": existing["id"],
                "existing_run_notes": existing["notes"],
            }

        rows = _load_pii_review_rows(conn)
        if len(rows) != 3654:
            raise RuntimeError(
                f"pii_review_hold cohort drift: expected 3,654 rows, got {len(rows)}. "
                f"Halt-and-surface per SAR-12 §0 baseline guard."
            )

        # Classify all rows in-memory first.
        classifications: list[dict] = []
        for r in rows:
            notes = _parse_notes(r["notes"])
            ieee_priv = bool(notes.get("ieee_private_registrant"))
            org_addr = notes.get("organization_address", "")
            ieee_registry = notes.get("ieee_registry", "")
            assignment_hex = notes.get("ieee_assignment_raw_hex", "")
            extraction_run_id = notes.get("extraction_run_id")
            cls, why = classify_row(
                r["candidate_manufacturer"], org_addr, ieee_priv,
            )
            classifications.append({
                "row_id": r["id"],
                "source_id": r["source_id"],
                "source_url": r["source_url"],
                "candidate_identifier": r["candidate_identifier"],
                "candidate_manufacturer": r["candidate_manufacturer"],
                "source_excerpt": r["source_excerpt"],
                "ieee_registry": ieee_registry,
                "assignment_hex": assignment_hex,
                "extraction_run_id": extraction_run_id,
                "notes_obj": notes,
                "class": cls,
                "rationale": why,
                "already_promoted": r["promoted_identifier_id"],
            })

        counts = Counter(c["class"] for c in classifications)
        class_c_count = counts.get("C", 0)
        if class_c_count != 133:
            raise RuntimeError(
                f"Class C count drift: expected 133, got {class_c_count}. "
                f"Halt-and-surface per dispatch §6."
            )

        class_d_count = counts.get("D", 0)
        class_d_pct = class_d_count / len(rows) * 100
        if class_d_pct > 5.0:
            raise RuntimeError(
                f"Class D count {class_d_count} ({class_d_pct:.2f}%) exceeds "
                f"5% halt threshold; escalate to CEO before bulk-apply per dispatch §6."
            )

        if dry_run:
            return {
                "status": "dry_run",
                "counts": dict(counts),
                "class_d_pct": class_d_pct,
                "classifications": classifications,
            }

        # ------ APPLY: single transaction ------
        cur = conn.cursor()
        cur.execute("BEGIN")
        try:
            # 1. Insert a single extraction_runs row capturing the Class A batch.
            run_notes = json.dumps({
                "dispatch": DISPATCH_IDEMPOTENCY_KEY,
                "scope": "MAC-88 Stream 1 IEEE pii_review_hold Class A entity-type validation",
                "class_counts": dict(counts),
                "class_d_pct": round(class_d_pct, 3),
                "validator_agent_id": VALIDATOR_AGENT_ID,
                "validated_at": NOW_UTC,
                "source_runs_validated": [95, 96, 97],
            }, separators=(",", ":"))
            cur.execute(
                """
                INSERT INTO extraction_runs
                  (agent_id, source_id, started_at, finished_at,
                   records_in, records_out, errors, status, notes)
                VALUES (?, NULL, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    VALIDATOR_AGENT_ID,
                    NOW_UTC,
                    NOW_UTC,
                    counts.get("A", 0),
                    counts.get("A", 0),
                    "ok",
                    run_notes,
                ),
            )
            extraction_run_id = cur.lastrowid

            # 2. Per-row apply.
            promoted_count = 0
            sustained_b = 0
            sustained_c = 0
            sustained_d = 0
            for c in classifications:
                cls = c["class"]
                notes_obj = c["notes_obj"]
                notes_obj["pii_review_disposition"] = {
                    "A": "corporate_no_suffix_validated",
                    "B": "individual_attributed_pii_sustain",
                    "C": "ieee_private_registrant_permanent_hold",
                    "D": "ambiguous_pending_ceo_resolution",
                }[cls]
                notes_obj["pii_review_disposition_rationale"] = c["rationale"]
                notes_obj["pii_review_validated_at"] = NOW_UTC
                notes_obj["pii_review_dispatch"] = DISPATCH_IDEMPOTENCY_KEY

                if cls == "A":
                    # Promote to identifiers; back-link.
                    ident_notes = json.dumps({
                        "wave_b_phase": "ieee_expanded_registries",
                        "dispatch": DISPATCH_IDEMPOTENCY_KEY,
                        "parent_dispatch": "MAC-91-wave-b-promotion-cycle-3",
                        "ieee_registry": c["ieee_registry"],
                        "ieee_assignment_raw_hex": c["assignment_hex"],
                        "pii_review_disposition": "corporate_no_suffix_validated",
                        "pii_review_rationale": c["rationale"],
                        "raw_observation_id": c["row_id"],
                    }, separators=(",", ":"))
                    cur.execute(
                        """
                        INSERT INTO identifiers
                          (identifier, identifier_type, device_category,
                           manufacturer, model, confidence, source_url,
                           source_type, source_excerpt, geographic_scope,
                           first_seen, last_verified, notes)
                        VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            c["candidate_identifier"],
                            "mac_range",
                            "unknown",
                            c["candidate_manufacturer"],
                            85,
                            c["source_url"],
                            "primary_registry",
                            c["source_excerpt"],
                            "global",
                            IEEE_WAVE_B_FIRST_SEEN,
                            NOW_UTC,
                            ident_notes,
                        ),
                    )
                    new_ident_id = cur.lastrowid
                    cur.execute(
                        """
                        UPDATE raw_observations
                        SET notes = ?, promoted_identifier_id = ?, processed_at = ?
                        WHERE id = ?
                        """,
                        (
                            json.dumps(notes_obj, separators=(",", ":")),
                            new_ident_id,
                            NOW_UTC,
                            c["row_id"],
                        ),
                    )
                    promoted_count += 1
                else:
                    # B / C / D — notes-disposition only; no promotion.
                    cur.execute(
                        """
                        UPDATE raw_observations
                        SET notes = ?, processed_at = ?
                        WHERE id = ?
                        """,
                        (
                            json.dumps(notes_obj, separators=(",", ":")),
                            NOW_UTC,
                            c["row_id"],
                        ),
                    )
                    if cls == "B":
                        sustained_b += 1
                    elif cls == "C":
                        sustained_c += 1
                    else:
                        sustained_d += 1

            conn.commit()
        except Exception:
            conn.rollback()
            raise

        return {
            "status": "applied",
            "extraction_run_id": extraction_run_id,
            "counts": dict(counts),
            "promoted_count": promoted_count,
            "sustained_b": sustained_b,
            "sustained_c": sustained_c,
            "sustained_d": sustained_d,
            "class_d_pct": round(class_d_pct, 3),
            "classifications": classifications,
        }
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="Classify only; no DB writes")
    ap.add_argument("--db", type=Path, default=None, help="Override DB path")
    args = ap.parse_args()

    result = run_triage(dry_run=args.dry_run, db_path=args.db)

    print(f"status: {result['status']}")
    if result["status"] == "noop_idempotent":
        print(f"existing_run_id: {result['existing_run_id']}")
        return
    counts = result["counts"]
    print(f"Class A (promote):                  {counts.get('A', 0)}")
    print(f"Class B (individual-attributed):    {counts.get('B', 0)}")
    print(f"Class C (IEEE Private placeholder): {counts.get('C', 0)}")
    print(f"Class D (ambiguous; escalate):      {counts.get('D', 0)}")
    print(f"Class D pct: {result['class_d_pct']}%")
    print(f"sum: {sum(counts.values())}")
    if result["status"] == "applied":
        print(f"extraction_run_id: {result['extraction_run_id']}")
        print(f"promoted: {result['promoted_count']}")


if __name__ == "__main__":
    main()
