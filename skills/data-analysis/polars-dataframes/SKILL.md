---
name: polars-dataframes
category: data-analysis
description: >
  Reach for Polars when pandas is too slow or blows past RAM. Use its expression + lazy API and
  multi-threaded Rust engine to filter/group/join/window millions of rows fast, stream
  bigger-than-RAM Parquet/CSV with collect(engine="streaming") and sink_*, and migrate pandas
  idioms cleanly. Trigger on "polars", "pl.scan_parquet", "lazy dataframe", "streaming query",
  "out-of-core", "faster than pandas", or "dataframe too big for memory".
when_to_use:
  - A pandas job is slow, single-threaded, or exhausts memory on a wide/tall table
  - You must process a dataset larger than RAM (scan + streaming + sink to Parquet/CSV)
  - You want a composable, optimizable query (predicate/projection pushdown) over CSV/Parquet/Arrow
  - Porting pandas code to a faster columnar engine while keeping a DataFrame API
  - Heavy group_by/join/window aggregations where multi-threading matters
when_not_to_use:
  - You only need SQL over local files or want to JOIN across formats ad hoc → use duckdb-analytics
  - Tiny data (< a few MB) where pandas is already instant → plain pandas is simpler
  - You need a full transform DAG with tests/lineage → use dbt-analytics-engineering or sqlmesh-transformations
  - Pure Parquet/Arrow file tuning (compression, row groups, schema) → use parquet-arrow-optimization
keywords: [polars, dataframe, lazyframe, expression-api, streaming, out-of-core, scan_parquet, sink_parquet, group_by, window-function, pandas-migration, columnar, arrow, predicate-pushdown, collect]
similar_to: [duckdb-analytics, parquet-arrow-optimization, data-processing]
inputs_needed: Path/format of the data (CSV/Parquet/Arrow/DB), approximate size vs RAM, the transform (filter/group/join/window), and desired output (DataFrame in memory vs sink to file).
produces: Runnable Polars code (eager or lazy/streaming) plus the exact pip install and the correct collect/sink calls for the installed version.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Polars DataFrames

Polars is a multi-threaded, columnar DataFrame library (Rust core, Arrow memory). Two dialects:
**eager** (`pl.read_*`, runs immediately) and **lazy** (`pl.scan_*` → build a plan → `.collect()`),
where the query optimizer does predicate/projection pushdown and the **streaming engine** runs
bigger-than-RAM data. Prefer lazy for anything non-trivial.

## When to use

Use this when pandas is the bottleneck: too slow (single-threaded), or the frame won't fit in RAM.
Polars wins on wide group-bys, joins, window functions, and Parquet/CSV scans. If you instead want
SQL over files or cross-format joins, use **duckdb-analytics** (they interoperate — both speak Arrow).

## Prerequisites

- Python 3.9+ (this Mac is 3.9). Install: `pip install polars` (or `pip install 'polars[all]'` for
  Excel/DB/plotting extras). No system deps, no brew needed — it's a self-contained wheel.
- For `pl.read_database` you also need a driver (e.g. `connectorx` or an SQLAlchemy engine).
- **Version matters for streaming.** Since ~1.25 the flag is `collect(engine="streaming")`.
  `collect(streaming=True)` is deprecated/removed. Check with:
  `python3 -c "import polars as pl; print(pl.__version__)"`.

## Core mental model

- `pl.col("x")` is an **expression** — a lazy description of a computation, not a value.
- Expressions run inside verbs: `.select()`, `.with_columns()`, `.filter()`, `.group_by().agg()`.
- `.with_columns()` adds/replaces columns and returns a **new** frame (immutable — never mutates).
- Everything inside one `with_columns`/`select` runs in **parallel**, so express many transforms at once.

## Recipes

### 1. Eager basics (drop-in for small data)

```python
import polars as pl

df = pl.read_csv("sales.csv")                     # or pl.read_parquet(...)
out = (
    df
    .filter(pl.col("region") == "EMEA")
    .with_columns(
        (pl.col("units") * pl.col("price")).alias("revenue"),
        pl.col("date").str.to_date("%Y-%m-%d"),
    )
    .group_by("category")
    .agg(
        pl.col("revenue").sum().alias("total_rev"),
        pl.col("units").sum(),
        pl.len().alias("n_rows"),                  # pl.len() = row count (was pl.count())
    )
    .sort("total_rev", descending=True)
)
print(out)
```

### 2. Lazy + streaming for bigger-than-RAM

Build the plan with `scan_*` (never loads the whole file), then collect with the streaming engine.
Predicate/projection pushdown means only needed rows/columns are read.

```python
lf = (
    pl.scan_parquet("s3_export/*.parquet")         # glob supported; lazy, nothing read yet
    .filter(pl.col("event_date") >= pl.date(2026, 1, 1))
    .group_by("user_id")
    .agg(pl.col("amount").sum().alias("spend"))
)

# Inspect the optimized plan without running it:
print(lf.explain(engine="streaming"))

df = lf.collect(engine="streaming")                # runs out-of-core, multi-threaded
```

To write results without ever materialising them in memory, **sink** straight to disk:

```python
(
    pl.scan_csv("huge.csv")
    .filter(pl.col("status") == "paid")
    .sink_parquet("paid.parquet")                  # streaming write; also sink_csv / sink_ipc / sink_ndjson
)
```

### 3. Window functions with `.over()`

No self-joins needed — compute a per-group aggregate aligned back to every row:

```python
df.with_columns(
    pl.col("revenue").sum().over("category").alias("cat_total"),
    pl.col("revenue").rank(descending=True).over("category").alias("rank_in_cat"),
    (pl.col("revenue") / pl.col("revenue").sum().over("category")).alias("share"),
)
```

### 4. Conditional logic and multi-column ops

```python
df.with_columns(
    pl.when(pl.col("score") >= 80).then(pl.lit("A"))
      .when(pl.col("score") >= 60).then(pl.lit("B"))
      .otherwise(pl.lit("C")).alias("grade"),
    # operate on many columns at once via selectors:
    pl.col(pl.Float64).round(2),                   # round every float column
)
```

### 5. Joins (incl. as-of for time series)

```python
df.join(dim, on="product_id", how="left")          # inner|left|right|full|semi|anti|cross
# time-ordered nearest-key join (both frames sorted on the key):
trades.join_asof(quotes, on="ts", by="symbol", strategy="backward")
```

### 6. Reshape

```python
df.pivot(on="month", index="store", values="revenue", aggregate_function="sum")
df.unpivot(index="store", on=["jan", "feb", "mar"])   # unpivot = old .melt (renamed)
```

### 7. pandas migration path

Polars interops through Arrow with near-zero copy — port incrementally.

```python
pdf = df.to_pandas()          # hand back to a pandas-only downstream lib
df2 = pl.from_pandas(pdf)     # bring a pandas frame in
```

Idiom map:
- `df[df.a > 0]`               → `df.filter(pl.col("a") > 0)`
- `df["c"] = df.a + df.b`      → `df.with_columns((pl.col("a") + pl.col("b")).alias("c"))`
- `df.groupby("k").sum()`      → `df.group_by("k").agg(pl.all().sum())`  (note **group_by**, underscore)
- `df.assign(...)` chained     → one `df.with_columns(...)` with all exprs (runs in parallel)
- `df.apply(f, axis=1)`        → prefer native exprs; last resort `pl.col("x").map_elements(f)` (slow)
- `pd.read_csv` on a big file  → `pl.scan_csv(...).collect(engine="streaming")`

Gotchas vs pandas: **no index** (use columns), operations are **immutable** (assign the result back),
and there is no silent `object` dtype — types are explicit.

## Verify

Quick end-to-end smoke test (works on any recent Polars):

```bash
python3 - <<'PY'
import polars as pl
lf = pl.LazyFrame({"k": ["a","a","b"], "v": [1,2,3]}).group_by("k").agg(pl.col("v").sum())
print(lf.collect(engine="streaming").sort("k"))   # expect a->3, b->3
PY
```

- Confirm the version supports `engine="streaming"`: if you get a `TypeError` on `engine=`, upgrade
  (`pip install -U polars`). On very old versions the flag was `streaming=True` — don't mix them.
- Use `lf.explain(engine="streaming")` to confirm pushdown filters appear near the scan (means the
  optimizer is skipping data). If a node says "not supported in streaming", it falls back to in-memory.

## Pitfalls

- **`group_by`, not `groupby`.** Polars uses the underscore form; the pandas spelling errors out.
- **`streaming=True` is dead.** Use `collect(engine="streaming")` and `sink_parquet(...)`. The old
  streaming engine (`engine="old-streaming"`) was removed.
- **Don't `.collect()` then wonder why it's slow.** Keep the whole pipeline lazy from `scan_*` to a
  single terminal `collect`/`sink` so the optimizer sees everything. Every early `.collect()` breaks
  pushdown and materialises intermediate data.
- **Not every op streams.** Some window/pivot/sort-heavy ops fall back to in-memory even under the
  streaming engine — check `explain` and keep a memory margin, or split by a partition key.
- **Expressions ≠ values.** `pl.col("x") + 1` builds a plan; it does nothing until inside a verb.
  You can't `if pl.col("x") > 0:` — use `pl.when().then().otherwise()`.
- **`map_elements` is the escape hatch, not the default.** It runs Python per row and kills throughput.
  Reach for a native expression (string, temporal, list, `.over`) first.
- **Reading a whole file eagerly to filter it** defeats the purpose. If the file is big, `scan_*` so
  the filter is pushed into the read.
- **Excel/DB extras aren't bundled.** `read_excel` needs `pip install 'polars[all]'` (or `fastexcel`);
  `read_database` needs `connectorx` or SQLAlchemy.
