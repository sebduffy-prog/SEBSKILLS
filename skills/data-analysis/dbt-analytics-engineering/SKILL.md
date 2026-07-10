---
name: dbt-analytics-engineering
category: data-analysis
description: >-
  Build a production dbt Core project the way analytics engineers actually do it — sources + freshness,
  staging/intermediate/marts layering, generic + singular tests, incremental models, seeds, packages, and
  auto-generated docs. Use when the user says "dbt", "build a dbt model", "staging and marts", "add dbt tests",
  "incremental model", "source freshness", "dbt docs", "sql transformation project", or is turning raw warehouse
  tables into tested, documented analytics tables. Grounds every command and every YAML key against real dbt 1.x
  syntax — never fabricates flags. Ships a runnable DuckDB example so the whole loop works locally with no cloud warehouse.
when_to_use:
  - User wants to scaffold or structure a dbt Core project (staging / intermediate / marts)
  - User wants to declare sources and add freshness checks over raw warehouse tables
  - User wants to add tests (unique, not_null, accepted_values, relationships, singular SQL tests)
  - User wants an incremental model or is asking how is_incremental() / unique_key work
  - User wants dbt docs, exposures, or a dependency lineage graph generated
  - User wants dbt_utils / packages wired in, or a seed CSV loaded as a table
when_not_to_use:
  - User wants Python-native transforms without a SQL-first framework → use polars-dataframes or duckdb-analytics
  - User wants an alternative SQL transform tool with virtual environments / blue-green → use sqlmesh-transformations
  - User wants an orchestrated asset graph across many tools → use dagster-asset-pipelines
  - User wants to ingest/extract raw data into the warehouse in the first place → use dlt-python-pipelines
  - User wants standalone row-level validation without a warehouse → use data-quality-validation
keywords:
  - dbt
  - analytics-engineering
  - staging
  - marts
  - sources
  - freshness
  - incremental
  - jinja
  - dbt-tests
  - dbt-docs
  - dbt_utils
  - seed
  - materialization
  - duckdb
  - warehouse
  - elt
similar_to:
  - sqlmesh-transformations
  - duckdb-analytics
  - dlt-python-pipelines
  - data-quality-validation
  - dagster-asset-pipelines
inputs_needed:
  - Target warehouse / adapter (DuckDB for local, else Snowflake / BigQuery / Postgres / Redshift) and connection creds
  - The raw source tables (schema + table names) to model
  - What marts / business questions the models should answer
produces: A layered, tested, documented dbt project (dbt_project.yml, profiles.yml, sources + schema YAML, staging/marts models, tests) that runs green via `dbt build`.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# dbt Analytics Engineering

Turn raw warehouse tables into **tested, documented, layered** analytics tables with dbt Core. This skill
encodes the dbt-labs house layering (staging → intermediate → marts), source freshness, the four generic tests,
incremental models, and docs — all grounded against real dbt 1.x syntax.

## When to use

Reach for this whenever the deliverable is a **SQL-first, version-controlled transformation layer** on top of a
warehouse. If there is no warehouse and the user just wants a dataframe, use `polars-dataframes` /
`duckdb-analytics` instead.

## Prerequisites

- **Python 3.8–3.12.** dbt Core is a pip package. On this Mac (py3.9), install into a venv.
- **An adapter.** dbt-core alone does nothing — you install a warehouse adapter. For a **zero-infra local loop
  use `dbt-duckdb`** (recommended for demos/tests). Cloud: `dbt-snowflake`, `dbt-bigquery`, `dbt-postgres`,
  `dbt-redshift`, `dbt-databricks`.
- **A `profiles.yml`** with connection creds (default lives at `~/.dbt/profiles.yml`; override with
  `--profiles-dir .` to keep it in-repo). **Never commit real credentials** — use `env_var('...')`.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install dbt-core dbt-duckdb        # swap dbt-duckdb for your adapter
dbt --version                          # confirm Core + adapter both listed
```

## Recipes

### 1. Scaffold the project

```bash
dbt init analytics            # interactive: pick adapter, name the profile
cd analytics
dbt debug --profiles-dir .    # verifies the connection compiles + opens
```

`dbt_project.yml` is the project root config. Set the layer materializations here (staging = views, marts = tables):

```yaml
# dbt_project.yml
name: analytics
version: "1.0.0"
profile: analytics            # must match a key in profiles.yml
model-paths: ["models"]
seed-paths: ["seeds"]
target-path: "target"
models:
  analytics:
    staging:
      +materialized: view
    marts:
      +materialized: table
```

A minimal local DuckDB profile (keep it in-repo, no secrets):

```yaml
# profiles.yml
analytics:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: dev.duckdb
      threads: 4
```

### 2. Declare sources + freshness

Sources name the **raw** tables so models reference `{{ source(...) }}`, not hardcoded schemas — giving you
lineage and freshness monitoring for free. Use the current nested `config.freshness` form (dbt 1.9+):

```yaml
# models/staging/_sources.yml
version: 2
sources:
  - name: jaffle_shop
    schema: raw
    tables:
      - name: orders
        config:
          loaded_at_field: _etl_loaded_at
          freshness:
            warn_after:  {count: 12, period: hour}
            error_after: {count: 24, period: hour}
      - name: customers      # no freshness = not monitored
```

```bash
dbt source freshness --profiles-dir .          # emits warn/error/pass per source
# only rebuild what went stale:
dbt build --profiles-dir . --select source_status:fresher+
```

### 3. Staging models (`stg_` — one per source table, 1:1, light cleanup only)

Staging is where you rename, cast, and coerce — **no joins, no business logic**. Materialized as views.

```sql
-- models/staging/stg_orders.sql
with source as (
    select * from {{ source('jaffle_shop', 'orders') }}
)
select
    id            as order_id,
    user_id       as customer_id,
    order_date,
    status,
    _etl_loaded_at
from source
```

### 4. Marts (`dim_` / `fct_` — joins + business logic, materialized as tables)

Marts reference staging with `{{ ref(...) }}` so dbt infers the DAG. Never `ref()` a source table directly.

```sql
-- models/marts/fct_orders.sql
with orders as (
    select * from {{ ref('stg_orders') }}
),
customers as (
    select * from {{ ref('stg_customers') }}
)
select
    o.order_id,
    o.customer_id,
    c.customer_name,
    o.order_date,
    o.status
from orders o
left join customers c using (customer_id)
```

> Use an **intermediate** layer (`models/intermediate/int_*.sql`, ephemeral or view) only when a mart's logic
> gets reused or too gnarly to read — not by default (YAGNI).

### 5. Tests — the four generic tests + singular tests

Attach generic tests in YAML next to the models. (dbt 1.8+ prefers the key `data_tests:`; the old `tests:`
still works.) These are the workhorses:

```yaml
# models/marts/_marts.yml
version: 2
models:
  - name: fct_orders
    description: One row per order, enriched with customer.
    columns:
      - name: order_id
        description: Primary key.
        data_tests: [unique, not_null]
      - name: status
        data_tests:
          - accepted_values:
              values: ['placed', 'shipped', 'completed', 'returned']
      - name: customer_id
        data_tests:
          - relationships:
              to: ref('stg_customers')
              field: customer_id
```

A **singular test** is any SQL that should return **zero rows** to pass — drop it in `tests/`:

```sql
-- tests/assert_no_future_orders.sql
select * from {{ ref('fct_orders') }} where order_date > current_date
```

```bash
dbt test --profiles-dir .                       # run all tests
dbt test --profiles-dir . --select fct_orders   # just one model's tests
```

### 6. Incremental models (append only new/changed rows on each run)

For large event tables, don't rebuild from scratch. `is_incremental()` is true only on runs where the table
already exists, letting you filter to the new slice. `unique_key` turns inserts into merges (upserts).

```sql
-- models/marts/fct_events.sql
{{ config(materialized='incremental', unique_key='event_id', on_schema_change='append_new_columns') }}

select event_id, user_id, event_type, event_at
from {{ ref('stg_events') }}
{% if is_incremental() %}
  -- only rows newer than what we already loaded
  where event_at > (select coalesce(max(event_at), '1900-01-01') from {{ this }})
{% endif %}
```

```bash
dbt run  --profiles-dir . --select fct_events              # incremental run
dbt run  --profiles-dir . --select fct_events --full-refresh  # rebuild from scratch
```

### 7. Seeds + packages

Small static CSVs (country codes, mappings) go in `seeds/` and load with `dbt seed`. Reference them with
`{{ ref('my_seed') }}`. Reusable macros/tests come from packages:

```yaml
# packages.yml
packages:
  - package: dbt-labs/dbt_utils
    version: [">=1.1.0", "<2.0.0"]
```

```bash
dbt deps --profiles-dir .     # installs packages into dbt_packages/
dbt seed --profiles-dir .     # loads seeds/*.csv as tables
```

### 8. Build everything in DAG order + generate docs

`dbt build` runs seeds → models → tests → snapshots **in dependency order**, stopping a downstream model if
its upstream test fails. This is the command to wire into CI.

```bash
dbt build --profiles-dir .                    # the one command that does it all
dbt docs generate --profiles-dir .            # builds catalog.json + manifest.json
dbt docs serve --profiles-dir .               # lineage graph + column docs at localhost:8080
```

## Verify

The loop is real and local — prove it end to end with DuckDB:

```bash
source .venv/bin/activate
dbt debug   --profiles-dir .    # connection + config OK
dbt build   --profiles-dir .    # PASS on every model + test → green
dbt test    --profiles-dir . --store-failures   # failing rows land in a table you can inspect
```

- `dbt ls --profiles-dir .` lists resources dbt sees — if a model is missing, the file is misnamed/misplaced.
- `dbt compile --profiles-dir .` writes rendered SQL to `target/compiled/` — read it to confirm `ref()`/`source()`
  resolved to the schemas you expect **before** running against a real warehouse.

## Pitfalls

- **`ref()` for models, `source()` for raw tables — never hardcode `schema.table`.** Hardcoding breaks lineage,
  freshness, and environment swaps (dev vs prod).
- **Business logic in staging.** Staging is 1:1 rename/cast only. Joins and aggregations belong in intermediate/marts.
- **Incremental without a filter.** If you forget the `{% if is_incremental() %}` guard, every run reprocesses the
  full table — same cost as a table model, but now with duplicate-row risk. Always test with `--full-refresh` once.
- **`unique_key` misunderstanding.** Without it, incremental only *appends* — late-arriving updates to an existing
  key duplicate. Set `unique_key` when rows can change.
- **Committing `profiles.yml` with secrets.** Use `password: "{{ env_var('DBT_PASSWORD') }}"` and gitignore real creds.
- **Confusing `dbt run` with `dbt build`.** `run` skips tests and seeds; `build` runs the whole graph in order and
  halts downstream on upstream test failure. Prefer `build` in CI.
- **Freshness needs `loaded_at_field`.** A source with no `loaded_at_field` (and no metadata-based freshness on
  supported adapters) can't be freshness-checked — the check is silently skipped.
- **Version drift in docs.** dbt syntax shifts between minors (e.g. `tests:` → `data_tests:`, `freshness` moving under
  `config:`). If a key errors, check `dbt --version` and the docs for that exact minor before assuming the skill is wrong.
