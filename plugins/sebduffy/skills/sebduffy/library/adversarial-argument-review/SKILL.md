---
name: adversarial-argument-review
category: verification
description: >
  Steelman an argument then attack it — reconstruct its strongest form, surface hidden assumptions,
  name logical fallacies, build the strongest counter-argument, run a pre-mortem, and mark which
  premises are load-bearing. Use before you send a strategy memo, recommendation, or client
  argument that must survive a hostile reader. Grounded in the yourlogicalfallacyis taxonomy and
  the UK MoD Red Teaming Handbook (pre-mortem, devil's advocate, alternative analysis). Outputs a
  structured teardown, not a vibe check.
when_to_use:
  - Before shipping a recommendation, strategy memo, or pitch that a skeptical exec or client will attack
  - You wrote a persuasive case and want to know where it actually breaks before someone else finds it
  - A debate or decision hinges on one argument and you need its real weak points, not its surface ones
  - Reviewing someone else's proposal and you must give a fair-but-ruthless critique
  - You suspect an argument is winning on rhetoric and want to separate the logic from the persuasion
when_not_to_use:
  - A specific factual claim is what's in doubt — use claim-verifier
  - The sources behind the argument are the concern — use source-credibility-audit
  - A statistic's math/methodology is the issue — use stat-check-review or research-methodology-review
  - You need quotes/links to match what they cite — use citation-integrity-check
  - Checking a document for internal contradictions — use self-consistency-check
keywords: [steelman, red team, pre-mortem, logical fallacy, counter-argument, hidden assumptions, load-bearing premise, devil's advocate, argument review, critical thinking, rebuttal, adversarial, straw man, alternative analysis]
similar_to: [claim-verifier, citation-integrity-check, stat-check-review, source-credibility-audit, research-methodology-review, self-consistency-check]
inputs_needed: The argument to review — a memo, slide, paragraph, recommendation, or spoken case — plus (optional) the audience/decision it's meant to win. Works fully offline; web access only helps when a premise rests on a checkable external fact.
produces: A structured teardown — steelmanned restatement, premise/conclusion map with load-bearing premises flagged, hidden-assumptions list, named fallacies with locations, the single strongest counter-argument, a pre-mortem ("it failed — why"), and a verdict with the cheapest fix that would most strengthen the case.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Adversarial Argument Review

Make an argument stronger by first stating it at its best (steelman), then attacking it the way a
smart, motivated opponent would. The goal is not to "win" — it's to find where the argument
actually breaks so it can be fixed before a real adversary (an exec, a client, a reviewer) finds
the crack. Grounded in the classic logical-fallacy taxonomy (yourlogicalfallacyis.com) and the
UK Ministry of Defence *Red Teaming Handbook* (pre-mortem, devil's advocate, alternative analysis).

## When to use

Reach for this when an argument has to survive contact with a hostile or skeptical reader and the
cost of it collapsing in the room is high. It answers a different question from its siblings: not
"is this fact true" (claim-verifier) or "are the sources any good" (source-credibility-audit), but
**"if someone wanted to demolish this reasoning, where would they strike, and does it hold?"**

## Prerequisites

- **No API keys, no install.** This is a reasoning rubric — run it by hand or as an LLM prompt.
- **Web access optional.** Only needed when a *premise* rests on an external fact you'd want to
  probe (then use WebSearch / WebFetch). The fallacy and structure work is fully offline.
- **The argument in a form you can quote.** Paste the memo/slide/paragraph. If it's implicit or
  spoken, write it down as explicit premises first — you cannot attack what you can't state.

## The seven-pass teardown

Run all seven in order. The steelman **must** come first — attacking a weak version (a straw man)
is the single most common failure of this exercise and produces useless critique.

### 1. Steelman — restate the argument at its strongest
Rewrite the argument in the most charitable, most defensible form. Fix its sloppy wording, grant
its most reasonable interpretation, add the obvious supporting point the author forgot. If your
restatement is weaker or more attackable than the original, you're strawmanning — redo it. Litmus
test: the original author should read your steelman and say "yes, that's what I meant, better."

### 2. Map premises → conclusion
Decompose into explicit premises (P1, P2, …) and the conclusion (C). Write each as a standalone
declarative sentence. Note the logical form: does C actually follow *if* all premises are true
(valid), or is there a gap even granting every premise (a non-sequitur)?

### 3. Flag load-bearing premises
For each premise ask: **"if this were false, does the conclusion collapse?"** Mark each
LOAD-BEARING (conclusion dies without it), SUPPORTING (weakens but survives), or DECORATIVE
(remove and nothing changes). The load-bearing set is where all real attack and defence effort
goes — everything else is noise. A robust argument has few load-bearing premises, each independently
well-supported.

### 4. Surface hidden assumptions
List the unstated things that must be true for the argument to work — the premises the author
didn't write because they seem "obvious." These are usually the weakest points because nobody
pressure-tested them. Prompts: What's assumed about the audience, the market, the timeframe, the
baseline, causality, or "all else equal"? What would a domain outsider find surprising that the
author took for granted?

### 5. Name the fallacies (with location)
Scan for reasoning errors and cite *where* each occurs — a fallacy label with no location is a
cheap shot. Common offenders (yourlogicalfallacyis taxonomy):

| Fallacy | Tell |
|---|---|
| Straw man | Attacks a distorted version of the opposing view |
| Ad hominem | Attacks the source, not the argument |
| False dilemma | Presents two options when more exist |
| Slippery slope | Asserts A inevitably leads to extreme Z with no mechanism |
| Hasty generalisation | Broad claim from a tiny / unrepresentative sample |
| Post hoc / correlation-as-cause | "B followed A, so A caused B" |
| Appeal to authority | "X is true because [figure] said so" |
| Appeal to novelty/tradition | True because it's new / because it's always been done |
| Begging the question | Conclusion smuggled into a premise (circular) |
| Anecdote | A vivid story standing in for representative evidence |
| Survivorship bias | Reasons only from the cases that made it through |
| Sunk cost | "We've already invested, so we must continue" |
| Bandwagon | True/right because many believe it |

Distinguish a *fatal* fallacy (breaks a load-bearing premise) from a *cosmetic* one (weakens
rhetoric but the logic survives). Report both, but rank fatal first.

### 6. Strongest counter-argument
Build the single best case *against* the conclusion — the one a well-prepared opponent would lead
with. Not five weak objections; one strong one. Then honestly assess: does the original argument
already answer it, or is it an unhandled kill-shot? This is the devil's-advocate move from the Red
Teaming Handbook.

### 7. Pre-mortem
Assume it's 12 months later and the recommendation was adopted and **failed**. Working backwards,
write the 2–4 most likely causes of that failure. The pre-mortem (Red Teaming Handbook /
Klein) beats a risk list because "it already failed" licenses people to name problems that
optimism suppresses. Each cause should trace back to a load-bearing premise or hidden assumption
from passes 3–4.

## Output template

```
ARGUMENT UNDER REVIEW: <one-line summary>
AUDIENCE / DECISION IT MUST WIN: <who, what call>

1. STEELMAN
   <strongest charitable restatement, 2-4 sentences>

2. STRUCTURE
   P1: ...            [LOAD-BEARING | SUPPORTING | DECORATIVE]
   P2: ...            [...]
   C : ...
   Valid if premises true?  YES / NO — <gap if no>

3. HIDDEN ASSUMPTIONS
   - <unstated thing that must hold>  → risk if false: <...>

4. FALLACIES
   - <name> @ "<quoted location>"  — FATAL / cosmetic — <why>

5. STRONGEST COUNTER-ARGUMENT
   <the one best case against C>
   Already answered by the argument?  YES / PARTIALLY / NO

6. PRE-MORTEM (it failed — why)
   - <cause 1, traces to P#/assumption>
   - <cause 2 ...>

VERDICT: HOLDS / HOLDS-WITH-FIXES / BREAKS
CHEAPEST HIGH-VALUE FIX: <the one change that most strengthens it per unit effort>
```

## Verify

Your review is doing its job when:

- **The steelman passes the author test** — the original author would accept it as fair or better.
  If you can only critique a version the author would disown, you've strawmanned; start over.
- **Every fallacy has a quoted location.** No location = drop it.
- **The counter-argument is one strong shot, not a scattergun.** If you listed five weak ones,
  you're padding — pick the deadliest.
- **Pre-mortem causes trace to load-bearing premises / hidden assumptions**, not to generic bad
  luck. "The market shifted" is lazy; "P2 assumed retention holds at scale, and it won't" is useful.
- **The verdict names the cheapest high-value fix**, not a wishlist. One lever, biggest move.

## Pitfalls

- **Strawmanning disguised as rigour.** Attacking a weak restatement feels productive and proves
  nothing. The steelman gate exists precisely to stop this — do not skip it.
- **Fallacy-hunting as a gotcha.** A cosmetic fallacy in the rhetoric doesn't mean the conclusion
  is wrong — that itself is the *fallacy fallacy*. Only fatal fallacies (those breaking a
  load-bearing premise) change the verdict.
- **Confusing "I disagree" with "this breaks."** Your job is to test the argument's internal
  strength and its exposure to counter-evidence, not to substitute your preferred conclusion.
- **Symmetric over-charity.** Steelman the argument, but don't also steelman away every objection.
  Charity applies to reconstruction (pass 1); pass 5–7 are adversarial by design.
- **Reviewing an implicit argument.** If premises are unstated you'll attack a phantom. Force the
  argument into explicit P→C form (pass 2) before critiquing.
- **Endless objections, no fix.** A teardown that lists twenty problems and no cheapest-fix is
  demoralising and unactionable. The verdict + one lever is the deliverable, not the wound count.
