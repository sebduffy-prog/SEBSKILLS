---
name: secrets-hygiene-and-remediation
category: security
description: >
  Hunt and kill leaked credentials. Scan working tree AND full git history with gitleaks,
  triage findings, then run the real incident playbook: ROTATE the exposed secret first,
  purge it from history with git-filter-repo/BFG, force-push, and invalidate caches. Then
  stop recurrence by wiring a gitleaks pre-commit + CI gate and moving secrets into a
  manager (SOPS+age or Vault). Use when a key is committed, a repo is going public, or an
  audit demands "prove there are no secrets in git".
when_to_use:
  - A credential (API key, token, password, private key) was committed and may be in git history
  - Preparing a private repo to go open-source and need to prove history is clean
  - Standing up CI/pre-commit secret scanning to block future leaks
  - An auditor or security review asks for evidence of secret hygiene
  - Migrating hardcoded secrets into a managed store (SOPS/age or Vault)
when_not_to_use:
  - Scanning source for code vulnerabilities/injection — use sast-semgrep-opengrep
  - Auditing third-party dependency CVEs — use supply-chain-sca-audit
  - Redacting PII from documents or datasets — use pii-redaction-presidio
  - Hardening container images / Terraform / IaC config — use container-iac-hardening
keywords:
  - secrets
  - gitleaks
  - credential-leak
  - git-history
  - secret-scanning
  - sops
  - age
  - vault
  - key-rotation
  - git-filter-repo
  - pre-commit
  - remediation
  - bfg
  - dotenv
similar_to:
  - sast-semgrep-opengrep
  - supply-chain-sca-audit
  - container-iac-hardening
  - pii-redaction-presidio
  - llm-red-team
inputs_needed: Repo path (with .git); write access to rotate the leaked secret at its provider; optional CI provider for the gate.
produces: Gitleaks findings report (SARIF/JSON), a rotate→purge→prevent remediation record, a committed pre-commit/CI scan gate, and secrets migrated to SOPS/age or Vault.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Secrets Hygiene and Remediation

Find leaked credentials in a repo (working tree **and** full git history), remediate in the
correct order, and stop it recurring. The cardinal rule: **a secret in git history is
compromised the moment it is pushed — rotate it, don't just delete it.** Purging history
without rotating is theatre; anyone who cloned still has the key.

## When to use

Use when a credential was committed, a repo is going public, you need a CI/pre-commit gate,
or an audit wants proof the history is clean. For code-vuln SAST use `sast-semgrep-opengrep`;
for dependency CVEs use `supply-chain-sca-audit`; for document PII use `pii-redaction-presidio`.

## Prerequisites

- **gitleaks v8+** — standalone binary, no brew needed on this Mac:
  ```bash
  GL=8.28.0; ARCH=$(uname -m | sed 's/arm64/arm64/;s/x86_64/x64/')
  curl -sSL -o /tmp/gl.tar.gz \
    "https://github.com/gitleaks/gitleaks/releases/download/v${GL}/gitleaks_${GL}_darwin_${ARCH}.tar.gz"
  tar -xzf /tmp/gl.tar.gz -C /tmp gitleaks && sudo mv /tmp/gitleaks /usr/local/bin/
  gitleaks version
  ```
- **git-filter-repo** for history rewrite (`pip3 install git-filter-repo`), or the BFG jar.
- **sops** + **age** if migrating to file-based secret management (binaries from their GitHub
  releases; both are single static binaries).
- Provider access to actually **rotate** the exposed credential (AWS/GitHub/Stripe/etc.).

Gitleaks exit codes: `0` = clean, `1` = leaks (or error) found, `126` = unknown flag. CI
gates rely on the `1`.

## Recipe 1 — Scan (working tree + full history)

Full-history scan is the important one — `git status` only shows the current tree.

```bash
cd /path/to/repo

# Full git history (uses `git log -p` under the hood). This is the audit scan.
gitleaks git . -v --report-format sarif --report-path gitleaks-history.sarif

# Only the working tree + staged/untracked files (no history) — fast pre-flight.
gitleaks dir . -v --report-format json --report-path gitleaks-tree.json

# Scope history to a range or all refs (e.g. after a suspected leak window):
gitleaks git . --log-opts="--all commitA..commitB"
```

Triage every hit: `RuleID`, `File`, `Commit`, `Secret` (redacted with `--redact=100`),
`StartLine`. Confirm each is a **live** credential before the fire drill — vendored test
fixtures and rotated keys are noise. Suppress confirmed false positives in `.gitleaks.toml`:

```toml
[[allowlists]]
description = "known-safe test fixtures & sample keys"
paths = ['''tests/fixtures/.*''', '''.*\.example$''']
regexes = ['''EXAMPLE_KEY_DO_NOT_USE''']
commits = ["<full-sha-of-a-reviewed-benign-commit>"]
```

Re-run with `-c .gitleaks.toml`. Keep the allowlist tight and reviewed — a loose allowlist
is how the next real leak slips through.

## Recipe 2 — Remediate a confirmed live leak (ORDER MATTERS)

1. **Rotate first, always.** Revoke/regenerate the credential at the provider *now*. History
   surgery is slow; a live key is exploitable in seconds. Assume every cloner has it.
2. **Purge from history** once the old value is dead (belt-and-braces so it can't be
   re-leaked or grepped by anyone who pulls later):
   ```bash
   # Replace the literal secret everywhere in history with ***REMOVED***
   printf 'literal-leaked-value==>***REMOVED***\n' > /tmp/replace.txt
   git filter-repo --replace-text /tmp/replace.txt

   # Or excise an entire file that should never have been tracked:
   git filter-repo --invert-paths --path config/secrets.yaml
   ```
   `git filter-repo` rewrites SHAs and drops the `origin` remote by design.
3. **Force-push the rewritten history** and have every collaborator re-clone (old clones and
   open PRs still carry the secret):
   ```bash
   git remote add origin git@github.com:org/repo.git
   git push --force --all && git push --force --tags
   ```
4. **Invalidate downstream caches.** On GitHub, rewritten commits can persist via cached
   views and forks — open a support request to purge cached commit SHAs, and check forks.
5. **Record it.** Note in your incident log: what leaked, when, when rotated, purge SHA,
   who re-cloned. That record is the audit evidence.

## Recipe 3 — Prevent recurrence: the gate

**Pre-commit** (blocks the leak before it is ever committed):

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.28.0
    hooks:
      - id: gitleaks
```
```bash
pip3 install pre-commit && pre-commit install
# Emergency bypass (use sparingly, it defeats the point): SKIP=gitleaks git commit ...
```

**CI gate** (defence in depth — the hook can be skipped, CI cannot):

```yaml
# .github/workflows/secrets.yml
name: secret-scan
on: [push, pull_request]
jobs:
  gitleaks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }   # full history, not just the tip commit
      - uses: gitleaks/gitleaks-action@v2
        env: { GITLEAKS_CONFIG: .gitleaks.toml }
```

Pin a **baseline** so an existing (already-remediated) finding backlog doesn't fail every
build while you burn it down: `gitleaks git . --baseline-path gitleaks-baseline.json`.

## Recipe 4 — Move secrets into a manager (so there's nothing to leak)

**SOPS + age** — encrypted secrets committed safely alongside code; only the private age key
decrypts them:

```bash
# One-time: generate an age keypair (prints the public recipient age1... )
age-keygen -o ~/.config/sops/age/keys.txt
export SOPS_AGE_KEY_FILE="$HOME/.config/sops/age/keys.txt"
```
```yaml
# .sops.yaml — auto-applies rules; devs never pass --age by hand
creation_rules:
  - path_regex: \.enc\.(ya?ml|json|env)$
    age: age1qxy...your-public-recipient...
    encrypted_regex: '^(data|stringData|password|token|.*_KEY)$'  # values only; keys stay readable
```
```bash
sops --encrypt --in-place secrets.enc.yaml   # encrypt in place per .sops.yaml
sops secrets.enc.yaml                         # opens $EDITOR on the DECRYPTED view; re-encrypts on save
sops --decrypt secrets.enc.yaml               # print plaintext (piping/debug)
sops exec-env secrets.enc.yaml './run.sh'     # inject decrypted values as env vars for a command
```
Commit only `*.enc.yaml`; never commit `keys.txt`. Distribute the age *public* key freely;
guard the private key file (0600, out of the repo).

**Vault** (dynamic/short-lived secrets, org scale) — reference by path, fetch at runtime;
never write the value to disk:
```bash
vault kv put secret/app/db password="$(openssl rand -base64 24)"
export DB_PASS="$(vault kv get -field=password secret/app/db)"
```

## Verify

```bash
gitleaks git . -v --report-format json --report-path /tmp/verify.json; echo "exit=$?"
# exit=0 and an empty findings array == clean history.
git log --all -p -S 'literal-leaked-value' | head   # must return NOTHING post-purge
sops --decrypt secrets.enc.yaml >/dev/null && echo "sops round-trips OK"
pre-commit run gitleaks --all-files                  # hook is wired and passes
```

## Pitfalls

- **Deleting a file in a new commit does NOT remove it from history.** `git rm secrets.yaml`
  leaves it in every prior commit — you must rewrite history (Recipe 2) *and* rotate.
- **Purging without rotating is the #1 mistake.** The key was public the moment it pushed.
  Rotate first, every time.
- **`gitleaks dir`/`detect` misses history.** Only `gitleaks git` walks commits — always run
  the git-mode scan for an audit, not just the tree scan.
- **CI must checkout full history** (`fetch-depth: 0`); the default shallow clone scans one
  commit and gives false confidence.
- **`git filter-repo` drops the `origin` remote and rewrites all SHAs** on purpose — re-add
  the remote, force-push, and warn collaborators to re-clone (rebasing on old history
  reintroduces the secret).
- **Forks and cached provider views survive a rewrite.** Delete/rewrite forks and ask the
  host to purge cached SHAs, or the "removed" secret is still fetchable.
- **Committing the age private key** defeats SOPS entirely. Encrypt values, never the key;
  keep `keys.txt` outside the repo with `chmod 600`.
- **`encrypted_regex` too broad** encrypts structural keys and breaks tooling; scope it to
  value fields so diffs stay reviewable.
