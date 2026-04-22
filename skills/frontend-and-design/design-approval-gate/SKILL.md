---
name: design-approval-gate
description: Use BEFORE shipping any visual or UI change — new components, new pages, landing pages, hero sections, theme changes, ui-effects integrations, layout overhauls, or CSS rewrites affecting appearance. Forces a preview (screenshot, deployed URL, or code sandbox link) and explicit user approval before the work is marked done. Pairs with frontend-design, theme-factory, and every ui-effects/* skill.
---

# Design Approval Gate

**One job:** no visual change is "done" until the user has seen it and said yes.

<HARD-GATE>
Do NOT claim a visual/UI task complete, do NOT commit the final version, and do NOT move to the next task until:
1. You have produced a preview the user can actually look at (screenshot, deployed URL, running dev server, sandbox link, or exported artifact), AND
2. The user has explicitly approved it ("ship it", "looks good", "yes", or equivalent).
A typecheck passing, tests passing, or the code compiling is NOT approval. Approval is a human saying yes after seeing it.
</HARD-GATE>

## When this skill applies

**Always applies:**
- New page, new section, new component with visible output
- Landing pages, hero images, marketing surfaces
- Any `ui-effects/*` integration (shatter, liquid-image, distortion, aurora, etc.)
- `frontend-design`, `theme-factory`, `canvas-design`, `brand-guidelines` outputs
- Theme change, dark-mode rework, palette change, typography overhaul
- Layout refactor (grid change, responsive breakpoints, spacing system)
- Animation / micro-interaction changes a user would notice

**Does NOT apply (skip the gate):**
- Pure content edits (copy changes, typo fixes) — still worth a quick look but no gate
- Internal refactors with no visible change (renames, extract component, prop cleanup)
- Bug fixes that restore previously-approved behavior (visual regression fixes)
- The user explicitly said "just do it, don't ask" for this task

## How to apply it

1. **Announce the gate.** Before starting visual work, say: "I'll produce a preview before marking this done." Sets expectation.
2. **Build.**
3. **Produce a real preview.** Pick whichever is cheapest in the current environment:
   - Local dev server URL (start it, verify it loads)
   - Playwright screenshot via `webapp-testing`
   - Deployed preview URL (if the project has CI previews)
   - Exported artifact (PNG / PDF for `canvas-design`, slides for `pptx`)
   - Code sandbox / CodePen link for isolated components
4. **Share the preview and the specific things to look at.** Not just "here's the link." Call out: "Note the hero animation timing, the gradient direction, and the mobile nav." This focuses the review.
5. **Wait.** Do not continue, commit final, or move to the next task. If the user is slow to respond, ask once whether they want to defer approval, not twice.
6. **On feedback:** iterate. Produce a new preview. Re-gate. Approval of v1 is not approval of v3 — re-confirm after substantive changes.
7. **On approval:** explicit ACK from the user unlocks commit / merge / ship.

## Anti-patterns

- **"Looks like it should work."** No. Show it.
- **"The tests pass."** Irrelevant to visual approval.
- **Screenshotting the wrong state.** Show the thing the user actually cares about (hover, focus, mobile, dark mode — whatever is in scope).
- **Batching approval.** Don't build five components and ask for approval on all of them at once. Gate each meaningful piece.
- **Skipping the gate on "quick" changes.** "Quick" visual changes are exactly where taste-level disagreement happens. Still gate.

## Interaction with other skills

- `frontend-design`, `theme-factory`, `canvas-design`, `brand-guidelines`, every `ui-effects/*`: this gate runs at the end of their flow.
- `webapp-testing` is the preferred preview mechanism for anything running in a browser.
- `verification-before-completion` is about correctness; this skill is about appearance. Both must pass before "done."
- `autonomy-policy` designates visual work as ASK-mode; this skill is the specific form that ASK takes.
