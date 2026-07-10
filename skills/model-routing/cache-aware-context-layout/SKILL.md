---
name: cache-aware-context-layout
category: model-routing
description: >
  Audit and restructure LLM prompts so the provider's prompt cache actually
  hits — turning 7% hit rates into 70%+. Enforces the one rule every vendor
  shares: static content FIRST (tools -> system -> long context), volatile
  content LAST, one stable breakpoint on the last shared block. Covers Anthropic
  cache_control ttl 5m/1h, OpenAI automatic caching, Gemini implicit/explicit
  caching, DeepSeek, plus cross-user prefix sharing. Use when someone says "my
  cache never hits", "improve prompt cache hit rate", "cut input token cost",
  "why is cache_read_input_tokens zero", "cache the system prompt", "prefix
  caching", "TTL 1 hour cache", or "reorder the prompt so it caches".
when_to_use:
  - "Your cache_read_input_tokens / cached_tokens is near zero even on repeated calls"
  - "The same big system prompt or RAG context is resent every request and you want it cached"
  - "You put a timestamp, user id, or the user question near the TOP of the prompt"
  - "You want to pick 5m vs 1h TTL and place the ≤4 breakpoints correctly"
  - "You want one shared static prefix to hit across many users / sessions"
  - "You're moving between providers and need each one's caching wired right"
when_not_to_use:
  - "You want to reuse whole RESPONSES for semantically-similar prompts -> semantic-response-cache"
  - "You want to shrink OUTPUT length / stop verbose generations -> output-token-diet"
  - "You want to send non-urgent work to a 50%-off batch queue -> batch-api-offloader"
  - "You just want a cheaper model per request, not layout -> model-triage-router"
  - "You want a total cost model across models/providers -> llm-cost-estimator"
keywords: [prompt caching, cache hit rate, cache_control, ephemeral, ttl, 5m, 1h, cache_read_input_tokens, cache_creation_input_tokens, prefix caching, static prefix, cached_tokens, kv cache, context layout, breakpoint, cache miss, prewarm cache, deepseek cache, gemini context caching, cross user cache]
similar_to: [semantic-response-cache, output-token-diet, batch-api-offloader, model-triage-router, llm-cost-estimator, best-model-per-step-pipeline]
inputs_needed:
  - "The exact request payload or template (tools + system + messages), or a sample of real prompts"
  - "Provider + model (min cacheable tokens differs: 1024 typical, 2048 Haiku 3.5)"
  - "Reuse pattern: same prefix across turns? across users? how often within 5 min / 1 hour?"
produces: A reordered prompt template (static prefix -> volatile suffix) with correct cache_control breakpoints/TTL, plus a before/after hit-rate + cost estimate.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Cache-Aware Context Layout

Provider prompt caches key on an **exact-match prefix**. A cache hit needs the
bytes from the start of the request up to a breakpoint to be byte-identical to a
recent request. Put anything that changes per call (timestamp, user id, the
question, retrieved chunks that reorder) near the front and you invalidate the
whole prefix every time — hit rate collapses to near zero. Fix the ordering and
the same traffic reads the cache at ~0.1x input cost.

The universal law across Anthropic, OpenAI, Gemini and DeepSeek:

> **Static content first, volatile content last.** tools → system → long shared
> context (docs, examples, schema) → then the per-call turn / question at the very end.

## When to use

- Repeated calls share a large fixed block (system prompt, RAG corpus, few-shot set, tool defs).
- `cache_read_input_tokens` (Anthropic) / `cached_tokens` (OpenAI) / `cachedContentTokenCount` (Gemini) / `prompt_cache_hit_tokens` (DeepSeek) stays low.
- You want cross-user sharing: a common instruction prefix that every user's request reuses.

## Prerequisites

- No new deps for the audit — `scripts/cache_audit.py` is pure Python 3 stdlib.
- To measure real hits you need the provider SDK + an API key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`).
- Know your model's **minimum cacheable tokens**: 1024 for most Claude models (2048 for Haiku 3.5); OpenAI caches automatically at ≥1024 tokens; Gemini 2.5 implicit caching kicks in ~1024 (Flash) / 2048 (Pro).

## Recipe 1 — Audit the current layout

```bash
python3 scripts/cache_audit.py request.json --min-tokens 1024
```

Flags the three killers: (a) prefix too small to cache, (b) volatile tokens
(`{{...}}`, timestamp, uuid, session_id) sitting in the static prefix, (c) a
breakpoint stuck on the last volatile block. Exit 1 = fix needed.

## Recipe 2 — Restructure (Anthropic explicit breakpoints)

Order is fixed by the API: **tools → system → messages**. A change at any level
invalidates that level and everything after it. Place the `cache_control`
breakpoint on the **last block you want cached** — the largest stable suffix.

```python
import anthropic
client = anthropic.Anthropic()

STATIC_DOCS = open("corpus.txt").read()   # big, unchanging per request

resp = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system=[
        {"type": "text", "text": "You are a support agent. Follow policy X."},
        {"type": "text", "text": STATIC_DOCS,
         "cache_control": {"type": "ephemeral", "ttl": "1h"}},  # ← breakpoint on last static block
    ],
    messages=[
        # volatile per-call content goes HERE, after the cached prefix
        {"role": "user", "content": f"Ticket #{ticket_id}: {question}"},
    ],
)
u = resp.usage
print(u.cache_creation_input_tokens, u.cache_read_input_tokens)
# call 1: creation>0, read=0   call 2 (within TTL): read>0, creation~0
```

Rules that matter:
- **Max 4 breakpoints** per request. The API also checks ~20 blocks back from each breakpoint for a hit, so a single well-placed breakpoint usually suffices.
- **TTL**: `"5m"` default (write 1.25x base input) vs `"1h"` (write 2.0x). Reads/refreshes are 0.1x either way. Use 1h only when reuse gaps exceed 5 min but stay under an hour; each hit within the window refreshes the TTL.
- **Do not** put the timestamp, user name, request id, or the user's turn inside the cached prefix. That is the #1 cause of 0% hit rate.
- Multi-turn: move the breakpoint forward to the latest stable turn each round so growing history keeps reading the cache.

## Recipe 3 — Pre-warm so the first real user hits

```python
client.messages.create(
    model="claude-sonnet-4-6", max_tokens=1,
    system=[{"type": "text", "text": STATIC_DOCS,
             "cache_control": {"type": "ephemeral", "ttl": "1h"}}],
    messages=[{"role": "user", "content": "warm"}],
)  # writes cache; discard output. Next real request reads it.
```

## Recipe 4 — Cross-provider notes

- **OpenAI** — caching is **automatic**, no `cache_control`. Just put the static
  content at the START of the prompt (identical prefix ≥1024 tokens, then in
  128-token steps). Discount on cached input tokens; see `usage.prompt_tokens_details.cached_tokens`.
- **Gemini 2.5** — **implicit** caching is on by default (put common content
  first; ~75% discount, `usageMetadata.cachedContentTokenCount`). For guaranteed
  hits use **explicit** `client.caches.create(...)` → a `CachedContent` handle
  with its own TTL, referenced by later `generateContent` calls.
- **DeepSeek** — automatic context caching; watch `prompt_cache_hit_tokens` vs
  `prompt_cache_miss_tokens`. Same rule: stable prefix first.
- Every provider: **exact byte match** of the prefix is required. Normalise
  whitespace, JSON key order (`sort_keys=True`), and tool-definition order so the
  prefix is deterministic across builds.

## Recipe 5 — Cross-user shared prefix

To share one cache across many users, the shared segment must be **100%
identical and appear first**, with all user-specific data strictly after the
breakpoint. Caches are isolated per **workspace/organization** (never shared
across orgs), so a common system prompt + corpus placed before any user field
lets every user's first call read a prefix another user just wrote.

## Verify

```bash
# Layout check (offline)
python3 scripts/cache_audit.py request.json && echo OK
```

Then confirm live: fire the same request twice within the TTL. Anthropic call 2
must show `cache_read_input_tokens` ≈ the prefix size and `cache_creation_input_tokens` ≈ 0.
Hit-rate = `cache_read / (cache_read + cache_creation + input)` across a window;
aim >0.7 for high-reuse traffic. Cost drops because read tokens bill at 0.1x.

## Pitfalls

- **Volatile prefix** — timestamp/uuid/user id before the breakpoint kills every hit. Move it to the suffix. This is 90% of "cache never hits".
- **Prefix under the minimum** (≈1024 tok) — nothing caches at all; consolidate small blocks or accept no caching.
- **Breakpoint on the last, changing block** — you pay the 1.25x write every call and never read. Anchor it on the last *stable* block.
- **Non-deterministic serialization** — reordered tools, unsorted JSON, or trailing-whitespace drift silently breaks the byte match; hit rate flickers.
- **Tool definition edits** invalidate the entire cache (tools sit at the front). Freeze tool schemas; don't regenerate them per request.
- **Wrong TTL economics** — paying 2.0x for 1h writes when reuse happens within 5 min wastes money; use 5m unless the reuse gap genuinely exceeds it.
- **Images/thinking/tool_choice toggles** invalidate message-level caches (not tools/system) — keep them constant across cached turns.
