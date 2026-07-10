#!/usr/bin/env python3
"""Audit an LLM-as-judge for the three headline biases + human agreement.

Ports the AlpacaEval length-controlled (LC) win-rate idea (Dubois et al. 2024,
"Length-Controlled AlpacaEval") plus standard position / self-preference
diagnostics into one dependency-light script (numpy + scipy).

INPUT: a JSONL file, one pairwise comparison per line. The judge compared a
CANDIDATE output against a BASELINE output for the same instruction.

Required per record:
  judge_winner   "candidate" | "baseline"   # content winner (de-swapped)
  len_candidate  number                      # length of candidate output (chars or tokens)
  len_baseline   number                      # length of baseline output
Optional per record (enable extra metrics when present):
  id             any                         # pair id linking the two presentation orders
  candidate_first  true|false                # was candidate shown FIRST to the judge
  human_winner   "candidate" | "baseline"    # gold human preference for the pair
  same_family    true|false                  # candidate shares the judge's model family

Run:  python3 judge_bias_audit.py judgments.jsonl
"""
import json
import sys
import math

import numpy as np
from scipy.optimize import minimize


def load(path):
    rows = []
    with open(path) as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError as e:
                sys.exit(f"line {n}: bad JSON: {e}")
            for req in ("judge_winner", "len_candidate", "len_baseline"):
                if req not in r:
                    sys.exit(f"line {n}: missing required field '{req}'")
            if r["judge_winner"] not in ("candidate", "baseline"):
                sys.exit(f"line {n}: judge_winner must be candidate|baseline")
            rows.append(r)
    if not rows:
        sys.exit("no records loaded")
    return rows


def raw_win_rate(rows):
    wins = sum(1 for r in rows if r["judge_winner"] == "candidate")
    return wins / len(rows)


def lc_win_rate(rows):
    """Length-controlled win rate: logistic reg of P(candidate wins) on the
    length delta, then read the prediction at delta = 0 (verbosity removed).
    Returns (lc_rate, length_coef, verdict). length_coef>0 => longer-wins bias."""
    y = np.array([1.0 if r["judge_winner"] == "candidate" else 0.0 for r in rows])
    # standardized length difference (candidate - baseline)
    delta = np.array([float(r["len_candidate"]) - float(r["len_baseline"]) for r in rows])
    sd = delta.std() or 1.0
    x = delta / sd

    def nll(theta):  # 2-param logistic: b0 + b1*x
        b0, b1 = theta
        z = b0 + b1 * x
        # stable log-loss
        ll = y * (-np.logaddexp(0, -z)) + (1 - y) * (-np.logaddexp(0, z))
        return -ll.sum()

    res = minimize(nll, np.array([0.0, 0.0]), method="BFGS")
    b0, b1 = res.x
    lc = 1.0 / (1.0 + math.exp(-b0))          # prediction at delta = 0
    coef = b1 / sd                            # per raw length-unit
    if abs(b1) < 0.15:
        v = "negligible length effect"
    elif b1 > 0:
        v = "VERBOSITY BIAS: judge favours LONGER outputs"
    else:
        v = "judge favours SHORTER outputs"
    return lc, b1, coef, v


def position_bias(rows):
    """Two paths. If pairs carry an `id` seen in BOTH orders -> consistency +
    directional first-preference. Else, single-order estimate of P(first wins)."""
    have_first = [r for r in rows if "candidate_first" in r]
    if not have_first:
        return None
    # P(the first-shown output won), regardless of which was candidate
    first_won = 0
    for r in have_first:
        cand_won = r["judge_winner"] == "candidate"
        cand_first = bool(r["candidate_first"])
        if (cand_won and cand_first) or ((not cand_won) and (not cand_first)):
            first_won += 1
    p_first = first_won / len(have_first)

    consistency = None
    byid = {}
    for r in have_first:
        if "id" in r:
            byid.setdefault(r["id"], []).append(r)
    pairs = [v for v in byid.values() if len(v) == 2]
    if pairs:
        agree = sum(1 for v in pairs if v[0]["judge_winner"] == v[1]["judge_winner"])
        consistency = agree / len(pairs)
    return p_first, consistency, len(pairs)


def self_preference(rows):
    """Compare judge-vs-human agreement for own-family candidates against
    other-family candidates. A positive gap = self-preference / self-enhancement."""
    tagged = [r for r in rows if "same_family" in r and "human_winner" in r]
    if not tagged:
        return None

    def agree_rate(subset):
        if not subset:
            return None
        a = sum(1 for r in subset if r["judge_winner"] == r["human_winner"])
        wr_judge = sum(1 for r in subset if r["judge_winner"] == "candidate") / len(subset)
        wr_human = sum(1 for r in subset if r["human_winner"] == "candidate") / len(subset)
        return a / len(subset), wr_judge, wr_human, len(subset)

    own = agree_rate([r for r in tagged if r["same_family"]])
    other = agree_rate([r for r in tagged if not r["same_family"]])
    return own, other


def human_agreement(rows):
    """Raw agreement + Cohen's kappa between judge and human on candidate/baseline."""
    tagged = [r for r in rows if "human_winner" in r]
    if not tagged:
        return None
    n = len(tagged)
    agree = sum(1 for r in tagged if r["judge_winner"] == r["human_winner"]) / n
    jc = sum(1 for r in tagged if r["judge_winner"] == "candidate") / n
    hc = sum(1 for r in tagged if r["human_winner"] == "candidate") / n
    pe = jc * hc + (1 - jc) * (1 - hc)          # chance agreement
    kappa = (agree - pe) / (1 - pe) if pe < 1 else float("nan")
    return agree, kappa, n


def pct(x):
    return "n/a" if x is None else f"{100 * x:5.1f}%"


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 judge_bias_audit.py judgments.jsonl")
    rows = load(sys.argv[1])
    print(f"\nLLM-JUDGE BIAS AUDIT  ({len(rows)} judgments)\n" + "=" * 52)

    print(f"\n[1] Raw candidate win rate      {pct(raw_win_rate(rows))}")

    lc, b1, coef, v = lc_win_rate(rows)
    print(f"\n[2] Length / verbosity bias")
    print(f"    Length-controlled win rate  {pct(lc)}   (verbosity removed)")
    print(f"    length coef (per unit)      {coef:+.4e}")
    print(f"    -> {v}")
    gap = raw_win_rate(rows) - lc
    print(f"    raw - LC gap                {gap:+.1%}  (how much length inflated the score)")

    pb = position_bias(rows)
    print(f"\n[3] Position bias")
    if pb is None:
        print("    no `candidate_first` field -> skipped (add it to measure)")
    else:
        p_first, cons, npairs = pb
        print(f"    P(first-shown output wins)  {pct(p_first)}   (0.50 = unbiased)")
        if cons is not None:
            print(f"    order-consistency           {pct(cons)}  over {npairs} swapped pairs")
        if abs(p_first - 0.5) > 0.05:
            print("    -> POSITION BIAS present; always randomize/average both orders")

    sp = self_preference(rows)
    print(f"\n[4] Self-preference bias")
    if sp is None:
        print("    need `same_family` + `human_winner` -> skipped")
    else:
        own, other = sp
        if own:
            print(f"    own-family : judge {pct(own[1])} vs human {pct(own[2])}  (agree {pct(own[0])}, n={own[3]})")
        if other:
            print(f"    other-fam  : judge {pct(other[1])} vs human {pct(other[2])}  (agree {pct(other[0])}, n={other[3]})")
        if own and other:
            infl_own = own[1] - own[2]      # judge over-scores own family vs humans
            infl_oth = other[1] - other[2]
            spgap = infl_own - infl_oth
            print(f"    self-preference gap         {spgap:+.1%}  (>0 => judge over-rates its own family)")

    ha = human_agreement(rows)
    print(f"\n[5] Human agreement (gold)")
    if ha is None:
        print("    no `human_winner` field -> skipped")
    else:
        agree, kappa, n = ha
        print(f"    raw agreement               {pct(agree)}  (n={n})")
        print(f"    Cohen's kappa               {kappa:+.3f}   (<0.4 weak, 0.4-0.6 moderate, >0.6 good)")
    print()


if __name__ == "__main__":
    main()
