#!/usr/bin/env bash
# scaffold-vale.sh — create a starter Vale config + house-style package.
# Usage: bash scaffold-vale.sh [TARGET_DIR] [STYLE_NAME]
# Defaults: TARGET_DIR=. STYLE_NAME=House
# Idempotent-ish: refuses to clobber an existing .vale.ini.
set -euo pipefail

TARGET="${1:-.}"
STYLE="${2:-House}"
STYLES_DIR="$TARGET/styles"
PKG_DIR="$STYLES_DIR/$STYLE"

if [ -f "$TARGET/.vale.ini" ]; then
  echo "refusing to overwrite existing $TARGET/.vale.ini" >&2
  exit 1
fi

mkdir -p "$PKG_DIR"

cat > "$TARGET/.vale.ini" <<EOF
StylesPath = styles
MinAlertLevel = suggestion

# 'vale sync' downloads these into StylesPath.
Packages = Google, proselint, write-good

[*.{md,txt,html}]
BasedOnStyles = Vale, Google, $STYLE
# Silence rules you disagree with, e.g.:
# Google.Headings = NO
EOF

# Substitution rule: banned/preferred terms (UK spelling + brand words).
cat > "$PKG_DIR/Terms.yml" <<'EOF'
extends: substitution
message: "Prefer '%s' over '%s'."
level: warning
ignorecase: true
# Regex on the left, replacement on the right.
swap:
  utili(s|z)e: use
  in order to: to
  leverage: use
  (?:web ?site): website
  e-mail: email
  organiz(e|ation): organis$1
EOF

# Existence rule: hard-banned words/phrases.
cat > "$PKG_DIR/Banned.yml" <<'EOF'
extends: existence
message: "Avoid '%s'."
level: error
ignorecase: true
tokens:
  - very
  - synergy
  - low-hanging fruit
  - moving forward
EOF

# Metric rule: Flesch-Kincaid grade-level ceiling.
cat > "$PKG_DIR/Readability.yml" <<'EOF'
extends: metric
message: "Try to keep the grade level (%s) below 10."
link: https://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_tests
formula: |
  (0.39 * (words / sentences)) + (11.8 * (syllables / words)) - 15.59
condition: "> 10"
EOF

echo "Scaffolded Vale config at: $TARGET/.vale.ini"
echo "House-style package at:    $PKG_DIR"
echo "Next: vale sync && vale <your-file.md>"
