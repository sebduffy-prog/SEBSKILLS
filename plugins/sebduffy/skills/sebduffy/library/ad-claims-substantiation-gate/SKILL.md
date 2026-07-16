---
name: ad-claims-substantiation-gate
category: compliance
description: >-
  Port Claude-for-Legal's citation-gate to advertising. Run before any copy, script,
  or deck ships: an ASA/CAP/FTC jurisdiction onboarding interview, then a claim
  inventory that tags every factual, comparative, superiority, health, and green claim,
  attributes each to a verified source (using the Anthropic Citations API where sources
  are documents), flags model-knowledge or thin evidence as [verify], and enforces a
  hard human sign-off gate that BLOCKS unsubstantiated objective claims. Grounded on
  CAP Code 3.7/1.7 (hold evidence before publication) and the FTC reasonable-basis
  doctrine so nothing goes out that the ad can't back.
when_to_use:
  - Pre-flight review of ad copy, TV/radio scripts, OOH, social, or a pitch deck before it leaves the building
  - A brief contains comparative ("beats X"), superiority ("UK's number one"), health, or environmental claims
  - Legal/regulatory sign-off is required and you need an auditable substantiation ledger per claim
  - Setting the jurisdiction and rulebook (ASA/CAP UK, FTC/NAD US, EU UCPD) for a campaign at kickoff
  - Grounding factual claims in source documents with the Anthropic Citations API for traceable attribution
when_not_to_use:
  - Cookie/consent/tracking privacy compliance — use consent-privacy-compliance
  - General app-security or secrets review — use the security-review skill
  - Writing the actual ad copy or concepts (creative generation) — use frontend-design or a copy skill; this only vets claims
  - Non-advertising legal drafting (contracts, MSAs) — use Anthropic's Claude-for-Legal plugins directly
keywords:
  - advertising-claims
  - substantiation
  - asa
  - cap-code
  - ftc
  - comparative-claims
  - superiority-claims
  - greenwashing
  - citations-api
  - source-attribution
  - compliance-gate
  - puffery
  - human-in-the-loop
  - regulatory-review
similar_to:
  - consent-privacy-compliance
inputs_needed: >-
  The draft asset (copy, script, or deck text); the campaign jurisdiction(s); and the
  supporting evidence set (test reports, survey data, third-party sources) as documents
  or references. An ANTHROPIC_API_KEY only if you want programmatic Citations attribution.
produces: >-
  A per-claim substantiation ledger (JSON) with claim type, attributed sources, [verify]
  flags, and reviewer sign-off; a pass/block gate result; and a reviewer note recording
  any unverified or model-knowledge claims that must not ship.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Ad Claims Substantiation Gate

Ports the citation-gate pattern from Anthropic's **Claude for Legal** (Apache-2.0, launched May 2026 — "source attribution on every citation, jurisdiction established during an onboarding interview, explicit gates before anything is filed, sent, or relied on") to advertising review. Legal's rule is "the lawyer reviews and verifies; the tooling makes that review easier, never skips it." Same contract here: **the account/legal lead signs off; this skill makes the sign-off fast and auditable, and it BLOCKS anything unsubstantiated from shipping.**

## When to use

Run this as the last gate before any external asset (copy, TV/radio script, OOH, paid social, landing page, or new-business deck) leaves the agency — especially when it carries comparative, superiority, health, or environmental claims.

## Prerequisites

- **This is a workflow pattern, not an Anthropic product.** "Ad Claims Substantiation Gate" is our port; there is no official Anthropic advertising plugin. Claude for Legal is the real, cited reference implementation.
- **You are not a lawyer.** Output is a *draft for reviewer sign-off*, not legal advice and not a guarantee of ASA/FTC compliance. A qualified person must approve before publication.
- **Regulators are real and current (verified July 2026):** UK **CAP Code rule 3.7** — marketers must *hold documentary evidence before* submitting a marketing communication for publication; **rule 1.7** — hold substantiation and produce it to the ASA without delay. US **FTC** — advertisers must have a *reasonable basis before dissemination*; comparative and "establishment" claims carry heavier proof. These are the rules the gate encodes; confirm the live wording at asa.org.uk and ftc.gov for the specific campaign.
- **Citations API** (`"citations": {"enabled": true}` on a `document` content block) is generally available on active Claude models (except Haiku 3) and needs an `ANTHROPIC_API_KEY`. It attributes claims to *your supplied documents* — it does NOT prove a claim is true; it proves *where in your evidence a statement came from*. Use it for traceability, not truth.

## Recipes

### 1. Jurisdiction onboarding interview (do this first, once per campaign)

Ask, don't assume. Establish and write down:

- **Territory & rulebook:** UK (ASA/CAP, plus BCAP for broadcast) / US (FTC + self-reg NAD) / EU (UCPD) / other. Multi-market ads must clear the *strictest* applicable rule.
- **Sector overlays:** food/HFSS, alcohol, financial promotions (FCA), medicines/health (MHRA/CAP health rules), children.
- **Media & audience:** broadcast vs online changes the code section and the clearance body (e.g. Clearcast for UK TV).
- **House escalation rule:** who is the named sign-off, and what triggers external legal.

Save this as the campaign's practice profile (a short markdown note the rest of the review reads from — mirrors Claude-for-Legal's `CLAUDE.md` practice profile).

### 2. Claim inventory — extract and classify every claim

Read the asset line by line and pull out each *claim*, then tag its type. This is the whole game: the type decides the evidence bar.

| Type | Example | Evidence bar |
|------|---------|--------------|
| `factual` | "Contains 30% recycled plastic" | Objective proof (spec, test) |
| `comparative` | "Cleans better than Brand X" | Evidence vs **every** named/implied rival, like-for-like test |
| `superiority` | "UK's number one", "most awarded" | Robust proof for the whole claimed scope; verify method + period |
| `health` | "Clinically proven to reduce wrinkles" | Rigorous clinical evidence; wording must match what the study shows |
| `environmental` | "100% recyclable", "carbon neutral" | Full-lifecycle basis; beware greenwashing (CMA/ASA green-claims scrutiny) |
| `puffery` | "The nation's favourite cuppa" | None — subjective; consumers won't take it literally. **Passes the gate.** |

The dividing line (CAP): claims *capable of objective substantiation* need evidence; genuine puffery/opinion does not. When unsure, treat it as objective.

### 3. Attribute each objective claim to a verified source

For every non-puffery claim, record at least one source with `verified: true`. Where the source is a document (test report PDF, survey topline), use the **Citations API** so the attribution points at the exact passage:

```bash
curl https://api.anthropic.com/v1/messages -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" -H "content-type: application/json" -d '{
  "model": "claude-opus-4-8", "max_tokens": 1024,
  "messages": [{"role":"user","content":[
    {"type":"document","source":{"type":"text","media_type":"text/plain",
      "data":"BS EN 13300 lab test 4471: coverage 12 m2/L vs Brand X 6 m2/L."},
    "title":"Coverage test #4471","citations":{"enabled":true}},
    {"type":"text","text":"Does the evidence support: twice the coverage of Brand X?"}
  ]}]}'
```

The response returns cited blocks — `type: char_location` (text), `page_location` (PDF), or `content_block_location` — each with `cited_text`, `document_index`, `document_title`, and `start_char_index`/`end_char_index` (or page numbers). Store the `cited_text` and `ref` in the claim's `sources[]`. A claim answered from the model's own knowledge with no supplied document is **not attributed** — flag it `[verify]`.

### 4. Uncertainty flagging — never paper over gaps

Following Claude-for-Legal's "flags uncertainty instead of papering over it":

- Source is model knowledge only, or a document that doesn't actually support the wording → mark the source `verified: false`, status `[verify]`.
- Comparative claim where you have data for some but not all named rivals → still blocked (set `competitors_covered: false`).
- No evidence set connected at all → put a **reviewer note at the top of the deliverable**: "Sources not verified — do not publish."

### 5. Hard human gate — run the enforcer

Build the ledger (`scripts/gate.py` documents the JSON schema) and run:

```bash
python3 scripts/gate.py ledger.json          # exit 2 = BLOCKED, do not ship
python3 scripts/gate.py ledger.json --report # advisory table, exit 0
```

The gate BLOCKS if any objective claim has no attributed+verified source, is flagged `[verify]`, a comparative claim hasn't covered all rivals, or an objective claim lacks a named `signed_off_by`. Puffery passes. **A green gate is necessary but not sufficient** — the named reviewer still reads and approves the asset; the gate just guarantees they never approve an unsubstantiated objective claim by accident.

## Verify

- `python3 scripts/gate.py ledger.json` exits **2** while any objective claim is unsubstantiated, and **0** only when all are attributed, verified, and signed off.
- Every `comparative`/`superiority` claim in the ledger names its rival(s)/scope and its test method + period.
- Each objective claim's `cited_text` actually contains the fact asserted in the copy (read them side by side — attribution ≠ truth).
- The deliverable header carries a reviewer note whenever any claim shipped `[verify]` or no evidence set was connected.
- A named human appears in `signed_off_by` for every objective claim — not "the tool".

## Pitfalls

- **Citations proves provenance, not truth.** It shows a statement came from your document; it cannot tell you the document is sound. Bad evidence cited precisely is still a bad claim.
- **Comparative claims need ALL rivals covered, like-for-like.** Beating one competitor doesn't license "the best". Same test conditions or the comparison misleads (CAP 3.33–3.37 / FTC).
- **"Up to", averages, and asterisked small print** don't rescue a headline claim if the dominant impression misleads — the ASA judges overall impression.
- **Environmental claims are a live enforcement front.** "Recyclable", "sustainable", "carbon neutral" need full-lifecycle basis; vague green claims are the fastest route to a ruling. Escalate all of them.
- **Puffery is narrow.** "Probably the best" survived; specific-sounding superlatives ("clinically", "9 out of 10", "number one") do not — they're objective.
- **Don't skip the human.** The gate passing is the floor, not sign-off. Keep the reviewer in the loop; that's the entire point of porting Legal's pattern.
- **Regulations move.** Re-check the exact CAP/BCAP rule numbers and FTC guidance for the campaign's date and sector — this skill encodes the doctrine, not a frozen rulebook.
