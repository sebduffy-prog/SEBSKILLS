---
name: agentsociety-urban-experiment
category: agent-simulation
description: >
  Design and run controlled treatment/control experiments on large LLM-agent
  populations in AgentSociety's urban simulator — inject interventions (messages,
  environment changes, direct state edits), send structured surveys and open
  interviews to targeted agent groups, then diff outcomes from the SQLite replay
  DB. Use when the user wants to A/B test a policy/message on simulated citizens,
  model social or economic behaviour at city scale, run a generative-agent field
  experiment, or "simulate a population and measure how an intervention changes it".
when_to_use:
  - "A/B / treatment-vs-control test of a nudge, message, price, or policy on simulated people"
  - "Run a city-scale LLM-agent social or economic simulation and collect survey data"
  - "Send a questionnaire or interview to a filtered subset of agents (by age, occupation, id)"
  - "Model how an environment shock (weather, rumor, curfew) shifts agent behaviour over days"
  - "Replay and analyse a finished agent-society run to compare group outcomes"
when_not_to_use:
  - "Simulating social-media feeds, posting, and network dynamics — use oasis-social-media-simulation"
  - "Designing one agent's memory/reflection/planning architecture — use generative-agent-architecture"
  - "A tiny 2-5 agent role-play with no surveys/metrics — a plain multi-agent script is lighter"
keywords: [agentsociety, agent society, urban simulation, llm agents, generative agents, treatment control, a/b test, intervention, survey, interview, social simulation, economic simulation, replay, tsinghua fiblab, societyagent, city agents, population simulation]
similar_to: [oasis-social-media-simulation, generative-agent-architecture]
inputs_needed:
  - "Hypothesis + the intervention (message / environment change / state edit) and who receives it"
  - "Agent population size and how to split treatment vs control (id ranges or a filter expression)"
  - "An LLM provider + API key (OpenAI, DeepSeek, Qwen, ZhipuAI GLM-4-Flash is free, or vLLM)"
  - "A map file (download a sample map) and an output/home dir for the SQLite results"
produces: A runnable AgentSociety config.yaml plus extracted treatment-vs-control survey/interview results
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# AgentSociety Urban Experiment

Run controlled experiments on large LLM-driven agent populations in a city
simulator. You define a **workflow** of steps: advance the simulation, inject an
**intervention** into a targeted group, then **survey/interview** everyone and
diff the treatment vs control answers from the SQLite replay database.

Grounded against `agentsociety` **1.5.7** (Apache-2.0, Tsinghua FIB-Lab). Everything
below matches the real Pydantic config classes and the `agentsociety` CLI.

## When to use

Reach for this when the deliverable is a *measured* social/economic experiment on
simulated humans: "does message X make citizens go home?", "how does a price shock
change spending across income groups?", "survey 500 agents before and after a
rumor." If you only need one clever agent, or a social-media feed, use a sibling
skill (see frontmatter).

## Prerequisites

- **Python 3.11 or 3.12** (not 3.13). `pip install agentsociety`
- **An LLM API key.** Providers: `openai`, `deepseek`, `qwen`, `zhipuai`,
  `siliconflow`, `vllm`. ZhipuAI's `glm-4-flash` is free (register at open.bigmodel.cn).
- **A map file.** The simulator needs a `.pb` map. Grab a sample map from the
  project's releases/examples (e.g. a Beijing district) — see the docs
  "custom map" / prerequisites pages. Point `map.file_path` at it.
- **Storage.** v1.5 defaults to **SQLite** (`env.db.db_type: sqlite`) — no Redis,
  Postgres, or MLflow required to run headless. Results land under `env.home_dir`.
  For the web replay UI or multi-tenant scale, switch to `postgresql` with a `pg_dsn`.
- Memory: ~12GB min (32GB for large populations). Cost scales with agents × ticks × LLM calls — start with 20-50 citizens.

## Config anatomy

A `config.yaml` has exactly five top-level sections (Pydantic `Config`):

```yaml
llm:                      # list, min 1
  - provider: zhipuai
    model: glm-4-flash
    api_key: "${ZHIPU_API_KEY}"
    concurrency: 50       # cap parallel LLM calls to dodge rate limits
    # base_url: ...       # optional, for vllm / custom gateways

env:
  db:
    enabled: true
    db_type: sqlite       # or: postgresql  (+ pg_dsn: "postgresql://...")
  home_dir: ./agentsociety_data   # SQLite + artifacts written here

map:
  file_path: ./maps/beijing.pb    # your downloaded map

agents:
  citizens:               # list of AgentConfig, min 1
    - agent_class: citizen        # alias for SocietyAgent
      number: 100
      # memory_distributions: {...}  # or memory_from_file: profiles.json
  # firms: []  banks: []  nbs: []  governments: []   # economic actors, optional
  # supervisor:            # optional agent that INTERCEPTS messages (for message-based interventions)

exp:
  name: rain_nudge_ab
  environment:
    start_tick: 28800      # 08:00 in seconds-of-day
    total_tick: 86400
  workflow:                # ordered list of steps — the heart of the experiment
    - ...
```

## Workflow step types (the experiment DSL)

`exp.workflow` is an ordered list. Each step has a `type` (`WorkflowType`) plus
type-specific fields. The real enum values:

| `type` | Purpose | Key fields |
|--------|---------|-----------|
| `run` | Advance the sim N **days** | `days`, `ticks_per_step` (default 300) |
| `step` | Advance N discrete **steps** | `steps`, `ticks_per_step` |
| `message` | **Intervention:** send text → agent's `react_to_intervention` | `target_agent`, `value` (message) — needs a `supervisor` |
| `environment` | **Intervention:** change a global env var (weather, prompt) | `key`, `value` |
| `update_state` | **Intervention:** directly overwrite an agent memory key | `target_agent`, `key`, `value` |
| `survey` | Send a structured questionnaire | `target_agent`, `survey` |
| `interview` | Ask an open-ended question | `target_agent`, `interview_message` |
| `save_context` | Snapshot an agent memory key for analysis | `target_agent`, `key`, `save_as` |
| `next_round` | Reset agents but **keep memory** (for repeated-measures A/B) | — |
| `delete_agent` | Remove agents mid-run | `target_agent` |
| `function` | Arbitrary code-driven intervention | `func` |

**Targeting** (`target_agent`) is either an explicit id list `[1,2,3]` **or** an
`AgentFilterConfig`:

```yaml
target_agent:
  agent_class: ["citizen"]          # or ["SocietyAgent"]
  filter_str: "${profile.age} >= 18 and ${profile.income} < 3000"
```

`filter_str` reads agent memory via `${profile.<field>}` / `${status.<field>}`.

## Recipe: treatment vs control A/B

The core pattern — split the population, intervene on the treatment half only,
survey both, diff the answers.

```yaml
exp:
  name: rain_go_home_ab
  environment: { start_tick: 28800, total_tick: 86400 }
  workflow:
    # 1. warm up so agents have plans/memory
    - type: run
      days: 1

    # 2. INTERVENTION on treatment group only (ids 1-50)
    - type: environment
      key: weather
      value: "Heavy rain and thunderstorm warning"
    - type: message
      target_agent: [1,2,3,4,5]      # ... treatment ids
      value: "Emergency alert: go home immediately."

    # 3. let behaviour unfold
    - type: run
      days: 1

    # 4. SURVEY everyone (both groups) with the SAME instrument
    - type: survey
      target_agent: { agent_class: ["citizen"] }
      survey:
        id: "a1b2c3d4-0000-0000-0000-000000000001"
        title: "Evening plans"
        pages:
          - name: p1
            elements:
              - name: go_home
                title: "Did you go straight home this evening?"
                type: radiogroup           # choices below
                choices: ["yes","no"]
              - name: concern
                title: "Rate your concern about the weather (1-5)"
                type: rating
                rateMax: 5
```

Question `type` values follow SurveyJS: `radiogroup`, `checkbox`, `rating`,
`text`, `boolean`, `comment`. Keep `id` a valid UUID and **identical** across
runs so results are comparable.

**Control group** = agents you never targeted (ids 51-100). Because the survey
goes to `agent_class: ["citizen"]` (all), the split happens at analysis time by
id — see Verify. For a cleaner design, run two separate configs that differ *only*
in whether the intervention step is present.

## Run it

```bash
export ZHIPU_API_KEY=...          # whatever your provider needs

# validate config + connectivity first (cheap, no LLM spend)
agentsociety check -c config.yaml

# run headless — writes SQLite results under env.home_dir
agentsociety run -c config.yaml

# OR launch the web UI to configure + watch + replay
agentsociety ui -c config.yaml
```

Under the hood the CLI does:
`society = AgentSociety.create(Config.model_validate(cfg), tenant_id); await society.run()`.
To embed in your own async code, call that directly inside `asyncio.run(...)`.

## Analyse / replay

Results are rows in the SQLite DB under `home_dir` (tables prefixed `as_`):
`as_survey(id=agent_id, survey_id, result=JSON)`, `as_dialog` (interviews),
`as_status` (per-tick snapshots). The bundled helper diffs groups for you:

```bash
# see what tables/rows the run produced
python3 scripts/replay_extract.py ./agentsociety_data/<run>.db --list

# compare survey answers: treatment ids vs control ids
python3 scripts/replay_extract.py ./agentsociety_data/<run>.db \
    --treatment 1-50 --control 51-100 --kind survey

# same for open interviews
python3 scripts/replay_extract.py ./agentsociety_data/<run>.db \
    --treatment 1-50 --control 51-100 --kind dialog
```

It introspects tables (tolerant of name suffixes), parses the `result`/`content`
JSON, and prints answer frequencies per group.

## Verify

- `agentsociety check -c config.yaml` exits clean (config + DB reachable).
- After `run`, a `.db` file exists under `home_dir` and `--list` shows non-zero
  `as_survey` / `as_dialog` rows.
- Treatment and control frequency tables differ in the direction your hypothesis
  predicts (and the control group actually got the survey — n>0).
- Re-run with the intervention step removed → the gap should collapse (sanity check
  that the effect is the intervention, not noise).

## Pitfalls

- **`message` interventions silently no-op without a `supervisor` agent** — the
  supervisor is the component that intercepts and delivers messages. Add one, or
  use `environment` / `update_state` which don't require it.
- **No map file = it won't start.** `map.file_path` is mandatory; the sim is
  spatial. Download a real sample map, don't invent a path.
- **Cost/time blow-ups.** Every tick can trigger LLM calls per agent. Start at
  20-50 citizens and 1-2 days; scale only once the workflow is proven. Set
  `llm.concurrency` to respect provider rate limits.
- **Confounded A/B.** If treatment and control differ in anything but the
  intervention (different survey wording, different `start_tick`), the diff is
  meaningless. Keep the instrument and environment identical; vary only the step.
- **`next_round` keeps memory** — great for repeated-measures, but agents
  "remember" the prior condition, so it's not a clean independent-groups design.
- **v1 vs v2.** This targets `agentsociety` (v1.x, urban/economic city sim, Apache-2.0).
  A newer `agentsociety2` package exists with a different Python API; don't mix
  their imports or config schemas.
- **Python 3.13 is unsupported** — pin 3.11/3.12 in your venv.
