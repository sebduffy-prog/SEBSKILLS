#!/usr/bin/env python3
"""Pre-connect audit for MCP tool descriptions + rug-pull pinning.

Reads a JSON list of tool objects (name, description, [inputSchema]) as emitted
by an MCP `tools/list` response, or a Claude/Cursor mcp.json-style config with a
"tools" array. Flags tool-poisoning indicators (hidden-instruction phrasing,
invisible/bidi Unicode, data-exfil hints) and maintains a hash pin file so a
silent description change (a "rug pull") is caught on the next run.

Stdlib only (Python 3.9+). No network calls — feed it captured tool JSON.

Usage:
    python3 audit_mcp_tools.py tools.json                 # audit only
    python3 audit_mcp_tools.py tools.json --pin pins.json # audit + rug-pull check
Exit code 0 = clean, 1 = findings, 2 = usage/parse error.
"""
import argparse
import hashlib
import json
import re
import sys
import unicodedata

# Phrases that legit tool descriptions almost never need; classic TPA payloads.
INSTRUCTION_PATTERNS = [
    r"\bignore (all |the |previous |above )",
    r"\bdo not (tell|mention|inform|reveal)\b",
    r"\bdon'?t (tell|mention|inform|reveal)\b",
    r"\b(before|prior to) (using|calling) (this|any other) tool\b",
    r"\byou (must|should|need to) (read|send|fetch|exfiltrate|include)\b",
    r"\b(system prompt|\.env|id_rsa|ssh key|credentials?|api[_ ]?key|secret)\b",
    r"<important>|<system>|<secret>|<hidden>",
    r"\bcurl\b|\bwget\b|https?://[^\s]+\?.*=",  # inline fetch/exfil URL
]
INSTRUCTION_RE = re.compile("|".join(INSTRUCTION_PATTERNS), re.IGNORECASE)

# Invisible / direction-control / private-use chars used to hide payloads.
SUSPICIOUS_CATEGORIES = {"Cf", "Co"}  # format controls, private use


def find_hidden_unicode(text):
    hits = []
    for ch in text:
        if unicodedata.category(ch) in SUSPICIOUS_CATEGORIES or ch in "​‎‏‪‮⁦⁩":
            name = unicodedata.name(ch, f"U+{ord(ch):04X}")
            hits.append(name)
    return sorted(set(hits))


def audit_tool(tool):
    """Return a list of finding strings for one tool object."""
    findings = []
    name = tool.get("name", "<unnamed>")
    blob = tool.get("description", "") or ""
    schema = tool.get("inputSchema") or tool.get("input_schema") or {}
    # Include parameter descriptions — payloads hide there too.
    for prop in (schema.get("properties") or {}).values():
        if isinstance(prop, dict) and prop.get("description"):
            blob += "\n" + prop["description"]

    for m in INSTRUCTION_RE.finditer(blob):
        findings.append(f"instruction-like phrase: {m.group(0)!r}")
    hidden = find_hidden_unicode(blob)
    if hidden:
        findings.append(f"hidden/invisible unicode: {', '.join(hidden)}")
    if len(blob) > 2000:
        findings.append(f"unusually long description ({len(blob)} chars) — review for buried text")
    return name, findings


def tool_hash(tool):
    payload = json.dumps(
        {"name": tool.get("name"), "description": tool.get("description"),
         "inputSchema": tool.get("inputSchema") or tool.get("input_schema")},
        sort_keys=True, ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_tools(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("tools", data.get("result", {}).get("tools", []))
    if not isinstance(data, list):
        raise ValueError("expected a list of tools or an object with a 'tools' array")
    return data


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tools_json", help="captured tools/list JSON")
    ap.add_argument("--pin", help="hash pin file for rug-pull detection (created if absent)")
    args = ap.parse_args()

    try:
        tools = load_tools(args.tools_json)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    any_findings = False
    pins = {}
    if args.pin:
        try:
            with open(args.pin, encoding="utf-8") as f:
                pins = json.load(f)
        except FileNotFoundError:
            pins = {}

    new_pins = {}
    for tool in tools:
        name, findings = audit_tool(tool)
        h = tool_hash(tool)
        new_pins[name] = h
        if args.pin and name in pins and pins[name] != h:
            findings.insert(0, "RUG PULL: description/schema changed since last pin — re-review before use")
        if findings:
            any_findings = True
            print(f"[!] {name}")
            for fnd in findings:
                print(f"      - {fnd}")
        else:
            print(f"[ok] {name}")

    if args.pin:
        with open(args.pin, "w", encoding="utf-8") as f:
            json.dump(new_pins, f, indent=2, sort_keys=True)
        print(f"\npins written to {args.pin} ({len(new_pins)} tools)")

    print("\nCLEAN" if not any_findings else "\nFINDINGS ABOVE — do not connect until reviewed")
    return 1 if any_findings else 0


if __name__ == "__main__":
    sys.exit(main())
