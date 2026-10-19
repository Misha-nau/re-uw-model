# RE Underwriting Model

Acquisition underwriting for a Singapore office building with a retail component.
Python engine + FastAPI backend + React (Mantine) frontend. See `PLAN.md` for the build plan.

## Prerequisites
- Python 3.13 (`py -3.13` launcher or `python` on PATH)
- Node.js 24 (`node --version`)

## Quick start (Windows)
Double-click **`dev.bat`**, or from PowerShell in this folder:
```powershell
.\dev.bat
```
On first run it:
1. creates a Python venv at `%USERPROFILE%\.venvs\re-uw-model` (kept outside OneDrive),
2. installs the backend (`pip install -e backend[dev]`),
3. installs frontend packages (`npm install` in `frontend/`).

Then it opens two windows (API on port 8000, UI on port 5173) and your browser at
http://127.0.0.1:5173. Close the two windows to stop.

- UI: http://127.0.0.1:5173
- API docs: http://127.0.0.1:8000/api/docs

## Tests
```powershell
$py = "$env:USERPROFILE\.venvs\re-uw-model\Scripts\python.exe"
cd backend
& $py -m pytest -q
```

## Project layout
| Path | What |
|---|---|
| `backend/re_uw/` | Calculation engine (pure Python) and input model |
| `backend/api/` | FastAPI app |
| `frontend/` | React + TypeScript UI |
| `scenarios/` | Saved scenarios (JSON) |
| `docs/inputs.md` | Every input field, with sample values (generated) |
| `docs/methodology.md` | How the numbers are calculated |

## Status
Phases 1–4 are built: input model, operating cash flow, debt, exit, fees and returns. Run `python -m re_uw.report` from `backend\` to see the sample deal.
