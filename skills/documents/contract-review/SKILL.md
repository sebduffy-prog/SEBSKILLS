---
name: contract-review
category: documents
description: >
  Review commercial contracts — MSAs, SOWs, NDAs, DPAs, order forms — the way a
  deal lawyer does: extract every obligation, deadline, payment term and renewal
  date into a structured register, score each clause against a risk playbook
  (which party it favours, why, and the fallback ask), redline the risky language
  as tracked changes, and hand back a plain-English risk summary a business owner
  can action. Use when the user says "review this contract", "check this MSA/SOW/
  NDA", "what are my obligations", "flag risky clauses", "redline this agreement",
  "is this indemnity one-sided", "what am I signing", or drops a legal PDF/DOCX and
  asks what to worry about. NOT legal advice — flags issues for a lawyer.
when_to_use:
  - "User drops an MSA, SOW, NDA, DPA, SaaS/order form or reseller agreement and asks what to worry about or what they're signing"
  - "User wants obligations, deadlines, payment terms, renewal/notice dates and termination rights pulled into a register"
  - "User wants clauses scored against a playbook — one-sided indemnity, uncapped liability, auto-renewal, unilateral change, broad IP assignment"
  - "User wants a redline (tracked-changes DOCX) with markup and fallback positions to send back to the counterparty"
  - "User wants a plain-English, business-owner-readable risk summary ranked by severity"
  - "User is comparing an inbound contract against their own standard/paper positions"
when_not_to_use:
  - "Drafting a contract from scratch or filling a template — use docx (tracked changes/find-replace) plus your own clause library"
  - "Only need to read/extract text or tables from the PDF with no legal analysis — use pdf"
  - "Editing/producing the Word file mechanically (TOC, letterhead, images) with no clause review — use docx"
  - "User wants an actual legal opinion, jurisdiction-specific enforceability, or to file/sign — escalate to a qualified lawyer; this skill only flags"
  - "Financial-model or spreadsheet output from the contract's numbers — use xlsx / three-statement-financial-model"
keywords: [contract review, msa, sow, nda, dpa, redline, tracked changes, indemnity, limitation of liability, liability cap, auto-renewal, obligations register, termination, playbook, clause risk, plain english summary, order form, ip assignment, governing law]
similar_to: [pdf, docx, doc-coauthoring, meeting-intelligence]
inputs_needed:
  - "The contract file (PDF or DOCX) — or pasted text"
  - "Which side you're on (customer/supplier, discloser/recipient) — flips who each clause favours"
  - "Optional: your playbook / standard positions, deal value, jurisdiction, must-haves and walk-aways"
produces: A structured obligations & dates register, a playbook-scored clause risk table (severity-ranked), a redlined tracked-changes DOCX with fallback language, and a plain-English risk summary
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Contract Review

Read a commercial contract the way a deal lawyer triages one: **extract → score → redline → summarise.** Output is issue-spotting for a human, **not legal advice**. Always lead the summary with that disclaimer.

**First question, every time: which side is the user on?** Every clause below favours one party. Indemnity, liability caps, termination-for-convenience and IP assignment all flip meaning depending on whether the user is the customer or the supplier, the discloser or the recipient. If unknown, ask before scoring.

## When to use

Use when someone hands you an MSA / SOW / NDA / DPA / order form and asks "what am I signing / what do I need to worry about / redline this." If they only want text extracted, use `pdf`; if they only want the Word file mechanically edited, use `docx`.

## Prerequisites

- **Read the file first.** PDF -> use the `pdf` skill (`pypdf` / `pdfplumber` for tables). DOCX -> `docx` skill or `python-docx`. Never review from the filename or a summary — quote actual clause text.
- For redlining you need the source as **DOCX**. If given a PDF, convert or rebuild the changed clauses in a DOCX; tracked changes cannot be injected into a flat PDF.
- Know the **counterparties, effective date, term, and which paper it is** (their standard, your standard, or negotiated) — read the cover/signature and definitions blocks first.

## Recipe 1 — Extract the obligations & dates register

Walk the whole document once and pull every hard commitment into a table. Miss nothing time-bound — dropped deadlines are the most common real-world failure.

| Field | What to capture |
|-------|-----------------|
| Obligation | The commitment, in plain words |
| Owner | Which party owes it (map "the Provider"/"the Client" to real names) |
| Trigger / due | Fixed date, or event + period (e.g. "30 days after invoice") |
| Source | Clause number + short quote |
| Consequence | What happens on breach (fee, termination right, interest) |

Then pull the **date-critical set** into its own list — these are what get diarised:
- **Term & effective date**, renewal type (fixed / evergreen auto-renew).
- **Notice-to-terminate window** and **auto-renewal cutoff** (e.g. "non-renewal notice ≥90 days before end" — the single most-missed date).
- **Payment terms** (net days, late interest, invoice disputes window).
- **SLA / delivery / milestone dates** and any liquidated damages.
- **Cure periods** (days to fix a breach before termination bites).
- **Insurance, audit, and reporting** recurring obligations.

## Recipe 2 — Score clauses against the risk playbook

For each clause below, state: **(a)** what it says, **(b)** who it favours *for the user's side*, **(c)** severity, **(d)** the fallback ask. Severity: CRITICAL (walk-away / uncapped exposure), HIGH (negotiate hard), MEDIUM (push if leverage), LOW (note only).

| Clause | Red flag (against you) | Typical fallback ask |
|--------|------------------------|----------------------|
| **Limitation of liability** | Uncapped, or cap far below deal value; carve-outs one-way; excludes the other side's liability entirely | Mutual cap = 12mo fees (or contract value); mutual carve-outs only (IP infringement, confidentiality, death/PI, gross negligence) |
| **Indemnities** | One-sided; broad "any and all claims"; no cap; defend-and-hold-harmless only from you | Make mutual where symmetric; cap consistent with LoL; limit to third-party claims from your breach/IP |
| **Auto-renewal / evergreen** | Renews automatically; long notice window; price uplift baked in | Shorten notice to 30–60 days; cap annual uplift (e.g. CPI or 5%); or convert to opt-in renewal |
| **Termination** | They get termination-for-convenience, you don't; no cure period; you owe early-termination fees | Mutual convenience right with equal notice; 30-day cure for material breach; delete/reduce ETFs |
| **IP / ownership** | Assigns your background IP or all deliverables to them; no licence back; work-for-hire over your tools | You retain background/pre-existing IP + tools; grant licence, not assignment; assignment only of bespoke deliverables on full payment |
| **Payment** | Short net terms; punitive late interest; no dispute window; auto price increases | Net-30/45; interest capped; good-faith dispute carve-out; notice + cap on increases |
| **Confidentiality / NDA** | Perpetual; one-way; over-broad definition; no return/destroy; residuals clause favouring them | Mutual; 3–5yr tail (perpetual only for trade secrets); standard carve-outs (public, independently developed, compelled by law) |
| **Data protection (DPA)** | No breach-notification SLA; broad sub-processor rights; data used to train models; poor deletion terms | Named sub-processors + change notice; breach notice ≤72h; no secondary use/training without consent; deletion on exit |
| **Unilateral change** | They can amend terms/pricing/policy by posting or on notice | Changes by mutual written agreement; or right to terminate on adverse change |
| **Warranties / disclaimers** | "AS IS", disclaims fitness/merchantability; no service warranty | Warranty of conformance to docs + workmanlike performance; remedy = re-perform or refund |
| **Governing law / venue** | Foreign jurisdiction, exclusive venue costly to you; arbitration waiving class/jury with their chosen forum | Neutral or your jurisdiction; or carve injunctive relief; scrutinise arbitration seat |
| **Assignment / change of control** | They assign freely, you can't; no consent on their CoC | Mutual consent-not-unreasonably-withheld; carve affiliate assignment |
| **Non-solicit / exclusivity** | Broad, long, covers all staff; exclusivity locks you in | Narrow to people who worked on the deal; 6–12mo; delete exclusivity or add volume commitment |
| **Force majeure** | One-way relief; payment obligations excused for them but not delivery to you | Mutual; excuses non-monetary performance only; termination right if prolonged |

Also flag **absences**: no liability cap at all, no confidentiality clause in an MSA, no DPA where personal data flows, no cure period, no IP clause on a build project. Missing protective clauses are as risky as bad ones.

## Recipe 3 — Redline as tracked changes

Deliver edits the counterparty can accept/reject, not prose. Use the `docx` skill's tracked-changes support, or `python-docx` for clean-copy replacements plus a change log. Minimal `python-docx` clause-swap pattern:

```python
from docx import Document

doc = Document("contract.docx")
OLD = "the total aggregate liability shall be unlimited"
NEW = "the total aggregate liability of each party shall not exceed the fees paid in the 12 months preceding the claim"

for p in doc.paragraphs:
    if OLD in p.text and p.runs:
        # capture the FULL paragraph text BEFORE touching runs — clearing runs first
        # would silently truncate any paragraph whose text spans multiple runs
        full = p.text
        for r in p.runs[1:]:
            r.text = ""
        p.runs[0].text = full.replace(OLD, NEW)
doc.save("contract-redlined.docx")
# verify: assert NEW is present and OLD is gone before sending the redline
assert any(NEW in p.text for p in Document("contract-redlined.docx").paragraphs)
```

For true Word **tracked changes** (`<w:ins>` / `<w:del>` revision marks) rather than a clean replacement, follow the `docx` skill — hand-editing `word/document.xml` runs the risk of corrupting the file, so use its helpers. Always pair the redline with a **change log** (clause, from -> to, why) so a reviewer sees intent at a glance.

## Recipe 4 — Plain-English risk summary

Lead with the disclaimer, then rank by severity so a busy owner reads top-down:

1. **Bottom line (1–2 sentences):** sign / negotiate / walk — and the single biggest reason.
2. **Deal-breakers (CRITICAL):** each with the clause, the exposure in plain money/risk terms, and the ask.
3. **Negotiate (HIGH/MEDIUM):** bulleted, most-favourable-ask first.
4. **Diarise these dates:** renewal cutoff, notice windows, payment terms, milestones.
5. **Open questions for the counterparty / your lawyer.**

Translate legalese: not "uncapped consequential damages" but "if their software loses your data, there's no ceiling on what you could owe — one incident could exceed the whole contract value."

## Verify

- [ ] Confirmed **which side** the user is on before scoring — every favours-call depends on it.
- [ ] Every register row and risk row **quotes a clause number**; nothing asserted from memory of the doc.
- [ ] The **auto-renewal / notice-to-terminate** dates are captured (top real-world miss).
- [ ] Checked for **missing** protective clauses, not just bad ones.
- [ ] Redlined DOCX opens in Word and the change log matches the edits.
- [ ] Summary opens with **"not legal advice — for a qualified lawyer to confirm."**

## Pitfalls

- **Reviewing from a summary, not the text.** Always read and quote the real clauses; defined terms ("Losses", "Confidential Information") often widen scope far beyond the plain word.
- **Ignoring the definitions section.** A benign-looking clause can be lethal because "Affiliate" or "Services" is defined broadly. Read defs before clauses.
- **Split runs in DOCX.** Word splits text across runs mid-sentence, so a naive `replace` misses matches — normalise the paragraph or use the `docx` helpers.
- **Scoring side-agnostically.** An uncapped indemnity is great if you're receiving it. Re-score if the user's side flips.
- **Flat PDF redlines.** You cannot inject tracked changes into a scanned/flat PDF — rebuild affected clauses in DOCX.
- **Over-claiming.** No enforceability opinions, no jurisdiction rulings. Flag, quote, suggest a fallback, and defer to counsel — that's the lane.
- **Losing the dates.** A perfect clause analysis that misses a 90-day non-renewal window still costs the client a year's fees. The date register is the highest-value output.
