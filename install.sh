#!/usr/bin/env bash
# SEBSKILLS installer
#
# Installs this repo's skills into a location Claude Code auto-discovers.
# Modes:
#   user     → ~/.claude/skills/            (every Claude Code session on this machine)
#   project  → ./.claude/skills/            (only the project you run this from)
#   web      → prints instructions only     (nothing to install; Claude Code Web auto-discovers
#                                            any SKILL.md in a connected repo)
#
# Usage:
#   ./install.sh user
#   ./install.sh project [path-to-project]
#   ./install.sh web

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_SRC="$REPO_ROOT/skills"

mode="${1:-}"
if [[ -z "$mode" ]]; then
  cat <<EOF
SEBSKILLS installer

Usage:
  ./install.sh user                   # link into ~/.claude/skills/
  ./install.sh project [path]         # link into <path>/.claude/skills/ (default: cwd)
  ./install.sh web                    # print instructions for Claude Code Web

What it does: creates one symlink per skill under the target .claude/skills/
directory. Existing links to this repo are overwritten; unrelated files are
left alone.
EOF
  exit 1
fi

link_skills() {
  local target="$1"
  mkdir -p "$target"
  local count=0
  for skill_dir in "$SKILLS_SRC"/*/*/; do
    skill_dir="${skill_dir%/}"
    [[ -f "$skill_dir/SKILL.md" ]] || continue
    local name
    name="$(basename "$skill_dir")"
    local link="$target/$name"
    if [[ -L "$link" ]]; then
      rm "$link"
    elif [[ -e "$link" ]]; then
      echo "  skip: $link exists and is not a symlink (leaving alone)"
      continue
    fi
    ln -s "$skill_dir" "$link"
    count=$((count + 1))
  done
  echo "Linked $count skills into $target"
}

case "$mode" in
  user)
    link_skills "$HOME/.claude/skills"
    ;;
  project)
    proj="${2:-$PWD}"
    if [[ ! -d "$proj" ]]; then
      echo "Error: $proj is not a directory" >&2
      exit 1
    fi
    link_skills "$proj/.claude/skills"
    ;;
  web)
    cat <<EOF
Claude Code Web auto-discovers any directory containing SKILL.md in a
connected repo. You have two options:

  1. Add this repo as a git submodule in your project:
       git submodule add https://github.com/sebduffy-prog/sebskills .claude/skills-lib
       git commit -m "Add SEBSKILLS"
     Push, then open the project in claude.ai/code. Every skill under
     .claude/skills-lib/skills/ becomes available automatically.

  2. Connect this repo directly in Claude Code Web as a secondary repo
     alongside your project. The web harness loads skills from all
     connected repos.

No symlinking is required for web. This installer is for the CLI /
desktop / IDE versions, where symlinks into ~/.claude/skills/ or
<project>/.claude/skills/ are needed for auto-discovery.
EOF
    ;;
  *)
    echo "Unknown mode: $mode (expected: user | project | web)" >&2
    exit 1
    ;;
esac
