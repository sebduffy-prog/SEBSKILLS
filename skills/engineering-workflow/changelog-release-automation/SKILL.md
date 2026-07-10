---
name: changelog-release-automation
category: engineering-workflow
description: >
  Automate versioning and releases from git history — wire up Conventional Commits, generated
  CHANGELOGs, SemVer bumps, git tags, and GitHub Releases without hand-editing version numbers.
  Use when you need to set up semantic-release or changesets, pick between them for a single-package
  vs monorepo, add the CI/CD release job, debug "no release published" runs, or backfill a changelog.
  Grounded on real semantic-release and changesets docs so the config and commands actually run.
when_to_use:
  - Setting up automated npm/library releases so version + CHANGELOG + tag + GitHub Release happen in CI
  - Choosing between semantic-release (commit-driven) and changesets (intent-file-driven) for a repo
  - A monorepo needs independent per-package version bumps and coordinated publishing
  - Enforcing or adopting Conventional Commits and generating a CHANGELOG from them
  - Debugging a release job that ran green but published nothing, or bumped the wrong semver level
  - Backfilling or regenerating a changelog for an existing project
when_not_to_use:
  - You only need to parse/lint commit messages, not release — use a commitlint/husky setup directly
  - Deploying an app (containers, servers) rather than publishing a versioned artifact — use your CD/use-railway flow
  - Building the CI pipeline itself from scratch — pair this with a dedicated GitHub Actions/CI skill
  - Managing python/rust release tooling exclusively — this centres on the JS/npm ecosystem toolchain
keywords:
  - semantic-release
  - changesets
  - conventional-commits
  - changelog
  - semver
  - release-automation
  - github-releases
  - monorepo
  - versioning
  - npm-publish
  - commit-analyzer
  - release-notes
similar_to:
  - repo-context-packer
  - ast-grep-codemod
  - dependency-upgrade-migration
  - api-contract-design
  - mutation-testing
inputs_needed: A git repo with a remote; Node.js + npm/pnpm/yarn; publish creds (NPM_TOKEN and/or GITHUB_TOKEN) in CI; decision on single-package vs monorepo.
produces: A working release pipeline — semantic-release or changesets config, CI job, generated CHANGELOG.md, git tags, and GitHub Releases on merge to the release branch.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Changelog & Release Automation

Stop hand-editing `version` fields and CHANGELOGs. This skill wires up **automated, git-driven
releases** using the two dominant JS-ecosystem tools, and tells you which one to reach for.

## When to use

Use this when a repo should cut releases automatically on merge: bump SemVer, write the changelog,
tag, publish, and open a GitHub Release — with humans never touching a version number. Also use it
to debug releases that silently no-op, and to backfill changelogs.

## Choose your tool first

| | **semantic-release** | **changesets** |
|---|---|---|
| Bump comes from | Conventional Commit messages | intent files authors write (`.changeset/*.md`) |
| Best for | single package, trunk-based, fully automatic | monorepos, many packages, human-curated notes |
| Release cadence | every qualifying merge | batched — a "Version Packages" PR you merge |
| Prereleases | branch-based (`beta`, `alpha`) | `pre enter <tag>` mode |
| Control | least — commits decide everything | most — contributor states impact per change |

Rule of thumb: **one package + you trust commit discipline → semantic-release. A monorepo or you
want a review gate on version/notes → changesets.**

## Prerequisites

- Node.js 18+ and a package manager (npm, pnpm, or yarn). macOS here has no brew; use the repo's own toolchain.
- A git repo with a GitHub remote. Releases run in CI, not locally, for real publishes.
- Secrets in CI: `GITHUB_TOKEN` (usually auto-provided) and, to publish to npm, an `NPM_TOKEN` with automation rights.
- For semantic-release: commits must follow **Conventional Commits** (`feat:`, `fix:`, `BREAKING CHANGE:`), or nothing bumps.
- `npx` works without global installs — every command below is copy-runnable.

---

## Recipe A — semantic-release (single package, commit-driven)

**1. Install.**
```bash
npm i -D semantic-release @semantic-release/changelog @semantic-release/git
```
The core ships four default plugins already (`commit-analyzer`, `release-notes-generator`, `npm`,
`github`); you add `changelog` + `git` only if you want the `CHANGELOG.md` committed back.

**2. Config** — `.releaserc.json` at repo root:
```json
{
  "branches": ["main", { "name": "beta", "prerelease": true }],
  "plugins": [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    ["@semantic-release/changelog", { "changelogFile": "CHANGELOG.md" }],
    "@semantic-release/npm",
    "@semantic-release/github",
    ["@semantic-release/git", {
      "assets": ["CHANGELOG.md", "package.json"],
      "message": "chore(release): ${nextRelease.version} [skip ci]\n\n${nextRelease.notes}"
    }]
  ]
}
```
Plugin **order matters**: analyzer → notes → changelog → npm → github → git. Default `tagFormat` is
`v${version}`. Drop `@semantic-release/npm` (or set `"npmPublish": false`) for a private, non-npm repo.

**3. Dry-run locally** to see the next version without publishing:
```bash
npx semantic-release --dry-run --no-ci
```
`dryRun` skips prepare/publish/success/fail and prints the computed version + notes. It defaults to
`true` outside CI, so `--no-ci` lets you exercise it on your machine.

**4. CI job** — `.github/workflows/release.yml`:
```yaml
name: release
on:
  push:
    branches: [main]
permissions:
  contents: write        # tags + GitHub Release + commit back
  issues: write
  pull-requests: write
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }   # full history — shallow clones break commit analysis
      - uses: actions/setup-node@v4
        with: { node-version: 20, registry-url: 'https://registry.npmjs.org' }
      - run: npm ci
      - run: npx semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```
Commit bump mapping: `fix:` → patch, `feat:` → minor, `feat!:`/`BREAKING CHANGE:` footer → major.
`docs:`/`chore:`/`refactor:` → **no release** (by default).

---

## Recipe B — changesets (monorepo / curated, intent-driven)

**1. Init.**
```bash
npm i -D @changesets/cli
npx changeset init          # creates .changeset/config.json + README
```

**2. Author a changeset per change** (usually as part of the feature PR):
```bash
npx changeset               # interactive: pick packages, bump level, write summary
```
This writes a small markdown file under `.changeset/` capturing **which packages** bump and by
**major/minor/patch** plus a changelog line. Commit it with the code.

**3. `.changeset/config.json`** — the fields that matter:
```json
{
  "$schema": "https://unpkg.com/@changesets/config/schema.json",
  "changelog": "@changesets/changelog-github",
  "commit": false,
  "access": "public",
  "baseBranch": "main",
  "updateInternalDependencies": "patch",
  "ignore": []
}
```
`access: "public"` is required to publish scoped packages to npm. For rich GitHub-linked changelogs
install `@changesets/changelog-github` and set `"changelog": ["@changesets/changelog-github", { "repo": "org/repo" }]`.

**4. Consume + publish.** `version` applies all pending changesets (bumps every affected
`package.json`, rewrites CHANGELOGs, deletes the consumed changeset files); `publish` pushes to npm
and creates git tags:
```bash
npx changeset version       # run at release time, not per-commit
npx changeset publish       # publishes + tags; needs npm auth
```

**5. CI via the official action** — `.github/workflows/release.yml`:
```yaml
name: release
on:
  push:
    branches: [main]
permissions:
  contents: write
  pull-requests: write
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci
      - uses: changesets/action@v1
        with:
          version: npx changeset version
          publish: npx changeset publish
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
```
On merge, `changesets/action` opens/updates a **"Version Packages" PR**. Merging *that* PR triggers
the same workflow again, which detects no pending changesets and runs `publish`. Two-step by design.

For a prerelease train: `npx changeset pre enter next` → make releases → `npx changeset pre exit`.

---

## Backfilling a changelog for an existing repo

- **conventional-changelog** regenerates from history: `npx conventional-changelog -p angular -i CHANGELOG.md -s -r 0` (rewrite all) — needs Conventional Commits already in place.
- With changesets, hand-write one changeset summarising the accumulated changes before the first automated release.
- With semantic-release, the first run reads history from the last matching git tag; if there is no tag it treats everything as one release, so tag your current version first (`git tag v1.4.0`).

## Verify

- Dry run shows a real next version: `npx semantic-release --dry-run --no-ci` prints "The next release version is X.Y.Z" (or "no release" — see Pitfalls).
- Changesets status: `npx changeset status --verbose` lists pending bumps per package; `--since=main` scopes to a branch.
- After a real run: `git tag --list` shows the new tag, the GitHub **Releases** page has an entry, `CHANGELOG.md` has a new section, and (if publishing) `npm view <pkg> version` matches.
- CI logs: confirm the analyzer picked commits — semantic-release logs "Analysis of N commits complete: <level> release".

## Pitfalls

- **"no release published" but the job was green** — usually shallow clone. Always `fetch-depth: 0`; semantic-release needs full history + tags. Second cause: only `chore/docs/refactor` commits since last release → nothing qualifies. `feat`/`fix` are the only default bumpers.
- **Wrong bump level** — a breaking change written as `feat:` without `!` or a `BREAKING CHANGE:` footer only bumps minor. The footer must be in the commit *body*, blank-line separated.
- **`npm publish` 403 / auth** — `NPM_TOKEN` must be an *automation* token (bypasses 2FA), and scoped packages need `access: public` (changesets config) or `publishConfig.access` in package.json.
- **Changesets publishes nothing** — you merged code but never ran `npx changeset` to add an intent file; there is nothing to consume. `changeset status` will show "No changesets".
- **Plugin order (semantic-release)** — put `@semantic-release/git` last; committing before the changelog/npm steps captures a stale tree. The whole chain runs in array order.
- **Infinite CI loops** — the release commit can re-trigger the workflow. Use `[skip ci]` in the commit message (shown above) or a path/branch filter.
- **Two package managers** — don't mix a yarn lockfile with `npm ci`. Match the CI install command to the lockfile in the repo.
- **Never bump versions by hand** once either tool owns releases — a manual `package.json` version edit desyncs the tool's tag-based state and causes duplicate or skipped versions.
