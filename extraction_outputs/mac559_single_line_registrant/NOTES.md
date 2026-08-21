# MAC-559 single-line-registrant evidence pass — corrected integrity battery

**Worker:** SourceWorker (`9cf8ff12-53c3-4f83-837f-3142d8d1d151`) · correction run `a91705d9-d783-4f3c-b11d-76d2760437ea`
**Brief:** `operator_review/MAC-559/single_line_registrant_brief.md` (binding contract)
**Brief sha256:** `d09bb4eb2580eeb4daf4c68799233468b7b4cb6b31803621acdb8efd17d4279f`
**Authority:** [MAC-554](<TRACKER_URL>issues/MAC-554) comment `064f044c`
**HEAD at corrected battery:** `ceff54f366fef26d6c884b15fb0e859f0c185895`
**Issue-time DB sha256:** `73af91f6bf8405c13c692d6258530715817de8b83256b516aaa2c7e98828b731`
**Final canonical DB sha256:** `2fad9f2eb2bb602ebe6b6bf4111304add313f2295a7a35bdb953c71bd3b396d7` (stable before/after fresh read-only revalidation)

## Amended scope

The brief's apply-time correction narrows the active lane from six rows to the three TKH rows:

- `00:04:7e` — `TKH Security B.V.`
- `00:1e:d1` — `TKH Security B.V.`
- `00:06:73` — `TKH Security Solutions USA`

Mercury and Paxton were closed structurally by the correction and are intentionally absent from the
contracted outputs. The original six-row input remains byte-preserved; scoped set equality filters it
to the three identifiers above.

## Disposition

**All 3 scoped rows remain `HOLD_UNKNOWN` at inherited confidence 80.**

| identifier | registrant | Gate A | reason |
|---|---|---|---|
| `00:04:7e` | TKH Security B.V. | FAIL | primary material positively establishes a `cctv_camera` line and at least three `NONE`-mapped lines |
| `00:1e:d1` | TKH Security B.V. | FAIL | same registrant; the same positively observed mixed-line evidence applies at catalogue level |
| `00:06:73` | TKH Security Solutions USA | FAIL | no registrant-bound complete catalogue established; reachable `/us/` body names B.V., not the USA registrant |

`RECATEGORIZE=0`, `HOLD_UNKNOWN=3`. Because every scoped row fails Gate A,
`secondary.jsonl` is intentionally empty. Brief §3 forbids secondary evidence assembly for a
Gate-A-killed row.

## Files

| file | rows | bytes | sha256 |
|---|---:|---:|---|
| `adjudication.jsonl` | 3 | 4384 | `8e85a447b2f03bd0051c38f5c7b686c3fd4a631feaf65af4b789386aed9a20cf` |
| `screen.jsonl` | 3 | 5615 | `6734cb4cc20dfd564db17cd055d9ee31fe84f55a0953404a14fac49f0e713402` |
| `secondary.jsonl` | 0 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## §6.1 Set equality and JSON validity

Executed harness shape:

```python
scope = {"00:04:7e", "00:1e:d1", "00:06:73"}
scoped_input = [row for row in input_rows if row["identifier"] in scope]
assert len(scoped_input) == len(adjudication) == len(screen) == 3
assert {row["identifier"] for row in scoped_input} == {
    row["identifier"] for row in adjudication
} == {row["identifier"] for row in screen}
assert all(row["verdict"] == "HOLD_UNKNOWN" for row in adjudication)
assert secondary_text == ""
```

```text
scoped_input=3  adjudication=3  screen=3
unique=3/3/3  set_equal=True
VERDICTS: {'HOLD_UNKNOWN': 3}
adjudication json_valid: 3/3
screen json_valid: 3/3
secondary rows: 0 (intentionally empty)
notes is JSON object: 3/3
```

## §6.2 Input integrity

```text
operator_review/MAC-559/candidates_6.jsonl
bytes=4699
sha256=51a6f71dc9aecb7d9c1341e1eac53499dc7ffeb5f41789f0e09b8ce1dfde8573
brief_expected bytes=4699
brief_expected sha256=51a6f71dc9aecb7d9c1341e1eac53499dc7ffeb5f41789f0e09b8ce1dfde8573
match=True
scoped identifiers=00:04:7e,00:1e:d1,00:06:73
```

## §6.3 IEEE cite-faithfulness

```text
raw/ieee_oui/oui_20260728T213418Z.txt
bytes=6532568
sha256=a75d05b7a646d41eaf0623c1bcb5673052ccc8d535420a8b2c7150bf2ad9284e
00:04:7e exact=True  "00-04-7E   (hex)\t\tTKH Security B.V."
00:1e:d1 exact=True  "00-1E-D1   (hex)\t\tTKH Security B.V."
00:06:73 exact=True  "00-06-73   (hex)\t\tTKH Security Solutions USA"
exact=3/3
```

## §6.4 Vendor material and entity boundary

Nine Gate A excerpts were checked as contiguous strings against preserved response bodies. All nine
matched raw body bytes exactly.

```text
00:04:7e and 00:1e:d1 — TKH Security B.V. evidence repeated at registrant level:
  https://tkhsecurity.com/system-vdg-sense-video-management       status=200 bytes=192568 exact=True
    "VDG SENSE Video Management System - TKH Security"
  https://tkhsecurity.com/park-assist-solutions                    status=200 bytes=164444 exact=True
    "Parking Guidance Solutions - TKH Security"
  https://tkhsecurity.com/system-iprotect-access-control          status=200 bytes=210380 exact=True
    "IPROTECT Access Control System - TKH Security"
  https://tkhsecurity.com/system-apollo-asset-and-site-management  status=200 bytes=172858 exact=True
    "APOLLO Asset and Site Management System - TKH Security"

00:06:73 entity-boundary evidence:
  https://tkhsecurity.com/us/  status=200 bytes=151131 exact=True
    excerpt="TKH Security B.V."
    "TKH Security Solutions USA" present in body=False
```

The B.V. sources positively establish at least four observed product-line areas. This is **not** an
exhaustive-catalogue claim. Gate A fails because positive `NONE`-mapped lines exist; one such line is
sufficient.

The USA registrant is distinct under brief §4. Four plausible registrant-specific domains have
preserved DNS-failure captures:

```text
https://tkhsolutionsusa.com/      http_status=null bytes=0 error=[Errno -2] Name or service not known
https://www.tkhsolutionsusa.com/  http_status=null bytes=0 error=[Errno -2] Name or service not known
https://tkhsecurity.us/           http_status=null bytes=0 error=[Errno -2] Name or service not known
https://www.tkhsecurity.us/       http_status=null bytes=0 error=[Errno -2] Name or service not known
```

DNS-stage reproduction command executed during correction; no HTTP request was made because all four
names failed resolution:

```bash
.venv/bin/python - <<'PY'
import socket
from urllib.parse import urlsplit
urls = ('https://tkhsolutionsusa.com/', 'https://www.tkhsolutionsusa.com/',
        'https://tkhsecurity.us/', 'https://www.tkhsecurity.us/')
for url in urls:
    host = urlsplit(url).hostname
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        print(f'{url} http_status=null bytes=0 dns_error={error}')
    else:
        print(f'{url} DNS_RESOLVED addresses={addresses}; HTTP_NOT_ATTEMPTED')
PY
```

Fresh robots-gated HTTP capture command executed for `/us/`:

```bash
.venv/bin/python - <<'PY'
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib import robotparser
from urllib.request import Request, urlopen
user_agent = 'ArgusPublicSourceAudit/1.0'
timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out_dir = Path('raw/tkh_search') / timestamp
out_dir.mkdir()
def fetch(url, filename):
    request = Request(url, headers={'User-Agent': user_agent, 'Accept': 'text/html,text/plain;q=0.9,*/*;q=0.1'})
    with urlopen(request, timeout=30) as response:
        body = response.read()
        envelope = {
            'url': url,
            'final_url': response.geturl(),
            'ts': timestamp,
            'http_status': response.status,
            'content_type': response.headers.get('Content-Type'),
            'bytes': len(body),
            'sha256': hashlib.sha256(body).hexdigest(),
            'body': body.decode('utf-8', errors='replace'),
        }
    path = out_dir / filename
    path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path, envelope
robots_path, robots = fetch('https://tkhsecurity.com/robots.txt', 'tkhsecurity.com_robots.txt')
parser = robotparser.RobotFileParser()
parser.set_url(robots['url'])
parser.parse(robots['body'].splitlines())
allowed = parser.can_fetch(user_agent, 'https://tkhsecurity.com/us/')
print(f'robots path={robots_path} status={robots["http_status"]} bytes={robots["bytes"]} sha256={robots["sha256"]} allowed_us={allowed}')
if not allowed:
    raise SystemExit('robots.txt disallows /us/ for this user agent')
page_path, page = fetch('https://tkhsecurity.com/us/', 'tkhsecurity.com_us_.html')
print(f'page path={page_path} status={page["http_status"]} bytes={page["bytes"]} sha256={page["sha256"]} final_url={page["final_url"]}')
PY
```

```text
robots path=raw/tkh_search/20260729T002908Z/tkhsecurity.com_robots.txt status=200 bytes=275 sha256=1232c57eb93eea18246f693100e73275ddb5511bd2516511fd18b6b9174b9122 allowed_us=True
page path=raw/tkh_search/20260729T002908Z/tkhsecurity.com_us_.html status=200 bytes=151131 sha256=c0319032523429632651479476093deb1aeebed0915b424573eca0d730f72863 final_url=https://tkhsecurity.com/us/
```

Raw artifacts:

- `raw/tkh_search/20260728T233744Z/tkhsecurity.com_.html`
- `raw/tkh_search/20260728T233817Z/`
- `raw/tkh_search/20260728T233842Z/{tkhsolutionsusa.com_,www.tkhsolutionsusa.com_,tkhsecurity.us_,www.tkhsecurity.us_}.html`
- `raw/tkh_search/20260729T002908Z/{tkhsecurity.com_robots.txt,tkhsecurity.com_us_.html}`

Zero bot walls, zero 5xx, and no evasive access attempts were observed.

## §6.5 Net-new and DB immutability

Executed read-only SQL for each scoped identifier:

```sql
SELECT COUNT(*)
FROM identifiers
WHERE lower(identifier) = lower(?);

SELECT COUNT(*)
FROM identifiers
WHERE lower(replace(replace(identifier, ':', ''), '-', '')) = ?;
```

Connection used SQLite URI `file:db/argus.db?mode=ro` plus `PRAGMA query_only=ON`.

```text
00:04:7e exact=0 separator_normalized=0
00:1e:d1 exact=0 separator_normalized=0
00:06:73 exact=0 separator_normalized=0
DB sha256 BEFORE=2fad9f2eb2bb602ebe6b6bf4111304add313f2295a7a35bdb953c71bd3b396d7
DB sha256 AFTER =2fad9f2eb2bb602ebe6b6bf4111304add313f2295a7a35bdb953c71bd3b396d7
DB_UNCHANGED=True
```

The first final-battery attempt was discarded because an unrelated concurrent session replaced the
shared canonical DB during the run (`73af…` → `2fad…`). No process held the DB afterward. The query
above was rerun against the new canonical snapshot over a fresh two-second stable hash window; all
three scoped identifiers remained absent. This worker never opened the DB writable or restored the
other session's snapshot.

## §6.6 Derived fields

```text
00:04:7e manufacturer_drift=False proposed=unknown confidence=80 verdict=HOLD_UNKNOWN
00:1e:d1 manufacturer_drift=False proposed=unknown confidence=80 verdict=HOLD_UNKNOWN
00:06:73 manufacturer_drift=False proposed=unknown confidence=80 verdict=HOLD_UNKNOWN
```

Manufacturers are carried verbatim from the scoped input objects. No category or confidence increase
occurs.

## §6.7 HEAD-pinned feed reach

Classifier loaded from `git show HEAD:db/validation/export_lynceus.py`:

```text
HEAD=ceff54f366fef26d6c884b15fb0e859f0c185895
classifier bytes=99489
classifier sha256=01bf89b056bb2759262e1ba91be07a241a375a7954627cd4674a50b6944e6c83
original-run classifier sha256=01bf89b056bb2759262e1ba91be07a241a375a7954627cd4674a50b6944e6c83
byte_identical=True
AS-PROPOSED unknown@80: std=0/3 hc=0/3 (unknown_category)
COUNTERFACTUAL cctv_camera@65: std=3/3 hc=0/3 (high-confidence floor)
```

## §6.8 Notes and secondary guard

```text
adjudication rows=3/3 JSON objects
notes objects=3/3
required notes keys present=3/3
screen rows=3/3 JSON objects
secondary bytes=0 rows=0
```

The empty secondary file is intentional enforcement of brief §3 guard 4, not missing work.

## §6.9 Write scope

```text
DB write: none
migration: none
commit: none
push: none
tag: none
main-table promotion: none
```

Only the two issue-owned output directories were corrected. The shared checkout's unrelated dirty
files were not touched.

## Limitations recorded honestly

- The B.V. pages positively establish multiple observed lines but do not contain an affirmative
  statement that those lines exhaust the catalogue. Exhaustiveness is unnecessary to a Gate A FAIL
  once a `NONE`-mapped line is positively established.
- No registrant-bound public catalogue for `TKH Security Solutions USA` was established. The reachable
  `/us/` page is B.V. material and cannot be borrowed. The original inline helper text was not
  preserved, so it was superseded by the fresh robots-gated capture whose exact command, status,
  response byte count, hashes, and raw envelopes are preserved above.
- `secondary.jsonl` is empty because no row survives Gate A.

## Release fence

- Zero new rows enter the corpus.
- Zero shipped rows are mutated.
- Zero `ssid_pattern` rows are created.
- The lane remains non-blocking for v1.7.0.
