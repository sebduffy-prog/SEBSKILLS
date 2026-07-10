---
name: rfp-proposal-response
category: documents
description: >
  Run a solicitation (RFP/RFI/ITT/PQQ/tender) from receipt to submission-ready
  draft the way a new-business/bid team does: shred the document into a line-by-
  line compliance matrix, decide bid/no-bid, mine the buyer's repeated pains into
  three-to-five win themes, then draft compliant answers grounded in a reusable
  content library. Use when the user says "respond to this RFP", "we got an ITT/
  PQQ/tender", "build a compliance matrix", "shred this RFP", "find the win
  themes", "draft the proposal response", "answer the security questionnaire", or
  drops a solicitation PDF/DOCX and asks how to win it. Enforces answer-every-
  requirement discipline so no mandatory line goes unanswered.
when_to_use:
  - "User drops an RFP/RFI/ITT/PQQ/tender/DDQ/security questionnaire and wants a structured response, not just a read"
  - "User wants every requirement shredded into a compliance matrix with owners, verdicts and cross-references"
  - "User needs a bid/no-bid call — which requirements are deal-breakers, where they're non-compliant"
  - "User wants win themes: the buyer's repeated pains/priorities turned into 3-5 differentiators that thread the whole response"
  - "User wants drafted, compliant answers reusing prior proposal content (a content/answer library) instead of writing cold"
  - "User is standing up a repeatable bid process — matrix template, answer library, colour-team reviews"
when_not_to_use:
  - "Only need to read/extract text or tables from the solicitation PDF with no bid work — use pdf"
  - "Reviewing the resulting contract/MSA for legal risk once you've won — use contract-review"
  - "Producing the final formatted proposal as a polished Word file (TOC, letterhead, styling) — draft here, then hand to docx"
  - "Building the pitch/sales deck rather than a written compliant response — use pptx or data-driven-deck-generator"
  - "Pricing model or cost spreadsheet for the bid — use xlsx / three-statement-financial-model"
keywords: [rfp, rfi, itt, pqq, tender, bid, proposal, compliance matrix, rfp shredding, win themes, content library, answer library, bid no-bid, solicitation, security questionnaire, ddq, new business, colour team review, executive summary, requirement traceability]
similar_to: [contract-review, pdf, docx, doc-coauthoring, data-driven-deck-generator]
inputs_needed:
  - "The solicitation file(s) — RFP/ITT/PQQ PDF or DOCX, plus any appendices, pricing schedules and Q&A addenda"
  - "Optional: a content/answer library of prior winning responses, boilerplate, case studies, certifications"
  - "Optional: submission rules — due date/time, format limits (page/word count), portal, mandatory forms"
produces:
  - "A compliance matrix (CSV) — one row per requirement with owner, Comply/Partial/Exception/No Bid verdict and cross-reference"
  - "A bid/no-bid recommendation with the deal-breaker requirements flagged"
  - "3-5 win themes tied to the buyer's repeated priorities, plus a proof point per theme"
  - "Drafted, compliance-mapped answers ready to pour into the final document"
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# RFP / Proposal Response

Take a solicitation from receipt to a submission-ready draft. The method is the
one bid teams and tools like Loopio and AutogenAI standardise around: **shred →
qualify → theme → draft → review**. The compliance matrix is the spine — if a
mandatory requirement is not a row in the matrix, it will be missed, and one
missed "shall" is often an automatic disqualification.

## When to use

Use the moment a request for proposal lands and someone has to *respond in
writing to defined requirements* — RFP, RFI, ITT (invitation to tender), PQQ
(pre-qualification questionnaire), tender, DDQ, or a security/vendor
questionnaire. If the task is reading a PDF, reviewing a signed contract, or
building a deck, use the alternatives named in `when_not_to_use`.

## Prerequisites

- **The solicitation text.** Extract it first with the `pdf` skill (or `docx`).
  Everything downstream depends on clean, complete requirement text — including
  appendices, pricing schedules, and any Q&A addenda that amend requirements.
- **`python3`** (3.9+, stdlib only) for the matrix helper — no install needed.
- **Optional content library.** Prior winning answers, boilerplate, case
  studies, certifications. Without one you draft cold (slower, still works). With
  one you reuse — this is the single biggest speed lever.
- **No API key or SaaS account required.** This skill is the *method*; commercial
  tools (Loopio, AutogenAI, Responsive/RFPIO) automate the same steps if the user
  has them, but nothing here depends on them.

## Recipes

### 1. Shred the solicitation into a compliance matrix

"Shredding" = deconstruct the document into atomic, testable requirements. Read
the whole solicitation and pull **every** obligation into a row. Signals:

- **Mandatory** language: *shall, must, is required to, will provide* → `M`.
- **Desirable** language: *should, may, preferred, is encouraged to* → `D`.
- Instructions to offerors, evaluation criteria, and submission rules (format,
  page limits, forms) are requirements too — capture them.
- Keep the **verbatim** text and its section number. Traceability back to the
  solicitation is what lets an evaluator (and a reviewer) confirm you answered.

Assemble the shredded list as JSON, then build the matrix CSV:

```bash
python3 scripts/build_compliance_matrix.py requirements.json -o matrix.csv
```

Each row carries: `req_id, section, requirement, mandatory (M/D), compliance,
owner, response_ref, win_theme, proof_point, status`. Compliance uses the
standard bid vocabulary: **Comply / Partial / Exception / No Bid**. Assign an
**owner** to every line and set internal deadlines *at least 48 hours before* the
real due date so there is time for review.

### 2. Bid / no-bid decision

Before drafting a word, qualify the deal — bidding costs real hours. Scan the
matrix for:

- **Deal-breakers**: mandatory requirements you cannot meet (a certification you
  lack, a delivery region you don't serve, an incumbent-only clause). One
  unmeetable `M` may kill the bid.
- **Exception count**: many `Partial`/`Exception` rows signal a poor fit.
- **Effort vs. odds**: page limits, custom forms, references required, and how
  wired the incumbent is.

Output a clear **Bid / No-Bid** recommendation with the specific rows that drive
it. It is cheaper to walk away early than to lose slowly.

### 3. Mine win themes

Win themes are the buyer's own repeated priorities, reflected back as reasons to
pick you. As you shred, tally what the buyer emphasises: if "data residency"
appears five times, that is a theme, not a footnote. Aim for **3-5** themes.

For each theme capture: the buyer pain it answers, *your* differentiated
response, and a concrete **proof point** (metric, case study, named client).
Thread the themes through the executive summary and tag matrix rows via the
`win_theme` column so answers reinforce the same few messages instead of reading
as disconnected form-filling.

### 4. Draft compliant answers

Work the matrix row by row, highest-weighted evaluation criteria first.

- **Answer the question asked**, in the buyer's own terminology, and make
  compliance obvious ("Yes — we comply. [evidence]"). Evaluators score against a
  rubric; make points easy to award.
- **Reuse the library.** Pull the closest prior answer into `proof_point`, then
  *tailor* it to this buyer — never paste generic boilerplate. If the user has
  Loopio/AutogenAI, this is their auto-suggest/generate step; the tailoring
  judgement is still yours.
- **Fold in the win theme** named on the row.
- Respect format limits (page/word count, required order). Update `status`
  through *Not started → Drafting → Review → Final*.

### 5. Colour-team review

Before submission, run the classic bid reviews (scale to the deal):

- **Pink team** — early structural read: are we answering the right questions?
- **Red team** — score the draft as the *evaluator* would against the rubric;
  hunt unanswered requirements and weak proof.
- **Gold team** — final exec sign-off, pricing, and submission compliance
  (forms complete, within limits, submitted to the right portal on time).

## Verify

- **Coverage:** every `M` row has `compliance != ""` and a non-empty
  `response_ref`. Fastest check:
  ```bash
  awk -F, 'NR>1 && $4=="M" && ($5=="" || $7=="") {print "GAP: "$1}' matrix.csv
  ```
  Any output is an unanswered mandatory requirement — fix before submission.
- **Themes:** 3-5 win themes, each with a proof point, and each appears in the
  executive summary.
- **Format compliance:** within page/word limits; all mandatory forms attached;
  submitted via the specified portal before the deadline.
- **Traceability:** pick three random matrix rows and confirm each maps to real
  text in the draft.

## Pitfalls

- **Paraphrasing requirements while shredding.** You lose the mandatory "shall"
  and answer a softer question than was asked. Keep verbatim text.
- **Ignoring Q&A addenda.** Buyers issue clarifications that *amend* requirements
  after release; a matrix built only from the original document goes stale.
- **Generic boilerplate.** Pasted, untailored library answers read as such and
  score badly. Reuse the structure, rewrite for *this* buyer.
- **Skipping bid/no-bid.** Teams burn days on unwinnable bids. Qualify first.
- **No single owner per row.** Shared ownership = orphaned requirements. One
  named owner, one deadline, per line.
- **Treating win themes as decoration.** Themes only work if they thread the
  whole response — exec summary through individual answers — not just a callout
  box.
- **This is the response, not the contract.** Once you win, review the resulting
  agreement with `contract-review` before signing.
