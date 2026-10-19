"""Operating cash flow (Phase 3): rent through to cash flow before debt service.

All formulas are documented in docs/methodology.md ("Operating cash flow").
Projections run for Years 1..N+1 (N = hold period); Year N+1 exists only to value the
exit on forward NOI and carries no one-off capex.

Internally every line is a positive amount in a numpy array indexed by year (position 0 =
Year 1). The presentation tables flip deductions to negative so each column adds up.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .inputs import SpaceComponent, UnderwritingInputs

Array = np.ndarray


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def growth_index(n_years: int, growth: float, overrides: dict[int, float] | None = None) -> Array:
    """Cumulative growth factors for Years 1..n. Year 1 = 1.0; Year t = Year t-1 x (1 + g_t)."""
    overrides = overrides or {}
    idx = np.ones(n_years)
    for t in range(2, n_years + 1):
        idx[t - 1] = idx[t - 2] * (1.0 + overrides.get(t, growth))
    return idx


def by_year(n_years: int, flat: float, overrides: dict[int, float] | None = None) -> Array:
    """Per-year values: the flat assumption, replaced by overrides where given."""
    overrides = overrides or {}
    return np.array([overrides.get(t, flat) for t in range(1, n_years + 1)], dtype=float)


# ---------------------------------------------------------------------------
# Component level
# ---------------------------------------------------------------------------
@dataclass
class ComponentCashFlow:
    name: str
    rent_psf_pm: Array
    vacancy_rate: Array
    gpr: Array
    vacancy_loss: Array
    rent_free: Array
    credit_loss: Array
    base_rent_collected: Array
    turnover_rent: Array
    recoveries: Array
    revenue: Array
    opex: Array
    area_released_sqft: Array
    leasing_commissions: Array
    fitout_contributions: Array


def component_cash_flow(c: SpaceComponent, n_years: int) -> ComponentCashFlow:
    r = c.revenue
    ls = c.leasing
    p = ls.renewal_probability

    rent_psf = r.rent_psf_pm * growth_index(n_years, r.rent_growth, r.rent_growth_overrides)
    v = by_year(n_years, r.vacancy, r.vacancy_overrides)

    gpr = c.nla_sqft * rent_psf * 12.0
    vacancy_loss = gpr * v
    occupied_rent = gpr - vacancy_loss

    # Steady state: m months free per lease year => m months' rent lost per year on occupied area.
    m_bar = p * ls.rent_free_months_per_year_renewal + (1 - p) * ls.rent_free_months_per_year_new
    rent_free = occupied_rent * m_bar / 12.0
    credit_loss = (occupied_rent - rent_free) * r.credit_loss
    base_rent_collected = occupied_rent - rent_free - credit_loss
    turnover_rent = base_rent_collected * c.turnover_rent_pct

    occupied_sqft = c.nla_sqft * (1.0 - v)
    recoveries = (occupied_sqft * c.recoveries_psf_pm * 12.0
                  * growth_index(n_years, c.recoveries_growth))
    revenue = base_rent_collected + turnover_rent + recoveries

    opex = c.nla_sqft * c.opex_psf_pm * 12.0 * growth_index(n_years, c.opex_growth)

    area_released = occupied_sqft / ls.avg_lease_term_years
    c_bar = p * ls.commission_months_renewal + (1 - p) * ls.commission_months_new
    leasing_commissions = area_released * rent_psf * c_bar
    fitout_contributions = area_released * (1 - p) * ls.fitout_contribution_psf_new

    return ComponentCashFlow(
        name=c.name,
        rent_psf_pm=rent_psf,
        vacancy_rate=v,
        gpr=gpr,
        vacancy_loss=vacancy_loss,
        rent_free=rent_free,
        credit_loss=credit_loss,
        base_rent_collected=base_rent_collected,
        turnover_rent=turnover_rent,
        recoveries=recoveries,
        revenue=revenue,
        opex=opex,
        area_released_sqft=area_released,
        leasing_commissions=leasing_commissions,
        fitout_contributions=fitout_contributions,
    )


# ---------------------------------------------------------------------------
# Property level
# ---------------------------------------------------------------------------
@dataclass
class OperatingCashFlow:
    years: list[int]  # 1..N+1
    calendar_years: list[int]
    hold_period_years: int
    components: list[ComponentCashFlow]
    other_income_lines: dict[str, Array]
    lines: dict[str, Array] = field(default_factory=dict)  # property-level, positive amounts

    # -- convenience ------------------------------------------------------------
    def __getitem__(self, key: str) -> Array:
        return self.lines[key]

    @property
    def noi(self) -> Array:
        return self.lines["noi"]

    @property
    def cf_before_debt(self) -> Array:
        return self.lines["cf_before_debt"]

    def table(self, scale: float = 1.0) -> pd.DataFrame:
        """Property-level annual cash flow; deductions negative; columns 'Y1 2027', ..."""
        L = self.lines
        rows: list[tuple[str, Array]] = [
            ("Gross potential rent", L["gpr"]),
            ("Vacancy loss", -L["vacancy_loss"]),
            ("Rent-free", -L["rent_free"]),
            ("Credit loss", -L["credit_loss"]),
            ("Base rent collected", L["base_rent_collected"]),
            ("Turnover rent", L["turnover_rent"]),
            ("Recoveries", L["recoveries"]),
            ("Other income", L["other_income"]),
            ("Effective gross income", L["egi"]),
            ("Component opex", -L["component_opex"]),
            ("Property tax", -L["property_tax"]),
            ("Management fee", -L["management_fee"]),
            ("Insurance", -L["insurance"]),
            ("Total operating expenses", -L["total_opex"]),
            ("Net operating income", L["noi"]),
            ("Leasing commissions", -L["leasing_commissions"]),
            ("Fit-out contributions", -L["fitout_contributions"]),
            ("Capex reserve", -L["capex_reserve"]),
            ("One-off capex", -L["capex_one_off"]),
            ("Cash flow before debt", L["cf_before_debt"]),
        ]
        cols = [self._col(t, cy) for t, cy in zip(self.years, self.calendar_years, strict=True)]
        return pd.DataFrame({k: v / scale + 0.0 for k, v in rows}, index=cols).T  # +0.0: no -0

    def component_table(self, name: str, scale: float = 1.0) -> pd.DataFrame:
        """Per-component lines. Rent psf pm and vacancy % are never scaled."""
        c = next(x for x in self.components if x.name == name)
        money = [
            ("Gross potential rent", c.gpr),
            ("Vacancy loss", -c.vacancy_loss),
            ("Rent-free", -c.rent_free),
            ("Credit loss", -c.credit_loss),
            ("Base rent collected", c.base_rent_collected),
            ("Turnover rent", c.turnover_rent),
            ("Recoveries", c.recoveries),
            ("Component revenue", c.revenue),
            ("Component opex", -c.opex),
            ("Leasing commissions", -c.leasing_commissions),
            ("Fit-out contributions", -c.fitout_contributions),
        ]
        rows: dict[str, Array] = {"Rent psf pm": c.rent_psf_pm, "Vacancy %": c.vacancy_rate * 100}
        rows |= {k: v / scale + 0.0 for k, v in money}
        cols = [self._col(t, cy) for t, cy in zip(self.years, self.calendar_years, strict=True)]
        return pd.DataFrame(rows, index=cols).T

    def _col(self, t: int, cy: int) -> str:
        return f"Y{t} {cy}" + (" (fwd)" if t > self.hold_period_years else "")


def operating_cash_flow(inp: UnderwritingInputs) -> OperatingCashFlow:
    hold = inp.analysis.hold_period_years
    n = hold + 1  # one forward year for exit valuation
    years = list(range(1, n + 1))

    comps = [component_cash_flow(c, n) for c in inp.components]

    def total(attr: str) -> Array:
        return np.sum([getattr(c, attr) for c in comps], axis=0)

    other_lines = {
        o.name: o.annual_amount * growth_index(n, o.growth) for o in inp.other_income
    }
    other_income = np.sum(list(other_lines.values()), axis=0) if other_lines else np.zeros(n)

    gpr = total("gpr")
    egi = total("revenue") + other_income

    ex = inp.expenses
    if ex.annual_value_year1 is not None:
        annual_value = ex.annual_value_year1 * gpr / gpr[0]
    else:
        annual_value = ex.av_to_gpr_ratio * gpr
    property_tax = ex.property_tax_rate * annual_value
    management_fee = ex.management_fee_pct * egi
    insurance = ex.insurance_annual * growth_index(n, ex.insurance_growth)
    component_opex = total("opex")
    total_opex = component_opex + property_tax + management_fee + insurance
    noi = egi - total_opex

    leasing_commissions = total("leasing_commissions")
    fitout = total("fitout_contributions")
    capex_reserve = (inp.capex.reserve_psf_pa * inp.total_nla_sqft
                     * growth_index(n, inp.capex.reserve_growth))
    capex_one_off = by_year(n, 0.0, inp.capex.one_off)
    cf_before_debt = noi - leasing_commissions - fitout - capex_reserve - capex_one_off

    lines = {
        "gpr": gpr,
        "vacancy_loss": total("vacancy_loss"),
        "rent_free": total("rent_free"),
        "credit_loss": total("credit_loss"),
        "base_rent_collected": total("base_rent_collected"),
        "turnover_rent": total("turnover_rent"),
        "recoveries": total("recoveries"),
        "other_income": other_income,
        "egi": egi,
        "component_opex": component_opex,
        "annual_value": annual_value,
        "property_tax": property_tax,
        "management_fee": management_fee,
        "insurance": insurance,
        "total_opex": total_opex,
        "noi": noi,
        "leasing_commissions": leasing_commissions,
        "fitout_contributions": fitout,
        "capex_reserve": capex_reserve,
        "capex_one_off": capex_one_off,
        "cf_before_debt": cf_before_debt,
    }
    start = inp.analysis.start_year
    return OperatingCashFlow(
        years=years,
        calendar_years=[start + t - 1 for t in years],
        hold_period_years=hold,
        components=comps,
        other_income_lines=other_lines,
        lines=lines,
    )
