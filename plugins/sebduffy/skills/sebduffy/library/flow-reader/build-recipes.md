# Build recipes

Quick-start patterns for turning a flow into working code. Pick the recipe
that matches the user's stack; adapt the structure to their flow.

## Recipe 1: Next.js App Router site

For a site map / UI flow.

**Directory shape:**
```
app/
├── layout.tsx              # Global layout (header, footer)
├── page.tsx                # Entry / Landing
├── {brand-or-section}/
│   ├── layout.tsx          # Section-specific layout (sticky toggle, etc.)
│   ├── page.tsx            # Section hub
│   ├── strategy/page.tsx
│   ├── ideas/page.tsx
│   └── ...
└── about/page.tsx          # Secondary / dashed-edge links live at top level
```

**Decisions to make from the flow:**

1. **Each hub gets a `layout.tsx`.** Hubs with the "tab" note get a tab component in their layout; hubs with "infinite scroll" get a long scrolling layout instead of separate routes (sub-sections become sections within a single `page.tsx`).

2. **Toggle/switch components** (anything dashed-linked between sibling hubs) go into a shared layout, not as routes. Example: a brand-switch toggle lives in `app/layout.tsx` or in a parent layout shared by both brand sections.

3. **Scoped duplicates** (Strategy under brand A vs. Strategy under brand B) are separate route files: `app/brand-a/strategy/page.tsx` and `app/brand-b/strategy/page.tsx`. Do not share a single Strategy component unless the flow makes that explicit.

4. **Notes become placeholder content.** Each page stub renders the notes as a list, with a TODO comment. Lets the user see the scaffold immediately and fill in real content later.

**Page stub template:**
```tsx
// app/brand-a/strategy/page.tsx
export default function Strategy() {
  return (
    <main>
      <h1>Strategy</h1>
      {/* TODO: from flow notes */}
      <ul>
        <li>Insight-led approach</li>
        <li>Channel mix</li>
      </ul>
    </main>
  );
}
```

## Recipe 2: XState state machine

For a state machine / interaction flow.

```ts
import { createMachine } from 'xstate';

export const flowMachine = createMachine({
  id: 'flow',
  initial: 'landing',
  states: {
    landing: {
      on: {
        CLICK_BRAND_A: 'brandA',
        CLICK_BRAND_B: 'brandB',
      },
    },
    brandA: {
      on: {
        TOGGLE: 'brandB',
        OPEN_STRATEGY: 'brandA.strategy',
      },
      // nested states for sub-pages
    },
    brandB: {
      on: { TOGGLE: 'brandA' },
    },
  },
});
```

**Decisions to make from the flow:**

1. **Edge labels become event names.** `[on click]` → `CLICK`. `[on success]` → `SUCCESS`. Normalise to `SCREAMING_SNAKE_CASE`.
2. **Sub-sections of a hub become nested states**, not top-level states.
3. **Guards from conditional labels.** `[if logged in]` → a `cond` on the transition.
4. **Final states marked with `type: 'final'`.**

## Recipe 3: LangGraph agent workflow

For an agent graph.

```python
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    input: str
    research: str
    draft: str
    final: str

graph = StateGraph(AgentState)

graph.add_node("researcher", researcher_fn)
graph.add_node("writer", writer_fn)
graph.add_node("editor", editor_fn)

graph.set_entry_point("researcher")
graph.add_edge("researcher", "writer")
graph.add_conditional_edges(
    "writer",
    lambda state: "approve" if state["draft"] else "redo",
    {"approve": "editor", "redo": "writer"},
)
graph.add_edge("editor", END)
```

**Decisions to make from the flow:**

1. **Each node becomes a function** taking `state` and returning a partial state update.
2. **Conditional edges** come from labelled edges or branching arrows.
3. **Loops** (cycles in the graph) are valid — make sure there's a termination condition.
4. **State shape** is inferred from what each node needs to read/write. Start minimal and let the user expand.

## Recipe 4: Documentation only

For "document this flow" requests, no code.

```markdown
# {Flow Name}

## Overview
{2-3 sentences from the structure: entry point, primary paths, what the
user/system achieves by traversing it.}

## Entry points
- **{Name}** — {how a user arrives here, based on context}

## Sections
### {Hub name}
{Purpose, sub-pages list, layout notes from the source.}

## Routes / States / Transitions
| From | To | Trigger | Notes |
|------|-----|---------|-------|
| ... | ... | ... | ... |

## Open questions
- {Anything ambiguous in the flow that the user should resolve before build}
```

## General tips for any build

1. **Don't build the whole thing in one shot.** Start with structure (routes, state config, graph). Show the user. Confirm. Then fill in components.

2. **Use the user's own labels verbatim.** If they wrote "Audience Bridge" don't rename it to "AudienceConnector". Their language is the source of truth.

3. **Flag your inferences.** If you treated a node as a component instead of a page, say so in a one-liner: "Treated 'Toggle' as a UI affordance, not a route — let me know if it should be standalone."

4. **Leave TODOs where the flow is thin.** Don't invent content. A `{/* TODO */}` comment is more honest than fake copy.

5. **Match the stack.** If the user mentions Next.js, don't propose Remix. If they say "vanilla HTML", don't reach for React.
