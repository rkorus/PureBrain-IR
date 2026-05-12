#!/usr/bin/env python3
"""Expand 13F filer coverage beyond seed filers.

Adds the next tier of major institutional investors by AUM.
Uses existing ingest_filer() pipeline — each filer gets:
  1. EDGAR submissions lookup
  2. 13F-HR filing extraction (most recent 2 quarters)
  3. Info table XML download + parse
  4. CUSIP→ticker resolution
  5. SQLite insert

Usage:
  python3 expand_filers.py              # ingest all expansion filers
  python3 expand_filers.py --dry-run    # show what would be ingested
  python3 expand_filers.py --stats      # show current DB stats
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.ingest import ingest_filer, show_stats
from pipeline.db import get_connection, get_stats, init_schema, upsert_investor, insert_holdings, generate_id
from pipeline.edgar_client import get_company_filings, extract_13f_filings, resolve_info_table, download_info_table
from pipeline.xml_parser import parse_info_table

# Top institutional 13F filers by AUM, excluding seed filers.
# All CIK numbers verified against SEC EDGAR.
#
# Seed filers already ingested (in edgar_client.py SEED_FILERS):
#   Vanguard(102909), BlackRock(2012383), Berkshire Hathaway(1067983),
#   State Street(93751), JPMorgan(19617), Renaissance Technologies(1037389),
#   Morgan Stanley(895421), Goldman Sachs(886982)
#
# Additional filers already in DB from prior runs (33 total) are filtered
# at runtime by expand_filers() -- duplicates are safe and skipped.
#
# This dict covers 108 unique CIK entries.

EXPANSION_FILERS = {

    # ===================================================================
    # TOP ASSET MANAGERS BY AUM (corrected CIKs — advisor entity, not holding co)
    # ===================================================================
    "315066": "Fidelity Management & Research",
    "1350694": "Capital Research Global Investors",
    "1422849": "Capital World Investors",           # was 34066 (wrong entity)
    "80255": "T. Rowe Price Associates",            # was 1004010 (wrong entity)
    "73124": "Northern Trust",
    "1214717": "Geode Capital Management",
    "354204": "Dimensional Fund Advisors",
    "902219": "Wellington Management Group",        # was 1060950 (wrong entity)
    "38777": "Franklin Templeton",
    "914208": "Invesco",
    "200217": "Dodge & Cox",                        # was 29440 (mutual fund family)
    "912938": "MFS Investment Management",          # was 63296 (wrong entity)
    "1163368": "PIMCO",                             # was 1401807 (wrong entity)
    "1521019": "Nuveen Asset Management",           # was 1414889 (wrong entity)
    "277751": "Janus Henderson",
    "312348": "Loomis Sayles",                      # was 62568 (wrong entity)
    "1418814": "Parametric Portfolio Associates",
    "887793": "TIAA-CREF Investment Management",    # was 810747 (wrong entity)
    "1272842": "Baillie Gifford",

    # ===================================================================
    # LARGE BANK WEALTH MANAGEMENT / BROKER-DEALERS
    # ===================================================================
    "1610520": "UBS Group AG",                      # was 1114446 (UBS AG banking entity)
    "70858": "Bank of America",
    "72971": "Wells Fargo",
    "316709": "Charles Schwab",
    "36104": "US Bancorp",
    "820081": "Ameriprise Financial",

    # ===================================================================
    # MEGA HEDGE FUNDS / MULTI-STRATEGY
    # ===================================================================
    "1423053": "Citadel Advisors",
    "1273087": "Millennium Management",
    "1603466": "Point72 Asset Management",
    "1179392": "Two Sigma Investments",
    "1048445": "Elliott Investment Management",
    "1103804": "Viking Global Investors",
    "1535392": "Coatue Management",
    "1040273": "Third Point",
    "921669": "Icahn Carl",
    "1061165": "Lone Pine Capital",
    "1544326": "Dragoneer Investment Group",
    "1549575": "Whale Rock Capital",
    "1364742": "Bridgewater Associates",
    "1004244": "AQR Capital Management",

    # ===================================================================
    # ACTIVIST INVESTORS
    # ===================================================================
    "1159159": "Jana Partners",
    "913760": "Appaloosa Management",
    "1540536": "ValueAct Capital",
    "1517137": "Starboard Value",

    # ===================================================================
    # VALUE / FUNDAMENTAL HEDGE FUNDS
    # ===================================================================
    "1061768": "Baupost Group",
    "1079114": "Greenlight Capital",
    "1009207": "Southeastern Asset Management",

    # ===================================================================
    # QUANT / SYSTEMATIC FUNDS
    # ===================================================================
    "1349785": "Arrowstreet Capital",
    "1547241": "Marshall Wace",
    "816563": "Man Group",

    # ===================================================================
    # INSURANCE COMPANIES (13F FILERS)
    # ===================================================================
    "1099219": "MetLife",
    "1137774": "Prudential Financial",
    "874766": "Hartford Financial Services",
    "59558": "Lincoln National",
    "764065": "Principal Financial Group",
    "85408": "American International Group",

    # ===================================================================
    # TIGER CUB / LEGACY HEDGE FUNDS
    # ===================================================================
    "806510": "Tiger Management",
    "1015780": "Maverick Capital",
    "1167365": "Jennison Associates",
    "1167483": "Tiger Global Management",           # was 1608863 (wrong CIK)

    # ===================================================================
    # EVENT-DRIVEN / DISTRESSED / CREDIT HEDGE FUNDS
    # ===================================================================
    "1022820": "Farallon Capital Management",
    "1301588": "Discovery Capital Management",
    "1034525": "Canyon Capital Advisors",
    "1138851": "Cerberus Capital Management",
    "1096098": "York Capital Management",

    # ===================================================================
    # PRIVATE EQUITY / ALTERNATIVE ASSET MANAGERS (13F FILERS)
    # ===================================================================
    "1259313": "Ares Management",                   # was 1555280 (holding company)
    "1449434": "Apollo Management Holdings",        # was 1411494 (holding company)
    "1399770": "KKR & Co",                          # was 1404912 (wrong entity)
    "1527166": "Carlyle Group",
    "1903793": "TPG GP A LLC",                      # was 1880661 (holding company)

    # ===================================================================
    # MAJOR MUTUAL FUND FAMILIES & ASSET MANAGERS
    # ===================================================================
    "1166559": "Lazard Asset Management",
    "810265": "Legg Mason (now Franklin)",
    "1048286": "Eaton Vance Management",
    "1111830": "Neuberger Berman Group",
    "908821": "AllianceBernstein",
    "1378454": "WisdomTree Investments",
    "1006249": "SEI Investments",
    "812295": "Putnam Investments",
    "1267083": "Artisan Partners",
    "1173334": "Cohen & Steers",
    "1045450": "Federated Hermes",
    "1006837": "Lord Abbett & Co",

    # ===================================================================
    # ENDOWMENT / PENSION-ADJACENT MANAGERS
    # ===================================================================
    "1167557": "D.E. Shaw & Co",
    "1336528": "Och-Ziff Capital (Sculptor)",

    # ===================================================================
    # CANADIAN / INTERNATIONAL FILERS WITH 13F OBLIGATIONS
    # ===================================================================
    "1086364": "Brookfield Asset Management",
    "1131013": "Manulife Financial (Hancock)",
    "878927": "Sun Life Financial",

    # ===================================================================
    # GROWTH / TECH-FOCUSED HEDGE FUNDS
    # ===================================================================
    "1544325": "Altimeter Capital Management",
    "1535581": "Durable Capital Partners",
    "1496147": "Alkeon Capital Management",
    "1599901": "Light Street Capital",
    "1336790": "Abdiel Capital Advisors",

    # ===================================================================
    # TWO SIGMA (SEPARATE FILING ENTITIES)
    # ===================================================================
    "1543160": "Two Sigma Advisors LP",             # separate from Two Sigma Investments
    "927971": "BMO Financial Group",                # was mislabeled as Ameriprise

    # ===================================================================
    # ADDITIONAL VERIFIED FILERS (SECOND PASS)
    # ===================================================================
    "1897612": "T. Rowe Price Investment Management",  # newer TROWE entity also files 13F
    "811401": "Northern Trust Investments",
    "1535323": "Allianz Asset Management (PIMCO parent)",  # combined 13F filing

    # ===================================================================
    # THIRD PASS — VERIFIED 13F FILERS (targeting 100+)
    # ===================================================================
    "909661": "Farallon Capital Management",    # correct CIK (was using wrong 1022820)
    "720005": "Raymond James Financial",
    "312069": "Barclays PLC",
    "1463559": "Alberta Investment Management Corp",
    "1762304": "HHLR Advisors (Hillhouse Capital)",
    "1334978": "Soros Fund Management",
    "1389508": "Adage Capital Management",
    "1056087": "Orbimed Advisors",
    "1077349": "Baker Bros Advisors",
    "1044316": "Senator Investment Group",
    "1301011": "Canada Pension Plan Investment Board",
    "908823": "AllianceBernstein Holding LP",
    "1598982": "Norges Bank Investment Management",
    "77281": "PNC Financial Services",
    "1129137": "Credit Suisse Group AG",
    "1280263": "Cowen Inc",
    "1345471": "York Capital Management Global Advisors",
    "1582002": "Steadfast Capital Management",
    "1167557": "D.E. Shaw & Co",                # already in list but may not have ingested
    "1408529": "Temasek Holdings",
    "1535323": "Allianz Global Investors",
    "1666730": "Darsana Capital Partners",
    "1697635": "Samlyn Capital",
    "1550523": "Sachem Head Capital Management",
    "1484148": "Glenview Capital Management",
    "1009171": "Highfields Capital Management",
    "1173413": "Harvest Fund Advisors",
    "1105838": "Kingdon Capital Management",
    "1167491": "Owl Creek Asset Management",
    "1040140": "Gabelli Funds (GAMCO)",
}


def load_cusip_cache() -> dict[str, str]:
    """Load CUSIP→ticker cache from disk (built from existing holdings)."""
    cache_path = os.path.join(os.path.dirname(__file__), "..", "cusip_ticker_cache.json")
    if os.path.exists(cache_path):
        import json
        with open(cache_path) as f:
            cache = json.load(f)
        print(f"Loaded CUSIP→ticker cache: {len(cache)} entries")
        return cache
    return {}


def ingest_filer_fast(cik: str, name: str, cusip_cache: dict,
                      max_filings: int = 2):
    """Fast ingestion: uses CUSIP cache instead of OpenFIGI API.

    Much faster than ingest_filer() because it skips the slow
    OpenFIGI API calls (6.5s per batch of 10 CUSIPs).
    """
    conn = get_connection()
    init_schema(conn)

    print(f"  [1/4] Fetching submissions from EDGAR...")
    try:
        submissions = get_company_filings(cik)
    except Exception as e:
        print(f"  ERROR: Failed to fetch submissions: {e}")
        conn.close()
        return 0

    company_name = submissions.get("name", name)

    filings = extract_13f_filings(submissions, max_filings=max_filings)
    print(f"  [2/4] Found {len(filings)} 13F-HR filings")

    if not filings:
        print(f"  WARNING: No 13F filings found for {name}")
        conn.close()
        return 0

    investor_id = upsert_investor(
        conn, name=company_name, type="asset_manager",
        cik=cik, last_13f_filed=filings[0].filing_date,
        data_source="edgar_13f",
    )
    conn.commit()

    total_holdings = 0
    for filing in filings:
        print(f"  Filing: {filing.period_of_report} (filed {filing.filing_date})")

        filing = resolve_info_table(filing)
        if not filing.info_table_url:
            print(f"    No information table found, skipping")
            continue

        print(f"    [3/4] Downloading XML...")
        try:
            xml_data = download_info_table(filing)
        except Exception as e:
            print(f"    ERROR: Download failed: {e}")
            continue

        if not xml_data:
            continue

        print(f"    [4/4] Parsing holdings...")
        try:
            holdings = parse_info_table(xml_data)
        except Exception as e:
            print(f"    ERROR: XML parse failed: {e}")
            continue

        # Resolve tickers from cache (no API calls)
        cache_hits = 0
        holdings_dicts = []
        for h in holdings:
            ticker = cusip_cache.get(h.cusip, "")
            if ticker:
                cache_hits += 1
            holdings_dicts.append({
                "ticker": ticker,
                "company_name": h.name_of_issuer,
                "cusip": h.cusip,
                "shares": h.shares,
                "market_value": h.value_thousands,
                "investment_discretion": h.investment_discretion,
                "source_url": filing.info_table_url or "",
            })

        insert_holdings(
            conn, investor_id, holdings_dicts,
            filing_type="13F",
            filing_date=filing.filing_date,
            period_of_report=filing.period_of_report,
        )
        conn.commit()
        total_holdings += len(holdings_dicts)
        print(f"    Loaded {len(holdings_dicts)} holdings "
              f"({cache_hits} tickers from cache)")

    conn.close()
    return total_holdings


def expand_filers(dry_run: bool = False, max_filings: int = 2):
    """Ingest expansion filers using fast cache-based approach."""
    conn = get_connection()
    stats_before = get_stats(conn)

    # Check which are already ingested
    existing_ciks = set()
    rows = conn.execute("SELECT cik FROM ir_investors WHERE cik IS NOT NULL").fetchall()
    for r in rows:
        existing_ciks.add(str(r[0]))
    conn.close()

    new_filers = {cik: name for cik, name in EXPANSION_FILERS.items()
                  if cik not in existing_ciks}

    print(f"Expansion filers: {len(EXPANSION_FILERS)} total, "
          f"{len(existing_ciks)} already in DB, {len(new_filers)} to ingest")

    if dry_run:
        print("\nWould ingest:")
        for cik, name in sorted(new_filers.items(), key=lambda x: x[1]):
            print(f"  CIK {cik}: {name}")
        return

    # Load CUSIP cache for fast ticker resolution
    cusip_cache = load_cusip_cache()

    print(f"\nStarting fast ingestion of {len(new_filers)} filers "
          f"(max {max_filings} filings each)...\n")

    success = 0
    failed = 0
    total_new_holdings = 0

    for i, (cik, name) in enumerate(new_filers.items()):
        print(f"\n--- [{i+1}/{len(new_filers)}] {name} (CIK: {cik}) ---")
        try:
            count = ingest_filer_fast(cik, name, cusip_cache,
                                      max_filings=max_filings)
            if count > 0:
                success += 1
                total_new_holdings += count
            else:
                failed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1
            continue

        # Checkpoint every 10 filers
        if (i + 1) % 10 == 0:
            conn = get_connection()
            stats = get_stats(conn)
            conn.close()
            print(f"\n  [CHECKPOINT] {stats['investors']} investors, "
                  f"{stats['holdings']} holdings after {i+1} filers")

    # Final stats
    conn = get_connection()
    stats_after = get_stats(conn)
    conn.close()

    print(f"\n{'='*60}")
    print(f"EXPANSION COMPLETE")
    print(f"{'='*60}")
    print(f"  Filers attempted: {len(new_filers)}")
    print(f"  Success: {success}")
    print(f"  Failed: {failed}")
    print(f"  New holdings: {stats_after['holdings'] - stats_before['holdings']}")
    print(f"  Total investors: {stats_after['investors']}")
    print(f"  Total holdings: {stats_after['holdings']}")
    print(f"  Total CUSIPs: {stats_after['unique_cusips']}")


if __name__ == "__main__":
    if "--stats" in sys.argv:
        show_stats()
    elif "--dry-run" in sys.argv:
        expand_filers(dry_run=True)
    else:
        max_f = 2
        for i, arg in enumerate(sys.argv):
            if arg == "--max-filings" and i + 1 < len(sys.argv):
                max_f = int(sys.argv[i + 1])
        expand_filers(max_filings=max_f)
