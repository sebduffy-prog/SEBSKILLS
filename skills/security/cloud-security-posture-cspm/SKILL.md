---
name: cloud-security-posture-cspm
category: security
description: >
  Audit a LIVE cloud account (AWS, Azure, GCP, Kubernetes) for misconfigurations against CIS,
  NIST, PCI-DSS, SOC2 and friends using Prowler and ScoutSuite. Use when someone asks "is our
  AWS/Azure/GCP secure", needs a CIS benchmark score, a CSPM audit, a public-bucket / open-SG /
  IAM sweep, or an evidence pack for an auditor. Runs read-only assessments, ranks FAIL findings
  by severity, and exports CSV/JSON-OCSF/HTML. Defensive, read-only, authorised accounts only.
when_to_use:
  - Auditing a live AWS / Azure / GCP / Kubernetes account against CIS or another benchmark
  - Producing a compliance score or auditor evidence pack (PCI-DSS, SOC2, HIPAA, NIST, ISO 27001)
  - Sweeping the estate for public S3 buckets, open security groups, over-broad IAM, unencrypted volumes
  - Ranking cloud misconfigurations by severity and service to build a remediation backlog
  - Re-scanning after fixes to confirm findings closed, or diffing against a prior baseline
  - Wiring a scheduled read-only posture scan into CI/CD or a cron job
when_not_to_use:
  - Scanning Terraform / CloudFormation / k8s YAML files (code, not a live estate) — use container-iac-hardening
  - Enforcing OPA/Kyverno/Gatekeeper admission or Rego policy on manifests — use policy-as-code-opa-kyverno
  - Finding hardcoded cloud keys in a repo or git history — use secrets-hygiene-and-remediation
  - Auditing third-party package/dependency CVEs and licences — use supply-chain-sca-audit
  - Active exploitation / pen-testing of cloud infra — out of scope; this is read-only assessment
keywords:
  - cspm
  - prowler
  - scoutsuite
  - cis-benchmark
  - aws
  - azure
  - gcp
  - kubernetes
  - misconfiguration
  - compliance
  - iam
  - s3-public
  - security-group
  - posture
  - ocsf
  - cloud-audit
similar_to:
  - container-iac-hardening
  - policy-as-code-opa-kyverno
  - supply-chain-sca-audit
  - secrets-hygiene-and-remediation
inputs_needed: Read-only credentials for the target cloud (AWS profile/role with SecurityAudit, Azure reader+ app, GCP viewer SA, or a kubeconfig). Provider name and optionally a compliance framework key.
produces: Ranked FAIL findings (CSV / JSON-OCSF / HTML), a per-framework compliance score, a severity+service remediation backlog, and an optional baseline for diffing re-scans.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Cloud Security Posture Management (CSPM)

Point a scanner at a **live** cloud account and get back every misconfiguration measured against
a benchmark (CIS, NIST, PCI-DSS, SOC2, HIPAA, ISO 27001…). Two tools cover the ground:

- **Prowler** — deepest AWS coverage plus Azure/GCP/Kubernetes; per-check and per-framework
  compliance output. This is the primary workhorse. Apache-2.0.
- **ScoutSuite** — fast multi-cloud snapshot rendered as a browsable HTML report. Good for a
  quick "show me the estate" pass. GPL-2.0.

This is an **authorised, read-only** assessment. Use credentials scoped to audit/read roles and
only against accounts you own or are engaged to test.

## When to use

Someone asks "is our AWS secure?", "what's our CIS score?", "find public buckets / open ports",
or an auditor wants an evidence pack. If the target is a **running account**, you're in the right
place. If the target is Terraform/YAML **files**, that's `container-iac-hardening` /
`policy-as-code-opa-kyverno` instead — code checks, not the estate.

## Prerequisites

- **Python** 3.10–3.12 (Prowler requires `>=3.10,<3.13`). macOS system `python3` is 3.9 — make a
  venv with a newer Python (e.g. `python3.11 -m venv .venv`) or use `pipx`/Docker.
- **Cloud read credentials**, least-privilege:
  - AWS: a profile/role with the AWS-managed `SecurityAudit` (and `ViewOnlyAccess`) policy.
  - Azure: an app registration / logged-in principal with `Reader` + `Security Reader`.
  - GCP: a service account with `roles/viewer` (+ `roles/iam.securityReviewer`).
  - Kubernetes: a `kubeconfig` context with read access.
- Never hardcode keys. Use the provider's normal auth (`aws sso login`, `az login`,
  `gcloud auth`, env vars, or an assumed role) — Prowler/ScoutSuite read the ambient session.

## Recipes

### 1. Install

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install prowler          # console command: `prowler`
pip install scoutsuite       # console command: `scout`
prowler -v && scout --help | head -1
```

No local Python 3.10+? Run Prowler containerised (reads your mounted creds):

```bash
docker run -v ~/.aws:/home/prowler/.aws prowlercloud/prowler:stable aws
```

### 2. Full AWS posture scan (all checks)

```bash
aws sso login --profile audit        # or export AWS_PROFILE / assume a role first
prowler aws --profile audit \
  --output-formats csv json-ocsf html \
  --output-directory ./cspm-out
```

Prowler runs read-only, prints a live PASS/FAIL/MANUAL tally, and writes timestamped files to
`./cspm-out/`. Scope it down when you only care about part of the estate:

```bash
prowler aws --services s3 iam ec2 --region eu-west-1 --profile audit   # by service + region
prowler aws --severity critical high                                   # only the loud stuff
prowler aws --check s3_bucket_public_access                            # a single check
```

### 3. Score against a compliance framework (CIS et al.)

Discover the exact framework keys first — they are versioned (e.g. `cis_3.0_aws`), so don't guess:

```bash
prowler aws --list-compliance                       # all framework keys for the provider
prowler aws --list-compliance-requirements cis_3.0_aws
```

Then scan against one and emit the compliance report:

```bash
prowler aws --compliance cis_3.0_aws \
  --output-formats csv html --output-directory ./cspm-out
```

Prowler writes a dedicated `compliance/` CSV mapping each requirement to PASS/FAIL — that CSV is
your auditor evidence and your score denominator. Same pattern for `pci_dss`, `soc2`, `hipaa`,
`nist_800_53`, `iso27001` — use whatever `--list-compliance` prints.

### 4. Azure / GCP / Kubernetes

```bash
az login && prowler azure --az-cli-auth                 # Azure via logged-in CLI
gcloud auth application-default login && prowler gcp     # GCP via ADC
prowler kubernetes --kubeconfig-file ~/.kube/config      # in-cluster or via kubeconfig
```

### 5. ScoutSuite HTML snapshot (quick browsable view)

```bash
scout aws   --profile audit          # writes scoutsuite-report/scoutsuite_results/... + HTML
scout azure --cli
scout gcp   --user-account
```

Open `scoutsuite-report/index.html` (or the printed path) in a browser to click through services,
dashboards, and flagged findings. Great for triage; use Prowler for the machine-readable evidence.

### 6. Rank the failures into a backlog

Feed Prowler's OCSF JSON to the bundled helper for a severity-ranked, per-service summary:

```bash
python3 scripts/prowler_fails.py ./cspm-out/prowler-output-*.ocsf.json
python3 scripts/prowler_fails.py ./cspm-out/*.ocsf.json --severity critical,high
```

It prints FAIL counts by severity, the noisiest services, and every Critical/High title — the
raw material for a remediation ticket list. (Schema-tolerant; it also reads from stdin.)

### 7. Baseline and re-scan (prove fixes landed)

Prowler supports muting known/accepted findings via an allowlist so a re-scan only surfaces what's
new or unfixed:

```bash
prowler aws --mutelist-file mutelist.yaml --profile audit    # suppress accepted findings
```

Keep the first run's CSV as the baseline, fix the Criticals, re-run, and diff the FAIL counts to
confirm closure.

## Verify

- `prowler -v` prints a version and `scout --help` prints usage → tools installed correctly.
- After a scan, `./cspm-out/` (Prowler) and `scoutsuite-report/` (ScoutSuite) contain fresh
  timestamped files; Prowler's stdout shows a non-zero total of checks executed.
- Smoke-test the helper offline (no cloud creds needed):

  ```bash
  printf '[{"status_code":"FAIL","severity":"critical","finding_info":{"title":"public bucket"},"resources":[{"group":{"name":"s3"}}]}]' \
    | python3 scripts/prowler_fails.py -
  ```

  → prints one Critical S3 finding.
- Sanity-check auth before a long scan: `prowler aws --list-checks` succeeds without a credentials
  error, confirming the session is valid and read access works.

## Pitfalls

- **Python 3.9 (macOS default) will not install Prowler.** It needs `>=3.10,<3.13`. Use a venv
  with a newer interpreter, `pipx`, or the Docker image — don't fight the system Python.
- **Compliance keys are versioned and change over time.** Never hardcode `cis_2.0_aws` from a
  blog; run `--list-compliance` and copy the exact current key, or the scan errors out.
- **FAIL ≠ vulnerability.** A finding is a policy deviation; some are accepted risk. Triage by
  severity, mute accepted items in the mutelist — don't dump 800 raw findings on a team.
- **Scope your credentials, not just your flags.** Read-only IAM roles are the real safety net; a
  scanner with write creds is a liability even though it only reads.
- **Big accounts are slow and rate-limited.** Narrow with `--services` / `--region` /
  `--severity` for iterative work; save the full sweep for scheduled runs.
- **These tools assess a live estate — they do not check your IaC.** A clean Prowler run says
  nothing about the Terraform in the PR that's about to change it. Gate the code with
  `container-iac-hardening` / `policy-as-code-opa-kyverno` *and* audit the estate here.
- **ScoutSuite and Prowler are complementary, not redundant.** Prowler = evidence + compliance
  scoring; ScoutSuite = fast visual triage. Reach for the one that fits the ask.
- **Authorisation only.** Assess accounts you own or are contracted to test. This skill is
  strictly read-only posture assessment — no exploitation.
