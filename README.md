# SEBSKILLS — The Ultimate Claude Code / Claude Code Web Skills Framework

A curated, deduplicated, and categorized library of **Agent Skills** for [Claude Code](https://docs.claude.com/claude-code) (CLI, Desktop, Web, and IDE extensions). Drop this repo into any project and Claude gains a set of reusable superpowers for building, designing, debugging, and shipping.

> **What is a Skill?** A folder with a `SKILL.md` file. The YAML frontmatter (`name`, `description`) tells Claude when to invoke it; the body tells Claude what to do. Claude loads the description for every skill at session start and pulls in the full body only when the task matches. See the official spec: <https://agentskills.io/specification>.

---

## TL;DR — three ways to use this repo

All three use the bundled installer. It creates symlinks to this repo; nothing is copied, so pulling new skills is a `git pull` away.

### 1. Shared user-level library (every Claude Code session)
```bash
git clone https://github.com/sebduffy-prog/sebskills ~/.claude/skills-lib
cd ~/.claude/skills-lib
./install.sh user
```
Every skill is now discoverable in every Claude Code session on this machine.

### 2. Project-local (only this project)
```bash
# from the root of your project
git clone https://github.com/sebduffy-prog/sebskills ../sebskills   # or submodule
../sebskills/install.sh project .
```
Skills are linked into `./.claude/skills/`; commit them if you want teammates to pick them up.

### 3. Claude Code Web (connect this repo as a second repo)
Add SEBSKILLS as a git submodule or connect it as a secondary repo in [claude.ai/code](https://claude.ai/code):
```bash
cd my-app
git submodule add https://github.com/sebduffy-prog/sebskills .claude/skills-lib
git commit -m "Add SEBSKILLS"
```
Push, then open the project on Claude Code Web. The web harness recursively discovers every directory containing a `SKILL.md` in any connected repo — no install step needed.

> For Windows or restricted environments where symlinks don't work, run `./install.sh web` to get the copy-based alternative.

---

## Framework at a glance

```
skills/
├── engineering-workflow/   → how Claude should think, plan, debug, review, ship
├── building-agents/        → Claude API, MCP servers, skill authoring
├── frontend-and-design/    → visual design, theming, web artifacts, testing
├── ui-effects/             → drop-in WebGL / CSS React components (Framer-grade)
├── documents/              → .docx / .pdf / .pptx / .xlsx / internal comms
├── media/                  → GIFs and other assorted media tooling
├── product/                → research, ideation, capability, launch
└── strategy/               → advertising, media, analyst, deck flow, headline stats
```

**67 skills** across 8 categories. Each is self-contained, has a `SKILL.md`, and carries its original license where applicable.

Raw source material (upstream zip bundles and the original single-file `.skill` packages that have already been expanded into `skills/ui-effects/`) lives in [`raw-files/`](raw-files) and is not loaded by Claude.

---

## The skills (quick index)

### Engineering Workflow — how to code well with an LLM
| Skill | Use it when… |
|---|---|
| [`karpathy-guidelines`](skills/engineering-workflow/karpathy-guidelines) | You want Claude to avoid overcomplication, surface assumptions, stay surgical |
| [`autonomy-policy`](skills/engineering-workflow/autonomy-policy) | At the start of every task — decides ACT (proceed) vs ASK (converse). The framework's ask-vs-act governor |
| [`brainstorming`](skills/engineering-workflow/brainstorming) | Before ANY creative work — explores intent and requirements first |
| [`writing-plans`](skills/engineering-workflow/writing-plans) | You have a spec and need a multi-step plan before touching code |
| [`executing-plans`](skills/engineering-workflow/executing-plans) | You have a written plan and need it executed with review checkpoints |
| [`test-driven-development`](skills/engineering-workflow/test-driven-development) | Implementing any feature or bugfix — tests first, code second |
| [`systematic-debugging`](skills/engineering-workflow/systematic-debugging) | Any bug, test failure, or unexpected behavior — before proposing a fix |
| [`verification-before-completion`](skills/engineering-workflow/verification-before-completion) | Before claiming work is done — evidence before assertions |
| [`requesting-code-review`](skills/engineering-workflow/requesting-code-review) | Before merging or finishing major work |
| [`receiving-code-review`](skills/engineering-workflow/receiving-code-review) | When getting review feedback — verify, don't performatively agree |
| [`finishing-a-development-branch`](skills/engineering-workflow/finishing-a-development-branch) | Work is complete — choose merge / PR / cleanup path |
| [`using-git-worktrees`](skills/engineering-workflow/using-git-worktrees) | Starting feature work that needs isolation |
| [`dispatching-parallel-agents`](skills/engineering-workflow/dispatching-parallel-agents) | 2+ independent tasks with no shared state |
| [`subagent-driven-development`](skills/engineering-workflow/subagent-driven-development) | Executing a plan with independent tasks in-session |
| [`using-superpowers`](skills/engineering-workflow/using-superpowers) | Meta-skill — how Claude should find and use every other skill |

### Building Agents — Claude API, MCP, and skill authoring
| Skill | Use it when… |
|---|---|
| [`claude-api`](skills/building-agents/claude-api) | Building/debugging/optimizing Anthropic SDK apps, prompt caching, model migrations |
| [`mcp-builder`](skills/building-agents/mcp-builder) | Creating a high-quality MCP server (Python/FastMCP or TS SDK) |
| [`skill-creator`](skills/building-agents/skill-creator) | Creating / modifying / testing / evaluating / optimizing a skill. Canonical skill-authoring entry point (absorbs what used to be `writing-skills`) |

### Frontend & Design — pages, components, theming, testing
| Skill | Use it when… |
|---|---|
| [`frontend-design`](skills/frontend-and-design/frontend-design) | Building distinctive, production-grade web UIs that avoid AI aesthetic |
| [`design-approval-gate`](skills/frontend-and-design/design-approval-gate) | Before shipping any visual/UI change — forces a preview + explicit user approval before marking done |
| [`web-artifacts-builder`](skills/frontend-and-design/web-artifacts-builder) | Multi-component Claude.ai artifacts (React + Tailwind + shadcn/ui) |
| [`canvas-design`](skills/frontend-and-design/canvas-design) | Posters, static art, design pieces in .png / .pdf |
| [`algorithmic-art`](skills/frontend-and-design/algorithmic-art) | Generative / flow-field / particle art in p5.js |
| [`theme-factory`](skills/frontend-and-design/theme-factory) | Apply a pre-set or custom theme across any artifact |
| [`brand-guidelines`](skills/frontend-and-design/brand-guidelines) | Applying Anthropic's official brand colors/type to an artifact |
| [`vccp-media-design`](skills/frontend-and-design/vccp-media-design) | VCCP Media 2026 — mustard + teal halves, Inter Tight, highlighter motif. Web UI, slides, PDFs, posters, infographics, social tiles, charts. |
| [`webapp-testing`](skills/frontend-and-design/webapp-testing) | Interactively testing a local webapp with Playwright |

### UI Effects — drop-in React / WebGL components
| Skill | Effect |
|---|---|
| [`image-shatter`](skills/ui-effects/image-shatter) | Image shatters into a grid on hover with spring physics + cursor magnet |
| [`interactive-distortion`](skills/ui-effects/interactive-distortion) | WebGL2 pixel-warp distortion that follows the cursor |
| [`liquid-image`](skills/ui-effects/liquid-image) | Water-ripple hover with grayscale→color reveal |
| [`liquid-glass-button`](skills/ui-effects/liquid-glass-button) | Apple-style frosted-glass button (pure CSS) |
| [`rubiks-image-cube`](skills/ui-effects/rubiks-image-cube) | Interactive 3D Rubik's cube displaying image segments |
| [`spectra-noise`](skills/ui-effects/spectra-noise) | Animated WebGL shader background (hue shift, warp, scanlines) |
| [`aurora-gradient`](skills/ui-effects/aurora-gradient) | Drifting blurred multi-color gradient background (Framer → Backgrounds) |
| [`magnetic-button`](skills/ui-effects/magnetic-button) | Button attracts toward cursor with spring snap-back (Framer → Buttons) |
| [`infinite-marquee`](skills/ui-effects/infinite-marquee) | Seamless looping logo / testimonial strip (Framer → Carousels) |
| [`animated-counter`](skills/ui-effects/animated-counter) | Number counts up on viewport entry with easing (Framer → Data) |
| [`floating-label-input`](skills/ui-effects/floating-label-input) | Material/Stripe-style input with floating label + focus ring (Framer → Forms) |
| [`magnetic-cursor`](skills/ui-effects/magnetic-cursor) | Global blend-mode cursor dot that grows over interactive elements (Framer → Interactions) |
| [`bento-grid`](skills/ui-effects/bento-grid) | Variable-span bento card grid with 3D hover tilt (Framer → Layout) |
| [`scroll-reveal-section`](skills/ui-effects/scroll-reveal-section) | Staggered fade/slide-in for children on viewport entry (Framer → Sections) |
| [`text-scramble`](skills/ui-effects/text-scramble) | Text scrambles random glyphs then "decrypts" to final string (Framer → Typography) |
| [`theme-toggle`](skills/ui-effects/theme-toggle) | Sun↔moon morphing dark-mode toggle with persistence (Framer → Utilities) |

### Documents — .docx, .pdf, .pptx, .xlsx, comms
| Skill | Use it for… |
|---|---|
| [`docx`](skills/documents/docx) | Any Word document work — create, edit, TOC, tracked changes |
| [`pdf`](skills/documents/pdf) | PDF create/merge/split/OCR/form-fill/watermark |
| [`pptx`](skills/documents/pptx) | Decks, slides, pitch decks — create or parse |
| [`xlsx`](skills/documents/xlsx) | Spreadsheets — clean, compute, chart, convert |
| [`doc-coauthoring`](skills/documents/doc-coauthoring) | Structured doc-writing workflow (specs, proposals, decisions) |
| [`internal-comms`](skills/documents/internal-comms) | Status reports, leadership updates, newsletters, incident reports |

### Media
| Skill | Use it for… |
|---|---|
| [`slack-gif-creator`](skills/media/slack-gif-creator) | Animated GIFs optimized for Slack |

### Strategy — advertising, media, research, audit, analyst, deck flow
**Research & data**
| Skill | Use it for… |
|---|---|
| [`raw-data-research`](skills/strategy/raw-data-research) | Write & execute scripts to parse and clean raw data — PDFs, scrapes, multi-sheet XLSX, JSON, transcripts |
| [`data-analyst`](skills/strategy/data-analyst) | Proper EDA, hypothesis tests, regression, time-series decomposition, A/B / lift / incrementality |
| [`data-cut-headline-stats`](skills/strategy/data-cut-headline-stats) | Cut a dataset and pull out the 3–7 stats worth a client slide |
| [`qualitative-research`](skills/strategy/qualitative-research) | Qual lifecycle — discussion guides, IDIs / groups / ethno, theme coding, synthesis |
| [`developed-research`](skills/strategy/developed-research) | Long-form immersive briefs, category reviews, sector POVs, audience deep dives |

**Audience & insight**
| Skill | Use it for… |
|---|---|
| [`audience-insight`](skills/strategy/audience-insight) | Excavate the human insight with tension — recognition / tension / brand-fit tests |
| [`audience-segmentation`](skills/strategy/audience-segmentation) | Build / name / profile / deploy segmentations (or interpret one a client owns) |
| [`cultural-semiotics`](skills/strategy/cultural-semiotics) | Decode category codes (Residual / Dominant / Emergent), spot tensions, recommend code-shifts |
| [`trend-foresight`](skills/strategy/trend-foresight) | Spot signals, weight them, separate fads from trends, write a foresight POV |

**Strategy**
| Skill | Use it for… |
|---|---|
| [`advertising-strategy`](skills/strategy/advertising-strategy) | Build a comms strategy from a brief — problem, audience, insight, role, SMP, RTB, measures |
| [`advertising-strategy-copy`](skills/strategy/advertising-strategy-copy) | Write the prose: propositions, manifestos, audience portraits, tone of voice — ban-list-enforced |
| [`media-strategy`](skills/strategy/media-strategy) | Channel role, brand/activation split, attention-adjusted reach, ESOV, flighting, test-and-learn |

**Audit & competitive**
| Skill | Use it for… |
|---|---|
| [`brand-audit`](skills/strategy/brand-audit) | Audit a brand's distinctive assets, mental availability, share metrics, coherence, drift |
| [`competitive-comms-audit`](skills/strategy/competitive-comms-audit) | Map competitors across positioning, codes, share, platform stability, white-space |
| [`share-of-search`](skills/strategy/share-of-search) | Compute / interpret share of search (Binet) as a leading indicator |

**Read-out & effectiveness**
| Skill | Use it for… |
|---|---|
| [`strategy-analyst`](skills/strategy/strategy-analyst) | Hybrid analyst-strategist read: hypothesis → triangulate → fact / inference / recommendation |
| [`deck-flow-structure`](skills/strategy/deck-flow-structure) | Plan the order of a deck before any slide is built — SCQA, story spine, pyramid |
| [`effectiveness-case`](skills/strategy/effectiveness-case) | IPA-standard effectiveness case — counterfactuals, triangulation, payback |

---

## Which skill for which task? (cheat sheet)

Every chain starts with `autonomy-policy` deciding whether the task is ACT (just do it) or ASK (pause and converse). The flows below assume that decision has already been made.

**"I'm about to start a feature…"**
→ `autonomy-policy` → `brainstorming` → `writing-plans` → `using-git-worktrees` → `test-driven-development`

**"I hit a bug."**
→ `autonomy-policy` → `systematic-debugging` → (fix) → `verification-before-completion`

**"I'm done, about to ship."**
→ `verification-before-completion` → `requesting-code-review` → `finishing-a-development-branch`

**"I want a striking hero image."**
→ `frontend-design` + pick one of `ui-effects/*` (shatter / liquid-image / distortion) → `design-approval-gate`

**"Build me a polished landing page."**
→ `frontend-design` + `theme-factory` + (optional) `ui-effects/*` → `design-approval-gate`

**"Write me a pitch deck."**
→ `pptx` + `theme-factory` + `canvas-design` → `design-approval-gate`

**"New client brief just landed."**
→ `advertising-strategy` → `data-cut-headline-stats` → `advertising-strategy-copy` → `deck-flow-structure` → `vccp-media-design` → `pptx`

**"Tracker / MMM / campaign data dropped — give me a POV."**
→ `data-cut-headline-stats` → `strategy-analyst` → `advertising-strategy-copy` → `deck-flow-structure`

**"Channel question — what should the media response look like?"**
→ `advertising-strategy` (problem) → `media-strategy` (channels) → `deck-flow-structure` → `vccp-media-design`

**"Pitch immersion — two weeks to know a category."**
→ `developed-research` + `cultural-semiotics` + `competitive-comms-audit` + `brand-audit` + `share-of-search` → `audience-insight` → `advertising-strategy` + `media-strategy` → `deck-flow-structure`

**"Folder of raw files — make this analysis-ready."**
→ `raw-data-research` → `data-analyst` → `data-cut-headline-stats` (or → `strategy-analyst`)

**"We need an effectiveness paper."**
→ `brand-audit` (baseline) + `share-of-search` + `data-analyst` (MMM / lift) → `strategy-analyst` → `effectiveness-case`

**"Qual study just wrapped — turn it into strategy."**
→ `qualitative-research` → `audience-insight` → `audience-segmentation` → `advertising-strategy`

**"Year-ahead trends piece."**
→ `trend-foresight` + `cultural-semiotics` + `developed-research` → `advertising-strategy-copy` (write-up) → `vccp-media-design`

**"Build an MCP server for my API."**
→ `mcp-builder` (+ `claude-api` if you're also calling Anthropic from it)

**"Turn this thing I keep repeating into a reusable tool."**
→ `skill-creator`

---

## How to add your own project + use these skills

This repo is designed to sit **next to** or **inside** your project. Three patterns:

### Pattern A — sibling library (recommended for teams)
```
my-org/
├── my-app/                 # Your project
│   └── .claude/
│       └── skills/         # symlinks created by ../sebskills/install.sh project .
└── sebskills/              # This repo, cloned once, shared
```
```bash
cd my-app && ../sebskills/install.sh project .
```

### Pattern B — submodule (recommended for solo dev + Claude Code Web)
```bash
cd my-app
git submodule add https://github.com/sebduffy-prog/sebskills .claude/skills-lib
git commit -m "Add SEBSKILLS"
.claude/skills-lib/install.sh project .
```
For Claude Code Web, the submodule alone is enough — the web harness recursively discovers every `SKILL.md` in any connected repo. The `install.sh` step is only needed for the CLI / desktop / IDE versions.

### Pattern C — user-global (recommended for solo dev, one machine)
```bash
git clone https://github.com/sebduffy-prog/sebskills ~/.claude/skills-lib
~/.claude/skills-lib/install.sh user
```
Every project on this machine picks up every skill automatically. No per-project setup.

In all patterns, Claude Code discovers `SKILL.md` files at session start. To ship a subset instead of all 49, run the installer and then `rm` the symlinks you don't want — the originals stay in `skills/`.

---

## Adding a new skill

1. Pick a category folder in `skills/`.
2. Create `skills/<category>/<your-skill>/SKILL.md`:
   ```markdown
   ---
   name: your-skill
   description: One-paragraph trigger description. What it does, when to use it, example phrasings.
   ---

   # Your Skill

   ## When to use
   ## What to produce
   ## Implementation notes
   ```
3. (Optional) Add `assets/`, `examples/`, or scripts alongside.
4. Add a row to the category's `README.md` index.
5. Add a row to this README's quick index.

Full guidance: [`skills/building-agents/skill-creator`](skills/building-agents/skill-creator).

---

## Sources & attribution

This framework is a curated remix. Original authors and licenses are preserved within each skill directory.

| Source | Upstream | Covers |
|---|---|---|
| Anthropic official Skills | [`anthropics/skills`](https://github.com/anthropics/skills) | Most `frontend-and-design`, `documents`, `building-agents`, `media` skills |
| Obra Superpowers | [`obra/superpowers`](https://github.com/obra/superpowers) | Most `engineering-workflow` skills |
| Karpathy Guidelines | [`forrestchang/andrej-karpathy-skills`](https://github.com/forrestchang/andrej-karpathy-skills) | `karpathy-guidelines`, root `CLAUDE.md` |
| Framer UI Effects | Framer modules, re-implemented standalone | All `ui-effects/*` |
| Awesome catalog (inspiration) | [`VoltAgent/awesome-agent-skills`](https://github.com/VoltAgent/awesome-agent-skills) | Directory-layout inspiration |
| Native to this framework | — | `autonomy-policy`, `design-approval-gate` (MIT) |

Each skill retains its original `SKILL.md` and license file where included.

---

## License

This repository is a collection; each skill carries its own license. The repo structure, organizing READMEs, and index are MIT.
