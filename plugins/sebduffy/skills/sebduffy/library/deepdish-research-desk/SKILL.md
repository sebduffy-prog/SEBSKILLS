---
name: deepdish-research-desk
category: recipes
description: >
  Recreate a DeerFlow / OpenAI Deep Research long-horizon research desk as a COMBO of proven
  SEBSKILLS. Takes a deep brief and drives it end-to-end: an orchestrator PLANs and runs the job
  long-horizon (longhorizon-research-agent), FANS OUT parallel evidence gathering across the web
  and private endpoints (deep-research + firecrawl-scrape + connect-public-api), folds findings
  into durable on-disk WORKING MEMORY (structured-memory-layers), adversarially VERIFIES every
  claim and citation (claim-verifier + citation-integrity-check), then DELIVERS a cited deck or
  report (data-driven-deck-generator or docx). Use to clone a deep-research agent, an autonomous
  "give it a brief, get a verified report" desk, or a fan-out-synthesize-verify-deliver pipeline.
when_to_use:
  - "You want a full deep-research agent (DeerFlow / OpenAI Deep Research style) that researches, synthesises AND delivers, not just one step"
  - "Turn an open-ended brief into a finished, verified, cited deck or Word report without babysitting each phase"
  - "Fan evidence gathering across web search, site scraping, and private APIs in parallel, then merge into one synthesis"
  - "Run a long-horizon job (minutes to hours) that survives crashes and resumes from an on-disk run directory"
  - "Guarantee every claim in the deliverable is fact-checked and every citation resolves before hand-off"
  - "Chain plan → fan-out → memory → verify → build as one auditable, reproducible recipe"
when_not_to_use:
  - "You only need single-shot cited web research with no build/deliver step → use deep-research directly"
  - "You only need to scrape one site or domain → use firecrawl-scrape directly"
  - "You only need to fact-check existing text or citations → use claim-verifier or citation-integrity-check directly"
  - "You only need the orchestrator shell without the opinionated verify+deliver combo → use longhorizon-research-agent"
  - "You just need to render a deck/report from data you already trust → use data-driven-deck-generator or docx"
keywords: [deep research, deerflow, openai deep research, research agent, long horizon, fan out, parallel subagents, working memory, claim verification, citation integrity, synthesis, research desk, cited report, deliverable, recipe, combo]
similar_to: [longhorizon-research-agent, deep-research, claim-verifier, data-driven-deck-generator]
inputs_needed:
  - "The brief: research question + required deliverable format (report.docx | deck.pptx) + audience"
  - "Source config: web keys (firecrawl/exa) and any private endpoints for connect-public-api"
  - "Budget caps: max parallel subagents, max tool-calls per subagent, wall-clock ceiling"
  - "A writable run directory for durable working memory (resumable state)"
  - "An LLM API key (any capable model) — the only hard external dependency"
produces: A resumable run directory (plan.json, memory/, findings/, verify/) plus a final claim-verified, citation-checked deliverable (docx or pptx) with a provenance log linking every statement to a source.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# DeepDish Research Desk (deep-research agent, recreated as a combo)

A flagship recipe that recreates a **long-horizon deep-research agent** — the DeerFlow /
OpenAI Deep Research shape — by chaining skills that already live in this library. Give it a
brief; it plans, gathers evidence in parallel, remembers on disk, verifies adversarially, and
hands back a finished cited deliverable.

## What it recreates

The behaviour of **OpenAI Deep Research** and **ByteDance DeerFlow** research agents: a single
autonomous run that decomposes a question, browses and reads many sources, keeps a durable
scratchpad, checks its own work, and writes up a properly cited report or deck. Those products
wrap a hosted model + browser + orchestration loop; this recipe reproduces the same loop locally
by stitching sibling skills together, so you own every phase and can inspect the run directory.

## Feasibility

**GREEN — fully reproducible locally.** Every link in the chain is a proven SEBSKILLS skill that
runs on this machine. No GPU, no fine-tune, no paid research product is required. The **only**
external dependency is an **LLM API key** (any capable model) plus web-search keys for the
gathering step — the same keys `deep-research` and `firecrawl-scrape` already need. There is no
amber or red step: the orchestration, memory, verification and delivery are all local. Honesty
note: quality still tracks the model and the source keys you supply — the recipe reproduces the
*loop and the guarantees*, not a proprietary crawler or index.

## The combo

Ordered pipeline — each step is an existing skill invoked by name:

1. **longhorizon-research-agent** — the orchestrator shell. Reads the brief, writes `plan.json`,
   sets budget caps, and drives the whole run long-horizon (resumable from disk). It owns the
   loop; steps 2–5 are the phases it dispatches.
2. **deep-research** — the primary fan-out. Breaks the question into sub-questions and runs
   multi-source web search + synthesis for each, producing cited findings.
3. **firecrawl-scrape** — deep-reads specific URLs and whole sites that step 2 surfaced but
   couldn't fully extract, returning clean markdown for the memory layer.
4. **connect-public-api** — pulls structured evidence from private or public APIs (pricing,
   filings, internal datasets) so the desk isn't limited to open web text.
   *(Steps 2–4 run in parallel across subagents, capped by the orchestrator's budget.)*
5. **structured-memory-layers** — the working memory. Folds every finding from 2–4 into a durable
   on-disk store (`memory/`, `findings/`), dedupes, and keeps provenance so the run is resumable.
6. **claim-verifier** — adversarially fact-checks each synthesised claim against the stored
   sources, flagging unsupported or contradicted statements.
7. **citation-integrity-check** — confirms every citation resolves, matches the claim it's
   attached to, and isn't hallucinated or mis-quoted.
8. **data-driven-deck-generator** *(or)* **docx** — builds the final deliverable: a cited slide
   deck for a presentation audience, or a Word report for a written one.

## Prerequisites

- The eight sibling skills above, available to `/sebduffy` in this library.
- An LLM API key for the orchestrator and subagents.
- Web keys for `deep-research` (firecrawl/exa) and `firecrawl-scrape`.
- Endpoint URLs + any keys for each `connect-public-api` source you want pulled in.
- A writable run directory (e.g. `./runs/<brief-slug>/`) for durable memory.
- Decide the deliverable up front: `report.docx` or `deck.pptx`.

## Run it

1. **State the brief.** Give the orchestrator the question, the audience, the deliverable format,
   and the budget caps. Invoke **longhorizon-research-agent** — it writes `plan.json` and a run
   directory.
2. **Fan out.** For each sub-question in the plan, the orchestrator dispatches **deep-research**;
   where a source needs full extraction it calls **firecrawl-scrape**; where structured data is
   needed it calls **connect-public-api**. Run these in parallel up to the subagent cap.
3. **Remember.** Each subagent writes its findings through **structured-memory-layers** into
   `memory/` and `findings/`, with source URLs/IDs attached. Re-running the recipe resumes from
   whatever is already on disk rather than re-fetching.
4. **Synthesise.** The orchestrator reads the folded memory and drafts the answer with inline
   citations.
5. **Verify.** Run **claim-verifier** over the draft to fact-check each claim against stored
   sources, then **citation-integrity-check** to confirm every citation resolves and matches.
   Loop back to step 2 for any claim that fails — the budget cap bounds how many times.
6. **Deliver.** Once verification is clean, build the artifact: **data-driven-deck-generator** for
   a deck or **docx** for a report. Write the provenance log alongside it.

## Verify

- **Run directory exists and is complete:** `plan.json`, `memory/`, `findings/`, `verify/` are
  all populated for the finished run.
- **Zero unresolved flags:** `claim-verifier` reports no unsupported/contradicted claims and
  `citation-integrity-check` reports every citation resolving. If any remain, the run is not done.
- **Every statement traces to a source:** spot-check the provenance log — pick three claims in
  the deliverable and confirm each links to a real entry in `findings/`.
- **Resumability:** kill and restart mid-run; it should pick up from disk without re-fetching
  completed sub-questions.
- **Deliverable opens clean:** the `.pptx`/`.docx` renders with citations intact (open it, don't
  just trust the build log).

## Pitfalls

- **Skipping verification to save time.** The verify pair is what separates this from a plausible-
  sounding hallucination. Never deliver on an unverified draft — that is the whole point of the
  recipe.
- **No budget cap.** Without max-subagents / max-tool-calls / wall-clock ceilings, the fan-out can
  run away. Always set caps in step 1.
- **Treating scrape and API pulls as optional.** Web synthesis alone misses paywalled detail and
  structured numbers; steps 3–4 are what make the evidence base deep rather than surface-level.
- **Losing provenance in the memory fold.** If findings land in `memory/` without their source
  IDs, `citation-integrity-check` can't do its job. Keep attribution on every stored finding.
- **Overselling it as a hosted product.** This reproduces the *loop and guarantees* of a deep-
  research agent, not a proprietary crawler/index. Quality tracks your model and source keys — say
  so to the user.
- **Re-fetching instead of resuming.** If a run crashes, point the orchestrator back at the
  existing run directory; don't start a fresh one and pay for the same searches twice.
