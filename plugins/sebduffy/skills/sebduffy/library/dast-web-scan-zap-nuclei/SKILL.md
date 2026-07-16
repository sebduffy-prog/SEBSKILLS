---
name: dast-web-scan-zap-nuclei
category: security
description: >-
  Dynamically scan a RUNNING web app or API for live vulnerabilities using
  OWASP ZAP (baseline / full / API scan) and ProjectDiscovery Nuclei
  (template-driven CVE + misconfig checks), then wire both into CI as a
  gate. Use when someone says "add a DAST scan", "scan the staging site",
  "check the running app for vulns", "run ZAP against our URL", "run
  nuclei", "find exposed panels / CVEs on this host", or "fail the pipeline
  on new web findings". Covers Docker + GitHub Actions, auth headers, alert
  suppression, JSON/SARIF output, and safe-scope guardrails. AUTHORISED
  targets only.
when_to_use:
  - Scanning a deployed/staging web app or API for live runtime vulnerabilities
  - Running an OWASP ZAP baseline, full, or API (OpenAPI/GraphQL) scan
  - Running Nuclei templates for known CVEs, exposed panels, and misconfigurations
  - Adding a DAST leg to CI to complement SAST + SCA in the AppSec triad
  - Gating a pipeline on new web findings, or triaging/suppressing false positives
  - Scanning an authenticated app by injecting a session/bearer header
when_not_to_use:
  - Static analysis of source code for bug patterns — use sast-semgrep-opengrep
  - Auditing dependency/CVE risk from manifests — use supply-chain-sca-audit
  - Hardening Dockerfiles/Terraform/K8s config — use container-iac-hardening
  - Attacking an LLM app's prompt layer — use llm-red-team
  - Finding committed secrets in a repo — use secrets-hygiene-and-remediation
keywords:
  - dast
  - owasp-zap
  - nuclei
  - web-scanning
  - vulnerability-scan
  - baseline-scan
  - api-scan
  - ci-gate
  - sarif
  - projectdiscovery
  - cve
  - misconfiguration
  - github-actions
  - appsec
  - penetration-testing
similar_to:
  - sast-semgrep-opengrep
  - supply-chain-sca-audit
  - container-iac-hardening
  - llm-red-team
  - secrets-hygiene-and-remediation
inputs_needed: A running target URL you are AUTHORISED to scan (staging/local); optionally an OpenAPI/GraphQL spec for API scans, a session/bearer header for authenticated scans, and Docker or Go available locally / a GitHub Actions runner for CI.
produces: HTML/Markdown/JSON ZAP reports and JSONL/SARIF Nuclei findings, plus a copy-paste CI workflow that runs the scan and fails on new issues.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# DAST Web Scanning with OWASP ZAP + Nuclei

Two complementary dynamic scanners against a **running** target:

- **OWASP ZAP** — a full web-app proxy/scanner. Crawls the app, runs passive
  rules (baseline) or active attacks (full scan), and understands API specs.
  Best for *your own app's* logic: XSS, injection, missing headers, CSRF, cookie flags.
- **Nuclei** — a fast, template-driven engine. Fires thousands of YAML checks for
  *known* CVEs, exposed admin panels, default creds, and misconfigurations.
  Best for breadth across hosts and catching publicly-known issues quickly.

Run both: ZAP for depth on the app you built, Nuclei for known-CVE breadth.

## When to use

Reach for this when you have a **deployed or locally-running** app/API and want
to find live vulnerabilities — not when you only have source code (that's SAST)
or a dependency manifest (that's SCA). This is the DAST leg of the triad.

## Authorisation (read first)

DAST sends real (sometimes attacking) traffic. Only scan targets you own or have
**written permission** to test. A ZAP *full scan* and many Nuclei templates are
active/intrusive — never point them at production or third-party hosts without
sign-off. Prefer staging or a local instance. Rate-limit against fragile targets.

## Prerequisites

- **Docker** (easiest for ZAP; no local install) — `docker --version`.
- **Nuclei**: `go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest`
  (needs Go >= 1.24), or Docker image `projectdiscovery/nuclei:latest`, or macOS
  `brew install nuclei`. First run: `nuclei -update-templates`.
- The ZAP image is `ghcr.io/zaproxy/zaproxy:stable` (the old `owasp/zap2docker-*`
  images are **retired** — do not use them).
- For CI: a GitHub Actions runner (both tools ship official actions).

## Recipes

### 1. ZAP baseline scan (passive, safe, ~1 min)

Spiders the target and runs passive rules only — no attacks. Safe first pass.

```bash
docker run --rm -v "$(pwd):/zap/wrk/:rw" -t ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py \
  -t https://staging.example.com \
  -r zap-baseline.html \
  -J zap-baseline.json \
  -j                       # also use the modern (AJAX-aware) spider
```

Reports land in the mounted dir (`/zap/wrk` == cwd). Exit code: `0` = clean,
`1` = FAIL-level alerts, `2` = WARN, `3` = internal error. Use `-w report.md`
for a Markdown report.

### 2. ZAP full active scan (intrusive — staging only)

Adds the active scanner (real attack payloads). Slower and can mutate data.

```bash
docker run --rm -v "$(pwd):/zap/wrk/:rw" -t ghcr.io/zaproxy/zaproxy:stable \
  zap-full-scan.py -t https://staging.example.com -r zap-full.html -J zap-full.json
```

### 3. ZAP API scan (OpenAPI / Swagger / GraphQL)

Feeds ZAP a spec so it exercises every endpoint instead of guessing by crawling.

```bash
docker run --rm -v "$(pwd):/zap/wrk/:rw" -t ghcr.io/zaproxy/zaproxy:stable \
  zap-api-scan.py -t https://api.example.com/openapi.json -f openapi \
  -r zap-api.html -J zap-api.json
```

`-f` accepts `openapi`, `soap`, or `graphql`.

### 4. Suppressing ZAP false positives

Generate a baseline TSV, mark noisy rules `IGNORE`, feed it back with `-c`:

```bash
# 1. Emit a config listing every triggered rule (all set to WARN)
docker run --rm -v "$(pwd):/zap/wrk/:rw" -t ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t https://staging.example.com -g gen.conf
# 2. Edit gen.conf: change WARN -> IGNORE for accepted findings (by rule ID)
# 3. Re-run with the tuned config so ignored rules no longer fail the build
docker run --rm -v "$(pwd):/zap/wrk/:rw" -t ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t https://staging.example.com -c gen.conf -J zap.json
```

### 5. Scanning an authenticated app (ZAP)

Inject a header on every request via env vars the ZAP scripts read:

```bash
docker run --rm -v "$(pwd):/zap/wrk/:rw" \
  -e ZAP_AUTH_HEADER="Authorization" \
  -e ZAP_AUTH_HEADER_VALUE="Bearer $TOKEN" \
  -e ZAP_AUTH_HEADER_SITE="staging.example.com" \
  -t ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t https://staging.example.com -J zap.json
```

### 6. Nuclei — known-CVE + misconfig sweep

```bash
nuclei -update-templates                       # refresh the template store first
nuclei -u https://staging.example.com \
  -severity critical,high,medium \
  -rate-limit 50 \                             # be gentle on fragile targets
  -jsonl-export nuclei.jsonl                    # machine-readable findings
```

Multiple targets: `nuclei -list urls.txt`. Narrow the template set with
`-tags cve,exposure` or `-t http/exposures/` and mute noise with
`-exclude-tags fuzz`. Add `-sarif-export nuclei.sarif` for GitHub code scanning.

Docker equivalent (mount cwd for the report):

```bash
docker run --rm -v "$(pwd):/root/nuclei-output" projectdiscovery/nuclei:latest \
  -u https://staging.example.com -severity critical,high \
  -jsonl-export /root/nuclei-output/nuclei.jsonl
```

### 7. Triage the Nuclei JSONL

```bash
# Count findings by severity
jq -r '.info.severity' nuclei.jsonl | sort | uniq -c | sort -rn
# List each finding: severity, template, matched URL
jq -r '"\(.info.severity)\t\(.["template-id"])\t\(.["matched-at"])"' nuclei.jsonl
```

### 8. CI gate — GitHub Actions

Runs on a deployed URL (set `TARGET_URL`) and fails on real findings. ZAP's
action opens a tracking issue with the alerts; Nuclei uploads SARIF to code scanning.

```yaml
name: dast
on:
  workflow_dispatch:
  schedule: [{ cron: "0 3 * * 1" }]   # weekly Monday 03:00 — DAST is slow; don't run per-PR
jobs:
  zap-baseline:
    runs-on: ubuntu-latest
    permissions: { issues: write, contents: read }
    steps:
      - uses: zaproxy/action-baseline@v0.15.0
        with:
          target: ${{ vars.TARGET_URL }}
          fail_action: true            # non-zero exit on FAIL-level alerts
          # rules_file_name: .zap/rules.tsv   # optional IGNORE list (rule\tIGNORE)

  nuclei:
    runs-on: ubuntu-latest
    permissions: { security-events: write, contents: read }
    steps:
      - uses: projectdiscovery/nuclei-action@v3   # v3 is CLI-first: pass real nuclei flags in `args`
        with:
          args: -u ${{ vars.TARGET_URL }} -severity critical,high -sarif-export nuclei.sarif
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with: { sarif_file: nuclei.sarif }
```

> Note: `nuclei-action@v2.x` (with `target`/`templates`/`flags` inputs) is
> **deprecated and unsupported after 2026-03-01** — use `@v3` and put flags in `args`.

## Verify

- ZAP produced a report: `test -s zap-baseline.json && echo "ZAP ran"`.
- Nuclei ran and templates loaded: `nuclei -version` and check
  `nuclei.jsonl` exists (empty = no findings, which is a valid pass).
- Confirm the exit code drives the gate: baseline returns `1` when FAIL alerts
  exist. Prove the pipeline actually *fails* by pointing it once at a known-bad
  target (e.g. `http://testphp.vulnweb.com` or a local juice-shop) and watching it go red.
- Sanity-check scope: the target in every command matches the authorised host.

## Pitfalls

- **Old ZAP images.** `owasp/zap2docker-stable` is retired. Use
  `ghcr.io/zaproxy/zaproxy:stable`, else you pull a stale/broken image.
- **Volume mount missing → no reports.** ZAP writes to `/zap/wrk`; without
  `-v "$(pwd):/zap/wrk/:rw"` your `-r/-J` files vanish with the container.
- **Full scan on production.** `zap-full-scan.py` sends attack payloads and can
  create/delete data. Staging only, with authorisation.
- **Running per-PR.** DAST needs a live deploy and is slow (minutes). Schedule it
  or trigger post-deploy — don't block every commit on it.
- **Stale Nuclei templates.** Always `-update-templates` (or `-cache` in the
  action) or you miss recent CVEs — the whole point of Nuclei.
- **Rate limits / WAFs.** Aggressive scans trip WAFs and rate limiters, poisoning
  results. Tune `-rate-limit` (Nuclei) and scan from an allow-listed source.
- **Auth expiry.** A bearer token that expires mid-scan makes ZAP crawl the login
  page and report nothing useful — use a long-lived staging token.
- **SPA blind spots.** Traditional spider misses JS-rendered routes; add ZAP's
  modern spider (`-j`) and, for heavy SPAs, seed it with an OpenAPI spec (recipe 3).
