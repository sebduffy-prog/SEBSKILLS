---
name: cross-provider-gateway
category: model-routing
description: >
  Put ONE OpenAI-compatible endpoint in front of Anthropic, OpenAI, Google/Gemini, Mistral, Groq,
  and open-weight models so a single call site can hit any vendor by changing a string. Ships three
  concrete recipes — LiteLLM proxy (self-host, config.yaml), Portkey gateway (self-host, npx/docker),
  and OpenRouter (hosted, zero infra). Use when someone says "one endpoint for all LLMs", "swap
  providers without changing code", "OpenAI-compatible proxy", "route to any model", "abstract the
  vendor behind base_url", "add Gemini/Mistral behind my OpenAI SDK", or "stop hardcoding one API".
when_to_use:
  - "I want one base_url + one SDK to call Claude, GPT, Gemini and open models interchangeably"
  - "Swap the model provider by changing a string, not rewriting the client"
  - "Stand up a self-hosted OpenAI-compatible proxy (LiteLLM or Portkey) in front of N vendors"
  - "Use OpenRouter as a hosted gateway so I don't run any infra"
  - "Give my whole team one endpoint + virtual keys instead of scattering provider API keys"
  - "Normalise every provider's request/response to the OpenAI chat-completions schema"
when_not_to_use:
  - "Deciding WHICH model a given request should go to by difficulty/cost — use model-triage-router"
  - "Retry a failed call on a backup provider / circuit-breaking — use provider-failover-reliability"
  - "Try cheap model first, escalate to bigger on low confidence — use model-cascade-escalation"
  - "Fan one prompt to several models and merge — use mixture-of-models-ensemble"
  - "Estimate $ per call across providers before running — use llm-cost-estimator"
keywords: [litellm, portkey, openrouter, openai-compatible, gateway, proxy, unified api, one endpoint, base_url, model routing, multi-provider, anthropic, gemini, mistral, groq, virtual keys, config.yaml, chat completions, vendor abstraction, drop-in]
similar_to: [model-triage-router, provider-failover-reliability, model-cascade-escalation, mixture-of-models-ensemble, llm-cost-estimator]
inputs_needed:
  - Which providers to expose (openai | anthropic | gemini | mistral | groq | ollama | ...) + their API keys
  - Deployment style — self-host (LiteLLM or Portkey) vs hosted (OpenRouter)
  - Whether you need team virtual keys / spend tracking (LiteLLM & Portkey) or just a raw passthrough
  - The client language/SDK that will call the gateway (usually the OpenAI SDK)
produces: A single OpenAI-compatible endpoint (base_url) that fans out to any configured vendor by model name
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Cross-Provider Gateway — one endpoint, any vendor

Collapse "which SDK / which base_url / which auth header" down to **one OpenAI-compatible endpoint**.
Your app always talks OpenAI chat-completions; the gateway translates to Anthropic / Gemini / Mistral /
Groq / Ollama and back. Change providers by editing config (or a model string), never the call site.

Three grounded paths — pick by how much infra you want to own:

| Path | Host | Best when | Extras |
|------|------|-----------|--------|
| **LiteLLM proxy** | self | full control, virtual keys, spend limits, 100+ providers | config.yaml, fallbacks, budgets |
| **Portkey gateway** | self | fast edge gateway, header- or config-driven routing | fallback/loadbalance configs |
| **OpenRouter** | hosted | zero infra, one key, pay-per-token | built-in fallback `models` array |

> This skill is the **plumbing** (one endpoint → many vendors). Deciding *which* model to send a
> given request to is `model-triage-router`; automatic retry-on-failure is `provider-failover-reliability`.

## Prerequisites

- Provider API keys for whatever you expose (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, …).
- **LiteLLM path:** Python 3.9+; `pip install 'litellm[proxy]'` (or `uv tool install 'litellm[proxy]'`).
- **Portkey path:** Node 18+ (for `npx`) or Docker.
- **OpenRouter path:** just an account + `OPENROUTER_API_KEY` (https://openrouter.ai/keys). No install.
- The OpenAI SDK on the client side: `pip install openai` / `npm i openai`.

---

## Recipe A — LiteLLM proxy (self-host, most control)

**1. Write `config.yaml`.** Each `model_name` is the alias your app calls; `litellm_params.model`
is the real `provider/model` LiteLLM dials. Keys come from env (`os.environ/VAR`) — never inline secrets.

```yaml
model_list:
  - model_name: gpt              # your alias
    litellm_params:
      model: openai/gpt-4o-mini
      api_key: os.environ/OPENAI_API_KEY
  - model_name: claude
    litellm_params:
      model: anthropic/claude-sonnet-4-5
      api_key: os.environ/ANTHROPIC_API_KEY
  - model_name: gemini
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: os.environ/GEMINI_API_KEY
  - model_name: mistral
    litellm_params:
      model: mistral/mistral-large-latest
      api_key: os.environ/MISTRAL_API_KEY
  - model_name: local            # open-weight via Ollama
    litellm_params:
      model: ollama/llama3.1
      api_base: http://localhost:11434

litellm_settings:
  num_retries: 2
  request_timeout: 60
```

**2. Start it** (default port **4000**). A master key turns on auth + virtual keys:

```bash
export LITELLM_MASTER_KEY='sk-master-CHANGE_ME'   # optional but recommended
litellm --config config.yaml                       # -> http://0.0.0.0:4000
```

**3. Call it with the plain OpenAI SDK** — swap vendors by changing `model` only:

```python
from openai import OpenAI
c = OpenAI(base_url="http://0.0.0.0:4000", api_key="sk-master-CHANGE_ME")

for alias in ["gpt", "claude", "gemini", "mistral", "local"]:
    r = c.chat.completions.create(model=alias, messages=[{"role":"user","content":"one word: ping?"}])
    print(alias, "→", r.choices[0].message.content)
```

**Team virtual keys (optional).** With a master key set, mint scoped keys with budgets so teammates
never see raw provider keys:

```bash
curl http://0.0.0.0:4000/key/generate -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"models":["gpt","claude"],"max_budget":20,"budget_duration":"30d"}'
```

**Fallbacks (define an ordered backup, still one alias).** Add under `router_settings`:

```yaml
router_settings:
  fallbacks: [{"gpt": ["claude", "gemini"]}]   # if gpt errors, try claude then gemini
```

---

## Recipe B — Portkey gateway (self-host, edge-fast)

Run the open-source gateway, then point the OpenAI SDK at it and name the target provider in a header.

```bash
npx @portkey-ai/gateway                 # -> http://localhost:8787 ; console at /public/
# or: docker run -p 8787:8787 portkey-ai/gateway
```

Base URL is `http://localhost:8787/v1`. Route with `x-portkey-provider` + the provider's own key:

```bash
# OpenAI
curl http://localhost:8787/v1/chat/completions \
  -H "x-portkey-provider: openai"    -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}]}'

# Anthropic — same URL, different two headers
curl http://localhost:8787/v1/chat/completions \
  -H "x-portkey-provider: anthropic" -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-4-5","messages":[{"role":"user","content":"hi"}],"max_tokens":64}'
```

From Python, pass the routing header via `default_headers` so the rest of your code is vanilla OpenAI SDK:

```python
from openai import OpenAI
def portkey(provider, key):
    return OpenAI(base_url="http://localhost:8787/v1", api_key=key,
                  default_headers={"x-portkey-provider": provider})

portkey("openai",    OPENAI_KEY).chat.completions.create(model="gpt-4o-mini", messages=msgs)
portkey("anthropic", ANTHROPIC_KEY).chat.completions.create(model="claude-sonnet-4-5", messages=msgs, max_tokens=256)
```

Fallback / load-balance across providers is expressed as a Portkey **config** (JSON with a `strategy`
of `fallback` or `loadbalance` and a `targets` list) passed via `x-portkey-config`. See the gateway
repo's `configs` docs; keep it in a file and reference it so routing is version-controlled.

---

## Recipe C — OpenRouter (hosted, zero infra)

One key, one URL, hundreds of models under a `vendor/model` slug. Nothing to run.

```python
from openai import OpenAI
c = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

c.chat.completions.create(
    model="anthropic/claude-sonnet-4.5",           # swap to openai/..., google/..., mistralai/...
    messages=[{"role":"user","content":"one word: ping?"}],
)
```

curl equivalent:

```bash
curl https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"anthropic/claude-sonnet-4.5","messages":[{"role":"user","content":"hi"}]}'
```

**Built-in fallback** — pass an ordered `models` array; OpenRouter tries them in turn on error/unavailability:

```json
{"models": ["anthropic/claude-sonnet-4.5", "openai/gpt-4o", "google/gemini-2.5-flash"],
 "messages": [{"role": "user", "content": "hi"}]}
```

Discover current slugs at `GET https://openrouter.ai/api/v1/models` (don't hardcode a slug you haven't verified).

---

## Choosing between them

- **Own the keys, want budgets/virtual keys/audit + 100+ providers →** LiteLLM (Recipe A).
- **Want a tiny fast gateway you can also deploy to an edge/worker →** Portkey (Recipe B).
- **Want it working in 60 seconds with one key and no server →** OpenRouter (Recipe C).
- Mix freely: many teams put LiteLLM/Portkey in front and add OpenRouter as *one more provider* behind it.

## Verify

- **Reachable:** `curl -s http://0.0.0.0:4000/health` (LiteLLM) / `http://localhost:8787/v1/health`
  (Portkey) returns OK; OpenRouter: a 200 from the models endpoint.
- **Vendor-swap works:** run the same `messages` against ≥3 different `model` values through the
  gateway and confirm each returns a completion — that proves the abstraction, not one lucky provider.
- **Fallback fires:** temporarily give the primary a bad key and confirm the request still succeeds
  via the backup (LiteLLM `fallbacks` / OpenRouter `models` array).
- **No secrets leaked:** grep your config and code — provider keys should be `os.environ/…` refs or
  env-injected headers, never literals committed to the repo.

## Pitfalls

- **Anthropic needs `max_tokens`.** Passing through to Claude without `max_tokens` 400s. Always send it.
- **Model names aren't portable.** `claude-sonnet-4-5` (LiteLLM), `anthropic/claude-sonnet-4.5`
  (OpenRouter), bare `claude-sonnet-4-5` (Portkey header route) differ. Verify each vendor's current
  slug from its models list — do not assume.
- **Not every param round-trips.** Provider-specific fields (Anthropic `thinking`, OpenAI
  `logprobs`, structured-output schemas) may be silently dropped or rejected by the translation layer.
  Test the exact features you rely on, per provider.
- **Streaming quirks.** SSE chunk shapes vary slightly; if you parse deltas, test streaming per vendor.
- **Bind address in prod.** `litellm` listens on `0.0.0.0:4000` — put it behind auth (master key) and
  a firewall/reverse proxy; never expose an unauthenticated proxy that holds your provider keys.
- **This is plumbing, not policy.** The gateway will send whatever `model` you name — it makes no
  cost/quality decision. For that, layer `model-triage-router` (choose model) and
  `provider-failover-reliability` (retry logic) on top of this endpoint.
- **Rate limits stack.** The gateway doesn't raise a provider's underlying TPM/RPM ceiling; set
  `num_retries`/timeouts and lean on fallbacks rather than hammering one vendor.
