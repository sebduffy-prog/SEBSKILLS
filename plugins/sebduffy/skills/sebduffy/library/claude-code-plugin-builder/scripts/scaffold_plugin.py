#!/usr/bin/env python3
"""Scaffold a multi-component Claude Code plugin + a marketplace catalog.

Emits the plugin tree the docs describe (skills/, agents/, hooks/, .mcp.json,
output-styles/) WITH a `.claude-plugin/marketplace.json` catalog so it can be
distributed from a git repo. `claude plugin init` only scaffolds into
~/.claude/skills and does NOT write a marketplace.json, so this fills that gap.

Grounded on code.claude.com/docs/en/plugins + /plugins-reference + /plugin-marketplaces.
Python 3.9+, stdlib only. Writes nothing outside <root>. Validate after with:
    claude plugin validate <root>/<marketplace>
"""
import argparse, json, os, sys, re

KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def kebab_ok(name: str) -> bool:
    return bool(KEBAB.match(name))


def w(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def build(root: str, mkt: str, plugin: str, desc: str, author: str,
          components) -> str:
    # marketplace root holds .claude-plugin/marketplace.json; plugin lives under plugins/
    mkt_root = os.path.join(root, mkt)
    p_root = os.path.join(mkt_root, "plugins", plugin)

    # plugin.json — name is the only required field; version pins updates.
    manifest = {
        "name": plugin,
        "description": desc,
        "version": "0.1.0",
        "author": {"name": author},
    }
    w(os.path.join(p_root, ".claude-plugin", "plugin.json"),
      json.dumps(manifest, indent=2) + "\n")

    if "skills" in components:
        w(os.path.join(p_root, "skills", "hello", "SKILL.md"),
          "---\ndescription: Example skill. Use when the user says hello.\n---\n\n"
          "Greet the user warmly using \"$ARGUMENTS\".\n")
    if "agents" in components:
        w(os.path.join(p_root, "agents", "reviewer.md"),
          "---\nname: reviewer\ndescription: Reviews a diff for bugs.\n---\n\n"
          "You are a focused code reviewer. Report only high-confidence issues.\n")
    if "hooks" in components:
        hooks = {"hooks": {"PostToolUse": [{"matcher": "Write|Edit", "hooks": [
            {"type": "command",
             "command": "\"${CLAUDE_PLUGIN_ROOT}\"/scripts/on-edit.sh"}]}]}}
        w(os.path.join(p_root, "hooks", "hooks.json"),
          json.dumps(hooks, indent=2) + "\n")
        w(os.path.join(p_root, "scripts", "on-edit.sh"),
          "#!/usr/bin/env bash\n# receives hook JSON on stdin\njq -r '.tool_input.file_path'\n")
    if "mcp" in components:
        mcp = {"mcpServers": {"example-db": {
            "command": "${CLAUDE_PLUGIN_ROOT}/servers/db",
            "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"]}}}
        w(os.path.join(p_root, ".mcp.json"), json.dumps(mcp, indent=2) + "\n")
    if "output-style" in components:
        w(os.path.join(p_root, "output-styles", "terse.md"),
          "---\nname: terse\ndescription: Terse, no-preamble replies.\n---\n\n"
          "Answer in as few words as correctness allows. No filler.\n")

    # marketplace.json — lists the plugin with a relative source.
    catalog = {
        "name": mkt,
        "owner": {"name": author},
        "plugins": [{
            "name": plugin,
            "source": f"./plugins/{plugin}",
            "description": desc,
        }],
    }
    w(os.path.join(mkt_root, ".claude-plugin", "marketplace.json"),
      json.dumps(catalog, indent=2) + "\n")
    w(os.path.join(mkt_root, "README.md"),
      f"# {mkt}\n\nAdd:  `/plugin marketplace add ./{mkt}`\n"
      f"Install:  `/plugin install {plugin}@{mkt}`\n")
    return mkt_root


def main() -> int:
    ap = argparse.ArgumentParser(description="Scaffold a Claude Code plugin + marketplace.")
    ap.add_argument("--root", default=".", help="parent dir to write into")
    ap.add_argument("--marketplace", required=True, help="marketplace name (kebab-case)")
    ap.add_argument("--plugin", required=True, help="plugin name (kebab-case)")
    ap.add_argument("--description", default="A Claude Code plugin.")
    ap.add_argument("--author", default=os.environ.get("USER", "unknown"))
    ap.add_argument("--with", dest="components", default="skills,agents,hooks,mcp,output-style",
                    help="comma list: skills,agents,hooks,mcp,output-style")
    a = ap.parse_args()
    for label, val in (("marketplace", a.marketplace), ("plugin", a.plugin)):
        if not kebab_ok(val):
            print(f"error: --{label} '{val}' must be kebab-case "
                  "(lowercase letters, digits, hyphens)", file=sys.stderr)
            return 2
    comps = {c.strip() for c in a.components.split(",") if c.strip()}
    out = build(a.root, a.marketplace, a.plugin, a.description, a.author, comps)
    print(f"scaffolded: {out}")
    print(f"next: claude plugin validate {out}")
    print(f"      claude --plugin-dir {os.path.join(out, 'plugins', a.plugin)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
