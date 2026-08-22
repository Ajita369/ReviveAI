from pathlib import Path

from fastapi.testclient import TestClient

from backend.database import seed_database
from backend.main import create_app
from data.generator import generate_dataset


def test_phase4_api_endpoints(tmp_path: Path) -> None:
    db_path = tmp_path / "phase4.db"
    dataset = generate_dataset(seed=42)
    seed_database(dataset.customers, dataset.transactions, db_path=db_path)
    client = TestClient(create_app(db_path))

    assert client.get("/health").json() == {"status": "ok"}

    response = client.get("/transactions", params={"status": "failed", "limit": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] > 0
    assert len(body["items"]) == 5
    assert all("gt_recoverable" not in item for item in body["items"])

    transaction_id = next(
        item["transaction_id"]
        for item in body["items"]
        if item.get("error_code") not in {"fraud_detected", "account_closed", "card_stolen"}
    )
    analysis = client.post(f"/analyze/{transaction_id}")
    assert analysis.status_code == 200
    assert "recommended_action" in analysis.json()

    recovery = client.post(f"/recover/{transaction_id}")
    assert recovery.status_code == 200
    assert recovery.json()["status"] in {"accepted", "recovered"}

    detail = client.get(f"/transactions/{transaction_id}")
    assert detail.status_code == 200
    assert len(detail.json()["attempts"]) == 1

    audit = client.get("/audit", params={"transaction_id": transaction_id})
    assert audit.status_code == 200
    assert audit.json()["items"]

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["transactions"] == 1000


def test_stubborn_gateway_demo_escalates_after_three_steps(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "demo.db"))

    assert client.post("/demo/reset").json()["status"] == "reset"
    for expected_attempts in (1, 2, 3):
        result = client.post("/demo/step").json()
        assert result["attempts"] == expected_attempts
    assert result["status"] == "escalated"

    detail = client.get("/transactions/txn_fail_demo").json()
    assert detail["transaction"]["recovery_status"] == "escalated"
    assert len(detail["attempts"]) == 3
    audit = client.get("/audit", params={"transaction_id": "txn_fail_demo"}).json()
    assert any(item["event_type"] == "recovery_escalated" for item in audit["items"])
