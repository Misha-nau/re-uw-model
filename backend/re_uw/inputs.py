"""Underwriting input model (Phase 2).

Conventions
-----------
* All rates are decimals: 0.05 means 5%.
* Rents and opex for space components are in currency per sq ft per MONTH (SG "psf pm").
* Periods are annual. Year 0 = acquisition (closing). Years 1..N = hold. The asset is
  sold at the end of Year N; with ``exit.noi_basis = "forward"`` the exit value uses Year N+1 NOI.
* Per-year override dictionaries are keyed by year number (1-based). A value in the dict
  replaces the flat assumption for that year only.

Extensibility
-------------
Revenue for each space component is described by a model with a ``method`` discriminator.
Only ``"market"`` exists today. A ``"rent_roll"`` model will be added later as another
member of the ``Revenue`` union, without changes elsewhere in the inputs.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# Reusable field types
# ---------------------------------------------------------------------------
Pct = Annotated[float, Field(ge=0.0, le=1.0)]
"""A rate between 0% and 100% (vacancy, LTV, fees...)."""

Growth = Annotated[float, Field(ge=-0.5, le=0.5)]
"""An annual growth rate; may be negative."""

Money = Annotated[float, Field(ge=0.0)]
YearOverrides = dict[Annotated[int, Field(ge=1)], float]


class _Model(BaseModel):
    """Base: reject unknown fields so typos in scenario JSON fail loudly."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


# ---------------------------------------------------------------------------
# Scenario / analysis
# ---------------------------------------------------------------------------
class ScenarioMeta(_Model):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


class Analysis(_Model):
    start_year: int = Field(2027, ge=2000, le=2100, description="Calendar year of Year 1")
    hold_period_years: int = Field(5, ge=1, le=30)
    discount_rate: Pct = Field(0.07, description="Used for NPV of unlevered and levered flows")
    currency: str = Field("SGD", min_length=3, max_length=3)


# ---------------------------------------------------------------------------
# Property
# ---------------------------------------------------------------------------
class PropertyInfo(_Model):
    name: str = Field(min_length=1)
    address: str = ""
    submarket: str = ""
    tenure: Literal["freehold", "leasehold"] = "leasehold"
    lease_years_remaining: float | None = Field(
        None, gt=0, le=999, description="Remaining land lease at acquisition (leasehold only)"
    )
    gfa_sqft: Money | None = Field(None, description="Gross floor area (informational)")

    @model_validator(mode="after")
    def _leasehold_needs_term(self) -> PropertyInfo:
        if self.tenure == "leasehold" and self.lease_years_remaining is None:
            raise ValueError("lease_years_remaining is required for leasehold tenure")
        return self


# ---------------------------------------------------------------------------
# Space components (Office, Retail, ...)
# ---------------------------------------------------------------------------
class MarketRevenue(_Model):
    """Simple market-rent build: NLA x rent psf pm x 12, less vacancy and credit loss."""

    method: Literal["market"] = "market"
    rent_psf_pm: float = Field(gt=0, description="Year 1 gross rent, per sq ft per month")
    rent_growth: Growth = Field(description="Annual growth applied from Year 2")
    rent_growth_overrides: YearOverrides = Field(default_factory=dict)
    vacancy: Pct = Field(description="Vacancy as % of gross potential rent")
    vacancy_overrides: YearOverrides = Field(default_factory=dict)
    credit_loss: Pct = Field(0.0, description="Bad debt as % of rent after vacancy")

    @field_validator("vacancy_overrides")
    @classmethod
    def _vacancy_range(cls, v: dict[int, float]) -> dict[int, float]:
        for yr, x in v.items():
            if not 0.0 <= x <= 1.0:
                raise ValueError(f"vacancy override for year {yr} must be between 0 and 1")
        return v

    @field_validator("rent_growth_overrides")
    @classmethod
    def _growth_range(cls, v: dict[int, float]) -> dict[int, float]:
        for yr, x in v.items():
            if not -0.5 <= x <= 0.5:
                raise ValueError(f"rent growth override for year {yr} must be between -50% and 50%")
            if yr == 1:
                raise ValueError("rent growth applies from year 2; set Year 1 via rent_psf_pm")
        return v


# Future: Revenue = Annotated[MarketRevenue | RentRollRevenue, Field(discriminator="method")]
Revenue = MarketRevenue


class LeasingAssumptions(_Model):
    """Steady-state leasing costs for the market-rent method.

    Each year ``1 / avg_lease_term_years`` of the occupied area rolls. Of that, a share
    ``renewal_probability`` renews; the rest is re-let to new tenants. A rent-roll method will
    replace this with lease-by-lease expiries.
    """

    avg_lease_term_years: float = Field(3.0, gt=0, le=30, description="Typical SG office: 3 years")
    renewal_probability: Pct = Field(0.65, description="Share of expiring area that renews")
    rent_free_months_per_year_new: float = Field(
        1.0, ge=0, le=12, description="Rent-free months per lease year, new leases"
    )
    rent_free_months_per_year_renewal: float = Field(
        0.5, ge=0, le=12, description="Rent-free months per lease year, renewals"
    )
    commission_months_new: float = Field(
        2.0, ge=0, le=12, description="Leasing commission in months of rent, new leases"
    )
    commission_months_renewal: float = Field(
        1.0, ge=0, le=12, description="Leasing commission in months of rent, renewals"
    )
    fitout_contribution_psf_new: Money = Field(
        0.0, description="Landlord fit-out contribution per sq ft, new leases only"
    )


class SpaceComponent(_Model):
    name: str = Field(min_length=1, description="Display name, e.g. 'Office' or 'Retail podium'")
    use_type: Literal["office", "retail"]
    nla_sqft: float = Field(gt=0)
    revenue: Revenue
    recoveries_psf_pm: Money = Field(
        0.0,
        description="Service charge / A&P billed on top of rent, psf pm (0 for gross leases)",
    )
    recoveries_growth: Growth = 0.025
    turnover_rent_pct: Pct = Field(
        0.0, description="Turnover (GTO) rent as % uplift on base rent collected (retail)"
    )
    leasing: LeasingAssumptions = Field(default_factory=LeasingAssumptions)
    opex_psf_pm: Money = Field(
        0.0, description="Landlord operating costs (excl. property tax), per sq ft NLA per month"
    )
    opex_growth: Growth = 0.025


# ---------------------------------------------------------------------------
# Property-level income and costs
# ---------------------------------------------------------------------------
class OtherIncome(_Model):
    name: str = Field(min_length=1)
    annual_amount: Money = Field(description="Year 1 amount")
    growth: Growth = 0.0


class Acquisition(_Model):
    purchase_price: float = Field(gt=0)
    deal_structure: Literal["asset", "share"] = Field(
        "asset",
        description="asset = buy the property (BSD tiers); share = buy the holding vehicle "
        "(0.2% share duty on price as a NAV proxy)",
    )
    stamp_duty_override_pct: Pct | None = Field(
        None, description="If set, replaces the calculated stamp duty (% of price)"
    )
    other_costs_pct: Pct = Field(0.01, description="Legal, due diligence, agency, % of price")
    upfront_capex: Money = Field(0.0, description="Capex spent at closing (Year 0)")


class PropertyExpenses(_Model):
    property_tax_rate: Pct = Field(0.10, description="SG non-residential rate: 10% of Annual Value")
    annual_value_year1: Money | None = Field(
        None,
        description="IRAS Annual Value for Year 1 if known; grows in line with total GPR. "
        "If null, AV = av_to_gpr_ratio x total GPR (before vacancy)",
    )
    av_to_gpr_ratio: Pct = Field(
        0.90, description="AV as % of gross potential rent; strips the service-charge element"
    )
    management_fee_pct: Pct = Field(0.03, description="% of effective gross income")
    insurance_annual: Money = Field(0.0, description="Year 1 amount")
    insurance_growth: Growth = 0.03


class Capex(_Model):
    reserve_psf_pa: Money = Field(0.0, description="Recurring reserve per sq ft total NLA per year")
    reserve_growth: Growth = 0.025
    one_off: YearOverrides = Field(
        default_factory=dict, description="One-off capex by year, e.g. {3: 2_000_000}"
    )

    @field_validator("one_off")
    @classmethod
    def _non_negative(cls, v: dict[int, float]) -> dict[int, float]:
        if any(x < 0 for x in v.values()):
            raise ValueError("one-off capex amounts must be >= 0")
        return v


# ---------------------------------------------------------------------------
# Financing, exit, waterfall
# ---------------------------------------------------------------------------
class Debt(_Model):
    enabled: bool = True
    target_ltv: Pct = Field(0.50, description="Max loan as % of purchase price")
    min_dscr: float | None = Field(
        None, gt=0, description="If set, loan is also capped so Year 1 DSCR >= this"
    )
    min_debt_yield: Pct | None = Field(
        None, description="If set, loan is also capped so Year 1 NOI / loan >= this"
    )
    base_rate: float = Field(0.020, ge=-0.05, le=0.30, description="e.g. compounded SORA / swap")
    base_rate_overrides: YearOverrides = Field(
        default_factory=dict, description="Per-year base rate (forward curve), e.g. {1: 0.018}"
    )
    margin: Pct = Field(0.011)
    amortization_years: int = Field(
        0, ge=0, le=50, description="0 = interest-only for the whole term"
    )
    io_years: int = Field(0, ge=0, le=50, description="Interest-only years before amortisation")
    upfront_fee_pct: Pct = Field(0.005, description="% of loan amount, paid at closing")

    @field_validator("base_rate_overrides")
    @classmethod
    def _rate_range(cls, v: dict[int, float]) -> dict[int, float]:
        for yr, x in v.items():
            if not -0.05 <= x <= 0.30:
                raise ValueError(f"base rate override for year {yr} must be between -5% and 30%")
        return v

    def all_in_rate(self, year: int = 1) -> float:
        """Base rate (override for ``year`` if set) + margin."""
        return self.base_rate_overrides.get(year, self.base_rate) + self.margin


class Exit(_Model):
    exit_cap_rate: float = Field(gt=0, lt=1)
    selling_cost_pct: Pct = 0.01
    noi_basis: Literal["forward", "trailing"] = Field(
        "forward", description="forward = Year N+1 NOI, trailing = Year N NOI"
    )


class WaterfallTier(_Model):
    """Cash between the previous hurdle and ``up_to_irr`` (LP IRR) is split with a GP promote.

    ``up_to_irr = None`` means "everything above the last hurdle" and must be the final tier.
    ``gp_promote`` is the GP's extra share of the cash in this tier, on top of its pro-rata
    co-invest share of the remainder.
    """

    up_to_irr: float | None = Field(None, gt=0, lt=1)
    gp_promote: Pct


class Fees(_Model):
    """Fund / manager fees. Paid out of equity cash flow, reported separately as manager income."""

    enabled: bool = True
    asset_mgmt_fee_pct: Pct = Field(0.005, description="Annual fee, % of the chosen basis")
    asset_mgmt_fee_basis: Literal["gav", "purchase_price", "equity"] = Field(
        "gav",
        description="gav = annual value estimate (next-year NOI / exit cap rate); "
        "purchase_price = fixed on price; equity = initial equity",
    )
    acquisition_fee_pct: Pct = Field(0.01, description="% of purchase price, paid at closing")
    divestment_fee_pct: Pct = Field(0.005, description="% of gross sale price, paid at exit")


class Waterfall(_Model):
    enabled: bool = True
    gp_coinvest_pct: Pct = Field(0.10, description="GP share of total equity")
    pref_rate: float = Field(0.07, gt=0, lt=1, description="LP preferred return (IRR)")
    tiers: list[WaterfallTier] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_tiers(self) -> Waterfall:
        *bounded, last = self.tiers
        if last.up_to_irr is not None:
            raise ValueError("the last waterfall tier must have up_to_irr = null (no cap)")
        prev = self.pref_rate
        for i, t in enumerate(bounded, start=1):
            if t.up_to_irr is None:
                raise ValueError(f"only the last tier may have no cap (tier {i} has none)")
            if t.up_to_irr <= prev:
                raise ValueError(
                    f"tier {i} hurdle {t.up_to_irr:.2%} must exceed the previous hurdle {prev:.2%}"
                )
            prev = t.up_to_irr
        return self


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
class UnderwritingInputs(_Model):
    schema_version: Literal[1] = SCHEMA_VERSION
    scenario: ScenarioMeta
    analysis: Analysis = Field(default_factory=Analysis)
    property: PropertyInfo
    components: list[SpaceComponent] = Field(min_length=1)
    other_income: list[OtherIncome] = Field(default_factory=list)
    acquisition: Acquisition
    expenses: PropertyExpenses = Field(default_factory=PropertyExpenses)
    capex: Capex = Field(default_factory=Capex)
    debt: Debt = Field(default_factory=Debt)
    exit: Exit
    fees: Fees = Field(default_factory=Fees)
    waterfall: Waterfall

    # -- cross-field validation ------------------------------------------------
    @model_validator(mode="after")
    def _cross_checks(self) -> UnderwritingInputs:
        names = [c.name for c in self.components]
        if len(names) != len(set(names)):
            raise ValueError("component names must be unique")

        # Forward NOI needs one extra year of projections.
        last_year = self.analysis.hold_period_years + 1
        for c in self.components:
            r = c.revenue
            for label, d in (("rent_growth_overrides", r.rent_growth_overrides),
                             ("vacancy_overrides", r.vacancy_overrides)):
                bad = [y for y in d if y > last_year]
                if bad:
                    raise ValueError(
                        f"{c.name}: {label} has year(s) {bad} beyond the projection "
                        f"horizon (year {last_year})"
                    )
        hold = self.analysis.hold_period_years
        for label, d in (("capex.one_off", self.capex.one_off),
                         ("debt.base_rate_overrides", self.debt.base_rate_overrides)):
            bad = [y for y in d if y > hold]
            if bad:
                raise ValueError(f"{label} has year(s) {bad} after the hold period")

        if (self.property.tenure == "leasehold"
                and self.property.lease_years_remaining is not None
                and self.property.lease_years_remaining <= self.analysis.hold_period_years):
            raise ValueError("hold period must be shorter than the remaining land lease")
        return self

    # -- convenience -------------------------------------------------------------
    @property
    def total_nla_sqft(self) -> float:
        return sum(c.nla_sqft for c in self.components)

    @property
    def price_psf(self) -> float:
        return self.acquisition.purchase_price / self.total_nla_sqft
