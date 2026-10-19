# Methodology

How the model calculates each number. Sections marked *planned* are specified here and
implemented in the phase shown. Field names refer to `docs/inputs.md`.

## Global assumptions
- **Ex-GST.** All figures exclude GST (9% from 1 Jan 2024). GST on commercial rent is a
  pass-through for a GST-registered landlord. The acquisition is assumed to qualify as a
  **transfer of a going concern** (tenanted building + leases; buyer GST-registered and continues
  the letting business), so no GST is charged on the price.
- **Pre-tax.** Returns are before income tax at the holding-vehicle or investor level.
- **Annual periods.** Year 0 = acquisition (closing). Years 1..N = hold
  (`analysis.hold_period_years`); sale at the end of Year N. Operating projections run to
  **Year N+1** so the exit can be valued on forward NOI. Year 1 = `analysis.start_year`.

## Acquisition (Phase 2b: stamp duty implemented in `re_uw/sg_tax.py`)
- **Stamp duty**
  - `deal_structure = "asset"`: Buyer's Stamp Duty, non-residential tiers (contracts on or
    after 15 Feb 2023): 1% on first $180k, 2% next $180k, 3% next $640k, 4% next $500k,
    5% above $1.5m. Equivalent to 5% × price − $30,400 for prices above $1.5m.
  - `deal_structure = "share"`: 0.2% of price (proxy for the higher of price and NAV of the
    shares). Additional Conveyance Duties apply only to residential property-holding entities.
  - `stamp_duty_override_pct` replaces either calculation.
  - No seller's stamp duty is modelled at exit (office/retail).
- **Other costs** = price × `other_costs_pct`
- **Total uses**: see Sources and uses below

## Operating cash flow (Phase 3: implemented in `re_uw/cashflow.py`)
Per space component *c*, year *t* (NLA = `nla_sqft`). Run `python -m re_uw.report` to print it.
All growth applies from Year 2 (Year 1 = the input value).

**Revenue**
- Rent psf pm: `rent_psf_pm` in Year 1; then × (1 + g_t), g_t = `rent_growth_overrides[t]`
  or `rent_growth`
- **GPR** (gross potential rent) = NLA × rent psf pm × 12
- **Vacancy loss** = GPR × v_t (`vacancy_overrides[t]` or `vacancy`)
- **Rent-free** = (GPR − vacancy loss) × m̄ / 12, where
  m̄ = p × `rent_free_months_per_year_renewal` + (1 − p) × `rent_free_months_per_year_new`,
  p = `renewal_probability`. (A lease of T years with m months free per lease year gives
  m × T free months; 1/T of occupied area re-leases each year, so the annual loss is m months'
  rent on occupied area.)
- **Credit loss** = (GPR − vacancy loss − rent-free) × `credit_loss` (no bad debt on free months)
- **Base rent collected** = GPR − vacancy − rent-free − credit loss
- **Turnover rent** = base rent collected × `turnover_rent_pct`
- **Recoveries** = NLA × (1 − v_t) × `recoveries_psf_pm` × 12, grown at `recoveries_growth`
- **Component revenue** = base rent collected + turnover rent + recoveries

**Property level**
- **Other income**: each line's `annual_amount`, grown at its `growth` from Year 2
- **EGI** = Σ component revenue + other income

**Operating expenses**
- **Component opex** = NLA × `opex_psf_pm` × 12, grown at `opex_growth`
- **Annual Value (AV)**: if `annual_value_year1` is set, AV_t = AV_1 × GPR_t / GPR_1 (total GPR);
  else AV_t = `av_to_gpr_ratio` × total GPR_t. AV uses GPR **before vacancy**: IRAS assesses
  market rent whether let or vacant, and there is no vacancy refund (removed 2014).
- **Property tax** = `property_tax_rate` × AV_t
- **Management fee** (property manager) = `management_fee_pct` × EGI
- **Insurance** = `insurance_annual`, grown at `insurance_growth`
- **NOI** = EGI − component opex − property tax − management fee − insurance

**Below NOI**
- Area re-leased_t = NLA × (1 − v_t) / `avg_lease_term_years`
- **Leasing commissions** = area re-leased × rent psf pm ×
  [p × `commission_months_renewal` + (1 − p) × `commission_months_new`]
- **Fit-out contributions** = area re-leased × (1 − p) × `fitout_contribution_psf_new`
  (flat nominal $ psf; not inflated)
- **Capex** = reserve (`reserve_psf_pa` × total NLA, grown at `reserve_growth`) + `capex.one_off[t]`
- **CF before debt** = NOI − leasing commissions − fit-out contributions − capex

## Debt (Phase 4: `re_uw/debt.py`)
- **Sizing** on Year 1: loan = min(`target_ltv` × price, NOI₁ / (`min_dscr` × debt constant),
  NOI₁ / `min_debt_yield`), using only the constraints that are set. Debt constant = Year 1
  all-in rate if Year 1 is interest-only, else the annuity constant over `amortization_years`.
  The binding constraint is reported.
- **Rate**: all-in rate_t = (`base_rate_overrides[t]` or `base_rate`) + `margin` (floating).
- **Interest**_t = opening balance × rate_t.
- **Amortisation**: none in the first `io_years`, or at all if `amortization_years = 0`. After
  that, the payment is re-solved each year as an annuity on the opening balance over the
  remaining amortisation term at that year's rate; principal = payment − interest.
- **Balloon**: the closing balance at the end of Year N is repaid from sale proceeds.
- **Loan fee** = loan × `upfront_fee_pct`, paid at closing.
- **DSCR**_t = NOI_t / (interest + principal); **ICR**_t = NOI_t / interest;
  **debt yield** = NOI₁ / loan.

## Sources and uses (Phase 4: `re_uw/returns.py`)
- **Property cost** = price + stamp duty + other costs + `upfront_capex`
- **Total uses** = property cost + loan fee + acquisition fee
- **Equity** = total uses − loan

## Exit (Phase 4)
- NOI basis = NOI_{N+1} (`noi_basis = "forward"`) or NOI_N (`"trailing"`)
- **Gross sale price** = NOI basis / `exit_cap_rate`
- **Selling costs** = gross × `selling_cost_pct`; **divestment fee** = gross × `divestment_fee_pct`
- No seller's stamp duty (office/retail)

## Fund fees (Phase 4)
- **Acquisition fee** = price × `acquisition_fee_pct` (Year 0)
- **Asset management fee**_t = `asset_mgmt_fee_pct` × basis_t, where basis is
  `gav`: NOI_{t+1} / exit cap rate (a year-end value estimate), `purchase_price`, or
  `equity`: equity at closing
- **Divestment fee**: see Exit
- Fees are fund-level: they are excluded from unlevered (property) returns.

## Cash flow streams and returns (Phase 4)
Years 0..N, end-of-year convention:
- **Unlevered** = −property cost (Y0); CF before debt (Y1..N); + gross sale − selling costs (YN)
- **Levered, gross of fund fees** = −(equity − acquisition fee) (Y0);
  CF before debt − debt service (Y1..N); + net sale − loan repayment (YN)
- **Equity cash flow, net of fees** = −equity (Y0); CF before debt − debt service − AM fee
  (Y1..N); + net sale − divestment fee − loan repayment (YN). The waterfall distributes this.
- **IRR**: rate where NPV = 0 (bisection). **Multiple** = Σ inflows / Σ outflows.
  **NPV** at `analysis.discount_rate`, first flow undiscounted.
- **Entry cap** = NOI₁ / price; **yield on cost** = NOI₁ / property cost
- **Cash-on-cash**_t = equity cash flow_t excluding sale / equity at closing
- **Peak equity** = most negative cumulative equity cash flow
- **Cross-check**: `backend/scripts/make_crosscheck_xlsx.py` rebuilds this section with live
  Excel formulas and compares with Python.

## Equity waterfall (Phase 5: `re_uw/waterfall.py`)
Distributes the **net equity cash flow** (after fund fees). GP co-invests g = `gp_coinvest_pct`.
- Contributions (negative years) split pro rata: LP (1 − g), GP g.
- Each hurdle h (the pref and each tier's `up_to_irr`) keeps an LP balance:
  B_h(t) = B_h(t−1) × (1 + h) + LP contribution(t) − LP distribution(t).
- Distributions fill segments in order:
  - Segment 0, return of capital + pref: pro rata (LP 1 − g) until B_pref = 0.
  - Segment k (tier k, promote p): LP share = (1 − p)(1 − g), GP share = p + (1 − p)g, until
    B_{h_k} = 0. Cash needed = B_{h_k} / LP share. The last tier (`up_to_irr = null`) is uncapped.
- No GP catch-up. **GP promote** = GP distributions − g × total distributions.
- With the waterfall disabled, everything is split pro rata.
- Worked example (tests/test_waterfall.py): −100 / +150, pref 10%, 20% promote to a 20% IRR then
  30%: LP receives 139.25 (IRR 39.25%), GP 10.75.

## Sensitivity (Phase 10: `re_uw/sensitivity.py`)
- Parameters are paths into the inputs (price, exit cap, base rate, LTV, AM fee, selling costs,
  and per component: rent, rent growth, vacancy, opex). Each has a default step (absolute, e.g.
  25 bp on the exit cap, or relative, e.g. 5% of rent).
- **Two-way grid**: the full model is re-run for every (x, y) pair; cells whose inputs break a
  validation rule show n/a.
- **Tornado**: each parameter moved one step down and up on its own; bars sorted by swing.
