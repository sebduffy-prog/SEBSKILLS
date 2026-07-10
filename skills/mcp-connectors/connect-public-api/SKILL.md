---
name: connect-public-api
category: mcp-connectors
description: >
  Talk to ANY public/REST API robustly when you have a URL and docs but no ready-made SDK or MCP
  server. Covers picking the right auth (API key, Bearer/OAuth2, Basic, HMAC), pagination
  (cursor, page/offset, RFC-5988 Link headers), rate-limit handling (429 + Retry-After), retries
  with exponential backoff + jitter, timeouts, and quick schema/endpoint discovery. Reach for this
  on "call this API", "wrap this REST endpoint", "how do I paginate/authenticate this API",
  "handle rate limits / 429 / Retry-After", "add retries with backoff", "no SDK for this service".
  Produces a runnable, resilient client (Python httpx+tenacity or curl) that actually survives
  throttling and transient failures.
when_to_use:
  - "You have an API's base URL + docs but there's no official SDK, client library, or MCP server"
  - "Someone says 'call this REST API', 'wrap this endpoint', or 'pull all pages from this API'"
  - "You keep hitting 429s / rate limits and need Retry-After + backoff done correctly"
  - "You need to authenticate an API request and aren't sure if it wants a key, Bearer token, Basic, or HMAC"
  - "A one-off curl worked but now you need pagination, retries, and timeouts for a real script"
  - "You want to discover an API's shape (endpoints, response schema, auth) from just the docs/base URL"
when_not_to_use:
  - "The service already ships an official MCP server → register-mcp-servers (or the specific connect-* skill)"
  - "It's GitHub → connect-github-mcp gives you native repo/issue/PR tools, no hand-rolled client"
  - "It's a SQL/NoSQL database, not an HTTP API → connect-database-mcp"
  - "You just need to fetch/scrape a rendered web page's content → connect-web-fetch-scrape-mcp or connect-playwright-mcp"
  - "You're building a NEW MCP server to expose an API as tools for others → mcp-builder"
keywords: [rest api, public api, http client, httpx, requests, curl, tenacity, retry, backoff, jitter, exponential backoff, rate limit, 429, retry-after, pagination, cursor pagination, link header, oauth2, bearer token, api key, basic auth, hmac, no sdk, wrap endpoint, schema discovery]
similar_to: [connect-github-mcp, connect-database-mcp, connect-web-fetch-scrape-mcp, register-mcp-servers]
inputs_needed:
  - "Base URL + a docs/OpenAPI link (or an example curl that already works)"
  - "Auth scheme + where the secret lives (env var name) — never paste raw secrets into code"
  - "Pagination style if known (cursor / page+offset / Link header) and how many records you actually need"
  - "Whether you need one-off exploration or a reusable, retry-hardened client"
produces: A resilient REST client (Python httpx+tenacity module or hardened curl) with auth, pagination, 429/Retry-After handling, and backoff+jitter retries
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Connect to Any Public REST API

When there's no SDK and no MCP server — just a URL and some docs — you hand-roll a client. Do it
*right* the first time: correct auth, real pagination, and retries that survive throttling instead
of hammering a 429 into a ban. This skill gives you the decision tree plus a drop-in
`scripts/api_client.py` (httpx + tenacity) that already does the hard parts.

## When to use

The moment a task needs an HTTP API that has no ready-made client. A single throwaway `curl` is
fine for a smoke test — but as soon as you need pagination, auth from env, or "pull everything and
don't die on a 429," reach for the hardened client here.

## Prerequisites

- **Python 3.9+** with two battle-tested libs (preferred path):
  `pip install "httpx>=0.27" "tenacity>=8.2"`. `httpx` is a modern sync/async HTTP client;
  `tenacity` is the standard retry library.
- **Or curl + jq** for quick exploration — no install beyond what most machines have.
- **The API's docs / OpenAPI spec** and an **auth secret in an env var** (never in source).

## Step 1 — Discover the API before you code

Read the shape first; guessing wastes calls and trips rate limits.

```bash
# Grab an OpenAPI/Swagger spec if one exists (common paths):
for p in openapi.json swagger.json openapi.yaml .well-known/openapi.json api-docs; do
  curl -fsSL "https://api.example.com/$p" -o spec.json && echo "found: $p" && break
done
# Peek at endpoints + auth from the spec:
jq '.paths | keys' spec.json 2>/dev/null
jq '.components.securitySchemes' spec.json 2>/dev/null   # tells you the auth scheme

# No spec? Probe one endpoint and read the headers (rate-limit budget lives here):
curl -sD - "https://api.example.com/v1/thing" -o /dev/null
# Look for: X-RateLimit-Limit / -Remaining / -Reset, Retry-After, Link, WWW-Authenticate
```

## Step 2 — Pick the auth scheme

Match what the docs (or `securitySchemes` / a `401 WWW-Authenticate` header) tell you.

| Scheme | How to send | Notes |
|---|---|---|
| API key (header) | `-H "X-API-Key: $KEY"` (header name varies) | Most common. Check exact header name. |
| API key (query) | `?api_key=$KEY` | Avoid if a header option exists (keys leak into logs/URLs). |
| Bearer / OAuth2 | `-H "Authorization: Bearer $TOKEN"` | Token from a `/oauth/token` client-credentials exchange (below). |
| Basic | `-u "$USER:$PASS"` or `Authorization: Basic base64(user:pass)` | HTTPS only. |
| HMAC-signed | Sign method+path+body+timestamp with a shared secret | Read the docs closely — order/encoding is exact. |

OAuth2 client-credentials token fetch (very common for machine-to-machine):

```bash
curl -s -X POST "$TOKEN_URL" \
  -d grant_type=client_credentials \
  -d client_id="$CLIENT_ID" -d client_secret="$CLIENT_SECRET" \
  -d scope="read" | jq -r .access_token
```

Rule: secrets come from `os.environ` / shell env, never literals. Validate they exist at startup
and fail fast with a clear message.

## Step 3 — Handle rate limits + retries (the part everyone gets wrong)

Non-negotiables for any real client:

- **Retry only transient failures**: connection/timeout errors and status `429, 500, 502, 503, 504`.
  Never retry `4xx` like `400/401/403/404` — backing off won't fix a bad request or bad token.
- **Exponential backoff + jitter** so parallel workers don't retry in lockstep (thundering herd).
- **Honour `Retry-After`** when the server sends it — sleep exactly that long before retrying.
- **Cap attempts** (e.g. 5) and set a **timeout** on every request so nothing hangs forever.

The `scripts/api_client.py` helper does all of this. Minimal use:

```python
import os
from scripts.api_client import ApiClient, build_auth_headers

with ApiClient(
    base_url="https://api.example.com",
    headers=build_auth_headers(bearer=os.environ["API_TOKEN"]),
) as api:
    data = api.get_json("/v1/things", params={"limit": 100})
```

If you'd rather not add the module, tenacity inline does the same:

```python
import httpx, logging
from tenacity import (retry, stop_after_attempt, wait_exponential_jitter,
                      retry_if_exception, before_sleep_log)
log = logging.getLogger(__name__)
RETRYABLE = {429, 500, 502, 503, 504}

def _retryable(e):
    return (isinstance(e, (httpx.TransportError, httpx.TimeoutException)) or
            (isinstance(e, httpx.HTTPStatusError) and e.response.status_code in RETRYABLE))

@retry(stop=stop_after_attempt(5),
       wait=wait_exponential_jitter(initial=1, max=30),
       retry=retry_if_exception(_retryable),
       before_sleep=before_sleep_log(log, logging.WARNING), reraise=True)
def get(client, url, **kw):
    r = client.get(url, timeout=30, **kw)
    r.raise_for_status()
    return r
```

Note: `httpx.HTTPTransport(retries=N)` only retries *connection* failures, not `429`/`5xx`
status codes — it is NOT a substitute for the above.

## Step 4 — Paginate to completion

Identify the style, then loop until there's no next page (always cap total pages as a guard).

| Style | Signal | Advance by |
|---|---|---|
| Link header (RFC-5988) | `Link: <…>; rel="next"` | Follow `resp.links["next"]["url"]` (GitHub, GitLab) |
| Cursor / token | `next_cursor` / `nextPageToken` in body | Pass it back as a query param |
| Page + offset | `?page=N` / `?offset=N&limit=M` | Increment until an empty/short page |

The helper handles Link-header pagination out of the box; pass a `next_link` callable for
cursor/offset APIs:

```python
# Cursor example: body has {"data": [...], "next_cursor": "abc"}
def next_cursor(resp):
    c = resp.json().get("next_cursor")
    return f"/v1/things?cursor={c}" if c else None

rows = []
for resp in api.paginate("/v1/things?limit=100", next_link=next_cursor, max_pages=100):
    rows.extend(resp.json()["data"])
```

## Verify

```bash
# 1) Helper imports + compiles clean:
python3 -c "import py_compile; py_compile.compile('scripts/api_client.py', doraise=True); print('ok')"

# 2) Live smoke test against a real, no-auth, paginated API (GitHub public list):
python3 scripts/api_client.py https://api.github.com/repositories --paginate --max-pages 2
#   -> prints "page … -> N items" lines and a total; proves auth-less GET + Link pagination + retries

# 3) Confirm your auth works BEFORE looping (expect 200, not 401/403):
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $API_TOKEN" \
  https://api.example.com/v1/whoami
```

Success = a 2xx on an authenticated call, pages advancing to the end, and a forced 429 (hit a
throttled endpoint) producing backoff-then-success in the logs rather than a crash.

## Pitfalls

- **Retrying 4xx.** `401/403` won't heal with backoff — fix the token/scope. Only retry `429`/`5xx`
  + transport errors.
- **Ignoring `Retry-After`.** Your exponential guess may be far shorter than the server's window;
  obey the header when present.
- **No jitter.** Pure exponential backoff synchronises parallel clients and re-collides. Always add
  jitter.
- **No timeout.** Without one, a stalled socket hangs the whole job. Set it on every request.
- **Unbounded pagination.** Always cap `max_pages`; a broken `next` link otherwise loops forever.
- **Secrets in URLs/code.** Prefer header auth; pull secrets from env; never log full request URLs
  that carry a `?api_key=`.
- **Trusting response shape.** Validate/parse at the boundary — an API can return `200` with an
  error body or a changed schema.
- **Reinventing a client that exists.** Before hand-rolling, re-check for an official SDK, MCP
  server, or the sibling connect-* skills — hand-rolling is the last resort, not the first.
