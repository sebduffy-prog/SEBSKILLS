---
name: quick-dashboard
category: frontend-and-design
description: >-
  Turn CSV, JSON, or pasted rows into ONE self-contained responsive dashboard HTML file — a KPI stat row,
  2–3 Chart.js charts, and one sortable data table, with a tasteful light+dark theme and zero build step.
  Use when someone says "make a dashboard", "visualise this data", "put these numbers on a page",
  "sales/analytics/metrics dashboard", "chart this CSV", or hands you a spreadsheet export and wants it
  readable at a glance. Opinionated defaults, WCAG-AA, awaiting-data placeholders, ends on an approval gate.
when_to_use:
  - User hands you a CSV/JSON/pasted table and wants it shown as stats + charts + a table
  - Someone asks for a "quick dashboard", "metrics page", or "analytics view" with no framework fuss
  - You need a single HTML file that opens with a double-click and works offline (one CDN dep)
  - A stakeholder wants numbers "on a screen by end of day" and iteration speed beats architecture
  - Data is partial or promised-later and you must scaffold now with a believable placeholder state
when_not_to_use:
  - Live/streaming data, auth, drill-downs, or shared server state — build a real app (use frontend-design + web-artifacts-builder)
  - You only need a single chart with no surrounding page — use quick-chart
  - The hard question is which metrics/layout, not the code — use dashboard-information-architecture first
  - Deep Chart.js theming, mixed axes, or 10+ series tuning — use dataviz for the colour/mark system
  - A print or PDF deliverable — use print-editorial-layout
keywords:
  - dashboard
  - chartjs
  - kpi
  - stat-row
  - csv
  - json
  - data-table
  - single-file
  - responsive
  - light-dark
  - no-build
  - metrics
  - analytics
  - visualisation
  - wcag
similar_to:
  - quick-chart
  - dashboard-information-architecture
  - quick-tool
  - quick-landing
  - dataviz
inputs_needed: A data source (CSV/JSON file, pasted rows, or an API shape) plus which fields are the KPIs, the time/category axis, and the table columns. If data is missing, proceed with the awaiting-data placeholder.
produces: One self-contained dashboard.html — KPI stat row, 2–3 Chart.js canvases, a sortable/scrollable table, light+dark theme, loading/empty/error states — plus a browser preview for the approval gate.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Quick Dashboard

Ship a single-file, responsive dashboard from raw data in one pass. This is the "make a good thing
quickly, reliably" lane: **one HTML file, no build, no framework, opinionated defaults, a real quality
floor.** Chart.js is the *only* external dependency — charting genuinely needs a library, so it is the
one justified CDN include.

## When to use

Someone has data (CSV, JSON, pasted rows, an API response) and wants it legible at a glance: headline
numbers, a couple of charts, a table for the detail — done today, opening with a double-click, offline
apart from one script tag. If the data isn't here yet, **don't block on questions** — build the full
frame now and render the "awaiting data" state. Never fabricate numbers into the KPIs.

## Prerequisites

- A modern browser. No Node, no npm, no bundler.
- Chart.js 4.5.1 via CDN (verified UMD build, global `Chart`):
  `https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js`
- Given a CSV? `head -5 data.csv` first to confirm delimiter and header row.

## Opinionated defaults (don't re-litigate)

- **One accent** in a single CSS custom property (`--accent`); charts read it, never hardcode hex in JS.
- **One spacing scale** 4/8/12/16/24/32px, **one radius** 12px, **one shadow**, **one type scale** (system font, 12/14/16/22/32px).
- **Light + dark both shipped**: `prefers-color-scheme` is the signal, `:root[data-theme]` overrides so a toggle wins.
- **At most ONE ui-effect** — a subtle KPI count-up. No parallax, no confetti.
- **Grid, not pixels**: KPI row is `auto-fit,minmax(200px,1fr)`; charts collapse to one column under ~720px.

## Quality floor (non-negotiable, even fast)

- Semantic `<header>`/`<main>`/`<section>` and a real `<table>` with `<th scope>`; sort headers are keyboard-operable `<button>`s with `:focus-visible` rings.
- Explicit **loading**, **empty/awaiting-data**, and **error** states — not just the happy path.
- WCAG-AA contrast in *both* themes; charts carry text legends, never colour alone.
- Wide table scrolls inside its own `overflow-x:auto` box; the page body never scrolls sideways. `prefers-reduced-motion` kills the count-up.

## Steps

1. **Shape the data.** Pick 3–4 KPIs (number + label + optional delta), the chart axis field (time or
   category), the series, and the table columns. Load a CSV with `parseCSV()` below, or paste a JS/JSON array into `DATA`.
2. **Drop it into the starter** — fill `DATA`, `computeKpis`, and the two chart configs.
3. **Keep charts theme-aware.** Chart.js won't pick up CSS-variable changes on a theme flip on its own;
   `applyChartTheme()` reads computed colours and re-renders. Keep it.
4. **Exercise the states.** `DATA = []` → empty; a bad value → error. Confirm both render.
5. **Preview + gate.** Open in a browser, screenshot both themes, invoke `design-approval-gate`, and don't call it done until the user approves.

## The starter (copy, then fill `DATA` / `KPIS` / chart configs)

```html
<!doctype html>
<html lang="en" data-theme="auto">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js"></script>
<style>
  :root{
    --bg:#f7f8fa; --surface:#fff; --text:#111418; --muted:#5b6470; --border:#e4e7ec;
    --accent:#2f6bff; --pos:#0a7c42; --neg:#c0392b; --shadow:0 1px 3px rgba(16,24,40,.08);
    --s1:4px;--s2:8px;--s3:12px;--s4:16px;--s5:24px;--s6:32px; --r:12px;
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  }
  @media (prefers-color-scheme:dark){ :root:not([data-theme=light]){
    --bg:#0e1116;--surface:#161a21;--text:#e7ecf3;--muted:#9aa4b2;--border:#262c36;
    --accent:#5b8bff;--pos:#3ddc84;--neg:#ff6b5e;--shadow:0 1px 3px rgba(0,0,0,.4);
  }}
  :root[data-theme=dark]{
    --bg:#0e1116;--surface:#161a21;--text:#e7ecf3;--muted:#9aa4b2;--border:#262c36;
    --accent:#5b8bff;--pos:#3ddc84;--neg:#ff6b5e;--shadow:0 1px 3px rgba(0,0,0,.4);
  }
  *{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--text);line-height:1.5}
  a{color:var(--accent)} h1{font-size:22px;margin:0} h2{font-size:16px;margin:0 0 var(--s4)}
  :focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
  header{display:flex;align-items:center;justify-content:space-between;gap:var(--s4);padding:var(--s5) var(--s6);border-bottom:1px solid var(--border)}
  main{padding:var(--s6);max-width:1200px;margin:0 auto}
  .kpis{display:grid;gap:var(--s4);grid-template-columns:repeat(auto-fit,minmax(200px,1fr));margin-bottom:var(--s6)}
  .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--r);box-shadow:var(--shadow);padding:var(--s5)}
  .kpi .label{color:var(--muted);font-size:14px} .kpi .num{font-size:32px;font-weight:700;margin:var(--s1) 0}
  .kpi .delta{font-size:12px;font-weight:600} .delta.up{color:var(--pos)} .delta.down{color:var(--neg)}
  .charts{display:grid;gap:var(--s4);grid-template-columns:1fr 1fr;margin-bottom:var(--s6)}
  .chart-wrap{position:relative;height:300px} @media (max-width:720px){.charts{grid-template-columns:1fr}}
  .table-scroll{overflow-x:auto} table{border-collapse:collapse;width:100%;font-size:14px;min-width:480px}
  th,td{text-align:left;padding:var(--s3) var(--s4);border-bottom:1px solid var(--border)}
  th button{all:unset;cursor:pointer;font-weight:600;display:inline-flex;gap:4px}
  .state{text-align:center;color:var(--muted);padding:var(--s6)} .state[hidden]{display:none}
  .toggle{all:unset;cursor:pointer;padding:var(--s2) var(--s3);border:1px solid var(--border);border-radius:8px;font-size:14px}
</style>
</head>
<body>
<header><h1>Sales Dashboard</h1>
  <button class="toggle" id="themeBtn" aria-label="Toggle dark mode">◐ Theme</button></header>
<main>
  <div class="state" id="loading">Loading…</div>
  <div class="state" id="empty" hidden>No data yet — awaiting the export. This is the live frame.</div>
  <div class="state" id="error" hidden role="alert"></div>
  <div id="content" hidden>
    <section class="kpis" id="kpis" aria-label="Key metrics"></section>
    <section class="charts">
      <div class="card"><h2>Revenue over time</h2><div class="chart-wrap"><canvas id="c1"></canvas></div></div>
      <div class="card"><h2>By category</h2><div class="chart-wrap"><canvas id="c2"></canvas></div></div>
    </section>
    <section class="card"><h2>Detail</h2><div class="table-scroll">
      <table id="tbl"><thead></thead><tbody></tbody></table></div></section>
  </div>
</main>
<script>
// ── 1. DATA ─────────────────────────────────────────────────────────────────
// Paste JSON/JS here, OR call parseCSV(text). Set to [] to preview the empty state.
const DATA = [
  {month:"Jan",revenue:42000,orders:310,category:"Retail"},
  {month:"Feb",revenue:47500,orders:352,category:"Retail"},
  {month:"Mar",revenue:51200,orders:401,category:"Wholesale"},
  {month:"Apr",revenue:49800,orders:388,category:"Wholesale"},
  {month:"May",revenue:58300,orders:455,category:"Online"},
  {month:"Jun",revenue:63100,orders:501,category:"Online"},
];
// Minimal, quote-aware CSV → array of objects. Numbers coerced when they look numeric.
function parseCSV(text){
  const rows=[]; let f="",row=[],q=false;
  for(let i=0;i<text.length;i++){const c=text[i];
    if(q){ if(c==='"'){ if(text[i+1]==='"'){f+='"';i++} else q=false } else f+=c }
    else if(c==='"')q=true; else if(c===','){row.push(f);f=""}
    else if(c==='\n'||c==='\r'){ if(f!==""||row.length){row.push(f);rows.push(row);row=[];f=""} if(c==='\r'&&text[i+1]==='\n')i++ }
    else f+=c }
  if(f!==""||row.length){row.push(f);rows.push(row)}
  const head=rows.shift().map(h=>h.trim());
  return rows.map(r=>Object.fromEntries(head.map((h,i)=>{
    const v=(r[i]??"").trim(); const n=Number(v.replace(/[,%$]/g,""));
    return [h, v!=="" && !isNaN(n) ? n : v];})));
}

// ── 2. KPIS + chart builders (edit these to match your fields) ───────────────
function computeKpis(d){
  const rev=d.reduce((s,r)=>s+(+r.revenue||0),0), ord=d.reduce((s,r)=>s+(+r.orders||0),0);
  const half=Math.floor(d.length/2)||1;
  const first=d.slice(0,half).reduce((s,r)=>s+(+r.revenue||0),0);
  const last=d.slice(-half).reduce((s,r)=>s+(+r.revenue||0),0);
  const growth=first?Math.round((last-first)/first*100):0;
  return [
    {label:"Total revenue", value:rev, fmt:v=>"$"+v.toLocaleString()},
    {label:"Orders", value:ord, fmt:v=>v.toLocaleString()},
    {label:"Avg order value", value:ord?rev/ord:0, fmt:v=>"$"+v.toFixed(0)},
    {label:"Revenue growth", value:growth, fmt:v=>v+"%", delta:growth},
  ];
}
function chartConfigs(d,c){
  const byCat={}; d.forEach(r=>byCat[r.category]=(byCat[r.category]||0)+(+r.revenue||0));
  return {
    c1:{type:"line", data:{labels:d.map(r=>r.month),
      datasets:[{label:"Revenue",data:d.map(r=>r.revenue),borderColor:c.accent,
        backgroundColor:c.accent+"22",fill:true,tension:.3,pointRadius:3}]}},
    c2:{type:"bar", data:{labels:Object.keys(byCat),
      datasets:[{label:"Revenue",data:Object.values(byCat),backgroundColor:c.accent}]}},
  };
}

// ── 3. Render engine (states, KPIs, table, theme-aware charts) ───────────────
const $=id=>document.getElementById(id); let charts=[];
function css(name){return getComputedStyle(document.documentElement).getPropertyValue(name).trim();}
function palette(){return {accent:css("--accent"),text:css("--text"),grid:css("--border"),muted:css("--muted")};}

function render(d){
  ["loading","empty","error","content"].forEach(s=>$(s).hidden=true);
  if(!Array.isArray(d)){ $("error").textContent="Data must be an array of rows."; $("error").hidden=false; return; }
  if(d.length===0){ $("empty").hidden=false; return; }
  $("content").hidden=false;

  const kpis=computeKpis(d);
  $("kpis").innerHTML=kpis.map(k=>{
    const dl=k.delta!=null?`<div class="delta ${k.delta>=0?"up":"down"}">${k.delta>=0?"▲":"▼"} ${Math.abs(k.delta)}%</div>`:"";
    return `<div class="card kpi"><div class="label">${k.label}</div>
      <div class="num" data-to="${k.value}">${k.fmt(k.value)}</div>${dl}</div>`;}).join("");
  countUp(kpis);

  const cols=Object.keys(d[0]);
  $("tbl").querySelector("thead").innerHTML="<tr>"+cols.map((col,i)=>
    `<th scope="col"><button data-col="${i}">${col} <span aria-hidden="true">↕</span></button></th>`).join("")+"</tr>";
  drawRows(d,cols);
  $("tbl").querySelectorAll("th button").forEach(b=>b.onclick=()=>{
    const k=cols[+b.dataset.col];
    d=[...d].sort((a,z)=>typeof a[k]==="number"?z[k]-a[k]:String(a[k]).localeCompare(String(z[k])));
    drawRows(d,cols);});

  applyChartTheme(d);
}
function drawRows(d,cols){
  $("tbl").querySelector("tbody").innerHTML=d.map(r=>"<tr>"+cols.map(c=>{
    const v=r[c]; return `<td>${typeof v==="number"?v.toLocaleString():String(v)}</td>`;}).join("")+"</tr>").join("");
}
function applyChartTheme(d){
  const c=palette();
  Chart.defaults.color=c.text; Chart.defaults.borderColor=c.grid; Chart.defaults.font.family=getComputedStyle(document.body).fontFamily;
  charts.forEach(ch=>ch.destroy()); charts=[];
  const cfgs=chartConfigs(d,c);
  for(const [id,cfg] of Object.entries(cfgs)){
    charts.push(new Chart($(id),{...cfg, options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{labels:{color:c.text}}},
      scales:{x:{ticks:{color:c.muted},grid:{color:c.grid}},y:{ticks:{color:c.muted},grid:{color:c.grid}}}}}));
  }
}
function countUp(kpis){
  if(matchMedia("(prefers-reduced-motion:reduce)").matches) return;
  document.querySelectorAll(".kpi .num").forEach((el,i)=>{
    const to=+el.dataset.to, fmt=kpis[i].fmt, t0=performance.now();
    (function step(t){const p=Math.min((t-t0)/700,1); el.textContent=fmt(to*(1-Math.pow(1-p,3)));
      if(p<1)requestAnimationFrame(step);})(t0);});
}

// ── 4. Theme toggle + boot ───────────────────────────────────────────────────
$("themeBtn").onclick=()=>{
  const cur=document.documentElement.getAttribute("data-theme");
  const next=cur==="dark"?"light":cur==="light"?"dark":(matchMedia("(prefers-color-scheme:dark)").matches?"light":"dark");
  document.documentElement.setAttribute("data-theme",next);
  if(!$("content").hidden) applyChartTheme(window.__d);
};
try{ window.__d=DATA; render(DATA); }
catch(e){ $("loading").hidden=true; $("error").textContent="Failed to load: "+e.message; $("error").hidden=false; }
</script>
</body>
</html>
```

## Verify

- **Renders:** KPI row, both charts, and the table appear; numbers count up once.
- **States:** `DATA = []` → "awaiting data"; `DATA = 5` → error banner. Both show cleanly.
- **Theme:** click the toggle — background, cards, *and* chart axes/legend recolour (re-rendered, not stale).
- **Keyboard:** Tab to a table header, Enter/Space sorts; focus ring visible.
- **Responsive:** at phone width charts stack, table scrolls inside its box, body doesn't scroll sideways.
- **Approval:** screenshot light + dark, then run `design-approval-gate` before declaring done.

## Pitfalls

- **Charts don't recolour on theme flip.** Chart.js caches colours at construction — you must `destroy()` and rebuild (what `applyChartTheme()` does), or update each scale/dataset colour then `.update()`.
- **`maintainAspectRatio:true` (the default) fights your layout.** Set it `false` and give the canvas a fixed-height wrapper (`.chart-wrap{height:300px}`), or it grows unboundedly.
- **Hardcoded chart hex** breaks dark mode — read `--accent`/`--text` via `getComputedStyle`.
- **CSV numbers arrive as strings.** `"1,200"` won't sum; the parser strips `, % $` and coerces — keep that or KPIs read `NaN`.
- **`innerHTML` with untrusted cells is XSS.** This starter renders values from a file *you* control; if data is user-supplied, switch table/KPI writes to `textContent`.
- **Reaching for React/a bundler.** One file until routing or shared server state truly forces it — then it's the wrong skill (use `web-artifacts-builder`).
- **Four+ charts, a wall of tiles.** More panels ≠ more insight. Cap at 3 charts + 4 KPIs; if the story needs more, step back through `dashboard-information-architecture`.
