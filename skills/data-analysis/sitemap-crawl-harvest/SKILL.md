---
name: sitemap-crawl-harvest
category: data-analysis
description: >
  Enumerate a site's FULL URL surface before you crawl. Parse robots.txt for
  Sitemap: hints, walk nested sitemap-index files and 50k-URL chunks (incl.
  gzipped .xml.gz, plain-text, RSS/Atom), dedup, and regex-filter down to a
  clean target list. Reach for this whenever you're about to scrape a whole
  site or section, need every product/article URL, or want a change-detection
  seed list — instead of blindly following links or guessing paths.
when_to_use:
  - Before a bulk crawl/scrape, to get the complete canonical URL list for a domain or section
  - Extracting every product, article, or listing URL without hand-writing path patterns
  - Building a seed/target file (filtered by regex) to feed a scraper, extractor, or change monitor
  - Auditing a site's coverage — how many URLs, which sections, freshest lastmod
  - Discovering sitemaps you didn't know about via robots.txt and sitemap-index recursion
when_not_to_use:
  - You need to render JS / follow in-page links to find URLs (sitemaps are static) — use stealth-browser-scraping or resilient-scraper
  - You already have the URL list and just need page content — use bulk-content-extraction or firecrawl-scrape
  - You want managed hosted crawling with JS + extraction in one call — use firecrawl-scrape
  - Watching a known set of pages for diffs over time — use web-change-monitor (feed it this skill's output)
keywords:
  - sitemap
  - robots.txt
  - crawl
  - url-discovery
  - sitemap-index
  - scrapy
  - sitemapspider
  - ultimate-sitemap-parser
  - gzip
  - lastmod
  - seed-list
  - url-enumeration
  - web-scraping
  - regex-filter
similar_to:
  - bulk-content-extraction
  - resilient-scraper
  - firecrawl-scrape
  - web-change-monitor
  - incremental-content-index
inputs_needed: Target site root (or a direct sitemap URL). Optionally a keep/exclude regex, whether to stay on-host, and where to write the output list.
produces: A deduped, filtered list of page URLs (stdout) plus optional JSONL with url + lastmod + priority + changefreq per page.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Sitemap Crawl Harvest

Get a site's entire URL surface **before** crawling. Sitemaps are the cheapest,
most complete, most polite source of a site's canonical URLs — no rendering, no
link-following, no rate-limit risk. This skill discovers them (robots.txt +
convention), walks the whole tree (index files → child sitemaps → pages),
handles every real-world format, and hands you a clean target list.

## When to use

Use when the deliverable is a **list of URLs to hit next**, or a coverage audit.
If you need page *content*, harvest here first, then pass the list to
`bulk-content-extraction` / `firecrawl-scrape`. If you need JS-rendered link
discovery, sitemaps won't help — use a browser scraper.

## Prerequisites

- **Default path: zero deps.** `scripts/harvest_sitemaps.py` uses only the
  Python stdlib (urllib, gzip, xml, re) and runs on the system `python3` (3.9+
  on this Mac). This is the recommended local tool.
- **Optional `usp`** (`ultimate-sitemap-parser`, GateNLP fork, v1.8.x) is more
  battle-tested (~1M-URL scale, RSS/Atom/News support) **but requires Python
  3.10+** — it will NOT install on the 3.9 system interpreter. Only reach for it
  inside a 3.10+ venv: `python3.11 -m pip install ultimate-sitemap-parser`.
- **Optional Scrapy** if you want to harvest + crawl + extract in one spider.
- No API keys. Be polite: sitemaps are static files, but still send a real
  User-Agent (the script does) and don't hammer.

## Protocol facts that make this correct

- **robots.txt** can carry any number of `Sitemap: <absolute-url>` lines — the
  authoritative discovery mechanism. Always check it first; fall back to the
  conventional `/sitemap.xml` only if none are declared.
- A single sitemap file holds **≤ 50,000 URLs and ≤ 50 MB uncompressed**; big
  sites split across many files fronted by a **`<sitemapindex>`** (itself capped
  at 50,000 sitemaps). You MUST recurse the index — the top file usually has
  zero page URLs.
- Sitemaps are frequently **gzipped** (`.xml.gz`) and come in flavours: standard
  `<urlset>`, plain-text (one URL/line), RSS 2.0 / Atom, Google News/Image.
- Namespaces vary (`sitemap.org`, News, xhtml alternates) — match tags by
  **local name**, never a hard-coded prefix. The script does `{*}loc` / localname
  matching so it survives odd namespaces.

## Recipe 1 — Stdlib harvester (default, works here now)

```bash
S=/Users/seb.duffy/Documents/GitHub/SEBSKILLS/skills/data-analysis/sitemap-crawl-harvest/scripts

# Full surface of a domain (auto-discovers via robots.txt, recurses index+gz)
python3 "$S/harvest_sitemaps.py" https://www.example.com > urls.txt

# Just the /blog/ section, drop image URLs, stay on-host, keep rich metadata
python3 "$S/harvest_sitemaps.py" https://www.example.com \
  --match '/blog/' --exclude '\.(jpg|png|webp)$' --same-host \
  --jsonl pages.jsonl > blog_urls.txt

# Point straight at a known sitemap or index (skips robots discovery)
python3 "$S/harvest_sitemaps.py" https://www.example.com/sitemap_index.xml.gz > urls.txt
```

Output: one URL per line on stdout; a `# N URLs harvested` summary on stderr;
`pages.jsonl` (with `--jsonl`) has `{"url","lastmod","priority","changefreq"}`
per page for sorting by freshness or importance.

Sort a seed list by most-recently-modified:

```bash
python3 - <<'PY'
import json
rows=[json.loads(l) for l in open('pages.jsonl')]
rows.sort(key=lambda r: r.get('lastmod',''), reverse=True)
for r in rows[:20]: print(r.get('lastmod','-'), r['url'])
PY
```

## Recipe 2 — ultimate-sitemap-parser (3.10+ venv, big/awkward sites)

More formats and error-tolerance than the stdlib script; use for RSS/Atom feeds,
News sitemaps, or million-URL crawls. Requires Python 3.10+.

```python
# pip install ultimate-sitemap-parser   (in a 3.10+ interpreter)
from usp.tree import sitemap_tree_for_homepage

tree = sitemap_tree_for_homepage("https://www.example.com/")
for page in tree.all_pages():        # generator — memory-efficient
    print(page.url, page.priority, page.last_modified, page.change_frequency)
```

`all_pages()` yields `SitemapPage` objects; every page has `.url` and
`.priority`, and `.last_modified` / `.change_frequency` / `.news_story` when the
sitemap provides them. `sitemap_tree_for_homepage` already reads robots.txt and
recurses index files for you.

## Recipe 3 — Scrapy SitemapSpider (harvest + crawl in one)

When you want to discover URLs from sitemaps AND immediately crawl/extract them,
skip a separate seed file and let Scrapy route by regex.

```python
from scrapy.spiders import SitemapSpider

class ProductSpider(SitemapSpider):
    name = "products"
    sitemap_urls = ["https://www.example.com/robots.txt"]  # or a sitemap.xml
    # (regex, callback) — first match wins; URLs not matched are dropped
    sitemap_rules = [("/product/", "parse_product")]
    # regexes of sitemaps (index children) to follow; default = follow all
    sitemap_follow = ["/product-sitemap"]
    sitemap_alternate_links = True   # also pull <xhtml:link> hreflang alternates

    # optional: filter index/url entries before fetch (e.g. only fresh lastmod)
    def sitemap_filter(self, entries):
        for entry in entries:
            if entry.get("lastmod", "") >= "2026-01-01":
                yield entry

    def parse_product(self, response):
        yield {"url": response.url, "title": response.css("h1::text").get()}
```

Run: `scrapy runspider product_spider.py -o products.jsonl`.

## Verify

```bash
S=/Users/seb.duffy/Documents/GitHub/SEBSKILLS/skills/data-analysis/sitemap-crawl-harvest/scripts
python3 -c "import ast; ast.parse(open('$S/harvest_sitemaps.py').read()); print('AST OK')"
# Known-good live target (multilingual sitemap-index → child urlsets):
python3 "$S/harvest_sitemaps.py" https://www.sitemaps.org --same-host | wc -l   # ~84 URLs
```

If the count looks tiny (e.g. 1), you likely stopped at an index file — confirm
recursion happened, or the site only exposes a stub sitemap (fall to a browser
crawl).

## Pitfalls

- **Index vs urlset.** The top sitemap is often a `<sitemapindex>` with zero page
  URLs — you must follow every `<sitemap><loc>` child. Recipe 1 & 2 do this;
  don't parse only the first file.
- **Gzip.** Many sitemaps are `.xml.gz` or gzip-encoded without the extension.
  The script sniffs the magic bytes (`1f 8b`) as well as the extension.
- **usp needs 3.10+.** It won't install on this Mac's system `python3` (3.9).
  Use the stdlib script locally, or spin a 3.10+ venv for usp.
- **Sitemaps ≠ complete.** They reflect what the site *chose* to publish and can
  omit noindex/paginated/JS-only pages, or be stale. For exhaustive discovery,
  combine with a link crawl. Treat lastmod as a hint, not a guarantee.
- **Cross-host & CDN URLs.** Index children and page `<loc>`s can point at other
  hosts/CDNs. Use `--same-host` (or usp filtering) when you only want the primary
  domain, or you'll drag in asset/partner domains.
- **Politeness & robots.** Harvesting sitemaps is light, but the *subsequent*
  crawl must honour robots.txt `Disallow` and crawl-delay. This skill only lists
  URLs; respect the rules when you go fetch them.
- **Cycles / runaway indexes.** Malformed sites can self-reference. The script
  dedups sitemap URLs and caps recursion at 5000 files — raise `MAX_SITEMAPS` for
  genuinely huge properties, but confirm it's not a loop first.
