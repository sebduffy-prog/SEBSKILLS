---
name: weather-climate-api
category: data-analysis
description: >
  Pull weather forecasts, ERA5 historical climate reanalysis (1940→now), and air-quality
  from free APIs to use as model covariates or narrative context. Reach for this whenever a
  task needs temperature/precip/wind/AQI by lat-lon or date range — footfall vs weather,
  seasonality features, "was it raining that day", pollution overlays. Open-Meteo (no key,
  forecast + archive + air-quality), NWS api.weather.gov (US, no key, needs User-Agent),
  OpenAQ v3 (free key) for ground-station measurements. Real endpoints, correct params.
when_to_use:
  - Adding weather (temp, rain, wind, humidity) as covariates to a forecasting/MMM/regression model
  - Backfilling historical climate for any lat-lon and date range via ERA5 reanalysis (from 1940)
  - Enriching an event/sales/footfall table with "what was the weather that day"
  - Fetching a live forecast for a location for a report, dashboard, or briefing
  - Overlaying air-quality (PM2.5, PM10, AQI, NO2, O3) on a place or campaign
when_not_to_use:
  - Geocoding a place name to lat-lon first — use geocoding-places-api (Open-Meteo geocoding is noted here but that skill is canonical)
  - Non-weather government/statistical open data — use govt-open-data-api
  - A general survey of which free API to reach for — use free-api-catalogue
  - Financial/market time series as covariates — use market-data-api
keywords: [weather, climate, era5, reanalysis, open-meteo, nws, weather.gov, openaq, air-quality, forecast, precipitation, temperature, covariate, historical-weather, pm25, aqi]
similar_to: [free-api-catalogue, market-data-api, govt-open-data-api, geocoding-places-api]
inputs_needed: Location as latitude/longitude (or a place name to geocode first); a date or date range for history; which variables (temp, precip, wind, AQI) you need; timezone.
produces: Tidy per-hour or per-day weather/climate/air-quality records (JSON→CSV/DataFrame) keyed by timestamp and location, ready to join onto your data.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Weather, Climate & Air-Quality API

Three free APIs, one job: get weather/climate/AQI by lat-lon and date. All examples are runnable
with `python3` (3.9, stdlib `urllib`) or `curl` — no SDK, no paid tier.

| API | Base URL | Key? | Best for |
|-----|----------|------|----------|
| Open-Meteo Forecast | `https://api.open-meteo.com/v1/forecast` | none | live/near-term forecast, global |
| Open-Meteo Archive (ERA5) | `https://archive-api.open-meteo.com/v1/archive` | none | historical covariates 1940→present |
| Open-Meteo Air-Quality | `https://air-quality-api.open-meteo.com/v1/air-quality` | none | modelled PM2.5/PM10/AQI/NO2/O3 |
| NWS | `https://api.weather.gov` | none (User-Agent required) | official US forecast text/periods |
| OpenAQ v3 | `https://api.openaq.org/v3` | **free key** (`X-API-Key`) | real ground-station measurements |

## When to use

You need weather/climate/pollution values joined to a place and time. For modelling, **Open-Meteo
Archive (ERA5) is the workhorse** — one consistent global gridded reanalysis back to 1940, so
train and score periods use the same source. Use NWS only for US-official forecast wording; use
OpenAQ only when you specifically need measured (not modelled) station readings.

## Prerequisites

- `python3` + stdlib only (or `curl`). No `requests` needed; examples use `urllib`.
- Open-Meteo & NWS: **no key**. NWS **requires** a descriptive `User-Agent` (email/app) or it 403s.
- OpenAQ v3: free key from https://explore.openaq.org/register → send header `X-API-Key: <key>`.
  Store in env `OPENAQ_API_KEY`; never hardcode.
- Have lat-lon ready. No place name? Geocode first (see geocoding-places-api, or the Open-Meteo
  geocoding one-liner in Recipe 5).
- Free/non-commercial use only for Open-Meteo without a plan; be polite (cache, batch, don't hammer).

## Recipes

### 1. Historical climate covariates (ERA5) — the main one

Daily aggregates for a date range, ready to join by date. ERA5 archive lags ~5 days behind today.

```bash
curl -sG 'https://archive-api.open-meteo.com/v1/archive' \
  --data-urlencode 'latitude=51.5074' \
  --data-urlencode 'longitude=-0.1278' \
  --data-urlencode 'start_date=2024-01-01' \
  --data-urlencode 'end_date=2024-03-31' \
  --data-urlencode 'daily=temperature_2m_mean,temperature_2m_max,precipitation_sum,rain_sum,wind_speed_10m_max,sunshine_duration' \
  --data-urlencode 'timezone=Europe/London'
```

Flatten `daily.time[]` + parallel arrays to rows in Python:

```python
import json, urllib.parse, urllib.request, csv, sys

def fetch(base, params):
    url = base + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "sebskills/1.0 (seb.duffy@vccp.com)"})
    with urllib.request.urlopen(req, timeout=30) as r:      # raises on HTTP error
        return json.load(r)

def daily_rows(js):
    d = js["daily"]; keys = [k for k in d if k != "time"]
    return [dict(date=t, **{k: d[k][i] for k in keys}) for i, t in enumerate(d["time"])]

js = fetch("https://archive-api.open-meteo.com/v1/archive", {
    "latitude": 51.5074, "longitude": -0.1278,
    "start_date": "2024-01-01", "end_date": "2024-03-31",
    "daily": "temperature_2m_mean,precipitation_sum,wind_speed_10m_max",
    "timezone": "Europe/London",
})
rows = daily_rows(js)
w = csv.DictWriter(sys.stdout, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
```

Swap `daily=` for `hourly=temperature_2m,precipitation,relative_humidity_2m,wind_speed_10m` and read
`js["hourly"]` for hour-level rows. Multiple locations: send `latitude=` / `longitude=` as
comma-lists — the response becomes a JSON **array**, one object per location.

### 2. Live / near-term forecast (Open-Meteo)

```bash
curl -sG 'https://api.open-meteo.com/v1/forecast' \
  --data-urlencode 'latitude=40.71' --data-urlencode 'longitude=-74.01' \
  --data-urlencode 'current=temperature_2m,precipitation,wind_speed_10m' \
  --data-urlencode 'hourly=temperature_2m,precipitation_probability' \
  --data-urlencode 'daily=temperature_2m_max,temperature_2m_min,precipitation_sum' \
  --data-urlencode 'forecast_days=7' --data-urlencode 'timezone=auto'
```

`current` gives a single snapshot; `hourly`/`daily` give arrays flattened exactly like Recipe 1.

### 3. Air quality (Open-Meteo, modelled, no key)

```bash
curl -sG 'https://air-quality-api.open-meteo.com/v1/air-quality' \
  --data-urlencode 'latitude=34.05' --data-urlencode 'longitude=-118.24' \
  --data-urlencode 'hourly=pm2_5,pm10,us_aqi,european_aqi,nitrogen_dioxide,ozone' \
  --data-urlencode 'timezone=auto'
```

Add `start_date`/`end_date` for a historical air-quality window (data from ~2022). Flatten `hourly`.

### 4. Official US forecast (NWS — two hops, User-Agent mandatory)

`/points/{lat},{lon}` returns the grid + a `forecast` URL you then fetch for `periods[]`.

```python
UA = {"User-Agent": "sebskills/1.0 (seb.duffy@vccp.com)"}   # NWS 403s without this
pts = fetch("https://api.weather.gov/points/38.8894,-77.0352", {})   # reuse fetch() from Recipe 1
fc  = fetch(pts["properties"]["forecast"], {})
for p in fc["properties"]["periods"][:4]:
    print(p["name"], p["temperature"], p["temperatureUnit"], "-", p["shortForecast"])
```

`properties.forecastHourly` gives the hourly grid; `properties.gridId/gridX/gridY` identify the cell.

### 5. Ground-station measurements (OpenAQ v3 — needs free key)

```bash
export OPENAQ_API_KEY=...   # from explore.openaq.org
# nearest stations within 12km, then that location's latest values
curl -s 'https://api.openaq.org/v3/locations?coordinates=51.5074,-0.1278&radius=12000&limit=20' \
  -H "X-API-Key: $OPENAQ_API_KEY"
curl -s 'https://api.openaq.org/v3/locations/2178/latest' -H "X-API-Key: $OPENAQ_API_KEY"
```

Note OpenAQ `coordinates` is `lat,lon`; `radius` is metres (max 25000). Historical: use
`/v3/sensors/{id}/measurements?datetime_from=...&datetime_to=...`.

### Geocode a place name first (Open-Meteo, no key)

```bash
curl -s 'https://geocoding-api.open-meteo.com/v1/search?name=Glasgow&count=1' \
  | python3 -c 'import json,sys;r=json.load(sys.stdin)["results"][0];print(r["latitude"],r["longitude"],r["timezone"])'
```

## Verify

- Run Recipe 1 for a known place/date — sanity-check magnitudes (London Jan mean ~5°C, not 50).
- Confirm array lengths match: `len(daily.time) == len(daily.<var>)` before zipping into rows.
- Archive returns empty/near-null for the **last ~5 days** (ERA5 lag) — end your range earlier or
  bridge the tail with the Forecast API's past days (`past_days=`).
- NWS: a 403 means missing/blank User-Agent. A 404 on `/points` means non-US coordinates — NWS is US-only.
- OpenAQ: a 401 means missing/invalid `X-API-Key`.

## Pitfalls

- **Timezone**: Open-Meteo defaults to **GMT/UTC**. Always pass `timezone=auto` (or an IANA name)
  or your daily buckets and joins silently shift by hours.
- **Units**: default °C, km/h, mm. Set `temperature_unit=fahrenheit`, `wind_speed_unit=mph`,
  `precipitation_unit=inch` explicitly if a downstream model expects them — don't assume.
- **Modelled ≠ measured**: Open-Meteo air-quality and ERA5 are model output, good for consistent
  covariates; OpenAQ is real sensors, sparser and gappy. Don't mix the two as one series.
- **ERA5 lag**: don't expect yesterday in the archive; it trails ~5 days.
- **Rate limits**: free Open-Meteo is generous but not infinite — cache responses to disk, batch
  multiple locations in one call (comma lat-lon lists) rather than N calls.
- **NULLs**: reanalysis has occasional `null` cells (e.g. `sunshine_duration` over sea) — handle,
  don't `float(None)`-crash your flattener.
- **Don't scrape when an API exists**: all of the above are official JSON endpoints; never HTML-parse.
