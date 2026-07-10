---
name: clickhouse-realtime-analytics
category: data-analysis
description: >
  Build real-time columnar OLAP over event streams with ClickHouse — ingest millions of events/sec, pre-aggregate on write via incremental materialized views, and serve sub-second GROUP BY dashboards. Use when the user says "ClickHouse", "real-time analytics", "event stream analytics", "materialized view", "MergeTree", "SummingMergeTree/AggregatingMergeTree", "clickhouse-local", "chDB", "Kafka table engine", "Tinybird", "clickstream/impression/telemetry rollups", or wants live rollups that DuckDB (embedded/batch) and Postgres (row-store) can't serve. Covers local single-binary, chDB (in-process Python), and server + Kafka ingest.
when_to_use:
  - User wants a live analytics store over a high-volume event/impression/clickstream/telemetry feed with sub-second aggregate queries
  - User wants incremental materialized views that pre-aggregate on insert (rollups by minute/hour, uniq counts, quantiles) instead of scanning raw rows per query
  - User wants to ingest from Kafka/streams continuously into a queryable columnar table
  - User wants to run ClickHouse SQL locally with zero server (clickhouse-local single binary or chDB in Python) over Parquet/CSV/files
  - User is choosing a MergeTree engine + ORDER BY / partitioning for a wide event table and wants it right the first time
  - User references Tinybird (managed ClickHouse + API endpoints) for a real-time data product
when_not_to_use:
  - User wants embedded batch SQL over a few files with zero infra and no streaming/rollups → use duckdb-analytics
  - User wants dataframe method-chaining not SQL → use polars-dataframes
  - User wants a transactional multi-writer app backend (row-level updates, foreign keys) → use Postgres/SQLite, not ClickHouse
  - User wants managed transformation modelling / DAGs over a warehouse → use dbt-analytics-engineering or sqlmesh-transformations
  - User only needs batch time-series forecasting on a small series → use time-series-forecasting
keywords:
  - clickhouse
  - real-time
  - olap
  - columnar
  - materialized-view
  - mergetree
  - aggregatingmergetree
  - summingmergetree
  - kafka
  - event-stream
  - clickhouse-local
  - chdb
  - tinybird
  - rollup
  - streaming
  - sub-second
similar_to:
  - duckdb-analytics
  - polars-dataframes
  - time-series-forecasting
  - dbt-analytics-engineering
  - parquet-arrow-optimization
inputs_needed:
  - The event source — a Kafka topic, a stream of INSERTs, or Parquet/CSV/JSON files/rows to load
  - The event schema (columns + types) and the primary sort/filter dimensions (e.g. timestamp, campaign_id, user_id)
  - The rollups/dashboards to serve — which GROUP BY dimensions, time bucket (minute/hour/day), and metrics (count, sum, uniq, quantile)
  - Deployment target — local single binary / chDB in Python / self-hosted server / ClickHouse Cloud / Tinybird
produces: A ClickHouse table design (MergeTree engine + ORDER BY + partitioning), incremental materialized views that pre-aggregate on write, and runnable ingest + query SQL — served locally, from Python, or on a server.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# ClickHouse Real-Time Analytics

ClickHouse is an open-source columnar OLAP database built for **real-time analytics over event streams**: it ingests millions of rows/sec and answers `GROUP BY` aggregates over billions of rows in sub-second. The trick that makes dashboards instant is the **incremental materialized view** — a trigger that pre-aggregates each inserted block into a rollup table, so queries read pre-summed data, not raw events. This is the gap DuckDB (embedded/batch) and Postgres (row-store) cannot fill. Ad-tech fit: impression/click/spend streams, campaign rollups, real-time frequency and reach (`uniq`) dashboards.

## When to use

Reach for ClickHouse when the workload is **append-heavy events + aggregate reads at scale/low latency**: clickstream, impressions, telemetry, logs. If it's a handful of files queried once, `duckdb-analytics` is simpler with zero infra. If you need row updates and transactions, use Postgres. Three deployment shapes, cheapest first:

1. **Local single binary** (`clickhouse local`) — SQL over files, no server. Like DuckDB but ClickHouse SQL + MergeTree.
2. **chDB** — ClickHouse embedded in Python (`pip install chdb`), for notebooks/ETL, with persistent sessions that keep MergeTree tables and MVs on disk.
3. **Server** (`clickhouse server` or ClickHouse Cloud / Tinybird) — persistent, Kafka ingest, concurrent dashboard queries.

## Prerequisites

- **No brew needed.** The single binary self-installs: `curl https://clickhouse.com/ | sh` drops a `./clickhouse` in the current dir (macOS arm64/x86, Linux). No root.
- **chDB** for Python: `pip install chdb` (Python 3.8+, so this Mac's 3.9 is fine; macOS + Linux, x86_64/ARM64).
- A **server** needs the same binary run as `./clickhouse server`, or use **ClickHouse Cloud** / **Tinybird** (managed — no ops). Kafka ingest requires a reachable broker.
- Know your **sort key** before creating a table — `ORDER BY` is the physical sort/primary index and is the single biggest performance lever. Put your most-filtered low-cardinality columns first, timestamp last.

## Recipe 1 — Zero-server SQL over files (clickhouse-local)

```bash
curl https://clickhouse.com/ | sh                 # → ./clickhouse (single binary)

# Query a Parquet/CSV directly, no server, no load step:
./clickhouse local -q "
  SELECT campaign_id, count() AS impressions, uniq(user_id) AS reach
  FROM file('events.parquet', Parquet)
  WHERE event_type = 'impression'
  GROUP BY campaign_id ORDER BY impressions DESC LIMIT 20"

# Convert / repartition on the way out:
./clickhouse local -q "
  SELECT * FROM file('raw/*.csv', CSVWithNames)
  INTO OUTFILE 'events.parquet' FORMAT Parquet"
```

`file()` globs, reads Parquet/CSV/JSON/Arrow, and infers schema. Use this for one-shot analysis and format conversion.

## Recipe 2 — In-process ClickHouse in Python (chDB)

```python
import chdb
# One-shot, stateless — returns bytes; ask for a format:
print(chdb.query("SELECT version()", "CSV"))
print(chdb.query(
    "SELECT campaign_id, count() c FROM file('events.parquet', Parquet) "
    "GROUP BY campaign_id ORDER BY c DESC LIMIT 5", "PrettyCompact"))

# Persistent session — MergeTree tables + materialized views survive on disk:
from chdb import session
sess = session.Session("./ch_data")            # dir persists between runs
sess.query("CREATE DATABASE IF NOT EXISTS app")
sess.query("""
  CREATE TABLE IF NOT EXISTS app.events (
     ts DateTime, campaign_id UInt32, user_id UInt64,
     event_type LowCardinality(String), cost Float64
  ) ENGINE = MergeTree ORDER BY (campaign_id, ts)""")
sess.query("INSERT INTO app.events VALUES (now(), 42, 1001, 'impression', 0.004)")
print(sess.query("SELECT campaign_id, count() FROM app.events GROUP BY campaign_id", "CSV"))
sess.close()
```

chDB also has `session.Session().query(sql, "DataFrame")` to hand results straight to Pandas.

## Recipe 3 — The pattern that makes it real-time: incremental materialized view

Never scan raw events per dashboard load. Create a **target rollup table** with an aggregating engine and a **materialized view** that fills it on every insert. The MV is a trigger: it runs its `SELECT` on each inserted block and writes the partial result to the target, which merges asynchronously.

```sql
-- Raw event stream (sorted for range scans by campaign then time):
CREATE TABLE events (
    ts          DateTime,
    campaign_id UInt32,
    user_id     UInt64,
    event_type  LowCardinality(String),
    cost        Float64
) ENGINE = MergeTree
PARTITION BY toYYYYMM(ts)
ORDER BY (campaign_id, ts);

-- Rollup target: one row per (minute, campaign). SummingMergeTree sums numeric
-- columns on merge; AggregateFunction columns hold partial uniq/quantile state.
CREATE TABLE campaign_1m (
    minute       DateTime,
    campaign_id  UInt32,
    impressions  UInt64,
    spend        Float64,
    reach_state  AggregateFunction(uniq, UInt64)
) ENGINE = SummingMergeTree
ORDER BY (campaign_id, minute);

-- Materialized view = the trigger. Pre-aggregates each insert block:
CREATE MATERIALIZED VIEW campaign_1m_mv TO campaign_1m AS
SELECT
    toStartOfMinute(ts)          AS minute,
    campaign_id,
    countIf(event_type='impression') AS impressions,
    sum(cost)                    AS spend,
    uniqState(user_id)           AS reach_state
FROM events
GROUP BY minute, campaign_id;
```

Query the rollup — sub-second even over billions of raw rows. Note `-Merge` finalises the `uniq` state, and re-aggregate because the target may hold several partial rows per key until background merge:

```sql
SELECT
    campaign_id,
    sum(impressions)          AS impressions,
    round(sum(spend), 2)      AS spend,
    uniqMerge(reach_state)    AS reach          -- finalise the aggregate state
FROM campaign_1m
WHERE minute >= now() - INTERVAL 1 HOUR
GROUP BY campaign_id
ORDER BY impressions DESC;
```

**Rules for MVs:** the MV reads only the *newly inserted* block, not history — it does not backfill (populate the target separately for existing data). It fires on the `FROM` table only. `SummingMergeTree` sums plain numeric columns with matching sort keys; use `AggregatingMergeTree` + `xState`/`xMerge` for `uniq`, `quantile`, `avg`, `argMax`. Deduplicate late/duplicate events with `ReplacingMergeTree(version)` + `FINAL` (or aggregate around it).

## Recipe 4 — Continuous ingest from Kafka

The Kafka table engine is a consumer; a materialized view moves rows from it into a MergeTree table (querying the Kafka table directly consumes/loses messages).

```sql
CREATE TABLE events_queue (
    ts DateTime, campaign_id UInt32, user_id UInt64,
    event_type String, cost Float64
) ENGINE = Kafka
SETTINGS kafka_broker_list = 'broker:9092',
         kafka_topic_list  = 'events',
         kafka_group_name  = 'ch_events',
         kafka_format      = 'JSONEachRow';

CREATE MATERIALIZED VIEW events_ingest_mv TO events AS
SELECT ts, campaign_id, user_id, event_type, cost FROM events_queue;
```

Now every message lands in `events`, which cascades into `campaign_1m` via Recipe 3. On **ClickHouse Cloud** prefer **ClickPipes**; on **Tinybird** you declare the same as a Data Source + a Pipe and get an auth'd HTTP endpoint over the rollup for free.

## Verify

```bash
./clickhouse local -q "SELECT version()"                      # binary works
python3 -c "import chdb; print(chdb.query('SELECT 1','CSV'))"  # chDB works, prints 1
```

- After creating an MV, `INSERT` a few rows into the source and confirm the rollup fills:
  `SELECT count() FROM campaign_1m` should grow as you insert into `events`.
- `SELECT * FROM system.mutations WHERE is_done = 0` — no stuck mutations.
- `EXPLAIN indexes = 1 SELECT ...` — confirm your `WHERE`/`ORDER BY` hits the primary index (no full scan).
- Force a merge to check final aggregate values: `OPTIMIZE TABLE campaign_1m FINAL` (dev only — expensive at scale).

## Pitfalls

- **MVs don't backfill.** Creating the MV only affects future inserts. Populate the target for existing rows with a one-off `INSERT INTO target SELECT ... FROM source`.
- **Querying a `SummingMergeTree`/`AggregatingMergeTree` without re-aggregating** returns pre-merge duplicate rows. Always wrap in `GROUP BY` + `sum(...)`/`xMerge(...)`; don't rely on background merges having run.
- **Wrong `ORDER BY`.** It is the primary index and the merge/dedup key — not just cosmetic. Lead with the columns you filter on most; a bad sort key makes every query a scan. There's no separate `PRIMARY KEY` needed unless it differs (prefix of ORDER BY).
- **Single-row / tiny inserts.** ClickHouse hates many small inserts (each makes a part). Batch to thousands–millions of rows, or use async inserts (`async_insert=1`) / a buffer. Kafka MVs already batch.
- **Treating it like OLTP.** No cheap single-row `UPDATE`/`DELETE` (they're async mutations that rewrite parts). Model as append-only events; express "current state" via `ReplacingMergeTree` + `FINAL` or `argMax`.
- **`uniq` vs `uniqExact`.** `uniq`/`uniqState` is an approximate HLL sketch (fast, mergeable) — right for reach/frequency dashboards; use `uniqExact` only when exactness matters (slower, heavier state).
- **`Nullable` and low-cardinality strings.** Avoid `Nullable` on hot columns (extra column + slower); use `LowCardinality(String)` for repeated categoricals like `event_type`/`country` — big memory + speed win.
- **chDB stateless `query()` forgets tables.** Use `chdb.session.Session(path)` when you need tables/MVs to persist across calls; the bare `chdb.query()` is one-shot in-memory.
