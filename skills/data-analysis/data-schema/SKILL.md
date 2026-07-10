---
name: data-schema
category: data-analysis
description: Inspect, validate, document, and design tabular data schemas with verification at every step. Use when the user shares an unknown dataset and wants its structure characterized, wants an existing schema validated against data, or wants to design a new schema. Triggers on "what's in this data", "what columns are here", "infer schema", "validate schema", "design a table", "what are the dtypes", "are there any nulls", "is this column unique". Anti-hallucination posture — never describe a schema without loading the data and computing dtypes, null counts, and uniqueness; never claim a constraint holds without testing it.
when_to_use:
  - User shares a dataset and asks what's in it
  - User wants column dtypes, null rates, cardinality, value ranges characterized
  - User wants to validate that data conforms to an expected schema (column names, types, constraints)
  - User wants to design a new table / schema for a known use case
  - User asks "what's the primary key", "are there duplicates", "what are the value ranges"
when_not_to_use:
  - User wants to clean / transform the data → use data-processing
  - User wants distributions / summary statistics → use exploratory-data-analysis
  - User wants to test hypotheses about the data → use statistical-testing
  - User only wants to read the file (no schema work) → use documents/xlsx, documents/pdf, etc.
similar_to:
  - data-processing
  - exploratory-data-analysis
keywords:
  - schema
  - dtype
  - column
  - validate
  - constraint
  - primary-key
  - unique
  - null
  - cardinality
  - dataframe
  - table-design
inputs_needed:
  - File path or DataFrame reference
  - (For validation) the expected schema — column names, types, constraints
  - (For design) the use case — what queries will run, what writes will happen, what the entity is
produces: A structured schema report (Markdown table) listing column name, dtype, null %, unique count, sample values, and inferred constraints. For design tasks, a CREATE TABLE statement or Pydantic model.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Data Schema

Inspect existing schemas, validate against expected ones, and design new ones — with verification at every step.

## Verification protocol — no claims without computation

1. **Never describe a schema you have not loaded.** First action for any inspection task: load the data, compute `df.dtypes`, `df.isna().mean()`, `df.nunique()`.
2. **Constraints are tested, not asserted.** If you claim "user_id is unique", you have run `df['user_id'].is_unique` and observed `True`.
3. **Sample values are real values from the data.** Use `df['col'].dropna().sample(min(5, len(df)))`, not an invented illustrative example.
4. **Ranges are computed.** Min/max for numerics, distinct count for categoricals, earliest/latest for dates — all from the actual data.
5. **Inferred types are flagged as inferred.** If pandas read a column as `object` but it looks like dates, you say "inferred datetime — needs confirmation" rather than asserting it.

## Inputs to confirm with the user

**For inspection / validation tasks:**
- **What is the source?** File path, DataFrame in memory, database table?
- **Do you have an expected schema to validate against?** (Column names, types, constraints — if not, the output is descriptive only.)
- **What level of detail?** Headline schema, or per-column distributions and outlier counts?

**For design tasks:**
- **What is the entity / what does one row represent?**
- **What are the queries that will run against it?** Drives indexing.
- **What are the writes that will happen?** Drives normalization choices.
- **What is the source of truth for each field?** (Computed, user-entered, third-party, etc.)
- **What are the volume expectations?** (Drives partitioning, types.)

## Workflow — inspect an unknown dataset

```python
import pandas as pd

df = pd.read_csv(path)

# 1. Shape + dtypes
print("shape:", df.shape)
print("dtypes:\n", df.dtypes)

# 2. Per-column report
for col in df.columns:
    s = df[col]
    print(f"\n--- {col} ---")
    print(f"  dtype: {s.dtype}")
    print(f"  null %: {s.isna().mean() * 100:.1f}")
    print(f"  unique: {s.nunique(dropna=True)}")
    print(f"  sample: {s.dropna().head(3).tolist()}")
    if pd.api.types.is_numeric_dtype(s):
        print(f"  range: [{s.min()}, {s.max()}]")
    if pd.api.types.is_datetime64_any_dtype(s):
        print(f"  range: [{s.min()}, {s.max()}]")

# 3. Candidate primary keys
for col in df.columns:
    if df[col].is_unique and df[col].notna().all():
        print(f"candidate PK: {col}")

# 4. Inferred type upgrades (object columns that look like dates / numbers)
for col in df.select_dtypes(include="object").columns:
    try:
        pd.to_datetime(df[col].dropna().head(50), errors="raise")
        print(f"  {col}: object but parseable as datetime — confirm with user")
    except Exception:
        pass
```

A more complete script is in `assets/schema-inspect.py`.

## Workflow — validate against an expected schema

```python
EXPECTED = {
    "user_id": {"dtype": "int64", "unique": True, "non_null": True},
    "email":   {"dtype": "object", "unique": True, "non_null": True},
    "created": {"dtype": "datetime64[ns]", "non_null": True},
}

failures = []
for col, spec in EXPECTED.items():
    if col not in df.columns:
        failures.append(f"MISSING column: {col}")
        continue
    s = df[col]
    if str(s.dtype) != spec.get("dtype", str(s.dtype)):
        failures.append(f"{col}: dtype expected {spec['dtype']}, got {s.dtype}")
    if spec.get("unique") and not s.is_unique:
        dup = s.value_counts()
        failures.append(f"{col}: not unique — top dup {dup.index[0]!r} appears {dup.iloc[0]}×")
    if spec.get("non_null") and s.isna().any():
        failures.append(f"{col}: {s.isna().sum()} nulls (non_null violated)")

extra = set(df.columns) - set(EXPECTED)
if extra:
    failures.append(f"UNEXPECTED columns: {sorted(extra)}")

if failures:
    for f in failures:
        print("FAIL:", f)
else:
    print("schema OK")
```

## Workflow — design a new schema

Before producing SQL or Pydantic, the model must:

1. Get clear answers to the design inputs above. If user gives vague answers, surface tradeoffs and ask again.
2. Produce a draft in plain English ("table `users` holds one row per registered user, identified by `user_id` (int, surrogate). `email` is unique and non-null. `created_at` is a UTC timestamp with no time zone…") and confirm with the user before writing DDL.
3. Then emit DDL (or Pydantic / SQLAlchemy / Prisma — match the user's stack).

## Anti-patterns to refuse

- "Looks like a typical customer table" without loading anything → **stop, load the data, then describe**.
- "user_id is probably the primary key" → either compute and confirm, or say "candidate PK to confirm with user".
- Inventing sample values for illustration → use real values from `df['col'].dropna().sample()`.
- Describing a column as "mostly integers" when it's typed `object` → either coerce and report failures, or flag as "object, parseable as int — needs user confirmation".

## Output format

For inspection, produce a Markdown table:

```markdown
| Column     | Dtype    | Null % | Unique | Range / Sample          | Notes                  |
|------------|----------|-------:|-------:|-------------------------|------------------------|
| user_id    | int64    |   0.0  |  10234 | [1, 10234]              | Candidate PK           |
| email      | object   |   0.1  |  10220 | "a@b.com", "c@d.com"    | 14 nulls; 13 dupes     |
| created_at | object   |   0.0  |   8421 | "2024-01-15 10:30:00"   | Parseable as datetime  |
```

## Asset

`assets/schema-inspect.py` — a runnable script that emits the Markdown schema table above for any CSV input.
