---
name: news-sentiment-api
category: data-analysis
description: >
  Pull free news coverage volume, tone and entity signals from GDELT DOC 2.0 (global tone/volume firehose, no key), Marketaux (financial news + per-entity sentiment scores), the Guardian Open Platform, and HN Algolia. Use to measure share-of-coverage, tone timelines, spikes, and sentiment around a brand, ticker, person or topic. Verb-first: fetch, chart, and score news tone without paying for a media-monitoring seat.
when_to_use:
  - Measuring volume + tone of news coverage for a brand, campaign, person or topic over time
  - Getting per-ticker/per-entity financial-news sentiment scores (Marketaux)
  - Building a share-of-coverage or spike-detection view across competitors
  - Pulling clean article lists (title, url, source, date) for a query to feed further NLP
  - Sampling tech/startup discourse and comment velocity from Hacker News
when_not_to_use:
  - Paid enterprise social + news monitoring with saved projects → use the Brand24 MCP tool
  - Audience attitudes/segmentation rather than news → use GWI Spark or wikidata-knowledge-api
  - Stock prices/fundamentals rather than news tone → use market-data-api
  - Generic "which free API exists" discovery → use free-api-catalogue first
  - Scraping arbitrary article bodies at scale → use bulk-content-extraction / firecrawl-scrape
keywords: [news, sentiment, gdelt, marketaux, guardian, hacker-news, tone, coverage-volume, share-of-voice, entity-sentiment, media-monitoring, financial-news, timeline, spike-detection]
similar_to: [free-api-catalogue, market-data-api, govt-open-data-api, wikidata-knowledge-api]
inputs_needed: Query term(s) or ticker; time window; which signal (volume, tone, entity sentiment, article list); Marketaux + Guardian free keys if using those sources
produces: JSON/CSV of article lists, tone/volume timelines and per-entity sentiment scores, ready to chart or feed downstream NLP
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# News & Sentiment APIs (GDELT · Marketaux · Guardian · HN)

Four free news signals, each best at one thing. Reach for the smallest source that answers the question.

| Source | Key? | Best for | Sentiment? |
|--------|------|----------|-----------|
| **GDELT DOC 2.0** | none | Global volume + tone timelines, share-of-coverage, article firehose | Yes (avg tone, -100..+100) |
| **Marketaux** | free token | Financial news with **per-entity sentiment scores** (-1..+1) per ticker | Yes (native, per entity) |
| **Guardian Open Platform** | free key | High-quality full-text UK/world articles, section/tag filters | No (bodies for your own NLP) |
| **HN Algolia** | none | Tech/startup discourse, points + comment velocity | No |

## When to use

Trigger when someone asks "how much coverage / what tone / what sentiment" around a brand, ticker, person, campaign or topic — and you want real data, not vibes. GDELT is the default first stop (no key, global, instant tone timeline). Add Marketaux for tickers, Guardian for quality bodies, HN for tech pulse.

## Prerequisites

- `curl` + `python3` (3.9 fine). No pip installs required for the core recipes.
- **GDELT**: no key. Hard rate limit — **one request per ~5 seconds** or you get a throttle text page instead of JSON. Space calls out.
- **Marketaux**: free token at https://www.marketaux.com (sign up → dashboard). Free tier ≈ **100 requests/day** and returns **only 3 articles per request** (`limit` capped at 3). Fine for a sentiment snapshot; not a firehose.
- **Guardian**: free developer key at https://open-platform.theguardian.com/access/ (email → key). `api-key=test` exists for quick trials but is heavily shared/rate-limited — get your own (12 req/s, 5000/day, non-commercial).
- **HN Algolia**: no key. Use **https** (`https://hn.algolia.com/api/v1/...`).

Store keys as env vars, never hardcode:
```bash
export MARKETAUX_TOKEN=...   # add to ~/.zshrc, not the repo
export GUARDIAN_KEY=...
```

## Recipes

### 1. GDELT — tone + volume timeline (the workhorse)
`mode` picks the output. `format=json` for machine use. `timespan` (e.g. `1week`, `3months`) or explicit `startdatetime`/`enddatetime` in `YYYYMMDDHHMMSS`. Quote multi-word phrases and URL-encode.

```bash
Q=$(python3 -c "import urllib.parse;print(urllib.parse.quote('\"electric vehicle\"'))")
# Average tone per day (JSON series):
curl -s "https://api.gdeltproject.org/api/v2/doc/doc?query=$Q&mode=timelinetone&timespan=3months&format=json" -o tone.json
# Coverage volume per day (% of all monitored articles):
curl -s "https://api.gdeltproject.org/api/v2/doc/doc?query=$Q&mode=timelinevol&timespan=3months&format=json" -o vol.json
```
Key modes: `artlist` (article list), `timelinevol` (volume %), `timelinevolraw` (raw counts), `timelinetone` (avg tone series), `tonechart` (tone histogram), `timelinesourcecountry`, `wordcloudimagetags`. `maxrecords` default 75, max 250. `sort` ∈ `datedesc`, `dateasc`, `tonedesc`, `toneasc`, `hybridrel`.

### 2. GDELT — clean article list to CSV
```bash
Q=$(python3 -c "import urllib.parse;print(urllib.parse.quote('heineken'))")
curl -s "https://api.gdeltproject.org/api/v2/doc/doc?query=$Q&mode=artlist&maxrecords=200&timespan=1week&format=json&sort=datedesc" \
| python3 -c '
import sys,json,csv
arts=json.load(sys.stdin).get("articles",[])
w=csv.writer(sys.stdout); w.writerow(["date","source","title","url","tone"])
for a in arts:
    w.writerow([a.get("seendate"),a.get("domain"),a.get("title"),a.get("url"),a.get("socialimage","")])
print(f"# {len(arts)} articles",file=sys.stderr)
' > gdelt_articles.csv
```
GDELT query operators: `domain:bbc.co.uk`, `sourcecountry:UK`, `sourcelang:english`, `tone<-5` (negative only), `(a OR b)`, `-exclude`, `theme:ECON_STOCKMARKET`. Combine freely inside `query=`.

### 3. GDELT — share-of-coverage across competitors
Loop brands, grab `timelinevol`, integrate the daily % — respecting the 5s limit.
```bash
for B in "heineken" "carlsberg" "guinness"; do
  Q=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$B")
  curl -s "https://api.gdeltproject.org/api/v2/doc/doc?query=$Q&mode=timelinevol&timespan=1month&format=json" \
  | python3 -c 'import sys,json;d=json.load(sys.stdin);s=d.get("timeline",[{}])[0].get("data",[]);import statistics as st;print(f"'"$B"': mean vol% = {st.mean([p[\"value\"] for p in s]):.4f}" if s else "'"$B"': no data")'
  sleep 5
done
```

### 4. Marketaux — per-ticker news + native sentiment
Each article carries `entities[]` with a `sentiment_score` (-1..+1) for the matched symbol.
```bash
curl -s "https://api.marketaux.com/v1/news/all?symbols=TSLA,AAPL&filter_entities=true&language=en&limit=3&api_token=$MARKETAUX_TOKEN" \
| python3 -c '
import sys,json
for a in json.load(sys.stdin).get("data",[]):
    for e in a.get("entities",[]):
        print(f"{e[\"symbol\"]:6} {e.get(\"sentiment_score\"):+.3f}  {a[\"title\"][:70]}")'
```
Useful params: `symbols`, `entity_types` (equity, index, etf, cryptocurrency), `industries`, `countries`, `sentiment_gte` / `sentiment_lte` (only articles above/below a tone), `filter_entities=true` (drop articles with no matched entity), `published_after=2026-07-01T00:00`, `search=<keywords>`. To average sentiment for a ticker, page a few requests (respect 100/day) and mean the `sentiment_score`s.

### 5. Guardian — quality full-text articles
```bash
curl -s "https://content.guardianapis.com/search?q=heineken&from-date=2026-01-01&order-by=newest&page-size=20&show-fields=headline,bodyText,byline&show-tags=keyword&api-key=$GUARDIAN_KEY" \
| python3 -c '
import sys,json
r=json.load(sys.stdin)["response"]
print("total",r["total"])
for x in r["results"][:5]:
    print(x["webPublicationDate"][:10], x["sectionName"], "-", x["webTitle"][:70])'
```
Params: `q`, `section`, `from-date`/`to-date` (YYYY-MM-DD), `order-by` (newest/oldest/relevance), `page`/`page-size` (max 200), `show-fields` (add `bodyText` for your own sentiment scoring), `show-tags`. Response is under `.response`.

### 6. HN Algolia — tech discourse & velocity (use https)
```bash
curl -s "https://hn.algolia.com/api/v1/search_by_date?query=anthropic&tags=story&hitsPerPage=20" \
| python3 -c '
import sys,json
for h in json.load(sys.stdin)["hits"]:
    print(f"{h.get(\"points\",0):>4}pts {h.get(\"num_comments\",0):>4}c  {(h.get(\"title\") or \"\")[:70]}")'
```
Endpoints: `/search` (relevance) vs `/search_by_date` (newest first). `tags` ∈ `story,comment,ask_hn,show_hn,job,poll`, ANDed; OR via parens e.g. `(story,poll)`; `author_pg`. Time filter via `numericFilters=created_at_i>UNIXTS` (get ts with `date -v-7d +%s` on macOS). `hitsPerPage` up to 1000.

## Verify
- GDELT: JSON should have `timeline` (timeline modes) or `articles` (artlist). If you instead see a plain-text "Please limit requests to one every 5 seconds" page, you were throttled — `sleep 5` and retry.
- Marketaux: `data[]` non-empty and each `entities[].sentiment_score` is a float in [-1,1]. `{"error":...}` means bad/missing token or quota hit.
- Guardian: `.response.status == "ok"` and `.response.total > 0`. `"API rate limit exceeded"` → you used the shared `test` key; switch to your own `$GUARDIAN_KEY`.
- HN: `nbHits` > 0 and hits carry `points`, `num_comments`, `created_at_i`.

Quick multi-source health check:
```bash
curl -s "https://hn.algolia.com/api/v1/search_by_date?query=test&tags=story&hitsPerPage=1" | python3 -c 'import sys,json;print("HN ok:",json.load(sys.stdin)["nbHits"])'
```

## Pitfalls
- **GDELT 5-second limit is real and unauthenticated-global.** Firing rapid calls returns a throttle *text* page (not JSON) → your `json.load` throws. Always `sleep 5` between GDELT calls; for heavy trend work switch to GDELT's bulk 15-min CSV files or the Web NGrams dataset.
- **GDELT tone is not sentiment-model output** — it's a lexical average tone (-100..+100, most news clusters near 0). Read it as *relative* movement over time, not an absolute "positive/negative" verdict.
- **Marketaux free tier returns only 3 articles/request and ~100 req/day.** Don't design a firehose on it; use it for a sentiment snapshot per ticker. Only Marketaux gives you real per-entity sentiment for free.
- **Guardian `test` key is shared and rate-limits fast** — always register your own key for anything real; it's UK-centric editorial, not a global firehose.
- **HN Algolia needs https** (http can hang/empty in sandboxes) and covers only HN — tech/startup skew, not general news.
- **URL-encode every query** (spaces, quotes, parens) or you'll get 400s / wrong matches. Quote multi-word phrases: `"electric vehicle"` searches the phrase, unquoted searches either word.
- **Different JSON shapes**: GDELT `articles`/`timeline`, Marketaux `data`, Guardian `response.results`, HN `hits`. Normalise to a common `{date,source,title,url,score}` before merging sources.
- **Terms of use**: these free tiers are for analysis/non-commercial or attributed use. Don't republish full article bodies; store IDs/URLs + your derived metrics.
