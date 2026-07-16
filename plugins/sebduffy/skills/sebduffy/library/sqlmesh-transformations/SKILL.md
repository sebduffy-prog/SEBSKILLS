---
name: sqlmesh-transformations
category: data-analysis
description: >
  Build in-warehouse SQL transformation pipelines with SQLMesh — the dbt alternative that gives you
  virtual data environments (zero-copy dev vs prod), automatic column-level lineage, breaking vs
  non-breaking change categorization, and automatic incremental backfills. Reach for this when someone
  says "transform tables in Snowflake/BigQuery/DuckDB", "I want dbt but with real dev environments",
  "compute only the changed partitions", "diff prod vs my branch", "categorize breaking changes", or
  "backfill incrementally". Grounded on TobikoData/sqlmesh (Apache-2.0). DuckDB works locally with no keys.
when_to_use:
  - Authoring SQL models (staging → marts) that run in a warehouse: DuckDB, Snowflake, BigQuery, Postgres, Databricks
  - You want isolated dev environments that share prod's physical tables (no full re-run to test a change)
  - Incremental models that process only the new/changed time partitions (@start_ds / @end_ds)
  - You need SQLMesh to auto-classify a change as breaking vs non-breaking and backfill only what's affected
  - Migrating an existing dbt project to SQLMesh, or comparing two environments/tables row-by-row
  - Enforcing data quality with audits (not_null, unique_values, accepted_range) that block bad data
when_not_to_use:
  - Extract/load (getting data INTO the warehouse) — use dlt-python-pipelines
  - You specifically need the dbt ecosystem/Cloud/packages — use dbt-analytics-engineering
  - Ad-hoc local SQL on files with no project/environments — use duckdb-analytics
  - Python-native asset orchestration across many tools — use dagster-asset-pipelines
  - Contract/schema enforcement without a transform engine — use data-contracts or data-quality-validation
keywords: [sqlmesh, tobiko, sql-transformations, elt, virtual-environments, incremental-by-time-range, column-level-lineage, breaking-change, backfill, audits, table-diff, duckdb, snowflake, bigquery, dbt-alternative, model-kinds, plan-apply]
similar_to: [dbt-analytics-engineering, dlt-python-pipelines, duckdb-analytics, dagster-asset-pipelines, data-quality-validation]
inputs_needed: Target engine (duckdb for local/keyless, else snowflake|bigquery|postgres|databricks + credentials), source tables/seeds, and the transform logic + grain (unique key) for each model.
produces: A runnable SQLMesh project (config.yaml + models/) with dev/prod virtual environments, incremental backfills, audits, and env-to-env table diffs.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# SQLMesh Transformations

SQLMesh is an open-source (Apache-2.0) transformation framework — a dbt alternative from Tobiko Data.
Its headline features over hand-rolled SQL or dbt:

- **Virtual data environments** — `plan dev` gives you a full logical copy of prod that *shares the
  same physical tables*. Testing a change costs nothing until the change actually differs. Promotion
  to prod is a metadata swap (a view repoint), not a re-run.
- **Automatic change categorization** — SQLMesh parses your SQL (via SQLGlot), builds column-level
  lineage, and decides whether an edit is **breaking** (backfill this model + downstream), **non-breaking**
  (backfill this model only), or **metadata** (no backfill). You don't tag changes by hand.
- **Incremental backfills by interval** — declare a model `INCREMENTAL_BY_TIME_RANGE` and SQLMesh
  tracks which date intervals have run, computing only the gaps.

## When to use

Use SQLMesh when the data is already in a warehouse and you need to **transform** it into clean,
tested, documented tables — and you want real dev environments + surgical backfills instead of dbt's
"re-run everything to be safe". If you're getting data *into* the warehouse, that's `dlt` (EL), not
this (T). See `when_not_to_use` for the exact sibling for each adjacent job.

## Prerequisites

- Python 3.9+ (`python3` on this Mac is 3.9 — fine). No brew needed.
- `pip install "sqlmesh[web]"` for the CLI + browser UI, or extras per engine:
  `sqlmesh[snowflake]`, `sqlmesh[bigquery]`, `sqlmesh[databricks]`, `sqlmesh[postgres]`.
- **DuckDB needs no credentials** and runs fully local — use it to learn and to build/test skills
  before pointing at a real warehouse. Cloud engines need creds via `{{ env_var('...') }}` in config.

```bash
python3 -m pip install --quiet "sqlmesh[web]"
sqlmesh version                       # confirm install
```

## Recipe 1 — Scaffold a local DuckDB project

`sqlmesh init` writes `config.yaml`, `models/`, `audits/`, `tests/`, `macros/`, `seeds/`.

```bash
mkdir my_pipeline && cd my_pipeline
sqlmesh init duckdb                    # skips prompts, wires a local DuckDB gateway
```

Minimal hand-written `config.yaml` (equivalent to the scaffold):

```yaml
gateways:
  local:
    connection:
      type: duckdb
      database: db.duckdb          # local file; created on first plan
default_gateway: local
model_defaults:
  dialect: duckdb                  # SQL dialect your models are written in
  start: '2024-01-01'             # earliest interval for incrementals
```

Point at a real engine by swapping the connection block (creds via env vars, never hard-coded):

```yaml
gateways:
  snowflake:
    connection:
      type: snowflake
      account: {{ env_var('SNOWFLAKE_ACCOUNT') }}
      user: {{ env_var('SNOWFLAKE_USER') }}
      password: {{ env_var('SNOWFLAKE_PASSWORD') }}
      warehouse: COMPUTE_WH
      database: ANALYTICS
```

## Recipe 2 — Write models (pick the right kind)

Each `.sql` in `models/` starts with a `MODEL(...)` block, then a SELECT. The **kind** decides
materialization strategy — this is the highest-leverage decision:

| Kind | Use for | Backfill behaviour |
|------|---------|--------------------|
| `VIEW` (default) | Thin passthrough / renames | Rebuilt as a view, no data cost |
| `FULL` | Small aggregates, no time dimension | Rewrites the whole table each run |
| `INCREMENTAL_BY_TIME_RANGE` | Event/fact tables partitioned by date | Computes only missing intervals |
| `INCREMENTAL_BY_UNIQUE_KEY` | Upsert/merge on a key | Insert new keys, update matched |
| `SCD_TYPE_2_BY_TIME` / `_BY_COLUMN` | Slowly-changing dimensions | Tracks valid_from / valid_to history |
| `SEED` | Static CSV loaded from `seeds/` | Loaded once until the file changes |

Incremental fact table (the common workhorse). The `WHERE` on the time column + `@start_ds`/`@end_ds`
macros is **required** — it's how SQLMesh bounds each interval:

```sql
-- models/marts/fct_orders.sql
MODEL (
  name analytics.fct_orders,
  kind INCREMENTAL_BY_TIME_RANGE (
    time_column order_date
  ),
  start '2024-01-01',
  cron '@daily',
  grain order_id,                      -- unique key: powers table_diff + audits
  audits (
    not_null(columns := (order_id, order_date)),
    accepted_range(column := amount, min_v := 0)
  )
);

SELECT
  order_id,
  order_date,
  customer_id,
  amount
FROM raw.orders
WHERE order_date BETWEEN @start_ds AND @end_ds;
```

Interval macros: `@start_ds`/`@end_ds` (date strings), `@start_dt`/`@end_dt` (timestamps), plus
`@start_ts`/`@end_ts` and epoch variants.

## Recipe 3 — Plan & apply (the core loop)

`plan` diffs your local code against a target environment, categorizes each change, and prompts before
backfilling. `run` executes scheduled/missed intervals afterward (what a cron/orchestrator calls).

```bash
# First deploy to prod (empty env → everything is "new")
sqlmesh plan                          # review, then answer y to "Apply - Backfill Tables"

# Iterate safely in an isolated virtual env sharing prod's tables:
sqlmesh plan dev                      # builds/updates the `dev` environment only
sqlmesh plan dev --start 2024-06-01 --end 2024-06-07   # cheap: backfill a narrow window in dev

# Preview WITHOUT applying:
sqlmesh plan dev --explain            # show exactly what it would backfill/change

# Promote validated dev → prod (usually a no-cost virtual update if data already built):
sqlmesh plan                          # prod plan reuses dev-built intervals where possible

# Run missing intervals for an environment (schedule this):
sqlmesh run                           # prod
sqlmesh run dev --start 2024-06-01 --end 2024-06-07
```

Query results per environment — dev tables get a `__dev` schema suffix:

```bash
sqlmesh fetchdf "select count(*) from analytics.fct_orders"          # prod
sqlmesh fetchdf "select count(*) from analytics__dev.fct_orders"     # dev
```

### Change categories (SQLMesh decides, you confirm)
- **Breaking** — logic/WHERE change with downstream impact → backfills the model **and** dependents.
- **Non-breaking** — additive (new column) → backfills the model only; dependents skip unless `SELECT *`.
- **Metadata** — comment/owner/audit-only edits → no backfill.
- **`--forward-only`** — reuse existing physical tables, no historical backfill (cheap schema change;
  new logic applies going forward). Use for huge tables where a full rebuild is prohibitive.

## Recipe 4 — Audits & unit tests

**Audits** run automatically after each model build and **block** the pipeline if they return rows.
Reference built-ins inline (Recipe 2) or write a custom audit in `audits/`:

```sql
-- audits/assert_positive_amount.sql
AUDIT (name assert_positive_amount);
SELECT * FROM @this_model WHERE amount < 0;
```

Built-ins include `not_null`, `unique_values`, `accepted_values`, `accepted_range`, `number_of_rows`,
`valid_email`, `valid_uuid`, `match_regex_pattern_list`, `mean_in_range`, `z_score`. Every one has a
`_non_blocking` variant (warn instead of halt). Run on demand: `sqlmesh audit --model analytics.fct_orders`.

**Unit tests** assert model *logic* on fixed inputs (YAML fixtures in `tests/`), run in dev before deploy:

```bash
sqlmesh create_test analytics.fct_orders \
  --query raw.orders "select * from raw.orders limit 5"   # auto-generate a fixture from live data
sqlmesh test                          # run all; exits non-zero on failure (CI gate)
sqlmesh test -k fct_orders -v         # filter + verbose
```

## Recipe 5 — Column-level lineage & environment diffs

```bash
sqlmesh ui                            # browser IDE at http://127.0.0.1:8000 with interactive lineage
sqlmesh dag lineage.html              # write the model DAG to an HTML file
sqlmesh render analytics.fct_orders   # show the fully-expanded SQL SQLMesh actually runs
```

**table_diff** is SQLMesh's killer QA tool — compare the same model across two environments (or two
tables) row-by-row on the grain, before promoting:

```bash
# Compare prod vs dev for one model (grain from the MODEL block):
sqlmesh table_diff prod:dev analytics.fct_orders

# Explicit join key + show differing rows:
sqlmesh table_diff prod:dev analytics.fct_orders -o order_id --show-sample

# Arbitrary two tables:
sqlmesh table_diff prod:dev 'db.schema.a:db.schema.b' -o id
```

It reports schema diffs, row-count diffs, and per-column value drift — so you *know* a change is safe
before it hits prod.

**Migrating from dbt:** `sqlmesh init` with the `dbt` project type reads an existing dbt project in
place (`dbt_project.yml`, `models/`, `seeds/`, sources), maps materializations to SQLMesh kinds, keeps
your `{{ ref() }}`/Jinja, and adds virtual environments + auto-categorization. Then `sqlmesh plan`.

## Verify

```bash
sqlmesh version                                   # CLI installed
cd my_pipeline && sqlmesh plan --explain          # config parses, models compile, no apply
sqlmesh test                                       # unit tests pass (exit 0)
sqlmesh audit                                      # audits pass
sqlmesh table_diff prod:dev analytics.fct_orders  # dev matches prod (empty diff) after promotion
```

A green `plan --explain` + passing `test`/`audit` means the project is wired correctly.

## Pitfalls

- **Incremental models MUST filter the time column with `@start_ds`/`@end_ds`.** Omit it and every
  interval reprocesses the whole source — silently expensive and often wrong. SQLMesh warns, don't ignore it.
- **`plan` categorizes; `run` executes scheduled intervals.** They're not interchangeable. Your
  cron/orchestrator calls `sqlmesh run <env>`; humans call `sqlmesh plan` when code changed.
- **Prod `plan` rejects `--start`/`--end`.** To reprocess a prod window use
  `sqlmesh plan --restate-model analytics.fct_orders --start 2024-06-01 --end 2024-06-07` (restatement).
- **Set a `grain`** on every model. Without it `table_diff` can't join and audits like `unique_values`
  have nothing to key on; SQLMesh will `--warn-grain-check` instead of validating.
- **`--forward-only` skips history.** Great for giant tables, but past data won't reflect the new logic
  unless you also restate. Understand the tradeoff before choosing it.
- **Env var interpolation is `{{ env_var('NAME') }}` in `config.yaml`** — never paste secrets inline.
  Export the vars in your shell/CI before `sqlmesh plan`.
- **dev schema suffix is `__<env>`** (e.g. `analytics__dev.fct_orders`). Querying the unsuffixed name
  hits prod — a common "why is my change not showing" confusion.
