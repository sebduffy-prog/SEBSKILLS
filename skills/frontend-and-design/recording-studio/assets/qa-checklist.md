# Recording Studio — functional QA checklist

Run this against a freshly generated (or re-configured) artist studio **before** `design-approval-gate`.
It checks that the build is **structurally correct** — nothing here judges whether the audience
segmentation, ideas, strategy prose, or imagery are *good*. Content and creative quality are the
human's call at `design-approval-gate`; this checklist exists so that call isn't wasted on a build
that's actually broken underneath.

Automate the mechanical items with `../scripts/qa-smoke.mjs` (run it, then work the rest by hand).

```
node skills/frontend-and-design/recording-studio/assets/scripts/qa-smoke.mjs \
  --old-artist "Muse" --artist "<New Artist>" --password "<new password>"
```

## 1. Build & boot

- [ ] `npm install` completes clean (no peer-dep errors that weren't already present in the template)
- [ ] `npm run build` exits 0
- [ ] `npm run build` succeeds with the **empty** `Market Research/` awaiting-data state too (every
      `getStaticProps` try/catch degrades to `[]`, nothing throws)
- [ ] `npm start` boots and `/` returns 200

## 2. Identity wiring (not leaked from the template)

- [ ] Header wordmark shows the new artist's name/logo, not the base template's
- [ ] Login gate accepts the **new** password; the template default no longer works
- [ ] No leftover template-artist string (e.g. `"Muse"`, `"Madonna"`) survives outside
      `Market Research/`, `public/`, and the config file itself — a leaked string here is a direct
      repeat of the exact bug class `The-Recording-Studio`'s data-integrity pass had to fix (artist
      name hardcoded in ~5 components, leaking into every non-matching build)
- [ ] Agency kicker still reads exactly **"VCCP Media Cultural Intelligence"** everywhere it appears
      (do not touch this — only the artist brand should have changed)

## 3. Audience ↔ CSV coupling (the #1 known bug)

- [ ] Segment key count in config === value-column count in every `gwi_*.csv` in `Market Research/`
- [ ] Column order matches segment order (spot-check one data row per file)
- [ ] Audience tab renders the correct segment under the correct label — no `undefined`, no
      off-by-one shift

## 4. Tabs per depth level

- [ ] Every tab in the chosen depth level (Lite / Standard / Full) renders without throwing
- [ ] Every tab **not** in the depth level is absent from the nav, not just visually hidden
- [ ] Awaiting-data tabs show a visible "awaiting data" state, not a blank/broken panel

## 5. Data sources degrade gracefully

For each configured source (Spotify, Last.fm, Brand24, Reddit, YouTube, GDELT, Wikipedia, Google
Trends, …):

- [ ] Missing env var/ID → the route returns an empty/awaiting-data shape, not a 500
- [ ] Any synthetic/placeholder numbers shown are visibly flagged as such, never presented as live
      data (same principle as the `demo: true` badge pattern used elsewhere for exactly this failure
      mode)
- [ ] A source with no ID configured does **not** silently fall back to the previous artist's
      hardcoded ID (Spotify ID, Last.fm name, YouTube channel, etc.)

## 6. Social listening adapter

- [ ] `socialListening.provider` in config resolves to the intended adapter (or the uploaded-data
      fallback) — not silently hardwired to Brand24 regardless of what's configured

## 7. Deploy readiness

- [ ] No secrets committed (`.env*`, config) — grep for anything that looks like a live API key
- [ ] `vercel.json` present and valid
- [ ] Env vars for this artist are set in Vercel, not local-only

## Out of scope (do not block on these here)

Audience segment choices, SOAP/POAP/strategy content, ideas-board seeds, image/creative asset
quality, colour and brand taste. Those are judged by the human at `design-approval-gate`, not by
this checklist.
