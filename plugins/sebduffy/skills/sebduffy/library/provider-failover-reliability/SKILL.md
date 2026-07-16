---
name: provider-failover-reliability
category: model-routing
description: >
  Make LLM calls survive rate-limits and provider outages by wiring automatic
  cross-vendor failover, retries with backoff, cooldowns, and cost- or
  latency-aware load-balancing across multiple API keys and providers. Use when
  you say "add fallback models", "failover when OpenAI 429s", "route to Anthropic
  if Azure is down", "load balance across API keys", "retry on rate limit", "make
  my LLM calls reliable / high availability", or "spread traffic by cost/latency".
  Produces a working LiteLLM Router (or Portkey gateway config) with fallbacks,
  num_retries, cooldowns and a routing strategy.
when_to_use:
  - "One provider keeps 429-ing or has an outage and you want calls to auto-retry on a different company"
  - "You have multiple API keys / deployments for the same model and want to load-balance across them"
  - "You want cheapest-first or lowest-latency routing with a safety net if the cheap one fails"
  - "You need context-window or content-policy fallbacks (overflow → bigger model)"
  - "You're moving from raw SDK calls to a resilient gateway in front of many providers"
when_not_to_use:
  - "You want to pick the right model per request by difficulty — use model-triage-router"
  - "You want one unified client/endpoint across vendors without the reliability layer — use cross-provider-gateway"
  - "You want cheap-first then escalate on low quality/confidence — use model-cascade-escalation"
  - "You want to fan out to many models and merge answers — use mixture-of-models-ensemble"
  - "You only want to estimate/compare spend, not route — use llm-cost-estimator"
keywords: [failover, fallback, litellm, portkey, router, rate limit, 429, retries, backoff, cooldown, load balancing, high availability, cost-based routing, latency routing, multiple api keys, outage, resilience]
similar_to: [cross-provider-gateway, model-triage-router, model-cascade-escalation, llm-cost-estimator, mixture-of-models-ensemble]
inputs_needed:
  - "Which providers/models to use as primary and as fallbacks (in priority order)"
  - "API keys for each provider (env vars)"
  - "Routing goal: reliability-only, cheapest-first, lowest-latency, or even load-balance"
  - "Whether you'll run in-process (LiteLLM Router) or as a shared proxy/gateway (LiteLLM proxy or Portkey)"
produces: A LiteLLM Router / config.yaml (or Portkey gateway config JSON) with cross-vendor fallbacks, retries, cooldowns and a routing strategy.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Provider Failover & Reliability

Wrap LLM calls so a 429, timeout, or outage on one company transparently retries
on another — plus cost/latency-aware load-balancing across keys. Two proven
engines: **LiteLLM Router** (Python, in-process or self-hosted proxy) and
**Portkey Gateway** (config-JSON, hosted or self-hosted). Pick one; don't stack them.

## When to use

Reach for this when *availability* is the problem, not model choice. If the same
logical `model` name should be servable by several deployments/vendors and a
failure on one should silently roll to the next, this is the skill.

## Prerequisites

- **LiteLLM path:** `pip install litellm` (Router is included; no proxy needed for in-process use). For the shared proxy add `pip install 'litellm[proxy]'`. Redis is **only** required for `usage-based` and `latency-based` strategies that share state across workers.
- **Portkey path:** `pip install portkey-ai` (or `openai` pointed at the gateway), plus a Portkey API key, OR self-host `docker run -d -p 8787:8787 portkeyai/gateway`.
- Provider keys in env: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AZURE_API_KEY`/`AZURE_API_BASE`, etc. Never hardcode — reference via `os.environ/…` in YAML.

## Recipe A — LiteLLM Router (in-process, no infra)

The fastest reliable setup. `model_name` is the *logical group*; list several
deployments under the same name and the router load-balances, then `fallbacks`
crosses to a different group when the whole group fails.

```python
import os
from litellm import Router

router = Router(
    model_list=[
        # Group "chat" — two keys / vendors, load-balanced by rpm weight
        {"model_name": "chat", "litellm_params": {
            "model": "openai/gpt-4o", "api_key": os.environ["OPENAI_API_KEY"], "rpm": 1000}},
        {"model_name": "chat", "litellm_params": {
            "model": "azure/gpt-4o", "api_key": os.environ["AZURE_API_KEY"],
            "api_base": os.environ["AZURE_API_BASE"], "rpm": 500}},
        # Fallback group — different company entirely
        {"model_name": "chat-backup", "litellm_params": {
            "model": "anthropic/claude-sonnet-4-5", "api_key": os.environ["ANTHROPIC_API_KEY"]}},
    ],
    routing_strategy="simple-shuffle",   # default; weighted by rpm, no Redis
    fallbacks=[{"chat": ["chat-backup"]}],  # cross-vendor safety net
    num_retries=3,          # retry same group before falling back
    request_timeout=30,
    allowed_fails=3,        # failures/min before a deployment is cooled down
    cooldown_time=30,       # seconds a bad deployment sits out
)

resp = router.completion(model="chat", messages=[{"role": "user", "content": "Hello"}])
print(resp.choices[0].message.content)
```

Order of operations: `num_retries` on the *primary group* (with backoff on
rate-limits) → still failing → `fallbacks` to the next group → a flapping
deployment is put in `cooldown_time` after `allowed_fails`/min.

## Recipe B — Typed fallbacks (overflow & content policy)

Different failures deserve different escapes. LiteLLM has three fallback lists:

```python
router = Router(
    model_list=[
        {"model_name": "gpt-4o",    "litellm_params": {"model": "openai/gpt-4o",    "api_key": os.environ["OPENAI_API_KEY"]}},
        {"model_name": "big-ctx",   "litellm_params": {"model": "anthropic/claude-sonnet-4-5", "api_key": os.environ["ANTHROPIC_API_KEY"]}},
        {"model_name": "lenient",   "litellm_params": {"model": "anthropic/claude-haiku-4-5",  "api_key": os.environ["ANTHROPIC_API_KEY"]}},
    ],
    fallbacks=[{"gpt-4o": ["big-ctx"]}],                  # generic errors / outage
    context_window_fallbacks=[{"gpt-4o": ["big-ctx"]}],   # prompt too long → bigger window
    content_policy_fallbacks=[{"gpt-4o": ["lenient"]}],   # policy block → different filter
    num_retries=2,
)
```

## Recipe C — Cost- or latency-aware routing

Same reliability, but pick the *cheapest* (or *fastest*) healthy deployment first.

```python
# Cheapest-first: router sends to lowest cost/token, fallbacks still apply
router = Router(
    model_list=[
        {"model_name": "chat", "litellm_params": {
            "model": "openai/gpt-4o-mini", "api_key": os.environ["OPENAI_API_KEY"],
            "input_cost_per_token": 0.00000015, "output_cost_per_token": 0.0000006}},
        {"model_name": "chat", "litellm_params": {
            "model": "anthropic/claude-haiku-4-5", "api_key": os.environ["ANTHROPIC_API_KEY"],
            "input_cost_per_token": 0.0000008, "output_cost_per_token": 0.000004}},
    ],
    routing_strategy="cost-based-routing",
    fallbacks=[{"chat": ["chat"]}],
)
```

Swap `routing_strategy` for: `"latency-based-routing"` (fastest recent, needs
Redis to share across processes), `"usage-based-routing-v2"` (lowest current
TPM/RPM, Redis), or `"least-busy"` (fewest in-flight). `"simple-shuffle"` (default)
is stateless and weights by `rpm`/`weight` — prefer it unless you need shared state.

## Recipe D — LiteLLM proxy (shared gateway for many apps)

`config.yaml`, then `litellm --config config.yaml`. Any app talks OpenAI-format
to `http://localhost:4000`.

```yaml
model_list:
  - model_name: chat
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY
      rpm: 1000
      weight: 9
  - model_name: chat
    litellm_params:
      model: azure/gpt-4o
      api_key: os.environ/AZURE_API_KEY
      api_base: os.environ/AZURE_API_BASE
      weight: 1
  - model_name: chat-backup
    litellm_params:
      model: anthropic/claude-sonnet-4-5
      api_key: os.environ/ANTHROPIC_API_KEY

litellm_settings:
  num_retries: 3
  request_timeout: 30
  fallbacks: [{"chat": ["chat-backup"]}]
  context_window_fallbacks: [{"chat": ["chat-backup"]}]
  allowed_fails: 3
  cooldown_time: 30

router_settings:
  routing_strategy: simple-shuffle
  # redis_host/redis_port/redis_password only needed for usage/latency strategies

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
```

## Recipe E — Portkey Gateway (config-JSON, no code change)

If you prefer a hosted/edge gateway and OpenAI-compatible clients. Fallback fires
on any non-2xx by default; scope it with `on_status_codes`.

```json
{
  "strategy": { "mode": "fallback", "on_status_codes": [429, 503, 500] },
  "targets": [
    { "override_params": { "model": "@openai-prod/gpt-4o" } },
    { "override_params": { "model": "@anthropic-prod/claude-sonnet-4-5" } }
  ]
}
```

Load-balance across keys/vendors by weight (targets can nest fallbacks):

```json
{
  "strategy": { "mode": "loadbalance" },
  "targets": [
    { "provider": "@openai-prod",  "weight": 0.7 },
    { "provider": "@azure-prod",   "weight": 0.3 }
  ]
}
```

Pass either JSON through the `config` parameter of the Portkey SDK / header
`x-portkey-config`. Nest a `loadbalance` block inside a `fallback` target to get
both at once.

## Verify

- **Simulate a fallback without real failures** (LiteLLM): add `mock_testing_fallbacks=True` to the `router.completion(...)` call — it forces the primary to fail so you can confirm the backup answers.
- **Force a 429 path:** temporarily set a tiny `rpm` on the primary deployment and fire a burst; confirm traffic shifts and the cooled-down deployment returns after `cooldown_time`.
- **Confirm routing choice:** log `resp._hidden_params.get("model_id")` / `resp.model` to see which deployment served the call.
- Quick smoke helper: `python3 scripts/failover_smoke.py` (needs at least one real key; prints which deployment answered and proves the fallback triggers).

## Pitfalls

- **`fallbacks` groups vs `model_list` load-balancing are different layers.** Multiple entries with the *same* `model_name` load-balance; `fallbacks` maps one `model_name` to *other* names. Don't put a cross-vendor jump only in `model_list` and expect ordered failover.
- **`latency-based`/`usage-based` strategies need Redis** to work across processes/workers — without it each worker has its own view and routing degrades to per-process. `simple-shuffle` and `cost-based` are fine stateless.
- **`num_retries` runs before `fallbacks`.** A high retry count on a hard-down provider adds latency before the cross-vendor jump. Keep `num_retries` small (2–3) and `request_timeout` tight so failover is fast.
- **Cost map staleness:** `cost-based-routing` uses LiteLLM's `model_cost` map unless you set `input_cost_per_token`/`output_cost_per_token` explicitly. Set them for new/renamed models so it doesn't misrank.
- **Model name drift:** provider model IDs change (e.g. dated Claude/GPT snapshots). Pin current IDs and review after any provider deprecation; a wrong ID looks like a permanent outage and burns your whole fallback chain.
- **Content-policy and context-window errors won't be caught by the generic `fallbacks` list** in the way you expect — use the typed `content_policy_fallbacks` / `context_window_fallbacks` (Recipe B).
- **Don't double-wrap:** running Portkey in front of a LiteLLM proxy (or vice-versa) doubles retries/timeouts and confuses cooldown accounting. Choose one reliability layer.
