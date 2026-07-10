---
name: data-contracts
category: data-analysis
description: >-
  Author and enforce data contracts as version-controlled YAML using the Open Data Contract Standard (ODCS v3)
  and the datacontract-cli. Use when the user says "data contract", "ODCS", "datacontract-cli", "schema contract",
  "SLA as code", "breaking-change detection", "contract-first data", or wants a
  git-tracked spec covering schema + quality + SLA that CI can lint, test against real data, and diff between
  versions to block breaking changes before they reach consumers. Grounded on real datacontract-cli 1.x and
  ODCS v3; ships a CI gate script and a runnable local example.
when_to_use:
  - User wants a machine-readable contract (schema, quality rules, SLA) between a data producer and its consumers
  - User wants CI to detect breaking schema changes before a new contract version merges
  - User wants to validate that a real dataset (Postgres, Snowflake, BigQuery, DuckDB, S3, Kafka, parquet/csv) conforms to its contract
  - User wants to generate a contract from existing DDL/SQL/BigQuery/dbt and keep it in the repo
  - User wants to export a contract to HTML docs, JSON Schema, dbt, Great Expectations, or SodaCL
  - User asks about ODCS v3 structure, apiVersion/kind/schema/servers/slaProperties fields
when_not_to_use:
  - User wants standalone row-level dataframe validation without a shared cross-team spec → use data-quality-validation
  - User wants to build and test dbt models (staging/marts) rather than a contract over them → use dbt-analytics-engineering
  - User wants to ingest/extract raw data into a warehouse in the first place → use dlt-python-pipelines
  - User wants virtual-environment SQL transforms with blue-green deploys → use sqlmesh-transformations
keywords:
  - data-contracts
  - odcs
  - datacontract-cli
  - schema-contract
  - breaking-change
  - sla-as-code
  - data-quality
  - producer-consumer
  - contract-first
  - changelog
  - governance
  - ci-gate
  - yaml-schema
  - bitol
  - open-data-contract-standard
similar_to:
  - data-quality-validation
  - dbt-analytics-engineering
  - dlt-python-pipelines
  - sqlmesh-transformations
  - dagster-asset-pipelines
inputs_needed:
  - The dataset to contract (server type + connection, or a local csv/parquet/duckdb file)
  - The schema (columns, types, required/unique/PK) and any existing DDL to import from
  - Quality rules and SLA targets (freshness, row count, uniqueness, latency, availability)
  - Where the baseline (previous) contract version lives, if enforcing breaking-change detection
produces: A version-controlled odcs.yaml contract plus a CI gate (lint + data test + breaking-change changelog) and exported docs/artefacts.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Data Contracts (ODCS + datacontract-cli)

A **data contract** is a version-controlled YAML file that a data *producer* publishes and *consumers* depend on. It pins the schema, quality expectations, and SLAs so that a breaking change is a reviewable diff in git rather than a 3am incident. The **Open Data Contract Standard (ODCS v3)** is the format (`apiVersion: v3.0.0`, `kind: DataContract`); the **datacontract-cli** lints it, tests it against real data, exports it to other formats, and produces a categorised changelog between versions for breaking-change detection.

## When to use

Reach for this when a schema is shared across teams and silent changes cause breakage — a producer table many dashboards read, an event stream downstream jobs parse, a partner data export. If the data lives inside one project and nobody else consumes it, `data-quality-validation` is lighter. If the ask is to *build* the transformations, use `dbt-analytics-engineering`.

## Prerequisites (honest)

- **Python 3.10+.** datacontract-cli 1.x requires 3.10–3.14. **This Mac's `python3` is 3.9 — it will NOT install there.** Use `uv` (fetches its own Python), pipx with a newer interpreter, or Docker:
  ```bash
  # cleanest on this machine — uv brings its own Python, no brew needed:
  curl -LsSf https://astral.sh/uv/install.sh | sh          # if uv absent
  uv tool install --python 3.12 --upgrade 'datacontract-cli[all]'
  datacontract --version                                    # expect 1.0.x

  # or Docker (no local Python at all):
  docker run --rm -v "$PWD":/home/datacontract datacontract/cli lint odcs.yaml
  ```
- `[all]` pulls the DB/engine drivers used by `test` (duckdb, postgres, snowflake, bigquery, kafka, s3…). Slim installs omit them.
- `test` needs credentials for real servers as **environment variables** (e.g. `DATACONTRACT_SNOWFLAKE_USERNAME`), not inline in the YAML.
- License: datacontract-cli and the ODCS spec are **MIT / open**. This skill is authored fresh against their docs; no upstream code is bundled.

## The core loop

`init → lint → test → changelog (gate) → export`. Every step is a real CLI command:

| Command | What it does |
|---|---|
| `datacontract init odcs.yaml` | Scaffold an example ODCS contract |
| `datacontract lint odcs.yaml` | Validate the contract is well-formed (stops at first error) |
| `datacontract test odcs.yaml` | Run schema + quality checks against the live data source |
| `datacontract changelog v1.yaml v2.yaml` | Categorised diff: **info / warning / error(=breaking)** |
| `datacontract import <format> --source …` | Generate a contract from DDL/SQL/BigQuery/dbt/avro/glue/excel |
| `datacontract export <format> …` | Emit html, jsonschema, sql, dbt, avro, protobuf, great-expectations, sodacl, pydantic-model, sqlalchemy, excel… |
| `datacontract edit odcs.yaml` | Open the visual Data Contract Editor |

> Note: the standalone `breaking` and `diff` subcommands were **removed in CLI 1.0.0**. Breaking-change detection now runs through `changelog`, whose **error**-level entries are the breaking ones (see the CI gate below).

## Recipe 1 — author a contract from scratch

`datacontract init odcs.yaml` writes a working example; edit it down to your columns. A minimal ODCS v3 contract over a DuckDB/parquet table:

```yaml
apiVersion: v3.0.0
kind: DataContract
id: orders-analytics
name: Orders
version: 1.0.0
status: active
description:
  purpose: Cleaned order events for analytics consumers.
servers:
  production:
    type: duckdb
    path: ./orders.duckdb
    schema: main
schema:
  - name: orders
    physicalType: table
    properties:
      - name: order_id
        logicalType: string
        physicalType: VARCHAR
        required: true
        unique: true
        primaryKey: true
      - name: customer_id
        logicalType: string
        required: true
      - name: amount
        logicalType: number
        physicalType: DECIMAL
        required: true
        quality:
          - type: sql
            query: SELECT COUNT(*) FROM orders WHERE amount < 0
            mustBe: 0            # no negative amounts
      - name: created_at
        logicalType: date
        physicalType: TIMESTAMP
        required: true
    quality:
      - type: sql
        description: at least a day's worth of rows
        query: SELECT COUNT(*) FROM orders
        mustBeGreaterThan: 1000
slaProperties:
  - property: latency          # freshness target
    value: 6
    unit: h
  - property: frequency
    value: 1
    unit: d
team:
  - username: data-platform@acme.com
    role: owner
```

Then `datacontract lint odcs.yaml` — fix until clean.

## Recipe 2 — generate a contract from existing DDL

Don't hand-type columns you already have. Import, then curate:

```bash
datacontract import sql --source schema.sql --dialect postgres --output odcs.yaml
# other sources: bigquery, glue, avro, jsonschema, dbt, dbml, excel, unity, iceberg, parquet
datacontract lint odcs.yaml
```

## Recipe 3 — test a contract against real data

```bash
# local file server (type: duckdb / csv / parquet) needs no creds:
datacontract test odcs.yaml

# remote server — creds via env vars, never in the YAML:
export DATACONTRACT_SNOWFLAKE_USERNAME=svc_reader
export DATACONTRACT_SNOWFLAKE_PASSWORD=…
datacontract test odcs.yaml
```
`test` checks every record complies with the declared schema and that each `quality` block passes, printing per-check pass/fail.

## Recipe 4 — CI gate: block breaking changes

The point of a contract is that raising `version` and changing the schema is a reviewable event. In PR CI, compare the proposed contract against the baseline on the main branch and fail on error-level (breaking) changes. Use the bundled helper:

```bash
scripts/contract_gate.sh odcs.yaml baseline/odcs.yaml
```

It runs `lint`, prints the `changelog`, and exits non-zero when the changelog reports an **error** (breaking) entry. GitHub Actions:

```yaml
name: data-contract
on: [pull_request]
jobs:
  contract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - run: pipx install 'datacontract-cli[all]'
      - name: baseline from main
        run: git show origin/main:odcs.yaml > baseline.odcs.yaml || echo "no baseline"
      - run: bash scripts/contract_gate.sh odcs.yaml baseline.odcs.yaml
```
Removing a required field, tightening a type, or dropping a column surfaces as an **error** in the changelog and fails the job; adding an optional field is **info** and passes. Bump `version` (semver) in the same PR: breaking → major, additive → minor.

## Recipe 5 — publish docs & downstream artefacts

```bash
datacontract export html odcs.yaml --output contract.html          # human-readable page
datacontract export jsonschema odcs.yaml                            # for app-side validation
datacontract export great-expectations odcs.yaml                    # GX suite
datacontract export dbt odcs.yaml                                   # dbt sources/models
datacontract export sodacl odcs.yaml                                # Soda checks
```

## Verify

```bash
datacontract --version                 # 1.0.x — confirms install worked
datacontract lint odcs.yaml            # "Data contract is valid" before committing
datacontract test odcs.yaml            # all checks pass against your data
bash scripts/contract_gate.sh odcs.yaml baseline.odcs.yaml   # gate green on additive, red on breaking
```
A contract is "done" only when `lint` is clean, `test` passes against the real source, and the gate correctly reds on a deliberately breaking edit (delete a required column and re-run to confirm).

## Pitfalls

- **Python 3.9 install fails silently-ish** — the pip resolver just backtracks. Install with `uv --python 3.12` or Docker (see Prerequisites).
- **`breaking`/`diff` commands are gone** (removed in 1.0.0). Anyone copying an old tutorial will hit "no such command". Use `changelog` and grade on error-level entries.
- **Missing engine drivers** — `test` errors like "unknown server type" mean you installed without `[all]`. Reinstall with the extras.
- **Creds in YAML** — never. `servers` holds host/type/path; secrets come from `DATACONTRACT_*` env vars. Committing a password is a security finding.
- **Forgetting to bump `version`** — the changelog compares whatever two files you give it; keep the baseline = last merged version and bump semver in the same PR so the gate is meaningful.
- **ODCS vs the older Data Contract Specification** — datacontract-cli supports both, but keep the whole repo on ODCS v3 (`apiVersion: v3.0.0`, `kind: DataContract`) so `changelog` compares like-for-like. Don't mix formats across versions.
- **Contract without a `test` in CI is theatre** — lint only proves the YAML is well-formed. Schedule `datacontract test` against the real source (nightly or on producer deploy) or the contract drifts from reality.
