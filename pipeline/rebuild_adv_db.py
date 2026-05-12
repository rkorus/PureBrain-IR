#!/usr/bin/env python3
"""
PureBrain IR -- Rebuild ADV Database from SEC FOIA Form ADV bulk data.

Reads from an already-downloaded SEC FOIA ZIP at /tmp/adv-filing-data-part1.zip,
extracts IA and ERA firms (latest filing per CRD), and populates a clean
SQLite database.

Target: /home/parallax/child-civ-template/data/purebrain-ir/api/purebrain_ir.db
Expected: ~27,679 IA firms, ~11,361 ERA firms (39,040 total)

Tables created:
  - adv_firms (Investment Adviser firms)
  - era_firms (Exempt Reporting Advisers)
  - firm_executives (officers/owners from Schedule A/B)
  - ir_fit_metrics (pre-computed fit score metrics, empty)
  - ingestion_log (tracking)

SEC FOIA CSV column reference (Form ADV Part 1):
  FilingID      - Unique filing ID (multiple filings per firm, keep latest)
  1A            - Firm legal name
  1B1           - Firm name (business name)
  1D            - SEC registration number (e.g., 801-30405)
  1E1           - CRD number
  1F1-*         - Main office address fields
  1F3           - Phone
  1F4           - Fax
  1I            - Has website (Y/N)
  1F2-Hours     - Business hours
  1N-CIK        - CIK number (IA only)
  5D1a-5D1n     - Client types (IA only)
  5E1-5E7       - Compensation types (IA only)
  5F2a/b/c      - AUM discretionary/nondiscretionary/total (IA only)
  5G1-5G12      - Service types (IA only)
  2B-Assets     - AUM (ERA only)
  3A            - Entity type (ERA only)
  3C-State/Country - Entity formation (ERA only)
  DateSubmitted - Filing date
  FormVersion   - Form version
"""

import csv
import io
import os
import shutil
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
API_DIR = SCRIPT_DIR.parent / "api"
TARGET_DB = API_DIR / "purebrain_ir.db"

# We expect the ZIP to already be downloaded
ZIP_PATH = Path("/tmp/adv-filing-data-part1.zip")

# Prefix inside the ZIP
ZIP_PREFIX = "adv-filing-data-20111105-20241231-part1"

# ── Schema ────────────────────────────────────────────────────────────────────

ADV_SCHEMA = """
-- adv_firms: SEC-registered Investment Advisers (IA) from Form ADV FOIA data
CREATE TABLE IF NOT EXISTS adv_firms (
    crd_number TEXT PRIMARY KEY,
    legal_name TEXT NOT NULL,
    dba_name TEXT DEFAULT '',
    sec_number TEXT DEFAULT '',
    street1 TEXT DEFAULT '',
    street2 TEXT DEFAULT '',
    city TEXT DEFAULT '',
    state TEXT DEFAULT '',
    country TEXT DEFAULT '',
    postal_code TEXT DEFAULT '',
    is_private_address INTEGER DEFAULT 0,
    phone TEXT DEFAULT '',
    fax TEXT DEFAULT '',
    has_website INTEGER DEFAULT 0,
    business_hours TEXT DEFAULT '',
    aum_discretionary REAL DEFAULT 0,
    aum_nondiscretionary REAL DEFAULT 0,
    aum_total REAL DEFAULT 0,
    clients_individuals INTEGER DEFAULT 0,
    clients_hnw INTEGER DEFAULT 0,
    clients_banking INTEGER DEFAULT 0,
    clients_investment_co INTEGER DEFAULT 0,
    clients_bdc INTEGER DEFAULT 0,
    clients_pooled INTEGER DEFAULT 0,
    clients_pension INTEGER DEFAULT 0,
    clients_charity INTEGER DEFAULT 0,
    clients_govt INTEGER DEFAULT 0,
    clients_other_ia INTEGER DEFAULT 0,
    clients_insurance INTEGER DEFAULT 0,
    clients_sovereign INTEGER DEFAULT 0,
    clients_corporate INTEGER DEFAULT 0,
    clients_other INTEGER DEFAULT 0,
    clients_other_desc TEXT DEFAULT '',
    svc_financial_planning INTEGER DEFAULT 0,
    svc_portfolio_indiv INTEGER DEFAULT 0,
    svc_portfolio_biz INTEGER DEFAULT 0,
    svc_pension_consulting INTEGER DEFAULT 0,
    svc_adviser_selection INTEGER DEFAULT 0,
    svc_publications INTEGER DEFAULT 0,
    svc_security_ratings INTEGER DEFAULT 0,
    svc_market_timing INTEGER DEFAULT 0,
    svc_educational INTEGER DEFAULT 0,
    svc_other INTEGER DEFAULT 0,
    svc_commodities INTEGER DEFAULT 0,
    svc_other2 INTEGER DEFAULT 0,
    svc_other_desc TEXT DEFAULT '',
    comp_pct_aum INTEGER DEFAULT 0,
    comp_hourly INTEGER DEFAULT 0,
    comp_subscription INTEGER DEFAULT 0,
    comp_fixed INTEGER DEFAULT 0,
    comp_commissions INTEGER DEFAULT 0,
    comp_performance INTEGER DEFAULT 0,
    comp_other INTEGER DEFAULT 0,
    entity_type TEXT DEFAULT '',
    entity_state TEXT DEFAULT '',
    entity_country TEXT DEFAULT '',
    filing_id INTEGER,
    filing_date TEXT DEFAULT '',
    form_version TEXT DEFAULT '',
    data_source TEXT DEFAULT 'sec_foia_adv',
    ingested_at TEXT DEFAULT (datetime('now')),
    cik_number TEXT DEFAULT ''
);

-- era_firms: Exempt Reporting Advisers from Form ADV FOIA data
CREATE TABLE IF NOT EXISTS era_firms (
    crd_number TEXT PRIMARY KEY,
    legal_name TEXT NOT NULL,
    dba_name TEXT DEFAULT '',
    sec_number TEXT DEFAULT '',
    street1 TEXT DEFAULT '',
    street2 TEXT DEFAULT '',
    city TEXT DEFAULT '',
    state TEXT DEFAULT '',
    country TEXT DEFAULT '',
    postal_code TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    fax TEXT DEFAULT '',
    has_website INTEGER DEFAULT 0,
    aum_total REAL DEFAULT 0,
    entity_type TEXT DEFAULT '',
    entity_state TEXT DEFAULT '',
    entity_country TEXT DEFAULT '',
    filing_id INTEGER,
    filing_date TEXT DEFAULT '',
    form_version TEXT DEFAULT '',
    data_source TEXT DEFAULT 'sec_foia_era',
    ingested_at TEXT DEFAULT (datetime('now'))
);

-- firm_executives: Key personnel from Form ADV Schedule A/B
CREATE TABLE IF NOT EXISTS firm_executives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crd_number TEXT NOT NULL,
    full_name TEXT NOT NULL,
    title TEXT DEFAULT '',
    is_control_person INTEGER DEFAULT 0,
    ownership_code TEXT DEFAULT '',
    schedule TEXT DEFAULT '',
    owner_id TEXT DEFAULT '',
    UNIQUE(crd_number, owner_id)
);

-- ir_fit_metrics: Pre-computed fit score metrics (populated by compute_metrics.py)
CREATE TABLE IF NOT EXISTS ir_fit_metrics (
    crd_number TEXT PRIMARY KEY,
    cik_number TEXT,
    investor_name TEXT,
    total_positions INTEGER DEFAULT 0,
    total_portfolio_value REAL DEFAULT 0,
    top10_concentration REAL DEFAULT 0,
    new_positions INTEGER DEFAULT 0,
    dropped_positions INTEGER DEFAULT 0,
    turnover_rate REAL DEFAULT 0,
    top_tickers TEXT DEFAULT '',
    latest_period TEXT,
    periods_available INTEGER DEFAULT 0,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ingestion_log: Track data ingestion runs
CREATE TABLE IF NOT EXISTS ingestion_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    table_name TEXT NOT NULL,
    rows_inserted INTEGER DEFAULT 0,
    rows_updated INTEGER DEFAULT 0,
    started_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    status TEXT DEFAULT 'running',
    notes TEXT DEFAULT ''
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_adv_state ON adv_firms(state);
CREATE INDEX IF NOT EXISTS idx_adv_city ON adv_firms(city);
CREATE INDEX IF NOT EXISTS idx_adv_aum ON adv_firms(aum_total);
CREATE INDEX IF NOT EXISTS idx_adv_name ON adv_firms(legal_name);
CREATE INDEX IF NOT EXISTS idx_adv_cik ON adv_firms(cik_number);
CREATE INDEX IF NOT EXISTS idx_adv_filing ON adv_firms(filing_id);
CREATE INDEX IF NOT EXISTS idx_era_state ON era_firms(state);
CREATE INDEX IF NOT EXISTS idx_era_aum ON era_firms(aum_total);
CREATE INDEX IF NOT EXISTS idx_era_name ON era_firms(legal_name);
CREATE INDEX IF NOT EXISTS idx_exec_crd ON firm_executives(crd_number);
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_int(val, default=0):
    if val is None or val == "" or val == "N/A":
        return default
    try:
        return int(float(str(val).replace(",", "").strip()))
    except (ValueError, TypeError):
        return default


def safe_float(val, default=0.0):
    if val is None or val == "" or val == "N/A":
        return default
    try:
        return float(str(val).replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return default


def safe_bool(val, default=0):
    if isinstance(val, str):
        return 1 if val.strip().upper() in ("Y", "YES", "1", "TRUE") else 0
    return default


def s(val):
    """Safe string."""
    if val is None:
        return ""
    return str(val).strip()


def parse_date(val):
    """Parse MM/DD/YYYY or MM/DD/YYYY HH:MM:SS to YYYY-MM-DD."""
    if not val or not val.strip():
        return ""
    raw = val.strip().split(" ")[0]  # Drop time part
    parts = raw.split("/")
    if len(parts) == 3:
        try:
            return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
        except Exception:
            return raw
    return raw


# ── CIK Lookup ────────────────────────────────────────────────────────────────

def load_cik_map(zf):
    """Load FilingID -> CIK mapping from the CIK CSV file."""
    fname = f"{ZIP_PREFIX}/IA_1D3_CIK_20111105_20241231.csv"
    cik_map = {}
    try:
        with zf.open(fname) as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"))
            for row in reader:
                fid = s(row.get("FilingID", ""))
                cik = s(row.get("CIK", ""))
                if fid and cik:
                    cik_map[int(float(fid))] = cik
    except Exception as e:
        print(f"  WARNING: Could not load CIK map: {e}")
    print(f"  Loaded {len(cik_map):,} CIK mappings")
    return cik_map


# ── IA Firms ──────────────────────────────────────────────────────────────────

def parse_ia_firms(zf, conn, cik_map):
    """Parse IA firms from IA_ADV_Base_A CSV. Keep only latest filing per CRD."""
    fname = f"{ZIP_PREFIX}/IA_ADV_Base_A_20111105_20241231.csv"
    print(f"  Reading: {fname}")

    # First pass: find the latest FilingID per CRD (1E1)
    # The CSV has ALL historical filings; we want only the most recent per firm
    print("  Pass 1: Finding latest filing per CRD...")
    latest_fid = {}  # CRD -> (FilingID, DateSubmitted)

    with zf.open(fname) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"))
        row_count = 0
        for row in reader:
            row_count += 1
            crd = s(row.get("1E1", ""))
            fid_str = s(row.get("FilingID", ""))
            date_str = s(row.get("DateSubmitted", ""))
            if not crd or not fid_str:
                continue
            fid = safe_int(fid_str)
            if fid <= 0:
                continue
            # Higher FilingID = more recent
            if crd not in latest_fid or fid > latest_fid[crd][0]:
                latest_fid[crd] = (fid, date_str)
            if row_count % 100000 == 0:
                print(f"    ... scanned {row_count:,} rows, {len(latest_fid):,} unique CRDs")

    print(f"  Pass 1 complete: {row_count:,} total rows, {len(latest_fid):,} unique CRDs")

    # Build set of latest filing IDs
    latest_fids = {fid for fid, _ in latest_fid.values()}
    print(f"  Latest filings to import: {len(latest_fids):,}")

    # Second pass: import the latest filing for each CRD
    print("  Pass 2: Importing latest filings...")
    inserted = 0
    skipped = 0

    with zf.open(fname) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"))
        for row in reader:
            fid = safe_int(row.get("FilingID", ""))
            if fid not in latest_fids:
                continue

            crd = s(row.get("1E1", ""))
            name = s(row.get("1A", ""))
            if not crd or not name:
                skipped += 1
                continue

            # Remove from set so we don't double-insert
            latest_fids.discard(fid)

            aum_d = safe_float(row.get("5F2a", ""))
            aum_nd = safe_float(row.get("5F2b", ""))
            aum_t = safe_float(row.get("5F2c", ""))
            if aum_t == 0 and (aum_d > 0 or aum_nd > 0):
                aum_t = aum_d + aum_nd

            cik = cik_map.get(fid, "")

            values = (
                crd,                                      # crd_number
                name,                                     # legal_name
                s(row.get("1B1", "")),                    # dba_name
                s(row.get("1D", "")),                     # sec_number
                s(row.get("1F1-Street 1", "")),           # street1
                s(row.get("1F1-Street 2", "")),           # street2
                s(row.get("1F1-City", "")),               # city
                s(row.get("1F1-State", "")),              # state
                s(row.get("1F1-Country", "")),            # country
                s(row.get("1F1-Postal", "")),             # postal_code
                safe_bool(row.get("1F1-Private", "")),    # is_private_address
                s(row.get("1F3", "")),                    # phone
                s(row.get("1F4", "")),                    # fax
                safe_bool(row.get("1I", "")),             # has_website
                s(row.get("1F2-Hours", "")),              # business_hours
                aum_d,                                    # aum_discretionary
                aum_nd,                                   # aum_nondiscretionary
                aum_t,                                    # aum_total
                safe_int(row.get("5D1a", "")),            # clients_individuals
                safe_int(row.get("5D1b", "")),            # clients_hnw
                safe_int(row.get("5D1c", "")),            # clients_banking
                safe_int(row.get("5D1d", "")),            # clients_investment_co
                safe_int(row.get("5D1e", "")),            # clients_bdc
                safe_int(row.get("5D1f", "")),            # clients_pooled
                safe_int(row.get("5D1g", "")),            # clients_pension
                safe_int(row.get("5D1h", "")),            # clients_charity
                safe_int(row.get("5D1i", "")),            # clients_govt
                safe_int(row.get("5D1j", "")),            # clients_other_ia
                safe_int(row.get("5D1k", "")),            # clients_insurance
                safe_int(row.get("5D1l", "")),            # clients_sovereign
                safe_int(row.get("5D1m", "")),            # clients_corporate
                safe_int(row.get("5D1n", "")),            # clients_other
                s(row.get("5D1n Other", "")),             # clients_other_desc
                safe_bool(row.get("5G1", "")),            # svc_financial_planning
                safe_bool(row.get("5G2", "")),            # svc_portfolio_indiv
                safe_bool(row.get("5G3", "")),            # svc_portfolio_biz
                safe_bool(row.get("5G4", "")),            # svc_pension_consulting
                safe_bool(row.get("5G5", "")),            # svc_adviser_selection
                safe_bool(row.get("5G6", "")),            # svc_publications
                safe_bool(row.get("5G7", "")),            # svc_security_ratings
                safe_bool(row.get("5G8", "")),            # svc_market_timing
                safe_bool(row.get("5G9", "")),            # svc_educational
                safe_bool(row.get("5G10", "")),           # svc_other
                safe_bool(row.get("5G11", "")),           # svc_commodities
                safe_bool(row.get("5G12", "")),           # svc_other2
                s(row.get("5G12-Other", row.get("5G12 Other", ""))),  # svc_other_desc
                safe_bool(row.get("5E1", "")),            # comp_pct_aum
                safe_bool(row.get("5E2", "")),            # comp_hourly
                safe_bool(row.get("5E3", "")),            # comp_subscription
                safe_bool(row.get("5E4", "")),            # comp_fixed
                safe_bool(row.get("5E5", "")),            # comp_commissions
                safe_bool(row.get("5E6", "")),            # comp_performance
                safe_bool(row.get("5E7", "")),            # comp_other
                "",                                       # entity_type (from Base_B)
                "",                                       # entity_state (from Base_B)
                "",                                       # entity_country (from Base_B)
                fid,                                      # filing_id
                parse_date(s(row.get("DateSubmitted", ""))),  # filing_date
                s(row.get("FormVersion", "")),            # form_version
                "sec_foia_adv",                           # data_source
                cik,                                      # cik_number
            )

            conn.execute(
                "INSERT OR REPLACE INTO adv_firms "
                "(crd_number, legal_name, dba_name, sec_number, "
                "street1, street2, city, state, country, postal_code, "
                "is_private_address, phone, fax, has_website, business_hours, "
                "aum_discretionary, aum_nondiscretionary, aum_total, "
                "clients_individuals, clients_hnw, clients_banking, "
                "clients_investment_co, clients_bdc, clients_pooled, "
                "clients_pension, clients_charity, clients_govt, "
                "clients_other_ia, clients_insurance, clients_sovereign, "
                "clients_corporate, clients_other, clients_other_desc, "
                "svc_financial_planning, svc_portfolio_indiv, svc_portfolio_biz, "
                "svc_pension_consulting, svc_adviser_selection, svc_publications, "
                "svc_security_ratings, svc_market_timing, svc_educational, "
                "svc_other, svc_commodities, svc_other2, svc_other_desc, "
                "comp_pct_aum, comp_hourly, comp_subscription, comp_fixed, "
                "comp_commissions, comp_performance, comp_other, "
                "entity_type, entity_state, entity_country, "
                "filing_id, filing_date, form_version, data_source, cik_number) "
                "VALUES (" + ",".join(["?"] * 61) + ")",
                values,
            )
            inserted += 1

            if inserted % 5000 == 0:
                conn.commit()
                print(f"    ... {inserted:,} IA firms inserted")

    conn.commit()
    print(f"  IA firms inserted: {inserted:,} (skipped: {skipped:,})")
    return inserted


def enrich_ia_from_base_b(zf, conn):
    """Enrich IA firms with entity type from IA_ADV_Base_B (organizational info)."""
    fname = f"{ZIP_PREFIX}/IA_ADV_Base_B_20111105_20241231.csv"
    print(f"  Reading Base B: {fname}")

    # Get the filing IDs that are in our adv_firms table
    our_fids = set()
    rows = conn.execute("SELECT filing_id FROM adv_firms WHERE filing_id IS NOT NULL").fetchall()
    for r in rows:
        our_fids.add(r[0])
    print(f"  Matching against {len(our_fids):,} filing IDs")

    updated = 0
    with zf.open(fname) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"))
        for row in reader:
            fid = safe_int(row.get("FilingID", ""))
            if fid not in our_fids:
                continue

            # Entity type = 4A in Base B
            entity_type = s(row.get("4A", row.get("3A", "")))
            entity_state = s(row.get("4B-State", row.get("3C-State", "")))
            entity_country = s(row.get("4B-Country", row.get("3C-Country", "")))

            if entity_type or entity_state or entity_country:
                conn.execute(
                    "UPDATE adv_firms SET entity_type = ?, entity_state = ?, "
                    "entity_country = ? WHERE filing_id = ?",
                    (entity_type, entity_state, entity_country, fid),
                )
                updated += 1

    conn.commit()
    print(f"  Enriched {updated:,} firms with entity type from Base B")


# ── ERA Firms ─────────────────────────────────────────────────────────────────

def parse_era_firms(zf, conn):
    """Parse ERA firms from ERA_ADV_Base CSV. Keep only latest filing per CRD."""
    fname = f"{ZIP_PREFIX}/ERA_ADV_Base_20111105_20241231.csv"
    print(f"  Reading: {fname}")

    # Pass 1: find latest filing per CRD
    print("  Pass 1: Finding latest filing per CRD...")
    latest_fid = {}

    with zf.open(fname) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"))
        row_count = 0
        for row in reader:
            row_count += 1
            crd = s(row.get("1E1", ""))
            fid = safe_int(row.get("FilingID", ""))
            if not crd or fid <= 0:
                continue
            if crd not in latest_fid or fid > latest_fid[crd]:
                latest_fid[crd] = fid

    print(f"  Pass 1: {row_count:,} rows, {len(latest_fid):,} unique CRDs")
    latest_fids = set(latest_fid.values())

    # Pass 2: import
    print("  Pass 2: Importing latest filings...")
    inserted = 0
    skipped = 0

    with zf.open(fname) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"))
        for row in reader:
            fid = safe_int(row.get("FilingID", ""))
            if fid not in latest_fids:
                continue

            crd = s(row.get("1E1", ""))
            name = s(row.get("1A", ""))
            if not crd or not name:
                skipped += 1
                continue

            latest_fids.discard(fid)

            aum = safe_float(row.get("2B-Assets", ""))

            values = (
                crd,                                      # crd_number
                name,                                     # legal_name
                s(row.get("1B1", "")),                    # dba_name
                s(row.get("1D", "")),                     # sec_number
                s(row.get("1F1-Street 1", "")),           # street1
                s(row.get("1F1-Street 2", "")),           # street2
                s(row.get("1F1-City", "")),               # city
                s(row.get("1F1-State", "")),              # state
                s(row.get("1F1-Country", "")),            # country
                s(row.get("1F1-Postal", "")),             # postal_code
                s(row.get("1F3", "")),                    # phone
                s(row.get("1F4", "")),                    # fax
                safe_bool(row.get("1I", "")),             # has_website
                aum,                                      # aum_total
                s(row.get("3A", "")),                     # entity_type
                s(row.get("3C-State", "")),               # entity_state
                s(row.get("3C-Country", "")),             # entity_country
                fid,                                      # filing_id
                parse_date(s(row.get("DateSubmitted", ""))),  # filing_date
                s(row.get("FormVersion", "")),            # form_version
            )

            conn.execute(
                "INSERT OR REPLACE INTO era_firms "
                "(crd_number, legal_name, dba_name, sec_number, "
                "street1, street2, city, state, country, postal_code, "
                "phone, fax, has_website, aum_total, "
                "entity_type, entity_state, entity_country, "
                "filing_id, filing_date, form_version) "
                "VALUES (" + ",".join(["?"] * 20) + ")",
                values,
            )
            inserted += 1

            if inserted % 5000 == 0:
                conn.commit()
                print(f"    ... {inserted:,} ERA firms inserted")

    conn.commit()
    print(f"  ERA firms inserted: {inserted:,} (skipped: {skipped:,})")
    return inserted


# ── Executives ────────────────────────────────────────────────────────────────

def parse_executives(zf, conn):
    """Parse IA executives from IA_Schedule_A_B CSV. Match via FilingID."""
    fname = f"{ZIP_PREFIX}/IA_Schedule_A_B_20111105_20241231.csv"
    print(f"  Reading: {fname}")

    # Build FilingID -> CRD mapping from adv_firms
    print("  Building FilingID -> CRD mapping...")
    fid_to_crd = {}
    rows = conn.execute(
        "SELECT crd_number, filing_id FROM adv_firms WHERE filing_id IS NOT NULL"
    ).fetchall()
    for crd, fid in rows:
        fid_to_crd[fid] = crd
    print(f"    {len(fid_to_crd):,} filing IDs mapped")

    execs_by_crd = defaultdict(list)
    processed = 0
    skipped = 0

    with zf.open(fname) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"))
        for row in reader:
            processed += 1

            fid = safe_int(row.get("FilingID", ""))
            if fid not in fid_to_crd:
                skipped += 1
                continue

            # Only individuals (not entity owners)
            owner_type = s(row.get("DE/FE/I", ""))
            if owner_type != "I":
                continue

            crd = fid_to_crd[fid]
            name = s(row.get("Full Legal Name", ""))
            title = s(row.get("Title or Status", ""))
            control = 1 if s(row.get("Control Person", "")).upper() in ("Y", "YES") else 0
            ownership = s(row.get("Ownership Code", ""))
            schedule = s(row.get("Schedule", ""))
            owner_id = s(row.get("OwnerID", ""))

            if name:
                execs_by_crd[crd].append({
                    "name": name,
                    "title": title,
                    "control": control,
                    "ownership": ownership,
                    "schedule": schedule,
                    "owner_id": owner_id,
                })

            if processed % 200000 == 0:
                print(f"    ... processed {processed:,} Schedule A/B rows")

    print(f"  Schedule A/B: {processed:,} rows, {skipped:,} skipped")
    print(f"  Firms with executives: {len(execs_by_crd):,}")

    # Insert
    inserted = 0
    for crd, execs in execs_by_crd.items():
        for ex in execs:
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO firm_executives "
                    "(crd_number, full_name, title, is_control_person, "
                    "ownership_code, schedule, owner_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (crd, ex["name"], ex["title"], ex["control"],
                     ex["ownership"], ex["schedule"], ex["owner_id"]),
                )
                inserted += 1
            except Exception:
                pass

    conn.commit()
    print(f"  Executives inserted: {inserted:,}")
    return inserted


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("PureBrain IR -- ADV Database Rebuild")
    print(f"Target: {TARGET_DB}")
    print(f"Source: {ZIP_PATH}")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    # Verify ZIP exists
    if not ZIP_PATH.exists():
        print(f"\nERROR: ZIP not found at {ZIP_PATH}")
        print("Download it first:")
        print(f'  curl --max-time 600 -L -o {ZIP_PATH} '
              '"https://www.sec.gov/files/adv-filing-data-20111105-20241231-part1.zip" '
              '-H "User-Agent: PureBrain-IR parallax.aiciv@gmail.com"')
        sys.exit(1)

    zf = zipfile.ZipFile(str(ZIP_PATH), "r")
    print(f"\n[1/6] ZIP verified: {len(zf.namelist())} files")

    # Create clean database
    print(f"\n[2/6] Creating clean database...")
    if TARGET_DB.exists():
        backup = TARGET_DB.with_suffix(".db.bak")
        print(f"  Backing up to {backup}")
        shutil.copy2(str(TARGET_DB), str(backup))
        os.remove(str(TARGET_DB))

    conn = sqlite3.connect(str(TARGET_DB))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")
    conn.executescript(ADV_SCHEMA)
    conn.execute(
        "INSERT INTO ingestion_log (source, table_name, status, notes) "
        "VALUES (?, ?, ?, ?)",
        ("sec_foia_adv", "adv_firms,era_firms,firm_executives", "running",
         f"Started {datetime.now().isoformat()}"),
    )
    conn.commit()
    print("  Schema created")

    # Load CIK map
    print(f"\n[3/6] Loading CIK mappings...")
    cik_map = load_cik_map(zf)

    # Parse IA firms
    print(f"\n[4/6] Parsing IA firms...")
    ia_count = parse_ia_firms(zf, conn, cik_map)

    # Enrich with Base B data
    print(f"\n  Enriching from Base B...")
    try:
        enrich_ia_from_base_b(zf, conn)
    except Exception as e:
        print(f"  WARNING: Base B enrichment failed: {e}")

    # Parse ERA firms
    print(f"\n[5/6] Parsing ERA firms...")
    era_count = parse_era_firms(zf, conn)

    # Parse executives
    print(f"\n[6/6] Parsing executives...")
    exec_count = parse_executives(zf, conn)

    # Update ingestion log
    conn.execute(
        "UPDATE ingestion_log SET status = ?, completed_at = ?, "
        "rows_inserted = ?, notes = ? WHERE id = (SELECT MAX(id) FROM ingestion_log)",
        ("completed", datetime.now().isoformat(),
         ia_count + era_count + exec_count,
         f"IA: {ia_count:,}, ERA: {era_count:,}, Execs: {exec_count:,}"),
    )
    conn.commit()

    # Verification
    print(f"\n{'=' * 70}")
    print("VERIFICATION")
    print("=" * 70)

    adv_count = conn.execute("SELECT COUNT(*) FROM adv_firms").fetchone()[0]
    era_db_count = conn.execute("SELECT COUNT(*) FROM era_firms").fetchone()[0]
    exec_db_count = conn.execute("SELECT COUNT(*) FROM firm_executives").fetchone()[0]
    fit_count = conn.execute("SELECT COUNT(*) FROM ir_fit_metrics").fetchone()[0]

    print(f"  adv_firms:       {adv_count:,}")
    print(f"  era_firms:       {era_db_count:,}")
    print(f"  firm_executives: {exec_db_count:,}")
    print(f"  ir_fit_metrics:  {fit_count:,} (empty, populated by compute_metrics.py)")
    print(f"  TOTAL FIRMS:     {adv_count + era_db_count:,}")

    print(f"\n  Top 5 IA firms by AUM:")
    for row in conn.execute(
        "SELECT legal_name, state, aum_total FROM adv_firms ORDER BY aum_total DESC LIMIT 5"
    ).fetchall():
        aum_b = row[2] / 1e9 if row[2] else 0
        print(f"    {row[0][:50]:50s} | {row[1] or 'N/A':5s} | ${aum_b:.1f}B")

    print(f"\n  Top 5 ERA firms by AUM:")
    for row in conn.execute(
        "SELECT legal_name, state, aum_total FROM era_firms ORDER BY aum_total DESC LIMIT 5"
    ).fetchall():
        aum_b = row[2] / 1e9 if row[2] else 0
        print(f"    {row[0][:50]:50s} | {row[1] or 'N/A':5s} | ${aum_b:.1f}B")

    print(f"\n  Top 10 states (IA):")
    for row in conn.execute(
        "SELECT state, COUNT(*) as cnt FROM adv_firms WHERE state != '' "
        "GROUP BY state ORDER BY cnt DESC LIMIT 10"
    ).fetchall():
        print(f"    {row[0]:5s}: {row[1]:,}")

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    print(f"\n  Tables: {[t[0] for t in tables]}")

    db_size_mb = TARGET_DB.stat().st_size / (1024 * 1024)
    print(f"  Database size: {db_size_mb:.1f} MB")

    conn.close()
    zf.close()

    print(f"\n{'=' * 70}")
    print(f"REBUILD COMPLETE")
    print(f"  IA firms:    {adv_count:,}")
    print(f"  ERA firms:   {era_db_count:,}")
    print(f"  Executives:  {exec_db_count:,}")
    print(f"  Database:    {TARGET_DB}")
    print(f"  Finished:    {datetime.now().isoformat()}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    import zipfile
    main()
