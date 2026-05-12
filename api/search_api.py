#!/usr/bin/env python3
"""
PureBrain IR — Search API (Sprint 1B)
Implements ally's core workflow: filtered search → ranked results → contact info

Can be used standalone or as a module imported by a web framework.
Designed for eventual deployment as a Cloudflare Worker (D1 SQLite compatible).
"""

import json
import math
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
DEFAULT_DB = SCRIPT_DIR / "purebrain_ir.db"


@dataclass
class SearchFilters:
    """Maps to ally's 5 Irwin filters."""

    # Filter 1: Geography (state, city, or country)
    state: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None

    # Filter 2: Client type (individual, hnw, corporate, pension, etc.)
    client_type: Optional[str] = None  # "individual", "hnw", "corporate", "pension", "pooled", "charity"

    # Filter 3: AUM range
    aum_min: Optional[float] = None
    aum_max: Optional[float] = None

    # Filter 4: Service type
    service: Optional[str] = None  # "financial_planning", "portfolio_indiv", "portfolio_biz", "pension_consulting", "adviser_selection"

    # Text search (firm name)
    query: Optional[str] = None

    # Firm type filter: "all", "ia", "era"
    firm_type: str = "all"

    # Pagination
    limit: int = 25
    offset: int = 0

    # Sort
    sort_by: str = "aum_total"  # "aum_total", "legal_name", "clients_total", "state", "filing_date"
    sort_dir: str = "DESC"


CLIENT_TYPE_MAP = {
    "individual": "clients_individuals",
    "hnw": "clients_hnw",
    "corporate": "clients_corporate",
    "pension": "clients_pension",
    "pooled": "clients_pooled",
    "charity": "clients_charity",
    "banking": "clients_banking",
    "insurance": "clients_insurance",
    "govt": "clients_govt",
    "sovereign": "clients_sovereign",
}

SERVICE_MAP = {
    "financial_planning": "svc_financial_planning",
    "portfolio_indiv": "svc_portfolio_indiv",
    "portfolio_biz": "svc_portfolio_biz",
    "pension_consulting": "svc_pension_consulting",
    "adviser_selection": "svc_adviser_selection",
    "publications": "svc_publications",
    "commodities": "svc_commodities",
}

SORT_WHITELIST = {"aum_total", "legal_name", "filing_date", "state", "city", "fit_score"}


def _format_name(name: str) -> str:
    """Convert 'LAST, FIRST, MIDDLE' to 'First Middle Last'."""
    parts = [p.strip() for p in name.split(",")]
    if len(parts) >= 2:
        # LAST, FIRST, MIDDLE -> First Middle Last
        last = parts[0].title()
        first = parts[1].title()
        middle = parts[2].title() if len(parts) > 2 else ""
        return f"{first} {middle} {last}".replace("  ", " ").strip()
    return name.title()


def search_firms(
    filters: SearchFilters,
    db_path: Path = DEFAULT_DB,
) -> dict:
    """
    Execute a filtered search against the ADV firms database.

    Returns:
        {
            "results": [...],
            "total": int,
            "page": int,
            "per_page": int,
            "filters_applied": {...}
        }
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Build WHERE clauses common to both IA and ERA tables
    where_clauses = []
    params = []

    # Geography filter
    if filters.state:
        where_clauses.append("state = ?")
        params.append(filters.state.upper())
    if filters.city:
        where_clauses.append("LOWER(city) = LOWER(?)")
        params.append(filters.city)
    if filters.country:
        where_clauses.append("LOWER(country) LIKE LOWER(?)")
        params.append(f"%{filters.country}%")

    # Client type filter (IA-only columns — ERA rows will be excluded by this)
    if filters.client_type:
        col = CLIENT_TYPE_MAP.get(filters.client_type.lower())
        if col:
            where_clauses.append(f"{col} > 0")

    # AUM range filter
    if filters.aum_min is not None:
        where_clauses.append("aum_total >= ?")
        params.append(filters.aum_min)
    if filters.aum_max is not None:
        where_clauses.append("aum_total <= ?")
        params.append(filters.aum_max)

    # Service filter (IA-only columns — ERA rows will be excluded by this)
    if filters.service:
        col = SERVICE_MAP.get(filters.service.lower())
        if col:
            where_clauses.append(f"{col} = 1")

    # Text search (firm name)
    if filters.query:
        where_clauses.append("(LOWER(legal_name) LIKE LOWER(?) OR LOWER(dba_name) LIKE LOWER(?))")
        params.append(f"%{filters.query}%")
        params.append(f"%{filters.query}%")

    # Build query
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # Sort
    # fit_score is handled post-query in server.py, use aum_total for SQL ordering
    sort_col = filters.sort_by if filters.sort_by in SORT_WHITELIST and filters.sort_by != "fit_score" else "aum_total"
    sort_dir = "ASC" if filters.sort_dir.upper() == "ASC" else "DESC"

    # Determine which tables to query
    include_ia = filters.firm_type in ("all", "ia")
    include_era = filters.firm_type in ("all", "era")

    # IA-only filters make ERA irrelevant
    if filters.client_type or filters.service:
        include_era = False

    # Build UNION query or single-table query
    ia_select = f"""
        SELECT
            crd_number, legal_name, dba_name, sec_number, cik_number,
            street1, street2, city, state, country, postal_code,
            phone, fax, has_website, business_hours,
            aum_total, aum_discretionary, aum_nondiscretionary,
            clients_individuals, clients_hnw, clients_corporate,
            clients_pension, clients_pooled, clients_charity,
            clients_insurance, clients_sovereign, clients_govt,
            svc_financial_planning, svc_portfolio_indiv, svc_portfolio_biz,
            svc_pension_consulting, svc_adviser_selection,
            entity_type, filing_date, 'IA' as firm_type
        FROM adv_firms
        WHERE {where_sql}
    """

    era_select = f"""
        SELECT
            crd_number, legal_name, dba_name, sec_number, NULL as cik_number,
            street1, street2, city, state, country, postal_code,
            phone, fax, has_website, NULL as business_hours,
            aum_total, 0 as aum_discretionary, 0 as aum_nondiscretionary,
            0 as clients_individuals, 0 as clients_hnw, 0 as clients_corporate,
            0 as clients_pension, 0 as clients_pooled, 0 as clients_charity,
            0 as clients_insurance, 0 as clients_sovereign, 0 as clients_govt,
            0 as svc_financial_planning, 0 as svc_portfolio_indiv, 0 as svc_portfolio_biz,
            0 as svc_pension_consulting, 0 as svc_adviser_selection,
            entity_type, filing_date, 'ERA' as firm_type
        FROM era_firms
        WHERE {where_sql}
    """

    if include_ia and include_era:
        combined_sql = f"{ia_select} UNION ALL {era_select}"
        count_params = params + params  # WHERE params needed for both
    elif include_ia:
        combined_sql = ia_select
        count_params = list(params)
    else:
        combined_sql = era_select
        count_params = list(params)

    # Count total
    count_sql = f"SELECT COUNT(*) FROM ({combined_sql})"
    total = conn.execute(count_sql, count_params).fetchone()[0]

    # Fetch results with sort and pagination
    select_sql = f"""
        SELECT * FROM ({combined_sql})
        ORDER BY {sort_col} {sort_dir}
        LIMIT ? OFFSET ?
    """
    fetch_params = count_params + [filters.limit, filters.offset]
    rows = conn.execute(select_sql, fetch_params).fetchall()

    results = []
    for row in rows:
        firm = dict(row)
        # Preserve firm_type tag
        firm_type_tag = firm.get("firm_type", "IA")
        # Format AUM for display
        aum = firm.get("aum_total", 0) or 0
        if aum >= 1e12:
            firm["aum_display"] = f"${aum/1e12:.1f}T"
        elif aum >= 1e9:
            firm["aum_display"] = f"${aum/1e9:.1f}B"
        elif aum >= 1e6:
            firm["aum_display"] = f"${aum/1e6:.0f}M"
        elif aum > 0:
            firm["aum_display"] = f"${aum/1e3:.0f}K"
        else:
            firm["aum_display"] = "N/A"

        # Aggregate client count
        firm["clients_total"] = sum([
            firm.get("clients_individuals", 0) or 0,
            firm.get("clients_hnw", 0) or 0,
            firm.get("clients_corporate", 0) or 0,
            firm.get("clients_pension", 0) or 0,
            firm.get("clients_pooled", 0) or 0,
            firm.get("clients_charity", 0) or 0,
            firm.get("clients_insurance", 0) or 0,
            firm.get("clients_sovereign", 0) or 0,
            firm.get("clients_govt", 0) or 0,
        ])

        # Build services list
        services = []
        svc_labels = {
            "svc_financial_planning": "Financial Planning",
            "svc_portfolio_indiv": "Portfolio Mgmt (Individual)",
            "svc_portfolio_biz": "Portfolio Mgmt (Business)",
            "svc_pension_consulting": "Pension Consulting",
            "svc_adviser_selection": "Adviser Selection",
        }
        for col, label in svc_labels.items():
            if firm.get(col):
                services.append(label)
        firm["services_list"] = services

        # Address display
        parts = [firm.get("street1", ""), firm.get("city", ""), firm.get("state", "")]
        firm["address_display"] = ", ".join(p for p in parts if p)

        # Key executives (top 3 by control person status) — IA firms only
        if firm_type_tag == "IA":
            exec_rows = conn.execute(
                "SELECT full_name, title FROM firm_executives "
                "WHERE crd_number = ? ORDER BY is_control_person DESC, rowid ASC LIMIT 3",
                (firm["crd_number"],),
            ).fetchall()
            firm["key_executives"] = [
                {"name": _format_name(r[0]), "title": r[1]} for r in exec_rows
            ]
        else:
            firm["key_executives"] = []

        results.append(firm)

    conn.close()

    return {
        "results": results,
        "total": total,
        "page": (filters.offset // filters.limit) + 1,
        "per_page": filters.limit,
        "total_pages": math.ceil(total / filters.limit) if filters.limit else 1,
        "filters_applied": {
            "state": filters.state,
            "city": filters.city,
            "country": filters.country,
            "client_type": filters.client_type,
            "aum_min": filters.aum_min,
            "aum_max": filters.aum_max,
            "service": filters.service,
            "query": filters.query,
            "firm_type": filters.firm_type,
        },
    }


def get_firm_detail(crd_number: str, db_path: Path = DEFAULT_DB) -> dict | None:
    """Get full firm profile by CRD number. Checks both IA and ERA tables."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Try IA first
    row = conn.execute(
        "SELECT *, 'IA' as firm_type FROM adv_firms WHERE crd_number = ?", (crd_number,)
    ).fetchone()

    # Fall back to ERA
    if not row:
        row = conn.execute(
            "SELECT *, 'ERA' as firm_type FROM era_firms WHERE crd_number = ?", (crd_number,)
        ).fetchone()

    if not row:
        conn.close()
        return None

    firm = dict(row)

    # All executives (IA firms only — ERA firms don't have executive data)
    if firm.get("firm_type") == "IA":
        exec_rows = conn.execute(
            "SELECT full_name, title, is_control_person, ownership_code "
            "FROM firm_executives WHERE crd_number = ? "
            "ORDER BY is_control_person DESC, rowid ASC",
            (crd_number,),
        ).fetchall()
        firm["executives"] = [
            {
                "name": _format_name(r[0]),
                "title": r[1],
                "control_person": bool(r[2]),
                "ownership": r[3],
            }
            for r in exec_rows
        ]
    else:
        firm["executives"] = []

    conn.close()
    return firm


def get_filter_options(db_path: Path = DEFAULT_DB) -> dict:
    """Return available filter values for UI dropdowns."""
    conn = sqlite3.connect(str(db_path))

    states = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT state FROM adv_firms WHERE state != '' ORDER BY state"
        ).fetchall()
    ]

    countries = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT country FROM adv_firms WHERE country != '' ORDER BY country"
        ).fetchall()
    ]

    conn.close()

    return {
        "states": states,
        "countries": countries,
        "client_types": list(CLIENT_TYPE_MAP.keys()),
        "services": list(SERVICE_MAP.keys()),
        "firm_types": [
            {"value": "all", "label": "All Firms"},
            {"value": "ia", "label": "Investment Advisers (IA)"},
            {"value": "era", "label": "Exempt Reporting Advisers (ERA)"},
        ],
        "aum_ranges": [
            {"label": "Any", "min": None, "max": None},
            {"label": "<$25M", "min": 0, "max": 25_000_000},
            {"label": "$25M - $100M", "min": 25_000_000, "max": 100_000_000},
            {"label": "$100M - $500M", "min": 100_000_000, "max": 500_000_000},
            {"label": "$500M - $1B", "min": 500_000_000, "max": 1_000_000_000},
            {"label": "$1B - $10B", "min": 1_000_000_000, "max": 10_000_000_000},
            {"label": "$10B - $100B", "min": 10_000_000_000, "max": 100_000_000_000},
            {"label": "$100B+", "min": 100_000_000_000, "max": None},
        ],
    }


def export_csv(filters: SearchFilters, db_path: Path = DEFAULT_DB) -> str:
    """Export search results as CSV string."""
    import csv
    import io

    # Remove pagination limit for export
    filters.limit = 10000
    filters.offset = 0
    data = search_firms(filters, db_path)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "CRD Number", "Legal Name", "DBA Name", "SEC Number", "CIK Number",
        "Street", "City", "State", "Country", "Postal Code",
        "Phone", "Fax", "Website", "Entity Type", "Firm Type",
        "AUM Total", "AUM Discretionary", "AUM Non-Discretionary",
        "Clients Individual", "Clients HNW", "Clients Corporate",
        "Clients Pension", "Clients Pooled", "Clients Charity",
        "Services", "Filing Date",
    ])

    for firm in data["results"]:
        writer.writerow([
            firm.get("crd_number", ""),
            firm.get("legal_name", ""),
            firm.get("dba_name", ""),
            firm.get("sec_number", ""),
            firm.get("cik_number", ""),
            firm.get("street1", ""),
            firm.get("city", ""),
            firm.get("state", ""),
            firm.get("country", ""),
            firm.get("postal_code", ""),
            firm.get("phone", ""),
            firm.get("fax", ""),
            "Yes" if firm.get("has_website") else "No",
            firm.get("entity_type", ""),
            firm.get("firm_type", "IA"),
            firm.get("aum_total", 0),
            firm.get("aum_discretionary", 0),
            firm.get("aum_nondiscretionary", 0),
            firm.get("clients_individuals", 0),
            firm.get("clients_hnw", 0),
            firm.get("clients_corporate", 0),
            firm.get("clients_pension", 0),
            firm.get("clients_pooled", 0),
            firm.get("clients_charity", 0),
            "; ".join(firm.get("services_list", [])),
            firm.get("filing_date", ""),
        ])

    return output.getvalue()


# ── CLI for testing ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "options":
        opts = get_filter_options()
        print(json.dumps(opts, indent=2))
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "detail":
        crd = sys.argv[2] if len(sys.argv) > 2 else "105958"
        firm = get_firm_detail(crd)
        if firm:
            print(json.dumps(firm, indent=2, default=str))
        else:
            print(f"Firm not found: CRD {crd}")
        sys.exit(0)

    # Default: run ally's test query
    filters = SearchFilters(
        state="TX",
        client_type="individual",
        aum_min=1_000_000_000,
        limit=10,
    )

    # Override from CLI
    if "--state" in sys.argv:
        idx = sys.argv.index("--state")
        filters.state = sys.argv[idx + 1]
    if "--client" in sys.argv:
        idx = sys.argv.index("--client")
        filters.client_type = sys.argv[idx + 1]
    if "--aum-min" in sys.argv:
        idx = sys.argv.index("--aum-min")
        filters.aum_min = float(sys.argv[idx + 1])
    if "--service" in sys.argv:
        idx = sys.argv.index("--service")
        filters.service = sys.argv[idx + 1]
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        filters.limit = int(sys.argv[idx + 1])

    result = search_firms(filters)

    print(f"\n{'='*70}")
    print(f"SEARCH RESULTS: {result['total']} firms found (page {result['page']}/{result['total_pages']})")
    print(f"Filters: {json.dumps(result['filters_applied'])}")
    print(f"{'='*70}\n")

    for i, firm in enumerate(result["results"], 1):
        print(f"{i:2d}. {firm['legal_name']}")
        print(f"    CRD: {firm['crd_number']} | {firm['address_display']}")
        print(f"    AUM: {firm['aum_display']} | Phone: {firm['phone']}")
        print(f"    Clients: {firm['clients_total']} total | Services: {', '.join(firm['services_list'])}")
        print()
