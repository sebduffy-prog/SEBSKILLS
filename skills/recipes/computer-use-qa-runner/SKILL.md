---
name: computer-use-qa-runner
category: recipes
description: >-
  Recreate a trycua/cua- and Microsoft-Fara-style agentic browser-and-computer-use QA runner as a
  COMBO that chains existing library skills: a computer-use agent drives a real UI by screenshot →
  plan → click/type, a safety gate halts destructive or off-policy actions before they fire, and a
  trajectory evaluator scores whether the run actually passed. Green for web QA (Playwright); amber
  for general-OS QA (needs a cua sandbox VM). Reach for this to auto-QA a web app or desktop flow,
  run agentic regression suites, or benchmark a computer-use policy over a task set.
when_to_use:
  - You want an agent to QA a web app or desktop flow by operating the real UI (screenshot → click/type), not by calling an API
  - You need a repeatable agentic regression suite that drives the product like a user and reports pass/fail per task
  - You want to benchmark or compare a computer-use policy (Claude driver vs Fara-7B) over a fixed task set
  - You need destructive or off-policy actions (submit, delete, pay, navigate off-domain) gated before they fire
  - You want trajectory-level scoring (was the whole click/type sequence correct) rather than a single end-state assert
  - You are reproducing the trycua/cua or Fara "agentic computer-use" demo locally and want an honest, staged build
when_not_to_use:
  - You only need to drive a browser and assert on it once — use agentic-web-automation or connect-playwright-mcp alone
  - You only need the sandboxed driver loop with no gate and no eval — use computer-use-agent by itself
  - You only need a safety tripwire on an existing agent — use swarm-guardrails alone
  - You only need to score or trace an agent that already runs — use agent-evals-and-tracing alone
  - The app has a clean API/MCP surface — call it directly; pixel-driving QA is slower and flakier
keywords:
  - computer-use
  - agentic-qa
  - trycua
  - cua
  - fara
  - fara-7b
  - browser-agent
  - playwright
  - trajectory-eval
  - regression-suite
  - screenshot-plan-act
  - safety-gate
  - guardrails
  - vla
  - web-automation
  - benchmark
similar_to:
  - computer-use-agent
  - connect-playwright-mcp
  - agentic-web-automation
  - swarm-guardrails
  - agent-evals-and-tracing
inputs_needed: >-
  A target under test (a URL for web QA, or a cua sandbox VM image/endpoint for OS QA); a task set
  (list of goals + a pass condition per task); a driver model key (Claude/GPT) or a local Fara-7B
  checkpoint; a policy config for the gate (allowed domains, blocked destructive verbs).
produces: >-
  A per-task pass/fail report with trajectory scores, screenshots at each step, a gate audit log of
  blocked/allowed actions, and OpenTelemetry traces of every run — the reproduced cua/Fara QA-runner
  output.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Computer-Use QA Runner

## What it recreates

A local stand-in for **trycua/cua** and **Microsoft Fara** — the "agentic browser & computer-use QA"
pattern where a vision-language agent operates a real UI (screenshot → plan → click/type/scroll →
verify), gated for safety, and scored on whether it actually completed the task. cua ships a
sandboxed `ComputerAgent` loop over disposable VMs; Fara-7B is the local no-API VLA policy. This
recipe reassembles that capability out of skills the library already has, and wires a safety gate and
a trajectory eval around it so runs are auditable and scored — not just "it clicked something."

## Feasibility

**Rating: amber.**

- **Green for web QA.** Driving a browser end-to-end is fully reproducible locally through Playwright
  (`connect-playwright-mcp` / `agentic-web-automation`). No external GPU, no VM. This half is honest
  green.
- **Amber for general-OS / desktop QA.** Operating a real desktop by pixels (arbitrary native apps,
  file dialogs, OS chrome) needs a cua **sandbox VM** and a computer-use driver — that is the amber
  step in `computer-use-agent`. It depends on an external sandbox (trycua cloud or a local
  Lume/Docker VM) and a driver API key, OR a local Fara-7B checkpoint plus a GPU. If you have neither,
  stay on the green web path and do not claim desktop coverage.
- The **gate** and the **eval** steps are green (pure local Python).

Do not oversell this as "full cua parity" — you are reproducing the loop and the QA harness, and
wrapping the one genuinely-external piece (the OS sandbox / VLA weights) rather than shipping it.

## The combo

An ordered chain. Each step is an existing library skill.

1. **`computer-use-agent`** — stand up the driver loop: screenshot → plan → click/type/scroll →
   verify. For web this can delegate to Playwright; for OS this runs inside a cua sandbox VM with a
   Claude/GPT driver or a local Fara-7B policy. This is the amber step for the OS path.
2. **`connect-playwright-mcp`** — the green web driver. Exposes the browser as MCP tools (navigate,
   click, fill, screenshot) so the agent drives a real Chromium page deterministically, no VM needed.
3. **`agentic-web-automation`** — the higher-level web QA harness: turn each task goal into a driven
   flow with selectors, waits, and an end assertion. Use this instead of step 1's OS path when the
   target is a web app.
4. **`swarm-guardrails`** — the safety gate. A tripwire that runs *before* each action fires: block
   off-domain navigation, destructive verbs (delete/pay/submit-when-not-allowed), and PII leakage;
   HALT the run instead of letting the model take the action. Produces the gate audit log.
5. **`agent-evals-and-tracing`** — the scorer. Grade each run at the **trajectory** level (was the
   click/type sequence correct), measure reliability with pass^k over repeated runs, and emit
   OpenTelemetry traces so every step is observable. Produces the pass/fail report.

## Prerequisites

- Python 3.10+ and Node (for Playwright/Chromium) on the green path.
- **Web path (green):** `pip`/`npx` for the Playwright MCP server; a driver model key (Claude/GPT).
- **OS path (amber):** a cua sandbox — trycua cloud endpoint OR local Lume/Docker VM image — plus a
  computer-use driver key, OR a local **Fara-7B** checkpoint and a GPU (≈16GB VRAM) if you want the
  no-API policy.
- A task set file: for each task a `goal`, a `start` (URL or app), and a `pass` condition (assertion
  or LLM-judge rubric).
- A gate policy: allowed domains, blocked destructive verbs, PII rules.

## Run it

1. **Pick the path.** Web target → green (steps 2–3). Desktop/native target → amber (step 1 with a
   cua sandbox or Fara-7B). If unsure or you lack a sandbox, run green and label desktop coverage as
   not-attempted.
2. **Stand up the driver.** Green: invoke `connect-playwright-mcp` to expose the browser tools, then
   `agentic-web-automation` to author the driven flow per task. Amber: invoke `computer-use-agent` to
   boot the sandbox VM and start the `ComputerAgent` (or Fara) screenshot→act loop.
3. **Insert the gate.** Wrap every action with `swarm-guardrails`: configure the tripwire from your
   policy (domain allowlist, blocked verbs, PII checks). It runs pre-action and HALTs on violation,
   writing an audit line. This is the "safe" in the cua safe-loop.
4. **Run the task set.** Execute each task N times (N≥3 for pass^k). Capture a screenshot at every
   step and the full action trajectory.
5. **Score it.** Feed trajectories to `agent-evals-and-tracing`: choose deterministic grading
   (final-state / exact-match) where the pass condition is crisp, LLM-as-judge where it is fuzzy.
   Report pass^k, not just pass@1. Emit OTel traces to Langfuse/Phoenix.
6. **Assemble the report.** Per task: pass/fail, trajectory score, step screenshots, gate log,
   trace link.

## Verify

- **Green path is real, not mocked:** confirm the browser actually navigated and interacted — check
  the Playwright screenshots and network log, not just an agent transcript.
- **Gate fires:** add a deliberately off-policy task (navigate off-domain, or a blocked verb). The
  run must HALT with a gate audit entry — a gate that never blocks is not wired.
- **Eval discriminates:** include one task the app genuinely fails. The report must mark it fail. If
  everything passes, your pass condition is too loose.
- **Reliability, not luck:** confirm pass^k < pass@1 on any flaky task — if they are equal on a known-
  flaky flow, k is too small or you ran once.
- **Amber honesty:** if you ran only the web path, the report must say desktop/OS QA was not
  attempted — never imply full cua parity.

## Pitfalls

- **Claiming desktop coverage you didn't run.** The OS path needs the sandbox VM or Fara weights.
  Without them you have web QA only — say so.
- **Skipping the gate to "just get a run."** An ungated computer-use agent can submit, pay, or delete
  for real against a live target. The gate is not optional; it is the difference between QA and an
  incident.
- **pass@1 theatre.** A single green run proves nothing for a pixel-driving agent — they are flaky by
  nature. Always repeat and report pass^k.
- **Grading the transcript, not the trajectory.** The model can narrate success while the UI never
  changed. Score screenshots/end-state, not the agent's own claims.
- **Pointing the runner at production.** Run against staging or a disposable environment; even gated,
  pixel automation on prod is a bad idea.
- **Treating this as one-click cua.** It is a staged reassembly — five skills chained. Build the green
  web path first, prove the gate and eval, then attempt the amber OS path only if you have the
  sandbox.
