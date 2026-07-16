---
name: opentelemetry-observability-slo
category: devops
description: >
  Verb-first trigger when you must instrument a service with OpenTelemetry (traces, metrics, logs),
  stand up an OTel Collector, ship signals to Prometheus + Grafana or an OTLP backend, and turn raw
  telemetry into SLOs with error budgets and multiwindow burn-rate alerts. Use when you need
  auto/manual OTel SDK instrumentation, OTLP exporters, a Collector pipeline (receivers/processors/
  exporters), RED/USE dashboards, PromQL SLIs, recording rules, or Google-SRE burn-rate paging.
when_to_use:
  - Instrumenting an app (Python/Node/Go/Java) with the OpenTelemetry SDK — traces, metrics, and logs over OTLP
  - Standing up an OTel Collector with otlp receivers, batch/memory_limiter processors, and prometheus/otlphttp exporters
  - Wiring telemetry into Prometheus + Grafana (or a vendor OTLP endpoint) and building RED/USE dashboards
  - Defining an SLO with an SLI, an error budget, and Prometheus recording rules over a 30-day window
  - Adding multiwindow multi-burn-rate alerts (14.4x / 6x / 1x) that page on fast budget burn and ticket on slow burn
  - Adding trace context propagation, span attributes, and exemplars that link metrics to traces
when_not_to_use:
  - Tracing LLM/agent calls or token usage specifically — use an LLM-observability skill instead
  - Building the CI pipeline that deploys the Collector or dashboards — use github-actions-pipelines instead
  - Provisioning the managed Prometheus/Grafana/observability infra itself — use terraform-iac-modules instead
  - Deploying the Collector as a Kubernetes workload (DaemonSet/Deployment manifests) — use kubernetes-workload-deploy instead
  - Reacting to a live incident and writing the postmortem — use incident-response-and-postmortem instead
keywords: [opentelemetry, otel, otlp, collector, traces, metrics, logs, prometheus, grafana, slo, sli, error-budget, burn-rate, observability, promql, instrumentation, exemplars, red-method]
similar_to: [kubernetes-workload-deploy, github-actions-pipelines, terraform-iac-modules, incident-response-and-postmortem]
inputs_needed: A running service you can add a dependency to and set env vars on; an OTLP-capable backend (self-hosted Prometheus + Grafana, or a vendor endpoint + token); and a target SLO (e.g. 99.9% availability over 30 days) with a defined "good vs bad" request criterion.
produces: An instrumented service emitting OTLP, a validated Collector config, Prometheus recording rules for the SLI, a Grafana-ready RED dashboard query set, and multiwindow burn-rate alert rules (scripts/gen_burn_rate_alerts.py).
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# OpenTelemetry Observability + SLOs

End-to-end path: **instrument → collect → store → measure → alert.** OpenTelemetry
(OTel) is the vendor-neutral standard for producing traces, metrics, and logs; the
Collector routes them; Prometheus + Grafana (or any OTLP backend) store and visualise;
SLOs + burn-rate alerts turn the data into a paging signal engineers trust.

## When to use

Reach for this when a service is a black box: you can see it's up but not *why* it's
slow, or you page on CPU instead of on user pain. This skill gets you real request-level
telemetry and an SLO-based alert that fires proportionally to error-budget burn.

## Prerequisites

- **A backend that speaks OTLP.** Simplest self-hosted stack: OTel Collector →
  Prometheus (metrics via `remote_write` or the Collector's `prometheus` exporter that
  Prometheus scrapes) + Grafana. Traces need a trace store (Tempo/Jaeger). Vendor
  backends (Grafana Cloud, Honeycomb, Datadog, New Relic) accept OTLP directly — you only
  need an endpoint + API token, no Collector required for a first cut.
- **OTLP ports:** gRPC `4317`, HTTP `4318`. Keep these straight — a wrong port is the #1
  "nothing shows up" bug.
- **Language SDK.** Install the OTel SDK + OTLP exporter for your runtime (examples below).
- **Prometheus 2.x+** with recording/alerting rules enabled, and Alertmanager for routing.
- No API keys needed for self-hosted; vendor OTLP needs `OTEL_EXPORTER_OTLP_HEADERS`.

## Recipes

### 1. Instrument a service (SDK)

**Python** — zero-code auto-instrumentation is the fastest start:
```bash
pip install opentelemetry-distro opentelemetry-exporter-otlp
opentelemetry-bootstrap -a install          # pulls instrumentation for your libs
OTEL_SERVICE_NAME=checkout \
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 \
OTEL_TRACES_EXPORTER=otlp OTEL_METRICS_EXPORTER=otlp OTEL_LOGS_EXPORTER=otlp \
  opentelemetry-instrument python app.py
```
Manual span + attribute (do this for business-meaningful operations):
```python
from opentelemetry import trace
tracer = trace.get_tracer("checkout")
with tracer.start_as_current_span("charge_card") as span:
    span.set_attribute("payment.provider", "stripe")
    span.set_attribute("order.value_gbp", amount)
    # ... work ...
```

**Node.js:**
```bash
npm i @opentelemetry/api @opentelemetry/auto-instrumentations-node @opentelemetry/exporter-trace-otlp-http
OTEL_SERVICE_NAME=checkout OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318 \
  node --require @opentelemetry/auto-instrumentations-node/register app.js
```

Key env vars (spec-standard across all SDKs): `OTEL_SERVICE_NAME`,
`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_PROTOCOL` (`grpc` |
`http/protobuf`), `OTEL_RESOURCE_ATTRIBUTES` (e.g. `deployment.environment=prod,service.version=1.4.2`).
Always set `service.name` — it's the primary key everything groups by.

### 2. Collector config (`otel-collector.yaml`)

The Collector decouples your app from your backend (batching, retries, redaction,
fan-out). Configuring a component does **not** enable it — it must appear in a
`service.pipelines` block.
```yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: 0.0.0.0:4317 }
      http: { endpoint: 0.0.0.0:4318 }
processors:
  memory_limiter:                 # FIRST processor — prevents OOM under load
    check_interval: 5s
    limit_mib: 512
    spike_limit_mib: 128
  batch: {}                       # batches to reduce egress calls
exporters:
  prometheus:                     # Prometheus scrapes this endpoint
    endpoint: 0.0.0.0:8889
  otlphttp:                       # forward traces/logs to a backend
    endpoint: https://otlp.example.com
  debug:                          # replaces the old `logging` exporter
    verbosity: normal
service:
  pipelines:
    traces:  { receivers: [otlp], processors: [memory_limiter, batch], exporters: [otlphttp, debug] }
    metrics: { receivers: [otlp], processors: [memory_limiter, batch], exporters: [prometheus] }
    logs:    { receivers: [otlp], processors: [memory_limiter, batch], exporters: [otlphttp] }
```
Run it: `otelcol-contrib --config otel-collector.yaml` (the `-contrib` distro carries
the extra receivers/exporters most stacks need). Point Prometheus to scrape
`otel-collector:8889`.

### 3. SLI recording rules (Prometheus)

Compute the *bad-event ratio* over the windows the burn-rate alerts need. RED method:
Rate, Errors, Duration. Availability SLI = fraction of requests that errored:
```yaml
groups:
  - name: checkout-sli
    rules:
      - record: job:slo_errors:ratio_rate5m
        expr: |
          sum(rate(http_server_request_duration_seconds_count{service="checkout",http_response_status_code=~"5.."}[5m]))
          /
          sum(rate(http_server_request_duration_seconds_count{service="checkout"}[5m]))
        labels: { service: checkout }
      # repeat for 30m, 1h, 6h, 3d windows (same expr, swap [Xm]/[Xh]/[Xd])
```
Latency SLI (fraction slower than 300ms, needs histogram buckets):
`1 - (sum(rate(..._bucket{le="0.3"}[5m])) / sum(rate(..._count[5m])))`.
Note OTel's HTTP metric is `http.server.request.duration` (seconds, histogram) — dots
become underscores in Prometheus. Older SDKs emit `http_server_duration_milliseconds`.

### 4. SLO + error budget + burn-rate alerts

Error budget = `1 − SLO`. For 99.9% over 30 days the budget is 0.1% of requests
(~43m of full downtime). Page fast when the budget burns fast; ticket when it burns
slow. Generate the 4-alert multiwindow scheme (Google SRE Workbook):
```bash
python3 scripts/gen_burn_rate_alerts.py --service checkout --objective 99.9 \
  > checkout-burn-rate.rules.yaml
```
This emits the standard tiers, each requiring **both** a long and short window to
exceed the threshold (the short window gives fast reset, cutting false pages):

| Long / short | Burn rate | Budget consumed | Severity |
|--------------|-----------|-----------------|----------|
| 1h / 5m      | 14.4x     | 2%              | page     |
| 6h / 30m     | 6x        | 5%              | page     |
| 3d / 6h      | 1x        | 10%             | ticket   |

Load both rule files in `prometheus.yml` under `rule_files:` and route
`severity: page` to Alertmanager's pager receiver.

### 5. Grafana RED dashboard queries

- **Rate:** `sum(rate(http_server_request_duration_seconds_count{service="$svc"}[5m]))`
- **Errors:** the `job:slo_errors:ratio_rate5m` rule × 100 for an error-% panel
- **Duration (p95):** `histogram_quantile(0.95, sum(rate(http_server_request_duration_seconds_bucket{service="$svc"}[5m])) by (le))`
- **Remaining budget:** `1 - (sum(increase(...err_count[30d])) / sum(increase(...count[30d]))) ) / 0.001`
- Enable **exemplars** in the metrics pipeline so a latency spike links straight to the
  slow trace — turn on exemplar storage in Prometheus and exemplar display in the panel.

## Verify

1. **App emits:** run with `OTEL_TRACES_EXPORTER=console` (or add the `debug` exporter)
   and confirm spans print with your `service.name` and attributes.
2. **Collector receives:** `debug` exporter at `verbosity: normal` logs accepted spans;
   check the Collector's own `:8888/metrics` for `otelcol_receiver_accepted_spans`.
3. **Prometheus scrapes:** query `up{job="otel-collector"} == 1` and confirm your
   metric name (e.g. `http_server_request_duration_seconds_count`) returns series.
4. **Rules load:** Prometheus UI → Status → Rules shows the SLI + burn-rate groups with
   no evaluation errors. `promtool check rules *.rules.yaml` validates syntax offline.
5. **Alert logic:** the generator is stdlib-only —
   `python3 scripts/gen_burn_rate_alerts.py --service demo --objective 99.9` prints valid
   YAML; confirm thresholds are 0.0144 / 0.006 / 0.001 for a 99.9% target.

## Pitfalls

- **Wrong OTLP port/protocol.** gRPC=4317, HTTP=4318. `OTEL_EXPORTER_OTLP_PROTOCOL` must
  match the port; mixing `grpc` with `:4318` silently drops everything.
- **`prometheus` exporter is scrape-pull, not push.** Prometheus must be configured to
  scrape the Collector's `:8889`; the Collector does not push to it. To push, use the
  `prometheusremotewrite` exporter instead.
- **`logging` exporter is gone** — it's `debug` now. Old configs fail to start.
- **`memory_limiter` must be the first processor** or the Collector can OOM before it
  throttles.
- **Metric name drift.** Semantic conventions renamed HTTP metrics (`http.server.duration`
  ms → `http.server.request.duration` s). Your PromQL must match what your SDK version
  actually emits — check `:8889/metrics` before writing queries.
- **Alerting on symptoms not SLOs.** CPU/memory alerts page on non-problems and miss real
  user pain. Burn-rate alerts fire proportionally to budget spend — prefer them.
- **No `service.name` = orphaned telemetry.** Everything groups by resource attributes;
  set them at startup, not per-span.
- **Cardinality explosions.** Never put user IDs, request IDs, or full URLs in *metric*
  attributes — that belongs on spans. High-cardinality metric labels melt Prometheus.
- **Sampling ≠ metrics.** Tail-sampling traces is fine, but keep metrics unsampled —
  SLIs must count every request or the ratio is wrong.
