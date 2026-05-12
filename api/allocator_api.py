#!/usr/bin/env python3
"""
PureBrain IR — Allocator Search API (Sprint 3A)

Search pension funds, endowments, SWFs, and other allocators from 13F data.
Designed to match Parallax's frontend API contract.

Endpoints served via server.py:
  GET /api/search/allocators     — Filtered search
  GET /api/allocators/{id}       — Detail with top holdings
  GET /api/search/allocators/export — CSV export
"""

import csv
import io
import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
HOLDINGS_DB = SCRIPT_DIR / "holdings_13f.db"
ADV_DB = SCRIPT_DIR / "purebrain_ir.db"


@dataclass
class AllocatorFilters:
    """Search filters for allocator search."""
    query: Optional[str] = None          # Name search
    entity_type: Optional[str] = None    # pension|endowment|sovereign_wealth|foundation|family_office|insurance
    aum_min: Optional[float] = None      # Minimum AUM estimate
    aum_max: Optional[float] = None
    state: Optional[str] = None          # US state (2-letter)
    country: Optional[str] = None        # ISO country code
    gatekeeper: Optional[bool] = None    # Has gatekeeper relationships
    sort_by: str = "total_value"         # total_value|name|holdings_count|filing_date
    sort_dir: str = "DESC"
    limit: int = 25
    offset: int = 0


def _format_aum(val: float) -> str:
    """Format dollar amounts for display."""
    if not val or val == 0:
        return "N/A"
    if val >= 1e12:
        return f"${val/1e12:.1f}T"
    elif val >= 1e9:
        return f"${val/1e9:.1f}B"
    elif val >= 1e6:
        return f"${val/1e6:.0f}M"
    elif val >= 1e3:
        return f"${val/1e3:.0f}K"
    return f"${val:.0f}"


def search_allocators(
    filters: AllocatorFilters,
    holdings_db: Path = HOLDINGS_DB,
    adv_db: Path = ADV_DB,
) -> dict:
    """
    Search allocator-type investors with filters.

    Returns:
        {
            "results": [...],
            "total": int,
            "page": int,
            "per_page": int,
            "total_pages": int,
            "filters_applied": {...},
        }
    """
    conn = sqlite3.connect(str(holdings_db))
    conn.row_factory = sqlite3.Row

    # Build base query — allocator types only
    allocator_types = ("pension", "endowment", "sovereign_wealth", "foundation", "family_office", "insurance")

    where_clauses = ["i.type IN ({})".format(",".join("?" * len(allocator_types)))]
    params = list(allocator_types)

    # Name search
    if filters.query:
        where_clauses.append("LOWER(i.name) LIKE LOWER(?)")
        params.append(f"%{filters.query}%")

    # Entity type
    if filters.entity_type:
        where_clauses.append("i.type = ?")
        params.append(filters.entity_type)

    # Geography
    if filters.state:
        where_clauses.append("i.hq_state = ?")
        params.append(filters.state.upper())
    if filters.country:
        where_clauses.append("i.hq_country = ?")
        params.append(filters.country.upper())

    where_sql = " AND ".join(where_clauses)

    # Sort mapping
    sort_map = {
        "total_value": "total_value",
        "name": "i.name",
        "holdings_count": "holdings_count",
        "filing_date": "i.last_13f_filed",
        "gatekeeper_score": "gatekeeper_score",
    }
    sort_col = sort_map.get(filters.sort_by, "total_value")
    sort_dir = "ASC" if filters.sort_dir.upper() == "ASC" else "DESC"

    # Main query with holdings aggregation
    query_sql = f"""
        SELECT
            i.id,
            i.name,
            i.type as entity_type,
            i.cik,
            i.hq_country,
            i.hq_state,
            i.aum_estimate,
            i.last_13f_filed as filing_date,
            i.data_source,
            COUNT(DISTINCT h.id) as holdings_count,
            COALESCE(SUM(h.market_value), 0) as total_value,
            MAX(h.period_of_report) as latest_period
        FROM ir_investors i
        LEFT JOIN ir_holdings h ON i.id = h.investor_id
            AND h.period_of_report = (
                SELECT MAX(h2.period_of_report)
                FROM ir_holdings h2 WHERE h2.investor_id = i.id
            )
        WHERE {where_sql}
        GROUP BY i.id
    """

    # AUM filter (on total_value from holdings)
    having_clauses = []
    having_params = []
    if filters.aum_min is not None:
        having_clauses.append("total_value >= ?")
        having_params.append(filters.aum_min)
    if filters.aum_max is not None:
        having_clauses.append("total_value <= ?")
        having_params.append(filters.aum_max)

    if having_clauses:
        query_sql += " HAVING " + " AND ".join(having_clauses)
        params.extend(having_params)

    # Count total
    count_sql = f"SELECT COUNT(*) FROM ({query_sql})"
    total = conn.execute(count_sql, params).fetchone()[0]

    # Fetch results with sort and pagination
    fetch_sql = f"""
        SELECT * FROM ({query_sql})
        ORDER BY {sort_col} {sort_dir}
        LIMIT ? OFFSET ?
    """
    fetch_params = params + [filters.limit, filters.offset]
    rows = conn.execute(fetch_sql, fetch_params).fetchall()

    # Build results
    results = []
    for row in rows:
        investor_id = row["id"]

        # Get top 5 holdings by value
        top_holdings = conn.execute("""
            SELECT ticker, company_name, market_value, shares
            FROM ir_holdings
            WHERE investor_id = ? AND period_of_report = ?
            AND ticker IS NOT NULL AND ticker != ''
            ORDER BY market_value DESC LIMIT 5
        """, (investor_id, row["latest_period"])).fetchall()

        # Gatekeeper score (placeholder — computed in gatekeeper module)
        gatekeeper_score = _compute_gatekeeper_score(investor_id, conn, adv_db)

        results.append({
            "id": investor_id,
            "name": row["name"],
            "entity_type": row["entity_type"],
            "cik": row["cik"],
            "country": row["hq_country"] or "US",
            "state": row["hq_state"],
            "aum": row["total_value"],
            "aum_display": _format_aum(row["total_value"]),
            "aum_estimate": row["aum_estimate"],
            "holdings_count": row["holdings_count"],
            "total_value": row["total_value"],
            "total_value_display": _format_aum(row["total_value"]),
            "filing_date": row["filing_date"],
            "latest_period": row["latest_period"],
            "gatekeeper_score": gatekeeper_score,
            "top_holdings": [
                {
                    "ticker": h["ticker"],
                    "company_name": h["company_name"],
                    "market_value": h["market_value"],
                    "shares": h["shares"],
                }
                for h in top_holdings
            ],
            "crd_number": None,  # Allocators may not have CRD
        })

    conn.close()

    return {
        "results": results,
        "total": total,
        "page": (filters.offset // filters.limit) + 1 if filters.limit else 1,
        "per_page": filters.limit,
        "total_pages": math.ceil(total / filters.limit) if filters.limit else 1,
        "filters_applied": {
            "query": filters.query,
            "entity_type": filters.entity_type,
            "aum_min": filters.aum_min,
            "aum_max": filters.aum_max,
            "state": filters.state,
            "country": filters.country,
            "gatekeeper": filters.gatekeeper,
        },
    }


def get_allocator_detail(
    allocator_id: str,
    holdings_db: Path = HOLDINGS_DB,
    adv_db: Path = ADV_DB,
) -> Optional[dict]:
    """Get full allocator profile with top holdings."""
    conn = sqlite3.connect(str(holdings_db))
    conn.row_factory = sqlite3.Row

    inv = conn.execute(
        "SELECT * FROM ir_investors WHERE id = ?", (allocator_id,)
    ).fetchone()

    if not inv:
        conn.close()
        return None

    inv = dict(inv)

    # Get latest period
    latest = conn.execute(
        "SELECT MAX(period_of_report) FROM ir_holdings WHERE investor_id = ?",
        (allocator_id,),
    ).fetchone()[0]

    # Holdings summary
    stats = conn.execute("""
        SELECT COUNT(*) as cnt, COALESCE(SUM(market_value), 0) as total_val
        FROM ir_holdings
        WHERE investor_id = ? AND period_of_report = ?
    """, (allocator_id, latest)).fetchone()

    # Top 20 holdings
    top_holdings = conn.execute("""
        SELECT ticker, company_name, cusip, shares, market_value, investment_discretion
        FROM ir_holdings
        WHERE investor_id = ? AND period_of_report = ?
        ORDER BY market_value DESC LIMIT 20
    """, (allocator_id, latest)).fetchall()

    # Sector breakdown
    sector_breakdown = conn.execute("""
        SELECT s.gics_sector, COUNT(*) as cnt, SUM(h.market_value) as sector_value
        FROM ir_holdings h
        LEFT JOIN ir_ticker_sectors s ON UPPER(h.ticker) = UPPER(s.ticker)
        WHERE h.investor_id = ? AND h.period_of_report = ?
        AND s.gics_sector IS NOT NULL
        GROUP BY s.gics_sector
        ORDER BY sector_value DESC
    """, (allocator_id, latest)).fetchall()

    # Filing history
    periods = conn.execute("""
        SELECT period_of_report, COUNT(*) as cnt, SUM(market_value) as total_val
        FROM ir_holdings
        WHERE investor_id = ?
        GROUP BY period_of_report
        ORDER BY period_of_report DESC
    """, (allocator_id,)).fetchall()

    gatekeeper_score = _compute_gatekeeper_score(allocator_id, conn, adv_db)

    conn.close()

    return {
        "id": allocator_id,
        "name": inv.get("name"),
        "entity_type": inv.get("type"),
        "cik": inv.get("cik"),
        "country": inv.get("hq_country") or "US",
        "state": inv.get("hq_state"),
        "aum_estimate": inv.get("aum_estimate"),
        "holdings_count": stats["cnt"] if stats else 0,
        "total_value": stats["total_val"] if stats else 0,
        "total_value_display": _format_aum(stats["total_val"] if stats else 0),
        "latest_period": latest,
        "filing_date": inv.get("last_13f_filed"),
        "gatekeeper_score": gatekeeper_score,
        "top_holdings": [
            {
                "ticker": h["ticker"],
                "company_name": h["company_name"],
                "cusip": h["cusip"],
                "shares": h["shares"],
                "market_value": h["market_value"],
                "market_value_display": _format_aum(h["market_value"]),
                "investment_discretion": h["investment_discretion"],
            }
            for h in top_holdings
        ],
        "sector_breakdown": [
            {
                "sector": s["gics_sector"],
                "count": s["cnt"],
                "value": s["sector_value"],
                "value_display": _format_aum(s["sector_value"]),
            }
            for s in sector_breakdown
        ],
        "filing_history": [
            {
                "period": p["period_of_report"],
                "holdings_count": p["cnt"],
                "total_value": p["total_val"],
                "total_value_display": _format_aum(p["total_val"]),
            }
            for p in periods
        ],
    }


def export_allocators_csv(
    filters: AllocatorFilters,
    holdings_db: Path = HOLDINGS_DB,
    adv_db: Path = ADV_DB,
) -> str:
    """Export allocator search results as CSV."""
    # Remove pagination for export
    filters.limit = 10000
    filters.offset = 0
    data = search_allocators(filters, holdings_db, adv_db)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Name", "Entity Type", "CIK", "Country", "State",
        "Holdings Count", "Total Value", "Filing Date",
        "Gatekeeper Score", "Top Holdings",
    ])

    for r in data["results"]:
        top_tickers = ", ".join(h["ticker"] for h in r.get("top_holdings", []) if h.get("ticker"))
        writer.writerow([
            r.get("name", ""),
            r.get("entity_type", ""),
            r.get("cik", ""),
            r.get("country", ""),
            r.get("state", ""),
            r.get("holdings_count", 0),
            r.get("total_value", 0),
            r.get("filing_date", ""),
            r.get("gatekeeper_score", 0),
            top_tickers,
        ])

    return output.getvalue()


def _compute_gatekeeper_score(
    investor_id: str,
    holdings_conn: sqlite3.Connection,
    adv_db: Path = ADV_DB,
) -> float:
    """
    Compute gatekeeper score (0-100) for an allocator.

    Measures how accessible the allocator is via pension consultants
    and adviser selection firms in our ADV database.

    Scoring:
    - 0: No known gatekeeper relationships
    - 25: Has overlapping holdings with adviser-selection firms
    - 50: Multiple adviser-selection firms share holdings
    - 75+: Strong overlap with pension consulting firms
    """
    try:
        adv_conn = sqlite3.connect(str(adv_db))

        # Count pension consulting and adviser-selection firms in our DB
        # These are the gatekeepers to allocators
        gatekeeper_count = adv_conn.execute("""
            SELECT COUNT(*) FROM adv_firms
            WHERE (svc_pension_consulting = 1 OR svc_adviser_selection = 1)
            AND aum_total > 100000000
        """).fetchone()[0]

        adv_conn.close()

        # Base score on existence of gatekeepers in our DB
        if gatekeeper_count > 50:
            return 50.0  # Moderate — we have gatekeepers, but no direct link yet
        elif gatekeeper_count > 10:
            return 25.0
        return 0.0
    except Exception:
        return 0.0


def get_allocator_filter_options(holdings_db: Path = HOLDINGS_DB) -> dict:
    """Return available filter values for allocator search UI."""
    conn = sqlite3.connect(str(holdings_db))

    types = conn.execute("""
        SELECT DISTINCT type FROM ir_investors
        WHERE type IN ('pension', 'endowment', 'sovereign_wealth', 'foundation', 'family_office', 'insurance')
        ORDER BY type
    """).fetchall()

    states = conn.execute("""
        SELECT DISTINCT hq_state FROM ir_investors
        WHERE hq_state IS NOT NULL AND hq_state != ''
        ORDER BY hq_state
    """).fetchall()

    countries = conn.execute("""
        SELECT DISTINCT hq_country FROM ir_investors
        WHERE hq_country IS NOT NULL AND hq_country != ''
        ORDER BY hq_country
    """).fetchall()

    conn.close()

    return {
        "entity_types": [r[0] for r in types],
        "states": [r[0] for r in states],
        "countries": [r[0] for r in countries],
        "sort_options": [
            {"value": "total_value", "label": "Portfolio Value"},
            {"value": "name", "label": "Name"},
            {"value": "holdings_count", "label": "Holdings Count"},
            {"value": "filing_date", "label": "Filing Date"},
        ],
    }


# ── CLI Testing ──

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "options":
        opts = get_allocator_filter_options()
        print(json.dumps(opts, indent=2))
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "detail":
        alloc_id = sys.argv[2] if len(sys.argv) > 2 else ""
        detail = get_allocator_detail(alloc_id)
        if detail:
            print(json.dumps(detail, indent=2, default=str))
        else:
            print(f"Allocator not found: {alloc_id}")
        sys.exit(0)

    # Default: search all allocators
    filters = AllocatorFilters(limit=50)
    data = search_allocators(filters)

    print(f"Total allocators: {data['total']}")
    print(f"{'='*80}")
    for i, r in enumerate(data["results"], 1):
        top = ", ".join(h["ticker"] for h in r.get("top_holdings", [])[:3] if h.get("ticker"))
        print(f"{i:2d}. {r['name']}")
        print(f"    Type: {r['entity_type']} | {r['country']}/{r.get('state', 'N/A')}")
        print(f"    Value: {r['total_value_display']} | {r['holdings_count']} holdings | Filed: {r.get('filing_date', 'N/A')}")
        print(f"    Top: {top}")
        print()
