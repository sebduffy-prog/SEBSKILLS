---
name: online-eval-drift-monitor
category: verification
description: >-
  Stand up online evaluation on live LLM traffic: sample a slice of production
  traces, score each with an LLM-judge or code scorer, compare the score
  distribution against a golden/baseline set, and alert when it drifts. Trigger
  when tracing already captures logs but nothing is *grading* them — when you
  need continuous quality monitoring, a regression alarm on faithfulness/
  correctness, or a cron that watches for silent model, prompt, or data drift
  in a RAG or agent app. Grounded on Braintrust online scoring + Galileo drift.
when_to_use:
  - You already log/trace production LLM calls but nothing scores them on an ongoing basis
  - You want to sample X% of live traffic and run LLM-judge or code scorers asynchronously
  - You need a drift alarm (PSI / KS / mean shift) when live quality diverges from a golden baseline
  - A model, prompt, retriever, or data-source change may have silently degraded output quality
  - You want a scheduled cron/CI gate that emails/Slacks when eval scores fall out of band
  - Standing up Braintrust online scoring rules or a Galileo-style guardrail on a project
when_not_to_use:
  - Running a one-off offline eval over a fixed dataset before shipping — use test-driven-development or an eval harness
  - Auditing whether an LLM judge is itself biased/miscalibrated — use llm-judge-bias-audit
  - Fact-checking specific claims in a document rather than scoring a traffic stream — use claim-verifier
  - Checking a single answer's internal consistency across samples — use self-consistency-check
  - Only recomputing numeric/statistical claims in a report — use stat-check-review
keywords:
  - online-eval
  - drift-detection
  - production-monitoring
  - llm-as-judge
  - sampling
  - braintrust
  - galileo
  - psi
  - ks-test
  - golden-set
  - scorers
  - guardrails
  - observability
  - regression-alarm
  - continuous-evaluation
similar_to:
  - llm-judge-bias-audit
  - claim-verifier
  - self-consistency-check
  - stat-check-review
  - research-methodology-review
inputs_needed: A source of live traces (Braintrust/Galileo/OpenTelemetry logs, or a JSON export of production inputs+outputs), one or more scorers (autoevals/LLM-judge or a code function returning 0-1), and a golden baseline — either a labelled reference set or a frozen historical score distribution to compare against.
produces: An online scoring config (Braintrust rule or a self-hosted sampling loop) plus a drift report per metric — PSI, KS statistic, mean shift, and a STABLE/WARN/ALERT verdict with a non-zero exit code for CI/alerting.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Online Eval & Drift Monitor

Tracing tells you *what happened*; it does not tell you whether quality is holding. This skill closes that gap: **sample live traffic → score it → compare the distribution to a golden baseline → alert on drift.** Two paths are covered — a managed rule on Braintrust, and a provider-agnostic sampling loop you run yourself (cron/CI) using the bundled `scripts/drift.py`.

## When to use

Use when logs/traces exist but nothing grades them on an ongoing basis, and you want a standing alarm for silent regressions after a model bump, prompt edit, retriever change, or data-source shift. If you only need a pre-ship offline eval, use an eval harness instead.

## Prerequisites

- **A scorer that returns 0-1.** Either `autoevals` (`pip install autoevals` — ships `Faithfulness`, `Factuality`, `AnswerCorrectness`, `LLMClassifier`), a hand-written code scorer, or an LLM-judge. LLM-judge scorers need an `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`.
- **A golden baseline.** Either a labelled reference set (expected outputs) *or* a frozen snapshot of a known-good score distribution to diff against.
- **Managed path only:** a Braintrust account + `BRAINTRUST_API_KEY`, and `pip install braintrust`. Galileo path needs a Galileo project + API key.
- **Self-hosted path:** just Python 3.9 stdlib — `scripts/drift.py` has zero third-party deps.

Never claim drift you did not measure. If a baseline is missing, snapshot the current distribution first and label it "provisional" — do not fabricate reference scores.

## Recipe A — Braintrust online scoring rule (managed)

Braintrust runs scorers **asynchronously after logging**, so it adds no request latency. Steps:

1. **Log production traffic** with the SDK:
   ```python
   import braintrust
   logger = braintrust.init_logger(project="support-bot")
   with logger.start_span(name="answer") as span:
       span.log(input=user_msg, output=reply, metadata={"model": model})
   ```
2. **Publish a scorer** as a Braintrust function (via `braintrust push` or the UI). Code scorer example using autoevals:
   ```python
   from autoevals import Factuality
   def score(input, output, expected, **_):
       return Factuality()(output=output, expected=expected, input=input).score
   ```
3. **Create the online rule** (REST — the SDK has no dedicated method; drive the API). `sampling_rate` is a fraction, `1` = 100%, `0.1` = 10%:
   ```bash
   curl https://api.braintrust.dev/v1/project_score \
     -H "Authorization: Bearer $BRAINTRUST_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "project_id": "<project_id>",
       "name": "prod-faithfulness",
       "score_type": "online",
       "config": { "online": {
         "sampling_rate": 0.1,
         "scorers": [{ "type": "function", "id": "<scorer_function_id>" }],
         "apply_to_root_span": true
       } }
     }'
   ```
   Use `PUT /v1/project_score` to upsert by name, `PATCH /v1/project_score/{id}` to retune the rate. High-volume apps: 1-10%. Critical/low-volume flows: up to 100%.
4. **Watch the score over time** in the project view; wire an alert on the metric moving below band (see Recipe C for the maths if you export the series).

## Recipe B — self-hosted sampling loop (provider-agnostic)

Works against any log store (OTel, Langfuse, a DB, a JSON export). Pattern:

1. **Sample** the last window of traces (e.g. reservoir-sample N, or take every k-th) so scoring cost is bounded and independent of volume.
2. **Score** each sampled trace with your 0-1 scorer; write `[{"id":..., "score":...}, ...]` to `live.json`.
3. **Diff vs golden** and alert:
   ```bash
   python3 scripts/drift.py \
     --baseline golden.json --live live.json \
     --field score --metric faithfulness \
     --psi-warn 0.10 --psi-alert 0.25 --ks-alert 0.20
   ```
   Exit `1` on ALERT (drift breached) so a cron/CI step can Slack/page; `0` on STABLE/WARN; `2` on bad input. Add `--json` for machine-readable output to feed a dashboard.
4. **Schedule** it (cron, GitHub Actions, or the `schedule` skill). Re-baseline deliberately after an *intended* quality change — never let the baseline silently track live, or drift becomes undetectable.

Sampling sketch (stdlib reservoir sample so memory stays flat over a stream):
```python
import random
def reservoir(stream, k):
    keep = []
    for i, x in enumerate(stream):
        if i < k: keep.append(x)
        elif (j := random.randint(0, i)) < k: keep[j] = x
    return keep
```

## What `scripts/drift.py` computes

- **PSI (Population Stability Index)** — the standard drift metric. `<0.10` stable, `0.10-0.25` moderate, `>0.25` significant. Bins the baseline, compares live proportions.
- **KS statistic** — max gap between the two empirical CDFs (distribution-shape drift, no bin choice needed).
- **Mean shift** — direction and size of the average-quality move (a fast, human-readable signal).

Verdict = ALERT if `PSI ≥ psi-alert` **or** `KS ≥ ks-alert`; WARN if `PSI ≥ psi-warn`; else STABLE.

## Drift beyond scores (Galileo-style)

Score drift catches *graded* quality regressions. To also catch **semantic / out-of-distribution** input drift — users asking things your golden set never covered — embed sampled inputs and track distance to the baseline cluster (Galileo calls this K-Core-Distance; a simple version is mean cosine distance to baseline centroid). Rising input-drift with flat score-drift means your evals may be blind to the new traffic — expand the golden set.

## Verify

- `python3 -c "import ast; ast.parse(open('scripts/drift.py').read())"` parses clean.
- Run the drifted fixture and confirm ALERT + exit 1:
  ```bash
  python3 -c "import json,random;random.seed(1);json.dump([round(random.gauss(0.85,0.05),3) for _ in range(200)],open('g.json','w'))"
  python3 -c "import json,random;random.seed(2);json.dump([{'id':i,'score':round(random.gauss(0.72,0.09),3)} for i in range(120)],open('l.json','w'))"
  python3 scripts/drift.py --baseline g.json --live l.json; echo "exit=$?"   # -> [ALERT] ... exit=1
  ```
- Feed identical baseline+live → expect `STABLE`, `PSI=0.0`, exit `0`.
- For the Braintrust path: `curl` the rule creation, send a test log, confirm a score appears on the trace within a minute.

## Pitfalls

- **Sampling rate too low on low volume** — 1% of 300 req/day scores ~3 traces; drift maths is noise. Raise the rate or the window until each run has ≥50-100 scored samples.
- **Baseline drift** — auto-updating the golden set from live traffic hides the very regressions you are watching for. Freeze it; re-baseline only on an intended change, and version it.
- **LLM-judge cost/latency blowup** — never score inline in the request path. Score async (Braintrust) or in a separate cron; that is the whole point of *sampling*.
- **PSI with tiny/degenerate bins** — a single-value or near-empty baseline makes PSI explode; `drift.py` guards with an epsilon and clamps out-of-range values, but prefer ≥100 baseline points and default 10 bins.
- **Judge miscalibration read as drift** — if the *judge* changed (model/prompt), scores shift for reasons unrelated to your app. Pin the judge model+prompt; audit it separately with `llm-judge-bias-audit`.
- **Alerting on a single run** — one noisy window trips a page. Require N consecutive ALERT runs, or alert on a rolling mean, before escalating.
