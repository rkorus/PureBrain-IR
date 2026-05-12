# AI Fit Score Algorithm Specification

**Author**: Parallax (Sprint 1B deliverable)
**Status**: Ready for implementation
**Implementor**: Keel (search API owner)

---

## 1. Purpose

The AI Fit Score answers: **"How likely is this investor to be interested in MY company?"**

Form ADV tells you what a firm *says* it does. 13F tells you what it *actually* does. The Fit Score bridges the gap by combining profile data (who they claim to be) with behavioral data (how they actually invest).

## 2. Score Structure

**Total: 0-100 points across 4 dimensions.**

Each dimension scores 0-25. The total score maps to tiers:

| Score | Tier | Label |
|-------|------|-------|
| 80-100 | A | Strong Fit |
| 60-79 | B | Good Fit |
| 40-59 | C | Possible Fit |
| 20-39 | D | Weak Fit |
| 0-19 | F | Poor Fit |

## 3. Inputs

The algorithm takes a **search context** — what the user is looking for:

```json
{
  "target_sectors": ["Technology", "AI/ML"],
  "target_aum_min": 100000000,
  "target_aum_max": 10000000000,
  "target_geography": "US",
  "target_state": "TX",
  "target_check_size": 5000000,
  "target_investor_types": ["Individuals", "Pooled Investment Vehicles"],
  "target_tickers": ["NVDA", "MSFT", "GOOGL"]
}
```

All fields optional. More specificity = better scoring precision.

## 4. Dimension 1: Profile Match (0-25 pts)

**Data source**: Form ADV (ir_investors table)
**Available for**: All 39,040 firms

This dimension uses declared profile data. Every firm gets this score.

### Sub-scores:

**4a. AUM Range Match (0-8 pts)**
- If firm AUM falls within `[target_aum_min, target_aum_max]`: 8 pts
- If firm AUM is within 2x of range boundary: 4 pts
- If firm AUM is outside 2x: 0 pts
- If AUM unknown: 3 pts (neutral)

**4b. Geography Match (0-7 pts)**
- Exact state match: 7 pts
- Same region (e.g., South, Northeast): 4 pts
- Same country: 2 pts
- Different country or unknown: 0 pts

**4c. Client Type Match (0-5 pts)**
- `client_types` field contains any value from `target_investor_types`: 5 pts
- Partial overlap (at least one match): 3 pts
- No match or unknown: 0 pts

**4d. Style/Compensation Match (0-5 pts)**
- `compensation_type` includes performance fees (signals active management): 3 pts
- `investment_style` aligns with target context: 2 pts
- If either field empty: 1 pt (neutral)

### SQL approach:
```sql
SELECT
  i.id,
  -- AUM score
  CASE
    WHEN i.aum_estimate BETWEEN :aum_min AND :aum_max THEN 8
    WHEN i.aum_estimate BETWEEN :aum_min/2 AND :aum_max*2 THEN 4
    WHEN i.aum_estimate IS NULL THEN 3
    ELSE 0
  END as aum_score,
  -- Geography score
  CASE
    WHEN i.hq_state = :target_state THEN 7
    WHEN i.hq_state IN (:same_region_states) THEN 4
    WHEN i.hq_country = :target_country THEN 2
    ELSE 0
  END as geo_score
  -- ... etc
FROM ir_investors i
```

## 5. Dimension 2: Sector Alignment (0-25 pts)

**Data source**: 13F holdings (ir_holdings table) + ticker-to-sector mapping
**Available for**: Firms with 13F data (currently 8 seed filers, expandable to 4,659 via CRD-to-CIK)

This dimension measures **actual portfolio exposure** to the target sector.

### Prerequisites:
- **Ticker-to-sector mapping table** (`ir_ticker_sectors`): Maps tickers to GICS sectors/sub-industries. Source: bulk download from SEC SIC codes or free tier financial APIs. ~5,000 tickers from our resolved CUSIPs.

### Sub-scores:

**5a. Current Sector Exposure (0-15 pts)**
```sql
-- For each firm, compute: (market_value in target sector) / (total market_value)
SELECT
  h.investor_id,
  SUM(CASE WHEN ts.sector IN (:target_sectors) THEN h.market_value ELSE 0 END) * 1.0
    / NULLIF(SUM(h.market_value), 0) as sector_pct
FROM ir_holdings h
JOIN ir_ticker_sectors ts ON h.ticker = ts.ticker
WHERE h.period_of_report = :latest_period
GROUP BY h.investor_id
```
- sector_pct >= 20%: 15 pts
- sector_pct >= 10%: 12 pts
- sector_pct >= 5%: 8 pts
- sector_pct >= 1%: 4 pts
- sector_pct > 0: 2 pts
- No exposure: 0 pts

**5b. Sector Trend (0-10 pts)** — Is exposure growing?
```sql
-- Compare latest quarter to previous quarter
WITH quarterly AS (
  SELECT
    h.investor_id,
    h.period_of_report,
    SUM(CASE WHEN ts.sector IN (:target_sectors) THEN h.market_value ELSE 0 END) * 1.0
      / NULLIF(SUM(h.market_value), 0) as sector_pct
  FROM ir_holdings h
  JOIN ir_ticker_sectors ts ON h.ticker = ts.ticker
  GROUP BY h.investor_id, h.period_of_report
)
SELECT
  q1.investor_id,
  q1.sector_pct as current_pct,
  q2.sector_pct as prev_pct,
  (q1.sector_pct - COALESCE(q2.sector_pct, 0)) as trend
FROM quarterly q1
LEFT JOIN quarterly q2 ON q1.investor_id = q2.investor_id
  AND q2.period_of_report = :prev_period
WHERE q1.period_of_report = :latest_period
```
- trend > +5%: 10 pts (actively increasing exposure)
- trend > +2%: 7 pts
- trend > 0%: 4 pts
- trend = 0: 2 pts (holding steady)
- trend < 0: 0 pts (reducing exposure)

### Fallback for firms WITHOUT 13F data:
- Use `primary_sector` and `secondary_sectors` from Form ADV
- If sector matches target: 12 pts (capped — no behavioral confirmation)
- If no sector data: 0 pts

## 6. Dimension 3: Position Behavior (0-25 pts)

**Data source**: 13F holdings (multi-quarter comparison)
**Available for**: Firms with 13F data across 2+ quarters

This dimension measures **how the firm invests** — active vs passive, conviction level.

### Sub-scores:

**6a. Concentration / Conviction (0-10 pts)**
```sql
-- Top-10 concentration: what % of total portfolio is in top 10 positions?
WITH ranked AS (
  SELECT
    investor_id,
    market_value,
    SUM(market_value) OVER (PARTITION BY investor_id) as total_mv,
    ROW_NUMBER() OVER (PARTITION BY investor_id ORDER BY market_value DESC) as rn
  FROM ir_holdings
  WHERE period_of_report = :latest_period
)
SELECT
  investor_id,
  SUM(CASE WHEN rn <= 10 THEN market_value ELSE 0 END) * 1.0 / total_mv as top10_pct
FROM ranked
GROUP BY investor_id
```
- top10_pct >= 50%: 10 pts (high conviction — concentrated bets)
- top10_pct >= 30%: 7 pts
- top10_pct >= 15%: 4 pts
- top10_pct < 15%: 1 pt (index-like — low conviction)

Why this matters: A firm that concentrates capital makes bigger bets. They're more likely to write a meaningful check if they like your company.

**6b. New Position Activity (0-8 pts)**
```sql
-- How many NEW positions appeared in the latest quarter?
SELECT
  h1.investor_id,
  COUNT(*) as new_positions,
  (SELECT COUNT(DISTINCT cusip) FROM ir_holdings h0
   WHERE h0.investor_id = h1.investor_id
   AND h0.period_of_report = :latest_period) as total_positions
FROM ir_holdings h1
WHERE h1.period_of_report = :latest_period
AND NOT EXISTS (
  SELECT 1 FROM ir_holdings h0
  WHERE h0.investor_id = h1.investor_id
  AND h0.cusip = h1.cusip
  AND h0.period_of_report = :prev_period
)
GROUP BY h1.investor_id
```
- new_positions / total_positions >= 15%: 8 pts (actively deploying)
- >= 10%: 6 pts
- >= 5%: 4 pts
- >= 1%: 2 pts
- 0%: 0 pts (static portfolio)

**6c. Check Size Compatibility (0-7 pts)**
```sql
-- Median position size vs target_check_size
SELECT
  investor_id,
  -- market_value is in thousands, so multiply by 1000
  MEDIAN(market_value * 1000) as median_position
FROM ir_holdings
WHERE period_of_report = :latest_period
GROUP BY investor_id
```
Note: SQLite lacks MEDIAN — use percentile approximation or sort+offset.

- If `target_check_size` falls within [median/5, median*5]: 7 pts
- Within [median/10, median*10]: 4 pts
- Outside: 1 pt

### Fallback for firms WITHOUT multi-quarter 13F data:
- Use `min_account_size` from Form ADV as proxy for check size: up to 4 pts
- Use `is_activist` flag: +3 pts if true (implies conviction investing)
- Cap at 10 pts total (no behavioral confirmation)

## 7. Dimension 4: Direct Signal (0-25 pts)

**Data source**: 13F holdings + target_tickers
**Available for**: Firms with 13F data AND user-provided target tickers

This is the strongest signal: **does this firm already own companies like yours?**

### Sub-scores:

**7a. Target Ticker Overlap (0-15 pts)**
```sql
-- Does the firm hold any of the user's target_tickers?
SELECT
  h.investor_id,
  COUNT(DISTINCT h.ticker) as overlap_count,
  SUM(h.market_value) as overlap_value
FROM ir_holdings h
WHERE h.ticker IN (:target_tickers)
AND h.period_of_report = :latest_period
GROUP BY h.investor_id
```
- Holds 3+ target tickers: 15 pts
- Holds 2: 12 pts
- Holds 1: 8 pts
- Holds 0: 0 pts

**7b. Target Ticker Trend (0-10 pts)**
```sql
-- Is the firm INCREASING positions in target tickers?
WITH q AS (
  SELECT investor_id, period_of_report,
    SUM(market_value) as target_mv
  FROM ir_holdings
  WHERE ticker IN (:target_tickers)
  GROUP BY investor_id, period_of_report
)
SELECT q1.investor_id,
  (q1.target_mv - COALESCE(q2.target_mv, 0)) as mv_change
FROM q q1
LEFT JOIN q q2 ON q1.investor_id = q2.investor_id
  AND q2.period_of_report = :prev_period
WHERE q1.period_of_report = :latest_period
```
- Increased position value: 10 pts
- Held steady (within 5%): 5 pts
- Decreased: 0 pts
- New position (wasn't there last quarter): 10 pts (strongest buy signal)

### Fallback for firms WITHOUT target ticker data:
- No fallback — this dimension requires specific holdings data
- Score: 0 pts (not penalized — other dimensions compensate)

## 8. Score Computation Pipeline

### Step 1: Pre-compute (batch, on 13F data refresh)
Run after each 13F ingestion cycle. Store in `ir_fit_metrics` table:

```sql
CREATE TABLE IF NOT EXISTS ir_fit_metrics (
  id TEXT PRIMARY KEY,
  investor_id TEXT NOT NULL REFERENCES ir_investors(id),
  period_of_report TEXT NOT NULL,
  -- Concentration
  top10_concentration REAL,        -- % of portfolio in top 10
  hhi_score REAL,                  -- Herfindahl-Hirschman Index
  total_positions INTEGER,         -- Number of distinct holdings
  -- Activity
  new_position_count INTEGER,      -- New positions this quarter
  exit_count INTEGER,              -- Exited positions this quarter
  turnover_rate REAL,              -- (new + exits) / total
  -- Size
  median_position_value REAL,      -- Median position in USD
  mean_position_value REAL,        -- Mean position in USD
  total_portfolio_value REAL,      -- Sum of all holdings
  -- Sectors (JSON — top 5 sectors by weight)
  sector_weights TEXT,             -- e.g. {"Technology": 0.35, "Healthcare": 0.22, ...}
  -- Computed at
  computed_at TEXT DEFAULT (datetime('now')),
  UNIQUE(investor_id, period_of_report)
);
```

### Step 2: Query-time scoring
When user searches with fit score enabled:
1. Apply standard filters (AUM, geography, etc.) to narrow candidates
2. For each candidate, compute 4 dimension scores using pre-computed metrics + search context
3. Sum dimensions, assign tier label
4. Sort by total score descending

### Step 3: Response shape
```json
{
  "investor_id": "abc-123",
  "name": "Vanguard Group",
  "fit_score": 82,
  "fit_tier": "A",
  "fit_breakdown": {
    "profile_match": 19,
    "sector_alignment": 22,
    "position_behavior": 18,
    "direct_signal": 23
  },
  "confidence": "high",
  "data_sources": ["form_adv", "13f_q4_2025"]
}
```

**Confidence levels:**
- `high`: Has 13F data + Form ADV (all 4 dimensions scored with real data)
- `medium`: Has Form ADV + CRD-to-CIK mapping but 13F not yet ingested
- `low`: Form ADV only (dimensions 2-4 use fallbacks or score 0)

## 9. API Integration

### New endpoint:
```
GET /api/v1/investors/search?fit_score=true&target_sectors=Technology,AI&target_aum_min=100000000&target_state=TX&target_tickers=NVDA,MSFT
```

### Existing search endpoint modification:
Add `fit_score` field to search results when `?fit_score=true` is present. Default sort by fit_score when enabled.

### New endpoint for single investor:
```
GET /api/v1/investors/{id}/fit?target_sectors=Technology&target_tickers=NVDA
```
Returns full breakdown with explanations.

## 10. Implementation Order

1. **Create `ir_fit_metrics` table** — schema above
2. **Build pre-compute script** (`compute_metrics.py`) — runs SQL aggregations over ir_holdings, populates ir_fit_metrics
3. **Build ticker-to-sector mapping** — either from SIC codes in EDGAR filings or a free bulk source. Store in `ir_ticker_sectors(ticker, sector, sub_industry)`
4. **Implement `fit_score.py`** — takes search context + investor_id, returns score breakdown
5. **Wire into search API** — add `?fit_score=true` parameter to search endpoint
6. **Test with seed data** — Validate scores make sense for our 8 filers (Vanguard should score low on concentration, Renaissance should score high)

## 11. Expected Results (Validation)

With our current 8 seed filers, expected scoring patterns:

| Filer | Concentration | Activity | Notes |
|-------|-------------|----------|-------|
| Renaissance | HIGH | HIGH | Quant fund, high turnover, concentrated |
| Berkshire | HIGH | LOW | Buy-and-hold, very concentrated |
| Vanguard | LOW | LOW | Index fund, 4,300+ positions |
| BlackRock | LOW | MEDIUM | Mix of active + index |
| Goldman | MEDIUM | HIGH | Active trading desk |

If Vanguard scores higher than Renaissance on a "concentrated active investor" search, something is wrong.

## 12. Data Gap: Ticker-to-Sector Mapping

**This is the one prerequisite Keel needs to source.** Options:

1. **SEC SIC codes**: Free, available via EDGAR company search API. Maps CIK to SIC code (4-digit industry classification). We can then map SIC to GICS sector.
2. **OpenFIGI**: Already in our pipeline for CUSIP resolution. Some responses include sector data.
3. **Bulk CSV**: Several free sources publish ticker→sector mappings (e.g., from index constituents).

Recommend: Start with SEC SIC codes (already have the EDGAR API client) and enhance later.
