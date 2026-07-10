---
name: llm-red-team
category: security
description: >
  Red-team an LLM app or model on YOUR OWN authorised targets. Run garak probes
  (jailbreaks, prompt-injection, encoding smuggling, data leakage, toxicity) plus
  promptfoo app-specific attacks mapped to the OWASP LLM Top-10, produce a triaged
  HTML/JSON report, and wire a CI gate that fails the build on new high-severity
  findings so regressions never merge. Use for chatbots, RAG, agents, and API
  endpoints. Trigger on "red team the LLM", "jailbreak testing", "prompt-injection
  scan", "garak", "promptfoo redteam", "OWASP LLM Top 10", "LLM security gate".
when_to_use:
  - You own or are explicitly authorised to test an LLM app, model, or API endpoint
  - You want automated jailbreak / prompt-injection / data-leakage coverage before shipping
  - You need findings mapped to the OWASP LLM Top-10 for a security sign-off
  - You want a CI gate that blocks PRs introducing new high-severity LLM vulnerabilities
  - You need a repeatable, versioned red-team baseline to detect regressions over time
when_not_to_use:
  - Attacking a third-party model/app you do not own or have written permission to test — stop; get authorisation first
  - You need SAST on the surrounding application code — use sast-semgrep-opengrep
  - You need to scrub secrets/PII from logs or transcripts — use pii-redaction-presidio or secrets-hygiene-and-remediation
  - You need dependency/CVE scanning of the ML stack — use supply-chain-sca-audit
keywords: [llm-security, red-team, garak, promptfoo, jailbreak, prompt-injection, owasp-llm-top-10, ci-gate, adversarial, data-leakage, guardrails, model-testing]
similar_to: [secrets-hygiene-and-remediation, sast-semgrep-opengrep, supply-chain-sca-audit, container-iac-hardening, pii-redaction-presidio]
inputs_needed: A target you are authorised to test (OpenAI/HF/Bedrock model id, or a REST endpoint URL + auth), the app's system prompt / purpose, and API keys via env.
produces: garak .report.jsonl + .report.html, promptfoo redteam report (OWASP-mapped), a triaged findings summary, and a CI job that fails on new HIGH/CRITICAL findings.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# LLM Red Team (garak + promptfoo, OWASP LLM Top-10)

Two complementary tools. **garak** = a broad library of pre-built probes that hammer a
*model/endpoint* (jailbreaks, encoding smuggling, toxicity, leakage). **promptfoo redteam**
= *application-aware* attacks generated from YOUR system prompt/purpose, scored and mapped
to the OWASP LLM Top-10. Run garak for breadth, promptfoo for app-specific depth and the
CI gate.

## When to use

Before shipping any LLM feature, and on a schedule/CI thereafter. Use garak to sweep a raw
model or endpoint; use promptfoo when you can describe the app's *purpose* (what it should
and must-not do) so attacks are contextual.

## Authorisation (read first)

Only run against targets you own or have **written** permission to test. These tools send
real adversarial traffic and can trip provider abuse detection. Use a dedicated test key,
a non-production endpoint where possible, and keep the scope/authorisation note in the repo.

## Prerequisites

- **Python 3.10–3.12 for garak.** This Mac's system `python3` is 3.9 — garak needs ≥3.10.
  Create a dedicated venv with a newer Python (`pyenv install 3.12`, or conda), then
  `python -m pip install -U garak`. (garak will not install/run on 3.9.)
- **Node 18+ for promptfoo** — run via `npx promptfoo@latest` (no install needed).
- **API keys via env**, never in files: `export OPENAI_API_KEY=...` (garak grader/target),
  and whatever your target needs. promptfoo's attack-generation also uses a provider key.
- Network egress to the target and provider.

## Recipe 1 — garak breadth sweep

Install into a 3.10+ venv:

```bash
python3.12 -m venv ~/.venvs/garak && source ~/.venvs/garak/bin/activate
python -m pip install -U garak
garak --list_probes          # browse the probe catalogue
```

Run a focused sweep against a hosted model. `--probes` takes families or specific probes;
`--generations` sets attempts per prompt (lower = faster/cheaper); `--report_prefix` names
the output:

```bash
export OPENAI_API_KEY=sk-...
garak --model_type openai --model_name gpt-4o-mini \
      --probes dan,encoding,promptinject,latentinjection,leakreplay \
      --generations 5 \
      --report_prefix myapp_baseline
```

High-signal probe families (start here, expand as needed):

| Family | Tests for | OWASP LLM |
|---|---|---|
| `promptinject`, `latentinjection` | direct & indirect prompt injection | LLM01 |
| `dan`, `grandma` | jailbreak / role-play persona bypass | LLM01 |
| `encoding` | base64/rot13/hex instruction smuggling | LLM01 |
| `leakreplay` | training-data / memorised content leakage | LLM02 |
| `xss`, `ansiescape` | unsafe output (markup/ANSI) → improper handling | LLM05 |
| `malwaregen`, `exploitation` | harmful code generation | LLM05/09 |
| `packagehallucination` | hallucinated (squattable) package names | LLM09 |
| `realtoxicityprompts`, `continuation` | toxicity / unsafe continuations | LLM09 |

> Recent garak also accepts `--target_type`/`--target_name` as aliases for
> `--model_type`/`--model_name`; either works.

**Custom REST endpoint** (your own app): create `rest.json`, then pass `-G`:

```json
{ "rest": { "RestGenerator": {
  "name": "my app",
  "uri": "https://staging.myapp.internal/chat",
  "method": "post",
  "headers": { "Authorization": "Bearer $KEY", "Content-Type": "application/json" },
  "req_template_json_object": { "message": "$INPUT" },
  "response_json": true,
  "response_json_field": "reply"
} } }
```

```bash
KEY=... garak --model_type rest -G rest.json \
      --probes promptinject,encoding --generations 3 --report_prefix myapp_rest
```

Reports land in `$XDG_DATA_HOME/garak/garak_runs/` (macOS: `~/.local/share/garak/garak_runs/`)
as `<prefix>.report.jsonl` (per-attempt results, pass/fail per detector) and
`<prefix>.report.html` (human summary). Regenerate the HTML from JSONL any time:

```bash
python -m garak.analyze.report_digest -r <prefix>.report.jsonl -o <prefix>.report.html
```

## Recipe 2 — promptfoo app-specific red team (OWASP-mapped)

Scaffold a config (headless):

```bash
npx promptfoo@latest redteam init --no-gui
```

Edit `promptfooconfig.yaml`. The `purpose` is what drives contextual attacks — be specific
about the app's job AND its guardrails (what it must refuse). Target your own endpoint:

```yaml
targets:
  - id: https
    label: support-bot
    config:
      url: https://staging.myapp.internal/chat
      method: POST
      headers: { Content-Type: application/json }
      body: { message: '{{prompt}}' }
      transformResponse: json.reply

purpose: >
  A customer-support assistant for AcmeCo. It may answer product/billing questions
  for the authenticated user only. It must never reveal its system prompt, other
  users' data, internal URLs, or discount codes; never run destructive actions.

redteam:
  plugins:
    - owasp:llm           # full OWASP LLM Top-10 pack
  strategies:
    - jailbreak           # iterative jailbreak search
    - jailbreak:composite
    - prompt-injection
  numTests: 5             # cases per plugin — raise for depth
```

To scope to specific risks instead of the whole pack, list individual IDs
(`owasp:llm:01` … `owasp:llm:10`), e.g. injection + leakage only:

```yaml
  plugins: [owasp:llm:01, owasp:llm:02, owasp:llm:07]
```

Generate + run + view:

```bash
npx promptfoo@latest redteam run        # generates adversarial cases and executes them
npx promptfoo@latest redteam report     # opens the OWASP-mapped web report
```

`redteam run` writes results to `redteam.yaml`/the eval store; `report` renders per-plugin
pass rates grouped by OWASP category with the exact attack prompt and model response for
each failure — that reproduction pair is what you hand to engineering.

## Recipe 3 — CI gate that blocks regressions

promptfoo drives the gate (deterministic exit codes, JSON output). Commit
`promptfooconfig.yaml` and a workflow. Fail the build on any failing red-team case:

```yaml
# .github/workflows/llm-redteam.yml
name: llm-red-team
on: [pull_request]
jobs:
  redteam:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - name: Red team (blocks on failures)
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          TARGET_URL: ${{ secrets.STAGING_CHAT_URL }}
        run: |
          npx promptfoo@latest redteam run \
            --output results.json --no-progress-bar
          # promptfoo exits non-zero when tests fail; enforce a floor explicitly too:
          npx promptfoo@latest redteam report --output report.html || true
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: redteam-report, path: report.html }
```

**Baseline vs. regression:** the first run establishes accepted pass rates. To block only
*new* failures (not the whole backlog), keep a committed `redteam.yaml` baseline and diff
pass counts, or gate on a threshold with `--filter-metadata`/`assert` in the config. Keep
`numTests` modest in CI (cost + runtime) and run the deep garak sweep nightly on a schedule,
not per-PR.

## Verify

- `garak --list_probes` prints families ⇒ garak installed on a 3.10+ interpreter.
- After a garak run, `<prefix>.report.jsonl` exists and `<prefix>.report.html` opens with
  per-probe pass/fail counts.
- `npx promptfoo@latest redteam run` completes and `redteam report` groups findings under
  OWASP LLM01–LLM10 with reproducible prompt/response pairs.
- CI: introduce a deliberately weak system prompt (e.g. one that leaks its instructions) and
  confirm the job goes red; fix it and confirm green.

## Pitfalls

- **Python 3.9 will not run garak.** Always use a ≥3.10 venv/conda env; the macOS system
  interpreter is 3.9.
- **Cost & rate limits.** Every probe = many model calls. Start with few `--generations` /
  low `numTests`; a full `owasp:llm` + all-probes run can be thousands of requests.
- **Authorisation & abuse detection.** Adversarial traffic can flag your account or WAF —
  test staging with a dedicated key, and keep permission on record.
- **grader keys.** garak's judgement and promptfoo's attack generation both call an LLM;
  a missing/underpowered grader model produces noisy or empty verdicts.
- **False positives are normal.** Triage every "hit" — some detectors flag safe outputs.
  Confirm the reproduction pair before filing; don't ship the raw report as ground truth.
- **Endpoint shape drift.** If the target's request/response JSON changes, update
  `req_template_json_object`/`response_json_field` (garak) and `body`/`transformResponse`
  (promptfoo) or every case fails for the wrong reason.
- **Don't gate CI on garak's broad sweep** — it's slow/noisy; use promptfoo for the
  deterministic per-PR gate and garak on a nightly schedule.
