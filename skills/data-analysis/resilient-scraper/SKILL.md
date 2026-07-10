---
name: resilient-scraper
category: data-analysis
description: >
  Build a polite, reliable HTTP scraper in Python that doesn't get banned or drop data — httpx (async + HTTP/2)
  with tenacity exponential backoff + jitter, robots.txt compliance, Retry-After honouring, a token-bucket rate
  limiter, bounded concurrency, and User-Agent/proxy rotation on 403/429. Use this whenever someone says "scrape
  a site reliably", "my scraper keeps getting 429/403/blocked", "fetch thousands of URLs without getting banned",
  "add retries/backoff to requests", "rate-limit my crawler", or wants a production HTTP fetch layer. For a plain
  HTML page this is overkill — but for volume, flakiness, or rate limits, reach for it.
when_to_use:
  - Fetching hundreds/thousands of URLs and needing to not get rate-limited or banned
  - An existing scraper intermittently fails with 429, 403, timeouts, or connection resets
  - You need backoff+jitter, robots.txt respect, and a global requests-per-second cap
  - You want bounded async concurrency over a URL list with clean error handling
when_not_to_use:
  - A single page → just use httpx.get / requests directly, no harness needed
  - Site needs JS rendering or is behind Cloudflare/DataDome → use stealth-browser-scraping
  - You want URL→clean markdown/JSON extraction as a managed service → use firecrawl-scrape
  - You need to enumerate a site's URLs first → use sitemap-crawl-harvest
  - Turning fetched HTML into typed records → use structured-page-extraction
keywords: [scraper, scraping, httpx, tenacity, retry, backoff, jitter, rate limit, token bucket, 429, 403, robots.txt, retry-after, async, concurrency, proxy rotation, user agent, crawler, requests, polite]
similar_to: [stealth-browser-scraping, firecrawl-scrape, structured-page-extraction, sitemap-crawl-harvest, connect-public-api]
inputs_needed:
  - The list (or source) of URLs to fetch
  - Target requests-per-second and max in-flight concurrency the site can tolerate
  - Whether robots.txt must be obeyed (default yes)
  - Any proxy pool / rotating UA list (optional)
produces: A reusable async fetch layer that returns fetched bodies with per-URL status, retried and rate-limited
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Resilient scraper

A production HTTP fetch layer that stays polite and survives flakiness: async httpx + tenacity retries with
jitter, a token-bucket RPS cap, bounded concurrency, robots.txt + Retry-After respect, and UA/proxy rotation on
block responses.

## When to use

Reach for this the moment you're fetching at volume or seeing intermittent `429`/`403`/timeouts. For one page,
`httpx.get(url)` is enough — don't over-build.

## Prerequisites

```bash
python3 -m pip install --user httpx tenacity   # httpx[http2] for HTTP/2
```
macOS note: this machine's `python3` is 3.9 — httpx and tenacity both support it.

## The pattern

```python
import asyncio, random, time
import httpx
from tenacity import (retry, stop_after_attempt, wait_exponential_jitter,
                      retry_if_exception_type)

UAS = ["Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"]

class TokenBucket:
    """Global requests-per-second limiter shared across all workers."""
    def __init__(self, rps: float):
        self.rate = rps; self.tokens = rps; self.updated = time.monotonic()
        self.lock = asyncio.Lock()
    async def take(self):
        async with self.lock:
            now = time.monotonic()
            self.tokens = min(self.rate, self.tokens + (now - self.updated) * self.rate)
            self.updated = now
            if self.tokens < 1:
                await asyncio.sleep((1 - self.tokens) / self.rate)
                self.tokens = 0
            else:
                self.tokens -= 1

RETRYABLE = (httpx.TransportError, httpx.HTTPStatusError)

@retry(stop=stop_after_attempt(5),
       wait=wait_exponential_jitter(initial=1, max=30),   # full jitter, caps at 30s
       retry=retry_if_exception_type(RETRYABLE), reraise=True)
async def _get(client, url, bucket):
    await bucket.take()
    r = await client.get(url, headers={"User-Agent": random.choice(UAS)})
    if r.status_code in (429, 503):
        # honour Retry-After if the server sent one
        ra = r.headers.get("Retry-After")
        if ra and ra.isdigit():
            await asyncio.sleep(min(int(ra), 60))
        r.raise_for_status()          # -> triggers a tenacity retry
    r.raise_for_status()
    return r

async def fetch_all(urls, rps=5, concurrency=10):
    bucket = TokenBucket(rps)
    sem = asyncio.Semaphore(concurrency)         # bounded in-flight
    limits = httpx.Limits(max_connections=concurrency)
    async with httpx.AsyncClient(http2=True, timeout=20, limits=limits,
                                 follow_redirects=True) as client:
        async def one(u):
            async with sem:
                try:
                    r = await _get(client, u, bucket)
                    return {"url": u, "status": r.status_code, "body": r.text}
                except Exception as e:
                    return {"url": u, "status": None, "error": repr(e)}
        return await asyncio.gather(*(one(u) for u in urls))

# results = asyncio.run(fetch_all(urls, rps=5, concurrency=10))
```

## robots.txt

Respect crawl rules before fetching (default on):

```python
import urllib.robotparser, urllib.parse
def allowed(url, ua="*"):
    p = urllib.parse.urlsplit(url)
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{p.scheme}://{p.netloc}/robots.txt"); rp.read()
    return rp.can_fetch(ua, url)
```

## Proxy / UA rotation on block

On a `403`, swap proxy and UA before the next attempt: build the client with `proxies=next(proxy_pool)` and pick a
fresh UA per request (already done above). Keep a small cooldown per proxy that just got blocked.

## Verify

- Point it at a batch of URLs with `rps=5, concurrency=10`; confirm results carry per-URL `status`/`error` and no unhandled exceptions.
- Hit an endpoint that returns 429 and confirm it backs off (honours Retry-After) and eventually succeeds or fails cleanly after 5 tries.

## Pitfalls

- **Don't set concurrency higher than the site tolerates** — the token bucket caps RPS, but too many open connections still trips WAFs. Start conservative.
- **Full jitter matters** — fixed backoff causes thundering-herd retries. `wait_exponential_jitter` randomises.
- **Retry-After can be a date**, not just seconds — the snippet handles the numeric form; parse HTTP-date if a target uses it.
- If a site actively fingerprints headless/bot traffic, no amount of politeness helps → escalate to `stealth-browser-scraping`.
