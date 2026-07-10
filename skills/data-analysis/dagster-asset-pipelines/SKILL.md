---
name: dagster-asset-pipelines
category: data-analysis
description: >-
  Build software-defined asset (SDA) pipelines with Dagster — a typed, lineage-aware dependency graph where
  each node is a data asset (a table, file, or model) rather than an opaque task. Reach for this when someone
  says "orchestrate my pipeline", "I need asset lineage / a data DAG", "schedule and backfill this", "add
  freshness / data-quality checks with alerts", "partition by day", "event-driven sensor", or "wrap my
  dbt/dlt/Polars steps in an orchestrator". Grounds every import, decorator, and CLI command against the real
  dagster 1.12.x API (`import dagster as dg`, `@dg.asset`, `Definitions`, `dagster dev`) — no fabricated flags.
when_to_use:
  - Turning a chain of extract/transform/load steps into a lineage-tracked asset graph you can see in a UI
  - Scheduling, backfilling, and partitioning materializations (daily/hourly/static partitions)
  - Event-driven runs — trigger on a new file, an upstream materialization, or an external signal (sensors)
  - Adding asset checks (row counts, null/freshness/schema assertions) that gate or alert on bad data
  - Orchestrating dbt, dlt, or Polars steps together with shared resources and IO managers
when_not_to_use:
  - Pure in-warehouse SQL transforms with no orchestration → dbt-analytics-engineering or sqlmesh-transformations
  - Just moving data source→destination (EL) with no DAG/UI → dlt-python-pipelines
  - Local DataFrame munging with no scheduling/lineage → polars-dataframes or duckdb-analytics
  - Only validating a dataset once, no pipeline → data-quality-validation
  - Cataloguing which public APIs exist → free-api-catalogue
keywords: [dagster, software-defined-assets, asset-graph, data-orchestration, lineage, partitions, schedules, sensors, asset-checks, io-manager, backfill, dbt-integration, dlt-integration, polars, materialization, definitions, dag]
similar_to: [dlt-python-pipelines, dbt-analytics-engineering, sqlmesh-transformations, data-quality-validation, incremental-content-index]
inputs_needed: The pipeline steps and their dependencies (what produces what), each step's tool (Python/Polars/dbt/dlt/SQL), the destination/IO (DuckDB, Parquet, warehouse), and any scheduling need (cron, partition scheme, or trigger event).
produces: A runnable Dagster project (assets + Definitions) that renders a lineage graph in the UI at localhost:3000, materializes on schedule/sensor, and gates on asset checks.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Dagster Asset Pipelines

Dagster orchestrates **software-defined assets**: you declare each persistent object your pipeline
produces (a table, file, ML model) as a Python function, and Dagster infers the dependency graph from
the function arguments. The graph is typed, observable in a web UI, schedulable, partitionable, and
checkable — unlike task-based orchestrators (Airflow) where the *task* is the unit and its data output
is invisible. Think in outputs, not steps.

## When to use

Use Dagster when you have **more than one data step with dependencies** and you want lineage, a UI,
scheduling/backfills, and data-quality gates in one place. For a single EL move use `dlt`; for pure
in-warehouse SQL use `dbt`/SQLMesh — then *wrap those inside Dagster* to orchestrate them together.
Don't reach for Dagster just to run one script on a cron.

## Prerequisites

- **Python 3.9+** in a venv (macOS system `python3` works):
  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  pip install dagster dagster-webserver          # core + the UI server
  # integration extras, add only what you use:
  pip install dagster-dbt dagster-dlt dagster-polars dagster-duckdb pandas
  ```
- `dagster-webserver` is what powers `dagster dev`; without it the UI won't launch.
- Verify: `python3 -c "import dagster as dg; print(dg.__version__)"` (expect 1.12.x+).
- **Two ways to define a project.** The classic, most portable form is a single module exporting a
  `Definitions` object, launched with `dagster dev -f defs.py`. The newer `create-dagster`/`dg` CLI
  scaffolds a package layout (`uvx create-dagster@latest project my_proj`, then `dg dev`). Recipes below
  use the classic form (runs anywhere with just `pip`) — port to `dg` when a team wants scaffolding.

## Recipes

Everything below lives in one file `defs.py` unless noted. `import dagster as dg` is the current idiom.

### 1. A minimal two-asset graph

Dependencies come from **argument names matching upstream asset names** — no manual wiring.

```python
import dagster as dg
import pandas as pd

@dg.asset
def raw_users() -> pd.DataFrame:
    return pd.DataFrame({"id": [1, 2, 3], "country": ["GB", "US", "GB"]})

@dg.asset
def uk_users(raw_users: pd.DataFrame) -> pd.DataFrame:   # depends on raw_users
    return raw_users[raw_users.country == "GB"]

defs = dg.Definitions(assets=[raw_users, uk_users])
```

Materialize: `dagster dev -f defs.py` → localhost:3000 → "Materialize all". Or `dagster asset materialize -f defs.py --select '*'`.

### 2. Metadata + logging via the execution context

Ask for `context: dg.AssetExecutionContext` and return a `MaterializeResult` to attach UI metadata.

```python
@dg.asset
def enriched(context: dg.AssetExecutionContext, uk_users: pd.DataFrame) -> dg.MaterializeResult:
    df = uk_users.assign(is_uk=True)
    context.log.info(f"enriched {len(df)} rows")
    return dg.MaterializeResult(
        metadata={
            "num_records": dg.MetadataValue.int(len(df)),
            "preview": dg.MetadataValue.md(df.head().to_markdown()),
        }
    )
```

### 3. Resources (share DB clients, configs) instead of globals

Resources are injected by name and configured once in `Definitions` — secrets/connections stay out of asset bodies.

```python
from dagster_duckdb import DuckDBResource

@dg.asset
def stored(context: dg.AssetExecutionContext, uk_users: pd.DataFrame, duckdb: DuckDBResource):
    with duckdb.get_connection() as conn:
        conn.execute("CREATE OR REPLACE TABLE uk_users AS SELECT * FROM uk_users_df",
                     {"uk_users_df": uk_users})  # duckdb reads the local df var

defs = dg.Definitions(
    assets=[raw_users, uk_users, stored],
    resources={"duckdb": DuckDBResource(database="analytics.duckdb")},
)
```

### 4. Asset checks — gate on data quality

Checks run with an asset, surface pass/fail in the UI, and can gate downstream or trigger alerts.

```python
@dg.asset_check(asset=uk_users)
def uk_users_non_empty(uk_users: pd.DataFrame) -> dg.AssetCheckResult:
    n = len(uk_users)
    return dg.AssetCheckResult(
        passed=n > 0,
        severity=dg.AssetCheckSeverity.ERROR,   # or WARN
        metadata={"row_count": n},
    )
```

Add it: `dg.Definitions(assets=[...], asset_checks=[uk_users_non_empty])`.

### 5. Partitions — one asset, many time slices

Materialize and backfill per day/hour/key; `context.partition_key` gives the slice.

```python
daily = dg.DailyPartitionsDefinition(start_date="2026-01-01")

@dg.asset(partitions_def=daily)
def events(context: dg.AssetExecutionContext) -> pd.DataFrame:
    day = context.partition_key                    # e.g. "2026-07-09"
    return fetch_events_for(day)                    # your loader
```

Backfill from the UI (Assets → Backfill) or `... --select events --partition 2026-07-09`. Static keys: `dg.StaticPartitionsDefinition(["GB", "US"])`.

### 6. Jobs + schedules — run on a cron

A job selects a slice of the graph; a schedule fires it on cron. Selection strings support `+` (up/downstream).

```python
daily_job = dg.define_asset_job("daily_job", selection="raw_users+")  # raw_users and all downstream

daily_schedule = dg.ScheduleDefinition(
    job=daily_job,
    cron_schedule="0 6 * * *",          # 06:00 daily
    default_status=dg.DefaultScheduleStatus.RUNNING,
)

defs = dg.Definitions(assets=[...], jobs=[daily_job], schedules=[daily_schedule])
```

Schedules only tick while `dagster dev` (or the daemon) runs — confirm it in the UI's Daemons tab.

### 7. Sensors — event-driven runs

Sensors poll for a condition and launch runs. Return `RunRequest` to fire, `SkipReason` to no-op, and persist a cursor so you don't reprocess.

```python
@dg.sensor(job=daily_job, minimum_interval_seconds=30)
def new_file_sensor(context: dg.SensorEvaluationContext):
    import os, glob
    seen = context.cursor or ""
    newest = max(glob.glob("inbox/*.csv"), default=None, key=os.path.getmtime)
    if newest and newest > seen:
        yield dg.RunRequest(run_key=newest)
        context.update_cursor(newest)
    else:
        yield dg.SkipReason("no new file")
```

Prefer `@dg.asset_sensor(asset_key=dg.AssetKey("raw_users"), ...)` to trigger when a *specific upstream
asset* materializes, rather than reinventing polling.

### 8. Wrap dbt (dagster-dbt)

Loads every dbt model as a Dagster asset from the manifest, merging dbt lineage into the graph.

```python
from pathlib import Path
from dagster_dbt import DbtProject, DbtCliResource, dbt_assets

dbt_project = DbtProject(project_dir=Path(__file__).parent / "my_dbt")
dbt_project.prepare_if_dev()                     # compiles manifest in dev

@dbt_assets(manifest=dbt_project.manifest_path)
def dbt_models(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()

defs = dg.Definitions(assets=[dbt_models], resources={"dbt": DbtCliResource(project_dir=dbt_project)})
```
For prod, build the manifest at deploy time with `dagster-dbt project prepare-and-package`.

### 9. Wrap dlt (dagster-dlt) and Polars (dagster-polars)

```python
from dagster_dlt import DagsterDltResource, dlt_assets

@dlt_assets(dlt_source=my_source(), dlt_pipeline=my_pipeline)   # your dlt objects
def ingested(context: dg.AssetExecutionContext, dlt: DagsterDltResource):
    yield from dlt.run(context=context)
```

For Polars, return a `polars.DataFrame` and set the Polars IO manager to persist it to Parquet automatically:

```python
from dagster_polars import PolarsParquetIOManager
import polars as pl

@dg.asset
def scores() -> pl.DataFrame:
    return pl.DataFrame({"id": [1, 2], "score": [0.9, 0.4]})

defs = dg.Definitions(assets=[scores],
    resources={"io_manager": PolarsParquetIOManager(base_dir="data")})
```

## Verify

- **Definitions load:** `dagster definitions validate -f defs.py` (or `dg check defs`).
- **Graph renders:** `dagster dev -f defs.py` → localhost:3000, confirm every asset and edge.
- **End-to-end:** `dagster asset materialize -f defs.py --select '*'` exits 0 and checks pass.
- **Automation live:** UI → Automation tab shows the schedule/sensor RUNNING and the daemon healthy.

## Pitfalls

- **UI won't start / `No module named dagster_webserver`:** you installed `dagster` but not
  `dagster-webserver`; `dagster dev` needs both.
- **Dependencies not detected:** an asset depends on another *only* when the parameter name equals the
  upstream asset's name (or you pass `deps=[...]`/`ins={...}` explicitly). Misspelling the arg drops the edge.
- **Schedules/sensors never fire:** they only tick while the **daemon** runs. `dagster dev` starts it;
  a bare `dagster asset materialize` does not. In prod run `dagster-daemon run` beside the webserver.
- **Return type must match the IO manager.** The default IO manager pickles return values; with
  `PolarsParquetIOManager`/`DuckDBIOManager` an asset must return the DataFrame it expects, not a
  `MaterializeResult` (which stores nothing). One pattern per asset.
- **dbt manifest missing:** `@dbt_assets` needs a compiled `manifest.json` — call
  `dbt_project.prepare_if_dev()` in dev or `prepare-and-package` in CI; don't hand-edit it.
- **Partitioned backfills are per-slice:** a range backfill launches one run per partition (a slow loader
  × 365 days = 365 runs). Test one partition first, then backfill the range.
- **Secrets:** source connection strings from env (`DuckDBResource(database=dg.EnvVar("DB_PATH"))`),
  never hardcoded in the asset body.
