from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_agent_endpoint():
    r = client.get("/api/agent?seed=20261015&question=Why%20did%20the%20home%20team%20score%3F")
    assert r.status_code == 200
    body = r.json()
    assert body["answer"]
    assert "tools" in body
    assert body["context"]["score"]


def test_heatmap_endpoint():
    r = client.get("/api/heatmap?seed=20261015")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0
    assert len(body["grid"]) == body["bins_y"]


def test_pass_network_endpoint():
    r = client.get("/api/pass-network?seed=20261015")
    assert r.status_code == 200
    body = r.json()
    assert body["nodes"]
    assert body["edges"] is not None


def test_xt_endpoint():
    r = client.get("/api/xt?seed=20261015")
    assert r.status_code == 200
    body = r.json()
    assert body["home"] >= 0
    assert body["away"] >= 0
    assert body["top"]
