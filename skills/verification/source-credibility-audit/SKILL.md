---
name: source-credibility-audit
category: verification
description: >
  Grade the sources behind a claim, deck, or report — reliability track record,
  independence and conflicts of interest, primary-vs-secondary, expertise,
  corroboration, transparency, recency — into a per-source weighted trust score
  and a claim-level weakest-link verdict. Use when someone cites a study, stat,
  vendor whitepaper, or news article to back an argument and you need to judge
  whether the evidence actually holds, not just whether it sounds authoritative.
when_to_use:
  - A claim, slide, or exec recommendation rests on one or more cited sources
  - You must decide if a study / stat / whitepaper is trustworthy enough to act on
  - Comparing several sources that disagree and need to weight them
  - Vetting funded, vendor, or advocacy material for conflict of interest
  - Building an evidence table for a pitch, PRD, or board paper
when_not_to_use:
  - The factual accuracy of one number is in question, not the source — use stat-check-review
  - You need to check that citations exist and match their claims — use citation-integrity-check
  - Verifying a specific factual claim end-to-end — use claim-verifier
  - Critiquing a study's internal design/methods — use research-methodology-review
keywords:
  - source credibility
  - reliability
  - bias
  - conflict of interest
  - primary source
  - trust score
  - weakest link
  - grade
  - media bias fact check
  - corroboration
  - evidence grading
  - provenance
similar_to:
  - claim-verifier
  - citation-integrity-check
  - stat-check-review
  - adversarial-argument-review
  - research-methodology-review
  - self-consistency-check
inputs_needed: The claim being supported plus its sources (URLs, citations, PDFs, or names) and, where known, who funded/published each.
produces: A per-source scorecard (7 dimensions, weighted 1-5 trust score, band A-F) and a claim-level weakest-link verdict naming the weakest load-bearing source.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Source Credibility Audit

Grade the *sources* behind a claim, not the claim's wording. A confident deck
built on one conflicted whitepaper is weaker than a hedged one built on three
independent studies. This skill scores each source on seven dimensions, then
applies a **weakest-link rule**: a claim is only as strong as the flimsiest
source it actually leans on. The rubric adapts GRADE's certainty domains (risk
of bias, indirectness, corroboration) and Media Bias/Fact Check's reliability +
bias split into one weighted score.

## When to use

Use the moment an argument's weight depends on *who said it*: a cited RCT, a "9
in 10 marketers agree" stat, a vendor benchmark, a news article, an expert
quote. Skip it for checking a single number's arithmetic (stat-check-review) or
whether a citation actually says what it's claimed to (citation-integrity-check).

## Prerequisites

- No API keys. The scorer is `python3` stdlib only (works with macOS 3.9).
- You supply the ratings — this skill is a **judgement scaffold**, not an
  automated fact-checker. To ground the reliability/bias dimension, optionally
  cross-check the outlet at `mediabiasfactcheck.com` and the study design against
  GRADE domains, but the scores are yours to defend.
- For each source, know (or find) its publisher, funder, and whether it is the
  origin of the data or a retelling.

## Steps

### 1. Enumerate the load-bearing sources

List every source the claim *depends on*. Mark ones that are merely
corroborating (nice-to-have) vs load-bearing (remove it and the claim falls).
Only load-bearing sources set the verdict.

### 2. Rate each source 1-5 on seven dimensions

5 = excellent, 1 = fails. Be concrete and cite the reason.

| Dimension | Weight | 5 looks like | 1 looks like |
|---|---|---|---|
| **reliability** | 25% | Long clean factual record; peer-reviewed; corrections issued | History of retractions / fabrication (MBFC "Low/Very Low") |
| **independence** | 20% | No stake in the conclusion; funder disclosed & neutral | Author/funder profits from the finding; hidden sponsorship |
| **primacy** | 15% | Primary: the origin of the data/measurement | Third-hand retelling of a retelling |
| **expertise** | 15% | Recognised domain authority; peer-reviewed venue | No relevant credentials; off-topic authority |
| **corroboration** | 10% | Independently replicated elsewhere | Sole source; contradicted by others |
| **transparency** | 10% | Full methodology, sample, and limitations published | Black-box "trust us" numbers |
| **recency** | 5% | Current for the claim's time window | Stale; superseded by newer data |

Two dimensions are **critical**: `reliability` and `independence`. A 1-2 on
either flags the source no matter how high the weighted average — a fabricated
or bought source is disqualified, not averaged.

### 3. Compute scores

Write the ratings to JSON and run the scorer:

```json
{"sources":[
 {"name":"Peer-reviewed RCT (Lancet)",
  "ratings":{"reliability":5,"independence":4,"primacy":5,"expertise":5,
             "corroboration":4,"transparency":5,"recency":4}},
 {"name":"Vendor whitepaper (funded)",
  "ratings":{"reliability":3,"independence":1,"primacy":4,"expertise":3,
             "corroboration":2,"transparency":2,"recency":5}}
],
"corroborating_only":["Trade-press summary"]}
```

```bash
python3 scripts/score.py sources.json
```

Output gives each source a `score` (weighted 1-5), a `band`
(A trust / B usable / C shaky / D unusable / **F flagged**), and the
`claim_verdict` = the weakest load-bearing source. `weakest_dim` names the
dimension dragging each source down so you know what to shore up.

### 4. Report the weakest link

State the verdict as the floor, not the average: *"This recommendation inherits
the credibility of its weakest load-bearing source — a vendor-funded whitepaper
(F flagged, independence 1/5). Treat as unproven until an independent source
corroborates."* Suggest the specific fix (find a primary source, get an
independent replication, disclose the funder).

## Verify

Run the bundled smoke test — the conflicted source must veto the claim even
though its average (2.65) is respectable, and the corroborating-only source must
be excluded from the verdict:

```bash
python3 scripts/score.py <<'EOF'
{"sources":[
 {"name":"funded","ratings":{"reliability":3,"independence":1,"primacy":4,
   "expertise":3,"corroboration":2,"transparency":2,"recency":5}}]}
EOF
# expect band "F flagged", weakest_link ["independence"], claim_verdict "F flagged"
```

Malformed input fails loud: a missing dimension or an out-of-1-5 rating raises a
`ValueError` naming the offending source rather than scoring silently.

## Pitfalls

- **Authority ≠ reliability.** A famous name with a conflict of interest still
  flags on `independence`. Rate the incentive, not the letterhead.
- **Averaging away a poison source.** Never mean-blend a fabricated or bought
  source into a healthy pack — that is exactly what the weakest-link veto exists
  to stop. If it is load-bearing, its flag is the claim's ceiling.
- **Counting the same source twice.** A press release, the article quoting it,
  and a tweet linking the article are *one* source's worth of independence, not
  three. Corroboration requires genuine independence of origin.
- **Confusing bias with unreliability.** A politically biased outlet can still be
  factually reliable, and vice versa — MBFC scores them separately. Keep
  `reliability` (track record) distinct from any partisanship judgement.
- **Over-trusting recency.** New is not truer; a fresh non-peer-reviewed
  preprint outranks nothing. Recency is deliberately the lowest weight (5%).
- **Gaming the rubric.** The numbers are only as honest as your justifications —
  record a one-line reason per rating so the score is auditable, not vibes.
