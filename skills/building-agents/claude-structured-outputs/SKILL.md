---
name: claude-structured-outputs
category: building-agents
description: >
  Force Claude to return JSON that provably matches your schema — the native Claude answer to instructor/BAML. Add `output_config.format` (JSON outputs) or `strict: true` tools to a Messages API call so grammar-constrained decoding guarantees conformance and you delete parse-retry loops, Pydantic try/excepts, and "please respond in JSON" prompt hacks. Covers Agent SDK `outputFormat` for validated multi-turn results, the supported JSON-Schema subset, SDK `parse()` helpers, and the failure modes (refusal, max_tokens, no streaming).
when_to_use:
  - You call the Claude Messages API and post-process the reply into a struct, DB row, or typed object
  - A pipeline has parse-retry loops or "if JSON invalid, ask again" glue you want to delete
  - You use tool calling and need the tool input arguments to be schema-valid every time
  - You run a Claude Agent SDK / Claude Code agent and want a validated JSON object as the final result
  - You are porting an instructor / BAML / OpenAI-json_schema pipeline onto Claude
  - You extract fields from documents or images and feed them straight into downstream code
when_not_to_use:
  - Building the Claude request plumbing itself (SDK setup, prompt caching, model choice) — use claude-api
  - Authoring a brand-new MCP tool server — use mcp-builder
  - Designing the agent loop / tool roster rather than its output shape — use claude-api or managed-agents-outcomes
  - You need streaming token output or Claude citations — structured outputs disable both
keywords:
  - structured-outputs
  - output_config
  - json_schema
  - strict-tool-use
  - claude-api
  - pydantic
  - zod
  - schema-conformance
  - constrained-decoding
  - instructor
  - baml
  - agent-sdk
  - output_format
  - data-extraction
similar_to:
  - claude-api
  - mcp-builder
  - managed-agents-outcomes
inputs_needed: An Anthropic API key (ANTHROPIC_API_KEY) or Bedrock/Vertex/Foundry access; a supported model (Sonnet 4.5 / Opus 4.5 / Haiku 4.5 or later); a JSON Schema (or Pydantic/Zod model) describing the target shape.
produces: A Messages API call (or Agent SDK query) that returns schema-conforming JSON, plus the SDK parse pattern to load it into a typed object with no defensive validation glue.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Claude Structured Outputs

Get JSON out of Claude that is **guaranteed** to match your schema, instead of prompting "return JSON" and hoping. On the Messages API, Anthropic constrains decoding to your grammar so the reply always parses; in the Agent SDK, the SDK validates the final result and re-prompts on mismatch. Either way you delete the parse-retry-validate scaffolding that instructor and BAML exist to hide.

## When to use

Reach for this the moment you find yourself calling `json.loads()` on a Claude reply, wrapping it in a `try/except`, or writing "respond ONLY with valid JSON, no markdown" in a prompt. It replaces those with a declared schema. Use **JSON outputs** for extraction/classification (you want one object back), and **strict tool use** when Claude is calling tools and you need the arguments valid every time.

## Prerequisites

- **Availability.** Went GA on the Claude Developer Platform on **2025-11-13** for **Claude Sonnet 4.5, Opus 4.5, and Haiku 4.5** (public beta before that was Sonnet 4.5 + Opus 4.1). Newer models generally support it too — confirm the current list at platform.claude.com/docs/en/build-with-claude/structured-outputs. Also on Amazon Bedrock, Google Vertex AI, and Microsoft Foundry, though the supported-model set lags the first-party API — verify per platform.
- **No beta header needed at GA.** The current request field is `output_config.format`. The old beta header `anthropic-beta: structured-outputs-2025-11-13` plus the top-level `output_format` param still work during a transition window, but write new code against `output_config.format`.
- **SDK versions.** The `messages.parse()` helper (Python) / `client.messages.parse()` with `zodOutputFormat` (TS), and the Agent SDK `outputFormat` option, need recent SDKs (`anthropic` Python/TS, `@anthropic-ai/claude-agent-sdk`). If `.parse()` is missing, upgrade or fall back to raw `output_config.format` + `json.loads(response.content[0].text)`.
- Set `ANTHROPIC_API_KEY`. `python3` here is 3.9 — `pip install --user anthropic pydantic` (or use TS/curl).

## Recipes

### 1. JSON outputs — raw schema (any language, shown as curl)

```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5",
    "max_tokens": 1024,
    "messages": [{"role":"user","content":"Extract the contact: Jane Doe, jane@acme.co"}],
    "output_config": {
      "format": {
        "type": "json_schema",
        "schema": {
          "type": "object",
          "properties": {
            "name":  {"type": "string"},
            "email": {"type": "string", "format": "email"}
          },
          "required": ["name", "email"],
          "additionalProperties": false
        }
      }
    }
  }'
```

The JSON string comes back in `response.content[0].text` — already valid, no fences, no prose. `json.loads()` it directly.

### 2. JSON outputs — Python with Pydantic (`parse()`)

```python
from anthropic import Anthropic
from pydantic import BaseModel

class Contact(BaseModel):
    name: str
    email: str

client = Anthropic()
resp = client.messages.parse(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Extract: Jane Doe, jane@acme.co"}],
    output_format=Contact,          # Pydantic model → schema, auto-generated
)
contact = resp.parsed_output        # already a typed Contact instance
print(contact.email)
```

Under the hood `parse()` derives the JSON Schema from the model, sends `output_config.format`, and validates the reply into `parsed_output`. No `json.loads`, no `Contact(**data)`, no retry loop.

### 3. JSON outputs — TypeScript with Zod

```typescript
import Anthropic, { zodOutputFormat } from "@anthropic-ai/sdk";
import { z } from "zod";

const Contact = z.object({ name: z.string(), email: z.string().email() });
const client = new Anthropic();

const resp = await client.messages.parse({
  model: "claude-sonnet-4-5",
  max_tokens: 1024,
  messages: [{ role: "user", content: "Extract: Jane Doe, jane@acme.co" }],
  output_config: { format: zodOutputFormat(Contact) },
});
resp.parsed_output.email; // typed
```

### 4. Strict tool use — valid tool args every call

Put `strict: true` on the tool; `input_schema` is enforced the same way. Use this in agent loops where a malformed tool call would break execution.

```json
{
  "model": "claude-sonnet-4-5",
  "max_tokens": 1024,
  "messages": [{"role":"user","content":"Book a flight to Tokyo on 2026-09-01"}],
  "tools": [{
    "name": "search_flights",
    "strict": true,
    "input_schema": {
      "type": "object",
      "properties": {
        "destination": {"type": "string"},
        "date": {"type": "string", "format": "date"}
      },
      "required": ["destination", "date"],
      "additionalProperties": false
    }
  }]
}
```

Strict and non-strict tools can coexist. Limits: max **20 strict tools** per request, **24 optional params** total, **16 params with union types**.

### 5. Agent SDK — validated result after multi-turn tool use

Different mechanism, same goal. The Agent SDK lets the agent use any tools, then **validates the final result against your schema client-side and re-prompts on mismatch** (not grammar-constrained decoding). The parsed object lands on `message.structured_output` of the `result` message.

```python
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

schema = {"type": "object",
          "properties": {"company_name": {"type": "string"},
                         "founded_year": {"type": "number"}},
          "required": ["company_name"]}

async for message in query(
    prompt="Research Anthropic and give key company info",
    options=ClaudeAgentOptions(output_format={"type": "json_schema", "schema": schema}),
):
    if isinstance(message, ResultMessage) and message.structured_output:
        print(message.structured_output)   # {'company_name': 'Anthropic', ...}
```

TypeScript uses `outputFormat: { type: "json_schema", schema }` and reads `message.structured_output` on `result`/`success`. On give-up the subtype is `error_max_structured_output_retries` — check it before blaming your schema (a model-fallback retraction can trigger the same subtype).

## Supported JSON Schema subset (know before you write the schema)

- **Supported:** `object` / `array` / `string` / `integer` / `number` / `boolean` / `null`; `enum`, `const`; `required`; `$ref` / `$defs` / `definitions` (internal only); `anyOf`; `default`; string `format` (`date-time`, `date`, `time`, `duration`, `email`, `hostname`, `uri`, `ipv4`, `ipv6`, `uuid`); simple `pattern` (quantifiers, char classes, groups).
- **`additionalProperties: false` is required on every object.** Omitting it is the #1 rejection cause.
- **NOT supported:** recursive schemas; numeric `minimum`/`maximum`/`multipleOf`; string `minLength`/`maxLength`; `maxItems`/`uniqueItems` (array `minItems` only 0 or 1); regex backreferences/lookahead/word-boundaries; external `$ref` URLs; `additionalProperties` set to a schema. Enforce those constraints in your own validation after parsing.

## Verify

1. **Conformance:** run recipe 1 and confirm `content[0].text` parses with `json.loads()` and has exactly your keys.
2. **Schema rejection:** drop `additionalProperties: false` and resend — expect an HTTP **400** naming the schema problem. This proves validation is active, not just prompted.
3. **Round-trip in code:** recipe 2/3 should return a typed object with no manual `json.loads`.
4. **Failure paths:** shrink `max_tokens` to ~20 and confirm `stop_reason: "max_tokens"` yields truncated (non-conforming) output — you must handle it (see Pitfalls).

## Pitfalls

- **Not a hallucination fix.** The schema guarantees the *shape*, never that field *values* are correct. Claude can still emit a plausible-but-wrong `founded_year`. Keep semantic checks.
- **`max_tokens` truncation breaks conformance.** If generation hits the cap, output is cut mid-JSON and won't parse — `stop_reason` is `"max_tokens"`, not `end_turn`. Size `max_tokens` generously and branch on `stop_reason`.
- **Refusals bypass the schema.** A safety refusal returns 200 with `stop_reason: "refusal"` and non-conforming content, and you are still billed. Handle it explicitly.
- **Enum capitalization drift.** Claude may return an enum value differing only in case. Compare case-insensitively or normalize.
- **No streaming, no citations.** Structured outputs are incompatible with streaming and with Claude citations (citations + `output_config.format` returns 400). If you need token streaming, you can't use this.
- **First-call latency + cache.** The grammar is compiled on first use (added latency) then cached ~24h; changing schema *structure* or the tool set invalidates it (name/description tweaks don't). Changing `output_config.format` also busts your prompt cache.
- **Property order isn't guaranteed useful.** Required props come first in schema order, then optional — don't rely on key order for anything semantic.
- **Agent SDK ≠ Messages API guarantee.** The Agent SDK path validates-and-reprompts (can still fail with `error_max_structured_output_retries`); only the Messages API path is grammar-constrained. Don't assume the same hard guarantee across both.
- **Don't over-constrain.** Deeply nested schemas with many required fields raise refusal/retry rates. Start minimal, mark uncertain fields optional, add depth only when needed.
