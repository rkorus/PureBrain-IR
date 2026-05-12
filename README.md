# PureBrain IR

AI-Powered Investor Intelligence Platform

PureBrain IR combines SEC regulatory filings with behavioral analytics to help fund managers, IR teams, and capital markets professionals find, score, and reach the right investors.

## Data Coverage

- **39,040** SEC-registered investment firms (27,679 IA + 11,361 ERA)
- **98,579** executive contacts
- **384,232** institutional holdings across 108 13F filers
- **20** institutional allocators (pension funds, endowments, sovereign wealth funds)
- **~$2.4 trillion** in tracked portfolio value

## Features

- **Firm Search** -- Search and filter investment advisers by geography, client type, AUM, services
- **AI Fit Score** -- 5-dimension scoring (0-100) ranking firms by alignment with your fundraise
- **Peer Analysis** -- Find investors holding your competitors but not you
- **Contact Search** -- 98K+ executive contacts with LinkedIn, email, BrokerCheck links
- **Outreach Engine** -- Context-aware email drafts with 8 templates and lifecycle tracking
- **Allocator Search** -- LP sourcing with LP Fit Score for pension funds, endowments, SWFs
- **Gatekeeper Intelligence** -- Identify pension consultants who can introduce you to allocator capital

## Tech Stack

- Python 3.10+ / FastAPI / SQLite
- Single-page frontend (HTML/CSS/JS, no build step)
- SEC EDGAR API + OpenFIGI for data enrichment

## Documentation

- [User Manual (PDF)](IR-User-Manual.pdf) -- 12-chapter comprehensive guide
- [User Manual (Markdown)](IR-User-Manual.md)
- [AI Fit Score Specification](AI_FIT_SCORE_SPEC.md)

## Quick Start

```bash
# Start the API server
cd api && uvicorn server:app --host 0.0.0.0 --port 8890

# Open in browser
open http://localhost:8890
```

## Data Pipeline

```bash
# Ingest seed filers (8 major asset managers)
python -m pipeline.ingest --seed

# Expand to 108 institutional investors
python pipeline/expand_filers.py

# Ingest 20 allocator-type filers
python api/fetch_allocators_13f.py

# Map tickers to GICS sectors
python pipeline/sector_mapper.py
```

## License

Proprietary. All rights reserved.
