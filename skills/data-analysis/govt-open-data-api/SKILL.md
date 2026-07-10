---
name: govt-open-data-api
category: data-analysis
description: >
  Pull real government & open-data programmatically from CKAN and Socrata portals (data.gov, data.gov.uk,
  data.cityofchicago.org, thousands more) plus the big official statistics APIs — US Census ACS demographics,
  Eurostat, UK ONS, and OECD. Use to find datasets, search catalogues, query rows with filters, and fetch
  demographic/economic indicators without fabricating numbers. Grounds every figure in a live API call, not memory.
when_to_use:
  - User wants demographic, economic, spending, health, crime, or census figures for a country/region/city
  - User names an open-data portal (data.gov, data.gov.uk, a US city/state Socrata site) or asks "is there open data on X"
  - User needs US Census ACS variables (population, income, age, race) by state/county/tract
  - User asks for Eurostat, OECD, or UK ONS statistics by geography and time period
  - You must cite an official source number and refuse to guess it
when_not_to_use:
  - Company/market/financial data (stocks, tickers, private firms) — use market-data-api
  - Weather or climate observations — use weather-climate-api
  - Turning a place name into lat/lng or admin boundaries — use geocoding-places-api
  - General "what free APIs exist" scouting — use free-api-catalogue
  - Encyclopaedic facts / entity relationships (not tabular stats) — use wikidata-knowledge-api
keywords: [ckan, socrata, soda, census, acs, eurostat, ons, oecd, open-data, data.gov, sdmx, soql, demographics, statistics, package_search, api, government]
similar_to: [free-api-catalogue, market-data-api, geocoding-places-api, weather-climate-api, wikidata-knowledge-api]
inputs_needed: Which portal/agency or geography+topic; the metric wanted; geography level (state/county/NUTS/LAD); time period; optional API key/app-token if you have one
produces: Live JSON/CSV rows from the portal plus a cited figure or a saved dataset file, with the exact endpoint URL used
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Government & Open-Data API

## When to use
Reach for this whenever a user needs a **real, citable** government statistic or an open-data dataset. Two worlds:

1. **Meta-platforms** — CKAN and Socrata power thousands of portals (national, city, agency). Same API shape everywhere, so learn once.
2. **Official statistics agencies** — Census (US), Eurostat (EU), ONS (UK), OECD. Bespoke but well-documented.

The anti-hallucination contract (see the category README) is strict here: **never report a demographic or economic number you did not fetch.** If you cannot reach the API, say so and hand the user the exact URL.

## Prerequisites
- `python3` (3.9 ok) + stdlib `urllib`, or `curl`. `requests`/`pandas` nice but optional.
- **Keys — mostly optional:**
  - CKAN, Eurostat, ONS, OECD: **no key needed**, fully open.
  - **US Census:** works keyless for light use but rate-limited; a free key (`api.census.gov/data/key_signup.html`) lifts limits. Pass as `&key=...`.
  - **Socrata:** works keyless but throttled; a free **app token** raises limits. Pass header `X-App-Token: TOKEN` (or `$$app_token=TOKEN`).
- Portals return **HTTP 200 even on logical errors** (CKAN especially) — always check the JSON `success`/`error` field, not just the status code.

## Recipes

### 0. Identify the platform first
Not sure if a portal is CKAN or Socrata? Probe it:
```bash
python3 scripts/portal_probe.py https://data.gov.uk        # -> ckan
python3 scripts/portal_probe.py data.cityofchicago.org     # -> socrata
```
It returns the platform and a filled-in search endpoint template.

### 1. CKAN — search a catalogue & fetch a dataset
Base pattern: `https://{site}/api/3/action/{action}`.
```bash
# Search datasets (q=full-text, rows=page size ≤1000, fq=Solr filter, start=offset)
curl -s 'https://data.gov.uk/api/3/action/package_search?q=air+quality&rows=5' \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d["success"]; \
    print(d["result"]["count"],"hits"); [print("-",r["name"]) for r in d["result"]["results"]]'

# Full metadata + resource (file) URLs for one dataset
curl -s 'https://data.gov.uk/api/3/action/package_show?id=DATASET_NAME' \
  | python3 -c 'import sys,json; d=json.load(sys.stdin)["result"]; \
    [print(res["format"], res["url"]) for res in d["resources"]]'
```
Useful actions: `package_search`, `package_show`, `resource_show`, `organization_list`, `group_list`, `tag_list`.
If a resource is in the **DataStore**, query rows directly (no download):
```bash
curl -s 'https://{site}/api/3/action/datastore_search?resource_id=RID&q=london&limit=100'
# Or SQL (where enabled):
curl -s --get 'https://{site}/api/3/action/datastore_search_sql' \
  --data-urlencode 'sql=SELECT * FROM "RID" WHERE "year"=2023 LIMIT 50'
```

### 2. Socrata (SODA) — query rows with SoQL
Classic endpoint: `https://{domain}/resource/{four-by-four}.json`. Params are `$`-prefixed SoQL.
```bash
# Chicago building permits, filtered + selected + sorted, capped at 1000 rows
curl -s -H 'X-App-Token: YOUR_TOKEN' \
  "https://data.cityofchicago.org/resource/ydr8-5enu.json?\$select=permit_,work_type,total_fee&\$where=total_fee>50000&\$order=total_fee%20DESC&\$limit=1000"

# Aggregate with $group + $where
curl -s "https://data.cityofchicago.org/resource/ydr8-5enu.json?\$select=work_type,count(*)&\$group=work_type"
```
SoQL clauses: `$select $where $order $group $having $limit $offset $q` (free-text). Discover datasets across all Socrata sites via the catalog:
`https://api.us.socrata.com/api/catalog/v1?domains={host}&q=permits`.
Paginate with `$limit` + `$offset`; default page is 1000, max is 50000 per request.

### 3. US Census — ACS demographics
Base: `https://api.census.gov/data/{year}/acs/acs5?get={vars}&for={geo}&in={parent}`.
```bash
# Total population (B01001_001E) + median household income (B19013_001E) per California county
curl -s 'https://api.census.gov/data/2022/acs/acs5?get=NAME,B01001_001E,B19013_001E&for=county:*&in=state:06'
```
- `acs5` = 5-year (best geographic detail, down to tract/block-group); `acs1` = 1-year (≥65k pop, most recent).
- Variables are codes ending `E` (estimate) / `M` (margin of error). Look them up:
  `https://api.census.gov/data/2022/acs/acs5/variables.html`.
- Geography: `for=state:06`, `for=county:*&in=state:06`, `for=tract:*&in=state:06+county:075`.
- Response is a **2-D array** (first row = headers), not objects — parse accordingly.
- Add `&key=YOUR_KEY` to avoid throttling.

### 4. Eurostat — EU statistics (JSON-stat)
Base: `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}?format=JSON&...`. No key.
```bash
# Unemployment rate (une_rt_m), Germany + France, latest 3 periods, seasonally adjusted, total, %
curl -s 'https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/une_rt_m?format=JSON&geo=DE&geo=FR&sinceTimePeriod=2025-01&s_adj=SA&sex=T&age=TOTAL&unit=PC_ACT'
```
Filter with dimension params (`geo`, `time`, `sinceTimePeriod`, plus dataset-specific dims). Response is **JSON-stat**: values live in `.value` keyed by a flat index; dimension order/sizes in `.dimension` and `.id`/`.size`. Find dataset codes at the Eurostat Data Browser.

### 5. UK ONS — beta API
Base: `https://api.beta.ons.gov.uk/v1`. No key.
```bash
# List datasets
curl -s 'https://api.beta.ons.gov.uk/v1/datasets?limit=20'
# CPIH inflation index: one observation (pin every dimension; use * as one wildcard)
curl -s 'https://api.beta.ons.gov.uk/v1/datasets/cpih01/editions/time-series/versions/4/observations?time=Apr-20&geography=K02000001&aggregate=cpih1dim1G100000'
```
Walk `datasets → editions → versions → dimensions → options` to learn valid codes before requesting observations. Exactly one dimension may be `*` (wildcard) per observations call.

### 6. OECD — SDMX REST
Base: `https://sdmx.oecd.org/public/rest/data/{agency},{dataflow},{version}/{key}?...`. No key.
```bash
# Key is dot-separated dimension filter (empty segment = all); startPeriod/endPeriod bound time
curl -s -H 'Accept: application/vnd.sdmx.data+json' \
  'https://sdmx.oecd.org/public/rest/data/OECD.SDD.TPS,DSD_QNA@DF_QNA,1.0/....?startPeriod=2023&dimensionAtObservation=AllDimensions'
```
Request `application/vnd.sdmx.data+json` for JSON; browse dataflows/dimension IDs at the OECD Data Explorer's Developer API panel.

## Verify
- **Always check the success flag:** CKAN `d["success"] is True`; Socrata/Census error bodies carry an `error`/`message`. A 200 is not proof of success.
- **Sanity-check magnitudes** against a known anchor (e.g. California ACS pop ≈ 39M) before quoting.
- **Cite the exact endpoint URL** you called alongside every figure so the user can reproduce it.
- Confirm the **year/edition** matches what the user asked — ACS `2022/acs5` covers 2018-2022, not "2022 today".

## Pitfalls
- **CKAN silent errors:** malformed `fq` or a missing dataset still returns 200 with `success:false` — assert on it or you'll "read" an empty result as zero.
- **Socrata pagination:** without `$limit` you silently get only 1000 rows; loop `$offset` (or `$order` a unique column) to page the full set. Reserved chars in `$where` must be URL-encoded; strings use single quotes.
- **Census array shape:** it is `[[header...],[row...]]`, values are **strings**, and suppressed cells come back as negative sentinels (e.g. `-666666666`) — filter those.
- **Eurostat/OECD wide queries 413/timeout:** over-broad selections exceed size limits; always pin dimensions and a time window.
- **ONS over-fetch:** observations endpoint needs every dimension pinned except one wildcard; otherwise it errors or returns 10k-capped noise.
- **Rate limits:** add a Census key / Socrata app token for anything beyond a handful of calls; back off on HTTP 429.
- **Don't hand-type four-by-fours or dataset codes from memory** — search the catalogue first; codes change and a wrong id silently returns nothing useful.
