"""Write the API's OpenAPI spec to frontend/src/api/openapi.json.

Run from backend/:  python scripts/export_openapi.py
Then in frontend/:  npm run gen:api   (regenerates src/api/schema.ts)
"""

import json

from api.main import app
from re_uw.scenarios import PROJECT_ROOT

out = PROJECT_ROOT / "frontend" / "src" / "api" / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8", newline="\n")
print(f"wrote {out}")
