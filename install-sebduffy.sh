#!/usr/bin/env bash
# Install the ONE file that unlocks the whole SEBSKILLS library: the /sebduffy router.
#
# After this, typing `/sebduffy <what you want>` in any Claude Code session routes to the
# best skill from the 300+ library and loads it on demand — whether or not the individual
# skills are installed locally.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/install-sebduffy.sh | bash
#   # or, from a local clone:  ./install-sebduffy.sh --local
set -euo pipefail

DEST="$HOME/.claude/skills/sebduffy"
RAW="https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/skills/meta/sebduffy/SKILL.md"

mkdir -p "$DEST"

if [[ "${1:-}" == "--local" ]]; then
  SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skills/meta/sebduffy/SKILL.md"
  cp "$SRC" "$DEST/SKILL.md"
  echo "Installed /sebduffy from local clone → $DEST/SKILL.md"
else
  curl -fsSL "$RAW" -o "$DEST/SKILL.md"
  echo "Installed /sebduffy → $DEST/SKILL.md"
fi

echo
echo "Done. Start a Claude Code session and type:  /sebduffy <what you want to do>"
echo "  /sebduffy list                 # browse the catalogue"
echo "  /sebduffy media                # list a category"
echo "  /sebduffy make a bento grid    # route to the right skill and load it"
echo
echo "The whole library is reachable from this one file — new skills appear automatically."
