# RE Underwriting Model — Build Plan

**Status:** Phase 4 built 🔍, awaiting Misha's checkpoint review. Next: Phase 5 (equity waterfall)
**Last updated:** 2026-10-19

## How we work
- We build in short phases. Each phase ends at a **checkpoint**: Claude stops, shows what changed, and waits for Misha to confirm before starting the next phase.
- This file is the source of truth. Each checkpoint updates the phase status and the decision log below.
- No phase starts until the one before it is marked ✅.

## Goal
A real estate acquisition underwriting model for a **Singapore office building with a retail component**: a Python calculation engine behind a web UI, where you can:
1. Enter or adjust deal assumptions and see results update
2. Save, load and duplicate named scenarios
3. See property-, equity- and partner-level (LP/GP) returns
4. Compare scenarios side by side and run sensitivities

**Users:** Misha only, running locally. No authentication; servers bind to `localhost`.

## Architecture
```
React UI (browser)  ──HTTP/JSON──▶  FastAPI (Python)  ──▶  re_uw engine (pure Python)
                                         │
                                         └──▶  Scenario store (JSON files at first, then a database later)
```
- **Engine** (`re_uw`): pure Python with no web code. It takes validated inputs and returns cash flows and metrics, and is fully unit-tested.
- **API** (FastAPI): thin layer that validates requests with Pydantic, calls the engine, and manages scenarios. It auto-generates an OpenAPI spec.
- **Frontend** (React + TypeScript): its TypeScript types are generated from the OpenAPI spec, so the frontend and backend can't drift apart.

## Stack
| Layer | Choice | Notes |
|---|---|---|
| Engine | Python 3.13, pandas/numpy, Pydantic v2 | Machine has Python 3.13.9 |
| API | FastAPI + Uvicorn | OpenAPI docs at `/api/docs` |
| Scenario store | JSON files in `scenarios/` behind a repository interface | Can switch to SQLite later without UI changes |
| Frontend build | Vite 8 + React 19 + TypeScript 5.9 | Machine has Node v24.16.0. `/api` proxied to FastAPI |
| UI components | Mantine 9 | |
| Data fetching | TanStack Query | Debounced recalculation |
| Forms | React Hook Form | |
| Tables | AG Grid Community | Excel-like cash flow tables |
| Charts | Recharts (Plotly for heatmaps if needed) | |
| API types | `openapi-typescript` | |
| Tests | pytest (engine + API), Vitest (frontend) | Playwright later if useful |
| Run locally | One script starts both servers | |
| Version control | Local Git repo, no remote | |

### Model conventions
- Annual periods. Year 0 = acquisition, Years 1..N = hold, exit at end of Year N valued on Year N+1 NOI
- Rates stored as decimals; rents in **SGD psf per month**; currency configurable (default **SGD**)
- Singapore market defaults (cap rates, property tax as % of annual value, stamp duty as a flat % of transaction costs at first)

### Design notes
- **Mixed-use from day one:** revenue is built from a list of *space components* (Office, Retail), each with its own NLA, market rent psf pm, rent growth, vacancy, credit loss and opex/recovery assumptions. Property-level items (property tax, management fee, capex, debt, exit) sit above the components.
- **Rent roll-ready:** each component's revenue has a `method` field. Phase 3 implements `market` (NLA × rent × occupancy). A later `rent_roll` method (lease-by-lease: tenant, area, rent, start/expiry, escalations, renewal probability, downtime, TI/LC) plugs into the same interface without changing the rest of the engine, API or UI.
- **Retail specifics (later):** turnover/percentage rent, service charge recoveries.
- **Exit:** single blended exit cap rate on total NOI at first; optional cap rate per component later.
- **Waterfall:** sits on top of the levered equity cash flow. LP/GP co-invest split, return of capital, preferred return, then IRR-hurdle promote tiers (configurable number of tiers), annual periods.

### OneDrive mitigations (code stays in OneDrive, per Misha)
- The Python venv lives **outside** OneDrive at `%USERPROFILE%\.venvs\re-uw-model`; the start script creates and uses it.
- `node_modules` stays inside `frontend/` (Vite needs it there). If syncing gets slow, pause OneDrive during `npm install`.
- `.gitignore` excludes `node_modules`, build output and caches.

### Folder structure
```
RE UW model/
├── PLAN.md                ← this file
├── CLAUDE.md              ← guide for Claude Code: structure, commands, conventions
├── README.md              ← setup and usage
├── .gitignore / .gitattributes
├── dev.ps1 / dev.bat      ← starts backend + frontend for local dev
├── backend/
│   ├── pyproject.toml
│   ├── re_uw/             ← engine: inputs.py, scenarios.py; later cashflow, debt, returns, waterfall, sensitivity
│   ├── api/               ← FastAPI app, routers, scenario repository
│   ├── scripts/           ← make_sample_scenario.py, gen_input_docs.py
│   └── tests/
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── api/           ← generated types + API client
│   │   ├── pages/         ← Underwriting, Compare, Sensitivity
│   │   └── components/
│   └── tests/
├── scenarios/             ← saved scenarios (JSON)
└── docs/
    ├── inputs.md          ← GENERATED input reference
    └── methodology.md     ← calculation logic, formula by formula
```

## Phases

### Phase 0: Agree scope and decisions ✅
- All questions answered; see the decision log

### Phase 1: Skeleton, end to end ✅ (first Windows run of `dev.bat` still to be confirmed)
- Folder structure, `CLAUDE.md`, `README.md`, `.gitignore`, dev start script, `git init` + first commit
- FastAPI with a `/health` endpoint; a React (Mantine) page that calls it and shows "API connected"
- **Checkpoint:** Misha runs one command and sees the React page talking to the API
- *Built:* `dev.bat` creates the venv at `%USERPROFILE%\.venvs\re-uw-model`, installs dependencies, starts API (8000) + UI (5173) and opens the browser. 2 API tests.

### Phase 2: Input model ✅
- Pydantic input classes: property, space components (Office, Retail), acquisition, operating expenses, capex, debt, exit, waterfall
- One sample scenario: Singapore CBD office with ground-floor retail, SGD, realistic defaults
- **Checkpoint:** Misha reviews the input list and defaults (`docs/inputs.md`, `scenarios/sample_sg_cbd_office_retail.json`)
- *Built:* `backend/re_uw/inputs.py` (schema v1, unknown keys rejected, cross-field validation), scenario load/save, sample generator, generated `docs/inputs.md`. 19 input tests.

### Phase 2b: Input model refinements (from SG research) ✅ (placeholders kept for now)
- Property tax on IRAS Annual Value (optional AV input, else `av_to_gpr_ratio` × GPR before vacancy)
- Retail: service charge / A&P recoveries and turnover (GTO) rent per component
- Leasing assumptions per component: lease term, renewal probability, rent-free, commissions, fit-out
- Deal structure (asset vs share) with SG stamp duty calculator (`re_uw/sg_tax.py`)
- Fund fees (asset management, acquisition, divestment); SORA base-rate curve overrides
- Sample office rent updated to $12.50 psf pm (CBRE Q3 2026 Core CBD Grade A: $12.75)
- Global assumptions documented: ex-GST (TOGC on acquisition), pre-tax
- **Placeholders to confirm:** leasing commissions (2.0 / 1.0 months new / renewal), office fit-out
  contribution ($5 psf, new leases), retail recoveries ($1.50 psf pm), retail turnover rent (5%),
  fund fees (0.5% AM on GAV, 1% acquisition, 0.5% divestment)
- **Checkpoint:** Misha confirms or replaces the placeholders

### Phase 3: Operating cash flow engine ✅
- Per component: GPR → vacancy and credit loss → other income → EGI; then property level: opex, property tax, management fee → NOI → capex → CF before debt
- Per-year overrides (rent growth, vacancy, one-off capex)
- Unit tests checked by hand
- **Checkpoint:** Misha reviews the annual cash flow for the sample deal
- *Built:* `re_uw/cashflow.py` (per component + property, Years 1..N+1), `python -m re_uw.report [--csv]`, 14 hand-checked tests. Sample Year 1 NOI S$32.6m, entry cap 3.67%.

### Phase 4: Debt, exit and returns 🔍 built, awaiting review
- Loan sizing (min of LTV, DSCR and debt yield), IO then amortisation, fee, balloon at exit
- Exit value from exit cap rate on forward NOI, less selling costs
- Metrics: unlevered/levered IRR, equity multiple, NPV, cash-on-cash, entry cap, yield on cost, DSCR, debt yield, LTV/LTC, sources and uses
- **Checkpoint:** metrics cross-checked against a quick Excel model
- *Built:* `finance.py`, `debt.py`, `returns.py` (`underwrite()`), fund fees, 3 cash flow streams, report extended, `scripts/make_crosscheck_xlsx.py` (live-formula Excel; matches Python exactly), 17 new tests (73 total). Sample: unlevered IRR 3.18%, equity IRR net 1.69%.

### Phase 5: Equity waterfall ⬜
- LP/GP co-invest split; return of capital; preferred return; N IRR-hurdle promote tiers
- Outputs: LP and GP distributions by year, IRR, equity multiple, GP promote amount
- Unit tests with a hand-calculated example
- **Checkpoint:** Misha reviews the waterfall for the sample deal

### Phase 6: API layer ⬜
- `POST /underwrite` (inputs → cash flow, returns and waterfall), `GET/POST/PUT/DELETE /scenarios`
- OpenAPI docs at `/docs`; TS types generated for the frontend; API tests
- **Checkpoint:** Misha tries the endpoints in the `/docs` page

### Phase 7: Frontend, underwriting page ⬜
- App shell and navigation; input form in tabs; KPI strip; cash flow table; charts; sources and uses; waterfall tab
- Recalculates as you edit (debounced)
- **Checkpoint:** Misha plays with the inputs and gives feedback on layout and usability

### Phase 8: Scenario management UI ⬜
- Save, save as, load, duplicate, delete; unsaved-changes indicator
- **Checkpoint:** feedback

### Phase 9: Scenario comparison page ⬜
- Side-by-side metrics (including LP/GP), diff of changed inputs, overlay charts
- **Checkpoint:** feedback

### Phase 10: Sensitivity page ⬜
- `POST /sensitivity` endpoint; 2D heatmap (e.g. exit cap × rent growth → levered IRR or LP IRR); tornado chart
- **Checkpoint:** feedback

### Phase 11: Optional extensions (pick any) ⬜
- [ ] Excel export (inputs, cash flow, metrics, waterfall)
- [ ] Rent roll / lease-by-lease tenancy schedule (`revenue_method = rent_roll`)
- [ ] Retail turnover rent from tenant sales (instead of a % uplift)
- [ ] Income tax at holding-vehicle level; GST cash timing if not a going-concern transfer
- [ ] Monthly periods
- [ ] SG leasehold handling (remaining lease affecting exit value)
- [ ] Per-component exit cap rates
- [ ] Development / value-add mode
- [ ] Database scenario store (SQLite)
- [ ] Docker packaging

## Decision log
| Date | Decision | Notes |
|---|---|---|
| 2026-10-19 | Build in phases with a checkpoint after each | Requested by Misha |
| 2026-10-19 | UI: FastAPI backend + React frontend (instead of Streamlit) | Engine stays UI-agnostic |
| 2026-10-19 | Local Git repo only, no GitHub remote for now | |
| 2026-10-19 | Tooling: Python 3.13.9, Node v24.16.0 | |
| 2026-10-19 | UI components: Mantine | |
| 2026-10-19 | Asset scope: office building with a retail component | Engine models space components |
| 2026-10-19 | Revenue: simple market rent first, extensible to a rent roll | `revenue_method` per component |
| 2026-10-19 | Equity waterfall (LP/GP) is a core requirement | New Phase 5 |
| 2026-10-19 | Code stays in OneDrive | venv placed outside OneDrive as mitigation |
| 2026-10-19 | Market defaults: Singapore / SGD | |
| 2026-10-19 | Single user (Misha), local only, no auth | |
| 2026-10-19 | Pinned TypeScript 5.9 (not 7.x) | TS 7 native compiler is new; 5.9 is the safer choice for now |
| 2026-10-19 | Vite dev server proxies `/api` to FastAPI | Browser talks to one origin; no CORS issues |
| 2026-10-19 | Revenue model uses a `method` discriminator (`"market"` now, `"rent_roll"` later) | Replaces the `revenue_method` field name in the earlier notes |
| 2026-10-19 | Property tax approximated as rate × effective rent (Annual Value proxy) | Review at Phase 2 checkpoint |
| 2026-10-19 | Property tax on IRAS Annual Value, not effective rent | IRAS AV = market gross rent excl. maintenance, assessed let or vacant; no vacancy refund since 2014 |
| 2026-10-19 | Office rents gross; retail gets recoveries + turnover rent | SG office rents quoted gross incl. service charge; GTO rent common in retail |
| 2026-10-19 | Deal structure toggle (asset BSD tiers vs 0.2% share duty) | Share deals avoid ~5% BSD on commercial; ACD is residential-only |
| 2026-10-19 | Steady-state leasing costs in market-rent mode | Rent-free ~1 month per lease year (Savills Dec 2025); 3-year leases |
| 2026-10-19 | Fund fees modelled (AM, acquisition, divestment) | Placeholders until fund terms provided |
| 2026-10-19 | Model is ex-GST (TOGC assumed) and pre-tax | Documented in docs/methodology.md |
| 2026-10-19 | Schema stays v1 (pre-release, no migration) | Only the sample scenario existed |
| 2026-10-19 | Placeholder assumptions kept for now | Leasing commissions, fit-out, retail recoveries/turnover, fund fees |
| 2026-10-19 | Credit loss applied after rent-free | No bad debt on rent-free months |
| 2026-10-19 | Projections show deductions as negatives; Year N+1 labelled "(fwd)" | Columns add up in the report |
| 2026-10-19 | Fund fees excluded from unlevered returns; equity IRR reported gross and net of fees | Net equity CF feeds the waterfall |
| 2026-10-19 | Floating-rate amortisation re-solves the annuity each year | Keeps the term fixed when SORA moves |
| 2026-10-19 | Sample deal returns are low (equity IRR 1.7% net) | Driven by 5% BSD, 3.75% exit vs 3.67% entry cap, 3.1% debt cost; see sensitivities at Phase 4 checkpoint |
