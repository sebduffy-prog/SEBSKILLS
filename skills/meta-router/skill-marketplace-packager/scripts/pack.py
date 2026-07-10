#!/usr/bin/env python3
"""Pack SEBSKILLS SKILL.md files into per-harness bundles.

Dependency-free (macOS system python3.9). Reads one or more SKILL.md files,
builds a shared manifest, and emits a native bundle for each target harness:
claude, cursor, opencode, copilot, codex, gemini.

Usage:
  pack.py --skills <dir-or-SKILL.md> [more...] --out <dir> \
          [--targets claude,cursor,opencode,copilot,codex,gemini]

The SKILL.md body (everything after frontmatter) is the instruction payload.
Only `name` and `description` are lifted from frontmatter; both are required.
"""
import argparse
import json
import os
import re
import sys

TARGETS = ["claude", "cursor", "opencode", "copilot", "codex", "gemini"]


def parse_skill(path):
    """Return {name, description, keywords, category, body} from a SKILL.md.

    Minimal frontmatter reader: handles `key: value`, folded `key: >` blocks,
    and inline `[a, b]` lists for the few fields we need. Body is verbatim.
    """
    text = open(path, encoding="utf-8").read()
    if not text.startswith("---"):
        raise ValueError(f"{path}: no YAML frontmatter")
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError(f"{path}: unterminated frontmatter")
    fm = text[3:end].strip("\n")
    body = text[end + 4 :].lstrip("\n")

    fields = {}
    lines = fm.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).rstrip()
        if val == ">" or val == "|":  # folded/literal block: gather indented
            block = []
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i] == ""):
                block.append(lines[i].strip())
                i += 1
            fields[key] = " ".join(x for x in block if x).strip()
            continue
        fields[key] = val
        i += 1

    name = fields.get("name", "").strip()
    desc = fields.get("description", "").strip().strip('"')
    if not name or not desc:
        raise ValueError(f"{path}: name and description are required")
    kw = fields.get("keywords", "").strip("[] ")
    keywords = [k.strip() for k in kw.split(",") if k.strip()] if kw else []
    return {
        "name": name,
        "description": " ".join(desc.split()),  # collapse to one line
        "keywords": keywords,
        "category": fields.get("category", "").strip(),
        "body": body,
        "source": path,
    }


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def emit_claude(s, out):
    # Native Claude skill: SKILL.md verbatim (frontmatter round-trips).
    body = open(s["source"], encoding="utf-8").read()
    _write(os.path.join(out, "claude", "skills", s["name"], "SKILL.md"), body)


def emit_cursor(s, out):
    fm = f"---\ndescription: {s['description']}\nglobs: []\nalwaysApply: false\n---\n\n"
    _write(os.path.join(out, "cursor", ".cursor", "rules", s["name"] + ".mdc"), fm + s["body"])


def emit_opencode(s, out):
    fm = f"---\ndescription: {s['description']}\nmode: subagent\n---\n\n"
    _write(os.path.join(out, "opencode", ".opencode", "agents", s["name"] + ".md"), fm + s["body"])


def emit_copilot(s, out):
    fm = f"---\nmode: agent\ndescription: {s['description']}\n---\n\n"
    _write(os.path.join(out, "copilot", ".github", "prompts", s["name"] + ".prompt.md"), fm + s["body"])


def emit_codex(s, out):
    # Codex custom prompt (top-level md, /name invocation).
    fm = f"---\ndescription: {s['description']}\nargument-hint: \"[context]\"\n---\n\n"
    _write(os.path.join(out, "codex", ".codex", "prompts", s["name"] + ".md"), fm + s["body"])


def emit_gemini(s, out):
    desc = s["description"].replace("\\", "\\\\").replace('"', '\\"')
    body = s["body"].replace("\\", "\\\\").replace('"', '\\"')
    toml = f'description = "{desc}"\nprompt = """\n{body}\n"""\n'
    _write(os.path.join(out, "gemini", ".gemini", "commands", s["name"] + ".toml"), toml)


EMITTERS = {
    "claude": emit_claude,
    "cursor": emit_cursor,
    "opencode": emit_opencode,
    "copilot": emit_copilot,
    "codex": emit_codex,
    "gemini": emit_gemini,
}


def collect(inputs):
    paths = []
    for p in inputs:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                if "SKILL.md" in files:
                    paths.append(os.path.join(root, "SKILL.md"))
        elif p.endswith("SKILL.md"):
            paths.append(p)
        else:
            print(f"skip (not a SKILL.md or dir): {p}", file=sys.stderr)
    return sorted(set(paths))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--targets", default=",".join(TARGETS))
    args = ap.parse_args()

    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    bad = [t for t in targets if t not in EMITTERS]
    if bad:
        sys.exit(f"unknown target(s): {bad}. valid: {TARGETS}")

    manifest = {"skills": []}
    errors = []
    for path in collect(args.skills):
        try:
            s = parse_skill(path)
        except ValueError as e:
            errors.append(str(e))
            continue
        for t in targets:
            EMITTERS[t](s, args.out)
        manifest["skills"].append(
            {"name": s["name"], "category": s["category"],
             "description": s["description"], "keywords": s["keywords"],
             "source": s["source"], "targets": targets}
        )

    _write(os.path.join(args.out, "manifest.json"), json.dumps(manifest, indent=2))
    print(f"packed {len(manifest['skills'])} skill(s) -> {args.out} for {targets}")
    if errors:
        print("ERRORS:", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
