---
name: theme-toggle
description: Animated sun/moon theme toggle button for React — smoothly morphs between a sunburst and a crescent moon, persists the choice to localStorage, and sets a data-attribute on <html> so CSS can read the theme. Use when the user asks for a "theme toggle", "dark mode toggle", "light/dark switch", "sun moon button", "theme switcher", or wants a classic top-right light/dark control that respects prefers-color-scheme on first load. Framer category — Utilities.
---

# Theme Toggle

A circular button that cycles between light and dark. The icon morphs: in light mode, a sun with 8 rays; in dark mode, the rays fade and a "mask" circle slides in to carve the sun into a crescent moon. Pure SVG + CSS transitions.

## When to use

- Any app where users expect a dark-mode control
- Portfolios where the toggle itself should feel polished
- Works with any theming system that reads a `data-theme` attribute (next-themes patterns, CSS custom properties, Tailwind's `darkMode: ['class', '[data-theme="dark"]']`)

## What to produce

`assets/ThemeToggle.tsx`.

```tsx
import ThemeToggle from "@/components/ThemeToggle";

// In your nav
<ThemeToggle />

// Change the attribute/target if your setup is different
<ThemeToggle target="body" attribute="class" lightValue="theme-light" darkValue="theme-dark" />
```

Then in CSS:
```css
:root { --bg: white; --fg: black; }
[data-theme="dark"] { --bg: #0b0b0b; --fg: white; }
body { background: var(--bg); color: var(--fg); }
```

## Props

| Prop | Type | Default | Notes |
|---|---|---|---|
| `size` | number | `40` | Button diameter (px). |
| `storageKey` | string | `"theme"` | localStorage key. |
| `target` | `"html" \| "body"` | `"html"` | Which element gets the theme attribute. |
| `attribute` | string | `"data-theme"` | Attribute name. Set to `"class"` for class-based theming. |
| `lightValue` / `darkValue` | string | `"light"` / `"dark"` | Values written to the attribute. |

## Implementation notes

- **Two-phase mount.** First render is always "light" (SSR-safe); on mount, `getInitial` reads localStorage → falls back to `prefers-color-scheme`. Prevents hydration mismatch in Next.js.
- **Crescent carving trick.** The moon shape is two overlapping `<circle>`s: the main filled circle and a second mask-colored circle offset to the top-right that "bites" out the crescent. In light mode the second circle is yanked far off-viewBox (`cx=30`) so it has no effect.
- **CSS var for mask color.** The mask uses `var(--theme-toggle-bg, white)`. If your button sits on a non-white background, set `style={{ "--theme-toggle-bg": "#0b0b0b" }}` on the component.
- **Rays transition.** 8 short `<line>`s evenly spaced at 45° intervals, each rotated into place. Opacity fades to 0 in dark mode.
- **Accessible label.** `aria-label` flips based on current state so screen readers announce "Switch to dark mode" / "Switch to light mode".

## Caveats

- **Flash of wrong theme.** Because the initial client render waits for `useEffect`, users may briefly see light mode. To prevent this, also inject a tiny blocking script in your `<head>` that applies the attribute before React hydrates:
  ```html
  <script>
    (function () {
      var s = localStorage.getItem("theme");
      var d = s === "dark" || (!s && matchMedia("(prefers-color-scheme: dark)").matches);
      document.documentElement.setAttribute("data-theme", d ? "dark" : "light");
    })();
  </script>
  ```
- **Tailwind `dark:` classes** want `class="dark"` on `<html>` by default. Either set `attribute="class"` + `darkValue="dark"` + `lightValue=""`, or configure Tailwind `darkMode: ['class', '[data-theme="dark"]']`.

## Attribution

Theme toggles are a universal web-app utility. Icon-morph technique (mask-circle carving a crescent) is a classic SVG trick, fully re-implementable without Framer.
