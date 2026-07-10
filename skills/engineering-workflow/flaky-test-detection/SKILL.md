---
name: flaky-test-detection
category: engineering-workflow
description: >-
  Catch, quarantine, and root-cause flaky tests — the ones that pass and fail on IDENTICAL code and
  poison CI trust. Rerun-and-compare to prove a test is non-deterministic (not a real regression),
  then isolate it: pytest-rerunfailures (--reruns / @pytest.mark.flaky) and Jest jest.retryTimes with
  logErrorsBeforeRetry, plus a language-agnostic flake_scan.sh that runs any command N times and
  reports the pass/fail ratio. Covers the common root causes (test order, time/timezone, async races,
  shared state, network) and how to quarantine without deleting coverage. Reach for this the moment
  "re-run the pipeline and it goes green" enters the conversation.
when_to_use:
  - A test passes locally but fails intermittently in CI, or a re-run of the same pipeline flips red to green
  - You need to PROVE a failure is flakiness (non-deterministic) versus a genuine regression before merging
  - CI is red often enough that people re-run by reflex and stop trusting the suite
  - You want to quarantine a known-flaky test so it stops blocking merges without losing its coverage
  - Root-causing WHY a test flakes — order dependence, time/timezone, async races, shared/global state, network
  - Adding bounded retries (pytest --reruns, jest.retryTimes) as a stopgap while the real fix is scheduled
when_not_to_use:
  - The test fails deterministically every run — that is a real bug; use `systematic-debugging` instead
  - Coverage is green but you doubt the assertions catch anything — use `mutation-testing`, not flake hunting
  - You are writing new tests from scratch — use `test-driven-development` / `tdd-workflow`
  - The whole suite is just slow, not flaky — profile and parallelize, don't rerun-loop it
keywords:
  - flaky-test
  - flaky-test-detection
  - rerun
  - quarantine
  - pytest-rerunfailures
  - jest-retrytimes
  - non-deterministic
  - test-order-dependence
  - race-condition
  - ci-reliability
  - suite-reliability
  - retryTimes
  - reruns
  - randomly-failing
  - test-isolation
similar_to:
  - mutation-testing
  - systematic-debugging
  - test-driven-development
  - verification-before-completion
inputs_needed: The failing/suspect test's path or name, the test runner (pytest/jest/other), and access to run it repeatedly.
produces: A flaky-vs-real verdict with a pass/fail ratio, a quarantine annotation, and a ranked root-cause hypothesis with the fix.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Flaky Test Detection

A flaky test passes and fails on the **same code**. It is not a regression — it is a reliability bug in the test (or the code's determinism). The discipline: **prove** flakiness by rerunning, **quarantine** to unblock the team, **root-cause** the non-determinism, then fix and de-quarantine. Retries are a stopgap, never the destination.

## When to use

Use this when a failure does not reproduce on demand: green-on-rerun, "works on my machine", CI-only failures, or a suite people re-trigger by reflex. If the test fails every single run, it is deterministic — stop here and use `systematic-debugging`.

## Prerequisites

- The test runner installed and runnable locally or in a scratch CI job.
- **Python:** `pip install pytest-rerunfailures`. Requires **pytest 8.2+** and **Python 3.10+**. Verify: `pytest --help | grep -- --reruns`.
- **JS/TS:** Jest 27+ (`jest.retryTimes` with an options object needs Jest 29.x+). No extra install.
- `scripts/flake_scan.sh` (bundled) needs only bash — works for any runner (go test, rspec, vitest, etc.).
- Ability to run the test **many times** — flakes surface with repetition, so budget 20–50 runs.

## Recipes

### 1. Prove it — rerun and compare (runner-agnostic)

Run the suspect test in a tight loop against unchanged code. Mixed pass/fail = flaky; all-agree = deterministic.

```bash
# 20 runs; exits 1 (FLAKY) if runs disagree, 0 if they all agree
scripts/flake_scan.sh 20 pytest tests/test_checkout.py::test_total
scripts/flake_scan.sh 25 npx jest --runInBand payment.test.ts
scripts/flake_scan.sh 30 go test -run TestCheckout ./checkout
```

Failing-run logs are written to a temp dir (printed at the top) so you can diff a passing run against a failing one — the diff is your first root-cause clue.

**Surface order-dependence** (a top cause) by shuffling execution order:

```bash
pytest -p no:randomly -q            # baseline order
pytest -p randomly --randomly-seed=last   # needs pytest-randomly; reruns the failing seed
npx jest --shuffle                  # Jest 29+: randomize test order
```

If a test only fails under a particular order, it depends on state leaked by another test — that is the bug.

### 2. Quarantine — unblock the team without losing coverage

Mark the test so a flake no longer fails the build, but the test still runs (so you keep signal and can watch it).

**pytest** — retry on rerun; only the final result gates the build:

```python
import pytest

@pytest.mark.flaky(reruns=3, reruns_delay=1)
def test_payment_settles():
    ...

# Retry ONLY on the transient error you expect, so real regressions still fail fast:
@pytest.mark.flaky(reruns=5, only_rerun=["ConnectionError", "TimeoutError"])
def test_calls_gateway():
    ...
```

CLI equivalents (no code change): `pytest --reruns 3 --reruns-delay 1 --only-rerun AssertionError`. Add `--rerun-show-tracebacks` to keep every attempt's traceback for diagnosis. Prefer a **marker on the one test** over a suite-wide `--reruns` — blanket retries hide real regressions everywhere.

**Jest** — schedule retries after the suite (put in the test file or a setup file):

```javascript
// Retries this file's failed tests; log the failing error before each retry.
jest.retryTimes(3, { logErrorsBeforeRetry: true });

test('payment settles', async () => { /* ... */ });
```

`jest.retryTimes(n, { logErrorsBeforeRetry, waitBeforeRetry, retryImmediately })` — the options object requires Jest 29.x+. `logErrorsBeforeRetry: true` is essential: without it a flake retries silently and you never see why it failed.

**Tag it, don't bury it.** Track quarantined tests in one place (a `@pytest.mark.flaky` grep, a `FLAKY.md`, or a CI label) with a ticket each. A quarantine with no follow-up ticket is just deleted coverage in disguise.

### 3. Root-cause — the usual suspects

Once proven flaky, work down this ranked list. The passing-vs-failing log diff from recipe 1 usually points straight at one.

| Cause | Tell-tale sign | Fix |
|---|---|---|
| **Order / shared state** | Fails only after another test; passes in isolation; fails under `--shuffle` | Reset globals/DB/singletons in teardown; make each test set up its own state |
| **Time & timezone** | Fails near midnight, month-end, or only in CI's UTC | Freeze the clock (`freezegun`, `jest.useFakeTimers()`); never assert on `now()` |
| **Async / race** | Fails under load or parallelism; timing-sensitive | `await` the real condition; poll with a deadline; never `sleep(n)` then assert |
| **Unseeded randomness** | Fails ~1 in N runs regardless of order | Seed the RNG per test; assert on invariants, not exact random values |
| **Network / external service** | Fails on DNS/timeout/rate-limit strings | Mock the boundary; if truly integration, `only_rerun` the transient error |
| **Floating-point / ordering of collections** | Off-by-epsilon; dict/set iteration order | Assert with tolerance; sort before comparing |

Confirm the fix by rerunning recipe 1 — the verdict must flip to **DETERMINISTIC (all pass)** across the full run budget. Then remove the quarantine marker and close the ticket.

## Verify

- `bash scripts/flake_scan.sh 4 sh -c 'test $((RANDOM % 2)) -eq 0'` prints mixed PASS/FAIL and exits `1` with `VERDICT: FLAKY` — proves the detector distinguishes non-determinism.
- `pytest --help | grep -- --reruns` lists `--reruns`, `--reruns-delay`, `--only-rerun` after install.
- A fixed test scores all-PASS across the **full** run budget (20–50), not just a lucky 3.

## Pitfalls

- **Retries are not a fix.** `--reruns`/`retryTimes` green a flake but leave the non-determinism live — it will bite elsewhere (prod, a sibling test). Always file the root-cause ticket.
- **Too few reruns lie.** A 1-in-30 flake looks solid in 5 runs. Match the run budget to how rarely it fails; when unsure, use 30–50.
- **Suite-wide `--reruns` masks real regressions.** A genuinely broken test that fails then passes on a retry ships a bug. Scope retries to specific tests and specific transient errors (`only_rerun`).
- **Blank `only_rerun` retries everything**, including assertion failures that are real. Name the transient exception classes.
- **Parallel runners hide and cause flakes.** `pytest-xdist -n` changes ordering and shared-resource contention; reproduce both with and without `-n`. (pytest-rerunfailures needs xdist ≥ 2.3.0 for crash recovery.)
- **`jest.retryTimes` without `logErrorsBeforeRetry: true`** swallows the failing error — you retry blind and lose the one clue you needed.
- **Deleting the test is not quarantining.** Skipping/deleting drops coverage silently; quarantine keeps it running and visible so it gets fixed.
