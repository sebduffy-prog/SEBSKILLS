"""
EDA template — produces a structured Markdown report
of summary stats, correlations, and outlier counts.

Anti-hallucination contract:
- Every statistic is computed in-session.
- Distribution shape is characterized by skew/kurtosis, not adjectives.
- Outliers use a stated rule (IQR × 1.5 by default).
"""

from pathlib import Path

import numpy as np
import pandas as pd

INPUT_PATH = Path("input.csv")
IQR_K = 1.5  # outlier rule multiplier; surface this to the user


def numeric_summary(df: pd.DataFrame) -> pd.DataFrame:
    num = df.select_dtypes(include="number")
    if num.empty:
        return pd.DataFrame()
    summary = num.describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.99]).T
    summary["skew"] = num.skew()
    summary["kurt"] = num.kurt()
    summary["null_pct"] = num.isna().mean() * 100
    return summary.round(3)


def categorical_summary(df: pd.DataFrame, top_n: int = 5) -> str:
    out: list[str] = []
    for col in df.select_dtypes(include=["object", "category"]).columns:
        s = df[col]
        out.append(f"\n**{col}** — {s.nunique(dropna=True)} unique, {s.isna().mean() * 100:.1f}% null")
        vc = s.value_counts(dropna=False).head(top_n)
        for v, c in vc.items():
            out.append(f"  - `{v!r}`: {c} ({c / len(s) * 100:.1f}%)")
    return "\n".join(out)


def correlations(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    num = df.select_dtypes(include="number")
    if num.shape[1] < 2:
        return pd.DataFrame(), pd.DataFrame()
    return num.corr().round(3), num.corr(method="spearman").round(3)


def outliers(df: pd.DataFrame, k: float = IQR_K) -> pd.DataFrame:
    num = df.select_dtypes(include="number")
    rows = []
    for col in num.columns:
        q1, q3 = num[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lo, hi = q1 - k * iqr, q3 + k * iqr
        mask = (num[col] < lo) | (num[col] > hi)
        rows.append({
            "column": col,
            "rule": f"< {lo:.3g} or > {hi:.3g}",
            "n_outliers": int(mask.sum()),
            "pct": round(mask.mean() * 100, 2),
        })
    return pd.DataFrame(rows)


def report(path: Path) -> None:
    df = pd.read_csv(path)
    print(f"# EDA report — `{path}`\n")
    print(f"**Shape**: {df.shape[0]:,} rows × {df.shape[1]} columns  •  "
          f"**Memory**: {df.memory_usage(deep=True).sum() / 1e6:.2f} MB\n")

    ns = numeric_summary(df)
    if not ns.empty:
        print("## Numeric summary\n")
        print(ns.to_markdown())

    cat = categorical_summary(df)
    if cat:
        print("\n## Categorical summary")
        print(cat)

    p, s = correlations(df)
    if not p.empty:
        print(f"\n## Correlations (Pearson, n={len(df)})\n")
        print(p.to_markdown())
        print(f"\n## Correlations (Spearman, n={len(df)})\n")
        print(s.to_markdown())

    out = outliers(df)
    if not out.empty:
        print(f"\n## Outliers (rule: IQR × {IQR_K})\n")
        print(out.to_markdown(index=False))


if __name__ == "__main__":
    report(INPUT_PATH)
