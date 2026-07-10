---
name: quick-form
category: frontend-and-design
description: >-
  Ship a production-quality contact / signup / feedback form as ONE self-contained HTML file —
  semantic fields, real-time inline validation, and genuine loading / success / error states,
  posting to Formspree, a webhook, or the console. Reach for this when someone asks for a "contact
  form", "signup form", "waitlist", "feedback form", "quick form", "form that actually validates",
  or a form that submits without a backend. Opinionated defaults, accessible by default, no build step.
when_to_use:
  - You need a working contact / signup / waitlist / feedback form fast, with no backend to stand up
  - A form needs real inline validation plus honest loading, success and error states (not just an alert)
  - You want to POST to Formspree or an arbitrary webhook from a static page with zero framework
  - Prototyping a form for a landing page / microsite where server code is overkill
  - An existing form silently fails, lacks accessible errors, or has no submit/loading feedback
when_not_to_use:
  - You need server-side validation, auth, a database, or file storage — build a real backend, not this
  - The form is one field inside a larger app already using React Hook Form / Formik — use that library
  - You just need the field's floating-label motion — use the floating-label-input skill
  - Building an HTML EMAIL with a form-like layout — use html-email-builder (email clients block JS/forms)
keywords:
  - form
  - contact form
  - signup form
  - waitlist
  - inline validation
  - formspree
  - webhook
  - form validation
  - accessible form
  - loading state
  - error state
  - html form
  - constraint validation
  - fetch submit
similar_to:
  - quick-landing
  - quick-microsite
  - quick-tool
  - floating-label-input
  - html-email-builder
inputs_needed: >-
  Fields wanted (name/email/message default); submit target (Formspree form ID like `xyzabcd`,
  a webhook URL, or "console" for demo); optional accent colour and product name.
produces: >-
  One self-contained `form.html` (inline CSS + JS, light+dark theme) with validated fields and
  live loading/success/error states, ready to open in a browser or drop into any page.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Quick Form

Build one honest, accessible form in a single HTML file. No framework, no build, no backend.
Native constraint validation for the cheap wins, a thin JS layer for inline messages and submit
states, and a `fetch` that talks to Formspree, any webhook, or the console for demos.

## When to use

A form that needs to WORK today — validate as the user types, show a spinner while sending, and
tell the truth on success and failure — without standing up a server. If you need server-side
validation, auth, or storage, stop and build a backend instead.

## Prerequisites

- A browser. That's the whole toolchain.
- A submit target, one of:
  - **Formspree** — free tier, no code backend. Create a form at formspree.io, copy its ID
    (the `xxxxxxxx` in `https://formspree.io/f/xxxxxxxx`). First real submission triggers a
    confirmation email you must click once.
  - **Webhook** — any endpoint accepting `POST` JSON (Make, n8n, Zapier, your own function).
  - **`console`** — logs the payload; use while designing, swap later.

## Opinionated defaults (don't reinvent these)

- ONE file — split only when routing or shared state appears, which a form never has.
- ONE light+dark theme via `prefers-color-scheme`, ONE spacing scale, ONE accent (`--accent`).
- Native validation first (`required`, `type="email"`, `minlength`, `pattern`) — the browser is a free, correct validator; JS only adds inline messaging and submit orchestration.
- AT MOST ONE ui-effect: the button focus/spinner transition. No parallax, no confetti.
- A honeypot field (`_gotcha`) catches bots invisibly; Formspree honours it.

## Quality floor (non-negotiable, even fast)

- Semantic `<form>`, every input has a bound `<label for>`, one `<button type="submit">`.
- `aria-describedby` links each field to its error node (`role="alert"`); `aria-invalid` toggles on failure; `:focus-visible` ring on every control.
- Real states: idle → **inline validation** → **loading** (button disabled + spinner) → **success** (form replaced) OR **error** (banner + fields re-enabled + focus moved).
- WCAG-AA contrast in both themes; error is never colour-alone (text + `aria-invalid` + `role="alert"`).
- Keyboard-complete: natural tab order, Enter submits, success/error announced to screen readers.

## Recipe

1. Copy the starter below to `form.html`.
2. Set the submit target at the top of the `<script>`: `const TARGET = { mode: "console" }`.
   For Formspree: `{ mode: "formspree", id: "xxxxxxxx" }`. For a webhook: `{ mode: "webhook", url: "https://…" }`.
3. Add/remove fields — copy a `.field` block, keep the `<label>`, error `<span>` and `aria-describedby` wiring.
4. Set `--accent` and the heading text. Open in a browser and test the flow.
5. **Awaiting data:** no submit target yet? Leave `mode: "console"` and add a visible note
   `<!-- TODO: swap console → formspree id -->`. Ship the working form now; wire the target later.
6. End on the **design-approval-gate**: screenshot idle + error + success, get explicit sign-off before "done".

### Starter (`form.html`)

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Get in touch</title>
<style>
  :root {
    --accent: #4f46e5; --bg: #ffffff; --fg: #18181b; --muted: #71717a;
    --line: #d4d4d8; --field: #ffffff; --err: #b91c1c; --ok: #15803d;
    --radius: 10px; --gap: 1rem; --maxw: 30rem;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #0b0b0f; --fg: #f4f4f5; --muted: #a1a1aa; --line: #3f3f46;
      --field: #18181b; --err: #f87171; --ok: #4ade80;
    }
  }
  * { box-sizing: border-box; }
  body { margin: 0; min-height: 100dvh; display: grid; place-items: center; padding: 2rem 1rem;
    background: var(--bg); color: var(--fg); font: 16px/1.5 system-ui, -apple-system, sans-serif; }
  .card { width: 100%; max-width: var(--maxw); }
  h1 { font-size: 1.4rem; margin: 0 0 .25rem; }
  .sub { color: var(--muted); margin: 0 0 1.5rem; }
  form { display: grid; gap: var(--gap); }
  .field { display: grid; gap: .35rem; }
  label { font-weight: 600; font-size: .9rem; }
  input, textarea { font: inherit; color: var(--fg); background: var(--field);
    border: 1px solid var(--line); border-radius: var(--radius); padding: .6rem .7rem;
    transition: border-color .15s, box-shadow .15s; }
  textarea { resize: vertical; min-height: 6rem; }
  input:focus-visible, textarea:focus-visible, button:focus-visible {
    outline: none; border-color: var(--accent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 35%, transparent); }
  [aria-invalid="true"] { border-color: var(--err); }
  .error { color: var(--err); font-size: .82rem; min-height: 1em; }
  .hp { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }
  button { font: inherit; font-weight: 600; color: #fff; background: var(--accent);
    border: 0; border-radius: var(--radius); padding: .7rem 1rem; cursor: pointer;
    display: inline-flex; align-items: center; justify-content: center; gap: .5rem; transition: filter .15s; }
  button:hover:not(:disabled) { filter: brightness(1.08); }
  button:disabled { opacity: .6; cursor: progress; }
  .spinner { width: 1em; height: 1em; border: 2px solid rgba(255,255,255,.4);
    border-top-color: #fff; border-radius: 50%; animation: spin .7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) { .spinner { animation-duration: 2s; } }
  .banner.err { padding: .7rem .8rem; border-radius: var(--radius); font-size: .9rem;
    background: color-mix(in srgb, var(--err) 15%, transparent); color: var(--err); }
  .done { text-align: center; padding: 1.5rem 0; }
  .done h2 { color: var(--ok); margin: 0 0 .5rem; }
</style>
</head>
<body>
<main class="card">
  <h1>Get in touch</h1>
  <p class="sub">We usually reply within a day.</p>

  <div id="banner" hidden></div>

  <form id="form" novalidate>
    <!-- honeypot: hidden from humans, catches bots -->
    <input class="hp" type="text" name="_gotcha" tabindex="-1" autocomplete="off" aria-hidden="true">

    <div class="field">
      <label for="name">Name</label>
      <input id="name" name="name" type="text" required minlength="2"
             autocomplete="name" aria-describedby="name-err">
      <span class="error" id="name-err" role="alert"></span>
    </div>

    <div class="field">
      <label for="email">Email</label>
      <input id="email" name="email" type="email" required
             autocomplete="email" aria-describedby="email-err">
      <span class="error" id="email-err" role="alert"></span>
    </div>

    <div class="field">
      <label for="message">Message</label>
      <textarea id="message" name="message" required minlength="10"
                aria-describedby="message-err"></textarea>
      <span class="error" id="message-err" role="alert"></span>
    </div>

    <button type="submit" id="submit">Send message</button>
  </form>
</main>

<script>
  // ── Configure your submit target ────────────────────────────────
  const TARGET = { mode: "console" }; // demo: logs payload, always succeeds
  // const TARGET = { mode: "formspree", id: "xxxxxxxx" };
  // const TARGET = { mode: "webhook", url: "https://example.com/hook" };
  // ────────────────────────────────────────────────────────────────

  const form = document.getElementById("form");
  const btn = document.getElementById("submit");
  const banner = document.getElementById("banner");

  // Friendly per-field messages from the native ValidityState.
  const messageFor = (input) => {
    const v = input.validity;
    if (v.valueMissing) return "This field is required.";
    if (v.typeMismatch) return "Enter a valid email address.";
    if (v.tooShort) return `Please use at least ${input.minLength} characters.`;
    if (v.patternMismatch) return "Please match the requested format.";
    return "Please check this field.";
  };

  const showError = (input, msg) => {
    input.setAttribute("aria-invalid", "true");
    document.getElementById(input.getAttribute("aria-describedby")).textContent = msg;
  };
  const clearError = (input) => {
    input.removeAttribute("aria-invalid");
    document.getElementById(input.getAttribute("aria-describedby")).textContent = "";
  };
  const fields = () => [...form.querySelectorAll("input:not(.hp), textarea")];

  // Inline validation: validate on blur, and re-validate as you fix a flagged field.
  fields().forEach((input) => {
    input.addEventListener("blur", () =>
      input.checkValidity() ? clearError(input) : showError(input, messageFor(input)));
    input.addEventListener("input", () => {
      if (input.getAttribute("aria-invalid") === "true" && input.checkValidity()) clearError(input);
    });
  });

  const setLoading = (on) => {
    btn.disabled = on;
    btn.innerHTML = on ? '<span class="spinner"></span> Sending…' : "Send message";
  };
  const showBanner = (msg) => {
    banner.className = "banner err"; banner.textContent = msg; banner.hidden = false;
  };

  async function send(data) {
    if (TARGET.mode === "console") {
      console.log("Form payload:", Object.fromEntries(data));
      await new Promise((r) => setTimeout(r, 600)); // simulate latency
      return;
    }
    const url = TARGET.mode === "formspree"
      ? `https://formspree.io/f/${TARGET.id}` : TARGET.url;
    const res = await fetch(url, {
      method: "POST",
      headers: { Accept: "application/json" }, // Formspree needs this for a JSON (not redirect) reply
      body: data, // FormData → multipart; Formspree & most webhooks accept it
    });
    if (!res.ok) {
      // Formspree returns { errors: [{ field, message }] } on 4xx
      const body = await res.json().catch(() => ({}));
      throw new Error(body.errors?.map((e) => e.message).join(", ") || `Request failed (${res.status})`);
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    banner.hidden = true;

    // Full validation pass; focus the first bad field.
    const bad = fields().filter((f) => !f.checkValidity());
    if (bad.length) {
      bad.forEach((f) => showError(f, messageFor(f)));
      bad[0].focus();
      return;
    }

    setLoading(true);
    try {
      await send(new FormData(form));
      form.innerHTML =
        '<div class="done"><h2>Thanks — message sent</h2>' +
        '<p class="sub">We\'ll be in touch shortly.</p></div>';
    } catch (err) {
      setLoading(false);
      showBanner(`Couldn't send: ${err.message} Please try again.`);
      btn.focus();
    }
  });
</script>
</body>
</html>
```

## Verify

- **Empty submit** → each field shows an inline `role="alert"` message; focus lands on the first bad one.
- **Bad email** ("`a@`") → "Enter a valid email address."; fixing it live clears the error on input.
- **Valid submit (console mode)** → spinner ~0.6s, then form replaced by the success panel; payload logged in DevTools.
- **Error path** → point at `{ mode: "webhook", url: "https://httpstat.us/500" }`; a red banner shows, fields re-enable, focus returns to the button.
- **Keyboard + dark mode** → Tab through all controls (Enter submits, `:focus-visible` ring on each); toggle OS theme and confirm contrast holds.

## Pitfalls

- **Formspree needs `Accept: application/json`.** Without it Formspree replies with an HTML redirect page, not JSON, and your success/error branching breaks. The starter sets it.
- **First Formspree submit needs confirmation.** The first POST to a new form emails you a "confirm this form" link; earlier submissions are held. Test with a real inbox.
- **`novalidate` is intentional.** It suppresses native bubble tooltips so YOUR accessible inline messages are the single source of truth. `checkValidity()` still works.
- **Honeypot: hidden but focus-skipped.** Off-screen + `tabindex="-1"` + `aria-hidden`, never `display:none` (bots detect it) and never `required`.
- **FormData vs JSON.** FormData (multipart) works for Formspree and most webhooks. If your webhook demands JSON, send `JSON.stringify(Object.fromEntries(data))` with `"Content-Type": "application/json"`.
- **Don't trust the client.** This validates for UX only — any receiving endpoint must re-validate server-side.
