---
name: qualitative-research
category: strategy
description: >
  Run the qualitative research lifecycle — design, fieldwork
  prep, analysis, synthesis. Covers in-depth interviews (IDIs),
  focus groups, ethnographic fieldwork, diary studies, paired
  conversations, expert interviews, co-creation workshops,
  shop-alongs, online communities, projective techniques, and
  Claude-assisted theme coding of transcripts at scale. Produces
  discussion guides, screeners, coding frameworks, theme maps,
  and synthesis read-outs. Use when the strategy / insight job
  needs depth rather than scale. Trigger on phrases like "design
  a discussion guide", "write a screener", "qual research",
  "qualitative", "focus groups", "IDIs", "in-depth interviews",
  "ethno", "ethnography", "shop-along", "diary study",
  "projective", "code these transcripts", "theme this", "qual
  synthesis", "qual debrief", "what came out of the groups",
  "fieldwork", "moderation", "co-creation", "online community
  insight", "go deep on this audience", "talk to actual people".
  Trigger when the user pastes transcript content and asks for
  themes. Pairs with audience-insight (the output),
  raw-data-research (transcript parsing), data-analyst
  (where qual triangulates with quant), and
  advertising-strategy (the use).
when_to_use:
  - The brief asks "why" not "how many" and needs depth rather than scale
  - Designing a qual study — picking the method (IDIs, groups, ethno, diary, online community), writing the screener, and building the discussion guide
  - An insight territory is forming and needs ground truth or verbatims from real people for a creative team or segmentation
  - Fieldwork prep — moderator brief, stimulus order, recording/transcription setup, observer rules
  - A transcript dump exists and needs coding into themes, quotes, and verbatim cards (including Claude-assisted coding for >20 transcripts)
  - Synthesising fieldwork into a read-out — headline, tensions worth briefing, the insight, and what was dismissed
when_not_to_use:
  - Pure quant tracker work — use data-analyst or data-cut-headline-stats instead
  - One-off audience portraits where qual hasn't actually been done — use advertising-strategy direct
  - Parsing raw transcript files into structured dataframes — that layer is raw-data-research
keywords:
  - qualitative research
  - discussion guide
  - screener
  - focus groups
  - idis
  - in-depth interviews
  - ethnography
  - shop-along
  - diary study
  - online community
  - co-creation
  - projective techniques
  - transcript coding
  - coding framework
  - theme map
  - verbatims
  - saturation
  - moderation
  - qual synthesis
  - fieldwork
similar_to:
  - audience-insight
  - raw-data-research
  - data-analyst
  - advertising-strategy
  - audience-segmentation
inputs_needed:
  - The strategic question(s) — the "why" the brief is asking, and the one thing that makes the fieldwork a win
  - Audience / segments to recruit (behaviour-first quotas), or transcripts if coding/synthesis is the job
  - Category and brand context, including any stimulus or creative direction to test
  - Budget/scope signals — number of sessions, method preference, timeline to saturation
produces: Discussion guides, screeners, coding frameworks, theme maps, and a synthesis read-out with attributed verbatims
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Qualitative research

Qual answers the questions quant can't — **why** people do what
they do, **what they don't say** out loud, **what the category
looks like from inside their head**. It is slower, smaller-
sample, harder to defend statistically, and more useful for
strategy than any other research mode.

This skill covers the four stages:

```
DESIGN  →  FIELDWORK PREP  →  CODING  →  SYNTHESIS
```

## When to use

- The brief asks "why" not "how many"
- An insight territory is forming and needs ground truth from
  real people
- A creative team needs verbatims to write from
- A segmentation needs human texture
- A category nobody on the team has bought from needs lived-
  experience evidence
- A transcript dump exists and needs to become themes / quotes
  / verbatim cards

**Don't use this skill** for: pure quant tracker work (use
[[data-analyst]] / [[data-cut-headline-stats]]) or for one-off
audience portraits where qual hasn't actually been done (use
[[advertising-strategy]] direct).

## Stage 1 — Design the study

### Pick the method to match the question

| Method | Best when… |
|---|---|
| **IDIs (in-depth interviews)**, 60–90 min, 1:1 | Sensitive / personal categories (money, health, sex, grief), expert audiences, B2B |
| **Friendship pairs** | Categories where social dynamics matter (food, drink, status purchases) — pairs unlock candour that strangers don't |
| **Focus groups**, 6–8 people, 90 min | Social norms / public discourse / cultural codes; risky for sensitive personal answers |
| **Ethnography / in-home** | Behaviour you can't trust people to self-report (cleaning, screen-time, parenting) |
| **Shop-along / store-side** | Retail / point-of-purchase decisions; reveals shelf logic and price thresholds |
| **Diary study** | Behaviour over time; mood / consumption rhythms |
| **Online community**, 1–4 weeks | Mid-budget, mid-depth, longitudinal flexibility; good for diary + projective combos |
| **Co-creation workshop** | When you want stakeholders + audience to converge on a territory |
| **Projective techniques** (collage, sentence-completion, brand-as-person, draw-the-category) | When the rational answer is blocking access to the real one |

### How many sessions?

| Method | Default n |
|---|---|
| IDIs | 8–12 per segment to reach saturation |
| Focus groups | 6 groups (2 cities × 3 segments) for a "national" steer |
| Ethno | 6–10 households |
| Diary | 12–24 participants, 1–2 weeks |
| Online community | 25–60 participants, 1–4 weeks |

Saturation = the point at which two consecutive sessions add no
new themes. If you're still hearing new themes at session 10,
do session 11.

### Design the screener

A bad screener gives you the wrong people in the right numbers.
Bias-checks for the screener:

- Avoid "professional respondents" — limit prior research
  participation to ≤2 in 6 months
- Recruit **behaviour first, attitude second**. Anyone can claim
  the attitude. Behaviour is harder to fake.
- Quota the category-relevant variables, not just demographics
- Avoid leading category questions in the screen ("Do you care
  about sustainable…?")
- Pay properly. Underpaid recruits give performative answers.

### Discussion guide structure (universal shape)

```
1. WARM-UP (5–10 min)
   - Easy questions about life, not the category
   - Goal: set the conversational register; respondent should
     feel listened-to before any category question

2. CATEGORY CONTEXT (15 min)
   - How they live with the category today
   - What they actually do (not what they should do)
   - Workarounds, frustrations, rituals, dread

3. INSIGHT EXCAVATION (25–30 min)
   - Projective / oblique questions
   - Tensions, wishes, things they don't say out loud
   - Critical incidents ("tell me about the last time you…")

4. BRAND CONTEXT (15 min)
   - Brand-in-life, not brand-on-shelf
   - Competitors, alternatives, "what would you do if X didn't
     exist"

5. STIMULUS / CREATIVE (optional, 10–15 min)
   - Only if there's a creative direction to test
   - Always after the insight section — never before

6. WRAP-UP (5 min)
   - "What's one thing nobody asked you that I should have?"
   - Sincere thanks, no debrief about the research itself
```

### Question-writing rules

- **Open, not closed.** *"Tell me about…"* not *"Do you…"*
- **One question per question.** No "do you ever… and if so,
  what?"
- **No category framing in early questions.** Ask about life,
  not the product, until trust is established.
- **Projective when the rational answer is in the way.** *"If
  this brand was a person at a party, who would it be?"*
- **Permission to be honest.** *"There's no right answer —
  what's the real reason?"*
- **Silence is a question.** After a difficult answer, wait.
  The follow-on sentence is usually the truth.
- **Never use the brand's preferred vocabulary.** *"Sustainability"*
  in the question primes the answer.

## Stage 2 — Fieldwork prep

- **Brief the moderator** in writing — the 3 key questions, the
  insight territory, the "no-go" topics, and the *one thing*
  we'd consider the trip a win for
- **Stimulus** — print plus on-screen versions, neutral mounts,
  consistent timing across sessions
- **Recording / transcription** — confirm consent on camera /
  audio; default to auto-transcribed (Otter, Descript) + human
  cleanup of the strategic sessions
- **Observer rules** — observers don't ask questions; observers
  don't react out loud; observers write down quotes, not summaries
- **Field log** — moderator writes a 5-line note after each
  session: *what surprised me / what changed my mind / a quote
  to keep / who they reminded me of / what to ask next time*

## Stage 3 — Coding

This is the part most qual studies do badly because it gets
compressed under deadline pressure.

### The coding framework

Build it **iteratively**, not up-front. Start with three or
four broad codes from the discussion guide. Add codes as
sessions reveal them. Merge codes that overlap. Drop codes
nobody hits.

```
CODE                       DESCRIPTION
category_context           what the category looks like in their life
critical_incident          a specific moment they recount
tension                    a contradiction or trade-off
brand_relationship         relationship to the client brand
competitor_relationship    relationship to competitors
verbatim_gold              a sentence worth a quote slide
unsaid                     pauses, "I don't know if I should say this"
projective                 metaphor / projective answer
behaviour                  what they actually do (with evidence)
need_state                 the moment-of-need they're in
```

A good qual coder will:

- Tag every quote with at least one code
- Tag verbatims with **the speaker, not just the file** — for
  attribution
- Use **double-coding** for important segments (two coders,
  reconcile differences; the disagreement is often the most
  interesting line)
- Build a **theme map** as codes group up into themes

### Claude-assisted coding (when scale demands it)

For >20 transcripts, manual coding becomes the bottleneck.
A practical pipeline:

```python
# Pseudocode — actual implementation pairs with
# raw-data-research for the parsing layer
import anthropic
client = anthropic.Anthropic()

CODES = open("coding_framework.md").read()

def code_turn(text, speaker, context):
    msg = client.messages.create(
      model="claude-sonnet-4-6",
      max_tokens=400,
      system=f"""You are a qualitative research coder.
Given a turn of dialogue, return JSON with the codes from this
framework that apply, plus a confidence (0-1) and a one-line
reason.

CODING FRAMEWORK:
{CODES}

Output ONLY valid JSON:
{{
  "codes": ["..."],
  "confidence": 0.0,
  "reason": "..."
}}""",
      messages=[{"role":"user","content":f"Speaker: {speaker}\nTurn: {text}\nPrior context: {context}"}],
    )
    return msg.content[0].text
```

Rules for LLM-assisted coding:

- **Always human-review the high-stakes themes.** Use the LLM
  for breadth coverage, not for the final read.
- **Keep prompts version-controlled.** When the prompt changes,
  the coding changes — track it.
- **Sample-check inter-rater reliability** between LLM and a
  human coder on 10% of turns. <80% agreement → fix the prompt
  or the framework.
- **Never use the LLM to *write* the verbatims back into the
  deck.** Verbatims must be exact, with file + timestamp.

## Stage 4 — Synthesis

### From themes to a read-out

A synthesis is not a list of themes. It is **what we now
believe, organised so a creative team can act on it**.

Synthesis shape:

```
1. THE HEADLINE — one sentence
   "What we now believe about [audience] that we didn't 4 weeks
    ago."

2. THE TENSIONS WORTH BRIEFING — 2–3 max
   Each: theme name, 3 verbatims, why this is the strategic
   move it implies.

3. THE INSIGHT — the four-line construction from [[audience-insight]]

4. THE TONE OF THIS AUDIENCE — how they sound, what they don't
   sound like (input for [[advertising-strategy-copy]])

5. WHAT WE DISMISSED — the themes we heard but won't act on,
   and why

6. WHAT WE'D STILL LIKE TO KNOW — the gaps that need quant or
   another qual wave to close

7. APPENDIX — full theme map, screener, discussion guide,
   field log, anonymised transcripts
```

### Verbatim discipline

Quotes are the credibility currency of qual. Rules:

- Always attribute (segment, age, region, session ID)
- Never edit verbatims for grammar — preserve the cadence
- Use ellipses for cuts; never for emphasis
- Mark verbatim slides with `VERBATIM` in the eyebrow so the
  reader knows it's a quote, not a paraphrase
- Three short verbatims beat one long one. Pick the line, not
  the paragraph.

## Output formats

### Discussion guide

```
DISCUSSION GUIDE — [project, audience]
Moderator: [name]    Duration: 60 min    Recording: ✓ consented

Goal of the session:
  [one sentence — the one thing we want to leave the room
   knowing]

Three questions to leave with answers to:
  1. [strategic question]
  2. [strategic question]
  3. [strategic question]

Section 1 (5 min) — Warm-up
  - [questions]
Section 2 (15 min) — Category context
  - [questions]
Section 3 (25 min) — Insight excavation
  - [questions, including projectives]
Section 4 (10 min) — Brand context
  - [questions]
Section 5 (5 min) — Wrap

Probes — use when:
  - [trigger] → [probe]

Stimulus:
  [list, in order, with neutral mounts]
```

### Theme map

```
THEME MAP — [project]

THEME A: [name]
  Sub-themes:
    A1 — [sub-theme]      n_sessions = 7/12
    A2 — [sub-theme]      n_sessions = 5/12
  Representative verbatims:
    "..." — [seg, age, region]
    "..." — [seg, age, region]
  Tension it points to:
    [one line]

THEME B: …
```

### Synthesis read-out

Use the [[deck-flow-structure]] for ordering. SCQA works well
for qual debriefs:

```
1. Cover
2. The complication — what's changed in our understanding
3. The question we set out to answer
4. The headline — what we now believe (one sentence)
5–7. The three tensions, one per slide, with verbatims
8. The insight (four-line construction)
9. What this means for the strategy
10. What we'd like to know next
```

## Common qual research mistakes to avoid

1. **Asking the brief question literally.** "Do you care about
   sustainability?" gets you nowhere. Ask about what they
   actually buy, why, and when they don't.
2. **Brand mentioned too early.** Hold the brand for the
   second half of the session.
3. **Treating focus groups as a sensitive-topic vehicle.**
   Groups force performance; sensitive topics need IDIs.
4. **Stimulus before insight.** Show creative *after* the
   open ground has been explored, never before.
5. **Single moderator across all sessions assumed neutral.**
   Moderators have biases. Vary moderators on long projects,
   compare reads.
6. **Synthesis = quotes glued to themes.** Synthesis means
   *what we now believe*, with verbatims as evidence.
7. **Sample size theatre.** *"50 IDIs"* is rarely better than
   12 well-recruited ones — most marginal sessions just confirm.
8. **Saturation declared by deadline.** If you're still
   hearing new themes, you haven't saturated.
9. **Verbatims paraphrased.** Once you paraphrase, you've lost
   the evidence.
10. **Qual without triangulation.** Pair qual with the quant
    cuts via [[data-analyst]] — alone, qual is a strong
    hypothesis but not a verdict.

## Tools

- **Transcription** — Otter, Descript, Rev, Whisper-large (local)
- **Coding** — Dovetail, Reduct, Aurelius, Notion (light), Atlas.ti
  / NVivo (heavy)
- **LLM-assisted coding** — Claude API (see code snippet) with
  the framework + verbatim attribution preserved
- **Online communities** — Recollective, Discuss.io, FlexMR
- **Pipeline of transcripts → dataframe** — use [[raw-data-research]]

## Handoffs

- **Output to** [[audience-insight]] (the four-line insight),
  [[advertising-strategy-copy]] (verbatim-flavoured prose),
  [[advertising-strategy]] (the strategic use)
- **Input from** [[raw-data-research]] (transcript parsing,
  speaker / theme structuring), [[audience-segmentation]] (who
  to recruit)
- **Triangulation with** [[data-analyst]] when qual meets quant
- **Deck-flow** via [[deck-flow-structure]], visual via
  [[vccp-media-design]]
