---
name: WLV
category: strategy
description: >
  Write Like Vallance — produce writing in the voice of Charles
  Vallance (chairman and founding partner of VCCP): erudite, witty,
  metaphor-led, optimistic brand-strategy thought leadership. Works
  in ANY format and length — Campaign-style columns and op-eds,
  LinkedIn posts, keynote and conference speeches, forewords and
  book/report intros, award entries, manifestos, internal memos and
  all-staff emails, newsletters, blog posts, byline articles, panel
  intros, tweet threads. This skill does NOT just write — it first
  calls on the research skills to ground every claim in real,
  attributed sources, then writes the voice over that evidence. Use
  it whenever the user wants something "in Vallance's voice", "like
  Charles writes", "a Vallance column / op-ed / post / speech /
  foreword", "write this the way Vallance would", or simply asks for
  VCCP-chairman thought-leadership writing on a brand, advertising,
  media, culture or AI topic. Trigger even on loose phrasings like
  "make this sound like one of Charles's columns" or "draft me a
  Vallance-style think piece on X". Pairs with the research skills
  deep-research, market-research, developed-research,
  data-cut-headline-stats, raw-data-research,
  cultural-semiotics and trend-foresight for evidence, with
  brand-voice for voice-profiling method, and with
  advertising-strategy-copy for the wider VCCP house voice.
when_to_use:
  - User wants writing "in Vallance's voice" / "like Charles writes"
  - A Campaign-style column, op-ed, byline, or think piece on brand, advertising, media, culture, technology or AI
  - A LinkedIn post, newsletter, blog, or tweet thread in that voice
  - A keynote, conference talk, panel intro, or after-dinner speech
  - A foreword, report intro, award entry, manifesto, or all-staff memo
  - Re-voicing existing dry copy into the Vallance register
when_not_to_use:
  - Generating the underlying strategy itself — use advertising-strategy (WLV only voices it)
  - Writing in a brand's own voice — use brand-voice or advertising-strategy-copy
  - Pieces with unsourced numbers, invented quotes, or fabricated studies — the skill refuses these
keywords: [vallance, charles vallance, vccp, thought leadership, column, op-ed, byline, linkedin post, keynote, speech, foreword, award entry, manifesto, memo, newsletter, tweet thread, voice, metaphor, sourced evidence, campaign magazine]
similar_to: [brand-voice, advertising-strategy-copy, advertising-strategy]
inputs_needed:
  - Format (column, LinkedIn post, speech, foreword, memo, thread, etc.)
  - Length (defaults to ~650-word Campaign-column shape if unstated)
  - Topic / argument
  - Audience and venue
  - Any must-include points or examples
produces: A fully voiced Vallance-style piece in the requested format, plus a Sources list of every attributed factual claim
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# WLV — Write Like Vallance

Write anything in the voice of **Charles Vallance**, chairman and
founding partner of VCCP: erudite worn lightly, dry British wit,
argument-by-metaphor, real evidence, and an optimist's turn at the
end. The skill carries its own training corpus — 22 of Charles's
real published columns — and a distilled voice profile, and it
refuses to write a single factual claim it hasn't sourced.

Two non-negotiables sit at the heart of this skill:

1. **Real sources only.** Every statistic, study, quote, date and
   campaign must trace to a genuine, named, checkable source. Never
   fabricate, never misattribute, never round a guess into a fact.
2. **Research before writing.** When a piece needs evidence (almost
   always), call the research skills *first*, gather the real
   material, then write the voice over it.

## When to use

- The user wants writing "in Vallance's voice" / "like Charles writes".
- A Campaign-style column, op-ed, byline, or think piece on brand,
  advertising, media, culture, technology or AI.
- A LinkedIn post, newsletter, blog, or thread in that voice.
- A keynote, conference talk, panel intro, or after-dinner speech.
- A foreword, report intro, award entry, manifesto, or all-staff memo.
- Any length — a three-line LinkedIn hook or a 2,000-word essay.
- Re-voicing existing dry copy into the Vallance register.

**Don't** use it to generate the underlying strategy (that's
[[advertising-strategy]]) — though it pairs with it — and don't use
it to write in a *brand's* voice when the brand has its own (use
[[brand-voice]] / [[advertising-strategy-copy]] there).

## The two reference files

**No local bundle? (remote use)** If these files aren't on disk beside
this SKILL.md, fetch each from GitHub raw (`curl -fsSL` or WebFetch)
before drafting:

- `https://raw.githubusercontent.com/sebduffy-prog/SebDuffy/main/skills/strategy/WLV/references/voice-profile.md`
- `https://raw.githubusercontent.com/sebduffy-prog/SebDuffy/main/skills/strategy/WLV/references/vallance-article-bank.md`

Read both before drafting. They live next to this file:

- **[references/voice-profile.md](references/voice-profile.md)** — the
  operational style guide: the shape of a piece, sentence rhythm,
  diction, the evidence rule, and a do/don't checklist. *Read this
  every time.*
- **[references/vallance-article-bank.md](references/vallance-article-bank.md)**
  — the ground-truth corpus of 22 real columns. Before writing a given
  format/topic, **re-read two or three of the closest pieces** and
  pattern-match the moves. The profile is the summary; the bank is the
  truth.

## Workflow

### 1. Scope the piece
Pin down, asking only what you can't infer: **format** (column,
LinkedIn, speech, foreword, memo, thread…), **length**, **topic /
argument**, **audience and venue**, and any **must-include** points or
examples. If the user just says "a Vallance column on X", proceed with
sensible defaults (≈650 words, Campaign-column shape).

### 2. Research the evidence — *before writing* (mandatory unless told otherwise)
A Vallance piece earns its authority from real, named proof. Decide
what the argument needs — a study, a market stat, a cultural signal, a
quote, a date — then **call the right research skill** and gather it:

| Need | Call |
|---|---|
| Web facts, studies, quotes, news pegs, cited report | [[deep-research]] |
| Market size, competitor, category, industry intelligence | [[market-research]] |
| Long-form category / sector / audience immersion | [[developed-research]] |
| A headline stat from a dataset the user has | [[data-cut-headline-stats]] |
| Parse / clean raw data (PDF, XLSX, scrape) first | [[raw-data-research]] |
| A cultural code, tension, or "is this residual/emergent" read | [[cultural-semiotics]] |
| A trend / signal, weighted and time-horizoned | [[trend-foresight]] |

If no research tool is available, use `WebSearch` / `WebFetch`
directly. **Keep a running source list** as you go — author, title,
publisher/outlet, date, URL. Anything you can't source does not go in
the piece; if a needed fact can't be verified, say so to the user and
write around it rather than inventing it.

### 3. Draft in the voice
With the evidence in hand, write to the voice profile:
- Open on a **hook**, not a throat-clear.
- Build the whole piece on **one frame / metaphor**.
- Weave the **real, attributed evidence** in mid-piece (name the
  source in the prose, the way Charles does: *"a Vanguard study found…",
  "Analytic Partners put the payback at +35%"*).
- Prove it with **precise brand / campaign examples**.
- **Turn optimistic** before the end.
- Land a **witty kicker** — a callback, an aside, the occasional
  deliberate typo gag.
- Short paragraphs, varied sentence length, British spelling, no
  agency cliché, (almost) no exclamation marks.

### 4. Adapt the furniture to the format
Keep the **hook → one frame → real evidence → turn → kicker** spine in
every format; change only the trim:

- **Column / op-ed / byline** — title (pun/question/metaphor), one-line
  dek, ~650 words, sign-off *"Charles Vallance is the chairman and
  founding partner of VCCP."*
- **LinkedIn post** — hook line that stands alone, tight body, line
  breaks for rhythm, one clear idea, soft CTA or question to close. No
  hashtag spam.
- **Speech / keynote** — written for the ear: shorter sentences, more
  repetition and signposting, planted pauses, a callback at the close.
  Mark `[pause]` / `[beat]` only if the user wants delivery notes.
- **Foreword / report intro** — gracious, sets up someone else's work,
  one borrowed idea of his own, generous handover at the end.
- **Award entry** — confident and evidence-dense; lead with results,
  keep the wit but let the numbers carry it.
- **Memo / all-staff email** — warmer, plainer, still one frame and a
  human kicker; drops the dek and sign-off.
- **Thread** — one idea per post, each post able to stand alone, the
  hook in post one.

### 5. Self-check before delivering
Run the do/don't checklist in the voice profile. Then verify the
**source list**: every stat, quote, date and study in the piece appears
in it with a real, checkable reference. Deliver the piece, and append
the **Sources** list (and offer to footnote/inline-cite as the venue
needs).

## Output contract

Deliver:
1. The piece, in the requested format, fully voiced.
2. A short **Sources** list — every factual claim, attributed and
   checkable.
3. (On request) delivery notes for speeches, or alternate hooks/titles.

Never ship a Vallance piece with an unsourced number, an invented
quote, or a fabricated study. The voice is the easy part; the
credibility is the point.
