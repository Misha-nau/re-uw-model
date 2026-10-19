"""Load and save scenario JSON files.

Phase 2 provides plain file helpers. Phase 6 wraps these in a repository interface used
by the API, so the storage can later move to SQLite without touching the UI.
"""

from __future__ import annotations

import json
from pathlib import Path

from .inputs import UnderwritingInputs

# backend/re_uw/scenarios.py -> project root is two levels above backend/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = PROJECT_ROOT / "scenarios"


def load_scenario(path: str | Path) -> UnderwritingInputs:
    with open(path, encoding="utf-8") as f:
        return UnderwritingInputs.model_validate(json.load(f))


def save_scenario(inputs: UnderwritingInputs, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(inputs.model_dump_json(indent=2))
        f.write("\n")
    return path
