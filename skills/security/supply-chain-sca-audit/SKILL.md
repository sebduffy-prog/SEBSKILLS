---
name: supply-chain-sca-audit
category: security
description: >-
  Audit a repo's dependency supply chain end-to-end. Generate a CycloneDX/SPDX SBOM with
  Syft, scan it with OSV-Scanner (reachability / call analysis) and Grype (EPSS + KEV
  prioritization), filter false positives with OpenVEX, then emit a minimal-bump upgrade
  plan via OSV-Scanner guided remediation. Trigger on "SBOM", "SCA", "dependency scan",
  "CVE in a lockfile", "reachable vulnerability", "supply-chain audit", or a failing
  vuln gate in CI. Defensive, authorised-use only.
when_to_use:
  - You need an SBOM (CycloneDX or SPDX) for a repo, container image, or release artifact
  - A lockfile / image is flagged for CVEs and you must know which are actually reachable
  - You want a prioritized, minimal-version-bump remediation plan instead of a wall of CVEs
  - You are wiring a dependency-vulnerability gate into CI and want low false positives
  - Auditors ask for an SBOM plus a VEX statement explaining non-exploitable findings
when_not_to_use:
  - Hunting hardcoded secrets in the tree — use secrets-hygiene-and-remediation instead
  - Static analysis of your own first-party source for bugs — use sast-semgrep-opengrep
  - Hardening a Dockerfile / IaC config rather than its dependencies — use container-iac-hardening
  - Redacting PII from data — use pii-redaction-presidio
keywords:
  - sbom
  - sca
  - osv-scanner
  - grype
  - syft
  - cyclonedx
  - spdx
  - vex
  - openvex
  - reachability
  - call-analysis
  - dependency-audit
  - cve
  - epss
  - supply-chain
  - guided-remediation
similar_to:
  - secrets-hygiene-and-remediation
  - sast-semgrep-opengrep
  - container-iac-hardening
  - pii-redaction-presidio
  - llm-red-team
inputs_needed: A repo path with lockfiles (or a container image / prebuilt SBOM); network access to osv.dev + the vuln DB; optional list of accepted false-positive CVEs for VEX.
produces: An SBOM (sbom.cdx.json / sbom.spdx.json), combined SARIF + JSON vuln reports, an OpenVEX doc, and a ranked minimal-bump upgrade plan.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Supply-Chain SCA Audit

Two-scanner dependency audit: **Syft** builds the SBOM, **OSV-Scanner** adds reachability
(call analysis) against osv.dev, **Grype** adds EPSS/KEV risk ranking against the Anchore
DB, **OpenVEX** suppresses proven false positives, and **OSV-Scanner `fix`** computes the
smallest version bumps that clear real findings. Use two scanners because their DBs and
matching heuristics differ — the intersection is your high-confidence set.

## When to use

Reach for this when you have a checked-out repo (or an image) and need to answer: *what
vulnerable dependencies do we ship, which are actually reachable, and what is the minimum
upgrade that fixes them?* This is defensive tooling — run it only on code/images you are
authorised to audit.

## Prerequisites

All three tools are single Go binaries — no brew needed. Install to a user bin dir (no
sudo). macOS `python3` here is 3.9; nothing below needs Python.

```bash
mkdir -p "$HOME/.local/bin"; export PATH="$HOME/.local/bin:$PATH"
curl -sSfL https://get.anchore.io/syft  | sh -s -- -b "$HOME/.local/bin"
curl -sSfL https://get.anchore.io/grype | sh -s -- -b "$HOME/.local/bin"
# OSV-Scanner: grab the matching darwin binary from releases (v2+ ships `scan source`)
curl -sSfL -o "$HOME/.local/bin/osv-scanner" \
  "https://github.com/google/osv-scanner/releases/latest/download/osv-scanner_darwin_$(uname -m | sed 's/x86_64/amd64/')"
chmod +x "$HOME/.local/bin/osv-scanner"
# Optional: vexctl to author OpenVEX statements
go install github.com/openvex/vexctl@latest 2>/dev/null || echo "vexctl needs Go; hand-write VEX below if absent"

syft version && grype version && osv-scanner --version
grype db update   # refresh the Anchore vuln DB before first real scan
```

Reachability (call analysis) is strongest for **Go** (on by default) and **Rust**; Java
JAR reachability is newer/partial; most other ecosystems get dependency-level matching
only. Do not claim reachability for a language the scanner doesn't analyse.

## Recipes

### 1. Generate the SBOM (source of truth for both scanners)

```bash
# From a repo directory — emit both CycloneDX and SPDX
syft dir:. -o cyclonedx-json=sbom.cdx.json -o spdx-json=sbom.spdx.json
# From a container image instead
syft docker:myorg/app:1.4.2 -o cyclonedx-json=sbom.cdx.json
```

Scan the SBOM, not the tree, so both scanners judge the *same* component set. Keep the
`.cdx.json` / `.spdx.json` suffixes — OSV-Scanner auto-detects SBOMs by filename.

### 2. OSV-Scanner — reachability + SARIF

```bash
# Scan the source dir with call analysis for ALL supported languages
osv-scanner scan source -r . \
  --call-analysis=all \
  --format sarif > osv.sarif.json
# ...or scan the SBOM directly (auto-detected by the .cdx.json name)
osv-scanner --sbom=sbom.cdx.json --format json > osv.json
```

`--call-analysis=all` turns on reachability everywhere it's supported; Go is on by
default, disable it with `--no-call-analysis=go` if it's noisy. In the SARIF/JSON, a
finding tagged as reached/called is real priority; an unreached one on a non-analysed
language is *unknown*, not *safe*.

### 3. Grype — EPSS + KEV prioritization, gate on fixables

```bash
grype sbom:sbom.cdx.json \
  -o table \
  -o json=grype.json \
  --only-fixed \
  --fail-on high
```

`--only-fixed` hides CVEs with no upstream fix (nothing to bump), and `--fail-on high`
sets the CI exit code. Grype ranks with EPSS (exploit probability) and CISA KEV (known
exploited) — a KEV hit outranks a nominally-higher CVSS with near-zero EPSS.

### 4. OpenVEX — suppress proven false positives

Author a VEX statement for each finding you've confirmed is not exploitable (e.g. vulnerable
code path is unreachable, or the component is build-only):

```bash
vexctl create \
  --product "pkg:oci/app@1.4.2" \
  --vuln    "CVE-2024-XXXXX" \
  --status  "not_affected" \
  --justification "vulnerable_code_not_in_execute_path" \
  --file vex.openvex.json
```

No `vexctl`? A minimal hand-written OpenVEX doc is valid:

```json
{
  "@context": "https://openvex.dev/ns/v0.2.0",
  "@id": "https://myorg/vex/app-2026-07-09",
  "author": "seb.duffy@vccp.com",
  "timestamp": "2026-07-09T00:00:00Z",
  "statements": [{
    "vulnerability": { "name": "CVE-2024-XXXXX" },
    "products": [{ "@id": "pkg:oci/app@1.4.2" }],
    "status": "not_affected",
    "justification": "vulnerable_code_not_in_execute_path"
  }]
}
```

Re-run Grype with the VEX applied — `not_affected` / `fixed` statements are filtered out:

```bash
grype sbom:sbom.cdx.json --vex vex.openvex.json --fail-on high -o table
```

Justification MUST be one of the OpenVEX enum values (`component_not_present`,
`vulnerable_code_not_present`, `vulnerable_code_not_in_execute_path`,
`vulnerable_code_cannot_be_controlled_by_adversary`, `inline_mitigations_already_exist`).
Never file VEX to silence a finding you haven't actually investigated.

### 5. Minimal-bump upgrade plan (guided remediation)

```bash
# In-place: smallest lockfile bumps that clear findings at/above severity 5 (CVSS), skip dev deps
osv-scanner fix \
  --strategy=in-place \
  --min-severity=5 \
  --ignore-dev \
  -L package-lock.json

# Relax manifest constraints to reach fixed versions with the least churn (npm/etc.)
osv-scanner fix --strategy=relax -M package.json -L package-lock.json
```

`in-place` bumps only the resolved versions in the lockfile (least churn); `relax` widens
manifest ranges when a fix needs a newer allowed version. `--min-severity` and
`--ignore-dev` keep the plan to what matters. Present the diff it proposes as the upgrade
plan — do not apply blindly; test after bumping.

## Verify

```bash
test -s sbom.cdx.json && echo "SBOM has content" || echo "FAIL: empty SBOM"
python3 -c "import json,sys; d=json.load(open('grype.json')); \
  print('grype matches:', len(d.get('matches', [])))"
python3 -c "import json; d=json.load(open('osv.json')); \
  print('osv result groups:', sum(len(r.get('packages',[])) for r in d.get('results',[])))"
# Gate check: non-zero exit from grype/osv-scanner == findings at/above threshold
grype sbom:sbom.cdx.json --fail-on high -q; echo "grype gate exit=$?"
```

A clean run: SBOM non-empty, both JSON reports parse, and the gate exit code is `0` after
VEX is applied. Cross-check that a CVE flagged by *both* scanners survives VEX — that's
your must-fix list.

## Pitfalls

- **Scanning the tree AND the SBOM gives different counts.** Pick one input (prefer the
  SBOM) so both scanners see identical components; otherwise you'll chase phantom deltas.
- **Unreached ≠ safe.** Call analysis only covers some languages. Absence of a "reached"
  tag on a Python/JS finding means *not analysed*, not *not exploitable*.
- **Stale DBs cause false clears.** Run `grype db update` and let OSV-Scanner hit osv.dev
  (or pre-cache with `--offline-vulnerabilities --download-offline-databases`) before
  trusting a zero-finding result.
- **`--only-fixed` hides real risk.** Great for a bump plan, dangerous as your only view —
  a critical CVE with no fix still needs a mitigation decision.
- **VEX is an assertion of fact.** A `not_affected` statement is auditable; filing one to
  mute noise you didn't investigate is how real CVEs ship to prod.
- **`osv-scanner fix` can propose breaking majors.** Cap it (`--max-depth`, review the
  diff) and run the test suite before committing any bump.
- **`sudo` install prompts.** The Anchore scripts default to `/usr/local/bin`; the `-b
  "$HOME/.local/bin"` form above avoids sudo on this Mac.
