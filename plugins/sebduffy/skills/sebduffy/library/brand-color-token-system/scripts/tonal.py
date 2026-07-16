#!/usr/bin/env python3
"""Turn ONE brand hex into a 50->950 tonal token ramp + semantic layer.

Pure stdlib (python3.9+). No deps. Uses Bjorn Ottosson's OKLab so the ramp
is perceptually even: hold hue, sweep lightness, taper chroma at the ends.

Usage:
  python3 tonal.py "#2F6BFF"                       # print ramp table
  python3 tonal.py "#2F6BFF" --name brand --css    # CSS custom properties
  python3 tonal.py "#2F6BFF" --name brand --tw     # Tailwind color object
  python3 tonal.py "#2F6BFF" --name brand --sd     # Style Dictionary tokens
  python3 tonal.py "#2F6BFF" --semantic            # + light/dark semantic layer
"""
import argparse, json, math, sys

STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
# Target OKLab L per step (light -> dark). Even-ish perceptual staircase.
L_TARGETS = [0.972, 0.936, 0.878, 0.800, 0.714, 0.630, 0.548, 0.460, 0.372, 0.284, 0.216]
# Chroma multiplier per step: fades toward the near-white/near-black extremes.
C_SCALE = [0.28, 0.42, 0.62, 0.82, 0.96, 1.00, 0.98, 0.90, 0.78, 0.62, 0.50]


def hex_to_rgb(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6 or any(c not in "0123456789abcdefABCDEF" for c in h):
        raise ValueError("hex must be #RGB or #RRGGBB, got %r" % h)
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def rgb_to_hex(r, g, b):
    f = lambda x: format(max(0, min(255, round(x * 255))), "02x")
    return "#" + f(r) + f(g) + f(b)


def _srgb_to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lin_to_srgb(c):
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def rgb_to_oklab(r, g, b):
    r, g, b = _srgb_to_lin(r), _srgb_to_lin(g), _srgb_to_lin(b)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    A = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    B = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, A, B


def oklab_to_rgb(L, A, B):
    l_ = L + 0.3963377774 * A + 0.2158037573 * B
    m_ = L - 0.1055613458 * A - 0.0638541728 * B
    s_ = L - 0.0894841775 * A - 1.2914855480 * B
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    b = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return _lin_to_srgb(r), _lin_to_srgb(g), _lin_to_srgb(b)


def oklab_to_lch(L, A, B):
    C = math.hypot(A, B)
    H = math.degrees(math.atan2(B, A)) % 360
    return L, C, H


def lch_to_rgb(L, C, H):
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))
    return oklab_to_rgb(L, a, b)


def clamp_to_gamut(L, C, H):
    """Binary-search the largest in-gamut chroma at this L/H (gamut clip)."""
    def in_gamut(c):
        r, g, b = lch_to_rgb(L, c, H)
        e = 1e-4
        return all(-e <= v <= 1 + e for v in (r, g, b))
    if in_gamut(C):
        return C
    lo, hi = 0.0, C
    for _ in range(24):
        mid = (lo + hi) / 2
        if in_gamut(mid):
            lo = mid
        else:
            hi = mid
    return lo


def build_ramp(hex_in):
    L0, A0, B0 = rgb_to_oklab(*hex_to_rgb(hex_in))
    _, C0, H0 = oklab_to_lch(L0, A0, B0)
    out = []
    for step, L, cs in zip(STEPS, L_TARGETS, C_SCALE):
        C = clamp_to_gamut(L, C0 * cs, H0)
        r, g, b = lch_to_rgb(L, C, H0)
        out.append({
            "step": step,
            "hex": rgb_to_hex(r, g, b),
            "oklch": "oklch(%.4f %.4f %.2f)" % (L, C, H0),
        })
    return out


# Semantic map: which ramp step each role points at, per mode.
SEMANTIC = {
    "bg":            (50, 950),   # (light-step, dark-step)
    "surface":       (100, 900),
    "surface-hover": (200, 800),
    "border":        (200, 800),
    "border-strong": (300, 700),
    "text-muted":    (600, 400),
    "text":          (900, 100),
    "primary":       (600, 500),
    "primary-hover": (700, 400),
    "on-primary":    (50, 950),
}


def semantic_layer(ramp, name):
    by = {r["step"]: r["hex"] for r in ramp}
    return {role: {"light": by[l], "dark": by[d]} for role, (l, d) in SEMANTIC.items()}


def emit_css(ramp, name, semantic):
    lines = [":root {"]
    for r in ramp:
        lines.append("  --%s-%d: %s;" % (name, r["step"], r["hex"]))
    if semantic:
        lines.append("  /* semantic (light) */")
        for role, m in semantic_layer(ramp, name).items():
            lines.append("  --%s-%s: %s;" % (name, role, m["light"]))
    lines.append("}")
    if semantic:
        lines.append('@media (prefers-color-scheme: dark) { :root {')
        for role, m in semantic_layer(ramp, name).items():
            lines.append("  --%s-%s: %s;" % (name, role, m["dark"]))
        lines.append("} }")
    return "\n".join(lines)


def emit_tailwind(ramp, name):
    obj = {name: {str(r["step"]): r["hex"] for r in ramp}}
    return "// tailwind.config -> theme.extend.colors\n" + json.dumps(obj, indent=2)


def emit_sd(ramp, name, semantic):
    tok = {name: {str(r["step"]): {"value": r["hex"], "type": "color"} for r in ramp}}
    if semantic:
        tok[name]["semantic"] = {
            role: {"light": {"value": m["light"], "type": "color"},
                   "dark": {"value": m["dark"], "type": "color"}}
            for role, m in semantic_layer(ramp, name).items()
        }
    return json.dumps({"color": tok}, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hex")
    ap.add_argument("--name", default="brand")
    ap.add_argument("--css", action="store_true")
    ap.add_argument("--tw", action="store_true")
    ap.add_argument("--sd", action="store_true")
    ap.add_argument("--semantic", action="store_true")
    a = ap.parse_args()
    ramp = build_ramp(a.hex)
    if a.css:
        print(emit_css(ramp, a.name, a.semantic)); return
    if a.tw:
        print(emit_tailwind(ramp, a.name)); return
    if a.sd:
        print(emit_sd(ramp, a.name, a.semantic)); return
    for r in ramp:
        print("%s-%-4d %s  %s" % (a.name, r["step"], r["hex"], r["oklch"]))
    if a.semantic:
        print("\nsemantic (light / dark):")
        for role, m in semantic_layer(ramp, a.name).items():
            print("  %-14s %s / %s" % (role, m["light"], m["dark"]))


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print("error: %s" % e, file=sys.stderr); sys.exit(1)
