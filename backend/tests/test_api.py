import json
import shutil

import pytest
from fastapi.testclient import TestClient

from api import main
from api.repository import ScenarioRepository, slugify
from re_uw.scenarios import SCENARIOS_DIR

SAMPLE_ID = "sample_sg_cbd_office_retail"


@pytest.fixture
def client(tmp_path):
    for f in SCENARIOS_DIR.glob("*.json"):
        shutil.copy(f, tmp_path / f.name)
    main.app.dependency_overrides[main.get_repo] = lambda: ScenarioRepository(tmp_path)
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()


@pytest.fixture
def sample(client):
    return client.get(f"/api/scenarios/{SAMPLE_ID}").json()


def test_list_and_get(client, sample):
    ids = [s["id"] for s in client.get("/api/scenarios").json()]
    assert SAMPLE_ID in ids and "upside_sg_cbd_office_retail" in ids
    assert sample["analysis"]["currency"] == "SGD"
    assert client.get("/api/scenarios/nope").status_code == 404
    assert client.get("/api/scenarios/..%2Fsecret").status_code == 404


def test_underwrite(client, sample):
    r = client.post("/api/underwrite", json=sample)
    assert r.status_code == 200
    body = r.json()
    assert body["metrics"]["entry_cap_rate"] == pytest.approx(0.036664, abs=1e-5)
    assert body["metrics"]["lp_irr"] is not None
    assert body["sizing"]["binding"] == "ltv"
    labels = [row["label"] for row in body["operating"]["rows"]]
    assert "Net operating income" in labels
    assert len(body["series"]["equity_cf"]) == 6  # Y0..Y5
    vac = next(r for r in body["components"][0]["table"]["rows"] if r["label"] == "Vacancy")
    assert vac["kind"] == "pct" and vac["values"][0] == pytest.approx(0.06)


def test_underwrite_validation_error(client, sample):
    sample["components"][0]["revenue"]["vacancy"] = 1.5
    r = client.post("/api/underwrite", json=sample)
    assert r.status_code == 422


def test_crud_cycle(client, sample):
    sample["scenario"]["name"] = "My Test Case"
    r = client.post("/api/scenarios", json={"inputs": sample})
    assert r.status_code == 201
    sid = r.json()["id"]
    assert sid == "my_test_case"
    # second create with same name gets a suffix
    assert client.post("/api/scenarios", json={"inputs": sample}).json()["id"] == "my_test_case_2"
    # explicit duplicate id -> 409
    assert client.post("/api/scenarios", json={"inputs": sample, "id": sid}).status_code == 409
    # update
    sample["exit"]["exit_cap_rate"] = 0.04
    assert client.put(f"/api/scenarios/{sid}", json=sample).status_code == 200
    assert client.get(f"/api/scenarios/{sid}").json()["exit"]["exit_cap_rate"] == 0.04
    # duplicate
    d = client.post(f"/api/scenarios/{sid}/duplicate", json={"name": "Copy of test"})
    assert d.status_code == 201 and d.json()["name"] == "Copy of test"
    # delete
    assert client.delete(f"/api/scenarios/{sid}").status_code == 204
    assert client.get(f"/api/scenarios/{sid}").status_code == 404
    assert client.put("/api/scenarios/missing", json=sample).status_code == 404


def test_saved_file_is_valid_json(client, sample, tmp_path):
    sid = client.post("/api/scenarios", json={"inputs": sample, "id": "abc"}).json()["id"]
    path = next(tmp_path.glob(f"{sid}.json"))
    assert json.loads(path.read_text())["scenario"]["name"] == sample["scenario"]["name"]


def test_sensitivity_grid(client, sample):
    r = client.post("/api/sensitivity", json={
        "inputs": sample, "x": "exit_cap", "y": "c0_growth", "metric": "levered_irr", "steps": 1})
    assert r.status_code == 200
    g = r.json()
    assert len(g["x_values"]) == 3 and len(g["values"]) == 3
    assert g["values"][1][1] == pytest.approx(g["base"])  # centre cell = base case
    assert g["x"]["step"] == pytest.approx(0.0025)
    # higher exit cap -> lower IRR
    assert g["values"][1][0] > g["values"][1][2]


def test_sensitivity_invalid_cell_is_null(client, sample):
    r = client.post("/api/sensitivity", json={
        "inputs": sample, "x": "c0_vacancy", "y": "exit_cap", "x_values": [0.05, 1.5],
        "y_values": [0.0375]})
    assert r.json()["values"][0][1] is None


def test_unknown_param(client, sample):
    r = client.post("/api/sensitivity", json={"inputs": sample, "x": "zzz", "y": "exit_cap"})
    assert r.status_code == 422


def test_tornado_and_parameters(client, sample):
    params = client.post("/api/sensitivity/parameters", json=sample).json()
    assert {"exit_cap", "c0_rent", "c1_vacancy"} <= {p["key"] for p in params}
    t = client.post("/api/tornado", json={"inputs": sample, "metric": "unlevered_irr"}).json()
    swings = [abs(b["high"] - b["low"]) for b in t["bars"]]
    assert swings == sorted(swings, reverse=True)


def test_metrics_catalog(client):
    keys = [m["key"] for m in client.get("/api/metrics").json()]
    assert "levered_irr" in keys and "gp_promote" in keys


def test_export_xlsx(client, sample):
    r = client.post("/api/export", json=sample)
    assert r.status_code == 200
    assert r.content[:2] == b"PK"  # xlsx is a zip
    assert "attachment" in r.headers["content-disposition"]


def test_slugify():
    assert slugify("Upside - share deal, 3.5%!") == "upside_share_deal_3_5"
