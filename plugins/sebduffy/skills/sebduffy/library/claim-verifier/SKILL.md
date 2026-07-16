---
name: claim-verifier
category: verification
description: >-
  Fact-check prose by decomposing it into atomic, decontextualized, checkable claims, retrieving
  evidence per claim (web/corpus), and returning a per-claim Supported / Refuted / Unverifiable
  verdict with citations, quotes, and a confidence score. Trigger when a report, deck, blog post,
  press release, LLM answer, or marketing copy makes factual assertions that must be validated
  before shipping — and you need a defensible, source-linked audit rather than a vibe check.
when_to_use:
  - Before publishing a report, whitepaper, or client deck that states figures, dates, quotes, or claims
  - Auditing an LLM/RAG answer for hallucinations against retrievable evidence
  - Vetting marketing or PR copy so every factual claim can survive legal/comms scrutiny
  - Reviewing a competitor/market narrative where each assertion needs a source
  - Producing a claim-by-claim evidence table for a fact-check or editorial sign-off
when_not_to_use:
  - Verifying only inline citations already present in a document — use citation-integrity-check
  - Recomputing or sanity-checking numeric/statistical claims specifically — use stat-check-review
  - Judging whether a source itself is trustworthy — use source-credibility-audit
  - Stress-testing an argument's logic or counterarguments — use adversarial-argument-review
keywords:
  - fact-check
  - claim-decomposition
  - atomic-claims
  - evidence-retrieval
  - verification
  - hallucination-detection
  - claimify
  - supported-refuted
  - decontextualization
  - citations
  - groundedness
  - misinformation
similar_to:
  - citation-integrity-check
  - stat-check-review
  - adversarial-argument-review
  - source-credibility-audit
  - research-methodology-review
  - self-consistency-check
inputs_needed: Prose to check (paste, file path, or URL). Optional evidence source (web via WebSearch/WebFetch, or a supplied corpus/knowledge base) and a confidence bar for what counts as "Supported".
produces: A claim table — each atomic claim with a Supported/Refuted/Unverifiable verdict, confidence 0-1, the deciding evidence snippet, and source URL/citation — plus a rollup accuracy summary and a flagged-claims shortlist.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Claim Verifier

Turn a block of prose into a defensible fact-check: split it into atomic claims, find evidence for
each, and issue a **Supported / Refuted / Unverifiable** verdict with a citation. Grounded in the
Claimify extraction methodology (Metropolitansky & Larson, MSR 2025) and the Factcheck-GPT pipeline
(Wang et al., 2024).

## When to use

Use this when a document makes factual assertions that must hold up before it ships, or when you
need to catch hallucinations in an LLM/RAG output. The deliverable is a per-claim evidence audit,
not a summary opinion. If you only need to check citations already in the text, statistics, source
quality, or argument logic, use the sibling skill named in `when_not_to_use`.

## Prerequisites

- **The source text.** Paste it, give a path, or a URL (fetch with `WebFetch`).
- **An evidence source.** Either the open web (`WebSearch` + `WebFetch` — load via
  `ToolSearch "select:WebSearch,WebFetch"` if deferred) or a caller-supplied corpus / knowledge base
  you retrieve against. Verification is only as good as what you can retrieve; state which you used.
- **No API keys required** for the web-tool path. A dedicated retrieval API (Tavily, Serper, an
  internal vector store) is optional and only changes the retrieval step, not the verdict logic.
- Honesty rule: never invent a citation. If nothing retrievable supports a claim, the verdict is
  **Unverifiable**, not Supported.

## The pipeline

```
prose ─▶ 1 SELECT ─▶ 2 DISAMBIGUATE ─▶ 3 DECOMPOSE ─▶ 4 RETRIEVE ─▶ 5 VERDICT ─▶ 6 REPORT
        check-worthy   resolve refs      atomic claims   evidence      per claim    rollup
```

### 1. Select check-worthy sentences

Walk the text sentence by sentence. Keep only **verifiable factual assertions**. Drop opinions
("this is the best tool"), predictions, rhetorical questions, definitions, and instructions. A
sentence is check-worthy if a reasonable reader could, in principle, look it up and find it true or
false. Tag each kept sentence with its source location (paragraph/line) so the report is traceable.

### 2. Disambiguate (decontextualize)

Rewrite each kept sentence so it stands alone with **no unresolved references**. Resolve pronouns
("it", "they", "the company"), relative time ("last year" → the actual year), and elliptical
comparisons ("grew faster" → faster than what). If a reference genuinely cannot be resolved from the
surrounding text, do **not** guess — mark that sentence `ambiguous` and exclude it from scoring with
a note. This is the Claimify disambiguation step; ambiguity that can't be settled is reported, not
papered over.

### 3. Decompose into atomic claims

Split each disambiguated sentence into **atomic** claims — one checkable fact each. A claim is
atomic when it cannot be true in part and false in part.

> "In 2023 Acme opened 12 UK stores and hired 400 staff."
> → C1: "Acme opened 12 stores in the UK in 2023."
> → C2: "Acme hired 400 staff in 2023."

Keep each claim self-contained (it must still make sense pulled out of the list). Preserve numbers,
units, named entities, and dates exactly as written — those are what you will check.

### 4. Retrieve evidence per claim

For each atomic claim, gather evidence *before* judging it. Do not decide from memory.

- Build a focused query from the claim's entities + the fact at issue (e.g.
  `Acme UK stores opened 2023`). Prefer primary sources (company filings, official stats, the org's
  own site) over aggregators.
- Web path: `WebSearch` for candidates, then `WebFetch` the 1-3 most authoritative to extract the
  passage that actually addresses the claim. Capture the exact quote and the URL.
- Corpus path: retrieve top-k passages from the supplied store; capture passage id + text.
- If the first pass is thin or contradictory, do **one** targeted re-query (Factcheck-GPT's
  multi-retry). If still empty, record "no evidence found" and move on — that drives an Unverifiable
  verdict, it is not a failure.

### 5. Issue a verdict

Judge the claim **only against the retrieved evidence**, using this rubric:

| Verdict | Rule |
|---|---|
| **Supported** | Evidence directly and unambiguously affirms the claim (matches numbers/dates/entities). |
| **Refuted** | Evidence directly contradicts the claim (different figure, wrong date, denies the event). |
| **Unverifiable** | No sufficient evidence found, sources conflict irreconcilably, or the claim was marked ambiguous. |

Record for every claim: `verdict`, `confidence` (0-1 — how strongly the evidence settles it),
`evidence` (the deciding quote), `source` (URL or passage id), and a one-line `rationale`.
Partial-support cases (evidence backs some but not all of the claim) mean the decomposition in step 3
wasn't atomic enough — split the claim further and re-verify rather than fudging a middle verdict.

### 6. Report

Emit a claim table plus a rollup. Suggested JSON shape:

```json
{
  "summary": { "claims": 14, "supported": 9, "refuted": 2, "unverifiable": 3,
               "accuracy": 0.64, "flagged": ["C4", "C11"] },
  "claims": [
    { "id": "C4", "text": "Acme opened 12 stores in the UK in 2023.",
      "source_loc": "para 2", "verdict": "Refuted", "confidence": 0.88,
      "evidence": "Acme's 2023 annual report lists 8 new UK store openings.",
      "source": "https://acme.example/annual-2023.pdf#p14",
      "rationale": "Report says 8, claim says 12." }
  ]
}
```

`accuracy` = supported / (supported + refuted); leave Unverifiable out of the denominator so an
un-sourced doc doesn't score as accurate. Surface **Refuted first**, then low-confidence Supported,
then Unverifiable — that is the shortlist the author must act on. Render a Markdown table too if a
human is reading it.

## Verify

Sanity-check the check itself before you hand it over:

- **Coverage:** every check-worthy sentence in the source produced at least one claim. Spot-check a
  paragraph by hand — no factual sentence should be silently dropped.
- **Atomicity:** no claim contains "and"/"but" joining two independent facts, and none got a
  partial-support fudge.
- **Traceability:** every Supported/Refuted verdict has a real, fetchable URL or passage id and a
  verbatim quote — open one at random and confirm the quote is actually on the page.
- **No fabrication:** any claim without retrievable evidence is Unverifiable, never Supported.
- **Reproducibility:** re-running retrieval on a Refuted claim returns the same contradicting source.

## Pitfalls

- **Judging from memory.** The model "knowing" a fact is not evidence. Always retrieve; the verdict
  must cite something a reader can open. This is the single biggest failure mode.
- **Under-decomposition.** Compound claims produce mushy "partially true" verdicts. If you reach for
  partial, split further and re-verify (step 3 → 5).
- **Skipping disambiguation.** Verifying "it grew 20%" without resolving "it" and the baseline checks
  nothing. Decontextualize first or mark ambiguous.
- **Stale or mismatched sources.** A source about a *different year/entity* looks relevant to search
  ranking but doesn't address the claim. Confirm the quote matches the claim's date and subject.
- **Aggregator laundering.** A blog citing a stat isn't the stat's source. Chase to the primary
  document before scoring Supported with high confidence.
- **Opinion smuggled as fact.** "The leading platform" is a claim ("has the largest market share")
  only if a measure exists; otherwise it's opinion — drop it in step 1, don't force a verdict.
- **Denominator gaming.** Counting Unverifiable claims as "fine" inflates apparent accuracy. Keep
  them out of the accuracy ratio and list them explicitly.
- **Framing (defensive use).** This skill verifies claims already present in supplied text; it is not
  for generating persuasive or deceptive content. Keep the audit authorised and source-honest.
