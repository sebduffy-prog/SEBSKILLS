---
name: raw-data-research
description: |
  Write and execute scripts to parse, clean, normalise and
  triangulate large volumes of raw data — messy CSVs, multi-tab
  XLSX exports, JSON dumps, NDJSON streams, PDF reports, scraped
  HTML, RSS / Atom feeds, social listening exports, search-trend
  CSVs, transcript dumps, tracker raw exports, panel data, ad
  spend pulls, sales data, log files. The output is a *clean,
  documented, analysis-ready artefact* (parquet, CSV, JSON,
  SQLite) plus a one-page provenance note. This is the pipeline
  layer that sits *before* [[data-analyst]] and
  [[data-cut-headline-stats]]. Trigger on phrases like "parse
  this data", "clean this file", "the raw data is messy",
  "normalise this", "join these files", "extract from PDFs",
  "scrape this", "stitch these exports together", "pull this
  apart", "wrangle this", "build a dataset", "make this
  analysis-ready", "raw data research", "data research",
  "process this dump", "consolidate these spreadsheets", "OCR
  these reports", "extract tables from PDF", "JSON to CSV",
  "transcripts to dataframe", "I have 200 files", "explode this
  dump", "long-form to wide-form", "wide-to-long", "pivot this".
  Trigger even when the user just says "do something useful with
  this folder of files". Pairs with [[data-analyst]] (next step),
  [[data-cut-headline-stats]] (for editorial cut), and the
  `xlsx` / `pdf` skills (for format-specific I/O).
---

# Raw data research

Most "data research" requests in advertising land are not
analysis — they're **pipeline**. Someone has dropped 47 PDF
reports, three XLSX exports with different column names, a JSON
dump from the panel provider, and a folder of HTML pages. The
job is to turn that into one clean, analysis-ready dataset with
a known provenance.

This skill writes and executes the scripts that do that.

## When to use

- The user has handed over a folder of files that need to be
  consolidated
- A tracker / panel / ad-spend export is in the wrong shape
- A PDF has tables the planner needs as a spreadsheet
- A research team has 100 transcripts and needs them coded by
  speaker / theme / topic
- Brand mentions need to be pulled from a social listening JSON
- Sales / panel data from multiple regions/months/SKUs needs
  stitching with consistent keys
- Web pages, RSS, or APIs need scraping into a structured table
- A YouGov / Kantar / GWI cut needs reshaping to long-form

**Don't use this skill** for: statistical analysis (use
[[data-analyst]]), strategic interpretation (use
[[strategy-analyst]]), or building dashboards (a separate
engineering job).

## The discipline

### 1. Map the inputs before writing code

Open the first file. Open the last file. Open one from the
middle. Write down:

```
Format:          [csv / xlsx / json / pdf / html / ndjson / parquet]
Granularity:     [one row = ...]
Time key:        [field, format, timezone]
Entity key:      [the natural key that joins to other files]
Schema:          [columns / fields, types]
Encoding:        [utf-8 / latin-1 / cp1252]
Header rows:     [row index where data begins]
Junk rows:       [totals, subtotals, page breaks]
Sample rows:     [3–5 rows of actual data]
```

The "junk rows" line is the one most pipelines fail on.
Tracker exports especially love mid-table subtotals.

### 2. Write the pipeline as four discrete stages

```
discover  →  ingest  →  normalise  →  publish
```

Don't fuse stages. A pipeline that does everything in one script
is impossible to debug.

```python
# project layout
data/
  raw/                  # untouched copies of inputs
  interim/              # post-ingest, pre-normalise
  processed/            # the publishable artefact
scripts/
  01_discover.py        # list files, print schemas
  02_ingest.py          # read raw → interim with minimal change
  03_normalise.py       # interim → processed (clean schema)
  04_publish.py         # processed → parquet/csv + provenance.md
```

### 3. Ingest defensively

Most failures come from assumptions the input file silently
breaks: encodings, headers in the wrong row, mixed types, comma
vs semicolon, dates as Excel serials, "1,234" with thousands
separators, "—" / "N/A" / "n/a" / "" all meaning missing.

```python
import pandas as pd

df = pd.read_csv(
    path,
    encoding="utf-8-sig",       # strips BOM if present
    sep=None, engine="python",  # auto-detect delim
    dtype=str,                  # read everything as string first
    na_values=["", "N/A", "n/a", "-", "—", "NULL", "null", "."],
    keep_default_na=False,
)
```

For XLSX with multiple sheets / dodgy headers:

```python
xls = pd.ExcelFile(path)
for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet,
                       header=None, dtype=str)
    # find the header row programmatically
    header_row = df.apply(lambda r: r.notna().sum(), axis=1).idxmax()
    df.columns = df.iloc[header_row]
    df = df.iloc[header_row+1:].reset_index(drop=True)
```

### 4. Normalise to a *single* schema

The processed artefact has one row-per-thing, lowercase
snake_case columns, ISO dates, typed numerics, and a `source`
column carrying the file of origin. Always carry provenance
through normalisation.

```python
out = (
    raw
    .rename(columns=str.lower)
    .rename(columns=lambda c: c.strip().replace(" ", "_"))
    .assign(
        date=lambda d: pd.to_datetime(d["date"], format="%d/%m/%Y", errors="coerce"),
        spend_gbp=lambda d: pd.to_numeric(
            d["spend"].str.replace(",", "").str.replace("£", ""),
            errors="coerce"),
        source=path.name,
    )
    .dropna(subset=["date"])     # rows we couldn't date — flag, don't silently drop without counting
)
```

Count what you drop. **Always.**

```python
dropped = before_n - len(out)
print(f"dropped {dropped} rows that failed date parsing ({dropped/before_n:.1%})")
```

### 5. Validate the result

Every pipeline ends with a validation pass:

```python
assert out["date"].notna().all(), "date column still has NaT"
assert out["spend_gbp"].dtype.kind == "f", "spend_gbp not numeric"
assert out["entity_id"].is_unique or out.duplicated(subset=["entity_id","date"]).sum()==0, \
    "duplicate keys"
assert (out["spend_gbp"] >= 0).all(), "negative spend"
# Sanity: row counts roughly match input
assert abs(len(out) - expected_n)/expected_n < 0.05, "row count drift > 5%"
```

If a check fails, **stop the pipeline and surface the row**, do
not silently fix it. Silent fixes accumulate into nonsense.

### 6. Publish with provenance

```
processed/
  campaign_spend_2023_2025.parquet
  campaign_spend_2023_2025.csv
  provenance.md
```

The provenance note is one page. It contains:

- Inputs: list of source files, dates, who provided them
- Transformations: what was joined, renamed, dropped, why
- Row counts: in → out, with the diff explained
- Schema: column, type, definition, example
- Known issues: anything wonky the analyst should know
- How to re-run: the single command

A dataset without provenance dies the moment the analyst leaves.

## Common ingestion playbooks

### Multi-file XLSX consolidation

```python
from pathlib import Path
import pandas as pd

frames = []
for f in Path("data/raw").glob("*.xlsx"):
    df = pd.read_excel(f, sheet_name="Data", header=4)
    df["source_file"] = f.name
    frames.append(df)
df = pd.concat(frames, ignore_index=True)
```

### PDF tables → DataFrame

```python
# Use camelot for clean table-extraction, fallback to pdfplumber
import camelot
tables = camelot.read_pdf("report.pdf", pages="all", flavor="lattice")
df = pd.concat([t.df for t in tables], ignore_index=True)
```

For scanned PDFs, prefer the `pdf` skill (handles OCR).

### Scraping pages → table

```python
import httpx
from bs4 import BeautifulSoup
import pandas as pd

with httpx.Client(headers={"User-Agent": "..."}, timeout=20) as cli:
    rows = []
    for url in urls:
        r = cli.get(url); r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        rows.append({
            "url": url,
            "title": soup.find("h1").get_text(strip=True),
            "date":  soup.find("time").get("datetime"),
            "body":  " ".join(p.get_text(strip=True) for p in soup.find_all("p")),
        })
df = pd.DataFrame(rows)
```

Respect `robots.txt`, rate-limit (`time.sleep(0.5)`), and cache
responses to disk so re-runs don't re-fetch.

### Social listening JSON → analysis-ready

```python
import pandas as pd
df = pd.read_json("brandwatch_export.ndjson", lines=True)
df = (df
    .assign(
      date=pd.to_datetime(df["created_at"]),
      brand=df["matched_keywords"].str[0],
      sentiment=df["sentiment_label"].map({"positive":1,"neutral":0,"negative":-1}),
    )
    .loc[:, ["date","platform","brand","author","text","sentiment","reach"]]
)
```

### Transcripts → speaker / theme dataframe

```python
import re
import pandas as pd
from pathlib import Path

rows = []
for f in Path("transcripts").glob("*.txt"):
    for m in re.finditer(r"^\[(\d{2}:\d{2}:\d{2})\]\s+([A-Z][^:]+):\s+(.+)$",
                         f.read_text(), re.M):
        rows.append({
          "file": f.name, "ts": m.group(1),
          "speaker": m.group(2).strip(), "text": m.group(3).strip(),
        })
df = pd.DataFrame(rows)
```

For LLM-assisted theme coding, feed the speaker turns to a
batch Claude API call (see [[qualitative-research]] for the
coding scheme) — keep the raw and coded versions separate.

### Long ↔ wide reshapes

```python
long_df = wide_df.melt(id_vars=["wave","brand"], var_name="metric", value_name="value")
wide_df = long_df.pivot_table(index=["wave","brand"], columns="metric", values="value")
```

### >1M rows — use DuckDB

```python
import duckdb
con = duckdb.connect()
df = con.sql("""
  SELECT date, brand, SUM(spend_gbp) AS spend
  FROM read_parquet('data/processed/spend_*.parquet')
  WHERE date >= '2024-01-01'
  GROUP BY 1,2
  ORDER BY 1,2
""").df()
```

DuckDB will read directly from the filesystem without loading
everything into memory.

## Scripts the skill writes — naming and structure

Use these file names so the next person can pick up the work:

```
scripts/
  01_discover.py        # list inputs, profile schemas, no transformation
  02_ingest_<source>.py # one per source family (tracker, spend, sales…)
  03_join.py            # bring sources together on the natural key
  04_clean.py           # final cleaning + validation
  05_export.py          # write parquet/csv + provenance.md
  utils/
    io.py               # reusable readers, encoding sniffers, junk-row finders
    keys.py             # entity ID normalisation
    dates.py            # date parsing & timezone normalisation
    text.py             # text cleaning helpers
```

Every script:

- Reads from `data/<previous-stage>/`, writes to `data/<this-stage>/`
- Is idempotent (re-running produces the same output)
- Logs the row count in and out
- Has a `--dry-run` flag that prints stats without writing
- Uses `argparse` rather than hard-coded paths

## Output deliverable

The skill returns:

1. **The processed dataset** (`parquet` + `csv` mirror)
2. **`provenance.md`** — one page
3. **`README.md`** in the project root — how to run it
4. **`scripts/`** — the actual pipeline, runnable end-to-end
5. **A summary message** to the user:

```
PROCESSED DATASET
File: data/processed/<name>.parquet (NN rows × M cols)
Sources: [list]
Time range: [start → end]
Natural key: [field(s)]
Dropped: NN rows ([reason])
Known issues: [list]
Next step: hand to [[data-analyst]] for [the analytic question]
```

## Common pipeline traps to avoid

1. **Implicit dtype coercion.** Reading `id_001234` as int and
   losing the leading zero. Read everything as string first.
2. **Excel date serials.** `45123` is an Excel date, not a count
   of anything. Convert with `pd.to_datetime(x, unit="D",
   origin="1899-12-30")`.
3. **Encoding mismatches.** A file that looks fine but contains
   `â€™` instead of `'` is `cp1252` saved as `utf-8`. Open with
   `encoding="cp1252"`.
4. **Merging on cleaned vs uncleaned keys.** `BRAND_A` vs
   `Brand A` won't join. Normalise keys before any join.
5. **Silent dedup that drops the wrong duplicate.** Choose the
   "keep" rule deliberately (`keep="last"` if newer overrides).
6. **Joining tables with different time granularities.** A
   weekly metric joined to a daily metric must be either upsampled
   or aggregated, deliberately.
7. **Timezone soup.** Always normalise to UTC at ingest, convert
   to local on display only.
8. **Wide tables of "competitor 1, competitor 2, competitor 3"**.
   Melt to long; you can't join a brand-keyed table to a column.
9. **No provenance.** The analyst will trust the data only if
   they can see where each row came from. Always carry
   `source_file`.
10. **One-script pipelines.** Split discover / ingest / normalise
    / publish into separate scripts.

## When to reach for which library

| Task | Tool |
|---|---|
| Tabular >100k rows | pandas |
| Tabular >1M rows | duckdb on parquet |
| Streaming JSON / NDJSON | `ijson` or line-by-line read |
| Excel multi-sheet | `openpyxl` (read-only mode for huge files) |
| PDF tables (digital) | `camelot` (lattice for grid tables, stream for flow) |
| PDF tables (scanned) | OCR via `tesseract` then `camelot` (or use the `pdf` skill) |
| HTML scraping | `httpx` + `beautifulsoup4` |
| Headless browser | `playwright` (for JS-rendered pages) |
| Word docs | `python-docx` (use the `docx` skill) |
| YouTube transcripts | `youtube-transcript-api` |
| LLM-assisted parsing of messy text | Anthropic SDK with batch jobs |

## Handoffs

- Once the processed dataset is published, hand to
  [[data-analyst]] for proper analysis
- For headline-stat cuts off the processed data, hand to
  [[data-cut-headline-stats]]
- For qual transcripts, hand to [[qualitative-research]] for
  the coding scheme
- For sector-wide research that consumes scraped sources, hand to
  [[developed-research]]
- For visualisation, [[vccp-media-design]]'s matplotlib config
