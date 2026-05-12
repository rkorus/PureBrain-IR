#!/usr/bin/env python3
"""
PureBrain IR — Allocator 13F Fetcher (Sprint 3A)

Fetches 13F-HR filings from SEC EDGAR for pension funds, endowments, and SWFs.
Populates holdings_13f.db with allocator-type investors and their holdings.

These are the ALLOCATORS that companies need — the LPs, not the managers.

Usage:
    python3 fetch_allocators_13f.py              # Fetch all allocators
    python3 fetch_allocators_13f.py --cik 919079 # Fetch single allocator
    python3 fetch_allocators_13f.py --list       # List allocator CIKs
"""

import json
import sqlite3
import time
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
HOLDINGS_DB = SCRIPT_DIR / "holdings_13f.db"
ADV_DB = SCRIPT_DIR / "purebrain_ir.db"

SEC_HEADERS = {
    "User-Agent": "PureBrain IR Research keel@agentmail.to",
    "Accept": "application/json",
}
RATE_LIMIT_DELAY = 0.12  # SEC allows 10 req/sec

# ── Verified Allocator CIKs (confirmed on SEC EDGAR) ──

ALLOCATOR_FILERS = [
    # US Pension Funds
    {"cik": "919079", "name": "California Public Employees Retirement System (CalPERS)", "type": "pension", "country": "US", "state": "CA"},
    {"cik": "1081019", "name": "California State Teachers Retirement System (CalSTRS)", "type": "pension", "country": "US", "state": "CA"},
    {"cik": "810265", "name": "New York State Common Retirement Fund", "type": "pension", "country": "US", "state": "NY"},
    {"cik": "796848", "name": "Teacher Retirement System of Texas", "type": "pension", "country": "US", "state": "TX"},
    {"cik": "854157", "name": "State of Wisconsin Investment Board", "type": "pension", "country": "US", "state": "WI"},
    {"cik": "938076", "name": "State Board of Administration of Florida", "type": "pension", "country": "US", "state": "FL"},
    {"cik": "1083190", "name": "Pennsylvania Public School Employees Retirement System", "type": "pension", "country": "US", "state": "PA"},
    {"cik": "762152", "name": "State of Michigan Retirement System", "type": "pension", "country": "US", "state": "MI"},
    {"cik": "1107314", "name": "Oregon Public Employees Retirement Fund", "type": "pension", "country": "US", "state": "OR"},
    {"cik": "943712", "name": "Washington State Investment Board", "type": "pension", "country": "US", "state": "WA"},
    {"cik": "1587973", "name": "State of Tennessee Treasury Department", "type": "pension", "country": "US", "state": "TN"},
    {"cik": "1795552", "name": "Maryland State Retirement and Pension System", "type": "pension", "country": "US", "state": "MD"},
    {"cik": "1584686", "name": "Kentucky Retirement Systems", "type": "pension", "country": "US", "state": "KY"},

    # Endowments
    {"cik": "938582", "name": "Yale University", "type": "endowment", "country": "US", "state": "CT"},

    # Canadian Pension/Sovereign
    {"cik": "1283718", "name": "Canada Pension Plan Investment Board (CPPIB)", "type": "pension", "country": "CA", "state": None},
    {"cik": "937567", "name": "Ontario Teachers Pension Plan Board", "type": "pension", "country": "CA", "state": None},
    {"cik": "1396318", "name": "Public Sector Pension Investment Board (PSP)", "type": "pension", "country": "CA", "state": None},
    {"cik": "1228242", "name": "British Columbia Investment Management Corp", "type": "pension", "country": "CA", "state": None},
    {"cik": "898286", "name": "Caisse de Depot et Placement du Quebec", "type": "pension", "country": "CA", "state": None},

    # Sovereign Wealth Funds
    {"cik": "1374170", "name": "Norges Bank (Government Pension Fund of Norway)", "type": "sovereign_wealth", "country": "NO", "state": None},
    {"cik": "1021944", "name": "Temasek Holdings (Private) Ltd", "type": "sovereign_wealth", "country": "SG", "state": None},
]


def _sec_get(url: str) -> dict:
    """Make a rate-limited GET request to SEC EDGAR."""
    req = urllib.request.Request(url, headers=SEC_HEADERS)
    resp = urllib.request.urlopen(req)
    time.sleep(RATE_LIMIT_DELAY)
    return json.loads(resp.read())


def _sec_get_raw(url: str) -> bytes:
    """Make a rate-limited GET request returning raw bytes."""
    req = urllib.request.Request(url, headers=SEC_HEADERS)
    resp = urllib.request.urlopen(req)
    time.sleep(RATE_LIMIT_DELAY)
    return resp.read()


def get_latest_13f_filing(cik: str, max_filings: int = 4) -> list[dict]:
    """
    Get the most recent 13F-HR filings for a CIK.
    Returns list of {accession_number, filing_date, period_of_report, primary_doc_url}.
    """
    padded_cik = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{padded_cik}.json"

    try:
        data = _sec_get(url)
    except Exception as e:
        print(f"    ERROR fetching submissions for CIK {cik}: {e}")
        return []

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])
    report_dates = recent.get("reportDate", [])

    filings = []
    for i, form in enumerate(forms):
        if form == "13F-HR" and len(filings) < max_filings:
            acc = accessions[i].replace("-", "")
            acc_dashed = accessions[i]
            filings.append({
                "accession_number": acc_dashed,
                "filing_date": dates[i] if i < len(dates) else "",
                "period_of_report": report_dates[i] if i < len(report_dates) else "",
                "primary_doc": primary_docs[i] if i < len(primary_docs) else "",
                "cik_padded": padded_cik,
                "acc_nodash": acc,
            })

    return filings


def find_infotable_url(cik: str, acc_nodash: str, acc_dashed: str) -> Optional[str]:
    """Find the information table XML URL from the filing index page."""
    import re

    cik_num = str(int(cik))  # Strip leading zeros for URL
    base = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_nodash}"

    # Use the index.htm page which reliably exists
    index_url = f"{base}/{acc_dashed}-index.htm"
    try:
        req = urllib.request.Request(index_url, headers=SEC_HEADERS)
        resp = urllib.request.urlopen(req)
        time.sleep(RATE_LIMIT_DELAY)
        content = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        # Fallback: try directory listing
        try:
            req = urllib.request.Request(f"{base}/", headers=SEC_HEADERS)
            resp = urllib.request.urlopen(req)
            time.sleep(RATE_LIMIT_DELAY)
            content = resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"    ERROR fetching filing index: {e}")
            return None

    # Extract ALL XML file links from the page
    all_xml = re.findall(r'href="([^"]*\.xml)"', content, re.IGNORECASE)

    # Filter out XSL-wrapped versions (these are HTML renderings, not raw XML)
    raw_xml = [link for link in all_xml if "xsl" not in link.lower()]

    def _full_url(link):
        if link.startswith("/"):
            return f"https://www.sec.gov{link}"
        if link.startswith("http"):
            return link
        return f"{base}/{link}"

    # Priority 1: filename contains "infotable"
    for link in raw_xml:
        if "infotable" in link.lower():
            return _full_url(link)

    # Priority 2: any non-primary XML (the 13F info table)
    for link in raw_xml:
        if "primary" not in link.lower():
            return _full_url(link)

    # Priority 3: if only XSL versions exist, try the raw one behind it
    # XSL links look like: xslForm13F_X02/filename.xml — the raw is just filename.xml
    for link in all_xml:
        if "xsl" in link.lower() and "primary" not in link.lower():
            # Extract just the filename
            parts = link.split("/")
            filename = parts[-1]
            return f"{base}/{filename}"

    return None


def parse_13f_infotable(xml_data: bytes) -> list[dict]:
    """Parse 13F information table XML into holdings records."""
    holdings = []

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        # Try removing BOM or encoding issues
        text = xml_data.decode("utf-8", errors="ignore")
        if text.startswith("\ufeff"):
            text = text[1:]
        try:
            root = ET.fromstring(text.encode("utf-8"))
        except ET.ParseError as e:
            print(f"    XML parse error: {e}")
            return []

    # Detect namespace from root tag
    ns = ""
    if "}" in root.tag:
        ns = root.tag.split("}")[0] + "}"

    # Find all infoTable entries using namespace-aware findall
    entries = root.findall(f"{ns}infoTable")

    for entry in entries:
        holding = {}

        for child in entry:
            tag_name = child.tag.split("}")[-1].lower() if "}" in child.tag else child.tag.lower()

            if tag_name == "nameofissuer":
                holding["company_name"] = (child.text or "").strip()
            elif tag_name == "titleofclass":
                holding["title_of_class"] = (child.text or "").strip()
            elif tag_name == "cusip":
                holding["cusip"] = (child.text or "").strip()
            elif tag_name == "value":
                try:
                    holding["market_value"] = float(child.text or 0)
                except (ValueError, TypeError):
                    holding["market_value"] = 0.0
            elif "shrsorprnamt" in tag_name:
                for sub in child:
                    sub_tag = sub.tag.split("}")[-1].lower() if "}" in sub.tag else sub.tag.lower()
                    if sub_tag == "sshprnamt":
                        try:
                            holding["shares"] = int(float(sub.text or 0))
                        except (ValueError, TypeError):
                            holding["shares"] = 0
                    elif sub_tag == "sshprnamttype":
                        holding["shares_type"] = (sub.text or "").strip()
            elif tag_name == "investmentdiscretion":
                holding["investment_discretion"] = (child.text or "").strip()

        if holding.get("cusip") or holding.get("company_name"):
            holdings.append(holding)

    return holdings


def _ticker_from_cusip(cusip: str, holdings_conn: sqlite3.Connection) -> Optional[str]:
    """Try to find ticker from CUSIP in existing holdings data."""
    if not cusip:
        return None
    row = holdings_conn.execute(
        "SELECT ticker FROM ir_holdings WHERE cusip = ? AND ticker IS NOT NULL AND ticker != '' LIMIT 1",
        (cusip,),
    ).fetchone()
    return row[0] if row else None


def fetch_and_store_allocator(
    allocator: dict,
    conn: sqlite3.Connection,
    max_quarters: int = 4,
) -> dict:
    """Fetch 13F holdings for one allocator and store in DB."""
    cik = allocator["cik"]
    name = allocator["name"]
    alloc_type = allocator["type"]

    print(f"\n  Fetching {name} (CIK {cik})...")

    # Check if already in DB
    existing = conn.execute(
        "SELECT id FROM ir_investors WHERE cik = ?", (cik,)
    ).fetchone()

    if existing:
        investor_id = existing[0]
        print(f"    Already in DB (id={investor_id}), checking for new filings...")
    else:
        investor_id = str(uuid.uuid4())
        conn.execute("""
            INSERT INTO ir_investors (id, name, type, cik, hq_country, hq_state, data_source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'edgar_13f', datetime('now'))
        """, (investor_id, name, alloc_type, cik,
              allocator.get("country"), allocator.get("state")))
        conn.commit()
        print(f"    Created investor record (id={investor_id})")

    # Get latest filings
    filings = get_latest_13f_filing(cik, max_filings=max_quarters)
    if not filings:
        print(f"    No 13F-HR filings found")
        return {"name": name, "cik": cik, "holdings_added": 0, "filings_processed": 0}

    print(f"    Found {len(filings)} recent 13F-HR filings")

    total_added = 0
    filings_processed = 0

    for filing in filings:
        period = filing["period_of_report"]
        filing_date = filing["filing_date"]

        # Check if we already have this period
        existing_count = conn.execute(
            "SELECT COUNT(*) FROM ir_holdings WHERE investor_id = ? AND period_of_report = ?",
            (investor_id, period),
        ).fetchone()[0]

        if existing_count > 0:
            print(f"    Period {period}: already have {existing_count} holdings, skipping")
            continue

        # Find info table URL
        info_url = find_infotable_url(
            cik, filing["acc_nodash"], filing["accession_number"]
        )
        if not info_url:
            print(f"    Period {period}: could not find info table XML")
            continue

        # Download and parse
        try:
            xml_data = _sec_get_raw(info_url)
            holdings = parse_13f_infotable(xml_data)
        except Exception as e:
            print(f"    Period {period}: error downloading/parsing: {e}")
            continue

        if not holdings:
            print(f"    Period {period}: no holdings parsed from XML")
            continue

        # Insert holdings
        added = 0
        for h in holdings:
            ticker = _ticker_from_cusip(h.get("cusip", ""), conn)
            holding_id = str(uuid.uuid4())

            try:
                conn.execute("""
                    INSERT OR IGNORE INTO ir_holdings
                    (id, investor_id, ticker, company_name, cusip, shares, market_value,
                     filing_type, filing_date, period_of_report, investment_discretion,
                     source_url, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, '13F', ?, ?, ?, ?, datetime('now'))
                """, (
                    holding_id, investor_id, ticker,
                    h.get("company_name", ""), h.get("cusip", ""),
                    h.get("shares", 0), h.get("market_value", 0.0),
                    filing_date, period, h.get("investment_discretion", ""),
                    info_url,
                ))
                added += 1
            except Exception:
                pass

        conn.commit()
        total_added += added
        filings_processed += 1
        print(f"    Period {period}: {added} holdings added (filed {filing_date})")

    # Update investor record with latest filing info
    if filings:
        conn.execute("""
            UPDATE ir_investors SET last_13f_filed = ?, last_updated = datetime('now')
            WHERE id = ?
        """, (filings[0]["filing_date"], investor_id))
        conn.commit()

    return {
        "name": name,
        "cik": cik,
        "type": alloc_type,
        "investor_id": investor_id,
        "holdings_added": total_added,
        "filings_processed": filings_processed,
    }


def backfill_tickers(conn: sqlite3.Connection) -> int:
    """Try to fill in missing tickers from CUSIP cross-references."""
    # Find holdings with CUSIP but no ticker
    missing = conn.execute("""
        SELECT DISTINCT h1.cusip
        FROM ir_holdings h1
        WHERE (h1.ticker IS NULL OR h1.ticker = '')
        AND h1.cusip IS NOT NULL AND h1.cusip != ''
        AND EXISTS (
            SELECT 1 FROM ir_holdings h2
            WHERE h2.cusip = h1.cusip
            AND h2.ticker IS NOT NULL AND h2.ticker != ''
        )
    """).fetchall()

    updated = 0
    for (cusip,) in missing:
        ticker_row = conn.execute(
            "SELECT ticker FROM ir_holdings WHERE cusip = ? AND ticker IS NOT NULL AND ticker != '' LIMIT 1",
            (cusip,),
        ).fetchone()
        if ticker_row:
            conn.execute(
                "UPDATE ir_holdings SET ticker = ? WHERE cusip = ? AND (ticker IS NULL OR ticker = '')",
                (ticker_row[0], cusip),
            )
            updated += conn.execute("SELECT changes()").fetchone()[0]

    conn.commit()
    return updated


def fetch_all_allocators(db_path: Path = HOLDINGS_DB, max_quarters: int = 4):
    """Fetch 13F holdings for all configured allocators."""
    conn = sqlite3.connect(str(db_path))

    print(f"PureBrain IR — Allocator 13F Fetcher")
    print(f"{'='*60}")
    print(f"Target: {len(ALLOCATOR_FILERS)} allocators")
    print(f"Quarters per filer: up to {max_quarters}")
    print(f"Database: {db_path}")
    print(f"{'='*60}")

    results = []
    for allocator in ALLOCATOR_FILERS:
        try:
            result = fetch_and_store_allocator(allocator, conn, max_quarters)
            results.append(result)
        except Exception as e:
            print(f"  ERROR processing {allocator['name']}: {e}")
            results.append({
                "name": allocator["name"],
                "cik": allocator["cik"],
                "holdings_added": 0,
                "filings_processed": 0,
                "error": str(e),
            })

    # Backfill tickers
    print(f"\nBackfilling tickers from CUSIP cross-references...")
    backfilled = backfill_tickers(conn)
    print(f"  → {backfilled} holdings got ticker symbols from CUSIP matches")

    # Summary
    total_added = sum(r.get("holdings_added", 0) for r in results)
    total_filings = sum(r.get("filings_processed", 0) for r in results)
    allocators_with_data = sum(1 for r in results if r.get("holdings_added", 0) > 0)

    # Count totals in DB
    total_investors = conn.execute("SELECT COUNT(*) FROM ir_investors").fetchone()[0]
    total_holdings = conn.execute("SELECT COUNT(*) FROM ir_holdings").fetchone()[0]
    allocator_count = conn.execute(
        "SELECT COUNT(*) FROM ir_investors WHERE type IN ('pension', 'endowment', 'sovereign_wealth')"
    ).fetchone()[0]

    conn.close()

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Allocators processed: {len(results)}")
    print(f"Allocators with new data: {allocators_with_data}")
    print(f"Filings processed: {total_filings}")
    print(f"Holdings added: {total_added}")
    print(f"Tickers backfilled: {backfilled}")
    print(f"\nDatabase totals:")
    print(f"  Total investors: {total_investors} ({allocator_count} allocators)")
    print(f"  Total holdings: {total_holdings}")
    print(f"{'='*60}")

    return results


# ── CLI ──

if __name__ == "__main__":
    import sys

    if "--list" in sys.argv:
        print(f"{'CIK':<12} {'Type':<18} {'Name'}")
        print("-" * 80)
        for a in ALLOCATOR_FILERS:
            print(f"{a['cik']:<12} {a['type']:<18} {a['name']}")
        print(f"\nTotal: {len(ALLOCATOR_FILERS)} allocators")
        sys.exit(0)

    if "--cik" in sys.argv:
        idx = sys.argv.index("--cik")
        target_cik = sys.argv[idx + 1]
        alloc = next((a for a in ALLOCATOR_FILERS if a["cik"] == target_cik), None)
        if not alloc:
            print(f"CIK {target_cik} not in allocator list")
            sys.exit(1)
        conn = sqlite3.connect(str(HOLDINGS_DB))
        result = fetch_and_store_allocator(alloc, conn)
        conn.close()
        print(f"\nResult: {json.dumps(result, indent=2)}")
        sys.exit(0)

    max_q = 4
    if "--quarters" in sys.argv:
        idx = sys.argv.index("--quarters")
        max_q = int(sys.argv[idx + 1])

    fetch_all_allocators(max_quarters=max_q)
