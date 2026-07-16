---
name: agentic-web-automation
category: frontend-and-design
description: >-
  Automate multi-step, natural-language web tasks when CSS/XPath selectors are
  too brittle to maintain — drive an LLM agent loop that observes the live DOM,
  plans, and acts. Reach for this when a scripted Playwright/Puppeteer flow keeps
  breaking on redesigns, A/B variants, or dynamic content, or when the task is
  described in prose ("log in, filter to unpaid invoices, export CSV") rather than
  in selectors. Grounded on Stagehand (@browserbasehq/stagehand, TypeScript) and
  Browser Use (browser-use, Python) with act/extract/observe/agent primitives.
when_to_use:
  - A scripted browser flow keeps breaking because selectors change across deploys or A/B variants
  - The task is stated in natural language and spans several pages (login, search, filter, export)
  - You need to extract structured, schema-validated data from a page whose markup is unstable
  - You want an autonomous agent to figure out the next click rather than hard-coding each step
  - Prototyping a scraper/QA bot fast before investing in brittle deterministic selectors
when_not_to_use:
  - The page is stable and selectors are known — use plain Playwright/Puppeteer (webapp-testing skill), it is faster and free
  - Interactive one-off browsing in the user's own Chrome — use the claude-in-chrome tools
  - Pure visual/UX QA of your own local app — use browser-qa or webapp-testing
  - You only need to render/screenshot HTML you generated — use webapp-testing
keywords:
  - stagehand
  - browser-use
  - agentic
  - web-automation
  - llm-agent
  - natural-language
  - scraping
  - act-extract-observe
  - playwright
  - browserbase
  - self-healing
  - zod
  - selectors
  - autonomous
similar_to: [computer-use-agent, connect-playwright-mcp, stealth-browser-scraping, resilient-scraper, firecrawl-scrape]
inputs_needed: >-
  An LLM API key (OPENAI_API_KEY or ANTHROPIC_API_KEY); the target URL; the task
  as a natural-language string; Node 18+ (Stagehand) or Python 3.11+ (Browser Use);
  optional BROWSERBASE_API_KEY for cloud browsers.
produces: >-
  A runnable agent script that navigates, acts, and returns structured
  (schema-validated) data or a task-completion history — no hand-written selectors.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Agentic Web Automation

Two production libraries turn "click the login button, then export the invoices"
into working automation without you writing a single CSS selector. Pick by stack:

| Library | Lang | Package | Best for |
|---|---|---|---|
| **Stagehand** | TypeScript | `@browserbasehq/stagehand` | Mix of deterministic Playwright + AI acts; schema extraction; caching selectors |
| **Browser Use** | Python | `browser-use` | Fully autonomous agent loop; fast default model; minimal code |

Both run against a **local** Chromium (free, your machine) or a **cloud** browser
(Browserbase) for scale/stealth.

## When to use

Reach for an agent loop only when selectors are the problem. If the DOM is stable
and you know the selectors, deterministic Playwright is faster, cheaper, and more
reliable — see the `webapp-testing` skill. The moment a flow keeps breaking on
redesigns/A-B variants, or the spec is prose across several pages, switch here.

## Prerequisites

- **Stagehand:** Node 18+, an `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `.env`.
- **Browser Use:** Python 3.11+ (macOS system python3 is 3.9 — use `python3.11`/`uv`),
  plus `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`.
- Never hard-code keys — load from env (`import "dotenv/config"` / `.env`).

## Recipe A — Stagehand (TypeScript)

Scaffold or install:

```bash
npx create-browser-app my-agent && cd my-agent && cp .env.example .env
# or into an existing project:
npm install @browserbasehq/stagehand zod
```

The four primitives — **act, extract, observe, agent**:

```typescript
import "dotenv/config";
import { Stagehand } from "@browserbasehq/stagehand";
import { z } from "zod";

async function main() {
  const stagehand = new Stagehand({
    env: "LOCAL",                       // "LOCAL" (free) or "BROWSERBASE" (cloud)
    modelName: "claude-sonnet-4-6",     // any provider model; gpt-4o-mini = cheap default
    modelClientOptions: { apiKey: process.env.ANTHROPIC_API_KEY },
    verbose: 1,                          // 0 silent, 1 info, 2 debug
  });
  await stagehand.init();

  const page = stagehand.context.pages()[0];
  await page.goto("https://news.ycombinator.com");

  // OBSERVE — discover candidate actions before acting (dry-run, no side effects)
  const candidates = await stagehand.observe("the top story link");
  console.log(candidates); // [{ selector, description, method, arguments }]

  // ACT — one natural-language step -> a deterministic browser action
  await stagehand.act("click the first story title");

  // EXTRACT — structured, schema-validated data (Zod)
  const { title, points } = await stagehand.extract(
    "extract the story title and its points",
    z.object({
      title: z.string().describe("the headline text"),
      points: z.number().describe("the score in points"),
    }),
  );
  console.log({ title, points });

  await stagehand.close();
}
main().catch((e) => { console.error(e); process.exit(1); });
```

Fully autonomous multi-step work — hand the goal to `agent()`:

```typescript
const agent = stagehand.agent({
  // omit model to use modelName; or use a computer-use model:
  model: "claude-sonnet-4-6",
  systemPrompt: "You control a browser. Be concise and stop when the goal is met.",
});
const result = await agent.execute("Find the top Show HN post and report its URL");
console.log(result); // { success, message, actions }
```

**Cache the plan for repeat runs:** `observe()` returns a concrete `selector` +
`method`. Persist that result and replay it with `act(cachedObserveResult)` to skip
the LLM call on subsequent runs — deterministic speed, self-healing fallback when
it misses.

## Recipe B — Browser Use (Python)

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install browser-use          # or: uv add browser-use
playwright install chromium      # first run only
```

Minimal autonomous agent:

```python
import asyncio
from browser_use import Agent
from browser_use.llm import ChatAnthropic  # or ChatOpenAI

async def main():
    agent = Agent(
        task="Go to news.ycombinator.com and return the title and URL "
             "of the top story as JSON.",
        llm=ChatAnthropic(model="claude-sonnet-4-6"),
    )
    history = await agent.run(max_steps=15)
    print(history.final_result())      # the agent's answer
    print(history.urls())              # pages it visited

asyncio.run(main())
```

Structured output with a Pydantic schema (validated result, not free text):

```python
from pydantic import BaseModel

class Story(BaseModel):
    title: str
    url: str
    points: int

agent = Agent(
    task="Return the top Hacker News story.",
    llm=ChatAnthropic(model="claude-sonnet-4-6"),
    output_model_schema=Story,
)
history = await agent.run()
story = Story.model_validate_json(history.final_result())
```

Reuse a logged-in browser / control the session:

```python
from browser_use import Agent, Browser

browser = Browser(headless=False, user_data_dir="~/.config/browseruse/profile")
agent = Agent(task="...", llm=..., browser=browser)
```

## Verify

- **Dry-run first with `observe()`** (Stagehand) — inspect the returned selectors
  before letting `act()` mutate the page; catches "clicked the wrong thing" early.
- **Assert on extracted data**, not on screenshots: the Zod/Pydantic parse *is* your
  test — a schema mismatch throws, so a green run means the data shape held.
- **Cap the loop**: Browser Use `max_steps=…`; for Stagehand agents keep tasks
  narrow. An uncapped agent can spend tokens wandering.
- **Re-run twice**: a genuinely self-healing flow passes on two different sessions.
  If it only works once, you are relying on incidental page state.
- Watch it live with `headless=False` (Browser Use) or `verbose: 2` (Stagehand)
  while developing; flip to headless for CI.

## Pitfalls

- **Cost & latency:** every `act`/`extract`/agent step is an LLM call. Don't loop
  agents over 500 rows — use the agent once to derive a selector via `observe()`,
  then replay it deterministically. Prefer `gpt-4o-mini`/small models for routing,
  reserve `claude-sonnet-4-6`/`gpt-4o` for extraction accuracy.
- **Non-determinism:** the same prompt can pick a different element run-to-run.
  Write specific instructions ("the *primary* submit button in the checkout form",
  not "the button") and cache observed selectors.
- **Python version:** `browser-use` needs 3.11+. macOS `python3` is 3.9 and will
  fail to install — use `python3.11`/`uv`. Run `playwright install chromium` once.
- **Auth walls & captchas:** local browsers get blocked by bot detection. For
  logged-in flows reuse a persistent `user_data_dir` profile; for scale/stealth use
  Browserbase (`env: "BROWSERBASE"` + `BROWSERBASE_API_KEY`).
- **Prompt injection:** an agent reads page text as instructions. Never point an
  autonomous agent with real credentials or payment ability at untrusted sites; scope
  its task and treat page content as hostile input.
- **Leaked sessions:** always `await stagehand.close()` / let Browser Use finish —
  orphaned Chromium processes and cloud sessions cost money and leak state.
- **Model IDs drift:** provider model names change; if a call 400s on the model,
  check the provider's current catalog rather than trusting a hard-coded string.
