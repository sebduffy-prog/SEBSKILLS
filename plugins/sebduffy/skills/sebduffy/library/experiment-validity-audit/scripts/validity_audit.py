#!/usr/bin/env python3
"""Experiment validity audit: SRM, peeking, power/MDE, novelty split.

Pure-stdlib math (uses scipy only if present, else exact stdlib fallbacks).
Runs on macOS system python3 (3.9) with no third-party deps required.

Subcommands
-----------
  srm      Sample Ratio Mismatch chi-square goodness-of-fit test.
  power    Required n per arm for a target MDE, or the MDE a given n can detect (proportions).
  peek     Corrected significance threshold when you looked K times (Pocock / Bonferroni).
  novelty  Compare an early window vs a later window to flag novelty/primacy decay.

Examples
--------
  python3 validity_audit.py srm --counts 50120 49880 --expected 0.5 0.5
  python3 validity_audit.py srm --counts 33500 33200 33990        # 3 equal arms
  python3 validity_audit.py power --baseline 0.10 --mde-rel 0.05 --alpha 0.05 --power 0.8
  python3 validity_audit.py power --baseline 0.10 --n 40000 --alpha 0.05 --power 0.8
  python3 validity_audit.py peek --looks 5 --alpha 0.05
  python3 validity_audit.py novelty --early 0.112 0.101 --late 0.104 0.103
"""
import argparse
import math
import sys

SRM_THRESHOLD = 0.0005  # Fabijan et al., KDD '19: severe-SRM alarm level.

# ---- distribution helpers (stdlib fallbacks; scipy used if available) --------
try:
    from scipy.stats import chi2 as _chi2, norm as _norm  # type: ignore

    def chi2_sf(x, df):
        return float(_chi2.sf(x, df))

    def norm_ppf(p):
        return float(_norm.ppf(p))

    def norm_sf(x):
        return float(_norm.sf(x))
except Exception:  # pragma: no cover - exercised only without scipy

    def _lower_gamma_reg(s, x):
        """Regularized lower incomplete gamma P(s, x) via series/continued fraction."""
        if x < 0 or s <= 0:
            raise ValueError("domain")
        if x == 0:
            return 0.0
        if x < s + 1.0:  # series expansion
            term = 1.0 / s
            total = term
            n = s
            for _ in range(1000):
                n += 1.0
                term *= x / n
                total += term
                if abs(term) < abs(total) * 1e-15:
                    break
            return total * math.exp(-x + s * math.log(x) - math.lgamma(s))
        # continued fraction for Q, then P = 1 - Q
        tiny = 1e-300
        b = x + 1.0 - s
        c = 1.0 / tiny
        d = 1.0 / b
        h = d
        for i in range(1, 1000):
            an = -i * (i - s)
            b += 2.0
            d = an * d + b
            if abs(d) < tiny:
                d = tiny
            c = b + an / c
            if abs(c) < tiny:
                c = tiny
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < 1e-15:
                break
        q = math.exp(-x + s * math.log(x) - math.lgamma(s)) * h
        return 1.0 - q

    def chi2_sf(x, df):
        if x <= 0:
            return 1.0
        return 1.0 - _lower_gamma_reg(df / 2.0, x / 2.0)

    def norm_sf(x):
        return 0.5 * math.erfc(x / math.sqrt(2.0))

    def norm_ppf(p):
        # Acklam's rational approximation to the normal quantile.
        if not 0.0 < p < 1.0:
            raise ValueError("p in (0,1)")
        a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
             1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
        b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
             6.680131188771972e+01, -1.328068155288572e+01]
        c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
             -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
        d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
             3.754408661907416e+00]
        plow, phigh = 0.02425, 1 - 0.02425
        if p < plow:
            q = math.sqrt(-2 * math.log(p))
            return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                   ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
        if p > phigh:
            q = math.sqrt(-2 * math.log(1 - p))
            return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                    ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
        q = p - 0.5
        r = q * q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


# ---- SRM ---------------------------------------------------------------------
def srm(counts, expected=None):
    total = sum(counts)
    k = len(counts)
    if k < 2 or total <= 0:
        raise ValueError("need >=2 arms and a positive total")
    if expected is None:
        expected = [1.0 / k] * k
    if abs(sum(expected) - 1.0) > 1e-6:
        s = sum(expected)
        expected = [e / s for e in expected]  # renormalise ratios to proportions
    exp_counts = [p * total for p in expected]
    stat = sum((o - e) ** 2 / e for o, e in zip(counts, exp_counts))
    df = k - 1
    p = chi2_sf(stat, df)
    return {
        "counts": counts, "expected_counts": [round(e, 1) for e in exp_counts],
        "chi2": stat, "df": df, "p": p,
        "srm": p < SRM_THRESHOLD, "threshold": SRM_THRESHOLD,
    }


# ---- power / MDE (two-proportion, two-sided) ---------------------------------
def _n_for_mde(p1, p2, alpha, power):
    za = norm_ppf(1 - alpha / 2.0)
    zb = norm_ppf(power)
    pbar = (p1 + p2) / 2.0
    num = (za * math.sqrt(2 * pbar * (1 - pbar)) +
           zb * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return num / (p2 - p1) ** 2


def power_calc(baseline, alpha, power, mde_rel=None, mde_abs=None, n=None):
    if n is not None:
        # bisect on relative MDE that this n can detect
        lo, hi = 1e-6, 0.999
        for _ in range(200):
            mid = (lo + hi) / 2.0
            p2 = min(0.999999, baseline * (1 + mid))
            need = _n_for_mde(baseline, p2, alpha, power)
            if need > n:
                lo = mid
            else:
                hi = mid
        return {"mode": "mde_from_n", "n_per_arm": n, "baseline": baseline,
                "detectable_mde_rel": hi, "detectable_abs_lift": baseline * hi,
                "alpha": alpha, "power": power}
    if mde_abs is not None:
        p2 = baseline + mde_abs
    elif mde_rel is not None:
        p2 = baseline * (1 + mde_rel)
    else:
        raise ValueError("give one of --n, --mde-rel, --mde-abs")
    need = _n_for_mde(baseline, p2, alpha, power)
    return {"mode": "n_from_mde", "baseline": baseline, "treatment": p2,
            "n_per_arm": math.ceil(need), "total_n": math.ceil(need) * 2,
            "alpha": alpha, "power": power}


# ---- peeking -----------------------------------------------------------------
def peek(looks, alpha):
    # Bonferroni is conservative; Pocock spends alpha evenly across K analyses.
    bonf = alpha / looks
    # Pocock nominal alpha (2-sided) approximation table + solver.
    # Solve for a such that P(any |Z_i|>c over K equally-spaced looks)=alpha.
    # Use independent-increments upper bound => same as sequential Sidak here.
    sidak = 1 - (1 - alpha) ** (1.0 / looks)
    naive_fpr = 1 - (1 - alpha) ** looks  # inflated FPR if you keep the nominal alpha
    return {"looks": looks, "nominal_alpha": alpha,
            "naive_actual_fpr_if_uncorrected": naive_fpr,
            "bonferroni_alpha_per_look": bonf,
            "sidak_alpha_per_look": sidak}


# ---- novelty -----------------------------------------------------------------
def novelty(early, late):
    e_ctrl, e_trt = early
    l_ctrl, l_trt = late
    early_lift = (e_trt - e_ctrl) / e_ctrl if e_ctrl else float("nan")
    late_lift = (l_trt - l_ctrl) / l_ctrl if l_ctrl else float("nan")
    decay = early_lift - late_lift
    flag = late_lift != 0 and abs(decay) > 0.5 * abs(early_lift)
    return {"early_lift_rel": early_lift, "late_lift_rel": late_lift,
            "lift_decay_rel": decay, "novelty_suspected": flag,
            "note": "If late lift is <50% of early lift, treat as novelty/primacy; "
                    "re-read on a fresh, later window or a holdout."}


def _fmt(d):
    lines = []
    for k, v in d.items():
        if isinstance(v, float):
            v = f"{v:.6g}"
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Experiment validity audit")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("srm")
    s.add_argument("--counts", type=float, nargs="+", required=True)
    s.add_argument("--expected", type=float, nargs="+", default=None)

    p = sub.add_parser("power")
    p.add_argument("--baseline", type=float, required=True)
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--power", type=float, default=0.8)
    p.add_argument("--mde-rel", type=float, default=None)
    p.add_argument("--mde-abs", type=float, default=None)
    p.add_argument("--n", type=float, default=None)

    k = sub.add_parser("peek")
    k.add_argument("--looks", type=int, required=True)
    k.add_argument("--alpha", type=float, default=0.05)

    nv = sub.add_parser("novelty")
    nv.add_argument("--early", type=float, nargs=2, required=True, help="ctrl trt")
    nv.add_argument("--late", type=float, nargs=2, required=True, help="ctrl trt")

    a = ap.parse_args(argv)
    if a.cmd == "srm":
        out = srm(a.counts, a.expected)
    elif a.cmd == "power":
        out = power_calc(a.baseline, a.alpha, a.power, a.mde_rel, a.mde_abs, a.n)
    elif a.cmd == "peek":
        out = peek(a.looks, a.alpha)
    else:
        out = novelty(tuple(a.early), tuple(a.late))
    print(a.cmd + ":")
    print(_fmt(out))
    return out


if __name__ == "__main__":
    main()
