---
name: duckdb-analytics
category: data-analysis
description: >
  Run fast in-process analytical SQL over Parquet/CSV/JSON/Arrow — directly on local files, globs, S3, or HTTPS — with zero server setup and larger-than-RAM query support. Use when the user wants to query, join, aggregate, or profile columnar/tabular files with SQL; convert CSV→Parquet; slice a 50GB dataset on a laptop; read remote Parquet without downloading it; or hand a Pandas/Polars frame to SQL and back. Triggers on "query this parquet/csv", "SQL on files", "DuckDB", "join two CSVs", "read parquet from S3", "too big for pandas", "count rows in a folder of files".
when_to_use:
  - User wants to run SQL over one or many local files (Parquet/CSV/JSON) without loading a database
  - User has a dataset too large for Pandas/Polars RAM and needs streaming/spill-to-disk aggregation
  - User wants to query remote Parquet/CSV over HTTPS or S3 without downloading the whole file
  - User wants to convert or repartition CSV/JSON into Parquet, or export a query result to a file
  - User wants to join/aggregate across a glob of files (a folder of daily exports) in one query
  - User wants SQL over an existing Pandas/Polars/Arrow frame and the result back as a frame
when_not_to_use:
  - User wants dataframe-style method chaining (.filter/.groupby) not SQL → use polars-dataframes
  - User wants a persistent multi-writer OLTP database / concurrent web-app backend → use Postgres/SQLite
  - User wants a versioned lakehouse with snapshots and schema evolution over DuckDB → use ducklake-lakehouse
  - User wants managed dbt/SQLMesh transformation modelling and DAGs → use dbt-analytics-engineering or sqlmesh-transformations
  - User only needs quick summary stats on a small frame already in memory → use exploratory-data-analysis
keywords:
  - duckdb
  - sql
  - parquet
  - csv
  - analytics
  - olap
  - in-process
  - larger-than-ram
  - s3
  - httpfs
  - arrow
  - columnar
  - glob
  - copy
  - read_parquet
similar_to:
  - polars-dataframes
  - ducklake-lakehouse
  - parquet-arrow-optimization
  - exploratory-data-analysis
  - dbt-analytics-engineering
inputs_needed:
  - Path(s) or glob to the data (local, s3://, or https://), or an in-memory frame variable
  - The question as SQL or plain English (columns to select/filter/group/join)
  - Output target — print, a DataFrame, or a written file (and format: Parquet/CSV/JSON)
  - For S3/private buckets — a credential source (env AWS keys, profile, or explicit keys)
produces: SQL query results as printed tables, a Pandas/Polars/Arrow DataFrame, or a written Parquet/CSV/JSON file — computed in-process over local or remote files.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# DuckDB Analytics

DuckDB is an in-process analytical (OLAP) SQL engine — "SQLite for analytics". No server, no daemon, one dependency. It reads Parquet/CSV/JSON/Arrow **directly off disk, globs, HTTPS, and S3**, runs a vectorised columnar engine, and spills to disk so you can aggregate datasets far larger than RAM on a laptop. Latest stable is **1.5.x** (LTS **1.4.x**); this skill targets 1.x syntax.

## When to use

Reach for DuckDB whenever the task is "SQL over files" or "this is too big for Pandas". It is the fastest zero-setup path to: joining a folder of CSVs, querying a remote Parquet without downloading it, converting formats, or profiling a multi-GB export. If the user wants method-chaining instead of SQL, prefer `polars-dataframes` — the two interoperate freely (DuckDB queries a Polars frame and vice-versa).

## Prerequisites

Nothing pre-installed here. Pick one:

```bash
# Python (needs 3.9+; this Mac has 3.9 — OK). No compiler needed, wheels are prebuilt.
python3 -m pip install --user duckdb

# Standalone CLI (official installer; installs to ~/.duckdb/cli/latest/duckdb):
curl https://install.duckdb.org | sh
export PATH="$HOME/.duckdb/cli/latest:$PATH"
duckdb --version
```

The Python package bundles everything; the CLI is a single self-contained binary. Remote access (`httpfs`, S3) is an extension DuckDB **auto-installs and auto-loads on first use** — no manual step in modern versions. No brew required.

## Recipes

Everything below is real, runnable 1.x syntax. In DuckDB you almost never `CREATE TABLE` first — you query the file path directly as if it were a table.

### 1. Query a file directly (no import)

```python
import duckdb
# One-shot, in-memory connection. Returns a Python object; pick your materialiser.
duckdb.sql("SELECT * FROM 'data.parquet' LIMIT 5").show()          # pretty-print
df   = duckdb.sql("SELECT * FROM 'data.csv'").df()                  # -> pandas
pl   = duckdb.sql("SELECT * FROM 'data.parquet'").pl()             # -> polars
arr  = duckdb.sql("SELECT * FROM read_json_auto('x.json')").arrow()# -> pyarrow
rows = duckdb.sql("SELECT count(*) FROM 'data.parquet'").fetchall()
```

CLI equivalent (great for a quick look):

```bash
duckdb -c "SELECT count(*) FROM 'data.parquet'"
duckdb -c "DESCRIBE SELECT * FROM 'data.csv'"          # infer & show schema
duckdb -c "SUMMARIZE SELECT * FROM 'data.parquet'"     # per-column stats profile
```

The bare-string form uses the replacement scan. To be explicit or pass options, use the table functions: `read_parquet(...)`, `read_csv(...)`/`read_csv_auto(...)`, `read_json_auto(...)`.

### 2. Glob a folder of files + get the source path

```sql
-- One query over every daily export; Hive-style dirs become columns.
SELECT * FROM read_parquet('exports/**/*.parquet', hive_partitioning = true);

-- Bring the filename in as a column so you know which file a row came from.
SELECT filename, * FROM read_csv('logs/2026-*.csv', filename = true);

-- Union files with slightly different columns by name, not position.
SELECT * FROM read_parquet('year=*/*.parquet', union_by_name = true);
```

### 3. Read remote data without downloading it

```sql
-- HTTPS: DuckDB range-reads only the Parquet row groups it needs.
SELECT region, sum(amount)
FROM 'https://blobs.duckdb.org/data/sales.parquet'
GROUP BY region;
```

For **S3**, register a secret once (config or auto-discover chain), then use `s3://` paths:

```sql
-- Explicit keys:
CREATE SECRET s3 (
    TYPE s3,
    KEY_ID    'AKIA...',
    SECRET    '...',
    REGION    'eu-west-2'
);
-- OR discover from env/profile/instance role (recommended, no secrets in SQL):
CREATE SECRET s3 ( TYPE s3, PROVIDER credential_chain );

SELECT * FROM 's3://my-bucket/prefix/**/*.parquet' LIMIT 100;
```

### 4. Handle messy CSVs

`read_csv_auto` sniffs delimiter, header, and types. Override when the sniffer is wrong:

```sql
SELECT * FROM read_csv('weird.csv',
    delim      = ';',
    header     = true,
    columns    = {'id': 'INTEGER', 'ts': 'TIMESTAMP', 'note': 'VARCHAR'},
    ignore_errors = true,          -- skip unparseable rows instead of aborting
    sample_size   = -1);           -- scan the whole file before deciding types
```

### 5. Convert / export with COPY

```sql
-- CSV -> compressed, partitioned Parquet (fast to re-query later):
COPY (SELECT * FROM 'big.csv')
  TO 'out' (FORMAT parquet, COMPRESSION zstd,
            PARTITION_BY (region), OVERWRITE_OR_IGNORE);

-- Query result -> single Parquet / CSV / JSON file:
COPY (SELECT region, sum(amount) AS total FROM 'sales.parquet' GROUP BY region)
  TO 'summary.parquet' (FORMAT parquet);
COPY (SELECT * FROM t) TO 'out.csv'  (HEADER, DELIMITER ',');
COPY (SELECT * FROM t) TO 'out.json' (FORMAT json, ARRAY true);
```

### 6. SQL over an in-memory frame (and back)

```python
import duckdb, pandas as pd, polars as pl
sales = pd.read_csv("sales.csv")          # any pandas/polars/arrow frame
# The frame is visible by its VARIABLE NAME inside the SQL — no registration needed.
out = duckdb.sql("""
    SELECT region, sum(amount) AS total
    FROM sales
    WHERE amount > 0
    GROUP BY region
    ORDER BY total DESC
""").pl()                                 # result straight to Polars
```

### 7. Larger-than-RAM: persist + tune

For big jobs, use a **file-backed** database (so intermediates can live on disk) and raise limits:

```python
con = duckdb.connect("work.duckdb")       # on-disk db, not :memory:
con.sql("SET memory_limit = '8GB'")       # cap RAM; excess spills to temp_directory
con.sql("SET threads = 8")
con.sql("SET temp_directory = '/tmp/duck.tmp'")     # where spill files go
con.sql("SET max_temp_directory_size = '200GB'")    # allow big spills
con.sql("SET preserve_insertion_order = false")     # lower memory on big sorts/exports
con.sql("COPY (SELECT ... huge aggregation ...) TO 'result.parquet' (FORMAT parquet)")
```

DuckDB streams and spills group-bys, joins, and sorts, so a 50GB aggregation completes on a 16GB laptop — just give it a `temp_directory` with room.

## Verify

Smoke-test the whole path end to end (no external data needed):

```bash
python3 - <<'PY'
import duckdb
duckdb.sql("COPY (SELECT i AS id, i%3 AS grp, i*1.5 AS amt "
           "FROM range(1000) t(i)) TO 'smoke.parquet' (FORMAT parquet)")
r = duckdb.sql("SELECT grp, count(*) n, round(sum(amt),1) s "
               "FROM 'smoke.parquet' GROUP BY grp ORDER BY grp").fetchall()
print(r)   # [(0, 334, ...), (1, 333, ...), (2, 333, ...)]
assert sum(x[1] for x in r) == 1000
print("OK")
PY
```

Expect three rows summing to 1000 and `OK`. If `SUMMARIZE`/`DESCRIBE` on your real file returns sensible dtypes, the read is good.

## Pitfalls

- **`:memory:` blows up on huge exports.** For anything that sorts/joins/exports GBs, `connect("file.duckdb")` and set `temp_directory` — an in-memory db can't spill and will OOM.
- **CSV type sniffing on tail garbage.** The sniffer samples the head; a bad value deep in the file causes cast errors. Use `sample_size = -1` or `ignore_errors = true`, or pin `columns = {...}` explicitly.
- **Globs need quotes and matching depth.** `**/*.parquet` recurses; `*/*.parquet` is exactly one level. Always quote the pattern so the shell doesn't expand it.
- **Secrets are session-scoped by default.** A `CREATE SECRET` in a fresh in-memory connection is gone next run; add `PERSISTENT` (stored under `~/.duckdb/stored_secrets`) or recreate it, and never paste live keys — prefer `PROVIDER credential_chain`.
- **Don't confuse the result object with a frame.** `duckdb.sql(...)` returns a lazy relation; call `.df()`, `.pl()`, `.arrow()`, `.fetchall()`, or `.show()` to materialise. Chaining another `duckdb.sql` over it is fine and stays lazy.
- **One writer.** DuckDB is single-process for writes. It is superb for analytics and ETL, not a concurrent OLTP backend — for that use Postgres.
- **`union_by_name` for schema drift.** Files whose columns differ in order or presence must be read with `union_by_name = true`, else columns align by position and silently mismatch.
