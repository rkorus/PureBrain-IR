#!/usr/bin/env python3
"""Batch resolve all unresolved CUSIPs in the database.

Runs as a background job. Progress is logged to stdout.
Free tier: ~10 CUSIPs per request, ~6.5 seconds between requests.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pipeline.db import get_connection
from pipeline.cusip_resolver import resolve_cusips, get_cache_stats


def resolve_all():
    conn = get_connection()

    # Get all unique CUSIPs without tickers
    rows = conn.execute("""
        SELECT DISTINCT cusip FROM ir_holdings
        WHERE cusip != '' AND (ticker = '' OR ticker IS NULL)
    """).fetchall()

    cusips = [r["cusip"] for r in rows]
    total = len(cusips)
    print(f"Found {total} unresolved CUSIPs")

    if total == 0:
        print("Nothing to resolve.")
        return

    # Process in batches of 10
    batch_size = 10
    resolved_count = 0
    failed_count = 0

    for i in range(0, total, batch_size):
        batch = cusips[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        try:
            results = resolve_cusips(batch)
            newly_resolved = 0

            for cusip, resolution in results.items():
                if resolution.ticker:
                    # Update database
                    conn.execute("""
                        UPDATE ir_holdings SET ticker = ?
                        WHERE cusip = ? AND (ticker = '' OR ticker IS NULL)
                    """, (resolution.ticker, cusip))
                    newly_resolved += 1

            conn.commit()
            resolved_count += newly_resolved
            failed_count += len(batch) - newly_resolved

            if batch_num % 10 == 0 or batch_num == total_batches:
                pct = (i + len(batch)) / total * 100
                print(f"  Batch {batch_num}/{total_batches} ({pct:.0f}%) — "
                      f"resolved: {resolved_count}, unresolvable: {failed_count}")

        except Exception as e:
            print(f"  Batch {batch_num} ERROR: {e}")
            failed_count += len(batch)
            time.sleep(5)

    print(f"\nDone. Resolved: {resolved_count}, Unresolvable: {failed_count}")
    stats = get_cache_stats()
    print(f"Cache: {stats}")

    conn.close()


if __name__ == "__main__":
    resolve_all()
