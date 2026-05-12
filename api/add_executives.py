#!/usr/bin/env python3
"""
PureBrain IR — Executive/Owner enrichment from Form ADV Schedule A/B.
Extracts key personnel (CEO, CCO, Managing Partner, etc.) per firm.
Links via FilingID → CRD mapping from adv_firms table.
"""

import csv
import io
import sqlite3
import zipfile
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ZIP_PATH = SCRIPT_DIR / "adv-filing-data-part1.zip"
DB_PATH = SCRIPT_DIR / "purebrain_ir.db"

db = sqlite3.connect(str(DB_PATH))

# Create executives table
db.execute("""
    CREATE TABLE IF NOT EXISTS firm_executives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crd_number TEXT NOT NULL,
        full_name TEXT NOT NULL,
        title TEXT,
        is_control_person INTEGER DEFAULT 0,
        ownership_code TEXT,
        schedule TEXT,
        owner_id TEXT,
        UNIQUE(crd_number, owner_id)
    )
""")
db.execute("DELETE FROM firm_executives")  # Fresh load
db.commit()

# Build FilingID → CRD mapping (latest filing per CRD)
print("Building FilingID → CRD mapping...")
fid_to_crd = {}
rows = db.execute("SELECT crd_number, filing_id FROM adv_firms").fetchall()
for crd, fid in rows:
    fid_to_crd[fid] = crd
print(f"  {len(fid_to_crd):,} filing IDs mapped to CRDs")

# Parse Schedule A/B
z = zipfile.ZipFile(str(ZIP_PATH), "r")
fname = [n for n in z.namelist() if "IA_Schedule_A_B" in n][0]
print(f"Parsing {fname}...")

# Collect executives per CRD (from latest filing only)
execs_by_crd = defaultdict(list)
skipped = 0
processed = 0

with z.open(fname) as f:
    reader = csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"))
    for row in reader:
        processed += 1
        fid = int(row["FilingID"]) if row["FilingID"].strip() else 0
        if fid not in fid_to_crd:
            skipped += 1
            continue

        # Only individuals (not entity owners)
        if row.get("DE/FE/I", "") != "I":
            continue

        crd = fid_to_crd[fid]
        name = row.get("Full Legal Name", "").strip()
        title = row.get("Title or Status", "").strip()
        control = 1 if row.get("Control Person", "").strip() == "Y" else 0
        ownership = row.get("Ownership Code", "").strip()
        schedule = row.get("Schedule", "").strip()
        owner_id = row.get("OwnerID", "").strip()

        if name:
            execs_by_crd[crd].append({
                "name": name,
                "title": title,
                "control": control,
                "ownership": ownership,
                "schedule": schedule,
                "owner_id": owner_id,
            })

print(f"  Processed: {processed:,} rows, Skipped: {skipped:,} (non-latest filings)")
print(f"  Firms with executives: {len(execs_by_crd):,}")

# Insert into database
inserted = 0
for crd, execs in execs_by_crd.items():
    for ex in execs:
        try:
            db.execute(
                "INSERT OR IGNORE INTO firm_executives "
                "(crd_number, full_name, title, is_control_person, ownership_code, schedule, owner_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (crd, ex["name"], ex["title"], ex["control"],
                 ex["ownership"], ex["schedule"], ex["owner_id"]),
            )
            inserted += 1
        except Exception as e:
            pass

db.commit()

# Create indexes
db.execute("CREATE INDEX IF NOT EXISTS idx_exec_crd ON firm_executives(crd_number)")
db.commit()

# Stats
total_execs = db.execute("SELECT COUNT(*) FROM firm_executives").fetchone()[0]
firms_with_execs = db.execute(
    "SELECT COUNT(DISTINCT crd_number) FROM firm_executives"
).fetchone()[0]
print(f"\nLoaded: {total_execs:,} executives across {firms_with_execs:,} firms")

# Sample: Top firms with executive names
print("\nSample — executives at largest firms:")
for row in db.execute("""
    SELECT a.legal_name, a.crd_number, e.full_name, e.title
    FROM adv_firms a
    JOIN firm_executives e ON a.crd_number = e.crd_number
    WHERE a.aum_total > 100000000000
    AND e.is_control_person = 1
    ORDER BY a.aum_total DESC
    LIMIT 15
""").fetchall():
    print(f"  {row[0][:40]:40s} | {row[2]:30s} | {row[3]}")

db.close()
z.close()
print("\nDone.")
