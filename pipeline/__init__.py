# PureBrain IR - 13F/EDGAR Pipeline
# Sprint 1A: Data Ingestion
#
# Architecture:
#   EDGAR API -> XML parse -> D1 schema -> CUSIP->ticker (OpenFIGI)
#
# Modules:
#   edgar_client.py  - SEC EDGAR API client (EFTS + submissions)
#   xml_parser.py    - 13F information table XML parser
#   cusip_resolver.py - CUSIP-to-ticker resolution via OpenFIGI
#   db.py            - SQLite/D1 schema setup and data loading
#   ingest.py        - Pipeline orchestrator
