---
name: free-api-catalogue
category: data-analysis
description: >
  Curated, verified lookup index of high-value FREE / public APIs — FX & crypto,
  weather & climate, geocoding & places, government & economic data, sports, news,
  Wikipedia/Wikidata knowledge, and demographics — each with a COPY-PASTE example
  call, the exact base URL, auth reality (none / free key / email UA), and rate-limit
  notes. Reach for this whenever you need "a free API for X", "public data source for
  X without paying", "which weather/geocoding/FX API can I just curl", or want to
  prototype against real data before wiring up a paid provider. Every endpoint here
  was smoke-tested and returns real JSON with no billing setup.
when_to_use:
  - "You need real data NOW and want a free endpoint you can curl without signing up"
  - "Prototyping before committing to a paid provider — need a working stand-in"
  - "'Is there a free API for currency / weather / holidays / earthquakes / countries?'"
  - "Enriching a dataset with geocodes, population, FX rates, or public-holiday dates"
  - "You want the exact base URL + auth style + rate limit, not a vague 'try OpenWeather'"
  - "Building a demo/notebook where API keys and billing would be friction"
when_not_to_use:
  - "Deep stock/market feeds (OHLCV, fundamentals) → use market-data-api"
  - "Heavy government open-data portals (data.gov, ONS, Eurostat) → use govt-open-data-api"
  - "Production geocoding at volume with SLAs → use geocoding-places-api"
  - "Forecast-grade meteorology / climate model pulls → use weather-climate-api"
  - "News with sentiment scoring / entity extraction → use news-sentiment-api"
  - "SPARQL / entity graph traversal on Wikidata → use wikidata-knowledge-api"
keywords: [free api, public api, no auth api, curl json, currency api, weather api, geocoding, nominatim, wikidata, wikipedia, coingecko, world bank, rest countries, public holidays, usgs earthquakes, frankfurter, open-meteo, demographics, rate limit]
similar_to: [market-data-api, govt-open-data-api, geocoding-places-api, weather-climate-api, news-sentiment-api, wikidata-knowledge-api]
inputs_needed:
  - "What KIND of data (FX, weather, geocode, country facts, holidays, news, knowledge)?"
  - "One-off lookup or repeated calls (decides whether rate limits / a free key matter)?"
  - "Any hard constraint: zero signup, commercial use allowed, attribution acceptable?"
produces: A working endpoint URL + copy-paste curl/Python call returning real JSON, plus its auth & rate-limit reality
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Free API Catalogue

A field guide to public APIs you can hit **today** with no billing. Every call below
was smoke-tested (HTTP 200, real JSON). Auth column is honest: **none** = pure `curl`,
**UA** = send a descriptive `User-Agent` (with contact email) or you get 403,
**key** = free registration for an API key. Respect the rate limits — they are the
price of "free".

## When to use

Grab-and-go data sourcing. If you just need *a* working endpoint for currencies,
weather, a country's population, or a place's coordinates, pick from the tables and
paste the call. Escalate to the specialised sibling skills (see `when_not_to_use`)
only when you outgrow the free tier or need SPARQL/portal-scale queries.

## Prerequisites

- `curl` (present on macOS) and optionally `jq` for pretty output. Python `urllib`
  works with zero installs if you prefer (`python3` here is 3.9).
- For **UA**-marked APIs set a real User-Agent: `-A "myapp/1.0 (you@example.com)"`.
  Nominatim and the Wikimedia/Wikidata APIs will 403 a blank/library UA.
- Nothing else. No keys required for anything in the **none**/**UA** tables.

## Recipes (verified, copy-paste)

### 1. Finance — FX rates & crypto (no auth)

| API | Base URL | Auth | Limit |
|-----|----------|------|-------|
| Frankfurter (ECB FX) | `api.frankfurter.dev/v1` | none | generous |
| CoinGecko (crypto) | `api.coingecko.com/api/v3` | none | ~10-30 req/min |

```bash
# USD → GBP + EUR, latest ECB reference rates
curl -s "https://api.frankfurter.dev/v1/latest?base=USD&symbols=GBP,EUR"
# Historical on a date:  /v1/2020-01-02?base=USD&symbols=GBP
# Time series:           /v1/2024-01-01..2024-01-31?base=USD&symbols=GBP

# Bitcoin + Ethereum spot in USD & GBP
curl -s "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd,gbp"
```

CoinGecko throttles hard on the free/no-key tier — cache results, don't hammer it.

### 2. Weather & climate — Open-Meteo (no auth, no key)

`api.open-meteo.com/v1` — the best free weather API; **no key at all**, generous
for non-commercial. Needs lat/lon (use the geocoder in §3).

```bash
# Current temp + 7-day daily max/min for London
curl -s "https://api.open-meteo.com/v1/forecast?latitude=51.5074&longitude=-0.1278\
&current=temperature_2m,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min&timezone=auto"

# Historical archive (ERA5 reanalysis) — different host:
curl -s "https://archive-api.open-meteo.com/v1/archive?latitude=51.5&longitude=-0.12\
&start_date=2023-01-01&end_date=2023-01-07&daily=temperature_2m_mean"
```

### 3. Geocoding & places (name ⇆ coordinates)

| API | Base URL | Auth | Limit |
|-----|----------|------|-------|
| Open-Meteo geocoder | `geocoding-api.open-meteo.com/v1` | none | generous |
| Nominatim (OSM) | `nominatim.openstreetmap.org` | **UA** | **1 req/sec** |
| Zippopotam (postcode) | `api.zippopotam.us` | none | generous |

```bash
# Fast, key-free forward geocode (returns lat/lon + admin hierarchy)
curl -s "https://geocoding-api.open-meteo.com/v1/search?name=Edinburgh&count=1"

# Nominatim — richer OSM data, but ONE request per second and a real UA is mandatory
curl -s -A "sebskills/1.0 (seb.duffy@vccp.com)" \
  "https://nominatim.openstreetmap.org/search?q=Eiffel+Tower&format=json&limit=1"

# Postcode/ZIP → place + coords (US 90210, GB, DE, ~60 countries)
curl -s "https://api.zippopotam.us/us/90210"
curl -s "https://api.zippopotam.us/gb/EC1A"
```

Never bulk-geocode Nominatim faster than 1/sec — you WILL be IP-banned. For volume
use Open-Meteo's geocoder or the geocoding-places-api sibling.

### 4. Government & economic data (no auth)

| API | Base URL | Auth | What |
|-----|----------|------|------|
| World Bank | `api.worldbank.org/v2` | none | indicators for every country/year |
| USGS Earthquakes | `earthquake.usgs.gov/fdsnws/event/1` | none | live seismic events (GeoJSON) |
| Nager.Date | `date.nager.at/api/v3` | none | public holidays, 100+ countries |
| REST Countries | `restcountries.com/v3.1` | none | country facts (pop, capital, currency) |

```bash
# UK total population time series (indicator SP.POP.TOTL)
curl -s "https://api.worldbank.org/v2/country/GB/indicator/SP.POP.TOTL?format=json&per_page=5"
#   GDP = NY.GDP.MKTP.CD · CO2 = EN.ATM.CO2E.PC · full list: /v2/indicator?format=json

# Magnitude 5+ quakes in the last day
curl -s "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minmagnitude=5&limit=5"

# UK public holidays for 2026
curl -s "https://date.nager.at/api/v3/PublicHolidays/2026/GB"

# Country facts (trim payload with ?fields=)
curl -s "https://restcountries.com/v3.1/name/france?fields=name,capital,population,currencies"
```

### 5. Knowledge — Wikipedia & Wikidata

| API | Base URL | Auth | Use |
|-----|----------|------|-----|
| Wikipedia REST summary | `en.wikipedia.org/api/rest_v1` | **UA** | one-shot article extract |
| Wikidata entities | `www.wikidata.org/w/api.php` | **UA** | structured facts by Q-id |

```bash
# Plain-text summary + thumbnail for an article
curl -s -A "sebskills/1.0 (seb.duffy@vccp.com)" \
  "https://en.wikipedia.org/api/rest_v1/page/summary/Python_(programming_language)"

# Wikidata: labels for Q42 (Douglas Adams). props: labels|descriptions|claims
curl -s -A "sebskills/1.0 (seb.duffy@vccp.com)" \
  "https://www.wikidata.org/w/api.php?action=wbgetentities&ids=Q42&props=labels&languages=en&format=json"
```

For graph traversal / joins use SPARQL at `query.wikidata.org/sparql` — see the
wikidata-knowledge-api sibling.

### 6. News & tech — Hacker News via Algolia (no auth)

```bash
# Recent stories matching a query, most recent first
curl -s "https://hn.algolia.com/api/v1/search_by_date?query=anthropic&tags=story&hitsPerPage=5"
```

Mainstream news with sentiment/entity scoring generally needs a key — hand off to
news-sentiment-api. HN Algolia is the reliable no-auth option for tech signal.

### 7. Zero-install Python fetch (no `requests` needed)

```python
python3 - <<'PY'
import json, urllib.request
url = "https://api.frankfurter.dev/v1/latest?base=USD&symbols=GBP,EUR"
req = urllib.request.Request(url, headers={"User-Agent": "sebskills/1.0 (seb.duffy@vccp.com)"})
print(json.dumps(json.load(urllib.request.urlopen(req, timeout=15)), indent=2))
PY
```

## Verify

Confirm any endpoint is live before building on it — check the HTTP code, not just
that *something* came back:

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" -A "sebskills/1.0 (seb.duffy@vccp.com)" \
  "https://api.open-meteo.com/v1/forecast?latitude=51.5&longitude=-0.12&current=temperature_2m"
# expect: HTTP 200
```

A `200` with a JSON body = good. `403` on Nominatim/Wikipedia/Wikidata = missing or
banned User-Agent (add `-A`). `429` = you hit the rate limit; back off and cache.

## Pitfalls

- **Blank User-Agent → 403.** Nominatim, Wikipedia REST, and Wikidata reject the
  default curl/library UA. Always pass `-A "app/1.0 (email)"` for **UA** APIs.
- **Nominatim is 1 request/second, full stop.** Bulk usage gets your IP blocked.
  Use Open-Meteo's geocoder for throughput.
- **CoinGecko free tier throttles** (roughly 10-30/min, no key). Cache prices; don't
  poll in a tight loop.
- **Frankfurter moved** from `frankfurter.app` to `frankfurter.dev/v1` — use the new
  host (the old one 301-redirects).
- **REST Countries `?fields=` is required for big queries** — `/v3.1/all` without a
  `fields` filter is rejected/huge. Always scope fields.
- **Free ≠ commercial-use-licensed.** OSM/Nominatim (ODbL), Wikipedia (CC-BY-SA),
  ECB data — check attribution/licence before shipping in a product.
- **These are stand-ins, not SLAs.** No uptime guarantee. Once a data source is
  load-bearing, move to the paid/managed sibling skill for that domain.
