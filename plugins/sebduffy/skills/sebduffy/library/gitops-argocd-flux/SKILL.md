---
name: gitops-argocd-flux
category: devops
description: >
  Set up pull-based GitOps delivery with Argo CD or Flux — git as the single source of truth, a
  controller that continuously reconciles the cluster, drift detection and self-heal, ordered
  rollouts via sync waves (Argo) or dependsOn (Flux), and prune-on-delete. Use when moving from
  push-style `kubectl apply` / CI-deploys to declarative pull delivery, wiring App-of-Apps or
  Flux Kustomizations, or debugging why a cluster won't converge on git. Covers both tools and
  when to pick which.
when_to_use:
  - Converting a push-based pipeline (CI runs kubectl/helm apply) to pull-based GitOps
  - Bootstrapping Argo CD Applications / ApplicationSets or Flux GitRepository + Kustomization
  - Enforcing drift detection + self-heal so manual cluster edits get reverted to git
  - Ordering multi-resource rollouts (CRDs before CRs, DB before app) with sync waves or dependsOn
  - Debugging an app stuck OutOfSync / not-Ready, or a prune that deleted the wrong thing
  - Deciding between Argo CD and Flux for a new platform
when_not_to_use:
  - Authoring the workload manifests / Helm values themselves — use kubernetes-workload-deploy
  - Writing the CI YAML that builds+pushes images or updates the git tag — use github-actions-pipelines
  - Provisioning the cluster and cloud infra (VPC, node pools, IAM) — use terraform-iac-modules
  - Plain one-shot `kubectl apply` with no reconciler and no git source of truth
keywords: [gitops, argocd, fluxcd, flux, pull-based-delivery, drift-detection, self-heal, sync-waves, app-of-apps, applicationset, kustomization, reconciliation, prune, kubernetes, continuous-delivery, declarative]
similar_to: [kubernetes-workload-deploy, github-actions-pipelines, terraform-iac-modules, incident-response-and-postmortem]
inputs_needed: A Kubernetes cluster with admin kubeconfig, a git repo holding manifests/Helm/Kustomize, and a git credential (PAT or deploy key) the controller can read the repo with.
produces: A running Argo CD or Flux control plane plus committed Application/Kustomization manifests that continuously reconcile the cluster to git, with drift self-heal, ordered sync, and prune-on-delete.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# GitOps with Argo CD & Flux

Pull-based delivery inverts the CI-push model: instead of your pipeline holding cluster credentials
and running `kubectl apply`, an **in-cluster controller** watches a git repo and reconciles the
cluster toward the committed desired state — forever, on an interval, correcting drift. Git is the
source of truth; the cluster is a cache of it. CI's job shrinks to *build image → commit a new tag
to the git repo*; the controller does the deploy.

## When to use

Reach for this when the deploy step should stop living in CI. If you are still writing the Deployment
YAML, the Helm values, or the image-build pipeline, use the sibling skills in `when_not_to_use` — this
skill is only the reconciliation layer on top of them.

## Argo CD vs Flux — pick one

| | **Argo CD** | **Flux** |
|---|---|---|
| Shape | App-centric, has a UI/dashboard | Toolkit of controllers, GitOps-native, no default UI |
| Unit | `Application` CRD | `GitRepository` source + `Kustomization`/`HelmRelease` |
| Ordering | `sync-wave` annotations + hooks | `dependsOn` between Kustomizations |
| Multi-target | `ApplicationSet` generators | one Kustomization per path, or matrix via CLI/Terraform |
| Best when | teams want a visual sync view + RBAC UI | you want everything as CRDs, tight Kustomize/Helm loop |

Both are CNCF-graduated and production-grade. Do **not** run both against the same namespaces.

## Prerequisites

- **A cluster + admin kubeconfig**: `kubectl cluster-info` returns a control plane.
- **A git repo** of manifests (raw YAML, Kustomize overlays, or Helm charts) the controller can read.
- **A git credential**: a PAT (HTTPS) or an SSH deploy key. Flux `bootstrap` can create the deploy
  key for you; Argo CD needs the repo registered with `argocd repo add`.
- **CLI**: `argocd` or `flux`. macOS without brew — download the release binary from the project's
  GitHub releases page, `chmod +x`, put it on `PATH`. Verify `argocd version --client` / `flux --version`.

---

## Recipe A — Argo CD

### Install the control plane

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
# initial admin password (delete the secret after you rotate it):
argocd admin initial-password -n argocd
```

### Declare an Application (commit this to git)

`argoproj.io/v1alpha1`. The controller polls `source`, applies into `destination`, and — with
`automated` — prunes removed resources and reverts drift.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: web
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/acme/deploy.git
    targetRevision: main            # a branch, tag, or commit; pin to a tag for prod
    path: apps/web/overlays/prod    # Kustomize/Helm/raw dir inside the repo
  destination:
    server: https://kubernetes.default.svc
    namespace: web
  syncPolicy:
    automated:
      prune: true                   # delete cluster resources removed from git
      selfHeal: true                # revert manual kubectl edits back to git
    syncOptions:
      - CreateNamespace=true        # create the target namespace if absent
      - ServerSideApply=true        # avoid last-applied-config annotation bloat
```

Apply once (`kubectl apply -f web-app.yaml`), then git drives everything after.

### Ordered rollout — sync waves & hooks

Argo applies resources in ascending `sync-wave` (default `0`, negatives run first). Put CRDs/namespaces
in an earlier wave than the CRs that need them.

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-1"        # runs before wave 0
```

Run a job at a phase with a **hook** (cleaned up per its delete-policy):

```yaml
metadata:
  annotations:
    argocd.argoproj.io/hook: PreSync                 # PreSync|Sync|PostSync|SyncFail|PostDelete
    argocd.argoproj.io/hook-delete-policy: HookSucceeded
```

### Fan out with ApplicationSet

One template + a generator = many Applications (per cluster, per git folder, etc.):

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata: { name: tenants, namespace: argocd }
spec:
  generators:
    - git:
        repoURL: https://github.com/acme/deploy.git
        revision: main
        directories: [{ path: tenants/* }]
  template:
    metadata: { name: '{{path.basename}}' }
    spec:
      project: default
      source: { repoURL: https://github.com/acme/deploy.git, targetRevision: main, path: '{{path}}' }
      destination: { server: https://kubernetes.default.svc, namespace: '{{path.basename}}' }
      syncPolicy: { automated: { prune: true, selfHeal: true } }
```

### Drive & inspect

```bash
argocd app list
argocd app get web                    # health + sync status, per-resource
argocd app diff web                   # live cluster vs desired git (exit != 0 if drift)
argocd app sync web                   # force a sync now (auto-sync also runs on interval/webhook)
argocd app history web                # revisions; roll back with: argocd app rollback web <id>
```

---

## Recipe B — Flux

### Bootstrap (installs Flux AND commits it to git)

`bootstrap` is idempotent: it installs the controllers, writes their manifests into your repo under
`--path`, and creates a deploy key. Re-run it to upgrade.

```bash
export GITHUB_TOKEN=ghp_xxx          # a PAT with repo scope
flux bootstrap github \
  --owner=acme --repository=deploy \
  --branch=main --path=clusters/prod \
  --personal                          # drop --personal if the owner is an org
```

Check the toolkit is healthy: `flux check`.

### Source + Kustomization (commit these to git)

A `GitRepository` (`source.toolkit.fluxcd.io/v1`) defines *what to watch*; a `Kustomization`
(`kustomize.toolkit.fluxcd.io/v1`) defines *what to apply and how*.

```yaml
apiVersion: source.toolkit.fluxcd.io/v1
kind: GitRepository
metadata: { name: deploy, namespace: flux-system }
spec:
  interval: 1m                        # how often to poll git (webhooks make this instant)
  url: https://github.com/acme/deploy.git
  ref: { branch: main }
---
apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata: { name: web, namespace: flux-system }
spec:
  interval: 10m                       # reconcile cadence; min 60s
  sourceRef: { kind: GitRepository, name: deploy }
  path: ./apps/web/overlays/prod
  prune: true                         # garbage-collect resources removed from git
  wait: true                          # block until all applied resources are healthy
  timeout: 5m
  dependsOn:
    - { name: infra }                 # ordering: infra must be Ready before web reconciles
```

`selfHeal` is implicit in Flux — the controller reapplies on every `interval`, reverting drift.
Use `dependsOn` (not sync waves) to sequence: e.g. a `cert-manager` Kustomization before the apps
that need its CRDs.

### Drive & inspect

```bash
flux get kustomizations                        # Ready / Suspended / last applied revision
flux get sources git                           # is git fetch succeeding?
flux reconcile kustomization web --with-source # pull git NOW, then apply (skip the interval wait)
flux diff kustomization web --path ./apps/web/overlays/prod   # local build vs live cluster
flux suspend kustomization web                 # freeze reconciliation (e.g. during an incident)
flux resume kustomization web                  # unfreeze
flux logs --level=error --all-namespaces       # controller errors across the toolkit
```

## Verify

A converged GitOps setup, end to end:

```bash
# Argo CD
argocd app get web -o json | grep -E '"health"|"sync"'   # expect Healthy + Synced
argocd app diff web && echo "NO_DRIFT"                    # exits 0 when live == git

# Flux
flux get kustomizations                                   # every row Ready=True, no error
kubectl -n flux-system get kustomization web \
  -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'   # -> True
```

**Prove drift self-heal** (the whole point): edit a live resource by hand and watch it revert.

```bash
kubectl -n web scale deploy/web --replicas=99   # tamper out-of-band
# Argo (selfHeal:true) or Flux (next interval) reverts it back to the git-declared count.
kubectl -n web get deploy/web -o jsonpath='{.spec.replicas}'   # returns to the committed value
```

## Pitfalls

- **`prune: true` on a mis-scoped path** — if a Kustomization/Application points at a folder that
  suddenly matches fewer resources (a bad refactor, a moved file), prune will *delete* the ones that
  vanished from git. Review `argocd app diff` / `flux diff` before merging structural moves.
- **Committing rendered secrets to git** — GitOps means everything in the repo is the source of truth,
  including anything plaintext. Use SOPS + `sops-secret` decryption (Flux) or a Sealed Secrets / external
  secrets operator; never commit raw `Secret` data.
- **CRDs applied in the same wave as their CRs** — the CR fails ("no matches for kind"). Put CRDs in an
  earlier Argo `sync-wave` (or a `dependsOn` Kustomization) than the resources that consume them.
- **Fighting the reconciler with `kubectl edit`** — with self-heal on, manual edits are reverted within
  one interval, which looks like a "flapping" bug. To make a real change, commit to git; to intervene
  during an incident, `flux suspend` / disable Argo auto-sync first, then remember to re-enable.
- **`targetRevision: HEAD`/`main` in prod** — a moving branch means any merge auto-deploys. Pin prod
  Applications to a tag or digest and promote by bumping the ref, so rollouts are explicit and revertible.
- **Running Argo CD and Flux over the same namespaces** — two controllers reconciling the same objects
  will thrash. Split by namespace/cluster, or standardise on one.
- **Interval set too aggressively** — a 5s git poll hammers the API and the git host. Keep intervals at
  minutes and wire a git webhook for instant syncs on push instead of tightening the poll.
- **Expecting CI to still deploy** — after adopting GitOps, CI must stop running `kubectl apply`. Its
  new job is to build the image and commit the new tag to the deploy repo; the controller deploys.
