---
name: recording-studio
category: frontend-and-design
description: >
  Stand up a branded, deploy-ready artist cultural-intelligence & campaign-tracking platform ("The Recording Studio")
  for a Warner Music artist by re-skinning and re-configuring the MuseRecordingStudio template. Use this whenever
  someone says "build a recording studio for <artist>", "spin up an artist tracking platform", "new artist
  campaign dashboard", "Warner artist intelligence site", "clone the Muse studio for <artist>", or wants the
  social-listening + audience + SOAP/POAP + music/streaming/YouTube/Reddit tracking dashboard branded for a new
  act. Works WITH the user to set the depth of detail and the personal branding, offers a template tab menu, wires
  social listening in by API, ingests an uploaded GWI audience file, and always finishes looking perfect. This is
  a marquee /sebduffy recipe — reach for it even if the user just says "recording studio".
when_to_use:
  - Building or branding an artist tracking/campaign platform for Warner Music (or any music campaign)
  - The user names an artist and wants a dashboard covering audience, social, streaming, strategy, campaign plan
  - Re-skinning the Muse/Madonna "Recording Studio" for a different artist
  - The user has a GWI audience export and/or a SOAP/POAP deck and wants it turned into a live platform
  - The user wants social listening (Brand24 / Reddit / YouTube) tracked for an artist in one place
when_not_to_use:
  - Just need a generic dashboard from arbitrary data → use quick-dashboard or web-artifacts-builder
  - Just theming/colour tokens for any site → use theme-factory or brand-color-token-system
  - Just audience segmentation analysis, no platform → use audience-segmentation or audience-insight
  - A chat-driven multi-workspace canvas builder → that is The-Recording-Studio (a different product), not this
  - Building a slide deck of the campaign → use pptx / data-driven-deck-generator
keywords: [recording studio, artist platform, warner music, wmg, cultural intelligence, campaign tracking, social listening, brand24, gwi audience, soap, poap, strategy on a page, plan on a page, tease release sustain, muse, madonna, artist dashboard, spotify tracking, reddit graphrag, campaign calendar, next.js platform, vercel deploy, artist branding]
similar_to: [theme-factory, brand-color-token-system, audience-insight, audience-segmentation, connect-public-api, requirement-elicitation, design-approval-gate]
inputs_needed:
  - Artist name + campaign name (and the studio wordmark text, top/bottom)
  - Depth level wanted (Lite / Standard / Full) and which tabs to enable
  - Brand primary colour (+ deep shade), font, background image, login password
  - Audience segments (keys, labels, colours) — MUST match the GWI CSV column order
  - The GWI audience export file(s), and any Reddit/YouTube corpora (or ship "awaiting data")
  - The artist's SOAP (Strategy on a Page) + POAP (Plan on a Page) content
  - Data-source IDs (Spotify artist ID, Last.fm name, YouTube channel, Wikipedia page, Brand24 project) + which env vars exist
produces: A branded, Vercel-deployable Next.js artist studio — one artist.config, a Market Research data pack, two AI prompt templates, a public image set, and enabled/branded tabs — ready to preview and ship
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# The Recording Studio — per-artist platform generator

Generate a branded artist **cultural-intelligence + campaign-tracking platform** for a Warner artist by
re-skinning and re-configuring the proven **`MuseRecordingStudio`** template. Every artist has different tags,
audiences and needs — but the **core site is shared**. Your job is to fill one clean per-artist config surface,
not to hand-edit 40 files. It must end up looking **perfect** — it's client-facing.

## What it builds

A Next.js 16 (pages router) SPA deployed on Vercel, with up to **11 tabs**:

| Tab | What it tracks |
|---|---|
| Dashboard | KPI/summary roll-up across all sources |
| Media | Cultural/news feed (Brave + RSS + GDELT) + Media Trend Index |
| Music | Spotify / Kworb / Last.fm / Apple / Wikipedia streaming & charts |
| Reddit / YouTube | Reddit "universe" GraphRAG + YouTube comment themes |
| Audience | GWI segment infographics (Index / Column % / Responses) |
| Strategy | **SOAP** (Strategy on a Page) + **POAP** (Plan on a Page), inline-editable |
| Tactics | Collaborative media-plan board |
| Ideas | Collaborative idea board |
| Calendar | Campaign block plan (defaults to the SOAP window) |
| Locations | Leaflet map, pins layered Tease / Release / Sustain |
| Research | Doc-upload knowledge base + Bear Hunt |

Plus always-on chrome: a live `MentionsTicker`, and a dormant `SocialDashboard` you can enable. Exports:
multi-sheet XLSX / CSV-zip / Word "Full Export".

Fixed for every artist: the Next.js shell, all tab engines, the API logic, the storage layer (`lib/kv.js` →
Vercel Blob), and the agency kicker **"VCCP Media Cultural Intelligence"**. Never rebrand the agency kicker.

## The core principle

Artist identity is currently **hardcoded across ~15–40 sites** (colour constants copy-pasted per component,
strategy prose in JSX, Spotify/Reddit/Brand24 IDs in API routes). So the platform generator's real work is:

> **hoist everything per-artist into one config surface, then fill that surface for the new artist.**

### Step 0 (once): refactor the template into a config surface

Before the first new artist, do a one-time refactor of `MuseRecordingStudio` so the per-artist bits read from a
single module. This is the difference between a real generator and a fragile find-replace. Hoist into
`lib/artist.config.js`:

1. **Identity** → header call-site props (`PulseParticleText`, `MuseDistortionWordmark` top/bottom), kicker, `loginPassword` (replaces the `pw === "muse2026"` literal at `pages/index.jsx:1034`).
2. **Brand** → `lib/brandColors.js` (`WMG_RED`, `WMG_RED_DEEP`), the font `<link>` + family in `pages/_document.jsx`, `public/*_BG.png`. Keep the duplicated **data-viz palette** per component (chart series are load-bearing — do not centralise those).
3. **Audience taxonomy** → `lib/audiences.js` segments **and** the positional column map in `getStaticProps` (`pages/index.jsx` ~761–800). **These are coupled — treat as one unit.**
4. **Data-source IDs** → the API-route constants (`kworb.js` Spotify ID, `lastfm.js` ARTIST, `spotify.js`, `youtube-rag.js` channel, `wikipedia-pageviews.js`, `google-trends.js`, `apple-charts.js` `isMuse()`, `gdelt.js`, `media-index.js`).
5. **Keyword taxonomies** → Reddit/YouTube theme buckets + `social-dashboard.js` positive/negative/theme word lists.
6. **Strategy content** → `StrategyRecommendations.jsx` (`OBJECTIVES`, `GROWTH_LEVERS`, `PILLARS`, `EXECUTIONS`).

Everything else (`kv.js`, boards, export, map, calendar, chart primitives, `DocUploader`) is already
artist-agnostic. Use the `assets/artist.config.template.jsonc` in this skill as the schema.

## The build flow (per artist)

**1. Interactive intake** — run `requirement-elicitation` first. Work WITH the user to pin down: the artist +
campaign, the **depth level**, the tabs to enable, the brand (colour/font/bg/wordmark/password), the audience
segments, the data-source IDs, and whether they have data now or want an "awaiting data" scaffold. Don't guess
branding — it has to be perfect.

**2. Pick the depth level:**
- **Lite** — Dashboard + Audience + Strategy (SOAP/POAP). Fastest; good with only a GWI file + a deck.
- **Standard** — Lite + Media + Music + Social listening + Tactics + Calendar.
- **Full** — all 11 tabs incl. Reddit/YouTube GraphRAG, Locations map, Ideas, Research corpora.

**3. Write the per-artist file set** (this is the whole job):
- `lib/artist.config.js` — from the template schema (identity, brand, tabs, audiences, pillars, strategy, data sources, taxonomies).
- `Market Research/` **data pack** — the uploaded **GWI audience file(s)** (`gwi_demographics.csv`, `gwi_music.csv`, `gwi_media.csv`), any Reddit/YouTube corpora, report PDFs.
- `strategy-prompt.md` + `youtube-themes-prompt.md` — the per-artist AI prompt templates (positioning, KPIs, categories, themes) that drive the Anthropic-SDK content.
- `public/` **image set** — homepage rotation + login/background image.
- Enabled/relabelled **tabs** per the depth level.

**4. Brand to perfection** — set the primary colour + deep shade, font, background, wordmark. Keep the dark
shell. Then **run `design-approval-gate`**: preview and get explicit sign-off before "done". It always needs to
look perfect.

**5. Deploy** — `vercel` (or push to the connected repo). Set env vars in Vercel (never commit them).

## Social listening — a malleable, swappable adapter

Keep social listening **provider-agnostic** — do NOT hardwire it to one vendor. Treat the source as a pluggable
adapter selected in `artist.config.js` under `socialListening.provider`, so it can be swapped per artist/campaign:

- **Any social-listening API** (Brand24, Brandwatch, Talkwalker, Sprout, Meltwater, a bespoke endpoint…) — the
  adapter normalises mentions/sentiment/volume into the shape `MentionsTicker` + the social dashboard expect.
- **Uploaded / exported data** — a mentions CSV/JSON dropped into `Market Research/` when there's no live API.
- **Owned channels** — the built-in Reddit corpus + YouTube live API path (`social-dashboard.js`), driven by
  per-artist keyword/theme/sentiment lists in config.

`pages/api/brand24.js` is the **reference adapter that ships wired** (Brand24 Data API, `X-Api-Key`, env
`BRAND24_API_KEY` + `BRAND24_PROJECT_ID`) — use it as the template for a new adapter, not as the only option. The
adapter contract is: given the config's provider + credentials, return normalised `{ mentions, sentiment, volume,
themes }`; everything downstream (ticker, dashboard, export) stays the same. So "API it in" = point the config at
whichever provider the artist uses, or fall back to uploaded data.

## Audience — the uploaded file (get this exactly right)

Structured audience data is a **build-time GWI CSV**, read by `getStaticProps`. Row shape:
`{ question, name, metric∈{Index|Column %|Row %|Responses}, totals, <segmentKey1..N> }`. The **CSV column order is
positionally coupled to the `audiences` segment keys** in config — they must have the same count and order, or the
Audience tab renders the wrong segment. This is the single most error-prone step: change the segments and the CSV
columns together. `DocUploader` (docx/txt) handles unstructured research docs separately (Research → Bear Hunt).

## SOAP & POAP (the Strategy tab)

- **SOAP = Strategy on a Page** — objectives + KPIs, the **three growth levers**, the growth-audiences diagram, and the **Tease / Release / Sustain** comms pillars. The pillars are referenced app-wide (map layers, calendar blocks), so set them first.
- **POAP = Plan on a Page** — Why (distinctive execution) · How (executional routes) · What (OESP owned/earned/shared/paid mix), plus phasing/budget.

Both live in `StrategyRecommendations.jsx`, are inline-editable, and persist via `strategy-overrides.js` → KV
("reset to default" restores config). Seed them from the artist's SOAP/POAP deck; if absent, ship the
default/"awaiting data" state and fill later.

## Data levels & "awaiting data"

`getStaticProps` `try/catch`es every file to empty arrays, so a new artist with **no corpus yet still ships** —
scaffold now with a visible "awaiting data" state, wire live APIs (IDs + env) first, add build-time corpora
later. (Framework first, data later.)

## Verify

Two different kinds of "done" — don't conflate them:

1. **Functional QA (structure, not taste)** — run `assets/qa-smoke.mjs` against the generated repo,
   then work `assets/qa-checklist.md` by hand for what it can't automate (Node is not on PATH on this
   Mac — use the portable runtime: `~/.local/runtimes/node-v22.17.0-darwin-arm64/bin/node`):
   ```
   ~/.local/runtimes/node-v22.17.0-darwin-arm64/bin/node assets/scripts/qa-smoke.mjs \
     --old-artist "Muse" --artist "<New Artist>" --password "<new password>"
   ```
   It checks: build succeeds (incl. the empty-`Market Research/` awaiting-data path), no leaked
   template-artist string outside `Market Research/`/`public/`, login gate rejects the template
   default password, agency kicker still exactly "VCCP Media Cultural Intelligence", and audience
   segment count matches the GWI CSV column count. This is deliberately blind to whether the
   audience segmentation, ideas, or strategy content are any *good* — that's not QA-able by a script.
2. **Design sign-off (taste, not structure)** — `design-approval-gate`: screenshots of every enabled
   tab, human approves it looks perfect on desktop + mobile. Only run this once step 1 is clean —
   don't waste a design review on a build that's structurally broken.

## Pitfalls

- **Audience ↔ CSV coupling** — the #1 bug. Segments and GWI columns must match count + order.
- **Scattered constants** — if you skip Step 0, you'll be editing ~40 files per artist and it will drift. Do the refactor once.
- **Don't rebrand the agency** — "VCCP Media Cultural Intelligence" is fixed; the *artist* brand is colour + imagery + wordmark, not a logotype.
- **Chart palette** — keep the per-component data-viz colours; only swap the primary accent, or charts lose meaning.
- **Base on Muse, not The-Recording-Studio** — the latter is a different (canvas-builder) product.
- **Env vars** — set in Vercel, never commit. Missing keys degrade gracefully to cached/empty, not crashes.
