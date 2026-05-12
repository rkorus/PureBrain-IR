"""Ticker-to-Sector mapping for AI Fit Score Dimension 2 (Sector Alignment).

Pipeline:
  1. Download SEC company_tickers.json -> ticker->CIK mapping
  2. Query EDGAR submissions API for SIC codes per CIK (cached, resumable)
  3. Map SIC -> GICS sector using static mapping
  4. Store in ir_ticker_sectors SQLite table

Usage:
  python3 sector_mapper.py           # full run
  python3 sector_mapper.py --resume  # resume from cache
  python3 sector_mapper.py --stats   # show stats only
"""

import json
import os
import sqlite3
import sys
import time
import urllib.request
import urllib.error

# Reuse EDGAR client's rate limiter and User-Agent
USER_AGENT = "PureBrainIR/1.0 parallax.aiciv@gmail.com"
EDGAR_BASE = "https://data.sec.gov"

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "purebrain_ir.db")
CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "sic_cache.json")

# Rate limiter
_last_request_time = 0.0


def _throttle():
    """Enforce 100ms minimum between requests (10 req/s)."""
    global _last_request_time
    now = time.time()
    elapsed = now - _last_request_time
    if elapsed < 0.12:  # slightly conservative
        time.sleep(0.12 - elapsed)
    _last_request_time = time.time()


def _fetch_json(url: str) -> dict:
    """Fetch JSON with User-Agent and rate limiting."""
    _throttle()
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("  Rate limited, waiting 5s...")
            time.sleep(5)
            return _fetch_json(url)
        raise


# ============================================================
# SIC -> GICS Sector Mapping
# ============================================================
# SIC codes are 4-digit. We map the first 2 digits (SIC Division/Major Group)
# to GICS sectors. This is an approximate but practical mapping.

SIC_TO_GICS = {
    # Agriculture, Forestry, Fishing (01-09) -> Materials
    range(100, 999+1): "Materials",
    # Mining (10-14) -> Energy / Materials
    range(1000, 1099+1): "Energy",       # Metal mining
    range(1200, 1499+1): "Energy",       # Coal, Oil & Gas, Mining
    range(1000, 1199+1): "Materials",    # Metal mining
    range(1500, 1799+1): "Industrials",  # Construction
    # Manufacturing (20-39)
    range(2000, 2099+1): "Consumer Staples",  # Food
    range(2100, 2199+1): "Consumer Staples",  # Tobacco
    range(2200, 2399+1): "Consumer Discretionary",  # Textiles, Apparel
    range(2400, 2599+1): "Materials",    # Lumber, Furniture
    range(2600, 2699+1): "Materials",    # Paper
    range(2700, 2799+1): "Communication Services",  # Printing, Publishing
    range(2800, 2899+1): "Health Care",  # Chemicals, Pharma
    range(2900, 2999+1): "Energy",       # Petroleum refining
    range(3000, 3099+1): "Materials",    # Rubber, Plastics
    range(3100, 3199+1): "Consumer Discretionary",  # Leather
    range(3200, 3299+1): "Materials",    # Stone, Clay, Glass
    range(3300, 3399+1): "Materials",    # Primary metals
    range(3400, 3499+1): "Industrials",  # Fabricated metals
    range(3500, 3599+1): "Industrials",  # Industrial machinery
    range(3600, 3699+1): "Information Technology",  # Electronic equipment
    range(3700, 3799+1): "Industrials",  # Transportation equipment
    range(3800, 3899+1): "Health Care",  # Instruments (medical, scientific)
    range(3900, 3999+1): "Consumer Discretionary",  # Misc manufacturing
    # Transportation, Utilities (40-49)
    range(4000, 4499+1): "Industrials",  # Transportation
    range(4500, 4599+1): "Industrials",  # Air transportation
    range(4600, 4699+1): "Industrials",  # Pipelines
    range(4700, 4799+1): "Industrials",  # Transportation services
    range(4800, 4899+1): "Communication Services",  # Communications
    range(4900, 4999+1): "Utilities",    # Electric, Gas, Sanitary
    # Wholesale Trade (50-51)
    range(5000, 5199+1): "Consumer Discretionary",
    # Retail Trade (52-59)
    range(5200, 5999+1): "Consumer Discretionary",
    # Finance, Insurance, Real Estate (60-67)
    range(6000, 6099+1): "Financials",   # Depository institutions
    range(6100, 6199+1): "Financials",   # Non-depository credit
    range(6200, 6299+1): "Financials",   # Security brokers
    range(6300, 6399+1): "Financials",   # Insurance carriers
    range(6400, 6499+1): "Financials",   # Insurance agents
    range(6500, 6599+1): "Real Estate",  # Real estate
    range(6600, 6699+1): "Financials",   # Combined RE/Finance
    range(6700, 6799+1): "Financials",   # Holding companies, investment offices
    # Services (70-89)
    range(7000, 7099+1): "Consumer Discretionary",  # Hotels
    range(7200, 7299+1): "Consumer Discretionary",  # Personal services
    range(7300, 7399+1): "Industrials",  # Business services
    range(7400, 7499+1): "Industrials",  # Auto repair
    range(7500, 7599+1): "Consumer Discretionary",  # Auto rental
    range(7600, 7699+1): "Industrials",  # Misc repair
    range(7700, 7799+1): "Consumer Discretionary",  # Motion pictures
    range(7800, 7899+1): "Communication Services",  # Amusement, recreation
    range(7900, 7999+1): "Communication Services",  # Amusement, recreation
    range(8000, 8099+1): "Health Care",  # Health services
    range(8100, 8199+1): "Industrials",  # Legal services
    range(8200, 8299+1): "Consumer Discretionary",  # Educational
    range(8300, 8399+1): "Health Care",  # Social services
    range(8400, 8499+1): "Consumer Discretionary",  # Museums
    range(8600, 8699+1): "Industrials",  # Membership organizations
    range(8700, 8799+1): "Information Technology",   # Engineering, management
    range(8800, 8899+1): "Industrials",  # Private households
    range(8900, 8999+1): "Industrials",  # Services NEC
    # Public Administration (91-99)
    range(9100, 9999+1): "Industrials",
}

# More precise SIC overrides for commonly occurring codes
SIC_PRECISE = {
    # Software
    7371: "Information Technology",  # Computer programming
    7372: "Information Technology",  # Prepackaged software
    7374: "Information Technology",  # Computer processing, data prep
    7376: "Information Technology",  # Computer facilities management
    7377: "Information Technology",  # Computer rental, leasing
    7378: "Information Technology",  # Computer maintenance
    7379: "Information Technology",  # Computer related services NEC
    7370: "Information Technology",  # Computer programming, data processing (incl Google, Meta)
    # Pharma / Biotech
    2833: "Health Care",  # Pharmaceutical preparations
    2834: "Health Care",  # Pharmaceutical preparations
    2835: "Health Care",  # In vitro diagnostics
    2836: "Health Care",  # Biological products
    # Semiconductors
    3674: "Information Technology",  # Semiconductors
    3672: "Information Technology",  # Printed circuit boards
    # Electronic computers
    3571: "Information Technology",  # Electronic computers
    3572: "Information Technology",  # Computer storage
    3575: "Information Technology",  # Electronic computers
    3577: "Information Technology",  # Computer peripherals
    3578: "Information Technology",  # Calculators, accounting machines
    3579: "Information Technology",  # Office machines NEC
    # Telecom
    4812: "Communication Services",  # Telephone
    4813: "Communication Services",  # Telephone
    4822: "Communication Services",  # Telegraph
    4833: "Communication Services",  # Television broadcasting
    4841: "Communication Services",  # Cable TV
    # Internet / E-commerce
    5961: "Consumer Discretionary",  # Catalog, mail-order houses
    5990: "Consumer Discretionary",  # Retail NEC
    # Investment vehicles (common in 13F)
    6726: "Financials",  # Investment offices NEC
    6770: "Financials",  # Blank checks
    6798: "Real Estate",  # REITs
    6199: "Financials",  # Finance services
    # Restaurants / Food service
    5812: "Consumer Discretionary",  # Eating places
    5813: "Consumer Discretionary",  # Drinking places
    # Grocery
    5411: "Consumer Staples",  # Grocery stores
    # Drug stores
    5912: "Consumer Staples",  # Drug stores
    # Beverages
    2080: "Consumer Staples",  # Beverages
    2082: "Consumer Staples",  # Malt beverages
    2085: "Consumer Staples",  # Distilled spirits
    2086: "Consumer Staples",  # Bottled soft drinks
    # Household products
    2840: "Consumer Staples",  # Soap, detergents
    2842: "Consumer Staples",  # Specialty cleaning
    2844: "Consumer Staples",  # Perfumes, cosmetics
}

# Valid GICS sectors
GICS_SECTORS = [
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities",
]


def sic_to_gics(sic_code: int) -> str | None:
    """Map a 4-digit SIC code to a GICS sector name."""
    # Check precise overrides first
    if sic_code in SIC_PRECISE:
        return SIC_PRECISE[sic_code]
    # Fall back to range-based mapping
    for sic_range, sector in SIC_TO_GICS.items():
        if sic_code in sic_range:
            return sector
    return None


# ============================================================
# SEC Data Pipeline
# ============================================================

def download_ticker_cik_map() -> dict[str, int]:
    """Download SEC company_tickers.json and return ticker->CIK mapping."""
    print("Downloading SEC company tickers...")
    url = "https://www.sec.gov/files/company_tickers.json"
    data = _fetch_json(url)
    ticker_to_cik = {}
    for entry in data.values():
        ticker = entry.get("ticker", "").upper()
        cik = entry.get("cik_str")
        if ticker and cik:
            ticker_to_cik[ticker] = int(cik) if isinstance(cik, str) else cik
    print(f"  Loaded {len(ticker_to_cik)} ticker->CIK mappings")
    return ticker_to_cik


def load_sic_cache() -> dict[str, dict]:
    """Load cached CIK->SIC mappings from disk."""
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}


def save_sic_cache(cache: dict):
    """Save CIK->SIC cache to disk."""
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f)


def fetch_sic_for_cik(cik: int) -> tuple[int | None, str | None]:
    """Query EDGAR submissions API for a company's SIC code.

    Returns (sic_code, sic_description) or (None, None).
    """
    padded = str(cik).zfill(10)
    url = f"{EDGAR_BASE}/submissions/CIK{padded}.json"
    try:
        data = _fetch_json(url)
        sic = data.get("sic")
        sic_desc = data.get("sicDescription")
        if sic:
            return int(sic), sic_desc
        return None, None
    except Exception as e:
        print(f"  Error fetching CIK {cik}: {e}")
        return None, None


def get_holdings_tickers(db_path: str = DB_PATH) -> list[str]:
    """Get all unique tickers from holdings table."""
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT DISTINCT ticker FROM ir_holdings "
        "WHERE length(ticker) BETWEEN 1 AND 5 AND ticker GLOB '[A-Z]*'"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def create_ticker_sectors_table(db_path: str = DB_PATH):
    """Create the ir_ticker_sectors table if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ir_ticker_sectors (
            ticker TEXT PRIMARY KEY,
            sic_code INTEGER,
            sic_description TEXT,
            gics_sector TEXT NOT NULL,
            source TEXT DEFAULT 'edgar',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ticker_sectors_gics
        ON ir_ticker_sectors(gics_sector)
    """)
    conn.commit()
    conn.close()
    print("Created ir_ticker_sectors table")


def populate_sectors(db_path: str = DB_PATH, resume: bool = False):
    """Main pipeline: map all holdings tickers to GICS sectors."""

    # Step 1: Get our tickers
    tickers = get_holdings_tickers(db_path)
    print(f"Found {len(tickers)} unique tickers in holdings")

    # Step 2: Get ticker->CIK mapping from SEC
    ticker_to_cik = download_ticker_cik_map()

    # Step 3: Match our tickers to CIKs
    matched = {t: ticker_to_cik[t] for t in tickers if t in ticker_to_cik}
    unmatched = [t for t in tickers if t not in ticker_to_cik]
    print(f"Matched {len(matched)} tickers to CIKs, {len(unmatched)} unmatched")

    # Step 4: Load SIC cache
    sic_cache = load_sic_cache() if resume else {}
    already_cached = sum(1 for t in matched if str(matched[t]) in sic_cache)
    print(f"SIC cache: {len(sic_cache)} entries ({already_cached} of our tickers cached)")

    # Step 5: Fetch SIC codes for uncached CIKs
    unique_ciks = set(matched.values())
    ciks_to_fetch = [cik for cik in unique_ciks if str(cik) not in sic_cache]
    print(f"Need to fetch SIC for {len(ciks_to_fetch)} CIKs ({len(unique_ciks)} unique total)")

    if ciks_to_fetch:
        print(f"Fetching SIC codes from EDGAR (est. {len(ciks_to_fetch) * 0.12:.0f}s)...")
        for i, cik in enumerate(ciks_to_fetch):
            sic_code, sic_desc = fetch_sic_for_cik(cik)
            sic_cache[str(cik)] = {
                "sic": sic_code,
                "desc": sic_desc,
            }
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{len(ciks_to_fetch)} fetched...")
                save_sic_cache(sic_cache)  # checkpoint
            if (i + 1) % 500 == 0:
                # Extra checkpoint
                save_sic_cache(sic_cache)

        save_sic_cache(sic_cache)
        print(f"  Fetched all {len(ciks_to_fetch)} SIC codes")

    # Step 6: Map to GICS sectors and insert
    conn = sqlite3.connect(db_path)
    create_ticker_sectors_table(db_path)

    inserted = 0
    no_sic = 0
    no_sector = 0
    sector_counts = {}

    for ticker in tickers:
        cik = matched.get(ticker)
        if cik:
            cached = sic_cache.get(str(cik), {})
            sic_code = cached.get("sic")
            sic_desc = cached.get("desc")
            if sic_code:
                sector = sic_to_gics(sic_code)
                if sector:
                    conn.execute(
                        "INSERT OR REPLACE INTO ir_ticker_sectors "
                        "(ticker, sic_code, sic_description, gics_sector, source) "
                        "VALUES (?, ?, ?, ?, 'edgar')",
                        (ticker, sic_code, sic_desc, sector),
                    )
                    inserted += 1
                    sector_counts[sector] = sector_counts.get(sector, 0) + 1
                else:
                    no_sector += 1
            else:
                no_sic += 1
        else:
            # Unmatched ticker - likely ETF or foreign security
            # Classify as Financials (investment vehicle) for now
            conn.execute(
                "INSERT OR REPLACE INTO ir_ticker_sectors "
                "(ticker, sic_code, sic_description, gics_sector, source) "
                "VALUES (?, NULL, NULL, 'Financials', 'fallback_etf')",
                (ticker, ),
            )
            inserted += 1
            sector_counts["Financials"] = sector_counts.get("Financials", 0) + 1

    conn.commit()
    conn.close()

    # Results
    print(f"\n--- Results ---")
    print(f"Total tickers: {len(tickers)}")
    print(f"Inserted: {inserted}")
    print(f"No SIC found: {no_sic}")
    print(f"SIC found but no GICS mapping: {no_sector}")
    print(f"\nSector distribution:")
    for sector in sorted(sector_counts, key=sector_counts.get, reverse=True):
        print(f"  {sector}: {sector_counts[sector]}")


def show_stats(db_path: str = DB_PATH):
    """Show current sector mapping statistics."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    total = conn.execute("SELECT COUNT(*) FROM ir_ticker_sectors").fetchone()[0]
    if total == 0:
        print("No sector mappings found. Run: python3 sector_mapper.py")
        conn.close()
        return

    print(f"Total ticker-sector mappings: {total}")
    print(f"\nBy sector:")
    rows = conn.execute(
        "SELECT gics_sector, COUNT(*) as cnt FROM ir_ticker_sectors "
        "GROUP BY gics_sector ORDER BY cnt DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r['gics_sector']}: {r['cnt']}")

    print(f"\nBy source:")
    rows = conn.execute(
        "SELECT source, COUNT(*) as cnt FROM ir_ticker_sectors "
        "GROUP BY source ORDER BY cnt DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r['source']}: {r['cnt']}")

    # Coverage vs holdings
    total_holdings_tickers = conn.execute(
        "SELECT COUNT(DISTINCT ticker) FROM ir_holdings "
        "WHERE length(ticker) BETWEEN 1 AND 5 AND ticker GLOB '[A-Z]*'"
    ).fetchone()[0]
    mapped = conn.execute(
        "SELECT COUNT(DISTINCT h.ticker) FROM ir_holdings h "
        "JOIN ir_ticker_sectors s ON h.ticker = s.ticker"
    ).fetchone()[0]
    print(f"\nCoverage: {mapped}/{total_holdings_tickers} "
          f"({mapped/total_holdings_tickers*100:.1f}%) of holdings tickers mapped")

    conn.close()


if __name__ == "__main__":
    if "--stats" in sys.argv:
        show_stats()
    else:
        resume = "--resume" in sys.argv
        create_ticker_sectors_table()
        populate_sectors(resume=resume)
        print("\n")
        show_stats()
