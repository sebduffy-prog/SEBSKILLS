#!/usr/bin/env bash
# SEBSKILLS installer
#
# Installs this repo's skills into a location Claude Code auto-discovers.
# Modes:
#   user     → ~/.claude/skills/            (every Claude Code session on this machine)
#   project  → ./.claude/skills/            (only the project you run this from)
#   web      → prints instructions          (Claude Code Web only discovers .claude/skills/<name>/
#                                            in the repo you OPEN — commit the router there)
#
# IMPORTANT: Claude Code (CLI, desktop, AND web) only discovers skills at
#   .claude/skills/<skill-name>/SKILL.md   (one directory deep; dir name = /command)
# It does NOT scan this repo's skills/<category>/<name>/ tree. That is why the
# installer links each skill's folder (by name) into a .claude/skills/ directory.
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
  one)
    # Install ONLY the /sebduffy router — the single file that reaches the whole library.
    target="$HOME/.claude/skills/sebduffy"
    mkdir -p "$target"
    ln -sf "$SKILLS_SRC/meta/sebduffy/SKILL.md" "$target/SKILL.md"
    echo "Linked /sebduffy → $target/SKILL.md"
    echo "Type '/sebduffy <intent>' in any Claude Code session to reach the whole library."
    ;;
  web)
    cat <<EOF
Claude Code Web discovers skills ONLY at .claude/skills/<name>/SKILL.md in the
repo you open as the project (symlinks aren't reliable in the web checkout, so
commit REAL files). It does not scan a "skills/<category>/<name>/" tree, and it
does not reliably load skills from a secondary connected repo — so a git
submodule or "connect this repo too" does NOT work.

Recommended — the one-upload door (just the router; the library loads on demand):

  cd <your-project>
  mkdir -p .claude/skills/sebduffy
  curl -fsSL https://raw.githubusercontent.com/sebduffy-prog/SebDuffy/main/skills/meta/sebduffy/SKILL.md \\
    -o .claude/skills/sebduffy/SKILL.md
  git add .claude/skills/sebduffy && git commit -m "add /sebduffy" && git push

  Then open that project in claude.ai/code and type: /sebduffy <what you want>
  (Equivalent one-liner: ./install-sebduffy.sh --project <your-project>)

Whole library committed instead of load-on-demand? Copy every skill as a real
folder into .claude/skills/ (flat, folder name = /command), commit and push:

  for d in "$SKILLS_SRC"/*/*/; do cp -R "\$d" .claude/skills/; done

Opening THIS repo directly in web already works: it ships .claude/skills/sebduffy/.
EOF
    ;;
  *)
    echo "Unknown mode: $mode (expected: user | project | web)" >&2
    exit 1
    ;;
esac
