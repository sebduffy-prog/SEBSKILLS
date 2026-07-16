---
name: dependency-upgrade-migration
category: engineering-workflow
description: >-
  Upgrade dependencies without breaking the build. Split the outdated list into safe batches
  (patch/minor) and risky majors handled one-at-a-time on their own branch; read the actual
  CHANGELOG / migration guide before every major, apply the upstream codemod (jscodeshift, ng
  update, cargo fix), and gate each step on a green test run. Covers npm/yarn/pnpm, pip/uv, cargo,
  and go, plus Renovate/Dependabot config so the safe bumps automate themselves. Reach for this
  the moment `npm outdated` (or the ecosystem equivalent) shows a wall of updates and you need a
  safe, ordered, reversible plan instead of a reckless `-u` on everything.
when_to_use:
  - "`npm outdated` / `pip list --outdated` / `cargo outdated` shows a large backlog and you want an ordered, low-risk upgrade plan"
  - A major-version bump is available (React 18→19, Angular, ESLint 8→9 flat config) and you need the migration guide + codemod, not a blind bump
  - You want to batch and auto-merge the safe patch/minor updates while isolating each risky major on its own branch
  - Setting up Renovate or Dependabot so routine bumps grouped and automerged instead of done by hand
  - A dependency upgrade broke the build and you need to bisect which bump caused it
when_not_to_use:
  - Adding a brand-new dependency rather than upgrading existing ones — just `npm install pkg` / `cargo add`
  - Applying a syntax-aware code rewrite the upstream tool does NOT ship a codemod for — use `ast-grep-codemod` to write your own
  - Cutting a release / generating release notes after upgrades land — use `changelog-release-automation`
  - Auditing/patching a security CVE with no version bump strategy needed — run `npm audit fix` / `pip-audit` directly
keywords:
  - dependency-upgrade
  - migration
  - breaking-change
  - codemod
  - npm-outdated
  - npm-check-updates
  - renovate
  - dependabot
  - semver
  - major-bump
  - lockfile
  - changelog
  - jscodeshift
  - cargo-update
  - go-get
  - automerge
similar_to:
  - ast-grep-codemod
  - changelog-release-automation
  - repo-context-packer
  - mutation-testing
  - semantic-code-search
inputs_needed: A git repo with a committed lockfile, the package manager in use (npm/yarn/pnpm/pip/uv/cargo/go), a working test/build command, and network access to registries + changelogs.
produces: An ordered upgrade plan, a series of small green-tested commits (one per major, batches for minors/patches), applied upstream codemods, and optionally a Renovate/Dependabot config that automates future safe bumps.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Dependency Upgrade & Migration

Upgrading everything at once with `ncu -u && npm install` is how you get a red build with 40
suspects and no way to bisect. The winning strategy is boring: **classify by risk, batch the safe
ones, isolate every major, and let the test suite gate each step.** SemVer is the lever — per the
Renovate maintainers, "non-major updates in SemVer ecosystems shouldn't have breaking changes (if
they follow the spec)," so patch/minor can travel together while every major gets its own branch,
changelog read, and codemod.

## When to use

The moment the outdated list is long enough that a single commit would be unbisectable, or a major
bump is on the table. If you only have one small patch to apply, skip the ceremony and bump it.

## Prerequisites

- **Git working tree clean** and the **lockfile committed** — this is your undo button. Every step
  below assumes you can `git checkout -- .` to bail.
- A **green baseline**: run the full test/build BEFORE touching anything. If it's already red, stop
  — you can't attribute failures to upgrades.
- The right tools per ecosystem (all optional installs, no brew needed):
  - Node: `npx npm-check-updates` (ncu) — no global install required.
  - Python: `pip list --outdated`; for pinned projects `pip-tools` (`pip-compile`) or `uv`.
  - Rust: `cargo update` is built in; `cargo install cargo-outdated` for the report.
  - Go: `go` toolchain only (`go list -u -m all`, `go get`, `go mod tidy`).

## Recipe 1 — Classify the backlog (Node)

Get the outdated report and split it by SemVer distance. `npm outdated` colour-codes but the
machine-readable split comes from ncu, which understands `--target`:

```bash
# What's behind, as JSON (wanted vs latest per package)
npm outdated --json | jq 'to_entries[] | {name:.key, current:.value.current, wanted:.value.wanted, latest:.value.latest}'

# The SAFE batch: everything reachable within minor/patch (no majors)
npx npm-check-updates --target minor      # preview only, writes nothing

# The RISKY list: what a full bump WOULD do (majors included)
npx npm-check-updates --target latest      # preview; majors show as red version jumps
```

Anything where `latest` crosses a major boundary from `current` goes on the **isolate** list.
Everything else is the **batch** list.

## Recipe 2 — Land the safe batch in one green commit

Apply only the non-major bumps, install, test, commit. `--target minor` guarantees ncu won't pull
a major:

```bash
npx npm-check-updates --target minor -u    # rewrites package.json
npm install                                 # updates lockfile
npm test && npm run build                   # GATE — must be green
git add package.json package-lock.json && git commit -m "chore(deps): batch minor+patch upgrades"
```

If the batch goes red, don't debug the whole batch — use **doctor mode** to find the culprit. It
upgrades one dependency at a time, runs your tests, and reverts the ones that fail:

```bash
npx npm-check-updates --target minor --doctor -u --doctorTest "npm test"
```

You're left with only the green bumps applied and a printed list of which package broke. Move the
broken one to the isolate list.

## Recipe 3 — Isolate and migrate ONE major

One branch, one major, one changelog, one commit. Never stack two majors in a branch — you lose
attribution.

```bash
git checkout -b deps/react-19
```

1. **Read the actual breaking-change notes first.** Don't guess. Fetch the release/migration doc:
   ```bash
   # Whatever the package's changelog convention is:
   gh release view v19.0.0 --repo facebook/react
   # or open the migration guide the release links to
   ```
2. **Run the upstream codemod** if one exists — most big libraries ship one. Examples:
   - React: `npx codemod@latest react/19/migration-recipe` (or `npx react-codemod`)
   - Angular: `ng update @angular/core@19 @angular/cli@19` (runs its own migrations)
   - ESLint 8→9 flat config: `npx @eslint/migrate-config .eslintrc.json`
   - Next.js: `npx @next/codemod@latest upgrade latest`
   - Rust editions/API: `cargo fix --edition` then `cargo fix --broken-code`
   If no codemod ships, express the mechanical rewrite yourself with **`ast-grep-codemod`**.
3. **Bump the single package**, install, and run the codemod's output through tests:
   ```bash
   npx npm-check-updates react react-dom --target latest -u
   npm install
   npm test && npm run build          # GATE
   ```
4. Fix the residue the codemod couldn't (deprecations, type errors), keep tests green, then commit
   and open a focused PR: `git commit -m "feat(deps): migrate to React 19"`.

Repeat per major. Small PRs review faster and revert cleanly.

## Recipe 4 — Other ecosystems

**Python (pinned via pip-tools):** bump one line in `requirements.in` or use `-P`:
```bash
pip-compile --upgrade-package django==5.1 requirements.in   # targeted
pip-compile --upgrade requirements.in                       # everything (the "batch")
pip-sync requirements.txt && pytest
```
With `uv`: `uv lock --upgrade-package django` (targeted) or `uv lock --upgrade` (all), then `uv sync`.

**Rust:**
```bash
cargo update -p serde --precise 1.0.210     # one crate, exact version
cargo update                                 # all compatible (semver-safe) bumps
cargo build && cargo test                    # GATE
# for a major that changed the edition:
cargo fix --edition && cargo fix --broken-code
```
`cargo update` only moves within your `Cargo.toml` semver ranges — to cross a major you edit the
version requirement in `Cargo.toml` first (or `cargo add serde@2`), then `cargo update -p serde`.

**Go:**
```bash
go get -u=patch ./...          # patch-only batch (safest)
go get -u ./...                # minor+patch batch
go get example.com/mod@v2.0.0  # a single major (note: v2+ import path changes!)
go mod tidy && go build ./... && go test ./...   # GATE
```

## Recipe 5 — Automate the safe bumps (Renovate / Dependabot)

Once the manual pass is clean, stop doing patch/minor by hand. Configure the bot to group and
automerge the safe classes and only ping you for majors.

**Renovate** (`renovate.json`) — automerge non-majors, separate every major into its own PR:
```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "packageRules": [
    { "matchUpdateTypes": ["minor", "patch"], "matchCurrentVersion": "!/^0/", "automerge": true },
    { "matchUpdateTypes": ["major"], "automerge": false, "addLabels": ["major-upgrade"] }
  ],
  "lockFileMaintenance": { "enabled": true, "automerge": true }
}
```
`matchCurrentVersion: "!/^0/"` excludes `0.x` deps (where minor can break). `lockFileMaintenance`
is the lowest-risk automerge candidate — it refreshes the lockfile without changing declared ranges.

**Dependabot** (`.github/dependabot.yml`) — group the minors/patches so they arrive as one PR:
```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule: { interval: "weekly" }
    groups:
      safe-bumps:
        update-types: ["minor", "patch"]
```

## Verify

- **Green gate every step:** the invariant is that `main` never regresses. Each commit above ends
  in a passing `npm test && npm run build` (or ecosystem equivalent). If a step is red, it doesn't
  commit.
- **Lockfile changed and committed:** `git status` should show `package-lock.json` / `Cargo.lock` /
  `go.sum` / `requirements.txt` staged alongside the manifest. A manifest bump with no lockfile
  change means the install didn't actually resolve the new version.
- **Confirm the new version resolved:** `npm ls react`, `cargo tree -i serde`, `go list -m all | grep mod`,
  `pip show django` — don't trust the manifest, trust the resolver.
- **Deprecation-clean:** run the build with warnings visible; a codemod that "passed" tests can
  still leave deprecated-API warnings that become the next major's hard errors.

## Pitfalls

- **Stacking majors in one branch.** Two majors = unbisectable red. One major per branch, always.
- **`ncu -u` without a target.** Bare `-u` writes every latest incl. majors into `package.json` in
  one shot — the exact unbisectable commit you're trying to avoid. Use `--target minor` for batches.
- **Editing the manifest but not running install.** `ncu -u` / editing `Cargo.toml` only rewrites
  the declaration; the lockfile (and thus the actual installed tree) doesn't move until you run the
  package manager. Always follow with `npm install` / `cargo update -p` / `pip-sync`.
- **Skipping the changelog because "SemVer says minor is safe."** SemVer is a promise, not a
  guarantee — `0.x` packages break on minors, and some maintainers mislabel. Read majors always;
  spot-check minors of load-bearing deps.
- **Go v2+ path trap.** A Go major (`v2`+) changes the *import path* (`/v2` suffix). `go get -u`
  will NOT move you across it — you edit imports (a codemod job) then `go get mod/v2@latest`.
- **Assuming a codemod is complete.** Codemods handle the mechanical 80%; they leave semantic
  changes, config migrations, and edge cases. Tests + a deprecation-clean build are what actually
  certify a major, not "the codemod ran."
- **Peer-dependency deadlock.** Bumping one package can strand a peer at an incompatible range.
  Resolve the peer in the SAME major branch (bump both together) rather than forcing with
  `--legacy-peer-deps`, which just hides the conflict until runtime.
