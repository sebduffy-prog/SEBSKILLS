---
name: wikidata-knowledge-api
category: data-analysis
description: >
  Query structured world knowledge and public-attention signals from Wikimedia — Wikidata
  SPARQL for the entity graph (occupations, birthplaces, genres, org relations), wbsearchentities
  for name→QID entity resolution, the Wikipedia REST summary/extract for one-line descriptions,
  and the Pageviews API for daily/monthly interest-over-time. Reach for this to ENRICH a list of
  people/brands/places with canonical facts, RESOLVE messy names to stable IDs, or measure the
  rise/fall of public attention. All endpoints are free, keyless, and need only a descriptive
  User-Agent. Every call in here was smoke-tested and returns real JSON.
when_to_use:
  - "You have a list of names (artists, brands, cities, companies) and need canonical facts or stable IDs"
  - "Resolving free-text entity names to Wikidata QIDs before joining or deduping"
  - "Pulling occupation / genre / birthplace / country / parent-org relations for a knowledge graph"
  - "Measuring public interest over time (pageviews trend, spikes around a launch/event)"
  - "Fetching a one-sentence description + thumbnail for an entity to enrich a dataset or UI"
when_not_to_use:
  - "You just want a working free endpoint for FX/weather/holidays → use free-api-catalogue"
  - "Government / economic statistical series (GDP, census, ONS) → use govt-open-data-api"
  - "Address→lat/lon geocoding at volume → use geocoding-places-api"
  - "News articles with sentiment / entity extraction → use news-sentiment-api"
  - "Survey-panel audience attitudes (GWI/TGI) → use the GWI Spark MCP, not Wikidata"
keywords: [wikidata, sparql, wikipedia, pageviews, entity resolution, knowledge graph, qid, wbsearchentities, rest api, enrichment, interest over time, dbpedia, linked data, attention signal, sitelinks]
similar_to: [free-api-catalogue, govt-open-data-api, geocoding-places-api, news-sentiment-api, market-data-api]
inputs_needed:
  - "What entities (a name, a list, or an existing QID)?"
  - "What do you want back — facts (SPARQL), an ID (search), a blurb (summary), or a trend (pageviews)?"
  - "For pageviews: which wiki/language project + date range + granularity (daily/monthly)?"
produces: Real JSON — resolved QIDs, SPARQL result bindings, page summaries, or a pageviews time series
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Wikidata & Wikimedia Knowledge API

Four free, keyless Wikimedia endpoints that together cover entity resolution, structured
facts, human-readable blurbs, and attention trends. **The only requirement is a descriptive
`User-Agent`** identifying your app + contact — Wikimedia blocks the default `python-requests`/
`curl` UAs. Set it once and reuse it everywhere.

## When to use

Enriching a list of entities, resolving names → stable IDs, walking the knowledge graph, or
measuring how public interest in something moved over time. If you don't need *structured*
knowledge or *attention* data, a simpler source (see `when_not_to_use`) is faster.

## Prerequisites

- **No API key.** Purely HTTP GET. Works with `curl`, `requests`, or stdlib `urllib`.
- **User-Agent is mandatory.** Format: `app-name/version (contact-email-or-url)`. Missing/generic
  UA → HTTP 403 or 429. This skill uses `WD` below.
- **Rate limits (be polite):** SPARQL ~1 query/sec, 60s query timeout, ~30-day result cap on huge
  queries. REST/Pageviews: ~200 req/s soft ceiling but throttle yourself to a few/sec for bulk.
- **macOS note:** stdlib `urllib.request` is enough — no pip installs needed.

```bash
export WD='wikidata-enrich/1.0 (seb.duffy@vccp.com)'
```

## Recipes

### 1. Resolve a name → QID (entity resolution)

The `wbsearchentities` action fuzzy-matches labels/aliases and returns candidates ranked by
relevance. **Always inspect the `description` to disambiguate** (e.g. "Adele" the given name
Q354370 vs "Adele" the singer Q23215).

```bash
curl -s -H "User-Agent: $WD" \
  'https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json&language=en&limit=5&search=Adele' \
  | python3 -c 'import json,sys;[print(x["id"],"—",x.get("description","")) for x in json.load(sys.stdin)["search"]]'
# Q354370 — female given name
# Q23215  — English singer-songwriter (born 1988)
```

Pick the QID whose description matches your domain. For brands/companies add context to the
search string ("Apple Inc") or verify against a SPARQL `instance of` (P31) check.

### 2. Structured facts via SPARQL

Endpoint: `https://query.wikidata.org/sparql` — pass `query=` (URL-encoded) and
`format=json`. Use the magic `wikibase:label` service to get human labels in one shot.
Key properties: `wdt:P31` instance-of, `wdt:P106` occupation, `wdt:P19` place-of-birth,
`wdt:P136` genre, `wdt:P17` country, `wdt:P749` parent-org, `wdt:P571` inception.

```bash
QUERY='SELECT ?occLabel WHERE {
  wd:Q23215 wdt:P106 ?occ .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}'
curl -s -G 'https://query.wikidata.org/sparql' -H "User-Agent: $WD" \
  --data-urlencode "query=$QUERY" --data-urlencode 'format=json' \
  | python3 -c 'import json,sys;[print(b["occLabel"]["value"]) for b in json.load(sys.stdin)["results"]["bindings"]]'
# singer / songwriter / musician ...
```

**Bulk enrichment pattern** — feed many QIDs with `VALUES`:

```sparql
SELECT ?item ?itemLabel ?birthLabel ?countryLabel WHERE {
  VALUES ?item { wd:Q23215 wd:Q1299 wd:Q383541 }        # Adele, The Beatles, Beyoncé's label...
  OPTIONAL { ?item wdt:P19 ?birth. }                     # place of birth
  OPTIONAL { ?item wdt:P495 ?country. }                  # country of origin
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

Each binding is a `{value, type}` dict. `type: "uri"` values are full entity URLs — strip
`http://www.wikidata.org/entity/` to recover the QID. Missing OPTIONALs are simply absent from
the binding, so use `.get()`, never `[...]`, when reading them.

### 3. One-line description + thumbnail (Wikipedia REST)

`https://{lang}.wikipedia.org/api/rest_v1/page/summary/{Title}` — title is case-sensitive and
space→`_` or `%20`. Returns `extract` (plain-text intro), `description`, `thumbnail`, and the
`wikibase_item` (its QID — a second, title-based route to entity resolution).

```bash
curl -s -H "User-Agent: $WD" 'https://en.wikipedia.org/api/rest_v1/page/summary/Adele' \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["wikibase_item"],"|",d["extract"][:120])'
```

Bridge QID→article: SPARQL `schema:about`/`wikibase:sitelinks`, or the article's summary gives
you `wikibase_item` directly. To go QID→title, query the sitelink:
`SELECT ?a WHERE { ?a schema:about wd:Q23215 ; schema:isPartOf <https://en.wikipedia.org/>. }`.

### 4. Interest over time (Pageviews API)

`https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{project}/{access}/{agent}/{article}/{granularity}/{start}/{end}`

- `project`: `en.wikipedia` (or `de.wikipedia`, etc.)
- `access`: `all-access` | `desktop` | `mobile-web` | `mobile-app`
- `agent`: `all-agents` | `user` (use `user` to exclude bots/spiders)
- `granularity`: `daily` | `monthly`; dates `YYYYMMDD`
- Article title must be URL-encoded; data starts **July 2015**.

```bash
curl -s -H "User-Agent: $WD" \
 'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/Adele/monthly/20240101/20241231' \
  | python3 -c 'import json,sys;[print(i["timestamp"][:6],i["views"]) for i in json.load(sys.stdin)["items"]]'
```

Use `user` agent + a launch/release window to detect attention spikes; monthly smooths noise,
daily catches the exact spike day. A 404 usually means a wrong/redirected title — resolve it via
the REST summary first (it follows redirects and returns the canonical title).

### Python one-liner for reusable calls

```python
import json, urllib.parse, urllib.request
UA = "wikidata-enrich/1.0 (seb.duffy@vccp.com)"
def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA})))
def qid_of(name, lang="en"):
    u = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "wbsearchentities", "format": "json", "language": lang, "limit": 5, "search": name})
    return [(r["id"], r.get("description", "")) for r in get(u)["search"]]
```

## Verify

```bash
# UA set?
[ -n "$WD" ] && echo "UA ok" || echo "run: export WD='app/1.0 (you@example.com)'"
# One end-to-end resolve→facts smoke test:
curl -s -H "User-Agent: $WD" 'https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json&language=en&limit=1&search=Beyonce' \
  | python3 -c 'import json,sys;print("QID:",json.load(sys.stdin)["search"][0]["id"])'
```

Expect `QID: Q36153`. If you get 403/429, your User-Agent is missing or too generic — fix it
and slow down.

## Pitfalls

- **No User-Agent = blocked.** The #1 failure. Set `WD` and pass it on *every* call, including
  redirects.
- **Label service placement:** the `SERVICE wikibase:label {…}` block must come *after* the
  triples that bind the variables, and you request `?xLabel` (variable name + `Label`). Put it
  last in the WHERE.
- **SPARQL timeouts:** open-ended queries (`?s ?p ?o`) over the whole graph time out at 60s.
  Constrain with `VALUES`, specific properties, and `LIMIT`. Batch bulk enrichment ~50 QIDs/query.
- **URIs vs QIDs:** SPARQL returns full entity URIs; strip the prefix. Labels can be missing for
  entities without an English label — handle blanks.
- **Wikipedia title ≠ Wikidata label.** Titles are case/redirect-sensitive; resolve ambiguous
  ones through the REST summary (it normalizes + follows redirects) before pageviews.
- **Pageviews gaps:** data only from 2015-07; brand-new or renamed articles return sparse/404.
  A mid-month partial (e.g. current month) shows a truncated count — don't read it as a crash.
- **Disambiguation is on you.** `wbsearchentities` returns candidates, not the answer. Always
  confirm with the description or a P31 instance-of check before joining data.
- **Licensing / attribution:** Wikidata is CC0 (free to reuse); Wikipedia text is CC BY-SA —
  attribute if you republish extracts.
