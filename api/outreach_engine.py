#!/usr/bin/env python3
"""
PureBrain IR — Outreach Engine (Sprint 2C, Tasks 3.1-3.4)

Generates context-aware email drafts for investor outreach using
firm profile data, executive contacts, holdings, and fit scores.

Templates are populated with real data from:
- Firm profile (AUM, state, services, client types)
- Executive contacts (name, title, LinkedIn)
- Holdings/13F data (peer overlap, sector exposure)
- Fit score dimensions
- Disclosure status

Usage:
    from outreach_engine import generate_draft, list_templates
    draft = generate_draft("105958", "intro", target_context={...})
"""

import sqlite3
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
ADV_DB = SCRIPT_DIR / "purebrain_ir.db"
HOLDINGS_DB = SCRIPT_DIR / "holdings_13f.db"


# ── Template Library (Task 3.2) ──

TEMPLATES = {
    "intro": {
        "name": "Initial Introduction",
        "subject": "Connecting on {target_company} — Investor Opportunity",
        "body": """Dear {first_name},

I hope this message finds you well. I'm reaching out on behalf of {target_company}{sector_line} to explore a potential conversation about our upcoming {raise_type}.

{firm_context}

{holdings_context}

We believe {firm_name}'s {firm_strength} makes you an ideal partner for this opportunity. I'd welcome a brief call to share more about what we're building.

Would you have 15-20 minutes this week or next?

Best regards,
{sender_name}
{sender_title}
{target_company}""",
        "use_case": "First outreach to a new investor contact",
    },
    "warm_intro": {
        "name": "Warm Introduction (Mutual Connection)",
        "subject": "Introduction via {mutual_connection} — {target_company}",
        "body": """Dear {first_name},

{mutual_connection} suggested I reach out to you regarding {target_company}'s {raise_type}. Given {firm_name}'s {firm_strength}, they thought there could be strong alignment.

{firm_context}

{holdings_context}

I'd love to schedule a brief introductory call at your convenience. Would any time this week work?

Best regards,
{sender_name}
{sender_title}
{target_company}""",
        "use_case": "When you have a mutual connection to reference",
    },
    "follow_up": {
        "name": "Follow-Up",
        "subject": "Following up — {target_company} Opportunity",
        "body": """Dear {first_name},

I wanted to follow up on my previous note regarding {target_company}. I understand how busy things can get, so I'll keep this brief.

{firm_context}

{update_line}

If the timing isn't right at this moment, I'd still appreciate the chance to introduce {target_company} for future consideration. Would a quick call work sometime this week?

Best regards,
{sender_name}
{sender_title}
{target_company}""",
        "use_case": "Follow-up after initial outreach with no response",
    },
    "meeting_request": {
        "name": "Meeting Request",
        "subject": "Meeting Request — {target_company} {raise_type}",
        "body": """Dear {first_name},

Thank you for your interest in {target_company}. I'd like to schedule a meeting to walk you through our investment thesis and current opportunity.

{firm_context}

{meeting_details}

Please let me know what times work best for you, and I'll send a calendar invite.

Best regards,
{sender_name}
{sender_title}
{target_company}""",
        "use_case": "Requesting a formal meeting after initial interest",
    },
    "peer_overlap": {
        "name": "Peer Overlap Outreach",
        "subject": "Your portfolio peers & {target_company}",
        "body": """Dear {first_name},

I noticed that {firm_name} holds positions in {peer_names}, which are peers to {target_company} in the {target_sector} space.

{holdings_context}

{firm_context}

Given your existing exposure to this sector, I believe {target_company} could be a compelling addition. Would you have time for a brief conversation?

Best regards,
{sender_name}
{sender_title}
{target_company}""",
        "use_case": "Leveraging known peer holdings for targeted outreach",
    },
}


# ── LP Outreach Templates (Sprint 3B) ──

LP_TEMPLATES = {
    "lp_fund_intro": {
        "name": "Fund Introduction",
        "subject": "{fund_name} — Investment Opportunity in {fund_strategy}",
        "body": """Dear {contact_name},

I am writing to introduce {fund_name}, a {fund_strategy} fund targeting {fund_sectors} with a {fund_size_display} target raise.

{allocator_context}

Our investment thesis focuses on {fund_thesis}. We believe {allocator_name}'s track record of investing in {allocator_strength} positions this opportunity well within your allocation strategy.

{portfolio_overlap}

We would welcome the opportunity to present our fund to your investment committee. Would you have time for a 30-minute introductory call?

Best regards,
{sender_name}
{sender_title}
{fund_name}""",
        "use_case": "First touch to a potential LP — fund thesis and alignment",
    },
    "lp_coinvest": {
        "name": "Co-Investment Opportunity",
        "subject": "Co-Investment Opportunity — {deal_company} ({deal_round})",
        "body": """Dear {contact_name},

I am reaching out regarding a co-investment opportunity alongside {fund_name} in {deal_company}, a {deal_description}.

{allocator_context}

Deal highlights:
- Company: {deal_company}
- Round: {deal_round}
- Sector: {fund_sectors}
- Why now: {deal_rationale}

{portfolio_overlap}

Given {allocator_name}'s existing exposure to {fund_sectors}, we believe this co-investment aligns well with your portfolio strategy. We are offering select LPs the opportunity to participate directly.

I'd be happy to share the full investment memo. Would you have time this week?

Best regards,
{sender_name}
{sender_title}
{fund_name}""",
        "use_case": "Specific deal co-investment offer to an existing or prospective LP",
    },
    "lp_capital_update": {
        "name": "Capital Call / Portfolio Update",
        "subject": "{fund_name} — Portfolio Update & Upcoming Close",
        "body": """Dear {contact_name},

I wanted to share a portfolio update for {fund_name} and inform you of our upcoming close timeline.

{fund_update}

Portfolio highlights:
- Deployed capital: {deployed_amount}
- Active investments: {active_investments}
- Key milestone: {key_milestone}

{allocator_context}

Our next close is scheduled for {close_date}. We have limited remaining capacity and wanted to ensure {allocator_name} has the opportunity to participate before we finalize commitments.

Please let me know if you'd like to schedule a call to discuss the portfolio in more detail.

Best regards,
{sender_name}
{sender_title}
{fund_name}""",
        "use_case": "Portfolio update and close timeline for existing or prospective LPs",
    },
}


@dataclass
class TargetContext:
    """Context about the company seeking investors."""
    target_company: str = ""
    target_sector: str = ""
    target_tickers: list = field(default_factory=list)
    raise_type: str = "fundraise"
    raise_size: Optional[float] = None
    sender_name: str = ""
    sender_title: str = ""
    mutual_connection: str = ""
    update_line: str = ""
    meeting_details: str = ""


@dataclass
class OutreachDraft:
    """Generated email draft."""
    template_id: str
    template_name: str
    recipient_name: str
    recipient_title: str
    recipient_email: Optional[str]
    recipient_linkedin: Optional[str]
    firm_name: str
    firm_crd: str
    subject: str
    body: str
    fit_score: Optional[float] = None
    risk_flag: str = "clean"
    generated_at: str = ""
    context_used: dict = field(default_factory=dict)


def _format_aum(aum: float) -> str:
    """Format AUM for display."""
    if not aum or aum <= 0:
        return "N/A"
    if aum >= 1_000_000_000_000:
        return f"${aum / 1_000_000_000_000:.1f}T"
    if aum >= 1_000_000_000:
        return f"${aum / 1_000_000_000:.1f}B"
    if aum >= 1_000_000:
        return f"${aum / 1_000_000:.0f}M"
    return f"${aum:,.0f}"


def _get_firm_strength(firm: dict) -> str:
    """Determine the firm's key strength for messaging."""
    aum = firm.get("aum_total", 0) or 0
    if aum >= 100_000_000_000:
        return f"scale ({_format_aum(aum)} AUM) and institutional reach"
    if aum >= 10_000_000_000:
        return f"significant AUM ({_format_aum(aum)}) and market presence"
    if aum >= 1_000_000_000:
        return f"established portfolio ({_format_aum(aum)} AUM)"

    # Check client types for angle
    if firm.get("clients_pension"):
        return "pension fund expertise"
    if firm.get("clients_hnw"):
        return "high-net-worth client focus"
    if firm.get("clients_pooled"):
        return "pooled vehicle experience"
    return "investment advisory expertise"


def _build_firm_context(firm: dict, target_ctx: TargetContext) -> str:
    """Build context paragraph about the firm."""
    parts = []
    aum = firm.get("aum_total", 0) or 0
    state = firm.get("state", "")
    city = firm.get("city", "")

    location = f"{city}, {state}" if city and state else state or ""

    if aum > 0:
        parts.append(f"{firm['legal_name']} manages {_format_aum(aum)} in assets")
        if location:
            parts[-1] += f" from {location}"
        parts[-1] += "."

    # Client type context
    client_types = []
    if firm.get("clients_hnw"):
        client_types.append("high-net-worth individuals")
    if firm.get("clients_pension"):
        client_types.append("pension plans")
    if firm.get("clients_pooled"):
        client_types.append("pooled investment vehicles")
    if firm.get("clients_corporate"):
        client_types.append("corporate clients")
    if client_types:
        parts.append(f"Your firm serves {', '.join(client_types[:3])}, which aligns well with our investor profile.")

    return " ".join(parts) if parts else ""


def _build_holdings_context(crd: str, target_ctx: TargetContext) -> str:
    """Build context about holdings overlap."""
    if not target_ctx.target_tickers:
        return ""

    try:
        from peer_analysis import get_peer_overlap_score
        score = get_peer_overlap_score(crd, target_ctx.target_tickers, target_ctx.target_sector)
        if score > 0:
            return (
                f"Our analysis shows alignment between your portfolio and "
                f"{target_ctx.target_company}'s peer group in the "
                f"{target_ctx.target_sector or 'relevant'} sector."
            )
    except Exception:
        pass

    return ""


def _get_best_contact(crd: str, db_path: Path = ADV_DB) -> Optional[dict]:
    """Get the best contact for outreach (highest-ranking control person)."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    contact = conn.execute("""
        SELECT full_name, first_name, last_name, title, email_inferred, linkedin_url
        FROM contact_enrichment
        WHERE crd_number = ?
        ORDER BY
            CASE WHEN title LIKE '%CEO%' OR title LIKE '%CHIEF EXECUTIVE%' THEN 1
                 WHEN title LIKE '%PRESIDENT%' THEN 2
                 WHEN title LIKE '%MANAGING%' THEN 3
                 WHEN title LIKE '%PARTNER%' THEN 4
                 WHEN title LIKE '%DIRECTOR%' THEN 5
                 WHEN title LIKE '%CFO%' OR title LIKE '%CHIEF FINANCIAL%' THEN 6
                 ELSE 10 END,
            rowid ASC
        LIMIT 1
    """, (crd,)).fetchone()

    conn.close()
    return dict(contact) if contact else None


def _get_firm_data(crd: str, db_path: Path = ADV_DB) -> Optional[dict]:
    """Get firm profile data."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    firm = conn.execute(
        "SELECT * FROM adv_firms WHERE crd_number = ?", (crd,)
    ).fetchone()

    # Get disclosure summary
    disc = conn.execute(
        "SELECT risk_flag FROM firm_disclosure_summary WHERE crd_number = ?", (crd,)
    ).fetchone()

    conn.close()

    if not firm:
        return None

    result = dict(firm)
    result["risk_flag"] = disc["risk_flag"] if disc else "clean"
    return result


def generate_draft(
    crd_number: str,
    template_id: str = "intro",
    target_context: Optional[dict] = None,
    contact_override: Optional[dict] = None,
    db_path: Path = ADV_DB,
) -> OutreachDraft:
    """
    Generate a context-aware outreach email draft.

    Args:
        crd_number: Firm CRD number
        template_id: Template to use (intro, warm_intro, follow_up, meeting_request, peer_overlap)
        target_context: Dict with target company info (target_company, sender_name, etc.)
        contact_override: Override auto-selected contact with specific person
        db_path: Path to database

    Returns:
        OutreachDraft with populated subject and body
    """
    if template_id not in TEMPLATES:
        raise ValueError(f"Unknown template: {template_id}. Available: {list(TEMPLATES.keys())}")

    template = TEMPLATES[template_id]
    ctx = TargetContext(**(target_context or {}))

    # Get firm data
    firm = _get_firm_data(crd_number, db_path)
    if not firm:
        raise ValueError(f"Firm not found: CRD {crd_number}")

    # Get contact
    if contact_override:
        contact = contact_override
    else:
        contact = _get_best_contact(crd_number, db_path)

    if not contact:
        contact = {
            "first_name": "Investor Relations",
            "last_name": "",
            "full_name": "Investor Relations Team",
            "title": "",
            "email_inferred": None,
            "linkedin_url": None,
        }

    # Build template variables
    firm_strength = _get_firm_strength(firm)
    firm_context = _build_firm_context(firm, ctx)
    holdings_context = _build_holdings_context(crd_number, ctx)

    peer_names = ", ".join(ctx.target_tickers[:5]) if ctx.target_tickers else ""
    sector_line = f" in the {ctx.target_sector} sector" if ctx.target_sector else ""

    # Get fit score if available
    fit_score_val = None
    try:
        from fit_score import FitContext, compute_fit_score
        fit_ctx = FitContext(
            target_tickers=ctx.target_tickers,
            target_sector=ctx.target_sector,
        )
        score = compute_fit_score(crd_number, fit_ctx)
        fit_score_val = score.total_score
    except Exception:
        pass

    # Populate template
    vars_dict = {
        "first_name": contact.get("first_name", ""),
        "last_name": contact.get("last_name", ""),
        "firm_name": firm["legal_name"],
        "firm_strength": firm_strength,
        "firm_context": firm_context,
        "holdings_context": holdings_context,
        "target_company": ctx.target_company or "[Your Company]",
        "target_sector": ctx.target_sector or "",
        "sector_line": sector_line,
        "raise_type": ctx.raise_type or "fundraise",
        "sender_name": ctx.sender_name or "[Your Name]",
        "sender_title": ctx.sender_title or "[Your Title]",
        "mutual_connection": ctx.mutual_connection or "[Mutual Connection]",
        "update_line": ctx.update_line or "We've made significant progress since my last note and have some exciting updates to share.",
        "meeting_details": ctx.meeting_details or "I'm flexible on timing and happy to meet in person or via video call.",
        "peer_names": peer_names,
    }

    subject = template["subject"].format(**vars_dict)
    body = template["body"].format(**vars_dict)

    # Clean up empty lines from missing context
    body = "\n".join(line for line in body.split("\n") if line.strip() or line == "")
    # Collapse multiple blank lines
    while "\n\n\n" in body:
        body = body.replace("\n\n\n", "\n\n")

    return OutreachDraft(
        template_id=template_id,
        template_name=template["name"],
        recipient_name=contact.get("full_name", ""),
        recipient_title=contact.get("title", ""),
        recipient_email=contact.get("email_inferred"),
        recipient_linkedin=contact.get("linkedin_url"),
        firm_name=firm["legal_name"],
        firm_crd=crd_number,
        subject=subject,
        body=body,
        fit_score=fit_score_val,
        risk_flag=firm.get("risk_flag", "clean"),
        generated_at=datetime.now().isoformat(),
        context_used=vars_dict,
    )


def list_templates(include_lp: bool = True) -> list:
    """List available outreach templates."""
    result = [
        {
            "id": tid,
            "name": t["name"],
            "use_case": t["use_case"],
            "subject_preview": t["subject"],
            "type": "firm",
        }
        for tid, t in TEMPLATES.items()
    ]
    if include_lp:
        result.extend([
            {
                "id": tid,
                "name": t["name"],
                "use_case": t["use_case"],
                "subject_preview": t["subject"],
                "type": "lp",
            }
            for tid, t in LP_TEMPLATES.items()
        ])
    return result


def _format_aum_short(val: float) -> str:
    """Format dollar amounts concisely."""
    if not val or val <= 0:
        return "N/A"
    if val >= 1e12:
        return f"${val/1e12:.1f}T"
    if val >= 1e9:
        return f"${val/1e9:.1f}B"
    if val >= 1e6:
        return f"${val/1e6:.0f}M"
    return f"${val:,.0f}"


def _get_allocator_strength(inv: dict, total_value: float) -> str:
    """Describe allocator's key strength for LP messaging."""
    inv_type = inv.get("type", "")
    if inv_type == "pension":
        return f"public pension assets ({_format_aum_short(total_value)} portfolio)"
    elif inv_type == "sovereign_wealth":
        return f"sovereign capital deployment ({_format_aum_short(total_value)} portfolio)"
    elif inv_type == "endowment":
        return f"endowment alternatives allocation ({_format_aum_short(total_value)} portfolio)"
    elif inv_type == "family_office":
        return f"family office direct investments ({_format_aum_short(total_value)} portfolio)"
    return f"institutional investment ({_format_aum_short(total_value)} portfolio)"


def _build_allocator_context(inv: dict, total_value: float) -> str:
    """Build context paragraph about the allocator."""
    name = inv.get("name", "")
    inv_type = inv.get("type", "")
    country = inv.get("hq_country", "US")
    state = inv.get("hq_state", "")

    type_labels = {
        "pension": "pension fund",
        "sovereign_wealth": "sovereign wealth fund",
        "endowment": "university endowment",
        "foundation": "foundation",
        "family_office": "family office",
        "insurance": "insurance company",
    }
    type_label = type_labels.get(inv_type, "institutional investor")

    location = f"{state}, {country}" if state else country
    parts = [f"{name} is a {type_label} based in {location}"]
    if total_value > 0:
        parts[0] += f" with a {_format_aum_short(total_value)} public equity portfolio."
    else:
        parts[0] += "."

    return " ".join(parts)


def _build_portfolio_overlap(investor_id: str, target_sectors: list, holdings_db: Path = HOLDINGS_DB) -> str:
    """Build context about portfolio overlap with fund sectors."""
    try:
        conn = sqlite3.connect(str(holdings_db))
        latest = conn.execute(
            "SELECT MAX(period_of_report) FROM ir_holdings WHERE investor_id = ?",
            (investor_id,),
        ).fetchone()[0]

        if not latest:
            conn.close()
            return ""

        # Get sector overlap
        if target_sectors:
            sector_conditions = " OR ".join(
                f"LOWER(s.gics_sector) LIKE LOWER(?)" for _ in target_sectors
            )
            rows = conn.execute(f"""
                SELECT s.gics_sector, COUNT(*) as cnt, SUM(h.market_value) as val
                FROM ir_holdings h
                JOIN ir_ticker_sectors s ON UPPER(h.ticker) = UPPER(s.ticker)
                WHERE h.investor_id = ? AND h.period_of_report = ?
                AND ({sector_conditions})
                GROUP BY s.gics_sector
                ORDER BY val DESC
            """, (investor_id, latest, *[f"%{s}%" for s in target_sectors])).fetchall()

            if rows:
                total_overlap = sum(r[2] for r in rows)
                conn.close()
                return (
                    f"Your public portfolio shows {_format_aum_short(total_overlap)} "
                    f"in exposure across our target sectors, suggesting strong alignment "
                    f"with our fund's investment thesis."
                )

        conn.close()
    except Exception:
        pass
    return ""


def generate_lp_draft(
    investor_id: str,
    template_id: str = "lp_fund_intro",
    fund_context: Optional[dict] = None,
    holdings_db: Path = HOLDINGS_DB,
) -> OutreachDraft:
    """
    Generate an LP outreach email draft for an allocator.

    Args:
        investor_id: Allocator investor ID from ir_investors
        template_id: LP template to use (lp_fund_intro, lp_coinvest, lp_capital_update)
        fund_context: Dict with fund info (fund_name, fund_strategy, sender_name, etc.)
        holdings_db: Path to holdings database

    Returns:
        OutreachDraft with populated subject and body
    """
    if template_id not in LP_TEMPLATES:
        raise ValueError(f"Unknown LP template: {template_id}. Available: {list(LP_TEMPLATES.keys())}")

    template = LP_TEMPLATES[template_id]
    ctx = fund_context or {}

    # Get allocator data
    conn = sqlite3.connect(str(holdings_db))
    conn.row_factory = sqlite3.Row

    inv = conn.execute(
        "SELECT * FROM ir_investors WHERE id = ?", (investor_id,)
    ).fetchone()

    if not inv:
        conn.close()
        raise ValueError(f"Allocator not found: {investor_id}")

    inv = dict(inv)

    # Get total portfolio value
    latest = conn.execute(
        "SELECT MAX(period_of_report) FROM ir_holdings WHERE investor_id = ?",
        (investor_id,),
    ).fetchone()[0]

    total_value = 0
    if latest:
        total_value = conn.execute(
            "SELECT COALESCE(SUM(market_value), 0) FROM ir_holdings WHERE investor_id = ? AND period_of_report = ?",
            (investor_id, latest),
        ).fetchone()[0]

    conn.close()

    # Build template variables
    fund_size = ctx.get("fund_size", 0)
    target_sectors = ctx.get("target_sectors", [])

    allocator_context = _build_allocator_context(inv, total_value)
    allocator_strength = _get_allocator_strength(inv, total_value)
    portfolio_overlap = _build_portfolio_overlap(investor_id, target_sectors, holdings_db)

    vars_dict = {
        "contact_name": inv.get("primary_contact_name") or "Investment Committee",
        "allocator_name": inv.get("name", ""),
        "allocator_context": allocator_context,
        "allocator_strength": allocator_strength,
        "portfolio_overlap": portfolio_overlap,
        "fund_name": ctx.get("fund_name", "[Fund Name]"),
        "fund_strategy": ctx.get("fund_strategy", "venture capital"),
        "fund_sectors": ", ".join(target_sectors) if target_sectors else "[Target Sectors]",
        "fund_size_display": _format_aum_short(fund_size) if fund_size else "[Fund Size]",
        "fund_thesis": ctx.get("fund_thesis", "identifying high-growth opportunities in emerging technology sectors"),
        "sender_name": ctx.get("sender_name", "[Your Name]"),
        "sender_title": ctx.get("sender_title", "[Your Title]"),
        # Co-investment fields
        "deal_company": ctx.get("deal_company", "[Company Name]"),
        "deal_round": ctx.get("deal_round", "[Round]"),
        "deal_description": ctx.get("deal_description", "[company description]"),
        "deal_rationale": ctx.get("deal_rationale", "[investment rationale]"),
        # Capital update fields
        "fund_update": ctx.get("fund_update", ""),
        "deployed_amount": ctx.get("deployed_amount", "[amount]"),
        "active_investments": ctx.get("active_investments", "[count]"),
        "key_milestone": ctx.get("key_milestone", "[milestone]"),
        "close_date": ctx.get("close_date", "[date]"),
    }

    subject = template["subject"].format(**vars_dict)
    body = template["body"].format(**vars_dict)

    # Clean up empty lines
    body = "\n".join(line for line in body.split("\n") if line.strip() or line == "")
    while "\n\n\n" in body:
        body = body.replace("\n\n\n", "\n\n")

    return OutreachDraft(
        template_id=template_id,
        template_name=template["name"],
        recipient_name=inv.get("primary_contact_name") or inv.get("name", ""),
        recipient_title="Investment Committee",
        recipient_email=inv.get("primary_contact_email"),
        recipient_linkedin=None,
        firm_name=inv.get("name", ""),
        firm_crd=inv.get("cik", ""),
        subject=subject,
        body=body,
        fit_score=None,
        risk_flag="clean",
        generated_at=datetime.now().isoformat(),
        context_used=vars_dict,
    )


# ── Outreach Tracking DB (Task 3.4) ──

def _ensure_outreach_tables(conn: sqlite3.Connection):
    """Create outreach tracking tables."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS outreach_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crd_number TEXT NOT NULL,
            template_id TEXT NOT NULL,
            recipient_name TEXT,
            recipient_email TEXT,
            firm_name TEXT,
            subject TEXT,
            body TEXT,
            fit_score REAL,
            risk_flag TEXT DEFAULT 'clean',
            status TEXT DEFAULT 'draft',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            sent_at TIMESTAMP,
            opened_at TIMESTAMP,
            replied_at TIMESTAMP,
            notes TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_outreach_crd ON outreach_drafts(crd_number)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach_drafts(status)
    """)
    conn.commit()


def save_draft(draft: OutreachDraft, db_path: Path = ADV_DB) -> int:
    """Save a generated draft to the database. Returns draft ID."""
    conn = sqlite3.connect(str(db_path))
    _ensure_outreach_tables(conn)

    cursor = conn.execute("""
        INSERT INTO outreach_drafts
        (crd_number, template_id, recipient_name, recipient_email, firm_name,
         subject, body, fit_score, risk_flag, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')
    """, (
        draft.firm_crd, draft.template_id, draft.recipient_name,
        draft.recipient_email, draft.firm_name, draft.subject,
        draft.body, draft.fit_score, draft.risk_flag,
    ))
    draft_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return draft_id


def update_draft_status(draft_id: int, status: str, db_path: Path = ADV_DB):
    """Update draft status (draft, sent, opened, replied, archived)."""
    conn = sqlite3.connect(str(db_path))
    _ensure_outreach_tables(conn)

    timestamp_col = {
        "sent": "sent_at",
        "opened": "opened_at",
        "replied": "replied_at",
    }.get(status)

    if timestamp_col:
        conn.execute(f"""
            UPDATE outreach_drafts
            SET status = ?, {timestamp_col} = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, draft_id))
    else:
        conn.execute(
            "UPDATE outreach_drafts SET status = ? WHERE id = ?",
            (status, draft_id),
        )
    conn.commit()
    conn.close()


def get_outreach_history(
    crd_number: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db_path: Path = ADV_DB,
) -> list:
    """Get outreach history, optionally filtered by firm or status."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    _ensure_outreach_tables(conn)

    query = "SELECT * FROM outreach_drafts WHERE 1=1"
    params = []

    if crd_number:
        query += " AND crd_number = ?"
        params.append(crd_number)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_outreach_stats(db_path: Path = ADV_DB) -> dict:
    """Get outreach analytics summary."""
    conn = sqlite3.connect(str(db_path))
    _ensure_outreach_tables(conn)

    total = conn.execute("SELECT COUNT(*) FROM outreach_drafts").fetchone()[0]
    by_status = conn.execute("""
        SELECT status, COUNT(*) as cnt FROM outreach_drafts GROUP BY status
    """).fetchall()
    by_template = conn.execute("""
        SELECT template_id, COUNT(*) as cnt FROM outreach_drafts GROUP BY template_id
    """).fetchall()
    avg_fit = conn.execute(
        "SELECT AVG(fit_score) FROM outreach_drafts WHERE fit_score IS NOT NULL"
    ).fetchone()[0]

    conn.close()

    return {
        "total_drafts": total,
        "by_status": {r[0]: r[1] for r in by_status},
        "by_template": {r[0]: r[1] for r in by_template},
        "avg_fit_score": round(avg_fit, 1) if avg_fit else None,
    }


# ── CLI ──

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) > 1 and sys.argv[1] == "templates":
        for t in list_templates():
            print(f"  {t['id']:15s} | {t['name']:30s} | {t['use_case']}")
    elif len(sys.argv) > 1 and sys.argv[1] == "stats":
        stats = get_outreach_stats()
        print(json.dumps(stats, indent=2))
    else:
        crd = sys.argv[1] if len(sys.argv) > 1 else "105958"
        template = sys.argv[2] if len(sys.argv) > 2 else "intro"

        draft = generate_draft(crd, template, target_context={
            "target_company": "Acme Corp",
            "target_sector": "Technology",
            "target_tickers": ["AAPL", "MSFT", "NVDA"],
            "raise_type": "Series B fundraise",
            "sender_name": "Russell Korus",
            "sender_title": "CEO",
        })

        print(f"To: {draft.recipient_name} ({draft.recipient_title})")
        print(f"Email: {draft.recipient_email}")
        print(f"LinkedIn: {draft.recipient_linkedin}")
        print(f"Fit Score: {draft.fit_score}")
        print(f"Risk: {draft.risk_flag}")
        print(f"\nSubject: {draft.subject}")
        print(f"\n{'─'*60}")
        print(draft.body)
        print(f"{'─'*60}")

        # Save draft
        draft_id = save_draft(draft)
        print(f"\nDraft saved with ID: {draft_id}")
