---
name: data-quality-validation
category: data-analysis
description: >
  Validate a dataframe or CSV/Parquet with declarative schema + rule checks before you trust it — use Pandera
  (typed DataFrameModel, lazy error aggregation) or Pointblank (chained col_vals_* steps + thresholds/actions +
  HTML report) to enforce ranges, sets, regex, nullability and uniqueness, THEN run integrity-forensics screens
  (Benford first-digit, straight-lining / non-differentiation, duplicate respondents, speeders) tuned for
  TGI/GWI/YouGov survey validity. Reach for this whenever data arrives and its trustworthiness is unproven.
when_to_use:
  - A new dataset (survey export, API pull, supplier feed) arrives and you must gate its quality before analysis
  - You need a reusable, versioned data contract that fails loudly on bad rows in a pipeline or CI
  - Auditing survey data for fabrication / bad respondents (straight-liners, speeders, duplicates, fake numbers)
  - Someone hands you TGI/GWI/YouGov tabs and asks "is this data actually valid?"
  - You want an HTML pass/fail data-quality report to attach to a deliverable
when_not_to_use:
  - Pure schema typing of a data-warehouse model without row rules — use data-contracts or dbt-analytics-engineering
  - You just need fast group-by/aggregation, not validation — use polars-dataframes or duckdb-analytics
  - Generating fake test data — use synthetic-data-generation
  - Great Expectations-specific suites already exist in the repo — keep using GX rather than porting
keywords: [data-quality, validation, pandera, pointblank, benford, straight-lining, survey-integrity, schema, data-contract, forensics, tgi, gwi, dataframe, checks, duplicates, speeders]
similar_to: [data-contracts, polars-dataframes, duckdb-analytics, synthetic-data-generation, dbt-analytics-engineering]
inputs_needed: Path to the data (CSV/Parquet/dataframe); which columns are keys/Likert/numeric; expected ranges, allowed value sets, and any regex/format rules; whether you want a Python contract, an HTML report, or forensics.
produces: A validation contract (Pandera model or Pointblank pipeline) plus a pass/fail summary / HTML report and, for surveys, a forensics flag list of suspect rows.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Data Quality & Integrity Forensics

Two complementary jobs: (1) **declarative validation** — does every row obey the schema and business rules? and
(2) **integrity forensics** — do the numbers look *fabricated* even when they pass the schema? Surveys need both:
a respondent who answers "3" to all 20 grid questions passes every range check yet is worthless.

## When to use

Run this the moment untrusted data lands, before any chart or model. Pandera when you want a typed, importable
**data contract** in a pipeline/CI; Pointblank when you want a **chained, threshold-driven report** for a
stakeholder. Layer the forensics screens on top for any survey / respondent-level or financial-count data.

## Prerequisites

macOS here is Python 3.9, no brew. Install into a venv:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install "pandera[pandas]" pointblank pandas pyarrow
```

- **Pandera** ≥0.24 exposes `import pandera.pandas as pa` (the current recommended module; older `import pandera as pa` still works but warns). Verified against 0.32.
- **Pointblank** (posit-dev) needs Polars or Pandas; `interrogate()` runs the plan, `get_tabular_report()` renders HTML.
- **forensics.py** (bundled) needs only pandas — no extra deps.

## Recipe 1 — Pandera contract (typed, CI-friendly)

Prefer the class-based `DataFrameModel` — it doubles as documentation and is importable across a codebase.

```python
import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

class SurveyResponse(pa.DataFrameModel):
    respondent_id: Series[str] = pa.Field(unique=True, str_matches=r"^R\d{6}$")
    age:           Series[int] = pa.Field(ge=16, le=99)
    region:        Series[str] = pa.Field(isin=["North", "South", "Midlands", "Scotland", "Wales"])
    q1:            Series[int] = pa.Field(ge=1, le=5, nullable=False)   # Likert 1–5
    weight:        Series[float] = pa.Field(gt=0, le=20)               # survey weight sanity band
    duration_sec:  Series[int] = pa.Field(ge=1)

    class Config:
        strict = True          # reject unexpected columns
        coerce = True          # cast dtypes where safe

# lazy=True collects EVERY failure instead of raising on the first
try:
    SurveyResponse.validate(df, lazy=True)
    print("PASS")
except pa.errors.SchemaErrors as exc:
    print(exc.failure_cases)   # dataframe: column, check, failure_case, index
```

Custom cross-column rule (e.g. weights must sum sensibly, or a skip-logic gate):

```python
class SurveyResponse(pa.DataFrameModel):
    ...
    @pa.dataframe_check
    def bought_implies_aware(cls, df: pd.DataFrame) -> pd.Series:
        # if q_bought == "Yes" then q_aware must not be null (skip-logic integrity)
        return ~((df["q_bought"] == "Yes") & (df["q_aware"].isna()))
```

Equivalent object API when you build the schema dynamically:

```python
schema = pa.DataFrameSchema({
    "age":    pa.Column(int, pa.Check.in_range(16, 99)),
    "region": pa.Column(str, pa.Check.isin(["North","South","Midlands","Scotland","Wales"])),
    "q1":     pa.Column(int, [pa.Check.ge(1), pa.Check.le(5)], nullable=False),
}, strict=True, coerce=True)
schema.validate(df, lazy=True)
```

## Recipe 2 — Pointblank pipeline + HTML report (stakeholder-facing)

Chain steps, set warn/error/critical thresholds as *fractions of failing rows*, then interrogate.

```python
import pointblank as pb

v = (
    pb.Validate(
        data=df,
        label="TGI wave 3 — data quality gate",
        thresholds=pb.Thresholds(warning=0.01, error=0.05, critical=0.10),
        actions=pb.Actions(critical="STOP: {step} breached critical"),
    )
    .col_exists(["respondent_id", "age", "region", "weight"])
    .col_vals_regex("respondent_id", pattern=r"^R\d{6}$")
    .col_vals_between("age", left=16, right=99)
    .col_vals_in_set("region", set=["North","South","Midlands","Scotland","Wales"])
    .col_vals_between("weight", left=0, right=20, inclusive=(False, True))
    .col_vals_not_null("q1")
    .rows_distinct()                       # no fully duplicated respondents
    .interrogate()
)

print(v.all_passed())                      # bool gate for CI
v.get_tabular_report().write_html("dq_report.html")   # attach to deliverable
# v.get_sundered_data(type="fail")         # pull only the failing rows for triage
```

Common steps: `col_vals_gt/ge/lt/le/between/eq/ne`, `col_vals_in_set` / `not_in_set`, `col_vals_regex`,
`col_vals_null` / `not_null`, `col_exists`, `col_count_match`, `row_count_match`, `rows_distinct`,
`rows_complete`, `conjointly(...)` for multi-condition logic.

## Recipe 3 — Integrity forensics (does it look fabricated?)

Schema-passing survey/financial data can still be junk. The bundled `scripts/forensics.py` runs four screens and
exits non-zero when one trips, so it drops into CI. It only needs pandas.

```bash
# Benford first-digit test — genuine "found" magnitudes (spend, counts, populations) follow log10(1+1/d).
# Flags NONCONFORMANT (Nigrini MAD>0.015) or chi2>15.51. Needs >=300 values to be meaningful.
python3 scripts/forensics.py benford data.csv --col claimed_spend

# Straight-lining / non-differentiation across a Likert grid — flat & low-variance rows.
python3 scripts/forensics.py straight data.csv --cols q1,q2,q3,q4,q5,q6

# Duplicate respondents on a key set of answers (copy-paste / bot fills).
python3 scripts/forensics.py duplicates data.csv --cols q1,q2,q3,q4,q5

# Speeders — completed in <40% of median time (tune with --floor).
python3 scripts/forensics.py speeders data.csv --col duration_sec --floor 0.4
```

Interpretation guardrails:
- **Benford applies only to naturally-scaled "found" numbers spanning orders of magnitude** — NOT to bounded
  Likert 1–5, ages, percentages, or assigned IDs. Using it there produces false alarms; don't.
- Straight-lining >5% of the sample, or speeders >10%, is a data-collection red flag worth escalating to the
  fieldwork supplier — not automatic deletion. Cross-check flagged indices before dropping.
- These screens *surface* suspects; the decision to exclude a respondent is human and should be logged.

## Verify

```bash
python3 -c "import pandera.pandas as pa, pointblank as pb; print('libs ok')"
python3 -c "import ast; ast.parse(open('scripts/forensics.py').read()); print('forensics syntax ok')"
# End-to-end: a clean frame passes, a dirty one fails and lists cases.
python3 - <<'PY'
import pandas as pd, pandera.pandas as pa
s = pa.DataFrameSchema({"age": pa.Column(int, pa.Check.in_range(16,99))}, coerce=True)
try: s.validate(pd.DataFrame({"age":[10,200]}), lazy=True)
except pa.errors.SchemaErrors as e: print("caught", len(e.failure_cases), "failures")
PY
```

Confirm the Pointblank report renders (`dq_report.html` opens with green/red step rows) and that
`forensics.py` returns rc=1 on injected straight-liners.

## Pitfalls

- **`lazy=True` matters.** Without it Pandera raises on the first bad row and you never see the full damage.
- **`strict=True` / `coerce=True` interact.** `strict` rejects extra columns (good for contracts) but breaks on
  benign metadata columns — whitelist or drop them first. `coerce` silently casts, which can *hide* a
  string-in-numeric problem; validate dtype explicitly when the source is dirty.
- **Pointblank thresholds are fractions, not counts** (0.05 = 5% of rows), and `pb.Thresholds` order is
  warning→error→critical. Passing a bare tuple `(0.01,0.05,0.10)` also works.
- **Don't Benford bounded/assigned fields.** Likert scales, ages, ratings, sequential IDs are not
  Benford-distributed; a "fail" there is your mistake, not the data's.
- **Forensics flags ≠ verdicts.** Duplicate detection on too few key columns yields false positives (many honest
  respondents share a handful of answers); pick enough discriminating columns. Log every exclusion.
- **Survey weights:** validate the weight band (e.g. 0<w≤20) — extreme weights distort every downstream stat and
  are a classic silent data-quality failure that no dtype check catches.
- Use the right neighbour: pure warehouse typing → data-contracts/dbt; existing Great Expectations suites → keep GX.
