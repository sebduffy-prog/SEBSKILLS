---
name: requirement-elicitation
category: meta-router
description: >
  Detect when a request is underspecified and, before acting, ask the minimum set of
  high-value clarifying questions that fully dissect the task. Runs a fast ambiguity
  scan (grounded in the CLAMBER taxonomy — epistemic, linguistic, and missing-slot
  ambiguity), decides ask-vs-proceed, then emits a tight 1-4 question menu with sensible
  defaults so the user can answer or say "use defaults". Use when a prompt feels vague,
  when you catch yourself about to guess a filename/scope/format/audience, or when someone
  says "clarify the requirements", "what do you need from me", "ask me questions first",
  "dissect this brief", or "before you start".
when_to_use:
  - A request is broad or vague ("build me a dashboard", "clean this up", "make it better") and guessing would waste a full build
  - You notice you are about to assume a scope, file, format, audience, deadline, or definition of done that the user never stated
  - Before kicking off an expensive or hard-to-reverse action (large refactor, deploy, mass edit, sending comms)
  - A brief has multiple plausible interpretations and picking wrong means redoing the work
  - The user explicitly asks you to gather requirements, scope a task, or "ask me what you need"
when_not_to_use:
  - The request is already specific and low-cost to attempt — just do it, don't interrogate (see autonomy-policy for the ask-vs-act line)
  - You are choosing which skill should handle a clear request — use automatic-skill-decision
  - You need to sequence several skills for a well-specified job — use skill-chaining-composer
  - No skill covers the task at all — use skill-gap-detector
  - Open-ended creative discovery where exploration matters more than a spec — use brainstorming
keywords: [clarifying questions, requirement elicitation, ambiguity detection, underspecified, vague request, scope, disambiguation, clamber, ask before acting, missing slots, definition of done, question menu, gather requirements, dissect brief, who what where when]
similar_to: [automatic-skill-decision, skill-chaining-composer, skill-gap-detector, brainstorming, autonomy-policy]
inputs_needed:
  - The raw user request as written (do not paraphrase it away before scanning)
  - Any context already on hand (files in the repo, prior turns, known conventions) so you don't ask what you can infer
  - A rough sense of the cost/reversibility of getting it wrong (cheap retry vs expensive redo)
produces: A go/ask decision plus, when asking, a numbered menu of 1-4 targeted clarifying questions each with a proposed default
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Requirement Elicitation

Turn a vague request into a dissected, actionable spec **before** you spend effort. Scan
for ambiguity, decide whether it blocks you, and if it does, ask the smallest set of
questions that removes the blockage — each with a default so answering is optional.

Grounded in the **CLAMBER** ambiguity taxonomy (Zhang et al., ACL 2024,
[arxiv 2405.12063](https://arxiv.org/abs/2405.12063)): LLMs default to *guessing* on
ambiguous input and are overconfident about it. The fix is a deliberate detect → decide →
ask loop, not more chain-of-thought.

## When to use

Run this the moment a request lands and either (a) reads as broad/vague, or (b) you feel
yourself inventing an unstated detail. If the task is already crisp and cheap to attempt,
skip this and just do it — over-asking is as bad as over-guessing.

## The loop

### 1. Scan for ambiguity (CLAMBER dimensions)

Read the request verbatim and check each dimension. Only real, blocking gaps count.

| Dimension | What to look for | Example gap |
|---|---|---|
| **Epistemic** | Unfamiliar entity/system, or a self-contradiction in the ask | "our usual format" (which?), "like last time" |
| **Linguistic** | A word with multiple meanings, or an unresolved referent ("it", "this", "the thing") | "clean up the data" (dedupe? reformat? delete?) |
| **Missing slots (WHO/WHAT/WHERE/WHEN)** | An output-shaping detail simply absent | audience, exact file, format, scope bound, deadline, definition of done |

Practical slot checklist — the questions that most often unblock real work:

- **WHAT** — exact artifact + format (PDF vs deck vs code), scope boundary (this file / whole repo), definition of done, quality bar
- **WHO** — audience / user, whose conventions to follow, who signs off
- **WHERE** — which file, path, branch, environment, repo
- **WHEN** — deadline, version/date range, ordering vs other work

### 2. Decide: ask or proceed

Ask a question **only** when both are true:

1. The gap is genuinely ambiguous — you cannot confidently infer it from context, files, or convention, and
2. Guessing wrong is costly — expensive to produce, hard to reverse, or wastes the user's time reviewing the wrong thing.

Otherwise **proceed and state your assumption** inline ("Assuming X; say so if not"). Cheap,
reversible, single-interpretation tasks should never trigger an interrogation. If in doubt
about the threshold, defer to `autonomy-policy`.

### 3. Ask a tight question menu

When you do ask, obey these rules (CLAMBER's failure modes are wrong-aspect and
wrong-specificity questions):

- **1-4 questions max.** Rank by decision impact; drop anything you can infer or default.
- **Target the right aspect.** Ask about the specific blocking gap, not a vaguely related one.
- **Right specificity.** Concrete enough to answer in a word, not a fishing expedition.
- **Never ask what you already know.** If the repo, prior turns, or convention answers it, don't ask.
- **Attach a default to each.** So the user can reply "defaults are fine" and you move.
- **Offer an escape hatch.** End with "or say 'use your best judgment' and I'll proceed with the defaults above."

Template:

```
Before I start, <N> quick things so I build the right thing:

1. <Question about the highest-impact gap>?  (default: <sensible default>)
2. <Next gap>?  (default: <default>)
3. <Next gap>?  (default: <default>)

Or say "use your best judgment" and I'll go with the defaults above.
```

## Recipes

**Vague build request** — "Build me a dashboard."
Blocking gaps: WHAT data/metrics, WHO audience, WHERE it runs, format. Ask 3, default the rest:
```
1. What are the 3-5 key metrics it should show?  (default: I'll infer from the data source)
2. Who's the audience — exec summary or analyst detail?  (default: exec summary)
3. Static artifact or a live app?  (default: single self-contained HTML)
Or say "best judgment" and I'll proceed.
```

**Ambiguous verb** — "Clean up this file."
Linguistic ambiguity on "clean". One question resolves it:
```
By "clean up" do you mean: format/lint, remove dead code, or fix bugs?  (default: format + remove dead code, no behaviour changes)
```

**Reference to prior state** — "Do it like last time."
Epistemic: unfamiliar referent. Confirm before repeating:
```
Which prior deliverable is "last time" — the June deck or the Q2 report?  (default: most recent, the Q2 report)
```

**Already specific** — "Add a `--dry-run` flag to scripts/deploy.sh that prints the commands instead of running them."
No blocking ambiguity → **do not ask**. Proceed; note any minor assumption inline.

## Verify

- Every question maps to a real blocking gap, not curiosity — cut any question whose answer wouldn't change what you build.
- No question asks something inferable from context, files, or convention.
- Each question has a usable default; the whole menu is answerable in under 30 seconds.
- You asked ≤4 questions, or you asked 0 and proceeded with stated assumptions.
- After answers (or "use defaults"), you can now write a one-line spec with no remaining unknowns.

## Pitfalls

- **Over-asking.** Interrogating on a cheap, clear task annoys users and stalls momentum. Default and proceed unless wrong-guess cost is high.
- **Wrong-aspect questions.** Asking about a tangential detail while the real ambiguity goes unresolved (CLAMBER's most common LLM error). Scan all three dimensions first.
- **Wrong specificity.** "What do you want exactly?" (too broad) or a 10-part questionnaire (too narrow/heavy). Aim for 1-4 word-answerable questions.
- **Defaultless questions.** If you can't propose a reasonable default, you probably don't understand the task enough to ask a good question yet.
- **Paraphrasing away the ambiguity.** If you silently rewrite the vague request into a specific one in your head and never surface it, the user can't catch a wrong turn. Surface the assumption.
- **Overconfidence.** Chain-of-thought makes you *feel* certain without adding information (CLAMBER finding). Feeling sure is not evidence the gap is filled — check against actual context.
