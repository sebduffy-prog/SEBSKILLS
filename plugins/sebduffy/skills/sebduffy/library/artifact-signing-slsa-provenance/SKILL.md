---
name: artifact-signing-slsa-provenance
category: security
description: >-
  Prove build integrity, not just scan for CVEs. Keyless-sign container images and release
  artifacts with Cosign + Sigstore (Fulcio/Rekor, no long-lived keys), attach SLSA build
  provenance and an SBOM as in-toto attestations, then enforce a verify gate in CI and at
  admission that FAILS closed on identity/issuer/digest mismatch. Trigger on "sign the
  image", "cosign", "sigstore", "keyless signing", "SLSA provenance", "build attestation",
  "SBOM attestation", "supply-chain integrity gate", "gh attestation", or "verify what we
  ship". Defensive, authorised-use only — sign artifacts you are entitled to sign.
when_to_use:
  - You publish container images or release binaries and must prove where/how they were built
  - You want tamper-evident signatures without managing private keys (keyless via OIDC)
  - You need to attach and later verify SLSA provenance and an SBOM as attestations
  - You are wiring a CI or Kubernetes admission gate that rejects unsigned/untrusted artifacts
  - Auditors or a customer ask for cryptographic proof of build origin (SLSA Level 2/3)
when_not_to_use:
  - You only need to find CVEs / build an SBOM, not prove integrity — use supply-chain-sca-audit
  - Hunting hardcoded secrets in the tree — use secrets-hygiene-and-remediation
  - Static analysis of first-party source for bugs — use sast-semgrep-opengrep
  - Hardening a Dockerfile / IaC config itself — use container-iac-hardening
keywords:
  - cosign
  - sigstore
  - keyless-signing
  - fulcio
  - rekor
  - slsa
  - provenance
  - attestation
  - sbom
  - in-toto
  - slsa-verifier
  - gh-attestation
  - admission-control
  - supply-chain
  - oidc
  - digest-pinning
similar_to:
  - supply-chain-sca-audit
  - container-iac-hardening
  - secrets-hygiene-and-remediation
inputs_needed: >-
  A pushed container image referenced by immutable digest (registry@sha256:...) or a release
  artifact; a CI OIDC identity (GitHub Actions token, or `cosign login`/interactive OIDC);
  push/write access to the registry for storing signatures + attestations.
produces: >-
  A Cosign signature + Rekor transparency-log entry, SLSA provenance and SBOM in-toto
  attestations attached to the image, a keyless verify command/policy that fails closed, and
  a CI + admission gate config (verify-attestation / slsa-verifier / gh attestation / policy-controller).
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Artifact Signing & SLSA Provenance

Signing proves **integrity and origin** — SCA only proves you scanned. This skill signs images
keyless with Sigstore, attaches SLSA provenance + an SBOM as attestations, and enforces a gate
that rejects anything not signed by the expected identity, from the expected build, at the
expected digest.

## When to use

Use when you must answer "can we prove this exact artifact came from our build?" — publishing
images/binaries, satisfying a SLSA L2/L3 requirement, or wiring a fail-closed verify gate in CI
or at Kubernetes admission. For finding CVEs or generating an SBOM without proving origin, use
`supply-chain-sca-audit`.

## Prerequisites

Honest deps. macOS here has no brew; install via the Go toolchain or the release binaries.

- **cosign** — signing/attestation. `go install github.com/sigstore/cosign/v2/cmd/cosign@latest`
  (or download from the sigstore/cosign releases). `cosign version` to confirm v2.x.
- **slsa-verifier** (optional, for SLSA-generator provenance):
  `go install github.com/slsa-framework/slsa-verifier/v2/cli/slsa-verifier@v2.7.1`
- **crane** (resolve tags → immutable digests): `go install github.com/google/go-containerregistry/cmd/crane@latest`
- **syft** (SBOM) if you don't already have one — see `supply-chain-sca-audit`.
- **gh** CLI ≥ 2.49 for GitHub-native attestations (`gh attestation verify`).
- An OIDC identity: in GitHub Actions it's automatic (`id-token: write`); locally, `cosign sign`
  opens a browser for Google/GitHub/Microsoft. Public keyless uses the **public-good** Fulcio CA
  + Rekor transparency log — signer identity is recorded publicly.

CRITICAL: always operate on an **immutable digest**, never a mutable tag. A tag can be repointed
between sign and deploy (TOCTOU). Pin it:

```bash
IMAGE=ghcr.io/acme/api:1.4.0
DIGEST_REF="ghcr.io/acme/api@$(crane digest "$IMAGE")"   # ghcr.io/acme/api@sha256:...
```

## Recipes

### 1. Keyless-sign an image (no private key)

```bash
# Signs $DIGEST_REF; --yes skips the Rekor upload confirmation (required in CI).
COSIGN_EXPERIMENTAL=1 cosign sign --yes "$DIGEST_REF"
```

In CI the OIDC token identifies the workflow; interactively it opens a browser. The signature is
stored as a `sha256-...sig` tag next to the image and the entry is logged to Rekor.

### 2. Attach an SBOM as an attestation

```bash
syft "$DIGEST_REF" -o spdx-json > sbom.spdx.json
cosign attest --yes --predicate sbom.spdx.json --type spdxjson "$DIGEST_REF"
# CycloneDX instead:  --predicate sbom.cdx.json --type cyclonedx
```

An **attestation** (in-toto, DSSE-wrapped) binds the SBOM to the image digest and to your signing
identity — stronger than `cosign attach sbom`, which is unsigned and now deprecated.

### 3. Attach SLSA provenance

Two paths — pick one:

**a) GitHub-native (simplest, recommended for GH Actions).** `actions/attest-build-provenance`
generates SLSA provenance and pushes it as an attestation to the registry:

```yaml
permissions:
  id-token: write       # OIDC for keyless signing
  attestations: write   # write the attestation
  contents: read
  packages: write       # push to ghcr.io
steps:
  - uses: actions/attest-build-provenance@v4   # v4.x = wrapper over actions/attest
    with:
      subject-name: ghcr.io/acme/api
      subject-digest: sha256:${{ steps.build.outputs.digest }}
      push-to-registry: true
```

**b) SLSA generator reusable workflow** (portable across registries, verifiable with slsa-verifier):

```yaml
permissions:
  actions: read       # detect the Actions environment
  id-token: write     # OIDC tokens for signing
  packages: write     # upload attestations
uses: slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@v2.1.0
with:
  image: ghcr.io/acme/api          # NO tag or digest here
  digest: ${{ needs.build.outputs.digest }}   # sha256:...
secrets:
  registry-username: ${{ github.actor }}
  registry-password: ${{ secrets.GITHUB_TOKEN }}
```

Or attach a hand-built predicate keyless: `cosign attest --yes --predicate provenance.json --type slsaprovenance1 "$DIGEST_REF"`.

### 4. Verify — the gate that fails closed

Keyless verification MUST pin the expected identity **and** issuer, or an attacker with any valid
Fulcio cert passes. For GitHub builds:

```bash
# Signature only
cosign verify "$DIGEST_REF" \
  --certificate-identity-regexp '^https://github.com/acme/api/\.github/workflows/.+@refs/tags/.+$' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com

# Provenance attestation, with a policy check on the predicate
cosign verify-attestation "$DIGEST_REF" \
  --type slsaprovenance \
  --certificate-identity-regexp '^https://github.com/acme/api/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --policy policy.rego
```

`--certificate-identity` (exact) or `--certificate-identity-regexp` (anchored `^…$`) is
**mandatory** — an unpinned verify is theatre. Verify SLSA-generator provenance instead with:

```bash
slsa-verifier verify-image "$DIGEST_REF" \
  --source-uri github.com/acme/api \
  --source-tag v1.4.0
```

GitHub-native attestations verify with the gh CLI (checks the attestation was signed by a
workflow in `--owner`'s repo):

```bash
gh attestation verify oci://"$DIGEST_REF" --owner acme
```

### 5. A CUE/Rego policy on the predicate (optional depth)

`--policy` lets `verify-attestation` assert facts inside the provenance, e.g. Rego requiring the
builder id and a protected source branch:

```rego
package signing
import rego.v1
deny contains msg if {
  input.predicate.builder.id != "https://github.com/acme/api/.github/workflows/release.yml@refs/tags/v1.4.0"
  msg := "unexpected builder id"
}
```

### 6. Enforce at Kubernetes admission

Fail-closed at deploy time with **Sigstore policy-controller** (or Kyverno). A `ClusterImagePolicy`
that admits only images signed by your CI identity:

```yaml
apiVersion: policy.sigstore.dev/v1beta1
kind: ClusterImagePolicy
metadata: { name: acme-signed-only }
spec:
  images:
    - glob: "ghcr.io/acme/**"
  authorities:
    - keyless:
        url: https://fulcio.sigstore.dev
        identities:
          - issuer: https://token.actions.githubusercontent.com
            subjectRegExp: "^https://github.com/acme/.+/.github/workflows/.+@refs/tags/.+$"
```

Unsigned or wrong-identity images are rejected by the webhook — no verify step to forget.

## Verify

- `cosign version` prints a v2.x version; `cosign tree "$DIGEST_REF"` lists the attached
  signature + attestation tags.
- A tampered or unsigned image makes step 4 exit **non-zero** — that non-zero is the gate. In CI,
  do not `|| true` it. Confirm the failure path locally against an unsigned test image.
- `cosign verify` output shows the certificate subject + issuer; check they match your build.
- `gh attestation verify oci://... --owner …` prints "✓ Verification succeeded!" only for a real
  attestation from that owner.

## Pitfalls

- **Unpinned identity = no security.** `cosign verify IMAGE` with no `--certificate-identity*`
  and `--certificate-oidc-issuer` passes for *any* Sigstore signature. Always pin both; anchor
  regexps with `^…$`.
- **Signing a tag, verifying a digest (or vice versa).** Sign, attest, and verify the SAME
  `@sha256:` digest end to end, or the gate silently checks the wrong bytes.
- **`cosign attach sbom` is not an attestation** — it's unsigned and deprecated. Use
  `cosign attest --type spdxjson/cyclonedx`.
- **Keyless identity is public.** Public-good Rekor logs the signer identity in a public
  transparency log. For private orgs, run a private Sigstore stack or use `--key`/KMS signing.
- **Provenance without a hardened builder isn't SLSA L3.** A self-hosted runner that lets the job
  forge its own provenance is L1-ish. Use the SLSA reusable generator or `actions/attest` on
  GitHub-hosted runners for isolation.
- **Missing OIDC permission in CI.** Keyless signing needs `id-token: write`; GitHub attestations
  also need `attestations: write`. Absent, signing fails with an OIDC/token error.
- **Rekor / Fulcio outage or air-gap.** Public-good endpoints can rate-limit or be unreachable;
  verify offline with `--offline` + a downloaded bundle and trusted root, or self-host.
- **Verifying a floating tag over time.** Re-resolve the digest before every verify; never trust a
  tag you resolved minutes ago.
