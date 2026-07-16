---
name: claude-programmatic-tool-calling
category: building-agents
description: >-
  Let Claude orchestrate your tools from Python inside the code-execution sandbox instead of
  one model round-trip per call. Add the code_execution tool, tag each tool with
  allowed_callers:["code_execution_20260120"], and Claude writes a script that loops, filters,
  and aggregates tool results — returning only the distilled answer while intermediate data
  never enters context. Use when an agent fans out across many records/endpoints, when tool
  results are huge and must be filtered before Claude reads them, or when 10-49 tools are
  bloating input tokens. Grounded on Anthropic's advanced-tool-use docs: real caller/container
  fields, the tool_result-only continuation rule, and honest token-savings numbers.
when_to_use:
  - Agent must fan out the same tool across many items (check 50 endpoints, look up 20 records) in one pass
  - Tool results are large and can be filtered/aggregated/summarised in code before Claude reads them
  - A tools array of ~10-49 definitions is bloating input tokens and you want 20-40% savings
  - Agentic search/retrieval where iterative querying and result filtering dominate the loop
  - You want conditional logic or early-termination across tool calls without re-sampling Claude between each
when_not_to_use:
  - Building a plain Claude tool-use / SDK app with no code execution — use claude-api
  - You need a generic secure runtime for agent-written code (E2B/Modal/Daytona) — use agent-code-sandbox
  - Designing tool names and JSON schemas from scratch — use mcp-builder
  - Strictly sequential workflows where each call needs Claude to reason over the last result first (no benefit; can cost ~8% more)
keywords:
  - programmatic-tool-calling
  - code-execution
  - allowed-callers
  - anthropic
  - claude-api
  - tool-use
  - token-reduction
  - agent
  - sandbox
  - caller-field
  - container
  - fan-out
  - asyncio
  - server-tool-use
  - context-engineering
similar_to:
  - claude-api
  - agent-code-sandbox
  - mcp-builder
  - managed-agents-outcomes
inputs_needed: Anthropic API key; a compatible model (Opus 4.5+/Sonnet 4.5+); one or more custom tools with JSON output whose results your client can serve; a client loop that returns tool_result blocks
produces: A configured Messages request where Claude calls tools from code — plus a working client loop that reuses the container, answers programmatic tool_use blocks with tool_result-only messages, and measures the token delta
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Claude Programmatic Tool Calling

Give Claude the **code execution** tool, mark your own tools as callable *from code*, and Claude
stops asking for tools one at a time. Instead it writes a Python script that runs your tools in a
loop, filters/aggregates the results in-sandbox, and returns only the distilled answer. The raw
intermediate results never hit the model's context window — that is where the token savings come from.

Concrete example from Anthropic's docs: checking budget compliance across 20 employees the normal
way needs 20 model round-trips and drags thousands of expense line items through context. With
programmatic tool calling a single script runs all 20 lookups, filters, and returns only the people
who exceeded their limit — shrinking what Claude reasons over from hundreds of KB to a few lines.

## When to use

- Fan-out / parallel operations over many items (50 endpoints, 20 records).
- Large tool results that can be filtered/aggregated **before** reaching context.
- Agentic search/retrieval where iterative querying + filtering dominate.
- A `tools` array of ~10-49 definitions that is inflating input tokens.

Do **not** reach for it on strictly sequential single-call turns — the docs measured that shape as
**~8% more expensive**, not cheaper. If unsure, measure billed input tokens with and without
`allowed_callers` on representative traffic before enabling broadly.

## Prerequisites (read the honest bits)

- **Anthropic API key** and the SDK (`anthropic` Python/TS, or raw HTTP). This is a Claude API /
  first-party feature — it is *not* a Claude Code or MCP-connector capability.
- **Code execution tool must be enabled** — programmatic calling is layered on top of it and bills
  under [code execution pricing](https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool#usage-and-pricing).
- **Model + tool version.** Requires code-execution tool version `code_execution_20260120` or later.
  Supported models include Opus 4.5+, Sonnet 4.5+, and the 5-series (Opus 4.8, Sonnet 5, etc.).
  **Version churn is real:** the original Nov-2025 launch (the cited engineering post) used the beta
  tool id `code_execution_20250825` behind header `anthropic-beta: advanced-tool-use-2025-11-20`.
  That has since GA'd; current docs use `code_execution_20260120` (and `..._20260521`, interchangeable
  in `allowed_callers`) with **no beta header shown**. Confirm the exact id against the live docs for
  your SDK version before shipping — pin one and don't mix carelessly.
- **Availability:** Claude API, Claude Platform on AWS, and Microsoft Foundry (Hosted-on-Anthropic
  deployment only). **Not** on Amazon Bedrock or Google Cloud (as of this writing).
- **Not ZDR-eligible.** Container data (artifacts, outputs) is retained up to 30 days; do not use it
  under a Zero-Data-Retention requirement.
- **The sandbox language is Python.** Your tools are surfaced to Claude's code as **async** Python
  functions.

## How it actually works

1. Claude writes Python that calls your tool as a function (possibly in a loop / with pre- and
   post-processing) and runs it in the sandbox container.
2. When that code calls a tool, execution **pauses** and the API returns a `tool_use` block whose
   `caller` names the code-execution run — response `stop_reason: "tool_use"`.
3. **Your client executes the tool and returns a `tool_result`.** The result is fed back into the
   *running code*, not into Claude's context.
4. The code resumes, may pause again for more calls, and when it finishes Claude sees only the final
   `stdout` (the `code_execution_tool_result`) and continues the turn.

Tools are exposed as async functions that take a single dict of args and return a **string** (the
text of the `tool_result` you send back). Claude's code awaits them with top-level `await`, runs
them in parallel with `asyncio.gather`, and parses what it needs, e.g.
`rows = json.loads(await query_database({"sql": "<sql>"}))`.

## Recipe 1 — Configure the request

Add the code-execution tool, then tag each custom tool with `allowed_callers`.

```python
import anthropic
client = anthropic.Anthropic()

TOOL_VERSION = "code_execution_20260120"  # pin one; confirm against live docs

resp = client.messages.create(
    model="claude-opus-4-8",           # or sonnet-5 / opus-4-5 etc.
    max_tokens=4096,
    messages=[{"role": "user",
               "content": "Query sales for West, East and Central regions, "
                          "then tell me which region had the highest revenue"}],
    tools=[
        {"type": TOOL_VERSION, "name": "code_execution"},   # enables the sandbox
        {
            "name": "query_database",
            # Describe the OUTPUT format precisely — Claude deserialises it in code.
            "description": "Execute a SQL query. Returns a JSON list of row objects "
                           "with fields: region (str), revenue (int).",
            "input_schema": {
                "type": "object",
                "properties": {"sql": {"type": "string", "description": "SQL to run"}},
                "required": ["sql"],
            },
            "allowed_callers": [TOOL_VERSION],   # <-- opt this tool into code calling
        },
    ],
)
```

`allowed_callers` values:
- `["direct"]` — Claude calls it the traditional way (default when omitted).
- `["code_execution_20260120"]` — Claude is guided to call it **only from code**.
- `["direct","code_execution_20260120"]` — both. The docs advise picking **one** for clearer guidance.

`allowed_callers` is guidance validated against `tool_choice`, **not a security boundary** — your
client must still be ready to handle a `direct` `tool_use` for any tool it defines.

## Recipe 2 — The continuation loop (this is the part people get wrong)

When the response pauses, you must answer *every* pending programmatic `tool_use` and re-send the
whole conversation. Three rules the API enforces:

- **`tool_result`-only message.** The user message carrying your results may contain **only**
  `tool_result` blocks — no `text`, not even after the results. (This rule applies only to
  programmatic calls; normal client-side tool use still allows trailing text.)
- **Text-only result content.** Each `tool_result.content` must be a string or `text` blocks. Images,
  documents, other block types are rejected.
- **Pass the `container` id** from the paused response, and re-send the **same `tools` array**
  (the code-execution tool must still be present so the paused code can resume).

```python
def run_ptc(client, messages, tools, tool_impls, model="claude-opus-4-8"):
    container = None
    while True:
        kwargs = dict(model=model, max_tokens=4096, messages=messages, tools=tools)
        if container:
            kwargs["container"] = container          # REQUIRED while calls are pending
        resp = client.messages.create(**kwargs)
        if getattr(resp, "container", None):
            container = resp.container.id
        messages.append({"role": "assistant", "content": resp.content})

        # Collect programmatic tool calls: tool_use blocks whose caller is code execution
        pending = [b for b in resp.content
                   if getattr(b, "type", None) == "tool_use"
                   and getattr(getattr(b, "caller", None), "type", "") != "direct"]
        if resp.stop_reason != "tool_use" or not pending:
            return resp                               # end_turn: final answer is in resp

        results = []
        for b in pending:
            try:
                out = tool_impls[b.name](b.input)     # your code runs the tool
            except Exception as e:
                out = f"Error: {e}"                   # errors surface in the code's stderr
            results.append({"type": "tool_result", "tool_use_id": b.id,
                            "content": str(out)})       # MUST be a string
        messages.append({"role": "user", "content": results})   # tool_result ONLY
```

Return results **fast**: a pending call raises `TimeoutError` inside Claude's code after ~4 minutes,
and idle containers are reclaimed after ~5 minutes (watch the `expires_at` field). Reuse the
`container` id across related requests to keep sandbox state.

## Recipe 3 — What Claude's code looks like

You don't write this — Claude does — but design your tools so these patterns are cheap:

```python
# Fan-out: N regions -> 1 model round-trip
results = {r: sum(row["revenue"] for row in json.loads(await query_database({"sql": f"... {r} ..."})))
           for r in ["West","East","Central","North","South"]}
print(max(results.items(), key=lambda kv: kv[1]))          # only the winner returns to context

# Early termination
for ep in ["us-east","eu-west","apac"]:
    if await check_health({"endpoint": ep}) == "healthy":
        print(f"healthy: {ep}"); break

# Filter before returning
errors = [l for l in (await fetch_logs({"server_id":"srv-01"})).splitlines() if "ERROR" in l]
print(f"{len(errors)} errors"); [print(e) for e in errors[-10:]]   # last 10 only
```

## Verify

- **Confirm it went programmatic:** in the paused response, the `tool_use` block has a `caller` of
  `{"type":"code_execution_20260120","tool_id":"srvtoolu_..."}` where `tool_id` matches the
  `server_tool_use` (`code_execution`) block's `id`. A `caller.type == "direct"` means Claude did
  *not* use code — recheck your `allowed_callers`.
- **Confirm the savings:** run the same task with and without `allowed_callers` and compare
  `response.usage.input_tokens`. Docs report ~38% fewer billed input tokens on a 75-tool benchmark
  (no accuracy change) and 20-40% typical for 10-49 tools; the engineering post cited 43,588 → 27,297
  tokens (~37%). Tool results from programmatic calls **do not** count toward token usage — only the
  final code output and Claude's response do.
- **Confirm the final answer** arrives with `stop_reason: "end_turn"` and a
  `code_execution_tool_result` block containing your aggregated `stdout`.

## Pitfalls

- **Vague output docs = no deserialisation.** Claude parses results in code, so spell out the JSON
  shape and field types in the tool `description`. Return concise, machine-readable data.
- **Trailing text in the continuation.** Adding any `text` block alongside `tool_result` when
  answering a programmatic call is a hard error. Results-only.
- **Dropping the `container` id.** A continuation with pending programmatic calls but no `container`
  is rejected. Always thread it back.
- **`tool_choice` can't force it.** You cannot force programmatic calling of a specific tool via
  `tool_choice`; naming a tool whose `allowed_callers` omits `"direct"` returns `400
  invalid_request_error`. Add `"direct"` or drop it from `tool_choice`.
- **Unsupported combos:** `strict: true` (structured outputs) tools, `disable_parallel_tool_use:
  true`, and **MCP-connector tools** cannot be called programmatically. A recursive `$ref` in a
  tool's `input_schema` fails with `Circular $ref detected` — keep that tool direct-only or unroll
  the schema.
- **Wrong workload.** Sequential single-call turns, or a couple of small tool calls on turn one, can
  cost *more* than they save (container + script overhead). This is a fan-out / big-result play.
- **Treating results as safe.** Programmatic tool results come back as strings that flow into a code
  environment — validate/escape anything sourced from users or external APIs to avoid injection.
