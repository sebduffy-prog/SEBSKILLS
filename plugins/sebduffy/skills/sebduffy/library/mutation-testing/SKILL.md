---
name: mutation-testing
category: engineering-workflow
description: >-
  Measure the REAL quality of a test suite by injecting mutants (flip `>` to `>=`, `+` to `-`,
  delete a return) and checking whether tests catch them. Line coverage lies — code can be 100%
  covered yet assert nothing; mutation testing exposes exactly that. Produces a mutation score
  plus a surviving-mutant list that names the weak assertions to fix. Covers Stryker (JS/TS),
  PIT (Java/JVM), and mutmut (Python): install, config, scoped incremental runs, and reading
  the report. Reach for this when coverage is green but bugs still ship.
when_to_use:
  - Coverage is high (80-100%) yet regressions keep slipping through, and you suspect the tests assert little
  - You want an objective quality gate on a critical module (payments, auth, pricing) beyond line coverage
  - Reviewing a PR that adds tests and you want proof the new tests actually detect faults, not just execute lines
  - Hardening a library or algorithm where a single flipped operator would be a real bug
  - Setting a CI threshold that fails when test effectiveness (not just coverage) drops
when_not_to_use:
  - You only need which lines executed, fast, every commit — use plain line/branch coverage (nyc, jacoco, coverage.py)
  - The suite is slow or flaky — fix flakiness and runtime first; mutation runs the suite N times and will be brutal
  - You want static bug-finding without running tests — use a linter/type-checker or `security-review`
  - Whole-repo scan on a huge codebase in one shot — scope to changed files first (see incremental recipes) or it runs for hours
keywords:
  - mutation-testing
  - mutation-score
  - stryker
  - pitest
  - pit
  - mutmut
  - surviving-mutant
  - test-quality
  - coverage-lies
  - assertion-gap
  - killed-mutant
  - quality-gate
  - test-effectiveness
  - jest
  - vitest
similar_to:
  - test-driven-development
  - verification-before-completion
  - repo-context-packer
  - tdd-workflow
inputs_needed: A project with a passing, non-flaky test suite and its runner (Jest/Vitest/Mocha, JUnit+Maven/Gradle, or pytest); a scope of files/classes to mutate.
produces: A mutation score (% mutants killed), an HTML/terminal report, and a ranked list of surviving mutants pinpointing weak or missing assertions.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Mutation Testing

## When to use

Line coverage answers "did a test *execute* this line?" Mutation testing answers the
question that actually matters: "would a test *fail* if this line were wrong?" A tool
makes tiny faulty edits — **mutants** — to your source (change `a + b` to `a - b`, `>` to
`>=`, `true` to `false`, delete a `return`), then reruns your suite against each one.

- Mutant **killed** = at least one test failed → your tests caught the fault. Good.
- Mutant **survived** = all tests still passed → a real bug in that spot would ship silently.
- **No coverage** = no test even ran the mutated line. **Timeout** = mutant caused an infinite loop (counts as killed).

**Mutation score = killed / (total valid mutants)**. Surviving mutants are your worklist:
each one names a line where an assertion is missing or too loose.

## Prerequisites

- **The suite must be green and non-flaky before you start.** Mutation runs it hundreds of
  times; one flaky test poisons the whole score. Run it 3x clean first.
- **It is slow by design** — roughly `suite_runtime x mutant_count`. Always scope to a module
  or changed files (recipes below). Never point it at a whole large repo on the first run.
- Tooling by ecosystem (all real, current):
  - **JS/TS** → Stryker, `npm init stryker@latest`. Needs Node 18+.
  - **Java/JVM** → PIT (pitest), a Maven/Gradle plugin. Needs JDK + Maven/Gradle.
  - **Python** → mutmut, `pip install mutmut`. (Note: this Mac's `python3` is 3.9 — check mutmut's supported versions in a venv.)
  - Others: `go-mutesting`/`gremlins` (Go), `cargo-mutants` (Rust), `Stryker.NET` (C#), `infection` (PHP). Same mental model.

## Recipe A — Stryker (JavaScript / TypeScript)

```bash
# 1. Scaffold config (interactive: pick your runner — jest, vitest, mocha, etc.)
npm init stryker@latest
# writes stryker.config.mjs and installs @stryker-mutator/core + the runner plugin
```

Minimal `stryker.config.mjs` (scope tightly with `mutate`):

```js
/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
export default {
  testRunner: 'vitest',            // or 'jest' / 'mocha' — needs @stryker-mutator/<runner>-runner
  reporters: ['html', 'clear-text', 'progress'],
  coverageAnalysis: 'perTest',     // big speedup: only run tests that cover each mutant
  mutate: ['src/pricing/**/*.ts', '!src/**/*.test.ts'],  // scope! not the whole repo
  thresholds: { high: 80, low: 60, break: 70 },          // break => exit 1 below 70%
  incremental: true,               // reuse prior results; only re-mutate changed code
};
```

```bash
npx stryker run                    # run it
npx stryker run --logLevel trace   # when it misbehaves / can't find tests
```

- Report: `reports/mutation/mutation.html` (open in a browser) plus a terminal summary.
- `break` is the CI gate: score below it exits non-zero. `high`/`low` only colour the report.
- Scope one PR's changes: set `mutate` to the changed files, e.g.
  `mutate: $(git diff --name-only main... | grep '\.ts$')` fed in via a small wrapper, or just
  edit the array. Combine with `incremental: true` so unchanged code is skipped.

## Recipe B — PIT / pitest (Java, Maven)

No config file needed to start — configure in `pom.xml` under the plugin, or pass `-D` flags:

```bash
# Compile then mutate. Scope with targetClasses so it doesn't mutate the world.
mvn test-compile org.pitest:pitest-maven:mutationCoverage \
  -DtargetClasses='com.acme.pricing.*' \
  -DtargetTests='com.acme.pricing.*Test' \
  -DmutationThreshold=75          # build fails (exit 1) below 75%
```

`pom.xml` for a repeatable setup:

```xml
<plugin>
  <groupId>org.pitest</groupId>
  <artifactId>pitest-maven</artifactId>
  <version>1.16.1</version>
  <configuration>
    <targetClasses><param>com.acme.pricing.*</param></targetClasses>
    <targetTests><param>com.acme.pricing.*Test</param></targetTests>
    <mutationThreshold>75</mutationThreshold>
    <threads>4</threads>
    <outputFormats><param>HTML</param><param>XML</param></outputFormats>
  </configuration>
</plugin>
```

- HTML report lands in `target/pit-reports/<timestamp>/index.html`.
- For changed-code-only runs use the **pitest-git / scmMutationCoverage** goal (`arcmutate`/`pitest-git-plugin`)
  or feed a class list from `git diff` into `targetClasses`. Gradle users: the `info.solidsoft.pitest` plugin, task `./gradlew pitest`.
- Bump `threads` to cut wall-clock; PIT already skips mutants with no covering test.

## Recipe C — mutmut (Python)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install mutmut
mutmut run                 # auto-discovers tests in tests/ or test/ and the source to mutate
mutmut browse              # interactive TUI: inspect survivors; press 'r' to retest after edits
mutmut results            # plain list of mutant ids + status for scripting/CI
mutmut show <id>           # diff of a single surviving mutant
```

- Scope explicitly instead of scanning everything:
  `mutmut run --paths-to-mutate src/pricing/`.
- It is incremental by default — it remembers prior work and resumes, so re-runs after adding
  tests are fast. `mutmut apply <id>` writes a mutant to disk (commit/stash first — it edits source).

## Verify

You have used it correctly when all of these hold:

1. **Baseline is clean:** the tool's initial full-suite run passes with zero failures/flakes
   before any mutant is introduced. If the baseline is red, the score is garbage — stop and fix tests.
2. **You get a numeric score and a survivor list**, not just a pass/fail. Open the HTML report.
3. **Spot-check one survivor:** read the mutant's diff, confirm you understand *why* no test caught
   it, add/strengthen an assertion, rerun that scope, and watch the mutant flip to killed and the
   score rise. That loop is the whole point.
4. **CI gate works:** with `break`/`mutationThreshold` set, artificially weakening a test drops the
   score below threshold and the command exits non-zero.

## Pitfalls

- **Coverage != mutation score.** 100% line coverage with a 40% mutation score is common and means
  your tests run code without checking its output. That gap is the finding — report it.
- **Equivalent mutants.** Some mutants are semantically identical to the original (e.g. `<` vs `<=`
  on a bound that's never hit), so they can *never* be killed. Don't chase 100%; a small residue of
  survivors is expected. Mark/ignore them rather than writing contrived tests.
- **Never chase the score by deleting or loosening tests.** The only valid way to raise it is
  stronger assertions. A rising score from weaker tests is fraud against yourself.
- **Flaky suite = meaningless run.** A test that fails 1-in-20 will "kill" mutants at random,
  inflating the score and wasting hours. Gate on flakiness first.
- **Runtime explodes without scoping.** `mutate`/`targetClasses`/`--paths-to-mutate` and per-test
  coverage analysis are mandatory on anything non-trivial. Start with one module, not the repo.
- **Don't gate raw CI on it every commit** unless the suite is fast — run it on a nightly job or on
  changed files per-PR (incremental). It complements, never replaces, unit tests and line coverage.
- **Mutmut and `mutmut apply` edit real source files.** Only run with a clean git tree so you can revert.
- **Timeouts count as killed** — an infinite-loop mutant is caught. Don't be alarmed by a "timeout" tally.
