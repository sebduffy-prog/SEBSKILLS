#!/usr/bin/env python3
"""Pack SKILL.md files into per-harness bundles — hardened for real trees.

Additions over the stock pack.py:
  1. Symlink-aware collect (followlinks + realpath de-dup, loop guard) so a
     library that is mostly symlinked in is not silently skipped.
  2. Graceful frontmatter: a missing `name` falls back to the folder name; a
     missing `description` falls back to the first H1 / first prose line. No
     valid skill fails the build just because its frontmatter is thin.
  3. Name-collision handling: identical `name`s no longer silently overwrite.
     First wins; the rest are reported and skipped (or --on-collision=namespace
     to keep them all, prefixed by category).

Usage:
  pack2.py --skills <dir-or-SKILL.md> [more...] --out <dir>
           [--targets claude,cursor,opencode,copilot,codex,gemini]
           [--on-collision skip|namespace] [--strict]
"""
import argparse
import json
import os
import re
import sys

TARGETS = ["claude", "cursor", "opencode", "copilot", "codex", "gemini"]


def _derive_description(body, name):
    in_fence = False
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("```"):                      # skip fenced code blocks
            in_fence = not in_fence
            continue
        if in_fence or not s:
            continue
        if s.startswith("#"):                        # first markdown heading
            h = s.lstrip("#").strip()
            if h.lower().startswith("preamble"):     # boilerplate, not a desc
                continue
            return h
        if s.startswith(("---", "<!--", "|", ">")):
            continue
        if re.match(r"^[a-zA-Z_]+:\s", s):           # leaked frontmatter line
            continue
        return s                                     # first real prose line
    return name                                      # nothing usable -> name


def parse_skill(path):
    text = open(path, encoding="utf-8").read()
    fm, body = "", text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end].strip("\n")
            body = text[end + 4:].lstrip("\n")

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
        if val in (">", "|"):
            block = []
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i] == ""):
                block.append(lines[i].strip())
                i += 1
            fields[key] = " ".join(x for x in block if x).strip()
            continue
        fields[key] = val
        i += 1

    folder = os.path.basename(os.path.dirname(os.path.realpath(path)))
    name = fields.get("name", "").strip() or folder
    derived = []
    if not fields.get("name", "").strip():
        derived.append("name")
    desc = fields.get("description", "").strip().strip('"')
    if not desc:
        desc = _derive_description(body, name)
        derived.append("description")
    kw = fields.get("keywords", "").strip("[] ")
    keywords = [k.strip() for k in kw.split(",") if k.strip()] if kw else []
    return {
        "name": name,
        "description": " ".join(desc.split()),
        "keywords": keywords,
        "category": fields.get("category", "").strip(),
        "body": body,
        "source": path,
        "derived": derived,
    }


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def emit_claude(s, out):
    _write(os.path.join(out, "claude", "skills", s["name"], "SKILL.md"),
           open(s["source"], encoding="utf-8").read())


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
    fm = f"---\ndescription: {s['description']}\nargument-hint: \"[context]\"\n---\n\n"
    _write(os.path.join(out, "codex", ".codex", "prompts", s["name"] + ".md"), fm + s["body"])


def emit_gemini(s, out):
    desc = s["description"].replace("\\", "\\\\").replace('"', '\\"')
    body = s["body"].replace("\\", "\\\\").replace('"', '\\"')
    _write(os.path.join(out, "gemini", ".gemini", "commands", s["name"] + ".toml"),
           f'description = "{desc}"\nprompt = """\n{body}\n"""\n')


EMITTERS = {"claude": emit_claude, "cursor": emit_cursor, "opencode": emit_opencode,
            "copilot": emit_copilot, "codex": emit_codex, "gemini": emit_gemini}


def collect(inputs):
    """Find every SKILL.md, following symlinks, with a loop + duplicate guard."""
    paths, seen_files, seen_dirs = [], set(), set()
    for p in inputs:
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p, followlinks=True):
                real = os.path.realpath(root)
                if real in seen_dirs:            # symlink cycle -> stop descending
                    dirs[:] = []
                    continue
                seen_dirs.add(real)
                if "SKILL.md" in files:
                    rp = os.path.realpath(os.path.join(root, "SKILL.md"))
                    if rp not in seen_files:     # same real file via 2 symlinks
                        seen_files.add(rp)
                        paths.append(os.path.join(root, "SKILL.md"))
        elif p.endswith("SKILL.md"):
            rp = os.path.realpath(p)
            if rp not in seen_files:
                seen_files.add(rp)
                paths.append(p)
        else:
            print(f"skip (not a SKILL.md or dir): {p}", file=sys.stderr)
    return sorted(paths)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--targets", default=",".join(TARGETS))
    ap.add_argument("--on-collision", choices=["skip", "namespace"], default="skip")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if any skill needed a derived name/description")
    args = ap.parse_args()

    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    bad = [t for t in targets if t not in EMITTERS]
    if bad:
        sys.exit(f"unknown target(s): {bad}. valid: {TARGETS}")

    manifest, taken, collisions, derived = {"skills": []}, {}, [], []
    for path in collect(args.skills):
        s = parse_skill(path)
        if s["derived"]:
            derived.append((s["source"], s["derived"]))
        name = s["name"]
        if name in taken:
            if args.on_collision == "skip":
                collisions.append((name, s["source"], taken[name]))
                continue
            name = (s["category"] + "-" + name) if s["category"] else name
            if name in taken:
                collisions.append((s["name"], s["source"], taken[s["name"]]))
                continue
            s["name"] = name
        taken[name] = s["source"]
        for t in targets:
            EMITTERS[t](s, args.out)
        manifest["skills"].append(
            {"name": s["name"], "category": s["category"], "description": s["description"],
             "keywords": s["keywords"], "source": s["source"], "targets": targets,
             "derived": s["derived"]})

    _write(os.path.join(args.out, "manifest.json"), json.dumps(manifest, indent=2))
    print(f"packed {len(manifest['skills'])} unique skill(s) -> {args.out} for {targets}")
    if derived:
        print(f"derived frontmatter for {len(derived)} skill(s) (folder name / first heading)")
    if collisions:
        print(f"skipped {len(collisions)} name collision(s) [--on-collision={args.on_collision}]")
        from collections import Counter
        for n, c in Counter(n for n, _, _ in collisions).most_common(10):
            print(f"    {c:>3}x  {n}")
    if args.strict and derived:
        sys.exit(1)


if __name__ == "__main__":
    main()
