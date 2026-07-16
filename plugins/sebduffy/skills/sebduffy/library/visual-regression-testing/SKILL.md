---
name: visual-regression-testing
category: frontend-and-design
description: >
  Set up pixel-diff screenshot baseline testing so UI changes are caught by comparing rendered
  screenshots against approved baselines. Use when asked for "visual regression", "screenshot
  diffing", "pixel diff", "did the layout change", "toHaveScreenshot", "BackstopJS", "reg-suit",
  "snapshot testing the UI", or catching unintended CSS/layout drift in CI. Ships an anti-flake
  playbook (disable animations, mask dynamic content, pin fonts/viewport) so diffs are real, not
  noise. NOT for asserting behaviour/clicks — that is browser-qa.
when_to_use:
  - Locking a component or page's appearance so future commits can't silently change it
  - Catching CSS/layout/theme regressions across a design-token or refactor change
  - Reviewing a PR that touches styling and you want a visual diff, not just code diff
  - Wiring screenshot baselines into CI with a stable, non-flaky diff signal
  - Multi-viewport / multi-browser appearance coverage (mobile + desktop, Chromium + WebKit)
  - Choosing between Playwright's built-in comparison, BackstopJS, or reg-suit
when_not_to_use:
  - Asserting clicks, form submits, navigation, or DOM state — use browser-qa or webapp-testing
  - Driving a live browser session interactively — use claude-in-chrome or agent-browser
  - Checking colour contrast / a11y specifically — use accessible-contrast-checker
  - Unit-testing component logic without rendering pixels — use test-driven-development
keywords:
  - visual regression
  - screenshot testing
  - pixel diff
  - tohavescreenshot
  - playwright
  - backstopjs
  - reg-suit
  - baseline
  - snapshot
  - anti-flake
  - pixelmatch
  - ci
  - percy
  - image diff
  - deterministic rendering
similar_to:
  - browser-qa
  - webapp-testing
  - browser-testing-with-devtools
  - design-approval-gate
  - accessible-contrast-checker
inputs_needed: A running app or static HTML (dev-server URL or file), Node.js 18+, and a stable environment (ideally the same OS/container in local + CI so font rendering matches).
produces: A committed baseline-screenshot set, a test suite that diffs against it, per-diff PNG artifacts (expected/actual/diff), and a CI gate that fails on unapproved visual change.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Visual Regression Testing

Catch UI changes by comparing freshly-rendered screenshots against approved **baselines** (aka golden/reference images). A pixel diff engine (pixelmatch / ImageMagick) reports whether the rendered pixels drifted. If the change is intended, you re-approve the baseline; if not, the test fails.

The hard part is not the diff — it's **flake**. Animations, blinking carets, web-font load races, sub-pixel anti-aliasing, and OS-level font rendering make identical code produce different pixels. Most of this skill is the anti-flake playbook.

## When to use

Use when you need to *freeze appearance*. If the assertion is "the button still looks like this", this is the skill. If the assertion is "clicking the button opens the modal", that is behaviour — use **browser-qa** instead.

## Prerequisites

- **Node.js 18+** and npm/pnpm.
- The default and recommended engine is **Playwright's built-in visual comparison** (`@playwright/test`) — no extra service, diffs stored in-repo, uses `pixelmatch`.
- **BackstopJS** is a good standalone alternative (config-driven, no test code, HTML diff report). Needs Chrome/Chromium.
- **reg-suit** is for teams that want cloud-hosted baselines (S3/GCS) + PR comments; it only *compares* images — you generate the screenshots yourself (e.g. with Playwright/Storycap).
- **Determinism is a hard dependency.** Font rendering differs across macOS / Linux / Windows, so a baseline captured on your Mac will diff against CI's Linux. Either capture baselines *inside the same container CI uses*, or accept a per-OS baseline set. Playwright supports this via `--update-snapshots` run in the CI image (e.g. `mcr.microsoft.com/playwright`).

## Recipe A — Playwright built-in (recommended)

### 1. Install

```bash
npm init -y
npm install -D @playwright/test
npx playwright install --with-deps chromium
```

### 2. Config with anti-flake defaults — `playwright.config.ts`

```ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  // Stops OS-name leaking into the filename so CI (linux) and local can share a name;
  // include {projectName} if you DO want per-browser baselines.
  snapshotPathTemplate: '{testDir}/__screenshots__/{testFilePath}/{arg}{ext}',
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.01, // tolerate <1% of pixels differing (anti-aliasing noise)
      threshold: 0.2,          // per-pixel YIQ colour delta before a pixel "counts" (0–1)
      animations: 'disabled',  // freezes CSS animations/transitions at their end state
      caret: 'hide',           // hides the blinking text caret
    },
  },
  use: { ...devices['Desktop Chrome'], deviceScaleFactor: 1 },
});
```

### 3. A test — `tests/home.spec.ts`

```ts
import { test, expect } from '@playwright/test';

test('homepage hero matches baseline', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await page.evaluate(() => document.fonts.ready); // wait for web fonts
  await expect(page).toHaveScreenshot('hero.png', {
    fullPage: true,
    mask: [page.locator('[data-dynamic]'), page.locator('time')], // black out volatile bits
  });
});
```

### 4. Create baselines, then run

```bash
# First run has no baseline → generate them (review the PNGs before committing!)
npx playwright test --update-snapshots

git add tests/__screenshots__ && git commit -m "test: add visual baselines"

# Subsequent runs compare; a real change fails and writes expected/actual/diff PNGs
npx playwright test
npx playwright show-report   # opens the HTML report with side-by-side diffs
```

Update modes (Playwright 1.51+): `--update-snapshots=missing` (only new, safe default in CI), `=changed` (update only failing), `=all`, `=none`. Add `--update-source-method=3way` for a git-mergeable review. Re-approve an intended change with `npx playwright test --update-snapshots=changed`.

## Recipe B — BackstopJS (no test code)

```bash
npx backstopjs init          # writes backstop.json + example scenarios
# edit backstop.json: set scenarios[].url, viewports, misMatchThreshold, delay/selectors
npx backstopjs test          # renders + diffs; auto-opens an HTML report
npx backstopjs approve       # promote the current run to the new baseline
```

Key `backstop.json` anti-flake knobs: `"misMatchThreshold": 0.1`, `"delay": 500`, per-scenario `"hideSelectors"` / `"removeSelectors"`, and a global `onReadyScript` to pause animations. `"viewports"` gives you responsive coverage in one config.

## Recipe C — reg-suit (cloud baselines + PR comments)

reg-suit does **not** take screenshots — feed it a directory you already produced (Playwright, Storycap, etc.).

```bash
npx reg-suit init   # prompts for plugins: reg-keygen-git-hash-plugin,
                    # reg-notify-github-plugin, reg-publish-s3-plugin
npx reg-suit run    # keygen finds the base commit's baseline, compares, publishes, comments on the PR
```

It uses git history to pick the correct baseline commit, so it fits PR workflows where baselines live in cloud storage rather than the repo.

## The anti-flake playbook (the actual point)

Apply these before trusting *any* diff engine:

1. **Kill animations** — Playwright `animations: 'disabled'`; elsewhere inject `* { animation: none !important; transition: none !important; }`.
2. **Hide the caret & focus rings** on captured inputs (`caret: 'hide'`).
3. **Wait for fonts** — `await page.evaluate(() => document.fonts.ready)`; a FOUT changes pixels. Prefer bundling/`woff2` self-hosted fonts over a CDN race.
4. **Mask volatile content** — timestamps, avatars, ad slots, random IDs, "live" counters. Use `mask:` / `hideSelectors` rather than widening the threshold.
5. **Pin the viewport & `deviceScaleFactor: 1`** — retina (2x) baselines diff against 1x CI.
6. **Freeze non-determinism** — stub `Date`/`Math.random`, seed data, mock network so the same content renders every time.
7. **Match the render environment** — same OS/container for baseline and CI. This single factor causes more false diffs than everything else combined. Use the official `mcr.microsoft.com/playwright` image or Docker for BackstopJS.
8. **Use ratio not raw pixels** — prefer `maxDiffPixelRatio` (scales with element size) over a fixed `maxDiffPixels`; keep `threshold` low (~0.2) so real changes still surface.
9. **Never commit a baseline you didn't eyeball** — a regression baked into the baseline silences the test forever.

## Verify

- Run twice with no code change → **passes both times** (proves it isn't flaky). If run 2 fails, fix flake before adding more tests.
- Introduce a deliberate 1px change (e.g. tweak a padding) → the test **fails** and the diff PNG highlights exactly that region.
- Revert the change → passes again.
- In CI, confirm the baseline directory is committed and that a styling PR produces a red check with downloadable diff artifacts.

## Pitfalls

- **OS font-rendering mismatch** — the #1 cause of "passes locally, fails in CI". Capture baselines in the CI container.
- **Threshold too loose** — a high `maxDiffPixelRatio`/`misMatchThreshold` hides real regressions; tune down until only true noise passes.
- **Baseline captured with a bug in it** — the test now enforces the bug. Always review baselines on creation and on every re-approval.
- **Full-page screenshots of lazy/async content** — scroll-triggered images or skeleton loaders race the capture; wait for network-idle and `document.fonts.ready`, or screenshot a stable region.
- **Using this to test behaviour** — a green pixel diff says nothing about whether the button *works*. Pair with browser-qa / webapp-testing.
- **Baselines bloating the repo** — hundreds of full-page PNGs add up; prefer targeted component screenshots, or move to reg-suit's cloud storage.
- **reg-suit without a screenshot step** — it compares only; you still need Playwright/Storycap to produce the images.
