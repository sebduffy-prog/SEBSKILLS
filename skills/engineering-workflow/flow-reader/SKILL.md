---
name: flow-reader
description: Read, interpret, and act on any flow-shaped diagram — UI/UX site maps, user journeys, state machines, agent graphs, workflow diagrams, system architecture — whether shared as a Flowsheet export, a Mermaid diagram, a screenshot of a flowchart, a JSON/YAML node-edge structure, or a plain bulleted list of pages and connections. Use this skill whenever the user pastes or attaches anything describing nodes connected by arrows or lines, mentions a "flow", "site map", "user journey", "state machine", "agent graph", "workflow", or "architecture diagram", shares text with arrow notation (single-headed, double-headed, or dashes), shares JSON with nodes/edges keys, shares a "Pages / Flow / Adjacency" Markdown structure, or asks Claude to build, critique, document, or route a sketched flow. Trigger generously — under-triggering wastes the user's careful work. When the input is shaped like a graph and the task involves understanding it, use this skill.
---

# Flow Reader

Reading a flow diagram is not the same as reading prose. A flow encodes design intent through structure — what's connected to what, in which direction, with which visual emphasis — and a lot of that intent gets lost if the diagram is treated as a flat list of items. This skill is the playbook for getting it right.

It handles four overlapping use cases, all of which start with the same reading step:

1. **Critique** — find gaps, dead ends, orphan nodes, weak IA, missing back-routes
2. **Build** — turn the flow into working code (Next.js routes, React components, state machine config, agent orchestration)
3. **Document** — produce specs, PRDs, route maps, journey docs
4. **Extend** — suggest missing nodes, fill thin sections, propose alternatives

If the user hasn't said which, infer from their phrasing or ask. Default to **build** if they pasted a flow with no instruction, since that's the most common downstream task.

---

## Step 1: Identify what you're looking at

Flow inputs arrive in several formats. Recognise the format before parsing.

**Flowsheet Markdown export** — has a three-section structure:
```
## Pages
### N1 · {Title}
- note
- note

## Flow
- **A** --> **B** **[label]** _(style)_

## Adjacency
- **A**
  - in: —
  - out: B
```

**Flowsheet JSON export** — has `nodes` and `edges` top-level keys; each edge has `from`, `to`, `fromPort`, `toPort`, `style`, `arrow`, `label`.

**Mermaid** — starts with `graph TD`, `flowchart LR`, `stateDiagram-v2`, etc.

**Plain text site map** — indented bullets, often with arrow-like notation (`→`, `->`, `-->`).

**Screenshot / image** — a drawn or screenshotted diagram. Read it visually: identify boxes, their labels, the lines between them, and any visual emphasis (line style, weight, colour).

**Node-edge JSON / YAML in some other shape** — could be from Figma, Whimsical, draw.io, LangGraph, n8n, etc. Look for the universal signature: a list of named things and a list of relationships between them.

If the format is ambiguous, ask. Don't guess.

---

## Step 2: Build the mental model BEFORE the response

This is the step that separates a good reading from a shallow one. Before writing anything for the user, internally answer these questions:

**Entry & exit topology**
- Which nodes have no incoming edges? Those are entry points.
- Which have no outgoing edges? Those are leaves / terminal states.
- Which has the most outgoing edges? That's likely the hub.
- Are there orphans (no edges at all)? Flag them.

**Direction realism**
- In hand-drawn sketches, **arrow direction is often a layout artefact, not navigation intent.** A node placed below its parent will be drawn with an arrow going up, even though semantically it's a child. If half the children of a hub point *to* the hub and half point *from* it, treat them all as siblings/children. Don't take the arrows literally without a sanity check.
- Exception: in state machines and agent graphs, direction is real and must be preserved.

**Edge style as semantics**
- Most flow tools use line style to encode meaning. Read them:
  - **solid / standard** — primary navigation or normal transition
  - **dashed** — optional, contextual, secondary, modal, or a toggle/switch (NOT primary nav)
  - **curved** — often used for parent→child standard links in Flowsheet specifically
  - **thick / bold** — emphasised / hero route
  - **dotted** — implicit, async, or "happens automatically"
  - **labelled** — the label is the trigger condition (`on success`, `if logged out`, `timeout`)
- When in doubt, treat dashed as "this is not a real route, it's a relationship" — that interpretation is rarely wrong.

**Duplicate titles**
- Two nodes with the same label in different sub-trees are almost always **intentional scoped duplicates** (e.g. a "Settings" page under each of three product areas). Do NOT consolidate them. Keep them as separate routes/components, scoped to their parent.

**Node-vs-component**
- Some "nodes" are not really pages. A node labelled "Button", "Toggle", "Modal", "Switch", "Animation" is a UI component, not a route. Render it as a persistent affordance attached to the pages it sits between, not as a standalone page. Common giveaway: it sits as a bridge between two sibling-like nodes (e.g. "Switch" between Brand A and Brand B).

**Asymmetry is information**
- If one branch has 9 children and a parallel branch has 3, that asymmetry is the user telling you something. Either one side is more developed, or the other side is genuinely thinner. Don't pad the thin side to match — preserve the asymmetry and flag it if it looks like an oversight.

**Notes are layout instructions**
- Page notes like "Tab or vertical view", "Infinite Scroll", "Modal", "Sticky header", "Animation?" are instructions for that specific page's rendering. Surface them — don't bury them as flavour text.

---

## Step 3: Output, scaled to the task

After building the model, produce output sized to what the user asked for. Default formats:

### For critique
A short prose read, then a structured list of findings. Order findings by severity. Include:
- Orphans / dead ends (nodes with no in or no out where there should be)
- Missing back-routes (where users can get stuck)
- Hub overload (too many children with no organisation)
- Duplicate/conflicting labels that aren't intentional
- Asymmetry that looks unintentional
- Missing standard pages (404, settings, profile, search, etc., where the context implies them)

### For build
A code deliverable scaled to the framework the user mentioned (or asked about). Standard outputs:
- **Web / Next.js**: a routes file or directory structure, plus stub components per page. Use the page notes as JSX placeholder content.
- **State machine**: an XState config or equivalent, with states, transitions, and guards from edge labels.
- **Agent graph**: a LangGraph / orchestration config with nodes, edges, and conditional routing from labels.

Don't build everything unless asked. Start with the structure (routes, state config, graph definition), confirm it looks right, then offer to fill in components/handlers.

### For documentation
Use this structure unless the user specifies otherwise:

```markdown
# {Flow Name}

## Overview
2–3 sentences: what this flow is, who it's for, how a user/agent traverses it.

## Entry points
List of nodes with no incoming edges and what brings users there.

## Primary path
The most common traversal, narrated.

## Sections
For each major sub-tree / hub:
### {Hub name}
- Purpose
- Sub-pages/states
- Layout notes from the source

## Edge cases & branches
Conditional routes, error paths, modal flows.

## Open questions
Gaps you noticed during reading.
```

### For extension
Bullet list of suggested additions, each with: where it slots in, why it's needed, what's currently missing without it. Don't dump 20 ideas — 3–5 high-value ones.

---

## Step 4: If anything is ambiguous, ask before acting

Things worth a clarifying question:
- Whether to honour arrow direction literally (matters for state machines, less for site maps)
- Whether duplicate-titled nodes are scoped duplicates or sketching mistakes
- Whether dashed edges are real connections or relationship hints
- Which framework/stack the build output should target
- Whether thin branches are intentional or to be filled

One question at a time. Don't pepper.

---

## Helper script

For Flowsheet JSON exports specifically (and any JSON in the same `{nodes: {...}, edges: {...}}` shape), `scripts/analyze_flow.py` produces a structured summary — entry points, leaves, hubs, orphans, edge-style distribution — that's faster and more reliable than eyeballing for graphs with >15 nodes.

Run it when:
- The graph has more than ~15 nodes (eyeballing gets unreliable)
- You need an authoritative orphan/dead-end check before critique
- The user asks for an audit or asks "what's wrong with this flow"

Skip it for small flows or non-JSON inputs (Mermaid, screenshots, prose) — parsing those by reading is fine.

Usage:
```bash
python scripts/analyze_flow.py <path-to-flowsheet.json>
```

Output is plain text designed to be read directly back into your reasoning, not shown to the user verbatim. Use it to inform your response.

---

## Reference material

For deeper specifics on particular flow types, consult the references when relevant:

- `references/flowsheet-format.md` — the full Flowsheet Markdown + JSON spec, edge-style semantics, and worked examples. Read when handling a Flowsheet export and you want to be sure about a detail.
- `references/diagram-types.md` — when to treat a flow as a site map vs. state machine vs. agent graph vs. user journey, and how the reading rules differ for each. Read when the input type isn't obvious or the user mixes paradigms.
- `references/build-recipes.md` — code-output patterns for the most common build targets (Next.js routes, XState, LangGraph). Read when the user wants a build deliverable and you need a clean starting structure.

---

## A worked example

User pastes:

```
## Pages
### N1 · Landing
- VCCP Branded
### N5 · Rubicon Page
- Rubicon Branded
- Tab or vertical view
### N7 · Button Inbetween the Two
- Rubicon to Irn Bru toggle
### N6 · Irn Bru Page
- Infinite Scroll

## Flow
- **Landing** --- **Rubicon Page** _(curved)_
- **Landing** --- **Irn Bru Page** _(curved)_
- **Rubicon Page** --- **Button Inbetween the Two** _(dashed)_
- **Button Inbetween the Two** --- **Irn Bru Page** _(dashed)_
```

Reading correctly:
- **Landing** is the entry hub (no incoming, two outgoing).
- **Rubicon Page** and **Irn Bru Page** are the two brand sub-experiences. Curved edge = standard parent→child navigation, even though `---` is non-directional.
- **Button Inbetween the Two** is NOT a page. It's a toggle component that lives on both brand pages. Dashed = "this is a UI affordance, not a route." Render it as a persistent switcher on the Rubicon and Irn Bru pages.
- "Tab or vertical view" on Rubicon and "Infinite Scroll" on Irn Bru are layout instructions for those specific hubs — apply them when building.

Wrong reading (what to avoid):
- Treating N7 as a standalone `/button` route.
- Asking the user "should I make a page for the toggle?" — the dashed-edge + UI-component name already answers that.
- Ignoring "Infinite Scroll" because it's just a note.

---

## One last thing

Flow diagrams are sketches. Sketches are lossy. The user has more context in their head than what's on the page — so when reading the flow gives you a strong inference, state the inference openly ("treating N7 as a toggle component, not a page — let me know if it should be a standalone route") rather than silently committing to it. That keeps the user in the loop without making them re-explain everything.
