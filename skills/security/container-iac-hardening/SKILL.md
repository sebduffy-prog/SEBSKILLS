---
name: container-iac-hardening
category: security
description: >
  Scan container images, Dockerfiles, Kubernetes manifests and Terraform for CVEs and
  misconfigurations, then fix them. Use when a build ships a Docker image, Helm chart, k8s
  YAML or Terraform module and you need to gate CVEs/misconfigs in CI or block bad deploys at
  admission. Runs Trivy (image + config), Checkov and KICS, wires exit-code gates, emits SARIF
  for code scanning, and generates Kyverno admission policies. Defensive, authorised only.
when_to_use:
  - Hardening a Dockerfile or base image before shipping (CVEs, root user, latest tag)
  - Gating a CI pipeline on image CVEs or IaC misconfigs with a nonzero exit code
  - Scanning Terraform / CloudFormation / Kubernetes / Helm for insecure defaults
  - Uploading SARIF findings to GitHub / GitLab code scanning
  - Adding a Kyverno admission gate so non-compliant Pods are rejected at deploy time
  - Producing an SBOM and scanning it, or diffing findings against a baseline
when_not_to_use:
  - Finding hardcoded secrets in code/history — use secrets-hygiene-and-remediation
  - App-source SAST (taint, injection, logic bugs) — use sast-semgrep-opengrep
  - Auditing third-party package/dependency CVEs & licences — use supply-chain-sca-audit
  - Redacting PII from data/documents — use pii-redaction-presidio
keywords:
  - trivy
  - checkov
  - kics
  - kyverno
  - dockerfile
  - kubernetes
  - terraform
  - container
  - cve
  - misconfiguration
  - sarif
  - admission-control
  - iac
  - sbom
  - hardening
similar_to:
  - secrets-hygiene-and-remediation
  - sast-semgrep-opengrep
  - supply-chain-sca-audit
  - pii-redaction-presidio
  - llm-red-team
inputs_needed: A Dockerfile / container image ref, and/or an IaC dir (Terraform, k8s, Helm). Optional CI runner and a k8s cluster with Kyverno for admission gating.
produces: Prioritised CVE + misconfig findings (table/JSON/SARIF), a CI gate with exit codes, an optional baseline file, and Kyverno ClusterPolicy YAML for admission-time enforcement.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Container & IaC Hardening

Scan-then-fix workflow for containers and infrastructure-as-code. Three scanners cover
overlapping surfaces — use them for what each does best:

- **Trivy** — image CVEs *and* IaC misconfig *and* secrets, one binary, fast, great SARIF.
- **Checkov** — deep, opinionated IaC policy (1000+ built-in checks), graph-aware Terraform.
- **KICS** — broad platform coverage (Terraform, k8s, Dockerfile, Ansible, CloudFormation, Helm).

Then **Kyverno** enforces the fixes at Kubernetes admission so drift can't creep back.

## When to use

Whenever a change ships a container image or touches IaC and you want a gate before it merges
or deploys. If you only care about one surface, run only that scanner.

## Prerequisites

macOS (no brew here): install the standalone binaries into `~/.local/bin` (on PATH).

```bash
mkdir -p ~/.local/bin
# Trivy (Go binary, universal darwin)
TRIVY_VER=0.58.1
curl -sL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VER}/trivy_${TRIVY_VER}_macOS-ARM64.tar.gz" \
  | tar -xz -C ~/.local/bin trivy            # use macOS-64bit on Intel
# KICS (needs its query assets; keep them beside the binary)
#   grab kics_*_darwin_arm64.tar.gz from github.com/Checkmarx/kics/releases and extract assets/
# Checkov (Python 3.7+; this Mac's python3 is 3.9 — fine)
python3 -m pip install --user checkov
trivy --version && checkov --version
```

Docker is only needed to scan a local image by name; Trivy also scans a saved tarball
(`--input img.tar`) or a remote registry ref with no daemon. Kyverno steps need a cluster
(`kubectl`) with Kyverno installed, or just the `kyverno` CLI for offline `test`/`apply`.
Grounded against the Trivy/Checkov/KICS/Kyverno docs (2026-07); verify flags with `--help`
and pin scanner versions in CI for reproducible gates.

## Recipes

### 1. Scan a container image for CVEs

```bash
# Human-readable, only actionable (fixed) HIGH/CRITICAL CVEs
trivy image --severity HIGH,CRITICAL --ignore-unfixed python:3.12-slim

# CI gate: exit 1 if any HIGH/CRITICAL is present (0 = clean)
trivy image --severity HIGH,CRITICAL --ignore-unfixed \
  --exit-code 1 --format table myorg/api:${GIT_SHA}

# Scan a tarball with no Docker daemon
docker save myorg/api:latest -o api.tar
trivy image --input api.tar --severity CRITICAL --exit-code 1
```

`--ignore-unfixed` drops CVEs with no upstream patch so the gate stays actionable. Combine
`--scanners vuln,secret,misconfig` to also flag baked-in secrets and bad image config in one pass.

### 2. Scan Dockerfile + IaC config with Trivy

```bash
# Auto-detects Dockerfile, k8s, Terraform, Helm under the path
trivy config --severity HIGH,CRITICAL --exit-code 1 .

# SARIF for GitHub code scanning (never fail the job here — let the gate step decide)
trivy config --format sarif --output trivy-config.sarif .
```

### 3. Deep IaC policy with Checkov

```bash
# Scan a directory, restrict frameworks, show only failures
checkov -d . --framework terraform,kubernetes,dockerfile --compact --quiet

# One file, SARIF out
checkov -f main.tf -o sarif --output-file-path checkov_out

# Suppress a noisy/accepted check, or run only specific ones
checkov -d . --skip-check CKV_AWS_18,CKV_K8S_43
checkov -d . --check CKV_AWS_20            # only this policy

# Snapshot current findings, then fail only on NEW issues on later runs
checkov -d . -o json | python3 -m json.tool > /dev/null   # sanity
checkov -d . --create-baseline             # writes .checkov.baseline
checkov -d . --baseline .checkov.baseline  # future runs ignore known findings
```

Checkov exits nonzero when any check fails; add `--soft-fail` to report without failing
the build (use during initial rollout, then remove to enforce). Inline waivers also work:
add a comment `# checkov:skip=CKV_AWS_20:reason` above the offending resource.

### 4. Broad multi-platform scan with KICS

```bash
# KICS needs its bundled query assets — point at them if not in the default location
kics scan -p . -t Terraform,Kubernetes,Dockerfile \
  --report-formats json,sarif -o ./kics-results \
  --fail-on high,critical --exclude-paths "tests/*,examples/*"
```

`--fail-on` sets which severities flip the exit code. `-t` limits platforms so a mixed repo
doesn't scan things you don't own.

### 5. SBOM, then scan the SBOM

```bash
trivy image --format cyclonedx --output sbom.cdx.json myorg/api:latest
trivy sbom --severity HIGH,CRITICAL --exit-code 1 sbom.cdx.json
```

Decoupling generation from scanning re-scans an old artifact against today's CVE DB.

### 6. Fix the common Dockerfile findings

The misconfig scanners flag the same handful repeatedly. Fix at the source:

```dockerfile
# BAD: FROM node:latest            (unpinned, unpredictable)
FROM node:20.18-bookworm-slim      # pin major.minor + distro
# ... build ...
RUN adduser --system --no-create-home app   # don't run as root
USER app                                     # DS002 / CKV_DOCKER_3
HEALTHCHECK CMD node healthcheck.js          # CKV_DOCKER_2
# COPY only what's needed; avoid `ADD <url>`; no secrets in ENV/ARG
```

Re-run `trivy config .` (or `checkov -f Dockerfile`) to confirm the finding clears.

### 7. CI gate (GitHub Actions)

```yaml
- name: Trivy image scan (gating)
  run: |
    trivy image --severity HIGH,CRITICAL --ignore-unfixed \
      --exit-code 1 --format table "${IMAGE}"
- name: Trivy IaC SARIF (report-only)
  if: always()
  run: trivy config --format sarif --output trivy.sarif .
- uses: github/codeql-action/upload-sarif@v3
  if: always()
  with: { sarif_file: trivy.sarif }
```

Keep the *gating* step and the *SARIF upload* step separate: the gate fails the build; the
upload always runs (`if: always()`) so findings still land in the Security tab.

### 8. Kyverno admission gate — enforce the fix in-cluster

Scanners catch issues pre-merge; Kyverno rejects non-compliant Pods at `kubectl apply` time
so nothing slips through. Save as `disallow-privileged.yaml`:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-privileged-containers
spec:
  background: true
  rules:
    - name: check-privileged
      match:
        any:
          - resources:
              kinds: [Pod]
      validate:
        failureAction: Enforce        # Audit = log-only; Enforce = block
        message: "Privileged containers are not allowed."
        pattern:
          spec:
            =(initContainers):
              - =(securityContext):
                  =(privileged): "false"
            containers:
              - =(securityContext):
                  =(privileged): "false"
```

Test it offline before you ship it to the cluster, then apply:

```bash
kyverno apply disallow-privileged.yaml --resource my-pod.yaml   # dry, prints pass/fail
kubectl apply -f disallow-privileged.yaml                       # install into cluster
```

Roll out with `failureAction: Audit` first, watch `PolicyReport`s, then flip to `Enforce`.
For a full battle-tested set, install the Kyverno "Pod Security" policy library rather than
hand-writing every rule.

## Verify

- **Gate actually fails**: introduce a known bad (`FROM ubuntu:latest` + `USER root`, or a
  public S3 bucket), confirm the scanner exits nonzero, revert, confirm exit 0.
- **SARIF is valid**: `python3 -c "import json;json.load(open('trivy.sarif'))"` and confirm it
  uploads to the code-scanning tab.
- **Kyverno blocks**: `kubectl run bad --image=nginx --privileged --dry-run=server` is rejected
  once the policy is in `Enforce`.

## Pitfalls

- **First Trivy run is slow / flaky offline** — it downloads the vuln DB. Pre-warm with
  `trivy image --download-db-only` and cache `~/.cache/trivy` (or `--cache-dir`) in CI.
- **KICS "no queries found"** — the CLI needs its `assets/queries` directory; ship them
  alongside the binary or pass `-q /path/to/assets/queries`. The Docker image bundles them.
- **Scanning everything, gating on noise** — start report-only (`--soft-fail` / `Audit` /
  `--severity CRITICAL`), triage, baseline the accepted set, *then* tighten the gate. A gate
  that always red gets ignored.
- **`--ignore-unfixed` hides real risk if misused** — great for a merge gate (nothing to do
  yet), wrong for a periodic audit where you want visibility into unpatched CVEs.
- **`validationFailureAction` is deprecated** — Kyverno moved enforcement to per-rule
  `validate.failureAction` (shown above); the old top-level `spec.validationFailureAction`
  still parses on older versions but prefer the rule-level field.
- **Kyverno patterns need anchors** — `=(field)` means "if present, must match"; a bare key
  means "must exist and match". Omitting anchors can reject Pods that legitimately lack a field.
- **Overlapping findings across three tools** — pick one authoritative scanner per surface
  (e.g. Checkov for Terraform, Trivy for images), run the others report-only, and pin scanner
  + CVE-DB versions in CI so a scanner bump doesn't suddenly fail an untouched repo.
