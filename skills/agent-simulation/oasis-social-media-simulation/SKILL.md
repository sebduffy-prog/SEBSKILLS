---
name: oasis-social-media-simulation
category: agent-simulation
description: >
  Run agent-based social-media simulations with OASIS (camel-ai/oasis) to model
  virality, polarization, rumor/misinformation spread, and audience reactions to a
  post BEFORE real spend. Use when someone says "simulate how this tweet spreads",
  "model a viral campaign", "test messaging on a synthetic audience", "how would
  Reddit react", "run a social-media agent simulation", "predict engagement", or
  wants a pre-mortem on a launch post. Scales from dozens to ~1M LLM/rule agents on
  Twitter- or Reddit-style graphs and writes a SQLite trace you can analyze.
when_to_use:
  - "Simulate how a specific post/tweet/headline spreads before publishing it"
  - "Model virality, echo chambers, polarization, or rumor/misinformation diffusion"
  - "Pressure-test campaign messaging on a synthetic audience and read reactions"
  - "Compare two message variants for reach/engagement without paid A/B testing"
  - "Study follow/unfollow, group, and recommendation-driven network dynamics at scale"
when_not_to_use:
  - "Modeling a whole city's daily behavior (mobility, econ) — use agentsociety-urban-experiment"
  - "Long-lived agents with reflective memory/relationships in a sandbox town — use generative-agent-architecture"
  - "You need REAL audience data, not a synthetic sim — use a GWI/Brand24/social-listening skill"
keywords: [oasis, camel-oasis, social media simulation, agent-based model, virality, misinformation, rumor spread, polarization, twitter simulation, reddit simulation, synthetic audience, LLM agents, million agents, camel-ai, echo chamber, message testing]
similar_to: [generative-agent-architecture, agentsociety-urban-experiment]
inputs_needed:
  - "Platform to mimic: Twitter/X-style or Reddit-style"
  - "The seed content to test (the post/tweet/headline) and how many timesteps to run"
  - "Roughly how many agents (dozens for a smoke test, thousands+ for signal) and the model backend (OpenAI key, or a local vLLM URL for big runs)"
produces: A runnable OASIS Python script + a SQLite trace (posts, likes, comments, follows) you can query for reach/engagement/sentiment
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# OASIS Social-Media Simulation

Spin up a synthetic social network of LLM-driven agents, drop in a seed post, and
watch it propagate. OASIS (camel-ai) reproduces Twitter- and Reddit-style feeds,
recommendation systems, and ~23 user actions, and scales to ~1M agents. Use it as a
cheap pre-mortem: which message goes viral, where polarization forms, how a rumor
mutates — before you spend on the real thing.

## When to use

Reach for this when the ask is "what would happen if we posted X" and you want a
mechanistic, inspectable answer (an event trace) rather than a vibe. Great for
message A/B pre-tests, misinformation/rumor studies, and network-dynamics research.

## Prerequisites

Python 3.10–3.11 (camel-oasis requires `>=3.10,<3.12`; pip installs fail on 3.12). Install the package (it pulls in `camel-ai`):

```bash
pip install camel-oasis
```

Pick a model backend — this is the main cost driver, since every active agent calls
an LLM each step:

- **Small runs (tens–hundreds of agents):** OpenAI. `export OPENAI_API_KEY=sk-...`
  Use `gpt-4o-mini` to keep cost sane.
- **Large runs (thousands–1M):** a **local vLLM** server so calls are free/fast.
  Start one (`vllm serve Qwen/Qwen2.5-7B-Instruct --port 8000`) and point OASIS at it.
  Do NOT run 100k agents against a paid API — that is a large, real bill.

Example agent profiles ship in the repo. Grab one to start:

```bash
# Reddit example profile (small)
curl -L -o user_data_36.json \
  https://raw.githubusercontent.com/camel-ai/oasis/main/data/reddit/user_data_36.json
# Twitter example profiles live under data/twitter_dataset/ in the repo
```

## Recipe 1 — Twitter-style: does this tweet spread?

Inject a seed post at step 0, then let agents react autonomously for several steps.

```python
import asyncio
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
import oasis
from oasis import (ActionType, LLMAction, ManualAction,
                   generate_twitter_agent_graph)

async def main():
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
    )

    # Actions agents are allowed to choose from each step
    available_actions = [
        ActionType.CREATE_POST, ActionType.LIKE_POST, ActionType.REPOST,
        ActionType.QUOTE_POST, ActionType.CREATE_COMMENT, ActionType.FOLLOW,
        ActionType.DO_NOTHING,
    ]

    agent_graph = await generate_twitter_agent_graph(
        profile_path="data/twitter_dataset/anonymous_topic_200_1h/False_Business_0.csv",
        model=model,
        available_actions=available_actions,
    )

    env = oasis.make(
        agent_graph=agent_graph,
        platform=oasis.DefaultPlatformType.TWITTER,
        database_path="./twitter_sim.db",   # delete this file before re-running
    )
    await env.reset()

    # STEP 0: agent 0 posts the message we want to test (a ManualAction).
    seed = {
        env.agent_graph.get_agent(0): ManualAction(
            action_type=ActionType.CREATE_POST,
            action_args={"content":
                "BREAKING: new study says 4-day work weeks boost output 22%."},
        )
    }
    await env.step(seed)

    # STEPS 1..N: everyone acts autonomously via the LLM; virality emerges here.
    for _ in range(5):
        actions = {agent: LLMAction()
                   for _, agent in env.agent_graph.get_agents()}
        await env.step(actions)

    await env.close()

asyncio.run(main())
```

## Recipe 2 — Reddit-style: rumor / community reaction

Same shape, different graph builder and platform. Reddit uses a downvote-capable feed.

```python
from oasis import generate_reddit_agent_graph
# ...
agent_graph = await generate_reddit_agent_graph(
    profile_path="./user_data_36.json",
    model=model,
    available_actions=[ActionType.CREATE_POST, ActionType.LIKE_POST,
                       ActionType.DISLIKE_POST, ActionType.CREATE_COMMENT,
                       ActionType.CREATE_GROUP, ActionType.JOIN_GROUP,
                       ActionType.DO_NOTHING],
)
env = oasis.make(agent_graph=agent_graph,
                 platform=oasis.DefaultPlatformType.REDDIT,
                 database_path="./reddit_sim.db")
```

## Recipe 3 — A/B message test + reading reactions

- **A/B:** run the sim twice, changing only the `CREATE_POST` content and the
  `database_path`. Compare total reposts/likes/comments the seed accrued (query below).
- **Direct reactions:** poll specific agents with `ActionType.INTERVIEW` to ask
  "what do you think of this post?" without polluting the feed:

```python
q = {env.agent_graph.get_agent(i): ManualAction(
        action_type=ActionType.INTERVIEW,
        action_args={"prompt": "In one line, react to the pinned post."})
     for i in range(10)}
await env.step(q)   # interview answers are written to the DB trace
```

## Key knobs

- **Scale:** agent count = rows in the profile file. Bigger profile → more agents.
  Above a few hundred, switch `ModelFactory` to your vLLM server:
  `ModelFactory.create(model_platform=ModelPlatformType.VLLM, model_type="Qwen/Qwen2.5-7B-Instruct", url="http://localhost:8000/v1")`.
- **Action menu** (`available_actions`) shapes dynamics: include `REPOST`/`QUOTE_POST`
  for virality; `FOLLOW`/`UNFOLLOW` for network reshaping; `DISLIKE_POST` +
  `CREATE_GROUP`/`JOIN_GROUP` for polarization/echo chambers. Full ~23-action set
  incl. `SEARCH_POSTS`, `TREND`, `REFRESH`, `MUTE`, `REPORT_POST`, `PURCHASE_PRODUCT`.
- **Timesteps:** each `env.step` is one round of activation. More steps = more
  cascade; virality usually resolves within ~5–15 steps.

## Verify

- `pip show camel-oasis` prints a version; the script imports without error.
- After a run the DB exists and has rows. Inspect the trace:

```bash
sqlite3 ./twitter_sim.db ".tables"
# reach of the seed post: how many reposts + likes it collected
sqlite3 ./twitter_sim.db \
  "SELECT (SELECT COUNT(*) FROM post WHERE original_post_id=1) AS reposts,
          (SELECT COUNT(*) FROM 'like' WHERE post_id=1)        AS likes,
          (SELECT COUNT(*) FROM comment WHERE post_id=1)       AS comments;"
```

Table/column names vary by OASIS version — run `.schema` first and adapt. The `trace`
table logs every agent action with a timestamp; it's the ground truth for building
reach-over-time and sentiment charts.

## Pitfalls

- **Cost blow-up:** N agents × T steps LLM calls. A "1M agents" headline run is a
  research-cluster job on local vLLM, not an OpenAI credit card. Smoke-test with
  ~20 agents / 3 steps first, then scale.
- **Stale DB:** OASIS appends to `database_path`. Delete the `.db` between runs or
  point each run at a fresh path, or A/B comparisons get contaminated.
- **Everything is async:** all `env` calls are awaited; wrap in `asyncio.run`.
  Reusing an env across `asyncio.run` calls breaks — build one env per run.
- **It's a simulation, not a forecast:** treat outputs as directional hypotheses
  about *mechanisms* (why something spreads), not calibrated real-world numbers.
  Validate against real listening data before betting spend on it.
- **API drift:** graph-builder and `oasis.make` signatures move between releases.
  If an import fails, check the installed version's `examples/` and the docs at
  https://docs.oasis.camel-ai.org before assuming this snippet is wrong.
