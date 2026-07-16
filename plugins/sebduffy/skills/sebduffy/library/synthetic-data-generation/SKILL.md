---
name: synthetic-data-generation
category: data-analysis
description: >
  Generate realistic synthetic datasets that preserve the statistical structure of a real table — reach for
  SDV (GaussianCopula / CTGAN / TVAE single-table, HMA multi-table) to learn column distributions and
  correlations then sample new rows, enforce business rules with sdv.cag constraints, and PROVE fidelity +
  privacy with run_diagnostic / evaluate_quality. For synthetic free text (support tickets, reviews, chat) use
  a schema-validated LLM generation loop. Use whenever you need share-safe test/demo data, a bigger training
  set, or to fill a table you can't release.
when_to_use:
  - You need fake-but-realistic tabular data that keeps real column distributions and correlations (demo, test, staging)
  - The real data is sensitive (PII, survey respondents, financials) and cannot be shared, but a stand-in is needed
  - You want to augment a small training/eval set with extra rows that behave like the originals
  - You must prove the synthetic copy is both statistically faithful AND not leaking real rows
  - You need synthetic free-text records (tickets, reviews, prompts) that conform to a fixed JSON schema
when_not_to_use:
  - You only need arbitrary throwaway rows with no fidelity requirement — use Faker or polars-dataframes directly
  - You are VALIDATING data quality, not generating — use data-quality-validation (Pandera/Pointblank)
  - You want to mask/redact real rows in place (format-preserving) rather than resample — that is tokenisation, not this
  - You need a huge deterministic fixture for load testing only — a Faker/random loop is simpler than a fitted model
keywords: [synthetic-data, sdv, ctgan, tvae, gaussian-copula, tabular, privacy, fidelity, data-augmentation, faker, llm-generation, differential-privacy, hma, metadata, constraints]
similar_to: [data-quality-validation, data-contracts, polars-dataframes, duckdb-analytics, exploratory-data-analysis]
inputs_needed: Path to the real table (CSV/Parquet/dataframe); which columns are ids/categoricals/datetimes/sensitive; how many synthetic rows you want; any hard business rules (col A < col B, positive, allowed combos); and whether you need a privacy guarantee. For text, the JSON schema + a few seed examples.
produces: A fitted synthesizer (.pkl), a synthetic CSV/Parquet of the requested size, and a quality + diagnostic score report (0-100 fidelity, privacy pass/fail). For text, a JSON/JSONL of schema-valid synthetic records.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Synthetic Data Generation

Two jobs under one roof. **Tabular** — fit a generative model to a real table and sample new rows that keep
the marginals AND the joint correlations, then measure how faithful and how private the copy is. **Text** —
loop an LLM under a fixed JSON schema so every generated record validates. Never eyeball "looks fine"; the
whole point of this skill is that synthetic data comes with a *proof* attached.

## When to use

Reach here when you need share-safe data that still behaves like the real thing: demo/staging fills, training
augmentation, or a releasable stand-in for a sensitive table. If fidelity does not matter (pure load-test
fixtures, obviously fake names) a Faker loop is cheaper — see Pitfalls.

## Prerequisites

- **SDV** (tabular): `pip install sdv` — MIT-licensed, `sdv.version.community`. GaussianCopula is pure
  NumPy/SciPy and works on this Mac's py3.9 with no GPU. **CTGAN/TVAE pull in PyTorch** (large, slow on CPU) —
  only use them when copula fidelity is not enough.
- Real data as a pandas DataFrame (SDV consumes DataFrames, not files directly).
- **Text path**: any LLM (Claude API skill, or local). No extra install beyond `jsonschema` for validation.
- Optional `pip install sdmetrics` is bundled with sdv; `faker` only for the cheap-fixture fallback.

## Recipe 1 — Single-table synthetic (the 90% case)

```python
import pandas as pd
from sdv.metadata import Metadata
from sdv.single_table import GaussianCopulaSynthesizer
from sdv.evaluation.single_table import run_diagnostic, evaluate_quality

real = pd.read_csv("real.csv")

# 1. Metadata: auto-detect, THEN eyeball it — detection is a guess, not gospel.
metadata = Metadata.detect_from_dataframe(real)
metadata.validate()                      # raises on inconsistencies
# Fix any mislabeled column, e.g. an id read as numeric:
# metadata.update_column(column_name="user_id", sdtype="id")
# metadata.update_column(column_name="signup", sdtype="datetime",
#                        datetime_format="%Y-%m-%d")

# 2. Fit + sample
synth = GaussianCopulaSynthesizer(metadata)
synth.fit(real)
fake = synth.sample(num_rows=5000)
synth.save("model.pkl")                  # reload later: GaussianCopulaSynthesizer.load("model.pkl")
fake.to_parquet("synthetic.parquet")

# 3. PROVE it (metadata is REQUIRED on both calls)
diag = run_diagnostic(real, fake, metadata)      # structure + privacy sanity; want ~1.0
qual = evaluate_quality(real, fake, metadata)     # column shapes + pair correlations
print("diagnostic:", diag.get_score(), "quality:", qual.get_score())
```

`diagnostic` (Data Validity + Data Structure) should be **1.0** — anything less means constraints/dtypes are
being violated. `quality` is a 0–1 fidelity blend (Column Shapes + Column Pair Trends); >0.8 is usually good
enough for demo/test, aim higher for training augmentation. Drill in with
`qual.get_details("Column Shapes")` to see the worst columns.

## Recipe 2 — Enforce business rules (constraints)

Programmatic-constraint classes live in **`sdv.cag`** (current SDV; older dict-based constraints are gone).
Add them before `fit`.

```python
from sdv.cag import Inequality, ScalarRange, FixedCombinations

synth.add_constraints([
    Inequality(low_column_name="checkin", high_column_name="checkout"),
    ScalarRange(column_name="age", low_value=18, high_value=99,
                strict_boundaries=False),
    FixedCombinations(column_names=["country", "currency"]),  # never invent GB+USD
])
synth.fit(real)
```

If a rule can't be expressed as a constraint (e.g. a computed total), sample extra rows and filter, or
post-process the DataFrame — but re-run `run_diagnostic` afterwards.

## Recipe 3 — Related tables (multi-table)

```python
from sdv.metadata import Metadata
from sdv.multi_table import HMASynthesizer

# tables = {"users": df_users, "orders": df_orders}
metadata = Metadata.detect_from_dataframes(tables)
# metadata.add_relationship(parent_table_name="users", child_table_name="orders",
#     parent_primary_key="user_id", child_foreign_key="user_id")
synth = HMASynthesizer(metadata)
synth.fit(tables)
fake_tables = synth.sample()   # dict of DataFrames, FK integrity preserved
```

HMA is exact but scales poorly on wide/deep schemas — keep it to a handful of tables and modest column counts.

## Recipe 4 — Synthetic free text (schema-locked LLM loop)

For records SDV can't model (support tickets, reviews, prompts), generate with an LLM and **validate every
item against a JSON schema** so nothing malformed enters the dataset. Pattern:

```python
import json, jsonschema
schema = {"type": "object", "required": ["category", "text", "sentiment"],
          "properties": {"category": {"enum": ["billing", "bug", "how-to"]},
                         "text": {"type": "string", "minLength": 20},
                         "sentiment": {"enum": ["neg", "neu", "pos"]}}}

def keep(item):                      # gate before persisting
    try: jsonschema.validate(item, schema); return True
    except jsonschema.ValidationError: return False
```

Drive the LLM with: (a) the schema, (b) 2–4 real seed examples, (c) an explicit **diversity instruction**
("vary tone, length, product area; do not repeat phrasing"), and request a batch of JSON objects. Filter with
`keep`, then de-dup (near-duplicate collapse) — LLMs mode-collapse without a temperature/diversity nudge.
The managed alternative is **Kiln** (`pip install kiln-ai`, MIT) whose UI + `adapter_for_task` runs this loop
with topic-tree branching and human curation; use it when you want a repeatable, reviewable dataset pipeline.

## Verify

- `run_diagnostic` score **= 1.0** (structure/validity) — non-1.0 is a bug, not a taste call.
- `evaluate_quality` score meets your bar (>0.8 demo, higher for training use).
- **Privacy check**: confirm no synthetic row is a copy of a real row —
  `pd.merge(real, fake, how="inner").empty` should be `True` on the identifying columns; for a proper metric
  use `sdmetrics` `NewRowSynthesis`. Copula/CTGAN are *not* differentially private — if you need a formal
  guarantee, say so and use a DP-specific synthesizer, don't claim privacy you didn't measure.
- For text: 100% of kept records pass `jsonschema.validate`; duplicate rate below your threshold.

## Pitfalls

- **Trusting auto-detected metadata.** Ids get read as numbers, dates as strings — always `validate()` and
  eyeball before fitting, or the model learns nonsense.
- **Reaching for CTGAN first.** It needs PyTorch and CPU epochs are slow; GaussianCopula is instant and often
  enough. Escalate to CTGAN/TVAE only when quality score is too low on skewed/multimodal columns.
- **Claiming privacy for free.** SDV models can memorise rare rows. "Synthetic" ≠ "anonymous" — run the
  NewRowSynthesis / exact-match check and be honest about the absence of a DP guarantee.
- **Tiny training data.** Fitting on <~500 rows gives a model that just parrots the input (a privacy leak and
  poor generalisation). Say so rather than shipping it.
- **Using this for pure fixtures.** If you just need 10k rows of plausible-shaped junk with zero fidelity
  requirement, a `faker` loop is simpler and faster — don't fit a generative model to fake a phone number.
- **Constraints after fit.** `add_constraints` must precede `fit`; adding them after silently does nothing.
