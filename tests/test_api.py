import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from safedesk import api  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SAFEDESK_TRACE_DIR", str(tmp_path))
    api._boot()
    return TestClient(api.app)


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_chat_keeps_session_and_reports_metrics(client):
    first = client.post("/chat", json={"message": "I need a refund"}).json()
    sid = first["session_id"]
    client.post("/chat", json={"message": "Order A1002", "session_id": sid})
    third = client.post("/chat", json={"message": "ana.ruiz@example.com", "session_id": sid}).json()
    assert "issued a refund" in third["reply"]
    assert all("ana.ruiz@example.com" not in str(c) for c in third["tool_calls"])
    metrics = client.get("/metrics").json()
    assert metrics["refunds_issued"] == 1 and metrics["turns"] == 3


def test_index_page_served(client):
    resp = client.get("/")
    assert resp.status_code == 200 and "SafeDesk" in resp.text
