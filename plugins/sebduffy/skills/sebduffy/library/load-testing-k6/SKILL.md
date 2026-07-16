---
name: load-testing-k6
category: devops
description: >-
  Write and run k6 (or Locust) load tests that model real traffic — ramping VUs, constant
  arrival-rate spikes, staged soak tests — and gate CI on p95/p99 latency and error-rate
  thresholds so a failing test breaks the build. Reach for this the moment someone says
  "load test", "will this survive the campaign launch", "simulate a traffic spike", "check p95
  under load", "stress test the API", "k6 script", "Locust", or "add a performance gate to CI".
when_to_use:
  - Sizing a service before a campaign launch, big drop, or expected traffic spike
  - Modelling ramp-up / spike / soak / stress profiles against an HTTP API or site
  - Gating a pipeline on p95/p99 response time and error rate so regressions fail the build
  - Reproducing a "site fell over under load" incident with a controlled, repeatable script
  - Choosing between closed-model (VUs) and open-model (arrival-rate) load and setting the numbers
  - Parameterising env (base URL, VUs, duration) so the same script runs local, staging, CI
when_not_to_use:
  - Authoring the CI workflow scaffolding itself (matrix, caching, OIDC) — use github-actions-pipelines
  - Instrumenting the service with traces/metrics and defining SLOs — use opentelemetry-observability-slo
  - Right-sizing pod requests/limits/HPA from the load results — use kubernetes-workload-deploy
  - Functional browser E2E assertions (not throughput) — use webapp-testing
  - Diagnosing why the service is slow once load reveals it — use systematic-debugging
keywords:
  - load-testing
  - k6
  - locust
  - performance
  - p95
  - p99
  - thresholds
  - stress-test
  - soak-test
  - arrival-rate
  - virtual-users
  - traffic-spike
  - ci-gate
  - latency
similar_to:
  - github-actions-pipelines
  - opentelemetry-observability-slo
  - kubernetes-workload-deploy
  - incident-response-and-postmortem
inputs_needed: Target base URL/endpoint(s), expected peak load (req/s or concurrent users), latency + error SLO to gate on, and whether it runs local, in CI, or against staging (never prod without sign-off).
produces: A parameterised k6 (or Locust) test script, threshold-based pass/fail gates, a CI workflow step that fails on breach, and a summary/JSON report of p95/p99 + error rate.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Load Testing with k6 (p95/p99 CI gates)

Model realistic traffic against an API or site, then **fail the build** when latency or error
budgets are blown. Default to **k6** (single binary, JS scripts, native thresholds → non-zero
exit). Reach for **Locust** only when the team lives in Python or needs complex stateful user
flows expressed as classes.

## When to use

Before a campaign launch or any anticipated spike; when adding a performance gate to CI; when
reproducing a load-related incident. If you only need "does the page work" (not "how fast under
N users"), that's `webapp-testing`, not this.

## Prerequisites

- **k6 binary.** No `brew` on this Mac — release assets are versioned (`k6-vX.Y.Z-...`), so fetch the latest tag first, then download:
  `TAG=$(curl -s https://api.github.com/repos/grafana/k6/releases/latest | grep -m1 tag_name | cut -d'"' -f4) && curl -sL "https://github.com/grafana/k6/releases/download/${TAG}/k6-${TAG}-macos-arm64.zip" -o k6.zip && unzip k6.zip` (or `-macos-amd64` on Intel). Put the `k6` binary on `PATH`. Check with `k6 version`. In CI, use the official actions/image (below) — no local install.
- **A target you are authorised to hit.** Load testing is a DoS against your own infra. Test local/staging by default. Against shared or prod-adjacent environments, get explicit sign-off and warn on-call — a spike test *is* an outage rehearsal.
- **Realistic numbers.** Peak req/s or concurrent users, and the SLO you gate on (e.g. p95 < 500 ms, error rate < 1%). Guessing these makes the test theatre.
- **Locust path only:** `python3 -m pip install locust` (works on the system 3.9).

## Recipe 1 — k6 script with p95/p99 gates

`load-test.js` — thresholds live in `options.thresholds`; a breach makes k6 exit non-zero (CI-friendly). Everything is parameterised via env vars so one script runs everywhere.

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

export const options = {
  // Closed model: N concurrent virtual users ramping over time.
  stages: [
    { duration: '30s', target: 50 },   // ramp up
    { duration: '2m',  target: 50 },   // hold at peak
    { duration: '30s', target: 0 },    // ramp down
  ],
  thresholds: {
    // p95 under 500ms, p99 under 1s — a breach fails the run (non-zero exit).
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    // Fewer than 1% failed requests.
    http_req_failed: ['rate<0.01'],
    // Custom per-endpoint check must pass 99% of the time.
    checks: ['rate>0.99'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}/api/health`);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'body not empty': (r) => r.body.length > 0,
  });
  sleep(1); // model think-time between user actions
}
```

Run it:

```bash
k6 run -e BASE_URL=https://staging.example.com load-test.js
# override load without editing the file:
k6 run --vus 100 --duration 90s -e BASE_URL=https://staging.example.com load-test.js
# machine-readable summary for dashboards/artifacts:
k6 run --summary-export=summary.json load-test.js
```

k6 prints per-metric threshold pass/fail and exits `0` on pass, non-zero on any breach.

## Recipe 2 — spike test with the open model (arrival rate)

Concurrent-VU stages throttle themselves when the server slows (fewer iterations finish, so
offered load drops — hiding the problem). To model a real **campaign spike** — "10k req/s
arrives whether or not you can serve it" — use an **arrival-rate** executor. k6 adds VUs to
sustain the *rate*, so a slow server shows as queued/failed requests, which is the truth.

```javascript
export const options = {
  scenarios: {
    campaign_spike: {
      executor: 'ramping-arrival-rate',
      startRate: 100,            // requests per timeUnit at start
      timeUnit: '1s',            // → 100 req/s
      preAllocatedVUs: 200,      // VU pool ready before the spike
      maxVUs: 2000,              // ceiling k6 may spin up to hold the rate
      stages: [
        { duration: '15s', target: 100 },   // baseline
        { duration: '10s', target: 3000 },  // the spike: 100 → 3000 req/s
        { duration: '1m',  target: 3000 },  // sustained peak
        { duration: '20s', target: 0 },     // drain
      ],
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<800', 'p(99)<1500'],
    http_req_failed: ['rate<0.02'],
  },
};
```

Use `abortOnFail` to stop early (and save spend) when a gate is already blown:

```javascript
thresholds: {
  http_req_duration: [{ threshold: 'p(99)<1500', abortOnFail: true, delayAbortEval: '10s' }],
}
```

Choosing a profile: **ramping-vus** = "how many concurrent users can we hold" (checkout, login);
**ramping-arrival-rate** = "can we absorb X req/s regardless" (ad click-through, launch traffic).
A **soak** is a long hold (`{ duration: '2h', target: 200 }`) to catch leaks; a **stress** test
ramps past expected peak until thresholds break, to find the ceiling.

## Recipe 3 — gate it in CI (GitHub Actions)

Official actions install k6 and run the test; a threshold breach fails the job automatically. See
`github-actions-pipelines` for hardening (SHA-pins, permissions).

```yaml
name: load-test
on: [workflow_dispatch, pull_request]
jobs:
  k6:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: grafana/setup-k6-action@v1
      - uses: grafana/run-k6-action@v1
        with:
          path: ./tests/load-test.js
        env:
          BASE_URL: ${{ vars.STAGING_URL }}
```

No-action equivalent (Docker) if you prefer explicit control:

```bash
docker run --rm -i -e BASE_URL="$STAGING_URL" -v "$PWD:/src" \
  grafana/k6 run /src/tests/load-test.js
```

Both surface k6's non-zero exit to the runner, so a busted p95/p99 or error rate **breaks the
build** with no extra parsing.

## Recipe 4 — Locust alternative (Python teams)

`locustfile.py` — user behaviour as a class; gate p95/error-rate in a `quitting` hook so CI fails.

```python
from locust import HttpUser, task, between, events

class CampaignUser(HttpUser):
    wait_time = between(1, 3)  # think-time

    @task
    def health(self):
        self.client.get("/api/health", name="/api/health")

# Fail the process (non-zero exit) when SLOs are breached — CI gate.
@events.quitting.add_listener
def _gate(environment, **_):
    stats = environment.stats.total
    if stats.get_response_time_percentile(0.95) > 500:
        environment.process_exit_code = 1
    elif stats.num_requests and stats.fail_ratio > 0.01:
        environment.process_exit_code = 1
```

```bash
# Headless (CI): 200 users, spawn 20/s, 2 minutes, then exit with the gate's code.
locust -f locustfile.py --headless -u 200 -r 20 -t 2m \
  --host https://staging.example.com --csv results
```

## Verify

- `k6 version` prints a version; `k6 run load-test.js` against a local echo server exits `0`.
- Force a breach to prove the gate bites: set a hostile threshold (`http_req_duration: ['p(95)<1']`) and confirm k6 exits non-zero and the CI job goes red.
- `summary.json` (or Locust `results_stats.csv`) contains the p95/p99 and error-rate numbers you gated on — attach it as a CI artifact.
- Sanity-check offered load: for arrival-rate, confirm `http_reqs` rate ≈ your target; if VUs hit `maxVUs`, raise the ceiling or the numbers are meaningless.

## Pitfalls

- **Testing prod without sign-off.** A spike test is a self-inflicted DoS. Default to staging; get explicit approval and warn on-call before anything shared. This is the one that gets people fired.
- **Closed-model spike tests lie.** Concurrent-VU stages back off when the server slows, so you never see the cliff. Model real spikes with `ramping-arrival-rate`.
- **`maxVUs` too low.** If k6 can't allocate enough VUs to sustain the rate, it silently under-delivers load and everything "passes". Watch the console warning and the achieved `http_reqs` rate.
- **Load generator is the bottleneck.** A single laptop/runner caps out (CPU, sockets, ephemeral ports) well before a real fleet. If generator CPU is pegged, distribute (k6 Cloud / multiple runners, Locust workers) — don't trust the numbers.
- **No think-time / no sleep** turns a load test into a tight-loop hammer that doesn't resemble users and inflates req/s unrealistically. Model pacing with `sleep()` / `wait_time`.
- **Averages hide the pain.** Gate on `p(95)`/`p(99)`, never `avg` — the tail is what your campaign users feel.
- **Cold caches / no warm-up.** First-hit latency skews p99. Add a short warm-up stage or discard it.
- **Hardcoded URLs.** Parameterise via `__ENV` / `--host` so the same script runs local, CI, and staging without edits.
