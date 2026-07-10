---
name: html-email-builder
category: frontend-and-design
description: >-
  Build client-proof HTML email that survives Outlook, Gmail and Apple Mail — pick MJML,
  React Email or Maizzle, get table-based layout with inlined CSS, dark-mode meta, bulletproof
  VML buttons and mso ghost tables. Use when asked for an HTML email, newsletter, transactional
  template, email that "breaks in Outlook", inlined-CSS email, or dark-mode-safe email markup.
when_to_use:
  - Authoring a marketing, newsletter, or transactional HTML email that must render across Outlook/Gmail/Apple Mail
  - An email renders fine in the browser but breaks (blown-out width, missing bg, wrong button) in Outlook
  - You need CSS inlined and a plain-text alternative before handing HTML to an ESP (SendGrid, Postmark, Mailchimp)
  - Adding dark-mode support or bulletproof VML buttons to an existing email template
  - Choosing between MJML, React Email, and Maizzle for an email project
when_not_to_use:
  - Building a normal responsive web page or app UI — use fluid-responsive-system or frontend-design
  - Designing a print or PDF layout — use print-editorial-layout
  - Just picking brand colours / tokens with no email markup — use brand-color-token-system
keywords:
  - html email
  - mjml
  - react email
  - maizzle
  - inline css
  - outlook vml
  - dark mode email
  - bulletproof button
  - transactional email
  - newsletter
  - email client compatibility
  - mso ghost table
  - responsive email
  - preheader
similar_to:
  - fluid-responsive-system
  - brand-color-token-system
  - print-editorial-layout
  - quick-landing
inputs_needed: Content/copy, brand colours + fonts, hero/CTA links and image URLs (absolute https), target clients, and which toolchain (MJML / React Email / Maizzle) or "raw" hand-coded.
produces: A production email .html (table-based, CSS inlined, dark-mode meta, VML Outlook fallbacks) plus a plain-text alternative, ready to paste into an ESP.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# HTML Email Builder

Email clients are stuck ~2003. Gmail strips `<style>` partially, Outlook (Windows) renders with the
**Word** engine (no `float`, no div `background-image`, no `max-width`), Apple Mail is modern. The
winning strategy is always: **table-based layout, CSS inlined onto elements, fixed pixel widths inside
a fluid outer table, and `mso` conditional comments for Outlook.** Don't hand-roll that — use a
compiler. This skill covers the three best and the raw fallbacks every one of them emits.

## When to use

Pick a toolchain up front — it decides everything downstream:

| Tool | Best when | Author in | Outputs |
|------|-----------|-----------|---------|
| **MJML** | Fastest path, marketing emails, no React | `.mjml` semantic tags | inlined responsive HTML |
| **React Email** | You already ship React; want components + previews | `.tsx` components | HTML via `render()` |
| **Maizzle** | Full control, Tailwind utility classes, complex brand systems | HTML + Tailwind | inlined HTML |

All three produce table-based, Outlook-hardened HTML. If you can't add a build step, jump to
**Recipe D (raw)**.

## Prerequisites

- Node 18+ and `npx` (macOS: `python3` unrelated; these are Node tools).
- Absolute `https://` URLs for every image — email clients never resolve relative paths.
- A test inbox. Litmus/Email on Acid are paid; free-ish: send to a Gmail + Outlook.com + Apple Mail
  account, or use `npx maizzle` preview / React Email's dev server.

## Recipe A — MJML (fastest)

```bash
npm install mjml            # local, gives the `mjml` binary via npx
npx mjml email.mjml -o email.html      # compile
npx mjml -w email.mjml                 # watch mode while editing
```

`email.mjml` — MJML auto-inlines CSS and emits ghost tables for Outlook:

```xml
<mjml>
  <mj-head>
    <mj-preview>Your 20% code expires tonight</mj-preview> <!-- inbox preheader -->
    <mj-attributes>
      <mj-all font-family="Helvetica, Arial, sans-serif" />
      <mj-text font-size="16px" color="#222222" line-height="1.5" />
    </mj-attributes>
    <mj-raw>
      <meta name="color-scheme" content="light dark" />
      <meta name="supported-color-schemes" content="light dark" />
    </mj-raw>
  </mj-head>
  <mj-body background-color="#f4f4f4">
    <mj-section background-color="#ffffff" padding="24px">
      <mj-column>
        <mj-image src="https://cdn.example.com/logo.png" width="120px" alt="Brand" />
        <mj-text font-size="22px" font-weight="700">Big news inside</mj-text>
        <mj-text>Hi Sam, here is the thing we promised you.</mj-text>
        <mj-button href="https://example.com/go" background-color="#e6006e" color="#ffffff"
                   border-radius="6px" padding="16px 0">Claim it</mj-button>
      </mj-column>
    </mj-section>
  </mj-body>
</mjml>
```

`mj-button`, `mj-section` and `mj-column` already emit the VML/ghost-table fallbacks — you don't hand-write them. Columns auto-stack on mobile.

## Recipe B — React Email (component-driven)

```bash
npx create-email@latest        # scaffolds a preview app in ./react-email-starter
cd react-email-starter && npm install && npm run dev   # live preview on :3000
```

Author `emails/welcome.tsx` with `@react-email/components`:

```tsx
import { Html, Head, Preview, Body, Container, Section, Text, Button, Img } from '@react-email/components';

export default function Welcome() {
  return (
    <Html>
      <Head />
      <Preview>Your 20% code expires tonight</Preview>
      <Body style={{ backgroundColor: '#f4f4f4', fontFamily: 'Helvetica, Arial, sans-serif' }}>
        <Container style={{ backgroundColor: '#fff', padding: '24px', maxWidth: '600px' }}>
          <Img src="https://cdn.example.com/logo.png" width="120" alt="Brand" />
          <Section>
            <Text style={{ fontSize: '22px', fontWeight: 700 }}>Big news inside</Text>
            <Button href="https://example.com/go"
              style={{ background: '#e6006e', color: '#fff', padding: '16px 24px', borderRadius: '6px' }}>
              Claim it
            </Button>
          </Section>
        </Container>
      </Body>
    </Html>
  );
}
```

Render to a client-ready HTML string (CSS gets inlined) plus a plain-text version:

```ts
import { render } from '@react-email/render';
import Welcome from './emails/welcome';

const html = await render(<Welcome />, { pretty: true });
const text = await render(<Welcome />, { plainText: true });
```

`<Button>` and `<Row>/<Column>` emit mso-safe markup internally. There's also a `<Tailwind>` wrapper if you prefer utility classes — it inlines the resulting styles at render time.

## Recipe C — Maizzle (Tailwind + full control)

```bash
npx create-maizzle           # scaffold; pick the Starter
cd <project> && npm install
npm run dev                  # dev server: live preview, device resize, dark-mode emulation
npm run build                # writes optimized, inlined HTML to build_production/
```

Templates are HTML with Tailwind classes; the build inlines CSS, purges unused rules, and adds
Outlook fixes. Configure per-environment in `config.js` / `config.production.js` (this is where you
toggle `inlineCSS`, `removeUnusedCSS`, and set the base URL for images).

## Recipe D — Raw / hand-coded (no build step)

The bones every compiler emits. Fluid outer table, fixed-width inner, `role="presentation"` so
screen readers skip layout tables:

```html
<!doctype html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta name="supported-color-schemes" content="light dark">
  <!--[if mso]><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch>
  </o:OfficeDocumentSettings></xml><![endif]-->
</head>
<body style="margin:0;padding:0;background:#f4f4f4;">
  <div style="display:none;max-height:0;overflow:hidden;">Your 20% code expires tonight</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
    <!--[if mso]><table role="presentation" width="600" cellpadding="0" cellspacing="0"><tr><td><![endif]-->
    <table role="presentation" width="600" cellpadding="0" cellspacing="0"
           style="width:600px;max-width:600px;background:#ffffff;">
      <tr><td style="padding:24px;font-family:Helvetica,Arial,sans-serif;color:#222;">
        Hi Sam, here is the thing we promised you.
      </td></tr>
    </table>
    <!--[if mso]></td></tr></table><![endif]-->
  </td></tr></table>
</body>
</html>
```

**Bulletproof VML button** (Outlook ignores CSS padding/radius, so draw a real rectangle):

```html
<!--[if mso]>
<v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" href="https://example.com/go"
  style="height:48px;v-text-anchor:middle;width:200px;" arcsize="12%" fillcolor="#e6006e" stroke="f">
  <center style="color:#ffffff;font-family:Helvetica,Arial,sans-serif;font-size:16px;">Claim it</center>
</v:roundrect>
<![endif]-->
<!--[if !mso]><!-- -->
<a href="https://example.com/go" style="background:#e6006e;color:#fff;text-decoration:none;
   padding:14px 28px;border-radius:6px;font-family:Helvetica,Arial,sans-serif;display:inline-block;">Claim it</a>
<!--<![endif]-->
```

**Dark mode.** After the meta tags, target capable clients (Apple Mail, iOS, some Outlook):

```html
<style>
  @media (prefers-color-scheme: dark) {
    .email-bg { background:#111 !important; }
    .email-text { color:#f4f4f4 !important; }
  }
</style>
```

Add matching classes to elements. Gmail rewrites classes to `u+...`, so also pick colours that
survive an auto-inverted light design — never rely on dark CSS alone.

## Verify

- **Compile clean:** `npx mjml email.mjml -o out.html` (A), `npm run build` (C), or the `render()`
  call resolves without throwing (B).
- **CSS is actually inlined:** open the output — visual styles live in `style="..."` on elements,
  not only in a `<style>` block. Run it through https://www.htmlemailcheck.com/ or Mailchimp's
  Inbox Inspector if available.
- **Widths hold in Outlook:** the ghost `<!--[if mso]><table width="600">` wrapper is present.
- **Renders in real clients:** send to Gmail (web + app), Outlook.com/Windows Outlook, Apple Mail.
  Litmus/Email on Acid if you have it.
- **Plain-text part exists** and links resolve — spam filters penalise HTML-only mail.
- **Images:** all `src` are absolute `https`; every `<img>` has `alt` (many clients block images by
  default, so the email must read with images off).

## Pitfalls

- **Never use `<div>` for layout in Outlook** — no float, no flexbox, no grid. Nest tables.
- **`max-width` is ignored by Outlook.** Set a real `width="600"` on the inner table *and* wrap it in
  the mso ghost table; use `max-width` only for the non-Outlook path.
- **No `background-image` on divs in Outlook** — use VML `<v:rect>`/`<v:fill>` or a solid bg colour.
- **Padding on `<p>`, `<a>`, images is unreliable** — put padding on the enclosing `<td>` instead.
- **Web fonts fall back everywhere** (Outlook, Gmail app). Always declare a real system fallback
  stack; don't ship text as an image to force a font — it kills accessibility and dark mode.
- **Gmail clips messages > ~102 KB**, hiding the unsubscribe footer. Keep HTML lean; Maizzle's purge
  and MJML's minify help.
- **Dark-mode auto-inversion** (Gmail/Outlook) can recolour logos and text unpredictably — test with
  dark mode on, and give transparent PNG logos a subtle background plate if they vanish.
- **Preheader text** must be the first hidden node in `<body>` (follow it with `&zwnj;&nbsp;` runs to
  stop body copy leaking in), or the inbox preview shows random alt text / "View in browser".
- **Don't inline by hand** — a mistyped `style` on one of 40 nested tds is unfindable. Let the tool inline.
