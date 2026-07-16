#!/usr/bin/env bash
# build_bundled_plugin.sh — make the sebduffy plugin SELF-CONTAINED (no network needed).
#
# WHY
#   The lean plugin ships only the router + embedded catalogue and fetches each skill's
#   body from GitHub on demand. That breaks in sandboxed/cloud Claude Code environments
#   with no network egress (and would break entirely if the GitHub repo ever went away).
#
#   This bundles every skill's files INTO the router skill's own folder, as plain data —
#   NOT as separately-registered skills — so:
#     * still exactly ONE skill loads at session start (no context bloat), and
#     * /sebduffy loads any skill from local disk with zero network.
#   The router already tries `library/<name>/SKILL.md` first (see its load ladder).
#
# USAGE
#   ./scripts/build_bundled_plugin.sh          # bundle all 436 skills into the plugin
#   ./scripts/build_bundled_plugin.sh --clean  # remove the bundle (back to lean plugin)
#
# After running, commit and the plugin is offline-capable for everyone who installs it.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_SRC="$ROOT/skills"
BUNDLE="$ROOT/plugins/sebduffy/skills/sebduffy/library"

if [[ "${1:-}" == "--clean" ]]; then
  rm -rf "$BUNDLE"
  echo "Removed bundle. Plugin is lean again (network-dependent)."
  exit 0
fi

rm -rf "$BUNDLE"
mkdir -p "$BUNDLE"

count=0
for dir in "$SKILLS_SRC"/*/*/; do
  dir="${dir%/}"
  [[ -f "$dir/SKILL.md" ]] || continue
  name="$(basename "$dir")"
  # flat by name (436/436 names are unique) — copy the WHOLE skill folder so bundled
  # scripts/assets/references travel with it.
  cp -R "$dir" "$BUNDLE/$name"
  count=$((count + 1))
done

# manifest gives the router name -> category lookup offline (for skills newer than the catalogue).
cp "$ROOT/manifest.json" "$BUNDLE/manifest.json"

size="$(du -sh "$BUNDLE" | cut -f1)"
echo "Bundled $count skills into plugins/sebduffy/skills/sebduffy/library/ ($size)."
echo "The plugin now loads every skill from local disk — no network required."
echo "Next: git add -A && git commit -m 'feat: self-contained sebduffy plugin (offline)' && git push"
