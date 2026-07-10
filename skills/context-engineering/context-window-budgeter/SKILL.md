---
name: context-window-budgeter
category: context-engineering
description: >
  Allocate a fixed token budget across competing context sources (system rules, tools, retrieved
  docs, memory, chat history) by priority, then drop or degrade the lowest-priority material under
  pressure so the window never overflows and generation always has headroom. Same priority-cutoff
  idea as anysphere/priompt, but source-agnostic. Use when you ask "how do I fit everything in the
  context window", "token budget", "context overflow", "prompt too long", "which context to drop
  first", "priority-based prompt", "reserve tokens for the answer", or "graceful context degradation".
when_to_use:
  - "Your prompt sometimes exceeds the model's context window and you need a deterministic rule for what to cut"
  - "Multiple context sources compete for room (system, tools, RAG docs, memory, history) and you want priorities, not ad-hoc truncation"
  - "You need to guarantee headroom is reserved for the model's own output before assembling context"
  - "You want low-priority material to degrade to a summary/placeholder instead of vanishing entirely"
  - "Porting priompt's priority-cutoff behaviour to a non-JSX / Python / plain-string pipeline"
  - "A single tool result or retrieved doc blows the budget and you need per-source caps"
when_not_to_use:
  - "The running conversation itself has grown too long and needs summarizing mid-run — use agent-context-compaction"
  - "You want to shrink one blob of text with token-level compression/LLMLingua — use prompt-compression"
  - "Deciding what belongs in short-term vs long-term memory tiers — use structured-memory-layers"
  - "Persisting durable notes to a file across sessions — use agent-memory-file"
  - "Measuring whether your context actually helps answer quality — use context-quality-evals"
  - "Isolating context per sub-agent so it never lands in the main window — use subagent-context-isolation"
keywords: [token budget, context window, context overflow, priompt, priority cutoff, prompt too long, context length exceeded, max tokens, reserve tokens, graceful degradation, drop context, truncate prompt, tiktoken, token counting, context assembly, prompt budget, context engineering, headroom]
similar_to: [agent-context-compaction, prompt-compression, structured-memory-layers, agent-memory-file, context-quality-evals, subagent-context-isolation]
inputs_needed:
  - "The model's context window size and your target max input tokens (leave slack for the model version)"
  - "How many tokens to reserve for the model's generated output (the answer / tool call)"
  - "The list of context sources you assemble each turn, each with a rough priority ranking"
  - "For any source that can be shortened: its degrade steps (summary, then placeholder) if you want graceful loss"
produces: A priority-ordered context assembly that provably fits a token budget with reserved output headroom — plus scripts/budget.py, a dependency-light budgeter that degrades or drops the lowest-priority sources first
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Context Window Budgeter

Truncating the prompt from the end is how you silently delete your system instructions. Instead,
give every context source a **priority**, set a **token budget** with **reserved output headroom**,
and let a budgeter keep sources in priority order until the budget is spent — degrading or dropping
the losers on purpose. This is the priority-cutoff idea from **anysphere/priompt** (MIT): "include
all scopes with priority ≥ cutoff that fit," made source-agnostic so it works in any language and
over plain strings, not just JSX.

## When to use

Reach for this when a turn's context is assembled from *competing* parts — system rules, tool
schemas, retrieved docs, memory, chat history — and their combined size is unpredictable. You want
one deterministic rule: **highest priority wins, output headroom is sacred, low-priority material
degrades gracefully.** If instead a long *running* conversation needs mid-flight summarizing, that
is `agent-context-compaction`; if you want to compress one text blob, that is `prompt-compression`.

## The mental model (borrowed from priompt)

- **Budget** = `max_input_tokens = context_window − reserve_for_output`. The reserve is
  non-negotiable; a prompt that fills the whole window leaves the model no room to answer and errors
  or truncates the reply.
- **Priority** = a number per source. Higher = kept first. Ties break by declared order.
- **Cutoff** = the highest priority threshold whose surviving sources fit the budget. priompt finds
  it by binary search over its JSX tree; a flat source list needs only a greedy descending pass.
- **Degrade** = an ordered fallback chain per source: full text → short summary → placeholder →
  dropped. priompt's `<first>` picks the first child that fits (e.g. full result, else
  "(result omitted)"); `<empty>` reserves space for generation. We model both explicitly.

Rough priority ladder for a typical agent turn:

| Priority | Source |
|---|---|
| 100 | System prompt / hard rules / safety |
| 90 | Current user message + active task |
| 70 | Tool schemas the model may call now |
| 50 | Latest tool result(s) |
| 40 | Top retrieved RAG passages |
| 30 | Long-term memory / user profile |
| 10 | Older conversation turns |

## Prerequisites

- **Python 3.9+** for `scripts/budget.py`. Zero required deps — it runs on the stdlib.
- **Accurate counts (recommended):** `pip install tiktoken`. The script uses it automatically when
  present (OpenAI/`cl100k_base` BPE); without it, it falls back to a ~4-chars/token heuristic that
  over/under-counts by ~10–20%, so leave a wider reserve if you rely on the fallback.
- For **Claude** exact counts, use the Anthropic SDK's token-counting endpoint
  (`client.messages.count_tokens(...)`) instead of tiktoken; tiktoken is an approximation for Claude.
- **priompt itself** (`npm i priompt`, MIT) is the right tool if you are in TypeScript/JSX and want
  the full component model (`<scope p=…>`, `<first>`, `<empty>`, `<isolate>`, caching). This skill
  is the language-neutral equivalent for everything else.

## Recipe 1 — budget a turn with scripts/budget.py

Describe each source as JSON with a `priority` and optional `degrade` chain (richest → cheapest):

```json
[
  {"id": "system",      "priority": 100, "text": "You are a careful assistant..."},
  {"id": "user",        "priority": 90,  "text": "Refactor the auth module and add tests."},
  {"id": "tool_result", "priority": 50,  "text": "<12k-token file dump>",
     "degrade": ["<1k-token summary of the file>", "(file contents omitted — ask to re-read)"]},
  {"id": "rag_doc",     "priority": 40,  "text": "<retrieved passage>",
     "degrade": ["<one-line gist>"]},
  {"id": "old_turn",    "priority": 10,  "text": "<earlier chat turn>"}
]
```

Run it, reserving output headroom:

```bash
# 200k window, hold 8k back for the model's answer
python3 scripts/budget.py --budget 200000 --reserve 8000 --model gpt-4o sources.json

# Emit just the assembled context string to pipe into your prompt
python3 scripts/budget.py --budget 200000 --reserve 8000 --assemble sources.json > context.txt
```

The JSON report shows, per source, the chosen `level` (0 = full, 1+ = which degrade step,
`-1`/`dropped` = cut), its `tokens`, plus totals `used`/`free`. The algorithm is a single greedy
descending-priority pass: for each source it keeps the **richest variant that still fits the
remaining budget**, so high-priority sources never lose room to low-priority ones.

## Recipe 2 — inline budgeter (any pipeline, ~15 lines)

When you don't want a file, the whole idea is small. Sort by priority, spend the budget, degrade:

```python
def assemble(sources, budget, count):        # count: str -> int (tiktoken or SDK)
    used, out = 0, []
    for s in sorted(sources, key=lambda x: -x["priority"]):
        for text in [s["text"], *s.get("degrade", []), ""]:   # richest -> "" (drop)
            t = count(text)
            if t <= budget - used:
                if text:
                    out.append(text); used += t
                break
    return "\n\n".join(out), used
```

The trailing `""` is priompt's `<first>` fallback: if nothing fits, the source silently drops.

## Recipe 3 — per-source caps (stop one blob eating the window)

Global priority alone lets a single 100k-token tool result starve everything below it. Cap each
elastic source *before* budgeting so no one source exceeds, say, 25% of the budget — truncate to a
head+tail window or pre-summarize, then feed the capped text in. In priompt this is `<isolate>`
(an independent sub-budget); here, clamp the source's token count in your `degrade[0]`.

## Recipe 4 — reserve for output, always

Set `--reserve` (or `budget − reserve`) to at least your expected `max_tokens` for the response,
plus slack for tool-call JSON. Under-reserving is the most common failure: the request fits but the
model's reply is cut mid-sentence or the API rejects it. Over-reserving just drops your lowest-value
context — a safe trade.

## Verify

```bash
# Deterministic tight-budget check: system full, tool_result degrades, old_turn drops
python3 - <<'PY'
import json,subprocess,sys,pathlib
sp=pathlib.Path("scripts/budget.py")
src=json.dumps([
 {"id":"system","priority":100,"text":"You are a careful assistant. Follow the rules."},
 {"id":"tool","priority":40,"text":"X"*400,"degrade":["short summary","(omitted)"]},
 {"id":"old","priority":10,"text":"Y"*400}])
out=json.loads(subprocess.run([sys.executable,str(sp),"--budget","30"],
     input=src,capture_output=True,text=True).stdout)
assert out["used"]<=30, out
byid={s["id"]:s for s in out["sources"]}
assert not byid["system"].get("dropped")            # top priority survives
assert byid["tool"]["degraded"]                     # mid degrades
assert byid["old"].get("dropped")                   # lowest drops
print("OK — budget respected, priority order honoured")
PY
```

Also sanity-check counts against your real tokenizer: `python3 -c "import tiktoken;print(len(tiktoken.get_encoding('cl100k_base').encode(open('context.txt').read())))"` and confirm it is ≤ your `--budget − --reserve`.

## Pitfalls

- **Truncating from the end deletes your system prompt.** Always cut by priority, never by position.
- **No output reserve = truncated answers.** The window must hold input *and* the reply; reserve first.
- **Heuristic counts drift.** The 4-chars/token fallback is approximate; install tiktoken (OpenAI)
  or use `count_tokens` (Claude) for anything near the limit, and keep a safety margin either way.
- **Wrong tokenizer for the model.** tiktoken ≠ Claude's tokenizer; counts differ by 10–30% on some
  text. Match the counter to the target model or widen the reserve.
- **One elastic source starves the rest.** Add per-source caps (Recipe 3) — global priority won't
  save a 90-priority source sitting below a 50-priority 100k-token dump *of equal declared order*.
- **Degrade chains that lie.** A summary placeholder the model can't act on ("(omitted)") is fine as
  a last resort, but prefer a real short summary so degraded turns stay useful.
- **Budgeting the same content twice.** If retrieval and memory both carry the same fact, dedupe
  before budgeting or you pay tokens twice and may drop something unique to make room.
- **Static priorities.** Priority is a function of the *turn*: the tool result you just requested
  should outrank stale memory. Recompute priorities per turn, don't hard-code them once.

## Credits

Priority-cutoff model adapted from **anysphere/priompt** (MIT License,
<https://github.com/anysphere/priompt>). This skill reimplements the concept source-agnostically;
no priompt code is copied.
