---
name: lsp-code-navigation
category: engineering-workflow
description: >-
  Wire a real Language Server (tsserver, pyright, gopls, rust-analyzer) into an
  agent over the jonrad/lsp-mcp MCP bridge so it answers go-to-definition,
  find-references, hover-type, document/workspace symbols, and rename with
  compiler-grade precision instead of grep guessing. Use when grep floods you
  with false positives on a common identifier, when you must find every real
  caller before a refactor, or when you need the true resolved type at a spot.
when_to_use:
  - Grep/ripgrep returns too many false hits for a common name and you need the ONE real definition
  - You must enumerate every genuine caller of a symbol before renaming or deleting it
  - You need the resolved/inferred type at a cursor position, not a textual guess
  - You want a semantic outline (document or workspace symbols) of an unfamiliar file or repo
  - You are doing a cross-file rename and want the language server to compute the edit set
when_not_to_use:
  - Plain literal or regex text search across files — use ripgrep or semantic-code-search
  - Structural pattern rewrites by AST shape — use ast-grep-codemod
  - Packing many files into one context blob for reading — use repo-context-packer
  - The language has no working LSP server installed and none can be installed — fall back to grep
keywords:
  - lsp
  - language-server
  - mcp
  - go-to-definition
  - find-references
  - rename-symbol
  - hover-type
  - document-symbol
  - workspace-symbol
  - tsserver
  - pyright
  - gopls
  - rust-analyzer
  - code-navigation
  - jonrad
similar_to:
  - ast-grep-codemod
  - repo-context-packer
  - semantic-code-search
inputs_needed: A checked-out repo, Node.js (for npx) or Docker, and an LSP server for the target language (typescript-language-server, pyright, gopls, rust-analyzer).
produces: An `lsp` MCP server registered with the agent, exposing LSP navigation tools (definition, references, hover, symbols, rename) plus `lsp_info` and `file_contents_to_uri`.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# LSP Code Navigation

Give the agent **compiler-grade** code navigation. Instead of `grep "handleClick"`
returning 60 textual hits, ask the language server "where is this *defined*" or
"who *actually calls* this" and get the exact, resolved answer — the same data
your editor's "Go to Definition" uses. Built on [`jonrad/lsp-mcp`](https://github.com/jonrad/lsp-mcp),
which bridges any stdio Language Server to MCP and dynamically exposes its
methods as tools generated from the LSP JSON schema.

## When to use

Reach for this the moment a plain text search betrays you: a method named `run`,
`get`, or `handle` that appears everywhere; a symbol you must delete safely; an
inferred generic type you cannot read off the source. LSP resolves scope,
imports, and types — grep cannot.

## Prerequisites (be honest about these)

- **Node.js** (the npx transport fetches `lsp-mcp` from git) **or Docker** for the pinned image.
- **A language server for your language, installed and on PATH.** The MCP bridge
  is a *proxy* — it ships no analysers. You need one of:
  - TypeScript/JS: `typescript-language-server` (+ `typescript`)
  - Python: `pyright` (`pyright-langserver`)
  - Go: `gopls`
  - Rust: `rust-analyzer`
- The LSP command is run through `sh -c`, so pass it as one string via `--lsp`.
- macOS note: no Homebrew here — install servers with `npm i -g` / `pip install`
  / language toolchain, or use the npx-in-npx form below which needs nothing global.

## Setup

### 1. Register the MCP server (project `.mcp.json`)

Claude Code reads `.mcp.json` at the repo root. TypeScript, zero global installs
(npx fetches both the bridge and the server, versions pinned for reproducibility):

```json
{
  "mcpServers": {
    "lsp": {
      "command": "npx",
      "args": [
        "-y", "--silent", "git+https://github.com/jonrad/lsp-mcp",
        "--workspace", ".",
        "--lsp", "npx -y --silent -p 'typescript@5.7.3' -p 'typescript-language-server@4.3.3' typescript-language-server --stdio"
      ]
    }
  }
}
```

Or add it imperatively:

```bash
claude mcp add-json lsp '{"command":"npx","args":["-y","--silent","git+https://github.com/jonrad/lsp-mcp","--workspace",".","--lsp","npx -y --silent -p typescript@5.7.3 -p typescript-language-server@4.3.3 typescript-language-server --stdio"]}'
```

Swap the `--lsp` string per language (server must be installed for these):

| Language   | `--lsp` value                          |
|------------|----------------------------------------|
| Python     | `pyright-langserver --stdio`           |
| Go         | `gopls`                                |
| Rust       | `rust-analyzer`                        |
| TypeScript | `typescript-language-server --stdio`   |

### 2. Docker transport (pinned, hermetic)

The image bundles common servers. Mount your repo and set `--workspace` to the
**in-container** path — URIs you send must match that path.

```json
{
  "mcpServers": {
    "lsp": {
      "command": "docker",
      "args": ["run", "-i", "--rm",
        "-v", "${PWD}:/workspace",
        "docker.io/jonrad/lsp-mcp:0.3.1",
        "--workspace", "/workspace",
        "--lsp", "typescript-language-server --stdio"]
    }
  }
}
```

### 3. CLI flags (from `lsp-mcp --help`)

- `-l, --lsp <string>` — LSP command to start (passed through `sh -c`). Required unless `--config`.
- `-w, --workspace [string]` — workspace root the server sees (default `/`). **Set this** or URIs won't resolve.
- `-m, --methods [string...]` — allow-list of LSP methods to expose (default: all non-blacklisted).
- `-c, --config [string]` — JSON config file, for running several servers at once.
- `-v, --verbose` — dev logging only; do **not** combine with MCP stdio (it corrupts the protocol stream).

## Recipes

The navigation tools are named after their **LSP method IDs** (dynamically
generated). Every position is **0-indexed** (`line` 0 = first line). Files on
disk are referenced by a `file://` URI under the workspace.

### Two always-present helper tools

- `lsp_info` — reports which servers are wired, their languages/extensions, and
  live capabilities. **Call this first** to confirm the server is up and speaks
  your language before debugging anything else.
- `file_contents_to_uri` — turns raw file contents into a URI for buffers that
  are not on the filesystem (unsaved edits). For real files, pass the path/URI directly.

### Go to definition

Method `textDocument/definition`. "Where is `parseConfig` really defined?"

```json
{
  "textDocument": { "uri": "file:///workspace/src/app.ts" },
  "position": { "line": 41, "character": 12 }
}
```

Returns the defining location(s) — the exact file + range, resolving imports and
re-exports that grep would miss.

### Find all references

Method `textDocument/references`. The killer app: every **real** caller.

```json
{
  "textDocument": { "uri": "file:///workspace/src/app.ts" },
  "position": { "line": 41, "character": 12 },
  "context": { "includeDeclaration": false }
}
```

Trust this list for "is this safe to delete?" in a way `grep -w` never earns.

### Hover for the resolved type

Method `textDocument/hover`. Same `{textDocument, position}` shape. Returns the
inferred type + doc — read a gnarly generic's actual instantiation without
running the compiler yourself.

### Symbol outline

- `textDocument/documentSymbol` (`{textDocument}` only) — the outline of one file.
- `workspace/symbol` (`{ "query": "UserService" }`) — fuzzy find a symbol repo-wide.

Great for orienting in an unfamiliar module before touching it.

### Rename across the codebase

Method `textDocument/rename`. The server computes the full multi-file edit set:

```json
{
  "textDocument": { "uri": "file:///workspace/src/app.ts" },
  "position": { "line": 41, "character": 12 },
  "newName": "parseSettings"
}
```

Returns a `WorkspaceEdit`. **Review it, then apply** — do not blind-apply a rename
touching dozens of files.

## Verify

1. Ask the agent to call `lsp_info`. You should see your language listed and,
   after the first request, `Started` with a capabilities blob.
2. Run `textDocument/definition` on a symbol you know — the returned URI+range
   must point at the true declaration, not a usage.
3. Cross-check one `textDocument/references` result set against your editor's
   "Find All References" on the same symbol; counts should match.
4. If a call errors, run the raw server once to confirm it's installed and stdio-clean:
   ```bash
   echo '' | typescript-language-server --stdio   # should hang waiting for input, not "command not found"
   ```

## Pitfalls

- **Workspace mismatch.** The single biggest failure: `--workspace` and your
  `file://` URIs must agree. Under Docker, use the in-container path (`/workspace/...`),
  not your host path.
- **Cold-start latency.** Servers start lazily on first file touch and index the
  project — the *first* definition/references call can take seconds (rust-analyzer,
  gopls index whole crates/modules). Later calls are fast. Don't treat the first slow call as a failure.
- **0-indexed positions.** Line/character are zero-based. Off-by-one lands you on
  the wrong token and returns empty or wrong results.
- **Server not installed.** `lsp-mcp` proxies only; "no results ever" usually
  means the `--lsp` command isn't found. `lsp_info` + the raw-run check above isolate this.
- **`--verbose` with MCP.** Verbose writes to the same stream as the protocol and
  breaks it. Keep it off in any real MCP config.
- **Rename is not text replace.** It respects scope and shadowing — which is the
  point — but still review the `WorkspaceEdit` before applying; servers occasionally
  miss dynamic or string-referenced usages.
- **Not a search engine.** For literal/regex sweeps use ripgrep; for AST-shape
  rewrites use ast-grep-codemod. LSP shines only where scope and types matter.
