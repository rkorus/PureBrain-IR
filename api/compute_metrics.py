#!/usr/bin/env python3
"""
PureBrain IR — Pre-compute Fit Score metrics table.
Heavy SQL aggregations on holdings data, run after each 13F ingest.
Creates ir_fit_metrics table for fast scoring during search.
"""

import sqlite3
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ADV_DB = SCRIPT_DIR / "purebrain_ir.db"
HOLDINGS_DB = SCRIPT_DIR / "holdings_13f.db"


def compute_metrics():
    """Pre-compute per-investor metrics from 13F holdings data."""
    if not HOLDINGS_DB.exists():
        print("No holdings DB found. Skipping.")
        return

    h_conn = sqlite3.connect(str(HOLDINGS_DB))
    adv_conn = sqlite3.connect(str(ADV_DB))

    # Create metrics table in ADV DB
    adv_conn.execute("""
        CREATE TABLE IF NOT EXISTS ir_fit_metrics (
            crd_number TEXT PRIMARY KEY,
            cik_number TEXT,
            investor_name TEXT,
            -- Portfolio stats
            total_positions INTEGER DEFAULT 0,
            total_portfolio_value REAL DEFAULT 0,
            -- Concentration
            top10_concentration REAL DEFAULT 0,
            -- Turnover (requires multi-quarter)
            new_positions INTEGER DEFAULT 0,
            dropped_positions INTEGER DEFAULT 0,
            turnover_rate REAL DEFAULT 0,
            -- Sector exposure (top tickers)
            top_tickers TEXT DEFAULT '',
            -- Period info
            latest_period TEXT,
            periods_available INTEGER DEFAULT 0,
            -- Computed at
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    adv_conn.execute("DELETE FROM ir_fit_metrics")
    adv_conn.commit()

    # Get all investors with CRD mappings
    investors = h_conn.execute("SELECT id, name, cik FROM ir_investors").fetchall()
    print(f"Processing {len(investors)} investors...")

    computed = 0
    for inv_id, inv_name, inv_cik in investors:
        # Find CRD for this CIK
        row = adv_conn.execute(
            "SELECT crd_number FROM adv_firms WHERE cik_number = ?",
            (str(inv_cik),),
        ).fetchone()

        if not row:
            continue

        crd = row[0]

        # Get distinct periods
        periods = h_conn.execute(
            "SELECT DISTINCT period_of_report FROM ir_holdings "
            "WHERE investor_id = ? ORDER BY period_of_report",
            (inv_id,),
        ).fetchall()
        periods_list = [p[0] for p in periods]

        if not periods_list:
            continue

        latest = periods_list[-1]

        # Latest holdings
        latest_h = h_conn.execute(
            "SELECT ticker, market_value, shares FROM ir_holdings "
            "WHERE investor_id = ? AND period_of_report = ? "
            "ORDER BY market_value DESC",
            (inv_id, latest),
        ).fetchall()

        total_positions = len(latest_h)
        total_value = sum(h[1] for h in latest_h)

        # Top-10 concentration
        top10_value = sum(h[1] for h in latest_h[:10])
        top10_conc = top10_value / total_value if total_value > 0 else 0

        # Top tickers (for quick sector lookup)
        top_tickers = ",".join(h[0] for h in latest_h[:20] if h[0])

        # Turnover (if multi-quarter)
        new_pos = 0
        dropped_pos = 0
        turnover = 0.0
        if len(periods_list) >= 2:
            previous = periods_list[-2]
            prev_h = h_conn.execute(
                "SELECT ticker FROM ir_holdings "
                "WHERE investor_id = ? AND period_of_report = ?",
                (inv_id, previous),
            ).fetchall()

            latest_tickers = set(h[0] for h in latest_h if h[0])
            prev_tickers = set(h[0] for h in prev_h if h[0])
            new_pos = len(latest_tickers - prev_tickers)
            dropped_pos = len(prev_tickers - latest_tickers)
            turnover = new_pos / len(latest_tickers) if latest_tickers else 0

        adv_conn.execute(
            "INSERT OR REPLACE INTO ir_fit_metrics "
            "(crd_number, cik_number, investor_name, total_positions, "
            "total_portfolio_value, top10_concentration, new_positions, "
            "dropped_positions, turnover_rate, top_tickers, latest_period, "
            "periods_available) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (crd, str(inv_cik), inv_name, total_positions,
             total_value, round(top10_conc, 4), new_pos,
             dropped_pos, round(turnover, 4), top_tickers,
             latest, len(periods_list)),
        )
        computed += 1
        print(f"  {inv_name}: {total_positions} positions, "
              f"${total_value/1e9:.1f}B, top10={top10_conc:.1%}")

    adv_conn.commit()
    h_conn.close()
    adv_conn.close()

    print(f"\nDone. {computed} investors with pre-computed metrics.")


if __name__ == "__main__":
    compute_metrics()
