---
name: market-research
category: product
description: Conduct market research, competitive analysis, investor due diligence, and industry intelligence with source attribution and decision-oriented summaries. Use when the user wants market sizing, competitor comparisons, fund research, technology scans, or research that informs business decisions.
when_to_use:
  - Researching a market, category, company, investor, or technology trend
  - Building TAM/SAM/SOM estimates (top-down and bottom-up)
  - Comparing competitors or adjacent products
  - Preparing investor or fund diligence dossiers before outreach
  - Pressure-testing a thesis before building, funding, or entering a market
when_not_to_use:
  - The research is general/topical rather than business-decision oriented — use deep-research
  - You are refining or stress-testing a raw idea, not gathering market evidence — use idea-refine
  - You need to validate the product "why" internally — use product-lens
keywords:
  - market research
  - competitive analysis
  - investor due diligence
  - fund diligence
  - tam sam som
  - market sizing
  - competitor comparison
  - technology scan
  - vendor research
  - industry intelligence
  - source attribution
  - thesis testing
  - positioning gaps
  - decision-oriented
similar_to:
  - deep-research
  - product-lens
inputs_needed: The market, competitor, investor, or technology to research, the decision it informs, and any specific claims or thesis to pressure-test.
produces: A decision-oriented research brief with sourced claims separating fact, inference, and recommendation.
status: stable
owner: seb.duffy
updated: 2026-07-09
origin: ECC
---

# Market Research

Produce research that supports decisions, not research theater.

## When to Activate

- researching a market, category, company, investor, or technology trend
- building TAM/SAM/SOM estimates
- comparing competitors or adjacent products
- preparing investor dossiers before outreach
- pressure-testing a thesis before building, funding, or entering a market

## Research Standards

1. Every important claim needs a source.
2. Prefer recent data and call out stale data.
3. Include contrarian evidence and downside cases.
4. Translate findings into a decision, not just a summary.
5. Separate fact, inference, and recommendation clearly.

## Tooling

- Use WebSearch/WebFetch (or firecrawl/exa MCP if connected) for every claim that needs a source.
- If NO web tooling is available, say so explicitly and mark claims as unverified — never fabricate sources.

## Common Research Modes

### Investor / Fund Diligence
Collect:
- fund size, stage, and typical check size
- relevant portfolio companies
- public thesis and recent activity
- reasons the fund is or is not a fit
- any obvious red flags or mismatches

### Competitive Analysis
Collect:
- product reality, not marketing copy
- funding and investor history if public
- traction metrics if public
- distribution and pricing clues
- strengths, weaknesses, and positioning gaps

### Market Sizing
Use:
- top-down estimates from reports or public datasets
- bottom-up sanity checks from realistic customer acquisition assumptions
- explicit assumptions for every leap in logic

### Technology / Vendor Research
Collect:
- how it works
- trade-offs and adoption signals
- integration complexity
- lock-in, security, compliance, and operational risk

## Output Format

Findings land in a file (`market-research-<topic>.md`) with a sources section, not chat prose.

Default structure:
1. executive summary
2. key findings
3. implications
4. risks and caveats
5. recommendation
6. sources

## Quality Gate

Before delivering:
- all numbers are sourced or labeled as estimates
- old data is flagged
- the recommendation follows from the evidence
- risks and counterarguments are included
- the output makes a decision easier
