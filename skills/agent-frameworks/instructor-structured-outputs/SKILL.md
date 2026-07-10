---
name: instructor-structured-outputs
category: agent-frameworks
description: >
  Get reliable, typed data out of ANY LLM by declaring a Pydantic model as response_model — Instructor patches
  the provider client so a bad/invalid response is automatically re-asked (max_retries) with the validation error
  fed back, until it parses. Provider-agnostic via from_provider("openai/…", "anthropic/…", "google/…",
  "mistral/…", "ollama/…"). Use when the user says "structured output", "get JSON out of the LLM", "Pydantic
  response_model", "validate LLM output", "instructor library", "extract structured data", "function calling on
  OpenAI/Gemini/Mistral/local", "retry on validation error", or "stream partial objects".
when_to_use:
  - "You need one LLM call to return a validated Pydantic object (extraction, classification, tagging), not free text"
  - "User names Instructor, response_model, or 'patch the OpenAI/Gemini client for structured output'"
  - "Output must satisfy real constraints (enums, ranges, regex) and you want auto-retry on failure, not manual parsing"
  - "You're on a non-Claude provider (OpenAI/Gemini/Mistral/Groq/Ollama/local) and want the same structured-output ergonomics"
  - "You want to stream a partial object as it's generated, or stream an iterable of extracted records"
  - "You need a provider-agnostic extraction layer that survives swapping models with one string change"
when_not_to_use:
  - "You're on Anthropic/Claude and want first-party tool use + caching — use claude-api (Instructor works too, but that skill is native)"
  - "You want a compile-your-prompt-schema DX with a dedicated language — use baml-structured-prompts"
  - "You want a full typed agent with tool-calling loops and dependency injection — use pydantic-ai-typed-agents or openai-agents-sdk"
  - "You want prompts/few-shots auto-tuned against a metric — use dspy-program-optimization"
  - "You need durable, checkpointed multi-step workflows — use langgraph-durable-workflows"
keywords: [instructor, structured outputs, response_model, pydantic, from_provider, max_retries, field_validator, create_partial, create_iterable, function calling, json mode, llm validation, extraction, openai, gemini, mistral, ollama, retry on validation error, typed llm output]
similar_to: [baml-structured-prompts, pydantic-ai-typed-agents, dspy-program-optimization, openai-agents-sdk]
inputs_needed:
  - "The target schema — what fields/types you want back (draft the Pydantic model)"
  - "Provider + model string (e.g. openai/gpt-4o-mini, anthropic/claude-3-5-sonnet, ollama/llama3.2) and its API key"
  - "Whether you need streaming (partial object vs iterable of records) and how many retries are acceptable"
produces: A patched Instructor client that returns validated Pydantic objects with auto-retry, plus runnable extraction code
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Instructor — Structured Outputs on Any Provider

Instructor patches a provider's chat client so you pass `response_model=YourPydanticModel` and get back a
**validated instance** — not a string you have to `json.loads` and pray over. If the model returns something
that fails Pydantic validation, Instructor re-prompts with the error attached and tries again (`max_retries`).
One `from_provider(...)` string swaps OpenAI ↔ Gemini ↔ Mistral ↔ local with no other code change.

## When to use

You want typed data out of a single LLM call and you care that it's *correct*. If you need multi-step tool
loops, prompt optimization, or durable workflows, see the "when_not_to_use" alternatives above.

## Prerequisites

```bash
pip install -U instructor          # pulls pydantic v2
# Provider SDKs are extras — install the one you use:
pip install -U instructor openai            # openai/… (also Groq/Together/local OpenAI-compatible)
pip install -U "instructor[anthropic]"      # anthropic/…
pip install -U "instructor[google-genai]"   # google/…  (Gemini)
pip install -U "instructor[mistral]"        # mistral/…
# Ollama needs no extra — it speaks the OpenAI protocol locally (ollama serve).
```

Set the provider's key: `export OPENAI_API_KEY=…` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` / `MISTRAL_API_KEY`.
`from_provider` reads the standard env var automatically; pass `api_key=` to override.

## Recipe 1 — Basic validated extraction

```python
import instructor
from pydantic import BaseModel, Field

class User(BaseModel):
    name: str
    age: int = Field(ge=0, le=130)          # constraints are enforced; violations trigger a retry

client = instructor.from_provider("openai/gpt-4o-mini")   # swap string to change provider

user = client.chat.completions.create(
    response_model=User,
    messages=[{"role": "user", "content": "Jason is twenty-five years old."}],
    max_retries=3,                          # re-ask up to 3x on a validation failure
)
assert isinstance(user, User)
print(user.name, user.age)                  # -> Jason 25
```

`from_provider("anthropic/claude-3-5-sonnet")`, `"google/gemini-2.0-flash"`, `"mistral/mistral-large-latest"`,
or `"ollama/llama3.2"` are drop-in replacements for that one line.

## Recipe 2 — Custom validators that steer the retry

A raised `ValueError` becomes the correction message the model sees on the next attempt. Use
`field_validator` for one field, `model_validator` for cross-field rules.

```python
from pydantic import BaseModel, field_validator

class Extraction(BaseModel):
    summary: str
    @field_validator("summary")
    @classmethod
    def no_pronouns(cls, v: str) -> str:
        if " it " in f" {v.lower()} ":
            raise ValueError("Rewrite without the pronoun 'it' — name the subject explicitly.")
        return v
```

For LLM-based checks (e.g. "must not contain PII"), use `instructor.llm_validator("...", client=client)` as an
`AfterValidator`. Note: **validators do not run on streamed partials** (Recipe 4) — fields are Optional mid-stream.

## Recipe 3 — Enums, nesting, and the `Maybe` "not found" guard

```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel
import instructor

class Priority(str, Enum):
    low = "low"; medium = "medium"; high = "high"

class Ticket(BaseModel):
    title: str
    priority: Priority
    assignee: Optional[str] = None

# Maybe[T] avoids hallucinated answers when the data isn't present:
MaybeTicket = instructor.Maybe(Ticket)
res = client.chat.completions.create(
    response_model=MaybeTicket,
    messages=[{"role": "user", "content": "Bug: login button dead, urgent, give to Sam."}],
)
if res.result:        # .result is None when the model reports .error / not found
    print(res.result.priority)
```

## Recipe 4 — Streaming (partial object, then iterable of records)

```python
# Stream ONE object as its fields fill in (all fields become Optional mid-stream):
for partial in client.chat.completions.create_partial(
    response_model=User,
    messages=[{"role": "user", "content": "Jason, 25, from Seattle."}],
):
    print(partial)     # User(name=None, age=None) -> User(name='Jason', age=None) -> full

# Stream a LIST — each complete record is yielded as soon as it's parsed:
for u in client.chat.completions.create_iterable(
    response_model=User,
    messages=[{"role": "user", "content": "Extract: Jason 25, Mary 32, Ann 19."}],
):
    print(u)           # one User at a time
```

Equivalent explicit form: `response_model=instructor.Partial[User]` or `Iterable[User]` with `stream=True`
passed to `.create(...)`.

## Recipe 5 — Async + inspecting the raw completion

```python
import asyncio, instructor

aclient = instructor.from_provider("openai/gpt-4o-mini", async_client=True)

async def main():
    # create_with_completion returns (validated_model, raw_provider_completion) — for token/usage logging:
    user, completion = await aclient.chat.completions.create_with_completion(
        response_model=User,
        messages=[{"role": "user", "content": "Jason is 25."}],
    )
    print(user, completion.usage)

asyncio.run(main())
```

## Recipe 6 — See the retries (hooks)

```python
def on_error(err): print("validation failed, retrying:", err)
client.on("parse:error", on_error)          # also: "completion:kwargs", "completion:response"
```

## Verify

```python
# It genuinely round-trips and validates — a bad model config raises, it never silently returns a dict:
u = client.chat.completions.create(response_model=User,
        messages=[{"role": "user", "content": "Jason 25"}])
assert isinstance(u, User) and u.age == 25
```

- On repeated failure Instructor raises `instructor.exceptions.InstructorRetryException` after `max_retries`;
  catch it and inspect `.n_attempts` / `.last_completion` rather than assuming success.
- Confirm the provider extra is installed: `python -c "import instructor; print(instructor.__version__)"`.

## Pitfalls

- **`response_model` is required for validation.** Omit it and you get the raw provider response — no retries, no typing.
- **Validators are skipped on partials.** During `create_partial`/streaming, fields are Optional and constraints
  don't run; validate the final assembled object yourself if it matters.
- **`max_retries` costs tokens.** Each retry is a full new call. Keep schemas tight and constraints meaningful;
  don't set retries to 10 to paper over a vague prompt.
- **Provider modes differ.** OpenAI/Anthropic use tool-calling by default; some models only support JSON mode.
  Pass `mode=instructor.Mode.JSON` (or `TOOLS`, `MD_JSON`) to `from_provider` if a model rejects the default.
- **Gemini/Mistral/Ollama need their extra + a reachable endpoint.** For Ollama, `ollama serve` must be running
  and the model pulled (`ollama pull llama3.2`).
- **Don't hand-roll JSON parsing around it.** The whole point is that `create(response_model=…)` already returns
  the typed object — re-`json.loads`-ing its `.model_dump()` is a smell.
- **This is single-call extraction, not an agent.** No built-in tool loop or memory — compose it yourself or
  reach for pydantic-ai-typed-agents / openai-agents-sdk.
