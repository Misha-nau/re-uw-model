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
    Fees,
    LeasingAssumptions,
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
            "5-year hold, 50% LTV interest-only, LP/GP JV with promote. "
            "PLACEHOLDERS to confirm: leasing commissions, fit-out contribution, "
            "retail recoveries and turnover rent, fund fees."
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
                rent_psf_pm=12.50,  # CBRE Q3 2026 Core CBD Grade A: 12.75
                rent_growth=0.020,
                vacancy=0.06,
                credit_loss=0.005,
            ),
            recoveries_psf_pm=0.0,  # gross lease: service charge inside rent
            turnover_rent_pct=0.0,
            leasing=LeasingAssumptions(
                avg_lease_term_years=3.0,
                renewal_probability=0.65,
                rent_free_months_per_year_new=1.0,  # Savills Dec 2025: ~1 month per lease year
                rent_free_months_per_year_renewal=0.5,
                commission_months_new=2.0,  # PLACEHOLDER
                commission_months_renewal=1.0,  # PLACEHOLDER
                fitout_contribution_psf_new=5.0,  # PLACEHOLDER
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
            recoveries_psf_pm=1.50,  # PLACEHOLDER: service charge + A&P billed separately
            recoveries_growth=0.025,
            turnover_rent_pct=0.05,  # PLACEHOLDER: GTO uplift on base rent
            leasing=LeasingAssumptions(
                avg_lease_term_years=3.0,
                renewal_probability=0.60,
                rent_free_months_per_year_new=0.5,
                rent_free_months_per_year_renewal=0.0,
                commission_months_new=2.0,  # PLACEHOLDER
                commission_months_renewal=1.0,  # PLACEHOLDER
                fitout_contribution_psf_new=0.0,
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
        deal_structure="asset",
        stamp_duty_override_pct=None,
        other_costs_pct=0.01,
        upfront_capex=5_000_000,
    ),
    expenses=PropertyExpenses(
        property_tax_rate=0.10,
        annual_value_year1=None,
        av_to_gpr_ratio=0.90,
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
        base_rate_overrides={},
        margin=0.011,
        amortization_years=0,
        io_years=0,
        upfront_fee_pct=0.005,
    ),
    exit=Exit(exit_cap_rate=0.0375, selling_cost_pct=0.01, noi_basis="forward"),
    fees=Fees(  # PLACEHOLDERS: replace with actual fund terms
        enabled=True,
        asset_mgmt_fee_pct=0.005,
        asset_mgmt_fee_basis="gav",
        acquisition_fee_pct=0.01,
        divestment_fee_pct=0.005,
    ),
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

def _upside() -> UnderwritingInputs:
    """Same building, bought via a share deal, stronger growth, tighter exit."""
    d = SAMPLE.model_dump()
    d["scenario"] = {
        "name": "Upside - share deal, 3.5% exit, 3.5% office growth",
        "description": "Sample deal acquired via its holding vehicle (0.2% share duty), office "
                       "rent growth 3.5% pa, exit cap 3.50%. Exercises the promote tiers.",
    }
    d["acquisition"]["deal_structure"] = "share"
    d["components"][0]["revenue"]["rent_growth"] = 0.035
    d["exit"]["exit_cap_rate"] = 0.035
    return UnderwritingInputs.model_validate(d)


if __name__ == "__main__":
    for inputs, name in ((SAMPLE, "sample_sg_cbd_office_retail.json"),
                         (_upside(), "upside_sg_cbd_office_retail.json")):
        print(f"wrote {save_scenario(inputs, SCENARIOS_DIR / name)}")
