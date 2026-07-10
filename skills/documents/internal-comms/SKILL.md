---
name: internal-comms
category: documents
description: A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use. Claude should use this skill whenever asked to write some sort of internal communications (status reports, leadership updates, 3P updates, company newsletters, FAQs, incident reports, project updates, etc.).
when_to_use:
  - Writing a 3P update (Progress, Plans, Problems) for a team or leadership
  - Drafting a company-wide newsletter or all-hands announcement
  - Answering FAQs / common questions in the company's preferred format
  - Producing a status report, leadership update, or project update
  - Writing an incident report or any general internal communication
  - Matching an internal message to the company's established tone and template
when_not_to_use:
  - The deliverable is a formatted Word .docx (letterhead, TOC, page numbers) — use docx
  - Guided section-by-section co-authoring of a longer doc/spec/proposal — use doc-coauthoring
  - Turning a meeting recording/transcript into minutes and follow-up emails — use meeting-intelligence
  - Reviewing a contract's clauses and obligations — use contract-review
keywords: [internal comms, 3P updates, progress plans problems, company newsletter, company comms, weekly update, faqs, common questions, status report, leadership update, project update, incident report, all-hands, announcement, updates]
similar_to: [doc-coauthoring, meeting-intelligence, docx]
inputs_needed: The communication type (3P/newsletter/FAQ/status/incident), the audience, and the raw content or context to convey; optionally the company's tone/template preferences.
produces: A formatted internal communication written to the company's preferred structure and tone for the chosen comms type.
license: Complete terms in LICENSE.txt
status: stable
owner: seb.duffy
updated: 2026-07-09
---

## When to use this skill
To write internal communications, use this skill for:
- 3P updates (Progress, Plans, Problems)
- Company newsletters
- FAQ responses
- Status reports
- Leadership updates
- Project updates
- Incident reports

## How to use this skill

To write any internal communication:

1. **Identify the communication type** from the request
2. **Load the appropriate guideline file** from the `examples/` directory:
    - `examples/3p-updates.md` - For Progress/Plans/Problems team updates
    - `examples/company-newsletter.md` - For company-wide newsletters
    - `examples/faq-answers.md` - For answering frequently asked questions
    - `examples/general-comms.md` - For anything else that doesn't explicitly match one of the above
3. **Follow the specific instructions** in that file for formatting, tone, and content gathering

If the communication type doesn't match any existing guideline, ask for clarification or more context about the desired format.

## Keywords
3P updates, company newsletter, company comms, weekly update, faqs, common questions, updates, internal comms
