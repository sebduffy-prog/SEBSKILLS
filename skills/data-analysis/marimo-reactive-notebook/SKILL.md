---
name: marimo-reactive-notebook
category: data-analysis
description: >
  Build reactive Python notebooks with marimo — notebooks stored as plain .py (git-diffable, importable,
  no hidden state), where changing one cell automatically re-runs everything that depends on it, and which deploy
  as interactive web apps or run as scripts. Use this whenever someone wants a "notebook" that isn't a
  reproducibility nightmare, says "marimo", "reactive notebook", "Jupyter but git-friendly", "turn this analysis
  into an app", "interactive data app with sliders", or wants a shareable analysis with UI widgets. Reach for it
  over Jupyter when reproducibility, version control, or app-deployment matter.
when_to_use:
  - Building a data analysis/notebook you want version-controlled and reproducible (no hidden out-of-order state)
  - Turning an analysis into an interactive web app with sliders/dropdowns/tables
  - Sharing a runnable notebook that also works as a plain Python script / import
  - Replacing a messy Jupyter notebook that breaks on re-run
when_not_to_use:
  - One-off throwaway exploration where a plain script is enough
  - A polished data dashboard for non-technical viewers → use quick-dashboard or living-dashboard
  - Heavy ETL pipelines / scheduled jobs → use dagster-asset-pipelines or dlt-python-pipelines
  - You specifically need the Jupyter ecosystem / an existing .ipynb workflow
keywords: [marimo, reactive notebook, python notebook, jupyter alternative, git-diffable, reproducible, data app, interactive, ui widgets, wasm, notebook as script, .py notebook, dataflow]
similar_to: [quick-dashboard, duckdb-analytics, polars-dataframes, exploratory-data-analysis]
inputs_needed:
  - The analysis or data to put in the notebook (CSV/DataFrame/query)
  - Whether it should ship as an interactive app, a script, or both
  - Any parameters users should control via widgets (date range, segment, threshold)
produces: A reactive .py marimo notebook, runnable as a script and deployable as an interactive web app
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# marimo reactive notebooks

marimo notebooks are pure `.py` files with a reactive dataflow: it parses the dependency graph between cells, so
editing or deleting a cell re-runs exactly what depends on it — **no stale state, no run-cells-out-of-order
bugs**. The same file is git-diffable, importable, runnable as a script, and deployable as an app.

## When to use

When a notebook needs to be reproducible, version-controlled, or shipped as an app. For a viewer-facing dashboard
use `quick-dashboard`; for pipelines use `dagster-asset-pipelines`.

## Prerequisites

```bash
python3 -m pip install --user marimo
marimo new            # scaffold, or:  marimo edit analysis.py   # open the editor
```

## Author

Each cell is a function; marimo wires dependencies from the variables you use. UI elements are reactive values:

```python
import marimo

app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import polars as pl
    return mo, pl


@app.cell
def _(mo):
    # a control — its .value flows into any cell that reads it
    seg = mo.ui.dropdown(["all", "new", "lapsed"], value="all", label="Segment")
    seg
    return (seg,)


@app.cell
def _(mo, pl, seg):
    # re-runs automatically whenever `seg` changes
    df = pl.read_csv("sales.csv")
    view = df if seg.value == "all" else df.filter(pl.col("segment") == seg.value)
    mo.md(f"**{len(view):,} rows** in segment *{seg.value}*")   # reactive markdown
    return df, view


if __name__ == "__main__":
    app.run()
```

Rules that give you reproducibility: **no variable is defined in two cells**, and there are **no cycles** — marimo
enforces both, which is exactly what stops Jupyter-style hidden state.

## Run / ship

```bash
marimo run analysis.py            # serve as an interactive web app (read-only for viewers)
python analysis.py                # run headless as a normal script
marimo export html-wasm analysis.py -o site   # static, runs fully in-browser (WASM), no server
```

## Verify

- Delete/re-run any cell → dependent cells update and there's no stale value (the reactive guarantee).
- `python analysis.py` runs clean (it's valid Python).
- `marimo run` serves an app where the widgets actually drive the outputs.

## Pitfalls

- **One definition per variable** — reusing a name across cells is an error by design; rename instead.
- **Expensive cells re-run on dependency change** — cache heavy work with `@mo.cache` / `functools.lru_cache` or gate it behind a `mo.ui.run_button`.
- **Not a substitute for a real dashboard** — `marimo run` is great for analysts; for polished client-facing viz use `quick-dashboard`/`living-dashboard`.
- **WASM export** can't use packages with C extensions that aren't pyodide-supported — check before relying on it.
