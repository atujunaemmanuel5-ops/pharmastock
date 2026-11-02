from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health_and_products():
    assert client.get("/health").status_code == 200
    response = client.get("/products")
    assert response.status_code == 200
    assert len(response.json()) == 8


def test_forecast_validation_and_unknown_group():
    assert client.get("/forecast/R03?horizon=8").status_code == 422
    assert client.get("/forecast/UNKNOWN").status_code == 404
    response = client.get("/forecast/R03")
    assert response.status_code == 200
    assert len(response.json()["forecasts"]) == 7


def test_reorder_what_if_returns_a_new_planning_scenario():
    response = client.get("/reorder/R03/what-if", params={"usable_stock": 10, "demand_multiplier": 1.5, "lead_time_days": 14})
    assert response.status_code == 200
    assert response.json()["demand_multiplier"] == 1.5
    assert response.json()["lead_time_days"] == 14


def test_dispense_endpoint_blocks_misoprostol_without_reference():
    response = client.post("/dispense/check", json={"drug_ids": ["D029"]})
    assert response.status_code == 200
    assert response.json()["decision"] == "BLOCK"
    assert response.json()["audit_id"]
    allowed = client.post("/dispense/check", json={"drug_ids": ["D029"], "prescription_reference": "RX-1"})
    assert allowed.json()["decision"] in {"OK", "INFO"}


def test_safety_reference_endpoints_return_serializable_rows():
    rules = client.get("/safety/rules")
    interactions = client.get("/safety/interactions")
    assert rules.status_code == 200
    assert interactions.status_code == 200
    assert any(row["drug_id"] == "D029" for row in rules.json())
    assert interactions.json()


def test_what_if_validation_rejects_invalid_demand_multiplier():
    assert client.get("/reorder/R03/what-if", params={"demand_multiplier": 6}).status_code == 422


def test_production_auth_protects_dispense_checks(monkeypatch):
    monkeypatch.setenv("PHARMASTOCK_AUTH_REQUIRED", "true")
    monkeypatch.setenv("PHARMASTOCK_API_KEY", "test-api-key")
    monkeypatch.setenv("PHARMASTOCK_ADMIN_KEY", "test-admin-key")
    assert client.post("/dispense/check", json={"drug_ids": ["D005"]}).status_code == 401
    response = client.post("/dispense/check", headers={"X-API-Key": "test-api-key", "X-Actor-ID": "tester"}, json={"drug_ids": ["D005"]})
    assert response.status_code == 200
    monkeypatch.setenv("PHARMASTOCK_AUTH_REQUIRED", "false")


def test_confirm_dispense_decrements_one_unit_and_records_actor():
    before = {row["drug_id"]: row["usable_stock"] for row in client.get("/inventory/stock-summary").json()}
    response = client.post("/dispense/confirm", headers={"X-Actor-ID": "test-dispenser"}, json={"drug_ids": ["D005"]})
    assert response.status_code == 200
    after = {row["drug_id"]: row["usable_stock"] for row in client.get("/inventory/stock-summary").json()}
    assert after["D005"] == before["D005"] - 1
