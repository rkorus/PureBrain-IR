#!/usr/bin/env python3
"""PureBrain IR - 13F/EDGAR Pipeline Orchestrator.

Usage:
  python -m pipeline.ingest --seed          # Ingest seed filers (top 20)
  python -m pipeline.ingest --cik 102909    # Ingest specific filer by CIK
  python -m pipeline.ingest --spike         # Re-parse spike data (Vanguard XML)
  python -m pipeline.ingest --stats         # Show database statistics

Pipeline flow:
  1. EDGAR API -> fetch company submissions
  2. Extract 13F-HR filings from submissions
  3. Download information table XML for each filing
  4. Parse XML -> extract holdings
  5. CUSIP -> ticker resolution via OpenFIGI
  6. Load into SQLite (D1-compatible schema)
"""

import argparse
import json
import os
import sys
import time

# Allow running as module from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.edgar_client import (
    get_company_filings, extract_13f_filings, resolve_info_table,
    download_info_table, get_seed_filers, Filing13F,
)
from pipeline.xml_parser import parse_info_table, parse_file, Holding
from pipeline.cusip_resolver import resolve_cusips, get_cache_stats
from pipeline.db import get_connection, init_schema, upsert_investor, insert_holdings, get_stats


SPIKE_DIR = os.path.join(os.path.dirname(__file__), "..", "spikes")


def ingest_filer(cik: str, name: str, max_filings: int = 4,
                 resolve_tickers: bool = True, verbose: bool = True):
    """Ingest all 13F filings for a single filer.

    Args:
        cik: SEC Central Index Key
        name: Company name
        max_filings: Maximum number of recent filings to process
        resolve_tickers: Whether to resolve CUSIPs to tickers
        verbose: Print progress
    """
    conn = get_connection()
    init_schema(conn)

    if verbose:
        print(f"\n{'='*60}")
        print(f"Ingesting: {name} (CIK: {cik})")
        print(f"{'='*60}")

    # Step 1: Fetch company submissions
    if verbose:
        print(f"  [1/5] Fetching submissions from EDGAR...")
    try:
        submissions = get_company_filings(cik)
    except Exception as e:
        print(f"  ERROR: Failed to fetch submissions: {e}")
        return

    company_name = submissions.get("name", name)

    # Step 2: Extract 13F filings
    filings = extract_13f_filings(submissions, max_filings=max_filings)
    if verbose:
        print(f"  [2/5] Found {len(filings)} 13F-HR filings")

    if not filings:
        print(f"  WARNING: No 13F filings found for {name}")
        conn.close()
        return

    # Step 3: Upsert investor record
    investor_id = upsert_investor(
        conn,
        name=company_name,
        type="asset_manager",
        cik=cik,
        last_13f_filed=filings[0].filing_date if filings else None,
        data_source="edgar_13f",
    )
    conn.commit()

    total_holdings = 0

    for filing in filings:
        if verbose:
            print(f"\n  Filing: {filing.period_of_report} (filed {filing.filing_date})")

        # Step 3: Download information table
        if verbose:
            print(f"    [3/5] Resolving info table URL...")
        filing = resolve_info_table(filing)
        if not filing.info_table_url:
            print(f"    WARNING: No information table found")
            continue

        if verbose:
            print(f"    [3/5] Downloading XML: {filing.info_table_url}")
        try:
            xml_data = download_info_table(filing)
        except Exception as e:
            print(f"    ERROR: Download failed: {e}")
            continue

        if not xml_data:
            print(f"    WARNING: Empty XML response")
            continue

        # Step 4: Parse XML
        if verbose:
            print(f"    [4/5] Parsing holdings...")
        try:
            holdings = parse_info_table(xml_data)
        except Exception as e:
            print(f"    ERROR: XML parse failed: {e}")
            continue

        if verbose:
            print(f"    [4/5] Parsed {len(holdings)} holdings")

        # Step 5: CUSIP -> ticker resolution
        holdings_dicts = []
        if resolve_tickers and holdings:
            cusips = [h.cusip for h in holdings if h.cusip]
            unique_cusips = list(set(cusips))
            if verbose:
                print(f"    [5/5] Resolving {len(unique_cusips)} unique CUSIPs via OpenFIGI...")

            try:
                resolutions = resolve_cusips(unique_cusips)
            except Exception as e:
                print(f"    WARNING: CUSIP resolution failed: {e}")
                resolutions = {}

            for h in holdings:
                ticker = ""
                if h.cusip in resolutions and resolutions[h.cusip].ticker:
                    ticker = resolutions[h.cusip].ticker
                holdings_dicts.append({
                    "ticker": ticker,
                    "company_name": h.name_of_issuer,
                    "cusip": h.cusip,
                    "shares": h.shares,
                    "market_value": h.value_thousands,
                    "investment_discretion": h.investment_discretion,
                    "source_url": filing.info_table_url,
                })
        else:
            for h in holdings:
                holdings_dicts.append({
                    "ticker": "",
                    "company_name": h.name_of_issuer,
                    "cusip": h.cusip,
                    "shares": h.shares,
                    "market_value": h.value_thousands,
                    "investment_discretion": h.investment_discretion,
                    "source_url": filing.info_table_url or "",
                })

        # Step 6: Load into database
        insert_holdings(
            conn, investor_id, holdings_dicts,
            filing_type="13F",
            filing_date=filing.filing_date,
            period_of_report=filing.period_of_report,
        )
        conn.commit()
        total_holdings += len(holdings_dicts)

        if verbose:
            print(f"    Loaded {len(holdings_dicts)} holdings")

    if verbose:
        stats = get_stats(conn)
        print(f"\n  Total loaded for {company_name}: {total_holdings} holdings")
        print(f"  DB totals: {stats['investors']} investors, {stats['holdings']} holdings, {stats['unique_cusips']} unique CUSIPs")
        cache = get_cache_stats()
        print(f"  CUSIP cache: {cache['resolved']}/{cache['total']} resolved")

    conn.close()


def ingest_seed_filers(max_filings: int = 2, resolve_tickers: bool = True):
    """Ingest all seed filers (top institutional investors)."""
    filers = get_seed_filers()
    print(f"Ingesting {len(filers)} seed filers...")
    print(f"Max filings per filer: {max_filings}")
    print(f"Ticker resolution: {'ON' if resolve_tickers else 'OFF'}")

    for cik, name in filers.items():
        try:
            ingest_filer(cik, name, max_filings=max_filings,
                        resolve_tickers=resolve_tickers)
        except Exception as e:
            print(f"\nERROR processing {name}: {e}")
            continue

    # Final stats
    conn = get_connection()
    stats = get_stats(conn)
    conn.close()

    print(f"\n{'='*60}")
    print(f"SEED INGESTION COMPLETE")
    print(f"{'='*60}")
    print(f"  Investors: {stats['investors']}")
    print(f"  Holdings:  {stats['holdings']}")
    print(f"  Filings:   {stats['filings']}")
    print(f"  CUSIPs:    {stats['unique_cusips']}")


def ingest_spike():
    """Re-parse the Vanguard spike data to validate pipeline."""
    spike_file = os.path.join(SPIKE_DIR, "vanguard_13f_holdings.xml")
    if not os.path.exists(spike_file):
        print(f"Spike file not found: {spike_file}")
        return

    print(f"Parsing spike file: {spike_file}")
    holdings = parse_file(spike_file)
    print(f"Parsed {len(holdings)} holdings")

    if holdings:
        print(f"\nFirst 5 holdings:")
        for h in holdings[:5]:
            print(f"  {h.name_of_issuer}: {h.shares:,} shares, ${h.value_thousands:,}K, CUSIP={h.cusip}")

        print(f"\nUnique CUSIPs: {len(set(h.cusip for h in holdings))}")

        # Load into DB
        conn = get_connection()
        init_schema(conn)

        investor_id = upsert_investor(
            conn, name="Vanguard Group", type="asset_manager",
            cik="102909", data_source="edgar_13f",
        )

        holdings_dicts = [{
            "ticker": "",
            "company_name": h.name_of_issuer,
            "cusip": h.cusip,
            "shares": h.shares,
            "market_value": h.value_thousands,
            "investment_discretion": h.investment_discretion,
            "source_url": "spike_data",
        } for h in holdings]

        insert_holdings(conn, investor_id, holdings_dicts,
                       filing_type="13F", filing_date="2025-02-14",
                       period_of_report="2024-12-31")
        conn.commit()

        stats = get_stats(conn)
        print(f"\nDB after spike load:")
        print(f"  Investors: {stats['investors']}")
        print(f"  Holdings:  {stats['holdings']}")
        conn.close()


def show_stats():
    """Show current database statistics."""
    conn = get_connection()
    try:
        stats = get_stats(conn)
    except Exception:
        print("Database not initialized. Run --spike or --seed first.")
        return
    finally:
        conn.close()

    print(f"PureBrain IR Database Statistics")
    print(f"{'='*40}")
    print(f"  Investors: {stats['investors']}")
    print(f"  Holdings:  {stats['holdings']}")
    print(f"  Filings:   {stats['filings']}")
    print(f"  CUSIPs:    {stats['unique_cusips']}")


def main():
    parser = argparse.ArgumentParser(description="PureBrain IR - 13F/EDGAR Pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--seed", action="store_true", help="Ingest seed filers (top 20)")
    group.add_argument("--cik", type=str, help="Ingest specific filer by CIK")
    group.add_argument("--spike", action="store_true", help="Re-parse Vanguard spike data")
    group.add_argument("--stats", action="store_true", help="Show database statistics")

    parser.add_argument("--max-filings", type=int, default=2, help="Max filings per filer (default: 2)")
    parser.add_argument("--no-tickers", action="store_true", help="Skip CUSIP->ticker resolution")
    parser.add_argument("--name", type=str, help="Company name (for --cik)")

    args = parser.parse_args()

    if args.spike:
        ingest_spike()
    elif args.seed:
        ingest_seed_filers(max_filings=args.max_filings, resolve_tickers=not args.no_tickers)
    elif args.cik:
        name = args.name or f"CIK-{args.cik}"
        ingest_filer(args.cik, name, max_filings=args.max_filings,
                    resolve_tickers=not args.no_tickers)
    elif args.stats:
        show_stats()


if __name__ == "__main__":
    main()
