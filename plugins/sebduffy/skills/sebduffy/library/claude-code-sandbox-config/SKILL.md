---
name: claude-code-sandbox-config
category: security
description: >
  Configure Claude Code's OS-level Bash sandbox for safe autonomy — scope filesystem write/read
  paths, set network domain allowlists, and block or mask secret files and env vars with
  sandbox.credentials. Layer auto mode's classifier (blocks git reset --hard, terraform destroy,
  force push, curl|bash) and Docker/VM isolation for unattended runs. Reach for this whenever
  wiring up /sandbox, auto mode, --dangerously-skip-permissions, or the sandbox.* keys in
  settings.json so an agent can run tests/builds without approving every command.
when_to_use:
  - Enabling the sandboxed Bash tool so Claude runs builds/tests without per-command prompts
  - Scoping which paths a sandboxed command may write and which network domains it may reach
  - Blocking or masking secret files (~/.aws, ~/.ssh) and env vars (GITHUB_TOKEN) from sandboxed commands
  - Setting up autonomous / unattended runs and wanting a hard boundary around destructive commands
  - Enforcing sandboxing org-wide via managed settings and stopping developers widening the policy
when_not_to_use:
  - Reducing prompts for non-Bash tools (Read/Edit/WebFetch/MCP) — that is permission rules, see update-config
  - Rotating or remediating a leaked secret — use secrets-hygiene-and-remediation
  - Hardening a Dockerfile/IaC image itself rather than Claude's runtime — use container-iac-hardening
  - Writing OPA/Kyverno cluster admission policy — use policy-as-code-opa-kyverno
keywords:
  - claude-code
  - sandbox
  - seatbelt
  - bubblewrap
  - autonomy
  - auto-mode
  - network-allowlist
  - filesystem-isolation
  - credentials
  - secret-blocking
  - dangerously-skip-permissions
  - managed-settings
  - devcontainer
  - egress-control
  - unattended
similar_to:
  - secrets-hygiene-and-remediation
  - container-iac-hardening
  - policy-as-code-opa-kyverno
inputs_needed: Target settings scope (~/.claude, project .claude, or managed); the paths/domains a task legitimately needs; the secret files and env vars to protect; whether the run is attended or unattended.
produces: A validated sandbox block in settings.json (filesystem, network, credentials), an auto-mode/isolation decision, and a lint report of policy footguns.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Claude Code Sandbox Config

Configure **safe autonomy** for Claude Code: let the agent run most Bash without asking, while the
operating system — not the model — enforces what files and domains each command can touch. This
skill covers the built-in sandbox (`sandbox.*` keys), secret protection (`sandbox.credentials`),
auto mode's destructive-command classifier, and heavier isolation (dev container, VM/microVM) for
unattended runs.

## When to use

Use it when someone says "stop asking me to approve every command", "run this unattended", "make it
safe to `--dangerously-skip-permissions`", or when you are editing the `sandbox` block of a
`settings.json`. The goal is fewer prompts **without** handing an agent your SSH keys or a path to
`terraform destroy` prod.

## Prerequisites (read the honest caveats)

- **Platforms**: macOS, Linux, WSL2. Native Windows is **not** supported — run inside WSL2.
- **macOS**: nothing to install; the sandbox uses the built-in Seatbelt framework.
- **Linux/WSL2**: needs `bubblewrap` (filesystem isolation) and `socat` (network relay):
  `sudo apt-get install bubblewrap socat` (or `dnf`). Optional seccomp Unix-socket blocking comes
  from `npm install -g @anthropic-ai/sandbox-runtime`. Run `/sandbox` — its Dependencies tab tells
  you what's missing.
- **Version floors** (verify with `claude --version`, features roll forward): `sandbox.credentials`
  needs **v2.1.187+**; env-var `mask` mode + `network.tlsTerminate` need **v2.1.199+**; auto mode
  needs **v2.1.83+** and specific models (Opus 4.6 / Sonnet 4.6 or newer; on Bedrock/Vertex/Foundry
  only Sonnet 5, Opus 4.7/4.8).
- **Beta / experimental — say so to the user**: **auto mode is a research preview** (reduces prompts,
  does not guarantee safety). `network.tlsTerminate` is **experimental**. The standalone
  `@anthropic-ai/sandbox-runtime` is a **beta research preview** and its config format may change.
- **Not a hard boundary**: by default the proxy does not inspect TLS, so a broad `allowedDomains`
  entry (e.g. `github.com`) can be a data-exfiltration path via domain fronting. The sandbox limits
  Bash only — MCP servers, hooks, and file tools still run on the host unless you wrap the whole
  process (see Recipe E).

## Recipes

### A. Turn it on and pick a mode

Run `/sandbox` in a session. Three tabs: **Mode** (auto-allow vs regular permissions), **Overrides**
(`allowUnsandboxedCommands`), **Config** (resolved settings). Picking a mode writes to
`.claude/settings.local.json`. To enable everywhere, put it in `~/.claude/settings.json`:

```json
{ "sandbox": { "enabled": true } }
```

Auto-allow mode runs sandboxed commands without prompting; commands that can't be sandboxed (new
network host, incompatible tool) fall back to the normal permission flow. Even in auto-allow, deny
rules, `rm`/`rmdir` targeting `/` or `$HOME`, and content-scoped `ask` rules (`Bash(git push *)`)
still prompt.

### B. Scope the filesystem

Default: write to the working directory + session `$TMPDIR`; **read the whole machine** (including
`~/.aws/credentials` and `~/.ssh` — see Recipe D). Widen writes only where a tool needs it:

```json
{
  "sandbox": {
    "enabled": true,
    "filesystem": {
      "allowWrite": ["~/.kube", "/tmp/build"],
      "denyRead":  ["~/"],
      "allowRead": ["."]
    }
  }
}
```

Path prefixes: `/` = absolute, `~/` = home, `./` or bare = project root (in project settings) or
`~/.claude` (in user settings). The `denyRead: ["~/"]` + `allowRead: ["."]` pair only blocks home
while keeping the project readable **when placed in the project's `.claude/settings.json`**, because
`.` resolves to project root there. Arrays merge across scopes (any scope can add; none can remove).
Footgun: an `allowWrite` into a `$PATH` dir or over `.bashrc`/`.zshrc` is a privilege-escalation
path — keep write paths narrow.

### C. Lock down egress

No domains are pre-allowed; the first new host prompts (and is remembered for the session as of
v2.1.191). Pre-allow to avoid prompts; deny to carve out of a wildcard:

```json
{
  "sandbox": {
    "enabled": true,
    "network": {
      "allowedDomains": ["registry.npmjs.org", "*.github.com"],
      "deniedDomains":  ["gist.github.com"]
    }
  }
}
```

For managed lockdown set `allowManagedDomainsOnly: true` (blocks non-allowed hosts instead of
prompting, honors only managed `allowedDomains`). A corporate MITM proxy: set
`network.httpProxyPort` / `network.socksProxyPort`.

### D. Protect credentials (v2.1.187+)

There is **no built-in deny list** — only what you list is protected. `deny` unsets an env var /
blocks a file read; `mask` (v2.1.199+) keeps auth working by swapping a per-session sentinel for the
real value only when a request reaches `injectHosts`.

```json
{
  "sandbox": {
    "enabled": true,
    "network": { "tlsTerminate": {}, "allowedDomains": ["*.github.com", "registry.npmjs.org"] },
    "credentials": {
      "files": [
        { "path": "~/.aws/credentials", "mode": "deny" },
        { "path": "~/.ssh",             "mode": "deny" }
      ],
      "envVars": [
        { "name": "NPM_TOKEN", "mode": "deny" },
        { "name": "GH_TOKEN",  "mode": "mask", "injectHosts": ["api.github.com"] }
      ]
    }
  }
}
```

`mask` requires `network.tlsTerminate` (the proxy must see request contents) and every `injectHosts`
entry must also be in `allowedDomains`; masking is honored only from user/managed/`--settings`
scopes, never a repo's `.claude/settings.json`. `deny` beats `mask` if both are set. To strip
Anthropic + cloud creds from **all** subprocesses regardless of sandbox, set the env var
`CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`.

### E. Choose isolation for unattended runs

The Bash sandbox constrains Bash only — **not enough** for `--dangerously-skip-permissions`. Layers,
weakest → strongest:

- **Auto mode** (`--permission-mode auto` or `defaultMode: "auto"` in **user** settings): a
  classifier reviews each action. Blocks by default include `curl | bash`, force push,
  `git reset --hard` / `git checkout -- .` / `git clean -fd` (v2.1.182+), `git commit --amend` on a
  pushed commit, `terraform destroy` / `pulumi destroy` / `cdk destroy`, prod deploys, mass cloud
  deletion, IAM grants, printing live tokens. It blocks 3-in-a-row / 20-total then resumes
  prompting. It is a per-action control, **not** an isolation boundary.
- **`@anthropic-ai/sandbox-runtime`** (beta): wraps the *whole* process (file tools, MCP, hooks).
  Configure `~/.srt-settings.json` (deny-all by default — allow your project, `~/.claude`,
  `~/.claude.json`, and `api.anthropic.com`), then `npx @anthropic-ai/sandbox-runtime claude`.
- **Dev container** (`.devcontainer/`, needs Docker): default-deny iptables firewall; safe to run
  `--dangerously-skip-permissions` because egress is blocked and Claude runs non-root.
- **VM / microVM** (Firecracker, or Docker Desktop sandboxes): kernel-level separation — use for
  untrusted repos.

`--dangerously-skip-permissions` refuses to start as root/sudo (skipped inside a recognized sandbox
— that is what the dev container relies on). `docker` itself is incompatible with the Bash sandbox:
add `docker *` to `sandbox.excludedCommands`.

### F. Enforce org-wide (managed settings)

Deliver via MDM-managed file or server-managed settings on Claude.ai. Boolean managed keys win over
local; arrays merge (developers can append).

```json
{
  "sandbox": {
    "enabled": true,
    "failIfUnavailable": true,
    "allowUnsandboxedCommands": false,
    "allowManagedReadPathsOnly": true,
    "network": { "allowManagedDomainsOnly": true }
  },
  "permissions": { "disableBypassPermissionsMode": "disable" }
}
```

`failIfUnavailable` makes a missing dep a hard stop (not a silent unsandboxed fallback);
`allowUnsandboxedCommands: false` kills the `dangerouslyDisableSandbox` escape hatch (Strict mode);
`allowManagedReadPathsOnly` / `allowManagedDomainsOnly` stop developers widening read paths / domains.
Lock auto mode with `permissions.disableAutoMode: "disable"`. Keep `excludedCommands` narrow — it has
no managed-only lockdown, so any scope can append to it.

## Verify

1. **Config lints clean**: `python3 scripts/lint_sandbox.py <path-to-settings.json>` — flags broad
   domains, `$PATH`/dotfile write grants, `mask` in a repo scope, and a missing credentials block.
2. **Filesystem holds**: ask Claude to run `touch ~/.zshrc.test` under the sandbox — it must be
   denied (or prompt), not silently succeed.
3. **Network holds**: run `curl https://example.com` for a host not in `allowedDomains` — expect a
   prompt (or a block under `allowManagedDomainsOnly`).
4. **Secrets hidden**: run `cat ~/.aws/credentials` and `echo "$GITHUB_TOKEN"` in a sandboxed
   command — the file read is denied and the var is empty when listed in `credentials`.
5. **Auto mode boundary**: confirm `claude auto-mode defaults` lists the destructive rules, and that
   `git reset --hard` is refused in auto mode.

## Pitfalls

- **Default read is wide open.** Enabling the sandbox does NOT hide `~/.aws` or `~/.ssh` — you must
  add `sandbox.credentials` or `filesystem.denyRead`. This surprises everyone.
- **`.` resolves by scope.** `allowRead: ["."]` means project root in project settings but `~/.claude`
  in user settings — a `denyRead: ["~/"]` in the wrong scope silently blocks your project.
- **`mask`/`tlsTerminate` from a repo scope is ignored** — put them in user/managed/`--settings`, and
  `mask` fails closed (auth breaks) without `tlsTerminate`.
- **Broad `allowedDomains` = exfil path.** TLS isn't inspected by default; `github.com` covers gists
  and arbitrary repos. Prefer specific hosts; use a real MITM proxy if your threat model needs it.
- **Sandbox ≠ full isolation.** MCP servers and hooks run on the host. For unattended
  `--dangerously-skip-permissions`, wrap the whole process (sandbox-runtime / container / VM), not
  just Bash.
- **`docker`, `watchman`/`jest`, Go CLIs (`gh`, `gcloud`, `terraform`) misbehave** in the sandbox —
  add to `excludedCommands`, use `jest --no-watchman`, and note excluded commands lose isolation.
- **Auto mode isn't a wall.** It's a classifier (research preview) that can be bypassed by novel
  phrasing and pauses after repeated blocks; for a hard guarantee add a `permissions.deny` rule —
  those apply in every mode.
- **`bypassPermissions` / `--dangerously-skip-permissions` offers no injection protection.** Only in
  isolated containers/VMs without internet.
