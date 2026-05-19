#!/usr/bin/env python3
"""Package every SEBSKILLS skill as a .zip for upload to claude.ai (chat) Skills.

claude.ai chat accepts one .zip per skill. Each zip must contain a SKILL.md
at the root and any reference files alongside it. The YAML `description:`
field has a hard 1024-character limit; longer descriptions are rejected.

This script:
  1. Walks skills/<category>/<skill>/SKILL.md
  2. If the description exceeds 1024 chars, trims it at a sentence/clause
     boundary and prepends the overflow to the body under a
     "## Extended description" heading. Originals in the repo are not
     touched.
  3. Writes dist/<skill-name>.zip per skill, plus dist/seb-skills-all.zip
     containing every per-skill zip for easy bulk download.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
DIST_DIR = ROOT / "dist"
MAX_DESC = 1024

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
DESC_RE = re.compile(
    r"^description:\s*(.+?)(?=\n[a-zA-Z_-]+:\s|\Z)",
    re.DOTALL | re.MULTILINE,
)


def split_description(desc: str, limit: int) -> tuple[str, str]:
    """Split desc into (kept, overflow) so kept <= limit. Prefer sentence breaks."""
    if len(desc) <= limit:
        return desc, ""
    window = desc[: limit - 1]  # leave room for trailing punctuation if we add it
    for sep in (". ", "; ", " — ", " - ", ", "):
        idx = window.rfind(sep)
        if idx > limit * 0.6:  # don't truncate too aggressively
            kept = desc[: idx + len(sep)].rstrip()
            overflow = desc[idx + len(sep):].strip()
            return kept, overflow
    # Fallback: hard cut at last space
    idx = window.rfind(" ")
    if idx <= 0:
        idx = limit - 1
    return desc[:idx].rstrip(), desc[idx:].strip()


def rewrite_skill_md(src: Path) -> str:
    """Return adjusted SKILL.md text, trimming the description if needed."""
    text = src.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return text  # no frontmatter; leave untouched
    fm, body = m.group(1), m.group(2)

    dm = DESC_RE.search(fm)
    if not dm:
        return text
    desc = dm.group(1).strip()
    quote = ""
    if (desc.startswith('"') and desc.endswith('"')) or (
        desc.startswith("'") and desc.endswith("'")
    ):
        quote = desc[0]
        desc = desc[1:-1]

    if len(desc) <= MAX_DESC:
        return text

    kept, overflow = split_description(desc, MAX_DESC)
    new_desc_value = f"{quote}{kept}{quote}" if quote else kept
    new_fm = fm[: dm.start(1)] + new_desc_value + fm[dm.end(1):]

    extra_section = (
        "\n## Extended description\n\n"
        f"{overflow}\n"
    )
    # Insert the extended description right after the first body heading-or-paragraph,
    # but simplest and safest is to put it at the very top of the body.
    new_body = extra_section + ("\n" + body.lstrip("\n") if body.strip() else "")
    return f"---\n{new_fm}\n---\n{new_body}"


def build_zip(skill_dir: Path, dest_zip: Path) -> tuple[str, bool]:
    """Build a zip for one skill. Returns (skill_name, trimmed_description)."""
    skill_name = skill_dir.name
    skill_md = skill_dir / "SKILL.md"
    original = skill_md.read_text(encoding="utf-8")
    rewritten = rewrite_skill_md(skill_md)
    trimmed = rewritten != original

    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / skill_name
        # Copy preserving structure but resolve symlinks (claude.ai needs real files)
        shutil.copytree(skill_dir, staging, symlinks=False)
        (staging / "SKILL.md").write_text(rewritten, encoding="utf-8")

        dest_zip.parent.mkdir(parents=True, exist_ok=True)
        if dest_zip.exists():
            dest_zip.unlink()
        with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(staging.parent))
    return skill_name, trimmed


def main() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    skills = sorted(SKILLS_DIR.glob("*/*/SKILL.md"))
    print(f"Packaging {len(skills)} skills → {DIST_DIR.relative_to(ROOT)}/")
    trimmed_skills: list[str] = []
    for skill_md in skills:
        skill_dir = skill_md.parent
        zip_path = DIST_DIR / f"{skill_dir.name}.zip"
        name, trimmed = build_zip(skill_dir, zip_path)
        marker = "*" if trimmed else " "
        print(f"  {marker} {name}.zip")
        if trimmed:
            trimmed_skills.append(name)

    # Combined bundle
    bundle = DIST_DIR / "seb-skills-all.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_STORED) as zf:
        for zp in sorted(DIST_DIR.glob("*.zip")):
            if zp.name == bundle.name:
                continue
            zf.write(zp, zp.name)

    print()
    print(f"Wrote {len(skills)} per-skill zips + seb-skills-all.zip")
    if trimmed_skills:
        print(
            f"* = description trimmed to fit claude.ai 1024-char limit "
            f"(overflow moved into body, {len(trimmed_skills)} skills)"
        )


if __name__ == "__main__":
    main()
