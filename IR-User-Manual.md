# PUREBRAIN IR USER MANUAL

---

## Chapter 1: What is PureBrain IR?

---

### 1.1 Overview

PureBrain IR is an AI-powered investor intelligence platform built for fund managers, IR teams, and capital markets professionals. It combines SEC regulatory filings with behavioral analytics to help you find, score, and reach the right investors — whether you're sourcing LPs for a fund, identifying allocators for a capital raise, or building targeted outreach campaigns.

The platform searches 39,040 SEC-registered investment firms, 98,000+ executive contacts, and 384,000+ institutional holdings across 108 13F filers, including 20 allocators (pension funds, endowments, and sovereign wealth funds) representing approximately $2.4 trillion in tracked portfolio value.

### 1.2 Who Is It For?

- Fund managers seeking LP commitments from pension funds, endowments, and sovereign wealth funds
- IR teams at public companies identifying institutional investors and tracking shareholder behavior
- Capital markets professionals building investor targeting lists for fundraises, IPO roadshows, or secondary offerings
- Placement agents matching funds with allocators based on strategy alignment and check size
- Business development teams generating personalized outreach to investment decision-makers

### 1.3 What Can You Do With It?

PureBrain IR has five core modules, each accessible as a tab in the main interface:

1. Firm Search — Search and filter 39,040 investment advisers by geography, client type, AUM, services, and more. Enable AI Fit Score to rank firms by behavioral alignment with your fundraise.

2. Peer Analysis — Enter peer company tickers and find institutional investors who hold those peers but not your company. Identify high-overlap prospects based on 13F holdings data.

3. Contact Search — Search 98,000+ executive contacts across all registered firms. Access LinkedIn profiles, inferred email addresses, and BrokerCheck verification links.

4. Outreach — Generate context-aware email drafts using 5 built-in templates. Track draft lifecycle from creation through sent, opened, and replied stages.

5. Allocator Search — Search pension funds, endowments, sovereign wealth funds, and other institutional allocators. Score allocators with LP Fit Score to identify which ones match your fund's strategy, check size, and sector focus. Generate LP-specific outreach directly from allocator profiles.

In addition to the five tabs, PureBrain IR includes Gatekeeper Intelligence — a scoring engine that identifies pension consultants and adviser selection firms that can introduce you to allocator capital, accessible through the Allocator Search filters and firm profiles.

### 1.4 Data Sources

All data comes from public SEC filings — no paid data subscriptions required:

| Source | What It Provides | Coverage |
|--------|-----------------|----------|
| SEC Form ADV | Firm registrations, AUM, client types, services, geography | 27,679 Investment Advisers + 11,361 Exempt Reporting Advisers |
| SEC 13F-HR | Institutional holdings (what firms own, how much, when filed) | 108 institutional investors, 384,232 holdings |
| SEC EDGAR | Executive data, CIK cross-references, filing dates | 98,579 executives, 4,659 CRD-to-CIK mappings |
| CUSIP Resolution | Ticker symbols mapped from CUSIP identifiers | 9,151+ resolved via OpenFIGI |
| GICS Sector Mapping | Sector classification for holdings analysis | 8,110 tickers mapped to 11 sectors |
| Disclosure Data | Regulatory, criminal, and civil disclosures | 18,502 disclosures with risk flags |

### 1.5 How Is It Different?

Traditional IR platforms like Irwin (acquired by FactSet) focus on subscription-based databases with manual search. PureBrain IR is different in three ways:

1. AI Scoring — Two scoring engines (Firm Fit Score and LP Fit Score) automatically rank investors by alignment with your specific fundraise parameters, not just static filters.

2. Allocator Intelligence — Purpose-built for LP sourcing. Instead of just listing RIA firms, it identifies the pension funds, endowments, and sovereign wealth funds that allocate capital to funds — and scores them by fit.

3. Gatekeeper Mapping — Identifies pension consultants and adviser selection firms (the gatekeepers) that can introduce you to allocator capital. Scores each gatekeeper by pension client count, service breadth, AUM influence, and allocator holdings overlap.

---

## Chapter 2: Getting Started

### 2.1 — Accessing the Application

PureBrain IR is a browser-based application. No installation required.

URL: http://157.230.191.4:8890/

Browser requirements: Any modern browser — Chrome, Firefox, Safari, or Edge. The interface is optimized for desktop/laptop screens at 1024px width or wider, with mobile-responsive layout for tablets and phones.

### 2.2 — Account Creation & Login

PureBrain IR requires authentication. When you first visit the URL, you will be redirected to the login page.

**Creating an Account:**
1. On the login page, click the "Create one" link below the sign-in form.
2. On the registration page, enter:
   - **Username** — at least 3 characters, lowercase
   - **Email** — a valid email address
   - **Password** — at least 8 characters
   - **Confirm Password** — must match the password field
3. Click "Create Account."
4. On success, you will be redirected to the login page after a brief confirmation message.

**Logging In:**
1. Enter your username and password on the login page.
2. Click "Sign In."
3. On successful authentication, you are redirected to the main dashboard.

**Session Management:**
- Sessions last 7 days. You will remain logged in across browser sessions until the session expires.
- To log out, navigate to /auth/logout. This destroys your session and redirects to the login page.
- If your session expires, you will be redirected to the login page on your next visit.

**Pre-Configured Account:**
A default account is available for initial access:
- Username: `purebrain`
- Password: `declaration2026`

It is recommended to create individual accounts for each user via the registration page.

### 2.3 — First-Time Orientation

When you log in to PureBrain IR, you will see:

1. Header bar — displays "PureBrain IR" and a summary of the database: 39,040 SEC-registered firms, 108 13F filers, 384K+ institutional holdings, and Allocator Search.
2. Tab navigation — five tabs across the top of the main area, each corresponding to a core module:
   - Firm Search (default active tab)
   - Peer Analysis
   - Contact Search
   - Outreach
   - Allocator Search
3. Filter panel — each tab has its own set of filters at the top. Filters vary by tab (text search, dropdowns, toggles).
4. Results area — below the filters. Shows result cards after you run a search. Cards are interactive — click to open a detailed profile modal.
5. Pagination & export — when results are returned, a stats bar shows the total count, current page, and an "Export CSV" button.

The Firm Search tab loads by default. No data is shown until you click "Search" — this is by design, so you can set your filters first.

### 2.4 — Quick Start: Your First Search

To verify the system is working, try this:

1. On the Firm Search tab, leave all filters at their defaults.
2. Click Search.
3. You should see 39,040 results with the first 25 firms displayed, sorted by AUM (highest first).
4. Click any firm card to open its detail modal, showing firm profile, executive contacts, 13F holdings, risk disclosures, and an outreach button.

For a filtered search:
1. Set State to "CA" and AUM Range to "$1B - $10B".
2. Click Search.
3. Results narrow to California-based advisers managing between $1 billion and $10 billion.

### 2.5 — Tab Overview

| Tab | Purpose | Key Action |
|-----|---------|------------|
| Firm Search | Find SEC-registered investment advisers by name, state, AUM, client type, service, and firm type | Search → click firm → view profile/contacts/holdings |
| Peer Analysis | Find institutional investors that hold specific peer tickers (e.g., competitors in your sector) | Enter peer tickers → Find Investors → ranked by peer overlap |
| Contact Search | Search 98,000+ executive contacts by name, title, or control person status | Name search → view contact details + linked firm |
| Outreach | View and manage all outreach drafts (sent, opened, replied) | Status filter → review drafts → track engagement |
| Allocator Search | Search 20 institutional allocators — pension funds, endowments, sovereign wealth funds | Filter by type/country/AUM → view holdings → LP Fit Score → generate LP outreach |

### 2.6 — Common UI Patterns

Across all tabs, these patterns are consistent:

- Filter → Search → Results → Detail. Every tab follows this flow. Set your criteria, click the search button, browse result cards, click a card for the full profile.
- Pagination. Results display 25 per page. Use the Previous/Next buttons at the bottom to navigate. The stats bar shows "Page X of Y."
- Export CSV. Available on Firm Search and Allocator Search. Exports the current filtered result set (all pages, not just the visible page).
- Detail modals. Click any result card to open a modal overlay with the full profile. Modals include tabbed sections for different data categories. Press the X button or click outside the modal to close.
- AI Fit Score toggle. Available on Firm Search and Allocator Search. When enabled, additional context inputs appear and each result card scores each result by alignment with your fund profile.

---

## Chapter 3: Firm Search

### 3.1 — Overview

The Firm Search tab is PureBrain IR's primary discovery interface. It searches 39,040 SEC-registered investment advisory firms — 27,679 Investment Advisers (IA) and 11,361 Exempt Reporting Advisers (ERA) — sourced from SEC Form ADV filings.

Use this tab to find firms by location, size, client type, services offered, and firm type. Every firm links to a full detail profile with executive contacts, 13F holdings, disclosures, and outreach tools.

### 3.2 — Filters

The Firm Search filter panel has 7 fields plus a Search button:

| Filter | Options | What It Does |
|--------|---------|-------------|
| Search by Name | Free text | Matches against the firm's legal name. Press Enter or click Search to execute. |
| State | All 50 US states + territories | Filters by the firm's registered state (from Form ADV). |
| Firm Type | All Firms / Investment Advisers (IA) / Exempt Reporting Advisers (ERA) | IAs are fully SEC-registered. ERAs file abbreviated reports and manage only private funds. ERA firms display an orange "ERA" badge. |
| Client Type | Individual, HNW, Corporate, Pension, Pooled Vehicle, Charity, Insurance, Sovereign Wealth | Filters by the firm's reported client base. A firm serving pension clients, for example, appears when you select Pension. |
| AUM Range | Under $25M through $100B+ (7 brackets) | Filters by the firm's total Assets Under Management as reported in Form ADV. |
| Service | Financial Planning, Portfolio Mgmt (Individual), Portfolio Mgmt (Business), Pension Consulting, Adviser Selection | Filters by services the firm offers. Pension Consulting and Adviser Selection are particularly relevant for gatekeeper identification. |
| Sort By | AUM (High/Low), AI Fit Score, Name (A-Z/Z-A), Recently Filed, State | Controls the order of results. Default is AUM (High to Low). |

All filters are optional. Leaving everything at defaults and clicking Search returns all 39,040 firms sorted by AUM.

### 3.3 — Result Cards

Each result is displayed as a card showing:

- Firm name — with an orange "ERA" badge if applicable
- AUM — formatted as $M, $B, or $T (top-right of card)
- AI Fit Score badge — appears only when Fit Score is enabled (see Chapter 4)
- CRD number — the firm's Central Registration Depository identifier
- Location — city and state
- Client count — total clients (IA firms only; ERA firms do not report this)
- Entity type — corporation, LLC, partnership, etc.
- Service tags — colored pills showing the firm's reported services
- Phone number and address
- Key executives — names of top personnel displayed at the bottom of the card

Results display 25 per page with Previous/Next pagination. The stats bar above results shows the total count and current page.

### 3.4 — Exporting Results

Click Export CSV in the stats bar to download the current filtered result set. The export includes all matching firms (not just the current page). The CSV contains: firm name, CRD, state, AUM, client counts, services, phone, address, and entity type.

### 3.5 — Firm Detail Modal

Click any result card to open the full firm profile modal. The modal contains the following sections:

Header:
- Firm name, CRD number, SEC number, and CIK number (if the firm has 13F filings)
- Risk/disclosure badge (top-right) — color-coded: green (clean), yellow (noted), orange (elevated), red (high risk)

Profile Grid:
- Total AUM (highlighted), Phone, Address, Entity Type, Discretionary AUM, Non-Discretionary AUM

Client Breakdown:
- Individual counts for each client category: Individuals, HNW, Corporations, Pension Plans, Pooled Vehicles, Charities

Services Offered:
- Tags for all services the firm reports: Financial Planning, Portfolio Management (Individual/Business), Pension Consulting, Adviser Selection. Additional services tracked from Form ADV include Publications and Commodities — these are stored in the database (svc_publications, svc_commodities columns) and displayed in the detail modal when present, though they are not exposed as search filters.

Key Personnel:
- Up to 20 executive contacts loaded from SEC filings. Each contact card shows:
  - Name and title
  - Control Person badge (if applicable — indicates ownership/decision-making authority)
  - Estimated email (based on firm domain pattern)
  - LinkedIn search link and BrokerCheck link (where available)
  - Phone number

Compensation:
- Tags showing how the firm charges: % of AUM, Hourly, Fixed Fees, Commissions, Performance-based

Outreach:
- "Generate Outreach" button — opens the template selector panel (see Chapter 8)
- Template selection, draft editor, Copy/Mark Sent/Regenerate actions

Disclosure History:
- Regulatory disclosures loaded from BrokerCheck data. Shows event type, date, and description. Risk badge in the header is computed from this data.

Footer:
- Filing date, Form ADV version, link to IAPD Profile (SEC external site), and 13F Filings link (for firms with CIK mapping)

### 3.6 — Practical Examples

Find large Texas advisers:
Set State → TX, AUM Range → $1B - $10B, click Search.

Find pension consultants:
Set Service → Pension Consulting, click Search. These firms advise pension funds on manager selection — useful for identifying gatekeepers.

Find ERA fund managers in New York:
Set State → NY, Firm Type → Exempt Reporting Advisers (ERA), click Search. ERA firms typically manage private funds (hedge funds, PE, VC).

Find firms serving sovereign wealth clients:
Set Client Type → Sovereign Wealth, Sort By → AUM (High to Low), click Search. Results show advisers with sovereign wealth fund clients.

---

## Chapter 4: AI Fit Score

### 4.1 — Overview

The AI Fit Score is a 0-100 scoring system that ranks how well an investment firm aligns with your fund profile. It answers the question: "Of all these firms, which ones are the best fit for what I'm raising?"

The score is computed across 5 dimensions, each worth 0-20 points:

| Dimension | Points | What It Measures |
|-----------|--------|-----------------|
| Profile Match | 0-20 | Geography, AUM range, client type, services breadth (from Form ADV) |
| Sector Alignment | 0-20 | Portfolio exposure to your target sector + direct ticker overlap (from 13F holdings + GICS sector mapping) |
| Position Behavior | 0-20 | Concentration (conviction), turnover rate (active vs passive), check size compatibility (from multi-quarter 13F data) |
| Direct Signal | 0-20 | Does the firm already hold your target tickers? Are positions increasing? Any new positions? (from 13F) |
| Peer Overlap | 0-20 | Does the firm hold comparable companies in your sector? (from peer analysis engine) |

The score is not a prediction — it is a data-driven alignment measure based entirely on public SEC filings.

### 4.2 — Confidence Levels

Not all firms have the same data depth. The score includes a confidence indicator:

| Confidence | Meaning | Dimensions Scored |
|-----------|---------|-------------------|
| High | Firm has multi-quarter 13F data (2+ filing periods) | All 5 dimensions |
| Medium | Firm has 13F data but only 1 filing period | Profile, Sector, Signal, Peer (no Behavior — requires multi-quarter) |
| Low | Firm has no 13F data (no CIK mapping or no filings) | Profile Match only (Dimension 1) |

Of the 39,040 firms in the database, approximately 4,666 have CRD-to-CIK cross-references linking their Form ADV data to 13F holdings data. These firms receive medium or high confidence scores. The remaining firms receive low-confidence scores based on Profile Match alone.

### 4.3 — How to Use It

1. Navigate to the Firm Search tab.
2. Click the AI Fit Score toggle (below the filter panel). The toggle turns purple when active.
3. Three context inputs appear:
   - Target Tickers — comma-separated ticker symbols your fund is associated with or competing in (e.g., AAPL,MSFT,NVDA). Drives Dimensions 2, 4, and 5.
   - Target Sector — your sector (e.g., Technology, Healthcare). Drives Dimension 2 sector exposure calculation.
   - Raise Size ($) — your fundraise amount in dollars (e.g., 50000000). Drives Dimension 3 check size compatibility.
4. Set any additional filters (state, AUM range, etc.) and click Search.
5. Results now display a score badge on each card showing the total score and confidence level. Below the badge, a 5-bar breakdown shows each dimension's contribution.

### 4.4 — Score Badge Colors

The score badge on each result card is color-coded:

| Score Range | Color | Meaning |
|-------------|-------|---------|
| 50-100 | Green | Strong alignment — firm's portfolio and profile match your fund context |
| 25-49 | Yellow | Moderate alignment — partial fit, worth investigating |
| 0-24 | Red | Weak alignment — firm's profile diverges from your criteria |

### 4.5 — Sorting by Fit Score

When the AI Fit Score toggle is enabled, you can sort results by score:
- Set Sort By to "AI Fit Score (High to Low)" to surface the strongest matches first.
- This is particularly effective when combined with broad filters — for example, searching all firms nationwide and letting the score rank them by alignment.

### 4.6 — Dimension Details

Profile Match (0-20): Scores every firm using Form ADV data alone:
- Geography match (0-6): exact state match = 6, different state = 1.5, no preference = 3
- AUM range fit (0-6): in-range = 6, partial = scaled, no AUM data = 0
- Client type match (0-4): firm serves your target client type = 4, no match = 1
- Services breadth (0-4): 1 point per service offered (capped at 4)

Sector Alignment (0-20): Requires 13F data + target tickers or sector:
- Ticker overlap (0-8): percentage of your target tickers held in the firm's portfolio
- Sector exposure (0-12): percentage of portfolio value in your target GICS sector. 30%+ exposure = full 12 points, scaled linearly below that

Position Behavior (0-20): Requires multi-quarter 13F data:
- Concentration (0-8): top-10 positions as % of total portfolio. Higher concentration = higher conviction = higher score
- Turnover (0-6): new positions as % of total. Moderate turnover (5-30%) = full score; too passive or too much churn = 3
- Check size (0-6): your raise size vs the firm's median position size. Within 10x = full score

Direct Signal (0-20): Requires target tickers:
- Holds target (0-8): percentage of your target tickers the firm holds
- Increasing position (0-8): percentage of target tickers where shares are growing
- New position (0-4): bonus if the firm recently initiated a position in any target ticker

Peer Overlap (0-20): Requires target tickers:
- Sourced from the Peer Analysis engine (Chapter 7). Measures how many comparable companies the firm holds. Weighted by overlap count and portfolio significance.

### 4.7 — Gatekeeper Score (Separate)

Each firm also receives a Gatekeeper Score (0-100), computed separately from the Fit Score. The gatekeeper score identifies firms that act as intermediaries between fund managers and institutional allocators — pension consultants, adviser selection firms, and similar gatekeepers. The gatekeeper score appears as a badge on firms that qualify (score 10+). This is detailed further in Chapter 10.

---

## Chapter 5: Firm Detail Profiles

### 5.1 — Overview

When you click any firm card in the Firm Search results, a detail modal opens with the firm's complete profile. This modal aggregates data from multiple SEC sources — Form ADV registration data, 13F institutional holdings, BrokerCheck disclosure records, and executive contact information — into a single view.

Chapter 3 (Section 3.5) introduced the modal layout. This chapter explains how to interpret each section for investor relations work.

### 5.2 — Header & Identifiers

The modal header displays:
- Firm name — the legal name as registered with the SEC
- CRD number — Central Registration Depository number, the firm's unique FINRA identifier. Use this to look up the firm on FINRA BrokerCheck.
- SEC number — the firm's SEC registration file number (8-digit format, e.g., 801-12345)
- CIK number — Central Index Key, the firm's SEC EDGAR identifier. Only present if the firm files 13F reports. If a CIK is displayed, the firm has institutional holdings data available.

The risk/disclosure badge appears in the top-right corner of the header (see Section 5.7).

### 5.3 — Profile Grid

Six fields in a 3x2 grid:

| Field | Source | What It Means |
|-------|--------|--------------|
| Total AUM | Form ADV Item 5.F | Total regulatory assets under management. This is the headline number for firm size. Displayed in $M, $B, or $T format. |
| Discretionary AUM | Form ADV Item 5.F(2)(a) | Assets where the firm has authority to make buy/sell decisions without client approval. Higher discretionary % indicates more active management authority. |
| Non-Discretionary AUM | Form ADV Item 5.F(2)(b) | Assets where the firm advises but the client makes final decisions. Common in broker-dealer relationships. |
| Phone | Form ADV Item 1.J | Primary business phone number. |
| Address | Form ADV Item 1.F | Main office address (street, city, state, ZIP). |
| Entity Type | Form ADV Item 3 | Legal structure — Corporation, LLC, Limited Partnership, Sole Proprietorship, etc. Relevant for understanding firm governance. |

### 5.4 — Client Breakdown

Shows the firm's reported client counts by category:

| Client Category | Form ADV Source | Why It Matters |
|----------------|-----------------|---------------|
| Individuals | Item 5.D(1)(a) | Retail advisory clients |
| HNW Individuals | Item 5.D(1)(b) | High net worth ($750K+ investable). Indicator of wealth management focus. |
| Corporations | Item 5.D(1)(c) | Corporate treasury/pension clients |
| Pension Plans | Item 5.D(1)(d) | Manages assets for pension funds — key signal for institutional access |
| Pooled Vehicles | Item 5.D(1)(e) | Hedge funds, PE funds, mutual funds. If present, firm manages commingled vehicles. |
| Charities | Item 5.D(1)(f) | Endowments, foundations. Indicates nonprofit institutional relationships. |

A firm with pension and pooled vehicle clients is more likely to be an institutional allocator or have institutional relationships. A firm with primarily individual and HNW clients is retail-focused.

### 5.5 — Services Offered

Service tags indicate what advisory services the firm provides. The 7 tracked services are:

| Service | Significance for IR |
|---------|-------------------|
| Financial Planning | Broad advisory — may include investment selection |
| Portfolio Mgmt (Individual) | Manages individual client portfolios — potential buyer |
| Portfolio Mgmt (Business) | Manages business/institutional portfolios — stronger buyer signal |
| Pension Consulting | Advises pension funds on manager selection — gatekeeper indicator |
| Adviser Selection | Selects investment advisers for clients — gatekeeper indicator |
| Publications | Issues investment publications/newsletters |
| Commodities | Provides commodities-related advisory services |

Firms offering Pension Consulting or Adviser Selection are potential gatekeepers — they influence which funds pension plans and institutions invest in.

### 5.6 — Compensation

Shows how the firm charges clients. Tags include:
- % of AUM — most common for advisory firms; fee is a percentage of managed assets
- Hourly — consulting-style billing
- Fixed Fees — flat fee for services
- Commissions — transaction-based compensation (common for broker-dealer dual registrants)
- Performance-based — fees tied to investment returns (common in hedge funds/PE)

A firm charging performance-based fees likely manages commingled funds — relevant for identifying fund-of-fund allocators.

### 5.7 — Risk & Disclosure History

The disclosure section loads regulatory history from BrokerCheck data:

Risk Badge (top-right of modal header):
| Badge | Meaning |
|-------|---------|
| Clean Record (green) | No regulatory disclosures on file |
| Noted (yellow) | Minor disclosures — routine regulatory matters |
| Elevated (orange) | Multiple or significant disclosures — investigate before outreach |
| High Risk (red) | Serious regulatory issues — approach with caution |

Below the badge, individual disclosures are listed with event type, date, and description (up to 10 shown). The database contains 18,502 total disclosures across all firms.

### 5.8 — Footer Links

The modal footer provides:
- Filing date — when the firm last filed Form ADV
- Form version — the ADV form version used
- IAPD Profile — link to the SEC's Investment Adviser Public Disclosure page for this firm (external)
- 13F Filings — link to the firm's 13F filings on SEC EDGAR (only appears if the firm has a CIK number)

### 5.9 — Outreach from Detail Modal

The "Generate Outreach" button in the detail modal opens the outreach template panel. This is covered in Chapter 8. From the detail modal, you can select a template, generate a personalized draft populated with the firm's data, and copy or mark it as sent — all without leaving the profile view.

---

## Chapter 6: Executive Contacts

### 6.1 — Overview

PureBrain IR contains 98,579 executive contacts extracted from SEC Form ADV filings. Every executive listed on a firm's registration is searchable — from CEOs and managing partners to compliance officers and directors.

Contacts are accessible in two ways:
1. Contact Search tab — standalone search across all 98K+ executives
2. Firm Detail modal — the Key Personnel section shows executives for a specific firm

### 6.2 — Contact Search Tab

The Contact Search tab (third tab) provides a dedicated search interface for finding executives across the entire database.

Filters:

| Filter | Options | What It Does |
|--------|---------|-------------|
| Search by Name | Free text | Matches against executive names. Press Enter or click Search. |
| Title | CEO, CFO, CCO/Compliance, President, Director, Partner, Managing Director/Member | Filters by role. Useful for targeting decision-makers (CEO, President) or compliance contacts (CCO). |
| Control Persons Only | Toggle | When set, shows only control persons — individuals who own 25%+ of the firm or have authority over management decisions. These are the ultimate decision-makers. |

### 6.3 — Contact Result Cards

Each contact result card shows:
- Executive name — with a purple "CONTROL" badge if they are a control person
- Title — their role at the firm
- Firm name — the advisory firm they are registered with
- Firm AUM — displayed in the top-right corner, showing the scale of the firm
- Firm location — city and state
- Firm CRD — the firm's CRD number
- LinkedIn button — opens an inferred LinkedIn profile search (external link)
- BrokerCheck button — links to the executive's FINRA BrokerCheck page (where available)

Clicking a contact card opens the firm's full detail modal (same as clicking from Firm Search).

Results display up to 50 contacts per search.

### 6.4 — Contacts in Firm Detail Modal

When you open a firm's detail modal (from Firm Search or Contact Search), the Key Personnel section loads up to 20 executive contacts. Each contact card within the modal includes:

- Name and title
- Control Person badge — purple "CONTROL" indicator for 25%+ owners or management authority holders
- Estimated email — generated based on the firm's domain pattern (e.g., firstname.lastname@firmname.com), with a confidence label (high/medium/low)
- LinkedIn link — inferred profile search
- BrokerCheck link — FINRA regulatory profile
- Individual CRD — the executive's personal CRD number (if registered)

If the firm has more than 20 executives, a "+ N more executives" indicator appears at the bottom.

The firm's inferred domain is displayed above the contact list (e.g., "Domain: vanguard.com"). This domain is used to generate estimated email addresses.

### 6.5 — Email Estimation

PureBrain IR generates estimated email addresses for executives using the firm's inferred domain and common corporate email patterns. Each email estimate includes a confidence indicator:

| Confidence | Meaning |
|-----------|---------|
| High | Domain verified and pattern matches known firm conventions |
| Medium | Domain inferred from firm name; pattern is standard but unverified |
| Low | Best-guess based on name and firm; domain may be inaccurate |

Email estimates are intended as starting points for outreach research, not guaranteed deliverable addresses. Always verify before sending.

### 6.6 — Control Persons

Control persons are flagged based on Form ADV Schedule A/B reporting. A control person is defined as an individual who:
- Directly or indirectly owns 25% or more of the firm, OR
- Has the authority to direct management or policies of the firm

For investor relations, control persons are typically the final decision-makers on allocation commitments, manager selection, and investment strategy. Filtering by Control Persons Only in the Contact Search tab surfaces these individuals directly.

### 6.7 — Data Source & Coverage

| Metric | Value |
|--------|-------|
| Total executives | 98,579 |
| Source | SEC Form ADV (Schedule A/B — Direct Owners and Executive Officers) |
| Coverage | All SEC-registered IA and ERA firms |
| Fields | Name, title, control person status, individual CRD, firm CRD linkage |
| Enrichment | Inferred email (domain + pattern), LinkedIn search URL, BrokerCheck URL |

Contact data is updated when firm ADV filings are refreshed. Executives who leave a firm and are removed from the filing will no longer appear in search results.

### 6.8 — Practical Examples

Find all CEOs at firms managing over $10B:
1. Go to Firm Search tab, set AUM Range → $10B - $100B, click Search
2. Click any firm card to open its detail modal
3. Scroll to Key Personnel — the CEO/President will typically be the first control person listed

Find compliance officers for due diligence:
Go to Contact Search tab, set Title → CCO/Compliance, click Search. Compliance officers are key contacts for operational due diligence during LP evaluation.

Find control persons at pension consulting firms:
1. Firm Search → Service → Pension Consulting → Search
2. Open a firm → Key Personnel section
3. Look for executives with the purple CONTROL badge — these are the decision-makers who influence pension fund allocations.

---

## Chapter 7: Peer Analysis

### 7.1 — Overview

The Peer Analysis tab answers the question: "Which institutional investors hold my competitors but don't yet hold me?"

This is a prospecting tool. You provide a list of comparable companies (peer tickers), and PureBrain IR scans 108 institutional investors across 384,000+ 13F holdings to find investors who already own those peers. These investors are pre-qualified — they have demonstrated interest in your sector by allocating capital to companies like yours.

### 7.2 — How It Works

The engine uses a two-pass optimization:
- Pass 1 (Fast): SQL-based peer matching across all investors. Finds every investor holding at least one peer ticker, calculates size-weighted overlap.
- Pass 2 (Selective): Sector affinity scoring applied only to top candidates. Measures how concentrated the investor's portfolio is in your target sector.

Results are ranked by a composite score (0-20) combining three dimensions:

| Dimension | Points | What It Measures |
|-----------|--------|-----------------|
| Overlap | 0-10 | How many peer tickers the investor holds, weighted by position size. More peers held = higher score. Larger positions = higher weight. |
| Recency | 0-5 | How recent the holdings data is. Latest quarter = full weight. Older filings decay by 15% per quarter. |
| Sector Affinity | 0-5 | What percentage of the investor's portfolio is in your target sector (via GICS sector mapping). Higher concentration = stronger sector conviction. |

### 7.3 — Filters

The Peer Analysis filter panel has 6 fields:

| Filter | Options | What It Does |
|--------|---------|-------------|
| Target Ticker | Free text (optional) | Your company's ticker. When provided, investors who already hold your target can be excluded (default behavior) or included. |
| Peer Tickers | Comma-separated (required) | Comparable companies to search for (e.g., SNOW,MDB,DDOG,CRWD,NET). This is the core input — at least one peer ticker is required. |
| Target Sector | Dropdown (11 GICS sectors) | Your sector. Enables the Sector Affinity dimension. Options: Technology, Healthcare, Financials, Consumer Discretionary, Industrials, Energy, Materials, Real Estate, Utilities, Communication Services, Consumer Staples. |
| Min Peer Overlap | 1+ through 5+ | Minimum number of peer tickers an investor must hold to appear in results. Higher threshold = fewer but more relevant results. |
| Include Target Holders | Exclude (default) / Include | When set to Exclude, investors who already hold your target ticker are filtered out — showing only new prospects. Set to Include to see all holders. |
| Results Limit | Top 10 / 25 / 50 / 100 | Maximum number of results. Default is Top 50. |

### 7.4 — Result Cards

Each result is displayed as a ranked card showing:

- Rank number — position in the scored results
- Investor name — with a "HOLDS TARGET" badge if the investor already holds your target ticker
- Composite score — 0-20 score with color coding (green 14+, yellow 8-14, red below 8)
- Score bar — visual progress bar showing score as percentage of 20
- Peer ticker tags — colored pills for each peer ticker. Green = held (with position value on hover). Red with X = not held.
- Summary row — overlap count (e.g., "4/5 peers, 80%"), total positions, portfolio value, AUM, state, CRD, CIK
- 3-dimension breakdown — bar charts showing Overlap, Recency, and Sector Affinity scores

Clicking a result card opens the firm's full detail modal (if the investor has a CRD mapping).

### 7.5 — Summary Bar

Above the results, a summary bar shows:
- Total matches found
- Total investors scanned (currently 108)
- Latest filing period in the dataset
- Target ticker and peer tickers used
- Sector filter (if applied)

### 7.6 — Target Exclusion Logic

The Include/Exclude target filter is the key prospecting mechanism:

- Exclude (default): "Show me investors who hold my peers but NOT me." These are your best new prospects — they already invest in your space but haven't discovered you yet.
- Include: "Show me ALL investors in this peer group, including those who already hold me." Useful for understanding your full shareholder overlap with peers.

### 7.7 — Practical Examples

Prospect for a cybersecurity company (ticker: CRWD):
- Target Ticker: CRWD
- Peer Tickers: PANW,ZS,FTNT,S,NET
- Target Sector: Technology
- Min Overlap: 2+
- Include Target Holders: Exclude
- Results: Investors who hold 2+ cybersecurity peers but don't hold CrowdStrike — ranked by position size and sector focus.

Find who owns your competitor group:
- Leave Target Ticker blank
- Peer Tickers: SNOW,MDB,DDOG,ESTC,CFLT
- Min Overlap: 3+
- Results: Investors heavily positioned in cloud data infrastructure, ranked by overlap count and portfolio concentration.

Map your existing shareholder overlap:
- Target Ticker: PLTR
- Peer Tickers: SNOW,MDB,DDOG
- Include Target Holders: Include
- Results: All investors in this peer group, including those already holding Palantir. Compare position sizes and peer breadth.

### 7.8 — Performance

Peer analysis queries execute in approximately 0.2 seconds across the full 108-investor, 384,000+ holding universe. The two-pass optimization (SQL-based filtering followed by selective scoring) enables sub-second response even with broad peer sets.

---

## Chapter 8: Outreach

### 8.1 — Overview

The Outreach system generates context-aware email drafts for investor outreach using real firm data. Drafts are populated with information from the firm's profile, executive contacts, 13F holdings, peer overlap, and fit score — not generic templates.

The system has two components:
1. Draft generation — available from the firm detail modal (Generate Outreach button)
2. Outreach History tab — a dashboard for tracking all drafts and their status

### 8.2 — Generating a Draft

1. Open any firm's detail modal (click a result card from Firm Search, Peer Analysis, or Contact Search).
2. Scroll to the Outreach section and click Generate Outreach.
3. The template selector panel opens, showing available templates as clickable chips.
4. Select a template. Three context inputs appear:
   - Your Company Name — pre-fills the sender company in the draft
   - Sector — used for sector-specific language (e.g., "Technology")
   - Raise Type — the type of fundraise or offering (e.g., "Series B", "infrastructure fund")
5. A draft is generated via the API with the firm's real data injected:
   - First executive name and title from the firm's contacts
   - Firm AUM, location, and services
   - Holdings overlap with your target tickers (if 13F data exists)
   - Peer companies held by the firm
6. The draft appears in an editable text area with a subject line above it.
7. Actions available:
   - Copy — copies the draft to clipboard
   - Mark Sent — updates the draft status to "sent" in the tracking database
   - Regenerate — generates a new draft with the same template and context

### 8.3 — Templates

Five firm-level outreach templates are available:

| Template | Use Case | Key Data Used |
|----------|----------|--------------|
| Initial Introduction | First outreach to a new investor contact | Firm name, AUM, sector, executive name, holdings context |
| Warm Introduction | When you have a mutual connection | Mutual connection name, firm profile, holdings |
| Follow-Up | After initial outreach with no response | Previous context, update line, firm profile |
| Meeting Request | Scheduling a formal meeting after initial interest | Firm profile, meeting details placeholder |
| Peer Overlap Outreach | Leveraging known peer holdings | Peer tickers held, sector, holdings context |

Each template uses placeholders that are automatically filled with real data from the firm's SEC filings. The draft engine pulls from: firm profile (AUM, state, services, client types), executive contacts (name, title), 13F holdings (peer overlap, sector exposure), fit score dimensions, and disclosure status.

### 8.4 — Outreach History Tab

The Outreach tab (fourth tab) displays all generated drafts with status tracking and engagement metrics.

Stats Dashboard:
At the top of the tab, four stat cards show:
- Total — total number of drafts generated
- Draft — drafts not yet sent
- Sent — drafts marked as sent
- Replied — drafts that received responses

Each stat card is color-coded (purple for Total, yellow for Sent, orange for Opened, green for Replied).

Status Filter:
A dropdown lets you filter by status: All Statuses, Drafts, Sent, Opened, or Replied. A Refresh button reloads the data.

Draft Cards:
Each outreach draft is displayed as a card showing:
- Firm name — the target firm
- Template used — which template generated the draft
- Status badge — Draft / Sent / Opened / Replied
- Subject line — the generated email subject
- Draft body — the full email text (truncated in the list view)
- Created date — when the draft was generated
- Actions — status lifecycle buttons to advance the draft through stages

### 8.5 — Draft Lifecycle

Drafts move through a status pipeline:

Draft → Sent → Opened → Replied

Each transition is tracked with a timestamp. You advance a draft's status using the action buttons on each card:
- A draft starts as "Draft" when generated
- Click "Mark Sent" when you send the email (from the detail modal or history tab)
- Update to "Opened" and "Replied" as engagement occurs

This pipeline provides a lightweight CRM-style tracking system for investor outreach without requiring an external tool.

### 8.6 — LP Outreach (Allocator-Specific)

In addition to the 5 firm-level templates above, the Allocator Search tab offers 3 LP-specific outreach templates for institutional allocator outreach:

| Template | Use Case |
|----------|----------|
| Fund Introduction | First touch to a potential LP — fund thesis and alignment with the allocator's portfolio |
| Co-Investment Opportunity | Direct co-investment opportunity in a specific deal |
| Capital Call / Update | Ongoing communication with existing LPs |

LP outreach uses allocator-specific data: allocator name, type (pension/endowment/SWF), portfolio size, sector overlap, and geographic alignment. These templates are accessed from the Allocator Detail modal (Chapter 11).

### 8.7 — Practical Examples

Outreach to a firm holding your peers:
1. Run a Peer Analysis search with your peer tickers
2. Click a high-scoring result to open the firm detail
3. Click Generate Outreach → select "Peer Overlap Outreach"
4. The draft automatically references which peer tickers the firm holds

Follow up on initial contact:
1. Go to Outreach tab → filter by Status: Sent
2. Find the draft you sent previously
3. Open the firm's detail modal
4. Generate a new draft using "Follow-Up" template
5. The draft maintains context from the firm's profile

Track outreach pipeline:
Go to the Outreach tab to see all drafts across all firms. Use the status filter to focus on active conversations (Sent, Opened) or cold leads (Draft).

---

## Chapter 9: Allocator Search

### 9.1 — Overview

The Allocator Search tab (fifth tab) is purpose-built for LP sourcing. It searches 20 institutional allocators — pension funds, endowments, sovereign wealth funds, and other large-scale capital allocators — sourced from SEC 13F filings.

These are not advisory firms (those are in the Firm Search tab). These are the institutions that commit capital to funds: CalPERS, CalSTRS, Harvard Endowment, Yale Endowment, Norges Bank, CPPIB, and others. Together, they represent approximately $2.4 trillion in tracked portfolio value across 384,000+ institutional holdings.

### 9.2 — Filters

The Allocator Search filter panel has 7 fields plus a Search button:

| Filter | Options | What It Does |
|--------|---------|-------------|
| Search by Name | Free text | Matches allocator names (e.g., CalPERS, Harvard, ADIA). Press Enter or click Search. |
| Entity Type | Public Pension, Endowment, Foundation, Sovereign Wealth Fund, Family Office, Insurance Company | Filters by institutional type. Pension funds and endowments are the most common allocator categories. |
| AUM Range | $10B+, $50B+, $100B+, $500B+ | Filters by total portfolio value from 13F data. Most allocators manage tens of billions or more, though some smaller systems (e.g., Kentucky Retirement) may fall below the $10B threshold. |
| Country | All Countries, United States, Canada, Norway, Singapore, Australia, Japan, United Kingdom, South Korea, Netherlands, Switzerland, Saudi Arabia, UAE, China, Germany, Sweden | Filters by domicile. International allocators include Norges Bank (Norway), CPPIB/Ontario Teachers/PSP/BCI/CDPQ (Canada), Temasek (Singapore), and others. When a non-US country is selected, the State filter automatically hides. |
| State | US states | Filters US-based allocators by state (e.g., CA for CalPERS and CalSTRS). Only visible when Country is set to US or All. |
| Gatekeeper Filter | All Firms / Gatekeepers Only / Non-Gatekeepers Only | Filters based on gatekeeper score (see Chapter 10). |
| Sort By | AUM (Highest), Gatekeeper Score, Name (A-Z), 13F Holdings Count | Controls result ordering. Default is AUM (Highest). |

### 9.3 — Result Cards

Each allocator result card shows:
- Allocator name — with a color-coded entity type badge:
  - Blue = Public Pension
  - Green = Endowment
  - Purple = Foundation
  - Amber = Sovereign Wealth Fund
  - Teal = Family Office
  - Gray = Insurance Company
- Total portfolio value — from 13F holdings (top-right)
- Country and state — international allocators show country instead of state
- Holdings count — number of 13F positions
- CIK number — SEC EDGAR identifier
- Gatekeeper score badge — if the allocator has a gatekeeper score above 10
- LP Fit Score badge — when LP Fit Score is enabled (see Section 9.4)

### 9.4 — LP Fit Score

The LP Fit Score is a separate scoring system from the AI Fit Score (Chapter 4). While the AI Fit Score evaluates advisory firms as potential investors, the LP Fit Score evaluates institutional allocators as potential limited partners for your fund.

How to Enable:
1. Below the allocator filter panel, click the LP Fit Score toggle (turns purple when active).
2. Three fund context inputs appear:
   - Target Sectors — your fund's sector focus (e.g., Technology, AI, Infrastructure)
   - Fund Size ($) — your target fund size in dollars (e.g., 100000000)
   - Strategy Type — dropdown: Venture Capital, Growth Equity, Infrastructure, Buyout/PE, Real Assets
3. Click Search Allocators. Each result card now shows a score badge and dimension breakdown.

Scoring Model:
The LP Fit Score is 0-100 across 5 dimensions, each worth 0-20 points:

| Dimension | Points | What It Measures |
|-----------|--------|-----------------|
| Strategy Alignment | 0-20 | Does the allocator's 13F portfolio show exposure to your target sectors? Measures sector overlap (0-14) and direct ticker overlap (0-6). |
| Check Size Match | 0-20 | Is the allocator's typical position size consistent with your fund's expected LP commitment? Compares median position size to fund size. |
| Allocation Pattern | 0-20 | Does the allocator invest actively or passively? Measures the ratio of active positions vs ETF/index holdings. Active allocators score higher for growth/venture funds. Uses a set of 60+ known ETF tickers for detection. |
| Geographic Reach | 0-20 | Is the allocator in a compatible geography? US-domiciled funds receive higher scores from US allocators. International allocators receive partial credit based on cross-border investment history. |
| Gatekeeper Access | 0-20 | How accessible is this allocator through known pension consultants and adviser selection firms? Higher scores indicate more gatekeeper pathways to the allocator. |

Tier Classification:
| Score Range | Tier | Meaning |
|-------------|------|---------|
| 75-100 | Top Prospect | Strong alignment across all dimensions |
| 60-74 | Strong Prospect | Good fit, worth pursuing |
| 45-59 | Moderate Prospect | Partial alignment, investigate further |
| 25-44 | Exploratory | Weak alignment, low priority |
| Below 25 | Not Fit | No meaningful alignment with fund profile |

Example: For a Technology/Venture Capital fund raising $25M:
- CalSTRS scored 97.0 (top_prospect) — Strategy 17, Check 20, Pattern 20, Geo 20, Gate 20
- CPPIB scored 93.0 (top_prospect)
- CalPERS scored 84.1 (top_prospect)

### 9.5 — CSV Export

Click Export CSV in the stats bar to download the current allocator search results. The export includes allocator name, entity type, country, state, AUM, holdings count, CIK, and gatekeeper score.

### 9.6 — Practical Examples

Find all public pension funds:
Set Entity Type → Public Pension, click Search. Shows CalPERS, CalSTRS, and other public pension systems sorted by portfolio value.

Find international allocators:
Set Country → Canada, click Search. Shows CPPIB, Ontario Teachers, PSP, BCI, and CDPQ.

Score allocators for an infrastructure fund:
Enable LP Fit Score toggle. Set Target Sectors → Infrastructure, Fund Size → 500000000, Strategy Type → Infrastructure. Click Search. Results ranked by alignment with infrastructure allocation.

---

## Chapter 10: Gatekeeper Intelligence

### 10.1 — Overview

Gatekeepers are firms that stand between fund managers and institutional capital. They are the pension consultants, adviser selection firms, and investment consulting firms that pension funds, endowments, and sovereign wealth funds rely on to evaluate and recommend investment managers.

If you want a pension fund to allocate to your fund, you often need to go through a gatekeeper first. PureBrain IR identifies and scores these gatekeepers so you know which firms have the most influence over allocator capital.

### 10.2 — What Makes a Gatekeeper

A firm qualifies as a gatekeeper if it meets one or more of these criteria:
- Offers Pension Consulting — advises pension funds on asset allocation and manager selection
- Offers Adviser Selection — selects investment advisers for institutional clients
- Has pension fund clients — reported in Form ADV (Item 5.D)
- Manages significant AUM — indicating institutional-scale advisory relationships

These are not the allocators themselves (those are in the Allocator Search tab). These are the advisory firms that allocators hire to help choose fund managers.

### 10.3 — Gatekeeper Score (0-100)

The Gatekeeper Score evaluates how influential a firm is as a gatekeeper across 4 dimensions:

| Dimension | Points | What It Measures |
|-----------|--------|-----------------|
| Pension Client Count | 0-30 | Number of pension fund clients reported in Form ADV. 100+ clients = 30 pts, 50+ = 25, 20+ = 20, 10+ = 15, 5+ = 10, any = 5. |
| Service Breadth | 0-25 | Pension Consulting = 15 pts. Adviser Selection = 10 pts. Both = full 25. |
| AUM Influence | 0-25 | Total AUM as a proxy for institutional reach. $100B+ = 25, $10B+ = 20, $1B+ = 15, $100M+ = 10, $10M+ = 5. |
| Holdings Overlap | 0-20 | Do allocators (pension funds, endowments, SWFs) hold securities that this firm also holds? Measures CUSIP overlap with allocator portfolios. 5+ allocators sharing holdings = 20, 3+ = 15, 1+ = 10. |

### 10.4 — Tier Classification

| Score | Tier | Meaning |
|-------|------|---------|
| 70-100 | Top Gatekeeper | Dominant pension consultant or adviser selector — direct access to major allocators |
| 50-69 | Strong Gatekeeper | Significant institutional advisory practice with multiple pension clients |
| 30-49 | Moderate Gatekeeper | Advisory firm with some pension/institutional business |
| 10-29 | Minor Gatekeeper | Limited gatekeeper activity — may have small pension advisory practice |
| Below 10 | Not a Gatekeeper | No meaningful gatekeeper indicators |

### 10.5 — Where Gatekeeper Scores Appear

Gatekeeper scores are surfaced in multiple places across the application:

1. Firm Search tab — firms with a gatekeeper score of 10+ display a gatekeeper badge on their result card. The AI Fit Score also computes a separate gatekeeper score (not included in the 0-100 total fit score) visible in the scoring detail.

2. Allocator Search tab — the Gatekeeper Filter dropdown lets you filter allocator results by gatekeeper status (Gatekeepers Only / Non-Gatekeepers Only). Sort by Gatekeeper Score to rank results.

3. Firm Detail Modal — gatekeeper-related services (Pension Consulting, Adviser Selection) are highlighted in the Services Offered section.

4. LP Fit Score — Dimension 5 (Gatekeeper Access) uses the gatekeeper scoring engine to evaluate how accessible each allocator is through known gatekeeper firms.

### 10.6 — Gatekeeper Search

The gatekeeper search engine (search_gatekeepers function) provides a focused query for finding top gatekeepers:
- Filters by firms offering Pension Consulting OR Adviser Selection services
- Requires either pension clients > 0 or AUM > $1B (to exclude irrelevant firms)
- Optionally filters by state
- Returns results sorted by gatekeeper score (highest first)

In the current version, gatekeeper search is integrated into the Firm Search and Allocator Search tabs via the gatekeeper filter and sort options. A dedicated Gatekeeper Search view is available for future expansion.

### 10.7 — How Gatekeepers Connect to Allocators

The relationship chain for LP sourcing works as follows:

Fund Manager → Gatekeeper (pension consultant) → Allocator (pension fund) → Capital Commitment

PureBrain IR maps both sides of this chain:
- Allocator Search (Chapter 9) identifies the allocators and scores them by fund alignment
- Gatekeeper Intelligence (this chapter) identifies the advisory firms that can facilitate introductions to those allocators

Practical workflow:
1. Run an Allocator Search with LP Fit Score enabled to find your top prospect allocators
2. Note which allocators score highest
3. Switch to Firm Search tab, set Service → Pension Consulting or Adviser Selection
4. Find gatekeeper firms in the same state as your target allocators
5. Use the Outreach Engine (Chapter 8) to draft introductions to the gatekeeper's key personnel

### 10.8 — Example: Finding Gatekeepers for CalPERS

1. From Allocator Search, note that CalPERS is in California (CA) and is a public pension fund.
2. Switch to Firm Search tab.
3. Set State → CA, Service → Pension Consulting.
4. Click Search. Results show California-based firms that offer pension consulting.
5. Sort by AUM (High to Low) to find the largest consulting firms in CalPERS's backyard.
6. Open the top results — look for firms with high pension client counts and Adviser Selection services.
7. These are the firms most likely to have existing relationships with CalPERS and similar California pension systems.

---

## Chapter 11: Allocator Detail Profiles

### 11.1 — Overview

When you click any allocator card in the Allocator Search results, a detail modal opens with the allocator's complete institutional profile. This modal aggregates data from SEC 13F filings, GICS sector mappings, gatekeeper scoring, and LP Fit Score analysis into a single view.

Unlike the Firm Detail modal (Chapter 5), which draws primarily from Form ADV registration data, the Allocator Detail modal is built entirely from 13F institutional holdings data — showing what the allocator owns, how much, in which sectors, and across which filing periods.

### 11.2 — Header

The modal header displays:
- Allocator name — the institution's legal filing name (e.g., "CALIFORNIA STATE TEACHERS RETIREMENT SYSTEM")
- Entity type badge — color-coded by institutional category:
  - Blue = Public Pension
  - Green = Endowment
  - Purple = Foundation
  - Amber = Sovereign Wealth Fund
  - Teal = Family Office
  - Gray = Insurance Company
- Gatekeeper score badge — if the allocator has a gatekeeper score of 10 or above, a badge displays the score

### 11.3 — Profile Grid

Below the header, a 2-column grid shows the allocator's key identifiers and summary metrics:

| Field | What It Shows |
|-------|--------------|
| CIK | SEC Central Index Key — the allocator's EDGAR filing identifier. Links to their 13F filings on SEC.gov. |
| Country | Domicile country. US-based allocators show "United States." International allocators show their home country (Canada, Norway, Singapore). |
| State | US state (2-letter code). Only displayed for US-domiciled allocators. |
| Total Portfolio Value | Sum of all holdings at market value from the latest 13F filing. Formatted as $M, $B, or $T. This is the headline number — the allocator's total tracked portfolio. |
| Holdings Count | Number of individual positions in the latest 13F filing. A higher count indicates a more diversified portfolio. |
| Latest Filing Period | The most recent 13F reporting period on record (e.g., "2025-12-31" for Q4 2025). |
| Filing Date | The date the allocator submitted their latest 13F-HR filing to the SEC. |

### 11.4 — Top Holdings

The Top Holdings section displays the allocator's 20 largest positions by market value, ordered from largest to smallest. Each holding row shows:

| Column | What It Shows |
|--------|--------------|
| Ticker | The stock's ticker symbol (resolved from CUSIP via OpenFIGI). If unresolved, shows the raw CUSIP. |
| Company Name | The issuer's name as reported in the 13F filing. |
| CUSIP | The 9-character CUSIP identifier for the security. |
| Shares | Number of shares held. |
| Market Value | Total market value of the position. Formatted as $M or $B. |
| Investment Discretion | How the allocator manages the position: Sole (full discretion), Shared (shared with another manager), or None (non-discretionary). |

The top holdings reveal the allocator's largest bets. For LP sourcing, look for:
- Sector concentration — if the top 20 are dominated by one sector, the allocator has a strong sector thesis
- Position sizes — the largest positions indicate the allocator's typical check size range
- Ticker overlap — if the allocator holds companies in your sector or your specific target tickers, that is a direct alignment signal

### 11.5 — Sector Breakdown

The Sector Breakdown section aggregates the allocator's entire portfolio by GICS sector. Each row shows:

| Column | What It Shows |
|--------|--------------|
| Sector | GICS sector name (e.g., Information Technology, Healthcare, Financials) |
| Count | Number of holdings in that sector |
| Value | Total market value across all holdings in that sector. Formatted as $M, $B, or $T. |

Sectors are ordered by total value (largest first). The 11 GICS sectors tracked are: Information Technology, Healthcare, Financials, Consumer Discretionary, Industrials, Energy, Materials, Real Estate, Utilities, Communication Services, and Consumer Staples.

The sector breakdown is particularly important for LP Fit Score Dimension 1 (Strategy Alignment). If your fund focuses on Technology and the allocator has 30%+ of their portfolio in the Technology sector, that is a strong alignment signal — and the LP Fit Score engine detects this automatically.

### 11.6 — Filing History

The Filing History section shows all 13F filing periods on record for the allocator, in reverse chronological order (most recent first). Each row shows:

| Column | What It Shows |
|--------|--------------|
| Period | The 13F reporting period (e.g., Q4 2025, Q3 2025) |
| Holdings Count | Number of positions reported in that period |
| Total Value | Aggregate portfolio value for that period. Formatted as $M, $B, or $T. |

Filing history reveals portfolio trends over time:
- Growing total value indicates an allocator that is deploying more capital
- Increasing holdings count may indicate a shift toward diversification
- Declining totals may signal redemptions, rebalancing, or market drawdowns

The database currently tracks up to 2 filing periods per allocator (typically Q3 and Q4 2025). As more quarters are ingested, filing history will expand to show longer-term trends.

### 11.7 — LP Fit Score in Detail Modal

When the LP Fit Score toggle is enabled on the Allocator Search tab (see Chapter 9, Section 9.4), the detail modal displays the allocator's full score breakdown:

Score Header:
- Total score (0-100) with tier classification (Top Prospect, Strong Prospect, Moderate Prospect, Exploratory, Not Fit)
- Confidence level (High, Medium, or Low) based on data availability

5-Dimension Breakdown:
Each dimension shows a labeled score bar (0-20) with a visual progress indicator:

| Dimension | What the Detail Shows |
|-----------|----------------------|
| Strategy Alignment (0-20) | Sector exposure percentage in your target sectors + ticker overlap count. Detail includes the exact % of portfolio in your sector and which target tickers the allocator holds. |
| Check Size Match (0-20) | Comparison of your fund size against the allocator's median position size, 25th percentile, and 75th percentile. A perfect fit means your expected LP commitment falls within the allocator's typical position range. |
| Allocation Pattern (0-20) | Active vs. passive split — percentage of portfolio in individual stocks vs. ETFs/index funds. Also shows portfolio concentration (top-10 holdings as % of total). Active allocators with moderate concentration score highest for growth/venture funds. |
| Geographic Reach (0-20) | Country match between your fund's domicile and the allocator's headquarters. Also considers entity type — pension funds and sovereign wealth funds receive higher geographic scores due to broader mandate reach. |
| Gatekeeper Access (0-20) | Number of known pension consultants and adviser selection firms whose holdings overlap with this allocator's portfolio. More gatekeeper pathways = easier access. Lists the top overlapping gatekeeper firms. |

### 11.8 — LP Outreach from Detail Modal

The "Generate LP Outreach" button in the allocator detail modal opens the LP outreach template panel. This is separate from the firm-level outreach system (Chapter 8) — it uses allocator-specific templates designed for LP fundraising.

Three LP outreach templates are available:

| Template | Use Case | Key Data Injected |
|----------|----------|------------------|
| Fund Introduction | First outreach to a potential LP. Presents your fund thesis and alignment with the allocator's portfolio. | Allocator name, entity type, location, portfolio value, sector overlap context, fund strategy |
| Co-Investment Opportunity | Direct deal invitation. Presents a specific co-investment alongside the fund commitment ask. | Deal company, round, sector, rationale, allocator portfolio context |
| Capital Call / Portfolio Update | Ongoing communication with existing or engaged LPs. Shares fund progress and upcoming close. | Fund update, deployed amount, active investments, key milestones, close date |

How to generate an LP draft:
1. Open an allocator's detail modal by clicking their result card
2. Click "Generate LP Outreach"
3. Select a template from the chip selector
4. Enter context fields:
   - Fund Name — your fund's name
   - Fund Strategy — brief strategy description (e.g., "AI infrastructure venture")
   - Additional context fields vary by template (deal company for co-invest, fund update text for capital call)
5. A draft generates with a subject line and body, both populated with real allocator data
6. Actions: Copy (to clipboard), Mark Sent (tracks in outreach history), Regenerate (new draft)

LP outreach drafts appear in the Outreach History tab (Chapter 8, Section 8.4) alongside firm-level drafts, but are labeled with the LP template name for easy filtering.

### 11.9 — Interpreting Allocator Profiles for LP Sourcing

The allocator detail modal provides the data needed to assess LP fit before outreach. Here is a practical framework:

Step 1 — Check portfolio scale:
Look at Total Portfolio Value and Holdings Count. Allocators managing $50B+ with 500+ holdings are large diversified institutions — they typically write larger checks but move slowly. Allocators managing $10-50B may be more accessible for emerging managers.

Step 2 — Review sector alignment:
Check the Sector Breakdown. If your fund focuses on Technology and the allocator has 25%+ in Information Technology, there is strong sector alignment. If their portfolio is concentrated in Financials or Energy with minimal tech exposure, the fit is weaker.

Step 3 — Examine top holdings:
Scan the Top 20 Holdings for companies in your sector or your specific target tickers. Direct overlap is the strongest signal — the allocator is already investing in your space.

Step 4 — Assess position sizing:
Look at the market value range in the top holdings. If the allocator's median position is $500M and your fund is raising $25M, the commitment ask is within range. If median positions are $5B+, a $25M fund may be below their threshold — though gatekeeper introductions can help.

Step 5 — Check LP Fit Score:
If enabled, the 5-dimension breakdown provides a quantitative summary of all the above factors. Focus on which dimensions scored highest and lowest to identify talking points and potential objections for your outreach.

### 11.10 — Practical Examples

Evaluate CalSTRS as an LP prospect:
1. Search for "CalSTRS" in Allocator Search
2. Click the result card to open the detail modal
3. Review: Public Pension, California, $300B+ portfolio, 3,000+ holdings
4. Check Sector Breakdown — if Technology is 25%+ of their portfolio, strong fit for a tech fund
5. Check Top Holdings for your target tickers or sector peers
6. Enable LP Fit Score with your fund parameters to see the quantitative alignment
7. Click Generate LP Outreach → Fund Introduction → generate a draft referencing their tech exposure

Compare two allocators side-by-side:
1. Open the first allocator's detail modal, note their sector breakdown and LP Fit Score
2. Close the modal, open the second allocator
3. Compare: Which has higher sector exposure to your target? Which has position sizes closer to your commitment ask? Which has more gatekeeper access pathways?
4. Prioritize outreach to the allocator with stronger alignment across all 5 dimensions

Find allocators with direct ticker overlap:
1. Enable LP Fit Score with your target tickers entered
2. Sort by LP Fit Score (High to Low)
3. Open the top-scored allocators
4. In Top Holdings, look for your specific target tickers — these allocators are already investing in companies like yours
5. Reference the specific overlapping tickers in your LP outreach for maximum relevance

---

## Chapter 12: Data Pipeline & Architecture

### 12.1 — Overview

PureBrain IR is built on three layers: a data pipeline that ingests and enriches SEC filings, a REST API that serves queries and computes scores, and a single-page frontend that renders the interface. All three layers run on a single server at port 8890, with no external dependencies beyond the SEC EDGAR API and OpenFIGI CUSIP resolution service.

This chapter describes the system architecture, data sources, database schema, API surface, and pipeline operations — intended for technical users, administrators, and developers extending the platform.

### 12.2 — Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| Web Framework | FastAPI |
| Database | SQLite 3 (WAL mode, foreign keys enabled) |
| Frontend | Single-page HTML/CSS/JavaScript (108 KB, no build step) |
| Server | Uvicorn (ASGI) |
| External APIs | SEC EDGAR (10 req/sec), OpenFIGI (25 req/min free tier) |
| Hosting | DigitalOcean droplet at 157.230.191.4:8890 |
| CORS | All origins allowed (credentials enabled) |
| Authentication | Cookie-based session auth with bcrypt password hashing |

### 12.3 — Data Sources

All data comes from public SEC filings. No paid subscriptions or proprietary data feeds are used.

| Source | API / URL | What It Provides | Rate Limit |
|--------|-----------|-----------------|------------|
| SEC FOIA Form ADV | Bulk CSV download | All registered investment advisers — firm profiles, AUM, services, client types, executives, disclosures. Source for all 39,040 firms, 98,579 executives, and 18,502 disclosures. | Bulk download |
| SEC EDGAR Submissions | data.sec.gov/submissions/CIK{cik}.json | Company filing indexes, SIC codes, CIK lookups | 10 req/sec (User-Agent required) |
| SEC 13F-HR Filings | sec.gov/Archives/edgar/data/{cik}/{accession}/ | Institutional holdings XML (information tables) | 10 req/sec |
| SEC EDGAR Full-Text Search | efts.sec.gov/LATEST/search-index | Filing search by form type | 10 req/sec |
| OpenFIGI | api.openfigi.com/v3/mapping | CUSIP → ticker/name/exchange resolution | Free: 25 req/min (10 CUSIPs/batch) |
| SEC Company Tickers | sec.gov/files/company_tickers.json | Full ticker → CIK mapping | Static file |

### 12.4 — Database Schema

PureBrain IR uses two SQLite database files:

**Database 1: ADV Firms (purebrain_ir.db in api/, 55 MB)**

| Table | Records | Contents |
|-------|---------|----------|
| adv_firms | 27,679 | SEC-registered Investment Advisers. Fields: CRD, legal name, DBA, SEC number, address, phone, AUM (total/discretionary/non-discretionary), client counts by category (8 types), services offered (7 boolean flags), entity type, filing date. |
| era_firms | 11,361 | Exempt Reporting Advisers. Same schema as adv_firms. ERA firms file abbreviated Form ADV and manage only private funds. |
| firm_executives | 98,579 | Executive contacts from Form ADV Schedule A/B. Fields: name, title, CRD, control person flag, linked firm CRD. |
| firm_disclosures | 18,502 | Regulatory, criminal, and civil disclosures from BrokerCheck. Fields: firm CRD, event type, date, description, risk level. |
| outreach_drafts | variable | Generated email drafts with lifecycle tracking. Fields: firm CRD, template, subject, body, status (draft/sent/opened/replied), timestamps. |
| ir_users | variable | User accounts. Fields: id, username (UNIQUE), email (UNIQUE), password_hash (bcrypt), created_at. |
| ir_sessions | variable | Active sessions. Fields: session_id, user_id, username, created_at, expires_at. Sessions expire after 7 days. |

**Database 2: 13F Holdings (purebrain_ir.db in pipeline root, symlinked as holdings_13f.db)**

| Table | Records | Contents |
|-------|---------|----------|
| ir_investors | 108 | Institutional 13F filers. Fields: id, name, type, CIK, AUM estimate, headquarters (country/state/city), entity metadata. Includes 20 allocator-type investors (pension, endowment, SWF). |
| ir_holdings | 384,232 | Individual holding positions from 13F-HR filings. Fields: investor_id, ticker, company_name, CUSIP, shares, market_value, investment_discretion, filing_date, period_of_report, shares_change, is_new_position, is_exit. Unique on (investor_id, cusip, filing_type, period_of_report). |
| ir_ticker_sectors | 8,110 | Ticker → GICS sector mapping. Fields: ticker, SIC code, SIC description, GICS sector, source. Built from SEC EDGAR SIC codes with manual overrides. |

**Cross-Reference: CRD-to-CIK Mapping**

4,659 advisory firms have both a CRD number (Form ADV) and a CIK number (EDGAR/13F), linking their registration data to their institutional holdings data. This linkage enables the AI Fit Score to combine Form ADV profile data with 13F behavioral data for the same firm.

### 12.5 — Pipeline Modules

The data pipeline lives at `data/purebrain-ir/pipeline/` and consists of 7 modules:

**edgar_client.py — SEC EDGAR API Client**
- Rate-limited to 10 requests/second (100ms minimum between requests)
- Fetches company submission indexes, locates 13F-HR filings, resolves information table URLs, downloads XML
- Includes 8 seed filers: Vanguard, BlackRock, Berkshire Hathaway, State Street, JPMorgan, Renaissance Technologies, Morgan Stanley, Goldman Sachs

**xml_parser.py — 13F Information Table Parser**
- Parses SEC 13F-HR XML into structured holding records
- Handles both namespaced and non-namespaced XML variants (SEC schema has changed over time)
- Extracts 10 fields per holding: issuer name, title of class, CUSIP, value (thousands), shares, share type, investment discretion, voting authority (sole/shared/none)

**cusip_resolver.py — CUSIP → Ticker Resolution**
- Calls OpenFIGI API to resolve 9-character CUSIPs to ticker symbols
- Batches 10 CUSIPs per API call, rate-limited to 25 requests/minute on free tier
- Maintains in-memory cache; pre-resolved mappings stored in cusip_ticker_cache.json (9,151+ entries)
- Returns ticker, company name, exchange, and FIGI identifier

**db.py — Database Schema and CRUD**
- Defines all table schemas with CREATE TABLE IF NOT EXISTS
- Provides upsert functions for investors and bulk insert for holdings (with duplicate skipping)
- Indexes on investor_id, ticker, cusip, period_of_report for query performance

**ingest.py — Main Pipeline Orchestrator**
- CLI entry point with modes: --seed (8 filers), --cik (specific filer), --stats (database summary), --spike (test parse)
- 7-step flow per filer: fetch submissions → extract 13F filings → resolve info table URL → download XML → parse holdings → resolve CUSIPs → upsert to SQLite
- Default: ingests 2 most recent filings per filer (configurable via --max-filings)

**sector_mapper.py — SIC → GICS Sector Mapping**
- Downloads SEC company_tickers.json for the full ticker → CIK map
- Queries EDGAR for each company's SIC code (cached in sic_cache.json for resumability)
- Maps SIC codes to 11 GICS sectors using 209 range-based mappings + 69 precise overrides
- Result: 8,110 tickers mapped at 95.4% coverage

**expand_filers.py — Coverage Expansion**
- Contains EXPANSION_FILERS dictionary with 108 institutional investor CIKs
- Includes asset managers, banks, hedge funds, activist investors, PE firms, pension funds, endowments, sovereign wealth funds, and international filers
- Fast ingestion mode uses pre-cached CUSIP mappings to avoid OpenFIGI rate limits

### 12.6 — API Endpoints

The API server (server.py) exposes the following endpoints via FastAPI at port 8890.

The api/ directory also contains **fetch_allocators_13f.py** — a specialized ingestion script for 20 allocator-type investors (CalPERS, CalSTRS, Harvard, Yale, Norges Bank, CPPIB, etc.). It sets entity type (pension/endowment/sovereign_wealth) and country/state metadata. Produced 43,073 allocator holdings with 5,959 tickers backfilled.

**Authentication**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /login | GET | Login page |
| /register | GET | Registration page |
| /auth/login | POST | Authenticate user (JSON: username, password) |
| /auth/register | POST | Create new account (JSON: username, email, password) |
| /auth/logout | GET | Destroy session and redirect to login |

All /api/* endpoints below require a valid session cookie (`pbir_session`). Unauthenticated requests return 401.

**Firm Search**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/search/firms | GET | Search 39,040 firms with 10 filter parameters |
| /api/search/export | GET | Export filtered firm results to CSV |
| /api/firms/{crd} | GET | Full firm profile with executives, holdings, disclosures |
| /api/firms/{crd}/contacts | GET | Enriched executive contact details |
| /api/firms/{crd}/disclosures | GET | Detailed disclosure history |
| /api/search/options | GET | Filter dropdown values (states, client types, services, AUM ranges) |

**Peer Analysis**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/peer-analysis | GET | Find investors holding peer tickers with composite scoring |

**Allocator Search**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/search/allocators | GET | Search 20 allocators with LP Fit Score |
| /api/search/allocators/export | GET | Export allocator results to CSV |
| /api/allocators/{id} | GET | Full allocator profile with top 20 holdings, sector breakdown, filing history |
| /api/search/allocators/options | GET | Filter dropdown values for allocator search |

**Scoring**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/fit-score/{crd} | GET | Compute 5-dimension AI Fit Score for a firm |
| /api/allocators/{id}/fit-score | GET | Compute LP Fit Score for an allocator |
| /api/gatekeepers | GET | List top gatekeeper firms ranked by score |
| /api/gatekeepers/{crd} | GET | Gatekeeper score for a specific firm |

**Outreach**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| POST /api/outreach/draft | POST | Generate email draft from template with firm data |
| POST /api/outreach/lp-draft | POST | Generate LP outreach draft with allocator data |
| GET /api/outreach/templates | GET | List available email templates (5 firm + 3 LP) |
| GET /api/outreach/history | GET | Retrieve all outreach drafts with status |
| GET /api/outreach/stats | GET | Outreach pipeline statistics (total/draft/sent/replied) |
| POST /api/outreach/{id}/status | POST | Update draft status (draft → sent → opened → replied) |

**System**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| GET /api/stats | GET | Database statistics (firm counts, holdings totals) |
| GET / | GET | Serve the frontend (index.html) — requires authenticated session |

### 12.7 — Scoring Algorithms

PureBrain IR has three independent scoring engines:

**AI Fit Score (0-100) — fit_score.py**
Evaluates advisory firms as potential investors. 5 dimensions × 20 points. Requires: target tickers, target sector, raise size. Confidence levels: High (multi-quarter 13F), Medium (single-quarter 13F), Low (no 13F — Profile Match only). See Chapter 4 for full scoring rules.

**LP Fit Score (0-100) — allocator_fit_score.py**
Evaluates institutional allocators as potential LPs. 5 dimensions × 20 points. Requires: target sectors, fund size, strategy type. Tier classification: Top Prospect (75+), Strong (60-74), Moderate (45-59), Exploratory (25-44), Not Fit (<25). See Chapter 9 for full scoring rules.

**Gatekeeper Score (0-100) — gatekeeper.py**
Evaluates advisory firms as institutional gatekeepers. 4 dimensions: Pension Client Count (0-30), Service Breadth (0-25), AUM Influence (0-25), Holdings Overlap (0-20). Tier classification: Top (70+), Strong (50-69), Moderate (30-49), Minor (10-29), Not a Gatekeeper (<10). See Chapter 10 for full scoring rules.

### 12.8 — Frontend Architecture

The frontend is a single HTML file (index.html, 108 KB) served as a static file at the root URL. It contains all CSS, JavaScript, and markup in one file — no build step, no framework dependencies, no npm packages.

The frontend communicates with the API via fetch() calls to /api/* endpoints on the same origin (port 8890), eliminating CORS issues. All rendering is done client-side: the API returns JSON, and JavaScript builds the DOM dynamically.

The 5-tab interface (Firm Search, Peer Analysis, Contact Search, Outreach, Allocator Search) is implemented as a tab panel system where each tab has its own filter panel, result area, and detail modal rendering logic.

### 12.9 — File Layout

```
data/purebrain-ir/
├── purebrain_ir.db              # 13F holdings database (ir_investors, ir_holdings, ir_ticker_sectors)
├── cusip_ticker_cache.json      # Pre-resolved CUSIP → ticker mappings (9,151+ entries)
├── sic_cache.json               # SEC SIC code cache (resumable)
├── IR-User-Manual.md            # This manual
├── AI_FIT_SCORE_SPEC.md         # Fit Score algorithm specification
│
├── pipeline/                    # Data ingestion modules
│   ├── edgar_client.py          # SEC EDGAR API client
│   ├── xml_parser.py            # 13F XML parser
│   ├── cusip_resolver.py        # CUSIP → ticker via OpenFIGI
│   ├── db.py                    # SQLite schema and CRUD
│   ├── ingest.py                # Main pipeline orchestrator
│   ├── sector_mapper.py         # SIC → GICS sector mapping
│   └── expand_filers.py         # 108-filer coverage expansion
│
└── api/                         # API server and scoring
    ├── server.py                # FastAPI application (port 8890)
    ├── auth.py                  # Authentication module (bcrypt, sessions, user management)
    ├── search_api.py            # Firm search logic (UNION IA + ERA)
    ├── allocator_api.py         # Allocator search and detail
    ├── fit_score.py             # 5-dimension AI Fit Score
    ├── allocator_fit_score.py   # 5-dimension LP Fit Score
    ├── peer_analysis.py         # Peer-based investor targeting
    ├── gatekeeper.py            # Gatekeeper score computation
    ├── outreach_engine.py       # Email templates and draft management
    ├── contact_enrichment.py    # Executive contact enrichment
    ├── fetch_allocators_13f.py  # 20 allocator ingestion
    ├── purebrain_ir.db          # Database (firms, executives, disclosures, users, sessions)
    ├── holdings_13f.db          # Symlink → ../purebrain_ir.db
    └── static/
        ├── index.html           # Single-page frontend (108 KB)
        ├── login.html           # Login page
        └── register.html        # Registration page
```

### 12.10 — Data Pipeline Operations

**Ingest seed filers (8 major asset managers):**
```
python -m pipeline.ingest --seed --max-filings 2
```

**Ingest a specific filer by CIK:**
```
python -m pipeline.ingest --cik 102909
```

**Expand to 108 institutional investors:**
```
python pipeline/expand_filers.py
```

**Ingest 20 allocator-type filers:**
```
python pipeline/fetch_allocators_13f.py
```

**Map tickers to GICS sectors:**
```
python pipeline/sector_mapper.py
```

**Check database statistics:**
```
python -m pipeline.ingest --stats
```

**Start the API server:**
```
cd data/purebrain-ir/api && uvicorn server:app --host 0.0.0.0 --port 8890
```

### 12.11 — Data Coverage Summary

| Category | Count | Source |
|----------|-------|--------|
| Investment Advisers (IA) | 27,679 | SEC Form ADV |
| Exempt Reporting Advisers (ERA) | 11,361 | SEC Form ADV |
| Total Searchable Firms | 39,040 | ADV + ERA |
| Executive Contacts | 98,579 | Form ADV Schedule A/B |
| Regulatory Disclosures | 18,502 | BrokerCheck |
| Institutional 13F Filers | 108 | SEC EDGAR |
| 13F Holdings Records | 384,232 | 13F-HR Filings |
| Allocator Investors | 20 | Pension/Endowment/SWF subset |
| Unique CUSIPs Resolved | 9,151+ | OpenFIGI |
| Tickers with GICS Sector | 8,110 | SIC → GICS mapping |
| CRD-to-CIK Cross-References | 4,659 | EDGAR/IAPD linkage |
| Tracked Portfolio Value | ~$2.4 trillion | Sum of allocator holdings |

### 12.12 — Data Freshness

All data is sourced from SEC filings at the time of pipeline ingestion. The data is not live-streaming — it reflects the state of filings when the pipeline last ran.

- **Form ADV data** (firms, executives, disclosures): Updated when the ADV ingestion pipeline is re-run. Firms file ADV amendments throughout the year; annual updates capture the majority of changes.
- **13F holdings data**: Filed quarterly (within 45 days of quarter-end). To capture the latest quarter, re-run the pipeline after the SEC filing deadline (typically mid-February, May, August, November).
- **CUSIP → ticker mappings**: Cached in cusip_ticker_cache.json. New CUSIPs from fresh filings are resolved on the next pipeline run.
- **Sector mappings**: Updated by re-running sector_mapper.py after new tickers enter the holdings database.

To refresh all data: re-run the pipeline modules in order (ingest → expand → allocators → sectors), then restart the API server to pick up the updated database files.
