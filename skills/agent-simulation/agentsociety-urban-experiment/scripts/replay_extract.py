#!/usr/bin/env python3
"""Extract survey / interview results from an AgentSociety SQLite replay DB and
compare a treatment agent group against a control group.

AgentSociety (v1.5.x) stores each run in SQLite (default db_type) under
env.home_dir. Tables are prefixed `as_`:
  as_survey  -> columns: id(agent_id), day, t, survey_id, result(JSON string), created_at
  as_dialog  -> columns: id(agent_id), day, t, type, speaker, content, created_at   # interviews
  as_status  -> per-tick agent status snapshots
This script is schema-tolerant: it introspects the tables and matches any table
whose name contains 'survey' or 'dialog', so it keeps working if names change.

Usage:
  python3 replay_extract.py RUN.db --treatment 1-50 --control 51-100 [--kind survey|dialog]
  python3 replay_extract.py RUN.db --list        # just list tables + row counts
"""
import argparse
import json
import sqlite3
import sys
from collections import Counter


def parse_ids(spec):
    """'1-50,77,90-92' -> set of ints."""
    out = set()
    if not spec:
        return out
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    return out


def list_tables(conn):
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    names = [r[0] for r in cur.fetchall()]
    for n in names:
        try:
            c = conn.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0]
        except sqlite3.Error:
            c = "?"
        print(f"  {n:40s} {c} rows")
    return names


def pick_table(conn, kind):
    names = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    hits = [n for n in names if kind in n.lower()]
    if not hits:
        sys.exit(f"No table matching '{kind}' found. Tables: {names}")
    # Prefer the shortest (least-suffixed) match.
    return sorted(hits, key=len)[0]


def agent_col(conn, table):
    cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")').fetchall()]
    for cand in ("id", "agent_id"):
        if cand in cols:
            return cand, cols
    sys.exit(f"Could not find an agent-id column in {table}: {cols}")


def summarize(rows, label):
    print(f"\n=== {label} (n={len(rows)}) ===")
    if not rows:
        return
    # Try to parse survey `result` JSON into answer frequency; else show samples.
    counter = Counter()
    parsed = 0
    for r in rows:
        blob = r.get("result") or r.get("content")
        if blob is None:
            continue
        try:
            data = json.loads(blob)
            parsed += 1
            if isinstance(data, dict):
                for k, v in data.items():
                    counter[f"{k}={v}"] += 1
        except (json.JSONDecodeError, TypeError):
            pass
    if parsed and counter:
        for answer, n in counter.most_common(20):
            print(f"  {n:4d}  {answer}")
    else:
        for r in rows[:5]:
            blob = r.get("result") or r.get("content") or ""
            print(f"  agent {r.get('id', r.get('agent_id'))}: {str(blob)[:120]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("db")
    ap.add_argument("--treatment", default="")
    ap.add_argument("--control", default="")
    ap.add_argument("--kind", default="survey", choices=["survey", "dialog"])
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    if args.list:
        list_tables(conn)
        return

    table = pick_table(conn, args.kind)
    acol, _ = agent_col(conn, table)
    treat = parse_ids(args.treatment)
    control = parse_ids(args.control)
    rows = [dict(r) for r in conn.execute(f'SELECT * FROM "{table}"').fetchall()]

    print(f"table={table}  agent_col={acol}  total_rows={len(rows)}")
    if not treat and not control:
        summarize(rows, "ALL")
        return
    summarize([r for r in rows if r[acol] in treat], "TREATMENT")
    summarize([r for r in rows if r[acol] in control], "CONTROL")


if __name__ == "__main__":
    main()
