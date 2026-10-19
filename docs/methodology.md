# Methodology

How the model calculates each number. Sections are filled in as each phase is built.
Field names refer to `docs/inputs.md`.

## Timeline
- Annual periods. **Year 0** = acquisition (closing). **Years 1..N** = hold
  (`analysis.hold_period_years`). Sale at the end of Year N.
- Operating projections run to **Year N+1** so the exit can be valued on forward NOI.
- Calendar labels: Year 1 = `analysis.start_year`.

## Operating cash flow (Phase 3, planned)
Per space component *c*, year *t*:
- Rent psf pm: `rent_psf_pm` in Year 1; × (1 + growth_t) each year after, where growth_t =
  `rent_growth_overrides[t]` if present, else `rent_growth`
- **Gross potential rent (GPR)** = NLA × rent psf pm × 12
- **Vacancy loss** = GPR × vacancy_t (`vacancy_overrides[t]` if present, else `vacancy`)
- **Credit loss** = (GPR − vacancy loss) × `credit_loss`
- **Effective rent** = GPR − vacancy loss − credit loss
- **Component opex** = NLA × `opex_psf_pm` × 12, grown at `opex_growth` from Year 2

Property level:
- **Other income**: each line's `annual_amount`, grown at its `growth` from Year 2
- **EGI** = Σ effective rent + other income
- **Property tax** = `property_tax_rate` × Σ effective rent (proxy for Annual Value)
- **Management fee** = `management_fee_pct` × EGI
- **Insurance**: `insurance_annual`, grown at `insurance_growth`
- **NOI** = EGI − component opex − property tax − management fee − insurance
- **Capex** = reserve (`reserve_psf_pa` × total NLA, grown) + `capex.one_off[t]`
- **CF before debt** = NOI − capex

## Acquisition (Phase 4, planned)
- Total cost = price × (1 + `stamp_duty_pct` + `other_costs_pct`) + `upfront_capex` + loan fee

## Debt (Phase 4, planned)
- Loan = min(LTV × price, DSCR-implied, debt-yield-implied); all-in rate = base + margin

## Exit and returns (Phase 4, planned)

## Equity waterfall (Phase 5, planned)
