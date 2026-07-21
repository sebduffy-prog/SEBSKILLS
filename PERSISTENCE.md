# Making SEBSKILLS outlive your work email — and run in every Claude

**The whole library depends on ONE thing: the GitHub account `sebduffy-prog` staying alive and public.**
Every install path, the `/sebduffy` router, and the on-demand skill fetch all read from
`https://github.com/sebduffy-prog/SebDuffy`. If that account is locked when your `@vccp.com`
email is disabled, the library goes dark everywhere at once. Fix that first; everything else is easy.

---

## 0. De-risk the GitHub account (do this before anything else)

The repo's commits are stamped `seb.duffy@vccp.com`. That is only commit metadata, but it's a
warning sign the **account** may be registered to your work email. Check and fix:

1. **GitHub → Settings → Emails.** Add a *personal* email (Gmail/iCloud/etc.) and **set it as
   primary**. Remove `seb.duffy@vccp.com` once the personal one is primary.
2. **GitHub → Settings → Password and authentication.** Confirm 2FA + recovery codes are saved
   somewhere you keep (not work systems). Reset the password to one in your personal manager.
3. **GitHub → Settings → Emails → "Keep my email address private"** and set a noreply commit email
   so future commits stop leaking the work address.
4. Confirm the repo is **Public** (Settings → General → Danger Zone shows "Make private", i.e. it is
   currently public). Public is required — the router fetches over the raw CDN with no auth.

> If the account genuinely cannot be detached from work, the clean fix is: create a new personal
> GitHub account, mirror the repo into it (`git push --mirror`), then run `./scripts/repoint.sh`
> (already in this repo) to rewrite every `sebduffy-prog` reference to the new owner, and commit.

**Belt-and-braces backup:** keep an offline copy so the library survives even GitHub going away.
```bash
git clone --mirror https://github.com/sebduffy-prog/SebDuffy ~/SEBSKILLS-backup.git
```
Store that on a personal drive. It contains every skill and all history.

---

## 1. There is no single artifact that installs into every Claude

Claude has **two distribution channels with different formats**. You need both to cover "all layers".

| Surface | Channel | Format | GitHub needed at runtime? |
|---|---|---|---|
| Claude Code **CLI** | Plugin marketplace | `marketplace.json` | Yes (router fetches skills) |
| Claude **desktop app** (Code) | Plugin marketplace | same | Yes |
| Claude Code **IDE** extensions | Plugin marketplace | same | Yes |
| **claude.ai/code** (web) | Plugin marketplace *or* commit router into the repo you open | same | Yes |
| **claude.ai chat** (web/desktop/mobile) | **Skills upload** | `.zip` per skill | **No — sandbox has no reliable internet** |

The Code family shares one mechanism. Chat is separate and must be **self-contained**.

---

## 2. Claude Code family (CLI, desktop, IDE, claude.ai/code)

Signed into **any** account, on **any** machine — nothing tied to your work login:

```
/plugin marketplace add sebduffy-prog/SebDuffy
/plugin install sebduffy@sebskills
```

Then `/sebduffy <anything>` routes to the best skill and loads it on demand. New skills you push to
the repo appear automatically — no reinstall.

Alternatives (also in SETUP.md):
- One-file router, no plugin: `curl -fsSL https://raw.githubusercontent.com/sebduffy-prog/SebDuffy/main/install-sebduffy.sh | bash`
- Whole library local + offline: `git clone … ~/.claude/skills-lib && ~/.claude/skills-lib/install.sh user`

## 3. Claude.ai chat (the one that needs zips)

Chat can't fetch from GitHub, so upload skills as self-contained zips:

```bash
./scripts/build_chat_zips.sh router          # the /sebduffy catalogue skill
./scripts/build_chat_zips.sh ffmpeg-cookbook dataviz   # specific skills you use in chat
./scripts/build_chat_zips.sh all             # every skill as its own zip (heavy)
```

Then **claude.ai → Settings → Capabilities → Skills → Upload skill**, and pick each `.zip` from
`dist/chat-skills/`.

Reality check for chat: the router skill gives you the catalogue and routing *advice*, but because
the sandbox can't fetch, it can't auto-load a target skill's full instructions. So for chat, also
upload the handful of skills you actually use there as their own zips. This is a platform limit, not
a repo problem.

---

## 4. One-time checklist

- [ ] GitHub account primary email switched to personal; work email removed
- [ ] 2FA recovery codes + password saved in personal manager
- [ ] Repo confirmed Public
- [ ] `~/SEBSKILLS-backup.git` mirror stored on a personal drive
- [ ] Code family: `/plugin marketplace add sebduffy-prog/SebDuffy` works from a clean session
- [ ] Chat: at least the router zip uploaded via Settings → Capabilities → Skills
