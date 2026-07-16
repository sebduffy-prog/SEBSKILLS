---
name: ducklake-lakehouse
category: data-analysis
description: >
  Stand up a real lakehouse with DuckLake — a SQL catalog (SQLite/Postgres/DuckDB) for metadata plus
  Parquet data files on local disk or S3 — giving you ACID transactions, snapshots, and time-travel
  queryable straight from DuckDB. Reach for this when you want Iceberg/Delta-style versioned tables
  without Spark or a metastore. Trigger on "ducklake", "lakehouse", "time travel", "table snapshots",
  "ACID parquet", "iceberg alternative", "versioned parquet", or "catalog + parquet on S3".
when_to_use:
  - You want ACID inserts/updates/deletes over Parquet with snapshot history and rollback
  - You need time-travel queries (query a table AT a past version or timestamp)
  - You want an Iceberg/Delta-like table format but backed by a plain SQL catalog, no Spark/metastore
  - Multiple readers (and a coordinated writer) need a shared, consistent view over Parquet on S3
  - You are prototyping a lakehouse locally and may later promote the catalog to Postgres
when_not_to_use:
  - You just need to run SQL over existing CSV/Parquet with no versioning → use duckdb-analytics
  - You only care about tuning one Parquet file (compression, row groups) → use parquet-arrow-optimization
  - You need a full transform DAG with tests + lineage → use dbt-analytics-engineering or sqlmesh-transformations
  - You must interop with an existing Iceberg/Delta catalog other engines already write → use those native formats
  - Pure in-memory dataframe crunching → use polars-dataframes
keywords: [ducklake, lakehouse, duckdb, parquet, acid, snapshots, time-travel, catalog, sqlite, postgres, s3, iceberg-alternative, delta-alternative, versioned-tables, metadata, schema-evolution]
similar_to: [duckdb-analytics, parquet-arrow-optimization, dbt-analytics-engineering, sqlmesh-transformations, dlt-python-pipelines]
inputs_needed: Catalog backend (sqlite/postgres/duckdb-file), where data files live (local dir or s3://), the source data (CSV/Parquet/DataFrame), and whether you need multi-writer (→ Postgres).
produces: A working DuckLake catalog + Parquet data path with versioned tables, plus runnable SQL for snapshots, time travel, change feeds, and compaction/expiry maintenance.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# DuckLake Lakehouse

DuckLake is an open table format (v1.0, April 2026) where **all metadata lives in a SQL database**
(SQLite, PostgreSQL, MySQL, or a DuckDB file) and **all data lives in Parquet files**. You get ACID
transactions, snapshots, time-travel, and schema evolution — driven entirely from DuckDB SQL, with no
Spark, no Hive metastore, and no pile of JSON manifest files (the Iceberg/Delta pain point). One
`ATTACH` and you are querying a versioned lakehouse.

## When to use

Use this to create/query versioned tables with rollback and change feeds. If you just want ad-hoc SQL
over files with no history, that's `duckdb-analytics` — come here the moment you need snapshots,
time-travel, or coordinated multi-reader access to Parquet.

## Prerequisites

- **DuckDB v1.3.0+** (ducklake needs it; v1.4 recommended). The `ducklake` extension is a **core
  extension that autoloads** on first `ATTACH 'ducklake:...'` — no manual INSTALL usually needed.
- CLI or Python. On this Mac (python3.9, no brew):
  ```bash
  pip3 install --quiet 'duckdb>=1.3'      # Python API, or:
  # CLI binary: download from https://duckdb.org/docs/installation (no brew needed)
  ```
- Backends: SQLite catalog needs nothing extra. **Postgres** catalog needs `INSTALL postgres;` and a
  reachable Postgres 12+ with the catalog DB pre-created. **S3** data path needs `INSTALL httpfs;` and
  credentials via a `CREATE SECRET`.
- Naming: `'ducklake:foo.ducklake'` uses a DuckDB-file catalog; `'ducklake:sqlite:foo.sqlite'` and
  `'ducklake:postgres:...'` pick those backends. `DATA_PATH` is where Parquet is written.

## Recipes

### 1. Local lakehouse in 3 lines (SQLite catalog + local Parquet)

```sql
-- metadata.sqlite holds the catalog; data_files/ holds the Parquet
ATTACH 'ducklake:sqlite:metadata.sqlite' AS lake (DATA_PATH 'data_files/');
USE lake;

CREATE TABLE nl_stations AS FROM 'https://blobs.duckdb.org/nl_stations.csv';
```

The DuckDB-file backend is even terser but is **single-client only** (one process): 
`ATTACH 'ducklake:metadata.ducklake' AS lake (DATA_PATH 'data_files/');`. Prefer **SQLite** for local
multi-reader, **Postgres** for real concurrency.

### 2. ACID mutations create snapshots automatically

Every committed statement is a new snapshot.

```sql
INSERT INTO nl_stations VALUES (999, 'ASD', 'X', 'Test', 'Test Halt', 4.9, 52.3, 'NL', 'megastation');
UPDATE nl_stations SET name_long = 'Johan Cruijff ArenA' WHERE code = 'ASB';
DELETE FROM nl_stations WHERE id = 999;

-- inspect the history
FROM lake.snapshots();                 -- snapshot_id, snapshot_time, schema_version, changes
FROM lake.current_snapshot();
```

### 3. Time travel (by version or timestamp)

```sql
-- by snapshot version number
SELECT name_long FROM nl_stations AT (VERSION => 2) WHERE code = 'ASB';

-- by wall-clock time (as-of query)
SELECT * FROM nl_stations AT (TIMESTAMP => TIMESTAMP '2026-07-09 12:00:00');
```

`AT (VERSION => n)` returns the table exactly as it was at snapshot `n`. This is your rollback /
audit / reproducibility lever — pin a report to a version and it never drifts.

### 4. Change feed between two snapshots (CDC)

```sql
-- rows that changed in table 'nl_stations' (main schema) from snapshot 1 → 3
SELECT * FROM ducklake_table_changes('lake', 'main', 'nl_stations', 1, 3);
```

Returns inserted/updated/deleted rows with a change-type column — cheap incremental downstream loads
without diffing full tables.

### 5. Commit metadata (author + message per snapshot)

```sql
BEGIN;
  INSERT INTO nl_stations VALUES (1000, 'ZZ', 'Z', 'Zed', 'Zed Central', 5.0, 52.0, 'NL', 'stoptreinstation');
  CALL lake.set_commit_message('seb', 'seed one row');
COMMIT;
```

### 6. Postgres-backed catalog (real concurrency) + S3 data

```sql
INSTALL postgres; INSTALL httpfs;

CREATE SECRET (TYPE s3, KEY_ID '…', SECRET '…', REGION 'eu-west-2');

-- the 'ducklake_catalog' Postgres DB must already exist
ATTACH 'ducklake:postgres:dbname=ducklake_catalog host=localhost' AS lake
    (DATA_PATH 's3://my-bucket/lakehouse/');
USE lake;
```

Now many DuckDB clients can read concurrently; Postgres serialises writer transactions. Same SQL as
the local recipes — only the ATTACH line changed.

### 7. Python driver (end-to-end)

```python
import duckdb
con = duckdb.connect()
con.execute("ATTACH 'ducklake:sqlite:metadata.sqlite' AS lake (DATA_PATH 'data_files/')")
con.execute("USE lake")
con.execute("CREATE TABLE IF NOT EXISTS events(id INTEGER, ts TIMESTAMP, kind VARCHAR)")
con.execute("INSERT INTO events VALUES (1, now(), 'click')")
print(con.sql("FROM lake.snapshots()").fetchall())
print(con.sql("SELECT * FROM events AT (VERSION => 0)").fetchall())  # empty pre-insert snapshot
```

### 8. Maintenance — compaction, expiry, checkpoint

Small frequent writes make many tiny Parquet files. Compact and prune periodically:

```sql
-- merge many small adjacent Parquet files into fewer big ones
CALL ducklake_merge_adjacent_files('lake');
CALL ducklake_merge_adjacent_files('lake', 'nl_stations', schema => 'main');  -- target one table

-- drop old snapshots: keep >=5 versions, remove anything older than 7 days
SELECT * FROM ducklake_expire_snapshots('lake', older_than => now() - INTERVAL '7 days', versions => 5);

-- physically delete Parquet files no longer referenced by any live snapshot
CALL ducklake_cleanup_old_files('lake', cleanup_all => true);
```

Run compaction after bulk loads and expiry on a schedule; expiry must precede cleanup (cleanup only
removes files already orphaned by expiry).

## Verify

Quick smoke test (SQLite backend, no network needed) — run in a scratch dir:

```bash
cd "$(mktemp -d)"
python3 - <<'PY'
import duckdb
c = duckdb.connect()
c.execute("ATTACH 'ducklake:sqlite:meta.sqlite' AS lake (DATA_PATH 'data/')")
c.execute("USE lake")
c.execute("CREATE TABLE t AS SELECT * FROM range(3) r(id)")
c.execute("UPDATE t SET id = 99 WHERE id = 0")
snaps = c.sql("FROM lake.snapshots()").fetchall()
v0 = c.sql("SELECT count(*) FROM t AT (VERSION => 1)").fetchone()[0]  # after CREATE
print("snapshots:", len(snaps), "rows@v1:", v0)
PY
ls data/          # Parquet data files should exist
```

Expect ≥2 snapshots (create + update) and Parquet files under `data/`. If `ATTACH` errors with
"unknown extension", your DuckDB is <1.3 — upgrade (`pip3 install -U 'duckdb>=1.3'`).

## Pitfalls

- **DuckDB-file catalog is single-process.** Two writers → lock errors. Use SQLite (local multi-read)
  or Postgres (true concurrency) the moment more than one process touches it.
- **Catalog + data path move together.** The Parquet files under `DATA_PATH` are useless without the
  catalog DB, and vice versa. Back up / relocate both; don't hand-edit the Parquet.
- **Postgres catalog DB must pre-exist.** `ATTACH` won't `CREATE DATABASE` for you — create
  `ducklake_catalog` first.
- **Tiny-file explosion.** Row-by-row inserts each write a Parquet file. Batch inserts, and run
  `ducklake_merge_adjacent_files` after heavy small-write phases.
- **Expiry is destructive and ordered.** `ducklake_expire_snapshots` drops history (time-travel to
  expired versions then fails); run it, *then* `ducklake_cleanup_old_files`. Set `versions`/`older_than`
  conservatively.
- **Relative paths for the DuckDB-file backend** must already exist and are resolved from the CWD —
  prefer absolute `DATA_PATH` in scripts to avoid surprises.
- **Not Iceberg/Delta on the wire.** Other engines can't read a DuckLake catalog natively; it's a
  DuckDB-first format. If you need cross-engine interop, export to Iceberg/Delta instead.
