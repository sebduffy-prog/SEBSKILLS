---
name: ast-grep-codemod
category: engineering-workflow
description: >-
  Run structural (AST-based) search-and-rewrite across a codebase with ast-grep — tree-sitter
  patterns, `$META` capture variables, YAML rule files with `fix`, dry-run diff preview, and
  interactive per-match apply. Reach for this the moment a refactor is syntax-aware — API
  migrations, renaming call shapes, mechanical codemods — where line-based sed/regex mangles
  strings, comments and formatting. Covers install, `sg run` one-liners, `sg scan` rule projects,
  constraints, and safe apply. Defensive, git-guarded, reversible.
when_to_use:
  - Migrating an API surface across many files (old call shape -> new call shape) where the match must respect syntax, not text
  - A regex/sed rewrite is corrupting matches inside strings, comments, or nested calls and you need AST-accurate targeting
  - Codifying a lint-and-fix rule (YAML with pattern + fix) to run repeatedly in CI or across a monorepo
  - Renaming or reshaping function calls, imports, JSX props, or method chains structurally with captured metavariables
  - You want a dry-run diff of every rewrite before touching disk, then to apply interactively or in bulk
when_not_to_use:
  - Pure text find-and-replace with no syntax meaning (URLs, config keys, prose) — use `sed`, `ripgrep`, or your editor
  - Rich type-aware or cross-file semantic refactors (rename-symbol, find-references) — use `lsp-code-navigation` or the language's own tooling (tsserver, gopls, rust-analyzer)
  - Just finding code without rewriting and you want semantic/embedding recall — use `semantic-code-search`
  - Language ast-grep does not parse (check supported list) — fall back to the language's native codemod tool (jscodeshift, libcst, gofmt -r)
keywords:
  - ast-grep
  - codemod
  - structural-search
  - tree-sitter
  - refactor
  - api-migration
  - rewrite
  - metavariable
  - yaml-rule
  - sg-scan
  - dry-run
  - find-and-replace
  - lint-fix
  - syntax-aware
similar_to:
  - semantic-code-search
  - lsp-code-navigation
  - dependency-upgrade-migration
  - repo-context-packer
  - mutation-testing
inputs_needed: A git repo (for safe rollback), the target language, and either a pattern->rewrite pair or a described API-migration you can express as before/after code shapes.
produces: Modified source files (after apply) plus a reviewable diff; optionally reusable YAML rule files under `rules/` and an `sgconfig.yml` project scaffold.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# ast-grep Codemod

Structural search-and-rewrite. `ast-grep` parses code with tree-sitter, matches against a
**pattern** (real code with `$META` holes), and rewrites captured nodes — so a match respects
syntax boundaries instead of blindly editing text. The binary is `ast-grep`, aliased `sg`.

## When to use

Use it for mechanical, syntax-aware refactors at scale: API migrations, call-shape renames,
import rewrites, JSX prop changes, codified lint-fixes. Two modes:

- **`sg run`** — throwaway one-liner: `-p` pattern, `-r` rewrite, `-l` language. Great for a
  single migration you run once.
- **`sg scan`** — YAML rule files with `fix`, `message`, `severity`, `constraints`. Reusable,
  reviewable, CI-friendly. Use once the rule is worth keeping.

Always work in a clean git tree — apply is destructive and `git` is your undo.

## Prerequisites

- **ast-grep installed.** This Mac has no Homebrew, so use npm (Node) — it ships the binary:
  ```bash
  npm install --global @ast-grep/cli   # provides both `ast-grep` and `sg`
  # alternatives: cargo install ast-grep --locked   |   pip3 install ast-grep-cli
  ```
  Verify: `ast-grep --version` (or `sg --version`).
- **A git repo**, committed clean (`git status` shows nothing to commit) so every apply is reversible.
- **Know the language.** Supported includes C, C++, Go, HTML, Java, JS, JSX, Kotlin, Python,
  Ruby, Rust, TS, TSX, YAML. Check `ast-grep --help` for the current list; unlisted langs need a native codemod tool instead.

Note on `sg`: on some systems `sg` collides with the `setgroups` util. If `sg` misbehaves, call `ast-grep` directly.

## Metavariable cheatsheet

| Syntax | Matches |
|--------|---------|
| `$A`, `$FOO` | exactly one named node (UPPERCASE letters/digits/underscore); reusable in the rewrite |
| `$$$ARGS` | zero-or-more nodes (a whole argument list, statement body, etc.) |
| `$_` / `$$$` | anonymous — match but don't capture |
| a captured `$A` reused twice | the SAME node both places (non-linear match) |

Non-matched metavariables become empty string in the `fix`.

## Recipe 1 — one-shot `sg run` migration

Rename `oldApi(x)` to `newApi(x)` across a TS codebase. **Preview first — this only prints a diff, touches nothing:**

```bash
ast-grep run --pattern 'oldApi($ARG)' --rewrite 'newApi($ARG)' --lang ts src/
```

Review the printed diff. Then apply — pick ONE:

```bash
# interactive: y/n per match (safest)
ast-grep run -p 'oldApi($ARG)' -r 'newApi($ARG)' -l ts --interactive src/

# bulk accept every match at once
ast-grep run -p 'oldApi($ARG)' -r 'newApi($ARG)' -l ts --update-all src/
```

Multi-arg example — capture a variadic list and reshape the call:

```bash
ast-grep run -p 'logger.log($$$ARGS)' -r 'logger.info($$$ARGS)' -l ts src/
```

Reorder/wrap captured args:

```bash
ast-grep run -p 'connect($HOST, $PORT)' -r 'connect({ host: $HOST, port: $PORT })' -l ts src/
```

## Recipe 2 — reusable YAML rule with `sg scan`

For anything you'll rerun or want reviewed, write a rule file. `fix` is the rewrite;
`message`/`severity` make it a lint too.

`rules/no-var.yml`:
```yaml
id: prefer-const-over-var
language: TypeScript
severity: warning
message: Use `let`/`const`, not `var`.
rule:
  pattern: var $NAME = $INIT
fix: const $NAME = $INIT
```

Preview then apply:
```bash
ast-grep scan --rule rules/no-var.yml src/           # prints diffs + messages, no writes
ast-grep scan --rule rules/no-var.yml --interactive src/
ast-grep scan --rule rules/no-var.yml --update-all src/
```

## Recipe 3 — relational + composite rules (target precisely)

Combine atomic (`pattern`, `kind`, `regex`), relational (`inside`, `has`, `follows`,
`precedes`), and composite (`all`, `any`, `not`) rules to avoid over-matching. Example: only
flag an `await` sitting inside a `Promise.all` argument.

`rules/await-in-promise-all.yml`:
```yaml
id: no-await-in-promise-all
language: TypeScript
severity: warning
message: await inside Promise.all is redundant — pass the bare promises.
rule:
  pattern: await $P
  inside:
    pattern: Promise.all($$$)
    stopBy: end        # search all ancestors, not just the direct parent
```

`constraints` narrows a metavariable further (regex / kind):

```yaml
rule:
  pattern: import $MOD from '$SOURCE'
constraints:
  SOURCE:
    regex: '^lodash$'    # only rewrite the bare 'lodash' import
fix: import $MOD from 'lodash-es'
```

## Recipe 4 — project scaffold for a rule suite

Standing up a monorepo rule set:

```bash
ast-grep new           # interactive: creates sgconfig.yml + rules/ rule-tests/ utils/
ast-grep new rule      # scaffold a new rule
ast-grep scan          # scan whole project using sgconfig.yml (no --rule needed)
```

`sgconfig.yml` points at your rule directories:
```yaml
ruleDirs:
  - rules
utilDirs:
  - utils
```
With it present, a bare `ast-grep scan` loads every rule and reports across the repo — wire that into CI.

## Verify

- **Machine-readable matches** (for scripting / counting before you apply):
  ```bash
  ast-grep run -p 'oldApi($ARG)' -l ts --json src/ | python3 -c 'import sys,json; print(len(json.load(sys.stdin)))'
  ```
- **After apply, diff is the truth:** `git diff --stat` then eyeball `git diff`. Every changed
  line should be an intended rewrite — nothing inside unrelated strings/comments.
- **Compiles/passes:** run the project's typecheck/build/tests (`tsc --noEmit`, `pytest`, etc.).
- **Instant rollback if wrong:** `git restore .` (or `git checkout -- .`). This is why the clean-tree prerequisite matters.

## Pitfalls

- **Never apply on a dirty tree.** `--update-all` overwrites files in place; without a clean git
  baseline you cannot cleanly revert. Preview (no flag) → interactive → bulk, in that order.
- **Pattern must parse as valid code** in the target language, or ast-grep can't build an AST for
  it. If a bare snippet is ambiguous, give it context (e.g. `function $F() { $$$ }`) so tree-sitter
  parses it the way you mean.
- **Wrong `--lang` = zero matches, silently.** TS vs TSX, JS vs JSX are distinct grammars. A file
  with JSX needs `tsx`/`jsx`, not `ts`/`js`.
- **`stopBy: end` matters for `has`/`inside`.** By default relational rules only look at the
  immediate parent/child; without `stopBy: end` a deeply-nested match is missed.
- **Formatting isn't preserved perfectly.** ast-grep rewrites the matched span; surrounding
  indentation of `$$$` bodies can shift. Run your formatter (prettier/black/gofmt) after applying
  and commit that separately so the codemod diff stays reviewable.
- **`$ARG` (one node) vs `$$$ARGS` (many).** Using `$ARG` on a multi-argument call won't match.
  Reach for `$$$` whenever the count varies.
- **Reused capture is an equality constraint.** `$A === $A` matches only when both sides are the
  *same* node — handy, but don't reuse a name by accident and wonder why matches vanish.
- **Not a semantic tool.** ast-grep matches shapes, not meaning. It can't tell two identically-named
  functions apart or follow imports. For rename-symbol / find-references use LSP tooling instead.
