#!/usr/bin/env bash
# Repoint the entire library off one GitHub account onto another — run once after
# forking for handover, so nothing depends on the original owner's account.
#
#   ./scripts/repoint.sh <new-owner> [new-repo]
#   e.g.  ./scripts/repoint.sh vccp-media          (repo stays "SEBSKILLS")
#         ./scripts/repoint.sh alice SkillLibrary
#
# It rewrites every sebduffy-prog/SebDuffy reference (install scripts, docs, the
# router, and the raw URLs baked into skill bodies), then regenerates the manifest,
# catalogue, router index and the .claude/skills + plugin mirrors, and runs the gate.
set -euo pipefail

OWNER="${1:?usage: ./scripts/repoint.sh <new-owner> [new-repo]}"
REPO="${2:-SEBSKILLS}"
OLD="sebduffy-prog/SebDuffy"
NEW="$OWNER/$REPO"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

files="$(grep -rl "$OLD" . --exclude-dir=.git || true)"
if [[ -z "$files" ]]; then
  echo "Nothing to repoint — no '$OLD' references found (already $NEW?)."
else
  n=0
  while IFS= read -r f; do
    perl -pi -e "s{\Q$OLD\E}{$NEW}g" "$f"
    n=$((n + 1))
  done <<< "$files"
  echo "Repointed $n files: $OLD -> $NEW"
fi

python3 scripts/build_manifest.py >/dev/null
echo "Regenerated manifest / catalogue / router index / mirrors."
python3 scripts/build_manifest.py --check

echo
echo "Done. Review, then publish:"
echo "  git add -A && git commit -m 'chore: repoint to $NEW' && git push"
