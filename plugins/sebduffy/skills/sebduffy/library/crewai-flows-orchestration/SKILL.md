---
name: crewai-flows-orchestration
category: agent-frameworks
description: >
  Build multi-agent systems with CrewAI — role-based Crews (Agent/Task, sequential or
  hierarchical process, YAML+Pydantic config via @CrewBase) plus deterministic, event-driven
  Flows (@start / @listen / @router, and_/or_, structured state, @persist for resumable runs).
  Use when the user says "CrewAI", "crew of agents", "agent flow", "@start @listen router",
  "hierarchical crew", "manager agent", "kickoff", "crewai create flow", or wants agents that
  hand work off deterministically and resume after a crash.
when_to_use:
  - "User explicitly wants CrewAI (not LangGraph / OpenAI Agents SDK)"
  - "Building a role-based team of agents (researcher + writer + reviewer) that run in sequence or under a manager"
  - "Wiring deterministic control flow between LLM steps with @start/@listen/@router and branching"
  - "Needs persisted, resumable state so a long pipeline can restart from where it crashed"
  - "Scaffolding a project with the crewai CLI and YAML agent/task config"
  - "Combining Crews (autonomous collaboration) with Flows (deterministic orchestration)"
when_not_to_use:
  - "Graph-based durable workflows without CrewAI's crew abstraction → langgraph-durable-workflows"
  - "OpenAI-native agents, handoffs, and Runner → openai-agents-sdk"
  - "Type-safe single-agent apps with validated outputs → pydantic-ai-typed-agents"
  - "Generic multi-agent design patterns, not CrewAI specifically → agent-orchestration-patterns"
  - "Router/handoff/swarm topology theory rather than CrewAI code → handoff-router-swarm"
keywords: [crewai, crew, flows, "@start", "@listen", "@router", crewbase, agent, task, process, hierarchical, sequential, manager_llm, kickoff, persist, resumable, and_, or_, pydantic-state, crewai-cli, multi-agent, orchestration, crewai-tools]
similar_to: [langgraph-durable-workflows, openai-agents-sdk, pydantic-ai-typed-agents, agent-orchestration-patterns, handoff-router-swarm]
inputs_needed:
  - "Which primitive: a Crew (collaborating agents), a Flow (deterministic orchestration), or both"
  - "LLM provider + API key (OPENAI_API_KEY, or model string like anthropic/claude-..., gemini/..., ollama/...)"
  - "The roles/goals of each agent and the task pipeline, or the event graph of steps"
  - "Whether runs must be resumable (persistence) and any tools each agent needs"
produces: A runnable CrewAI project — Crew (@CrewBase + YAML) and/or Flow (@start/@listen/@router) with optional persisted state.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# CrewAI Flows & Crews Orchestration

Two composable primitives. **Crews** = a team of role-based `Agent`s that autonomously
collaborate on `Task`s (good for open-ended reasoning). **Flows** = deterministic,
event-driven Python that wires steps with `@start`/`@listen`/`@router` and carries typed
state (good for control, branching, and resumable pipelines). Real power = Flows that
`kickoff()` Crews at chosen steps.

## When to use
- User asks for CrewAI by name, a "crew of agents", or `@start`/`@listen`/`@router` flows.
- You need a researcher→writer→reviewer pipeline (Crew) or a branching, resumable
  orchestration (Flow), or a Flow that calls one or more Crews.

## Prerequisites
- **Python 3.10–3.13** (CrewAI requires `>=3.10, <3.14`).
- Install the CLI with uv (recommended) or pip:
  ```bash
  uv tool install crewai          # global CLI: crewai create/run/flow
  # or inside a venv:
  pip install "crewai[tools]"      # library + crewai-tools bundle
  ```
- **An LLM key.** Default provider is OpenAI: `export OPENAI_API_KEY=sk-...`. For other
  providers set the matching key and pass a `model=` / `LLM(...)` string, e.g.
  `anthropic/claude-sonnet-4-5`, `gemini/gemini-2.5-pro`, `ollama/llama3.1`.
- Verify: `crewai version` (0.1x+ series; API below is current for 0.100+).

## Recipe 1 — Scaffold with the CLI
```bash
crewai create crew my_crew     # role-based team, YAML config, main.py
crewai create flow my_flow     # event-driven Flow scaffold (bundles a crew inside)
cd my_flow
crewai install                 # resolve deps into the project's uv venv
crewai run                     # run a crew project
crewai flow kickoff            # run a flow project
crewai flow plot               # render the flow graph to an HTML file
```
Scaffolding writes `.env` (add your key), `config/agents.yaml`, `config/tasks.yaml`,
and a `crew.py` / `main.py`. Edit YAML for prompts, code for wiring.

## Recipe 2 — A Crew with @CrewBase + YAML
`config/agents.yaml` and `config/tasks.yaml` hold the prompts; the class binds them.
YAML supports `{topic}`-style interpolation filled from `kickoff(inputs=...)`.

```python
# crew.py
from crewai import Agent, Crew, Task, Process
from crewai.project import CrewBase, agent, task, crew

@CrewBase
class ResearchCrew:
    agents_config = "config/agents.yaml"   # keys become @agent method names
    tasks_config  = "config/tasks.yaml"

    @agent
    def researcher(self) -> Agent:
        return Agent(config=self.agents_config["researcher"], verbose=True)

    @agent
    def writer(self) -> Agent:
        return Agent(config=self.agents_config["writer"], verbose=True)

    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config["research_task"])

    @task
    def write_task(self) -> Task:
        return Task(config=self.tasks_config["write_task"])  # context flows from prior task

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,   # auto-collected from @agent methods
            tasks=self.tasks,     # auto-collected from @task methods, in order
            process=Process.sequential,
            verbose=True,
        )

if __name__ == "__main__":
    result = ResearchCrew().crew().kickoff(inputs={"topic": "state of edge AI"})
    print(result.raw)            # .raw text; also .pydantic / .json_dict / .tasks_output
```

```yaml
# config/agents.yaml
researcher:
  role: "{topic} Senior Researcher"
  goal: "Find accurate, current facts about {topic}"
  backstory: "A meticulous analyst who cites sources."
writer:
  role: "Tech Content Writer"
  goal: "Turn research into a crisp brief"
  backstory: "You make complex topics readable."
```
```yaml
# config/tasks.yaml
research_task:
  description: "Research {topic}. Gather 5 key findings with sources."
  expected_output: "A bulleted list of 5 findings, each with a source URL."
  agent: researcher
write_task:
  description: "Write a 3-paragraph brief from the research."
  expected_output: "A 3-paragraph markdown brief."
  agent: writer
```

**Hierarchical process** — a manager delegates instead of running tasks in a fixed line.
Requires `manager_llm` **or** `manager_agent` (never assign a manager to a task):
```python
from crewai import LLM
return Crew(agents=self.agents, tasks=self.tasks,
            process=Process.hierarchical,
            manager_llm=LLM(model="gpt-4o"))   # or manager_agent=Agent(...)
```

## Recipe 3 — A Flow with typed state and routing
```python
# main.py
from crewai.flow.flow import Flow, listen, start, router
from pydantic import BaseModel

class PipelineState(BaseModel):     # structured state: attribute access, validated
    topic: str = ""
    score: int = 0
    draft: str = ""

class ContentFlow(Flow[PipelineState]):
    @start()
    def generate(self):
        self.state.draft = f"A draft about {self.state.topic}"
        self.state.score = len(self.state.draft) % 10
        return self.state.draft

    @router(generate)              # returns a label that names the next branch
    def gate(self):
        return "publish" if self.state.score >= 5 else "revise"

    @listen("publish")
    def publish(self):
        return f"PUBLISHED: {self.state.draft}"

    @listen("revise")
    def revise(self):
        return f"NEEDS WORK (score {self.state.score})"

if __name__ == "__main__":
    flow = ContentFlow()
    print(flow.kickoff(inputs={"topic": "resumable agents"}))
    flow.plot("content_flow")      # writes content_flow.html
```
- `@start()` marks entry points (multiple allowed; can label with `@start("after_revise")`).
- `@listen(method)` fires when that method finishes; its return is the listener's arg.
- `@router(method)` returns a **string label**; `@listen("label")` catches it.
- Fan-in: `@listen(and_(a, b))` waits for both; `@listen(or_(a, b))` fires on either.
  Import both from `crewai.flow.flow`.
- Unstructured state: subclass plain `Flow` and use `self.state["key"]` (dict). Every
  state auto-gets a unique `id`.

## Recipe 4 — Flow that kicks off a Crew
```python
from crewai.flow.flow import Flow, start, listen
from my_crew.crew import ResearchCrew

class HybridFlow(Flow):
    @start()
    def pick_topic(self):
        self.state["topic"] = "post-quantum crypto"

    @listen(pick_topic)
    def run_crew(self):
        out = ResearchCrew().crew().kickoff(inputs={"topic": self.state["topic"]})
        self.state["brief"] = out.raw
        return out.raw
```

## Recipe 5 — Persisted, resumable state
Decorate the Flow (or a single method) with `@persist`. State is checkpointed to a local
SQLite store keyed by the state `id`, so a crashed run resumes instead of restarting.
```python
from crewai.flow.flow import Flow, start, listen
from crewai.flow.persistence import persist

@persist                                   # class-level: persist after every method
class DurableFlow(Flow):
    @start()
    def step_one(self):
        self.state["count"] = self.state.get("count", 0) + 1

# resume a specific prior run:
DurableFlow().kickoff(inputs={"id": "<prior-state-id>"})
```

## Verify
- `crewai version` prints the installed version; `python -c "import crewai"` imports clean.
- Run the crew: `crewai run` (or `python crew.py`) → you see agent thoughts (verbose) and a
  final `result.raw`.
- Run the flow: `crewai flow kickoff` → prints the terminal listener's return; then
  `crewai flow plot` (or `flow.plot("f")`) opens an HTML DAG matching your `@listen` wiring.
- Persistence: kill a `@persist` flow mid-run, re-`kickoff` with the same `id`, confirm it
  continues (counter/state advances rather than resetting).

## Pitfalls
- **`kickoff()` vs `.raw`.** `kickoff` returns a `CrewOutput`, not a string. Use `.raw`,
  `.json_dict`, `.pydantic`, or `.tasks_output[i]` — don't concatenate the object directly.
- **Hierarchical needs a manager.** `Process.hierarchical` without `manager_llm`/`manager_agent`
  raises. And never also put a manager agent in the `tasks`' `agent=` — the manager is separate.
- **`@router` must return a string label**, and that exact label must be caught by a
  `@listen("label")`. A returned value with no matching listener silently dead-ends the branch.
- **Structured vs unstructured state don't mix.** `Flow[MyModel]` → `self.state.field`;
  plain `Flow` → `self.state["field"]`. Using `[]` on a Pydantic state (or `.attr` on a dict
  state) fails. Give Pydantic fields defaults so `kickoff` can init empty state.
- **YAML keys must match method names.** With `@CrewBase`, each `@agent`/`@task` method name
  must equal its key in the YAML, or `config=self.agents_config["name"]` KeyErrors.
- **`inputs=` interpolation is literal.** `{topic}` in YAML/`Task.description` only fills if you
  pass `inputs={"topic": ...}`; unmatched braces stay as text.
- **Async.** In async contexts use `await flow.kickoff_async(...)` / `crew.kickoff_async(...)`;
  calling the sync `kickoff` inside a running loop blocks it.
- **Provider drift.** Non-OpenAI models need the provider prefix (`anthropic/…`, `gemini/…`,
  `ollama/…`) and the matching key env var, or CrewAI defaults to OpenAI and 401s.
