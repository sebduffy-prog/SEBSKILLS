---
name: frontend-design
category: frontend-and-design
description: >
  Create distinctive, production-grade frontend interfaces with high design quality. Use this
  skill when the user asks to build web components, pages, artifacts, posters, or applications
  (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or
  when styling/beautifying any web UI). Generates creative, polished code and UI design that
  avoids generic AI aesthetics.
when_to_use:
  - Building a web component, page, application, or interface (websites, landing pages, dashboards)
  - Writing React components or HTML/CSS/JS layouts that need a strong aesthetic point of view
  - Styling or beautifying any existing web UI
  - Committing to a bold aesthetic direction (typography, color, motion, spatial composition) before coding
  - Avoiding generic "AI slop" aesthetics (Inter/Roboto, purple gradients, cookie-cutter layouts)
when_not_to_use:
  - Fixed-canvas visual designs like posters, flyers, or slide decks — use canvas-design or theme-factory
  - Shipping a visual change without user sign-off — run design-approval-gate first
  - A single named effect or component (e.g. magnetic-button, aurora-gradient, bento-grid) — use that sibling skill directly
  - Non-visual frontend work such as pure logic, data fetching, or API integration
keywords:
  - frontend
  - ui design
  - web components
  - landing pages
  - dashboards
  - react
  - html
  - css
  - typography
  - color theme
  - motion
  - animations
  - micro-interactions
  - spatial composition
  - backgrounds
  - aesthetics
  - styling
  - beautify
similar_to:
  - canvas-design
  - theme-factory
  - web-artifacts-builder
  - design-approval-gate
inputs_needed:
  - Frontend requirements — the component, page, application, or interface to build
  - Purpose and audience — what problem the interface solves and who uses it
  - Technical constraints — framework, performance, accessibility requirements
  - Desired tone or aesthetic direction, if the user has one
produces: Production-grade, visually distinctive frontend code (HTML/CSS/JS, React, Vue, etc.)
status: stable
owner: seb.duffy
updated: 2026-07-10
license: Complete terms in LICENSE.txt
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

## Design Thinking

Before coding, understand the context and commit to a BOLD aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction.
- **Constraints**: Technical requirements (framework, performance, accessibility).
- **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Frontend Aesthetics Guidelines

Focus on:
- **Typography**: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics; unexpected, characterful font choices. Pair a distinctive display font with a refined body font.
- **Color & Theme**: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.
- **Motion**: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions. Use scroll-triggering and hover states that surprise.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density.
- **Backgrounds & Visual Details**: Create atmosphere and depth rather than defaulting to solid colors. Add contextual effects and textures that match the overall aesthetic. Apply creative forms like gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, custom cursors, and grain overlays.

NEVER use generic AI-generated aesthetics like overused font families (Inter, Roboto, Arial, system fonts), cliched color schemes (particularly purple gradients on white backgrounds), predictable layouts and component patterns, and cookie-cutter design that lacks context-specific character.

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

Remember: Claude is capable of extraordinary creative work. Don't hold back, show what can truly be created when thinking outside the box and committing fully to a distinctive vision.
