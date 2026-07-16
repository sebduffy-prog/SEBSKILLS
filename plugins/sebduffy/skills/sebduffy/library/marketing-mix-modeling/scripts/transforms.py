#!/usr/bin/env python3
"""Media-transformation primitives for MMM sanity checks and quick prototypes.

Pure numpy (py3.9 safe, no heavy deps). These mirror the transforms used by
Meridian and PyMC-Marketing so you can eyeball adstock/saturation curves and
sanity-check a contribution decomposition BEFORE committing to a full
Bayesian fit. NOT a replacement for a proper posterior model.

Run:  python3 transforms.py --demo
"""
from __future__ import annotations
import argparse
import numpy as np


def geometric_adstock(x: np.ndarray, alpha: float, l_max: int = 12,
                      normalize: bool = True) -> np.ndarray:
    """Geometric carryover. alpha in [0,1): fraction retained each period.

    y[t] = sum_{l=0..l_max-1} w[l] * x[t-l], w[l] = alpha**l (optionally
    normalized to sum to 1 so total spend/impact is conserved).
    """
    if not 0.0 <= alpha < 1.0:
        raise ValueError("alpha must be in [0, 1)")
    weights = alpha ** np.arange(l_max)
    if normalize:
        weights = weights / weights.sum()
    out = np.zeros_like(x, dtype=float)
    for lag, w in enumerate(weights):
        out[lag:] += w * x[: len(x) - lag]
    return out


def hill_saturation(x: np.ndarray, half_sat: float, slope: float = 1.0) -> np.ndarray:
    """Hill / logistic-style diminishing returns, output in [0,1).

    y = x**slope / (half_sat**slope + x**slope). half_sat is the spend level
    at which response reaches 50% of its asymptote.
    """
    if half_sat <= 0:
        raise ValueError("half_sat must be > 0")
    xp = np.power(np.clip(x, 0, None), slope)
    return xp / (half_sat ** slope + xp)


def logistic_saturation(x: np.ndarray, lam: float) -> np.ndarray:
    """PyMC-Marketing LogisticSaturation: (1 - exp(-lam*x)) / (1 + exp(-lam*x))."""
    if lam <= 0:
        raise ValueError("lam must be > 0")
    return (1 - np.exp(-lam * x)) / (1 + np.exp(-lam * x))


def contribution_share(contributions: dict[str, float]) -> dict[str, float]:
    """Normalize per-channel incremental contributions to % of modelled outcome."""
    total = sum(contributions.values())
    if total == 0:
        raise ValueError("total contribution is zero")
    return {k: v / total for k, v in contributions.items()}


def roi(contribution: float, spend: float) -> float:
    """Return-on-investment = incremental outcome / spend. Watch units."""
    if spend <= 0:
        raise ValueError("spend must be > 0")
    return contribution / spend


def _demo() -> None:
    rng = np.random.default_rng(0)
    spend = rng.uniform(0, 100, size=52)
    carried = geometric_adstock(spend, alpha=0.6, l_max=8)
    saturated = hill_saturation(carried, half_sat=40, slope=1.3)
    print("weeks:", len(spend))
    print("adstock conserves total (normalized):",
          round(spend.sum(), 2), "->", round(carried.sum(), 2))
    print("saturation range:", round(saturated.min(), 3), "-", round(saturated.max(), 3))
    contribs = {"tv": 120_000.0, "social": 60_000.0, "search": 90_000.0}
    shares = contribution_share(contribs)
    print("contribution shares:", {k: round(v, 3) for k, v in shares.items()})
    print("tv ROI:", round(roi(contribs["tv"], spend=300_000.0), 3))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        _demo()
    else:
        ap.print_help()
