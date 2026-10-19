# RE Underwriting Model

Acquisition underwriting for a Singapore office building with a retail component.
Python engine + FastAPI backend + React (Mantine) frontend. Build history and decisions: `PLAN.md`.

## Prerequisites
- Python 3.13 (`py -3.13` launcher or `python` on PATH)
- Node.js 24 (`node --version`)

## Start it (Windows)
Double-click **`dev.bat`**, or from PowerShell in this folder: `.\dev.bat`

On first run (and whenever dependencies change) it:
1. creates a Python venv at `%USERPROFILE%\.venvs\re-uw-model` (kept outside OneDrive),
2. installs the backend (`pip install -e backend[dev]`),
3. installs frontend packages (`npm install` in `frontend\`; pause OneDrive if slow).

It then opens two windows (API on port 8000, UI on port 5173) and your browser.
Close the two windows to stop.

- UI: http://127.0.0.1:5173
- API docs (try every endpoint): http://127.0.0.1:8000/api/docs

## Using the app
**Scenario bar (top):** pick a scenario; edits make it *Unsaved*. **Save** overwrites it,
**Save as / Duplicate** creates a new one, **Reset** discards edits, **Export Excel** downloads
all result tables, **Delete** removes the file. Scenarios are JSON files in `scenarios\`
(version them with Git).

**Underwriting page:** inputs on the left (all rates in %, rents in $ psf per month), results on
the right. Everything recalculates as you type. Result tabs: summary (sources & uses + all
metrics), operating cash flow, by component, returns (cash flow streams), debt, waterfall.
Use the `SGD m / k / units` toggle to change the table scale. Invalid inputs show a red message
explaining which field is wrong; the last valid result stays on screen.

**Compare page:** pick up to 6 scenarios (including your unsaved working copy). Shows every
metric side by side with the difference to the first column, equity cash flow and NOI charts,
and a table of the inputs that differ.

**Sensitivity page:** two-way table (pick any two drivers, step sizes and the output metric);
blue cells beat the current case, red cells are worse, the outlined cell is the current case.
The tornado ranks which single input moves the result most.

## Command line
```powershell
$py = "$env:USERPROFILE\.venvs\re-uw-model\Scripts\python.exe"
cd backend
& $py -m re_uw.report                                 # full underwriting of the sample, printed
& $py -m re_uw.report ..\scenarios\upside_sg_cbd_office_retail.json --csv ..\reports\upside.csv
& $py scripts\make_crosscheck_xlsx.py                # Excel cross-check with live formulas
```

## Tests
```powershell
cd backend;  & $py -m pytest -q        # engine + API (hand-checked numbers)
cd frontend; npm test                  # formatting / helpers
```

## Project layout
| Path | What |
|---|---|
| `backend/re_uw/` | Calculation engine (pure Python): inputs, cash flow, debt, returns, waterfall, sensitivity |
| `backend/api/` | FastAPI app, scenario storage, Excel export |
| `frontend/` | React + TypeScript UI |
| `scenarios/` | Saved scenarios (JSON) |
| `docs/inputs.md` | Every input field, with sample values (generated) |
| `docs/methodology.md` | How every number is calculated |
| `reports/` | Generated CSV/Excel outputs (not in Git) |

## Key assumptions
Annual periods; exit on forward NOI; ex-GST (acquisition treated as a transfer of a going
concern); pre-tax; SG property tax on IRAS Annual Value; BSD tiers or 0.2% share duty;
steady-state leasing costs in market-rent mode. Placeholder assumptions in the sample scenarios
(leasing commissions, fit-out, retail recoveries/turnover rent, fund fees) are flagged in
`PLAN.md`. Details in `docs/methodology.md`.
