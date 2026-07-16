#!/usr/bin/env python3
"""Route a user request to the best-matching skill(s) from a SKILL.md manifest.

Pure stdlib. Scores every skill's triggers (keywords + when_to_use + description)
against the request with a lexical signal, then applies a semantic-router-style
decision: absolute threshold (no-match -> None) + a RouteLLM-style top1/top2
margin (ambiguous -> ask the user).

Usage:
  python3 route.py --skills-dir /path/to/skills "make my hero image ripple on hover"
  python3 route.py --skills-dir ./skills --json "route each step to a different llm"

Exit codes: 0 confident route, 2 ambiguous (needs a question), 3 no-match.
"""
import argparse, json, os, re, sys, math
from collections import Counter

# --- decision bands (manifest-specific; the script narrows, Claude adjudicates) ---
WEAK = 0.35            # top score below this -> no_match (nothing meaningfully matched)
CONFIDENT = 0.80       # top score above this AND margin clear -> confident route
MARGIN = 0.30          # top1-top2 gap needed to call a confident route
MAX_CANDIDATES = 4     # how many to surface in the shortlist

STOP = set("a an the of to for and or in on with your you my me it is are be this that "
           "how do i want need make build create use using add get set from as at into "
           "when what which any all can should would like new".split())


def tokenize(text):
    toks = re.findall(r"[a-z0-9][a-z0-9+#.\-]*", (text or "").lower())
    return [t for t in toks if t not in STOP and len(t) > 1]


def parse_frontmatter(path):
    """Extract routing-relevant fields from a SKILL.md YAML frontmatter (no PyYAML)."""
    try:
        raw = open(path, encoding="utf-8").read()
    except OSError:
        return None
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", raw, re.S)
    if not m:
        return None
    fm = m.group(1)
    name = _scalar(fm, "name") or os.path.basename(os.path.dirname(path))
    return {
        "name": name,
        "category": _scalar(fm, "category") or "",
        "description": _block(fm, "description"),
        "keywords": _inline_list(fm, "keywords"),
        "when_to_use": _yaml_list(fm, "when_to_use"),
        "when_not_to_use": _yaml_list(fm, "when_not_to_use"),
        "path": path,
    }


def _scalar(fm, key):
    m = re.search(rf"^{key}:\s*(.+)$", fm, re.M)
    return m.group(1).strip().strip("\"'") if m else ""


def _block(fm, key):
    # "description: >" or "description: |" folded block, or inline scalar
    m = re.search(rf"^{key}:\s*[>|]\s*\n((?:[ \t]+.*\n?)+)", fm, re.M)
    if m:
        return " ".join(l.strip() for l in m.group(1).splitlines())
    return _scalar(fm, key)


def _inline_list(fm, key):
    m = re.search(rf"^{key}:\s*\[(.*?)\]", fm, re.S | re.M)
    if not m:
        return []
    return [x.strip().strip("\"'") for x in m.group(1).split(",") if x.strip()]


def _yaml_list(fm, key):
    m = re.search(rf"^{key}:\s*\n((?:[ \t]*-.*\n?)+)", fm, re.M)
    if not m:
        return []
    return [re.sub(r'^[ \t]*-\s*', '', l).strip().strip("\"'")
            for l in m.group(1).splitlines() if l.strip().startswith(tuple(" \t-")) and "-" in l]


def load_manifest(skills_dir):
    skills = []
    for root, _, files in os.walk(skills_dir):
        if "SKILL.md" in files:
            fm = parse_frontmatter(os.path.join(root, "SKILL.md"))
            if fm:
                skills.append(fm)
    return skills


def score(req_tokens, req_text, skill):
    """Lexical relevance in [0,1]-ish. Keyword phrase hits weigh most; token
    overlap with when_to_use/description is the semantic-ish backstop."""
    req_set = set(req_tokens)
    req_lc = req_text.lower()
    s = 0.0
    # 1) exact keyword / phrase hits (strongest trigger signal)
    for kw in skill["keywords"]:
        kw_lc = kw.lower()
        if " " in kw_lc or "-" in kw_lc:
            if kw_lc in req_lc:                       # phrase present verbatim
                s += 0.9
            else:
                parts = set(tokenize(kw_lc))
                if parts and parts <= req_set:        # all words present, any order
                    s += 0.5
        elif kw_lc in req_set:
            s += 0.35
    # 2) token overlap with when_to_use lines + description (intent match)
    corpus = " ".join(skill["when_to_use"]) + " " + (skill["description"] or "")
    ctoks = set(tokenize(corpus))
    if ctoks:
        overlap = len(req_set & ctoks)
        s += 0.35 * overlap / math.sqrt(len(req_set) + 1)
    # 3) when_not_to_use acts as a demoter when the request matches an exclusion
    for line in skill["when_not_to_use"]:
        ntoks = set(tokenize(line))
        if ntoks and len(req_set & ntoks) >= 2:
            s -= 0.15
    return max(0.0, s)


def rank(request, skills):
    rt = tokenize(request)
    scored = [(sk, score(rt, request, sk)) for sk in skills]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def _shortlist(scored, top_s):
    near = [s for s in scored if s[1] >= WEAK and (top_s - s[1] < MARGIN)]
    near = near or scored[:1]
    return [{"name": s[0]["name"], "category": s[0]["category"],
             "score": round(s[1], 3)} for s in near[:MAX_CANDIDATES]]


def decide(scored):
    """Three bands. The lexical score only NARROWS; Claude reads the shortlist's
    when_to_use / when_not_to_use to make the final call (this is the semantic
    step). Never trust a lone coincidental token match as a confident route."""
    top, top_s = (scored[0][0], scored[0][1]) if scored else (None, 0.0)
    second_s = scored[1][1] if len(scored) > 1 else 0.0
    cands = _shortlist(scored, top_s)

    if top_s < WEAK:                                   # nothing matched
        return {"decision": "no_match", "route": None, "candidates": cands}
    if top_s >= CONFIDENT and (top_s - second_s) >= MARGIN:
        return {"decision": "route", "route": top["name"],
                "category": top["category"], "score": round(top_s, 3),
                "candidates": cands}
    # weak-but-present, or a near-tie -> Claude adjudicates / asks the user
    return {"decision": "verify", "route": None, "candidates": cands}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("request", help="the user's request text")
    ap.add_argument("--skills-dir", required=True)
    ap.add_argument("--json", action="store_true", help="emit raw JSON")
    ap.add_argument("--top", type=int, default=5, help="show N ranked in text mode")
    args = ap.parse_args()

    skills = load_manifest(args.skills_dir)
    if not skills:
        print(f"No SKILL.md found under {args.skills_dir}", file=sys.stderr)
        sys.exit(3)
    scored = rank(args.request, skills)
    result = decide(scored)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"decision: {result['decision']}")
        if result["decision"] == "route":
            print(f"-> {result['route']}  ({result['category']}, score={result['score']})")
        for sk, sc in scored[:args.top]:
            print(f"   {sc:5.3f}  {sk['name']}")
    sys.exit({"route": 0, "verify": 2, "no_match": 3}[result["decision"]])


if __name__ == "__main__":
    main()
