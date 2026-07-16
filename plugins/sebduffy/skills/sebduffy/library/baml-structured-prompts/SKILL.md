---
name: baml-structured-prompts
category: agent-frameworks
description: >
  Author LLM functions in BAML (BoundaryML) — a type-safe DSL where input/output
  classes, enums, and jinja prompt templates compile to a typed client (Python, TS,
  Ruby, Go). Schema-Aligned Parsing repairs malformed model output (unquoted keys,
  markdown fences, chain-of-thought yapping) into the declared schema with no retries.
  Use when you want reliable structured extraction, function-calling, or classification
  without hand-writing JSON prompts or brittle regex parsers. Triggers: "BAML",
  "baml_src", "boundaryml", "schema-aligned parsing", "type-safe prompts",
  ".baml file", "extract structured data from LLM", "typed LLM client".
when_to_use:
  - "I want type-safe structured outputs from an LLM without writing raw JSON prompts"
  - "The model keeps returning malformed JSON / markdown-fenced JSON that breaks my parser"
  - "I need one prompt definition callable from Python AND TypeScript with the same types"
  - "Set up a .baml / baml_src project and generate a typed baml_client"
  - "Extract a resume/invoice/entity into a typed class, or classify into an enum"
  - "Add fallback + retry across OpenAI/Anthropic to one LLM function"
when_not_to_use:
  - "You want Pydantic-native output in a pure-Python codebase with no build step → instructor-structured-outputs"
  - "You want a full typed agent loop with tools and deps in Python → pydantic-ai-typed-agents"
  - "You want to auto-optimize prompts/few-shots by compiling against a metric → dspy-program-optimization"
  - "You need durable multi-step stateful workflows/graphs → langgraph-durable-workflows"
keywords: [baml, boundaryml, baml-py, baml_src, baml_client, baml-cli, schema-aligned parsing, sap, structured output, typed prompts, llm function, jinja prompt, ctx.output_format, structured extraction, function calling, classifier, dsl]
similar_to: [instructor-structured-outputs, pydantic-ai-typed-agents, dspy-program-optimization]
inputs_needed:
  - Target language for the generated client (python, typescript, ruby, go)
  - The output shape you want (fields/types) and the LLM provider + model + API key env var
  - Whether streaming, fallback, or retry are required
produces: A baml_src/ project (functions, classes, clients, tests) that compiles to a typed baml_client callable from your app
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# BAML Structured Prompts

BAML (Basically A Made-up Language) is a DSL from BoundaryML for defining LLM
functions. You declare input/output **classes** and **enums**, write the prompt as a
jinja template, and `baml-cli generate` produces a **typed client** in your language.
At runtime, **Schema-Aligned Parsing (SAP)** coerces whatever the model returns into
your schema — no JSON mode required, no retry loop, ~sub-10ms Rust parser.

## When to use

Reach for BAML when you want the reliability of typed outputs but hate hand-writing
`response_format` JSON, escaping schemas into prompt strings, or regex-repairing broken
JSON. One `.baml` definition → the same types in Python, TypeScript, Ruby, and Go.

## Prerequisites

- An LLM provider API key (OpenAI, Anthropic, Google, Ollama, etc.) in your env.
- The runtime package for your language:
  - **Python** (3.8+): `pip install baml-py` (or `uv add baml-py` / `poetry add baml-py`)
  - **TypeScript**: `npm install @boundaryml/baml`
- The **BAML VSCode extension** is strongly recommended — it gives a prompt playground,
  live preview of the rendered prompt, and auto-runs `generate` on save.
- `baml-cli` ships with the runtime package (call via `baml-cli …` after install; in a
  fresh venv use `python -m baml_py … ` if the shim isn't on PATH, or `npx baml-cli` for TS).

## Steps

### 1. Scaffold the project

```bash
pip install baml-py           # Python; TS: npm install @boundaryml/baml
baml-cli init                 # creates ./baml_src with a starter generator + example
```

`baml_src/` holds your `.baml` source. Never edit the generated `baml_client/` by hand.

### 2. Set the generator (target language)

In `baml_src/generators.baml`:

```baml
generator target {
  output_type "python/pydantic"   // or "typescript" | "ruby/sorbet" | "go"
  output_dir "../"                // baml_client lands next to baml_src
  version "0.x.x"                 // must match your installed baml-py version
}
```

### 3. Define a client (provider + model)

```baml
client<llm> GPT4o {
  provider openai
  options {
    model "gpt-4o"
    api_key env.OPENAI_API_KEY
    temperature 0.0
  }
}

client<llm> Claude {
  provider anthropic
  options {
    model "claude-sonnet-4-5"
    api_key env.ANTHROPIC_API_KEY
    max_tokens 1024
  }
}
```

Resilience — wrap clients in a fallback (try in order) or round-robin (load balance),
and attach a retry policy:

```baml
retry_policy Exponential {
  max_retries 3
  strategy { type exponential_backoff  delay_ms 200  multiplier 1.5 }
}

client<llm> Resilient {
  provider fallback
  options { strategy [GPT4o, Claude] }
  retry_policy Exponential
}
```

### 4. Declare types and the function

`{{ ctx.output_format }}` injects the schema instructions BAML derives from your return
type — this is the mechanism, do not hand-write the schema. `{{ _.role("user") }}`
starts a user turn; text before the first role is the system prompt.

```baml
class Resume {
  name string
  email string?                        // ? = optional
  skills string[]
  seniority Seniority
}

enum Seniority {
  Junior
  Mid
  Senior
}

function ExtractResume(raw: string) -> Resume {
  client Resilient
  prompt #"
    Extract the candidate's details from the resume below.

    {{ ctx.output_format }}

    {{ _.role("user") }}
    {{ raw }}
  "#
}
```

### 5. Generate the typed client

```bash
baml-cli generate                 # writes ./baml_client (regenerate after every .baml edit)
```

Commit `baml_src/`; the generated `baml_client/` can be committed or gitignored + built in CI.

### 6. Call it from your app

Python (sync / async / streaming):

```python
from baml_client.sync_client import b
from baml_client.types import Resume

resume: Resume = b.ExtractResume(raw_text)   # fully typed, already parsed via SAP
print(resume.seniority)                       # Seniority enum

# async:
from baml_client.async_client import b as ab
resume = await ab.ExtractResume(raw_text)

# streaming partials (fields fill in as tokens arrive):
stream = b.stream.ExtractResume(raw_text)
for partial in stream:        # PartialResume — every field Optional until complete
    print(partial)
final: Resume = stream.get_final_response()
```

TypeScript:

```ts
import { b } from "./baml_client";
const resume = await b.ExtractResume(rawText);   // typed Resume
```

### 7. Write and run tests (no app code needed)

```baml
test SmokeResume {
  functions [ExtractResume]
  args { raw "Jane Doe — Senior Python engineer, jane@x.com" }
  @@assert(has_email, {{ this.email == "jane@x.com" }})
  @@assert(is_senior, {{ this.seniority == "Senior" }})
}
```

```bash
baml-cli test                       # run all; or -i "ExtractResume::" to filter
```

`@@assert` hard-fails; `@@check` records a soft property without failing the run.

## Verify

- `baml-cli generate` exits 0 and `baml_client/` regenerates (delete it first to be sure).
- `baml-cli test` passes your `@@assert`s; iterate prompts in the VSCode playground.
- In app code, the return value is your class type (not a dict/str) and enum fields are
  enum members — if you're doing `json.loads()` on the result, you've bypassed BAML.
- Feed a deliberately messy string; SAP should still return a valid typed object.

## Pitfalls

- **Version skew**: the `version` in `generators.baml` must match the installed `baml-py`
  / `@boundaryml/baml`. A mismatch throws at import — run `baml-cli generate` after any
  package upgrade.
- **Forgetting to regenerate**: editing a `.baml` file does nothing until `generate` runs.
  Install the VSCode extension (auto-generates on save) or add a pre-commit / build step.
- **Dropping `{{ ctx.output_format }}`**: without it the model gets no schema and SAP has
  nothing to align to — accuracy collapses. Keep it in every function prompt.
- **BAML uses no colons** in blocks except function params (`raw: string`). `model "gpt-4o"`,
  not `model: "gpt-4o"`.
- **Enums/literals are how you constrain choices** — prefer an `enum` or a union
  (`type X = "a" | "b"`) over free-text-plus-validation for classification.
- **SAP is not magic JSON mode**: it repairs unquoted keys, markdown fences, and trailing
  yapping, but the model must still emit the right *values*. Test on real inputs; use
  fallback/retry clients for flaky providers.
- **Secrets**: reference keys as `env.OPENAI_API_KEY`, never literal strings in `.baml`.
