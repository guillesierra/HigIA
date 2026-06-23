def test_health(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_list_sources(client) -> None:
    response = client.get("/api/sources")
    assert response.status_code == 200
    assert len(response.json()) >= 4


def test_consumption_filters(client) -> None:
    response = client.get("/api/consumption", params={"geography": "Asturias", "atc": "J01"})
    assert response.status_code == 200
    rows = response.json()
    assert rows
    assert all(row["geography"] == "Asturias" for row in rows)


def test_relationships(client) -> None:
    response = client.get("/api/relationships/drug/Diazepam")
    assert response.status_code == 200
    body = response.json()
    assert body["drugs"]
    assert body["alerts"]


def test_compare_before_after(client) -> None:
    response = client.get(
        "/api/consumption/compare-before-after",
        params={"alert_id": 1, "atc_code": "N05BA", "window_years": 2},
    )
    assert response.status_code == 200
    assert response.json()["metric"] == "dhd"

