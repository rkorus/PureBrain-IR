#!/usr/bin/env python3
"""
PureBrain IR — AI Fit Score Algorithm (Sprint 2A)
5-dimension scoring model (v2.0).

Total: 0-100 across 5 dimensions (20 pts each):
1. Profile Match (0-20) — AUM, geography, client type. ALL firms.
2. Sector Alignment (0-20) — Portfolio exposure via 13F. CIK-mapped firms.
3. Position Behavior (0-20) — Concentration, turnover, check size. Multi-Q 13F.
4. Direct Signal (0-20) — Holds target tickers? Increasing? Strongest signal.
5. Peer Overlap (0-20) — Holds comparable companies? Weighted by size/recency.

Firms without 13F data get Dimension 1 only (confidence="low").
"""

import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
ADV_DB = SCRIPT_DIR / "purebrain_ir.db"
HOLDINGS_DB = SCRIPT_DIR / "holdings_13f.db"


@dataclass
class FitContext:
    """Search context that defines what the user is looking for."""
    # Target company profile (for sector alignment)
    target_tickers: list[str] = None  # e.g. ["AAPL", "MSFT"]
    target_sector: Optional[str] = None  # e.g. "Technology"

    # Preferred investor profile
    preferred_state: Optional[str] = None
    preferred_aum_min: Optional[float] = None
    preferred_aum_max: Optional[float] = None
    preferred_client_type: Optional[str] = None  # "individual", "hnw", "corporate"

    # Target fundraise size (for check size compatibility)
    target_raise_size: Optional[float] = None  # e.g. 50_000_000

    def __post_init__(self):
        if self.target_tickers is None:
            self.target_tickers = []


@dataclass
class FitScore:
    """Scoring breakdown for a firm."""
    crd_number: str
    total_score: float = 0.0
    confidence: str = "low"  # "low" (ADV only), "medium" (some 13F), "high" (full 13F)

    # Dimension breakdowns (5 x 20 = 100)
    profile_match: float = 0.0  # 0-20
    sector_alignment: float = 0.0  # 0-20
    position_behavior: float = 0.0  # 0-20
    direct_signal: float = 0.0  # 0-20
    peer_overlap: float = 0.0  # 0-20

    # Gatekeeper bonus (0-100 separate score, not included in total_score)
    gatekeeper_score: float = 0.0
    gatekeeper_tier: str = "not_gatekeeper"

    # Detail
    profile_detail: dict = None
    sector_detail: dict = None
    position_detail: dict = None
    signal_detail: dict = None
    peer_detail: dict = None
    gatekeeper_detail: dict = None

    def __post_init__(self):
        if self.profile_detail is None:
            self.profile_detail = {}
        if self.sector_detail is None:
            self.sector_detail = {}
        if self.position_detail is None:
            self.position_detail = {}
        if self.signal_detail is None:
            self.signal_detail = {}
        if self.peer_detail is None:
            self.peer_detail = {}
        if self.gatekeeper_detail is None:
            self.gatekeeper_detail = {}


def _score_profile_match(firm: dict, ctx: FitContext) -> tuple[float, dict]:
    """Dimension 1: Profile Match (0-20). Works for ALL firms."""
    score = 0.0
    detail = {}

    # Geography match (0-6)
    if ctx.preferred_state and firm.get("state"):
        if firm["state"].upper() == ctx.preferred_state.upper():
            score += 6
            detail["geography"] = "exact_match"
        else:
            score += 1.5  # Different state but still US-based
            detail["geography"] = "different_state"
    elif not ctx.preferred_state:
        score += 3  # No preference = neutral
        detail["geography"] = "no_preference"

    # AUM range fit (0-6)
    aum = firm.get("aum_total", 0) or 0
    if ctx.preferred_aum_min or ctx.preferred_aum_max:
        aum_min = ctx.preferred_aum_min or 0
        aum_max = ctx.preferred_aum_max or float("inf")
        if aum_min <= aum <= aum_max:
            score += 6
            detail["aum_fit"] = "in_range"
        elif aum > 0:
            if aum > aum_max:
                ratio = aum_max / aum if aum > 0 else 0
            else:
                ratio = aum / aum_min if aum_min > 0 else 0
            score += max(0, 6 * ratio * 0.5)
            detail["aum_fit"] = "partial"
        else:
            detail["aum_fit"] = "no_aum_data"
    else:
        score += 3 if aum > 0 else 1
        detail["aum_fit"] = "no_preference"

    # Client type match (0-4)
    if ctx.preferred_client_type:
        client_map = {
            "individual": "clients_individuals",
            "hnw": "clients_hnw",
            "corporate": "clients_corporate",
            "pension": "clients_pension",
        }
        col = client_map.get(ctx.preferred_client_type)
        if col and (firm.get(col, 0) or 0) > 0:
            score += 4
            detail["client_type"] = "match"
        else:
            score += 1
            detail["client_type"] = "no_match"
    else:
        score += 2
        detail["client_type"] = "no_preference"

    # Services breadth (0-4)
    svc_count = sum(1 for k in [
        "svc_financial_planning", "svc_portfolio_indiv", "svc_portfolio_biz",
        "svc_pension_consulting", "svc_adviser_selection",
    ] if firm.get(k))
    score += min(4, svc_count)
    detail["services_count"] = svc_count

    return min(20, score), detail


def _score_sector_alignment(
    holdings_conn: sqlite3.Connection,
    investor_id: str,
    ctx: FitContext,
) -> tuple[float, dict]:
    """Dimension 2: Sector Alignment (0-20). Requires 13F data.

    Scoring split:
    - Ticker overlap (0-8): direct holdings of target tickers
    - Sector exposure (0-12): % of portfolio in target sector via ir_ticker_sectors
    """
    if not ctx.target_tickers and not ctx.target_sector:
        return 0.0, {"reason": "no_target_tickers_or_sector"}

    # Get all holdings for this investor (latest period)
    rows = holdings_conn.execute(
        "SELECT ticker, market_value, period_of_report FROM ir_holdings "
        "WHERE investor_id = ? ORDER BY period_of_report DESC",
        (investor_id,),
    ).fetchall()

    if not rows:
        return 0.0, {"reason": "no_holdings"}

    # Get latest period
    latest_period = rows[0][2]
    latest_holdings = [(r[0], r[1]) for r in rows if r[2] == latest_period]

    total_value = sum(h[1] for h in latest_holdings)
    if total_value == 0:
        return 0.0, {"reason": "zero_portfolio_value"}

    score = 0.0
    detail = {"total_positions": len(latest_holdings)}

    # Part A: Ticker overlap (0-8)
    if ctx.target_tickers:
        target_set = set(t.upper() for t in ctx.target_tickers)
        held_tickers = set(h[0].upper() for h in latest_holdings if h[0])
        overlap = target_set & held_tickers

        if overlap:
            overlap_pct = len(overlap) / len(target_set)
            score += overlap_pct * 8
            detail["tickers_held"] = list(overlap)
            detail["ticker_overlap_pct"] = round(overlap_pct, 2)
        else:
            detail["tickers_held"] = []
            detail["ticker_overlap_pct"] = 0

    # Part B: Sector exposure (0-12) — uses ir_ticker_sectors table
    if ctx.target_sector:
        # Check if sector table exists
        has_sectors = holdings_conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='ir_ticker_sectors'"
        ).fetchone()[0]

        if has_sectors:
            # Get sector for each held ticker
            sector_value = 0.0
            for ticker, mkt_val in latest_holdings:
                if not ticker:
                    continue
                sec_row = holdings_conn.execute(
                    "SELECT gics_sector FROM ir_ticker_sectors WHERE ticker = ?",
                    (ticker.upper(),),
                ).fetchone()
                if sec_row and sec_row[0] and ctx.target_sector.lower() in sec_row[0].lower():
                    sector_value += mkt_val

            sector_pct = sector_value / total_value if total_value > 0 else 0
            # Scale: 30%+ sector exposure = full 12 points, linear below
            sector_score = min(12, (sector_pct / 0.30) * 12)
            score += sector_score
            detail["sector_exposure_pct"] = round(sector_pct, 4)
            detail["sector_exposure_value"] = round(sector_value)
            detail["target_sector"] = ctx.target_sector
        else:
            # Fallback: no sector table, give partial credit based on ticker overlap
            if ctx.target_tickers:
                target_set = set(t.upper() for t in ctx.target_tickers)
                overlap_value = sum(
                    h[1] for h in latest_holdings
                    if h[0] and h[0].upper() in target_set
                )
                concentration = overlap_value / total_value if total_value > 0 else 0
                score += min(12, concentration * 100 * 12)
                detail["sector_fallback"] = "no_sector_table"
    else:
        # No target sector specified — give partial credit for having diverse holdings
        score += 4
        detail["sector_note"] = "no_target_sector"

    return min(20, score), detail


def _score_position_behavior(
    holdings_conn: sqlite3.Connection,
    investor_id: str,
    ctx: FitContext,
) -> tuple[float, dict]:
    """Dimension 3: Position Behavior (0-20). Requires multi-quarter 13F."""
    # Get distinct periods
    periods = holdings_conn.execute(
        "SELECT DISTINCT period_of_report FROM ir_holdings "
        "WHERE investor_id = ? ORDER BY period_of_report",
        (investor_id,),
    ).fetchall()

    if len(periods) < 2:
        return 0.0, {"reason": "need_multi_quarter", "periods": len(periods)}

    latest = periods[-1][0]
    previous = periods[-2][0]

    # Get holdings for both periods
    latest_h = holdings_conn.execute(
        "SELECT ticker, market_value, shares FROM ir_holdings "
        "WHERE investor_id = ? AND period_of_report = ?",
        (investor_id, latest),
    ).fetchall()

    prev_h = holdings_conn.execute(
        "SELECT ticker, market_value, shares FROM ir_holdings "
        "WHERE investor_id = ? AND period_of_report = ?",
        (investor_id, previous),
    ).fetchall()

    if not latest_h:
        return 0.0, {"reason": "no_latest_holdings"}

    # Concentration score (0-8): top-10 positions as % of portfolio
    latest_sorted = sorted(latest_h, key=lambda x: x[1], reverse=True)
    total_val = sum(h[1] for h in latest_sorted)
    top10_val = sum(h[1] for h in latest_sorted[:10])
    concentration = top10_val / total_val if total_val > 0 else 0

    # Higher concentration = more conviction = higher score (for active managers)
    conc_score = concentration * 8

    # Turnover score (0-6): new positions as % of total
    latest_tickers = set(h[0] for h in latest_h if h[0])
    prev_tickers = set(h[0] for h in prev_h if h[0])
    new_positions = latest_tickers - prev_tickers
    turnover = len(new_positions) / len(latest_tickers) if latest_tickers else 0
    # Moderate turnover is ideal (active but not churning)
    if 0.05 <= turnover <= 0.30:
        turn_score = 6
    elif turnover < 0.05:
        turn_score = 3  # Too passive
    else:
        turn_score = 3  # Too much churn

    # Check size compatibility (0-6)
    if ctx.target_raise_size and latest_sorted:
        median_idx = len(latest_sorted) // 2
        median_position = latest_sorted[median_idx][1]
        if median_position > 0:
            ratio = ctx.target_raise_size / median_position
            if 0.1 <= ratio <= 10:
                check_score = 6
            elif 0.01 <= ratio <= 100:
                check_score = 2.5
            else:
                check_score = 0
        else:
            check_score = 0
    else:
        check_score = 3  # No preference

    score = conc_score + turn_score + check_score
    detail = {
        "concentration_top10": round(concentration, 3),
        "new_positions": len(new_positions),
        "total_positions": len(latest_tickers),
        "turnover_rate": round(turnover, 3),
        "periods_available": len(periods),
    }

    return min(20, score), detail


def _score_direct_signal(
    holdings_conn: sqlite3.Connection,
    investor_id: str,
    ctx: FitContext,
) -> tuple[float, dict]:
    """Dimension 4: Direct Signal (0-20). Does firm hold target tickers?"""
    if not ctx.target_tickers:
        return 0.0, {"reason": "no_target_tickers"}

    target_set = set(t.upper() for t in ctx.target_tickers)

    # Get holdings of target tickers across all periods
    placeholders = ",".join(["?"] * len(target_set))
    rows = holdings_conn.execute(
        f"SELECT ticker, market_value, shares, shares_change, shares_change_pct, "
        f"period_of_report, is_new_position "
        f"FROM ir_holdings "
        f"WHERE investor_id = ? AND UPPER(ticker) IN ({placeholders}) "
        f"ORDER BY period_of_report DESC",
        (investor_id, *target_set),
    ).fetchall()

    if not rows:
        return 0.0, {"reason": "does_not_hold_target", "tickers_checked": list(target_set)}

    # Score based on: holding (8), increasing (8), new position (4)
    score = 0
    held_tickers = set()
    increasing = []
    new_positions = []

    for r in rows:
        ticker = r[0].upper() if r[0] else ""
        held_tickers.add(ticker)
        if r[3] and r[3] > 0:  # shares_change > 0
            increasing.append(ticker)
        if r[6]:  # is_new_position
            new_positions.append(ticker)

    # Holds target (0-8)
    hold_pct = len(held_tickers) / len(target_set)
    score += hold_pct * 8

    # Increasing position (0-8)
    if increasing:
        inc_pct = len(set(increasing)) / len(target_set)
        score += inc_pct * 8

    # New position in target (0-4)
    if new_positions:
        score += 4

    detail = {
        "held_tickers": list(held_tickers),
        "increasing_tickers": list(set(increasing)),
        "new_position_tickers": list(set(new_positions)),
        "hold_coverage": round(hold_pct, 2),
    }

    return min(20, score), detail


def compute_fit_score(
    crd_number: str,
    ctx: FitContext,
    adv_db: Path = ADV_DB,
    holdings_db: Path = HOLDINGS_DB,
) -> FitScore:
    """Compute full fit score for a firm given search context."""
    result = FitScore(crd_number=crd_number)

    # Get firm from ADV database
    adv_conn = sqlite3.connect(str(adv_db))
    adv_conn.row_factory = sqlite3.Row
    firm = adv_conn.execute(
        "SELECT * FROM adv_firms WHERE crd_number = ?", (crd_number,)
    ).fetchone()
    adv_conn.close()

    if not firm:
        return result

    firm = dict(firm)

    # Dimension 1: Profile Match (always available)
    result.profile_match, result.profile_detail = _score_profile_match(firm, ctx)
    result.confidence = "low"

    # Check if we have 13F data for this firm
    cik = firm.get("cik_number")
    investor_id = None

    if cik and holdings_db.exists():
        h_conn = sqlite3.connect(str(holdings_db))
        inv = h_conn.execute(
            "SELECT id FROM ir_investors WHERE cik = ?", (cik,)
        ).fetchone()
        if inv:
            investor_id = inv[0]

            # Dimension 2: Sector Alignment
            result.sector_alignment, result.sector_detail = _score_sector_alignment(
                h_conn, investor_id, ctx
            )

            # Dimension 3: Position Behavior
            result.position_behavior, result.position_detail = _score_position_behavior(
                h_conn, investor_id, ctx
            )

            # Dimension 4: Direct Signal
            result.direct_signal, result.signal_detail = _score_direct_signal(
                h_conn, investor_id, ctx
            )

            result.confidence = "high" if result.position_detail.get("periods_available", 0) >= 2 else "medium"

        h_conn.close()

    # Dimension 5: Peer Overlap (requires target_tickers as peers)
    if ctx.target_tickers and len(ctx.target_tickers) > 0:
        from peer_analysis import get_peer_overlap_score
        result.peer_overlap = get_peer_overlap_score(
            crd_number, ctx.target_tickers, ctx.target_sector
        )
        result.peer_detail = {"peer_tickers": ctx.target_tickers, "score": result.peer_overlap}

    # Gatekeeper Score (separate 0-100 score, not part of total)
    from gatekeeper import compute_gatekeeper_score as _gk_score
    gk = _gk_score(crd_number, adv_db, holdings_db)
    result.gatekeeper_score = gk.get("score", 0)
    result.gatekeeper_tier = gk.get("tier", "not_gatekeeper")
    result.gatekeeper_detail = gk.get("detail", {})

    result.total_score = round(
        result.profile_match + result.sector_alignment +
        result.position_behavior + result.direct_signal +
        result.peer_overlap, 1
    )

    return result


def batch_score(
    crd_numbers: list[str],
    ctx: FitContext,
) -> list[FitScore]:
    """Score multiple firms and return sorted by total_score DESC."""
    scores = [compute_fit_score(crd, ctx) for crd in crd_numbers]
    scores.sort(key=lambda s: s.total_score, reverse=True)
    return scores


# ── CLI testing ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test: Score the 8 seed filers for a tech company raising $50M
    ctx = FitContext(
        target_tickers=["AAPL", "MSFT", "NVDA", "GOOGL"],
        target_sector="Technology",
        preferred_state="CA",
        preferred_aum_min=1_000_000_000,
        preferred_client_type="hnw",
        target_raise_size=50_000_000,
    )

    # Get CRDs for the 8 seed filers via CIK mapping
    adv_conn = sqlite3.connect(str(ADV_DB))
    h_conn = sqlite3.connect(str(HOLDINGS_DB))

    investors = h_conn.execute("SELECT id, name, cik FROM ir_investors").fetchall()
    print(f"Scoring {len(investors)} filers for: Tech company, CA-based, HNW, $1B+ AUM, $50M raise\n")

    for inv_id, inv_name, inv_cik in investors:
        # Find CRD for this CIK
        row = adv_conn.execute(
            "SELECT crd_number FROM adv_firms WHERE cik_number = ?", (str(inv_cik),)
        ).fetchone()

        if row:
            crd = row[0]
            score = compute_fit_score(crd, ctx)
            print(f"{inv_name}")
            print(f"  CRD: {crd} | Total: {score.total_score}/100 ({score.confidence})")
            print(f"  Profile: {score.profile_match:.1f}/20 | Sector: {score.sector_alignment:.1f}/20 | "
                  f"Behavior: {score.position_behavior:.1f}/20 | Signal: {score.direct_signal:.1f}/20 | "
                  f"Peer: {score.peer_overlap:.1f}/20")
            if score.signal_detail.get("held_tickers"):
                print(f"  Holds: {score.signal_detail['held_tickers']}")
            print()
        else:
            print(f"{inv_name}: No CRD mapping for CIK {inv_cik}\n")

    adv_conn.close()
    h_conn.close()
