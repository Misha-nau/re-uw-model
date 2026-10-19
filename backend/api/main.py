"""FastAPI application. Thin layer over the re_uw engine.

Run (from backend/):  uvicorn api.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from re_uw import __version__

app = FastAPI(
    title="RE Underwriting Model API",
    version=__version__,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# The Vite dev server proxies /api to this app, so CORS is only a fallback
# for calling the API directly from the browser during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Health(BaseModel):
    status: str
    version: str


@app.get("/api/health", response_model=Health, tags=["system"])
def health() -> Health:
    return Health(status="ok", version=__version__)
