---
name: property-based-testing
category: engineering-workflow
description: >-
  Stop hand-picking example inputs — assert PROPERTIES ("output is always sorted", "decode(encode(x))==x")
  and let a generator hurl hundreds of adversarial cases at them, then auto-SHRINK any failure to a minimal
  counterexample for the bug report. Covers Hypothesis (Python) and fast-check (JS/TS): writing generators,
  preconditions, seed replay, and STATEFUL/model-based testing that finds ordering bugs example tests never
  reach. Reach for it on parsers, encoders, math, data structures, and any round-trip or invariant. Ships a
  zero-dependency demo of the generate-then-shrink loop.
when_to_use:
  - You keep writing example-based tests and suspect edge cases (empty, negative, unicode, huge, duplicate) are slipping through
  - Testing a round-trip — serialize/parse, encode/decode, compress/decompress, save/load — where decode(encode(x)) must equal x
  - Verifying an invariant that must hold for ALL inputs (sorted output stays sorted, balance never negative, idempotency, commutativity)
  - A stateful system (cache, queue, state machine, CRUD store) where a specific SEQUENCE of operations triggers bugs
  - You want a reproducible minimal counterexample instead of a giant random failing input
  - Hardening a parser, validator, pricing/math routine, or data-structure library against the whole input space
when_not_to_use:
  - You need to prove existing tests actually assert something — use mutation-testing to score suite quality, not generate inputs
  - You are doing the red-green-refactor loop for a single concrete feature — use test-driven-development / tdd-workflow first
  - The function has heavy external side effects (network, real DB) with no pure core — extract a pure unit first, then apply this
  - You only need one specific regression case reproduced — write a plain example test, not a generator
keywords:
  - property-based-testing
  - hypothesis
  - fast-check
  - fuzzing
  - generative-testing
  - shrinking
  - counterexample
  - stateful-testing
  - model-based-testing
  - invariants
  - round-trip
  - arbitraries
  - strategies
  - quickcheck
  - edge-cases
similar_to:
  - mutation-testing
  - test-driven-development
  - tdd-workflow
  - systematic-debugging
  - verification-loop
inputs_needed: A pure-ish function or stateful component to test, its runtime (Python or JS/TS), and at least one property/invariant it must always satisfy.
produces: Property tests (Hypothesis or fast-check) that generate hundreds of cases, plus minimal shrunk counterexamples and a reproducible seed for any failure.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Property-Based Testing (Hypothesis + fast-check)

Example tests check the inputs *you* thought of. Property-based testing (PBT) checks a **property** against inputs a generator invents — hundreds per run, deliberately including the nasty ones (0, -1, empty, NaN, `"\0"`, huge, duplicated). When a case fails, the framework **shrinks** it to the smallest input that still fails, so you get `[1, 0]` in a bug report, not a random 400-element array.

## When to use

Reach for PBT when you can name a rule that must hold for *every* input. The four workhorse property shapes:

- **Round-trip / inverse**: `decode(encode(x)) == x`, `parse(render(x)) == x`, `load(save(x)) == x`.
- **Invariant**: output is always sorted; a balance is never negative; length is preserved; the result is idempotent.
- **Oracle / model**: your fast implementation agrees with a slow-but-obviously-correct reference (`myMax(xs) == max(xs)`).
- **Metamorphic**: `sort(xs) == sort(shuffle(xs))`; `f(x)+f(y) == f(x+y)`; adding an item then removing it is a no-op.

## Prerequisites

- **Python**: `pip install hypothesis` (6.x). Pairs with pytest/unittest. Optional extras: `hypothesis[numpy]`, `hypothesis[pandas]`.
- **JS/TS**: `npm i -D fast-check` (4.x). Works with Jest, Vitest, Mocha, node:test. Optional `@fast-check/vitest` / `@fast-check/jest` wrappers add a `test.prop` helper.
- On this Mac (no brew, python3 = 3.9): Hypothesis 6.x supports 3.9. If you can't install anything, the bundled `scripts/mini_pbt.py` runs on the stdlib and demonstrates the generate-then-shrink loop.

## Recipe 1 — Python / Hypothesis

```python
from hypothesis import given, settings, assume, example
from hypothesis import strategies as st

# Round-trip: JSON survives a save/load cycle.
@given(st.dictionaries(st.text(), st.integers()))
def test_json_roundtrip(d):
    import json
    assert json.loads(json.dumps(d)) == d

# Invariant + oracle: our sort matches sorted(), output is ordered.
@given(st.lists(st.integers()))
def test_mysort_matches_builtin(xs):
    out = mysort(xs)
    assert out == sorted(xs)
    assert all(out[i] <= out[i + 1] for i in range(len(out) - 1))

# Preconditions with assume(); pin known-tricky cases with @example.
@example(x=0)  # always run this exact case too
@given(st.integers())
def test_reciprocal(x):
    assume(x != 0)          # discard, don't fail, on x == 0
    assert 1 / (1 / x) != 0
```

Key strategies: `st.integers(min_value=, max_value=)`, `st.floats(allow_nan=False, allow_infinity=False)`, `st.text()`, `st.lists(elem, min_size=, max_size=)`, `st.dictionaries(k, v)`, `st.sampled_from([...])`, `st.one_of(a, b)`, `st.tuples(...)`, `st.builds(MyClass, ...)`. Build custom generators with `@st.composite` or `.map()` / `.filter()` / `.flatmap()`.

Tuning and replay:

```python
@settings(max_examples=500, deadline=None)   # more cases, no per-case time limit
@given(st.text())
def test_slugify_idempotent(s): ...
```

Run with `pytest -q`. On failure Hypothesis prints `Falsifying example: test_x(xs=[0, -1])` and stores it in `.hypothesis/` — the **next run replays that exact case first**, so a fix is verified deterministically. Force a seed with `@seed(12345)` or `pytest --hypothesis-seed=12345`.

## Recipe 2 — JS/TS / fast-check

```ts
import fc from "fast-check";
import { test, expect } from "vitest";

test("array reverse is its own inverse", () => {
  fc.assert(
    fc.property(fc.array(fc.integer()), (xs) => {
      expect([...xs].reverse().reverse()).toEqual(xs);
    }),
  );
});

// Preconditions with fc.pre, and a bump to numRuns.
test("division round-trips for non-zero", () => {
  fc.assert(
    fc.property(fc.integer(), (x) => {
      fc.pre(x !== 0);
      return 1 / (1 / x) !== 0;
    }),
    { numRuns: 1000, seed: 42 },
  );
});
```

Core arbitraries: `fc.integer({min, max})`, `fc.nat()`, `fc.float()` / `fc.double({noNaN: true})`, `fc.string()`, `fc.array(arb, {minLength, maxLength})`, `fc.record({...})`, `fc.constantFrom(...vals)`, `fc.oneof(a, b)`, `fc.tuple(a, b)`, `fc.option(arb)`. Combine with `.map()`, `.filter()`, `.chain()`. For async code use `fc.asyncProperty(...)` and `await fc.assert(...)`. On failure fast-check throws with the **shrunk** counterexample plus a `seed`/`path` you paste back into `{ seed, path }` to reproduce exactly.

## Recipe 3 — Stateful / model-based testing

This is where PBT earns its keep: bugs that only appear after a *sequence* of operations. You describe commands, run them against the real system, and check each against a simple model.

fast-check:

```ts
class PushCmd implements fc.Command<Model, RealStack> {
  constructor(readonly v: number) {}
  check = () => true;
  run(m: Model, r: RealStack) { r.push(this.v); m.items.push(this.v);
    expect(r.size()).toBe(m.items.length); }
  toString = () => `push(${this.v})`;
}
// ...PopCmd similar...
fc.assert(fc.property(
  fc.commands([fc.integer().map((v) => new PushCmd(v)), fc.constant(new PopCmd())]),
  (cmds) => fc.modelRun(() => ({ model: { items: [] }, real: new RealStack() }), cmds),
));
```

Hypothesis (`RuleBasedStateMachine`): declare `@rule()`-decorated methods that mutate state, `@invariant()` checks that must always hold, and `Bundle`s to feed outputs of one rule into another. Hypothesis explores operation sequences and shrinks a failing trace to the **shortest** reproducing sequence.

## Verify

```bash
# Concept demo, no installs — shows generate → fail → shrink to minimal.
python3 scripts/mini_pbt.py
# Expect: PASS on reverse-twice; FAIL on buggy_max shrunk to a tiny case like [1, 0].

python3 -m py_compile scripts/mini_pbt.py   # syntax check

# Real suites:
pytest -q            # Hypothesis via pytest
npx vitest run       # fast-check via Vitest
```

A property is working when it (a) passes many runs on correct code and (b) fails **and shrinks to a small input** when you deliberately break the implementation. If a "passing" property never fails even against broken code, it is asserting nothing — treat that like a green mutation score of zero.

## Pitfalls

- **Trivial/tautological properties.** `assert f(x) == f(x)` always passes. Assert a relationship to something independent (an oracle, an inverse, an invariant) — not the function against itself.
- **Reimplementing the code in the test.** If your "model" is the same algorithm, both share the bug. The oracle must be *obviously* correct (slower, simpler), not a copy.
- **Over-filtering.** Heavy `assume()` / `fc.pre()` discards most inputs; Hypothesis will raise `Unsatisfied`/too-many-filtered. Generate valid data directly (`.map()` into the valid shape) instead of generating-then-rejecting.
- **Flaky = non-reproducible.** Non-determinism (real clock, network, `random` without seed, dict ordering) makes shrinking loop or lie. Inject seeds/clocks; test a pure core.
- **Unbounded floats.** `st.floats()` / `fc.float()` include `NaN` and `Infinity` by default and `NaN != NaN` breaks equality properties — pass `allow_nan=False` / `{noNaN: true, noDefaultInfinity: true}` unless you mean to test them.
- **Slow properties starve coverage.** A per-case time budget caps how many run. Set `deadline=None` for legitimately slow code and raise `max_examples`/`numRuns` on critical modules; keep others fast.
- **Ignoring the replay database.** Hypothesis's `.hypothesis/` and fast-check's printed `seed`/`path` are gold — commit-adjacent reproduction. Don't `.gitignore` away the ability to re-hit a fixed bug; pin regressions with `@example`.
- **PBT is not a mutation-test replacement.** It finds inputs that break code; mutation-testing checks whether your assertions catch broken code. Use both: strong properties tend to raise mutation scores.
