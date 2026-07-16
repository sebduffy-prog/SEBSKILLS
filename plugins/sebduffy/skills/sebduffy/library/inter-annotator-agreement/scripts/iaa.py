#!/usr/bin/env python3
"""Inter-annotator agreement from long-format labels.

Input CSV columns (default): unit,rater,label
  - unit  : id of the item being labelled
  - rater : id of the annotator (or "judge" for an LLM judge)
  - label : the assigned category / score

Outputs Krippendorff's alpha (with bootstrap CI), Fleiss' kappa,
mean pairwise Cohen's kappa, plus an adjudication queue of the units
where annotators disagreed — the items a human should resolve.

Deps: numpy, pandas, statsmodels, krippendorff
  python3 -m pip install numpy pandas statsmodels krippendorff

Usage:
  python3 iaa.py labels.csv --level nominal
  python3 iaa.py labels.csv --level ordinal --order low,med,high
  python3 iaa.py labels.csv --unit item_id --rater judge --label verdict --queue adj.csv
"""
import argparse
import sys

import numpy as np
import pandas as pd


def build_matrix(df, unit_col, rater_col, label_col, order=None):
    """Return (raters x units) matrix, code->label map, and the wide frame.

    Missing cells (a rater did not label a unit) become np.nan, which
    Krippendorff's alpha handles natively.
    """
    labels = pd.unique(df[label_col].dropna())
    if order:
        missing = [l for l in labels if l not in order]
        if missing:
            sys.exit(f"--order is missing labels present in data: {missing}")
        ordered = order
    else:
        ordered = sorted(labels, key=str)
    code = {lab: i for i, lab in enumerate(ordered)}
    inv = {i: lab for lab, i in code.items()}

    wide = df.pivot_table(
        index=rater_col, columns=unit_col, values=label_col,
        aggfunc="first",
    )
    elementwise = wide.map if hasattr(wide, "map") else wide.applymap
    coded = elementwise(lambda x: code.get(x, np.nan))
    return coded.to_numpy(dtype=float), inv, wide


def bootstrap_alpha(matrix, level, n=1000, seed=0):
    """Percentile bootstrap CI for alpha by resampling units (columns)."""
    import krippendorff
    rng = np.random.default_rng(seed)
    n_units = matrix.shape[1]
    vals = []
    for _ in range(n):
        idx = rng.integers(0, n_units, n_units)
        sample = matrix[:, idx]
        try:
            vals.append(krippendorff.alpha(
                reliability_data=sample, level_of_measurement=level))
        except Exception:
            continue
    if not vals:
        return (float("nan"), float("nan"))
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def fleiss(df, unit_col, rater_col, label_col):
    from statsmodels.stats.inter_rater import aggregate_raters, fleiss_kappa
    wide = df.pivot_table(
        index=unit_col, columns=rater_col, values=label_col, aggfunc="first")
    # aggregate_raters needs equal raters per subject; drop incomplete rows.
    complete = wide.dropna()
    if complete.empty:
        return None, 0
    table, _ = aggregate_raters(complete.to_numpy())
    return float(fleiss_kappa(table)), len(complete)


def mean_cohen(matrix):
    """Mean Cohen's kappa over all rater pairs (units both rated)."""
    from statsmodels.stats.inter_rater import cohens_kappa
    n_raters = matrix.shape[0]
    ks = []
    for i in range(n_raters):
        for j in range(i + 1, n_raters):
            mask = ~np.isnan(matrix[i]) & ~np.isnan(matrix[j])
            if mask.sum() < 2:
                continue
            a, b = matrix[i, mask], matrix[j, mask]
            cats = sorted(set(a) | set(b))
            tbl = pd.crosstab(
                pd.Categorical(a, cats), pd.Categorical(b, cats), dropna=False
            ).to_numpy()
            try:
                ks.append(cohens_kappa(tbl).kappa)
            except Exception:
                continue
    return float(np.mean(ks)) if ks else None


def adjudication_queue(df, unit_col, rater_col, label_col):
    """Units where labels are not unanimous, with the vote breakdown."""
    rows = []
    for unit, g in df.groupby(unit_col):
        vc = g[label_col].value_counts()
        if len(vc) > 1:
            majority = vc.idxmax()
            tie = (vc == vc.max()).sum() > 1
            rows.append({
                unit_col: unit,
                "n_labels": int(vc.sum()),
                "distinct": int(len(vc)),
                "majority": None if tie else majority,
                "tie": tie,
                "votes": "; ".join(f"{k}:{v}" for k, v in vc.items()),
            })
    return pd.DataFrame(rows)


def interpret(alpha):
    if alpha is None or np.isnan(alpha):
        return "n/a"
    if alpha >= 0.8:
        return "reliable"
    if alpha >= 0.667:
        return "tentative (use with caution)"
    return "unreliable — revise guidelines / retrain"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--unit", default="unit")
    ap.add_argument("--rater", default="rater")
    ap.add_argument("--label", default="label")
    ap.add_argument("--level", default="nominal",
                    choices=["nominal", "ordinal", "interval", "ratio"])
    ap.add_argument("--order", default=None,
                    help="comma list fixing ordinal/interval label order, "
                         "e.g. low,med,high")
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--queue", default=None,
                    help="write adjudication queue CSV to this path")
    args = ap.parse_args()

    import krippendorff  # fail early with clear message if absent

    df = pd.read_csv(args.csv)
    for c in (args.unit, args.rater, args.label):
        if c not in df.columns:
            sys.exit(f"column '{c}' not in {list(df.columns)}")

    order = args.order.split(",") if args.order else None
    matrix, inv, _ = build_matrix(df, args.unit, args.rater, args.label, order)
    n_raters, n_units = matrix.shape

    alpha = krippendorff.alpha(
        reliability_data=matrix, level_of_measurement=args.level)
    lo, hi = bootstrap_alpha(matrix, args.level, args.bootstrap)
    fk, n_complete = fleiss(df, args.unit, args.rater, args.label)
    mck = mean_cohen(matrix)
    queue = adjudication_queue(df, args.unit, args.rater, args.label)

    print(f"units={n_units}  raters={n_raters}  level={args.level}")
    print(f"Krippendorff alpha = {alpha:.3f}  "
          f"95% CI [{lo:.3f}, {hi:.3f}]  -> {interpret(alpha)}")
    if fk is not None:
        print(f"Fleiss kappa       = {fk:.3f}  (over {n_complete} fully-rated units)")
    if mck is not None:
        print(f"Mean pairwise Cohen kappa = {mck:.3f}")
    print(f"Adjudication queue : {len(queue)} of {n_units} units disagree")

    if args.queue and not queue.empty:
        queue.to_csv(args.queue, index=False)
        print(f"  wrote -> {args.queue}")


if __name__ == "__main__":
    main()
