---
name: insight-to-deck-autopilot
category: recipes
description: >-
  Recreate an agency's core money-maker — the research-to-branded-pitch-deck pipeline that
  tools like Gamma, Tome and Decktopus promise — as a fully local combo. Chain deep desk
  research into headline-stat extraction, hard number-guarding, and a native branded .pptx
  in one autopilot run: brief in, cited insight-driven client deck out. Reach for this when
  someone says "turn this research into a deck", "build me the pitch from scratch", or wants
  an end-to-end insight-to-slides generator rather than any single step.
when_to_use:
  - You have a topic/brief and need a finished, cited, branded pitch deck with no manual step between
  - Recreating a Gamma / Tome / Decktopus "prompt to deck" flow but with real research and guarded numbers
  - Producing a repeatable insight-to-slides pipeline for new-business or planning pitches
  - You want every headline stat on a slide traceable to a source and sanity-checked before it ships
  - Applying the VCCP Media house look to an auto-generated deck in the same run
when_not_to_use:
  - You only need the research report, no slides — use `deep-research` or `market-research` alone
  - You already have clean stats and just need slides — use `data-driven-deck-generator` directly
  - You only want to verify numbers in an existing deck — use `stat-check-review` alone
  - You just need to read/parse/lightly edit an existing .pptx — use `pptx`
keywords: [insight-to-deck, research-to-deck, pitch deck, autopilot, gamma, tome, decktopus, deep research, headline stats, stat check, data-driven deck, branded deck, pptx, vccp media, end-to-end, agency pipeline]
similar_to:
  - deep-research
  - market-research
  - data-cut-headline-stats
  - stat-check-review
  - data-driven-deck-generator
inputs_needed: >-
  A research brief or topic (audience, market, category question), a brand spec (VCCP Media or
  client palette + fonts, optional logo PNG), and a rough slide plan / narrative arc. Optional:
  seed sources or a prior data cut to anchor the research, and a .pptx template to inherit theme.
produces: >-
  A single branded .pptx pitch deck whose headline stats are extracted from cited desk research,
  each number sanity-checked, rendered as native editable charts and insight titles in the VCCP
  Media (or client) look — plus the underlying research report and a stat-check audit log.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Insight-to-Deck Autopilot

## What it recreates

The "prompt in, finished deck out" experience sold by **Gamma**, **Tome**, **Beautiful.ai**
and **Decktopus** — but with two things those tools lack: *real, cited desk research* feeding
the content, and a *numbers guard* so a wrong stat never lands on a client slide. This is the
agency money-maker made reproducible: a brief becomes a branded, insight-driven pitch deck end
to end, with a paper trail behind every figure.

## Feasibility

**GREEN — fully reproducible locally.** Every step is an existing SEBSKILLS skill; nothing here
needs an external GPU, paid image model, or bespoke key beyond what `deep-research` already uses
for web search. The research step (`deep-research` / `market-research`) does hit the live web, so
output quality varies with what is publicly available — but the pipeline itself runs to completion
locally and produces a real .pptx. No step is amber or red. High commercial pull for VCCP because
it collapses a multi-day planner-plus-designer job into one guided run.

## The combo

An ordered chain of real sibling skills — `/sebduffy` can hand off to each by name:

1. **`deep-research`** (or **`market-research`** for category/audience briefs) — fan out web
   searches, fetch and adversarially verify sources, and synthesise a cited research report from
   the brief. This is the raw material; keep the citations.
2. **`data-cut-headline-stats`** — mine that report for the punchy, presentable numbers: pull the
   headline stats, frame each as a slide-ready one-liner, and keep the source reference attached
   to every figure.
3. **`stat-check-review`** — guard the numbers. Recompute and stress-test each extracted stat
   (denominator sanity, base rates, GRIM/percentage plausibility, significance claims). Anything
   that fails is corrected or dropped *before* it reaches a slide. This is the step the commercial
   tools skip.
4. **`data-driven-deck-generator`** — bind the surviving stats to native, editable python-pptx
   charts and auto-write insight titles from the numbers, following the slide plan / narrative arc.
5. **`theme-factory`** + **`vccp-media-design`** — apply the house look: palette, fonts, logo,
   layout tokens. Use `theme-factory` to lock the token set, `vccp-media-design` for the VCCP Media
   brand system (swap for a client brand spec when pitching externally).
6. **`pptx`** — final assembly, template inheritance, speaker notes, and a clean export that opens
   correctly in PowerPoint / Keynote / Google Slides. Also used to render slides to images for QA.

## Prerequisites

- Web access for step 1 (`deep-research` uses live search + fetch).
- Python with `python-pptx` available (the deck skills rely on it) — the deck generator will flag
  if it is missing.
- A brand spec: VCCP Media tokens are built in via `vccp-media-design`; for a client pitch, supply
  hex palette, font names, and a logo PNG.
- A slide plan / narrative arc. If you don't have one, let `data-driven-deck-generator` propose the
  default insight-per-slide structure and edit from there.

## Run it

1. **Frame the brief.** State the audience/market/category question crisply. If it is
   underspecified, answer the 2-3 clarifying questions `deep-research` asks first — a vague brief
   produces a vague deck.
2. **Research.** Invoke `deep-research` (or `market-research`) with the brief. Save the cited report;
   do not discard sources — steps 2 and 3 need them.
3. **Extract.** Run `data-cut-headline-stats` over the report to produce a list of candidate headline
   stats, each with its slide-ready framing and source pointer.
4. **Guard the numbers.** Run `stat-check-review` on that stat list. Fix or cut every flagged figure.
   Only the survivors proceed. Keep the audit log — it is your defensibility if a client challenges a
   number.
5. **Build the deck.** Feed the checked stats + the slide plan into `data-driven-deck-generator` to get
   native charts and computed insight titles.
6. **Brand it.** Lock tokens with `theme-factory`, then apply `vccp-media-design` (or the client brand)
   so palette, fonts, and logo are consistent across every slide.
7. **Assemble + export.** Use `pptx` to inherit any template master, add speaker notes, and export the
   final .pptx.
8. **Gate it.** Before calling it done, pass through `design-approval-gate` — a rendered preview plus
   explicit sign-off — since this is a client-facing artefact.

## Verify

- **Every stat is traceable.** Pick three headline numbers at random; each must resolve to a source in
  the step-1 report. No orphan figures.
- **The stat-check audit log is clean.** No unresolved flags from `stat-check-review` carried into the
  final stat list.
- **The deck opens clean.** Render slides to images via `pptx` and eyeball for overflow, overlap, and
  contrast; confirm charts are native/editable, not flat screenshots.
- **Brand fidelity.** Palette, fonts, and logo match the VCCP Media (or client) spec on every slide.
- **Narrative holds.** Read the insight titles alone top-to-bottom — they should tell the story without
  the body copy.

## Pitfalls

- **Garbage brief in, garbage deck out.** The research step is only as good as the framing — don't skip
  the clarifying questions.
- **Skipping the guard.** The temptation is to jump research → deck. `stat-check-review` is the whole
  differentiator versus Gamma/Tome; a wrong stat in a pitch is a credibility hit. Never bypass step 3.
- **Losing citations between steps.** If `data-cut-headline-stats` drops the source pointer, you can't
  verify later. Carry the reference on every stat through to the deck's notes.
- **Over-fitting the narrative to the data.** Let the checked numbers shape the arc; don't force stats to
  fit a pre-written story (that's the p-hacking screen `stat-check-review` also watches for).
- **Brand drift on charts.** The deck generator and the brand skills can disagree on chart colours —
  apply `vccp-media-design` *after* chart generation and re-check contrast.
- **Treating it as one-click.** It's an autopilot, not an oracle: review the report, the stats, and the
  rendered deck at each handoff. The value is the guarded pipeline, not blind automation.
