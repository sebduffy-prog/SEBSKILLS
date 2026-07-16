---
name: classifier-agent-routing
category: agent-frameworks
description: >
  Route every user turn to the best specialist agent with a central intent Classifier that keeps a global view of the
  whole conversation — using AWS Labs' Agent Squad (formerly Multi-Agent Orchestrator). The Classifier reads all agent
  descriptions plus chat history and picks one agent per turn; the Orchestrator runs it, persists the exchange, and
  falls back to a default agent when confidence is low. Use when the user says "agent squad", "multi-agent orchestrator",
  "intent classifier routing", "route to the right agent", "central router keeps conversation context", "supervisor
  agent", or wants a customer-support-style bot that dispatches to Bedrock/Anthropic/OpenAI/Lex/Lambda specialists.
when_to_use:
  - User wants ONE central classifier to pick the best specialist agent per turn from short agent descriptions
  - User wants the router to keep a global view of the whole conversation and switch agents mid-thread
  - User names "Agent Squad" or "Multi-Agent Orchestrator" (the awslabs framework, Python or TypeScript)
  - User wants a fallback/default agent when the classifier is unsure, plus per-agent conversation memory
  - User wants to mix agent backends (Bedrock, Anthropic, OpenAI, Amazon Lex, Lambda) behind one router
  - User wants a SupervisorAgent that fans a query out to several specialists in parallel and composes the answer
when_not_to_use:
  - Agents transfer control to each other peer-to-peer (no central brain) → use handoff-router-swarm
  - You want the OpenAI Agents SDK's handoffs/guardrails/sessions specifically → use openai-agents-sdk
  - Durable, checkpointed, resumable graph workflows → use langgraph-durable-workflows
  - Role/crew + sequential flow orchestration → use crewai-flows-orchestration
  - Generic routing theory not tied to Agent Squad → use agent-orchestration-patterns
keywords: [agent squad, agent-squad, multi-agent orchestrator, classifier, intent classification, routing, bedrock classifier, anthropicclassifier, openaiclassifier, supervisor agent, route_request, awslabs, default agent, per-agent memory, chat routing]
similar_to: [handoff-router-swarm, openai-agents-sdk, agent-orchestration-patterns, crewai-flows-orchestration, langgraph-durable-workflows]
inputs_needed:
  - Language target (Python `agent-squad` or TypeScript `agent-squad`)
  - Classifier backend + credentials (ANTHROPIC_API_KEY, OPENAI_API_KEY, or AWS Bedrock creds/region)
  - The list of specialist agents, each with a SHORT, discriminating description, and which one is the default fallback
produces: A runnable classifier-routed multi-agent app (orchestrator + agents + classifier + default fallback + memory)
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Classifier Agent Routing (Agent Squad)

Route each turn to the best specialist with a **central Classifier that sees the whole conversation** — AWS Labs' [Agent Squad](https://github.com/awslabs/agent-squad) (renamed from Multi-Agent Orchestrator). Four moving parts:

- **Orchestrator** (`AgentSquad`) — owns the loop: classify → run agent → save exchange → return.
- **Classifier** — one LLM call that reads every agent's `description` + chat history and returns `{selected_agent, confidence}`.
- **Agents** — specialists (`BedrockLLMAgent`, `AnthropicAgent`, `OpenAIAgent`, `LexBotAgent`, `LambdaAgent`, …).
- **Storage** — per-agent conversation memory (`InMemoryChatStorage`, DynamoDB, SQL).

The classifier picks **one** agent per turn but keeps global context, so the conversation can switch specialists mid-thread and still make sense.

## When to use

Reach for this when the routing brain should be **central**, not peer-to-peer: agents don't hand off to each other, a classifier chooses on every turn. If instead agents transfer control to one another, use `handoff-router-swarm` or `openai-agents-sdk`.

## Prerequisites

Python **3.11+** (or Node 18+ for TS). Install with the extra for your chosen classifier/agents — the framework is modular and each backend is optional:

```bash
pip install "agent-squad[anthropic]"   # Anthropic classifier + agents
pip install "agent-squad[openai]"      # OpenAI classifier + agents
pip install "agent-squad[aws]"         # Bedrock classifier/agents, Lex, Lambda, DynamoDB
pip install "agent-squad[all]"         # everything
# npm install agent-squad              # TypeScript

export ANTHROPIC_API_KEY=sk-ant-...    # or OPENAI_API_KEY, or AWS creds+region for Bedrock
```

Key API surface (verify names against your installed version):

- `AgentSquad(options=None, storage=None, classifier=None, logger=None, default_agent=None)`
- `orchestrator.add_agent(agent)` — registers the agent AND refreshes the classifier's agent list.
- `await orchestrator.route_request(user_input, user_id, session_id, additional_params=None, stream_response=False)`
- `ClassifierResult(selected_agent, confidence)` — what every classifier returns.

## Recipes

### 1. Minimal classifier-routed orchestrator (Anthropic)

The **default classifier is BedrockClassifier**. Pass a different one explicitly if you don't use Bedrock — otherwise the orchestrator tries to instantiate Bedrock and needs AWS creds.

```python
import asyncio, os, uuid
from agent_squad.orchestrator import AgentSquad, AgentSquadConfig
from agent_squad.classifiers import AnthropicClassifier, AnthropicClassifierOptions
from agent_squad.agents import AnthropicAgent, AnthropicAgentOptions

key = os.environ["ANTHROPIC_API_KEY"]

# One LLM call classifies each turn against the agent descriptions below.
classifier = AnthropicClassifier(AnthropicClassifierOptions(
    api_key=key,
    model_id="claude-3-5-sonnet-20240620",
    inference_config={"temperature": 0.0},   # deterministic routing
))

orchestrator = AgentSquad(
    classifier=classifier,
    options=AgentSquadConfig(
        USE_DEFAULT_AGENT_IF_NONE_IDENTIFIED=True,   # fall back instead of erroring
        MAX_MESSAGE_PAIRS_PER_AGENT=10,              # memory window per agent
        LOG_CLASSIFIER_OUTPUT=True,                  # see which agent won + confidence
    ),
)

# Descriptions are the ROUTING SIGNAL — make them short and discriminating.
orchestrator.add_agent(AnthropicAgent(AnthropicAgentOptions(
    api_key=key, name="Billing Agent",
    description="Handles invoices, refunds, payment methods, subscription plans and pricing questions.",
)))
orchestrator.add_agent(AnthropicAgent(AnthropicAgentOptions(
    api_key=key, name="Tech Support Agent",
    description="Troubleshoots bugs, error messages, installation, API integration and how-to product usage.",
)))

async def main():
    user_id, session_id = "user-123", str(uuid.uuid4())
    for turn in ["My card was charged twice", "Now the app won't launch after that"]:
        resp = await orchestrator.route_request(turn, user_id, session_id)
        print(f"[{resp.metadata.agent_name}] {resp.output.content[0]['text']}")

asyncio.run(main())
```

Same `session_id` across turns = shared conversation context, so the classifier can flip from Billing to Tech Support when the topic shifts.

### 2. Set a default (fallback) agent

When the classifier's confidence is low (or no agent matches) and `USE_DEFAULT_AGENT_IF_NONE_IDENTIFIED=True`, the orchestrator routes to the default agent instead of failing.

```python
general = AnthropicAgent(AnthropicAgentOptions(
    api_key=key, name="General Assistant",
    description="Handles greetings, small talk and anything not covered by a specialist.",
))
orchestrator.set_default_agent(general)   # or pass default_agent=general to AgentSquad(...)
```

### 3. Swap the classifier backend

The classifier is decoupled from the agents — route with OpenAI while your specialists run on Bedrock, etc.

```python
from agent_squad.classifiers import OpenAIClassifier, OpenAIClassifierOptions
classifier = OpenAIClassifier(OpenAIClassifierOptions(
    api_key=os.environ["OPENAI_API_KEY"], model_id="gpt-4o",
))
# or BedrockClassifier(BedrockClassifierOptions(model_id="anthropic.claude-3-5-sonnet-20240620-v1:0", region="us-east-1"))
```

### 4. Tune the routing prompt

Routing quality lives in the classifier's system prompt. Override it (keep the agent-list / history template variables) to inject domain rules, tie-breakers, or output-format constraints.

```python
classifier.set_system_prompt(
    """You route customer messages to ONE agent.
Agents:
{{AGENT_DESCRIPTIONS}}
History:
{{HISTORY}}
Rules: prefer the current agent when the topic is unchanged; only switch on a clear topic shift.
Return the analyzePrompt tool call with the chosen agent name and a confidence 0-1.""",
    variables={},
)
```

### 5. Custom classifier (non-LLM or rules-first routing)

Skip the LLM for cheap/deterministic routing by subclassing `Classifier` and returning a `ClassifierResult`. Useful for keyword shortcuts, an embeddings/vector router, or a small fine-tuned model.

```python
from agent_squad.classifiers import Classifier, ClassifierResult
from agent_squad.types import ConversationMessage

class KeywordClassifier(Classifier):
    async def process_request(self, input_text: str,
                              chat_history: list[ConversationMessage]) -> ClassifierResult:
        text = input_text.lower()
        if any(w in text for w in ("refund", "invoice", "charge", "billing")):
            return ClassifierResult(selected_agent=self.agents["Billing Agent"], confidence=0.95)
        return ClassifierResult(selected_agent=None, confidence=0.0)  # -> default agent fallback

orchestrator = AgentSquad(classifier=KeywordClassifier())
```

`self.agents` is the name→agent map populated by `set_agents()` when you `add_agent(...)`. Returning `selected_agent=None` triggers the default-agent fallback (recipe 2).

### 6. SupervisorAgent — parallel fan-out instead of pick-one

When a query needs several specialists at once, register a `SupervisorAgent` (agents-as-tools): it queries team members in parallel and composes one answer, while the classifier still routes to the supervisor as a single agent.

```python
from agent_squad.agents import SupervisorAgent, SupervisorAgentOptions
team = SupervisorAgent(SupervisorAgentOptions(
    name="Trip Planner", description="Coordinates flights, hotels and weather for a travel request.",
    lead_agent=AnthropicAgent(AnthropicAgentOptions(api_key=key, name="Lead", description="composes final trip answer")),
    team=[flights_agent, hotels_agent, weather_agent],
))
orchestrator.add_agent(team)
```

## Verify

- Set `LOG_CLASSIFIER_OUTPUT=True` and confirm each turn logs the selected agent + confidence, and that off-topic turns fall to the default agent.
- Send a 3-turn conversation that changes topic mid-thread; assert `resp.metadata.agent_name` changes on the topic shift but reuses the same agent when the topic holds.
- Force a nonsense input and assert it routes to the default agent (not an exception).
- Quick check that the package imports and reports its version:

```bash
python -c "import agent_squad, importlib.metadata as m; print('agent-squad', m.version('agent-squad'))"
```

## Pitfalls

- **Descriptions ARE the router.** Vague, overlapping descriptions = misroutes. Write one crisp sentence per agent listing the topics/verbs it owns; make them mutually exclusive.
- **Default classifier is Bedrock.** If you don't pass `classifier=`, the orchestrator instantiates `BedrockClassifier` and fails without AWS creds/region. Always pass one explicitly unless you're on Bedrock.
- **Enable the fallback.** Without `USE_DEFAULT_AGENT_IF_NONE_IDENTIFIED=True` (or a `default_agent`), a low-confidence turn yields no agent and returns `NO_SELECTED_AGENT_MESSAGE` instead of a helpful reply.
- **Set temperature 0.0** on the classifier for stable, reproducible routing — routing should not be creative.
- **Same `session_id` = shared context.** Reusing a `session_id` across users leaks memory between them; generate a fresh one per conversation, keep `user_id` stable per user.
- **`route_request` is async.** Call it inside an event loop (`asyncio.run(...)`); there is no sync wrapper by default.
- **Memory is per-agent, windowed.** `MAX_MESSAGE_PAIRS_PER_AGENT` trims history each agent sees — set it high enough that a specialist has the context it needs after a switch.
- **Streaming:** pass `stream_response=True` only for agents that support streaming; the classifier step itself is not streamed.
