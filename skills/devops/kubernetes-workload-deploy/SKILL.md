---
name: kubernetes-workload-deploy
category: devops
description: >
  Ship a containerised app to Kubernetes properly. Verb-first trigger when you must write or fix
  Deployment / Service / Ingress manifests, add an HPA autoscaler, template with Helm, layer envs
  with Kustomize overlays, roll out and roll back, or debug a pod stuck in CrashLoopBackOff /
  ImagePullBackOff / Pending. Use when Docker Compose has outgrown a single host and you need
  replicas, health probes, resource limits, secrets, and a real ingress route on a cluster.
when_to_use:
  - Turning a Docker image into a production Deployment with probes, resource requests/limits, and replicas
  - Exposing a workload via Service (ClusterIP/NodePort/LoadBalancer) and an Ingress host/path route with TLS
  - Adding a HorizontalPodAutoscaler so pods scale on CPU or memory
  - Packaging manifests as a reusable Helm chart, or installing/upgrading a third-party chart
  - Managing per-environment config (dev/stage/prod) with Kustomize base + overlays
  - Rolling out a new image version and rolling back a bad release, or debugging a stuck/crashing pod
when_not_to_use:
  - Single-host container run or local dev stack — use dockerfile-and-compose-authoring instead
  - Provisioning the cluster/VPC/node pools itself (EKS/GKE/AKS) — use terraform-iac-modules instead
  - Deploying to a managed PaaS with no cluster to manage — use use-railway instead
  - Building the CI pipeline that runs kubectl/helm — use github-actions-pipelines instead
keywords: [kubernetes, kubectl, helm, kustomize, deployment, service, ingress, hpa, autoscaling, rollout, crashloopbackoff, imagepullbackoff, probes, manifests, yaml, k8s]
similar_to: [dockerfile-and-compose-authoring, terraform-iac-modules, github-actions-pipelines, use-railway]
inputs_needed: A container image reference (registry/name:tag), the container port it listens on, target namespace, and a working kubeconfig context (kubectl cluster-info succeeds). For Ingress, an ingress controller installed and a hostname.
produces: Applied Kubernetes resources (Deployment, Service, optional Ingress + HPA) as version-controllable YAML, or a Helm release / Kustomize overlay set, with a verified healthy rollout.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Kubernetes Workload Deploy

Run a container image on a cluster the way production expects: replicas, health probes, resource
bounds, a stable network identity, an external route, autoscaling — plus the Helm/Kustomize
workflows that keep it maintainable across environments.

## When to use

Compose is single-host: no self-healing, no rolling updates, no autoscaling. The moment you need
N replicas across nodes, zero-downtime deploys, or environment overlays, you are on Kubernetes.
This skill covers raw manifests, Helm, Kustomize, and day-2 rollout/debug.

## Prerequisites

- `kubectl` on PATH and a context that reaches a cluster: `kubectl cluster-info` must succeed.
  (Local options: `kind`, `minikube`, `k3d`, Docker Desktop Kubernetes.)
- The image must be pullable by the cluster. Private registry ⇒ an `imagePullSecrets` entry.
- **Ingress needs a controller** installed (e.g. ingress-nginx) — manifests alone do nothing.
  Check: `kubectl get pods -n ingress-nginx`.
- **HPA needs metrics-server** — `kubectl top pods` must return numbers, else HPA targets stay
  `<unknown>` and never scale.
- Helm 3 (`helm version` → v3.x; no Tiller) for the Helm recipe.

## Recipe 1 — Raw manifests (Deployment + Service + Ingress)

Use the stable API groups shown below (not the old betas). `deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  labels: { app: web }
spec:
  replicas: 3
  selector:
    matchLabels: { app: web }          # MUST match template labels exactly
  strategy:
    type: RollingUpdate
    rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }   # zero-downtime
  template:
    metadata:
      labels: { app: web }
    spec:
      containers:
        - name: web
          image: registry.example.com/web:1.4.2   # pin a tag, never :latest
          ports:
            - containerPort: 8080
          resources:
            requests: { cpu: "100m", memory: "128Mi" }   # scheduler + HPA baseline
            limits:   { cpu: "500m", memory: "256Mi" }
          readinessProbe:                # gates traffic; failing = pulled from Service
            httpGet: { path: /healthz, port: 8080 }
            initialDelaySeconds: 5
          livenessProbe:                 # failing = container restarted
            httpGet: { path: /healthz, port: 8080 }
            initialDelaySeconds: 15
```

`service.yaml` — stable virtual IP + DNS name (`web.<namespace>.svc.cluster.local`):

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  selector: { app: web }     # selects the Deployment's pods by label
  ports:
    - port: 80               # Service port
      targetPort: 8080       # containerPort
  type: ClusterIP            # in-cluster only; use LoadBalancer for a cloud external IP
```

`ingress.yaml` — HTTP host/path routing + TLS:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  tls:
    - hosts: [app.example.com]
      secretName: web-tls        # a kubernetes.io/tls secret (e.g. from cert-manager)
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web
                port: { number: 80 }   # matches Service.port, not targetPort
```

Apply and watch:

```bash
kubectl apply -n prod -f deployment.yaml -f service.yaml -f ingress.yaml
kubectl rollout status deployment/web -n prod   # blocks until healthy or fails
```

## Recipe 2 — HorizontalPodAutoscaler

Requires `resources.requests` (percentages are relative to the request) and metrics-server.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: { type: Utilization, averageUtilization: 70 }
```

```bash
kubectl apply -f hpa.yaml -n prod
kubectl get hpa web -n prod -w      # TARGETS shows <unknown> until metrics-server reports
```

## Recipe 3 — Helm chart

```bash
helm create web-chart                       # generates templates/ + values.yaml
helm template web ./web-chart -f prod-values.yaml   # render locally, no cluster
helm install web ./web-chart -n prod --create-namespace -f prod-values.yaml
# ship a new version:
helm upgrade web ./web-chart -n prod -f prod-values.yaml --atomic --wait
helm rollback web 1 -n prod                  # revert to a known-good revision
```

`--atomic --wait` auto-rolls-back if the release never becomes healthy. Public charts install the
same way after `helm repo add <name> <url> && helm repo update`.

## Recipe 4 — Kustomize overlays (dev/stage/prod)

One base, thin per-env patches. No templating language — strategic merge + generators.
Layout: `base/{deployment.yaml,service.yaml,kustomization.yaml}` and `overlays/prod/kustomization.yaml`.

`base/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources: [deployment.yaml, service.yaml]
```

`overlays/prod/kustomization.yaml`:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: prod
resources: [../../base]
replicas:
  - { name: web, count: 5 }
images:
  - { name: registry.example.com/web, newTag: "1.4.2" }
```

```bash
kubectl kustomize overlays/prod        # render to stdout to review the diff
kubectl apply -k overlays/prod         # -k applies a kustomization directory
```

## Recipe 5 — Rollout, rollback, and debugging

```bash
kubectl set image deployment/web web=registry.example.com/web:1.4.3 -n prod
kubectl rollout status deployment/web -n prod
kubectl rollout undo deployment/web -n prod             # back to previous ReplicaSet
```

Triage a broken pod — always start with `describe` (Events at the bottom tell you why):

```bash
kubectl describe pod <pod> -n prod        # Events: image pull, scheduling, probe failures
kubectl logs <pod> -n prod --previous     # logs of the crashed container instance
```

Common statuses:
- **ImagePullBackOff** — wrong image/tag or missing registry auth (`imagePullSecrets`).
- **CrashLoopBackOff** — container exits on start; read `logs --previous`, check the command/env.
- **Pending** — unschedulable: insufficient CPU/memory, or a PVC/node-selector unmet.
- **0/1 Ready** — liveness OK but readiness failing; traffic (correctly) withheld.

## Verify

```bash
kubectl get deploy,svc,ingress,hpa -n prod         # everything created
kubectl rollout status deployment/web -n prod      # healthy rollout
kubectl get pods -n prod -l app=web                # all replicas Running & Ready
kubectl port-forward svc/web 8080:80 -n prod       # then curl localhost:8080/healthz
```

Ingress reachable: `curl -H 'Host: app.example.com' http://<ingress-external-ip>/`.
HPA live: `kubectl get hpa web -n prod` shows a real TARGETS %, not `<unknown>`.

## Pitfalls

- **`:latest` tags** make rollouts non-deterministic and undoable — pin an immutable tag/digest.
- **Selector ≠ template labels.** `spec.selector.matchLabels` must equal `template.metadata.labels`,
  and the selector is immutable after creation — a mismatch is rejected or orphans pods.
- **No resource requests ⇒ no HPA and poor scheduling.** Requests are the baseline the scheduler
  and the HPA percentage both use. Missing them silently breaks autoscaling.
- **Liveness vs readiness confusion.** Liveness restarts the container; readiness only gates
  traffic. A too-aggressive liveness probe restart-loops a slow-starting app — use a
  `startupProbe` for slow boots.
- **Ingress with no controller** applies cleanly and does nothing. Confirm a controller and set
  `ingressClassName`.
- **Secrets are base64, not encrypted.** Do not commit plaintext Secrets; use sealed-secrets,
  SOPS, or an external secrets operator.
- **HPA + hard-coded replicas** in the same Deployment oscillate. Let one own the count.
