"""Generic finance helpers: IRR, NPV, equity multiple, annuity payment.

Cash flow arrays are annual, index 0 = Year 0 (today), end-of-period convention.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def npv(rate: float, cash_flows: Sequence[float]) -> float:
    """NPV with the first cash flow at t=0 (unlike Excel's NPV, which discounts it)."""
    cf = np.asarray(cash_flows, dtype=float)
    t = np.arange(len(cf))
    return float(np.sum(cf / (1.0 + rate) ** t))


def irr(cash_flows: Sequence[float], lo: float = -0.99, hi: float = 10.0,
        tol: float = 1e-12, max_iter: int = 500) -> float | None:
    """Internal rate of return by bisection. Returns None if there is no sign change.

    Bisection is slower than Newton but cannot diverge, and annual RE cash flows are short.
    """
    cf = np.asarray(cash_flows, dtype=float)
    if not (np.any(cf < 0) and np.any(cf > 0)):
        return None
    f_lo, f_hi = npv(lo, cf), npv(hi, cf)
    if f_lo * f_hi > 0:
        return None
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        f_mid = npv(mid, cf)
        if abs(f_mid) < tol or (hi - lo) < tol:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return 0.5 * (lo + hi)


def equity_multiple(cash_flows: Sequence[float]) -> float | None:
    """Total distributions / total contributions."""
    cf = np.asarray(cash_flows, dtype=float)
    invested = -cf[cf < 0].sum()
    return float(cf[cf > 0].sum() / invested) if invested > 0 else None


def annuity_payment(principal: float, rate: float, n_periods: int) -> float:
    """Level payment that repays ``principal`` over ``n_periods`` at ``rate`` per period."""
    if n_periods <= 0:
        return principal
    if rate == 0:
        return principal / n_periods
    return principal * rate / (1.0 - (1.0 + rate) ** -n_periods)
