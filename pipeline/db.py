"""Database layer for PureBrain IR pipeline.

Uses SQLite locally (compatible with Cloudflare D1 schema).
Schema matches SRS Section 3 exactly.
"""

import sqlite3
import uuid
import os
from dataclasses import dataclass

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "purebrain_ir.db")


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Get SQLite connection with WAL mode for performance."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection):
    """Create all tables matching SRS Section 3 schema."""
    conn.executescript(SCHEMA_SQL)


def generate_id() -> str:
    """Generate a UUID for primary keys."""
    return str(uuid.uuid4())


# -- Data insertion --

def upsert_investor(conn: sqlite3.Connection, **kwargs) -> str:
    """Insert or update an investor record. Returns investor ID.

    Matches on CIK (for 13F filers) or IARD number (for Form ADV).
    """
    cik = kwargs.get("cik")
    iard = kwargs.get("iard_number")

    # Check existing
    existing = None
    if cik:
        existing = conn.execute(
            "SELECT id FROM ir_investors WHERE cik = ?", (cik,)
        ).fetchone()
    elif iard:
        existing = conn.execute(
            "SELECT id FROM ir_investors WHERE iard_number = ?", (iard,)
        ).fetchone()

    if existing:
        investor_id = existing["id"]
        # Update mutable fields
        updates = []
        params = []
        for field in ["name", "type", "aum_estimate", "investment_style",
                       "geography", "hq_state", "hq_city", "address",
                       "website", "phone", "last_13f_filed", "data_source"]:
            if field in kwargs and kwargs[field] is not None:
                updates.append(f"{field} = ?")
                params.append(kwargs[field])
        if updates:
            updates.append("last_updated = datetime('now')")
            params.append(investor_id)
            conn.execute(
                f"UPDATE ir_investors SET {', '.join(updates)} WHERE id = ?",
                params,
            )
        return investor_id

    # Insert new
    investor_id = generate_id()
    kwargs["id"] = investor_id
    kwargs.setdefault("type", "asset_manager")
    kwargs.setdefault("data_source", "edgar_13f")

    fields = [k for k in kwargs if k in INVESTOR_FIELDS]
    placeholders = ", ".join(["?"] * len(fields))
    columns = ", ".join(fields)
    values = [kwargs[f] for f in fields]

    conn.execute(
        f"INSERT INTO ir_investors ({columns}) VALUES ({placeholders})",
        values,
    )
    return investor_id


def insert_holdings(conn: sqlite3.Connection, investor_id: str,
                    holdings: list[dict], filing_type: str,
                    filing_date: str, period_of_report: str):
    """Bulk insert holdings for an investor/filing.

    Uses INSERT OR IGNORE to skip duplicates (unique constraint on
    investor_id + ticker + filing_type + period_of_report).
    """
    for h in holdings:
        conn.execute("""
            INSERT OR IGNORE INTO ir_holdings
            (id, investor_id, ticker, company_name, cusip, shares,
             market_value, filing_type, filing_date, period_of_report,
             investment_discretion, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            generate_id(),
            investor_id,
            h.get("ticker", ""),
            h.get("company_name", ""),
            h.get("cusip", ""),
            h.get("shares", 0),
            h.get("market_value", 0),
            filing_type,
            filing_date,
            period_of_report,
            h.get("investment_discretion", ""),
            h.get("source_url", ""),
        ))


def get_investor_by_cik(conn: sqlite3.Connection, cik: str) -> dict | None:
    """Look up investor by CIK."""
    row = conn.execute(
        "SELECT * FROM ir_investors WHERE cik = ?", (cik,)
    ).fetchone()
    return dict(row) if row else None


def get_holdings_count(conn: sqlite3.Connection) -> int:
    """Get total holdings count."""
    row = conn.execute("SELECT COUNT(*) as cnt FROM ir_holdings").fetchone()
    return row["cnt"]


def get_investor_count(conn: sqlite3.Connection) -> int:
    """Get total investor count."""
    row = conn.execute("SELECT COUNT(*) as cnt FROM ir_investors").fetchone()
    return row["cnt"]


def get_stats(conn: sqlite3.Connection) -> dict:
    """Get database statistics."""
    return {
        "investors": get_investor_count(conn),
        "holdings": get_holdings_count(conn),
        "filings": conn.execute(
            "SELECT COUNT(DISTINCT investor_id || period_of_report) as cnt FROM ir_holdings"
        ).fetchone()["cnt"],
        "unique_cusips": conn.execute(
            "SELECT COUNT(DISTINCT cusip) as cnt FROM ir_holdings WHERE cusip != ''"
        ).fetchone()["cnt"],
    }


# -- Field whitelist --

INVESTOR_FIELDS = {
    "id", "name", "type", "cik", "sec_file_number", "iard_number",
    "aum_estimate", "aum_updated_at", "investment_style", "primary_sector",
    "secondary_sectors", "geography", "hq_country", "hq_state", "hq_city",
    "address", "website", "phone", "founded_year", "num_employees",
    "client_types", "min_account_size", "compensation_type", "custodians",
    "primary_contact_name", "primary_contact_email", "primary_contact_phone",
    "tags", "is_activist", "is_passive", "last_13f_filed", "last_adv_updated",
    "data_source",
}


# -- Schema SQL (from SRS Section 3) --

SCHEMA_SQL = """
-- ir_investors: Institutional investors and registered investment advisers
CREATE TABLE IF NOT EXISTS ir_investors (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  cik TEXT,
  sec_file_number TEXT,
  iard_number TEXT,
  aum_estimate INTEGER,
  aum_updated_at TEXT,
  investment_style TEXT,
  primary_sector TEXT,
  secondary_sectors TEXT,
  geography TEXT,
  hq_country TEXT,
  hq_state TEXT,
  hq_city TEXT,
  address TEXT,
  website TEXT,
  phone TEXT,
  founded_year INTEGER,
  num_employees INTEGER,
  client_types TEXT,
  min_account_size INTEGER,
  compensation_type TEXT,
  custodians TEXT,
  primary_contact_name TEXT,
  primary_contact_email TEXT,
  primary_contact_phone TEXT,
  tags TEXT,
  is_activist INTEGER DEFAULT 0,
  is_passive INTEGER DEFAULT 0,
  last_13f_filed TEXT,
  last_adv_updated TEXT,
  data_source TEXT,
  last_updated TEXT DEFAULT (datetime('now')),
  created_at TEXT DEFAULT (datetime('now'))
);

-- ir_holdings: Investor holdings from 13F filings
CREATE TABLE IF NOT EXISTS ir_holdings (
  id TEXT PRIMARY KEY,
  investor_id TEXT NOT NULL REFERENCES ir_investors(id),
  ticker TEXT NOT NULL,
  company_name TEXT,
  cusip TEXT,
  shares INTEGER NOT NULL,
  market_value REAL NOT NULL,
  ownership_pct REAL,
  filing_type TEXT NOT NULL,
  filing_date TEXT NOT NULL,
  period_of_report TEXT NOT NULL,
  shares_change INTEGER,
  shares_change_pct REAL,
  is_new_position INTEGER DEFAULT 0,
  is_exit INTEGER DEFAULT 0,
  investment_discretion TEXT,
  source_url TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(investor_id, cusip, filing_type, period_of_report)
);

-- ir_shareholders: Current shareholders (latest snapshot per ticker)
CREATE TABLE IF NOT EXISTS ir_shareholders (
  id TEXT PRIMARY KEY,
  ticker TEXT NOT NULL,
  investor_id TEXT REFERENCES ir_investors(id),
  investor_name TEXT NOT NULL,
  investor_type TEXT,
  shares_held INTEGER NOT NULL,
  ownership_pct REAL NOT NULL,
  market_value REAL,
  status TEXT NOT NULL,
  change_pct REAL,
  change_shares INTEGER,
  first_appeared TEXT,
  last_filing_date TEXT,
  is_activist INTEGER DEFAULT 0,
  updated_at TEXT DEFAULT (datetime('now')),
  UNIQUE(ticker, investor_name)
);

-- ir_ownership_snapshots: Historical ownership snapshots
CREATE TABLE IF NOT EXISTS ir_ownership_snapshots (
  id TEXT PRIMARY KEY,
  ticker TEXT NOT NULL,
  snapshot_date TEXT NOT NULL,
  total_shares_outstanding INTEGER,
  institutional_shares INTEGER,
  institutional_pct REAL,
  top10_shares INTEGER,
  top10_pct REAL,
  top25_pct REAL,
  data_source TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  UNIQUE(ticker, snapshot_date)
);

-- ir_contacts: Individual investor contacts
CREATE TABLE IF NOT EXISTS ir_contacts (
  id TEXT PRIMARY KEY,
  investor_id TEXT NOT NULL REFERENCES ir_investors(id),
  name TEXT NOT NULL,
  title TEXT,
  email TEXT,
  phone TEXT,
  linkedin_url TEXT,
  is_primary INTEGER DEFAULT 0,
  source TEXT,
  last_verified TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_investors_cik ON ir_investors(cik);
CREATE INDEX IF NOT EXISTS idx_investors_type ON ir_investors(type);
CREATE INDEX IF NOT EXISTS idx_investors_geography ON ir_investors(geography);
CREATE INDEX IF NOT EXISTS idx_investors_aum ON ir_investors(aum_estimate);
CREATE INDEX IF NOT EXISTS idx_holdings_investor ON ir_holdings(investor_id);
CREATE INDEX IF NOT EXISTS idx_holdings_ticker ON ir_holdings(ticker);
CREATE INDEX IF NOT EXISTS idx_holdings_cusip ON ir_holdings(cusip);
CREATE INDEX IF NOT EXISTS idx_holdings_period ON ir_holdings(period_of_report);
CREATE INDEX IF NOT EXISTS idx_shareholders_ticker ON ir_shareholders(ticker);
CREATE INDEX IF NOT EXISTS idx_contacts_investor ON ir_contacts(investor_id);
"""
