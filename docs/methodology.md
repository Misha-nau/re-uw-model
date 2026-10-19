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
- **Total acquisition cost** *(planned, Phase 4)* = price + stamp duty + other costs +
  `upfront_capex` + loan fee + acquisition fee

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

## Debt (planned, Phase 4)
- Loan = min(LTV × price, DSCR-implied, debt-yield-implied)
- Interest rate_t = (`base_rate_overrides[t]` or `base_rate`) + `margin`

## Fees (planned, Phase 4)
- Acquisition fee = price × `acquisition_fee_pct` (Year 0)
- Asset management fee_t = `asset_mgmt_fee_pct` × basis: `gav` = NOI_{t+1} / exit cap rate,
  `purchase_price`, or `equity` (initial equity)
- Divestment fee = gross sale price × `divestment_fee_pct` (Year N)
- Fees reduce equity cash flow and are reported separately as manager income.

## Exit and returns (planned, Phase 4)

## Equity waterfall (planned, Phase 5)
