#!/usr/bin/env bash
# Rank skills by how many query terms hit their SKILL.md frontmatter
# (name + description + when_to_use + keywords). Discovery beats guessing.
#
# Usage: find_candidates.sh "term1 term2 term3" [SKILLS_ROOT]
set -euo pipefail

TERMS="${1:?usage: find_candidates.sh \"terms...\" [skills_root]}"
ROOT="${2:-/Users/seb.duffy/Documents/GitHub/SEBSKILLS/skills}"

if [[ ! -d "$ROOT" ]]; then
  echo "skills root not found: $ROOT" >&2
  exit 1
fi

# Score each SKILL.md by number of distinct query terms it matches (case-insensitive).
while IFS= read -r skill; do
  score=0
  hits=""
  for term in $TERMS; do
    if grep -qi -- "$term" "$skill" 2>/dev/null; then
      score=$((score + 1))
      hits="$hits $term"
    fi
  done
  if [[ "$score" -gt 0 ]]; then
    # skills/<category>/<name>/SKILL.md -> category/name
    label=$(printf '%s\n' "$skill" | sed -E "s#^.*/skills/##; s#/SKILL.md\$##")
    printf '%d\t%s\t(%s )\n' "$score" "$label" "${hits# }"
  fi
done < <(find "$ROOT" -name SKILL.md) | sort -rn | head -12
