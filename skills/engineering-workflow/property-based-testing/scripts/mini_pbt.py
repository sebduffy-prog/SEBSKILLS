#!/usr/bin/env python3
"""Dependency-free property-based test runner — teaches generate + shrink.

Real projects should use Hypothesis (Python) or fast-check (JS/TS). This ~90-line
runner exists ONLY to make the core loop concrete and runnable with stdlib on
Python 3.9: draw random inputs, find a failure, then SHRINK it to a minimal
counterexample. Run:  python3 mini_pbt.py
"""
from __future__ import annotations
import random
from typing import Callable, Iterator


def gen_int(rng: random.Random, lo: int = -1000, hi: int = 1000) -> int:
    return rng.randint(lo, hi)


def gen_list(rng: random.Random, max_len: int = 12) -> list[int]:
    return [gen_int(rng, 0, 100) for _ in range(rng.randint(0, max_len))]


def shrink_int(x: int) -> Iterator[int]:
    """Yield candidates 'simpler' (closer to 0) than x."""
    if x == 0:
        return
    yield 0
    cur = x
    while abs(cur) > 1:
        cur //= 2
        yield cur
    if x > 0:
        yield x - 1
    else:
        yield x + 1


def shrink_list(xs: list[int]) -> Iterator[list[int]]:
    """Yield simpler lists: drop elements, then shrink individual elements."""
    if not xs:
        return
    # Remove chunks (shorter is simpler).
    n = len(xs)
    size = n
    while size > 0:
        for start in range(0, n, size):
            yield xs[:start] + xs[start + size:]
        size //= 2
    # Shrink each element toward 0.
    for i in range(n):
        for smaller in shrink_int(xs[i]):
            yield xs[:i] + [smaller] + xs[i + 1:]


def run_property(name: str, gen: Callable, shrink: Callable,
                 prop: Callable, runs: int = 300, seed: int = 42) -> bool:
    rng = random.Random(seed)
    for _ in range(runs):
        value = gen(rng)
        if not _holds(prop, value):
            minimal = _shrink_to_minimal(shrink, prop, value)
            print(f"FAIL {name}: falsified by {minimal!r} (raw {value!r}, seed={seed})")
            return False
    print(f"PASS {name}: {runs} runs, no counterexample")
    return True


def _holds(prop: Callable, value) -> bool:
    try:
        return bool(prop(value))
    except Exception:
        return False


def _shrink_to_minimal(shrink: Callable, prop: Callable, failing):
    current = failing
    improved = True
    while improved:
        improved = False
        for candidate in shrink(current):
            if not _holds(prop, candidate):
                current = candidate
                improved = True
                break
    return current


if __name__ == "__main__":
    # A correct property: reversing twice is identity.
    run_property("reverse-twice is identity", gen_list, shrink_list,
                 lambda xs: list(reversed(list(reversed(xs)))) == xs)

    # A buggy 'max' that ignores the first element — PBT should shrink to a
    # tiny counterexample like [1] or [1, 0].
    def buggy_max(xs: list[int]) -> int:
        return max(xs[1:]) if len(xs) > 1 else (xs[0] if xs else 0)

    run_property("buggy_max equals builtin max (expected FAIL)",
                 lambda r: gen_list(r, 6), shrink_list,
                 lambda xs: (not xs) or buggy_max(xs) == max(xs))
