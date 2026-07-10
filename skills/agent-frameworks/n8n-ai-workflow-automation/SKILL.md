---
name: n8n-ai-workflow-automation
category: agent-frameworks
description: >
  Build low-code visual AI agents and automations in n8n — 400+ integration nodes plus the
  LangChain AI nodes (AI Agent, Chat Trigger, chat models, memory, tools, vector stores) wired
  on a canvas, not in code. Use when the user says "n8n", "self-host n8n", "AI Agent node",
  "webhook automation", "no-code / low-code workflow", "connect Slack/Sheets/Gmail to an LLM",
  "n8n workflow JSON", or wants to trigger, activate, import/export or version workflows via
  the Public API or CLI. Covers Docker/npx setup, node/connection JSON, and RAG on the canvas.
when_to_use:
  - "User explicitly wants n8n (not a code-first framework like LangGraph or CrewAI)"
  - "Standing up self-hosted n8n via Docker or npx and reaching the editor at :5678"
  - "Building a visual AI Agent: Chat Trigger -> AI Agent -> chat model + memory + tool sub-nodes"
  - "Automating SaaS glue (Slack, Gmail, Sheets, HTTP, webhooks) with triggers and 400+ nodes"
  - "Programmatically creating / activating / exporting workflows via the Public API or n8n CLI"
  - "Hand-writing or reviewing workflow JSON (nodes[] + connections{}) for import"
when_not_to_use:
  - "Code-first durable graphs in Python/TS → langgraph-durable-workflows"
  - "Role-based multi-agent crews in code → crewai-flows-orchestration"
  - "OpenAI-native agents with handoffs in code → openai-agents-sdk"
  - "Building an MCP server to expose tools to Claude → mcp-builder"
  - "Pure retrieval pipeline design decisions rather than n8n canvas wiring → rag skills"
keywords: [n8n, low-code, no-code, workflow-automation, ai-agent, chat-trigger, langchain-nodes, webhook, self-host, docker, public-api, nodes, connections, rag, vector-store, memory, tools-agent, integrations, cron-trigger, credentials]
similar_to: [langgraph-durable-workflows, crewai-flows-orchestration, openai-agents-sdk, agent-orchestration-patterns, mcp-builder]
inputs_needed:
  - "Where n8n runs: local Docker/npx, n8n Cloud, or an existing self-hosted URL"
  - "The trigger (webhook / chat / schedule / app event) and the target apps + their credentials"
  - "For AI flows: an LLM provider + API key (OpenAI, Anthropic, Google, Ollama, etc.)"
  - "For Public API use: N8N_API_KEY from Settings -> n8n API"
produces: A runnable n8n workflow (importable JSON or live via API), plus setup + Public API/CLI commands to trigger, activate, and version it.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# n8n AI Workflow Automation

n8n is a **fair-code, low-code automation platform**: you wire nodes on a visual canvas
instead of writing orchestration code. It ships 400+ integration nodes and a full set of
**LangChain-based AI nodes**, so an agent (Chat Trigger → AI Agent → chat model + memory +
tools) is built the same way as a Slack-to-Sheets automation. Everything is stored as JSON
(`nodes[]` + `connections{}`), which makes workflows importable, versionable, and scriptable
via the Public REST API and CLI.

## When to use

Reach for n8n when the value is in **connecting systems visually** and letting non-engineers
read/edit the flow — SaaS glue, webhooks, scheduled jobs, and canvas-built AI agents/RAG. If
the logic belongs in a code repo with tests and custom control flow, use a code-first
framework instead (see `when_not_to_use`).

## Prerequisites

- **Docker** (recommended) or **Node.js 20+** for `npx`. macOS note: no brew here — use
  Docker Desktop or the official installer for Node.
- An **LLM provider API key** for AI nodes (OpenAI/Anthropic/Google/Ollama, etc.).
- **License:** n8n is distributed under the fair-code **Sustainable Use License**;
  self-hosting for internal business use is free. n8n Cloud is the hosted paid option.
- The AI nodes live in the built-in package `@n8n/n8n-nodes-langchain` — no separate install.

## Recipes

### 1. Run n8n locally

```bash
# Quick throwaway (needs Node 20+):
npx n8n
# Editor opens at http://localhost:5678

# Persistent Docker (recommended) — data + encryption key survive restarts:
docker volume create n8n_data
docker run -it --rm --name n8n -p 5678:5678 \
  -e GENERIC_TIMEZONE="Europe/London" \
  -e N8N_ENCRYPTION_KEY="$(openssl rand -hex 16)" \
  -v n8n_data:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n
```

Key env vars: `N8N_ENCRYPTION_KEY` (encrypts stored credentials — **set it and keep it
stable**, or credentials break on restart), `WEBHOOK_URL` (public base URL when behind a
reverse proxy/ngrok so webhook nodes emit correct URLs), `GENERIC_TIMEZONE`, and for
production `DB_TYPE=postgresdb` + `DB_POSTGRESDB_*` to use Postgres instead of SQLite.
On first load you create an owner account (user management), then add credentials in the UI.

### 2. A minimal importable workflow (Manual Trigger → Set)

Paste via the editor: top-right menu → **Import from File / URL**, or POST it with the
Public API (Recipe 4). Shape:

```json
{
  "name": "Hello n8n",
  "nodes": [
    {
      "parameters": {},
      "id": "a1", "name": "Manual Trigger",
      "type": "n8n-nodes-base.manualTrigger",
      "typeVersion": 1, "position": [0, 0]
    },
    {
      "parameters": {
        "assignments": { "assignments": [
          { "id": "s1", "name": "greeting", "value": "hi", "type": "string" }
        ]}
      },
      "id": "b2", "name": "Set",
      "type": "n8n-nodes-base.set",
      "typeVersion": 3.4, "position": [220, 0]
    }
  ],
  "connections": {
    "Manual Trigger": { "main": [[{ "node": "Set", "type": "main", "index": 0 }]] }
  },
  "settings": {}
}
```

`connections` is keyed by the **source node name**; each entry lists output slots, and each
slot is an array of `{node, type, index}` targets. `type` is the **connection kind**
(`main` for data flow; AI sub-nodes use special kinds — next recipe).

### 3. A canvas AI Agent (Chat Trigger → AI Agent + model + memory + tool)

The AI Agent node (`@n8n/n8n-nodes-langchain.agent`) is a **root node**: sub-nodes attach to
it via typed AI connections, not `main`. As of n8n 1.82+ there is a single agent type,
**Tools Agent**. Attach at least one tool. Sub-node connection kinds:

| Connection type      | Attach a node like                                             |
|----------------------|----------------------------------------------------------------|
| `ai_languageModel`   | `@n8n/n8n-nodes-langchain.lmChatOpenAi` / `lmChatAnthropic`     |
| `ai_memory`          | `@n8n/n8n-nodes-langchain.memoryBufferWindow`                   |
| `ai_tool`            | `toolWorkflow`, `toolHttpRequest`, `toolCalculator`, MCP tools  |
| `ai_embedding`       | `embeddingsOpenAi` (feeds a vector store)                       |
| `ai_vectorStore`     | `vectorStoreInMemory` / `vectorStorePinecone` / `...Qdrant`     |

Wiring (built in the UI by dragging from the round AI connectors; in JSON the model connects
into the agent like this):

```json
"connections": {
  "When chat message received": { "main": [[{ "node": "AI Agent", "type": "main", "index": 0 }]] },
  "OpenAI Chat Model": { "ai_languageModel": [[{ "node": "AI Agent", "type": "ai_languageModel", "index": 0 }]] },
  "Window Buffer Memory": { "ai_memory": [[{ "node": "AI Agent", "type": "ai_memory", "index": 0 }]] },
  "Calculator": { "ai_tool": [[{ "node": "AI Agent", "type": "ai_tool", "index": 0 }]] }
}
```

The Chat Trigger is `@n8n/n8n-nodes-langchain.chatTrigger`. Click **Chat** in the editor to
test the agent conversationally. **RAG:** add a Vector Store node with an embeddings sub-node,
load documents once, then attach the vector store to the agent as an `ai_tool` (retriever) so
the agent can search your knowledge base mid-conversation.

### 4. Drive workflows from the Public API

Create an API key in **Settings → n8n API → Create an API key**, then use the bundled helper
(stdlib only, Python 3.9+):

```bash
export N8N_BASE_URL=http://localhost:5678
export N8N_API_KEY=n8n_api_...            # from Settings -> n8n API
python3 scripts/n8n_api.py list                 # list workflows + active state
python3 scripts/n8n_api.py create hello.json    # POST /api/v1/workflows
python3 scripts/n8n_api.py activate <id>         # turn triggers/webhooks live
```

Raw equivalent (header is `X-N8N-API-KEY`):

```bash
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" "$N8N_BASE_URL/api/v1/workflows?limit=20"
```

### 5. CLI: run, export, import (great for git-versioning workflows)

```bash
# Inside the container: docker exec -it n8n n8n <cmd>   (or just `n8n <cmd>` on npx installs)
n8n execute --id <workflow_id>                 # run one workflow once, headless
n8n export:workflow --all --output=./flows/    # dump every workflow to JSON (commit these)
n8n import:workflow --separate --input=./flows # load them back into another instance
```

### 6. Fire a webhook

A **Webhook** node (`n8n-nodes-base.webhook`) exposes two URLs: the **test** URL
(`/webhook-test/<path>`, active only while you click "Listen for test event") and the
**production** URL (`/webhook/<path>`, live once the workflow is **Active**). Trigger it:

```bash
curl -X POST "$N8N_BASE_URL/webhook/my-path" \
  -H "Content-Type: application/json" -d '{"hello":"world"}'
```

## Verify

- `curl -sf http://localhost:5678/healthz` returns `{"status":"ok"}` when n8n is up.
- Editor loads at `http://localhost:5678` and you can create the owner account.
- `python3 scripts/n8n_api.py list` returns your workflows (proves API key + connectivity).
- For an AI Agent: open **Chat**, send a message, and confirm the tool/memory sub-nodes light
  up green in the execution and the reply reflects tool output.
- Syntax-check the helper: `python3 -m py_compile scripts/n8n_api.py`.

## Pitfalls

- **Losing `N8N_ENCRYPTION_KEY`.** If it changes (or isn't set and the container is
  recreated), all stored credentials become undecryptable. Set it explicitly and back it up.
- **Webhook URL vs test URL.** The test URL only fires while you're actively listening;
  external callers must hit the **production** `/webhook/...` path, which requires the
  workflow to be **Active**. Behind a proxy/tunnel, set `WEBHOOK_URL` so emitted URLs match.
- **AI sub-nodes use typed connections, not `main`.** A model/memory/tool wired with
  `type:"main"` won't attach to the agent — it must be `ai_languageModel`/`ai_memory`/`ai_tool`.
- **SQLite in production.** The default file DB is fine for trials but locks under load —
  switch to `DB_TYPE=postgresdb` for anything real.
- **Node type prefixes matter.** Core/integration nodes are `n8n-nodes-base.*`; AI nodes are
  `@n8n/n8n-nodes-langchain.*`. A wrong prefix makes import fail with "unknown node type".
- **Public API is opt-in and versioned at `/api/v1`.** It's disabled on some hosted tiers;
  the header is `X-N8N-API-KEY` (not a Bearer token). Community edition may gate a few
  endpoints — the four used here (list/get/create/activate) are available.
- **License scope.** The Sustainable Use License permits internal business automation but
  restricts reselling n8n itself as a hosted service — check terms before commercial hosting.
