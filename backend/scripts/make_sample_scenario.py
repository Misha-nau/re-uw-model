"""Regenerate scenarios/sample_sg_cbd_office_retail.json from code.

Run from backend/:  python scripts/make_sample_scenario.py

The numbers are illustrative Singapore CBD Grade A assumptions for model testing.
They are not market advice; review them before using the model for a real deal.
"""

from re_uw.inputs import (
    Acquisition,
    Analysis,
    Capex,
    Debt,
    Exit,
    MarketRevenue,
    OtherIncome,
    PropertyExpenses,
    PropertyInfo,
    ScenarioMeta,
    SpaceComponent,
    UnderwritingInputs,
    Waterfall,
    WaterfallTier,
)
from re_uw.scenarios import SCENARIOS_DIR, save_scenario

SAMPLE = UnderwritingInputs(
    scenario=ScenarioMeta(
        name="Sample - SG CBD office + retail podium",
        description=(
            "Illustrative Grade A CBD office tower with a ground/basement retail podium. "
            "5-year hold, 50% LTV interest-only, LP/GP JV with promote."
        ),
    ),
    analysis=Analysis(start_year=2027, hold_period_years=5, discount_rate=0.07, currency="SGD"),
    property=PropertyInfo(
        name="Sample Tower",
        address="Raffles Place, Singapore",
        submarket="CBD - Raffles Place",
        tenure="leasehold",
        lease_years_remaining=85,
        gfa_sqft=400_000,
    ),
    components=[
        SpaceComponent(
            name="Office",
            use_type="office",
            nla_sqft=300_000,
            revenue=MarketRevenue(
                rent_psf_pm=11.80,
                rent_growth=0.020,
                vacancy=0.06,
                credit_loss=0.005,
            ),
            opex_psf_pm=1.40,
            opex_growth=0.025,
        ),
        SpaceComponent(
            name="Retail podium",
            use_type="retail",
            nla_sqft=20_000,
            revenue=MarketRevenue(
                rent_psf_pm=14.00,
                rent_growth=0.015,
                vacancy=0.05,
                credit_loss=0.010,
            ),
            opex_psf_pm=2.00,
            opex_growth=0.025,
        ),
    ],
    other_income=[
        OtherIncome(name="Carpark", annual_amount=600_000, growth=0.02),
        OtherIncome(name="Signage & licences", annual_amount=150_000, growth=0.02),
    ],
    acquisition=Acquisition(
        purchase_price=890_000_000,
        stamp_duty_pct=0.05,
        other_costs_pct=0.01,
        upfront_capex=5_000_000,
    ),
    expenses=PropertyExpenses(
        property_tax_rate=0.10,
        management_fee_pct=0.03,
        insurance_annual=250_000,
        insurance_growth=0.03,
    ),
    capex=Capex(reserve_psf_pa=1.50, reserve_growth=0.025, one_off={3: 3_000_000}),
    debt=Debt(
        enabled=True,
        target_ltv=0.50,
        min_dscr=1.50,
        min_debt_yield=None,
        base_rate=0.020,
        margin=0.011,
        amortization_years=0,
        io_years=0,
        upfront_fee_pct=0.005,
    ),
    exit=Exit(exit_cap_rate=0.0375, selling_cost_pct=0.01, noi_basis="forward"),
    waterfall=Waterfall(
        enabled=True,
        gp_coinvest_pct=0.10,
        pref_rate=0.07,
        tiers=[
            WaterfallTier(up_to_irr=0.10, gp_promote=0.15),
            WaterfallTier(up_to_irr=None, gp_promote=0.25),
        ],
    ),
)

if __name__ == "__main__":
    path = save_scenario(SAMPLE, SCENARIOS_DIR / "sample_sg_cbd_office_retail.json")
    print(f"wrote {path}")
