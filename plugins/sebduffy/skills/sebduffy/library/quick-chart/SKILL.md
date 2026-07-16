---
name: quick-chart
category: frontend-and-design
description: >-
  Render ONE correct chart from a dataset in a single self-contained HTML file — auto-pick the right chart
  type (bar/line/scatter/doughnut) from the data shape, apply a colourblind-safe palette, wire a light+dark
  theme, and add a screen-reader data-table fallback. Use when someone says "chart this", "graph these
  numbers", "plot this CSV", "make a bar/line/pie chart", or hands you a column of values and wants a picture.
  The most granular, most repeated viz ask. Opinionated defaults, WCAG-AA, awaiting-data state, approval gate.
when_to_use:
  - Someone hands you rows/values and wants exactly ONE chart, not a page or dashboard
  - You must pick the right chart type FROM the data and don't want to hand-tune a library
  - A single HTML file that opens on double-click and works offline (one CDN dep) is the deliverable
  - Numbers need to be legible + accessible fast — colourblind-safe, keyboard-reachable, AA contrast
  - Data is partial or promised-later and you must scaffold the chart now with a placeholder state
when_not_to_use:
  - You need stat tiles + multiple charts + a table on one page — use quick-dashboard
  - The hard question is the colour/mark SYSTEM across many charts — use dataviz first
  - You only need to validate a palette's contrast/colourblindness — use colorblind-safe-palettes
  - Live/streaming/drill-down/interactive analytics — build a real app with frontend-design
  - A print or PDF chart deliverable — use print-editorial-layout
keywords:
  - chart
  - chartjs
  - graph
  - plot
  - bar-chart
  - line-chart
  - scatter
  - doughnut
  - csv
  - single-file
  - colorblind-safe
  - light-dark
  - accessible
  - no-build
  - visualisation
similar_to:
  - quick-dashboard
  - dataviz
  - colorblind-safe-palettes
  - dashboard-information-architecture
  - quick-tool
inputs_needed: A dataset (CSV/JSON/pasted rows) plus which column is the category/x-axis and which is the value/series. If the chart type is obvious from the shape, pick it; if data is missing, render the awaiting-data placeholder.
produces: One self-contained chart.html — a single responsive Chart.js canvas with a colourblind-safe palette, light+dark theme, screen-reader data-table fallback, and loading/empty/error states — plus a browser preview for the approval gate.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Quick Chart

Turn a dataset into **one correct, accessible chart** in a single HTML file. This skill lives in the
"make a good thing quickly, reliably" lane: **one file, no build, no framework, opinionated defaults,
a real quality floor.** Chart.js is the *one* justified CDN dependency; the SVG recipe at the bottom
needs zero dependencies.

## When to use

Someone has a handful of numbers — a CSV column, a JSON array, rows pasted into chat — and wants a
*picture*, not a report. One chart. Your job: (1) pick the **right type** from the data shape,
(2) colour it so everyone can read it, (3) ship a file that opens on double-click. If the data isn't
here yet, **don't block on questions** — render the "awaiting data" state; never fabricate values.

## Prerequisites

- A modern browser. No Node, no npm, no bundler.
- Chart.js 4.5.1 via CDN (verified UMD build, global `Chart`):
  `https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js`
- Know two things: which field is the **category / x-axis**, and which is the **value(s)**.

## Step 1 — Pick the chart type (deterministic)

Don't guess. Run the shape through this ladder top-to-bottom, first match wins:

| Data shape | Chart type | Why |
|---|---|---|
| x is a **date / ordered sequence**, y is numeric | **line** | trend over time reads as slope |
| **part-to-whole**, ≤ 5 slices, sums to a meaningful 100% | **doughnut** | proportion of a whole; never a pie |
| part-to-whole with > 5 categories | **bar** | humans can't compare > 5 arcs |
| one category column + one value | **bar** (horizontal if > 8 bars or long labels) | length is the most precise encoding |
| **two numeric** columns (correlation) | **scatter** | position on 2 axes shows relationship |
| distribution of one numeric column | **bar** (as histogram, pre-binned) | shape of spread |

Baked in: **bar beats pie**, **doughnut over pie** always, **horizontal bar** when labels are long or
bars exceed ~8, value axes start at **zero**, and **sort bars by value** unless the category has a natural order.

## Step 2 — Copy the starter, drop in your data

One file. Replace the `RAW` array and the `PICK` block; everything else is done.

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chart</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
<style>
  :root{
    --bg:#ffffff; --fg:#1a1d21; --muted:#5b6470; --grid:#e7eaee; --card:#ffffff; --border:#e2e6ea;
    --accent:#3b6ef5; --focus:#3b6ef5;
  }
  @media (prefers-color-scheme:dark){
    :root{ --bg:#12151a; --fg:#e9edf2; --muted:#9aa4b1; --grid:#262b33; --card:#171b21; --border:#262b33; }
  }
  *{box-sizing:border-box}
  body{margin:0;font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg);display:grid;place-items:center;min-height:100vh;padding:24px}
  .card{width:min(760px,100%);background:var(--card);border:1px solid var(--border);border-radius:14px;padding:24px 24px 12px}
  h1{margin:0 0 4px;font-size:1.15rem} p.sub{margin:0 0 16px;color:var(--muted);font-size:.9rem}
  .wrap{position:relative;height:min(52vh,420px)}
  .state{display:none;place-items:center;height:100%;color:var(--muted);text-align:center;border:1px dashed var(--border);border-radius:10px}
  .state.show{display:grid}
  :where(a,button,canvas):focus-visible{outline:3px solid var(--focus);outline-offset:3px;border-radius:6px}
  table.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
</style>
</head>
<body>
<main class="card">
  <h1 id="title">Revenue by region</h1>
  <p class="sub" id="subtitle">FY2026 · GBP thousands</p>

  <div class="wrap">
    <div class="state" id="loading" role="status">Loading…</div>
    <div class="state" id="empty">No data yet — awaiting the dataset. This is a placeholder frame.</div>
    <div class="state" id="error" role="alert"></div>
    <!-- Chart.js draws here; role+aria-label make the image legible to AT, table.sr is the real fallback -->
    <canvas id="chart" role="img" aria-label="Chart of revenue by region"></canvas>
  </div>

  <!-- Screen-reader + no-JS data table. Always present, visually hidden. -->
  <table class="sr" id="dataTable"><caption>Data table for the chart above</caption></table>
</main>

<script>
// 1) YOUR DATA — array of {label, value}. Leave [] to see the awaiting-data state.
const RAW = [
  {label:"North",  value:412},
  {label:"South",  value:389},
  {label:"Midlands", value:501},
  {label:"Scotland", value:277},
];

// 2) PICK — set the type per Step 1, or leave "auto" to let the heuristic choose.
const PICK = "auto"; // "auto" | "bar" | "line" | "doughnut" | "scatter"

// Colourblind-safe categorical palette (Okabe–Ito; distinguishable for all common CVD types).
const PALETTE = ["#0072b2","#e69f00","#009e73","#cc79a7","#d55e00","#56b4e9","#f0e442","#000000"];

function chooseType(rows){
  if (PICK !== "auto") return PICK;
  const isDate = rows.length && !isNaN(Date.parse(rows[0].label));
  if (isDate) return "line";
  if (rows.length <= 5) return "doughnut";
  return "bar";
}

const cssVar = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function show(id){ ["loading","empty","error"].forEach(s=>document.getElementById(s).classList.remove("show"));
  document.getElementById("chart").style.visibility = id ? "hidden":"visible";
  if(id) document.getElementById(id).classList.add("show"); }

function render(){
  try{
    const rows = Array.isArray(RAW) ? RAW.filter(r=>r && r.label!=null && !isNaN(+r.value)) : [];
    if(!rows.length){ show("empty"); buildTable([]); return; }
    show(null);
    const type = chooseType(rows);
    const horizontal = type==="bar" && (rows.length>8 || rows.some(r=>String(r.label).length>12));
    if(type==="bar") rows.sort((a,b)=>b.value-a.value); // sort by value for comparison bars
    const single = type==="bar" || type==="line";
    const colors = rows.map((_,i)=>PALETTE[i%PALETTE.length]);
    const data = {
      labels: rows.map(r=>r.label),
      datasets: [{
        label: document.getElementById("subtitle").textContent,
        data: rows.map(r=>+r.value),
        backgroundColor: single ? cssVar("--accent") : colors,
        borderColor: type==="line" ? cssVar("--accent") : "transparent",
        borderWidth: type==="line" ? 2 : 0,
        tension: 0.25, pointRadius: 3, fill:false,
        borderRadius: type==="bar" ? 6 : 0,
      }]
    };
    const isCircular = type==="doughnut";
    new Chart(document.getElementById("chart"), {
      type,
      data,
      options: {
        responsive:true, maintainAspectRatio:false,
        indexAxis: horizontal ? "y" : "x",
        animation:{duration:600},          // the ONE ui-effect: a gentle draw-in
        color: cssVar("--fg"),
        plugins:{
          legend:{ display:isCircular, position:"right", labels:{color:cssVar("--fg")} },
          tooltip:{ backgroundColor:cssVar("--fg"), bodyColor:cssVar("--bg"), titleColor:cssVar("--bg") },
        },
        scales: isCircular ? {} : {   // value axis begins at zero so bar length ∝ magnitude
          x:{ grid:{color:cssVar("--grid")}, ticks:{color:cssVar("--muted")}, beginAtZero:true },
          y:{ grid:{color:cssVar("--grid")}, ticks:{color:cssVar("--muted")}, beginAtZero:true },
        }
      }
    });
    buildTable(rows);
  }catch(e){
    const el=document.getElementById("error"); el.textContent="Couldn’t render: "+e.message; show("error");
  }
}

function buildTable(rows){
  const t=document.getElementById("dataTable");
  t.innerHTML="<caption>Data table for the chart above</caption>"+
    "<thead><tr><th scope=col>Category</th><th scope=col>Value</th></tr></thead><tbody>"+
    rows.map(r=>`<tr><th scope=row>${r.label}</th><td>${r.value}</td></tr>`).join("")+"</tbody>";
}

render();
// Re-render on OS theme flip so grid/label colours stay correct.
matchMedia("(prefers-color-scheme:dark)").addEventListener("change", render);
</script>
</body>
</html>
```

## Step 3 — Awaiting-data mode

No numbers yet? Ship the file **as-is with `const RAW = [];`** — the empty state renders, the frame,
title, and table scaffold are present, nothing is invented. Fill `RAW` when the data lands.

## Verify

- **Type is right:** re-check Step 1 against the shape — a time axis must be a line, not bars.
- **Contrast (AA):** labels vs background ≥ 4.5:1 (the tokens pass in both themes; recolour → `accessible-contrast-checker`).
- **Colourblind-safe:** categorical series use Okabe–Ito; never rely on colour alone — keep the legend/labels (`colorblind-safe-palettes`).
- **Keyboard + AT:** `Tab` reaches the canvas (`role="img"` + `aria-label`); the visually-hidden `<table>` carries the numbers for screen readers and no-JS.
- **States:** `RAW=[]` → empty shows; a bad `value:"x"` row drops, not crashes.
- Open in a browser (or the `webapp-testing` skill) and screenshot before you call it done.

## Ship: design-approval-gate

**Don't mark done without a preview.** Open `chart.html`, screenshot it (or share the file/URL), confirm
the type, palette, and labels read correctly in **both** light and dark, and get **explicit approval** —
"yes, ship it" — before finishing. See the `design-approval-gate` skill.

## Pitfalls

- **Pie charts and 3-D anything.** Never. Doughnut ≤ 5 slices, else bar.
- **Truncated value axes.** Bars/histograms must start at zero or they lie about magnitude.
- **Colour as the only signal.** Keep text labels/legend; the palette is a bonus, not the message.
- **Rainbow single-series bars.** One series = one colour (`--accent`); multi-colour only for categorical/part-to-whole.
- **Bare `<canvas>` with no `<table>` fallback** — invisible to screen readers. Non-negotiable.
- **A second dependency.** Chart.js is the only allowed include; if you need more, you've outgrown this → `quick-dashboard`.
- **Pinning `@latest`.** Pin `@4.5.1` so a future major (v5) can't silently break the config.

### Zero-dependency alternative (pure SVG)

When the host forbids external scripts and the chart is a simple static bar/line (≤ ~12 bars), drop
an inline `<svg viewBox="0 0 400 220" role="img" aria-label="…">` into `.wrap` instead of the canvas:
generate `<rect>`/`<text>` in JS (`x=index*step`, `height ∝ value/max*180`, `y=190-height`), fill every
bar `var(--accent)`, and keep the same visually-hidden `<table>`. Reach for Chart.js the moment you
need tooltips, legends, scatter, or responsive re-layout.
