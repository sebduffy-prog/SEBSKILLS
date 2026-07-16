#!/usr/bin/env bash
# build_chat_zips.sh — package skills for Claude.ai CHAT (Settings -> Capabilities -> Skills)
#
# WHY THIS EXISTS
#   Claude.ai chat (consumer web/desktop/mobile) does NOT understand plugins or
#   marketplaces. It only accepts Skills uploaded as .zip files, one skill per zip,
#   each zip containing a top-level SKILL.md. Its sandbox also has no reliable
#   internet, so the /sebduffy router's "fetch from GitHub on demand" does not work
#   there — a chat skill must be SELF-CONTAINED.
#
#   This script produces upload-ready zips into dist/chat-skills/.
#
# USAGE
#   ./scripts/build_chat_zips.sh router        # just the /sebduffy router (catalogue only)
#   ./scripts/build_chat_zips.sh all           # every skill as its own zip (436 files)
#   ./scripts/build_chat_zips.sh <name> [...]  # named skills, e.g. ffmpeg-cookbook dataviz
#
# Then in Claude.ai: Settings -> Capabilities -> Skills -> Upload skill, pick each zip.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"
OUT="$REPO_ROOT/dist/chat-skills"

mode="${1:-}"
if [[ -z "$mode" ]]; then
  grep -E '^#( |$)' "$0" | sed -E 's/^# ?//'
  exit 1
fi

mkdir -p "$OUT"

# zip one skill folder (must contain SKILL.md) into OUT/<name>.zip, with SKILL.md at
# the zip's top level (Claude.ai requires SKILL.md at the archive root).
zip_skill() {
  local dir="$1"
  [[ -f "$dir/SKILL.md" ]] || { echo "  skip (no SKILL.md): $dir"; return; }
  local name; name="$(basename "$dir")"
  local tmp; tmp="$(mktemp -d)"
  cp -R "$dir" "$tmp/$name"
  ( cd "$tmp/$name" && zip -qr "$OUT/$name.zip" . )
  rm -rf "$tmp"
  echo "  built: dist/chat-skills/$name.zip"
}

case "$mode" in
  router)
    zip_skill "$SKILLS_SRC/meta/sebduffy"
    ;;
  all)
    count=0
    for d in "$SKILLS_SRC"/*/*/; do
      d="${d%/}"; [[ -f "$d/SKILL.md" ]] || continue
      zip_skill "$d"; count=$((count+1))
    done
    echo "Done. $count zips in dist/chat-skills/"
    ;;
  *)
    for want in "$@"; do
      found=""
      for d in "$SKILLS_SRC"/*/"$want"/; do
        [[ -f "${d}SKILL.md" ]] || continue
        zip_skill "${d%/}"; found=1
      done
      [[ -z "$found" ]] && echo "  not found: $want"
    done
    ;;
esac
