---
name: stealth-browser-scraping
category: data-analysis
description: >
  Get past Cloudflare Turnstile, DataDome, Akamai, PerimeterX and Kasada bot walls when plain
  requests/httpx and vanilla headless Chrome/Playwright are 403'd, challenged, or fingerprint-flagged.
  Drive a stealth browser — nodriver (CDP, no webdriver flags), Camoufox (patched Firefox with real
  fingerprint injection) or Patchright (undetected Playwright) — with fingerprint spoofing, residential
  proxies, human-like pacing and persistent cookie sessions. Reach for this the moment a scrape returns
  a challenge page, "Just a moment...", or an empty body instead of the data.
when_to_use:
  - A normal HTTP scrape returns a Cloudflare/DataDome/Akamai challenge, 403, or "Just a moment..." interstitial
  - Vanilla Playwright/Selenium gets flagged (navigator.webdriver, CDP leaks, TLS/JA3 mismatch)
  - You need to hold a logged-in or cookie-cleared session across many page loads without re-triggering the wall
  - The target renders data client-side AND gates the browser behind bot detection
  - You must pass a JS/Turnstile challenge to even reach the HTML
when_not_to_use:
  - The site has no bot wall and returns HTML to plain requests — use resilient-scraper or bulk-content-extraction
  - You just need clean article text from open pages — use firecrawl-scrape or structured-page-extraction
  - You have (or can get) an official API — use free-api-catalogue / the domain API skills instead
  - Crawling a sitemap of static pages at scale — use sitemap-crawl-harvest
  - The content is JS-rendered but UNPROTECTED — plain Playwright is lighter; save stealth for walls
keywords: [cloudflare, datadome, akamai, bot-detection, anti-bot, nodriver, camoufox, patchright, fingerprint, stealth, turnstile, undetected-chromedriver, ja3, residential-proxy, cdp, webdriver, scraping, captcha]
similar_to: [resilient-scraper, firecrawl-scrape, structured-page-extraction, sitemap-crawl-harvest, web-change-monitor, bulk-content-extraction]
inputs_needed: Target URL(s); which wall (Cloudflare / DataDome / Akamai / unknown); whether login/cookies are needed; proxy availability (residential strongly preferred); volume and acceptable pace.
produces: A working stealth scraper that reaches the real HTML/JSON behind the wall, plus saved cookie session for reuse.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Stealth Browser Scraping

When plain `httpx`/`requests` or vanilla headless Chrome hits a bot wall (Cloudflare Turnstile,
DataDome, Akamai Bot Manager, PerimeterX/HUMAN, Kasada), the fix is a browser that does not leak
automation signals: no `navigator.webdriver`, a coherent TLS/JA3 + header + fingerprint story, and
human-like timing. This skill picks the right tool and gives runnable recipes for the three best.

## When to use

Reach for this ONLY after a lighter path fails. Diagnose first (see Step 0). If plain HTTP returns
the data, do not spin up a browser. If it returns a challenge/403/empty body, escalate here.

**Tool picker:**

| Tool | Engine | Best against | Notes |
|------|--------|--------------|-------|
| **nodriver** | Chromium via raw CDP | Cloudflare JS/Turnstile, most Chrome-fingerprint walls | No Selenium/webdriver at all; successor to undetected-chromedriver; async. |
| **Camoufox** | patched Firefox + Playwright | DataDome, canvas/WebGL/font fingerprinting | Injects *real* rotated fingerprints at the C++ level; hardest to detect. |
| **Patchright** | Chrome via patched Playwright | Akamai, sites you already have Playwright code for | Drop-in `playwright` replacement; keep config minimal or it self-defeats. |

## Prerequisites

- Python 3.9+ (this Mac has 3.9). All three are `pip install`, no brew needed.
- **A real Chrome install** for nodriver/Patchright (they drive Google Chrome, not just Chromium).
  Camoufox ships its own patched Firefox binary you fetch once.
- **A residential/mobile proxy** for anything at volume — datacenter IPs are the #1 giveaway and no
  amount of fingerprint spoofing saves a flagged ASN. Have `PROXY_URL` ready (`http://user:pass@host:port`).
- Honest expectation: this is an arms race. These tools work today against the named walls but no
  approach is permanent. Respect robots/ToS and rate limits; prefer an official API when one exists.

## Step 0 — Diagnose the wall (do this first)

```bash
python3 - <<'PY'
import httpx
r = httpx.get("https://TARGET", follow_redirects=True, timeout=20,
              headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"})
print("status", r.status_code)
h = " ".join(f"{k}:{v}" for k,v in r.headers.items()).lower()
body = r.text[:4000].lower()
for name, sig in [("cloudflare","cf-mitigated" in h or "just a moment" in body or "cf-ray" in h),
                  ("datadome","datadome" in h or "datadome" in body),
                  ("akamai","akamai" in h or "_abck" in h or "ak_bmsc" in h),
                  ("perimeterx","_px" in body or "perimeterx" in body)]:
    if sig: print("WALL:", name)
if r.status_code == 200 and not any(s in body for s in ["just a moment","captcha","access denied"]):
    print("NO WALL — use resilient-scraper / plain httpx, not this skill")
PY
```

The detected vendor tells you which recipe to start with (picker table above).

## Recipe A — nodriver (Cloudflare / general Chrome walls)

```bash
pip install nodriver
```

```python
# scrape_nodriver.py  — run: python3 scrape_nodriver.py
import asyncio, nodriver as uc

async def main():
    browser = await uc.start(
        headless=False,                 # headless is a strong tell; keep visible if you can
        lang="en-US",
        browser_args=["--proxy-server=http://HOST:PORT"],  # residential; auth via extension or per-req
    )
    tab = await browser.get("https://TARGET")
    # Cloudflare interstitial resolves itself; just wait it out, don't hammer.
    await tab.sleep(6)
    # Confirm you're through: challenge pages have no real content.
    html = await tab.get_content()
    if "just a moment" in html.lower():
        await tab.sleep(6)
        html = await tab.get_content()

    # Interact like a human: find by text, select by CSS.
    for _ in range(3):
        await tab.scroll_down(400)
        await tab.sleep(0.8)
    rows = await tab.select_all("table tr")
    print("rows:", len(rows), "html bytes:", len(html))

    await browser.save_cookies("cf_cookies.dat")   # reuse the cleared session next run
    await browser.stop()

uc.loop().run_until_complete(main())   # do NOT wrap in asyncio.run — use uc.loop()
```

Reuse the session next run with `await browser.cookies.load("cf_cookies.dat")` (or `browser.load_cookies`)
before `browser.get(...)` so you skip the challenge entirely.

## Recipe B — Camoufox (DataDome / fingerprint walls)

```bash
pip install camoufox[geoip]
python3 -m camoufox fetch          # one-time: downloads the patched Firefox binary
```

```python
# scrape_camoufox.py
from camoufox.sync_api import Camoufox

with Camoufox(
    headless=True,          # Camoufox headless is much safer than Chrome headless
    humanize=True,          # human-curved mouse movement + timing
    os="macos",             # spoof a coherent OS fingerprint (match your proxy's region)
    geoip=True,             # derive locale/timezone/geo from the proxy IP — keeps the story consistent
    block_images=True,      # faster; skip when a wall checks image loads
    proxy={"server": "http://HOST:PORT", "username": "U", "password": "P"},
) as browser:
    page = browser.new_page()
    page.goto("https://TARGET", wait_until="networkidle")
    page.wait_for_timeout(2500)
    print(page.title(), len(page.content()))
    # Standard Playwright API from here:
    for cell in page.query_selector_all("table td"):
        print(cell.inner_text())
    browser.contexts[0].storage_state(path="dd_state.json")   # persist session
```

`geoip=True` is the key move against DataDome: fingerprint OS/locale/timezone must agree with the
proxy exit IP. Mismatched signals (US IP, `os="windows"`, Europe/London timezone) are an instant flag.

## Recipe C — Patchright (Akamai / existing Playwright code)

```bash
pip install patchright
patchright install chrome     # installs Google Chrome, not Chromium
```

```python
# scrape_patchright.py  — only the import changed vs stock Playwright
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir="./pw_profile",   # persistent profile = warm, trusted session
        channel="chrome",               # real Chrome, NOT chromium
        headless=False,
        no_viewport=True,
        proxy={"server": "http://HOST:PORT", "username": "U", "password": "P"},
        # DO NOT set user_agent / extra headers / init scripts — they undo the patches.
    )
    page = ctx.new_page()
    page.goto("https://TARGET", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    print(page.url, len(page.content()))
    ctx.close()
```

Patchright's stealth comes from *removing* Playwright's tells. Adding `add_init_script`, custom
`user_agent`, extra headers, or `--disable-*` flags re-introduces detectable behaviour. Keep it bare.
Note: Patchright disables the CDP console domain, so `page.on("console")` won't fire.

## Cross-cutting tactics (apply to all three)

- **Persist cookies/state** and reuse it — the expensive part is passing the challenge once.
- **Pace like a human:** randomized sleeps (0.5–3s), scroll before reading, one tab at a time.
  Bursts of parallel identical requests are the clearest bot signal after IP reputation.
- **Match the fingerprint story to the IP:** OS, locale, timezone, `Accept-Language` and proxy exit
  region must all agree.
- **Rotate on failure, not on schedule:** back off and swap IP when you get challenged, don't cycle
  every request (that itself looks robotic).
- **Prefer visible (non-headless) for Chrome tools.** For unavoidable headless Chrome use
  `--headless=new`, never the legacy `--headless`.

## Verify

- Success = the real page content is present and NO challenge markers remain:
  `assert "just a moment" not in html.lower() and "captcha" not in html.lower()` and your target
  selectors return rows.
- Sanity-check leakage against the site's own probes: load `https://bot.sannysoft.com` or
  `https://abrahamjuliot.github.io/creepjs/` in the same driver and confirm `navigator.webdriver` is
  `undefined`/false and no obvious red flags.
- If you still get challenged after fingerprint + pacing are correct, the problem is almost always the
  **IP** — switch to residential/mobile before touching anything else.

## Pitfalls

- **Datacenter proxy = game over.** Spoofing can't fix a flagged ASN; this is the top failure cause.
- **Headless Chrome is detectable** even patched. Camoufox headless is fine; Chrome tools prefer visible.
- `uc.start()` needs `uc.loop().run_until_complete(...)`, not `asyncio.run()` — the latter can break its
  event-loop handling.
- **Don't over-configure Patchright/nodriver.** Extra headers, fake UAs and init scripts *reduce* stealth.
- **Solving Turnstile/hCaptcha isn't scraping the box** — usually you just wait for the JS challenge to
  clear. Only reach for a CAPTCHA-solving service (2captcha/CapSolver) for interactive image/click challenges.
- **Fingerprint/IP mismatch** (region, timezone, locale) flags faster than any single signal — keep them coherent.
- These walls update; a recipe that works today may need a tool bump tomorrow. Pin versions, and keep
  nodriver/Camoufox/Patchright current (`pip install -U`).
