---
name: agent-code-sandbox
category: building-agents
description: >-
  Give a code-writing agent a secure, ephemeral runtime so LLM-generated code never
  executes on your host. Use when an agent must run untrusted Python/Bash, a data-analysis
  or code-interpreter loop, run tests, or install packages, and you need isolation, hard
  timeouts, and guaranteed teardown. Covers E2B, Modal, and Daytona sandboxes with real
  create/exec/files/kill APIs, API-key setup, and a drop-in run-and-capture helper.
when_to_use:
  - Your agent generates code and you refuse to run it directly on the host or CI runner
  - Building a code-interpreter / data-analysis loop (write code, execute, read result, retry)
  - Running untrusted or user-supplied code, package installs, or shell commands in isolation
  - You need hard wall-clock timeouts and guaranteed VM teardown around each execution
  - Executing agent-written unit tests or reproductions in a throwaway environment
  - Choosing between E2B, Modal, and Daytona for agent runtime isolation
when_not_to_use:
  - Designing the agent's tools/schema rather than its runtime — use mcp-builder
  - Just calling the Claude API with tool use and no code execution — use claude-api
  - Deploying a long-lived hosted service (not ephemeral per-task) — use use-railway
  - Only need a local shell for trusted first-party code — run it directly, no sandbox
keywords:
  - sandbox
  - e2b
  - modal
  - daytona
  - code-interpreter
  - untrusted-code
  - ephemeral
  - isolation
  - agent-runtime
  - code-execution
  - timeout
  - data-analysis
  - firecracker
  - security
similar_to:
  - mcp-builder
  - claude-api
  - permanent-agent
inputs_needed: >-
  A provider API key (E2B_API_KEY, Modal token, or DAYTONA_API_KEY); the code/command string
  to run; a per-task timeout budget; optional files or env vars to seed into the sandbox.
produces: >-
  Captured stdout/stderr/results/error from isolated execution, plus any files the sandbox
  wrote, with the VM torn down afterward. Includes scripts/run_in_sandbox.py as a drop-in.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Agent Code Sandbox

Code-writing agents must not `exec()` model output on the machine that holds your keys,
repo, and prod credentials. Route every LLM-generated snippet through an **ephemeral,
isolated micro-VM**: create it, run the code with a hard timeout, capture the result,
**always kill it**. This skill grounds three battle-tested providers (E2B, Modal, Daytona)
with real, current APIs so the loop actually works.

## When to use

Use this the moment an agent's plan includes "run this code / test / install". Symptoms
you need it: you're tempted to `subprocess.run(model_output)`, you're piping generated
Python into a bare interpreter, or a data-analysis agent needs matplotlib/pandas without
polluting the host. If the code is trusted first-party code you wrote, you don't need a
sandbox — just run it.

## Prerequisites

- **Python 3.9+** (this host's `python3`). SDKs also have JS/TS equivalents.
- **A provider account + API key.** All three have free tiers. Pick ONE to start:
  - **E2B** — `pip install e2b-code-interpreter`; needs `E2B_API_KEY` (from e2b.dev/dashboard).
    Best default for a code-interpreter loop: `run_code()` returns structured stdout,
    rich results (charts/dataframes), and errors in one call.
  - **Modal** — `pip install modal` then `modal token new` (browser auth). Best when you
    want a custom image (pinned deps, GPU) and to reuse an `App` across runs.
  - **Daytona** — `pip install daytona`; needs `DAYTONA_API_KEY`. Simple `process.code_run`.
- **Never** bake keys into code. Read from env; validate presence at startup and fail fast.
- Cost/limits are real: sandboxes bill by wall-clock. Always set a timeout and kill.

## Provider decision

| Need | Pick |
|---|---|
| Fast code-interpreter loop, structured results, charts | **E2B** (`run_code`) |
| Custom/pinned image, GPU, reuse a warm App, filesystem streaming | **Modal** |
| Dead-simple `create → code_run → result`, self-host option | **Daytona** |

## Recipe 1 — E2B (recommended default)

```python
import os
from e2b_code_interpreter import Sandbox

assert os.environ.get("E2B_API_KEY"), "set E2B_API_KEY"

# timeout = wall-clock lifetime of the whole VM (default ~5 min; max 1h Base / 24h Pro).
sbx = Sandbox.create(timeout=60)
try:
    sbx.files.write("/home/user/data.csv", "a,b\n1,2\n3,4\n")   # seed input
    execution = sbx.run_code(
        "import pandas as pd; df = pd.read_csv('/home/user/data.csv'); print(df.sum().to_dict())",
        request_timeout=60,        # guards this single call from hanging
    )
    if execution.error:
        print("FAILED:", execution.error.name, execution.error.value)
    else:
        print("".join(execution.logs.stdout))     # stdout lines
        print(execution.results)                  # rich results: charts, dfs, images
    out = sbx.files.read("/home/user/data.csv")    # pull files back out
finally:
    sbx.kill()                                     # ALWAYS reclaim the VM
```

Also useful: `sbx.commands.run("pip install seaborn")` for shell/installs;
`sbx.set_timeout(120)` to extend a live sandbox; `Sandbox.connect(sandbox_id)` to
reattach to a running one across process boundaries.

## Recipe 2 — Modal (custom image / reuse an App)

```python
import modal

app = modal.App.lookup("agent-sandbox", create_if_missing=True)
image = modal.Image.debian_slim().pip_install("pandas", "matplotlib")

sb = modal.Sandbox.create(app=app, image=image, timeout=60)  # timeout in seconds
try:
    p = sb.exec("python", "-c", "print(sum(range(100)))", timeout=30)
    print(p.stdout.read())         # blocking read; iterate `for line in p.stdout` to stream
    print("exit:", p.wait())       # return code
finally:
    sb.terminate()                 # kill the VM
```

Pass untrusted code as an argument (`"-c", code`) or write it to a file first — never
string-format it into a shell command (injection). Modal isolates each Sandbox in its own
gVisor-backed container.

## Recipe 3 — Daytona (minimal)

```python
from daytona import Daytona, DaytonaConfig

daytona = Daytona(DaytonaConfig(api_key=__import__("os").environ["DAYTONA_API_KEY"]))
sandbox = daytona.create()
try:
    resp = sandbox.process.code_run('print("hello from sandbox")')
    print(resp.result)
finally:
    sandbox.delete()
```

## Recipe 4 — Drop-in helper + agent loop

`scripts/run_in_sandbox.py` wraps E2B with a hard timeout, error capture (the sandboxed
exception never propagates into your process), and guaranteed `kill()` in a `finally`.

```bash
export E2B_API_KEY=e2b_...
echo "print(2**10)" | python3 scripts/run_in_sandbox.py --timeout 30
python3 scripts/run_in_sandbox.py --file model_output.py --timeout 60   # -> JSON result
```

Wire it into an agent's write→run→observe→retry loop: the agent proposes code, you shell
out to the helper, feed the returned JSON (`ok`, `stdout`, `error`) back as an observation,
and let the model fix-and-retry. Because it returns structured JSON and swallows crashes,
one bad snippet can't take down the orchestrator.

## Verify

- `python3 -m py_compile scripts/run_in_sandbox.py` — helper is syntactically valid.
- `echo "" | python3 scripts/run_in_sandbox.py` → `{"ok": false, "error": "no code supplied"}`
  (proves the guardrails run without any SDK/key installed).
- With a key set: `echo "print(6*7)" | python3 scripts/run_in_sandbox.py` → `stdout: "42\n"`.
- Confirm teardown: after a run, the provider dashboard shows no lingering running sandbox.

## Pitfalls

- **No timeout = runaway bill.** Every provider bills wall-clock. Always pass a timeout AND
  kill in a `finally`. A crashed orchestrator must not orphan a live VM.
- **Sandbox ≠ your filesystem.** Code runs on a remote VM. `files.write`/`files.read`
  (E2B) or image mounts (Modal) move data in/out — a local path won't exist inside.
- **Don't string-format untrusted code into a shell.** Pass it as an argument or write it
  to a file; formatting into `bash -c "{code}"` is a command-injection hole.
- **Isolation is not a license to leak.** Do not inject prod secrets/tokens into the
  sandbox env unless the task truly needs them — sandboxed code can exfiltrate anything it
  can read. Seed only the minimum.
- **Default timeouts vary and drift** (E2B ~5 min, providers change tiers) — set it
  explicitly rather than relying on the default; verify current limits on the dashboard.
- **Cold starts add latency.** For a tight loop, reuse a warm sandbox (`Sandbox.connect`,
  Modal warm `App`) instead of creating one per snippet, but still enforce a max lifetime.
- **These are execution runtimes, not a network firewall.** If the task must not reach the
  internet, disable egress via provider config — isolation from your host is the default,
  network lockdown is opt-in.
