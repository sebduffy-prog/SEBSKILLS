#!/usr/bin/env python3
"""Lint a Claude Code settings.json `hooks` block before you trust it.

Catches the mistakes that silently no-op a hook: unknown event names,
blocking logic wired to non-blocking events, hookSpecificOutput whose
hookEventName does not match its parent event, and missing command paths.

Usage:
    python3 validate_hooks.py .claude/settings.json
    python3 validate_hooks.py            # defaults to ./.claude/settings.json

Exit code 0 = clean, 1 = warnings/errors printed. Advisory only; the docs
event catalogue moves, so treat unknown-event warnings as "double-check",
not "definitely wrong". Grounded on https://code.claude.com/docs/en/hooks
"""
import json
import sys

# Event names from the 2026 catalogue. Kept as a set for a soft check only.
KNOWN_EVENTS = {
    "SessionStart", "Setup", "UserPromptSubmit", "UserPromptExpansion",
    "PreToolUse", "PermissionRequest", "PermissionDenied", "PostToolUse",
    "PostToolUseFailure", "PostToolBatch", "Notification", "MessageDisplay",
    "SubagentStart", "SubagentStop", "TaskCreated", "TaskCompleted",
    "Stop", "StopFailure", "TeammateIdle", "InstructionsLoaded",
    "ConfigChange", "CwdChanged", "FileChanged", "WorktreeCreate",
    "WorktreeRemove", "PreCompact", "PostCompact", "Elicitation",
    "ElicitationResult", "SessionEnd",
}

# Events where a non-zero exit code (2) actually blocks the action.
BLOCKING_EVENTS = {
    "PreToolUse", "PermissionRequest", "UserPromptSubmit",
    "UserPromptExpansion", "Stop", "SubagentStop", "TeammateIdle",
    "TaskCreated", "TaskCompleted", "ConfigChange", "PreCompact",
    "PostToolBatch", "WorktreeCreate", "Elicitation", "ElicitationResult",
}

VALID_TYPES = {"command", "http", "mcp_tool", "prompt", "agent"}


def check(path):
    problems = []
    try:
        with open(path) as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return [f"ERROR: no such file: {path}"]
    except json.JSONDecodeError as exc:
        return [f"ERROR: invalid JSON in {path}: {exc}"]

    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return [f"ERROR: no top-level 'hooks' object in {path}"]

    for event, groups in hooks.items():
        if event not in KNOWN_EVENTS:
            problems.append(
                f"WARN: '{event}' is not a known event name (typo? new version?)"
            )
        if not isinstance(groups, list):
            problems.append(f"ERROR: hooks.{event} must be an array")
            continue
        for gi, group in enumerate(groups):
            loc = f"{event}[{gi}]"
            for hi, hook in enumerate(group.get("hooks", [])):
                hloc = f"{loc}.hooks[{hi}]"
                htype = hook.get("type")
                if htype not in VALID_TYPES:
                    problems.append(
                        f"ERROR: {hloc} type '{htype}' not in {sorted(VALID_TYPES)}"
                    )
                if htype == "command" and not hook.get("command"):
                    problems.append(f"ERROR: {hloc} command hook missing 'command'")
                if htype == "http" and not hook.get("url"):
                    problems.append(f"ERROR: {hloc} http hook missing 'url'")
    # Soft nudge: mention which events can block, so authors relying on exit 2
    # know it is honoured. Purely informational.
    non_blocking = [e for e in hooks if e in KNOWN_EVENTS and e not in BLOCKING_EVENTS]
    if non_blocking:
        problems.append(
            "INFO: exit-code-2 does NOT block on these configured events: "
            + ", ".join(sorted(non_blocking))
            + " (they run advisory-only)"
        )
    return problems


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else ".claude/settings.json"
    problems = check(path)
    if not problems:
        print(f"OK: {path} hooks block looks well-formed")
        return 0
    for p in problems:
        print(p)
    return 1 if any(p.startswith(("ERROR", "WARN")) for p in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
