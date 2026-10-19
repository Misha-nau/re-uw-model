"""Senior debt: loan sizing and the annual debt schedule (Phase 4).

Sizing uses Year 1 NOI and the Year 1 all-in rate:
    loan = min(LTV x price, NOI1 / (min DSCR x debt constant), NOI1 / min debt yield)
Debt constant = interest rate if Year 1 is interest-only, else the annuity constant.

Schedule (Years 1..N): interest on opening balance at that year's all-in rate (floating:
base-rate overrides apply). After the IO period the payment is re-solved each year as an
annuity over the remaining amortisation term at the current rate. The outstanding balance
is repaid from sale proceeds at the end of Year N (balloon).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from .finance import annuity_payment
from .inputs import Debt

Constraint = Literal["ltv", "dscr", "debt_yield", "none"]


@dataclass
class LoanSizing:
    amount: float
    binding: Constraint
    ltv_amount: float
    dscr_amount: float | None
    debt_yield_amount: float | None


@dataclass
class DebtSchedule:
    opening_balance: np.ndarray  # Years 1..N
    interest_rate: np.ndarray
    interest: np.ndarray
    principal: np.ndarray
    closing_balance: np.ndarray

    @property
    def debt_service(self) -> np.ndarray:
        return self.interest + self.principal

    @property
    def balloon(self) -> float:
        return float(self.closing_balance[-1])


def _amortises_in_year(debt: Debt, year: int) -> bool:
    return debt.amortization_years > 0 and year > debt.io_years


def year1_debt_constant(debt: Debt) -> float:
    r = debt.all_in_rate(1)
    if not _amortises_in_year(debt, 1):
        return r
    return annuity_payment(1.0, r, debt.amortization_years)


def size_loan(debt: Debt, purchase_price: float, noi_year1: float) -> LoanSizing:
    if not debt.enabled:
        return LoanSizing(0.0, "none", 0.0, None, None)

    ltv_amount = debt.target_ltv * purchase_price
    candidates: dict[Constraint, float] = {"ltv": ltv_amount}
    dscr_amount = dy_amount = None
    if debt.min_dscr is not None:
        dscr_amount = max(noi_year1, 0.0) / (debt.min_dscr * year1_debt_constant(debt))
        candidates["dscr"] = dscr_amount
    if debt.min_debt_yield:
        dy_amount = max(noi_year1, 0.0) / debt.min_debt_yield
        candidates["debt_yield"] = dy_amount

    binding = min(candidates, key=lambda k: candidates[k])
    return LoanSizing(candidates[binding], binding, ltv_amount, dscr_amount, dy_amount)


def debt_schedule(debt: Debt, loan: float, hold_years: int) -> DebtSchedule:
    n = hold_years
    opening, rate, interest, principal, closing = (np.zeros(n) for _ in range(5))
    balance = loan
    for t in range(1, n + 1):
        i = t - 1
        r = debt.all_in_rate(t) if loan > 0 else 0.0
        opening[i] = balance
        rate[i] = r
        interest[i] = balance * r
        if _amortises_in_year(debt, t) and balance > 0:
            remaining = debt.amortization_years - (t - debt.io_years - 1)
            payment = annuity_payment(balance, r, remaining)
            principal[i] = min(payment - interest[i], balance)
        balance -= principal[i]
        closing[i] = balance
    return DebtSchedule(opening, rate, interest, principal, closing)
