#!/usr/bin/env python3
"""Data-driven Lottie versioning: fill ${TOKEN} placeholders in a Lottie JSON
template from a CSV or JSON rows file, write one .json per row, and optionally
render each to MP4/GIF via the `lottie_convert.py` CLI (from the `lottie` pkg).

Pure stdlib (py3.9) for the templating step. Rendering shells out to
`lottie_convert.py`, which requires `pip install "lottie[all]"`.

Placeholder rules (safe for JSON, no eval):
  - Text/colour swaps: put ${NAME} inside JSON string values in the template,
    e.g.  "t": "${TITLE}"  or  a hex colour token you post-process.
  - Numbers: a bare "${DURATION}" string value is coerced to int/float if the
    row value parses as a number (so keyframe times / positions can vary too).

Usage:
  python3 version_lottie.py template.json rows.csv --out out/ [--render mp4|gif]
  python3 version_lottie.py template.json rows.json --out out/ --render gif --fps 30

rows.csv  -> header row = token names (without ${}); one output per data row.
rows.json -> list of {token: value} objects.
Each row SHOULD include a `SLUG` column used for the output filename.
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys

TOKEN_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


def load_rows(path):
    """Return list[dict[str,str]] from a .csv or .json rows file. Validated."""
    if not os.path.isfile(path):
        sys.exit(f"rows file not found: {path}")
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
            sys.exit("rows.json must be a JSON array of objects")
        return [{str(k): v for k, v in r.items()} for r in data]
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def coerce(value):
    """Coerce a stringy value to int/float when it parses cleanly, else str."""
    if not isinstance(value, str):
        return value
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def substitute(node, row):
    """Recursively replace ${TOKEN} in every string in the parsed JSON tree.

    A string that is EXACTLY one token becomes the coerced (typed) value so
    numeric tokens keep their JSON number type. Missing tokens raise KeyError.
    Immutable: builds and returns new containers, never mutates the input.
    """
    if isinstance(node, str):
        m = TOKEN_RE.fullmatch(node)
        if m:
            key = m.group(1)
            if key not in row:
                raise KeyError(key)
            return coerce(row[key])
        return TOKEN_RE.sub(lambda mm: _lookup(mm, row), node)
    if isinstance(node, list):
        return [substitute(x, row) for x in node]
    if isinstance(node, dict):
        return {k: substitute(v, row) for k, v in node.items()}
    return node


def _lookup(match, row):
    key = match.group(1)
    if key not in row:
        raise KeyError(key)
    return str(row[key])


def render(json_path, fmt, fps):
    """Render a Lottie JSON to mp4/gif via lottie_convert.py. Returns out path."""
    out_path = os.path.splitext(json_path)[0] + "." + fmt
    cmd = ["lottie_convert.py", json_path, out_path]
    if fps:
        cmd += ["--fps", str(fps)]
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        sys.exit('lottie_convert.py not found. Install: pip install "lottie[all]"')
    except subprocess.CalledProcessError as exc:
        sys.exit(f"render failed for {json_path}: {exc}")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Version a Lottie template from data rows.")
    ap.add_argument("template", help="Lottie JSON template with ${TOKEN} placeholders")
    ap.add_argument("rows", help="rows.csv or rows.json (one output per row)")
    ap.add_argument("--out", default="out", help="output directory")
    ap.add_argument("--render", choices=["mp4", "gif"], help="also render each variant")
    ap.add_argument("--fps", type=int, default=0, help="frames/sec for render (0 = template default)")
    args = ap.parse_args()

    with open(args.template, encoding="utf-8") as fh:
        template = json.load(fh)
    rows = load_rows(args.rows)
    if not rows:
        sys.exit("no rows to process")
    os.makedirs(args.out, exist_ok=True)

    for i, row in enumerate(rows):
        slug = row.get("SLUG") or f"v{i + 1:02d}"
        try:
            filled = substitute(template, row)
        except KeyError as exc:
            sys.exit(f"row {i + 1} ({slug}) missing token {exc}")
        json_path = os.path.join(args.out, f"{slug}.json")
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(filled, fh, separators=(",", ":"))
        line = f"wrote {json_path}"
        if args.render:
            line += " -> " + render(json_path, args.render, args.fps)
        print(line)


if __name__ == "__main__":
    main()
