---
name: design-system
description: Use this skill to generate or audit design systems, check visual consistency, and review PRs that touch styling.
origin: ECC
category: frontend-and-design
when_to_use:
  - Generating a new design system with tokens, spacing, and type scales
  - Auditing visual consistency across a product or screens
  - Reviewing PRs that touch styling
  - Detecting AI-slop or generic aesthetics
when_not_to_use:
  - Applying an existing brand (VCCP/Anthropic) — use vccp-media-design or brand-guidelines
  - A quick theme swap on an artifact — use theme-factory
  - Building the components themselves — use frontend-ui-engineering
keywords:
  - design system
  - design tokens
  - visual consistency
  - audit
  - ai slop
  - style review
  - spacing scale
  - type scale
  - component library
  - tokens
  - pr review
  - generate
similar_to:
  - frontend-ui-engineering
  - theme-factory
  - brand-color-token-system
  - vccp-media-design
inputs_needed: Either the brand/product to generate a system for, or the codebase/PR/screens to audit.
produces: A generated design-system spec or a visual-consistency/AI-slop audit report.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Design System — Generate & Audit Visual Systems

## When to Use

- Starting a new project that needs a design system
- Auditing an existing codebase for visual consistency
- Before a redesign — understand what you have
- When the UI looks "off" but you can't pinpoint why
- Reviewing PRs that touch styling

## How It Works

### Mode 1: Generate Design System

Analyzes your codebase and generates a cohesive design system:

```
1. Scan CSS/Tailwind/styled-components for existing patterns
2. Extract: colors, typography, spacing, border-radius, shadows, breakpoints
3. (Optional) Research 3 competitor sites for inspiration (via browser MCP).
   No browser/network access? Skip this step and note the omission in DESIGN.md
4. Propose a design token set (JSON + CSS custom properties)
5. Generate DESIGN.md with rationale for each decision
6. Create an interactive HTML preview page (self-contained, no deps)
```

Output: `DESIGN.md` + `design-tokens.json` + `design-preview.html`

### Mode 2: Visual Audit

Scores your UI across 10 dimensions (0-10 each):

```
1. Color consistency — are you using your palette or random hex values?
2. Typography hierarchy — clear h1 > h2 > h3 > body > caption?
3. Spacing rhythm — consistent scale (4px/8px/16px) or arbitrary?
4. Component consistency — do similar elements look similar?
5. Responsive behavior — fluid or broken at breakpoints?
6. Dark mode — complete or half-done?
7. Animation — purposeful or gratuitous?
8. Accessibility — contrast ratios, focus states, touch targets
9. Information density — cluttered or clean?
10. Polish — hover states, transitions, loading states, empty states
```

Each dimension gets a score, specific examples, and a fix with exact file:line.

### Mode 3: AI Slop Detection

Identifies generic AI-generated design patterns:

```
- Gratuitous gradients on everything
- Purple-to-blue defaults
- "Glass morphism" cards with no purpose
- Rounded corners on things that shouldn't be rounded
- Excessive animations on scroll
- Generic hero with centered text over stock gradient
- Sans-serif font stack with no personality
```

## Examples

These are natural-language intents (there is no CLI or bundled tool to invoke):

- **Generate for a SaaS app:** "Generate a minimal design system with an earth-tones palette for this app."
- **Audit existing UI:** "Audit the UI at http://localhost:3000 across `/`, `/pricing`, and `/docs` for design-system consistency."
- **Check for AI slop:** "Check this UI for generic AI-slop patterns and flag them."
