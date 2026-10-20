"""Production entry point: seed an empty persistent store, then start the app."""
import os
import shutil
from pathlib import Path

import uvicorn


def seed_scenarios(source: Path, destination: Path) -> None:
    # Only initialize a new store; never restore scenarios the team has deleted.
    destination.mkdir(parents=True, exist_ok=True)
    marker = destination / ".initialized"
    if marker.exists():
        return
    for sample in source.glob("*.json"):
        target = destination / sample.name
        if not target.exists():
            shutil.copyfile(sample, target)
    marker.touch()


if __name__ == "__main__":
    seed_scenarios(Path("/app/seed-scenarios"), Path(os.environ["RE_UW_SCENARIOS_DIR"]))
    uvicorn.run("api.main:app", host="0.0.0.0", port=1337, workers=1)
