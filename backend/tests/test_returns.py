"""Debt, exit, fees and returns with exact, hand-checkable answers.

The "flat" deal: NOI = 120,000 every year (no growth, no vacancy, no opex/tax),
price 1.2m (10% cap), no transaction costs, exit at 10% cap on forward NOI = 1.2m.
=> unlevered IRR exactly 10%. With 50% LTV interest-only at 5%: equity 600k,
annual equity CF 120k - 30k = 90k, exit equity 600k => levered IRR exactly 15%.
"""

import copy

import numpy as np
import pytest

from re_uw.debt import debt_schedule, size_loan
from re_uw.finance import annuity_payment, equity_multiple, irr, npv
from re_uw.inputs import Debt, UnderwritingInputs
from re_uw.returns import underwrite
from re_uw.scenarios import SCENARIOS_DIR, load_scenario
from tests.test_cashflow import ZERO_LEASING

A = pytest.approx

FLAT = {
    "scenario": {"name": "flat"},
    "analysis": {"start_year": 2027, "hold_period_years": 3, "discount_rate": 0.10},
    "property": {"name": "T", "tenure": "freehold"},
    "components": [{
        "name": "Office", "use_type": "office", "nla_sqft": 1_000,
        "revenue": {"rent_psf_pm": 10.0, "rent_growth": 0.0, "vacancy": 0.0, "credit_loss": 0.0},
        "leasing": ZERO_LEASING, "opex_psf_pm": 0.0,
    }],
    "acquisition": {"purchase_price": 1_200_000, "stamp_duty_override_pct": 0.0,
                    "other_costs_pct": 0.0},
    "expenses": {"property_tax_rate": 0.0, "management_fee_pct": 0.0},
    "capex": {"reserve_psf_pa": 0.0},
    "debt": {"enabled": False},
    "exit": {"exit_cap_rate": 0.10, "selling_cost_pct": 0.0},
    "fees": {"enabled": False},
    "waterfall": {"pref_rate": 0.08, "tiers": [{"up_to_irr": None, "gp_promote": 0.2}]},
}

DEBT_50_IO_5 = {"enabled": True, "target_ltv": 0.5, "min_dscr": None, "base_rate": 0.05,
                "margin": 0.0, "amortization_years": 0, "upfront_fee_pct": 0.0}


def flat(**sections) -> UnderwritingInputs:
    d = copy.deepcopy(FLAT)
    for k, v in sections.items():
        d[k] = {**d[k], **v} if isinstance(d.get(k), dict) else v
    return UnderwritingInputs.model_validate(d)


# --- finance helpers --------------------------------------------------------------
def test_irr_npv_multiple():
    assert irr([-100, 110]) == A(0.10)
    assert irr([-100, 0, 121]) == A(0.10)
    assert irr([-100, 10, 10, 110]) == A(0.10)
    assert irr([100, 50]) is None  # no sign change
    assert npv(0.10, [-100, 110]) == A(0.0, abs=1e-9)
    assert equity_multiple([-100, 10, 10, 110]) == A(1.3)


def test_annuity_payment():
    # 1,000 at 10% over 2 years: 1,000 x 0.1 / (1 - 1.1^-2) = 576.19
    assert annuity_payment(1_000, 0.10, 2) == A(576.190476, rel=1e-6)
    assert annuity_payment(1_000, 0.0, 4) == A(250)


# --- loan sizing ------------------------------------------------------------------
def test_sizing_ltv_binds():
    s = size_loan(Debt(target_ltv=0.5, min_dscr=1.5, base_rate=0.05, margin=0.0),
                  purchase_price=1_000_000, noi_year1=85_200)
    # DSCR amount = 85,200 / (1.5 x 5%) = 1,136,000 > LTV 500,000
    assert s.binding == "ltv" and s.amount == A(500_000)
    assert s.dscr_amount == A(1_136_000)


def test_sizing_dscr_binds():
    s = size_loan(Debt(target_ltv=0.5, min_dscr=2.0, base_rate=0.10, margin=0.0),
                  purchase_price=1_000_000, noi_year1=85_200)
    assert s.binding == "dscr" and s.amount == A(426_000)  # 85,200 / (2.0 x 10%)


def test_sizing_debt_yield_binds():
    s = size_loan(Debt(target_ltv=0.5, min_debt_yield=0.20, base_rate=0.05, margin=0.0),
                  purchase_price=1_000_000, noi_year1=85_200)
    assert s.binding == "debt_yield" and s.amount == A(426_000)  # 85,200 / 20%


def test_sizing_dscr_uses_annuity_constant_when_amortising():
    debt = Debt(target_ltv=0.9, min_dscr=1.0, base_rate=0.10, margin=0.0, amortization_years=2)
    s = size_loan(debt, purchase_price=10_000_000, noi_year1=576.190476)
    assert s.amount == A(1_000, rel=1e-6)  # payment 576.19 per 1,000 of loan


def test_debt_disabled():
    s = size_loan(Debt(enabled=False), 1_000_000, 85_200)
    assert s.amount == 0 and s.binding == "none"


# --- debt schedule ----------------------------------------------------------------
def test_full_amortisation():
    d = Debt(base_rate=0.10, margin=0.0, amortization_years=2)
    s = debt_schedule(d, 1_000, hold_years=2)
    assert s.interest == A([100, 52.380952], rel=1e-6)
    assert s.principal == A([476.190476, 523.809524], rel=1e-6)
    assert s.closing_balance == A([523.809524, 0.0], abs=1e-6)
    assert s.balloon == A(0.0, abs=1e-6)


def test_io_then_amortisation_and_balloon():
    d = Debt(base_rate=0.10, margin=0.0, amortization_years=2, io_years=1)
    s = debt_schedule(d, 1_000, hold_years=2)
    # Y1 IO; Y2 first amortising year: payment 576.19 -> principal 476.19
    assert s.principal == A([0.0, 476.190476], rel=1e-6)
    assert s.balloon == A(523.809524, rel=1e-6)


def test_floating_rate_overrides():
    d = Debt(base_rate=0.02, base_rate_overrides={2: 0.03}, margin=0.01)
    s = debt_schedule(d, 1_000_000, hold_years=3)
    assert s.interest_rate == A([0.03, 0.04, 0.03])
    assert s.interest == A([30_000, 40_000, 30_000])


# --- whole-deal returns ------------------------------------------------------------
def test_flat_unlevered_irr_is_cap_rate():
    r = underwrite(flat())
    assert r.unlevered_cf == A([-1_200_000, 120_000, 120_000, 1_320_000])
    assert r.metrics["unlevered_irr"] == A(0.10)
    assert r.metrics["levered_irr"] == A(0.10)  # no debt, no fees
    assert r.metrics["unlevered_npv"] == A(0.0, abs=1e-6)  # discount rate 10%
    assert r.metrics["entry_cap_rate"] == A(0.10)


def test_flat_levered_irr():
    r = underwrite(flat(debt=DEBT_50_IO_5))
    assert r.sources_uses.loan == A(600_000)
    assert r.sources_uses.equity == A(600_000)
    assert r.levered_net_cf == A([-600_000, 90_000, 90_000, 690_000])
    assert r.metrics["levered_irr"] == A(0.15)
    assert r.metrics["dscr_year1"] == A(4.0)  # 120,000 / 30,000
    assert r.metrics["debt_yield_year1"] == A(0.20)


def test_trailing_vs_forward_exit():
    fwd = underwrite(flat(components=[{**FLAT["components"][0],
                                       "revenue": {**FLAT["components"][0]["revenue"],
                                                   "rent_growth": 0.10}}]))
    trl = underwrite(flat(components=fwd.inputs.model_dump()["components"],
                          exit={"noi_basis": "trailing"}))
    # 3-year hold: forward uses Year 4 NOI, trailing Year 3 NOI (10% apart)
    assert fwd.exit.noi_basis == A(trl.exit.noi_basis * 1.10)


def test_fees_reduce_equity_cash_flow():
    fees = {"enabled": True, "asset_mgmt_fee_pct": 0.01, "asset_mgmt_fee_basis": "purchase_price",
            "acquisition_fee_pct": 0.01, "divestment_fee_pct": 0.01}
    r = underwrite(flat(debt=DEBT_50_IO_5, fees=fees))
    # equity = 1.2m + 12k acq fee - 600k loan = 612k; AM fee 12k pa; divestment 12k
    assert r.sources_uses.equity == A(612_000)
    assert r.asset_mgmt_fee == A([12_000] * 3)
    assert r.levered_net_cf == A([-612_000, 78_000, 78_000, 78_000 + 600_000 - 12_000])
    # gross-of-fees stream is unchanged at 15%
    assert r.metrics["levered_irr_gross"] == A(0.15)
    assert r.metrics["total_fund_fees"] == A(12_000 * 5)


def test_gav_fee_basis_uses_next_year_noi():
    fees = {"enabled": True, "asset_mgmt_fee_pct": 0.01, "asset_mgmt_fee_basis": "gav",
            "acquisition_fee_pct": 0.0, "divestment_fee_pct": 0.0}
    r = underwrite(flat(fees=fees))
    assert r.asset_mgmt_fee == A([12_000] * 3)  # 1% x 120,000 / 10%


def test_transaction_costs_in_sources_uses():
    r = underwrite(flat(acquisition={**FLAT["acquisition"], "stamp_duty_override_pct": 0.05,
                                     "other_costs_pct": 0.01, "upfront_capex": 10_000},
                        debt={**DEBT_50_IO_5, "upfront_fee_pct": 0.01}))
    su = r.sources_uses
    assert su.stamp_duty == A(60_000) and su.other_costs == A(12_000)
    assert su.loan_fee == A(6_000)  # 1% x 600k
    assert su.total_uses == A(1_200_000 + 60_000 + 12_000 + 10_000 + 6_000)
    assert su.loan + su.equity == A(su.total_uses)
    assert r.unlevered_cf[0] == A(-1_282_000)  # loan fee excluded at property level


# --- sample: consistency checks ------------------------------------------------------
def test_sample_identities():
    r = underwrite(load_scenario(SCENARIOS_DIR / "sample_sg_cbd_office_retail.json"))
    t = r.cash_flow_table()
    unlev = ["CF before debt", "Acquisition (price + duty + costs + capex)", "Gross sale price",
             "Selling costs"]
    assert np.allclose(t.loc[unlev].sum(), t.loc["Unlevered cash flow"])
    lev = ["Unlevered cash flow", "Loan drawdown", "Loan fee", "Interest",
           "Principal amortisation", "Loan repayment at exit"]
    assert np.allclose(t.loc[lev].sum(), t.loc["Levered cash flow (gross of fund fees)"])
    net = ["Levered cash flow (gross of fund fees)", "Fund fees (acq + AM + divestment)"]
    assert np.allclose(t.loc[net].sum(), t.loc["Equity cash flow (net of fees)"])
    m = r.metrics
    assert m["ltv"] == A(0.5)
    assert npv(m["levered_irr"], r.levered_net_cf) == A(0.0, abs=1e-3)
