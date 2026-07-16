---
name: geospatial-analysis
category: data-analysis
description: >
  Turn location data into analysis and maps with GeoPandas + leafmap — load
  shapefiles/GeoJSON, build points from lat/lon, reproject CRS, run spatial
  joins (point-in-polygon, nearest), draw buffer catchments, dissolve/aggregate
  to territories, enrich with census/boundary demographics, and render
  choropleths (static Matplotlib or interactive slippy maps). Reach for this
  when you must answer "which region is each customer in", "how many stores
  within 5km", "colour councils by penetration", "sales by catchment", or
  produce a shaded territory/heat map. Wires the real GeoPandas 1.x API so CRS
  and buffer maths are correct, not fabricated.
when_to_use:
  - Assigning points (customers, stores, events) to polygons via spatial join / point-in-polygon
  - Building buffer or ring catchments around sites and counting/summing what falls inside
  - Dissolving or aggregating geometries into territories/regions with summed metrics
  - Enriching a boundary layer with census/demographic data and rendering a choropleth
  - Reprojecting between lat/lon (EPSG:4326) and a metric CRS for distance/area maths
  - Nearest-feature joins (each point to closest depot) with computed distance
when_not_to_use:
  - Turning addresses/place names into coordinates, isochrones, or POI lookups → use geocoding-places-api
  - Pulling the raw census/demographic tables by geography code → use govt-open-data-api
  - Plain non-spatial dataframe wrangling with no geometry → use polars-dataframes or duckdb-analytics
  - SQL-native spatial queries at warehouse scale → use duckdb-analytics with its spatial extension
keywords:
  - geospatial
  - geopandas
  - leafmap
  - shapely
  - spatial-join
  - choropleth
  - crs
  - reproject
  - buffer
  - catchment
  - point-in-polygon
  - dissolve
  - shapefile
  - geojson
  - census
  - territory
similar_to:
  - geocoding-places-api
  - govt-open-data-api
  - polars-dataframes
  - duckdb-analytics
inputs_needed: Point data (CSV with lat/lon or a GeoJSON/shapefile) and/or a boundary layer (councils, postcodes, census tracts); the metric column to map; the country's local CRS if metric distances/areas matter.
produces: A GeoDataFrame with joined/aggregated attributes plus a choropleth or catchment map (PNG via Matplotlib or interactive HTML via leafmap).
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Geospatial Analysis (GeoPandas + leafmap)

Spatial joins, catchments, territory aggregation, census enrichment, and
choropleths. This skill owns the *analysis and map* layer; getting coordinates
in the first place (geocoding, isochrones, POIs) belongs to
`geocoding-places-api`.

## When to use

Reach here once you have location data and need to relate it to areas, measure
distances/areas, or shade a map by a metric. If you only have addresses and no
coordinates yet, geocode first (sibling skill), then come back.

## Prerequisites

No API keys. Pure-Python stack — install into the working venv:

```bash
python3 -m pip install "geopandas>=1.0" shapely pyproj mapclassify \
                       matplotlib contextily leafmap
```

- `mapclassify` is **required** for `scheme=` (Quantiles/EqualInterval/…) in both
  GeoPandas `.plot()` and `leafmap.add_data()`. Without it those calls error.
- `contextily` adds web-tile basemaps under static plots (optional).
- `leafmap` is only needed for interactive HTML maps; skip it for PNG output.
- macOS note: GeoPandas 1.x ships wheels with GEOS/PROJ bundled — no brew/GDAL
  system install needed. On the py3.9 system Python prefer a fresh venv.

### CRS discipline (the #1 source of wrong answers)

- Raw lat/lon is **EPSG:4326** (degrees) — good for storage and web maps, **wrong
  for distance/area** (a "1" means 1 degree, not 1 metre).
- Before any `buffer`, `.length`, `.area`, or `sjoin_nearest(max_distance=…)`,
  reproject to a **metric** CRS with `.to_crs(...)`:
  - UK: `27700` (British National Grid, metres)
  - Continental EU: `3035` (ETRS89-LAEA)
  - US: an appropriate State Plane or UTM zone; global web maps: `3857`
- Reproject results back to `4326` for GeoJSON/web display.

## Recipes

### 1. Build points from a CSV of lat/lon

```python
import geopandas as gpd, pandas as pd
df = pd.read_csv("customers.csv")           # needs lon + lat columns
pts = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["lon"], df["lat"]),
    crs="EPSG:4326",
)
```

### 2. Load a boundary layer (shapefile / GeoJSON / GeoPackage)

```python
areas = gpd.read_file("councils.geojson")   # or .shp, .gpkg
areas = areas.to_crs(4326)                  # normalise CRS
print(areas.crs, len(areas))
```

### 3. Point-in-polygon: which area is each point in?

`sjoin` with `predicate="within"` tags every point with the polygon it sits in.

```python
tagged = pts.sjoin(areas[["area_code", "area_name", "geometry"]],
                   how="left", predicate="within")
# tagged now has area_code/area_name per customer; NaN = outside all polygons
by_area = tagged.groupby("area_name").size().rename("customers")
```

`predicate` options: `intersects` (default), `within`, `contains`, `touches`,
`crosses`, `overlaps`. `how`: `left`/`right`/`inner`.

### 4. Buffer catchment: count/sum what falls within N metres of each site

Reproject to metres, buffer, then join. Buffer radius is in the CRS's units.

```python
sites_m = sites.to_crs(27700)               # UK metres
sites_m["geometry"] = sites_m.buffer(5000)  # 5 km rings (polygons)
pts_m = pts.to_crs(27700)
hits = pts_m.sjoin(sites_m[["site_id", "geometry"]],
                   how="inner", predicate="within")
per_site = hits.groupby("site_id").agg(reach=("value", "sum"),
                                       n=("value", "size"))
```

### 5. Nearest feature with distance (each point → closest depot)

```python
pts_m = pts.to_crs(27700); depots_m = depots.to_crs(27700)
nearest = pts_m.sjoin_nearest(depots_m[["depot_id", "geometry"]],
                              how="left", distance_col="dist_m",
                              max_distance=50000)  # metres; None = no cap
```

### 6. Dissolve into territories with aggregated metrics

Merge small areas into regions and sum their numbers in one pass.

```python
areas = areas.merge(sales_df, on="area_code")          # attribute join first
territories = areas.dissolve(by="region",
                             aggfunc={"sales": "sum", "population": "sum"})
territories["sales_per_capita"] = (
    territories["sales"] / territories["population"])
```

### 7. Census enrichment: attach demographics to a metric layer

If your boundaries and the census tables share a code, use a plain `merge`.
If they only share geometry (different boundary sets), spatial-join instead:

```python
# same code → attribute join
enriched = areas.merge(census[["area_code", "median_age", "population"]],
                       on="area_code", how="left")
# different boundaries → area-weighted overlay (needs metric CRS)
overlaid = gpd.overlay(areas.to_crs(27700), census.to_crs(27700),
                       how="intersection")
```

### 8a. Static choropleth (PNG) with Matplotlib

```python
import matplotlib.pyplot as plt
ax = enriched.plot(column="sales_per_capita", scheme="Quantiles", k=5,
                   cmap="viridis", legend=True, edgecolor="white",
                   linewidth=0.3, figsize=(9, 11),
                   legend_kwds={"title": "Sales / capita"},
                   missing_kwds={"color": "lightgrey", "label": "no data"})
ax.set_axis_off()
plt.savefig("choropleth.png", dpi=150, bbox_inches="tight")
```

Add a basemap under it with `contextily` (data must be in `3857`):

```python
import contextily as cx
ax = enriched.to_crs(3857).plot(column="sales_per_capita", alpha=0.7,
                                scheme="Quantiles", cmap="magma", legend=True)
cx.add_basemap(ax, source=cx.providers.CartoDB.Positron)
```

### 8b. Interactive choropleth (HTML) with leafmap

```python
import leafmap
m = leafmap.Map(center=[54.5, -3], zoom=6)
m.add_data(enriched, column="sales_per_capita", scheme="Quantiles",
           cmap="Blues", legend_title="Sales / capita")
m.to_html("map.html")            # self-contained interactive map
```

For a quick unclassified overlay use `m.add_gdf(gdf, layer_name="sites")`.
Both `.plot(scheme=...)` and `add_data(scheme=...)` require `mapclassify`.

## Verify

```bash
python3 - <<'PY'
import geopandas as gpd
from shapely.geometry import Point, Polygon
# point-in-polygon sanity
poly = gpd.GeoDataFrame({"name":["box"]},
        geometry=[Polygon([(0,0),(0,2),(2,2),(2,0)])], crs=4326)
pts  = gpd.GeoDataFrame({"id":[1,2]},
        geometry=[Point(1,1), Point(5,5)], crs=4326)
j = pts.sjoin(poly, how="left", predicate="within")
assert j.loc[j.id==1,"name"].iloc[0]=="box"          # inside
assert j.loc[j.id==2,"name"].isna().iloc[0]          # outside
# metric buffer area ≈ pi r^2 (reproject to metres first)
r = gpd.GeoSeries([Point(-0.1,51.5)], crs=4326).to_crs(27700).buffer(1000)
assert 3.0e6 < r.area.iloc[0] < 3.3e6                 # ~pi*1000^2
print("OK", gpd.__version__)
PY
```

## Pitfalls

- **Buffering in EPSG:4326.** Degrees are not metres and vary with latitude —
  always `.to_crs()` to a metric CRS before `buffer`/`area`/`length`, then back.
- **CRS mismatch in sjoin.** Both frames must share a CRS or the join silently
  mis-locates. Call `.to_crs()` on both to the same code first.
- **`predicate="within"` vs `"contains"` direction.** `within` = left-inside-right;
  swap the frames or the predicate if the join comes back empty.
- **`scheme=` errors with no traceback hint.** That means `mapclassify` is
  missing — `pip install mapclassify`.
- **Duplicated rows after sjoin.** A point on a shared boundary can match two
  polygons; dedupe on the point id or use `predicate="within"` with clean geoms.
- **Invalid geometries** (self-intersections) break overlay/dissolve — repair with
  `gdf.geometry = gdf.geometry.make_valid()` (GeoPandas 1.x / Shapely 2.x).
- **Huge shapefiles** are slow to plot — `gdf.simplify(tolerance, preserve_topology=True)`
  before rendering, and read only needed columns.
- **leafmap not installed** on a headless box is fine — fall back to the
  Matplotlib PNG recipe (8a); leafmap is only for interactive HTML.
