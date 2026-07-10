#!/usr/bin/env python3
"""Turn a GeoJSON FeatureCollection into a self-contained MapLibre choropleth HTML.

Native MapLibre data-driven `fill-color` (no API key, no deck.gl needed). The GeoJSON
is embedded inline so the output HTML is a single portable file. `preserveDrawingBuffer`
is on so you can screenshot/export the canvas to PNG for a deck.

Usage:
  python3 build_choropleth.py DATA.geojson --value pop_density --out map.html \
      [--title "Population density"] [--ramp blues] [--steps 6]

Python 3.9+, stdlib only.
"""
import argparse
import json
import sys

# ColorBrewer-style sequential ramps (light -> dark), colour-blind safe.
RAMPS = {
    "blues": ["#f7fbff", "#c6dbef", "#9ecae1", "#6baed6", "#3182bd", "#08519c"],
    "greens": ["#f7fcf5", "#c7e9c0", "#a1d99b", "#74c476", "#31a354", "#006d2c"],
    "oranges": ["#fff5eb", "#fdd0a2", "#fdae6b", "#fd8d3c", "#e6550d", "#a63603"],
    "purples": ["#fcfbfd", "#dadaeb", "#bcbddc", "#9e9ac8", "#756bb1", "#54278f"],
    "viridis": ["#440154", "#414487", "#2a788e", "#22a884", "#7ad151", "#fde725"],
    "reds": ["#fff5f0", "#fcbba1", "#fc9272", "#fb6a4a", "#de2d26", "#a50f15"],
}


def numeric_values(features, prop):
    vals = []
    for f in features:
        v = (f.get("properties") or {}).get(prop)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            vals.append(float(v))
    return vals


def quantile_stops(vals, ramp, steps):
    """Even quantile breaks -> list of [value, color] pairs for `interpolate`."""
    s = sorted(vals)
    n = len(s)
    colors = ramp[:steps] if len(ramp) >= steps else ramp
    steps = len(colors)
    stops = []
    for i, color in enumerate(colors):
        q = i / (steps - 1) if steps > 1 else 0
        idx = min(n - 1, int(round(q * (n - 1))))
        stops.append([s[idx], color])
    # `interpolate` needs strictly ascending input stops; nudge duplicates.
    for i in range(1, len(stops)):
        if stops[i][0] <= stops[i - 1][0]:
            stops[i][0] = stops[i - 1][0] + 1e-6
    return stops


def bounds_of(features):
    xs, ys = [], []

    def walk(coords):
        if coords and isinstance(coords[0], (int, float)):
            xs.append(coords[0])
            ys.append(coords[1])
        else:
            for c in coords or []:
                walk(c)

    for f in features:
        geom = f.get("geometry") or {}
        walk(geom.get("coordinates"))
    if not xs:
        return [-0.2, 51.4, 0.05, 51.6]
    return [min(xs), min(ys), max(xs), max(ys)]


TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<title>__TITLE__</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.css" rel="stylesheet">
<script src="https://unpkg.com/maplibre-gl@5.24.0/dist/maplibre-gl.js"></script>
<style>
  html,body{margin:0;height:100%;font-family:system-ui,sans-serif}
  #map{position:absolute;inset:0}
  .legend{position:absolute;bottom:24px;left:12px;background:#fff;padding:10px 12px;
    border-radius:8px;box-shadow:0 1px 6px rgba(0,0,0,.3);font-size:12px;line-height:1.5}
  .legend h4{margin:0 0 6px;font-size:12px}
  .legend .row{display:flex;align-items:center;gap:6px}
  .legend .sw{width:14px;height:14px;border-radius:2px;display:inline-block}
</style></head><body>
<div id="map"></div>
<div class="legend"><h4>__TITLE__</h4><div id="legend-rows"></div></div>
<script>
const DATA = __DATA__;
const STOPS = __STOPS__;        // [[value,color],...]
const BOUNDS = __BOUNDS__;      // [minx,miny,maxx,maxy]
const VALUE_PROP = "__PROP__";

const map = new maplibregl.Map({
  container: 'map',
  style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json', // free, no key
  bounds: BOUNDS, fitBoundsOptions: {padding: 40},
  preserveDrawingBuffer: true   // required to export the canvas to PNG
});
map.addControl(new maplibregl.NavigationControl(), 'top-right');

// data-driven fill: interpolate the metric across the colour stops
const fillColor = ['interpolate', ['linear'], ['coalesce', ['get', VALUE_PROP], STOPS[0][0]]];
STOPS.forEach(s => { fillColor.push(s[0], s[1]); });

map.on('load', () => {
  map.addSource('data', {type: 'geojson', data: DATA});
  map.addLayer({id:'fill', type:'fill', source:'data',
    paint:{'fill-color': fillColor, 'fill-opacity':0.8}});
  map.addLayer({id:'line', type:'line', source:'data',
    paint:{'line-color':'#ffffff', 'line-width':0.5}});

  const popup = new maplibregl.Popup({closeButton:false});
  map.on('mousemove','fill', e => {
    const p = e.features[0].properties;
    const v = p[VALUE_PROP];
    popup.setLngLat(e.lngLat)
      .setHTML('<b>'+VALUE_PROP+':</b> '+(v==null?'n/a':v)).addTo(map);
    map.getCanvas().style.cursor='pointer';
  });
  map.on('mouseleave','fill', () => { popup.remove(); map.getCanvas().style.cursor=''; });
});

// legend
const rows = document.getElementById('legend-rows');
STOPS.forEach(s => {
  const d=document.createElement('div'); d.className='row';
  d.innerHTML='<span class="sw" style="background:'+s[1]+'"></span>'+
    Math.round(s[0]*100)/100;
  rows.appendChild(d);
});
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("geojson")
    ap.add_argument("--value", required=True, help="numeric property to colour by")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--ramp", default="blues", choices=sorted(RAMPS))
    ap.add_argument("--steps", type=int, default=6)
    a = ap.parse_args()

    with open(a.geojson) as fh:
        gj = json.load(fh)
    feats = gj.get("features")
    if not isinstance(feats, list) or not feats:
        sys.exit("error: no features found in GeoJSON")

    vals = numeric_values(feats, a.value)
    if not vals:
        sys.exit(f"error: no numeric values for property '{a.value}'")

    stops = quantile_stops(vals, RAMPS[a.ramp], max(2, a.steps))
    html = (
        TEMPLATE.replace("__TITLE__", a.title or a.value)
        .replace("__DATA__", json.dumps(gj))
        .replace("__STOPS__", json.dumps(stops))
        .replace("__BOUNDS__", json.dumps(bounds_of(feats)))
        .replace("__PROP__", a.value)
    )
    with open(a.out, "w") as fh:
        fh.write(html)
    print(f"wrote {a.out}  ({len(feats)} features, {len(vals)} with values, "
          f"range {min(vals):.2f}-{max(vals):.2f})")


if __name__ == "__main__":
    main()
