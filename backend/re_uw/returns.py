"""Acquisition, exit, fees and returns (Phase 4). Entry point: ``underwrite(inputs)``.

Three cash flow streams, Years 0..N (index 0 = closing):
* **Unlevered** (property level): price + stamp duty + other costs + upfront capex out at
  Year 0; CF before debt each year; net sale proceeds in Year N. No financing, no fund fees.
* **Levered, gross of fees**: equity before fund fees.
* **Levered, net of fees** (equity cash flow): after debt service and fund fees. This is
  the stream the LP/GP waterfall (``waterfall.py``) distributes.

Formulas: docs/methodology.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .cashflow import OperatingCashFlow, operating_cash_flow
from .debt import DebtSchedule, LoanSizing, debt_schedule, size_loan
from .finance import equity_multiple, irr, npv
from .inputs import UnderwritingInputs
from .sg_tax import acquisition_stamp_duty
from .waterfall import WaterfallResult, run_waterfall


@dataclass
class SourcesUses:
    purchase_price: float
    stamp_duty: float
    other_costs: float
    upfront_capex: float
    loan_fee: float
    acquisition_fee: float
    loan: float
    equity: float

    @property
    def property_cost(self) -> float:
        """All-in property cost, excluding financing and fund fees."""
        return self.purchase_price + self.stamp_duty + self.other_costs + self.upfront_capex

    @property
    def total_uses(self) -> float:
        return self.property_cost + self.loan_fee + self.acquisition_fee

    def table(self) -> pd.DataFrame:
        uses = [("Purchase price", self.purchase_price), ("Stamp duty", self.stamp_duty),
                ("Other acquisition costs", self.other_costs),
                ("Upfront capex", self.upfront_capex), ("Loan fee", self.loan_fee),
                ("Acquisition fee", self.acquisition_fee), ("Total uses", self.total_uses)]
        sources = [("Senior loan", self.loan), ("Equity", self.equity),
                   ("Total sources", self.loan + self.equity)]
        rows = [("Uses", k, v) for k, v in uses] + [("Sources", k, v) for k, v in sources]
        df = pd.DataFrame(rows, columns=["side", "item", "amount"])
        df["% of total"] = df["amount"] / self.total_uses
        return df


@dataclass
class ExitValue:
    year: int  # N
    noi_basis: float
    cap_rate: float
    gross_value: float
    selling_costs: float
    divestment_fee: float
    loan_repayment: float

    @property
    def net_property_proceeds(self) -> float:
        return self.gross_value - self.selling_costs

    @property
    def net_equity_proceeds(self) -> float:
        return self.net_property_proceeds - self.divestment_fee - self.loan_repayment


@dataclass
class UnderwritingResult:
    inputs: UnderwritingInputs
    operating: OperatingCashFlow
    sizing: LoanSizing
    sources_uses: SourcesUses
    debt: DebtSchedule
    exit: ExitValue
    asset_mgmt_fee: np.ndarray  # Years 1..N
    unlevered_cf: np.ndarray  # Years 0..N
    levered_gross_cf: np.ndarray
    levered_net_cf: np.ndarray
    waterfall: WaterfallResult
    metrics: dict[str, float | None] = field(default_factory=dict)

    def cash_flow_table(self, scale: float = 1.0) -> pd.DataFrame:
        """Years 0..N: from CF before debt down to the three cash flow streams."""
        n = self.operating.hold_period_years
        ocf = self.operating
        z = np.zeros(1)

        def yrs(a: np.ndarray) -> np.ndarray:  # Years 1..N padded with Year 0
            return np.concatenate([z, a[:n]])

        su, ex, d = self.sources_uses, self.exit, self.debt
        sale = np.zeros(n + 1)
        sale[n] = ex.gross_value
        sell_cost = np.zeros(n + 1)
        sell_cost[n] = ex.selling_costs
        acq = np.zeros(n + 1)
        acq[0] = su.property_cost
        loan_in = np.zeros(n + 1)
        loan_in[0] = su.loan
        repay = np.zeros(n + 1)
        repay[n] = ex.loan_repayment
        fin_fees = np.zeros(n + 1)
        fin_fees[0] = su.loan_fee
        fund_fees = yrs(self.asset_mgmt_fee)
        fund_fees[0] += su.acquisition_fee
        fund_fees[n] += ex.divestment_fee

        rows = [
            ("Net operating income", yrs(ocf.noi)),
            ("CF before debt", yrs(ocf.cf_before_debt)),
            ("Acquisition (price + duty + costs + capex)", -acq),
            ("Gross sale price", sale),
            ("Selling costs", -sell_cost),
            ("Unlevered cash flow", self.unlevered_cf),
            ("Loan drawdown", loan_in),
            ("Loan fee", -fin_fees),
            ("Interest", -yrs(d.interest)),
            ("Principal amortisation", -yrs(d.principal)),
            ("Loan repayment at exit", -repay),
            ("Levered cash flow (gross of fund fees)", self.levered_gross_cf),
            ("Fund fees (acq + AM + divestment)", -fund_fees),
            ("Equity cash flow (net of fees)", self.levered_net_cf),
        ]
        start = self.inputs.analysis.start_year
        cols = [f"Y{t} {start + t - 1}" for t in range(n + 1)]
        return pd.DataFrame({k: v / scale + 0.0 for k, v in rows}, index=cols).T

    def debt_table(self, scale: float = 1.0) -> pd.DataFrame:
        d = self.debt
        n = len(d.interest)
        start = self.inputs.analysis.start_year
        cols = [f"Y{t} {start + t - 1}" for t in range(1, n + 1)]
        noi = self.operating.noi[:n]
        ds = d.debt_service
        rows = {
            "Opening balance": d.opening_balance / scale,
            "All-in rate %": d.interest_rate * 100,
            "Interest": d.interest / scale,
            "Principal": d.principal / scale,
            "Closing balance": d.closing_balance / scale,
            "DSCR (NOI / debt service)": np.divide(noi, ds, out=np.full(n, np.nan), where=ds > 0),
            "ICR (NOI / interest)": np.divide(noi, d.interest, out=np.full(n, np.nan),
                                              where=d.interest > 0),
        }
        return pd.DataFrame(rows, index=cols).T


# ---------------------------------------------------------------------------
def underwrite(inp: UnderwritingInputs) -> UnderwritingResult:
    ocf = operating_cash_flow(inp)
    n = inp.analysis.hold_period_years
    acq, fees = inp.acquisition, inp.fees
    price = acq.purchase_price
    noi = ocf.noi  # Years 1..N+1
    cfbd = ocf.cf_before_debt[:n]

    # --- acquisition, financing --------------------------------------------------
    sizing = size_loan(inp.debt, price, noi[0])
    loan = sizing.amount
    acquisition_fee = price * fees.acquisition_fee_pct if fees.enabled else 0.0
    su = SourcesUses(
        purchase_price=price,
        stamp_duty=acquisition_stamp_duty(acq),
        other_costs=price * acq.other_costs_pct,
        upfront_capex=acq.upfront_capex,
        loan_fee=loan * inp.debt.upfront_fee_pct,
        acquisition_fee=acquisition_fee,
        loan=loan,
        equity=0.0,
    )
    su.equity = su.total_uses - loan
    sched = debt_schedule(inp.debt, loan, n)

    # --- exit -----------------------------------------------------------------------
    noi_basis = noi[n] if inp.exit.noi_basis == "forward" else noi[n - 1]
    gross_value = noi_basis / inp.exit.exit_cap_rate
    ex = ExitValue(
        year=n,
        noi_basis=noi_basis,
        cap_rate=inp.exit.exit_cap_rate,
        gross_value=gross_value,
        selling_costs=gross_value * inp.exit.selling_cost_pct,
        divestment_fee=gross_value * fees.divestment_fee_pct if fees.enabled else 0.0,
        loan_repayment=sched.balloon,
    )

    # --- fund fees ------------------------------------------------------------------
    if fees.enabled:
        if fees.asset_mgmt_fee_basis == "gav":
            basis = noi[1 : n + 1] / inp.exit.exit_cap_rate  # value at year t = NOI_{t+1}/cap
        elif fees.asset_mgmt_fee_basis == "purchase_price":
            basis = np.full(n, price)
        else:
            basis = np.full(n, su.equity)
        am_fee = fees.asset_mgmt_fee_pct * basis
    else:
        am_fee = np.zeros(n)

    # --- cash flow streams (Years 0..N) ------------------------------------------
    unlev = np.concatenate([[-su.property_cost], cfbd])
    unlev[n] += ex.net_property_proceeds

    lev_gross = np.concatenate([[-(su.equity - su.acquisition_fee)], cfbd - sched.debt_service])
    lev_gross[n] += ex.net_property_proceeds - ex.loan_repayment

    lev_net = np.concatenate([[-su.equity], cfbd - sched.debt_service - am_fee])
    lev_net[n] += ex.net_equity_proceeds

    result = UnderwritingResult(
        inputs=inp, operating=ocf, sizing=sizing, sources_uses=su, debt=sched, exit=ex,
        asset_mgmt_fee=am_fee, unlevered_cf=unlev, levered_gross_cf=lev_gross,
        levered_net_cf=lev_net, waterfall=run_waterfall(inp.waterfall, lev_net),
    )
    result.metrics = _metrics(result) | result.waterfall.metrics()
    return result


def _metrics(r: UnderwritingResult) -> dict[str, float | None]:
    inp, su, d, ex = r.inputs, r.sources_uses, r.debt, r.exit
    n = inp.analysis.hold_period_years
    dr = inp.analysis.discount_rate
    noi = r.operating.noi
    ds = d.debt_service
    has_debt = su.loan > 0

    dscr = noi[:n] / ds if has_debt and np.all(ds > 0) else None
    icr = noi[:n] / d.interest if has_debt and np.all(d.interest > 0) else None
    operating_equity_cf = r.levered_net_cf[1:].copy()
    operating_equity_cf[-1] -= ex.net_equity_proceeds  # exclude sale
    cum = np.cumsum(r.levered_net_cf)

    return {
        # property
        "noi_year1": float(noi[0]),
        "entry_cap_rate": float(noi[0] / su.purchase_price),
        "yield_on_cost": float(noi[0] / su.property_cost),
        "price_psf": su.purchase_price / inp.total_nla_sqft,
        "exit_value": ex.gross_value,
        "exit_value_psf": ex.gross_value / inp.total_nla_sqft,
        # unlevered
        "unlevered_irr": irr(r.unlevered_cf),
        "unlevered_multiple": equity_multiple(r.unlevered_cf),
        "unlevered_npv": npv(dr, r.unlevered_cf),
        "unlevered_profit": float(r.unlevered_cf.sum()),
        # levered
        "levered_irr_gross": irr(r.levered_gross_cf),
        "levered_multiple_gross": equity_multiple(r.levered_gross_cf),
        "levered_irr": irr(r.levered_net_cf),
        "levered_multiple": equity_multiple(r.levered_net_cf),
        "levered_npv": npv(dr, r.levered_net_cf),
        "levered_profit": float(r.levered_net_cf.sum()),
        "equity": su.equity,
        "peak_equity": float(-cum.min()),
        "avg_cash_on_cash": float(operating_equity_cf.mean() / su.equity),
        "year1_cash_on_cash": float(operating_equity_cf[0] / su.equity),
        # debt
        "loan": su.loan,
        "ltv": su.loan / su.purchase_price,
        "ltc": su.loan / su.total_uses,
        "debt_yield_year1": float(noi[0] / su.loan) if has_debt else None,
        "dscr_year1": float(dscr[0]) if dscr is not None else None,
        "dscr_min": float(dscr.min()) if dscr is not None else None,
        "icr_year1": float(icr[0]) if icr is not None else None,
        "icr_min": float(icr.min()) if icr is not None else None,
        "exit_ltv": ex.loan_repayment / ex.gross_value,
        # fees
        "total_fund_fees": float(su.acquisition_fee + r.asset_mgmt_fee.sum() + ex.divestment_fee),
    }
