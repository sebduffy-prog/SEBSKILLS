---
name: geocoding-places-api
category: data-analysis
description: >
  Turn addresses and place names into lat/lon and back, then enrich with POIs,
  administrative boundaries, road distances and drive/walk-time isochrones — all
  on free tiers. Reach for this when you must geocode a spreadsheet of addresses,
  reverse-geocode GPS points, find "cafes within 500m", draw a "10-minute drive"
  catchment, or compute a distance/travel-time matrix. Wires up Nominatim (OSM),
  the US Census geocoder, Overpass and OpenRouteService with correct endpoints,
  auth and rate-limit discipline so you do not get banned.
when_to_use:
  - Geocoding addresses or place names to coordinates (single or batch)
  - Reverse-geocoding lat/lon back to an address, postcode or admin area
  - Finding POIs (shops, amenities, transit) near a point or inside a bbox
  - Building drive/walk/cycle-time isochrones or catchment polygons
  - Computing road distances or a travel-time matrix between many points
when_not_to_use:
  - Heavy commercial batch geocoding at scale (use paid Google/Mapbox/HERE; Nominatim bans bulk)
  - Rendering interactive slippy maps or choropleths (use geospatial-analysis / a tile lib)
  - Pulling census demographics by geography beyond the code lookup (use govt-open-data-api)
  - Country/market macro indicators keyed by ISO code (use market-data-api)
keywords:
  - geocoding
  - reverse-geocoding
  - nominatim
  - openstreetmap
  - overpass
  - openrouteservice
  - isochrone
  - poi
  - lat-lon
  - census-geocoder
  - travel-time-matrix
  - distance
  - haversine
  - catchment
  - boundaries
similar_to:
  - free-api-catalogue
  - govt-open-data-api
  - market-data-api
  - geospatial-analysis
  - weather-climate-api
inputs_needed: Addresses or place names (or lat/lon), the country/region, radius or travel time, and — for ORS routing/isochrones — a free OpenRouteService API key.
produces: Coordinates, addresses, POI lists, boundary/isochrone GeoJSON and distance/time matrices as JSON/CSV.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Geocoding & Places API

Address ↔ coordinate conversion plus places, boundaries, distances and isochrones,
using four free services. Pick the smallest tool that answers the question.

| Need | Service | Key? | Notes |
|------|---------|------|-------|
| Geocode / reverse (worldwide) | **Nominatim** (OSM) | no | 1 req/s max, real User-Agent required |
| Geocode US addresses in bulk | **US Census** geocoder | no | free batch to 10k rows, US only |
| POIs / boundaries near a point | **Overpass** (OSM) | no | Overpass QL; be gentle |
| Directions / isochrones / matrix | **OpenRouteService** | yes (free) | 2,000–2,500 req/day, 40 req/min |
| Straight-line distance | local **haversine** | no | no network needed |

## When to use

Use when you have text locations and need geometry, or geometry and need context.
For a "which coffee shops are within a 10-minute walk of this office" question you
geocode the office (Nominatim), draw a walk isochrone (ORS), then query POIs inside
it (Overpass) — this skill chains all three.

## Prerequisites

- `curl` + `python3` (3.9 on this Mac) — everything here is HTTP + JSON.
- **OpenRouteService key** (only for directions/isochrones/matrix): sign up free at
  https://openrouteservice.org/dev/#/signup → create a token. Store it:
  `export ORS_KEY=your_token_here`.
- **Nominatim etiquette is enforced by ban**: send a genuine `User-Agent` identifying
  your app + contact, cap at **1 request/second**, cache results, and never bulk-scrape.
  Read https://operations.osmfoundation.org/policies/nominatim/ before batching.
- No key for Nominatim, Census, or Overpass.

## Recipes

### 1. Geocode a place name (Nominatim)

```bash
curl -s -G 'https://nominatim.openstreetmap.org/search' \
  --data-urlencode 'q=Tate Modern, London' \
  -d 'format=jsonv2' -d 'limit=1' -d 'addressdetails=1' \
  -H 'User-Agent: sebskills-geocoder/1.0 (seb.duffy@vccp.com)' \
  | python3 -c 'import sys,json; r=json.load(sys.stdin)[0]; print(r["lat"], r["lon"], r["display_name"])'
```

### 2. Reverse-geocode a coordinate (Nominatim)

```bash
curl -s -G 'https://nominatim.openstreetmap.org/reverse' \
  -d 'lat=51.5076' -d 'lon=-0.0994' -d 'format=jsonv2' \
  -H 'User-Agent: sebskills-geocoder/1.0 (seb.duffy@vccp.com)' \
  | python3 -c 'import sys,json; r=json.load(sys.stdin); print(r["display_name"]); print(r["address"].get("postcode"))'
```

### 3. Batch-geocode a CSV, politely (Nominatim, 1 req/s)

`addresses.csv` has a column `address`. Rate-limit is non-negotiable.

```bash
python3 - <<'PY'
import csv, time, json, urllib.parse, urllib.request
UA = "sebskills-geocoder/1.0 (seb.duffy@vccp.com)"
BASE = "https://nominatim.openstreetmap.org/search"
out = []
with open("addresses.csv") as f:
    rows = list(csv.DictReader(f))
for row in rows:
    q = urllib.parse.urlencode({"q": row["address"], "format": "jsonv2", "limit": 1})
    req = urllib.request.Request(f"{BASE}?{q}", headers={"User-Agent": UA})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=20))
        lat, lon = (r[0]["lat"], r[0]["lon"]) if r else ("", "")
    except Exception as e:
        lat, lon = "", ""; print("WARN", row["address"], e)
    out.append({**row, "lat": lat, "lon": lon})
    time.sleep(1.1)  # HARD 1 req/s cap — do not remove
with open("addresses_geocoded.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print(f"wrote {len(out)} rows")
PY
```

For **US addresses** skip the rate limit and use the Census batch endpoint instead
(no key, thousands of rows in one POST):

```bash
# CSV must be headerless: id,street,city,state,zip
curl -s --form addressFile=@addresses_us.csv \
  --form benchmark=Public_AR_Current \
  https://geocoding.geo.census.gov/geocoder/locations/addressbatch \
  -o census_out.csv
# single address:
curl -s -G 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress' \
  --data-urlencode 'address=1600 Pennsylvania Ave NW, Washington, DC' \
  -d 'benchmark=Public_AR_Current' -d 'format=json' | python3 -m json.tool
```

Add census tract/block for a point via the **geographies** path
(`.../geographies/coordinates?x=LON&y=LAT&benchmark=Public_AR_Current&vintage=Current_Current&format=json`).

### 4. POIs near a point (Overpass QL)

Cafes within 800m of a lat/lon. `around:RADIUS_m,LAT,LON`.

```bash
curl -s https://overpass-api.de/api/interpreter --data-urlencode 'data=
[out:json][timeout:25];
(
  node["amenity"="cafe"](around:800,51.5076,-0.0994);
  way["amenity"="cafe"](around:800,51.5076,-0.0994);
);
out center tags;' \
  | python3 -c 'import sys,json;
d=json.load(sys.stdin)["elements"];
[print(e.get("tags",{}).get("name","?"), e.get("lat") or e["center"]["lat"], e.get("lon") or e["center"]["lon"]) for e in d]'
```

Swap the tag filter for any OSM key: `["shop"="supermarket"]`, `["railway"="station"]`,
`["leisure"="park"]`. Tag reference: https://wiki.openstreetmap.org/wiki/Map_features .
For an admin boundary polygon, query `relation["boundary"="administrative"]["name"="Camden"]; out geom;`.

### 5. Isochrone — a drive/walk-time catchment (ORS, needs key)

10- and 20-minute drive polygons around a point (ORS wants **lon,lat** order,
`range` in **seconds**):

```bash
curl -s -X POST 'https://api.openrouteservice.org/v2/isochrones/driving-car' \
  -H "Authorization: $ORS_KEY" -H 'Content-Type: application/json' \
  -d '{"locations":[[-0.0994,51.5076]],"range":[600,1200],"range_type":"time"}' \
  -o isochrone.geojson
python3 -c 'import json;g=json.load(open("isochrone.geojson"));print(len(g["features"]),"rings")'
```

Profiles: `driving-car`, `foot-walking`, `cycling-regular`. Use `"range_type":"distance"`
(metres) for a distance catchment. Free-tier isochrone limits: ≤5 locations, ≤10 ranges,
range ≤1h drive / 5h cycle / 20h foot.

### 6. Road distance & travel-time matrix (ORS, needs key)

Durations (s) and distances (m) between all point pairs — one call, not N²:

```bash
curl -s -X POST 'https://api.openrouteservice.org/v2/matrix/driving-car' \
  -H "Authorization: $ORS_KEY" -H 'Content-Type: application/json' \
  -d '{"locations":[[-0.0994,51.5076],[-0.1276,51.5074],[-0.1419,51.5014]],
       "metrics":["duration","distance"]}' \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);print("durations(s)",d["durations"]);print("distances(m)",d["distances"])'
```

Point-to-point directions (GeoJSON route line): `POST /v2/directions/{profile}/geojson`
with the same `{"coordinates":[[lon,lat],[lon,lat]]}` body.

### 7. Straight-line distance — no API needed

Great-circle metres between two lat/lon, when road routing is overkill:

```bash
python3 -c 'import math;
a=(51.5076,-0.0994); b=(51.5014,-0.1419); R=6371000;
p=math.radians; dlat=p(b[0]-a[0]); dlon=p(b[1]-a[1]);
h=math.sin(dlat/2)**2+math.cos(p(a[0]))*math.cos(p(b[0]))*math.sin(dlon/2)**2;
print(round(2*R*math.asin(math.sqrt(h))), "m")'
```

## Verify

- **Geocode sanity**: lat in [-90,90], lon in [-180,180]; reverse-geocode the result and
  confirm the returned country/city matches your input. A silent empty `[]` from Nominatim
  means no match — check spelling / add country context, don't assume (0,0).
- **ORS key works**: `curl -s -o /dev/null -w '%{http_code}' -X POST \
  'https://api.openrouteservice.org/v2/isochrones/driving-car' -H "Authorization: $ORS_KEY" \
  -H 'Content-Type: application/json' -d '{"locations":[[8.68,49.41]],"range":[300]}'`
  → `200` good; `403` bad/missing key; `429` over quota.
- **Coordinate order**: Nominatim/Census return `lat,lon`; ORS and GeoJSON use `lon,lat`.
  Swapped order is the #1 bug — if your point lands in the ocean, you flipped it.
- **Overpass load**: a `429`/`504` means the public instance is busy — back off and retry,
  or add `[timeout:60]`.

## Pitfalls

- **Nominatim bulk = ban.** The public server allows ≤1 req/s, requires a real
  `User-Agent`, and forbids scraping/autocomplete. For real volume run your own
  Nominatim (Docker) or use the Census batch endpoint (US) / a paid provider.
- **lon,lat vs lat,lon** — ORS, Overpass `out geom`, and all GeoJSON are **lon,lat**;
  humans and Nominatim say lat,lon. Convert explicitly at every boundary.
- **ORS quotas are per-endpoint and per-minute** (~2,000–2,500/day, 40/min free). Batch
  matrix calls instead of looping directions; cache isochrones — they rarely change.
- **Census is US-only** and needs a valid `benchmark` (`Public_AR_Current`); it silently
  returns "No Match" for typos rather than erroring.
- **Overpass `around` radius is metres**, and `node` misses features mapped as `way`/
  `relation` (buildings, parks) — include all three and use `out center` to get a point.
- **Don't hardcode secrets** — keep `ORS_KEY` in the environment, never in committed code.
