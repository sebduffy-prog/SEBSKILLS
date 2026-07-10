---
name: dlt-python-pipelines
category: data-analysis
description: >
  Build declarative extract-and-load pipelines in pure Python with dlt (dlthub) — pull from REST APIs,
  SQL databases, or files and land them in DuckDB, BigQuery, Snowflake, Postgres, or Parquet with
  automatic schema inference AND evolution, incremental cursor loads, merge/upsert, and persisted state.
  Reach for this whenever someone says "I need to load this API/DB into a warehouse", "sync incrementally",
  "handle schema changes automatically", or "EL without Airbyte/Fivetran". Grounded on dlt-hub/dlt.
when_to_use:
  - Extracting from a REST API (paginated/authed) and loading to a warehouse or DuckDB
  - Replicating a source SQL database (Postgres/MySQL) into an analytics store
  - Incremental syncs that only pull rows changed since the last run (cursor + state)
  - Nested JSON that needs to be flattened into normalized relational tables automatically
  - Merge/upsert (dedup on primary key) or append-only ingestion into a destination
when_not_to_use:
  - In-warehouse SQL transforms (T of ELT) — use dbt-analytics-engineering or sqlmesh-transformations
  - Ad-hoc local DataFrame munging with no destination — use polars-dataframes or duckdb-analytics
  - Web scraping / HTML extraction — use firecrawl-scrape or structured-page-extraction
  - Cataloguing which public APIs exist — use free-api-catalogue
  - Orchestration/scheduling of many assets — use dagster-asset-pipelines (wrap dlt inside it)
keywords: [dlt, dlthub, elt, extract-load, incremental-loading, schema-evolution, rest-api-source, sql-database, duckdb, merge-upsert, pipeline-state, data-ingestion, warehouse-load, cursor, write-disposition]
similar_to: [duckdb-analytics, dbt-analytics-engineering, sqlmesh-transformations, incremental-content-index, dagster-asset-pipelines]
inputs_needed: Source type (REST API URL + auth / SQL connection string / file glob), destination (duckdb|bigquery|snowflake|postgres|filesystem), and load mode (append|replace|merge + primary key / cursor field for incremental).
produces: A runnable Python dlt pipeline that lands normalized, schema-evolved tables in the chosen destination, with incremental state persisted between runs.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# dlt Python Pipelines

`dlt` (data load tool, from dlthub) is a lightweight, pip-installable Python library for the **EL** of
ELT. You write a source that `yield`s dicts; dlt infers a schema, normalizes nested JSON into relational
tables, evolves the schema when fields change, and loads to your destination — tracking incremental
state so reruns only fetch new data. No servers, no UI, no YAML-heavy config.

## When to use

Use dlt when you need data *moved* from a source into a store, reliably and repeatedly, without
hand-rolling pagination, schema DDL, and state files. It shines for REST APIs, SQL replication, and
messy nested JSON. It does NOT transform data in-warehouse — pair it with dbt or SQLMesh for that.

## Prerequisites

- **Python 3.9+** (macOS system `python3` is fine). Install into a venv:
  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  pip install "dlt[duckdb]"            # destination extra picks deps
  # other extras: dlt[bigquery] dlt[snowflake] dlt[postgres] dlt[filesystem] dlt[parquet]
  pip install "dlt[sql_database]"      # for DB sources (adds SQLAlchemy)
  ```
- **Secrets** live in `.dlt/secrets.toml` (git-ignored) or env vars. dlt reads `dlt.secrets["key"]`
  and `dlt.secrets.value` from there. Env form: `DESTINATION__BIGQUERY__CREDENTIALS__...` or
  `SOURCES__<name>__<field>`. Never hardcode tokens in the .py file.
- DuckDB needs nothing extra; it writes a local `*.duckdb` file next to the script.

Verify the install: `python3 -c "import dlt; print(dlt.version.__version__)"`.

## Recipes

### 1. Bare-minimum pipeline (any Python iterable → DuckDB)

```python
import dlt

@dlt.resource(table_name="issues", write_disposition="replace")
def issues():
    for i in range(100):
        yield {"id": i, "title": f"Item {i}", "labels": [{"name": "bug"}]}  # nested list is auto-normalized

pipeline = dlt.pipeline(pipeline_name="demo", destination="duckdb", dataset_name="raw")
info = pipeline.run(issues)
print(info)                                  # tables created, rows loaded
print(pipeline.dataset().issues.df().head()) # read it back as a DataFrame
```

dlt creates `issues` AND a child table `issues__labels` (the nested list), linked by `_dlt_id`.

### 2. REST API source (paginated + authed + incremental)

The declarative `rest_api_source` handles pagination and per-endpoint incremental cursors:

```python
import dlt
from dlt.sources.rest_api import rest_api_source

source = rest_api_source({
    "client": {
        "base_url": "https://api.github.com/",
        "auth": {"type": "bearer", "token": dlt.secrets["github_token"]},
        "paginator": {"type": "header_link"},          # follows RFC5988 Link headers
    },
    "resource_defaults": {"write_disposition": "merge", "primary_key": "id"},
    "resources": [
        {
            "name": "issues",
            "endpoint": {
                "path": "repos/dlt-hub/dlt/issues",
                "params": {
                    "state": "all",
                    "since": {                          # incremental: only rows updated since last run
                        "type": "incremental",
                        "cursor_path": "updated_at",
                        "initial_value": "2024-01-01T00:00:00Z",
                    },
                },
            },
        },
    ],
})

pipeline = dlt.pipeline("github", destination="duckdb", dataset_name="github_data")
print(pipeline.run(source))
```

Paginator `type` options include `json_link` (`next_url_path`), `header_link`, `offset`
(`limit`/`offset`/`total_path`), `page_number`, and `cursor`. Auth `type`: `bearer`, `api_key`,
`http_basic`. On the second run only issues with a newer `updated_at` are fetched — state is persisted.

### 3. Custom resource with `dlt.sources.incremental`

When you write the extractor yourself, declare the cursor as a parameter:

```python
import dlt

@dlt.resource(primary_key="id", write_disposition="merge")
def orders(
    cursor=dlt.sources.incremental("updated_at", initial_value="1970-01-01T00:00:00Z"),
):
    # cursor.last_value = high-water mark from the previous run (or initial_value on first run)
    for row in fetch_orders(since=cursor.last_value):
        yield row

# last_value_func defaults to max; use min for descending sources:
# dlt.sources.incremental("seq", last_value_func=min)
```

Access `cursor.start_value` (run start) and `cursor.last_value` (moves as you yield). dlt stores the
final `last_value` in pipeline state so the next run resumes there.

### 4. SQL database → warehouse

```python
import dlt
from dlt.sources.sql_database import sql_database

source = sql_database(
    "postgresql://user:pass@host:5432/prod",   # or put creds in secrets.toml
    table_names=["customers", "orders"],
)
# incremental on one table:
source.orders.apply_hints(incremental=dlt.sources.incremental("updated_at"))

pipeline = dlt.pipeline("pg_replica", destination="duckdb", dataset_name="replica")
print(pipeline.run(source, write_disposition="merge"))
```

`sql_table("...", table="orders")` loads a single table. Reflection auto-maps column types.

### 5. Files → tables (filesystem / bucket)

```python
import dlt
from dlt.sources.filesystem import readers

reader = readers(bucket_url="file:///data/dumps", file_glob="*.jsonl").read_jsonl()
pipeline = dlt.pipeline("files", destination="duckdb", dataset_name="staged")
print(pipeline.run(reader.with_name("events")))
# also: .read_csv(), .read_parquet(); bucket_url supports s3://, gs://, az://
```

## Write dispositions (pick per resource)

- `append` — add all yielded rows; never dedups. Good for immutable event logs.
- `replace` — truncate + reload the whole table each run. Good for small dimension pulls.
- `merge` — upsert on `primary_key` (dedup, keeps latest); or use `merge_key` for delete-insert on a
  partition. This is the go-to for incremental syncs of mutable records.

Set on the decorator (`@dlt.resource(write_disposition="merge", primary_key="id")`), in
`resource_defaults`, or at `pipeline.run(..., write_disposition=...)`.

## Verify

```bash
# 1) Did it load? Inspect the pipeline (schema, last load, row counts):
dlt pipeline <pipeline_name> info
dlt pipeline <pipeline_name> show      # opens a Streamlit browser (optional)

# 2) Query the data directly (DuckDB destination):
python3 -c "import duckdb; print(duckdb.connect('demo.duckdb').sql('SELECT count(*) FROM raw.issues'))"

# 3) Confirm incrementality: run twice, second run should load ~0 new rows.
```

`load_info` from `pipeline.run()` raises on failed jobs; call `load_info.raise_on_failed_jobs()`
to fail loudly in scripts/CI. Every dlt table also gets `_dlt_load_id` and `_dlt_id` audit columns.

## Pitfalls

- **Schema contracts**: by default dlt *evolves* the schema (new columns just appear). For strict
  pipelines set `@dlt.resource(schema_contract={"columns": "freeze"})` to reject unexpected fields
  instead of silently widening the table.
- **Merge needs a key**: `write_disposition="merge"` without `primary_key`/`merge_key` degrades to
  append-like behavior. Always declare the key.
- **Incremental cursor must be monotonic** and present on every row. Mixed timezones or nullable
  cursor fields break the high-water mark — normalize to UTC ISO8601 first.
- **State is keyed by `pipeline_name` + working dir**. Reusing a name across unrelated pipelines
  corrupts incremental state; give each pipeline a unique, stable name.
- **`dataset_name` = schema/dataset** in the destination, not the table. Tables come from
  `table_name`/resource name.
- **Secrets precedence**: env vars > `.dlt/secrets.toml`. A stale env var silently overrides your
  toml — check with `dlt pipeline <name> info` if auth mysteriously fails.
- **macOS py3.9**: install the destination extra (`dlt[duckdb]`) not bare `dlt`, or the loader deps
  are missing at run time. Full refresh: `pipeline.run(source, refresh="drop_sources")`.
- **Don't transform here.** dlt lands raw normalized data; do business logic downstream in dbt/SQLMesh.

## References

- Docs: https://dlthub.com/docs — REST API source, incremental loading, destinations.
- Repo: https://github.com/dlt-hub/dlt (Apache-2.0). `dlt init <source> <destination>` scaffolds a project.
