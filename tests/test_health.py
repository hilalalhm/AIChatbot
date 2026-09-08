from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok():
    # The context manager triggers the lifespan so init_db() runs.
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] in ("ok", "degraded")
        assert "database" in body
        assert "providers" in body
        assert "telegram" in body


def test_root():
    with TestClient(app) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"