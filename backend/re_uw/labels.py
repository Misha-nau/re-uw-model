"""Display metadata for result metrics (shared by the CLI report, API and UI)."""

from __future__ import annotations

from typing import Literal

Fmt = Literal["money", "pct", "ratio", "psf"]

# key -> (label, format, group)
METRICS: dict[str, tuple[str, Fmt, str]] = {
    "noi_year1": ("Year 1 NOI", "money", "Property"),
    "entry_cap_rate": ("Entry cap rate (NOI1 / price)", "pct", "Property"),
    "yield_on_cost": ("Yield on cost (NOI1 / all-in cost)", "pct", "Property"),
    "price_psf": ("Price psf", "psf", "Property"),
    "exit_value": ("Exit value (gross)", "money", "Property"),
    "exit_value_psf": ("Exit value psf", "psf", "Property"),
    "unlevered_irr": ("Unlevered IRR", "pct", "Unlevered"),
    "unlevered_multiple": ("Unlevered multiple", "ratio", "Unlevered"),
    "unlevered_npv": ("Unlevered NPV", "money", "Unlevered"),
    "unlevered_profit": ("Unlevered profit", "money", "Unlevered"),
    "levered_irr_gross": ("Levered IRR (gross of fund fees)", "pct", "Equity"),
    "levered_multiple_gross": ("Levered multiple (gross of fund fees)", "ratio", "Equity"),
    "levered_irr": ("Equity IRR (net of fees)", "pct", "Equity"),
    "levered_multiple": ("Equity multiple (net)", "ratio", "Equity"),
    "levered_npv": ("Equity NPV (net)", "money", "Equity"),
    "levered_profit": ("Equity profit (net)", "money", "Equity"),
    "equity": ("Equity at closing", "money", "Equity"),
    "peak_equity": ("Peak equity", "money", "Equity"),
    "avg_cash_on_cash": ("Avg cash-on-cash (net)", "pct", "Equity"),
    "year1_cash_on_cash": ("Year 1 cash-on-cash", "pct", "Equity"),
    "lp_irr": ("LP IRR", "pct", "LP / GP"),
    "lp_multiple": ("LP multiple", "ratio", "LP / GP"),
    "lp_profit": ("LP profit", "money", "LP / GP"),
    "gp_irr": ("GP IRR", "pct", "LP / GP"),
    "gp_multiple": ("GP multiple", "ratio", "LP / GP"),
    "gp_profit": ("GP profit", "money", "LP / GP"),
    "gp_promote": ("GP promote", "money", "LP / GP"),
    "loan": ("Loan", "money", "Debt"),
    "ltv": ("LTV", "pct", "Debt"),
    "ltc": ("LTC", "pct", "Debt"),
    "debt_yield_year1": ("Year 1 debt yield", "pct", "Debt"),
    "dscr_year1": ("Year 1 DSCR", "ratio", "Debt"),
    "dscr_min": ("Min DSCR", "ratio", "Debt"),
    "icr_year1": ("Year 1 ICR", "ratio", "Debt"),
    "icr_min": ("Min ICR", "ratio", "Debt"),
    "exit_ltv": ("LTV at exit", "pct", "Debt"),
    "total_fund_fees": ("Total fund fees", "money", "Fees"),
}
