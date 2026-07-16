---
name: autosuggestive-schema-builder
category: building-agents
description: >
  Build Lovable.dev / v0-style no-code builders where Claude proposes
  accept/reject changes against a declarative content schema with a
  live preview pane updating in real time. Covers the full loop: a
  registry of typed sections, an editable-schema config (which props
  are inline fields vs. repeating arrays), a `/suggest` API endpoint
  returning 5 kinds of structured operations (patch / add / remove /
  move / replace) with per-suggestion reasons, an Accept/Reject UI,
  applySuggestion mutators that handle each op safely, and a sticky
  CSS-variable-scoped LivePreview component that renders the schema
  through the same component registry the published page uses. Trigger
  this skill whenever the user wants to "build a page builder",
  "Lovable for X", "drag-and-drop site editor", "Claude makes
  suggestions in the schema", "live preview pane", "render control of
  the site", "structured AI edits", "accept/reject AI changes",
  "no-code editor", or "schema-driven builder". The pattern works for
  any domain where output is a list of typed blocks: marketing pages,
  email templates, dashboards, slide decks, forms, courses. SKIP only
  if the user wants free-text AI editing without structured operations.
when_to_use:
  - Building a Lovable.dev / v0-style no-code page builder where Claude proposes accept/reject edits
  - The output is a list of typed blocks (sections, slides, widgets, email blocks, form steps) rendered from a component registry
  - The user wants schema-level structured AI edits (patch/add/remove/move/replace) with a per-suggestion reason, not free-form prose edits
  - You need a live preview pane that renders the schema through the same registry the published page uses
  - Wiring a /suggest endpoint that returns validated structured operations from a single Claude call, with a mock-mode fallback
  - Adding reversible, auditable AI editing — every suggestion is one op the user can undo or batch
when_not_to_use:
  - Free-text AI editing without structured operations — a chat editor is the right shape, not this
  - Output is a single long blob rather than a list of typed blocks
  - You need the raw Anthropic API plumbing (caching, models, tool use) — see claude-api
  - Exposing the builder's actions as tools for other LLMs — see mcp-builder
  - Authoring a new skill rather than a builder app — see skill-creator
keywords:
  - page builder
  - no-code editor
  - schema-driven builder
  - accept/reject suggestions
  - live preview
  - structured operations
  - patch add remove move replace
  - section registry
  - editable schemas
  - suggest endpoint
  - applySuggestion
  - lovable
  - v0
  - render control
  - suggestion cards
  - list of typed blocks
  - next.js
  - anthropic api
similar_to:
  - claude-api
  - mcp-builder
inputs_needed:
  - The content domain and its typed block types (sections, slides, email blocks, etc.)
  - Which props per block are inline editable fields vs. repeating arrays
  - Whether an ANTHROPIC_API_KEY is available or mock-mode fixtures are needed
  - Theme/CSS-variable pack the LivePreview should scope to
produces: A Next.js builder app — section registry, editable-schema config, /suggest endpoint, accept/reject suggestion UI, and a live preview pane
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Autosuggestive schema builder

The recipe for a no-code editor where Claude is a structured
collaborator — not a chatbot. The user sees suggestions as cards,
clicks Accept or Reject, watches the live preview update. No prose to
parse, no diffs to interpret, no waiting for free-form generation.

Originally shipped in the VCCP Sandbox Recording Studio
([`pages/api/page/suggest.js`][1], [`page/new.jsx`][2]) — but the
shape transfers to any list-of-blocks content domain.

[1]: https://github.com/vccp/sandbox/blob/main/pages/api/page/suggest.js
[2]: https://github.com/vccp/sandbox/blob/main/pages/workspace/%5Bslug%5D/page/new.jsx

## When to use

- The output is a **list of typed blocks** (sections / slides /
  widgets / steps). If output is a single long blob, this isn't the
  shape — use a chat editor instead.
- The user expects **schema-level editing** (move section 3 above
  section 2; tweak the headline; swap the bento for a comparison
  table). Free-form prose editing maps poorly.
- You want **reversibility and auditability** — every suggestion is
  one structured op, easy to undo or batch.

## The five operations

Every accept/reject card represents exactly one of these:

```ts
type Suggestion =
  | { id: string; kind: 'patch';   targetIndex: number; patch: object; reason: string }
  | { id: string; kind: 'add';     insertAt: number;    section: { sectionId: string; props: object }; reason: string }
  | { id: string; kind: 'remove';  targetIndex: number; reason: string }
  | { id: string; kind: 'move';    targetIndex: number; toIndex: number; reason: string }
  | { id: string; kind: 'replace'; targetIndex: number; section: { sectionId: string; props: object }; reason: string };
```

Every suggestion **must** carry a one-sentence `reason` — that's how
the user decides at-a-glance. Without it, accept rates plummet because
the user has to read the diff to know what they're agreeing to.

## Stack architecture

```
┌────────────────────────────────────────────┐
│   sectionRegistry  →  id → { component, displayName, category }
│   editableSchemas  →  id → { fields[], arrays{} } + defaultsFor(id)
└──────────────────────────────────┬─────────┘
                                   │  imported by both:
                ┌──────────────────┴───────────────────┐
                │                                       │
       ┌────────▼─────────┐                  ┌──────────▼──────────┐
       │  Builder UI      │                  │  /api/suggest       │
       │  - schema editor │  POST(current)   │  - reads schemas    │
       │  - LivePreview   │ ───────────────▶ │  - calls Claude     │
       │  - accept/reject │ ◀─────────────── │  - returns ops[]    │
       │  - applyOp()     │   ops + reasons  │                     │
       └──────────────────┘                  └─────────────────────┘
```

Both the builder UI and the suggest endpoint read from the **same**
section registry + editable-schema config. That single source of truth
is what makes the loop work — Claude knows the exact prop shape of
each section type, so its suggestions parse cleanly.

## Registry shape

```js
// sectionRegistry.js — one source of truth
import HeroAurora from './sections/HeroAurora.jsx';
// …

export const SECTION_REGISTRY = {
  'hero-aurora':    { component: HeroAurora,    displayName: 'Hero (Aurora)',   category: 'Hero' },
  'feature-bento':  { component: FeatureBento,  displayName: 'Feature Bento',   category: 'Features' },
  // …
};

export const getSection = (id) => SECTION_REGISTRY[id] || null;
export const listSections = () =>
  Object.entries(SECTION_REGISTRY).map(([id, s]) => ({ id, displayName: s.displayName, category: s.category }));
```

## Editable-schema shape

```js
// editableSchemas.js — drives both the form UI and the AI prompt
export const EDITABLE_PROPS = {
  'hero-aurora': [
    { key: 'eyebrow',  label: 'Eyebrow' },
    { key: 'headline', label: 'Headline', type: 'textarea' },
    { key: 'ctaLabel', label: 'CTA label' },
    { key: 'align',    label: 'Align', type: 'select', options: ['left', 'center'] },
  ],
};

export const EDITABLE_ARRAYS = {
  'feature-bento': {
    features: {
      label: 'Features',
      kind: 'object',
      fields: [
        { key: 'title', label: 'Title' },
        { key: 'body',  label: 'Body', type: 'textarea' },
      ],
      defaultItem: () => ({ title: 'New feature', body: 'Description.' }),
      max: 12,
    },
  },
};

export function defaultsFor(sectionId) { /* return sensible defaults for new sections */ }
```

The same module is imported on both server and client — Next.js Pages
Router handles that automatically.

## The /suggest endpoint

```js
// /api/page/suggest.js — single Anthropic call, JSON in / JSON out
const VALID_KINDS = new Set(['patch', 'add', 'remove', 'move', 'replace']);

export default async function handler(req, res) {
  const { sections, brief } = req.body;
  const schema = buildSchemaSummary();     // from EDITABLE_PROPS + EDITABLE_ARRAYS
  const current = buildSectionsSummary(sections);

  const system = `You are a design + copy critic. Output ONLY JSON: { "suggestions": [...] }.
  3-8 diverse suggestions. Every section type must come from the registry below.`;

  const user = `## Brief\n${brief}\n\n## Current\n${current}\n\n## Schema\n${schema}`;

  const result = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 2500,
    system,
    messages: [{ role: 'user', content: user }],
  });

  const text = extractText(result).replace(/^```(?:json)?\s*|\s*```$/g, '');
  const parsed = JSON.parse(text);
  const cleaned = parsed.suggestions
    .filter((s) => s && VALID_KINDS.has(s.kind))
    .slice(0, 12)
    .map((s, i) => ({ id: `s-${Date.now()}-${i}`, ...s }));

  res.json({ ok: true, suggestions: cleaned });
}
```

Always include a **mock-mode fallback** for `process.env.ANTHROPIC_API_KEY`
being unset — return a small fixture of suggestions so the UI is
demonstrable without a real key.

## applySuggestion — the safe mutator

```js
function applySuggestion(sug, setSections) {
  setSections((current) => {
    const list = [...current];
    const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, Math.round(Number(n))));
    switch (sug.kind) {
      case 'patch': {
        const i = clamp(sug.targetIndex, 0, list.length - 1);
        list[i] = { ...list[i], props: { ...(list[i].props || {}), ...(sug.patch || {}) } };
        return list;
      }
      case 'add': {
        if (!sug.section?.sectionId) return current;
        const at = clamp(sug.insertAt, 0, list.length);
        list.splice(at, 0, { id: uid(), sectionId: sug.section.sectionId, props: sug.section.props || {} });
        return list;
      }
      case 'remove': {
        const i = clamp(sug.targetIndex, 0, list.length - 1);
        list.splice(i, 1);
        return list;
      }
      case 'move': {
        const from = clamp(sug.targetIndex, 0, list.length - 1);
        const to = clamp(sug.toIndex, 0, list.length - 1);
        if (from === to) return current;
        const [moved] = list.splice(from, 1);
        list.splice(to, 0, moved);
        return list;
      }
      case 'replace': {
        const i = clamp(sug.targetIndex, 0, list.length - 1);
        if (!sug.section?.sectionId) return current;
        list[i] = { id: list[i].id, sectionId: sug.section.sectionId, props: sug.section.props || {} };
        return list;
      }
      default: return current;
    }
  });
}
```

The `clamp()` is non-negotiable — the model occasionally returns
indices off-by-one. Better to silently nudge into range than crash the
session.

## LivePreview pane (the "literal render control")

This is what closes the loop — the user sees what the page will look
like, not what the schema says. Render the same components the
published route uses, inside a CSS-variable-scoped wrapper.

```jsx
function LivePreview({ sections, themePack, accent }) {
  const themeVars = themeVarsForPack(themePack, accent);
  return (
    <aside style={{ position: 'sticky', top: 24, maxHeight: 'calc(100vh - 48px)', overflow: 'auto' }}>
      <div style={{ ...themeVars, minHeight: 200 }}>
        {sections.map((s, i) => {
          const entry = getSection(s.sectionId);
          if (!entry) return <Missing key={i} id={s.sectionId} />;
          const Comp = entry.component;
          return <Comp key={s.id || i} {...(s.props || {})} />;
        })}
      </div>
    </aside>
  );
}
```

Two-column responsive layout: `grid-template-columns: minmax(0, 900px) minmax(0, 1fr)`
on wide screens, single column ≤1100px. The preview is sticky so it
stays visible while the user scrolls the schema editor.

Add viewport simulation (Desktop / Tablet / Mobile) by wrapping the
preview in a scaled `transform: scale(N)` container with
`transform-origin: top center` — measure container width with a
`ResizeObserver` and compute `N = min(1, containerWidth / targetWidth)`.

## SuggestionCard UI

```jsx
function SuggestionCard({ suggestion, sections, onAccept, onReject }) {
  return (
    <article>
      <header>
        <span className={`pill pill--${suggestion.kind}`}>{suggestion.kind}</span>
        <span>{describeTarget(suggestion, sections)}</span>
      </header>
      <p>{suggestion.reason}</p>
      {(suggestion.kind === 'patch' || suggestion.kind === 'replace') && (
        <details>
          <summary>Preview changes</summary>
          <pre>{JSON.stringify(suggestion.patch || suggestion.section?.props, null, 2)}</pre>
        </details>
      )}
      <button onClick={onAccept}>Accept</button>
      <button onClick={onReject}>Reject</button>
    </article>
  );
}
```

Use distinct colours per kind (patch=yellow, add=teal, remove=red,
move=violet, replace=pink) so users can scan a stack of cards visually
without reading every word.

## Anti-patterns

1. **One mega "edit the page" suggestion** instead of N small ones.
   Hard to accept/reject — the user wants granularity.
2. **No `reason` field.** The user shouldn't have to read the diff to
   decide.
3. **Free-text suggestions** ("change the hero to be more bold").
   The whole point of this skill is structured ops.
4. **Different schemas on server and client.** Single source of truth
   in `editableSchemas.js`. Import from both.
5. **No live preview.** Schema-only feedback isn't "render control" —
   it's a form.
6. **Auto-applying suggestions.** Always wait for accept. Even an
   AI-driven editor needs a human in the loop.

## Extension paths

- **Undo/redo** via a `sections` history stack (every applySuggestion
  pushes to history).
- **Iterative chat-over-page** — same endpoint, but accept the prior
  suggestion stack as context so Claude knows what was already
  rejected.
- **Per-section AI fill** (`/api/page/auto-section`) — a smaller
  endpoint that takes one sectionId + brief and returns just that
  section's props. Lets users say "regenerate this card" without
  invoking the full suggester.
- **Multi-domain** — the same shape works for slide decks (each slide
  is a section), email templates (each block is a section), etc.
  Swap the registry, keep the rest.

## Verify

The deliverable is the running, verified app — not pasted snippets.

- `npm run dev` (or `npm run build`) — the Next.js app compiles and
  serves without errors.
- With `ANTHROPIC_API_KEY` unset, POST to `/suggest` — the mock-mode
  fixture returns `{ ok: true, suggestions: [...] }` with valid kinds.
- Open the builder: the LivePreview renders the seeded sections
  through the registry (no `<Missing>` placeholders).
- Accept one suggestion of each kind and confirm the preview updates;
  Reject one and confirm the schema is untouched. The full
  accept/reject flow must round-trip before the session is done.
