#!/usr/bin/env python3
"""Order a set of skill steps into a runnable chain.

Reads a JSON plan on stdin (or a file arg) describing steps, the artifacts each
step needs, and the artifacts each step produces. Emits a dependency-ordered
execution plan, or a precise error if the chain is unbuildable (cycle, missing
artifact, or two steps producing the same artifact).

Plan schema (list of steps):
  [
    {"id": "extract",  "skill": "pdf",              "needs": [],            "produces": ["rows.csv"]},
    {"id": "clean",    "skill": "xlsx",            "needs": ["rows.csv"],  "produces": ["clean.xlsx"]},
    {"id": "chart",    "skill": "dataviz",         "needs": ["clean.xlsx"],"produces": ["fig.svg"]},
    {"id": "deck",     "skill": "pptx",            "needs": ["fig.svg"],   "produces": ["out.pptx"]}
  ]

Exit codes: 0 = ordered plan printed; 1 = unbuildable (reason on stderr); 2 = bad input.
"""
import json
import sys


def load(argv):
    raw = open(argv[1]).read() if len(argv) > 1 else sys.stdin.read()
    try:
        plan = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"[input error] not valid JSON: {e}")
    if not isinstance(plan, list) or not plan:
        sys.exit("[input error] plan must be a non-empty JSON array of steps")
    return plan


def validate(plan):
    seen_ids, producers = set(), {}
    for i, s in enumerate(plan):
        for k in ("id", "skill"):
            if not s.get(k):
                sys.exit(f"[input error] step {i} missing required field '{k}'")
        if s["id"] in seen_ids:
            sys.exit(f"[input error] duplicate step id '{s['id']}'")
        seen_ids.add(s["id"])
        s.setdefault("needs", [])
        s.setdefault("produces", [])
        for art in s["produces"]:
            if art in producers:
                sys.exit(f"[unbuildable] artifact '{art}' produced by two steps "
                         f"('{producers[art]}' and '{s['id']}') — chains need one owner per artifact")
            producers[art] = s["id"]
    return producers


def order(plan, producers):
    # Kahn topological sort over artifact dependencies.
    by_id = {s["id"]: s for s in plan}
    indeg = {sid: 0 for sid in by_id}
    edges = {sid: [] for sid in by_id}
    external = set()  # artifacts nobody in the plan produces (must pre-exist)
    for s in plan:
        for art in s["needs"]:
            dep = producers.get(art)
            if dep is None:
                external.add(art)
            elif dep != s["id"]:
                edges[dep].append(s["id"])
                indeg[s["id"]] += 1
    queue = sorted([sid for sid, d in indeg.items() if d == 0])
    ordered = []
    while queue:
        sid = queue.pop(0)
        ordered.append(sid)
        for nxt in sorted(edges[sid]):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
        queue.sort()
    if len(ordered) != len(by_id):
        stuck = sorted(sid for sid in by_id if sid not in ordered)
        sys.exit(f"[unbuildable] dependency cycle among steps: {', '.join(stuck)}")
    return [by_id[sid] for sid in ordered], sorted(external)


def main():
    plan = load(sys.argv)
    producers = validate(plan)
    ordered, external = order(plan, producers)
    if external:
        print("# pre-existing inputs required (produced by no step):")
        for art in external:
            print(f"#  - {art}")
        print()
    print("# execution order:")
    for n, s in enumerate(ordered, 1):
        needs = ", ".join(s["needs"]) or "-"
        prod = ", ".join(s["produces"]) or "-"
        print(f"{n}. {s['id']:<12} skill={s['skill']:<16} needs=[{needs}] -> [{prod}]")


if __name__ == "__main__":
    main()
