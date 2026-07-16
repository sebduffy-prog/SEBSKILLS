---
name: structured-page-extraction
category: data-analysis
description: >
  Turn one raw HTML page into typed, schema-validated records. First strip nav/ads/boilerplate
  with trafilatura (main text + title/author/date/sitename metadata, markdown or JSON out). Then
  pull the fields you actually want two ways: a cheap CSS/XPath fast-path with parsel when the page
  is regular (product cards, tables, listings), or Instructor+Pydantic LLM extraction that coerces
  types and RE-PROMPTS on validation errors until the JSON matches your model. Reach for this when
  the shape of the data matters — you need `price: float`, `date: date`, enums, required fields —
  not a text blob. Emits validated Python objects / JSONL you can trust downstream.
when_to_use:
  - You have HTML and need typed records (numbers, dates, enums, required fields), not raw text
  - Boilerplate (nav, ads, related-posts, cookie banners) is polluting your extraction
  - A page is regular enough for CSS/XPath selectors and you want a fast, LLM-free extractor
  - Selectors are brittle or the layout varies, so you want an LLM to fill a Pydantic schema
  - You need extraction that self-corrects — retries on validation failure instead of returning junk
  - Pulling article metadata (author, publish date, sitename) reliably across many sites
when_not_to_use:
  - You just need clean text/markdown of many pages, no schema — use bulk-content-extraction or firecrawl-scrape
  - The content is behind JS rendering or bot walls — render first with stealth-browser-scraping, then feed HTML here
  - You are crawling/discovering URLs at scale — use sitemap-crawl-harvest or resilient-scraper, then extract here
  - Source is office/PDF files on disk, not web HTML — use bulk-content-extraction
  - You only want to know if a page changed — use web-change-monitor
keywords:
  - html extraction
  - trafilatura
  - instructor
  - pydantic
  - schema validation
  - css selectors
  - xpath
  - parsel
  - boilerplate removal
  - structured extraction
  - llm extraction
  - typed records
  - retry on validation
  - article metadata
  - main content extraction
similar_to:
  - bulk-content-extraction
  - firecrawl-scrape
  - resilient-scraper
  - sitemap-crawl-harvest
  - zero-shot-auto-tagging
inputs_needed: >
  The HTML (a URL to fetch or a raw string), the target schema (fields + types, which are required),
  whether the page is regular enough for CSS/XPath or needs LLM extraction, and — if using the LLM
  path — which provider/model and API key are available.
produces: Validated Pydantic objects (or JSONL rows) plus the cleaned main text/metadata trafilatura pulled out.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Structured Page Extraction

Raw HTML → typed, validated records. Two stages, mix as needed:

1. **Clean** — `trafilatura` rips out nav/ads/boilerplate, keeps the main article body and
   metadata (title, author, date, sitename). Apache-2.0.
2. **Structure** — pull fields either with a **CSS/XPath fast-path** (`parsel`, free & instant)
   when the page is regular, or with **Instructor + Pydantic** (LLM) that coerces types and
   **re-prompts on validation errors** until the output matches your schema. Instructor is MIT.

Decision rule: **regular layout → selectors; irregular/prose/varying → LLM.** Cleaning with
trafilatura first makes the LLM path cheaper (fewer tokens) and more accurate (no ad text).

## When to use

Use when the *shape* matters — you need `price: float`, `published: date`, an enum, or a
required field enforced — and a plain text dump won't do. If you only want clean markdown of
lots of pages, use bulk-content-extraction instead.

## Prerequisites

```bash
python3 -m pip install trafilatura parsel pydantic instructor
# instructor pulls an LLM SDK; install the one you use:
python3 -m pip install "instructor[anthropic]"   # or instructor[openai], instructor[google-genai]
```

- Python 3.9 here (`python3`). trafilatura and parsel need **no** API keys.
- The **LLM path only** needs a key: `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY`.
- No key / offline / regular page → stay on the CSS-XPath recipe; it is free and deterministic.

## Recipe 1 — Clean the page (always do this first)

```python
import trafilatura

html = trafilatura.fetch_url("https://example.com/article")   # or: open(path).read()

# Flat clean text (markdown keeps headings/links/tables):
text = trafilatura.extract(html, output_format="markdown",
                           include_comments=False, include_tables=True,
                           favor_precision=True)

# Structured dict with metadata + body in one call:
doc = trafilatura.bare_extraction(html, with_metadata=True, include_comments=False)
# doc is a Document; get a plain dict:
meta = doc.as_dict() if hasattr(doc, "as_dict") else doc
# keys include: title, author, date, url, description, sitename, text
print(meta["title"], meta["author"], meta["date"], meta["sitename"])
```

`favor_precision=True` drops borderline blocks (less noise); use `favor_recall=True` if it's
cutting real content. `output_format` accepts `txt`, `markdown`, `json`, `xml`, `csv`, `html`,
`xmltei`. For article metadata alone (author/date), `bare_extraction` is the reliable path.

## Recipe 2 — CSS / XPath fast-path (regular pages, no LLM)

For product cards, tables, search results — anything with a repeating, stable structure.
`parsel` is Scrapy's selector engine: CSS + XPath, `.get()`/`.getall()`, `::text`, `::attr()`.

```python
from parsel import Selector
from pydantic import BaseModel, HttpUrl, field_validator

class Product(BaseModel):
    name: str
    price: float
    url: HttpUrl

    @field_validator("price", mode="before")
    @classmethod
    def _clean_price(cls, v):
        # "£1,299.00" -> 1299.0
        return float(str(v).replace("£", "").replace("$", "").replace(",", "").strip())

sel = Selector(text=html)
rows = []
for card in sel.css("div.product-card"):
    rows.append(Product(
        name=card.css("h2.title::text").get(default="").strip(),
        price=card.css("span.price::text").get(default="0"),
        url=card.css("a::attr(href)").get(),
    ))
# Pydantic still enforces types — a bad price raises ValidationError, so you fail loudly.
```

XPath when CSS can't express it: `card.xpath('.//time/@datetime').get()`. Always pass
`default=` to `.get()` so a missing node doesn't silently become `None` in a required field —
let Pydantic reject it instead. Selectors break when markup changes; that's the tradeoff for
zero cost and full determinism.

## Recipe 3 — Instructor + Pydantic LLM extraction (irregular pages, self-correcting)

When layout varies, fields are buried in prose, or selectors would be a nightmare. Instructor
patches your LLM client so `response_model=` returns a **validated** Pydantic object, and
`max_retries` feeds validation errors back to the model to fix until it passes.

```python
import instructor
from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Literal, Optional

class Article(BaseModel):
    headline: str
    author: Optional[str] = None      # str | None needs 3.10+; we're on 3.9
    published: date                                  # coerced from strings by pydantic
    sentiment: Literal["positive", "neutral", "negative"]
    key_points: list[str] = Field(min_length=1, max_length=5)

    @field_validator("headline")
    @classmethod
    def _not_empty(cls, v):
        if not v.strip():
            raise ValueError("headline must not be empty")   # triggers a retry
        return v

client = instructor.from_provider("anthropic/claude-3-5-sonnet-latest")  # reads ANTHROPIC_API_KEY

article = client.chat.completions.create(
    response_model=Article,
    max_retries=3,                    # re-prompts with the ValidationError on each failure
    max_tokens=1024,                  # anthropic requires max_tokens
    messages=[{
        "role": "user",
        "content": f"Extract the fields from this article:\n\n{text}",   # text = cleaned trafilatura output
    }],
)
print(article.model_dump_json(indent=2))
```

Key points:
- `instructor.from_provider("provider/model")` is the current unified entry point; it reads the
  provider's env var. Older code uses `instructor.from_anthropic(Anthropic())` / `from_openai(OpenAI())` — both still work.
- **Feed it the cleaned `text`, not raw HTML** — cheaper and more accurate.
- Constraints (`Literal`, `min_length`, `field_validator`) are your quality gate: every failure
  becomes a retry, so the model is forced toward a valid answer instead of returning garbage.
- Batch: loop pages, `try/except ValidationError`, append `.model_dump()` to a JSONL file, and
  count ok/fail so one hard page never kills the run.

## Combined pipeline (the normal case)

```python
import trafilatura, instructor
# 1. clean
html = trafilatura.fetch_url(url)
text = trafilatura.extract(html, output_format="markdown", include_comments=False, favor_precision=True)
# 2. structure (Recipe 2 if regular, else Recipe 3 on `text`)
```

## Verify

```bash
python3 -c "import trafilatura, parsel, pydantic, instructor; print('deps ok')"
# smoke test the clean + selector path with no network / no key:
python3 - <<'PY'
import trafilatura
from parsel import Selector
h = "<html><body><nav>menu</nav><article><h1>Hi</h1><p>Real body text here.</p>"\
    "<div class=p><span class=price>$9.99</span></div></article><footer>ads</footer></body></html>"
print("text:", trafilatura.extract(h))                       # -> "Real body text here." (nav/footer gone)
print("price:", Selector(text=h).css("span.price::text").get())  # -> "$9.99"
PY
```

Both lines printing (boilerplate stripped, selector hit) confirms the LLM-free core works. For
the LLM path, run Recipe 3 once and check `.model_dump_json()` parses and types are right.

## Pitfalls

- **JS-rendered / bot-walled pages**: `fetch_url` gets an empty shell. Render with
  stealth-browser-scraping first, then pass that HTML string to `extract`/`Selector`.
- **trafilatura returns None**: page had no detectable main content, or precision was too
  aggressive — retry with `favor_recall=True`, or fall back to the raw HTML for the LLM.
- **Anthropic needs `max_tokens`** on every create call; omitting it errors. OpenAI does not.
- **`.get()` with no default** silently yields `None` and can slip past a non-required field —
  make the Pydantic field required (or add `default=` on `.get()`) so bad rows fail loudly.
- **Over-using the LLM**: if the page is regular, selectors are ~1000x cheaper and deterministic.
  Only reach for Instructor when structure genuinely varies.
- **Price/date strings**: LLMs and selectors both hand back strings — use a `field_validator`
  (Recipe 1's `_clean_price`) or pydantic's native `date`/`int`/`float` coercion, don't post-process by hand.
- **Version drift**: `instructor.from_provider` is current; if you inherit old code using
  `patch()` / `from_openai`, it still runs — don't "modernize" a working client blindly.
