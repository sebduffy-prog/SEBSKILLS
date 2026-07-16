---
name: repo-context-packer
category: engineering-workflow
description: >-
  Pack a whole codebase, subfolder, or remote GitHub repo into ONE AI-ready
  context bundle with repomix — directory tree + per-file contents, .gitignore
  and glob-aware filtering, Secretlint secret redaction, tree-sitter --compress
  to cut ~70% of tokens, token counting, and XML/Markdown/JSON/plain output.
  Reach for this when you must hand an LLM an entire repo, diff two versions, or
  measure/trim context size before pasting into a prompt.
when_to_use:
  - Feeding an entire repo or folder to an LLM that lacks direct file access
  - Packing a remote GitHub repo (owner/repo or URL) without cloning it yourself
  - Shrinking a large codebase under a token budget via --compress and includes
  - Auditing what secrets/files would leak before sharing code with an AI
  - Producing a reproducible, config-driven repo snapshot for review or prompts
when_not_to_use:
  - Searching for a symbol or pattern across code — use semantic-code-search or ripgrep
  - Structural find/replace across files — use ast-grep-codemod
  - Navigating types/refs interactively in an editor — use lsp-code-navigation
  - Generating an API client from a spec — use openapi-client-codegen
keywords:
  - repomix
  - context-packing
  - codebase-to-prompt
  - token-budget
  - tree-sitter
  - compress
  - gitignore
  - secretlint
  - xml-output
  - remote-repo
  - llm-context
  - directory-tree
similar_to:
  - semantic-code-search
  - ast-grep-codemod
  - lsp-code-navigation
inputs_needed: A local repo/folder path OR a GitHub URL/owner-repo; Node.js (for npx); optional include/ignore globs and a target token budget
produces: A single context file (repomix-output.xml/.md/.json/.txt) or stdout stream containing a directory tree, packed file contents, token counts, and a secret-scan report
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Repo Context Packer (repomix)

Turn a codebase into a single, LLM-shaped text bundle. `repomix` walks a repo,
respects `.gitignore`, scans for secrets, optionally compresses code down to its
structural skeleton with tree-sitter, counts tokens, and emits one file (XML by
default) you can paste into a prompt or attach to an agent run.

## When to use

Use this whenever an LLM needs the *whole* repo (or a curated slice) as flat
context: onboarding a model to an unfamiliar project, asking for a cross-file
refactor, reviewing a remote repo you haven't cloned, or measuring how many
tokens a codebase costs before you commit to a prompt. For pinpoint lookups or
edits, prefer the sibling skills in `when_not_to_use`.

## Prerequisites

- **Node.js 18+** — repomix is a Node CLI. Run it zero-install with `npx`.
- **No Homebrew needed.** On this Mac, do NOT `brew install`; use `npx repomix@latest`.
- **git** — only required for `--remote`, `--include-logs`, and `--include-diffs`.
- Secret scanning uses bundled **Secretlint**; no key or network call needed.
- Token counts use `tiktoken` encodings shipped with repomix (offline).

Confirm it runs:

```bash
npx --yes repomix@latest --version
```

## Recipes

All commands are runnable as-is. `npx --yes` avoids the install prompt.

### 1. Pack the current repo (default XML)

```bash
cd /path/to/repo
npx --yes repomix@latest
# → writes ./repomix-output.xml  (dir tree + every non-ignored file + token summary)
```

The run prints a summary: top-N largest files, total files, total characters,
total tokens, and any secrets Secretlint flagged.

### 2. Curate a slice with include / ignore globs

Include is comma-separated glob patterns; `--ignore` adds patterns on top of
`.gitignore` and the built-in defaults (node_modules, lockfiles, binaries…).

```bash
npx --yes repomix@latest \
  --include "src/**/*.ts,src/**/*.tsx,README.md" \
  --ignore "**/*.test.ts,**/__snapshots__/**"
```

### 3. Compress to fit a token budget (tree-sitter)

`--compress` keeps signatures, class/function structure and drops bodies —
typically ~70% fewer tokens. Combine with Markdown for readable prompts.

```bash
npx --yes repomix@latest --compress --style markdown -o context.md
```

Pair with `--remove-comments` and `--remove-empty-lines` for maximum shrinkage:

```bash
npx --yes repomix@latest --compress --remove-comments --remove-empty-lines
```

### 4. Pack a REMOTE repo without cloning

Accepts a full URL or shorthand `owner/repo`. Add `--remote-branch` for a ref,
tag, or commit.

```bash
npx --yes repomix@latest --remote yamadashy/repomix --style markdown -o repomix.md
npx --yes repomix@latest --remote https://github.com/anthropics/anthropic-sdk-python --remote-branch main
```

### 5. Stream to stdout / clipboard (skip the file)

```bash
npx --yes repomix@latest --stdout > /tmp/ctx.xml   # pipe into another tool
npx --yes repomix@latest --copy                    # also copy to macOS clipboard
```

### 6. Measure tokens before you spend them

`--token-count-tree` prints the directory tree annotated with per-node token
counts; pass a number to hide anything under that threshold. `--top-files-len`
controls how many largest files the summary lists.

```bash
npx --yes repomix@latest --token-count-tree 5000 --top-files-len 15
npx --yes repomix@latest --token-count-encoding o200k_base   # GPT-4o/Claude-ish; default
```

### 7. Add git history and diffs for change-review prompts

```bash
npx --yes repomix@latest --include-diffs                 # working tree + staged diff
npx --yes repomix@latest --include-logs --include-logs-count 30
```

### 8. Steer the model with a header + instruction file

```bash
echo "You are reviewing this repo for auth bugs. Focus on session handling." > .repomix-instructions.md
npx --yes repomix@latest \
  --header-text "SNAPSHOT for security review — do not execute" \
  --instruction-file-path .repomix-instructions.md
```

### 9. Reproducible config (recommended for anything you'll re-run)

`--init` scaffolds `repomix.config.json` (JSON5: comments + trailing commas OK).
A minimal, honest config:

```json
{
  "output": {
    "filePath": "repomix-output.xml",
    "style": "xml",
    "compress": false,
    "removeComments": false,
    "showLineNumbers": false,
    "topFilesLength": 10
  },
  "include": ["src/**", "*.md"],
  "ignore": {
    "useGitignore": true,
    "useDefaultPatterns": true,
    "customPatterns": ["**/*.min.js", "dist/**", "coverage/**"]
  },
  "security": { "enableSecurityCheck": true },
  "tokenCount": { "encoding": "o200k_base" }
}
```

Then just run `npx --yes repomix@latest` in that directory — flags override
config when both are present. Use `-c ./other.config.json` for an alternate.

## Verify

- **Exit code 0** and a summary printed with non-zero "Total Files" / "Total Tokens".
- The output file exists and starts with a `<file_summary>` (XML) or `# File Summary`
  (Markdown) block, followed by a `<directory_structure>` tree.
- Secret scan line reads `No suspicious files found` — if not, STOP and inspect
  the listed paths before sharing (see Pitfalls).
- Token total is under your intended budget; if not, apply `--compress` / tighter
  `--include`, then re-run and re-check the summary.

```bash
npx --yes repomix@latest -o /tmp/out.xml \
  && head -c 400 /tmp/out.xml \
  && grep -c "<file " /tmp/out.xml   # rough file count in the XML
```

## Pitfalls

- **Secrets can still leak.** Secretlint catches common patterns (AWS keys, tokens)
  but not everything. `--no-security-check` disables it entirely — only do that on
  code you've independently verified is safe. Never pack `.env` files: they're in
  the default ignore set, so avoid `--no-default-patterns` unless you re-add them.
- **`--compress` is lossy.** It drops function/method bodies. If the model needs
  exact logic (debugging a specific line), pack that path uncompressed via
  `--include` instead of compressing the whole repo.
- **`--no-gitignore` + `--no-default-patterns` = firehose.** You'll pull in
  `node_modules`, build artifacts, and binaries, blowing your token budget and
  possibly embedding secrets. Keep defaults on unless you know why.
- **Remote packs shallow-clone to a temp dir.** Private repos need your git auth
  (SSH agent or a `gh auth`-backed credential helper) to be configured first.
- **XML vs Markdown for the model.** repomix defaults to XML because Claude parses
  the `<file path="…">` tags cleanly; use `--style markdown` only when a human
  will read it or the target model prefers fenced blocks.
- **Huge repos are slow / may OOM Node.** Scope with `--include` before reaching
  for the full tree; check `--token-count-tree` first to find the heavy folders.
- **`npx` prompts on first run.** Always pass `--yes` in scripts/agents so it
  doesn't hang waiting for install confirmation.
