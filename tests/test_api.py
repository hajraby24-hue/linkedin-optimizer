from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi", reason="the API extra is not installed")
from fastapi.testclient import TestClient  # noqa: E402

from linkedin_optimizer import __version__  # noqa: E402
from linkedin_optimizer.api import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_rules_endpoint_lists_the_rule_set(client: TestClient) -> None:
    payload = client.get("/rules").json()
    assert payload["total_weight"] == 100.0
    assert {rule["id"] for rule in payload["rules"]} >= {"headline", "about", "experience"}


def test_analyze_scores_a_strong_profile(client: TestClient, strong_profile_data: dict) -> None:
    response = client.post("/analyze", json={"profile": strong_profile_data})
    assert response.status_code == 200
    payload = response.json()
    assert payload["score"] > 85
    assert payload["grade"] in {"A", "B"}
    assert payload["profile_name"] == "Layla Haddad"


def test_analyze_scores_a_weak_profile(client: TestClient, weak_profile_data: dict) -> None:
    payload = client.post("/analyze", json={"profile": weak_profile_data}).json()
    assert payload["grade"] == "F"
    assert payload["summary"]["critical"] >= 1
    assert payload["actions"][0]["suggestion"]


def test_analyze_accepts_an_empty_profile(client: TestClient) -> None:
    response = client.post("/analyze", json={"profile": {}})
    assert response.status_code == 200
    assert response.json()["score"] < 10


def test_max_actions_is_honoured(client: TestClient, weak_profile_data: dict) -> None:
    payload = client.post("/analyze", json={"profile": weak_profile_data, "max_actions": 2}).json()
    assert len(payload["actions"]) == 2


def test_markdown_is_opt_in(client: TestClient, weak_profile_data: dict) -> None:
    body = {"profile": weak_profile_data}
    assert "markdown" not in client.post("/analyze", json=body).json()
    with_markdown = client.post("/analyze", json={**body, "include_markdown": True}).json()
    assert with_markdown["markdown"].startswith("# Omar Nasser")


@pytest.mark.parametrize(
    "body",
    [
        {"profile": {"skills": "not a list"}},
        {"profile": {"experiences": [{"title": 5.5, "company": []}]}},
        {"max_actions": 3},
        {"profile": {}, "max_actions": 0},
    ],
)
def test_malformed_requests_are_rejected(client: TestClient, body: dict) -> None:
    assert client.post("/analyze", json=body).status_code == 422
