#!/usr/bin/env bash
# Install the ONE file that unlocks the whole SEBSKILLS library: the /sebduffy router.
#
# After this, typing `/sebduffy <what you want>` in any Claude Code session routes to the
# best skill from the 300+ library and loads it on demand — whether or not the individual
# skills are installed locally.
#
# Claude Code (CLI, desktop, AND web at claude.ai/code) discovers skills ONLY at
#   .claude/skills/<name>/SKILL.md   — never a claude.ai account "customize" toggle.
# So this installs the router into a location Claude Code actually scans.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/install-sebduffy.sh | bash
#       → ~/.claude/skills/sebduffy/   (personal; every CLI/desktop session on this machine)
#   ./install-sebduffy.sh --local
#       → same, copied from a local clone instead of fetched
#   ./install-sebduffy.sh --project [path]
#       → <path>/.claude/skills/sebduffy/   (commit + push this for Claude Code WEB:
#          web only sees .claude/skills/ in the repo you OPEN as the project)
set -euo pipefail

RAW="https://raw.githubusercontent.com/sebduffy-prog/SEBSKILLS/main/skills/meta/sebduffy/SKILL.md"
LOCAL_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skills/meta/sebduffy/SKILL.md"

mode="${1:-}"
if [[ "$mode" == "--project" ]]; then
  proj="${2:-$PWD}"
  DEST="$proj/.claude/skills/sebduffy"
else
  DEST="$HOME/.claude/skills/sebduffy"
fi

mkdir -p "$DEST"
if [[ "$mode" == "--local" || ( "$mode" == "--project" && -f "$LOCAL_SRC" ) ]]; then
  cp "$LOCAL_SRC" "$DEST/SKILL.md"
  echo "Installed /sebduffy (from local clone) → $DEST/SKILL.md"
else
  curl -fsSL "$RAW" -o "$DEST/SKILL.md"
  echo "Installed /sebduffy → $DEST/SKILL.md"
fi

if [[ "$mode" == "--project" ]]; then
  echo "For Claude Code Web: commit and push this file, then open the project at claude.ai/code."
fi

echo
echo "Done. Start a Claude Code session and type:  /sebduffy <what you want to do>"
echo "  /sebduffy list                 # browse the catalogue"
echo "  /sebduffy media                # list a category"
echo "  /sebduffy make a bento grid    # route to the right skill and load it"
echo
echo "The whole library is reachable from this one file — new skills appear automatically."
