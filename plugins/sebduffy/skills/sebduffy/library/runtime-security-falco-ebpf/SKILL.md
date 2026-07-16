---
name: runtime-security-falco-ebpf
category: security
description: >
  Deploy eBPF-based RUNTIME threat detection on Linux/Kubernetes hosts you are authorised to
  monitor. Use when you need to catch attacks AT EXECUTION — shell-in-container, reverse shells,
  crypto-miners, privilege escalation, unexpected outbound connections, file writes to /etc, kubectl
  exec — that static/pre-deploy scanners miss. Covers Falco (rule engine + alerting) and Cilium
  Tetragon (TracingPolicy + kernel-level enforcement/kill), modern_ebpf drivers, rule authoring,
  Helm install, and tuning out false positives. Detection and defence only, never offence.
when_to_use:
  - You need to detect live threats on running hosts/pods (post-deploy), not scan artifacts
  - A container spawned an unexpected shell, reverse shell, or crypto-miner and you want an alert
  - You want kernel-enforced blocking/kill of a syscall pattern (Tetragon TracingPolicy enforcement)
  - You are wiring runtime alerts into Slack/SIEM/Falcosidekick or a k8s audit pipeline
  - You must tune noisy Falco rules or write a custom detection rule for your workload
  - You want file-integrity or network-egress monitoring on a Kubernetes cluster you administer
when_not_to_use:
  - Scanning images/IaC/manifests before deploy — use container-iac-hardening
  - Static code vulnerability scanning — use sast-semgrep-opengrep
  - Live web-app attack testing — use dast-web-scan-zap-nuclei
  - Admission-time policy blocking (not runtime syscalls) — use policy-as-code-opa-kyverno
  - Dependency/CVE auditing — use supply-chain-sca-audit
keywords:
  - falco
  - tetragon
  - ebpf
  - runtime-security
  - threat-detection
  - kubernetes
  - syscall
  - reverse-shell
  - falcosidekick
  - tracingpolicy
  - modern-bpf
  - container-security
  - intrusion-detection
  - falcoctl
similar_to:
  - container-iac-hardening
  - policy-as-code-opa-kyverno
  - sast-semgrep-opengrep
  - dast-web-scan-zap-nuclei
inputs_needed: Authorised access (root/kubectl-admin) to the host or cluster you will monitor; kernel 5.8+ for modern_ebpf; Helm 3 + kubectl for k8s, or a Linux host with a package manager
produces: A running Falco/Tetragon deployment, validated custom detection rules or TracingPolicies, and an alert stream (stdout/JSON/Falcosidekick) plus a tuning checklist
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Runtime Security with Falco & Tetragon (eBPF)

Catch attacks **while they run**. Static scanners (SAST, image scans, IaC) find weaknesses before
deploy; they cannot see a compromised pod spawning `/bin/bash`, connecting to a C2 server, or writing
to `/etc/passwd` at 3am. Falco and Tetragon load eBPF programs into the kernel to observe every
syscall with near-zero overhead and alert (Falco) or **block/kill** (Tetragon) on suspicious patterns.

**Authorised use only.** Deploy these on infrastructure you own or administer. This is defensive
detection and response, not exploitation.

## When to use

Runtime is the last line — the one that fires *after* an attacker is already inside. Reach for this
when you need the "what is happening on my hosts *right now*" signal that pre-deploy tooling can't give.

## Prerequisites (honest deps)

- **Kernel 5.8+** for the `modern_ebpf` (CO-RE, no kernel module, no driver build) path. Older kernels
  need the legacy `ebpf` probe or the kernel module — avoid if you can.
- **Falco**: a Linux host (package install) or **Helm 3 + kubectl** (Kubernetes DaemonSet). `falcoctl`
  (bundled with recent charts) manages rule/plugin artifacts.
- **Tetragon**: **Helm 3 + kubectl**; the `tetra` CLI for observing events. Repo is `cilium/tetragon`.
- Both are open source (Falco = CNCF graduated; Tetragon = CNCF, Apache-2.0). No license key needed.
- macOS note: these are **Linux-kernel** tools. From a Mac, drive a remote Linux host / k8s cluster —
  you cannot run the eBPF probe locally. Use `scripts/validate.sh` to lint rules/policies from anywhere.

Confirm kernel support before installing:

```bash
uname -r                      # want 5.8+ for modern_ebpf
ls /sys/kernel/btf/vmlinux    # exists => BTF present => CO-RE / modern_ebpf works
```

## Recipe 1 — Falco on Kubernetes (detect + alert)

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm repo update

helm install falco falcosecurity/falco \
  --namespace falco --create-namespace \
  --set driver.kind=modern_ebpf \
  --set collectors.containerd.enabled=true \
  --set collectors.docker.enabled=false \
  --set tty=true \
  --set falco.json_output=true \
  --set falco.json_include_output_property=true

kubectl rollout status ds/falco -n falco
```

Watch alerts stream from the DaemonSet:

```bash
kubectl logs -f -n falco -l app.kubernetes.io/name=falco -c falco
```

Trigger a built-in rule to confirm detection works (this fires **Terminal shell in container**):

```bash
kubectl run pwn --rm -it --image=alpine -- sh   # opening a shell in a pod = a real Falco alert
```

You should see a `Notice`/`Warning` line naming the rule, container, and command.

## Recipe 2 — Falco on a single Linux host

```bash
# Debian/Ubuntu example (see falco.org for RPM / other distros)
curl -fsSL https://falco.org/repo/falcosecurity-packages.asc | \
  sudo gpg --dearmor -o /usr/share/keyrings/falco-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/falco-archive-keyring.gpg] \
  https://download.falco.org/packages/deb stable main" | \
  sudo tee /etc/apt/sources.list.d/falcosecurity.list
sudo apt-get update && sudo apt-get install -y falco

# Run with the modern eBPF probe (no kernel module build)
sudo falco -o engine.kind=modern_ebpf
```

## Recipe 3 — Write & load a custom Falco rule

Falco rules are YAML: `list` (reusable values), `macro` (reusable conditions), and `rule`
(condition → output → priority). Save as `custom_rules.yaml`:

```yaml
- macro: outbound
  condition: (evt.type in (connect) and evt.dir=< and fd.typechar=4)

- list: allowed_egress_ports
  items: [443, 80, 53]

- rule: Unexpected outbound connection from container
  desc: A container opened an egress connection to a non-standard port
  condition: >
    outbound and container
    and not fd.sport in (allowed_egress_ports)
    and not fd.dport in (allowed_egress_ports)
  output: >
    Unexpected egress (command=%proc.cmdline connection=%fd.name
    container=%container.name image=%container.image.repository)
  priority: WARNING
  tags: [network, mitre_exfiltration]
```

Validate before you ship it (never load an unvalidated rule):

```bash
falco --validate custom_rules.yaml           # syntax/schema check, exits non-zero on error
falco -L                                      # list all loaded rules
falco -l | grep fd.                           # list available fields for conditions
```

Load it into the k8s DaemonSet via a ConfigMap + Helm `customRules`:

```bash
helm upgrade falco falcosecurity/falco -n falco --reuse-values \
  --set-file customRules."custom_rules\.yaml"=./custom_rules.yaml
```

**Priorities** (highest→lowest): `EMERGENCY ALERT CRITICAL ERROR WARNING NOTICE INFORMATIONAL DEBUG`.
Route only `WARNING` and above to paging; keep the rest for forensics.

## Recipe 4 — Fan alerts out with Falcosidekick

```bash
helm upgrade falco falcosecurity/falco -n falco --reuse-values \
  --set falcosidekick.enabled=true \
  --set falcosidekick.config.slack.webhookurl="$SLACK_WEBHOOK_URL" \
  --set falcosidekick.config.slack.minimumpriority="warning"
```

Falcosidekick has 50+ outputs (Slack, Elasticsearch, Loki, PagerDuty, AWS/GCP, webhook). Prefer a
minimum priority so `DEBUG`/`INFO` noise never pages a human.

## Recipe 5 — Tetragon (observe + enforce/kill)

Tetragon adds kernel-level **enforcement** — it can `SIGKILL` a process the instant it matches, not
just alert. Install:

```bash
helm repo add cilium https://helm.cilium.io
helm repo update
helm install tetragon cilium/tetragon -n kube-system
kubectl rollout status -n kube-system ds/tetragon -w
```

Observe process execution events with the `tetra` CLI (runs inside the DaemonSet pod):

```bash
kubectl exec -ti -n kube-system ds/tetragon -c tetragon -- \
  tetra getevents -o compact
# scope to one pod:  ... tetra getevents -o compact --pods <podname>
```

Apply a **TracingPolicy** that kills any process reading `/etc/shadow` (enforcement, not just alert):

```yaml
# block-shadow-read.yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: "block-sensitive-file-read"
spec:
  kprobes:
  - call: "security_file_permission"
    syscall: false
    args:
    - index: 0
      type: "file"
    selectors:
    - matchArgs:
      - index: 0
        operator: "Equal"
        values:
        - "/etc/shadow"
      matchActions:
      - action: Sigkill    # kernel kills the offending process immediately
```

```bash
kubectl apply -f block-shadow-read.yaml     # cluster-wide; use TracingPolicyNamespaced to scope
```

Start with `action: Post` (observe/alert) and only switch to `Sigkill`/`Override` once you have
proven the policy never matches legitimate workloads — an over-broad kill action is an outage.

## Verify

- **Falco is loading eBPF, not the kernel module:** `kubectl logs -n falco -l app.kubernetes.io/name=falco -c falco | grep -i "modern ebpf"` (or `Falco initialized`).
- **Rules loaded:** the startup log prints `X rules loaded`, and `falco --validate <file>` exits 0.
- **Detection actually fires:** run Recipe 1's `kubectl run pwn` shell — an alert must appear within seconds. No alert = misconfigured driver/collector.
- **Tetragon sees events:** `tetra getevents -o compact` shows `🚀 process` lines for pod activity.
- **Enforcement works:** in a throwaway pod, `cat /etc/shadow` should be killed once the TracingPolicy is applied (test in a non-prod namespace first).
- Lint any rule/policy file offline with `scripts/validate.sh <file.yaml>`.

## Pitfalls

- **modern_ebpf needs kernel 5.8+ and BTF.** No `/sys/kernel/btf/vmlinux` → fall back to the legacy probe or module, or you get a silent no-events deployment. Always check `uname -r` first.
- **Wrong container runtime collector = zero container metadata.** Modern clusters are `containerd`; enabling only the `docker` collector yields alerts with empty `container.name`. Match the collector to the runtime.
- **Managed control planes (GKE/EKS/AKS)** don't let you load kernel modules — you MUST use `modern_ebpf` (or the eBPF probe), never `driver.kind=module`.
- **Alert fatigue kills the tool.** The default ruleset is noisy on real workloads (package managers, CI runners, base-image shells). Tune with exceptions/`not` clauses per rule rather than disabling rules wholesale, and gate paging on `priority >= WARNING`.
- **Tetragon `Sigkill`/`Override` is a live weapon.** A broad match action can kill legitimate processes and cause an outage. Ship policies as observe-only first; scope with `TracingPolicyNamespaced`.
- **These are not preventive controls at build time.** They detect/respond at runtime — pair with image scanning (container-iac-hardening) and admission policy (policy-as-code-opa-kyverno) for defence in depth.
- **Rule/plugin drift:** let `falcoctl artifacts follow` keep the maintained rules current, but pin and review versions in regulated environments rather than auto-pulling.
- **Overhead is low, not zero.** Very high-syscall workloads (databases, proxies) can feel eBPF cost; measure before rolling to every node and scope noisy TracingPolicies tightly.
