# Flowsheet format reference

Flowsheet is a flowchart sketching tool that exports in two formats:
Markdown (designed for Claude to read) and JSON (designed for round-tripping
back into the tool). Both describe the same data.

## Markdown export structure

Three sections, in this order:

### Section 1: `## Pages`

Every node, formatted as:
```
### N{id} · {Page Title}
- note line 1
- note line 2
```

If a page has no notes, it shows `- _no notes_`.

**How to read notes:** they describe what's ON the page — components, content,
branding intent, layout hints. Treat them as design directives, not flavour text.
Common note patterns:
- `Tab or vertical view` → the page is a hub with sub-sections that can render either way
- `Infinite Scroll` → sub-sections render as one long scrolling page, not separate routes
- `Sticky header`, `Modal`, `Animation?` → component-level instructions
- A brand name (e.g. "VCCP Branded", "Rubicon Branded") → the page inherits that brand's design system

### Section 2: `## Flow`

Every edge, formatted as:
```
- **{From Title}** {arrow} **{To Title}** **[{label}]** _({style})_
```

Where:
- `arrow` is `-->` (one-way), `<->` (bidirectional), or `---` (non-directional)
- `[label]` (optional) is the trigger/condition for the transition
- `_(style)_` (optional, omitted for "straight") is one of: `orthogonal`, `curved`, `dashed`, `thick`

### Section 3: `## Adjacency`

Explicit in/out lists per node:
```
- **{Title}**
  - in: {comma-separated incoming sources, or —}
  - out: {comma-separated outgoing targets, or —}
```

Use this section to spot orphans, hubs, entry points, leaves at a glance.

## JSON export structure

```json
{
  "nodes": {
    "n1": { "x": 100, "y": 200, "title": "...", "notes": "..." }
  },
  "edges": {
    "e1": {
      "from": "n1",
      "fromPort": "right",
      "to": "n2",
      "toPort": "left",
      "style": "curved",
      "arrow": "none",
      "label": ""
    }
  }
}
```

`fromPort` and `toPort` are one of `top`, `right`, `bottom`, `left` and indicate
which side of the node the edge connects to — usually NOT semantically meaningful,
just a layout detail. Ignore unless you're regenerating the visual.

`x` and `y` are canvas pixel coordinates. Useful as a fallback for inferring
relative layout (top→bottom is often hub→children) but don't rely on it.

## Edge style semantics

Flowsheet users use style to encode meaning. This is the most important thing
to read correctly:

| Style | Common meaning |
|-------|----------------|
| `straight` (no tag) | Primary navigation / standard route |
| `curved` | Standard parent→child relationship; default for routine nav |
| `orthogonal` (step) | Sequential / wizard-style transition |
| `dashed` | **Not a primary route.** Toggle, modal trigger, brand switch, secondary link, "see also" |
| `thick` | Emphasised / hero route / primary CTA path |

**Dashed is the one that matters most.** When you see dashed:
1. Check if the node it connects looks like a UI component (Button, Toggle, Switch, Modal)
2. If yes → render the "node" as a persistent UI affordance, not a separate page
3. If no → treat it as a soft/contextual link, not part of the main navigation

## Arrow modes

| Arrow | Meaning |
|-------|---------|
| `end` (`-->`) | One-way navigation from source to target |
| `both` (`<->`) | Bidirectional — users can go either way |
| `none` (`---`) | No direction implied — relationship only |

Note: in hand-drawn sketches, users often default to `none` because they're
focused on connecting things, not deciding direction. If most edges are `none`,
direction is being inferred from layout/style, not the arrow itself.

## Common Flowsheet patterns to recognise

**Pattern: Brand-switch toggle**
```
Brand A --- Toggle Button --- Brand B   (all dashed)
```
The "Toggle Button" is not a page. It's a persistent switcher available on both brand pages.

**Pattern: Hub with mixed-direction children**
```
Some children: Hub --- Child
Other children: Child --- Hub   (arrows flipped due to canvas layout)
```
Treat all connected sub-nodes as children of the hub, regardless of arrow direction.

**Pattern: Scoped duplicate**
```
Brand A --- Strategy (one node)
Brand B --- Strategy (different node, same title)
```
Two separate pages, scoped per brand. Do NOT merge.

**Pattern: Contextual "about" link**
```
Landing --- About --- (dashed)
```
About is a sibling reachable from Landing but not part of the main funnel.
