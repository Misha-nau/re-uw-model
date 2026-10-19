"""Operating cash flow tests with small, hand-checkable numbers.

Base case used throughout (see _inputs): one office component, 1,000 sq ft,
$10 psf pm, 10% rent growth, 10% vacancy, 2-year hold (so 3 projection years),
$1 psf pm opex, property tax 10% on AV = 90% of GPR. Everything else zero.
"""

import copy

import numpy as np
import pytest

from re_uw.cashflow import by_year, growth_index, operating_cash_flow
from re_uw.inputs import UnderwritingInputs
from re_uw.scenarios import SCENARIOS_DIR, load_scenario

ZERO_LEASING = {
    "avg_lease_term_years": 3.0,
    "renewal_probability": 0.5,
    "rent_free_months_per_year_new": 0.0,
    "rent_free_months_per_year_renewal": 0.0,
    "commission_months_new": 0.0,
    "commission_months_renewal": 0.0,
    "fitout_contribution_psf_new": 0.0,
}

BASE = {
    "scenario": {"name": "test"},
    "analysis": {"start_year": 2027, "hold_period_years": 2, "discount_rate": 0.07},
    "property": {"name": "T", "tenure": "freehold"},
    "components": [{
        "name": "Office",
        "use_type": "office",
        "nla_sqft": 1_000,
        "revenue": {"rent_psf_pm": 10.0, "rent_growth": 0.10, "vacancy": 0.10, "credit_loss": 0.0},
        "leasing": ZERO_LEASING,
        "opex_psf_pm": 1.0,
        "opex_growth": 0.0,
    }],
    "acquisition": {"purchase_price": 1_000_000},
    "expenses": {"property_tax_rate": 0.10, "av_to_gpr_ratio": 0.90,
                 "management_fee_pct": 0.0, "insurance_annual": 0.0},
    "capex": {"reserve_psf_pa": 0.0},
    "exit": {"exit_cap_rate": 0.05},
    "waterfall": {"pref_rate": 0.08, "tiers": [{"up_to_irr": None, "gp_promote": 0.2}]},
}


def _inputs(**patch) -> UnderwritingInputs:
    d = copy.deepcopy(BASE)
    for path, value in patch.items():
        node = d
        *parents, leaf = path.split("__")
        for key in parents:
            node = node[int(key)] if key.isdigit() else node[key]
        node[leaf] = value
    return UnderwritingInputs.model_validate(d)


A = pytest.approx


# --- helpers --------------------------------------------------------------------
def test_growth_index():
    assert growth_index(3, 0.10) == A([1.0, 1.1, 1.21])
    assert growth_index(3, 0.10, {2: 0.0}) == A([1.0, 1.0, 1.1])


def test_by_year():
    assert by_year(3, 0.1, {2: 0.5}) == A([0.1, 0.5, 0.1])


# --- base case --------------------------------------------------------------------
def test_projects_hold_plus_one_years():
    ocf = operating_cash_flow(_inputs())
    assert ocf.years == [1, 2, 3]
    assert ocf.calendar_years == [2027, 2028, 2029]
    assert list(ocf.table().columns) == ["Y1 2027", "Y2 2028", "Y3 2029 (fwd)"]


def test_base_case_by_hand():
    ocf = operating_cash_flow(_inputs())
    # GPR = 1,000 x 10 x 12 = 120,000, growing 10%
    assert ocf["gpr"] == A([120_000, 132_000, 145_200])
    assert ocf["vacancy_loss"] == A([12_000, 13_200, 14_520])
    assert ocf["egi"] == A([108_000, 118_800, 130_680])
    # opex 1,000 x 1 x 12, no growth
    assert ocf["component_opex"] == A([12_000, 12_000, 12_000])
    # property tax = 10% x 90% x GPR (before vacancy)
    assert ocf["property_tax"] == A([10_800, 11_880, 13_068])
    # NOI Y1 = 108,000 - 12,000 - 10,800 = 85,200
    assert ocf.noi == A([85_200, 94_920, 105_612])
    assert ocf.cf_before_debt == A(ocf.noi)


def test_property_tax_ignores_vacancy():
    full = operating_cash_flow(_inputs(components__0__revenue__vacancy=0.0))
    half = operating_cash_flow(_inputs(components__0__revenue__vacancy=0.5))
    assert full["property_tax"] == A(half["property_tax"])


def test_annual_value_input_grows_with_gpr():
    ocf = operating_cash_flow(_inputs(expenses__annual_value_year1=100_000))
    # AV 100,000 then x GPR growth (10%); tax at 10%
    assert ocf["annual_value"] == A([100_000, 110_000, 121_000])
    assert ocf["property_tax"] == A([10_000, 11_000, 12_100])


# --- leasing, recoveries, turnover ---------------------------------------------
def test_leasing_rent_free_commissions_fitout():
    leasing = {**ZERO_LEASING, "renewal_probability": 0.5,
               "rent_free_months_per_year_new": 1.0, "rent_free_months_per_year_renewal": 0.0,
               "commission_months_new": 2.0, "commission_months_renewal": 1.0,
               "fitout_contribution_psf_new": 6.0}
    ocf = operating_cash_flow(_inputs(components__0__revenue__vacancy=0.0,
                                      components__0__revenue__credit_loss=0.01,
                                      components__0__revenue__rent_growth=0.0,
                                      components__0__leasing=leasing))
    c = ocf.components[0]
    # blended rent-free = 0.5 x 0 + 0.5 x 1 = 0.5 month/yr -> 120,000 x 0.5 / 12 = 5,000
    assert c.rent_free[0] == A(5_000)
    # credit loss on rent after rent-free: 1% x 115,000 = 1,150
    assert c.credit_loss[0] == A(1_150)
    assert c.base_rent_collected[0] == A(113_850)
    # 1/3 of 1,000 sq ft re-leases; blended commission 1.5 months x $10 -> 333.33 x 15 = 5,000
    assert c.area_released_sqft[0] == A(1_000 / 3)
    assert c.leasing_commissions[0] == A(5_000)
    # fit-out on new leases only: 333.33 x 0.5 x 6 = 1,000
    assert c.fitout_contributions[0] == A(1_000)
    # below NOI: CF before debt = NOI - 5,000 - 1,000
    assert ocf.cf_before_debt[0] == A(ocf.noi[0] - 6_000)


def test_turnover_rent_and_recoveries():
    ocf = operating_cash_flow(_inputs(components__0__turnover_rent_pct=0.10,
                                      components__0__recoveries_psf_pm=2.0,
                                      components__0__recoveries_growth=0.0))
    c = ocf.components[0]
    # turnover = 10% of base rent collected (108,000)
    assert c.turnover_rent[0] == A(10_800)
    # recoveries on occupied area: 900 sq ft x 2 x 12 = 21,600
    assert c.recoveries[0] == A(21_600)
    assert ocf["egi"][0] == A(108_000 + 10_800 + 21_600)


# --- overrides, other income, fees, capex ----------------------------------------
def test_year_overrides():
    ocf = operating_cash_flow(_inputs(components__0__revenue__vacancy_overrides={2: 0.5},
                                      components__0__revenue__rent_growth_overrides={3: 0.0}))
    c = ocf.components[0]
    assert c.vacancy_rate == A([0.1, 0.5, 0.1])
    assert c.rent_psf_pm == A([10.0, 11.0, 11.0])
    assert c.vacancy_loss[1] == A(132_000 * 0.5)


def test_other_income_mgmt_fee_insurance():
    ocf = operating_cash_flow(_inputs(
        other_income=[{"name": "Carpark", "annual_amount": 12_000, "growth": 0.05}],
        expenses__management_fee_pct=0.03,
        expenses__insurance_annual=1_000,
        expenses__insurance_growth=0.10,
    ))
    assert ocf["other_income"] == A([12_000, 12_600, 13_230])
    assert ocf["egi"][0] == A(120_000)  # 108,000 rent + 12,000 carpark
    assert ocf["management_fee"][0] == A(3_600)  # 3% x 120,000
    assert ocf["insurance"] == A([1_000, 1_100, 1_210])
    assert ocf.noi[0] == A(120_000 - 12_000 - 10_800 - 3_600 - 1_000)


def test_capex_reserve_and_one_off():
    ocf = operating_cash_flow(_inputs(capex__reserve_psf_pa=2.0, capex__reserve_growth=0.5,
                                      capex__one_off={2: 7_000}))
    assert ocf["capex_reserve"] == A([2_000, 3_000, 4_500])
    assert ocf["capex_one_off"] == A([0, 7_000, 0])  # never in the forward year
    assert ocf.cf_before_debt == A(ocf.noi - ocf["capex_reserve"] - ocf["capex_one_off"])


def test_two_components_sum():
    d = copy.deepcopy(BASE)
    retail = copy.deepcopy(d["components"][0]) | {"name": "Retail", "use_type": "retail"}
    d["components"].append(retail)
    ocf = operating_cash_flow(UnderwritingInputs.model_validate(d))
    single = operating_cash_flow(_inputs())
    assert ocf["gpr"] == A(2 * single["gpr"])
    assert ocf.noi == A(2 * single.noi)


# --- sample scenario: internal consistency ---------------------------------------
def test_sample_table_columns_add_up():
    inp = load_scenario(SCENARIOS_DIR / "sample_sg_cbd_office_retail.json")
    t = operating_cash_flow(inp).table()
    rev = ["Gross potential rent", "Vacancy loss", "Rent-free", "Credit loss"]
    assert np.allclose(t.loc[rev].sum(), t.loc["Base rent collected"])
    egi = ["Base rent collected", "Turnover rent", "Recoveries", "Other income"]
    assert np.allclose(t.loc[egi].sum(), t.loc["Effective gross income"])
    opex = ["Component opex", "Property tax", "Management fee", "Insurance"]
    assert np.allclose(t.loc[opex].sum(), t.loc["Total operating expenses"])
    assert np.allclose(t.loc["Effective gross income"] + t.loc["Total operating expenses"],
                       t.loc["Net operating income"])
    below = ["Net operating income", "Leasing commissions", "Fit-out contributions",
             "Capex reserve", "One-off capex"]
    assert np.allclose(t.loc[below].sum(), t.loc["Cash flow before debt"])


def test_sample_year1_noi_and_cap_rate():
    inp = load_scenario(SCENARIOS_DIR / "sample_sg_cbd_office_retail.json")
    noi1 = operating_cash_flow(inp).noi[0]
    # Regression guard (hand-reconciled 2026-10-19): ~S$32.6m, entry cap ~3.67%
    assert noi1 == A(32_633_000, rel=1e-3)
    assert noi1 / inp.acquisition.purchase_price == A(0.0367, abs=5e-4)
