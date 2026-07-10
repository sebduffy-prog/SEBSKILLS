---
name: skill-auditor
category: meta-router
description: >
  Audit a SEBSKILLS skill for both correctness AND whether it actually works — a STATIC pass (all 10 frontmatter
  fields present, name==folder, 8-20 real keywords, disambiguating when_not_to_use, no fabricated flags/APIs
  versus the cited source) and a WORKS pass (probe the required dependency/API key, then smoke-test the skill's own
  commands on a tiny fixture) — returning a per-skill verdict of works / needs-setup / broken. Use this whenever
  someone says "audit this skill", "does this skill actually work", "check my skills", "is this SKILL.md valid",
  "review the skill library", or before a skill is added or shipped. Reach for it as the gate on every new skill.
when_to_use:
  - Before adding a new skill to the library (run by skill-adder)
  - Verifying that a batch of just-authored skills actually work, not just parse
  - Checking a SKILL.md for frontmatter completeness and router-readiness
  - Distinguishing "broken skill" from "works but needs a dependency/key installed"
when_not_to_use:
  - Authoring a brand-new skill from scratch → use skill-creator
  - The guarded intake pipeline that registers a skill after audit → use skill-adder
  - Generating the library manifest / linting frontmatter across the whole repo → use build-manifest (scripts/)
  - Finding which skill to use for a task → use automatic-skill-decision
keywords: [skill audit, skill-auditor, works check, smoke test, frontmatter lint, validate skill, does it work, skill review, dependency probe, fabricated flag, skill quality, router-ready, verify skill]
similar_to: [skill-adder, skill-creator, skill-gap-detector, verification-before-completion, automatic-skill-decision]
inputs_needed:
  - The path to the skill directory / SKILL.md to audit (or a list of them)
  - Whether to run the works-check (needs a shell) or static-only
  - Any API keys/fixtures available for the works-check
produces: A per-skill audit report — static PASS/FAIL by field + a works verdict (works / needs-setup / broken) with the failing command
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Skill auditor

Two audits in one: does the skill **parse and rank** (static), and does it **actually run** (works). This is the
gate every new skill passes before it's trusted — the honest answer to "will they work".

## When to use

On any new or changed skill, and across a batch after authoring. `skill-adder` calls this as its merge gate.

## Static audit (always)

For each `SKILL.md`:

1. **Frontmatter completeness** — all 10 required fields present and non-empty (`similar_to` may be `[]`):
   `name, category, description, when_to_use, when_not_to_use, keywords, similar_to, inputs_needed, produces,
   status`. (`owner`/`updated` are allowed extras, not errors.)
2. **name == folder name**, unique across the library.
3. **category == parent folder** and in the canonical set.
4. **keywords**: 8-20, lowercase, no dupes — the field the router leans on hardest.
5. **when_not_to_use** actually disambiguates (each line names an alternative skill).
6. **description**: 120-800 chars, verb-first, no `[[wikilinks]]`.
7. **No fabricated flags/APIs** — spot-check the commands/flags/APIs in the body against the cited source
   (`sources`/links). Flag any invented flag, wrong package name, or API that doesn't exist.

```bash
# static frontmatter check for one skill
f="$1"; req="name category description when_to_use when_not_to_use keywords similar_to inputs_needed produces status"
for k in $req; do grep -q "^$k:" "$f" || echo "MISSING: $k"; done
kw=$(grep -c '^  - ' <(awk '/^keywords:/{f=1;next}/^[a-z_]+:/{f=0}f' "$f")) # or count inline [a,b,...]
```

## Works audit (when a shell is available)

The point of difference — actually exercise the skill:

1. **Dependency probe** — parse `Prerequisites` for required tools/packages/keys and check presence:
   `command -v <tool>`, `python3 -c "import <pkg>"`, `[ -n "$SOME_API_KEY" ]`. Record what's missing.
2. **Smoke-test the skill's own commands** — pull the first runnable command/snippet from the body and run it on
   a **tiny fixture** the auditor creates (e.g. a 1-second test clip for a video skill, a 3-row CSV for a data
   skill, a throwaway file for a codemod). Confirm it produces the expected artifact.
3. **Verdict:**
   - **works** — dependency present + smoke-test produced the artifact.
   - **needs-setup** — code is correct but a dependency/API key is absent (install/set and it works).
   - **broken** — dependency present but the command errors, or output is wrong / a flag is fabricated.

```bash
# example works-check pattern for a media skill
FF=$(python3 -c "import imageio_ffmpeg as m;print(m.get_ffmpeg_exe())" 2>/dev/null) \
  && "$FF" -f lavfi -i testsrc=size=64x64:duration=1 -y /tmp/_fix.mp4 2>/dev/null \
  && echo "dep OK, fixture made" || echo "needs-setup: ffmpeg"
# then run the skill's actual recipe against /tmp/_fix.mp4 and check the output exists
```

Match the fixture to the skill's domain — never smoke-test with the user's real data, and never run destructive
commands (deletes, deploys, network writes) during an audit.

## Batch mode

Run static across every skill, works-check the ones with a shell-runnable recipe, and emit a table:
`skill · static PASS/FAIL · works verdict · note`. Sort broken first.

## Verify

- On a known-good skill (e.g. `ffmpeg-cookbook`) → static PASS, works = works (GIF recipe runs).
- On a skill missing a field → static FAIL naming the field.
- On a skill needing an uninstalled package → works = needs-setup (not broken).

## Pitfalls

- **needs-setup ≠ broken** — don't fail a correct skill just because a heavy dep isn't installed; say so.
- **Never run destructive or networked commands** in the works-check — sandbox to a fixture.
- **The lint standard is the 10 fields** — do not invent extra required keys (a common auditor error); `owner`/`updated`/`status` beyond the 10 are fine.
- Static-only is valid where no shell exists (Desktop/Web) — report that the works-check was skipped, don't claim it passed.
