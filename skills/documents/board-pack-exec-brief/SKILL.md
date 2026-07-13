---
name: board-pack-exec-brief
category: documents
description: >-
  Write dense, decision-first executive briefs — board pre-reads, ExCo/SLT decision
  memos, Amazon-style 6-pagers, options papers, and one-page decision notes — that lead
  with the ask and recommendation, not the backstory. Trigger whenever someone needs a
  written brief (NOT a deck) for a board, ExCo, SLT, client leadership, or investment
  committee: a pre-read, decision memo, options/business case, or QBR narrative. Structures
  the argument with the Minto Pyramid (answer first) and Situation–Complication–Resolution
  so a busy reader gets the recommendation and the decision needed in under 60 seconds.
when_to_use:
  - Drafting a board or ExCo pre-read that must be read cold before the meeting
  - Writing an SCR / SCQA decision memo that leads with a single recommendation and a clear ask
  - Producing an Amazon-style 6-pager narrative to replace a slide deck for a meaty decision
  - Building an options/business case that weighs 2-4 routes against explicit criteria
  - Condensing a sprawling analysis into a one-page decision note or single governing thought
  - Preparing a QBR or investment-committee narrative where prose must carry the argument
when_not_to_use:
  - The deliverable is a slide deck / pitch presentation — use pptx or data-driven-deck-generator
  - It is a team/company status update, newsletter, 3P, or incident report — use internal-comms
  - You want guided section-by-section co-authoring of a long spec/PRD/RFC — use doc-coauthoring
  - Turning a meeting recording/transcript into minutes and actions — use meeting-intelligence
  - The output must be a formatted Word .docx with letterhead/TOC/page numbers — use docx
keywords: [board pack, board pre-read, exec brief, decision memo, six pager, 6-pager, minto pyramid, scr, scqa, situation complication resolution, options paper, business case, one pager, exco, slt, investment committee, qbr, governing thought, decision paper]
similar_to: [internal-comms, doc-coauthoring, data-driven-deck-generator, meeting-intelligence, pptx]
inputs_needed: The decision or ask on the table, the audience and forum (board/ExCo/client/IC), the raw analysis or facts to draw on, any options being weighed, and the deadline/meeting date. Optionally a length target (1-pager vs 6-pager) and house tone.
produces: A finished decision-first written brief in Markdown (ready to paste into Docs/Word or hand to the docx skill) — headline recommendation, the ask, SCR-structured argument, options table, risks, and appendix — sized to the chosen format.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Board Pack & Executive Brief

Turn a messy pile of analysis into a **dense, decision-first written brief** a senior reader can absorb cold. This is prose, not slides: the argument carries in sentences, and the recommendation is legible in the first 60 seconds.

## When to use this skill

Use it whenever the deliverable is a *read*, not a talk-track: board pre-reads, ExCo/SLT decision memos, Amazon-style 6-pagers, options papers, business/investment cases, one-page decision notes, QBR narratives. If someone will *present slides*, use `pptx` / `data-driven-deck-generator` instead — a brief and a deck are different instruments.

## Prerequisites (honest)

- **No packages or keys.** This is a writing method; output is Markdown you paste anywhere or hand to the `docx` skill for letterhead/TOC formatting.
- **You need the decision, not just the topic.** A brief exists to get a *decision made*. If the ask is fuzzy, resolve it first (see Step 1) — a brief with no ask is just a report.
- **You need the evidence.** Numbers, options, and risks must be real. Never fabricate figures; mark unknowns as `[TBC]` and list them under Open Questions.

## The two frameworks this skill runs on

**Minto Pyramid Principle — answer first.** Lead with the single governing thought (the recommendation). Support it with 3-5 grouped arguments. Each argument is in turn supported by data. Readers descend the pyramid only as far as they need. Never make them assemble the conclusion themselves.

**SCR / SCQA — the narrative spine.** Open by establishing the shared, non-controversial *Situation*; introduce the *Complication* that disturbs it (the reason we're here); pose the implicit *Question* ("what should we do?"); deliver the *Resolution* (your recommendation). This is the classic pre-read opening and mirrors how Amazon narratives set up a decision.

## Recipe A — SCR decision memo / board pre-read (the default, ~1-3 pages)

1. **Nail the ask in one sentence.** Write it before anything else: *"We ask the Board to approve £X to do Y by Z."* If you can't, the brief isn't ready. Classify the ask: **Approve / Decide-between / Note / Discuss**.
2. **Write the BLUF header** (Bottom Line Up Front) — 3-5 lines the reader could act on alone:
   - **Recommendation:** the governing thought, one sentence.
   - **The ask:** exactly what you need from this forum.
   - **Why now:** the complication forcing a decision.
   - **What it costs / risks:** the headline number and the top risk.
3. **Body via SCR.** Situation (1 short para of agreed context) → Complication (what changed / the tension) → Resolution (the recommendation, then 3-5 pyramid arguments as bolded sub-heads, each 2-4 sentences of evidence).
4. **Options considered.** A tight table so the reader sees you weighed alternatives (below). Name the rejected options and *why* — this pre-empts the obvious pushback.
5. **Risks & mitigations**, then **Open questions / [TBC]**, then **Appendix** (detail the body doesn't need).
6. **Cut ruthlessly.** A pre-read earns its length. One decision → 1-2 pages. Push supporting detail to the appendix, not the argument.

## Recipe B — Amazon-style 6-pager narrative (a meaty, multi-part decision)

Full-sentence prose, no bullets-as-argument, ~6 pages, with data in the appendix (which does *not* count toward the six). A reliable section order:

1. **Introduction / the ask** — one paragraph: what this is and the decision requested.
2. **Tenets** (optional) — the principles you're optimising for, so disagreements surface as principle-level, not detail-level.
3. **Context / Situation** — what the reader must know to judge the rest.
4. **The problem (Complication)** — sharpened, quantified.
5. **Recommendation & rationale** — the pyramid: answer, then grouped reasons.
6. **Alternatives considered** — and why rejected.
7. **Risks, dependencies, financials.**
8. **Appendix** — FAQ, data tables, working. Anticipate the hard questions and answer them here.

Meetings that use this read the doc in silence for the first ~20 minutes, then discuss. Write for that: it must stand alone with zero narration.

## Recipe C — One-page decision note

Everything on Recipe A collapsed to a single page: BLUF header, a 3-bullet *why*, a 3-row options table, top risk, the ask. Use for fast governance items and delegated-authority approvals.

## Options table (drop into A, B or C)

```markdown
| Option | What it is | Cost / effort | Upside | Key risk | Verdict |
|--------|-----------|---------------|--------|----------|---------|
| 1. Recommended — Do X | one line | £X, N weeks | the payoff | the main downside | **Recommended** |
| 2. Do Y | one line | £Y | ... | ... | Rejected — reason |
| 3. Do nothing | hold | £0 | ... | the cost of inaction | Rejected — reason |
```
Always include a "do nothing" baseline — it makes the cost of inaction explicit and stops the decision drifting.

## Deliverable (always ship a file, never chat-only prose)

Do not end the session with the brief living only in the chat window. Write the finished brief to a real Markdown file — default `~/Desktop/<slug>-brief.md` (e.g. `board-pre-read-2026-q3.md`) — or, if the user asked for Word, hand that file to the `docx` skill for letterhead/TOC. Final step: confirm the file exists, open it, and spot-check that the BLUF header, options table, and appendix all landed. If inputs are thin (no firm numbers, options, or ask), still ship the full structure with every gap marked `[TBC]` and an **Open questions** block up top — an "awaiting data" scaffold the user can fill, not a verbal summary.

## Verify (checklist before you hand it over)

- [ ] **Answer first:** the recommendation and the ask are in the first 5 lines — cover the rest and the reader still knows what to do.
- [ ] **One governing thought**, supported by 3-5 grouped arguments (Minto). Not a list of everything you found.
- [ ] **SCR holds:** Situation is genuinely uncontroversial; Complication is the real reason for the meeting; Resolution answers the implicit Question.
- [ ] **Every argument carries evidence** — a number, a source, a named fact. No adjectives doing an analyst's job.
- [ ] **Options include a rejected set + "do nothing"**, each with a reason.
- [ ] **No fabricated figures.** Unknowns are `[TBC]` and listed under Open Questions.
- [ ] **Length is earned** — appendix holds the detail; the argument is tight.
- [ ] **MECE grouping:** the supporting arguments don't overlap and don't leave an obvious gap.
- [ ] **Passes the "read cold" test:** a reader with no prior context could act on it without you in the room.

## Pitfalls

- **Chronology instead of conclusion.** "First we did A, then B, then C…" buries the ask. Lead with the answer; the journey goes in the appendix if at all.
- **A deck flattened into prose.** Bullet fragments and orphaned chart titles aren't a brief. 6-pagers are *sentences*; if a point needs a slide's worth of build-up, write the build-up.
- **No decision.** If the reader finishes unsure what you want from them, it's a report, not a brief. State the ask and the forum's role (approve/decide/note).
- **Situation that's actually the Complication.** If your opening "Situation" is already contentious, the reader argues from line one. Situation = shared ground; Complication = the disturbance.
- **Recommendation with no rejected options.** Senior readers assume you cherry-picked. Show the alternatives and kill them explicitly.
- **Padding to hit a page count.** A 6-pager is a ceiling, not a target. One clean page beats six loose ones.
- **Weasel hedging.** "We could potentially consider exploring…" reads as no recommendation at all. Commit, then caveat with named risks.
