from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_platforms() -> None:
    response = client.get("/platforms")

    assert response.status_code == 200
    names = {platform["name"] for platform in response.json()}
    assert len(names) >= 5
    assert {"bilibili", "weibo", "douyin", "zhihu", "baidu", "toutiao", "ithome"}.issubset(names)


def test_plugin_hot_load_and_unload() -> None:
    load_response = client.post("/plugins/load", json={"path": "examples/sample_plugin.py"})
    assert load_response.status_code == 200
    assert load_response.json()["platform"] == "sample"

    platforms = {item["name"] for item in client.get("/platforms").json()}
    assert "sample" in platforms

    unload_response = client.delete("/plugins/sample")
    assert unload_response.status_code == 200
    names = {item["name"] for item in client.get("/platforms").json()}
    assert "sample" not in names
