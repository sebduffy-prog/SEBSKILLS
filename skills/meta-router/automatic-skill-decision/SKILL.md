---
name: automatic-skill-decision
category: meta-router
description: >
  Given any user request, silently pick the right skill(s) from a SKILL.md manifest by
  scoring trigger keywords + semantic intent, then apply a no-match gate and an ambiguity
  gate so you route confidently, ask when it's a near-tie, and fall back when nothing fits.
  This is the routing brain behind /sebduffy. Use when you need to decide "which skill
  handles this", "auto-select a skill", "route this request", "map intent to skill",
  "dispatch to the best-matching skill", "should I even use a skill for this", or to build
  the selector that a slash-command or dispatcher calls before doing any work.
when_to_use:
  - "A dispatcher / slash command must choose one or more skills for a free-text request before acting"
  - "You have a big skills library and need to auto-select the right one instead of guessing"
  - "You want a no-match fallback so out-of-scope requests don't force a wrong skill"
  - "Two skills both look plausible and you need a principled way to ask the user which"
  - "You're wiring the routing layer behind /sebduffy or a similar 'do the right thing' command"
  - "You need to explain WHY a request routed where it did (score + margin + shortlist)"
when_not_to_use:
  - "Turning ONE vague request into concrete requirements before work -> requirement-elicitation"
  - "The request needs SEVERAL skills run in sequence/parallel and stitched -> skill-chaining-composer"
  - "No existing skill fits and you need to spec a new one -> skill-gap-detector"
  - "Routing a request between LLM MODELS by cost/quality (not between skills) -> model-triage-router"
keywords: [skill router, skill routing, auto-select skill, which skill, intent routing, semantic router, route request, skill selection, dispatcher, manifest, trigger matching, score threshold, ambiguity gate, no-match fallback, meta router, sebduffy, routellm, intent classification]
similar_to: [requirement-elicitation, skill-chaining-composer, skill-gap-detector, model-triage-router]
inputs_needed:
  - "The user's request text (verbatim)"
  - "Path to the skills directory (each skill is a folder with a SKILL.md front-matter)"
  - "Optional: tuned WEAK / CONFIDENT / MARGIN thresholds for your manifest size"
produces: A routing decision (route | verify | no_match) plus a ranked shortlist with scores, ready for a dispatcher to act on or to ask the user with.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Automatic Skill Decision

The selector that sits in front of your skill library. Given a free-text request it
**scores every skill's triggers** (keywords + `when_to_use` + `description`), then makes
one of three calls, borrowed from production request routers:

- **route** — one skill clearly wins → dispatch it.
- **verify** — something matched but weakly, or it's a near-tie → read the shortlist's
  `when_to_use` / `when_not_to_use` and pick, or ask the user one question.
- **no_match** — nothing meaningfully matched → fall back (plain answer, or
  `skill-gap-detector` if the user clearly wanted a skill that doesn't exist).

Design is a two-stage hybrid, the same shape `aurelio-labs/semantic-router` and
`lm-sys/RouteLLM` use: a **cheap lexical/semantic score narrows to a shortlist**, then a
**decision gate** (absolute threshold for no-match, top1−top2 margin for ambiguity) decides
whether to act or escalate. The score only *narrows*; **you (Claude) adjudicate the shortlist**
— never blindly execute a lone coincidental keyword hit.

## When to use

Call this before doing work whenever a request could be handled by one of many skills and
you want the choice to be principled and explainable, not a vibe. It is the brain a
`/sebduffy`-style command runs first.

## Prerequisites

- **Python 3.8+** — the reference router (`scripts/route.py`) is pure stdlib, no installs.
- A **skills directory** where each skill is `.../<name>/SKILL.md` with YAML front-matter
  containing `name`, `keywords`, `when_to_use`, `description`, `when_not_to_use`
  (the SEBSKILLS standard). The router parses these directly — the manifest *is* the
  front-matter, so it never drifts from the skills themselves.
- Optional upgrade: an embedding model (OpenAI / Cohere / local) to replace the lexical
  signal with cosine similarity for fuzzier intent. Not required — lexical + `when_to_use`
  overlap covers most real requests.

## Recipe A — route a single request (reference implementation)

```bash
# route (exit 0), verify (exit 2), no_match (exit 3)
python3 scripts/route.py --skills-dir /path/to/skills \
  "route each step to a different llm, reasoning plans then coding implements"
# -> decision: route  ->  best-model-per-step-pipeline (model-routing, score=2.911)

python3 scripts/route.py --skills-dir /path/to/skills --json \
  "make the hero image ripple like water on hover"
# -> JSON: {decision, route, category, score, candidates:[...]}  <- feed a dispatcher
```

The `--json` output is the contract a slash-command consumes:

```json
{ "decision": "verify", "route": null,
  "candidates": [ {"name": "liquid-image", "category": "ui-effects", "score": 0.72},
                  {"name": "interactive-distortion", "category": "ui-effects", "score": 0.63} ] }
```

## Recipe B — the decision policy (what to do with each band)

```
score = rank(request, manifest)          # lexical: keyword hits + when_to_use overlap
top, second = score[0], score[1]

if top < WEAK:                 -> no_match  # answer directly / suggest skill-gap-detector
elif top >= CONFIDENT and (top-second) >= MARGIN:
                               -> route     # dispatch top; still sanity-check its when_to_use
else:                          -> verify    # read shortlist front-matter; pick or ASK ONE question
```

- **WEAK (default 0.35)** — the semantic-router "return None" idea: below it, no route is
  forced. Prevents the classic failure of jamming an out-of-scope request into a wrong skill.
- **MARGIN (0.30)** — the RouteLLM threshold idea applied to *skills*: a thin gap between #1
  and #2 means the lexical signal can't separate them → escalate rather than coin-flip.
- **CONFIDENT (0.80)** — only a clear, well-separated winner auto-routes.

Tune these to your manifest: more skills / overlapping domains → raise MARGIN. Print the
shortlist + scores whenever you ask the user, so the question is concrete
("Do you want to *generate* an image, or add a *hover ripple* to an existing one?").

## Recipe C — asking well when it's a near-tie (verify band)

Don't dump scores at the user. Convert the shortlist into a single disambiguating question
grounded in the skills' `when_to_use`:

> Two skills fit "make the logo strip loop":
> **infinite-marquee** (endless auto-scroll of logos) or **magnetic-cursor** (cursor pull)?
> Which behaviour do you mean?

Then route to their answer. If they pick neither, drop to `no_match` handling.

## Verify

```bash
python3 scripts/route.py --skills-dir /path/to/skills "read the text out of this pptx deck"   # route or verify -> a documents skill, not a UI one
python3 scripts/route.py --skills-dir /path/to/skills "what is the capital of France"          # no_match / verify -> nothing real matched
python3 scripts/route.py --skills-dir /path/to/skills --json "route each step to a different llm" | python3 -c "import json,sys;print(json.load(sys.stdin)['decision'])"
```

A healthy router: clear requests come back **route** with a large margin; genuinely
out-of-scope requests come back **no_match**; and near-synonyms land in **verify** with a
2–4 skill shortlist. If everything routes confidently (even nonsense), your WEAK/MARGIN are
too low; if nothing ever routes, they're too high.

## Pitfalls

- **Lexical scoring mis-ranks generate-vs-transform near-synonyms.** "image … colour reveal"
  can rank an image *generator* above a hover *effect* skill because they share tokens. That's
  why **route still means "confirm against the top skill's `when_to_use` before dispatching"** —
  the score narrows, you decide. For a stubborn manifest, swap the lexical signal for embeddings.
- **Stale manifest.** The router reads live front-matter, so a skill with thin `keywords` /
  `when_to_use` under-triggers. Fix the *skill's* triggers (see `skill-creator`), don't hack the router.
- **Over-eager auto-route.** Never execute a destructive skill purely on a lexical win — treat
  side-effecting skills as always-`verify`.
- **Routing vs eliciting vs chaining.** If the request is too vague to score, that's
  `requirement-elicitation`, not a low-confidence route. If it needs *several* skills, hand the
  shortlist to `skill-chaining-composer`. If the winner is `no_match` because the skill should
  exist but doesn't, that's `skill-gap-detector`.
- **Thresholds aren't universal.** WEAK/CONFIDENT/MARGIN are calibrated for lexical scores over
  ~100–300 skills. Re-check them (Recipe B) after big manifest growth or an embedding swap.
