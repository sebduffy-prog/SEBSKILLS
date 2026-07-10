#!/usr/bin/env python3
"""Static audit for a SEBSKILLS SKILL.md — stage 2 of skill-adder.

Dependency-free (macOS system python3.9, no PyYAML). Parses the leading
frontmatter block and checks the library standard. Exits non-zero on any
BLOCK finding so a pipeline can HALT. Usage:

    python3 audit_static.py skills/<category>/<name>/SKILL.md
"""
import os
import re
import sys

REQUIRED = [
    "name", "category", "description", "when_to_use", "when_not_to_use",
    "keywords", "similar_to", "inputs_needed", "produces", "status",
]
MIN_KEYWORDS, MAX_KEYWORDS = 8, 20
DESC_MIN, DESC_MAX = 120, 800
WHEN_USE_MIN, WHEN_USE_MAX = 3, 7
WHEN_NOT_MIN, WHEN_NOT_MAX = 2, 5


def read_frontmatter(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        raise SystemExit("BLOCK: no --- frontmatter block at top of file")
    return m.group(1), text


def parse_fields(block):
    """Minimal top-level key parser. Values may be inline, block scalar (>),
    or a following indented list. Returns {key: raw_value_or_list}."""
    fields, lines, i = {}, block.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([a-z_]+):(.*)$", line)
        if not m:
            i += 1
            continue
        key, rest = m.group(1), m.group(2).strip()
        if rest in (">", "|", ">-", "|-"):  # folded/block scalar
            buf, i = [], i + 1
            while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
                buf.append(lines[i].strip())
                i += 1
            fields[key] = " ".join(x for x in buf if x).strip()
            continue
        if rest == "":  # possible block list of "- item"
            items, i = [], i + 1
            while i < len(lines) and lines[i].startswith(("  -", "  ", "\t")):
                item = lines[i].strip()
                if item.startswith("- "):
                    items.append(item[2:].strip().strip('"'))
                i += 1
            fields[key] = items
            continue
        fields[key] = rest
        i += 1
    return fields


def as_list(v):
    if isinstance(v, list):
        return v
    s = str(v).strip()
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        return [x.strip().strip('"') for x in inner.split(",")] if inner else []
    return [v] if v else []


def audit(path):
    block, text = read_frontmatter(path)
    f = parse_fields(block)
    folder = os.path.basename(os.path.dirname(os.path.abspath(path)))
    blocks, warns = [], []

    for k in REQUIRED:
        if k not in f:
            blocks.append(f"missing field: {k}")
        elif k != "similar_to" and (f[k] == "" or f[k] == []):
            blocks.append(f"empty field: {k} (only similar_to may be empty)")

    name = str(f.get("name", "")).strip()
    if name and name != folder:
        blocks.append(f"name '{name}' != folder '{folder}'")

    desc = str(f.get("description", ""))
    if not (DESC_MIN <= len(desc) <= DESC_MAX):
        blocks.append(f"description length {len(desc)} outside {DESC_MIN}-{DESC_MAX}")
    if "[[" in desc:
        blocks.append("description contains [[wikilinks]] — strip them")

    kws = as_list(f.get("keywords", []))
    if not (MIN_KEYWORDS <= len(kws) <= MAX_KEYWORDS):
        blocks.append(f"keywords count {len(kws)} outside {MIN_KEYWORDS}-{MAX_KEYWORDS}")

    wu = as_list(f.get("when_to_use", []))
    if not (WHEN_USE_MIN <= len(wu) <= WHEN_USE_MAX):
        blocks.append(f"when_to_use has {len(wu)} items, need {WHEN_USE_MIN}-{WHEN_USE_MAX}")
    wn = as_list(f.get("when_not_to_use", []))
    if not (WHEN_NOT_MIN <= len(wn) <= WHEN_NOT_MAX):
        blocks.append(f"when_not_to_use has {len(wn)} items, need {WHEN_NOT_MIN}-{WHEN_NOT_MAX}")
    # disambiguation: each when_not_to_use should name an alternative
    for item in wn:
        if not re.search(r"->|→|\buse\b|instead", item, re.IGNORECASE):
            warns.append(f"when_not_to_use item names no alternative: {item[:60]!r}")

    if str(f.get("status", "")).strip() != "stable":
        warns.append(f"status is '{f.get('status')}', expected 'stable'")

    # fabricated-flag heuristic: any --flag mentioned in the body should NOT be
    # asserted as verified here; this is a hint for the works-check stage.
    flags = sorted(set(re.findall(r"(?<!-)--[a-z][a-z0-9-]+", text)))
    return blocks, warns, flags


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: audit_static.py <path/to/SKILL.md>")
    blocks, warns, flags = audit(sys.argv[1])
    for w in warns:
        print(f"WARN  {w}")
    for b in blocks:
        print(f"BLOCK {b}")
    if flags:
        print("INFO  --flags to verify in works-check: " + ", ".join(flags))
    if blocks:
        print(f"\nFAIL — {len(blocks)} blocking issue(s). Nothing may be registered.")
        sys.exit(1)
    print("\nPASS — static audit clean.")


if __name__ == "__main__":
    main()
