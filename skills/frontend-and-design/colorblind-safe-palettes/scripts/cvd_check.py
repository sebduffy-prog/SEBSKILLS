#!/usr/bin/env python3
"""Colour-vision-deficiency (CVD) palette checker — pure stdlib, no deps.

Simulates protan/deutan/tritan vision with the Machado et al. 2009 severity-1.0
matrices and reports the minimum CIEDE2000 separation between every pair of
swatches, for normal vision and each CVD type. Flags pairs that collapse.

Usage:
  python3 cvd_check.py "#E69F00" "#56B4E9" "#009E73" ...
  python3 cvd_check.py --min 15 "#4477AA" "#EE6677" "#228833"

Refs: Machado, Oliveira & Fernandes 2009 (IEEE TVCG 15:6). Matrices applied to
gamma-encoded sRGB (DaltonLens convention). CIEDE2000 per Sharma et al. 2005.
"""
import sys
import math

# Machado 2009 severity-1.0 matrices (verified vs colour-science machado2010.py).
CVD = {
    "protan": [[0.152286, 1.052583, -0.204868],
               [0.114503, 0.786281, 0.099216],
               [-0.003882, -0.048116, 1.051998]],
    "deutan": [[0.367322, 0.860646, -0.227968],
               [0.280085, 0.672501, 0.047413],
               [-0.011820, 0.042940, 0.968881]],
    "tritan": [[1.255528, -0.076749, -0.178779],
               [-0.078411, 0.930809, 0.147602],
               [0.004733, 0.691367, 0.303900]],
}

# CIEDE2000 bands: <5 indistinguishable, 5-10 risky, >=10 practical categorical
# floor (matches Okabe-Ito / Paul Tol design), >=15 comfortable.
DEFAULT_MIN = 10.0


def parse_hex(s):
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        raise ValueError(f"bad hex: {s!r}")
    return tuple(int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def apply_cvd(rgb, m):
    """Machado matrices act on gamma-encoded sRGB in [0,1]; clamp result."""
    out = []
    for row in m:
        v = row[0] * rgb[0] + row[1] * rgb[1] + row[2] * rgb[2]
        out.append(min(1.0, max(0.0, v)))
    return tuple(out)


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb):
    r, g, b = (_lin(c) for c in rgb)
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    x, y, z = x / 0.95047, y / 1.0, z / 1.08883

    def f(t):
        return t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29
    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def ciede2000(lab1, lab2):
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2
    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    Cbar = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cbar ** 7 / (Cbar ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360
    h2p = math.degrees(math.atan2(b2, a2p)) % 360

    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    elif abs(h2p - h1p) <= 180:
        dhp = h2p - h1p
    elif h2p - h1p > 180:
        dhp = h2p - h1p - 360
    else:
        dhp = h2p - h1p + 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2)

    Lbar = (L1 + L2) / 2
    Cbp = (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbar = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hbar = (h1p + h2p) / 2
    elif h1p + h2p < 360:
        hbar = (h1p + h2p + 360) / 2
    else:
        hbar = (h1p + h2p - 360) / 2

    T = (1 - 0.17 * math.cos(math.radians(hbar - 30))
         + 0.24 * math.cos(math.radians(2 * hbar))
         + 0.32 * math.cos(math.radians(3 * hbar + 6))
         - 0.20 * math.cos(math.radians(4 * hbar - 63)))
    dtheta = 30 * math.exp(-(((hbar - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + (0.015 * (Lbar - 50) ** 2) / math.sqrt(20 + (Lbar - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dtheta)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                     + Rt * (dCp / Sc) * (dHp / Sh))


def min_separation(labs):
    """Return (min_dE, i, j) over all unordered pairs."""
    best = (float("inf"), -1, -1)
    for i in range(len(labs)):
        for j in range(i + 1, len(labs)):
            d = ciede2000(labs[i], labs[j])
            if d < best[0]:
                best = (d, i, j)
    return best


def main(argv):
    thresh = DEFAULT_MIN
    hexes = []
    it = iter(argv)
    for a in it:
        if a in ("--min", "-m"):
            thresh = float(next(it))
        else:
            hexes.append(a)
    if len(hexes) < 2:
        print(__doc__)
        return 2

    rgbs = [parse_hex(h) for h in hexes]
    print(f"{len(rgbs)} swatches · warn when CIEDE2000 < {thresh}\n")
    print(f"{'vision':<10} {'min ΔE00':>9}   closest pair")
    print("-" * 46)
    failed = False
    for label, mat in [("normal", None)] + [(k, CVD[k]) for k in CVD]:
        sim = rgbs if mat is None else [apply_cvd(c, mat) for c in rgbs]
        labs = [rgb_to_lab(c) for c in sim]
        d, i, j = min_separation(labs)
        flag = "  <-- FAIL" if d < thresh else ""
        if flag:
            failed = True
        print(f"{label:<10} {d:>9.1f}   {hexes[i]} / {hexes[j]}{flag}")
    print()
    if failed:
        print("VERDICT: not CVD-safe — merge/replace the flagged pair(s).")
        return 1
    print("VERDICT: safe — every pair stays separable under all CVD types.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
