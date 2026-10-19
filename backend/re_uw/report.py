"""Print or export a scenario's underwriting: operating cash flow, debt, returns.

Usage (from backend/):
    python -m re_uw.report                                   # sample scenario
    python -m re_uw.report ../scenarios/other.json
    python -m re_uw.report --csv ../reports/cashflow.csv     # also write CSVs (full precision)
    python -m re_uw.report --components                      # include per-component tables
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .returns import underwrite
from .scenarios import SCENARIOS_DIR, load_scenario

DEFAULT = SCENARIOS_DIR / "sample_sg_cbd_office_retail.json"

PCT = {"entry_cap_rate", "yield_on_cost", "unlevered_irr", "levered_irr_gross", "levered_irr",
       "avg_cash_on_cash", "year1_cash_on_cash", "ltv", "ltc", "debt_yield_year1", "exit_ltv"}
MULT = {"unlevered_multiple", "levered_multiple_gross", "levered_multiple", "dscr_year1",
        "dscr_min", "icr_year1", "icr_min"}
PSF = {"price_psf", "exit_value_psf"}

LABELS = {
    "noi_year1": "Year 1 NOI", "entry_cap_rate": "Entry cap rate (NOI1 / price)",
    "yield_on_cost": "Yield on cost (NOI1 / all-in cost)", "price_psf": "Price psf",
    "exit_value": "Exit value (gross)", "exit_value_psf": "Exit value psf",
    "unlevered_irr": "Unlevered IRR", "unlevered_multiple": "Unlevered multiple",
    "unlevered_npv": "Unlevered NPV", "unlevered_profit": "Unlevered profit",
    "levered_irr_gross": "Levered IRR (gross of fund fees)",
    "levered_multiple_gross": "Levered multiple (gross of fund fees)",
    "levered_irr": "Equity IRR (net of fees)", "levered_multiple": "Equity multiple (net)",
    "levered_npv": "Equity NPV (net)", "levered_profit": "Equity profit (net)",
    "equity": "Equity at closing", "peak_equity": "Peak equity",
    "avg_cash_on_cash": "Avg cash-on-cash (net)", "year1_cash_on_cash": "Year 1 cash-on-cash",
    "loan": "Loan", "ltv": "LTV", "ltc": "LTC", "debt_yield_year1": "Year 1 debt yield",
    "dscr_year1": "Year 1 DSCR", "dscr_min": "Min DSCR", "icr_year1": "Year 1 ICR",
    "icr_min": "Min ICR", "exit_ltv": "LTV at exit", "total_fund_fees": "Total fund fees",
}


def _fmt(key: str, v: float | None, cur: str) -> str:
    if v is None:
        return "n/a"
    if key in PCT:
        return f"{v:.2%}"
    if key in MULT:
        return f"{v:.2f}x"
    if key in PSF:
        return f"{cur} {v:,.0f}"
    return f"{cur} {v / 1e6:,.2f}m"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("scenario", nargs="?", default=str(DEFAULT))
    ap.add_argument("--csv", help="write cash flow CSVs; this path is the operating CF file")
    ap.add_argument("--components", action="store_true", help="print per-component tables")
    args = ap.parse_args(argv)

    inp = load_scenario(args.scenario)
    res = underwrite(inp)
    ocf = res.operating
    cur = inp.analysis.currency
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 20)

    print(f"\n{inp.scenario.name}  |  {inp.property.name}  |  {cur} millions")
    print("\n== Operating cash flow ==")
    print(ocf.table(scale=1e6).round(2).to_string())
    if args.components:
        for c in inp.components:
            print(f"\n-- {c.name} ({c.nla_sqft:,.0f} sq ft) --")
            print(ocf.component_table(c.name, scale=1e6).round(2).to_string())

    print("\n== Sources & uses ==")
    su = res.sources_uses.table()
    su["amount"] = (su["amount"] / 1e6).round(2)
    su["% of total"] = (su["% of total"] * 100).round(1)
    print(su.to_string(index=False))
    s = res.sizing
    print(f"\nLoan sizing: binding = {s.binding}; LTV amount {s.ltv_amount / 1e6:,.1f}m"
          + (f"; DSCR amount {s.dscr_amount / 1e6:,.1f}m" if s.dscr_amount is not None else "")
          + (f"; debt-yield amount {s.debt_yield_amount / 1e6:,.1f}m"
             if s.debt_yield_amount is not None else ""))

    print("\n== Debt schedule ==")
    print(res.debt_table(scale=1e6).round(2).to_string())

    print("\n== Cash flows (Years 0..N) ==")
    print(res.cash_flow_table(scale=1e6).round(2).to_string())

    print("\n== Returns and metrics ==")
    for key, label in LABELS.items():
        print(f"  {label:<40} {_fmt(key, res.metrics[key], cur)}")

    if args.csv:
        out = Path(args.csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        ocf.table().to_csv(out)
        res.cash_flow_table().to_csv(out.with_name(out.stem + "_returns.csv"))
        print(f"\nwrote {out} and {out.with_name(out.stem + '_returns.csv')}")


if __name__ == "__main__":
    main()
