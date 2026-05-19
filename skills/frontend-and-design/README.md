# Frontend & Design

**Pages, components, artifacts, theming, and visual art.**

Everything Claude needs to produce a polished UI — from a Tailwind landing page to a generative poster.

## Index

| Skill | Use when |
|---|---|
| [`frontend-design`](frontend-design) | Building web components, pages, landing pages, dashboards, React/HTML layouts. Focus: distinctive, production-grade, avoids generic "AI UI" aesthetic. |
| [`design-approval-gate`](design-approval-gate) | Before shipping any visual / UI change — forces a preview (screenshot, URL, artifact) and explicit user approval before marking done. Pairs with every other skill in this folder and every `ui-effects/*`. |
| [`web-artifacts-builder`](web-artifacts-builder) | Elaborate multi-component claude.ai artifacts with state/routing/shadcn — not for single-file HTML. |
| [`canvas-design`](canvas-design) | Static visual art — posters, designs, pieces in .png / .pdf. |
| [`algorithmic-art`](algorithmic-art) | Code-based generative art with p5.js (flow fields, particle systems, seeded randomness). |
| [`theme-factory`](theme-factory) | Apply a cohesive theme (10 presets or a custom one) to any artifact: slides, docs, HTML. |
| [`brand-guidelines`](brand-guidelines) | Apply Anthropic's official brand colors/typography to an artifact. |
| [`vccp-media-design`](vccp-media-design) | VCCP Media 2026 brand — mustard + teal halves, Inter Tight, highlighter parallelogram motif. The four official brand lockups live in `assets/logos/`. Use for any VCCP web UI, slide deck, PDF report, poster, infographic, social tile, or chart. |
| [`vccp-logo-use`](vccp-logo-use) | Recolour the four VCCP bear-and-girl lockups for client-branded surfaces — CSS masks, ImageMagick, Pillow + python-pptx recipes. Use only on co-branded / sponsor / white-label work; VCCP-owned surfaces stay black. |
| [`professional-page-templates`](professional-page-templates) | Section taxonomy (20+ block types) + 11 starter shapes for genuinely different page layouts: SaaS landing, agency portfolio, product launch, startup metrics, indie creator, creator portfolio, community event, newsroom, dashboard-product, portfolio feed, experiential art. Use whenever the user wants Lovable-level template variety. |
| [`webapp-testing`](webapp-testing) | Playwright-based interactive testing of a local webapp — verify UI works, screenshot, read browser logs. |

## Recipes

**"Build me a stunning landing page"**
→ `frontend-design` → `theme-factory` (optional polish) → pick one effect from [`../ui-effects/`](../ui-effects/)

**"Make a pitch deck look professional"**
→ [`../documents/pptx`](../documents/pptx) + `theme-factory` + `canvas-design` for cover art

**"Design a poster"**
→ `canvas-design` (+ `algorithmic-art` if you want generative)

**"Verify my Next.js page actually works"**
→ `webapp-testing`

**"Artifact with tabs, state, shadcn buttons, routing"**
→ `web-artifacts-builder` (not `frontend-design` — that one is file-output focused)

## Pair with

- [`../ui-effects/`](../ui-effects/) for hero-image effects
- [`../engineering-workflow/test-driven-development`](../engineering-workflow/test-driven-development) + [`webapp-testing`](webapp-testing) to TDD the UI

## Attribution

All Anthropic-origin skills come from [`anthropics/skills`](https://github.com/anthropics/skills). `design-approval-gate` is native to this framework.
