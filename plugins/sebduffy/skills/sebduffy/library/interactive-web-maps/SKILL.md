---
name: interactive-web-maps
category: data-analysis
description: >
  Render location data as interactive web maps with MapLibre GL + deck.gl —
  choropleths shaded by any metric, store/dealer locators with popups and
  nearest-branch search, point clusters, hexbin/heatmap density, arc flow maps,
  and radius catchments. Free keyless basemaps, output a single self-contained
  HTML you host or screenshot into a deck. Turn a GeoJSON or lat/lon table into
  "colour councils by penetration", "plot 2,000 stores", or "density heatmap" —
  grounded on the real MapLibre 5.x / deck.gl 9.x APIs so layers actually render.
when_to_use:
  - Shading regions/postcodes/councils by a metric (penetration, sales, index) as a choropleth
  - Building a store/dealer/venue locator with markers, popups, geolocate and nearest-branch search
  - Plotting thousands to millions of points (clusters, hexbin, heatmap) that a slippy map must stay smooth on
  - Drawing origin→destination arc/flow maps or radius/ring catchments around sites
  - Producing an interactive map to embed in a landing page, dashboard, or screenshot into a slide
when_not_to_use:
  - Spatial maths (point-in-polygon joins, buffers, dissolves, CRS reprojection) before rendering → use geospatial-analysis
  - Turning addresses/place names into coordinates or POIs → use geocoding-places-api
  - A static, non-interactive shaded map for print → use geospatial-analysis (Matplotlib) or canvas-design
  - A generic chart with no map (bar/line/scatter) → use dataviz
keywords:
  - maplibre
  - deck.gl
  - choropleth
  - store-locator
  - geojson
  - heatmap
  - hexbin
  - catchment
  - basemap
  - webgl
  - flow-map
  - interactive-map
similar_to:
  - geospatial-analysis
  - geocoding-places-api
  - dataviz
inputs_needed: A GeoJSON FeatureCollection (polygons for choropleth, points for locator/heatmap) or a table with lat/lon columns; the property name to colour/size by.
produces: A single self-contained interactive HTML map (MapLibre GL, optional deck.gl overlay) plus a legend; optionally a PNG screenshot for decks.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Interactive Web Maps (MapLibre GL + deck.gl)

Render geodata as interactive maps in the browser. **MapLibre GL** draws the basemap and
native vector layers (fills, lines, symbols) with data-driven styling; **deck.gl** overlays
high-performance WebGL layers (thousands→millions of points, hexbin, arcs) on the same map.
Both are open-source and need no token when you use a free basemap.

## When to use

Choropleths, store locators, density heat/hexbin, flow maps, catchment rings — anything where
the output is an *interactive* map for the web or a screenshot for a deck. Do the spatial maths
(joins, buffers, CRS) first with `geospatial-analysis`; this skill is the render layer.

## Prerequisites

- **No install or key needed for the basics.** Everything runs from CDN in a single HTML file.
  Basemaps used here are free and keyless:
  - CARTO: `https://basemaps.cartocdn.com/gl/positron-gl-style/style.json` (also `dark-matter`, `voyager`)
  - MapLibre demo: `https://demotiles.maplibre.org/style.json`
- Pinned versions (verified on npm, Jul 2026): `maplibre-gl@5.24.0`, `deck.gl@9.3.6`.
- Local generator script: `python3` 3.9+, stdlib only (no deps).
- PNG export for decks needs `preserveDrawingBuffer: true` on the map (already set by the script).
- For a production bundler build instead of CDN: `npm i maplibre-gl @deck.gl/core @deck.gl/layers @deck.gl/aggregation-layers @deck.gl/mapbox`.

## Recipe 1 — Choropleth (native MapLibre, keyless, one file)

Fastest path. `scripts/build_choropleth.py` embeds your GeoJSON inline and writes a portable HTML
with a data-driven `fill-color`, hover popups, legend, and PNG-ready canvas:

```bash
python3 scripts/build_choropleth.py councils.geojson \
    --value penetration --out councils.html \
    --title "Brand penetration %" --ramp viridis --steps 6
# ramps: blues greens oranges purples reds viridis (all colour-blind safe)
```

The core is MapLibre's `interpolate` expression — data-driven paint, computed on the GPU:

```js
map.addSource('data', {type:'geojson', data: GEOJSON});
map.addLayer({id:'fill', type:'fill', source:'data', paint:{
  'fill-color': ['interpolate', ['linear'], ['get','penetration'],
     0,'#f7fbff', 25,'#9ecae1', 50,'#3182bd', 75,'#08519c'],
  'fill-opacity': 0.8 }});
```

Hand-roll this when you need custom breaks (quantile/Jenks), or let the script pick even quantiles.

## Recipe 2 — Store / dealer locator

Markers + popups + browser geolocation + nearest-branch. Load MapLibre from CDN, then:

```js
const map = new maplibregl.Map({container:'map',
  style:'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
  center:[-1.5,52.5], zoom:5});
map.addControl(new maplibregl.NavigationControl(),'top-right');
const geo = new maplibregl.GeolocateControl({trackUserLocation:true});
map.addControl(geo,'top-right');

STORES.forEach(s => {                       // STORES = [{name,lng,lat,phone},...]
  new maplibregl.Marker({color:'#e6320f'})
    .setLngLat([s.lng,s.lat])
    .setPopup(new maplibregl.Popup().setHTML(`<b>${s.name}</b><br>${s.phone}`))
    .addTo(map);
});

// nearest store to a click (haversine, km)
function nearest(lng,lat){
  const R=6371, rad=d=>d*Math.PI/180;
  return STORES.map(s=>{
    const dLat=rad(s.lat-lat), dLng=rad(s.lng-lng);
    const a=Math.sin(dLat/2)**2 + Math.cos(rad(lat))*Math.cos(rad(s.lat))*Math.sin(dLng/2)**2;
    return {...s, km: 2*R*Math.asin(Math.sqrt(a))};
  }).sort((a,b)=>a.km-b.km)[0];
}
```

For 500+ pins use MapLibre's built-in clustering (`cluster:true` on the GeoJSON source) or the
deck.gl `ScatterplotLayer` from Recipe 3 — DOM markers get slow past a few hundred.

## Recipe 3 — deck.gl overlay for scale (points, hexbin, heat, arcs)

Add deck.gl as a MapLibre control so it shares the same camera. The standalone CDN bundle exposes
everything on a global `deck` (verified: `deck.MapboxOverlay`, `deck.GeoJsonLayer`,
`deck.ScatterplotLayer`, `deck.HexagonLayer`, `deck.HeatmapLayer`, `deck.ArcLayer`).

```html
<script src="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.css" rel="stylesheet">
<script src="https://unpkg.com/deck.gl@9.3.6/dist.min.js"></script>
```
```js
const map = new maplibregl.Map({container:'map',
  style:'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  center:[-1.9,52.5], zoom:5});

const overlay = new deck.MapboxOverlay({ interleaved:true, layers:[
  // hexbin density from raw points [{position:[lng,lat]},...]
  new deck.HexagonLayer({id:'hex', data:POINTS, getPosition:d=>d.position,
    radius:2000, elevationScale:20, extruded:true, pickable:true}),
  // OR heatmap:  new deck.HeatmapLayer({id:'heat', data:POINTS, getPosition:d=>d.position, radiusPixels:40}),
  // OR flows:    new deck.ArcLayer({id:'arc', data:FLOWS, getSourcePosition:d=>d.from,
  //                getTargetPosition:d=>d.to, getSourceColor:[0,128,255], getTargetColor:[255,0,128], getWidth:2}),
]});
map.addControl(overlay);
// update reactively (e.g. after a filter):  overlay.setProps({layers:[...]})
```

`GeoJsonLayer` renders polygons/lines/points from GeoJSON with `getFillColor`/`getLineColor`
accessors — use it instead of native fills when you need per-feature JS logic or extrusion.

## Recipe 4 — Catchment rings

Draw radius catchments around sites as GeoJSON circles (approx, degrees), then style as a fill:

```js
function ring(lng,lat,km,steps=64){
  const c=[], dLat=km/111, dLng=km/(111*Math.cos(lat*Math.PI/180));
  for(let i=0;i<=steps;i++){const t=i/steps*2*Math.PI;
    c.push([lng+dLng*Math.cos(t), lat+dLat*Math.sin(t)]);}
  return {type:'Feature',geometry:{type:'Polygon',coordinates:[c]}};
}
```

For **drive-time isochrones** (not straight-line radius) you need a routing API — use
`geocoding-places-api` (or an OpenRouteService/Mapbox isochrone endpoint) to fetch the polygon,
then drop it into the same `addSource`/`addLayer` fill.

## Recipe 5 — Screenshot into a deck

Set `preserveDrawingBuffer:true` on the map (Recipe 1's script does), wait for idle, export:

```js
map.once('idle', () => {
  const png = map.getCanvas().toDataURL('image/png');   // data URI → save/insert
});
```

For headless/batch PNGs, drive the HTML with `webapp-testing` (Playwright) and screenshot the
canvas, then hand the PNG to `pptx`/`docx` for the slide.

## Verify

- Generate and sanity-check the choropleth without a browser:
  ```bash
  python3 scripts/build_choropleth.py test.geojson --value pop_density --out out.html
  grep -q 'preserveDrawingBuffer: true' out.html && grep -q 'positron-gl-style' out.html && echo OK
  ```
- Open `out.html` — regions shade light→dark, hover shows the value, legend matches the ramp.
- deck.gl loaded correctly if `typeof deck.MapboxOverlay === 'function'` in the console.
- Basemap tiles drawing = your network can reach the CARTO/MapLibre CDN (both keyless).

## Pitfalls

- **`interpolate` needs strictly ascending stops.** Duplicate break values throw at load; the
  script nudges duplicates by 1e-6 — do the same if you hand-write breaks from skewed data.
- **Coordinate order is `[lng, lat]`** everywhere in MapLibre/deck.gl (GeoJSON order), not `[lat,lng]`.
  Swapping them silently drops points into the ocean off Africa (0,0).
- **DOM `Marker`s don't scale.** Past ~300 pins switch to clustering or a deck.gl layer, or the
  page janks.
- **`preserveDrawingBuffer` costs performance** — leave it on only when you need PNG export.
- **CARTO basemaps are free but rate-limited/attribution-required** for public production traffic;
  self-host a style + tiles (or a paid provider) for a real launch. Keep the attribution control.
- **CDN `@latest` drifts.** Pin exact versions (as above) so a MapLibre/deck.gl major bump can't
  break a shipped map. deck.gl 9 requires MapLibre ≥ 2; they're compatible here.
- **Antimeridian & huge polygons**: very large fills or arcs crossing ±180° render oddly — split
  geometries upstream in `geospatial-analysis`.
