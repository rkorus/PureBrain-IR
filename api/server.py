#!/usr/bin/env python3
"""
PureBrain IR — API Server (Sprint 1B)
FastAPI wrapper around search_api.py

Run: uvicorn server:app --host 0.0.0.0 --port 8890
"""

from pathlib import Path

from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional

from search_api import SearchFilters, search_firms, get_firm_detail, get_filter_options, export_csv
from fit_score import FitContext, compute_fit_score, batch_score
from peer_analysis import PeerQuery, analyze_peers
from allocator_api import AllocatorFilters, search_allocators, get_allocator_detail, export_allocators_csv, get_allocator_filter_options
from gatekeeper import compute_gatekeeper_score, search_gatekeepers
from allocator_fit_score import FundContext, compute_allocator_fit_score, batch_score_allocators
from outreach_engine import generate_lp_draft

app = FastAPI(
    title="PureBrain IR API",
    version="0.1.0",
    description="AI Investor Intelligence — Search SEC-registered investment advisers",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _build_filters(
    state=None, city=None, country=None, client_type=None,
    aum_min=None, aum_max=None, service=None, query=None,
    sort_by="aum_total", sort_dir="DESC", limit=25, offset=0,
    firm_type="all",
):
    return SearchFilters(
        state=state, city=city, country=country,
        client_type=client_type, aum_min=aum_min, aum_max=aum_max,
        service=service, query=query,
        sort_by=sort_by, sort_dir=sort_dir, limit=limit, offset=offset,
        firm_type=firm_type,
    )


@app.get("/api/search/firms")
async def search(
    state: Optional[str] = Query(None, description="2-letter state code"),
    city: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    client_type: Optional[str] = Query(None, description="individual|hnw|corporate|pension|pooled|charity"),
    aum_min: Optional[float] = Query(None, description="Minimum AUM in dollars"),
    aum_max: Optional[float] = Query(None, description="Maximum AUM in dollars"),
    service: Optional[str] = Query(None, description="financial_planning|portfolio_indiv|portfolio_biz|pension_consulting|adviser_selection"),
    query: Optional[str] = Query(None, description="Search by firm name"),
    sort_by: str = Query("aum_total"),
    sort_dir: str = Query("DESC"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    firm_type: str = Query("all", description="all|ia|era"),
    # AI Fit Score parameters
    fit_score: bool = Query(False, description="Enable AI Fit Score computation"),
    target_tickers: Optional[str] = Query(None, description="Comma-separated target tickers, e.g. AAPL,MSFT,NVDA"),
    target_sector: Optional[str] = Query(None, description="Target sector, e.g. Technology"),
    target_raise_size: Optional[float] = Query(None, description="Target fundraise size in dollars"),
):
    """Search investment adviser firms with ally's 5 Irwin filters + text search."""
    filters = _build_filters(
        state=state, city=city, country=country, client_type=client_type,
        aum_min=aum_min, aum_max=aum_max, service=service, query=query,
        sort_by=sort_by, sort_dir=sort_dir, limit=limit, offset=offset,
        firm_type=firm_type,
    )
    data = search_firms(filters)

    # Compute AI Fit Score if requested
    if fit_score:
        ctx = FitContext(
            target_tickers=target_tickers.split(",") if target_tickers else [],
            target_sector=target_sector,
            preferred_state=state,
            preferred_aum_min=aum_min,
            preferred_aum_max=aum_max,
            preferred_client_type=client_type,
            target_raise_size=target_raise_size,
        )
        from dataclasses import asdict
        for firm in data["results"]:
            score = compute_fit_score(firm["crd_number"], ctx)
            firm["fit_score"] = asdict(score)

        # Only re-sort by fit score if user explicitly selected fit_score sort
        if sort_by == "fit_score":
            data["results"].sort(key=lambda f: f.get("fit_score", {}).get("total_score", 0), reverse=(sort_dir.upper() == "DESC"))

    return data


@app.get("/api/search/export")
async def search_export(
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    client_type: Optional[str] = Query(None),
    aum_min: Optional[float] = Query(None),
    aum_max: Optional[float] = Query(None),
    service: Optional[str] = Query(None),
    query: Optional[str] = Query(None),
    sort_by: str = Query("aum_total"),
    sort_dir: str = Query("DESC"),
    firm_type: str = Query("all"),
):
    """Export search results as CSV download."""
    from fastapi.responses import Response

    filters = _build_filters(
        state=state, city=city, country=country, client_type=client_type,
        aum_min=aum_min, aum_max=aum_max, service=service, query=query,
        sort_by=sort_by, sort_dir=sort_dir, firm_type=firm_type,
    )
    csv_data = export_csv(filters)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=purebrain-ir-export.csv"},
    )


@app.get("/api/firms/{crd_number}")
async def firm_detail(crd_number: str):
    """Get full firm profile by CRD number."""
    firm = get_firm_detail(crd_number)
    if not firm:
        return JSONResponse(status_code=404, content={"error": "Firm not found"})

    # Add disclosure summary if available
    import sqlite3
    db_path = Path(__file__).parent / "purebrain_ir.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    disc = conn.execute(
        "SELECT risk_flag, total_disclosures, regulatory_count, criminal_count, "
        "civil_count, total_monetary FROM firm_disclosure_summary WHERE crd_number = ?",
        (crd_number,),
    ).fetchone()
    conn.close()

    if disc:
        firm["disclosure_summary"] = dict(disc)
    else:
        firm["disclosure_summary"] = {"risk_flag": "clean", "total_disclosures": 0}

    return firm


@app.get("/api/fit-score/{crd_number}")
async def fit_score_detail(
    crd_number: str,
    target_tickers: Optional[str] = Query(None),
    target_sector: Optional[str] = Query(None),
    preferred_state: Optional[str] = Query(None),
    preferred_aum_min: Optional[float] = Query(None),
    preferred_aum_max: Optional[float] = Query(None),
    preferred_client_type: Optional[str] = Query(None),
    target_raise_size: Optional[float] = Query(None),
):
    """Compute AI Fit Score for a single firm."""
    from dataclasses import asdict
    ctx = FitContext(
        target_tickers=target_tickers.split(",") if target_tickers else [],
        target_sector=target_sector,
        preferred_state=preferred_state,
        preferred_aum_min=preferred_aum_min,
        preferred_aum_max=preferred_aum_max,
        preferred_client_type=preferred_client_type,
        target_raise_size=target_raise_size,
    )
    score = compute_fit_score(crd_number, ctx)
    return asdict(score)


@app.get("/api/firms/{crd_number}/contacts")
async def firm_contacts(crd_number: str):
    """Get enriched executive contacts for a firm by CRD number."""
    from contact_enrichment import enrich_firm_contacts

    data = enrich_firm_contacts(crd_number)
    if "error" in data:
        return JSONResponse(status_code=404, content={"error": data["error"]})

    return {
        "crd_number": data["crd_number"],
        "firm_name": data["firm_name"],
        "firm_phone": data["firm_phone"],
        "firm_domain": data["firm_domain"],
        "total_executives": data["total"],
        "contacts": data["contacts"],
    }


@app.get("/api/firms/{crd_number}/disclosures")
async def firm_disclosures(crd_number: str):
    """Get regulatory/criminal/civil disclosure history for a firm."""
    import sqlite3

    db_path = Path(__file__).parent / "purebrain_ir.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Get summary
    summary = conn.execute(
        "SELECT * FROM firm_disclosure_summary WHERE crd_number = ?",
        (crd_number,),
    ).fetchone()

    # Get detailed disclosures
    disclosures = conn.execute(
        "SELECT disclosure_type, initiator_type, initiated_by, principal_sanction, "
        "date_initiated, case_number, allegations, status, resolution, "
        "resolution_date, monetary_amount, has_bar, has_suspension, summary "
        "FROM firm_disclosures WHERE crd_number = ? "
        "ORDER BY date_initiated DESC",
        (crd_number,),
    ).fetchall()

    conn.close()

    return {
        "crd_number": crd_number,
        "risk_flag": dict(summary)["risk_flag"] if summary else "clean",
        "summary": dict(summary) if summary else {
            "total_disclosures": 0, "regulatory_count": 0,
            "criminal_count": 0, "civil_count": 0,
            "total_monetary": 0, "risk_flag": "clean",
        },
        "disclosures": [dict(d) for d in disclosures],
    }


@app.get("/api/peer-analysis")
async def peer_analysis(
    target_ticker: Optional[str] = Query(None, description="Your company's ticker (excluded from results unless include_target_holders=true)"),
    peer_tickers: str = Query(..., description="Comma-separated peer tickers, e.g. SNOW,MDB,DDOG"),
    target_sector: Optional[str] = Query(None, description="Target sector for affinity scoring, e.g. Technology"),
    min_overlap: int = Query(1, ge=1, description="Minimum peers held to appear in results"),
    include_target_holders: bool = Query(False, description="Include investors who already hold the target"),
    limit: int = Query(50, ge=1, le=200),
):
    """Peer-based investor targeting: find investors who hold your peers."""
    query = PeerQuery(
        target_ticker=target_ticker,
        peer_tickers=[t.strip() for t in peer_tickers.split(",") if t.strip()],
        target_sector=target_sector,
        min_overlap=min_overlap,
        include_target_holders=include_target_holders,
        limit=limit,
    )
    return analyze_peers(query)


@app.get("/api/outreach/templates")
async def outreach_templates():
    """List available outreach email templates."""
    from outreach_engine import list_templates
    return {"templates": list_templates()}


@app.post("/api/outreach/draft")
async def outreach_draft(
    crd_number: str = Body(...),
    template_id: str = Body("intro"),
    target_company: str = Body(""),
    target_sector: Optional[str] = Body(None),
    target_tickers: Optional[str] = Body(None),
    raise_type: str = Body("fundraise"),
    sender_name: str = Body(""),
    sender_title: str = Body(""),
    mutual_connection: Optional[str] = Body(None),
    update_line: Optional[str] = Body(None),
    save: bool = Body(True, description="Save draft to DB"),
):
    """Generate a context-aware outreach email draft."""
    from dataclasses import asdict
    from outreach_engine import generate_draft, save_draft

    ctx = {
        "target_company": target_company,
        "target_sector": target_sector,
        "target_tickers": target_tickers.split(",") if target_tickers else [],
        "raise_type": raise_type,
        "sender_name": sender_name,
        "sender_title": sender_title,
    }
    if mutual_connection:
        ctx["mutual_connection"] = mutual_connection
    if update_line:
        ctx["update_line"] = update_line

    try:
        draft = generate_draft(crd_number, template_id, target_context=ctx)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    result = asdict(draft)
    if save:
        draft_id = save_draft(draft)
        result["draft_id"] = draft_id

    return result


@app.get("/api/outreach/history")
async def outreach_history(
    crd_number: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Get outreach draft history."""
    from outreach_engine import get_outreach_history
    drafts = get_outreach_history(crd_number=crd_number, status=status, limit=limit)
    return {"total": len(drafts), "drafts": drafts}


@app.get("/api/outreach/stats")
async def outreach_stats():
    """Get outreach analytics summary."""
    from outreach_engine import get_outreach_stats
    return get_outreach_stats()


@app.post("/api/outreach/{draft_id}/status")
async def update_outreach_status(
    draft_id: int,
    status: str = Body(..., embed=True),
):
    """Update outreach draft status (draft, sent, opened, replied, archived)."""
    from outreach_engine import update_draft_status
    valid = ["draft", "sent", "opened", "replied", "archived"]
    if status not in valid:
        return JSONResponse(status_code=400, content={"error": f"Invalid status. Use: {valid}"})
    update_draft_status(draft_id, status)
    return {"draft_id": draft_id, "status": status}


@app.get("/api/search/options")
async def filter_options():
    """Available filter values for UI dropdowns."""
    return get_filter_options()


# ── Allocator Search Endpoints (Sprint 3A) ──

@app.get("/api/search/allocators")
async def search_allocators_endpoint(
    query: Optional[str] = Query(None, description="Search by allocator name"),
    entity_type: Optional[str] = Query(None, description="pension|endowment|sovereign_wealth|foundation|family_office|insurance"),
    aum_min: Optional[float] = Query(None, description="Minimum portfolio value"),
    aum_max: Optional[float] = Query(None, description="Maximum portfolio value"),
    state: Optional[str] = Query(None, description="US state (2-letter code)"),
    country: Optional[str] = Query(None, description="Country (2-letter ISO code)"),
    gatekeeper: Optional[bool] = Query(None, description="Filter by gatekeeper relationships"),
    sort_by: str = Query("total_value", description="total_value|name|holdings_count|filing_date|allocator_fit_score"),
    sort_dir: str = Query("DESC"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    # LP Fit Score parameters (Sprint 3B)
    fit_score: bool = Query(False, description="Enable LP Fit Score computation"),
    target_sectors: Optional[str] = Query(None, description="Comma-separated target GICS sectors"),
    fund_size: Optional[float] = Query(None, description="Target fund size in dollars"),
    strategy_type: Optional[str] = Query(None, description="venture|growth|buyout|infrastructure|real_estate"),
):
    """Search allocator-type investors (pension funds, endowments, SWFs)."""
    filters = AllocatorFilters(
        query=query, entity_type=entity_type,
        aum_min=aum_min, aum_max=aum_max,
        state=state, country=country, gatekeeper=gatekeeper,
        sort_by=sort_by, sort_dir=sort_dir,
        limit=limit, offset=offset,
    )
    data = search_allocators(filters)

    # Compute LP Fit Score if requested
    if fit_score:
        from dataclasses import asdict
        fund_ctx = FundContext(
            target_sectors=[s.strip() for s in target_sectors.split(",")] if target_sectors else [],
            fund_size=fund_size,
            min_commitment=fund_size * 0.1 if fund_size else None,
            fund_domicile="US",
            strategy_type=strategy_type or "venture",
        )
        for allocator in data["results"]:
            score = compute_allocator_fit_score(allocator["id"], fund_ctx)
            allocator["allocator_fit_score"] = asdict(score)

        # Re-sort by fit score if requested
        if sort_by == "allocator_fit_score":
            data["results"].sort(
                key=lambda a: a.get("allocator_fit_score", {}).get("total_score", 0),
                reverse=(sort_dir.upper() == "DESC"),
            )

    return data


@app.get("/api/allocators/{allocator_id}/fit-score")
async def allocator_fit_score_endpoint(
    allocator_id: str,
    target_sectors: Optional[str] = Query(None, description="Comma-separated target GICS sectors"),
    fund_size: Optional[float] = Query(None, description="Target fund size in dollars"),
    min_commitment: Optional[float] = Query(None, description="Minimum LP commitment"),
    strategy_type: Optional[str] = Query(None, description="venture|growth|buyout|infrastructure|real_estate"),
    fund_domicile: str = Query("US", description="Fund domicile country"),
):
    """Compute LP Fit Score for a single allocator."""
    from dataclasses import asdict
    fund_ctx = FundContext(
        target_sectors=[s.strip() for s in target_sectors.split(",")] if target_sectors else [],
        fund_size=fund_size,
        min_commitment=min_commitment or (fund_size * 0.1 if fund_size else None),
        fund_domicile=fund_domicile,
        strategy_type=strategy_type or "venture",
    )
    score = compute_allocator_fit_score(allocator_id, fund_ctx)
    return asdict(score)


@app.post("/api/outreach/lp-draft")
async def lp_outreach_draft(
    allocator_id: str = Body(...),
    template_id: str = Body("lp_fund_intro"),
    fund_name: str = Body(""),
    fund_strategy: str = Body("venture capital"),
    fund_sector: Optional[str] = Body(None),
    target_sectors: Optional[list] = Body(None),
    fund_size: Optional[float] = Body(None),
    fund_thesis: Optional[str] = Body(None),
    sender_name: str = Body(""),
    sender_title: str = Body(""),
    # Co-investment fields
    deal_company: Optional[str] = Body(None),
    deal_round: Optional[str] = Body(None),
    deal_description: Optional[str] = Body(None),
    deal_rationale: Optional[str] = Body(None),
    # Capital update fields
    fund_update: Optional[str] = Body(None),
    deployed_amount: Optional[str] = Body(None),
    active_investments: Optional[str] = Body(None),
    key_milestone: Optional[str] = Body(None),
    close_date: Optional[str] = Body(None),
):
    """Generate an LP outreach email draft for an allocator."""
    from dataclasses import asdict

    # Build fund context from either fund_sector (frontend) or target_sectors
    sectors = target_sectors or ([fund_sector] if fund_sector else [])

    fund_context = {
        "fund_name": fund_name,
        "fund_strategy": fund_strategy,
        "target_sectors": sectors,
        "fund_size": fund_size,
        "fund_thesis": fund_thesis or f"identifying high-growth opportunities in {fund_strategy}",
        "sender_name": sender_name,
        "sender_title": sender_title,
        "deal_company": deal_company or "[Company Name]",
        "deal_round": deal_round or "[Round]",
        "deal_description": deal_description or "[company description]",
        "deal_rationale": deal_rationale or "[investment rationale]",
        "fund_update": fund_update or "",
        "deployed_amount": deployed_amount or "[amount]",
        "active_investments": active_investments or "[count]",
        "key_milestone": key_milestone or "[milestone]",
        "close_date": close_date or "[date]",
    }

    try:
        draft = generate_lp_draft(allocator_id, template_id, fund_context)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

    return asdict(draft)


@app.get("/api/search/allocators/export")
async def allocators_export(
    query: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    aum_min: Optional[float] = Query(None),
    aum_max: Optional[float] = Query(None),
    state: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    sort_by: str = Query("total_value"),
    sort_dir: str = Query("DESC"),
):
    """Export allocator search results as CSV."""
    from fastapi.responses import Response

    filters = AllocatorFilters(
        query=query, entity_type=entity_type,
        aum_min=aum_min, aum_max=aum_max,
        state=state, country=country,
        sort_by=sort_by, sort_dir=sort_dir,
    )
    csv_data = export_allocators_csv(filters)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=purebrain-ir-allocators.csv"},
    )


@app.get("/api/allocators/{allocator_id}")
async def allocator_detail(allocator_id: str):
    """Get full allocator profile with top holdings."""
    detail = get_allocator_detail(allocator_id)
    if not detail:
        return JSONResponse(status_code=404, content={"error": "Allocator not found"})
    return detail


@app.get("/api/search/allocators/options")
async def allocator_filter_options():
    """Available filter values for allocator search UI dropdowns."""
    return get_allocator_filter_options()


# ── Gatekeeper Endpoints (Sprint 3A) ──

@app.get("/api/gatekeepers")
async def gatekeepers_list(
    state: Optional[str] = Query(None, description="Filter by US state"),
    min_score: float = Query(30, description="Minimum gatekeeper score (0-100)"),
    limit: int = Query(50, ge=1, le=200),
):
    """Find top gatekeeper firms — pension consultants who can introduce you to allocators."""
    return {
        "results": search_gatekeepers(state=state, min_score=min_score, limit=limit),
        "total": len(search_gatekeepers(state=state, min_score=min_score, limit=limit)),
    }


@app.get("/api/gatekeepers/{crd_number}")
async def gatekeeper_score(crd_number: str):
    """Compute gatekeeper score for a specific firm."""
    return compute_gatekeeper_score(crd_number)


@app.get("/api/stats")
async def stats():
    """Database stats."""
    import sqlite3
    from pathlib import Path

    db_path = Path(__file__).parent / "purebrain_ir.db"
    conn = sqlite3.connect(str(db_path))
    ia = conn.execute("SELECT COUNT(*) FROM adv_firms").fetchone()[0]
    era = conn.execute("SELECT COUNT(*) FROM era_firms").fetchone()[0]
    with_cik = conn.execute(
        "SELECT COUNT(*) FROM adv_firms WHERE cik_number IS NOT NULL AND cik_number != ''"
    ).fetchone()[0]
    with_aum = conn.execute(
        "SELECT COUNT(*) FROM adv_firms WHERE aum_total > 0"
    ).fetchone()[0]
    conn.close()

    # Allocator stats from holdings DB
    h_db_path = Path(__file__).parent / "holdings_13f.db"
    h_conn = sqlite3.connect(str(h_db_path))
    allocator_count = h_conn.execute(
        "SELECT COUNT(*) FROM ir_investors WHERE type IN ('pension','endowment','sovereign_wealth')"
    ).fetchone()[0]
    total_holdings = h_conn.execute("SELECT COUNT(*) FROM ir_holdings").fetchone()[0]
    total_investors = h_conn.execute("SELECT COUNT(*) FROM ir_investors").fetchone()[0]
    h_conn.close()

    return {
        "ia_firms": ia,
        "era_firms": era,
        "total_firms": ia + era,
        "with_cik_mapping": with_cik,
        "with_aum": with_aum,
        "allocators": allocator_count,
        "total_investors_13f": total_investors,
        "total_holdings_13f": total_holdings,
        "data_source": "SEC FOIA Form ADV bulk CSV + SEC EDGAR 13F",
        "last_updated": "2026-05-12",
    }


@app.get("/")
async def root():
    """Serve the search UI."""
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).parent / "static" / "index.html")


# Mount static files (must be after route definitions)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
