---
name: agentic-commerce-integration
category: commerce
description: >-
  Wire a merchant catalog into ChatGPT Instant Checkout via the Agentic Commerce
  Protocol (ACP). Use to build the product feed, implement the four merchant
  checkout-session endpoints plus delegate-payment, verify request signatures,
  redeem the Stripe Shared Payment Token, and pass the OpenAI onboarding review.
  Reach for this when someone says ACP, Instant Checkout, "sell in ChatGPT",
  agentic commerce, shopping agents, product feed, or delegated payment token.
when_to_use:
  - Exposing a product catalog to ChatGPT / shopping agents so items are buyable in chat
  - Implementing the ACP checkout_sessions create / update / complete / cancel endpoints
  - Building or validating the OpenAI product feed (fields, availability, checkout eligibility)
  - Redeeming a Stripe Shared Payment Token (spt_) on checkout completion
  - Verifying inbound ACP request signatures and enforcing idempotency
  - Preparing an Etsy/Shopify-style merchant for OpenAI Instant Checkout onboarding
when_not_to_use:
  - Building a generic Stripe Checkout / Payment Intents web flow with no agent (use a plain Stripe integration, not ACP)
  - Standing up an MCP server to expose tools to Claude (use mcp-builder)
  - Pure catalog/merchandising strategy with no technical integration (use a strategy skill)
  - Google/Meta shopping feed only, no ChatGPT checkout (use those platforms' native feed docs)
keywords:
  - agentic commerce
  - acp
  - instant checkout
  - chatgpt shopping
  - product feed
  - delegate payment
  - shared payment token
  - stripe
  - openai
  - checkout session
  - shopping agents
  - idempotency
  - webhook
  - iso 4217
similar_to: []
inputs_needed: Product catalog data; a Stripe account (PSP) or ACP-compatible processor; a merchant HTTPS backend to host endpoints; OpenAI merchant/commerce access + shared API key
produces: A validated product feed, four ACP checkout endpoints + delegate-payment, signature verification and Stripe SPT redemption, ready for OpenAI onboarding
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Agentic Commerce Integration (ChatGPT Instant Checkout / ACP)

Make a merchant catalog discoverable and buyable inside ChatGPT. The **Agentic
Commerce Protocol (ACP)** — co-maintained by OpenAI and Stripe, Apache-2.0,
spec version dated `2026-04-17` — has two halves: a **product feed** you upload
to OpenAI, and a set of **REST endpoints the merchant implements** that the
agent calls to run the cart and complete the order. Payment is *delegated*: the
buyer's card becomes a scoped **Stripe Shared Payment Token** you charge on your
own PSP.

## When to use

Use this when a brand wants its products to appear in ChatGPT Shopping and be
purchased in-chat (the Etsy / Shopify / Glossier / Vuori pattern), or when you
must build/validate the feed, implement the checkout endpoints, or wire up
delegated payment. See frontmatter for the full when-to-use / when-not.

## Prerequisites (honest)

- **A merchant HTTPS backend** you control to host the endpoints (any stack).
- **A PSP that supports ACP delegated payment** — Stripe is the reference. You
  need Stripe API keys; the Shared Payment Token is redeemed like a normal
  payment method on a PaymentIntent.
- **OpenAI commerce access**: a shared secret / API key issued during merchant
  onboarding, used both to authenticate inbound agent requests and to sign the
  feed upload. Instant Checkout is invite/allowlist gated and (at launch) US
  buyers + US sellers — confirm current eligibility before promising a date.
- No SDK is required; ACP is plain JSON over HTTPS. `python3` (3.9 here) is
  enough to validate the feed and prototype handlers.
- Ground truth: `github.com/agentic-commerce-protocol/agentic-commerce-protocol`
  (`spec/2026-04-17/openapi/*.yaml`), `docs.stripe.com/agentic-commerce/acp`,
  `developers.openai.com/commerce`.

## Recipe 1 — Build and validate the product feed

The feed is a JSON array (or NDJSON) of product objects uploaded to OpenAI on a
refresh schedule. **Required** fields per the OpenAI Products spec:

| field | notes |
|-------|-------|
| `item_id` | your product id, ≤100 chars |
| `title` | ≤150 chars |
| `description` | ≤5000 chars |
| `url`, `image_url` | product page + main image |
| `brand` | ≤70 chars |
| `price` | `"<amount> <ISO4217>"`, e.g. `"29.99 USD"` |
| `availability` | `in_stock` \| `out_of_stock` \| `pre_order` \| `backorder` \| `unknown` |
| `is_eligible_search` | boolean — show in ChatGPT Shopping search |
| `is_eligible_checkout` | boolean — allow in-chat purchase |
| `seller_name`, `seller_url` | seller identity |
| `target_countries` | list of ISO 3166-1 alpha-2 |
| `store_country` | ISO 3166-1 alpha-2 |

When `is_eligible_checkout` is true you **must** also provide `seller_tos` and
`seller_privacy_policy` URLs. Useful optionals: `sale_price`, `gtin` (8–14
digits), `condition`, `group_id` (variants), `return_deadline_in_days`,
`star_rating`, `review_count`.

Validate before every upload:

```bash
python3 scripts/validate_feed.py feed.json          # array
python3 scripts/validate_feed.py feed.ndjson        # one object per line
```

It checks required fields, char limits, the availability enum, the
`price` "amount ISO4217" format, ISO-2 country codes, and the checkout ToS/
privacy dependency. Exit 0 = clean, 1 = issues printed per row.

## Recipe 2 — Implement the merchant checkout endpoints

The agent (ChatGPT) is the client; **you implement the server**. All under
`openapi.agentic_checkout.yaml`:

| method | path | purpose |
|--------|------|---------|
| `POST` | `/checkout_sessions` | create — return `201` with authoritative cart |
| `POST` | `/checkout_sessions/{id}` | update items / address / fulfillment option |
| `GET`  | `/checkout_sessions/{id}` | retrieve current state |
| `POST` | `/checkout_sessions/{id}/complete` | apply payment, create the order |
| `POST` | `/checkout_sessions/{id}/cancel` | cancel if not completed |

Your response is the source of truth for pricing, tax, shipping and totals — the
agent renders exactly what you return. Session `status` moves through:
`incomplete` → `not_ready_for_payment` / `ready_for_payment` → `completed`
(also `canceled`, `expired`, `requires_escalation`, `in_progress`). Always
recompute totals and `messages`/`fulfillment_options` server-side; never trust
the agent's view of price.

**Inbound headers on every request** (validate them all):

- `Authorization: Bearer <token>` — the shared key from onboarding.
- `API-Version` — e.g. `2026-04-17`; branch on it.
- `Idempotency-Key` — REQUIRED on create/complete; store the first response and
  replay it (echo `Idempotent-Replayed: true`) for repeats. Missing key → `400`.
- `Request-Id` — echo it back for correlation.
- `Signature` + `Timestamp` — HMAC over the raw body; verify before parsing.
- `Content-Type`, `Accept-Language`, `User-Agent`.

Verify the signature over the **raw bytes** with constant-time compare, and
reject stale timestamps to block replays:

```python
import hmac, hashlib, time

def verify(raw_body: bytes, sig_header: str, ts_header: str, secret: str,
           max_skew_s: int = 300) -> bool:
    if abs(time.time() - int(ts_header)) > max_skew_s:
        return False                      # replay / clock-skew guard
    signed = f"{ts_header}.".encode() + raw_body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header)  # never ==
```

(Confirm the exact signing string against your onboarding docs — schemes evolve;
the timestamp-dot-body construction and constant-time compare are the invariant.)

## Recipe 3 — Complete with a delegated Stripe payment token

On `POST /checkout_sessions/{id}/complete` the body carries `buyer` and
`payment_data`:

```json
{
  "buyer": { "first_name": "John", "last_name": "Smith", "email": "j@mail.com" },
  "payment_data": { "token": "spt_123", "provider": "stripe" }
}
```

The `spt_...` **Shared Payment Token** is a delegated, allowance-scoped
credential (max amount, currency, `checkout_session_id`, `merchant_id`,
`expires_at`) minted via the **Delegate Payment API** — the buyer's card is
tokenized once and constrained to this one order. Redeem it on your own Stripe
account as the payment method:

```python
import stripe                                   # pip install stripe
stripe.api_key = "sk_live_..."
intent = stripe.PaymentIntent.create(
    amount=session_total_minor_units,           # integer minor units, e.g. cents
    currency="usd",
    payment_method=payment_data["token"],       # the spt_ token
    confirm=True,
    off_session=True,
)
```

On success create the order, set session `status: "completed"`, and return the
order in the response. If the charge fails, keep the session
`ready_for_payment` and return a structured `Error` (`type`, `code`, `message`)
— do not fabricate an order.

If you are the PSP/processor side, you *implement* the delegate endpoint instead:
`POST /agentic_commerce/delegate_payment` (from `openapi.delegate_payment.yaml`)
tokenizes the `payment_method` (currently `card` only) under the `allowance`
and returns `{ "id": "vt_...", ... }`.

## Recipe 4 — Order lifecycle after completion

Report fulfillment back so ChatGPT can show status. Order-level `status`:
`created` → `confirmed` → `processing` → `shipped` → `completed` (or
`manual_review`, `canceled`). Line-item fulfillment events: `processing`,
`shipped`, `in_transit`, `out_for_delivery`, `ready_for_pickup`, `delivered`,
`failed`, `canceled`. Adjustments (`refund`, `return`, `exchange`, `dispute`)
carry their own `pending`/`completed`/`failed` status. **Always accept
unrecognized enum values gracefully** — the spec mandates forward compatibility.

## Verify

- `python3 scripts/validate_feed.py feed.json` exits 0 on a clean feed, 1 with
  per-row errors — run it in CI before every upload.
- Round-trip a session locally: create → update (add address, pick shipping) →
  complete with a Stripe **test** token → assert `status: completed` and an
  order id. Use Stripe test mode (`sk_test_...`, card `4242 4242 4242 4242`).
- Replay a create with the same `Idempotency-Key` → identical body +
  `Idempotent-Replayed: true`, no duplicate order.
- Tamper with one body byte → `verify()` returns `False`.
- Diff your handlers against the pinned spec:
  `curl -s https://raw.githubusercontent.com/agentic-commerce-protocol/agentic-commerce-protocol/main/spec/2026-04-17/openapi/openapi.agentic_checkout.yaml`

## Pitfalls

- **Missing `Idempotency-Key` handling** → duplicate charges/orders on agent
  retries. Persist keyed responses; missing key on create/complete is a `400`.
- **Trusting agent-supplied prices/totals.** Recompute everything server-side;
  your response is authoritative. The agent only renders what you return.
- **Signature over parsed JSON, not raw bytes** → intermittent failures from
  key reordering/whitespace. Capture the raw body before deserializing.
- **`price` format.** It is `"29.99 USD"` (amount + ISO 4217), not a bare number
  or minor units — but Stripe `amount` **is** integer minor units. Don't cross them.
- **Checkout-eligible items without `seller_tos` / `seller_privacy_policy`** are
  rejected at ingestion. The validator catches this.
- **Over-promising availability.** ChatGPT only surfaces buyable stock; stale
  `in_stock` on sold-out items causes failed completions and review flags.
- **Hardcoding the API version.** Read the `API-Version` header and branch;
  the spec is date-versioned and adds fields over time.
- **Assuming global rollout.** Instant Checkout is allowlisted and region-gated
  (US-first). Confirm eligibility rather than committing a public launch date.
- **Skipping the timestamp/skew check** leaves you open to signature replay.
