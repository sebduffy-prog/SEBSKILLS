---
name: firecrawl-scrape
category: data-analysis
description: >
  Turn any URL or entire website into clean, LLM-ready markdown or schema-validated JSON using Firecrawl —
  scrape (one page), crawl (a whole site), map (discover all URLs), extract (structured fields with a schema), and
  actions (click/scroll/fill before scraping JS pages). Use this whenever someone says "scrape this site into
  markdown", "crawl a docs site for RAG", "turn these pages into structured data", "extract prices/specs from
  these URLs", "get clean text from a JS-heavy page", or wants the fast path from web page to usable data without
  hand-rolling a scraper. Reach for it even if they just say "get the content off this site".
when_to_use:
  - Converting a page or whole site into clean markdown for a RAG knowledge base
  - Extracting typed fields (price, title, specs) from many URLs against a schema
  - Scraping JS-rendered pages that plain HTTP fetching returns empty for
  - Discovering every URL on a site before crawling (map)
when_not_to_use:
  - You want a self-hosted, dependency-free HTTP fetch layer → use resilient-scraper
  - Site is behind aggressive Cloudflare/DataDome bot walls → use stealth-browser-scraping
  - You only need to enumerate URLs from sitemaps → use sitemap-crawl-harvest
  - Local HTML you already have → use structured-page-extraction
keywords: [firecrawl, scrape, crawl, map, extract, actions, markdown, llm-ready, rag ingest, web scraping, structured extraction, schema, js rendering, website to markdown, crawl4ai]
similar_to: [resilient-scraper, stealth-browser-scraping, structured-page-extraction, sitemap-crawl-harvest]
inputs_needed:
  - The URL(s) or site to scrape/crawl
  - Desired output — markdown, or a JSON schema of fields to extract
  - For crawl — depth/page limit and include/exclude path patterns
  - A FIRECRAWL_API_KEY (cloud) or a self-hosted Firecrawl endpoint
produces: Clean markdown and/or schema-validated JSON records for the requested pages
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Firecrawl scrape

The fast path from web page to usable data: Firecrawl handles JS rendering, boilerplate stripping, crawling and
schema extraction, returning clean markdown or typed JSON. Managed service (or self-host the OSS engine).

## When to use

When you want *content or data out of the web* without building and babysitting a scraper. For a self-contained,
no-service fetch layer use `resilient-scraper`; for the hardest bot-walls use `stealth-browser-scraping`.

## Prerequisites

```bash
python3 -m pip install --user firecrawl-py     # or: npm i @mendable/firecrawl-js
export FIRECRAWL_API_KEY="fc-..."              # cloud; or point at a self-hosted instance
```
Self-host (no per-page cost, OSS) via `github.com/firecrawl/firecrawl` docker compose, then set the base URL.
An OSS-only alternative with no service is `github.com/unclecode/crawl4ai`.

## The five operations

```python
from firecrawl import Firecrawl
from firecrawl.types import ScrapeOptions
app = Firecrawl()   # reads FIRECRAWL_API_KEY

# 1. SCRAPE one page -> markdown (JS rendered, boilerplate stripped)
doc = app.scrape("https://example.com/post", formats=["markdown"])
md = doc.markdown

# 2. MAP a site -> every discoverable URL (fast, for planning a crawl)
urls = app.map("https://docs.example.com").links

# 3. CRAWL a whole site -> markdown for each page (async job)
job = app.crawl("https://docs.example.com", limit=200,
                include_paths=["/docs/.*"],
                scrape_options=ScrapeOptions(formats=["markdown"]))
pages = job.data     # [Document(url=..., markdown=...), ...]

# 4. EXTRACT typed fields against a schema (LLM-backed, validated)
schema = {"type": "object", "properties": {
    "title": {"type": "string"}, "price": {"type": "number"},
    "in_stock": {"type": "boolean"}}, "required": ["title"]}
rec = app.scrape("https://shop.example.com/item/42",
                 formats=[{"type": "json", "schema": schema}])
data = rec.json

# 5. ACTIONS -> interact before scraping a JS page
app.scrape("https://app.example.com",
           formats=["markdown"],
           actions=[{"type": "click", "selector": "#load-more"},
                    {"type": "wait", "milliseconds": 800}])
```

## Recipes

- **Seed a RAG base:** `crawl` a docs site to markdown, chunk with `rag-chunking-contextual`, embed.
- **Product table:** `map` → filter product URLs → `scrape` each with a `json` format schema → dataframe.
- **Cost control:** `map` first to see page count and scope `include_paths` before a large `crawl`.

## Verify

- `scrape` on a known page returns non-empty `markdown` with the article body and without nav/footer noise.
- The `json` format returns data that matches your schema keys and types on a couple of sample URLs.

## Pitfalls

- **Crawl cost/scope** — always `map` and set `limit` + `includePaths`/`excludePaths`, or a crawl balloons.
- **Extract is LLM-backed** — validate the returned JSON against your schema and spot-check; it can miss fields on odd layouts (fall back to `structured-page-extraction`'s CSS/XPath path).
- **Rate limits / API key** — cloud has per-plan limits; self-host removes them but you run the browser fleet.
- **Respect robots/ToS** — Firecrawl fetches real pages; honour site terms and rate limits.
