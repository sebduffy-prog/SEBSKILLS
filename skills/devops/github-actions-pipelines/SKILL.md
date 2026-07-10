---
name: github-actions-pipelines
category: devops
description: >-
  Build robust, secure GitHub Actions CI/CD — matrix builds, dependency caching,
  reusable + composite workflows, OIDC cloud auth (no long-lived secrets), least-privilege
  `permissions`, concurrency cancellation, and SHA-pinned actions hardened against
  supply-chain attacks with step-security/harden-runner egress control. Reach for this the
  moment someone says "add CI", "write a GitHub Actions workflow", "cache my build",
  "deploy from Actions to AWS/GCP", "pin our actions", or "our pipeline got compromised".
when_to_use:
  - Authoring a new CI or CD workflow (build, test, lint, release, deploy)
  - Adding a language/OS matrix or dependency caching to speed a slow pipeline
  - Replacing stored cloud secrets with keyless OIDC role assumption (AWS/GCP/Azure)
  - Hardening a repo against the tj-actions / supply-chain style attacks (SHA-pin + egress audit)
  - Extracting shared steps into a reusable (`workflow_call`) or composite action
  - Tightening `GITHUB_TOKEN` permissions and cancelling superseded runs on new pushes
when_not_to_use:
  - Writing the Dockerfile the pipeline builds — use dockerfile-and-compose-authoring
  - Provisioning the cloud role/OIDC trust policy itself — use terraform-iac-modules
  - Handling a live production outage the pipeline shipped — use incident-response-and-postmortem
  - Deep SAST rule authoring for the scan step — use sast-semgrep-opengrep (security)
  - GitLab CI, CircleCI, Jenkins — this skill is GitHub Actions only
keywords:
  - github-actions
  - ci-cd
  - workflow
  - matrix
  - caching
  - reusable-workflow
  - composite-action
  - oidc
  - harden-runner
  - sha-pinning
  - supply-chain
  - permissions
  - concurrency
  - gha
  - deploy
similar_to:
  - dockerfile-and-compose-authoring
  - terraform-iac-modules
  - incident-response-and-postmortem
inputs_needed: Repo with a build/test command; runtime (node/python/go/etc); for CD a cloud OIDC role ARN + region.
produces: Hardened .github/workflows/*.yml (CI + optional CD), pinned action SHAs, and a reusable/composite workflow where shared.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# GitHub Actions Pipelines

Ship CI/CD that is fast, least-privilege, and hard to poison. Every recipe below is
grounded against current (2026) action versions and the supply-chain hardening pattern
that the tj-actions/changed-files compromise made non-negotiable.

## When to use

Use when creating or hardening a `.github/workflows/*.yml` file — CI (build/test/lint), CD
(deploy/release), or shared building blocks (reusable/composite). If the task is the Dockerfile, the
cloud IAM trust policy, or a live incident, use the sibling skill named in the frontmatter instead.

## Prerequisites

- A GitHub repo; workflows live in `.github/workflows/`.
- **Recommended tools** (Go binaries, no brew needed): `pinact` or `frizbee` to convert `@v7` tags to
  pinned SHAs; `actionlint` to lint; `zizmor` for Actions security audit (template-injection, over-broad perms).
- For CD via OIDC: a cloud IAM role whose trust policy permits your repo's `sub` claim — creating that
  role is IaC work (terraform-iac-modules); this skill consumes the resulting role ARN.

## The non-negotiables (put these on every workflow)

1. **Pin actions to a full 40-char commit SHA**, never a tag — tags are mutable; a compromised
   maintainer can repoint `v4` at malicious code (how tj-actions/changed-files was weaponised in 2025).
   Keep a `# v7.0.0` comment so humans and Dependabot can read it.
2. **Least-privilege `permissions`** at top level (`contents: read`), widen per-job only where needed.
3. **`concurrency`** so a new push cancels the stale in-flight run.
4. **harden-runner** as the first step of each job to audit (then block) network egress — it turns a
   runner into an EDR sensor and surfaces exfiltration attempts.

## Recipe 1 — Hardened CI with matrix + caching

`.github/workflows/ci.yml`:
```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

# Least privilege at the top; jobs widen only if they must.
permissions:
  contents: read

# Cancel superseded runs on the same ref (keeps the queue short & cheap).
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false            # let every matrix leg finish so you see all failures
      matrix:
        node: [20, 22, 24]
    steps:
      # EDR for the runner. Start in audit; flip to block once you know your egress.
      - uses: step-security/harden-runner@f808768d1510423e83855289c910610ca9b43176 # v2.17.0
        with: { egress-policy: audit }
      - uses: actions/checkout@<PIN-TO-SHA> # v7.0.0  (run pinact to fill the SHA)
      - uses: actions/setup-node@<PIN-TO-SHA> # v6.4.0
        with:
          node-version: ${{ matrix.node }}
          cache: npm            # built-in dependency cache, keyed on the lockfile
      - run: npm ci             # ci (not install) → reproducible, respects the lockfile
      - run: npm test
```

`setup-node` / `setup-python` / `setup-go` have **built-in caching** via the `cache:` input —
prefer it over hand-rolling `actions/cache` for dependencies; it auto-keys on the lockfile hash.
Use `actions/cache` directly only for *non-dependency* caches (build artefacts, compiled output):

```yaml
      - uses: actions/cache@<PIN-TO-SHA> # v4.2.4
        with:
          path: ~/.cache/my-build
          key: build-${{ runner.os }}-${{ hashFiles('**/lockfile') }}
          restore-keys: |
            build-${{ runner.os }}-          # partial-match fallback → warm-start on lockfile bump
```

## Recipe 2 — Keyless deploy to AWS via OIDC (no stored secrets)

Long-lived `AWS_ACCESS_KEY_ID` secrets are the crown-jewel target. Replace them with OIDC: Actions
mints a short-lived token, AWS STS exchanges it for temporary creds. **`id-token: write` is what lets
the job request that token** — grant it only on the deploy job.

```yaml
name: Deploy
on:
  push:
    branches: [main]

permissions:
  contents: read              # top-level default stays locked down

concurrency:
  group: deploy-${{ github.ref }}
  cancel-in-progress: false   # never cancel a half-finished deploy

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production     # gate on required reviewers / wait timer
    permissions:
      id-token: write           # REQUIRED to fetch the OIDC token
      contents: read
    steps:
      - uses: step-security/harden-runner@f808768d1510423e83855289c910610ca9b43176 # v2.17.0
        with: { egress-policy: audit }
      - uses: actions/checkout@<PIN-TO-SHA> # v7.0.0
      - uses: aws-actions/configure-aws-credentials@<PIN-TO-SHA> # v4.3.1
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-deploy
          aws-region: eu-west-2
          # no access-key-id/secret — the OIDC token IS the credential
      - run: aws sts get-caller-identity   # prove the role assumed
      - run: ./deploy.sh
```

The role's trust policy must scope the `token.actions.githubusercontent.com:sub` condition to your
repo/branch/environment (e.g. `repo:org/name:ref:refs/heads/main` or `repo:org/name:environment:production`)
— created in Terraform, not here. GCP uses `google-github-actions/auth` (Workload Identity Federation),
Azure `azure/login` (pass `client-id`/`tenant-id`/`subscription-id` and OIDC is used automatically — no `enable-oidc` input exists) — both follow the identical `id-token: write` pattern.

## Recipe 3 — Reusable workflow (DRY across repos/jobs)

Callee — `.github/workflows/reusable-test.yml` (declare its own `inputs`, `secrets`, `permissions`):
```yaml
on:
  workflow_call:
    inputs:
      node-version: { type: string, default: "22" }
    secrets:
      NPM_TOKEN: { required: false }
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: step-security/harden-runner@f808768d1510423e83855289c910610ca9b43176 # v2.17.0
        with: { egress-policy: audit }
      - uses: actions/checkout@<PIN-TO-SHA> # v7.0.0
      - uses: actions/setup-node@<PIN-TO-SHA> # v6.4.0
        with: { node-version: "${{ inputs.node-version }}", cache: npm }
      - run: npm ci && npm test
```

Caller:
```yaml
jobs:
  ci:
    uses: ./.github/workflows/reusable-test.yml   # or org/repo/.github/workflows/x.yml@<sha>
    with: { node-version: "24" }
    secrets: inherit
```

**Reusable workflow vs composite action:** a *reusable workflow* (`workflow_call`) shares whole jobs
(own runner, own `permissions`, can call other jobs); a *composite action* (`action.yml`,
`runs.using: composite`) bundles a **sequence of steps** inside an existing job — lighter, but no
job-level `permissions`/`strategy`.

## Pinning: fill every `<PIN-TO-SHA>` correctly

Author with tags, then mechanically pin — do not copy SHAs by hand:
```bash
pinact run                                                       # rewrites every action to SHA + comment
frizbee actions .github/workflows/                               # equivalent alternative
gh api repos/actions/checkout/git/ref/tags/v7.0.0 --jq .object.sha   # resolve one by hand
```

Then let **Dependabot** keep the SHAs current (add `.github/dependabot.yml` with
`package-ecosystem: github-actions`, `directory: /`, `schedule: { interval: weekly }`). Pin
**first-party `actions/*`** too — GitHub's own org is not immune, and uniform pinning means one rule.

## Verify

```bash
actionlint                                                      # structure, shell, expressions
zizmor .github/workflows/                                       # template-injection, over-broad perms, unpinned
# No mutable refs left — this must print nothing:
grep -rnE 'uses:.*@(v[0-9]|main|master|latest)\b' .github/workflows/ || echo "OK: all pinned"
# YAML valid:
for f in .github/workflows/*.yml; do python3 -c "import yaml,sys;yaml.safe_load(open(sys.argv[1]))" "$f" && echo "OK $f"; done
```

A green pipeline is not the bar — a *pinned, least-privilege, egress-audited* one is. After the first
`audit` run, open the harden-runner job summary, read the recorded outbound connections, then switch to
`egress-policy: block` with an explicit `allowed-endpoints` list.

## Pitfalls

- **Tags are not immutable.** `@v4` / `@main` = trusting a maintainer's account forever; one compromised
  token repoints the tag and every consumer runs the payload on the next build. Pin SHAs.
- **`pull_request_target` + checking out the PR head = RCE.** That trigger runs with repo secrets, so
  checking out untrusted PR code under it hands attackers your secrets. Use plain `pull_request` for forks;
  never `actions/checkout` the PR `head.sha` under `pull_request_target`.
- **Template injection.** Never interpolate `${{ github.event.* }}` (PR title, branch, issue body) into
  a `run:` shell — attackers control those. Pass via `env:` and reference `"$VAR"` so the shell, not the
  expression engine, handles the value.
- **`secrets: inherit` over-shares** — it forwards *all* caller secrets to a reusable workflow. Pass
  named secrets explicitly unless you genuinely need all of them.
- **Forgetting `permissions` = write-all.** Without a top-level block, older repos default `GITHUB_TOKEN`
  to broad read-write. Always set `contents: read` at the top and widen per-job.
- **`cancel-in-progress: true` on deploy jobs** can kill a half-applied deploy mid-flight — use `false`
  for CD, `true` only for idempotent CI. And `fail-fast: true` (the matrix default) cancels sibling legs
  on first failure, hiding the others; set `fail-fast: false` in CI. Never cache credentials or sensitive
  build output — `actions/cache` is readable by other runs on the repo.
