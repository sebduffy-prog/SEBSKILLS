---
name: claude-excel-addin-ops
category: documents
description: >
  Drive the Claude for Excel add-in (the in-app sidebar, NOT file-level .xlsx
  editing) to change model assumptions while preserving formula dependencies,
  edit pivot tables and charts, apply conditional formatting and data
  validation, get cell-level citations for every calculation, trace and debug
  errors, save reusable Excel Skills, and carry live analysis into PowerPoint
  and Word via M365 shared context. Use for prompt patterns, install/deploy,
  verification, and honest limits of the generally-available add-in.
when_to_use:
  - Flexing a forecast assumption (discount rate, growth, margin) inside a live workbook and needing downstream cells to recompute correctly
  - Editing pivot tables/charts, applying conditional formatting, or setting data validation dropdowns through the Claude sidebar rather than by hand
  - Auditing how a number was derived and wanting clickable cell-level citations back to the source cells
  - Saving a repeatable variance/model-convention workflow as a one-click Skill available in the Excel and PowerPoint sidebars
  - Pulling numbers from an open Excel model straight into a PowerPoint slide or Word memo via shared context
  - Debugging a #REF!/#DIV/0! root cause across a multi-tab model in-app
when_not_to_use:
  - Programmatically reading/writing .xlsx/.csv files with pandas or openpyxl outside Excel — use xlsx
  - Building a formula-driven three-statement or DCF/LBO model spec from scratch — use three-statement-financial-model or dcf-lbo-valuation-model
  - Formal formula/dependency audit deliverable with a written trace report — use excel-model-audit
  - Designing scenario/sensitivity table structures and data-table mechanics — use excel-scenario-sensitivity
  - Authoring dynamic-array or LAMBDA formula libraries — use excel-dynamic-array-formulas or excel-lambda-functions
keywords:
  - claude for excel
  - excel add-in
  - formula dependencies
  - cell-level citations
  - pivot table
  - conditional formatting
  - excel skills
  - m365 shared context
  - powerpoint word
  - assumption flexing
  - three-statement model
  - prompt injection
  - office agents
  - claude log
  - data validation
similar_to:
  - excel-model-audit
  - excel-scenario-sensitivity
  - three-statement-financial-model
  - dcf-lbo-valuation-model
  - xlsx
  - excel-kpi-dashboard-formulas
inputs_needed: >
  A paid Claude account (Pro, Max, Team, or Enterprise); Excel on web / Windows
  M365 build 16.0.13127.20296+ / Mac 16.46+ with the add-in installed and
  signed in; a TRUSTED open .xlsx or .xlsm workbook. For cross-app work, the
  target PowerPoint/Word file must also be open.
produces: >
  In-workbook edits (assumption changes, pivot/chart/formatting edits) with
  highlighted cells and explanatory comments, answers with clickable
  cell-level citations, optional Claude Log audit tab, saved reusable Skills,
  and data carried into open PowerPoint/Word files.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Claude for Excel Add-in Ops

Operate the **Claude for Excel add-in** — the sidebar agent that reads from and
writes to the *currently open* workbook. This is distinct from `xlsx`, which
manipulates the file on disk. Everything below is grounded in Anthropic's
[Use Claude for Excel](https://support.claude.com/en/articles/12650343-use-claude-for-excel)
help article and the [office-agents docs](https://claude.com/docs/office-agents/excel).

## Agent-mode deliverable

Every recipe below is a prompt a *human* types into the Excel sidebar. When
running as an agent (Claude Code, headless — no sidebar), you cannot execute
them; do not end with chat-only narration. The deliverable is a **file**:
write a ready-to-paste prompt pack to `excel-addin-prompts.md` — one block per
relevant recipe, filled in with the user's actual cell refs, tab names, and
context — plus any workbook scaffolding python-openpyxl can do directly (e.g.
a pre-built Claude Log tab or named assumption cells).

## When to use

Reach for this when the value is in *live, dependency-aware* work inside an
open model: flex an assumption and let downstream cells recompute, trace a
number back to its source cells with citations, edit pivots/charts/formatting
by instruction, or push the result into a deck or memo without copy-paste.

## Prerequisites (read the honest bits)

- **Plan**: Generally available on **Pro, Max, Team, Enterprise**. It is GA,
  not beta — but the *cross-app shared-context* experience rolled out to Mac
  and Windows on paid plans **in beta** (March 2026 update), so treat
  Excel↔PowerPoint↔Word↔Outlook context passing as newer and less stable.
- **Platforms**: Excel on the **web**; **Windows** M365 build
  `16.0.13127.20296`+; **Mac** version `16.46`+ (build `21011600`+).
  **Not supported**: Excel 2016/2019 perpetual/volume, Excel on **iPad** (no
  SharedRuntime), Excel on **Android**, older M365 builds.
- **File formats**: `.xlsx` and `.xlsm` only.
- **Unsupported features**: **Data tables**, **macros**, and **VBA**. If a
  model relies on these, the add-in cannot drive them — fall back to `xlsx`
  or native Excel.
- **Models**: switchable between **Claude Opus 4.7, Opus 4.6, Sonnet 4.6** in
  the sidebar. (These are the versions the docs list as of writing; the picker
  changes as models ship.)
- **Data handling**: chat history is stored **locally in your browser via
  IndexedDB** — not on Anthropic servers, not synced across devices,
  clearable from Settings. Inputs/outputs deleted backend-side within ~30 days.
  **Not** included in Enterprise audit logs or the Compliance API, and it does
  **not** inherit org custom data-retention settings — flag this for regulated
  clients.
- **Trust**: only point it at **trusted** workbooks. See Pitfalls.

Install for yourself: Microsoft AppSource →
[Claude for Excel listing](https://marketplace.microsoft.com/en-us/product/office/WA200009404)
→ "Get it now" → open Excel, activate the add-in, sign in with your Claude
account. Admin deploy is via **Microsoft 365 Admin Center → Settings →
Integrated apps → Add-ins** (search "Claude by Anthropic for Excel"), or a
custom manifest XML (`https://pivot.claude.ai/manifest-excel.xml`) where Office
Store access is disabled.

## Recipes (real prompt patterns)

These run in the sidebar chat against the open workbook — not through any tool
call here. Be specific; name cells and tabs.

### 1. Flex an assumption, keep dependencies intact
Claude updates cell *values* while preserving formula relationships, so
downstream cells recompute. Verify with the citations it returns.
- "Change the discount rate in `Assumptions!B4` to 8% and update dependent
  calculations."
- "Flex the growth rate from 5% to 10% and show me the impact on terminal
  value."

### 2. Trace a number with cell-level citations
Answers include **clickable citations** that jump to the referenced cell — use
these to audit before trusting.
- "Walk me through how the revenue number in `Model!C42` is calculated."
- "What assumptions drive the gross-margin forecast, and cite each cell?"

### 3. Edit pivots, charts, formatting, validation
The add-in performs native Excel operations directly — ask plainly.
- "Add a `Region` filter to the pivot on the `Summary` tab and refresh it."
- "Apply a red-amber-green conditional format to `Actuals!D2:D200` by
  variance %."
- "Add a data-validation dropdown of Q1–Q4 to `Inputs!C3:C6`."

### 4. Debug a broken model
- "Find the root cause of the `#REF!` error in the summary tab and propose a
  fix."
- "Trace why `Calc!H15` returns `#DIV/0!`."

### 5. Turn on the audit trail
Claude highlights every cell it updates and leaves explanatory comments. For a
per-turn ledger, ask it to keep a **Claude Log** tab:
- "Keep a Claude Log tab and record every change you make this session."

### 6. Save a reusable Skill
Skills you enable in **Claude settings** are available in the Excel sidebar and
applied automatically as relevant. Teams can save standardized processes (a
specific variance analysis, an approved template fill) as reusable Skills
surfaced in both the Excel and PowerPoint sidebars. Set formatting defaults
that persist across every Excel conversation via **Settings → Instructions** in
the sidebar (Excel Instructions are separate from PowerPoint/Word).

### 7. Carry analysis into PowerPoint / Word (shared context)
With the target file **open**, one conversation can span apps — context
transfers automatically, so you do not re-explain the model.
- "Pull the revenue and EBITDA outputs from this model into new slides in the
  open deck."
- "Draft a Word memo in the open document summarizing the downside scenario."
Note: cross-app chat history is **not saved between sessions**, and Claude can
only read/write files that are **currently open**.

## Verify

- **Citations first**: click through the cell-level citations before accepting
  any explanation of a calculation — they are the auditable link.
- **Inspect highlights + comments**: every changed cell is highlighted with an
  explanatory comment; scan them (or the Claude Log tab) as the change record.
- **Overwrite protection**: Claude warns before overwriting existing data —
  read the warning, do not click through blindly.
- **Recompute check**: after an assumption flex, confirm a known downstream
  output moved in the expected direction (e.g. higher discount rate → lower
  terminal value).
- **Confirm risky ops**: when Claude asks you to confirm a risky operation,
  review it — especially on externally-sourced files.

## Pitfalls

- **This is not file editing.** It only touches the *open* workbook via the
  add-in. For headless/batch `.xlsx` work use `xlsx`; for a written audit
  deliverable use `excel-model-audit`.
- **Prompt injection is a real, documented risk.** Cells, formulas, and
  comments in an untrusted file can contain hidden instructions that trick the
  add-in into extracting or destroying data. Only use trusted spreadsheets;
  start from a trusted copy before wide edits.
- **No macros / VBA / data tables.** These silently fall outside scope — the
  add-in cannot drive them.
- **Not for final client deliverables or audit-critical numbers without human
  review.** Anthropic says so explicitly; treat output as a draft.
- **Compliance gap for regulated clients.** Activity is not in Enterprise audit
  logs or the Compliance API and ignores org retention settings — do not assume
  it is captured.
- **Cross-app context is beta and ephemeral.** Both files must be open;
  cross-app history is not persisted between sessions.
- **Local history only.** IndexedDB storage means clearing the browser or
  switching device loses conversation history; it does not sync.
- **iPad/Android/2016-2019 users cannot run it** — confirm the colleague's
  build before promising a live demo.
