# Data Analysis

Skills for rigorous data work — processing, schema, exploratory analysis, statistical testing, and mathematics.

## The shared posture: NO CLAIM WITHOUT COMPUTATION

Every skill in this category enforces the same anti-hallucination contract:

| The model NEVER… | The model ALWAYS… |
|---|---|
| Describes data it has not loaded | Inspects (`shape`, `dtypes`, `isna`, `head`) before saying anything about the data |
| Reports a number it has not computed | Executes code and cites the computed value |
| Declares "significant" without running a test | Runs the appropriate test and reports effect size + CI, not just p-value |
| Solves a math problem without verification | Solves symbolically AND verifies numerically |
| Approximates ("roughly 5,000 rows") | Reports exact computed values |
| Hides failures (`try / except: pass`) | Stops on unexpected behavior and surfaces it to the user |

If the model can't execute code in the current environment, it must **say so** and either produce a script the user can run, or refuse to answer questions that require computation.

## Skills in this category

| Skill | Use when… |
|---|---|
| **data-processing** | User wants to clean, dedupe, transform, join, or reshape tabular data |
| **data-schema** | User wants to inspect an unknown dataset's schema, validate a known one, or design a new one |
| **exploratory-data-analysis** | User asks "what does this data look like" — summary stats, distributions, correlations |
| **statistical-testing** | User asks about significance, comparing groups, regression, or A/B test analysis |
| **mathematical-computation** | User asks an algebra, calculus, linear-algebra, or probability problem |

## Toolchain

- **Python 3.10+** is the assumed runtime.
- **pandas** or **polars** for tabular data. Default to pandas; switch to polars if dataset > 10M rows or user requests.
- **scipy.stats** + **statsmodels** for statistical tests.
- **sympy** for symbolic math; **numpy** for numerical verification.
- **matplotlib** for plots only when asked; verification is the default deliverable, plots are optional.

## Inputs to confirm before any work begins

Before executing anything beyond initial inspection, confirm with the user:

1. **What does success look like?** A cleaned file? A test result? A summary report?
2. **What is the source of the data?** A file path? A DataFrame already in memory? A database connection?
3. **What is the domain meaning of the columns?** Critical when the names are opaque (`val_1`, `flag_a`).
4. **What is the expected output format?** New file, in-place modification, returned object, printed report?

If the user can't answer, the skill proposes a default and asks for confirmation.

## When NOT to use this category

- **File-format I/O without analysis** — use `documents/xlsx`, `documents/pdf`, etc.
- **Visualization-only requests** — use `frontend-design` or a charting-specific skill if/when one exists.
- **General Python coding** — these skills are for *data and math reasoning*, not for arbitrary Python tasks.
