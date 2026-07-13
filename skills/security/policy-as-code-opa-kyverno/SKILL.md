---
name: policy-as-code-opa-kyverno
category: security
description: >
  Author, test, and enforce policy-as-code with OPA/Rego, Conftest, and Kyverno. Use to
  write default-deny admission and config guardrails (block latest tags, require limits,
  ban :latest, enforce labels), unit-test policies with opa test, gate IaC/manifests in
  CI with conftest test, and run Kyverno ClusterPolicies against Kubernetes. Grounds every
  command against OPA 1.0 (Rego v1) and current Kyverno so nothing is fabricated.
when_to_use:
  - Writing preventative guardrails (default-deny) for Kubernetes manifests, Terraform plans, or Dockerfiles
  - Unit-testing Rego policies with opa test and formatting/linting with opa fmt / opa check
  - Gating IaC and YAML in CI with conftest before merge or apply
  - Building Kyverno ClusterPolicies for in-cluster admission control (validate/mutate/generate)
  - Migrating legacy Rego (deny[msg]) to OPA 1.0 Rego v1 (deny contains msg if)
  - Standing up a reusable policy library shared across repos via conftest push/pull (OCI)
when_not_to_use:
  - Reactively scanning already-deployed cloud/K8s config for drift — use container-iac-hardening
  - Scanning source code for injection/vuln patterns — use sast-semgrep-opengrep
  - Auditing dependency CVEs / SBOMs — use supply-chain-sca-audit
  - Finding hardcoded secrets in a repo — use secrets-hygiene-and-remediation
keywords:
  - opa
  - rego
  - conftest
  - kyverno
  - policy-as-code
  - admission-control
  - open-policy-agent
  - default-deny
  - kubernetes
  - terraform
  - guardrails
  - gatekeeper
  - rego-v1
  - ci-gate
similar_to:
  - container-iac-hardening
  - sast-semgrep-opengrep
  - supply-chain-sca-audit
inputs_needed: Manifests/IaC to gate (K8s YAML, Terraform plan JSON, Dockerfile) or a cluster; the rules you want enforced; opa/conftest/kyverno binaries.
produces: Rego policy modules + tests, Conftest CI gate, Kyverno ClusterPolicy YAML, and a validate.sh that runs opa check/test + conftest verify.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Policy-as-Code: OPA/Rego, Conftest & Kyverno

Shift-left, **preventative** policy: write rules once, unit-test them, gate them in CI
(Conftest), enforce them at the Kubernetes admission webhook (Kyverno). You *block* the bad
manifest before it ever applies.

## When to use

When the ask is "stop X from ever shipping" — no `:latest` images, limits required, no
privileged pods, mandatory `team` labels, no public S3. If instead you're *scanning what
already exists*, use the alternatives named in the frontmatter. Three tools, one model:

| Tool | Language | Best at |
|------|----------|---------|
| **OPA + Rego** | Rego | the policy engine + unit tests (`opa eval` / `opa test`) |
| **Conftest** | Rego | gating files (YAML/JSON/HCL/Dockerfile) in CI pre-merge |
| **Kyverno** | YAML (no Rego) | live K8s admission: validate / mutate / generate |

## Prerequisites

macOS (no brew here) — install the standalone binaries:

```bash
# OPA (Apple Silicon; use _amd64 on Intel)
curl -L -o /usr/local/bin/opa https://openpolicyagent.org/downloads/latest/opa_darwin_arm64_static
chmod +x /usr/local/bin/opa && opa version   # expect 1.x (Rego v1 is the default)

# Conftest
curl -L -o /tmp/conftest.tgz https://github.com/open-policy-agent/conftest/releases/latest/download/conftest_Darwin_arm64.tar.gz
tar -xzf /tmp/conftest.tgz -C /usr/local/bin conftest && conftest --version

# Kyverno CLI (only for local Kyverno testing): kyverno-cli_*_darwin_arm64.tar.gz
# from https://github.com/kyverno/kyverno/releases
```

Honest deps: **OPA ≥ 1.0 makes Rego v1 the default** — `deny[msg]` no longer parses; write
`deny contains msg if { ... }`. Conftest defaults to a `policy/` dir (override `-p/--policy`)
and package `main` (override `--namespace`). Kyverno needs a cluster (or `kyverno apply`
offline); no API key for either. Terraform must be rendered to JSON (`terraform show -json`).

## Recipes

### 1. A default-deny Conftest policy for Kubernetes (Rego v1)

`policy/deployment.rego`:

```rego
package main

import rego.v1

# deny: Deployments must not use the :latest tag or an untagged image
deny contains msg if {
	input.kind == "Deployment"
	some container in input.spec.template.spec.containers
	endswith(container.image, ":latest")
	msg := sprintf("container %q uses a mutable :latest tag", [container.name])
}

# deny: every container must set a memory limit
deny contains msg if {
	input.kind == "Deployment"
	some container in input.spec.template.spec.containers
	not container.resources.limits.memory
	msg := sprintf("container %q must set resources.limits.memory", [container.name])
}
```

Run it:

```bash
conftest test deployment.yaml               # policies auto-loaded from ./policy
conftest test -p policy/ manifests/*.yaml   # explicit dir, multiple files
cat deployment.yaml | conftest test -       # from stdin
```

Exit code is non-zero on any `deny` (or `warn` with `--fail-on-warn`), so it drops straight
into CI. Use `violation` instead of `deny` for structured objects (`{"msg", "details"}`).

### 2. Unit-test the policy with `opa test`

Tests are Rego rules prefixed `test_`. `policy/deployment_test.rego`:

```rego
package main

import rego.v1

test_denies_latest_tag if {
	deny["container \"api\" uses a mutable :latest tag"] with input as {
		"kind": "Deployment",
		"spec": {"template": {"spec": {"containers": [{"name": "api", "image": "app:latest"}]}}},
	}
}

test_allows_pinned_tag_with_limits if {
	count(deny) == 0 with input as {"kind": "Deployment", "spec": {"template": {"spec": {"containers": [{
		"name": "api", "image": "app:1.4.2", "resources": {"limits": {"memory": "256Mi"}},
	}]}}}}
}
```

```bash
opa test policy/ -v          # run all tests, verbose
opa test policy/ -c          # with coverage report
opa fmt -w policy/           # auto-format (canonical Rego style)
opa check --strict policy/   # parse + type + strict-mode lint
```

### 3. Gate a Terraform plan in CI

Render the plan to JSON first — rules read `input.resource_changes[]`, not raw HCL:

```bash
terraform plan -out=tfplan.bin && terraform show -json tfplan.bin > tfplan.json
conftest test -p policy/terraform tfplan.json
```

```rego
package main
import rego.v1

deny contains msg if {
	some rc in input.resource_changes
	rc.type == "aws_s3_bucket"
	rc.change.after.acl == "public-read"
	msg := sprintf("S3 bucket %q must not be public-read", [rc.address])
}
```

### 4. Enforce at admission with a Kyverno ClusterPolicy (no Rego)

Kyverno policies are plain YAML. `require-limits.yaml`:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resource-limits
spec:
  background: true
  rules:
    - name: check-memory-limit
      match:
        any:
          - resources:
              kinds: ["Pod"]
      validate:
        failureAction: Enforce             # Enforce = block; Audit = report only
        message: "Every container must set resources.limits.memory."
        pattern:
          spec:
            containers:
              - resources:
                  limits:
                    memory: "?*"           # ?* = any non-empty value
```

Test it offline against manifests before you ever touch the cluster:

```bash
kyverno apply require-limits.yaml --resource bad-pod.yaml   # prints pass/fail per rule
kyverno test .                                              # run a kyverno-test.yaml suite
```

Then in-cluster: `kubectl apply -f require-limits.yaml`. With `Enforce` non-compliant Pods
are rejected by the webhook; with `Audit` they're allowed but logged as PolicyReports.
`validate.failureAction` is per-rule in current Kyverno (the old spec-level
`validationFailureAction` and lowercase `enforce`/`audit` are deprecated). Kyverno also does
`mutate` and `generate` — same shape.

### 5. Share a policy library over OCI (Conftest)

```bash
conftest push ghcr.io/acme/policies:latest   # push ./policy as an OCI artifact
conftest pull ghcr.io/acme/policies:latest   # pull into ./policy on other repos
conftest verify -p policy/                    # run the *_test.rego suites in the lib
```

## Verify

`scripts/validate.sh` is the CI gate — it fails fast on any parse error, failing test, or
policy violation:

```bash
bash scripts/validate.sh policy/ examples/   # <policy-dir> <manifests-dir>
```

It runs, in order: `opa fmt --fail`, `opa check --strict`, `opa test -c`, then
`conftest test` over the manifests. Manual spot-check the raw deny set:

```bash
opa eval -d policy/ -i deployment.yaml 'data.main.deny' -f pretty
```

## Pitfalls

- **Rego v1 is mandatory on OPA 1.0.** Legacy `deny[msg] { ... }` fails with "`if` keyword
  is required". Add `import rego.v1` and rewrite to `deny contains msg if { ... }`, or run
  `opa fmt --rego-v1 -w policy/` to auto-migrate an old repo.
- **Conftest default namespace is `main`.** If your package is `kubernetes.deployment`,
  Conftest won't find your rules unless you pass `--namespace kubernetes.deployment` (or
  `--all-namespaces`). Keep it simple: `package main`.
- **`deny` vs `warn` vs `violation`.** Only `deny` and unwaived `violation` fail the build
  by default; `warn` needs `--fail-on-warn`. Don't expect `warn` to block a merge.
- **Empty deny set ≠ error.** A policy that never matches silently passes. Always write a
  `test_denies_*` case so a typo'd field path (`limits.memmory`) is caught by CI, not prod.
- **Kyverno `pattern` uses wildcards, not Rego.** `"?*"` = required/any value, `"*"` =
  optional. For conditional logic use `validate.deny` / `foreach` / CEL — Kyverno runs no Rego.
- **Enforce in staging first.** Ship every Kyverno policy as `Audit`, watch PolicyReports
  for false positives, then flip to `Enforce` — going straight to Enforce can wedge deploys.
- **Prevention, not detection.** This stops new bad config; it won't find what's already
  running or drifted — pair with container-iac-hardening for that.
