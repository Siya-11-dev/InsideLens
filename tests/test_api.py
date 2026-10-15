from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "en" in body["languages"]


def test_index_and_static():
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/styles.css").status_code == 200


def test_analysis_endpoint():
    r = client.get("/api/analysis?seed=20261015")
    assert r.status_code == 200
    body = r.json()
    home, away = (int(x) for x in body["score"].split("-"))
    assert home + away == len(body["goals"])
    assert body["goals"]
    assert body["state"]["home"]["possession"] > 0


def test_analysis_translation():
    r = client.get("/api/analysis?seed=20261015&translate=true")
    assert r.status_code == 200
    body = r.json()
    goal = body["goals"][0]
    assert goal["translations"]["es"]
    assert goal["translations"]["ar"]


def test_recap_endpoint():
    r = client.get("/api/recap?seed=20261015")
    assert r.status_code == 200
    recap = r.json()["recap"]
    assert "Full-time" in recap


def test_recap_personalized_es():
    r = client.get("/api/recap?seed=20261015&persona=global-fan-es")
    assert r.status_code == 200
    assert "Goles" in r.json()["recap"]


def test_personas_endpoint():
    r = client.get("/api/personas")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()["personas"]}
    assert "studio-analyst" in ids


def test_teams_endpoint():
    r = client.get("/api/teams")
    assert r.status_code == 200
    teams = r.json()["teams"]
    assert len(teams) == 20
    ids = {t["id"] for t in teams}
    assert {"MUN", "MCI", "ARS", "LIV"} <= ids


def test_analysis_with_selected_teams():
    r = client.get("/api/analysis?seed=1&home=ARS&away=TOT")
    assert r.status_code == 200
    match = r.json()["match"]
    assert match["home"]["name"] == "Arsenal"
    assert match["away"]["name"] == "Tottenham Hotspur"
    assert match["match_id"] == "ARS-TOT-2026"


def test_highlights_endpoint():
    r = client.get("/api/highlights?seed=20261015&persona=fan-home")
    assert r.status_code == 200
    highlights = r.json()["highlights"]
    assert highlights
    assert highlights[0]["team_id"] == "HOME"


def test_personalize_endpoint():
    r = client.get("/api/personalize?seed=20261015&persona=studio-analyst")
    assert r.status_code == 200
    body = r.json()
    assert body["persona"]["id"] == "studio-analyst"
    assert body["insights"]
    assert body["insights"][0]["show_factors"] is True


def test_dataset_export_endpoint():
    r = client.get("/api/dataset/export?seed=20261015&format=csv")
    assert r.status_code == 200
    body = r.json()
    assert body["rows"] > 1000
    assert body["format"] == "csv"


def test_store_stats_endpoint():
    r = client.get("/api/store/stats")
    assert r.status_code == 200
    assert "backend" in r.json()


