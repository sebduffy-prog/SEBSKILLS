---
name: editorial-style-linter
category: documents
description: >
  Enforce a deterministic editorial house style with Vale — flag banned terms, UK/US
  spelling drift, wordy phrases, inconsistent capitalisation, and over-hard readability.
  Trigger when someone says "lint the copy", "enforce our style guide", "check UK spelling",
  "flag banned words", "readability score", "Vale config", "style linter", or wants
  repeatable, gate-able prose checks in CI instead of a subjective human read-through.
when_to_use:
  - Codifying a brand/editorial style guide into machine-checkable rules (banned words, preferred terms)
  - Catching US vs UK spelling drift across decks, blog posts, docs, or campaign copy
  - Failing a CI job or pre-commit hook when copy breaks house style
  - Measuring readability (Flesch-Kincaid grade level) and gating on a ceiling
  - Standardising capitalisation of product/brand names and section headings
  - Onboarding a new writer with instant, consistent feedback on drafts
when_not_to_use:
  - Qualitative brand-voice / tone judgement ("does this sound like us") — that is subjective; use a review pass, not this skill
  - Translating or QA-ing localised copy across locales — use i18n-localization-qa
  - Producing the document itself (.docx/.pptx) — use docx or pptx, then lint the output
  - Grammar/spell-check inside a live Word doc — use the docx skill's tooling
keywords:
  - vale
  - linter
  - style guide
  - house style
  - readability
  - uk spelling
  - banned words
  - substitution
  - proselint
  - editorial
  - prose
  - flesch-kincaid
  - ci
  - copy-editing
similar_to:
  - i18n-localization-qa
  - contract-review
  - docx
  - internal-comms
inputs_needed: A document or directory to lint (.md/.txt/.html/.adoc etc.), plus your house-style rules (banned/preferred terms, spelling variant, readability ceiling).
produces: A .vale.ini config, a reusable house-style package under styles/, and per-line lint results (CLI table, JSON, or CI failures).
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Editorial Style Linter (Vale)

Turn a subjective "does this follow our style guide?" into a deterministic, versioned check.
[Vale](https://vale.sh) (errata-ai/vale, MIT) lints prose against YAML rules: banned terms,
US→UK swaps, wordiness, capitalisation, and readability. Same input → same output, every time.
Brand *voice* stays qualitative; this handles the mechanical, gate-able 80%.

## When to use

Reach for this the moment "style" needs to be repeatable — a CI gate, a pre-commit hook, or
consistent feedback for every writer. If the judgement is subjective (tone, wit, persuasion),
this is the wrong tool; do a human read instead.

## Prerequisites

- **Vale binary** — a single static Go executable, no runtime. macOS here has no Homebrew, so
  install from the GitHub release archive (steps below). Verify with `vale --version`.
- **A StylesPath** — a `styles/` directory named in `.vale.ini` where packages and your rules live.
- **Network for `vale sync`** — only needed once to download packages (Google, proselint,
  write-good). Your own rules need no network.
- Vale lints markup-aware: Markdown, HTML, AsciiDoc, reStructuredText, plain text, and code
  comments. It does **not** read binary .docx/.pptx — export to Markdown/text first.

## Install (macOS, no Homebrew)

```bash
# Pick the arch: arm64 (Apple Silicon) or 64-bit (Intel). Check latest tag first.
VER=$(curl -fsSL https://api.github.com/repos/errata-ai/vale/releases/latest | grep -m1 tag_name | cut -d'"' -f4 | tr -d v)
ARCH=$([ "$(uname -m)" = arm64 ] && echo arm64 || echo 64-bit)
curl -fsSL -o /tmp/vale.tar.gz \
  "https://github.com/errata-ai/vale/releases/download/v${VER}/vale_${VER}_macOS_${ARCH}.tar.gz"
mkdir -p ~/bin && tar -xzf /tmp/vale.tar.gz -C ~/bin vale
export PATH="$HOME/bin:$PATH"   # add to ~/.zshrc to persist
vale --version
```

## Recipe 1 — Scaffold a house style in one command

The bundled helper writes a working `.vale.ini` plus a starter package (banned words,
UK-spelling swaps, readability ceiling) so you can edit rather than start from a blank file.

```bash
bash scripts/scaffold-vale.sh . VCCP   # TARGET_DIR, STYLE_NAME
vale sync                              # downloads the Packages listed in .vale.ini
vale README.md                         # lint a file
```

`.vale.ini` is INI-format. Key lines:

```ini
StylesPath = styles          # where rules + synced packages live
MinAlertLevel = suggestion   # suggestion | warning | error — floor for what's shown
Packages = Google, proselint, write-good

[*.{md,txt,html}]            # glob → which styles apply to which files
BasedOnStyles = Vale, Google, VCCP
Google.Headings = NO         # disable a single upstream rule you disagree with
VCCP.Banned = error          # or bump one rule's level
```

## Recipe 2 — Write your own rules

Rules are `.yml` files (never `.yaml`) inside `styles/<StyleName>/`. The rule name is the
filename, so `styles/VCCP/Banned.yml` reports as `VCCP.Banned`.

**Preferred terms + UK spelling (`substitution`)** — left side is regex, right is the fix.
`%s` in the message is filled with the matched/suggested text:

```yaml
extends: substitution
message: "Prefer '%s' over '%s'."
level: warning
ignorecase: true
swap:
  utili(s|z)e: use
  in order to: to
  e-mail: email
  organiz(e|ation): organis$1   # $1 back-references the capture group
```

**Hard-banned words (`existence`)** — flags any match, no suggestion:

```yaml
extends: existence
message: "Avoid '%s'."
level: error
ignorecase: true
tokens:
  - very
  - synergy
  - low-hanging fruit
```

**Readability ceiling (`metric`)** — Flesch-Kincaid grade level, fail above 10:

```yaml
extends: metric
message: "Keep the grade level (%s) below 10."
formula: |
  (0.39 * (words / sentences)) + (11.8 * (syllables / words)) - 15.59
condition: "> 10"
```

Other useful `extends` values: `repetition` ("the the"), `consistency` (pick one of
two spellings and stick to it), `capitalization` (heading/brand casing, `match: $title`),
`occurrence` (limit passive/adverb density), and `spelling` (Hunspell dictionary + custom
`filters`/vocab). Every rule needs `extends` and `message`; `level` and `scope`
(e.g. `heading`, `sentence`, `raw`) are optional.

## Recipe 3 — Run it, and gate CI on it

```bash
vale docs/                       # lint a whole tree
vale --output=JSON post.md       # machine-readable for tooling
vale --no-exit --output=line .   # print but always exit 0 (report-only)
vale --minAlertLevel=error .     # only fail on errors, ignore suggestions
vale ls-config                   # dump the resolved config (debug what's active)
```

Vale exits non-zero when it finds an alert at/above `MinAlertLevel`, so a bare `vale .`
is already a CI gate. In GitHub Actions, `errata-ai/vale-action` posts inline PR comments;
or run the binary directly and let the exit code fail the job. For a local guardrail, drop
`vale --minAlertLevel=error $(git diff --cached --name-only)` into a pre-commit hook.

## Verify

```bash
vale --version                                  # binary installed & on PATH
printf 'We must utilise synergy in order to win.\n' > /tmp/t.md
vale /tmp/t.md                                  # expect: utilise→use, synergy banned, in order to→to
vale ls-config | grep -A2 BasedOnStyles         # confirm your style is active for the glob
```

A correctly wired setup flags all three issues in that one sentence. If it flags nothing,
your `.vale.ini` glob probably doesn't match the file extension, or you skipped `vale sync`.

## Pitfalls

- **`.yaml` files are silently ignored** — rule files MUST end in `.yml`.
- **Forgot `vale sync`** — packages listed in `.vale.ini` won't exist until synced; Vale
  warns about the missing style and skips it rather than erroring loudly.
- **Glob mismatch** — `[*.md]` won't lint a `.markdown` or `.txt` file. Use
  `[*.{md,markdown,txt}]`. Debug with `vale ls-config`.
- **StylesPath is relative to `.vale.ini`**, not your shell's CWD — run Vale from the repo
  root or point `--config` at the file.
- **`substitution` left side is regex** — unescaped `.`/`(`/`?` will over-match. Anchor or
  escape when you mean a literal.
- **Binary formats aren't supported** — convert `.docx`/`.pptx`/PDF to Markdown or text first
  (use the docx/pptx/pdf skills), then lint the export.
- **Readability is a heuristic** — Flesch-Kincaid is a proxy, not truth. Set the ceiling to
  match your audience (marketing ≈ 8, technical docs ≈ 12) and treat it as `suggestion`, not `error`.
- **This is not brand voice** — don't try to encode "sounds premium" in Vale. Encode the
  mechanical rules; keep tone as a human review step.
