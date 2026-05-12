#!/usr/bin/env python3
"""
parse_disclosures.py - Parse SEC FOIA Form ADV DRP disclosure data.

Reads Criminal, Civil Judicial, and Regulatory DRP CSVs from the SEC FOIA
bulk data ZIP, maps FilingID -> CRD number via the adv_firms table, and
populates a firm_disclosures table in the PureBrain IR database.

Data source: /tmp/adv-filing-data-part1.zip
    Contains: adv-filing-data-20111105-20241231-part1/
        - IA_DRP_Criminal_20111105_20241231.csv          (26 cols)
        - IA_DRP_Civil_Judicial_20111105_20241231.csv    (44 cols)
        - IA_DRP_Regulatory_20111105_20151231.csv        (54 cols)
        - IA_DRP_Regulatory_20160101_20201231.csv        (54 cols)
        - IA_DRP_Regulatory_20210101_20241231.csv        (54 cols)

Target: purebrain_ir.db -> firm_disclosures table
"""

import csv
import io
import os
import re
import sqlite3
import sys
import zipfile
from collections import defaultdict

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ZIP_PATH = "/tmp/adv-filing-data-part1.zip"
DB_PATH = "/home/parallax/child-civ-template/data/purebrain-ir/api/purebrain_ir.db"
CSV_ENCODING = "latin-1"

PREFIX = "adv-filing-data-20111105-20241231-part1"

CRIMINAL_CSV = f"{PREFIX}/IA_DRP_Criminal_20111105_20241231.csv"
CIVIL_CSV = f"{PREFIX}/IA_DRP_Civil_Judicial_20111105_20241231.csv"
REGULATORY_CSVS = [
    f"{PREFIX}/IA_DRP_Regulatory_20111105_20151231.csv",
    f"{PREFIX}/IA_DRP_Regulatory_20160101_20201231.csv",
    f"{PREFIX}/IA_DRP_Regulatory_20210101_20241231.csv",
]

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = """
DROP TABLE IF EXISTS firm_disclosures;

CREATE TABLE IF NOT EXISTS firm_disclosures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crd_number TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_date TEXT,
    description TEXT,
    allegations TEXT,
    principal_sanction TEXT,
    monetary_amount REAL,
    status TEXT,
    resolution TEXT,
    has_bar INTEGER DEFAULT 0,
    filing_id INTEGER,
    FOREIGN KEY (crd_number) REFERENCES adv_firms(crd_number)
);

CREATE INDEX IF NOT EXISTS idx_disc_crd ON firm_disclosures(crd_number);
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_monetary(value: str) -> float | None:
    """Parse a monetary amount string into a float. Returns None if empty/invalid."""
    if not value or not value.strip():
        return None
    cleaned = value.strip().replace("$", "").replace(",", "").replace(" ", "")
    # Handle parenthetical negatives like (1000)
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_bar(value: str) -> int:
    """Check if the Bar field indicates a bar was imposed."""
    if not value or not value.strip():
        return 0
    v = value.strip().upper()
    if v in ("Y", "YES", "TRUE", "1"):
        return 1
    # Any non-empty, non-N value also counts
    if v not in ("N", "NO", "FALSE", "0", ""):
        return 1
    return 0


def safe_str(value: str) -> str | None:
    """Return stripped string or None if empty."""
    if value is None:
        return None
    v = value.strip()
    return v if v else None


def build_filing_map(conn: sqlite3.Connection) -> dict[int, str]:
    """Build a mapping from filing_id (int) -> crd_number (str)."""
    cur = conn.cursor()
    cur.execute("SELECT filing_id, crd_number FROM adv_firms WHERE filing_id IS NOT NULL")
    mapping = {}
    for row in cur.fetchall():
        filing_id, crd = row
        if filing_id is not None:
            mapping[int(filing_id)] = str(crd)
    return mapping


def read_csv_from_zip(zf: zipfile.ZipFile, csv_path: str):
    """Read a CSV file from the ZIP, yielding dicts for each row."""
    with zf.open(csv_path) as f:
        text = io.TextIOWrapper(f, encoding=CSV_ENCODING, errors="replace")
        reader = csv.DictReader(text)
        for row in reader:
            yield row


# ---------------------------------------------------------------------------
# Parsers for each DRP type
# ---------------------------------------------------------------------------


def parse_criminal(zf: zipfile.ZipFile, filing_map: dict[int, str]) -> list[tuple]:
    """
    Parse Criminal DRP CSV.

    Key columns:
        FilingID, Filed Against, Date First Charged, Event Detail,
        Felony, Status, Disposition, Summary
    """
    rows = []
    skipped = 0
    total = 0

    for record in read_csv_from_zip(zf, CRIMINAL_CSV):
        total += 1
        try:
            filing_id = int(record.get("FilingID", "0"))
        except (ValueError, TypeError):
            skipped += 1
            continue

        crd = filing_map.get(filing_id)
        if not crd:
            skipped += 1
            continue

        # Build description from Event Detail + Filed Against + Felony info
        parts = []
        if safe_str(record.get("Filed Against", "")):
            parts.append(f"Filed against: {record['Filed Against'].strip()}")
        if safe_str(record.get("Court", "")):
            parts.append(f"Court: {record['Court'].strip()}")
        felony = record.get("Felony", "").strip().upper()
        if felony == "Y":
            parts.append("Felony: Yes")

        event_detail = safe_str(record.get("Event Detail", ""))
        if event_detail:
            parts.append(event_detail)

        description = "; ".join(parts) if parts else None
        summary = safe_str(record.get("Summary", ""))

        rows.append((
            crd,                                          # crd_number
            "criminal",                                   # event_type
            safe_str(record.get("Date First Charged", "")),  # event_date
            description,                                  # description
            summary,                                      # allegations (using summary for criminal)
            None,                                         # principal_sanction
            None,                                         # monetary_amount (not in criminal)
            safe_str(record.get("Status", "")),           # status
            safe_str(record.get("Disposition", "")),      # resolution
            0,                                            # has_bar (not in criminal)
            filing_id,                                    # filing_id
        ))

    print(f"  Criminal: {total} total rows, {len(rows)} matched, {skipped} skipped")
    return rows


def parse_civil(zf: zipfile.ZipFile, filing_map: dict[int, str]) -> list[tuple]:
    """
    Parse Civil Judicial DRP CSV.

    Key columns:
        FilingID, Filed Against, Filing Date, Allegations, Principal Product,
        Status, Resolution Type, Resolution Date, Monetary Amount, Bar, Summary
    """
    rows = []
    skipped = 0
    total = 0

    for record in read_csv_from_zip(zf, CIVIL_CSV):
        total += 1
        try:
            filing_id = int(record.get("FilingID", "0"))
        except (ValueError, TypeError):
            skipped += 1
            continue

        crd = filing_map.get(filing_id)
        if not crd:
            skipped += 1
            continue

        # Build description
        parts = []
        if safe_str(record.get("Filed Against", "")):
            parts.append(f"Filed against: {record['Filed Against'].strip()}")
        if safe_str(record.get("Initiated By", "")):
            parts.append(f"Initiated by: {record['Initiated By'].strip()}")
        if safe_str(record.get("Court", "")):
            parts.append(f"Court: {record['Court'].strip()}")
        if safe_str(record.get("Principal Product", "")):
            parts.append(f"Product: {record['Principal Product'].strip()}")
        if safe_str(record.get("Sanction Detail", "")):
            parts.append(record["Sanction Detail"].strip())

        description = "; ".join(parts) if parts else None

        # Resolution: combine type and date
        res_type = safe_str(record.get("Resolution Type", ""))
        res_date = safe_str(record.get("Resolution Date", ""))
        resolution = None
        if res_type and res_date:
            resolution = f"{res_type} ({res_date})"
        elif res_type:
            resolution = res_type
        elif res_date:
            resolution = res_date

        # Other sanctions text
        other_sanctions = safe_str(record.get("Other Sanctions", ""))

        rows.append((
            crd,                                          # crd_number
            "civil",                                      # event_type
            safe_str(record.get("Filing Date", "")),      # event_date
            description,                                  # description
            safe_str(record.get("Allegations", "")),      # allegations
            safe_str(record.get("Relief Sought", "")),    # principal_sanction
            parse_monetary(record.get("Monetary Amount", "")),  # monetary_amount
            safe_str(record.get("Status", "")),           # status
            resolution,                                   # resolution
            parse_bar(record.get("Bar", "")),             # has_bar
            filing_id,                                    # filing_id
        ))

    print(f"  Civil Judicial: {total} total rows, {len(rows)} matched, {skipped} skipped")
    return rows


def parse_regulatory(zf: zipfile.ZipFile, filing_map: dict[int, str]) -> list[tuple]:
    """
    Parse Regulatory DRP CSVs (all 3 time periods).

    Key columns:
        FilingID, Filed Against, Principal Sanction, Other Sanctions,
        Date Initiated, Allegations, Status, Resolution, Resolution Date,
        Monetary Amount, Bar, Summary
    """
    all_rows = []
    total_all = 0
    matched_all = 0
    skipped_all = 0

    for csv_path in REGULATORY_CSVS:
        rows = []
        skipped = 0
        total = 0
        basename = os.path.basename(csv_path)

        for record in read_csv_from_zip(zf, csv_path):
            total += 1
            try:
                filing_id = int(record.get("FilingID", "0"))
            except (ValueError, TypeError):
                skipped += 1
                continue

            crd = filing_map.get(filing_id)
            if not crd:
                skipped += 1
                continue

            # Build description
            parts = []
            if safe_str(record.get("Filed Against", "")):
                parts.append(f"Filed against: {record['Filed Against'].strip()}")
            if safe_str(record.get("Initiated By", "")):
                parts.append(f"Initiated by: {record['Initiated By'].strip()}")
            if safe_str(record.get("Case Number", "")):
                parts.append(f"Case: {record['Case Number'].strip()}")
            if safe_str(record.get("Principal Product", "")):
                parts.append(f"Product: {record['Principal Product'].strip()}")
            if safe_str(record.get("Sanction Detail", "")):
                parts.append(record["Sanction Detail"].strip())
            summary = safe_str(record.get("Summary", ""))
            if summary:
                parts.append(summary)

            description = "; ".join(parts) if parts else None

            # Principal sanction + other sanctions
            principal = safe_str(record.get("Principal Sanction", ""))
            other = safe_str(record.get("Other Sanctions", ""))
            if principal and other:
                principal_sanction = f"{principal}; {other}"
            else:
                principal_sanction = principal or other

            # Resolution: combine resolution type and date
            res_type = safe_str(record.get("Resolution", ""))
            res_date = safe_str(record.get("Resolution Date", ""))
            resolution = None
            if res_type and res_date:
                resolution = f"{res_type} ({res_date})"
            elif res_type:
                resolution = res_type
            elif res_date:
                resolution = res_date

            rows.append((
                crd,                                              # crd_number
                "regulatory",                                     # event_type
                safe_str(record.get("Date Initiated", "")),       # event_date
                description,                                      # description
                safe_str(record.get("Allegations", "")),          # allegations
                principal_sanction,                               # principal_sanction
                parse_monetary(record.get("Monetary Amount", "")),  # monetary_amount
                safe_str(record.get("Status", "")),               # status
                resolution,                                       # resolution
                parse_bar(record.get("Bar", "")),                 # has_bar
                filing_id,                                        # filing_id
            ))

        print(f"  Regulatory ({basename}): {total} total rows, {len(rows)} matched, {skipped} skipped")
        total_all += total
        matched_all += len(rows)
        skipped_all += skipped
        all_rows.extend(rows)

    print(f"  Regulatory TOTAL: {total_all} total rows, {matched_all} matched, {skipped_all} skipped")
    return all_rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 70)
    print("SEC FOIA Form ADV DRP Disclosure Parser")
    print("=" * 70)

    # Validate inputs
    if not os.path.exists(ZIP_PATH):
        print(f"ERROR: ZIP file not found: {ZIP_PATH}")
        sys.exit(1)

    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found: {DB_PATH}")
        sys.exit(1)

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # Build filing_id -> crd_number mapping
    print("\n[1/5] Building FilingID -> CRD mapping from adv_firms...")
    filing_map = build_filing_map(conn)
    print(f"  Loaded {len(filing_map)} filing_id -> crd_number mappings")

    # Create table (idempotent)
    print("\n[2/5] Creating firm_disclosures table...")
    conn.executescript(CREATE_TABLE_SQL)
    print("  Table created (previous data dropped)")

    # Open ZIP and parse all DRP types
    print(f"\n[3/5] Parsing DRP CSVs from {ZIP_PATH}...")
    all_disclosures = []

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        # Verify expected files exist
        names = zf.namelist()
        for expected in [CRIMINAL_CSV, CIVIL_CSV] + REGULATORY_CSVS:
            if expected not in names:
                print(f"  WARNING: Expected file not found in ZIP: {expected}")

        print("\n  --- Criminal DRP ---")
        criminal_rows = parse_criminal(zf, filing_map)
        all_disclosures.extend(criminal_rows)

        print("\n  --- Civil Judicial DRP ---")
        civil_rows = parse_civil(zf, filing_map)
        all_disclosures.extend(civil_rows)

        print("\n  --- Regulatory DRP ---")
        regulatory_rows = parse_regulatory(zf, filing_map)
        all_disclosures.extend(regulatory_rows)

    # Insert into database
    print(f"\n[4/5] Inserting {len(all_disclosures)} disclosures into database...")
    insert_sql = """
    INSERT INTO firm_disclosures (
        crd_number, event_type, event_date, description, allegations,
        principal_sanction, monetary_amount, status, resolution,
        has_bar, filing_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    # Batch insert for performance
    BATCH_SIZE = 5000
    for i in range(0, len(all_disclosures), BATCH_SIZE):
        batch = all_disclosures[i : i + BATCH_SIZE]
        conn.executemany(insert_sql, batch)
        if (i + BATCH_SIZE) % 50000 == 0 or i + BATCH_SIZE >= len(all_disclosures):
            print(f"  Inserted {min(i + BATCH_SIZE, len(all_disclosures))}/{len(all_disclosures)} rows...")

    conn.commit()
    print("  Commit complete.")

    # Summary statistics
    print(f"\n[5/5] Summary Statistics")
    print("=" * 70)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM firm_disclosures")
    total = cur.fetchone()[0]
    print(f"  Total disclosures:          {total:,}")

    cur.execute("SELECT event_type, COUNT(*) FROM firm_disclosures GROUP BY event_type ORDER BY COUNT(*) DESC")
    print("\n  By type:")
    for event_type, count in cur.fetchall():
        print(f"    {event_type:20s} {count:>8,}")

    cur.execute("SELECT COUNT(DISTINCT crd_number) FROM firm_disclosures")
    firms_with = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM adv_firms")
    total_firms = cur.fetchone()[0]
    print(f"\n  Firms with disclosures:     {firms_with:,} / {total_firms:,} ({100*firms_with/total_firms:.1f}%)")

    cur.execute("SELECT COUNT(DISTINCT crd_number) FROM firm_disclosures WHERE has_bar = 1")
    bar_firms = cur.fetchone()[0]
    print(f"  Firms with bar actions:     {bar_firms:,}")

    cur.execute("SELECT COUNT(*) FROM firm_disclosures WHERE monetary_amount IS NOT NULL AND monetary_amount > 0")
    monetary_count = cur.fetchone()[0]
    cur.execute("SELECT SUM(monetary_amount) FROM firm_disclosures WHERE monetary_amount IS NOT NULL AND monetary_amount > 0")
    monetary_sum = cur.fetchone()[0] or 0
    print(f"  Monetary sanctions:         {monetary_count:,} events, ${monetary_sum:,.0f} total")

    cur.execute("SELECT COUNT(*) FROM firm_disclosures WHERE event_type = 'criminal'")
    crim = cur.fetchone()[0]
    print(f"  Criminal disclosures:       {crim:,}")

    # High-risk: firms with 3+ disclosures OR any criminal OR any bar
    cur.execute("""
        SELECT COUNT(DISTINCT crd_number) FROM (
            SELECT crd_number FROM firm_disclosures
            GROUP BY crd_number HAVING COUNT(*) >= 3
            UNION
            SELECT DISTINCT crd_number FROM firm_disclosures WHERE event_type = 'criminal'
            UNION
            SELECT DISTINCT crd_number FROM firm_disclosures WHERE has_bar = 1
        )
    """)
    high_risk = cur.fetchone()[0]
    print(f"  High-risk firms:            {high_risk:,} (3+ events OR criminal OR bar)")

    # Top 5 most-disclosed firms
    cur.execute("""
        SELECT d.crd_number, f.legal_name, COUNT(*) as cnt
        FROM firm_disclosures d
        LEFT JOIN adv_firms f ON d.crd_number = f.crd_number
        GROUP BY d.crd_number
        ORDER BY cnt DESC
        LIMIT 5
    """)
    print("\n  Top 5 firms by disclosure count:")
    for crd, name, cnt in cur.fetchall():
        display_name = (name[:50] + "...") if name and len(name) > 50 else (name or "Unknown")
        print(f"    CRD {crd:>8s}: {cnt:>4,} disclosures  ({display_name})")

    print("\n" + "=" * 70)
    print("Done. firm_disclosures table populated successfully.")
    print("=" * 70)

    conn.close()


if __name__ == "__main__":
    main()
