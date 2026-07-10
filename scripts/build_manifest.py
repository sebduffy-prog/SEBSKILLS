#!/usr/bin/env python3
"""Build the SEBSKILLS manifest.

Walks skills/<category>/<name>/SKILL.md, parses the frontmatter, and:
  - writes manifest.json          (the machine-readable index the router + MCP server consume)
  - splices a compact index into  skills/meta/sebduffy/SKILL.md  between the MANIFEST markers
  - writes REPORT.md              (health: per-category counts, enriched %, ranking-blind skills)

Usage:
  python3 scripts/build_manifest.py            # generate everything
  python3 scripts/build_manifest.py --check    # validate only, non-zero exit on any error (CI gate)

Node isn't required on this machine; this is the source of truth for manifest.json regardless of language.
"""
import json, os, re, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
REQUIRED = ["name", "category", "description", "when_to_use", "when_not_to_use",
            "keywords", "similar_to", "inputs_needed", "produces", "status"]
BEGIN, END = "<!-- BEGIN:MANIFEST", "<!-- END:MANIFEST"


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    lines = text[3:end].splitlines()
    data, i = {}, 0
    while i < len(lines):
        m = re.match(r"^([a-zA-Z_]+):\s*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in (">", "|", ">-", "|-", "") and i + 1 < len(lines) and lines[i + 1].startswith("  "):
            block, i = [], i + 1
            is_list = lines[i].lstrip().startswith("- ")
            while i < len(lines) and (lines[i].startswith("  ") or lines[i].strip() == ""):
                s = lines[i].strip()
                if s:
                    block.append(s[2:].strip().strip('"\'') if is_list and s.startswith("- ") else s)
                i += 1
            data[key] = block if is_list else " ".join(block)
            continue
        if val.startswith("[") and val.endswith("]"):
            data[key] = [x.strip().strip('"\'') for x in val[1:-1].split(",") if x.strip()]
        else:
            data[key] = val.strip('"\'')
        i += 1
    return data


def load_skills():
    out = []
    for cat in sorted(os.listdir(SKILLS)):
        cat_dir = os.path.join(SKILLS, cat)
        if not os.path.isdir(cat_dir):
            continue
        for name in sorted(os.listdir(cat_dir)):
            path = os.path.join(cat_dir, name, "SKILL.md")
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as fh:
                fm = parse_frontmatter(fh.read())
            fm["_folder"], fm["_cat"] = name, cat
            fm["_path"] = os.path.relpath(path, ROOT)
            out.append(fm)
    return out


def trigger(desc):
    d = re.sub(r"\s+", " ", (desc or "")).strip()
    cut = d.find(". ")
    return (d[:cut] if 0 < cut < 140 else d[:140]).rstrip(" .,")


def check(skills):
    errors = []
    seen = {}
    for s in skills:
        who = s.get("_path", "?")
        for k in REQUIRED:
            v = s.get(k)
            if v is None:
                errors.append(f"{who}: missing '{k}'")
            elif isinstance(v, (str, list)) and len(v) == 0 and k != "similar_to":
                # similar_to may legitimately be [] per the standard
                errors.append(f"{who}: empty '{k}'")
        if s.get("name") != s.get("_folder"):
            errors.append(f"{who}: name '{s.get('name')}' != folder '{s.get('_folder')}'")
        if s.get("category") != s.get("_cat"):
            errors.append(f"{who}: category '{s.get('category')}' != folder '{s.get('_cat')}'")
        kw = s.get("keywords") or []
        if len(kw) < 1:
            errors.append(f"{who}: zero keywords (ranks blind)")
        n = s.get("name")
        if n in seen:
            errors.append(f"{who}: duplicate name '{n}' (also {seen[n]})")
        seen[n] = who
    return errors


def build(skills):
    records = []
    for s in skills:
        kw = s.get("keywords") or []
        records.append({
            "name": s.get("name", s["_folder"]),
            "category": s.get("category", s["_cat"]),
            "path": s["_path"],
            "description": s.get("description", ""),
            "trigger": trigger(s.get("description", "")),
            "when_to_use": s.get("when_to_use", []),
            "when_not_to_use": s.get("when_not_to_use", []),
            "keywords": kw,
            "similar_to": s.get("similar_to", []),
            "produces": s.get("produces", ""),
            "status": s.get("status", ""),
            "keywordCount": len(kw),
            "enriched": len(kw) >= 8 and bool(s.get("when_to_use")),
        })
    cats = sorted({r["category"] for r in records})
    manifest = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "skillCount": len(records),
        "categories": cats,
        "ref": "main",
        "rawBase": "https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/",
        "skills": records,
    }
    with open(os.path.join(ROOT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    # compact, grouped index for the router SKILL.md (short triggers, no table markup)
    from collections import defaultdict as _dd
    by = _dd(list)
    for r in records:
        by[r["category"]].append(r)
    lines = []
    for cat in sorted(by):
        lines.append(f"\n**{cat}** ({len(by[cat])})")
        for r in sorted(by[cat], key=lambda x: x["name"]):
            t = (r["trigger"] or "")[:76].rstrip(" .,;:")
            lines.append(f"- `{r['name']}` — {t}")
    block = "\n".join(lines).strip()
    splice_router(block, len(records))

    write_report(records, cats)
    write_catalog(records)
    return manifest


def write_catalog(records):
    from collections import defaultdict as _dd
    by = _dd(list)
    for r in records:
        by[r["category"]].append(r)
    lines = ["# SEBSKILLS — full catalogue", "",
             f"_Auto-generated by `scripts/build_manifest.py` — **{len(records)} skills** across "
             f"**{len(by)} categories**. Do not edit by hand._", "",
             "Type `/sebduffy <what you want>` to route to any of these automatically, or "
             "`/sebduffy <category>` to browse one.", ""]
    for cat in sorted(by):
        lines.append(f"\n## {cat} · {len(by[cat])}\n")
        for r in sorted(by[cat], key=lambda x: x["name"]):
            lines.append(f"- **`{r['name']}`** — {r['trigger']}")
    with open(os.path.join(ROOT, "CATALOG.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def splice_router(block, n):
    router = os.path.join(SKILLS, "meta", "sebduffy", "SKILL.md")
    if not os.path.isfile(router):
        print(f"  (router not found at {router} — skipping splice)")
        return
    with open(router, encoding="utf-8") as fh:
        txt = fh.read()
    b, e = txt.find(BEGIN), txt.find(END)
    if b == -1 or e == -1:
        print("  (MANIFEST markers not found in router — skipping splice)")
        return
    b_end = txt.find("-->", b) + 3
    new = (txt[:b_end] + f"\n_Generated index — {n} skills. Do not edit by hand._\n\n"
           + block + "\n\n" + txt[e:])
    with open(router, "w", encoding="utf-8") as fh:
        fh.write(new)
    print(f"  spliced {n}-skill index into router")


def write_report(records, cats):
    from collections import Counter
    by_cat = Counter(r["category"] for r in records)
    enriched = sum(1 for r in records if r["enriched"])
    blind = [r for r in records if r["keywordCount"] < 8]
    lines = ["# SEBSKILLS — library health report", "",
             f"- **Total skills:** {len(records)}",
             f"- **Categories:** {len(cats)}",
             f"- **Enriched (>=8 keywords + when_to_use):** {enriched}/{len(records)} "
             f"({round(100*enriched/len(records))}%)",
             f"- **Ranking-blind (<8 keywords):** {len(blind)}", "",
             "## Skills per category", "", "| category | count |", "|---|---|"]
    for c in sorted(by_cat, key=lambda c: -by_cat[c]):
        flag = " ⚠️ over 18" if by_cat[c] > 18 else ""
        lines.append(f"| {c} | {by_cat[c]}{flag} |")
    if blind:
        lines += ["", "## Ranking-blind skills (backfill keywords)", ""]
        lines += [f"- `{r['name']}` ({r['category']}) — {r['keywordCount']} keywords" for r in blind]
    with open(os.path.join(ROOT, "REPORT.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main():
    skills = load_skills()
    errors = check(skills)
    if "--check" in sys.argv:
        if errors:
            print(f"FAIL — {len(errors)} issue(s):")
            for e in errors[:80]:
                print("  " + e)
            sys.exit(1)
        print(f"OK — {len(skills)} skills valid")
        return
    if errors:
        print(f"WARNING — {len(errors)} frontmatter issue(s) (see below); building anyway:")
        for e in errors[:40]:
            print("  " + e)
    m = build(skills)
    print(f"Built manifest.json ({m['skillCount']} skills, {len(m['categories'])} categories) + REPORT.md")


if __name__ == "__main__":
    main()
