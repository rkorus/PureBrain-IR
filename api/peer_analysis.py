#!/usr/bin/env python3
"""
PureBrain IR — Peer-Based Targeting Engine (Sprint 2A)

Core query: "Which investors hold my peers but not me?"
Scoring: weighted by position size, filing recency, and sector affinity.

Usage:
    from peer_analysis import analyze_peers, PeerQuery
    query = PeerQuery(target_ticker="PLTR", peer_tickers=["SNOW", "MDB", "DDOG"])
    results = analyze_peers(query)
"""

import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
ADV_DB = SCRIPT_DIR / "purebrain_ir.db"
HOLDINGS_DB = SCRIPT_DIR / "holdings_13f.db"


@dataclass
class PeerQuery:
    """Input for peer-based investor targeting."""
    target_ticker: Optional[str] = None       # Your company's ticker (optional — for exclusion)
    peer_tickers: list[str] = field(default_factory=list)  # Comparable companies
    target_sector: Optional[str] = None       # Sector for affinity scoring
    min_overlap: int = 1                      # Minimum peers held to appear in results
    limit: int = 50                           # Max results
    include_target_holders: bool = False      # If True, also include firms holding the target


@dataclass
class PeerOverlapResult:
    """Scoring result for a single investor."""
    investor_id: str
    investor_name: str
    crd_number: Optional[str] = None
    cik: Optional[str] = None

    # Overlap metrics
    peers_held: list[str] = field(default_factory=list)
    peers_not_held: list[str] = field(default_factory=list)
    overlap_count: int = 0
    overlap_ratio: float = 0.0

    # Weighted scores
    raw_overlap_score: float = 0.0       # Size-weighted overlap
    recency_score: float = 0.0           # Recency-adjusted score
    sector_affinity_score: float = 0.0   # Sector concentration score
    composite_score: float = 0.0         # Combined peer overlap score (0-20)

    # Context
    holds_target: bool = False
    total_positions: int = 0
    total_portfolio_value: float = 0.0
    peer_position_values: dict = field(default_factory=dict)

    # Firm profile (from ADV)
    legal_name: Optional[str] = None
    state: Optional[str] = None
    aum_total: float = 0.0
    aum_display: str = "N/A"


# ── Recency Weighting ──

# Weight multipliers by how recent the filing period is
def _recency_weight(period_of_report: str, latest_period: str) -> float:
    """Weight filing recency: latest quarter = 1.0, decaying for older filings."""
    if not period_of_report or not latest_period:
        return 0.5

    try:
        period_dt = datetime.strptime(period_of_report, "%Y-%m-%d")
        latest_dt = datetime.strptime(latest_period, "%Y-%m-%d")
        quarters_ago = (latest_dt.year - period_dt.year) * 4 + (latest_dt.month - period_dt.month) // 3
        # Decay: 1.0, 0.85, 0.7, 0.55, 0.4 for Q0-Q4 ago
        return max(0.2, 1.0 - (quarters_ago * 0.15))
    except (ValueError, TypeError):
        return 0.5


def _format_aum(aum: float) -> str:
    """Format AUM for display."""
    if aum >= 1e12:
        return f"${aum/1e12:.1f}T"
    elif aum >= 1e9:
        return f"${aum/1e9:.1f}B"
    elif aum >= 1e6:
        return f"${aum/1e6:.0f}M"
    elif aum > 0:
        return f"${aum/1e3:.0f}K"
    return "N/A"


# ── Core Engine ──

def analyze_peers(
    query: PeerQuery,
    holdings_db: Path = HOLDINGS_DB,
    adv_db: Path = ADV_DB,
) -> dict:
    """
    Find investors who hold peer tickers, scored by overlap, size, recency, and sector.

    Two-pass optimization:
      Pass 1 — Fast: SQL-based peer matching + overlap/size scoring
      Pass 2 — Selective: Sector affinity only for top candidates

    Returns:
        {
            "results": [PeerOverlapResult, ...],
            "query": {...},
            "total_investors_scanned": int,
            "total_matches": int,
        }
    """
    if not query.peer_tickers:
        return {"results": [], "query": asdict(query), "total_investors_scanned": 0, "total_matches": 0}

    h_conn = sqlite3.connect(str(holdings_db))
    h_conn.row_factory = sqlite3.Row
    adv_conn = sqlite3.connect(str(adv_db))
    adv_conn.row_factory = sqlite3.Row

    peer_set = set(t.upper() for t in query.peer_tickers)
    target_upper = query.target_ticker.upper() if query.target_ticker else None

    # Find the latest period across all holdings
    latest_period = h_conn.execute(
        "SELECT MAX(period_of_report) FROM ir_holdings"
    ).fetchone()[0]

    # ── PASS 1: SQL-based peer matching (fast) ──
    # Find all investors who hold at least min_overlap peer tickers in one query
    peer_list = list(peer_set)
    placeholders = ",".join(["?"] * len(peer_list))

    # Get peer holdings grouped by investor
    peer_holdings_sql = f"""
        SELECT h.investor_id, i.name, i.cik,
               UPPER(h.ticker) as ticker, h.market_value, h.period_of_report
        FROM ir_holdings h
        JOIN ir_investors i ON h.investor_id = i.id
        WHERE UPPER(h.ticker) IN ({placeholders})
        ORDER BY h.investor_id, h.period_of_report DESC
    """
    peer_rows = h_conn.execute(peer_holdings_sql, peer_list).fetchall()

    # Group by investor, deduplicate to latest period per ticker
    investor_peers = {}  # inv_id -> {ticker: row}
    investor_info = {}   # inv_id -> (name, cik)
    for r in peer_rows:
        inv_id = r["investor_id"]
        ticker = r["ticker"]
        if inv_id not in investor_peers:
            investor_peers[inv_id] = {}
            investor_info[inv_id] = (r["name"], str(r["cik"]) if r["cik"] else None)
        if ticker not in investor_peers[inv_id]:
            investor_peers[inv_id][ticker] = r

    # Count total investors for reporting
    total_investors = h_conn.execute("SELECT COUNT(*) FROM ir_investors").fetchone()[0]

    # Filter by min_overlap and target exclusion
    candidates = []
    for inv_id, seen_tickers in investor_peers.items():
        overlap_count = len(seen_tickers)
        if overlap_count < query.min_overlap:
            continue

        inv_name, inv_cik = investor_info[inv_id]

        # Check target exclusion
        holds_target = False
        if target_upper:
            target_row = h_conn.execute(
                "SELECT 1 FROM ir_holdings WHERE investor_id = ? AND UPPER(ticker) = ? LIMIT 1",
                (inv_id, target_upper),
            ).fetchone()
            holds_target = target_row is not None
            if holds_target and not query.include_target_holders:
                continue

        # Portfolio total (use a fast query with index)
        portfolio_stats = h_conn.execute(
            "SELECT COUNT(*) as cnt, SUM(market_value) as total_val "
            "FROM ir_holdings WHERE investor_id = ? AND period_of_report = ?",
            (inv_id, latest_period),
        ).fetchone()
        total_positions = portfolio_stats["cnt"] or 0
        total_value = portfolio_stats["total_val"] or 0.0

        # Score 1: Size-weighted overlap
        size_score = 0.0
        peer_values = {}
        peers_held = list(seen_tickers.keys())
        for ticker, row in seen_tickers.items():
            mkt_val = row["market_value"] or 0
            peer_values[ticker] = mkt_val
            if total_value > 0:
                position_weight = min(0.10, mkt_val / total_value)
                size_score += position_weight * 100

        overlap_ratio = overlap_count / len(peer_set)
        raw_overlap = overlap_ratio * 10
        size_weighted = min(10.0, size_score)

        # Score 2: Recency weighting
        recency_total = sum(
            _recency_weight(row["period_of_report"], latest_period)
            for row in seen_tickers.values()
        )
        recency_avg = recency_total / len(seen_tickers)
        recency_score = recency_avg * 5.0

        # Preliminary score (without sector) for ranking
        prelim_score = raw_overlap + size_weighted + recency_score

        candidates.append({
            "inv_id": inv_id,
            "inv_name": inv_name,
            "inv_cik": inv_cik,
            "peers_held": peers_held,
            "overlap_count": overlap_count,
            "overlap_ratio": overlap_ratio,
            "raw_overlap": raw_overlap,
            "size_weighted": size_weighted,
            "recency_score": recency_score,
            "prelim_score": prelim_score,
            "holds_target": holds_target,
            "total_positions": total_positions,
            "total_value": total_value,
            "peer_values": peer_values,
        })

    # Sort by preliminary score, take top candidates for sector scoring
    candidates.sort(key=lambda c: c["prelim_score"], reverse=True)
    # Compute sector only for top N (limit only — sector rarely changes rankings)
    sector_candidates = candidates[:query.limit]

    # ── PASS 2: Sector affinity (only for top candidates) ──
    # Pre-compute sector concentration using an aggregate query for efficiency
    results = []
    for c in sector_candidates:
        sector_score = 0.0
        if query.target_sector and c["total_value"] > 0:
            # Use targeted aggregate instead of scanning all holdings
            sector_row = h_conn.execute(
                "SELECT COALESCE(SUM(h.market_value), 0) "
                "FROM ir_holdings h "
                "JOIN ir_ticker_sectors s ON h.ticker = s.ticker "
                "WHERE h.investor_id = ? AND h.period_of_report = ? "
                "AND s.gics_sector LIKE ?",
                (c["inv_id"], latest_period, f"%{query.target_sector}%"),
            ).fetchone()

            sector_value = sector_row[0] if sector_row else 0
            sector_pct = sector_value / c["total_value"]
            sector_score = min(5.0, (sector_pct / 0.30) * 5.0)

        # Composite Score (0-20)
        raw_composite = c["raw_overlap"] + c["size_weighted"] + c["recency_score"] + sector_score
        composite = min(20.0, raw_composite * (20.0 / 30.0))

        # Look up ADV firm data via CIK
        crd_number = None
        legal_name = c["inv_name"]
        state = None
        aum_total = 0.0

        if c["inv_cik"]:
            adv_row = adv_conn.execute(
                "SELECT crd_number, legal_name, state, aum_total FROM adv_firms WHERE cik_number = ?",
                (c["inv_cik"],),
            ).fetchone()
            if adv_row:
                crd_number = adv_row["crd_number"]
                legal_name = adv_row["legal_name"]
                state = adv_row["state"]
                aum_total = adv_row["aum_total"] or 0.0

        result = PeerOverlapResult(
            investor_id=c["inv_id"],
            investor_name=c["inv_name"],
            crd_number=crd_number,
            cik=c["inv_cik"],
            peers_held=c["peers_held"],
            peers_not_held=list(peer_set - set(c["peers_held"])),
            overlap_count=c["overlap_count"],
            overlap_ratio=round(c["overlap_ratio"], 3),
            raw_overlap_score=round(c["raw_overlap"], 2),
            recency_score=round(c["recency_score"], 2),
            sector_affinity_score=round(sector_score, 2),
            composite_score=round(composite, 2),
            holds_target=c["holds_target"],
            total_positions=c["total_positions"],
            total_portfolio_value=c["total_value"],
            peer_position_values={k: round(v) for k, v in c["peer_values"].items()},
            legal_name=legal_name,
            state=state,
            aum_total=aum_total,
            aum_display=_format_aum(aum_total),
        )
        results.append(result)

    h_conn.close()
    adv_conn.close()

    # Final sort by composite score
    results.sort(key=lambda r: r.composite_score, reverse=True)
    results = results[:query.limit]

    return {
        "results": [asdict(r) for r in results],
        "query": {
            "target_ticker": query.target_ticker,
            "peer_tickers": list(peer_set),
            "target_sector": query.target_sector,
            "min_overlap": query.min_overlap,
            "include_target_holders": query.include_target_holders,
        },
        "total_investors_scanned": total_investors,
        "total_matches": len(results),
        "latest_filing_period": latest_period,
    }


def get_peer_overlap_score(
    crd_number: str,
    peer_tickers: list[str],
    target_sector: Optional[str] = None,
    holdings_db: Path = HOLDINGS_DB,
    adv_db: Path = ADV_DB,
) -> float:
    """
    Get peer overlap score (0-20) for a single firm.
    Used by fit_score.py as the 5th dimension.
    """
    if not peer_tickers:
        return 0.0

    adv_conn = sqlite3.connect(str(adv_db))
    cik_row = adv_conn.execute(
        "SELECT cik_number FROM adv_firms WHERE crd_number = ?", (crd_number,)
    ).fetchone()
    adv_conn.close()

    if not cik_row or not cik_row[0]:
        return 0.0

    cik = cik_row[0]
    h_conn = sqlite3.connect(str(holdings_db))

    inv_row = h_conn.execute(
        "SELECT id FROM ir_investors WHERE cik = ?", (cik,)
    ).fetchone()

    if not inv_row:
        h_conn.close()
        return 0.0

    inv_id = inv_row[0]
    peer_set = set(t.upper() for t in peer_tickers)

    # Latest period
    latest_period = h_conn.execute(
        "SELECT MAX(period_of_report) FROM ir_holdings"
    ).fetchone()[0]

    # Check peer holdings
    placeholders = ",".join(["?"] * len(peer_set))
    peer_rows = h_conn.execute(
        f"SELECT ticker, market_value, period_of_report "
        f"FROM ir_holdings "
        f"WHERE investor_id = ? AND UPPER(ticker) IN ({placeholders}) "
        f"ORDER BY period_of_report DESC",
        (inv_id, *peer_set),
    ).fetchall()

    seen = {}
    for r in peer_rows:
        t = r[0].upper() if r[0] else ""
        if t not in seen:
            seen[t] = (r[1] or 0, r[2])

    if not seen:
        h_conn.close()
        return 0.0

    overlap_count = len(seen)
    overlap_ratio = overlap_count / len(peer_set)

    # Portfolio total
    total_val_row = h_conn.execute(
        "SELECT SUM(market_value) FROM ir_holdings WHERE investor_id = ? AND period_of_report = ?",
        (inv_id, latest_period),
    ).fetchone()
    total_value = total_val_row[0] if total_val_row[0] else 1.0

    # Size-weighted score
    size_score = 0.0
    for ticker, (mkt_val, period) in seen.items():
        position_weight = min(0.10, mkt_val / total_value) if total_value > 0 else 0
        size_score += position_weight * 100

    # Recency
    recency_total = sum(_recency_weight(v[1], latest_period) for v in seen.values())
    recency_avg = recency_total / len(seen)
    recency_score = recency_avg * 5.0

    # Sector affinity
    sector_score = 0.0
    if target_sector:
        sector_rows = h_conn.execute(
            "SELECT h.market_value, s.gics_sector "
            "FROM ir_holdings h "
            "LEFT JOIN ir_ticker_sectors s ON UPPER(h.ticker) = UPPER(s.ticker) "
            "WHERE h.investor_id = ? AND h.period_of_report = ?",
            (inv_id, latest_period),
        ).fetchall()
        sector_value = sum(
            r[0] or 0 for r in sector_rows
            if r[1] and target_sector.lower() in r[1].lower()
        )
        if total_value > 0:
            sector_pct = sector_value / total_value
            sector_score = min(5.0, (sector_pct / 0.30) * 5.0)

    h_conn.close()

    raw = (overlap_ratio * 10) + min(10.0, size_score) + recency_score + sector_score
    return round(min(20.0, raw * (20.0 / 30.0)), 2)


# ── CLI Testing ──

if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "PLTR"
    peers = sys.argv[2].split(",") if len(sys.argv) > 2 else ["SNOW", "MDB", "DDOG", "CRWD", "NET"]
    sector = sys.argv[3] if len(sys.argv) > 3 else "Technology"

    print(f"Target: {target}")
    print(f"Peers: {peers}")
    print(f"Sector: {sector}")
    print(f"{'='*80}\n")

    query = PeerQuery(
        target_ticker=target,
        peer_tickers=peers,
        target_sector=sector,
        include_target_holders=True,
    )
    data = analyze_peers(query)

    print(f"Scanned {data['total_investors_scanned']} investors, {data['total_matches']} matches")
    print(f"Latest filing period: {data['latest_filing_period']}\n")

    for i, r in enumerate(data["results"], 1):
        target_flag = " [HOLDS TARGET]" if r["holds_target"] else ""
        print(f"{i:2d}. {r['investor_name']}{target_flag}")
        print(f"    Score: {r['composite_score']:.1f}/20 | Peers: {r['overlap_count']}/{len(peers)} ({r['overlap_ratio']:.0%})")
        print(f"    Held: {', '.join(r['peers_held'])} | Missing: {', '.join(r['peers_not_held'])}")
        print(f"    CRD: {r['crd_number'] or 'N/A'} | AUM: {r['aum_display']} | State: {r['state'] or 'N/A'}")
        print(f"    Breakdown: overlap={r['raw_overlap_score']:.1f} + recency={r['recency_score']:.1f} + sector={r['sector_affinity_score']:.1f}")
        print()
