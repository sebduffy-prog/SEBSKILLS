---
name: shadcn-tailwind-v4-stack
category: frontend-and-design
description: >
  Scaffold the dominant 2026 React build stack — Tailwind CSS v4 (CSS-first, zero
  config file) plus shadcn/ui components — the correct, non-broken way. Use when
  starting a new Next.js/Vite app, adding shadcn to an existing repo, running
  `npx shadcn@latest init`/`add`, wiring `@import "tailwindcss"`, `@theme inline`,
  `@custom-variant dark`, oklch tokens, or fixing "unknown at-rule @tailwind",
  missing `cn`, or dark mode not toggling. Grounded on ui.shadcn.com.
when_to_use:
  - Starting a new Next.js (App Router) or Vite + React app that needs Tailwind v4 + shadcn/ui
  - Adding shadcn/ui to an existing React project already on (or migrating to) Tailwind v4
  - Running `npx shadcn@latest init` / `add` and unsure about prompts, components.json, or styles
  - Setting up the CSS-first Tailwind v4 theme (@import, @theme inline, @custom-variant dark, oklch tokens)
  - Migrating a Tailwind v3 + shadcn project (tailwind.config.js, HSL, forwardRef) up to v4
  - Debugging "unknown at-rule @tailwind", missing `@/lib/utils` cn(), or the dark class not applying
when_not_to_use:
  - Designing the overall aesthetic direction / bespoke layout — use frontend-design first, then scaffold here
  - Just adding a light/dark switch to an already-working stack — use theme-toggle
  - Picking or generating a colour palette / theme tokens conceptually — use theme-factory or oklch-color-engine
  - Building a plain HTML/CSS artifact with no React toolchain — use web-artifacts-builder
keywords:
  - shadcn
  - tailwind
  - tailwind-v4
  - shadcn-ui
  - nextjs
  - vite
  - react
  - components.json
  - oklch
  - css-first
  - dark-mode
  - radix
  - design-system
  - scaffold
  - cn-utility
similar_to:
  - theme-factory
  - theme-toggle
  - frontend-design
  - oklch-color-engine
  - design-system
inputs_needed: Node 18+ and a package manager (pnpm/npm/bun); a Next.js App Router or Vite+React project (or permission to scaffold one); network access for the shadcn registry.
produces: A working Tailwind v4 + shadcn/ui project — components.json, CSS-first globals.css with oklch theme tokens + dark variant, lib/utils cn(), and installed components under components/ui.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# shadcn/ui + Tailwind v4 Stack

Set up the 2026-standard React UI stack — **Tailwind CSS v4** (CSS-first, no
`tailwind.config.js`) and **shadcn/ui** (copy-in Radix components you own) —
correctly the first time. Two failure modes dominate: (1) mixing v3 syntax
(`@tailwind base`, HSL vars, `tailwind.config.js`) with a v4 install, and (2) the
dead `shadcn-ui` package. This pins the correct commands and CSS-first theme.

## When to use

New app, or bolting shadcn onto an existing React repo, on Tailwind v4. Still on
v3? Stay on v3 shadcn or migrate first (Recipe C).

## Prerequisites (honest)

- **Node 18.18+** and a package manager (`pnpm` recommended; `npm`/`bun` work).
- CLI is **`shadcn`** via `npx shadcn@latest`. The old **`shadcn-ui` package is
  deprecated** — do not install it.
- Tailwind **v4** ships as `tailwind` + `@tailwindcss/postcss` (Next) or
  `@tailwindcss/vite` (Vite). **No `tailwind.config.js`**, no `tailwindcss init` — config is CSS.
- Next.js has the `@/*` alias by default; **Vite must add it** in both `tsconfig`
  and `vite.config` (Recipe B) or `init` fails. Needs registry access (`ui.shadcn.com/r`).

## Recipe A — New Next.js (App Router) app

Fastest correct path: let `shadcn init` scaffold Next + Tailwind v4 for you.

```bash
# One command: creates a Next.js App Router app pre-wired with Tailwind v4 + shadcn
npx shadcn@latest init

# ...or start from create-next-app, then init inside it:
npx create-next-app@latest my-app   # choose: TypeScript, App Router, Tailwind
cd my-app
npx shadcn@latest init
```

`init` prompts for a **base color** (neutral/gray/zinc/stone/slate) and writes
`components.json`, an updated `app/globals.css` (CSS-first theme), and
`lib/utils.ts` (the `cn()` helper). Default style is **`new-york`** (the old
`default` style is retired). Then add components — you own the source under
`components/ui/`:

```bash
npx shadcn@latest add button card input dialog
npx shadcn@latest add --all          # everything
```

Use one:

```tsx
import { Button } from "@/components/ui/button"

export default function Page() {
  return <Button variant="outline">Click</Button>
}
```

## Recipe B — Vite + React

Vite needs Tailwind's Vite plugin and the `@/` alias wired before `init`.

```bash
npm create vite@latest my-app -- --template react-ts && cd my-app && npm install
npm install tailwindcss @tailwindcss/vite && npm install -D @types/node
```

`src/index.css` — replace the whole file with a single line: `@import "tailwindcss";`

`vite.config.ts` — add the Tailwind plugin and `@` alias:

```ts
import path from "path"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
})
```

`tsconfig.json` **and** `tsconfig.app.json` — add `"baseUrl": "."` and
`"paths": { "@/*": ["./src/*"] }` under `compilerOptions` so the CLI and editor
resolve `@/*`. Then:

```bash
npx shadcn@latest init      # pick a base color; choose Vite when asked
npx shadcn@latest add button
```

## Recipe C — Migrate an existing v3 + shadcn project to v4

Run the official codemod on a clean git branch, then reconcile shadcn:

```bash
npx @tailwindcss/upgrade@latest       # v3 -> v4 codemod
```


- Delete `tailwind.config.{js,ts}` (v4 reads CSS); move any genuinely custom values into `@theme`.
- Replace `@tailwind base; @tailwind components; @tailwind utilities;` with a single `@import "tailwindcss";`.
- Swap the animation dep **`tailwindcss-animate` → `tw-animate-css`** and `@import "tw-animate-css";`.
- Convert colour tokens to **oklch** and expose them via `@theme inline` (see below).
- v4 components drop **`React.forwardRef`** and add **`data-slot`** attributes — re-pull with `npx shadcn@latest add <name> --overwrite`.
- The `toast` component is retired → migrate to **`sonner`**.

## The CSS-first theme (what globals.css must contain)

This is the shape `init` writes and the thing to get right by hand. Tokens are
`oklch()`; `@theme inline` maps them to Tailwind colour utilities; a custom
variant drives dark mode off a `.dark` class.

```css
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));

:root {
  --radius: 0.625rem;
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  --primary-foreground: oklch(0.985 0 0);
  --border: oklch(0.922 0 0);
  --ring: oklch(0.708 0 0);
  /* card, popover, secondary, muted, accent, destructive, input,
     chart-1..5, sidebar-* follow the same shape */
}
.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  --primary: oklch(0.922 0 0);
  --border: oklch(1 0 0 / 10%);
  --ring: oklch(0.556 0 0);
}

@theme inline {                        /* maps tokens -> Tailwind utilities */
  --radius-sm: calc(var(--radius) - 4px);
  --radius-lg: var(--radius);
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-primary: var(--primary);
  --color-border: var(--border);
  --color-ring: var(--ring);          /* map the rest the same way */
}

@layer base {
  * { @apply border-border outline-ring/50; }
  body { @apply bg-background text-foreground; }
}
```

Toggle dark by adding/removing `class="dark"` on `<html>` (or use `theme-toggle`
/ `next-themes` with `attribute="class"`). Full token set init writes: `background,
foreground, card, popover, primary, secondary, muted, accent` (each with a
`-foreground`), plus `destructive, border, input, ring, chart-1..5` and the
`sidebar-*` family.

## components.json (reference)

`init` writes this; it drives where `add` puts files. Key fields:

```jsonc
{
  "style": "new-york",
  "rsc": true,                 // false for Vite (no React Server Components)
  "tailwind": {
    "css": "app/globals.css",  // "src/index.css" for Vite
    "baseColor": "neutral", "cssVariables": true
  },
  "aliases": { "components": "@/components", "utils": "@/lib/utils", "ui": "@/components/ui" }
}
```

## Verify

```bash
npx shadcn@latest --help                       # right CLI (not shadcn-ui / "not found")
ls lib/utils.ts src/lib/utils.ts 2>/dev/null   # cn() helper exists after init
test -f tailwind.config.js && echo "WARN: remove v3 config (v4 is CSS-first)"
grep -q '@import "tailwindcss"' app/globals.css src/index.css 2>/dev/null && echo "v4 import OK"
grep -q '@tailwind base' app/globals.css src/index.css 2>/dev/null && echo "WARN: v3 directives present"
npm run dev                                     # render a page using <Button>
```

Pass = styled `<Button>` renders, `.dark` on `<html>` flips colours, no
"unknown at-rule" console warnings.

## Pitfalls

- **`npm i shadcn-ui`** — wrong/dead package. Never install a package; use
  `npx shadcn@latest`. Components are copied into your repo, not imported from a lib.
- **Mixing v3 and v4** — `@tailwind base/components/utilities` or a
  `tailwind.config.js` alongside `@import "tailwindcss"` silently breaks utilities.
  Pick one era. In v4 the config lives in CSS via `@theme`.
- **Vite alias missing** — `init` errors resolving `@/lib/utils` if `@/*` isn't in
  `tsconfig` paths **and** `vite.config` resolve.alias. Add both.
- **Editor flags `@theme`/`@custom-variant`/`@apply` as "unknown at-rule"** — that's
  the CSS language server, not a build error. Set VS Code `css.lint.unknownAtRules`
  to `ignore` or install the Tailwind IntelliSense extension.
- **Dark mode does nothing** — inert without both the `@custom-variant dark
  (&:is(.dark *))` line *and* a `.dark` class on an ancestor (`<html>`).
- **`tailwindcss-animate` not found** — v4 shadcn uses **`tw-animate-css`**; install
  and `@import` it or accordion/dialog animations won't run.
- **`add` overwriting edits** — it won't clobber an existing file unless you pass
  `--overwrite`; use it deliberately and diff. And `toast` is gone → use `sonner`.
