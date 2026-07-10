---
name: semantic-code-search
category: engineering-workflow
description: >-
  Stand up a local-first semantic (embedding) code index with SeaGOAT so an
  agent finds code by MEANING, not literal grep — ask "where do we round
  currency" or "the retry/backoff logic" and get ranked file:line hits across a
  large, unfamiliar repo. Reach for this before editing code you don't know: run
  seagoat-server once, then `gt "<intent>"` with --context / --max-results /
  --vimgrep. Runs offline (ChromaDB + local model), no code leaves the machine,
  and it blends embeddings WITH ripgrep so exact tokens still rank. Use it when
  keyword grep keeps missing because the words don't match the concept.
when_to_use:
  - Exploring an unfamiliar or large repo where you don't know the right keywords
  - Finding all code implementing a concept ("auth token refresh", "rate limiting")
  - Locating where a behaviour lives before editing, when grep terms keep missing
  - Wanting ranked-by-relevance file:line hits an agent can open directly
  - Needing a fully offline / private index (no code sent to any API)
when_not_to_use:
  - You already know the exact string/symbol — plain ripgrep or lsp-code-navigation is faster
  - Structural find-and-replace across the tree — use ast-grep-codemod
  - Jumping to a type's definition/refs/callers interactively — use lsp-code-navigation
  - Packing the WHOLE repo into one LLM context bundle — use repo-context-packer
keywords:
  - semantic-search
  - embeddings
  - seagoat
  - code-search
  - vector-index
  - chromadb
  - ripgrep
  - local-first
  - codebase-navigation
  - retrieval
  - offline
  - file-line
similar_to:
  - repo-context-packer
  - ast-grep-codemod
  - lsp-code-navigation
inputs_needed: A local code repo path; Python 3.11+ and ripgrep installed; pipx for install
produces: A background semantic index plus ranked file:line search hits (plain, --vimgrep, or --generative)
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Semantic Code Search (SeaGOAT)

Find code by **what it does**, not the exact identifier. SeaGOAT builds a local
vector index (ChromaDB + a local embedding model) and blends it with ripgrep, so
`gt "where are numbers rounded"` returns ranked `file:line` hits even when the
source says `Decimal.quantize`. Everything runs on your machine — no code is sent
to any API.

Grounded against SeaGOAT (github.com/kantord/SeaGOAT, MIT © Daniel Kantor).

## When to use

Reach for this the moment you're about to edit an unfamiliar large repo and
keyword grep keeps missing because the words in your head don't match the words
in the code. It complements — does not replace — ripgrep (exact strings) and an
LSP (types/refs). Use it to *locate*, then open the real files to read.

## Prerequisites (honest)

- **Python 3.11+** (this Mac's system `python3` is 3.9 — too old; see install note).
- **ripgrep** (`rg`) on PATH — a hard dependency, SeaGOAT shells out to it.
- **pipx** to install the CLI in its own venv.
- Optional: **bat** for colourised output.
- First query on a fresh repo returns *partial* results and prints an accuracy
  warning until background indexing reaches 100%. This is expected, not a bug.
- The index lives under a cache dir (see `seagoat-server server-info`), not in
  your repo. Nothing is uploaded.

Install (macOS, no brew — use a 3.11+ interpreter for pipx):

```bash
# ripgrep without brew: pipx-installable shim, or download the ripgrep release binary.
pipx install ripgrep-bin 2>/dev/null || echo "install ripgrep from https://github.com/BurntSushi/ripgrep/releases"

# SeaGOAT itself (needs Python >=3.11; point pipx at one if system python is 3.9):
pipx install seagoat --python python3.11
seagoat --version
```

## Steps

### 1. Start the index server for a repo

```bash
seagoat-server start /path/to/your/repo
```

Runs in the background and begins embedding files. You can query immediately —
it indexes while you work. Check progress / where files are stored:

```bash
seagoat-server server-info
```

### 2. Query by meaning

Two aliases: `gt` (short) or `seagoat`. `repo_path` defaults to `$(pwd)`, so run
from inside the repo or pass the path as the 2nd arg.

```bash
gt "where are monetary amounts rounded"
gt "retry with exponential backoff" /path/to/repo
```

You can mix in regex-ish intent; SeaGOAT fuses semantic hits with ripgrep matches:

```bash
gt "the function that validates JWT tokens"
```

### 3. Shape the output for an agent

Real flags (verified from `seagoat/cli.py`):

| Flag | Short | Effect |
|------|-------|--------|
| `--max-results N` | `-l` | Cap result lines (default: unlimited) |
| `--context-above N` | `-B` | Lines of context before each hit (default 3) |
| `--context-below N` | `-A` | Lines of context after each hit (default 3) |
| `--context N` | `-C` | Context both sides (sets -A and -B) |
| `--reverse` | `-r` | Most-relevant last (nice in a scrolling terminal) |
| `--vimgrep` | | `file:line:col:` grep-line format for editors/pipes |
| `--no-color` | | Plain text (auto-on when piped) |
| `--generative` | `-g` | LLM-summarise/re-rank the hits (extra latency) |
| `--version` | | Print version |

Agent-friendly recipe — top 10 concise, machine-parseable hits:

```bash
gt "the code path that refreshes an expired access token" \
   --max-results 10 --vimgrep --no-color
```

`--vimgrep` yields `path/to/file.py:142:9: <line>` — trivial to parse into file +
line for a follow-up Read/open.

### 4. Iterate, then read the real files

Treat hits as *pointers*. Open the actual files (not just the snippet) before
editing — SeaGOAT finds the neighbourhood, your own read confirms the exact spot.

### 5. Keep the index fresh / tidy up

The server picks up changes as you edit. Stop it when done with the repo:

```bash
seagoat-server stop /path/to/your/repo
```

## Optional: config file

Drop a `.seagoat.yml` at the repo root to pin a port or exclude paths beyond
`.gitignore`:

```yaml
# .seagoat.yml
server:
  port: 31134
ignorePatterns:
  - "vendor/**"
  - "**/*.min.js"
```

## Verify

Confirm the toolchain and a live query before trusting results:

```bash
seagoat --version                         # CLI installed
rg --version                              # ripgrep present (hard dep)
seagoat-server start "$PWD"               # start on current repo
seagoat-server server-info                # shows cache/index location
gt "read a file from disk" --max-results 5 --no-color
```

A healthy run prints ranked hits. If you see
`Warning: SeaGOAT is still analyzing your repository ... accuracy N%`, indexing
is in progress — re-run the query in a few seconds for fuller coverage. Exit
code `3` = server not running (start it); `4` = server error.

## Pitfalls

- **Python 3.9 will fail the install.** SeaGOAT needs 3.11+. Pass
  `--python python3.11` to pipx or the venv build errors out. Don't fight
  system `python3` on this Mac — point pipx at a newer interpreter.
- **No ripgrep, no results.** `rg` is a runtime dependency, not optional. Verify
  `rg --version` first; a missing `rg` yields empty/partial output, not a clear error.
- **First-query emptiness is indexing, not failure.** Fresh repos return partial
  hits with an accuracy warning until embedding finishes. Wait and re-query.
- **Snippets ≠ ground truth.** The line shown may be a lead-in; always open the
  file to read the full function before you edit.
- **It locates, it doesn't refactor.** For safe structural rewrites use
  ast-grep-codemod; for definitions/references use an LSP. SeaGOAT is discovery.
- **Server is per-repo and stateful.** Each repo runs its own server on its own
  port; stop stale ones (`seagoat-server stop <repo>`) to free ports/RAM.
- **Don't commit the cache.** The index lives in a cache dir outside the repo by
  default — good. If you set a repo-local index path, add it to `.gitignore`.
