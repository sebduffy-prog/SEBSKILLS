#!/usr/bin/env python3
"""Classify distinctive brand assets on Romaniuk's Fame x Uniqueness grid and
compute a brand's mental-availability metrics from CEP association counts.

Pure stdlib (python3.9+). No mutation of caller data — returns new dicts.

DBA GRID (Romaniuk, "Building Distinctive Brand Assets"):
  Fame (Y)       = % of category buyers who link the asset to the brand.
  Uniqueness (X) = of those who link it to ANY brand, the % who link it to
                   YOUR brand only (i.e. not shared with competitors).
  Quadrants (defaults: fame >= 50%, uniqueness >= 50%):
    solid_gold          high fame, high uniqueness  -> protect + lead with it
    investment_potential low fame, high uniqueness  -> yours alone; build fame
    avoid               high fame, low uniqueness   -> famous but shared;
                                                       misattribution risk
    ignore              low fame, low uniqueness     -> retire / do not invest

Usage:
    from dba_grid import classify_asset, dba_grid, mental_metrics
"""
from __future__ import annotations

FAME_THRESHOLD = 50.0        # % of category buyers
UNIQUENESS_THRESHOLD = 50.0  # % exclusive linkage

QUADRANT_ACTIONS = {
    "solid_gold": "Protect and lead. Use consistently, never restyle casually.",
    "investment_potential": "Yours alone but under-known — invest to build fame.",
    "avoid": "Famous but shared — high misattribution risk; do not rely on it alone.",
    "ignore": "Weak and shared — retire or de-prioritise; do not spend against it.",
}


def classify_asset(fame: float, uniqueness: float,
                   fame_threshold: float = FAME_THRESHOLD,
                   uniqueness_threshold: float = UNIQUENESS_THRESHOLD) -> dict:
    """Return {quadrant, action} for one asset. fame/uniqueness are 0-100 %."""
    for value, name in ((fame, "fame"), (uniqueness, "uniqueness")):
        if not 0 <= value <= 100:
            raise ValueError(f"{name} must be 0-100, got {value}")
    hi_fame = fame >= fame_threshold
    hi_uniq = uniqueness >= uniqueness_threshold
    if hi_fame and hi_uniq:
        quadrant = "solid_gold"
    elif not hi_fame and hi_uniq:
        quadrant = "investment_potential"
    elif hi_fame and not hi_uniq:
        quadrant = "avoid"
    else:
        quadrant = "ignore"
    return {"fame": fame, "uniqueness": uniqueness,
            "quadrant": quadrant, "action": QUADRANT_ACTIONS[quadrant]}


def dba_grid(assets: dict, **thresholds) -> dict:
    """assets = {asset_name: (fame, uniqueness)}. Returns new dict of results."""
    return {name: classify_asset(f, u, **thresholds)
            for name, (f, u) in assets.items()}


def mental_metrics(brand_links: dict, category_total_links: int,
                   n_buyers: int) -> dict:
    """Compute mental-availability metrics from CEP association counts.

    brand_links          {cep_name: # buyers linking brand to that CEP}
    category_total_links total brand-CEP associations across ALL brands
    n_buyers             number of category buyers surveyed

    mental_market_share  brand's associations / all-brand associations
    network_size         avg CEPs the brand is linked to, per buyer
    mental_penetration   NOTE: needs unique-buyer data; approximated as the
                         max single-CEP linkage as a floor (see Pitfalls).
    """
    if n_buyers <= 0 or category_total_links <= 0:
        raise ValueError("n_buyers and category_total_links must be > 0")
    brand_total = sum(brand_links.values())
    return {
        "brand_associations": brand_total,
        "mental_market_share_pct": round(100 * brand_total / category_total_links, 1),
        "network_size": round(brand_total / n_buyers, 2),
        "top_cep": max(brand_links, key=brand_links.get) if brand_links else None,
        "mental_penetration_floor_pct": round(
            100 * (max(brand_links.values()) if brand_links else 0) / n_buyers, 1),
    }


if __name__ == "__main__":
    demo = {"Yellow M":(72,64),"Jingle":(58,41),"Mascot":(31,80),"Slogan":(22,18)}
    for name, res in dba_grid(demo).items():
        print(f"{name:10} {res['quadrant']:20} {res['action']}")
    print(mental_metrics({"on the go":300,"treat":210,"kids":140},
                         category_total_links=3200, n_buyers=1000))
