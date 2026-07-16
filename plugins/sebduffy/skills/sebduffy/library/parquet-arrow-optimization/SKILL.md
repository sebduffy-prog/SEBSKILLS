---
name: parquet-arrow-optimization
category: data-analysis
description: >
  Design columnar storage that actually reads fast — pick compression (zstd vs snappy) and
  tune row-group size, partition + sort files for predicate/projection pushdown, verify
  column statistics exist, and hand data between Arrow-native tools (Polars, DuckDB, pandas)
  zero-copy. Use when a Parquet file is slow, huge, or won't push down filters; when someone
  asks how to lay out a dataset, "best compression for parquet", "row group size", "partition
  by date", "why is my parquet scan reading everything", or "convert to Arrow/Feather".
when_to_use:
  - A Parquet file is bigger or slower to scan than it should be and you need to re-lay-it-out
  - You are choosing compression, row-group size, dictionary encoding, or page size for a write
  - You want partitioning + sort order so engines skip row groups / files via predicate pushdown
  - You need to confirm column statistics (min/max) and sorting hints are actually written
  - You are moving data between Arrow-backed tools and want zero-copy interchange (Feather/IPC)
  - You are converting CSV/JSON → Parquet and want the layout right the first time
when_not_to_use:
  - You just want to run SQL over existing Parquet ad hoc → use duckdb-analytics
  - You want dataframe transforms (filter/group/join) not storage tuning → use polars-dataframes
  - You need a versioned lakehouse with snapshots/schema evolution → use ducklake-lakehouse
  - The dataset is tiny (< a few MB) where layout is irrelevant → just write default Parquet
  - You need row-level validation/quality gates on the data → use data-quality-validation
keywords: [parquet, arrow, pyarrow, columnar, compression, zstd, snappy, row-group, partitioning, predicate-pushdown, projection-pushdown, dictionary-encoding, column-statistics, feather, ipc, zero-copy, hive-partitioning, sorting-columns]
similar_to: [duckdb-analytics, polars-dataframes, ducklake-lakehouse, data-processing]
inputs_needed: Source data (path + format), approximate row/byte size, the columns/filters real queries use most (for partition + sort keys), and the consuming tool (Polars/DuckDB/pandas/Spark).
produces: Runnable pyarrow write/read code with the right compression, row-group size, partitioning, sort order, and statistics — plus verification that pushdown works.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Parquet & Arrow Optimization

Make columnar files small on disk AND fast to query. The two goals are different: small
files come from compression + encoding; fast queries come from **row-group sizing +
statistics + partitioning + sort order** so engines skip data they never read. Author with
`pyarrow`, verify the layout, hand off zero-copy.

## When to use

Reach here when a Parquet scan reads far more than the query needs, when you're deciding
how to lay out a dataset for repeated querying, or when moving a table between Arrow-native
tools. If you only need to *query* files, use duckdb-analytics or polars-dataframes — this
skill is about the physical layout underneath them.

## Prerequisites

- `python3 -m pip install "pyarrow>=17"` — the engine here. macOS py3.9 works (tested on
  pyarrow 21). No brew or system deps needed.
- Optional consumers: `polars`, `duckdb` (both read Parquet + Arrow natively, zero-copy).
- No API keys. Everything is local file I/O.

## Mental model (read this first)

A Parquet file is **row groups → column chunks → data pages**. Readers prune at the row-group
level using per-column **statistics** (min/max/null count). So the wins are:

1. **Statistics + sort order** → readers skip whole row groups whose min/max can't match the
   filter. This is *predicate pushdown*. Useless if the filter column is scattered randomly
   across every row group — you must **sort by the filter key before writing**.
2. **Row-group size** → too small = statistics/metadata overhead and poor compression; too
   large = coarse pruning and big memory spikes. Aim for ~128MB–512MB per row group (hundreds
   of thousands to a few million rows). Default `row_group_size` is huge — set it deliberately.
3. **Partitioning** (directory per key, e.g. `region=eu/`) → engines skip entire *files/dirs*
   before opening them. Partition on a **low-cardinality** column you always filter on (date,
   region). High-cardinality partitioning = thousands of tiny files = slow.
4. **Projection pushdown** → columnar means reading only the columns you ask for. Always pass
   `columns=[...]`. Free, but only if you don't `SELECT *`.
5. **Compression + dictionary encoding** → shrink bytes. `zstd` for best ratio (level 3 is a
   great default), `snappy` for max decode speed, `lz4` for Arrow IPC. Dictionary encoding is
   on by default and huge for low-cardinality string columns.

## Recipe 1 — write a well-tuned Parquet file

```python
import pyarrow as pa, pyarrow.parquet as pq

# table is your pyarrow.Table (from pandas: pa.Table.from_pandas(df))
# 1) SORT by the column your queries filter on, so row-group min/max are tight:
table = table.sort_by([("event_date", "ascending"), ("user_id", "ascending")])

# 2) hint the sort order so readers trust it (column indexes into the schema):
sort_hint = [pq.SortingColumn(column_index=table.schema.get_field_index("event_date")),
             pq.SortingColumn(column_index=table.schema.get_field_index("user_id"))]

pq.write_table(
    table, "events.parquet",
    compression="zstd", compression_level=3,   # snappy=faster decode, zstd=smaller
    row_group_size=512_000,                      # ~rows/group; tune to ~128–512MB
    data_page_size=1 << 20,                      # 1MB pages
    use_dictionary=True,                         # great for low-cardinality strings
    write_statistics=True,                       # REQUIRED for pushdown (default True)
    sorting_columns=sort_hint,
)
```

Rule of thumb for `row_group_size`: `target_bytes / (table.nbytes / table.num_rows)`. Start
from a ~256MB target and adjust after checking the written file (Recipe 4).

## Recipe 2 — partitioned dataset for pushdown at the file level

```python
import pyarrow.dataset as ds

ds.write_dataset(
    table, "warehouse/events",
    format="parquet",
    partitioning=["region"],                     # low-cardinality filter column only
    partitioning_flavor="hive",                  # writes region=eu/ dirs (portable)
    existing_data_behavior="overwrite_or_ignore",
    file_options=ds.ParquetFileFormat().make_write_options(
        compression="zstd", write_statistics=True),
    max_rows_per_file=2_000_000,                 # cap tiny-file / huge-file extremes
    max_rows_per_group=512_000,
)
```

Partition on **one or two** low-cardinality columns you filter on constantly (date, region,
tenant). Do NOT partition on user_id/uuid — that's the classic small-files disaster. Sort the
*within-partition* data by your secondary filter key for row-group pruning too.

## Recipe 3 — read with pushdown (the payoff)

```python
import pyarrow.dataset as ds

d = ds.dataset("warehouse/events", format="parquet", partitioning="hive")

# partition filter skips whole dirs; value filter skips row groups; columns= skips columns
sub = d.to_table(
    columns=["user_id", "amount"],                       # projection pushdown
    filter=(ds.field("region") == "eu") &
           (ds.field("event_date") >= "2026-01-01"),     # predicate pushdown
)
```

Polars and DuckDB do the same pushdown automatically over these files:
`pl.scan_parquet("warehouse/events/**/*.parquet").filter(...).select(...).collect()` or
`duckdb.sql("SELECT user_id,amount FROM 'warehouse/events/**/*.parquet' WHERE region='eu'")`.

## Recipe 4 — verify the layout actually pushes down

Never trust the write blind — inspect the metadata:

```python
import pyarrow.parquet as pq
pf = pq.ParquetFile("events.parquet")
md = pf.metadata
print("row groups:", md.num_row_groups, "rows:", md.num_rows)
rg = md.row_group(0); col = rg.column(0)
print("compression:", col.compression, "encodings:", col.encodings)
s = col.statistics
print("has min/max:", s.has_min_max, "min:", s.min, "max:", s.max)   # must be True
print("sorted hint:", md.row_group(0).sorting_columns)
```

Green flags: `has_min_max` is True, `num_row_groups` > 1 for a big file, min/max values are
*tight and non-overlapping across row groups* (that's what makes pruning work — a symptom of
sorting first). Cheap metadata-only read (no data pages): `pq.read_metadata("events.parquet")`.

## Recipe 5 — zero-copy Arrow interchange between tools

Arrow is the in-memory format; Parquet is the on-disk format. Keep data in Arrow to move it
between libraries without re-serializing:

```python
import pyarrow.feather as ft
# Feather = Arrow IPC on disk. Fast to mmap, no decode cost, lz4/zstd optional.
ft.write_feather(table, "t.feather", compression="lz4")
back = ft.read_table("t.feather", memory_map=True)      # zero-copy mmap

# Hand the SAME arrow buffers to other tools — no serialization:
import polars as pl; df = pl.from_arrow(back)            # zero-copy
import duckdb; duckdb.sql("SELECT * FROM back LIMIT 5")  # registers arrow table directly
pdf = back.to_pandas(types_mapper=pd.ArrowDtype)         # arrow-backed pandas, no copy
```

Use **Feather/IPC** for short-lived hand-offs and caches (fast, no compression tax). Use
**Parquet** for storage and anything queried later (statistics, partitioning, best ratio).

## Verify

```bash
python3 -c "import pyarrow.parquet as pq; m=pq.read_metadata('events.parquet'); \
print('rows',m.num_rows,'groups',m.num_row_groups,\
'stats',m.row_group(0).column(0).statistics.has_min_max)"
```
Then confirm a filtered read touches far fewer bytes than a full scan (compare
`d.to_table(filter=...)` timing/rows vs `d.to_table()`), and that a downstream
`pl.scan_parquet(...).filter(...)` returns the same rows.

## Pitfalls

- **Statistics without sorting is nearly useless.** If the filter column isn't sorted, every
  row group's min/max spans the whole range and nothing gets pruned. Sort, then write.
- **Default row-group size can be one giant group** → no pruning granularity and memory
  spikes. Always set `row_group_size` deliberately.
- **Over-partitioning = the small-files problem.** Thousands of sub-1MB files destroy scan
  performance (metadata + open overhead). Keep partition cardinality low; cap with
  `max_rows_per_file`. Compact/rewrite tiny files periodically.
- **`SELECT *` throws away projection pushdown** — the biggest free win. Name your columns.
- **zstd level too high** (>6) costs write time for marginal size gains; level 3 is the sweet
  spot. Use `snappy` when read/decode speed dominates and disk is cheap.
- **Turning off `write_statistics`** (or old writers) silently kills pushdown — verify with
  Recipe 4 after any pipeline change.
- **Reading Parquet just to get row count/schema** — use `pq.read_metadata()` (metadata only),
  don't load data pages.
- **Nested/large-string types + old readers**: prefer `large_string`/`string_view` carefully;
  confirm the consuming engine version supports them before shipping.
