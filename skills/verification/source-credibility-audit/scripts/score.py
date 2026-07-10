#!/usr/bin/env python3
"""Source-credibility scorer. Reads a JSON list of sources on stdin (or a
file arg), each rated 1-5 on seven dimensions, and prints a weighted trust
score per source plus a claim-level weakest-link verdict.

python3.9 stdlib only. Usage:
    python3 score.py sources.json
    cat sources.json | python3 score.py
"""
import json
import sys

# Dimension weights (sum = 1.0). Reliability + independence dominate.
WEIGHTS = {
    "reliability": 0.25,     # factual track record (MBFC factual tier)
    "independence": 0.20,    # freedom from conflict of interest / funding stake
    "primacy": 0.15,         # primary source of the data vs secondhand
    "expertise": 0.15,       # domain authority / peer review
    "corroboration": 0.10,   # independently confirmed elsewhere
    "transparency": 0.10,    # methodology + corrections disclosed
    "recency": 0.05,         # still current for the claim's time window
}
# Dimensions that trigger a weakest-link veto if they score at/below the floor.
CRITICAL = ("reliability", "independence")
FLOOR = 2  # 1-2 on a critical dimension flags the source regardless of average

BANDS = [(4.3, "A trust"), (3.5, "B usable"), (2.5, "C shaky"),
         (0.0, "D unusable")]


def band(score):
    for cut, label in BANDS:
        if score >= cut:
            return label
    return "D unusable"


def score_source(src):
    r = src.get("ratings", {})
    missing = [d for d in WEIGHTS if d not in r]
    if missing:
        raise ValueError("source %r missing dimensions: %s"
                         % (src.get("name", "?"), ", ".join(missing)))
    bad = {d: v for d, v in r.items() if not (1 <= v <= 5)}
    if bad:
        raise ValueError("source %r out-of-range (need 1-5): %s"
                         % (src.get("name", "?"), bad))
    weighted = sum(r[d] * w for d, w in WEIGHTS.items())
    flags = [d for d in CRITICAL if r[d] <= FLOOR]
    return {
        "name": src.get("name", "?"),
        "score": round(weighted, 2),
        "band": "F flagged" if flags else band(weighted),
        "weakest_link": flags,
        "weakest_dim": min(r, key=r.get),
    }


def main():
    raw = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    data = json.loads(raw)
    sources = data["sources"] if isinstance(data, dict) else data
    if not sources:
        sys.exit("no sources provided")
    results = [score_source(s) for s in sources]

    # Claim verdict = weakest load-bearing source (a chain is only as strong
    # as its weakest link). Any flagged source drags the claim to flagged.
    load_bearing = [r for r in results
                    if r["name"] not in data.get("corroborating_only", [])] \
        if isinstance(data, dict) else results
    load_bearing = load_bearing or results
    worst = min(load_bearing, key=lambda r: (bool(not r["weakest_link"]),
                                             r["score"]))
    print(json.dumps({
        "sources": results,
        "claim_verdict": worst["band"],
        "weakest_source": worst["name"],
        "note": "claim inherits its weakest load-bearing source",
    }, indent=2))


if __name__ == "__main__":
    main()
