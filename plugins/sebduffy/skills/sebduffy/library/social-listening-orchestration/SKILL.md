---
name: social-listening-orchestration
category: strategy
description: >
  Run a full social-listening study end to end over Brand24 or
  Brandwatch — not just a raw connector pull. Designs the boolean
  query set (brand + competitors), pulls mentions and daily volume
  within the 31-day API window, computes Share of Voice across the
  set, clusters conversation into themes, detects spikes, tracks
  sentiment over time, and writes it up for a strategy or comms deck.
  Trigger on "social listening", "listening study", "buzz analysis",
  "share of voice", "SOV", "Brandwatch query", "Brand24 mentions",
  "conversation audit", "sentiment tracking", or "spike detection".
when_to_use:
  - A brief needs to know what audiences are actually saying about a brand or category online
  - You must size Share of Voice for a brand against a named competitive set
  - A campaign or crisis needs spike/anomaly detection and a sentiment-over-time read
  - A strategy deck needs themed, quotable conversation clusters (not a raw mention dump)
  - You have Brand24 or Brandwatch access and need a repeatable study, not one-off queries
when_not_to_use:
  - Search-demand momentum rather than social conversation — use share-of-search
  - Survey/panel attitudes and audience sizing — use audience-insight or the GWI connector
  - A one-off single-tool call with no analysis layer — call the connector directly
  - Paid-media SOV from spend data — use media-strategy / attention-planning-metrics
  - Broad web/desk research on a topic — use developed-research or deep-research
keywords:
  - social listening
  - share of voice
  - sov
  - brandwatch
  - brand24
  - boolean query
  - mentions
  - sentiment analysis
  - theme clustering
  - spike detection
  - anomaly detection
  - buzz analysis
  - conversation audit
  - reach
  - net sentiment
  - consumer research api
similar_to:
  - share-of-search
  - competitive-comms-audit
  - audience-insight
  - trend-foresight
  - cultural-semiotics
inputs_needed:
  - Access to Brand24 (MCP connector or X-Api-Key) OR Brandwatch (OAuth token + projectId)
  - Focal brand plus a competitive set (2-6 brands, same category and market)
  - Market/geography and language scope, and a date window
  - The strategic question the study must answer (SOV, crisis, launch, positioning)
produces:
  - A boolean query set (brand + competitors, inclusions/exclusions)
  - Share-of-Voice table + per-day SOV series across the set
  - Themed conversation clusters with representative quotes
  - Spike/anomaly log and a sentiment-over-time read
  - A written study section ready for a strategy or comms deck
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Social Listening Orchestration

Turn a raw listening connector into a **study**: query design → data pull →
Share of Voice → themes → spikes → sentiment → write-up. Grounded against the
real Brand24 Data API and Brandwatch Consumer Research API so the calls are
correct, not fabricated.

## When to use

Use when someone needs the *analysis*, not just the mentions: "what is the
conversation about X, how do we sit vs competitors, and what changed." If they
only want one connector call, skip this and call the tool directly.

## Prerequisites (honest)

You need real access to one of these platforms — there is no free public tier:

- **Brand24** — either the `Brand24` MCP connector (authenticate first) or a
  Data API key sent as the `X-Api-Key` header. Base URL
  `https://api-data.brand24.com`. You pull from *existing projects* (each project
  is a saved keyword monitor); the API does not run ad-hoc booleans on demand,
  so the boolean lives in the project config.
- **Brandwatch** (Consumer Research) — OAuth bearer token from `/oauth/token`
  (valid ~1 year for an API user), a `projectId`, and one or more `queryId`s.
  Base URL `https://api.brandwatch.com`. Booleans are authored as *queries* in
  the project.

Both cap a single data call at a **31-day date range** — you chunk longer
windows. `python3` (3.9 on this Mac) for the analysis helper; no extra packages.

## Recipe 1 — Design the boolean query set

One query per brand in the set so SOV is comparable. For each brand:

- **Core**: brand name + obvious variants/handles. `"IRN-BRU" OR "IRN BRU" OR irnbru OR @irnbru`
- **Disambiguate** with `AND` context or `NOT` exclusions for homonyms
  (e.g. `apple AND (iphone OR mac OR ios) NOT (fruit OR pie OR orchard)`).
- **Scope**: language + country filters; decide whether to include retweets/reposts
  (usually exclude for a cleaner conversation read, include for reach).
- Keep the *structure* identical across competitors — same source set, same
  filters — or the SOV is apples-to-oranges.

Brandwatch queries are validated in-platform (`/projects/{projectId}/queries`);
Brand24 booleans are set in each project's keyword config. Confirm each query
returns a sane volume before trusting the study.

## Recipe 2 — Pull mentions + daily volume (Brand24)

List projects, then pull per project. Chunk the window to ≤31 days.

```bash
KEY=$BRAND24_API_KEY
BASE=https://api-data.brand24.com/api-data/v1
# 1. find your project / account ids
curl -s -H "X-Api-Key: $KEY" "$BASE/account/$ACCOUNT_ID/projects_list/"
# 2. daily volume trend (per brand project)
curl -s -H "X-Api-Key: $KEY" \
  "$BASE/project/$PID/mentions/count?date_from=2026-06-01&date_to=2026-06-30"
# 3. the mentions themselves (cursor-paginated) for quotes + themes
curl -s -H "X-Api-Key: $KEY" \
  "$BASE/project/$PID/mentions?date_from=2026-06-01&date_to=2026-06-30"
```

Other useful Brand24 endpoints on `/project/{PID}/`: `mentions/sentiment`,
`mentions/reach`, `topics`, `project_events` (built-in anomaly/spike list),
`trending-hashtags`, `most-followers`, `demographics`, `ai-summary`.

Prefer the connector's built-ins where they exist (`topics`, `project_events`,
`ai-summary`) — then layer the cross-brand analysis this skill adds on top.

## Recipe 2b — Pull mentions + aggregates (Brandwatch)

```bash
TOK=$BW_TOKEN; BASE=https://api.brandwatch.com/projects/$PROJECT_ID
# mentions (pageSize up to 5000, page indexed from 0)
curl -s -H "Authorization: bearer $TOK" \
  "$BASE/data/mentions?queryId=$QID&startDate=2026-06-01&endDate=2026-06-30&pageSize=5000&page=0"
# aggregate volume / sentiment (feeds the dashboards)
curl -s -H "Authorization: bearer $TOK" \
  "$BASE/data/volume/months/queries?queryId=$QID&startDate=2026-06-01&endDate=2026-06-30"
curl -s -H "Authorization: bearer $TOK" \
  "$BASE/data/sentiment/days?queryId=$QID&startDate=2026-06-01&endDate=2026-06-30"
```

`fulltext` endpoint gives full text instead of a snippet. Aggregate the daily
volume per query into the shape the helper expects.

## Recipe 3 — Share of Voice + spike detection

Reshape each brand's daily volume into `{brand: [{date,count},...]}` and run:

```bash
python3 scripts/listening_analysis.py --infile counts.json --window 7 --z 2.5
```

Returns overall SOV %, a per-day SOV series, and rolling-z-score spike days per
brand (default: a day whose volume is ≥2.5σ above the prior 7-day mean). Cross-
check spikes against Brand24 `project_events` — if both agree, it is real. Feed
the SOV table straight into the deck.

## Recipe 4 — Theme clustering

Start from the platform's own themes (Brand24 `topics`, Brandwatch `topics`
endpoint), then refine by hand — auto-topics are noisy:

1. Pull a representative mention sample (top by reach + a random slice, not just
   the loudest).
2. Cluster into 4-8 named themes (e.g. *product taste*, *price/value*, *nostalgia*,
   *health backlash*). Name them in the audience's language.
3. For each theme record: share of conversation, net sentiment, 2-3 verbatim
   quotes (with source + reach), and whether it is rising or fading.

## Recipe 5 — Sentiment over time + write-up

Pull `mentions/sentiment` (Brand24) or `data/sentiment/days` (Brandwatch), compute
**net sentiment = (positive − negative) / total** per day, and overlay it on the
volume spikes: a spike with collapsing net sentiment is a risk; a spike with
positive sentiment is earned attention. Then write the study:

- **Headline**: SOV standing + the one thing that changed.
- **SOV table** across the set, with direction of travel.
- **Themes** (Recipe 4), each with a quote and a "so what".
- **Spikes** log: date, driver, sentiment, reach.
- **Recommendation** for strategy/comms — hand to competitive-comms-audit or
  advertising-strategy.

## Verify

- `python3 -m py_compile scripts/listening_analysis.py` — helper parses.
- SOV percentages across the set sum to ~100 (±rounding).
- Every quoted mention is traceable to a real URL/source and date — never
  invent verbatims.
- Spot-check one API call per platform returns HTTP 200 with non-empty data
  before trusting downstream numbers.
- Spikes flagged by the helper reconcile with the platform's own event list.

## Pitfalls

- **31-day cap**: both APIs reject wider ranges — always chunk and stitch.
- **Uneven query structure** makes SOV meaningless — same sources, same filters,
  same retweet policy across all brands.
- **Bot/retweet inflation**: a viral repost can dwarf genuine conversation.
  Report reach and mention count separately; consider excluding reposts for the
  conversation read.
- **Auto-topics are not themes** — always human-refine; the platform clusters
  by keyword co-occurrence, not by strategic meaning.
- **Sampling bias**: pulling "top" mentions only skews to the loudest voices —
  mix in a random slice.
- **Brand24 booleans live in projects**, not in the API call — you cannot pass an
  ad-hoc boolean to the Data API; set it in the project first.
- **Sentiment is directional, not truth** — auto-sentiment misreads sarcasm and
  slang; sanity-check the net-sentiment swings against the actual quotes.
- **Relative, not census**: listening covers only public, indexed posts — never
  claim it as total market opinion.
