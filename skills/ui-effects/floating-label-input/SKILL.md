---
name: floating-label-input
description: Material/Stripe-style floating label input for React — label sits inside the field at rest, floats up and shrinks when focused or filled, with animated focus ring and error state. Use when the user asks for a "floating label input", "material input", "Stripe-style input", "animated form field", "label that floats", "notched input", or any polished form field beyond a plain `<input>`. Framer category — Forms.
---

# Floating Label Input

Controlled-or-uncontrolled React input where the label lives inside the field until the user focuses or types, at which point it floats up to the border, shrinks, and recolours. Animated focus ring and error state built in. Zero dependencies.

## When to use

- Any production form (login, signup, checkout, contact)
- Anywhere a plain HTML label feels too utilitarian
- Pairs well with Stripe-ish or Linear-ish aesthetics

## What to produce

`assets/FloatingLabelInput.tsx`.

```tsx
import FloatingLabelInput from "@/components/FloatingLabelInput";

<FloatingLabelInput label="Email" type="email" />

// Controlled + error:
<FloatingLabelInput
  label="Password"
  type="password"
  value={pw}
  onChange={setPw}
  error={tooShort ? "Minimum 8 characters" : undefined}
/>

// Custom accent:
<FloatingLabelInput label="Work email" accentColor="#10b981" helper="We never share this." />
```

## Props

| Prop | Type | Default | Notes |
|---|---|---|---|
| `label` | string | — | Required. |
| `value` / `onChange` | string / `(v) => void` | — | Optional, for controlled use. |
| `defaultValue` | string | `""` | For uncontrolled use. |
| `type` | string | `"text"` | Any HTML input type. |
| `error` | string | — | Red state + message below. |
| `helper` | string | — | Sub-label; hidden when `error` is set. |
| `accentColor` | string | `"#6366f1"` | Focus border + ring. |
| `inputProps` | object | — | Passed through to the underlying `<input>` (for `autoComplete`, `name`, `maxLength`, etc.). |

## Implementation notes

- **Label "floated" when** focused OR value has length. Computed with a `floated` flag; don't split into two states.
- **Focus ring** is `box-shadow: 0 0 0 4px accent22` — the `22` is ~13% alpha. No outline ring — that clips at corners.
- **Label background pill.** When floated, the label gets `background: white` + small padding to "punch through" the border stroke. If your container isn't white, pass a container with matching bg or wrap accordingly.
- **Controlled/uncontrolled dual-mode:** checks `value !== undefined`. Same pattern as shadcn/ui.
- **useId** produces a stable SSR-safe id for label/input association.

## Common tweaks

- **Dark mode:** pass `style={{ background: "#0b0b0b" }}` on a wrapper and adjust the label background to match. Or swap `white` → `var(--bg)` and use CSS vars.
- **Textarea variant:** the same skeleton works for `<textarea>` — swap the `<input>` tag. Label position offset may need slight tweak (`top: 18px` at rest instead of `50%`).
- **Inline currency icon:** add `paddingLeft: 32` on the input and an absolute-positioned `$` in the relative wrapper.

## Attribution

Floating-label pattern is public web-design canon (Material 2014, Stripe Checkout since). No Framer code reused.
