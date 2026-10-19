"""Scenario storage: one JSON file per scenario in a folder.

Kept behind this small interface so it can later move to SQLite without API/UI changes.
"""

from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from re_uw.inputs import UnderwritingInputs
from re_uw.scenarios import SCENARIOS_DIR, load_scenario, save_scenario

ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")


class ScenarioNotFound(KeyError):
    pass


class ScenarioExists(ValueError):
    pass


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return (s or "scenario")[:60]


class ScenarioRepository:
    def __init__(self, folder: Path | None = None):
        env = os.environ.get("RE_UW_SCENARIOS_DIR")
        self.folder = Path(folder or env or SCENARIOS_DIR)
        self.folder.mkdir(parents=True, exist_ok=True)

    def _path(self, scenario_id: str) -> Path:
        if not ID_RE.match(scenario_id):
            raise ScenarioNotFound(scenario_id)
        return self.folder / f"{scenario_id}.json"

    def list(self) -> list[dict]:
        out = []
        for p in sorted(self.folder.glob("*.json")):
            try:
                with open(p, encoding="utf-8") as f:
                    meta = json.load(f).get("scenario", {})
            except (OSError, json.JSONDecodeError):
                continue
            out.append({
                "id": p.stem,
                "name": meta.get("name", p.stem),
                "description": meta.get("description", ""),
                "updated_at": datetime.fromtimestamp(p.stat().st_mtime, UTC).isoformat(),
            })
        return sorted(out, key=lambda s: s["name"].lower())

    def get(self, scenario_id: str) -> UnderwritingInputs:
        p = self._path(scenario_id)
        if not p.exists():
            raise ScenarioNotFound(scenario_id)
        return load_scenario(p)

    def exists(self, scenario_id: str) -> bool:
        try:
            return self._path(scenario_id).exists()
        except ScenarioNotFound:
            return False

    def create(self, inputs: UnderwritingInputs, scenario_id: str | None = None) -> str:
        if scenario_id:
            if self.exists(scenario_id):
                raise ScenarioExists(scenario_id)
            self._path(scenario_id)  # validates the id
        else:
            base = slugify(inputs.scenario.name)
            scenario_id, k = base, 2
            while self.exists(scenario_id):
                scenario_id, k = f"{base}_{k}", k + 1
        save_scenario(inputs, self._path(scenario_id))
        return scenario_id

    def save(self, scenario_id: str, inputs: UnderwritingInputs) -> None:
        p = self._path(scenario_id)
        if not p.exists():
            raise ScenarioNotFound(scenario_id)
        save_scenario(inputs, p)

    def delete(self, scenario_id: str) -> None:
        p = self._path(scenario_id)
        if not p.exists():
            raise ScenarioNotFound(scenario_id)
        p.unlink()
