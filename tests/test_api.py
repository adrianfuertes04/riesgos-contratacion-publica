from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.db import GoldDB
from api.main import app, get_db
from pipelines.indicators.build_gold import build
from tests.test_indicators import synthetic_silver


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> Iterator[TestClient]:
    base: Path = tmp_path_factory.mktemp("api")
    synthetic_silver(base / "silver")
    build(base / "silver", base / "gold")
    db = GoldDB(base / "gold")
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_kpis(client: TestClient) -> None:
    body = client.get("/api/kpis").json()
    assert body["n_contracts"] == 54
    assert body["n_buyers"] == 1


def test_meta(client: TestClient) -> None:
    body = client.get("/api/meta").json()
    assert body["procedure"]["1"] == "Abierto"
    assert "I1" in body["indicators"]


def test_buyer_and_company(client: TestClient) -> None:
    buyers = client.get("/api/buyers").json()
    assert buyers[0]["buyer_id"] == "ORG1"
    profile = client.get("/api/buyers/ORG1").json()
    assert profile["buyer"]["n_contracts"] == 54
    assert {c["id"] for c in profile["companies"]} == {"B12345674", "B87654321"}
    company = client.get("/api/companies/B12345674").json()
    assert company["company"]["nif_valid"] is True
    assert client.get("/api/companies/NOEXISTE").status_code == 404
    ranked = client.get("/api/companies", params={"sort": "risk_score"}).json()
    assert all(c["n_contracts"] >= 10 for c in ranked)


def test_alerts_filters_and_paging(client: TestClient) -> None:
    all_alerts = client.get("/api/alerts", params={"size": 2}).json()
    assert all_alerts["total"] > 2 and len(all_alerts["items"]) == 2
    i3 = client.get("/api/alerts", params={"indicator": "I3"}).json()
    assert i3["total"] == 1
    assert "15000" in i3["items"][0]["explanation"]
    assert client.get("/api/alerts", params={"sort": "nope"}).status_code == 422


def test_territories_search_graph(client: TestClient) -> None:
    terr = client.get("/api/territories", params={"level": 3}).json()
    assert terr[0]["code"] == "ES300"
    assert client.get("/api/territories/ES30").json()["buyers"][0]["buyer_id"] == "ORG1"
    found = client.get("/api/search", params={"q": "empresa"}).json()
    assert {r["kind"] for r in found} == {"company"}
    g = client.get("/api/graph", params={"node": "buyer:ORG1", "depth": 2}).json()
    assert len(g["nodes"]) == 3 and len(g["edges"]) == 2
    assert client.get("/api/graph", params={"node": "x:1"}).status_code == 422
