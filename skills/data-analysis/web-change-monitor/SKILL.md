---
name: web-change-monitor
category: data-analysis
description: >
  Watch web pages for MEANINGFUL changes, not raw byte churn. Fetch a URL, extract a stable
  signal (visible text, a JSON key, or a CSS-selected region), diff it against a stored
  baseline, threshold on a change ratio so ads/timestamps/CSRF-tokens don't trip it, advance
  the baseline, and POST a webhook when it's significant. Use for price/stock trackers,
  policy/ToS/pricing-page watches, competitor-page monitoring, "tell me when this changes"
  polling, and scheduled cron/launchd change alerts. Ports concepts from changedetection.io
  with a stdlib runner, plus the recipe to run the full changedetection.io app for visual diff.
when_to_use:
  - Poll a page and alert only when a real change crosses a significance threshold
  - Track a price, stock level, or a specific JSON/API field over time
  - Watch a ToS / pricing / policy / release-notes page and diff against last-seen
  - Monitor a competitor or listing page on a cron/launchd schedule with webhook notify
  - Need a baseline+diff loop that ignores noisy churn (timestamps, tokens, rotating ads)
when_not_to_use:
  - One-off scrape of current content with no diffing — use resilient-scraper or firecrawl-scrape
  - Extracting many structured fields from one page — use structured-page-extraction
  - Crawling/harvesting a whole site's URLs — use sitemap-crawl-harvest
  - Pixel-perfect VISUAL/screenshot diff of a JS-rendered page — run the real changedetection.io app (Recipe C)
  - Bot-defended pages needing a stealth browser — use stealth-browser-scraping to fetch, then diff here
keywords: [change-detection, web-monitor, diff, baseline, threshold, price-tracker, stock-watch, webhook, changedetection.io, polling, css-selector, json-path, cron, notification, snapshot]
similar_to: [resilient-scraper, firecrawl-scrape, structured-page-extraction, sitemap-crawl-harvest, incremental-content-index]
inputs_needed: URL(s) to watch; per-watch mode (text/json/css) + selector; a significance threshold (0..1); optional webhook URL for alerts; a datastore dir for baselines
produces: A per-watch report (text or JSON) of changed/significant/ratio/diff, persisted baselines, and optional webhook notifications on significant change
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Web Change Monitor

Fetch -> extract a stable signal -> diff vs baseline -> threshold on significance -> advance baseline -> notify. The stdlib runner (`scripts/watch.py`) handles text, JSON-field, and CSS-selector modes and persists state between runs so it's cron-friendly. For pixel/visual diff of JS-heavy pages, run the real changedetection.io app (Recipe C).

## When to use

Reach for this when the question is "did this page *meaningfully* change since last time?" — price/stock, policy/ToS/pricing text, a specific API field, or a CSS region. The threshold is what separates it from a naive hash: rotating ads, timestamps, CSRF tokens, and view counters change every fetch; you only want to hear about the parts that matter.

## Prerequisites

- **python3** (3.9 stdlib is enough for `text` and `json` modes — no pip install).
- **css mode** additionally needs `pip install beautifulsoup4` (the script raises a clear error if it's missing).
- **Recipe C (visual diff)** needs Docker OR `pip3 install changedetection.io` (+ Playwright browser for screenshots). Apache-2.0; concepts ported here, see `## Credits`.
- No secrets required for the stdlib runner. A webhook URL (env `CD_WEBHOOK` or `--webhook`) is optional.

## How significance works (the important bit)

`ratio = 1 - difflib.SequenceMatcher(baseline, current).ratio()` → `0.0` identical, `1.0` totally different. A watch fires only when `ratio >= threshold`. The **baseline advances only on a significant change**, so a slow drift of tiny sub-threshold edits won't silently accumulate past your alert — each fire re-baselines. First run always just saves a baseline (no alert). Tune `threshold`:

| threshold | behaviour |
|-----------|-----------|
| `0.0`     | any byte-level change fires (noisy) |
| `0.02`    | small — good for tight CSS/JSON selectors |
| `0.10`    | moderate — good for whole-page text mode |
| `0.30+`   | only large rewrites fire |

Prefer a **narrow selector** (css/json mode) over a big threshold — pinpoint the price element and a low threshold beats diffing the whole noisy page.

## Recipe A — stdlib watcher (text / json / css)

1. Write a `watches.json` (array). Each entry: `url` (required), `mode` (`text`|`json`|`css`, default `text`), `selector`, `threshold`, optional `name` and `headers`.

```json
[
  { "name": "gpu-price", "url": "https://example.com/product/x",
    "mode": "css", "selector": ".product-price", "threshold": 0.02 },
  { "name": "api-stock", "url": "https://example.com/api/item/9",
    "mode": "json", "selector": "data.items.0.stock", "threshold": 0.01 },
  { "name": "tos-page", "url": "https://example.com/terms",
    "mode": "text", "threshold": 0.08 }
]
```

- `text` — strips `<script>/<style>/tags`, collapses whitespace → visible-text signal.
- `json` — parses the body, walks a **dotted path** (`data.items.0.stock`; list indices are integers). Empty selector = whole doc.
- `css` — BeautifulSoup `.select(selector)`, joined text of matched nodes.

2. Run it (baselines land in `--datastore`, default `./cd_datastore`):

```bash
python3 scripts/watch.py --watchlist watches.json --datastore ./ds
python3 scripts/watch.py --watchlist watches.json --datastore ./ds --json   # machine-readable
```

First run prints `[BASE]`; later runs print `[ ok ]`, `[chg ]` (below threshold, ignored), or `[CHG!]` (significant). Each result carries `ratio` and a unified-diff `preview`.

3. Notify on significant change — POST a JSON `{name,url,ratio,diff}` to a webhook (Slack/Discord/Teams incoming-webhook, or your own endpoint):

```bash
python3 scripts/watch.py --watchlist watches.json --datastore ./ds \
  --webhook "$SLACK_WEBHOOK_URL"        # or export CD_WEBHOOK=...
```

## Recipe B — schedule the poll (cron / launchd)

The datastore persists baselines, so scheduling is just "run it every N minutes". Cron:

```bash
# every 30 min; log output; alerts go to the webhook in the env
*/30 * * * * cd /path/to/skill && CD_WEBHOOK=https://hooks.slack.com/... \
  /usr/bin/python3 scripts/watch.py --watchlist watches.json --datastore ./ds >> watch.log 2>&1
```

On macOS you can equivalently wrap the same command in a launchd `.plist` with `StartInterval`. Be a good citizen: keep intervals sane (minutes, not seconds) and set a real `User-Agent` per watch via `headers` for sites that expect one.

## Recipe C — full changedetection.io for VISUAL diff & Apprise

When you need screenshot/visual diff of a JS-rendered page, XPath filters, restock detection, or 80+ notification targets, run the real app instead of the stdlib runner:

```bash
# Docker (recommended)
docker run -d --restart always -p "127.0.0.1:5000:5000" \
  -v datastore-volume:/datastore --name changedetection.io dgtlmoon/changedetection.io
# or pip
pip3 install changedetection.io && changedetection.io -d ./cd_data -p 5000
```

Open `http://127.0.0.1:5000`, add a watch, set the filter (CSS/XPath/JSON), and wire notifications via Apprise URLs (e.g. `slack://`, `discord://`, `mailto://`). Drive it programmatically via its REST API (key in **Settings → API**):

```bash
API=http://127.0.0.1:5000/api/v1 ; KEY=your_key
curl -s -H "x-api-key: $KEY" "$API/watch"                                   # list watches
curl -s -H "x-api-key: $KEY" -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/terms","tag":"legal"}' "$API/watch"       # create
curl -s -H "x-api-key: $KEY" "$API/watch/<uuid>/history"                    # snapshots
curl -s -H "x-api-key: $KEY" \
  "$API/watch/<uuid>/difference/<from_ts>/<to_ts>"                          # diff two snapshots
```

## Verify

```bash
python3 -c "import ast; ast.parse(open('scripts/watch.py').read()); print('syntax OK')"
# functional smoke with a file:// fixture (no network):
printf '<html><body><p>GBP 10.00</p></body></html>' > /tmp/v.html
echo '[{"name":"t","url":"file:///tmp/v.html","mode":"text","threshold":0.05}]' > /tmp/w.json
python3 scripts/watch.py --watchlist /tmp/w.json --datastore /tmp/ds   # -> [BASE]
python3 scripts/watch.py --watchlist /tmp/w.json --datastore /tmp/ds   # -> [ ok ]
printf '<html><body><p>GBP 42.00 huge sale today</p></body></html>' > /tmp/v.html
python3 scripts/watch.py --watchlist /tmp/w.json --datastore /tmp/ds   # -> [CHG!] ratio>threshold
```

## Pitfalls

- **Whole-page text mode is noisy.** Nav, footers, and cookie banners shift the ratio. Pin a `css`/`json` selector to the region you actually care about, then use a *low* threshold.
- **JS-rendered content isn't in the HTML.** The stdlib runner fetches raw HTML (urllib). If the price is injected by JavaScript, the text won't be there — use Recipe C (browser-backed) or feed pre-rendered HTML from stealth-browser-scraping.
- **Baseline advances only on significant fires.** That's deliberate (prevents drift creep), but it means a `[chg ]` below threshold keeps comparing against the *old* baseline until something crosses the line. Lower the threshold if you're missing gradual changes.
- **Renaming a watch resets its baseline.** The baseline filename is a hash of `name` (or `url` if unnamed). Change the name → new file → next run is a fresh `[BASE]`. Keep names stable.
- **Don't hammer sites.** Poll in minutes, set a `User-Agent`, and respect `robots.txt`/ToS. Per-watch errors are reported (`[ERR ]`) and never crash the batch.
- **`json` dotted path is literal keys + integer indices.** It is not full JSONPath — no wildcards/filters. For complex queries, extract in `text`/`css` mode or post-process with jq upstream.

## Credits

Concepts (baseline+diff, selector filters, thresholding, notification-on-change) ported from **changedetection.io** by dgtlmoon — Apache-2.0. The stdlib runner here is an original lightweight reimplementation; run the upstream app (Recipe C) for visual diff, XPath, restock detection, and Apprise. See `LICENSE` in this skill dir.
