#!/usr/bin/env python3
"""
analyze_flow.py — Structural analysis of a Flowsheet JSON export (or any
JSON with the same {nodes: {...}, edges: {...}} shape).

Output is plain text designed for Claude to read into its reasoning, NOT
to show verbatim to the user. It produces facts (entry points, leaves,
hubs, orphans, edge style distribution) so Claude doesn't have to eyeball
a large graph.

Usage:
    python analyze_flow.py <path-to-flow.json>

Exits 0 on success, 1 on parse failure.
"""

import json
import sys
from collections import Counter, defaultdict


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "nodes" not in data or "edges" not in data:
        raise ValueError("Not a Flowsheet-shaped JSON (missing 'nodes' or 'edges')")
    return data


def analyze(data):
    nodes = data["nodes"]
    edges = data["edges"]

    # ── Adjacency ────────────────────────────────────────────
    out_edges = defaultdict(list)  # node_id -> [(target_id, edge_meta)]
    in_edges = defaultdict(list)   # node_id -> [(source_id, edge_meta)]
    for eid, e in edges.items():
        out_edges[e["from"]].append((e["to"], e))
        in_edges[e["to"]].append((e["from"], e))

    # ── Topology ─────────────────────────────────────────────
    entries = [n for n in nodes if not in_edges[n]]
    leaves  = [n for n in nodes if not out_edges[n]]
    orphans = [n for n in nodes if not in_edges[n] and not out_edges[n]]

    # Hub = node with most outgoing edges
    out_counts = {n: len(out_edges[n]) for n in nodes}
    in_counts  = {n: len(in_edges[n])  for n in nodes}
    total_counts = {n: out_counts[n] + in_counts[n] for n in nodes}

    # Sort hubs by total degree (in+out) — captures both "I send to many"
    # and "I'm referenced by many"
    top_hubs = sorted(total_counts.items(), key=lambda x: -x[1])[:5]

    # ── Edge style distribution ──────────────────────────────
    style_counts = Counter(e.get("style", "unknown") for e in edges.values())
    arrow_counts = Counter(e.get("arrow", "unknown") for e in edges.values())
    labelled = [e for e in edges.values() if (e.get("label") or "").strip()]

    # ── Duplicate titles ─────────────────────────────────────
    title_to_ids = defaultdict(list)
    for nid, n in nodes.items():
        t = (n.get("title") or "").strip().lower()
        if t:
            title_to_ids[t].append(nid)
    duplicates = {t: ids for t, ids in title_to_ids.items() if len(ids) > 1}

    # ── Likely UI components masquerading as pages ──────────
    component_keywords = ("button", "toggle", "switch", "modal", "popup",
                          "dropdown", "sheet", "drawer", "animation",
                          "transition", "loader")
    suspected_components = []
    for nid, n in nodes.items():
        title = (n.get("title") or "").lower()
        if any(kw in title for kw in component_keywords):
            # extra signal: dashed edges on both sides
            in_styles = [e.get("style") for _, e in in_edges[nid]]
            out_styles = [e.get("style") for _, e in out_edges[nid]]
            dashed_signal = "dashed" in in_styles or "dashed" in out_styles
            suspected_components.append({
                "id": nid,
                "title": n.get("title"),
                "dashed_edges": dashed_signal,
            })

    # ── Directional sanity check ─────────────────────────────
    # If a node's parent has multiple children but some arrows point IN to
    # the parent and some point OUT — that's a sketching layout artefact,
    # not real intent.
    mixed_direction_hubs = []
    for nid in nodes:
        # consider a node a "hub" candidate if it has ≥3 connections
        if total_counts[nid] >= 3:
            outgoing_neighbours = {t for t, _ in out_edges[nid]}
            incoming_neighbours = {s for s, _ in in_edges[nid]}
            # Children we send to that also send to us = real cycle, ignore.
            # What we want: are there children-shaped neighbours on both sides?
            asymmetric = (outgoing_neighbours | incoming_neighbours)
            if len(outgoing_neighbours) >= 2 and len(incoming_neighbours) >= 2:
                # Check if the in-neighbours look like sub-sections
                # (i.e. THEY are leaves apart from this one connection)
                child_like_in = [
                    s for s in incoming_neighbours
                    if out_counts[s] == 1 and in_counts[s] == 0
                ]
                if child_like_in:
                    mixed_direction_hubs.append({
                        "hub": nid,
                        "title": nodes[nid].get("title"),
                        "child_like_incomers": child_like_in,
                    })

    return {
        "totals": {"nodes": len(nodes), "edges": len(edges)},
        "entries": entries,
        "leaves": leaves,
        "orphans": orphans,
        "top_hubs": top_hubs,
        "out_counts": out_counts,
        "in_counts": in_counts,
        "style_counts": dict(style_counts),
        "arrow_counts": dict(arrow_counts),
        "labelled_edges": [
            {"from": e["from"], "to": e["to"], "label": e["label"]}
            for e in labelled
        ],
        "duplicates": duplicates,
        "suspected_components": suspected_components,
        "mixed_direction_hubs": mixed_direction_hubs,
        "_nodes": nodes,  # for title lookup
    }


def title_of(nodes, nid):
    return (nodes[nid].get("title") or "").strip() or nid


def render(report):
    nodes = report["_nodes"]
    out = []
    p = out.append

    p("FLOW ANALYSIS")
    p("=" * 60)
    p(f"Nodes: {report['totals']['nodes']}   Edges: {report['totals']['edges']}")
    p("")

    p("ENTRY POINTS (no incoming edges)")
    p("-" * 40)
    if report["entries"]:
        for nid in report["entries"]:
            p(f"  {nid}  {title_of(nodes, nid)}")
    else:
        p("  (none — every node has an incoming edge; possible cycle or missing entry)")
    p("")

    p("LEAVES (no outgoing edges — terminal states)")
    p("-" * 40)
    if report["leaves"]:
        for nid in report["leaves"]:
            p(f"  {nid}  {title_of(nodes, nid)}")
    else:
        p("  (none — every node has somewhere to go)")
    p("")

    if report["orphans"]:
        p("ORPHANS (no edges at all — likely sketching artefacts)")
        p("-" * 40)
        for nid in report["orphans"]:
            p(f"  {nid}  {title_of(nodes, nid)}")
        p("")

    p("TOP HUBS (by total degree)")
    p("-" * 40)
    for nid, deg in report["top_hubs"]:
        ic = report["in_counts"][nid]
        oc = report["out_counts"][nid]
        p(f"  {nid}  {title_of(nodes, nid):<40} in:{ic}  out:{oc}  total:{deg}")
    p("")

    p("EDGE STYLE DISTRIBUTION")
    p("-" * 40)
    for style, count in sorted(report["style_counts"].items(), key=lambda x: -x[1]):
        p(f"  {style:<15} {count}")
    p("")
    p("ARROW DISTRIBUTION")
    p("-" * 40)
    for arrow, count in sorted(report["arrow_counts"].items(), key=lambda x: -x[1]):
        p(f"  {arrow:<15} {count}")
    p("")

    if report["labelled_edges"]:
        p("LABELLED EDGES (likely conditions / triggers)")
        p("-" * 40)
        for e in report["labelled_edges"]:
            p(f"  {title_of(nodes, e['from'])} → {title_of(nodes, e['to'])}: [{e['label']}]")
        p("")

    if report["duplicates"]:
        p("DUPLICATE TITLES (likely scoped per parent — DO NOT consolidate)")
        p("-" * 40)
        for title, ids in report["duplicates"].items():
            p(f"  '{title}' appears as: {', '.join(ids)}")
        p("")

    if report["suspected_components"]:
        p("SUSPECTED UI COMPONENTS (not real pages)")
        p("-" * 40)
        for c in report["suspected_components"]:
            flag = " [dashed-edge confirmed]" if c["dashed_edges"] else ""
            p(f"  {c['id']}  {c['title']}{flag}")
        p("")

    if report["mixed_direction_hubs"]:
        p("MIXED-DIRECTION HUBS (arrow direction likely a layout artefact)")
        p("-" * 40)
        p("  These hubs have child-like neighbours pointing IN to them, when")
        p("  semantically those neighbours are probably children. Treat all")
        p("  connected sub-nodes as siblings/children regardless of arrow direction.")
        p("")
        for h in report["mixed_direction_hubs"]:
            incomers = ", ".join(title_of(nodes, c) for c in h["child_like_incomers"])
            p(f"  Hub: {h['title']} ({h['hub']})")
            p(f"    Children that point IN (treat as children anyway): {incomers}")
        p("")

    p("=" * 60)
    p("End of analysis. Use these facts to inform your response.")

    return "\n".join(out)


def main():
    if len(sys.argv) != 2:
        print("Usage: python analyze_flow.py <path-to-flow.json>", file=sys.stderr)
        sys.exit(1)
    try:
        data = load(sys.argv[1])
    except Exception as e:
        print(f"Failed to load: {e}", file=sys.stderr)
        sys.exit(1)
    report = analyze(data)
    print(render(report))


if __name__ == "__main__":
    main()
