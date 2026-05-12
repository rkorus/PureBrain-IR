"""SEC EDGAR API client for 13F filings.

Endpoints used:
  - https://data.sec.gov/submissions/CIK{cik}.json  (company filings index)
  - https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/  (filing documents)
  - https://efts.sec.gov/LATEST/search-index?forms=13F-HR  (full-text search)

Rate limit: 10 req/s. User-Agent required.
"""

import json
import os
import time
import re
import urllib.request
import urllib.error
from dataclasses import dataclass


USER_AGENT = "PureBrainIR/1.0 parallax.aiciv@gmail.com"
EDGAR_BASE = "https://data.sec.gov"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
EFTS_SEARCH = "https://efts.sec.gov/LATEST/search-index"

# Rate limiter: max 10 req/s
_last_request_time = 0.0


def _throttle():
    """Enforce 100ms minimum between requests (10 req/s)."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < 0.1:
        time.sleep(0.1 - elapsed)
    _last_request_time = time.time()


def _fetch(url: str, accept: str = "application/json") -> bytes:
    """Fetch URL with required User-Agent and rate limiting."""
    _throttle()
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": accept,
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(2)
            return _fetch(url, accept)
        raise


def _fetch_json(url: str) -> dict:
    return json.loads(_fetch(url))


@dataclass
class Filing13F:
    """Metadata for a single 13F-HR filing."""
    cik: str
    company_name: str
    accession_number: str  # e.g. "0000102909-25-000003"
    filing_date: str       # e.g. "2025-02-14"
    period_of_report: str  # e.g. "2024-12-31"
    primary_doc: str       # URL to primary document
    info_table_url: str | None  # URL to information table XML


def pad_cik(cik: str) -> str:
    """Pad CIK to 10 digits as required by EDGAR API."""
    return cik.zfill(10)


def get_company_filings(cik: str) -> dict:
    """Get all filings for a company from EDGAR submissions API."""
    padded = pad_cik(cik)
    url = f"{EDGAR_BASE}/submissions/CIK{padded}.json"
    return _fetch_json(url)


def extract_13f_filings(submissions: dict, max_filings: int = 20) -> list[Filing13F]:
    """Extract 13F-HR filings from submissions response.

    Returns most recent filings up to max_filings.
    """
    cik = str(submissions.get("cik", ""))
    company_name = submissions.get("name", "")

    filings = []
    recent = submissions.get("filings", {}).get("recent", {})

    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])
    periods = recent.get("reportDate", [])
    primary_docs = recent.get("primaryDocument", [])

    for i, form in enumerate(forms):
        if form not in ("13F-HR", "13F-HR/A"):
            continue
        if len(filings) >= max_filings:
            break

        accession = accessions[i]
        accession_path = accession.replace("-", "")
        primary_doc_name = primary_docs[i] if i < len(primary_docs) else ""

        filing = Filing13F(
            cik=cik,
            company_name=company_name,
            accession_number=accession,
            filing_date=dates[i] if i < len(dates) else "",
            period_of_report=periods[i] if i < len(periods) else "",
            primary_doc=f"{SEC_ARCHIVES}/{cik}/{accession_path}/{primary_doc_name}",
            info_table_url=None,  # resolved in get_info_table_url()
        )
        filings.append(filing)

    return filings


def get_filing_index(cik: str, accession: str) -> dict:
    """Get the filing index JSON to find the information table document."""
    accession_path = accession.replace("-", "")
    # EDGAR archives use raw CIK (no padding) and www.sec.gov
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_path}/index.json"
    return _fetch_json(url)


def find_info_table_url(cik: str, accession: str) -> str | None:
    """Find the information table XML URL within a 13F filing.

    The information table is the XML document containing all holdings.
    It's typically named something like 'infotable.xml' or similar.
    """
    try:
        index = get_filing_index(cik, accession)
    except Exception:
        return None

    items = index.get("directory", {}).get("item", [])
    accession_path = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_path}"

    # Look for information table XML by common naming patterns
    for item in items:
        name = item.get("name", "").lower()
        if any(pattern in name for pattern in ["infotable", "information_table", "13f_", "13f-"]):
            if name.endswith(".xml"):
                return f"{base}/{item['name']}"

    # Fallback: largest XML that's not primary_doc
    xml_files = [(item, int(item.get("size", "0") or "0"))
                 for item in items
                 if item.get("name", "").lower().endswith(".xml")
                 and "primary" not in item.get("name", "").lower()
                 and "index" not in item.get("name", "").lower()]
    if xml_files:
        xml_files.sort(key=lambda x: x[1], reverse=True)
        return f"{base}/{xml_files[0][0]['name']}"

    return None


def resolve_info_table(filing: Filing13F) -> Filing13F:
    """Resolve the information table URL for a filing."""
    if filing.info_table_url is None:
        filing.info_table_url = find_info_table_url(filing.cik, filing.accession_number)
    return filing


def download_info_table(filing: Filing13F) -> bytes | None:
    """Download the raw information table XML."""
    if not filing.info_table_url:
        filing = resolve_info_table(filing)
    if not filing.info_table_url:
        return None
    return _fetch(filing.info_table_url, accept="application/xml")


def search_13f_filers(query: str = "", start: int = 0, count: int = 40) -> list[dict]:
    """Search for 13F filers via EDGAR full-text search.

    Returns list of {cik, name, filing_date, accession} dicts.
    """
    params = f"?q={query}&forms=13F-HR&from={start}&size={count}"
    url = f"{EFTS_SEARCH}{params}"
    try:
        data = _fetch_json(url)
    except Exception:
        return []

    results = []
    for hit in data.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        results.append({
            "cik": source.get("entity_id", ""),
            "name": source.get("entity_name", ""),
            "filing_date": source.get("file_date", ""),
            "accession": source.get("file_num", ""),
        })
    return results


# --- Bulk filing discovery ---

# Major institutional filers for initial seed (CIK numbers)
SEED_FILERS = {
    "102909": "Vanguard Group",
    "2012383": "BlackRock",
    "1067983": "Berkshire Hathaway",
    "93751": "State Street",
    "19617": "JPMorgan Chase",
    "1037389": "Renaissance Technologies",
    "895421": "Morgan Stanley",
    "886982": "Goldman Sachs",
}


def get_seed_filers() -> dict[str, str]:
    """Return seed CIK→name mapping for initial pipeline run."""
    return SEED_FILERS
