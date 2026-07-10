---
name: mathematical-computation
category: data-analysis
description: Solve mathematics problems — algebra, calculus, linear algebra, ODEs, probability, combinatorics — with symbolic computation in SymPy AND numerical verification in NumPy/SciPy. Use when the user asks a math problem of any kind, wants a derivation, wants to solve an equation, integrate, differentiate, invert a matrix, find eigenvalues, work with probability distributions, or verify a hand-derived result. Triggers on "solve", "integrate", "differentiate", "matrix", "eigenvalues", "ODE", "limit", "probability of", "expected value", "factorial", "Bayes". Anti-hallucination posture — every claimed result is produced by SymPy / NumPy in-session; symbolic answers are cross-checked numerically with random sampling; nothing is "obviously" true without showing the computation.
when_to_use:
  - User asks to solve an algebraic equation or system of equations
  - User asks to differentiate, integrate, take a limit, expand a series
  - User asks for matrix operations — inverse, determinant, rank, eigendecomposition, SVD
  - User asks to solve an ODE or PDE
  - User wants probability calculations — distributions, expectations, Bayes updates
  - User wants to verify a hand-derived result
  - User asks combinatorics — permutations, combinations, generating functions
when_not_to_use:
  - User wants statistical hypothesis testing on data → use statistical-testing
  - User wants data summary stats → use exploratory-data-analysis
  - User wants to manipulate a dataset, not solve a math problem → use data-processing
  - User wants symbolic differentiation of model code (autograd) — that's an ML concern
similar_to:
  - statistical-testing
  - exploratory-data-analysis
keywords:
  - solve
  - equation
  - integral
  - derivative
  - limit
  - matrix
  - eigenvalue
  - determinant
  - svd
  - ode
  - sympy
  - numpy
  - probability
  - bayes
  - combinatorics
  - factorial
  - simplify
  - expand
inputs_needed:
  - The exact problem statement (in LaTeX or plain text)
  - Whether the user wants a symbolic answer, a numerical answer, or both
  - Domain constraints (real / complex, positive / non-zero, integer)
  - For ODEs / probability — initial conditions, parameter values, support of variables
produces: A step-by-step solution showing setup, symbolic computation, numerical cross-check, and the final answer in the requested form (LaTeX / decimal / interval)
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Mathematical Computation

Solve mathematics problems with symbolic computation, cross-verified numerically.

## Verification protocol — no claims without computation

1. **Solve symbolically first, then verify numerically.** For any symbolic result, plug in a random sample of valid input values and check the identity holds (to within floating-point tolerance). If it doesn't, the symbolic answer is wrong — debug, don't ship.
2. **Show each step.** Don't write "after simplification, we get …". Print the intermediate expression that SymPy produced.
3. **State domain assumptions explicitly.** `sympy.solve(x**2 == 4)` returns `[-2, 2]`. If the user said "x is positive", filter — and SAY you filtered.
4. **Convergence / existence is checked, not assumed.** Limits computed by `sympy.limit` may not exist. Integrals may diverge. Series may have radius of convergence. Report what SymPy returns honestly (`oo`, `NaN`, `Undefined`).
5. **Numerical results carry uncertainty.** When using floats, report to a reasonable precision and note the tolerance.
6. **"Trivial" steps are still executed.** Even if a step seems obvious, run it through SymPy. Hand-arithmetic mistakes are the most common math errors.

## Inputs to confirm with the user

- **Exact statement.** Rewrite the user's problem in LaTeX and confirm before solving. "Solve x² + 2x = 8" — confirm the equation, the variable, and what "solve" means (real roots, all complex roots, factored form).
- **Domain.** Reals or complex? Positive integers? `x ≠ 0`?
- **Output form.** Symbolic / exact (e.g. `2 + sqrt(3)`)? Numerical to N decimals? Both?
- **For probability problems** — the support, the distribution, parameters. Distinguish discrete vs continuous explicitly.

## Standard workflow (algebra example)

```python
import sympy as sp
import numpy as np

# 1. STATE THE PROBLEM
x = sp.symbols("x", real=True)            # domain matters
eq = sp.Eq(x**3 - 6*x**2 + 11*x - 6, 0)
print(f"Solving: {sp.latex(eq)}")

# 2. SOLVE SYMBOLICALLY
roots = sp.solve(eq, x)
print(f"Symbolic roots: {roots}")

# 3. NUMERICAL CROSS-CHECK — substitute each back in
for r in roots:
    residual = sp.simplify(eq.lhs.subs(x, r))
    print(f"  x={r}: lhs evaluates to {residual} (should be 0)")
    assert residual == 0, f"symbolic root {r} failed substitution"

# 4. ADDITIONAL VERIFICATION — numerical sampling for identities
#    For polynomials: factor and verify the expansion matches
factored = sp.factor(eq.lhs)
print(f"Factored: {factored}")
assert sp.simplify(sp.expand(factored) - eq.lhs) == 0

# 5. OUTPUT — both forms
print("\nFinal answer:")
print(f"  Exact: x ∈ {{ {', '.join(map(str, roots))} }}")
print(f"  Numerical: x ∈ {{ {', '.join(f'{float(r):.6f}' for r in roots)} }}")
```

A more complete template is in `assets/solve-template.py`.

## Workflow patterns by problem type

### Solving equations
- `sp.solve(eq, x)` for closed-form. For systems: `sp.solve([eq1, eq2], [x, y])`.
- For numerical roots: `sp.nsolve(eq, x, x0)` (needs initial guess).
- Always verify each root by substitution.

### Calculus
- `sp.diff(f, x, n)` for the n-th derivative.
- `sp.integrate(f, x)` (indefinite) or `sp.integrate(f, (x, a, b))` (definite).
- `sp.limit(f, x, a)` — note direction with `dir='+'` or `'-'`.
- Verify by: differentiate the antiderivative and check it equals the integrand (`sp.simplify(sp.diff(F, x) - f) == 0`).

### Linear algebra
- `sp.Matrix([[…]])` for exact arithmetic; `np.array` for numerical.
- For numerical work, use `numpy.linalg`:
  - `np.linalg.inv(A)` — check `A @ A_inv ≈ I` to a tolerance.
  - `np.linalg.eig(A)` — check `A @ v ≈ λ v` for each pair.
  - `np.linalg.solve(A, b)` over `inv(A) @ b` — better numerically.
- **Always state condition number** for any matrix being inverted (`np.linalg.cond(A)`); flag if > 1e10.

### ODEs
- `sp.dsolve(ode, y(x))`, then apply initial conditions with `ics={…}`.
- Verify by substituting the solution back into the ODE — residual must be 0.
- For stiff / nonlinear ODEs without symbolic form: `scipy.integrate.solve_ivp` (numerical). Report tolerance and integrator used.

### Probability
- Discrete: `scipy.stats.<dist>(params).pmf(k)` and `.cdf(k)`.
- Continuous: `.pdf(x)` and `.cdf(x)`. Note PDFs are *densities*, not probabilities.
- Verify by sampling: draw n = 1e6 samples and check the empirical mean / variance / quantiles match the theoretical values to 3 decimal places.
- Bayes: explicitly write prior, likelihood, evidence, posterior — verify posterior integrates to 1.

## Anti-patterns to refuse

- "By inspection, the answer is …" → No. Compute.
- Skipping the substitution check on symbolic results. → Every root, every antiderivative, every solution gets plugged back in.
- Reporting `sp.solve(eq, x)` output without filtering for domain. → "x is real and positive" means filter.
- Confusing PDF value with probability for continuous distributions. → Always compute via `.cdf` for "probability of X < a".
- Reporting eigenvalues from a matrix with `cond(A) > 1e10` without flagging numerical instability.
- "The series converges" without computing or citing the radius of convergence.
- Hand-arithmetic in the final answer. Even "(2)(3) = 6" goes through Python.
- Confidently giving a numerical answer to many digits — round to a precision consistent with input precision.

## Output format

Produce a structured solution:

```markdown
## Problem
<restate in LaTeX, confirm domain>

## Setup
<symbols, constraints, the equation/integral/etc.>

## Solution
1. <step 1 description>
   ```
   <code that produced the step>
   ```
   Result: <SymPy output>

2. <step 2>
   ...

## Verification
- Substitution check: <residual = 0 ✓>
- Numerical sample check: <random samples agree to 1e-10 ✓>

## Answer
- **Exact**: <LaTeX>
- **Numerical**: <decimal to appropriate precision>
```

## Escalation paths

- **No closed form** — switch to numerical (`nsolve`, `solve_ivp`, `quad`) and report tolerance.
- **Symbolic explosion** (`sp.simplify` runs forever) — try `sp.nsimplify`, `sp.cancel`, or a different approach. Don't hang waiting.
- **High-dimensional linear algebra** — use NumPy, not SymPy; warn the user about floating-point precision.
- **Pure proof-style mathematics** without numerical input — this skill focuses on computation; for proofs, structure the argument step by step and verify each computable claim.

## Asset

`assets/solve-template.py` — a runnable Python script demonstrating the solve-then-verify pattern for several common problem types.
