---
name: browser-qa
description: Use this skill to automate visual testing and UI interaction verification using browser automation after deploying features.
origin: ECC
category: frontend-and-design
when_to_use:
  - Automating visual testing after deploying a feature
  - Running a smoke test against a deployed URL
  - Verifying UI interactions and checking for visual regression
  - A quick accessibility pass with a ship/fix verdict
  - Producing a structured QA report before sign-off
when_not_to_use:
  - Interactive build-time screenshot/click loop — use agent-browser
  - Deep DevTools DOM/network/performance inspection — use browser-testing-with-devtools
  - Scripting Playwright tests for a local app — use webapp-testing
keywords:
  - browser qa
  - visual testing
  - smoke test
  - interaction test
  - visual regression
  - accessibility
  - automated testing
  - qa report
  - post-deploy
  - ui verification
  - verdict
similar_to:
  - agent-browser
  - browser-testing-with-devtools
  - webapp-testing
  - design-approval-gate
inputs_needed: The deployed URL to test and the key flows or interactions to verify.
produces: A structured QA report (smoke, interactions, visual, accessibility) with a ship/fix verdict.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Browser QA — Automated Visual Testing & Interaction

## When to Use

- After deploying a feature to staging/preview
- When you need to verify UI behavior across pages
- Before shipping — confirm layouts, forms, interactions actually work
- When reviewing PRs that touch frontend code
- Accessibility audits and responsive testing

## How It Works

Uses the browser automation MCP (claude-in-chrome, Playwright, or Puppeteer) to interact with live pages like a real user.

### Phase 1: Smoke Test
```
1. Navigate to target URL
2. Check for console errors (filter noise: analytics, third-party)
3. Verify no 4xx/5xx in network requests
4. Screenshot above-the-fold on desktop + mobile viewport
5. Check Core Web Vitals: LCP < 2.5s, CLS < 0.1, INP < 200ms
```

### Phase 2: Interaction Test
```
1. Click every nav link — verify no dead links
2. Submit forms with valid data — verify success state
3. Submit forms with invalid data — verify error state
4. Test auth flow: login → protected page → logout
5. Test critical user journeys (checkout, onboarding, search)
```

### Phase 3: Visual Regression
```
1. Screenshot key pages at 3 breakpoints (375px, 768px, 1440px)
2. Compare against baseline screenshots (if stored)
3. Flag layout shifts > 5px, missing elements, overflow
4. Check dark mode if applicable
```

### Phase 4: Accessibility
```
1. Run axe-core or equivalent on each page
2. Flag WCAG AA violations (contrast, labels, focus order)
3. Verify keyboard navigation works end-to-end
4. Check screen reader landmarks
```

## Output Format

```markdown
## QA Report — [URL] — [timestamp]

### Smoke Test
- Console errors: 0 critical, 2 warnings (analytics noise)
- Network: all 200/304, no failures
- Core Web Vitals: LCP 1.2s ✓, CLS 0.02 ✓, INP 89ms ✓

### Interactions
- [✓] Nav links: 12/12 working
- [✗] Contact form: missing error state for invalid email
- [✓] Auth flow: login/logout working

### Visual
- [✗] Hero section overflows on 375px viewport
- [✓] Dark mode: all pages consistent

### Accessibility
- 2 AA violations: missing alt text on hero image, low contrast on footer links

### Verdict: SHIP WITH FIXES (2 issues, 0 blockers)
```

## Integration

Works with any browser MCP:
- `mChild__claude-in-chrome__*` tools (preferred — uses your actual Chrome)
- Playwright via `mcp__browserbase__*`
- Direct Puppeteer scripts

Pair with `/canary-watch` for post-deploy monitoring.
