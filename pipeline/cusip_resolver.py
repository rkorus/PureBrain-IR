"""Resolve CUSIP identifiers to ticker symbols via OpenFIGI API.

OpenFIGI API: https://www.openfigi.com/api
  - Free tier: 25 requests/min, 100 identifiers per request
  - No API key required for basic usage (rate limited)
  - With API key: 250 requests/min

Request format:
  POST https://api.openfigi.com/v3/mapping
  Body: [{"idType": "ID_CUSIP", "idValue": "XXXXXXXXX"}]

Response format:
  [{"data": [{"ticker": "AAPL", "name": "APPLE INC", ...}]}]
"""

import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass


OPENFIGI_URL = "https://api.openfigi.com/v3/mapping"
BATCH_SIZE = 10  # free tier limit (with API key: 100)
MIN_INTERVAL = 6.5  # seconds between requests (free tier: 25/min)

_last_request = 0.0
_cache: dict[str, str | None] = {}  # cusip -> ticker


@dataclass
class CusipResolution:
    cusip: str
    ticker: str | None
    name: str | None
    exchange: str | None
    figi: str | None


def resolve_cusips(cusips: list[str], api_key: str | None = None) -> dict[str, CusipResolution]:
    """Resolve a list of CUSIPs to ticker symbols.

    Returns dict mapping CUSIP -> CusipResolution.
    Batches into groups of 100 per API call.
    """
    # Filter out already cached
    uncached = [c for c in cusips if c not in _cache]
    results = {}

    # Return cached results
    for cusip in cusips:
        if cusip in _cache:
            results[cusip] = CusipResolution(
                cusip=cusip, ticker=_cache[cusip],
                name=None, exchange=None, figi=None,
            )

    # Batch resolve uncached
    for i in range(0, len(uncached), BATCH_SIZE):
        batch = uncached[i:i + BATCH_SIZE]
        batch_results = _resolve_batch(batch, api_key)
        results.update(batch_results)

    return results


def _resolve_batch(cusips: list[str], api_key: str | None = None) -> dict[str, CusipResolution]:
    """Resolve a single batch of CUSIPs (max 100)."""
    global _last_request

    # Rate limit
    now = time.time()
    elapsed = now - _last_request
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    _last_request = time.time()

    # Build request
    body = [{"idType": "ID_CUSIP", "idValue": cusip} for cusip in cusips]
    data = json.dumps(body).encode()

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "PureBrainIR/1.0",
    }
    if api_key:
        headers["X-OPENFIGI-APIKEY"] = api_key

    req = urllib.request.Request(OPENFIGI_URL, data=data, headers=headers, method="POST")

    results = {}
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            response = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(10)
            return _resolve_batch(cusips, api_key)
        if e.code == 413 and len(cusips) > 1:
            # Batch too large — split in half and retry
            mid = len(cusips) // 2
            r1 = _resolve_batch(cusips[:mid], api_key)
            r2 = _resolve_batch(cusips[mid:], api_key)
            r1.update(r2)
            return r1
        # On error, return empty results
        for cusip in cusips:
            results[cusip] = CusipResolution(cusip=cusip, ticker=None, name=None, exchange=None, figi=None)
            _cache[cusip] = None
        return results

    # Parse response — response is array aligned with request array
    for i, item in enumerate(response):
        cusip = cusips[i] if i < len(cusips) else ""
        data_list = item.get("data", [])
        if data_list:
            best = data_list[0]
            ticker = best.get("ticker")
            resolution = CusipResolution(
                cusip=cusip,
                ticker=ticker,
                name=best.get("name"),
                exchange=best.get("exchCode"),
                figi=best.get("figi"),
            )
        else:
            ticker = None
            resolution = CusipResolution(cusip=cusip, ticker=None, name=None, exchange=None, figi=None)

        results[cusip] = resolution
        _cache[cusip] = ticker

    return results


def resolve_single(cusip: str, api_key: str | None = None) -> CusipResolution:
    """Resolve a single CUSIP."""
    result = resolve_cusips([cusip], api_key)
    return result.get(cusip, CusipResolution(cusip=cusip, ticker=None, name=None, exchange=None, figi=None))


def get_cache_stats() -> dict:
    """Return cache statistics."""
    total = len(_cache)
    resolved = sum(1 for v in _cache.values() if v is not None)
    return {"total": total, "resolved": resolved, "unresolved": total - resolved}
