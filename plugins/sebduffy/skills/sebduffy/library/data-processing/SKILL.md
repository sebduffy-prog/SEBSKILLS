---
name: data-processing
category: data-analysis
description: Clean, transform, deduplicate, normalize, and reshape tabular data with verification at every step. Use when the user has a CSV, Excel, JSON, or DataFrame and wants it cleaned, joined, pivoted, aggregated, or otherwise transformed before downstream use. Triggers on phrases like "clean this data", "deduplicate", "fill missing values", "merge these files", "reshape", "normalize", "transform", "ETL". Anti-hallucination posture — never describe the result of a transformation without executing it and reporting actual row/column counts before and after.
when_to_use:
  - User has a dataset and asks for cleaning, joining, reshaping, or deduplication
  - User wants to handle missing values, outliers, or type coercion
  - User wants to derive new columns or aggregate rows
  - User wants to merge or join multiple datasets
  - User mentions "tidy", "wrangle", "munge", "ETL", "pipeline"
when_not_to_use:
  - User wants statistical analysis → use exploratory-data-analysis or statistical-testing
  - User wants to design a schema from scratch with no data yet → use data-schema
  - User wants to read/write a spreadsheet file format → use documents/xlsx
  - User asks a math problem unrelated to data → use mathematical-computation
similar_to:
  - data-schema
  - exploratory-data-analysis
  - xlsx
keywords:
  - clean
  - transform
  - dedupe
  - deduplicate
  - merge
  - join
  - pivot
  - reshape
  - normalize
  - pandas
  - polars
  - dataframe
  - etl
  - wrangle
  - tidy
inputs_needed:
  - File path or DataFrame reference
  - What "clean" means in this case (the user's success criteria)
  - Which columns are keys (for dedupe and joins)
  - How to handle missing values (drop row, drop column, fill with what)
  - Expected output format (new file, in-place, returned object)
produces: A reproducible Python script and a verified output dataset, with row/column counts logged at each stage
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Data Processing

Clean, transform, deduplicate, and reshape tabular data with verification at every stage.

## Verification protocol — no claims without computation

1. **Inspect before transforming.** First action: load the data, print `df.shape`, `df.dtypes`, `df.isna().sum()`, `df.head()`. Do not propose transformations before this.
2. **Count before AND after every step.** Each transformation logs row count before, row count after, and the delta. Surprises (dropped 90% of rows, etc.) are flagged in the response.
3. **Never describe the output without computing it.** "Now there are 1,234 unique users" must come from `df['user'].nunique()` you actually executed in this session.
4. **Sample, don't summarize.** When showing transformation results, include `df.head(5)` of the output, not a paraphrase.
5. **Validate invariants.** After dedup, assert key column is unique. After fillna, assert null count is what you expect.

## Inputs to confirm with the user before starting

Ask if not already provided:

- **What does "clean" or "transformed" mean to you?** Specific output schema, or general tidying?
- **Which columns are keys?** Critical for deduplication and joins.
- **How should missing values be handled?** Drop the row? Drop the column? Fill with mean/median/zero/sentinel/forward-fill?
- **Are there known invalid values to exclude?** (e.g. test rows, `-999` sentinels, future dates)
- **What is the expected output format?** New CSV? Update in place? DataFrame returned?
- **Performance constraint?** If dataset > 10M rows, propose polars or chunked reads.

If the user can't answer, propose a default and confirm before executing.

## Standard workflow

```python
import pandas as pd

# 1. LOAD + INSPECT (always first)
df = pd.read_csv(path)
print("Loaded:", df.shape)
print("Dtypes:\n", df.dtypes)
print("Nulls per column:\n", df.isna().sum())
print("Sample:\n", df.head())

# 2. TRANSFORM (log delta on every step)
before = len(df)
df = df.drop_duplicates(subset=["user_id"])
print(f"Dedup on user_id: {before} -> {len(df)} ({before - len(df)} removed)")

before = len(df)
df = df.dropna(subset=["email"])
print(f"Drop null email: {before} -> {len(df)} ({before - len(df)} removed)")

# 3. VALIDATE (assert invariants)
assert df["user_id"].is_unique, "user_id not unique after dedup"
assert df["email"].notna().all(), "null emails remain"

# 4. OUTPUT + SAMPLE
df.to_csv(output_path, index=False)
print("Wrote:", output_path, df.shape)
print(df.head())
```

A more complete template lives in `assets/processing-template.py`.

## Anti-patterns to refuse

- "It should have around 5,000 rows after deduplication." → **Never approximate.** Compute and report exact.
- Silent transformations. **Every step must log row-count delta.**
- `try / except: pass`. If a coercion fails, **stop and report** — don't paper over it.
- Filling missing values without asking. **Default behavior must be confirmed with the user.**
- Joining on columns without first verifying join cardinality. Always report join type and inflation/loss.
- Using `df.dropna()` without specifying a column subset — usually drops far more than intended.

## Common operations + their verification

| Operation | What to log |
|---|---|
| `drop_duplicates(subset=…)` | rows before / after / removed |
| `dropna(subset=…)` | rows before / after / removed; which columns checked |
| `merge` / `join` | left rows, right rows, output rows; relationship (1:1, 1:many) verified |
| `groupby().agg(…)` | input rows, output rows; check no unexpected nulls in aggregation |
| `astype(…)` | rows where coercion failed (use `pd.to_numeric(errors='coerce')` and count NaNs introduced) |
| `fillna(…)` | count of nulls filled per column |
| `pivot` / `melt` | shape before, shape after; spot-check with `head()` |

## Escalation paths

- **Dataset > 10M rows** → propose polars or chunked pandas; tell the user before switching.
- **Ambiguous business rule** (e.g. "are these two rows the same person?") → surface the ambiguity, propose options, don't guess.
- **Unrecognized file format** → ask the user, don't assume.

## Asset

`assets/processing-template.py` — a reusable Python script with the verification protocol baked in. Adapt the transformation steps; keep the logging structure.
