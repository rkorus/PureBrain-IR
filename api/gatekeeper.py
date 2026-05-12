#!/usr/bin/env python3
"""
PureBrain IR — Gatekeeper Intelligence (Sprint 3A)

Identifies "gatekeeper" firms — pension consultants and adviser selection
firms that can introduce companies to allocator capital (pension funds,
endowments, SWFs).

Gatekeeper Score (0-100):
  - Pension client count (0-30): More pension clients = stronger gate
  - Service breadth (0-25): Pension consulting + adviser selection
  - AUM influence (0-25): Larger = more allocator relationships
  - Holdings overlap (0-20): Allocator portfolios they manage

Usage:
    from gatekeeper import compute_gatekeeper_score, search_gatekeepers
"""

import sqlite3
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
ADV_DB = SCRIPT_DIR / "purebrain_ir.db"
HOLDINGS_DB = SCRIPT_DIR / "holdings_13f.db"


def compute_gatekeeper_score(
    crd_number: str,
    adv_db: Path = ADV_DB,
    holdings_db: Path = HOLDINGS_DB,
) -> dict:
    """
    Compute gatekeeper score (0-100) for a single firm.

    Measures how well this firm can introduce a company to allocator capital.
    """
    conn = sqlite3.connect(str(adv_db))
    conn.row_factory = sqlite3.Row

    firm = conn.execute(
        "SELECT * FROM adv_firms WHERE crd_number = ?", (crd_number,)
    ).fetchone()

    if not firm:
        conn.close()
        return {"crd_number": crd_number, "score": 0, "reason": "firm_not_found"}

    firm = dict(firm)
    score = 0.0
    detail = {}

    # ── Dimension 1: Pension Client Count (0-30) ──
    pension_clients = firm.get("clients_pension", 0) or 0
    if pension_clients >= 100:
        pension_score = 30
    elif pension_clients >= 50:
        pension_score = 25
    elif pension_clients >= 20:
        pension_score = 20
    elif pension_clients >= 10:
        pension_score = 15
    elif pension_clients >= 5:
        pension_score = 10
    elif pension_clients > 0:
        pension_score = 5
    else:
        pension_score = 0
    score += pension_score
    detail["pension_clients"] = pension_clients
    detail["pension_score"] = pension_score

    # ── Dimension 2: Service Breadth (0-25) ──
    svc_score = 0
    if firm.get("svc_pension_consulting"):
        svc_score += 15
        detail["pension_consulting"] = True
    else:
        detail["pension_consulting"] = False

    if firm.get("svc_adviser_selection"):
        svc_score += 10
        detail["adviser_selection"] = True
    else:
        detail["adviser_selection"] = False

    score += svc_score
    detail["service_score"] = svc_score

    # ── Dimension 3: AUM Influence (0-25) ──
    aum = firm.get("aum_total", 0) or 0
    if aum >= 100_000_000_000:  # $100B+
        aum_score = 25
    elif aum >= 10_000_000_000:  # $10B+
        aum_score = 20
    elif aum >= 1_000_000_000:  # $1B+
        aum_score = 15
    elif aum >= 100_000_000:  # $100M+
        aum_score = 10
    elif aum >= 10_000_000:  # $10M+
        aum_score = 5
    else:
        aum_score = 0
    score += aum_score
    detail["aum"] = aum
    detail["aum_score"] = aum_score

    # ── Dimension 4: Holdings Overlap with Allocators (0-20) ──
    overlap_score = 0
    cik = firm.get("cik_number")
    if cik:
        try:
            h_conn = sqlite3.connect(str(holdings_db))
            # Check if this firm's CIK appears in any allocator's holdings
            inv = h_conn.execute(
                "SELECT id FROM ir_investors WHERE cik = ?", (cik,)
            ).fetchone()

            if inv:
                # Check how many allocators hold securities from this firm
                allocator_holders = h_conn.execute("""
                    SELECT COUNT(DISTINCT h2.investor_id)
                    FROM ir_holdings h1
                    JOIN ir_holdings h2 ON h1.cusip = h2.cusip AND h1.investor_id != h2.investor_id
                    JOIN ir_investors i2 ON h2.investor_id = i2.id
                    WHERE h1.investor_id = ?
                    AND i2.type IN ('pension', 'endowment', 'sovereign_wealth')
                    LIMIT 1
                """, (inv[0],)).fetchone()[0]

                if allocator_holders >= 5:
                    overlap_score = 20
                elif allocator_holders >= 3:
                    overlap_score = 15
                elif allocator_holders >= 1:
                    overlap_score = 10
                detail["allocator_holders"] = allocator_holders

            h_conn.close()
        except Exception:
            pass

    score += overlap_score
    detail["overlap_score"] = overlap_score

    conn.close()

    # Classify
    if score >= 70:
        tier = "top_gatekeeper"
    elif score >= 50:
        tier = "strong_gatekeeper"
    elif score >= 30:
        tier = "moderate_gatekeeper"
    elif score >= 10:
        tier = "minor_gatekeeper"
    else:
        tier = "not_gatekeeper"

    return {
        "crd_number": crd_number,
        "score": round(score, 1),
        "tier": tier,
        "detail": detail,
    }


def search_gatekeepers(
    state: Optional[str] = None,
    min_score: float = 30,
    limit: int = 50,
    adv_db: Path = ADV_DB,
) -> list[dict]:
    """
    Find top gatekeeper firms — pension consultants and adviser selectors
    that can introduce companies to allocator capital.
    """
    conn = sqlite3.connect(str(adv_db))
    conn.row_factory = sqlite3.Row

    where = ["(svc_pension_consulting = 1 OR svc_adviser_selection = 1)"]
    params = []

    if state:
        where.append("state = ?")
        params.append(state.upper())

    # Only consider firms with meaningful pension relationships
    where.append("(clients_pension > 0 OR aum_total > 1000000000)")

    where_sql = " AND ".join(where)

    rows = conn.execute(f"""
        SELECT crd_number, legal_name, state, city, aum_total,
               clients_pension, svc_pension_consulting, svc_adviser_selection,
               phone, has_website
        FROM adv_firms
        WHERE {where_sql}
        ORDER BY clients_pension DESC, aum_total DESC
        LIMIT ?
    """, params + [limit * 3]).fetchall()  # Over-fetch for scoring/filtering

    conn.close()

    # Score each
    results = []
    for r in rows:
        r = dict(r)
        score_data = compute_gatekeeper_score(r["crd_number"])
        if score_data["score"] >= min_score:
            aum = r.get("aum_total", 0) or 0
            if aum >= 1e12:
                aum_display = f"${aum/1e12:.1f}T"
            elif aum >= 1e9:
                aum_display = f"${aum/1e9:.1f}B"
            elif aum >= 1e6:
                aum_display = f"${aum/1e6:.0f}M"
            else:
                aum_display = "N/A"

            results.append({
                "crd_number": r["crd_number"],
                "legal_name": r["legal_name"],
                "state": r["state"],
                "city": r["city"],
                "aum_total": aum,
                "aum_display": aum_display,
                "pension_clients": r["clients_pension"] or 0,
                "pension_consulting": bool(r["svc_pension_consulting"]),
                "adviser_selection": bool(r["svc_adviser_selection"]),
                "gatekeeper_score": score_data["score"],
                "gatekeeper_tier": score_data["tier"],
            })

    # Sort by score
    results.sort(key=lambda x: x["gatekeeper_score"], reverse=True)
    return results[:limit]


# ── CLI ──

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "score":
        crd = sys.argv[2] if len(sys.argv) > 2 else "105958"
        result = compute_gatekeeper_score(crd)
        print(json.dumps(result, indent=2))
    else:
        state = sys.argv[1] if len(sys.argv) > 1 else None
        results = search_gatekeepers(state=state, min_score=25, limit=20)
        print(f"Top Gatekeepers{' in ' + state if state else ''}: {len(results)} found\n")
        for i, r in enumerate(results, 1):
            svcs = []
            if r["pension_consulting"]:
                svcs.append("PC")
            if r["adviser_selection"]:
                svcs.append("AS")
            print(f"{i:2d}. {r['legal_name']:<50} {r['state'] or 'N/A':<4} "
                  f"Score: {r['gatekeeper_score']:>5.1f} | "
                  f"Pension clients: {r['pension_clients']:>6} | "
                  f"AUM: {r['aum_display']:>10} | [{' '.join(svcs)}]")
