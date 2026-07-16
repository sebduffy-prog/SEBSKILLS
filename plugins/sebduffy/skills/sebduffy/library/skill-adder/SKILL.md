---
name: skill-adder
category: meta-router
description: >
  Contribute a NEW skill into the SEBSKILLS library through a guarded, gated intake — a
  "PR-merge for skills". Capture intent + category, draft via skill-creator, run a static
  audit (10 fields, keywords 8-20, name == folder, no fabricated flags, disambiguation),
  works-check the skill's own commands on a fixture, stamp the standard, preserve any upstream
  license, and ONLY on a clean PASS register it into the category README + root index. Use when
  someone says "add this to my skills", "register a new skill", "intake this", or hands you a
  draft SKILL.md to land safely. Nothing lands unaudited.
when_to_use:
  - Someone hands you a finished or draft SKILL.md and wants it landed in the library correctly
  - You just authored a skill and need to register it (README rows, index, manifest) without breaking conventions
  - A contributor is porting an upstream skill and you must preserve its license while conforming it
  - You want a repeatable intake gate so half-baked or mis-triggering skills never get registered
  - skill-gap-detector proposed a new capability and you're taking it from draft to merged
when_not_to_use:
  - You need to DECIDE which existing skill handles a request — use automatic-skill-decision instead
  - No skill exists yet and you're only detecting the gap — use skill-gap-detector first
  - You're authoring/iterating the skill's content itself (drafts, evals, description tuning) — use skill-creator
  - You just want to audit an already-registered skill's quality with no intent to add — run the static/works checks directly, not this intake
keywords: [skill intake, register skill, add skill, skill contribution, pr merge for skills, skill audit, static audit, works check, frontmatter standard, manifest, category readme, root index, license preservation, quality gate, skill-creator handoff, meta router, skill onboarding, guarded pipeline]
similar_to: [skill-creator, skill-gap-detector, automatic-skill-decision, skill-chaining-composer, requirement-elicitation]
inputs_needed:
  - The skill's intent (what it does + trigger phrases) OR an existing draft SKILL.md path
  - A target category under skills/ (one of the existing category folders, or a justified new one)
  - Write access to the SEBSKILLS repo root (default /Users/seb.duffy/Documents/GitHub/SEBSKILLS)
  - Any upstream source URL + license if the skill is ported, so attribution is preserved
produces: A registered skill folder (SKILL.md + optional assets) plus updated category README row, root README index row, and a PASS/HALT audit report — or a halt at the first failed gate with nothing written.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Skill Adder

A guarded intake pipeline that lands a new skill into SEBSKILLS the way a reviewed PR
lands code: six stages, each a checkpoint that can **HALT before anything is written**.
The library only grows through this gate, so a mis-triggering, unaudited, or
convention-breaking skill can never silently ship.

## When to use

Reach for this once the *content* of a skill exists or is about to (from `skill-creator`
or a `skill-gap-detector` proposal) and the job is now to **land it safely**. It is the
merge step, not the authoring step — see `skill-creator` for the write/iterate loop.

## Prerequisites

- Repo root writable. Default: `/Users/seb.duffy/Documents/GitHub/SEBSKILLS`.
- `python3` (macOS system 3.9 is fine — the audit helper is dependency-free).
- The static-audit helper: `scripts/audit_static.py` (bundled with this skill).
- Know the registration surface for THIS repo: root `README.md` quick index + each
  category's `README.md`, plus the generated artifacts — root `manifest.json`, `CATALOG.md`,
  `REPORT.md`, and the `/sebduffy` router index — rebuilt by `python3 scripts/build_manifest.py`
  (never hand-edited; `--check` is the CI gate).

## Mechanism / Steps

Run the stages in order. **Do not advance past a HALT.** Write nothing to shared files
until Stage 5.

### Stage 0 — Capture intent + target category (checkpoint: scope agreed)
- Restate in one line: what the skill does, the phrases that should trigger it, what it produces.
- Pick a category folder under `skills/` (`ls skills/`). Reuse an existing one where it fits
  (see the CONTRIBUTING "Categorization rule of thumb"); only mint a new category with a reason.
- Derive the kebab-case `name` and confirm `skills/<category>/<name>/` does not already exist:
  ```bash
  test -e skills/<category>/<name> && echo "HALT: name taken" || echo "free"
  ```
- **HALT** if intent is vague or the name collides. (Vague brief → `requirement-elicitation`.)

### Stage 1 — Draft via skill-creator (checkpoint: draft exists in a scratch path)
- Hand the intent to `skill-creator` to produce the SKILL.md **in a scratch location**
  (e.g. the session scratchpad), NOT yet under `skills/`. Nothing is registered by drafting.
- If a draft was supplied, skip authoring and take that file as the candidate.
- **HALT** if no coherent draft comes back.

### Stage 2 — Static audit (checkpoint: zero BLOCK findings)
Run the bundled checker on the candidate file:
```bash
python3 skills/meta-router/skill-adder/scripts/audit_static.py <path/to/candidate/SKILL.md>
```
It enforces the library standard and exits non-zero on any BLOCK:
- all 10 frontmatter fields present + non-empty (`similar_to` may be `[]`),
- `name` == folder, `description` 120–800 chars with no `[[wikilinks]]`,
- `keywords` 8–20, `when_to_use` 3–7, `when_not_to_use` 2–5,
- each `when_not_to_use` names an alternative (disambiguation), `status: stable`,
- it also prints every `--flag` in the body as an `INFO` list to verify in Stage 3
  (this is how "no fabricated flags" gets caught — an unverifiable flag is a HALT there).
- **HALT** on FAIL. Send fixes back to Stage 1; do not hand-patch around the gate.

### Stage 3 — Works-check (checkpoint: the skill's own commands actually run)
Prove the skill is buildable, not just well-formed:
- **Dependency probe** — for each tool/CLI/library the body assumes, confirm it exists
  (`command -v <tool>`, `python3 -c "import x"`, `gh --version`). Missing dep on macOS
  (no brew) is a HALT unless the skill degrades gracefully and says so.
- **Flag verification** — for every `--flag` the Stage-2 INFO listed, confirm it is real
  (`<tool> --help | grep -- --flag`, or the vendor docs via WebFetch). A fabricated flag is a HALT.
- **Smoke-test on a fixture** — run any `scripts/` the skill ships against a tiny throwaway
  input in the scratchpad and assert a clean exit / expected output. If the skill has no
  runnable command, exercise its core instruction on one worked example instead.
- **HALT** on any failure. A skill that can't run its own recipe does not land.

### Stage 4 — Stamp frontmatter + preserve license (checkpoint: conformed in place)
- Set `owner`, today's `updated`, `status: stable`; normalise `similar_to` to real sibling
  names in the same category; re-run Stage 2 to confirm still-PASS after edits.
- If ported: keep the upstream `LICENSE`/attribution file in the skill folder and add a
  one-line provenance note ("Ported from <url> under <license>") near the top of the body.
  Stripping a source license is a HALT.

### Stage 5 — Register (checkpoint: indexes updated + build check clean)
Only now touch shared files. Move the candidate into place, then register it:
```bash
mkdir -p skills/<category>/<name>
mv <scratch>/SKILL.md skills/<category>/<name>/SKILL.md   # + any assets/ scripts/
```
- Add a row to the category `README.md` (create it if missing) and to the **root**
  `README.md` quick index, matching the existing `| [`name`](skills/cat/name) | use… |` format.
- Regenerate the generated artifacts: `python3 scripts/build_manifest.py`, then verify with
  `python3 scripts/build_manifest.py --check` (the CI gate — non-zero exit on any staleness).
  Commit the regenerated `manifest.json`/`CATALOG.md`/`REPORT.md` and the router splice
  alongside the skill.
- Commit as a reviewed unit: `feat: add <name> skill (<category>)`.

## Verify

- `python3 skills/meta-router/skill-adder/scripts/audit_static.py skills/<category>/<name>/SKILL.md`
  prints `PASS` and exits 0.
- The new name resolves in BOTH indexes:
  ```bash
  grep -rl "skills/<category>/<name>" README.md skills/<category>/README.md
  ```
- The skill's own smoke-test (Stage 3) still exits clean from the registered path.
- `git status` shows exactly: the new skill folder + the two README edits + the regenerated
  `manifest.json`/`CATALOG.md`/`REPORT.md`/router splice — nothing stray.

## Pitfalls

- **Registering before auditing.** The whole point is order: no README/manifest edit before a
  clean Stage 2 AND Stage 3. If you find yourself editing indexes mid-pipeline, you skipped a gate.
- **Well-formed but non-functional.** Static PASS is necessary, not sufficient — a skill can have
  perfect frontmatter and a fabricated `--flag`. Stage 3 is what stops that.
- **Hand-patching past the checker.** Fixes go back through `skill-creator` (Stage 1) so the draft
  and the landed file never diverge. Silencing a BLOCK by editing the checker is cheating the gate.
- **Losing the license.** Ported skills must keep upstream attribution; a merge that drops it is a HALT,
  not a cleanup.
- **Hand-editing generated files.** `manifest.json`/`CATALOG.md`/`REPORT.md` and the router index
  are outputs of `python3 scripts/build_manifest.py` — regenerate, never patch them by hand, and
  let `--check` confirm nothing is stale.
- **New category sprawl.** Prefer an existing category; a one-off new folder fragments the index. Justify it.
