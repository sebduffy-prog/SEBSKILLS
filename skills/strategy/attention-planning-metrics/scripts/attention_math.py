#!/usr/bin/env python3
"""Attention-planning math: convert vendor attention metrics into planning currency.

Grounded formulas (Lumen / industry standard):
  APM  = %viewed * average view time (seconds)   -> attentive seconds per 000 impressions
  aCPM = CPM / APM                                -> cost per attentive second-thousand
  attention-adjusted impressions = impressions * (%viewed) [reach quality proxy]

No third-party deps. Python 3.9+. All functions are pure (no mutation).
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Placement:
    name: str
    cpm: float            # media cost per 1000 impressions (£/$)
    pct_viewed: float     # 0-1, share of impressions actually seen (Lumen %viewed)
    avg_view_time_s: float  # average attentive seconds when seen (dwell)


def apm(pct_viewed: float, avg_view_time_s: float) -> float:
    """Attentive seconds per 1000 impressions = %viewed * avg view time * 1000."""
    if not 0 <= pct_viewed <= 1:
        raise ValueError(f"pct_viewed must be 0-1, got {pct_viewed}")
    if avg_view_time_s < 0:
        raise ValueError("avg_view_time_s must be >= 0")
    return pct_viewed * avg_view_time_s * 1000.0


def acpm(cpm: float, apm_value: float) -> float:
    """Cost per 1000 attentive seconds = CPM / APM. Lower is better value."""
    if apm_value <= 0:
        raise ValueError("APM must be > 0 to compute aCPM")
    return cpm / apm_value * 1000.0


def evaluate(p: Placement) -> dict:
    a = apm(p.pct_viewed, p.avg_view_time_s)
    return {
        "name": p.name,
        "apm_sec_per_000": round(a, 1),
        "acpm": round(acpm(p.cpm, a), 4),
        "attentive_impr_per_000": round(p.pct_viewed * 1000, 0),
    }


def rank(placements: list[Placement]) -> list[dict]:
    """Rank placements by best (lowest) aCPM — attention value for money."""
    scored = [evaluate(p) for p in placements]
    return sorted(scored, key=lambda r: r["acpm"])


if __name__ == "__main__":
    demo = [
        Placement("Online video 15s", cpm=12.0, pct_viewed=0.55, avg_view_time_s=2.4),
        Placement("Standard display MPU", cpm=2.5, pct_viewed=0.35, avg_view_time_s=0.9),
        Placement("Social in-feed", cpm=8.0, pct_viewed=0.62, avg_view_time_s=1.3),
    ]
    for row in rank(demo):
        print(f"{row['name']:<22} APM={row['apm_sec_per_000']:>7} "
              f"aCPM={row['acpm']:>8}  (best value first)")
