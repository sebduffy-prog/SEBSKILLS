---
name: sast-semgrep-opengrep
category: security
description: >-
  Run and author static-analysis (SAST) rules to catch injection, auth,
  path-traversal and secret bugs in YOUR OWN code with Semgrep or the
  Opengrep fork. Use when you need pattern rules, taint/dataflow tracking,
  autofix, `--validate`/`--test` rule tests, SARIF output, or a CI gate
  that only fails on NEW findings via a git baseline. Reach for this the
  moment someone says "add a SAST scan", "write a Semgrep rule", "catch
  this bug pattern everywhere", or "gate the pipeline on code security".
when_to_use:
  - Adding a SAST scan (Semgrep/Opengrep) to a repo or CI pipeline
  - Authoring a custom rule to ban a dangerous pattern across a codebase
  - Tracking tainted user input to a dangerous sink (SQLi, command inj, SSRF, XSS)
  - Applying autofix to mechanically rewrite an unsafe pattern
  - Gating CI on only newly introduced findings using a git baseline
  - Emitting SARIF for GitHub code scanning or another dashboard
when_not_to_use:
  - Finding committed secrets/credentials — use secrets-hygiene-and-remediation
  - Auditing third-party dependency CVEs — use supply-chain-sca-audit
  - Hardening Dockerfiles/Terraform/K8s config — use container-iac-hardening
  - Redacting PII from data/text at runtime — use pii-redaction-presidio
keywords:
  - semgrep
  - opengrep
  - sast
  - static-analysis
  - taint
  - dataflow
  - autofix
  - sarif
  - injection
  - custom-rules
  - baseline
  - ci-gate
  - owasp
  - security-scan
  - code-scanning
similar_to:
  - secrets-hygiene-and-remediation
  - supply-chain-sca-audit
  - container-iac-hardening
  - pii-redaction-presidio
  - llm-red-team
inputs_needed: A source tree to scan; optionally a target bug pattern to encode as a rule, and a git baseline commit for CI.
produces: Findings (text/JSON/SARIF), validated/tested custom rule YAML, optional autofixed source, and a CI gate that fails on new findings.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# SAST with Semgrep / Opengrep

Author and run static-analysis rules against **your own, authorised** code to catch
injection, broken auth, path traversal, unsafe deserialization and hardcoded-secret
bugs. Semgrep is the reference engine; **Opengrep** is the community LGPL fork with a
near-identical CLI — the rule YAML is shared, so everything here works on both.

## When to use

Use when you want repeatable, low-noise pattern detection you control: a curated
registry ruleset, a hand-written rule that bans one dangerous call everywhere, or a
taint rule that only fires when *user input actually reaches* a sink. For CI, wire the
git-baseline gate so a PR fails only on findings *it introduced*.

## Prerequisites

- **Semgrep**: `python3 -m pip install --user semgrep` (needs Python ≥3.9; this Mac's
  `python3` is 3.9, fine). No Homebrew needed. Verify: `semgrep --version`.
- **Opengrep** (optional, fork): `curl -fsSL https://raw.githubusercontent.com/opengrep/opengrep/main/install.sh | bash` — installs an `opengrep` binary. Verify: `opengrep --version`.
- Registry rules (`--config p/...`, `--config auto`) fetch from `semgrep.dev` and need
  network. Custom local rule files (`--config ./rules/`) run fully offline. Opengrep
  ships its own registry; prefer local YAML for air-gapped runs.
- No login/token required for local scans. `SEMGREP_APP_TOKEN` is only for the hosted
  platform — not needed here.

Swap `semgrep` → `opengrep` in any command below; note only the two flag differences
called out in the Opengrep recipe.

## Recipes

### 1. Fast baseline scan of a repo

```bash
# Curated, high-signal security rulesets from the registry:
semgrep scan --config p/security-audit --config p/secrets --config p/owasp-top-ten .

# Or let Semgrep pick rules per detected language:
semgrep scan --config auto .
```

`p/...` are registry pack shorthands (`p/default`, `p/ci`, `p/security-audit`,
`p/owasp-top-ten`, `p/secrets`, `p/command-injection`, ...). Findings print with
severity `ERROR`/`WARNING`/`INFO`. Add `--severity ERROR` to show only the worst.

### 2. Write a pattern rule (ban a dangerous call)

Pattern rules match syntax, not text — `...` is an ellipsis (any args/statements) and
`$X` is a metavariable that must bind consistently. Save as `rules/no-eval.yml`:

```yaml
rules:
  - id: python-no-eval
    languages: [python]
    severity: ERROR
    message: >-
      Avoid eval() on dynamic data; it enables code injection. Use ast.literal_eval
      or an explicit dispatch table.
    metadata:
      cwe: "CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code"
      owasp: "A03:2021 Injection"
    patterns:
      - pattern: eval(...)
      # Reduce noise: skip a call whose sole arg is a string literal
      - pattern-not: eval("...")
```

Key operators: `pattern` (match), `patterns` (AND of all), `pattern-either` (OR),
`pattern-not` (exclude), `pattern-inside` / `pattern-not-inside` (scope to a
surrounding construct), `metavariable-regex` / `metavariable-pattern` (constrain a
`$VAR`). Run it: `semgrep scan --config rules/no-eval.yml .`

### 3. Taint / dataflow rule (only fire when input reaches a sink)

Pattern rules match a single site; taint mode tracks a value from a **source**, through
optional **propagators**, past **sanitizers**, into a **sink** — this is what cuts false
positives on injection bugs. Requires `mode: taint`.

```yaml
rules:
  - id: flask-tainted-sql
    mode: taint
    languages: [python]
    severity: ERROR
    message: User-controlled request data reaches a raw SQL execute() — SQL injection.
    metadata: { cwe: "CWE-89", owasp: "A03:2021 Injection" }
    pattern-sources:
      - pattern: flask.request.$ANYTHING
    pattern-sanitizers:
      - pattern: sqlalchemy.text(...)          # parameterised → safe
    pattern-sinks:
      - patterns:
          - pattern: $CURSOR.execute($Q, ...)
          - focus-metavariable: $Q
```

`pattern-sources`/`-sinks`/`-sanitizers`/`-propagators` each accept
`pattern`/`patterns`/`pattern-either`/`pattern-regex`. `pattern-propagators` needs
`from:`/`to:` metavariables to model taint flowing through a helper. `focus-metavariable`
narrows the reported region to the tainted argument.

### 4. Autofix — mechanically rewrite the bad pattern

Add a `fix:` key (metavariables interpolate), then apply with `--autofix`:

```yaml
rules:
  - id: use-defusedxml
    languages: [python]
    severity: WARNING
    message: Parse untrusted XML with defusedxml to prevent XXE/billion-laughs.
    pattern: xml.etree.ElementTree.parse($SRC)
    fix: defusedxml.ElementTree.parse($SRC)
```

```bash
semgrep scan --config rules/use-defusedxml.yml --autofix .   # rewrites files in place
semgrep scan --config rules/use-defusedxml.yml --dryrun .    # preview the diff only
```

### 5. Test and validate rules before trusting them

Put a fixture next to the rule with the **same basename** (`no-eval.yml` →
`no-eval.py`). Annotate expected lines with comments:

```python
eval(user_data)          # ruleid: python-no-eval
eval("static")           # ok: python-no-eval
```

```bash
semgrep --validate --config rules/       # lint rule schema
semgrep --test --config rules/           # assert ruleid/ok annotations match hits
```

`--validate` catches malformed YAML/operators; `--test` fails if a `ruleid:` line
isn't flagged or an `ok:` line is. Run both in CI so rules can't rot.

### 6. CI gate on NEW findings only (git baseline)

A full scan on every PR drowns teams in legacy debt. Scan against a baseline commit so
only findings the diff *introduced* fail the build:

```bash
semgrep ci --config p/security-audit --baseline-commit "$(git merge-base origin/main HEAD)"
# or on a plain `scan`:
semgrep scan --config rules/ --baseline-commit origin/main --error .
```

`--error` sets a non-zero exit code when findings remain, which fails the pipeline
step. Emit SARIF for GitHub code scanning:

```bash
semgrep scan --config p/security-audit --sarif --output semgrep.sarif .
# GitHub Action step then: uploads semgrep.sarif via github/codeql-action/upload-sarif
```

### 7. Opengrep (LGPL fork) equivalents

The rule YAML is identical. Two CLI differences to know:

```bash
opengrep scan -f rules/ .                       # -f is the config flag (--config also works)
opengrep scan -f rules/ --sarif-output=out.sarif .   # SARIF flag name differs
opengrep scan -f rules/ --taint-intrafile .     # opt-in intra-file taint tracking
```

Prefer Opengrep when you need a fully OSS, self-hostable engine with no registry
telemetry; author against local YAML and it stays offline.

## Verify

- `semgrep --version` (and/or `opengrep --version`) prints a version — install is good.
- `semgrep --validate --config rules/` exits 0 — every rule's schema is legal.
- `semgrep --test --config rules/` reports all annotations passing — rules match what
  you think. This is the single best proof a rule actually works.
- On a known-vulnerable fixture, the scan flags it; on the sanitized version it does
  not. If a taint rule fires with the sanitizer present, your `pattern-sanitizers` is
  wrong.
- CI: confirm the step exit code is non-zero on an introduced finding (`echo $?`).

## Pitfalls

- **`...` is not regex.** It's a typed AST ellipsis. To constrain text inside a match,
  use `metavariable-regex` on a `$VAR`, not string globbing.
- **Metavariable names bind.** Two `$X` in one rule must resolve to the same code; use
  distinct names (`$A`, `$B`) when you mean different things.
- **Pattern rules can't prove reachability.** "unsafe function is called" ≠ "attacker
  input reaches it." For injection classes, use taint mode or expect false positives.
- **Registry configs need network + implicitly send metrics.** For air-gapped or
  privacy-sensitive runs, use local `--config ./rules/` and add `--metrics=off`.
- **Baseline needs real git history.** `--baseline-commit` fails in shallow clones —
  add `fetch-depth: 0` (or `git fetch --unshallow`) in CI.
- **Autofix edits files in place.** Run `--dryrun` first and review the diff; commit or
  stash beforehand so you can revert.
- **Severity ≠ exit code.** Findings alone don't fail a plain `scan`; add `--error` (or
  use `semgrep ci`) to make the pipeline actually gate.
- **Scope, don't spray.** A repo-wide `pattern: $F(...)` matches everything. Anchor with
  `pattern-inside` and `pattern-not` to keep signal high, or the team will mute the scan.
- **Authorised targets only.** Run SAST on code you own or are permitted to assess.
