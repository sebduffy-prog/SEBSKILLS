---
name: geo-answer-engine-optimization
category: strategy
description: >-
  Optimise a brand, page or site to be RETRIEVED and CITED by AI answer engines
  (ChatGPT, Perplexity, Google AI Overviews, Claude, Gemini, Copilot) — the
  GEO/AEO discipline. Ship an /llms.txt curation file (AnswerDotAI spec), valid
  JSON-LD schema (Organization, Article, FAQPage, Product), self-contained
  quotable passages seeded with stats + citations + direct quotes (the Princeton
  GEO levers that lift visibility ~30-40%), and consistent entity signals across
  the web. Trigger on "GEO", "AEO", "answer engine optimization", "get cited by
  ChatGPT/Perplexity", "llms.txt", "AI Overviews", "make our brand show up in AI
  answers", "schema markup for AI", "why isn't the LLM citing us". Structural +
  content playbook, not a guaranteed-ranking promise.
when_to_use:
  - A brand/page is invisible or misquoted in ChatGPT, Perplexity, Gemini or Google AI Overviews and you want it cited
  - You are shipping or auditing an /llms.txt (and optional /llms-full.txt) curation file for a site
  - You need JSON-LD schema (Organization, Article, FAQPage, Product, Person) that machines can parse cleanly
  - You are rewriting content into self-contained, quotable, stat-and-citation-dense passages for LLM retrieval
  - You want an entity-consistency audit (name, NAP, sameAs links, Wikidata/Wikipedia) so engines resolve one identity
  - Leadership asks "how do we get into AI answers" and you need a concrete technical + editorial checklist
when_not_to_use:
  - You want classic blue-link keyword/backlink SEO for Google's ten links — use a dedicated SEO workflow, not GEO
  - You want to measure share of brand mentions across AI vs search demand — use [[share-of-search]]
  - You need audience/segment insight or personas to write FOR — use [[audience-insight]] or [[persona-population-builder]]
  - You need a full brand teardown of positioning and identity — use [[brand-audit]]
  - You want a competitor comms/messaging teardown — use [[competitive-comms-audit]]
keywords:
  - geo
  - aeo
  - answer engine optimization
  - generative engine optimization
  - llms.txt
  - json-ld
  - schema.org
  - ai overviews
  - perplexity
  - chatgpt citation
  - quotable passages
  - entity consistency
  - sameas
  - structured data
  - fact density
similar_to:
  - share-of-search
  - competitive-comms-audit
  - brand-audit
inputs_needed: >-
  The brand/site URL and its key pages; the priority question set you want to be cited for;
  canonical brand facts (legal name, founding, HQ, key stats, spokespeople, product SKUs);
  existing entity links (Wikipedia/Wikidata/Crunchbase/LinkedIn) if any.
produces: >-
  A shippable /llms.txt (+ optional /llms-full.txt), JSON-LD schema blocks per page type,
  rewritten quotable passages, an entity-consistency fix list, and a citation-tracking
  prompt harness with baseline/target metrics.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# GEO / Answer Engine Optimization

Make a brand **retrievable and citable** by AI answer engines. Two jobs: (1) let
machines find and trust a clean, structured version of the facts (llms.txt +
JSON-LD + entity consistency), and (2) write passages LLMs actually lift into
answers (self-contained, stat-dense, quoted, sourced). Grounded in the
[AnswerDotAI llms.txt spec](https://llmstxt.org/), [Google's AI-optimization
guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide),
and the [Princeton GEO study](https://arxiv.org/abs/2311.09735) (cite-sources /
add-statistics / add-quotations lift visibility ~30-40%).

## When to use

Reach for this when the deliverable is "get us into AI answers" — an llms.txt to
ship, schema to add, or copy to rewrite so ChatGPT/Perplexity/AI-Overviews quote
it. Not for classic keyword SEO, and not for measuring mention share (that is
[[share-of-search]]).

## Prerequisites

- The site URL + a list of its high-value pages (home, product, about, key posts).
- A **priority question set** (10-30 real prompts you want to win, e.g. "best
  challenger soft drink in Scotland", "who makes IRN-BRU").
- **Canonical facts**: legal name, founding year, HQ, headline stats, named
  experts/spokespeople, product names. GEO rewards verifiable specifics.
- Access to publish `/llms.txt` at the domain root and edit page `<head>`.

## Recipe 1 — Ship an llms.txt (AnswerDotAI spec)

`/llms.txt` is a root-level Markdown file that curates the LLM-readable map of a
site. **Exactly one H1, then a blockquote summary, then optional prose (no
headings), then H2 link-lists.** The `## Optional` section is special: its links
may be dropped when a shorter context is needed. Structure:

```markdown
# Acme Drinks

> Acme Drinks is a Scottish challenger soft-drinks maker founded in 1901,
> best known for IRN-BRU. This file points AI engines at the canonical facts.

Acme sells across the UK and 30+ export markets. Primary spokesperson: Dr Jane Roe, Head of Flavour.

## Core

- [About Acme](https://acme.example/about.md): legal name, founding, HQ, ownership
- [Products](https://acme.example/products.md): full SKU list with ingredients
- [Newsroom](https://acme.example/press.md): dated announcements and stats

## Optional

- [Sustainability report 2026](https://acme.example/esg.md): secondary detail
```

Rules that matter:
- Serve it at **`https://DOMAIN/llms.txt`** (root), `Content-Type: text/plain` or `text/markdown`.
- Link to **clean Markdown** versions of pages where possible (append `.md`, or a `?format=md` route). LLMs parse Markdown far more reliably than JS-rendered HTML.
- Keep the H1 = brand/site name; the blockquote must carry the single most important sentence of context.
- Optionally also publish **`/llms-full.txt`** — the same map with full page text inlined, for engines that want one-shot context. Keep it in sync.
- llms.txt is a *retrieval convenience*, not yet honoured by every crawler — treat it as additive, never the only signal.

Validate/expand with AnswerDotAI's tooling:

```bash
# reference implementation; expands an llms.txt into an LLM-ready context file
python3 -m pip install --user llms-txt   # provides llms_txt2ctx
llms_txt2ctx llms.txt > llms-ctx.txt     # sanity-check it parses
```

## Recipe 2 — JSON-LD schema per page type

Add **JSON-LD** in a `<script type="application/ld+json">` in `<head>`. It gives
engines an unambiguous, machine-readable fact layer. Pick the type per page:

- Site/brand → `Organization` (with `sameAs` entity links)
- Article/post → `Article` / `BlogPosting` (with `author`, `datePublished`, `dateModified`)
- Q&A content → `FAQPage`
- Product → `Product` (+ `Offer`, `AggregateRating` if genuine)
- People → `Person`

Organization + sameAs (the entity-resolution backbone):

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Acme Drinks",
  "legalName": "Acme Drinks Ltd",
  "url": "https://acme.example",
  "logo": "https://acme.example/logo.png",
  "foundingDate": "1901",
  "sameAs": [
    "https://en.wikipedia.org/wiki/Acme_Drinks",
    "https://www.wikidata.org/wiki/Q000000",
    "https://www.linkedin.com/company/acme-drinks",
    "https://www.crunchbase.com/organization/acme-drinks"
  ]
}
</script>
```

FAQPage (a high-yield GEO format — mirrors the question→answer shape engines love):

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [{
    "@type": "Question",
    "name": "Who makes IRN-BRU?",
    "acceptedAnswer": {
      "@type": "Answer",
      "text": "IRN-BRU is made by Acme Drinks Ltd, a Scottish maker founded in 1901."
    }
  }]
}
</script>
```

Non-negotiables:
- **`dateModified` must equal the real last-edit time.** Engines weight freshness; a fake or stale date erodes trust. Keep it in sync with the `Last-Modified` HTTP header and XML sitemap `<lastmod>`.
- Schema must **describe content actually visible on the page** — invisible/contradicting markup is spam and gets ignored or penalised.
- Validate every block (see Verify).

## Recipe 3 — Rewrite passages to be quotable (the Princeton levers)

LLMs lift **short, self-contained passages**. Rewrite so each answers one
question on its own and is dense with verifiable specifics:

1. **Question-first / answer-first.** Lead with the direct answer in one sentence, then support it. Use the real question as an H2/H3.
2. **Add statistics.** Swap vague claims for numbers with units and a date ("grew 42% in FY2025") — a top Princeton lever.
3. **Cite sources.** Name and link the origin of each stat/claim; engines prefer sourced text.
4. **Add quotations.** Include a short attributed quote from a named expert — another proven lift.
5. **Self-contained chunks.** Each paragraph should make sense with zero surrounding context (no "as mentioned above"). ~2-4 sentences.
6. **Entity clarity.** Name the brand/product explicitly in the passage; avoid pronoun-only references an extracted chunk would lose.

Before → after:

```
BEFORE: We're one of the most popular soft drinks and have been around a while.

AFTER:  IRN-BRU is Scotland's best-selling non-cola soft drink, outselling
        Coca-Cola in Scotland since the 1980s (Nielsen, 2024). "It's the taste
        people describe as unmistakably Scottish," says Dr Jane Roe, Acme's
        Head of Flavour. The brand launched in 1901.
```

## Recipe 4 — Entity consistency audit

Engines must resolve the brand to **one** entity. Check every surface:
- **Exact name + NAP** (name, address, phone) identical across site, Google Business Profile, LinkedIn, Crunchbase, Wikipedia.
- **`sameAs` graph** links all authoritative profiles; the Wikidata/Wikipedia pair is the strongest anchor — create/curate them if missing.
- **No naming drift** ("Acme" vs "ACME Drinks Ltd" vs "Acme Beverages") — pick one canonical display name and one legal name and use them consistently.
- **Author/expert entities**: give named experts `Person` schema + real profiles (LinkedIn, Muck Rack) so quotes carry authority.

## Recipe 5 — Citation-tracking harness

Establish a baseline and re-run monthly. For each priority prompt, ask each
engine and log whether the brand is **cited/linked** and whether the facts are
**correct**:

- **AI Citation Rate** = pages cited ÷ pages tracked.
- **Response Inclusion Rate** = prompts mentioning the brand ÷ prompts tested.
- **Accuracy** = correct mentions ÷ total mentions (misquotes are a fixable GEO defect).

Run the priority set through ChatGPT, Perplexity, Gemini and Google AI Overviews;
record engine, prompt, cited y/n, source URL, correct y/n. Watch which formats
(FAQ, stat-led, quote-led) win, and double down.

## Verify

- **llms.txt parses**: `llms_txt2ctx llms.txt > /dev/null` exits cleanly; file is reachable at the root URL (`curl -sI https://DOMAIN/llms.txt` → 200, text/plain|markdown).
- **JSON-LD is valid**: paste each block into Google's [Rich Results Test](https://search.google.com/test/rich-results) and the [Schema Markup Validator](https://validator.schema.org/) — zero errors; `dateModified` matches reality.
- **Passages self-contained**: read any lifted paragraph in isolation — it answers a question, names the entity, and carries a sourced number.
- **Entity graph resolves**: every `sameAs` URL is live and points to the same brand; name is identical across profiles.
- **Baseline captured**: citation harness has a dated row for every priority prompt on every engine before you claim improvement.

## Pitfalls

- **Fabricated facts / stats.** GEO amplifies whatever you publish — invented numbers get quoted, then discredited. Only ship verifiable claims.
- **Schema that lies.** Markup contradicting or not visible on the page is spam; engines drop it. Keep schema and page in lockstep.
- **Stale `dateModified`.** Faking freshness backfires — align schema, HTTP `Last-Modified`, and sitemap `<lastmod>` to true edit times.
- **JS-only content.** If facts render only via client-side JS, many retrievers miss them. Ship server-rendered HTML and Markdown mirrors.
- **Treating llms.txt as magic.** Not every crawler honours it yet; it is one additive signal, not a substitute for clean HTML + schema + authority.
- **Naming drift.** Inconsistent brand/legal names split the entity across identities and dilute every signal.
- **Chasing rankings, not answers.** GEO wins *inclusion in a synthesised answer* by fact density and authority — not a blue-link position. Measure citation, not rank.
- **One-and-done.** Answer engines re-crawl and re-rank constantly; re-run the citation harness monthly and iterate on the formats that get cited.
