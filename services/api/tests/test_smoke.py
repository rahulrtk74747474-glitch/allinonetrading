from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_demo_screener() -> None:
    response = client.post(
        "/api/v1/screener/scan",
        json={
            "universe": "nifty50",
            "timeframe": "1d",
            "conditions": [
                {"id": "rsi", "field": "rsi", "operator": ">", "value": 50}
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "demo"
    assert response.json()["results"]
