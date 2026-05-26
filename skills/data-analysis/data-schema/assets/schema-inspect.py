"""
Schema inspection — produces a Markdown table characterizing
every column in a tabular dataset.

Anti-hallucination contract:
- All values reported are computed from the actual data.
- Sample values are real (sampled with .head() / .sample()).
- Inferred type upgrades are flagged as "confirm" rather than asserted.
"""

from pathlib import Path

import pandas as pd

INPUT_PATH = Path("input.csv")


def column_report(s: pd.Series) -> dict:
    """One row of the schema table for a single column."""
    null_pct = s.isna().mean() * 100
    unique = s.nunique(dropna=True)
    notes: list[str] = []

    # Range or sample
    if pd.api.types.is_numeric_dtype(s):
        rng = f"[{s.min()}, {s.max()}]"
    elif pd.api.types.is_datetime64_any_dtype(s):
        rng = f"[{s.min()}, {s.max()}]"
    else:
        sample = s.dropna().head(2).tolist()
        rng = ", ".join(repr(v) for v in sample)

    # Candidate PK?
    if s.is_unique and s.notna().all():
        notes.append("Candidate PK")

    # Object column parseable as datetime?
    if s.dtype == "object":
        try:
            pd.to_datetime(s.dropna().head(50), errors="raise")
            notes.append("Parseable as datetime (confirm)")
        except Exception:
            pass
        try:
            pd.to_numeric(s.dropna().head(50), errors="raise")
            notes.append("Parseable as numeric (confirm)")
        except Exception:
            pass

    # Duplicates with non-null
    if not s.is_unique:
        dup_count = len(s) - unique - s.isna().sum()
        if dup_count > 0:
            notes.append(f"{dup_count} duplicated non-null values")

    if s.isna().any():
        notes.append(f"{s.isna().sum()} nulls")

    return {
        "column": s.name,
        "dtype": str(s.dtype),
        "null_pct": f"{null_pct:.1f}",
        "unique": unique,
        "range_or_sample": rng,
        "notes": "; ".join(notes) if notes else "",
    }


def to_markdown(rows: list[dict]) -> str:
    headers = ["Column", "Dtype", "Null %", "Unique", "Range / Sample", "Notes"]
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append(
            "| {column} | {dtype} | {null_pct} | {unique} | {range_or_sample} | {notes} |".format(**r)
        )
    return "\n".join(out)


def main(path: Path) -> None:
    df = pd.read_csv(path)
    print(f"# Schema report: {path}")
    print(f"\nShape: **{df.shape[0]:,} rows × {df.shape[1]} columns**\n")
    rows = [column_report(df[c]) for c in df.columns]
    print(to_markdown(rows))


if __name__ == "__main__":
    main(INPUT_PATH)
