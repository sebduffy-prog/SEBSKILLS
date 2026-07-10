---
name: sebduffy
category: meta
description: >
  The one-upload door to the entire SEBSKILLS library. Invoked as /sebduffy, it routes any request to the best
  skill(s) from an embedded catalogue of 300+ skills and loads that skill on demand — whether or not the skill is
  installed locally — so the whole library is reachable from this single file on any Claude surface (Code CLI,
  Desktop, Web, API). Use this whenever the user types "/sebduffy", says "find me a skill", "use my skills",
  "sebskills", "which skill for…", or asks for something a specialised skill would do better. Always reach for it
  to pick and load the right skill instead of improvising.
when_to_use:
  - The user types /sebduffy (optionally followed by an intent, a category, or a skill name)
  - The user asks which skill fits a task, or to use their skill library
  - A request clearly maps to a specialist capability (video, data, agents, design, decks…) and you want the right skill loaded
  - You need to browse or list what skills exist
when_not_to_use:
  - You already know the exact skill and it's installed → invoke that skill directly
  - Authoring a new skill → use skill-creator; adding one to the library → use skill-adder
  - A purely conversational reply with no task → just answer
keywords: [sebduffy, /sebduffy, sebskills, skill router, find a skill, which skill, use my skills, skill library, router, load skill, skill picker, meta]
similar_to: [automatic-skill-decision, requirement-elicitation, skill-gap-detector, skill-chaining-composer, skill-adder]
inputs_needed:
  - The user's intent (free-form), or a category name, or an exact skill name
  - Nothing else — the catalogue is embedded; skill bodies are fetched on demand
produces: The best-matching skill loaded and executed for the user's request (or a short list when ambiguous)
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# /sebduffy — the library router

You are the front door to the whole SEBSKILLS library. The full catalogue is embedded below, so **routing needs
no network**. Only *loading a chosen skill's body* touches the network, and only when it isn't already installed.

## Output discipline — READ FIRST

**Be action-first and quiet. Route, load, and DO the task — never narrate the routing.**

- **Do NOT** print the catalogue, the ranking/scores, the fetch-ladder steps, per-surface notes, or an explanation of what you're "about to do." All of that is internal machinery — the user never sees it.
- Silently pick the best skill, load its body, and **execute the user's actual request** following that skill.
- Preamble = **at most one short line** (e.g. `→ quick-dashboard`) or nothing. No "I'll now…", no restating the task, no summarising what the skill does before doing it.
- Produce a **list only** when the user explicitly types `/sebduffy list`, `/sebduffy <category>`, or `/sebduffy search <term>`.
- Ask a question **only** when the request is genuinely ambiguous or too thin to act on. Otherwise just act.
- If a skill is already loaded/obvious, skip the routing narration entirely and go straight to the work.

The user wants the **result**, not a description of how you got there. Bias hard toward doing over explaining.

## Parse the command

After `/sebduffy`:
- **`<free-form intent>`** → rank the catalogue (below) and load the best skill. If the top two are close, ask which.
- **`list`** → show the catalogue grouped by category.
- **`<category>`** (e.g. `/sebduffy media`) → list only that category.
- **`<exact-skill-name>`** → skip ranking, load it directly.
- **`search <term>`** → show all matching rows + scores, don't auto-load.
- **bare `/sebduffy`** → short help + the categories with counts.

## Route (this is `automatic-skill-decision`)

Score each catalogue row against the intent, mirroring the library's ranking:
`+10` if the skill name appears in the query · `+3` per keyword/trigger-word hit · `+1` per shared ≥3-char token ·
`−0.5` per token that appears in a skill's "not for" note. Then:

- **Confident** (clear top score) → load it, don't ask.
- **Ambiguous** (top two within ~25%) → show both with their one-line trigger and ask the user to pick.
- **Too thin to route** (nothing scores, or the request is underspecified) → load **`requirement-elicitation`**
  and ask 2-3 sharp questions, then re-rank. Never guess when the brief is empty.
- **No skill fits** → load **`skill-gap-detector`** → offer `skill-creator`.
- **Compound task** → load **`skill-chaining-composer`** to sequence several skills.

## Load the chosen skill — the fetch ladder (first success wins, never fabricate)

Resolve skill `X` in category `C`, trying in order:

1. **Local install** — read `~/.claude/skills/X/SKILL.md`, then `./.claude/skills/X/SKILL.md`. If found, use it. No network.
2. **Web fetch** — `WebFetch("https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/skills/C/X/SKILL.md")`.
3. **Shell (CLI only)** — `curl -fsSL <raw-url>`; or `gh api repos/sebduffy-prog/SEBSKILLS/contents/skills/C/X/SKILL.md --jq '.content' | base64 -d`.
4. **MCP resource** — if the `sebskills` MCP server is registered, read `skill://body/X`.
5. **Fail loud** — tell the user which skill was wanted, print the raw URL, suggest `install.sh`. **Do not invent the skill's contents.**

Detect your capabilities first (do you have WebFetch? Bash? MCP?) and pick the first rung that's available. The
loaded body becomes your instructions for the rest of the turn. Fetch a skill's bundled files (e.g. `assets/…`) the
same way, by templated URL, only when it references them.

## Per-surface behaviour

- **Code CLI / IDE:** full ladder (local → WebFetch → curl/gh). Most robust.
- **Desktop:** local → WebFetch → MCP body. No arbitrary bash.
- **Web / claude.ai:** if the repo is connected, skills are already local; else WebFetch.
- **API / Agent SDK:** WebFetch tool → else bash tool → else emit the raw URL for the orchestrator to fetch. Never claim to have loaded a skill you couldn't fetch.

## The catalogue

<!-- BEGIN:MANIFEST (generated by scripts/build_manifest.py — do not edit) -->
_Generated index — 415 skills. Do not edit by hand._

| skill | category | trigger |
|---|---|---|
| blender-mcp-asset-import | 3d | Pull real and AI-generated assets into a live Blender session over ahujasid/blender-mcp — Poly Haven HDRIs / PBR textures / models, Sketchfa |
| blender-mcp-bpy-api-navigator | 3d | Write correct bpy the FIRST time instead of guessing — resolve the exact operator argument names, property paths, and enum string values aga |
| blender-mcp-procedural-generation | 3d | Generate PARAMETRIC content in a live Blender session over MCP — build Geometry Nodes trees, stack modifiers (Array / Subsurf / Bevel / Soli |
| blender-mcp-render-review-loop | 3d | Close the visual feedback loop in a live Blender + MCP session: render (or screenshot the viewport), Read the resulting image back, critique |
| blender-mcp-scene-building | 3d | Build and modify a Blender scene over MCP with CORRECT bpy — add primitives, set transforms/parenting, author Principled-BSDF materials, pla |
| blender-mcp-scene-inspection | 3d | Read a Blender scene BEFORE editing it — collection/object hierarchy, per-object detail, data-block counts, render engine, missing external |
| blender-mcp-setup | 3d | Install and wire up the ahujasid/blender-mcp add-on so Claude can drive Blender end-to-end |
| photo-to-3d-asset | 3d | Turn a single product/hero photo (or a text prompt) into a clean, textured, game/AR-ready 3D mesh (GLB) using open image-to-3D models — Huny |
| paid-media-campaign-ops | adtech-ops | Run the media-agency day-job from the terminal: create, list, pause, budget and report on Meta (Facebook/Instagram) ad campaigns with the of |
| a2a-agent-interop | agent-frameworks | Make agents from different frameworks or vendors talk to each other over Google's Agent2Agent (A2A) protocol — publish a discoverable Agent |
| agent-evals-and-tracing | agent-frameworks | Evaluate and trace agentic LLM systems end to end — score whole trajectories and tool-call accuracy, choose deterministic (final-state / exa |
| agent-orchestration-patterns | agent-frameworks | Framework-agnostic reference and decision heuristics for the canonical multi-agent topologies — prompt chaining, routing/classifier, paralle |
| baml-structured-prompts | agent-frameworks | Author LLM functions in BAML (BoundaryML) — a type-safe DSL where input/output classes, enums, and jinja prompt templates compile to a typed |
| classifier-agent-routing | agent-frameworks | Route every user turn to the best specialist agent with a central intent Classifier that keeps a global view of the whole conversation — usi |
| computer-use-agent | agent-frameworks | Scaffold a sandboxed computer/browser-driving agent that operates a real desktop or browser like a human — screenshot then plan then click/t |
| crewai-flows-orchestration | agent-frameworks | Build multi-agent systems with CrewAI — role-based Crews (Agent/Task, sequential or hierarchical process, YAML+Pydantic config via @CrewBase |
| dspy-program-optimization | agent-frameworks | Build and optimize LLM programs with DSPy instead of hand-tuning prompt strings |
| handoff-router-swarm | agent-frameworks | Build handoff-based agent swarms where specialists transfer control directly to each other — no central supervisor |
| human-in-the-loop-approval | agent-frameworks | Put a durable human approval gate in front of any consequential agent action — send email, post to Slack, spend money, deploy, delete, DM a |
| instructor-structured-outputs | agent-frameworks | Get reliable, typed data out of ANY LLM by declaring a Pydantic model as response_model — Instructor patches the provider client so a bad/in |
| langgraph-durable-workflows | agent-frameworks | Build stateful, durable, multi-agent systems with LangGraph — StateGraph with typed state and reducers, supervisor and orchestrator-worker t |
| llm-guardrails-injection-defense | agent-frameworks | Add a standalone, provider-agnostic guardrail layer that defends ANY LLM app against prompt injection, jailbreaks, and unsafe output — input |
| llm-observability | agent-frameworks | Wire full production LLM/agent observability into an existing Claude or OpenAI app with Langfuse — trace every call and agent trajectory (in |
| longhorizon-research-agent | agent-frameworks | Build a DeerFlow-style long-horizon "super-agent" harness that takes a deep multi-step brief and runs it to a finished deliverable — a lead |
| n8n-ai-workflow-automation | agent-frameworks | Build low-code visual AI agents and automations in n8n — 400+ integration nodes plus the LangChain AI nodes (AI Agent, Chat Trigger, chat mo |
| openai-agents-sdk | agent-frameworks | Build multi-agent apps with the OpenAI Agents SDK (the production successor to Swarm) — define Agents with typed tools, wire Handoffs that t |
| prompt-optimization | agent-frameworks | Harden a prompt the eval-driven way: build a tiny labelled eval set, score the current prompt to get a baseline, diagnose the actual failure |
| pydantic-ai-typed-agents | agent-frameworks | Build type-safe Python LLM agents with PydanticAI — a typed deps_type for dependency injection via RunContext, a Pydantic output_type for st |
| swarm-evaluation-harness | agent-frameworks | Evaluate multi-agent swarms at the TRAJECTORY level, not just the final answer — score handoff/routing correctness, per-agent sub-goal (task |
| swarm-guardrails | agent-frameworks | Wrap an LLM app or agent with OpenAI Guardrails so a tripwire HALTS the run before tokens or side-effects are spent — jailbreak blocking, mo |
| agentsociety-urban-experiment | agent-simulation | Design and run controlled treatment/control experiments on large LLM-agent populations in AgentSociety's urban simulator — inject interventi |
| generative-agent-architecture | agent-simulation | Give an LLM agent believable long-run behaviour with Stanford's "Generative Agents" (Smallville) cognitive loop: a memory stream retrieved b |
| oasis-social-media-simulation | agent-simulation | Run agent-based social-media simulations with OASIS (camel-ai/oasis) to model virality, polarization, rumor/misinformation spread, and audie |
| adversarial-skill-forge | building-agents | Harden a Claude skill through generator-vs-adversary self-play over skill-creator's eval harness |
| agent-code-sandbox | building-agents | Give a code-writing agent a secure, ephemeral runtime so LLM-generated code never executes on your host |
| auto-dream-loop | building-agents | Give an agent an idle-time "sleep and dream" self-improvement loop that only ships measured wins |
| autosuggestive-schema-builder | building-agents | Build Lovable.dev / v0-style no-code builders where Claude proposes accept/reject changes against a declarative content schema with a live p |
| claude-api | building-agents | Build, debug, and optimize Claude API / Anthropic SDK apps |
| federated-knowledge-memory | building-agents | Build a shared, append-only, provenance-tracked knowledge store for a whole skill library or agent fleet — any contributor's LLM (any provid |
| mcp-builder | building-agents | Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-design |
| moltbook | building-agents | Run N heterogeneous agents (different models/personas) through structured propose->critique->revise rounds where EVERY proposed change must |
| openclaw-personal-agent-harness | building-agents | Stand up and HARDEN a self-hosted OpenClaw personal-agent gateway (Steinberger's open-source assistant, formerly Clawdbot/Moltbot) that give |
| permanent-agent | building-agents | Stand up an always-on, self-maintaining agent that outlives a single session |
| skill-creator | building-agents | Create, edit, verify, and optimize skills (SKILL.md files) |
| agentic-commerce-integration | commerce | Wire a merchant catalog into ChatGPT Instant Checkout via the Agentic Commerce Protocol (ACP) |
| product-feed-retail-media | commerce | Generate, optimise and debug product-catalog feeds for Google Merchant Center and Meta (Facebook/Instagram) commerce, plus SKU-level retail- |
| consent-privacy-compliance | compliance | Audit and fix digital-advertising privacy compliance before non-consented tags stop serving |
| agent-context-compaction | context-engineering | Keep long-running / multi-turn agents cheap AND sharp by compacting context before the window fills |
| agent-context-db | context-engineering | Give a project agent ONE self-evolving "context database" that unifies episodic memory (what happened), semantic RAG (docs/knowledge) and sk |
| agent-memory-file | context-engineering | Use the filesystem as durable, out-of-context memory for a Claude agent — scoped CLAUDE.md rule files, a NOTES.md progress ledger that survi |
| context-quality-evals | context-engineering | Evaluate the CONTEXT itself, not just the model — run needle-in-a-haystack / RULER-style sweeps, lost-in-the-middle position tests, distract |
| context-window-budgeter | context-engineering | Allocate a fixed token budget across competing context sources (system rules, tools, retrieved docs, memory, chat history) by priority, then |
| managed-agent-memory | context-engineering | Wire a managed memory service into an agent instead of hand-rolling memory files — Mem0 (extract/store/search facts), Zep + Graphiti (tempor |
| prompt-compression | context-engineering | Shrink bloated prompts, few-shot exemplars and RAG context 2-20x with LLMLingua-2 token pruning BEFORE they hit the LLM, cutting input-token |
| structured-memory-layers | context-engineering | Give an agent tiered durable memory that survives across sessions — pick the right tool for the need and wire it in |
| subagent-context-isolation | context-engineering | Keep the orchestrator's context lean by delegating deep work to sub-agents with scoped, isolated context windows and artifact-backed hand-of |
| bulk-content-extraction | data-analysis | Extract clean text plus structured metadata from thousands of heterogeneous files (PDF, DOCX, PPTX, XLSX, HTML, EML, EPUB, RTF, ODT, images) |
| clickhouse-realtime-analytics | data-analysis | Build real-time columnar OLAP over event streams with ClickHouse — ingest millions of events/sec, pre-aggregate on write via incremental mat |
| corpus-dedup-pipeline | data-analysis | Deduplicate large text corpora with a tiered exact -> fuzzy (MinHash/LSH) -> semantic (embeddings) pipeline |
| dagster-asset-pipelines | data-analysis | Build software-defined asset (SDA) pipelines with Dagster — a typed, lineage-aware dependency graph where each node is a data asset (a table |
| data-contracts | data-analysis | Author and enforce data contracts as version-controlled YAML using the Open Data Contract Standard (ODCS v3) and the datacontract-cli |
| data-processing | data-analysis | Clean, transform, deduplicate, normalize, and reshape tabular data with verification at every step |
| data-quality-validation | data-analysis | Validate a dataframe or CSV/Parquet with declarative schema + rule checks before you trust it — use Pandera (typed DataFrameModel, lazy erro |
| data-schema | data-analysis | Inspect, validate, document, and design tabular data schemas with verification at every step |
| dbt-analytics-engineering | data-analysis | Build a production dbt Core project the way analytics engineers actually do it — sources + freshness, staging/intermediate/marts layering, g |
| dlt-python-pipelines | data-analysis | Build declarative extract-and-load pipelines in pure Python with dlt (dlthub) — pull from REST APIs, SQL databases, or files and land them i |
| duckdb-analytics | data-analysis | Run fast in-process analytical SQL over Parquet/CSV/JSON/Arrow — directly on local files, globs, S3, or HTTPS — with zero server setup and l |
| ducklake-lakehouse | data-analysis | Stand up a real lakehouse with DuckLake — a SQL catalog (SQLite/Postgres/DuckDB) for metadata plus Parquet data files on local disk or S3 — |
| embedding-corpus-clustering | data-analysis | Turn a pile of unlabeled text (docs, tickets, reviews, headlines, transcripts, survey verbatims) into interpretable topics/clusters using se |
| excel-forecasting-formulas | data-analysis | Build formula-only time-series forecasts inside an Excel workbook — no add-ins, no Python |
| excel-monte-carlo-formulas | data-analysis | Run a Monte-Carlo simulation in Excel using formulas ONLY — no VBA, no @RISK, no add-ins |
| exploratory-data-analysis | data-analysis | Produce rigorous exploratory analysis of a dataset — distributions, central tendency, dispersion, correlations, outliers — with every report |
| firecrawl-scrape | data-analysis | Turn any URL or entire website into clean, LLM-ready markdown or schema-validated JSON using Firecrawl — scrape (one page), crawl (a whole s |
| free-api-catalogue | data-analysis | Curated, verified lookup index of high-value FREE / public APIs — FX & crypto, weather & climate, geocoding & places, government & economic |
| geocoding-places-api | data-analysis | Turn addresses and place names into lat/lon and back, then enrich with POIs, administrative boundaries, road distances and drive/walk-time i |
| geospatial-analysis | data-analysis | Turn location data into analysis and maps with GeoPandas + leafmap — load shapefiles/GeoJSON, build points from lat/lon, reproject CRS, run |
| govt-open-data-api | data-analysis | Pull real government & open-data programmatically from CKAN and Socrata portals (data.gov, data.gov.uk, data.cityofchicago.org, thousands mo |
| incremental-content-index | data-analysis | Maintain a resumable, content-addressable index over a growing file collection so re-runs process ONLY new or changed files, never the whole |
| interactive-web-maps | data-analysis | Render location data as interactive web maps with MapLibre GL + deck.gl — choropleths shaded by any metric, store/dealer locators with popup |
| magika-file-triage | data-analysis | Detect the TRUE content type of huge, mislabeled, or extensionless file collections and route each file to the right parser using Google Mag |
| marimo-reactive-notebook | data-analysis | Build reactive Python notebooks with marimo — notebooks stored as plain .py (git-diffable, importable, no hidden state), where changing one |
| market-data-api | data-analysis | Pull finance and macroeconomic data from free public APIs into tidy, date-aligned datasets |
| mathematical-computation | data-analysis | Solve mathematics problems — algebra, calculus, linear algebra, ODEs, probability, combinatorics — with symbolic computation in SymPy AND nu |
| news-sentiment-api | data-analysis | Pull free news coverage volume, tone and entity signals from GDELT DOC 2.0 (global tone/volume firehose, no key), Marketaux (financial news |
| parquet-arrow-optimization | data-analysis | Design columnar storage that actually reads fast — pick compression (zstd vs snappy) and tune row-group size, partition + sort files for pre |
| perceptual-image-dedup | data-analysis | Find exact and near-duplicate images across huge photo/asset libraries |
| polars-dataframes | data-analysis | Reach for Polars when pandas is too slow or blows past RAM |
| resilient-scraper | data-analysis | Build a polite, reliable HTTP scraper in Python that doesn't get banned or drop data — httpx (async + HTTP/2) with tenacity exponential back |
| sitemap-crawl-harvest | data-analysis | Enumerate a site's FULL URL surface before you crawl |
| sqlmesh-transformations | data-analysis | Build in-warehouse SQL transformation pipelines with SQLMesh — the dbt alternative that gives you virtual data environments (zero-copy dev v |
| statistical-testing | data-analysis | Run the correct statistical test for the user's question, check assumptions before running it, and report effect size + confidence interval |
| stealth-browser-scraping | data-analysis | Get past Cloudflare Turnstile, DataDome, Akamai, PerimeterX and Kasada bot walls when plain requests/httpx and vanilla headless Chrome/Playw |
| structured-page-extraction | data-analysis | Turn one raw HTML page into typed, schema-validated records |
| synthetic-data-generation | data-analysis | Generate realistic synthetic datasets that preserve the statistical structure of a real table — reach for SDV (GaussianCopula / CTGAN / TVAE |
| time-series-forecasting | data-analysis | Forecast a time series in Python with Nixtla StatsForecast (AutoARIMA, AutoETS, AutoTheta, MSTL) or TimeGPT — backtest with rolling cross-va |
| weather-climate-api | data-analysis | Pull weather forecasts, ERA5 historical climate reanalysis (1940→now), and air-quality from free APIs to use as model covariates or narrativ |
| web-change-monitor | data-analysis | Watch web pages for MEANINGFUL changes, not raw byte churn |
| wikidata-knowledge-api | data-analysis | Query structured world knowledge and public-attention signals from Wikimedia — Wikidata SPARQL for the entity graph (occupations, birthplace |
| zero-shot-auto-tagging | data-analysis | Auto-tag and classify a large document collection into a KNOWN taxonomy without labelled training data |
| dockerfile-and-compose-authoring | devops | Author lean, secure Dockerfiles and Compose files and lint them with hadolint |
| github-actions-pipelines | devops | Build robust, secure GitHub Actions CI/CD — matrix builds, dependency caching, reusable + composite workflows, OIDC cloud auth (no long-live |
| gitops-argocd-flux | devops | Set up pull-based GitOps delivery with Argo CD or Flux — git as the single source of truth, a controller that continuously reconciles the cl |
| incident-response-and-postmortem | devops | Run a live production incident and its blameless postmortem end to end |
| kubernetes-workload-deploy | devops | Ship a containerised app to Kubernetes properly |
| load-testing-k6 | devops | Write and run k6 (or Locust) load tests that model real traffic — ramping VUs, constant arrival-rate spikes, staged soak tests — and gate CI |
| opentelemetry-observability-slo | devops | Verb-first trigger when you must instrument a service with OpenTelemetry (traces, metrics, logs), stand up an OTel Collector, ship signals t |
| terraform-iac-modules | devops | Author production Terraform / OpenTofu — reusable modules with typed variables + outputs, remote state with locking (S3 native lockfile or D |
| accessible-document-remediation | documents | Use to make a PDF accessible and legally compliant — tag it for screen readers (PDF/UA-1 / ISO 14289), fix WCAG 2.1 AA structure, add alt te |
| board-pack-exec-brief | documents | Write dense, decision-first executive briefs — board pre-reads, ExCo/SLT decision memos, Amazon-style 6-pagers, options papers, and one-page |
| contract-review | documents | Review commercial contracts — MSAs, SOWs, NDAs, DPAs, order forms — the way a deal lawyer does: extract every obligation, deadline, payment |
| data-driven-deck-generator | documents | Generate a data-driven PowerPoint deck where every chart and headline is bound to real data — read a CSV/DataFrame/dict, build NATIVE editab |
| dcf-lbo-valuation-model | documents | Build a fully-linked DCF and LBO valuation in one Excel workbook — formulas only, zero hardcoded outputs — so every cell recalculates live w |
| doc-coauthoring | documents | Guide users through a structured workflow for co-authoring documentation |
| document-assembly-mail-merge | documents | Mass-produce personalised Word documents from ONE .docx template plus a data source (CSV / JSON / Excel) using docxtpl (python-docx-template |
| docx | documents | Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files) |
| docx-redline-compare | documents | Generate a Word tracked-changes redline (native w:ins / w:del markup) between two .docx versions so reviewers see exactly what changed and c |
| editorial-style-linter | documents | Enforce a deterministic editorial house style with Vale — flag banned terms, UK/US spelling drift, wordy phrases, inconsistent capitalisatio |
| excel-dynamic-array-formulas | documents | Replace VLOOKUP-drag, helper columns, and manual pivot tables with spilling dynamic-array formulas — FILTER, SORT, SORTBY, UNIQUE, SEQUENCE |
| excel-kpi-dashboard-formulas | documents | Build a single-screen, formula-driven KPI dashboard in Excel with zero VBA or macros — a SWITCH/CHOOSE metric selector wired to a dropdown |
| excel-lambda-functions | documents | Build reusable, named custom functions in Excel with LET and LAMBDA — no VBA, no add-ins |
| excel-model-audit | documents | Error-proof and stress-test a spreadsheet financial model against FAST and ICAEW standards |
| excel-scenario-sensitivity | documents | Build deterministic what-if analysis in a real .xlsx — native one- and two-variable Data Tables (Excel's {=TABLE()} array via openpyxl DataT |
| google-workspace-authoring | documents | Author and edit native Google Slides, Docs, and Sheets programmatically via the batchUpdate APIs — build decks, briefs, and trackers with re |
| i18n-localization-qa | documents | QA a localisation before it ships |
| internal-comms | documents | A set of resources to help me write all kinds of internal communications, using the formats that my company likes to use |
| meeting-intelligence | documents | Turn a meeting recording or raw transcript into a clean deliverable pack: minutes, a decisions log, an owner/deadline action table, and read |
| pdf | documents | Use this skill whenever the user wants to do anything with PDF files |
| pptx | documents | Use this skill any time a .pptx file is involved in any way — as input, output, or both |
| rfp-proposal-response | documents | Run a solicitation (RFP/RFI/ITT/PQQ/tender) from receipt to submission-ready draft the way a new-business/bid team does: shred the document |
| three-statement-financial-model | documents | Build a fully-linked three-statement financial model (income statement, balance sheet, cash flow) in Excel with FORMULAS ONLY — every foreca |
| xlsx | documents | Use this skill any time a spreadsheet file is the primary input or output |
| api-contract-design | engineering-workflow | Design and lint a REST API contract properly — author OpenAPI 3.1 (JSON Schema 2020-12) with reusable components, enforce house style with a |
| ast-grep-codemod | engineering-workflow | Run structural (AST-based) search-and-rewrite across a codebase with ast-grep — tree-sitter patterns, `$META` capture variables, YAML rule f |
| autonomy-policy | engineering-workflow | Use at the start of EVERY task to decide whether to proceed autonomously or pause and converse with the user |
| brainstorming | engineering-workflow | You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior |
| changelog-release-automation | engineering-workflow | Automate versioning and releases from git history — wire up Conventional Commits, generated CHANGELOGs, SemVer bumps, git tags, and GitHub R |
| coding-standards | engineering-workflow | Baseline cross-project coding conventions for naming, readability, immutability, and code-quality review |
| continuous-learning-v2 | engineering-workflow | Instinct-based learning system that observes sessions via hooks, creates atomic instincts with confidence scoring, and evolves them into ski |
| debugging-and-error-recovery | engineering-workflow | Guides systematic root-cause debugging |
| dependency-upgrade-migration | engineering-workflow | Upgrade dependencies without breaking the build |
| dispatching-parallel-agents | engineering-workflow | Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies |
| email-deliverability | engineering-workflow | Diagnose and fix why email lands in spam or gets rejected |
| executing-plans | engineering-workflow | Use when you have a written implementation plan to execute in a separate session with review checkpoints |
| finishing-a-development-branch | engineering-workflow | Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development wor |
| flaky-test-detection | engineering-workflow | Catch, quarantine, and root-cause flaky tests — the ones that pass and fail on IDENTICAL code and poison CI trust |
| flow-reader | engineering-workflow | Read, interpret, and act on any flow-shaped diagram — UI/UX site maps, user journeys, state machines, agent graphs, workflow diagrams, syste |
| git-workflow | engineering-workflow | Git workflow patterns including branching strategies, commit conventions, merge vs rebase, conflict resolution, and collaborative developmen |
| incremental-implementation | engineering-workflow | Delivers changes incrementally |
| karpathy-guidelines | engineering-workflow | Behavioral guidelines to reduce common LLM coding mistakes |
| lsp-code-navigation | engineering-workflow | Wire a real Language Server (tsserver, pyright, gopls, rust-analyzer) into an agent over the jonrad/lsp-mcp MCP bridge so it answers go-to-d |
| mutation-testing | engineering-workflow | Measure the REAL quality of a test suite by injecting mutants (flip `>` to `>=`, `+` to `-`, delete a return) and checking whether tests cat |
| openapi-client-codegen | engineering-workflow | Generate a fully typed API client from an OpenAPI/Swagger spec with orval — TypeScript models, fetch/axios call functions, Zod request+respo |
| property-based-testing | engineering-workflow | Stop hand-picking example inputs — assert PROPERTIES ("output is always sorted", "decode(encode(x))==x") and let a generator hurl hundreds o |
| receiving-code-review | engineering-workflow | Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - |
| repo-context-packer | engineering-workflow | Pack a whole codebase, subfolder, or remote GitHub repo into ONE AI-ready context bundle with repomix — directory tree + per-file contents |
| requesting-code-review | engineering-workflow | Use when completing tasks, implementing major features, or before merging to verify work meets requirements |
| security-review | engineering-workflow | Use this skill when adding authentication, handling user input, working with secrets, creating API endpoints, or implementing payment/sensit |
| semantic-code-search | engineering-workflow | Stand up a local-first semantic (embedding) code index with SeaGOAT so an agent finds code by MEANING, not literal grep — ask "where do we r |
| source-driven-development | engineering-workflow | Grounds every implementation decision in official documentation |
| spec-driven-development | engineering-workflow | Creates specs before coding |
| subagent-driven-development | engineering-workflow | Use when executing implementation plans with independent tasks in the current session |
| systematic-debugging | engineering-workflow | Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes |
| tdd-workflow | engineering-workflow | Use this skill when writing new features, fixing bugs, or refactoring code |
| test-driven-development | engineering-workflow | Use when implementing any feature or bugfix, before writing implementation code |
| using-git-worktrees | engineering-workflow | Use when starting feature work that needs isolation from current workspace or before executing implementation plans - creates isolated git w |
| using-superpowers | engineering-workflow | Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including c |
| verification-before-completion | engineering-workflow | Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and |
| verification-loop | engineering-workflow | A comprehensive verification system for Claude Code sessions |
| writing-plans | engineering-workflow | Use when you have a spec or requirements for a multi-step task, before touching code |
| finance-accounting-ops | finance-ops | Run daily bookkeeping against Xero and QuickBooks Online: parse invoices and receipts into structured lines, reconcile bank statements to th |
| accessibility | frontend-and-design | Design, implement, and audit inclusive digital products using WCAG 2.2 Level AA standards |
| accessible-contrast-checker | frontend-and-design | Check AND auto-fix colour contrast before you ship a palette |
| ag-ui-agent-frontend | frontend-and-design | Wire an AG-UI-speaking agent backend into a React/Next.js frontend with CopilotKit — stream agent events (text, tool calls, shared state, re |
| agent-browser | frontend-and-design | Drive a real Chrome browser from the CLI to view, test, screenshot and debug web pages — the visual-QA loop for any frontend work |
| agentic-web-automation | frontend-and-design | Automate multi-step, natural-language web tasks when CSS/XPath selectors are too brittle to maintain — drive an LLM agent loop that observes |
| algorithmic-art | frontend-and-design | Creating algorithmic art using p5.js with seeded randomness and interactive parameter exploration |
| brand-color-token-system | frontend-and-design | Turn ONE brand hex into a complete 50->950 tonal ramp with a semantic token layer and light/dark parity, exported as CSS custom properties |
| brand-guidelines | frontend-and-design | Applies Anthropic's official brand colors and typography to any sort of artifact that may benefit from having Anthropic's look-and-feel |
| brand-voice | frontend-and-design | Build a source-derived writing style profile from real posts, essays, launch notes, docs, or site copy, then reuse that profile across conte |
| browser-qa | frontend-and-design | Use this skill to automate visual testing and UI interaction verification using browser automation after deploying features |
| browser-testing-with-devtools | frontend-and-design | Tests in real browsers |
| canvas-design | frontend-and-design | Create beautiful visual art in .png and .pdf documents using design philosophy |
| click-path-audit | frontend-and-design | Trace every user-facing button/touchpoint through its full state change sequence to find bugs where functions individually work but cancel e |
| code-review-and-quality | frontend-and-design | Conducts multi-axis code review |
| color-harmony-generator | frontend-and-design | Generate complementary, analogous, triadic, split-complementary, tetradic and square colour harmonies by rotating hue in OKLCH so every swat |
| color-psychology-advertising | frontend-and-design | Choose ad and brand colours using what the peer-reviewed evidence actually supports — and refuse to over-claim |
| colorblind-safe-palettes | frontend-and-design | Pick, validate, and repair categorical colour palettes for colour-vision deficiency (protan/deutan/tritan ~8% of men, 0.5% of women) |
| dashboard-information-architecture | frontend-and-design | Lay out data-dense dashboards so they actually get READ — decide KPI hierarchy, scan order, density-tier grids, and drill-down layering BEFO |
| design-approval-gate | frontend-and-design | Use BEFORE shipping any visual or UI change — new components, new pages, landing pages, hero sections, theme changes, ui-effects integration |
| design-system | frontend-and-design | Use this skill to generate or audit design systems, check visual consistency, and review PRs that touch styling |
| design-tokens-pipeline | frontend-and-design | Build a full W3C DTCG design-token pipeline with Style Dictionary v5 — spacing, radius, shadow, typography, motion/duration, and color — com |
| filmic-static-panels | frontend-and-design | Recreate the cinematic "static" container look — dark gradient panels (raised→surface, hairline border, soft radius, depth shadow) sitting u |
| fluid-responsive-system | frontend-and-design | Generate breakpoint-free fluid type, space and grid using CSS clamp() interpolation — the Utopia method — so headings, body text, gaps and m |
| frontend-design | frontend-and-design | Create distinctive, production-grade frontend interfaces with high design quality |
| frontend-ui-engineering | frontend-and-design | Builds production-quality UIs |
| generative-ui-chat-interface | frontend-and-design | Build a streaming AI chat / generative-UI front-end with the Vercel AI SDK v7 (useChat + DefaultChatTransport) and AI Elements |
| html-email-builder | frontend-and-design | Build client-proof HTML email that survives Outlook, Gmail and Apple Mail — pick MJML, React Email or Maizzle, get table-based layout with i |
| icon-system | frontend-and-design | Stand up ONE consistent icon system instead of pasting random SVGs from everywhere — pick a source (Lucide for a curated stroke set, Iconify |
| image-palette-extraction | frontend-and-design | Extract a dominant palette from a photo, poster, or logo and turn it into a usable theme — quantise pixels (median-cut, k-means/WSMeans, or |
| motion-system | frontend-and-design | Define a reusable motion design system instead of hand-tuning every transition — a small named scale of duration, easing, spring and stagger |
| oklch-color-engine | frontend-and-design | Do perceptually-uniform colour work in OKLCH/OKLab — parse any input, convert to OKLCH, build even lightness/chroma ramps, interpolate gradi |
| perceptual-gradient-designer | frontend-and-design | Design banding-free multi-stop gradients by interpolating in OKLab/OKLCH instead of naive sRGB — kills the grey dead-zone where blue→yellow |
| performance-optimization | frontend-and-design | Optimizes application performance |
| print-editorial-layout | frontend-and-design | Turn HTML/CSS into print-quality paginated PDFs with Paged.js |
| professional-page-templates | frontend-and-design | Build professionally-designed marketing pages, product sites, portfolios, dashboards, conference pages, newsrooms, and experiential scrollyt |
| pwa-installable-offline | frontend-and-design | Make a Vite web app installable and offline-capable with vite-plugin-pwa (Workbox under the hood) |
| quick-chart | frontend-and-design | Render ONE correct chart from a dataset in a single self-contained HTML file — auto-pick the right chart type (bar/line/scatter/doughnut) fr |
| quick-dashboard | frontend-and-design | Turn CSV, JSON, or pasted rows into ONE self-contained responsive dashboard HTML file — a KPI stat row, 2–3 Chart.js charts, and one sortabl |
| quick-form | frontend-and-design | Ship a production-quality contact / signup / feedback form as ONE self-contained HTML file — semantic fields, real-time inline validation, a |
| quick-landing | frontend-and-design | Ship one polished, single-file HTML + Tailwind (Play CDN) landing page in under 2 minutes, no build step — semantic hero, exactly 3 feature |
| quick-microsite | frontend-and-design | Ship a polished 2-4 "page" static microsite (event, product launch, personal profile, docs-lite) as ONE self-contained HTML file using ancho |
| quick-tool | frontend-and-design | Ship one single-purpose interactive tool — calculator, unit/currency converter, generator (password, slug, QR-input, color), picker, scorer/ |
| recording-studio | frontend-and-design | Stand up a branded, deploy-ready artist cultural-intelligence & campaign-tracking platform ("The Recording Studio") for a Warner Music artis |
| shadcn-tailwind-v4-stack | frontend-and-design | Scaffold the dominant 2026 React build stack — Tailwind CSS v4 (CSS-first, zero config file) plus shadcn/ui components — the correct, non-br |
| svg-illustration-animation | frontend-and-design | Animate SVG illustrations with GSAP's now-free (since 2025) plugins — DrawSVGPlugin for self-drawing line art, MorphSVGPlugin for shape-to-s |
| theme-factory | frontend-and-design | Toolkit for styling artifacts with a theme |
| typography-type-system | frontend-and-design | Build a real typography system, not just font-sizes — a modular scale with a named ratio, fluid clamp() steps, variable-font axes wired corr |
| ui-demo | frontend-and-design | Record polished UI demo videos using Playwright |
| vccp-logo-use | frontend-and-design | Apply the four official VCCP bear-and-girl logo lockups — `Logo.png`, `Bear_Lockup.png`, `Girl_Lockup.png`, `Girl_and_Bear.png` — to client- |
| vccp-media-design | frontend-and-design | Apply the VCCP Media 2026 brand system to any client-facing artifact — web pages, web apps, dashboards, slide decks (PPTX / Keynote / Google |
| visual-regression-testing | frontend-and-design | Set up pixel-diff screenshot baseline testing so UI changes are caught by comparing rendered screenshots against approved baselines |
| web-artifacts-builder | frontend-and-design | Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS |
| webapp-testing | frontend-and-design | Toolkit for interacting with and testing local web applications using Playwright |
| webgl-3d-scene | frontend-and-design | Build a production-grade 3D scene on the web with React Three Fiber (Three.js) — a Canvas with proper camera and lighting rigs, GLTF model l |
| geo-incrementality-testing | marketing-science | Design and analyse geo holdout / geo-lift experiments to measure the TRUE incremental effect of a media campaign — not correlated last-click |
| marketing-mix-modeling | marketing-science | Build a Bayesian marketing-mix model to measure media ROI, decompose sales, and optimise budget |
| multi-touch-attribution | marketing-science | Attribute conversions across the multi-touch customer journey with data-driven models, not just last-click |
| uplift-modeling | marketing-science | Model who a campaign actually CHANGES — not who converts anyway — with uplift / heterogeneous-treatment-effect models, then target the persu |
| connect-database-mcp | mcp-connectors | Wire a SQL database into Claude Code over MCP for safe, read-only querying — Postgres, MySQL, SQLite, BigQuery (and 20+ more) via the google |
| connect-github-mcp | mcp-connectors | Wire up GitHub's OFFICIAL MCP server so Claude can drive repos, issues, PRs, code search, and Actions natively — no `gh` binary, no shelling |
| connect-playwright-mcp | mcp-connectors | Register and drive a real browser over MCP with Microsoft's Playwright MCP server (@playwright/mcp) |
| connect-public-api | mcp-connectors | Talk to ANY public/REST API robustly when you have a URL and docs but no ready-made SDK or MCP server |
| connect-web-fetch-scrape-mcp | mcp-connectors | Wire up an MCP server to pull web content into Claude — the lightweight Fetch server (URL -> markdown, no key) vs Firecrawl (JS-rendered pag |
| mcp-apps-interactive-ui | mcp-connectors | Build MCP Apps (the ext-apps / SEP-1865 extension, spec 2026-01-26) so an MCP tool returns an INTERACTIVE UI — a chart, form, picker, dashbo |
| mcp-server-security | mcp-connectors | Secure an MCP server and vet third-party ones before you connect |
| mcp-tool-gateway-router | mcp-connectors | Fight MCP tool sprawl and context bloat when a session aggregates many servers (GitHub + Slack + Sentry + DB + Adobe = 200+ tools, ~55k toke |
| register-mcp-servers | mcp-connectors | Install, register, and manage MCP servers in Claude Code, Claude Desktop, and remote clients |
| ai-upscale-restore | media | AI-upscale and restore low-res or degraded images and video, and fix damaged faces |
| audio-loudness-ducking | media | Fix audio levels the right way with ffmpeg: two-pass EBU R128 loudnorm to hit an exact platform target (-14 LUFS for YouTube/Spotify/TikTok/ |
| audio-mastering-chain | media | Master and finish a mix to a delivery-ready file with Matchering + ffmpeg |
| auto-silence-cut | media | Auto jump-cut talking-head, tutorial, podcast, or screen-recording footage by detecting and removing (or speeding up) the silent gaps — dead |
| background-removal-batch | media | Batch-remove image backgrounds to transparent PNGs (real alpha) using rembg with BiRefNet / BRIA RMBG / IS-Net / U²-Net models, plus optiona |
| batch-transcode-encode | media | Batch-transcode a whole FOLDER of videos to clean H.264/H.265 MP4, or make lightweight editing PROXIES, with the RIGHT codec + quality choic |
| beat-synced-edit | media | Cut video to the beat of music — detect the beat grid, downbeats, or transient onsets in a track with librosa (beat_track / onset_detect), t |
| channel-playlist-archive | media | Bulk-lift a whole YouTube channel or playlist with yt-dlp, using a --download-archive file so re-runs SKIP everything already grabbed (perfe |
| comfyui-workflow-runner | media | Headlessly execute a ComfyUI workflow from the command line via its HTTP + WebSocket API — POST the API-format node graph to /prompt, track |
| contact-sheet-storyboard | media | Turn a video into a single contact-sheet / storyboard grid — evenly-spaced thumbnails tiled into rows and columns with the source timecode b |
| controllable-video-to-video | media | Restyle, relight, recompose, or VFX an EXISTING clip while keeping its motion — video-to-video, not fresh generation |
| ffmpeg-cookbook | media | Battle-tested, copy-pasteable ffmpeg recipes with the CORRECT flags for each job: losslessly concat/stitch clips, trim/cut without re-encodi |
| flux-image-gen | media | Generate or instruction-edit images with the Flux family (FLUX.2 / FLUX.1 Kontext / Pro / dev) via the Black Forest Labs API, fal.ai, or Rep |
| frame-interpolation-retiming | media | Generate synthetic in-between frames to make video smoother — buttery slow-motion from ordinary 30fps footage, or up-convert a clip's frame |
| hdr-tonemap-color | media | Fix washed-out, grey, milky, or over-bright HDR video by correctly tonemapping HDR (BT.2020 PQ/HLG) down to SDR (BT.709) with ffmpeg zscale+ |
| keyframe-motion-frame-diff | media | Frame-diff analysis for video: collapse thousands of near-identical frames into a handful of UNIQUE keyframes using perceptual hashing (phas |
| lip-sync-avatar | media | Make a face TALK — drive lips on a photo or video clip from any audio/VO so a spokesperson, presenter, or dubbed actor mouths the words |
| long-video-to-shorts | media | Turn ONE long video (podcast, interview, webinar, lecture, stream VOD) into a ranked set of vertical 9:16 shorts — transcribe it, find and s |
| lottie-motion-graphics | media | Generate and template Lottie JSON animations in code, then render them to MP4/GIF/WebM — for versioned logo stings, animated lower-thirds, a |
| media-toolchain-bootstrap | media | One-shot macOS setup or repair of the local media toolchain WITHOUT Homebrew or sudo: installs the standalone yt-dlp_macos binary, a portabl |
| music-generation-jingle | media | Generate original music, jingles, stings, loops, and underscores from a text prompt using open models (MusicGen / AudioCraft, Stable Audio O |
| nano-banana-image | media | Generate and edit images with Google's Nano Banana (Gemini Flash Image, gemini-2.5-flash-image) via the Gemini API — the model that actually |
| open-video-gen-wan | media | Self-host open-weight text-to-video and image-to-video on your OWN GPU with license-clean models — Wan 2.2 (MoE A14B + the 24GB-friendly TI2 |
| sfx-foley-generation | media | Generate sound effects and foley from a TEXT prompt — footsteps, whooshes, impacts, UI clicks, ambience, stingers — via ElevenLabs SFX v2 (c |
| shot-scene-detection | media | Detect every shot boundary / scene cut in a video and produce a timecoded shot list plus split clips |
| slack-gif-creator | media | Knowledge and utilities for creating animated GIFs optimized for Slack |
| social-video-reframe | media | Reframe (recrop) horizontal 16:9 video into vertical 9:16, square 1:1, or portrait 4:5 for Reels, Shorts, and TikTok — with subject-aware sm |
| stem-separation | media | Split a song into separate stems — vocals, drums, bass, and other (or guitar/piano with the 6-source model) — using Demucs (Hybrid Transform |
| typographic-image-gen | media | Generate ad comps where the IN-IMAGE TEXT is legible, correctly spelled, and on-brand — OOH/billboard posters, pack shots, price flashes, me |
| video-audio-rip | media | Rip audio-only files (mp3 / m4a / opus / flac / wav) from a YouTube URL, podcast page, or a local video file — with embedded cover art and c |
| video-clip-extractor | media | Grab ONLY the part you want out of a video — a single timestamp range (e.g |
| video-frame-extraction | media | Extract video frames to PNG/JPG with ffmpeg — pull every frame, every Nth frame, one per second, keyframes only, or a single frame at an exa |
| video-gen-pipeline | media | Generate short AI video clips from text (or a first-frame image) with the current model catalogue — Veo 3.1, Kling 2.1/3.0 Pro, Seedance 2.0 |
| video-matting-rotoscope | media | Pull a temporally-stable alpha matte off a person/subject across a whole video with RobustVideoMatting (RVM) — clean, flicker-free green-scr |
| video-object-tracking-sam2 | media | Track, segment and mask ONE (or several) objects across every frame of a video with SAM 2 / SAM 2.1 from a single click, box or point prompt |
| video-ocr-onscreen-text | media | Read text that is baked into a video's pixels — rip hardcoded/burned-in subtitles to a timed SRT, and log every lower-third, name super, chy |
| voice-clone-tts | media | Generate spoken narration and voiceover LOCALLY — few-shot voice cloning from a ~10s reference clip (Chatterbox / GPT-SoVITS) or fast preset |
| whisper-caption-burn | media | Generate word-level Whisper captions and turn them into animated TikTok/Reels-style karaoke subtitles (active word pops + accent colour), th |
| youtube-download | media | Download a YouTube (or any yt-dlp-supported) video to a local file with robust format/resolution choice, and survive 2026-era breakage: SABR |
| youtube-transcript-lift | media | Pull a clean, readable text transcript out of a YouTube (or any yt-dlp-supported) video WITHOUT downloading the video |
| sebduffy | meta | The one-upload door to the entire SEBSKILLS library |
| automatic-skill-decision | meta-router | Given any user request, silently pick the right skill(s) from a SKILL.md manifest by scoring trigger keywords + semantic intent, then apply |
| requirement-elicitation | meta-router | Detect when a request is underspecified and, before acting, ask the minimum set of high-value clarifying questions that fully dissect the ta |
| skill-adder | meta-router | Contribute a NEW skill into the SEBSKILLS library through a guarded, gated intake — a "PR-merge for skills" |
| skill-auditor | meta-router | Audit a SEBSKILLS skill for both correctness AND whether it actually works — a STATIC pass (all 10 frontmatter fields present, name==folder |
| skill-chaining-composer | meta-router | Turn ONE compound request into an ordered chain of skills: decompose the job into sub-tasks, map each sub-task to the right skill, order the |
| skill-gap-detector | meta-router | Detect when NO existing skill covers the user's request, name the missing capability precisely, and hand off to skill-creator to author it |
| skill-marketplace-packager | meta-router | Package SEBSKILLS skills as portable, harness-agnostic bundles so the library installs beyond Claude Code — into Codex CLI, Cursor, OpenCode |
| build-train-gnn | ml | Build and train Graph Neural Networks with PyTorch Geometric (PyG) |
| conformal-prediction | ml | Wrap ANY trained model (sklearn, XGBoost, TabPFN, even an API model) with conformal prediction to get distribution-free, calibrated uncertai |
| embedding-model-training | ml | Fine-tune embedding (bi-encoder) and reranker (cross-encoder) models with Sentence Transformers v3/v4 — pick the right loss for your data sh |
| gradient-boosting-tabular | ml | Build a strong tabular ML model with gradient-boosted trees (XGBoost / LightGBM / CatBoost) for churn, propensity, lead-scoring, conversion |
| lora-qlora-finetune | ml | Fine-tune an open LLM cheaply with LoRA/QLoRA |
| ml-model-eval | ml | Evaluate a trained model like an adult instead of quoting a single accuracy number |
| neural-net-from-scratch | ml | Write your own PyTorch training loop from bare metal — Dataset/DataLoader, forward/backward, mixed-precision (AMP), gradient accumulation, L |
| tabular-foundation-model | ml | Predict on small tabular datasets with TabPFN — a pretrained transformer that does in-context tabular classification/regression in ONE forwa |
| mobile-app-scaffold | mobile | Verb-first: scaffold a real React Native app with Expo, then build, submit, update, and push-notify it via EAS — the only path in this libra |
| batch-api-offloader | model-routing | Cut LLM spend in half on non-realtime work by moving it to the Anthropic Message Batches API or OpenAI Batch API for a guaranteed 50% discou |
| best-model-per-step-pipeline | model-routing | Assign each STEP of a multi-step task to the model+vendor best at that step (deep reasoning on one, coding on another, vision on another, ch |
| cache-aware-context-layout | model-routing | Audit and restructure LLM prompts so the provider's prompt cache actually hits — turning 7% hit rates into 70%+ |
| cross-provider-gateway | model-routing | Put ONE OpenAI-compatible endpoint in front of Anthropic, OpenAI, Google/Gemini, Mistral, Groq, and open-weight models so a single call site |
| cross-vendor-llm-judge | model-routing | Grade, verify, or debate one model's output using a judge from a DIFFERENT company — independent LLM-as-a-judge and voting panels that dodge |
| llm-cost-estimator | model-routing | Price an LLM call in USD BEFORE you run it |
| mixture-of-models-ensemble | model-routing | Fan one prompt to several models from different vendors in parallel, then have an aggregator model synthesize their drafts into one better a |
| model-cascade-escalation | model-routing | Run a cheap/small model first and escalate to a stronger (often different-vendor) model ONLY when a gate — self-reported confidence, an LLM |
| model-routing-eval-benchmark | model-routing | Benchmark models ACROSS vendors on YOUR OWN data to prove which model to route each task type to — then turn the results into a routing tabl |
| model-triage-router | model-routing | Route each request cheap-first inside ONE vendor's tier ladder (Anthropic Haiku -> Sonnet -> Opus, or OpenAI mini -> full) using a difficult |
| output-token-diet | model-routing | Cut OUTPUT tokens 40-70% — the side you're billed 4-5x more for — without losing information, by combining chain-of-draft reasoning, structu |
| provider-failover-reliability | model-routing | Make LLM calls survive rate-limits and provider outages by wiring automatic cross-vendor failover, retries with backoff, cooldowns, and cost |
| semantic-response-cache | model-routing | Put an embedding-similarity (semantic) cache in front of an LLM or RAG app so near-duplicate questions reuse a stored answer and skip infere |
| deep-research | product | Multi-source deep research using firecrawl and exa MCPs |
| documentation-and-adrs | product | Records decisions and documentation |
| idea-refine | product | Refines ideas iteratively |
| market-research | product | Conduct market research, competitive analysis, investor due diligence, and industry intelligence with source attribution and decision-orient |
| product-capability | product | Translate PRD intent, roadmap asks, or product discussions into an implementation-ready capability plan that exposes constraints, invariants |
| product-lens | product | Use this skill to validate the "why" before building, run product diagnostics, and pressure-test product direction before the request become |
| shipping-and-launch | product | Prepares production launches |
| agentic-rag-pipeline | rag | Build an agentic retrieval loop instead of one fixed top-k fetch — decompose the query, route sub-questions to the right source, grade every |
| graphrag-builder | rag | Build and query a knowledge-graph RAG system so you can answer multi-hop and global-summary questions that plain vector RAG cannot ("what ar |
| hybrid-search-reranking | rag | Build two-stage retrieval that fixes both recall and precision: fuse BM25/sparse lexical search with dense ANN vectors using Reciprocal Rank |
| lancedb-multimodal-store | rag | Build an embedded LanceDB/Lance multimodal store that keeps vectors, raw media bytes (images, audio, video frames, PDFs) and metadata togeth |
| llm-rag-eval-harness | rag | Build a regression-proof eval suite for a RAG or LLM app — a versioned golden dataset, the right retrieval + generation metrics (context pre |
| long-doc-chunking | rag | Split any long document, PDF, transcript, or source-code file into clean, structure-preserving chunks using Chonkie — pick token / recursive |
| rag-chunking-contextual | rag | Choose and implement the right RAG chunking + embedding strategy — fixed-token, recursive, semantic, hierarchical/parent-child, and late chu |
| retrieval-as-context | rag | Turn a pile of retrieved chunks into clean, ordered, citation-ready LLM context |
| vector-store-setup | rag | Pick, provision, and tune the vector store under a RAG app — pgvector, Qdrant, Chroma, or LanceDB |
| visual-document-rag | rag | Retrieve over PDF/deck/scan PAGES AS IMAGES using ColPali-family late-interaction multimodal models (ColQwen2.5, ColPali, ColSmol) — no OCR |
| brand-kontext-studio | recipes | Recreate FLUX.1 Kontext / Nano-Banana style in-context brand image editing as a named combo |
| computer-use-qa-runner | recipes | Recreate a trycua/cua- and Microsoft-Fara-style agentic browser-and-computer-use QA runner as a COMBO that chains existing library skills: a |
| deepdish-research-desk | recipes | Recreate a DeerFlow / OpenAI Deep Research long-horizon research desk as a COMBO of proven SEBSKILLS |
| insight-to-deck-autopilot | recipes | Recreate an agency's core money-maker — the research-to-branded-pitch-deck pipeline that tools like Gamma, Tome and Decktopus promise — as a |
| kinetic-type-promo | recipes | Recreate After-Effects-style kinetic typography and motion-graphics promos entirely web-native (CSS + WebGL, no AE) as a named combo |
| living-dashboard | recipes | Recreate a Hex / Observable-style self-updating analytics app as a COMBO of existing SEBSKILLS — pull live public data, transform it in-proc |
| product-hero-3d | recipes | Recreate a Hunyuan3D-2 / TRELLIS style image-to-3D asset pipeline as a named combo: turn one clean product photo into a textured 3D mesh and |
| reel-foundry | recipes | Recreate a Wan2.2 / FramePack-style automated ad-reel factory as a named combo — take a prompt list or a pile of supplied footage and turn i |
| subagent-swarm | recipes | Recreate a portable agent-orchestration harness — the kind sold as a marketplace product (wshobson's agent marketplace, the openai-agents "h |
| synthetic-audience-lab | recipes | Recreate a silicon-sampling / synthetic-persona message-testing lab (the "ask an AI audience before you spend" capability behind tools like |
| temporal-memory-spine | recipes | Recreate a persistent, self-evolving agent-memory backbone — the Graphiti / OpenViking shape — as a COMBO of proven SEBSKILLS |
| voiceover-dub-booth | recipes | Recreate an ElevenLabs / Chatterbox-style dubbing booth locally as a named combo — clone or preset-narrate a script into a voiceover, align |
| crm-pipeline-automation | sales-crm | Read and write CRM records across HubSpot, Salesforce, and Pipedrive from the terminal — paginate contacts/deals, dedup by email/domain, enr |
| artifact-signing-slsa-provenance | security | Prove build integrity, not just scan for CVEs |
| cloud-security-posture-cspm | security | Audit a LIVE cloud account (AWS, Azure, GCP, Kubernetes) for misconfigurations against CIS, NIST, PCI-DSS, SOC2 and friends using Prowler an |
| container-iac-hardening | security | Scan container images, Dockerfiles, Kubernetes manifests and Terraform for CVEs and misconfigurations, then fix them |
| dast-web-scan-zap-nuclei | security | Dynamically scan a RUNNING web app or API for live vulnerabilities using OWASP ZAP (baseline / full / API scan) and ProjectDiscovery Nuclei |
| llm-red-team | security | Red-team an LLM app or model on YOUR OWN authorised targets |
| pii-redaction-presidio | security | Detect, redact and anonymize PII/PHI in text at scale with Microsoft Presidio |
| policy-as-code-opa-kyverno | security | Author, test, and enforce policy-as-code with OPA/Rego, Conftest, and Kyverno |
| runtime-security-falco-ebpf | security | Deploy eBPF-based RUNTIME threat detection on Linux/Kubernetes hosts you are authorised to monitor |
| sast-semgrep-opengrep | security | Run and author static-analysis (SAST) rules to catch injection, auth, path-traversal and secret bugs in YOUR OWN code with Semgrep or the Op |
| secrets-hygiene-and-remediation | security | Hunt and kill leaked credentials |
| supply-chain-sca-audit | security | Audit a repo's dependency supply chain end-to-end |
| WLV | strategy | Write Like Vallance — produce writing in the voice of Charles Vallance (chairman and founding partner of VCCP): erudite, witty, metaphor-led |
| advertising-strategy | strategy | Build an advertising / communications strategy from a client brief |
| advertising-strategy-copy | strategy | Write the *prose* of an advertising / communications strategy: written strategy paragraphs, single-minded propositions, manifestos, strategi |
| attention-planning-metrics | strategy | Plan and measure media with attention metrics — Adelaide AU, Lumen APM/aCPM, Amplified Intelligence active/passive seconds, TVision eyes-on- |
| audience-insight | strategy | Excavate a usable human insight about an audience — the "unsaid truth" that a brand can credibly act on |
| audience-segmentation | strategy | Build, name, profile, and *use* audience segmentations — behavioural, attitudinal, need-state, value-based, and occasion-based |
| behavioural-science-comms | strategy | Apply behavioural science to advertising and comms — diagnose the target behaviour with COM-B, design the intervention with the BIT EAST fra |
| brand-audit | strategy | Audit an existing brand's current comms, positioning and equity: distinctive brand assets, share of voice, share of search, share-of-categor |
| brand-health-tracker-design | strategy | Design an ONGOING brand health tracker, not a one-off audit: pick the metric spine (funnel + equity pillars), set wave cadence and base size |
| category-entry-points-mental-availability | strategy | Map a brand for growth the Ehrenberg-Bass way: elicit Category Entry Points (CEPs) with the 7 W's, score mental availability (mental market |
| competitive-comms-audit | strategy | Audit competitor advertising and communications across paid, owned, earned and shared — to map who is saying what, in what codes, at what we |
| creative-pretesting-framework | strategy | Design a real-world creative pretest (System1 Test Your Ad, Kantar LINK+, Neurons Predict AI) and interpret the scores into a hard go/refine |
| cultural-semiotics | strategy | Decode cultural codes in a category — Residual (the codes fading), Dominant (the codes the category currently runs on), Emergent (the codes |
| data-analyst | strategy | Proper data analyst workflow — exploratory data analysis (EDA), hypothesis testing, segmentation, cohort analysis, time-series decomposition |
| data-cut-headline-stats | strategy | Cut and interrogate raw data (CSV, XLSX, brand tracker exports, media plan returns, campaign performance, sales data, social listening, sear |
| deck-flow-structure | strategy | Plan the *flow* of a deck — the narrative architecture and the order of information — before any slide gets designed or filled with content |
| developed-research | strategy | Build long-form developed research — immersive briefs, category POVs, sector reviews, audience deep dives, "state of X" reports, foresight p |
| effectiveness-case | strategy | Write an effectiveness case — an IPA Effectiveness Awards-style write-up that argues, with evidence, that a piece of advertising made a meas |
| geo-answer-engine-optimization | strategy | Optimise a brand, page or site to be RETRIEVED and CITED by AI answer engines (ChatGPT, Perplexity, Google AI Overviews, Claude, Gemini, Cop |
| influencer-creator-strategy | strategy | Source, fraud-screen, cost and brief creators for a paid influencer campaign, then benchmark it with EMV and lock disclosure compliance |
| media-strategy | strategy | Build a media / communications-channel strategy: audience-first channel selection, role of each channel against the funnel, reach vs frequen |
| persona-population-builder | strategy | Build a large, statistically-grounded synthetic persona population by scaffolding on PersonaHub (proj-persona/PersonaHub, 200K preview / 1B |
| qualitative-research | strategy | Run the qualitative research lifecycle — design, fieldwork prep, analysis, synthesis |
| raw-data-research | strategy | Write and execute scripts to parse, clean, normalise and triangulate large volumes of raw data — messy CSVs, multi-tab XLSX exports, JSON du |
| retail-media-network-strategy | strategy | Build a retail media network (RMN) plan: split budget across Amazon Ads, Walmart Connect, Kroger, Instacart and others by marginal increment |
| share-of-search | strategy | Compute, interpret, and present share of search (SoS) as a leading indicator of brand health and a competitive lens — the Les Binet / James |
| social-listening-orchestration | strategy | Run a full social-listening study end to end over Brand24 or Brandwatch — not just a raw connector pull |
| strategy-analyst | strategy | Acts as a strategic analyst across media and advertising — the hybrid role that takes numbers (brand tracker, MMM, search, social listening |
| synthetic-audience-message-testing | strategy | Pre-flight ad copy, taglines, value props, or full creative against a simulated target audience BEFORE spend, and return a decision-ready re |
| synthetic-focus-group | strategy | Run a synthetic focus group, brainstorm or concept-reaction session with Microsoft TinyTroupe LLM personas for fast, cheap, directional reac |
| trend-foresight | strategy | Identify, weight, and act on trends — separating fads, micro- shifts, macro-shifts, and structural changes — and write a foresight POV with |
| animated-counter | ui-effects | Number that counts up (or down) to a target value when it scrolls into view |
| aurora-gradient | ui-effects | Animated multi-color gradient blob background (React, pure CSS) — soft blurred "aurora" blobs drift across a container |
| bento-grid | ui-effects | Responsive bento-box grid layout for React — variable column/row spans per card, with 3D hover tilt + lift that tracks the cursor |
| css-scroll-driven-animations | ui-effects | Build scroll-linked and view-triggered animations with native CSS — zero JavaScript, zero IntersectionObserver — using animation-timeline: s |
| floating-label-input | ui-effects | Material/Stripe-style floating label input for React — label sits inside the field at rest, floats up and shrinks when focused or filled, wi |
| framer-level-interactions | ui-effects | Build Framer-grade interactive section components for marketing pages, product sites, portfolios, and dashboards |
| image-shatter | ui-effects | Build a React/Next.js component that shatters an image into a grid of tiles on hover, with each tile flying outward/rotating with spring phy |
| infinite-marquee | ui-effects | Seamless infinite horizontal marquee / logo ticker in React using pure CSS animation — duplicates children, scrolls forever, pauses on hover |
| interactive-distortion | ui-effects | Build a WebGL2 interactive mouse-driven pixel distortion effect for images and videos in React/Next.js |
| liquid-glass-button | ui-effects | Build an Apple-style liquid glass back button (or generic glass button) in React/Next.js using pure CSS — no WebGL, no canvas |
| liquid-image | ui-effects | Build a WebGL liquid-water hover effect for images in React/Next.js — ripples follow the cursor, and a grayscale-to-colour reveal mask follo |
| magnetic-button | ui-effects | React button that attracts toward the cursor when it's within a radius, with spring-damped follow and elastic snap-back on exit |
| magnetic-cursor | ui-effects | Custom cursor dot that follows the mouse with spring lag, scales up over interactive elements, shrinks on mousedown, and uses mix-blend-mode |
| rive-lottie-web-animation | ui-effects | Embed a designer-authored Rive (.riv) state machine or dotLottie (.lottie) animation at runtime on the web and DRIVE it from code — fire tri |
| rubiks-image-cube | ui-effects | Build an interactive 3D Rubik's cube component in React/Next.js using CSS 3D transforms and framer-motion |
| scroll-reveal-section | ui-effects | React wrapper that fades and slides its children into view with stagger as the section enters the viewport |
| skeleton-and-optimistic-ui | ui-effects | Build perceived-speed UI: shimmer/skeleton placeholders while data loads, React Suspense streaming with the use() hook, and instant optimist |
| spectra-noise | ui-effects | Build a WebGL shader-based animated noise background component for React/Next.js |
| spectral-distortion | ui-effects | Compose a red-themed spectra-noise WebGL shader background with an interactive-distortion image overlay so that the spectra's animated field |
| text-scramble | ui-effects | Text that scrambles random glyphs and then "decrypts" into its final string when triggered (viewport/hover/mount) |
| theme-toggle | ui-effects | Animated sun/moon theme toggle button for React — smoothly morphs between a sunburst and a crescent moon, persists the choice to localStorag |
| view-transitions-morphing | ui-effects | Use the native View Transitions API to morph between UI states and pages with zero animation JS — crossfade the whole viewport, or FLIP-morp |
| adversarial-argument-review | verification | Steelman an argument then attack it — reconstruct its strongest form, surface hidden assumptions, name logical fallacies, build the stronges |
| ai-provenance-deepfake-check | verification | Verify whether an image, video, or audio file is AI-generated, edited, or authentic by reading C2PA / Content Credentials manifests, checkin |
| citation-integrity-check | verification | Verify every reference in a manuscript, report, or LLM output actually EXISTS and says what it is cited for |
| claim-verifier | verification | Fact-check prose by decomposing it into atomic, decontextualized, checkable claims, retrieving evidence per claim (web/corpus), and returnin |
| eval-dataset-curation | verification | Build, version and defend a golden eval set BEFORE trusting any eval number — pin an immutable frozen slice with a content hash, run a two-t |
| experiment-validity-audit | verification | Gate an A/B test result before anyone calls a winner — run the four integrity checks that catch most false positives: Sample Ratio Mismatch |
| inter-annotator-agreement | verification | Measure how much your human labellers (or LLM judges) actually agree, using Cohen's kappa, Fleiss' kappa, and Krippendorff's alpha — then ro |
| llm-judge-bias-audit | verification | Audit and debias an LLM-as-judge before you trust its scores |
| online-eval-drift-monitor | verification | Stand up online evaluation on live LLM traffic: sample a slice of production traces, score each with an LLM-judge or code scorer, compare th |
| research-methodology-review | verification | Appraise the METHODOLOGY behind a study, survey or research claim before you trust or cite it — match it to the right reporting guideline (C |
| self-consistency-check | verification | Catch likely LLM hallucinations with NO knowledge base — re-sample the same answer N times at high temperature and flag any fact that change |
| source-credibility-audit | verification | Grade the sources behind a claim, deck, or report — reliability track record, independence and conflicts of interest, primary-vs-secondary |
| stat-check-review | verification | Recompute and stress-test the statistics in a report, deck or paper so a wrong number never ships — statcheck-style t/F/χ²/df/p consistency |
| realtime-voice-agent | voice-agents | Build a low-latency speech-to-speech conversational voice agent with barge-in, natural turn-taking, and mid-call tool/function calls |

<!-- END:MANIFEST -->
