---
name: batch-api-offloader
category: model-routing
description: >
  Cut LLM spend in half on non-realtime work by moving it to the Anthropic Message Batches
  API or OpenAI Batch API for a guaranteed 50% discount. Packages many prompts into one
  batch job keyed by custom_id, submits, polls processing status until done, then reconciles
  results back to your inputs. Use when someone says "run this overnight", "batch these
  prompts", "50% off", "bulk classify/summarize", "offload to batch", or has thousands of
  independent, latency-tolerant calls.
when_to_use:
  - Bulk classification, summarization, extraction, or scoring over thousands of rows where a result within ~24h is fine
  - Large-scale evals or backfills where you want the built-in 50% batch discount, not synchronous pricing
  - '"Run these overnight / by tomorrow" or "we do not need it live" workloads'
  - Re-processing a whole dataset with a new prompt or model and reconciling outputs by id
  - Any many-independent-calls job where per-request latency does not matter but total cost does
when_not_to_use:
  - Live user-facing / interactive requests that need a response in seconds — use cross-provider-gateway
  - Picking which model or tier a single request should hit — use model-triage-router or model-cascade-escalation
  - Estimating token cost before you run anything — use llm-cost-estimator
  - Fanning one prompt to several models and merging — use mixture-of-models-ensemble
keywords: [batch api, message batches, 50% discount, custom_id, offload, bulk inference, jsonl, overnight, async llm, anthropic batch, openai batch, processing_status, results_url, reconcile, batch job, half price]
similar_to: [llm-cost-estimator, cross-provider-gateway, model-triage-router, best-model-per-step-pipeline]
inputs_needed:
  - Provider (Anthropic or OpenAI) and API key in env (ANTHROPIC_API_KEY / OPENAI_API_KEY)
  - Model name and per-request params (system, messages, max_tokens)
  - The list of input items, each with a stable unique id you control (used as custom_id)
produces: A submitted batch job plus a reconciled results file/dict mapping each custom_id to its succeeded/errored/expired result
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Batch API Offloader

Move latency-tolerant LLM work off the synchronous endpoints and onto the provider's
**Batch API** for a flat **50% discount**. You pack N prompts into one job, each tagged
with a `custom_id` you choose, submit, poll until processing ends, then join results back
to your inputs by that id.

## When to use

Any job that is (1) many independent calls and (2) fine to finish within the provider's
window (most batches finish in well under an hour; the SLA is 24h). Evals, backfills,
bulk classify/summarize/extract, dataset re-scoring. If it must be live, this is the wrong
skill — see `cross-provider-gateway`.

## Prerequisites

- Python 3.9+ with the official SDK: `pip install anthropic` and/or `pip install openai`.
- API key exported: `export ANTHROPIC_API_KEY=...` or `export OPENAI_API_KEY=...`.
- No special account flag is needed; batch endpoints are on by default.

Key limits (verify against current docs, but as of 2026-07):

| | Anthropic Message Batches | OpenAI Batch |
|---|---|---|
| Discount | 50% off input+output | 50% off |
| Max per batch | 100,000 requests **or** 256 MB | 50,000 requests, 200 MB file |
| Completion window | up to 24h (`processing_status`) | `completion_window="24h"` |
| Results retention | 29 days | download from `output_file_id` |
| Key field | `custom_id` (`^[a-zA-Z0-9_-]{1,64}$`) | `custom_id` (your string) |

`max_tokens` must be >= 1 per request (Anthropic). `custom_id`s must be unique within a batch.

## Recipe A — Anthropic Message Batches

The SDK takes params inline; **no JSONL file to upload**. Each entry is `{custom_id, params}`
where `params` is exactly a normal Messages call.

```python
import anthropic
client = anthropic.Anthropic()

# 1. Build requests — custom_id is YOUR stable key back to the source row.
items = [{"id": "row-1", "text": "..."}, {"id": "row-2", "text": "..."}]
requests = [
    {
        "custom_id": it["id"],  # must match ^[a-zA-Z0-9_-]{1,64}$
        "params": {
            "model": "claude-sonnet-4-5",
            "max_tokens": 256,
            "messages": [{"role": "user", "content": f"Classify: {it['text']}"}],
        },
    }
    for it in items
]

# 2. Submit
batch = client.messages.batches.create(requests=requests)
print(batch.id, batch.processing_status)  # e.g. msgbatch_..., "in_progress"
```

Poll until `processing_status == "ended"`, then stream results. Each result carries the
`custom_id` and a `result.type` of one of four values: `succeeded`, `errored`, `canceled`,
`expired`.

```python
import time
# 3. Poll (exponential-ish backoff; most finish fast)
while True:
    b = client.messages.batches.retrieve(batch.id)
    if b.processing_status == "ended":
        break
    print(b.request_counts)  # {processing, succeeded, errored, canceled, expired}
    time.sleep(30)

# 4. Reconcile — join back to source by custom_id
out = {}
for r in client.messages.batches.results(batch.id):  # streams the .jsonl results
    if r.result.type == "succeeded":
        out[r.custom_id] = r.result.message.content[0].text
    elif r.result.type == "errored":
        out[r.custom_id] = {"error": r.result.error.type}
    else:  # canceled | expired
        out[r.custom_id] = {"status": r.result.type}
```

Note: results are **not** guaranteed to be in submission order — always key by `custom_id`.

## Recipe B — OpenAI Batch

OpenAI is file-based: write a JSONL, upload it, create the batch pointing at it.

```python
import json, time
from openai import OpenAI
client = OpenAI()

items = [{"id": "row-1", "text": "..."}, {"id": "row-2", "text": "..."}]

# 1. Write JSONL — one request per line
with open("batch_in.jsonl", "w") as f:
    for it in items:
        f.write(json.dumps({
            "custom_id": it["id"],
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "gpt-4.1-mini",
                "messages": [{"role": "user", "content": f"Classify: {it['text']}"}],
                "max_tokens": 256,
            },
        }) + "\n")

# 2. Upload + create
up = client.files.create(file=open("batch_in.jsonl", "rb"), purpose="batch")
batch = client.batches.create(
    input_file_id=up.id,
    endpoint="/v1/chat/completions",
    completion_window="24h",
)

# 3. Poll: validating -> in_progress -> finalizing -> completed (or failed/expired/cancelled)
while True:
    b = client.batches.retrieve(batch.id)
    if b.status in ("completed", "failed", "expired", "cancelled"):
        break
    print(b.status, b.request_counts)
    time.sleep(30)

# 4. Reconcile — download output_file_id, key by custom_id
out = {}
if b.output_file_id:
    for line in client.files.content(b.output_file_id).text.splitlines():
        rec = json.loads(line)
        if rec.get("error") is None and rec["response"]["status_code"] == 200:
            out[rec["custom_id"]] = rec["response"]["body"]["choices"][0]["message"]["content"]
        else:
            out[rec["custom_id"]] = {"error": rec.get("error")}
# Failed rows land in b.error_file_id (same JSONL shape) — download and merge similarly.
```

## Helper

`scripts/batch_submit.py` wraps both providers: give it a JSONL of `{id, prompt}` items and
it submits, polls, and writes a reconciled `results.jsonl`. Run `python3 scripts/batch_submit.py --help`.

## Verify

- Submission returns an `id` and a non-terminal status — the job was accepted.
- After polling ends, `len(out) == len(items)` and every source id is a key. A missing id
  means a malformed `custom_id` (Anthropic) or a dropped line (OpenAI) — inspect the error file.
- Spot-check the cost: batch line items on your usage dashboard should be ~50% of the
  synchronous rate for the same model.

## Pitfalls

- **Never rely on result order.** Always map by `custom_id`. Anthropic streams results in
  completion order, not submission order.
- **`custom_id` must be unique and valid.** Anthropic enforces `^[a-zA-Z0-9_-]{1,64}$`; a
  raw email or path will be rejected. Hash or slugify long/odd ids and keep a lookup table.
- **Validation is deferred.** Anthropic validates each request's `params` asynchronously —
  a bad body shows up only in that row's `errored` result at the end, not at submit time.
  Sanity-check one request against the normal Messages API first.
- **Partial failure is normal.** Some rows `errored` or `expired` (24h window elapsed for
  stragglers) while others succeed. Handle every result type; re-submit only the failures.
- **Not for streaming or tools that need turns.** Batch is one-shot per request; multi-turn
  tool loops don't fit — keep those synchronous.
- **`max_tokens: 0` is unsupported inside an Anthropic batch** (cache pre-warming won't work).
- **Results expire.** Anthropic download window is 29 days; OpenAI files persist but pull
  `output_file_id`/`error_file_id` promptly and store your own copy.
