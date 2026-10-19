from fastapi.testclient import TestClient

from api.main import app
from re_uw import __version__

client = TestClient(app)


def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "version": __version__}


def test_openapi_available():
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    assert r.json()["info"]["title"] == "RE Underwriting Model API"
