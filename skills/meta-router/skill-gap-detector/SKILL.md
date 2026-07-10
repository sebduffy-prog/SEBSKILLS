---
name: skill-gap-detector
category: meta-router
description: >
  Detect when NO existing skill covers the user's request, name the missing capability precisely, and hand off to skill-creator to author it. Use this whenever a task feels like it SHOULD have a reusable skill but none matches — recurring workflows, "why do I keep doing this by hand", a request that half-matches a skill but misses the core, or an obvious library gap. Runs the routing check first, then either points to the right existing skill or proposes a new one and kicks off skill-creator. Prevents silently re-improvising work that deserves to be captured.
when_to_use:
  - "You reach for a skill to handle a task and realise none in the library actually fits"
  - "The user says 'don't we have a skill for this?' or 'why do I keep redoing this'"
  - "A request half-matches an existing skill but the core capability is missing"
  - "You notice you've improvised the same multi-step workflow 2+ times across sessions"
  - "Someone asks to add a capability to the SEBSKILLS library but hasn't named the skill"
  - "A router (automatic-skill-decision) returns no confident match and you need to decide: build or improvise"
when_not_to_use:
  - "A good skill already matches — use automatic-skill-decision to route to it instead"
  - "You already know exactly what skill to author — go straight to skill-creator"
  - "The request is vague on requirements, not on coverage — use requirement-elicitation first"
  - "The task needs several existing skills orchestrated together — use skill-chaining-composer"
keywords: [skill gap, missing skill, no skill fits, coverage gap, capability gap, does a skill exist, skill discovery, gap detection, propose new skill, skill-creator handoff, library gap, undertriggering, meta router, skill inventory, recurring workflow]
similar_to: [automatic-skill-decision, requirement-elicitation, skill-chaining-composer]
inputs_needed:
  - The user's actual request or the workflow you keep re-improvising
  - Read access to the skills library root (default /Users/seb.duffy/Documents/GitHub/SEBSKILLS/skills)
produces: A gap verdict (covered / partial / gap) plus, on a real gap, a one-paragraph skill proposal handed to skill-creator
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Skill Gap Detector

Skills only pay off if they get **used** and if missing ones get **built**. The failure this skill guards against is quiet: Claude improvises a multi-step workflow from scratch, ships it, and never notices the workflow deserved to be a reusable skill. Do that twice and you've paid for the same thinking twice. This skill makes the "is there a skill for this? no? should there be?" decision explicit instead of skipped.

The output is a **verdict**, not a build. On a genuine gap you write a tight proposal and hand off to `skill-creator` — you do not author the SKILL.md here.

## When to use

Trigger this the moment a task feels like it *should* have a skill but nothing fits: a recurring workflow, a request that half-matches a skill but misses the core, a user asking "don't we have something for this?", or a router that came back empty. If a skill clearly fits, this is the wrong tool — route with `automatic-skill-decision`.

## Prerequisites

No API keys, no installs. You need:
- Read access to the skills library (default root below). Override if the user's library lives elsewhere.
- `grep`/`find` (present on macOS/Linux).

```bash
SKILLS_ROOT="/Users/seb.duffy/Documents/GitHub/SEBSKILLS/skills"
```

## Steps

### 1. Search the library before claiming a gap

Most "gaps" are actually discovery failures — the skill exists under a name you didn't guess. Search **descriptions and keywords**, not just folder names, because triggering lives in the frontmatter. Pull the candidate set fast:

```bash
# Rank skills by how many query terms hit name+description+keywords.
# Usage: ./scripts/find_candidates.sh "audience segmentation tgi crosstab"
scripts/find_candidates.sh "TERMS" "$SKILLS_ROOT"
```

Or inline without the helper — grep the frontmatter of every skill for each salient term:

```bash
for term in segmentation crosstab audience tgi; do
  echo "== $term =="
  grep -ril "$term" "$SKILLS_ROOT"/*/*/SKILL.md
done | sort | uniq -c | sort -rn
```

Read the top 3-5 candidates' frontmatter (`name`, `description`, `when_to_use`, `when_not_to_use`) before deciding. Guessing from the folder name alone is how duplicate skills get born.

### 2. Classify the match — covered, partial, or gap

Judge the **top candidate** against the request's *core capability* (the verb + artifact the user actually wants), not surface keyword overlap.

| Verdict | Meaning | Action |
|---|---|---|
| **Covered** | A skill's core capability == the request's core. | Stop. Route to it via `automatic-skill-decision`. No gap. |
| **Partial** | A skill overlaps but misses the core, wrong artifact, or wrong domain. | Decide: *extend* the existing skill, or *author* a sibling. Usually extend if the core is the same and only inputs/outputs differ; author new if the core verb differs. |
| **Gap** | Nothing covers the core capability. | Proceed to step 3 — write a proposal. |

The trap to avoid: a skill that shares keywords but has a different **core verb** is a gap, not a match. Example: a `pdf` skill that reads/merges PDFs does **not** cover "fill a government PDF form from a CSV each week" if no candidate's core is form-filling from tabular data — shared noun ("PDF"), different verb ("fill from data on a schedule"). Conversely, don't invent a gap for a one-off: if you'll never do this again, improvise it and move on. The bar for "gap" is *recurring or clearly reusable*.

### 3. Name the capability precisely

A vague gap ("we need something for reports") produces a vague, under-triggering skill. Name it as **verb + object + qualifier**, the way a `when_to_use` line reads:

- Weak: "audience skill"
- Strong: "Build a TGI-vs-GWI audience crosstab from a raw survey export and rank segments by index"

Pin down, in one or two sentences each:
- **Core capability** — the single verb+artifact. If you need "and" to describe it, it may be two skills (see `skill-chaining-composer`).
- **Trigger phrases** — 3-5 things a user would actually type that should fire it.
- **Produces** — the concrete artifact (a file, a rendered thing, a decision).
- **Nearest existing skill** — and one sentence on why it's *not* enough. This becomes the new skill's `when_not_to_use` and prevents an overlap war.

### 4. Hand off to skill-creator

Don't author the SKILL.md here — that's `skill-creator`'s job, and it carries the eval/iterate loop this skill deliberately omits. Hand it a filled proposal so it starts from intent, not a blank page:

```
Invoke skill-creator with this proposal:

- Proposed name: <kebab-case>
- Category: <existing category folder, or propose a new one with a one-line rationale>
- Core capability: <verb + object + qualifier>
- Trigger phrases: <3-5 real user utterances>
- Produces: <concrete artifact>
- Nearest existing skill + why it's insufficient: <one sentence>
- Any tool/API/data dependencies you already know of: <list or "none">
```

If you're the one continuing, load `skill-creator` (via the Skill tool) and pass the proposal as its intent. If the user is driving, present the proposal and ask "want me to build this now?" before spawning skill-creator.

## Verify

- The verdict names a **specific top candidate** you actually read — not "I didn't find anything" from a folder-name skim.
- On **covered**, you routed instead of building. On **gap**, the proposal has a single-verb core capability and a named nearest-neighbour.
- The proposal handed to skill-creator would let a fresh Claude write a correct `description` without asking what the skill is for.
- You did **not** write a SKILL.md in this skill — the handoff did.

## Pitfalls

- **Folder-name-only search.** Triggering lives in `description`/`keywords`, so a keyword grep across frontmatter beats eyeballing directory names. Skipping this is the #1 cause of duplicate skills.
- **Keyword match ≠ capability match.** Same noun, different verb = still a gap. Judge the core verb+artifact, not term overlap.
- **Gap-flagging one-offs.** Not every task deserves a skill. Reserve "gap" for recurring or clearly-reusable work; improvise the rest.
- **Building here.** This skill *detects and proposes*; `skill-creator` *builds and evals*. Authoring the SKILL.md inline skips the test/iterate loop and produces weaker skills.
- **Partial → silent duplicate.** When a skill *almost* fits, default to extending it. A brand-new sibling that overlaps 80% just splits triggering and confuses the router later — only fork when the core verb genuinely differs.
- **Vague proposals.** "A skill for X" hands skill-creator a blank page. Give it verb+object+qualifier, real trigger phrases, and the nearest-neighbour delta.
