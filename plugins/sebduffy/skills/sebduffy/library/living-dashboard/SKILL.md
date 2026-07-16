---
name: living-dashboard
category: recipes
description: >-
  Recreate a Hex / Observable-style self-updating analytics app as a COMBO of existing SEBSKILLS —
  pull live public data, transform it in-process, decide the layout, ship a single-file dashboard, then
  host it and wire a scheduled refresh so the numbers update themselves. Use when someone asks for a
  "live dashboard", "self-updating dashboard", "Observable/Hex-style data app", "auto-refreshing
  metrics page", "notebook that redeploys itself", or an analytics view that stays current without a
  human re-running it. Green feasibility — every step is a local library skill; "self-updating" is a
  cron, not magic.
when_to_use:
  - Someone wants a dashboard that refreshes itself on a schedule from a live public data source
  - You are asked to recreate a Hex / Observable / Streamlit-style data app without that SaaS
  - Metrics must stay current (daily/hourly) with no analyst re-running a notebook
  - A stakeholder wants "the FRED / weather / market numbers on a page that never goes stale"
  - You want a repeatable data → transform → layout → build → deploy → cron pipeline
when_not_to_use:
  - You only need a one-off static dashboard from data you already have — just use quick-dashboard
  - You only need to fetch the data, not display it — use connect-public-api or market-data-api alone
  - You only need the transform step (SQL/dataframe wrangle) — use duckdb-analytics or polars-dataframes
  - Live per-user auth, drill-downs, or writes back to a database — that is a real app, not this combo
keywords:
  - living-dashboard
  - self-updating
  - hex
  - observable
  - streamlit
  - live-data
  - cron
  - analytics-app
  - dashboard
  - duckdb
  - polars
  - public-api
  - scheduled-refresh
  - single-file
  - combo
  - recipe
similar_to:
  - quick-dashboard
  - dashboard-information-architecture
  - duckdb-analytics
  - polars-dataframes
  - market-data-api
  - connect-public-api
inputs_needed: A live data source (a public/REST API URL + docs, or a market/macro series id) and any free API key it needs; which fields are the KPIs, the time/category axis, and the table columns; a refresh cadence (e.g. daily 06:00 UTC); and a host target (static host or Railway).
produces: A single self-contained dashboard.html plus a small fetch+transform script and a scheduled job (GitHub Actions cron or Railway) that rebuilds and redeploys the file, so the hosted page stays current without manual reruns.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Living Dashboard

Chain six library skills into one pipeline that behaves like a Hex/Observable data app: it fetches live
data, transforms it, renders a legible dashboard, hosts it, and **re-runs itself on a schedule** so the
page is always current. Nothing here is a wrapper around a paid SaaS — it is real skills stitched with a
cron.

## What it recreates

A **self-updating analytics app** in the mould of **Hex**, **Observable**, or **Streamlit** — the class
of tool where a data source feeds a notebook, the notebook renders KPIs + charts + a table, and a
schedule keeps it fresh. We reproduce the *behaviour* (live → transform → present → auto-refresh), not
their hosted editor or their collaboration features.

## Feasibility

**Green.** Every step is a local SEBSKILLS skill and runs on this machine with no GPU and no paid model.

The single honest caveat is at **Step 1**: some live sources need a **free API key** (e.g. FRED,
OpenWeather). That is a free credential, not a paid dependency — so this stays green, not amber. If your
chosen source is fully open (World Bank, many govt-open-data feeds), there is no key at all. The
"self-updating" property is delivered by a **cron** (GitHub Actions or Railway), not by any live
server-push — be honest about that: the page is rebuilt on a cadence, it is not a websocket stream.

## The combo

1. **`connect-public-api`** (or **`market-data-api`** for finance/macro) — fetch the live source
   robustly: right auth, pagination, 429/Retry-After handling, retries with backoff. Output: raw JSON
   pulled into a tidy shape. Use `market-data-api` when the source is FRED/SEC/World Bank/FX/crypto;
   use `connect-public-api` for any other REST URL.
2. **`duckdb-analytics`** (or **`polars-dataframes`**) — transform the raw pull into the exact rows the
   dashboard needs: aggregate, window, date-align, compute the KPI deltas. DuckDB when you want SQL over
   files; Polars when you want a fast in-memory dataframe. Output: a small clean table (CSV/JSON/parquet).
3. **`dashboard-information-architecture`** — decide *what goes where*: which numbers are the KPI row,
   which series are the charts, which columns are the table, and the reading order. Output: a layout
   spec. Do this before building so the design question is settled, not improvised.
4. **`quick-dashboard`** — build ONE self-contained `dashboard.html` from the transformed table +
   layout spec: KPI stat row, 2–3 Chart.js canvases, a sortable table, light+dark theme, no build step.
   Ends on its own approval gate. Output: the artifact.
5. **`web-artifacts-builder`** — host the single file so it has a stable URL (static host or bundle).
   Output: a live link people can open.
6. **`github-actions-pipelines`** — the "living" part: a scheduled workflow (cron) that re-runs steps
   1→2→4 and redeploys the HTML on your cadence. Output: a `.github/workflows/refresh.yml` that keeps
   the hosted page current. (On Railway, use `use-railway` with a scheduled/cron service instead.)

## Prerequisites

- Python 3 with the fetch/transform stack the sub-skills use (httpx + tenacity; duckdb or polars).
- A modern browser to open the built dashboard. No Node/bundler needed for `quick-dashboard` itself.
- Chart.js 4.5.1 via CDN (the one justified dependency `quick-dashboard` already declares).
- The free API key for your source, stored as a secret (env var / GitHub Actions secret) — never inline.
- A host: a static host via `web-artifacts-builder`, or a Railway project via `use-railway`.

## Run it

1. **Pick the source and settle the layout.** Invoke `dashboard-information-architecture` with the
   source's field list to lock KPIs, axes, and table columns. Keep its spec — Step 4 consumes it.
2. **Write the fetch step.** Invoke `connect-public-api` (or `market-data-api`) to produce
   `fetch.py` that returns raw records. Read the key from `os.environ`, not the file.
3. **Write the transform step.** Invoke `duckdb-analytics` (or `polars-dataframes`) to produce
   `transform.py` that turns raw records into `data.json` — exactly the KPIs/series/rows the layout
   spec named. This file is the single contract between data and view.
4. **Build the dashboard.** Invoke `quick-dashboard` with `data.json` + the layout spec to emit
   `dashboard.html`. Pass its approval gate before going further.
5. **Deploy once, by hand.** Invoke `web-artifacts-builder` to host `dashboard.html` and capture the
   stable URL. Confirm it opens and renders real numbers.
6. **Make it self-updating.** Invoke `github-actions-pipelines` to write `refresh.yml`: `on.schedule`
   cron at your cadence → run `fetch.py` → `transform.py` → rebuild `dashboard.html` → redeploy. Store
   the API key as an Actions secret. (Railway alternative: `use-railway` cron service running the same
   three scripts.)

Result: opening the URL always shows current data because the workflow rebuilt the file on the last
tick — the Hex/Observable behaviour, from local skills plus a scheduler.

## Verify

- **Cold build works:** `python fetch.py && python transform.py` produces a non-empty `data.json`, and
  the dashboard renders real KPIs (not the awaiting-data placeholder).
- **Contract holds:** every field named in the layout spec exists in `data.json` — the view never
  silently drops a series.
- **The cron actually fires:** trigger the workflow manually (`workflow_dispatch`) once, confirm it
  redeploys, and confirm the scheduled run appears in the Actions log after the first tick.
- **Freshness is visible:** the dashboard stamps a "data as of <UTC>" line so staleness is obvious at a
  glance — if the timestamp stops advancing, the refresh broke.
- **Secret hygiene:** the API key is only in the secret store; `grep` the repo to prove it is not inline.

## Pitfalls

- **Calling it "real-time."** It is not — it is cron-fresh. Say so. If someone needs sub-minute live
  data this recipe is the wrong shape; that is a streaming app, not a rebuilt static file.
- **Rate limits on every tick.** A too-aggressive cron can burn your free quota. Match the cadence to
  the source's real update frequency (FRED macro series update daily/monthly, not hourly).
- **Fetch failures poisoning the page.** If Step 1 fails, do not redeploy an empty dashboard — the
  workflow should fail loudly and leave the last-good file in place. Let `connect-public-api`'s retry
  logic absorb transient 429s first.
- **Skipping Step 3.** Building the dashboard before deciding the layout produces a generic chart dump.
  `dashboard-information-architecture` is cheap and settles the one hard question.
- **Data/view contract drift.** If you rename a field in `transform.py`, the dashboard silently loses
  it. Keep `data.json` as the explicit contract and verify it every build.
- **Over-reaching the combo.** The moment you need auth, per-user views, or write-back, stop chaining
  and build a real app — this recipe deliberately stays in the single-file, read-only lane.
