#!/usr/bin/env python3
"""
PureBrain IR — Allocator Fit Score (Sprint 3B)

Answers: "Would this allocator commit capital to a fund like ours?"

Total: 0-100 across 5 dimensions (20 pts each):
1. Strategy Alignment (0-20) — Does the allocator hold tickers in the fund's target sectors?
2. Check Size Match (0-20) — Is the allocator's typical position size consistent with fund commitment?
3. Allocation Pattern (0-20) — Does the allocator invest in active/growth strategies vs pure index?
4. Geographic Reach (0-20) — Is the allocator based in the fund's target geography?
5. Gatekeeper Access (0-20) — How accessible is this allocator via known gatekeepers?

Usage:
    from allocator_fit_score import FundContext, compute_allocator_fit_score
    ctx = FundContext(target_sectors=["Information Technology"], fund_size=25_000_000)
    score = compute_allocator_fit_score("investor-uuid", ctx)
"""

import sqlite3
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
HOLDINGS_DB = SCRIPT_DIR / "holdings_13f.db"
ADV_DB = SCRIPT_DIR / "purebrain_ir.db"

# Common ETF tickers — used to detect passive/index allocations
ETF_TICKERS = {
    "SPY", "QQQ", "IWM", "VTI", "VOO", "IVV", "AGG", "BND", "EFA", "VEA",
    "VWO", "IEMG", "EEM", "IWF", "IWD", "VTV", "VUG", "SCHD", "JEPI", "VIG",
    "XLF", "XLK", "XLE", "XLV", "XLI", "XLY", "XLP", "XLB", "XLU", "XLRE",
    "DIA", "RSP", "MDY", "IJR", "IJH", "IWB", "IWR", "IWS", "IWO", "IWN",
    "GLD", "SLV", "TLT", "SHY", "LQD", "HYG", "TIP", "BNDX", "VCIT", "VCSH",
    "VNQ", "SCHB", "SCHA", "SCHF", "SCHE", "SPTM", "SPLG", "SPYG", "SPYV",
}


@dataclass
class FundContext:
    """Context describing the fund seeking LP commitments."""
    target_sectors: list[str] = None       # GICS sectors, e.g. ["Information Technology", "Industrials"]
    target_tickers: list[str] = None       # Specific tickers the fund invests alongside
    fund_size: Optional[float] = None      # Target fund size (e.g. 25_000_000 for $25M)
    min_commitment: Optional[float] = None # Minimum LP commitment (e.g. 5_000_000)
    fund_domicile: str = "US"              # Fund domicile country
    strategy_type: str = "venture"         # venture|growth|buyout|infrastructure|real_estate

    def __post_init__(self):
        if self.target_sectors is None:
            self.target_sectors = []
        if self.target_tickers is None:
            self.target_tickers = []


@dataclass
class AllocatorFitScore:
    """Scoring breakdown for an allocator."""
    investor_id: str
    total_score: float = 0.0
    confidence: str = "low"  # low|medium|high

    # 5 dimensions × 20 = 100
    strategy_alignment: float = 0.0   # 0-20
    check_size_match: float = 0.0     # 0-20
    allocation_pattern: float = 0.0   # 0-20
    geographic_reach: float = 0.0     # 0-20
    gatekeeper_access: float = 0.0    # 0-20

    # Tier classification
    tier: str = "not_fit"

    # Detail breakdowns
    strategy_detail: dict = None
    check_size_detail: dict = None
    pattern_detail: dict = None
    geography_detail: dict = None
    gatekeeper_detail: dict = None

    def __post_init__(self):
        for attr in ("strategy_detail", "check_size_detail", "pattern_detail",
                      "geography_detail", "gatekeeper_detail"):
            if getattr(self, attr) is None:
                setattr(self, attr, {})


def _score_strategy_alignment(
    conn: sqlite3.Connection,
    investor_id: str,
    ctx: FundContext,
) -> tuple[float, dict]:
    """
    Dimension 1: Strategy Alignment (0-20).
    Does the allocator hold tickers in the fund's target sectors?
    """
    if not ctx.target_sectors and not ctx.target_tickers:
        return 10.0, {"reason": "no_target_specified", "note": "neutral_score"}

    # Get latest period holdings
    latest_period = conn.execute(
        "SELECT MAX(period_of_report) FROM ir_holdings WHERE investor_id = ?",
        (investor_id,),
    ).fetchone()[0]

    if not latest_period:
        return 0.0, {"reason": "no_holdings"}

    holdings = conn.execute(
        "SELECT ticker, market_value FROM ir_holdings "
        "WHERE investor_id = ? AND period_of_report = ?",
        (investor_id, latest_period),
    ).fetchall()

    if not holdings:
        return 0.0, {"reason": "no_holdings"}

    total_value = sum(h[1] for h in holdings if h[1])
    if total_value == 0:
        return 0.0, {"reason": "zero_portfolio_value"}

    score = 0.0
    detail = {"total_positions": len(holdings), "total_value": total_value}

    # Part A: Sector exposure (0-14)
    if ctx.target_sectors:
        sector_value = 0.0
        sector_positions = 0
        for ticker, mkt_val in holdings:
            if not ticker:
                continue
            sec_row = conn.execute(
                "SELECT gics_sector FROM ir_ticker_sectors WHERE UPPER(ticker) = UPPER(?)",
                (ticker,),
            ).fetchone()
            if sec_row and sec_row[0]:
                for target_sector in ctx.target_sectors:
                    if target_sector.lower() in sec_row[0].lower():
                        sector_value += (mkt_val or 0)
                        sector_positions += 1
                        break

        sector_pct = sector_value / total_value if total_value > 0 else 0
        # 25%+ sector exposure = full 14 points
        sector_score = min(14, (sector_pct / 0.25) * 14)
        score += sector_score
        detail["sector_exposure_pct"] = round(sector_pct, 4)
        detail["sector_positions"] = sector_positions
        detail["sector_value"] = round(sector_value)
    else:
        score += 7  # No sector preference = neutral

    # Part B: Ticker overlap (0-6)
    if ctx.target_tickers:
        target_set = {t.upper() for t in ctx.target_tickers}
        held_set = {h[0].upper() for h in holdings if h[0]}
        overlap = target_set & held_set
        if overlap:
            overlap_pct = len(overlap) / len(target_set)
            score += overlap_pct * 6
            detail["tickers_held"] = sorted(overlap)
            detail["ticker_overlap_pct"] = round(overlap_pct, 2)
        else:
            detail["tickers_held"] = []
            detail["ticker_overlap_pct"] = 0
    else:
        score += 3  # No ticker preference = neutral

    return min(20, score), detail


def _score_check_size_match(
    conn: sqlite3.Connection,
    investor_id: str,
    ctx: FundContext,
) -> tuple[float, dict]:
    """
    Dimension 2: Check Size Match (0-20).
    Is the allocator's typical position size consistent with fund commitment?
    """
    latest_period = conn.execute(
        "SELECT MAX(period_of_report) FROM ir_holdings WHERE investor_id = ?",
        (investor_id,),
    ).fetchone()[0]

    if not latest_period:
        return 0.0, {"reason": "no_holdings"}

    # Get position sizes
    positions = conn.execute(
        "SELECT market_value FROM ir_holdings "
        "WHERE investor_id = ? AND period_of_report = ? AND market_value > 0 "
        "ORDER BY market_value",
        (investor_id, latest_period),
    ).fetchall()

    if not positions:
        return 0.0, {"reason": "no_positions"}

    values = [p[0] for p in positions]
    total_value = sum(values)
    median_position = values[len(values) // 2]
    p25 = values[len(values) // 4] if len(values) >= 4 else values[0]
    p75 = values[3 * len(values) // 4] if len(values) >= 4 else values[-1]

    detail = {
        "total_portfolio_value": round(total_value),
        "position_count": len(values),
        "median_position": round(median_position),
        "p25_position": round(p25),
        "p75_position": round(p75),
    }

    # If no fund size specified, score based on portfolio scale
    commitment = ctx.min_commitment or (ctx.fund_size * 0.1 if ctx.fund_size else None)

    if not commitment:
        # No fund size: score based on portfolio scale (larger = more likely LP)
        if total_value >= 100_000_000_000:   # $100B+
            return 18.0, {**detail, "reason": "mega_allocator"}
        elif total_value >= 10_000_000_000:   # $10B+
            return 15.0, {**detail, "reason": "large_allocator"}
        elif total_value >= 1_000_000_000:    # $1B+
            return 10.0, {**detail, "reason": "mid_allocator"}
        else:
            return 5.0, {**detail, "reason": "small_allocator"}

    detail["target_commitment"] = round(commitment)

    # Compare commitment size to their typical position
    # Ideal: commitment is between p25 and p75 of their position sizes
    score = 0.0

    if p25 <= commitment <= p75:
        score = 20  # Perfect fit — commitment matches their sweet spot
    elif commitment <= median_position * 5 and commitment >= p25 * 0.1:
        # Reasonable range — within 10x of their typical
        ratio = min(commitment, median_position) / max(commitment, median_position)
        score = 8 + (ratio * 12)  # 8-20 range
    elif commitment < p25 * 0.1:
        # Too small for them — they write bigger checks
        score = 5  # Still possible, just small for them
    else:
        # Too large for them
        if commitment <= total_value * 0.05:
            score = 8  # Up to 5% of portfolio is reasonable
        elif commitment <= total_value * 0.10:
            score = 4  # Up to 10% is a stretch
        else:
            score = 1  # Over 10% of portfolio — unlikely

    return min(20, score), detail


def _score_allocation_pattern(
    conn: sqlite3.Connection,
    investor_id: str,
    ctx: FundContext,
) -> tuple[float, dict]:
    """
    Dimension 3: Allocation Pattern (0-20).
    Does the allocator invest in active/growth strategies vs pure index?
    Higher concentration in non-ETF = more likely to invest in alternative funds.
    """
    latest_period = conn.execute(
        "SELECT MAX(period_of_report) FROM ir_holdings WHERE investor_id = ?",
        (investor_id,),
    ).fetchone()[0]

    if not latest_period:
        return 0.0, {"reason": "no_holdings"}

    holdings = conn.execute(
        "SELECT ticker, market_value FROM ir_holdings "
        "WHERE investor_id = ? AND period_of_report = ?",
        (investor_id, latest_period),
    ).fetchall()

    if not holdings:
        return 0.0, {"reason": "no_holdings"}

    total_value = sum(h[1] for h in holdings if h[1])
    if total_value == 0:
        return 0.0, {"reason": "zero_value"}

    # ETF vs active allocation
    etf_value = 0
    active_value = 0
    etf_count = 0
    active_count = 0

    for ticker, mkt_val in holdings:
        if not ticker or not mkt_val:
            continue
        if ticker.upper() in ETF_TICKERS:
            etf_value += mkt_val
            etf_count += 1
        else:
            active_value += mkt_val
            active_count += 1

    active_pct = active_value / total_value if total_value > 0 else 0

    # Concentration — top 10 as % of total (higher = more conviction)
    sorted_holdings = sorted(holdings, key=lambda x: x[1] or 0, reverse=True)
    top10_value = sum(h[1] for h in sorted_holdings[:10] if h[1])
    concentration = top10_value / total_value if total_value > 0 else 0

    detail = {
        "active_pct": round(active_pct, 3),
        "etf_pct": round(1 - active_pct, 3),
        "etf_count": etf_count,
        "active_count": active_count,
        "top10_concentration": round(concentration, 3),
    }

    score = 0.0

    # Active allocation score (0-12): higher active % = more likely to invest in alts
    if active_pct >= 0.90:
        score += 12
    elif active_pct >= 0.70:
        score += 10
    elif active_pct >= 0.50:
        score += 7
    elif active_pct >= 0.30:
        score += 4
    else:
        score += 2  # Mostly passive — less likely to allocate to funds

    # Concentration score (0-8): moderate concentration = conviction investor
    if 0.20 <= concentration <= 0.60:
        score += 8  # Conviction but diversified — ideal LP profile
    elif concentration > 0.60:
        score += 6  # Very concentrated — still good
    elif concentration >= 0.10:
        score += 5  # Moderate — index-like but not pure passive
    else:
        score += 2  # Extremely diversified — likely passive

    return min(20, score), detail


def _score_geographic_reach(
    conn: sqlite3.Connection,
    investor_id: str,
    ctx: FundContext,
) -> tuple[float, dict]:
    """
    Dimension 4: Geographic Reach (0-20).
    Allocators in the fund's domicile country score higher.
    """
    inv = conn.execute(
        "SELECT hq_country, hq_state, name, type FROM ir_investors WHERE id = ?",
        (investor_id,),
    ).fetchone()

    if not inv:
        return 0.0, {"reason": "investor_not_found"}

    country = inv[0] or "US"
    state = inv[1]
    inv_type = inv[3]

    detail = {
        "country": country,
        "state": state,
        "fund_domicile": ctx.fund_domicile,
    }

    score = 0.0

    # Country match (0-12)
    if country.upper() == ctx.fund_domicile.upper():
        score += 12
        detail["country_match"] = True
    else:
        # Cross-border LP relationships (common for pensions/SWFs)
        # Canadian pensions frequently invest in US funds
        cross_border_friendly = {"CA", "GB", "SG", "NO", "AU", "NL", "CH"}
        if country.upper() in cross_border_friendly:
            score += 8
            detail["country_match"] = False
            detail["cross_border_friendly"] = True
        else:
            score += 3
            detail["country_match"] = False
            detail["cross_border_friendly"] = False

    # Entity type score (0-8): some types more likely to be LPs in VC/PE
    type_scores = {
        "pension": 8,           # Pensions actively allocate to alternatives
        "sovereign_wealth": 8,  # SWFs are major LP sources
        "endowment": 7,         # Endowments (Yale model) love alternatives
        "foundation": 5,        # Foundations sometimes allocate
        "family_office": 6,     # Family offices are active LPs
        "insurance": 4,         # Insurance companies — less common for VC
    }
    type_score = type_scores.get(inv_type, 3)
    score += type_score
    detail["entity_type"] = inv_type
    detail["entity_type_score"] = type_score

    return min(20, score), detail


def _score_gatekeeper_access(
    investor_id: str,
    conn: sqlite3.Connection,
    adv_db: Path = ADV_DB,
) -> tuple[float, dict]:
    """
    Dimension 5: Gatekeeper Access (0-20).
    How accessible is this allocator via known gatekeepers (pension consultants)?
    Uses holdings overlap between allocator and gatekeeper firms.
    """
    # Get allocator's holdings (latest period)
    latest_period = conn.execute(
        "SELECT MAX(period_of_report) FROM ir_holdings WHERE investor_id = ?",
        (investor_id,),
    ).fetchone()[0]

    if not latest_period:
        return 0.0, {"reason": "no_holdings"}

    allocator_cusips = set()
    rows = conn.execute(
        "SELECT cusip FROM ir_holdings WHERE investor_id = ? AND period_of_report = ? AND cusip IS NOT NULL",
        (investor_id, latest_period),
    ).fetchall()
    allocator_cusips = {r[0] for r in rows}

    if not allocator_cusips:
        return 5.0, {"reason": "no_cusips_for_overlap", "note": "base_score"}

    # Check overlap with gatekeeper firms from ADV database
    try:
        adv_conn = sqlite3.connect(str(adv_db))

        # Get CIKs of pension consulting / adviser selection firms
        gk_firms = adv_conn.execute("""
            SELECT crd_number, legal_name, cik_number, aum_total
            FROM adv_firms
            WHERE (svc_pension_consulting = 1 OR svc_adviser_selection = 1)
            AND cik_number IS NOT NULL AND cik_number != ''
            AND aum_total > 100000000
            ORDER BY aum_total DESC
            LIMIT 50
        """).fetchall()

        adv_conn.close()

        if not gk_firms:
            return 5.0, {"reason": "no_gatekeepers_with_cik", "note": "base_score"}

        # Check which gatekeeper firms have holdings overlapping with this allocator
        overlapping_gatekeepers = []
        for gk_crd, gk_name, gk_cik, gk_aum in gk_firms:
            gk_investor = conn.execute(
                "SELECT id FROM ir_investors WHERE cik = ?", (gk_cik,),
            ).fetchone()

            if not gk_investor:
                continue

            # Get gatekeeper's holdings CUSIPs
            gk_cusips = set()
            gk_rows = conn.execute(
                "SELECT cusip FROM ir_holdings WHERE investor_id = ? AND cusip IS NOT NULL",
                (gk_investor[0],),
            ).fetchall()
            gk_cusips = {r[0] for r in gk_rows}

            overlap = allocator_cusips & gk_cusips
            if overlap:
                overlapping_gatekeepers.append({
                    "name": gk_name,
                    "crd": gk_crd,
                    "overlap_count": len(overlap),
                    "aum": gk_aum,
                })

        detail = {
            "gatekeepers_checked": len(gk_firms),
            "overlapping_gatekeepers": len(overlapping_gatekeepers),
            "top_gatekeepers": overlapping_gatekeepers[:5],
        }

        if len(overlapping_gatekeepers) >= 5:
            return 20.0, detail
        elif len(overlapping_gatekeepers) >= 3:
            return 16.0, detail
        elif len(overlapping_gatekeepers) >= 1:
            return 12.0, detail
        else:
            return 5.0, {**detail, "note": "no_overlap_found"}

    except Exception:
        return 5.0, {"reason": "gatekeeper_check_failed"}


def compute_allocator_fit_score(
    investor_id: str,
    ctx: FundContext,
    holdings_db: Path = HOLDINGS_DB,
    adv_db: Path = ADV_DB,
) -> AllocatorFitScore:
    """Compute full allocator fit score for LP sourcing."""
    result = AllocatorFitScore(investor_id=investor_id)

    conn = sqlite3.connect(str(holdings_db))
    conn.row_factory = sqlite3.Row

    # Verify investor exists
    inv = conn.execute(
        "SELECT id, name, type FROM ir_investors WHERE id = ?",
        (investor_id,),
    ).fetchone()

    if not inv:
        conn.close()
        return result

    # Dimension 1: Strategy Alignment
    result.strategy_alignment, result.strategy_detail = _score_strategy_alignment(
        conn, investor_id, ctx
    )

    # Dimension 2: Check Size Match
    result.check_size_match, result.check_size_detail = _score_check_size_match(
        conn, investor_id, ctx
    )

    # Dimension 3: Allocation Pattern
    result.allocation_pattern, result.pattern_detail = _score_allocation_pattern(
        conn, investor_id, ctx
    )

    # Dimension 4: Geographic Reach
    result.geographic_reach, result.geography_detail = _score_geographic_reach(
        conn, investor_id, ctx
    )

    # Dimension 5: Gatekeeper Access
    result.gatekeeper_access, result.gatekeeper_detail = _score_gatekeeper_access(
        investor_id, conn, adv_db
    )

    conn.close()

    # Total
    result.total_score = round(
        result.strategy_alignment + result.check_size_match +
        result.allocation_pattern + result.geographic_reach +
        result.gatekeeper_access, 1
    )

    # Confidence based on data quality
    has_holdings = result.strategy_detail.get("total_positions", 0) > 0
    has_positions = result.check_size_detail.get("position_count", 0) > 0
    if has_holdings and has_positions:
        result.confidence = "high"
    elif has_holdings:
        result.confidence = "medium"
    else:
        result.confidence = "low"

    # Tier
    if result.total_score >= 75:
        result.tier = "top_prospect"
    elif result.total_score >= 60:
        result.tier = "strong_prospect"
    elif result.total_score >= 45:
        result.tier = "moderate_prospect"
    elif result.total_score >= 25:
        result.tier = "exploratory"
    else:
        result.tier = "not_fit"

    return result


def batch_score_allocators(
    ctx: FundContext,
    entity_type: Optional[str] = None,
    min_score: float = 0,
    limit: int = 50,
    holdings_db: Path = HOLDINGS_DB,
    adv_db: Path = ADV_DB,
) -> list[dict]:
    """Score all allocators and return ranked list."""
    conn = sqlite3.connect(str(holdings_db))
    conn.row_factory = sqlite3.Row

    allocator_types = ("pension", "endowment", "sovereign_wealth", "foundation", "family_office", "insurance")

    if entity_type:
        investors = conn.execute(
            "SELECT id, name, type FROM ir_investors WHERE type = ?",
            (entity_type,),
        ).fetchall()
    else:
        placeholders = ",".join("?" * len(allocator_types))
        investors = conn.execute(
            f"SELECT id, name, type FROM ir_investors WHERE type IN ({placeholders})",
            allocator_types,
        ).fetchall()

    conn.close()

    results = []
    for inv in investors:
        score = compute_allocator_fit_score(inv["id"], ctx, holdings_db, adv_db)
        if score.total_score >= min_score:
            results.append({
                "investor_id": inv["id"],
                "name": inv["name"],
                "entity_type": inv["type"],
                "total_score": score.total_score,
                "tier": score.tier,
                "confidence": score.confidence,
                "strategy_alignment": score.strategy_alignment,
                "check_size_match": score.check_size_match,
                "allocation_pattern": score.allocation_pattern,
                "geographic_reach": score.geographic_reach,
                "gatekeeper_access": score.gatekeeper_access,
            })

    results.sort(key=lambda x: x["total_score"], reverse=True)
    return results[:limit]


# ── CLI ──

if __name__ == "__main__":
    import json
    import sys

    # Default: MAKR-like fund context
    ctx = FundContext(
        target_sectors=["Information Technology", "Industrials"],
        fund_size=25_000_000,
        min_commitment=5_000_000,
        fund_domicile="US",
        strategy_type="venture",
    )

    if len(sys.argv) > 1 and sys.argv[1] == "score":
        inv_id = sys.argv[2] if len(sys.argv) > 2 else ""
        score = compute_allocator_fit_score(inv_id, ctx)
        print(json.dumps(asdict(score), indent=2, default=str))
    else:
        print("Scoring all allocators for MAKR-like fund ($25M, Tech/Infra, US VC)\n")
        results = batch_score_allocators(ctx, min_score=20, limit=25)
        print(f"{'#':>3} {'Name':<55} {'Type':<15} {'Score':>5} {'Tier':<18} "
              f"{'Strat':>5} {'Check':>5} {'Patt':>5} {'Geo':>5} {'Gate':>5}")
        print("-" * 140)
        for i, r in enumerate(results, 1):
            print(f"{i:3d} {r['name']:<55} {r['entity_type']:<15} {r['total_score']:>5.1f} "
                  f"{r['tier']:<18} {r['strategy_alignment']:>5.1f} {r['check_size_match']:>5.1f} "
                  f"{r['allocation_pattern']:>5.1f} {r['geographic_reach']:>5.1f} "
                  f"{r['gatekeeper_access']:>5.1f}")
