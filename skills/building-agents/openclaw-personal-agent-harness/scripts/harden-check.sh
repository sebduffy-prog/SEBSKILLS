#!/usr/bin/env bash
# harden-check.sh — read-only preflight audit of an OpenClaw gateway config.
# Flags the risky settings that turn a personal assistant into an open shell.
# Usage: bash harden-check.sh [~/.openclaw/openclaw.json]
# Requires: python3 (3.9+ ok). Never writes; exits non-zero if any WARN found.

set -euo pipefail
CFG="${1:-$HOME/.openclaw/openclaw.json}"

if [ ! -f "$CFG" ]; then
  echo "FATAL: config not found: $CFG" >&2
  echo "Run 'openclaw onboard --install-daemon' first, or pass the path." >&2
  exit 2
fi

python3 - "$CFG" <<'PY'
import json, sys
path = sys.argv[1]
raw = open(path, "r", encoding="utf-8").read()
try:
    cfg = json.loads(raw)
except Exception as e:
    # OpenClaw accepts JSON5-ish configs; fall back to substring heuristics.
    print(f"NOTE: could not strict-parse JSON ({e}); using text heuristics.")
    cfg = None

warns = 0
def warn(msg):
    global warns
    warns += 1
    print(f"WARN: {msg}")
def ok(msg):
    print(f"OK:   {msg}")

def dig(d, *keys):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d

if cfg is not None:
    # 1) DM policy must not be globally open.
    channels = dig(cfg, "channels") or {}
    open_dm = False
    def scan(node):
        global open_dm
        if isinstance(node, dict):
            if node.get("dmPolicy") == "open":
                open_dm = True
            for v in node.values():
                scan(v)
        elif isinstance(node, list):
            for v in node:
                scan(v)
    scan(channels)
    scan(dig(cfg, "agents") or {})
    if open_dm:
        warn('dmPolicy="open" found — anyone messaging the bot is processed. Prefer "pairing".')
    else:
        ok('no dmPolicy="open" (unknown senders gated by pairing).')

    # 2) Sandbox mode should not be "off".
    mode = dig(cfg, "agents", "defaults", "sandbox", "mode")
    if mode == "off":
        warn('agents.defaults.sandbox.mode="off" — no isolation. Use "non-main" or "all".')
    elif mode in ("non-main", "all"):
        ok(f'sandbox.mode="{mode}".')
    else:
        warn('agents.defaults.sandbox.mode unset — default may not isolate group sessions. Set "non-main".')

    # 3) Skills allowlist should be explicit (least privilege).
    skills = dig(cfg, "agents", "defaults", "skills")
    if skills is None:
        warn("agents.defaults.skills unset — every installed skill is exposed. Pin an explicit allowlist.")
    elif isinstance(skills, list) and "*" in skills:
        warn('skills allowlist contains "*" — grants all skills. Enumerate instead.')
    else:
        ok(f"skills allowlist explicit ({len(skills) if isinstance(skills, list) else '?'} entries).")
else:
    for needle, msg in [
        ('"open"', 'possible dmPolicy="open" — verify manually.'),
        ('"off"', 'possible sandbox.mode="off" — verify manually.'),
    ]:
        if needle in raw:
            warn(msg)

print("---")
if warns:
    print(f"{warns} warning(s). Harden before exposing the gateway to any channel.")
    sys.exit(1)
print("No warnings. Still: audit installed skills with `openclaw skills list`.")
PY
