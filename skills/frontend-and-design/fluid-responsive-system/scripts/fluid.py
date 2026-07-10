#!/usr/bin/env python3
"""Generate Utopia-style fluid CSS clamp() custom properties.

Fluid type + space that interpolates smoothly between a min viewport and a max
viewport with no media queries. Math is identical to utopia.fyi:

    slope     = (maxSize - minSize) / (maxVw - minVw)          # px per px
    intercept = minSize - minVw * slope                        # px
    clamp(minSize_rem, intercept_rem + slope*100 vw, maxSize_rem)

Sizes are entered in px (design units) and emitted in rem (accessible: scales
with the user's root font-size). Defaults follow Utopia's 320->1240px range.

Usage:
    python3 fluid.py                          # demo scale to stdout
    python3 fluid.py --min-vw 320 --max-vw 1240 \
        --min-base 18 --max-base 20 \
        --min-ratio 1.2 --max-ratio 1.25 \
        --steps -2,-1,0,1,2,3,4,5
"""
import argparse

REM = 16.0  # CSS root px-per-rem (do not change unless :root font-size differs)


def clamp(min_px: float, max_px: float, min_vw: float, max_vw: float) -> str:
    """Return a CSS clamp() string fluid between min_vw and max_vw."""
    if max_vw == min_vw:
        raise ValueError("min-vw and max-vw must differ")
    slope = (max_px - min_px) / (max_vw - min_vw)
    intercept_px = min_px - min_vw * slope
    lo, hi = sorted((min_px / REM, max_px / REM))
    return (
        f"clamp({lo:.4g}rem, "
        f"{intercept_px / REM:.4g}rem + {slope * 100:.4g}vw, "
        f"{hi:.4g}rem)"
    )


def modular(base: float, ratio: float, step: int) -> float:
    """Size at `step` on a modular scale (step 0 == base)."""
    return base * (ratio ** step)


def type_scale(args) -> list[tuple[str, str]]:
    steps = [int(s) for s in args.steps.split(",")]
    rows = []
    for step in steps:
        min_px = modular(args.min_base, args.min_ratio, step)
        max_px = modular(args.max_base, args.max_ratio, step)
        name = f"--step-{step}" if step >= 0 else f"--step--{abs(step)}"
        rows.append((name, clamp(min_px, max_px, args.min_vw, args.max_vw)))
    return rows


def space_scale(args) -> list[tuple[str, str]]:
    # Space multiples of the base text size, Utopia's default T-shirt sizes.
    mults = {"3xs": 0.25, "2xs": 0.5, "xs": 0.75, "s": 1.0,
             "m": 1.5, "l": 2.0, "xl": 3.0, "2xl": 4.0, "3xl": 6.0}
    rows = []
    for name, mult in mults.items():
        min_px = args.min_base * mult
        max_px = args.max_base * mult
        rows.append((f"--space-{name}", clamp(min_px, max_px, args.min_vw, args.max_vw)))
    return rows


def main():
    p = argparse.ArgumentParser(description="Generate fluid clamp() tokens.")
    p.add_argument("--min-vw", type=float, default=320)
    p.add_argument("--max-vw", type=float, default=1240)
    p.add_argument("--min-base", type=float, default=18, help="base font px at min-vw")
    p.add_argument("--max-base", type=float, default=20, help="base font px at max-vw")
    p.add_argument("--min-ratio", type=float, default=1.2)
    p.add_argument("--max-ratio", type=float, default=1.25)
    p.add_argument("--steps", default="-2,-1,0,1,2,3,4,5")
    args = p.parse_args()

    print(":root {")
    print("  /* Fluid type scale */")
    for name, val in type_scale(args):
        print(f"  {name}: {val};")
    print("\n  /* Fluid space scale */")
    for name, val in space_scale(args):
        print(f"  {name}: {val};")
    print("}")


if __name__ == "__main__":
    main()
