---
name: product-feed-retail-media
category: commerce
description: >
  Generate, optimise and debug product-catalog feeds for Google Merchant Center
  and Meta (Facebook/Instagram) commerce, plus SKU-level retail-media (RMN)
  structuring. Use when the user says "build a Merchant Center feed", "my
  products got disapproved", "fix the catalog", "why is this SKU not serving",
  "make a Meta product feed", "GTIN error", "feed spec", or wants a clean RSS/TSV
  feed from a product spreadsheet. Ships a stdlib feed_tool.py that builds the
  RSS-2.0 g:-namespace XML / TSV / CSV, validates every attribute against the real
  spec (char limits, price format, availability enums, GS1 GTIN check digit), and
  maps issues to the exact disapproval reason a merchant sees.
when_to_use:
  - Building a Google Merchant Center feed (RSS 2.0 XML or TSV) from a product CSV/JSON
  - Building a Meta commerce catalog data feed (CSV/TSV) for Advantage+ / catalog ads
  - Diagnosing product disapprovals or "not serving" items and getting the fix per SKU
  - Validating attribute limits, price format, availability/condition enums, GTIN check digits
  - Structuring variants (item_group_id) and SKU-level fields for retail-media networks (RMN)
  - Turning a merchandising spreadsheet into a spec-compliant feed before upload
when_not_to_use:
  - Launching or budgeting the campaigns that consume the catalog — use paid-media-campaign-ops
  - Building a storefront checkout / agentic-commerce API integration — use agentic-commerce-integration
  - Audience sizing or shopper segmentation research — use the GWI Spark / strategy skills
  - Designing product creative or lifestyle imagery — use canvas-design or frontend-design
keywords:
  - product-feed
  - merchant-center
  - google-shopping
  - meta-catalog
  - facebook-catalog
  - feed-spec
  - disapproval
  - gtin
  - retail-media
  - rmn
  - item-group-id
  - availability
  - feed-validation
  - shopping-ads
  - product-data
similar_to:
  - agentic-commerce-integration
inputs_needed: A product CSV or JSON (canonical schema — id, title, description, link, image_link, availability, price, brand, gtin/mpn, condition, variant attrs); target platform (google|meta); desired output format (xml|tsv|csv)
produces: Spec-compliant feed files (RSS-2.0 g: XML for Google, CSV/TSV for both), a severity-ranked validation report (ERROR/WARN/INFO, exit 1 on error for CI), and a disapproval-reason diagnosis mapping each issue to the merchant-facing fix
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Product Feed & Retail Media

Turn a merchandising spreadsheet into a **spec-compliant** Google Merchant Center
or Meta catalog feed, then validate and diagnose it before upload. Feeds are pure
structured data — most disapprovals are avoidable with a strict pre-flight check
that the platform UIs make painfully slow. This skill does that check offline.

## When to use

- You have product data (CSV/JSON) and need a Google **RSS 2.0** (`g:` namespace)
  or **TSV** feed, or a Meta catalog **CSV/TSV**.
- Items are disapproved / "not serving" and you need the *reason* and *fix* per SKU.
- You need to enforce attribute limits, enums, price format and **GTIN check digits**
  in CI before anyone uploads.

## Prerequisites

- **Python 3.9+ stdlib only** — no pip installs, no network. Works on this Mac as-is.
- A product file. Canonical column/key names (superset of both platforms):
  `id, title, description, link, image_link, additional_image_link,
  availability, availability_date, price, sale_price, currency, brand, gtin,
  mpn, condition, google_product_category, product_type, item_group_id, color,
  size, gender, age_group, quantity, mobile_link`.
  Bare prices (`129.99`) are combined with `currency` (default `GBP`); or supply
  `12.99 GBP` directly.
- To actually upload: a Merchant Center account + feed URL/SFTP, or a Meta
  Commerce Manager catalog + data-feed schedule. This skill produces the file;
  it does not push it (that is a manual upload or a scheduled fetch URL you host).

## Grounded spec facts (do not fabricate around these)

| Attribute | Rule |
|---|---|
| `id` | ≤ 50 chars, unique, stable |
| `title` | ≤ 150 chars; front-load brand + key attributes; no promo text/ALL CAPS |
| `description` | ≤ 5000 chars |
| `link` / `image_link` | absolute `https://` URL; image ≥ 500×500 px |
| `price` | numeric + ISO-4217 currency, e.g. `129.99 GBP`; must match landing page |
| `availability` (Google) | `in_stock`, `out_of_stock`, `preorder`, `backorder` |
| `availability` (Meta) | `in stock`, `out of stock`, `preorder`, `available for order`, `discontinued` |
| `condition` | `new`, `refurbished`, `used` |
| `brand` | ≤ 70 chars, required for most items |
| `gtin` | ≤ 50 digits, valid **GS1 mod-10** check digit; else use `mpn` |
| `item_group_id` | ≤ 50 chars, groups variants sharing a parent |
| Meta stock | `quantity_to_sell_on_facebook` ≥ 1 **and** `in stock` to be buyable |

Google uses **underscores** in enums; Meta canonical uses **spaces**. The tool
normalises per platform on output, so keep one canonical input and target either.

## Recipes

All commands use `scripts/feed_tool.py`. Run `--help` on any subcommand.

### 1. Validate before you upload (CI-friendly)

```bash
python3 scripts/feed_tool.py validate products.csv --platform google
# exit code 1 if any ERROR — wire into a pre-commit / pipeline gate
python3 scripts/feed_tool.py validate products.csv --platform meta --json
```

Output is severity-ranked: `ERROR` (blocks/disapproves), `WARN` (degrades
performance or risks review), `INFO` (advisory, e.g. auto-assigned category).

### 2. Build the feed file

```bash
# Google Merchant Center RSS 2.0 (g: namespace) — the canonical XML feed
python3 scripts/feed_tool.py build products.csv --platform google --format xml -o feed.xml

# Google TSV (tab-separated) if you prefer a flat feed
python3 scripts/feed_tool.py build products.csv --platform google --format tsv -o feed.tsv

# Meta catalog CSV (emits quantity_to_sell_on_facebook)
python3 scripts/feed_tool.py build products.csv --platform meta --format csv -o meta_catalog.csv
```

Host `feed.xml` at a stable HTTPS URL (or SFTP) and register it in Merchant
Center as a scheduled fetch; for Meta, upload `meta_catalog.csv` or point a
scheduled data feed at its URL in Commerce Manager.

### 3. Diagnose disapprovals

```bash
python3 scripts/feed_tool.py diagnose products.csv --platform google
```

Buckets every actionable issue into the **merchant-facing reason** (image issues,
price mismatch, availability mismatch, invalid GTIN, title policy, missing brand,
category mismatch) with a count and an example SKU — so you fix the highest-volume
cause first.

### 4. SKU-level structuring for retail media (RMN)

Retail-media networks (Amazon Ads, Criteo, Instacart, Walmart Connect, plus the
Google/Meta shopping surfaces) bid at the **SKU/variant** grain. To keep a feed
RMN-ready:

- One row per sellable **variant**; share a parent via `item_group_id`.
- Every variant carries its own `id`, `price`, `availability`, `gtin` and the
  differentiating attribute (`color`/`size`). The tool WARNs if you set a variant
  attribute without an `item_group_id` to group it.
- Keep `gtin` populated and valid — most RMNs match inventory on GTIN, and an
  invalid check digit silently drops the SKU from bidding.
- Use `product_type` for your own merchandising taxonomy (≤ 750 chars) and let
  `google_product_category` carry the platform taxonomy; RMNs slice reporting by
  both.

## Verify

```bash
# Syntax check (no execution)
python3 -c "import ast; ast.parse(open('scripts/feed_tool.py').read()); print('OK')"

# End-to-end on the canonical example: a clean row passes (exit 0),
# a broken row fails (exit 1) with per-attribute ERRORs.
python3 scripts/feed_tool.py validate products.csv --platform google; echo "exit=$?"
```

A well-formed feed: `validate` exits 0 with zero `ERROR`s; `build --format xml`
produces `<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">` with one
`<item>` per SKU and only non-empty `g:` tags.

## Pitfalls

- **Price/availability mismatch is the #1 silent disapproval.** The feed value
  must match the microdata on the live landing page to the penny and the exact
  stock state — the tool checks *format*, not the page. Confirm parity after upload.
- **GTIN check digit.** A GTIN that looks right but fails GS1 mod-10 gets the item
  dropped, not flagged loudly. The tool rejects it up front; if you genuinely have
  no GTIN, omit it and supply `mpn` + `brand`.
- **Meta vs Google enums differ** (`in stock` vs `in_stock`). Keep ONE canonical
  input and let `build`/`validate` normalise; do not hand-edit both feeds.
- **XML is Google-only here.** `build --platform meta --format xml` is rejected —
  use `csv`/`tsv` for Meta.
- **Titles.** ≤ 150 chars, but front-load brand + product + key attribute; ALL-CAPS
  and promotional text ("SALE!!!") trigger review. The tool WARNs on both.
- **Variants without `item_group_id`** serve as unrelated products and split your
  performance data — always group them.
- The tool validates structure offline; it does **not** crawl your landing pages,
  fetch images to confirm 500×500, or push to any platform. Those are manual/hosted steps.
