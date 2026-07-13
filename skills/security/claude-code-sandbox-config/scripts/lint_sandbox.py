#!/usr/bin/env python3
"""Lint a Claude Code settings.json sandbox block for common footguns.

Usage: python3 lint_sandbox.py <settings.json> [--scope user|project|managed]

Grounded against https://code.claude.com/docs/en/sandboxing . Best-effort static
checks only; it cannot see resolved cross-scope merges. Exit 1 if any WARN/ERROR.
Python 3.9+, stdlib only.
"""
import json
import sys

# Domains broad enough to double as data-exfiltration paths (TLS is not inspected by default).
BROAD_DOMAINS = {"github.com", "*.github.com", "githubusercontent.com", "*", "*.com",
                 "gitlab.com", "*.amazonaws.com", "s3.amazonaws.com", "pastebin.com"}
# Write grants that can lead to code execution in another security context.
DANGEROUS_WRITE = ("/bin", "/usr", "/etc", "~/.bashrc", "~/.zshrc", "~/.profile",
                   "~/.bash_profile", "~/.config", "/usr/local/bin")


def add(findings, level, msg):
    findings.append((level, msg))


def lint(cfg, scope):
    findings = []
    sb = cfg.get("sandbox")
    if not isinstance(sb, dict):
        add(findings, "ERROR", "no 'sandbox' object found")
        return findings
    if not sb.get("enabled"):
        add(findings, "WARN", "sandbox.enabled is not true; the sandbox is off")

    fs = sb.get("filesystem", {}) or {}
    for path in fs.get("allowWrite", []) or []:
        if any(str(path).rstrip("/").startswith(d) for d in DANGEROUS_WRITE):
            add(findings, "ERROR", f"allowWrite '{path}' can enable privilege escalation ($PATH/dotfile)")

    creds = sb.get("credentials", {}) or {}
    if not creds:
        add(findings, "WARN", "no sandbox.credentials block: default read policy still exposes "
                              "~/.aws and ~/.ssh to sandboxed commands")
    for ev in creds.get("envVars", []) or []:
        if ev.get("mode") == "mask":
            if scope == "project":
                add(findings, "ERROR", f"'mask' on {ev.get('name')} is ignored in project/local "
                                       "scope; move to user/managed/--settings")
            if "tlsTerminate" not in (sb.get("network", {}) or {}):
                add(findings, "ERROR", f"'mask' on {ev.get('name')} requires network.tlsTerminate "
                                       "or it fails closed (auth breaks)")

    net = sb.get("network", {}) or {}
    for dom in net.get("allowedDomains", []) or []:
        if dom in BROAD_DOMAINS:
            add(findings, "WARN", f"allowedDomains '{dom}' is broad; potential exfiltration path "
                                  "(TLS not inspected by default)")
    # injectHosts must be covered by allowedDomains.
    allowed = set(net.get("allowedDomains", []) or [])
    for ev in creds.get("envVars", []) or []:
        for host in ev.get("injectHosts", []) or []:
            if host not in allowed and not any(a.startswith("*.") and host.endswith(a[1:]) for a in allowed):
                add(findings, "ERROR", f"injectHosts '{host}' for {ev.get('name')} is not in "
                                       "network.allowedDomains")

    if not findings:
        add(findings, "OK", "no issues detected")
    return findings


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    scope = "unknown"
    for a in sys.argv[1:]:
        if a.startswith("--scope"):
            scope = a.split("=")[-1] if "=" in a else "project"
    if not args:
        print(__doc__)
        sys.exit(2)
    try:
        with open(args[0]) as fh:
            cfg = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read/parse {args[0]}: {exc}")
        sys.exit(2)

    findings = lint(cfg, scope)
    bad = False
    for level, msg in findings:
        print(f"[{level}] {msg}")
        if level in ("WARN", "ERROR"):
            bad = True
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
