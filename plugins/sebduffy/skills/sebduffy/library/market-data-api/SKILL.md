---
name: market-data-api
category: data-analysis
description: >
  Pull finance and macroeconomic data from free public APIs into tidy, date-aligned
  datasets. Use to fetch FRED time series (GDP, CPI, rates, unemployment), SEC EDGAR /
  XBRL company financials (revenue, EPS, balance-sheet facts), World Bank / IMF / OECD
  indicators, FX rates, and crypto prices — then merge them into one pandas frame keyed
  on date. Reach for this whenever someone asks for economic indicators, filings numbers,
  exchange rates, or a joined macro/markets panel without paying for Bloomberg.
when_to_use:
  - Fetching a FRED macro series (CPIAUCSL, UNRATE, DGS10, GDP) as a dated pandas Series
  - Extracting a company's XBRL financial facts (revenue, net income, assets) from SEC EDGAR
  - Getting World Bank / IMF / OECD country indicators across years
  - Pulling FX rates (ECB via Frankfurter) or crypto prices (CoinGecko) for a date range
  - Joining several sources into one date-aligned table for analysis or charting
when_not_to_use:
  - Real-time tick or intraday equity quotes → use a paid feed (Polygon, Alpaca, IEX Cloud)
  - Non-finance government open data (transport, health) → use govt-open-data-api
  - A general index of which free API to pick → use free-api-catalogue first
  - Heavy transform/join of already-downloaded data → use polars-dataframes or duckdb-analytics
keywords:
  - fred
  - sec-edgar
  - xbrl
  - world-bank
  - imf
  - oecd
  - economic-indicators
  - fx-rates
  - crypto-prices
  - coingecko
  - frankfurter
  - macro
  - time-series
  - fredapi
  - company-facts
  - cpi
similar_to:
  - free-api-catalogue
  - govt-open-data-api
  - weather-climate-api
  - duckdb-analytics
  - polars-dataframes
inputs_needed: >
  Which source(s) and identifiers — FRED series IDs, SEC ticker/CIK + XBRL tag, World Bank
  country + indicator code, FX currency pair, or crypto coin id; the date range; and (FRED
  only) a free API key.
produces: A tidy pandas DataFrame/Series indexed by date (or a saved CSV/Parquet), plus the raw JSON if needed.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Market & Economic Data API

Fetch finance and macro data from **free, keyless-or-cheap** public APIs and land it as
tidy, date-aligned pandas objects. Every endpoint below is verified live (2026-07).

## When to use

Someone needs numbers — inflation, rates, GDP, a company's reported revenue, an FX rate,
a coin price — and you want a clean dated Series/DataFrame, not a screenshot. This skill
covers the five workhorse free sources and how to join them.

| Source | Auth | Base URL | Best for |
|--------|------|----------|----------|
| FRED | free key | `https://api.stlouisfed.org/fred` | US/global macro time series |
| SEC EDGAR (XBRL) | UA header only | `https://data.sec.gov` | company filing financials |
| World Bank | none | `https://api.worldbank.org/v2` | country dev indicators |
| Frankfurter (ECB) | none | `https://api.frankfurter.dev/v1` | daily FX rates |
| CoinGecko | none (free tier) | `https://api.coingecko.com/api/v3` | crypto prices |

## Prerequisites

- `python3` (3.9 on this Mac) with `requests` and `pandas`. Install if missing:
  `python3 -m pip install --user requests pandas`.
- **FRED key** (only for FRED): free, instant at <https://fredaccount.stlouisfed.org/apikeys>.
  Export it: `export FRED_API_KEY=...`. Never hardcode it.
- **SEC requires a User-Agent** with contact info on *every* request, or you get 403.
  Use e.g. `User-Agent: seb.duffy@vccp.com market-data-api`. SEC fair-use ≈ 10 req/s.
- Optional convenience lib for FRED: `python3 -m pip install --user fredapi` (thin wrapper,
  same key). Raw `requests` below works without it.

## Recipes

### 1. FRED time series → dated pandas Series

Endpoint: `GET /series/observations` with `series_id`, `file_type=json`, `api_key`, and
optional `observation_start` / `observation_end` (YYYY-MM-DD), `units`, `frequency`.

```python
import os, requests, pandas as pd

def fred_series(series_id, start=None, end=None):
    key = os.environ["FRED_API_KEY"]
    p = {"series_id": series_id, "api_key": key, "file_type": "json"}
    if start: p["observation_start"] = start
    if end:   p["observation_end"] = end
    r = requests.get("https://api.stlouisfed.org/fred/series/observations",
                     params=p, timeout=30)
    r.raise_for_status()
    obs = r.json()["observations"]
    s = pd.Series({o["date"]: (float(o["value"]) if o["value"] != "." else None)
                   for o in obs}, name=series_id)
    s.index = pd.to_datetime(s.index)
    return s.dropna()

cpi = fred_series("CPIAUCSL", "2015-01-01")   # US CPI, all urban consumers
```

Note FRED uses `"."` for missing values — always coerce, never `float(".")`. Handy series:
`GDP`, `UNRATE` (unemployment), `DGS10` (10y treasury), `FEDFUNDS`, `T10Y2Y` (yield curve),
`CPIAUCSL`, `DEXUSEU` (USD/EUR). Discover more via `GET /series/search?search_text=...`.

With the wrapper: `from fredapi import Fred; Fred(os.environ["FRED_API_KEY"]).get_series("UNRATE")`.

### 2. SEC EDGAR — company XBRL facts

First resolve a **CIK** (10 digits, zero-padded). Map ticker→CIK once from the official file:

```python
import requests
UA = {"User-Agent": "seb.duffy@vccp.com market-data-api"}
tickers = requests.get("https://www.sec.gov/files/company_tickers.json",
                       headers=UA, timeout=30).json()
by_ticker = {v["ticker"]: str(v["cik_str"]).zfill(10) for v in tickers.values()}
cik = by_ticker["AAPL"]   # -> '0000320193'
```

Then hit one of three endpoints (all under `https://data.sec.gov`):

- **All facts:** `/api/xbrl/companyfacts/CIK{cik}.json` — every reported tag.
- **One concept:** `/api/xbrl/companyconcept/CIK{cik}/us-gaap/{Tag}.json` — one line item across time.
- **Cross-company frame:** `/api/xbrl/frames/us-gaap/{Tag}/USD/CY2023Q1I.json` — same tag, all filers, one period.

```python
def sec_concept(cik, tag, taxonomy="us-gaap", unit="USD"):
    url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{tag}.json"
    d = requests.get(url, headers=UA, timeout=30).json()
    rows = d["units"][unit]
    df = pd.DataFrame(rows)                 # start,end,val,fy,fp,form,filed,frame
    df["end"] = pd.to_datetime(df["end"])
    return df

rev = sec_concept(cik, "RevenueFromContractWithCustomerExcludingAssessedTax")
# Deduplicate to one value per period (filings restate): keep latest-filed
rev = rev.sort_values("filed").drop_duplicates("end", keep="last")
```

Common tags: `Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax`, `NetIncomeLoss`,
`Assets`, `Liabilities`, `EarningsPerShareDiluted`, `CashAndCashEquivalentsAtCarryingValue`.
Frame period codes: `CY2023` (annual), `CY2023Q1` (quarterly duration), `CY2023Q1I` (instant/balance-sheet).

### 3. World Bank indicator

Keyless. `GET /country/{iso}/indicator/{code}?format=json&date=2010:2023&per_page=500`.
Response is a 2-element array `[metadata, data]`.

```python
def worldbank(country, indicator, start=2000, end=2023):
    url = (f"https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"
           f"?format=json&per_page=1000&date={start}:{end}")
    data = requests.get(url, timeout=30).json()[1]
    s = pd.Series({int(d["date"]): d["value"] for d in data if d["value"] is not None},
                  name=indicator).sort_index()
    return s

gdp = worldbank("US", "NY.GDP.MKTP.CD")   # nominal GDP, current USD
```

Codes: `NY.GDP.MKTP.CD` (GDP), `FP.CPI.TOTL.ZG` (inflation %), `SL.UEM.TOTL.ZS` (unemployment),
`SP.POP.TOTL` (population). Use `all` as country for every economy. Multi-country: comma-join
ISO2 codes, e.g. `country/US;GB;DE/...`. (IMF: `https://www.imf.org/external/datamapper/api/v1`;
OECD SDMX: `https://sdmx.oecd.org/public/rest/data/...` — same tidy-into-Series pattern.)

### 4. FX rates (Frankfurter / ECB)

Keyless, daily ECB reference rates back to 1999. `base` + `symbols`; use `/YYYY-MM-DD` for a
day or `/START..END` for a range.

```python
# latest
requests.get("https://api.frankfurter.dev/v1/latest",
             params={"base": "USD", "symbols": "GBP,EUR"}, timeout=30).json()
# time series -> DataFrame of rates
ts = requests.get("https://api.frankfurter.dev/v1/2024-01-01..2024-12-31",
                  params={"base": "USD", "symbols": "GBP"}, timeout=30).json()
fx = pd.Series({k: v["GBP"] for k, v in ts["rates"].items()}, name="USDGBP")
fx.index = pd.to_datetime(fx.index)
```

### 5. Crypto prices (CoinGecko)

Free tier, no key. Spot: `/simple/price?ids=bitcoin&vs_currencies=usd`. History (max range,
daily): `/coins/{id}/market_chart?vs_currency=usd&days=365` → `prices` = `[[ms_epoch, price], …]`.

```python
mc = requests.get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
                  params={"vs_currency": "usd", "days": 365}, timeout=30).json()
btc = pd.Series({pd.to_datetime(ms, unit="ms").normalize(): px for ms, px in mc["prices"]},
                name="BTCUSD")
```

Rate limit ~5-15 req/min on free tier — add `time.sleep(2)` between calls; on HTTP 429 back off.

### 6. Join into one date-aligned panel

Every recipe returns a dated Series/DataFrame, so alignment is a one-liner. Resample to a
common frequency (month-start here) before concat so mixed daily/monthly sources line up:

```python
panel = pd.concat(
    [s.resample("MS").last() for s in (cpi, fx, btc)], axis=1
).sort_index()
panel.to_parquet("macro_panel.parquet")   # or .to_csv(...)
```

## Verify

Quick smoke tests (SEC + Frankfurter + CoinGecko need no key):

```bash
# SEC concept (needs UA or 403)
curl -s -A "you@example.com test" \
  "https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Revenues.json" | head -c 120
# FX
curl -sL "https://api.frankfurter.dev/v1/latest?base=USD&symbols=GBP" | head -c 120
# FRED (expect a clean key error, confirming the endpoint)
curl -s "https://api.stlouisfed.org/fred/series/observations?series_id=GDP&file_type=json" | head -c 120
```

A good FRED response has non-empty `observations`; a good SEC response has `units.USD`; a
good World Bank response is a 2-element array with the data list at index `[1]`.

## Pitfalls

- **SEC 403** = missing/blank `User-Agent`. It is mandatory and must identify you.
- **FRED `"."`** is the missing marker — coercing with a plain `float()` throws; guard it.
- **XBRL restatements**: the same period appears multiple times across filings. Dedup on
  `end` keeping the latest `filed`, or you double-count.
- **CIK padding**: endpoints want a 10-digit zero-padded CIK (`CIK0000320193`), not the raw int.
- **Frankfurter has no weekend/holiday rows** (ECB doesn't publish) — reindex + ffill if you
  need a value for every calendar day.
- **World Bank returns nulls** for years with no data and paginates (`per_page`); drop `None`
  and raise `per_page` (max 1000) rather than looping pages.
- **Rate limits**: SEC ~10 req/s, CoinGecko free ~5-15 req/min. Batch identifiers into one
  request where the API allows (comma-separated `ids`/countries) and sleep between calls.
- **Not for intraday equities.** These free sources are daily/EOD or lower. For live quotes
  use a paid feed — see `free-api-catalogue` for the shortlist.
