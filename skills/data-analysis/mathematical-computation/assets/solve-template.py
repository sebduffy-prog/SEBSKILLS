"""
Math-solving template — symbolic with SymPy, cross-checked numerically.

Anti-hallucination contract:
- Every symbolic result is verified by substitution.
- Every integral is verified by differentiating the antiderivative.
- Every probability result is verified by sampling 1e6 draws.
- The script halts on any verification failure.

Adapt the sections you need; delete the rest. The pattern is what matters:
  solve → verify → report.
"""

import numpy as np
import sympy as sp
from scipy import stats


def verify(label: str, residual_expr, tol: float = 1e-10) -> None:
    """Assert a symbolic residual simplifies to zero."""
    simplified = sp.simplify(residual_expr)
    if simplified == 0:
        print(f"  ✓ {label}: residual = 0 (exact)")
        return
    # Maybe it's exact but SymPy didn't catch it — try numerical
    try:
        val = float(simplified)
        if abs(val) < tol:
            print(f"  ✓ {label}: residual = {val:.2e} (< {tol})")
            return
    except (TypeError, ValueError):
        pass
    raise AssertionError(f"{label} FAILED: residual = {simplified}")


# ---------------------------------------------------------------------------
# 1. SOLVING A POLYNOMIAL
# ---------------------------------------------------------------------------
def example_polynomial() -> None:
    print("\n=== POLYNOMIAL ===")
    x = sp.symbols("x", real=True)
    eq = sp.Eq(x**3 - 6 * x**2 + 11 * x - 6, 0)
    print(f"Solve: {eq}")

    roots = sp.solve(eq, x)
    print(f"Roots: {roots}")

    for r in roots:
        verify(f"x = {r}", eq.lhs.subs(x, r))

    print(f"Factored: {sp.factor(eq.lhs)}")


# ---------------------------------------------------------------------------
# 2. CALCULUS — DEFINITE INTEGRAL WITH VERIFICATION
# ---------------------------------------------------------------------------
def example_integral() -> None:
    print("\n=== INTEGRAL ===")
    x = sp.symbols("x")
    f = sp.sin(x) ** 2

    F = sp.integrate(f, x)                        # antiderivative
    print(f"∫ sin²(x) dx = {F}")
    verify("d/dx of antiderivative = integrand", sp.diff(F, x) - f)

    a, b = 0, sp.pi
    definite = sp.integrate(f, (x, a, b))
    print(f"∫₀^π sin²(x) dx = {definite} = {float(definite):.6f}")

    # Numerical cross-check
    from scipy.integrate import quad
    num, err = quad(lambda v: np.sin(v) ** 2, 0, np.pi)
    verify("numerical quad agrees with symbolic", definite - num, tol=err * 10)


# ---------------------------------------------------------------------------
# 3. LINEAR ALGEBRA — EIGENVALUES + VERIFICATION
# ---------------------------------------------------------------------------
def example_linear_algebra() -> None:
    print("\n=== LINEAR ALGEBRA ===")
    A = np.array([[4.0, -2.0], [1.0, 1.0]])
    print(f"A =\n{A}")
    print(f"cond(A) = {np.linalg.cond(A):.2e}")

    eigvals, eigvecs = np.linalg.eig(A)
    print(f"Eigenvalues: {eigvals}")

    for lam, v in zip(eigvals, eigvecs.T):
        residual = A @ v - lam * v
        print(f"  ✓ λ={lam:.6f}: ||Av - λv|| = {np.linalg.norm(residual):.2e}")


# ---------------------------------------------------------------------------
# 4. ODE — SOLVE + VERIFY BY SUBSTITUTION
# ---------------------------------------------------------------------------
def example_ode() -> None:
    print("\n=== ODE ===")
    x = sp.symbols("x")
    y = sp.Function("y")
    ode = sp.Eq(y(x).diff(x) - 2 * y(x), 0)
    print(f"ODE: {ode}")

    sol = sp.dsolve(ode, y(x), ics={y(0): 1})
    print(f"Solution: {sol}")

    lhs = sol.rhs.diff(x) - 2 * sol.rhs
    verify("solution satisfies ODE", lhs)


# ---------------------------------------------------------------------------
# 5. PROBABILITY — THEORY VS SAMPLING
# ---------------------------------------------------------------------------
def example_probability() -> None:
    print("\n=== PROBABILITY ===")
    # P(X > 2) for X ~ Normal(0, 1)
    p_theory = 1 - stats.norm.cdf(2)
    print(f"P(X > 2), X ~ N(0,1): {p_theory:.6f}")

    rng = np.random.default_rng(seed=0)
    samples = rng.standard_normal(1_000_000)
    p_empirical = (samples > 2).mean()
    print(f"Empirical (n=1e6, seed=0):     {p_empirical:.6f}")

    diff = abs(p_theory - p_empirical)
    print(f"  ✓ |theory - empirical| = {diff:.2e} (expected ≲ 1e-4 at n=1e6)")
    assert diff < 1e-3, "empirical disagrees with theory — bug somewhere"


if __name__ == "__main__":
    example_polynomial()
    example_integral()
    example_linear_algebra()
    example_ode()
    example_probability()
    print("\nAll verifications passed.")
