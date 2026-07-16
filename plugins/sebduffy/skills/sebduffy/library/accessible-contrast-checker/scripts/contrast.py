#!/usr/bin/env python3
"""Colour-contrast checker + auto-fixer. WCAG 2.x ratio AND APCA Lc.

Pure stdlib (works on macOS system python3.9). No external deps.

APCA constants are APCA-W3 0.1.9 (SA98G) from Myndex/apca-w3 — the reference
implementation the CSS WG cites. WCAG uses the WCAG 2.1/2.2 relative-luminance
formula. Auto-fix nudges ONE colour along its lightness axis (mixing toward
black or white, whichever raises contrast) via binary search to the nearest
value that passes the target threshold.

CLI:
  contrast.py check  <fg> <bg> [--level AA|AAA] [--size normal|large]
  contrast.py fix    <fg> <bg> [--fix fg|bg] [--level AA|AAA] [--size ...]
  contrast.py apca   <text> <bg>
All colours are #rgb / #rrggbb / rrggbb. Exit 0 = pass, 1 = fail (check only).
"""
import argparse, math, re, sys

# --- APCA-W3 0.1.9 SA98G config ------------------------------------------
SA = dict(mainTRC=2.4, sRco=0.2126729, sGco=0.7151522, sBco=0.0721750,
          normBG=0.56, normTXT=0.57, revTXT=0.62, revBG=0.65,
          blkThrs=0.022, blkClmp=1.414, scaleBoW=1.14, scaleWoB=1.14,
          loBoWoffset=0.027, loWoBoffset=0.027, deltaYmin=0.0005, loClip=0.1)


def parse_hex(s):
    s = s.strip().lstrip('#')
    if len(s) == 3:
        s = ''.join(c * 2 for c in s)
    if not re.fullmatch(r'[0-9a-fA-F]{6}', s):
        raise ValueError(f'bad colour: {s!r} (use #rgb or #rrggbb)')
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(rgb):
    return '#' + ''.join(f'{max(0, min(255, round(c))):02x}' for c in rgb)


# --- WCAG 2.x ------------------------------------------------------------
def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def rel_luminance(rgb):
    r, g, b = (_lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def wcag_ratio(fg, bg):
    l1, l2 = rel_luminance(fg), rel_luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def wcag_threshold(level, size):
    # AA: 4.5 normal / 3.0 large. AAA: 7.0 normal / 4.5 large.
    table = {('AA', 'normal'): 4.5, ('AA', 'large'): 3.0,
             ('AAA', 'normal'): 7.0, ('AAA', 'large'): 4.5}
    return table[(level, size)]


# --- APCA ----------------------------------------------------------------
def _srgb_to_y(rgb):
    return (SA['sRco'] * (rgb[0] / 255.0) ** SA['mainTRC'] +
            SA['sGco'] * (rgb[1] / 255.0) ** SA['mainTRC'] +
            SA['sBco'] * (rgb[2] / 255.0) ** SA['mainTRC'])


def _soft_clamp(y):
    return y if y > SA['blkThrs'] else y + (SA['blkThrs'] - y) ** SA['blkClmp']


def apca_lc(text_rgb, bg_rgb):
    """Return APCA Lc (roughly -108..106). Sign = polarity; use abs() for magnitude."""
    txt_y = _soft_clamp(_srgb_to_y(text_rgb))
    bg_y = _soft_clamp(_srgb_to_y(bg_rgb))
    if abs(bg_y - txt_y) < SA['deltaYmin']:
        return 0.0
    if bg_y > txt_y:  # dark text on light bg (BoW)
        sapc = (bg_y ** SA['normBG'] - txt_y ** SA['normTXT']) * SA['scaleBoW']
        out = 0.0 if sapc < SA['loClip'] else sapc - SA['loBoWoffset']
    else:             # light text on dark bg (WoB)
        sapc = (bg_y ** SA['revBG'] - txt_y ** SA['revTXT']) * SA['scaleWoB']
        out = 0.0 if sapc > -SA['loClip'] else sapc + SA['loWoBoffset']
    return out * 100.0


# --- Auto-fix: nudge one colour along lightness toward nearest pass -------
def _mix(rgb, target, t):
    return tuple(rgb[i] + (target[i] - rgb[i]) * t for i in range(3))


def _quantise(rgb):
    return tuple(max(0, min(255, round(c))) for c in rgb)


def fix_to_ratio(fg, bg, fix_which, target_ratio, max_steps=40):
    """Nudge fix_which ('fg' or 'bg') toward black or white until wcag_ratio>=target.
    Binary-searches the smallest mix fraction t, evaluating the *8-bit-quantised*
    candidate at every step so the emitted hex genuinely passes (the un-rounded
    float can round back below threshold). Returns (new_hex, ratio, changed)."""
    movable = fg if fix_which == 'fg' else bg
    other = bg if fix_which == 'fg' else fg
    if wcag_ratio(fg, bg) >= target_ratio:
        return to_hex(movable), wcag_ratio(fg, bg), False
    # Try both endpoints; keep whichever reaches the target with the smaller t.
    best = None
    for endpoint in ((0, 0, 0), (255, 255, 255)):
        lo, hi = 0.0, 1.0
        # Ratio of the quantised mix — the colour we would actually emit at t.
        def ratio_at(t):
            m = _quantise(_mix(movable, endpoint, t))
            return wcag_ratio(m, other) if fix_which == 'fg' else wcag_ratio(other, m)
        # endpoint is already integer; it must reach the target, else skip
        if ratio_at(1.0) < target_ratio:
            continue
        # Invariant: hi always names a t whose quantised colour passes.
        for _ in range(max_steps):
            mid = (lo + hi) / 2
            if ratio_at(mid) >= target_ratio:
                hi = mid
            else:
                lo = mid
        cand = _quantise(_mix(movable, endpoint, hi))
        r = ratio_at(hi)
        if best is None or hi < best[2]:
            best = (cand, r, hi)
    if best is None:  # unreachable even at pure black/white
        return to_hex(movable), wcag_ratio(fg, bg), False
    return to_hex(best[0]), best[1], True


# --- CLI -----------------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('check', 'fix', 'apca'):
        sp = sub.add_parser(name)
        sp.add_argument('fg'); sp.add_argument('bg')
        if name != 'apca':
            sp.add_argument('--level', choices=['AA', 'AAA'], default='AA')
            sp.add_argument('--size', choices=['normal', 'large'], default='normal')
        if name == 'fix':
            sp.add_argument('--fix', choices=['fg', 'bg'], default='fg')
    a = p.parse_args(argv)
    fg, bg = parse_hex(a.fg), parse_hex(a.bg)

    if a.cmd == 'apca':
        lc = apca_lc(fg, bg)
        print(f'APCA Lc = {lc:+.1f}  (|Lc| {abs(lc):.1f})')
        return 0

    ratio = wcag_ratio(fg, bg)
    need = wcag_threshold(a.level, a.size)
    lc = apca_lc(fg, bg)
    passed = ratio >= need
    if a.cmd == 'check':
        print(f'WCAG {a.level} {a.size}: {ratio:.2f}:1  (need {need}:1)  '
              f'{"PASS" if passed else "FAIL"}')
        print(f'APCA Lc = {lc:+.1f}')
        return 0 if passed else 1

    # fix
    new_hex, new_ratio, changed = fix_to_ratio(fg, bg, a.fix, need)
    orig = a.fg if a.fix == 'fg' else a.bg
    if not changed:
        print(f'already passes ({ratio:.2f}:1) — no change')
    else:
        print(f'{a.fix}: {orig} -> {new_hex}   {ratio:.2f}:1 -> {new_ratio:.2f}:1  '
              f'(>= {need}:1)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
