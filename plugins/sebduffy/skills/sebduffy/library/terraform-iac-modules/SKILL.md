---
name: terraform-iac-modules
category: devops
description: >
  Author production Terraform / OpenTofu — reusable modules with typed variables + outputs, remote
  state with locking (S3 native lockfile or DynamoDB, GCS, azurerm), drift detection via
  plan -detailed-exitcode, and a fmt/validate/tflint/checkov gate in CI. Use when writing or
  refactoring .tf modules, wiring backends/workspaces, or hardening an IaC pipeline. Works with
  either `terraform` or `tofu` — commands are interchangeable.
when_to_use:
  - Writing a new reusable Terraform/OpenTofu module (variables, outputs, versions.tf)
  - Configuring remote state with locking (S3 use_lockfile, DynamoDB, GCS, azurerm)
  - Adding drift detection to a scheduled job or PR check
  - Wiring fmt / validate / tflint / checkov into GitHub Actions or pre-commit
  - Migrating from Terraform to OpenTofu, or splitting a monolith root into modules
when_not_to_use:
  - Building or shipping container images — use dockerfile-and-compose-authoring
  - Authoring the CI workflow YAML itself (matrices, caching, OIDC) — use github-actions-pipelines
  - Imperative cloud one-offs or app deploys (Railway/Vercel) — use the platform's own skill
  - Ansible/Chef/Puppet config management — Terraform is provisioning, not config mgmt
keywords: [terraform, opentofu, tofu, iac, modules, remote-state, state-locking, drift-detection, checkov, tflint, backend, s3-backend, terraform-fmt, terraform-validate, hcl, devops]
similar_to: [dockerfile-and-compose-authoring, github-actions-pipelines, incident-response-and-postmortem]
inputs_needed: A target cloud (AWS/GCP/Azure), credentials/OIDC for plan+apply, and a state backend bucket/container already created (or permission to create one).
produces: A module directory (main/variables/outputs/versions.tf), a backend + provider config, and a fmt/validate/tflint/checkov CI gate with drift detection.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Terraform / OpenTofu IaC Modules

Author infrastructure that is reusable, safe to run concurrently, and gated in CI. Everything
below works identically with `terraform` and `tofu` (OpenTofu is a drop-in fork). Pick one binary
per repo and pin it. Examples use `tofu`; swap in `terraform` if that is your standard.

## When to use

Reach for this when you are creating or reviewing `.tf` code: a new module, a root that composes
modules, a backend/locking setup, or the CI checks around them. If your task is the pipeline YAML,
the image, or an imperative deploy, use the sibling skill named in `when_not_to_use`.

## Prerequisites

- **A CLI**: `tofu` (OpenTofu) or `terraform` >= 1.6. macOS without brew: grab the release binary
  from the GitHub releases page and put it on `PATH`; verify with `tofu version`.
- **Cloud credentials** for the provider you target (env vars, a named profile, or OIDC in CI).
- **A state backend that already exists**: an S3 bucket / GCS bucket / Azure storage container.
  Terraform will not create its own backend bucket (chicken-and-egg) — provision it once by hand
  or with a tiny bootstrap root that uses local state.
- Optional but recommended: `tflint`, `checkov` (`pip3 install --user checkov`), `pre-commit`.

## Module anatomy

A module is just a directory of `.tf` files. Keep every module to a single clear responsibility and
split these four files — do not cram everything into one `main.tf`.

`versions.tf` — pin the CLI and every provider. Unpinned providers are the #1 cause of "works on
my machine" drift.

```hcl
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"   # allow patch/minor, block major bumps
    }
  }
}
```

`variables.tf` — type EVERYTHING, add descriptions, and validate at the boundary.

```hcl
variable "name" {
  description = "Name prefix for all resources in this module."
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,30}$", var.name))
    error_message = "name must be lowercase alphanumeric/hyphen, 2-31 chars, starting with a letter."
  }
}

variable "tags" {
  description = "Tags merged onto every taggable resource."
  type        = map(string)
  default     = {}
}
```

`main.tf` — the resources. Prefer `for_each` (stable keys) over `count` (index churn causes
destroy/recreate when a list element is removed).

```hcl
locals {
  common_tags = merge(var.tags, { ManagedBy = "opentofu", Module = "example" })
}

resource "aws_s3_bucket" "this" {
  bucket = "${var.name}-assets"
  tags   = local.common_tags
}
```

`outputs.tf` — expose IDs/ARNs callers need; mark secrets `sensitive = true`. **Consume** the
module from a root pinned to a git tag (never a moving branch):

```hcl
module "assets" {
  source = "git::https://github.com/org/tf-modules.git//s3-bucket?ref=v1.4.0"
  name   = "acme-prod"
  tags   = { Environment = "prod", Team = "platform" }
}
```

## Remote state with locking

Local state does not survive a laptop and offers no concurrency protection. Use a remote backend
with locking so two `apply`s can never corrupt state.

**AWS S3 with native lockfile** (OpenTofu 1.10+ / Terraform 1.11+). This replaces the old
DynamoDB-table requirement — locking now uses an S3 conditional-write lockfile, no extra table:

```hcl
terraform {
  backend "s3" {
    bucket       = "acme-tfstate"
    key          = "prod/network/terraform.tfstate"
    region       = "eu-west-1"
    encrypt      = true            # server-side encryption of the state object
    use_lockfile = true            # native S3 lock — no DynamoDB needed
  }
}
```

On older CLIs, or if you prefer it, DynamoDB locking is still fully supported and not deprecated:
add `dynamodb_table = "acme-tf-locks"` (a table with primary key `LockID`). You can run both keys
at once during a migration, then drop `dynamodb_table`.

Other backends: **GCS** (`backend "gcs"` — locking is automatic via the object generation),
**azurerm** (`backend "azurerm"` — uses blob leases automatically). Never commit `*.tfstate` or
`*.tfvars` with secrets; state contains plaintext secrets by design.

Pass backend values that vary per environment at init time instead of hardcoding:

```bash
tofu init -backend-config=backend/prod.hcl
```

## Recipes

### Format, validate, and lint locally

```bash
tofu fmt -recursive            # rewrite files to canonical style
tofu fmt -check -recursive     # CI mode: non-zero exit if anything is unformatted
tofu init -backend=false       # init providers WITHOUT touching remote state (validate-only)
tofu validate                  # type/reference check — needs providers, no cloud creds
tflint --recursive             # provider-aware lint: deprecated args, bad instance types
```

`init -backend=false` is the trick for `validate` in CI: it installs providers so validation can
resolve schemas without any cloud credentials or state access.

### Plan and apply safely

```bash
tofu plan -out=tfplan          # write the plan to a file
tofu apply tfplan              # apply EXACTLY that reviewed plan (no re-plan surprise)
```

Applying a saved plan file guarantees what you reviewed is what runs. Never `apply -auto-approve`
against prod from a laptop.

### Drift detection (scheduled or PR check)

`plan -detailed-exitcode` gives three exit codes: `0` = no changes, `1` = error, `2` = drift/changes.
Use it to fail a nightly job when reality has diverged from state:

```bash
tofu plan -detailed-exitcode -lock=false -input=false
code=$?
if [ "$code" -eq 2 ]; then
  echo "::warning::Infrastructure drift detected"; exit 1
elif [ "$code" -eq 1 ]; then
  echo "plan errored"; exit 1
fi
echo "no drift"
```

`-lock=false` is safe for read-only drift checks and avoids blocking real applies. Do NOT use
`-lock=false` for an actual apply.

### Security + policy scan with Checkov

```bash
checkov -d .                                   # scan all .tf in the tree
checkov -d modules/vpc --framework terraform   # one module, terraform only
checkov -d . --skip-check CKV_AWS_18           # suppress a specific check by ID
checkov -d . --compact --quiet                 # CI-friendly: failures only, no ASCII art
checkov -d . -o sarif --output-file-path .     # SARIF for GitHub code scanning upload
```

Scan the **plan**, not just source, to catch issues that only appear after variables/modules
expand (interpolated values, computed names):

```bash
tofu plan -out=tfplan && tofu show -json tfplan > tfplan.json
checkov -f tfplan.json
```

Suppress a finding inline (with a reason) when a control is intentionally not applicable:

```hcl
resource "aws_s3_bucket" "logs" {
  # checkov:skip=CKV_AWS_18:Access logging bucket cannot log to itself
  bucket = "acme-access-logs"
}
```

### The CI gate (order matters)

Run cheap/fast checks first so failures surface quickly: `fmt -check` → `init -backend=false` →
`validate` → `tflint` → `checkov`. Only after all pass does a plan run against real state. See the
`github-actions-pipelines` skill for the workflow YAML, OIDC auth, and caching.

### pre-commit hook (local safety net)

Add `antonbabenko/pre-commit-terraform` to `.pre-commit-config.yaml` with the `terraform_fmt`,
`terraform_validate`, `terraform_tflint`, and `terraform_checkov` hooks, then `pre-commit install`.
This catches unformatted/invalid code before it ever reaches CI.

## Verify

```bash
tofu version                                   # confirm the pinned binary
tofu fmt -check -recursive && echo FMT_OK      # exits 0 only if all files canonical
tofu init -backend=false && tofu validate      # config is internally consistent
tofu plan -detailed-exitcode || echo "exit=$? (2 means changes/drift)"
checkov -d . --compact --quiet; echo "checkov exit=$?"   # 0 = all passed
```

A green run: `fmt -check` exits 0, `validate` prints "Success!", the plan you intend shows the
expected resource count, and Checkov reports 0 failed checks (or only explicitly-skipped ones).

## Pitfalls

- **Unpinned providers/modules** — always pin `required_providers` versions and pin module `?ref=`
  to a tag. A floating `main` will silently change your infra on the next `init -upgrade`.
- **`count` for collections that change** — removing a middle element renumbers indexes and
  destroys/recreates unrelated resources. Use `for_each` with stable string keys.
- **Committing state or secret tfvars** — `.tfstate` and secret `*.tfvars` hold plaintext secrets.
  Gitignore them; keep state remote and encrypted.
- **`apply -auto-approve` in prod from a laptop** — apply a reviewed saved plan file (`apply tfplan`)
  and gate real applies behind CI with OIDC, not long-lived keys.
- **Skipping `init -backend=false` before `validate` in CI** — `validate` needs provider schemas;
  without providers installed it errors, tempting people to give CI needless cloud/state access.
- **DynamoDB assumed mandatory** — on current CLIs `use_lockfile = true` gives native S3 locking;
  you no longer need a lock table. Don't add infra you don't need.
- **Running Checkov only on source** — some misconfigs appear only after interpolation, so also
  scan the JSON plan (`checkov -f tfplan.json`).
- **`-lock=false` on a real apply** — fine for read-only drift checks only; on apply it invites
  concurrent-write state corruption.
